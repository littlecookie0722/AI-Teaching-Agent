"""Local-core MCP Agent MVP with an auditable, review-gated tool plan."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from mcp_server import DEFAULT_MCP_TOOL_PROFILE, McpToolError, invoke_mcp_tool, mcp_tool_profile_metadata


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUBMISSION = "examples/submissions/readonly-demo"
DEFAULT_GRADING_EVIDENCE_OUTPUT = "examples/output/local-core-agent-grading-evidence.json"


class LocalCoreAgentError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        errors: list[dict[str, str]] | None = None,
        *,
        stage: str | None = None,
        tool_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []
        self.stage = stage
        self.tool_name = tool_name

    def diagnostic(self) -> dict[str, Any]:
        """Return a JSON-safe operator hint without exposing request secrets."""
        action_by_code = {
            "VALIDATION_ERROR": "修正输入路径、审核人、输出路径或提交目录后重新运行。",
            "AGENT_RUN_RECORD_INVALID": "选择由 agent local-core run 生成的完整 JSON run record 后重新 replay。",
            "AGENT_TASK_NOT_APPROVED": "先由人工审核任务，确认状态为 APPROVED 后再传入该任务 ID。",
            "MCP_TOOL_NOT_IN_PROFILE": "当前工具不属于 local-core-mvp；保持在本地停止线，不要改用真实平台工具。",
            "AGENT_RESPONSE_SHAPE_INVALID": "检查关联 DSL、评分 evidence 或本地导入产物是否存在且格式有效，然后重新运行。",
        }
        return {
            "component": "LocalCoreAgentDiagnostic",
            "code": self.code,
            "stage": self.stage or "agent_run",
            "tool": self.tool_name,
            "operatorAction": action_by_code.get(self.code, "根据 errors 中的字段修正本地输入或工具状态后重新运行。"),
            "retryAllowed": self.code not in {"MCP_TOOL_NOT_IN_PROFILE"},
            "realPlatformActionRequired": False,
            "secretsRequired": False,
        }


def run_local_core_agent(
    *,
    input_path: str,
    reviewer: str,
    output_path: str,
    submission_path: str = DEFAULT_SUBMISSION,
    grading_evidence_output: str = DEFAULT_GRADING_EVIDENCE_OUTPUT,
    approved_lab_task_id: str | None = None,
    approved_exam_task_id: str | None = None,
    approved_grading_task_id: str | None = None,
    store_path: Path | None = None,
    root: Path = ROOT,
    trace_id: str | None = None,
    replayed_from: str | None = None,
) -> dict[str, Any]:
    """Run one deterministic local-core agent path and persist an audit record.

    Generation always stops at ``WAITING_REVIEW``. The optional approved task IDs
    are a separate, human-approved continuation for local preview/mock/dry-run.
    """

    _validate_request(input_path, reviewer, output_path, submission_path)
    run_id = f"local_agent_{uuid4().hex[:12]}"
    run_trace_id = trace_id or f"trace_{run_id}"
    profile = mcp_tool_profile_metadata(DEFAULT_MCP_TOOL_PROFILE, root)
    steps: list[dict[str, Any]] = []
    def call(step_id: str, tool_name: str, arguments: dict[str, Any], *, review_stop: bool, mutates: bool) -> dict[str, Any]:
        response = _call_tool(
            tool_name=tool_name,
            arguments=arguments,
            store_path=store_path,
            root=root,
            trace_id=run_trace_id,
        )
        steps.append(_completed_step(step_id, len(steps) + 1, tool_name, response, review_stop, mutates))
        return response

    material = call("analyze_material", "analyze_material", {"input": input_path}, review_stop=False, mutates=False)
    lab = call("generate_lab", "generate_lab_from_source", {"input": input_path}, review_stop=True, mutates=True)
    lab_data = _data(lab)
    lab_task = _task(lab_data, "Lab")
    lab_generation = lab_data.get("providerGeneration") if isinstance(lab_data.get("providerGeneration"), dict) else {}
    lab_id = str(_require(lab_generation, "dslId", "generate_lab_from_source"))

    exam_grading = call(
        "generate_exam_grading",
        "generate_exam_from_lab",
        {"labId": lab_id},
        review_stop=True,
        mutates=True,
    )
    exam_grading_data = _data(exam_grading)
    exam_task = _task(exam_grading_data, "Exam/Grading")
    grading_path = str(_require(exam_grading_data, "gradingDslPath", "generate_exam_from_lab"))

    ppt = call("generate_ppt", "generate_ppt", {"input": input_path}, review_stop=True, mutates=True)
    ppt_data = _data(ppt)
    ppt_task = _task(ppt_data, "PPT")

    grading = call(
        "collect_grading_evidence",
        "run_grading_evidence_auto",
        {
            "grading": grading_path,
            "submission": submission_path,
            "output": grading_evidence_output,
            "taskId": str(exam_task["id"]),
        },
        review_stop=True,
        mutates=True,
    )
    grading_data = _data(grading)

    review_entries: list[dict[str, str]] = []
    for label, task in (("Lab", lab_task), ("Exam/Grading", exam_task), ("PPT", ppt_task)):
        task_id = str(task["id"])
        detail = call(
            f"inspect_{label.lower().replace('/', '_')}_review",
            "get_review_detail",
            {"taskId": task_id},
            review_stop=True,
            mutates=False,
        )
        review_entries.append(
            {
                "label": label,
                "taskId": task_id,
                "status": str(_review_task(detail).get("status") or task.get("status")),
                "route": f"review-center.html?taskId={task_id}",
            }
        )

    local_import: list[dict[str, Any]] = []
    approved = {
        "lab": approved_lab_task_id,
        "exam": approved_exam_task_id,
        "grading": approved_grading_task_id,
    }
    for kind, task_id in approved.items():
        if task_id:
            _validate_approved_task(kind=kind, task_id=task_id, call=call)
            local_import.append(
                _run_local_import_pipeline(
                    kind=kind,
                    task_id=task_id,
                    reviewer=reviewer,
                    output_root=Path(output_path).parent,
                    store_path=store_path,
                    root=root,
                    trace_id=run_trace_id,
                    call=call,
                )
            )

    pending_import_plan = _pending_import_plan(reviewer, lab_task, exam_task)
    import_completed = bool(local_import) and all(item["status"] == "COMPLETED" for item in local_import)
    stop_reason = "LOCAL_CORE_MVP_STOP_LINE_REACHED" if import_completed else "WAITING_REVIEW_REQUIRED"
    report = {
        "component": "LocalCoreAgentRun",
        "mode": "LOCAL_CORE_AGENT_MVP",
        "runId": run_id,
        "traceId": run_trace_id,
        "replayedFrom": replayed_from,
        "input": {"path": input_path, "reviewer": reviewer, "submissionPath": submission_path},
        "toolProfile": profile,
        "plan": {
            "goal": "generate review-gated local teaching artifacts and stop before platform handoff",
            "steps": [
                "analyze_material",
                "generate_lab_from_source",
                "generate_exam_from_lab",
                "generate_ppt",
                "run_grading_evidence_auto",
                "get_review_detail",
                "human approval before local import-preview/mock-import/import-dry-run",
            ],
            "plannedLocalImportAfterHumanApproval": pending_import_plan,
        },
        "steps": steps,
        "artifacts": {
            "labDslPath": lab_data.get("dslPath"),
            "examDslPath": exam_grading_data.get("examDslPath"),
            "gradingDslPath": grading_path,
            "pptDslPath": ppt_data.get("pptDslPath"),
            "gradingEvidencePath": grading_data.get("reportPath"),
        },
        "tasks": {"lab": lab_task, "examGrading": exam_task, "ppt": ppt_task},
        "reviewEntries": review_entries,
        "localImport": local_import,
        "stopReason": {
            "code": stop_reason,
            "message": (
                "已完成本地 import-preview/mock-import/import-dry-run，停止在本地 MVP 交接点。"
                if import_completed
                else "生成产物均保持 WAITING_REVIEW；必须由人工审核后才可执行本地导入预览链路。"
            ),
            "nextHumanAction": "review_generated_artifacts" if not import_completed else "review_local_import_dry_run",
        },
        "safety": {
            "toolProfileEnforced": profile["profile"] == DEFAULT_MCP_TOOL_PROFILE,
            "realAgentStarted": False,
            "realLlmCalled": False,
            "secretsRead": False,
            "networkAccess": False,
            "realAgentImport": False,
            "autoApproveAllowed": False,
            "autoPublishAllowed": False,
            "realPublish": False,
            "controlledCommandRequested": False,
            "contestantCodeExecuted": bool(_data(grading).get("report", {}).get("safety", {}).get("contestantCodeExecuted", False)),
        },
        "replay": {
            "command": f"python lab_cli.py agent local-core replay --record {output_path} --output <new-run-record.json>",
            "recordPath": output_path,
        },
    }
    report["operatorSummary"] = _operator_summary(
        steps=steps,
        review_entries=review_entries,
        local_import=local_import,
        stop_reason=stop_reason,
    )
    report["nextActions"] = _next_actions(
        reviewer=reviewer,
        review_entries=review_entries,
        local_import=local_import,
        output_path=output_path,
        stop_reason=stop_reason,
    )
    _write_record(Path(output_path), report)
    return report


def replay_local_core_agent(
    *,
    record_path: str,
    output_path: str,
    store_path: Path | None = None,
    root: Path = ROOT,
    trace_id: str | None = None,
) -> dict[str, Any]:
    path = Path(record_path)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        raise LocalCoreAgentError("VALIDATION_ERROR", "参数错误", [{"field": "record", "reason": "文件不存在"}])
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LocalCoreAgentError("VALIDATION_ERROR", "参数错误", [{"field": "record", "reason": "不是合法 JSON"}]) from exc
    source = record.get("input") if isinstance(record, dict) else None
    if not isinstance(source, dict) or not source.get("path") or not source.get("reviewer"):
        raise LocalCoreAgentError("AGENT_RUN_RECORD_INVALID", "Agent run record 缺少可复放输入", [{"field": "input", "reason": "path 和 reviewer 必填"}])
    approved = record.get("localImport") if isinstance(record.get("localImport"), list) else []
    task_ids = {item.get("kind"): item.get("taskId") for item in approved if isinstance(item, dict)}
    return run_local_core_agent(
        input_path=str(source["path"]),
        reviewer=str(source["reviewer"]),
        output_path=output_path,
        submission_path=str(source.get("submissionPath") or DEFAULT_SUBMISSION),
        approved_lab_task_id=_optional_str(task_ids.get("lab")),
        approved_exam_task_id=_optional_str(task_ids.get("exam")),
        approved_grading_task_id=_optional_str(task_ids.get("grading")),
        store_path=store_path,
        root=root,
        trace_id=trace_id,
        replayed_from=str(record_path),
    )


def _run_local_import_pipeline(
    *,
    kind: str,
    task_id: str,
    reviewer: str,
    output_root: Path,
    store_path: Path | None,
    root: Path,
    trace_id: str,
    call,
) -> dict[str, Any]:
    tools = {
        "lab": ("create_lab_template_import_preview", "create_lab_template_mock_import"),
        "exam": ("create_exam_question_import_preview", "create_exam_question_mock_import"),
        "grading": ("create_grading_rule_import_preview", "create_grading_rule_mock_import"),
    }
    preview_tool, mock_tool = tools[kind]
    preview = call(
        f"{kind}_import_preview",
        preview_tool,
        {"taskId": task_id, "reviewer": reviewer, "output": str(output_root / f"local-core-agent-{kind}-preview.json")},
        review_stop=True,
        mutates=True,
    )
    mocked = call(
        f"{kind}_mock_import",
        mock_tool,
        {"taskId": task_id, "reviewer": reviewer, "output": str(output_root / f"local-core-agent-{kind}-mock-import.json")},
        review_stop=True,
        mutates=True,
    )
    entity = _find_entity(_data(mocked))
    entity_id = str(entity["id"])
    dry_run = call(
        f"{kind}_import_dry_run",
        "create_agent_entity_import_dry_run",
        {"id": entity_id, "reviewer": reviewer, "output": str(output_root / f"local-core-agent-{kind}-dry-run.json")},
        review_stop=True,
        mutates=True,
    )
    return {
        "kind": kind,
        "taskId": task_id,
        "status": "COMPLETED",
        "previewTool": preview_tool,
        "mockImportTool": mock_tool,
        "agentEntityId": entity_id,
        "dryRunTool": "create_agent_entity_import_dry_run",
        "previewRecordId": _record_id(preview),
        "mockImportRecordId": _record_id(mocked),
        "dryRunRecordId": _record_id(dry_run),
    }


def _validate_approved_task(*, kind: str, task_id: str, call) -> None:
    detail = call(
        f"validate_{kind}_import_approval",
        "get_review_detail",
        {"taskId": task_id},
        review_stop=True,
        mutates=False,
    )
    task = _review_task(detail)
    if not isinstance(task, dict) or not task.get("id"):
        raise LocalCoreAgentError(
            "AGENT_RESPONSE_SHAPE_INVALID",
            "审核详情未返回任务信息",
            [{"field": "data.task.id", "reason": "required"}],
            stage="validate_local_import",
            tool_name="get_review_detail",
        )
    if task.get("status") != "APPROVED":
        raise LocalCoreAgentError(
            "AGENT_TASK_NOT_APPROVED",
            "本地导入要求任务已由人工审核通过",
            [
                {"field": "taskId", "reason": str(task.get("id"))},
                {"field": "status", "reason": f"expected APPROVED, actual {task.get('status') or 'UNKNOWN'}"},
            ],
            stage="validate_local_import",
            tool_name="get_review_detail",
        )


def _operator_summary(
    *,
    steps: list[dict[str, Any]],
    review_entries: list[dict[str, str]],
    local_import: list[dict[str, Any]],
    stop_reason: str,
) -> dict[str, Any]:
    waiting_review_total = sum(1 for item in review_entries if item.get("status") == "WAITING_REVIEW")
    return {
        "component": "LocalCoreAgentOperatorSummary",
        "phase": "LOCAL_IMPORT_COMPLETE" if stop_reason == "LOCAL_CORE_MVP_STOP_LINE_REACHED" else "HUMAN_REVIEW_REQUIRED",
        "completedToolStepTotal": len(steps),
        "reviewTaskTotal": len(review_entries),
        "waitingReviewTaskTotal": waiting_review_total,
        "localImportCompletedTotal": len(local_import),
        "actionRequired": "review_local_dry_run" if stop_reason == "LOCAL_CORE_MVP_STOP_LINE_REACHED" else "human_review",
        "message": (
            "本地导入预览链路已完成，当前演示在本地 dry-run DTO 停止。"
            if stop_reason == "LOCAL_CORE_MVP_STOP_LINE_REACHED"
            else "生成和评分 evidence 已完成；所有内容仍需人工审核，Agent 不会自动批准或发布。"
        ),
        "realPlatformActionRequired": False,
        "autoApproveAllowed": False,
        "autoPublishAllowed": False,
    }


def _next_actions(
    *,
    reviewer: str,
    review_entries: list[dict[str, str]],
    local_import: list[dict[str, Any]],
    output_path: str,
    stop_reason: str,
) -> list[dict[str, Any]]:
    if stop_reason == "LOCAL_CORE_MVP_STOP_LINE_REACHED":
        return [
            {
                "id": "review_local_dry_run",
                "kind": "HUMAN_REVIEW",
                "required": True,
                "message": "核对本地 import-preview、mock-import 和 import-dry-run DTO；不得发送真实平台请求。",
                "localImportKinds": [item["kind"] for item in local_import],
                "blockedActions": ["import-send", "import-status", "publish"],
            }
        ]

    return [
        {
            "id": "review_generated_artifacts",
            "kind": "HUMAN_REVIEW",
            "required": True,
            "message": "逐项查看 DSL、候选人安全预览和评分 evidence，并仅在人工确认后批准任务。",
            "reviewRoutes": [entry["route"] for entry in review_entries],
            "approvalCommands": [
                f"python lab_cli.py review approve --task-id {entry['taskId']} --reviewer {reviewer}"
                for entry in review_entries
            ],
            "autoApproveAllowed": False,
        },
        {
            "id": "continue_local_import_after_approval",
            "kind": "LOCAL_AGENT_RUN",
            "required": False,
            "message": "仅对已批准的 Lab、Exam 和 Grading 任务，显式传入任务 ID 继续本地导入预览链路。",
            "commandTemplate": (
                "python lab_cli.py agent local-core run --input <input.md> --reviewer "
                f"{reviewer} --output <local-import-run.json> --approved-lab-task-id <lab_task_id> "
                "--approved-exam-task-id <exam_task_id> --approved-grading-task-id <grading_task_id>"
            ),
            "sourceRunRecord": output_path,
            "requiresHumanApproval": True,
            "realPlatformActionRequired": False,
        },
    ]


def _pending_import_plan(reviewer: str, lab_task: dict[str, Any], exam_task: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "kind": "lab",
            "taskId": lab_task["id"],
            "requiredStatus": "APPROVED",
            "tools": ["create_lab_template_import_preview", "create_lab_template_mock_import", "create_agent_entity_import_dry_run"],
            "reviewer": reviewer,
        },
        {
            "kind": "exam",
            "taskId": exam_task["id"],
            "requiredStatus": "APPROVED",
            "tools": ["create_exam_question_import_preview", "create_exam_question_mock_import", "create_agent_entity_import_dry_run"],
            "reviewer": reviewer,
        },
        {
            "kind": "grading",
            "taskId": exam_task["id"],
            "requiredStatus": "APPROVED",
            "tools": ["create_grading_rule_import_preview", "create_grading_rule_mock_import", "create_agent_entity_import_dry_run"],
            "reviewer": reviewer,
        },
    ]


def _call_tool(*, tool_name: str, arguments: dict[str, Any], store_path: Path | None, root: Path, trace_id: str) -> dict[str, Any]:
    try:
        response = invoke_mcp_tool(
            tool_name,
            arguments,
            store_path=store_path,
            root=root,
            actor="local-core-agent",
            trace_id=trace_id,
            profile=DEFAULT_MCP_TOOL_PROFILE,
        )
    except McpToolError as exc:
        raise LocalCoreAgentError(
            exc.code,
            exc.message,
            exc.errors,
            stage="mcp_tool_call",
            tool_name=tool_name,
        ) from exc
    if response.get("success") is not True:
        raise LocalCoreAgentError(
            str(response.get("code") or "AGENT_TOOL_FAILED"),
            str(response.get("message") or "MCP 工具调用失败"),
            response.get("errors") or [],
            stage="mcp_tool_call",
            tool_name=tool_name,
        )
    return response


def _completed_step(step_id: str, order: int, tool_name: str, response: dict[str, Any], review_stop: bool, mutates: bool) -> dict[str, Any]:
    label, purpose = _step_presentation(step_id, tool_name)
    return {
        "id": step_id,
        "order": order,
        "tool": tool_name,
        "label": label,
        "purpose": purpose,
        "status": "COMPLETED",
        "humanReviewStop": review_stop,
        "mutatesLocalState": mutates,
        "mcpToolCallRecordId": _record_id(response),
    }


def _step_presentation(step_id: str, tool_name: str) -> tuple[str, str]:
    presentation = {
        "analyze_material": ("分析教学素材", "识别素材主题和生成所需上下文。"),
        "generate_lab": ("生成 Lab DSL", "生成实验草稿，并创建待人工审核任务。"),
        "generate_exam_grading": ("生成 Exam 与 Grading DSL", "从 Lab 草稿生成试题和评分规则，保持候选人答案隔离。"),
        "generate_ppt": ("生成 PPT DSL", "生成教学演示草稿，并创建待人工审核任务。"),
        "collect_grading_evidence": ("收集评分 evidence", "以受控只读方式生成可审核的评分证据。"),
    }
    if step_id in presentation:
        return presentation[step_id]
    if step_id.startswith("inspect_"):
        return ("读取审核详情", "确认任务状态、审核入口和人工复核证据。")
    if step_id.startswith("validate_"):
        return ("确认人工批准", "仅检查任务是否已被人工审核通过，不改变审核状态。")
    if step_id.endswith("_import_preview"):
        return ("生成本地导入预览", "生成本地平台实体映射预览，不发送平台请求。")
    if step_id.endswith("_mock_import"):
        return ("写入本地 Mock 实体", "仅写入本地 Mock store，便于检查导入结果。")
    if step_id.endswith("_import_dry_run"):
        return ("生成本地导入 dry-run DTO", "生成本地 DTO 并在当前 MVP 停止。")
    return (tool_name, "执行 local-core-mvp 中已验证的本地工具。")


def _data(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    return data if isinstance(data, dict) else {}


def _review_task(response: dict[str, Any]) -> dict[str, Any]:
    data = _data(response)
    direct_task = data.get("task")
    if isinstance(direct_task, dict):
        return direct_task
    review_detail = data.get("reviewDetail")
    if isinstance(review_detail, dict) and isinstance(review_detail.get("task"), dict):
        return review_detail["task"]
    return {}


def _task(data: dict[str, Any], label: str) -> dict[str, Any]:
    task = data.get("task")
    if not isinstance(task, dict) or not task.get("id") or task.get("status") != "WAITING_REVIEW":
        raise LocalCoreAgentError(
            "AGENT_RESPONSE_SHAPE_INVALID",
            f"{label} 生成结果未返回 WAITING_REVIEW 任务",
            [{"field": "data.task", "reason": "id 和 WAITING_REVIEW 必填"}],
        )
    return task


def _require(data: dict[str, Any], key: str, tool_name: str) -> Any:
    if not data.get(key):
        raise LocalCoreAgentError("AGENT_RESPONSE_SHAPE_INVALID", f"{tool_name} 响应缺少 {key}", [{"field": f"data.{key}", "reason": "required"}])
    return data[key]


def _find_entity(data: dict[str, Any]) -> dict[str, Any]:
    for key in ("agentEntity", "entity", "mockImport"):
        candidate = data.get(key)
        if isinstance(candidate, dict) and candidate.get("id"):
            return candidate
    for value in data.values():
        if isinstance(value, dict) and value.get("id") and (value.get("entityType") or value.get("sourceTaskId")):
            return value
    raise LocalCoreAgentError("AGENT_RESPONSE_SHAPE_INVALID", "本地 mock-import 未返回平台实体 ID", [{"field": "data.agentEntity.id", "reason": "required"}])


def _record_id(response: dict[str, Any]) -> str | None:
    record = _data(response).get("mcpToolCallRecord")
    return str(record["id"]) if isinstance(record, dict) and record.get("id") else None


def _validate_request(input_path: str, reviewer: str, output_path: str, submission_path: str) -> None:
    for field, value in (("input", input_path), ("reviewer", reviewer), ("output", output_path), ("submission", submission_path)):
        if not value:
            raise LocalCoreAgentError("VALIDATION_ERROR", "参数错误", [{"field": field, "reason": "缺少参数"}])
    source = Path(input_path)
    if not source.is_absolute():
        source = ROOT / source
    if not source.is_file():
        raise LocalCoreAgentError("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "文件不存在"}])
    submission = Path(submission_path)
    if not submission.is_absolute():
        submission = ROOT / submission
    if not submission.is_dir():
        raise LocalCoreAgentError("VALIDATION_ERROR", "参数错误", [{"field": "submission", "reason": "目录不存在"}])


def _write_record(path: Path, payload: dict[str, Any]) -> None:
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _optional_str(value: Any) -> str | None:
    return str(value) if value else None
