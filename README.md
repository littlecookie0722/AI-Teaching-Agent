# AI Teaching Agent

AI Teaching Agent is a standalone, Python-based project for turning one
Markdown teaching source into a reviewable, locally exportable Lab and Exam
package and an optional 5-8 slide teaching presentation. It keeps generated
content inside a structured and auditable workflow instead of publishing it
directly.

The core MVP generates linked Lab, Exam, and internal Grading artifacts,
validates them, protects candidate-facing content, and stops for a human
decision before local export. The selected next stage productizes a local PPTX
deck from that approved package and adds page-by-page human review.

## Current MVP

- Generates versioned Lab DSL artifacts from source material.
- Converts a Lab DSL into linked Exam DSL and Grading DSL artifacts.
- Validates the linked Lab, Exam, and Grading artifacts before they continue.
- Creates `WAITING_REVIEW` tasks and records human approve/reject decisions.
- Produces a candidate-safe exam preview that excludes answers and internal
  grading references.
- Exports the reviewed teaching package locally without automatic publishing.
- Generates a 5-8 slide local teaching deck from an approved package, with six
  slides by default.
- Renders a 16:9 PPTX, per-slide PNG previews, and a contact sheet for manual
  page review before whole-deck approval and download.

Automatic grading productization, local entity expansion, MCP/Agent expansion,
external platforms, and additional workbench pages remain frozen. PPT
productization is intentionally limited to local generation, review, and
download; it does not add an online editor or publishing path.

## Architecture

```text
Teaching material
       |
       v
single generation entry
       |
       v
Prompt + provider -> Lab / Exam / Grading DSL
       |
       v
Schema validation -> WAITING_REVIEW -> human decision
       |                                  |
       |                                  v
       |                         candidate-safe preview
       v
local teaching-package export
       |
       v
5-8 slide PPTX -> page review -> whole-deck approval -> local download
```

## Current Status

The project has already demonstrated a broader local-core PoC, including PPT,
controlled grading evidence, local entity persistence, MCP, and Agent paths.
The Lab + Exam/Grading review-and-export workflow is complete. The current PPT
stage derives a local 5-8 slide deck only after those three source tasks are
approved, creates a separate child workflow and `WAITING_REVIEW` task, and
requires every rendered page to be reviewed before whole-deck approval. It is
not a hosted service, online editor, cloud resource manager, or automatic
publishing system.

The detailed delivery boundaries, implemented capabilities, and stop lines are
maintained in [the project progress map](docs/24_PROJECT_PROGRESS_MAP.md).
The selected generation and review entry points, compatibility strategy, and
next implementation slices are recorded in
[the simplified MVP entrypoint decision](docs/28_SIMPLIFIED_MVP_ENTRYPOINTS.md).

## Installation

