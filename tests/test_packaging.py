"""Distribution-level smoke test for the installable CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

from tests.runtime_requirements import presentations_runtime_available


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_WHEEL_ASSETS = {
    "ai-workflows/phase2-content-generation.contract.json",
    "cli/teaching_package_export.py",
    "cli/teaching_presentation.py",
    "cli/pptx_artifact.py",
    "config/runtime.contract.json",
    "evals/dsl_quality/v1/manifest.json",
    "evals/dsl_quality/v1/baseline-bundle.json",
    "frontend/ui.manifest.json",
    "mcp-server/tools.manifest.json",
    "prompts/manifest.json",
    "prompts/workflows/lab_generation.md",
    "prompts/workflows/ppt_generation.md",
    "scripts/build_pptx_from_ppt_dsl.mjs",
    "sandbox/images/python-pytest/Dockerfile",
    "templates/lab/lab.schema.json",
    "templates/ppt/ppt.schema.json",
    "templates/ppt/examples/course-ppt.yaml",
}
TEACHING_PACKAGE_MEMBERS = {
    "manifest.json",
    "lab.json",
    "exam.json",
    "grading.json",
    "exam-candidate-preview.json",
    "review-summary.json",
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
        metadata_members = [member for member in wheel_members if member.endswith(".dist-info/METADATA")]
        assert len(metadata_members) == 1
        metadata_lines = archive.read(metadata_members[0]).decode("utf-8").splitlines()
    assert REQUIRED_WHEEL_ASSETS <= wheel_members
    assert "Version: 0.1.9" in metadata_lines
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

    workspace = tmp_path / "user-workspace"
    source = outside_checkout / "source.md"
    source.write_text("# Installed CLI source\n\nTeach a small Python validation lab.\n", encoding="utf-8")
    external_env = dict(clean_env)
    external_env.pop("LAB_CLI_STORE", None)
    external_env["LAB_CLI_WORKSPACE"] = str(workspace)

    workspace_info_result = _run([str(console), "workspace", "info"], cwd=outside_checkout, env=external_env)
    workspace_info = json.loads(workspace_info_result.stdout)
    assert workspace_info["success"] is True
    assert workspace_info["data"]["workspace"]["workspaceRoot"] == str(workspace.resolve())
    assert workspace_info["data"]["workspace"]["storageMode"] == "USER_WORKSPACE"
    package_root = Path(workspace_info["data"]["workspace"]["packageRoot"])

    teaching_core_result = _run(
        [
            str(python),
            "-c",
            (
                "import json, sys; from pathlib import Path; import backend; "
                "from backend.mock_api import handle_request; "
                "assert Path(sys.prefix).resolve() in Path(backend.__file__).resolve().parents; "
                "generated = handle_request("
                "'POST', '/api/phase2/workflows/content-generation/run', "
                "body={'input': sys.argv[1], 'reviewer': 'packaging-test', "
                "'artifactProfile': 'teaching-core'}"
                "); "
                "assert generated['success'], generated; "
                "approvals = [handle_request("
                "'POST', f\"/api/ai-tasks/{task['id']}/approve\", "
                "body={'reviewer': 'packaging-test'}"
                ") for task in generated['data']['createdTasks']]; "
                "assert len(approvals) == 3 and all(item['success'] for item in approvals), approvals; "
                "print(json.dumps({"
                "'workflowRunId': generated['data']['workflowRun']['id'], "
                "'taskIds': [task['id'] for task in generated['data']['createdTasks']]"
                "}))"
            ),
            str(source),
        ],
        cwd=outside_checkout,
        env=external_env,
    )
    teaching_core = json.loads(teaching_core_result.stdout)
    assert len(teaching_core["taskIds"]) == 3
    workflow_run_id = teaching_core["workflowRunId"]

    teaching_package_result = _run(
        [
            str(console),
            "teaching-package",
            "export",
            "--workflow-run-id",
            workflow_run_id,
            "--reviewer",
            "packaging-test",
        ],
        cwd=outside_checkout,
        env=external_env,
    )
    teaching_package_payload = json.loads(teaching_package_result.stdout)
    assert teaching_package_payload["success"] is True
    teaching_package = teaching_package_payload["data"]["teachingPackageExport"]
    package_path = workspace / "examples" / "output" / "teaching-packages" / f"{workflow_run_id}.zip"
    assert Path(teaching_package["outputPath"]).resolve() == package_path.resolve()
    assert package_path.is_file()
    assert not (package_root / "examples" / "output" / "teaching-packages" / package_path.name).exists()
    with zipfile.ZipFile(package_path) as archive:
        assert set(archive.namelist()) == TEACHING_PACKAGE_MEMBERS

    teaching_presentation_result = _run(
        [
            str(console),
            "ppt",
            "generate-from-teaching-package",
            "--workflow-run-id",
            workflow_run_id,
            "--reviewer",
            "packaging-test",
            "--slide-count",
            "6",
        ],
        cwd=outside_checkout,
        env=external_env,
    )
    teaching_presentation_payload = json.loads(teaching_presentation_result.stdout)
    assert teaching_presentation_payload["success"] is True
    teaching_presentation = teaching_presentation_payload["data"]["teachingPresentation"]
    assert teaching_presentation["slideCount"] == 6
    assert teaching_presentation["task"]["status"] == "WAITING_REVIEW"
    presentation_output = Path(teaching_presentation["outputDirectory"])
    assert workspace.resolve() in presentation_output.resolve().parents
    assert presentation_output.is_dir()
    assert Path(teaching_presentation["pptxArtifact"]["path"]).is_file()
    assert len(teaching_presentation["pptxArtifact"]["metadata"]["slidePreviews"]) == 6
    assert not (package_root / "examples" / "output" / "teaching-presentations").exists()

    generation_result = _run(
        [str(console), "lab", "generate-from-source", "--input", "source.md"],
        cwd=outside_checkout,
        env=external_env,
    )
    generation = json.loads(generation_result.stdout)
    assert generation["success"] is True
    task_id = generation["data"]["task"]["id"]
    assert generation["data"]["status"] == "WAITING_REVIEW"
    dsl_path = workspace / generation["data"]["dslPath"]
    assert dsl_path.is_file()
    assert (workspace / ".lab_cli_store.json").is_file()

    detail_result = _run(
        [str(console), "review", "detail", "--task-id", task_id],
        cwd=outside_checkout,
        env=external_env,
    )
    detail = json.loads(detail_result.stdout)
    assert detail["success"] is True
    assert detail["data"]["reviewDetail"]["reviewPage"]["dslPreview"]["contentLoaded"] is True

    approve_result = _run(
        [str(console), "review", "approve", "--task-id", task_id, "--reviewer", "packaging-test"],
        cwd=outside_checkout,
        env=external_env,
    )
    assert json.loads(approve_result.stdout)["data"]["task"]["status"] == "APPROVED"

    import_preview = workspace / "examples" / "output" / "installed-lab-import-preview.json"
    import_result = _run(
        [
            str(console),
            "lab",
            "import-preview",
            "--task-id",
            task_id,
            "--reviewer",
            "packaging-test",
            "--output",
            str(import_preview),
        ],
        cwd=outside_checkout,
        env=external_env,
    )
    import_payload = json.loads(import_result.stdout)
    assert import_payload["success"] is True
    assert import_preview.is_file()

    exam_result = _run(
        [
            str(console),
            "exam",
            "generate-from-lab",
            "--lab",
            "templates/lab/examples/basic-lab.yaml",
        ],
        cwd=outside_checkout,
        env=external_env,
    )
    exam_payload = json.loads(exam_result.stdout)
    assert exam_payload["success"] is True
    exam_task_id = exam_payload["data"]["task"]["id"]
    for output_key in ("examDslPath", "gradingDslPath", "candidatePreviewPath"):
        output_path = Path(exam_payload["data"][output_key])
        assert output_path == Path("examples/output") / output_path.name
        assert (workspace / output_path).is_file()
        assert not (package_root / output_path).exists()

    exam_approve_result = _run(
        [
            str(console),
            "review",
            "approve",
            "--task-id",
            exam_task_id,
            "--reviewer",
            "packaging-test",
        ],
        cwd=outside_checkout,
        env=external_env,
    )
    assert json.loads(exam_approve_result.stdout)["data"]["task"]["status"] == "APPROVED"

    exam_import_result = _run(
        [
            str(console),
            "exam",
            "import-preview",
            "--task-id",
            exam_task_id,
            "--reviewer",
            "packaging-test",
        ],
        cwd=outside_checkout,
        env=external_env,
    )
    assert json.loads(exam_import_result.stdout)["success"] is True
    assert (workspace / "examples/output/exam-question-import-preview.json").is_file()

    grading_import_result = _run(
        [
            str(console),
            "grade",
            "import-preview",
            "--task-id",
            exam_task_id,
            "--reviewer",
            "packaging-test",
        ],
        cwd=outside_checkout,
        env=external_env,
    )
    assert json.loads(grading_import_result.stdout)["success"] is True
    assert (workspace / "examples/output/grading-rule-import-preview.json").is_file()

    ppt_result = _run(
        [
            str(console),
            "ppt",
            "generate",
            "--input",
            "source.md",
        ],
        cwd=outside_checkout,
        env=external_env,
    )
    ppt_payload = json.loads(ppt_result.stdout)
    assert ppt_payload["success"] is True
    ppt_task_id = ppt_payload["data"]["task"]["id"]
    ppt_output_path = Path(ppt_payload["data"]["pptDslPath"])
    assert ppt_output_path == Path("examples/output") / f"{ppt_task_id}-ppt.json"
    assert (workspace / ppt_output_path).is_file()
    assert not (package_root / ppt_output_path).exists()

    ppt_approve_result = _run(
        [
            str(console),
            "review",
            "approve",
            "--task-id",
            ppt_task_id,
            "--reviewer",
            "packaging-test",
        ],
        cwd=outside_checkout,
        env=external_env,
    )
    assert json.loads(ppt_approve_result.stdout)["data"]["task"]["status"] == "APPROVED"

    ppt_import_result = _run(
        [
            str(console),
            "ppt",
            "import-preview",
            "--task-id",
            ppt_task_id,
            "--reviewer",
            "packaging-test",
        ],
        cwd=outside_checkout,
        env=external_env,
    )
    assert json.loads(ppt_import_result.stdout)["success"] is True
    assert (workspace / "examples/output/ppt-deck-import-preview.json").is_file()

    if presentations_runtime_available():
        installed_pptx = workspace / "examples" / "output" / "installed-ppt-artifact.pptx"
        artifact_result = _run(
            [
                str(console),
                "ppt",
                "artifact",
                "build",
                "--dsl",
                "templates/ppt/examples/course-ppt.yaml",
                "--output",
                str(installed_pptx),
                "--reviewer",
                "packaging-test",
            ],
            cwd=outside_checkout,
            env=external_env,
        )
        artifact_payload = json.loads(artifact_result.stdout)
        assert artifact_payload["success"] is True
        assert artifact_payload["data"]["task"]["status"] == "WAITING_REVIEW"
        assert artifact_payload["data"]["artifact"]["kind"] == "PPTX_FILE"
        assert artifact_payload["data"]["artifact"]["metadata"]["qualityReport"]["status"] == "PASS"
        assert artifact_payload["data"]["artifact"]["metadata"]["qualityReport"]["issueTotal"] == 0
        assert installed_pptx.is_file()
        assert not (package_root / "outputs").exists()

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
