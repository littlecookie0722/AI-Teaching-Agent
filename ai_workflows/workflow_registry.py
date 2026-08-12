"""Phase 2 workflow registry helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_CONTRACT_PATH = "ai-workflows/phase2-workflow-registry.contract.json"


class WorkflowRegistryError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise WorkflowRegistryError(
            "VALIDATION_ERROR",
            "Workflow Registry 契约不是合法 JSON",
            [{"field": "contract", "reason": str(exc)}],
        ) from exc


def load_phase2_workflow_registry(root: Path = ROOT) -> dict[str, Any]:
    registry_path = root / REGISTRY_CONTRACT_PATH
    if not registry_path.exists():
        raise WorkflowRegistryError(
            "NOT_FOUND",
            "Phase 2 Workflow Registry 不存在",
            [{"field": "registry", "reason": REGISTRY_CONTRACT_PATH}],
        )
    registry = _read_json(registry_path)
    for workflow in registry.get("workflows", []):
        contract_path = root / workflow["contractPath"]
        if not contract_path.exists():
            raise WorkflowRegistryError(
                "VALIDATION_ERROR",
                "Workflow Registry 引用了不存在的契约文件",
                [{"field": f"workflows.{workflow['workflowId']}.contractPath", "reason": workflow["contractPath"]}],
            )
    return registry


def _summarize_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflowId": workflow["workflowId"],
        "title": workflow["title"],
        "phase": workflow["phase"],
        "mode": workflow["mode"],
        "category": workflow["category"],
        "status": workflow["status"],
        "contractPath": workflow["contractPath"],
        "cli": workflow["entrypoints"]["cli"],
        "backend": workflow["entrypoints"]["backend"],
        "outputKinds": workflow["outputKinds"],
        "reviewRequired": workflow["reviewGate"]["reviewRequired"],
        "publishBlockedUntilApproved": workflow["reviewGate"]["publishBlockedUntilApproved"],
        "safety": workflow["safety"],
    }


def list_phase2_workflows(*, root: Path = ROOT, category: str | None = None) -> dict[str, Any]:
    registry = load_phase2_workflow_registry(root)
    workflows = registry.get("workflows", [])
    if category:
        workflows = [workflow for workflow in workflows if workflow.get("category") == category]
    items = [_summarize_workflow(workflow) for workflow in workflows]
    return {
        "registryId": registry["registryId"],
        "phase": registry["phase"],
        "mode": registry["mode"],
        "total": len(items),
        "filters": {"category": category},
        "items": items,
        "safety": registry["safety"],
    }


def get_phase2_workflow(workflow_id: str, *, root: Path = ROOT) -> dict[str, Any]:
    registry = load_phase2_workflow_registry(root)
    for workflow in registry.get("workflows", []):
        if workflow["workflowId"] == workflow_id:
            contract = _read_json(root / workflow["contractPath"])
            return {
                "registryId": registry["registryId"],
                "phase": registry["phase"],
                "mode": registry["mode"],
                "workflow": workflow,
                "contract": contract,
                "safety": registry["safety"],
            }
    raise WorkflowRegistryError(
        "NOT_FOUND",
        "Phase 2 Workflow 不存在",
        [{"field": "workflowId", "reason": workflow_id}],
    )
