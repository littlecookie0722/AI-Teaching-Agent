import json
import subprocess
from pathlib import Path

from cli.dsl import load_schema, load_yaml, validate_dsl
from sandbox.controlled_command_executor import (
    DEFAULT_IMAGE,
    MODE,
    ControlledCommandSandboxError,
    build_controlled_command_sandbox_report,
)


ROOT = Path(__file__).resolve().parents[1]


def load_controlled_grading():
    grading = load_yaml(ROOT / "templates/grading/examples/controlled-command-sandbox.yaml")
    validate_dsl(grading, load_schema("grading", ROOT))
    return grading


def fake_completed(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


def image_inspection(image_id="sha256:demo"):
    return json.dumps(
        {
            "Id": image_id,
            "RepoTags": ["local-python:demo"],
            "Created": "2026-07-12T00:00:00Z",
            "Config": {
                "Labels": {
                    "org.opencontainers.image.title": "AI Training Platform Python Pytest Grading Image",
                    "org.opencontainers.image.version": "0.1",
                    "ai-training-platform.sandbox": "controlled-command",
                    "ai-training-platform.sandbox.profile": "local-python-pytest-controlled-v1",
                }
            },
        }
    )


def test_controlled_command_sandbox_executes_stdout_and_pytest_with_docker(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:2] == ["docker", "info"]:
            return fake_completed(args, stdout='"29.5.3"')
        if args[:3] == ["docker", "image", "inspect"]:
            return fake_completed(args, stdout="sha256:demo")
        if "main.py" in args:
            return fake_completed(args, stdout="accuracy=0.90\n")
        if "pytest" in args:
            return fake_completed(args, stdout="1 passed\n")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_run)

    report = build_controlled_command_sandbox_report(
        load_controlled_grading(),
        ROOT / "examples/submissions/controlled-command-demo",
        "trace_controlled",
        image="local-python:demo",
    )

    assert report["mode"] == MODE
    assert report["runner"]["runtime"] == "docker"
    assert report["runner"]["image"] == "local-python:demo"
    assert report["runner"]["imageSupplyChain"]["inspection"]["imageId"] == "sha256:demo"
    assert report["imageSupplyChain"]["component"] == "ControlledDockerImageSupplyChain"
    assert report["imageSupplyChain"]["policyId"] == "controlled-docker-local-image-allowlist-v1"
    assert report["imageSupplyChain"]["allowlist"]["matched"] is True
    assert report["imageSupplyChain"]["allowlist"]["matchedEntry"] == "local-python:"
    assert report["imageSupplyChain"]["allowlist"]["status"] == "MATCHED"
    assert report["imageSupplyChain"]["registry"]["automaticPullDisabled"] is True
    assert report["imageSupplyChain"]["registry"]["registryAuthUsed"] is False
    assert report["executionSummary"]["executed"] == 2
    assert report["executionSummary"]["completed"] == 2
    assert report["executionSummary"]["passed"] == 2
    assert report["checkSummary"]["executed"] == 2
    assert report["checkSummary"]["completed"] == 2
    assert report["score"]["earnedScore"] == 100
    assert report["score"]["executableScore"] == 100
    assert report["isolation"]["submissionMount"]["mode"] == "ro"
    assert report["isolation"]["submissionMount"]["containerPath"] == "/workspace/submission"
    assert report["isolation"]["networkEnabled"] is False
    assert report["isolation"]["containerReadOnlyRootFilesystem"] is True
    assert report["isolation"]["resourceLimits"]["cpus"] == "1"
    assert report["isolation"]["resourceLimits"]["memory"] == "512m"
    assert report["isolation"]["resourceLimits"]["pidsLimit"] == 64
    assert report["isolation"]["outputPolicy"]["stdoutCaptured"] is True
    assert report["isolation"]["outputPolicy"]["stderrCaptured"] is True
    assert report["isolation"]["outputPolicy"]["maxOutputChars"] == 12000
    assert report["isolation"]["imageSupplyChain"]["inspection"]["digest"] == "sha256:demo"
    assert report["isolationQuality"]["component"] == "ControlledDockerIsolationQuality"
    assert report["isolationQuality"]["qualityState"] == "CONTROLLED_DOCKER_ISOLATION_READY"
    assert report["isolationQuality"]["readyForLocalControlledEvidence"] is True
    assert report["isolationQuality"]["criticalIsolationReady"] is True
    assert report["isolationQuality"]["manualImageReviewRequired"] is False
    assert report["isolationQuality"]["passedCheckTotal"] == report["isolationQuality"]["checkTotal"]
    assert report["isolationQuality"]["failedCheckIds"] == []
    assert {item["id"] for item in report["isolationQuality"]["checks"]} >= {
        "network_disabled",
        "submission_mount_readonly",
        "rootfs_readonly",
        "resource_limits_present",
        "output_captured_by_runner",
        "local_image_inspected",
        "registry_network_not_used",
    }
    assert report["isolationQuality"]["reviewBoundary"]["productionSandboxCertified"] is False
    assert report["sandboxPolicy"]["submissionMountMode"] == "ro"
    assert report["sandboxPolicy"]["isolationQuality"]["qualityState"] == "CONTROLLED_DOCKER_ISOLATION_READY"
    assert report["sandboxPolicy"]["imageSupplyChain"]["allowlist"]["status"] == "MATCHED"
    assert report["executionSummary"]["imageId"] == "sha256:demo"
    assert report["executionSummary"]["allowlistStatus"] == "MATCHED"
    assert report["executionSummary"]["isolationQualityState"] == "CONTROLLED_DOCKER_ISOLATION_READY"
    assert report["executionSummary"]["readyForLocalControlledEvidence"] is True
    assert report["sandboxPolicy"]["outputIsolation"]["artifactWriteOnlyByRunner"] is True
    assert report["safety"]["sandboxExecuted"] is True
    assert report["safety"]["contestantCodeExecuted"] is True
    assert report["safety"]["commandExecuted"] is True
    assert report["safety"]["networkEnabled"] is False
    assert report["safety"]["unknownShellExecuted"] is False
    assert report["safety"]["pytestExecuted"] is True
    assert report["safety"]["submissionMountedReadOnly"] is True
    assert report["safety"]["outputCapturedByRunner"] is True
    assert report["safety"]["imageSupplyChainAudited"] is True
    assert report["safety"]["imageAllowlistMatched"] is True
    assert report["safety"]["imagePulledAutomatically"] is False
    assert report["safety"]["registryAuthUsed"] is False
    checks = {check["id"]: check for check in report["checks"]}
    assert checks["check_stdout_accuracy"]["evidence"]["matchedEvidence"] == ["accuracy=0.90"]
    assert checks["check_stdout_accuracy"]["isolation"]["submissionMountMode"] == "ro"
    assert checks["check_stdout_accuracy"]["evidence"]["outputTruncatedToChars"] == 12000
    assert checks["check_pytest"]["evidence"]["exitCode"] == 0
    docker_runs = [call for call in calls if call[:2] == ["docker", "run"]]
    assert len(docker_runs) == 2
    assert all("--network" in call and "none" in call for call in docker_runs)
    assert all("--read-only" in call for call in docker_runs)
    assert all("/workspace/submission:ro" in " ".join(call) for call in docker_runs)


