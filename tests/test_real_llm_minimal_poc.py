import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cli import lab_cli
from cli.store import JsonTaskStore
from providers import (
    ProviderError,
    RealLlmMinimalPocRequest,
    describe_real_llm_minimal_poc,
    run_real_llm_minimal_poc,
)


ROOT = Path(__file__).resolve().parents[1]


def valid_lab_dsl():
    return {
        "version": "1.0",
        "kind": "Lab",
        "metadata": {
            "id": "lab-real-llm-minimal-poc",
            "title": "真实 LLM 最小 PoC 实验",
            "category": "ai-platform",
            "difficulty": "beginner",
            "durationMinutes": 30,
        },
        "status": "WAITING_REVIEW",
        "spec": {
            "objectives": ["理解真实 LLM 单请求接入边界"],
            "targetUsers": ["平台开发者"],
            "environment": {"type": "notebook", "image": "python:3.11"},
            "steps": [
                {
                    "id": "step-1",
                    "title": "阅读输入材料",
                    "instruction": "阅读给定材料并确认 Lab DSL 字段。",
                }
            ],
        },
    }


def test_describe_real_llm_minimal_poc_declares_single_request_scope():
    result = describe_real_llm_minimal_poc(root=ROOT)

    assert result["mode"] == "REAL_LLM_MINIMAL_SINGLE_REQUEST"
    assert result["scope"]["outputKind"] == "Lab DSL"
    assert result["scope"]["requestCount"] == 1
    assert result["scope"]["batchRequest"] is False
    assert result["scope"]["streaming"] is False
    assert result["reviewPolicy"]["generatedStatus"] == "WAITING_REVIEW"
    assert result["reviewPolicy"]["autoPublishAllowed"] is False


def test_run_real_llm_minimal_poc_requires_explicit_confirmations(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ProviderError) as exc_info:
        run_real_llm_minimal_poc(RealLlmMinimalPocRequest(provider_id="openai"), root=ROOT)

    exc = exc_info.value
    assert exc.code == "REAL_LLM_MINIMAL_CALL_CONFIRMATION_REQUIRED"
    assert {error["field"] for error in exc.errors} == {
        "explicit_real_call_opt_in",
        "confirm_single_request",
        "confirm_lab_only",
        "confirm_waiting_review",
        "confirm_no_auto_publish",
    }


def test_run_real_llm_minimal_poc_requires_secret_before_request(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ProviderError) as exc_info:
        run_real_llm_minimal_poc(
            RealLlmMinimalPocRequest(
                provider_id="openai",
                model="test-model",
                explicit_real_call_opt_in=True,
                confirm_single_request=True,
                confirm_lab_only=True,
                confirm_waiting_review=True,
                confirm_no_auto_publish=True,
            ),
            root=ROOT,
            client_factory=lambda **_: pytest.fail("client must not be created without secret"),
        )

    assert exc_info.value.code == "REAL_LLM_MINIMAL_CALL_SECRET_REQUIRED"


def test_run_real_llm_minimal_poc_uses_single_responses_request_and_validates_schema(monkeypatch):
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="resp_fake_1",
                output_text=json.dumps(valid_lab_dsl(), ensure_ascii=False),
                usage=SimpleNamespace(input_tokens=11, output_tokens=22, total_tokens=33),
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            created_kwargs.append(kwargs)
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-value")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://env-base-url.test/v1")
    created_kwargs = []

    result = run_real_llm_minimal_poc(
        RealLlmMinimalPocRequest(
            provider_id="openai",
            model="test-model",
            base_url="https://argument-base-url.test/v1",
            generation_context={
                "targetUsers": ["高职学生"],
                "durationMinutes": 60,
                "difficulty": "beginner",
                "techTags": ["Python"],
                "teachingStyle": "guided_practice",
            },
            explicit_real_call_opt_in=True,
            confirm_single_request=True,
            confirm_lab_only=True,
            confirm_waiting_review=True,
            confirm_no_auto_publish=True,
        ),
        root=ROOT,
        client_factory=FakeClient,
    )

    assert created_kwargs == [{"api_key": "test-secret-value", "base_url": "https://argument-base-url.test/v1"}]
    assert len(calls) == 1
    call = calls[0]
    assert call["model"] == "test-model"
    assert call["stream"] is False
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["name"] == "lab_dsl"
    assert "Lab generation context JSON" in call["input"]
    assert '"durationMinutes": 60' in call["input"]
    assert "targetUsers" in call["instructions"]
    assert "metadata.durationMinutes" in call["instructions"]
    assert "spec.targetUsers" in call["instructions"]
    assert result["realLlmCalled"] is True
    assert result["networkAccess"] is True
    assert result["secretValueReturned"] is False
    assert result["baseUrlConfigured"] is True
    assert result["baseUrlSource"] == "argument"
    assert "https://argument-base-url.test/v1" not in json.dumps(result, ensure_ascii=False)
    assert result["schemaValidated"] is True
    assert result["generatedStatus"] == "WAITING_REVIEW"
    assert result["generationContext"]["targetUsers"] == ["高职学生"]
    assert result["promptVersion"] == "real-llm-minimal-poc-v2"
    assert result["promptPath"] == "prompts/workflows/lab_generation.md"
    assert result["taskCreated"] is False
    assert result["usage"]["total_tokens"] == 33
    assert "test-secret-value" not in json.dumps(result, ensure_ascii=False)


