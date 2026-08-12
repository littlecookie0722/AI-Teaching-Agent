---
id: exam_generation_v0
version: 0.1.0
phase: Phase 2
mode: MOCK_ONLY
realMode: REAL_LLM_DEMO_DSL_GENERATION
outputKind: Exam
outputSchema: templates/exam/exam.schema.json
defaultStatus: WAITING_REVIEW
reviewRequired: true
answerVisibleToCandidate: false
---

# Exam DSL Generation Prompt

Generate one Exam DSL JSON object for an AI training platform demo.

Return JSON only. Do not use Markdown fences, comments, prose, or multiple objects.

## Input

- Source material.
- Lab DSL or Lab summary in `Request JSON.context.labDsl`.
- Optional demo constraints.

## Required Output Contract

- The object must validate against `templates/exam/exam.schema.json`.
- Set `version` to `"1.0"`.
- Set `kind` to `"Exam"`.
- Set `status` to `"WAITING_REVIEW"`.
- Set `metadata.sourceLabId` from the Lab DSL metadata id when available.
- Use `questionType` from the schema enum: `notebook_fill_blank`, `coding_task`, or `short_answer`.
- Include at least one question.
- Every question must include `id`, `title`, `stem`, `score`, and `gradingRef`.
- Total question scores must equal `spec.totalScore`.

## Candidate Safety

- It is allowed to store `answer` inside the reviewer DSL when useful.
- Never add a candidate-facing preview field containing answers.
- Do not include standard answers in `stem`, `title`, or `blankCode`.

## Safety

- Do not reveal standard answers to candidate-facing output.
- Do not publish the exam.
- Do not bypass human review.
- Do not include secrets.
- Do not execute code, notebooks, shell commands, or grading checks.
