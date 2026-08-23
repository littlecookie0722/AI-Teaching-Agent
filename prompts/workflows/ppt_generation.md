---
id: ppt_generation_v0
version: 0.1.9
phase: Phase 2
mode: MOCK_ONLY
realMode: REAL_LLM_DEMO_DSL_GENERATION
outputKind: PPT
outputSchema: templates/ppt/ppt.schema.json
defaultStatus: WAITING_REVIEW
reviewRequired: true
artifactGenerated: false
---

# PPT DSL Generation Prompt

Generate one PPT DSL JSON object for an AI training platform demo.

Return JSON only. Do not use Markdown fences, comments, prose, or multiple objects.

## Input

- Local Markdown source material.
- Lab DSL / Exam DSL summaries when available.

## Required Output Contract

- The object must validate against `templates/ppt/ppt.schema.json`.
- Set `version` to `"1.0"`.
- Set `kind` to `"PPT"`.
- Set `status` to `"WAITING_REVIEW"`.
- Set `metadata.title`, `metadata.audience`, and `metadata.durationMinutes`.
- Include `spec.theme.style` and `spec.theme.language`.
- Include 5-8 slides. Prefer exactly 6 for the default teaching presentation.
- Use this teaching flow: cover, learning objectives, core concept, lab process,
  candidate-safe exercise, and summary.
- Use `layout` values from `hero`, `objectives`, `concept`, `process`,
  `exercise`, and `summary` to create at least three distinct layouts.
- Keep slide titles concise.
- Use bullets derived from the source or Lab DSL.

## Slide Planning Rules

- Build a clear teaching flow: title, learning goals, main content, process,
  practice, and summary.
- Keep each content slide to 3-5 bullets.
- Do not generate binary PPTX content.

## Safety

- Do not generate a real PPT artifact in this DSL step.
- Do not publish courseware.
- Do not bypass human review.
- Do not include secrets.
- Do not include answers, answer text, `gradingRef`, internal IDs, review status,
  PoC labels, or publish policy in visible slide content.
