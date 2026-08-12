import json
from pathlib import Path

import pytest

from agents.local_core_agent import LocalCoreAgentError, replay_local_core_agent, run_local_core_agent
from cli.ai_task import TaskStatus
from cli.lab_cli import main
from cli.store import JsonTaskStore


ROOT = Path(__file__).resolve().parents[1]


def _approve(store: JsonTaskStore, task_id: str) -> None:
    task = store.get(task_id)
    assert task is not None
    task.transition_to(TaskStatus.APPROVED, reviewer="teacher_1", reason="test approved local import continuation")
    store.save(task)


def test_local_core_agent_runs_stable_tools_and_stops_for_review(tmp_path):
    report_path = tmp_path / "agent-run.json"
    result = run_local_core_agent(
        input_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        output_path=str(report_path),
        grading_evidence_output=str(tmp_path / "grading-evidence.json"),
        store_path=tmp_path / "store.json",
        root=ROOT,
        trace_id="trace_local_core_agent_run",
    )

    assert result["mode"] == "LOCAL_CORE_AGENT_MVP"
    assert result["toolProfile"]["profile"] == "local-core-mvp"
    assert result["stopReason"]["code"] == "WAITING_REVIEW_REQUIRED"
    assert result["operatorSummary"]["phase"] == "HUMAN_REVIEW_REQUIRED"
    assert result["operatorSummary"]["actionRequired"] == "human_review"
    assert result["nextActions"][0]["id"] == "review_generated_artifacts"
    assert result["nextActions"][0]["autoApproveAllowed"] is False
    assert {task["status"] for task in result["tasks"].values()} == {"WAITING_REVIEW"}
    assert result["artifacts"]["gradingEvidencePath"] == str(tmp_path / "grading-evidence.json")
    assert result["safety"]["realAgentImport"] is False
    assert result["safety"]["autoApproveAllowed"] is False
    assert result["safety"]["autoPublishAllowed"] is False
    assert result["safety"]["contestantCodeExecuted"] is False
    assert {step["tool"] for step in result["steps"]} >= {
        "analyze_material",
        "generate_lab_from_source",
        "generate_exam_from_lab",
        "generate_ppt",
        "run_grading_evidence_auto",
        "get_review_detail",
    }
    assert all(step["label"] and step["purpose"] for step in result["steps"])
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted["runId"] == result["runId"]
    assert persisted["replay"]["recordPath"] == str(report_path)


def test_local_core_agent_replay_uses_run_record_inputs(tmp_path):
    source_record = tmp_path / "source-run.json"
    replay_record = tmp_path / "replay-run.json"
    store_path = tmp_path / "store.json"
    run_local_core_agent(
        input_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        output_path=str(source_record),
        grading_evidence_output=str(tmp_path / "source-evidence.json"),
        store_path=store_path,
        root=ROOT,
    )

    replay = replay_local_core_agent(
        record_path=str(source_record),
        output_path=str(replay_record),
        store_path=store_path,
        root=ROOT,
    )

    assert replay["replayedFrom"] == str(source_record)
    assert replay["runId"] != json.loads(source_record.read_text(encoding="utf-8"))["runId"]
    assert replay_record.is_file()
    assert replay["stopReason"]["code"] == "WAITING_REVIEW_REQUIRED"


def test_local_core_agent_executes_local_import_only_for_preapproved_tasks(tmp_path):
    store_path = tmp_path / "store.json"
    initial = run_local_core_agent(
        input_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        output_path=str(tmp_path / "initial.json"),
        grading_evidence_output=str(tmp_path / "initial-evidence.json"),
        store_path=store_path,
        root=ROOT,
    )
    store = JsonTaskStore(store_path)
    _approve(store, initial["tasks"]["lab"]["id"])
    _approve(store, initial["tasks"]["examGrading"]["id"])

    resumed = run_local_core_agent(
        input_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        output_path=str(tmp_path / "resumed.json"),
        grading_evidence_output=str(tmp_path / "resumed-evidence.json"),
        approved_lab_task_id=initial["tasks"]["lab"]["id"],
        approved_exam_task_id=initial["tasks"]["examGrading"]["id"],
        approved_grading_task_id=initial["tasks"]["examGrading"]["id"],
        store_path=store_path,
        root=ROOT,
    )

    assert resumed["stopReason"]["code"] == "LOCAL_CORE_MVP_STOP_LINE_REACHED"
    assert {item["kind"] for item in resumed["localImport"]} == {"lab", "exam", "grading"}
    assert all(item["agentEntityId"] for item in resumed["localImport"])
    assert all(item["dryRunRecordId"] for item in resumed["localImport"])
    assert "agent_internal_publish_request" not in {step["tool"] for step in resumed["steps"]}
    assert resumed["operatorSummary"]["phase"] == "LOCAL_IMPORT_COMPLETE"
    assert resumed["nextActions"] == [
        {
            "id": "review_local_dry_run",
            "kind": "HUMAN_REVIEW",
            "required": True,
            "message": "核对本地 import-preview、mock-import 和 import-dry-run DTO；不得发送真实平台请求。",
            "localImportKinds": ["lab", "exam", "grading"],
            "blockedActions": ["import-send", "import-status", "publish"],
        }
    ]


