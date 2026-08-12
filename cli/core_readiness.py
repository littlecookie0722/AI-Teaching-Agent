"""Read-only core workflow readiness summary."""

from __future__ import annotations

from typing import Any

from .audit import OperationAction, OperationResourceType
from .agent_entity_readiness import agent_entities_for_task_type
from .review_detail import build_review_detail
from .store import JsonTaskStore


IMPORT_PREVIEW_TOOL_BY_ENTITY = {
    "lab_template": "create_lab_template_import_preview",
    "exam_question": "create_exam_question_import_preview",
    "grading_rule": "create_grading_rule_import_preview",
}

MOCK_IMPORT_TOOL_BY_ENTITY = {
    "lab_template": "create_lab_template_mock_import",
    "exam_question": "create_exam_question_mock_import",
    "grading_rule": "create_grading_rule_mock_import",
}

ENTITY_KIND_BY_PLATFORM_ENTITY = {
    "lab_template": "lab",
    "exam_question": "exam",
    "grading_rule": "grading",
}

DEFAULT_IMPORT_PREVIEW_OUTPUT_BY_ENTITY = {
    "lab_template": "examples/output/lab-template-import-preview.json",
    "exam_question": "examples/output/exam-question-import-preview.json",
    "grading_rule": "examples/output/grading-rule-import-preview.json",
}

DEFAULT_MOCK_IMPORT_OUTPUT_BY_ENTITY = {
    "lab_template": "examples/output/lab-template-mock-import.json",
    "exam_question": "examples/output/exam-question-mock-import.json",
    "grading_rule": "examples/output/grading-rule-mock-import.json",
}

DEFAULT_PLATFORM_ENTITY_SIGNOFF_OUTPUT = "examples/output/platform-entity-signoff-record.json"
DEFAULT_FINAL_PUBLISH_REVIEW_DECISION_OUTPUT = (
    "examples/output/platform-entity-final-publish-review-decision.json"
)
GRADING_REVIEW_TASK_TYPES = {"GRADING_GENERATION", "GRADING_GENERATION_REVISION"}


def _step(id_: str, label: str, ready: bool, source: str, next_action: str) -> dict[str, Any]:
    return {
        "id": id_,
        "label": label,
        "ready": ready,
        "source": source,
        "nextAction": "none" if ready else next_action,
    }


def _relevant_platform_items(readiness: dict[str, Any], task_type: str) -> list[dict[str, Any]]:
    items = readiness.get("items", []) if isinstance(readiness, dict) else []
    if not isinstance(items, list):
        return []
    relevant_entities = agent_entities_for_task_type(task_type)
    if relevant_entities is None:
        return []
    return [item for item in items if item.get("agentEntity") in relevant_entities]


def _platform_summary_for_task(readiness: dict[str, Any], task_type: str) -> dict[str, Any]:
    items = _relevant_platform_items(readiness, task_type)
    return {
        "requiredTotal": len(items),
        "previewCreatedTotal": sum(1 for item in items if item.get("previewCreated") is True),
        "mockImportCreatedTotal": sum(1 for item in items if item.get("mockImportCreated") is True),
        "dryRunPreparedTotal": sum(1 for item in items if item.get("dryRunPrepared") is True),
        "requestSentTotal": sum(1 for item in items if item.get("requestSent") is True),
        "statusQueriedTotal": sum(1 for item in items if item.get("statusQueried") is True),
        "resultRecordedTotal": sum(1 for item in items if item.get("resultRecorded") is True),
        "agentEntitySignoffRecordedTotal": sum(1 for item in items if item.get("signoffRecorded") is True),
        "finalPublishReviewDecisionRecordedTotal": sum(
            1
            for item in items
            if item.get("finalPublishReviewDecision", {}).get("recorded") is True
        ),
    }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _content_quality_readiness(detail: dict[str, Any]) -> dict[str, Any]:
    summary = detail.get("contentQualitySummary", {})
    summary = summary if isinstance(summary, dict) else {}
    available = summary.get("available") is True
    blocked_kinds = summary.get("blockedForImportPreviewKinds", [])
    blocked_kinds = blocked_kinds if isinstance(blocked_kinds, list) else []
    ready_kinds = summary.get("readyForImportPreviewKinds", [])
    ready_kinds = ready_kinds if isinstance(ready_kinds, list) else []
    decision_status = str(summary.get("decisionStatus") or ("AVAILABLE" if available else "NOT_AVAILABLE"))
    requires_revision = (
        summary.get("requiresRevisionBeforeImportPreview") is True
        or decision_status == "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW"
        or bool(blocked_kinds)
    )
    blocking_issue_total = _safe_int(summary.get("blockingIssueTotal"))
    warning_issue_total = _safe_int(summary.get("warningIssueTotal"))
    return {
        "component": "CoreContentQualityReadiness",
        "source": "reviewDetail.contentQualitySummary",
        "available": available,
        "readyForImportPreview": True if not available else not requires_revision,
        "decisionStatus": decision_status,
        "recommendedAction": str(summary.get("recommendedAction") or "none"),
        "requiresRevisionBeforeImportPreview": requires_revision if available else False,
        "requiresEvidenceBeforeFinalApproval": bool(summary.get("requiresEvidenceBeforeFinalApproval"))
        if available
        else False,
        "readyForImportPreviewKinds": [str(item) for item in ready_kinds],
        "blockedForImportPreviewKinds": [str(item) for item in blocked_kinds],
        "blockingIssueTotal": blocking_issue_total,
        "warningIssueTotal": warning_issue_total,
        "manualReviewRequired": True if available else False,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
        "nextAction": "request_content_revision_before_import_preview" if requires_revision else "none",
    }


def _content_quality_step(readiness: dict[str, Any]) -> dict[str, Any] | None:
    if readiness.get("available") is not True:
        return None
    step = _step(
        "content_quality_ready_for_import_preview",
        "内容质量允许进入导入预览",
        readiness.get("readyForImportPreview") is True,
        "reviewDetail.contentQualitySummary",
        "request_content_revision_before_import_preview",
    )
    step["contentQuality"] = {
        "decisionStatus": readiness.get("decisionStatus"),
        "recommendedAction": readiness.get("recommendedAction"),
        "blockedForImportPreviewKinds": readiness.get("blockedForImportPreviewKinds", []),
        "blockingIssueTotal": readiness.get("blockingIssueTotal", 0),
        "warningIssueTotal": readiness.get("warningIssueTotal", 0),
    }
    return step


