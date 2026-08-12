"""Phase 2 mock PPT generation workflow helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from materials import MaterialAnalysisError, analyze_material
from providers import ProviderError

from .provider_adapter_workflow import PHASE2_SAFETY, generate_mock_dsl_via_adapter


ROOT = Path(__file__).resolve().parents[1]
PHASE2_PPT_WORKFLOW_ID = "phase2_ppt_generation"
PHASE2_PPT_STEP_BY_KIND = {"ppt": "generate_ppt_dsl"}


class PptWorkflowInputError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _validate_markdown_input(input_path: Path) -> None:
    if input_path.suffix.lower() not in {".md", ".markdown"}:
        raise PptWorkflowInputError(
            "VALIDATION_ERROR",
            "PPT Workflow 仅支持 Markdown 输入",
            [{"field": "input", "reason": "仅支持 .md 或 .markdown"}],
        )


def _read_markdown_source(input_path: Path) -> str:
    try:
        return input_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise PptWorkflowInputError("VALIDATION_ERROR", "Markdown 素材编码不支持", [{"field": "input", "reason": "仅支持 UTF-8"}]) from exc


def _extract_sections(markdown: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
    headings = analysis.get("headings") or []
    if not headings:
        headings = [analysis.get("title") or "课程内容"]
    sections = []
    for index, heading in enumerate(headings[:6], start=1):
        sections.append(
            {
                "id": f"section_{index}",
                "title": heading,
                "source": "markdown_heading",
                "estimatedSlideCount": 1,
            }
        )
    if len(sections) == 1:
        sections.append(
            {
                "id": "section_2",
                "title": "学习目标",
                "source": "material_summary",
                "estimatedSlideCount": 1,
            }
        )
    return sections


def _extract_key_points(markdown: str, analysis: dict[str, Any]) -> list[str]:
    points = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            point = stripped[2:].strip()
            if point:
                points.append(point)
        if len(points) >= 6:
            break
    if not points:
        points = [
            analysis.get("summary", analysis.get("title", "课程内容"))[:120],
            "DSL 先行，生成内容进入人工审核",
            "保持 Mock-only 安全边界",
        ]
    return points[:6]


def build_mock_slide_plan(input_path: Path, analysis: dict[str, Any]) -> dict[str, Any]:
    markdown = _read_markdown_source(input_path)
    sections = _extract_sections(markdown, analysis)
    key_points = _extract_key_points(markdown, analysis)
    slides = [
        {
            "id": "slide_plan_1",
            "type": "title",
            "title": analysis.get("title", "课程课件"),
            "sourceSectionId": sections[0]["id"],
            "speakerNote": "开场介绍课程主题和学习目标。",
        }
    ]
    for index, section in enumerate(sections[1:4], start=2):
        slides.append(
            {
                "id": f"slide_plan_{index}",
                "type": "content",
                "title": section["title"],
                "sourceSectionId": section["id"],
                "bullets": key_points[:3],
                "speakerNote": "围绕素材中的要点展开讲解。",
            }
        )
    if len(slides) == 1:
        slides.append(
            {
                "id": "slide_plan_2",
                "type": "content",
                "title": "学习目标",
                "sourceSectionId": sections[-1]["id"],
                "bullets": key_points[:3],
                "speakerNote": "说明本节课的学习收益。",
            }
        )
    return {
        "id": f"slide_plan_{uuid4().hex[:12]}",
        "mode": "MOCK_ONLY",
        "inputRef": str(input_path),
        "title": analysis.get("title", "课程课件"),
        "sections": sections,
        "keyPoints": key_points,
        "slides": slides,
        "artifactGenerated": False,
        "pptFileGenerated": False,
        "reviewRequired": True,
    }


def _summarize_generation(generation: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "ppt",
        "outputKind": generation["outputKind"],
        "promptId": generation["promptId"],
        "dslId": generation["dslId"],
        "dslPath": generation["dslPath"],
        "status": generation["generatedStatus"],
        "reviewRequired": generation["reviewRequired"],
        "publishBlockedUntilApproved": generation["publishBlockedUntilApproved"],
        "provider": generation["provider"],
        "artifactGenerated": generation.get("artifactGenerated", False),
        "pptFileGenerated": False,
    }


def run_phase2_ppt_generation(
    *,
    input_path: Path,
    reviewer: str,
    trace_id: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    _validate_markdown_input(input_path)
    try:
        material_analysis = analyze_material(input_path, trace_id=trace_id)
    except MaterialAnalysisError as exc:
        raise PptWorkflowInputError(exc.code, exc.message, exc.errors) from exc
    slide_plan = build_mock_slide_plan(input_path, material_analysis)
    try:
        ppt = generate_mock_dsl_via_adapter("ppt", input_ref=str(input_path), trace_id=trace_id, root=root)
    except ProviderError:
        raise
    generated_dsl = {"ppt": _summarize_generation(ppt)}
    return {
        "id": f"phase2_ppt_report_{uuid4().hex[:12]}",
        "workflowId": PHASE2_PPT_WORKFLOW_ID,
        "phase": "Phase 2",
        "mode": "MOCK_ONLY",
        "title": "Phase 2 Mock PPT Generation Workflow",
        "input": str(input_path),
        "reviewer": reviewer,
        "providerAdapter": "mock_provider_adapter",
        "providerInterface": "LLMProvider",
        "workflowContract": "ai-workflows/phase2-ppt-generation.contract.json",
        "providerAdapterContract": "providers/provider-adapter.contract.json",
        "promptManifest": "prompts/manifest.json",
        "materialAnalysis": material_analysis,
        "slidePlan": slide_plan,
        "steps": [
            {
                "name": "validate_input",
                "status": "COMPLETED",
                "inputRef": str(input_path),
                "inputType": "markdown",
                "localOnly": True,
            },
            {
                "name": "analyze_material",
                "status": "COMPLETED",
                "materialAnalysis": {
                    "title": material_analysis["title"],
                    "fileType": material_analysis["fileType"],
                    "riskCount": material_analysis["riskCount"],
                    "unknownShellExecuted": material_analysis["unknownShellExecuted"],
                    "requiresHumanReview": material_analysis["requiresHumanReview"],
                },
            },
            {
                "name": "build_chapter_tree",
                "status": "COMPLETED",
                "sections": slide_plan["sections"],
                "realLlmCalled": False,
            },
            {
                "name": "extract_key_points",
                "status": "COMPLETED",
                "keyPoints": slide_plan["keyPoints"],
                "realLlmCalled": False,
            },
            {
                "name": "build_slide_plan",
                "status": "COMPLETED",
                "slidePlanId": slide_plan["id"],
                "slideCount": len(slide_plan["slides"]),
                "pptFileGenerated": False,
            },
            {
                "name": "generate_ppt_dsl",
                "kind": "ppt",
                "status": ppt["generatedStatus"],
                "generatedStatus": ppt["generatedStatus"],
                "promptId": ppt["promptId"],
                "dslId": ppt["dslId"],
                "dslPath": ppt["dslPath"],
                "provider": ppt["provider"],
                "reviewRequired": ppt["reviewRequired"],
                "publishBlockedUntilApproved": ppt["publishBlockedUntilApproved"],
                "artifactGenerated": ppt.get("artifactGenerated", False),
            },
            {
                "name": "assemble_ppt_review_bundle",
                "status": "COMPLETED",
                "reviewRequired": True,
                "publishBlockedUntilApproved": True,
                "artifactGenerated": False,
                "pptFileGenerated": False,
                "realPublish": False,
            },
        ],
        "generatedDsl": generated_dsl,
        "providerGenerations": {"ppt": ppt},
        "reviewSummary": {
            "generatedStatus": "WAITING_REVIEW",
            "reviewRequired": True,
            "publishBlockedUntilApproved": True,
            "artifactGenerated": False,
            "pptFileGenerated": False,
            "autoPublishAllowed": False,
        },
        "acceptanceSignals": {
            "materialAnalyzed": True,
            "chapterTreeBuilt": True,
            "keyPointsExtracted": True,
            "slidePlanBuiltBeforePptDsl": True,
            "providerAdapterUsed": True,
            "schemaValidated": True,
            "generatedDslWaitingReview": True,
            "artifactGenerationDeferred": True,
            "mockOnly": True,
        },
        "safety": {**PHASE2_SAFETY, "realPptFileCreated": False},
        "traceId": trace_id,
    }
