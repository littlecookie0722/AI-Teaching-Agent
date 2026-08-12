import os
import shutil
from pathlib import Path

import pytest


def presentations_runtime_available() -> bool:
    node_override = os.environ.get("CODEX_NODE_EXE")
    node_available = shutil.which(node_override or "node") is not None
    if not node_available and node_override:
        node_available = Path(node_override).expanduser().is_file()
    if not node_available:
        return False

    skill_override = os.environ.get("PRESENTATIONS_SKILL_DIR")
    if skill_override:
        skill_dirs = [Path(skill_override)]
    else:
        runtime_root = Path.home() / ".codex" / "plugins" / "cache" / "openai-primary-runtime" / "presentations"
        skill_dirs = [path / "skills" / "presentations" for path in runtime_root.glob("*") if path.is_dir()]
    return any(
        (skill_dir / "container_tools" / "artifact_tool_utils.mjs").is_file()
        or (skill_dir / "scripts" / "artifact_tool_utils.mjs").is_file()
        for skill_dir in skill_dirs
    )


requires_presentations_runtime = pytest.mark.skipif(
    not presentations_runtime_available(),
    reason="requires Node.js and the optional Codex presentations runtime",
)
