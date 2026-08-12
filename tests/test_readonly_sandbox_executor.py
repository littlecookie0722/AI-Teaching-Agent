import json
from pathlib import Path

from cli.dsl import load_schema, load_yaml, validate_dsl
from sandbox.grade_runner import build_grading_report_detail
from sandbox.readonly_sandbox_executor import ReadonlySandboxExecutorError, build_readonly_sandbox_report


ROOT = Path(__file__).resolve().parents[1]


def load_readonly_grading():
    grading = load_yaml(ROOT / "templates/grading/examples/readonly-sandbox.yaml")
    validate_dsl(grading, load_schema("grading", ROOT))
    return grading


def test_readonly_sandbox_executes_static_file_checks_only():
    report = build_readonly_sandbox_report(
        load_readonly_grading(),
        ROOT / "examples/submissions/readonly-demo",
        "trace_readonly",
    )

    assert report["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert report["runner"]["supportedCheckTypes"] == ["file_exists", "json_field", "notebook_cell", "log_keyword"]
    assert report["executionSummary"]["total"] == 5
    assert report["executionSummary"]["executed"] == 4
    assert report["executionSummary"]["passed"] == 4
    assert report["executionSummary"]["deferred"] == 1
    assert report["checkSummary"]["executed"] == 4
    assert report["checkSummary"]["plannedOnly"] == 1
    assert report["checkSummary"]["scoreTotalMatchesSpec"] is True
    assert report["score"]["executableScore"] == 120
    assert report["score"]["earnedScore"] == 120
    assert report["score"]["deferredScore"] == 30
    assert report["totalScore"] == 150
    assert report["earnedScore"] == 120
    assert report["assessmentPlanSummary"]["source"] == "grading.spec.assessmentPlan"
    assert report["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert report["explainability"]["status"] == "READONLY_EVIDENCE_PARTIAL"
    assert report["explainability"]["readonlyEvidenceCollected"] is True
    assert report["sandboxPolicy"]["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert report["sandboxPolicy"]["readonlyOnly"] is True
    assert report["safety"]["sandboxExecuted"] is True
    assert report["safety"]["readonlyOnly"] is True
    assert report["safety"]["contestantCodeExecuted"] is False
    assert report["safety"]["commandExecuted"] is False
    assert report["safety"]["pytestExecuted"] is False
    assert report["safety"]["notebookExecuted"] is False
    checks = {check["id"]: check for check in report["checks"]}
    assert checks["check_result_file"]["status"] == "PASSED"
    assert checks["check_result_file"]["evidence"]["exists"] is True
    assert checks["check_result_file"]["readonlyEvidence"]["status"] == "COLLECTED"
    assert checks["check_result_file"]["sandboxExecutionRequest"]["mode"] == "REAL_SANDBOX_REQUIRED"
    assert checks["check_result_file"]["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY"
    assert checks["check_result_file"]["assessmentPlanAlignedWithCheck"] is True
    assert checks["check_accuracy_metric"]["status"] == "PASSED"
    assert checks["check_accuracy_metric"]["evidence"]["actualValue"] == 0.9
    assert checks["check_accuracy_metric"]["readonlyEvidence"]["actualValue"] == 0.9
    assert checks["check_notebook_static"]["status"] == "PASSED"
    assert checks["check_notebook_static"]["evidence"]["method"] == "STATIC_NOTEBOOK_JSON_PARSE"
    assert checks["check_notebook_static"]["readonlyEvidence"]["kind"] == "notebook_cell_static_parse"
    assert checks["check_notebook_static"]["readonlyEvidence"]["matchedTokens"] == ["review-safe notebook evidence"]
    assert checks["check_notebook_static"]["readonlyEvidence"]["notebookKernelStarted"] is False
    assert checks["check_notebook_static"]["readonlyEvidence"]["notebookExecuted"] is False
    assert checks["check_notebook_static"]["readonlyEvidence"]["contestantCodeExecuted"] is False
    assert checks["check_training_log"]["status"] == "PASSED"
    assert checks["check_training_log"]["evidence"]["method"] == "STATIC_LOG_TEXT_SCAN"
    assert checks["check_training_log"]["readonlyEvidence"]["kind"] == "log_keyword_static_scan"
    assert checks["check_training_log"]["readonlyEvidence"]["matchedTokens"] == ["training complete"]
    assert checks["check_training_log"]["readonlyEvidence"]["contestantCodeExecuted"] is False
    assert checks["check_training_log"]["readonlyEvidence"]["commandExecuted"] is False
    assert checks["check_pytest_deferred"]["status"] == "DEFERRED"
    assert checks["check_pytest_deferred"]["sandboxExecuted"] is False
    assert checks["check_pytest_deferred"]["readonlyEvidence"]["status"] == "NOT_COLLECTED"
    detail = build_grading_report_detail(report)
    assert detail["source"] == "sandbox.grade_runner.build_grading_report_detail"
    assert detail["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert detail["checkSummary"]["executed"] == 4
    assert detail["checkPlans"][0]["readonlyEvidence"]["status"] == "COLLECTED"
    assert detail["checkPlans"][2]["readonlyEvidence"]["method"] == "STATIC_NOTEBOOK_JSON_PARSE"
    assert detail["checkPlans"][3]["readonlyEvidence"]["method"] == "STATIC_LOG_TEXT_SCAN"
    assert detail["checkPlans"][4]["status"] == "DEFERRED"
    assert detail["safety"]["sandboxExecuted"] is True
    assert detail["safety"]["contestantCodeExecuted"] is False


def test_readonly_sandbox_blocks_paths_outside_submission(tmp_path):
    (tmp_path / "submission").mkdir()
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    grading = load_readonly_grading()
    grading["spec"]["checks"] = [
        {
            "id": "check_escape",
            "type": "file_exists",
            "path": "../secret.txt",
            "score": 100,
        }
    ]
    grading["spec"]["totalScore"] = 100

    report = build_readonly_sandbox_report(grading, tmp_path / "submission", "trace_escape")
    check = report["checks"][0]

    assert check["status"] == "FAILED"
    assert check["passed"] is False
    assert check["error"]["code"] == "PATH_OUTSIDE_SUBMISSION"
    assert check["evidence"]["filesInspected"] == []
    assert check["contestantCodeExecuted"] is False
    assert check["commandExecuted"] is False


def test_readonly_sandbox_rejects_missing_submission_directory(tmp_path):
    try:
        build_readonly_sandbox_report(load_readonly_grading(), tmp_path / "missing", "trace_missing")
    except ReadonlySandboxExecutorError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "submission"
    else:
        raise AssertionError("expected ReadonlySandboxExecutorError")


def test_readonly_sandbox_reports_json_mismatch(tmp_path):
    submission = tmp_path / "submission"
    submission.mkdir()
    (submission / "metrics.json").write_text(json.dumps({"accuracy": 0.7}), encoding="utf-8")
    grading = load_readonly_grading()
    grading["spec"]["checks"] = [
        {
            "id": "check_accuracy_metric",
            "type": "json_field",
            "path": "metrics.json",
            "jsonPath": "$.accuracy",
            "expectedValue": 0.9,
            "score": 100,
        }
    ]
    grading["spec"]["totalScore"] = 100

    report = build_readonly_sandbox_report(grading, submission, "trace_json_mismatch")
    check = report["checks"][0]

    assert check["status"] == "FAILED"
    assert check["passed"] is False
    assert check["evidence"]["actualValue"] == 0.7
    assert check["evidence"]["expectedValue"] == 0.9


def test_readonly_sandbox_reports_static_notebook_token_mismatch(tmp_path):
    submission = tmp_path / "submission"
    notebook_dir = submission / "notebooks"
    notebook_dir.mkdir(parents=True)
    (notebook_dir / "analysis.ipynb").write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "source": ["This notebook has another answer."],
                        "metadata": {},
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )
    grading = load_readonly_grading()
    grading["spec"]["checks"] = [
        {
            "id": "check_notebook_static",
            "type": "notebook_cell",
            "notebookPath": "notebooks/analysis.ipynb",
            "cellIndex": 0,
            "expected": ["expected answer token"],
            "score": 100,
        }
    ]
    grading["spec"]["totalScore"] = 100

    report = build_readonly_sandbox_report(grading, submission, "trace_notebook_mismatch")
    check = report["checks"][0]

    assert check["status"] == "FAILED"
    assert check["passed"] is False
    assert check["evidence"]["method"] == "STATIC_NOTEBOOK_JSON_PARSE"
    assert check["evidence"]["matchedTokens"] == []
    assert check["evidence"]["missingTokens"] == ["expected answer token"]
    assert check["readonlyEvidence"]["notebookKernelStarted"] is False
    assert check["readonlyEvidence"]["notebookExecuted"] is False
    assert check["readonlyEvidence"]["commandExecuted"] is False


def test_readonly_sandbox_reports_log_keyword_mismatch(tmp_path):
    submission = tmp_path / "submission"
    log_dir = submission / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "train.log").write_text("epoch=1 accuracy=0.72\nstill running\n", encoding="utf-8")
    grading = load_readonly_grading()
    grading["spec"]["checks"] = [
        {
            "id": "check_training_log",
            "type": "log_keyword",
            "path": "logs/train.log",
            "expected": ["training complete"],
            "score": 100,
        }
    ]
    grading["spec"]["totalScore"] = 100

    report = build_readonly_sandbox_report(grading, submission, "trace_log_mismatch")
    check = report["checks"][0]

    assert check["status"] == "FAILED"
    assert check["passed"] is False
    assert check["evidence"]["method"] == "STATIC_LOG_TEXT_SCAN"
    assert check["evidence"]["matchedTokens"] == []
    assert check["evidence"]["missingTokens"] == ["training complete"]
    assert check["readonlyEvidence"]["kind"] == "log_keyword_static_scan"
    assert check["readonlyEvidence"]["contestantCodeExecuted"] is False
    assert check["readonlyEvidence"]["commandExecuted"] is False