def test_local_core_agent_rejects_unapproved_import_task_with_operator_diagnostic(tmp_path):
    initial = run_local_core_agent(
        input_path=str(ROOT / "examples/input/demo-source.md"),
        reviewer="teacher_1",
        output_path=str(tmp_path / "initial.json"),
        grading_evidence_output=str(tmp_path / "initial-evidence.json"),
        store_path=tmp_path / "store.json",
        root=ROOT,
    )

    with pytest.raises(LocalCoreAgentError) as exc_info:
        run_local_core_agent(
            input_path=str(ROOT / "examples/input/demo-source.md"),
            reviewer="teacher_1",
            output_path=str(tmp_path / "unapproved-import.json"),
            approved_lab_task_id=initial["tasks"]["lab"]["id"],
            store_path=tmp_path / "store.json",
            root=ROOT,
        )

    assert exc_info.value.code == "AGENT_TASK_NOT_APPROVED"
    assert exc_info.value.diagnostic() == {
        "component": "LocalCoreAgentDiagnostic",
        "code": "AGENT_TASK_NOT_APPROVED",
        "stage": "validate_local_import",
        "tool": "get_review_detail",
        "operatorAction": "先由人工审核任务，确认状态为 APPROVED 后再传入该任务 ID。",
        "retryAllowed": True,
        "realPlatformActionRequired": False,
        "secretsRequired": False,
    }


@pytest.mark.parametrize(
    ("code", "expected_action"),
    [
        ("VALIDATION_ERROR", "修正输入路径、审核人、输出路径或提交目录后重新运行。"),
        ("AGENT_RUN_RECORD_INVALID", "选择由 agent local-core run 生成的完整 JSON run record 后重新 replay。"),
        ("MCP_TOOL_NOT_IN_PROFILE", "当前工具不属于 local-core-mvp；保持在本地停止线，不要改用真实平台工具。"),
        ("AGENT_RESPONSE_SHAPE_INVALID", "检查关联 DSL、评分 evidence 或本地导入产物是否存在且格式有效，然后重新运行。"),
    ],
)
def test_local_core_agent_common_diagnostics_are_operator_readable(code, expected_action):
    diagnostic = LocalCoreAgentError(code, "test").diagnostic()

    assert diagnostic["operatorAction"] == expected_action
    assert diagnostic["realPlatformActionRequired"] is False
    assert diagnostic["secretsRequired"] is False


def test_local_core_agent_rejects_missing_source_file(tmp_path):
    with pytest.raises(LocalCoreAgentError) as exc_info:
        run_local_core_agent(
            input_path=str(tmp_path / "missing.md"),
            reviewer="teacher_1",
            output_path=str(tmp_path / "run.json"),
            store_path=tmp_path / "store.json",
            root=ROOT,
        )

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.errors == [{"field": "input", "reason": "文件不存在"}]


def test_local_core_agent_cli_returns_unified_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "cli-store.json"))
    output = tmp_path / "cli-run.json"

    exit_code = main(
        [
            "agent",
            "local-core",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(output),
            "--grading-evidence-output",
            str(tmp_path / "cli-evidence.json"),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert set(payload) >= {"success", "code", "message", "data", "traceId"}
    assert payload["success"] is True
    assert payload["data"]["agentRun"]["stopReason"]["code"] == "WAITING_REVIEW_REQUIRED"
    assert output.is_file()


def test_local_core_agent_replay_cli_returns_json_diagnostic_for_invalid_record(tmp_path, capsys):
    invalid_record = tmp_path / "invalid-record.json"
    invalid_record.write_text('{"input": {"path": "only-path"}}', encoding="utf-8")

    exit_code = main(
        [
            "agent",
            "local-core",
            "replay",
            "--record",
            str(invalid_record),
            "--output",
            str(tmp_path / "replay.json"),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "AGENT_RUN_RECORD_INVALID"
    assert payload["agentDiagnostic"]["component"] == "LocalCoreAgentDiagnostic"
    assert payload["agentDiagnostic"]["operatorAction"] == "选择由 agent local-core run 生成的完整 JSON run record 后重新 replay。"
