import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmDryRunPlanRequest,
    build_real_llm_dry_run_plan,
    build_real_llm_dry_run_plan_error_context,
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


def test_real_llm_dry_run_plan_contract_is_mock_only_and_local():
    contract = load_json("providers/real-llm-dry-run-plan.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["planId"] == "real_llm_dry_run_plan"
    assert contract["activeProvider"] == "mock"
    assert contract["requiredContext"]["dryRunOnly"] is True
    assert contract["requiredContext"]["providerEnabled"] is False
    assert contract["requiredContext"]["adapterEnabled"] is False
    assert contract["requiredContext"]["readyForRealProvider"] is False
    assert contract["requiredContext"]["sdkImported"] is False
    assert contract["requiredContext"]["clientCreated"] is False
    assert contract["requiredContext"]["secretPresenceChecked"] is False
    assert contract["requiredContext"]["secretValueRead"] is False
    assert contract["requiredContext"]["realLlmCalled"] is False
    assert contract["requiredContext"]["secretsRead"] is False
    assert contract["requiredContext"]["networkAccess"] is False
    assert "provider_runtime_guard" in contract["plannedSteps"]
    assert "disabled_real_llm_poc_adapter" in contract["plannedSteps"]
    assert "create_ai_task_from_real_output" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_llm_dry_run_plan" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_llm_dry_run_plan_passes_locally_without_real_execution(monkeypatch):
    fake_key = "sk-" + "dry-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    request = RealLlmDryRunPlanRequest(
        provider_id="openai",
        payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
    )

    plan = build_real_llm_dry_run_plan(request, root=ROOT)
    serialized = json.dumps(plan, ensure_ascii=False)

    assert plan["planId"] == "real_llm_dry_run_plan"
    assert plan["planPassed"] is True
    assert plan["runtimeGuardPassed"] is True
    assert plan["dryRunOnly"] is True
    assert plan["defaultProvider"] == "mock"
    assert plan["providerId"] == "openai"
    assert plan["providerEnabled"] is False
    assert plan["providerContractEnabled"] is False
    assert plan["adapterEnabled"] is False
    assert plan["readyForRealProvider"] is False
    assert plan["secretPresenceChecked"] is False
    assert plan["secretValueRead"] is False
    assert plan["secretValueReturned"] is False
    assert plan["generatedStatus"] == "WAITING_REVIEW"
    assert plan["runtimeFlags"]["ENABLE_REAL_LLM"] == "false"
    assert plan["sdkImported"] is False
    assert plan["clientCreated"] is False
    assert plan["generatedContentCreated"] is False
    assert plan["taskCreated"] is False
    assert plan["realLlmCalled"] is False
    assert plan["secretsRead"] is False
    assert plan["networkAccess"] is False
    assert plan["adapterDescriptor"]["adapterId"] == "real_llm_poc_adapter"
    assert {step["id"] for step in plan["plannedSteps"]} >= {
        "provider_runtime_guard",
        "schema_validate_lab_dsl",
        "create_waiting_review_task",
        "human_review",
    }
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized


def test_real_llm_dry_run_plan_rejects_invalid_scope_and_keeps_safe_context():
    request = RealLlmDryRunPlanRequest(provider_id="openai", output_kind="Exam")

    try:
        build_real_llm_dry_run_plan(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_llm_dry_run_plan_error_context(exc, request=request, root=ROOT)
        assert context["planId"] == "real_llm_dry_run_plan"
        assert context["planPassed"] is False
        assert context["runtimeGuardPassed"] is False
        assert context["readyForRealProvider"] is False
        assert context["secretValueRead"] is False
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
    else:
        raise AssertionError("expected ProviderError")


def test_real_llm_dry_run_plan_cli_returns_json_plan(capsys):
    exit_code, payload = run_cli(["provider", "real-dry-run", "plan", "--provider", "openai"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["data"]["planId"] == "real_llm_dry_run_plan"
    assert payload["data"]["planPassed"] is True
    assert payload["data"]["runtimeGuardPassed"] is True
    assert payload["data"]["dryRunOnly"] is True
    assert payload["data"]["providerEnabled"] is False
    assert payload["data"]["adapterEnabled"] is False
    assert payload["data"]["realLlmCalled"] is False
    assert payload["data"]["secretsRead"] is False
    assert payload["data"]["networkAccess"] is False


def test_real_llm_dry_run_plan_cli_redacts_payload(capsys):
    fake_key = "sk-" + "dry-cli-hidden"
    exit_code, payload = run_cli(
        [
            "provider",
            "real-dry-run",
            "plan",
            "--provider",
            "openai",
            "--payload",
            json.dumps({"apiKey": fake_key, "text": f"token={fake_key}"}),
        ],
        capsys,
    )
    serialized = json.dumps(payload, ensure_ascii=False)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert payload["data"]["redactedPayloadPreview"]["apiKey"] == "[REDACTED]"


def test_real_llm_dry_run_plan_cli_rejects_bad_payload_and_invalid_timeout(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-dry-run", "plan", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        ["provider", "real-dry-run", "plan", "--provider", "openai", "--timeout-seconds", "0"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["realLlmDryRunPlanContext"]["planPassed"] is False
    assert payload["realLlmDryRunPlanContext"]["realLlmCalled"] is False
    assert payload["realLlmDryRunPlanContext"]["secretsRead"] is False
    assert payload["realLlmDryRunPlanContext"]["networkAccess"] is False
