import json
import subprocess
from pathlib import Path

import ai_workflows.provider_adapter_workflow as workflow_module
from cli.lab_cli import main
from tests.runtime_requirements import requires_presentations_runtime


ROOT = Path(__file__).resolve().parents[1]


def run_cli(args, capsys):
    exit_code = main(args)
    output = capsys.readouterr().out
    payload = json.loads(output)
    return exit_code, payload


def assert_json_envelope(payload):
    assert set(payload) >= {"success", "code", "message", "traceId"}
    assert payload["traceId"].startswith("trace_")
    if payload["success"]:
        assert "data" in payload
    else:
        assert "errors" in payload


def fake_controlled_docker_run(args, **kwargs):
    if args[:2] == ["docker", "info"]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout='"29.5.3"', stderr="")
    if args[:3] == ["docker", "image", "inspect"]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="sha256:demo", stderr="")
    command_line = " ".join(str(arg) for arg in args)
    if "main.py" in command_line:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="WAITING_REVIEW\n", stderr="")
    if "pytest" in command_line:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1 passed\n", stderr="")
    raise AssertionError(f"unexpected command: {args}")


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def valid_real_lab_dsl():
    return {
        "version": "1.0",
        "kind": "Lab",
        "metadata": {
            "id": "lab-real-workflow-cli",
            "title": "真实 LLM CLI Workflow 实验",
            "category": "ai-platform",
            "difficulty": "beginner",
            "durationMinutes": 45,
            "tags": ["LLM"],
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "objectives": ["验证真实 LLM Lab DSL CLI 回接"],
            "targetUsers": ["平台开发者"],
            "environment": {"type": "notebook", "image": "python:3.11"},
            "steps": [
                {
                    "id": "step-1",
                    "title": "检查审核状态",
                    "instruction": "确认真实 LLM 生成内容等待人工审核。",
                }
            ],
        },
    }


def fake_real_llm_workflow_result(request):
    lab_dsl = valid_real_lab_dsl()
    return {
        "pocId": "real_llm_minimal_poc",
        "phase": "Phase 2",
        "mode": "REAL_LLM_MINIMAL_SINGLE_REQUEST",
        "providerId": request.provider_id,
        "sdkImportName": "openai",
        "sdkImported": True,
        "clientCreated": True,
        "secretEnv": "OPENAI_API_KEY",
        "secretPresent": True,
        "secretValueRead": True,
        "secretValueReturned": False,
        "secretValueLogged": False,
        "model": request.model,
        "inputRef": request.input_ref,
        "promptId": "lab_generation_v0",
        "promptVersion": "real-llm-minimal-poc-v2",
        "requestSent": True,
        "requestCount": 1,
        "singleRequestOnly": True,
        "batchRequest": False,
        "streaming": False,
        "networkAccess": True,
        "realLlmCalled": True,
        "realCloudResourceChanged": False,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
        "generatedContentCreated": True,
        "schemaValidated": True,
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "reviewBypassed": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "taskCreated": False,
        "outputKind": "Lab",
        "dslId": lab_dsl["metadata"]["id"],
        "responseId": "resp_fake_workflow_cli",
        "usage": {"total_tokens": 51},
        "labDsl": lab_dsl,
        "traceId": request.trace_id,
    }


def valid_real_exam_dsl():
    return {
        "version": "1.0",
        "kind": "Exam",
        "metadata": {
            "id": "exam-real-workflow-cli",
            "title": "真实 LLM CLI Workflow 试题",
            "sourceLabId": "lab-real-workflow-cli",
            "difficulty": "beginner",
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "questionType": "coding_task",
            "totalScore": 100,
            "questions": [
                {
                    "id": "q1",
                    "title": "补全审核状态检查",
                    "stem": "请实现一个函数，返回生成内容是否处于 WAITING_REVIEW。",
                    "score": 100,
                    "gradingRef": "check_waiting_review",
                }
            ],
        },
    }


def valid_real_grading_dsl():
    return {
        "version": "1.0",
        "kind": "Grading",
        "metadata": {
            "id": "grading-real-workflow-cli",
            "title": "真实 LLM CLI Workflow 评分",
            "sourceExamId": "exam-real-workflow-cli",
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "totalScore": 100,
            "timeoutSeconds": 30,
            "checks": [
                {
                    "id": "check_waiting_review",
                    "type": "stdout_contains",
                    "command": "python main.py",
                    "expected": ["WAITING_REVIEW"],
                    "score": 100,
                }
            ],
            "assessmentPlan": [
                {
                    "checkId": "check_waiting_review",
                    "type": "stdout_contains",
                    "runner": "StdoutContainsGrader",
                    "score": 100,
                    "inputSummary": "Check demo output contains WAITING_REVIEW.",
                    "executionPlan": {
                        "strategy": "MOCK_PLAN_ONLY",
                        "requiredLimits": {
                            "cpu": "required",
                            "memory": "required",
                            "timeout": "30s",
                            "network": "disabled_by_default",
                            "filesystem": "isolated_workspace_required",
                            "process": "limited",
                        },
                        "wouldRunInsideRealSandbox": True,
                    },
                    "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
                    "riskLevel": "medium",
                    "sandboxRequiredBeforeRealExecution": True,
                }
            ],
        },
    }


def valid_real_ppt_dsl():
    return {
        "version": "1.0",
        "kind": "PPT",
        "metadata": {
            "id": "ppt-real-workflow-cli",
            "title": "真实 LLM CLI Workflow 课件",
            "audience": "平台开发者",
            "durationMinutes": 30,
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "theme": {"style": "clean", "language": "zh-CN"},
            "slides": [
                {"id": "slide_1", "type": "title", "title": "真实 LLM 演示"},
                {
                    "id": "slide_2",
                    "type": "content",
                    "title": "审核边界",
                    "bullets": ["DSL 先行", "WAITING_REVIEW", "人工审核后发布"],
                },
            ],
        },
    }


def fake_real_demo_workflow_result(request, *, root):
    dsl_by_kind = {
        "lab": valid_real_lab_dsl(),
        "exam": valid_real_exam_dsl(),
        "grading": valid_real_grading_dsl(),
        "ppt": valid_real_ppt_dsl(),
    }
    dsl = dsl_by_kind[request.kind]
    return {
        "demoId": "real_llm_demo_dsl_generation",
        "phase": "Phase 2",
        "mode": "REAL_LLM_DEMO_DSL_GENERATION",
        "providerId": request.provider_id,
        "sdkImportName": "openai",
        "sdkImported": True,
        "clientCreated": True,
        "secretEnv": "OPENAI_API_KEY",
        "secretPresent": True,
        "secretValueRead": True,
        "secretValueReturned": False,
        "secretValueLogged": False,
        "model": request.model,
        "kind": request.kind,
        "outputKind": dsl["kind"],
        "inputRef": request.input_ref,
        "inputPayloadKeys": sorted(request.input_payload or {}),
        "promptId": f"{request.kind}_generation_v0",
        "promptVersion": "real-llm-demo-v1",
        "promptPath": f"prompts/workflows/{request.kind}_generation.md",
        "requestSent": True,
        "requestCount": 1,
        "singleRequestForKind": True,
        "batchRequest": False,
        "streaming": False,
        "networkAccess": True,
        "realLlmCalled": True,
        "realCloudResourceChanged": False,
        "sandboxExecuted": False,
        "contestantCodeExecuted": False,
        "generatedContentCreated": True,
        "schemaValidated": True,
        "generatedStatus": "WAITING_REVIEW",
        "reviewRequired": True,
        "reviewBypassed": False,
        "autoPublishAllowed": False,
        "realPublish": False,
        "taskCreated": False,
        "dslId": dsl["metadata"]["id"],
        "responseId": f"resp_fake_cli_{request.kind}",
        "usage": {"total_tokens": 100 + len(request.kind)},
        "apiSurface": "chat.completions",
        "normalization": {
            "applied": request.kind in {"lab", "ppt"},
            "patches": ["set.metadata.category"] if request.kind == "lab" else (["set.spec.slides[0].bullets"] if request.kind == "ppt" else []),
        },
        "schemaRepair": {
            "attempted": request.kind == "grading",
            "applied": request.kind == "grading",
            "errorCount": 1 if request.kind == "grading" else 0,
        },
        "schemaRepairAttempted": request.kind == "grading",
        "schemaRepairApplied": request.kind == "grading",
        "dsl": dsl,
        "traceId": request.trace_id,
    }


