from __future__ import annotations

from pathlib import Path

import cli.lab_cli as lab_cli
from cli.workspace import default_store_path, resolve_cli_path, workspace_root


def test_explicit_workspace_is_absolute_and_store_uses_it(tmp_path: Path) -> None:
    package_root = tmp_path / "installed"
    package_root.mkdir()
    current = tmp_path / "project"
    current.mkdir()
    workspace = current / "agent-state"
    environment = {"LAB_CLI_WORKSPACE": "agent-state"}

    assert workspace_root(environ=environment, root=package_root, cwd=current) == workspace.resolve()
    assert default_store_path(environ=environment, root=package_root, cwd=current) == workspace.resolve() / ".lab_cli_store.json"


def test_installed_path_resolution_keeps_source_and_outputs_separate(tmp_path: Path) -> None:
    package_root = tmp_path / "installed"
    (package_root / "templates" / "lab").mkdir(parents=True)
    asset = package_root / "templates" / "lab" / "schema.json"
    asset.write_text("{}", encoding="utf-8")
    current = tmp_path / "empty"
    current.mkdir()
    source = current / "source.md"
    source.write_text("# source", encoding="utf-8")
    workspace = tmp_path / "workspace"

    assert resolve_cli_path("source.md", root=package_root, cwd=current, workspace=workspace) == source
    assert resolve_cli_path("templates/lab/schema.json", root=package_root, cwd=current, workspace=workspace) == asset
    assert resolve_cli_path("examples/output/generated.json", root=package_root, cwd=current, workspace=workspace) == workspace / "examples/output/generated.json"


def test_presentation_workspace_uses_resolved_user_workspace(tmp_path: Path, monkeypatch) -> None:
    package_root = tmp_path / "installed"
    user_workspace = tmp_path / "user-workspace"
    package_root.mkdir()
    monkeypatch.setattr(lab_cli, "ROOT", package_root)
    monkeypatch.setattr(lab_cli, "workspace_root", lambda *, root: user_workspace)
    monkeypatch.setenv("CODEX_THREAD_ID", "workspace-test")

    presentation_workspace = lab_cli._create_presentation_workspace("pptx-artifact")

    assert presentation_workspace.is_dir()
    assert presentation_workspace.is_relative_to(user_workspace)
    assert not (package_root / "outputs").exists()
