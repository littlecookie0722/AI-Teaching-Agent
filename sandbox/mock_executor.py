"""Phase 1/3 mock sandbox executor facade.

This module never executes contestant code. It only converts an already
validated Grading DSL document into a deterministic mock report.
"""

from __future__ import annotations

from typing import Any

from sandbox.grade_runner import GradingRunner, GradingRunnerError, build_grading_audit_detail, build_grading_report_detail


class MockSandboxExecutor:
    mode = "MOCK_ONLY"

    def run_grading(self, grading: dict[str, Any], trace_id: str) -> dict[str, Any]:
        return GradingRunner().run(grading, trace_id)


def build_mock_grading_report(grading: dict[str, Any], trace_id: str) -> dict[str, Any]:
    return MockSandboxExecutor().run_grading(grading, trace_id)


__all__ = [
    "MockSandboxExecutor",
    "GradingRunnerError",
    "build_mock_grading_report",
    "build_grading_audit_detail",
    "build_grading_report_detail",
]
