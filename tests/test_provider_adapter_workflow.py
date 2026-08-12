import json
from pathlib import Path

import ai_workflows.provider_adapter_workflow as workflow_module
from ai_workflows.provider_adapter_workflow import (
    PHASE2_REAL_LLM_MODE,
    PHASE2_WORKFLOW_ID,
    PHASE2_REAL_LLM_DEMO_MODE,
    PHASE2_REAL_LLM_MINIMAL_MODE,
    PROVIDER_MODE_REAL_LLM,
    PROVIDER_MODE_REAL_LLM_DEMO,
    PROVIDER_MODE_REAL_LLM_MINIMAL,
    REAL_LLM_DSL_GENERATION_MODE,
    generate_mock_dsl_via_adapter,
    generate_workflow_dsl_bundle,
    run_phase2_content_generation,
)
from providers import ProviderError


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def valid_real_lab_dsl():
    return {
        "version": "1.0",
        "kind": "Lab",
        "metadata": {
            "id": "lab-real-workflow",
            "title": "真实 LLM Workflow 实验",
            "category": "ai-platform",
            "difficulty": "beginner",
            "durationMinutes": 45,
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "objectives": ["理解真实 LLM Lab DSL 回接流程"],
            "targetUsers": ["平台开发者"],
            "environment": {"type": "notebook", "image": "python:3.11"},
            "steps": [
                {
                    "id": "step-1",
                    "title": "查看生成结果",
                    "instruction": "确认 Lab DSL 状态为 WAITING_REVIEW。",
                }
            ],
        },
    }