def test_controlled_command_sandbox_default_image_is_project_grading_baseline():
    assert DEFAULT_IMAGE == "ai-grading-python:0.1"


def test_controlled_command_sandbox_records_execution_profile_and_image_metadata(monkeypatch):
    def fake_run(args, **kwargs):
        if args[:2] == ["docker", "info"]:
            return fake_completed(args, stdout='"29.5.3"')
        if args[:3] == ["docker", "image", "inspect"]:
            return fake_completed(args, stdout=image_inspection())
        if "main.py" in args:
            return fake_completed(args, stdout="accuracy=0.90\n")
        if "pytest" in args:
            return fake_completed(args, stdout="1 passed\n")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_run)

    report = build_controlled_command_sandbox_report(
        load_controlled_grading(),
        ROOT / "examples/submissions/controlled-command-demo",
        "trace_profile_metadata",
        image="local-python:demo",
    )

    assert report["executionProfile"]["id"] == "local-python-pytest-controlled-v1"
    assert report["executionProfile"]["network"]["enabled"] is False
    assert report["executionProfile"]["filesystem"]["submissionMount"]["mode"] == "ro"
    assert report["executionProfile"]["resourceLimits"]["memory"] == "512m"
    assert report["imageSupplyChain"]["metadata"]["requiredLabelsPresent"] is True
    assert report["imageSupplyChain"]["metadata"]["missingRequiredLabels"] == []
    assert report["safety"]["imageMetadataValidated"] is True


