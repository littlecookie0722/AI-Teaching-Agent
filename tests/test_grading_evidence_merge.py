import json
from pathlib import Path

from cli.dsl import load_schema, load_yaml, validate_dsl
from sandbox.controlled_command_executor import build_controlled_command_sandbox_report
from sandbox.evidence_merge import build_grading_evidence_merge_report
from sandbox.evidence_readiness import build_grading_evidence_readiness
from sandbox.readonly_sandbox_executor import build_readonly_sandbox_report


ROOT = Path(__file__).resolve().parents[1]


def load_grading(name: str):
    grading = load_yaml(ROOT / f"templates/grading/examples/{name}")
    validate_dsl(grading, load_schema("grading", ROOT))
    return grading


def write_mixed_submission(path: Path) -> Path:
    path.mkdir()
    (path / "result.csv").write_text("id,accuracy\n1,0.90\n", encoding="utf-8")
    (path / "metrics.json").write_text('{"accuracy": 0.9}', encoding="utf-8")
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


def test_grading_evidence_merge_combines_readonly_and_controlled_reports(tmp_path, monkeypatch):
    def fake_run(args, **kwargs):
        import subprocess

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
    source_grading = load_grading("mixed-checks.yaml")
    controlled_grading = load_grading("mixed-checks.yaml")
    controlled_grading["spec"]["checks"] = [
        check for check in controlled_grading["spec"]["checks"] if check["type"] in {"stdout_contains", "pytest"}
    ]
    for check in controlled_grading["spec"]["checks"]:
        if check["type"] == "pytest":
            check["path"] = "checks/check_main.py"
    controlled_grading["spec"]["assessmentPlan"] = [
        plan for plan in controlled_grading["spec"]["assessmentPlan"] if plan["type"] in {"stdout_contains", "pytest"}
    ]
    controlled_grading["spec"]["totalScore"] = 50

    readonly = build_readonly_sandbox_report(
        source_grading,
        write_mixed_submission(tmp_path / "mixed-submission"),
        "trace_merge_readonly",
    )
    controlled = build_controlled_command_sandbox_report(
        controlled_grading,
        ROOT / "examples/submissions/controlled-command-demo",
        "trace_merge_controlled",
        image="local-python:demo",
    )

    merged = build_grading_evidence_merge_report(
        [readonly, controlled],
        report_paths=["readonly.json", "controlled.json"],
        trace_id="trace_merge",
    )

    assert merged["mode"] == "GRADING_EVIDENCE_MERGE_REPORT"
    assert merged["sourceReportTotal"] == 2
    assert merged["summary"]["checkTotal"] == 6
    assert merged["summary"]["executed"] == 6
    assert merged["summary"]["passedCheckTotal"] == 6
    assert merged["summary"]["failedCheckTotal"] == 0
    assert merged["summary"]["deferredCheckTotal"] == 0
    assert merged["summary"]["passed"] is True
    assert merged["summary"]["totalScore"] == 100
    assert merged["summary"]["earnedScore"] == 100
    assert merged["evidenceCoverage"]["controlledDocker"]["score"] == 50
    assert merged["evidenceCoverage"]["readonlyStatic"]["score"] == 50
    assert merged["evidenceCoverage"]["coverageRatio"] == 1.0
    assert merged["safety"]["sandboxExecuted"] is True
    assert merged["safety"]["contestantCodeExecuted"] is True
    assert merged["safety"]["commandExecuted"] is True
    assert merged["safety"]["networkEnabled"] is False
    assert merged["safety"]["autoApproveAllowed"] is False
    assert merged["safety"]["realPublishAllowed"] is False
    assert {item["checkId"] for item in merged["mergeWarnings"]} == {"check_stdout_accuracy", "check_pytest"}
    assert {item["reason"] for item in merged["mergeWarnings"]} == {"higher_evidence_rank_selected"}


def test_grading_evidence_readiness_summarizes_existing_reports_without_execution():
    readiness = build_grading_evidence_readiness(
        [
            {
                "id": "readonly_report",
                "mode": "READONLY_REAL_SANDBOX_POC",
                "checks": [
                    {
                        "id": "check_static_json",
                        "type": "json_field",
                        "status": "PASSED",
                        "passed": True,
                        "score": 40,
                        "earnedScore": 40,
                    },
                    {
                        "id": "check_pending_pytest",
                        "type": "pytest",
                        "status": "DEFERRED",
                        "score": 60,
                        "earnedScore": 0,
                    },
                ],
                "safety": {
                    "sandboxExecuted": False,
                    "contestantCodeExecuted": False,
                    "commandExecuted": False,
                    "networkEnabled": False,
                },
            }
        ],
        report_paths=["readonly.json"],
        trace_id="trace_readiness",
    )

    assert readiness["mode"] == "GRADING_EVIDENCE_READINESS"
    assert readiness["summary"]["checkTotal"] == 2
    assert readiness["summary"]["evidenceReadyTotal"] == 1
    assert readiness["summary"]["missingEvidenceTotal"] == 1
    assert readiness["summary"]["controlledCommandMissingTotal"] == 1
    assert readiness["summary"]["coverageRatio"] == 0.4
    assert readiness["summary"]["readyForApprovalRecommendation"] is False
    assert readiness["items"][0]["recommendedAction"] == "verify_static_evidence_and_score"
    missing = next(item for item in readiness["items"] if item["checkId"] == "check_pending_pytest")
    assert missing["recommendedNextEvidence"] == "controlled_command_evidence"
    assert missing["recommendedAction"] == "run_controlled_command_evidence_after_review"
    assert readiness["nextActions"][0]["id"] == "run_controlled_command_evidence_after_review"
    assert readiness["safety"]["readExistingReportsOnly"] is True
    assert readiness["safety"]["sandboxExecutedByReadiness"] is False
    assert readiness["safety"]["contestantCodeExecutedByReadiness"] is False
