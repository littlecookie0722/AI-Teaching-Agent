# Changelog

All notable project changes will be documented here.

## [Unreleased]

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
