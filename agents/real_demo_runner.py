"""Mock runner for the real-demo agent workflow contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from mcp_server import (
    ALL_MCP_TOOL_PROFILE,
    DEFAULT_MCP_TOOL_PROFILE,
    McpToolError,
    invoke_mcp_tool,
    list_mcp_tools,
    mcp_tool_profile_metadata,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "delivery/real-demo-agent-workflow.json"

_LOCAL_CORE_STOP_TOOL_NAMES = {
    "agent_internal_publish_request",
    "query_agent_publish_status",
    "record_agent_entity_publish_result",
    "record_agent_entity_signoff",
    "record_final_publish_review_decision",
}


class RealDemoAgentRunnerError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


def _load_contract(root: Path) -> dict[str, Any]:
    contract_path = root / "delivery/real-demo-agent-workflow.json"
    with contract_path.open("r", encoding="utf-8") as file:
        contract = json.load(file)
    if not isinstance(contract, dict):
        raise RealDemoAgentRunnerError(
            "AGENT_WORKFLOW_CONTRACT_INVALID",
            "Agent workflow contract must be an object",
            [{"field": "contract", "reason": "must be object"}],
        )
    return contract


def _validate_request(*, demo_source_path: str, reviewer: str, revision_priority: str) -> None:
    if not demo_source_path:
        raise RealDemoAgentRunnerError("VALIDATION_ERROR", "参数错误", [{"field": "demoSourcePath", "reason": "缺少参数"}])
    if not reviewer:
        raise RealDemoAgentRunnerError("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}])
    if revision_priority not in {"LOW", "NORMAL", "HIGH"}:
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "revisionPriority", "reason": "必须是 LOW/NORMAL/HIGH"}],
        )


def _validate_core_next_tool_plan_request(*, task_id: str, reviewer: str) -> None:
    if not task_id:
        raise RealDemoAgentRunnerError("VALIDATION_ERROR", "参数错误", [{"field": "taskId", "reason": "缺少参数"}])
    if not reviewer:
        raise RealDemoAgentRunnerError("VALIDATION_ERROR", "参数错误", [{"field": "reviewer", "reason": "缺少参数"}])


def _validate_approved_task_request(
    *,
    approved_lab_task_id: str | None,
    lab_import_output: str | None,
    create_lab_mock_import: bool,
    lab_mock_import_output: str | None,
    approved_exam_task_id: str | None,
    exam_import_output: str | None,
    create_exam_mock_import: bool,
    exam_mock_import_output: str | None,
    approved_grading_task_id: str | None,
    grading_import_output: str | None,
    create_grading_mock_import: bool,
    grading_mock_import_output: str | None,
    readonly_grading_submission: str | None,
    readonly_grading_output: str | None,
    controlled_grading_submission: str | None,
    controlled_grading_output: str | None,
    controlled_grading_image: str | None,
    auto_grading_submission: str | None,
    auto_grading_output: str | None,
    auto_grading_include_controlled: bool,
    auto_grading_fail_on_controlled_unavailable: bool,
    auto_grading_image: str | None,
) -> None:
    if lab_import_output and not approved_lab_task_id:
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "approvedLabTaskId", "reason": "指定 labImportOutput 时必须提供已审核通过的 Lab task id"}],
        )
    if (create_lab_mock_import or lab_mock_import_output) and not approved_lab_task_id:
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "approvedLabTaskId", "reason": "指定 Lab Mock 导入时必须提供已审核通过的 Lab task id"}],
        )
    if exam_import_output and not approved_exam_task_id:
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "approvedExamTaskId", "reason": "指定 examImportOutput 时必须提供已审核通过的 Exam task id"}],
        )
    if (create_exam_mock_import or exam_mock_import_output) and not approved_exam_task_id:
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "approvedExamTaskId", "reason": "指定 Exam Mock 导入时必须提供已审核通过的 Exam task id"}],
        )
    if grading_import_output and not approved_grading_task_id:
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "approvedGradingTaskId", "reason": "指定 gradingImportOutput 时必须提供已审核通过的 Grading task id"}],
        )
    if (create_grading_mock_import or grading_mock_import_output) and not approved_grading_task_id:
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "approvedGradingTaskId", "reason": "指定 Grading Mock 导入时必须提供已审核通过的 Grading task id"}],
        )
    if (readonly_grading_submission or readonly_grading_output) and not approved_grading_task_id:
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "approvedGradingTaskId", "reason": "指定 readonly grading evidence 时必须提供已审核通过的 Grading task id"}],
        )
    if (controlled_grading_submission or controlled_grading_output or controlled_grading_image) and not approved_grading_task_id:
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "approvedGradingTaskId", "reason": "指定 controlled grading evidence 时必须提供已审核通过的 Grading task id"}],
        )
    if (
        auto_grading_submission
        or auto_grading_output
        or auto_grading_include_controlled
        or auto_grading_fail_on_controlled_unavailable
        or auto_grading_image
    ) and not approved_grading_task_id:
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "approvedGradingTaskId", "reason": "指定 auto grading evidence 时必须提供已审核通过的 Grading task id"}],
        )
    if auto_grading_include_controlled and not auto_grading_submission:
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "autoGradingSubmission", "reason": "启用 auto controlled evidence 时必须提供提交目录"}],
        )


def _agent_tool_profile_metadata(root: Path, profile: str | None) -> dict[str, Any]:
    try:
        return mcp_tool_profile_metadata(profile, root)
    except McpToolError as exc:
        raise RealDemoAgentRunnerError(exc.code, exc.message, exc.errors) from exc


def _active_tool_names_for_profile(root: Path, profile: str | None) -> set[str]:
    try:
        return {str(tool["name"]) for tool in list_mcp_tools(root, profile=profile)}
    except McpToolError as exc:
        raise RealDemoAgentRunnerError(exc.code, exc.message, exc.errors) from exc


def _tool_profile_stop_guidance(tool_name: str | None, tool_profile: dict[str, Any]) -> dict[str, Any] | None:
    if not tool_name:
        return None
    profile = str(tool_profile.get("profile") or DEFAULT_MCP_TOOL_PROFILE)
    if profile != DEFAULT_MCP_TOOL_PROFILE:
        return None
    if tool_name in _LOCAL_CORE_STOP_TOOL_NAMES:
        return {
            "component": "AgentToolProfileStopGuidance",
            "reasonCode": "LOCAL_CORE_MVP_STOP_LINE_REACHED",
            "label": "当前本地核心 MVP 停在 import-dry-run / 人工复核交接点",
            "nextOperatorAction": "review_local_import_dry_run_and_wait_for_future_platform_backend_handoff",
            "futureHandoff": "真实平台后端接口、AGENT_API_TOKEN、import-send/import-status/signoff/final publish 当前暂停",
        }
    return {
        "component": "AgentToolProfileStopGuidance",
        "reasonCode": "MCP_TOOL_PAUSED_FOR_LOCAL_CORE_MVP",
        "label": "该 MCP Tool 属于历史全量 manifest 或暂停范围",
        "nextOperatorAction": "continue_with_local_core_mvp_tools_or_use_profile_all_only_for_historical_regression",
        "futureHandoff": "仅在用户明确恢复对应真实平台、环境或 revision-loop 能力时再启用",
    }


def _detect_next_paused_platform_tool(summary: dict[str, Any]) -> dict[str, Any] | None:
    """Detect the next paused platform tool from readiness report summary totals.

    When the readiness report returns ``LOCAL_CORE_MVP_STOP_LINE_REACHED`` with
    no tool name (because ``include_future_platform_steps=False`` for the
    local-core-mvp profile), this helper inspects the summary totals to surface
    the next platform tool that would be blocked by the current profile.
    """
    required = int(summary.get("platformRequiredTotal") or 0)
    if required <= 0:
        return None
    dry_run = int(summary.get("platformDryRunPreparedTotal") or 0)
    request_sent = int(summary.get("platformRequestSentTotal") or 0)
    status_queried = int(summary.get("platformStatusQueriedTotal") or 0)
    result_recorded = int(summary.get("platformResultRecordedTotal") or 0)
    signoff_recorded = int(summary.get("platformSignoffRecordedTotal") or 0)
    final_decision = int(summary.get("finalPublishReviewDecisionRecordedTotal") or 0)
    if dry_run >= required and request_sent < required:
        return {
            "toolName": "agent_internal_publish_request",
            "reasonCode": "PLATFORM_IMPORT_REQUEST_PENDING",
            "argumentsPreview": {
                "id": "<agent_entity_id>",
                "reviewer": "<reviewer>",
                "dryRun": "<reviewed_dry_run_report_path>",
                "baseUrl": "<platform_api_base_url>",
                "output": "examples/output/platform-entity-import-send-report.json",
                "explicitPlatformCallOptIn": True,
                "confirmDryRunReviewed": True,
                "confirmManualPlatformReview": True,
                "confirmNoAutoPublish": True,
            },
            "argumentHints": [
                {"name": "dryRun", "required": True, "source": "reviewed local dry-run report path"},
                {"name": "baseUrl", "required": True, "source": "reviewer-provided platform API base URL"},
                {"name": "output", "required": True, "source": "local send report output path"},
            ],
        }
    if request_sent >= required and status_queried < required:
        return {
            "toolName": "query_agent_publish_status",
            "reasonCode": "PLATFORM_IMPORT_STATUS_QUERY_PENDING",
            "argumentsPreview": {
                "id": "<agent_entity_id>",
                "reviewer": "<reviewer>",
                "sendResult": "<reviewed_import_send_report_path>",
                "baseUrl": "<platform_api_base_url>",
                "output": "examples/output/platform-entity-import-status-query.json",
                "explicitPlatformQueryOptIn": True,
            },
            "argumentHints": [
                {"name": "sendResult", "required": True, "source": "reviewed import send report path"},
                {"name": "baseUrl", "required": True, "source": "reviewer-provided platform API base URL"},
                {"name": "output", "required": True, "source": "local status report output path"},
            ],
        }
    if status_queried >= required and result_recorded < required:
        return {
            "toolName": "record_agent_entity_publish_result",
            "reasonCode": "PLATFORM_IMPORT_RESULT_RECORD_PENDING",
            "argumentsPreview": {
                "id": "<agent_entity_id>",
                "reviewer": "<reviewer>",
                "sendResult": "<reviewed_import_send_report_path>",
                "agentStatus": "ACCEPTED_FOR_DRAFT",
                "output": "examples/output/platform-entity-import-result-record.json",
            },
            "argumentHints": [
                {"name": "sendResult", "required": True, "source": "reviewed import send report path"},
                {"name": "agentStatus", "required": True, "source": "human-reviewed platform draft status"},
                {"name": "output", "required": True, "source": "local result record output path"},
            ],
        }
    if result_recorded >= required and signoff_recorded < required:
        return {
            "toolName": "record_agent_entity_signoff",
            "reasonCode": "PLATFORM_ENTITY_SIGNOFF_REQUIRED",
            "argumentsPreview": {
                "id": "<agent_entity_id>",
                "reviewer": "<reviewer>",
                "output": "examples/output/platform-entity-signoff.json",
            },
            "argumentHints": [],
        }
    if signoff_recorded >= required and final_decision < required:
        return {
            "toolName": "record_final_publish_review_decision",
            "reasonCode": "FINAL_PUBLISH_REVIEW_DECISION_REQUIRED",
            "argumentsPreview": {
                "id": "<agent_entity_id>",
                "reviewer": "<reviewer>",
                "decision": "APPROVED_FOR_PUBLISH_PLANNING",
                "output": "examples/output/final-publish-review-decision.json",
            },
            "argumentHints": [],
        }
    return None


def _run_tool(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    store_path: Path | None,
    root: Path,
    trace_id: str,
    tool_profile: str | None = ALL_MCP_TOOL_PROFILE,
) -> dict[str, Any]:
    try:
        response = invoke_mcp_tool(
            tool_name,
            arguments,
            store_path=store_path,
            root=root,
            actor="real-demo-agent-mock",
            trace_id=trace_id,
            profile=tool_profile,
        )
    except McpToolError as exc:
        raise RealDemoAgentRunnerError(exc.code, exc.message, exc.errors) from exc
    if not response.get("success"):
        raise RealDemoAgentRunnerError(response.get("code", "AGENT_TOOL_FAILED"), response.get("message", "工具调用失败"), response.get("errors", []))
    return response


def _step_result(
    *,
    step_id: str,
    order: int,
    tool_name: str | None,
    response: dict[str, Any] | None,
    state_check: str,
    human_review_stop: bool,
    mutates_state: bool,
) -> dict[str, Any]:
    record = None
    if response:
        data = response.get("data") if isinstance(response.get("data"), dict) else {}
        record = data.get("mcpToolCallRecord") if isinstance(data, dict) else response.get("mcpToolCallRecord")
    return {
        "id": step_id,
        "order": order,
        "tool": tool_name,
        "status": "COMPLETED",
        "stateCheck": state_check,
        "humanReviewStop": human_review_stop,
        "mutatesState": mutates_state,
        "mcpToolCallRecordId": record.get("id") if isinstance(record, dict) else None,
    }


def _build_core_next_tool_plan(
    *,
    core_readiness_response: dict[str, Any],
    task_id: str,
    reviewer: str,
    tool_profile: dict[str, Any],
    active_tool_names: set[str],
) -> dict[str, Any]:
    report = core_readiness_response.get("data", {}).get("coreWorkflowReadinessReport", {})
    if not isinstance(report, dict):
        report = {}
    recommendation = report.get("nextToolRecommendation") if isinstance(report.get("nextToolRecommendation"), dict) else {}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    safety = report.get("safety") if isinstance(report.get("safety"), dict) else {}
    arguments_preview = recommendation.get("argumentsPreview")
    if not isinstance(arguments_preview, dict):
        arguments_preview = {}
    argument_hints = recommendation.get("argumentHints")
    if not isinstance(argument_hints, list):
        argument_hints = []

    recommended_tool_name = recommendation.get("toolName")
    recommended_tool_name = str(recommended_tool_name) if recommended_tool_name else None
    reason_code = str(recommendation.get("reasonCode") or "NO_RECOMMENDATION")
    action_type = str(recommendation.get("actionType") or "manual_action")

    paused_platform_tool = None
    if not recommended_tool_name and reason_code == "LOCAL_CORE_MVP_STOP_LINE_REACHED":
        paused_platform_tool = _detect_next_paused_platform_tool(summary)
        if paused_platform_tool:
            recommended_tool_name = paused_platform_tool["toolName"]
            reason_code = paused_platform_tool["reasonCode"]
            action_type = "mcp_tool"
            if paused_platform_tool.get("argumentsPreview"):
                arguments_preview = paused_platform_tool["argumentsPreview"]
            if paused_platform_tool.get("argumentHints"):
                argument_hints = paused_platform_tool["argumentHints"]

    recommended_tool_in_profile = recommended_tool_name in active_tool_names if recommended_tool_name else True
    tool_profile_stop_guidance = None if recommended_tool_in_profile else _tool_profile_stop_guidance(
        recommended_tool_name,
        tool_profile,
    )
    recommendation_tool_available = bool(recommendation.get("toolAvailable", False)) or paused_platform_tool is not None
    profile_allowed_tool_available = recommendation_tool_available and recommended_tool_in_profile
    can_call_tool_after_human_confirmation = (
        recommendation_tool_available
        and recommended_tool_in_profile
        and recommendation.get("autoExecuteAllowed") is False
        and bool(recommended_tool_name)
    )
    manual_action_required = not recommendation_tool_available or not recommended_tool_in_profile
    final_review_state = recommendation.get("finalReviewState") or summary.get("finalReviewState")
    manual_action_kind = "none"
    manual_action_label = "none"
    if manual_action_required:
        if tool_profile_stop_guidance:
            manual_action_kind = "local_core_mvp_profile_stop"
            manual_action_label = str(tool_profile_stop_guidance.get("label") or "当前工具不在本地核心 MVP profile 中")
        elif reason_code == "CONTENT_QUALITY_REVISION_REQUIRED" or action_type == "manual_revision_request":
            manual_action_kind = "content_quality_revision_request"
            manual_action_label = "内容质量需先记录修订请求"
        elif action_type == "manual_review_decision_note":
            manual_action_kind = "grading_review_decision_note"
            manual_action_label = "需要人工记录评分审核结论"
        elif action_type == "manual_review":
            manual_action_kind = "human_content_approval"
            manual_action_label = "需要人工审核通过生成内容"
        else:
            manual_action_kind = "manual_review_action"
            manual_action_label = "需要人工审核或人工复核动作"
    content_quality_readiness = recommendation.get("contentQualityReadiness")
    if not isinstance(content_quality_readiness, dict):
        content_quality_readiness = report.get("contentQualityReadiness") if isinstance(report.get("contentQualityReadiness"), dict) else {}

    return {
        "component": "AgentCoreNextToolPlan",
        "mode": "MOCK_AGENT_RUNNER_READ_ONLY_PLAN",
        "source": "get_core_workflow_readiness.data.coreWorkflowReadinessReport.nextToolRecommendation",
        "taskId": task_id,
        "reviewer": reviewer,
        "taskStatus": report.get("taskStatus"),
        "coreReady": bool(report.get("ready", False)),
        "coreStatus": report.get("status"),
        "recommendedNextAction": report.get("recommendedNextAction"),
        "finalReviewState": final_review_state,
        "blockedTotal": summary.get("blockedTotal", 0),
        "reasonCode": reason_code,
        "actionType": action_type,
        "toolName": recommended_tool_name,
        "toolAvailable": profile_allowed_tool_available,
        "recommendedToolAvailableBeforeProfile": recommendation_tool_available,
        "recommendedToolInProfile": recommended_tool_in_profile,
        "blockedByToolProfile": bool(tool_profile_stop_guidance),
        "toolProfileStopGuidance": tool_profile_stop_guidance,
        "canCallToolAfterHumanConfirmation": can_call_tool_after_human_confirmation,
        "manualActionRequired": manual_action_required,
        "manualActionKind": manual_action_kind,
        "manualActionLabel": manual_action_label,
        "manualActionCliCommand": recommendation.get("cliCommand") if manual_action_required else None,
        "contentQualityReadiness": content_quality_readiness,
        "argumentsPreview": arguments_preview,
        "argumentHints": argument_hints,
        "plannedSteps": [
            {
                "id": "read_core_workflow_readiness",
                "order": 1,
                "tool": "get_core_workflow_readiness",
                "status": "COMPLETED",
                "mutatesState": False,
                "humanReviewStop": True,
                "stateCheck": "coreWorkflowReadinessReport.safety.readOnly == true",
            },
            {
                "id": "review_next_tool_recommendation",
                "order": 2,
                "tool": recommended_tool_name,
                "status": "PLANNED_ONLY",
                "mutatesState": False,
                "humanReviewStop": True,
                "stateCheck": (
                    "nextToolRecommendation.autoExecuteAllowed == false and recommended tool is allowed by MCP profile"
                    if recommended_tool_in_profile
                    else "recommended tool is paused by current MCP profile"
                ),
            },
        ],
        "toolProfile": tool_profile,
        "safety": {
            "readOnlyPlan": True,
            "realAgentStarted": False,
            "realMcpServerStarted": False,
            "recommendedToolCalled": False,
            "toolProfileEnforced": True,
            "activeToolProfile": tool_profile.get("profile"),
            "pausedMcpToolBlocked": bool(tool_profile_stop_guidance),
            "realPlatformBackendToolsEnabledByDefault": False,
            "realPlatformBackendToolsEnabledInProfile": tool_profile.get("profile") != DEFAULT_MCP_TOOL_PROFILE,
            "newLlmRequestSent": False,
            "realLlmCalled": False,
            "secretsRead": False,
            "networkAccess": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "databaseWritten": False,
            "realAgentImport": False,
            "autoExecuteAllowed": bool(recommendation.get("autoExecuteAllowed", False)),
            "autoApproveAllowed": bool(recommendation.get("autoApproveAllowed", False)),
            "autoPublishAllowed": bool(recommendation.get("autoPublishAllowed", False)),
            "realPublishAllowed": bool(recommendation.get("realPublishAllowed", False)),
            "coreReadinessReadOnly": bool(safety.get("readOnly", False)),
        },
    }


_SINGLE_EXECUTION_ALLOWED_TOOLS = {
    "create_lab_template_import_preview",
    "create_exam_question_import_preview",
    "create_grading_rule_import_preview",
    "create_lab_template_mock_import",
    "create_exam_question_mock_import",
    "create_grading_rule_mock_import",
    "create_agent_entity_import_dry_run",
    "agent_internal_publish_request",
    "query_agent_publish_status",
    "record_agent_entity_publish_result",
    "run_grading_evidence_auto",
    "record_review_decision_note",
    "record_agent_entity_signoff",
    "record_final_publish_review_decision",
    "regenerate_from_revision_mock",
}


def _replace_argument_placeholders(value: Any, *, task_id: str, reviewer: str) -> Any:
    if isinstance(value, dict):
        return {
            key: _replace_argument_placeholders(item, task_id=task_id, reviewer=reviewer)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _replace_argument_placeholders(item, task_id=task_id, reviewer=reviewer)
            for item in value
        ]
    if value == "<taskId>":
        return task_id
    if value == "<reviewer>":
        return reviewer
    return value


def _find_unresolved_argument_placeholders(value: Any, path: str = "$") -> list[dict[str, str]]:
    if isinstance(value, dict):
        errors: list[dict[str, str]] = []
        for key, item in value.items():
            errors.extend(_find_unresolved_argument_placeholders(item, f"{path}.{key}"))
        return errors
    if isinstance(value, list):
        errors = []
        for index, item in enumerate(value):
            errors.extend(_find_unresolved_argument_placeholders(item, f"{path}[{index}]"))
        return errors
    if isinstance(value, str) and value.startswith("<") and value.endswith(">"):
        return [{"field": path, "reason": f"参数占位符 {value} 未替换"}]
    return []


def _build_confirmed_recommended_tool_arguments(
    *,
    plan: dict[str, Any],
    task_id: str,
    reviewer: str,
    tool_arguments: dict[str, Any] | None,
) -> dict[str, Any]:
    arguments_preview = plan.get("argumentsPreview")
    if not isinstance(arguments_preview, dict):
        arguments_preview = {}
    merged = _replace_argument_placeholders(arguments_preview, task_id=task_id, reviewer=reviewer)
    if tool_arguments:
        merged.update(tool_arguments)
    placeholder_errors = _find_unresolved_argument_placeholders(merged)
    if placeholder_errors:
        raise RealDemoAgentRunnerError(
            "RECOMMENDED_TOOL_ARGUMENTS_INCOMPLETE",
            "推荐工具参数仍包含未替换占位符",
            placeholder_errors,
        )
    return merged


def _build_next_single_step_action_guide(
    *,
    plan: dict[str, Any],
    task_id: str,
    reviewer: str,
) -> dict[str, Any]:
    arguments_preview = plan.get("argumentsPreview")
    if not isinstance(arguments_preview, dict):
        arguments_preview = {}
    argument_hints = plan.get("argumentHints")
    if not isinstance(argument_hints, list):
        argument_hints = []
    suggested_arguments = _replace_argument_placeholders(
        arguments_preview,
        task_id=task_id,
        reviewer=reviewer,
    )
    placeholder_errors = _find_unresolved_argument_placeholders(suggested_arguments)
    tool_name = plan.get("toolName")
    can_continue = (
        bool(tool_name)
        and plan.get("toolAvailable") is True
        and plan.get("canCallToolAfterHumanConfirmation") is True
        and not placeholder_errors
    )
    suggested_cli_command = None
    if can_continue:
        profile = plan.get("toolProfile", {}).get("profile") if isinstance(plan.get("toolProfile"), dict) else None
        profile_arg = f"--profile {profile} " if profile else ""
        suggested_cli_command = (
            "python lab_cli.py agent real-demo execute-core-next-tool "
            f"--task-id {task_id} --reviewer {reviewer} {profile_arg}"
            f"--arguments {json.dumps(suggested_arguments, ensure_ascii=False)} "
            "--confirm-execute-recommended-tool"
        )
    manual_cli_command = None
    if plan.get("manualActionRequired") is True:
        manual_cli_command = plan.get("manualActionCliCommand") or plan.get("recommendedNextAction")
    profile_stop_guidance = plan.get("toolProfileStopGuidance")
    if isinstance(profile_stop_guidance, dict):
        stop_reason = str(profile_stop_guidance.get("reasonCode") or "MCP_TOOL_PAUSED_FOR_LOCAL_CORE_MVP")
        stop_label = str(profile_stop_guidance.get("label") or "推荐工具不在当前 MCP profile 中")
        next_operator_action = str(profile_stop_guidance.get("nextOperatorAction") or "review_current_local_artifacts")
    elif placeholder_errors:
        stop_reason = "ADDITIONAL_ARGUMENTS_REQUIRED"
        stop_label = "需要补齐推荐工具参数"
        next_operator_action = "fill_tool_arguments_then_rerun_with_confirmation"
    elif can_continue:
        stop_reason = "CONFIRMABLE_TOOL_READY"
        stop_label = "可继续执行一个已推荐工具"
        next_operator_action = "copy_suggested_cli_command_after_manual_confirmation"
    elif plan.get("manualActionKind") == "content_quality_revision_request":
        stop_reason = "CONTENT_QUALITY_REVISION_REQUIRED"
        stop_label = "内容质量需先记录修订请求"
        next_operator_action = "record_review_revision_request_before_import_preview"
    elif plan.get("manualActionRequired") is True:
        stop_reason = "HUMAN_MANUAL_ACTION_REQUIRED"
        stop_label = str(plan.get("manualActionLabel") or "需要人工审核或人工复核动作")
        next_operator_action = str(plan.get("recommendedNextAction") or "perform_manual_review_action")
    else:
        stop_reason = "NO_NEXT_TOOL_AVAILABLE"
        stop_label = "暂无可执行推荐工具"
        next_operator_action = "inspect_core_readiness_report"
    operator_summary = (
        f"{stop_label}; reasonCode={plan.get('reasonCode')}; "
        f"finalReviewState={plan.get('finalReviewState')}; "
        f"nextTool={tool_name or 'none'}; canContinueWithSameCommand={str(can_continue).lower()}"
    )
    blocked_by_profile = isinstance(profile_stop_guidance, dict)
    return {
        "component": "AgentCoreNextSingleStepActionGuide",
        "mode": "ADVISORY_ONLY",
        "source": "postExecutionCoreNextToolPlan",
        "taskId": task_id,
        "reviewer": reviewer,
        "reasonCode": plan.get("reasonCode"),
        "recommendedNextAction": plan.get("recommendedNextAction"),
        "finalReviewState": plan.get("finalReviewState"),
        "nextToolName": tool_name,
        "canContinueWithSameCommand": can_continue,
        "requiresHumanManualAction": plan.get("manualActionRequired") is True,
        "requiresAdditionalArguments": bool(placeholder_errors) and not blocked_by_profile,
        "placeholderErrors": [] if blocked_by_profile else placeholder_errors,
        "suggestedArguments": {} if blocked_by_profile else suggested_arguments,
        "argumentHints": [] if blocked_by_profile else argument_hints,
        "toolProfileStopGuidance": profile_stop_guidance if blocked_by_profile else None,
        "suggestedCliCommand": suggested_cli_command,
        "manualActionHint": manual_cli_command,
        "manualActionKind": plan.get("manualActionKind"),
        "manualActionLabel": plan.get("manualActionLabel"),
        "contentQualityReadiness": plan.get("contentQualityReadiness") if isinstance(plan.get("contentQualityReadiness"), dict) else {},
        "currentStop": {
            "reasonCode": stop_reason,
            "label": stop_label,
            "nextOperatorAction": next_operator_action,
            "requiresHumanConfirmation": True,
            "recommendedToolCalledByGuide": False,
            "autoExecuteAllowed": False,
        },
        "operatorSummary": operator_summary,
        "autoExecuteAllowed": False,
        "autoApproveAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
    }


def _build_quality_aware_review_triage(review_summary: dict[str, Any]) -> dict[str, Any]:
    review_task_summary = review_summary.get("data", {}).get("reviewTaskSummary", {})
    if not isinstance(review_task_summary, dict):
        review_task_summary = {}
    provider_signal = review_task_summary.get("providerQualityTaskSignal", {})
    if not isinstance(provider_signal, dict):
        provider_signal = {}
    priority_queue = review_task_summary.get("reviewPriorityQueue", {})
    if not isinstance(priority_queue, dict):
        priority_queue = {}
    queue_items = priority_queue.get("items") if isinstance(priority_queue.get("items"), list) else []

    quality_items = provider_signal.get("items") if isinstance(provider_signal.get("items"), list) else []
    available_items = [item for item in quality_items if isinstance(item, dict) and item.get("available") is True]
    ready_items = [item for item in available_items if item.get("readyForReview") is True]
    real_llm_items = [item for item in available_items if item.get("realLlmCalled") is True]

    if real_llm_items and len(ready_items) == len(available_items):
        primary_action = "manual_review_real_llm_outputs_before_import_preview"
        reason_code = "REAL_LLM_PROVIDER_QUALITY_READY_FOR_MANUAL_REVIEW"
    elif ready_items:
        primary_action = "manual_review_ready_outputs_before_import_preview"
        reason_code = "PROVIDER_QUALITY_READY_FOR_MANUAL_REVIEW"
    else:
        primary_action = "open_review_detail_and_collect_quality_evidence"
        reason_code = "PROVIDER_QUALITY_NOT_READY_OR_NOT_AVAILABLE"

    return {
        "component": "AgentQualityAwareReviewTriage",
        "mode": "MOCK_AGENT_RUNNER",
        "source": "get_review_task_summary.data.reviewTaskSummary.providerQualityTaskSignal",
        "queueSource": "get_review_task_summary.data.reviewTaskSummary.reviewPriorityQueue",
        "taskTotal": provider_signal.get("taskTotal", 0),
        "providerQualityAvailableTotal": provider_signal.get("availableTotal", 0),
        "realLlmCalledTotal": provider_signal.get("realLlmCalledTotal", 0),
        "readyForReviewTotal": provider_signal.get("readyForReviewTotal", 0),
        "normalizationPatchTotal": provider_signal.get("normalizationPatchTotal", 0),
        "schemaRepairAppliedTotal": provider_signal.get("schemaRepairAppliedTotal", 0),
        "primaryRecommendedAction": primary_action,
        "reasonCode": reason_code,
        "manualReviewRequired": True,
        "importPreviewEligibleNow": False,
        "importPreviewAllowedAfterApproval": bool(ready_items),
        "nextReviewTaskIds": [
            item.get("taskId")
            for item in queue_items
            if isinstance(item, dict) and item.get("taskId")
        ],
        "nextRecommendedActions": [
            item.get("recommendedAction")
            for item in queue_items
            if isinstance(item, dict) and item.get("recommendedAction")
        ],
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
    }


def _build_review_detail_guidance(review_detail_response: dict[str, Any]) -> dict[str, Any]:
    review_detail = review_detail_response.get("data", {}).get("reviewDetail", {})
    if not isinstance(review_detail, dict):
        review_detail = {}
    task = review_detail.get("task") if isinstance(review_detail.get("task"), dict) else {}
    review_page = review_detail.get("reviewPage") if isinstance(review_detail.get("reviewPage"), dict) else {}
    action_bar = review_page.get("actionBar") if isinstance(review_page.get("actionBar"), dict) else {}
    dsl_preview = review_page.get("dslPreview") if isinstance(review_page.get("dslPreview"), dict) else {}
    import_actions = review_detail.get("platformImportPreviewActions")
    if not isinstance(import_actions, dict):
        import_actions = review_page.get("platformImportPreviewActions") if isinstance(review_page.get("platformImportPreviewActions"), dict) else {}

    approve_action = action_bar.get("approve") if isinstance(action_bar.get("approve"), dict) else {}
    reject_action = action_bar.get("reject") if isinstance(action_bar.get("reject"), dict) else {}
    revision_action = action_bar.get("requestRevision") if isinstance(action_bar.get("requestRevision"), dict) else {}
    mock_publish_action = action_bar.get("mockPublish") if isinstance(action_bar.get("mockPublish"), dict) else {}
    import_items = import_actions.get("items") if isinstance(import_actions.get("items"), list) else []
    enabled_import_items = [item for item in import_items if isinstance(item, dict) and item.get("enabled") is True]

    if revision_action.get("enabled") is True:
        primary_action = "request_review_revision_before_any_publish"
    elif approve_action.get("enabled") is True:
        primary_action = "human_reviewer_decides_approve_or_reject"
    else:
        primary_action = "inspect_review_detail_before_next_action"

    return {
        "component": "AgentReviewDetailGuidance",
        "mode": "MOCK_AGENT_RUNNER",
        "source": "get_review_detail.data.reviewDetail.reviewPage",
        "taskId": task.get("id"),
        "taskType": task.get("taskType"),
        "taskStatus": task.get("status"),
        "artifactKind": dsl_preview.get("artifactKind"),
        "approveVisible": bool(approve_action.get("enabled", False)),
        "rejectVisible": bool(reject_action.get("enabled", False)),
        "requestRevisionVisible": bool(revision_action.get("enabled", False)),
        "requestRevisionChangesTaskStatus": bool(revision_action.get("changesTaskStatus", False)),
        "mockPublishEnabled": bool(mock_publish_action.get("enabled", False)),
        "platformImportPreviewActionsVisible": bool(import_actions.get("visible", False)),
        "platformImportPreviewEnabledTotal": len(enabled_import_items),
        "platformImportPreviewAllowedAfterApproval": bool(import_items),
        "primaryRecommendedAction": primary_action,
        "manualReviewRequired": True,
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
    }


def _build_platform_import_preview_guidance(
    import_preview_response: dict[str, Any] | None,
    *,
    component: str,
    preview_key: str,
    draft_key: str,
    source: str,
    disabled_reason: str,
) -> dict[str, Any]:
    if not import_preview_response:
        return {
            "component": component,
            "mode": "MOCK_AGENT_RUNNER",
            "enabled": False,
            "reason": disabled_reason,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        }
    preview = import_preview_response.get("data", {}).get(preview_key, {})
    if not isinstance(preview, dict):
        preview = {}
    draft = preview.get(draft_key) if isinstance(preview.get(draft_key), dict) else {}
    safety = preview.get("safety") if isinstance(preview.get("safety"), dict) else {}
    return {
        "component": component,
        "mode": "MOCK_AGENT_RUNNER",
        "enabled": True,
        "source": source,
        "taskId": preview.get("sourceTaskId"),
        "sourceTaskStatus": preview.get("sourceTaskStatus"),
        "sourceArtifactKind": preview.get("sourceArtifactKind"),
        "agentEntity": preview.get("agentEntity"),
        "draftId": draft.get("id"),
        "draftStatus": draft.get("status"),
        "databaseWritten": bool(safety.get("databaseWritten", False)),
        "realAgentImport": bool(safety.get("realAgentImport", False)),
        "answerVisibleToCandidate": bool(safety.get("answerVisibleToCandidate", False)),
        "sandboxExecuted": bool(safety.get("sandboxExecuted", False)),
        "contestantCodeExecuted": bool(safety.get("contestantCodeExecuted", False)),
        "autoPublishAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": bool(safety.get("realPublishAllowed", False)),
        "nextRecommendedAction": "human_signoff_platform_import_preview",
    }


def _build_lab_import_preview_guidance(import_preview_response: dict[str, Any] | None) -> dict[str, Any]:
    return _build_platform_import_preview_guidance(
        import_preview_response,
        component="AgentLabImportPreviewGuidance",
        preview_key="labTemplateImportPreview",
        draft_key="labTemplateDraft",
        source="create_lab_template_import_preview.data.labTemplateImportPreview",
        disabled_reason="approvedLabTaskId not provided",
    )


def _build_exam_import_preview_guidance(import_preview_response: dict[str, Any] | None) -> dict[str, Any]:
    return _build_platform_import_preview_guidance(
        import_preview_response,
        component="AgentExamImportPreviewGuidance",
        preview_key="examQuestionImportPreview",
        draft_key="examQuestionDraft",
        source="create_exam_question_import_preview.data.examQuestionImportPreview",
        disabled_reason="approvedExamTaskId not provided",
    )


def _build_grading_import_preview_guidance(import_preview_response: dict[str, Any] | None) -> dict[str, Any]:
    return _build_platform_import_preview_guidance(
        import_preview_response,
        component="AgentGradingImportPreviewGuidance",
        preview_key="gradingRuleImportPreview",
        draft_key="gradingRuleDraft",
        source="create_grading_rule_import_preview.data.gradingRuleImportPreview",
        disabled_reason="approvedGradingTaskId not provided",
    )


def _build_agent_entity_mock_import_guidance(
    mock_import_response: dict[str, Any] | None,
    *,
    component: str,
    source: str,
    disabled_reason: str,
) -> dict[str, Any]:
    if not mock_import_response:
        return {
            "component": component,
            "mode": "MOCK_AGENT_RUNNER",
            "enabled": False,
            "reason": disabled_reason,
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        }
    report = mock_import_response.get("data", {}).get("agentEntityMockImport", {})
    if not isinstance(report, dict):
        report = {}
    record = report.get("agentEntityRecord") if isinstance(report.get("agentEntityRecord"), dict) else {}
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    source_preview = report.get("sourcePreview") if isinstance(report.get("sourcePreview"), dict) else {}
    safety = report.get("safety") if isinstance(report.get("safety"), dict) else {}
    return {
        "component": component,
        "mode": "MOCK_AGENT_RUNNER",
        "enabled": True,
        "source": source,
        "taskId": report.get("taskId"),
        "taskStatus": report.get("taskStatus"),
        "agentEntity": report.get("agentEntity"),
        "agentEntityId": record.get("id"),
        "agentEntityStatus": record.get("status"),
        "agentEntityType": record.get("entityType"),
        "sourcePreviewArtifactId": source_preview.get("artifactId"),
        "schemaValidated": bool(source_preview.get("schemaValidated", False)),
        "answerVisibleToCandidate": bool(payload.get("candidateAnswerVisible", False)),
        "mockStoreWritten": bool(safety.get("mockStoreWritten", False)),
        "databaseWritten": bool(safety.get("databaseWritten", False)),
        "realAgentImport": bool(safety.get("realAgentImport", False)),
        "sandboxExecuted": bool(safety.get("sandboxExecuted", False)),
        "contestantCodeExecuted": bool(safety.get("contestantCodeExecuted", False)),
        "autoPublishAllowed": False,
        "batchStateChangeAllowed": False,
        "realPublishAllowed": bool(safety.get("realPublishAllowed", False)),
        "nextRecommendedAction": "manual_agent_entity_review_before_real_import",
    }


def _build_lab_mock_import_guidance(mock_import_response: dict[str, Any] | None) -> dict[str, Any]:
    return _build_agent_entity_mock_import_guidance(
        mock_import_response,
        component="AgentLabMockImportGuidance",
        source="create_lab_template_mock_import.data.agentEntityMockImport",
        disabled_reason="createLabMockImport not requested",
    )


def _build_exam_mock_import_guidance(mock_import_response: dict[str, Any] | None) -> dict[str, Any]:
    return _build_agent_entity_mock_import_guidance(
        mock_import_response,
        component="AgentExamMockImportGuidance",
        source="create_exam_question_mock_import.data.agentEntityMockImport",
        disabled_reason="createExamMockImport not requested",
    )


def _build_grading_mock_import_guidance(mock_import_response: dict[str, Any] | None) -> dict[str, Any]:
    return _build_agent_entity_mock_import_guidance(
        mock_import_response,
        component="AgentGradingMockImportGuidance",
        source="create_grading_rule_mock_import.data.agentEntityMockImport",
        disabled_reason="createGradingMockImport not requested",
    )


def _build_agent_entity_readiness_guidance(readiness_response: dict[str, Any] | None) -> dict[str, Any]:
    if not readiness_response:
        return {
            "component": "AgentAgentEntityReadinessGuidance",
            "mode": "MOCK_AGENT_RUNNER",
            "enabled": False,
            "reason": "platform entity readiness report not requested",
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        }
    report = readiness_response.get("data", {}).get("agentEntityReadinessReport", {})
    if not isinstance(report, dict):
        report = {}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    safety = report.get("safety") if isinstance(report.get("safety"), dict) else {}
    items = report.get("items") if isinstance(report.get("items"), list) else []
    missing_preview_entities = [
        item.get("agentEntity")
        for item in items
        if isinstance(item, dict) and item.get("previewCreated") is not True
    ]
    missing_mock_import_entities = [
        item.get("agentEntity")
        for item in items
        if isinstance(item, dict) and item.get("mockImportCreated") is not True
    ]
    ready_entities = [
        item.get("agentEntity")
        for item in items
        if isinstance(item, dict) and item.get("readyForManualAgentReview") is True
    ]
    signoff_ready_entities = [
        item.get("agentEntity")
        for item in items
        if isinstance(item, dict) and item.get("readyForAgentEntitySignoff") is True
    ]
    signed_entities = [
        item.get("agentEntity")
        for item in items
        if isinstance(item, dict) and item.get("signoffRecorded") is True
    ]
    signoff_pending_entities = [
        item.get("agentEntity")
        for item in items
        if isinstance(item, dict)
        and item.get("readyForManualAgentReview") is True
        and item.get("signoffRecorded") is not True
    ]
    if summary.get("allPostSignoffPrePublishReady") is True:
        next_action = "review_signed_agent_entities_before_publish_planning"
    elif signoff_ready_entities:
        next_action = "record_manual_agent_entity_signoff"
    elif summary.get("allReadyForManualPlatformReview") is True:
        next_action = "manual_platform_review_and_real_import_planning"
    elif missing_preview_entities:
        next_action = "create_missing_import_previews_before_platform_review"
    else:
        next_action = "create_mock_imports_after_manual_platform_signoff"

    return {
        "component": "AgentAgentEntityReadinessGuidance",
        "mode": "MOCK_AGENT_RUNNER",
        "enabled": True,
        "source": "get_agent_entity_readiness_report.data.agentEntityReadinessReport",
        "requiredTotal": summary.get("requiredTotal", 0),
        "previewCreatedTotal": summary.get("previewCreatedTotal", 0),
        "mockImportCreatedTotal": summary.get("mockImportCreatedTotal", 0),
        "readyForManualAgentReviewTotal": summary.get("readyForManualAgentReviewTotal", 0),
        "missingPreviewTotal": summary.get("missingPreviewTotal", 0),
        "missingMockImportTotal": summary.get("missingMockImportTotal", 0),
        "agentEntitySignoffReadyTotal": summary.get("agentEntitySignoffReadyTotal", 0),
        "agentEntitySignoffRecordedTotal": summary.get("agentEntitySignoffRecordedTotal", 0),
        "postSignoffPrePublishReadyTotal": summary.get("postSignoffPrePublishReadyTotal", 0),
        "allReadyForManualPlatformReview": bool(summary.get("allReadyForManualPlatformReview", False)),
        "allPlatformEntitiesReadyForSignoff": bool(summary.get("allPlatformEntitiesReadyForSignoff", False)),
        "allPlatformEntitiesSignoffRecorded": bool(summary.get("allPlatformEntitiesSignoffRecorded", False)),
        "allPostSignoffPrePublishReady": bool(summary.get("allPostSignoffPrePublishReady", False)),
        "readyEntities": ready_entities,
        "signoffReadyEntities": signoff_ready_entities,
        "signedEntities": signed_entities,
        "signoffPendingEntities": signoff_pending_entities,
        "missingPreviewEntities": missing_preview_entities,
        "missingMockImportEntities": missing_mock_import_entities,
        "nextRecommendedAction": next_action,
        "readOnly": bool(safety.get("readOnly", False)),
        "databaseWritten": bool(safety.get("databaseWritten", False)),
        "realAgentImport": bool(safety.get("realAgentImport", False)),
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": bool(safety.get("realPublish", False)),
    }


def _build_readonly_grading_evidence_guidance(evidence_response: dict[str, Any] | None) -> dict[str, Any]:
    if not evidence_response:
        return {
            "component": "AgentReadonlyGradingEvidenceGuidance",
            "mode": "MOCK_AGENT_RUNNER",
            "enabled": False,
            "reason": "readonlyGradingSubmission not provided",
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        }
    data = evidence_response.get("data") if isinstance(evidence_response.get("data"), dict) else {}
    report = data.get("report") if isinstance(data.get("report"), dict) else {}
    safety = report.get("safety") if isinstance(report.get("safety"), dict) else {}
    execution_summary = report.get("executionSummary") if isinstance(report.get("executionSummary"), dict) else {}
    score = report.get("score") if isinstance(report.get("score"), dict) else {}
    return {
        "component": "AgentReadonlyGradingEvidenceGuidance",
        "mode": "MOCK_AGENT_RUNNER",
        "enabled": True,
        "source": "run_readonly_grading_evidence.data.report",
        "reportId": report.get("id"),
        "gradingId": report.get("gradingId"),
        "reportPath": report.get("reportPath"),
        "submissionRoot": report.get("submissionRoot"),
        "executed": execution_summary.get("executed", 0),
        "deferred": execution_summary.get("deferred", 0),
        "passed": execution_summary.get("passed", 0),
        "failed": execution_summary.get("failed", 0),
        "earnedScore": score.get("earnedScore"),
        "totalScore": score.get("totalScore"),
        "readonlyOnly": bool(safety.get("readonlyOnly", False)),
        "sandboxExecuted": bool(safety.get("sandboxExecuted", False)),
        "commandExecuted": bool(safety.get("commandExecuted", False)),
        "pytestExecuted": bool(safety.get("pytestExecuted", False)),
        "notebookExecuted": bool(safety.get("notebookExecuted", False)),
        "contestantCodeExecuted": bool(safety.get("contestantCodeExecuted", False)),
        "networkEnabled": bool(safety.get("networkEnabled", False)),
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "nextRecommendedAction": "human_review_readonly_grading_evidence_before_any_execution",
    }


def _build_controlled_grading_evidence_guidance(evidence_response: dict[str, Any] | None) -> dict[str, Any]:
    if not evidence_response:
        return {
            "component": "AgentControlledGradingEvidenceGuidance",
            "mode": "MOCK_AGENT_RUNNER",
            "enabled": False,
            "reason": "controlledGradingSubmission not provided",
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        }
    data = evidence_response.get("data") if isinstance(evidence_response.get("data"), dict) else {}
    report = data.get("report") if isinstance(data.get("report"), dict) else {}
    safety = report.get("safety") if isinstance(report.get("safety"), dict) else {}
    execution_summary = report.get("executionSummary") if isinstance(report.get("executionSummary"), dict) else {}
    score = report.get("score") if isinstance(report.get("score"), dict) else {}
    runner = report.get("runner") if isinstance(report.get("runner"), dict) else {}
    return {
        "component": "AgentControlledGradingEvidenceGuidance",
        "mode": "MOCK_AGENT_RUNNER",
        "enabled": True,
        "source": "run_controlled_grading_evidence.data.report",
        "reportId": report.get("id"),
        "gradingId": report.get("gradingId"),
        "reportPath": report.get("reportPath"),
        "submissionRoot": report.get("submissionRoot"),
        "runtime": runner.get("runtime"),
        "image": runner.get("image"),
        "supportedCheckTypes": runner.get("supportedCheckTypes", []),
        "deferredCheckTypes": runner.get("deferredCheckTypes", []),
        "executed": execution_summary.get("executed", 0),
        "deferred": execution_summary.get("deferred", 0),
        "passed": execution_summary.get("passed", 0),
        "failed": execution_summary.get("failed", 0),
        "earnedScore": score.get("earnedScore"),
        "totalScore": score.get("totalScore"),
        "readonlyOnly": bool(safety.get("readonlyOnly", False)),
        "sandboxExecuted": bool(safety.get("sandboxExecuted", False)),
        "commandExecuted": bool(safety.get("commandExecuted", False)),
        "pytestExecuted": bool(safety.get("pytestExecuted", False)),
        "notebookExecuted": bool(safety.get("notebookExecuted", False)),
        "contestantCodeExecuted": bool(safety.get("contestantCodeExecuted", False)),
        "unknownShellExecuted": bool(safety.get("unknownShellExecuted", False)),
        "networkEnabled": bool(safety.get("networkEnabled", False)),
        "hostExecutionAllowed": bool(safety.get("hostExecutionAllowed", False)),
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "nextRecommendedAction": "human_review_controlled_docker_grading_evidence_before_approval_or_publish",
    }


def _build_auto_grading_evidence_guidance(evidence_response: dict[str, Any] | None) -> dict[str, Any]:
    if not evidence_response:
        return {
            "component": "AgentAutoGradingEvidenceGuidance",
            "mode": "MOCK_AGENT_RUNNER",
            "enabled": False,
            "reason": "autoGradingSubmission not provided",
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        }
    data = evidence_response.get("data") if isinstance(evidence_response.get("data"), dict) else {}
    report = data.get("report") if isinstance(data.get("report"), dict) else {}
    safety = report.get("safety") if isinstance(report.get("safety"), dict) else {}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    coverage = report.get("evidenceCoverage") if isinstance(report.get("evidenceCoverage"), dict) else {}
    dsl_coverage = (
        report.get("gradingDslCoverageSummary")
        if isinstance(report.get("gradingDslCoverageSummary"), dict)
        else {}
    )
    readonly = coverage.get("readonlyStatic") if isinstance(coverage.get("readonlyStatic"), dict) else {}
    controlled = coverage.get("controlledDocker") if isinstance(coverage.get("controlledDocker"), dict) else {}
    steps = report.get("steps") if isinstance(report.get("steps"), list) else []
    return {
        "component": "AgentAutoGradingEvidenceGuidance",
        "mode": "MOCK_AGENT_RUNNER",
        "enabled": True,
        "source": "run_grading_evidence_auto.data.report",
        "reportId": report.get("id"),
        "gradingId": report.get("gradingId"),
        "reportPath": report.get("reportPath") or data.get("reportPath"),
        "submissionRoot": report.get("submissionRoot"),
        "sourceMode": report.get("sourceMode"),
        "sourceReportTotal": report.get("sourceReportTotal", 0),
        "stepTotal": len(steps),
        "stepIds": [step.get("id") for step in steps if isinstance(step, dict)],
        "warningsTotal": len(report.get("warnings") if isinstance(report.get("warnings"), list) else []),
        "checkTotal": summary.get("checkTotal", 0),
        "executed": summary.get("executed", 0),
        "deferred": summary.get("deferredCheckTotal", summary.get("deferred", 0)),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "earnedScore": summary.get("earnedScore"),
        "totalScore": summary.get("totalScore"),
        "coverageRatio": coverage.get("coverageRatio"),
        "readonlyCheckTotal": readonly.get("checkTotal", 0),
        "controlledCheckTotal": controlled.get("checkTotal", 0),
        "gradingDslCoverageStatus": dsl_coverage.get("status"),
        "gradingDslCheckTotal": dsl_coverage.get("dslCheckTotal", 0),
        "gradingDslEvidenceReadyTotal": dsl_coverage.get("evidenceReadyTotal", 0),
        "gradingDslMissingEvidenceTotal": dsl_coverage.get("missingEvidenceTotal", 0),
        "gradingDslMissingCheckIds": dsl_coverage.get("missingCheckIds", []),
        "gradingDslDecisionNoteRecommendation": dsl_coverage.get("decisionNoteRecommendation"),
        "gradingDslNextCoreActionId": dsl_coverage.get("nextCoreActionId"),
        "readonlyAlwaysRunsFirst": bool(safety.get("readonlyAlwaysRunsFirst", False)),
        "controlledCommandRequested": bool(safety.get("controlledCommandRequested", False)),
        "controlledCommandIncluded": bool(safety.get("controlledCommandIncluded", False)),
        "commandExecuted": bool(safety.get("commandExecuted", False)),
        "contestantCodeExecuted": bool(safety.get("contestantCodeExecuted", False)),
        "networkEnabled": bool(safety.get("networkEnabled", False)),
        "hostExecutionAllowed": bool(safety.get("hostExecutionAllowed", False)),
        "autoApproveAllowed": False,
        "batchStateChangeAllowed": False,
        "autoPublishAllowed": False,
        "realPublishAllowed": False,
        "nextRecommendedAction": "human_review_auto_grading_evidence_before_approval_or_publish",
    }


def _artifact_path_from_review_detail(review_detail_response: dict[str, Any], artifact_kind: str) -> str | None:
    review_detail = review_detail_response.get("data", {}).get("reviewDetail", {})
    if not isinstance(review_detail, dict):
        return None
    artifacts = review_detail.get("artifacts") if isinstance(review_detail.get("artifacts"), list) else []
    for artifact in artifacts:
        if isinstance(artifact, dict) and artifact.get("kind") == artifact_kind and artifact.get("path"):
            return str(artifact["path"])
    return None


def _enabled_import_action_total(review_detail_response: dict[str, Any], tool_name: str) -> int:
    review_detail = review_detail_response.get("data", {}).get("reviewDetail", {})
    if not isinstance(review_detail, dict):
        return 0
    action_panel = review_detail.get("platformImportPreviewActions")
    if not isinstance(action_panel, dict):
        return 0
    items = action_panel.get("items") if isinstance(action_panel.get("items"), list) else []
    return len(
        [
            item
            for item in items
            if isinstance(item, dict)
            and item.get("mcpTool") == tool_name
            and item.get("enabled") is True
        ]
    )


def _ensure_approved_import_action(
    *,
    review_detail_response: dict[str, Any],
    guidance: dict[str, Any],
    field: str,
    tool_name: str,
    label: str,
) -> None:
    if guidance["taskStatus"] != "APPROVED":
        raise RealDemoAgentRunnerError(
            f"APPROVED_{label.upper()}_TASK_REQUIRED",
            f"{label} 导入预览需要已人工审核通过的任务",
            [{"field": field, "reason": "任务状态必须是 APPROVED"}],
        )
    if _enabled_import_action_total(review_detail_response, tool_name) < 1:
        raise RealDemoAgentRunnerError(
            "IMPORT_PREVIEW_ACTION_NOT_AVAILABLE",
            f"已审核任务未开放 {label} 导入预览入口",
            [{"field": field, "reason": f"{tool_name} enabled action 必须存在"}],
        )


def plan_core_next_tool_from_readiness(
    *,
    task_id: str,
    reviewer: str,
    store_path: Path | None = None,
    root: Path = ROOT,
    trace_id: str | None = None,
    tool_profile: str | None = ALL_MCP_TOOL_PROFILE,
) -> dict[str, Any]:
    """Build a read-only agent plan from CoreWorkflowReadiness.nextToolRecommendation."""

    _validate_core_next_tool_plan_request(task_id=task_id, reviewer=reviewer)
    contract = _load_contract(root)
    run_trace_id = trace_id or f"trace_agent_plan_{uuid4().hex[:12]}"
    tool_profile_metadata = _agent_tool_profile_metadata(root, tool_profile)
    active_tool_names = _active_tool_names_for_profile(root, tool_profile_metadata["profile"])
    core_readiness_response = _run_tool(
        tool_name="get_core_workflow_readiness",
        arguments={"taskId": task_id},
        store_path=store_path,
        root=root,
        trace_id=run_trace_id,
        tool_profile=tool_profile_metadata["profile"],
    )
    plan = _build_core_next_tool_plan(
        core_readiness_response=core_readiness_response,
        task_id=task_id,
        reviewer=reviewer,
        tool_profile=tool_profile_metadata,
        active_tool_names=active_tool_names,
    )
    record = core_readiness_response.get("data", {}).get("mcpToolCallRecord", {})
    return {
        "component": "RealDemoAgentCoreNextToolPlanner",
        "mode": "MOCK_AGENT_RUNNER_READ_ONLY_PLAN",
        "contractId": contract["id"],
        "traceId": run_trace_id,
        "taskId": task_id,
        "reviewer": reviewer,
        "steps": [
            _step_result(
                step_id="read_core_workflow_readiness",
                order=1,
                tool_name="get_core_workflow_readiness",
                response=core_readiness_response,
                state_check="coreWorkflowReadinessReport.safety.readOnly == true",
                human_review_stop=True,
                mutates_state=False,
            ),
            {
                "id": "plan_recommended_next_tool",
                "order": 2,
                "tool": plan.get("toolName"),
                "status": "PLANNED_ONLY",
                "stateCheck": "nextToolRecommendation.autoExecuteAllowed == false",
                "humanReviewStop": True,
                "mutatesState": False,
                "mcpToolCallRecordId": None,
            },
        ],
        "summary": {
            "stepTotal": 2,
            "completedTotal": 1,
            "plannedOnlyTotal": 1,
            "taskStatus": plan.get("taskStatus"),
            "coreReady": plan.get("coreReady"),
            "coreStatus": plan.get("coreStatus"),
            "recommendedNextAction": plan.get("recommendedNextAction"),
            "finalReviewState": plan.get("finalReviewState"),
            "recommendedToolName": plan.get("toolName"),
            "reasonCode": plan.get("reasonCode"),
            "canCallToolAfterHumanConfirmation": plan.get("canCallToolAfterHumanConfirmation"),
            "manualActionRequired": plan.get("manualActionRequired"),
            "recommendedToolCalled": False,
            "toolProfile": tool_profile_metadata["profile"],
            "recommendedToolInProfile": plan.get("recommendedToolInProfile"),
            "blockedByToolProfile": plan.get("blockedByToolProfile"),
            "mcpToolCallRecordId": record.get("id") if isinstance(record, dict) else None,
        },
        "agentCoreNextToolPlan": plan,
        "toolProfile": tool_profile_metadata,
        "toolResponses": {
            "coreWorkflowReadiness": core_readiness_response,
        },
        "safety": plan["safety"],
    }


def execute_core_next_tool_from_readiness(
    *,
    task_id: str,
    reviewer: str,
    tool_arguments: dict[str, Any] | None = None,
    confirm_execute_recommended_tool: bool = False,
    store_path: Path | None = None,
    root: Path = ROOT,
    trace_id: str | None = None,
    tool_profile: str | None = ALL_MCP_TOOL_PROFILE,
) -> dict[str, Any]:
    """Execute exactly one recommended MCP tool after explicit human confirmation."""

    _validate_core_next_tool_plan_request(task_id=task_id, reviewer=reviewer)
    if tool_arguments is not None and not isinstance(tool_arguments, dict):
        raise RealDemoAgentRunnerError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": "toolArguments", "reason": "必须是 JSON object"}],
        )
    if not confirm_execute_recommended_tool:
        raise RealDemoAgentRunnerError(
            "CONFIRM_RECOMMENDED_TOOL_REQUIRED",
            "执行推荐工具前必须显式确认",
            [{"field": "confirmExecuteRecommendedTool", "reason": "必须为 true"}],
        )

    run_trace_id = trace_id or f"trace_agent_execute_{uuid4().hex[:12]}"
    tool_profile_metadata = _agent_tool_profile_metadata(root, tool_profile)
    plan_result = plan_core_next_tool_from_readiness(
        task_id=task_id,
        reviewer=reviewer,
        store_path=store_path,
        root=root,
        trace_id=run_trace_id,
        tool_profile=tool_profile_metadata["profile"],
    )
    plan = plan_result["agentCoreNextToolPlan"]
    tool_name = plan.get("toolName")
    if plan.get("blockedByToolProfile") is True:
        raise RealDemoAgentRunnerError(
            "RECOMMENDED_TOOL_NOT_IN_AGENT_PROFILE",
            "推荐工具不在当前 Agent MCP profile 中",
            [
                {"field": "agentCoreNextToolPlan.toolName", "reason": str(tool_name or "")},
                {"field": "toolProfile", "reason": str(tool_profile_metadata["profile"])},
            ],
        )
    if not tool_name or plan.get("toolAvailable") is not True:
        raise RealDemoAgentRunnerError(
            "NEXT_TOOL_MANUAL_ACTION_REQUIRED",
            "当前下一步需要人工动作，没有可执行推荐工具",
            [{"field": "agentCoreNextToolPlan.toolName", "reason": "推荐工具不可用"}],
        )
    if plan.get("canCallToolAfterHumanConfirmation") is not True:
        raise RealDemoAgentRunnerError(
            "NEXT_TOOL_NOT_CONFIRMABLE",
            "当前推荐工具不允许通过该 Agent 命令执行",
            [{"field": "agentCoreNextToolPlan.canCallToolAfterHumanConfirmation", "reason": "必须为 true"}],
        )
    if tool_name not in _SINGLE_EXECUTION_ALLOWED_TOOLS:
        raise RealDemoAgentRunnerError(
            "RECOMMENDED_TOOL_NOT_ALLOWED_FOR_SINGLE_EXECUTION",
            "推荐工具不在单步确认执行范围内",
            [{"field": "agentCoreNextToolPlan.toolName", "reason": f"{tool_name} 需要独立流程处理"}],
        )

    recommended_arguments = _build_confirmed_recommended_tool_arguments(
        plan=plan,
        task_id=task_id,
        reviewer=reviewer,
        tool_arguments=tool_arguments,
    )
    recommended_response = _run_tool(
        tool_name=tool_name,
        arguments=recommended_arguments,
        store_path=store_path,
        root=root,
        trace_id=run_trace_id,
        tool_profile=tool_profile_metadata["profile"],
    )
    record = recommended_response.get("data", {}).get("mcpToolCallRecord", {})
    post_core_readiness_response = _run_tool(
        tool_name="get_core_workflow_readiness",
        arguments={"taskId": task_id},
        store_path=store_path,
        root=root,
        trace_id=run_trace_id,
        tool_profile=tool_profile_metadata["profile"],
    )
    active_tool_names = _active_tool_names_for_profile(root, tool_profile_metadata["profile"])
    post_execution_plan = _build_core_next_tool_plan(
        core_readiness_response=post_core_readiness_response,
        task_id=task_id,
        reviewer=reviewer,
        tool_profile=tool_profile_metadata,
        active_tool_names=active_tool_names,
    )
    next_single_step_action_guide = _build_next_single_step_action_guide(
        plan=post_execution_plan,
        task_id=task_id,
        reviewer=reviewer,
    )
    post_readiness_record = post_core_readiness_response.get("data", {}).get("mcpToolCallRecord", {})
    contract = _load_contract(root)
    return {
        "component": "RealDemoAgentCoreNextToolExecutor",
        "mode": "MOCK_AGENT_RUNNER_SINGLE_CONFIRMED_TOOL_EXECUTION",
        "contractId": contract["id"],
        "traceId": run_trace_id,
        "taskId": task_id,
        "reviewer": reviewer,
        "steps": [
            plan_result["steps"][0],
            {
                "id": "execute_one_confirmed_recommended_tool",
                "order": 2,
                "tool": tool_name,
                "status": "COMPLETED",
                "stateCheck": "exactly one recommended MCP tool was called after explicit confirmation",
                "humanReviewStop": True,
                "mutatesState": True,
                "mcpToolCallRecordId": record.get("id") if isinstance(record, dict) else None,
            },
            {
                "id": "read_post_execution_core_workflow_readiness",
                "order": 3,
                "tool": "get_core_workflow_readiness",
                "status": "COMPLETED",
                "stateCheck": "postExecutionCoreNextToolPlan reflects next stop or next recommended tool",
                "humanReviewStop": True,
                "mutatesState": False,
                "mcpToolCallRecordId": post_readiness_record.get("id") if isinstance(post_readiness_record, dict) else None,
            },
        ],
        "summary": {
            "stepTotal": 3,
            "completedTotal": 3,
            "plannedOnlyTotal": 0,
            "taskStatus": plan.get("taskStatus"),
            "coreReady": plan.get("coreReady"),
            "coreStatus": plan.get("coreStatus"),
            "recommendedNextAction": plan.get("recommendedNextAction"),
            "recommendedToolName": tool_name,
            "executedToolName": tool_name,
            "executedToolTotal": 1,
            "reasonCode": plan.get("reasonCode"),
            "confirmedByHuman": True,
            "recommendedToolCalled": True,
            "postExecutionRecommendedNextAction": post_execution_plan.get("recommendedNextAction"),
            "finalReviewState": plan.get("finalReviewState"),
            "postExecutionFinalReviewState": post_execution_plan.get("finalReviewState"),
            "postExecutionRecommendedToolName": post_execution_plan.get("toolName"),
            "postExecutionReasonCode": post_execution_plan.get("reasonCode"),
            "postExecutionManualActionRequired": post_execution_plan.get("manualActionRequired"),
            "postExecutionCanCallToolAfterHumanConfirmation": post_execution_plan.get(
                "canCallToolAfterHumanConfirmation"
            ),
            "canContinueWithSameCommand": next_single_step_action_guide["canContinueWithSameCommand"],
            "requiresAdditionalArguments": next_single_step_action_guide["requiresAdditionalArguments"],
            "toolProfile": tool_profile_metadata["profile"],
            "postExecutionRecommendedToolInProfile": post_execution_plan.get("recommendedToolInProfile"),
            "postExecutionBlockedByToolProfile": post_execution_plan.get("blockedByToolProfile"),
            "mcpToolCallRecordId": record.get("id") if isinstance(record, dict) else None,
        },
        "agentCoreNextToolPlan": plan,
        "postExecutionCoreNextToolPlan": post_execution_plan,
        "nextSingleStepActionGuide": next_single_step_action_guide,
        "toolProfile": tool_profile_metadata,
        "executedTool": {
            "toolName": tool_name,
            "arguments": recommended_arguments,
            "mcpToolCallRecordId": record.get("id") if isinstance(record, dict) else None,
            "backendPath": record.get("backendPath") if isinstance(record, dict) else None,
        },
        "toolResponses": {
            "coreWorkflowReadiness": plan_result["toolResponses"]["coreWorkflowReadiness"],
            "recommendedTool": recommended_response,
            "postExecutionCoreWorkflowReadiness": post_core_readiness_response,
        },
        "safety": {
            "singleToolExecution": True,
            "confirmedByHuman": True,
            "readOnlyPlan": False,
            "realAgentStarted": False,
            "realMcpServerStarted": False,
            "recommendedToolCalled": True,
            "newLlmRequestSent": False,
            "realLlmCalled": False,
            "secretsRead": False,
            "networkAccess": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "databaseWritten": False,
            "realAgentImport": False,
            "autoExecuteAllowed": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublishAllowed": False,
        },
    }


def run_real_demo_agent_workflow(
    *,
    demo_source_path: str,
    reviewer: str,
    revision_comment: str = "补充步骤截图验收标准。",
    revision_priority: str = "HIGH",
    revision_output: str | None = None,
    approved_lab_task_id: str | None = None,
    lab_import_output: str | None = None,
    create_lab_mock_import: bool = False,
    lab_mock_import_output: str | None = None,
    approved_exam_task_id: str | None = None,
    exam_import_output: str | None = None,
    create_exam_mock_import: bool = False,
    exam_mock_import_output: str | None = None,
    approved_grading_task_id: str | None = None,
    grading_import_output: str | None = None,
    create_grading_mock_import: bool = False,
    grading_mock_import_output: str | None = None,
    readonly_grading_submission: str | None = None,
    readonly_grading_output: str | None = None,
    controlled_grading_submission: str | None = None,
    controlled_grading_output: str | None = None,
    controlled_grading_image: str | None = None,
    auto_grading_submission: str | None = None,
    auto_grading_output: str | None = None,
    auto_grading_include_controlled: bool = False,
    auto_grading_fail_on_controlled_unavailable: bool = False,
    auto_grading_image: str | None = None,
    store_path: Path | None = None,
    root: Path = ROOT,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Run the fixed mock agent workflow with existing MCP mock tools."""

    _validate_request(demo_source_path=demo_source_path, reviewer=reviewer, revision_priority=revision_priority)
    _validate_approved_task_request(
        approved_lab_task_id=approved_lab_task_id,
        lab_import_output=lab_import_output,
        create_lab_mock_import=create_lab_mock_import,
        lab_mock_import_output=lab_mock_import_output,
        approved_exam_task_id=approved_exam_task_id,
        exam_import_output=exam_import_output,
        create_exam_mock_import=create_exam_mock_import,
        exam_mock_import_output=exam_mock_import_output,
        approved_grading_task_id=approved_grading_task_id,
        grading_import_output=grading_import_output,
        create_grading_mock_import=create_grading_mock_import,
        grading_mock_import_output=grading_mock_import_output,
        readonly_grading_submission=readonly_grading_submission,
        readonly_grading_output=readonly_grading_output,
        controlled_grading_submission=controlled_grading_submission,
        controlled_grading_output=controlled_grading_output,
        controlled_grading_image=controlled_grading_image,
        auto_grading_submission=auto_grading_submission,
        auto_grading_output=auto_grading_output,
        auto_grading_include_controlled=auto_grading_include_controlled,
        auto_grading_fail_on_controlled_unavailable=auto_grading_fail_on_controlled_unavailable,
        auto_grading_image=auto_grading_image,
    )
    contract = _load_contract(root)
    run_trace_id = trace_id or f"trace_agent_{uuid4().hex[:12]}"
    output_path = revision_output or "examples/output/demo-agent-lab-revision.json"
    lab_import_output_path = lab_import_output or "examples/output/demo-agent-lab-import-preview.json"
    lab_mock_import_output_path = lab_mock_import_output or "examples/output/demo-agent-lab-mock-import.json"
    exam_import_output_path = exam_import_output or "examples/output/demo-agent-exam-import-preview.json"
    exam_mock_import_output_path = exam_mock_import_output or "examples/output/demo-agent-exam-mock-import.json"
    grading_import_output_path = grading_import_output or "examples/output/demo-agent-grading-import-preview.json"
    grading_mock_import_output_path = grading_mock_import_output or "examples/output/demo-agent-grading-mock-import.json"
    readonly_grading_output_path = readonly_grading_output or "examples/output/demo-agent-readonly-grading-evidence.json"
    controlled_grading_output_path = controlled_grading_output or "examples/output/demo-agent-controlled-grading-evidence.json"
    auto_grading_output_path = auto_grading_output or "examples/output/demo-agent-grading-evidence-auto.json"

    steps: list[dict[str, Any]] = [
        {
            "id": "open_static_demo",
            "order": 1,
            "tool": None,
            "status": "COMPLETED",
            "stateCheck": "frontend/real-demo.html visible",
            "humanReviewStop": False,
            "mutatesState": False,
            "evidencePath": "frontend/real-demo.html",
        }
    ]

    summary_response = _run_tool(
        tool_name="get_review_task_summary",
        arguments={"status": "WAITING_REVIEW"},
        store_path=store_path,
        root=root,
        trace_id=run_trace_id,
    )
    steps.append(
        _step_result(
            step_id="summarize_review_queue",
            order=2,
            tool_name="get_review_task_summary",
            response=summary_response,
            state_check="reviewTaskSummary.realDemoReviewQueue.waitingReviewTotal == 4",
            human_review_stop=True,
            mutates_state=False,
        )
    )

    created = _run_tool(
        tool_name="generate_lab_from_source",
        arguments={"input": demo_source_path},
        store_path=store_path,
        root=root,
        trace_id=run_trace_id,
    )
    task = created["data"]["task"]
    task_id = task["id"]
    steps.append(
        _step_result(
            step_id="create_local_lab_task",
            order=3,
            tool_name="generate_lab_from_source",
            response=created,
            state_check="task.status == WAITING_REVIEW",
            human_review_stop=True,
            mutates_state=True,
        )
    )

    quality_summary_response = _run_tool(
        tool_name="get_review_task_summary",
        arguments={"status": "WAITING_REVIEW", "taskType": "LAB_GENERATION"},
        store_path=store_path,
        root=root,
        trace_id=run_trace_id,
    )
    agent_review_triage = _build_quality_aware_review_triage(quality_summary_response)
    steps.append(
        _step_result(
            step_id="triage_provider_quality",
            order=4,
            tool_name="get_review_task_summary",
            response=quality_summary_response,
            state_check="providerQualityTaskSignal drives manual review recommendation",
            human_review_stop=True,
            mutates_state=False,
        )
    )

    review_detail_response = _run_tool(
        tool_name="get_review_detail",
        arguments={"taskId": task_id},
        store_path=store_path,
        root=root,
        trace_id=run_trace_id,
    )
    agent_review_detail_guidance = _build_review_detail_guidance(review_detail_response)
    steps.append(
        _step_result(
            step_id="inspect_review_detail",
            order=5,
            tool_name="get_review_detail",
            response=review_detail_response,
            state_check="reviewDetail.reviewPage.actionBar keeps publish blocked",
            human_review_stop=True,
            mutates_state=False,
        )
    )

    revision = _run_tool(
        tool_name="request_review_revision",
        arguments={
            "taskId": task_id,
            "reviewer": reviewer,
            "comment": revision_comment,
            "priority": revision_priority,
            "targetSections": ["steps"],
        },
        store_path=store_path,
        root=root,
        trace_id=run_trace_id,
    )
    revision_request = revision["data"]["revisionRequest"]
    revision_request_id = revision_request["id"]
    steps.append(
        _step_result(
            step_id="request_revision",
            order=6,
            tool_name="request_review_revision",
            response=revision,
            state_check="revisionRequest.taskStatusChanged == false",
            human_review_stop=True,
            mutates_state=True,
        )
    )

    regeneration = _run_tool(
        tool_name="regenerate_from_revision_mock",
        arguments={
            "taskId": task_id,
            "reviewer": reviewer,
            "revisionRequestId": revision_request_id,
            "output": output_path,
        },
        store_path=store_path,
        root=root,
        trace_id=run_trace_id,
    )
    mock_regeneration = regeneration["data"]["mockRegeneration"]
    steps.append(
        _step_result(
            step_id="create_mock_revision",
            order=7,
            tool_name="regenerate_from_revision_mock",
            response=regeneration,
            state_check="mockRegeneration.newTask.status == WAITING_REVIEW",
            human_review_stop=True,
            mutates_state=True,
        )
    )

    audit = _run_tool(
        tool_name="list_mcp_tool_call_records",
        arguments={"toolName": "regenerate_from_revision_mock", "traceId": run_trace_id},
        store_path=store_path,
        root=root,
        trace_id=run_trace_id,
    )
    steps.append(
        _step_result(
            step_id="inspect_audit",
            order=8,
            tool_name="list_mcp_tool_call_records",
            response=audit,
            state_check="mcpToolCallRecords include regenerate_from_revision_mock",
            human_review_stop=False,
            mutates_state=False,
        )
    )

    approved_review_detail_response: dict[str, Any] | None = None
    approved_review_detail_guidance: dict[str, Any] | None = None
    lab_import_preview_response: dict[str, Any] | None = None
    lab_import_preview_guidance: dict[str, Any] = _build_lab_import_preview_guidance(None)
    lab_mock_import_response: dict[str, Any] | None = None
    lab_mock_import_guidance: dict[str, Any] = _build_lab_mock_import_guidance(None)
    post_import_review_detail_response: dict[str, Any] | None = None
    approved_exam_review_detail_response: dict[str, Any] | None = None
    approved_exam_review_detail_guidance: dict[str, Any] | None = None
    exam_import_preview_response: dict[str, Any] | None = None
    exam_import_preview_guidance: dict[str, Any] = _build_exam_import_preview_guidance(None)
    exam_mock_import_response: dict[str, Any] | None = None
    exam_mock_import_guidance: dict[str, Any] = _build_exam_mock_import_guidance(None)
    post_exam_import_review_detail_response: dict[str, Any] | None = None
    approved_grading_review_detail_response: dict[str, Any] | None = None
    approved_grading_review_detail_guidance: dict[str, Any] | None = None
    grading_import_preview_response: dict[str, Any] | None = None
    grading_import_preview_guidance: dict[str, Any] = _build_grading_import_preview_guidance(None)
    grading_mock_import_response: dict[str, Any] | None = None
    grading_mock_import_guidance: dict[str, Any] = _build_grading_mock_import_guidance(None)
    post_grading_import_review_detail_response: dict[str, Any] | None = None
    readonly_grading_evidence_response: dict[str, Any] | None = None
    readonly_grading_evidence_guidance: dict[str, Any] = _build_readonly_grading_evidence_guidance(None)
    controlled_grading_evidence_response: dict[str, Any] | None = None
    controlled_grading_evidence_guidance: dict[str, Any] = _build_controlled_grading_evidence_guidance(None)
    auto_grading_evidence_response: dict[str, Any] | None = None
    auto_grading_evidence_guidance: dict[str, Any] = _build_auto_grading_evidence_guidance(None)
    agent_entity_readiness_response: dict[str, Any] | None = None
    agent_entity_readiness_guidance: dict[str, Any] = _build_agent_entity_readiness_guidance(None)
    if approved_lab_task_id:
        approved_review_detail_response = _run_tool(
            tool_name="get_review_detail",
            arguments={"taskId": approved_lab_task_id},
            store_path=store_path,
            root=root,
            trace_id=run_trace_id,
        )
        approved_review_detail_guidance = _build_review_detail_guidance(approved_review_detail_response)
        if approved_review_detail_guidance["taskStatus"] != "APPROVED":
            raise RealDemoAgentRunnerError(
                "APPROVED_LAB_TASK_REQUIRED",
                "Lab 导入预览需要已人工审核通过的 Lab 任务",
                [{"field": "approvedLabTaskId", "reason": "任务状态必须是 APPROVED"}],
            )
        if approved_review_detail_guidance["artifactKind"] != "LAB_DSL":
            raise RealDemoAgentRunnerError(
                "APPROVED_LAB_TASK_REQUIRED",
                "Lab 导入预览需要 Lab DSL 任务",
                [{"field": "approvedLabTaskId", "reason": "任务必须关联 LAB_DSL"}],
            )
        if approved_review_detail_guidance["platformImportPreviewEnabledTotal"] < 1:
            raise RealDemoAgentRunnerError(
                "IMPORT_PREVIEW_ACTION_NOT_AVAILABLE",
                "已审核任务未开放 Lab 导入预览入口",
                [{"field": "approvedLabTaskId", "reason": "platformImportPreviewActions.enabledTotal 必须大于 0"}],
            )
        steps.append(
            _step_result(
                step_id="inspect_approved_lab_detail",
                order=9,
                tool_name="get_review_detail",
                response=approved_review_detail_response,
                state_check="approved review detail exposes lab import preview action",
                human_review_stop=False,
                mutates_state=False,
            )
        )

        lab_import_preview_response = _run_tool(
            tool_name="create_lab_template_import_preview",
            arguments={
                "taskId": approved_lab_task_id,
                "reviewer": reviewer,
                "output": lab_import_output_path,
            },
            store_path=store_path,
            root=root,
            trace_id=run_trace_id,
        )
        lab_import_preview_guidance = _build_lab_import_preview_guidance(lab_import_preview_response)
        steps.append(
            _step_result(
                step_id="create_lab_import_preview",
                order=10,
                tool_name="create_lab_template_import_preview",
                response=lab_import_preview_response,
                state_check="labTemplateImportPreview.databaseWritten == false",
                human_review_stop=True,
                mutates_state=True,
            )
        )

        post_import_review_detail_response = _run_tool(
            tool_name="get_review_detail",
            arguments={"taskId": approved_lab_task_id},
            store_path=store_path,
            root=root,
            trace_id=run_trace_id,
        )
        steps.append(
            _step_result(
                step_id="inspect_lab_import_preview_signoff",
                order=11,
                tool_name="get_review_detail",
                response=post_import_review_detail_response,
                state_check="reviewDetail.platformImportPreview visible after local preview",
                human_review_stop=True,
                mutates_state=False,
            )
        )

        if create_lab_mock_import:
            lab_mock_import_response = _run_tool(
                tool_name="create_lab_template_mock_import",
                arguments={
                    "taskId": approved_lab_task_id,
                    "reviewer": reviewer,
                    "output": lab_mock_import_output_path,
                },
                store_path=store_path,
                root=root,
                trace_id=run_trace_id,
            )
            lab_mock_import_guidance = _build_lab_mock_import_guidance(lab_mock_import_response)
            steps.append(
                _step_result(
                    step_id="create_lab_mock_import",
                    order=len(steps) + 1,
                    tool_name="create_lab_template_mock_import",
                    response=lab_mock_import_response,
                    state_check="labTemplateMockImport.databaseWritten == false",
                    human_review_stop=True,
                    mutates_state=True,
                )
            )

    if approved_exam_task_id:
        next_order = len(steps) + 1
        approved_exam_review_detail_response = _run_tool(
            tool_name="get_review_detail",
            arguments={"taskId": approved_exam_task_id},
            store_path=store_path,
            root=root,
            trace_id=run_trace_id,
        )
        approved_exam_review_detail_guidance = _build_review_detail_guidance(approved_exam_review_detail_response)
        _ensure_approved_import_action(
            review_detail_response=approved_exam_review_detail_response,
            guidance=approved_exam_review_detail_guidance,
            field="approvedExamTaskId",
            tool_name="create_exam_question_import_preview",
            label="Exam",
        )
        steps.append(
            _step_result(
                step_id="inspect_approved_exam_detail",
                order=next_order,
                tool_name="get_review_detail",
                response=approved_exam_review_detail_response,
                state_check="approved review detail exposes exam import preview action",
                human_review_stop=False,
                mutates_state=False,
            )
        )

        exam_import_preview_response = _run_tool(
            tool_name="create_exam_question_import_preview",
            arguments={
                "taskId": approved_exam_task_id,
                "reviewer": reviewer,
                "output": exam_import_output_path,
            },
            store_path=store_path,
            root=root,
            trace_id=run_trace_id,
        )
        exam_import_preview_guidance = _build_exam_import_preview_guidance(exam_import_preview_response)
        steps.append(
            _step_result(
                step_id="create_exam_import_preview",
                order=next_order + 1,
                tool_name="create_exam_question_import_preview",
                response=exam_import_preview_response,
                state_check="examQuestionImportPreview.answerVisibleToCandidate == false",
                human_review_stop=True,
                mutates_state=True,
            )
        )

        post_exam_import_review_detail_response = _run_tool(
            tool_name="get_review_detail",
            arguments={"taskId": approved_exam_task_id},
            store_path=store_path,
            root=root,
            trace_id=run_trace_id,
        )
        steps.append(
            _step_result(
                step_id="inspect_exam_import_preview_signoff",
                order=next_order + 2,
                tool_name="get_review_detail",
                response=post_exam_import_review_detail_response,
                state_check="reviewDetail.platformImportPreview includes exam_question preview",
                human_review_stop=True,
                mutates_state=False,
            )
        )

        if create_exam_mock_import:
            exam_mock_import_response = _run_tool(
                tool_name="create_exam_question_mock_import",
                arguments={
                    "taskId": approved_exam_task_id,
                    "reviewer": reviewer,
                    "output": exam_mock_import_output_path,
                },
                store_path=store_path,
                root=root,
                trace_id=run_trace_id,
            )
            exam_mock_import_guidance = _build_exam_mock_import_guidance(exam_mock_import_response)
            steps.append(
                _step_result(
                    step_id="create_exam_mock_import",
                    order=len(steps) + 1,
                    tool_name="create_exam_question_mock_import",
                    response=exam_mock_import_response,
                    state_check="examQuestionMockImport.answerVisibleToCandidate == false",
                    human_review_stop=True,
                    mutates_state=True,
                )
            )

    if approved_grading_task_id:
        next_order = len(steps) + 1
        approved_grading_review_detail_response = _run_tool(
            tool_name="get_review_detail",
            arguments={"taskId": approved_grading_task_id},
            store_path=store_path,
            root=root,
            trace_id=run_trace_id,
        )
        approved_grading_review_detail_guidance = _build_review_detail_guidance(approved_grading_review_detail_response)
        _ensure_approved_import_action(
            review_detail_response=approved_grading_review_detail_response,
            guidance=approved_grading_review_detail_guidance,
            field="approvedGradingTaskId",
            tool_name="create_grading_rule_import_preview",
            label="Grading",
        )
        steps.append(
            _step_result(
                step_id="inspect_approved_grading_detail",
                order=next_order,
                tool_name="get_review_detail",
                response=approved_grading_review_detail_response,
                state_check="approved review detail exposes grading import preview action",
                human_review_stop=False,
                mutates_state=False,
            )
        )

        grading_import_preview_response = _run_tool(
            tool_name="create_grading_rule_import_preview",
            arguments={
                "taskId": approved_grading_task_id,
                "reviewer": reviewer,
                "output": grading_import_output_path,
            },
            store_path=store_path,
            root=root,
            trace_id=run_trace_id,
        )
        grading_import_preview_guidance = _build_grading_import_preview_guidance(grading_import_preview_response)
        steps.append(
            _step_result(
                step_id="create_grading_import_preview",
                order=next_order + 1,
                tool_name="create_grading_rule_import_preview",
                response=grading_import_preview_response,
                state_check="gradingRuleImportPreview.sandboxExecuted == false",
                human_review_stop=True,
                mutates_state=True,
            )
        )

        post_grading_import_review_detail_response = _run_tool(
            tool_name="get_review_detail",
            arguments={"taskId": approved_grading_task_id},
            store_path=store_path,
            root=root,
            trace_id=run_trace_id,
        )
        steps.append(
            _step_result(
                step_id="inspect_grading_import_preview_signoff",
                order=next_order + 2,
                tool_name="get_review_detail",
                response=post_grading_import_review_detail_response,
                state_check="reviewDetail.platformImportPreview includes grading_rule preview",
                human_review_stop=True,
                mutates_state=False,
            )
        )

        if create_grading_mock_import:
            grading_mock_import_response = _run_tool(
                tool_name="create_grading_rule_mock_import",
                arguments={
                    "taskId": approved_grading_task_id,
                    "reviewer": reviewer,
                    "output": grading_mock_import_output_path,
                },
                store_path=store_path,
                root=root,
                trace_id=run_trace_id,
            )
            grading_mock_import_guidance = _build_grading_mock_import_guidance(grading_mock_import_response)
            steps.append(
                _step_result(
                    step_id="create_grading_mock_import",
                    order=len(steps) + 1,
                    tool_name="create_grading_rule_mock_import",
                    response=grading_mock_import_response,
                    state_check="gradingRuleMockImport.sandboxExecuted == false",
                    human_review_stop=True,
                    mutates_state=True,
                )
            )

        if readonly_grading_submission:
            grading_dsl_path = _artifact_path_from_review_detail(
                post_grading_import_review_detail_response,
                "GRADING_DSL",
            )
            if not grading_dsl_path:
                raise RealDemoAgentRunnerError(
                    "GRADING_DSL_ARTIFACT_REQUIRED",
                    "只读评分证据需要已审核任务关联 Grading DSL Artifact",
                    [{"field": "approvedGradingTaskId", "reason": "missing GRADING_DSL artifact path"}],
                )
            next_order = len(steps) + 1
            readonly_grading_evidence_response = _run_tool(
                tool_name="run_readonly_grading_evidence",
                arguments={
                    "grading": grading_dsl_path,
                    "submission": readonly_grading_submission,
                    "output": readonly_grading_output_path,
                },
                store_path=store_path,
                root=root,
                trace_id=run_trace_id,
            )
            readonly_grading_evidence_guidance = _build_readonly_grading_evidence_guidance(
                readonly_grading_evidence_response
            )
            steps.append(
                _step_result(
                    step_id="collect_readonly_grading_evidence",
                    order=next_order,
                    tool_name="run_readonly_grading_evidence",
                    response=readonly_grading_evidence_response,
                    state_check="readonly grading evidence keeps contestantCodeExecuted == false",
                    human_review_stop=True,
                    mutates_state=True,
                )
            )

        if controlled_grading_submission:
            grading_dsl_path = _artifact_path_from_review_detail(
                post_grading_import_review_detail_response,
                "GRADING_DSL",
            )
            if not grading_dsl_path:
                raise RealDemoAgentRunnerError(
                    "GRADING_DSL_ARTIFACT_REQUIRED",
                    "受控 Docker 评分证据需要已审核任务关联 Grading DSL Artifact",
                    [{"field": "approvedGradingTaskId", "reason": "missing GRADING_DSL artifact path"}],
                )
            next_order = len(steps) + 1
            controlled_arguments = {
                "grading": grading_dsl_path,
                "submission": controlled_grading_submission,
                "output": controlled_grading_output_path,
            }
            if controlled_grading_image:
                controlled_arguments["image"] = controlled_grading_image
            controlled_grading_evidence_response = _run_tool(
                tool_name="run_controlled_grading_evidence",
                arguments=controlled_arguments,
                store_path=store_path,
                root=root,
                trace_id=run_trace_id,
            )
            controlled_grading_evidence_guidance = _build_controlled_grading_evidence_guidance(
                controlled_grading_evidence_response
            )
            steps.append(
                _step_result(
                    step_id="collect_controlled_grading_evidence",
                    order=next_order,
                    tool_name="run_controlled_grading_evidence",
                    response=controlled_grading_evidence_response,
                    state_check="controlled grading evidence keeps networkEnabled == false",
                    human_review_stop=True,
                    mutates_state=True,
                )
            )

        if auto_grading_submission:
            grading_dsl_path = _artifact_path_from_review_detail(
                post_grading_import_review_detail_response,
                "GRADING_DSL",
            )
            if not grading_dsl_path:
                raise RealDemoAgentRunnerError(
                    "GRADING_DSL_ARTIFACT_REQUIRED",
                    "自动评分证据需要已审核任务关联 Grading DSL Artifact",
                    [{"field": "approvedGradingTaskId", "reason": "missing GRADING_DSL artifact path"}],
                )
            next_order = len(steps) + 1
            auto_arguments: dict[str, Any] = {
                "taskId": approved_grading_task_id,
                "grading": grading_dsl_path,
                "submission": auto_grading_submission,
                "output": auto_grading_output_path,
                "includeControlledCommand": auto_grading_include_controlled,
                "failOnControlledUnavailable": auto_grading_fail_on_controlled_unavailable,
            }
            if auto_grading_image:
                auto_arguments["image"] = auto_grading_image
            auto_grading_evidence_response = _run_tool(
                tool_name="run_grading_evidence_auto",
                arguments=auto_arguments,
                store_path=store_path,
                root=root,
                trace_id=run_trace_id,
            )
            auto_grading_evidence_guidance = _build_auto_grading_evidence_guidance(
                auto_grading_evidence_response
            )
            steps.append(
                _step_result(
                    step_id="collect_auto_grading_evidence",
                    order=next_order,
                    tool_name="run_grading_evidence_auto",
                    response=auto_grading_evidence_response,
                    state_check="auto grading evidence keeps manual review and publish blocked",
                    human_review_stop=True,
                    mutates_state=True,
                )
            )

    if lab_import_preview_response or exam_import_preview_response or grading_import_preview_response:
        agent_entity_readiness_response = _run_tool(
            tool_name="get_agent_entity_readiness_report",
            arguments={},
            store_path=store_path,
            root=root,
            trace_id=run_trace_id,
        )
        agent_entity_readiness_guidance = _build_agent_entity_readiness_guidance(
            agent_entity_readiness_response
        )
        steps.append(
            _step_result(
                step_id="summarize_agent_entity_readiness",
                order=len(steps) + 1,
                tool_name="get_agent_entity_readiness_report",
                response=agent_entity_readiness_response,
                state_check="agentEntityReadinessReport is read-only and realAgentImport == false",
                human_review_stop=True,
                mutates_state=False,
            )
        )

    tool_responses: dict[str, Any] = {
        "reviewSummary": summary_response,
        "qualityReviewSummary": quality_summary_response,
        "reviewDetail": review_detail_response,
        "createdTask": created,
        "revisionRequest": revision,
        "mockRegeneration": regeneration,
        "audit": audit,
    }
    if approved_review_detail_response is not None:
        tool_responses["approvedReviewDetail"] = approved_review_detail_response
    if lab_import_preview_response is not None:
        tool_responses["labImportPreview"] = lab_import_preview_response
    if lab_mock_import_response is not None:
        tool_responses["labMockImport"] = lab_mock_import_response
    if post_import_review_detail_response is not None:
        tool_responses["postImportReviewDetail"] = post_import_review_detail_response
    if approved_exam_review_detail_response is not None:
        tool_responses["approvedExamReviewDetail"] = approved_exam_review_detail_response
    if exam_import_preview_response is not None:
        tool_responses["examImportPreview"] = exam_import_preview_response
    if exam_mock_import_response is not None:
        tool_responses["examMockImport"] = exam_mock_import_response
    if post_exam_import_review_detail_response is not None:
        tool_responses["postExamImportReviewDetail"] = post_exam_import_review_detail_response
    if approved_grading_review_detail_response is not None:
        tool_responses["approvedGradingReviewDetail"] = approved_grading_review_detail_response
    if grading_import_preview_response is not None:
        tool_responses["gradingImportPreview"] = grading_import_preview_response
    if grading_mock_import_response is not None:
        tool_responses["gradingMockImport"] = grading_mock_import_response
    if post_grading_import_review_detail_response is not None:
        tool_responses["postGradingImportReviewDetail"] = post_grading_import_review_detail_response
    if readonly_grading_evidence_response is not None:
        tool_responses["readonlyGradingEvidence"] = readonly_grading_evidence_response
    if controlled_grading_evidence_response is not None:
        tool_responses["controlledGradingEvidence"] = controlled_grading_evidence_response
    if auto_grading_evidence_response is not None:
        tool_responses["autoGradingEvidence"] = auto_grading_evidence_response
    if agent_entity_readiness_response is not None:
        tool_responses["agentEntityReadiness"] = agent_entity_readiness_response

    return {
        "component": "RealDemoAgentMockRunner",
        "mode": "MOCK_AGENT_RUNNER",
        "contractId": contract["id"],
        "traceId": run_trace_id,
        "goal": contract["agentGoal"],
        "input": {
            "demoSourcePath": demo_source_path,
            "reviewer": reviewer,
            "revisionPriority": revision_priority,
            "approvedLabTaskId": approved_lab_task_id,
            "createLabMockImport": create_lab_mock_import,
            "approvedExamTaskId": approved_exam_task_id,
            "createExamMockImport": create_exam_mock_import,
            "approvedGradingTaskId": approved_grading_task_id,
            "createGradingMockImport": create_grading_mock_import,
            "readonlyGradingSubmission": readonly_grading_submission,
            "controlledGradingSubmission": controlled_grading_submission,
            "controlledGradingImage": controlled_grading_image,
            "autoGradingSubmission": auto_grading_submission,
            "autoGradingIncludeControlled": auto_grading_include_controlled,
            "autoGradingFailOnControlledUnavailable": auto_grading_fail_on_controlled_unavailable,
            "autoGradingImage": auto_grading_image,
        },
        "steps": steps,
        "summary": {
            "stepTotal": len(steps),
            "completedTotal": len([step for step in steps if step["status"] == "COMPLETED"]),
            "humanReviewStopTotal": len([step for step in steps if step["humanReviewStop"]]),
            "mutatingStepTotal": len([step for step in steps if step["mutatesState"]]),
            "sourceTaskId": task_id,
            "sourceTaskStatus": task["status"],
            "revisionRequestId": revision_request_id,
            "newTaskId": mock_regeneration["newTask"]["id"],
            "newTaskStatus": mock_regeneration["newTask"]["status"],
            "newArtifactId": mock_regeneration["artifact"]["id"],
            "revisionOutput": output_path,
            "primaryRecommendedAction": agent_review_triage["primaryRecommendedAction"],
            "reviewDetailPrimaryRecommendedAction": agent_review_detail_guidance["primaryRecommendedAction"],
            "providerQualityAvailableTotal": agent_review_triage["providerQualityAvailableTotal"],
            "readyForReviewTotal": agent_review_triage["readyForReviewTotal"],
            "importPreviewEligibleNow": agent_review_triage["importPreviewEligibleNow"],
            "platformImportPreviewEnabledTotal": agent_review_detail_guidance["platformImportPreviewEnabledTotal"],
            "approvedLabTaskId": approved_lab_task_id,
            "labImportPreviewCreated": bool(lab_import_preview_response),
            "labImportPreviewOutput": lab_import_output_path if lab_import_preview_response else None,
            "labImportPreviewDraftId": lab_import_preview_guidance.get("draftId"),
            "labMockImportCreated": bool(lab_mock_import_response),
            "labMockImportOutput": lab_mock_import_output_path if lab_mock_import_response else None,
            "labMockImportEntityId": lab_mock_import_guidance.get("agentEntityId"),
            "approvedExamTaskId": approved_exam_task_id,
            "examImportPreviewCreated": bool(exam_import_preview_response),
            "examImportPreviewOutput": exam_import_output_path if exam_import_preview_response else None,
            "examImportPreviewDraftId": exam_import_preview_guidance.get("draftId"),
            "examMockImportCreated": bool(exam_mock_import_response),
            "examMockImportOutput": exam_mock_import_output_path if exam_mock_import_response else None,
            "examMockImportEntityId": exam_mock_import_guidance.get("agentEntityId"),
            "approvedGradingTaskId": approved_grading_task_id,
            "gradingImportPreviewCreated": bool(grading_import_preview_response),
            "gradingImportPreviewOutput": grading_import_output_path if grading_import_preview_response else None,
            "gradingImportPreviewDraftId": grading_import_preview_guidance.get("draftId"),
            "gradingMockImportCreated": bool(grading_mock_import_response),
            "gradingMockImportOutput": grading_mock_import_output_path if grading_mock_import_response else None,
            "gradingMockImportEntityId": grading_mock_import_guidance.get("agentEntityId"),
            "agentEntityMockImportCreatedTotal": len(
                [
                    response
                    for response in [
                        lab_mock_import_response,
                        exam_mock_import_response,
                        grading_mock_import_response,
                    ]
                    if response is not None
                ]
            ),
            "readonlyGradingEvidenceCreated": bool(readonly_grading_evidence_response),
            "readonlyGradingEvidenceOutput": readonly_grading_output_path if readonly_grading_evidence_response else None,
            "readonlyGradingEvidenceExecutedTotal": readonly_grading_evidence_guidance.get("executed", 0),
            "readonlyGradingEvidenceDeferredTotal": readonly_grading_evidence_guidance.get("deferred", 0),
            "readonlyGradingEvidenceEarnedScore": readonly_grading_evidence_guidance.get("earnedScore"),
            "readonlyGradingEvidenceTotalScore": readonly_grading_evidence_guidance.get("totalScore"),
            "controlledGradingEvidenceCreated": bool(controlled_grading_evidence_response),
            "controlledGradingEvidenceOutput": controlled_grading_output_path if controlled_grading_evidence_response else None,
            "controlledGradingEvidenceExecutedTotal": controlled_grading_evidence_guidance.get("executed", 0),
            "controlledGradingEvidenceDeferredTotal": controlled_grading_evidence_guidance.get("deferred", 0),
            "controlledGradingEvidenceEarnedScore": controlled_grading_evidence_guidance.get("earnedScore"),
            "controlledGradingEvidenceTotalScore": controlled_grading_evidence_guidance.get("totalScore"),
            "autoGradingEvidenceCreated": bool(auto_grading_evidence_response),
            "autoGradingEvidenceOutput": auto_grading_output_path if auto_grading_evidence_response else None,
            "autoGradingEvidenceSourceReportTotal": auto_grading_evidence_guidance.get("sourceReportTotal", 0),
            "autoGradingEvidenceExecutedTotal": auto_grading_evidence_guidance.get("executed", 0),
            "autoGradingEvidenceDeferredTotal": auto_grading_evidence_guidance.get("deferred", 0),
            "autoGradingEvidenceEarnedScore": auto_grading_evidence_guidance.get("earnedScore"),
            "autoGradingEvidenceTotalScore": auto_grading_evidence_guidance.get("totalScore"),
            "autoGradingEvidenceControlledIncluded": auto_grading_evidence_guidance.get(
                "controlledCommandIncluded", False
            ),
            "agentEntityReadinessReported": bool(agent_entity_readiness_response),
            "agentEntityReadyTotal": agent_entity_readiness_guidance.get("readyForManualAgentReviewTotal", 0),
            "agentEntityRequiredTotal": agent_entity_readiness_guidance.get("requiredTotal", 0),
            "agentEntityMissingPreviewTotal": agent_entity_readiness_guidance.get("missingPreviewTotal", 0),
            "agentEntityMissingMockImportTotal": agent_entity_readiness_guidance.get("missingMockImportTotal", 0),
            "agentEntitySignoffReadyTotal": agent_entity_readiness_guidance.get(
                "agentEntitySignoffReadyTotal", 0
            ),
            "agentEntitySignoffRecordedTotal": agent_entity_readiness_guidance.get(
                "agentEntitySignoffRecordedTotal", 0
            ),
            "postSignoffPrePublishReadyTotal": agent_entity_readiness_guidance.get(
                "postSignoffPrePublishReadyTotal", 0
            ),
            "agentEntityReadinessNextAction": agent_entity_readiness_guidance.get("nextRecommendedAction"),
        },
        "agentReviewTriage": agent_review_triage,
        "agentReviewDetailGuidance": agent_review_detail_guidance,
        "approvedLabReviewDetailGuidance": approved_review_detail_guidance,
        "agentLabImportPreviewGuidance": lab_import_preview_guidance,
        "agentLabMockImportGuidance": lab_mock_import_guidance,
        "approvedExamReviewDetailGuidance": approved_exam_review_detail_guidance,
        "agentExamImportPreviewGuidance": exam_import_preview_guidance,
        "agentExamMockImportGuidance": exam_mock_import_guidance,
        "approvedGradingReviewDetailGuidance": approved_grading_review_detail_guidance,
        "agentGradingImportPreviewGuidance": grading_import_preview_guidance,
        "agentGradingMockImportGuidance": grading_mock_import_guidance,
        "agentReadonlyGradingEvidenceGuidance": readonly_grading_evidence_guidance,
        "agentControlledGradingEvidenceGuidance": controlled_grading_evidence_guidance,
        "agentAutoGradingEvidenceGuidance": auto_grading_evidence_guidance,
        "agentAgentEntityReadinessGuidance": agent_entity_readiness_guidance,
        "toolResponses": tool_responses,
        "safety": {
            "realAgentStarted": False,
            "externalPlatformConnected": False,
            "newLlmRequestSent": False,
            "realLlmCalled": False,
            "secretsRead": False,
            "networkAccess": False,
            "realMcpServerStarted": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "controlledSandboxExecuted": controlled_grading_evidence_guidance.get("sandboxExecuted", False),
            "controlledCommandExecuted": controlled_grading_evidence_guidance.get("commandExecuted", False),
            "controlledContestantCodeExecuted": controlled_grading_evidence_guidance.get("contestantCodeExecuted", False),
            "controlledNetworkEnabled": controlled_grading_evidence_guidance.get("networkEnabled", False),
            "autoGradingEvidenceCreated": bool(auto_grading_evidence_response),
            "autoGradingControlledCommandIncluded": auto_grading_evidence_guidance.get(
                "controlledCommandIncluded", False
            ),
            "autoGradingContestantCodeExecuted": auto_grading_evidence_guidance.get("contestantCodeExecuted", False),
            "autoGradingNetworkEnabled": auto_grading_evidence_guidance.get("networkEnabled", False),
            "autoApproveAllowed": False,
            "batchStateChangeAllowed": False,
            "autoPublishAllowed": False,
            "realPublish": False,
            "databaseWritten": False,
            "realAgentImport": False,
            "sourceTaskStatusUnchanged": True,
            "newTaskWaitingReview": mock_regeneration["newTask"]["status"] == "WAITING_REVIEW",
        },
    }
