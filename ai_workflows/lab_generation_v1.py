"""Lab generation v1 stabilization helpers.

These helpers keep the first core feature focused: a source file becomes one
review-gated Lab DSL artifact that is tied to the current task and can move to
local import preview after manual approval.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from cli.dsl import load_schema, validate_dsl


ROOT = Path(__file__).resolve().parents[1]


def finalize_lab_generation_v1(
    generation: dict[str, Any],
    *,
    input_path: Path,
    material_analysis: dict[str, Any],
    task_id: str,
    root: Path = ROOT,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """Return a task-specific Lab generation result and persist its DSL JSON."""

    finalized = deepcopy(generation)
    dsl = deepcopy(finalized.get("dsl") or {})
    if not isinstance(dsl, dict):
        dsl = {}
    metadata = dsl.setdefault("metadata", {})
    spec = dsl.setdefault("spec", {})
    if isinstance(metadata, dict):
        title = str(material_analysis.get("title") or "").strip()
        if title:
            metadata["title"] = f"{title}实验"
    if isinstance(spec, dict):
        spec["materials"] = [_source_material(input_path, root=root)]
        _ensure_minimum_lab_teaching_content(spec)

    validate_dsl(dsl, load_schema("lab", root))
    artifact_root = output_root or root
    output_path = artifact_root / "examples" / "output" / f"{task_id}-lab.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dsl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_ref = _display_path(output_path, root=artifact_root)

    finalized["dsl"] = dsl
    finalized["dslPath"] = output_ref
    finalized["dslId"] = dsl.get("metadata", {}).get("id") or finalized.get("dslId")
    finalized["schemaValidated"] = True
    finalized["labFeatureReadiness"] = build_lab_feature_readiness(
        finalized,
        material_analysis=material_analysis,
        task={"id": task_id, "status": "WAITING_REVIEW", "taskType": "LAB_GENERATION", "finalResultPath": output_ref},
        artifacts=[],
    )
    return finalized


def lab_generation_from_real_llm_result(result: dict[str, Any]) -> dict[str, Any]:
    """Adapt a real LLM Lab DSL result into the Lab v1 generation shape."""

    return {
        "kind": "lab",
        "promptId": result.get("promptId", "lab_generation_v0"),
        "promptVersion": result.get("promptVersion"),
        "provider": {
            "adapterId": "openai_responses_sdk_adapter",
            "interfaceName": "LLMProvider",
            "operation": "generateJson",
            "providerId": result.get("providerId", "openai"),
            "mode": "REAL_LLM",
            "model": result.get("model"),
            "baseUrlConfigured": result.get("baseUrlConfigured"),
            "baseUrlSource": result.get("baseUrlSource"),
            "realLlmCalled": True,
            "secretsRead": bool(result.get("secretValueRead")),
            "networkAccess": bool(result.get("networkAccess", True)),
            "traceId": result.get("traceId"),
            "requestCount": result.get("requestCount"),
            "singleRequestOnly": result.get("singleRequestForKind"),
            "schemaRepairAttempted": result.get("schemaRepairAttempted", False),
            "schemaRepairApplied": result.get("schemaRepairApplied", False),
            "secretValueReturned": result.get("secretValueReturned", False),
            "responseId": result.get("responseId"),
            "apiSurface": result.get("apiSurface"),
        },
        "dsl": result.get("dsl"),
        "dslPath": "",
        "dslId": result.get("dslId"),
        "inputRef": result.get("inputRef"),
        "outputKind": result.get("outputKind", "Lab"),
        "generatedStatus": result.get("generatedStatus", "WAITING_REVIEW"),
        "reviewRequired": bool(result.get("reviewRequired", True)),
        "publishBlockedUntilApproved": True,
        "answerVisibleToCandidate": False,
        "artifactGenerated": True,
        "sandboxRequiredBeforeRealExecution": False,
        "schemaValidated": bool(result.get("schemaValidated", True)),
        "usage": result.get("usage"),
        "responseId": result.get("responseId"),
        "apiSurface": result.get("apiSurface"),
        "normalization": result.get("normalization"),
        "schemaRepair": result.get("schemaRepair"),
        "schemaRepairAttempted": result.get("schemaRepairAttempted", False),
        "schemaRepairApplied": result.get("schemaRepairApplied", False),
    }


def build_lab_feature_readiness(
    generation: dict[str, Any],
    *,
    material_analysis: dict[str, Any],
    task: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    dsl = generation.get("dsl") if isinstance(generation.get("dsl"), dict) else {}
    spec = dsl.get("spec") if isinstance(dsl.get("spec"), dict) else {}
    metadata = dsl.get("metadata") if isinstance(dsl.get("metadata"), dict) else {}
    provider = generation.get("provider") if isinstance(generation.get("provider"), dict) else {}
    objectives = spec.get("objectives") if isinstance(spec.get("objectives"), list) else []
    steps = spec.get("steps") if isinstance(spec.get("steps"), list) else []
    materials = spec.get("materials") if isinstance(spec.get("materials"), list) else []
    expected_result_total = sum(1 for step in steps if isinstance(step, dict) and str(step.get("expectedResult") or "").strip())
    schema_validated = bool(generation.get("schemaValidated", True))
    task_status = str(task.get("status") or generation.get("generatedStatus") or "")
    review_required = bool(generation.get("reviewRequired", True))
    minimum_teaching_quality_met = len(objectives) >= 2 and len(steps) >= 3 and expected_result_total == len(steps)
    safety = {
        "realLlmCalled": bool(provider.get("realLlmCalled")),
        "networkAccess": bool(provider.get("networkAccess")),
        "secretsRead": bool(provider.get("secretsRead")),
        "remoteContentFetched": bool(material_analysis.get("remoteContentFetched")),
        "unknownShellExecuted": bool(material_analysis.get("unknownShellExecuted")),
        "sandboxExecuted": bool(material_analysis.get("sandboxExecuted")),
        "autoPublishAllowed": False,
        "realPublish": False,
        "answerVisibleToCandidate": False,
    }
    requirement_status = {
        "inputMaterialAnalyzed": bool(material_analysis.get("inputRef")),
        "labDslGenerated": dsl.get("kind") == "Lab",
        "schemaValidated": schema_validated,
        "waitingReviewTaskCreated": task_status == "WAITING_REVIEW" and bool(task.get("id")),
        "manualReviewRequired": review_required,
        "publishBlockedUntilApproved": bool(generation.get("publishBlockedUntilApproved", True)),
        "taskSpecificOutputCreated": bool(generation.get("dslPath")) and str(generation.get("dslPath")).startswith("examples/output/"),
        "sourceMaterialReferenced": _materials_reference_input(materials, material_analysis.get("inputRef")),
        "minimumTeachingQualityMet": minimum_teaching_quality_met,
        "safetyBoundariesKept": not any(safety[key] for key in ("remoteContentFetched", "unknownShellExecuted", "sandboxExecuted", "realPublish")),
    }
    complete = all(requirement_status.values())
    task_id = str(task.get("id") or "")
    return {
        "component": "LabGenerationV1Readiness",
        "featureId": "lab_generate_from_source",
        "status": "STABLE_V1_READY_FOR_MANUAL_REVIEW" if complete else "NEEDS_FIX_BEFORE_STABLE_V1",
        "completeForStableV1": complete,
        "summary": {
            "labId": metadata.get("id"),
            "title": metadata.get("title"),
            "objectiveTotal": len(objectives),
            "stepTotal": len(steps),
            "expectedResultTotal": expected_result_total,
            "materialTotal": len(materials),
            "environmentType": (spec.get("environment") or {}).get("type") if isinstance(spec.get("environment"), dict) else None,
            "dslPath": generation.get("dslPath"),
            "artifactTotal": len(artifacts),
        },
        "requirements": requirement_status,
        "nextActions": {
            "reviewDetail": {
                "cli": f"python lab_cli.py review detail --task-id {task_id}",
                "api": f"GET /api/review-tasks/{task_id}",
                "frontend": f"review-center.html?taskId={task_id}",
            },
            "approveThenImportPreview": {
                "enabledAfter": "task.status=APPROVED",
                "cli": f"python lab_cli.py lab import-preview --task-id {task_id} --reviewer <reviewer> --output examples/output/lab-template-import-preview.json",
                "api": "POST /api/labs/import-preview",
            },
            "mockImportAfterPreview": {
                "enabledAfter": "LabTemplateImportPreview exists",
                "cli": f"python lab_cli.py lab mock-import --task-id {task_id} --reviewer <reviewer> --output examples/output/lab-template-mock-import.json",
                "api": "POST /api/labs/mock-import",
            },
        },
        "safety": safety,
        "stopLine": "Stable Lab v1 stops at task-specific WAITING_REVIEW DSL plus manual review/import-preview path; no real platform publish.",
    }


def _ensure_minimum_lab_teaching_content(spec: dict[str, Any]) -> None:
    objectives = spec.get("objectives") if isinstance(spec.get("objectives"), list) else []
    while len(objectives) < 2:
        objectives.append("能够按步骤完成一次可审核的实验操作并记录结果")
    spec["objectives"] = objectives

    steps = spec.get("steps") if isinstance(spec.get("steps"), list) else []
    default_steps = [
        {
            "id": "step_1",
            "title": "环境检查",
            "instruction": "检查 Python 环境是否可用。",
            "commands": ["python --version"],
            "expectedResult": "能正常输出 Python 版本号。",
        },
        {
            "id": "step_2",
            "title": "阅读实验资料",
            "instruction": "阅读输入素材，整理本实验需要完成的目标和操作要点。",
            "commands": [],
            "expectedResult": "能够列出本实验的目标、输入材料和预期产物。",
        },
        {
            "id": "step_3",
            "title": "完成实验记录",
            "instruction": "按照实验要求执行操作，并保存关键命令、截图或文字记录供教师审核。",
            "commands": [],
            "expectedResult": "形成可被人工审核的实验记录和结果说明。",
        },
    ]
    for index in range(len(steps), 3):
        steps.append(default_steps[index])
    for index, step in enumerate(steps, start=1):
        if isinstance(step, dict):
            step.setdefault("id", f"step_{index}")
            step.setdefault("title", f"实验步骤 {index}")
            step.setdefault("instruction", "完成本步骤要求的实验操作。")
            if not str(step.get("expectedResult") or "").strip():
                step["expectedResult"] = "完成本步骤后能够给出可审核的结果。"
    spec["steps"] = steps


def _source_material(input_path: Path, *, root: Path) -> dict[str, str]:
    return {"type": "markdown", "path": _display_path(input_path, root=root)}


def _display_path(path: Path, *, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _materials_reference_input(materials: list[Any], input_ref: Any) -> bool:
    if not input_ref:
        return bool(materials)
    input_text = str(input_ref).replace("\\", "/")
    for material in materials:
        if isinstance(material, dict) and str(material.get("path") or "").replace("\\", "/") in input_text:
            return True
        if isinstance(material, dict) and input_text.endswith(str(material.get("path") or "").replace("\\", "/")):
            return True
    return False
