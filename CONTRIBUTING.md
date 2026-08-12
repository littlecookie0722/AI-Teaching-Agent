# Contributing

Thanks for improving AI Teaching Agent. This project values reproducible,
reviewable changes over broad rewrites.

## Before You Start

1. Read `AGENTS.md` and `docs/24_PROJECT_PROGRESS_MAP.md`.
2. Check whether a stable CLI, API, workflow, or test already covers the
   behavior you plan to change.
3. Open an issue before changing a public CLI response shape, DSL schema, or
   review-state transition.

## Development Rules

- Keep Lab, Exam, Grading, and PPT output schema-valid.
- Generated artifacts must enter `WAITING_REVIEW`; do not bypass a human
  decision or add automatic publishing.
- Keep prompts under `prompts/` or `skills/`.
- Put credentials only in local environment variables. Never commit a real
  `.env` file, API key, access token, private key, database password, or local
  customer data.
- Do not execute untrusted learner submissions outside the controlled sandbox
  path.
- Avoid unrelated refactors and preserve JSON CLI compatibility unless the
  issue explicitly approves a breaking change.

## Validation

Run the narrowest useful test first, then run the full suite before opening a
pull request:

```powershell
python -m pytest -q
```

For workflow changes, also run a representative JSON CLI command and verify
that generated output remains review-gated and schema-valid.

## Pull Requests

Describe the problem, the behavioral change, tests run, and any compatibility
or security considerations. Keep each pull request focused. Do not include
generated local stores, IDE metadata, screenshots captured from a personal
environment, or unreviewed model outputs unless they are intentional,
sanitized regression fixtures.
