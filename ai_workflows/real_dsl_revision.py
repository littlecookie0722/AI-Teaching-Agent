"""Local revision draft builder for real LLM generated DSL files."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from cli.dsl import DslValidationError, load_schema, load_yaml, validate_dsl
from providers.mock_provider import ProviderError
from providers.real_llm_demo_dsl import RealLlmDemoDslRequest, run_real_llm_demo_dsl_generation


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_KINDS = {"lab", "exam", "grading", "ppt"}
DEFAULT_SOURCE_BY_KIND = {
    "lab": "examples/output/real-llm-lab.json",
    "exam": "examples/output/real-llm-exam.json",
    "grading": "examples/output/real-llm-grading.json",
    "ppt": "examples/output/real-llm-ppt.json",
}
DEFAULT_OUTPUT_BY_KIND = {
    "lab": "examples/output/real-llm-lab-revision.json",
    "exam": "examples/output/real-llm-exam-revision.json",
    "grading": "examples/output/real-llm-grading-revision.json",
    "ppt": "examples/output/real-llm-ppt-revision.json",
}
DEFAULT_REPORT_BY_KIND = {
    "lab": "examples/output/real-llm-lab-revision-report.json",
    "exam": "examples/output/real-llm-exam-revision-report.json",
    "grading": "examples/output/real-llm-grading-revision-report.json",
    "ppt": "examples/output/real-llm-ppt-revision-report.json",
}
DEFAULT_BATCH_REPORT_PATH = "examples/output/real-llm-demo-revision-batch-report.json"
DEFAULT_DIFF_PREVIEW_PATH = "examples/output/real-llm-demo-revision-diff-preview.json"
DEFAULT_DECISION_REPORT_PATH = "examples/output/real-llm-demo-revision-decision-report.json"
DEFAULT_PROMOTION_OUTPUT_PATH = "examples/output/real-llm-demo-revision-promoted-candidate.json"
DEFAULT_PROMOTION_REPORT_PATH = "examples/output/real-llm-demo-revision-promotion-report.json"
PROVIDER_MODE_LOCAL = "local"
PROVIDER_MODE_REAL_LLM = "real-llm"
SUPPORTED_PROVIDER_MODES = {PROVIDER_MODE_LOCAL, PROVIDER_MODE_REAL_LLM}
SUPPORTED_REVISION_DECISIONS = {"approve", "reject", "request-change"}
REAL_LLM_REVISION_MODE = "REAL_LLM_DSL_REVISION_DRAFT"
ClientFactory = Callable[..., Any]


class RealDslRevisionError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def create_real_dsl_revision_draft(
    *,
    kind: str,
    source_path: Path,
    reviewer: str,
    comment: str,
    target_sections: list[str] | None = None,
    requested_changes: list[str] | None = None,
    output_path: Path | None = None,
    report_output_path: Path | None = None,
    provider_mode: str = PROVIDER_MODE_LOCAL,
    model: str | None = None,
    base_url: str | None = None,
    timeout_seconds: int = 60,
    max_output_tokens: int = 2200,
    explicit_real_call_opt_in: bool = False,
    confirm_waiting_review: bool = False,
    confirm_no_auto_publish: bool = False,
    root: Path = ROOT,
    trace_id: str | None = None,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    kind = _normalize_kind(kind)
    provider_mode = _normalize_provider_mode(provider_mode)
    reviewer = str(reviewer or "").strip()
    comment = str(comment or "").strip()
    target_sections = _normalize_string_list(target_sections)
    requested_changes = _normalize_string_list(requested_changes)
    if not reviewer:
        raise RealDslRevisionError("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}])
    if not comment:
        raise RealDslRevisionError("VALIDATION_ERROR", "参数错误", [{"field": "comment", "reason": "缺少参数"}])

    source_path = _resolve_path(source_path, root)
    source_dsl = _load_and_validate_source(kind, source_path, root=root)
    provider_result: dict[str, Any] | None = None
    if provider_mode == PROVIDER_MODE_REAL_LLM:
        provider_result = _run_real_llm_revision(
            kind=kind,
            source_path=source_path,
            source_dsl=source_dsl,
            reviewer=reviewer,
            comment=comment,
            target_sections=target_sections,
            requested_changes=requested_changes,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            explicit_real_call_opt_in=explicit_real_call_opt_in,
            confirm_waiting_review=confirm_waiting_review,
            confirm_no_auto_publish=confirm_no_auto_publish,
            root=root,
            trace_id=trace_id,
            client_factory=client_factory,
        )
        revised_dsl = provider_result["dsl"]
        changed_fields = _changed_fields_from_revision(source_dsl, revised_dsl)
    else:
        revised_dsl, changed_fields = _apply_revision(
            kind,
            source_dsl,
            reviewer=reviewer,
            comment=comment,
            target_sections=target_sections,
            requested_changes=requested_changes,
        )
    try:
        validate_dsl(revised_dsl, load_schema(kind, root))
    except DslValidationError as exc:
        raise RealDslRevisionError("SCHEMA_VALIDATION_ERROR", "修订版 DSL Schema 校验失败", exc.errors) from exc

    output_path = _resolve_path(output_path or Path(DEFAULT_OUTPUT_BY_KIND[kind]), root)
    report_output_path = _resolve_path(report_output_path or Path(DEFAULT_REPORT_BY_KIND[kind]), root)
    _write_json(output_path, revised_dsl)
    revision_report = _build_revision_report(
        kind=kind,
        source_path=source_path,
        output_path=output_path,
        report_output_path=report_output_path,
        reviewer=reviewer,
        comment=comment,
        target_sections=target_sections,
        requested_changes=requested_changes,
        source_dsl=source_dsl,
        revised_dsl=revised_dsl,
        changed_fields=changed_fields,
        provider_mode=provider_mode,
        provider_result=provider_result,
        trace_id=trace_id,
    )
    _write_json(report_output_path, revision_report)
    return {
        "realDslRevisionDraft": revision_report,
        "revisedDsl": revised_dsl,
        "sourcePath": _path_str(source_path, root),
        "outputPath": _path_str(output_path, root),
        "reportOutputPath": _path_str(report_output_path, root),
        "mode": revision_report["mode"],
        "provider": revision_report.get("provider"),
        "safety": revision_report["safety"],
    }


def create_real_dsl_revision_batch_from_preview(
    *,
    preview_path: Path,
    reviewer: str,
    output_dir: Path | None = None,
    report_output_path: Path | None = None,
    root: Path = ROOT,
    trace_id: str | None = None,
) -> dict[str, Any]:
    reviewer = str(reviewer or "").strip()
    if not reviewer:
        raise RealDslRevisionError("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}])
    preview_path = _resolve_path(preview_path, root)
    preview = _load_revision_preview(preview_path)
    suggestions = _list_of_objects(preview.get("revisionSuggestions"))
    if not suggestions:
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "审核预览没有可执行修订建议",
            [{"field": "preview.revisionSuggestions", "reason": "至少需要 1 条建议"}],
        )
    output_dir = _resolve_path(output_dir or Path("examples/output"), root)
    report_output_path = _resolve_path(report_output_path or Path(DEFAULT_BATCH_REPORT_PATH), root)
    drafts: list[dict[str, Any]] = []
    for index, suggestion in enumerate(suggestions, start=1):
        kind = _normalize_kind(str(suggestion.get("kind") or ""))
        comment = str(suggestion.get("comment") or "").strip()
        if not comment:
            raise RealDslRevisionError(
                "VALIDATION_ERROR",
                "修订建议缺少 comment",
                [{"field": f"preview.revisionSuggestions[{index - 1}].comment", "reason": "缺少参数"}],
            )
        target_section = str(suggestion.get("targetSection") or "").strip()
        suggestion_id = _safe_file_part(str(suggestion.get("id") or f"suggestion_{index}"))
        output_path = output_dir / f"real-llm-{kind}-revision-{suggestion_id}.json"
        draft_report_path = output_dir / f"real-llm-{kind}-revision-{suggestion_id}-report.json"
        draft_result = create_real_dsl_revision_draft(
            kind=kind,
            source_path=root / DEFAULT_SOURCE_BY_KIND[kind],
            reviewer=reviewer,
            comment=comment,
            target_sections=[target_section] if target_section else [],
            requested_changes=[comment],
            output_path=output_path,
            report_output_path=draft_report_path,
            provider_mode=PROVIDER_MODE_LOCAL,
            root=root,
            trace_id=trace_id,
        )
        draft = draft_result["realDslRevisionDraft"]
        drafts.append(
            {
                "suggestionId": suggestion.get("id"),
                "kind": kind,
                "targetSection": target_section,
                "commentPreview": _take_text(comment, 180),
                "outputPath": draft_result["outputPath"],
                "reportOutputPath": draft_result["reportOutputPath"],
                "revisedDslId": draft.get("revisedDslId"),
                "revisedStatus": draft.get("revisedStatus"),
                "changedFields": draft.get("changedFields", []),
                "schemaValidated": draft.get("schemaValidated") is True,
                "safety": draft.get("safety", {}),
            }
        )
    batch_report = _build_batch_revision_report(
        preview_path=preview_path,
        report_output_path=report_output_path,
        reviewer=reviewer,
        preview=preview,
        drafts=drafts,
        trace_id=trace_id,
    )
    _write_json(report_output_path, batch_report)
    return {
        "realDslRevisionBatch": batch_report,
        "drafts": drafts,
        "previewPath": _path_str(preview_path, root),
        "reportOutputPath": _path_str(report_output_path, root),
        "mode": batch_report["mode"],
        "safety": batch_report["safety"],
    }


def build_real_dsl_revision_diff_preview(
    *,
    batch_report_path: Path,
    output_path: Path | None = None,
    root: Path = ROOT,
    trace_id: str | None = None,
) -> dict[str, Any]:
    batch_report_path = _resolve_path(batch_report_path, root)
    batch = _load_revision_batch_report(batch_report_path)
    draft_diffs: list[dict[str, Any]] = []
    for draft in _list_of_objects(batch.get("drafts")):
        kind = _normalize_kind(str(draft.get("kind") or ""))
        source_path = root / DEFAULT_SOURCE_BY_KIND[kind]
        revised_path = _resolve_path(Path(str(draft.get("outputPath") or "")), root)
        source_dsl = _load_and_validate_source(kind, source_path, root=root)
        revised_dsl = _load_and_validate_source(kind, revised_path, root=root)
        field_diffs = [
            _build_field_diff(field, source_dsl=source_dsl, revised_dsl=revised_dsl)
            for field in _normalize_string_list(draft.get("changedFields"))
        ]
        draft_diffs.append(
            {
                "suggestionId": draft.get("suggestionId"),
                "kind": kind,
                "targetSection": draft.get("targetSection"),
                "sourcePath": _path_str(source_path, root),
                "revisedPath": _path_str(revised_path, root),
                "sourceDslId": _object(source_dsl.get("metadata")).get("id"),
                "revisedDslId": _object(revised_dsl.get("metadata")).get("id"),
                "sourceTitle": _object(source_dsl.get("metadata")).get("title"),
                "revisedTitle": _object(revised_dsl.get("metadata")).get("title"),
                "sourceStatus": source_dsl.get("status"),
                "revisedStatus": revised_dsl.get("status"),
                "schemaValidated": True,
                "changedFieldTotal": len(field_diffs),
                "fieldDiffs": field_diffs,
                "summary": {
                    "source": _dsl_summary(kind, source_dsl),
                    "revised": _dsl_summary(kind, revised_dsl),
                },
                "reviewRecommendation": "REVIEW_BEFORE_APPROVAL",
            }
        )

    diff_total = sum(draft["changedFieldTotal"] for draft in draft_diffs)
    safety = {
        "mode": "LOCAL_REAL_DSL_REVISION_DIFF_PREVIEW",
        "realLlmCalled": False,
        "newLlmRequestSent": False,
        "secretsRead": False,
        "networkAccess": False,
        "taskCreated": False,
        "artifactCreated": output_path is not None,
        "reviewRequired": True,
        "generatedStatus": "WAITING_REVIEW",
        "answerVisibleToCandidate": False,
        "gradingRefVisibleToCandidate": False,
        "autoApproveAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
    }
    preview = {
        "component": "RealDslRevisionDiffPreview",
        "mode": "LOCAL_REAL_DSL_REVISION_DIFF_PREVIEW",
        "sourceBatchReportPath": _path_str(batch_report_path, root),
        "sourcePreviewPath": batch.get("sourcePreviewPath"),
        "summary": {
            "draftTotal": len(draft_diffs),
            "diffTotal": diff_total,
            "schemaValidatedTotal": sum(1 for draft in draft_diffs if draft.get("schemaValidated") is True),
            "allDraftsWaitingReview": all(draft.get("revisedStatus") == "WAITING_REVIEW" for draft in draft_diffs),
            "manualReviewRequired": True,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        },
        "draftDiffs": draft_diffs,
        "safety": safety,
    }
    if trace_id:
        preview["traceId"] = trace_id
    if output_path is not None:
        output_path = _resolve_path(output_path, root)
        _write_json(output_path, preview)
    return {
        "realDslRevisionDiffPreview": preview,
        "batchReportPath": _path_str(batch_report_path, root),
        "outputPath": _path_str(output_path, root) if output_path is not None else None,
        "mode": preview["mode"],
        "safety": safety,
    }


def create_real_dsl_revision_decision(
    *,
    diff_preview_path: Path,
    suggestion_id: str,
    reviewer: str,
    decision: str,
    reason: str | None = None,
    output_path: Path | None = None,
    root: Path = ROOT,
    trace_id: str | None = None,
) -> dict[str, Any]:
    reviewer = str(reviewer or "").strip()
    suggestion_id = str(suggestion_id or "").strip()
    decision = _normalize_revision_decision(decision)
    reason = str(reason or "").strip()
    if not reviewer:
        raise RealDslRevisionError("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}])
    if not suggestion_id:
        raise RealDslRevisionError("VALIDATION_ERROR", "参数错误", [{"field": "suggestionId", "reason": "缺少参数"}])
    if decision in {"reject", "request-change"} and not reason:
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "reason", "reason": "reject/request-change 必须填写原因"}],
        )

    diff_preview_path = _resolve_path(diff_preview_path, root)
    diff_preview = _load_revision_diff_preview(diff_preview_path)
    draft = _find_draft_diff(diff_preview, suggestion_id)
    decision_status = {
        "approve": "REVISION_APPROVED_FOR_MANUAL_MERGE",
        "reject": "REVISION_REJECTED",
        "request-change": "REVISION_CHANGE_REQUESTED",
    }[decision]
    safety = {
        "mode": "LOCAL_REAL_DSL_REVISION_DECISION",
        "realLlmCalled": False,
        "newLlmRequestSent": False,
        "secretsRead": False,
        "networkAccess": False,
        "taskCreated": False,
        "artifactCreated": output_path is not None,
        "reviewRequired": True,
        "sourceDslModified": False,
        "revisedDslModified": False,
        "manualMergeRequired": decision == "approve",
        "answerVisibleToCandidate": False,
        "gradingRefVisibleToCandidate": False,
        "autoApproveAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
    }
    report = {
        "component": "RealDslRevisionDecision",
        "mode": "LOCAL_REAL_DSL_REVISION_DECISION",
        "sourceDiffPreviewPath": _path_str(diff_preview_path, root),
        "suggestionId": suggestion_id,
        "kind": draft.get("kind"),
        "targetSection": draft.get("targetSection"),
        "sourcePath": draft.get("sourcePath"),
        "revisedPath": draft.get("revisedPath"),
        "sourceDslId": draft.get("sourceDslId"),
        "revisedDslId": draft.get("revisedDslId"),
        "sourceStatus": draft.get("sourceStatus"),
        "revisedStatus": draft.get("revisedStatus"),
        "reviewer": reviewer,
        "decision": decision,
        "decisionStatus": decision_status,
        "reasonPreview": _take_text(reason, 220),
        "changedFieldTotal": draft.get("changedFieldTotal", 0),
        "changedFields": [field.get("field") for field in _list_of_objects(draft.get("fieldDiffs"))],
        "manualMergeRequired": decision == "approve",
        "manualReviewRequired": True,
        "sourceDslModified": False,
        "revisedDslModified": False,
        "publishBlockedUntilApproved": True,
        "nextRequiredAction": {
            "approve": "manual_merge_or_promote_revision_after_policy_review",
            "reject": "close_revision_or_create_new_revision_request",
            "request-change": "create_followup_revision_request",
        }[decision],
        "safety": safety,
    }
    if trace_id:
        report["traceId"] = trace_id
    if output_path is not None:
        output_path = _resolve_path(output_path, root)
        _write_json(output_path, report)
    return {
        "realDslRevisionDecision": report,
        "diffPreviewPath": _path_str(diff_preview_path, root),
        "outputPath": _path_str(output_path, root) if output_path is not None else None,
        "mode": report["mode"],
        "safety": safety,
    }


def promote_real_dsl_revision_candidate(
    *,
    decision_report_path: Path,
    reviewer: str,
    output_path: Path | None = None,
    report_output_path: Path | None = None,
    root: Path = ROOT,
    trace_id: str | None = None,
) -> dict[str, Any]:
    reviewer = str(reviewer or "").strip()
    if not reviewer:
        raise RealDslRevisionError("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}])

    decision_report_path = _resolve_path(decision_report_path, root)
    decision = _load_revision_decision_report(decision_report_path)
    if decision.get("decision") != "approve":
        raise RealDslRevisionError(
            "REVISION_NOT_APPROVED",
            "只有 approve 的修订决策可以提升为候选 DSL",
            [{"field": "decision", "reason": "expected approve"}],
        )
    if decision.get("decisionStatus") != "REVISION_APPROVED_FOR_MANUAL_MERGE":
        raise RealDslRevisionError(
            "REVISION_NOT_APPROVED",
            "修订决策状态不可提升",
            [{"field": "decisionStatus", "reason": "expected REVISION_APPROVED_FOR_MANUAL_MERGE"}],
        )

    kind = _normalize_kind(str(decision.get("kind") or ""))
    revised_path = _resolve_path(Path(str(decision.get("revisedPath") or "")), root)
    revised_dsl = _load_and_validate_source(kind, revised_path, root=root)
    if revised_dsl.get("status") != "WAITING_REVIEW":
        raise RealDslRevisionError(
            "SCHEMA_VALIDATION_ERROR",
            "修订版 DSL 状态不可提升",
            [{"field": "$.status", "reason": "expected WAITING_REVIEW"}],
        )

    promoted_dsl = copy.deepcopy(revised_dsl)
    metadata = _object(promoted_dsl.setdefault("metadata", {}))
    source_revised_id = str(metadata.get("id") or decision.get("revisedDslId") or f"real_llm_{kind}_revision")
    metadata["id"] = f"{source_revised_id}_candidate_{uuid4().hex[:8]}"
    metadata["title"] = _append_once(str(metadata.get("title") or f"{kind} DSL"), "（待审核候选版）")
    promoted_dsl["status"] = "WAITING_REVIEW"
    validate_dsl(promoted_dsl, load_schema(kind, root))

    output_path = _resolve_path(output_path or Path(DEFAULT_PROMOTION_OUTPUT_PATH), root)
    report_output_path = _resolve_path(report_output_path or Path(DEFAULT_PROMOTION_REPORT_PATH), root)
    _write_json(output_path, promoted_dsl)

    safety = {
        "mode": "LOCAL_REAL_DSL_REVISION_PROMOTION",
        "realLlmCalled": False,
        "newLlmRequestSent": False,
        "secretsRead": False,
        "networkAccess": False,
        "taskCreated": False,
        "artifactCreated": True,
        "sourceDslModified": False,
        "revisedDslModified": False,
        "promotedCandidateWritten": True,
        "reviewRequired": True,
        "generatedStatus": "WAITING_REVIEW",
        "answerVisibleToCandidate": False,
        "gradingRefVisibleToCandidate": False,
        "autoApproveAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
    }
    report = {
        "component": "RealDslRevisionPromotion",
        "mode": "LOCAL_REAL_DSL_REVISION_PROMOTION",
        "sourceDecisionReportPath": _path_str(decision_report_path, root),
        "suggestionId": decision.get("suggestionId"),
        "kind": kind,
        "sourcePath": decision.get("sourcePath"),
        "revisedPath": decision.get("revisedPath"),
        "promotedPath": _path_str(output_path, root),
        "reportOutputPath": _path_str(report_output_path, root),
        "sourceDslId": decision.get("sourceDslId"),
        "revisedDslId": decision.get("revisedDslId"),
        "promotedDslId": metadata.get("id"),
        "promotedTitle": metadata.get("title"),
        "promotedStatus": promoted_dsl.get("status"),
        "reviewer": reviewer,
        "decisionReviewer": decision.get("reviewer"),
        "decisionStatus": decision.get("decisionStatus"),
        "changedFieldTotal": decision.get("changedFieldTotal", 0),
        "changedFields": _normalize_string_list(decision.get("changedFields")),
        "schemaValidated": True,
        "manualReviewRequired": True,
        "publishBlockedUntilApproved": True,
        "promotionStrategy": "copy_approved_revision_as_waiting_review_candidate",
        "nextRequiredAction": "manual_review_promoted_candidate_before_any_publish",
        "safety": safety,
    }
    if trace_id:
        report["traceId"] = trace_id
    _write_json(report_output_path, report)
    return {
        "realDslRevisionPromotion": report,
        "promotedDsl": promoted_dsl,
        "decisionReportPath": _path_str(decision_report_path, root),
        "outputPath": _path_str(output_path, root),
        "reportOutputPath": _path_str(report_output_path, root),
        "mode": report["mode"],
        "safety": safety,
    }


def _normalize_kind(kind: str) -> str:
    value = str(kind or "").strip().lower()
    if value not in SUPPORTED_KINDS:
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "真实 DSL 修订草稿不支持该 kind",
            [{"field": "kind", "reason": f"expected one of {sorted(SUPPORTED_KINDS)}"}],
        )
    return value


def _normalize_provider_mode(provider_mode: str) -> str:
    value = str(provider_mode or PROVIDER_MODE_LOCAL).strip().lower()
    if value not in SUPPORTED_PROVIDER_MODES:
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "真实 DSL 修订草稿不支持该 provider mode",
            [{"field": "providerMode", "reason": f"expected one of {sorted(SUPPORTED_PROVIDER_MODES)}"}],
        )
    return value


def _normalize_revision_decision(decision: str) -> str:
    value = str(decision or "").strip().lower()
    if value not in SUPPORTED_REVISION_DECISIONS:
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "真实 DSL 修订决策不支持该 decision",
            [{"field": "decision", "reason": f"expected one of {sorted(SUPPORTED_REVISION_DECISIONS)}"}],
        )
    return value


def _load_and_validate_source(kind: str, source_path: Path, *, root: Path) -> dict[str, Any]:
    if not source_path.exists() or not source_path.is_file():
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "真实 DSL 修订源文件不存在",
            [{"field": "source", "reason": "文件不存在"}],
        )
    try:
        dsl = load_yaml(source_path)
        validate_dsl(dsl, load_schema(kind, root))
    except DslValidationError as exc:
        raise RealDslRevisionError("SCHEMA_VALIDATION_ERROR", "真实 DSL 修订源文件未通过 Schema 校验", exc.errors) from exc
    if not isinstance(dsl, dict):
        raise RealDslRevisionError(
            "SCHEMA_VALIDATION_ERROR",
            "真实 DSL 修订源文件未通过 Schema 校验",
            [{"field": "$", "reason": "root must be object"}],
        )
    return dsl


def _load_revision_preview(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "审核预览文件不存在",
            [{"field": "preview", "reason": "文件不存在"}],
        )
    try:
        preview = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "审核预览 JSON 解析失败",
            [{"field": "preview", "reason": str(exc)}],
        ) from exc
    if not isinstance(preview, dict) or preview.get("component") != "RealDslReviewPreview":
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "审核预览格式错误",
            [{"field": "preview.component", "reason": "expected RealDslReviewPreview"}],
        )
    return preview


def _load_revision_batch_report(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "批量修订报告不存在",
            [{"field": "batchReport", "reason": "文件不存在"}],
        )
    try:
        batch = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "批量修订报告 JSON 解析失败",
            [{"field": "batchReport", "reason": str(exc)}],
        ) from exc
    if not isinstance(batch, dict) or batch.get("component") != "RealDslRevisionBatch":
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "批量修订报告格式错误",
            [{"field": "batchReport.component", "reason": "expected RealDslRevisionBatch"}],
        )
    return batch


def _load_revision_diff_preview(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "修订差异预览不存在",
            [{"field": "diffPreview", "reason": "文件不存在"}],
        )
    try:
        preview = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "修订差异预览 JSON 解析失败",
            [{"field": "diffPreview", "reason": str(exc)}],
        ) from exc
    if not isinstance(preview, dict) or preview.get("component") != "RealDslRevisionDiffPreview":
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "修订差异预览格式错误",
            [{"field": "diffPreview.component", "reason": "expected RealDslRevisionDiffPreview"}],
        )
    return preview


def _load_revision_decision_report(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "修订审核决策报告不存在",
            [{"field": "decisionReport", "reason": "文件不存在"}],
        )
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "修订审核决策报告 JSON 解析失败",
            [{"field": "decisionReport", "reason": str(exc)}],
        ) from exc
    if not isinstance(report, dict) or report.get("component") != "RealDslRevisionDecision":
        raise RealDslRevisionError(
            "VALIDATION_ERROR",
            "修订审核决策报告格式错误",
            [{"field": "decisionReport.component", "reason": "expected RealDslRevisionDecision"}],
        )
    return report


def _find_draft_diff(diff_preview: dict[str, Any], suggestion_id: str) -> dict[str, Any]:
    for draft in _list_of_objects(diff_preview.get("draftDiffs")):
        if str(draft.get("suggestionId") or "") == suggestion_id:
            return draft
    raise RealDslRevisionError(
        "NOT_FOUND",
        "未找到修订草稿差异",
        [{"field": "suggestionId", "reason": "未找到对应修订建议"}],
    )


def _apply_revision(
    kind: str,
    source_dsl: dict[str, Any],
    *,
    reviewer: str,
    comment: str,
    target_sections: list[str],
    requested_changes: list[str],
) -> tuple[dict[str, Any], list[str]]:
    revised = copy.deepcopy(source_dsl)
    changed_fields: list[str] = []
    metadata = _object(revised.setdefault("metadata", {}))
    original_id = str(metadata.get("id") or f"real_llm_{kind}")
    metadata["id"] = f"{original_id}_rev_{uuid4().hex[:8]}"
    metadata["title"] = _append_once(str(metadata.get("title") or f"{kind} DSL"), "（修订草稿）")
    revised["status"] = "WAITING_REVIEW"
    changed_fields.extend(["$.metadata.id", "$.metadata.title", "$.status"])

    note = _revision_note(reviewer=reviewer, comment=comment, target_sections=target_sections, requested_changes=requested_changes)
    if kind == "lab":
        changed_fields.extend(_revise_lab(revised, note))
    elif kind == "exam":
        changed_fields.extend(_revise_exam(revised, note))
    elif kind == "grading":
        changed_fields.extend(_revise_grading(revised, note))
    elif kind == "ppt":
        changed_fields.extend(_revise_ppt(revised, note))
    return revised, changed_fields


def _run_real_llm_revision(
    *,
    kind: str,
    source_path: Path,
    source_dsl: dict[str, Any],
    reviewer: str,
    comment: str,
    target_sections: list[str],
    requested_changes: list[str],
    model: str | None,
    base_url: str | None,
    timeout_seconds: int,
    max_output_tokens: int,
    explicit_real_call_opt_in: bool,
    confirm_waiting_review: bool,
    confirm_no_auto_publish: bool,
    root: Path,
    trace_id: str | None,
    client_factory: ClientFactory | None,
) -> dict[str, Any]:
    return run_real_llm_demo_dsl_generation(
        RealLlmDemoDslRequest(
            kind=kind,
            input_ref=str(_path_str(source_path, root)),
            input_payload={
                "revisionMode": REAL_LLM_REVISION_MODE,
                "instruction": (
                    "Revise the provided source DSL according to human review feedback. "
                    "Return exactly one complete DSL JSON object with the same kind. "
                    "Keep status WAITING_REVIEW and do not publish."
                ),
                "sourceDsl": source_dsl,
                "reviewFeedback": {
                    "reviewer": reviewer,
                    "comment": comment,
                    "targetSections": target_sections,
                    "requestedChanges": requested_changes,
                },
            },
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            explicit_real_call_opt_in=explicit_real_call_opt_in,
            confirm_waiting_review=confirm_waiting_review,
            confirm_no_auto_publish=confirm_no_auto_publish,
            trace_id=trace_id,
        ),
        root=root,
        client_factory=client_factory,
    )


def _changed_fields_from_revision(source_dsl: dict[str, Any], revised_dsl: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    _collect_changed_fields(source_dsl, revised_dsl, "$", changed)
    return changed or ["$"]


def _collect_changed_fields(source: Any, revised: Any, path: str, changed: list[str]) -> None:
    if isinstance(source, dict) and isinstance(revised, dict):
        for key in sorted(set(source) | set(revised)):
            _collect_changed_fields(source.get(key), revised.get(key), f"{path}.{key}", changed)
        return
    if isinstance(source, list) and isinstance(revised, list):
        max_len = max(len(source), len(revised))
        for index in range(max_len):
            source_item = source[index] if index < len(source) else None
            revised_item = revised[index] if index < len(revised) else None
            _collect_changed_fields(source_item, revised_item, f"{path}[{index}]", changed)
        return
    if source != revised:
        changed.append(path)


def _revise_lab(revised: dict[str, Any], note: str) -> list[str]:
    steps = _list_of_objects(_object(revised.get("spec")).get("steps"))
    if not steps:
        return []
    steps[0]["instruction"] = _append_paragraph(str(steps[0].get("instruction") or ""), note)
    return ["$.spec.steps[0].instruction"]


def _revise_exam(revised: dict[str, Any], note: str) -> list[str]:
    questions = _list_of_objects(_object(revised.get("spec")).get("questions"))
    if not questions:
        return []
    questions[0]["gradingRef"] = _append_paragraph(str(questions[0].get("gradingRef") or ""), note)
    return ["$.spec.questions[0].gradingRef"]


def _revise_grading(revised: dict[str, Any], note: str) -> list[str]:
    spec = _object(revised.get("spec"))
    assessment_plan = _list_of_objects(spec.get("assessmentPlan"))
    if assessment_plan:
        assessment_plan[0]["inputSummary"] = _append_paragraph(str(assessment_plan[0].get("inputSummary") or ""), note)
        return ["$.spec.assessmentPlan[0].inputSummary"]
    checks = _list_of_objects(spec.get("checks"))
    if checks:
        expected = checks[0].setdefault("expected", [])
        if isinstance(expected, list):
            expected.append(_take_text(note, 80))
            return ["$.spec.checks[0].expected"]
    return []


def _revise_ppt(revised: dict[str, Any], note: str) -> list[str]:
    slides = _list_of_objects(_object(revised.get("spec")).get("slides"))
    if not slides:
        return []
    target = next((slide for slide in slides if slide.get("type") in {"content", "summary"}), slides[0])
    bullets = target.setdefault("bullets", [])
    if isinstance(bullets, list):
        bullets.append(_take_text(note, 96))
        return ["$.spec.slides[].bullets"]
    target["subtitle"] = _append_paragraph(str(target.get("subtitle") or ""), _take_text(note, 120))
    return ["$.spec.slides[].subtitle"]


def _build_revision_report(
    *,
    kind: str,
    source_path: Path,
    output_path: Path,
    report_output_path: Path,
    reviewer: str,
    comment: str,
    target_sections: list[str],
    requested_changes: list[str],
    source_dsl: dict[str, Any],
    revised_dsl: dict[str, Any],
    changed_fields: list[str],
    provider_mode: str,
    provider_result: dict[str, Any] | None,
    trace_id: str | None,
) -> dict[str, Any]:
    real_llm_mode = provider_mode == PROVIDER_MODE_REAL_LLM
    mode = REAL_LLM_REVISION_MODE if real_llm_mode else "LOCAL_REAL_DSL_REVISION_DRAFT"
    report = {
        "component": "RealDslRevisionDraft",
        "mode": mode,
        "providerMode": provider_mode,
        "kind": kind,
        "sourcePath": _path_str(source_path, ROOT),
        "outputPath": _path_str(output_path, ROOT),
        "reportOutputPath": _path_str(report_output_path, ROOT),
        "sourceDslId": _object(source_dsl.get("metadata")).get("id"),
        "revisedDslId": _object(revised_dsl.get("metadata")).get("id"),
        "sourceStatus": source_dsl.get("status"),
        "revisedStatus": revised_dsl.get("status"),
        "reviewer": reviewer,
        "commentPreview": _take_text(comment, 180),
        "targetSections": target_sections,
        "requestedChanges": requested_changes,
        "changedFields": changed_fields,
        "schemaValidated": True,
        "manualReviewRequired": True,
        "publishBlockedUntilApproved": True,
        "revisionStrategy": "real_llm_rewrite_with_schema_validation" if real_llm_mode else "append_review_note_to_schema_allowed_field",
        "safety": {
            "mode": mode,
            "realLlmCalled": real_llm_mode,
            "newLlmRequestSent": real_llm_mode,
            "secretsRead": real_llm_mode,
            "networkAccess": real_llm_mode,
            "taskCreated": False,
            "artifactCreated": True,
            "reviewRequired": True,
            "generatedStatus": "WAITING_REVIEW",
            "answerVisibleToCandidate": False,
            "gradingRefVisibleToCandidate": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
        },
    }
    if provider_result is not None:
        report["provider"] = {
            "adapterId": "openai_responses_sdk_adapter",
            "interfaceName": "LLMProvider",
            "operation": "reviseDsl",
            "providerId": provider_result.get("providerId"),
            "mode": provider_result.get("mode"),
            "model": provider_result.get("model"),
            "baseUrlConfigured": provider_result.get("baseUrlConfigured"),
            "baseUrlSource": provider_result.get("baseUrlSource"),
            "apiSurface": provider_result.get("apiSurface"),
            "responseId": provider_result.get("responseId"),
            "usage": provider_result.get("usage"),
            "requestCount": provider_result.get("requestCount"),
            "secretValueReturned": provider_result.get("secretValueReturned"),
            "secretValueLogged": provider_result.get("secretValueLogged"),
        }
    if trace_id:
        report["traceId"] = trace_id
    return report


def _build_field_diff(field: str, *, source_dsl: dict[str, Any], revised_dsl: dict[str, Any]) -> dict[str, Any]:
    source_value, source_available = _value_at_path(source_dsl, field)
    revised_value, revised_available = _value_at_path(revised_dsl, field)
    return {
        "field": field,
        "sourceAvailable": source_available,
        "revisedAvailable": revised_available,
        "changed": source_value != revised_value if source_available and revised_available else True,
        "sourcePreview": _preview_value(source_value, available=source_available),
        "revisedPreview": _preview_value(revised_value, available=revised_available),
    }


def _value_at_path(value: Any, path: str) -> tuple[Any, bool]:
    tokens = _path_tokens(path)
    if tokens is None:
        return None, False
    return _apply_path_tokens(value, tokens)


def _path_tokens(path: str) -> list[tuple[str, Any]] | None:
    if path == "$":
        return []
    if not path.startswith("$"):
        return None
    index = 1
    tokens: list[tuple[str, Any]] = []
    while index < len(path):
        char = path[index]
        if char == ".":
            index += 1
            start = index
            while index < len(path) and path[index] not in ".[":
                index += 1
            key = path[start:index]
            if not key:
                return None
            tokens.append(("key", key))
            continue
        if char == "[":
            end = path.find("]", index)
            if end == -1:
                return None
            raw_index = path[index + 1 : end]
            if raw_index == "":
                tokens.append(("wildcard", None))
            else:
                try:
                    tokens.append(("index", int(raw_index)))
                except ValueError:
                    return None
            index = end + 1
            continue
        return None
    return tokens


def _apply_path_tokens(value: Any, tokens: list[tuple[str, Any]]) -> tuple[Any, bool]:
    if not tokens:
        return value, True
    token_type, token_value = tokens[0]
    remaining = tokens[1:]
    if token_type == "key":
        if not isinstance(value, dict) or token_value not in value:
            return None, False
        return _apply_path_tokens(value[token_value], remaining)
    if token_type == "index":
        if not isinstance(value, list) or token_value < 0 or token_value >= len(value):
            return None, False
        return _apply_path_tokens(value[token_value], remaining)
    if token_type == "wildcard":
        if not isinstance(value, list):
            return None, False
        extracted: list[Any] = []
        for item in value:
            item_value, available = _apply_path_tokens(item, remaining)
            if available:
                extracted.append(item_value)
        return extracted, bool(extracted)
    return None, False


def _preview_value(value: Any, *, available: bool, limit: int = 260) -> str:
    if not available:
        return "<unavailable>"
    if isinstance(value, str):
        return _take_text(value, limit)
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        return _take_text(text, limit)
    return _take_text(json.dumps(value, ensure_ascii=False), limit)


def _dsl_summary(kind: str, dsl: dict[str, Any]) -> dict[str, Any]:
    metadata = _object(dsl.get("metadata"))
    spec = _object(dsl.get("spec"))
    summary: dict[str, Any] = {
        "kind": kind,
        "id": metadata.get("id"),
        "title": metadata.get("title"),
        "status": dsl.get("status"),
    }
    if kind == "lab":
        summary["objectiveTotal"] = len(spec.get("objectives") if isinstance(spec.get("objectives"), list) else [])
        summary["stepTotal"] = len(spec.get("steps") if isinstance(spec.get("steps"), list) else [])
    elif kind == "exam":
        summary["questionTotal"] = len(spec.get("questions") if isinstance(spec.get("questions"), list) else [])
        summary["totalScore"] = spec.get("totalScore")
    elif kind == "grading":
        summary["checkTotal"] = len(spec.get("checks") if isinstance(spec.get("checks"), list) else [])
        summary["assessmentPlanTotal"] = len(spec.get("assessmentPlan") if isinstance(spec.get("assessmentPlan"), list) else [])
    elif kind == "ppt":
        summary["slideTotal"] = len(spec.get("slides") if isinstance(spec.get("slides"), list) else [])
    return summary


def _build_batch_revision_report(
    *,
    preview_path: Path,
    report_output_path: Path,
    reviewer: str,
    preview: dict[str, Any],
    drafts: list[dict[str, Any]],
    trace_id: str | None,
) -> dict[str, Any]:
    safety = {
        "mode": "LOCAL_REAL_DSL_REVISION_BATCH",
        "realLlmCalled": False,
        "newLlmRequestSent": False,
        "secretsRead": False,
        "networkAccess": False,
        "taskCreated": False,
        "artifactCreated": True,
        "reviewRequired": True,
        "generatedStatus": "WAITING_REVIEW",
        "answerVisibleToCandidate": False,
        "gradingRefVisibleToCandidate": False,
        "autoApproveAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
    }
    report = {
        "component": "RealDslRevisionBatch",
        "mode": "LOCAL_REAL_DSL_REVISION_BATCH",
        "sourcePreviewPath": _path_str(preview_path, ROOT),
        "reportOutputPath": _path_str(report_output_path, ROOT),
        "reviewer": reviewer,
        "sourceQualityStatus": _object(preview.get("summary")).get("qualityStatus"),
        "sourceQualityIssueTotal": _object(preview.get("summary")).get("qualityIssueTotal"),
        "suggestionTotal": len(_list_of_objects(preview.get("revisionSuggestions"))),
        "draftTotal": len(drafts),
        "draftKinds": sorted({draft["kind"] for draft in drafts}),
        "drafts": drafts,
        "schemaValidatedTotal": sum(1 for draft in drafts if draft.get("schemaValidated") is True),
        "allDraftsWaitingReview": all(draft.get("revisedStatus") == "WAITING_REVIEW" for draft in drafts),
        "manualReviewRequired": True,
        "publishBlockedUntilApproved": True,
        "safety": safety,
    }
    if trace_id:
        report["traceId"] = trace_id
    return report


def _revision_note(*, reviewer: str, comment: str, target_sections: list[str], requested_changes: list[str]) -> str:
    parts = [f"修订草稿说明：审核人 {reviewer} 要求调整：{comment}"]
    if target_sections:
        parts.append(f"目标部分：{', '.join(target_sections)}")
    if requested_changes:
        parts.append(f"请求变更：{'; '.join(requested_changes)}")
    parts.append("该内容仍为 WAITING_REVIEW，发布前必须人工复核。")
    return " ".join(parts)


def _normalize_string_list(value: list[str] | None) -> list[str]:
    if not value:
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_objects(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _append_once(value: str, suffix: str) -> str:
    return value if value.endswith(suffix) else f"{value}{suffix}"


def _append_paragraph(value: str, paragraph: str) -> str:
    return f"{value.rstrip()}\n\n{paragraph}".strip()


def _take_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _safe_file_part(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.strip().lower())
    text = "-".join(part for part in text.split("-") if part)
    return text or "revision"


def _resolve_path(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else root / path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _path_str(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)
