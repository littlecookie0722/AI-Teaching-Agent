# python-pytest

Minimal local grading image for `CONTROLLED_DOCKER_SANDBOX_POC`.

## 输入说明

- Base image: `python:3.11-slim`.
- Dockerfile installs `pytest==9.0.2`.
- Required local metadata labels: OCI title/version, `ai-training-platform.sandbox=controlled-command`, and `ai-training-platform.sandbox.profile=local-python-pytest-controlled-v1`.
- No secrets or project source files are baked into the image.

## 输出说明

- Local image tag: `ai-grading-python:0.1`.
- The image is used by `grade sandbox-run --execution-mode controlled-command`.

## 命令示例

```powershell
python lab_cli.py grade sandbox-image build
python lab_cli.py grade sandbox-image verify
python lab_cli.py grade sandbox-run --execution-mode controlled-command --grading templates/grading/examples/controlled-command-sandbox.yaml --submission examples/submissions/controlled-command-demo --image ai-grading-python:0.1 --output examples/output/controlled-command-sandbox-report.json
```

## 测试方式

```powershell
python -m pytest tests/test_controlled_command_sandbox_executor.py
```

## 限制说明

- Builds a local Docker image only.
- Does not push images.
- Does not read secrets.
- Does not enable network inside grading containers.
- The execution profile fixes `--network none`, read-only root filesystem and submission mount, `1` CPU, `512m` memory, `64` PIDs, `/tmp` tmpfs, and a maximum 60-second check timeout. Evidence output includes this profile, image inspection metadata, and diagnostic codes.
- `docker build` may need registry/package access depending on the local Docker cache and environment.
