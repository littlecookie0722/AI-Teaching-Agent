"""Static material analyzer for Phase 1 mock workflows.

The analyzer only reads local text files. It never executes shell commands,
calls a model, fetches remote content, or writes output files.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


MAX_TEXT_BYTES = 256 * 1024
SUPPORTED_EXTENSIONS = {".md", ".markdown", ".sh", ".bash", ".txt"}
SHELL_EXTENSIONS = {".sh", ".bash"}
RISK_PATTERNS = {
    "rm -rf": "recursive_delete",
    "sudo ": "privilege_escalation",
    "curl ": "network_download",
    "wget ": "network_download",
    "Invoke-Expression": "dynamic_execution",
    "iex ": "dynamic_execution",
    "docker run": "container_execution",
    "kubectl ": "cluster_operation",
    "terraform ": "cloud_infra_operation",
}
TECH_PATTERNS = {
    "python": "Python",
    "pytest": "pytest",
    "pandas": "Pandas",
    "jupyter": "Jupyter",
    "notebook": "Notebook",
    "node": "Node.js",
    "docker": "Docker",
    "linux": "Linux",
    "shell": "Shell",
    "bash": "Bash",
    "ai": "AI",
}


class MaterialAnalysisError(Exception):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


@dataclass(frozen=True)
class MaterialRisk:
    pattern: str
    riskType: str
    severity: str
    requiresHumanReview: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MaterialAnalysis:
    inputRef: str
    fileType: str
    title: str
    summary: str
    lineCount: int
    byteSize: int
    detectedTechnologies: list[str]
    headings: list[str]
    risks: list[MaterialRisk]
    mode: str = "MOCK_ONLY"
    realLlmCalled: bool = False
    remoteContentFetched: bool = False
    unknownShellExecuted: bool = False
    sandboxExecuted: bool = False
    requiresHumanReview: bool = True
    traceId: str = field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["risks"] = [risk.to_dict() for risk in self.risks]
        data["riskCount"] = len(self.risks)
        return data


def _read_text(path: Path) -> tuple[str, int]:
    size = path.stat().st_size
    if size > MAX_TEXT_BYTES:
        raise MaterialAnalysisError(
            "VALIDATION_ERROR",
            "素材文件过大",
            [{"field": "input", "reason": f"文件大小超过 {MAX_TEXT_BYTES} bytes"}],
        )
    try:
        return path.read_text(encoding="utf-8"), size
    except UnicodeDecodeError as exc:
        raise MaterialAnalysisError(
            "VALIDATION_ERROR",
            "素材文件编码不支持",
            [{"field": "input", "reason": "仅支持 UTF-8 文本素材"}],
        ) from exc


def _detect_headings(lines: list[str]) -> list[str]:
    headings = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                headings.append(heading)
    return headings[:8]


def _detect_title(path: Path, headings: list[str]) -> str:
    if headings:
        return headings[0]
    return path.stem.replace("-", " ").replace("_", " ").strip() or path.name


def _detect_technologies(text: str) -> list[str]:
    lower = text.lower()
    technologies = {
        label
        for pattern, label in TECH_PATTERNS.items()
        if pattern in lower
    }
    return sorted(technologies)


def _detect_risks(text: str) -> list[MaterialRisk]:
    risks = []
    lower = text.lower()
    for pattern, risk_type in RISK_PATTERNS.items():
        if pattern.lower() in lower:
            severity = "HIGH" if risk_type in {"recursive_delete", "cloud_infra_operation", "cluster_operation"} else "MEDIUM"
            risks.append(MaterialRisk(pattern=pattern, riskType=risk_type, severity=severity))
    return risks


def _summary(title: str, lines: list[str], detected_technologies: list[str], risks: list[MaterialRisk]) -> str:
    non_empty = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    first_sentence = non_empty[0] if non_empty else title
    tech_text = ", ".join(detected_technologies[:5]) if detected_technologies else "未识别明确技术栈"
    risk_text = "存在需人工关注的脚本风险" if risks else "未发现高风险脚本模式"
    return f"{first_sentence[:120]} | 技术栈: {tech_text} | 风险: {risk_text}"


def analyze_material(path: Path, trace_id: str | None = None) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise MaterialAnalysisError("VALIDATION_ERROR", "参数错误", [{"field": "input", "reason": "文件不存在"}])
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise MaterialAnalysisError(
            "VALIDATION_ERROR",
            "不支持的素材类型",
            [{"field": "input", "reason": f"仅支持 {sorted(SUPPORTED_EXTENSIONS)}"}],
        )
    text, size = _read_text(path)
    lines = text.splitlines()
    headings = _detect_headings(lines)
    title = _detect_title(path, headings)
    detected_technologies = _detect_technologies(text)
    risks = _detect_risks(text)
    analysis = MaterialAnalysis(
        inputRef=str(path),
        fileType="shell" if suffix in SHELL_EXTENSIONS else "markdown" if suffix in {".md", ".markdown"} else "text",
        title=title,
        summary=_summary(title, lines, detected_technologies, risks),
        lineCount=len(lines),
        byteSize=size,
        detectedTechnologies=detected_technologies,
        headings=headings,
        risks=risks,
        traceId=trace_id or f"trace_{uuid4().hex[:12]}",
    )
    return analysis.to_dict()
