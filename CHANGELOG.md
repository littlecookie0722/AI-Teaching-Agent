# Changelog

All notable project changes will be documented here.

## [Unreleased]

- Added a reproducible `demo offline` CLI path that validates the local
  Lab/Exam/Grading/PPT workflow, writes a candidate-safe preview, and keeps
  generated artifacts behind `WAITING_REVIEW`.
- Added offline Demo coverage to the fixed quick/core regression profiles and
  the core GitHub Actions workflow.

## [0.1.0] - 2026-08-12

- Added versioned Lab, Exam, Grading, and PPT DSL schemas and examples.
- Added JSON CLI, local HTTP/ASGI, and MCP stdio entry points.
- Added review-gated generation, candidate-safe previews, and audit records.
- Added controlled local grading evidence and SQLite-backed entity staging.
- Added contributor guidance, security guidance, and GitHub Actions regression
  coverage.
