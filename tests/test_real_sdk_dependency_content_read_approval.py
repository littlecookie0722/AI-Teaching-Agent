import json
from dataclasses import asdict
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyContentReadApprovalRequest,
    build_real_sdk_dependency_content_read_approval,
    build_real_sdk_dependency_content_read_approval_error_context,
    describe_real_sdk_dependency_content_read_approval,
)
from tests.test_real_sdk_dependency_readonly_snapshot import (
    assert_safe_snapshot_context,
    confirmed_cli_args as confirmed_snapshot_cli_args,
    confirmed_request as confirmed_snapshot_request,
)
from tests.test_real_sdk_dependency_executor_disabled import assert_json_envelope


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def run_cli(args, capsys):
    exit_code = main(args)
    output = capsys.readouterr().out
    payload = json.loads(output)
    return exit_code, payload


def assert_safe_content_read_context(context):
    assert_safe_snapshot_context(context)
    for key in [
        "contentReadApprovalRecordPersisted",
        "contentReadApprovalArtifactWritten",
        "dependencyContentReadAuthorized",
        "dependencyContentReadExecuted",
        "dependencyManifestContentRead",
        "dependencyLockfileContentRead",
        "dependencyContentPersisted",
        "dependencyContentReturned",
        "rawDependencyContentReturned",
        "realCallAfterContentReadApprovalAuthorized",
    ]:
        assert context[key] is False


def confirmed_request(**overrides):
    payload = asdict(confirmed_snapshot_request())
    payload.update(
        {
            "approval_ref": "CONTENT-READ-APPROVAL-001",
            "content_read_approval_scope_confirmed": True,
            "content_read_reviewer_confirmed": True,
            "content_read_reason_confirmed": True,
            "content_read_redaction_policy_confirmed": True,
            "manifest_content_read_policy_confirmed": True,
            "lockfile_content_read_policy_confirmed": True,
            "no_dependency_content_read_now_confirmed": True,
            "no_content_persistence_confirmed": True,
            "no_patch_generation_after_content_read_approval_confirmed": True,
            "no_command_execution_after_content_read_approval_confirmed": True,
            "no_dependency_install_after_content_read_approval_confirmed": True,
            "no_real_call_after_content_read_approval_confirmed": True,
        }
    )
    payload.update(overrides)
    return RealSdkDependencyContentReadApprovalRequest(**payload)