def _revision_loop_state(store: JsonTaskStore, task_id: str) -> dict[str, Any]:
    revision_events = store.list_operation_audit_events(
        resource_type=OperationResourceType.AI_TASK.value,
        resource_id=task_id,
        action=OperationAction.REVIEW_REVISION_REQUEST.value,
    )
    latest_revision = revision_events[0].to_dict() if revision_events else None
    regeneration_events = store.list_operation_audit_events(
        action=OperationAction.REVIEW_MOCK_REGENERATE.value,
    )
    matched_regenerations = []
    for event in regeneration_events:
        payload = event.to_dict()
        detail = payload.get("detail") if isinstance(payload.get("detail"), dict) else {}
        if detail.get("sourceTaskId") == task_id:
            matched_regenerations.append(payload)
    latest_regeneration = matched_regenerations[0] if matched_regenerations else None
    latest_revision_detail = latest_revision.get("detail", {}) if isinstance(latest_revision, dict) else {}
    latest_regeneration_detail = latest_regeneration.get("detail", {}) if isinstance(latest_regeneration, dict) else {}
    return {
        "component": "CoreRevisionLoopState",
        "source": "operationAuditEvents.REVIEW_REVISION_REQUEST + REVIEW_MOCK_REGENERATE",
        "revisionRequestTotal": len(revision_events),
        "latestRevisionRequestId": latest_revision.get("id") if isinstance(latest_revision, dict) else None,
        "latestRevisionPriority": latest_revision_detail.get("priority"),
        "latestRevisionComment": latest_revision_detail.get("comment"),
        "mockRegenerationTotal": len(matched_regenerations),
        "latestMockRegenerationId": latest_regeneration.get("id") if isinstance(latest_regeneration, dict) else None,
        "latestMockRevisionTaskId": latest_regeneration_detail.get("newTaskId"),
        "latestMockRevisionArtifactId": latest_regeneration_detail.get("artifactId"),
        "latestMockRevisionOutputPath": latest_regeneration_detail.get("outputPath"),
        "revisionRequestPendingRegeneration": bool(revision_events) and not bool(matched_regenerations),
        "mockRevisionAlreadyGenerated": bool(matched_regenerations),
        "newLlmRequestSent": False,
        "realLlmCalled": False,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def _platform_import_preview_action_summary(
    actions: dict[str, Any],
    *,
    relevant_agent_entities: set[str] | None = None,
) -> dict[str, Any]:
    items = actions.get("items", []) if isinstance(actions, dict) else []
    items = items if isinstance(items, list) else []
    if relevant_agent_entities is not None:
        items = [item for item in items if str(item.get("agentEntity") or "") in relevant_agent_entities]
    pending_items = [item for item in items if item.get("previewAlreadyCreated") is not True]
    return {
        "component": "PlatformImportPreviewActionSummary",
        "source": "reviewDetail.platformImportPreviewActions",
        "available": bool(actions.get("visible")) if isinstance(actions, dict) else False,
        "total": len(items),
        "enabledTotal": sum(1 for item in items if item.get("enabled") is True),
        "previewAlreadyCreatedTotal": sum(1 for item in items if item.get("previewAlreadyCreated") is True),
        "pendingPreviewTotal": len(pending_items),
        "pendingPlatformEntities": [
            str(item.get("agentEntity")) for item in pending_items if item.get("agentEntity")
        ],
        "pendingPreviewComponents": [
            str(item.get("previewComponent")) for item in pending_items if item.get("previewComponent")
        ],
        "pendingCliCommands": [str(item.get("cliCommand")) for item in pending_items if item.get("cliCommand")],
        "pendingNextRequiredActions": [
            str(item.get("nextRequiredAction")) for item in pending_items if item.get("nextRequiredAction")
        ],
        "contentQualityAvailable": bool(actions.get("contentQualityAvailable")) if isinstance(actions, dict) else False,
        "contentQualityReadyTotal": sum(1 for item in items if item.get("contentQualityReadyForImportPreview") is True),
        "contentQualityBlockedTotal": sum(
            1
            for item in items
            if item.get("contentQualityAvailable") is True
            and item.get("contentQualityReadyForImportPreview") is not True
        ),
        "contentQualityReadyForImportPreviewKinds": actions.get("contentQualityReadyForImportPreviewKinds", [])
        if isinstance(actions, dict)
        else [],
        "contentQualityBlockedForImportPreviewKinds": actions.get("contentQualityBlockedForImportPreviewKinds", [])
        if isinstance(actions, dict)
        else [],
        "approvalStillRequired": bool(actions.get("approvalStillRequired", True)) if isinstance(actions, dict) else True,
        "autoApproveAllowed": False,
        "realPublishAllowed": False,
    }


def _platform_steps(
    platform_summary: dict[str, Any],
    platform_import_action_summary: dict[str, Any] | None = None,
    *,
    include_future_platform_steps: bool = False,
) -> list[dict[str, Any]]:
    summary = platform_summary
    required_total = int(summary.get("requiredTotal") or 0)
    if required_total == 0:
        return []
    import_preview_step = _step(
        "platform_import_preview_created",
        "平台导入预览已生成",
        required_total > 0 and summary.get("previewCreatedTotal") == required_total,
        "reviewDetail.agentEntityReadinessReport.summary.previewCreatedTotal",
        "create_platform_import_preview",
    )
    if platform_import_action_summary:
        import_preview_step["actionSummary"] = {
            "source": platform_import_action_summary["source"],
            "pendingPreviewTotal": platform_import_action_summary["pendingPreviewTotal"],
            "pendingPlatformEntities": platform_import_action_summary["pendingPlatformEntities"],
            "pendingPreviewComponents": platform_import_action_summary["pendingPreviewComponents"],
            "pendingCliCommands": platform_import_action_summary["pendingCliCommands"],
            "contentQualityReadyTotal": platform_import_action_summary["contentQualityReadyTotal"],
            "contentQualityBlockedTotal": platform_import_action_summary["contentQualityBlockedTotal"],
        }
    steps = [
        import_preview_step,
        _step(
            "platform_mock_import_created",
            "本地平台实体草稿已生成",
            required_total > 0 and summary.get("mockImportCreatedTotal") == required_total,
            "reviewDetail.agentEntityReadinessReport.summary.mockImportCreatedTotal",
            "create_agent_entity_mock_import",
        ),
        _step(
            "platform_dry_run_prepared",
            "本地平台导入 dry-run DTO 已准备",
            required_total > 0 and summary.get("dryRunPreparedTotal") == required_total,
            "reviewDetail.agentEntityReadinessReport.summary.dryRunPreparedTotal",
            "run_agent_entity_import_dry_run",
        ),
    ]
    if not include_future_platform_steps:
        return steps
    steps.extend(
        [
            _step(
                "platform_import_request_sent",
                "平台 draft import 请求已发送",
                required_total > 0 and summary.get("requestSentTotal") == required_total,
                "reviewDetail.agentEntityReadinessReport.summary.requestSentTotal",
                "agent_internal_publish_request_after_manual_review",
            ),
            _step(
                "platform_status_and_result_recorded",
                "平台状态已查询且结果已人工登记",
                required_total > 0
                and summary.get("statusQueriedTotal") == required_total
                and summary.get("resultRecordedTotal") == required_total,
                "reviewDetail.agentEntityReadinessReport.summary.statusQueriedTotal+resultRecordedTotal",
                "query_platform_status_and_record_import_result",
            ),
            _step(
                "agent_entity_signoff_recorded",
                "本地平台实体人工签收已记录",
                required_total > 0 and summary.get("agentEntitySignoffRecordedTotal") == required_total,
                "reviewDetail.agentEntityReadinessReport.summary.agentEntitySignoffRecordedTotal",
                "record_agent_entity_signoff",
            ),
            _step(
                "final_publish_review_decision_recorded",
                "最终人工复核结论已记录",
                required_total > 0 and summary.get("finalPublishReviewDecisionRecordedTotal") == required_total,
                "reviewDetail.agentEntityReadinessReport.summary.finalPublishReviewDecisionRecordedTotal",
                "record_final_human_publish_review_decision",
            ),
        ]
    )
    return steps


def _grading_steps(pre_approve: dict[str, Any]) -> list[dict[str, Any]]:
    summary = pre_approve.get("summary", {}) if isinstance(pre_approve, dict) else {}
    decision_note_recommendation = summary.get("decisionNoteRecommendation")
    next_decision_note_action = summary.get("nextDecisionNoteAction")
    if decision_note_recommendation == "approve-ready":
        decision_note_next_action = "record_approve_ready_review_decision_note"
    elif decision_note_recommendation == "needs-revision":
        decision_note_next_action = "record_needs_revision_decision_note_or_request_revision"
    elif decision_note_recommendation == "needs-evidence":
        decision_note_next_action = "collect_or_review_grading_evidence_before_decision_note"
    else:
        decision_note_next_action = str(next_decision_note_action or "record_review_decision_note")
    return [
        _step(
            "grading_evidence_ready",
            "评分证据已准备",
            summary.get("evidenceReady") is True,
            "reviewDetail.preApproveReviewCheck.summary.evidenceReady",
            "run_grading_evidence_auto_and_review_report",
        ),
        _step(
            "grading_review_decision_note_recorded",
            "评分审核 decision note 已记录",
            summary.get("reviewDecisionNoteRecorded") is True,
            "reviewDetail.preApproveReviewCheck.summary.reviewDecisionNoteRecorded",
            decision_note_next_action,
        ),
        _step(
            "grading_decision_approve_ready",
            "评分审核结论为 approve-ready",
            summary.get("approveReadyDecision") is True,
            "reviewDetail.preApproveReviewCheck.summary.approveReadyDecision",
            decision_note_next_action,
        ),
    ]


def _grading_record_review_step(grading_records: dict[str, Any]) -> dict[str, Any]:
    review_integration = (
        grading_records.get("reviewIntegration")
        if isinstance(grading_records.get("reviewIntegration"), dict)
        else {}
    )
    latest_record_id = review_integration.get("latestRecordId")
    step = _step(
        "grading_record_human_review_approved",
        "评分记录已人工复核通过",
        review_integration.get("readyForAgentReview") is True,
        "reviewDetail.gradingRecords.reviewIntegration.readyForAgentReview",
        str(review_integration.get("nextRequiredAction") or "review_latest_grading_record_for_platform_review"),
    )
    step["gradingRecordReview"] = {
        "state": review_integration.get("state"),
        "latestRecordId": latest_record_id,
        "latestStatus": review_integration.get("latestStatus"),
        "latestDecision": review_integration.get("latestDecision"),
        "latestReviewedBy": review_integration.get("latestReviewedBy"),
        "latestReviewedAt": review_integration.get("latestReviewedAt"),
        "blockingReasons": review_integration.get("blockingReasons", []),
        "humanReviewRecordedTotal": review_integration.get("humanReviewRecordedTotal", 0),
    }
    return step


def _recommended_next_action(steps: list[dict[str, Any]], *, include_future_platform_steps: bool = False) -> str:
    for item in steps:
        if item["ready"] is not True:
            return str(item["nextAction"])
    return (
        "ready_for_final_manual_review_or_publish_planning"
        if include_future_platform_steps
        else "LOCAL_CORE_MVP_STOP_LINE_REACHED"
    )


def _final_review_state(
    *,
    grading_applicable: bool,
    pre_approve_summary: dict[str, Any],
    blocked_steps: list[dict[str, Any]],
) -> str:
    if not grading_applicable:
        return "NOT_GRADING_REVIEW"
    latest_decision = pre_approve_summary.get("latestDecision")
    if pre_approve_summary.get("approveReadyDecision") is True:
        return "READY_FOR_HUMAN_APPROVE"
    if latest_decision == "needs-revision":
        return "NEEDS_REVISION"
    if (
        latest_decision == "needs-evidence"
        or pre_approve_summary.get("scorePreviewReadyForDecisionNote") is False
        or pre_approve_summary.get("decisionNoteRecommendation") == "needs-evidence"
    ):
        return "NEEDS_MORE_EVIDENCE"
    if pre_approve_summary.get("evidenceReady") is True and pre_approve_summary.get("reviewDecisionNoteRecorded") is not True:
        return "WAITING_DECISION_NOTE"
    if any(str(step.get("id") or "") == "grading_evidence_ready" for step in blocked_steps):
        return "WAITING_EVIDENCE"
    return "WAITING_REVIEW_INPUTS"


def _first_platform_item_matching(items: list[dict[str, Any]], **expected: bool) -> dict[str, Any] | None:
    for item in items:
        if all(item.get(key) is value for key, value in expected.items()):
            return item
    return None


def _first_platform_item_missing_final_review(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in items:
        final_decision = item.get("finalPublishReviewDecision")
        final_decision = final_decision if isinstance(final_decision, dict) else {}
        if item.get("signoffRecorded") is True and final_decision.get("recorded") is not True:
            return item
    return None


def _manual_recommendation(
    *,
    reason_code: str,
    action_type: str,
    recommended_next_action: str,
    cli_command: str | None = None,
    final_review_state: str | None = None,
) -> dict[str, Any]:
    recommendation = {
        "component": "CoreWorkflowNextToolRecommendation",
        "mode": "READ_ONLY_TOOL_SELECTION_ADVICE",
        "reasonCode": reason_code,
        "actionType": action_type,
        "recommendedNextAction": recommended_next_action,
        "finalReviewState": final_review_state,
        "toolName": None,
        "toolAvailable": False,
        "manualReviewRequired": True,
        "autoExecuteAllowed": False,
        "autoApproveAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "notes": [
            "This recommendation is advisory only.",
            "Callers must not execute the suggested action without an explicit human step.",
        ],
    }
    if cli_command:
        recommendation["cliCommand"] = cli_command
    return recommendation


def _mcp_tool_recommendation(
    *,
    reason_code: str,
    recommended_next_action: str,
    tool_name: str,
    arguments_preview: dict[str, Any] | None = None,
    argument_hints: list[dict[str, Any]] | None = None,
    review_required: bool = True,
    real_platform_call: bool = False,
    final_review_state: str | None = None,
) -> dict[str, Any]:
    recommendation = {
        "component": "CoreWorkflowNextToolRecommendation",
        "mode": "READ_ONLY_TOOL_SELECTION_ADVICE",
        "reasonCode": reason_code,
        "actionType": "mcp_tool",
        "recommendedNextAction": recommended_next_action,
        "finalReviewState": final_review_state,
        "toolName": tool_name,
        "toolAvailable": True,
        "reviewRequired": review_required,
        "manualReviewRequired": True,
        "autoExecuteAllowed": False,
        "autoApproveAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "realPlatformCall": real_platform_call,
        "notes": [
            "This recommendation is advisory only.",
            "The readiness report does not call tools or mutate state.",
        ],
    }
    if arguments_preview:
        recommendation["argumentsPreview"] = arguments_preview
    if argument_hints:
        recommendation["argumentHints"] = argument_hints
    return recommendation


def _next_tool_recommendation(
    *,
    task_id: str,
    recommended_next_action: str,
    blocked_steps: list[dict[str, Any]],
    platform_import_action_summary: dict[str, Any],
    platform_items: list[dict[str, Any]],
    content_quality_readiness: dict[str, Any],
    revision_loop_state: dict[str, Any],
    pre_approve_summary: dict[str, Any] | None = None,
    grading_record_review: dict[str, Any] | None = None,
    final_review_state: str | None = None,
    include_future_platform_steps: bool = False,
) -> dict[str, Any]:
    pre_approve_summary = pre_approve_summary or {}
    grading_record_review = grading_record_review or {}
    if not blocked_steps:
        return _manual_recommendation(
            reason_code=("CORE_WORKFLOW_READY" if include_future_platform_steps else "LOCAL_CORE_MVP_STOP_LINE_REACHED"),
            action_type=("manual_final_review" if include_future_platform_steps else "local_core_stop"),
            recommended_next_action=recommended_next_action,
            final_review_state=final_review_state,
            cli_command=(
                "python lab_cli.py platform-entity final-publish-review-decision "
                "--id <agent_entity_id> --reviewer <reviewer> --decision APPROVED_FOR_PUBLISH_PLANNING "
                "--output examples/output/final-publish-review-decision.json "
                "--confirm-no-auto-publish --confirm-no-real-publish --confirm-final-human-review"
                if include_future_platform_steps
                else None
            ),
        )

    blocked_step_id = str(blocked_steps[0].get("id") or "")
    if blocked_step_id == "content_quality_ready_for_import_preview":
        if revision_loop_state.get("revisionRequestPendingRegeneration") is True:
            recommendation = _mcp_tool_recommendation(
                reason_code="CONTENT_QUALITY_REVISION_REGENERATION_PENDING",
                recommended_next_action="regenerate_from_latest_review_revision_request",
                tool_name="regenerate_from_revision_mock",
                final_review_state=final_review_state,
                arguments_preview={
                    "taskId": task_id,
                    "reviewer": "<reviewer>",
                    "revisionRequestId": revision_loop_state.get("latestRevisionRequestId"),
                    "output": f"examples/output/{task_id}-content-quality-revision.json",
                },
            )
            recommendation["revisionLoopState"] = revision_loop_state
            recommendation["contentQualityReadiness"] = {
                "available": content_quality_readiness.get("available"),
                "readyForImportPreview": content_quality_readiness.get("readyForImportPreview"),
                "decisionStatus": content_quality_readiness.get("decisionStatus"),
                "blockedForImportPreviewKinds": content_quality_readiness.get("blockedForImportPreviewKinds", []),
            }
            return recommendation
        if revision_loop_state.get("mockRevisionAlreadyGenerated") is True:
            recommendation = _manual_recommendation(
                reason_code="CONTENT_QUALITY_REVISION_REVIEW_PENDING",
                action_type="manual_review_revised_task",
                recommended_next_action="review_generated_revision_task_before_import_preview",
                final_review_state=final_review_state,
                cli_command=(
                    "python lab_cli.py review detail --task-id "
                    f"{revision_loop_state.get('latestMockRevisionTaskId') or '<revision_task_id>'}"
                ),
            )
            recommendation["revisionLoopState"] = revision_loop_state
            recommendation["contentQualityReadiness"] = {
                "available": content_quality_readiness.get("available"),
                "readyForImportPreview": content_quality_readiness.get("readyForImportPreview"),
                "decisionStatus": content_quality_readiness.get("decisionStatus"),
                "blockedForImportPreviewKinds": content_quality_readiness.get("blockedForImportPreviewKinds", []),
            }
            return recommendation
        recommendation = _manual_recommendation(
            reason_code="CONTENT_QUALITY_REVISION_REQUIRED",
            action_type="manual_revision_request",
            recommended_next_action=recommended_next_action,
            final_review_state=final_review_state,
            cli_command=(
                f"python lab_cli.py review revision-request --task-id {task_id} --reviewer <reviewer> "
                "--comment <content_quality_revision_comment> --priority HIGH"
            ),
        )
        recommendation["contentQualityReadiness"] = {
            "available": content_quality_readiness.get("available"),
            "readyForImportPreview": content_quality_readiness.get("readyForImportPreview"),
            "decisionStatus": content_quality_readiness.get("decisionStatus"),
            "recommendedAction": content_quality_readiness.get("recommendedAction"),
            "requiresRevisionBeforeImportPreview": content_quality_readiness.get(
                "requiresRevisionBeforeImportPreview"
            ),
            "blockedForImportPreviewKinds": content_quality_readiness.get("blockedForImportPreviewKinds", []),
            "blockingIssueTotal": content_quality_readiness.get("blockingIssueTotal", 0),
            "warningIssueTotal": content_quality_readiness.get("warningIssueTotal", 0),
        }
        recommendation["revisionLoopState"] = revision_loop_state
        return recommendation

    if blocked_step_id == "generated_content_human_approved":
        return _manual_recommendation(
            reason_code="HUMAN_APPROVAL_REQUIRED",
            action_type="manual_review",
            recommended_next_action=recommended_next_action,
            final_review_state=final_review_state,
            cli_command=f"python lab_cli.py review approve --task-id {task_id} --reviewer <reviewer>",
        )

    if blocked_step_id == "grading_evidence_ready":
        return _mcp_tool_recommendation(
            reason_code="GRADING_EVIDENCE_REQUIRED",
            recommended_next_action=recommended_next_action,
            tool_name="run_grading_evidence_auto",
            final_review_state=final_review_state,
            arguments_preview={
                "taskId": task_id,
                "output": "examples/output/grading-evidence-auto.json",
            },
            argument_hints=[
                {
                    "name": "grading",
                    "required": True,
                    "source": "approved Grading DSL path from review detail or workflow output",
                },
                {
                    "name": "submission",
                    "required": True,
                    "source": "candidate submission directory selected by reviewer",
                },
            ],
        )

    if blocked_step_id in {"grading_review_decision_note_recorded", "grading_decision_approve_ready"}:
        if recommended_next_action == "collect_or_review_grading_evidence_before_decision_note":
            return _mcp_tool_recommendation(
                reason_code="GRADING_ADDITIONAL_EVIDENCE_RECOMMENDED",
                recommended_next_action=recommended_next_action,
                tool_name="run_grading_evidence_auto",
                final_review_state=final_review_state,
                arguments_preview={
                    "taskId": task_id,
                    "includeControlledCommand": True,
                    "output": "examples/output/grading-evidence-auto.json",
                },
                argument_hints=[
                    {
                        "name": "grading",
                        "required": True,
                        "source": "approved Grading DSL path from review detail or workflow output",
                    },
                    {
                        "name": "submission",
                        "required": True,
                        "source": "candidate submission directory selected by reviewer",
                    },
                ],
            )
        decision = str(pre_approve_summary.get("decisionNoteRecommendation") or "approve-ready")
        if decision not in {"approve-ready", "needs-revision", "needs-evidence"}:
            decision = "approve-ready"
        reason = str(
            pre_approve_summary.get("decisionNoteRecommendationReason")
            or "Grading evidence is fully covered and ready for human approve-ready decision note."
        )
        return _mcp_tool_recommendation(
            reason_code="GRADING_DECISION_NOTE_REQUIRED",
            recommended_next_action=recommended_next_action,
            tool_name="record_review_decision_note",
            final_review_state=final_review_state,
            arguments_preview={
                "taskId": task_id,
                "reviewer": "<reviewer>",
                "decision": decision,
                "reason": reason,
                "output": "examples/output/review-decision-note.json",
            },
            argument_hints=[
                {
                    "name": "decision",
                    "required": True,
                    "source": "preApproveReviewCheck.summary.decisionNoteRecommendation",
                },
                {
                    "name": "reason",
                    "required": False,
                    "source": "human reviewer may override or expand the suggested reason before execution",
                },
            ],
        )

    if blocked_step_id == "grading_record_human_review_approved":
        latest_record_id = str(grading_record_review.get("latestRecordId") or "")
        state = str(grading_record_review.get("state") or "")
        if state == "NO_GRADING_RECORD" or not latest_record_id:
            return _manual_recommendation(
                reason_code="GRADING_RECORD_REQUIRED",
                action_type="manual_grading_record_create",
                recommended_next_action=recommended_next_action,
                final_review_state=final_review_state,
                cli_command=(
                    f"python lab_cli.py grade record-create --task-id {task_id} "
                    "--report <latest_reviewed_grading_evidence_report_path> "
                    "--submission-id <submission_id> --reviewer <reviewer>"
                ),
            )
        return _manual_recommendation(
            reason_code="GRADING_RECORD_REVIEW_REQUIRED",
            action_type="manual_grading_record_review",
            recommended_next_action=recommended_next_action,
            final_review_state=final_review_state,
            cli_command=(
                f"python lab_cli.py grade record-review --id {latest_record_id} "
                "--reviewer <reviewer> --decision approve-ready"
            ),
        )

    if blocked_step_id == "platform_import_preview_created":
        entities = platform_import_action_summary.get("pendingPlatformEntities", [])
        entity = str(entities[0]) if isinstance(entities, list) and entities else ""
        tool_name = IMPORT_PREVIEW_TOOL_BY_ENTITY.get(entity)
        if tool_name:
            return _mcp_tool_recommendation(
                reason_code="PLATFORM_IMPORT_PREVIEW_PENDING",
                recommended_next_action=recommended_next_action,
                tool_name=tool_name,
                final_review_state=final_review_state,
                arguments_preview={
                    "taskId": task_id,
                    "reviewer": "<reviewer>",
                    "output": DEFAULT_IMPORT_PREVIEW_OUTPUT_BY_ENTITY.get(
                        entity, "examples/output/platform-import-preview.json"
                    ),
                },
            )

    if blocked_step_id == "platform_mock_import_created":
        item = _first_platform_item_matching(platform_items, previewCreated=True, mockImportCreated=False)
        entity = str(item.get("agentEntity") or "") if item else ""
        tool_name = MOCK_IMPORT_TOOL_BY_ENTITY.get(entity)
        if tool_name:
            return _mcp_tool_recommendation(
                reason_code="PLATFORM_MOCK_IMPORT_PENDING",
                recommended_next_action=recommended_next_action,
                tool_name=tool_name,
                final_review_state=final_review_state,
                arguments_preview={
                    "taskId": task_id,
                    "reviewer": "<reviewer>",
                    "output": DEFAULT_MOCK_IMPORT_OUTPUT_BY_ENTITY.get(
                        entity, "examples/output/platform-entity-mock-import.json"
                    ),
                },
            )

    if blocked_step_id == "platform_dry_run_prepared":
        item = _first_platform_item_matching(platform_items, mockImportCreated=True, dryRunPrepared=False)
        entity_id = str(item.get("agentEntityId") or "") if item else ""
        return _mcp_tool_recommendation(
            reason_code="PLATFORM_IMPORT_DRY_RUN_PENDING",
            recommended_next_action=recommended_next_action,
            tool_name="create_agent_entity_import_dry_run",
            final_review_state=final_review_state,
            arguments_preview={
                "id": entity_id or "<agent_entity_id>",
                "reviewer": "<reviewer>",
                "output": "examples/output/platform-entity-import-dry-run.json",
            },
        )

    if blocked_step_id == "platform_import_request_sent":
        item = _first_platform_item_matching(platform_items, dryRunPrepared=True, requestSent=False)
        entity_id = str(item.get("agentEntityId") or "") if item else ""
        return _mcp_tool_recommendation(
            reason_code="PLATFORM_IMPORT_REQUEST_PENDING",
            recommended_next_action=recommended_next_action,
            tool_name="agent_internal_publish_request",
            final_review_state=final_review_state,
            arguments_preview={
                "id": entity_id or "<agent_entity_id>",
                "reviewer": "<reviewer>",
                "dryRun": "<reviewed_dry_run_report_path>",
                "baseUrl": "<platform_api_base_url>",
                "output": "examples/output/platform-entity-import-send-report.json",
                "explicitPlatformCallOptIn": True,
                "confirmDryRunReviewed": True,
                "confirmManualPlatformReview": True,
                "confirmNoAutoPublish": True,
            },
            argument_hints=[
                {"name": "dryRun", "required": True, "source": "reviewed local dry-run report path"},
                {"name": "baseUrl", "required": True, "source": "reviewer-provided platform API base URL"},
                {"name": "output", "required": True, "source": "local send report output path"},
            ],
            real_platform_call=True,
        )

    if blocked_step_id == "platform_status_and_result_recorded":
        status_item = _first_platform_item_matching(platform_items, requestSent=True, statusQueried=False)
        result_item = _first_platform_item_matching(platform_items, statusQueried=True, resultRecorded=False)
        if status_item:
            return _mcp_tool_recommendation(
                reason_code="PLATFORM_IMPORT_STATUS_QUERY_PENDING",
                recommended_next_action=recommended_next_action,
                tool_name="query_agent_publish_status",
                final_review_state=final_review_state,
                arguments_preview={
                    "id": str(status_item.get("agentEntityId") or "<agent_entity_id>"),
                    "reviewer": "<reviewer>",
                    "sendResult": "<reviewed_import_send_report_path>",
                    "baseUrl": "<platform_api_base_url>",
                    "output": "examples/output/platform-entity-import-status-query.json",
                    "explicitPlatformQueryOptIn": True,
                },
                argument_hints=[
                    {"name": "sendResult", "required": True, "source": "reviewed import send report path"},
                    {"name": "baseUrl", "required": True, "source": "reviewer-provided platform API base URL"},
                    {"name": "output", "required": True, "source": "local status report output path"},
                ],
                real_platform_call=True,
            )
        if result_item:
            return _mcp_tool_recommendation(
                reason_code="PLATFORM_IMPORT_RESULT_RECORD_PENDING",
                recommended_next_action=recommended_next_action,
                tool_name="record_agent_entity_publish_result",
                final_review_state=final_review_state,
                arguments_preview={
                    "id": str(result_item.get("agentEntityId") or "<agent_entity_id>"),
                    "reviewer": "<reviewer>",
                    "sendResult": "<reviewed_import_send_report_path>",
                    "agentStatus": "ACCEPTED_FOR_DRAFT",
                    "output": "examples/output/platform-entity-import-result-record.json",
                },
                argument_hints=[
                    {"name": "sendResult", "required": True, "source": "reviewed import send report path"},
                    {"name": "agentStatus", "required": True, "source": "human-reviewed platform draft status"},
                    {"name": "output", "required": True, "source": "local result record output path"},
                ],
            )

    if blocked_step_id == "agent_entity_signoff_recorded":
        item = _first_platform_item_matching(platform_items, signoffRecorded=False)
        entity_id = str(item.get("agentEntityId") or "") if item else ""
        return _mcp_tool_recommendation(
            reason_code="PLATFORM_ENTITY_SIGNOFF_REQUIRED",
            recommended_next_action=recommended_next_action,
            tool_name="record_agent_entity_signoff",
            final_review_state=final_review_state,
            arguments_preview={
                "id": entity_id or "<agent_entity_id>",
                "reviewer": "<reviewer>",
                "output": DEFAULT_PLATFORM_ENTITY_SIGNOFF_OUTPUT,
            },
        )

    if blocked_step_id == "final_publish_review_decision_recorded":
        item = _first_platform_item_missing_final_review(platform_items)
        entity_id = str(item.get("agentEntityId") or "") if item else ""
        return _mcp_tool_recommendation(
            reason_code="FINAL_HUMAN_REVIEW_DECISION_REQUIRED",
            recommended_next_action=recommended_next_action,
            tool_name="record_final_publish_review_decision",
            final_review_state=final_review_state,
            arguments_preview={
                "id": entity_id or "<agent_entity_id>",
                "reviewer": "<reviewer>",
                "decision": "APPROVED_FOR_PUBLISH_PLANNING",
                "output": DEFAULT_FINAL_PUBLISH_REVIEW_DECISION_OUTPUT,
                "confirmNoAutoPublish": True,
                "confirmNoRealPublish": True,
                "confirmFinalHumanReview": True,
            },
        )

    return _manual_recommendation(
        reason_code="NO_AUTOMATED_TOOL_RECOMMENDATION",
        action_type="manual_triage",
        recommended_next_action=recommended_next_action,
        final_review_state=final_review_state,
    )


def build_core_readiness_report(
    store: JsonTaskStore,
    task_id: str,
    *,
    platform_readiness_override: dict[str, Any] | None = None,
    include_future_platform_steps: bool = False,
) -> dict[str, Any] | None:
    detail = build_review_detail(store, task_id)
    if detail is None:
        return None

    task = detail.get("task", {})
    task_type = str(task.get("taskType") or "")
    task_status = str(task.get("status") or "")
    review_ready = task_status == "APPROVED"
    content_quality_readiness = _content_quality_readiness(detail)
    revision_loop_state = _revision_loop_state(store, task_id)
    content_quality_step = _content_quality_step(content_quality_readiness)
    steps: list[dict[str, Any]] = []
    if content_quality_step:
        steps.append(content_quality_step)
    steps.append(
        _step(
            "generated_content_human_approved",
            "生成内容已人工审核通过",
            review_ready,
            "reviewDetail.task.status",
            "approve_generated_content_after_manual_review",
        )
    )
    platform_readiness = platform_readiness_override or detail.get("agentEntityReadinessReport", {})
    platform_items = _relevant_platform_items(platform_readiness, task_type)
    platform_summary = _platform_summary_for_task(platform_readiness, task_type)
    relevant_agent_entities = {str(item.get("agentEntity")) for item in platform_items if item.get("agentEntity")}
    platform_import_action_summary = _platform_import_preview_action_summary(
        detail.get("platformImportPreviewActions", {}),
        relevant_agent_entities=relevant_agent_entities,
    )
    platform_steps = _platform_steps(
        platform_summary,
        platform_import_action_summary,
        include_future_platform_steps=include_future_platform_steps,
    )
    grading_applicable = task_type in GRADING_REVIEW_TASK_TYPES
    grading_records = detail.get("gradingRecords", {}) if isinstance(detail.get("gradingRecords"), dict) else {}
    grading_record_review = (
        grading_records.get("reviewIntegration")
        if isinstance(grading_records.get("reviewIntegration"), dict)
        else {}
    )
    if grading_applicable:
        steps.extend(_grading_steps(detail.get("preApproveReviewCheck", {})))
        if grading_records.get("visible") is True:
            steps.append(_grading_record_review_step(grading_records))
    steps.extend(platform_steps)

    ready_total = sum(1 for item in steps if item["ready"] is True)
    blocked_steps = [item for item in steps if item["ready"] is not True]
    readiness_state = "CORE_DEMO_READY_FOR_FINAL_REVIEW" if not blocked_steps else "CORE_DEMO_NEEDS_ACTION"
    pre_approve_summary = detail.get("preApproveReviewCheck", {}).get("summary", {})
    recommended_next_action = _recommended_next_action(
        steps,
        include_future_platform_steps=include_future_platform_steps,
    )
    final_review_state = _final_review_state(
        grading_applicable=grading_applicable,
        pre_approve_summary=pre_approve_summary,
        blocked_steps=blocked_steps,
    )
    next_tool_recommendation = _next_tool_recommendation(
        task_id=task_id,
        recommended_next_action=recommended_next_action,
        blocked_steps=blocked_steps,
        platform_import_action_summary=platform_import_action_summary,
        platform_items=platform_items,
        content_quality_readiness=content_quality_readiness,
        revision_loop_state=revision_loop_state,
        pre_approve_summary=pre_approve_summary,
        grading_record_review=grading_record_review,
        final_review_state=final_review_state,
        include_future_platform_steps=include_future_platform_steps,
    )
    return {
        "component": "CoreWorkflowReadinessReport",
        "mode": "CORE_WORKFLOW_READINESS_READ_ONLY",
        "taskId": task_id,
        "taskType": task_type,
        "taskStatus": task_status,
        "status": readiness_state,
        "ready": not blocked_steps,
        "recommendedNextAction": recommended_next_action,
        "summary": {
            "stepTotal": len(steps),
            "readyTotal": ready_total,
            "blockedTotal": len(blocked_steps),
            "platformRequiredTotal": platform_summary.get("requiredTotal", 0),
            "platformPreviewCreatedTotal": platform_summary.get("previewCreatedTotal", 0),
            "platformMockImportCreatedTotal": platform_summary.get("mockImportCreatedTotal", 0),
            "platformDryRunPreparedTotal": platform_summary.get("dryRunPreparedTotal", 0),
            "platformRequestSentTotal": platform_summary.get("requestSentTotal", 0),
            "platformStatusQueriedTotal": platform_summary.get("statusQueriedTotal", 0),
            "platformResultRecordedTotal": platform_summary.get("resultRecordedTotal", 0),
            "platformSignoffRecordedTotal": platform_summary.get("agentEntitySignoffRecordedTotal", 0),
            "finalPublishReviewDecisionRecordedTotal": platform_summary.get(
                "finalPublishReviewDecisionRecordedTotal", 0
            ),
            "platformImportPreviewActionTotal": platform_import_action_summary["total"],
            "platformImportPreviewActionEnabledTotal": platform_import_action_summary["enabledTotal"],
            "platformImportPreviewPendingTotal": platform_import_action_summary["pendingPreviewTotal"],
            "platformImportPreviewPendingEntities": platform_import_action_summary["pendingPlatformEntities"],
            "platformImportPreviewPendingNextActions": platform_import_action_summary["pendingNextRequiredActions"],
            "contentQualityAvailable": content_quality_readiness["available"],
            "contentQualityReadyForImportPreview": content_quality_readiness["readyForImportPreview"],
            "contentQualityDecisionStatus": content_quality_readiness["decisionStatus"],
            "contentQualityRecommendedAction": content_quality_readiness["recommendedAction"],
            "contentQualityRevisionRequired": content_quality_readiness["requiresRevisionBeforeImportPreview"],
            "contentQualityEvidenceRequiredBeforeFinalApproval": content_quality_readiness[
                "requiresEvidenceBeforeFinalApproval"
            ],
            "contentQualityReadyForImportPreviewKinds": content_quality_readiness[
                "readyForImportPreviewKinds"
            ],
            "contentQualityBlockedForImportPreviewKinds": content_quality_readiness[
                "blockedForImportPreviewKinds"
            ],
            "contentQualityBlockingIssueTotal": content_quality_readiness["blockingIssueTotal"],
            "contentQualityWarningIssueTotal": content_quality_readiness["warningIssueTotal"],
            "revisionRequestTotal": revision_loop_state["revisionRequestTotal"],
            "latestRevisionRequestId": revision_loop_state["latestRevisionRequestId"],
            "revisionRequestPendingRegeneration": revision_loop_state["revisionRequestPendingRegeneration"],
            "mockRevisionAlreadyGenerated": revision_loop_state["mockRevisionAlreadyGenerated"],
            "latestMockRevisionTaskId": revision_loop_state["latestMockRevisionTaskId"],
            "finalReviewState": final_review_state,
            "gradingEvidenceReady": pre_approve_summary.get("evidenceReady") if grading_applicable else None,
            "gradingApproveReadyDecision": (
                pre_approve_summary.get("approveReadyDecision") if grading_applicable else None
            ),
            "gradingManualReviewChecklistStatus": (
                pre_approve_summary.get("manualReviewChecklistStatus") if grading_applicable else None
            ),
            "gradingScorePreviewAvailable": (
                pre_approve_summary.get("scorePreviewAvailable") if grading_applicable else None
            ),
            "gradingScorePreviewStatus": (
                pre_approve_summary.get("scorePreviewStatus") if grading_applicable else None
            ),
            "gradingScorePreviewEarnedScore": (
                pre_approve_summary.get("scorePreviewEarnedScore") if grading_applicable else None
            ),
            "gradingScorePreviewTotalScore": (
                pre_approve_summary.get("scorePreviewTotalScore") if grading_applicable else None
            ),
            "gradingScorePreviewCoveredScore": (
                pre_approve_summary.get("scorePreviewCoveredScore") if grading_applicable else None
            ),
            "gradingScorePreviewMissingScore": (
                pre_approve_summary.get("scorePreviewMissingScore") if grading_applicable else None
            ),
            "gradingScorePreviewCoverageRatio": (
                pre_approve_summary.get("scorePreviewCoverageRatio") if grading_applicable else None
            ),
            "gradingScorePreviewPassRate": (
                pre_approve_summary.get("scorePreviewPassRate") if grading_applicable else None
            ),
            "gradingScorePreviewReadyForDecisionNote": (
                pre_approve_summary.get("scorePreviewReadyForDecisionNote") if grading_applicable else None
            ),
            "gradingScorePreviewMissingEvidenceTotal": (
                pre_approve_summary.get("scorePreviewMissingEvidenceTotal") if grading_applicable else None
            ),
            "gradingScorePreviewMissingCheckIds": (
                pre_approve_summary.get("scorePreviewMissingCheckIds") if grading_applicable else None
            ),
            "gradingDecisionNoteRecommendation": (
                pre_approve_summary.get("decisionNoteRecommendation") if grading_applicable else None
            ),
            "gradingDecisionNoteRecommendationReason": (
                pre_approve_summary.get("decisionNoteRecommendationReason") if grading_applicable else None
            ),
            "gradingNextDecisionNoteAction": (
                pre_approve_summary.get("nextDecisionNoteAction") if grading_applicable else None
            ),
            "gradingRecordTotal": grading_records.get("total") if grading_applicable else None,
            "gradingRecordLatestStatus": (
                grading_records.get("summary", {}).get("latestStatus") if grading_applicable else None
            ),
            "gradingRecordLatestDecision": (
                grading_records.get("summary", {}).get("latestReviewDecision") if grading_applicable else None
            ),
            "gradingRecordHumanReviewRecordedTotal": (
                grading_record_review.get("humanReviewRecordedTotal") if grading_applicable else None
            ),
            "gradingRecordReviewState": (
                grading_record_review.get("state") if grading_applicable else None
            ),
            "gradingRecordReadyForPlatformReview": (
                grading_record_review.get("readyForAgentReview") if grading_applicable else None
            ),
            "gradingRecordNextRequiredAction": (
                grading_record_review.get("nextRequiredAction") if grading_applicable else None
            ),
        },
        "steps": steps,
        "blockedSteps": blocked_steps,
        "contentQualityReadiness": content_quality_readiness,
        "revisionLoopState": revision_loop_state,
        "gradingRecordReview": grading_record_review,
        "platformImportPreviewActionSummary": platform_import_action_summary,
        "nextToolRecommendation": next_tool_recommendation,
        "sources": {
            "reviewDetail": "GET /api/review-tasks/{id}",
            "contentQualitySummary": "reviewDetail.contentQualitySummary",
            "revisionLoopState": "operationAuditEvents.REVIEW_REVISION_REQUEST + REVIEW_MOCK_REGENERATE",
            "agentEntityReadinessReport": "reviewDetail.agentEntityReadinessReport",
            "platformImportPreviewActions": "reviewDetail.platformImportPreviewActions",
            "preApproveReviewCheck": "reviewDetail.preApproveReviewCheck",
            "gradingRecordReview": "reviewDetail.gradingRecords.reviewIntegration",
        },
        "safety": {
            "readOnly": True,
            "newLlmRequestSent": False,
            "realLlmCalled": False,
            "networkAccess": False,
            "secretsRead": False,
            "databaseWritten": False,
            "realAgentImport": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublish": False,
            "sandboxExecutedByReport": False,
            "contestantCodeExecutedByReport": False,
        },
    }
