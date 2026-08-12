"""Distribution-level smoke test for the installable CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_WHEEL_ASSETS = {
    "config/runtime.contract.json",
    "evals/dsl_quality/v1/manifest.json",
    "evals/dsl_quality/v1/baseline-bundle.json",
    "frontend/ui.manifest.json",
    "mcp-server/tools.manifest.json",
    "prompts/manifest.json",
    "prompts/workflows/lab_generation.md",
    "sandbox/images/python-pytest/Dockerfile",
    "templates/lab/lab.schema.json",
}


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        timeout=180,
    )
    assert completed.returncode == 0, (
        f"command failed: {command}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    return completed


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _console_script(environment: Path) -> Path:
    return environment / ("Scripts/ai-teaching-agent.exe" if os.name == "nt" else "bin/ai-teaching-agent")


def test_wheel_installs_and_runs_from_outside_checkout(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    outside_checkout = tmp_path / "outside-checkout"
    environment = tmp_path / "venv"
    dist_dir.mkdir()
    outside_checkout.mkdir()

    _run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist_dir), str(ROOT)],
        cwd=outside_checkout,
    )
    wheels = list(dist_dir.glob("ai_teaching_agent-*.whl"))
    assert len(wheels) == 1
    wheel = wheels[0]

    with zipfile.ZipFile(wheel) as archive:
        wheel_members = set(archive.namelist())
    assert REQUIRED_WHEEL_ASSETS <= wheel_members
    assert not any(member.startswith("tests/") for member in wheel_members)
    assert not any(member.startswith("examples/output/") for member in wheel_members)

    venv.EnvBuilder(with_pip=True).create(environment)
    python = _venv_python(environment)
    console = _console_script(environment)
    _run(
        [str(python), "-m", "pip", "install", "--disable-pip-version-check", str(wheel)],
        cwd=outside_checkout,
    )

    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)
    clean_env.pop("PYTHONIOENCODING", None)
    clean_env["LAB_CLI_STORE"] = str(tmp_path / "read-only-smoke-store.json")

    help_result = _run([str(console), "--help"], cwd=outside_checkout, env=clean_env)
    assert "usage:" in help_result.stdout.lower()

    smoke_result = _run(
        [str(console), "quality", "regression-profiles"],
        cwd=outside_checkout,
        env=clean_env,
    )
    payload = json.loads(smoke_result.stdout)
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["regressionProfiles"]["defaultProfile"] == "quick"

    dsl_result = _run(
        [
            str(console),
            "dsl",
            "validate",
            "--kind",
            "lab",
            "--file",
            "templates/lab/examples/basic-lab.yaml",
        ],
        cwd=outside_checkout,
        env=clean_env,
    )
    dsl_payload = json.loads(dsl_result.stdout)
    assert dsl_payload["success"] is True
    assert dsl_payload["data"]["dslId"] == "lab_demo"

    mcp_result = _run(
        [str(console), "mcp", "server-info"],
        cwd=outside_checkout,
        env=clean_env,
    )
    mcp_payload = json.loads(mcp_result.stdout)
    assert mcp_payload["success"] is True
    assert mcp_payload["data"]["toolPolicy"]["source"] == "mcp-server/tools.manifest.json"

    quality_result = _run(
        [str(console), "quality", "dsl-eval"],
        cwd=outside_checkout,
        env=clean_env,
    )
    quality_payload = json.loads(quality_result.stdout)
    quality_report = quality_payload["data"]["dslQualityEvaluation"]
    assert quality_report["success"] is True
    assert quality_report["summary"]["caseTotal"] == 20
    assert not Path(clean_env["LAB_CLI_STORE"]).exists()

    asset_result = _run(
        [
            str(python),
            "-c",
            (
                "from pathlib import Path; import cli; "
                "from cli.dsl import load_schema, load_yaml, validate_dsl; "
                "root = Path(cli.__file__).resolve().parents[1]; "
                "document = load_yaml(root / 'templates/lab/examples/basic-lab.yaml'); "
                "validate_dsl(document, load_schema('lab', root)); "
                "print(document['kind'])"
            ),
        ],
        cwd=outside_checkout,
        env=clean_env,
    )
    assert asset_result.stdout.strip() == "Lab"

    location_result = _run(
        [
            str(python),
            "-c",
            (
                "from pathlib import Path; import cli, sys; "
                "path = Path(cli.__file__).resolve(); "
                "assert Path(sys.prefix).resolve() in path.parents, (sys.prefix, path); "
                "print(path)"
            ),
        ],
        cwd=outside_checkout,
        env=clean_env,
    )
    assert str(ROOT) not in location_result.stdout
