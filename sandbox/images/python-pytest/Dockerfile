FROM python:3.11-slim

LABEL org.opencontainers.image.title="AI Training Platform Python Pytest Grading Image"
LABEL org.opencontainers.image.version="0.1"
LABEL ai-training-platform.sandbox="controlled-command"
LABEL ai-training-platform.sandbox.profile="local-python-pytest-controlled-v1"
LABEL ai-training-platform.sandbox.execution="local-only-no-network"

RUN python -m pip install --no-cache-dir pytest==9.0.2

WORKDIR /workspace/submission
