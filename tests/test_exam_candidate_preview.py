import json
from pathlib import Path

from ai_workflows.exam_candidate_preview import (
    ExamCandidatePreviewError,
    build_exam_candidate_preview_from_file,
)


ROOT = Path(__file__).resolve().parents[1]


def test_build_exam_candidate_preview_removes_answers():
    preview = build_exam_candidate_preview_from_file(
        ROOT / "templates/exam/examples/notebook-fill-blank.yaml",
        root=ROOT,
        trace_id="trace_preview",
    )
    serialized = json.dumps(preview, ensure_ascii=False)

    assert preview["kind"] == "ExamCandidatePreview"
    assert preview["sourceExamId"] == "exam_demo"
    assert preview["sourceStatus"] == "WAITING_REVIEW"
    assert preview["questions"][0]["id"] == "q1"
    assert "answer" not in preview["questions"][0]
    assert "gradingRef" not in preview["questions"][0]
    assert preview["answersRemoved"] is True
    assert preview["answerVisibleToCandidate"] is False
    assert preview["redaction"]["answerFieldsRemoved"] == 1
    assert preview["redaction"]["removedFields"] == ["questions[].answer", "questions[].gradingRef"]
    assert preview["redaction"]["answerLeakDetected"] is False
    assert preview["safety"]["standardAnswerRemoved"] is True
    assert preview["safety"]["realPublish"] is False
    assert preview["traceId"] == "trace_preview"
    assert "read_csv" not in serialized


def test_build_exam_candidate_preview_rejects_missing_file(tmp_path):
    try:
        build_exam_candidate_preview_from_file(tmp_path / "missing.yaml", root=ROOT)
    except ExamCandidatePreviewError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "exam"
    else:
        raise AssertionError("expected ExamCandidatePreviewError")


def test_build_exam_candidate_preview_rejects_schema_error(tmp_path):
    bad_exam = tmp_path / "bad-exam.yaml"
    bad_exam.write_text(
        """
version: "1.0"
kind: "Exam"
metadata:
  id: "exam_bad"
status: "WAITING_REVIEW"
spec:
  questionType: "notebook_fill_blank"
  totalScore: 100
  questions: []
""".strip(),
        encoding="utf-8",
    )

    try:
        build_exam_candidate_preview_from_file(bad_exam, root=ROOT)
    except ExamCandidatePreviewError as exc:
        assert exc.code == "SCHEMA_VALIDATION_ERROR"
        assert any(error["field"] == "$.metadata.title" for error in exc.errors)
    else:
        raise AssertionError("expected ExamCandidatePreviewError")


def test_build_exam_candidate_preview_rejects_answer_text_leak(tmp_path):
    leaky_exam = tmp_path / "leaky-exam.yaml"
    leaky_exam.write_text(
        """
version: "1.0"
kind: "Exam"
metadata:
  id: "exam_leaky"
  title: "Notebook 代码挖空题"
  sourceLabId: "lab_demo"
  difficulty: "beginner"
status: "WAITING_REVIEW"
spec:
  questionType: "notebook_fill_blank"
  totalScore: 100
  questions:
    - id: "q1"
      title: "补全 CSV 读取代码"
      stem: "请直接使用 read_csv 完成读取。"
      blankCode: "df = pd.____('data.csv')"
      answer: "read_csv"
      score: 100
      gradingRef: "check_pytest"
""".strip(),
        encoding="utf-8",
    )

    try:
        build_exam_candidate_preview_from_file(leaky_exam, root=ROOT)
    except ExamCandidatePreviewError as exc:
        assert exc.code == "CANDIDATE_PREVIEW_ANSWER_LEAK_DETECTED"
        assert exc.errors[0]["field"] == "$.questions[0].stem"
    else:
        raise AssertionError("expected ExamCandidatePreviewError")
