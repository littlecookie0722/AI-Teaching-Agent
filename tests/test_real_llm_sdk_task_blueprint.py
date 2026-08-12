import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmSdkTaskBlueprintRequest,
    build_real_llm_sdk_task_blueprint,
    build_real_llm_sdk_task_blueprint_error_context,
)


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def run_cli(args, capsys):
    exit_code = main(args)
    output = capsys.readouterr().out
    payload = json.loads(output)
    return exit_code, payload


def assert_json_envelope(payload):
    assert set(payload) >= {"success", "code", "message", "traceId"}
    assert payload["traceId"].startswith("trace_")


def test_real_llm_sdk_task_blueprint_contract_is_mock_only_and_local():
    contract = load_json("providers/real-llm-sdk-task-blueprint.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["blueprintId"] == "real_llm_sdk_task_blueprint"
    assert contract["targetTaskType"] == "REAL_LLM_SDK_MINIMAL_POC"
    assert contract["activeProvider"] == "mock"
    assert contract["requiredContext"]["blueprintGenerated"] is True
    assert contract["requiredContext"]["implementationAllowed"] is False
    assert contract["requiredContext"]["realCallAuthorized"] is False
    assert contract["requiredContext"]["sdkDependencyInstalled"] is False
    assert contract["requiredContext"]["providerContractChangeApplied"] is False
    assert contract["requiredContext"]["runtimeContractChangeApplied"] is False
    assert contract["requiredContext"]["secretPresenceChecked"] is False
    assert contract["requiredContext"]["secretValueRead"] is False
    assert contract["requiredContext"]["realLlmCalled"] is False
    assert contract["requiredContext"]["secretsRead"] is False
    assert contract["requiredContext"]["networkAccess"] is False
    assert contract["targetScope"]["generatedStatus"] == "WAITING_REVIEW"
    assert contract["targetScope"]["publishAllowed"] is False
    assert "install_sdk_dependency" in contract["blockedOperations"]
    assert "enable_provider_contract" in contract["blockedOperations"]
    assert "network_call" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_llm_sdk_task_blueprint" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_llm_sdk_task_blueprint_defaults_to_not_ready_but_safe():
    request = RealLlmSdkTaskBlueprintRequest(provider_id="openai")
    result = build_real_llm_sdk_task_blueprint(request, root=ROOT)

    assert result["blueprintId"] == "real_llm_sdk_task_blueprint"
    assert result["blueprintGenerated"] is True
    assert result["blueprintReady"] is False
    assert result["readyForImplementationTask"] is False
    assert result["approvalGateSummary"]["readyForImplementationTask"] is False
    assert result["approvalGateSummary"]["realCallAuthorized"] is False
    assert result["targetScope"]["operation"] == "generateJson"
    assert result["targetScope"]["promptId"] == "lab_generation_v0"
    assert result["targetScope"]["outputKind"] == "Lab"
    assert result["targetScope"]["generatedStatus"] == "WAITING_REVIEW"
    assert result["implementationAllowed"] is False
    assert result["realCallAuthorized"] is False
    assert result["sdkDependencyInstalled"] is False
    assert result["providerContractChangeApplied"] is False
    assert result["runtimeContractChangeApplied"] is False
    assert result["secretPresenceChecked"] is False
    assert result["secretValueRead"] is False
    assert result["sdkImported"] is False
    assert result["clientCreated"] is False
    assert result["taskCreated"] is False
    assert result["realLlmCalled"] is False
    assert result["secretsRead"] is False
    assert result["networkAccess"] is False


def test_real_llm_sdk_task_blueprint_ready_requires_approval_gate_but_never_authorizes_call(monkeypatch):
    fake_key = "sk-" + "blueprint-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    request = RealLlmSdkTaskBlueprintRequest(
        provider_id="openai",
        approval_ref="APPROVAL-001",
        reviewer="teacher_1",
        dry_run_plan_confirmed=True,
        runtime_guard_confirmed=True,
        schema_review_confirmed=True,
        human_review_policy_confirmed=True,
        audit_redaction_confirmed=True,
        task_ref="REALSDK-P1",
        payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
    )

    result = build_real_llm_sdk_task_blueprint(request, root=ROOT)
    serialized = json.dumps(result, ensure_ascii=False)
    change_paths = {item["path"] for item in result["proposedChangeSet"]}
    test_ids = {item["id"] for item in result["testMatrix"]}

    assert result["blueprintReady"] is True
    assert result["readyForImplementationTask"] is True
    assert result["approvalGateSummary"]["readyForImplementationTask"] is True
    assert result["implementationAllowed"] is False
    assert result["realCallAuthorized"] is False
    assert result["sdkDependencyInstalled"] is False
    assert result["dependencyPlan"]["dependencyChangeAllowedNow"] is False
    assert result["environmentPlan"]["secretNameOnly"] is True
    assert result["environmentPlan"]["secretValueRead"] is False
    assert result["networkPlan"]["networkAccessEnabledNow"] is False
    assert result["humanReviewPlan"]["generatedStatus"] == "WAITING_REVIEW"
    assert "providers/real_llm_poc_adapter.py" in change_paths
    assert "providers/provider.contract.json" in change_paths
    assert "config/runtime.contract.json" in change_paths
    assert "tests/test_real_provider_sdk_poc.py" in change_paths
    assert "test_real_provider_sdk_poc" in test_ids
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized


def test_real_llm_sdk_task_blueprint_invalid_scope_keeps_safe_context():
    request = RealLlmSdkTaskBlueprintRequest(provider_id="openai", output_kind="Exam")

    try:
        build_real_llm_sdk_task_blueprint(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_llm_sdk_task_blueprint_error_context(exc, request=request, root=ROOT)
        assert context["blueprintGenerated"] is False
        assert context["blueprintReady"] is False
        assert context["readyForImplementationTask"] is False
        assert context["implementationAllowed"] is False
        assert context["realCallAuthorized"] is False
        assert context["secretValueRead"] is False
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
    else:
        raise AssertionError("expected ProviderError")


def test_real_llm_sdk_task_blueprint_cli_default_and_confirmed_paths(capsys):
    exit_code, payload = run_cli(["provider", "real-sdk-blueprint", "plan", "--provider", "openai"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["blueprintId"] == "real_llm_sdk_task_blueprint"
    assert payload["data"]["blueprintReady"] is False
    assert payload["data"]["readyForImplementationTask"] is False
    assert payload["data"]["realCallAuthorized"] is False

    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-blueprint",
            "plan",
            "--provider",
            "openai",
            "--approval-ref",
            "APPROVAL-001",
            "--reviewer",
            "teacher_1",
            "--confirm-dry-run-plan",
            "--confirm-runtime-guard",
            "--confirm-schema-review",
            "--confirm-human-review-policy",
            "--confirm-audit-redaction",
        ],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["data"]["blueprintReady"] is True
    assert payload["data"]["readyForImplementationTask"] is True
    assert payload["data"]["implementationAllowed"] is False
    assert payload["data"]["realCallAuthorized"] is False
    assert payload["data"]["realLlmCalled"] is False


def test_real_llm_sdk_task_blueprint_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-blueprint", "plan", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        ["provider", "real-sdk-blueprint", "plan", "--provider", "openai", "--output-kind", "Exam"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["realLlmSdkTaskBlueprintContext"]["realCallAuthorized"] is False
    assert payload["realLlmSdkTaskBlueprintContext"]["realLlmCalled"] is False
    assert payload["realLlmSdkTaskBlueprintContext"]["secretsRead"] is False
    assert payload["realLlmSdkTaskBlueprintContext"]["networkAccess"] is False
