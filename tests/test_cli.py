import json
import os
import subprocess
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

import cli.lab_cli as lab_cli
from cli.ai_task import create_waiting_review_task
from cli.artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from cli.lab_cli import main
from cli.store import JsonTaskStore
from providers import ProviderError
from tests.fakes_backend_mysql import FakeMySQLDatabase
from tests.fakes_backend_postgres import FakePostgreSQLDatabase
from tests.runtime_requirements import requires_presentations_runtime


SUPPORTED_GRADING_CHECK_TYPES = ["file_exists", "stdout_contains", "pytest", "notebook_cell", "json_field", "log_keyword"]


class RecordingPlatformImportHandler(BaseHTTPRequestHandler):
    requests = []
    quiet = True

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length)
        body = json.loads(raw.decode("utf-8"))
        self.__class__.requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "contentType": self.headers.get("Content-Type"),
                "body": body,
            }
        )
        response = {
            "draftImportId": "draft_import_test",
            "status": "PENDING_MANUAL_PLATFORM_REVIEW",
            "receivedEntityType": body.get("entityType"),
        }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        self.__class__.requests.append(
            {
                "method": "GET",
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "contentType": self.headers.get("Content-Type"),
            }
        )
        response = {
            "draftImportId": "draft_import_test",
            "status": "ACCEPTED_FOR_DRAFT",
            "message": "draft import accepted for manual publish review",
        }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        if self.quiet:
            return
        super().log_message(format, *args)


def start_recording_platform_server():
    RecordingPlatformImportHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), RecordingPlatformImportHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}"


class ConfigurablePlatformImportHandler(BaseHTTPRequestHandler):
    requests = []
    quiet = True

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length)
        body = json.loads(raw.decode("utf-8"))
        self.__class__.requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "contentType": self.headers.get("Content-Type"),
                "body": body,
            }
        )
        response = {"jobId": "job_import_test", "reviewState": "QUEUED"}
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        self.__class__.requests.append(
            {
                "method": "GET",
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "contentType": self.headers.get("Content-Type"),
            }
        )
        response = {"jobId": "job_import_test", "reviewState": "DONE"}
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        if self.quiet:
            return
        super().log_message(format, *args)


def start_configurable_platform_server():
    ConfigurablePlatformImportHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), ConfigurablePlatformImportHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}"


def stop_recording_platform_server(server, thread):
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


def run_cli(args, capsys):
    exit_code = main(args)
    output = capsys.readouterr().out
    payload = json.loads(output)
    return exit_code, payload


def assert_json_envelope(payload):
    assert set(payload) >= {"success", "code", "message", "traceId"}
    assert payload["traceId"].startswith("trace_")
    if payload["success"]:
        assert "data" in payload
    else:
        assert "errors" in payload


def fake_controlled_docker_run(args, **kwargs):
    if args[:2] == ["docker", "info"]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout='"29.5.3"', stderr="")
    if args[:3] == ["docker", "image", "inspect"]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="sha256:demo", stderr="")
    if "main.py" in args:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="accuracy=0.90\n", stderr="")
    if "pytest" in args:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1 passed\n", stderr="")
    raise AssertionError(f"unexpected command: {args}")


def write_mixed_submission(path: Path) -> Path:
    path.mkdir()
    (path / "result.csv").write_text("id,accuracy\n1,0.90\n", encoding="utf-8")
    (path / "metrics.json").write_text(json.dumps({"accuracy": 0.9}), encoding="utf-8")
    (path / "logs").mkdir()
    (path / "logs" / "train.log").write_text("training complete\n", encoding="utf-8")
    (path / "notebooks").mkdir()
    notebook = {
        "cells": [
            {"cell_type": "markdown", "source": ["intro"], "outputs": []},
            {"cell_type": "code", "source": ["x = 1"], "outputs": []},
            {"cell_type": "code", "source": ["y = 2"], "outputs": []},
            {"cell_type": "code", "source": ["print('accuracy')"], "outputs": [{"text": ["accuracy=0.90"]}]},
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (path / "notebooks" / "analysis.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
    return path


def create_mixed_evidence_merge_for_task(tmp_path, capsys, monkeypatch, task_id: str | None = None):
    readonly_submission = write_mixed_submission(tmp_path / f"mixed-submission-{task_id or 'standalone'}")
    readonly_report_path = tmp_path / f"mixed-readonly-report-{task_id or 'standalone'}.json"
    controlled_plan_path = tmp_path / f"mixed-controlled-plan-{task_id or 'standalone'}.json"
    controlled_source_path = tmp_path / f"mixed-controlled-source-{task_id or 'standalone'}.json"
    controlled_report_path = tmp_path / f"mixed-controlled-report-{task_id or 'standalone'}.json"
    merged_report_path = tmp_path / f"merged-evidence-report-{task_id or 'standalone'}.json"
    source_grading = json.loads(json.dumps(lab_cli.load_yaml(Path("templates/grading/examples/mixed-checks.yaml"))))
    pytest_check = next(check for check in source_grading["spec"]["checks"] if check["type"] == "pytest")
    pytest_check["path"] = "checks/check_main.py"
    pytest_plan = next(plan for plan in source_grading["spec"]["assessmentPlan"] if plan["type"] == "pytest")
    pytest_plan["inputSummary"] = "Plan pytest check at checks/check_main.py"
    controlled_source_path.write_text(json.dumps(source_grading), encoding="utf-8")

    run_cli(
        [
            "grade",
            "controlled-plan",
            "--grading",
            str(controlled_source_path),
            "--output",
            str(controlled_plan_path),
        ],
        capsys,
    )
    readonly_exit_code, readonly_payload = run_cli(
        [
            "grade",
            "sandbox-run",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(readonly_submission),
            "--output",
            str(readonly_report_path),
        ],
        capsys,
    )
    assert readonly_exit_code == 0
    assert_json_envelope(readonly_payload)

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)
    controlled_exit_code, controlled_payload = run_cli(
        [
            "grade",
            "sandbox-run",
            "--execution-mode",
            "controlled-command",
            "--grading",
            str(controlled_plan_path),
            "--submission",
            "examples/submissions/controlled-command-demo",
            "--image",
            "local-python:demo",
            "--output",
            str(controlled_report_path),
        ],
        capsys,
    )
    assert controlled_exit_code == 0
    assert_json_envelope(controlled_payload)

    merge_args = [
        "grade",
        "evidence-merge",
        "--report",
        str(readonly_report_path),
        "--report",
        str(controlled_report_path),
        "--output",
        str(merged_report_path),
    ]
    if task_id:
        merge_args.extend(["--task-id", task_id])
    merge_exit_code, merge_payload = run_cli(merge_args, capsys)
    assert merge_exit_code == 0
    assert_json_envelope(merge_payload)
    assert merge_payload["data"]["scorePreview"]["readyForDecisionNote"] is True
    return {
        "readonlyReportPath": readonly_report_path,
        "controlledPlanPath": controlled_plan_path,
        "controlledReportPath": controlled_report_path,
        "mergedReportPath": merged_report_path,
        "mergePayload": merge_payload,
    }


def create_approved_grading_task_with_decision_note(tmp_path, capsys, monkeypatch, *, reviewer: str = "teacher_1") -> str:
    store_path = tmp_path / "store.json"
    monkeypatch.setenv("LAB_CLI_STORE", str(store_path))
    grading_path = Path("templates/grading/examples/mixed-checks.yaml").resolve()
    store = JsonTaskStore(store_path)
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Agent CLI Grading closure",
        input_type="grading-dsl",
        input_ref=str(grading_path),
        final_result_path=str(grading_path),
        trace_id="trace_cli_agent_grading_closure_setup",
    )
    store.save(task)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.GRADING_DSL,
            path=str(grading_path),
            title="Mixed Checks Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id="trace_cli_agent_grading_closure_setup",
            task_id=task.id,
            source_ref=str(grading_path),
            metadata={"dslKind": "Grading", "reviewRequired": True},
        )
    )
    result = create_mixed_evidence_merge_for_task(tmp_path, capsys, monkeypatch, task_id=task.id)
    assert result["mergedReportPath"].exists()
    note_exit, note_payload = run_cli(
        [
            "review",
            "decision-note",
            "--task-id",
            task.id,
            "--reviewer",
            reviewer,
            "--decision",
            "approve-ready",
            "--output",
            str(tmp_path / "agent-cli-grading-decision-note.json"),
        ],
        capsys,
    )
    assert note_exit == 0
    assert note_payload["data"]["decisionNote"]["decision"] == "approve-ready"
    approve_exit, approve_payload = run_cli(
        ["review", "approve", "--task-id", task.id, "--reviewer", reviewer],
        capsys,
    )
    assert approve_exit == 0
    assert approve_payload["data"]["task"]["status"] == "APPROVED"
    return task.id


def test_grade_evidence_auto_runs_readonly_and_merges_report(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    submission = write_mixed_submission(tmp_path / "mixed-auto-submission")
    output = tmp_path / "evidence-auto.json"

    exit_code, payload = run_cli(
        [
            "grade",
            "evidence-auto",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(submission),
            "--output",
            str(output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    report = payload["data"]
    assert output.exists()
    assert report["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert report["sourceMode"] == "EVIDENCE_AUTO"
    assert report["summary"]["readonlyReportIncluded"] is True
    assert report["summary"]["controlledCommandRequested"] is False
    assert report["summary"]["controlledCommandIncluded"] is False
    assert report["summary"]["evidenceReadyTotal"] == 4
    assert report["summary"]["missingEvidenceTotal"] == 2
    assert report["summary"]["controlledCommandMissingTotal"] == 2
    assert report["summary"]["nextCoreActionId"] == "run_evidence_auto_with_controlled_command"
    assert report["summary"]["scorePreviewStatus"] == "PARTIAL_SCORE_PREVIEW_NEEDS_MORE_EVIDENCE"
    assert report["summary"]["scorePreviewEarnedScore"] == 50
    assert report["summary"]["scorePreviewTotalScore"] == 100
    assert report["summary"]["scorePreviewCoverageRatio"] == 0.5
    assert report["summary"]["gradingDslCoverageStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert report["summary"]["gradingDslEvidenceReadyTotal"] == 4
    assert report["summary"]["gradingDslMissingEvidenceTotal"] == 2
    assert report["scorePreview"]["component"] == "GradingEvidenceAutoScorePreview"
    assert report["scorePreview"]["earnedScore"] == 50
    assert report["scorePreview"]["coveredScore"] == 50
    assert report["scorePreview"]["missingScore"] == 50
    assert report["scorePreview"]["readyForDecisionNote"] is False
    assert set(report["scorePreview"]["missingCheckIds"]) == {"check_stdout_accuracy", "check_pytest"}
    assert report["executionMatrix"]["mode"] == "GRADING_EVIDENCE_AUTO_EXECUTION_MATRIX"
    assert report["executionMatrix"]["summary"]["checkTotal"] == 6
    assert report["executionMatrix"]["summary"]["readonlyStaticCoveredTotal"] == 4
    assert report["executionMatrix"]["summary"]["controlledCommandCoveredTotal"] == 0
    missing_stdout_item = next(
        item for item in report["executionMatrix"]["items"] if item["checkId"] == "check_stdout_accuracy"
    )
    assert missing_stdout_item["status"] == "MISSING"
    assert missing_stdout_item["passed"] is None
    assert missing_stdout_item["earnedScore"] == 0
    assert missing_stdout_item["selectedEvidenceMode"] == "MISSING"
    assert missing_stdout_item["evidenceSourceKind"] == "MISSING"
    assert missing_stdout_item["reason"] == "run_evidence_auto_with_controlled_command"
    dsl_coverage = report["gradingDslCoverageSummary"]
    assert dsl_coverage["component"] == "GradingDslCoverageSummary"
    assert dsl_coverage["status"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert dsl_coverage["dslCheckTotal"] == 6
    assert dsl_coverage["evidenceReadyTotal"] == 4
    assert dsl_coverage["missingEvidenceTotal"] == 2
    assert set(dsl_coverage["controlledCommandMissingCheckIds"]) == {"check_stdout_accuracy", "check_pytest"}
    assert dsl_coverage["decisionNoteRecommendation"] == "needs-evidence"
    assert dsl_coverage["nextCoreActionId"] == "run_evidence_auto_with_controlled_command"
    assert report["nextCoreAction"]["id"] == "run_evidence_auto_with_controlled_command"
    assert report["nextCoreAction"]["api"]["bodyPatch"]["includeControlledCommand"] is True
    checklist = report["manualReviewChecklist"]
    assert checklist["component"] == "GradingEvidenceAutoManualReviewChecklist"
    assert checklist["status"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert checklist["summary"]["itemTotal"] == 6
    assert checklist["summary"]["readyForDecisionTotal"] == 4
    assert checklist["summary"]["controlledCommandMissingTotal"] == 2
    assert checklist["decisionNoteRecommendation"]["decision"] == "needs-evidence"
    assert report["summary"]["manualReviewChecklistStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert report["summary"]["decisionNoteRecommendation"] == "needs-evidence"
    stdout_item = next(item for item in checklist["items"] if item["checkId"] == "check_stdout_accuracy")
    assert stdout_item["recommendedReviewAction"] == "collect_controlled_command_evidence_before_decision_note"
    assert stdout_item["recommendedDecision"] == "needs-evidence"
    assert checklist["safety"]["autoApproveAllowed"] is False
    assert checklist["safety"]["realPublishAllowed"] is False
    reviewer_safety = report["reviewerSafetySummary"]
    assert reviewer_safety["component"] == "GradingEvidenceAutoReviewerSafetySummary"
    assert reviewer_safety["status"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert reviewer_safety["readyForHumanReview"] is True
    assert reviewer_safety["readyForApproveReadyDecision"] is False
    assert reviewer_safety["evidence"]["controlledCommandRequested"] is False
    assert reviewer_safety["evidence"]["controlledCommandIncluded"] is False
    assert reviewer_safety["evidence"]["controlledCommandMissingTotal"] == 2
    assert {reason["id"] for reason in reviewer_safety["blockingReasons"]} >= {
        "controlled_command_evidence_missing",
        "score_preview_not_ready_for_approve_ready",
    }
    assert reviewer_safety["nextCoreAction"]["id"] == "run_evidence_auto_with_controlled_command"
    assert reviewer_safety["safety"]["contestantCodeExecutedInControlledSandbox"] is False
    assert reviewer_safety["safety"]["autoApproveAllowed"] is False
    assert report["summary"]["reviewerSafetySummaryStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert report["summary"]["reviewerSafetyReadyForApproveReadyDecision"] is False
    assert report["evidenceCoverage"]["readonlyStatic"]["checkTotal"] == 4
    assert report["evidenceCoverage"]["controlledDocker"]["checkTotal"] == 0
    assert report["safety"]["sandboxExecuted"] is True
    assert report["safety"]["contestantCodeExecuted"] is False
    assert report["safety"]["controlledCommandRequiresExplicitFlag"] is True
    assert report["safety"]["autoApproveAllowed"] is False
    assert report["safety"]["realPublishAllowed"] is False
    assert report["operationAuditEvent"]["action"] == "GRADING_EVIDENCE_MERGE"
    assert report["operationAuditEvent"]["detail"]["gradingDslCoverageSummary"] == dsl_coverage
    assert report["operationAuditEvent"]["detail"]["reviewerSafetySummary"] == reviewer_safety
    assert report["artifact"]["kind"] == "GRADING_REPORT"
    assert report["artifact"]["metadata"]["gradingDslCoverageSummary"] == dsl_coverage
    assert report["artifact"]["metadata"]["reviewerSafetySummary"] == reviewer_safety


def test_grade_evidence_auto_can_include_controlled_command_evidence(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    submission = write_mixed_submission(tmp_path / "mixed-auto-controlled-submission")
    (submission / "main.py").write_text("print('accuracy=0.90')\n", encoding="utf-8")
    (submission / "checks").mkdir()
    (submission / "checks" / "check_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    output = tmp_path / "evidence-auto-controlled.json"
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)

    exit_code, payload = run_cli(
        [
            "grade",
            "evidence-auto",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(submission),
            "--output",
            str(output),
            "--include-controlled-command",
            "--image",
            "local-python:demo",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    report = payload["data"]
    assert report["summary"]["controlledCommandRequested"] is True
    assert report["summary"]["controlledCommandIncluded"] is True
    assert report["summary"]["controlledCommandWarningTotal"] == 0
    assert report["controlledExecutionProfile"]["id"] == "local-python-pytest-controlled-v1"
    assert report["controlledExecutionDiagnostic"]["code"] == "OK"
    assert report["summary"]["evidenceReadyTotal"] == 6
    assert report["summary"]["missingEvidenceTotal"] == 0
    assert report["summary"]["scorePreviewStatus"] == "READY_FOR_HUMAN_SCORE_REVIEW"
    assert report["summary"]["scorePreviewEarnedScore"] == 75
    assert report["summary"]["scorePreviewTotalScore"] == 100
    assert report["summary"]["scorePreviewCoverageRatio"] == 1.0
    assert report["summary"]["gradingDslCoverageStatus"] == "FULLY_COVERED_READY_FOR_HUMAN_DECISION"
    assert report["summary"]["gradingDslEvidenceReadyTotal"] == 6
    assert report["summary"]["gradingDslMissingEvidenceTotal"] == 0
    assert report["scorePreview"]["earnedScore"] == 75
    assert report["scorePreview"]["coveredScore"] == 100
    assert report["scorePreview"]["missingScore"] == 0
    assert report["scorePreview"]["scoreRatio"] == 0.75
    assert report["scorePreview"]["passRate"] == 0.8333
    assert report["scorePreview"]["readyForDecisionNote"] is True
    assert report["executionMatrix"]["summary"]["controlledCommandCoveredTotal"] == 2
    assert report["executionMatrix"]["summary"]["readyForApprovalRecommendation"] is True
    controlled_matrix_item = next(
        item for item in report["executionMatrix"]["items"] if item["checkId"] == "check_stdout_accuracy"
    )
    assert controlled_matrix_item["status"] == "PASSED"
    assert controlled_matrix_item["passed"] is True
    assert controlled_matrix_item["earnedScore"] == 25
    assert controlled_matrix_item["selectedEvidenceMode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert controlled_matrix_item["evidenceSourceKind"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert controlled_matrix_item["reason"] == "selected_controlled_docker_evidence_passed"
    assert controlled_matrix_item["exitCode"] == 0
    assert "accuracy=0.90" in controlled_matrix_item["stdoutTail"]
    assert report["gradingDslCoverageSummary"]["status"] == "FULLY_COVERED_READY_FOR_HUMAN_DECISION"
    assert report["gradingDslCoverageSummary"]["missingCheckIds"] == []
    assert report["gradingDslCoverageSummary"]["decisionNoteRecommendation"] == "approve-ready"
    assert report["nextCoreAction"]["id"] == "review_score_and_record_decision_note"
    checklist = report["manualReviewChecklist"]
    assert checklist["status"] == "READY_FOR_DECISION_NOTE"
    assert checklist["summary"]["readyForDecisionTotal"] == 6
    assert checklist["decisionNoteRecommendation"]["decision"] == "approve-ready"
    controlled_item = next(item for item in checklist["items"] if item["checkId"] == "check_pytest")
    assert controlled_item["selectedEvidenceMode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert controlled_item["recommendedReviewAction"] == "verify_controlled_docker_output_and_score"
    assert controlled_item["recommendedDecision"] == "approve-ready"
    reviewer_safety = report["reviewerSafetySummary"]
    assert reviewer_safety["status"] == "READY_FOR_HUMAN_APPROVE_READY_DECISION"
    assert reviewer_safety["readyForHumanScoreReview"] is True
    assert reviewer_safety["readyForApproveReadyDecision"] is True
    assert reviewer_safety["blockingReasons"] == []
    assert reviewer_safety["score"]["earnedScore"] == 75
    assert reviewer_safety["score"]["totalScore"] == 100
    assert reviewer_safety["evidence"]["controlledCommandRequested"] is True
    assert reviewer_safety["evidence"]["controlledCommandIncluded"] is True
    assert reviewer_safety["evidence"]["controlledCommandMissingTotal"] == 0
    assert reviewer_safety["nextCoreAction"]["id"] == "review_score_and_record_decision_note"
    assert reviewer_safety["safety"]["contestantCodeExecutedInControlledSandbox"] is True
    assert reviewer_safety["safety"]["networkEnabled"] is False
    assert report["summary"]["reviewerSafetySummaryStatus"] == "READY_FOR_HUMAN_APPROVE_READY_DECISION"
    assert report["summary"]["reviewerSafetyReadyForApproveReadyDecision"] is True
    assert report["summary"]["manualReviewChecklistStatus"] == "READY_FOR_DECISION_NOTE"
    assert report["summary"]["decisionNoteRecommendation"] == "approve-ready"
    assert report["evidenceCoverage"]["controlledDocker"]["checkTotal"] == 2
    assert set(report["evidenceCoverage"]["controlledDocker"]["checkTypes"]) == {"pytest", "stdout_contains"}
    assert report["safety"]["contestantCodeExecuted"] is True
    assert report["safety"]["commandExecuted"] is True
    assert report["safety"]["networkEnabled"] is False
    assert report["safety"]["realPublishAllowed"] is False


def test_grade_stable_v1_creates_controlled_evidence_record_review_detail_and_report(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    submission = write_mixed_submission(tmp_path / "stable-v1-submission")
    (submission / "main.py").write_text("print('accuracy=0.90')\n", encoding="utf-8")
    (submission / "checks").mkdir()
    (submission / "checks" / "check_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    report_output = tmp_path / "stable-v1-evidence-auto.json"
    detail_output = tmp_path / "stable-v1-review-detail.json"
    preview_output = tmp_path / "stable-v1-result-preview.json"
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)

    exit_code, payload = run_cli(
        [
            "grade",
            "stable-v1",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(submission),
            "--output",
            str(report_output),
            "--submission-id",
            "submission_stable_v1_001",
            "--candidate-id",
            "candidate_stable_v1_001",
            "--reviewer",
            "teacher_1",
            "--image",
            "local-python:demo",
            "--review-detail-output",
            str(detail_output),
            "--result-preview-output",
            str(preview_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    data = payload["data"]
    readiness = data["gradingStableV1Readiness"]
    report = data["report"]
    record = data["gradingRecord"]
    detail = data["reviewDetail"]
    result_preview = data["gradingResultPreview"]

    assert data["mode"] == "GRADING_EXECUTION_STABLE_V1"
    assert data["taskCreated"] is True
    assert data["task"]["status"] == "WAITING_REVIEW"
    assert data["gradingDslArtifact"]["kind"] == "GRADING_DSL"
    assert report_output.exists()
    assert detail_output.exists()
    assert preview_output.exists()
    assert report["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert report["summary"]["controlledCommandRequested"] is True
    assert report["summary"]["controlledCommandIncluded"] is True
    assert report["summary"]["scorePreviewStatus"] == "READY_FOR_HUMAN_SCORE_REVIEW"
    assert report["reviewerSafetySummary"]["status"] == "READY_FOR_HUMAN_APPROVE_READY_DECISION"
    assert report["reviewerSafetySummary"]["readyForApproveReadyDecision"] is True
    stdout_matrix_item = next(
        item for item in report["executionMatrix"]["items"] if item["checkId"] == "check_stdout_accuracy"
    )
    assert stdout_matrix_item["status"] == "PASSED"
    assert stdout_matrix_item["passed"] is True
    assert stdout_matrix_item["earnedScore"] == 25
    assert stdout_matrix_item["evidenceSourceKind"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert stdout_matrix_item["exitCode"] == 0
    assert "accuracy=0.90" in stdout_matrix_item["stdoutTail"]
    assert report["reportDetail"]["source"] == "sandbox.grade_runner.build_grading_report_detail"
    assert record["status"] == "READY_FOR_HUMAN_REVIEW"
    assert record["decisionNoteRecommendation"] == "approve-ready"
    assert record["safety"]["recordCreatesNewExecution"] is False
    assert record["safety"]["contestantCodeExecutedByRecord"] is False
    assert detail["gradingRecords"]["total"] == 1
    assert detail["gradingRecords"]["latest"]["id"] == record["id"]
    assert detail["mergedGradingEvidence"]["visible"] is True
    assert detail["summary"]["gradingRecordLatestStatus"] == "READY_FOR_HUMAN_REVIEW"
    assert result_preview["mode"] == "READ_EXISTING_GRADING_REPORT_ONLY"
    assert result_preview["reportPath"] == str(report_output)
    assert result_preview["evidencePreview"]["totalVisible"] == 6
    stdout_preview_item = next(
        item for item in result_preview["evidencePreview"]["items"] if item["checkId"] == "check_stdout_accuracy"
    )
    assert stdout_preview_item["exitCode"] == 0
    assert "accuracy=0.90" in stdout_preview_item["stdoutTail"]
    assert stdout_preview_item["reason"] == "selected_controlled_docker_evidence_passed"
    assert result_preview["safety"]["sandboxExecutedByPreview"] is False
    assert readiness["completeForStableV1"] is True
    assert report["artifact"]["metadata"]["reviewerSafetySummary"]["readyForApproveReadyDecision"] is True
    assert readiness["requirements"]["gradingDslSchemaValidated"] is True
    assert readiness["requirements"]["controlledEvidenceIncluded"] is True
    assert readiness["requirements"]["gradingRecordCreated"] is True
    assert readiness["requirements"]["reviewDetailShowsGradingRecord"] is True
    assert readiness["requirements"]["gradingReportReadable"] is True
    assert readiness["requirements"]["autoApproveBlocked"] is True
    assert readiness["requirements"]["realPublishBlocked"] is True
    assert readiness["nextCoreAction"] == "record_human_grading_record_review"
    assert "grade record-review" in readiness["manualReviewNextCommand"]
    assert data["autoApproveAllowed"] is False
    assert data["realPublish"] is False


def test_grade_stable_v1_mixed_checks_pass_fixture_scores_full_marks(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_output = tmp_path / "stable-v1-full-pass-evidence-auto.json"
    detail_output = tmp_path / "stable-v1-full-pass-review-detail.json"
    preview_output = tmp_path / "stable-v1-full-pass-result-preview.json"
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)

    exit_code, payload = run_cli(
        [
            "grade",
            "stable-v1",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            "examples/submissions/mixed-checks-pass",
            "--output",
            str(report_output),
            "--submission-id",
            "submission_stable_v1_full_pass",
            "--candidate-id",
            "candidate_stable_v1_full_pass",
            "--reviewer",
            "teacher_1",
            "--image",
            "local-python:demo",
            "--review-detail-output",
            str(detail_output),
            "--result-preview-output",
            str(preview_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    data = payload["data"]
    report = data["report"]
    result_preview = data["gradingResultPreview"]

    assert report["summary"]["earnedScore"] == 100
    assert report["summary"]["totalScore"] == 100
    assert report["summary"]["passedCheckTotal"] == 6
    assert report["summary"]["failedCheckTotal"] == 0
    assert report["scorePreview"]["scoreRatio"] == 1.0
    assert report["scorePreview"]["passRate"] == 1.0
    assert report["evidenceCoverage"]["failedCheckIds"] == []
    assert data["gradingRecord"]["earnedScore"] == 100
    assert data["gradingRecord"]["evidenceSummary"]["passedTotal"] == 6
    assert data["gradingStableV1Readiness"]["completeForStableV1"] is True
    assert result_preview["score"]["earnedScore"] == 100
    assert result_preview["score"]["totalScore"] == 100
    assert result_preview["summary"]["passed"] == 6
    assert result_preview["summary"]["failed"] == 0
    assert result_preview["evidencePreview"]["totalVisible"] == 6
    assert all(item["status"] == "PASSED" for item in result_preview["evidencePreview"]["items"])
    pytest_item = next(item for item in result_preview["evidencePreview"]["items"] if item["checkId"] == "check_pytest")
    assert pytest_item["exitCode"] == 0
    assert "1 passed" in pytest_item["stdoutTail"]
    assert data["autoApproveAllowed"] is False
    assert data["realPublish"] is False


def test_grade_stable_v1_requires_submission_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_output = tmp_path / "stable-v1-missing-submission.json"

    exit_code, payload = run_cli(
        [
            "grade",
            "stable-v1",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(tmp_path / "missing-submission"),
            "--output",
            str(report_output),
            "--submission-id",
            "submission_missing_stable_v1",
            "--reviewer",
            "teacher_1",
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"] == [{"field": "submission", "reason": "目录不存在"}]
    assert not report_output.exists()


def test_grade_record_create_list_get_from_evidence_auto_report(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    submission = write_mixed_submission(tmp_path / "record-submission")
    (submission / "main.py").write_text("print('accuracy=0.90')\n", encoding="utf-8")
    (submission / "checks").mkdir()
    (submission / "checks" / "check_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    report_output = tmp_path / "record-evidence-auto.json"
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)
    run_cli(
        [
            "grade",
            "evidence-auto",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(submission),
            "--output",
            str(report_output),
            "--include-controlled-command",
            "--image",
            "local-python:demo",
        ],
        capsys,
    )

    create_exit, create_payload = run_cli(
        [
            "grade",
            "record-create",
            "--report",
            str(report_output),
            "--submission-id",
            "submission_001",
            "--candidate-id",
            "candidate_001",
            "--reviewer",
            "teacher_1",
        ],
        capsys,
    )
    record = create_payload["data"]["gradingRecord"]
    list_exit, list_payload = run_cli(["grade", "record-list", "--submission-id", "submission_001"], capsys)
    get_exit, get_payload = run_cli(["grade", "record-get", "--id", record["id"]], capsys)

    assert create_exit == 0
    assert_json_envelope(create_payload)
    assert record["status"] == "READY_FOR_HUMAN_REVIEW"
    assert record["earnedScore"] == 75
    assert record["totalScore"] == 100
    assert record["coveredScore"] == 100
    assert record["missingScore"] == 0
    assert record["coverageRatio"] == 1.0
    assert record["decisionNoteRecommendation"] == "approve-ready"
    assert record["manualReviewChecklistStatus"] == "READY_FOR_DECISION_NOTE"
    assert record["safety"]["derivedFromExistingReport"] is True
    assert record["safety"]["recordCreatesNewExecution"] is False
    assert record["safety"]["sandboxExecutedByRecord"] is False
    assert record["evidenceSummary"]["controlledExecutionProfile"]["id"] == "local-python-pytest-controlled-v1"
    assert record["evidenceSummary"]["controlledExecutionDiagnostic"]["code"] == "OK"
    assert create_payload["data"]["operationAuditEvent"]["action"] == "GRADING_RECORD_CREATE"
    assert create_payload["data"]["autoApproveAllowed"] is False

    assert list_exit == 0
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["id"] == record["id"]
    assert get_exit == 0
    assert get_payload["data"]["gradingRecord"]["id"] == record["id"]


def test_review_detail_includes_local_grading_record_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    store = JsonTaskStore(tmp_path / "store.json")
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Grading record review detail",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_cli_grading_record_detail",
    )
    store.save(task)
    submission = write_mixed_submission(tmp_path / "record-detail-submission")
    report_output = tmp_path / "record-detail-evidence-auto.json"
    run_cli(
        [
            "grade",
            "evidence-auto",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(submission),
            "--output",
            str(report_output),
            "--task-id",
            task.id,
        ],
        capsys,
    )
    create_exit, create_payload = run_cli(
        [
            "grade",
            "record-create",
            "--report",
            str(report_output),
            "--submission-id",
            "submission_detail_001",
            "--task-id",
            task.id,
            "--reviewer",
            "teacher_1",
        ],
        capsys,
    )
    detail_exit, detail_payload = run_cli(["review", "detail", "--task-id", task.id], capsys)

    assert create_exit == 0
    assert detail_exit == 0
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["gradingRecords"]["visible"] is True
    assert detail["gradingRecords"]["total"] == 1
    assert detail["gradingRecords"]["latest"]["id"] == create_payload["data"]["gradingRecord"]["id"]
    assert detail["gradingRecords"]["summary"]["latestStatus"] == "NEEDS_EVIDENCE"
    assert detail["reviewPage"]["gradingRecords"]["total"] == 1
    assert detail["summary"]["gradingRecordTotal"] == 1


def test_grade_record_review_updates_local_record_without_task_transition(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    store = JsonTaskStore(tmp_path / "store.json")
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Grading record human review",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_cli_grading_record_review",
    )
    store.save(task)
    submission = write_mixed_submission(tmp_path / "record-review-submission")
    (submission / "main.py").write_text("print('accuracy=0.90')\n", encoding="utf-8")
    (submission / "checks").mkdir()
    (submission / "checks" / "check_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    report_output = tmp_path / "record-review-evidence-auto.json"
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)
    run_cli(
        [
            "grade",
            "evidence-auto",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(submission),
            "--output",
            str(report_output),
            "--task-id",
            task.id,
            "--include-controlled-command",
            "--image",
            "local-python:demo",
        ],
        capsys,
    )
    run_cli(
        [
            "review",
            "decision-note",
            "--task-id",
            task.id,
            "--reviewer",
            "teacher_1",
            "--decision",
            "approve-ready",
            "--output",
            str(tmp_path / "record-review-decision-note.json"),
        ],
        capsys,
    )
    run_cli(["review", "approve", "--task-id", task.id, "--reviewer", "teacher_1"], capsys)
    _, create_payload = run_cli(
        [
            "grade",
            "record-create",
            "--report",
            str(report_output),
            "--submission-id",
            "submission_review_001",
            "--task-id",
            task.id,
        ],
        capsys,
    )
    record_id = create_payload["data"]["gradingRecord"]["id"]

    pre_core_exit, pre_core_payload = run_cli(["review", "core-readiness", "--task-id", task.id], capsys)
    review_exit, review_payload = run_cli(
        [
            "grade",
            "record-review",
            "--id",
            record_id,
            "--reviewer",
            "teacher_1",
            "--decision",
            "approve-ready",
        ],
        capsys,
    )
    detail_exit, detail_payload = run_cli(["review", "detail", "--task-id", task.id], capsys)

    assert review_exit == 0
    assert_json_envelope(review_payload)
    reviewed_record = review_payload["data"]["gradingRecord"]
    assert reviewed_record["status"] == "HUMAN_APPROVED"
    assert reviewed_record["reviewDecision"] == "approve-ready"
    assert reviewed_record["reviewedBy"] == "teacher_1"
    assert reviewed_record["safety"]["taskStatusChangedByRecordReview"] is False
    assert review_payload["data"]["operationAuditEvent"]["action"] == "GRADING_RECORD_REVIEW"
    assert review_payload["data"]["taskStatusChanged"] is False
    assert JsonTaskStore(tmp_path / "store.json").get(task.id).status.value == "APPROVED"

    assert pre_core_exit == 0
    pre_core = pre_core_payload["data"]["coreWorkflowReadinessReport"]
    assert pre_core["summary"]["gradingRecordReviewState"] == "WAITING_GRADING_RECORD_REVIEW"
    assert pre_core["summary"]["gradingRecordReadyForPlatformReview"] is False
    assert pre_core["recommendedNextAction"] == "review_latest_grading_record_for_platform_review"
    assert pre_core["nextToolRecommendation"]["reasonCode"] == "GRADING_RECORD_REVIEW_REQUIRED"
    assert pre_core["nextToolRecommendation"]["toolName"] is None
    assert pre_core["nextToolRecommendation"]["toolAvailable"] is False
    assert pre_core["nextToolRecommendation"]["actionType"] == "manual_grading_record_review"
    assert record_id in pre_core["nextToolRecommendation"]["cliCommand"]

    assert detail_exit == 0
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["gradingRecords"]["summary"]["humanApprovedTotal"] == 1
    assert detail["gradingRecords"]["summary"]["latestReviewDecision"] == "approve-ready"
    assert detail["gradingRecords"]["summary"]["readyForAgentReview"] is True
    assert detail["gradingRecords"]["summary"]["platformReviewState"] == "READY_FOR_PLATFORM_REVIEW"
    assert detail["gradingRecords"]["reviewIntegration"]["nextRequiredAction"] == (
        "continue_platform_review_after_grading_record_approved"
    )
    assert detail["summary"]["gradingRecordLatestStatus"] == "HUMAN_APPROVED"
    assert detail["summary"]["gradingRecordReadyForPlatformReview"] is True
    assert detail["summary"]["gradingRecordPlatformReviewState"] == "READY_FOR_PLATFORM_REVIEW"

    post_core_exit, post_core_payload = run_cli(["review", "core-readiness", "--task-id", task.id], capsys)
    assert post_core_exit == 0
    post_core = post_core_payload["data"]["coreWorkflowReadinessReport"]
    assert post_core["summary"]["gradingRecordReviewState"] == "READY_FOR_PLATFORM_REVIEW"
    assert post_core["summary"]["gradingRecordReadyForPlatformReview"] is True
    grading_steps = {step["id"]: step for step in post_core["steps"]}
    assert grading_steps["grading_record_human_review_approved"]["ready"] is True


def test_grade_record_review_requires_reason_for_needs_evidence(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    submission = write_mixed_submission(tmp_path / "record-review-invalid-submission")
    report_output = tmp_path / "record-review-invalid-evidence-auto.json"
    run_cli(
        [
            "grade",
            "evidence-auto",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(submission),
            "--output",
            str(report_output),
        ],
        capsys,
    )
    _, create_payload = run_cli(
        [
            "grade",
            "record-create",
            "--report",
            str(report_output),
            "--submission-id",
            "submission_review_invalid_001",
        ],
        capsys,
    )
    record_id = create_payload["data"]["gradingRecord"]["id"]

    review_exit, review_payload = run_cli(
        [
            "grade",
            "record-review",
            "--id",
            record_id,
            "--reviewer",
            "teacher_1",
            "--decision",
            "needs-evidence",
        ],
        capsys,
    )

    assert review_exit == 1
    assert_json_envelope(review_payload)
    assert review_payload["success"] is False
    assert review_payload["code"] == "VALIDATION_ERROR"
    assert review_payload["errors"] == [{"field": "reason", "reason": "该复核决策必须填写原因"}]


def test_grade_job_create_run_list_get_and_review_detail(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    store = JsonTaskStore(tmp_path / "store.json")
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Local grading job",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_cli_grading_job",
    )
    store.save(task)
    submission = write_mixed_submission(tmp_path / "job-submission")
    output = tmp_path / "job-evidence-auto.json"

    create_exit, create_payload = run_cli(
        [
            "grade",
            "job-create",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(submission),
            "--output",
            str(output),
            "--submission-id",
            "submission_job_001",
            "--task-id",
            task.id,
            "--candidate-id",
            "candidate_job_001",
            "--reviewer",
            "teacher_1",
        ],
        capsys,
    )
    job_id = create_payload["data"]["gradingJob"]["id"]
    run_exit, run_payload = run_cli(["grade", "job-run", "--id", job_id], capsys)
    list_exit, list_payload = run_cli(["grade", "job-list", "--task-id", task.id], capsys)
    get_exit, get_payload = run_cli(["grade", "job-get", "--id", job_id], capsys)
    detail_exit, detail_payload = run_cli(["review", "detail", "--task-id", task.id], capsys)

    assert create_exit == 0
    assert_json_envelope(create_payload)
    assert create_payload["data"]["gradingJob"]["status"] == "QUEUED"
    assert create_payload["data"]["queuePersistedToProduction"] is False
    assert run_exit == 0
    assert_json_envelope(run_payload)
    job = run_payload["data"]["gradingJob"]
    record = run_payload["data"]["gradingRecord"]
    assert job["status"] == "WAITING_REVIEW"
    assert job["gradingRecordId"] == record["id"]
    assert job["summary"]["earnedScore"] == 50
    assert job["summary"]["totalScore"] == 100
    assert record["submissionId"] == "submission_job_001"
    assert record["status"] == "NEEDS_EVIDENCE"
    assert run_payload["data"]["operationAuditEvent"]["action"] == "GRADING_JOB_RUN"
    assert run_payload["data"]["workerStarted"] is False
    assert output.exists()

    assert list_exit == 0
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["id"] == job_id
    assert get_exit == 0
    assert get_payload["data"]["gradingJob"]["id"] == job_id
    assert detail_exit == 0
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["gradingJobs"]["visible"] is True
    assert detail["gradingJobs"]["summary"]["waitingReviewTotal"] == 1
    assert detail["gradingJobs"]["summary"]["latestGradingRecordId"] == record["id"]
    assert detail["gradingRecords"]["total"] == 1
    assert detail["summary"]["gradingJobTotal"] == 1
    assert detail["summary"]["gradingJobLatestStatus"] == "WAITING_REVIEW"


def test_grade_db_init_sync_local_and_summary_from_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    store = JsonTaskStore(tmp_path / "store.json")
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Local grading db sync",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_cli_grading_db",
    )
    store.save(task)
    submission = write_mixed_submission(tmp_path / "db-sync-submission")
    output = tmp_path / "db-sync-evidence-auto.json"
    db_path = tmp_path / "grading.sqlite3"
    _, run_payload = run_cli(
        [
            "grade",
            "job-run",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(submission),
            "--output",
            str(output),
            "--submission-id",
            "submission_db_001",
            "--task-id",
            task.id,
        ],
        capsys,
    )

    init_exit, init_payload = run_cli(["grade", "db-init", "--db-path", str(db_path)], capsys)
    sync_exit, sync_payload = run_cli(["grade", "db-sync-local", "--db-path", str(db_path)], capsys)
    summary_exit, summary_payload = run_cli(["grade", "db-summary", "--db-path", str(db_path)], capsys)

    assert run_payload["success"] is True
    assert init_exit == 0
    assert_json_envelope(init_payload)
    assert init_payload["data"]["gradingRepository"]["safety"]["localSqliteOnly"] is True
    assert init_payload["data"]["productionDatabaseWritten"] is False
    assert init_payload["data"]["operationAuditEvent"]["action"] == "GRADING_REPOSITORY_INIT"
    assert db_path.exists()

    assert sync_exit == 0
    assert sync_payload["data"]["gradingRepositorySync"]["jobsSynced"] == 1
    assert sync_payload["data"]["gradingRepositorySync"]["recordsSynced"] == 1
    assert sync_payload["data"]["operationAuditEvent"]["action"] == "GRADING_REPOSITORY_SYNC_LOCAL"
    assert sync_payload["data"]["workerStarted"] is False

    assert summary_exit == 0
    summary = summary_payload["data"]["gradingRepository"]
    assert summary["jobTotal"] == 1
    assert summary["recordTotal"] == 1
    assert summary["jobsByStatus"] == {"WAITING_REVIEW": 1}
    assert summary["recordsByStatus"] == {"NEEDS_EVIDENCE": 1}
    assert summary["safety"]["productionDatabaseWritten"] is False


def test_backend_core_postgresql_plan_returns_redacted_json(monkeypatch, capsys):
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", "postgresql://user:secret@example.invalid/prod")

    exit_code, payload = run_cli(["backend-core", "postgresql", "plan"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    plan = payload["data"]["backendCorePostgresqlMigration"]
    assert plan["mode"] == "BACKEND_CORE_POSTGRESQL_MIGRATION_PLAN"
    assert plan["repositoryKind"] == "postgresql"
    assert plan["databaseUrlSummary"]["valueReturned"] is False
    assert plan["adapter"]["registeredByDefaultInHttpMock"] is False
    assert plan["requiresTestDatabase"] is True
    assert plan["networkAccess"] is False
    assert plan["schemaWritePlanned"] is False
    assert "user:secret" not in json.dumps(payload, ensure_ascii=False)


def test_backend_core_postgresql_init_requires_test_database_confirmation(monkeypatch, capsys):
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", "postgresql://user:secret@example.invalid/prod")

    exit_code, payload = run_cli(["backend-core", "postgresql", "init"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"] == [
        {"field": "confirmTestDatabase", "reason": "必须确认目标是测试或 staging 数据库"}
    ]
    assert "user:secret" not in json.dumps(payload, ensure_ascii=False)


def test_backend_core_postgresql_init_and_summary_with_fake_connector(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", "postgresql://user:secret@example.invalid/prod")
    database = FakePostgreSQLDatabase()
    monkeypatch.setattr(
        "cli.lab_cli.initialize_postgresql_backend_core_repository",
        lambda root, *, database_url_env: __import__(
            "backend.core_postgres_migration",
            fromlist=["initialize_postgresql_backend_core_repository"],
        ).initialize_postgresql_backend_core_repository(
            root,
            database_url_env=database_url_env,
            connector=database.connect,
        ),
    )
    monkeypatch.setattr(
        "cli.lab_cli.summarize_postgresql_backend_core_repository",
        lambda root, *, database_url_env: __import__(
            "backend.core_postgres_migration",
            fromlist=["summarize_postgresql_backend_core_repository"],
        ).summarize_postgresql_backend_core_repository(
            root,
            database_url_env=database_url_env,
            connector=database.connect,
        ),
    )

    init_exit, init_payload = run_cli(
        ["backend-core", "postgresql", "init", "--confirm-test-database"],
        capsys,
    )
    summary_exit, summary_payload = run_cli(["backend-core", "postgresql", "summary"], capsys)

    assert init_exit == 0
    assert_json_envelope(init_payload)
    init_data = init_payload["data"]
    assert init_data["mode"] == "BACKEND_CORE_POSTGRESQL_SCHEMA_INIT"
    assert init_data["schemaInitialized"] is True
    assert init_data["externalDatabaseWritten"] is True
    assert init_data["productionDatabaseWritten"] is False
    assert init_data["operationAuditEvent"]["action"] == "BACKEND_CORE_REPOSITORY_INIT"
    assert "ai_tasks" in database.tables

    assert summary_exit == 0
    assert_json_envelope(summary_payload)
    summary = summary_payload["data"]["backendCoreRepository"]
    assert summary["mode"] == "POSTGRESQL_BACKEND_CORE_REPOSITORY"
    assert summary["schemaVersion"] == "1"
    assert summary["taskTotal"] == 0
    assert summary["safety"]["externalDatabase"] is True
    assert "user:secret" not in json.dumps(init_payload, ensure_ascii=False)
    assert "user:secret" not in json.dumps(summary_payload, ensure_ascii=False)


def test_backend_core_postgresql_smoke_requires_test_database_confirmation(monkeypatch, capsys):
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", "postgresql://user:secret@example.invalid/prod")

    exit_code, payload = run_cli(["backend-core", "postgresql", "smoke"], capsys)

    assert exit_code == 1
    assert payload["success"] is False
    assert "traceId" in payload
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"] == [
        {"field": "confirmTestDatabase", "reason": "必须确认目标是测试或 staging 数据库"}
    ]
    assert "user:secret" not in json.dumps(payload, ensure_ascii=False)


def test_backend_core_postgresql_smoke_with_fake_connector(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", "postgresql://user:secret@example.invalid/prod")
    database = FakePostgreSQLDatabase()
    monkeypatch.setattr(
        "cli.lab_cli.run_postgresql_backend_core_smoke",
        lambda root, *, database_url_env, reviewer: __import__(
            "backend.core_postgres_migration",
            fromlist=["run_postgresql_backend_core_smoke"],
        ).run_postgresql_backend_core_smoke(
            root,
            database_url_env=database_url_env,
            reviewer=reviewer,
            connector=database.connect,
        ),
    )

    exit_code, payload = run_cli(
        [
            "backend-core",
            "postgresql",
            "smoke",
            "--reviewer",
            "teacher_smoke",
            "--confirm-test-database",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    smoke = payload["data"]
    assert smoke["mode"] == "BACKEND_CORE_POSTGRESQL_SMOKE"
    assert smoke["createdTask"]["status"] == "WAITING_REVIEW"
    assert smoke["reviewedTask"]["status"] == "APPROVED"
    assert smoke["roundTrip"]["taskLoaded"] is True
    assert smoke["roundTrip"]["operationAuditListed"] is True
    assert smoke["backendCoreRepository"]["taskTotal"] == 1
    assert smoke["productionDatabaseWritten"] is False
    assert smoke["autoApproveAllowed"] is False
    assert "user:secret" not in json.dumps(payload, ensure_ascii=False)


def test_backend_core_mysql_plan_returns_redacted_json(monkeypatch, capsys):
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", "mysql://user:secret@example.invalid/prod")

    exit_code, payload = run_cli(["backend-core", "mysql", "plan"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    plan = payload["data"]["backendCoreMysqlMigration"]
    assert plan["mode"] == "BACKEND_CORE_MYSQL_MIGRATION_PLAN"
    assert plan["repositoryKind"] == "mysql"
    assert plan["databaseUrlSummary"]["valueReturned"] is False
    assert plan["adapter"]["registeredByDefaultInHttpMock"] is False
    assert plan["requiresTestDatabase"] is True
    assert plan["networkAccess"] is False
    assert plan["schemaWritePlanned"] is False
    assert "user:secret" not in json.dumps(payload, ensure_ascii=False)


def test_backend_core_mysql_init_requires_test_database_confirmation(monkeypatch, capsys):
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", "mysql://user:secret@example.invalid/prod")

    exit_code, payload = run_cli(["backend-core", "mysql", "init"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"] == [
        {"field": "confirmTestDatabase", "reason": "必须确认目标是测试或 staging 数据库"}
    ]
    assert "user:secret" not in json.dumps(payload, ensure_ascii=False)


def test_backend_core_mysql_init_and_summary_with_fake_connector(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", "mysql://user:secret@example.invalid/prod")
    database = FakeMySQLDatabase()
    monkeypatch.setattr(
        "cli.lab_cli.initialize_mysql_backend_core_repository",
        lambda root, *, database_url_env: __import__(
            "backend.core_mysql_migration",
            fromlist=["initialize_mysql_backend_core_repository"],
        ).initialize_mysql_backend_core_repository(
            root,
            database_url_env=database_url_env,
            connector=database.connect,
        ),
    )
    monkeypatch.setattr(
        "cli.lab_cli.summarize_mysql_backend_core_repository",
        lambda root, *, database_url_env: __import__(
            "backend.core_mysql_migration",
            fromlist=["summarize_mysql_backend_core_repository"],
        ).summarize_mysql_backend_core_repository(
            root,
            database_url_env=database_url_env,
            connector=database.connect,
        ),
    )

    init_exit, init_payload = run_cli(
        ["backend-core", "mysql", "init", "--confirm-test-database"],
        capsys,
    )
    summary_exit, summary_payload = run_cli(["backend-core", "mysql", "summary"], capsys)

    assert init_exit == 0
    assert_json_envelope(init_payload)
    init_data = init_payload["data"]
    assert init_data["mode"] == "BACKEND_CORE_MYSQL_SCHEMA_INIT"
    assert init_data["schemaInitialized"] is True
    assert init_data["externalDatabaseWritten"] is True
    assert init_data["productionDatabaseWritten"] is False
    assert init_data["operationAuditEvent"]["action"] == "BACKEND_CORE_REPOSITORY_INIT"
    assert "ai_tasks" in database.tables

    assert summary_exit == 0
    assert_json_envelope(summary_payload)
    summary = summary_payload["data"]["backendCoreRepository"]
    assert summary["mode"] == "MYSQL_BACKEND_CORE_REPOSITORY"
    assert summary["schemaVersion"] == "1"
    assert summary["taskTotal"] == 0
    assert summary["safety"]["externalDatabase"] is True
    assert "user:secret" not in json.dumps(init_payload, ensure_ascii=False)
    assert "user:secret" not in json.dumps(summary_payload, ensure_ascii=False)


def test_backend_core_mysql_smoke_requires_test_database_confirmation(monkeypatch, capsys):
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", "mysql://user:secret@example.invalid/prod")

    exit_code, payload = run_cli(["backend-core", "mysql", "smoke"], capsys)

    assert exit_code == 1
    assert payload["success"] is False
    assert "traceId" in payload
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"] == [
        {"field": "confirmTestDatabase", "reason": "必须确认目标是测试或 staging 数据库"}
    ]
    assert "user:secret" not in json.dumps(payload, ensure_ascii=False)


def test_backend_core_mysql_smoke_with_fake_connector(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", "mysql://user:secret@example.invalid/prod")
    database = FakeMySQLDatabase()
    monkeypatch.setattr(
        "cli.lab_cli.run_mysql_backend_core_smoke",
        lambda root, *, database_url_env, reviewer: __import__(
            "backend.core_mysql_migration",
            fromlist=["run_mysql_backend_core_smoke"],
        ).run_mysql_backend_core_smoke(
            root,
            database_url_env=database_url_env,
            reviewer=reviewer,
            connector=database.connect,
        ),
    )

    exit_code, payload = run_cli(
        [
            "backend-core",
            "mysql",
            "smoke",
            "--reviewer",
            "teacher_smoke",
            "--confirm-test-database",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    smoke = payload["data"]
    assert smoke["mode"] == "BACKEND_CORE_MYSQL_SMOKE"
    assert smoke["createdTask"]["status"] == "WAITING_REVIEW"
    assert smoke["reviewedTask"]["status"] == "APPROVED"
    assert smoke["roundTrip"]["taskLoaded"] is True
    assert smoke["roundTrip"]["operationAuditListed"] is True
    assert smoke["backendCoreRepository"]["taskTotal"] == 1
    assert smoke["productionDatabaseWritten"] is False
    assert smoke["autoApproveAllowed"] is False
    assert "user:secret" not in json.dumps(payload, ensure_ascii=False)


def test_backend_core_asgi_smoke_cli_writes_json_report(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    monkeypatch.setenv("LAB_BACKEND_API_TOKEN", "outer-token-should-be-restored")
    output_path = tmp_path / "backend-asgi-smoke-report.json"
    work_dir = tmp_path / "backend-asgi-smoke"

    exit_code, payload = run_cli(
        [
            "backend-core",
            "asgi-smoke",
            "--work-dir",
            str(work_dir),
            "--output",
            str(output_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    smoke = payload["data"]
    assert smoke["mode"] == "BACKEND_ASGI_MOUNT_SMOKE"
    assert smoke["passed"] is True
    assert smoke["summary"]["failedStepTotal"] == 0
    assert smoke["safety"]["networkListenerStarted"] is False
    assert smoke["safety"]["externalDatabaseConnected"] is False
    assert smoke["safety"]["productionDatabaseWritten"] is False
    assert smoke["safety"]["realLlmCalled"] is False
    assert smoke["authBoundary"]["missingTokenRejected"] is True
    assert smoke["authBoundary"]["existingSecretEnvTemporarilyMasked"] is True
    assert smoke["authBoundary"]["secretValueReturned"] is False
    assert smoke["safety"]["userSecretEnvTemporarilyMasked"] is True
    assert smoke["reportPath"] == str(output_path)
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is True
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "local-asgi-smoke-token" not in serialized
    assert "outer-token-should-be-restored" not in serialized
    assert os.environ["LAB_BACKEND_API_TOKEN"] == "outer-token-should-be-restored"


def test_grade_worker_run_once_executes_sqlite_job_and_mirrors_to_store(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    store = JsonTaskStore(tmp_path / "store.json")
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Local grading worker",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_cli_grading_worker",
    )
    store.save(task)
    output = tmp_path / "worker-evidence-auto.json"
    db_path = tmp_path / "grading.sqlite3"
    _, create_payload = run_cli(
        [
            "grade",
            "job-create",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            "examples/submissions/readonly-demo",
            "--output",
            str(output),
            "--submission-id",
            "submission_worker_cli_001",
            "--task-id",
            task.id,
        ],
        capsys,
    )
    job_id = create_payload["data"]["gradingJob"]["id"]
    run_cli(["grade", "db-sync-local", "--db-path", str(db_path)], capsys)

    worker_exit, worker_payload = run_cli(
        [
            "grade",
            "worker-run-once",
            "--db-path",
            str(db_path),
            "--job-id",
            job_id,
            "--lease-seconds",
            "120",
            "--max-attempts",
            "4",
        ],
        capsys,
    )
    list_exit, list_payload = run_cli(["grade", "record-list", "--task-id", task.id], capsys)

    assert worker_exit == 0
    assert_json_envelope(worker_payload)
    result = worker_payload["data"]
    assert result["workerRun"]["status"] == "COMPLETED"
    assert result["workerRun"]["claimOwner"] == "local-grading-worker"
    assert result["workerRun"]["attemptCount"] == 1
    assert result["workerRun"]["leaseSeconds"] == 120
    assert result["workerRun"]["maxAttempts"] == 4
    assert result["claimRecovery"]["expiredClaimTotal"] == 0
    assert result["gradingJob"]["status"] == "WAITING_REVIEW"
    assert result["gradingJob"]["claimOwner"] == "local-grading-worker"
    assert result["gradingJob"]["attemptCount"] == 1
    assert result["gradingRecord"]["submissionId"] == "submission_worker_cli_001"
    assert result["safety"]["workerStarted"] is True
    assert result["safety"]["claimLeaseUsed"] is True
    assert result["safety"]["productionQueueUsed"] is False
    assert result["safety"]["productionDatabaseWritten"] is False
    assert output.exists()

    assert list_exit == 0
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["id"] == result["gradingRecord"]["id"]


def test_grade_worker_drain_once_executes_limited_sqlite_jobs(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    store = JsonTaskStore(tmp_path / "store.json")
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Local grading worker drain",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_cli_grading_worker_drain",
    )
    store.save(task)
    db_path = tmp_path / "grading.sqlite3"
    for index in range(3):
        run_cli(
            [
                "grade",
                "job-create",
                "--grading",
                "templates/grading/examples/mixed-checks.yaml",
                "--submission",
                "examples/submissions/readonly-demo",
                "--output",
                str(tmp_path / f"worker-drain-cli-{index}.json"),
                "--submission-id",
                f"submission_worker_drain_cli_{index}",
                "--task-id",
                task.id,
            ],
            capsys,
        )
    run_cli(["grade", "db-sync-local", "--db-path", str(db_path)], capsys)

    worker_exit, worker_payload = run_cli(
        [
            "grade",
            "worker-drain-once",
            "--db-path",
            str(db_path),
            "--limit",
            "2",
            "--lease-seconds",
            "120",
            "--max-attempts",
            "4",
        ],
        capsys,
    )
    list_exit, list_payload = run_cli(["grade", "job-list", "--task-id", task.id, "--db-path", str(db_path)], capsys)

    assert worker_exit == 0
    assert_json_envelope(worker_payload)
    result = worker_payload["data"]
    assert result["workerDrain"]["status"] == "COMPLETED"
    assert result["workerDrain"]["executedTotal"] == 2
    assert result["workerDrain"]["noopReached"] is False
    assert result["workerDrain"]["limit"] == 2
    assert result["workerDrain"]["leaseSeconds"] == 120
    assert result["workerDrain"]["maxAttempts"] == 4
    assert result["workerDrain"]["quota"]["limitReached"] is True
    assert result["workerDrain"]["quota"]["queueMayStillHaveRunnableJobs"] is True
    assert result["workerDrain"]["resourceCleanup"]["retainedReportTotal"] == 2
    assert result["workerDrain"]["resourceCleanup"]["cleanupExecuted"] is False
    assert len(result["workerRuns"]) == 2
    assert result["operationAuditEvent"]["action"] == "GRADING_WORKER_DRAIN"
    assert result["operationAuditEvent"]["detail"]["quota"]["effectiveLimit"] == 2
    assert result["safety"]["singleProcessSequentialDrain"] is True
    assert result["safety"]["quotaEnforced"] is True
    assert result["safety"]["resourceCleanupPlanned"] is True
    assert result["safety"]["persistentBackgroundWorker"] is False
    assert result["safety"]["productionQueueUsed"] is False

    assert list_exit == 0
    statuses = sorted(item["status"] for item in list_payload["data"]["items"])
    assert statuses == ["QUEUED", "WAITING_REVIEW", "WAITING_REVIEW"]


def test_grade_worker_drain_once_rejects_invalid_limit(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    exit_code, payload = run_cli(["grade", "worker-drain-once", "--limit", "0"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "limit"


def test_grade_job_sqlite_mode_create_run_list_get_and_review_detail(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    store = JsonTaskStore(tmp_path / "store.json")
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Local grading job sqlite mode",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_cli_grading_job_sqlite",
    )
    store.save(task)
    db_path = tmp_path / "grading.sqlite3"
    output = tmp_path / "sqlite-job-evidence-auto.json"

    create_exit, create_payload = run_cli(
        [
            "grade",
            "job-create",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            "examples/submissions/readonly-demo",
            "--output",
            str(output),
            "--submission-id",
            "submission_sqlite_cli_001",
            "--task-id",
            task.id,
            "--candidate-id",
            "candidate_sqlite_cli_001",
            "--reviewer",
            "teacher_1",
            "--db-path",
            str(db_path),
        ],
        capsys,
    )
    job_id = create_payload["data"]["gradingJob"]["id"]
    list_exit, list_payload = run_cli(["grade", "job-list", "--task-id", task.id, "--db-path", str(db_path)], capsys)
    get_exit, get_payload = run_cli(["grade", "job-get", "--id", job_id, "--db-path", str(db_path)], capsys)
    run_exit, run_payload = run_cli(["grade", "job-run", "--id", job_id, "--db-path", str(db_path)], capsys)
    detail_exit, detail_payload = run_cli(["review", "detail", "--task-id", task.id], capsys)

    assert create_exit == 0
    assert_json_envelope(create_payload)
    assert create_payload["data"]["mode"] == "LOCAL_SQLITE_GRADING_JOB"
    assert create_payload["data"]["localSqliteWritten"] is True
    assert create_payload["data"]["databaseWritten"] is False
    assert create_payload["data"]["productionDatabaseWritten"] is False
    assert create_payload["data"]["gradingJob"]["safety"]["localSqliteWritten"] is True
    assert db_path.exists()

    assert list_exit == 0
    assert list_payload["data"]["mode"] == "LOCAL_SQLITE_GRADING_JOB"
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["id"] == job_id
    assert list_payload["data"]["localSqliteRead"] is True
    assert get_exit == 0
    assert get_payload["data"]["gradingJob"]["id"] == job_id
    assert get_payload["data"]["localSqliteRead"] is True

    assert run_exit == 0
    assert_json_envelope(run_payload)
    result = run_payload["data"]
    assert result["mode"] == "LOCAL_SQLITE_GRADING_WORKER_ONCE"
    assert result["workerRun"]["status"] == "COMPLETED"
    assert result["workerRun"]["claimOwner"] == "lab-cli"
    assert result["workerRun"]["attemptCount"] == 1
    assert result["gradingJob"]["status"] == "WAITING_REVIEW"
    assert result["gradingJob"]["claimOwner"] == "lab-cli"
    assert result["gradingJob"]["attemptCount"] == 1
    assert result["gradingRecord"]["submissionId"] == "submission_sqlite_cli_001"
    assert result["safety"]["workerStarted"] is True
    assert result["safety"]["claimLeaseUsed"] is True
    assert result["productionDatabaseWritten"] is False
    assert output.exists()

    assert detail_exit == 0
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["gradingJobs"]["summary"]["latestGradingRecordId"] == result["gradingRecord"]["id"]
    assert detail["gradingRecords"]["total"] == 1


def test_grading_import_signoff_shows_evidence_auto_report_summary(tmp_path, monkeypatch, capsys):
    store_path = tmp_path / "store.json"
    monkeypatch.setenv("LAB_CLI_STORE", str(store_path))
    grading_path = Path("templates/grading/examples/mixed-checks.yaml").resolve()
    store = JsonTaskStore(store_path)
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Grading import signoff evidence auto",
        input_type="grading-dsl",
        input_ref=str(grading_path),
        final_result_path=str(grading_path),
        trace_id="trace_cli_import_signoff_auto_evidence",
    )
    store.save(task)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.GRADING_DSL,
            path=str(grading_path),
            title="Mixed Checks Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id="trace_cli_import_signoff_auto_evidence",
            task_id=task.id,
            source_ref=str(grading_path),
            metadata={"dslKind": "Grading", "reviewRequired": True},
        )
    )
    run_cli(["review", "approve", "--task-id", task.id, "--reviewer", "teacher_1"], capsys)
    run_cli(
        [
            "grade",
            "import-preview",
            "--task-id",
            task.id,
            "--reviewer",
            "teacher_1",
            "--output",
            str(tmp_path / "grading-rule-import-preview.json"),
        ],
        capsys,
    )
    submission = write_mixed_submission(tmp_path / "mixed-auto-import-signoff-submission")
    evidence_output = tmp_path / "grading-evidence-auto.json"

    evidence_exit_code, evidence_payload = run_cli(
        [
            "grade",
            "evidence-auto",
            "--task-id",
            task.id,
            "--grading",
            str(grading_path),
            "--submission",
            str(submission),
            "--output",
            str(evidence_output),
        ],
        capsys,
    )
    detail_exit_code, detail_payload = run_cli(["review", "detail", "--task-id", task.id], capsys)

    assert evidence_exit_code == 0
    assert_json_envelope(evidence_payload)
    assert detail_exit_code == 0
    detail = detail_payload["data"]["reviewDetail"]
    signoff = detail["platformImportPreviewSignoff"]
    report_summary = signoff["gradingEvidenceReportSummary"]
    assert report_summary["available"] is True
    assert report_summary["latestReportType"] == "GRADING_EVIDENCE_AUTO"
    assert report_summary["latestReportPath"] == str(evidence_output)
    assert report_summary["checkEvidenceReviewItemTotal"] == 6
    assert report_summary["readyForDecisionNote"] is False
    assert report_summary["manualReviewChecklistStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert report_summary["decisionNoteRecommendation"] == "needs-evidence"
    assert report_summary["nextRequiredAction"] == "record_needs_evidence_decision_note_or_collect_more_evidence"
    assert signoff["summary"]["gradingEvidenceReportAvailable"] is True
    grading_signoff = next(item for item in signoff["items"] if item["agentEntity"] == "grading_rule")
    assert grading_signoff["gradingEvidenceReportSummary"] == report_summary
    check_ids = {check["id"] for check in grading_signoff["checks"]}
    assert "confirm_grading_evidence_report_before_grading_rule_import" in check_ids
    precheck = detail["preApproveReviewCheck"]
    assert precheck["summary"]["scorePreviewAvailable"] is True
    assert precheck["summary"]["scorePreviewStatus"] == "PARTIAL_SCORE_PREVIEW_NEEDS_MORE_EVIDENCE"
    assert precheck["summary"]["scorePreviewEarnedScore"] == 50
    assert precheck["summary"]["scorePreviewTotalScore"] == 100
    assert precheck["summary"]["scorePreviewCoveredScore"] == 50
    assert precheck["summary"]["scorePreviewMissingScore"] == 50
    assert precheck["summary"]["scorePreviewCoverageRatio"] == 0.5
    assert precheck["summary"]["scorePreviewReadyForDecisionNote"] is False
    assert precheck["summary"]["scorePreviewMissingEvidenceTotal"] == 2
    assert set(precheck["summary"]["scorePreviewMissingCheckIds"]) == {"check_stdout_accuracy", "check_pytest"}
    assert precheck["summary"]["manualReviewChecklistStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert precheck["summary"]["decisionNoteRecommendation"] == "needs-evidence"
    assert precheck["summary"]["nextDecisionNoteAction"] == "collect_or_review_grading_evidence_before_decision_note"
    assert detail["reviewPage"]["platformImportPreviewSignoff"] == signoff


def test_grade_evidence_auto_degrades_when_controlled_runtime_unavailable(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    submission = write_mixed_submission(tmp_path / "mixed-auto-degraded-submission")
    output = tmp_path / "evidence-auto-degraded.json"

    def fake_missing_docker(args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=args)

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_missing_docker)

    exit_code, payload = run_cli(
        [
            "grade",
            "evidence-auto",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--submission",
            str(submission),
            "--output",
            str(output),
            "--include-controlled-command",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    report = payload["data"]
    assert report["summary"]["controlledCommandRequested"] is True
    assert report["summary"]["controlledCommandIncluded"] is False
    assert report["summary"]["controlledCommandWarningTotal"] == 1
    assert report["summary"]["nextCoreActionId"] == "prepare_controlled_docker_runtime_or_manual_review"
    assert report["executionMatrix"]["summary"]["controlledCommandRuntimeWarning"] is True
    assert report["executionMatrix"]["summary"]["controlledCommandMissingTotal"] == 2
    assert report["nextCoreAction"]["id"] == "prepare_controlled_docker_runtime_or_manual_review"
    checklist = report["manualReviewChecklist"]
    assert checklist["status"] == "CONTROLLED_RUNTIME_UNAVAILABLE"
    assert checklist["summary"]["readyForDecisionTotal"] == 4
    assert checklist["decisionNoteRecommendation"]["decision"] == "needs-evidence"
    assert report["summary"]["manualReviewChecklistStatus"] == "CONTROLLED_RUNTIME_UNAVAILABLE"
    assert report["steps"][1]["status"] == "SKIPPED"
    assert report["steps"][1]["code"] == "DOCKER_RUNTIME_UNAVAILABLE"
    assert report["controlledExecutionDiagnostic"]["code"] == "DOCKER_RUNTIME_UNAVAILABLE"
    assert report["controlledExecutionProfile"]["id"] == "local-python-pytest-controlled-v1"
    assert report["safety"]["contestantCodeExecuted"] is False
    assert report["evidenceCoverage"]["readonlyStatic"]["checkTotal"] == 4


def test_lab_generate_from_source_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    exit_code, payload = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["status"] == "WAITING_REVIEW"
    task_id = payload["data"]["task"]["id"]
    expected_lab_output = f"examples/output/{task_id}-lab.json"
    assert payload["data"]["task"]["finalResultPath"] == expected_lab_output
    assert payload["data"]["dslPath"] == expected_lab_output
    assert payload["data"]["providerGeneration"]["dslPath"] == expected_lab_output
    assert payload["data"]["dsl"]["spec"]["materials"][0]["path"] == "examples/input/demo-source.md"
    assert len(payload["data"]["dsl"]["spec"]["objectives"]) >= 2
    assert len(payload["data"]["dsl"]["spec"]["steps"]) >= 3
    assert Path(expected_lab_output).exists()
    assert payload["data"]["providerGeneration"]["provider"]["adapterId"] == "mock_provider_adapter"
    assert payload["data"]["providerGeneration"]["provider"]["realLlmCalled"] is False
    assert payload["data"]["providerGeneration"]["providerCallAuditEvent"]["status"] == "SUCCESS"
    assert payload["data"]["providerGeneration"]["providerCallAuditEvent"]["detail"]["workflowId"] == "lab_generate_from_source"
    assert payload["data"]["providerGeneration"]["providerCallAuditEvent"]["taskCreated"] is False
    assert payload["data"]["providerGeneration"]["providerCallAuditEvent"]["realLlmCalled"] is False
    assert payload["data"]["dsl"]["kind"] == "Lab"
    assert payload["data"]["materialAnalysis"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["materialAnalysis"]["unknownShellExecuted"] is False
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} == {"MATERIAL_ANALYSIS", "LAB_DSL"}
    assert all(artifact["realPublish"] is False for artifact in payload["data"]["artifacts"])
    readiness = payload["data"]["labFeatureReadiness"]
    assert readiness["component"] == "LabGenerationV1Readiness"
    assert readiness["completeForStableV1"] is True
    assert readiness["requirements"]["taskSpecificOutputCreated"] is True
    assert readiness["requirements"]["sourceMaterialReferenced"] is True
    assert readiness["requirements"]["minimumTeachingQualityMet"] is True
    assert readiness["safety"]["realPublish"] is False

    audit_exit, audit_payload = run_cli(
        ["provider", "audit", "--operation", "generateJson", "--prompt-id", "lab_generation_v0"],
        capsys,
    )
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 1
    assert audit_payload["data"]["items"][0]["detail"]["workflowStep"] == "generate_lab_dsl"

    approve_exit, approve_payload = run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)
    assert approve_exit == 0
    assert approve_payload["data"]["task"]["status"] == "APPROVED"

    import_output = tmp_path / "lab-v1-import-preview.json"
    import_exit, import_payload = run_cli(
        [
            "lab",
            "import-preview",
            "--task-id",
            task_id,
            "--reviewer",
            "teacher_1",
            "--output",
            str(import_output),
        ],
        capsys,
    )
    assert import_exit == 0
    preview = import_payload["data"]["labTemplateImportPreview"]
    assert preview["component"] == "LabTemplateImportPreview"
    assert preview["sourceDslPath"] == expected_lab_output
    assert preview["schemaValidated"] is True
    assert preview["labTemplateDraft"]["sourceDslPath"] == expected_lab_output
    assert preview["safety"]["realAgentImport"] is False
    assert preview["safety"]["realPublishAllowed"] is False
    Path(expected_lab_output).unlink(missing_ok=True)


def test_lab_generate_from_source_real_llm_mode_uses_explicit_opt_in_and_stays_review_gated(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    captured = {}

    def fake_run_real_llm_demo_dsl_generation(request, *, root):
        captured["request"] = request
        captured["root"] = root
        dsl = lab_cli.load_yaml(Path("templates/lab/examples/basic-lab.yaml"))
        dsl["metadata"]["id"] = "lab_real_cli_test"
        dsl["metadata"]["title"] = "未归一化真实 Lab"
        dsl["spec"]["materials"] = [{"type": "markdown", "path": "stale-input.md"}]
        dsl["spec"]["objectives"] = ["理解真实大模型生成 Lab DSL 的审核流程"]
        dsl["spec"]["steps"] = [
            {
                "id": "step_real_1",
                "title": "阅读材料",
                "instruction": "阅读输入素材并整理实验目标。",
                "commands": [],
            }
        ]
        return {
            "promptId": "lab_generation_v0",
            "promptVersion": "real-llm-demo-v1",
            "providerId": "openai",
            "model": "deepseek-v4-flash",
            "baseUrlConfigured": True,
            "baseUrlSource": "argument",
            "secretValueRead": True,
            "secretValueReturned": False,
            "networkAccess": True,
            "traceId": request.trace_id,
            "requestCount": 1,
            "singleRequestForKind": True,
            "schemaRepairAttempted": False,
            "schemaRepairApplied": False,
            "responseId": "resp_lab_cli_real_test",
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            "apiSurface": "chat.completions",
            "dsl": dsl,
            "dslId": "lab_real_cli_test",
            "inputRef": request.input_ref,
            "outputKind": "Lab",
            "generatedStatus": "WAITING_REVIEW",
            "reviewRequired": True,
            "schemaValidated": True,
            "normalization": {"applied": False, "patches": []},
            "schemaRepair": {"attempted": False, "applied": False, "errorCount": 0},
        }

    monkeypatch.setattr(lab_cli, "run_real_llm_demo_dsl_generation", fake_run_real_llm_demo_dsl_generation)

    exit_code, payload = run_cli(
        [
            "lab",
            "generate-from-source",
            "--input",
            "examples/input/demo-source.md",
            "--provider-mode",
            "real-llm",
            "--model",
            "deepseek-v4-flash",
            "--base-url",
            "https://api.deepseek.com",
            "--api-surface",
            "chat.completions",
            "--max-output-tokens",
            "2600",
            "--repair-on-schema-failure",
            "--explicit-real-call-opt-in",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    request = captured["request"]
    assert request.kind == "lab"
    assert request.model == "deepseek-v4-flash"
    assert request.base_url == "https://api.deepseek.com"
    assert request.api_surface == "chat.completions"
    assert request.max_output_tokens == 2600
    assert request.repair_on_schema_failure is True
    assert request.explicit_real_call_opt_in is True
    assert request.confirm_waiting_review is True
    assert request.confirm_no_auto_publish is True
    assert request.input_payload["labGenerationContext"]["taskId"].startswith("task_")
    data = payload["data"]
    task_id = data["task"]["id"]
    expected_lab_output = f"examples/output/{task_id}-lab.json"
    assert data["providerMode"] == "real-llm"
    assert data["task"]["status"] == "WAITING_REVIEW"
    assert data["task"]["modelName"] == "deepseek-v4-flash"
    assert data["task"]["promptVersion"] == "real-llm-demo-v1"
    assert data["task"]["finalResultPath"] == expected_lab_output
    assert data["dslPath"] == expected_lab_output
    provider = data["providerGeneration"]["provider"]
    assert provider["adapterId"] == "openai_responses_sdk_adapter"
    assert provider["mode"] == "REAL_LLM"
    assert provider["realLlmCalled"] is True
    assert provider["secretsRead"] is True
    assert provider["networkAccess"] is True
    assert provider["apiSurface"] == "chat.completions"
    assert data["providerGeneration"]["usage"]["total_tokens"] == 30
    assert data["providerGeneration"]["providerCallAuditEvent"]["realLlmCalled"] is True
    assert data["providerGeneration"]["providerCallAuditEvent"]["taskCreated"] is True
    assert data["providerGeneration"]["providerCallAuditEvent"]["detail"]["model"] == "deepseek-v4-flash"
    assert data["dsl"]["spec"]["materials"][0]["path"] == "examples/input/demo-source.md"
    assert len(data["dsl"]["spec"]["objectives"]) >= 2
    assert len(data["dsl"]["spec"]["steps"]) >= 3
    assert data["labFeatureReadiness"]["completeForStableV1"] is True
    assert data["labFeatureReadiness"]["safety"]["realLlmCalled"] is True
    assert data["labFeatureReadiness"]["safety"]["realPublish"] is False
    lab_artifact = next(artifact for artifact in data["artifacts"] if artifact["kind"] == "LAB_DSL")
    assert lab_artifact["metadata"]["providerAdapter"] == "openai_responses_sdk_adapter"
    assert lab_artifact["metadata"]["labFeatureReadiness"]["completeForStableV1"] is True

    audit_exit, audit_payload = run_cli(["provider", "audit", "--trace-id", payload["traceId"]], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["items"][0]["realLlmCalled"] is True
    assert audit_payload["data"]["items"][0]["mode"] == "REAL_LLM"
    Path(expected_lab_output).unlink(missing_ok=True)


def test_exam_generate_from_lab_real_llm_mode_outputs_task_specific_exam_grading_and_candidate_preview(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    captured = []

    def fake_run_real_llm_demo_dsl_generation(request, *, root):
        captured.append(request)
        if request.kind == "exam":
            dsl = {
                "version": "1.0",
                "kind": "Exam",
                "metadata": {
                    "id": "exam_real_cli_test",
                    "title": "未归一化真实 Exam",
                    "sourceLabId": "stale_lab",
                    "difficulty": "advanced",
                },
                "status": "WAITING_REVIEW",
                "spec": {
                    "questionType": "coding_task",
                    "totalScore": 99,
                    "questions": [
                        {
                            "id": "q1",
                            "title": "读取数据",
                            "stem": "请补全代码中用于读取 CSV 文件的函数。",
                            "blankCode": "df = pd.____('data.csv')",
                            "answer": "read_csv",
                            "score": 40,
                            "gradingRef": "check_q1",
                        },
                        {
                            "id": "q2",
                            "title": "输出评估指标",
                            "stem": "请补全模型评估环节需要输出的指标键名。",
                            "blankCode": "print(metrics['____'])",
                            "answer": "accuracy",
                            "score": 60,
                            "gradingRef": "check_q1",
                        },
                    ],
                },
            }
            dsl_id = "exam_real_cli_test"
            output_kind = "Exam"
        else:
            dsl = {
                "version": "1.0",
                "kind": "Grading",
                "metadata": {"id": "grading_real_cli_test", "title": "未归一化真实 Grading"},
                "status": "WAITING_REVIEW",
                "spec": {
                    "totalScore": 1,
                    "checks": [{"id": "stale_check", "type": "file_exists", "path": "result.txt", "score": 1}],
                },
            }
            dsl_id = "grading_real_cli_test"
            output_kind = "Grading"
        return {
            "promptId": f"{request.kind}_generation_v0",
            "promptVersion": "real-llm-demo-v1",
            "providerId": "openai",
            "model": "deepseek-v4-flash",
            "baseUrlConfigured": True,
            "baseUrlSource": "argument",
            "secretValueRead": True,
            "secretValueReturned": False,
            "networkAccess": True,
            "traceId": request.trace_id,
            "requestCount": 1,
            "singleRequestForKind": True,
            "schemaRepairAttempted": False,
            "schemaRepairApplied": False,
            "responseId": f"resp_{request.kind}_cli_real_test",
            "usage": {"input_tokens": 11, "output_tokens": 22, "total_tokens": 33},
            "apiSurface": "chat.completions",
            "dsl": dsl,
            "dslId": dsl_id,
            "inputRef": request.input_ref,
            "outputKind": output_kind,
            "generatedStatus": "WAITING_REVIEW",
            "reviewRequired": True,
            "schemaValidated": True,
            "normalization": {"applied": False, "patches": []},
            "schemaRepair": {"attempted": False, "applied": False, "errorCount": 0},
        }

    monkeypatch.setattr(lab_cli, "run_real_llm_demo_dsl_generation", fake_run_real_llm_demo_dsl_generation)

    exit_code, payload = run_cli(
        [
            "exam",
            "generate-from-lab",
            "--lab",
            "templates/lab/examples/basic-lab.yaml",
            "--provider-mode",
            "real-llm",
            "--model",
            "deepseek-v4-flash",
            "--base-url",
            "https://api.deepseek.com",
            "--api-surface",
            "chat.completions",
            "--max-output-tokens",
            "2600",
            "--repair-on-schema-failure",
            "--explicit-real-call-opt-in",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert [request.kind for request in captured] == ["exam", "grading"]
    assert captured[0].input_payload["labDsl"]["kind"] == "Lab"
    assert captured[0].model == "deepseek-v4-flash"
    assert captured[0].base_url == "https://api.deepseek.com"
    assert captured[0].api_surface == "chat.completions"
    assert captured[0].max_output_tokens == 2600
    assert captured[0].repair_on_schema_failure is True
    assert captured[0].explicit_real_call_opt_in is True
    assert captured[1].input_payload["examDsl"]["kind"] == "Exam"

    data = payload["data"]
    task_id = data["task"]["id"]
    expected_exam_output = f"examples/output/{task_id}-exam.json"
    expected_grading_output = f"examples/output/{task_id}-grading.json"
    expected_preview_output = f"examples/output/{task_id}-exam-candidate-preview.json"
    assert data["providerMode"] == "real-llm"
    assert data["task"]["status"] == "WAITING_REVIEW"
    assert data["task"]["inputType"] == "lab_dsl"
    assert data["task"]["modelName"] == "deepseek-v4-flash"
    assert data["examDslPath"] == expected_exam_output
    assert data["gradingDslPath"] == expected_grading_output
    assert data["candidatePreviewPath"] == expected_preview_output
    assert Path(expected_exam_output).exists()
    assert Path(expected_grading_output).exists()
    assert Path(expected_preview_output).exists()

    exam_dsl = json.loads(Path(expected_exam_output).read_text(encoding="utf-8"))
    grading_dsl = json.loads(Path(expected_grading_output).read_text(encoding="utf-8"))
    assert exam_dsl["metadata"]["sourceLabId"] == "lab_demo"
    assert exam_dsl["spec"]["totalScore"] == 100
    assert grading_dsl["metadata"]["sourceExamId"] == exam_dsl["metadata"]["id"]
    assert grading_dsl["spec"]["totalScore"] == 100
    assert {check["id"] for check in grading_dsl["spec"]["checks"]} == {"check_q1", "check_q2"}
    assert {item["checkId"] for item in grading_dsl["spec"]["assessmentPlan"]} == {"check_q1", "check_q2"}

    provider = data["providerGenerations"]["exam"]["provider"]
    assert provider["adapterId"] == "openai_responses_sdk_adapter"
    assert provider["mode"] == "REAL_LLM"
    assert provider["realLlmCalled"] is True
    assert data["providerGenerations"]["grading"]["providerCallAuditEvent"]["realLlmCalled"] is True
    candidate_preview = data["candidatePreview"]
    assert candidate_preview["kind"] == "ExamCandidatePreview"
    assert candidate_preview["answersRemoved"] is True
    assert candidate_preview["answerVisibleToCandidate"] is False
    assert all("answer" not in question for question in candidate_preview["questions"])
    assert all("gradingRef" not in question for question in candidate_preview["questions"])
    serialized_preview = json.dumps(candidate_preview, ensure_ascii=False)
    assert "read_csv" not in serialized_preview
    assert "accuracy" not in serialized_preview
    readiness = data["examGradingFeatureReadiness"]
    assert readiness["component"] == "ExamGradingGenerationV1Readiness"
    assert readiness["completeForStableV1"] is True
    assert readiness["requirements"]["labDslValidated"] is True
    assert readiness["requirements"]["questionGradingRefsUnique"] is True
    assert readiness["requirements"]["questionGradingRefsCovered"] is True
    assert readiness["requirements"]["candidatePreviewAnswerSafe"] is True
    assert readiness["requirements"]["scoreAligned"] is True
    assert readiness["safety"]["realLlmCalled"] is True
    assert readiness["safety"]["realAgentImport"] is False
    assert {artifact["kind"] for artifact in data["artifacts"]} == {"EXAM_DSL", "GRADING_DSL", "WORKFLOW_REPORT"}

    detail_exit, detail_payload = run_cli(["review", "detail", "--task-id", task_id], capsys)
    assert detail_exit == 0
    assert detail_payload["data"]["reviewDetail"]["mode"] == "REAL_LLM_EXAM_GRADING_WORKFLOW"

    approve_exit, approve_payload = run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_5"], capsys)
    assert approve_exit == 0
    assert approve_payload["data"]["task"]["status"] == "APPROVED"
    exam_import_exit, exam_import_payload = run_cli(
        ["exam", "import-preview", "--task-id", task_id, "--reviewer", "teacher_5", "--output", str(tmp_path / "exam-import.json")],
        capsys,
    )
    grading_import_exit, grading_import_payload = run_cli(
        ["grade", "import-preview", "--task-id", task_id, "--reviewer", "teacher_5", "--output", str(tmp_path / "grading-import.json")],
        capsys,
    )
    assert exam_import_exit == 0
    assert exam_import_payload["data"]["examQuestionImportPreview"]["sourceDslPath"] == expected_exam_output
    assert exam_import_payload["data"]["examQuestionImportPreview"]["safety"]["answerVisibleToCandidate"] is False
    assert grading_import_exit == 0
    assert grading_import_payload["data"]["gradingRuleImportPreview"]["sourceDslPath"] == expected_grading_output
    assert grading_import_payload["data"]["gradingRuleImportPreview"]["safety"]["realAgentImport"] is False

    Path(expected_exam_output).unlink(missing_ok=True)
    Path(expected_grading_output).unlink(missing_ok=True)
    Path(expected_preview_output).unlink(missing_ok=True)


def test_exam_generate_from_lab_real_llm_mode_requires_lab_dsl(capsys):
    exit_code, payload = run_cli(["exam", "generate-from-lab", "--provider-mode", "real-llm"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "lab"


def test_exam_candidate_preview_exports_answer_safe_json(tmp_path, capsys):
    output_path = tmp_path / "candidate-preview.json"

    exit_code, payload = run_cli(
        [
            "exam",
            "candidate-preview",
            "--exam",
            "templates/exam/examples/notebook-fill-blank.yaml",
            "--output",
            str(output_path),
        ],
        capsys,
    )
    exported = json.loads(output_path.read_text(encoding="utf-8"))
    serialized = json.dumps(payload, ensure_ascii=False)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output_path.exists()
    assert payload["data"]["candidatePreview"]["kind"] == "ExamCandidatePreview"
    assert payload["data"]["candidatePreview"]["sourceExamId"] == "exam_demo"
    assert payload["data"]["candidatePreview"]["answersRemoved"] is True
    assert payload["data"]["candidatePreview"]["answerVisibleToCandidate"] is False
    assert payload["data"]["candidatePreview"]["redaction"]["answerFieldsRemoved"] == 1
    assert "answer" not in payload["data"]["candidatePreview"]["questions"][0]
    assert "gradingRef" not in payload["data"]["candidatePreview"]["questions"][0]
    assert "questions[].gradingRef" in payload["data"]["candidatePreview"]["redaction"]["removedFields"]
    assert exported == payload["data"]["candidatePreview"]
    assert "read_csv" not in serialized


def test_exam_candidate_preview_missing_file_returns_json(capsys):
    exit_code, payload = run_cli(["exam", "candidate-preview", "--exam", "missing.yaml"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "exam"


def test_phase1_check_success(capsys):
    exit_code, payload = run_cli(["phase1", "check"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["passed"] is True
    assert payload["data"]["total"] >= 10
    assert {item["name"] for item in payload["data"]["checks"]} >= {
        "dsl_lab",
        "dsl_exam",
        "dsl_grading",
        "dsl_ppt",
        "unreviewed_publish_blocked",
        "backend_health",
        "artifact_manifest_mock",
    }


def test_phase1_check_missing_input_returns_json(capsys):
    exit_code, payload = run_cli(["phase1", "check", "--input", "missing.md"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"


def test_phase1_export_writes_delivery_package(tmp_path, capsys):
    output_path = tmp_path / "delivery-package.json"

    exit_code, payload = run_cli(
        ["phase1", "export", "--reviewer", "teacher_1", "--output", str(output_path)],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output_path.exists()
    package = json.loads(output_path.read_text(encoding="utf-8"))
    assert package["mode"] == "MOCK_ONLY"
    assert package["deliveryContract"]["path"] == "config/delivery-package.contract.json"
    assert "acceptanceChecklist" in package["deliveryContract"]["requiredSections"]
    assert package["deliveryManifest"]["summary"]["missingRequired"] == 0
    assert package["phase1Check"]["passed"] is True
    assert {item["kind"] for item in package["dslManifest"]} == {"lab", "exam", "grading", "ppt"}
    assert package["workflowReport"]["reviewRequired"] is True
    assert package["acceptanceSummary"]["passed"] is True
    assert package["acceptanceSummary"]["readyForPhase2MockHandoff"] is True
    assert all(item["passed"] for item in package["acceptanceChecklist"] if item["required"])
    assert all(assertion["passed"] for assertion in package["safetyAssertions"])
    assert "不发布真实实验或考试" in package["securityLimits"]
    assert payload["data"]["packagePath"] == str(output_path)


def test_phase1_export_missing_input_returns_json(tmp_path, capsys):
    output_path = tmp_path / "delivery-package.json"

    exit_code, payload = run_cli(
        ["phase1", "export", "--input", "missing.md", "--output", str(output_path)],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert not output_path.exists()


def test_phase1_report_writes_acceptance_markdown(tmp_path, capsys):
    package_path = tmp_path / "delivery-package.json"
    report_path = tmp_path / "phase1-acceptance-report.md"

    export_exit, _ = run_cli(["phase1", "export", "--output", str(package_path)], capsys)
    exit_code, payload = run_cli(
        ["phase1", "report", "--package", str(package_path), "--output", str(report_path)],
        capsys,
    )

    assert export_exit == 0
    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["acceptancePassed"] is True
    assert payload["data"]["missingRequired"] == 0
    assert payload["data"]["reportPath"] == str(report_path)
    content = report_path.read_text(encoding="utf-8")
    assert "# Phase 1 Mock 验收报告" in content
    assert "acceptanceSummary.passed" in content
    assert "`MOCK_ONLY`" in content
    assert "`real_llm_disabled`" in content
    assert "publishBlockedUntilApproved" in content


def test_phase1_report_missing_package_returns_json(tmp_path, capsys):
    report_path = tmp_path / "phase1-acceptance-report.md"

    exit_code, payload = run_cli(
        ["phase1", "report", "--package", "missing-delivery-package.json", "--output", str(report_path)],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "package"
    assert not report_path.exists()


def test_phase1_report_rejects_non_mock_package(tmp_path, capsys):
    package_path = tmp_path / "delivery-package.json"
    report_path = tmp_path / "phase1-acceptance-report.md"
    package_path.write_text(json.dumps({"phase": "Phase 1", "mode": "REAL"}), encoding="utf-8")

    exit_code, payload = run_cli(
        ["phase1", "report", "--package", str(package_path), "--output", str(report_path)],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "package.mode"
    assert not report_path.exists()


def test_ai_task_list_empty_store_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    exit_code, payload = run_cli(["ai-task", "list"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["items"] == []
    assert payload["data"]["total"] == 0


def test_artifact_list_empty_store_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    exit_code, payload = run_cli(["artifact", "list"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["items"] == []
    assert payload["data"]["total"] == 0


def test_artifact_list_rejects_unknown_kind(capsys):
    exit_code, payload = run_cli(["artifact", "list", "--kind", "UNKNOWN"], capsys)

    assert exit_code == 2
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"


@requires_presentations_runtime
def test_ppt_artifact_build_creates_waiting_review_pptx_artifact(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    output = tmp_path / "course-artifact.pptx"
    manifest = tmp_path / "course-artifact-manifest.json"
    preview = tmp_path / "course-artifact-slide-01.png"
    preview_dir = tmp_path / "course-artifact-slides"
    contact_sheet = tmp_path / "course-artifact-contact-sheet.png"

    exit_code, payload = run_cli(
        [
            "ppt",
            "artifact",
            "build",
            "--dsl",
            "templates/ppt/examples/course-ppt.yaml",
            "--output",
            str(output),
            "--manifest-output",
            str(manifest),
            "--preview-output",
            str(preview),
            "--preview-dir",
            str(preview_dir),
            "--contact-sheet-output",
            str(contact_sheet),
            "--reviewer",
            "teacher_1",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output.exists()
    assert manifest.exists()
    assert preview.exists()
    assert preview.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert (preview_dir / "slide-01.png").exists()
    assert (preview_dir / "slide-02.png").exists()
    assert (preview_dir / "slide-02.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert contact_sheet.exists()
    assert contact_sheet.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert zipfile.is_zipfile(output)
    with zipfile.ZipFile(output) as package:
        names = set(package.namelist())
    assert "ppt/presentation.xml" in names
    assert "ppt/slides/slide1.xml" in names
    assert "ppt/slides/slide2.xml" in names
    assert payload["data"]["mode"] == "LOCAL_PPTX_ARTIFACT_POC"
    assert payload["data"]["task"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["task"]["taskType"] == "PPT_ARTIFACT_GENERATION"
    assert payload["data"]["artifact"]["kind"] == "PPTX_FILE"
    assert payload["data"]["artifact"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["artifact"]["metadata"]["slideCount"] == 2
    assert payload["data"]["artifact"]["metadata"]["generator"] == "@oai/artifact-tool/presentation-jsx"
    assert payload["data"]["artifact"]["metadata"]["previewAvailable"] is True
    assert payload["data"]["artifact"]["metadata"]["firstSlidePreview"]["title"] == "AI 工具应用课程"
    assert payload["data"]["artifact"]["metadata"]["firstSlidePreview"]["imagePath"] == str(preview)
    assert payload["data"]["artifact"]["metadata"]["preview"]["renderAttempted"] is True
    assert payload["data"]["artifact"]["metadata"]["preview"]["reason"] == "PREVIEW_RENDERED"
    assert len(payload["data"]["artifact"]["metadata"]["slidePreviews"]) == 2
    assert payload["data"]["artifact"]["metadata"]["pageReviewSummary"]["status"] == "NEEDS_REVIEW"
    assert payload["data"]["artifact"]["metadata"]["pageReviewSummary"]["needsReview"] == 2
    assert payload["data"]["artifact"]["metadata"]["qualityReport"]["status"] == "PASS"
    assert payload["data"]["artifact"]["metadata"]["qualityReport"]["issueTotal"] == 0
    assert payload["data"]["artifact"]["metadata"]["pageReviewSummary"]["preflightStatus"] == "PASS"
    assert payload["data"]["artifact"]["metadata"]["slidePreviews"][0]["reviewStatus"] == "NEEDS_REVIEW"
    assert payload["data"]["artifact"]["metadata"]["slidePreviews"][0]["manualComment"]["required"] is True
    assert payload["data"]["artifact"]["metadata"]["slidePreviews"][0]["qaSignals"]["layout"] == "NEEDS_REVIEW"
    assert payload["data"]["artifact"]["metadata"]["slidePreviews"][1]["qaSignals"]["visualDensity"] == "BALANCED"
    assert payload["data"]["artifact"]["metadata"]["contactSheet"]["path"] == str(contact_sheet)
    assert manifest_payload["preview"]["previewAvailable"] is True
    assert manifest_payload["preview"]["renderAttempted"] is True
    assert manifest_payload["preview"]["reason"] == "PREVIEW_RENDERED"
    assert len(manifest_payload["preview"]["slidePreviews"]) == 2
    assert manifest_payload["preview"]["contactSheet"]["path"] == str(contact_sheet)
    assert manifest_payload["preview"]["firstSlide"]["title"] == "AI 工具应用课程"
    assert manifest_payload["preview"]["firstSlide"]["imagePath"] == str(preview)
    assert manifest_payload["qualityReport"]["status"] == "PASS"
    assert manifest_payload["qualityReport"]["issueTotal"] == 0
    assert payload["data"]["artifact"]["realLlmCalled"] is False
    assert payload["data"]["artifact"]["realPublish"] is False
    assert payload["data"]["safety"]["newLlmRequestSent"] is False
    assert payload["data"]["safety"]["secretsRead"] is False
    assert payload["data"]["safety"]["realPublish"] is False
    assert payload["data"]["operationAuditEvent"]["resourceType"] == "ARTIFACT"
    assert payload["data"]["operationAuditEvent"]["action"] == "PPTX_ARTIFACT_BUILD"
    _, listed = run_cli(["artifact", "list", "--kind", "PPTX_FILE"], capsys)
    assert listed["data"]["total"] == 1
    _, page_status = run_cli(["review", "ppt-page-status", "--task-id", payload["data"]["task"]["id"]], capsys)
    assert page_status["data"]["pptPageReview"]["available"] is True
    assert page_status["data"]["pptPageReview"]["pageReviewSummary"]["status"] == "NEEDS_REVIEW"
    assert page_status["data"]["pptPageReview"]["pageReviewSummary"]["total"] == 2
    assert page_status["data"]["pptPageReview"]["slideReviews"][0]["reviewStatus"] == "NEEDS_REVIEW"
    assert page_status["data"]["pptPageReview"]["operatorDecision"]["autoApproveAllowed"] is False
    _, page_update = run_cli(
        [
            "review",
            "ppt-page-update",
            "--task-id",
            payload["data"]["task"]["id"],
            "--slide-index",
            "1",
            "--review-status",
            "APPROVED",
            "--reviewer",
            "teacher_1",
            "--comment",
            "封面通过",
        ],
        capsys,
    )
    assert page_update["data"]["pptPageReviewUpdate"]["pptPageReview"]["pageReviewSummary"]["approved"] == 1
    assert page_update["data"]["pptPageReviewUpdate"]["pptPageReview"]["pageReviewSummary"]["needsReview"] == 1
    assert page_update["data"]["pptPageReviewUpdate"]["pptPageReview"]["slideReviews"][0]["reviewStatus"] == "APPROVED"
    assert page_update["data"]["pptPageReviewUpdate"]["operationAuditEvent"]["action"] == "PPT_PAGE_REVIEW_UPDATE"
    assert page_update["data"]["pptPageReviewUpdate"]["safety"]["taskStatusChanged"] is False


@requires_presentations_runtime
def test_review_ppt_page_update_revise_requires_comment(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(
        [
            "ppt",
            "artifact",
            "build",
            "--dsl",
            "templates/ppt/examples/course-ppt.yaml",
            "--output",
            str(tmp_path / "course-artifact.pptx"),
        ],
        capsys,
    )

    exit_code, payload = run_cli(
        [
            "review",
            "ppt-page-update",
            "--task-id",
            created["data"]["task"]["id"],
            "--slide-index",
            "1",
            "--review-status",
            "REVISE_REQUIRED",
            "--reviewer",
            "teacher_1",
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "comment"


def test_ppt_artifact_build_missing_dsl_returns_json(tmp_path, capsys):
    exit_code, payload = run_cli(
        [
            "ppt",
            "artifact",
            "build",
            "--dsl",
            str(tmp_path / "missing.yaml"),
            "--output",
            str(tmp_path / "artifact.pptx"),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "dsl"


def test_ppt_artifact_build_rejects_non_waiting_review_status(tmp_path, capsys):
    dsl = tmp_path / "approved-ppt.yaml"
    dsl.write_text(
        """
version: "1.0"
kind: "PPT"
metadata:
  id: "ppt_approved"
  title: "Approved PPT"
  audience: "students"
  durationMinutes: 10
status: "APPROVED"
spec:
  theme:
    style: "modern"
    language: "zh-CN"
  slides:
    - id: "slide_1"
      type: "title"
      title: "Approved PPT"
""".strip(),
        encoding="utf-8",
    )

    exit_code, payload = run_cli(
        [
            "ppt",
            "artifact",
            "build",
            "--dsl",
            str(dsl),
            "--output",
            str(tmp_path / "artifact.pptx"),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "status"


def test_material_analyze_records_artifact(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    exit_code, payload = run_cli(["material", "analyze", "--input", "examples/input/demo-source.md"], capsys)
    artifact_id = payload["data"]["artifact"]["id"]
    _, listed = run_cli(["artifact", "list", "--kind", "MATERIAL_ANALYSIS"], capsys)
    _, fetched = run_cli(["artifact", "get", "--id", artifact_id], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["artifact"]["kind"] == "MATERIAL_ANALYSIS"
    assert payload["data"]["artifact"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["artifact"]["realLlmCalled"] is False
    assert listed["data"]["total"] == 1
    assert fetched["data"]["artifact"]["id"] == artifact_id


def test_ai_task_list_returns_created_tasks(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    run_cli(["ppt", "generate", "--input", "examples/input/demo-source.md"], capsys)

    exit_code, payload = run_cli(["ai-task", "list"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["total"] == 2
    assert {item["taskType"] for item in payload["data"]["items"]} == {"LAB_GENERATION", "PPT_GENERATION"}


def test_ai_task_list_filters_by_status_and_task_type(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]
    run_cli(["ppt", "generate", "--input", "examples/input/demo-source.md"], capsys)
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    exit_code, payload = run_cli(
        ["ai-task", "list", "--status", "WAITING_REVIEW", "--task-type", "PPT_GENERATION"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["taskType"] == "PPT_GENERATION"
    assert payload["data"]["items"][0]["status"] == "WAITING_REVIEW"


def test_ai_task_list_rejects_unknown_status(capsys):
    exit_code, payload = run_cli(["ai-task", "list", "--status", "UNKNOWN"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "status"


def test_env_list_empty_store_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    exit_code, payload = run_cli(["env", "list"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["items"] == []
    assert payload["data"]["total"] == 0


def test_env_create_get_and_list(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    exit_code, created = run_cli(
        ["env", "create", "--type", "vm", "--title", "Ubuntu VM", "--image", "ubuntu-22.04"],
        capsys,
    )
    env_id = created["data"]["environment"]["id"]
    _, fetched = run_cli(["env", "get", "--id", env_id], capsys)
    _, listed = run_cli(["env", "list", "--type", "vm", "--status", "CREATED"], capsys)

    assert exit_code == 0
    assert_json_envelope(created)
    assert created["data"]["mode"] == "MOCK_ONLY"
    assert created["data"]["operationAuditEvent"]["action"] == "ENV_CREATE"
    assert created["data"]["operationAuditEvent"]["resourceType"] == "ENVIRONMENT"
    assert created["data"]["operationAuditEvent"]["realCloudResourceChanged"] is False
    assert fetched["data"]["environment"]["id"] == env_id
    assert listed["data"]["total"] == 1
    assert listed["data"]["items"][0]["envType"] == "vm"


def test_env_start_stop_reset(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(
        ["env", "create", "--type", "notebook", "--title", "Notebook", "--image", "jupyter/base"],
        capsys,
    )
    env_id = created["data"]["environment"]["id"]

    _, started = run_cli(["env", "start", "--id", env_id], capsys)
    _, stopped = run_cli(["env", "stop", "--id", env_id], capsys)
    exit_code, reset = run_cli(["env", "reset", "--id", env_id], capsys)

    assert started["data"]["environment"]["status"] == "RUNNING"
    assert stopped["data"]["environment"]["status"] == "STOPPED"
    assert exit_code == 0
    assert reset["data"]["environment"]["status"] == "STOPPED"
    assert started["data"]["operationAuditEvent"]["action"] == "ENV_START"
    assert stopped["data"]["operationAuditEvent"]["action"] == "ENV_STOP"
    assert reset["data"]["operationAuditEvent"]["action"] == "ENV_RESET"
    assert reset["data"]["operationAuditEvent"]["realCloudResourceChanged"] is False


def test_audit_list_filters_operation_events(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(
        ["env", "create", "--type", "vm", "--title", "Ubuntu VM", "--image", "ubuntu-22.04"],
        capsys,
    )
    env_id = created["data"]["environment"]["id"]

    exit_code, payload = run_cli(
        ["audit", "list", "--resource-type", "ENVIRONMENT", "--resource-id", env_id, "--action", "ENV_CREATE"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["resourceId"] == env_id
    assert payload["data"]["items"][0]["action"] == "ENV_CREATE"
    assert payload["data"]["items"][0]["mode"] == "MOCK_ONLY"


def test_provider_list_returns_mock_registry(capsys):
    exit_code, payload = run_cli(["provider", "list"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["activeProvider"] == "mock"
    assert payload["data"]["realLlmCalled"] is False
    assert payload["data"]["secretsRead"] is False
    assert [provider["id"] for provider in payload["data"]["providers"] if provider["enabled"]] == ["mock"]


def test_provider_health_returns_mock_status(capsys):
    exit_code, payload = run_cli(["provider", "health"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["providerId"] == "mock"
    assert payload["data"]["status"] == "UP"
    assert payload["data"]["realLlmCalled"] is False
    assert payload["data"]["secretsRead"] is False
    assert payload["data"]["networkAccess"] is False


def test_provider_real_llm_runtime_config_is_redacted(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-never-return")
    monkeypatch.setenv("OPENAI_MODEL", "mimo-v2.5-pro")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.test/v1")

    exit_code, payload = run_cli(["provider", "real-llm-runtime-config"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["component"] == "RealLlmRuntimeConfigSummary"
    assert payload["data"]["env"]["OPENAI_API_KEY"]["present"] is True
    assert payload["data"]["env"]["OPENAI_API_KEY"]["valueReturned"] is False
    assert "value" not in payload["data"]["env"]["OPENAI_API_KEY"]
    assert payload["data"]["env"]["OPENAI_MODEL"]["value"] == "mimo-v2.5-pro"
    assert payload["data"]["readyForRealLlmCommand"] is True
    assert payload["data"]["commandReadiness"]["canRunWithCurrentEnvironment"] is True
    assert payload["data"]["safeCommandTemplates"]["secretEnvPowerShell"] == '$env:OPENAI_API_KEY="<your-api-key>"'
    assert payload["data"]["safety"]["requestSent"] is False
    assert payload["data"]["safety"]["realLlmCalled"] is False
    assert "sk-test-never-return" not in json.dumps(payload)


def test_provider_real_llm_runtime_config_accepts_cli_model_and_base_url_without_secret(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-never-return")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    exit_code, payload = run_cli(
        [
            "provider",
            "real-llm-runtime-config",
            "--model",
            "deepseek-v4-flash",
            "--base-url",
            "https://api.deepseek.com",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    env = payload["data"]["env"]
    assert env["OPENAI_API_KEY"]["present"] is True
    assert "value" not in env["OPENAI_API_KEY"]
    assert env["OPENAI_MODEL"]["value"] == "deepseek-v4-flash"
    assert env["OPENAI_MODEL"]["source"] == "argument"
    assert env["OPENAI_MODEL"]["envPresent"] is False
    assert env["OPENAI_MODEL"]["argumentProvided"] is True
    assert env["OPENAI_BASE_URL"]["value"] == "https://<redacted-host>"
    assert env["OPENAI_BASE_URL"]["source"] == "argument"
    assert payload["data"]["readyForRealLlmCommand"] is True
    assert payload["data"]["commandReadiness"]["model"]["source"] == "argument"
    assert payload["data"]["commandReadiness"]["baseUrl"]["source"] == "argument"
    assert "deepseek-v4-flash" in payload["data"]["safeCommandTemplates"]["workflowRunArgs"]
    assert "https://api.deepseek.com" not in payload["data"]["safeCommandTemplates"]["workflowRunArgs"]
    assert "<openai-compatible-base-url>" in payload["data"]["safeCommandTemplates"]["workflowRunArgs"]
    assert "--confirm-real-dsl" in payload["data"]["safeCommandTemplates"]["workflowRunArgs"]
    assert payload["data"]["recommendedCliDefaults"]["modelSource"] == "argument"
    assert payload["data"]["recommendedCliDefaults"]["baseUrlSource"] == "argument"
    assert payload["data"]["safety"]["requestSent"] is False
    assert payload["data"]["safety"]["realLlmCalled"] is False
    assert "sk-test-never-return" not in json.dumps(payload)


def test_provider_health_rejects_disabled_provider(capsys):
    exit_code, payload = run_cli(["provider", "health", "--provider", "openai"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "PROVIDER_DISABLED"
    assert payload["errors"][0]["field"] == "provider"
    assert payload["providerErrorContext"]["adapterId"] == "mock_provider_adapter"
    assert payload["providerErrorContext"]["operation"] == "health"
    assert payload["providerErrorContext"]["providerId"] == "openai"
    assert payload["providerErrorContext"]["realLlmCalled"] is False
    assert payload["providerErrorContext"]["secretsRead"] is False
    assert payload["providerErrorContext"]["networkAccess"] is False
    assert payload["providerErrorContext"]["taskCreated"] is False


def test_provider_real_preflight_requires_explicit_opt_in(capsys):
    exit_code, payload = run_cli(["provider", "real-preflight", "--provider", "openai"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_PROVIDER_OPT_IN_REQUIRED"
    assert payload["errors"][0]["field"] == "explicitOptIn"
    assert payload["providerGateContext"]["mode"] == "MOCK_ONLY"
    assert payload["providerGateContext"]["defaultProvider"] == "mock"
    assert payload["providerGateContext"]["readyForRealProvider"] is False
    assert payload["providerGateContext"]["realLlmCalled"] is False
    assert payload["providerGateContext"]["secretsRead"] is False
    assert payload["providerGateContext"]["networkAccess"] is False


def test_provider_real_preflight_explicit_opt_in_still_disabled(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-never-return")

    exit_code, payload = run_cli(["provider", "real-preflight", "--provider", "openai", "--explicit-opt-in"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_PROVIDER_DISABLED"
    assert payload["providerGateContext"]["explicitOptIn"] is True
    assert payload["providerGateContext"]["secretValueReturned"] is False
    assert payload["providerGateContext"]["realLlmCalled"] is False
    assert payload["providerGateContext"]["secretsRead"] is False
    assert payload["providerGateContext"]["networkAccess"] is False
    assert "sk-never-return" not in json.dumps(payload)


def test_provider_mock_generate_returns_waiting_review_dsl(capsys):
    exit_code, payload = run_cli(
        ["provider", "mock-generate", "--prompt-id", "lab_generation_v0", "--input-ref", "examples/input/demo-source.md"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["providerId"] == "mock"
    assert payload["data"]["adapterId"] == "mock_provider_adapter"
    assert payload["data"]["interfaceName"] == "LLMProvider"
    assert payload["data"]["operation"] == "generateJson"
    assert payload["data"]["generatedStatus"] == "WAITING_REVIEW"
    assert payload["data"]["reviewRequired"] is True
    assert payload["data"]["publishBlockedUntilApproved"] is True
    assert payload["data"]["dslPath"] == "templates/lab/examples/basic-lab.yaml"
    assert payload["data"]["dsl"]["kind"] == "Lab"
    assert payload["data"]["realLlmCalled"] is False
    assert payload["data"]["secretsRead"] is False


def test_provider_mock_generate_rejects_unknown_prompt(capsys):
    exit_code, payload = run_cli(["provider", "mock-generate", "--prompt-id", "missing_prompt"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"][0]["field"] == "promptId"
    assert payload["providerErrorContext"]["operation"] == "generateJson"
    assert payload["providerErrorContext"]["generatedContentCreated"] is False
    assert payload["providerErrorContext"]["taskCreated"] is False
    assert payload["providerErrorContext"]["reviewBypassed"] is False


def test_provider_mock_generate_rejects_output_kind_mismatch(capsys):
    exit_code, payload = run_cli(
        ["provider", "mock-generate", "--prompt-id", "lab_generation_v0", "--output-kind", "Exam"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "outputKind"
    assert payload["providerErrorContext"]["errorCode"] == "VALIDATION_ERROR"
    assert payload["providerErrorContext"]["realLlmCalled"] is False


def test_provider_mock_generate_rejects_missing_prompt_id_with_safe_context(capsys):
    exit_code, payload = run_cli(["provider", "mock-generate"], capsys)

    assert exit_code == 2
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert "providerErrorContext" not in payload


def test_phase2_real_llm_schema_failure_reports_real_provider_context(monkeypatch, capsys, tmp_path):
    failure_report = tmp_path / "phase2-real-llm-failure-report.json"
    schema_failure_diagnostic = {
        "version": "real-llm-schema-failure-diagnostic-v1",
        "kind": "grading",
        "outputKind": "Grading",
        "errorTotal": 1,
        "errors": [
            {
                "field": "$.spec.assessmentPlan[0].executionPlan.requiredLimits.cpu",
                "reason": "expected string",
                "category": "expected_string",
                "sensitiveValueRedacted": False,
            }
        ],
    }

    def fake_run_phase2_content_generation(**kwargs):
        raise ProviderError(
            "REAL_LLM_DEMO_DSL_SCHEMA_VALIDATION_FAILED",
            "真实 LLM 生成内容未通过 Schema 校验",
            [{"field": "$.spec.assessmentPlan[0].executionPlan.requiredLimits.cpu", "reason": "expected string"}],
            {"schemaFailureDiagnostic": schema_failure_diagnostic},
        )

    monkeypatch.setattr(lab_cli, "run_phase2_content_generation", fake_run_phase2_content_generation)

    exit_code, payload = run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--provider-mode",
            "real-llm",
            "--model",
            "test-model",
            "--base-url",
            "https://example.test/v1",
            "--output",
            str(failure_report),
            "--explicit-real-call-opt-in",
            "--confirm-real-dsl",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_LLM_DEMO_DSL_SCHEMA_VALIDATION_FAILED"
    assert payload["providerErrorContext"]["adapterId"] == "openai_responses_sdk_adapter"
    assert payload["providerErrorContext"]["mode"] == "REAL_LLM"
    assert payload["providerErrorContext"]["providerId"] == "openai"
    assert payload["providerErrorContext"]["realLlmCalled"] is True
    assert payload["providerErrorContext"]["networkAccess"] is True
    assert payload["providerErrorContext"]["schemaFailureDiagnostic"] == schema_failure_diagnostic
    assert payload["details"]["schemaFailureDiagnostic"] == schema_failure_diagnostic
    assert payload["failureReportPath"] == str(failure_report)
    report = json.loads(failure_report.read_text(encoding="utf-8"))
    assert report["mode"] == "PHASE2_WORKFLOW_FAILURE_REPORT"
    assert report["status"] == "FAILED"
    assert report["code"] == "REAL_LLM_DEMO_DSL_SCHEMA_VALIDATION_FAILED"
    assert report["providerErrorContext"]["schemaFailureDiagnostic"] == schema_failure_diagnostic
    assert report["schemaFailureDiagnostic"] == schema_failure_diagnostic
    assert report["redaction"]["secretValuesIncluded"] is False
    assert report["redaction"]["rawGeneratedDslIncluded"] is False


def test_phase2_real_llm_cli_passes_schema_repair_flag(monkeypatch, capsys):
    captured = {}

    def fake_run_phase2_content_generation(**kwargs):
        captured.update(kwargs)
        raise ProviderError("STOP_TEST", "stop after argument capture", [])

    monkeypatch.setattr(lab_cli, "run_phase2_content_generation", fake_run_phase2_content_generation)

    exit_code, payload = run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--provider-mode",
            "real-llm",
            "--model",
            "test-model",
            "--base-url",
            "https://example.test/v1",
            "--api-surface",
            "chat.completions",
            "--repair-on-schema-failure",
            "--explicit-real-call-opt-in",
            "--confirm-real-dsl",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "STOP_TEST"
    assert captured["repair_on_schema_failure"] is True
    assert captured["api_surface"] == "chat.completions"
    assert captured["provider_mode"] == "real-llm"


def test_provider_audit_lists_success_and_failed_calls(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    health_exit, health = run_cli(["provider", "health"], capsys)
    failed_exit, failed = run_cli(["provider", "mock-generate", "--prompt-id", "missing_prompt"], capsys)
    list_exit, listed = run_cli(["provider", "audit"], capsys)
    filter_exit, filtered = run_cli(
        ["provider", "audit", "--operation", "generateJson", "--status", "FAILED", "--prompt-id", "missing_prompt"],
        capsys,
    )

    assert health_exit == 0
    assert failed_exit == 1
    assert list_exit == 0
    assert filter_exit == 0
    assert health["data"]["providerCallAuditEvent"]["status"] == "SUCCESS"
    assert health["data"]["providerCallAuditEvent"]["operation"] == "health"
    assert failed["providerErrorContext"]["generatedContentCreated"] is False
    assert listed["data"]["total"] == 2
    assert {item["status"] for item in listed["data"]["items"]} == {"SUCCESS", "FAILED"}
    assert filtered["data"]["total"] == 1
    event = filtered["data"]["items"][0]
    assert event["providerId"] == "mock"
    assert event["errorCode"] == "NOT_FOUND"
    assert event["realLlmCalled"] is False
    assert event["secretsRead"] is False
    assert event["taskCreated"] is False


def test_mcp_list_returns_manifest_tools(capsys):
    exit_code, payload = run_cli(["mcp", "list", "--tool", "workflow_demo"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["protocol"] == "mcp-contract-draft"
    assert payload["data"]["realMcpServerStarted"] is False
    assert payload["data"]["realAgentStarted"] is False
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["name"] == "workflow_demo"
    assert payload["data"]["items"][0]["backend"]["path"] == "/api/workflow/demo"


def test_mcp_call_invokes_local_backend_mock(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    exit_code, payload = run_cli(
        ["mcp", "call", "--tool", "analyze_material", "--arguments", json.dumps({"input": str(source)})],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["realMcpServerStarted"] is False
    assert payload["data"]["realAgentStarted"] is False
    assert payload["data"]["response"]["success"] is True
    assert payload["data"]["response"]["data"]["analysis"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["response"]["data"]["mcpTool"]["name"] == "analyze_material"
    assert payload["data"]["response"]["data"]["mcpToolCallRecord"]["status"] == "SUCCESS"
    assert payload["data"]["response"]["data"]["mcpToolCallRecord"]["actor"] == "lab-cli"

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--tool", "analyze_material"], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 1
    assert audit_payload["data"]["items"][0]["toolName"] == "analyze_material"
    assert audit_payload["data"]["items"][0]["status"] == "SUCCESS"


def test_mcp_call_runs_grading_evidence_auto(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    output = tmp_path / "mcp-auto-grading-evidence.json"

    exit_code, payload = run_cli(
        [
            "mcp",
            "call",
            "--tool",
            "run_grading_evidence_auto",
            "--arguments",
            json.dumps(
                {
                    "grading": "templates/grading/examples/mixed-checks.yaml",
                    "submission": "examples/submissions/readonly-demo",
                    "output": str(output),
                }
            ),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["mode"] == "MOCK_ONLY"
    response = payload["data"]["response"]
    assert response["success"] is True
    report = response["data"]["report"]
    assert report["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert report["sourceMode"] == "EVIDENCE_AUTO"
    assert report["steps"][0]["id"] == "readonly_static_evidence"
    assert report["steps"][1]["id"] == "controlled_command_evidence"
    assert report["steps"][1]["status"] == "SKIPPED"
    assert report["safety"]["controlledCommandIncluded"] is False
    assert response["data"]["mcpToolCallRecord"]["toolName"] == "run_grading_evidence_auto"
    assert response["data"]["mcpToolCallRecord"]["actor"] == "lab-cli"
    assert output.exists()

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--tool", "run_grading_evidence_auto"], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 1
    assert audit_payload["data"]["items"][0]["backendPath"] == "/api/grading/evidence-auto"
    assert audit_payload["data"]["items"][0]["status"] == "SUCCESS"


def test_mcp_call_rejects_invalid_arguments(capsys):
    exit_code, payload = run_cli(["mcp", "call", "--tool", "analyze_material", "--arguments", "{}"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"


def test_mcp_call_records_validation_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    exit_code, payload = run_cli(["mcp", "call", "--tool", "analyze_material", "--arguments", "{}"], capsys)
    audit_exit, audit_payload = run_cli(["mcp", "audit", "--status", "FAILED", "--tool", "analyze_material"], capsys)

    assert exit_code == 1
    assert payload["code"] == "VALIDATION_ERROR"
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 1
    record = audit_payload["data"]["items"][0]
    assert record["backendCalled"] is False
    assert record["errorCode"] == "VALIDATION_ERROR"
    assert record["argumentKeys"] == []


def test_mcp_server_info_and_tools_return_mock_runtime(capsys):
    info_exit, info = run_cli(["mcp", "server-info"], capsys)
    tools_exit, tools = run_cli(["mcp", "server-tools"], capsys)

    assert info_exit == 0
    assert tools_exit == 0
    assert_json_envelope(info)
    assert_json_envelope(tools)
    assert info["data"]["server"]["phase"] == "Phase 4"
    assert info["data"]["server"]["transport"] == "local_function_only"
    assert info["data"]["server"]["toolProfile"] == "local-core-mvp"
    assert info["data"]["server"]["manifestToolCount"] > info["data"]["server"]["toolCount"]
    assert info["data"]["safety"]["realMcpServerStarted"] is False
    assert info["data"]["safety"]["networkListenerStarted"] is False
    assert tools["data"]["total"] == tools["data"]["server"]["toolCount"]
    names = {tool["name"] for tool in tools["data"]["items"]}
    assert "analyze_material" in names
    assert "run_grading_evidence_auto" in names
    assert "create_agent_entity_import_dry_run" in names
    assert "agent_internal_publish_request" not in names
    assert "query_agent_publish_status" not in names
    assert "publish_lab" not in names
    assert "destroy_environment" not in names
    assert tools["data"]["toolPolicy"]["realPlatformBackendToolsEnabledByDefault"] is False


def test_mcp_server_call_invokes_tool_and_records_audit(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    exit_code, payload = run_cli(
        ["mcp", "server-call", "--tool", "analyze_material", "--arguments", json.dumps({"input": str(source)})],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["networkListenerStarted"] is False
    response = payload["data"]["response"]
    assert response["success"] is True
    assert response["data"]["mcpServer"]["id"] == "ai_training_platform_mcp_mock"
    assert response["data"]["mcpServerSafety"]["realMcpServerStarted"] is False
    assert response["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    assert response["data"]["mcpToolCallRecord"]["actor"] == "lab-cli-mcp-server"

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--tool", "analyze_material"], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 1
    assert audit_payload["data"]["items"][0]["actor"] == "lab-cli-mcp-server"


def test_mcp_stdio_smoke_cli_writes_json_report(tmp_path, capsys):
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    output = tmp_path / "mcp-stdio-client-smoke.json"

    exit_code, payload = run_cli(
        [
            "mcp",
            "stdio-smoke",
            "--input",
            str(source),
            "--work-dir",
            str(tmp_path / "mcp-stdio-smoke"),
            "--output",
            str(output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output.exists()
    report = payload["data"]["mcpStdioClientSmoke"]
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved == report
    assert report["success"] is True
    assert report["initialize"]["passed"] is True
    assert report["toolsList"]["passed"] is True
    assert report["toolCall"]["passed"] is True
    assert report["toolCall"]["analysisMode"] == "MOCK_ONLY"
    assert report["safety"]["networkListenerStarted"] is False
    assert payload["data"]["networkListenerStarted"] is False
    assert payload["data"]["realAgentStarted"] is False


def test_mcp_stdio_local_core_demo_cli_returns_review_gated_draft(tmp_path, capsys):
    source = tmp_path / "source.md"
    source.write_text("# Local Core MCP Client", encoding="utf-8")
    output = tmp_path / "mcp-local-core-client.json"

    exit_code, payload = run_cli(
        [
            "mcp",
            "stdio-local-core-demo",
            "--input",
            str(source),
            "--work-dir",
            str(tmp_path / "mcp-local-core-client"),
            "--output",
            str(output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output.exists()
    report = payload["data"]["mcpLocalCoreClient"]
    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert report["mode"] == "LOCAL_CORE_DRAFT_WAITING_REVIEW"
    assert report["generatedTask"]["status"] == "WAITING_REVIEW"
    assert report["stopReason"]["code"] == "WAITING_REVIEW_REQUIRED"
    assert report["pausedToolCheck"]["code"] == "MCP_TOOL_NOT_IN_PROFILE"
    assert payload["data"]["networkListenerStarted"] is False


def test_quality_regression_profiles_cli_returns_json(capsys):
    exit_code, payload = run_cli(["quality", "regression-profiles"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    profiles = payload["data"]["regressionProfiles"]
    assert profiles["defaultProfile"] == "quick"
    assert {item["id"] for item in profiles["profiles"]} >= {"quick", "core", "mcp"}
    assert profiles["safety"]["arbitraryCommandAllowed"] is False


def test_quality_dsl_eval_cli_writes_json_report(tmp_path, capsys):
    output = tmp_path / "dsl-quality-eval.json"

    exit_code, payload = run_cli(
        ["quality", "dsl-eval", "--output", str(output)],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    report = payload["data"]["dslQualityEvaluation"]
    assert report["success"] is True
    assert report["summary"]["caseTotal"] == 20
    assert report["summary"]["failedTotal"] == 0
    assert json.loads(output.read_text(encoding="utf-8")) == report


def test_quality_regression_matrix_cli_writes_json_report(tmp_path, monkeypatch, capsys):
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1 passed\n", stderr="")

    monkeypatch.setattr("quality.regression_matrix.subprocess.run", fake_run)
    output = tmp_path / "regression-matrix.json"

    exit_code, payload = run_cli(
        ["quality", "regression-matrix", "--profile", "mcp", "--output", str(output)],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output.exists()
    report = payload["data"]["regressionMatrix"]
    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert report["success"] is True
    assert report["profile"] == "mcp"
    assert report["passedTotal"] == 1
    assert report["commands"][0]["command"][1:3] == ["-m", "pytest"]
    assert report["safety"]["shellExecutionAllowed"] is False


def test_quality_regression_matrix_cli_returns_failure_json(tmp_path, monkeypatch, capsys):
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="failed")

    monkeypatch.setattr("quality.regression_matrix.subprocess.run", fake_run)
    output = tmp_path / "regression-matrix-failed.json"

    exit_code, payload = run_cli(
        ["quality", "regression-matrix", "--profile", "mcp", "--output", str(output)],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REGRESSION_MATRIX_FAILED"
    assert output.exists()
    assert payload["regressionMatrix"]["success"] is False
    assert payload["regressionMatrix"]["failedTotal"] == 1


def test_mcp_call_review_revision_loop_creates_mock_revision_task(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    source_task_id = created["data"]["task"]["id"]

    revision_exit, revision_payload = run_cli(
        [
            "mcp",
            "call",
            "--profile",
            "all",
            "--tool",
            "request_review_revision",
            "--arguments",
            json.dumps(
                {
                    "taskId": source_task_id,
                    "reviewer": "teacher_1",
                    "comment": "补充步骤截图验收标准。",
                    "priority": "HIGH",
                    "targetSections": ["steps"],
                }
            ),
        ],
        capsys,
    )
    revision_request_id = revision_payload["data"]["response"]["data"]["revisionRequest"]["id"]
    regenerate_exit, regenerate_payload = run_cli(
        [
            "mcp",
            "call",
            "--profile",
            "all",
            "--tool",
            "regenerate_from_revision_mock",
            "--arguments",
            json.dumps(
                {
                    "taskId": source_task_id,
                    "reviewer": "teacher_1",
                    "revisionRequestId": revision_request_id,
                }
            ),
        ],
        capsys,
    )

    assert revision_exit == 0
    assert_json_envelope(revision_payload)
    revision_response = revision_payload["data"]["response"]
    assert revision_response["success"] is True
    assert revision_response["data"]["revisionRequest"]["taskStatusChanged"] is False
    assert revision_response["data"]["revisionRequest"]["newLlmRequestSent"] is False
    assert revision_response["data"]["mcpToolCallRecord"]["toolName"] == "request_review_revision"
    assert regenerate_exit == 0
    assert_json_envelope(regenerate_payload)
    regeneration = regenerate_payload["data"]["response"]["data"]["mockRegeneration"]
    assert regeneration["sourceTask"]["status"] == "WAITING_REVIEW"
    assert regeneration["newTask"]["status"] == "WAITING_REVIEW"
    assert regeneration["newTask"]["taskType"] == "LAB_GENERATION_REVISION"
    assert regeneration["safety"]["newLlmRequestSent"] is False

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--tool", "regenerate_from_revision_mock"], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 1
    assert audit_payload["data"]["items"][0]["reviewRequired"] is True


def test_agent_real_demo_run_executes_mock_mcp_workflow(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    revision_output = tmp_path / "agent-lab-revision.json"

    exit_code, payload = run_cli(
        [
            "agent",
            "real-demo",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--revision-output",
            str(revision_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    agent_run = payload["data"]["agentRun"]
    assert agent_run["component"] == "RealDemoAgentMockRunner"
    assert agent_run["mode"] == "MOCK_AGENT_RUNNER"
    assert agent_run["summary"]["stepTotal"] == 8
    assert agent_run["summary"]["completedTotal"] == 8
    assert agent_run["agentReviewTriage"]["primaryRecommendedAction"] == "open_review_detail_and_collect_quality_evidence"
    assert agent_run["agentReviewTriage"]["autoApproveAllowed"] is False
    assert agent_run["agentReviewTriage"]["realPublishAllowed"] is False
    assert agent_run["agentReviewDetailGuidance"]["primaryRecommendedAction"] == "request_review_revision_before_any_publish"
    assert agent_run["agentReviewDetailGuidance"]["mockPublishEnabled"] is False
    assert agent_run["agentReviewDetailGuidance"]["realPublishAllowed"] is False
    assert agent_run["summary"]["sourceTaskStatus"] == "WAITING_REVIEW"
    assert agent_run["summary"]["newTaskStatus"] == "WAITING_REVIEW"
    assert agent_run["summary"]["labImportPreviewCreated"] is False
    assert agent_run["agentLabImportPreviewGuidance"]["enabled"] is False
    assert agent_run["toolResponses"]["audit"]["data"]["total"] == 1
    assert agent_run["safety"]["realAgentStarted"] is False
    assert agent_run["safety"]["realLlmCalled"] is False
    assert agent_run["safety"]["realMcpServerStarted"] is False
    assert agent_run["safety"]["realPublish"] is False
    assert payload["data"]["realAgentStarted"] is False
    assert payload["data"]["realLlmCalled"] is False
    assert payload["data"]["realMcpServerStarted"] is False
    assert revision_output.exists()

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--actor", "real-demo-agent-mock"], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 7


def test_agent_real_demo_plan_core_next_tool_uses_readonly_readiness(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    created_exit, created_payload = run_cli(
        ["lab", "generate-from-source", "--input", "examples/input/demo-source.md"],
        capsys,
    )
    task_id = created_payload["data"]["task"]["id"]
    output = tmp_path / "agent-core-next-tool-plan.json"

    exit_code, payload = run_cli(
        [
            "agent",
            "real-demo",
            "plan-core-next-tool",
            "--task-id",
            task_id,
            "--reviewer",
            "teacher_1",
            "--output",
            str(output),
        ],
        capsys,
    )

    assert created_exit == 0
    assert exit_code == 0
    assert_json_envelope(payload)
    assert output.exists()
    plan_run = payload["data"]["agentCoreNextToolPlan"]
    assert plan_run["component"] == "RealDemoAgentCoreNextToolPlanner"
    assert plan_run["summary"]["toolProfile"] == "local-core-mvp"
    assert plan_run["toolProfile"]["profile"] == "local-core-mvp"
    assert plan_run["summary"]["reasonCode"] == "HUMAN_APPROVAL_REQUIRED"
    assert plan_run["summary"]["recommendedToolName"] is None
    assert plan_run["summary"]["recommendedToolCalled"] is False
    assert plan_run["agentCoreNextToolPlan"]["safety"]["recommendedToolCalled"] is False
    assert payload["data"]["recommendedToolCalled"] is False
    audit_exit, audit_payload = run_cli(["mcp", "audit", "--actor", "real-demo-agent-mock"], capsys)
    assert audit_exit == 0
    records = audit_payload["data"]["items"]
    assert [record["toolName"] for record in records] == ["get_core_workflow_readiness"]
    assert records[0]["backendPath"] == f"/api/review-tasks/{task_id}/core-readiness"


def test_agent_real_demo_execute_core_next_tool_calls_confirmed_recommendation_once(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    created_exit, created_payload = run_cli(
        ["lab", "generate-from-source", "--input", "examples/input/demo-source.md"],
        capsys,
    )
    assert created_exit == 0
    task_id = created_payload["data"]["task"]["id"]
    approve_exit, approve_payload = run_cli(
        ["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"],
        capsys,
    )
    assert approve_exit == 0
    assert approve_payload["data"]["task"]["status"] == "APPROVED"
    tool_output = tmp_path / "lab-template-import-preview.json"
    report_output = tmp_path / "agent-core-next-tool-execution.json"

    exit_code, payload = run_cli(
        [
            "agent",
            "real-demo",
            "execute-core-next-tool",
            "--task-id",
            task_id,
            "--reviewer",
            "teacher_1",
            "--arguments",
            json.dumps({"output": str(tool_output)}),
            "--output",
            str(report_output),
            "--confirm-execute-recommended-tool",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert tool_output.exists()
    assert report_output.exists()
    execution = payload["data"]["agentCoreNextToolExecution"]
    assert execution["component"] == "RealDemoAgentCoreNextToolExecutor"
    assert execution["summary"]["executedToolName"] == "create_lab_template_import_preview"
    assert execution["summary"]["executedToolTotal"] == 1
    assert execution["summary"]["recommendedToolCalled"] is True
    assert execution["summary"]["postExecutionReasonCode"] == "PLATFORM_MOCK_IMPORT_PENDING"
    assert execution["summary"]["postExecutionRecommendedToolName"] == "create_lab_template_mock_import"
    assert execution["summary"]["canContinueWithSameCommand"] is True
    assert execution["postExecutionCoreNextToolPlan"]["toolName"] == "create_lab_template_mock_import"
    assert execution["nextSingleStepActionGuide"]["nextToolName"] == "create_lab_template_mock_import"
    assert execution["nextSingleStepActionGuide"]["canContinueWithSameCommand"] is True
    assert execution["nextSingleStepActionGuide"]["currentStop"]["reasonCode"] == "CONFIRMABLE_TOOL_READY"
    assert "nextTool=create_lab_template_mock_import" in execution["nextSingleStepActionGuide"]["operatorSummary"]
    assert "--confirm-execute-recommended-tool" in execution["nextSingleStepActionGuide"]["suggestedCliCommand"]
    assert execution["safety"]["singleToolExecution"] is True
    assert execution["safety"]["autoApproveAllowed"] is False
    assert execution["safety"]["autoPublishAllowed"] is False
    assert payload["data"]["executedToolName"] == "create_lab_template_import_preview"
    assert payload["data"]["recommendedToolCalled"] is True
    assert payload["data"]["reviewCenterReportUrl"] == (
        "review-center.html?"
        + urlencode({"taskId": task_id, "agentReport": str(report_output)})
    )
    assert "commandExecutedByPage" not in payload["data"]["reviewCenterReportUrl"]
    written_report = json.loads(report_output.read_text(encoding="utf-8"))
    assert written_report["reviewCenterReportUrl"] == payload["data"]["reviewCenterReportUrl"]
    assert written_report["reportPath"] == str(report_output)

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--actor", "real-demo-agent-mock"], capsys)
    assert audit_exit == 0
    records = audit_payload["data"]["items"]
    assert sorted(record["toolName"] for record in records) == [
        "create_lab_template_import_preview",
        "get_core_workflow_readiness",
        "get_core_workflow_readiness",
    ]
    import_record = next(record for record in records if record["toolName"] == "create_lab_template_import_preview")
    assert import_record["backendPath"] == "/api/labs/import-preview"


def test_agent_real_demo_execute_core_next_tool_advances_grading_to_dry_run(tmp_path, monkeypatch, capsys):
    task_id = create_approved_grading_task_with_decision_note(tmp_path, capsys, monkeypatch)
    preview_output = tmp_path / "agent-grading-import-preview.json"

    preview_exit, preview_payload = run_cli(
        [
            "agent",
            "real-demo",
            "execute-core-next-tool",
            "--task-id",
            task_id,
            "--reviewer",
            "teacher_1",
            "--arguments",
            json.dumps({"output": str(preview_output)}),
            "--confirm-execute-recommended-tool",
        ],
        capsys,
    )

    assert preview_exit == 0
    assert_json_envelope(preview_payload)
    preview_execution = preview_payload["data"]["agentCoreNextToolExecution"]
    assert preview_execution["summary"]["executedToolName"] == "create_grading_rule_import_preview"
    assert preview_execution["summary"]["postExecutionRecommendedToolName"] == "create_grading_rule_mock_import"
    assert preview_execution["nextSingleStepActionGuide"]["canContinueWithSameCommand"] is True
    assert preview_execution["safety"]["autoApproveAllowed"] is False
    assert preview_output.exists()

    mock_output = tmp_path / "agent-grading-mock-import.json"
    mock_exit, mock_payload = run_cli(
        [
            "agent",
            "real-demo",
            "execute-core-next-tool",
            "--task-id",
            task_id,
            "--reviewer",
            "teacher_1",
            "--arguments",
            json.dumps({"output": str(mock_output)}),
            "--confirm-execute-recommended-tool",
        ],
        capsys,
    )

    assert mock_exit == 0
    mock_execution = mock_payload["data"]["agentCoreNextToolExecution"]
    assert mock_execution["summary"]["executedToolName"] == "create_grading_rule_mock_import"
    assert mock_execution["summary"]["postExecutionRecommendedToolName"] == "create_agent_entity_import_dry_run"
    assert mock_execution["summary"]["postExecutionReasonCode"] == "PLATFORM_IMPORT_DRY_RUN_PENDING"
    assert mock_output.exists()

    dry_run_output = tmp_path / "agent-grading-platform-dry-run.json"
    dry_run_exit, dry_run_payload = run_cli(
        [
            "agent",
            "real-demo",
            "execute-core-next-tool",
            "--task-id",
            task_id,
            "--reviewer",
            "teacher_1",
            "--arguments",
            json.dumps({"output": str(dry_run_output)}),
            "--confirm-execute-recommended-tool",
        ],
        capsys,
    )

    assert dry_run_exit == 0
    dry_run_execution = dry_run_payload["data"]["agentCoreNextToolExecution"]
    assert dry_run_execution["summary"]["executedToolName"] == "create_agent_entity_import_dry_run"
    assert dry_run_execution["summary"]["postExecutionRecommendedToolName"] == "agent_internal_publish_request"
    assert dry_run_execution["summary"]["postExecutionReasonCode"] == "PLATFORM_IMPORT_REQUEST_PENDING"
    assert dry_run_execution["summary"]["toolProfile"] == "local-core-mvp"
    assert dry_run_execution["summary"]["postExecutionRecommendedToolInProfile"] is False
    assert dry_run_execution["summary"]["postExecutionBlockedByToolProfile"] is True
    assert dry_run_execution["postExecutionCoreNextToolPlan"]["blockedByToolProfile"] is True
    assert dry_run_execution["postExecutionCoreNextToolPlan"]["toolProfile"]["profile"] == "local-core-mvp"
    assert dry_run_execution["nextSingleStepActionGuide"]["requiresAdditionalArguments"] is False
    assert dry_run_execution["nextSingleStepActionGuide"]["placeholderErrors"] == []
    assert dry_run_execution["nextSingleStepActionGuide"]["currentStop"]["reasonCode"] == (
        "LOCAL_CORE_MVP_STOP_LINE_REACHED"
    )
    assert "AGENT_API_TOKEN" in dry_run_execution["nextSingleStepActionGuide"]["toolProfileStopGuidance"]["futureHandoff"]
    assert dry_run_execution["toolResponses"]["recommendedTool"]["data"]["agentEntityImportDryRun"]["entityType"] == (
        "grading_rule"
    )
    assert dry_run_output.exists()

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--actor", "real-demo-agent-mock"], capsys)
    assert audit_exit == 0
    tool_names = [record["toolName"] for record in audit_payload["data"]["items"]]
    assert tool_names.count("create_grading_rule_import_preview") == 1
    assert tool_names.count("create_grading_rule_mock_import") == 1
    assert tool_names.count("create_agent_entity_import_dry_run") == 1
    assert tool_names.count("get_core_workflow_readiness") >= 6


def test_agent_real_demo_run_creates_lab_import_preview_for_approved_task(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    revision_output = tmp_path / "agent-lab-revision.json"
    import_output = tmp_path / "agent-lab-import-preview.json"

    generate_exit, generated = run_cli(
        [
            "lab",
            "generate-from-source",
            "--input",
            "examples/input/demo-source.md",
        ],
        capsys,
    )
    assert generate_exit == 0
    approved_task_id = generated["data"]["task"]["id"]
    approve_exit, approve_payload = run_cli(
        ["review", "approve", "--task-id", approved_task_id, "--reviewer", "teacher_1"],
        capsys,
    )
    assert approve_exit == 0
    assert approve_payload["data"]["task"]["status"] == "APPROVED"

    exit_code, payload = run_cli(
        [
            "agent",
            "real-demo",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--revision-output",
            str(revision_output),
            "--approved-lab-task-id",
            approved_task_id,
            "--lab-import-output",
            str(import_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    agent_run = payload["data"]["agentRun"]
    assert agent_run["summary"]["stepTotal"] == 12
    assert agent_run["summary"]["completedTotal"] == 12
    assert agent_run["summary"]["approvedLabTaskId"] == approved_task_id
    assert agent_run["summary"]["labImportPreviewCreated"] is True
    assert agent_run["summary"]["labImportPreviewOutput"] == str(import_output)
    assert agent_run["approvedLabReviewDetailGuidance"]["taskStatus"] == "APPROVED"
    assert agent_run["approvedLabReviewDetailGuidance"]["platformImportPreviewEnabledTotal"] == 1
    assert agent_run["agentLabImportPreviewGuidance"]["enabled"] is True
    assert agent_run["agentLabImportPreviewGuidance"]["taskId"] == approved_task_id
    assert agent_run["agentLabImportPreviewGuidance"]["databaseWritten"] is False
    assert agent_run["agentLabImportPreviewGuidance"]["realAgentImport"] is False
    assert agent_run["agentLabImportPreviewGuidance"]["realPublishAllowed"] is False
    assert agent_run["toolResponses"]["postImportReviewDetail"]["data"]["reviewDetail"]["platformImportPreview"]["visible"] is True
    assert agent_run["toolResponses"]["postImportReviewDetail"]["data"]["reviewDetail"]["platformImportPreviewSignoff"]["readyForHumanSignoff"] is True
    assert agent_run["safety"]["databaseWritten"] is False
    assert agent_run["safety"]["realAgentImport"] is False
    assert agent_run["safety"]["realPublish"] is False
    assert revision_output.exists()
    assert import_output.exists()

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--actor", "real-demo-agent-mock"], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 11
    assert {item["toolName"] for item in audit_payload["data"]["items"]} >= {
        "get_review_detail",
        "create_lab_template_import_preview",
    }


def test_agent_real_demo_run_creates_exam_and_grading_import_previews(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    revision_output = tmp_path / "agent-lab-revision.json"
    exam_output = tmp_path / "agent-exam-import-preview.json"
    grading_output = tmp_path / "agent-grading-import-preview.json"

    generate_exit, generated = run_cli(["exam", "generate-from-lab", "--lab-id", "lab_demo"], capsys)
    assert generate_exit == 0
    approved_task_id = generated["data"]["task"]["id"]
    approve_exit, approve_payload = run_cli(
        ["review", "approve", "--task-id", approved_task_id, "--reviewer", "teacher_1"],
        capsys,
    )
    assert approve_exit == 0
    assert approve_payload["data"]["task"]["status"] == "APPROVED"

    exit_code, payload = run_cli(
        [
            "agent",
            "real-demo",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--revision-output",
            str(revision_output),
            "--approved-exam-task-id",
            approved_task_id,
            "--exam-import-output",
            str(exam_output),
            "--approved-grading-task-id",
            approved_task_id,
            "--grading-import-output",
            str(grading_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    agent_run = payload["data"]["agentRun"]
    assert agent_run["summary"]["stepTotal"] == 15
    assert agent_run["summary"]["completedTotal"] == 15
    assert agent_run["summary"]["approvedExamTaskId"] == approved_task_id
    assert agent_run["summary"]["approvedGradingTaskId"] == approved_task_id
    assert agent_run["summary"]["examImportPreviewCreated"] is True
    assert agent_run["summary"]["gradingImportPreviewCreated"] is True
    assert agent_run["summary"]["examImportPreviewOutput"] == str(exam_output)
    assert agent_run["summary"]["gradingImportPreviewOutput"] == str(grading_output)
    assert agent_run["agentExamImportPreviewGuidance"]["enabled"] is True
    assert agent_run["agentExamImportPreviewGuidance"]["sourceArtifactKind"] == "EXAM_DSL"
    assert agent_run["agentExamImportPreviewGuidance"]["answerVisibleToCandidate"] is False
    assert agent_run["agentExamImportPreviewGuidance"]["databaseWritten"] is False
    assert agent_run["agentGradingImportPreviewGuidance"]["enabled"] is True
    assert agent_run["agentGradingImportPreviewGuidance"]["sourceArtifactKind"] == "GRADING_DSL"
    assert agent_run["agentGradingImportPreviewGuidance"]["sandboxExecuted"] is False
    assert agent_run["agentGradingImportPreviewGuidance"]["contestantCodeExecuted"] is False
    assert agent_run["agentGradingImportPreviewGuidance"]["databaseWritten"] is False
    assert agent_run["toolResponses"]["examImportPreview"]["data"]["examQuestionImportPreview"]["safety"]["answerVisibleToCandidate"] is False
    assert agent_run["toolResponses"]["gradingImportPreview"]["data"]["gradingRuleImportPreview"]["safety"]["sandboxExecuted"] is False
    assert agent_run["toolResponses"]["postGradingImportReviewDetail"]["data"]["reviewDetail"]["platformImportPreview"]["total"] == 2
    assert agent_run["safety"]["databaseWritten"] is False
    assert agent_run["safety"]["realAgentImport"] is False
    assert agent_run["safety"]["realPublish"] is False
    assert revision_output.exists()
    assert exam_output.exists()
    assert grading_output.exists()

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--actor", "real-demo-agent-mock"], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 14
    assert {item["toolName"] for item in audit_payload["data"]["items"]} >= {
        "create_exam_question_import_preview",
        "create_grading_rule_import_preview",
    }


def test_agent_real_demo_run_collects_readonly_grading_evidence(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    revision_output = tmp_path / "agent-lab-revision.json"
    grading_output = tmp_path / "agent-grading-import-preview.json"
    evidence_output = tmp_path / "agent-readonly-grading-evidence.json"

    generate_exit, generated = run_cli(["exam", "generate-from-lab", "--lab-id", "lab_demo"], capsys)
    assert generate_exit == 0
    approved_task_id = generated["data"]["task"]["id"]
    approve_exit, approve_payload = run_cli(
        ["review", "approve", "--task-id", approved_task_id, "--reviewer", "teacher_1"],
        capsys,
    )
    assert approve_exit == 0
    assert approve_payload["data"]["task"]["status"] == "APPROVED"

    exit_code, payload = run_cli(
        [
            "agent",
            "real-demo",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--revision-output",
            str(revision_output),
            "--approved-grading-task-id",
            approved_task_id,
            "--grading-import-output",
            str(grading_output),
            "--readonly-grading-submission",
            "examples/submissions/readonly-demo",
            "--readonly-grading-output",
            str(evidence_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    agent_run = payload["data"]["agentRun"]
    assert agent_run["summary"]["stepTotal"] == 13
    assert agent_run["summary"]["gradingImportPreviewCreated"] is True
    assert agent_run["summary"]["readonlyGradingEvidenceCreated"] is True
    assert agent_run["summary"]["readonlyGradingEvidenceOutput"] == str(evidence_output)
    assert agent_run["summary"]["readonlyGradingEvidenceExecutedTotal"] >= 0
    assert agent_run["summary"]["readonlyGradingEvidenceDeferredTotal"] >= 1
    evidence_guidance = agent_run["agentReadonlyGradingEvidenceGuidance"]
    assert evidence_guidance["enabled"] is True
    assert evidence_guidance["readonlyOnly"] is True
    assert evidence_guidance["commandExecuted"] is False
    assert evidence_guidance["pytestExecuted"] is False
    assert evidence_guidance["notebookExecuted"] is False
    assert evidence_guidance["contestantCodeExecuted"] is False
    evidence = agent_run["toolResponses"]["readonlyGradingEvidence"]["data"]["report"]
    assert evidence["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert evidence["safety"]["commandExecuted"] is False
    assert evidence["safety"]["contestantCodeExecuted"] is False
    assert evidence_output.exists()
    assert grading_output.exists()

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--actor", "real-demo-agent-mock"], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 12
    assert {item["toolName"] for item in audit_payload["data"]["items"]} >= {
        "create_grading_rule_import_preview",
        "run_readonly_grading_evidence",
    }


def test_agent_real_demo_run_collects_controlled_grading_evidence(tmp_path, monkeypatch, capsys):
    store_path = tmp_path / "store.json"
    monkeypatch.setenv("LAB_CLI_STORE", str(store_path))
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)
    revision_output = tmp_path / "agent-lab-revision.json"
    grading_output = tmp_path / "agent-grading-import-preview.json"
    evidence_output = tmp_path / "agent-controlled-grading-evidence.json"
    grading_path = Path("templates/grading/examples/controlled-command-sandbox.yaml").resolve()
    store = JsonTaskStore(store_path)
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Controlled Docker grading plan",
        input_type="grading-dsl",
        input_ref=str(grading_path),
        final_result_path=str(grading_path),
        trace_id="trace_cli_agent_controlled_setup",
    )
    store.save(task)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.GRADING_DSL,
            path=str(grading_path),
            title="Controlled Docker Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id="trace_cli_agent_controlled_setup",
            task_id=task.id,
            source_ref=str(grading_path),
        )
    )
    approve_exit, approve_payload = run_cli(
        ["review", "approve", "--task-id", task.id, "--reviewer", "teacher_1"],
        capsys,
    )
    assert approve_exit == 0
    assert approve_payload["data"]["task"]["status"] == "APPROVED"

    exit_code, payload = run_cli(
        [
            "agent",
            "real-demo",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--revision-output",
            str(revision_output),
            "--approved-grading-task-id",
            task.id,
            "--grading-import-output",
            str(grading_output),
            "--controlled-grading-submission",
            "examples/submissions/controlled-command-demo",
            "--controlled-grading-output",
            str(evidence_output),
            "--controlled-grading-image",
            "local-python:demo",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    agent_run = payload["data"]["agentRun"]
    assert agent_run["summary"]["stepTotal"] == 13
    assert agent_run["summary"]["gradingImportPreviewCreated"] is True
    assert agent_run["summary"]["controlledGradingEvidenceCreated"] is True
    assert agent_run["summary"]["controlledGradingEvidenceOutput"] == str(evidence_output)
    assert agent_run["summary"]["controlledGradingEvidenceExecutedTotal"] == 2
    assert agent_run["summary"]["controlledGradingEvidenceEarnedScore"] == 100
    evidence_guidance = agent_run["agentControlledGradingEvidenceGuidance"]
    assert evidence_guidance["enabled"] is True
    assert evidence_guidance["readonlyOnly"] is False
    assert evidence_guidance["commandExecuted"] is True
    assert evidence_guidance["pytestExecuted"] is True
    assert evidence_guidance["contestantCodeExecuted"] is True
    assert evidence_guidance["networkEnabled"] is False
    evidence = agent_run["toolResponses"]["controlledGradingEvidence"]["data"]["report"]
    assert evidence["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert evidence["safety"]["commandExecuted"] is True
    assert evidence["safety"]["contestantCodeExecuted"] is True
    assert evidence["safety"]["networkEnabled"] is False
    assert evidence_output.exists()
    assert grading_output.exists()

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--actor", "real-demo-agent-mock"], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 12
    assert {item["toolName"] for item in audit_payload["data"]["items"]} >= {
        "create_grading_rule_import_preview",
        "run_controlled_grading_evidence",
    }


def test_agent_real_demo_run_collects_auto_grading_evidence(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    revision_output = tmp_path / "agent-lab-revision.json"
    grading_output = tmp_path / "agent-grading-import-preview.json"
    evidence_output = tmp_path / "agent-auto-grading-evidence.json"

    generate_exit, generated = run_cli(["exam", "generate-from-lab", "--lab-id", "lab_demo"], capsys)
    assert generate_exit == 0
    approved_task_id = generated["data"]["task"]["id"]
    approve_exit, approve_payload = run_cli(
        ["review", "approve", "--task-id", approved_task_id, "--reviewer", "teacher_1"],
        capsys,
    )
    assert approve_exit == 0
    assert approve_payload["data"]["task"]["status"] == "APPROVED"

    exit_code, payload = run_cli(
        [
            "agent",
            "real-demo",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--revision-output",
            str(revision_output),
            "--approved-grading-task-id",
            approved_task_id,
            "--grading-import-output",
            str(grading_output),
            "--auto-grading-submission",
            "examples/submissions/readonly-demo",
            "--auto-grading-output",
            str(evidence_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    agent_run = payload["data"]["agentRun"]
    assert agent_run["summary"]["stepTotal"] == 13
    assert agent_run["summary"]["gradingImportPreviewCreated"] is True
    assert agent_run["summary"]["autoGradingEvidenceCreated"] is True
    assert agent_run["summary"]["autoGradingEvidenceOutput"] == str(evidence_output)
    assert agent_run["summary"]["autoGradingEvidenceSourceReportTotal"] == 1
    assert agent_run["summary"]["autoGradingEvidenceControlledIncluded"] is False
    guidance = agent_run["agentAutoGradingEvidenceGuidance"]
    assert guidance["enabled"] is True
    assert guidance["readonlyAlwaysRunsFirst"] is True
    assert guidance["controlledCommandIncluded"] is False
    assert guidance["commandExecuted"] is False
    assert guidance["contestantCodeExecuted"] is False
    evidence = agent_run["toolResponses"]["autoGradingEvidence"]["data"]["report"]
    assert evidence["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert evidence["steps"][0]["id"] == "readonly_static_evidence"
    assert evidence["steps"][1]["status"] == "SKIPPED"
    detail_exit, detail_payload = run_cli(["review", "detail", "--task-id", approved_task_id], capsys)
    assert detail_exit == 0
    merged = detail_payload["data"]["reviewDetail"]["mergedGradingEvidence"]
    assert merged["visible"] is True
    assert merged["latestReportType"] == "GRADING_EVIDENCE_AUTO"
    assert merged["summary"]["autoEvidenceReport"] is True
    batch_exit, batch_payload = run_cli(["review", "batch-summary", "--status", "APPROVED"], capsys)
    assert batch_exit == 0
    signal = batch_payload["data"]["reviewTaskSummary"]["mergedGradingEvidenceReviewSignal"]
    assert signal["available"] is True
    assert signal["autoEvidenceReportTotal"] >= 1
    assert signal["latestReportType"] == "GRADING_EVIDENCE_AUTO"
    assert evidence_output.exists()
    assert grading_output.exists()

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--actor", "real-demo-agent-mock"], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 12
    assert {item["toolName"] for item in audit_payload["data"]["items"]} >= {
        "create_grading_rule_import_preview",
        "run_grading_evidence_auto",
    }


def test_agent_real_demo_run_collects_auto_grading_evidence_with_controlled_command(tmp_path, monkeypatch, capsys):
    store_path = tmp_path / "store.json"
    monkeypatch.setenv("LAB_CLI_STORE", str(store_path))
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)
    revision_output = tmp_path / "agent-lab-revision.json"
    grading_output = tmp_path / "agent-grading-import-preview.json"
    evidence_output = tmp_path / "agent-auto-controlled-grading-evidence.json"
    grading_path = Path("templates/grading/examples/controlled-command-sandbox.yaml").resolve()
    store = JsonTaskStore(store_path)
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Auto controlled Docker grading plan",
        input_type="grading-dsl",
        input_ref=str(grading_path),
        final_result_path=str(grading_path),
        trace_id="trace_cli_agent_auto_controlled_setup",
    )
    store.save(task)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.GRADING_DSL,
            path=str(grading_path),
            title="Auto Controlled Docker Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id="trace_cli_agent_auto_controlled_setup",
            task_id=task.id,
            source_ref=str(grading_path),
        )
    )
    approve_exit, approve_payload = run_cli(
        ["review", "approve", "--task-id", task.id, "--reviewer", "teacher_1"],
        capsys,
    )
    assert approve_exit == 0
    assert approve_payload["data"]["task"]["status"] == "APPROVED"

    exit_code, payload = run_cli(
        [
            "agent",
            "real-demo",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--revision-output",
            str(revision_output),
            "--approved-grading-task-id",
            task.id,
            "--grading-import-output",
            str(grading_output),
            "--auto-grading-submission",
            "examples/submissions/controlled-command-demo",
            "--auto-grading-output",
            str(evidence_output),
            "--auto-grading-include-controlled",
            "--auto-grading-image",
            "local-python:demo",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    agent_run = payload["data"]["agentRun"]
    assert agent_run["summary"]["stepTotal"] == 13
    assert agent_run["summary"]["gradingImportPreviewCreated"] is True
    assert agent_run["summary"]["autoGradingEvidenceCreated"] is True
    assert agent_run["summary"]["autoGradingEvidenceControlledIncluded"] is True
    guidance = agent_run["agentAutoGradingEvidenceGuidance"]
    assert guidance["controlledCommandRequested"] is True
    assert guidance["controlledCommandIncluded"] is True
    assert guidance["commandExecuted"] is True
    assert guidance["contestantCodeExecuted"] is True
    assert guidance["networkEnabled"] is False
    assert guidance["gradingDslCoverageStatus"] == "FULLY_COVERED_READY_FOR_HUMAN_DECISION"
    assert guidance["gradingDslDecisionNoteRecommendation"] == "approve-ready"
    evidence = agent_run["toolResponses"]["autoGradingEvidence"]["data"]["report"]
    assert evidence["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert evidence["summary"]["scorePreviewStatus"] == "READY_FOR_HUMAN_SCORE_REVIEW"
    assert evidence["gradingDslCoverageSummary"]["missingCheckIds"] == []
    assert evidence["safety"]["controlledCommandIncluded"] is True
    assert evidence["safety"]["contestantCodeExecuted"] is True
    assert evidence["safety"]["networkEnabled"] is False
    assert agent_run["safety"]["realPublish"] is False
    assert evidence_output.exists()
    assert grading_output.exists()

    audit_exit, audit_payload = run_cli(["mcp", "audit", "--actor", "real-demo-agent-mock"], capsys)
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 12
    assert {item["toolName"] for item in audit_payload["data"]["items"]} >= {
        "create_grading_rule_import_preview",
        "run_grading_evidence_auto",
    }


def test_mcp_call_high_risk_tool_creates_review_intent(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    exit_code, payload = run_cli(
        [
            "mcp",
            "call",
            "--tool",
            "publish_lab",
            "--profile",
            "all",
            "--arguments",
            json.dumps({"labId": "lab_demo", "reason": "运营申请发布"}),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    response = payload["data"]["response"]
    assert response["success"] is True
    assert response["data"]["intent"]["status"] == "WAITING_REVIEW"
    assert response["data"]["intent"]["realPublish"] is False
    assert response["data"]["intent"]["autoPublishAllowed"] is False
    assert response["data"]["task"]["taskType"] == "MCP_PUBLISH_LAB_INTENT"
    assert response["data"]["operationAuditEvent"]["action"] == "PUBLISH_LAB_INTENT"
    assert response["data"]["mcpToolCallRecord"]["toolName"] == "publish_lab"
    assert response["data"]["mcpToolCallRecord"]["reviewRequired"] is True


def test_mcp_server_call_high_risk_tool_requires_second_confirmation(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    exit_code, payload = run_cli(
        [
            "mcp",
            "server-call",
            "--tool",
            "destroy_environment",
            "--profile",
            "all",
            "--arguments",
            json.dumps({"environmentId": "env_demo", "reason": "清理申请"}),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    response = payload["data"]["response"]
    assert response["data"]["intent"]["requiresSecondConfirmation"] is True
    assert response["data"]["intent"]["environmentDestroyed"] is False
    assert response["data"]["intent"]["realCloudResourceChanged"] is False
    assert response["data"]["task"]["taskType"] == "MCP_DESTROY_ENVIRONMENT_INTENT"
    assert response["data"]["mcpToolCallRecord"]["riskLevel"] == "critical"


def test_mcp_call_gets_second_confirmation_status_read_only(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(
        [
            "mcp",
            "call",
            "--tool",
            "destroy_environment",
            "--profile",
            "all",
            "--arguments",
            json.dumps({"environmentId": "env_demo", "reason": "清理申请", "actor": "operator_1"}),
        ],
        capsys,
    )
    task_id = created["data"]["response"]["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    exit_code, payload = run_cli(
        [
            "mcp",
            "call",
            "--tool",
            "get_second_confirmation_status",
            "--profile",
            "all",
            "--arguments",
            json.dumps({"taskId": task_id}),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    response = payload["data"]["response"]
    assert response["success"] is True
    status = response["data"]["secondConfirmationStatus"]
    assert status["readOnly"] is True
    assert status["state"] == "APPROVED_PENDING_SECOND_CONFIRMATION"
    assert status["secondConfirmationRequired"] is True
    assert status["secondConfirmationSatisfied"] is False
    assert status["confirmationActionAvailable"] is False
    assert status["destroyRealEnvironmentEnabled"] is False
    assert status["environmentDestroyed"] is False
    record = response["data"]["mcpToolCallRecord"]
    assert record["toolName"] == "get_second_confirmation_status"
    assert record["actor"] == "lab-cli"
    assert record["reviewRequired"] is False
    assert record["riskLevel"] == "critical"


def test_mcp_call_second_confirmation_status_rejects_publish_intent(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(
        [
            "mcp",
            "call",
            "--tool",
            "publish_lab",
            "--profile",
            "all",
            "--arguments",
            json.dumps({"labId": "lab_demo", "reason": "运营申请发布", "actor": "operator_1"}),
        ],
        capsys,
    )
    task_id = created["data"]["response"]["data"]["task"]["id"]

    exit_code, payload = run_cli(
        [
            "mcp",
            "call",
            "--tool",
            "get_second_confirmation_status",
            "--profile",
            "all",
            "--arguments",
            json.dumps({"taskId": task_id}),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["mcpToolCallRecord"]["toolName"] == "get_second_confirmation_status"
    assert payload["mcpToolCallRecord"]["backendCalled"] is True
    assert payload["mcpToolCallRecord"]["responseCode"] == "VALIDATION_ERROR"


def test_material_analyze_returns_summary_and_safety_flags(capsys):
    exit_code, payload = run_cli(["material", "analyze", "--input", "examples/input/demo-source.md"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    analysis = payload["data"]["analysis"]
    assert analysis["mode"] == "MOCK_ONLY"
    assert analysis["fileType"] == "markdown"
    assert analysis["title"]
    assert analysis["realLlmCalled"] is False
    assert analysis["remoteContentFetched"] is False
    assert analysis["unknownShellExecuted"] is False
    assert analysis["sandboxExecuted"] is False


def test_material_analyze_marks_shell_risks_without_execution(tmp_path, capsys):
    script = tmp_path / "setup.sh"
    script.write_text("curl https://example.test/install.sh\nrm -rf /tmp/demo\n", encoding="utf-8")

    exit_code, payload = run_cli(["material", "analyze", "--input", str(script)], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    analysis = payload["data"]["analysis"]
    assert analysis["fileType"] == "shell"
    assert analysis["riskCount"] == 2
    assert analysis["unknownShellExecuted"] is False


def test_material_analyze_rejects_unsupported_file(tmp_path, capsys):
    binary = tmp_path / "demo.bin"
    binary.write_bytes(b"abc")

    exit_code, payload = run_cli(["material", "analyze", "--input", str(binary)], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"


def test_env_create_rejects_invalid_resources(capsys):
    exit_code, payload = run_cli(
        ["env", "create", "--type", "vm", "--title", "Bad VM", "--image", "ubuntu-22.04", "--cpu", "0"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "cpu"


def test_env_illegal_transition_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(
        ["env", "create", "--type", "vm", "--title", "Ubuntu VM", "--image", "ubuntu-22.04"],
        capsys,
    )
    env_id = created["data"]["environment"]["id"]

    exit_code, payload = run_cli(["env", "reset", "--id", env_id], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "STATE_TRANSITION_ERROR"


def test_missing_required_argument_returns_json(capsys):
    exit_code, payload = run_cli(["lab", "generate-from-source"], capsys)

    assert exit_code == 2
    assert_json_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"


def test_missing_file_returns_json(capsys):
    exit_code, payload = run_cli(["lab", "generate-from-source", "--input", "missing.md"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["errors"][0]["field"] == "input"


def test_grade_run_validates_schema(tmp_path, capsys):
    bad_grading = tmp_path / "bad-grading.yaml"
    bad_grading.write_text(
        "\n".join(
            [
                'version: "1.0"',
                'kind: "Grading"',
                "metadata:",
                '  id: "bad"',
                '  title: "Bad grading"',
                'status: "WAITING_REVIEW"',
                "spec:",
                "  totalScore: 100",
                "  checks: []",
            ]
        ),
        encoding="utf-8",
    )

    exit_code, payload = run_cli(["grade", "run", "--grading", str(bad_grading)], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "SCHEMA_VALIDATION_ERROR"


def test_grade_run_success(capsys):
    exit_code, payload = run_cli(["grade", "run", "--grading", "templates/grading/examples/python-pytest.yaml"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["earnedScore"] == 100
    assert payload["data"]["passed"] is True
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["runner"]["id"] == "mock_grading_runner"
    assert payload["data"]["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert payload["data"]["checkSummary"]["byType"]["pytest"] == 1
    assert payload["data"]["explainability"]["status"] == "EXPLAINABLE_MOCK_PLAN"
    assert payload["data"]["sandboxExecuted"] is False
    assert payload["data"]["commandExecuted"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "MOCK_GRADING_RUN"
    assert payload["data"]["operationAuditEvent"]["contestantCodeExecuted"] is False
    audit_detail = payload["data"]["operationAuditEvent"]["detail"]
    assert audit_detail["runner"]["id"] == "mock_grading_runner"
    assert audit_detail["sandboxPolicy"]["hostExecutionAllowed"] is False
    assert audit_detail["checkSummary"]["executed"] == 0
    assert audit_detail["explainability"]["realSandboxEvidenceRequired"] is True
    assert audit_detail["runRealPytestEnabled"] is False


def test_grade_run_mixed_checks_returns_phase3_runner_plan(capsys):
    exit_code, payload = run_cli(["grade", "run", "--grading", "templates/grading/examples/mixed-checks.yaml"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["phase"] == "Phase 3"
    assert payload["data"]["runner"]["supportedCheckTypes"] == SUPPORTED_GRADING_CHECK_TYPES
    assert payload["data"]["checkSummary"]["byType"] == {
        "file_exists": 1,
        "stdout_contains": 1,
        "pytest": 1,
        "notebook_cell": 1,
        "json_field": 1,
        "log_keyword": 1,
    }
    assert payload["data"]["checkSummary"]["executed"] == 0
    assert payload["data"]["explainability"]["eachCheckHasMockEvidencePlaceholder"] is True
    assert payload["data"]["sandboxExecuted"] is False
    assert payload["data"]["contestantCodeExecuted"] is False
    assert payload["data"]["commandExecuted"] is False
    assert all(check["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for check in payload["data"]["checks"])
    assert all(check["executionPlan"]["requiredLimits"]["network"] == "disabled_by_default" for check in payload["data"]["checks"])
    assert all(check["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED" for check in payload["data"]["checks"])
    audit_detail = payload["data"]["operationAuditEvent"]["detail"]
    assert audit_detail["phase"] == "Phase 3"
    assert audit_detail["runner"]["id"] == "mock_grading_runner"
    assert audit_detail["checkSummary"]["byType"] == {
        "file_exists": 1,
        "stdout_contains": 1,
        "pytest": 1,
        "notebook_cell": 1,
        "json_field": 1,
        "log_keyword": 1,
    }
    assert audit_detail["checkSummary"]["executed"] == 0
    assert len(audit_detail["checkPlans"]) == 6
    assert all(plan["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for plan in audit_detail["checkPlans"])
    assert all(plan["inputSummary"] for plan in audit_detail["checkPlans"])
    assert all(plan["commandExecuted"] is False for plan in audit_detail["checkPlans"])
    assert "runRealPytest" in audit_detail["blockedActions"]
    assert audit_detail["hostExecutionAllowed"] is False


def test_grade_run_writes_report(tmp_path, capsys):
    report_path = tmp_path / "grading-report.json"

    exit_code, payload = run_cli(
        ["grade", "run", "--grading", "templates/grading/examples/python-pytest.yaml", "--output", str(report_path)],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "MOCK_ONLY"
    assert report["runner"]["id"] == "mock_grading_runner"
    assert report["earnedScore"] == 100
    assert payload["data"]["reportPath"] == str(report_path)
    assert payload["data"]["artifact"]["kind"] == "GRADING_REPORT"
    assert payload["data"]["artifact"]["sandboxExecuted"] is False
    assert payload["data"]["artifact"]["metadata"]["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert payload["data"]["artifact"]["metadata"]["explainability"]["status"] == "EXPLAINABLE_MOCK_PLAN"


def test_grade_sandbox_precheck_success_writes_json_report(tmp_path, capsys):
    report_path = tmp_path / "grading-precheck.json"

    exit_code, payload = run_cli(
        [
            "grade",
            "sandbox-precheck",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "REAL_SANDBOX_PRECHECK_ONLY"
    assert report["readiness"]["status"] == "READY_FOR_MANUAL_SANDBOX_REVIEW"
    assert report["readiness"]["readyForRealSandboxImplementation"] is True
    assert report["readiness"]["readyForRealSandboxExecution"] is False
    assert report["summary"]["checkTotal"] == 6
    assert report["safety"]["sandboxExecuted"] is False
    assert report["safety"]["contestantCodeExecuted"] is False
    assert report["safety"]["commandExecuted"] is False
    assert report["safety"]["realPublish"] is False
    assert payload["data"]["reportPath"] == str(report_path)
    assert payload["data"]["operationAuditEvent"]["detail"]["reportType"] == "REAL_SANDBOX_PRECHECK"
    assert payload["data"]["operationAuditEvent"]["detail"]["realSandboxRunEnabled"] is False
    assert payload["data"]["artifact"]["kind"] == "GRADING_REPORT"
    assert payload["data"]["artifact"]["metadata"]["reportType"] == "REAL_SANDBOX_PRECHECK"
    assert payload["data"]["artifact"]["metadata"]["readyForRealSandboxExecution"] is False


def test_grade_sandbox_run_executes_readonly_file_checks(tmp_path, capsys):
    report_path = tmp_path / "readonly-sandbox-report.json"

    exit_code, payload = run_cli(
        [
            "grade",
            "sandbox-run",
            "--grading",
            "templates/grading/examples/readonly-sandbox.yaml",
            "--submission",
            "examples/submissions/readonly-demo",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert report["executionSummary"]["executed"] == 4
    assert report["executionSummary"]["deferred"] == 1
    assert report["checkSummary"]["executed"] == 4
    assert report["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert report["reportDetail"]["source"] == "sandbox.grade_runner.build_grading_report_detail"
    assert report["reportDetail"]["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert report["reportDetail"]["checkSummary"]["executed"] == 4
    assert report["reportDetail"]["checkPlans"][0]["readonlyEvidence"]["status"] == "COLLECTED"
    assert report["reportDetail"]["checkPlans"][2]["readonlyEvidence"]["method"] == "STATIC_NOTEBOOK_JSON_PARSE"
    assert report["reportDetail"]["checkPlans"][3]["readonlyEvidence"]["method"] == "STATIC_LOG_TEXT_SCAN"
    assert report["score"]["earnedScore"] == 120
    assert report["safety"]["sandboxExecuted"] is True
    assert report["safety"]["readonlyOnly"] is True
    assert report["safety"]["contestantCodeExecuted"] is False
    assert report["safety"]["commandExecuted"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "READONLY_SANDBOX_RUN"
    assert payload["data"]["operationAuditEvent"]["detail"]["blockedActions"] == [
        "executeGradingCommand",
        "runRealPytest",
        "executeNotebook",
        "executeContestantCode",
        "unknownShellExecution",
        "networkAccess",
        "realPublish",
    ]
    assert payload["data"]["artifact"]["kind"] == "GRADING_REPORT"
    assert payload["data"]["artifact"]["sandboxExecuted"] is True
    assert payload["data"]["artifact"]["contestantCodeExecuted"] is False
    assert payload["data"]["artifact"]["metadata"]["reportType"] == "READONLY_SANDBOX_RUN"
    assert payload["data"]["reportDetail"]["source"] == "sandbox.grade_runner.build_grading_report_detail"
    assert payload["data"]["reportDetail"]["audit"]["action"] == "READONLY_SANDBOX_RUN"
    assert payload["data"]["artifact"]["metadata"]["reportDetailSummary"]["checkSummary"]["executed"] == 4


def test_grade_sandbox_run_missing_submission_returns_json(tmp_path, capsys):
    exit_code, payload = run_cli(
        [
            "grade",
            "sandbox-run",
            "--grading",
            "templates/grading/examples/readonly-sandbox.yaml",
            "--submission",
            str(tmp_path / "missing"),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "submission"


def test_grade_sandbox_run_controlled_command_mode_returns_json(tmp_path, capsys, monkeypatch):
    report_path = tmp_path / "controlled-sandbox-report.json"

    def fake_run(args, **kwargs):
        if args[:2] == ["docker", "info"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout='"29.5.3"', stderr="")
        if args[:3] == ["docker", "image", "inspect"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="sha256:demo", stderr="")
        if "main.py" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="accuracy=0.90\n", stderr="")
        if "pytest" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="1 passed\n", stderr="")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_run)

    exit_code, payload = run_cli(
        [
            "grade",
            "sandbox-run",
            "--execution-mode",
            "controlled-command",
            "--grading",
            "templates/grading/examples/controlled-command-sandbox.yaml",
            "--submission",
            "examples/submissions/controlled-command-demo",
            "--image",
            "local-python:demo",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert report["executionSummary"]["executed"] == 2
    assert report["executionSummary"]["completed"] == 2
    assert report["executionSummary"]["passed"] == 2
    assert report["score"]["earnedScore"] == 100
    assert report["isolation"]["submissionMount"]["mode"] == "ro"
    assert report["isolation"]["networkEnabled"] is False
    assert report["isolation"]["outputPolicy"]["stdoutCaptured"] is True
    assert report["isolation"]["outputPolicy"]["maxOutputChars"] == 12000
    assert report["isolationQuality"]["qualityState"] == "CONTROLLED_DOCKER_ISOLATION_READY"
    assert report["isolationQuality"]["readyForLocalControlledEvidence"] is True
    assert report["isolationQuality"]["reviewBoundary"]["localEvidenceOnly"] is True
    assert report["imageSupplyChain"]["inspection"]["imageId"] == "sha256:demo"
    assert report["imageSupplyChain"]["allowlist"]["status"] == "MATCHED"
    assert report["imageSupplyChain"]["registry"]["automaticPullDisabled"] is True
    assert report["safety"]["sandboxExecuted"] is True
    assert report["safety"]["contestantCodeExecuted"] is True
    assert report["safety"]["commandExecuted"] is True
    assert report["safety"]["networkEnabled"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "CONTROLLED_SANDBOX_RUN"
    assert payload["data"]["operationAuditEvent"]["detail"]["reportType"] == "CONTROLLED_DOCKER_SANDBOX_RUN"
    assert payload["data"]["operationAuditEvent"]["detail"]["isolation"]["submissionMount"]["mode"] == "ro"
    assert payload["data"]["operationAuditEvent"]["detail"]["isolationQuality"]["criticalIsolationReady"] is True
    assert payload["data"]["operationAuditEvent"]["detail"]["imageSupplyChain"]["inspection"]["imageId"] == "sha256:demo"
    assert payload["data"]["operationAuditEvent"]["detail"]["blockedActions"] == [
        "executeNotebook",
        "unknownShellExecution",
        "networkAccess",
        "hostExecution",
        "realPublish",
    ]
    assert payload["data"]["artifact"]["metadata"]["reportType"] == "CONTROLLED_DOCKER_SANDBOX_RUN"
    assert payload["data"]["artifact"]["metadata"]["isolation"]["outputPolicy"]["artifactWriteOnlyByRunner"] is True
    assert payload["data"]["artifact"]["metadata"]["isolationQuality"]["qualityState"] == "CONTROLLED_DOCKER_ISOLATION_READY"
    assert payload["data"]["artifact"]["metadata"]["imageSupplyChain"]["allowlist"]["status"] == "MATCHED"
    assert payload["data"]["artifact"]["sandboxExecuted"] is True
    assert payload["data"]["artifact"]["contestantCodeExecuted"] is True
    assert payload["data"]["reportDetail"]["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert payload["data"]["reportDetail"]["isolation"]["containerReadOnlyRootFilesystem"] is True
    assert payload["data"]["reportDetail"]["isolationQuality"]["readyForLocalControlledEvidence"] is True
    assert payload["data"]["reportDetail"]["imageSupplyChain"]["registry"]["registryAuthUsed"] is False
    assert payload["data"]["reportDetail"]["audit"]["action"] == "CONTROLLED_SANDBOX_RUN"


def test_grade_evidence_merge_combines_readonly_and_controlled_reports(tmp_path, capsys, monkeypatch):
    result = create_mixed_evidence_merge_for_task(tmp_path, capsys, monkeypatch)
    assert result["mergedReportPath"].exists()
    merged = json.loads(result["mergedReportPath"].read_text(encoding="utf-8"))
    assert merged["mode"] == "GRADING_EVIDENCE_MERGE_REPORT"
    assert merged["summary"]["checkTotal"] == 6
    assert merged["summary"]["executed"] == 6
    assert merged["summary"]["passedCheckTotal"] == 6
    assert merged["summary"]["deferredCheckTotal"] == 0
    assert merged["summary"]["passed"] is True
    assert merged["summary"]["totalScore"] == 100
    assert merged["summary"]["earnedScore"] == 100
    assert merged["summary"]["manualReviewRequired"] is True
    assert merged["summary"]["autoApproveAllowed"] is False
    assert merged["evidenceCoverage"]["controlledDocker"]["checkIds"] == ["check_stdout_accuracy", "check_pytest"]
    assert merged["evidenceCoverage"]["readonlyStatic"]["checkIds"] == [
        "check_result_file",
        "check_notebook_accuracy",
        "check_metrics_json",
        "check_training_log",
    ]
    assert merged["evidenceCoverage"]["coverageRatio"] == 1.0
    assert merged["safety"]["contestantCodeExecuted"] is True
    assert merged["safety"]["hostExecutionAllowed"] is False
    assert merged["operationAuditEvent"]["action"] == "GRADING_EVIDENCE_MERGE"
    assert merged["artifact"]["metadata"]["reportType"] == "GRADING_EVIDENCE_MERGE"


def test_grade_evidence_readiness_reads_existing_report(tmp_path, capsys, monkeypatch):
    result = create_mixed_evidence_merge_for_task(tmp_path, capsys, monkeypatch)
    output = tmp_path / "evidence-readiness.json"

    exit_code, payload = run_cli(
        [
            "grade",
            "evidence-readiness",
            "--report",
            str(result["mergedReportPath"]),
            "--output",
            str(output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output.exists()
    readiness = payload["data"]["gradingEvidenceReadiness"]
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["mode"] == "GRADING_EVIDENCE_READINESS"
    assert readiness["summary"]["checkTotal"] == 6
    assert readiness["summary"]["evidenceReadyTotal"] == 6
    assert readiness["summary"]["missingEvidenceTotal"] == 0
    assert readiness["summary"]["readyForApprovalRecommendation"] is True
    assert readiness["summary"]["autoApproveAllowed"] is False
    assert readiness["safety"]["readExistingReportsOnly"] is True
    assert readiness["safety"]["sandboxExecutedByReadiness"] is False
    assert readiness["safety"]["contestantCodeExecutedByReadiness"] is False
    assert readiness["nextActions"][-1]["id"] == "review_ready_score_and_evidence"


def test_grade_evidence_merge_can_attach_to_review_detail(tmp_path, capsys, monkeypatch):
    store_path = tmp_path / "store.json"
    monkeypatch.setenv("LAB_CLI_STORE", str(store_path))

    grading_path = Path("templates/grading/examples/mixed-checks.yaml").resolve()
    store = JsonTaskStore(store_path)
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Merged grading evidence review",
        input_type="grading-dsl",
        input_ref=str(grading_path),
        final_result_path=str(grading_path),
        trace_id="trace_cli_merge_detail_setup",
    )
    store.save(task)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.GRADING_DSL,
            path=str(grading_path),
            title="Mixed Checks Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id="trace_cli_merge_detail_setup",
            task_id=task.id,
            source_ref=str(grading_path),
            metadata={"dslKind": "Grading", "reviewRequired": True},
        )
    )

    result = create_mixed_evidence_merge_for_task(tmp_path, capsys, monkeypatch, task_id=task.id)
    merge_payload = result["mergePayload"]
    assert_json_envelope(merge_payload)
    assert merge_payload["data"]["artifact"]["taskId"] == task.id

    detail_exit_code, detail_payload = run_cli(["review", "detail", "--task-id", task.id], capsys)
    assert detail_exit_code == 0
    detail = detail_payload["data"]["reviewDetail"]
    merged = detail["mergedGradingEvidence"]
    assert merged["visible"] is True
    assert merged["reportTotal"] == 1
    assert merged["summary"]["checkTotal"] == 6
    assert merged["summary"]["executedTotal"] == 6
    assert merged["summary"]["earnedScore"] == 100
    assert merged["summary"]["totalScore"] == 100
    assert merged["summary"]["coverageRatio"] == 1.0
    assert merged["summary"]["controlledDockerCheckTotal"] == 2
    assert merged["summary"]["readonlyStaticCheckTotal"] == 4
    assert merged["summary"]["checkEvidenceReviewItemTotal"] == 6
    assert merged["summary"]["manualCheckReviewTotal"] == 0
    assert len(merged["checkEvidenceReviewItems"]) == 6
    assert merged["reviewDecisionHints"]["overallHint"] == "READY_FOR_MANUAL_REVIEW_DECISION"
    assert merged["reviewDecisionHints"]["hintTotal"] == 6
    assert merged["reviewDecisionHints"]["approveReadyTotal"] == 6
    assert merged["summary"]["reviewDecisionHint"] == "READY_FOR_MANUAL_REVIEW_DECISION"
    controlled_check = next(
        item for item in merged["checkEvidenceReviewItems"] if item["checkId"] == "check_pytest"
    )
    assert controlled_check["evidenceSourceKind"] == "controlledDocker"
    assert controlled_check["recommendedAction"] == "verify_controlled_docker_output_and_score"
    assert controlled_check["manualReviewRequired"] is False
    readonly_check = next(
        item for item in merged["checkEvidenceReviewItems"] if item["checkId"] == "check_metrics_json"
    )
    assert readonly_check["evidenceSourceKind"] == "readonlyStatic"
    assert readonly_check["recommendedAction"] == "verify_static_evidence_and_score"
    assert merged["safety"]["mergeExecutedOnlyExistingReports"] is True
    assert merged["safety"]["contestantCodeExecuted"] is True
    assert merged["safety"]["hostExecutionAllowed"] is False
    assert detail["reviewPage"]["mergedGradingEvidence"] == merged
    assert detail["preApproveReviewCheck"]["applicable"] is True
    assert detail["preApproveReviewCheck"]["status"] == "APPROVE_ALLOWED_WITH_WARNINGS"
    assert detail["preApproveReviewCheck"]["summary"]["evidenceReady"] is True
    assert detail["preApproveReviewCheck"]["summary"]["reviewDecisionNoteRecorded"] is False
    assert detail["preApproveReviewCheck"]["summary"]["approveReadyDecision"] is False
    assert detail["preApproveReviewCheck"]["summary"]["warningTotal"] == 1
    assert detail["preApproveReviewCheck"]["summary"]["recommendedWarnings"] == [
        "review_decision_note_missing_before_approve"
    ]
    assert detail["reviewPage"]["preApproveReviewCheck"] == detail["preApproveReviewCheck"]
    assert detail["summary"]["mergedGradingEvidenceVisible"] is True
    assert detail["summary"]["mergedGradingEvidenceExecutedTotal"] == 6
    assert detail["summary"]["mergedGradingEvidenceEarnedScore"] == 100
    assert detail["summary"]["preApproveReviewCheckVisible"] is True
    assert detail["summary"]["preApproveReviewCheckWarningTotal"] == 1
    assert detail["summary"]["preApproveReviewCheckApproveReadyDecision"] is False
    assert detail["safety"]["mergeExecutedOnlyExistingReports"] is True
    assert detail["safety"]["networkEnabledForMergedGrading"] is False

    batch_exit_code, batch_payload = run_cli(["review", "batch-summary"], capsys)
    assert batch_exit_code == 0
    batch_summary = batch_payload["data"]["reviewTaskSummary"]
    signal = batch_summary["mergedGradingEvidenceReviewSignal"]
    assert signal["component"] == "MergedGradingEvidenceReviewSignal"
    assert signal["source"] == "reviewDetail.mergedGradingEvidence"
    assert signal["sourceMode"] == "DYNAMIC_MERGED_GRADING_EVIDENCE"
    assert signal["taskTotal"] == 1
    assert signal["reportTotal"] == 1
    assert signal["executed"] == 6
    assert signal["passedCheckTotal"] == 6
    assert signal["earnedScore"] == 100
    assert signal["totalScore"] == 100
    assert signal["coverageRatio"] == 1.0
    assert signal["controlledDockerCheckTotal"] == 2
    assert signal["readonlyStaticCheckTotal"] == 4
    assert signal["checkEvidenceReviewItemTotal"] == 6
    assert signal["manualCheckReviewTotal"] == 0
    assert signal["safety"]["mergeExecutedOnlyExistingReports"] is True
    assert signal["safety"]["contestantCodeExecuted"] is True
    assert signal["safety"]["networkAllowed"] is False
    assert signal["items"][0]["taskId"] == task.id
    assert signal["items"][0]["reportPath"] == str(result["mergedReportPath"])
    priority_item = batch_summary["reviewPriorityQueue"]["items"][0]
    assert priority_item["reasonCode"] == "MERGED_GRADING_EVIDENCE_REVIEW_REQUIRED"
    assert priority_item["recommendedAction"] == "review_merged_grading_evidence_before_approval"
    assert priority_item["mergedGradingEvidenceSummary"]["available"] is True
    assert priority_item["mergedGradingEvidenceSummary"]["coverageRatio"] == 1.0
    assert priority_item["mergedGradingEvidenceSummary"]["earnedScore"] == 100
    assert priority_item["mergedGradingEvidenceSummary"]["checkEvidenceReviewItemTotal"] == 6
    assert priority_item["mergedGradingEvidenceSummary"]["checkEvidenceReviewItems"][0]["checkId"]
    assert (
        priority_item["mergedGradingEvidenceSummary"]["reviewDecisionHintsSummary"]["overallHint"]
        == "READY_FOR_MANUAL_REVIEW_DECISION"
    )
    assert priority_item["mergedGradingEvidenceSummary"]["reviewDecisionHintsSummary"]["approveReadyTotal"] == 6
    assert priority_item["mergedGradingEvidenceSummary"]["reviewDecisionHintsSummary"]["autoApproveAllowed"] is False
    readiness = priority_item["gradingEvidenceReadinessSummary"]
    assert readiness["component"] == "GradingEvidenceReadiness"
    assert readiness["available"] is True
    assert readiness["status"] == "READY_FOR_APPROVAL_RECOMMENDATION"
    assert readiness["summary"]["evidenceReadyTotal"] == 6
    assert readiness["summary"]["missingEvidenceTotal"] == 0
    assert readiness["summary"]["readyForApprovalRecommendation"] is True
    assert readiness["safety"]["sandboxExecutedByReadiness"] is False
    assert readiness["actionGuide"]["component"] == "GradingEvidenceActionGuide"
    assert readiness["actionGuide"]["primaryAction"] == "review_ready_score_and_evidence_before_approval"
    assert readiness["actionGuide"]["api"]["path"] == "/api/grading/evidence-auto"
    assert "grade evidence-auto" in readiness["actionGuide"]["cli"]
    assert readiness["actionGuide"]["safety"]["autoApproveAllowed"] is False
    readiness_signal = batch_summary["gradingEvidenceReadinessSignal"]
    assert readiness_signal["component"] == "GradingEvidenceReadinessSignal"
    assert readiness_signal["availableTotal"] == 1
    assert readiness_signal["evidenceReadyTotal"] == 6
    assert readiness_signal["missingEvidenceTotal"] == 0
    assert readiness_signal["readyForApprovalRecommendationTotal"] == 1
    assert readiness_signal["autoApproveAllowed"] is False
    precheck = priority_item["preApproveReviewCheck"]
    assert precheck["component"] == "PreApproveReviewCheck"
    assert precheck["source"] == "reviewDetail.mergedGradingEvidence + reviewDetail.reviewDecisionNotes"
    assert precheck["applicable"] is True
    assert precheck["status"] == "APPROVE_ALLOWED_WITH_WARNINGS"
    assert precheck["approvalStillAllowed"] is True
    assert precheck["summary"]["evidenceReady"] is True
    assert precheck["summary"]["reviewDecisionNoteRecorded"] is False
    assert precheck["summary"]["approveReadyDecision"] is False
    assert precheck["summary"]["warningTotal"] == 1
    assert precheck["summary"]["recommendedWarnings"] == ["review_decision_note_missing_before_approve"]
    precheck_signal = batch_summary["preApproveReviewCheckSignal"]
    assert precheck_signal["component"] == "PreApproveReviewCheckSignal"
    assert precheck_signal["taskTotal"] == 1
    assert precheck_signal["applicableTotal"] == 1
    assert precheck_signal["readyForHumanApproveTotal"] == 0
    assert precheck_signal["approveAllowedWithWarningsTotal"] == 1
    assert precheck_signal["evidenceReadyTotal"] == 1
    assert precheck_signal["reviewDecisionNoteRecordedTotal"] == 0
    assert precheck_signal["warningTotal"] == 1
    assert precheck_signal["autoApproveAllowed"] is False

    note_output = tmp_path / "review-decision-note.json"
    note_exit_code, note_payload = run_cli(
        [
            "review",
            "decision-note",
            "--task-id",
            task.id,
            "--reviewer",
            "teacher_1",
            "--decision",
            "approve-ready",
            "--output",
            str(note_output),
        ],
        capsys,
    )
    assert note_exit_code == 0
    assert_json_envelope(note_payload)
    note = note_payload["data"]["decisionNote"]
    assert note["decision"] == "approve-ready"
    assert note["taskStatusBefore"] == "WAITING_REVIEW"
    assert note["taskStatusAfter"] == "WAITING_REVIEW"
    assert note["statusChanged"] is False
    assert note["safety"]["autoApproveAllowed"] is False
    assert note["reviewDecisionHintsSnapshot"]["overallHint"] == "READY_FOR_MANUAL_REVIEW_DECISION"
    assert note_payload["data"]["artifact"]["kind"] == "REVIEW_DECISION_NOTE"
    assert note_payload["data"]["operationAuditEvent"]["action"] == "REVIEW_DECISION_NOTE_RECORD"
    assert note_payload["data"]["reviewDetail"]["task"]["status"] == "WAITING_REVIEW"
    assert note_payload["data"]["reviewDetail"]["reviewDecisionNotes"]["total"] == 1
    assert note_payload["data"]["reviewDetail"]["reviewDecisionNotes"]["latest"]["decision"] == "approve-ready"
    assert json.loads(note_output.read_text(encoding="utf-8"))["artifact"]["kind"] == "REVIEW_DECISION_NOTE"

    post_note_batch_exit_code, post_note_batch_payload = run_cli(["review", "batch-summary"], capsys)
    assert post_note_batch_exit_code == 0
    post_note_summary = post_note_batch_payload["data"]["reviewTaskSummary"]
    post_note_precheck = post_note_summary["reviewPriorityQueue"]["items"][0]["preApproveReviewCheck"]
    assert post_note_precheck["status"] == "READY_FOR_HUMAN_APPROVE"
    assert post_note_precheck["summary"]["reviewDecisionNoteRecorded"] is True
    assert post_note_precheck["summary"]["approveReadyDecision"] is True
    assert post_note_precheck["summary"]["scorePreviewAvailable"] is True
    assert post_note_precheck["summary"]["scorePreviewStatus"] == "READY_FOR_HUMAN_SCORE_REVIEW"
    assert post_note_precheck["summary"]["scorePreviewEarnedScore"] == 100
    assert post_note_precheck["summary"]["scorePreviewTotalScore"] == 100
    assert post_note_precheck["summary"]["scorePreviewCoveredScore"] == 100
    assert post_note_precheck["summary"]["scorePreviewMissingScore"] == 0
    assert post_note_precheck["summary"]["scorePreviewReadyForDecisionNote"] is True
    assert post_note_precheck["summary"]["warningTotal"] == 0
    assert post_note_precheck["summary"]["latestDecision"] == "approve-ready"
    assert post_note_summary["preApproveReviewCheckSignal"]["readyForHumanApproveTotal"] == 1
    assert post_note_summary["preApproveReviewCheckSignal"]["warningTotal"] == 0

    core_exit_code, core_payload = run_cli(["review", "core-readiness", "--task-id", task.id], capsys)
    assert core_exit_code == 0
    assert_json_envelope(core_payload)
    core = core_payload["data"]["coreWorkflowReadinessReport"]
    assert core["component"] == "CoreWorkflowReadinessReport"
    assert core["taskId"] == task.id
    assert core["taskType"] == "GRADING_GENERATION"
    assert core["ready"] is False
    assert core["recommendedNextAction"] == "approve_generated_content_after_manual_review"
    assert core["summary"]["gradingEvidenceReady"] is True
    assert core["summary"]["gradingApproveReadyDecision"] is True
    assert core["summary"]["finalReviewState"] == "READY_FOR_HUMAN_APPROVE"
    assert core["nextToolRecommendation"]["finalReviewState"] == "READY_FOR_HUMAN_APPROVE"
    assert core["summary"]["gradingScorePreviewAvailable"] is True
    assert core["summary"]["gradingScorePreviewStatus"] == "READY_FOR_HUMAN_SCORE_REVIEW"
    assert core["summary"]["gradingScorePreviewEarnedScore"] == 100
    assert core["summary"]["gradingScorePreviewTotalScore"] == 100
    assert core["summary"]["gradingScorePreviewCoveredScore"] == 100
    assert core["summary"]["gradingScorePreviewMissingScore"] == 0
    assert core["summary"]["gradingScorePreviewReadyForDecisionNote"] is True
    assert {step["id"] for step in core["steps"]} >= {
        "generated_content_human_approved",
        "grading_evidence_ready",
        "grading_review_decision_note_recorded",
        "grading_decision_approve_ready",
    }
    grading_steps = {step["id"]: step for step in core["steps"]}
    assert grading_steps["grading_evidence_ready"]["ready"] is True
    assert grading_steps["grading_review_decision_note_recorded"]["ready"] is True
    assert grading_steps["grading_decision_approve_ready"]["ready"] is True
    assert core["safety"]["autoApproveAllowed"] is False
    assert core["safety"]["realPublish"] is False

    approve_exit_code, approve_payload = run_cli(
        ["review", "approve", "--task-id", task.id, "--reviewer", "teacher_2"],
        capsys,
    )
    assert approve_exit_code == 0
    precheck = approve_payload["data"]["preApproveReviewCheck"]
    assert precheck["applicable"] is True
    assert precheck["status"] == "READY_FOR_HUMAN_APPROVE"
    assert precheck["approvalStillAllowed"] is True
    assert precheck["blocking"] is False
    assert precheck["summary"]["evidenceReady"] is True
    assert precheck["summary"]["reviewDecisionNoteRecorded"] is True
    assert precheck["summary"]["approveReadyDecision"] is True
    assert precheck["summary"]["scorePreviewAvailable"] is True
    assert precheck["summary"]["scorePreviewStatus"] == "READY_FOR_HUMAN_SCORE_REVIEW"
    assert precheck["summary"]["scorePreviewEarnedScore"] == 100
    assert precheck["summary"]["scorePreviewReadyForDecisionNote"] is True
    assert precheck["summary"]["warningTotal"] == 0
    assert precheck["safety"]["autoApproveAllowed"] is False
    assert (
        approve_payload["data"]["operationAuditEvent"]["detail"]["preApproveReviewCheck"]["summary"]["latestDecision"]
        == "approve-ready"
    )


def test_grade_evidence_merge_rejects_missing_task_id(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "id": "report_missing_task",
                "mode": "READONLY_REAL_SANDBOX_POC",
                "checks": [{"id": "check_1", "status": "PASSED", "passed": True, "score": 1, "earnedScore": 1}],
                "safety": {"sandboxExecuted": True, "readonlyOnly": True},
            }
        ),
        encoding="utf-8",
    )

    exit_code, payload = run_cli(
        [
            "grade",
            "evidence-merge",
            "--report",
            str(report_path),
            "--output",
            str(tmp_path / "merged.json"),
            "--task-id",
            "task_missing",
        ],
        capsys,
    )

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"] == [{"field": "taskId", "reason": "未找到任务"}]


def test_grade_controlled_plan_builds_real_demo_executable_subset(tmp_path, capsys):
    plan_path = tmp_path / "mimo-real-demo-controlled-plan.json"

    exit_code, payload = run_cli(
        [
            "grade",
            "controlled-plan",
            "--grading",
            "examples/output/mimo-real-demo-grading.json",
            "--stdout-command",
            "python main.py",
            "--stdout-expected",
            "Python 3.11",
            "--pytest-path",
            "checks\\check_main.py",
            "--output",
            str(plan_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert plan_path.exists()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["kind"] == "Grading"
    assert plan["status"] == "WAITING_REVIEW"
    assert plan["metadata"]["id"] == "grading_real_llm_demo_controlled_docker_plan"
    assert plan["spec"]["totalScore"] == 40
    assert [check["id"] for check in plan["spec"]["checks"]] == ["check_q1", "check_q4"]
    assert plan["spec"]["checks"][0]["command"] == "python main.py"
    assert plan["spec"]["checks"][0]["expected"] == ["Python 3.11"]
    assert plan["spec"]["checks"][1]["path"] == "checks/check_main.py"
    assert [item["checkId"] for item in plan["spec"]["assessmentPlan"]] == ["check_q1", "check_q4"]
    assert payload["data"]["mode"] == "CONTROLLED_DOCKER_GRADING_PLAN"
    assert payload["data"]["summary"]["selectedCheckTotal"] == 2
    assert payload["data"]["summary"]["selectedCheckTypes"] == ["pytest", "stdout_contains"]
    assert payload["data"]["summary"]["deferredCheckTotal"] == 0
    assert payload["data"]["summary"]["deferredCheckTypes"] == []
    assert payload["data"]["summary"]["deferredScore"] == 0
    assert payload["data"]["summary"]["readonlyStaticCheckTotal"] == 2
    assert payload["data"]["summary"]["readonlyStaticCheckTypes"] == ["notebook_cell"]
    assert payload["data"]["summary"]["readonlyStaticScore"] == 60
    assert payload["data"]["summary"]["sourceTotalScore"] == 100
    assert payload["data"]["summary"]["executableScore"] == 40
    assert payload["data"]["summary"]["coveredByKnownExecutorsScore"] == 100
    assert payload["data"]["summary"]["uncoveredScore"] == 0
    assert payload["data"]["summary"]["patchTotal"] == 3
    assert payload["data"]["deferredChecks"] == []
    assert payload["data"]["executionCoverage"]["coverageRatio"] == 1.0
    assert payload["data"]["executionCoverage"]["allSourceChecksCoveredByAvailableExecutors"] is True
    assert payload["data"]["executionCoverage"]["controlledDocker"]["score"] == 40
    assert payload["data"]["executionCoverage"]["controlledDocker"]["checkIds"] == ["check_q1", "check_q4"]
    assert payload["data"]["executionCoverage"]["readonlyStatic"]["score"] == 60
    assert payload["data"]["executionCoverage"]["readonlyStatic"]["checkIds"] == ["check_q2", "check_q3"]
    assert payload["data"]["executionCoverage"]["deferred"]["score"] == 0
    assert payload["data"]["summary"]["waitingReview"] is True
    assert payload["data"]["safety"]["sandboxExecuted"] is False
    assert payload["data"]["safety"]["contestantCodeExecuted"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "CONTROLLED_GRADING_PLAN_BUILD"
    assert payload["data"]["operationAuditEvent"]["detail"]["reportType"] == "CONTROLLED_DOCKER_GRADING_PLAN"
    assert payload["data"]["operationAuditEvent"]["detail"]["summary"]["coveredByKnownExecutorsScore"] == 100
    assert payload["data"]["artifact"]["kind"] == "GRADING_DSL"
    assert payload["data"]["artifact"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["artifact"]["metadata"]["summary"]["coveredByKnownExecutorsScore"] == 100


def test_grade_controlled_plan_reports_mixed_executor_coverage(tmp_path, capsys):
    plan_path = tmp_path / "mixed-controlled-plan.json"

    exit_code, payload = run_cli(
        [
            "grade",
            "controlled-plan",
            "--grading",
            "templates/grading/examples/mixed-checks.yaml",
            "--output",
            str(plan_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["summary"]["executableScore"] == 50
    assert payload["data"]["summary"]["readonlyStaticScore"] == 50
    assert payload["data"]["summary"]["deferredScore"] == 0
    coverage = payload["data"]["executionCoverage"]
    assert coverage["sourceCheckTotal"] == 6
    assert coverage["sourceTotalScore"] == 100
    assert coverage["coveredByKnownExecutorsScore"] == 100
    assert coverage["uncoveredScore"] == 0
    assert coverage["coverageRatio"] == 1.0
    assert coverage["controlledDocker"]["checkIds"] == ["check_stdout_accuracy", "check_pytest"]
    assert coverage["controlledDocker"]["checkTypes"] == ["pytest", "stdout_contains"]
    assert coverage["readonlyStatic"]["checkIds"] == [
        "check_result_file",
        "check_notebook_accuracy",
        "check_metrics_json",
        "check_training_log",
    ]
    assert coverage["readonlyStatic"]["checkTypes"] == ["file_exists", "json_field", "log_keyword", "notebook_cell"]
    assert coverage["deferred"]["checkTotal"] == 0
    assert coverage["recommendedNextCommands"]["controlledDocker"].startswith("python lab_cli.py grade sandbox-run")


def test_grade_controlled_plan_normalizes_real_llm_expected_string(tmp_path, capsys):
    source = tmp_path / "real-llm-grading-string-expected.json"
    plan_path = tmp_path / "controlled-plan.json"
    source.write_text(
        json.dumps(
            {
                "version": "1.0",
                "kind": "Grading",
                "metadata": {"id": "grading_string_expected", "title": "String Expected"},
                "status": "WAITING_REVIEW",
                "spec": {
                    "totalScore": 100,
                    "timeoutSeconds": 30,
                    "checks": [
                        {
                            "id": "check_stdout",
                            "type": "stdout_contains",
                            "command": "python main.py",
                            "expected": "accuracy=0.90",
                            "score": 50,
                        },
                        {"id": "check_pytest", "type": "pytest", "path": "checks\\check_main.py", "score": 50},
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code, payload = run_cli(
        [
            "grade",
            "controlled-plan",
            "--grading",
            str(source),
            "--output",
            str(plan_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["spec"]["checks"][0]["expected"] == ["accuracy=0.90"]
    assert plan["spec"]["checks"][1]["path"] == "checks/check_main.py"
    assert payload["data"]["summary"]["selectedCheckTotal"] == 2
    assert payload["data"]["summary"]["deferredCheckTotal"] == 0
    assert payload["data"]["summary"]["patchTotal"] == 2
    assert payload["data"]["patches"] == [
        {
            "checkId": "check_stdout",
            "field": "expected",
            "value": ["accuracy=0.90"],
            "reason": "coerced_expected_string_to_array",
        },
        {
            "checkId": "check_pytest",
            "field": "path",
            "value": "checks/check_main.py",
            "reason": "normalized_path_separator",
        },
    ]


def test_grade_controlled_plan_rejects_absolute_pytest_path(tmp_path, capsys):
    exit_code, payload = run_cli(
        [
            "grade",
            "controlled-plan",
            "--grading",
            "examples/output/mimo-real-demo-grading.json",
            "--pytest-path",
            "C:\\temp\\check_main.py",
            "--output",
            str(tmp_path / "plan.json"),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "pytestPath"


def test_real_demo_controlled_plan_can_feed_controlled_sandbox_run(tmp_path, capsys, monkeypatch):
    plan_path = tmp_path / "mimo-real-demo-controlled-plan.json"
    report_path = tmp_path / "mimo-real-demo-controlled-report.json"

    run_cli(
        [
            "grade",
            "controlled-plan",
            "--grading",
            "examples/output/mimo-real-demo-grading.json",
            "--stdout-command",
            "python main.py",
            "--stdout-expected",
            "Python 3.11",
            "--pytest-path",
            "checks\\check_main.py",
            "--output",
            str(plan_path),
        ],
        capsys,
    )

    def fake_run(args, **kwargs):
        if args[:2] == ["docker", "info"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout='"29.5.3"', stderr="")
        if args[:3] == ["docker", "image", "inspect"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="sha256:demo", stderr="")
        if "main.py" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="Python 3.11 demo ready\n", stderr="")
        if "pytest" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="1 passed\n", stderr="")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_run)
    exit_code, payload = run_cli(
        [
            "grade",
            "sandbox-run",
            "--execution-mode",
            "controlled-command",
            "--grading",
            str(plan_path),
            "--submission",
            "examples/submissions/real-demo-controlled",
            "--image",
            "local-python:demo",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["gradingId"] == "grading_real_llm_demo_controlled_docker_plan"
    assert report["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert report["executionSummary"]["executed"] == 2
    assert report["executionSummary"]["passed"] == 2
    assert report["score"]["earnedScore"] == 40
    assert report["passed"] is True
    assert report["safety"]["contestantCodeExecuted"] is True
    assert report["safety"]["hostExecutionAllowed"] is False


def test_grade_sandbox_image_build_and_verify_return_json(tmp_path, capsys, monkeypatch):
    commands = []

    def fake_run(args, **kwargs):
        commands.append(args)
        if args[:2] == ["docker", "build"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="Successfully tagged ai-grading-python:0.1\n", stderr="")
        if args[:3] == ["docker", "image", "inspect"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="sha256:grading\n", stderr="")
        if args[:2] == ["docker", "run"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="pytest 9.0.2\n", stderr="")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr("cli.lab_cli.subprocess.run", fake_run)

    build_exit_code, build_payload = run_cli(["grade", "sandbox-image", "build"], capsys)
    assert build_exit_code == 0
    assert_json_envelope(build_payload)
    assert build_payload["data"]["mode"] == "CONTROLLED_DOCKER_SANDBOX_IMAGE_BUILD"
    assert build_payload["data"]["tag"] == "ai-grading-python:0.1"
    assert build_payload["data"]["imageBuilt"] is True
    assert build_payload["data"]["pushed"] is False
    assert build_payload["data"]["networkEnabledForGrading"] is False

    verify_path = tmp_path / "image-verify.json"
    verify_exit_code, verify_payload = run_cli(
        ["grade", "sandbox-image", "verify", "--output", str(verify_path)],
        capsys,
    )
    assert verify_exit_code == 0
    assert_json_envelope(verify_payload)
    assert verify_path.exists()
    verification = json.loads(verify_path.read_text(encoding="utf-8"))
    assert verification["mode"] == "CONTROLLED_DOCKER_SANDBOX_IMAGE_VERIFY"
    assert verify_payload["data"]["pytestAvailable"] is True
    assert verify_payload["data"]["imageMetadata"]["rebuildRequired"] is True
    assert verify_payload["data"]["stdout"] == "pytest 9.0.2"
    assert any(command[:2] == ["docker", "build"] for command in commands)
    assert any(command[:2] == ["docker", "run"] and "--network" in command and "none" in command for command in commands)


def write_minimal_real_demo_workflow_report(path: Path) -> None:
    generated = {}
    for kind, output_kind, dsl_id, dsl_path in (
        ("lab", "Lab", "lab_demo", "templates/lab/examples/basic-lab.yaml"),
        ("exam", "Exam", "exam_demo", "templates/exam/examples/notebook-fill-blank.yaml"),
        ("grading", "Grading", "grading_readonly_sandbox_demo", "templates/grading/examples/readonly-sandbox.yaml"),
        ("ppt", "PPT", "ppt_demo", "templates/ppt/examples/course-ppt.yaml"),
    ):
        generated[kind] = {
            "kind": kind,
            "outputKind": output_kind,
            "promptId": f"{kind}_generation_v0",
            "dslId": dsl_id,
            "dslPath": dsl_path,
            "status": "WAITING_REVIEW",
            "reviewRequired": True,
            "publishBlockedUntilApproved": True,
            "schemaValidated": True,
            "provider": {
                "adapterId": "openai_responses_sdk_demo_adapter",
                "providerId": "openai",
                "mode": "REAL_LLM_DEMO_DSL_GENERATION",
                "model": "test-model",
                "realLlmCalled": True,
                "networkAccess": True,
                "requestCount": 1,
                "responseId": f"resp_{kind}",
                "providerCallAuditEventId": f"provider_audit_{kind}",
            },
        }
    path.write_text(
        json.dumps(
            {
                "id": "phase2_report_test_real_demo",
                "workflowId": "phase2_content_generation",
                "phase": "Phase 2",
                "mode": "REAL_LLM_DEMO_WORKFLOW",
                "providerMode": "real-llm-demo",
                "providerAdapter": "openai_responses_sdk_demo_adapter",
                "input": "examples/input/demo-source.md",
                "reviewer": "teacher_1",
                "labGenerationContext": {
                    "targetUsers": ["高职学生"],
                    "durationMinutes": 60,
                    "difficulty": "beginner",
                    "techTags": ["AI"],
                    "teachingStyle": "guided_practice",
                },
                "qualitySignals": {"overall": {"reviewRequired": True}, "reviewHighlights": []},
                "generatedDsl": generated,
                "safety": {
                    "realLlmCalled": True,
                    "secretsRead": True,
                    "networkAccess": True,
                    "realLlmGeneratedKinds": ["lab", "exam", "grading", "ppt"],
                    "realLlmRequestCount": 4,
                    "realAgentStarted": False,
                    "realCloudResourceCreated": False,
                    "realCloudResourceChanged": False,
                    "sandboxExecuted": False,
                    "contestantCodeExecuted": False,
                    "unknownShellExecuted": False,
                    "autoPublishAllowed": False,
                    "realPublish": False,
                    "reviewBypassed": False,
                },
                "traceId": "trace_real_demo_test",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


@requires_presentations_runtime
def test_phase2_demo_bundle_build_replays_real_outputs_and_runs_readonly_sandbox(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    workflow_report = tmp_path / "real-demo-workflow-report.json"
    output = tmp_path / "real-demo-bundle.json"
    normalized = tmp_path / "normalized-grading.json"
    precheck = tmp_path / "precheck.json"
    readonly = tmp_path / "readonly-report.json"
    evidence_grading = tmp_path / "readonly-evidence-grading.json"
    evidence_report = tmp_path / "readonly-evidence-report.json"
    preview = tmp_path / "candidate-preview.json"
    pptx = tmp_path / "real-demo-ppt-artifact.pptx"
    pptx_manifest = tmp_path / "real-demo-ppt-artifact-manifest.json"
    pptx_preview = tmp_path / "real-demo-ppt-artifact-slide-01.png"
    pptx_preview_dir = tmp_path / "real-demo-ppt-artifact-slides"
    pptx_contact_sheet = tmp_path / "real-demo-ppt-artifact-contact-sheet.png"
    write_minimal_real_demo_workflow_report(workflow_report)

    exit_code, payload = run_cli(
        [
            "phase2",
            "demo-bundle",
            "build",
            "--workflow-report",
            str(workflow_report),
            "--lab",
            "templates/lab/examples/basic-lab.yaml",
            "--exam",
            "templates/exam/examples/notebook-fill-blank.yaml",
            "--grading",
            "templates/grading/examples/readonly-sandbox.yaml",
            "--ppt",
            "templates/ppt/examples/course-ppt.yaml",
            "--submission",
            "examples/submissions/readonly-demo",
            "--normalized-grading-output",
            str(normalized),
            "--precheck-output",
            str(precheck),
            "--readonly-report-output",
            str(readonly),
            "--readonly-evidence-grading-output",
            str(evidence_grading),
            "--readonly-evidence-report-output",
            str(evidence_report),
            "--candidate-preview-output",
            str(preview),
            "--pptx-output",
            str(pptx),
            "--pptx-manifest-output",
            str(pptx_manifest),
            "--pptx-preview-output",
            str(pptx_preview),
            "--pptx-preview-dir",
            str(pptx_preview_dir),
            "--pptx-contact-sheet-output",
            str(pptx_contact_sheet),
            "--output",
            str(output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output.exists()
    assert normalized.exists()
    assert precheck.exists()
    assert readonly.exists()
    assert evidence_grading.exists()
    assert evidence_report.exists()
    assert preview.exists()
    assert pptx.exists()
    assert pptx_manifest.exists()
    assert pptx_preview.exists()
    assert pptx_preview.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert (pptx_preview_dir / "slide-01.png").exists()
    assert (pptx_preview_dir / "slide-02.png").exists()
    assert pptx_contact_sheet.exists()
    assert pptx_contact_sheet.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert zipfile.is_zipfile(pptx)
    with zipfile.ZipFile(pptx) as package:
        names = set(package.namelist())
    assert "ppt/presentation.xml" in names
    assert "ppt/slides/slide1.xml" in names
    bundle = json.loads(output.read_text(encoding="utf-8"))
    assert bundle["mode"] == "REAL_LLM_DEMO_REPLAY_AND_READONLY_SANDBOX_BUNDLE"
    assert bundle["generatedDsl"]["lab"]["status"] == "WAITING_REVIEW"
    assert bundle["generatedDsl"]["exam"]["answerVisibleToCandidate"] is False
    assert bundle["candidatePreview"]["answersRemoved"] is True
    assert bundle["candidatePreview"]["answerVisibleToCandidate"] is False
    assert bundle["sandboxPrecheck"]["readiness"]["status"] == "READY_FOR_MANUAL_SANDBOX_REVIEW"
    assert bundle["readonlySandbox"]["executionSummary"]["executed"] == 4
    assert bundle["readonlySandbox"]["executionSummary"]["deferred"] == 1
    assert bundle["readonlySandbox"]["score"]["earnedScore"] == 120
    readonly_report = json.loads(readonly.read_text(encoding="utf-8"))
    assert readonly_report["reportDetail"]["source"] == "sandbox.grade_runner.build_grading_report_detail"
    assert readonly_report["reportDetail"]["checkSummary"]["executed"] == 4
    assert readonly_report["reportDetail"]["checkPlans"][0]["readonlyEvidence"]["status"] == "COLLECTED"
    assert bundle["readonlyEvidenceDemo"]["doesNotModifySourceGrading"] is True
    assert bundle["readonlyEvidenceDemo"]["executionSummary"]["executed"] == 2
    assert bundle["readonlyEvidenceDemo"]["executionSummary"]["deferred"] == 0
    assert bundle["readonlyEvidenceDemo"]["score"]["earnedScore"] == 70
    assert bundle["readonlyEvidenceDemo"]["safety"]["contestantCodeExecuted"] is False
    readonly_evidence_report = json.loads(evidence_report.read_text(encoding="utf-8"))
    assert readonly_evidence_report["reportDetail"]["source"] == "sandbox.grade_runner.build_grading_report_detail"
    assert readonly_evidence_report["reportDetail"]["checkSummary"]["executed"] == 2
    assert readonly_evidence_report["reportDetail"]["checkPlans"][0]["readonlyEvidence"]["status"] == "COLLECTED"
    assert bundle["generatedDsl"]["ppt"]["artifactGenerated"] is True
    assert bundle["generatedDsl"]["ppt"]["pptxPath"] == str(pptx)
    assert bundle["generatedDsl"]["ppt"]["pptxPreviewPath"] == str(pptx_preview)
    assert bundle["generatedDsl"]["ppt"]["pptxPreviewDir"] == str(pptx_preview_dir)
    assert bundle["generatedDsl"]["ppt"]["pptxContactSheetPath"] == str(pptx_contact_sheet)
    assert bundle["generatedDsl"]["ppt"]["pptxPreviewAvailable"] is True
    assert bundle["generatedDsl"]["ppt"]["slidePreviewCount"] == 2
    assert bundle["generatedDsl"]["ppt"]["firstSlidePreview"]["title"] == "AI 工具应用课程"
    assert bundle["pptArtifact"]["kind"] == "PPTX_FILE"
    assert bundle["pptArtifact"]["status"] == "WAITING_REVIEW"
    assert bundle["pptArtifact"]["qualityReport"]["status"] == "PASS"
    assert bundle["pptArtifact"]["qualityReport"]["issueTotal"] == 0
    assert bundle["pptArtifact"]["path"] == str(pptx)
    assert bundle["pptArtifact"]["manifestPath"] == str(pptx_manifest)
    assert bundle["pptArtifact"]["previewPath"] == str(pptx_preview)
    assert bundle["pptArtifact"]["previewDir"] == str(pptx_preview_dir)
    assert bundle["pptArtifact"]["contactSheetPath"] == str(pptx_contact_sheet)
    assert bundle["pptArtifact"]["slideCount"] == 2
    assert bundle["pptArtifact"]["previewAvailable"] is True
    assert bundle["pptArtifact"]["preview"]["renderAttempted"] is True
    assert bundle["pptArtifact"]["preview"]["reason"] == "PREVIEW_RENDERED"
    assert len(bundle["pptArtifact"]["slidePreviews"]) == 2
    assert bundle["pptArtifact"]["contactSheet"]["path"] == str(pptx_contact_sheet)
    assert bundle["pptArtifact"]["firstSlidePreview"]["imagePath"] == str(pptx_preview)
    assert bundle["pptArtifact"]["firstSlidePreview"]["title"] == "AI 工具应用课程"
    assert bundle["pptArtifact"]["autoPublishAllowed"] is False
    assert bundle["pptArtifact"]["realPublish"] is False
    assert bundle["acceptanceSignals"]["readonlyEvidenceDemoExecuted"] is True
    assert bundle["acceptanceSignals"]["readonlyEvidenceDemoEarnedScore"] == 70
    assert bundle["acceptanceSignals"]["pptxArtifactGenerated"] is True
    assert bundle["acceptanceSignals"]["pptxArtifactWaitingReview"] is True
    assert bundle["safety"]["realLlmCalled"] is True
    assert bundle["safety"]["newLlmRequestSent"] is False
    assert bundle["safety"]["secretsRead"] is False
    assert bundle["safety"]["pptxArtifactGenerated"] is True
    assert bundle["safety"]["pptxArtifactAutoPublishAllowed"] is False
    assert bundle["safety"]["contestantCodeExecuted"] is False
    assert payload["data"]["workflowRun"]["workflowId"] == "phase2_real_llm_demo_bundle"
    assert payload["data"]["artifact"]["kind"] == "WORKFLOW_REPORT"
    assert payload["data"]["artifact"]["metadata"]["pptArtifact"]["kind"] == "PPTX_FILE"
    assert payload["data"]["artifact"]["metadata"]["pptArtifact"]["previewAvailable"] is True
    assert payload["data"]["artifact"]["metadata"]["readonlyEvidenceDemo"]["doesNotModifySourceGrading"] is True
    assert payload["data"]["summary"]["acceptanceSignals"]["candidatePreviewAnswerSafe"] is True
    assert payload["data"]["summary"]["pptArtifact"]["path"] == str(pptx)
    assert payload["data"]["summary"]["readonlyEvidenceDemo"]["doesNotModifySourceGrading"] is True


def test_phase2_real_dsl_demo_verify_summarizes_local_outputs(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    workflow_report = tmp_path / "real-demo-workflow-report.json"
    output = tmp_path / "real-demo-local-verification.json"
    write_minimal_real_demo_workflow_report(workflow_report)

    exit_code, payload = run_cli(
        [
            "phase2",
            "real-dsl-demo",
            "verify",
            "--workflow-report",
            str(workflow_report),
            "--lab",
            "templates/lab/examples/basic-lab.yaml",
            "--exam",
            "templates/exam/examples/notebook-fill-blank.yaml",
            "--grading",
            "templates/grading/examples/readonly-sandbox.yaml",
            "--ppt",
            "templates/ppt/examples/course-ppt.yaml",
            "--output",
            str(output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    verification = payload["data"]["verification"]
    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8")) == verification
    assert verification["mode"] == "REAL_LLM_DEMO_LOCAL_VERIFICATION"
    assert verification["schemaValidated"] is True
    assert verification["readyForHumanReview"] is True
    assert set(verification["waitingReviewKinds"]) == {"lab", "exam", "grading", "ppt"}
    assert set(verification["readyForImportPreviewKinds"]) == {"lab", "exam", "grading"}
    assert verification["blockerTotal"] == 0
    assert verification["items"]["lab"]["stepCount"] >= 1
    assert verification["items"]["exam"]["questionCount"] >= 1
    assert verification["items"]["grading"]["checkCount"] >= 1
    assert verification["items"]["ppt"]["slideCount"] >= 1
    assert verification["safety"]["readOnly"] is True
    assert verification["safety"]["realLlmCalled"] is False
    assert verification["safety"]["taskCreated"] is False
    assert verification["safety"]["realPublish"] is False
    assert payload["data"]["summary"]["nextRecommendedAction"] == "open_review_detail_and_continue_import_preview"


def test_phase2_demo_bundle_missing_workflow_report_returns_json(tmp_path, capsys):
    exit_code, payload = run_cli(
        [
            "phase2",
            "demo-bundle",
            "build",
            "--workflow-report",
            str(tmp_path / "missing.json"),
            "--output",
            str(tmp_path / "bundle.json"),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "workflow-report"


@requires_presentations_runtime
def test_phase2_demo_bundle_acceptance_returns_closed_loop_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    workflow_report = tmp_path / "real-demo-workflow-report.json"
    bundle_output = tmp_path / "real-demo-bundle.json"
    acceptance_output = tmp_path / "real-demo-acceptance-summary.json"
    write_minimal_real_demo_workflow_report(workflow_report)
    build_exit, _ = run_cli(
        [
            "phase2",
            "demo-bundle",
            "build",
            "--workflow-report",
            str(workflow_report),
            "--lab",
            "templates/lab/examples/basic-lab.yaml",
            "--exam",
            "templates/exam/examples/notebook-fill-blank.yaml",
            "--grading",
            "templates/grading/examples/readonly-sandbox.yaml",
            "--ppt",
            "templates/ppt/examples/course-ppt.yaml",
            "--submission",
            "examples/submissions/readonly-demo",
            "--normalized-grading-output",
            str(tmp_path / "normalized-grading.json"),
            "--precheck-output",
            str(tmp_path / "precheck.json"),
            "--readonly-report-output",
            str(tmp_path / "readonly-report.json"),
            "--readonly-evidence-grading-output",
            str(tmp_path / "readonly-evidence-grading.json"),
            "--readonly-evidence-report-output",
            str(tmp_path / "readonly-evidence-report.json"),
            "--candidate-preview-output",
            str(tmp_path / "candidate-preview.json"),
            "--pptx-output",
            str(tmp_path / "real-demo-ppt-artifact.pptx"),
            "--pptx-manifest-output",
            str(tmp_path / "real-demo-ppt-artifact-manifest.json"),
            "--pptx-preview-output",
            str(tmp_path / "real-demo-ppt-artifact-slide-01.png"),
            "--pptx-preview-dir",
            str(tmp_path / "real-demo-ppt-artifact-slides"),
            "--pptx-contact-sheet-output",
            str(tmp_path / "real-demo-ppt-artifact-contact-sheet.png"),
            "--output",
            str(bundle_output),
        ],
        capsys,
    )

    exit_code, payload = run_cli(
        [
            "phase2",
            "demo-bundle",
            "acceptance",
            "--bundle",
            str(bundle_output),
            "--output",
            str(acceptance_output),
        ],
        capsys,
    )

    assert build_exit == 0
    assert exit_code == 0
    assert_json_envelope(payload)
    assert acceptance_output.exists()
    summary = payload["data"]["acceptanceSummary"]
    saved = json.loads(acceptance_output.read_text(encoding="utf-8"))
    assert saved == summary
    assert payload["data"]["summary"]["passed"] is True
    assert summary["mode"] == "REAL_LLM_DEMO_ACCEPTANCE_STATIC"
    assert summary["route"] == "/real-demo -> /review-center -> /ppt/:id/review -> /grading/:id/report"
    assert summary["signals"]["dslValidatedTotal"] == 4
    assert summary["signals"]["waitingReviewDslTotal"] == 4
    assert summary["signals"]["realDemoReviewQueueTaskTotal"] == 4
    assert summary["signals"]["mcpOutputContractIncludesRealDemoReviewQueue"] is True
    assert summary["signals"]["readonlyEvidenceCollectedTotal"] == 2
    assert summary["signals"]["readonlyEvidenceDemoEarnedScore"] == 70
    assert summary["signals"]["controlledDockerEvidenceEarnedScore"] == 40
    assert summary["signals"]["notebookStaticEvidenceEarnedScore"] == 60
    assert summary["signals"]["gradingEvidenceCoverageEarnedScore"] == 100
    assert summary["signals"]["gradingEvidenceCoverageTotalScore"] == 100
    assert summary["signals"]["gradingEvidenceCoverageStatus"] == "GRADING_EVIDENCE_COVERAGE_COMPLETE"
    assert summary["gradingEvidenceCoverage"]["earnedScore"] == 100
    assert summary["gradingEvidenceCoverage"]["totalScore"] == 100
    assert summary["gradingEvidenceCoverage"]["manualReviewRequired"] is True
    assert summary["gradingEvidenceCoverage"]["autoApproveAllowed"] is False
    assert summary["signals"]["pptPageReviewActionVisible"] is True
    assert summary["signals"]["candidatePreviewAnswerSafe"] is True
    assert summary["safety"]["newLlmRequestSent"] is False
    assert summary["safety"]["secretsRead"] is False
    assert summary["safety"]["networkAccess"] is False
    assert summary["safety"]["autoApproveAllowed"] is False
    assert summary["safety"]["batchStateChangeAllowed"] is False
    assert summary["safety"]["realPublishAllowed"] is False
    assert summary["acceptance"]["passed"] is True
    assert summary["acceptance"]["passedCount"] == summary["acceptance"]["total"] == 7
    assert [step["id"] for step in summary["steps"]] == [
        "real_demo_bundle_valid",
        "real_demo_page_visible",
        "review_center_real_demo_queue_visible",
        "mcp_get_review_task_summary_contract_visible",
        "grading_report_readonly_report_detail_visible",
        "grading_evidence_coverage_complete",
        "ppt_artifact_review_action_visible",
    ]


def test_phase2_demo_bundle_acceptance_missing_bundle_returns_json(tmp_path, capsys):
    output = tmp_path / "real-demo-acceptance-summary.json"

    exit_code, payload = run_cli(
        ["phase2", "demo-bundle", "acceptance", "--bundle", str(tmp_path / "missing.json"), "--output", str(output)],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "bundle"
    assert not output.exists()


@requires_presentations_runtime
def test_phase2_demo_bundle_checklist_returns_one_click_demo_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    workflow_report = tmp_path / "real-demo-workflow-report.json"
    bundle_output = tmp_path / "real-demo-bundle.json"
    acceptance_output = tmp_path / "real-demo-acceptance-summary.json"
    checklist_output = tmp_path / "real-demo-checklist.json"
    write_minimal_real_demo_workflow_report(workflow_report)
    run_cli(
        [
            "phase2",
            "demo-bundle",
            "build",
            "--workflow-report",
            str(workflow_report),
            "--lab",
            "templates/lab/examples/basic-lab.yaml",
            "--exam",
            "templates/exam/examples/notebook-fill-blank.yaml",
            "--grading",
            "templates/grading/examples/readonly-sandbox.yaml",
            "--ppt",
            "templates/ppt/examples/course-ppt.yaml",
            "--submission",
            "examples/submissions/readonly-demo",
            "--normalized-grading-output",
            str(tmp_path / "normalized-grading.json"),
            "--precheck-output",
            str(tmp_path / "precheck.json"),
            "--readonly-report-output",
            str(tmp_path / "readonly-report.json"),
            "--readonly-evidence-grading-output",
            str(tmp_path / "readonly-evidence-grading.json"),
            "--readonly-evidence-report-output",
            str(tmp_path / "readonly-evidence-report.json"),
            "--candidate-preview-output",
            str(tmp_path / "candidate-preview.json"),
            "--pptx-output",
            str(tmp_path / "real-demo-ppt-artifact.pptx"),
            "--pptx-manifest-output",
            str(tmp_path / "real-demo-ppt-artifact-manifest.json"),
            "--pptx-preview-output",
            str(tmp_path / "real-demo-ppt-artifact-slide-01.png"),
            "--pptx-preview-dir",
            str(tmp_path / "real-demo-ppt-artifact-slides"),
            "--pptx-contact-sheet-output",
            str(tmp_path / "real-demo-ppt-artifact-contact-sheet.png"),
            "--output",
            str(bundle_output),
        ],
        capsys,
    )
    run_cli(
        [
            "phase2",
            "demo-bundle",
            "acceptance",
            "--bundle",
            str(bundle_output),
            "--output",
            str(acceptance_output),
        ],
        capsys,
    )

    exit_code, payload = run_cli(
        [
            "phase2",
            "demo-bundle",
            "checklist",
            "--bundle",
            str(bundle_output),
            "--acceptance-summary",
            str(acceptance_output),
            "--output",
            str(checklist_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert checklist_output.exists()
    checklist = payload["data"]["demoChecklist"]
    saved = json.loads(checklist_output.read_text(encoding="utf-8"))
    assert saved == checklist
    assert checklist["component"] == "RealDemoOneClickChecklist"
    assert checklist["mode"] == "REAL_LLM_DEMO_CHECKLIST_STATIC"
    assert checklist["summary"]["readyForDemo"] is True
    assert checklist["summary"]["acceptancePassed"] is True
    assert checklist["summary"]["acceptancePassedCount"] == 7
    assert checklist["summary"]["acceptanceTotal"] == 7
    assert checklist["summary"]["sectionPassedCount"] == checklist["summary"]["sectionTotal"] == 6
    assert checklist["summary"]["gradingEvidenceCoverageEarnedScore"] == 100
    assert checklist["summary"]["gradingEvidenceCoverageTotalScore"] == 100
    assert [section["id"] for section in checklist["sections"]] == [
        "generated_dsl",
        "candidate_preview",
        "grading_evidence_coverage",
        "pptx_artifact",
        "review_and_mcp",
        "safety_boundaries",
    ]
    assert all(section["passed"] is True for section in checklist["sections"])
    assert checklist["sections"][2]["evidence"]["controlledDockerScore"] == 40
    assert checklist["sections"][2]["evidence"]["notebookStaticScore"] == 60
    assert checklist["safety"]["newLlmRequestSent"] is False
    assert checklist["safety"]["secretsRead"] is False
    assert checklist["safety"]["sandboxExecutedByChecklist"] is False
    assert checklist["safety"]["commandExecutedByChecklist"] is False
    assert checklist["safety"]["notebookExecutedByChecklist"] is False
    assert checklist["safety"]["realPublishAllowed"] is False
    assert checklist["sections"][0]["command"].endswith(str(bundle_output))
    assert checklist["safeCommands"][0].endswith(str(bundle_output))
    assert str(acceptance_output) in checklist["safeCommands"][1]
    assert "python lab_cli.py phase2 demo-bundle checklist" in checklist["safeCommands"][2]
    assert str(bundle_output) in checklist["safeCommands"][2]
    assert str(acceptance_output) in checklist["safeCommands"][2]
    assert str(checklist_output) in checklist["safeCommands"][2]
    assert payload["data"]["summary"]["readyForDemo"] is True
    assert payload["data"]["outputPath"] == str(checklist_output)


def test_phase2_demo_bundle_checklist_missing_acceptance_summary_returns_json(tmp_path, capsys):
    output = tmp_path / "real-demo-checklist.json"

    exit_code, payload = run_cli(
        [
            "phase2",
            "demo-bundle",
            "checklist",
            "--bundle",
            "examples/output/real-llm-demo-bundle.json",
            "--acceptance-summary",
            str(tmp_path / "missing-acceptance.json"),
            "--output",
            str(output),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "acceptanceSummary"
    assert not output.exists()


@requires_presentations_runtime
def test_phase2_real_dsl_demo_one_click_runs_close_loop_and_entry_routes(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    real_subprocess_run = subprocess.run

    def fake_controlled_run_with_pptx_builder_passthrough(args, **kwargs):
        if args and str(args[0]).lower().endswith("node.exe"):
            return real_subprocess_run(args, **kwargs)
        return fake_controlled_docker_run(args, **kwargs)

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_run_with_pptx_builder_passthrough)
    workflow_report = tmp_path / "real-demo-workflow-report.json"
    one_click_output = tmp_path / "real-demo-one-click.json"
    close_loop_output = tmp_path / "real-demo-close-loop.json"
    controlled_report = tmp_path / "real-demo-controlled-report.json"
    controlled_submission = tmp_path / "controlled-submission"
    controlled_submission.mkdir()
    (controlled_submission / "main.py").write_text("print('accuracy=0.90')\n", encoding="utf-8")
    (controlled_submission / "tests").mkdir()
    (controlled_submission / "tests" / "test_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (controlled_submission / "checks").mkdir()
    (controlled_submission / "checks" / "check_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    write_minimal_real_demo_workflow_report(workflow_report)

    exit_code, payload = run_cli(
        [
            "phase2",
            "real-dsl-demo",
            "one-click",
            "--workflow-report",
            str(workflow_report),
            "--input",
            "examples/input/demo-source.md",
            "--lab",
            "templates/lab/examples/basic-lab.yaml",
            "--exam",
            "templates/exam/examples/notebook-fill-blank.yaml",
            "--grading",
            "templates/grading/examples/readonly-sandbox.yaml",
            "--ppt",
            "templates/ppt/examples/course-ppt.yaml",
            "--submission",
            "examples/submissions/readonly-demo",
            "--verification-output",
            str(tmp_path / "real-demo-local-verification.json"),
            "--normalized-grading-output",
            str(tmp_path / "normalized-grading.json"),
            "--precheck-output",
            str(tmp_path / "precheck.json"),
            "--readonly-report-output",
            str(tmp_path / "readonly-report.json"),
            "--readonly-evidence-grading-output",
            str(tmp_path / "readonly-evidence-grading.json"),
            "--readonly-evidence-report-output",
            str(tmp_path / "readonly-evidence-report.json"),
            "--candidate-preview-output",
            str(tmp_path / "candidate-preview.json"),
            "--pptx-output",
            str(tmp_path / "real-demo-ppt-artifact.pptx"),
            "--pptx-manifest-output",
            str(tmp_path / "real-demo-ppt-artifact-manifest.json"),
            "--pptx-preview-output",
            str(tmp_path / "real-demo-ppt-artifact-slide-01.png"),
            "--pptx-preview-dir",
            str(tmp_path / "real-demo-ppt-artifact-slides"),
            "--pptx-contact-sheet-output",
            str(tmp_path / "real-demo-ppt-artifact-contact-sheet.png"),
            "--bundle-output",
            str(tmp_path / "real-demo-bundle.json"),
            "--acceptance-output",
            str(tmp_path / "real-demo-acceptance-summary.json"),
            "--checklist-output",
            str(tmp_path / "real-demo-checklist.json"),
            "--close-loop-output",
            str(close_loop_output),
            "--run-close-loop",
            "--lab-import-output",
            str(tmp_path / "lab-template-import-preview.json"),
            "--exam-import-output",
            str(tmp_path / "exam-question-import-preview.json"),
            "--grading-import-output",
            str(tmp_path / "grading-rule-import-preview.json"),
            "--create-mock-imports",
            "--lab-mock-import-output",
            str(tmp_path / "lab-template-mock-import.json"),
            "--exam-mock-import-output",
            str(tmp_path / "exam-question-mock-import.json"),
            "--grading-mock-import-output",
            str(tmp_path / "grading-rule-mock-import.json"),
            "--controlled-submission",
            str(controlled_submission),
            "--controlled-plan-output",
            str(tmp_path / "real-demo-controlled-plan.json"),
            "--controlled-report-output",
            str(controlled_report),
            "--controlled-image",
            "local-python:demo",
            "--controlled-stdout-command",
            "python main.py",
            "--controlled-stdout-expected",
            "accuracy=0.90",
            "--controlled-pytest-path",
            "checks/check_main.py",
            "--confirm-lab-review-approved",
            "--confirm-exam-review-approved",
            "--confirm-grading-review-approved",
            "--output",
            str(one_click_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert one_click_output.exists()
    assert close_loop_output.exists()
    one_click = payload["data"]["oneClick"]
    close_loop = one_click["closeLoopSummary"]
    routes = one_click["entryRoutes"]
    assert json.loads(one_click_output.read_text(encoding="utf-8")) == one_click
    assert one_click["summary"]["closeLoopExecuted"] is True
    assert one_click["summary"]["closeLoopReadyForDemo"] is True
    assert one_click["summary"]["reviewCenterRouteAvailable"] is True
    assert one_click["summary"]["agentEntitiesRouteAvailable"] is True
    assert one_click["summary"]["gradingReportRouteAvailable"] is True
    assert close_loop["approvedImportableTaskTotal"] == 3
    assert close_loop["pptWaitingReview"] is True
    assert one_click["entryRoutes"]["agentEntityIds"].keys() == {"lab", "exam", "grading"}
    assert "ppt" not in one_click["entryRoutes"]["agentEntityIds"]
    assert one_click["safety"]["newLlmRequestSent"] is False
    assert one_click["safety"]["secretsRead"] is False
    assert one_click["safety"]["realPublish"] is False
    assert routes["summary"]["closeLoopExecuted"] is True
    assert routes["summary"]["reviewCenterRouteAvailable"] is True
    assert routes["summary"]["agentEntitiesRouteAvailable"] is True
    assert routes["summary"]["gradingReportRouteAvailable"] is True
    assert routes["reviewCenter"].startswith("review-center.html?taskId=")
    assert routes["agentEntities"].startswith("agent-entities.html?entityId=")
    assert "entityKind=lab" in routes["agentEntities"]
    assert routes["gradingReport"].startswith("grading-report.html?file=")
    assert "real-demo-controlled-report.json" in routes["gradingReport"]
    assert "taskId=task_" in routes["gradingReport"]
    assert routes["outputFiles"]["closeLoop"] == str(close_loop_output)
    assert routes["outputFiles"]["controlledGradingReport"] == str(controlled_report)
    saved_close_loop = json.loads(close_loop_output.read_text(encoding="utf-8"))
    assert saved_close_loop["agentEntityReadinessScope"]["agentEntities"] == [
        "exam_question",
        "grading_rule",
        "lab_template",
    ]
    assert saved_close_loop["agentEntityReadinessScope"]["pptDeckIncluded"] is False
    assert saved_close_loop["summary"]["allPlatformEntitiesReadyForManualReview"] is True
    assert saved_close_loop["summary"]["controlledGradingEvidenceEnabled"] is True
    assert saved_close_loop["summary"]["controlledGradingReportCreated"] is True
    assert saved_close_loop["reviewDetails"]["ppt"]["task"]["status"] == "WAITING_REVIEW"


def test_grade_normalize_repairs_real_llm_demo_grading_for_precheck(tmp_path, capsys):
    exam_path = tmp_path / "exam.json"
    grading_path = tmp_path / "grading.json"
    output_path = tmp_path / "normalized-grading.json"
    exam_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "kind": "Exam",
                "metadata": {
                    "id": "exam-real-demo-cli-test",
                    "title": "真实 Demo CLI 试题",
                    "sourceLabId": "lab-real-demo-cli-test",
                    "difficulty": "beginner",
                },
                "status": "WAITING_REVIEW",
                "spec": {
                    "questionType": "coding_task",
                    "totalScore": 100,
                    "questions": [
                        {"id": "q1", "title": "输出检查", "stem": "输出结果", "score": 40, "gradingRef": "expected stdout token"},
                        {"id": "q2", "title": "Notebook", "stem": "运行单元", "score": 60, "gradingRef": "expected notebook token"},
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    grading_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "kind": "Grading",
                "metadata": {
                    "id": "grading-real-demo-cli-test",
                    "title": "真实 Demo CLI 评分",
                    "sourceExamId": "exam-real-demo-cli-test",
                },
                "status": "WAITING_REVIEW",
                "spec": {
                    "totalScore": 100,
                    "timeoutSeconds": 30,
                    "checks": [
                        {"id": "check_q1", "type": "stdout_contains", "score": 1},
                        {"id": "check_q2", "type": "notebook_cell", "score": 1, "notebookPath": "demo.ipynb"},
                    ],
                    "assessmentPlan": [
                        {
                            "checkId": "check_q1",
                            "type": "stdout_contains",
                            "runner": "StdoutContainsGrader",
                            "score": 1,
                            "inputSummary": "incomplete",
                            "executionPlan": {
                                "strategy": "MOCK_PLAN_ONLY",
                                "requiredLimits": {
                                    "cpu": "required",
                                    "memory": "required",
                                    "timeout": "30s",
                                    "network": "disabled_by_default",
                                    "filesystem": "isolated_workspace_required",
                                    "process": "limited",
                                },
                                "wouldRunInsideRealSandbox": True,
                            },
                            "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
                            "riskLevel": "medium",
                            "sandboxRequiredBeforeRealExecution": True,
                        },
                        {
                            "checkId": "check_q2",
                            "type": "notebook_cell",
                            "runner": "NotebookGrader",
                            "score": 1,
                            "inputSummary": "incomplete",
                            "executionPlan": {
                                "strategy": "MOCK_PLAN_ONLY",
                                "requiredLimits": {
                                    "cpu": "required",
                                    "memory": "required",
                                    "timeout": "30s",
                                    "network": "disabled_by_default",
                                    "filesystem": "isolated_workspace_required",
                                    "process": "limited",
                                },
                                "wouldRunInsideRealSandbox": True,
                            },
                            "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
                            "riskLevel": "high",
                            "sandboxRequiredBeforeRealExecution": True,
                        },
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code, payload = run_cli(
        [
            "grade",
            "normalize",
            "--grading",
            str(grading_path),
            "--exam",
            str(exam_path),
            "--output",
            str(output_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output_path.exists()
    normalized = json.loads(output_path.read_text(encoding="utf-8"))
    checks = {check["id"]: check for check in normalized["spec"]["checks"]}
    assert payload["data"]["mode"] == "REAL_LLM_DEMO_DSL_NORMALIZATION"
    assert payload["data"]["normalization"]["applied"] is True
    assert checks["check_q1"]["command"] == "python main.py"
    assert checks["check_q1"]["expected"] == ["expected stdout token"]
    assert checks["check_q1"]["score"] == 40
    assert checks["check_q2"]["cellIndex"] == 0
    assert checks["check_q2"]["expected"] == ["expected notebook token"]
    assert checks["check_q2"]["score"] == 60
    assert payload["data"]["precheckSummary"]["status"] == "READY_FOR_MANUAL_SANDBOX_REVIEW"
    assert payload["data"]["precheckSummary"]["blockerCount"] == 0
    assert payload["data"]["precheckSummary"]["sandboxExecuted"] is False
    assert payload["data"]["artifact"]["kind"] == "GRADING_DSL"
    assert payload["data"]["artifact"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["artifact"]["metadata"]["sandboxRequiredBeforeRealExecution"] is True


def test_grade_sandbox_precheck_schema_error_returns_json(tmp_path, capsys):
    bad_grading = tmp_path / "bad-grading.yaml"
    bad_grading.write_text(
        "\n".join(
            [
                'version: "1.0"',
                'kind: "Grading"',
                "metadata:",
                '  id: "bad"',
                '  title: "Bad Grading"',
                'status: "WAITING_REVIEW"',
                "spec:",
                "  totalScore: 100",
                "  checks: []",
            ]
        ),
        encoding="utf-8",
    )

    exit_code, payload = run_cli(["grade", "sandbox-precheck", "--grading", str(bad_grading)], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "SCHEMA_VALIDATION_ERROR"


def test_grade_report_reads_saved_report(tmp_path, capsys):
    report_path = tmp_path / "grading-report.json"
    run_cli(
        ["grade", "run", "--grading", "templates/grading/examples/python-pytest.yaml", "--output", str(report_path)],
        capsys,
    )

    exit_code, payload = run_cli(["grade", "report", "--file", str(report_path)], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["report"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["report"]["passed"] is True


def test_grade_report_missing_file_returns_json(capsys):
    exit_code, payload = run_cli(["grade", "report", "--file", "missing-grading-report.json"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "file"


def test_grade_result_preview_reads_existing_report_without_execution(tmp_path, capsys):
    report_path = tmp_path / "readonly-sandbox-report.json"
    preview_path = tmp_path / "grading-result-preview.json"
    run_exit_code, run_payload = run_cli(
        [
            "grade",
            "sandbox-run",
            "--grading",
            "templates/grading/examples/readonly-sandbox.yaml",
            "--submission",
            "examples/submissions/readonly-demo",
            "--output",
            str(report_path),
        ],
        capsys,
    )
    assert run_exit_code == 0
    assert_json_envelope(run_payload)

    exit_code, payload = run_cli(
        [
            "grade",
            "result-preview",
            "--report",
            str(report_path),
            "--candidate-id",
            "candidate_001",
            "--max-items",
            "3",
            "--output",
            str(preview_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    preview = payload["data"]["gradingResultPreview"]
    assert preview["component"] == "GradingResultPreview"
    assert preview["mode"] == "READ_EXISTING_GRADING_REPORT_ONLY"
    assert preview["candidateId"] == "candidate_001"
    assert preview["reportPath"] == str(report_path)
    assert preview["score"]["earnedScore"] == 120
    assert preview["score"]["passed"] is False
    assert preview["resultStatus"] == "NOT_PASSED"
    assert preview["summary"]["executed"] == 4
    assert preview["evidencePreview"]["totalVisible"] == 3
    assert preview["reviewHints"]["answerVisibleToCandidate"] is False
    assert preview["reviewHints"]["gradingRefVisibleToCandidate"] is False
    assert preview["safety"]["readOnly"] is True
    assert preview["safety"]["sandboxExecutedByPreview"] is False
    assert preview["safety"]["sourceSandboxExecuted"] is True
    assert preview["safety"]["autoApproveAllowed"] is False
    assert preview["outputPath"] == str(preview_path)
    saved_preview = json.loads(preview_path.read_text(encoding="utf-8"))
    assert saved_preview["component"] == "GradingResultPreview"


def test_dsl_validate_success(capsys):
    exit_code, payload = run_cli(
        ["dsl", "validate", "--kind", "ppt", "--file", "templates/ppt/examples/course-ppt.yaml"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["kind"] == "ppt"
    assert payload["data"]["dslId"] == "ppt_demo"


def test_dsl_validate_schema_error(tmp_path, capsys):
    bad_ppt = tmp_path / "bad-ppt.yaml"
    bad_ppt.write_text(
        "\n".join(
            [
                'version: "1.0"',
                'kind: "PPT"',
                "metadata:",
                '  id: "bad"',
                '  title: "Bad PPT"',
                'status: "WAITING_REVIEW"',
                "spec:",
                "  slides: []",
            ]
        ),
        encoding="utf-8",
    )

    exit_code, payload = run_cli(["dsl", "validate", "--kind", "ppt", "--file", str(bad_ppt)], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "SCHEMA_VALIDATION_ERROR"


def test_review_reject_without_reason_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]

    exit_code, payload = run_cli(["review", "reject", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    assert exit_code == 2
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"


def test_review_list_defaults_to_waiting_review(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    _, created = run_cli(["ppt", "generate", "--input", "examples/input/demo-source.md"], capsys)
    approved_task_id = created["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", approved_task_id, "--reviewer", "teacher_1"], capsys)

    exit_code, payload = run_cli(["review", "list"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["total"] == 1
    assert payload["data"]["reviewRequired"] is True
    assert payload["data"]["items"][0]["status"] == "WAITING_REVIEW"
    assert payload["data"]["items"][0]["taskType"] == "LAB_GENERATION"


def test_review_list_filters_by_task_type(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    run_cli(["ppt", "generate", "--input", "examples/input/demo-source.md"], capsys)

    exit_code, payload = run_cli(["review", "list", "--task-type", "PPT_GENERATION"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["taskType"] == "PPT_GENERATION"


def test_review_batch_summary_returns_queue_cards(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    run_cli(["ppt", "generate", "--input", "examples/input/demo-source.md"], capsys)

    exit_code, payload = run_cli(["review", "batch-summary"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    summary = payload["data"]["reviewTaskSummary"]
    assert summary["mode"] == "MOCK_ONLY"
    assert summary["total"] == 2
    assert summary["queueSummary"]["waitingReviewTotal"] == 2
    provider_signal = summary["providerQualityTaskSignal"]
    assert provider_signal["source"] == "reviewDetail.reviewPage.providerSummary.qualitySummary"
    assert provider_signal["taskTotal"] == 2
    assert provider_signal["availableTotal"] == 2
    assert provider_signal["realLlmCalledTotal"] == 0
    assert provider_signal["readyForReviewTotal"] == 2
    assert provider_signal["autoApproveAllowed"] is False
    assert provider_signal["batchStateChangeAllowed"] is False
    assert provider_signal["realPublishAllowed"] is False
    assert summary["batchActionPolicy"]["batchApproveAllowed"] is False
    assert summary["batchActionPolicy"]["batchRejectAllowed"] is False
    assert summary["batchActionPolicy"]["batchPublishAllowed"] is False
    assert summary["safety"]["realPublish"] is False
    assert {item["task"]["taskType"] for item in summary["items"]} == {"LAB_GENERATION", "PPT_GENERATION"}
    assert all(item["reviewPageSummary"]["actionBar"]["mockPublish"]["enabled"] is False for item in summary["items"])
    priority_queue = summary["reviewPriorityQueue"]
    assert priority_queue["summary"]["queueTotal"] == 2
    assert priority_queue["summary"]["normalTotal"] == 2
    assert priority_queue["summary"]["providerQualityAvailableTotal"] == 2
    assert priority_queue["summary"]["providerQualityReadyForReviewTotal"] == 2
    assert priority_queue["summary"]["autoApproveAllowed"] is False
    assert {item["reasonCode"] for item in priority_queue["items"]} == {
        "LAB_QUALITY_NEEDS_REVIEW",
        "PPT_SLIDE_PLAN_REVIEW",
    }
    real_demo_queue = summary["realDemoReviewQueue"]
    assert real_demo_queue["component"] == "RealDemoReviewQueue"
    assert real_demo_queue["source"] == "reviewTaskSummary.realDemoReviewQueue + local examples/output real LLM artifacts"
    assert real_demo_queue["taskTotal"] == 4
    assert real_demo_queue["waitingReviewTotal"] == 4
    assert real_demo_queue["dynamicTaskTotal"] == 0
    assert real_demo_queue["readonlyEvidenceCollectedTotal"] == 2
    assert real_demo_queue["autoApproveAllowed"] is False
    assert real_demo_queue["batchStateChangeAllowed"] is False
    assert real_demo_queue["realPublishAllowed"] is False
    assert [item["taskId"] for item in real_demo_queue["items"]] == [
        "real_demo_lab",
        "real_demo_exam",
        "real_demo_grading",
        "real_demo_ppt",
    ]
    controlled_signal = summary["controlledDockerEvidenceReviewSignal"]
    assert controlled_signal["component"] == "ControlledDockerEvidenceReviewSignal"
    assert controlled_signal["source"] == "realDemoPrototype.controlledDockerEvidenceDemo"
    assert controlled_signal["dynamicSource"] == "reviewDetail.controlledGradingEvidence"
    assert controlled_signal["fallbackSource"] == "realDemoPrototype.controlledDockerEvidenceDemo"
    assert controlled_signal["sourceMode"] == "STATIC_DEMO_FALLBACK"
    assert controlled_signal["taskId"] == "real_demo_grading"
    assert controlled_signal["status"] == "PARTIAL_CONTROLLED_EVIDENCE_COLLECTED"
    assert controlled_signal["available"] is True
    assert controlled_signal["taskTotal"] == 1
    assert controlled_signal["planTotal"] == 1
    assert controlled_signal["reportTotal"] == 1
    assert controlled_signal["controlledPlanPath"] == "examples/output/mimo-real-demo-controlled-plan.json"
    assert controlled_signal["controlledReportPath"] == "examples/output/mimo-real-demo-controlled-sandbox-report.json"
    assert controlled_signal["coveredCheckIds"] == ["check_q1", "check_q4"]
    assert controlled_signal["coveredCheckTypes"] == ["stdout_contains", "pytest"]
    assert controlled_signal["earnedScore"] == 40
    assert controlled_signal["totalControlledScore"] == 40
    assert controlled_signal["items"][0]["source"] == "realDemoPrototype.controlledDockerEvidenceDemo"
    assert controlled_signal["items"][0]["planPath"] == "examples/output/mimo-real-demo-controlled-plan.json"
    assert controlled_signal["items"][0]["reportPath"] == "examples/output/mimo-real-demo-controlled-sandbox-report.json"
    assert controlled_signal["items"][0]["networkEnabled"] is False
    assert controlled_signal["remainingCheckIds"] == ["check_q2", "check_q3"]
    assert controlled_signal["remainingCheckTypes"] == ["notebook_cell"]
    assert controlled_signal["remainingStatus"] == "STATIC_NOTEBOOK_EVIDENCE_READY_FOR_REVIEW"
    assert controlled_signal["notebookEvidenceReviewPlanSource"] == "reviewTaskSummary.notebookEvidenceReviewPlan"
    assert controlled_signal["remainingReviewPlanStatus"] == "NOTEBOOK_STATIC_EVIDENCE_COLLECTED"
    assert controlled_signal["remainingScore"] == 60
    assert controlled_signal["recommendedAction"] == "review_container_and_static_notebook_evidence_before_approval"
    assert controlled_signal["manualReviewRequired"] is True
    assert controlled_signal["autoApproveAllowed"] is False
    assert controlled_signal["batchStateChangeAllowed"] is False
    assert controlled_signal["realPublishAllowed"] is False
    merged_signal = summary["mergedGradingEvidenceReviewSignal"]
    assert merged_signal["component"] == "MergedGradingEvidenceReviewSignal"
    assert merged_signal["source"] == "reviewDetail.mergedGradingEvidence"
    assert merged_signal["sourceMode"] == "NO_MERGED_EVIDENCE_REPORT"
    assert merged_signal["available"] is False
    assert merged_signal["reportTotal"] == 0
    assert merged_signal["recommendedAction"] == "run_grade_evidence_merge_before_final_grading_review"
    assert merged_signal["autoApproveAllowed"] is False
    assert merged_signal["batchStateChangeAllowed"] is False
    assert merged_signal["realPublishAllowed"] is False
    notebook_plan = summary["notebookEvidenceReviewPlan"]
    assert notebook_plan["component"] == "NotebookEvidenceReviewPlan"
    assert notebook_plan["status"] == "NOTEBOOK_STATIC_EVIDENCE_COLLECTED"
    assert notebook_plan["staticEvidencePlanPath"] == "examples/output/mimo-real-demo-notebook-static-plan.json"
    assert notebook_plan["staticEvidenceReportPath"] == "examples/output/mimo-real-demo-notebook-static-report.json"
    assert notebook_plan["remainingCheckIds"] == ["check_q2", "check_q3"]
    assert notebook_plan["checkTypes"] == ["notebook_cell"]
    assert notebook_plan["checkTotal"] == 2
    assert notebook_plan["scoreTotal"] == 60
    assert notebook_plan["evidenceStatus"] == "STATIC_NOTEBOOK_EVIDENCE_COLLECTED"
    assert notebook_plan["reviewStrategy"] == "STATIC_NOTEBOOK_JSON_PARSE_REVIEW"
    assert notebook_plan["executed"] == 2
    assert notebook_plan["earnedScore"] == 60
    assert notebook_plan["staticEvidenceMethod"] == "STATIC_NOTEBOOK_JSON_PARSE"
    assert [item["checkId"] for item in notebook_plan["items"]] == ["check_q2", "check_q3"]
    assert all(item["runner"] == "NotebookGrader" for item in notebook_plan["items"])
    assert notebook_plan["safety"]["notebookKernelStarted"] is False
    assert notebook_plan["safety"]["notebookExecuted"] is False
    assert notebook_plan["safety"]["contestantCodeExecuted"] is False
    assert notebook_plan["safety"]["realPublishAllowed"] is False


def test_review_batch_summary_filters_and_limits(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    run_cli(["ppt", "generate", "--input", "examples/input/demo-source.md"], capsys)

    exit_code, payload = run_cli(
        ["review", "batch-summary", "--task-type", "LAB_GENERATION", "--limit", "1"],
        capsys,
    )

    assert exit_code == 0
    summary = payload["data"]["reviewTaskSummary"]
    assert summary["total"] == 1
    assert summary["filters"]["taskType"] == "LAB_GENERATION"
    assert summary["filters"]["limit"] == 1
    assert summary["items"][0]["task"]["taskType"] == "LAB_GENERATION"
    assert summary["reviewPriorityQueue"]["summary"]["queueTotal"] == 1
    assert summary["reviewPriorityQueue"]["items"][0]["taskType"] == "LAB_GENERATION"


def test_review_batch_summary_includes_grading_manual_checklist_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    run_cli(
        [
            "phase2",
            "grading-generate",
            "run",
            "--exam",
            "templates/exam/examples/notebook-fill-blank.yaml",
            "--reviewer",
            "teacher_1",
            "--output",
            str(tmp_path / "grading-report.json"),
        ],
        capsys,
    )

    exit_code, payload = run_cli(
        ["review", "batch-summary", "--task-type", "GRADING_GENERATION"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    summary = payload["data"]["reviewTaskSummary"]
    priority_queue = summary["reviewPriorityQueue"]
    assert priority_queue["summary"]["queueTotal"] == 1
    assert priority_queue["summary"]["urgentTotal"] == 1
    assert priority_queue["summary"]["manualReviewChecklistTaskTotal"] == 1
    assert priority_queue["summary"]["manualReviewChecklistNeedsHumanReviewTotal"] == 5
    item = priority_queue["items"][0]
    assert item["taskType"] == "GRADING_GENERATION"
    assert item["reasonCode"] == "HIGH_RISK_MOCK_EVIDENCE_REQUIRED"
    assert item["providerQualitySummary"]["source"] == "reviewDetail.reviewPage.providerSummary.qualitySummary"
    assert item["providerQualitySummary"]["available"] is True
    assert item["providerQualitySummary"]["realLlmCalled"] is False
    assert item["providerQualitySummary"]["readyForReview"] is True
    assert item["providerQualitySummary"]["autoApproveAllowed"] is False
    assert item["providerQualitySummary"]["batchStateChangeAllowed"] is False
    assert item["providerQualitySummary"]["realPublishAllowed"] is False
    checklist_summary = item["manualReviewChecklistSummary"]
    assert checklist_summary["enabled"] is True
    assert checklist_summary["source"] == "reviewDetail.assessmentPlan.manualReviewChecklist"
    assert checklist_summary["primaryReviewFocus"] == "review_assessment_plan_before_approval"
    assert checklist_summary["status"] == "NEEDS_HUMAN_REVIEW"
    assert checklist_summary["checklistTotal"] == 5
    assert checklist_summary["matchedTotal"] == 5
    assert checklist_summary["needsHumanReviewTotal"] == 5
    assert checklist_summary["nextReviewChecklistIds"] == [
        "verify_assessment_plan_aligned_with_checks",
        "confirm_mock_evidence_not_collected",
        "confirm_real_sandbox_evidence_required_before_real_execution",
        "verify_required_limits_present",
        "confirm_no_execution_or_publish",
    ]
    assert checklist_summary["operatorDecision"]["autoApproveAllowed"] is False
    assert checklist_summary["operatorDecision"]["batchStateChangeAllowed"] is False
    assert checklist_summary["operatorDecision"]["realSandboxRunEnabled"] is False
    assert checklist_summary["operatorDecision"]["realPublishAllowed"] is False


def test_review_batch_summary_writes_output_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    output_path = tmp_path / "review-batch-summary.json"

    exit_code, payload = run_cli(["review", "batch-summary", "--output", str(output_path)], capsys)

    assert exit_code == 0
    assert output_path.exists()
    assert payload["data"]["outputPath"] == str(output_path)
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["total"] == 1
    assert saved["batchActionPolicy"]["batchPublishAllowed"] is False


def test_review_batch_summary_rejects_invalid_limit(capsys):
    exit_code, payload = run_cli(["review", "batch-summary", "--limit", "0"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "limit"


def test_review_list_rejects_unknown_status(capsys):
    exit_code, payload = run_cli(["review", "list", "--status", "UNKNOWN"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "status"


def test_review_illegal_transition_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    exit_code, payload = run_cli(
        ["review", "reject", "--task-id", task_id, "--reviewer", "teacher_2", "--reason", "不符合要求"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "STATE_TRANSITION_ERROR"


def test_review_approve_records_reviewer_and_time(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]

    exit_code, payload = run_cli(
        ["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["task"]["status"] == "APPROVED"
    assert payload["data"]["task"]["reviewer"] == "teacher_1"
    assert payload["data"]["task"]["reviewedAt"] is not None
    assert payload["data"]["auditEvent"]["action"] == "APPROVE"
    assert payload["data"]["auditEvent"]["actor"] == "teacher_1"
    assert payload["data"]["auditEvent"]["fromStatus"] == "WAITING_REVIEW"
    assert payload["data"]["auditEvent"]["toStatus"] == "APPROVED"
    assert payload["data"]["auditEvent"]["realPublish"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "REVIEW_APPROVE"
    assert payload["data"]["operationAuditEvent"]["realPublish"] is False
    precheck = payload["data"]["preApproveReviewCheck"]
    assert precheck["component"] == "PreApproveReviewCheck"
    assert precheck["applicable"] is False
    assert precheck["approvalStillAllowed"] is True
    assert precheck["blocking"] is False


def test_review_audit_lists_events(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    exit_code, payload = run_cli(["review", "audit", "--task-id", task_id, "--action", "APPROVE"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["taskId"] == task_id
    assert payload["data"]["items"][0]["action"] == "APPROVE"
    assert payload["data"]["items"][0]["mode"] == "MOCK_ONLY"


def test_review_revision_request_records_feedback_without_status_change(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]

    exit_code, payload = run_cli(
        [
            "review",
            "revision-request",
            "--task-id",
            task_id,
            "--reviewer",
            "teacher_1",
            "--comment",
            "步骤 2 需要补充截图要求。",
            "--priority",
            "HIGH",
            "--target-section",
            "steps",
            "--requested-change",
            "补充截图验收标准",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["task"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["revisionRequest"]["taskId"] == task_id
    assert payload["data"]["revisionRequest"]["priority"] == "HIGH"
    assert payload["data"]["revisionRequest"]["targetSections"] == ["steps"]
    assert payload["data"]["revisionRequest"]["requestedChanges"] == ["补充截图验收标准"]
    assert payload["data"]["revisionRequest"]["taskStatusChanged"] is False
    assert payload["data"]["revisionRequest"]["newLlmRequestSent"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "REVIEW_REVISION_REQUEST"
    assert payload["data"]["operationAuditEvent"]["beforeState"] == "WAITING_REVIEW"
    assert payload["data"]["operationAuditEvent"]["afterState"] == "WAITING_REVIEW"
    assert payload["data"]["safety"]["realLlmCalled"] is False

    _, list_payload = run_cli(["review", "revision-list", "--task-id", task_id], capsys)
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["comment"] == "步骤 2 需要补充截图要求。"

    _, detail_payload = run_cli(["review", "detail", "--task-id", task_id], capsys)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["revisionRequests"]["total"] == 1
    assert detail["reviewPage"]["revisionRequests"]["highPriorityCount"] == 1
    assert detail["reviewPage"]["actionBar"]["requestRevision"]["enabled"] is True
    assert detail["reviewPage"]["actionBar"]["requestRevision"]["triggersLlm"] is False
    assert detail["summary"]["revisionRequestTotal"] == 1


def test_review_revision_request_rejects_non_waiting_review_task(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    exit_code, payload = run_cli(
        [
            "review",
            "revision-request",
            "--task-id",
            task_id,
            "--reviewer",
            "teacher_2",
            "--comment",
            "已通过后不再写入修改意见。",
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REVIEW_REVISION_REQUEST_INVALID_STATUS"


def test_review_regenerate_mock_creates_new_waiting_review_task(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    source_task_id = created["data"]["task"]["id"]
    _, revision_payload = run_cli(
        [
            "review",
            "revision-request",
            "--task-id",
            source_task_id,
            "--reviewer",
            "teacher_1",
            "--comment",
            "补充实验步骤的截图验收标准。",
            "--target-section",
            "steps",
        ],
        capsys,
    )
    revision_request_id = revision_payload["data"]["revisionRequest"]["id"]
    output_path = tmp_path / "lab-revision.json"

    exit_code, payload = run_cli(
        [
            "review",
            "regenerate-mock",
            "--task-id",
            source_task_id,
            "--reviewer",
            "teacher_1",
            "--revision-request-id",
            revision_request_id,
            "--output",
            str(output_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    regeneration = payload["data"]["mockRegeneration"]
    assert regeneration["sourceTask"]["id"] == source_task_id
    assert regeneration["sourceTask"]["status"] == "WAITING_REVIEW"
    assert regeneration["newTask"]["status"] == "WAITING_REVIEW"
    assert regeneration["newTask"]["taskType"] == "LAB_GENERATION_REVISION"
    assert regeneration["newTask"]["inputRef"] == revision_request_id
    assert regeneration["artifact"]["kind"] == "LAB_DSL"
    assert regeneration["artifact"]["metadata"]["sourceTaskId"] == source_task_id
    assert regeneration["artifact"]["metadata"]["sourceRevisionRequestId"] == revision_request_id
    assert regeneration["artifact"]["metadata"]["contentQualitySummary"]["readyForImportPreview"] is True
    assert regeneration["artifact"]["metadata"]["workflowContentQualitySummary"]["blockedForImportPreviewKinds"] == []
    assert regeneration["operationAuditEvent"]["action"] == "REVIEW_MOCK_REGENERATE"
    assert regeneration["operationAuditEvent"]["detail"]["newTaskId"] == regeneration["newTask"]["id"]
    assert regeneration["operationAuditEvent"]["detail"]["contentQualityReadyForImportPreview"] is True
    assert regeneration["safety"]["realLlmCalled"] is False
    assert regeneration["safety"]["newLlmRequestSent"] is False
    assert output_path.exists()

    revised = json.loads(output_path.read_text(encoding="utf-8"))
    assert revised["status"] == "WAITING_REVIEW"
    assert revised["metadata"]["title"].endswith("（修订草稿）")
    assert "sourceTaskId" not in revised["metadata"]

    _, detail_payload = run_cli(["review", "detail", "--task-id", regeneration["newTask"]["id"]], capsys)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["task"]["id"] == regeneration["newTask"]["id"]
    assert detail["summary"]["artifactTotal"] == 1
    assert detail["summary"]["workflowRunTotal"] == 1
    assert detail["reviewPage"]["dslPreview"]["artifactKind"] == "LAB_DSL"
    assert detail["reviewPage"]["contentQualitySummary"]["requiresRevisionBeforeImportPreview"] is False


def test_review_regenerate_mock_requires_revision_request(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    source_task_id = created["data"]["task"]["id"]

    exit_code, payload = run_cli(
        ["review", "regenerate-mock", "--task-id", source_task_id, "--reviewer", "teacher_1"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REVISION_REQUEST_NOT_FOUND"


def test_review_real_dsl_preview_exports_static_review_preview(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    output = tmp_path / "real-dsl-review-preview.json"

    exit_code, payload = run_cli(
        [
            "review",
            "real-dsl-preview",
            "--lab",
            "examples/output/real-llm-lab.json",
            "--exam",
            "examples/output/real-llm-exam.json",
            "--grading",
            "examples/output/real-llm-grading.json",
            "--ppt",
            "examples/output/real-llm-ppt.json",
            "--candidate-preview",
            "examples/output/real-llm-demo-candidate-preview.json",
            "--output",
            str(output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output.exists()
    preview = payload["data"]["realDslReviewPreview"]
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved == preview
    assert preview["component"] == "RealDslReviewPreview"
    assert preview["summary"]["labStepTotal"] == len(preview["labReview"]["steps"])
    assert preview["summary"]["examQuestionTotal"] == len(preview["examReview"]["candidateQuestions"])
    assert preview["summary"]["gradingPlanTotal"] == len(preview["gradingReview"]["assessmentPlan"])
    assert preview["summary"]["pptSlideTotal"] == len(preview["pptReview"]["slides"])
    assert preview["summary"]["qualityIssueTotal"] == len(preview["reviewIssues"])
    assert preview["summary"]["revisionSuggestionTotal"] == len(preview["revisionSuggestions"])
    assert preview["qualitySignals"]["summary"]["manualReviewRequired"] is True
    assert preview["qualitySignals"]["summary"]["autoApproveAllowed"] is False
    assert preview["qualitySignals"]["summary"]["realPublishAllowed"] is False
    assert preview["revisionSuggestions"]
    assert all(suggestion["keepsWaitingReview"] is True for suggestion in preview["revisionSuggestions"])
    assert preview["examReview"]["candidateSafety"]["gradingRefVisibleToCandidate"] is False
    assert all(question["gradingRefVisibleToCandidate"] is False for question in preview["examReview"]["candidateQuestions"])
    assert all(ref["teacherOnly"] is True and ref["candidateVisible"] is False for ref in preview["examReview"]["teacherQuestionRefs"])
    assert preview["gradingReview"]["commandExecutionAllowedFromPage"] is False
    assert payload["data"]["safety"]["newLlmRequestSent"] is False
    assert payload["data"]["safety"]["gradingRefVisibleToCandidate"] is False
    assert payload["data"]["safety"]["realPublishAllowed"] is False


def test_review_real_dsl_preview_missing_lab_returns_json(tmp_path, capsys):
    output = tmp_path / "real-dsl-review-preview.json"

    exit_code, payload = run_cli(
        [
            "review",
            "real-dsl-preview",
            "--lab",
            str(tmp_path / "missing-lab.json"),
            "--output",
            str(output),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "lab"
    assert not output.exists()


def test_review_real_dsl_revision_creates_waiting_review_draft(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    output = tmp_path / "lab-revision.json"
    report_output = tmp_path / "lab-revision-report.json"

    exit_code, payload = run_cli(
        [
            "review",
            "real-dsl-revision",
            "--kind",
            "lab",
            "--source",
            "examples/output/real-llm-lab.json",
            "--reviewer",
            "teacher_1",
            "--comment",
            "请补充实验验收说明，并保持人工审核。",
            "--target-section",
            "steps",
            "--requested-change",
            "补充验收说明",
            "--output",
            str(output),
            "--report-output",
            str(report_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output.exists()
    assert report_output.exists()
    draft = payload["data"]["realDslRevisionDraft"]
    assert draft["component"] == "RealDslRevisionDraft"
    assert draft["kind"] == "lab"
    assert draft["revisedStatus"] == "WAITING_REVIEW"
    assert draft["schemaValidated"] is True
    assert draft["safety"]["realLlmCalled"] is False
    assert draft["safety"]["newLlmRequestSent"] is False
    assert draft["safety"]["realPublishAllowed"] is False
    saved_dsl = json.loads(output.read_text(encoding="utf-8"))
    assert saved_dsl["status"] == "WAITING_REVIEW"
    assert "人工审核" in saved_dsl["spec"]["steps"][0]["instruction"]


def test_review_real_dsl_revision_missing_source_returns_json(tmp_path, capsys):
    output = tmp_path / "missing-source-revision.json"

    exit_code, payload = run_cli(
        [
            "review",
            "real-dsl-revision",
            "--kind",
            "lab",
            "--source",
            str(tmp_path / "missing-lab.json"),
            "--reviewer",
            "teacher_1",
            "--comment",
            "补充说明",
            "--output",
            str(output),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "source"
    assert not output.exists()


def test_review_real_dsl_revision_batch_creates_waiting_review_drafts(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_output = tmp_path / "revision-batch-report.json"

    exit_code, payload = run_cli(
        [
            "review",
            "real-dsl-revision-batch",
            "--preview",
            "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "--reviewer",
            "teacher_1",
            "--output-dir",
            str(tmp_path),
            "--report-output",
            str(report_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert report_output.exists()
    batch = payload["data"]["realDslRevisionBatch"]
    assert batch["component"] == "RealDslRevisionBatch"
    assert batch["draftTotal"] == 3
    assert batch["schemaValidatedTotal"] == 3
    assert batch["allDraftsWaitingReview"] is True
    assert batch["draftKinds"] == ["grading", "lab", "ppt"]
    assert batch["safety"]["realLlmCalled"] is False
    assert batch["safety"]["newLlmRequestSent"] is False
    assert batch["safety"]["realPublishAllowed"] is False
    assert all((tmp_path / Path(draft["outputPath"]).name).exists() for draft in batch["drafts"])


def test_review_real_dsl_revision_diff_preview_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    batch_report = tmp_path / "revision-batch-report.json"
    diff_output = tmp_path / "revision-diff-preview.json"
    create_batch_exit_code, create_batch_payload = run_cli(
        [
            "review",
            "real-dsl-revision-batch",
            "--preview",
            "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "--reviewer",
            "teacher_1",
            "--output-dir",
            str(tmp_path),
            "--report-output",
            str(batch_report),
        ],
        capsys,
    )
    assert create_batch_exit_code == 0
    assert create_batch_payload["success"] is True

    exit_code, payload = run_cli(
        [
            "review",
            "real-dsl-revision-diff-preview",
            "--batch-report",
            str(batch_report),
            "--output",
            str(diff_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    assert diff_output.exists()
    preview = payload["data"]["realDslRevisionDiffPreview"]
    assert preview["component"] == "RealDslRevisionDiffPreview"
    assert preview["summary"]["draftTotal"] == 3
    assert preview["summary"]["allDraftsWaitingReview"] is True
    assert preview["safety"]["newLlmRequestSent"] is False
    assert preview["safety"]["realPublishAllowed"] is False


def test_review_real_dsl_revision_decision_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    batch_report = tmp_path / "revision-batch-report.json"
    diff_output = tmp_path / "revision-diff-preview.json"
    decision_output = tmp_path / "revision-decision.json"
    run_cli(
        [
            "review",
            "real-dsl-revision-batch",
            "--preview",
            "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "--reviewer",
            "teacher_1",
            "--output-dir",
            str(tmp_path),
            "--report-output",
            str(batch_report),
        ],
        capsys,
    )
    run_cli(
        [
            "review",
            "real-dsl-revision-diff-preview",
            "--batch-report",
            str(batch_report),
            "--output",
            str(diff_output),
        ],
        capsys,
    )

    exit_code, payload = run_cli(
        [
            "review",
            "real-dsl-revision-decision",
            "--diff-preview",
            str(diff_output),
            "--suggestion-id",
            "revise_lab_objective_depth",
            "--reviewer",
            "teacher_1",
            "--decision",
            "approve",
            "--reason",
            "人工确认该修订可进入后续手动合并。",
            "--output",
            str(decision_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    assert decision_output.exists()
    decision = payload["data"]["realDslRevisionDecision"]
    assert decision["component"] == "RealDslRevisionDecision"
    assert decision["decisionStatus"] == "REVISION_APPROVED_FOR_MANUAL_MERGE"
    assert decision["manualMergeRequired"] is True
    assert decision["safety"]["sourceDslModified"] is False
    assert decision["safety"]["realPublishAllowed"] is False


def test_review_real_dsl_revision_promote_returns_waiting_review_candidate(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    batch_report = tmp_path / "revision-batch-report.json"
    diff_output = tmp_path / "revision-diff-preview.json"
    decision_output = tmp_path / "revision-decision.json"
    promoted_output = tmp_path / "revision-promoted.json"
    promotion_report = tmp_path / "revision-promotion-report.json"
    run_cli(
        [
            "review",
            "real-dsl-revision-batch",
            "--preview",
            "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "--reviewer",
            "teacher_1",
            "--output-dir",
            str(tmp_path),
            "--report-output",
            str(batch_report),
        ],
        capsys,
    )
    run_cli(["review", "real-dsl-revision-diff-preview", "--batch-report", str(batch_report), "--output", str(diff_output)], capsys)
    run_cli(
        [
            "review",
            "real-dsl-revision-decision",
            "--diff-preview",
            str(diff_output),
            "--suggestion-id",
            "revise_lab_objective_depth",
            "--reviewer",
            "teacher_1",
            "--decision",
            "approve",
            "--output",
            str(decision_output),
        ],
        capsys,
    )

    exit_code, payload = run_cli(
        [
            "review",
            "real-dsl-revision-promote",
            "--decision-report",
            str(decision_output),
            "--reviewer",
            "teacher_2",
            "--output",
            str(promoted_output),
            "--report-output",
            str(promotion_report),
        ],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    assert promoted_output.exists()
    assert promotion_report.exists()
    promotion = payload["data"]["realDslRevisionPromotion"]
    assert promotion["component"] == "RealDslRevisionPromotion"
    assert promotion["promotedStatus"] == "WAITING_REVIEW"
    assert promotion["schemaValidated"] is True
    assert promotion["safety"]["sourceDslModified"] is False
    assert promotion["safety"]["newLlmRequestSent"] is False
    assert promotion["safety"]["realPublishAllowed"] is False


def test_review_real_dsl_revision_enqueue_creates_review_detail(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    batch_report = tmp_path / "revision-batch-report.json"
    diff_output = tmp_path / "revision-diff-preview.json"
    decision_output = tmp_path / "revision-decision.json"
    promoted_output = tmp_path / "revision-promoted.json"
    promotion_report = tmp_path / "revision-promotion-report.json"
    run_cli(
        [
            "review",
            "real-dsl-revision-batch",
            "--preview",
            "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "--reviewer",
            "teacher_1",
            "--output-dir",
            str(tmp_path),
            "--report-output",
            str(batch_report),
        ],
        capsys,
    )
    run_cli(["review", "real-dsl-revision-diff-preview", "--batch-report", str(batch_report), "--output", str(diff_output)], capsys)
    run_cli(
        [
            "review",
            "real-dsl-revision-decision",
            "--diff-preview",
            str(diff_output),
            "--suggestion-id",
            "revise_lab_objective_depth",
            "--reviewer",
            "teacher_1",
            "--decision",
            "approve",
            "--output",
            str(decision_output),
        ],
        capsys,
    )
    run_cli(
        [
            "review",
            "real-dsl-revision-promote",
            "--decision-report",
            str(decision_output),
            "--reviewer",
            "teacher_2",
            "--output",
            str(promoted_output),
            "--report-output",
            str(promotion_report),
        ],
        capsys,
    )

    exit_code, payload = run_cli(
        [
            "review",
            "real-dsl-revision-enqueue",
            "--promotion-report",
            str(promotion_report),
            "--reviewer",
            "teacher_3",
        ],
        capsys,
    )

    assert exit_code == 0
    assert payload["success"] is True
    queue_item = payload["data"]["promotionReviewQueueItem"]
    assert queue_item["component"] == "RealDslRevisionPromotionReviewQueueItem"
    assert queue_item["taskStatus"] == "WAITING_REVIEW"
    assert queue_item["artifactKind"] == "LAB_DSL"
    assert queue_item["schemaValidated"] is True
    assert queue_item["safety"]["newLlmRequestSent"] is False
    assert queue_item["safety"]["realPublishAllowed"] is False
    detail = payload["data"]["reviewDetail"]
    assert detail["task"]["id"] == queue_item["taskId"]
    assert detail["task"]["status"] == "WAITING_REVIEW"
    assert detail["reviewPage"]["dslPreview"]["artifactKind"] == "LAB_DSL"
    assert detail["reviewPage"]["actionBar"]["approve"]["enabled"] is True
    assert detail["promotionReviewDisposition"]["state"] == "WAITING_HUMAN_REVIEW"
    assert detail["promotionReviewDisposition"]["nextRequiredAction"] == "approve_or_reject_promoted_candidate"
    assert detail["reviewPolicy"]["realPublishAllowed"] is False

    approve_exit_code, approve_payload = run_cli(
        ["review", "approve", "--task-id", queue_item["taskId"], "--reviewer", "teacher_4"],
        capsys,
    )
    detail_exit_code, detail_payload = run_cli(["review", "detail", "--task-id", queue_item["taskId"]], capsys)

    assert approve_exit_code == 0
    assert approve_payload["data"]["task"]["status"] == "APPROVED"
    assert approve_payload["data"]["operationAuditEvent"]["action"] == "REVIEW_APPROVE"
    assert detail_exit_code == 0
    approved_detail = detail_payload["data"]["reviewDetail"]
    assert approved_detail["promotionReviewDisposition"]["state"] == "APPROVED_FOR_MOCK_PUBLISH_ONLY"
    assert approved_detail["promotionReviewDisposition"]["mockPublishAvailable"] is True
    assert approved_detail["promotionReviewDisposition"]["realPublishAllowed"] is False
    assert approved_detail["reviewPage"]["promotionReviewDisposition"]["autoPublishAllowed"] is False
    action_panel = approved_detail["platformImportPreviewActions"]
    assert action_panel["visible"] is True
    assert action_panel["enabled"] is True
    assert action_panel["total"] == 1
    assert action_panel["enabledTotal"] == 1
    assert action_panel["previewAlreadyCreatedTotal"] == 0
    assert action_panel["contentQualityAdvisoryOnly"] is True
    assert action_panel["approvalStillRequired"] is True
    assert action_panel["items"][0]["component"] == "LabTemplateImportPreviewAction"
    assert action_panel["items"][0]["previewComponent"] == "LabTemplateImportPreview"
    assert action_panel["items"][0]["previewAlreadyCreated"] is False
    assert action_panel["items"][0]["contentQualityAdvisoryOnly"] is True
    assert f"lab import-preview --task-id {queue_item['taskId']}" in action_panel["items"][0]["cliCommand"]
    assert action_panel["items"][0]["apiEndpoint"] == "POST /api/labs/import-preview"
    assert action_panel["items"][0]["mcpTool"] == "create_lab_template_import_preview"
    assert approved_detail["reviewPage"]["platformImportPreviewActions"] == action_panel
    pre_core_exit_code, pre_core_payload = run_cli(["review", "core-readiness", "--task-id", queue_item["taskId"]], capsys)
    assert pre_core_exit_code == 0
    pre_core = pre_core_payload["data"]["coreWorkflowReadinessReport"]
    assert pre_core["summary"]["platformImportPreviewActionTotal"] == 1
    assert pre_core["summary"]["platformImportPreviewPendingTotal"] == 1
    assert pre_core["summary"]["platformImportPreviewPendingEntities"] == ["lab_template"]
    assert pre_core["platformImportPreviewActionSummary"]["pendingPreviewComponents"] == [
        "LabTemplateImportPreview"
    ]
    assert "lab import-preview" in pre_core["platformImportPreviewActionSummary"]["pendingCliCommands"][0]
    assert pre_core["nextToolRecommendation"]["component"] == "CoreWorkflowNextToolRecommendation"
    assert pre_core["nextToolRecommendation"]["mode"] == "READ_ONLY_TOOL_SELECTION_ADVICE"
    assert pre_core["nextToolRecommendation"]["reasonCode"] == "PLATFORM_IMPORT_PREVIEW_PENDING"
    assert pre_core["nextToolRecommendation"]["toolName"] == "create_lab_template_import_preview"
    assert pre_core["nextToolRecommendation"]["toolAvailable"] is True
    assert pre_core["nextToolRecommendation"]["argumentsPreview"]["taskId"] == queue_item["taskId"]
    assert pre_core["nextToolRecommendation"]["autoExecuteAllowed"] is False
    assert pre_core["nextToolRecommendation"]["autoApproveAllowed"] is False
    assert pre_core["nextToolRecommendation"]["autoPublishAllowed"] is False
    preview_step = next(step for step in pre_core["steps"] if step["id"] == "platform_import_preview_created")
    assert preview_step["actionSummary"]["pendingPlatformEntities"] == ["lab_template"]
    pre_signoff = approved_detail["platformImportPreviewSignoff"]
    assert pre_signoff["component"] == "AgentImportPreviewSignoffChecklist"
    assert pre_signoff["visible"] is True
    assert pre_signoff["readyForHumanSignoff"] is False
    assert pre_signoff["total"] == 0
    assert pre_signoff["missingPreviewTotal"] == 1
    assert pre_signoff["blockedTotal"] == 1
    assert pre_signoff["missingPreviewActions"][0]["component"] == "LabTemplateImportPreviewAction"
    assert approved_detail["reviewPage"]["platformImportPreviewSignoff"] == pre_signoff

    import_output = tmp_path / "lab-template-import-preview.json"
    import_exit_code, import_payload = run_cli(
        [
            "lab",
            "import-preview",
            "--task-id",
            queue_item["taskId"],
            "--reviewer",
            "teacher_4",
            "--output",
            str(import_output),
        ],
        capsys,
    )

    assert import_exit_code == 0
    preview = import_payload["data"]["labTemplateImportPreview"]
    assert preview["component"] == "LabTemplateImportPreview"
    assert preview["sourceTaskStatus"] == "APPROVED"
    assert preview["sourceArtifactKind"] == "LAB_DSL"
    assert preview["schemaValidated"] is True
    assert preview["labTemplateDraft"]["status"] == "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW"
    assert preview["importPlan"]["databaseWritePlanned"] is False
    assert preview["safety"]["realAgentImport"] is False
    assert preview["safety"]["realPublishAllowed"] is False
    assert import_payload["data"]["artifact"]["metadata"]["component"] == "LabTemplateImportPreview"
    assert import_payload["data"]["operationAuditEvent"]["action"] == "LAB_TEMPLATE_IMPORT_PREVIEW"
    assert import_output.exists()

    detail_after_import_exit_code, detail_after_import_payload = run_cli(
        ["review", "detail", "--task-id", queue_item["taskId"]],
        capsys,
    )
    assert detail_after_import_exit_code == 0
    detail_after_import = detail_after_import_payload["data"]["reviewDetail"]
    import_summary = detail_after_import["platformImportPreview"]
    assert import_summary["visible"] is True
    assert import_summary["total"] == 1
    assert import_summary["agentEntities"] == ["lab_template"]
    assert import_summary["items"][0]["component"] == "LabTemplateImportPreview"
    assert import_summary["items"][0]["draftStatus"] == "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW"
    assert import_summary["items"][0]["databaseWritten"] is False
    assert detail_after_import["reviewPage"]["platformImportPreview"] == import_summary
    assert detail_after_import["summary"]["platformImportPreviewTotal"] == 1
    action_panel_after_import = detail_after_import["platformImportPreviewActions"]
    assert action_panel_after_import["previewAlreadyCreatedTotal"] == 1
    assert action_panel_after_import["items"][0]["previewAlreadyCreated"] is True
    assert detail_after_import["reviewPage"]["platformImportPreviewActions"] == action_panel_after_import
    signoff = detail_after_import["platformImportPreviewSignoff"]
    assert signoff["visible"] is True
    assert signoff["readyForHumanSignoff"] is True
    assert signoff["total"] == 1
    assert signoff["needsHumanSignoffTotal"] == 1
    assert signoff["blockedTotal"] == 0
    assert signoff["missingPreviewTotal"] == 0
    assert signoff["items"][0]["component"] == "LabTemplateImportPreviewSignoff"
    assert signoff["items"][0]["agentEntity"] == "lab_template"
    assert signoff["items"][0]["status"] == "NEEDS_HUMAN_SIGNOFF"
    assert {
        check["id"] for check in signoff["items"][0]["checks"]
    } >= {
        "confirm_source_dsl_and_schema",
        "confirm_no_database_write_or_publish",
        "confirm_objectives_steps_environment_and_grading_ref",
    }
    assert signoff["databaseWritten"] is False
    assert signoff["realPublishAllowed"] is False
    assert detail_after_import["reviewPage"]["platformImportPreviewSignoff"] == signoff
    assert detail_after_import["summary"]["platformImportPreviewSignoffTotal"] == 1
    assert detail_after_import["summary"]["platformImportPreviewSignoffReady"] is True


def test_lab_import_preview_requires_approved_task(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    exit_code, generated = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = generated["data"]["task"]["id"]

    preview_exit_code, preview_payload = run_cli(
        ["lab", "import-preview", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "preview.json")],
        capsys,
    )

    assert exit_code == 0
    assert preview_exit_code == 1
    assert preview_payload["code"] == "STATE_TRANSITION_ERROR"
    assert preview_payload["errors"][0]["field"] == "status"


def test_lab_mock_import_requires_preview_and_creates_agent_entity(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, generated = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    blocked_exit, blocked = run_cli(
        ["lab", "mock-import", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "blocked.json")],
        capsys,
    )
    run_cli(
        ["lab", "import-preview", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "preview.json")],
        capsys,
    )
    output = tmp_path / "lab-template-mock-import.json"
    import_exit, imported = run_cli(
        ["lab", "mock-import", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(output)],
        capsys,
    )

    assert blocked_exit == 1
    assert blocked["code"] == "VALIDATION_ERROR"
    assert blocked["errors"][0]["field"] == "platformImportPreview"
    assert import_exit == 0
    assert output.exists()
    report = imported["data"]["agentEntityMockImport"]
    entity = imported["data"]["agentEntityRecord"]
    assert report["component"] == "LabTemplateMockImport"
    assert report["mode"] == "LOCAL_PLATFORM_ENTITY_MOCK_IMPORT"
    assert report["safety"]["mockStoreWritten"] is True
    assert report["safety"]["databaseWritten"] is False
    assert report["safety"]["realAgentImport"] is False
    assert entity["entityType"] == "lab_template"
    assert entity["status"] == "DRAFT_CREATED"
    assert entity["sourceTaskId"] == task_id
    assert entity["databaseWritten"] is False
    assert imported["data"]["operationAuditEvent"]["action"] == "LAB_TEMPLATE_MOCK_IMPORT"

    _, listed = run_cli(["platform-entity", "list", "--source-task-id", task_id], capsys)
    _, fetched = run_cli(["platform-entity", "get", "--id", entity["id"]], capsys)
    _, detail_payload = run_cli(["review", "detail", "--task-id", task_id], capsys)

    assert listed["data"]["total"] == 1
    assert listed["data"]["items"][0]["id"] == entity["id"]
    assert fetched["data"]["agentEntityRecord"]["id"] == entity["id"]
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["agentEntityMockImport"]["visible"] is True
    assert detail["agentEntityMockImport"]["total"] == 1
    assert detail["agentEntityMockImport"]["items"][0]["entityType"] == "lab_template"
    assert detail["reviewPage"]["agentEntityMockImport"] == detail["agentEntityMockImport"]
    assert detail["summary"]["agentEntityMockImportTotal"] == 1


def test_agent_entity_import_dry_run_builds_real_api_payload_without_sending(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, generated = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)
    run_cli(
        ["lab", "import-preview", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "preview.json")],
        capsys,
    )
    _, imported = run_cli(
        ["lab", "mock-import", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "mock-import.json")],
        capsys,
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]
    output = tmp_path / "platform-import-dry-run.json"

    exit_code, payload = run_cli(
        ["platform-entity", "import-dry-run", "--id", entity_id, "--reviewer", "teacher_2", "--output", str(output)],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert output.exists()
    dry_run = payload["data"]["agentEntityImportDryRun"]
    assert dry_run["component"] == "AgentEntityImportDryRun"
    assert dry_run["mode"] == "REAL_PLATFORM_IMPORT_DRY_RUN_ONLY"
    assert dry_run["agentEntityId"] == entity_id
    assert dry_run["entityType"] == "lab_template"
    assert dry_run["targetEndpoint"] == {
        "method": "POST",
        "path": "/api/platform/lab-template/draft-imports",
    }
    assert dry_run["requestPreview"]["apiVersion"] == "platform-import-dry-run/v1"
    assert dry_run["requestPreview"]["idempotencyKey"] == f"dryrun:{entity_id}"
    assert dry_run["requestPreview"]["payload"]["reviewStatus"] == "PENDING_MANUAL_PLATFORM_REVIEW"
    assert dry_run["requestPreview"]["payload"]["title"]
    assert dry_run["validation"]["readyForRealApiImplementation"] is True
    assert dry_run["validation"]["readyForRealApiCall"] is False
    assert dry_run["safety"]["dryRunOnly"] is True
    assert dry_run["safety"]["requestSent"] is False
    assert dry_run["safety"]["databaseWritten"] is False
    assert dry_run["safety"]["realAgentImport"] is False
    assert dry_run["safety"]["realPublish"] is False
    assert payload["data"]["artifact"]["mode"] == "REAL_PLATFORM_IMPORT_DRY_RUN_ONLY"
    assert payload["data"]["operationAuditEvent"]["action"] == "PLATFORM_ENTITY_IMPORT_DRY_RUN"


def test_ppt_deck_import_preview_mock_import_and_dry_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, generated = run_cli(["ppt", "generate", "--input", "examples/input/demo-source.md"], capsys)
    task_id = generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    preview_output = tmp_path / "ppt-deck-import-preview.json"
    preview_exit, preview_payload = run_cli(
        ["ppt", "import-preview", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(preview_output)],
        capsys,
    )
    import_output = tmp_path / "ppt-deck-mock-import.json"
    import_exit, imported = run_cli(
        ["ppt", "mock-import", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(import_output)],
        capsys,
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]
    dry_run_output = tmp_path / "ppt-deck-platform-import-dry-run.json"
    dry_run_exit, dry_run_payload = run_cli(
        ["platform-entity", "import-dry-run", "--id", entity_id, "--reviewer", "teacher_2", "--output", str(dry_run_output)],
        capsys,
    )

    assert preview_exit == 0
    assert preview_output.exists()
    preview = preview_payload["data"]["pptDeckImportPreview"]
    assert preview["component"] == "PptDeckImportPreview"
    assert preview["agentEntity"] == "ppt_deck"
    assert preview["pptDeckDraft"]["slideTotal"] >= 1
    assert preview["pptDeckDraft"]["pptxArtifactRequiredBeforePublish"] is True
    assert preview["safety"]["databaseWritten"] is False
    assert preview["safety"]["realAgentImport"] is False
    assert preview_payload["data"]["operationAuditEvent"]["action"] == "PPT_DECK_IMPORT_PREVIEW"

    assert import_exit == 0
    assert import_output.exists()
    entity = imported["data"]["agentEntityRecord"]
    assert entity["entityType"] == "ppt_deck"
    assert entity["payload"]["pptxArtifactImported"] is False
    assert entity["databaseWritten"] is False
    assert imported["data"]["operationAuditEvent"]["action"] == "PPT_DECK_MOCK_IMPORT"

    assert dry_run_exit == 0
    assert dry_run_output.exists()
    dry_run = dry_run_payload["data"]["agentEntityImportDryRun"]
    assert dry_run["entityType"] == "ppt_deck"
    assert dry_run["targetEndpoint"]["path"] == "/api/platform/ppt-deck/draft-imports"
    assert dry_run["requestPreview"]["entityType"] == "ppt_deck"
    assert dry_run["requestPreview"]["payload"]["pptxArtifactRequiredBeforePublish"] is True
    assert dry_run["requestPreview"]["payload"]["pptxArtifactImported"] is False
    assert dry_run["safety"]["requestSent"] is False
    assert dry_run["safety"]["realAgentImport"] is False


def test_agent_entity_import_dry_run_missing_entity_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))

    exit_code, payload = run_cli(
        [
            "platform-entity",
            "import-dry-run",
            "--id",
            "agent_entity_missing",
            "--reviewer",
            "teacher_2",
            "--output",
            str(tmp_path / "dry-run.json"),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"][0]["field"] == "id"


def test_agent_entity_import_send_requires_explicit_confirmations(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, generated = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)
    run_cli(
        ["lab", "import-preview", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "preview.json")],
        capsys,
    )
    _, imported = run_cli(
        ["lab", "mock-import", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "mock-import.json")],
        capsys,
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]
    dry_run = tmp_path / "platform-import-dry-run.json"
    run_cli(
        ["platform-entity", "import-dry-run", "--id", entity_id, "--reviewer", "teacher_2", "--output", str(dry_run)],
        capsys,
    )

    exit_code, payload = run_cli(
        [
            "platform-entity",
            "import-send",
            "--id",
            entity_id,
            "--reviewer",
            "teacher_3",
            "--dry-run",
            str(dry_run),
            "--output",
            str(tmp_path / "send-report.json"),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "PLATFORM_IMPORT_SEND_CONFIRMATION_REQUIRED"
    assert payload["errors"][0]["field"] == "explicitPlatformCallOptIn"


def test_agent_entity_import_send_posts_dry_run_payload_to_configured_platform(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    monkeypatch.setenv("AGENT_API_TOKEN", "platform-secret-token")
    server, thread, base_url = start_recording_platform_server()
    try:
        _, generated = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
        task_id = generated["data"]["task"]["id"]
        run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)
        run_cli(
            ["lab", "import-preview", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "preview.json")],
            capsys,
        )
        _, imported = run_cli(
            ["lab", "mock-import", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "mock-import.json")],
            capsys,
        )
        entity_id = imported["data"]["agentEntityRecord"]["id"]
        dry_run = tmp_path / "platform-import-dry-run.json"
        send_report = tmp_path / "platform-import-send-report.json"
        run_cli(
            ["platform-entity", "import-dry-run", "--id", entity_id, "--reviewer", "teacher_2", "--output", str(dry_run)],
            capsys,
        )

        exit_code, payload = run_cli(
            [
                "platform-entity",
                "import-send",
                "--id",
                entity_id,
                "--reviewer",
                "teacher_3",
                "--dry-run",
                str(dry_run),
                "--output",
                str(send_report),
                "--base-url",
                base_url,
                "--max-retries",
                "1",
                "--explicit-platform-call-opt-in",
                "--confirm-dry-run-reviewed",
                "--confirm-manual-platform-review",
                "--confirm-no-auto-publish",
            ],
            capsys,
        )
        status_report = tmp_path / "platform-import-status-query.json"
        status_exit_code, status_payload = run_cli(
            [
                "platform-entity",
                "import-status",
                "--id",
                entity_id,
                "--reviewer",
                "teacher_4",
                "--send-result",
                str(send_report),
                "--output",
                str(status_report),
                "--max-retries",
                "1",
                "--explicit-platform-query-opt-in",
            ],
            capsys,
        )
    finally:
        stop_recording_platform_server(server, thread)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert send_report.exists()
    post_requests = [item for item in RecordingPlatformImportHandler.requests if item.get("method") != "GET"]
    assert len(post_requests) == 1
    recorded = post_requests[0]
    assert recorded["path"] == "/api/platform/lab-template/draft-imports"
    assert recorded["authorization"] == "Bearer platform-secret-token"
    assert recorded["body"]["entityType"] == "lab_template"
    result = payload["data"]["agentEntityImportSendResult"]
    assert result["component"] == "AgentEntityImportSendResult"
    assert result["mode"] == "REAL_PLATFORM_IMPORT_REQUEST_SENT"
    assert result["agentEntityId"] == entity_id
    assert result["response"]["statusCode"] == 202
    assert result["response"]["body"]["json"]["status"] == "PENDING_MANUAL_PLATFORM_REVIEW"
    assert result["request"]["maxRetries"] == 1
    assert result["response"]["attempts"] == 1
    assert result["response"]["maxRetries"] == 1
    assert result["safety"]["requestSent"] is True
    assert result["safety"]["networkAccess"] is True
    assert result["safety"]["secretsRead"] is True
    assert result["safety"]["secretValueReturned"] is False
    assert result["safety"]["databaseWrittenByLocalSystem"] is False
    assert result["safety"]["realAgentImportAttempted"] is True
    assert result["safety"]["realAgentImportAccepted"] is True
    assert result["safety"]["autoPublishAllowed"] is False
    assert result["safety"]["realPublish"] is False
    assert payload["data"]["artifact"]["mode"] == "REAL_PLATFORM_IMPORT_REQUEST_SENT"
    assert payload["data"]["operationAuditEvent"]["action"] == "PLATFORM_ENTITY_IMPORT_SEND"
    _, fetched = run_cli(["platform-entity", "get", "--id", entity_id], capsys)
    activity = fetched["data"]["agentEntityImportActivity"]
    assert activity["component"] == "AgentEntityImportActivitySummary"
    assert activity["summary"]["dryRunPrepared"] is True
    assert activity["summary"]["requestSent"] is True
    assert activity["summary"]["latestStatusCode"] == 202
    assert activity["summary"]["secretValueReturned"] is False
    assert activity["summary"]["databaseWrittenByLocalSystem"] is False
    assert activity["summary"]["realPublish"] is False
    _, detail_payload = run_cli(["review", "detail", "--task-id", task_id], capsys)
    task_activity = detail_payload["data"]["reviewDetail"]["agentEntityImportActivity"]
    assert task_activity["visible"] is True
    assert task_activity["sendTotal"] == 1
    assert task_activity["summary"]["latestStatusCode"] == 202
    assert detail_payload["data"]["reviewDetail"]["reviewPage"]["agentEntityImportActivity"]["sendTotal"] == 1
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "platform-secret-token" not in serialized

    assert status_exit_code == 0
    assert_json_envelope(status_payload)
    assert status_report.exists()
    get_requests = [item for item in RecordingPlatformImportHandler.requests if item.get("method") == "GET"]
    assert len(get_requests) == 1
    assert get_requests[0]["path"] == "/api/platform/lab-template/draft-imports/draft_import_test"
    assert get_requests[0]["authorization"] == "Bearer platform-secret-token"
    status_query = status_payload["data"]["agentEntityImportStatusQuery"]
    assert status_query["component"] == "AgentEntityImportStatusQuery"
    assert status_query["mode"] == "REAL_PLATFORM_IMPORT_STATUS_QUERY"
    assert status_query["agentDraftId"] == "draft_import_test"
    assert status_query["agentStatus"] == "ACCEPTED_FOR_DRAFT"
    assert status_query["suggestedImportResultStatus"] == "ACCEPTED_FOR_DRAFT"
    assert status_query["response"]["statusCode"] == 200
    assert status_query["request"]["maxRetries"] == 1
    assert status_query["response"]["attempts"] == 1
    assert status_query["response"]["maxRetries"] == 1
    assert status_query["summary"]["localEntityStatusChanged"] is False
    assert status_query["safety"]["requestSent"] is True
    assert status_query["safety"]["networkAccess"] is True
    assert status_query["safety"]["mockStoreUpdated"] is False
    assert status_query["safety"]["secretValueReturned"] is False
    assert status_query["safety"]["realPublish"] is False
    assert status_payload["data"]["agentEntityRecord"]["status"] == "DRAFT_CREATED"

    _, fetched_after_status = run_cli(["platform-entity", "get", "--id", entity_id], capsys)
    status_activity = fetched_after_status["data"]["agentEntityImportActivity"]
    assert status_activity["statusQueryTotal"] == 1
    assert status_activity["summary"]["statusQueried"] is True
    assert status_activity["summary"]["latestQueriedPlatformStatus"] == "ACCEPTED_FOR_DRAFT"
    assert status_activity["summary"]["latestSuggestedImportResultStatus"] == "ACCEPTED_FOR_DRAFT"
    assert status_activity["safety"]["secretsRead"] is True
    assert status_activity["safety"]["secretValueReturned"] is False

    result_record = tmp_path / "platform-import-result-record.json"
    result_exit_code, result_payload = run_cli(
        [
            "platform-entity",
            "import-result",
            "--id",
            entity_id,
            "--reviewer",
            "teacher_4",
            "--send-result",
            str(send_report),
            "--platform-status",
            "ACCEPTED_FOR_DRAFT",
            "--output",
            str(result_record),
        ],
        capsys,
    )
    assert result_exit_code == 0
    assert_json_envelope(result_payload)
    assert result_record.exists()
    result_record_payload = result_payload["data"]["agentEntityImportResultRecord"]
    assert result_record_payload["component"] == "AgentEntityImportResultRecord"
    assert result_record_payload["agentEntityId"] == entity_id
    assert result_record_payload["agentDraftId"] == "draft_import_test"
    assert result_record_payload["agentStatus"] == "ACCEPTED_FOR_DRAFT"
    assert result_record_payload["localEntityStatus"]["before"] == "DRAFT_CREATED"
    assert result_record_payload["localEntityStatus"]["after"] == "REAL_IMPORT_DRAFT_ACCEPTED"
    assert result_record_payload["summary"]["acceptedForDraft"] is True
    assert result_record_payload["safety"]["requestSent"] is False
    assert result_record_payload["safety"]["networkAccess"] is False
    assert result_record_payload["safety"]["secretValueReturned"] is False
    assert result_record_payload["safety"]["realPublish"] is False
    assert result_payload["data"]["agentEntityRecord"]["status"] == "REAL_IMPORT_DRAFT_ACCEPTED"
    assert result_payload["data"]["operationAuditEvent"]["action"] == "PLATFORM_ENTITY_IMPORT_RESULT_RECORD"

    _, fetched_after_result = run_cli(["platform-entity", "get", "--id", entity_id], capsys)
    post_activity = fetched_after_result["data"]["agentEntityImportActivity"]
    assert post_activity["resultTotal"] == 1
    assert post_activity["summary"]["resultRecorded"] is True
    assert post_activity["summary"]["latestPlatformDraftId"] == "draft_import_test"
    assert post_activity["summary"]["latestPlatformStatus"] == "ACCEPTED_FOR_DRAFT"
    assert post_activity["summary"]["acceptedForDraft"] is True
    _, post_detail_payload = run_cli(["review", "detail", "--task-id", task_id], capsys)
    assert post_detail_payload["data"]["reviewDetail"]["agentEntityImportActivity"]["resultTotal"] == 1
    assert (
        post_detail_payload["data"]["reviewDetail"]["reviewPage"]["agentEntityImportActivity"]["summary"][
            "latestPlatformStatus"
        ]
        == "ACCEPTED_FOR_DRAFT"
    )


def test_agent_entity_import_uses_contract_config_for_endpoint_and_status_aliases(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    monkeypatch.setenv("AGENT_API_TOKEN", "platform-secret-token")
    contract_config = tmp_path / "platform-contract.json"
    contract_config.write_text(
        json.dumps(
            {
                "statusMapping": {"DONE": "ACCEPTED_FOR_DRAFT", "QUEUED": "PENDING_MANUAL_PLATFORM_REVIEW"},
                "entities": {
                    "lab_template": {
                        "draftImportPath": "/open/lab-imports",
                        "statusPathTemplate": "/open/lab-imports/{agentDraftId}/state",
                        "draftIdResponseKeys": ["jobId"],
                        "statusResponseKeys": ["reviewState"],
                        "requestBodyMapping": {
                            "lab.title": {"source": "payload.title", "required": True},
                            "lab.duration": "payload.durationMinutes",
                            "workflow.idempotencyKey": "idempotencyKey",
                            "review.status": {"value": "PENDING_MANUAL_PLATFORM_REVIEW"},
                        },
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    server, thread, base_url = start_configurable_platform_server()
    try:
        _, generated = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
        task_id = generated["data"]["task"]["id"]
        run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)
        run_cli(
            ["lab", "import-preview", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "preview.json")],
            capsys,
        )
        _, imported = run_cli(
            ["lab", "mock-import", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "mock-import.json")],
            capsys,
        )
        entity_id = imported["data"]["agentEntityRecord"]["id"]
        dry_run = tmp_path / "platform-import-dry-run.json"
        send_report = tmp_path / "platform-import-send-report.json"
        status_report = tmp_path / "platform-import-status-query.json"
        dry_run_exit, dry_run_payload = run_cli(
            [
                "platform-entity",
                "import-dry-run",
                "--id",
                entity_id,
                "--reviewer",
                "teacher_2",
                "--output",
                str(dry_run),
                "--contract-config",
                str(contract_config),
            ],
            capsys,
        )
        send_exit, send_payload = run_cli(
            [
                "platform-entity",
                "import-send",
                "--id",
                entity_id,
                "--reviewer",
                "teacher_3",
                "--dry-run",
                str(dry_run),
                "--output",
                str(send_report),
                "--base-url",
                base_url,
                "--explicit-platform-call-opt-in",
                "--confirm-dry-run-reviewed",
                "--confirm-manual-platform-review",
                "--confirm-no-auto-publish",
            ],
            capsys,
        )
        status_exit, status_payload = run_cli(
            [
                "platform-entity",
                "import-status",
                "--id",
                entity_id,
                "--reviewer",
                "teacher_4",
                "--send-result",
                str(send_report),
                "--output",
                str(status_report),
                "--explicit-platform-query-opt-in",
            ],
            capsys,
        )
    finally:
        stop_recording_platform_server(server, thread)

    assert dry_run_exit == 0
    dry_run_data = dry_run_payload["data"]["agentEntityImportDryRun"]
    assert dry_run_data["targetEndpoint"] == {"method": "POST", "path": "/open/lab-imports"}
    assert dry_run_data["platformApiContract"]["configApplied"] is True
    assert dry_run_data["contractValidation"]["valid"] is True
    assert dry_run_data["contractValidation"]["checkedEntityTypes"] == ["lab_template"]
    assert dry_run_data["contractValidation"]["summary"]["sampleValidatedEntityTotal"] == 1
    assert dry_run_data["requestBodyMapping"]["mode"] == "CONFIGURED_FIELD_MAPPING"
    assert dry_run_data["requestBody"]["workflow"]["idempotencyKey"] == f"dryrun:{entity_id}"
    assert send_exit == 0
    send_result = send_payload["data"]["agentEntityImportSendResult"]
    assert send_result["platformApiContract"]["draftIdResponseKeys"] == ["jobId"]
    assert send_result["request"]["bodySource"] == "requestBody"
    assert send_result["requestBodyMapping"]["applied"] is True
    assert status_exit == 0
    post_requests = [item for item in ConfigurablePlatformImportHandler.requests if item.get("method") != "GET"]
    get_requests = [item for item in ConfigurablePlatformImportHandler.requests if item.get("method") == "GET"]
    assert post_requests[0]["path"] == "/open/lab-imports"
    assert post_requests[0]["body"]["workflow"]["idempotencyKey"] == f"dryrun:{entity_id}"
    assert post_requests[0]["body"]["review"]["status"] == "PENDING_MANUAL_PLATFORM_REVIEW"
    assert "payload" not in post_requests[0]["body"]
    assert get_requests[0]["path"] == "/open/lab-imports/job_import_test/state"
    status_query = status_payload["data"]["agentEntityImportStatusQuery"]
    assert status_query["agentDraftId"] == "job_import_test"
    assert status_query["agentStatus"] == "DONE"
    assert status_query["suggestedImportResultStatus"] == "ACCEPTED_FOR_DRAFT"
    assert status_query["platformApiContract"]["statusResponseKeys"] == ["reviewState"]


def test_agent_entity_contract_validate_cli_reports_local_contract_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    contract_config = tmp_path / "platform-contract.json"
    contract_config.write_text(
        json.dumps(
            {
                "ignoredNote": "local-only note",
                "statusMapping": {"DONE": "ACCEPTED_FOR_DRAFT"},
                "entities": {
                    "lab_template": {
                        "draftImportPath": "/open/lab-imports",
                        "requestBodyMapping": {
                            "lab.title": {"source": "payload.title", "required": True},
                        },
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code, payload = run_cli(
        [
            "platform-entity",
            "contract-validate",
            "--contract-config",
            str(contract_config),
            "--entity-type",
            "lab_template",
        ],
        capsys,
    )

    assert exit_code == 0
    validation = payload["data"]["platformApiContractValidation"]
    assert validation["valid"] is True
    assert validation["checkedEntityTypes"] == ["lab_template"]
    assert validation["summary"]["requestBodyMappingConfiguredEntityTotal"] == 1
    assert validation["summary"]["warningTotal"] == 1
    assert validation["unknownTopLevelKeys"] == ["ignoredNote"]
    assert validation["entities"]["lab_template"]["draftImportEndpoint"] == {
        "method": "POST",
        "path": "/open/lab-imports",
    }
    assert validation["safety"]["networkAccess"] is False
    assert validation["safety"]["secretsRead"] is False


def test_agent_entity_contract_validate_cli_rejects_bad_config(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    contract_config = tmp_path / "bad-platform-contract.json"
    contract_config.write_text('{"entities":{"bad_entity":{}}}', encoding="utf-8")

    exit_code, payload = run_cli(
        ["platform-entity", "contract-validate", "--contract-config", str(contract_config)],
        capsys,
    )

    assert exit_code == 1
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"] == [{"field": "entities.bad_entity", "reason": "unsupported entity type override"}]


def test_agent_entity_import_result_rejects_missing_send_result(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, generated = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)
    run_cli(
        ["lab", "import-preview", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "preview.json")],
        capsys,
    )
    _, imported = run_cli(
        ["lab", "mock-import", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "mock-import.json")],
        capsys,
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]

    exit_code, payload = run_cli(
        [
            "platform-entity",
            "import-result",
            "--id",
            entity_id,
            "--reviewer",
            "teacher_4",
            "--send-result",
            str(tmp_path / "missing-send-result.json"),
            "--platform-status",
            "ACCEPTED_FOR_DRAFT",
            "--output",
            str(tmp_path / "result.json"),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "sendResult"


def test_agent_entity_import_status_requires_explicit_opt_in(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, generated = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)
    run_cli(
        ["lab", "import-preview", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "preview.json")],
        capsys,
    )
    _, imported = run_cli(
        ["lab", "mock-import", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "mock-import.json")],
        capsys,
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]

    exit_code, payload = run_cli(
        [
            "platform-entity",
            "import-status",
            "--id",
            entity_id,
            "--reviewer",
            "teacher_4",
            "--send-result",
            str(tmp_path / "missing-send.json"),
            "--output",
            str(tmp_path / "status.json"),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "PLATFORM_IMPORT_STATUS_QUERY_CONFIRMATION_REQUIRED"
    assert payload["errors"][0]["field"] == "explicitPlatformQueryOptIn"


def test_exam_and_grading_import_preview_from_approved_task(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    exit_code, generated = run_cli(["exam", "generate-from-lab", "--lab-id", "lab_demo"], capsys)
    task_id = generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_5"], capsys)
    pre_detail_exit_code, pre_detail_payload = run_cli(["review", "detail", "--task-id", task_id], capsys)
    assert pre_detail_exit_code == 0
    pre_action_panel = pre_detail_payload["data"]["reviewDetail"]["platformImportPreviewActions"]
    assert pre_action_panel["visible"] is True
    assert pre_action_panel["total"] == 2
    assert pre_action_panel["enabledTotal"] == 2
    assert pre_action_panel["previewAlreadyCreatedTotal"] == 0
    assert {item["component"] for item in pre_action_panel["items"]} == {
        "ExamQuestionImportPreviewAction",
        "GradingRuleImportPreviewAction",
    }
    assert {item["apiEndpoint"] for item in pre_action_panel["items"]} == {
        "POST /api/exams/import-preview",
        "POST /api/grading/import-preview",
    }
    pre_signoff = pre_detail_payload["data"]["reviewDetail"]["platformImportPreviewSignoff"]
    assert pre_signoff["visible"] is True
    assert pre_signoff["readyForHumanSignoff"] is False
    assert pre_signoff["total"] == 0
    assert pre_signoff["missingPreviewTotal"] == 2
    assert {
        item["component"] for item in pre_signoff["missingPreviewActions"]
    } == {
        "ExamQuestionImportPreviewAction",
        "GradingRuleImportPreviewAction",
    }

    exam_output = tmp_path / "exam-question-import-preview.json"
    exam_exit_code, exam_payload = run_cli(
        [
            "exam",
            "import-preview",
            "--task-id",
            task_id,
            "--reviewer",
            "teacher_5",
            "--output",
            str(exam_output),
        ],
        capsys,
    )
    grading_output = tmp_path / "grading-rule-import-preview.json"
    grading_exit_code, grading_payload = run_cli(
        [
            "grade",
            "import-preview",
            "--task-id",
            task_id,
            "--reviewer",
            "teacher_5",
            "--output",
            str(grading_output),
        ],
        capsys,
    )

    assert exit_code == 0
    assert exam_exit_code == 0
    exam_preview = exam_payload["data"]["examQuestionImportPreview"]
    assert exam_preview["component"] == "ExamQuestionImportPreview"
    assert exam_preview["sourceTaskStatus"] == "APPROVED"
    assert exam_preview["sourceArtifactKind"] == "EXAM_DSL"
    assert exam_preview["schemaValidated"] is True
    assert exam_preview["agentEntity"] == "exam_question"
    assert exam_preview["examQuestionDraft"]["status"] == "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW"
    assert exam_preview["examQuestionDraft"]["candidateAnswerVisible"] is False
    assert exam_preview["safety"]["answerVisibleToCandidate"] is False
    assert exam_payload["data"]["operationAuditEvent"]["action"] == "EXAM_QUESTION_IMPORT_PREVIEW"
    assert exam_output.exists()
    assert grading_exit_code == 0
    grading_preview = grading_payload["data"]["gradingRuleImportPreview"]
    assert grading_preview["component"] == "GradingRuleImportPreview"
    assert grading_preview["sourceTaskStatus"] == "APPROVED"
    assert grading_preview["sourceArtifactKind"] == "GRADING_DSL"
    assert grading_preview["schemaValidated"] is True
    assert grading_preview["agentEntity"] == "grading_rule"
    assert grading_preview["gradingRuleDraft"]["status"] == "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW"
    assert grading_preview["gradingRuleDraft"]["sandboxRequiredBeforeRealExecution"] is True
    controlled_next_action = grading_preview["controlledEvidenceNextAction"]
    assert controlled_next_action["component"] == "ControlledGradingEvidenceNextAction"
    assert controlled_next_action["apiEndpoint"] == "POST /api/grading/evidence-auto"
    assert "grade evidence-auto" in controlled_next_action["cliCommand"]
    assert "--include-controlled-command" in controlled_next_action["cliCommand"]
    assert controlled_next_action["manualReviewRequired"] is True
    assert controlled_next_action["autoApproveAllowed"] is False
    assert controlled_next_action["safety"]["sandboxExecutedByPreview"] is False
    assert grading_preview["importPlan"]["evidenceAutoRequiredBeforeFinalImportReview"] is True
    assert grading_preview["importPlan"]["databaseWritePlanned"] is False
    assert grading_preview["safety"]["realAgentImport"] is False
    assert grading_payload["data"]["operationAuditEvent"]["action"] == "GRADING_RULE_IMPORT_PREVIEW"
    assert grading_output.exists()

    detail_exit_code, detail_payload = run_cli(["review", "detail", "--task-id", task_id], capsys)
    assert detail_exit_code == 0
    detail = detail_payload["data"]["reviewDetail"]
    import_summary = detail["platformImportPreview"]
    assert import_summary["visible"] is True
    assert import_summary["total"] == 2
    assert import_summary["agentEntities"] == ["exam_question", "grading_rule"]
    assert {item["component"] for item in import_summary["items"]} == {
        "ExamQuestionImportPreview",
        "GradingRuleImportPreview",
    }
    assert {item["sourceArtifactKind"] for item in import_summary["items"]} == {"EXAM_DSL", "GRADING_DSL"}
    assert all(item["databaseWritten"] is False for item in import_summary["items"])
    grading_import_summary_item = next(
        item for item in import_summary["items"] if item["component"] == "GradingRuleImportPreview"
    )
    assert grading_import_summary_item["controlledEvidenceNextAction"]["apiEndpoint"] == "POST /api/grading/evidence-auto"
    assert import_summary["controlledEvidenceNextActionTotal"] == 1
    assert import_summary["safety"]["realPublishAllowed"] is False
    assert detail["reviewPage"]["platformImportPreview"] == import_summary
    assert detail["summary"]["platformImportPreviewVisible"] is True
    assert detail["summary"]["platformImportPreviewTotal"] == 2
    action_panel = detail["platformImportPreviewActions"]
    assert action_panel["total"] == 2
    assert action_panel["enabledTotal"] == 2
    assert action_panel["previewAlreadyCreatedTotal"] == 2
    assert {item["previewComponent"] for item in action_panel["items"]} == {
        "ExamQuestionImportPreview",
        "GradingRuleImportPreview",
    }
    assert all(item["previewAlreadyCreated"] is True for item in action_panel["items"])
    assert detail["reviewPage"]["platformImportPreviewActions"] == action_panel
    signoff = detail["platformImportPreviewSignoff"]
    assert signoff["visible"] is True
    assert signoff["readyForHumanSignoff"] is True
    assert signoff["total"] == 2
    assert signoff["blockedTotal"] == 0
    assert {item["component"] for item in signoff["items"]} == {
        "ExamQuestionImportPreviewSignoff",
        "GradingRuleImportPreviewSignoff",
    }
    signoff_check_ids = {
        check["id"] for item in signoff["items"] for check in item["checks"]
    }
    assert "confirm_candidate_answer_hidden_and_grading_refs_teacher_only" in signoff_check_ids
    assert "confirm_sandbox_required_before_real_execution" in signoff_check_ids
    assert "confirm_pre_approve_review_check_before_grading_rule_import" in signoff_check_ids
    assert "confirm_controlled_grading_evidence_next_action_before_platform_import" in signoff_check_ids
    assert signoff["preApproveReviewCheckSummary"]["applicable"] is True
    assert signoff["preApproveReviewCheckSummary"]["approveReadyDecision"] is False
    assert signoff["preApproveReviewCheckSummary"]["warningTotal"] == 2
    assert signoff["summary"]["controlledEvidenceNextActionTotal"] == 1
    grading_signoff = next(item for item in signoff["items"] if item["component"] == "GradingRuleImportPreviewSignoff")
    assert grading_signoff["preApproveReviewCheckSummary"] == signoff["preApproveReviewCheckSummary"]
    assert grading_signoff["controlledEvidenceNextAction"]["nextRequiredAction"] == (
        "run_grading_evidence_auto_before_final_grading_rule_import_review"
    )
    assert detail["reviewPage"]["platformImportPreviewSignoff"] == signoff
    assert detail["summary"]["platformImportPreviewSignoffVisible"] is True
    assert detail["summary"]["platformImportPreviewSignoffTotal"] == 2
    assert detail["summary"]["platformImportPreviewSignoffBlockedTotal"] == 0
    assert detail["summary"]["platformImportPreviewSignoffReady"] is True


def test_exam_and_grading_mock_import_from_previews(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, generated = run_cli(["exam", "generate-from-lab", "--lab-id", "lab_demo"], capsys)
    task_id = generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_5"], capsys)
    run_cli(
        ["exam", "import-preview", "--task-id", task_id, "--reviewer", "teacher_5", "--output", str(tmp_path / "exam-preview.json")],
        capsys,
    )
    run_cli(
        ["grade", "import-preview", "--task-id", task_id, "--reviewer", "teacher_5", "--output", str(tmp_path / "grading-preview.json")],
        capsys,
    )

    exam_exit, exam_imported = run_cli(
        ["exam", "mock-import", "--task-id", task_id, "--reviewer", "teacher_5", "--output", str(tmp_path / "exam-import.json")],
        capsys,
    )
    grading_exit, grading_imported = run_cli(
        ["grade", "mock-import", "--task-id", task_id, "--reviewer", "teacher_5", "--output", str(tmp_path / "grading-import.json")],
        capsys,
    )
    _, listed = run_cli(["platform-entity", "list", "--source-task-id", task_id], capsys)

    assert exam_exit == 0
    assert grading_exit == 0
    assert exam_imported["data"]["agentEntityRecord"]["entityType"] == "exam_question"
    assert exam_imported["data"]["agentEntityRecord"]["payload"]["candidateAnswerVisible"] is False
    assert grading_imported["data"]["agentEntityRecord"]["entityType"] == "grading_rule"
    assert grading_imported["data"]["agentEntityRecord"]["payload"]["sandboxRequiredBeforeRealExecution"] is True
    assert {item["entityType"] for item in listed["data"]["items"]} == {"exam_question", "grading_rule"}


def test_agent_entity_readiness_report_covers_mock_import_chain(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, lab_generated = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    lab_task_id = lab_generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", lab_task_id, "--reviewer", "teacher_1"], capsys)
    run_cli(
        ["lab", "import-preview", "--task-id", lab_task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "lab-preview.json")],
        capsys,
    )
    run_cli(
        ["lab", "mock-import", "--task-id", lab_task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "lab-import.json")],
        capsys,
    )

    _, exam_generated = run_cli(["exam", "generate-from-lab", "--lab-id", "lab_demo"], capsys)
    exam_task_id = exam_generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", exam_task_id, "--reviewer", "teacher_5"], capsys)
    run_cli(
        ["exam", "import-preview", "--task-id", exam_task_id, "--reviewer", "teacher_5", "--output", str(tmp_path / "exam-preview.json")],
        capsys,
    )
    run_cli(
        ["grade", "import-preview", "--task-id", exam_task_id, "--reviewer", "teacher_5", "--output", str(tmp_path / "grading-preview.json")],
        capsys,
    )
    run_cli(
        ["exam", "mock-import", "--task-id", exam_task_id, "--reviewer", "teacher_5", "--output", str(tmp_path / "exam-import.json")],
        capsys,
    )
    run_cli(
        ["grade", "mock-import", "--task-id", exam_task_id, "--reviewer", "teacher_5", "--output", str(tmp_path / "grading-import.json")],
        capsys,
    )

    _, ppt_generated = run_cli(["ppt", "generate", "--input", "examples/input/demo-source.md"], capsys)
    ppt_task_id = ppt_generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", ppt_task_id, "--reviewer", "teacher_6"], capsys)
    run_cli(
        ["ppt", "import-preview", "--task-id", ppt_task_id, "--reviewer", "teacher_6", "--output", str(tmp_path / "ppt-preview.json")],
        capsys,
    )
    run_cli(
        ["ppt", "mock-import", "--task-id", ppt_task_id, "--reviewer", "teacher_6", "--output", str(tmp_path / "ppt-import.json")],
        capsys,
    )

    exit_code, payload = run_cli(["platform-entity", "readiness-report"], capsys)
    filtered_exit_code, filtered_payload = run_cli(
        ["platform-entity", "readiness-report", "--source-task-id", lab_task_id],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    report = payload["data"]["agentEntityReadinessReport"]
    assert report["component"] == "AgentEntityReadinessReport"
    assert report["mode"] == "LOCAL_AGENT_ENTITY_READINESS_REPORT"
    assert report["summary"]["requiredTotal"] == 4
    assert report["summary"]["previewCreatedTotal"] == 4
    assert report["summary"]["mockImportCreatedTotal"] == 4
    assert report["summary"]["allReadyForManualPlatformReview"] is True
    assert report["summary"]["finalPublishReviewDecisionRecordedTotal"] == 0
    assert report["summary"]["allFinalPublishReviewDecisionsRecorded"] is False
    assert report["safety"]["readOnly"] is True
    assert report["safety"]["realAgentImport"] is False
    assert report["safety"]["realPublish"] is False
    assert {item["agentEntity"] for item in report["items"]} == {
        "lab_template",
        "exam_question",
        "grading_rule",
        "ppt_deck",
    }
    assert all(item["readyForManualAgentReview"] is True for item in report["items"])
    assert all(item["safety"]["databaseWritten"] is False for item in report["items"])
    assert all(item["finalPublishReviewDecision"]["recorded"] is False for item in report["items"])
    assert all(
        item["postSignoffPrePublishChecklist"]["entitySpecificReviewFocus"]["component"]
        == "AgentEntitySpecificPrePublishReviewFocus"
        for item in report["items"]
    )
    assert {
        item["agentEntity"]: item["postSignoffPrePublishChecklist"]["entitySpecificReviewFocus"][
            "primaryReviewFocus"
        ]
        for item in report["items"]
    } == {
        "lab_template": "review_lab_objectives_environment_and_grading_ref_before_publish",
        "exam_question": "review_candidate_safe_exam_preview_and_scoring_before_publish",
        "grading_rule": "review_grading_plan_sandbox_limits_and_evidence_before_publish",
        "ppt_deck": "review_ppt_deck_content_artifact_and_classroom_readiness_before_publish",
    }

    assert filtered_exit_code == 0
    filtered_report = filtered_payload["data"]["agentEntityReadinessReport"]
    assert filtered_report["sourceTaskId"] == lab_task_id
    assert filtered_report["summary"]["readyForManualAgentReviewTotal"] == 1
    assert filtered_report["summary"]["missingPreviewTotal"] == 3
    assert filtered_report["summary"]["missingMockImportTotal"] == 3
    lab_item = next(item for item in filtered_report["items"] if item["agentEntity"] == "lab_template")
    exam_item = next(item for item in filtered_report["items"] if item["agentEntity"] == "exam_question")
    assert lab_item["sourceTaskId"] == lab_task_id
    assert lab_item["readyForManualAgentReview"] is True
    assert exam_item["blockers"] == ["IMPORT_PREVIEW_MISSING", "MOCK_IMPORT_ENTITY_MISSING"]


def test_agent_entity_final_publish_review_decision_cli_records_local_decision(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    monkeypatch.setenv("AGENT_API_TOKEN", "platform-secret-token")
    _, generated = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = generated["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)
    run_cli(
        ["lab", "import-preview", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "preview.json")],
        capsys,
    )
    imported_exit, imported = run_cli(
        ["lab", "mock-import", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "import.json")],
        capsys,
    )
    assert imported_exit == 0
    entity_id = imported["data"]["agentEntityRecord"]["id"]

    dry_run = tmp_path / "dry-run.json"
    send_report = tmp_path / "send.json"
    status_report = tmp_path / "status.json"
    result_report = tmp_path / "result.json"
    signoff_report = tmp_path / "signoff.json"
    final_review_report = tmp_path / "final-review.json"
    run_cli(["platform-entity", "import-dry-run", "--id", entity_id, "--reviewer", "teacher_1", "--output", str(dry_run)], capsys)
    server, thread, base_url = start_recording_platform_server()
    try:
        run_cli(
            [
                "platform-entity",
                "import-send",
                "--id",
                entity_id,
                "--reviewer",
                "teacher_1",
                "--dry-run",
                str(dry_run),
                "--output",
                str(send_report),
                "--base-url",
                base_url,
                "--explicit-platform-call-opt-in",
                "--confirm-dry-run-reviewed",
                "--confirm-manual-platform-review",
                "--confirm-no-auto-publish",
            ],
            capsys,
        )
        run_cli(
            [
                "platform-entity",
                "import-status",
                "--id",
                entity_id,
                "--reviewer",
                "teacher_1",
                "--send-result",
                str(send_report),
                "--output",
                str(status_report),
                "--base-url",
                base_url,
                "--explicit-platform-query-opt-in",
            ],
            capsys,
        )
    finally:
        stop_recording_platform_server(server, thread)
    run_cli(
        [
            "platform-entity",
            "import-result",
            "--id",
            entity_id,
            "--reviewer",
            "teacher_1",
            "--send-result",
            str(send_report),
            "--platform-status",
            "ACCEPTED_FOR_DRAFT",
            "--output",
            str(result_report),
        ],
        capsys,
    )

    pre_signoff_core_exit, pre_signoff_core_payload = run_cli(
        ["review", "core-readiness", "--task-id", task_id, "--output", str(tmp_path / "core-before-signoff.json")],
        capsys,
    )
    assert pre_signoff_core_exit == 0
    pre_signoff_core = pre_signoff_core_payload["data"]["coreWorkflowReadinessReport"]
    assert pre_signoff_core["recommendedNextAction"] == "LOCAL_CORE_MVP_STOP_LINE_REACHED"
    assert pre_signoff_core["nextToolRecommendation"]["reasonCode"] == "LOCAL_CORE_MVP_STOP_LINE_REACHED"
    assert pre_signoff_core["nextToolRecommendation"]["toolAvailable"] is False
    assert pre_signoff_core["nextToolRecommendation"]["autoExecuteAllowed"] is False

    run_cli(
        ["platform-entity", "signoff", "--id", entity_id, "--reviewer", "teacher_1", "--output", str(signoff_report)],
        capsys,
    )

    pre_final_core_exit, pre_final_core_payload = run_cli(
        ["review", "core-readiness", "--task-id", task_id, "--output", str(tmp_path / "core-before-final-review.json")],
        capsys,
    )
    assert pre_final_core_exit == 0
    pre_final_core = pre_final_core_payload["data"]["coreWorkflowReadinessReport"]
    assert pre_final_core["recommendedNextAction"] == "LOCAL_CORE_MVP_STOP_LINE_REACHED"
    assert pre_final_core["nextToolRecommendation"]["reasonCode"] == "LOCAL_CORE_MVP_STOP_LINE_REACHED"
    assert pre_final_core["nextToolRecommendation"]["toolAvailable"] is False
    assert pre_final_core["nextToolRecommendation"]["autoPublishAllowed"] is False

    missing_exit, missing_payload = run_cli(
        [
            "platform-entity",
            "final-publish-review-decision",
            "--id",
            entity_id,
            "--reviewer",
            "teacher_1",
            "--decision",
            "APPROVED_FOR_PUBLISH_PLANNING",
            "--output",
            str(final_review_report),
        ],
        capsys,
    )
    assert missing_exit == 1
    assert missing_payload["code"] == "VALIDATION_ERROR"
    assert missing_payload["errors"][0]["field"] == "confirmNoAutoPublish"

    exit_code, payload = run_cli(
        [
            "platform-entity",
            "final-publish-review-decision",
            "--id",
            entity_id,
            "--reviewer",
            "teacher_1",
            "--decision",
            "APPROVED_FOR_PUBLISH_PLANNING",
            "--comment",
            "approved for planning only",
            "--output",
            str(final_review_report),
            "--confirm-no-auto-publish",
            "--confirm-no-real-publish",
            "--confirm-final-human-review",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert final_review_report.exists()
    decision = payload["data"]["finalPublishReviewDecision"]
    assert decision["component"] == "FinalPublishReviewDecision"
    assert decision["decision"] == "APPROVED_FOR_PUBLISH_PLANNING"
    assert decision["summary"]["publishExecuted"] is False
    assert decision["safety"]["realPublish"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "PLATFORM_ENTITY_FINAL_PUBLISH_REVIEW_DECISION"

    _, readiness_payload = run_cli(["platform-entity", "readiness-report", "--source-task-id", task_id], capsys)
    readiness = readiness_payload["data"]["agentEntityReadinessReport"]
    item = next(item for item in readiness["items"] if item["agentEntityId"] == entity_id)
    assert item["finalPublishReviewDecision"]["recorded"] is True
    assert item["finalPublishReviewDecision"]["decision"] == "APPROVED_FOR_PUBLISH_PLANNING"
    assert readiness["summary"]["finalPublishReviewDecisionRecordedTotal"] == 1
    assert readiness["summary"]["approvedForPublishPlanningTotal"] == 1

    core_exit, core_payload = run_cli(
        ["review", "core-readiness", "--task-id", task_id, "--output", str(tmp_path / "core-readiness.json")],
        capsys,
    )
    assert core_exit == 0
    assert_json_envelope(core_payload)
    core = core_payload["data"]["coreWorkflowReadinessReport"]
    assert core["component"] == "CoreWorkflowReadinessReport"
    assert core["taskId"] == task_id
    assert core["taskType"] == "LAB_GENERATION"
    assert core["status"] == "CORE_DEMO_READY_FOR_FINAL_REVIEW"
    assert core["ready"] is True
    assert core["recommendedNextAction"] == "LOCAL_CORE_MVP_STOP_LINE_REACHED"
    assert core["summary"]["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert core["nextToolRecommendation"]["reasonCode"] == "LOCAL_CORE_MVP_STOP_LINE_REACHED"
    assert core["nextToolRecommendation"]["finalReviewState"] == "NOT_GRADING_REVIEW"
    assert core["nextToolRecommendation"]["toolAvailable"] is False
    assert core["nextToolRecommendation"]["manualReviewRequired"] is True
    assert core["nextToolRecommendation"]["realPublishAllowed"] is False
    assert core["summary"]["platformRequiredTotal"] == 1
    assert core["summary"]["platformPreviewCreatedTotal"] == 1
    assert core["summary"]["platformMockImportCreatedTotal"] == 1
    assert core["summary"]["platformSignoffRecordedTotal"] == 1
    assert core["summary"]["finalPublishReviewDecisionRecordedTotal"] == 1
    assert not core["blockedSteps"]
    assert {step["id"] for step in core["steps"]} >= {
        "generated_content_human_approved",
        "platform_import_preview_created",
        "platform_mock_import_created",
        "platform_dry_run_prepared",
    }
    assert core["safety"]["readOnly"] is True
    assert core["safety"]["realPublish"] is False
    assert core["safety"]["networkAccess"] is False


def test_exam_import_preview_requires_approved_task(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, generated = run_cli(["exam", "generate-from-lab", "--lab-id", "lab_demo"], capsys)
    task_id = generated["data"]["task"]["id"]

    preview_exit_code, preview_payload = run_cli(
        ["exam", "import-preview", "--task-id", task_id, "--reviewer", "teacher_1", "--output", str(tmp_path / "preview.json")],
        capsys,
    )

    assert preview_exit_code == 1
    assert preview_payload["code"] == "STATE_TRANSITION_ERROR"
    assert preview_payload["errors"][0]["field"] == "status"


def test_review_real_dsl_revision_real_llm_requires_confirmations(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")
    output = tmp_path / "real-provider-revision.json"

    exit_code, payload = run_cli(
        [
            "review",
            "real-dsl-revision",
            "--kind",
            "lab",
            "--source",
            "examples/output/real-llm-lab.json",
            "--reviewer",
            "teacher_1",
            "--comment",
            "请用真实 LLM 重新组织步骤说明。",
            "--provider-mode",
            "real-llm",
            "--model",
            "test-model",
            "--base-url",
            "https://example.test/v1",
            "--output",
            str(output),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_LLM_DEMO_DSL_CONFIRMATION_REQUIRED"
    assert payload["providerErrorContext"]["adapterId"] == "openai_responses_sdk_adapter"
    assert payload["providerErrorContext"]["operation"] == "reviseDsl"
    assert payload["providerErrorContext"]["mode"] == "REAL_LLM"
    assert payload["providerErrorContext"]["realLlmCalled"] is False
    assert payload["providerErrorContext"]["autoPublishAllowed"] is False
    assert not output.exists()


def test_review_detail_returns_task_artifacts_and_policy(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]

    exit_code, payload = run_cli(["review", "detail", "--task-id", task_id], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    detail = payload["data"]["reviewDetail"]
    assert detail["mode"] == "MOCK_ONLY"
    assert detail["task"]["id"] == task_id
    assert detail["summary"]["artifactTotal"] == 2
    assert {artifact["kind"] for artifact in detail["artifacts"]} == {"MATERIAL_ANALYSIS", "LAB_DSL"}
    assert detail["reviewPolicy"]["reviewRequired"] is True
    assert detail["reviewPolicy"]["publishBlockedUntilApproved"] is True
    assert detail["reviewPolicy"]["allowedActions"] == ["approve", "reject", "request_revision"]
    assert detail["safety"]["realLlmCalled"] is False
    assert detail["safety"]["realPublish"] is False
    assert detail["reviewPage"]["header"]["taskId"] == task_id
    assert detail["reviewPage"]["dslPreview"]["artifactKind"] == "LAB_DSL"
    assert detail["reviewPage"]["riskSummary"]["unknownShellExecuted"] is False
    assert detail["reviewPage"]["actionBar"]["approve"]["enabled"] is True
    assert detail["reviewPage"]["actionBar"]["reject"]["requiresReason"] is True
    assert detail["reviewPage"]["actionBar"]["requestRevision"]["enabled"] is True
    assert detail["reviewPage"]["actionBar"]["mockPublish"]["enabled"] is False
    assert detail["reviewPage"]["emptyStates"]["noArtifacts"] is False
    assert detail["preApproveReviewCheck"]["applicable"] is False
    assert detail["preApproveReviewCheck"]["summary"]["approveReadyDecision"] is False
    assert detail["reviewPage"]["preApproveReviewCheck"] == detail["preApproveReviewCheck"]


def test_review_detail_writes_output_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]
    output_path = tmp_path / "review-detail.json"

    exit_code, payload = run_cli(["review", "detail", "--task-id", task_id, "--output", str(output_path)], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["outputPath"] == str(output_path)
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["task"]["id"] == task_id
    assert saved["reviewPage"]["actionBar"]["mockPublish"]["realPublish"] is False
    assert saved["safety"]["realLlmCalled"] is False


def test_review_detail_after_approval_includes_audit_events(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    exit_code, payload = run_cli(["review", "detail", "--task-id", task_id], capsys)

    assert exit_code == 0
    detail = payload["data"]["reviewDetail"]
    assert detail["task"]["status"] == "APPROVED"
    assert detail["reviewPolicy"]["reviewRequired"] is False
    assert detail["reviewPolicy"]["publishBlockedUntilApproved"] is False
    assert detail["reviewPolicy"]["allowedActions"] == ["mock_publish"]
    assert detail["summary"]["reviewAuditEventTotal"] == 1
    assert detail["summary"]["operationAuditEventTotal"] == 1
    assert detail["reviewAuditEvents"][0]["action"] == "APPROVE"
    assert detail["operationAuditEvents"][0]["action"] == "REVIEW_APPROVE"


def test_review_detail_includes_high_risk_mcp_publish_intent(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(
        [
            "mcp",
            "call",
            "--tool",
            "publish_lab",
            "--profile",
            "all",
            "--arguments",
            '{"labId":"lab_demo","reason":"运营申请发布","actor":"operator_1"}',
        ],
        capsys,
    )
    task_id = created["data"]["response"]["data"]["task"]["id"]

    exit_code, payload = run_cli(["review", "detail", "--task-id", task_id], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    detail = payload["data"]["reviewDetail"]
    assert detail["task"]["taskType"] == "MCP_PUBLISH_LAB_INTENT"
    assert detail["reviewPolicy"]["highRiskIntent"] is True
    assert detail["reviewPolicy"]["reviewIntentOnly"] is True
    assert detail["reviewPolicy"]["allowedActions"] == ["approve", "reject", "request_revision"]
    assert detail["highRiskIntent"]["intentType"] == "publish_lab"
    assert detail["highRiskIntent"]["toolName"] == "publish_lab"
    assert detail["highRiskIntent"]["resourceType"] == "LAB"
    assert detail["highRiskIntent"]["resourceId"] == "lab_demo"
    assert detail["highRiskIntent"]["riskLevel"] == "high"
    assert detail["highRiskIntent"]["requiresSecondConfirmation"] is False
    assert detail["highRiskIntent"]["reviewIntentOnly"] is True
    assert detail["highRiskIntent"]["realActionExecuted"] is False
    assert detail["highRiskIntent"]["realPublish"] is False
    disposition = detail["highRiskIntent"]["postReviewDisposition"]
    assert disposition["state"] == "WAITING_HUMAN_REVIEW"
    assert disposition["nextRequiredAction"] == "approve_or_reject"
    assert disposition["executionBlocked"] is True
    assert disposition["executeRealActionAllowed"] is False
    assert detail["reviewPolicy"]["postReviewDispositionState"] == "WAITING_HUMAN_REVIEW"
    assert detail["summary"]["operationAuditEventTotal"] == 1
    assert detail["summary"]["highRiskIntentAuditEventTotal"] == 1
    assert detail["operationAuditEvents"][0]["action"] == "PUBLISH_LAB_INTENT"
    assert detail["operationAuditEvents"][0]["resourceType"] == "LAB"
    assert detail["reviewPage"]["highRiskIntentPanel"]["visible"] is True
    assert detail["reviewPage"]["highRiskIntentPanel"]["postReviewState"] == "WAITING_HUMAN_REVIEW"
    assert detail["reviewPage"]["highRiskIntentPanel"]["executionBlocked"] is True
    assert detail["reviewPage"]["highRiskIntentPanel"]["executeRealPublishEnabled"] is False
    assert detail["reviewPage"]["highRiskIntentPanel"]["destroyRealEnvironmentEnabled"] is False
    assert detail["safety"]["highRiskIntentExecutionAllowed"] is False


def test_review_detail_for_approved_publish_intent_uses_execution_blocked_disposition(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(
        [
            "mcp",
            "call",
            "--tool",
            "publish_lab",
            "--profile",
            "all",
            "--arguments",
            '{"labId":"lab_demo","reason":"运营申请发布","actor":"operator_1"}',
        ],
        capsys,
    )
    task_id = created["data"]["response"]["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    exit_code, payload = run_cli(["review", "detail", "--task-id", task_id], capsys)

    assert exit_code == 0
    detail = payload["data"]["reviewDetail"]
    assert detail["task"]["status"] == "APPROVED"
    assert detail["reviewPolicy"]["highRiskIntent"] is True
    assert detail["reviewPolicy"]["allowedActions"] == []
    assert detail["reviewPolicy"]["postReviewDispositionState"] == "APPROVED_EXECUTION_BLOCKED"
    disposition = detail["highRiskIntent"]["postReviewDisposition"]
    assert disposition["state"] == "APPROVED_EXECUTION_BLOCKED"
    assert disposition["nextRequiredAction"] == "mock_disposition_only"
    assert disposition["secondConfirmationRequired"] is False
    assert disposition["executionBlocked"] is True
    assert disposition["executeRealPublishEnabled"] is False
    assert disposition["realPublish"] is False
    assert detail["reviewPage"]["actionBar"]["mockPublish"]["enabled"] is False
    assert detail["reviewPage"]["highRiskIntentPanel"]["postReviewState"] == "APPROVED_EXECUTION_BLOCKED"
    assert detail["reviewPage"]["highRiskIntentPanel"]["executeRealPublishEnabled"] is False


def test_review_detail_for_approved_high_risk_intent_still_blocks_execution(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(
        [
            "mcp",
            "call",
            "--tool",
            "destroy_environment",
            "--profile",
            "all",
            "--arguments",
            '{"environmentId":"env_demo","reason":"清理申请","actor":"operator_1"}',
        ],
        capsys,
    )
    task_id = created["data"]["response"]["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    exit_code, payload = run_cli(["review", "detail", "--task-id", task_id], capsys)

    assert exit_code == 0
    detail = payload["data"]["reviewDetail"]
    assert detail["task"]["status"] == "APPROVED"
    assert detail["reviewPolicy"]["highRiskIntent"] is True
    assert detail["reviewPolicy"]["allowedActions"] == []
    assert detail["reviewPolicy"]["postReviewDispositionState"] == "APPROVED_PENDING_SECOND_CONFIRMATION"
    assert detail["reviewPolicy"]["secondConfirmationRequired"] is True
    assert detail["highRiskIntent"]["intentType"] == "destroy_environment"
    assert detail["highRiskIntent"]["requiresSecondConfirmation"] is True
    disposition = detail["highRiskIntent"]["postReviewDisposition"]
    assert disposition["state"] == "APPROVED_PENDING_SECOND_CONFIRMATION"
    assert disposition["nextRequiredAction"] == "second_confirmation"
    assert disposition["secondConfirmationRequired"] is True
    assert disposition["secondConfirmationSatisfied"] is False
    assert disposition["executionBlocked"] is True
    assert disposition["destroyRealEnvironmentEnabled"] is False
    assert detail["highRiskIntent"]["environmentDestroyed"] is False
    assert detail["reviewPage"]["actionBar"]["mockPublish"]["enabled"] is False
    assert (
        detail["reviewPage"]["highRiskIntentPanel"]["postReviewState"]
        == "APPROVED_PENDING_SECOND_CONFIRMATION"
    )
    assert detail["reviewPage"]["highRiskIntentPanel"]["secondConfirmationRequired"] is True
    assert detail["reviewPage"]["highRiskIntentPanel"]["secondConfirmationSatisfied"] is False
    assert detail["reviewPage"]["highRiskIntentPanel"]["destroyRealEnvironmentEnabled"] is False


def test_review_second_confirmation_status_for_destroy_intent_is_read_only(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(
        [
            "mcp",
            "call",
            "--tool",
            "destroy_environment",
            "--profile",
            "all",
            "--arguments",
            '{"environmentId":"env_demo","reason":"清理申请","actor":"operator_1"}',
        ],
        capsys,
    )
    task_id = created["data"]["response"]["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    exit_code, payload = run_cli(["review", "second-confirmation-status", "--task-id", task_id], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    status = payload["data"]["secondConfirmationStatus"]
    assert status["mode"] == "MOCK_ONLY"
    assert status["eligible"] is True
    assert status["intent"]["intentType"] == "destroy_environment"
    assert status["state"] == "APPROVED_PENDING_SECOND_CONFIRMATION"
    assert status["nextRequiredAction"] == "second_confirmation"
    assert status["secondConfirmationRequired"] is True
    assert status["secondConfirmationSatisfied"] is False
    assert status["readOnly"] is True
    assert status["confirmationActionAvailable"] is False
    assert status["confirmationEndpointEnabled"] is False
    assert status["executeRealActionAllowed"] is False
    assert status["destroyRealEnvironmentEnabled"] is False
    assert status["realCloudResourceChanged"] is False
    assert status["environmentDestroyed"] is False
    assert "destroyRealEnvironment" in status["blockedActions"]


def test_review_second_confirmation_status_rejects_publish_intent(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(
        [
            "mcp",
            "call",
            "--tool",
            "publish_lab",
            "--profile",
            "all",
            "--arguments",
            '{"labId":"lab_demo","reason":"运营申请发布","actor":"operator_1"}',
        ],
        capsys,
    )
    task_id = created["data"]["response"]["data"]["task"]["id"]

    exit_code, payload = run_cli(["review", "second-confirmation-status", "--task-id", task_id], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "taskId"
    assert "不需要二次确认" in payload["message"]


def test_review_second_confirmation_status_missing_task_returns_json(capsys):
    exit_code, payload = run_cli(["review", "second-confirmation-status", "--task-id", "task_missing"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"][0]["field"] == "taskId"


def test_review_detail_missing_task_returns_json(capsys):
    exit_code, payload = run_cli(["review", "detail", "--task-id", "task_missing"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"][0]["field"] == "taskId"


def test_review_detail_includes_workflow_steps(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, demo = run_cli(
        [
            "workflow",
            "demo",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
        ],
        capsys,
    )
    task_id = demo["data"]["steps"][0]["taskId"]
    run_id = demo["data"]["workflowRun"]["id"]

    exit_code, payload = run_cli(["review", "detail", "--task-id", task_id], capsys)

    assert exit_code == 0
    detail = payload["data"]["reviewDetail"]
    assert detail["summary"]["workflowRunTotal"] == 1
    assert detail["workflowRuns"][0]["id"] == run_id
    assert detail["workflowSteps"][0]["workflowRunId"] == run_id
    assert detail["workflowSteps"][0]["name"] == "generate_lab_dsl"
    assert detail["workflowSteps"][0]["detail"]["taskId"] == task_id


def test_review_detail_for_phase2_grading_includes_manual_review_checklist(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "phase2-grading-generation-report.json"
    _, generated = run_cli(
        [
            "phase2",
            "grading-generate",
            "run",
            "--exam",
            "templates/exam/examples/notebook-fill-blank.yaml",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
        ],
        capsys,
    )
    grading_task = generated["data"]["createdTasks"][0]

    exit_code, payload = run_cli(["review", "detail", "--task-id", grading_task["id"]], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    detail = payload["data"]["reviewDetail"]
    manual_checklist = detail["assessmentPlan"]["manualReviewChecklist"]
    assert manual_checklist["enabled"] is True
    assert manual_checklist["source"] == "reviewDetail.assessmentPlan"
    assert manual_checklist["taskId"] == grading_task["id"]
    assert [item["id"] for item in manual_checklist["checklist"]] == [
        "verify_assessment_plan_aligned_with_checks",
        "confirm_mock_evidence_not_collected",
        "confirm_real_sandbox_evidence_required_before_real_execution",
        "verify_required_limits_present",
        "confirm_no_execution_or_publish",
    ]
    assert all(item["matched"] is True for item in manual_checklist["checklist"])
    assert manual_checklist["operatorDecision"]["autoApproveAllowed"] is False
    assert manual_checklist["operatorDecision"]["batchStateChangeAllowed"] is False
    assert manual_checklist["operatorDecision"]["realSandboxRunEnabled"] is False
    assert manual_checklist["operatorDecision"]["contestantCodeExecuted"] is False
    assert manual_checklist["operatorDecision"]["realPublishAllowed"] is False
    assert detail["reviewPage"]["assessmentPlanManualReviewChecklist"] == manual_checklist


def test_unapproved_task_cannot_publish(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]

    exit_code, payload = run_cli(["review", "publish", "--task-id", task_id], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "STATE_TRANSITION_ERROR"


def test_approved_task_can_mock_publish(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, created = run_cli(["lab", "generate-from-source", "--input", "examples/input/demo-source.md"], capsys)
    task_id = created["data"]["task"]["id"]
    run_cli(["review", "approve", "--task-id", task_id, "--reviewer", "teacher_1"], capsys)

    exit_code, payload = run_cli(["review", "publish", "--task-id", task_id], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["task"]["status"] == "COMPLETED"
    assert payload["data"]["publishResult"]["published"] is False
    assert payload["data"]["publishResult"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["auditEvent"]["action"] == "MOCK_PUBLISH"
    assert payload["data"]["auditEvent"]["realPublish"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "MOCK_PUBLISH"
    assert payload["data"]["operationAuditEvent"]["realPublish"] is False


def test_workflow_demo_returns_main_chain(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "workflow-report.json"

    exit_code, payload = run_cli(
        [
            "workflow",
            "demo",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert report_path.exists()
    assert payload["data"]["reportPath"] == str(report_path)
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["reviewRequired"] is True
    assert payload["data"]["publishBlockedUntilApproved"] is True
    assert [step["name"] for step in payload["data"]["steps"]] == [
        "generate_lab_dsl",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "generate_ppt_dsl",
        "mock_grade_run",
    ]
    assert payload["data"]["steps"][-1]["report"]["earnedScore"] == 100
    assert payload["data"]["providerAdapter"] == "mock_provider_adapter"
    assert payload["data"]["steps"][0]["provider"]["adapterId"] == "mock_provider_adapter"
    assert payload["data"]["steps"][1]["provider"]["providerId"] == "mock"
    assert payload["data"]["steps"][2]["provider"]["networkAccess"] is False
    assert payload["data"]["steps"][3]["provider"]["realLlmCalled"] is False
    assert set(payload["data"]["providerCallAuditEvents"]) == {"lab", "exam", "grading", "ppt"}
    assert [payload["data"]["steps"][index]["providerCallAuditEvent"]["detail"]["workflowStep"] for index in range(4)] == [
        "generate_lab_dsl",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "generate_ppt_dsl",
    ]
    assert payload["data"]["steps"][0]["providerCallAuditEvent"]["promptId"] == "lab_generation_v0"
    assert payload["data"]["steps"][1]["providerCallAuditEvent"]["inputRef"] == "lab_demo"
    assert payload["data"]["steps"][2]["providerCallAuditEvent"]["inputRef"] == "exam_demo"
    assert payload["data"]["steps"][3]["providerCallAuditEvent"]["generatedContentCreated"] is True
    assert payload["data"]["steps"][3]["providerCallAuditEvent"]["realLlmCalled"] is False
    assert payload["data"]["materialAnalysis"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["steps"][0]["materialAnalysis"]["unknownShellExecuted"] is False
    assert payload["data"]["workflowRun"]["workflowId"] == "phase1_main_demo"
    assert payload["data"]["workflowRun"]["status"] == "COMPLETED"
    assert payload["data"]["workflowRun"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["workflowRun"]["realLlmCalled"] is False
    assert payload["data"]["workflowRun"]["sandboxExecuted"] is False
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} >= {
        "MATERIAL_ANALYSIS",
        "LAB_DSL",
        "EXAM_DSL",
        "GRADING_DSL",
        "PPT_DSL",
        "WORKFLOW_REPORT",
    }
    assert all(artifact["workflowRunId"] == payload["data"]["workflowRun"]["id"] for artifact in payload["data"]["artifacts"])
    assert [step["name"] for step in payload["data"]["workflowRun"]["steps"][:4]] == [
        "generate_lab_dsl",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "generate_ppt_dsl",
    ]
    assert all("taskId" in step["detail"] for step in payload["data"]["workflowRun"]["steps"][:4])
    assert all("providerCallAuditEvent" in step["detail"] for step in payload["data"]["workflowRun"]["steps"][:4])

    audit_exit, audit_payload = run_cli(
        ["provider", "audit", "--operation", "generateJson", "--trace-id", payload["traceId"]],
        capsys,
    )
    assert audit_exit == 0
    assert audit_payload["data"]["total"] == 4
    assert {item["detail"]["workflowId"] for item in audit_payload["data"]["items"]} == {"phase1_main_demo"}
    assert {item["detail"]["workflowStep"] for item in audit_payload["data"]["items"]} == {
        "generate_lab_dsl",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "generate_ppt_dsl",
    }


def test_workflow_list_and_get_returns_run_log(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "workflow-report.json"
    _, demo = run_cli(
        [
            "workflow",
            "demo",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
        ],
        capsys,
    )
    run_id = demo["data"]["workflowRun"]["id"]

    exit_code, listed = run_cli(["workflow", "list", "--workflow-id", "phase1_main_demo", "--status", "COMPLETED"], capsys)
    _, fetched = run_cli(["workflow", "get", "--id", run_id], capsys)

    assert exit_code == 0
    assert_json_envelope(listed)
    assert listed["data"]["total"] == 1
    assert listed["data"]["items"][0]["id"] == run_id
    assert listed["data"]["items"][0]["steps"][0]["name"] == "generate_lab_dsl"
    assert fetched["data"]["workflowRun"]["id"] == run_id
    assert fetched["data"]["workflowRun"]["publishBlockedUntilApproved"] is True


def test_artifact_list_filters_by_workflow_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    _, demo = run_cli(
        [
            "workflow",
            "demo",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
        ],
        capsys,
    )
    run_id = demo["data"]["workflowRun"]["id"]

    exit_code, payload = run_cli(["artifact", "list", "--workflow-run-id", run_id], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["total"] == len(demo["data"]["artifacts"])
    assert {item["workflowRunId"] for item in payload["data"]["items"]} == {run_id}


def test_workflow_get_missing_run_returns_json(capsys):
    exit_code, payload = run_cli(["workflow", "get", "--id", "workflow_run_missing"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"][0]["field"] == "id"


def test_workflow_report_reads_saved_report(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "workflow-report.json"
    run_cli(
        [
            "workflow",
            "demo",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    exit_code, payload = run_cli(["workflow", "report", "--file", str(report_path)], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["report"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["report"]["reviewRequired"] is True


def test_workflow_report_missing_file_returns_json(capsys):
    exit_code, payload = run_cli(["workflow", "report", "--file", "missing-report.json"], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "file"