def test_controlled_command_sandbox_marks_unmatched_image_as_audit_only(monkeypatch):
    def fake_run(args, **kwargs):
        if args[:2] == ["docker", "info"]:
            return fake_completed(args, stdout='"29.5.3"')
        if args[:3] == ["docker", "image", "inspect"]:
            return fake_completed(args, stdout='"sha256:custom"')
        if "main.py" in args:
            return fake_completed(args, stdout="accuracy=0.90\n")
        if "pytest" in args:
            return fake_completed(args, stdout="1 passed\n")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_run)

    report = build_controlled_command_sandbox_report(
        load_controlled_grading(),
        ROOT / "examples/submissions/controlled-command-demo",
        "trace_custom_image",
        image="custom.registry/grading:demo",
    )

    supply_chain = report["imageSupplyChain"]
    assert supply_chain["inspection"]["imageId"] == "sha256:custom"
    assert supply_chain["allowlist"]["matched"] is False
    assert supply_chain["allowlist"]["status"] == "UNMATCHED_AUDIT_ONLY"
    assert supply_chain["allowlist"]["enforcementMode"] == "AUDIT_ONLY_LOCAL_POC"
    assert report["isolationQuality"]["qualityState"] == "CONTROLLED_DOCKER_ISOLATION_NEEDS_IMAGE_REVIEW"
    assert report["isolationQuality"]["criticalIsolationReady"] is True
    assert report["isolationQuality"]["readyForLocalControlledEvidence"] is False
    assert report["isolationQuality"]["manualImageReviewRequired"] is True
    assert report["safety"]["imageSupplyChainAudited"] is True
    assert report["safety"]["imageAllowlistMatched"] is False


def test_controlled_command_sandbox_rejects_shell_operator(monkeypatch):
    grading = load_controlled_grading()
    grading["spec"]["checks"][0]["command"] = "python main.py && echo unsafe"

    monkeypatch.setattr(
        "sandbox.controlled_command_executor.subprocess.run",
        lambda args, **kwargs: fake_completed(args, stdout="ok"),
    )

    try:
        build_controlled_command_sandbox_report(
            grading,
            ROOT / "examples/submissions/controlled-command-demo",
            "trace_shell_operator",
            image="local-python:demo",
        )
    except ControlledCommandSandboxError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "command"
    else:
        raise AssertionError("expected ControlledCommandSandboxError")


def test_controlled_command_sandbox_rejects_stdout_path_escape(monkeypatch):
    grading = load_controlled_grading()
    grading["spec"]["checks"][0]["command"] = "python ../main.py"

    monkeypatch.setattr(
        "sandbox.controlled_command_executor.subprocess.run",
        lambda args, **kwargs: fake_completed(args, stdout="ok"),
    )

    try:
        build_controlled_command_sandbox_report(
            grading,
            ROOT / "examples/submissions/controlled-command-demo",
            "trace_stdout_path_escape",
            image="local-python:demo",
        )
    except ControlledCommandSandboxError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors[0]["field"] == "command"
        assert exc.errors[0]["reason"] == "path escapes submission root"
    else:
        raise AssertionError("expected ControlledCommandSandboxError")


def test_controlled_command_sandbox_rejects_missing_docker_image(monkeypatch):
    def fake_run(args, **kwargs):
        if args[:2] == ["docker", "info"]:
            return fake_completed(args, stdout='"29.5.3"')
        if args[:3] == ["docker", "image", "inspect"]:
            raise subprocess.CalledProcessError(returncode=1, cmd=args)
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_run)

    try:
        build_controlled_command_sandbox_report(
            load_controlled_grading(),
            ROOT / "examples/submissions/controlled-command-demo",
            "trace_missing_image",
            image="missing-python:demo",
        )
    except ControlledCommandSandboxError as exc:
        assert exc.code == "SANDBOX_IMAGE_MISSING"
        assert exc.errors[0]["field"] == "image"
        assert exc.errors[1] == {"field": "nextAction", "reason": "build_or_select_a_local_allowlisted_image"}
    else:
        raise AssertionError("expected ControlledCommandSandboxError")


