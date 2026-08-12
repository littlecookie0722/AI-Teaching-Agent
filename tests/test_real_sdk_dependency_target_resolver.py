import json
from dataclasses import asdict
from pathlib import Path

from cli.lab_cli import main
from providers import (
    ProviderError,
    RealSdkDependencyTargetResolverRequest,
    build_real_sdk_dependency_target_resolver,
    build_real_sdk_dependency_target_resolver_error_context,
    describe_real_sdk_dependency_target_resolver,
)
from tests.test_real_sdk_dependency_dry_run_evidence import (
    confirmed_cli_args as confirmed_evidence_cli_args,
    confirmed_request as confirmed_evidence_request,
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


def assert_safe_target_context(context):
    for key in [
        "targetPathResolutionExecuted",
        "dependencyManifestTargetResolved",
        "dependencyLockfileTargetResolved",
        "dependencySnapshotReadFromFile",
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
        "realCallAfterResolverAuthorized",
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
    payload = asdict(confirmed_evidence_request())
    payload.update(
        {
            "approval_ref": "TARGET-RESOLVER-001",
            "target_resolver_scope_confirmed": True,
            "manifest_target_policy_confirmed": True,
            "lockfile_target_policy_confirmed": True,
            "path_safety_policy_confirmed": True,
            "no_live_dependency_file_read_confirmed": True,
            "no_target_file_write_confirmed": True,
            "no_patch_generation_after_resolver_confirmed": True,
            "no_command_execution_after_resolver_confirmed": True,
            "no_dependency_install_after_resolver_confirmed": True,
            "no_real_call_after_resolver_confirmed": True,
        }
    )
    payload.update(overrides)
    return RealSdkDependencyTargetResolverRequest(**payload)


def confirmed_cli_args():
    args = confirmed_evidence_cli_args()
    args[1] = "real-sdk-dependency-target-resolver"
    args[2] = "resolve"
    args[args.index("--approval-ref") + 1] = "TARGET-RESOLVER-001"
    flags = [
        "target-resolver-scope",
        "manifest-target-policy",
        "lockfile-target-policy",
        "path-safety-policy",
        "no-live-dependency-file-read",
        "no-target-file-write",
        "no-patch-generation-after-resolver",
        "no-command-execution-after-resolver",
        "no-dependency-install-after-resolver",
        "no-real-call-after-resolver",
    ]
    return args + [f"--confirm-{flag}" for flag in flags]


def test_real_sdk_dependency_target_resolver_contract_is_mock_only_and_local():
    contract = load_json("providers/real-sdk-dependency-target-resolver.contract.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert contract["phase"] == "Phase 1"
    assert contract["targetPhase"] == "Phase 2"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["gateId"] == "real_sdk_dependency_target_resolver"
    assert contract["activeProvider"] == "mock"
    assert contract["supportedProvider"] == "openai"
    assert contract["requiredContext"]["targetResolverOnly"] is True
    assert contract["requiredContext"]["targetResolverModelReady"] is False
    assert contract["requiredContext"]["readyForDependencyTargetReview"] is False
    assert contract["requiredContext"]["liveDependencyFileRead"] is False
    assert contract["requiredContext"]["targetFileWritten"] is False
    assert contract["requiredContext"]["patchGenerated"] is False
    assert "read_live_dependency_manifest" in contract["blockedOperations"]
    assert "write_dependency_target_file" in contract["blockedOperations"]
    assert "generate_dependency_patch" in contract["blockedOperations"]
    assert "test_real_sdk_dependency_target_resolver" in contract["recommendedCommandIds"]
    assert set(contract["recommendedCommandIds"]).issubset(allowed)

    for entry in contract["inputs"]:
        assert entry["required"] is True
        assert entry["localOnly"] is True
        assert (ROOT / entry["path"]).exists()


def test_real_sdk_dependency_target_resolver_describe_is_disabled_and_safe():
    descriptor = describe_real_sdk_dependency_target_resolver(root=ROOT)

    assert descriptor["targetResolverId"] == "real_sdk_dependency_target_resolver"
    assert descriptor["gateMode"] == "DEPENDENCY_TARGET_RESOLVER_DISABLED_ONLY"
    assert descriptor["defaultProvider"] == "mock"
    assert descriptor["requiresDryRunEvidenceModelReady"] is True
    assert descriptor["targetResolverOnly"] is True
    assert "future_dependency_manifest_readonly_review" in descriptor["pipeline"]
    assert_safe_target_context(descriptor)


def test_real_sdk_dependency_target_resolver_default_is_not_ready_and_redacts_payload(monkeypatch):
    fake_key = "sk-" + "target-hidden"
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    result = build_real_sdk_dependency_target_resolver(
        RealSdkDependencyTargetResolverRequest(
            provider_id="openai",
            payload={"apiKey": fake_key, "text": f"Bearer {fake_key}"},
        ),
        root=ROOT,
    )

    serialized = json.dumps(result, ensure_ascii=False)
    checklist = {item["id"]: item for item in result["targetResolverChecklist"]}
    assert result["dryRunEvidenceModelReady"] is False
    assert result["targetResolverModelReady"] is False
    assert result["readyForDependencyTargetReview"] is False
    assert checklist["dry_run_evidence_model_ready"]["passed"] is False
    assert checklist["target_resolver_scope_confirmed"]["passed"] is False
    assert fake_key not in serialized
    assert "[REDACTED]" in serialized
    assert_safe_target_context(result)


def test_real_sdk_dependency_target_resolver_evidence_ready_but_missing_target_confirmations():
    request = confirmed_request(path_safety_policy_confirmed=False, no_target_file_write_confirmed=False)
    result = build_real_sdk_dependency_target_resolver(request, root=ROOT)
    checklist = {item["id"]: item for item in result["targetResolverChecklist"]}

    assert result["dryRunEvidenceModelReady"] is True
    assert result["dryRunEvidenceSummary"]["readyForCommandReviewEvidence"] is True
    assert result["targetResolverModelReady"] is False
    assert result["readyForDependencyTargetReview"] is False
    assert checklist["dry_run_evidence_model_ready"]["passed"] is True
    assert checklist["path_safety_policy_confirmed"]["passed"] is False
    assert checklist["no_target_file_write_confirmed"]["passed"] is False
    assert_safe_target_context(result)


def test_real_sdk_dependency_target_resolver_ready_but_no_read_write_patch_or_execution():
    result = build_real_sdk_dependency_target_resolver(confirmed_request(), root=ROOT)
    checklist = {item["id"]: item for item in result["targetResolverChecklist"]}

    assert result["dryRunEvidenceModelReady"] is True
    assert result["targetResolverModelReady"] is True
    assert result["readyForDependencyTargetReview"] is True
    assert result["liveDependencyFileRead"] is False
    assert result["targetFileWritten"] is False
    assert result["patchGenerated"] is False
    assert result["commandExecuted"] is False
    assert result["dependencyInstallExecuted"] is False
    assert checklist["no_live_dependency_file_read_confirmed"]["passed"] is True
    assert result["targetResolverModel"]["readNow"] is False
    assert result["targetResolverModel"]["writeNow"] is False
    assert result["targetResolverModel"]["patchNow"] is False
    assert result["targetResolverModel"]["candidateTargets"][0]["path"] == "pyproject.toml"
    assert result["targetResolverModel"]["candidateTargets"][1]["path"] == "requirements.txt"
    assert all(item["allowedNow"] is False for item in result["targetResolverModel"]["blockedActions"])
    assert result["futureChangeEnvelope"]["liveDependencyFileRead"] is False
    assert result["futureChangeEnvelope"]["targetFileWritten"] is False
    assert result["futureChangeEnvelope"]["patchGenerated"] is False
    assert result["futureChangeEnvelope"]["realLlmCalled"] is False
    assert_safe_target_context(result)


def test_real_sdk_dependency_target_resolver_invalid_scope_keeps_safe_error_context():
    request = confirmed_request(output_kind="Exam")

    try:
        build_real_sdk_dependency_target_resolver(request, root=ROOT)
    except ProviderError as exc:
        assert exc.code == "VALIDATION_ERROR"
        context = build_real_sdk_dependency_target_resolver_error_context(
            exc,
            request=request,
            root=ROOT,
        )
    else:
        raise AssertionError("expected ProviderError")

    assert context["errorCode"] == "VALIDATION_ERROR"
    assert context["targetResolverModelReady"] is False
    assert context["outputKind"] == "Exam"
    assert_safe_target_context(context)


def test_real_sdk_dependency_target_resolver_cli_describe_and_resolve_paths(capsys):
    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-target-resolver", "describe"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["targetResolverId"] == "real_sdk_dependency_target_resolver"
    assert payload["data"]["targetResolverModelReady"] is False
    assert_safe_target_context(payload["data"])

    exit_code, payload = run_cli(
        ["provider", "real-sdk-dependency-target-resolver", "resolve", "--provider", "openai"],
        capsys,
    )

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["dryRunEvidenceModelReady"] is False
    assert payload["data"]["targetResolverModelReady"] is False
    assert_safe_target_context(payload["data"])

    exit_code, payload = run_cli(confirmed_cli_args(), capsys)

    assert exit_code == 0
    assert_json_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["dryRunEvidenceModelReady"] is True
    assert payload["data"]["targetResolverModelReady"] is True
    assert payload["data"]["readyForDependencyTargetReview"] is True
    assert payload["data"]["liveDependencyFileRead"] is False
    assert payload["data"]["targetFileWritten"] is False
    assert payload["data"]["patchGenerated"] is False
    assert_safe_target_context(payload["data"])


def test_real_sdk_dependency_target_resolver_cli_rejects_bad_payload_and_invalid_scope(capsys):
    exit_code, payload = run_cli(
        [
            "provider",
            "real-sdk-dependency-target-resolver",
            "resolve",
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
            "real-sdk-dependency-target-resolver",
            "resolve",
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
    context = payload["realSdkDependencyTargetResolverContext"]
    assert context["outputKind"] == "Exam"
    assert_safe_target_context(context)
