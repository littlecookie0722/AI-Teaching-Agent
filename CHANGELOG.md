# Changelog

All notable project changes will be documented here.

## [Unreleased]

## [0.1.6] - 2026-08-23

- Added the compatible `teaching-core` artifact profile to the existing
  content-generation API, producing only linked Lab, Exam, and Grading DSL.
- Added a candidate-safe Exam preview and teaching-package generation summary
  before the three tasks enter `WAITING_REVIEW`.
- Switched the default generation workspace to the three-artifact teaching
  package while preserving the historical four-artifact API behavior when no
  profile is supplied.
- Ensured real-LLM teaching-core runs skip the PPT request and generation,
  Schema, profile, or redaction failures create no review tasks.
- Included the Phase 2 content-generation contract in the installable wheel.

## [0.1.5] - 2026-08-22

- Connected PPT generation and review pages to the existing local PPT Deck
  import-preview and mock-import APIs.
- Added PPT Deck preparation to the Platform Entities workflow, including
  repository-aware import preview, mock import, and import dry-run output.
- Preserved Core SQLite, Grading SQLite, and workflow-report context through
  PPT import navigation while keeping approval and publishing boundaries.
- Added frontend contract coverage for the four-kind local import workflow.

## [0.1.4] - 2026-08-22

- Made the AI Task Center aware of `agentReport` workflow batches.
- Forwarded report, Core SQLite, and Grading SQLite context through the
  read-only task summary and review-detail requests.
- Rendered report-backed Lab, Exam, Grading, and PPT artifacts as synthetic
  read-only task cards when the local task list is empty, while keeping review,
  publishing, and candidate-answer boundaries unchanged.
- Added frontend contract coverage for the report-aware task/detail path.

## [0.1.3] - 2026-08-16

- Added a deterministic, advisory PPT quality preflight to `ppt artifact
  build` and the replayed Demo Bundle.
- Reported empty titles, long text, dense slide bodies, and bullets truncated
  by the renderer in the build JSON, manifest, Artifact metadata, and page QA
  signals.
- Added unit coverage and a fixed quick/core regression command for PPT
  preflight results; PPTX generation remains `WAITING_REVIEW` and never auto
  publishes.

## [0.1.2] - 2026-08-16

- Packaged the PPTX DSL builder with the installable CLI so `ppt artifact
  build` works outside a source checkout when the optional presentation runtime
  is available.
- Routed temporary PPTX build workspaces through `LAB_CLI_WORKSPACE` and kept
  generated PPTX files, manifests, and previews out of `site-packages`.
- Added wheel asset and installed-workspace regression coverage for the PPTX
  artifact path.

## [0.1.1] - 2026-08-15

- Added a reproducible `demo offline` CLI path that validates the local
  Lab/Exam/Grading/PPT workflow, writes a candidate-safe preview, and keeps
  generated artifacts behind `WAITING_REVIEW`.
- Added offline Demo coverage to the fixed quick/core regression profiles and
  the core GitHub Actions workflow.
- Added installed CLI workspace support for generated task state, DSL
  artifacts, review details, approvals, and local import previews.

## [0.1.0] - 2026-08-12

- Added versioned Lab, Exam, Grading, and PPT DSL schemas and examples.
- Added JSON CLI, local HTTP/ASGI, and MCP stdio entry points.
- Added review-gated generation, candidate-safe previews, and audit records.
- Added controlled local grading evidence and SQLite-backed entity staging.
- Added contributor guidance, security guidance, and GitHub Actions regression
  coverage.
