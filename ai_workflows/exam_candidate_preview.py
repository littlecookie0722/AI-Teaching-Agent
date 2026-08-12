"""Candidate-facing Exam DSL preview redaction helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from cli.dsl import DslValidationError, load_schema, load_yaml, validate_dsl


ROOT = Path(__file__).resolve().parents[1]
ANSWER_FIELD_NAMES = {"answer", "standardAnswer", "solution", "referenceAnswer"}
CANDIDATE_VISIBLE_QUESTION_FIELDS = ("id", "title", "stem", "blankCode", "score")
INTERNAL_ONLY_QUESTION_FIELDS = ("gradingRef",)


class ExamCandidatePreviewError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def build_exam_candidate_preview_from_file(
    exam_path: Path,
    *,
    root: Path = ROOT,
    trace_id: str | None = None,
) -> dict[str, Any]:
    if not exam_path.exists() or not exam_path.is_file():
        raise ExamCandidatePreviewError(
            "VALIDATION_ERROR",
            "Exam DSL 文件不存在",
            [{"field": "exam", "reason": "文件不存在"}],
        )
    try:
        exam_dsl = load_yaml(exam_path)
        validate_dsl(exam_dsl, load_schema("exam", root))
    except DslValidationError as exc:
        raise ExamCandidatePreviewError("SCHEMA_VALIDATION_ERROR", "Exam DSL Schema 校验失败", exc.errors) from exc
    if not isinstance(exam_dsl, dict):
        raise ExamCandidatePreviewError(
            "SCHEMA_VALIDATION_ERROR",
            "Exam DSL Schema 校验失败",
            [{"field": "$", "reason": "root must be object"}],
        )
    return build_candidate_safe_exam_preview(exam_dsl, source_path=exam_path, trace_id=trace_id)


def build_candidate_safe_exam_preview(
    exam_dsl: dict[str, Any],
    *,
    source_path: Path | str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    metadata = exam_dsl.get("metadata", {})
    spec = exam_dsl.get("spec", {})
    questions = spec.get("questions", [])
    safe_questions: list[dict[str, Any]] = []
    answer_values: list[str] = []
    answer_fields_removed = 0
    removed_fields: set[str] = set()

    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            continue
        safe_question = {
            field: question[field]
            for field in CANDIDATE_VISIBLE_QUESTION_FIELDS
            if field in question
        }
        safe_questions.append(safe_question)
        for internal_key in INTERNAL_ONLY_QUESTION_FIELDS:
            if internal_key in question:
                removed_fields.add(f"questions[].{internal_key}")
        for answer_key in ANSWER_FIELD_NAMES:
            answer_value = question.get(answer_key)
            if answer_value is None:
                continue
            answer_fields_removed += 1
            removed_fields.add(f"questions[].{answer_key}")
            normalized_answer = _normalize_text(answer_value)
            if normalized_answer:
                answer_values.append(normalized_answer)

    preview = {
        "version": "1.0",
        "kind": "ExamCandidatePreview",
        "mode": "LOCAL_DSL_REDACTION",
        "sourceExamId": metadata.get("id"),
        "sourceExamTitle": metadata.get("title"),
        "sourceLabId": metadata.get("sourceLabId"),
        "sourceStatus": exam_dsl.get("status"),
        "difficulty": metadata.get("difficulty"),
        "questionType": spec.get("questionType"),
        "totalScore": spec.get("totalScore"),
        "questions": safe_questions,
        "answersRemoved": True,
        "answerVisibleToCandidate": False,
        "reviewRequired": True,
        "publishBlockedUntilApproved": True,
        "redaction": {
            "candidateSafe": True,
            "answerFieldsRemoved": answer_fields_removed,
            "removedFields": sorted(removed_fields),
            "answerLeakDetected": False,
        },
        "safety": {
            "answerVisibleToCandidate": False,
            "standardAnswerRemoved": True,
            "realPublish": False,
            "autoPublishAllowed": False,
            "reviewBypassed": False,
            "contestantCodeExecuted": False,
        },
    }
    if source_path is not None:
        preview["sourcePath"] = str(source_path)
    if trace_id:
        preview["traceId"] = trace_id

    leaks = _find_answer_leaks(preview, answer_values)
    if leaks:
        raise ExamCandidatePreviewError(
            "CANDIDATE_PREVIEW_ANSWER_LEAK_DETECTED",
            "候选人预览检测到标准答案泄露",
            leaks,
        )
    return preview


def _find_answer_leaks(payload: dict[str, Any], answer_values: Iterable[str]) -> list[dict[str, str]]:
    unique_answers = sorted(set(answer_values), key=len, reverse=True)
    if not unique_answers:
        return []
    leaks: list[dict[str, str]] = []
    for field_path, value in _iter_string_fields(payload):
        normalized_value = value.casefold()
        for answer in unique_answers:
            if _matches_answer(answer, normalized_value):
                leaks.append({"field": field_path, "reason": "candidate preview contains answer text"})
                break
    return leaks


def _iter_string_fields(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_string_fields(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_string_fields(item, f"{path}[{index}]")


def _matches_answer(answer: str, normalized_value: str) -> bool:
    normalized_answer = answer.casefold()
    if len(normalized_answer) <= 4:
        return normalized_value.strip() == normalized_answer
    return normalized_answer in normalized_value


def _normalize_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True).strip()
    return str(value).strip()
