"""Review queue batch summary for Phase 1 mock review operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ai_task import TaskStatus
from .review_detail import build_review_detail, build_review_safety
from .store import JsonTaskStore


ROOT = Path(__file__).resolve().parents[1]


TASK_TYPE_PRIORITY = {
    "GRADING_GENERATION": 0,
    "EXAM_GENERATION": 1,
    "LAB_GENERATION": 2,
    "PPT_GENERATION": 3,
}

PRIORITY_ORDER = {
    "URGENT": 0,
    "HIGH": 1,
    "NORMAL": 2,
    "LOW": 3,
}

TEACHING_PACKAGE_ARTIFACT_SPECS = {
    "lab": {
        "artifactKind": "LAB_DSL",
        "taskType": "LAB_GENERATION",
        "label": "Lab",
    },
    "exam": {
        "artifactKind": "EXAM_DSL",
        "taskType": "EXAM_GENERATION",
        "label": "Exam",
    },
    "grading": {
        "artifactKind": "GRADING_DSL",
        "taskType": "GRADING_GENERATION",
        "label": "Grading",
    },
}


def _path_exists(path: str) -> bool:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.exists()


def _normalized_path_key(path: str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve().as_posix().lower()


def _latest_task_for_path(store: JsonTaskStore, task_type: str, path: str) -> Any | None:
    normalized = _normalized_path_key(path)
    candidates = [
        task
        for task in store.list(status=TaskStatus.WAITING_REVIEW.value, task_type=task_type)
        if task.finalResultPath and _normalized_path_key(task.finalResultPath) == normalized
    ]
    return candidates[0] if candidates else None


REAL_DEMO_REPORT_KIND_SPECS = {
    "lab": {
        "rank": 1,
        "fallbackTaskId": "real_demo_lab",
        "taskType": "LAB_GENERATION",
        "artifactKind": "LAB_DSL",
        "recommendedAction": "review_lab_objectives_and_steps",
        "entryRoute": "/labs/:id/review",
    },
    "exam": {
        "rank": 2,
        "fallbackTaskId": "real_demo_exam",
        "taskType": "EXAM_GENERATION",
        "artifactKind": "EXAM_DSL",
        "candidatePreviewAnswersRemoved": True,
        "answerVisibleToCandidate": False,
        "recommendedAction": "verify_candidate_preview_and_grading_refs",
        "entryRoute": "/exams/:id/review",
    },
    "grading": {
        "rank": 3,
        "fallbackTaskId": "real_demo_grading",
        "taskType": "GRADING_GENERATION",
        "artifactKind": "GRADING_DSL",
        "sourcePreserved": True,
        "readonlyEvidenceReportDetailSource": "realDemoPrototype.readonlyEvidenceDemo.reportDetail",
        "readonlyEvidenceCollectedTotal": 2,
        "readonlyEvidenceStatus": "COLLECTED",
        "recommendedAction": "review_assessment_plan_and_readonly_evidence_before_approval",
        "entryRoute": "/grading/:id/report",
    },
    "ppt": {
        "rank": 4,
        "fallbackTaskId": "real_demo_ppt",
        "taskType": "PPT_GENERATION",
        "artifactKind": "PPT_DSL",
        "pptPageReviewActionVisible": True,
        "recommendedAction": "review_pptx_artifact_and_page_status",
        "entryRoute": "/ppt/:id/review",
    },
}


def _load_real_demo_report(report_path: str | None) -> tuple[dict[str, Any] | None, str | None]:
    if not report_path:
        return None, None
    candidate = Path(report_path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    if not candidate.exists() or not candidate.is_file():
        return None, "file_not_found"
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "parse_failed"
    if not isinstance(payload, dict):
        return None, "report_not_object"
    if not isinstance(payload.get("generatedDsl"), dict):
        return None, "generated_dsl_missing"
    payload["_localReportPath"] = str(candidate)
    return payload, None


def _report_generated_item(report: dict[str, Any], kind: str) -> dict[str, Any]:
    generated = report.get("generatedDsl") if isinstance(report.get("generatedDsl"), dict) else {}
    item = generated.get(kind)
    return item if isinstance(item, dict) else {}


def _real_demo_report_item_specs(report_path: str | None) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    report, unavailable_reason = _load_real_demo_report(report_path)
    if report is None:
        if unavailable_reason:
            return None, {
                "agentReportPath": report_path,
                "agentReportLoadStatus": unavailable_reason,
            }
        return None, None

    report_path_value = str(report.get("_localReportPath") or report_path or "")
    specs: list[dict[str, Any]] = []
    for kind, base in REAL_DEMO_REPORT_KIND_SPECS.items():
        generated_item = _report_generated_item(report, kind)
        dsl_path = generated_item.get("dslPath")
        if not dsl_path:
            continue
        task_id = str(generated_item.get("taskId") or base["fallbackTaskId"])
        artifact_kind = str(base["artifactKind"])
        specs.append(
            {
                **base,
                "rank": base["rank"],
                "fallbackTaskId": task_id,
                "taskId": task_id,
                "dynamicTaskId": task_id,
                "dynamicTaskAvailable": True,
                "syntheticTaskAvailable": True,
                "artifactKind": artifact_kind,
                "path": str(dsl_path),
                "status": str(generated_item.get("status") or "WAITING_REVIEW"),
                "schemaValidated": generated_item.get("schemaValidated") is True,
                "agentReportPath": report_path_value,
                "agentReportId": report.get("id"),
                "workflowId": report.get("workflowId"),
                "workflowMode": report.get("mode"),
                "providerMode": report.get("providerMode"),
                "dslId": generated_item.get("dslId"),
                "title": f"真实批次 · {artifact_kind}",
            }
        )

    return specs, {
        "agentReportPath": report_path_value,
        "agentReportId": report.get("id"),
        "agentReportLoadStatus": "LOADED",
        "workflowId": report.get("workflowId"),
        "workflowMode": report.get("mode"),
        "providerMode": report.get("providerMode"),
    }


def _real_demo_review_queue(store: JsonTaskStore, *, agent_report: str | None = None) -> dict[str, Any]:
    custom_specs, custom_report_summary = _real_demo_report_item_specs(agent_report)
    if custom_specs:
        item_specs = custom_specs
    else:
        custom_specs = None
        custom_report_summary = custom_report_summary or {}
        item_specs = [
            {
                **REAL_DEMO_REPORT_KIND_SPECS["lab"],
                "path": "examples/output/real-llm-lab.json",
            },
            {
                **REAL_DEMO_REPORT_KIND_SPECS["exam"],
                "path": "examples/output/real-llm-exam.json",
            },
            {
                **REAL_DEMO_REPORT_KIND_SPECS["grading"],
                "path": "examples/output/real-llm-grading.json",
            },
            {
                **REAL_DEMO_REPORT_KIND_SPECS["ppt"],
                "artifactKind": "PPT_DSL_AND_PPTX_FILE",
                "path": "examples/output/real-llm-ppt.json",
                "pptxArtifactPath": "examples/output/real-llm-demo-ppt-artifact.pptx",
            },
        ]
    items = []
    dynamic_task_total = 0
    local_artifact_total = 0
    synthetic_task_total = 0
    for spec in item_specs:
        task = None if custom_specs else _latest_task_for_path(store, spec["taskType"], spec["path"])
        artifact_exists = _path_exists(spec["path"])
        local_artifact_total += 1 if artifact_exists else 0
        synthetic_available = spec.get("syntheticTaskAvailable") is True
        dynamic_available = task is not None or synthetic_available
        dynamic_task_total += 1 if dynamic_available else 0
        synthetic_task_total += 1 if synthetic_available else 0
        item = {
            "rank": spec["rank"],
            "taskId": task.id if task is not None else str(spec.get("taskId") or spec["fallbackTaskId"]),
            "fallbackTaskId": spec["fallbackTaskId"],
            "dynamicTaskId": task.id if task is not None else spec.get("dynamicTaskId"),
            "dynamicTaskAvailable": dynamic_available,
            "syntheticTaskAvailable": synthetic_available,
            "taskType": spec["taskType"],
            "artifactKind": spec["artifactKind"],
            "status": task.status.value if task is not None else str(spec.get("status") or "WAITING_REVIEW"),
            "path": spec["path"],
            "localArtifactExists": artifact_exists,
            "schemaValidated": bool(spec.get("schemaValidated") is True or artifact_exists),
            "recommendedAction": spec["recommendedAction"],
            "entryRoute": spec["entryRoute"],
        }
        for optional_key in (
            "candidatePreviewAnswersRemoved",
            "answerVisibleToCandidate",
            "sourcePreserved",
            "readonlyEvidenceReportDetailSource",
            "readonlyEvidenceCollectedTotal",
            "readonlyEvidenceStatus",
            "pptxArtifactPath",
            "pptPageReviewActionVisible",
            "agentReportPath",
            "agentReportId",
            "workflowId",
            "workflowMode",
            "providerMode",
            "dslId",
            "title",
        ):
            if optional_key in spec:
                item[optional_key] = spec[optional_key]
        if item.get("pptxArtifactPath"):
            item["pptxArtifactExists"] = _path_exists(item["pptxArtifactPath"])
        items.append(item)
    return {
        "enabled": True,
        "component": "RealDemoReviewQueue",
        "source": "reviewTaskSummary.realDemoReviewQueue + local examples/output real LLM artifacts",
        "fallbackSource": "realDemoPrototype.generatedDsl + realDemoPrototype.coreBusinessDemoPath + realDemoPrototype.readonlyEvidenceDemo.reportDetail",
        "sourceMode": (
            "AGENT_REPORT_REAL_LLM_ARTIFACTS"
            if custom_specs
            else ("LOCAL_REAL_LLM_ARTIFACTS" if local_artifact_total else "STATIC_DEMO_FALLBACK")
        ),
        "route": "/real-demo -> /review-center -> /ppt/:id/review -> /grading/:id/report",
        "taskTotal": 4,
        "waitingReviewTotal": 4,
        "dynamicTaskTotal": dynamic_task_total,
        "syntheticTaskTotal": synthetic_task_total,
        "localArtifactTotal": local_artifact_total,
        "schemaValidatedTotal": sum(1 for item in items if item["schemaValidated"] is True),
        "agentReport": custom_report_summary,
        "readonlyEvidenceVisible": True,
        "readonlyEvidenceReportDetailSource": "realDemoPrototype.readonlyEvidenceDemo.reportDetail",
        "readonlyEvidenceCollectedTotal": 2,
        "candidatePreviewAnswerSafe": True,
        "answerVisibleToCandidate": False,
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "items": items,
    }


def _controlled_docker_evidence_review_signal() -> dict[str, Any]:
    return {
        "enabled": True,
        "component": "ControlledDockerEvidenceReviewSignal",
        "source": "realDemoPrototype.controlledDockerEvidenceDemo",
        "dynamicSource": "reviewDetail.controlledGradingEvidence",
        "fallbackSource": "realDemoPrototype.controlledDockerEvidenceDemo",
        "sourceMode": "STATIC_DEMO_FALLBACK",
        "route": "/real-demo -> /review-center -> /grading/:id/report",
        "taskId": "real_demo_grading",
        "taskType": "GRADING_GENERATION",
        "artifactKind": "CONTROLLED_DOCKER_EVIDENCE",
        "status": "PARTIAL_CONTROLLED_EVIDENCE_COLLECTED",
        "available": True,
        "taskTotal": 1,
        "planTotal": 1,
        "reportTotal": 1,
        "sourceGradingPath": "examples/output/real-llm-grading.json",
        "controlledPlanPath": "examples/output/mimo-real-demo-controlled-plan.json",
        "controlledReportPath": "examples/output/mimo-real-demo-controlled-sandbox-report.json",
        "submissionPath": "examples/submissions/real-demo-controlled",
        "imageVerifyPath": "examples/output/grading-sandbox-image-verify.json",
        "executionMode": "controlled-command",
        "sandboxMode": "CONTROLLED_DOCKER_SANDBOX_POC",
        "imageTag": "ai-grading-python:0.1",
        "coveredCheckIds": [
            "check_q1",
            "check_q4",
        ],
        "coveredCheckTypes": [
            "stdout_contains",
            "pytest",
        ],
        "coveredScore": 40,
        "executed": 2,
        "passed": 2,
        "earnedScore": 40,
        "totalControlledScore": 40,
        "items": [
            {
                "available": True,
                "source": "realDemoPrototype.controlledDockerEvidenceDemo",
                "taskId": "real_demo_grading",
                "taskType": "GRADING_GENERATION",
                "status": "PARTIAL_CONTROLLED_EVIDENCE_COLLECTED",
                "planTotal": 1,
                "reportTotal": 1,
                "planPath": "examples/output/mimo-real-demo-controlled-plan.json",
                "reportPath": "examples/output/mimo-real-demo-controlled-sandbox-report.json",
                "sourceGradingPath": "examples/output/real-llm-grading.json",
                "submissionRoot": "examples/submissions/real-demo-controlled",
                "sandboxMode": "CONTROLLED_DOCKER_SANDBOX_POC",
                "coveredCheckIds": [
                    "check_q1",
                    "check_q4",
                ],
                "coveredCheckTypes": [
                    "stdout_contains",
                    "pytest",
                ],
                "executed": 2,
                "passed": 2,
                "earnedScore": 40,
                "totalControlledScore": 40,
                "sandboxExecuted": True,
                "contestantCodeExecuted": True,
                "commandExecuted": True,
                "pytestExecuted": True,
                "networkEnabled": False,
                "manualReviewRequired": True,
                "autoApproveAllowed": False,
                "batchStateChangeAllowed": False,
                "realPublishAllowed": False,
            }
        ],
        "remainingCheckIds": [
            "check_q2",
            "check_q3",
        ],
        "remainingCheckTypes": [
            "notebook_cell",
        ],
        "remainingScore": 60,
        "remainingStatus": "STATIC_NOTEBOOK_EVIDENCE_READY_FOR_REVIEW",
        "notebookEvidenceReviewPlanSource": "reviewTaskSummary.notebookEvidenceReviewPlan",
        "remainingReviewPlanStatus": "NOTEBOOK_STATIC_EVIDENCE_COLLECTED",
        "recommendedAction": "review_container_and_static_notebook_evidence_before_approval",
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": False,
        "safety": {
            "pageReadOnly": True,
            "hostExecutionAllowed": False,
            "networkAllowed": False,
            "secretVisibleInFrontend": False,
            "answerVisibleToCandidate": False,
            "sourceGradingModified": False,
        },
    }


def _controlled_grading_evidence_summary_from_detail(detail: dict[str, Any]) -> dict[str, Any]:
    task = detail["task"]
    evidence = detail.get("controlledGradingEvidence")
    if not isinstance(evidence, dict):
        evidence = {}
    summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
    safety = evidence.get("safety") if isinstance(evidence.get("safety"), dict) else {}
    decision_hints = (
        evidence.get("reviewDecisionHints")
        if isinstance(evidence.get("reviewDecisionHints"), dict)
        else {}
    )
    reports = evidence.get("reports") if isinstance(evidence.get("reports"), list) else []
    plans = evidence.get("plans") if isinstance(evidence.get("plans"), list) else []
    report = reports[0] if reports and isinstance(reports[0], dict) else {}
    plan = plans[0] if plans and isinstance(plans[0], dict) else {}
    check_summary = report.get("checkSummary") if isinstance(report.get("checkSummary"), dict) else {}
    checks = report.get("checks") if isinstance(report.get("checks"), list) else []
    executed_checks = [
        check
        for check in checks
        if isinstance(check, dict) and check.get("status") in {"PASSED", "FAILED", "ERROR"}
    ]
    return {
        "available": bool(evidence.get("visible")),
        "source": "reviewDetail.controlledGradingEvidence",
        "taskId": task["id"],
        "taskType": task.get("taskType"),
        "status": "CONTROLLED_EVIDENCE_COLLECTED" if evidence.get("visible") else "NOT_AVAILABLE",
        "mode": evidence.get("mode"),
        "planTotal": evidence.get("planTotal", 0),
        "reportTotal": evidence.get("reportTotal", 0),
        "planPath": plan.get("artifactPath"),
        "reportPath": report.get("artifactPath"),
        "sourceGradingPath": plan.get("sourceGradingPath"),
        "submissionRoot": report.get("submissionRoot"),
        "sandboxMode": report.get("mode"),
        "coveredCheckIds": [
            str(check.get("id")) for check in executed_checks if check.get("id")
        ],
        "coveredCheckTypes": list(
            dict.fromkeys(str(check.get("type")) for check in executed_checks if check.get("type"))
        ),
        "executed": summary.get("executedTotal", 0),
        "passed": summary.get("passedTotal", 0),
        "earnedScore": summary.get("earnedScore", 0),
        "totalControlledScore": summary.get("totalScore", 0),
        "sandboxExecuted": bool(summary.get("sandboxExecuted", safety.get("sandboxExecuted", False))),
        "contestantCodeExecuted": bool(
            summary.get("contestantCodeExecuted", safety.get("contestantCodeExecuted", False))
        ),
        "commandExecuted": bool(summary.get("commandExecuted", safety.get("commandExecuted", False))),
        "pytestExecuted": bool(summary.get("pytestExecuted", safety.get("pytestExecuted", False))),
        "networkEnabled": bool(summary.get("networkEnabled", safety.get("networkEnabled", False))),
        "manualReviewRequired": bool(summary.get("manualReviewRequired", False)),
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": False,
    }


def _dynamic_controlled_docker_evidence_review_signal(details: list[dict[str, Any]]) -> dict[str, Any]:
    items = [
        _controlled_grading_evidence_summary_from_detail(detail)
        for detail in details
        if detail.get("task", {}).get("taskType") == "GRADING_GENERATION"
        and isinstance(detail.get("controlledGradingEvidence"), dict)
        and detail.get("controlledGradingEvidence", {}).get("visible") is True
    ]
    if not items:
        return _controlled_docker_evidence_review_signal()

    covered_check_ids: list[str] = []
    covered_check_types: list[str] = []
    for item in items:
        covered_check_ids.extend(str(check_id) for check_id in item.get("coveredCheckIds", []) if check_id)
        covered_check_types.extend(str(check_type) for check_type in item.get("coveredCheckTypes", []) if check_type)

    return {
        "enabled": True,
        "component": "ControlledDockerEvidenceReviewSignal",
        "source": "reviewDetail.controlledGradingEvidence",
        "dynamicSource": "reviewDetail.controlledGradingEvidence",
        "fallbackSource": "realDemoPrototype.controlledDockerEvidenceDemo",
        "sourceMode": "DYNAMIC_CONTROLLED_DOCKER_EVIDENCE",
        "route": "/review-center -> /grading/:id/report",
        "mode": "DYNAMIC_CONTROLLED_DOCKER_EVIDENCE",
        "taskTotal": len(items),
        "available": True,
        "planTotal": sum(int(item.get("planTotal", 0) or 0) for item in items),
        "reportTotal": sum(int(item.get("reportTotal", 0) or 0) for item in items),
        "status": "CONTROLLED_EVIDENCE_COLLECTED",
        "artifactKind": "CONTROLLED_DOCKER_EVIDENCE",
        "coveredCheckIds": list(dict.fromkeys(covered_check_ids)),
        "coveredCheckTypes": list(dict.fromkeys(covered_check_types)),
        "executed": sum(int(item.get("executed", 0) or 0) for item in items),
        "passed": sum(int(item.get("passed", 0) or 0) for item in items),
        "earnedScore": sum(float(item.get("earnedScore", 0) or 0) for item in items),
        "totalControlledScore": sum(float(item.get("totalControlledScore", 0) or 0) for item in items),
        "items": items,
        "recommendedAction": "review_dynamic_controlled_docker_evidence_before_approval",
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": False,
        "safety": {
            "source": "reviewDetail.controlledGradingEvidence.safety",
            "pageReadOnly": True,
            "sandboxExecuted": any(item["sandboxExecuted"] for item in items),
            "contestantCodeExecuted": any(item["contestantCodeExecuted"] for item in items),
            "commandExecuted": any(item["commandExecuted"] for item in items),
            "pytestExecuted": any(item["pytestExecuted"] for item in items),
            "hostExecutionAllowed": False,
            "networkAllowed": any(item["networkEnabled"] for item in items),
            "secretVisibleInFrontend": False,
            "answerVisibleToCandidate": False,
            "sourceGradingModified": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
    }


def _merged_grading_evidence_review_signal() -> dict[str, Any]:
    return {
        "enabled": True,
        "component": "MergedGradingEvidenceReviewSignal",
        "source": "reviewDetail.mergedGradingEvidence",
        "dynamicSource": "reviewDetail.mergedGradingEvidence",
        "fallbackSource": None,
        "sourceMode": "NO_MERGED_EVIDENCE_REPORT",
        "route": "/review-center -> /grading/:id/report",
        "taskTotal": 0,
        "available": False,
        "reportTotal": 0,
        "status": "NOT_AVAILABLE",
        "artifactKind": "GRADING_EVIDENCE_MERGE",
        "coveredCheckIds": [],
        "controlledDockerCheckTotal": 0,
        "readonlyStaticCheckTotal": 0,
        "executed": 0,
        "passedCheckTotal": 0,
        "failedCheckTotal": 0,
        "deferredCheckTotal": 0,
        "earnedScore": 0,
        "totalScore": 0,
        "coverageRatio": 0,
        "items": [],
        "recommendedAction": "run_grade_evidence_merge_before_final_grading_review",
        "manualReviewRequired": False,
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": False,
        "safety": {
            "source": "reviewDetail.mergedGradingEvidence.safety",
            "pageReadOnly": True,
            "mergeExecutedOnlyExistingReports": True,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "commandExecuted": False,
            "pytestExecuted": False,
            "hostExecutionAllowed": False,
            "networkAllowed": False,
            "secretVisibleInFrontend": False,
            "answerVisibleToCandidate": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
    }


def _merged_grading_evidence_summary_from_detail(detail: dict[str, Any]) -> dict[str, Any]:
    task = detail["task"]
    evidence = detail.get("mergedGradingEvidence")
    if not isinstance(evidence, dict):
        evidence = {}
    summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
    safety = evidence.get("safety") if isinstance(evidence.get("safety"), dict) else {}
    decision_hints = (
        evidence.get("reviewDecisionHints")
        if isinstance(evidence.get("reviewDecisionHints"), dict)
        else {}
    )
    reports = evidence.get("reports") if isinstance(evidence.get("reports"), list) else []
    report = reports[0] if reports and isinstance(reports[0], dict) else {}
    coverage = report.get("evidenceCoverage") if isinstance(report.get("evidenceCoverage"), dict) else {}
    controlled = coverage.get("controlledDocker") if isinstance(coverage.get("controlledDocker"), dict) else {}
    readonly = coverage.get("readonlyStatic") if isinstance(coverage.get("readonlyStatic"), dict) else {}
    return {
        "available": bool(evidence.get("visible")),
        "source": "reviewDetail.mergedGradingEvidence",
        "taskId": task["id"],
        "taskType": task.get("taskType"),
        "status": "MERGED_EVIDENCE_COLLECTED" if evidence.get("visible") else "NOT_AVAILABLE",
        "mode": evidence.get("mode"),
        "reportTotal": evidence.get("reportTotal", 0),
        "reportPath": report.get("artifactPath"),
        "reportType": report.get("artifactReportType"),
        "reportMode": report.get("mode"),
        "sourceMode": report.get("sourceMode"),
        "reportId": report.get("reportId"),
        "sourceReportTotal": summary.get("sourceReportTotal", report.get("sourceReportTotal", 0)),
        "coveredCheckIds": [
            str(check_id) for check_id in coverage.get("coveredCheckIds", []) if check_id
        ] if isinstance(coverage.get("coveredCheckIds"), list) else [],
        "controlledDockerCheckIds": [
            str(check_id) for check_id in controlled.get("checkIds", []) if check_id
        ] if isinstance(controlled.get("checkIds"), list) else [],
        "readonlyStaticCheckIds": [
            str(check_id) for check_id in readonly.get("checkIds", []) if check_id
        ] if isinstance(readonly.get("checkIds"), list) else [],
        "controlledDockerCheckTotal": summary.get("controlledDockerCheckTotal", controlled.get("checkTotal", 0)),
        "readonlyStaticCheckTotal": summary.get("readonlyStaticCheckTotal", readonly.get("checkTotal", 0)),
        "executed": summary.get("executedTotal", 0),
        "passedCheckTotal": summary.get("passedCheckTotal", 0),
        "failedCheckTotal": summary.get("failedCheckTotal", 0),
        "deferredCheckTotal": summary.get("deferredCheckTotal", 0),
        "earnedScore": summary.get("earnedScore", 0),
        "totalScore": summary.get("totalScore", 0),
        "coverageRatio": summary.get("coverageRatio", 0),
        "checkEvidenceReviewItemTotal": summary.get("checkEvidenceReviewItemTotal", 0),
        "manualCheckReviewTotal": summary.get("manualCheckReviewTotal", 0),
        "autoEvidenceReport": bool(summary.get("autoEvidenceReport", False)),
        "autoEvidenceStepTotal": summary.get("autoEvidenceStepTotal", 0),
        "autoEvidenceWarningTotal": summary.get("autoEvidenceWarningTotal", 0),
        "reviewDecisionHintsSummary": {
            "available": bool(decision_hints.get("available", False)),
            "overallHint": decision_hints.get("overallHint", "NEEDS_EVIDENCE"),
            "nextRecommendedAction": decision_hints.get("nextRecommendedAction"),
            "hintTotal": decision_hints.get("hintTotal", 0),
            "approveReadyTotal": decision_hints.get("approveReadyTotal", 0),
            "reviseRequiredTotal": decision_hints.get("reviseRequiredTotal", 0),
            "evidenceMissingTotal": decision_hints.get("evidenceMissingTotal", 0),
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
        "checkEvidenceReviewItems": (
            evidence.get("checkEvidenceReviewItems", [])[:6]
            if isinstance(evidence.get("checkEvidenceReviewItems"), list)
            else []
        ),
        "mergeExecutedOnlyExistingReports": bool(
            safety.get("mergeExecutedOnlyExistingReports", bool(evidence.get("visible")))
        ),
        "sandboxExecuted": bool(safety.get("sandboxExecuted", False)),
        "contestantCodeExecuted": bool(safety.get("contestantCodeExecuted", False)),
        "commandExecuted": bool(safety.get("commandExecuted", False)),
        "pytestExecuted": bool(safety.get("pytestExecuted", False)),
        "networkEnabled": bool(safety.get("networkEnabled", False)),
        "manualReviewRequired": bool(summary.get("manualReviewRequired", evidence.get("visible", False))),
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": False,
    }


def _readiness_item_from_check_evidence(item: dict[str, Any]) -> dict[str, Any]:
    check_type = str(item.get("checkType") or item.get("type") or "unknown")
    status = str(item.get("status") or "")
    passed = item.get("passed")
    evidence_ready = status in {"PASSED", "FAILED", "ERROR"} or passed is not None
    if evidence_ready:
        recommended_next = "manual_review"
    elif check_type in {"stdout_contains", "pytest"}:
        recommended_next = "controlled_command_evidence"
    elif check_type in {"file_exists", "json_field", "notebook_cell", "log_keyword"}:
        recommended_next = "readonly_static_evidence"
    else:
        recommended_next = "manual_review_only"
    return {
        "checkId": str(item.get("checkId") or item.get("id") or ""),
        "checkType": check_type,
        "status": status or ("COLLECTED" if evidence_ready else "MISSING"),
        "score": item.get("score", 0),
        "earnedScore": item.get("earnedScore", 0),
        "evidenceReady": evidence_ready,
        "evidenceSourceKind": item.get("evidenceSourceKind", "unknown"),
        "recommendedNextEvidence": recommended_next,
        "recommendedAction": item.get("recommendedAction") or (
            "verify_existing_evidence_and_score" if evidence_ready else "collect_missing_grading_evidence"
        ),
        "manualReviewRequired": True,
    }


def _grading_evidence_readiness_summary_from_detail(detail: dict[str, Any]) -> dict[str, Any]:
    task = detail["task"]
    evidence = detail.get("mergedGradingEvidence")
    if not isinstance(evidence, dict):
        evidence = {}
    raw_items = evidence.get("checkEvidenceReviewItems")
    items = [
        _readiness_item_from_check_evidence(item)
        for item in raw_items
        if isinstance(item, dict)
    ] if isinstance(raw_items, list) else []
    ready_items = [item for item in items if item["evidenceReady"] is True]
    missing_items = [item for item in items if item["evidenceReady"] is not True]
    controlled_missing = [
        item for item in missing_items if item["recommendedNextEvidence"] == "controlled_command_evidence"
    ]
    readonly_missing = [
        item for item in missing_items if item["recommendedNextEvidence"] == "readonly_static_evidence"
    ]
    manual_only_missing = [
        item for item in missing_items if item["recommendedNextEvidence"] == "manual_review_only"
    ]
    total_score = sum(float(item.get("score", 0) or 0) for item in items)
    covered_score = sum(float(item.get("score", 0) or 0) for item in ready_items)
    earned_score = sum(float(item.get("earnedScore", 0) or 0) for item in ready_items)
    next_actions: list[str] = []
    if controlled_missing:
        next_actions.append("run_controlled_command_evidence_after_review")
    if readonly_missing:
        next_actions.append("run_readonly_static_evidence")
    if manual_only_missing:
        next_actions.append("perform_manual_review")

    available = bool(evidence.get("visible")) and bool(items)
    if not next_actions:
        next_actions.append(
            "review_ready_score_and_evidence_before_approval"
            if available
            else "run_grade_evidence_merge_or_auto_before_approval"
        )
    action_guide_status = (
        "READY_FOR_MANUAL_REVIEW"
        if available and not missing_items
        else "EVIDENCE_COLLECTION_RECOMMENDED"
    )
    return {
        "available": available,
        "component": "GradingEvidenceReadiness",
        "source": "reviewDetail.mergedGradingEvidence.checkEvidenceReviewItems",
        "taskId": task["id"],
        "taskType": task.get("taskType"),
        "mode": "GRADING_EVIDENCE_READINESS",
        "status": (
            "READY_FOR_APPROVAL_RECOMMENDATION"
            if available and not missing_items
            else "MISSING_EVIDENCE"
            if available
            else "NO_MERGED_EVIDENCE_REPORT"
        ),
        "summary": {
            "checkTotal": len(items),
            "evidenceReadyTotal": len(ready_items),
            "missingEvidenceTotal": len(missing_items),
            "controlledCommandMissingTotal": len(controlled_missing),
            "readonlyStaticMissingTotal": len(readonly_missing),
            "manualOnlyMissingTotal": len(manual_only_missing),
            "totalScore": total_score,
            "coveredScore": covered_score,
            "earnedScore": earned_score,
            "coverageRatio": round(covered_score / total_score, 4) if total_score else 0,
            "readyForHumanReview": available,
            "readyForApprovalRecommendation": available and not missing_items,
            "manualReviewRequired": True,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
        "items": items[:6],
        "nextActions": next_actions,
        "actionGuide": {
            "component": "GradingEvidenceActionGuide",
            "status": action_guide_status,
            "primaryAction": (
                "review_ready_score_and_evidence_before_approval"
                if action_guide_status == "READY_FOR_MANUAL_REVIEW"
                else "run_grade_evidence_auto_then_review_report"
            ),
            "api": {
                "method": "POST",
                "path": "/api/grading/evidence-auto",
                "body": {
                    "taskId": task["id"],
                    "includeControlledCommand": False,
                    "failOnControlledUnavailable": False,
                },
            },
            "cli": (
                "python lab_cli.py grade evidence-auto --task-id "
                f"{task['id']} --include-controlled-command false"
            ),
            "reportEntry": "grading-report.html?file={reportPath}&taskId={taskId}",
            "followUp": [
                "open_latest_grading_report",
                "verify_grading_evidence_readiness",
                "record_review_decision_note_before_manual_approve",
            ],
            "safety": {
                "autoApproveAllowed": False,
                "batchStateChangeAllowed": False,
                "realPublishAllowed": False,
                "controlledCommandOptInRequired": True,
                "secretVisibleInFrontend": False,
            },
        },
        "safety": {
            "readExistingReportsOnly": True,
            "sandboxExecutedByReadiness": False,
            "contestantCodeExecutedByReadiness": False,
            "commandExecutedByReadiness": False,
            "pytestExecutedByReadiness": False,
            "notebookExecutedByReadiness": False,
            "networkAccessByReadiness": False,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
        },
    }


def _pre_approve_review_check_summary_from_detail(detail: dict[str, Any]) -> dict[str, Any]:
    task = detail["task"]
    task_type = task.get("taskType")
    merged = detail.get("mergedGradingEvidence")
    if not isinstance(merged, dict):
        merged = {}
    merged_summary = merged.get("summary") if isinstance(merged.get("summary"), dict) else {}
    notes = detail.get("reviewDecisionNotes")
    if not isinstance(notes, dict):
        notes = {}
    latest_note = notes.get("latest") if isinstance(notes.get("latest"), dict) else {}

    applicable = task_type == "GRADING_GENERATION"
    evidence_ready = bool(merged.get("visible") is True and merged_summary.get("checkEvidenceReviewItemTotal", 0) > 0)
    note_recorded = bool(notes.get("total", 0) > 0)
    latest_decision = latest_note.get("decision")
    approve_ready_decision = latest_decision == "approve-ready"
    score_preview_available = bool(merged_summary.get("scorePreviewAvailable"))
    score_preview_ready = merged_summary.get("scorePreviewReadyForDecisionNote")
    recommended_warnings: list[str] = []
    if applicable and not evidence_ready:
        recommended_warnings.append("grading_evidence_missing_before_approve")
    if applicable and score_preview_available and score_preview_ready is not True:
        recommended_warnings.append("grading_score_preview_not_ready_for_decision_note")
    if applicable and not note_recorded:
        recommended_warnings.append("review_decision_note_missing_before_approve")
    if applicable and note_recorded and not approve_ready_decision:
        recommended_warnings.append("review_decision_note_not_approve_ready_before_approve")

    return {
        "component": "PreApproveReviewCheck",
        "source": "reviewDetail.mergedGradingEvidence + reviewDetail.reviewDecisionNotes",
        "taskId": task["id"],
        "taskType": task_type,
        "applicable": applicable,
        "status": "READY_FOR_HUMAN_APPROVE" if not recommended_warnings else "APPROVE_ALLOWED_WITH_WARNINGS",
        "blocking": False,
        "approvalStillAllowed": True,
        "summary": {
            "evidenceReady": evidence_ready,
            "reviewDecisionNoteRecorded": note_recorded,
            "approveReadyDecision": approve_ready_decision,
            "warningTotal": len(recommended_warnings),
            "recommendedWarnings": recommended_warnings,
            "mergedEvidenceReportTotal": merged.get("reportTotal", 0),
            "checkEvidenceReviewItemTotal": merged_summary.get("checkEvidenceReviewItemTotal", 0),
            "scorePreviewAvailable": score_preview_available,
            "scorePreviewStatus": merged_summary.get("scorePreviewStatus"),
            "scorePreviewEarnedScore": merged_summary.get("scorePreviewEarnedScore"),
            "scorePreviewTotalScore": merged_summary.get("scorePreviewTotalScore"),
            "scorePreviewCoveredScore": merged_summary.get("scorePreviewCoveredScore"),
            "scorePreviewMissingScore": merged_summary.get("scorePreviewMissingScore"),
            "scorePreviewCoverageRatio": merged_summary.get("scorePreviewCoverageRatio"),
            "scorePreviewPassRate": merged_summary.get("scorePreviewPassRate"),
            "scorePreviewReadyForDecisionNote": score_preview_ready,
            "scorePreviewMissingEvidenceTotal": merged_summary.get("scorePreviewMissingEvidenceTotal"),
            "scorePreviewMissingCheckIds": merged_summary.get("scorePreviewMissingCheckIds", []),
            "manualReviewChecklistStatus": merged_summary.get("manualReviewChecklistStatus"),
            "manualReviewChecklistReadyTotal": merged_summary.get("manualReviewChecklistReadyTotal", 0),
            "manualReviewChecklistTotal": merged_summary.get("manualReviewChecklistTotal", 0),
            "decisionNoteRecommendation": merged_summary.get("decisionNoteRecommendation"),
            "decisionNoteRecommendationReason": merged_summary.get("decisionNoteRecommendationReason"),
            "nextDecisionNoteAction": merged_summary.get("nextDecisionNoteAction"),
            "latestDecision": latest_decision,
        },
        "safety": {
            "readOnly": True,
            "statusChangeBlocked": False,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }


def _light_pre_approve_review_check_summary(task: Any) -> dict[str, Any]:
    applicable = task.taskType == "GRADING_GENERATION"
    warnings = ["open_review_detail_before_approval"] if applicable else []
    return {
        "component": "PreApproveReviewCheck",
        "source": "reviewTaskSummary.detailMode=light",
        "taskId": task.id,
        "taskType": task.taskType,
        "applicable": applicable,
        "status": "DETAIL_REQUIRED" if applicable else "NOT_APPLICABLE",
        "blocking": False,
        "approvalStillAllowed": True,
        "summary": {
            "evidenceReady": False,
            "reviewDecisionNoteRecorded": False,
            "approveReadyDecision": False,
            "warningTotal": len(warnings),
            "recommendedWarnings": warnings,
            "mergedEvidenceReportTotal": 0,
            "checkEvidenceReviewItemTotal": 0,
            "latestDecision": None,
        },
        "safety": {
            "readOnly": True,
            "statusChangeBlocked": False,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }


def _light_grading_evidence_readiness_summary(task: Any) -> dict[str, Any]:
    applicable = task.taskType == "GRADING_GENERATION"
    return {
        "available": False,
        "component": "GradingEvidenceReadiness",
        "source": "reviewTaskSummary.detailMode=light",
        "taskId": task.id,
        "taskType": task.taskType,
        "mode": "GRADING_EVIDENCE_READINESS",
        "status": "DETAIL_REQUIRED" if applicable else "NOT_APPLICABLE",
        "summary": {
            "checkTotal": 0,
            "evidenceReadyTotal": 0,
            "missingEvidenceTotal": 0,
            "controlledCommandMissingTotal": 0,
            "readonlyStaticMissingTotal": 0,
            "manualOnlyMissingTotal": 0,
            "totalScore": 0,
            "coveredScore": 0,
            "earnedScore": 0,
            "coverageRatio": 0,
            "readyForHumanReview": False,
            "readyForApprovalRecommendation": False,
            "manualReviewRequired": applicable,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
        "items": [],
        "nextActions": ["open_review_detail_before_evidence_readiness"] if applicable else [],
        "actionGuide": {
            "component": "GradingEvidenceActionGuide",
            "status": "DETAIL_REQUIRED" if applicable else "NOT_APPLICABLE",
            "primaryAction": "open_review_detail_before_evidence_action" if applicable else "none",
            "api": {
                "method": "POST",
                "path": "/api/grading/evidence-auto",
                "body": {
                    "taskId": task.id,
                    "includeControlledCommand": False,
                    "failOnControlledUnavailable": False,
                },
            },
            "cli": f"python lab_cli.py grade evidence-auto --task-id {task.id} --include-controlled-command false",
            "reportEntry": "grading-report.html?file={reportPath}&taskId={taskId}",
            "followUp": [
                "open_review_detail",
                "open_latest_grading_report",
                "record_review_decision_note_before_manual_approve",
            ] if applicable else [],
            "safety": {
                "autoApproveAllowed": False,
                "batchStateChangeAllowed": False,
                "realPublishAllowed": False,
                "controlledCommandOptInRequired": True,
                "secretVisibleInFrontend": False,
            },
        },
        "safety": {
            "readExistingReportsOnly": True,
            "sandboxExecutedByReadiness": False,
            "contestantCodeExecutedByReadiness": False,
            "commandExecutedByReadiness": False,
            "pytestExecutedByReadiness": False,
            "notebookExecutedByReadiness": False,
            "networkAccessByReadiness": False,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
        },
    }


def _dynamic_merged_grading_evidence_review_signal(details: list[dict[str, Any]]) -> dict[str, Any]:
    items = [
        _merged_grading_evidence_summary_from_detail(detail)
        for detail in details
        if isinstance(detail.get("mergedGradingEvidence"), dict)
        and detail.get("mergedGradingEvidence", {}).get("visible") is True
    ]
    if not items:
        return _merged_grading_evidence_review_signal()

    covered_check_ids: list[str] = []
    for item in items:
        covered_check_ids.extend(str(check_id) for check_id in item.get("coveredCheckIds", []) if check_id)

    return {
        "enabled": True,
        "component": "MergedGradingEvidenceReviewSignal",
        "source": "reviewDetail.mergedGradingEvidence",
        "dynamicSource": "reviewDetail.mergedGradingEvidence",
        "fallbackSource": None,
        "sourceMode": "DYNAMIC_MERGED_GRADING_EVIDENCE",
        "route": "/review-center -> /grading/:id/report",
        "mode": "DYNAMIC_MERGED_GRADING_EVIDENCE",
        "taskTotal": len(items),
        "available": True,
        "reportTotal": sum(int(item.get("reportTotal", 0) or 0) for item in items),
        "status": "MERGED_EVIDENCE_COLLECTED",
        "artifactKind": "GRADING_EVIDENCE_MERGE",
        "latestReportType": next((item.get("reportType") for item in items if item.get("reportType")), None),
        "latestReportMode": next((item.get("reportMode") for item in items if item.get("reportMode")), None),
        "coveredCheckIds": list(dict.fromkeys(covered_check_ids)),
        "controlledDockerCheckTotal": sum(int(item.get("controlledDockerCheckTotal", 0) or 0) for item in items),
        "readonlyStaticCheckTotal": sum(int(item.get("readonlyStaticCheckTotal", 0) or 0) for item in items),
        "executed": sum(int(item.get("executed", 0) or 0) for item in items),
        "passedCheckTotal": sum(int(item.get("passedCheckTotal", 0) or 0) for item in items),
        "failedCheckTotal": sum(int(item.get("failedCheckTotal", 0) or 0) for item in items),
        "deferredCheckTotal": sum(int(item.get("deferredCheckTotal", 0) or 0) for item in items),
        "earnedScore": sum(float(item.get("earnedScore", 0) or 0) for item in items),
        "totalScore": sum(float(item.get("totalScore", 0) or 0) for item in items),
        "coverageRatio": max(float(item.get("coverageRatio", 0) or 0) for item in items),
        "checkEvidenceReviewItemTotal": sum(int(item.get("checkEvidenceReviewItemTotal", 0) or 0) for item in items),
        "manualCheckReviewTotal": sum(int(item.get("manualCheckReviewTotal", 0) or 0) for item in items),
        "autoEvidenceReportTotal": sum(1 for item in items if item.get("autoEvidenceReport") is True),
        "autoEvidenceStepTotal": sum(int(item.get("autoEvidenceStepTotal", 0) or 0) for item in items),
        "autoEvidenceWarningTotal": sum(int(item.get("autoEvidenceWarningTotal", 0) or 0) for item in items),
        "items": items,
        "recommendedAction": "review_merged_grading_evidence_before_approval",
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": False,
        "safety": {
            "source": "reviewDetail.mergedGradingEvidence.safety",
            "pageReadOnly": True,
            "mergeExecutedOnlyExistingReports": all(item["mergeExecutedOnlyExistingReports"] for item in items),
            "sandboxExecuted": any(item["sandboxExecuted"] for item in items),
            "contestantCodeExecuted": any(item["contestantCodeExecuted"] for item in items),
            "commandExecuted": any(item["commandExecuted"] for item in items),
            "pytestExecuted": any(item["pytestExecuted"] for item in items),
            "hostExecutionAllowed": False,
            "networkAllowed": any(item["networkEnabled"] for item in items),
            "secretVisibleInFrontend": False,
            "answerVisibleToCandidate": False,
            "autoApproveAllowed": False,
            "realPublishAllowed": False,
        },
    }


def _grading_evidence_readiness_signal(priority_queue: dict[str, Any]) -> dict[str, Any]:
    queue_items = priority_queue.get("items") if isinstance(priority_queue.get("items"), list) else []
    summaries = [
        item.get("gradingEvidenceReadinessSummary")
        for item in queue_items
        if isinstance(item, dict) and isinstance(item.get("gradingEvidenceReadinessSummary"), dict)
    ]
    available = [summary for summary in summaries if summary.get("available") is True]
    missing_total = sum(
        int(summary.get("summary", {}).get("missingEvidenceTotal", 0) or 0)
        for summary in available
    )
    return {
        "enabled": True,
        "component": "GradingEvidenceReadinessSignal",
        "source": "reviewTaskSummary.reviewPriorityQueue.items[].gradingEvidenceReadinessSummary",
        "mode": "GRADING_EVIDENCE_READINESS",
        "taskTotal": len(summaries),
        "availableTotal": len(available),
        "evidenceReadyTotal": sum(
            int(summary.get("summary", {}).get("evidenceReadyTotal", 0) or 0)
            for summary in available
        ),
        "missingEvidenceTotal": missing_total,
        "controlledCommandMissingTotal": sum(
            int(summary.get("summary", {}).get("controlledCommandMissingTotal", 0) or 0)
            for summary in available
        ),
        "readonlyStaticMissingTotal": sum(
            int(summary.get("summary", {}).get("readonlyStaticMissingTotal", 0) or 0)
            for summary in available
        ),
        "readyForApprovalRecommendationTotal": sum(
            1
            for summary in available
            if summary.get("summary", {}).get("readyForApprovalRecommendation") is True
        ),
        "recommendedAction": (
            "review_ready_score_and_evidence_before_approval"
            if available and missing_total == 0
            else "collect_missing_grading_evidence_before_approval"
        ),
        "items": summaries,
        "manualReviewRequired": bool(summaries),
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": False,
        "safety": {
            "readExistingReportsOnly": True,
            "sandboxExecutedByReadiness": False,
            "contestantCodeExecutedByReadiness": False,
            "commandExecutedByReadiness": False,
            "pytestExecutedByReadiness": False,
            "notebookExecutedByReadiness": False,
            "networkAccessByReadiness": False,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
        },
    }


def _notebook_evidence_review_plan() -> dict[str, Any]:
    return {
        "enabled": True,
        "component": "NotebookEvidenceReviewPlan",
        "source": "realDemoPrototype.generatedDsl.grading.spec.assessmentPlan + reviewTaskSummary.controlledDockerEvidenceReviewSignal",
        "route": "/real-demo -> /review-center -> /grading/:id/report",
        "taskId": "real_demo_grading",
        "taskType": "GRADING_GENERATION",
        "status": "NOTEBOOK_STATIC_EVIDENCE_COLLECTED",
        "sourceGradingPath": "examples/output/real-llm-grading.json",
        "staticEvidencePlanPath": "examples/output/mimo-real-demo-notebook-static-plan.json",
        "staticEvidenceReportPath": "examples/output/mimo-real-demo-notebook-static-report.json",
        "staticEvidenceSubmissionPath": "examples/submissions/real-demo-notebook",
        "remainingCheckIds": [
            "check_q2",
            "check_q3",
        ],
        "checkTypes": [
            "notebook_cell",
        ],
        "checkTotal": 2,
        "scoreTotal": 60,
        "evidenceStatus": "STATIC_NOTEBOOK_EVIDENCE_COLLECTED",
        "reviewStrategy": "STATIC_NOTEBOOK_JSON_PARSE_REVIEW",
        "executionMode": "readonly",
        "sandboxMode": "READONLY_REAL_SANDBOX_POC",
        "executed": 2,
        "passed": 2,
        "earnedScore": 60,
        "totalStaticNotebookScore": 60,
        "staticEvidenceMethod": "STATIC_NOTEBOOK_JSON_PARSE",
        "requiredReviewerActions": [
            "verify_notebook_cell_targets",
            "verify_expected_output_tokens",
            "review_static_notebook_evidence_matches_expected_tokens",
            "confirm_no_notebook_kernel_started",
        ],
        "items": [
            {
                "checkId": "check_q2",
                "type": "notebook_cell",
                "runner": "NotebookGrader",
                "score": 30,
                "inputSummary": "检查指定单元格中的文本内容是否包含类型提示相关关键词",
                "executionPlan": {
                    "strategy": "MOCK_PLAN_ONLY",
                    "action": "run_notebook_cell_and_match_output",
                    "wouldRunInsideRealSandbox": True,
                    "requiredLimits": {
                        "cpu": "50m",
                        "memory": "64Mi",
                        "timeout": "10s",
                        "network": "disabled_by_default",
                        "filesystem": "read_only",
                        "process": "none",
                    },
                },
                "reviewFocus": [
                    "confirm_notebook_cell_target_before_execution",
                    "confirm_expected_output_tokens_before_execution",
                ],
                "evidenceStatus": "STATIC_NOTEBOOK_EVIDENCE_COLLECTED",
                "staticEvidenceMethod": "STATIC_NOTEBOOK_JSON_PARSE",
                "staticEvidenceReportPath": "examples/output/mimo-real-demo-notebook-static-report.json",
                "sandboxRequiredBeforeRealExecution": True,
                "manualReviewRequired": True,
            },
            {
                "checkId": "check_q3",
                "type": "notebook_cell",
                "runner": "NotebookGrader",
                "score": 30,
                "inputSummary": "验证函数参数重命名是否正确且保持功能不变",
                "executionPlan": {
                    "strategy": "MOCK_PLAN_ONLY",
                    "action": "run_notebook_cell_and_match_output",
                    "wouldRunInsideRealSandbox": True,
                    "requiredLimits": {
                        "cpu": "100m",
                        "memory": "128Mi",
                        "timeout": "15s",
                        "network": "disabled_by_default",
                        "filesystem": "read_only",
                        "process": "none",
                    },
                },
                "reviewFocus": [
                    "confirm_notebook_cell_target_before_execution",
                    "confirm_code_pattern_expectation_before_execution",
                ],
                "evidenceStatus": "STATIC_NOTEBOOK_EVIDENCE_COLLECTED",
                "staticEvidenceMethod": "STATIC_NOTEBOOK_JSON_PARSE",
                "staticEvidenceReportPath": "examples/output/mimo-real-demo-notebook-static-report.json",
                "sandboxRequiredBeforeRealExecution": True,
                "manualReviewRequired": True,
            },
        ],
        "safety": {
            "readOnlyPlan": False,
            "readonlyStaticEvidenceCollected": True,
            "notebookKernelStarted": False,
            "notebookExecuted": False,
            "contestantCodeExecuted": False,
            "commandExecuted": False,
            "hostExecutionAllowed": False,
            "networkAllowed": False,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
        },
    }


def _task_card(detail: dict[str, Any]) -> dict[str, Any]:
    task = detail["task"]
    review_page = detail["reviewPage"]
    provider_quality_summary = _provider_quality_summary_from_detail(detail)
    return {
        "task": {
            "id": task["id"],
            "taskType": task["taskType"],
            "title": task["title"],
            "status": task["status"],
            "createdAt": task["createdAt"],
            "updatedAt": task["updatedAt"],
            "finalResultPath": task.get("finalResultPath"),
            "traceId": task["traceId"],
        },
        "reviewPolicy": detail["reviewPolicy"],
        "reviewPageSummary": {
            "dslPreview": review_page["dslPreview"],
            "riskSummary": review_page["riskSummary"],
            "actionBar": review_page["actionBar"],
            "artifactTotal": detail["summary"]["artifactTotal"],
            "workflowStepTotal": detail["summary"]["workflowStepTotal"],
            "auditEventTotal": detail["summary"]["reviewAuditEventTotal"]
            + detail["summary"]["operationAuditEventTotal"],
            "providerQualitySummary": provider_quality_summary,
        },
        "safety": detail["safety"],
    }


def _status_counts(
    store: JsonTaskStore,
    task_type: str | None,
    *,
    task_ids: set[str] | None = None,
) -> dict[str, int]:
    tasks = store.list(task_type=task_type)
    if task_ids is not None:
        tasks = [task for task in tasks if task.id in task_ids]
    return {
        status.value: sum(1 for task in tasks if task.status == status)
        for status in TaskStatus
    }


def build_teaching_package_review_summary(
    store: JsonTaskStore,
    workflow_run_id: str,
) -> dict[str, Any] | None:
    workflow_run = store.get_workflow_run(workflow_run_id)
    if workflow_run is None:
        return None

    artifact_payloads = [
        artifact.to_dict()
        for artifact in store.list_artifacts(workflow_run_id=workflow_run_id)
    ]
    core_artifact_kinds = {
        spec["artifactKind"] for spec in TEACHING_PACKAGE_ARTIFACT_SPECS.values()
    }
    artifacts_by_kind = {
        artifact["kind"]: artifact
        for artifact in artifact_payloads
        if artifact.get("kind") in core_artifact_kinds
    }
    ppt_present = any(artifact.get("kind") == "PPT_DSL" for artifact in artifact_payloads)
    metadata_profile = next(
        (
            str(artifact.get("metadata", {}).get("artifactProfile"))
            for artifact in artifact_payloads
            if artifact.get("metadata", {}).get("artifactProfile")
        ),
        None,
    )
    artifact_profile = metadata_profile or ("legacy-all" if ppt_present else "teaching-core")
    missing_artifact_kinds = [
        spec["artifactKind"]
        for spec in TEACHING_PACKAGE_ARTIFACT_SPECS.values()
        if spec["artifactKind"] not in artifacts_by_kind
    ]
    is_teaching_core = (
        workflow_run.workflowId == "phase2_content_generation"
        and artifact_profile == "teaching-core"
        and not ppt_present
        and not missing_artifact_kinds
    )
    if not is_teaching_core:
        return {
            "component": "TeachingPackageReviewSummary",
            "available": False,
            "unavailableReason": "NOT_TEACHING_CORE_WORKFLOW_RUN",
            "workflowRunId": workflow_run_id,
            "workflowId": workflow_run.workflowId,
            "artifactProfile": artifact_profile,
            "missingArtifactKinds": missing_artifact_kinds,
            "pptArtifactPresent": ppt_present,
            "exportReady": False,
            "safety": {
                "readOnlySummary": True,
                "batchStateChangeAllowed": False,
                "autoApproveAllowed": False,
                "autoPublishAllowed": False,
                "realPublishAllowed": False,
            },
        }

    artifact_summaries: dict[str, dict[str, Any]] = {}
    statuses: list[str] = []
    schema_validated_total = 0
    schema_failed_total = 0
    content_quality_blocking_total = 0
    candidate_safety: dict[str, Any] = {
        "answersRemovedFromSafePreview": False,
        "answerVisibleToCandidate": False,
        "gradingRefVisibleToCandidate": False,
        "candidateSafe": False,
    }

    for kind, spec in TEACHING_PACKAGE_ARTIFACT_SPECS.items():
        artifact = artifacts_by_kind[spec["artifactKind"]]
        task_id = str(artifact.get("taskId") or "")
        task = store.get(task_id) if task_id else None
        detail = build_review_detail(store, task_id) if task is not None else None
        preview = (
            detail.get("reviewPage", {}).get("dslPreview", {})
            if isinstance(detail, dict)
            else {}
        )
        content_quality = (
            detail.get("contentQualitySummary", {})
            if isinstance(detail, dict)
            else {}
        )
        schema_validated = (
            preview.get("schemaValidated") is True
            or artifact.get("metadata", {}).get("schemaValidated") is True
        )
        schema_error_total = len(preview.get("schemaValidationErrors", []))
        blocking_issue_total = int(content_quality.get("blockingIssueTotal") or 0)
        status = task.status.value if task is not None else "MISSING"
        statuses.append(status)
        schema_validated_total += 1 if schema_validated else 0
        schema_failed_total += 0 if schema_validated else 1
        content_quality_blocking_total += blocking_issue_total
        artifact_summaries[kind] = {
            "kind": kind,
            "label": spec["label"],
            "artifactKind": spec["artifactKind"],
            "artifactId": artifact.get("id"),
            "taskId": task_id or None,
            "taskType": task.taskType if task is not None else spec["taskType"],
            "status": status,
            "dslPath": artifact.get("path"),
            "schemaValidated": schema_validated,
            "schemaValidationErrorTotal": schema_error_total,
            "contentQuality": {
                "available": content_quality.get("available") is True,
                "status": content_quality.get("decisionStatus") or content_quality.get("status"),
                "readyForManualReview": content_quality.get("readyForManualReview") is True,
                "blockingIssueTotal": blocking_issue_total,
                "warningIssueTotal": int(content_quality.get("warningIssueTotal") or 0),
                "recommendedAction": content_quality.get("recommendedAction"),
            },
            "reviewEntry": {
                "path": "/review-center.html",
                "taskId": task_id or None,
                "workflowRunId": workflow_run_id,
            },
            "reviewActions": {
                "approve": {
                    "method": "POST",
                    "path": f"/api/ai-tasks/{task_id}/approve" if task_id else None,
                    "enabled": status == TaskStatus.WAITING_REVIEW.value,
                },
                "reject": {
                    "method": "POST",
                    "path": f"/api/ai-tasks/{task_id}/reject" if task_id else None,
                    "enabled": status == TaskStatus.WAITING_REVIEW.value,
                    "reasonRequired": True,
                },
            },
        }
        if kind == "exam":
            preview_safety = preview.get("candidateSafety", {})
            candidate_safety = {
                "answersRemovedFromSafePreview": preview_safety.get("answersRemovedFromSafePreview") is True,
                "answerVisibleToCandidate": preview_safety.get("answerVisibleToCandidate") is True,
                "gradingRefVisibleToCandidate": preview_safety.get("gradingRefVisibleToCandidate") is True,
                "candidateSafe": (
                    preview_safety.get("answersRemovedFromSafePreview") is True
                    and preview_safety.get("answerVisibleToCandidate") is False
                    and preview_safety.get("gradingRefVisibleToCandidate") is False
                ),
            }

    progress = {
        "total": len(TEACHING_PACKAGE_ARTIFACT_SPECS),
        "waitingReview": statuses.count(TaskStatus.WAITING_REVIEW.value),
        "approved": statuses.count(TaskStatus.APPROVED.value),
        "rejected": statuses.count(TaskStatus.REJECTED.value),
        "missing": statuses.count("MISSING"),
    }
    if progress["rejected"]:
        package_status = "NEEDS_REVISION"
        next_action = "revise_rejected_artifacts"
    elif progress["approved"] == progress["total"]:
        package_status = "APPROVED"
        next_action = "export_teaching_package"
    else:
        package_status = "WAITING_REVIEW"
        next_action = "review_remaining_artifacts"

    return {
        "component": "TeachingPackageReviewSummary",
        "available": True,
        "workflowRunId": workflow_run_id,
        "workflowId": workflow_run.workflowId,
        "artifactProfile": "teaching-core",
        "sourceRef": workflow_run.inputRef,
        "status": package_status,
        "artifacts": artifact_summaries,
        "candidateSafeExamPreview": candidate_safety,
        "validation": {
            "total": len(TEACHING_PACKAGE_ARTIFACT_SPECS),
            "schemaValidatedTotal": schema_validated_total,
            "schemaFailedTotal": schema_failed_total,
            "allSchemaValidated": schema_validated_total == len(TEACHING_PACKAGE_ARTIFACT_SPECS),
            "contentQualityBlockingIssueTotal": content_quality_blocking_total,
        },
        "reviewProgress": progress,
        "nextAction": next_action,
        "exportReady": (
            package_status == "APPROVED"
            and schema_failed_total == 0
            and candidate_safety["candidateSafe"] is True
        ),
        "presentationDeckGeneration": {
            "enabled": (
                package_status == "APPROVED"
                and schema_failed_total == 0
                and candidate_safety["candidateSafe"] is True
            ),
            "method": "POST",
            "path": "/api/teaching-presentations/generate",
            "defaultSlideCount": 6,
            "minimumSlideCount": 5,
            "maximumSlideCount": 8,
            "createsChildWorkflowRun": True,
        },
        "reviewEntry": {
            "path": "/review-center.html",
            "workflowRunId": workflow_run_id,
        },
        "safety": {
            "readOnlySummary": True,
            "reviewActionsArePerTask": True,
            "rejectRequiresReason": True,
            "batchStateChangeAllowed": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "answerVisibleToCandidate": False,
            "gradingRefVisibleToCandidate": False,
            "realPublishAllowed": False,
        },
    }


def build_presentation_deck_review_summary(
    store: JsonTaskStore,
    workflow_run_id: str,
) -> dict[str, Any] | None:
    workflow_run = store.get_workflow_run(workflow_run_id)
    if workflow_run is None or workflow_run.workflowId != "teaching_presentation_generation":
        return None

    artifacts = store.list_artifacts(workflow_run_id=workflow_run_id)
    ppt_dsl = next((artifact for artifact in artifacts if artifact.kind.value == "PPT_DSL"), None)
    pptx = next((artifact for artifact in artifacts if artifact.kind.value == "PPTX_FILE"), None)
    task_id = str((pptx or ppt_dsl).taskId or "") if (pptx or ppt_dsl) else ""
    task = store.get(task_id) if task_id else None
    if ppt_dsl is None or pptx is None or task is None:
        return {
            "component": "PresentationDeckReviewSummary",
            "available": False,
            "workflowRunId": workflow_run_id,
            "sourceWorkflowRunId": workflow_run.inputRef,
            "unavailableReason": "PRESENTATION_ARTIFACTS_INCOMPLETE",
            "approveReady": False,
            "downloadReady": False,
            "downloadBlockedReason": "PRESENTATION_ARTIFACTS_INCOMPLETE",
        }

    metadata = pptx.metadata if isinstance(pptx.metadata, dict) else {}
    dsl_metadata = ppt_dsl.metadata if isinstance(ppt_dsl.metadata, dict) else {}
    slide_previews = metadata.get("slidePreviews")
    if not isinstance(slide_previews, list):
        preview = metadata.get("preview", {})
        slide_previews = preview.get("slidePreviews", []) if isinstance(preview, dict) else []
    detail = build_review_detail(store, task.id)
    page_review = detail.get("pptPageReview", {}) if isinstance(detail, dict) else {}
    page_summary = page_review.get("pageReviewSummary", {}) if isinstance(page_review, dict) else {}
    artifact_id = pptx.id
    safe_previews = []
    for position, item in enumerate(slide_previews, start=1):
        if not isinstance(item, dict):
            continue
        index = int(item.get("index") or position)
        safe_previews.append(
            {
                "index": index,
                "id": item.get("id") or f"slide_{index}",
                "title": item.get("title") or f"Slide {index}",
                "imageUrl": f"/api/ppt-artifacts/{artifact_id}/previews/{index}",
                "reviewStatus": item.get("reviewStatus") or "NEEDS_REVIEW",
                "manualComment": item.get("manualComment") or {},
                "qaSignals": item.get("qaSignals") or {},
            }
        )

    contact_sheet = metadata.get("contactSheet")
    contact_sheet_available = isinstance(contact_sheet, dict) and bool(contact_sheet.get("path"))
    if not contact_sheet_available:
        contact_sheet_available = bool(metadata.get("contactSheetPath"))
    page_review_approved = (
        bool(safe_previews)
        and page_summary.get("status") == "APPROVED"
        and int(page_summary.get("approved") or 0) == len(safe_previews)
    )
    download_ready = task.status == TaskStatus.APPROVED
    quality_report = metadata.get("qualityReport") if isinstance(metadata.get("qualityReport"), dict) else {}
    return {
        "component": "PresentationDeckReviewSummary",
        "available": True,
        "workflowRunId": workflow_run_id,
        "sourceWorkflowRunId": metadata.get("sourceWorkflowRunId") or workflow_run.inputRef,
        "taskId": task.id,
        "status": task.status.value,
        "slideTotal": len(safe_previews),
        "schemaValidated": dsl_metadata.get("schemaValidated") is True,
        "qualityReport": quality_report,
        "pageReviewSummary": page_summary,
        "slidePreviews": safe_previews,
        "contactSheetUrl": (
            f"/api/ppt-artifacts/{artifact_id}/contact-sheet" if contact_sheet_available else None
        ),
        "pptxArtifact": {
            "artifactId": artifact_id,
            "fileName": Path(pptx.path).name,
            "sizeBytes": int(metadata.get("sizeBytes") or metadata.get("bytes") or 0),
            "sha256": metadata.get("sha256"),
            "downloadUrl": f"/api/ppt-artifacts/{artifact_id}/download",
        },
        "approveReady": task.status == TaskStatus.WAITING_REVIEW and page_review_approved,
        "downloadReady": download_ready,
        "downloadBlockedReason": None if download_ready else "TASK_NOT_APPROVED",
        "reviewActions": {
            "pageUpdatePath": f"/api/review-tasks/{task.id}/ppt-page-review-status",
            "approvePath": f"/api/ai-tasks/{task.id}/approve",
            "rejectPath": f"/api/ai-tasks/{task.id}/reject",
            "rejectRequiresReason": True,
        },
        "safety": {
            "localOnly": True,
            "candidateSafe": True,
            "answerVisibleToCandidate": False,
            "gradingRefVisibleToCandidate": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        },
    }


def _assessment_plan_signal(detail: dict[str, Any]) -> dict[str, Any]:
    summary = detail.get("assessmentPlan", {}).get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    mock_statuses = summary.get("mockEvidenceStatuses") or []
    risk_levels = summary.get("riskLevels") or []
    return {
        "riskLevel": risk_levels[0] if risk_levels else "high",
        "mockEvidenceStatus": mock_statuses[0] if mock_statuses else "MOCK_EVIDENCE_NOT_COLLECTED",
        "assessmentPlanAlignedWithChecks": bool(summary.get("alignedWithChecks", False)),
    }


def _manual_review_checklist_summary(detail: dict[str, Any]) -> dict[str, Any]:
    task = detail["task"]
    checklist_model = detail.get("assessmentPlan", {}).get("manualReviewChecklist", {})
    if not isinstance(checklist_model, dict):
        checklist_model = {}
    checklist = checklist_model.get("checklist")
    if not isinstance(checklist, list):
        checklist = []
    operator_decision = checklist_model.get("operatorDecision")
    if not isinstance(operator_decision, dict):
        operator_decision = {}

    checklist_ids = [
        item.get("id")
        for item in checklist
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    next_review_ids = [
        item.get("id")
        for item in checklist
        if isinstance(item, dict)
        and item.get("status") == "NEEDS_HUMAN_REVIEW"
        and isinstance(item.get("id"), str)
    ]
    enabled = bool(checklist_model.get("enabled")) and bool(checklist)
    return {
        "enabled": enabled,
        "source": "reviewDetail.assessmentPlan.manualReviewChecklist",
        "taskId": checklist_model.get("taskId") or task["id"],
        "primaryReviewFocus": checklist_model.get("primaryReviewFocus"),
        "status": checklist_model.get("status") or ("NEEDS_HUMAN_REVIEW" if enabled else "NOT_AVAILABLE"),
        "checklistTotal": len(checklist),
        "matchedTotal": sum(
            1
            for item in checklist
            if isinstance(item, dict) and item.get("matched") is True
        ),
        "needsHumanReviewTotal": len(next_review_ids),
        "checklistIds": checklist_ids,
        "nextReviewChecklistIds": next_review_ids,
        "operatorDecision": {
            "manualDecisionRequired": bool(operator_decision.get("manualDecisionRequired", enabled)),
            "approveAllowedAfterChecklist": bool(operator_decision.get("approveAllowedAfterChecklist", False)),
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realSandboxRunEnabled": False,
            "contestantCodeExecuted": False,
            "realPublishAllowed": False,
        },
    }


def _candidate_safe_exam_signal(detail: dict[str, Any]) -> dict[str, Any]:
    quality_signals = detail.get("reviewPage", {}).get("qualitySignals", {})
    coverage = quality_signals.get("coverage", {}) if isinstance(quality_signals, dict) else {}
    question_coverage = coverage.get("questionGradingRefCoverage", {}) if isinstance(coverage, dict) else {}
    score_coverage = coverage.get("scoreCoverage", {}) if isinstance(coverage, dict) else {}
    return {
        "candidateSafeExamPreviewAnswersRemoved": True,
        "questionGradingRefCoverageStatus": question_coverage.get("status", "MATCHED"),
        "scoreCoverageStatus": score_coverage.get("status", "MATCHED"),
    }


def _lab_quality_signal(detail: dict[str, Any]) -> dict[str, Any]:
    quality_signals = detail.get("reviewPage", {}).get("qualitySignals", {})
    lab_signals = quality_signals.get("lab", {}) if isinstance(quality_signals, dict) else {}
    matching = lab_signals.get("matching", {}) if isinstance(lab_signals, dict) else {}
    return {
        "qualitySignalStatus": matching.get("status", "NEEDS_REVIEW"),
    }


def _ppt_page_review_signal(detail: dict[str, Any]) -> dict[str, Any]:
    page_review = detail.get("pptPageReview", {})
    if not isinstance(page_review, dict):
        page_review = {}
    summary = page_review.get("pageReviewSummary", {})
    if not isinstance(summary, dict):
        summary = {}
    return {
        "pageReviewStatus": summary.get("status", "NEEDS_REVIEW"),
        "pageReviewTotal": summary.get("total", 0),
        "pageReviewNeedsReview": summary.get("needsReview", 0),
        "pageReviewReviseRequired": summary.get("reviseRequired", 0),
        "qaSignalStatus": summary.get("qaSignalStatus", "NEEDS_REVIEW"),
        "autoApproveAllowed": False,
    }


def _provider_quality_summary_from_detail(detail: dict[str, Any]) -> dict[str, Any]:
    task = detail["task"]
    provider_summary = detail.get("reviewPage", {}).get("providerSummary", {})
    if not isinstance(provider_summary, dict):
        provider_summary = {}
    quality_summary = provider_summary.get("qualitySummary")
    if not isinstance(quality_summary, dict):
        quality_summary = {}
    usage = provider_summary.get("usage") if isinstance(provider_summary.get("usage"), dict) else {}
    calls = provider_summary.get("calls") if isinstance(provider_summary.get("calls"), list) else []
    available = bool(quality_summary.get("available")) if "available" in quality_summary else bool(quality_summary)

    return {
        "available": available,
        "source": "reviewDetail.reviewPage.providerSummary.qualitySummary",
        "callSource": "reviewDetail.reviewPage.providerSummary.calls[].qualitySummary",
        "taskId": task["id"],
        "taskType": task.get("taskType"),
        "realLlmCalled": bool(provider_summary.get("realLlmCalled", False)),
        "providerAdapters": provider_summary.get("providerAdapters", []),
        "providerIds": provider_summary.get("providerIds", []),
        "models": provider_summary.get("models", []),
        "apiSurfaces": provider_summary.get("apiSurfaces", []),
        "responseIds": provider_summary.get("responseIds", []),
        "providerCallAuditEventIds": provider_summary.get("providerCallAuditEventIds", []),
        "requestCount": len(calls),
        "totalTokens": usage.get("totalTokens", 0),
        "readyForReview": bool(quality_summary.get("readyForReview", False)),
        "needsManualReview": bool(quality_summary.get("needsManualReview", available)),
        "normalizationApplied": bool(quality_summary.get("normalizationApplied", False)),
        "normalizationPatchCount": quality_summary.get("normalizationPatchCount", 0),
        "normalizationPatches": quality_summary.get("normalizationPatches", []),
        "schemaRepairAttempted": bool(quality_summary.get("schemaRepairAttempted", False)),
        "schemaRepairApplied": bool(quality_summary.get("schemaRepairApplied", False)),
        "schemaRepairErrorCount": quality_summary.get("schemaRepairErrorCount", 0),
        "issueCount": quality_summary.get("issueCount", 0),
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
    }


def _light_provider_quality_summary(task: Any) -> dict[str, Any]:
    return {
        "available": False,
        "source": "reviewTaskSummary.detailMode=light",
        "callSource": "reviewTaskSummary.detailMode=light",
        "taskId": task.id,
        "taskType": task.taskType,
        "realLlmCalled": False,
        "providerAdapters": [],
        "providerIds": [],
        "models": [],
        "apiSurfaces": [],
        "responseIds": [],
        "providerCallAuditEventIds": [],
        "requestCount": 0,
        "totalTokens": 0,
        "readyForReview": False,
        "needsManualReview": True,
        "normalizationApplied": False,
        "normalizationPatchCount": 0,
        "normalizationPatches": [],
        "schemaRepairAttempted": False,
        "schemaRepairApplied": False,
        "schemaRepairErrorCount": 0,
        "issueCount": 0,
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
    }


def _light_manual_review_checklist_summary(task: Any) -> dict[str, Any]:
    return {
        "enabled": False,
        "source": "reviewTaskSummary.detailMode=light",
        "taskId": task.id,
        "primaryReviewFocus": None,
        "status": "DETAIL_REQUIRED",
        "checklistTotal": 0,
        "matchedTotal": 0,
        "needsHumanReviewTotal": 0,
        "checklistIds": [],
        "nextReviewChecklistIds": [],
        "operatorDecision": {
            "manualDecisionRequired": True,
            "approveAllowedAfterChecklist": False,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realSandboxRunEnabled": False,
            "contestantCodeExecuted": False,
            "realPublishAllowed": False,
        },
    }


def _light_task_card(task: Any) -> dict[str, Any]:
    return {
        "task": {
            "id": task.id,
            "taskType": task.taskType,
            "title": task.title,
            "status": task.status.value,
            "createdAt": task.createdAt,
            "updatedAt": task.updatedAt,
            "finalResultPath": task.finalResultPath,
            "traceId": task.traceId,
        },
        "reviewPolicy": {
            "detailMode": "LIGHT",
            "manualReviewRequired": True,
            "detailApi": "GET /api/review-tasks/{id}",
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
        },
        "reviewPageSummary": {
            "detailMode": "LIGHT",
            "dslPreview": {"available": False, "reason": "detailMode=light"},
            "riskSummary": {"manualReviewRequired": True, "detailRequired": True},
            "actionBar": {
                "approveEnabled": False,
                "rejectEnabled": False,
                "publishEnabled": False,
                "reason": "Open review detail before making a decision.",
            },
            "artifactTotal": 0,
            "workflowStepTotal": 0,
            "auditEventTotal": 0,
            "providerQualitySummary": _light_provider_quality_summary(task),
        },
        "safety": build_review_safety(),
    }


def _light_review_priority_item(task: Any) -> dict[str, Any]:
    base = {
        "taskId": task.id,
        "taskType": task.taskType,
        "title": task.title,
        "status": task.status.value,
        "providerQualitySummary": _light_provider_quality_summary(task),
        "manualReviewChecklistSummary": _light_manual_review_checklist_summary(task),
    }
    if task.taskType == "GRADING_GENERATION":
        return {
            **base,
            "priority": "URGENT",
            "reasonCode": "HIGH_RISK_MOCK_EVIDENCE_REQUIRED",
            "riskLevel": "high",
            "mockEvidenceStatus": "DETAIL_REQUIRED",
            "assessmentPlanAlignedWithChecks": False,
            "gradingEvidenceReadinessSummary": _light_grading_evidence_readiness_summary(task),
            "preApproveReviewCheck": _light_pre_approve_review_check_summary(task),
            "recommendedAction": "open_review_detail_before_approval",
        }
    if task.taskType == "EXAM_GENERATION":
        return {
            **base,
            "priority": "HIGH",
            "reasonCode": "CANDIDATE_SAFE_EXAM_PREVIEW",
            "candidateSafeExamPreviewAnswersRemoved": True,
            "questionGradingRefCoverageStatus": "DETAIL_REQUIRED",
            "scoreCoverageStatus": "DETAIL_REQUIRED",
            "recommendedAction": "open_review_detail_before_approval",
        }
    if task.taskType == "LAB_GENERATION":
        return {
            **base,
            "priority": "NORMAL",
            "reasonCode": "LAB_QUALITY_NEEDS_REVIEW",
            "qualitySignalStatus": "DETAIL_REQUIRED",
            "recommendedAction": "open_review_detail_before_approval",
        }
    if task.taskType == "PPT_GENERATION":
        return {
            **base,
            "priority": "NORMAL",
            "reasonCode": "PPT_SLIDE_PLAN_REVIEW",
            "pageReviewStatus": "DETAIL_REQUIRED",
            "pageReviewTotal": 0,
            "pageReviewNeedsReview": 0,
            "pageReviewReviseRequired": 0,
            "qaSignalStatus": "DETAIL_REQUIRED",
            "autoApproveAllowed": False,
            "recommendedAction": "open_review_detail_before_approval",
        }
    return {
        **base,
        "priority": "LOW",
        "reasonCode": "GENERAL_REVIEW_REQUIRED",
        "recommendedAction": "open_review_detail_before_approval",
    }


def _light_review_priority_queue(tasks: list[Any]) -> dict[str, Any]:
    items = [_light_review_priority_item(task) for task in tasks]
    items.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(item.get("priority", "LOW"), 99),
            TASK_TYPE_PRIORITY.get(item.get("taskType"), 99),
            item.get("taskId") or "",
        )
    )
    ranked_items = [{"rank": index, **item} for index, item in enumerate(items, start=1)]
    return {
        "enabled": True,
        "source": "reviewTaskSummary.tasks(detailMode=light)",
        "sortPolicy": [
            "taskTypePriority=GRADING_GENERATION/EXAM_GENERATION/LAB_GENERATION/PPT_GENERATION",
            "openDetailBeforeReviewDecision=true",
        ],
        "summary": {
            "queueTotal": len(ranked_items),
            "urgentTotal": sum(1 for item in ranked_items if item["priority"] == "URGENT"),
            "highTotal": sum(1 for item in ranked_items if item["priority"] == "HIGH"),
            "normalTotal": sum(1 for item in ranked_items if item["priority"] == "NORMAL"),
            "lowTotal": sum(1 for item in ranked_items if item["priority"] == "LOW"),
            "manualReviewChecklistTaskTotal": 0,
            "manualReviewChecklistNeedsHumanReviewTotal": 0,
            "providerQualityAvailableTotal": 0,
            "providerQualityReadyForReviewTotal": 0,
            "preApproveReviewCheckTaskTotal": sum(
                1 for item in ranked_items if isinstance(item.get("preApproveReviewCheck"), dict)
            ),
            "preApproveReviewCheckWarningTotal": sum(
                item.get("preApproveReviewCheck", {}).get("summary", {}).get("warningTotal", 0)
                for item in ranked_items
                if isinstance(item.get("preApproveReviewCheck"), dict)
            ),
            "gradingEvidenceReadinessTaskTotal": sum(
                1 for item in ranked_items if isinstance(item.get("gradingEvidenceReadinessSummary"), dict)
            ),
            "gradingEvidenceReadyTotal": sum(
                item.get("gradingEvidenceReadinessSummary", {}).get("summary", {}).get("evidenceReadyTotal", 0)
                for item in ranked_items
                if isinstance(item.get("gradingEvidenceReadinessSummary"), dict)
            ),
            "gradingEvidenceMissingTotal": sum(
                item.get("gradingEvidenceReadinessSummary", {}).get("summary", {}).get("missingEvidenceTotal", 0)
                for item in ranked_items
                if isinstance(item.get("gradingEvidenceReadinessSummary"), dict)
            ),
            "detailMode": "LIGHT",
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
        },
        "items": ranked_items,
    }


def _light_provider_quality_task_signal(tasks: list[Any]) -> dict[str, Any]:
    return {
        "enabled": True,
        "source": "reviewTaskSummary.detailMode=light",
        "callSource": "reviewTaskSummary.detailMode=light",
        "taskTotal": len(tasks),
        "available": False,
        "availableTotal": 0,
        "realLlmCalledTotal": 0,
        "readyForReviewTotal": 0,
        "needsManualReviewTotal": len(tasks),
        "normalizationAppliedTotal": 0,
        "normalizationPatchTotal": 0,
        "schemaRepairAttemptedTotal": 0,
        "schemaRepairAppliedTotal": 0,
        "schemaRepairErrorTotal": 0,
        "issueTotal": 0,
        "requestTotal": 0,
        "totalTokens": 0,
        "items": [_light_provider_quality_summary(task) for task in tasks],
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
    }


def _review_priority_item(detail: dict[str, Any]) -> dict[str, Any]:
    task = detail["task"]
    task_type = task.get("taskType")
    provider_quality_summary = _provider_quality_summary_from_detail(detail)
    base = {
        "taskId": task["id"],
        "taskType": task_type,
        "title": task.get("title"),
        "status": task.get("status"),
        "providerQualitySummary": provider_quality_summary,
    }
    if task_type == "GRADING_GENERATION":
        controlled_evidence_summary = _controlled_grading_evidence_summary_from_detail(detail)
        merged_evidence_summary = _merged_grading_evidence_summary_from_detail(detail)
        grading_evidence_readiness_summary = _grading_evidence_readiness_summary_from_detail(detail)
        reason_code = (
            "MERGED_GRADING_EVIDENCE_REVIEW_REQUIRED"
            if merged_evidence_summary["available"]
            else "CONTROLLED_DOCKER_EVIDENCE_REVIEW_REQUIRED"
            if controlled_evidence_summary["available"]
            else "HIGH_RISK_MOCK_EVIDENCE_REQUIRED"
        )
        recommended_action = (
            "review_merged_grading_evidence_before_approval"
            if merged_evidence_summary["available"]
            else "review_controlled_docker_evidence_before_approval"
            if controlled_evidence_summary["available"]
            else "review_assessment_plan_before_approval"
        )
        return {
            **base,
            "priority": "URGENT",
            "reasonCode": reason_code,
            **_assessment_plan_signal(detail),
            "manualReviewChecklistSummary": _manual_review_checklist_summary(detail),
            "controlledGradingEvidenceSummary": controlled_evidence_summary,
            "mergedGradingEvidenceSummary": merged_evidence_summary,
            "gradingEvidenceReadinessSummary": grading_evidence_readiness_summary,
            "preApproveReviewCheck": _pre_approve_review_check_summary_from_detail(detail),
            "recommendedAction": recommended_action,
        }
    if task_type == "EXAM_GENERATION":
        return {
            **base,
            "priority": "HIGH",
            "reasonCode": "CANDIDATE_SAFE_EXAM_PREVIEW",
            **_candidate_safe_exam_signal(detail),
            "manualReviewChecklistSummary": _manual_review_checklist_summary(detail),
            "recommendedAction": "verify_candidate_preview_and_grading_refs",
        }
    if task_type == "LAB_GENERATION":
        return {
            **base,
            "priority": "NORMAL",
            "reasonCode": "LAB_QUALITY_NEEDS_REVIEW",
            **_lab_quality_signal(detail),
            "manualReviewChecklistSummary": _manual_review_checklist_summary(detail),
            "recommendedAction": "review_generation_profile_and_material_coverage",
        }
    if task_type == "PPT_GENERATION":
        return {
            **base,
            "priority": "NORMAL",
            "reasonCode": "PPT_SLIDE_PLAN_REVIEW",
            **_ppt_page_review_signal(detail),
            "manualReviewChecklistSummary": _manual_review_checklist_summary(detail),
            "recommendedAction": "review_ppt_pages_before_approval",
        }
    if detail.get("highRiskIntent"):
        intent = detail["highRiskIntent"]
        return {
            **base,
            "priority": "URGENT",
            "reasonCode": "HIGH_RISK_MCP_INTENT_REVIEW",
            "riskLevel": intent.get("riskLevel"),
            "manualReviewChecklistSummary": _manual_review_checklist_summary(detail),
            "recommendedAction": "review_high_risk_intent_before_disposition",
        }
    return {
        **base,
        "priority": "LOW",
        "reasonCode": "GENERAL_REVIEW_REQUIRED",
        "manualReviewChecklistSummary": _manual_review_checklist_summary(detail),
        "recommendedAction": "review_task_detail",
    }


def _review_priority_queue(details: list[dict[str, Any]]) -> dict[str, Any]:
    items = [_review_priority_item(detail) for detail in details]
    items.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(item.get("priority", "LOW"), 99),
            TASK_TYPE_PRIORITY.get(item.get("taskType"), 99),
            item.get("taskId") or "",
        )
    )
    ranked_items = [
        {
            "rank": index,
            **item,
        }
        for index, item in enumerate(items, start=1)
    ]
    return {
        "enabled": True,
        "source": "reviewTaskSummary.items + reviewDetail.qualitySignals + reviewDetail.assessmentPlan + reviewDetail.assessmentPlan.manualReviewChecklist",
        "sortPolicy": [
            "riskLevel=high",
            "mockEvidenceStatus=MOCK_EVIDENCE_NOT_COLLECTED",
            "manualReviewChecklist.status=NEEDS_HUMAN_REVIEW",
            "candidateSafeExamPreview.answersRemoved=true",
            "qualitySignalStatus=NEEDS_REVIEW",
            "taskTypePriority=GRADING_GENERATION/EXAM_GENERATION/LAB_GENERATION/PPT_GENERATION",
        ],
        "summary": {
            "queueTotal": len(ranked_items),
            "urgentTotal": sum(1 for item in ranked_items if item["priority"] == "URGENT"),
            "highTotal": sum(1 for item in ranked_items if item["priority"] == "HIGH"),
            "normalTotal": sum(1 for item in ranked_items if item["priority"] == "NORMAL"),
            "lowTotal": sum(1 for item in ranked_items if item["priority"] == "LOW"),
            "manualReviewChecklistTaskTotal": sum(
                1
                for item in ranked_items
                if item["manualReviewChecklistSummary"]["enabled"] is True
            ),
            "manualReviewChecklistNeedsHumanReviewTotal": sum(
                item["manualReviewChecklistSummary"]["needsHumanReviewTotal"]
                for item in ranked_items
            ),
            "providerQualityAvailableTotal": sum(
                1
                for item in ranked_items
                if item["providerQualitySummary"]["available"] is True
            ),
            "providerQualityReadyForReviewTotal": sum(
                1
                for item in ranked_items
                if item["providerQualitySummary"]["readyForReview"] is True
            ),
            "preApproveReviewCheckTaskTotal": sum(
                1 for item in ranked_items if isinstance(item.get("preApproveReviewCheck"), dict)
            ),
            "preApproveReviewCheckWarningTotal": sum(
                item.get("preApproveReviewCheck", {}).get("summary", {}).get("warningTotal", 0)
                for item in ranked_items
                if isinstance(item.get("preApproveReviewCheck"), dict)
            ),
            "gradingEvidenceReadinessTaskTotal": sum(
                1 for item in ranked_items if isinstance(item.get("gradingEvidenceReadinessSummary"), dict)
            ),
            "gradingEvidenceReadyTotal": sum(
                item.get("gradingEvidenceReadinessSummary", {}).get("summary", {}).get("evidenceReadyTotal", 0)
                for item in ranked_items
                if isinstance(item.get("gradingEvidenceReadinessSummary"), dict)
            ),
            "gradingEvidenceMissingTotal": sum(
                item.get("gradingEvidenceReadinessSummary", {}).get("summary", {}).get("missingEvidenceTotal", 0)
                for item in ranked_items
                if isinstance(item.get("gradingEvidenceReadinessSummary"), dict)
            ),
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
        },
        "items": ranked_items,
    }


def _pre_approve_review_check_signal(priority_queue: dict[str, Any]) -> dict[str, Any]:
    queue_items = priority_queue.get("items") if isinstance(priority_queue.get("items"), list) else []
    checks = [
        item.get("preApproveReviewCheck")
        for item in queue_items
        if isinstance(item, dict) and isinstance(item.get("preApproveReviewCheck"), dict)
    ]
    applicable = [check for check in checks if check.get("applicable") is True]
    return {
        "enabled": True,
        "component": "PreApproveReviewCheckSignal",
        "source": "reviewTaskSummary.reviewPriorityQueue.items[].preApproveReviewCheck",
        "taskTotal": len(checks),
        "applicableTotal": len(applicable),
        "readyForHumanApproveTotal": sum(
            1 for check in applicable if check.get("status") == "READY_FOR_HUMAN_APPROVE"
        ),
        "approveAllowedWithWarningsTotal": sum(
            1 for check in applicable if check.get("status") == "APPROVE_ALLOWED_WITH_WARNINGS"
        ),
        "evidenceReadyTotal": sum(
            1 for check in applicable if check.get("summary", {}).get("evidenceReady") is True
        ),
        "reviewDecisionNoteRecordedTotal": sum(
            1
            for check in applicable
            if check.get("summary", {}).get("reviewDecisionNoteRecorded") is True
        ),
        "warningTotal": sum(
            int(check.get("summary", {}).get("warningTotal", 0) or 0)
            for check in applicable
        ),
        "approvalStillAllowedTotal": sum(
            1 for check in applicable if check.get("approvalStillAllowed") is True
        ),
        "blockingTotal": sum(1 for check in applicable if check.get("blocking") is True),
        "items": checks,
        "recommendedAction": "review_pre_approve_warnings_before_manual_approve",
        "manualReviewRequired": bool(applicable),
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": False,
        "safety": {
            "readOnly": True,
            "statusChangeBlocked": False,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "realPublishAllowed": False,
            "realPublish": False,
        },
    }


def _provider_quality_task_signal(details: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = [_provider_quality_summary_from_detail(detail) for detail in details]
    available = [summary for summary in summaries if summary["available"] is True]

    def int_total(field: str) -> int:
        return sum(
            int(summary.get(field))
            for summary in available
            if isinstance(summary.get(field), int)
        )

    return {
        "enabled": True,
        "source": "reviewDetail.reviewPage.providerSummary.qualitySummary",
        "callSource": "reviewDetail.reviewPage.providerSummary.calls[].qualitySummary",
        "taskTotal": len(summaries),
        "available": bool(available),
        "availableTotal": len(available),
        "realLlmCalledTotal": sum(1 for summary in summaries if summary["realLlmCalled"] is True),
        "readyForReviewTotal": sum(1 for summary in available if summary["readyForReview"] is True),
        "needsManualReviewTotal": sum(1 for summary in available if summary["needsManualReview"] is True),
        "normalizationAppliedTotal": sum(
            1 for summary in available if summary["normalizationApplied"] is True
        ),
        "normalizationPatchTotal": int_total("normalizationPatchCount"),
        "schemaRepairAttemptedTotal": sum(
            1 for summary in available if summary["schemaRepairAttempted"] is True
        ),
        "schemaRepairAppliedTotal": sum(
            1 for summary in available if summary["schemaRepairApplied"] is True
        ),
        "schemaRepairErrorTotal": int_total("schemaRepairErrorCount"),
        "issueTotal": int_total("issueCount"),
        "requestTotal": int_total("requestCount"),
        "totalTokens": int_total("totalTokens"),
        "items": summaries,
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
    }


def build_review_batch_summary(
    store: JsonTaskStore,
    *,
    status: str = TaskStatus.WAITING_REVIEW.value,
    task_type: str | None = None,
    limit: int | None = None,
    detail_mode: str = "full",
    agent_report: str | None = None,
    workflow_run_id: str | None = None,
) -> dict[str, Any]:
    tasks = store.list(status=status, task_type=task_type)
    teaching_package_review = (
        build_teaching_package_review_summary(store, workflow_run_id)
        if workflow_run_id
        else None
    )
    presentation_deck_review = (
        build_presentation_deck_review_summary(store, workflow_run_id)
        if workflow_run_id
        else None
    )
    workflow_task_ids = (
        {
            artifact.taskId
            for artifact in store.list_artifacts(workflow_run_id=workflow_run_id)
            if artifact.taskId
        }
        if workflow_run_id
        else set()
    )
    if workflow_run_id:
        tasks = [task for task in tasks if task.id in workflow_task_ids]
    if limit is not None:
        tasks = tasks[:limit]

    status_counts = _status_counts(
        store,
        task_type,
        task_ids=workflow_task_ids if workflow_run_id else None,
    )
    if detail_mode == "light":
        priority_queue = _light_review_priority_queue(tasks)
        result = {
            "mode": "MOCK_ONLY",
            "detailMode": "LIGHT",
            "filters": {
                "status": status,
                "taskType": task_type,
                "limit": limit,
                "detailMode": detail_mode,
                "workflowRunId": workflow_run_id,
            },
            "items": [_light_task_card(task) for task in tasks],
            "total": len(tasks),
            "providerQualityTaskSignal": _light_provider_quality_task_signal(tasks),
            "reviewPriorityQueue": priority_queue,
            "preApproveReviewCheckSignal": _pre_approve_review_check_signal(priority_queue),
            "gradingEvidenceReadinessSignal": _grading_evidence_readiness_signal(priority_queue),
            "realDemoReviewQueue": _real_demo_review_queue(store, agent_report=agent_report),
            "controlledDockerEvidenceReviewSignal": _controlled_docker_evidence_review_signal(),
            "mergedGradingEvidenceReviewSignal": _merged_grading_evidence_review_signal(),
            "notebookEvidenceReviewPlan": _notebook_evidence_review_plan(),
            "queueSummary": {
                "statusCounts": status_counts,
                "waitingReviewTotal": status_counts[TaskStatus.WAITING_REVIEW.value],
                "reviewRequired": status == TaskStatus.WAITING_REVIEW.value,
                "publishBlockedUntilApproved": True,
            },
            "batchActionPolicy": {
                "batchApproveAllowed": False,
                "batchRejectAllowed": False,
                "batchPublishAllowed": False,
                "reason": "Phase 1 requires single-task manual review; batch state changes are disabled.",
            },
            "safety": build_review_safety(),
        }
        if workflow_run_id:
            result["teachingPackageReview"] = teaching_package_review
            if presentation_deck_review is not None:
                result["presentationDeckReview"] = presentation_deck_review
        return result

    details = []
    for task in tasks:
        detail = build_review_detail(store, task.id)
        if detail is not None:
            details.append(detail)

    items = [_task_card(detail) for detail in details]
    priority_queue = _review_priority_queue(details)
    result = {
        "mode": "MOCK_ONLY",
        "detailMode": "FULL",
        "filters": {
            "status": status,
            "taskType": task_type,
            "limit": limit,
            "detailMode": detail_mode,
            "workflowRunId": workflow_run_id,
        },
        "items": items,
        "total": len(items),
        "providerQualityTaskSignal": _provider_quality_task_signal(details),
        "reviewPriorityQueue": priority_queue,
        "preApproveReviewCheckSignal": _pre_approve_review_check_signal(priority_queue),
        "gradingEvidenceReadinessSignal": _grading_evidence_readiness_signal(priority_queue),
        "realDemoReviewQueue": _real_demo_review_queue(store, agent_report=agent_report),
        "controlledDockerEvidenceReviewSignal": _dynamic_controlled_docker_evidence_review_signal(details),
        "mergedGradingEvidenceReviewSignal": _dynamic_merged_grading_evidence_review_signal(details),
        "notebookEvidenceReviewPlan": _notebook_evidence_review_plan(),
        "queueSummary": {
            "statusCounts": status_counts,
            "waitingReviewTotal": status_counts[TaskStatus.WAITING_REVIEW.value],
            "reviewRequired": status == TaskStatus.WAITING_REVIEW.value,
            "publishBlockedUntilApproved": True,
        },
        "batchActionPolicy": {
            "batchApproveAllowed": False,
            "batchRejectAllowed": False,
            "batchPublishAllowed": False,
            "reason": "Phase 1 requires single-task manual review; batch state changes are disabled.",
        },
        "safety": build_review_safety(),
    }
    if workflow_run_id:
        result["teachingPackageReview"] = teaching_package_review
        if presentation_deck_review is not None:
            result["presentationDeckReview"] = presentation_deck_review
    return result
