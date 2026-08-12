import json
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealLlmApprovalGateRequest,
    build_real_llm_approval_gate_error_context,
    evaluate_real_llm_approval_gate,
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


def test_real_llm_approval_gate_contract_is_mock_only_and_local():
    contract = load_json("providers/real-llm-approval-gate.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_llm_approval_gate"
    assert contract["activeProvider"] == "mock"
    assert contract["requiredContext"]["realCallAuthorized"] is False
    assert contract["requiredContext"]["secretPresenceChecked"] is False
    assert contract["requiredContext"]["secretValueRead"] is False
    assert contract["requiredContext"]["realLlmCalled"] is False
    assert contract["requiredContext"]["secretsRead"] is False
    assert contract["requiredContext"]["networkAccess"] is False
    assert "authorize_real_call" in contract["blockedOperations"]
    assert "bypass_dry_run_plan" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_llm_approval_gate" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_llm_approval_gate_defaults_to_not_ready_but_safe():
    request = RealLlmApprovalGateRequest(provider_id="openai")
    result = evaluate_real_llm_approval_gate(request, root=ROOT)
    checklist = {item["id"]: item for item in result["approvalChecklist"]}

    assert result["gateId"] == "real_llm_approval_gate"
    assert result["approvalGateEvaluated"] is True
    assert result["dryRunPlanPassed"] is True
    assert result["approvalChecklistPassed"] is False
    assert result["readyForImplementationTask"] is False
    assert checklist["approval_ref_provided"]["passed"] is False
    assert checklist["reviewer_provided"]["passed"] is False
    assert checklist["dry_run_plan_passed"]["passed"] is True
    assert result["realCallAuthorized"] is False
    assert result["secretPresenceChecked"] is False
    assert result["secretValueRead"] is False
    assert result["sdkImported"] is False
    assert result["clientCreated"] is False
    assert result["taskCreated"] is False
    assert result["realLlmCalled"] is False
    assert result["secretsRead"] is False
    assert result["networkAccess"] is False


def test_real_llm_approval_gate_can_mark_implementation_task_ready_without_authorizing_call(monkeypatch):
    fake_key = "sk-" + "approval-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    request = RealLlmApprovalGateRequest(
        provider_id="openai",
        approval_ref="APPROVAL-001",
        reviewer="teacher_1",
        dry_run_plan_confirmed=True,
        runtime_guard_confirmed=True,
        schema_review_confirmed=True,
        human_review_policy_confirmed=True,
        audit_redaction_confirmed=True,
        payload={"apiKey": fake_key},
    )

    result = evaluate_real_llm_approval_gate(request, root=ROOT)
    serialized = json.dumps(result, ensure_ascii=False)

    assert result["approvalChecklistPassed"] is True
    assert result["readyForImplementationTask"] is True
    assert result["realCallAuthorized"] is False
    assert result["readyForRealProvider"] is False
    assert result["dryRunPlanSummary"]["planPassed"] is True
    assert result["dryRunPlanSummary"]["realLlmCalled"] is False
    assert result["dryRunPlanSummary"]["secretValueRead"] is False
    assert result["dryRunPlanSummary"]["secretPresenceChecked"] is False
    assert result["dryRunPlanSummary"]["taskCreated"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized


def test_real_llm_approval_gate_invalid_scope_keeps_safe_context():
    request = RealLlmApprovalGateRequest(provider_id="openai", output_kind="Exam")

    try:
        evaluate_real_llm_approval_gate(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_llm_approval_gate_error_context(exc, request=request, root=ROOT)
        assert context["approvalGateEvaluated"] is False
        assert context["approvalChecklistPassed"] is False
        assert context["readyForImplementationTask"] is False
        assert context["realCallAuthorized"] is False
        assert context["secretValueRead"] is False
        assert context["realLlmCalled"] is False
        assert context["secretsRead"] is False
        assert context["networkAccess"] is False
    else:
        raise AssertionError("expected ProviderError")


def test_real_llm_approval_gate_cli_default_and_confirmed_paths(capsys):
    exit_code, payload = run_cli(["provider", "real-approval-gate", "check", "--provider", "openai"], capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["gateId"] == "real_llm_approval_gate"
    assert payload["data"]["approvalChecklistPassed"] is False
    assert payload["data"]["readyForImplementationTask"] is False
    assert payload["data"]["realCallAuthorized"] is False

    exit_code, payload = run_cli(
        [
            "provider",
            "real-approval-gate",
            "check",
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
    assert payload["data"]["approvalChecklistPassed"] is True
    assert payload["data"]["readyForImplementationTask"] is True
    assert payload["data"]["realCallAuthorized"] is False
    assert payload["data"]["realLlmCalled"] is False


def test_real_llm_approval_gate_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-approval-gate", "check", "--provider", "openai", "--payload", "not-json"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        ["provider", "real-approval-gate", "check", "--provider", "openai", "--output-kind", "Exam"],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["realLlmApprovalGateContext"]["realCallAuthorized"] is False
    assert payload["realLlmApprovalGateContext"]["realLlmCalled"] is False
    assert payload["realLlmApprovalGateContext"]["secretsRead"] is False
    assert payload["realLlmApprovalGateContext"]["networkAccess"] is False
