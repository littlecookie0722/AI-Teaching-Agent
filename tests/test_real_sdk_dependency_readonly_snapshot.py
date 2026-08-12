import json
from dataclasses import asdict
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyReadonlySnapshotRequest,
    build_real_sdk_dependency_readonly_snapshot,
    build_real_sdk_dependency_readonly_snapshot_error_context,
    describe_real_sdk_dependency_readonly_snapshot,
)
from tests.test_real_sdk_dependency_executor_disabled import assert_json_envelope
from tests.test_real_sdk_dependency_target_resolver import (
    confirmed_cli_args as confirmed_target_cli_args,
    confirmed_request as confirmed_target_request,
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


def assert_safe_snapshot_context(context):
    for key in [
        "snapshotModelMaterialized",
        "snapshotReviewRecordPersisted",
        "snapshotFileWritten",
        "snapshotArtifactWritten",
        "targetPathResolutionExecuted",
        "dependencyManifestTargetResolved",
        "dependencyLockfileTargetResolved",
        "dependencySnapshotReadFromFile",
        "dependencySnapshotContentCaptured",
        "dependencyFileRead",
        "liveDependencyFileRead",
        "targetFileWritten",
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
        "realCallAfterSnapshotAuthorized",
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
    payload = asdict(confirmed_target_request())
    payload.update(
        {
            "approval_ref": "READONLY-SNAPSHOT-001",
            "readonly_snapshot_scope_confirmed": True,
            "snapshot_review_policy_confirmed": True,
            "manifest_snapshot_policy_confirmed": True,
            "lockfile_snapshot_policy_confirmed": True,
            "snapshot_redaction_policy_confirmed": True,
            "no_live_dependency_file_read_after_snapshot_confirmed": True,
            "no_snapshot_file_write_confirmed": True,
            "no_patch_generation_after_snapshot_confirmed": True,
            "no_command_execution_after_snapshot_confirmed": True,
            "no_dependency_install_after_snapshot_confirmed": True,
            "no_real_call_after_snapshot_confirmed": True,
        }
    )
    payload.update(overrides)
    return RealSdkDependencyReadonlySnapshotRequest(**payload)


def confirmed_cli_args():
    args = confirmed_target_cli_args()
    args[1] = "real-sdk-dependency-readonly-snapshot"
    args[2] = "snapshot"
    args[args.index("--approval-ref") + 1] = "READONLY-SNAPSHOT-001"
    flags = [
        "readonly-snapshot-scope",
        "snapshot-review-policy",
        "manifest-snapshot-policy",
        "lockfile-snapshot-policy",
        "snapshot-redaction-policy",
        "no-live-dependency-file-read-after-snapshot",
        "no-snapshot-file-write",
        "no-patch-generation-after-snapshot",
        "no-command-execution-after-snapshot",
        "no-dependency-install-after-snapshot",
        "no-real-call-after-snapshot",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def test_real_sdk_dependency_readonly_snapshot_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-readonly-snapshot.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_readonly_snapshot"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["requiredContext"]["readonlySnapshotOnly"] is True
    assert contract["requiredContext"]["readonlySnapshotModelReady"] is False
    assert contract["requiredContext"]["readyForReadonlyDependencySnapshotReview"] is False
    assert contract["requiredContext"]["dependencySnapshotReadFromFile"] is False
    assert contract["requiredContext"]["snapshotFileWritten"] is False
    assert contract["requiredContext"]["patchGenerated"] is False
    assert "read_live_dependency_manifest" in contract["blockedOperations"]
    assert "write_snapshot_file" in contract["blockedOperations"]
    assert "capture_dependency_snapshot_content" in contract["blockedOperations"]
    assert "test_real_sdk_dependency_readonly_snapshot" in contract["recommendedCommandIds"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_readonly_snapshot_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_dependency_readonly_snapshot(root=ROOT)

    assert descriptor["readonlySnapshotId"] == "real_sdk_dependency_readonly_snapshot"
    assert descriptor["gateMode"] == "DEPENDENCY_READONLY_SNAPSHOT_DISABLED_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["requiresTargetResolverModelReady"] is True
    assert descriptor["readonlySnapshotOnly"] is True
    assert "future_dependency_manifest_content_review" in descriptor["pipeline"]
    assert_safe_snapshot_context(descriptor)


def test_real_sdk_dependency_readonly_snapshot_default_is_not_ready_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "snapshot-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = build_real_sdk_dependency_readonly_snapshot(
        RealSdkDependencyReadonlySnapshotRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["readonlySnapshotChecklist"]}
    assert result["targetResolverModelReady"] is False
    assert result["readonlySnapshotModelReady"] is False
    assert result["readyForReadonlyDependencySnapshotReview"] is False
    assert checklist["target_resolver_model_ready"]["passed"] is False
    assert checklist["readonly_snapshot_scope_confirmed"]["passed"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_snapshot_context(result)


def test_real_sdk_dependency_readonly_snapshot_target_ready_but_missing_snapshot_confirmations():
    request = confirmed_request(snapshot_redaction_policy_confirmed=False, no_snapshot_file_write_confirmed=False)
    result = build_real_sdk_dependency_readonly_snapshot(request, root=ROOT)
    checklist = {item["id"]: item for item in result["readonlySnapshotChecklist"]}

    assert result["targetResolverModelReady"] is True
    assert result["targetResolverSummary"]["readyForDependencyTargetReview"] is True
    assert result["readonlySnapshotModelReady"] is False
    assert result["readyForReadonlyDependencySnapshotReview"] is False
    assert checklist["target_resolver_model_ready"]["passed"] is True
    assert checklist["snapshot_redaction_policy_confirmed"]["passed"] is False
    assert checklist["no_snapshot_file_write_confirmed"]["passed"] is False
    assert_safe_snapshot_context(result)


def test_real_sdk_dependency_readonly_snapshot_ready_but_no_read_write_snapshot_patch_or_execution():
    result = build_real_sdk_dependency_readonly_snapshot(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["readonlySnapshotChecklist"]}

    assert result["targetResolverModelReady"] is True
    assert result["readonlySnapshotModelReady"] is True
    assert result["readyForReadonlyDependencySnapshotReview"] is True
    assert result["dependencySnapshotReadFromFile"] is False
    assert result["dependencySnapshotContentCaptured"] is False
    assert result["snapshotFileWritten"] is False
    assert result["patchGenerated"] is False
    assert result["commandExecuted"] is False
    assert result["dependencyInstallExecuted"] is False
    assert checklist["no_live_dependency_file_read_after_snapshot_confirmed"]["passed"] is True
    assert result["readonlySnapshotModel"]["readNow"] is False
    assert result["readonlySnapshotModel"]["writeNow"] is False
    assert result["readonlySnapshotModel"]["patchNow"] is False
    assert result["readonlySnapshotModel"]["redactionPolicy"]["dependencyContentIncludedNow"] is False
    assert all(item["allowedNow"] is False for item in result["readonlySnapshotModel"]["blockedActions"])
    assert result["futureChangeEnvelope"]["dependencySnapshotReadFromFile"] is False
    assert result["futureChangeEnvelope"]["snapshotFileWritten"] is False
    assert result["futureChangeEnvelope"]["patchGenerated"] is False
    assert result["futureChangeEnvelope"]["realLlmCalled"] is False
    assert_safe_snapshot_context(result)


def test_real_sdk_dependency_readonly_snapshot_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_readonly_snapshot(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_readonly_snapshot_error_context(
            exc,
            request=request,
            root=ROOT,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["readonlySnapshotModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_snapshot_context(context)


def test_real_sdk_dependency_readonly_snapshot_cli_describe_and_snapshot_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-readonly-snapshot", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["readonlySnapshotId"] == "real_sdk_dependency_readonly_snapshot"
    assert payload["data"]["readonlySnapshotModelReady"] is False
    assert_safe_snapshot_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-readonly-snapshot", "snapshot", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["targetResolverModelReady"] is False
    assert payload["data"]["readonlySnapshotModelReady"] is False
    assert_safe_snapshot_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["targetResolverModelReady"] is True
    assert payload["data"]["readonlySnapshotModelReady"] is True
    assert payload["data"]["readyForReadonlyDependencySnapshotReview"] is True
    assert payload["data"]["dependencySnapshotReadFromFile"] is False
    assert payload["data"]["snapshotFileWritten"] is False
    assert payload["data"]["patchGenerated"] is False
    assert_safe_snapshot_context(payload["data"])


def test_real_sdk_dependency_readonly_snapshot_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-readonly-snapshot",
            "snapshot",
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
            "real-sdk-dependency-readonly-snapshot",
            "snapshot",
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
    context = payload["realSdkDependencyReadonlySnapshotContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_snapshot_context(context)