def test_run_real_llm_minimal_poc_rejects_invalid_schema(monkeypatch):
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(output_text=json.dumps({"kind": "Lab"}))

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-value")

    with pytest.raises(ProviderError) as exc_info:
        run_real_llm_minimal_poc(
            RealLlmMinimalPocRequest(
                provider_id="openai",
                model="test-model",
                explicit_real_call_opt_in=True,
                confirm_single_request=True,
                confirm_lab_only=True,
                confirm_waiting_review=True,
                confirm_no_auto_publish=True,
            ),
            root=ROOT,
            client_factory=FakeClient,
        )

    assert exc_info.value.code == "REAL_LLM_MINIMAL_CALL_SCHEMA_VALIDATION_FAILED"


def test_cli_real_llm_minimal_poc_missing_secret_returns_json(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = lab_cli.main(
        [
            "provider",
            "real-llm-minimal-poc",
            "run",
            "--provider",
            "openai",
            "--model",
            "test-model",
            "--explicit-real-call-opt-in",
            "--confirm-single-request",
            "--confirm-lab-only",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_MINIMAL_CALL_SECRET_REQUIRED"
    context = payload["realLlmMinimalPocContext"]
    assert context["secretPresent"] is False
    assert context["requestSent"] is False
    assert context["realLlmCalled"] is False


def test_cli_real_llm_minimal_poc_success_writes_waiting_review_task_and_audit(monkeypatch, tmp_path, capsys):
    store_path = tmp_path / "store.json"
    output_path = tmp_path / "real-llm-lab.json"
    monkeypatch.setenv("LAB_CLI_STORE", str(store_path))

    def fake_run(request, root):
        assert request.base_url == "https://cli-base-url.test/v1"
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
            "baseUrlConfigured": bool(request.base_url),
            "baseUrlSource": "argument" if request.base_url else None,
            "inputRef": request.input_ref,
            "promptId": "lab_generation_v0",
            "promptVersion": "real-llm-minimal-poc-v2",
            "promptPath": "prompts/workflows/lab_generation.md",
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
            "dslId": "lab-real-llm-minimal-poc",
            "responseId": "resp_fake_1",
            "usage": {"total_tokens": 33},
            "labDsl": valid_lab_dsl(),
            "traceId": request.trace_id,
        }

    monkeypatch.setattr(lab_cli, "run_real_llm_minimal_poc", fake_run)

    exit_code = lab_cli.main(
        [
            "provider",
            "real-llm-minimal-poc",
            "run",
            "--provider",
            "openai",
            "--input",
            "examples/input/demo-source.md",
            "--output",
            str(output_path),
            "--model",
            "test-model",
            "--base-url",
            "https://cli-base-url.test/v1",
            "--created-by",
            "teacher_1",
            "--explicit-real-call-opt-in",
            "--confirm-single-request",
            "--confirm-lab-only",
            "--confirm-waiting-review",
            "--confirm-no-auto-publish",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["success"] is True
    result = payload["data"]
    assert result["taskCreated"] is True
    assert result["task"]["status"] == "WAITING_REVIEW"
    assert result["task"]["modelName"] == "test-model"
    assert result["task"]["promptVersion"] == "real-llm-minimal-poc-v2"
    assert result["artifact"]["realLlmCalled"] is True
    assert result["artifact"]["realPublish"] is False
    assert result["providerCallAuditEvent"]["realLlmCalled"] is True
    assert result["providerCallAuditEvent"]["networkAccess"] is True
    assert result["providerCallAuditEvent"]["secretsRead"] is True
    assert result["providerCallAuditEvent"]["mockOutputCreated"] is False
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["status"] == "WAITING_REVIEW"

    store = JsonTaskStore(store_path)
    tasks = store.list(status="WAITING_REVIEW", task_type="LAB_GENERATION")
    assert len(tasks) == 1
    audits = store.list_provider_call_audit_events(provider_id="openai", operation="generateJson")
    assert len(audits) == 1
    assert audits[0].realLlmCalled is True
