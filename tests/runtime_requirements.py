from importlib import util

import pytest


def presentations_runtime_available() -> bool:
    return util.find_spec("pptx") is not None and util.find_spec("PIL") is not None


requires_presentations_runtime = pytest.mark.skipif(
    not presentations_runtime_available(),
    reason="requires python-pptx and Pillow",
)
