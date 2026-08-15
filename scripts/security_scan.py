"""Run the repository's public-release sensitive-information checks.

The scanner is intentionally conservative about reporting: it prints paths,
rules, and line numbers, but never prints the matched value. It is a release
check, not a proof that a repository contains no sensitive information.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
TARGET_NAME = "littlecookie"
TARGET_EMAIL = "littlecookie0722@users.noreply.github.com"

TEXT_SUFFIXES = {
    ".cfg",
    ".conf",
    ".contract",
    ".csv",
    ".html",
    ".ipynb",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".rst",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_FILENAMES = {".env.example", "Dockerfile", "Makefile", "Procfile"}
BINARY_SUFFIXES = {
    ".7z",
    ".db",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".pptx",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".whl",
    ".webp",
    ".zip",
}
SKIP_NAMES = {".env", ".env.local", ".env.development", ".env.production"}
EXAMPLE_SECRET_VALUES = {
    "<your-api-key>",
    "<real-api-key>",
    "<random-local-token>",
    "test-client-boundary-smoke-key",
    "test-client-boundary-secret",
    "hidden-value-that-must-not-leak",
    "test-cli-client-boundary-secret",
    "local-asgi-smoke-token",
    "platform-secret-token",
    "fake-secret-that-must-be-redacted",
    "abcdefghijklmnopqrstuvwxyz",
    "token_1",
}
RESERVED_EMAIL_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "example.invalid",
    "users.noreply.github.com",
}


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    detail: str


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item for item in result.stdout.decode("utf-8").split("\0") if item]


def _display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _text_findings(path: Path) -> Iterable[Finding]:
    if path.name in SKIP_NAMES or (
        path.suffix.lower() not in TEXT_SUFFIXES
        and path.name not in TEXT_FILENAMES
    ) or path.suffix.lower() in BINARY_SUFFIXES:
        return
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    rules = (
        (
            "private-email",
            re.compile(
                r"(?i)(?<![\w.+-])[\w.+-]+@(?P<domain>[\w.-]+\.[a-z]{2,})(?![\w.-])"
            ),
        ),
        (
            "private-key",
            re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY-----"),
        ),
        (
            "credential-assignment",
            re.compile(
                r"(?i)(?<![\"'])\b(?:password|passwd|pwd|token|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret)\s*(?::|=(?!=))\s*(?P<quote>['\"])?(?!<)(?!$)(?P<value>[^\s,'\"}\]]+)"
            ),
        ),
        (
            "bearer-token-literal",
            re.compile(
                r"(?i)\bAuthorization\s*:\s*Bearer\s+(?!<)(?!\$\{)(?!['\"]?\$env)([^\s'\"]+)"
            ),
        ),
        (
            "cloud-key-prefix",
            re.compile(
                r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{20,}\b|\bsk-[A-Za-z0-9_-]{20,}\b"
            ),
        ),
    )
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in rules:
            match = pattern.search(line)
            if not match:
                continue
            if rule == "private-email":
                domain = match.group("domain").lower()
                if domain in RESERVED_EMAIL_DOMAINS:
                    continue
            value = match.group(0)
            if rule == "credential-assignment" and any(
                example in value for example in EXAMPLE_SECRET_VALUES
            ):
                continue
            if rule == "credential-assignment":
                assigned_value = match.group("value").rstrip(".;)")
                if "(" in assigned_value or "[" in assigned_value or "{" in assigned_value:
                    continue
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", assigned_value):
                    continue
            yield Finding(rule, _display(path), f"line {line_number}")


def _metadata_findings(path: Path) -> Iterable[Finding]:
    suffix = path.suffix.lower()
    if suffix == ".pptx":
        try:
            with zipfile.ZipFile(path) as archive:
                raw = archive.read("docProps/core.xml")
            root = ElementTree.fromstring(raw)
        except (KeyError, OSError, ValueError, ElementTree.ParseError):
            return
        for element in root.iter():
            value = (element.text or "").strip()
            if not value:
                continue
            field = element.tag.rsplit("}", 1)[-1]
            if field in {"creator", "lastModifiedBy", "title", "subject", "description", "keywords"}:
                if "@" in value or "\\" in value or re.search(
                    r"(?i)\b(?:company|corp|inc|\.cn|\.com)\b", value
                ):
                    yield Finding("pptx-core-metadata", _display(path), f"field {field}")
    elif suffix == ".png":
        try:
            data = path.read_bytes()
        except OSError:
            return
        position = 8
        while position + 12 <= len(data):
            length = int.from_bytes(data[position : position + 4], "big")
            chunk_type = data[position + 4 : position + 8].decode("latin1", "replace")
            if chunk_type in {"tEXt", "zTXt", "iTXt"}:
                yield Finding("png-text-metadata", _display(path), f"chunk {chunk_type}")
                return
            position += 12 + length
            if chunk_type == "IEND":
                return
    elif suffix in {".jpg", ".jpeg"}:
        try:
            data = path.read_bytes()
        except OSError:
            return
        if b"Exif\x00\x00" in data:
            yield Finding("jpeg-exif-metadata", _display(path), "EXIF block")


def _identity_findings() -> Iterable[Finding]:
    ref = "HEAD"
    result = subprocess.run(
        ["git", "log", "--use-mailmap", ref, "--format=%aN\t%aE\t%cN\t%cE"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for line_number, line in enumerate(result.stdout.splitlines(), start=1):
        parts = line.split("\t")
        if len(parts) != 4:
            yield Finding("git-identity-format", f"git:{ref}", f"entry {line_number}")
            continue
        author_name, author_email, committer_name, committer_email = parts
        if (author_name, author_email) != (TARGET_NAME, TARGET_EMAIL) or (
            committer_name,
            committer_email,
        ) != (TARGET_NAME, TARGET_EMAIL):
            yield Finding("git-identity", f"git:{ref}", f"entry {line_number}")


def scan() -> list[Finding]:
    findings: list[Finding] = []
    for path in _tracked_files():
        findings.extend(_text_findings(path))
        findings.extend(_metadata_findings(path))
    findings.extend(_identity_findings())
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="write a machine-readable report")
    args = parser.parse_args(argv)
    findings = scan()
    report = {
        "success": not findings,
        "mode": "TRACKED_REPOSITORY_RELEASE_SCAN",
        "targetIdentity": {"name": TARGET_NAME, "email": TARGET_EMAIL},
        "findingTotal": len(findings),
        "findings": [finding.__dict__ for finding in findings],
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif findings:
        print("SECURITY_SCAN_FAILED")
        for finding in findings:
            print(f"- {finding.rule}: {finding.path} ({finding.detail})")
    else:
        print("SECURITY_SCAN_PASSED")
        print("- tracked text, Git identity, PPTX core metadata, PNG text metadata, and JPEG EXIF checked")
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
