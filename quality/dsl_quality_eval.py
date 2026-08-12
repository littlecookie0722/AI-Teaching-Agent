"""Deterministic offline quality evaluation for linked teaching DSL bundles."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Iterable

from cli.dsl import DslValidationError, validate_dsl


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = ROOT / "evals/dsl_quality/v1/manifest.json"
REPORT_VERSION = "dsl-quality-eval-report-v1"
REQUIRED_ARTIFACTS = ("lab", "exam", "grading", "ppt")
FORBIDDEN_CANDIDATE_KEYS = {"answer", "gradingref"}
PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Za-z][A-Za-z0-9_]*)\}\}")


class DslQualityEvalError(ValueError):
    """Raised when the corpus configuration cannot be evaluated safely."""

    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def run_dsl_quality_eval(
    *,
    root: Path = ROOT,
    manifest_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Evaluate every sanitized corpus case and optionally write stable JSON."""

    root = root.resolve()
    manifest_file = (manifest_path or root / "evals/dsl_quality/v1/manifest.json").resolve()
    manifest = _load_json_object(manifest_file, field="manifest")
    manifest_schema_file = manifest_file.parent / "manifest.schema.json"
    manifest_schema = _load_json_object(manifest_schema_file, field="manifestSchema")

    try:
        validate_dsl(manifest, manifest_schema)
    except DslValidationError as exc:
        raise DslQualityEvalError(
            "DSL_QUALITY_MANIFEST_INVALID",
            "DSL 质量语料 manifest 未通过 Schema 校验",
            exc.errors,
        ) from exc

    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise DslQualityEvalError(
            "DSL_QUALITY_MANIFEST_INVALID",
            "DSL 质量语料没有可评测 case",
            [{"field": "$.cases", "reason": "expected non-empty array"}],
        )
    case_ids = [str(case.get("id", "")) for case in cases if isinstance(case, dict)]
    duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    if duplicates:
        raise DslQualityEvalError(
            "DSL_QUALITY_MANIFEST_INVALID",
            "DSL 质量语料 case id 必须唯一",
            [{"field": "$.cases", "reason": f"duplicate case id: {case_id}"} for case_id in duplicates],
        )

    baseline_ref = manifest.get("baselineBundle")
    if not isinstance(baseline_ref, str) or not baseline_ref.strip():
        raise DslQualityEvalError(
            "DSL_QUALITY_MANIFEST_INVALID",
            "DSL 质量语料缺少 baseline bundle",
            [{"field": "$.baselineBundle", "reason": "expected non-empty string"}],
        )
    baseline_reference = Path(baseline_ref)
    if baseline_reference.is_absolute():
        baseline_file = baseline_reference.resolve()
    else:
        manifest_relative = (manifest_file.parent / baseline_reference).resolve()
        root_relative = (root / baseline_reference).resolve()
        baseline_file = manifest_relative if manifest_relative.exists() or not root_relative.exists() else root_relative
    baseline = _load_json_object(baseline_file, field="baselineBundle")
    _require_bundle_shape(baseline)

    schema_by_kind = {
        kind: _load_json_object(root / "templates" / kind / f"{kind}.schema.json", field=f"schema.{kind}")
        for kind in REQUIRED_ARTIFACTS
    }
    case_reports = [
        _evaluate_case(case, baseline=baseline, schema_by_kind=schema_by_kind)
        for case in sorted(cases, key=lambda item: str(item["id"]))
    ]
    report = _build_report(
        manifest=manifest,
        manifest_file=manifest_file,
        baseline_file=baseline_file,
        root=root,
        case_reports=case_reports,
    )
    if output_path is not None:
        write_dsl_quality_report(report, output_path)
    return report


