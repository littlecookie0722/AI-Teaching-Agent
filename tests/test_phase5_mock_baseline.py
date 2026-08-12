import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_phase5_mock_baseline_is_mock_only_and_safe():
    contract = load_json("delivery/phase5-mock-baseline.json")

    assert contract["phase"] == "Phase 5"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["id"] == "phase5_mock_baseline"
    assert contract["safety"]["manualOnly"] is True
    assert contract["safety"]["readOnly"] is True
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["realProviderEnabled"] is False
    assert contract["safety"]["realMcpServerStarted"] is False
    assert contract["safety"]["realAgentStarted"] is False
    assert contract["safety"]["realCloudResourceChanged"] is False
    assert contract["safety"]["realCloudResourceCreated"] is False
    assert contract["safety"]["sandboxExecuted"] is False
    assert contract["safety"]["contestantCodeExecuted"] is False
    assert contract["safety"]["unknownShellExecuted"] is False
    assert contract["safety"]["autoPublishAllowed"] is False
    assert contract["safety"]["realPublish"] is False
    assert contract["safety"]["remoteUploadAllowed"] is False
    assert contract["safety"]["secretVisibleInFrontend"] is False
    assert contract["safety"]["answerVisibleToCandidate"] is False


def test_phase5_mock_baseline_inputs_outputs_and_snapshot_exist():
    contract = load_json("delivery/phase5-mock-baseline.json")
    snapshot = contract["baselineSnapshot"]

    for entry in [*contract["inputs"], *contract["outputs"]]:
        assert entry.get("required") is True or entry.get("requiredForBaseline") is True
        assert (ROOT / entry["path"]).exists()
        assert not entry["path"].startswith(("http://", "https://"))

    assert snapshot["deliveryReady"] == 175
    assert snapshot["deliveryRequired"] == 175
    assert snapshot["missingRequired"] == 0
    assert snapshot["phase1CheckPassed"] == 20
    assert snapshot["phase1CheckTotal"] == 20
    assert snapshot["acceptancePassed"] == 14
    assert snapshot["acceptanceRequired"] == 14
    assert snapshot["safetyAssertionPassed"] == 6
    assert snapshot["safetyAssertionTotal"] == 6
    assert snapshot["frontendStaticRouteTotal"] == 31
    assert snapshot["defaultProvider"] == "mock"
    assert snapshot["generatedStatus"] == "WAITING_REVIEW"
    assert snapshot["mockOnly"] is True


