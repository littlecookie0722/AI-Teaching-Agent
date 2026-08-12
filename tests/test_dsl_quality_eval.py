from __future__ import annotations

import json
import shutil
from pathlib import Path

from quality.dsl_quality_eval import run_dsl_quality_eval


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "evals/dsl_quality/v1"


def test_default_corpus_has_balanced_coverage_and_passes_all_metrics():
    first = run_dsl_quality_eval(root=ROOT)
    second = run_dsl_quality_eval(root=ROOT)

    assert first == second
    assert first["success"] is True
    assert first["summary"]["caseTotal"] == 20
    assert first["summary"]["passedTotal"] == 20
    assert first["summary"]["failedTotal"] == 0
    assert first["coverage"]["languages"] == {"en": 10, "zh": 10}
    assert first["coverage"]["variants"] == {"boundary": 10, "normal": 10}
    assert len(first["coverage"]["domains"]) == 5
    assert set(first["summary"]["metricPassedTotals"].values()) == {20}
    assert all(case["artifactRefs"]["lab"]["schemaValidated"] for case in first["cases"])


def test_report_writer_is_stable_json(tmp_path: Path):
    output = tmp_path / "dsl-quality-report.json"

    report = run_dsl_quality_eval(root=ROOT, output_path=output)

    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert output.read_text(encoding="utf-8").endswith("\n")


def test_runner_detects_status_schema_score_reference_and_candidate_leaks(tmp_path: Path):
    corpus = tmp_path / "corpus"
    shutil.copytree(CORPUS, corpus)
    manifest_path = corpus / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    baseline_path = corpus / Path(manifest["baselineBundle"]).name

    for case in manifest["cases"]:
        case.setdefault("overrides", {})["/lab/status"] = "APPROVED"
        case["overrides"]["/ppt/metadata/durationMinutes"] = True
        case["overrides"]["/exam/spec/questions/0/gradingRef"] = "missing_check"
        case["expected"]["totalScore"] = 999
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate_questions = baseline["candidatePreview"].get("questions")
    if not isinstance(candidate_questions, list):
        candidate_questions = baseline["candidatePreview"]["spec"]["questions"]
    candidate_questions[0]["answer"] = "INTERNAL-ANSWER-DO-NOT-EXPOSE"
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")

    report = run_dsl_quality_eval(root=ROOT, manifest_path=manifest_path)

    assert report["success"] is False
    assert report["summary"]["failedTotal"] == 20
    totals = report["summary"]["metricPassedTotals"]
    assert totals["reviewGated"] == 0
    assert totals["schemaValid"] == 0
    assert totals["scoreConsistent"] == 0
    assert totals["gradingReferencesCovered"] == 0
    assert totals["candidatePreviewSafe"] == 0
    assert {
        "reviewGated",
        "schemaValid",
        "scoreConsistent",
        "gradingReferencesCovered",
        "candidatePreviewSafe",
    } <= {failure["metric"] for failure in report["cases"][0]["failures"]}
