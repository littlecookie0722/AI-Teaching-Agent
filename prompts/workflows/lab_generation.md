---
id: lab_generation_v0
version: real-llm-minimal-poc-v2
phase: Phase 2
mode: MOCK_ONLY
realMode: REAL_LLM_MINIMAL_SINGLE_REQUEST
outputKind: Lab
outputSchema: templates/lab/lab.schema.json
defaultStatus: WAITING_REVIEW
reviewRequired: true
---

# Lab DSL Generation Prompt

Generate one AI training Lab DSL JSON object.

Return JSON only. Do not use Markdown fences, comments, prose, or multiple objects.

## Input

- Teaching source material.
- Optional `Lab generation context JSON`.

## Required Output Contract

- The object must validate against `templates/lab/lab.schema.json`.
- Set `version` to `"1.0"`.
- Set `kind` to `"Lab"`.
- Set `status` to `"WAITING_REVIEW"`.
- Generate a stable `metadata.id` using lowercase letters, numbers, and hyphens.
- Keep the lab concise, reviewable, and suitable for manual approval.

## Generation Context Mapping

When `Lab generation context JSON` is present, apply it strictly:

- `targetUsers` must be copied into `spec.targetUsers`.
- `durationMinutes` must be copied into `metadata.durationMinutes`.
- `difficulty` must be copied into `metadata.difficulty`.
- `techTags` must be included in `metadata.tags` together with any source-derived tags.
- `teachingStyle` must shape the step design:
  - `guided_practice`: step-by-step guided practice with clear expected results.
  - `project_based`: build toward a small complete project or deliverable.
  - `challenge_based`: include challenge-style tasks while keeping answers out of the DSL.
  - `lecture_demo`: organize as teacher-led demo steps with learner checkpoints.

If a context field conflicts with the source material, prefer the context field and make the lab content fit that context.

## Lab Content Rules

- Use the source material as the primary subject matter.
- Include at least 2 distinct learning objectives and at least one step. The objectives must describe different learner outcomes, not repeated wording.
- Each step must include `id`, `title`, and `instruction`.
- Include `expectedResult` when it helps human reviewers judge the step.
- Include only commands that are safe, illustrative, and derived from the source.
- Do not include standard answers intended for exam candidates.

## Safety

- Do not publish the lab.
- Do not execute unknown shell scripts.
- Do not create real VM or Notebook resources.
- Do not include secrets.
- Do not include API keys, tokens, passwords, private URLs, or credential placeholders.
- Do not instruct the platform to create, modify, or delete real cloud resources.
- Do not instruct the platform to execute contestant code or run a sandbox.
