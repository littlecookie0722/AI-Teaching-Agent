import json

from ai_workflows.exam_candidate_preview import ExamCandidatePreviewError
from cli.lab_cli import main


def run_cli(args, capsys):
    exit_code = main(args)
    payload = json.loads(capsys.readouterr().out)
    return exit_code, payload


def assert_json_envelope(payload):
    assert set(payload) >= {"success", "code", "message", "traceId"}
    assert payload["traceId"].startswith("trace_")
    if payload["success"]:
        assert "data" in payload
    else:
        assert "errors" in payload


def test_offline_demo_returns_review_gated_summary_and_candidate_preview(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    summary_path = tmp_path / "summary.json"
    workflow_path = tmp_path / "workflow.json"
    preview_path = tmp_path / "candidate-preview.json"

    exit_code, payload = run_cli(
        [
            "demo",
            "offline",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "offline-test",
            "--output",
            str(summary_path),
            "--workflow-output",
            str(workflow_path),
            "--candidate-preview-output",
            str(preview_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    data = payload["data"]
    summary = data["summary"]
    assert summary == json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["mode"] == "offline"
    assert {key for key in summary["generatedDsl"]} == {"lab", "exam", "grading", "ppt"}
    assert all(item["schemaValidated"] is True for item in summary["generatedDsl"].values())
    assert all(item["status"] == "WAITING_REVIEW" for item in summary["generatedDsl"].values())
    assert summary["reviewStatus"] == "WAITING_REVIEW"
    assert summary["reviewRequired"] is True
    assert summary["publishBlockedUntilApproved"] is True
    assert summary["candidatePreviewSafe"] is True
    assert summary["blockingIssueTotal"] == 0
    assert summary["safety"] == {
        "realLlmCalled": False,
        "secretsRead": False,
        "networkAccess": False,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
        "unknownShellExecuted": False,
        "realCloudResourceCreated": False,
        "realCloudResourceChanged": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "reviewBypassed": False,
    }
    assert workflow_path.exists()
    assert preview_path.exists()
    assert data["workflowReportPath"] == str(workflow_path)
    assert data["candidatePreviewPath"] == str(preview_path)
    assert set(data["taskIds"]) == {"LAB_GENERATION", "EXAM_GENERATION", "GRADING_GENERATION", "PPT_GENERATION"}

    preview = json.loads(preview_path.read_text(encoding="utf-8"))
    assert preview["answersRemoved"] is True
    assert preview["answerVisibleToCandidate"] is False
    assert preview["redaction"]["answerLeakDetected"] is False
    assert all("answer" not in question and "gradingRef" not in question for question in preview["questions"])


def test_offline_demo_missing_input_returns_json_without_outputs(tmp_path, capsys):
    summary_path = tmp_path / "summary.json"
    workflow_path = tmp_path / "workflow.json"
    preview_path = tmp_path / "candidate-preview.json"

    exit_code, payload = run_cli(
        [
            "demo",
            "offline",
            "--input",
            str(tmp_path / "missing.md"),
            "--output",
            str(summary_path),
            "--workflow-output",
            str(workflow_path),
            "--candidate-preview-output",
            str(preview_path),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"
    assert not summary_path.exists()
    assert not workflow_path.exists()
    assert not preview_path.exists()


def test_offline_demo_candidate_preview_schema_error_is_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    summary_path = tmp_path / "summary.json"
    workflow_path = tmp_path / "workflow.json"
    preview_path = tmp_path / "candidate-preview.json"

    def reject_preview(*args, **kwargs):
        raise ExamCandidatePreviewError(
            "SCHEMA_VALIDATION_ERROR",
            "Exam DSL Schema 校验失败",
            [{"field": "$.spec.questions", "reason": "invalid fixture"}],
        )

    monkeypatch.setattr("cli.lab_cli.build_exam_candidate_preview_from_file", reject_preview)
    exit_code, payload = run_cli(
        [
            "demo",
            "offline",
            "--output",
            str(summary_path),
            "--workflow-output",
            str(workflow_path),
            "--candidate-preview-output",
            str(preview_path),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "SCHEMA_VALIDATION_ERROR"
    assert payload["errors"] == [{"field": "$.spec.questions", "reason": "invalid fixture"}]
    assert workflow_path.exists()
    assert not summary_path.exists()
    assert not preview_path.exists()


def test_offline_demo_rejects_unsafe_candidate_preview_before_writing_it(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    summary_path = tmp_path / "summary.json"
    workflow_path = tmp_path / "workflow.json"
    preview_path = tmp_path / "candidate-preview.json"

    monkeypatch.setattr(
        "cli.lab_cli.build_exam_candidate_preview_from_file",
        lambda *args, **kwargs: {
            "answersRemoved": False,
            "answerVisibleToCandidate": True,
            "redaction": {"answerLeakDetected": True},
        },
    )
    exit_code, payload = run_cli(
        [
            "demo",
            "offline",
            "--output",
            str(summary_path),
            "--workflow-output",
            str(workflow_path),
            "--candidate-preview-output",
            str(preview_path),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "status"
    assert workflow_path.exists()
    assert not summary_path.exists()
    assert not preview_path.exists()