def valid_real_exam_dsl():
    return {
        "version": "1.0",
        "kind": "Exam",
        "metadata": {
            "id": "exam-real-workflow",
            "title": "真实 LLM Workflow 试题",
            "sourceLabId": "lab-real-workflow",
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


def invalid_score_real_exam_dsl():
    exam = valid_real_exam_dsl()
    exam["spec"]["totalScore"] = 100
    exam["spec"]["questions"] = [
        {
            "id": "q1",
            "title": "题目一",
            "stem": "完成题目一。",
            "score": 40,
            "gradingRef": "check_q1",
        },
        {
            "id": "q2",
            "title": "题目二",
            "stem": "完成题目二。",
            "score": 40,
            "gradingRef": "check_q2",
        },
    ]
    return exam


def valid_real_grading_dsl():
    return {
        "version": "1.0",
        "kind": "Grading",
        "metadata": {
            "id": "grading-real-workflow",
            "title": "真实 LLM Workflow 评分",
            "sourceExamId": "exam-real-workflow",
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
                    "inputSummary": "Check that demo output contains WAITING_REVIEW.",
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
            "id": "ppt-real-workflow",
            "title": "真实 LLM Workflow 课件",
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


def fake_real_llm_result(request):
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
        "responseId": "resp_fake_workflow",
        "usage": {"total_tokens": 42},
        "labDsl": lab_dsl,
        "traceId": request.trace_id,
    }


def fake_real_demo_generation(request, *, root):
    dsl_by_kind = {
        "lab": valid_real_lab_dsl(),
        "exam": valid_real_exam_dsl(),
        "grading": valid_real_grading_dsl(),
        "ppt": valid_real_ppt_dsl(),
    }
    dsl = dsl_by_kind[request.kind]
    schema_repair_applied = request.repair_on_schema_failure and request.kind == "exam"
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
        "requestCount": 2 if schema_repair_applied else 1,
        "singleRequestForKind": not schema_repair_applied,
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
        "responseId": f"resp_fake_{request.kind}",
        "usage": {"total_tokens": 100 + len(request.kind)},
        "dsl": dsl,
        "schemaRepair": {
            "attempted": True,
            "applied": True,
            "errorCount": 1,
            "errors": [{"field": "$.spec.questions[0].score", "reason": "expected integer"}],
        } if schema_repair_applied else {"attempted": False, "applied": False, "errorCount": 0},
        "schemaRepairAttempted": schema_repair_applied,
        "schemaRepairApplied": schema_repair_applied,
        "traceId": request.trace_id,
    }


def test_provider_audit_workflow_contract_is_mock_only_and_paths_exist():
    contract = load_json("ai-workflows/provider-audit-workflow.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["storeKey"] == "providerCallAuditEvents"
    assert contract["workflowId"] == "phase1_main_demo"
    assert {step["stepName"] for step in contract["auditedWorkflowSteps"]} == {
        "generate_lab_dsl",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "generate_ppt_dsl",
    }
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()
    assert contract["expectedEventDetail"]["source"] == "workflow_adapter"
    assert contract["expectedEventDetail"]["workflowStepRequired"] is True
    assert contract["expectedEventDetail"]["taskIdRequired"] is True
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["secretsRead"] is False
    assert contract["safety"]["networkAccess"] is False
    assert contract["safety"]["autoPublishAllowed"] is False


def test_generate_mock_dsl_via_adapter_returns_review_gated_lab():
    result = generate_mock_dsl_via_adapter(
        "lab",
        input_ref="examples/input/demo-source.md",
        trace_id="trace_test",
        root=ROOT,
    )

    assert result["promptId"] == "lab_generation_v0"
    assert result["inputRef"] == "examples/input/demo-source.md"
    assert result["dslPath"] == "templates/lab/examples/basic-lab.yaml"
    assert result["dsl"]["kind"] == "Lab"
    assert len(result["dsl"]["spec"]["objectives"]) >= 2
    assert len(result["dsl"]["spec"]["steps"]) >= 3
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert result["reviewRequired"] is True
    assert result["publishBlockedUntilApproved"] is True
    assert result["provider"]["adapterId"] == "mock_provider_adapter"
    assert result["provider"]["interfaceName"] == "LLMProvider"
    assert result["provider"]["operation"] == "generateJson"
    assert result["provider"]["realLlmCalled"] is False
    assert result["provider"]["secretsRead"] is False
    assert result["provider"]["networkAccess"] is False


def test_generate_workflow_dsl_bundle_uses_adapter_for_all_generated_dsl():
    bundle = generate_workflow_dsl_bundle(
        input_ref="examples/input/demo-source.md",
        trace_id="trace_bundle",
        root=ROOT,
    )

    assert set(bundle) == {"lab", "exam", "grading", "ppt"}
    assert bundle["lab"]["outputKind"] == "Lab"
    assert bundle["lab"]["inputRef"] == "examples/input/demo-source.md"
    assert bundle["exam"]["outputKind"] == "Exam"
    assert bundle["exam"]["inputRef"] == "lab_demo"
    assert bundle["grading"]["outputKind"] == "Grading"
    assert bundle["grading"]["inputRef"] == "exam_demo"
    assert bundle["ppt"]["outputKind"] == "PPT"
    assert bundle["exam"]["provider"]["adapterId"] == "mock_provider_adapter"
    assert bundle["grading"]["provider"]["providerId"] == "mock"
    assert bundle["ppt"]["provider"]["realLlmCalled"] is False


def test_run_phase2_content_generation_builds_review_gated_bundle():
    report = run_phase2_content_generation(
        input_ref="examples/input/demo-source.md",
        reviewer="teacher_1",
        trace_id="trace_phase2",
        root=ROOT,
        material_analysis={
            "mode": "MOCK_ONLY",
            "title": "Demo Source",
            "fileType": "markdown",
            "riskCount": 0,
            "unknownShellExecuted": False,
            "requiresHumanReview": True,
        },
    )

    assert report["workflowId"] == PHASE2_WORKFLOW_ID
    assert report["phase"] == "Phase 2"
    assert report["mode"] == "MOCK_ONLY"
    assert report["providerAdapter"] == "mock_provider_adapter"
    assert report["labGenerationContext"] == {
        "targetUsers": ["高职学生"],
        "durationMinutes": 60,
        "difficulty": "beginner",
        "techTags": [],
        "teachingStyle": "guided_practice",
        "constraintsApplied": True,
    }
    assert report["qualitySignals"]["overall"]["reviewRequired"] is True
    assert report["qualitySignals"]["overall"]["schemaValidated"] is True
    assert report["qualitySignals"]["lab"]["objectivesCount"] >= 1
    assert report["qualitySignals"]["lab"]["matching"]["status"] == "MATCHED"
    assert report["qualitySignals"]["lab"]["matching"]["targetUsers"]["matched"] is True
    assert report["qualitySignals"]["lab"]["matching"]["durationMinutes"]["matched"] is True
    assert report["qualitySignals"]["lab"]["matching"]["difficulty"]["matched"] is True
    assert report["qualitySignals"]["lab"]["matching"]["stepGranularity"]["matched"] is True
    assert report["qualitySignals"]["lab"]["matching"]["teachingStyle"]["matched"] is True
    assert report["qualitySignals"]["lab"]["teachingStyleSignal"]["status"] == "MATCHED"
    assert report["qualitySignals"]["materialCoverage"]["available"] is True
    assert report["qualitySignals"]["materialCoverage"]["sourceReferencedInDsl"] is True
    assert report["qualitySignals"]["materialCoverage"]["status"] == "LINKED"
    assert report["qualitySignals"]["materialCoverage"]["riskReview"]["status"] == "CLEAR"
    assert [step["name"] for step in report["steps"]] == [
        "validate_input",
        "analyze_material",
        "generate_lab_dsl",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "generate_ppt_dsl",
        "assemble_review_bundle",
    ]
    assert set(report["generatedDsl"]) == {"lab", "exam", "grading", "ppt"}
    assert {item["status"] for item in report["generatedDsl"].values()} == {"WAITING_REVIEW"}
    assert report["generatedDsl"]["exam"]["answerVisibleToCandidate"] is False
    assert report["generatedDsl"]["ppt"]["artifactGenerated"] is False
    assert report["reviewSummary"]["publishBlockedUntilApproved"] is True
    assert report["acceptanceSignals"]["providerAdapterUsed"] is True
    assert report["safety"]["realLlmCalled"] is False
    assert report["safety"]["realAgentStarted"] is False
    assert report["safety"]["realCloudResourceCreated"] is False
    assert report["safety"]["sandboxExecuted"] is False
    assert report["safety"]["realPublish"] is False


def test_run_phase2_content_generation_accepts_lab_business_parameters():
    report = run_phase2_content_generation(
        input_ref="examples/input/demo-source.md",
        reviewer="teacher_1",
        trace_id="trace_phase2_context",
        root=ROOT,
        lab_generation_context={
            "targetUsers": "高职学生,教师",
            "durationMinutes": 90,
            "difficulty": "intermediate",
            "techTags": "Python,Notebook",
            "teachingStyle": "project_based",
        },
    )

    assert report["labGenerationContext"]["targetUsers"] == ["高职学生", "教师"]
    assert report["labGenerationContext"]["durationMinutes"] == 90
    assert report["labGenerationContext"]["difficulty"] == "intermediate"
    assert report["labGenerationContext"]["techTags"] == ["Python", "Notebook"]
    assert report["labGenerationContext"]["teachingStyle"] == "project_based"
    lab_step = next(step for step in report["steps"] if step["name"] == "generate_lab_dsl")
    assert lab_step["labGenerationContext"] == report["labGenerationContext"]
    assert lab_step["qualitySignals"]["requestedDurationMinutes"] == 90
    assert lab_step["qualitySignals"]["matching"]["status"] == "NEEDS_REVIEW"
    assert lab_step["qualitySignals"]["matching"]["targetUsers"]["matched"] is False
    assert lab_step["qualitySignals"]["matching"]["durationMinutes"]["matched"] is False
    assert lab_step["qualitySignals"]["matching"]["difficulty"]["matched"] is False
    assert lab_step["qualitySignals"]["matching"]["techTags"]["matched"] is False
    assert lab_step["qualitySignals"]["matching"]["teachingStyle"]["matched"] is False
    assert lab_step["qualitySignals"]["stepGranularity"]["matched"] is True
    assert "确认课时是否符合本次生成参数" in report["qualitySignals"]["reviewHighlights"]
    assert "确认难度是否符合本次生成参数" in report["qualitySignals"]["reviewHighlights"]
    assert "确认技术标签是否覆盖本次生成参数" in report["qualitySignals"]["reviewHighlights"]
    assert "确认教学风格是否符合本次生成参数" in report["qualitySignals"]["reviewHighlights"]
    assert report["acceptanceSignals"]["labGenerationContextCaptured"] is True
    assert report["acceptanceSignals"]["qualitySignalsGenerated"] is True


def test_run_phase2_content_generation_real_minimal_lab_reuses_mock_for_other_dsl(tmp_path, monkeypatch):
    calls = []
    real_lab_output = tmp_path / "phase2-real-lab.json"

    def fake_run(request, *, root):
        calls.append((request, root))
        return fake_real_llm_result(request)

    monkeypatch.setattr(workflow_module, "run_real_llm_minimal_poc", fake_run)

    report = run_phase2_content_generation(
        input_ref="examples/input/demo-source.md",
        reviewer="teacher_1",
        trace_id="trace_real_workflow",
        root=ROOT,
        provider_mode=PROVIDER_MODE_REAL_LLM_MINIMAL,
        real_lab_output_ref=str(real_lab_output),
        lab_generation_context={"targetUsers": "平台开发者", "durationMinutes": 45, "techTags": "LLM"},
        real_llm_model="test-model",
        explicit_real_call_opt_in=True,
        confirm_single_request=True,
        confirm_lab_only=True,
        confirm_waiting_review=True,
        confirm_no_auto_publish=True,
    )

    assert len(calls) == 1
    assert calls[0][0].model == "test-model"
    assert calls[0][0].explicit_real_call_opt_in is True
    assert calls[0][0].generation_context["targetUsers"] == ["平台开发者"]
    assert calls[0][0].generation_context["durationMinutes"] == 45
    assert calls[0][0].generation_context["techTags"] == ["LLM"]
    assert real_lab_output.exists()
    assert json.loads(real_lab_output.read_text(encoding="utf-8"))["metadata"]["id"] == "lab-real-workflow"
    assert report["mode"] == PHASE2_REAL_LLM_MINIMAL_MODE
    assert report["providerMode"] == PROVIDER_MODE_REAL_LLM_MINIMAL
    assert report["providerAdapter"] == "mixed_real_llm_minimal_and_mock_provider_adapter"
    assert report["generatedDsl"]["lab"]["provider"]["realLlmCalled"] is True
    assert report["generatedDsl"]["lab"]["provider"]["networkAccess"] is True
    assert report["generatedDsl"]["exam"]["provider"]["realLlmCalled"] is False
    assert report["generatedDsl"]["grading"]["provider"]["realLlmCalled"] is False
    assert report["generatedDsl"]["ppt"]["provider"]["realLlmCalled"] is False
    assert report["providerGenerations"]["exam"]["inputRef"] == "lab-real-workflow"
    assert report["reviewSummary"]["publishBlockedUntilApproved"] is True
    assert report["acceptanceSignals"]["mockOnly"] is False
    assert report["acceptanceSignals"]["realLlmMinimalLabConnected"] is True
    assert report["safety"]["realLlmCalled"] is True
    assert report["safety"]["secretsRead"] is True
    assert report["safety"]["networkAccess"] is True
    assert report["safety"]["realPublish"] is False
    assert report["safety"]["realCloudResourceCreated"] is False
    assert "真实 LLM 仅用于 Lab DSL，Exam/Grading/PPT 仍为 Mock" in report["reviewSummary"]["reviewHighlights"]


def test_generate_workflow_dsl_bundle_real_demo_generates_all_dsl(tmp_path, monkeypatch):
    calls = []
    output_refs = {
        "lab": str(tmp_path / "demo-lab.json"),
        "exam": str(tmp_path / "demo-exam.json"),
        "grading": str(tmp_path / "demo-grading.json"),
        "ppt": str(tmp_path / "demo-ppt.json"),
    }

    def fake_run(request, *, root):
        calls.append((request, root))
        return fake_real_demo_generation(request, root=root)

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)

    bundle = generate_workflow_dsl_bundle(
        input_ref="examples/input/demo-source.md",
        trace_id="trace_real_demo_bundle",
        root=ROOT,
        provider_mode=PROVIDER_MODE_REAL_LLM_DEMO,
        lab_generation_context={"targetUsers": ["平台开发者"], "durationMinutes": 45, "techTags": ["LLM"]},
        real_demo_output_refs=output_refs,
        real_llm_model="test-model",
        explicit_real_call_opt_in=True,
        confirm_waiting_review=True,
        confirm_no_auto_publish=True,
    )

    assert [call[0].kind for call in calls] == ["lab", "exam", "grading", "ppt"]
    assert all(call[0].model == "test-model" for call in calls)
    assert "labDsl" in calls[1][0].input_payload
    assert "examDsl" in calls[2][0].input_payload
    assert "gradingDsl" in calls[3][0].input_payload
    assert set(bundle) == {"lab", "exam", "grading", "ppt"}
    assert {generation["provider"]["realLlmCalled"] for generation in bundle.values()} == {True}
    assert bundle["grading"]["sandboxRequiredBeforeRealExecution"] is True
    assert bundle["ppt"]["artifactGenerated"] is False
    for kind, output_ref in output_refs.items():
        output_path = Path(output_ref)
        assert output_path.exists()
        assert json.loads(output_path.read_text(encoding="utf-8"))["kind"] == bundle[kind]["outputKind"]


def test_generate_workflow_dsl_bundle_real_llm_generates_all_dsl(tmp_path, monkeypatch):
    calls = []
    output_refs = {
        "lab": str(tmp_path / "real-lab.json"),
        "exam": str(tmp_path / "real-exam.json"),
        "grading": str(tmp_path / "real-grading.json"),
        "ppt": str(tmp_path / "real-ppt.json"),
    }

    def fake_run(request, *, root):
        calls.append((request, root))
        assert request.base_url == "https://workflow-base-url.test/v1"
        return fake_real_demo_generation(request, root=root)

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)

    bundle = generate_workflow_dsl_bundle(
        input_ref="examples/input/demo-source.md",
        trace_id="trace_real_llm_bundle",
        root=ROOT,
        provider_mode=PROVIDER_MODE_REAL_LLM,
        lab_generation_context={"targetUsers": ["平台开发者"], "durationMinutes": 45, "techTags": ["LLM"]},
        real_output_refs=output_refs,
        real_llm_model="test-model",
        real_llm_base_url="https://workflow-base-url.test/v1",
        explicit_real_call_opt_in=True,
        confirm_waiting_review=True,
        confirm_no_auto_publish=True,
    )

    assert [call[0].kind for call in calls] == ["lab", "exam", "grading", "ppt"]
    assert set(bundle) == {"lab", "exam", "grading", "ppt"}
    assert {generation["provider"]["realLlmCalled"] for generation in bundle.values()} == {True}
    assert {generation["provider"]["mode"] for generation in bundle.values()} == {REAL_LLM_DSL_GENERATION_MODE}
    for kind, output_ref in output_refs.items():
        output_path = Path(output_ref)
        assert output_path.exists()
        assert json.loads(output_path.read_text(encoding="utf-8"))["kind"] == bundle[kind]["outputKind"]


def test_run_phase2_content_generation_real_demo_records_four_real_dsl(tmp_path, monkeypatch):
    calls = []
    output_refs = {
        "lab": str(tmp_path / "demo-lab.json"),
        "exam": str(tmp_path / "demo-exam.json"),
        "grading": str(tmp_path / "demo-grading.json"),
        "ppt": str(tmp_path / "demo-ppt.json"),
    }

    def fake_run(request, *, root):
        calls.append((request, root))
        return fake_real_demo_generation(request, root=root)

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)

    report = run_phase2_content_generation(
        input_ref="examples/input/demo-source.md",
        reviewer="teacher_1",
        trace_id="trace_real_demo_workflow",
        root=ROOT,
        provider_mode=PROVIDER_MODE_REAL_LLM_DEMO,
        real_demo_output_refs=output_refs,
        lab_generation_context={"targetUsers": "平台开发者", "durationMinutes": 45, "techTags": "LLM"},
        real_llm_model="test-model",
        explicit_real_call_opt_in=True,
        confirm_waiting_review=True,
        confirm_no_auto_publish=True,
    )

    assert len(calls) == 4
    assert report["mode"] == PHASE2_REAL_LLM_DEMO_MODE
    assert report["providerMode"] == PROVIDER_MODE_REAL_LLM_DEMO
    assert report["providerAdapter"] == "openai_responses_sdk_demo_adapter"
    assert report["realLlmDemoDoc"] == "docs/18_REAL_LLM_DEMO_WORKFLOW.md"
    assert set(report["generatedDsl"]) == {"lab", "exam", "grading", "ppt"}
    assert {item["status"] for item in report["generatedDsl"].values()} == {"WAITING_REVIEW"}
    assert {item["provider"]["realLlmCalled"] for item in report["generatedDsl"].values()} == {True}
    assert report["safety"]["realLlmCalled"] is True
    assert report["safety"]["secretsRead"] is True
    assert report["safety"]["networkAccess"] is True
    assert report["safety"]["realLlmGeneratedKinds"] == ["lab", "exam", "grading", "ppt"]
    assert report["safety"]["realLlmRequestCount"] == 4
    assert report["safety"]["realPublish"] is False
    assert report["safety"]["sandboxExecuted"] is False
    assert report["reviewSummary"]["generatedStatus"] == "WAITING_REVIEW"
    assert "真实 LLM Demo 已生成 Lab/Exam/Grading/PPT 四类 DSL，全部仍需人工审核" in report["reviewSummary"]["reviewHighlights"]
    assert "真实 LLM 仅用于 Lab DSL，Exam/Grading/PPT 仍为 Mock" not in report["reviewSummary"]["reviewHighlights"]
    assert report["acceptanceSignals"]["mockOnly"] is False
    assert report["acceptanceSignals"]["realLlmDemoConnected"] is True
    assert report["acceptanceSignals"]["realLlmDemoGeneratedAllDsl"] is True
    assert report["acceptanceSignals"]["realLlmDemoRequestCount"] == 4
    assert report["acceptanceSignals"]["realLlmMinimalLabConnected"] is False


