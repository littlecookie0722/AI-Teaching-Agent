# Core Regression Run Evidence

> Last updated: 2026-08-13

This document records the current local core regression run for the AI training platform project. It is an evidence note, not a new gate or a new test runner.

## Scope

- Profile: `core`
- Runner: `python lab_cli.py quality regression-matrix`
- Output: `examples/output/regression-matrix-core.json`
- Marker filter: `not integration and not real_llm_online`
- Safety boundary: predefined pytest profiles only; no shell command string input; no real LLM online call; no production database; no real cloud resource change; no publish.

## Command

```powershell
python lab_cli.py quality regression-matrix --profile core --stop-on-failure --output examples/output/regression-matrix-core.json
```

## Result

```text
success=true
profile=core
commandTotal=9
executedTotal=9
passedTotal=9
failedTotal=0
timeoutTotal=0
stoppedEarly=false
durationMs=20107
```

## Covered Commands

| Command ID | Owner | Result | Test Scope |
| --- | --- | --- | --- |
| `dsl_contract` | DSL | PASSED | `tests/test_dsl_examples.py` |
| `provider_mock_and_workflow` | Provider | PASSED | `tests/test_provider_mock.py`, `tests/test_provider_adapter_workflow.py` |
| `real_llm_offline_schema` | Real LLM | PASSED | `tests/test_real_llm_demo_dsl.py` |
| `backend_asgi_core` | Backend | PASSED | `tests/test_backend_asgi_mount_smoke.py`, `tests/test_backend_deployment_manifest.py` |
| `backend_core_services` | Backend | PASSED | backend core contract/service/task/audit/platform entity service tests |
| `grading_core` | Grading | PASSED | controlled Docker evidence, grading evidence merge, job service, record service and SQLite repository tests |
| `platform_api_contract` | Platform | PASSED | platform contract and adapter tests |
| `mcp_stdio_client` | MCP | PASSED | MCP stdio server/client/manifest tests |
| `frontend_core_manifest` | Frontend | PASSED | `tests/test_frontend_manifest.py` |

## Acceptance

This closes the local "core regression actual run record" slice for the current stage:

1. The existing fixed regression matrix was reused.
2. A real local `core` profile run was executed.
3. JSON evidence was written to `examples/output/regression-matrix-core.json`.
4. The run stayed within local-only safety boundaries.

## Remaining Work

- Record GitHub Actions or external CI artifacts after an actual remote workflow run.
- Add newly important test files to existing profiles only when new core behavior is added.
- Do not create another regression runner, CI shell, or arbitrary command execution path for the same purpose.

## Latest Quick Profile Evidence

This section records the current local quick regression run after adding the Grading stable-v1 full-pass fixture and bringing the existing Frontend core manifest command into the quick profile. It reuses the existing fixed matrix and is not a new gate.

```powershell
python lab_cli.py quality regression-matrix --profile quick --stop-on-failure --output examples/output/regression-matrix-quick.json
```

```text
success=true
profile=quick
commandTotal=9
executedTotal=9
passedTotal=9
failedTotal=0
timeoutTotal=0
stoppedEarly=false
durationMs=21040
```

The `grading_stable_v1` command now includes `tests/test_cli.py::test_grade_stable_v1_mixed_checks_pass_fixture_scores_full_marks`, which verifies the `examples/submissions/mixed-checks-pass` fixture reaches `100/100` in the stable-v1 scoring path.
The `frontend_core_manifest` command now runs in `quick` as well as `core`, so the fast local regression also protects the Review Center, Grading Report, AI Task, and Platform Entities page contracts after frontend core-link fixes.

## Latest Grading Report Safety Summary Rerun

This quick rerun was executed after wiring `reviewerSafetySummary` into the Grading Report frontend and manifest contract.

```text
success=true
profile=quick
commandTotal=9
executedTotal=9
passedTotal=9
failedTotal=0
timeoutTotal=0
stoppedEarly=false
durationMs=21436
```

The rerun keeps the same `quick` profile and output file, `examples/output/regression-matrix-quick.json`. It confirms the new `ReviewerSafetySummary` Grading Report contract is covered by `frontend_core_manifest` without adding another regression runner or gate.

## Latest Offline Demo And Matrix Rerun

This rerun records the first reproducible offline Demo slice. The Demo command
and the fixed pytest profile were both executed from the current checkout on
2026-08-13; earlier `commandTotal=9` entries above remain historical records.

```powershell
python lab_cli.py demo offline `
  --output examples/output/offline-demo-summary.json `
  --workflow-output examples/output/offline-demo-workflow-report.json `
  --candidate-preview-output examples/output/offline-demo-candidate-preview.json
```

```text
success=true
summary.status=PASS
summary.mode=offline
summary.labValidated=true
summary.examValidated=true
summary.gradingValidated=true
summary.pptValidated=true
summary.candidatePreviewSafe=true
summary.reviewStatus=WAITING_REVIEW
summary.blockingIssueTotal=0
summary.safety.realLlmCalled=false
summary.safety.networkAccess=false
summary.safety.sandboxExecuted=false
summary.safety.realPublish=false
```

The fixed matrix was then rerun with the new `offline_demo` command:

```powershell
python lab_cli.py quality regression-matrix --profile quick --stop-on-failure --output examples/output/regression-matrix-quick.json
python lab_cli.py quality regression-matrix --profile core --stop-on-failure --output examples/output/regression-matrix-core.json
```

```text
profile=quick  commandTotal=10  executedTotal=10  passedTotal=10  failedTotal=0
profile=core   commandTotal=13  executedTotal=13  passedTotal=13  failedTotal=0
```

The workflow also invokes `demo offline` before the core matrix and uploads its
summary, workflow report, candidate preview, and CLI envelope as CI artifacts.
The offline Demo remains deterministic and local: it does not call a model,
read credentials, access the network, execute learner code, or publish.
