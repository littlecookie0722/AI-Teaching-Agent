"""Read-only sandbox PoC for low-risk grading checks.

This executor only inspects files inside an explicitly provided submission
directory. It supports `file_exists`, `json_field`, static `notebook_cell`
JSON parsing, and `log_keyword` text matching; it does not run commands,
pytest, notebook kernels, shells, containers, or contestant code.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from sandbox.grade_runner import (
    SANDBOX_POLICY,
    SUPPORTED_CHECK_TYPES,
    build_assessment_plan_summary,
    build_grading_check_plan_fields,
)


MODE = "READONLY_REAL_SANDBOX_POC"
EXECUTOR_ID = "readonly_submission_sandbox_executor"
SUPPORTED_READONLY_CHECK_TYPES = ("file_exists", "json_field", "notebook_cell", "log_keyword")
MAX_JSON_BYTES = 1024 * 1024
MAX_NOTEBOOK_BYTES = 5 * 1024 * 1024
MAX_LOG_BYTES = 1024 * 1024


class ReadonlySandboxExecutorError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


class ReadonlySandboxExecutor:
    mode = MODE
    executor_id = EXECUTOR_ID

    def run(self, grading: dict[str, Any], submission_root: Path | str, trace_id: str) -> dict[str, Any]:
        root = _validate_submission_root(Path(submission_root))
        checks = grading.get("spec", {}).get("checks", [])
        check_results = [self._execute_check(check, grading=grading, submission_root=root, trace_id=trace_id) for check in checks]
        executed = [check for check in check_results if check["status"] in {"PASSED", "FAILED", "ERROR"}]
        deferred = [check for check in check_results if check["status"] == "DEFERRED"]
        passed = [check for check in executed if check["passed"] is True]
        failed = [check for check in executed if check["passed"] is False]
        executable_score = sum(int(check.get("score", 0)) for check in executed)
        earned_score = sum(int(check.get("earnedScore", 0)) for check in executed)
        total_score = int(grading.get("spec", {}).get("totalScore", 0))
        type_counts = _counts_by_type(check_results)
        assessment_plan_summary = build_assessment_plan_summary(grading, check_results)

        return {
            "id": f"readonly_sandbox_report_{uuid4().hex[:12]}",
            "mode": MODE,
            "phase": "Phase 3",
            "gradingId": grading.get("metadata", {}).get("id"),
            "totalScore": total_score,
            "earnedScore": earned_score,
            "submissionRoot": str(root),
            "runner": {
                "id": EXECUTOR_ID,
                "mode": MODE,
                "supportedCheckTypes": list(SUPPORTED_READONLY_CHECK_TYPES),
                "deferredCheckTypes": [
                    check_type for check_type in SUPPORTED_CHECK_TYPES if check_type not in SUPPORTED_READONLY_CHECK_TYPES
                ],
                "strategy": "READONLY_STATIC_FILE_INSPECTION_ONLY",
                "realSandboxExecuted": True,
                "hostExecutionAllowed": False,
            },
            "sandboxPolicy": {
                **SANDBOX_POLICY,
                "mode": MODE,
                "realSandboxRunEnabled": True,
                "readonlyOnly": True,
                "supportedRealExecutionCheckTypes": list(SUPPORTED_READONLY_CHECK_TYPES),
                "deferredCheckTypes": [
                    check_type for check_type in SUPPORTED_CHECK_TYPES if check_type not in SUPPORTED_READONLY_CHECK_TYPES
                ],
            },
            "checkSummary": {
                "total": len(check_results),
                "passed": len(passed),
                "failed": len(failed),
                "executed": len(executed),
                "deferred": len(deferred),
                "plannedOnly": len(deferred),
                "byType": type_counts,
                "scoreTotalMatchesSpec": sum(int(check.get("score", 0)) for check in check_results) == total_score,
            },
            "executionSummary": {
                "total": len(check_results),
                "executed": len(executed),
                "passed": len(passed),
                "failed": len(failed),
                "deferred": len(deferred),
                "byType": type_counts,
            },
            "score": {
                "totalScore": total_score,
                "executableScore": executable_score,
                "earnedScore": earned_score,
                "deferredScore": sum(int(check.get("score", 0)) for check in deferred),
            },
            "assessmentPlanSummary": assessment_plan_summary,
            "explainability": {
                "status": "READONLY_EVIDENCE_PARTIAL",
                "eachCheckHasPlan": all(bool(check.get("executionPlan")) for check in check_results),
                "eachCheckHasInputSummary": all(bool(check.get("inputSummary")) for check in check_results),
                "eachCheckHasMockEvidencePlaceholder": all(bool(check.get("mockEvidence")) for check in check_results),
                "assessmentPlanSource": assessment_plan_summary["source"],
                "assessmentPlanAlignedWithChecks": assessment_plan_summary["alignedWithChecks"],
                "readonlyEvidenceCollected": bool(executed),
                "readonlyEvidenceCheckTypes": list(SUPPORTED_READONLY_CHECK_TYPES),
                "deferredCheckTypes": [
                    check_type for check_type in SUPPORTED_CHECK_TYPES if check_type not in SUPPORTED_READONLY_CHECK_TYPES
                ],
                "realSandboxEvidenceRequired": bool(deferred),
            },
            "passed": len(deferred) == 0 and len(failed) == 0 and earned_score >= total_score,
            "checks": check_results,
            "sandboxExecuted": bool(executed),
            "contestantCodeExecuted": False,
            "unknownShellExecuted": False,
            "commandExecuted": False,
            "networkEnabled": False,
            "filesystemIsolated": True,
            "realSandboxRequiredBeforeExecution": bool(deferred),
            "safety": {
                "sandboxExecuted": bool(executed),
                "readonlyOnly": True,
                "contestantCodeExecuted": False,
                "commandExecuted": False,
                "unknownShellExecuted": False,
                "pytestExecuted": False,
                "notebookExecuted": False,
                "networkEnabled": False,
                "hostExecutionAllowed": False,
                "realPublish": False,
            },
            "traceId": trace_id,
            "note": "Read-only sandbox PoC only inspects low-risk files inside the submission directory.",
        }

    def _execute_check(
        self,
        check: dict[str, Any],
        *,
        grading: dict[str, Any],
        submission_root: Path,
        trace_id: str,
    ) -> dict[str, Any]:
        check_type = str(check.get("type"))
        plan_fields = build_grading_check_plan_fields(check, grading=grading, trace_id=trace_id)
        base = {
            **plan_fields,
            "id": check.get("id"),
            "type": check_type,
            "score": int(check.get("score", 0)),
            "mode": MODE,
            "executor": EXECUTOR_ID,
            "sandboxExecuted": False,
            "readonlyOnly": True,
            "contestantCodeExecuted": False,
            "commandExecuted": False,
            "unknownShellExecuted": False,
            "networkEnabled": False,
            "traceId": trace_id,
        }
        if check_type not in SUPPORTED_READONLY_CHECK_TYPES:
            return {
                **base,
                "status": "DEFERRED",
                "passed": None,
                "earnedScore": 0,
                "reason": "Check type is not supported by the read-only sandbox PoC.",
                "realSandboxRequiredBeforeExecution": True,
                "evidence": {
                    "status": "NOT_COLLECTED",
                    "matchedEvidence": [],
                    "filesInspected": [],
                "auditLogRef": None,
                },
                "readonlyEvidence": {
                    "status": "NOT_COLLECTED",
                    "reason": "Check type is not supported by the read-only sandbox PoC.",
                },
            }
        if check_type == "file_exists":
            return self._run_file_exists(check, base=base, submission_root=submission_root)
        if check_type == "json_field":
            return self._run_json_field(check, base=base, submission_root=submission_root)
        if check_type == "notebook_cell":
            return self._run_notebook_cell(check, base=base, submission_root=submission_root)
        return self._run_log_keyword(check, base=base, submission_root=submission_root)

    def _run_file_exists(self, check: dict[str, Any], *, base: dict[str, Any], submission_root: Path) -> dict[str, Any]:
        started = time.perf_counter()
        resolved = _resolve_submission_file(submission_root, check.get("path"), field=f"checks.{check.get('id')}.path")
        if isinstance(resolved, dict):
            return _failed_check(base, resolved, duration_ms=0)
        exists = resolved.is_file()
        return {
            **base,
            "status": "PASSED" if exists else "FAILED",
            "passed": exists,
            "earnedScore": base["score"] if exists else 0,
            "sandboxExecuted": True,
            "durationMs": _duration_ms(started),
            "evidence": {
                "status": "COLLECTED",
                "path": _relative_posix(submission_root, resolved),
                "exists": exists,
                "matchedEvidence": ["file_exists"] if exists else [],
                "filesInspected": [_relative_posix(submission_root, resolved)],
                "auditLogRef": f"readonly://{base['id']}",
            },
            "readonlyEvidence": {
                "status": "COLLECTED",
                "kind": "file_exists",
                "path": _relative_posix(submission_root, resolved),
                "exists": exists,
                "matchedEvidence": ["file_exists"] if exists else [],
                "auditLogRef": f"readonly://{base['id']}",
            },
        }

    def _run_json_field(self, check: dict[str, Any], *, base: dict[str, Any], submission_root: Path) -> dict[str, Any]:
        started = time.perf_counter()
        resolved = _resolve_submission_file(submission_root, check.get("path"), field=f"checks.{check.get('id')}.path")
        if isinstance(resolved, dict):
            return _failed_check(base, resolved, duration_ms=0)
        if not resolved.is_file():
            return _failed_check(
                base,
                {"code": "FILE_NOT_FOUND", "field": f"checks.{check.get('id')}.path", "reason": "file does not exist"},
                duration_ms=_duration_ms(started),
                files_inspected=[_relative_posix(submission_root, resolved)],
            )
        try:
            if resolved.stat().st_size > MAX_JSON_BYTES:
                return _failed_check(
                    base,
                    {"code": "JSON_FILE_TOO_LARGE", "field": f"checks.{check.get('id')}.path", "reason": "file exceeds 1MB"},
                    duration_ms=_duration_ms(started),
                    files_inspected=[_relative_posix(submission_root, resolved)],
                )
            document = json.loads(resolved.read_text(encoding="utf-8"))
            actual_value = _json_path_value(document, str(check.get("jsonPath") or "$"))
        except (OSError, json.JSONDecodeError, ReadonlySandboxExecutorError) as exc:
            return _failed_check(
                base,
                {
                    "code": getattr(exc, "code", "JSON_FIELD_READ_FAILED"),
                    "field": f"checks.{check.get('id')}.jsonPath",
                    "reason": getattr(exc, "message", exc.__class__.__name__),
                },
                duration_ms=_duration_ms(started),
                files_inspected=[_relative_posix(submission_root, resolved)],
            )

        expected_value = check.get("expectedValue")
        passed = actual_value == expected_value
        return {
            **base,
            "status": "PASSED" if passed else "FAILED",
            "passed": passed,
            "earnedScore": base["score"] if passed else 0,
            "sandboxExecuted": True,
            "durationMs": _duration_ms(started),
            "evidence": {
                "status": "COLLECTED",
                "path": _relative_posix(submission_root, resolved),
                "jsonPath": check.get("jsonPath"),
                "expectedValue": expected_value,
                "actualValue": actual_value,
                "matchedEvidence": ["json_field_equal"] if passed else [],
                "filesInspected": [_relative_posix(submission_root, resolved)],
                "auditLogRef": f"readonly://{base['id']}",
            },
            "readonlyEvidence": {
                "status": "COLLECTED",
                "kind": "json_field",
                "path": _relative_posix(submission_root, resolved),
                "jsonPath": check.get("jsonPath"),
                "expectedValue": expected_value,
                "actualValue": actual_value,
                "matchedEvidence": ["json_field_equal"] if passed else [],
                "auditLogRef": f"readonly://{base['id']}",
            },
        }

    def _run_notebook_cell(self, check: dict[str, Any], *, base: dict[str, Any], submission_root: Path) -> dict[str, Any]:
        started = time.perf_counter()
        resolved = _resolve_submission_file(
            submission_root,
            check.get("notebookPath"),
            field=f"checks.{check.get('id')}.notebookPath",
        )
        if isinstance(resolved, dict):
            return _failed_check(base, resolved, duration_ms=0)
        if resolved.suffix.lower() != ".ipynb":
            return _failed_check(
                base,
                {
                    "code": "NOTEBOOK_EXTENSION_UNSUPPORTED",
                    "field": f"checks.{check.get('id')}.notebookPath",
                    "reason": "notebookPath must point to a .ipynb file",
                },
                duration_ms=_duration_ms(started),
                files_inspected=[_relative_posix(submission_root, resolved)],
            )
        if not resolved.is_file():
            return _failed_check(
                base,
                {"code": "NOTEBOOK_NOT_FOUND", "field": f"checks.{check.get('id')}.notebookPath", "reason": "file does not exist"},
                duration_ms=_duration_ms(started),
                files_inspected=[_relative_posix(submission_root, resolved)],
            )

        try:
            if resolved.stat().st_size > MAX_NOTEBOOK_BYTES:
                return _failed_check(
                    base,
                    {
                        "code": "NOTEBOOK_FILE_TOO_LARGE",
                        "field": f"checks.{check.get('id')}.notebookPath",
                        "reason": "notebook exceeds 5MB",
                    },
                    duration_ms=_duration_ms(started),
                    files_inspected=[_relative_posix(submission_root, resolved)],
                )
            notebook = json.loads(resolved.read_text(encoding="utf-8"))
            cell_text = _notebook_cell_text(notebook, check.get("cellIndex"))
        except (OSError, json.JSONDecodeError, ReadonlySandboxExecutorError) as exc:
            return _failed_check(
                base,
                {
                    "code": getattr(exc, "code", "NOTEBOOK_STATIC_PARSE_FAILED"),
                    "field": f"checks.{check.get('id')}.notebookPath",
                    "reason": getattr(exc, "message", exc.__class__.__name__),
                },
                duration_ms=_duration_ms(started),
                files_inspected=[_relative_posix(submission_root, resolved)],
            )

        expected_tokens = _expected_tokens(check)
        matched_tokens = [token for token in expected_tokens if token in cell_text]
        missing_tokens = [token for token in expected_tokens if token not in cell_text]
        passed = bool(expected_tokens) and not missing_tokens
        return {
            **base,
            "status": "PASSED" if passed else "FAILED",
            "passed": passed,
            "earnedScore": base["score"] if passed else 0,
            "sandboxExecuted": True,
            "durationMs": _duration_ms(started),
            "evidence": {
                "status": "COLLECTED",
                "method": "STATIC_NOTEBOOK_JSON_PARSE",
                "notebookPath": _relative_posix(submission_root, resolved),
                "cellIndex": check.get("cellIndex"),
                "expected": expected_tokens,
                "matchedTokens": matched_tokens,
                "missingTokens": missing_tokens,
                "matchedEvidence": ["notebook_cell_static_token_match"] if passed else matched_tokens,
                "filesInspected": [_relative_posix(submission_root, resolved)],
                "auditLogRef": f"readonly://{base['id']}",
                "notebookKernelStarted": False,
                "notebookExecuted": False,
                "contestantCodeExecuted": False,
                "commandExecuted": False,
                "networkEnabled": False,
            },
            "readonlyEvidence": {
                "status": "COLLECTED",
                "kind": "notebook_cell_static_parse",
                "method": "STATIC_NOTEBOOK_JSON_PARSE",
                "notebookPath": _relative_posix(submission_root, resolved),
                "cellIndex": check.get("cellIndex"),
                "expected": expected_tokens,
                "matchedTokens": matched_tokens,
                "missingTokens": missing_tokens,
                "matchedEvidence": ["notebook_cell_static_token_match"] if passed else matched_tokens,
                "auditLogRef": f"readonly://{base['id']}",
                "notebookKernelStarted": False,
                "notebookExecuted": False,
                "contestantCodeExecuted": False,
                "commandExecuted": False,
                "networkEnabled": False,
            },
        }

    def _run_log_keyword(self, check: dict[str, Any], *, base: dict[str, Any], submission_root: Path) -> dict[str, Any]:
        started = time.perf_counter()
        resolved = _resolve_submission_file(submission_root, check.get("path"), field=f"checks.{check.get('id')}.path")
        if isinstance(resolved, dict):
            return _failed_check(base, resolved, duration_ms=0)
        if not resolved.is_file():
            return _failed_check(
                base,
                {"code": "LOG_FILE_NOT_FOUND", "field": f"checks.{check.get('id')}.path", "reason": "file does not exist"},
                duration_ms=_duration_ms(started),
                files_inspected=[_relative_posix(submission_root, resolved)],
            )
        try:
            if resolved.stat().st_size > MAX_LOG_BYTES:
                return _failed_check(
                    base,
                    {"code": "LOG_FILE_TOO_LARGE", "field": f"checks.{check.get('id')}.path", "reason": "file exceeds 1MB"},
                    duration_ms=_duration_ms(started),
                    files_inspected=[_relative_posix(submission_root, resolved)],
                )
            content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return _failed_check(
                base,
                {"code": "LOG_FILE_DECODE_FAILED", "field": f"checks.{check.get('id')}.path", "reason": "file must be UTF-8 text"},
                duration_ms=_duration_ms(started),
                files_inspected=[_relative_posix(submission_root, resolved)],
            )
        except OSError as exc:
            return _failed_check(
                base,
                {"code": "LOG_FILE_READ_FAILED", "field": f"checks.{check.get('id')}.path", "reason": exc.__class__.__name__},
                duration_ms=_duration_ms(started),
                files_inspected=[_relative_posix(submission_root, resolved)],
            )

        expected_tokens = _expected_tokens(check)
        matched_tokens = [token for token in expected_tokens if token in content]
        missing_tokens = [token for token in expected_tokens if token not in content]
        passed = bool(expected_tokens) and not missing_tokens
        return {
            **base,
            "status": "PASSED" if passed else "FAILED",
            "passed": passed,
            "earnedScore": base["score"] if passed else 0,
            "sandboxExecuted": True,
            "durationMs": _duration_ms(started),
            "evidence": {
                "status": "COLLECTED",
                "method": "STATIC_LOG_TEXT_SCAN",
                "path": _relative_posix(submission_root, resolved),
                "expected": expected_tokens,
                "matchedTokens": matched_tokens,
                "missingTokens": missing_tokens,
                "matchedEvidence": ["log_keyword_static_match"] if passed else matched_tokens,
                "filesInspected": [_relative_posix(submission_root, resolved)],
                "auditLogRef": f"readonly://{base['id']}",
                "contestantCodeExecuted": False,
                "commandExecuted": False,
                "networkEnabled": False,
            },
            "readonlyEvidence": {
                "status": "COLLECTED",
                "kind": "log_keyword_static_scan",
                "method": "STATIC_LOG_TEXT_SCAN",
                "path": _relative_posix(submission_root, resolved),
                "expected": expected_tokens,
                "matchedTokens": matched_tokens,
                "missingTokens": missing_tokens,
                "matchedEvidence": ["log_keyword_static_match"] if passed else matched_tokens,
                "auditLogRef": f"readonly://{base['id']}",
                "contestantCodeExecuted": False,
                "commandExecuted": False,
                "networkEnabled": False,
            },
        }


def build_readonly_sandbox_report(grading: dict[str, Any], submission_root: Path | str, trace_id: str) -> dict[str, Any]:
    return ReadonlySandboxExecutor().run(grading, submission_root, trace_id)


def _validate_submission_root(path: Path) -> Path:
    root = path.resolve()
    if not root.exists() or not root.is_dir():
        raise ReadonlySandboxExecutorError(
            "VALIDATION_ERROR",
            "Submission root must be an existing directory.",
            [{"field": "submission", "reason": "directory does not exist"}],
        )
    return root


def _resolve_submission_file(submission_root: Path, value: Any, *, field: str) -> Path | dict[str, str]:
    if not isinstance(value, str) or not value:
        return {"code": "PATH_REQUIRED", "field": field, "reason": "must be a non-empty relative path"}
    raw_path = Path(value)
    if raw_path.is_absolute():
        return {"code": "ABSOLUTE_PATH_NOT_ALLOWED", "field": field, "reason": "path must be relative to submission root"}
    candidate = (submission_root / raw_path).resolve()
    try:
        candidate.relative_to(submission_root)
    except ValueError:
        return {"code": "PATH_OUTSIDE_SUBMISSION", "field": field, "reason": "path escapes submission root"}
    return candidate


def _json_path_value(document: Any, json_path: str) -> Any:
    tokens = _json_path_tokens(json_path)
    current = document
    for token in tokens:
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                raise ReadonlySandboxExecutorError("JSON_PATH_NOT_FOUND", "JSON path index not found")
            current = current[token]
        else:
            if not isinstance(current, dict) or token not in current:
                raise ReadonlySandboxExecutorError("JSON_PATH_NOT_FOUND", "JSON path key not found")
            current = current[token]
    return current


def _json_path_tokens(json_path: str) -> list[str | int]:
    if json_path == "$":
        return []
    if not json_path.startswith("$."):
        raise ReadonlySandboxExecutorError("JSON_PATH_UNSUPPORTED", "Only $.field style JSON paths are supported")
    tokens: list[str | int] = []
    for part in json_path[2:].split("."):
        if not part:
            raise ReadonlySandboxExecutorError("JSON_PATH_UNSUPPORTED", "JSON path contains an empty segment")
        while "[" in part:
            field, _, rest = part.partition("[")
            if field:
                tokens.append(field)
            index_text, sep, remainder = rest.partition("]")
            if sep != "]" or not index_text.isdigit():
                raise ReadonlySandboxExecutorError("JSON_PATH_UNSUPPORTED", "Only numeric array indexes are supported")
            tokens.append(int(index_text))
            part = remainder
        if part:
            tokens.append(part)
    return tokens


def _expected_tokens(check: dict[str, Any]) -> list[str]:
    raw_tokens = check.get("expected")
    if not isinstance(raw_tokens, list):
        return []
    return [token for token in raw_tokens if isinstance(token, str) and token]


def _notebook_cell_text(notebook: Any, cell_index: Any) -> str:
    if not isinstance(cell_index, int) or cell_index < 0:
        raise ReadonlySandboxExecutorError("NOTEBOOK_CELL_INDEX_INVALID", "cellIndex must be a non-negative integer")
    if not isinstance(notebook, dict):
        raise ReadonlySandboxExecutorError("NOTEBOOK_FORMAT_INVALID", "Notebook JSON root must be an object")
    cells = notebook.get("cells")
    if not isinstance(cells, list):
        raise ReadonlySandboxExecutorError("NOTEBOOK_FORMAT_INVALID", "Notebook cells must be an array")
    if cell_index >= len(cells):
        raise ReadonlySandboxExecutorError("NOTEBOOK_CELL_NOT_FOUND", "Notebook cell index not found")
    cell = cells[cell_index]
    if not isinstance(cell, dict):
        raise ReadonlySandboxExecutorError("NOTEBOOK_FORMAT_INVALID", "Notebook cell must be an object")
    parts = [_text_from_notebook_value(cell.get("source"))]
    outputs = cell.get("outputs", [])
    if isinstance(outputs, list):
        for output in outputs:
            if not isinstance(output, dict):
                continue
            parts.append(_text_from_notebook_value(output.get("text")))
            parts.append(_text_from_notebook_value(output.get("data", {}).get("text/plain") if isinstance(output.get("data"), dict) else None))
    return "\n".join(part for part in parts if part)


def _text_from_notebook_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(item for item in value if isinstance(item, str))
    return ""


def _failed_check(
    base: dict[str, Any],
    error: dict[str, str],
    *,
    duration_ms: int,
    files_inspected: list[str] | None = None,
) -> dict[str, Any]:
    return {
        **base,
        "status": "FAILED",
        "passed": False,
        "earnedScore": 0,
        "sandboxExecuted": True,
        "durationMs": duration_ms,
        "error": error,
        "evidence": {
            "status": "ERROR",
            "matchedEvidence": [],
            "filesInspected": files_inspected or [],
            "auditLogRef": f"readonly://{base['id']}",
        },
        "readonlyEvidence": {
            "status": "ERROR",
            "matchedEvidence": [],
            "filesInspected": files_inspected or [],
            "error": error,
            "auditLogRef": f"readonly://{base['id']}",
        },
    }


def _relative_posix(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _duration_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _counts_by_type(checks: list[dict[str, Any]]) -> dict[str, int]:
    return {check_type: sum(1 for check in checks if check.get("type") == check_type) for check_type in SUPPORTED_CHECK_TYPES}
