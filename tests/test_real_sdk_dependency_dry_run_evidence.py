import json
from dataclasses import asdict
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyDryRunEvidenceRequest,
    build_real_sdk_dependency_dry_run_evidence,
    build_real_sdk_dependency_dry_run_evidence_error_context,
    describe_real_sdk_dependency_dry_run_evidence,
)
from tests.test_real_sdk_dependency_executor_disabled import (
    assert_json_envelope,
    confirmed_cli_args as confirmed_executor_cli_args,
    confirmed_request as confirmed_executor_request,
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


def assert_safe_evidence_context(context):
    for key in [
        "executionApprovalGranted",
        "executionTaskCreated",
        "taskPersisted",
        "taskQueued",
        "executionDispatched",
        "executorStarted",
        "executorRunCreated",
        "dryRunExecuted",
        "installDryRunExecuted",
        "evidenceFileWritten",
        "commandReviewRecordPersisted",
        "commandMaterialized",
        "installCommandMaterialized",
        "dependencyFileMutationAuthorized",
        "dependencyFileChangeAuthorized",
        "dependencyManifestWriteAuthorized",
        "dependencyLockfileWriteAuthorized",
        "dependencyManifestMutated",
        "dependencyLockfileMutated",
        "dependencyFileChanged",
        "patchGenerated",
        "patchMaterialized",
        "patchFileWritten",
        "patchApplied",
        "commandExecutionAuthorized",
        "commandExecuted",
        "dependencyInstallExecuted",
        "sdkDependencyInstalled",
        "sdkImported",
        "clientCreated",
        "secretPresenceChecked",
        "secretValueRead",
        "networkAccess",
        "realCallAfterEvidenceAuthorized",
        "realLlmCalled",
        "generatedContentCreated",
        "taskCreated",
        "reviewBypassed",
        "realCallAuthorized",
        "autoPublishAllowed",
        "realPublish",
    ]:
        assert context[key] is False


def confirmed_request(**overrides):
    payload = asdict(confirmed_executor_request())
    payload.update(
        {
            "approval_ref": "DRY-RUN-EVIDENCE-001",
            "dry_run_evidence_scope_confirmed": True,
            "command_review_record_confirmed": True,
            "evidence_owner_confirmed": True,
            "evidence_retention_policy_confirmed": True,
            "no_evidence_file_write_confirmed": True,
            "no_command_materialization_after_evidence_confirmed": True,
            "no_command_execution_after_evidence_confirmed": True,
            "no_dependency_file_mutation_after_evidence_confirmed": True,
            "no_dependency_install_after_evidence_confirmed": True,
            "no_real_call_after_evidence_confirmed": True,
        }
    )
    payload.update(overrides)
    return RealSdkDependencyDryRunEvidenceRequest(**payload)


def confirmed_cli_args():
    args = confirmed_executor_cli_args()
    args[1] = "real-sdk-dependency-dry-run-evidence"
    args[2] = "record"
    args[args.index("--approval-ref") + 1] = "DRY-RUN-EVIDENCE-001"
    flags = [
        "dry-run-evidence-scope",
        "command-review-record",
        "evidence-owner",
        "evidence-retention-policy",
        "no-evidence-file-write",
        "no-command-materialization-after-evidence",
        "no-command-execution-after-evidence",
        "no-dependency-file-mutation-after-evidence",
        "no-dependency-install-after-evidence",
        "no-real-call-after-evidence",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def test_real_sdk_dependency_dry_run_evidence_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-dry-run-evidence.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_dry_run_evidence"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["requiredContext"]["dryRunEvidenceOnly"] is True
    assert contract["requiredContext"]["dryRunEvidenceModelReady"] is False
    assert contract["requiredContext"]["readyForCommandReviewEvidence"] is False
    assert contract["requiredContext"]["dryRunExecuted"] is False
    assert contract["requiredContext"]["evidenceFileWritten"] is False
    assert contract["requiredContext"]["commandExecuted"] is False
    assert "write_dry_run_evidence_file" in contract["blockedOperations"]
    assert "persist_command_review_record" in contract["blockedOperations"]
    assert "execute_dry_run" in contract["blockedOperations"]
    assert "execute_install_command" in contract["blockedOperations"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_sdk_dependency_dry_run_evidence" in contract["recommendedCommandIds"]

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_dry_run_evidence_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_dependency_dry_run_evidence(root=ROOT)

    assert descriptor["dryRunEvidenceId"] == "real_sdk_dependency_dry_run_evidence"
    assert descriptor["gateMode"] == "DEPENDENCY_DRY_RUN_EVIDENCE_DISABLED_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["requiresExecutorModelReady"] is True
    assert descriptor["dryRunEvidenceOnly"] is True
    assert "future_install_command_review" in descriptor["pipeline"]
    assert_safe_evidence_context(descriptor)


def test_real_sdk_dependency_dry_run_evidence_default_is_not_ready_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "evidence-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = build_real_sdk_dependency_dry_run_evidence(
        RealSdkDependencyDryRunEvidenceRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["dryRunEvidenceChecklist"]}
    assert result["executorModelReady"] is False
    assert result["dryRunEvidenceModelReady"] is False
    assert result["readyForCommandReviewEvidence"] is False
    assert checklist["executor_model_ready"]["passed"] is False
    assert checklist["evidence_owner_confirmed"]["passed"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_evidence_context(result)


def test_real_sdk_dependency_dry_run_evidence_executor_ready_but_missing_evidence_confirmations():
    request = confirmed_request(evidence_owner_confirmed=False, no_evidence_file_write_confirmed=False)
    result = build_real_sdk_dependency_dry_run_evidence(request, root=ROOT)
    checklist = {item["id"]: item for item in result["dryRunEvidenceChecklist"]}

    assert result["executorModelReady"] is True
    assert result["executorSummary"]["readyForDisabledDependencyExecutor"] is True
    assert result["dryRunEvidenceModelReady"] is False
    assert result["readyForCommandReviewEvidence"] is False
    assert checklist["executor_model_ready"]["passed"] is True
    assert checklist["evidence_owner_confirmed"]["passed"] is False
    assert checklist["no_evidence_file_write_confirmed"]["passed"] is False
    assert_safe_evidence_context(result)


def test_real_sdk_dependency_dry_run_evidence_ready_but_no_write_or_execution():
    result = build_real_sdk_dependency_dry_run_evidence(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["dryRunEvidenceChecklist"]}

    assert result["executorModelReady"] is True
    assert result["dryRunEvidenceModelReady"] is True
    assert result["readyForCommandReviewEvidence"] is True
    assert result["dryRunExecuted"] is False
    assert result["evidenceFileWritten"] is False
    assert result["commandReviewRecordPersisted"] is False
    assert result["commandMaterialized"] is False
    assert checklist["no_command_execution_after_evidence_confirmed"]["passed"] is True
    assert result["dryRunEvidenceModel"]["writeNow"] is False
    assert result["dryRunEvidenceModel"]["dryRunNow"] is False
    assert result["dryRunEvidenceModel"]["commandReview"]["allowedCommands"] == []
    assert result["dryRunEvidenceModel"]["evidenceRecord"]["status"] == "NOT_WRITTEN"
    assert all(item["allowedNow"] is False for item in result["dryRunEvidenceModel"]["blockedActions"])
    assert result["futureChangeEnvelope"]["dryRunExecuted"] is False
    assert result["futureChangeEnvelope"]["evidenceFileWritten"] is False
    assert result["futureChangeEnvelope"]["commandExecuted"] is False
    assert result["futureChangeEnvelope"]["realLlmCalled"] is False
    assert_safe_evidence_context(result)


def test_real_sdk_dependency_dry_run_evidence_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_dry_run_evidence(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_dry_run_evidence_error_context(
            exc,
            request=request,
            root=ROOT,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["dryRunEvidenceModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_evidence_context(context)


def test_real_sdk_dependency_dry_run_evidence_cli_describe_and_record_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-dry-run-evidence", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["dryRunEvidenceId"] == "real_sdk_dependency_dry_run_evidence"
    assert payload["data"]["dryRunEvidenceModelReady"] is False
    assert_safe_evidence_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-dry-run-evidence", "record", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["executorModelReady"] is False
    assert payload["data"]["dryRunEvidenceModelReady"] is False
    assert_safe_evidence_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["executorModelReady"] is True
    assert payload["data"]["dryRunEvidenceModelReady"] is True
    assert payload["data"]["readyForCommandReviewEvidence"] is True
    assert payload["data"]["dryRunExecuted"] is False
    assert payload["data"]["evidenceFileWritten"] is False
    assert payload["data"]["commandExecuted"] is False
    assert_safe_evidence_context(payload["data"])


def test_real_sdk_dependency_dry_run_evidence_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-dry-run-evidence",
            "record",
            "--provider",
            "openai",
            "--payload",
            "not-json",
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "payload"

    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-dry-run-evidence",
            "record",
            "--provider",
            "openai",
            "--output-kind",
            "Exam",
        ],
        capsys,
    )

    assert exit_code == 1
    assert_json_envelope(payload)
    assert payload["code"] == "VALIDATION_ERROR"
    context = payload["realSdkDependencyDryRunEvidenceContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_evidence_context(context)