def confirmed_cli_args():
    args = confirmed_snapshot_cli_args()
    args[1] = "real-sdk-dependency-content-read-approval"
    args[2] = "approve-read"
    args[args.index("--approval-ref") + 1] = "CONTENT-READ-APPROVAL-001"
    flags = [
        "content-read-approval-scope",
        "content-read-reviewer",
        "content-read-reason",
        "content-read-redaction-policy",
        "manifest-content-read-policy",
        "lockfile-content-read-policy",
        "no-dependency-content-read-now",
        "no-content-persistence",
        "no-patch-generation-after-content-read-approval",
        "no-command-execution-after-content-read-approval",
        "no-dependency-install-after-content-read-approval",
        "no-real-call-after-content-read-approval",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def test_real_sdk_dependency_content_read_approval_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-content-read-approval.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_content_read_approval"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["requiredContext"]["contentReadApprovalOnly"] is True
    assert contract["requiredContext"]["contentReadApprovalModelReady"] is False
    assert contract["requiredContext"]["readyForFutureDependencyContentReadReview"] is False
    assert contract["requiredContext"]["dependencyContentReadAuthorized"] is False
    assert contract["requiredContext"]["dependencyContentReadExecuted"] is False
    assert contract["requiredContext"]["dependencyContentReturned"] is False
    assert "read_dependency_manifest_content" in contract["blockedOperations"]
    assert "return_raw_dependency_content" in contract["blockedOperations"]
    assert "persist_dependency_content" in contract["blockedOperations"]
    assert "test_real_sdk_dependency_content_read_approval" in contract["recommendedCommandIds"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_content_read_approval_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_dependency_content_read_approval(root=ROOT)

    assert descriptor["contentReadApprovalId"] == "real_sdk_dependency_content_read_approval"
    assert descriptor["gateMode"] == "DEPENDENCY_CONTENT_READ_APPROVAL_DISABLED_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["requiresReadonlySnapshotModelReady"] is True
    assert descriptor["contentReadApprovalOnly"] is True
    assert "future_dependency_content_read_after_explicit_approval" in descriptor["pipeline"]
    assert_safe_content_read_context(descriptor)


def test_real_sdk_dependency_content_read_approval_default_is_not_ready_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "content-read-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = build_real_sdk_dependency_content_read_approval(
        RealSdkDependencyContentReadApprovalRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["contentReadApprovalChecklist"]}
    assert result["readonlySnapshotModelReady"] is False
    assert result["contentReadApprovalModelReady"] is False
    assert result["readyForFutureDependencyContentReadReview"] is False
    assert checklist["readonly_snapshot_model_ready"]["passed"] is False
    assert checklist["content_read_approval_scope_confirmed"]["passed"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_content_read_context(result)


def test_real_sdk_dependency_content_read_approval_snapshot_ready_but_missing_confirmations():
    request = confirmed_request(
        content_read_reason_confirmed=False,
        no_content_persistence_confirmed=False,
    )
    result = build_real_sdk_dependency_content_read_approval(request, root=ROOT)
    checklist = {item["id"]: item for item in result["contentReadApprovalChecklist"]}

    assert result["readonlySnapshotModelReady"] is True
    assert result["readonlySnapshotSummary"]["readyForReadonlyDependencySnapshotReview"] is True
    assert result["contentReadApprovalModelReady"] is False
    assert result["readyForFutureDependencyContentReadReview"] is False
    assert checklist["readonly_snapshot_model_ready"]["passed"] is True
    assert checklist["content_read_reason_confirmed"]["passed"] is False
    assert checklist["no_content_persistence_confirmed"]["passed"] is False
    assert_safe_content_read_context(result)


def test_real_sdk_dependency_content_read_approval_ready_but_no_read_persist_patch_or_execution():
    result = build_real_sdk_dependency_content_read_approval(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["contentReadApprovalChecklist"]}

    assert result["readonlySnapshotModelReady"] is True
    assert result["contentReadApprovalModelReady"] is True
    assert result["readyForFutureDependencyContentReadReview"] is True
    assert result["dependencyContentReadAuthorized"] is False
    assert result["dependencyContentReadExecuted"] is False
    assert result["dependencyManifestContentRead"] is False
    assert result["dependencyLockfileContentRead"] is False
    assert result["dependencyContentPersisted"] is False
    assert result["dependencyContentReturned"] is False
    assert result["patchGenerated"] is False
    assert result["commandExecuted"] is False
    assert result["dependencyInstallExecuted"] is False
    assert checklist["no_dependency_content_read_now_confirmed"]["passed"] is True
    assert result["contentReadApprovalModel"]["readNow"] is False
    assert result["contentReadApprovalModel"]["writeNow"] is False
    assert result["contentReadApprovalModel"]["persistNow"] is False
    assert result["contentReadApprovalModel"]["contentReadScope"]["contentIncludedNow"] is False
    assert result["contentReadApprovalModel"]["redactionPolicy"]["rawDependencyContentReturnedNow"] is False
    assert all(item["allowedNow"] is False for item in result["contentReadApprovalModel"]["blockedActions"])
    assert result["futureChangeEnvelope"]["dependencyContentReadAuthorized"] is False
    assert result["futureChangeEnvelope"]["dependencyContentReturned"] is False
    assert result["futureChangeEnvelope"]["realLlmCalled"] is False
    assert_safe_content_read_context(result)


def test_real_sdk_dependency_content_read_approval_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_content_read_approval(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_content_read_approval_error_context(
            exc,
            request=request,
            root=ROOT,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["contentReadApprovalModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_content_read_context(context)


def test_real_sdk_dependency_content_read_approval_cli_describe_and_approve_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-content-read-approval", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["contentReadApprovalId"] == "real_sdk_dependency_content_read_approval"
    assert payload["data"]["contentReadApprovalModelReady"] is False
    assert_safe_content_read_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-content-read-approval", "approve-read", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["readonlySnapshotModelReady"] is False
    assert payload["data"]["contentReadApprovalModelReady"] is False
    assert_safe_content_read_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["readonlySnapshotModelReady"] is True
    assert payload["data"]["contentReadApprovalModelReady"] is True
    assert payload["data"]["readyForFutureDependencyContentReadReview"] is True
    assert payload["data"]["dependencyContentReadAuthorized"] is False
    assert payload["data"]["dependencyContentReturned"] is False
    assert payload["data"]["patchGenerated"] is False
    assert_safe_content_read_context(payload["data"])


def test_real_sdk_dependency_content_read_approval_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-content-read-approval",
            "approve-read",
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
            "real-sdk-dependency-content-read-approval",
            "approve-read",
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
    context = payload["realSdkDependencyContentReadApprovalContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_content_read_context(context)
