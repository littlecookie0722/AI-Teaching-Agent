"""Read-only pre-approve review checks."""

from __future__ import annotations

from typing import Any

from .review_detail import build_pre_approve_review_check_from_models, build_review_detail
from .store import JsonTaskStore


def build_pre_approve_review_check(store: JsonTaskStore, task_id: str) -> dict[str, Any]:
    detail = build_review_detail(store, task_id)
    task = detail.get("task", {}) if detail else {}
    merged = detail.get("mergedGradingEvidence", {}) if detail else {}
    notes = detail.get("reviewDecisionNotes", {}) if detail else {}
    return build_pre_approve_review_check_from_models(task, merged, notes)