def test_run_phase2_content_generation_real_llm_records_four_real_dsl(tmp_path, monkeypatch):
    calls = []
    output_refs = {
        "lab": str(tmp_path / "real-lab.json"),
        "exam": str(tmp_path / "real-exam.json"),
        "grading": str(tmp_path / "real-grading.json"),
        "ppt": str(tmp_path / "real-ppt.json"),
    }

    def fake_run(request, *, root):
        calls.append((request, root))
        assert request.base_url == "https://workflow-base-url.test/v1"
        return fake_real_demo_generation(request, root=root)

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)

    report = run_phase2_content_generation(
        input_ref="examples/input/demo-source.md",
        reviewer="teacher_1",
        trace_id="trace_real_llm_workflow",
        root=ROOT,
        provider_mode=PROVIDER_MODE_REAL_LLM,
        real_output_refs=output_refs,
        lab_generation_context={"targetUsers": "平台开发者", "durationMinutes": 45, "techTags": "LLM"},
        real_llm_model="test-model",
        real_llm_base_url="https://workflow-base-url.test/v1",
        explicit_real_call_opt_in=True,
        confirm_waiting_review=True,
        confirm_no_auto_publish=True,
    )

    assert len(calls) == 4
    assert report["mode"] == PHASE2_REAL_LLM_MODE
    assert report["providerMode"] == PROVIDER_MODE_REAL_LLM
    assert report["providerAdapter"] == "openai_responses_sdk_adapter"
    assert report["realLlmWorkflowDoc"] == "docs/AI_PLATFORM_CODEX_FULL_GUIDE.md"
    assert report["realLlmDemoDoc"] is None
    assert {item["provider"]["realLlmCalled"] for item in report["generatedDsl"].values()} == {True}
    assert report["safety"]["realLlmGeneratedKinds"] == ["lab", "exam", "grading", "ppt"]
    assert report["safety"]["realLlmRequestCount"] == 4
    assert report["acceptanceSignals"]["mockOnly"] is False
    assert report["acceptanceSignals"]["realLlmConnected"] is True
    assert report["acceptanceSignals"]["realLlmGeneratedAllDsl"] is True
    assert report["acceptanceSignals"]["realLlmRequestCount"] == 4
    assert report["acceptanceSignals"]["realLlmDemoConnected"] is False
    assert "真实 LLM 已生成 Lab/Exam/Grading/PPT 四类 DSL，全部仍需人工审核" in report["reviewSummary"]["reviewHighlights"]
    assert "真实 LLM 仅用于 Lab DSL，Exam/Grading/PPT 仍为 Mock" not in report["reviewSummary"]["reviewHighlights"]


