---
id: grading_generation_v0
version: 0.1.0
phase: Phase 2
mode: MOCK_ONLY
realMode: REAL_LLM_DEMO_DSL_GENERATION
outputKind: Grading
outputSchema: templates/grading/grading.schema.json
defaultStatus: WAITING_REVIEW
reviewRequired: true
sandboxRequiredBeforeRealExecution: true
---

# Grading DSL Generation Prompt

Generate one Grading DSL JSON object for an AI training platform demo.

Return JSON only. Do not use Markdown fences, comments, prose, or multiple objects.

## Input

- Exam DSL in `Request JSON.context.examDsl`.
- Lab DSL and source material when available.
- The generated Grading DSL is a plan for deterministic checks; it must not execute anything.

## Required Output Contract

- The object must validate against `templates/grading/grading.schema.json`.
- Set `version` to `"1.0"`.
- Set `kind` to `"Grading"`.
- Set `status` to `"WAITING_REVIEW"`.
- Set `metadata.sourceExamId` from the Exam DSL metadata id when available.
- `spec.totalScore` must equal the Exam DSL total score when available.
- Include at least one deterministic check.
- Prefer supported check types: `file_exists`, `stdout_contains`, `pytest`, `notebook_cell`, `json_field`, `log_keyword`.
- `checks[].id` must align with Exam DSL `questions[].gradingRef` whenever available.
- Include `spec.assessmentPlan`.

## Check Field Rules

Every check must include the runner-required fields for its type:

- `file_exists`: `path`.
- `stdout_contains`: `command` and non-empty string array `expected`.
- `pytest`: `path`.
- `notebook_cell`: `notebookPath`, non-negative integer `cellIndex`, and non-empty string array `expected`.
- `json_field`: `path`, `jsonPath`, and `expectedValue`.
- `log_keyword`: `path` and non-empty string array `expected`.

If the Exam DSL is short-answer oriented, still generate deterministic placeholder checks that can be reviewed before real sandbox execution. For example, use `stdout_contains` with `command: "python main.py"` and `expected` derived from the corresponding question grading expectation.

## Assessment Plan Rules

Every assessment plan item must include:

- `checkId` equal to a generated check id.
- `type` equal to the check type.
- `runner` as a human-readable runner name.
- `score` equal to the check score.
- `inputSummary` explaining what would be checked.
- `executionPlan.strategy` exactly `"MOCK_PLAN_ONLY"`.
- `executionPlan.requiredLimits.network` exactly `"disabled_by_default"`.
- `executionPlan.requiredLimits` with `cpu`, `memory`, `timeout`, `network`, `filesystem`, and `process`.
- `executionPlan.wouldRunInsideRealSandbox` exactly `true`.
- `mockEvidence.status` exactly `"MOCK_EVIDENCE_NOT_COLLECTED"`.
- `riskLevel` as `low`, `medium`, or `high`.
- `sandboxRequiredBeforeRealExecution` exactly `true`.

## Safety

- Do not score submissions with a language model.
- Do not execute generated commands.
- Do not run contestant code without a real sandbox.
- Do not include secrets.
- Do not publish generated grading rules.
