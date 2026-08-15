"""Runtime path policy for source checkouts and installed CLI users."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path


WORKSPACE_ENV = "LAB_CLI_WORKSPACE"
STORE_ENV = "LAB_CLI_STORE"
STORE_FILENAME = ".lab_cli_store.json"
_WORKSPACE_OUTPUT_PREFIX = ("examples", "output")
_PACKAGE_PATH_PREFIXES = (
    "config",
    "examples/input",
    "examples/notebooks",
    "examples/submissions",
    "frontend",
    "mcp-server",
    "prompts",
    "providers",
    "sandbox/images",
    "skills",
    "templates",
)


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_source_checkout(root: Path | None = None) -> bool:
    """Return whether the runtime is executing from the repository checkout."""

    resolved_root = (root or package_root()).resolve()
    return (resolved_root / ".git").exists() or (resolved_root / "examples" / "output").is_dir()


def _absolute(path: Path) -> Path:
    return path.expanduser().resolve()


def workspace_root(
    *,
    environ: Mapping[str, str] | None = None,
    root: Path | None = None,
    cwd: Path | None = None,
) -> Path:
    """Resolve the writable artifact/state directory.

    A source checkout keeps the historical repository-local behavior unless the
    caller explicitly sets ``LAB_CLI_WORKSPACE``. An installed wheel has no
    checkout marker, so it defaults to a per-user data directory instead of
    attempting to write into ``site-packages``.
    """

    env = os.environ if environ is None else environ
    resolved_root = (root or package_root()).resolve()
    current_directory = (cwd or Path.cwd()).resolve()
    configured = str(env.get(WORKSPACE_ENV) or "").strip()
    if configured:
        configured_path = Path(configured).expanduser()
        if not configured_path.is_absolute():
            configured_path = current_directory / configured_path
        return _absolute(configured_path)

    if is_source_checkout(resolved_root):
        return resolved_root

    if sys.platform == "win32":
        base = Path(str(env.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(str(env.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")))
    return _absolute(base / "ai-teaching-agent")


def default_store_path(
    *,
    environ: Mapping[str, str] | None = None,
    root: Path | None = None,
    cwd: Path | None = None,
) -> Path:
    """Resolve the default JSON state file without exposing secret values."""

    env = os.environ if environ is None else environ
    configured = str(env.get(STORE_ENV) or "").strip()
    if configured:
        return Path(configured).expanduser()

    resolved_root = (root or package_root()).resolve()
    if str(env.get(WORKSPACE_ENV) or "").strip():
        return workspace_root(environ=env, root=resolved_root, cwd=cwd) / STORE_FILENAME
    if is_source_checkout(resolved_root):
        return resolved_root / "cli" / STORE_FILENAME
    return workspace_root(environ=env, root=resolved_root, cwd=cwd) / STORE_FILENAME


def _matches_prefix(path: Path, prefix: str) -> bool:
    normalized = path.as_posix().lstrip("./")
    return normalized == prefix or normalized.startswith(prefix + "/")


def _is_workspace_output(path: Path) -> bool:
    return _matches_prefix(path, "/".join(_WORKSPACE_OUTPUT_PREFIX))


def _is_package_asset(path: Path) -> bool:
    return any(_matches_prefix(path, prefix) for prefix in _PACKAGE_PATH_PREFIXES)


def resolve_cli_path(
    value: str | Path,
    *,
    root: Path | None = None,
    cwd: Path | None = None,
    workspace: Path | None = None,
) -> Path:
    """Resolve a CLI path while keeping package assets and user files distinct."""

    path = Path(value).expanduser()
    if path.is_absolute():
        return path

    resolved_root = (root or package_root()).resolve()
    current_directory = (cwd or Path.cwd()).resolve()
    current_path = current_directory / path
    package_path = resolved_root / path
    resolved_workspace = (workspace or workspace_root(root=resolved_root, cwd=current_directory)).resolve()
    explicit_workspace = bool(str(os.environ.get(WORKSPACE_ENV) or "").strip())

    if _is_workspace_output(path):
        if not explicit_workspace and (current_path.exists() or current_path.parent.exists()):
            return current_path
        if not explicit_workspace and (resolved_root / "examples" / "output").is_dir():
            return package_path
        return resolved_workspace / path

    if current_path.exists():
        return current_path
    if package_path.exists():
        return package_path
    if current_path.parent.exists():
        return current_path
    if _is_package_asset(path):
        return package_path
    return current_path


def describe_workspace(
    *,
    environ: Mapping[str, str] | None = None,
    root: Path | None = None,
    cwd: Path | None = None,
) -> dict[str, object]:
    """Return a safe, read-only description suitable for the JSON CLI."""

    env = os.environ if environ is None else environ
    resolved_root = (root or package_root()).resolve()
    resolved_cwd = (cwd or Path.cwd()).resolve()
    resolved_workspace = workspace_root(environ=env, root=resolved_root, cwd=resolved_cwd)
    resolved_store = default_store_path(environ=env, root=resolved_root, cwd=resolved_cwd)
    return {
        "packageRoot": str(resolved_root),
        "currentDirectory": str(resolved_cwd),
        "workspaceRoot": str(resolved_workspace),
        "storePath": str(resolved_store),
        "storageMode": "SOURCE_CHECKOUT_COMPAT" if is_source_checkout(resolved_root) and not env.get(WORKSPACE_ENV) else "USER_WORKSPACE",
        "workspaceEnv": WORKSPACE_ENV,
        "storeEnv": STORE_ENV,
        "relativeOutputNamespace": "examples/output",
        "writesToPackageRoot": False if not is_source_checkout(resolved_root) else not bool(env.get(WORKSPACE_ENV)),
    }
