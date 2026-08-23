# Changelog

All notable project changes will be documented here.

## [Unreleased]

## [0.1.10] - 2026-08-23

- Fixed product teaching decks silently dropping bullets by writing explicit
  layouts and constraining generated content to each renderer slot capacity.
- Preserved every source Lab step in compact decks by using the final available
  process slot to explicitly aggregate remaining steps instead of silently
  omitting them or overstating the summary.
- Made PPT preflight use the same explicit or inferred layout as rendering and
  report accurate `renderedBulletLimit` / `renderedBulletTotal` values.
- Applied shared title, subtitle, and bullet display limits to PPTX and PNG
  output, with visible ellipses and advisory warnings for oversized legacy DSLs.
- Added 5/6/8-slide content-integrity regression coverage, long Chinese text
  checks, 5/8-slide PowerPoint 2021 compatibility validation, and the full PPT
  artifact path to the existing quick/core regression profile.

## [0.1.9] - 2026-08-23

- Added a productized teaching-presentation path that turns an approved
  `teaching-core` workflow into a deterministic 5-8 slide deck, defaulting to
  six teaching-focused layouts.
- Added local `python-pptx` and Pillow rendering for the PPTX file, 1280x720
  page previews, contact sheet, manifest, integrity metadata, and quality
  preflight signals.
- Added a child presentation workflow, candidate-answer and `gradingRef`
  leakage checks, and a single `WAITING_REVIEW` task without changing the
  approved source teaching package.
- Added Review Center generation, page-by-page review, whole-deck approval,
  and approved-only local PPTX download; no online editor, platform import,
  automatic approval, or publishing is included.
- Bound product-deck preview and download routes to optional Backend API auth
  and registered SHA-256 values, blocked short or truncated answer leakage,
  and retained legacy PPT teaching-content and layout-alias compatibility.

## [0.1.8] - 2026-08-23

- Added review-gated local teaching-package export for `teaching-core`
  workflow runs after Lab, Exam, and Grading are all manually approved.
- Added a deterministic ZIP containing `manifest.json`, the three validated
  DSL files, a candidate-safe Exam preview, and the review summary.
- Kept reviewer and export-time metadata in operation audit only so they do not
  make `manifest.json` or otherwise identical package content nondeterministic.
- Kept export local and atomic: blocked or invalid runs create no package and
  never call platform import, grading sandbox, network, or publish paths.

## [0.1.7] - 2026-08-23

- Added workflow-run-scoped Lab, Exam, and Grading review aggregation with
  derived package status, validation signals, candidate safety, and export
  readiness.
- Added a single teaching-package review strip to the default Review Center,
  with per-artifact approve/reject actions, reviewer capture, and required
  rejection reasons.
- Preserved the existing single-task review APIs and historical `legacy-all`
  workflow behavior; no batch review, publishing, PPT generation, or package
  export was added in this slice.

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
