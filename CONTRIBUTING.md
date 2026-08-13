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

Before pushing a public-release change, also run the tracked-tree security
scan. It checks text fixtures, Notebook content, Git author/committer identity,
PPTX core metadata, PNG text chunks, and JPEG EXIF without printing matched
values:

```powershell
python scripts/security_scan.py
```

The repository-level Git identity is intentionally local to this checkout. Do
not change global Git configuration for this project:

```powershell
git config --local user.name "littlecookie"
git config --local user.email "littlecookie0722@users.noreply.github.com"
```

## Pull Requests

Describe the problem, the behavioral change, tests run, and any compatibility
or security considerations. Keep each pull request focused. Do not include
generated local stores, IDE metadata, screenshots captured from a personal
environment, or unreviewed model outputs unless they are intentional,
sanitized regression fixtures.
