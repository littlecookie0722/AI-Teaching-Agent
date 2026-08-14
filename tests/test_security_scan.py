from __future__ import annotations

import struct
import zipfile
from pathlib import Path

from scripts import security_scan


def test_security_scan_passes_for_current_tracked_release_tree() -> None:
    assert security_scan.scan() == []


def test_security_scan_does_not_treat_placeholders_as_credentials(tmp_path: Path) -> None:
    path = tmp_path / "fixture.md"
    path.write_text(
        '$env:OPENAI_API_KEY="<your-api-key>"\n'
        "Authorization: Bearer <random-local-token>\n"
        "OPENAI_API_KEY=\n",
        encoding="utf-8",
    )

    assert list(security_scan._text_findings(path)) == []


def test_security_scan_flags_legacy_demo_token_literal(tmp_path: Path) -> None:
    path = tmp_path / "fixture.md"
    legacy_token = "local" + "-dev-token"
    authorization_header = "Authori" + "zation: Bearer "
    path.write_text(authorization_header + legacy_token + "\n", encoding="utf-8")

    rules = {finding.rule for finding in security_scan._text_findings(path)}
    assert "bearer-token-literal" in rules


def test_security_scan_flags_literal_private_email_and_key(tmp_path: Path) -> None:
    path = tmp_path / "fixture.md"
    path.write_text(
        "owner@" + "private.example.test\n"
        "-----BEGIN " + "OPENSSH PRIVATE KEY-----\n"
        "tok" + "en=real-value\n",
        encoding="utf-8",
    )

    rules = {finding.rule for finding in security_scan._text_findings(path)}
    assert {"private-email", "private-key", "credential-assignment"} <= rules


def test_security_scan_checks_metadata_extensions() -> None:
    tracked = {path.suffix.lower() for path in security_scan._tracked_files()}
    assert ".pptx" in tracked
    assert ".png" in tracked
    assert ".ipynb" in tracked


def test_security_scan_flags_png_text_metadata(tmp_path: Path) -> None:
    path = tmp_path / "fixture.png"
    text_chunk = b"author\0" + b"owner@" + b"private.example.test"
    png = (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", len(text_chunk))
        + b"tEXt"
        + text_chunk
        + b"\x00\x00\x00\x00"
        + struct.pack(">I", 0)
        + b"IEND"
        + b"\x00\x00\x00\x00"
    )
    path.write_bytes(png)

    findings = list(security_scan._metadata_findings(path))

    assert [finding.rule for finding in findings] == ["png-text-metadata"]


def test_security_scan_flags_pptx_identity_metadata(tmp_path: Path) -> None:
    path = tmp_path / "fixture.pptx"
    creator = "owner@" + "private.example.test"
    core_xml = (
        "<cp:coreProperties xmlns:cp=\"http://schemas.openxmlformats.org/package/2006/metadata/core-properties\" "
        "xmlns:dc=\"http://purl.org/dc/elements/1.1/\"><dc:creator>"
        + creator
        + "</dc:creator></cp:coreProperties>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("docProps/core.xml", core_xml)

    findings = list(security_scan._metadata_findings(path))

    assert [finding.rule for finding in findings] == ["pptx-core-metadata"]