def test_phase2_content_generation_contract_is_mock_only_and_local():
    contract = load_json("ai-workflows/phase2-content-generation.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed_ids = {command["id"] for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["workflowId"] == "phase2_content_generation"
    assert {mode["id"] for mode in contract["providerModes"]} == {"mock", "real-llm-minimal", "real-llm-demo"}
    real_mode = next(mode for mode in contract["providerModes"] if mode["id"] == "real-llm-minimal")
    assert real_mode["workflowMode"] == "REAL_LLM_MINIMAL_LAB_WORKFLOW"
    assert real_mode["realLlmKinds"] == ["lab"]
    assert real_mode["mockKinds"] == ["exam", "grading", "ppt"]
    demo_mode = next(mode for mode in contract["providerModes"] if mode["id"] == "real-llm-demo")
    assert demo_mode["workflowMode"] == "REAL_LLM_DEMO_WORKFLOW"
    assert demo_mode["realLlmKinds"] == ["lab", "exam", "grading", "ppt"]
    assert demo_mode["mockKinds"] == []
    assert demo_mode["requestCount"] == 4
    assert contract["providerAdapter"]["adapterId"] == "mock_provider_adapter"
    assert contract["providerAdapter"]["activeProvider"] == "mock"
    assert contract["providerAdapter"]["realLlmCalled"] is False
    assert contract["optionalRealLlmMinimalLabMode"]["providerMode"] == "real-llm-minimal"
    assert contract["optionalRealLlmMinimalLabMode"]["singleRequestOnly"] is True
    assert contract["optionalRealLlmMinimalLabMode"]["examGradingPptRemainMock"] is True
    assert contract["optionalRealLlmDemoMode"]["providerMode"] == "real-llm-demo"
    assert contract["optionalRealLlmDemoMode"]["requestCount"] == 4
    assert contract["optionalRealLlmDemoMode"]["generatedKinds"] == ["lab", "exam", "grading", "ppt"]
    assert contract["optionalRealLlmDemoMode"]["dslStatus"] == "WAITING_REVIEW"
    assert {item["id"] for item in contract["labGenerationControls"]} == {
        "targetUsers",
        "durationMinutes",
        "difficulty",
        "techTags",
        "teachingStyle",
    }
    assert contract["qualitySignals"]["reviewRequired"] is True
    assert contract["qualitySignals"]["publishBlockedUntilApproved"] is True
    assert "lab.matching" in contract["qualitySignals"]["fields"]
    assert "lab.stepGranularity" in contract["qualitySignals"]["fields"]
    assert "lab.teachingStyleSignal" in contract["qualitySignals"]["fields"]
    assert "materialCoverage.sourceReference" in contract["qualitySignals"]["fields"]
    assert contract["reviewGate"]["defaultGeneratedStatus"] == "WAITING_REVIEW"
    assert contract["reviewGate"]["publishBlockedUntilApproved"] is True
    assert set(contract["recommendedCommandIds"]).issubset(allowed_ids)
    for item in contract["inputs"]:
        assert item["localOnly"] is True
        assert (ROOT / item["path"]).exists()
    for item in contract["outputs"]:
        if not item.get("generated", False):
            assert (ROOT / item["path"]).exists()
        if item["kind"] in {"Lab", "Exam", "Grading", "PPT"}:
            assert item["status"] == "WAITING_REVIEW"
            assert item["reviewRequired"] is True
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["realAgentStarted"] is False
    assert contract["safety"]["realCloudResourceCreated"] is False
    assert contract["safety"]["sandboxExecuted"] is False
    assert contract["safety"]["contestantCodeExecuted"] is False
    assert contract["safety"]["realPublish"] is False


def test_phase2_workflow_run_returns_json_and_records_local_state(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "phase2-report.json"

    exit_code, payload = run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert report_path.exists()
    assert payload["data"]["workflowId"] == "phase2_content_generation"
    assert payload["data"]["phase"] == "Phase 2"
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["providerAdapter"] == "mock_provider_adapter"
    assert payload["data"]["labGenerationContext"]["targetUsers"] == ["高职学生"]
    assert payload["data"]["qualitySignals"]["overall"]["reviewRequired"] is True
    assert [step["name"] for step in payload["data"]["steps"]] == [
        "validate_input",
        "analyze_material",
        "generate_lab_dsl",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "generate_ppt_dsl",
        "assemble_review_bundle",
    ]
    assert {item["status"] for item in payload["data"]["generatedDsl"].values()} == {"WAITING_REVIEW"}
    assert payload["data"]["generatedDsl"]["exam"]["answerVisibleToCandidate"] is False
    assert payload["data"]["generatedDsl"]["ppt"]["artifactGenerated"] is False
    assert payload["data"]["reviewSummary"]["publishBlockedUntilApproved"] is True
    assert payload["data"]["safety"]["realLlmCalled"] is False
    assert payload["data"]["safety"]["realAgentStarted"] is False
    assert payload["data"]["safety"]["realCloudResourceCreated"] is False
    assert payload["data"]["safety"]["sandboxExecuted"] is False
    assert payload["data"]["safety"]["realPublish"] is False
    assert [task["taskType"] for task in payload["data"]["createdTasks"]] == [
        "LAB_GENERATION",
        "EXAM_GENERATION",
        "GRADING_GENERATION",
        "PPT_GENERATION",
    ]
    assert {task["status"] for task in payload["data"]["createdTasks"]} == {"WAITING_REVIEW"}
    assert set(payload["data"]["providerCallAuditEvents"]) == {"lab", "exam", "grading", "ppt"}
    assert {event["detail"]["workflowId"] for event in payload["data"]["providerCallAuditEvents"].values()} == {
        "phase2_content_generation"
    }
    assert payload["data"]["workflowRun"]["workflowId"] == "phase2_content_generation"
    assert payload["data"]["workflowRun"]["realLlmCalled"] is False
    assert payload["data"]["workflowRun"]["realPublish"] is False
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} >= {
        "MATERIAL_ANALYSIS",
        "LAB_DSL",
        "EXAM_DSL",
        "GRADING_DSL",
        "PPT_DSL",
        "WORKFLOW_REPORT",
    }
    assert all(artifact["workflowRunId"] == payload["data"]["workflowRun"]["id"] for artifact in payload["data"]["artifacts"])

    _, listed = run_cli(["workflow", "list", "--workflow-id", "phase2_content_generation"], capsys)
    _, audit = run_cli(["provider", "audit", "--trace-id", payload["traceId"]], capsys)
    assert listed["data"]["total"] == 1
    assert audit["data"]["total"] == 4


def test_phase2_workflow_run_records_lab_context_quality_and_review_detail(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "phase2-report.json"

    exit_code, payload = run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
            "--target-users",
            "高职学生,教师",
            "--duration-minutes",
            "90",
            "--difficulty",
            "intermediate",
            "--tech-tags",
            "Python,Notebook",
            "--teaching-style",
            "project_based",
        ],
        capsys,
    )

    assert exit_code == 0
    data = payload["data"]
    assert data["labGenerationContext"]["targetUsers"] == ["高职学生", "教师"]
    assert data["labGenerationContext"]["durationMinutes"] == 90
    assert data["labGenerationContext"]["difficulty"] == "intermediate"
    assert data["labGenerationContext"]["techTags"] == ["Python", "Notebook"]
    assert data["qualitySignals"]["lab"]["requestedDurationMinutes"] == 90
    assert data["qualitySignals"]["lab"]["matching"]["status"] == "NEEDS_REVIEW"
    assert data["qualitySignals"]["lab"]["matching"]["targetUsers"]["matched"] is False
    assert data["qualitySignals"]["lab"]["matching"]["durationMinutes"]["matched"] is False
    assert data["qualitySignals"]["lab"]["matching"]["difficulty"]["matched"] is False
    assert data["qualitySignals"]["lab"]["matching"]["techTags"]["matched"] is False
    assert data["qualitySignals"]["lab"]["matching"]["teachingStyle"]["matched"] is False
    assert data["qualitySignals"]["lab"]["stepGranularity"]["matched"] is True
    assert data["qualitySignals"]["materialCoverage"]["sourceReferencedInDsl"] is True
    assert data["qualitySignals"]["materialCoverage"]["status"] == "LINKED"
    lab_artifact = next(artifact for artifact in data["artifacts"] if artifact["kind"] == "LAB_DSL")
    assert lab_artifact["metadata"]["generationContext"] == data["labGenerationContext"]
    assert lab_artifact["metadata"]["qualitySignals"]["requestedDurationMinutes"] == 90
    assert lab_artifact["metadata"]["qualitySignals"]["matching"]["status"] == "NEEDS_REVIEW"
    lab_task = next(task for task in data["createdTasks"] if task["taskType"] == "LAB_GENERATION")

    _, detail_payload = run_cli(["review", "detail", "--task-id", lab_task["id"]], capsys)
    review_detail = detail_payload["data"]["reviewDetail"]
    review_page = review_detail["reviewPage"]
    assert review_page["generationProfile"]["context"]["targetUsers"] == ["高职学生", "教师"]
    assert review_page["qualitySignals"]["lab"]["requestedDurationMinutes"] == 90
    assert review_page["qualitySignals"]["lab"]["matching"]["durationMinutes"]["matched"] is False
    assert review_page["qualitySignals"]["lab"]["matching"]["teachingStyle"]["matched"] is False
    assert review_page["qualitySignals"]["lab"]["stepGranularity"]["matched"] is True
    assert review_page["qualitySignals"]["materialCoverage"]["sourceReferencedInDsl"] is True
    assert review_page["qualitySignals"]["overall"]["reviewRequired"] is True
    assert review_page["providerSummary"]["realLlmCalled"] is False
    assert review_detail["safety"]["realLlmCalled"] is False


