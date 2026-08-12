import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_manifest():
    with (ROOT / "mcp-server/tools.manifest.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_tool_call_audit_contract():
    with (ROOT / "mcp-server/tool-call-audit.contract.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_server_contract():
    with (ROOT / "mcp-server/server.contract.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_mcp_manifest_has_phase1_mock_contract():
    manifest = load_manifest()

    assert manifest["phase"] == "Phase 1"
    assert manifest["mode"] == "MOCK_ONLY"
    assert manifest["protocol"] == "mcp-contract-draft"
    assert manifest["tools"]


def test_mcp_manifest_tool_names_are_unique():
    manifest = load_manifest()
    names = [tool["name"] for tool in manifest["tools"]]

    assert len(names) == len(set(names))


def test_mcp_manifest_tools_define_inputs_and_json_outputs():
    manifest = load_manifest()
    required_output = {"success", "code", "message", "traceId"}

    assert set(manifest["outputSchema"]["required"]) == required_output
    for tool in manifest["tools"]:
        assert tool["inputSchema"]["type"] == "object"
        assert tool["inputSchema"].get("additionalProperties") is False
        assert set(tool["inputSchema"].get("required", [])) <= set(tool["inputSchema"]["properties"])
        assert tool["backend"]["method"] in {"GET", "POST"}
        assert tool["backend"]["path"].startswith("/api/")
        assert tool["cli"].startswith("python lab_cli.py ")


def test_mcp_manifest_generation_tools_require_review():
    manifest = load_manifest()
    tools = {tool["name"]: tool for tool in manifest["tools"]}

    for name in [
        "workflow_demo",
        "generate_lab_from_source",
        "generate_exam_from_lab",
        "generate_ppt",
        "mock_provider_generate",
        "publish_lab",
        "publish_exam",
        "destroy_environment",
    ]:
        assert tools[name]["reviewRequired"] is True
        assert tools[name]["safety"]["defaultGeneratedStatus"] == "WAITING_REVIEW"
        assert tools[name]["safety"]["publishBlockedUntilApproved"] is True


def test_mcp_manifest_blocks_real_execution_and_cloud_resources():
    manifest = load_manifest()
    tools = {tool["name"]: tool for tool in manifest["tools"]}

    assert tools["analyze_material"]["reviewRequired"] is False
    assert tools["analyze_material"]["safety"]["realLlmCalled"] is False
    assert tools["analyze_material"]["safety"]["remoteContentFetched"] is False
    assert tools["analyze_material"]["safety"]["unknownShellExecuted"] is False
    assert tools["analyze_material"]["safety"]["sandboxExecuted"] is False
    assert tools["run_grading"]["safety"]["sandboxExecuted"] is False
    assert tools["run_grading"]["safety"]["contestantCodeExecuted"] is False
    assert tools["list_review_audit_events"]["safety"]["realPublish"] is False
    assert tools["get_review_task_summary"]["safety"]["batchApproveAllowed"] is False
    assert tools["get_review_task_summary"]["safety"]["batchRejectAllowed"] is False
    assert tools["get_review_task_summary"]["safety"]["batchPublishAllowed"] is False
    assert tools["get_review_task_summary"]["safety"]["realPublish"] is False
    assert tools["get_real_llm_runtime_config"]["backend"]["path"] == "/api/providers/real-llm-runtime-config"
    assert tools["get_real_llm_runtime_config"]["reviewRequired"] is False
    assert tools["get_real_llm_runtime_config"]["safety"]["readOnly"] is True
    assert tools["get_real_llm_runtime_config"]["safety"]["requestSent"] is False
    assert tools["get_real_llm_runtime_config"]["safety"]["realLlmCalled"] is False
    assert tools["get_real_llm_runtime_config"]["safety"]["networkAccess"] is False
    assert tools["get_real_llm_runtime_config"]["safety"]["secretValueReturned"] is False
    assert tools["get_real_llm_runtime_config"]["outputContract"]["dataPath"] == "data.realLlmRuntimeConfig"
    assert tools["get_real_llm_runtime_config"]["outputContract"]["component"] == "RealLlmRuntimeConfigSummary"
    assert tools["get_real_dsl_review_preview"]["backend"]["path"] == "/api/review/real-dsl-preview"
    assert tools["get_real_dsl_review_preview"]["reviewRequired"] is False
    assert tools["get_real_dsl_review_preview"]["safety"]["readOnly"] is True
    assert tools["get_real_dsl_review_preview"]["safety"]["newLlmRequestSent"] is False
    assert tools["get_real_dsl_review_preview"]["safety"]["secretsRead"] is False
    assert tools["get_real_dsl_review_preview"]["safety"]["networkAccess"] is False
    assert tools["get_real_dsl_review_preview"]["safety"]["answerVisibleToCandidate"] is False
    assert tools["get_real_dsl_review_preview"]["safety"]["gradingRefVisibleToCandidate"] is False
    assert tools["get_real_dsl_review_preview"]["safety"]["teacherOnlyGradingRefVisibleInReview"] is True
    assert tools["get_real_dsl_review_preview"]["safety"]["autoApproveAllowed"] is False
    assert tools["get_real_dsl_review_preview"]["safety"]["realPublishAllowed"] is False
    assert tools["get_real_dsl_review_preview"]["outputContract"]["dataPath"] == "data.realDslReviewPreview"
    assert tools["get_real_dsl_review_preview"]["outputContract"]["component"] == "RealDslReviewPreview"
    assert "examQuestionTotal" in tools["get_real_dsl_review_preview"]["outputContract"]["summaryFields"]
    assert "qualitySignals" in tools["get_real_dsl_review_preview"]["outputContract"]["requiredFields"]
    assert "reviewIssues" in tools["get_real_dsl_review_preview"]["outputContract"]["requiredFields"]
    assert "revisionSuggestions" in tools["get_real_dsl_review_preview"]["outputContract"]["requiredFields"]
    assert "qualityIssueTotal" in tools["get_real_dsl_review_preview"]["outputContract"]["summaryFields"]
    assert tools["create_real_dsl_revision_draft"]["backend"]["path"] == "/api/review/real-dsl-revision"
    assert tools["create_real_dsl_revision_draft"]["inputSchema"]["required"] == ["kind", "reviewer", "comment"]
    assert tools["create_real_dsl_revision_draft"]["inputSchema"]["properties"]["providerMode"]["enum"] == ["local", "real-llm"]
    assert tools["create_real_dsl_revision_draft"]["inputSchema"]["properties"]["explicitRealCallOptIn"]["type"] == "boolean"
    assert tools["create_real_dsl_revision_draft"]["inputSchema"]["properties"]["confirmWaitingReview"]["type"] == "boolean"
    assert tools["create_real_dsl_revision_draft"]["inputSchema"]["properties"]["confirmNoAutoPublish"]["type"] == "boolean"
    assert tools["create_real_dsl_revision_draft"]["safety"]["defaultGeneratedStatus"] == "WAITING_REVIEW"
    assert tools["create_real_dsl_revision_draft"]["safety"]["newLlmRequestSent"] is False
    assert tools["create_real_dsl_revision_draft"]["safety"]["realLlmCalled"] is False
    assert tools["create_real_dsl_revision_draft"]["safety"]["secretsRead"] is False
    assert tools["create_real_dsl_revision_draft"]["safety"]["networkAccess"] is False
    assert tools["create_real_dsl_revision_draft"]["safety"]["artifactCreated"] is True
    assert tools["create_real_dsl_revision_draft"]["safety"]["autoApproveAllowed"] is False
    assert tools["create_real_dsl_revision_draft"]["safety"]["autoPublishAllowed"] is False
    assert tools["create_real_dsl_revision_draft"]["safety"]["realPublishAllowed"] is False
    assert tools["create_real_dsl_revision_draft"]["outputContract"]["dataPath"] == "data.realDslRevisionDraft"
    assert tools["create_real_dsl_revision_draft"]["outputContract"]["component"] == "RealDslRevisionDraft"
    assert tools["create_real_dsl_revision_draft"]["outputContract"]["newTaskStatus"] == "WAITING_REVIEW"
    assert tools["create_real_dsl_revision_draft"]["outputContract"]["realLlmCalledWhenProviderModeRealLlm"] is True
    assert tools["create_real_dsl_revision_draft"]["outputContract"]["networkAccessWhenProviderModeRealLlm"] is True
    assert tools["create_real_dsl_revision_draft"]["outputContract"]["autoPublishAllowed"] is False
    assert tools["create_real_dsl_revision_batch_from_preview"]["backend"]["path"] == "/api/review/real-dsl-revision-batch"
    assert tools["create_real_dsl_revision_batch_from_preview"]["inputSchema"]["required"] == ["reviewer"]
    assert tools["create_real_dsl_revision_batch_from_preview"]["safety"]["defaultGeneratedStatus"] == "WAITING_REVIEW"
    assert tools["create_real_dsl_revision_batch_from_preview"]["safety"]["newLlmRequestSent"] is False
    assert tools["create_real_dsl_revision_batch_from_preview"]["safety"]["realLlmCalled"] is False
    assert tools["create_real_dsl_revision_batch_from_preview"]["safety"]["realPublishAllowed"] is False
    assert tools["create_real_dsl_revision_batch_from_preview"]["outputContract"]["dataPath"] == "data.realDslRevisionBatch"
    assert tools["create_real_dsl_revision_batch_from_preview"]["outputContract"]["component"] == "RealDslRevisionBatch"
    assert tools["create_real_dsl_revision_batch_from_preview"]["outputContract"]["newTaskStatus"] == "WAITING_REVIEW"
    assert tools["create_real_dsl_revision_batch_from_preview"]["outputContract"]["autoPublishAllowed"] is False
    assert tools["get_real_dsl_revision_diff_preview"]["backend"]["method"] == "GET"
    assert tools["get_real_dsl_revision_diff_preview"]["backend"]["path"] == "/api/review/real-dsl-revision-diff-preview"
    assert tools["get_real_dsl_revision_diff_preview"]["inputSchema"]["required"] == []
    assert tools["get_real_dsl_revision_diff_preview"]["safety"]["readOnly"] is True
    assert tools["get_real_dsl_revision_diff_preview"]["safety"]["newLlmRequestSent"] is False
    assert tools["get_real_dsl_revision_diff_preview"]["safety"]["realLlmCalled"] is False
    assert tools["get_real_dsl_revision_diff_preview"]["safety"]["secretsRead"] is False
    assert tools["get_real_dsl_revision_diff_preview"]["safety"]["networkAccess"] is False
    assert tools["get_real_dsl_revision_diff_preview"]["safety"]["realPublishAllowed"] is False
    assert tools["get_real_dsl_revision_diff_preview"]["outputContract"]["dataPath"] == "data.realDslRevisionDiffPreview"
    assert tools["get_real_dsl_revision_diff_preview"]["outputContract"]["component"] == "RealDslRevisionDiffPreview"
    assert "diffTotal" in tools["get_real_dsl_revision_diff_preview"]["outputContract"]["summaryFields"]
    assert tools["create_real_dsl_revision_decision"]["backend"]["method"] == "POST"
    assert tools["create_real_dsl_revision_decision"]["backend"]["path"] == "/api/review/real-dsl-revision-decision"
    assert tools["create_real_dsl_revision_decision"]["inputSchema"]["required"] == [
        "suggestionId",
        "reviewer",
        "decision",
    ]
    assert tools["create_real_dsl_revision_decision"]["inputSchema"]["properties"]["decision"]["enum"] == [
        "approve",
        "reject",
        "request-change",
    ]
    assert tools["create_real_dsl_revision_decision"]["safety"]["newLlmRequestSent"] is False
    assert tools["create_real_dsl_revision_decision"]["safety"]["realLlmCalled"] is False
    assert tools["create_real_dsl_revision_decision"]["safety"]["sourceDslModified"] is False
    assert tools["create_real_dsl_revision_decision"]["safety"]["revisedDslModified"] is False
    assert tools["create_real_dsl_revision_decision"]["safety"]["realPublishAllowed"] is False
    assert tools["create_real_dsl_revision_decision"]["outputContract"]["dataPath"] == "data.realDslRevisionDecision"
    assert tools["create_real_dsl_revision_decision"]["outputContract"]["component"] == "RealDslRevisionDecision"
    assert tools["create_real_dsl_revision_decision"]["outputContract"]["sourceDslModified"] is False
    assert tools["promote_real_dsl_revision_candidate"]["backend"]["method"] == "POST"
    assert tools["promote_real_dsl_revision_candidate"]["backend"]["path"] == "/api/review/real-dsl-revision-promote"
    assert tools["promote_real_dsl_revision_candidate"]["reviewRequired"] is True
    assert tools["promote_real_dsl_revision_candidate"]["inputSchema"]["required"] == ["reviewer"]
    assert tools["promote_real_dsl_revision_candidate"]["safety"]["newLlmRequestSent"] is False
    assert tools["promote_real_dsl_revision_candidate"]["safety"]["realLlmCalled"] is False
    assert tools["promote_real_dsl_revision_candidate"]["safety"]["sourceDslModified"] is False
    assert tools["promote_real_dsl_revision_candidate"]["safety"]["revisedDslModified"] is False
    assert tools["promote_real_dsl_revision_candidate"]["safety"]["promotedCandidateWritten"] is True
    assert tools["promote_real_dsl_revision_candidate"]["safety"]["realPublishAllowed"] is False
    assert tools["promote_real_dsl_revision_candidate"]["outputContract"]["dataPath"] == "data.realDslRevisionPromotion"
    assert tools["promote_real_dsl_revision_candidate"]["outputContract"]["component"] == "RealDslRevisionPromotion"
    assert tools["promote_real_dsl_revision_candidate"]["outputContract"]["newTaskStatus"] == "WAITING_REVIEW"
    assert tools["enqueue_real_dsl_revision_candidate_review"]["backend"]["method"] == "POST"
    assert tools["enqueue_real_dsl_revision_candidate_review"]["backend"]["path"] == "/api/review/real-dsl-revision-enqueue"
    assert tools["enqueue_real_dsl_revision_candidate_review"]["reviewRequired"] is True
    assert tools["enqueue_real_dsl_revision_candidate_review"]["inputSchema"]["required"] == ["reviewer"]
    assert tools["enqueue_real_dsl_revision_candidate_review"]["safety"]["taskCreated"] is True
    assert tools["enqueue_real_dsl_revision_candidate_review"]["safety"]["artifactCreated"] is True
    assert tools["enqueue_real_dsl_revision_candidate_review"]["safety"]["newLlmRequestSent"] is False
    assert tools["enqueue_real_dsl_revision_candidate_review"]["safety"]["realPublishAllowed"] is False
    assert tools["enqueue_real_dsl_revision_candidate_review"]["outputContract"]["dataPath"] == "data.promotionReviewQueueItem"
    assert tools["enqueue_real_dsl_revision_candidate_review"]["outputContract"]["component"] == "RealDslRevisionPromotionReviewQueueItem"
    assert tools["enqueue_real_dsl_revision_candidate_review"]["outputContract"]["newTaskStatus"] == "WAITING_REVIEW"
    assert tools["create_lab_template_import_preview"]["backend"]["method"] == "POST"
    assert tools["create_lab_template_import_preview"]["backend"]["path"] == "/api/labs/import-preview"
    assert tools["create_lab_template_import_preview"]["inputSchema"]["required"] == ["taskId", "reviewer"]
    assert "contractConfig" not in tools["create_lab_template_import_preview"]["inputSchema"]["properties"]
    assert tools["create_lab_template_import_preview"]["safety"]["requiresApprovedTask"] is True
    assert tools["create_lab_template_import_preview"]["safety"]["databaseWritten"] is False
    assert tools["create_lab_template_import_preview"]["safety"]["realAgentImport"] is False
    assert tools["create_lab_template_import_preview"]["safety"]["realPublishAllowed"] is False
    assert tools["create_lab_template_import_preview"]["outputContract"]["dataPath"] == "data.labTemplateImportPreview"
    assert tools["create_lab_template_import_preview"]["outputContract"]["component"] == "LabTemplateImportPreview"
    assert tools["create_lab_template_import_preview"]["outputContract"]["sourceTaskStatus"] == "APPROVED"
    assert tools["create_lab_template_import_preview"]["outputContract"]["databaseWritten"] is False
    for name, path, source_kind, data_path, component, agent_entity in [
        (
            "create_exam_question_import_preview",
            "/api/exams/import-preview",
            "EXAM_DSL",
            "data.examQuestionImportPreview",
            "ExamQuestionImportPreview",
            "exam_question",
        ),
        (
            "create_grading_rule_import_preview",
            "/api/grading/import-preview",
            "GRADING_DSL",
            "data.gradingRuleImportPreview",
            "GradingRuleImportPreview",
            "grading_rule",
        ),
    ]:
        assert tools[name]["backend"]["method"] == "POST"
        assert tools[name]["backend"]["path"] == path
        assert tools[name]["inputSchema"]["required"] == ["taskId", "reviewer"]
        assert tools[name]["safety"]["requiresApprovedTask"] is True
        assert tools[name]["safety"]["sourceArtifactKind"] == source_kind
        assert tools[name]["safety"]["databaseWritten"] is False
        assert tools[name]["safety"]["realAgentImport"] is False
        assert tools[name]["safety"]["realPublishAllowed"] is False
        assert tools[name]["outputContract"]["dataPath"] == data_path
        assert tools[name]["outputContract"]["component"] == component
        assert tools[name]["outputContract"]["sourceTaskStatus"] == "APPROVED"
        assert tools[name]["outputContract"]["agentEntity"] == agent_entity
        assert tools[name]["outputContract"]["databaseWritten"] is False
    for name, path, component, agent_entity in [
        (
            "create_lab_template_mock_import",
            "/api/labs/mock-import",
            "LabTemplateMockImport",
            "lab_template",
        ),
        (
            "create_exam_question_mock_import",
            "/api/exams/mock-import",
            "ExamQuestionMockImport",
            "exam_question",
        ),
        (
            "create_grading_rule_mock_import",
            "/api/grading/mock-import",
            "GradingRuleMockImport",
            "grading_rule",
        ),
    ]:
        assert tools[name]["backend"]["method"] == "POST"
        assert tools[name]["backend"]["path"] == path
        assert tools[name]["inputSchema"]["required"] == ["taskId", "reviewer"]
        assert tools[name]["reviewRequired"] is True
        assert tools[name]["safety"]["requiresApprovedTask"] is True
        assert tools[name]["safety"]["requiresImportPreview"] is True
        assert tools[name]["safety"]["mockStoreWritten"] is True
        assert tools[name]["safety"]["databaseWritten"] is False
        assert tools[name]["safety"]["realAgentImport"] is False
        assert tools[name]["safety"]["realPublishAllowed"] is False
        assert tools[name]["outputContract"]["dataPath"] == "data.agentEntityMockImport"
        assert tools[name]["outputContract"]["component"] == component
        assert tools[name]["outputContract"]["agentEntity"] == agent_entity
        assert tools[name]["outputContract"]["mockStoreWritten"] is True
        assert tools[name]["outputContract"]["databaseWritten"] is False
        assert tools[name]["outputContract"]["realPublish"] is False
    list_entities_tool = tools["list_agent_entities"]
    assert list_entities_tool["backend"]["method"] == "GET"
    assert list_entities_tool["backend"]["path"] == "/api/platform-entities"
    assert list_entities_tool["reviewRequired"] is False
    assert list_entities_tool["inputSchema"]["required"] == []
    assert list_entities_tool["inputSchema"]["properties"]["entityType"]["type"] == "string"
    assert list_entities_tool["inputSchema"]["properties"]["sourceTaskId"]["type"] == "string"
    assert list_entities_tool["inputSchema"]["properties"]["coreDbPath"]["type"] == "string"
    assert list_entities_tool["safety"]["mode"] == "LOCAL_PLATFORM_ENTITY_READONLY"
    assert list_entities_tool["safety"]["readOnly"] is True
    assert list_entities_tool["safety"]["localCoreReadOnlyWhenCoreDbPathProvided"] is True
    assert list_entities_tool["safety"]["databaseWritten"] is False
    assert list_entities_tool["safety"]["productionDatabaseWritten"] is False
    assert list_entities_tool["safety"]["realAgentImport"] is False
    assert list_entities_tool["safety"]["realPublish"] is False
    assert list_entities_tool["outputContract"]["dataPath"] == "data.items"
    assert "LOCAL_SQLITE_BACKEND_CORE_READONLY" in list_entities_tool["outputContract"]["modeMayBe"]
    assert list_entities_tool["outputContract"]["readOnly"] is True
    assert list_entities_tool["outputContract"]["realAgentImport"] is False
    get_entity_tool = tools["get_agent_entity"]
    assert get_entity_tool["backend"]["method"] == "GET"
    assert get_entity_tool["backend"]["path"] == "/api/platform-entities/{id}"
    assert get_entity_tool["reviewRequired"] is False
    assert get_entity_tool["inputSchema"]["required"] == ["id"]
    assert get_entity_tool["inputSchema"]["properties"]["coreDbPath"]["type"] == "string"
    assert get_entity_tool["safety"]["mode"] == "LOCAL_PLATFORM_ENTITY_READONLY"
    assert get_entity_tool["safety"]["readOnly"] is True
    assert get_entity_tool["safety"]["databaseWritten"] is False
    assert get_entity_tool["safety"]["realAgentImport"] is False
    assert get_entity_tool["outputContract"]["dataPath"] == "data.agentEntityRecord"
    assert get_entity_tool["outputContract"]["activityPath"] == "data.agentEntityImportActivity"
    assert get_entity_tool["outputContract"]["readOnly"] is True
    validate_contract_tool = tools["validate_agent_entity_contract"]
    assert validate_contract_tool["backend"]["method"] == "POST"
    assert validate_contract_tool["backend"]["path"] == "/api/platform-entities/contract-validate"
    assert validate_contract_tool["reviewRequired"] is False
    assert validate_contract_tool["inputSchema"]["required"] == ["contractConfig"]
    assert validate_contract_tool["inputSchema"]["properties"]["entityType"]["type"] == "string"
    assert validate_contract_tool["safety"]["mode"] == "LOCAL_PLATFORM_API_CONTRACT_VALIDATION"
    assert validate_contract_tool["safety"]["localConfigOnly"] is True
    assert validate_contract_tool["safety"]["requestSent"] is False
    assert validate_contract_tool["safety"]["networkAccess"] is False
    assert validate_contract_tool["safety"]["secretsRead"] is False
    assert validate_contract_tool["safety"]["realAgentImport"] is False
    assert validate_contract_tool["outputContract"]["dataPath"] == "data.platformApiContractValidation"
    assert validate_contract_tool["outputContract"]["localConfigOnly"] is True
    assert validate_contract_tool["outputContract"]["requestSent"] is False
    assert validate_contract_tool["outputContract"]["realAgentImport"] is False
    readiness_tool = tools["get_agent_entity_readiness_report"]
    assert readiness_tool["backend"]["method"] == "GET"
    assert readiness_tool["backend"]["path"] == "/api/platform-entities/readiness-report"
    assert readiness_tool["reviewRequired"] is False
    assert readiness_tool["inputSchema"]["required"] == []
    assert readiness_tool["inputSchema"]["properties"]["sourceTaskId"]["type"] == "string"
    assert readiness_tool["safety"]["mode"] == "LOCAL_AGENT_ENTITY_READINESS_REPORT"
    assert readiness_tool["safety"]["readOnly"] is True
    assert readiness_tool["safety"]["databaseWritten"] is False
    assert readiness_tool["safety"]["realAgentImport"] is False
    assert readiness_tool["safety"]["realPublish"] is False
    assert readiness_tool["outputContract"]["dataPath"] == "data.agentEntityReadinessReport"
    assert readiness_tool["outputContract"]["component"] == "AgentEntityReadinessReport"
    assert readiness_tool["outputContract"]["agentEntities"] == [
        "lab_template",
        "exam_question",
        "grading_rule",
        "ppt_deck",
    ]
    assert readiness_tool["outputContract"]["summaryFields"] == [
        "agentEntitySignoffReadyTotal",
        "agentEntitySignoffRecordedTotal",
        "allPlatformEntitiesReadyForSignoff",
        "allPlatformEntitiesSignoffRecorded",
        "postSignoffPrePublishReadyTotal",
        "allPostSignoffPrePublishReady",
    ]
    assert readiness_tool["outputContract"]["itemFields"] == [
        "signoffState",
        "readyForAgentEntitySignoff",
        "signoffRecorded",
        "latestSignoffArtifactId",
        "postSignoffPrePublishChecklist",
    ]
    assert readiness_tool["outputContract"]["signoffReadyMeans"] == (
        "ready for manual signoff action and not yet signed"
    )
    assert readiness_tool["outputContract"]["signoffRecordedMeans"] == (
        "local AgentEntitySignoffRecord already exists"
    )
    assert readiness_tool["outputContract"]["postSignoffPrePublishChecklistMeans"] == (
        "read-only final human review checklist before any real publish planning"
    )
    assert readiness_tool["outputContract"]["databaseWritten"] is False
    assert readiness_tool["outputContract"]["realAgentImport"] is False
    assert readiness_tool["outputContract"]["realPublish"] is False
    core_readiness_tool = tools["get_core_workflow_readiness"]
    assert core_readiness_tool["backend"]["method"] == "GET"
    assert core_readiness_tool["backend"]["path"] == "/api/review-tasks/{taskId}/core-readiness"
    assert core_readiness_tool["reviewRequired"] is False
    assert core_readiness_tool["inputSchema"]["required"] == ["taskId"]
    assert core_readiness_tool["inputSchema"]["properties"]["taskId"]["type"] == "string"
    assert core_readiness_tool["safety"]["mode"] == "CORE_WORKFLOW_READINESS_READ_ONLY"
    assert core_readiness_tool["safety"]["readOnly"] is True
    assert core_readiness_tool["safety"]["newLlmRequestSent"] is False
    assert core_readiness_tool["safety"]["realLlmCalled"] is False
    assert core_readiness_tool["safety"]["secretsRead"] is False
    assert core_readiness_tool["safety"]["networkAccess"] is False
    assert core_readiness_tool["safety"]["databaseWritten"] is False
    assert core_readiness_tool["safety"]["realAgentImport"] is False
    assert core_readiness_tool["safety"]["sandboxExecutedByReport"] is False
    assert core_readiness_tool["safety"]["contestantCodeExecutedByReport"] is False
    assert core_readiness_tool["safety"]["autoApproveAllowed"] is False
    assert core_readiness_tool["safety"]["autoPublishAllowed"] is False
    assert core_readiness_tool["safety"]["realPublish"] is False
    assert core_readiness_tool["outputContract"]["dataPath"] == "data.coreWorkflowReadinessReport"
    assert core_readiness_tool["outputContract"]["component"] == "CoreWorkflowReadinessReport"
    assert core_readiness_tool["outputContract"]["mode"] == "CORE_WORKFLOW_READINESS_READ_ONLY"
    assert "summary" in core_readiness_tool["outputContract"]["requiredFields"]
    assert "blockedSteps" in core_readiness_tool["outputContract"]["requiredFields"]
    assert "platformImportPreviewActionSummary" in core_readiness_tool["outputContract"]["requiredFields"]
    assert "nextToolRecommendation" in core_readiness_tool["outputContract"]["requiredFields"]
    assert core_readiness_tool["outputContract"]["summaryPath"] == "data.coreWorkflowReadinessReport.summary"
    assert core_readiness_tool["outputContract"]["finalReviewStatePath"] == (
        "data.coreWorkflowReadinessReport.summary.finalReviewState"
    )
    assert core_readiness_tool["outputContract"]["stepsPath"] == "data.coreWorkflowReadinessReport.steps"
    assert core_readiness_tool["outputContract"]["blockedStepsPath"] == "data.coreWorkflowReadinessReport.blockedSteps"
    assert core_readiness_tool["outputContract"]["platformImportPreviewActionSummaryPath"] == (
        "data.coreWorkflowReadinessReport.platformImportPreviewActionSummary"
    )
    assert core_readiness_tool["outputContract"]["platformImportPreviewActionSummaryFields"] == [
        "pendingPreviewTotal",
        "pendingPlatformEntities",
        "pendingPreviewComponents",
        "pendingCliCommands",
        "pendingNextRequiredActions",
        "contentQualityReadyTotal",
        "contentQualityBlockedTotal",
    ]
    assert core_readiness_tool["outputContract"]["nextToolRecommendationPath"] == (
        "data.coreWorkflowReadinessReport.nextToolRecommendation"
    )
    assert core_readiness_tool["outputContract"]["nextToolRecommendationFields"] == [
        "reasonCode",
        "actionType",
        "recommendedNextAction",
        "finalReviewState",
        "toolName",
        "toolAvailable",
        "autoExecuteAllowed",
        "autoApproveAllowed",
        "autoPublishAllowed",
        "realPublishAllowed",
    ]
    assert core_readiness_tool["outputContract"]["manualReviewRequired"] is True
    assert core_readiness_tool["outputContract"]["autoApproveAllowed"] is False
    assert core_readiness_tool["outputContract"]["autoPublishAllowed"] is False
    assert core_readiness_tool["outputContract"]["realPublishAllowed"] is False
    signoff_tool = tools["record_agent_entity_signoff"]
    assert signoff_tool["backend"]["method"] == "POST"
    assert signoff_tool["backend"]["path"] == "/api/platform-entities/{id}/signoff"
    assert signoff_tool["reviewRequired"] is True
    assert signoff_tool["inputSchema"]["required"] == ["id", "reviewer"]
    assert signoff_tool["safety"]["mode"] == "LOCAL_PLATFORM_ENTITY_SIGNOFF_RECORD"
    assert signoff_tool["safety"]["networkAccess"] is False
    assert signoff_tool["safety"]["secretsRead"] is False
    assert signoff_tool["safety"]["autoPublishAllowed"] is False
    assert signoff_tool["safety"]["realPublish"] is False
    assert signoff_tool["outputContract"]["dataPath"] == "data.agentEntitySignoffRecord"
    assert signoff_tool["outputContract"]["component"] == "AgentEntitySignoffRecord"
    assert signoff_tool["outputContract"]["realPublish"] is False
    final_review_tool = tools["record_final_publish_review_decision"]
    assert final_review_tool["backend"]["method"] == "POST"
    assert final_review_tool["backend"]["path"] == "/api/platform-entities/{id}/final-publish-review-decision"
    assert final_review_tool["reviewRequired"] is True
    assert final_review_tool["inputSchema"]["required"] == [
        "id",
        "reviewer",
        "decision",
        "confirmNoAutoPublish",
        "confirmNoRealPublish",
        "confirmFinalHumanReview",
    ]
    assert final_review_tool["safety"]["mode"] == "LOCAL_FINAL_HUMAN_PUBLISH_REVIEW_DECISION"
    assert final_review_tool["safety"]["autoPublishAllowed"] is False
    assert final_review_tool["safety"]["realPublish"] is False
    assert final_review_tool["safety"]["publishExecuted"] is False
    assert final_review_tool["outputContract"]["dataPath"] == "data.finalPublishReviewDecision"
    assert final_review_tool["outputContract"]["component"] == "FinalPublishReviewDecision"
    assert final_review_tool["outputContract"]["publishExecuted"] is False
    import_dry_run_tool = tools["create_agent_entity_import_dry_run"]
    assert import_dry_run_tool["backend"]["method"] == "POST"
    assert import_dry_run_tool["backend"]["path"] == "/api/platform-entities/{id}/import-dry-run"
    assert import_dry_run_tool["reviewRequired"] is True
    assert import_dry_run_tool["inputSchema"]["required"] == ["id", "reviewer"]
    assert import_dry_run_tool["inputSchema"]["properties"]["output"]["type"] == "string"
    assert import_dry_run_tool["inputSchema"]["properties"]["contractConfig"]["type"] == "string"
    assert import_dry_run_tool["safety"]["mode"] == "REAL_PLATFORM_IMPORT_DRY_RUN_ONLY"
    assert import_dry_run_tool["safety"]["requiresMockImport"] is True
    assert import_dry_run_tool["safety"]["manualPlatformReviewRequired"] is True
    assert import_dry_run_tool["safety"]["dryRunOnly"] is True
    assert import_dry_run_tool["safety"]["requestSent"] is False
    assert import_dry_run_tool["safety"]["networkAccess"] is False
    assert import_dry_run_tool["safety"]["secretsRead"] is False
    assert import_dry_run_tool["safety"]["databaseWritten"] is False
    assert import_dry_run_tool["safety"]["realAgentImport"] is False
    assert import_dry_run_tool["safety"]["realPublish"] is False
    assert import_dry_run_tool["outputContract"]["dataPath"] == "data.agentEntityImportDryRun"
    assert import_dry_run_tool["outputContract"]["component"] == "AgentEntityImportDryRun"
    assert import_dry_run_tool["outputContract"]["mode"] == "REAL_PLATFORM_IMPORT_DRY_RUN_ONLY"
    assert import_dry_run_tool["outputContract"]["agentEntities"] == [
        "lab_template",
        "exam_question",
        "grading_rule",
        "ppt_deck",
    ]
    assert import_dry_run_tool["outputContract"]["dryRunOnly"] is True
    assert import_dry_run_tool["outputContract"]["requestSent"] is False
    assert import_dry_run_tool["outputContract"]["networkAccess"] is False
    assert import_dry_run_tool["outputContract"]["databaseWritten"] is False
    assert import_dry_run_tool["outputContract"]["realAgentImport"] is False
    assert import_dry_run_tool["outputContract"]["realPublish"] is False
    import_send_tool = tools["agent_internal_publish_request"]
    assert import_send_tool["backend"]["method"] == "POST"
    assert import_send_tool["backend"]["path"] == "/api/platform-entities/{id}/import-send"
    assert import_send_tool["riskLevel"] == "high"
    assert import_send_tool["reviewRequired"] is True
    assert import_send_tool["inputSchema"]["required"] == [
        "id",
        "reviewer",
        "dryRun",
        "explicitPlatformCallOptIn",
        "confirmDryRunReviewed",
        "confirmManualPlatformReview",
        "confirmNoAutoPublish",
    ]
    assert import_send_tool["inputSchema"]["properties"]["baseUrl"]["type"] == "string"
    assert import_send_tool["inputSchema"]["properties"]["timeoutSeconds"]["type"] == "integer"
    assert import_send_tool["inputSchema"]["properties"]["maxRetries"]["type"] == "integer"
    assert import_send_tool["inputSchema"]["properties"]["contractConfig"]["type"] == "string"
    assert import_send_tool["safety"]["mode"] == "REAL_PLATFORM_IMPORT_REQUEST_SENT"
    assert import_send_tool["safety"]["requestSent"] is True
    assert import_send_tool["safety"]["networkAccess"] is True
    assert import_send_tool["safety"]["secretsRead"] is True
    assert import_send_tool["safety"]["secretValueReturned"] is False
    assert import_send_tool["safety"]["databaseWrittenByLocalSystem"] is False
    assert import_send_tool["safety"]["manualPlatformReviewRequired"] is True
    assert import_send_tool["safety"]["autoPublishAllowed"] is False
    assert import_send_tool["safety"]["realPublish"] is False
    assert import_send_tool["outputContract"]["dataPath"] == "data.agentEntityImportSendResult"
    assert import_send_tool["outputContract"]["component"] == "AgentEntityImportSendResult"
    assert import_send_tool["outputContract"]["mode"] == "REAL_PLATFORM_IMPORT_REQUEST_SENT"
    assert import_send_tool["outputContract"]["requestSent"] is True
    assert import_send_tool["outputContract"]["secretValueReturned"] is False
    assert import_send_tool["outputContract"]["databaseWrittenByLocalSystem"] is False
    assert import_send_tool["outputContract"]["autoPublishAllowed"] is False
    assert import_send_tool["outputContract"]["realPublish"] is False
    import_result_tool = tools["record_agent_entity_publish_result"]
    assert import_result_tool["backend"]["method"] == "POST"
    assert import_result_tool["backend"]["path"] == "/api/platform-entities/{id}/import-result"
    assert import_result_tool["riskLevel"] == "medium"
    assert import_result_tool["reviewRequired"] is True
    assert import_result_tool["inputSchema"]["required"] == [
        "id",
        "reviewer",
        "sendResult",
        "agentStatus",
    ]
    assert import_result_tool["inputSchema"]["properties"]["agentStatus"]["enum"] == [
        "PENDING_MANUAL_PLATFORM_REVIEW",
        "ACCEPTED_FOR_DRAFT",
        "REJECTED_BY_PLATFORM",
        "FAILED",
    ]
    assert import_result_tool["safety"]["mode"] == "LOCAL_PLATFORM_IMPORT_RESULT_RECORD"
    assert import_result_tool["safety"]["requestSent"] is False
    assert import_result_tool["safety"]["networkAccess"] is False
    assert import_result_tool["safety"]["secretsRead"] is False
    assert import_result_tool["safety"]["mockStoreUpdated"] is True
    assert import_result_tool["safety"]["databaseWrittenByLocalSystem"] is False
    assert import_result_tool["safety"]["realPublish"] is False
    assert import_result_tool["outputContract"]["dataPath"] == "data.agentEntityImportResultRecord"
    assert import_result_tool["outputContract"]["component"] == "AgentEntityImportResultRecord"
    assert import_result_tool["outputContract"]["mode"] == "LOCAL_PLATFORM_IMPORT_RESULT_RECORD"
    assert import_result_tool["outputContract"]["requestSent"] is False
    assert import_result_tool["outputContract"]["networkAccess"] is False
    assert import_result_tool["outputContract"]["secretValueReturned"] is False
    assert import_result_tool["outputContract"]["mockStoreUpdated"] is True
    assert import_result_tool["outputContract"]["realPublish"] is False
    import_status_tool = tools["query_agent_publish_status"]
    assert import_status_tool["backend"]["method"] == "POST"
    assert import_status_tool["backend"]["path"] == "/api/platform-entities/{id}/import-status"
    assert import_status_tool["riskLevel"] == "medium"
    assert import_status_tool["reviewRequired"] is True
    assert import_status_tool["inputSchema"]["required"] == [
        "id",
        "reviewer",
        "sendResult",
        "explicitPlatformQueryOptIn",
    ]
    assert import_status_tool["inputSchema"]["properties"]["statusPathTemplate"]["type"] == "string"
    assert import_status_tool["inputSchema"]["properties"]["contractConfig"]["type"] == "string"
    assert import_status_tool["inputSchema"]["properties"]["timeoutSeconds"]["type"] == "integer"
    assert import_status_tool["inputSchema"]["properties"]["maxRetries"]["type"] == "integer"
    assert import_status_tool["safety"]["mode"] == "REAL_PLATFORM_IMPORT_STATUS_QUERY"
    assert import_status_tool["safety"]["readOnlyToPlatform"] is True
    assert import_status_tool["safety"]["requestSent"] is True
    assert import_status_tool["safety"]["networkAccess"] is True
    assert import_status_tool["safety"]["secretsRead"] is True
    assert import_status_tool["safety"]["secretValueReturned"] is False
    assert import_status_tool["safety"]["mockStoreUpdated"] is False
    assert import_status_tool["safety"]["manualResultRecordRequired"] is True
    assert import_status_tool["safety"]["realPublish"] is False
    assert import_status_tool["outputContract"]["dataPath"] == "data.agentEntityImportStatusQuery"
    assert import_status_tool["outputContract"]["component"] == "AgentEntityImportStatusQuery"
    assert import_status_tool["outputContract"]["mode"] == "REAL_PLATFORM_IMPORT_STATUS_QUERY"
    assert import_status_tool["outputContract"]["requestSent"] is True
    assert import_status_tool["outputContract"]["networkAccess"] is True
    assert import_status_tool["outputContract"]["secretValueReturned"] is False
    assert import_status_tool["outputContract"]["mockStoreUpdated"] is False
    assert import_status_tool["outputContract"]["realPublish"] is False
    readonly_tool = tools["run_readonly_grading_evidence"]
    assert readonly_tool["backend"]["method"] == "POST"
    assert readonly_tool["backend"]["path"] == "/api/grading/readonly-evidence"
    assert readonly_tool["inputSchema"]["required"] == ["grading", "submission"]
    assert readonly_tool["safety"]["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert readonly_tool["safety"]["readonlyOnly"] is True
    assert readonly_tool["safety"]["commandExecuted"] is False
    assert readonly_tool["safety"]["pytestExecuted"] is False
    assert readonly_tool["safety"]["notebookExecuted"] is False
    assert readonly_tool["safety"]["contestantCodeExecuted"] is False
    assert readonly_tool["safety"]["realPublish"] is False
    assert readonly_tool["outputContract"]["dataPath"] == "data.report"
    assert readonly_tool["outputContract"]["detailPath"] == "data.reportDetail"
    assert readonly_tool["outputContract"]["contestantCodeExecuted"] is False
    controlled_tool = tools["run_controlled_grading_evidence"]
    assert controlled_tool["backend"]["method"] == "POST"
    assert controlled_tool["backend"]["path"] == "/api/grading/controlled-evidence"
    assert controlled_tool["inputSchema"]["required"] == ["grading", "submission"]
    assert controlled_tool["safety"]["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert controlled_tool["safety"]["readonlyOnly"] is False
    assert controlled_tool["safety"]["commandExecuted"] is True
    assert controlled_tool["safety"]["pytestExecuted"] is True
    assert controlled_tool["safety"]["notebookExecuted"] is False
    assert controlled_tool["safety"]["contestantCodeExecuted"] is True
    assert controlled_tool["safety"]["networkEnabled"] is False
    assert controlled_tool["safety"]["hostExecutionAllowed"] is False
    assert controlled_tool["safety"]["realPublish"] is False
    assert controlled_tool["outputContract"]["dataPath"] == "data.report"
    assert controlled_tool["outputContract"]["detailPath"] == "data.reportDetail"
    assert controlled_tool["outputContract"]["controlledDockerOnly"] is True
    assert controlled_tool["outputContract"]["supportedCheckTypes"] == ["stdout_contains", "pytest"]
    assert controlled_tool["outputContract"]["safetyRequired"]["contestantCodeExecuted"] is True
    assert controlled_tool["outputContract"]["safetyRequired"]["networkEnabled"] is False
    merge_evidence_tool = tools["merge_grading_evidence_reports"]
    assert merge_evidence_tool["backend"]["method"] == "POST"
    assert merge_evidence_tool["backend"]["path"] == "/api/grading/evidence-merge"
    assert merge_evidence_tool["inputSchema"]["required"] == ["reports", "output"]
    assert merge_evidence_tool["inputSchema"]["properties"]["reports"]["type"] == "array"
    assert merge_evidence_tool["inputSchema"]["properties"]["reports"]["minItems"] == 1
    assert merge_evidence_tool["safety"]["mode"] == "GRADING_EVIDENCE_MERGE_REPORT"
    assert merge_evidence_tool["safety"]["readExistingReportsOnly"] is True
    assert merge_evidence_tool["safety"]["mergeExecutedOnlyExistingReports"] is True
    assert merge_evidence_tool["safety"]["sandboxExecutedByTool"] is False
    assert merge_evidence_tool["safety"]["contestantCodeExecutedByTool"] is False
    assert merge_evidence_tool["safety"]["networkAccess"] is False
    assert merge_evidence_tool["safety"]["autoApproveAllowed"] is False
    assert merge_evidence_tool["safety"]["realPublish"] is False
    assert merge_evidence_tool["outputContract"]["dataPath"] == "data.report"
    assert merge_evidence_tool["outputContract"]["mode"] == "GRADING_EVIDENCE_MERGE_REPORT"
    assert merge_evidence_tool["outputContract"]["coveragePath"] == "data.report.evidenceCoverage"
    assert merge_evidence_tool["outputContract"]["toolExecutionSafety"]["sandboxExecutedByTool"] is False
    assert merge_evidence_tool["outputContract"]["toolExecutionSafety"]["contestantCodeExecutedByTool"] is False
    assert merge_evidence_tool["outputContract"]["manualReviewRequired"] is True
    assert merge_evidence_tool["outputContract"]["autoApproveAllowed"] is False
    assert merge_evidence_tool["outputContract"]["realPublishAllowed"] is False
    auto_evidence_tool = tools["run_grading_evidence_auto"]
    assert auto_evidence_tool["backend"]["method"] == "POST"
    assert auto_evidence_tool["backend"]["path"] == "/api/grading/evidence-auto"
    assert auto_evidence_tool["inputSchema"]["required"] == ["grading", "submission", "output"]
    assert auto_evidence_tool["inputSchema"]["properties"]["includeControlledCommand"]["type"] == "boolean"
    assert auto_evidence_tool["safety"]["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert auto_evidence_tool["safety"]["sourceMode"] == "EVIDENCE_AUTO"
    assert auto_evidence_tool["safety"]["readonlyAlwaysRunsFirst"] is True
    assert auto_evidence_tool["safety"]["controlledCommandRequiresExplicitFlag"] is True
    assert auto_evidence_tool["safety"]["controlledCommandDefaultEnabled"] is False
    assert auto_evidence_tool["safety"]["defaultContestantCodeExecuted"] is False
    assert auto_evidence_tool["safety"]["defaultCommandExecuted"] is False
    assert auto_evidence_tool["safety"]["controlledCommandMayExecuteWhenExplicitlyRequested"] is True
    assert auto_evidence_tool["safety"]["networkEnabled"] is False
    assert auto_evidence_tool["safety"]["hostExecutionAllowed"] is False
    assert auto_evidence_tool["safety"]["autoApproveAllowed"] is False
    assert auto_evidence_tool["safety"]["realPublish"] is False
    assert auto_evidence_tool["outputContract"]["dataPath"] == "data.report"
    assert auto_evidence_tool["outputContract"]["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert auto_evidence_tool["outputContract"]["sourceMode"] == "EVIDENCE_AUTO"
    assert auto_evidence_tool["outputContract"]["stepsPath"] == "data.report.steps"
    assert auto_evidence_tool["outputContract"]["warningsPath"] == "data.report.warnings"
    assert "executionMatrix" in auto_evidence_tool["outputContract"]["requiredFields"]
    assert "nextCoreAction" in auto_evidence_tool["outputContract"]["requiredFields"]
    assert auto_evidence_tool["outputContract"]["executionMatrixPath"] == "data.report.executionMatrix"
    assert auto_evidence_tool["outputContract"]["nextCoreActionPath"] == "data.report.nextCoreAction"
    assert auto_evidence_tool["outputContract"]["coveragePath"] == "data.report.evidenceCoverage"
    assert auto_evidence_tool["outputContract"]["readonlyAlwaysRunsFirst"] is True
    assert auto_evidence_tool["outputContract"]["controlledCommandDefaultEnabled"] is False
    assert auto_evidence_tool["outputContract"]["defaultToolExecutionSafety"]["contestantCodeExecuted"] is False
    assert auto_evidence_tool["outputContract"]["defaultToolExecutionSafety"]["commandExecuted"] is False
    assert auto_evidence_tool["outputContract"]["controlledCommandSafetyWhenExplicit"]["mayExecuteCommandInControlledDocker"] is True
    assert auto_evidence_tool["outputContract"]["manualReviewRequired"] is True
    assert auto_evidence_tool["outputContract"]["autoApproveAllowed"] is False
    assert auto_evidence_tool["outputContract"]["realPublishAllowed"] is False
    create_job_tool = tools["create_grading_job"]
    assert create_job_tool["backend"]["method"] == "POST"
    assert create_job_tool["backend"]["path"] == "/api/grading/jobs"
    assert create_job_tool["inputSchema"]["required"] == ["grading", "submission", "output", "submissionId"]
    assert create_job_tool["inputSchema"]["properties"]["dbPath"]["type"] == "string"
    assert create_job_tool["safety"]["mode"] == "LOCAL_GRADING_JOB"
    assert create_job_tool["safety"]["jobStatus"] == "QUEUED"
    assert create_job_tool["safety"]["sandboxExecutedByCreate"] is False
    assert create_job_tool["safety"]["contestantCodeExecutedByCreate"] is False
    assert create_job_tool["safety"]["queuePersistedToProduction"] is False
    assert create_job_tool["safety"]["productionDatabaseWritten"] is False
    assert create_job_tool["safety"]["autoApproveAllowed"] is False
    assert create_job_tool["safety"]["realPublish"] is False
    assert create_job_tool["outputContract"]["dataPath"] == "data.gradingJob"
    assert create_job_tool["outputContract"]["newJobStatus"] == "QUEUED"
    assert create_job_tool["outputContract"]["sandboxExecutedByCreate"] is False
    list_jobs_tool = tools["list_grading_jobs"]
    assert list_jobs_tool["backend"]["method"] == "GET"
    assert list_jobs_tool["backend"]["path"] == "/api/grading/jobs"
    assert list_jobs_tool["inputSchema"]["required"] == []
    assert list_jobs_tool["inputSchema"]["properties"]["status"]["type"] == "string"
    assert list_jobs_tool["safety"]["readOnly"] is True
    assert list_jobs_tool["safety"]["localSqliteReadOptional"] is True
    assert list_jobs_tool["safety"]["sandboxExecutedByRead"] is False
    assert list_jobs_tool["outputContract"]["dataPath"] == "data.items"
    get_job_tool = tools["get_grading_job"]
    assert get_job_tool["backend"]["path"] == "/api/grading/jobs/{id}"
    assert get_job_tool["inputSchema"]["required"] == ["id"]
    assert get_job_tool["safety"]["readOnly"] is True
    run_job_tool = tools["run_grading_job"]
    assert run_job_tool["backend"]["method"] == "POST"
    assert run_job_tool["backend"]["path"] == "/api/grading/jobs/{id}/run"
    assert run_job_tool["inputSchema"]["required"] == ["id"]
    assert run_job_tool["inputSchema"]["properties"]["leaseSeconds"]["type"] == "integer"
    assert run_job_tool["inputSchema"]["properties"]["maxAttempts"]["type"] == "integer"
    assert run_job_tool["safety"]["mode"] == "LOCAL_GRADING_JOB_SYNC_RUN"
    assert run_job_tool["safety"]["usesEvidenceAuto"] is True
    assert run_job_tool["safety"]["createsGradingRecord"] is True
    assert run_job_tool["safety"]["newRecordReviewState"] == "WAITING_REVIEW_OR_NEEDS_EVIDENCE"
    assert run_job_tool["safety"]["controlledCommandDefaultEnabled"] is False
    assert run_job_tool["safety"]["networkEnabled"] is False
    assert run_job_tool["safety"]["hostExecutionAllowed"] is False
    assert run_job_tool["safety"]["autoApproveAllowed"] is False
    assert run_job_tool["safety"]["realPublish"] is False
    assert run_job_tool["outputContract"]["recordPath"] == "data.gradingRecord"
    assert run_job_tool["outputContract"]["manualRecordReviewRequired"] is True
    create_record_tool = tools["create_grading_record"]
    assert create_record_tool["backend"]["method"] == "POST"
    assert create_record_tool["backend"]["path"] == "/api/grading/records"
    assert create_record_tool["inputSchema"]["required"] == ["report", "submissionId"]
    assert create_record_tool["safety"]["mode"] == "LOCAL_GRADING_RECORD"
    assert create_record_tool["safety"]["readsExistingReportOnly"] is True
    assert create_record_tool["safety"]["recordCreatesNewExecution"] is False
    assert create_record_tool["safety"]["taskStatusChanged"] is False
    assert create_record_tool["safety"]["sandboxExecutedByRecordCreate"] is False
    assert create_record_tool["outputContract"]["dataPath"] == "data.gradingRecord"
    assert create_record_tool["outputContract"]["newRecordReviewState"] == "WAITING_REVIEW_OR_NEEDS_EVIDENCE"
    list_records_tool = tools["list_grading_records"]
    assert list_records_tool["backend"]["method"] == "GET"
    assert list_records_tool["backend"]["path"] == "/api/grading/records"
    assert list_records_tool["inputSchema"]["required"] == []
    assert list_records_tool["safety"]["readOnly"] is True
    assert list_records_tool["outputContract"]["component"] == "GradingRecordList"
    get_record_tool = tools["get_grading_record"]
    assert get_record_tool["backend"]["path"] == "/api/grading/records/{id}"
    assert get_record_tool["inputSchema"]["required"] == ["id"]
    assert get_record_tool["safety"]["readOnly"] is True
    review_record_tool = tools["review_grading_record"]
    assert review_record_tool["backend"]["method"] == "POST"
    assert review_record_tool["backend"]["path"] == "/api/grading/records/{id}/review"
    assert review_record_tool["reviewRequired"] is True
    assert review_record_tool["inputSchema"]["required"] == ["id", "reviewer", "decision"]
    assert review_record_tool["inputSchema"]["properties"]["decision"]["enum"] == [
        "approve-ready",
        "needs-evidence",
        "needs-revision",
    ]
    assert review_record_tool["safety"]["mode"] == "LOCAL_GRADING_RECORD_REVIEW"
    assert review_record_tool["safety"]["recordReviewOnly"] is True
    assert review_record_tool["safety"]["taskStatusChanged"] is False
    assert review_record_tool["safety"]["recordCreatesNewExecution"] is False
    assert review_record_tool["safety"]["sandboxExecutedByRecordReview"] is False
    assert review_record_tool["safety"]["contestantCodeExecutedByRecordReview"] is False
    assert review_record_tool["safety"]["autoApproveAllowed"] is False
    assert review_record_tool["safety"]["realPublish"] is False
    assert review_record_tool["outputContract"]["allowedDecisions"] == [
        "approve-ready",
        "needs-evidence",
        "needs-revision",
    ]
    assert review_record_tool["outputContract"]["taskStatusChanged"] is False
    assert review_record_tool["outputContract"]["recordCreatesNewExecution"] is False
    decision_note_tool = tools["record_review_decision_note"]
    assert decision_note_tool["backend"]["method"] == "POST"
    assert decision_note_tool["backend"]["path"] == "/api/review-tasks/{taskId}/decision-note"
    assert decision_note_tool["reviewRequired"] is True
    assert decision_note_tool["inputSchema"]["required"] == ["taskId", "reviewer", "decision"]
    assert "contractConfig" not in decision_note_tool["inputSchema"]["properties"]
    assert decision_note_tool["inputSchema"]["properties"]["decision"]["enum"] == [
        "approve-ready",
        "needs-revision",
        "needs-evidence",
    ]
    assert decision_note_tool["safety"]["mode"] == "LOCAL_REVIEW_DECISION_NOTE_RECORD"
    assert decision_note_tool["safety"]["taskStatusChanged"] is False
    assert decision_note_tool["safety"]["autoApproveAllowed"] is False
    assert decision_note_tool["safety"]["batchStateChangeAllowed"] is False
    assert decision_note_tool["safety"]["sandboxExecutedByDecisionNote"] is False
    assert decision_note_tool["safety"]["contestantCodeExecuted"] is False
    assert decision_note_tool["safety"]["realPublish"] is False
    assert decision_note_tool["outputContract"]["dataPath"] == "data.decisionNote"
    assert decision_note_tool["outputContract"]["artifactKind"] == "REVIEW_DECISION_NOTE"
    assert decision_note_tool["outputContract"]["taskStatusChanged"] is False
    assert decision_note_tool["outputContract"]["autoApproveAllowed"] is False
    assert decision_note_tool["outputContract"]["realPublish"] is False
    readiness_tool = tools["get_grading_evidence_readiness"]
    assert readiness_tool["backend"]["method"] == "GET"
    assert readiness_tool["backend"]["path"] == "/api/grading/evidence-readiness"
    assert readiness_tool["inputSchema"]["required"] == ["report"]
    assert readiness_tool["inputSchema"]["properties"]["report"]["type"] == "array"
    assert readiness_tool["inputSchema"]["properties"]["report"]["minItems"] == 1
    assert readiness_tool["safety"]["mode"] == "GRADING_EVIDENCE_READINESS"
    assert readiness_tool["safety"]["readExistingReportsOnly"] is True
    assert readiness_tool["safety"]["sandboxExecutedByReadiness"] is False
    assert readiness_tool["safety"]["contestantCodeExecutedByReadiness"] is False
    assert readiness_tool["safety"]["commandExecutedByReadiness"] is False
    assert readiness_tool["safety"]["autoApproveAllowed"] is False
    assert readiness_tool["safety"]["realPublish"] is False
    assert readiness_tool["outputContract"]["dataPath"] == "data.gradingEvidenceReadiness"
    assert readiness_tool["outputContract"]["mode"] == "GRADING_EVIDENCE_READINESS"
    assert readiness_tool["outputContract"]["summaryPath"] == "data.gradingEvidenceReadiness.summary"
    assert readiness_tool["outputContract"]["itemsPath"] == "data.gradingEvidenceReadiness.items"
    assert readiness_tool["outputContract"]["nextActionsPath"] == "data.gradingEvidenceReadiness.nextActions"
    assert readiness_tool["outputContract"]["readExistingReportsOnly"] is True
    assert readiness_tool["outputContract"]["manualReviewRequired"] is True
    assert readiness_tool["outputContract"]["autoApproveAllowed"] is False
    assert readiness_tool["outputContract"]["realPublishAllowed"] is False
    review_summary_contract = tools["get_review_task_summary"]["outputContract"]
    assert review_summary_contract["dataPath"] == "data.reviewTaskSummary"
    assert "reviewPriorityQueue" in review_summary_contract["requiredFields"]
    assert review_summary_contract["reviewPriorityQueue"]["dataPath"] == (
        "data.reviewTaskSummary.reviewPriorityQueue"
    )
    assert "reasonCode" in review_summary_contract["reviewPriorityQueue"]["itemFields"]
    assert "providerQualityTaskSignal" in review_summary_contract["requiredFields"]
    assert "preApproveReviewCheckSignal" in review_summary_contract["requiredFields"]
    assert "providerQualitySummary" in review_summary_contract["reviewPriorityQueue"]["itemFields"]
    provider_quality_contract = review_summary_contract["providerQualityTaskSignal"]
    assert provider_quality_contract["dataPath"] == "data.reviewTaskSummary.providerQualityTaskSignal"
    assert provider_quality_contract["source"] == "reviewDetail.reviewPage.providerSummary.qualitySummary"
    assert provider_quality_contract["autoApproveAllowed"] is False
    assert provider_quality_contract["batchStateChangeAllowed"] is False
    assert provider_quality_contract["realPublishAllowed"] is False
    provider_quality_item_contract = review_summary_contract["reviewPriorityQueue"]["providerQualitySummary"]
    assert provider_quality_item_contract["source"] == "reviewDetail.reviewPage.providerSummary.qualitySummary"
    assert provider_quality_item_contract["autoPublishAllowed"] is False
    assert provider_quality_item_contract["realPublishAllowed"] is False
    assert "manualReviewChecklistSummary" in review_summary_contract["reviewPriorityQueue"]["itemFields"]
    assert "controlledGradingEvidenceSummary" in review_summary_contract["reviewPriorityQueue"]["itemFields"]
    assert "mergedGradingEvidenceSummary" in review_summary_contract["reviewPriorityQueue"]["itemFields"]
    assert "preApproveReviewCheck" in review_summary_contract["reviewPriorityQueue"]["itemFields"]
    checklist_contract = review_summary_contract["reviewPriorityQueue"]["manualReviewChecklistSummary"]
    assert checklist_contract["source"] == "reviewDetail.assessmentPlan.manualReviewChecklist"
    assert checklist_contract["autoApproveAllowed"] is False
    assert checklist_contract["batchStateChangeAllowed"] is False
    assert checklist_contract["realSandboxRunEnabled"] is False
    assert checklist_contract["realPublishAllowed"] is False
    controlled_summary_contract = review_summary_contract["reviewPriorityQueue"]["controlledGradingEvidenceSummary"]
    assert controlled_summary_contract["source"] == "reviewDetail.controlledGradingEvidence"
    assert controlled_summary_contract["autoApproveAllowed"] is False
    assert controlled_summary_contract["batchStateChangeAllowed"] is False
    assert controlled_summary_contract["realPublishAllowed"] is False
    merged_summary_contract = review_summary_contract["reviewPriorityQueue"]["mergedGradingEvidenceSummary"]
    assert merged_summary_contract["source"] == "reviewDetail.mergedGradingEvidence"
    assert "coverageRatio" in merged_summary_contract["itemFields"]
    assert "checkEvidenceReviewItemTotal" in merged_summary_contract["itemFields"]
    assert "manualCheckReviewTotal" in merged_summary_contract["itemFields"]
    assert "checkEvidenceReviewItems" in merged_summary_contract["itemFields"]
    assert merged_summary_contract["checkEvidenceReviewItems"]["source"] == (
        "reviewDetail.mergedGradingEvidence.checkEvidenceReviewItems"
    )
    assert merged_summary_contract["checkEvidenceReviewItems"]["autoApproveAllowed"] is False
    assert "mergeExecutedOnlyExistingReports" in merged_summary_contract["itemFields"]
    assert merged_summary_contract["autoApproveAllowed"] is False
    assert merged_summary_contract["batchStateChangeAllowed"] is False
    assert merged_summary_contract["realPublishAllowed"] is False
    precheck_item_contract = review_summary_contract["reviewPriorityQueue"]["preApproveReviewCheck"]
    assert precheck_item_contract["source"] == (
        "reviewDetail.mergedGradingEvidence + reviewDetail.reviewDecisionNotes"
    )
    assert precheck_item_contract["blocking"] is False
    assert precheck_item_contract["approvalStillAllowed"] is True
    assert "summary.approveReadyDecision" in precheck_item_contract["itemFields"]
    assert precheck_item_contract["autoApproveAllowed"] is False
    assert precheck_item_contract["batchStateChangeAllowed"] is False
    assert precheck_item_contract["realPublishAllowed"] is False
    assert review_summary_contract["reviewPriorityQueue"]["autoApproveAllowed"] is False
    assert review_summary_contract["reviewPriorityQueue"]["batchStateChangeAllowed"] is False
    precheck_signal_contract = review_summary_contract["preApproveReviewCheckSignal"]
    assert precheck_signal_contract["dataPath"] == "data.reviewTaskSummary.preApproveReviewCheckSignal"
    assert precheck_signal_contract["source"] == (
        "reviewTaskSummary.reviewPriorityQueue.items[].preApproveReviewCheck"
    )
    assert precheck_signal_contract["blocking"] is False
    assert precheck_signal_contract["approvalStillAllowed"] is True
    assert precheck_signal_contract["autoApproveAllowed"] is False
    assert precheck_signal_contract["batchStateChangeAllowed"] is False
    assert precheck_signal_contract["realPublishAllowed"] is False
    assert "mergedGradingEvidenceReviewSignal" in review_summary_contract["requiredFields"]
    merged_signal_contract = review_summary_contract["mergedGradingEvidenceReviewSignal"]
    assert merged_signal_contract["dataPath"] == "data.reviewTaskSummary.mergedGradingEvidenceReviewSignal"
    assert merged_signal_contract["source"] == "reviewDetail.mergedGradingEvidence"
    assert merged_signal_contract["dynamicSource"] == "reviewDetail.mergedGradingEvidence"
    assert merged_signal_contract["noReportSourceMode"] == "NO_MERGED_EVIDENCE_REPORT"
    assert merged_signal_contract["dynamicSourceMode"] == "DYNAMIC_MERGED_GRADING_EVIDENCE"
    assert merged_signal_contract["recommendedActionWhenMissing"] == "run_grade_evidence_merge_before_final_grading_review"
    assert merged_signal_contract["recommendedActionWhenAvailable"] == "review_merged_grading_evidence_before_approval"
    assert "coverageRatio" in merged_signal_contract["requiredFields"]
    assert "checkEvidenceReviewItemTotal" in merged_signal_contract["requiredFields"]
    assert "manualCheckReviewTotal" in merged_signal_contract["requiredFields"]
    assert merged_signal_contract["mergeExecutedOnlyExistingReports"] is True
    assert merged_signal_contract["autoApproveAllowed"] is False
    assert merged_signal_contract["batchStateChangeAllowed"] is False
    assert merged_signal_contract["realPublishAllowed"] is False
    assert merged_signal_contract["hostExecutionAllowed"] is False
    assert merged_signal_contract["networkAllowed"] is False
    assert tools["get_review_detail"]["safety"]["autoPublishAllowed"] is False
    assert tools["get_review_detail"]["safety"]["realPublish"] is False
    assert tools["get_review_detail"]["safety"]["answerVisibleToCandidate"] is False
    assert tools["get_review_detail"]["safety"]["includesReviewPageModel"] is True
    assert tools["request_review_revision"]["backend"]["path"] == "/api/review-tasks/{taskId}/revision-request"
    assert tools["request_review_revision"]["reviewRequired"] is False
    assert tools["request_review_revision"]["inputSchema"]["required"] == ["taskId", "reviewer", "comment"]
    assert tools["request_review_revision"]["inputSchema"]["properties"]["priority"]["enum"] == ["LOW", "NORMAL", "HIGH"]
    assert tools["request_review_revision"]["safety"]["taskStatusChanged"] is False
    assert tools["request_review_revision"]["safety"]["newLlmRequestSent"] is False
    assert tools["request_review_revision"]["safety"]["realLlmCalled"] is False
    assert tools["request_review_revision"]["safety"]["autoPublishAllowed"] is False
    assert tools["request_review_revision"]["outputContract"]["statusChangeAllowed"] is False
    assert tools["regenerate_from_revision_mock"]["backend"]["path"] == "/api/review-tasks/{taskId}/regenerate-mock"
    assert tools["regenerate_from_revision_mock"]["reviewRequired"] is True
    assert tools["regenerate_from_revision_mock"]["safety"]["defaultGeneratedStatus"] == "WAITING_REVIEW"
    assert tools["regenerate_from_revision_mock"]["safety"]["sourceTaskStatusChanged"] is False
    assert tools["regenerate_from_revision_mock"]["safety"]["newLlmRequestSent"] is False
    assert tools["regenerate_from_revision_mock"]["safety"]["realLlmCalled"] is False
    assert tools["regenerate_from_revision_mock"]["safety"]["realPublish"] is False
    assert tools["regenerate_from_revision_mock"]["outputContract"]["newTaskStatus"] == "WAITING_REVIEW"
    assert tools["regenerate_from_revision_mock"]["outputContract"]["sourceTaskStatusUnchanged"] is True
    assert tools["get_second_confirmation_status"]["backend"]["path"] == "/api/review-tasks/{taskId}/second-confirmation-status"
    assert tools["get_second_confirmation_status"]["riskLevel"] == "critical"
    assert tools["get_second_confirmation_status"]["reviewRequired"] is False
    assert tools["get_second_confirmation_status"]["inputSchema"]["required"] == ["taskId"]
    assert tools["get_second_confirmation_status"]["safety"]["readOnly"] is True
    assert tools["get_second_confirmation_status"]["safety"]["requiresSecondConfirmation"] is True
    assert tools["get_second_confirmation_status"]["safety"]["secondConfirmationSatisfied"] is False
    assert tools["get_second_confirmation_status"]["safety"]["confirmationActionAvailable"] is False
    assert tools["get_second_confirmation_status"]["safety"]["confirmationEndpointEnabled"] is False
    assert tools["get_second_confirmation_status"]["safety"]["executeRealActionAllowed"] is False
    assert tools["get_second_confirmation_status"]["safety"]["destroyRealEnvironmentEnabled"] is False
    assert tools["get_second_confirmation_status"]["safety"]["environmentDestroyed"] is False
    assert tools["get_second_confirmation_status"]["safety"]["realCloudResourceChanged"] is False
    assert tools["get_second_confirmation_status"]["safety"]["bypassReviewEnabled"] is False
    assert tools["list_operation_audit_events"]["safety"]["realCloudResourceChanged"] is False
    assert tools["list_operation_audit_events"]["safety"]["contestantCodeExecuted"] is False
    assert tools["list_workflow_runs"]["safety"]["realLlmCalled"] is False
    assert tools["list_workflow_runs"]["safety"]["sandboxExecuted"] is False
    assert tools["list_artifacts"]["safety"]["realPublish"] is False
    assert tools["list_artifacts"]["safety"]["realLlmCalled"] is False
    assert tools["get_artifact"]["safety"]["contestantCodeExecuted"] is False
    assert tools["get_workflow_run"]["safety"]["realPublish"] is False
    assert tools["list_workflows"]["backend"]["path"] == "/api/workflow-registry"
    assert tools["list_workflows"]["safety"]["workflowExecuted"] is False
    assert tools["list_workflows"]["safety"]["taskCreated"] is False
    assert tools["list_workflows"]["safety"]["artifactCreated"] is False
    assert tools["get_workflow"]["backend"]["path"] == "/api/workflow-registry/{workflowId}"
    assert tools["get_workflow"]["inputSchema"]["required"] == ["workflowId"]
    assert tools["get_workflow"]["safety"]["workflowExecuted"] is False
    assert tools["get_workflow"]["safety"]["taskCreated"] is False
    assert tools["get_workflow"]["safety"]["artifactCreated"] is False
    assert tools["create_vm_environment"]["safety"]["realCloudResourceCreated"] is False
    assert tools["create_notebook_environment"]["safety"]["realCloudResourceCreated"] is False
    assert tools["publish_lab"]["backend"]["path"] == "/api/mcp/intents/publish-lab"
    assert tools["publish_lab"]["safety"]["reviewIntentOnly"] is True
    assert tools["publish_lab"]["safety"]["realPublish"] is False
    assert tools["publish_lab"]["safety"]["autoPublishAllowed"] is False
    assert tools["publish_exam"]["backend"]["path"] == "/api/mcp/intents/publish-exam"
    assert tools["publish_exam"]["safety"]["reviewIntentOnly"] is True
    assert tools["publish_exam"]["safety"]["realPublish"] is False
    assert tools["destroy_environment"]["backend"]["path"] == "/api/mcp/intents/destroy-environment"
    assert tools["destroy_environment"]["riskLevel"] == "critical"
    assert tools["destroy_environment"]["safety"]["requiresSecondConfirmation"] is True
    assert tools["destroy_environment"]["safety"]["realCloudResourceChanged"] is False
    assert tools["destroy_environment"]["safety"]["environmentDestroyed"] is False
    assert tools["list_providers"]["safety"]["realLlmCalled"] is False
    assert tools["list_providers"]["safety"]["secretsRead"] is False
    assert tools["list_providers"]["safety"]["networkAccess"] is False
    assert tools["get_provider_health"]["safety"]["activeProvider"] == "mock"
    assert tools["mock_provider_generate"]["safety"]["realLlmCalled"] is False
    assert tools["list_provider_audit_events"]["backend"]["path"] == "/api/provider-audit-events"
    assert tools["list_provider_audit_events"]["safety"]["realMcpServerStarted"] is False
    assert tools["list_provider_audit_events"]["safety"]["realAgentStarted"] is False
    assert tools["list_provider_audit_events"]["safety"]["autoPublishAllowed"] is False
    assert tools["list_mcp_tool_call_records"]["backend"]["path"] == "/api/mcp-tool-call-records"
    assert tools["list_mcp_tool_call_records"]["safety"]["realMcpServerStarted"] is False
    assert tools["list_mcp_tool_call_records"]["safety"]["realAgentStarted"] is False
    assert tools["list_mcp_tool_call_records"]["safety"]["argumentPreviewRedactsSecrets"] is True


def test_mcp_tool_call_audit_contract_is_mock_only():
    contract = load_tool_call_audit_contract()

    assert contract["phase"] == "Phase 1"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["storeKey"] == "mcpToolCallRecords"
    assert "SUCCESS" in contract["recordSchema"]["statusValues"]
    assert "FAILED" in contract["recordSchema"]["statusValues"]
    assert contract["recordSchema"]["argumentPolicy"]["storeRawArguments"] is False
    assert contract["recordSchema"]["argumentPolicy"]["storeRedactedPreview"] is True
    assert contract["safetyAssertions"]["realMcpServerStarted"] is False
    assert contract["safetyAssertions"]["realAgentStarted"] is False
    assert contract["safetyAssertions"]["realLlmCalled"] is False
    assert "test_mcp_mock_tools" in contract["recommendedCommandIds"]


def test_mcp_server_contract_is_phase4_mock_only():
    contract = load_server_contract()

    assert contract["phase"] == "Phase 4"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["server"]["protocol"] == "mcp-server-mock"
    assert contract["server"]["transport"] == "local_function_only"
    assert contract["capabilities"]["initialize"] is True
    assert contract["capabilities"]["listTools"] is True
    assert contract["capabilities"]["callTool"] is True
    assert contract["capabilities"]["streaming"] is False
    assert contract["toolPolicy"]["toolsCallBackendMockOnly"] is True
    assert contract["toolPolicy"]["defaultToolProfile"] == "local-core-mvp"
    assert contract["toolPolicy"]["directInvocationDefaultProfile"] == "local-core-mvp"
    assert contract["toolPolicy"]["allToolsProfile"] == "all"
    assert contract["toolPolicy"]["realPlatformBackendToolsEnabledByDefault"] is False
    assert contract["toolPolicy"]["returnsUnifiedJson"] is True
    assert contract["toolPolicy"]["auditRequired"] is True
    assert contract["safetyAssertions"]["realMcpServerStarted"] is False
    assert contract["safetyAssertions"]["realAgentStarted"] is False
    assert contract["safetyAssertions"]["networkListenerStarted"] is False
    assert "python lab_cli.py mcp stdio-smoke --input examples/input/demo-source.md --output examples/output/mcp-stdio-client-smoke.json" in contract["entrypoints"]["cli"]
    assert contract["stdioSafetyAssertions"]["stdioTransportStarted"] is True
    assert contract["stdioSafetyAssertions"]["networkListenerStarted"] is False
    assert "test_mcp_server_mock" in contract["recommendedCommandIds"]
    assert "test_mcp_stdio_client_smoke" in contract["recommendedCommandIds"]


def test_mcp_local_core_client_usage_doc_defines_default_profile_and_stop_line():
    content = read_text("docs/27_MCP_LOCAL_CORE_CLIENT_USAGE.md")
    example_config = read_text("examples/mcp/local-core-mcp.json")
    readme = read_text("mcp-server/README.md")
    spec = read_text("docs/07_MCP_SPEC.md")
    progress = read_text("docs/24_PROJECT_PROGRESS_MAP.md")

    assert "# 27_MCP_LOCAL_CORE_CLIENT_USAGE" in content
    assert '"command": "python"' in content
    assert '"args": ["-m", "mcp_server.stdio_server"]' in content
    assert '"cwd": "<PROJECT_ROOT>"' in content
    assert '"command": "python"' in example_config
    assert '"args": ["-m", "mcp_server.stdio_server"]' in example_config
    assert '"cwd": "<PROJECT_ROOT>"' in example_config
    assert "D:\\\\NanJing" not in content
    assert "D:\\\\NanJing" not in example_config
    assert "local-core-mvp" in content
    assert "invoke_mcp_tool()" in content
    assert "get_real_llm_runtime_config" in content
    assert "analyze_material" in content
    assert "generate_lab_from_source" in content
    assert "run_grading_evidence_auto" in content
    assert "record_review_decision_note" in content
    assert "create_agent_entity_import_dry_run" in content
    assert "WAITING_REVIEW" in content
    assert "LOCAL_CORE_MVP_STOP_LINE_REACHED" in content
    assert "REAL_PLATFORM_BACKEND_PAUSED" in content
    assert "MCP_TOOL_NOT_IN_PROFILE" in content
    assert "Do not configure `AGENT_API_TOKEN`" in content
    assert "Do not work around it by asking for platform API base URL or platform token" in content
    assert "Stop at `create_agent_entity_import_dry_run`" in content
    assert "mcp stdio-local-core-demo" in content
    assert "agent_internal_publish_request" in content
    assert "query_agent_publish_status" not in content
    assert "auto approve" in content
    assert "publish" in content
    assert "docs/27_MCP_LOCAL_CORE_CLIENT_USAGE.md" in readme
    assert "docs/27_MCP_LOCAL_CORE_CLIENT_USAGE.md" in spec
    assert "docs/27_MCP_LOCAL_CORE_CLIENT_USAGE.md" in progress
