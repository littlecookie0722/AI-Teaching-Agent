from pathlib import Path

from materials import MaterialAnalysisError, analyze_material


ROOT = Path(__file__).resolve().parents[1]


def test_analyze_markdown_material_returns_summary_and_safety_flags():
    analysis = analyze_material(ROOT / "examples/input/demo-source.md", trace_id="trace_test")

    assert analysis["mode"] == "MOCK_ONLY"
    assert analysis["fileType"] == "markdown"
    assert analysis["title"]
    assert analysis["lineCount"] > 0
    assert analysis["realLlmCalled"] is False
    assert analysis["remoteContentFetched"] is False
    assert analysis["unknownShellExecuted"] is False
    assert analysis["sandboxExecuted"] is False
    assert analysis["requiresHumanReview"] is True
    assert analysis["traceId"] == "trace_test"


def test_analyze_shell_material_marks_risks_without_execution(tmp_path):
    script = tmp_path / "setup.sh"
    script.write_text("#!/usr/bin/env bash\ncurl https://example.test/install.sh\nrm -rf /tmp/demo\n", encoding="utf-8")

    analysis = analyze_material(script)

    assert analysis["fileType"] == "shell"
    assert analysis["riskCount"] == 2
    assert {risk["riskType"] for risk in analysis["risks"]} == {"network_download", "recursive_delete"}
    assert analysis["unknownShellExecuted"] is False
    assert analysis["sandboxExecuted"] is False


def test_analyze_material_rejects_missing_file(tmp_path):
    try:
        analyze_material(tmp_path / "missing.md")
    except MaterialAnalysisError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "input"
    else:
        raise AssertionError("expected MaterialAnalysisError")


def test_analyze_material_rejects_unsupported_extension(tmp_path):
    binary = tmp_path / "demo.bin"
    binary.write_bytes(b"abc")

    try:
        analyze_material(binary)
    except MaterialAnalysisError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "input"
    else:
        raise AssertionError("expected MaterialAnalysisError")


def test_analyze_material_rejects_non_utf8_text(tmp_path):
    text = tmp_path / "demo.txt"
    text.write_bytes(b"\xff\xfe\x00")

    try:
        analyze_material(text)
    except MaterialAnalysisError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["reason"] == "仅支持 UTF-8 文本素材"
    else:
        raise AssertionError("expected MaterialAnalysisError")