def write_dsl_quality_report(report: dict[str, Any], output_path: Path) -> None:
    """Write a deterministic UTF-8 report with stable formatting."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _evaluate_case(
    case: dict[str, Any],
    *,
    baseline: dict[str, Any],
    schema_by_kind: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    bundle = _materialize_case_bundle(case, baseline)
    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
    failures: list[dict[str, str]] = []

    schema_errors: dict[str, list[dict[str, str]]] = {}
    for kind in REQUIRED_ARTIFACTS:
        try:
            validate_dsl(bundle[kind], schema_by_kind[kind])
        except DslValidationError as exc:
            schema_errors[kind] = exc.errors
            for error in exc.errors:
                failures.append(
                    {
                        "metric": "schemaValid",
                        "field": f"$.{kind}{error['field'][1:]}",
                        "reason": error["reason"],
                    }
                )
    schema_valid = not schema_errors

    statuses = {kind: _nested(bundle[kind], "status") for kind in REQUIRED_ARTIFACTS}
    review_gated = all(status == "WAITING_REVIEW" for status in statuses.values())
    if not review_gated:
        for kind, status in statuses.items():
            if status != "WAITING_REVIEW":
                failures.append(
                    {
                        "metric": "reviewGated",
                        "field": f"$.{kind}.status",
                        "reason": f"expected WAITING_REVIEW, got {status!r}",
                    }
                )

    cross_links_valid, cross_link_failures = _evaluate_cross_links(bundle)
    failures.extend(cross_link_failures)

    score_consistent, score_summary, score_failures = _evaluate_scores(bundle, expected)
    failures.extend(score_failures)

    grading_refs_covered, reference_summary, reference_failures = _evaluate_grading_references(bundle)
    failures.extend(reference_failures)

    candidate_safe, candidate_summary, candidate_failures = _evaluate_candidate_preview(bundle)
    failures.extend(candidate_failures)

    lab_complete, lab_summary, lab_failures = _evaluate_lab_content(bundle["lab"], expected)
    failures.extend(lab_failures)

    ppt_complete, ppt_summary, ppt_failures = _evaluate_ppt_content(bundle["ppt"], expected)
    failures.extend(ppt_failures)

    metrics = {
        "schemaValid": schema_valid,
        "reviewGated": review_gated,
        "crossArtifactLinksValid": cross_links_valid,
        "scoreConsistent": score_consistent,
        "gradingReferencesCovered": grading_refs_covered,
        "candidatePreviewSafe": candidate_safe,
        "labContentComplete": lab_complete,
        "pptContentComplete": ppt_complete,
    }
    artifact_refs = {
        kind: {
            "kind": _nested(bundle[kind], "kind"),
            "id": _nested(bundle[kind], "metadata", "id"),
            "status": statuses[kind],
            "schemaValidated": kind not in schema_errors,
        }
        for kind in REQUIRED_ARTIFACTS
    }
    artifact_refs["candidatePreview"] = {
        "questionTotal": candidate_summary["candidateQuestionTotal"],
        "answerSafe": candidate_safe,
    }
    return {
        "id": case["id"],
        "domain": case["domain"],
        "language": case["language"],
        "variant": case["variant"],
        "inputRef": case["inputRef"],
        "success": all(metrics.values()),
        "artifactRefs": artifact_refs,
        "metrics": metrics,
        "details": {
            "score": score_summary,
            "references": reference_summary,
            "candidateSafety": candidate_summary,
            "labContent": lab_summary,
            "pptContent": ppt_summary,
        },
        "failures": failures,
    }


def _materialize_case_bundle(case: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    variables: dict[str, Any] = {
        "caseId": case["id"],
        "domain": case["domain"],
        "language": case["language"],
        "variant": case["variant"],
    }
    configured_variables = case.get("variables")
    if isinstance(configured_variables, dict):
        variables.update(configured_variables)
    rendered = _render_value(copy.deepcopy(baseline), variables)
    overrides = case.get("overrides") or {}
    if not isinstance(overrides, dict):
        raise DslQualityEvalError(
            "DSL_QUALITY_MANIFEST_INVALID",
            "DSL 质量语料 overrides 必须是对象",
            [{"field": f"$.cases[{case['id']}].overrides", "reason": "expected object"}],
        )
    for pointer, value in sorted(overrides.items()):
        _apply_json_pointer(rendered, str(pointer), _render_value(copy.deepcopy(value), variables), case_id=case["id"])
    _require_bundle_shape(rendered)
    unresolved = _find_unresolved_placeholders(rendered)
    if unresolved:
        raise DslQualityEvalError(
            "DSL_QUALITY_MANIFEST_INVALID",
            "DSL 质量语料存在未解析占位符",
            [{"field": f"$.cases[{case['id']}].variables", "reason": value} for value in unresolved],
        )
    return rendered


def _evaluate_cross_links(bundle: dict[str, Any]) -> tuple[bool, list[dict[str, str]]]:
    expected = {
        "$.exam.metadata.sourceLabId": _nested(bundle["lab"], "metadata", "id"),
        "$.grading.metadata.sourceExamId": _nested(bundle["exam"], "metadata", "id"),
        "$.lab.spec.grading.ref": _nested(bundle["grading"], "metadata", "id"),
    }
    actual = {
        "$.exam.metadata.sourceLabId": _nested(bundle["exam"], "metadata", "sourceLabId"),
        "$.grading.metadata.sourceExamId": _nested(bundle["grading"], "metadata", "sourceExamId"),
        "$.lab.spec.grading.ref": _nested(bundle["lab"], "spec", "grading", "ref"),
    }
    failures = [
        {"metric": "crossArtifactLinksValid", "field": field, "reason": f"expected {expected[field]!r}"}
        for field in expected
        if actual[field] != expected[field]
    ]
    return not failures, failures


def _evaluate_scores(
    bundle: dict[str, Any], expected: dict[str, Any]
) -> tuple[bool, dict[str, Any], list[dict[str, str]]]:
    questions = _list_at(bundle["exam"], "spec", "questions")
    checks = _list_at(bundle["grading"], "spec", "checks")
    plan = _list_at(bundle["grading"], "spec", "assessmentPlan")
    totals = {
        "expected": expected.get("totalScore"),
        "examDeclared": _nested(bundle["exam"], "spec", "totalScore"),
        "questionSum": _integer_sum(questions, "score"),
        "gradingDeclared": _nested(bundle["grading"], "spec", "totalScore"),
        "checkSum": _integer_sum(checks, "score"),
        "assessmentPlanSum": _integer_sum(plan, "score"),
    }
    values = list(totals.values())
    consistent = all(isinstance(value, int) and not isinstance(value, bool) for value in values) and len(set(values)) == 1
    failures = [] if consistent else [
        {
            "metric": "scoreConsistent",
            "field": "$.exam.spec.totalScore",
            "reason": "expected declared totals and item sums to match",
        }
    ]
    return consistent, totals, failures


def _evaluate_grading_references(
    bundle: dict[str, Any],
) -> tuple[bool, dict[str, Any], list[dict[str, str]]]:
    questions = _list_at(bundle["exam"], "spec", "questions")
    checks = _list_at(bundle["grading"], "spec", "checks")
    plan = _list_at(bundle["grading"], "spec", "assessmentPlan")
    question_refs = [item.get("gradingRef") for item in questions if isinstance(item, dict)]
    check_ids = [item.get("id") for item in checks if isinstance(item, dict)]
    plan_ids = [item.get("checkId") for item in plan if isinstance(item, dict)]
    non_empty_refs = all(isinstance(value, str) and bool(value.strip()) for value in question_refs)
    unique_ids = len(check_ids) == len(set(check_ids)) and len(plan_ids) == len(set(plan_ids))
    covered = (
        non_empty_refs
        and unique_ids
        and set(question_refs).issubset(set(check_ids))
        and set(check_ids) == set(plan_ids)
    )
    summary = {
        "questionRefs": sorted(str(value) for value in question_refs),
        "checkIds": sorted(str(value) for value in check_ids),
        "assessmentPlanIds": sorted(str(value) for value in plan_ids),
        "missingCheckRefs": sorted(str(value) for value in set(question_refs) - set(check_ids)),
    }
    failures = [] if covered else [
        {
            "metric": "gradingReferencesCovered",
            "field": "$.exam.spec.questions[].gradingRef",
            "reason": "expected every question ref to resolve and checks to match assessmentPlan",
        }
    ]
    return covered, summary, failures


def _evaluate_candidate_preview(
    bundle: dict[str, Any],
) -> tuple[bool, dict[str, Any], list[dict[str, str]]]:
    candidate = bundle["candidatePreview"]
    forbidden_paths = sorted(_find_forbidden_keys(candidate))
    questions = _list_at(bundle["exam"], "spec", "questions")
    sensitive_values: set[str] = set()
    for question in questions:
        if not isinstance(question, dict):
            continue
        sensitive_values.update(_string_leaves(question.get("answer")))
        grading_ref = question.get("gradingRef")
        if isinstance(grading_ref, str) and grading_ref:
            sensitive_values.add(grading_ref)
    candidate_strings = _string_leaves(candidate)
    leaked_values = sorted(sensitive_values & candidate_strings)
    candidate_questions = _candidate_questions(candidate)
    exam_ids = [item.get("id") for item in questions if isinstance(item, dict)]
    candidate_ids = [item.get("id") for item in candidate_questions if isinstance(item, dict)]
    question_coverage = exam_ids == candidate_ids
    safe = not forbidden_paths and not leaked_values and question_coverage
    summary = {
        "candidateQuestionTotal": len(candidate_questions),
        "sourceQuestionTotal": len(questions),
        "forbiddenKeyPaths": forbidden_paths,
        "leakedSensitiveValues": leaked_values,
        "questionCoverage": question_coverage,
    }
    failures: list[dict[str, str]] = []
    if forbidden_paths:
        failures.append(
            {
                "metric": "candidatePreviewSafe",
                "field": forbidden_paths[0],
                "reason": "candidate preview contains answer or gradingRef key",
            }
        )
    if leaked_values:
        failures.append(
            {
                "metric": "candidatePreviewSafe",
                "field": "$.candidatePreview",
                "reason": "candidate preview contains an answer or internal grading reference value",
            }
        )
    if not question_coverage:
        failures.append(
            {
                "metric": "candidatePreviewSafe",
                "field": "$.candidatePreview.questions",
                "reason": "candidate question ids do not match source exam order",
            }
        )
    return safe, summary, failures


def _evaluate_lab_content(
    lab: dict[str, Any], expected: dict[str, Any]
) -> tuple[bool, dict[str, Any], list[dict[str, str]]]:
    objectives = _list_at(lab, "spec", "objectives")
    steps = _list_at(lab, "spec", "steps")
    minimum_objectives = expected.get("minimumObjectives", 1)
    minimum_steps = expected.get("minimumSteps", 1)
    objective_text_complete = all(isinstance(item, str) and bool(item.strip()) for item in objectives)
    step_text_complete = all(
        isinstance(step, dict)
        and all(isinstance(step.get(key), str) and bool(step[key].strip()) for key in ("title", "instruction", "expectedResult"))
        for step in steps
    )
    complete = (
        isinstance(minimum_objectives, int)
        and isinstance(minimum_steps, int)
        and len(objectives) >= minimum_objectives
        and len(steps) >= minimum_steps
        and objective_text_complete
        and step_text_complete
    )
    summary = {
        "objectiveTotal": len(objectives),
        "minimumObjectives": minimum_objectives,
        "stepTotal": len(steps),
        "minimumSteps": minimum_steps,
        "allRequiredTextPresent": objective_text_complete and step_text_complete,
    }
    failures = [] if complete else [
        {
            "metric": "labContentComplete",
            "field": "$.lab.spec",
            "reason": "expected minimum objectives/steps and non-empty step outcomes",
        }
    ]
    return complete, summary, failures


def _evaluate_ppt_content(
    ppt: dict[str, Any], expected: dict[str, Any]
) -> tuple[bool, dict[str, Any], list[dict[str, str]]]:
    slides = _list_at(ppt, "spec", "slides")
    minimum_slides = expected.get("minimumSlides", 1)
    titles_complete = all(
        isinstance(slide, dict) and isinstance(slide.get("title"), str) and bool(slide["title"].strip())
        for slide in slides
    )
    complete = isinstance(minimum_slides, int) and len(slides) >= minimum_slides and titles_complete
    summary = {
        "slideTotal": len(slides),
        "minimumSlides": minimum_slides,
        "allTitlesPresent": titles_complete,
    }
    failures = [] if complete else [
        {
            "metric": "pptContentComplete",
            "field": "$.ppt.spec.slides",
            "reason": "expected minimum slides and non-empty titles",
        }
    ]
    return complete, summary, failures


def _build_report(
    *,
    manifest: dict[str, Any],
    manifest_file: Path,
    baseline_file: Path,
    root: Path,
    case_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    metric_names = list(case_reports[0]["metrics"])
    metric_totals = {
        metric: sum(1 for case in case_reports if case["metrics"][metric])
        for metric in metric_names
    }
    passed_total = sum(1 for case in case_reports if case["success"])
    case_total = len(case_reports)
    return {
        "version": REPORT_VERSION,
        "mode": "OFFLINE_SANITIZED_DSL_CORPUS",
        "corpusVersion": manifest["version"],
        "manifest": _display_path(manifest_file, root),
        "baselineBundle": _display_path(baseline_file, root),
        "success": passed_total == case_total,
        "summary": {
            "caseTotal": case_total,
            "passedTotal": passed_total,
            "failedTotal": case_total - passed_total,
            "passRate": round(passed_total / case_total, 4),
            "metricPassedTotals": metric_totals,
        },
        "coverage": {
            "domains": _count(case["domain"] for case in case_reports),
            "languages": _count(case["language"] for case in case_reports),
            "variants": _count(case["variant"] for case in case_reports),
        },
        "cases": case_reports,
        "safety": {
            "sanitizedFixtureData": True,
            "networkAccess": False,
            "realLlmCalled": False,
            "learnerCodeExecuted": False,
            "autoPublishAllowed": False,
        },
    }


def _load_json_object(path: Path, *, field: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DslQualityEvalError(
            "DSL_QUALITY_FILE_NOT_FOUND",
            "DSL 质量评测文件不存在",
            [{"field": field, "reason": str(path)}],
        ) from exc
    except json.JSONDecodeError as exc:
        raise DslQualityEvalError(
            "DSL_QUALITY_JSON_INVALID",
            "DSL 质量评测文件不是合法 JSON",
            [{"field": field, "reason": f"line {exc.lineno}, column {exc.colno}"}],
        ) from exc
    if not isinstance(value, dict):
        raise DslQualityEvalError(
            "DSL_QUALITY_JSON_INVALID",
            "DSL 质量评测文件必须是 JSON object",
            [{"field": field, "reason": "expected object"}],
        )
    return value


def _require_bundle_shape(bundle: dict[str, Any]) -> None:
    missing = [key for key in (*REQUIRED_ARTIFACTS, "candidatePreview") if not isinstance(bundle.get(key), dict)]
    if missing:
        raise DslQualityEvalError(
            "DSL_QUALITY_BUNDLE_INVALID",
            "DSL 质量 baseline bundle 不完整",
            [{"field": f"$.{key}", "reason": "expected object"} for key in missing],
        )


def _render_value(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _render_value(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [_render_value(item, variables) for item in value]
    if not isinstance(value, str):
        return value
    full_match = PLACEHOLDER_PATTERN.fullmatch(value)
    if full_match and full_match.group(1) in variables:
        return copy.deepcopy(variables[full_match.group(1)])
    return PLACEHOLDER_PATTERN.sub(
        lambda match: str(variables.get(match.group(1), match.group(0))),
        value,
    )


def _apply_json_pointer(document: dict[str, Any], pointer: str, value: Any, *, case_id: str) -> None:
    if not pointer.startswith("/"):
        raise _pointer_error(case_id, pointer, "expected JSON Pointer starting with /")
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]
    target: Any = document
    try:
        for part in parts[:-1]:
            target = target[int(part)] if isinstance(target, list) else target[part]
        final = parts[-1]
        if isinstance(target, list):
            target[int(final)] = value
        else:
            if final not in target:
                raise KeyError(final)
            target[final] = value
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _pointer_error(case_id, pointer, "pointer does not resolve in baseline bundle") from exc


def _pointer_error(case_id: str, pointer: str, reason: str) -> DslQualityEvalError:
    return DslQualityEvalError(
        "DSL_QUALITY_MANIFEST_INVALID",
        "DSL 质量语料 override 无效",
        [{"field": f"$.cases[{case_id}].overrides.{pointer}", "reason": reason}],
    )


def _find_unresolved_placeholders(value: Any) -> list[str]:
    unresolved: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            unresolved.update(_find_unresolved_placeholders(item))
    elif isinstance(value, list):
        for item in value:
            unresolved.update(_find_unresolved_placeholders(item))
    elif isinstance(value, str):
        unresolved.update(match.group(0) for match in PLACEHOLDER_PATTERN.finditer(value))
    return sorted(unresolved)


def _find_forbidden_keys(value: Any, path: str = "$.candidatePreview") -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_CANDIDATE_KEYS:
                yield child_path
            yield from _find_forbidden_keys(item, child_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _find_forbidden_keys(item, f"{path}[{index}]")


def _string_leaves(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value} if value else set()
    if isinstance(value, dict):
        result: set[str] = set()
        for item in value.values():
            result.update(_string_leaves(item))
        return result
    if isinstance(value, list):
        result = set()
        for item in value:
            result.update(_string_leaves(item))
        return result
    return set()


def _candidate_questions(candidate: dict[str, Any]) -> list[Any]:
    direct = candidate.get("questions")
    if isinstance(direct, list):
        return direct
    nested = _nested(candidate, "spec", "questions")
    return nested if isinstance(nested, list) else []


def _nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _list_at(value: Any, *keys: str) -> list[Any]:
    item = _nested(value, *keys)
    return item if isinstance(item, list) else []


def _integer_sum(items: list[Any], key: str) -> int | None:
    values = [item.get(key) for item in items if isinstance(item, dict)]
    if len(values) != len(items) or not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
        return None
    return sum(values)


def _count(values: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