def test_controlled_command_sandbox_path_failure_does_not_start_container(monkeypatch):
    grading = load_controlled_grading()
    grading["spec"]["checks"] = [
        {
            "id": "check_pytest",
            "type": "pytest",
            "path": "../checks/test_escape.py",
            "score": 60,
        }
    ]
    grading["spec"]["totalScore"] = 60

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:2] == ["docker", "info"]:
            return fake_completed(args, stdout='"29.5.3"')
        if args[:3] == ["docker", "image", "inspect"]:
            return fake_completed(args, stdout="sha256:demo")
        raise AssertionError(f"container command should not start: {args}")

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_run)

    report = build_controlled_command_sandbox_report(
        grading,
        ROOT / "examples/submissions/controlled-command-demo",
        "trace_path_failure",
        image="local-python:demo",
    )

    assert report["executionSummary"]["executed"] == 0
    assert report["executionSummary"]["completed"] == 1
    assert report["executionSummary"]["failed"] == 1
    assert report["checkSummary"]["executed"] == 0
    assert report["checkSummary"]["completed"] == 1
    assert report["score"]["executableScore"] == 0
    assert report["score"]["earnedScore"] == 0
    assert report["sandboxExecuted"] is False
    assert report["contestantCodeExecuted"] is False
    assert report["commandExecuted"] is False
    assert report["safety"]["sandboxExecuted"] is False
    assert report["safety"]["contestantCodeExecuted"] is False
    assert report["safety"]["commandExecuted"] is False

    check = report["checks"][0]
    assert check["status"] == "FAILED"
    assert check["error"]["code"] == "PATH_OUTSIDE_SUBMISSION"
    assert check["sandboxExecuted"] is False
    assert check["contestantCodeExecuted"] is False
    assert check["commandExecuted"] is False
    assert check["evidence"]["auditLogRef"] is None
    assert check["isolation"]["containerStarted"] is False
    assert check["logs"][0]["event"] == "docker_command_not_started"
    assert [call[:2] for call in calls] == [["docker", "info"], ["docker", "image"]]


def test_controlled_command_sandbox_timeout_marks_attempted_execution(monkeypatch):
    grading = load_controlled_grading()
    grading["spec"]["checks"] = [grading["spec"]["checks"][0]]
    grading["spec"]["totalScore"] = 40

    def fake_run(args, **kwargs):
        if args[:2] == ["docker", "info"]:
            return fake_completed(args, stdout='"29.5.3"')
        if args[:3] == ["docker", "image", "inspect"]:
            return fake_completed(args, stdout="sha256:demo")
        if "main.py" in args:
            raise subprocess.TimeoutExpired(args, timeout=kwargs.get("timeout", 30), output="partial", stderr="late")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_run)

    report = build_controlled_command_sandbox_report(
        grading,
        ROOT / "examples/submissions/controlled-command-demo",
        "trace_timeout",
        image="local-python:demo",
    )

    assert report["executionSummary"]["executed"] == 1
    assert report["executionSummary"]["completed"] == 1
    assert report["executionSummary"]["failed"] == 1
    assert report["score"]["executableScore"] == 40
    assert report["score"]["earnedScore"] == 0
    assert report["safety"]["sandboxExecuted"] is True
    assert report["safety"]["contestantCodeExecuted"] is True
    assert report["safety"]["commandExecuted"] is True

    check = report["checks"][0]
    assert check["status"] == "ERROR"
    assert check["error"]["code"] == "COMMAND_TIMEOUT"
    assert check["sandboxExecuted"] is True
    assert check["evidence"]["stdout"] == "partial"
    assert check["evidence"]["stderr"] == "late"
    assert check["evidence"]["auditLogRef"] == f"controlled-docker://{check['id']}"
    assert check["logs"][0]["event"] == "docker_command_timeout"