def test_run_phase2_content_generation_real_llm_can_enable_schema_repair(tmp_path, monkeypatch):
    calls = []
    output_refs = {
        "lab": str(tmp_path / "real-lab.json"),
        "exam": str(tmp_path / "real-exam.json"),
        "grading": str(tmp_path / "real-grading.json"),
        "ppt": str(tmp_path / "real-ppt.json"),
    }

    def fake_run(request, *, root):
        calls.append((request, root))
        return fake_real_demo_generation(request, root=root)

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)

    report = run_phase2_content_generation(
        input_ref="examples/input/demo-source.md",
        reviewer="teacher_1",
        trace_id="trace_real_llm_workflow_repair",
        root=ROOT,
        provider_mode=PROVIDER_MODE_REAL_LLM,
        real_output_refs=output_refs,
        real_llm_model="test-model",
        explicit_real_call_opt_in=True,
        confirm_waiting_review=True,
        confirm_no_auto_publish=True,
        repair_on_schema_failure=True,
    )

    assert len(calls) == 4
    assert all(call[0].repair_on_schema_failure is True for call in calls)
    assert report["generatedDsl"]["exam"]["provider"]["requestCount"] == 2
    assert report["generatedDsl"]["exam"]["provider"]["singleRequestOnly"] is False
    assert report["generatedDsl"]["exam"]["provider"]["schemaRepairAttempted"] is True
    assert report["generatedDsl"]["exam"]["provider"]["schemaRepairApplied"] is True
    assert report["generatedDsl"]["exam"]["schemaRepair"]["applied"] is True
    assert report["providerGenerations"]["exam"]["schemaRepair"]["applied"] is True
    assert report["safety"]["realLlmRequestCount"] == 5
    assert report["acceptanceSignals"]["realLlmRequestCount"] == 5