def test_phase2_workflow_run_rejects_invalid_lab_context(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "phase2-report.json"

    exit_code, payload = run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--output",
            str(report_path),
            "--duration-minutes",
            "0",
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "durationMinutes"
    assert not report_path.exists()


def test_phase2_workflow_run_real_minimal_lab_records_mixed_state(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "phase2-real-report.json"
    lab_output = tmp_path / "phase2-real-lab.json"

    def fake_run(request, *, root):
        calls.append((request, root))
        return fake_real_llm_workflow_result(request)

    monkeypatch.setattr(workflow_module, "run_real_llm_minimal_poc", fake_run)

    exit_code, payload = run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
            "--provider-mode",
            "real-llm-minimal",
            "--real-lab-output",
            str(lab_output),
            "--model",
            "test-model",
            "--target-users",
            "平台开发者",
            "--duration-minutes",
            "45",
            "--tech-tags",
            "LLM",
            "--explicit-real-call-opt-in",
            "--confirm-single-request",
            "--confirm-lab-only",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert len(calls) == 1
    assert calls[0][0].generation_context["targetUsers"] == ["平台开发者"]
    assert calls[0][0].generation_context["durationMinutes"] == 45
    assert calls[0][0].generation_context["techTags"] == ["LLM"]
    assert report_path.exists()
    assert lab_output.exists()
    data = payload["data"]
    assert data["mode"] == "REAL_LLM_MINIMAL_LAB_WORKFLOW"
    assert data["providerMode"] == "real-llm-minimal"
    assert data["providerAdapter"] == "mixed_real_llm_minimal_and_mock_provider_adapter"
    assert data["generatedDsl"]["lab"]["provider"]["realLlmCalled"] is True
    assert data["generatedDsl"]["exam"]["provider"]["realLlmCalled"] is False
    assert data["generatedDsl"]["grading"]["provider"]["realLlmCalled"] is False
    assert data["generatedDsl"]["ppt"]["provider"]["realLlmCalled"] is False
    assert data["safety"]["realLlmCalled"] is True
    assert data["safety"]["networkAccess"] is True
    assert data["safety"]["realPublish"] is False
    assert data["workflowRun"]["mode"] == "REAL_LLM_MINIMAL_LAB_WORKFLOW"
    assert data["workflowRun"]["realLlmCalled"] is True
    assert data["workflowRun"]["realPublish"] is False
    assert [task["taskType"] for task in data["createdTasks"]] == [
        "LAB_GENERATION",
        "EXAM_GENERATION",
        "GRADING_GENERATION",
        "PPT_GENERATION",
    ]
    lab_task = next(task for task in data["createdTasks"] if task["taskType"] == "LAB_GENERATION")
    assert lab_task["status"] == "WAITING_REVIEW"
    assert lab_task["modelName"] == "test-model"
    assert lab_task["promptVersion"] == "real-llm-minimal-poc-v2"
    assert data["providerCallAuditEvents"]["lab"]["realLlmCalled"] is True
    assert data["providerCallAuditEvents"]["lab"]["networkAccess"] is True
    assert data["providerCallAuditEvents"]["lab"]["taskCreated"] is True
    assert data["providerCallAuditEvents"]["exam"]["realLlmCalled"] is False
    lab_artifact = next(artifact for artifact in data["artifacts"] if artifact["kind"] == "LAB_DSL")
    report_artifact = next(artifact for artifact in data["artifacts"] if artifact["kind"] == "WORKFLOW_REPORT")
    assert lab_artifact["realLlmCalled"] is True
    assert lab_artifact["metadata"]["generationContext"]["targetUsers"] == ["平台开发者"]
    assert lab_artifact["metadata"]["qualitySignals"]["provider"]["realLlmCalled"] is True
    assert lab_artifact["metadata"]["qualitySignals"]["matching"]["status"] == "MATCHED"
    assert report_artifact["realLlmCalled"] is True

    _, detail_payload = run_cli(["review", "detail", "--task-id", lab_task["id"]], capsys)
    assert detail_payload["data"]["reviewDetail"]["mode"] == "REAL_LLM_MINIMAL_LAB_WORKFLOW"
    assert detail_payload["data"]["reviewDetail"]["reviewPage"]["providerSummary"]["realLlmCalled"] is True
    assert detail_payload["data"]["reviewDetail"]["safety"]["realLlmCalled"] is True

    _, listed = run_cli(["workflow", "list", "--workflow-id", "phase2_content_generation"], capsys)
    _, audit = run_cli(["provider", "audit", "--trace-id", payload["traceId"]], capsys)
    assert listed["data"]["total"] == 1
    assert audit["data"]["total"] == 4
    assert sum(1 for event in audit["data"]["items"] if event["realLlmCalled"]) == 1


def test_phase2_workflow_run_real_minimal_lab_missing_secret_returns_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    report_path = tmp_path / "phase2-real-report.json"

    exit_code, payload = run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--output",
            str(report_path),
            "--provider-mode",
            "real-llm-minimal",
            "--model",
            "test-model",
            "--explicit-real-call-opt-in",
            "--confirm-single-request",
            "--confirm-lab-only",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "REAL_LLM_MINIMAL_CALL_SECRET_REQUIRED"
    assert payload["providerErrorContext"]["providerId"] == "openai"
    assert payload["failureReportPath"] == str(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "PHASE2_WORKFLOW_FAILURE_REPORT"
    assert report["status"] == "FAILED"
    assert report["code"] == "REAL_LLM_MINIMAL_CALL_SECRET_REQUIRED"
    assert report["providerErrorContext"]["providerId"] == "openai"
    assert report["generatedContentCreated"] is False
    assert report["taskCreated"] is False
    assert report["redaction"]["secretValuesIncluded"] is False
    assert report["safety"]["realPublish"] is False


def test_phase2_workflow_run_real_demo_records_all_generated_dsl(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "phase2-real-demo-report.json"
    lab_output = tmp_path / "demo-real-lab.json"
    exam_output = tmp_path / "demo-real-exam.json"
    grading_output = tmp_path / "demo-real-grading.json"
    ppt_output = tmp_path / "demo-real-ppt.json"

    def fake_run(request, *, root):
        calls.append((request, root))
        return fake_real_demo_workflow_result(request, root=root)

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)

    exit_code, payload = run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
            "--provider-mode",
            "real-llm-demo",
            "--real-demo-lab-output",
            str(lab_output),
            "--real-demo-exam-output",
            str(exam_output),
            "--real-demo-grading-output",
            str(grading_output),
            "--real-demo-ppt-output",
            str(ppt_output),
            "--model",
            "test-model",
            "--target-users",
            "平台开发者",
            "--duration-minutes",
            "45",
            "--tech-tags",
            "LLM",
            "--explicit-real-call-opt-in",
            "--confirm-demo-real-dsl",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert [call[0].kind for call in calls] == ["lab", "exam", "grading", "ppt"]
    assert all(call[0].model == "test-model" for call in calls)
    assert report_path.exists()
    assert lab_output.exists()
    assert exam_output.exists()
    assert grading_output.exists()
    assert ppt_output.exists()
    data = payload["data"]
    assert data["mode"] == "REAL_LLM_DEMO_WORKFLOW"
    assert data["providerMode"] == "real-llm-demo"
    assert data["providerAdapter"] == "openai_responses_sdk_demo_adapter"
    assert data["acceptanceSignals"]["mockOnly"] is False
    assert data["acceptanceSignals"]["realLlmDemoConnected"] is True
    assert data["acceptanceSignals"]["realLlmDemoGeneratedAllDsl"] is True
    assert data["acceptanceSignals"]["realLlmDemoRequestCount"] == 4
    assert data["safety"]["realLlmCalled"] is True
    assert data["safety"]["networkAccess"] is True
    assert data["safety"]["realLlmGeneratedKinds"] == ["lab", "exam", "grading", "ppt"]
    assert data["safety"]["realLlmRequestCount"] == 4
    assert data["safety"]["realPublish"] is False
    assert data["safety"]["sandboxExecuted"] is False
    assert {item["status"] for item in data["generatedDsl"].values()} == {"WAITING_REVIEW"}
    assert {item["provider"]["realLlmCalled"] for item in data["generatedDsl"].values()} == {True}
    assert {item["qualitySummary"]["readyForReview"] for item in data["generatedDsl"].values()} == {True}
    assert data["generatedDsl"]["lab"]["qualitySummary"]["normalizationApplied"] is True
    assert data["generatedDsl"]["lab"]["qualitySummary"]["normalizationPatchCount"] == 1
    assert data["generatedDsl"]["lab"]["qualitySummary"]["normalizationPatches"] == ["set.metadata.category"]
    assert data["generatedDsl"]["grading"]["qualitySummary"]["schemaRepairAttempted"] is True
    assert data["generatedDsl"]["grading"]["qualitySummary"]["schemaRepairApplied"] is True
    assert data["generatedDsl"]["grading"]["qualitySummary"]["schemaRepairErrorCount"] == 1
    assert data["generatedDsl"]["ppt"]["qualitySummary"]["normalizationPatches"] == ["set.spec.slides[0].bullets"]
    assert {item["qualitySummary"]["requestCount"] for item in data["generatedDsl"].values()} == {1}
    assert {item["qualitySummary"]["apiSurface"] for item in data["generatedDsl"].values()} == {"chat.completions"}
    assert data["contentQualitySummary"]["component"] == "RealDslContentQualitySummary"
    assert data["contentQualitySummary"]["manualReviewRequired"] is True
    assert data["contentQualitySummary"]["autoApproveAllowed"] is False
    assert data["contentQualitySummary"]["realPublishAllowed"] is False
    assert data["contentQualitySummary"]["decision"]["component"] == "RealDslContentQualityDecision"
    assert data["contentQualitySummary"]["decisionStatus"] == (
        "READY_FOR_IMPORT_PREVIEW_EVIDENCE_REQUIRED_BEFORE_FINAL_APPROVAL"
    )
    assert data["contentQualitySummary"]["recommendedAction"] == (
        "create_import_previews_then_collect_required_evidence"
    )
    assert data["contentQualitySummary"]["requiresRevisionBeforeImportPreview"] is False
    assert data["contentQualitySummary"]["requiresEvidenceBeforeFinalApproval"] is True
    assert data["contentQualitySummary"]["decision"]["evidenceRequiredKinds"] == ["grading"]
    assert data["contentQualitySummary"]["items"]["exam"]["readyForImportPreview"] is True
    assert data["contentQualitySummary"]["items"]["grading"]["decisionStatus"] == (
        "READY_FOR_IMPORT_PREVIEW_EVIDENCE_REQUIRED_BEFORE_FINAL_APPROVAL"
    )
    assert data["contentQualitySummary"]["items"]["grading"]["recommendedAction"] == (
        "create_import_preview_then_collect_grading_evidence"
    )
    assert data["contentQualitySummary"]["items"]["grading"]["requiresEvidenceBeforeFinalApproval"] is True
    assert data["generatedDsl"]["lab"]["contentQualitySummary"]["kind"] == "lab"
    assert data["generatedDsl"]["lab"]["contentQualitySummary"]["readyForManualReview"] is True
    assert data["generatedDsl"]["lab"]["contentQualitySummary"]["decisionStatus"] == (
        "READY_FOR_IMPORT_PREVIEW_WITH_WARNINGS"
    )
    assert data["generatedDsl"]["lab"]["contentQualitySummary"]["recommendedAction"] == (
        "review_warnings_then_create_lab_import_preview"
    )
    assert data["reviewSummary"]["contentQualitySummary"]["readyForImportPreviewKinds"] == ["lab", "exam", "grading"]
    assert {task["status"] for task in data["createdTasks"]} == {"WAITING_REVIEW"}
    assert {task["modelName"] for task in data["createdTasks"]} == {"test-model"}
    assert {task["promptVersion"] for task in data["createdTasks"]} == {"real-llm-demo-v1"}
    assert data["workflowRun"]["mode"] == "REAL_LLM_DEMO_WORKFLOW"
    assert data["workflowRun"]["realLlmCalled"] is True
    assert data["workflowRun"]["realPublish"] is False
    assert set(data["providerCallAuditEvents"]) == {"lab", "exam", "grading", "ppt"}
    assert all(event["realLlmCalled"] is True for event in data["providerCallAuditEvents"].values())
    assert all(event["networkAccess"] is True for event in data["providerCallAuditEvents"].values())
    assert all(event["taskCreated"] is True for event in data["providerCallAuditEvents"].values())
    dsl_artifacts = [artifact for artifact in data["artifacts"] if artifact["kind"].endswith("_DSL")]
    assert {artifact["realLlmCalled"] for artifact in dsl_artifacts} == {True}
    assert {artifact["metadata"]["providerAdapter"] for artifact in dsl_artifacts} == {"openai_responses_sdk_demo_adapter"}
    assert all(artifact["metadata"]["contentQualitySummary"]["readyForManualReview"] is True for artifact in dsl_artifacts)
    assert all(artifact["metadata"]["workflowContentQualitySummary"]["component"] == "RealDslContentQualitySummary" for artifact in dsl_artifacts)
    assert any("Real LLM Demo" in artifact["title"] for artifact in dsl_artifacts)

    lab_task = next(task for task in data["createdTasks"] if task["taskType"] == "LAB_GENERATION")
    _, detail_payload = run_cli(["review", "detail", "--task-id", lab_task["id"]], capsys)
    lab_review_detail = detail_payload["data"]["reviewDetail"]
    lab_provider_summary = lab_review_detail["reviewPage"]["providerSummary"]
    assert lab_review_detail["mode"] == "REAL_LLM_DEMO_WORKFLOW"
    assert lab_provider_summary["realLlmCalled"] is True
    assert lab_provider_summary["responseIds"] == ["resp_fake_cli_lab"]
    assert lab_provider_summary["apiSurfaces"] == ["chat.completions"]
    assert lab_provider_summary["usage"]["totalTokens"] == 103
    assert lab_provider_summary["auditSummary"]["realLlmCalled"] == 1
    assert lab_provider_summary["calls"][0]["responseId"] == "resp_fake_cli_lab"
    assert lab_provider_summary["calls"][0]["apiSurface"] == "chat.completions"
    assert lab_provider_summary["calls"][0]["normalization"]["applied"] is True
    assert lab_provider_summary["calls"][0]["qualitySummary"]["readyForReview"] is True
    assert lab_provider_summary["calls"][0]["qualitySummary"]["normalizationPatchCount"] == 1
    assert lab_provider_summary["qualitySummary"]["normalizationPatches"] == ["set.metadata.category"]
    assert lab_provider_summary["qualitySummaries"][0]["responseId"] == "resp_fake_cli_lab"
    assert lab_provider_summary["calls"][0]["totalTokens"] == 103
    assert lab_review_detail["providerCallAuditEvents"][0]["detail"]["responseId"] == "resp_fake_cli_lab"
    assert lab_review_detail["providerCallAuditEvents"][0]["detail"]["apiSurface"] == "chat.completions"
    assert lab_review_detail["providerCallAuditEvents"][0]["detail"]["usage"]["total_tokens"] == 103
    assert lab_review_detail["providerCallAuditEvents"][0]["detail"]["qualitySummary"]["readyForReview"] is True
    assert lab_review_detail["contentQualitySummary"]["available"] is True
    assert lab_review_detail["contentQualitySummary"]["items"]["lab"]["readyForManualReview"] is True
    assert lab_review_detail["contentQualitySummary"]["items"]["lab"]["decisionStatus"] == (
        "READY_FOR_IMPORT_PREVIEW_WITH_WARNINGS"
    )
    assert lab_review_detail["contentQualitySummary"]["items"]["lab"]["decision"]["warningTotal"] >= 1
    assert lab_review_detail["reviewPage"]["contentQualitySummary"] == lab_review_detail["contentQualitySummary"]
    lab_import_actions = lab_review_detail["platformImportPreviewActions"]
    assert lab_import_actions["contentQualityAvailable"] is True
    assert lab_import_actions["contentQualityReadyTotal"] == 1
    assert lab_import_actions["contentQualityBlockedTotal"] == 0
    assert lab_import_actions["contentQualityReadyForImportPreviewKinds"] == ["lab"]
    assert lab_import_actions["items"][0]["contentQualityReadyForImportPreview"] is True
    assert lab_import_actions["items"][0]["contentQualityRecommendedAction"] == (
        "approve_task_then_create_import_preview"
    )
    assert lab_review_detail["reviewPage"]["platformImportPreviewActions"] == lab_import_actions
    assert lab_review_detail["summary"]["contentQualityAvailable"] is True
    assert lab_review_detail["summary"]["providerCallAuditEventTotal"] == 1
    assert lab_review_detail["safety"]["realLlmCalled"] is True

    exam_task = next(task for task in data["createdTasks"] if task["taskType"] == "EXAM_GENERATION")
    _, exam_detail_payload = run_cli(["review", "detail", "--task-id", exam_task["id"]], capsys)
    exam_review_detail = exam_detail_payload["data"]["reviewDetail"]
    exam_candidate_preview = exam_review_detail["candidatePreview"]
    exam_provider_summary = exam_review_detail["reviewPage"]["providerSummary"]
    assert exam_candidate_preview["available"] is True
    assert exam_candidate_preview["kind"] == "ExamCandidatePreview"
    assert exam_candidate_preview["questionCount"] == 1
    assert exam_candidate_preview["answerVisibleToCandidate"] is False
    assert exam_candidate_preview["answerLeakDetected"] is False
    assert exam_candidate_preview["publishBlockedUntilApproved"] is True
    assert "questions" not in exam_candidate_preview
    assert exam_review_detail["reviewPage"]["candidatePreview"] == exam_candidate_preview
    assert exam_provider_summary["responseIds"] == ["resp_fake_cli_exam"]
    assert exam_provider_summary["usage"]["totalTokens"] == 104
    assert exam_provider_summary["calls"][0]["outputKind"] == "Exam"

    grading_task = next(task for task in data["createdTasks"] if task["taskType"] == "GRADING_GENERATION")
    _, grading_detail_payload = run_cli(["review", "detail", "--task-id", grading_task["id"]], capsys)
    grading_provider_summary = grading_detail_payload["data"]["reviewDetail"]["reviewPage"]["providerSummary"]
    grading_content_quality = grading_detail_payload["data"]["reviewDetail"]["contentQualitySummary"]["items"]["grading"]
    assert grading_provider_summary["qualitySummary"]["schemaRepairAttempted"] is True
    assert grading_provider_summary["qualitySummary"]["schemaRepairApplied"] is True
    assert grading_provider_summary["qualitySummary"]["schemaRepairErrorCount"] == 1
    assert grading_provider_summary["calls"][0]["qualitySummary"]["responseId"] == "resp_fake_cli_grading"
    assert grading_content_quality["decisionStatus"] == (
        "READY_FOR_IMPORT_PREVIEW_EVIDENCE_REQUIRED_BEFORE_FINAL_APPROVAL"
    )
    assert grading_content_quality["requiresEvidenceBeforeFinalApproval"] is True
    assert grading_content_quality["evidenceStatus"] == "GRADING_EVIDENCE_REQUIRED_BEFORE_FINAL_APPROVAL"

    _, batch_payload = run_cli(["review", "batch-summary"], capsys)
    batch_summary = batch_payload["data"]["reviewTaskSummary"]
    provider_signal = batch_summary["providerQualityTaskSignal"]
    assert provider_signal["source"] == "reviewDetail.reviewPage.providerSummary.qualitySummary"
    assert provider_signal["taskTotal"] == 4
    assert provider_signal["availableTotal"] == 4
    assert provider_signal["realLlmCalledTotal"] == 4
    assert provider_signal["readyForReviewTotal"] == 4
    assert provider_signal["normalizationPatchTotal"] == 2
    assert provider_signal["schemaRepairAppliedTotal"] == 1
    assert provider_signal["requestTotal"] == 4
    assert provider_signal["totalTokens"] == 417
    assert provider_signal["autoApproveAllowed"] is False
    assert provider_signal["batchStateChangeAllowed"] is False
    assert provider_signal["realPublishAllowed"] is False
    priority_queue = batch_summary["reviewPriorityQueue"]
    assert priority_queue["summary"]["providerQualityAvailableTotal"] == 4
    assert priority_queue["summary"]["providerQualityReadyForReviewTotal"] == 4
    lab_queue_item = next(item for item in priority_queue["items"] if item["taskType"] == "LAB_GENERATION")
    assert lab_queue_item["providerQualitySummary"]["realLlmCalled"] is True
    assert lab_queue_item["providerQualitySummary"]["responseIds"] == ["resp_fake_cli_lab"]
    assert lab_queue_item["providerQualitySummary"]["normalizationPatchCount"] == 1
    assert lab_queue_item["providerQualitySummary"]["autoPublishAllowed"] is False
    assert lab_queue_item["providerQualitySummary"]["realPublishAllowed"] is False

    _, listed = run_cli(["workflow", "list", "--workflow-id", "phase2_content_generation"], capsys)
    _, audit = run_cli(["provider", "audit", "--trace-id", payload["traceId"]], capsys)
    assert listed["data"]["total"] == 1
    assert audit["data"]["total"] == 4
    assert sum(1 for event in audit["data"]["items"] if event["realLlmCalled"]) == 4


def test_phase2_real_dsl_demo_close_loop_approves_import_previews_and_signoff(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "phase2-real-demo-report.json"
    lab_output = tmp_path / "demo-real-lab.json"
    exam_output = tmp_path / "demo-real-exam.json"
    grading_output = tmp_path / "demo-real-grading.json"
    ppt_output = tmp_path / "demo-real-ppt.json"

    def fake_run(request, *, root):
        return fake_real_demo_workflow_result(request, root=root)

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)
    run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
            "--provider-mode",
            "real-llm-demo",
            "--real-demo-lab-output",
            str(lab_output),
            "--real-demo-exam-output",
            str(exam_output),
            "--real-demo-grading-output",
            str(grading_output),
            "--real-demo-ppt-output",
            str(ppt_output),
            "--model",
            "test-model",
            "--explicit-real-call-opt-in",
            "--confirm-demo-real-dsl",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    close_loop_output = tmp_path / "real-demo-close-loop.json"
    exit_code, payload = run_cli(
        [
            "phase2",
            "real-dsl-demo",
            "close-loop",
            "--workflow-report",
            str(report_path),
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_2",
            "--lab-import-output",
            str(tmp_path / "lab-import-preview.json"),
            "--exam-import-output",
            str(tmp_path / "exam-import-preview.json"),
            "--grading-import-output",
            str(tmp_path / "grading-import-preview.json"),
            "--output",
            str(close_loop_output),
            "--confirm-lab-review-approved",
            "--confirm-exam-review-approved",
            "--confirm-grading-review-approved",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert close_loop_output.exists()
    close_loop = payload["data"]["closeLoop"]
    assert close_loop["component"] == "RealLlmDemoCloseLoop"
    assert close_loop["mode"] == "REAL_LLM_DEMO_CLOSE_LOOP"
    assert close_loop["summary"]["readyForDemo"] is True
    assert close_loop["summary"]["dslValidatedTotal"] == 4
    assert close_loop["summary"]["approvedImportableTaskTotal"] == 3
    assert close_loop["summary"]["importPreviewTotal"] == 3
    assert close_loop["summary"]["signoffReadyTotal"] == 3
    assert close_loop["summary"]["mockImportCreatedTotal"] == 0
    assert close_loop["summary"]["agentEntityReadyTotal"] == 0
    assert close_loop["summary"]["agentEntityMissingMockImportTotal"] == 3
    assert close_loop["summary"]["allPlatformEntitiesReadyForManualReview"] is False
    assert close_loop["agentEntityReadinessScope"]["agentEntities"] == [
        "exam_question",
        "grading_rule",
        "lab_template",
    ]
    assert close_loop["agentEntityReadinessScope"]["pptDeckIncluded"] is False
    assert close_loop["summary"]["pptWaitingReview"] is True
    assert close_loop["safety"]["newLlmRequestSent"] is False
    assert close_loop["safety"]["realAgentImport"] is False
    assert close_loop["safety"]["mockStoreWritten"] is False
    assert close_loop["safety"]["realPublishAllowed"] is False
    assert close_loop["mockImports"]["enabled"] is False
    assert close_loop["agentEntityReadinessReport"]["summary"]["previewCreatedTotal"] == 3
    assert close_loop["agentEntityReadinessReport"]["summary"]["mockImportCreatedTotal"] == 0
    assert close_loop["agentEntityReadinessReport"]["scope"] == {
        "agentEntities": ["lab_template", "exam_question", "grading_rule"],
        "filtered": True,
    }
    assert {item["agentEntity"] for item in close_loop["agentEntityReadinessReport"]["items"]} == {
        "lab_template",
        "exam_question",
        "grading_rule",
    }
    assert {item["task"]["status"] for item in close_loop["approvals"].values()} == {"APPROVED"}
    assert close_loop["reviewDetails"]["ppt"]["task"]["status"] == "WAITING_REVIEW"
    assert close_loop["importPreviews"]["lab"]["labTemplateImportPreview"]["component"] == "LabTemplateImportPreview"
    assert close_loop["importPreviews"]["exam"]["examQuestionImportPreview"]["component"] == "ExamQuestionImportPreview"
    assert close_loop["importPreviews"]["grading"]["gradingRuleImportPreview"]["component"] == "GradingRuleImportPreview"
    assert {item["readyForHumanSignoff"] for item in close_loop["platformImportPreviewSignoff"].values()} == {True}
    assert {item["missingPreviewTotal"] for item in close_loop["platformImportPreviewSignoff"].values()} == {0}
    assert payload["data"]["summary"]["readyForDemo"] is True


def test_phase2_real_dsl_demo_close_loop_creates_explicit_mock_imports_and_readiness(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "phase2-real-demo-report.json"
    lab_output = tmp_path / "demo-real-lab.json"
    exam_output = tmp_path / "demo-real-exam.json"
    grading_output = tmp_path / "demo-real-grading.json"
    ppt_output = tmp_path / "demo-real-ppt.json"

    def fake_run(request, *, root):
        return fake_real_demo_workflow_result(request, root=root)

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)
    run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
            "--provider-mode",
            "real-llm-demo",
            "--real-demo-lab-output",
            str(lab_output),
            "--real-demo-exam-output",
            str(exam_output),
            "--real-demo-grading-output",
            str(grading_output),
            "--real-demo-ppt-output",
            str(ppt_output),
            "--model",
            "test-model",
            "--explicit-real-call-opt-in",
            "--confirm-demo-real-dsl",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    close_loop_output = tmp_path / "real-demo-close-loop.json"
    lab_mock_output = tmp_path / "lab-mock-import.json"
    exam_mock_output = tmp_path / "exam-mock-import.json"
    grading_mock_output = tmp_path / "grading-mock-import.json"
    exit_code, payload = run_cli(
        [
            "phase2",
            "real-dsl-demo",
            "close-loop",
            "--workflow-report",
            str(report_path),
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_2",
            "--lab-import-output",
            str(tmp_path / "lab-import-preview.json"),
            "--exam-import-output",
            str(tmp_path / "exam-import-preview.json"),
            "--grading-import-output",
            str(tmp_path / "grading-import-preview.json"),
            "--create-mock-imports",
            "--lab-mock-import-output",
            str(lab_mock_output),
            "--exam-mock-import-output",
            str(exam_mock_output),
            "--grading-mock-import-output",
            str(grading_mock_output),
            "--output",
            str(close_loop_output),
            "--confirm-lab-review-approved",
            "--confirm-exam-review-approved",
            "--confirm-grading-review-approved",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert close_loop_output.exists()
    assert lab_mock_output.exists()
    assert exam_mock_output.exists()
    assert grading_mock_output.exists()
    close_loop = payload["data"]["closeLoop"]
    assert close_loop["mockImports"]["enabled"] is True
    assert close_loop["mockImports"]["mockImportCreatedTotal"] == 3
    assert set(close_loop["mockImports"]["entityIds"]) == {"lab", "exam", "grading"}
    assert close_loop["mockImports"]["databaseWritten"] is False
    assert close_loop["mockImports"]["realAgentImport"] is False
    assert close_loop["summary"]["mockImportCreatedTotal"] == 3
    assert close_loop["summary"]["agentEntityReadyTotal"] == 3
    assert close_loop["summary"]["agentEntityRequiredTotal"] == 3
    assert close_loop["summary"]["agentEntityMissingPreviewTotal"] == 0
    assert close_loop["summary"]["agentEntityMissingMockImportTotal"] == 0
    assert close_loop["summary"]["allPlatformEntitiesReadyForManualReview"] is True
    assert close_loop["agentEntityReadinessScope"]["pptDeckIncluded"] is False
    assert close_loop["agentEntityReadinessReport"]["scope"] == {
        "agentEntities": ["lab_template", "exam_question", "grading_rule"],
        "filtered": True,
    }
    assert close_loop["agentEntityReadinessReport"]["summary"]["allReadyForManualPlatformReview"] is True
    assert close_loop["agentEntityReadinessReport"]["summary"]["mockImportCreatedTotal"] == 3
    assert all(
        item["readyForManualAgentReview"] is True
        for item in close_loop["agentEntityReadinessReport"]["items"]
    )
    assert close_loop["safety"]["mockStoreWritten"] is True
    assert close_loop["safety"]["databaseWritten"] is False
    assert close_loop["safety"]["realAgentImport"] is False
    assert close_loop["safety"]["realPublish"] is False
    assert payload["data"]["summary"]["allPlatformEntitiesReadyForManualReview"] is True


@requires_presentations_runtime
def test_phase2_real_dsl_demo_one_click_runs_local_demo_and_optional_close_loop(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    original_subprocess_run = subprocess.run

    def fake_docker_only(args, **kwargs):
        command_line = " ".join(str(arg) for arg in args)
        if command_line.startswith("docker ") or "\\docker" in command_line:
            return fake_controlled_docker_run(args, **kwargs)
        return original_subprocess_run(args, **kwargs)

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_docker_only)
    report_path = tmp_path / "phase2-real-demo-report.json"
    lab_output = tmp_path / "demo-real-lab.json"
    exam_output = tmp_path / "demo-real-exam.json"
    grading_output = tmp_path / "demo-real-grading.json"
    ppt_output = tmp_path / "demo-real-ppt.json"

    def fake_run(request, *, root):
        return fake_real_demo_workflow_result(request, root=root)

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)
    run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
            "--provider-mode",
            "real-llm-demo",
            "--real-demo-lab-output",
            str(lab_output),
            "--real-demo-exam-output",
            str(exam_output),
            "--real-demo-grading-output",
            str(grading_output),
            "--real-demo-ppt-output",
            str(ppt_output),
            "--model",
            "test-model",
            "--explicit-real-call-opt-in",
            "--confirm-demo-real-dsl",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    close_loop_output = tmp_path / "real-demo-close-loop.json"
    one_click_output = tmp_path / "real-demo-one-click.json"
    controlled_report_output = tmp_path / "controlled-report.json"
    exit_code, payload = run_cli(
        [
            "phase2",
            "real-dsl-demo",
            "one-click",
            "--workflow-report",
            str(report_path),
            "--input",
            "examples/input/demo-source.md",
            "--lab",
            str(lab_output),
            "--exam",
            str(exam_output),
            "--grading",
            str(grading_output),
            "--ppt",
            str(ppt_output),
            "--submission",
            "examples/submissions/readonly-demo",
            "--verification-output",
            str(tmp_path / "real-demo-local-verification.json"),
            "--normalized-grading-output",
            str(tmp_path / "normalized-grading.json"),
            "--precheck-output",
            str(tmp_path / "precheck.json"),
            "--readonly-report-output",
            str(tmp_path / "readonly-report.json"),
            "--readonly-evidence-grading-output",
            str(tmp_path / "readonly-evidence-grading.json"),
            "--readonly-evidence-report-output",
            str(tmp_path / "readonly-evidence-report.json"),
            "--candidate-preview-output",
            str(tmp_path / "candidate-preview.json"),
            "--pptx-output",
            str(tmp_path / "real-demo-ppt-artifact.pptx"),
            "--pptx-manifest-output",
            str(tmp_path / "real-demo-ppt-artifact-manifest.json"),
            "--pptx-preview-output",
            str(tmp_path / "real-demo-ppt-artifact-slide-01.png"),
            "--pptx-preview-dir",
            str(tmp_path / "real-demo-ppt-artifact-slides"),
            "--pptx-contact-sheet-output",
            str(tmp_path / "real-demo-ppt-artifact-contact-sheet.png"),
            "--bundle-output",
            str(tmp_path / "real-demo-bundle.json"),
            "--acceptance-output",
            str(tmp_path / "real-demo-acceptance-summary.json"),
            "--checklist-output",
            str(tmp_path / "real-demo-checklist.json"),
            "--run-close-loop",
            "--lab-import-output",
            str(tmp_path / "lab-import-preview.json"),
            "--exam-import-output",
            str(tmp_path / "exam-import-preview.json"),
            "--grading-import-output",
            str(tmp_path / "grading-import-preview.json"),
            "--create-mock-imports",
            "--lab-mock-import-output",
            str(tmp_path / "lab-mock-import.json"),
            "--exam-mock-import-output",
            str(tmp_path / "exam-mock-import.json"),
            "--grading-mock-import-output",
            str(tmp_path / "grading-mock-import.json"),
            "--controlled-submission",
            "examples/submissions/controlled-command-demo",
            "--controlled-plan-output",
            str(tmp_path / "controlled-plan.json"),
            "--controlled-report-output",
            str(controlled_report_output),
            "--controlled-image",
            "local-python:demo",
            "--controlled-stdout-expected",
            "WAITING_REVIEW",
            "--close-loop-output",
            str(close_loop_output),
            "--output",
            str(one_click_output),
            "--confirm-lab-review-approved",
            "--confirm-exam-review-approved",
            "--confirm-grading-review-approved",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert one_click_output.exists()
    assert close_loop_output.exists()
    one_click = payload["data"]["oneClick"]
    assert one_click["component"] == "RealLlmDemoOneClick"
    assert one_click["mode"] == "REAL_LLM_DEMO_ONE_CLICK_LOCAL"
    assert one_click["summary"]["readyForHumanReview"] is True
    assert one_click["summary"]["acceptancePassed"] is True
    assert one_click["summary"]["checklistReadyForDemo"] is True
    assert one_click["summary"]["closeLoopExecuted"] is True
    assert one_click["summary"]["closeLoopReadyForDemo"] is True
    assert one_click["summary"]["reviewCenterRouteAvailable"] is True
    assert one_click["summary"]["agentEntitiesRouteAvailable"] is True
    assert one_click["summary"]["gradingReportRouteAvailable"] is True
    assert one_click["closeLoopSummary"]["mockImportCreatedTotal"] == 3
    assert one_click["closeLoopSummary"]["allPlatformEntitiesReadyForManualReview"] is True
    assert one_click["closeLoopSummary"]["controlledGradingEvidenceEnabled"] is True
    entry_routes = one_click["entryRoutes"]
    lab_task_id = one_click["entryRoutes"]["taskIds"]["lab"]
    grading_task_id = one_click["entryRoutes"]["taskIds"]["grading"]
    assert entry_routes["component"] == "RealLlmDemoEntryRoutes"
    assert entry_routes["mode"] == "LOCAL_REVIEW_NAVIGATION_ONLY"
    assert entry_routes["reviewCenter"] == f"review-center.html?taskId={lab_task_id}"
    assert entry_routes["reviewCenterAfterAgentEntityReturn"] == (
        f"review-center.html?taskId={lab_task_id}&agentEntityRefresh=1"
    )
    assert entry_routes["agentEntities"].startswith("agent-entities.html?")
    assert f"sourceTaskId={lab_task_id}" in entry_routes["agentEntities"]
    assert entry_routes["gradingReview"] == f"grading-review.html?taskId={grading_task_id}"
    assert entry_routes["gradingReport"].startswith("grading-report.html?")
    assert f"taskId={grading_task_id}" in entry_routes["gradingReport"]
    assert "file=" in entry_routes["gradingReport"]
    assert entry_routes["outputFiles"]["bundle"] == str(tmp_path / "real-demo-bundle.json")
    assert entry_routes["outputFiles"]["closeLoop"] == str(close_loop_output)
    assert entry_routes["outputFiles"]["controlledGradingReport"] == str(controlled_report_output)
    assert entry_routes["summary"]["manualReviewRequired"] is True
    assert entry_routes["safety"]["readOnlyNavigation"] is True
    assert entry_routes["safety"]["realAgentImport"] is False
    assert entry_routes["safety"]["realPublish"] is False
    assert one_click["safety"]["newLlmRequestSent"] is False
    assert one_click["safety"]["secretsRead"] is False
    assert one_click["safety"]["networkAccess"] is False
    assert one_click["safety"]["realAgentImport"] is False
    assert one_click["safety"]["realPublish"] is False
    assert payload["data"]["summary"]["newLlmRequestSent"] is False


def test_phase2_real_dsl_demo_close_loop_collects_controlled_grading_evidence(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_controlled_docker_run)
    report_path = tmp_path / "phase2-real-demo-report.json"
    lab_output = tmp_path / "demo-real-lab.json"
    exam_output = tmp_path / "demo-real-exam.json"
    grading_output = tmp_path / "demo-real-grading.json"
    ppt_output = tmp_path / "demo-real-ppt.json"

    def fake_run(request, *, root):
        return fake_real_demo_workflow_result(request, root=root)

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)
    run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
            "--provider-mode",
            "real-llm-demo",
            "--real-demo-lab-output",
            str(lab_output),
            "--real-demo-exam-output",
            str(exam_output),
            "--real-demo-grading-output",
            str(grading_output),
            "--real-demo-ppt-output",
            str(ppt_output),
            "--model",
            "test-model",
            "--explicit-real-call-opt-in",
            "--confirm-demo-real-dsl",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    close_loop_output = tmp_path / "real-demo-close-loop.json"
    controlled_plan_output = tmp_path / "controlled-plan.json"
    controlled_report_output = tmp_path / "controlled-report.json"
    exit_code, payload = run_cli(
        [
            "phase2",
            "real-dsl-demo",
            "close-loop",
            "--workflow-report",
            str(report_path),
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_2",
            "--lab-import-output",
            str(tmp_path / "lab-import-preview.json"),
            "--exam-import-output",
            str(tmp_path / "exam-import-preview.json"),
            "--grading-import-output",
            str(tmp_path / "grading-import-preview.json"),
            "--controlled-submission",
            "examples/submissions/controlled-command-demo",
            "--controlled-plan-output",
            str(controlled_plan_output),
            "--controlled-report-output",
            str(controlled_report_output),
            "--controlled-image",
            "local-python:demo",
            "--controlled-stdout-command",
            "python main.py",
            "--controlled-stdout-expected",
            "WAITING_REVIEW",
            "--output",
            str(close_loop_output),
            "--confirm-lab-review-approved",
            "--confirm-exam-review-approved",
            "--confirm-grading-review-approved",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert close_loop_output.exists()
    assert controlled_plan_output.exists()
    assert controlled_report_output.exists()
    close_loop = payload["data"]["closeLoop"]
    controlled = close_loop["controlledGradingEvidence"]
    assert controlled["enabled"] is True
    assert controlled["planCreated"] is True
    assert controlled["reportCreated"] is True
    assert controlled["planPath"] == str(controlled_plan_output)
    assert controlled["reportPath"] == str(controlled_report_output)
    assert controlled["image"] == "local-python:demo"
    assert controlled["plan"]["summary"]["selectedCheckTotal"] == 1
    assert controlled["plan"]["summary"]["executableScore"] == 100
    assert controlled["plan"]["summary"]["deferredCheckTotal"] == 0
    assert controlled["report"]["executionSummary"]["executed"] == 1
    assert controlled["report"]["executionSummary"]["passed"] == 1
    assert controlled["report"]["score"]["earnedScore"] == 100
    assert controlled["sandboxExecuted"] is True
    assert controlled["contestantCodeExecuted"] is True
    assert controlled["commandExecuted"] is True
    assert controlled["networkEnabled"] is False
    assert close_loop["summary"]["controlledGradingEvidenceEnabled"] is True
    assert close_loop["summary"]["controlledGradingPlanCreated"] is True
    assert close_loop["summary"]["controlledGradingReportCreated"] is True
    assert close_loop["summary"]["controlledGradingEvidenceExecutedTotal"] == 1
    assert close_loop["summary"]["controlledGradingEvidenceEarnedScore"] == 100
    assert close_loop["safety"]["sandboxExecuted"] is True
    assert close_loop["safety"]["contestantCodeExecuted"] is True
    assert close_loop["safety"]["commandExecuted"] is True
    assert close_loop["safety"]["networkEnabledForControlledGrading"] is False
    assert close_loop["safety"]["realPublishAllowed"] is False
    saved_report = json.loads(controlled_report_output.read_text(encoding="utf-8"))
    assert saved_report["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    grading_task_id = close_loop["createdTasks"]["grading"]["id"]
    _, detail_payload = run_cli(["review", "detail", "--task-id", grading_task_id], capsys)
    detail = detail_payload["data"]["reviewDetail"]
    evidence = detail["controlledGradingEvidence"]
    assert evidence["visible"] is True
    assert evidence["planTotal"] == 1
    assert evidence["reportTotal"] == 1
    assert evidence["summary"]["executedTotal"] == 1
    assert evidence["summary"]["passedTotal"] == 1
    assert evidence["summary"]["earnedScore"] == 100
    assert evidence["summary"]["totalScore"] == 100
    assert evidence["summary"]["manualReviewRequired"] is True
    assert evidence["summary"]["autoApproveAllowed"] is False
    assert evidence["summary"]["realPublishAllowed"] is False
    assert evidence["safety"]["sandboxExecuted"] is True
    assert evidence["safety"]["contestantCodeExecuted"] is True
    assert evidence["safety"]["commandExecuted"] is True
    assert evidence["safety"]["networkEnabled"] is False
    assert evidence["reports"][0]["artifactPath"] == str(controlled_report_output)
    assert evidence["reports"][0]["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert evidence["reports"][0]["reportDetail"]["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert detail["reviewPage"]["controlledGradingEvidence"] == evidence
    assert detail["summary"]["controlledGradingEvidenceVisible"] is True
    assert detail["summary"]["controlledGradingEvidenceReportTotal"] == 1
    assert detail["summary"]["controlledGradingEvidenceExecutedTotal"] == 1
    assert detail["summary"]["controlledGradingEvidenceEarnedScore"] == 100
    assert detail["safety"]["sandboxExecuted"] is True
    assert detail["safety"]["contestantCodeExecuted"] is True
    assert detail["safety"]["networkEnabledForControlledGrading"] is False
    _, batch_payload = run_cli(["review", "batch-summary", "--status", "APPROVED"], capsys)
    batch_summary = batch_payload["data"]["reviewTaskSummary"]
    controlled_signal = batch_summary["controlledDockerEvidenceReviewSignal"]
    assert controlled_signal["source"] == "reviewDetail.controlledGradingEvidence"
    assert controlled_signal["dynamicSource"] == "reviewDetail.controlledGradingEvidence"
    assert controlled_signal["fallbackSource"] == "realDemoPrototype.controlledDockerEvidenceDemo"
    assert controlled_signal["sourceMode"] == "DYNAMIC_CONTROLLED_DOCKER_EVIDENCE"
    assert controlled_signal["mode"] == "DYNAMIC_CONTROLLED_DOCKER_EVIDENCE"
    assert controlled_signal["taskTotal"] == 1
    assert controlled_signal["planTotal"] == 1
    assert controlled_signal["reportTotal"] == 1
    assert controlled_signal["coveredCheckIds"] == ["check_waiting_review"]
    assert controlled_signal["coveredCheckTypes"] == ["stdout_contains"]
    assert controlled_signal["executed"] == 1
    assert controlled_signal["passed"] == 1
    assert controlled_signal["earnedScore"] == 100
    assert controlled_signal["totalControlledScore"] == 100
    assert controlled_signal["safety"]["sandboxExecuted"] is True
    assert controlled_signal["safety"]["contestantCodeExecuted"] is True
    assert controlled_signal["safety"]["networkAllowed"] is False
    assert controlled_signal["items"][0]["taskId"] == grading_task_id
    assert controlled_signal["items"][0]["reportPath"] == str(controlled_report_output)
    priority_item = next(
        item
        for item in batch_summary["reviewPriorityQueue"]["items"]
        if item["taskId"] == grading_task_id
    )
    assert priority_item["reasonCode"] == "CONTROLLED_DOCKER_EVIDENCE_REVIEW_REQUIRED"
    assert priority_item["recommendedAction"] == "review_controlled_docker_evidence_before_approval"
    assert priority_item["controlledGradingEvidenceSummary"]["available"] is True
    assert priority_item["controlledGradingEvidenceSummary"]["coveredCheckIds"] == ["check_waiting_review"]
    assert priority_item["controlledGradingEvidenceSummary"]["coveredCheckTypes"] == ["stdout_contains"]
    assert priority_item["controlledGradingEvidenceSummary"]["executed"] == 1
    assert priority_item["controlledGradingEvidenceSummary"]["earnedScore"] == 100


def test_phase2_real_dsl_demo_close_loop_requires_explicit_review_confirmations(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "phase2-real-demo-report.json"

    def fake_run(request, *, root):
        return fake_real_demo_workflow_result(request, root=root)

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)
    run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--output",
            str(report_path),
            "--provider-mode",
            "real-llm-demo",
            "--model",
            "test-model",
            "--explicit-real-call-opt-in",
            "--confirm-demo-real-dsl",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ],
        capsys,
    )

    exit_code, payload = run_cli(
        [
            "phase2",
            "real-dsl-demo",
            "close-loop",
            "--workflow-report",
            str(report_path),
            "--input",
            "examples/input/demo-source.md",
            "--output",
            str(tmp_path / "blocked-close-loop.json"),
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert {error["field"] for error in payload["errors"]} == {
        "confirmLabReviewApproved",
        "confirmExamReviewApproved",
        "confirmGradingReviewApproved",
    }


def test_phase2_workflow_report_reads_and_summarizes_saved_report(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LAB_CLI_STORE", str(tmp_path / "store.json"))
    report_path = tmp_path / "phase2-report.json"
    run_cli(
        [
            "phase2",
            "workflow",
            "run",
            "--input",
            "examples/input/demo-source.md",
            "--reviewer",
            "teacher_1",
            "--output",
            str(report_path),
        ],
        capsys,
    )

    exit_code, payload = run_cli(["phase2", "workflow", "report", "--file", str(report_path)], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["summary"]["workflowId"] == "phase2_content_generation"
    assert payload["data"]["summary"]["phase"] == "Phase 2"
    assert payload["data"]["summary"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["summary"]["reviewRequired"] is True
    assert payload["data"]["summary"]["publishBlockedUntilApproved"] is True
    assert payload["data"]["summary"]["generatedDsl"]["lab"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["summary"]["safety"]["realLlmCalled"] is False


def test_phase2_workflow_run_missing_input_returns_json(tmp_path, capsys):
    report_path = tmp_path / "phase2-report.json"

    exit_code, payload = run_cli(
        ["phase2", "workflow", "run", "--input", "missing.md", "--output", str(report_path)],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"
    assert not report_path.exists()


def test_phase2_workflow_report_rejects_phase1_report(tmp_path, capsys):
    report_path = tmp_path / "bad-report.json"
    report_path.write_text(json.dumps({"phase": "Phase 1", "mode": "MOCK_ONLY"}), encoding="utf-8")

    exit_code, payload = run_cli(["phase2", "workflow", "report", "--file", str(report_path)], capsys)

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "phase"
