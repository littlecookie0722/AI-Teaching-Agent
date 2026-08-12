import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_contract():
    with (ROOT / "config/delivery-package.contract.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def test_delivery_package_contract_is_phase1_mock_only():
    contract = load_contract()

    assert contract["phase"] == "Phase 1"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["rules"]["realProvidersMustStayDisabled"] is True
    assert contract["rules"]["generatedPackageMustStayLocal"] is True
    assert contract["reportCommand"] == (
        "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json "
        "--output examples/output/phase1-acceptance-report.md"
    )
    assert contract["defaultReportPath"] == "examples/output/phase1-acceptance-report.md"


def test_delivery_package_required_sections_are_declared():
    contract = load_contract()
    sections = set(contract["packageSchema"]["requiredSections"])

    for section in [
        "deliveryContract",
        "deliveryManifest",
        "dslManifest",
        "workflowReport",
        "phase1Check",
        "acceptanceChecklist",
        "acceptanceSummary",
        "safetyAssertions",
        "securityLimits",
        "recommendedCommands",
    ]:
        assert section in sections


def test_delivery_package_deliverable_ids_are_unique_and_exist():
    contract = load_contract()
    ids = [deliverable["id"] for deliverable in contract["deliverables"]]

    assert len(ids) == len(set(ids))
    assert "delivery_index_readme" in ids
    assert "delivery_index_contract" in ids
    assert "delivery_faq_md" in ids
    assert "delivery_faq_contract" in ids
    assert "delivery_handoff_md" in ids
    assert "delivery_handoff_contract" in ids
    assert "demo_script_checklist_md" in ids
    assert "demo_script_checklist_contract" in ids
    assert "phase2_readiness_md" in ids
    assert "phase2_readiness_contract" in ids
    assert "phase2_provider_plan_md" in ids
    assert "phase2_provider_plan_contract" in ids
    assert "provider_adapter" in ids
    assert "real_provider_gate" in ids
    assert "real_provider_gate_contract" in ids
    assert "real_provider_shell" in ids
    assert "real_provider_shell_contract" in ids
    assert "provider_runtime_guard" in ids
    assert "provider_runtime_guard_contract" in ids
    assert "real_llm_poc_adapter" in ids
    assert "real_llm_poc_adapter_contract" in ids
    assert "real_llm_dry_run_plan" in ids
    assert "real_llm_dry_run_plan_contract" in ids
    assert "real_llm_approval_gate" in ids
    assert "real_llm_approval_gate_contract" in ids
    assert "real_llm_sdk_task_blueprint" in ids
    assert "real_llm_sdk_task_blueprint_contract" in ids
    assert "real_provider_sdk_poc" in ids
    assert "real_provider_sdk_poc_contract" in ids
    assert "real_sdk_enablement" in ids
    assert "real_sdk_enablement_contract" in ids
    assert "real_sdk_minimal_impl" in ids
    assert "real_sdk_minimal_impl_contract" in ids
    assert "real_sdk_dependency_env_gate" in ids
    assert "real_sdk_dependency_env_gate_contract" in ids
    assert "provider_adapter_contract" in ids
    assert "provider_adapter_errors_contract" in ids
    assert "provider_call_audit_model" in ids
    assert "provider_audit_contract" in ids
    assert "provider_audit_workflow_contract" in ids
    assert "provider_adapter_workflow_helper" in ids
    assert "mcp_mock_tools" in ids
    assert "mcp_tool_call_audit_model" in ids
    assert "mcp_tool_call_audit_contract" in ids
    assert "high_risk_mcp_safety_matrix" in ids
    assert "high_risk_mcp_handoff_md" in ids
    assert "high_risk_mcp_handoff_contract" in ids
    assert "final_signoff_md" in ids
    assert "final_signoff_contract" in ids
    assert "operations_manual_md" in ids
    assert "operations_manual_contract" in ids
    assert "operations_skill_pack_md" in ids
    assert "operations_skill_pack_contract" in ids
    assert "standalone_agent_delivery_md" in ids
    assert "standalone_agent_delivery_contract" in ids
    assert "access_entrypoints_md" in ids
    assert "access_entrypoints_contract" in ids
    assert "phase5_mock_baseline_md" in ids
    assert "phase5_mock_baseline_contract" in ids
    assert "mcp_mock_tools_tests" in ids
    assert "review_detail_example" in ids
    assert "review_batch_model" in ids
    assert "frontend_console_prototype" in ids
    assert "frontend_dashboard_prototype" in ids
    assert "frontend_audit_observability_prototype" in ids
    assert "frontend_audit_detail_prototype" in ids
    assert "frontend_audit_incident_review_prototype" in ids
    assert "frontend_operations_launchpad_prototype" in ids
    assert "frontend_access_entrypoints_prototype" in ids
    assert "frontend_operations_runbook_prototype" in ids
    assert "frontend_operations_acceptance_prototype" in ids
    assert "frontend_operations_demo_map_prototype" in ids
    assert "frontend_operations_presenter_prototype" in ids
    assert "frontend_operations_demo_script_prototype" in ids
    assert "frontend_review_center_prototype" in ids
    assert "frontend_ai_task_center_prototype" in ids
    assert "frontend_labs_prototype" in ids
    assert "frontend_lab_generate_prototype" in ids
    assert "frontend_lab_review_prototype" in ids
    assert "frontend_exams_prototype" in ids
    assert "frontend_exam_review_prototype" in ids
    assert "frontend_exam_generate_prototype" in ids
    assert "frontend_ppt_management_prototype" in ids
    assert "frontend_ppt_review_prototype" in ids
    assert "frontend_delivery_prototype" in ids
    assert "frontend_environment_management_prototype" in ids
    assert "frontend_skills_management_prototype" in ids
    assert "frontend_provider_settings_prototype" in ids
    assert "frontend_grading_management_prototype" in ids
    assert "frontend_grading_review_prototype" in ids
    assert "frontend_grading_report_prototype" in ids
    assert "scripts_phase1_demo_runbook_json" in ids
    assert "scripts_phase1_demo_runbook_md" in ids
    for deliverable in contract["deliverables"]:
        assert deliverable["required"] is True
        assert (ROOT / deliverable["path"]).exists()


def test_delivery_package_acceptance_checklist_is_required_and_unique():
    contract = load_contract()
    ids = [item["id"] for item in contract["acceptanceChecklist"]]

    assert len(ids) == len(set(ids))
    assert "phase1_demo_runbook_present" in ids
    assert "demo_script_checklist_present" in ids
    assert {item["source"]["type"] for item in contract["acceptanceChecklist"]} >= {
        "phase1Check",
        "workflowReport",
        "deliverables",
    }
    assert all(item["required"] is True for item in contract["acceptanceChecklist"])


def test_delivery_package_safety_assertions_disable_real_execution():
    contract = load_contract()
    assertions = {assertion["id"]: assertion for assertion in contract["safetyAssertions"]}

    for assertion_id in [
        "real_llm_disabled",
        "real_cloud_disabled",
        "real_sandbox_disabled",
        "auto_publish_disabled",
        "contestant_code_execution_disabled",
        "unknown_shell_execution_disabled",
    ]:
        assert assertions[assertion_id]["expected"] is False
        assert assertions[assertion_id]["actual"] is False


def test_delivery_package_recommended_commands_are_local_mock_commands():
    contract = load_contract()

    assert "python -m pytest tests/test_real_provider_gate.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_provider_shell.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_llm_poc_adapter.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_llm_dry_run_plan.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_llm_approval_gate.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_llm_sdk_task_blueprint.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_provider_sdk_poc.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_enablement.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_minimal_impl.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_real_sdk_dependency_env_gate.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_provider_adapter_workflow.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_high_risk_mcp_safety_contract.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_high_risk_mcp_handoff.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_final_signoff.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_operations_manual.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_operations_skill_pack.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_standalone_agent_delivery.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_access_entrypoints.py" in contract["recommendedCommands"]
    assert "python -m pytest tests/test_phase5_mock_baseline.py" in contract["recommendedCommands"]
    for command in contract["recommendedCommands"]:
        assert command.startswith("python ")
        assert "aws " not in command
        assert "gcloud " not in command
        assert "kubectl " not in command
        assert "docker run" not in command