def test_run_phase2_content_generation_content_quality_decision_blocks_import_preview_on_high_issue(
    tmp_path, monkeypatch
):
    output_refs = {
        "lab": str(tmp_path / "real-lab.json"),
        "exam": str(tmp_path / "real-exam.json"),
        "grading": str(tmp_path / "real-grading.json"),
        "ppt": str(tmp_path / "real-ppt.json"),
    }

    def fake_run(request, *, root):
        result = fake_real_demo_generation(request, root=root)
        if request.kind == "exam":
            result["dsl"] = invalid_score_real_exam_dsl()
            result["dslId"] = result["dsl"]["metadata"]["id"]
        return result

    monkeypatch.setattr(workflow_module, "run_real_llm_demo_dsl_generation", fake_run)

    report = run_phase2_content_generation(
        input_ref="examples/input/demo-source.md",
        reviewer="teacher_1",
        trace_id="trace_real_llm_quality_blocker",
        root=ROOT,
        provider_mode=PROVIDER_MODE_REAL_LLM,
        real_output_refs=output_refs,
        real_llm_model="test-model",
        explicit_real_call_opt_in=True,
        confirm_waiting_review=True,
        confirm_no_auto_publish=True,
    )

    summary = report["contentQualitySummary"]
    exam_quality = report["generatedDsl"]["exam"]["contentQualitySummary"]
    assert summary["decisionStatus"] == "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW"
    assert summary["requiresRevisionBeforeImportPreview"] is True
    assert summary["requiresEvidenceBeforeFinalApproval"] is False
    assert summary["recommendedAction"] == "revise_blocked_dsl_before_import_preview"
    assert summary["decision"]["evidenceRequiredKinds"] == []
    assert summary["decision"]["blockerTotal"] == 2
    assert summary["decision"]["blockers"][0]["id"] == "exam_score_mismatch"
    assert exam_quality["decisionStatus"] == "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW"
    assert exam_quality["recommendedAction"] == "align_question_scores"
    assert exam_quality["requiresRevisionBeforeImportPreview"] is True
    assert exam_quality["readyForImportPreview"] is False
    assert report["reviewSummary"]["contentQualitySummary"]["blockingIssueTotal"] == 2
    assert report["reviewSummary"]["publishBlockedUntilApproved"] is True
    assert report["safety"]["realPublish"] is False


def test_generate_mock_dsl_via_adapter_rejects_unknown_kind():
    try:
        generate_mock_dsl_via_adapter("unknown", root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "kind"
    else:
        raise AssertionError("expected ProviderError")
