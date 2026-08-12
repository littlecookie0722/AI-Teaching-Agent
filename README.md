# AI Teaching Agent

AI Teaching Agent is a standalone, Python-based project for turning teaching
materials into reviewable learning artifacts. It keeps LLM-generated content
inside a structured and auditable workflow instead of publishing it directly.

The project is an MVP for maintainers, educators, and developers who need a
repeatable path from source material to teaching experiments, assessment
questions, grading rules, and presentation plans.

## What It Does

- Generates versioned Lab DSL artifacts from source material.
- Converts a Lab DSL into linked Exam DSL and Grading DSL artifacts.
- Produces PPT DSL slide plans from teaching material.
- Validates all four DSL types before a task can continue.
- Creates `WAITING_REVIEW` tasks and records human approve/reject decisions.
- Produces a candidate-safe exam preview that excludes answers and internal
  grading references.
- Runs grading evidence through a controlled local Docker path when explicitly
  requested; the normal workflow never runs unreviewed learner code on the
  host.
- Exposes the stable local capabilities through JSON CLI commands, a minimal
  HTTP/ASGI adapter, and an MCP stdio server.

## Architecture

```text
Teaching material
       |
       v
CLI / HTTP API / MCP stdio
       |
       v
Prompt + provider -> Lab / Exam / Grading / PPT DSL
       |
       v
Schema validation -> WAITING_REVIEW -> human decision
       |                                  |
       |                                  v
       |                         candidate-safe preview
       v
local artifacts, audit events, and SQLite-backed entities
       |
       v
controlled grading evidence (explicit local Docker execution only)
```

## Current Status

The project has reached a local-core MVP: real LLM output can be normalized
into Lab, Exam, Grading, and PPT DSL artifacts; generated content remains
review-gated; local entity persistence and controlled grading evidence are
available. It is not a production hosted service, cloud resource manager, or
automatic publishing system.

The detailed delivery boundaries, implemented capabilities, and stop lines are
maintained in [the project progress map](docs/24_PROJECT_PROGRESS_MAP.md).

## Quick Start

Requirements: Python 3.11 or later and a local Git checkout. Docker is only
needed for the explicit controlled-grading path.

```powershell
python -m pip install -r requirements.txt
python lab_cli.py lab generate-from-source --input examples/input/demo-source.md
python lab_cli.py exam generate-from-lab --lab templates/lab/examples/basic-lab.yaml
python -m pytest -q
```

Every CLI command returns a JSON envelope. The default provider mode is local
mock data. A real OpenAI-compatible model request requires explicit opt-in,
environment-provided credentials, and still creates a `WAITING_REVIEW` task.

For a controlled local grading example, see
[the project progress map](docs/24_PROJECT_PROGRESS_MAP.md) and the fixtures
under `examples/submissions/`.

## Detailed References

- [Project progress map and current stop lines](docs/24_PROJECT_PROGRESS_MAP.md)
- [Real SDK installation execution record](docs/13_REAL_SDK_INSTALL_EXECUTION.md)
- [SDK client boundary execution record](docs/14_REAL_SDK_CLIENT_BOUNDARY_EXECUTION.md)
- [Minimal real LLM request PoC](docs/15_REAL_LLM_MINIMAL_POC.md)
- [Real LLM workflow reconnect record](docs/16_REAL_LLM_WORKFLOW_RECONNECT.md)

Historical execution records retained for project compatibility: 真实 SDK 安装执行收口已完成。真实 SDK 环境变量与 client 构造边界已完成。

- 真实 SDK 安装执行收口已完成: `python -m pip install -r requirements.txt` and
  `python -c "import openai; print(openai.__version__)"`.
- 真实 SDK 环境变量与 client 构造边界已完成: `clientCreated=true`.
- 最小真实 LLM 单请求 PoC 已实现: `provider real-llm-minimal-poc run`.
- 真实 LLM Lab Workflow 回接已实现: `phase2 workflow run --provider-mode real-llm-minimal`.

## Project Layout

```text
agents/          Local agent orchestration and replay records
ai_workflows/    Lab, Exam, Grading, and PPT generation workflows
backend/         Local HTTP/ASGI adapters and persistence services
cli/             JSON CLI implementation and review helpers
frontend/        Standalone local UI prototypes
mcp_server/      MCP stdio server and tool adapters
prompts/         Versioned prompt sources and prompt manifest
sandbox/         Controlled grading and evidence generation
templates/       Lab, Exam, Grading, and PPT schemas and examples
tests/           Regression and contract tests
docs/            Architecture, workflow, and project-progress documentation
```

## Development

Read [AGENTS.md](AGENTS.md) before modifying the project. It defines the DSL,
review, secret-handling, sandbox, and compatibility boundaries. In particular:

- Keep prompts in `prompts/` or `skills/`, never inline in business logic.
- Keep generated artifacts review-gated.
- Do not add credentials to source control or logs.
- Do not execute untrusted learner code outside the controlled grading path.
- Prefer a focused test run for the changed module, then run the full suite
  before a release.

Contribution and security-reporting guidance is available in
[CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

This project is licensed under the [MIT License](LICENSE).