Requirements: Python 3.11 or later. The default installation includes the
offline DSL/CLI runtime plus `python-pptx` and Pillow for local presentation
rendering. Docker is needed only for explicit controlled grading, and no model
SDK or database driver is installed unless selected.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
ai-teaching-agent --help
ai-teaching-agent quality regression-profiles
```

Use extras for the capability you are developing or running:

```powershell
python -m pip install ".[dev]"       # pytest and wheel-build checks
python -m pip install ".[llm]"       # OpenAI-compatible provider SDK
python -m pip install ".[postgres]"  # PostgreSQL adapter
python -m pip install ".[mysql]"     # MySQL adapter
python -m pip install ".[dev,llm,postgres,mysql]"
```

`python -m pip install -r requirements.txt` remains the backward-compatible
all-features development entry point.

## Quick Start

From a Git checkout, the installed console command and the historical
`python lab_cli.py` shim invoke the same JSON CLI:

```powershell
ai-teaching-agent lab generate-from-source --input examples/input/demo-source.md
ai-teaching-agent exam generate-from-lab --lab templates/lab/examples/basic-lab.yaml
ai-teaching-agent teaching-package export --workflow-run-id <workflowRunId> --reviewer teacher_1
ai-teaching-agent ppt generate-from-teaching-package --workflow-run-id <approvedWorkflowRunId> --reviewer teacher_1 --slide-count 6
ai-teaching-agent demo offline
ai-teaching-agent quality dsl-eval --output examples/output/dsl-quality-eval.json
python -m pytest -q
```

Build and inspect the same wheel boundary used by CI with:

```powershell
python -m pip install ".[dev]"
python -m build --wheel
python -m pytest tests/test_packaging.py -q
```

The wheel includes the schemas, prompts, local runtime contracts, MCP manifest,
frontend static assets, and controlled-grading image recipe used by installed
commands. Repository-only historical outputs under `examples/output/` are
deliberately excluded. In a source checkout, the historical repository-local
staging behavior is preserved. After installing a wheel, generated artifacts
and task state go to a per-user workspace instead of `site-packages`; inspect
the resolved location with `ai-teaching-agent workspace info` or set
`LAB_CLI_WORKSPACE` to an explicit directory. The installed `exam
generate-from-lab` path also keeps its task-specific Exam, Grading, and
candidate-preview JSON artifacts in that workspace, and `ppt generate` writes
its task-specific PPT DSL there as well. The `ppt artifact build` command also
keeps its temporary presentation workspace outside `site-packages` and writes
the PPTX artifact and previews to the user workspace. Presentation rendering
uses the installed Python dependencies and does not require Node.js or an
external presentation runtime. Approval and local import-preview can continue
from the same directory.

After a `teaching-core` run has three manually approved tasks, `teaching-package
export` writes `examples/output/teaching-packages/<workflowRunId>.zip` in the
resolved workspace unless `--output` is provided. The ZIP contains exactly the
manifest, Lab/Exam/Grading JSON, candidate-safe Exam preview, and review summary;
the manifest excludes reviewer and export-time metadata so identical inputs stay
deterministic, while those values are recorded only in the operation audit. The
export does not call platform import, grading execution, or publishing paths.

After that source workflow is approved, `ppt generate-from-teaching-package`
creates a separate child workflow under
`examples/output/teaching-presentations/<childWorkflowRunId>/`. The directory
contains `presentation.json`, `presentation.pptx`, six page previews by
default, a contact sheet, and `manifest.json`. Generation revalidates the source
contracts and blocks answer text or internal `gradingRef` values from visible
slides. The Review Center exposes only authenticated, registered local preview
URLs, verifies their recorded SHA-256 values when serving bytes, requires all
pages to pass manual review, and allows PPTX download only after the deck task
is approved.

Every CLI command returns a JSON envelope. The default provider mode is local
mock data. A real OpenAI-compatible model request requires explicit opt-in,
environment-provided credentials, and still creates a `WAITING_REVIEW` task.

The no-key offline demo is the shortest end-to-end check:

```powershell
ai-teaching-agent demo offline
```

It validates the four local Lab/Exam/Grading/PPT DSL fixtures, creates a
candidate-safe Exam preview, and confirms that generated work remains in
`WAITING_REVIEW` with publishing blocked until approval. It does not call a
model, read credentials, access the network, execute learner code, or publish.
The default outputs are written under `examples/output/` in a checkout and are
mapped into the user workspace for installed runs; pass `--output`,
`--workflow-output`, and `--candidate-preview-output` to choose another
writable directory.

The offline quality command evaluates 20 sanitized, review-gated Lab/Exam/
Grading/PPT bundles across five teaching domains, Chinese and English, and
normal/boundary variants. It performs the same Draft 2020-12 validation used by
runtime workflows, plus linked-score, grading-reference, candidate-safety, and
minimum-content checks. It is deterministic and does not call a model or run
learner code; see [the quality guide](quality/README.md).

PPTX artifact builds also include a local advisory preflight report. It checks
slide titles, body density, long text, and the six-bullet renderer limit; it
does not modify the DSL, approve a task, or publish a deck.

When opening `frontend/ai-tasks.html?agentReport=<workflow-report-json>`, the
AI Task Center forwards the report context to the read-only review summary. A
valid custom report exposes its Lab, Exam, Grading, and PPT artifacts as
synthetic `WAITING_REVIEW` task cards and loads their detail through
`GET /api/review-tasks/{id}?agentReport=...`; this is a display bridge only and
does not create tasks, approve content, publish artifacts, execute a sandbox,
or reveal candidate answers.

The older PPT generation and review pages still retain their direct local
import-preview compatibility, but that path is outside the current product
flow. The default Review Center stops at approved local PPTX download and does
not offer platform import or publishing.

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