def test_phase5_mock_baseline_freezes_llm_entry_gates():
    contract = load_json("delivery/phase5-mock-baseline.json")
    gates = {gate["id"]: gate for gate in contract["llmPocEntryGates"]}
    frozen = {item["id"]: item for item in contract["frozenCapabilities"]}

    assert {
        "explicit_opt_in_required",
        "default_provider_remains_mock",
        "api_keys_from_environment_only",
        "first_scope_lab_generate_from_source_only",
        "schema_validation_required",
        "generated_status_waiting_review",
        "audit_redaction_required",
        "cli_json_envelope_required",
        "auto_publish_disabled",
        "real_cloud_disabled",
        "real_sandbox_disabled",
        "real_mcp_server_disabled",
        "real_agent_disabled",
        "real_provider_shell_disabled",
        "real_provider_shell_no_sdk_import",
        "real_provider_shell_generation_disabled",
        "real_llm_poc_adapter_disabled",
        "real_llm_poc_adapter_no_sdk_import",
        "real_llm_poc_adapter_no_network_call",
        "real_llm_poc_adapter_no_generated_content",
        "real_llm_dry_run_plan_required",
        "real_llm_dry_run_plan_no_secret_presence_check",
        "real_llm_dry_run_plan_no_task_creation",
        "real_llm_approval_gate_required",
        "real_llm_approval_gate_no_real_call_authorization",
        "real_llm_approval_gate_no_secret_presence_check",
        "real_llm_sdk_task_blueprint_required",
        "real_llm_sdk_task_blueprint_no_implementation_allowed",
        "real_llm_sdk_task_blueprint_no_contract_change",
        "real_llm_sdk_task_blueprint_no_sdk_dependency",
        "real_provider_sdk_poc_required",
        "real_provider_sdk_poc_disabled",
        "real_provider_sdk_poc_no_sdk_import",
        "real_provider_sdk_poc_no_network_call",
        "real_provider_sdk_poc_no_secret_presence_check",
        "real_sdk_enablement_required",
        "real_sdk_enablement_no_implementation_allowed",
        "real_sdk_enablement_no_contract_change",
        "real_sdk_enablement_no_secret_presence_check",
        "real_sdk_enablement_no_network_call",
        "real_sdk_minimal_impl_required",
        "real_sdk_minimal_impl_disabled",
        "real_sdk_minimal_impl_no_sdk_import",
        "real_sdk_minimal_impl_no_network_call",
        "real_sdk_minimal_impl_no_secret_presence_check",
        "real_sdk_minimal_impl_no_task_creation",
        "real_sdk_dependency_env_gate_required",
        "real_sdk_dependency_env_gate_no_dependency_install",
        "real_sdk_dependency_env_gate_no_sdk_import",
        "real_sdk_dependency_env_gate_no_lockfile_change",
        "real_sdk_dependency_env_gate_no_secret_presence_check",
        "real_sdk_dependency_env_gate_no_network_call",
        "real_sdk_dependency_target_resolver_required",
        "real_sdk_dependency_target_resolver_no_live_dependency_file_read",
        "real_sdk_dependency_target_resolver_no_target_file_write",
        "real_sdk_dependency_target_resolver_no_patch_generation",
        "real_sdk_dependency_target_resolver_no_command_execution",
        "real_sdk_dependency_target_resolver_no_dependency_install",
        "real_sdk_dependency_target_resolver_no_secret_presence_check",
        "real_sdk_dependency_target_resolver_no_network_call",
        "real_sdk_dependency_target_resolver_no_real_llm_call",
        "real_sdk_dependency_readonly_snapshot_required",
        "real_sdk_dependency_readonly_snapshot_no_live_dependency_file_read",
        "real_sdk_dependency_readonly_snapshot_no_snapshot_content_capture",
        "real_sdk_dependency_readonly_snapshot_no_snapshot_file_write",
        "real_sdk_dependency_readonly_snapshot_no_snapshot_review_persistence",
        "real_sdk_dependency_readonly_snapshot_no_patch_generation",
        "real_sdk_dependency_readonly_snapshot_no_command_execution",
        "real_sdk_dependency_readonly_snapshot_no_dependency_install",
        "real_sdk_dependency_readonly_snapshot_no_secret_presence_check",
        "real_sdk_dependency_readonly_snapshot_no_network_call",
        "real_sdk_dependency_readonly_snapshot_no_real_llm_call",
        "real_sdk_dependency_content_read_plan_required",
        "real_sdk_dependency_content_read_plan_no_dependency_content_read",
        "real_sdk_dependency_content_read_plan_no_dependency_content_return",
        "real_sdk_dependency_content_read_plan_no_content_persistence",
        "real_sdk_dependency_content_read_plan_no_plan_artifact_write",
        "real_sdk_dependency_content_read_plan_no_content_snapshot_write",
        "real_sdk_dependency_content_read_plan_no_patch_generation",
        "real_sdk_dependency_content_read_plan_no_command_execution",
        "real_sdk_dependency_content_read_plan_no_dependency_install",
        "real_sdk_dependency_content_read_plan_no_secret_presence_check",
        "real_sdk_dependency_content_read_plan_no_network_call",
        "real_sdk_dependency_content_read_plan_no_real_llm_call",
        "real_sdk_dependency_content_read_final_confirmation_required",
        "real_sdk_dependency_content_read_final_confirmation_no_dependency_content_read",
        "real_sdk_dependency_content_read_final_confirmation_no_dependency_content_return",
        "real_sdk_dependency_content_read_final_confirmation_no_content_persistence",
        "real_sdk_dependency_content_read_final_confirmation_no_final_confirmation_artifact_write",
        "real_sdk_dependency_content_read_final_confirmation_no_content_read_execution_task_creation",
        "real_sdk_dependency_content_read_final_confirmation_no_content_read_execution_authorization",
        "real_sdk_dependency_content_read_final_confirmation_no_patch_generation",
        "real_sdk_dependency_content_read_final_confirmation_no_command_execution",
        "real_sdk_dependency_content_read_final_confirmation_no_dependency_install",
        "real_sdk_dependency_content_read_final_confirmation_no_secret_presence_check",
        "real_sdk_dependency_content_read_final_confirmation_no_network_call",
        "real_sdk_dependency_content_read_final_confirmation_no_real_llm_call",
        "real_sdk_dependency_content_read_readonly_execution_required",
        "real_sdk_dependency_content_read_readonly_execution_redacted_preview_only",
        "real_sdk_dependency_content_read_readonly_execution_no_raw_content_return",
        "real_sdk_dependency_content_read_readonly_execution_no_content_persistence",
        "real_sdk_dependency_content_read_readonly_execution_no_artifact_write",
        "real_sdk_dependency_content_read_readonly_execution_no_patch_generation",
        "real_sdk_dependency_content_read_readonly_execution_no_command_execution",
        "real_sdk_dependency_content_read_readonly_execution_no_dependency_install",
        "real_sdk_dependency_content_read_readonly_execution_no_secret_presence_check",
        "real_sdk_dependency_content_read_readonly_execution_no_network_call",
        "real_sdk_dependency_content_read_readonly_execution_no_real_llm_call",
        "real_sdk_dependency_install_change_proposal_required",
        "real_sdk_dependency_install_change_proposal_plan_only",
        "real_sdk_dependency_install_change_proposal_no_dependency_file_write",
        "real_sdk_dependency_install_change_proposal_no_patch_file_write",
        "real_sdk_dependency_install_change_proposal_no_patch_apply",
        "real_sdk_dependency_install_change_proposal_no_command_materialization",
        "real_sdk_dependency_install_change_proposal_no_command_execution",
        "real_sdk_dependency_install_change_proposal_no_dependency_install",
        "real_sdk_dependency_install_change_proposal_no_package_resolution",
        "real_sdk_dependency_install_change_proposal_no_secret_presence_check",
        "real_sdk_dependency_install_change_proposal_no_network_call",
        "real_sdk_dependency_install_change_proposal_no_real_llm_call",
        "real_sdk_dependency_install_execution_gate_required",
        "real_sdk_dependency_install_execution_gate_gate_only",
        "real_sdk_dependency_install_execution_gate_no_execution_authorization",
        "real_sdk_dependency_install_execution_gate_no_dependency_file_write",
        "real_sdk_dependency_install_execution_gate_no_patch_file_write",
        "real_sdk_dependency_install_execution_gate_no_patch_apply",
        "real_sdk_dependency_install_execution_gate_no_command_materialization",
        "real_sdk_dependency_install_execution_gate_no_command_execution",
        "real_sdk_dependency_install_execution_gate_no_dependency_install",
        "real_sdk_dependency_install_execution_gate_no_package_resolution",
        "real_sdk_dependency_install_execution_gate_no_secret_presence_check",
        "real_sdk_dependency_install_execution_gate_no_network_call",
        "real_sdk_dependency_install_execution_gate_no_real_llm_call",
    } <= set(gates)
    assert gates["generated_status_waiting_review"]["expected"] == "WAITING_REVIEW"
    assert gates["auto_publish_disabled"]["expected"] is False
    assert gates["real_cloud_disabled"]["expected"] is False
    assert gates["real_agent_disabled"]["expected"] is False
    assert gates["real_provider_sdk_poc_disabled"]["expected"] is True
    assert gates["real_provider_sdk_poc_no_sdk_import"]["expected"] is False
    assert gates["real_provider_sdk_poc_no_network_call"]["expected"] is False
    assert gates["real_provider_sdk_poc_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_enablement_required"]["expected"] is True
    assert gates["real_sdk_enablement_no_implementation_allowed"]["expected"] is False
    assert gates["real_sdk_enablement_no_contract_change"]["expected"] is False
    assert gates["real_sdk_enablement_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_enablement_no_network_call"]["expected"] is False
    assert gates["real_sdk_minimal_impl_required"]["expected"] is True
    assert gates["real_sdk_minimal_impl_disabled"]["expected"] is True
    assert gates["real_sdk_minimal_impl_no_sdk_import"]["expected"] is False
    assert gates["real_sdk_minimal_impl_no_network_call"]["expected"] is False
    assert gates["real_sdk_minimal_impl_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_minimal_impl_no_task_creation"]["expected"] is False
    assert gates["real_sdk_dependency_env_gate_required"]["expected"] is True
    assert gates["real_sdk_dependency_env_gate_no_dependency_install"]["expected"] is False
    assert gates["real_sdk_dependency_env_gate_no_sdk_import"]["expected"] is False
    assert gates["real_sdk_dependency_env_gate_no_lockfile_change"]["expected"] is False
    assert gates["real_sdk_dependency_env_gate_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_dependency_env_gate_no_network_call"]["expected"] is False
    assert gates["real_sdk_dependency_target_resolver_required"]["expected"] is True
    assert gates["real_sdk_dependency_target_resolver_no_live_dependency_file_read"]["expected"] is False
    assert gates["real_sdk_dependency_target_resolver_no_target_file_write"]["expected"] is False
    assert gates["real_sdk_dependency_target_resolver_no_patch_generation"]["expected"] is False
    assert gates["real_sdk_dependency_target_resolver_no_command_execution"]["expected"] is False
    assert gates["real_sdk_dependency_target_resolver_no_dependency_install"]["expected"] is False
    assert gates["real_sdk_dependency_target_resolver_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_dependency_target_resolver_no_network_call"]["expected"] is False
    assert gates["real_sdk_dependency_target_resolver_no_real_llm_call"]["expected"] is False
    assert gates["real_sdk_dependency_readonly_snapshot_required"]["expected"] is True
    assert gates["real_sdk_dependency_readonly_snapshot_no_live_dependency_file_read"]["expected"] is False
    assert gates["real_sdk_dependency_readonly_snapshot_no_snapshot_content_capture"]["expected"] is False
    assert gates["real_sdk_dependency_readonly_snapshot_no_snapshot_file_write"]["expected"] is False
    assert gates["real_sdk_dependency_readonly_snapshot_no_snapshot_review_persistence"]["expected"] is False
    assert gates["real_sdk_dependency_readonly_snapshot_no_patch_generation"]["expected"] is False
    assert gates["real_sdk_dependency_readonly_snapshot_no_command_execution"]["expected"] is False
    assert gates["real_sdk_dependency_readonly_snapshot_no_dependency_install"]["expected"] is False
    assert gates["real_sdk_dependency_readonly_snapshot_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_dependency_readonly_snapshot_no_network_call"]["expected"] is False
    assert gates["real_sdk_dependency_readonly_snapshot_no_real_llm_call"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_plan_required"]["expected"] is True
    assert gates["real_sdk_dependency_content_read_plan_no_dependency_content_read"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_plan_no_dependency_content_return"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_plan_no_content_persistence"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_plan_no_plan_artifact_write"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_plan_no_content_snapshot_write"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_plan_no_patch_generation"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_plan_no_command_execution"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_plan_no_dependency_install"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_plan_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_plan_no_network_call"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_plan_no_real_llm_call"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_required"]["expected"] is True
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_dependency_content_read"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_dependency_content_return"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_content_persistence"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_final_confirmation_artifact_write"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_content_read_execution_task_creation"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_content_read_execution_authorization"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_patch_generation"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_command_execution"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_dependency_install"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_network_call"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_final_confirmation_no_real_llm_call"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_readonly_execution_required"]["expected"] is True
    assert gates["real_sdk_dependency_content_read_readonly_execution_redacted_preview_only"]["expected"] is True
    assert gates["real_sdk_dependency_content_read_readonly_execution_no_raw_content_return"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_readonly_execution_no_content_persistence"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_readonly_execution_no_artifact_write"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_readonly_execution_no_patch_generation"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_readonly_execution_no_command_execution"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_readonly_execution_no_dependency_install"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_readonly_execution_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_readonly_execution_no_network_call"]["expected"] is False
    assert gates["real_sdk_dependency_content_read_readonly_execution_no_real_llm_call"]["expected"] is False
    assert gates["real_sdk_dependency_install_change_proposal_required"]["expected"] is True
    assert gates["real_sdk_dependency_install_change_proposal_plan_only"]["expected"] is True
    assert gates["real_sdk_dependency_install_change_proposal_no_dependency_file_write"]["expected"] is False
    assert gates["real_sdk_dependency_install_change_proposal_no_patch_file_write"]["expected"] is False
    assert gates["real_sdk_dependency_install_change_proposal_no_patch_apply"]["expected"] is False
    assert gates["real_sdk_dependency_install_change_proposal_no_command_materialization"]["expected"] is False
    assert gates["real_sdk_dependency_install_change_proposal_no_command_execution"]["expected"] is False
    assert gates["real_sdk_dependency_install_change_proposal_no_dependency_install"]["expected"] is False
    assert gates["real_sdk_dependency_install_change_proposal_no_package_resolution"]["expected"] is False
    assert gates["real_sdk_dependency_install_change_proposal_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_dependency_install_change_proposal_no_network_call"]["expected"] is False
    assert gates["real_sdk_dependency_install_change_proposal_no_real_llm_call"]["expected"] is False
    assert gates["real_sdk_dependency_install_execution_gate_required"]["expected"] is True
    assert gates["real_sdk_dependency_install_execution_gate_gate_only"]["expected"] is True
    assert gates["real_sdk_dependency_install_execution_gate_no_execution_authorization"]["expected"] is False
    assert gates["real_sdk_dependency_install_execution_gate_no_dependency_file_write"]["expected"] is False
    assert gates["real_sdk_dependency_install_execution_gate_no_patch_file_write"]["expected"] is False
    assert gates["real_sdk_dependency_install_execution_gate_no_patch_apply"]["expected"] is False
    assert gates["real_sdk_dependency_install_execution_gate_no_command_materialization"]["expected"] is False
    assert gates["real_sdk_dependency_install_execution_gate_no_command_execution"]["expected"] is False
    assert gates["real_sdk_dependency_install_execution_gate_no_dependency_install"]["expected"] is False
    assert gates["real_sdk_dependency_install_execution_gate_no_package_resolution"]["expected"] is False
    assert gates["real_sdk_dependency_install_execution_gate_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_dependency_install_execution_gate_no_network_call"]["expected"] is False
    assert gates["real_sdk_dependency_install_execution_gate_no_real_llm_call"]["expected"] is False
    assert gates["real_sdk_dependency_install_authorization_package_required"]["expected"] is True
    assert gates["real_sdk_dependency_install_authorization_package_package_only"]["expected"] is True
    assert gates["real_sdk_dependency_install_authorization_package_no_execution_authorization"]["expected"] is False
    assert gates["real_sdk_dependency_install_authorization_package_no_dependency_file_write"]["expected"] is False
    assert gates["real_sdk_dependency_install_authorization_package_no_patch_file_write"]["expected"] is False
    assert gates["real_sdk_dependency_install_authorization_package_no_patch_apply"]["expected"] is False
    assert gates["real_sdk_dependency_install_authorization_package_no_command_materialization"]["expected"] is False
    assert gates["real_sdk_dependency_install_authorization_package_no_command_execution"]["expected"] is False
    assert gates["real_sdk_dependency_install_authorization_package_no_dependency_install"]["expected"] is False
    assert gates["real_sdk_dependency_install_authorization_package_no_package_resolution"]["expected"] is False
    assert gates["real_sdk_dependency_install_authorization_package_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_dependency_install_authorization_package_no_network_call"]["expected"] is False
    assert gates["real_sdk_dependency_install_authorization_package_no_real_llm_call"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_required"]["expected"] is True
    assert gates["real_sdk_dependency_install_executor_disabled_executor_only"]["expected"] is True
    assert gates["real_sdk_dependency_install_executor_disabled_no_execution_authorization"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_executor_dispatch"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_executor_start"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_executor_run_creation"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_dependency_file_write"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_patch_file_write"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_patch_apply"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_command_materialization"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_command_execution"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_dependency_install"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_package_resolution"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_secret_presence_check"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_network_call"]["expected"] is False
    assert gates["real_sdk_dependency_install_executor_disabled_no_real_llm_call"]["expected"] is False
    assert all(gate["required"] is True for gate in gates.values())
    assert "provider_adapter_mock_only_ready" in frozen
    assert "real_provider_gate" in frozen
    assert "real_provider_shell" in frozen
    assert "real_llm_poc_adapter" in frozen
    assert "real_llm_dry_run_plan" in frozen
    assert "real_llm_approval_gate" in frozen
    assert "real_llm_sdk_task_blueprint" in frozen
    assert "real_provider_sdk_poc" in frozen
    assert "real_sdk_enablement" in frozen
    assert "real_sdk_minimal_impl" in frozen
    assert "real_sdk_dependency_env_gate" in frozen
    assert "real_sdk_dependency_apply_gate" in frozen
    assert "real_sdk_dependency_target_resolver" in frozen
    assert "real_sdk_dependency_readonly_snapshot" in frozen
    assert "real_sdk_dependency_content_read_plan" in frozen
    assert "real_sdk_dependency_content_read_final_confirmation" in frozen
    assert "real_sdk_dependency_content_read_readonly_execution" in frozen
    assert "real_sdk_dependency_install_change_proposal" in frozen
    assert "real_sdk_dependency_install_execution_gate" in frozen
    assert "real_sdk_dependency_install_authorization_package" in frozen
    assert "real_sdk_dependency_install_executor_disabled" in frozen
    assert "review_gate_ready" in frozen
    assert "final_signoff_ready" in frozen
    assert all(item["status"] == "READY" for item in frozen.values())


def test_phase5_mock_baseline_commands_are_allowlisted():
    contract = load_json("delivery/phase5-mock-baseline.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_real_provider_gate" in contract["recommendedCommandIds"]
    assert "test_real_provider_shell" in contract["recommendedCommandIds"]
    assert "test_real_llm_poc_adapter" in contract["recommendedCommandIds"]
    assert "test_real_llm_dry_run_plan" in contract["recommendedCommandIds"]
    assert "test_real_llm_approval_gate" in contract["recommendedCommandIds"]
    assert "test_real_llm_sdk_task_blueprint" in contract["recommendedCommandIds"]
    assert "test_real_provider_sdk_poc" in contract["recommendedCommandIds"]
    assert "test_real_sdk_enablement" in contract["recommendedCommandIds"]
    assert "test_real_sdk_minimal_impl" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_env_gate" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_apply_gate" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_target_resolver" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_readonly_snapshot" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_plan" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_final_confirmation" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_readonly_execution" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_change_proposal" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_execution_gate" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_authorization_package" in contract["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_executor_disabled" in contract["recommendedCommandIds"]
    assert "test_phase5_mock_baseline" in contract["recommendedCommandIds"]

    for command_id in contract["recommendedCommandIds"]:
        command = allowed[command_id]
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
        assert "docker run" not in command["command"]
        assert "kubectl " not in command["command"]
        assert "aws " not in command["command"]
        assert "gcloud " not in command["command"]


def test_phase5_mock_baseline_is_registered_in_delivery_and_signoff():
    delivery_contract = load_json("config/delivery-package.contract.json")
    delivery_index = load_json("delivery/phase1-delivery-index.json")
    final_signoff = load_json("delivery/final-signoff.json")
    operations_manual = load_json("delivery/operations-manual.json")
    handoff = load_json("delivery/phase1-handoff.json")
    skill_pack = load_json("skills/operations-skill-pack.contract.json")
    runbook = load_json("scripts/phase1-demo.runbook.json")
    manifest = load_json("scripts/manifest.json")

    deliverable_ids = {item["id"] for item in delivery_contract["deliverables"]}
    entry_ids = {item["id"] for item in delivery_index["entryPoints"]}
    final_input_ids = {item["id"] for item in final_signoff["inputs"]}
    operations_input_ids = {item["id"] for item in operations_manual["inputs"]}
    handoff_input_ids = {item["id"] for item in handoff["inputs"]}
    skill_input_ids = {item["id"] for item in skill_pack["inputs"]}
    runbook_input_ids = {item["id"] for item in runbook["inputs"]}
    command_ids = {item["id"] for item in manifest["allowedCommands"]}

    assert "phase5_mock_baseline_md" in deliverable_ids
    assert "phase5_mock_baseline_contract" in deliverable_ids
    assert "real_provider_shell" in deliverable_ids
    assert "real_provider_shell_contract" in deliverable_ids
    assert "real_llm_poc_adapter" in deliverable_ids
    assert "real_llm_poc_adapter_contract" in deliverable_ids
    assert "real_llm_dry_run_plan" in deliverable_ids
    assert "real_llm_dry_run_plan_contract" in deliverable_ids
    assert "real_llm_approval_gate" in deliverable_ids
    assert "real_llm_approval_gate_contract" in deliverable_ids
    assert "real_llm_sdk_task_blueprint" in deliverable_ids
    assert "real_llm_sdk_task_blueprint_contract" in deliverable_ids
    assert "real_provider_sdk_poc" in deliverable_ids
    assert "real_provider_sdk_poc_contract" in deliverable_ids
    assert "real_sdk_enablement" in deliverable_ids
    assert "real_sdk_enablement_contract" in deliverable_ids
    assert "real_sdk_minimal_impl" in deliverable_ids
    assert "real_sdk_minimal_impl_contract" in deliverable_ids
    assert "real_sdk_dependency_env_gate" in deliverable_ids
    assert "real_sdk_dependency_env_gate_contract" in deliverable_ids
    assert "real_sdk_dependency_apply_gate" in deliverable_ids
    assert "real_sdk_dependency_apply_gate_contract" in deliverable_ids
    assert "real_sdk_dependency_target_resolver" in deliverable_ids
    assert "real_sdk_dependency_target_resolver_contract" in deliverable_ids
    assert "real_sdk_dependency_readonly_snapshot" in deliverable_ids
    assert "real_sdk_dependency_readonly_snapshot_contract" in deliverable_ids
    assert "real_sdk_dependency_content_read_plan" in deliverable_ids
    assert "real_sdk_dependency_content_read_plan_contract" in deliverable_ids
    assert "real_sdk_dependency_content_read_final_confirmation" in deliverable_ids
    assert "real_sdk_dependency_content_read_final_confirmation_contract" in deliverable_ids
    assert "real_sdk_dependency_content_read_readonly_execution" in deliverable_ids
    assert "real_sdk_dependency_content_read_readonly_execution_contract" in deliverable_ids
    assert "real_sdk_dependency_install_change_proposal" in deliverable_ids
    assert "real_sdk_dependency_install_change_proposal_contract" in deliverable_ids
    assert "real_sdk_dependency_install_execution_gate" in deliverable_ids
    assert "real_sdk_dependency_install_execution_gate_contract" in deliverable_ids
    assert "real_sdk_dependency_install_authorization_package" in deliverable_ids
    assert "real_sdk_dependency_install_authorization_package_contract" in deliverable_ids
    assert "real_sdk_dependency_install_executor_disabled" in deliverable_ids
    assert "real_sdk_dependency_install_executor_disabled_contract" in deliverable_ids
    assert "phase5_mock_baseline" in entry_ids
    assert "phase5_mock_baseline_contract" in entry_ids
    assert "phase5_mock_baseline" in final_input_ids
    assert "phase5_mock_baseline_contract" in final_input_ids
    assert "phase5_mock_baseline" in operations_input_ids
    assert "phase5_mock_baseline_contract" in operations_input_ids
    assert "phase5_mock_baseline" in handoff_input_ids
    assert "phase5_mock_baseline_contract" in handoff_input_ids
    assert "phase5_mock_baseline" in skill_input_ids
    assert "phase5_mock_baseline" in runbook_input_ids
    assert "test_phase5_mock_baseline" in command_ids
    assert "test_real_provider_shell" in command_ids
    assert "test_real_llm_poc_adapter" in command_ids
    assert "test_real_llm_dry_run_plan" in command_ids
    assert "test_real_llm_approval_gate" in command_ids
    assert "test_real_llm_sdk_task_blueprint" in command_ids
    assert "test_real_provider_sdk_poc" in command_ids
    assert "test_real_sdk_enablement" in command_ids
    assert "test_real_sdk_minimal_impl" in command_ids
    assert "test_real_sdk_dependency_env_gate" in command_ids
    assert "test_real_sdk_dependency_apply_gate" in command_ids
    assert "test_real_sdk_dependency_target_resolver" in command_ids
    assert "test_real_sdk_dependency_readonly_snapshot" in command_ids
    assert "test_real_sdk_dependency_content_read_plan" in command_ids
    assert "test_real_sdk_dependency_content_read_final_confirmation" in command_ids
    assert "test_real_sdk_dependency_content_read_readonly_execution" in command_ids
    assert "test_real_sdk_dependency_install_change_proposal" in command_ids
    assert "test_real_sdk_dependency_install_execution_gate" in command_ids
    assert "test_real_sdk_dependency_install_authorization_package" in command_ids
    assert "test_real_sdk_dependency_install_executor_disabled" in command_ids
    assert "test_real_provider_shell" in final_signoff["recommendedCommandIds"]
    assert "test_real_provider_shell" in operations_manual["recommendedCommandIds"]
    assert "test_real_provider_shell" in delivery_index["recommendedCommandIds"]
    assert "test_real_llm_poc_adapter" in final_signoff["recommendedCommandIds"]
    assert "test_real_llm_poc_adapter" in operations_manual["recommendedCommandIds"]
    assert "test_real_llm_poc_adapter" in delivery_index["recommendedCommandIds"]
    assert "test_real_llm_dry_run_plan" in final_signoff["recommendedCommandIds"]
    assert "test_real_llm_dry_run_plan" in operations_manual["recommendedCommandIds"]
    assert "test_real_llm_dry_run_plan" in delivery_index["recommendedCommandIds"]
    assert "test_real_llm_approval_gate" in final_signoff["recommendedCommandIds"]
    assert "test_real_llm_approval_gate" in operations_manual["recommendedCommandIds"]
    assert "test_real_llm_approval_gate" in delivery_index["recommendedCommandIds"]
    assert "test_real_llm_sdk_task_blueprint" in final_signoff["recommendedCommandIds"]
    assert "test_real_llm_sdk_task_blueprint" in operations_manual["recommendedCommandIds"]
    assert "test_real_llm_sdk_task_blueprint" in delivery_index["recommendedCommandIds"]
    assert "test_real_provider_sdk_poc" in final_signoff["recommendedCommandIds"]
    assert "test_real_provider_sdk_poc" in operations_manual["recommendedCommandIds"]
    assert "test_real_provider_sdk_poc" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_enablement" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_enablement" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_enablement" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_minimal_impl" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_minimal_impl" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_minimal_impl" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_dependency_env_gate" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_env_gate" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_dependency_env_gate" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_dependency_apply_gate" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_apply_gate" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_dependency_apply_gate" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_dependency_target_resolver" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_target_resolver" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_dependency_target_resolver" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_dependency_readonly_snapshot" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_readonly_snapshot" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_dependency_readonly_snapshot" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_plan" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_plan" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_plan" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_final_confirmation" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_final_confirmation" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_final_confirmation" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_readonly_execution" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_readonly_execution" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_dependency_content_read_readonly_execution" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_change_proposal" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_change_proposal" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_change_proposal" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_execution_gate" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_execution_gate" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_execution_gate" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_authorization_package" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_authorization_package" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_authorization_package" in delivery_index["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_executor_disabled" in final_signoff["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_executor_disabled" in operations_manual["recommendedCommandIds"]
    assert "test_real_sdk_dependency_install_executor_disabled" in delivery_index["recommendedCommandIds"]
    assert "test_phase5_mock_baseline" in final_signoff["recommendedCommandIds"]
    assert "test_phase5_mock_baseline" in operations_manual["recommendedCommandIds"]
    assert "test_phase5_mock_baseline" in delivery_index["recommendedCommandIds"]

    core = next(item for item in delivery_contract["acceptanceChecklist"] if item["id"] == "core_deliverables_present")
    assert "phase5_mock_baseline_md" in core["source"]["ids"]
    assert "phase5_mock_baseline_contract" in core["source"]["ids"]
    assert "real_provider_shell" in core["source"]["ids"]
    assert "real_provider_shell_contract" in core["source"]["ids"]
    assert "real_llm_poc_adapter" in core["source"]["ids"]
    assert "real_llm_poc_adapter_contract" in core["source"]["ids"]
    assert "real_llm_dry_run_plan" in core["source"]["ids"]
    assert "real_llm_dry_run_plan_contract" in core["source"]["ids"]
    assert "real_llm_approval_gate" in core["source"]["ids"]
    assert "real_llm_approval_gate_contract" in core["source"]["ids"]
    assert "real_llm_sdk_task_blueprint" in core["source"]["ids"]
    assert "real_llm_sdk_task_blueprint_contract" in core["source"]["ids"]
    assert "real_provider_sdk_poc" in core["source"]["ids"]
    assert "real_provider_sdk_poc_contract" in core["source"]["ids"]
    assert "real_sdk_enablement" in core["source"]["ids"]
    assert "real_sdk_enablement_contract" in core["source"]["ids"]
    assert "real_sdk_minimal_impl" in core["source"]["ids"]
    assert "real_sdk_minimal_impl_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_env_gate" in core["source"]["ids"]
    assert "real_sdk_dependency_env_gate_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_apply_gate" in core["source"]["ids"]
    assert "real_sdk_dependency_apply_gate_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_target_resolver" in core["source"]["ids"]
    assert "real_sdk_dependency_target_resolver_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_readonly_snapshot" in core["source"]["ids"]
    assert "real_sdk_dependency_readonly_snapshot_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_content_read_plan" in core["source"]["ids"]
    assert "real_sdk_dependency_content_read_plan_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_content_read_final_confirmation" in core["source"]["ids"]
    assert "real_sdk_dependency_content_read_final_confirmation_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_content_read_readonly_execution" in core["source"]["ids"]
    assert "real_sdk_dependency_content_read_readonly_execution_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_install_change_proposal" in core["source"]["ids"]
    assert "real_sdk_dependency_install_change_proposal_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_install_execution_gate" in core["source"]["ids"]
    assert "real_sdk_dependency_install_execution_gate_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_install_authorization_package" in core["source"]["ids"]
    assert "real_sdk_dependency_install_authorization_package_contract" in core["source"]["ids"]
    assert "real_sdk_dependency_install_executor_disabled" in core["source"]["ids"]
    assert "real_sdk_dependency_install_executor_disabled_contract" in core["source"]["ids"]
    assert "python -m pytest tests/test_real_provider_shell.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_llm_poc_adapter.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_llm_dry_run_plan.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_llm_approval_gate.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_llm_sdk_task_blueprint.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_provider_sdk_poc.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_enablement.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_minimal_impl.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_env_gate.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_apply_gate.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_target_resolver.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_readonly_snapshot.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_content_read_plan.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_content_read_final_confirmation.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_content_read_readonly_execution.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_install_change_proposal.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_install_execution_gate.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_install_authorization_package.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_install_executor_disabled.py" in delivery_contract["recommendedCommands"]
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in delivery_contract["recommendedCommands"]


def test_phase5_mock_baseline_markdown_documents_usage_and_limits():
    content = (ROOT / "delivery/PHASE5_MOCK_BASELINE.md").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## 收口基线", "## LLM 准入门禁", "## 命令示例", "## 测试方式", "## 限制说明"]:
        assert heading in content
    assert "175/175" in content
    assert "WAITING_REVIEW" in content
    assert "默认 Provider 仍为 `mock`" in content
    assert "API Key 只能来自环境变量" in content
    assert "lab generate-from-source" in content
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in content
    assert "python -m pytest tests/test_real_llm_poc_adapter.py" in content
    assert "python -m pytest tests/test_real_llm_dry_run_plan.py" in content
    assert "python -m pytest tests/test_real_llm_approval_gate.py" in content
    assert "python -m pytest tests/test_real_llm_sdk_task_blueprint.py" in content
    assert "python -m pytest tests/test_real_provider_sdk_poc.py" in content
    assert "python -m pytest tests/test_real_sdk_enablement.py" in content
    assert "python -m pytest tests/test_real_sdk_minimal_impl.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_env_gate.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_apply_gate.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_target_resolver.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_readonly_snapshot.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_content_read_plan.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_content_read_final_confirmation.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_content_read_readonly_execution.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_install_change_proposal.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_install_execution_gate.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_install_authorization_package.py" in content
    assert "python -m pytest tests/test_real_sdk_dependency_install_executor_disabled.py" in content
    assert "install change proposal" in content
    assert "install execution gate" in content
    assert "install authorization package" in content
    assert "install executor disabled" in content
    assert "不接入真实大模型" in content
    assert "不启用真实 Provider" in content
    assert "不读取或输出真实密钥" in content
