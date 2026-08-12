import json

from backend.agent_entity_service import BackendAgentEntityService, BackendAgentEntityServiceError
from backend.core_service import BackendCoreService
from cli.artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from cli.audit import OperationAction, OperationResourceType, create_operation_audit_event
from cli.grading_record import GradingRecord, GradingRecordStatus
from cli.agent_entity import AgentEntityType, create_agent_entity_record
from cli.store import JsonTaskStore


def _seed_agent_entity(store: JsonTaskStore):
    entity = create_agent_entity_record(
        entity_type=AgentEntityType.LAB_TEMPLATE,
        title="Service Lab Template",
        payload={"title": "Service Lab Template"},
        source_task_id="task_agent_entity_service_001",
        source_preview_artifact_id="artifact_preview_001",
        source_preview_path="examples/output/lab-template-import-preview.json",
        reviewer="teacher_1",
        trace_id="trace_agent_entity_service",
        source_dsl_path="examples/output/real-llm-lab.json",
        source_artifact_id="artifact_lab_dsl_001",
        source_artifact_kind="LAB_DSL",
    )
    store.save_agent_entity(entity)
    dry_run_artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path="examples/output/platform-entity-import-dry-run.json",
        title="Platform Entity Import Dry Run",
        status=ArtifactStatus.COMPLETED,
        trace_id=entity.traceId,
        metadata={
            "component": "AgentEntityImportDryRun",
            "agentEntityId": entity.id,
            "entityType": entity.entityType.value,
            "agentEntity": entity.entityType.value,
        },
        mode="LOCAL_PLATFORM_IMPORT_DRY_RUN",
    )
    store.save_artifact(dry_run_artifact)
    operation_event = create_operation_audit_event(
        action=OperationAction.PLATFORM_ENTITY_IMPORT_DRY_RUN,
        resource_type=OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor="teacher_1",
        trace_id=entity.traceId,
        detail={
            "artifactId": dry_run_artifact.id,
            "outputPath": dry_run_artifact.path,
            "requestSent": False,
            "networkAccess": False,
            "realPublish": False,
        },
    )
    store.save_operation_audit_event(operation_event)
    return entity, dry_run_artifact, operation_event


def _seed_grading_rule_agent_entity(store: JsonTaskStore):
    entity = create_agent_entity_record(
        entity_type=AgentEntityType.GRADING_RULE,
        title="Service Grading Rule",
        payload={"title": "Service Grading Rule"},
        source_task_id="task_platform_grading_service_001",
        source_preview_artifact_id="artifact_grading_preview_001",
        source_preview_path="examples/output/grading-rule-import-preview.json",
        reviewer="teacher_1",
        trace_id="trace_platform_grading_service",
        source_dsl_path="examples/output/real-llm-grading.json",
        source_artifact_id="artifact_grading_dsl_001",
        source_artifact_kind="GRADING_DSL",
    )
    store.save_agent_entity(entity)
    preview_artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path="examples/output/grading-rule-import-preview.json",
        title="Grading Rule Import Preview",
        status=ArtifactStatus.COMPLETED,
        trace_id=entity.traceId,
        task_id=entity.sourceTaskId,
        metadata={
            "component": "GradingRuleImportPreview",
            "agentEntity": "grading_rule",
        },
        mode="LOCAL_PLATFORM_IMPORT_PREVIEW",
    )
    mock_import_artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path="examples/output/grading-rule-mock-import.json",
        title="Grading Rule Mock Import",
        status=ArtifactStatus.COMPLETED,
        trace_id=entity.traceId,
        task_id=entity.sourceTaskId,
        metadata={
            "component": "GradingRuleMockImport",
            "agentEntity": "grading_rule",
            "agentEntityId": entity.id,
        },
        mode="LOCAL_PLATFORM_ENTITY_MOCK_IMPORT",
    )
    store.save_artifact(preview_artifact)
    store.save_artifact(mock_import_artifact)
    return entity


def test_backend_agent_entity_service_lists_entities_with_filters(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity, _artifact, _event = _seed_agent_entity(store)
    service = BackendAgentEntityService(store=store)

    result = service.list_entities(
        {
            "entityType": "lab_template",
            "sourceTaskId": entity.sourceTaskId,
            "traceId": entity.traceId,
        }
    )

    assert result["mode"] == "MOCK_ONLY"
    assert result["total"] == 1
    assert result["items"][0]["id"] == entity.id
    assert result["filters"]["entityType"] == "lab_template"
    assert result["databaseWritten"] is False
    assert result["realAgentImport"] is False


def test_backend_agent_entity_service_rejects_invalid_entity_type(tmp_path):
    service = BackendAgentEntityService(store=JsonTaskStore(tmp_path / "store.json"))

    try:
        service.list_entities({"entityType": "bad_entity"})
    except BackendAgentEntityServiceError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors == [{"field": "entityType", "reason": "非法实体类型"}]
    else:
        raise AssertionError("expected BackendAgentEntityServiceError")


def test_backend_agent_entity_service_gets_entity_with_import_activity(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity, artifact, event = _seed_agent_entity(store)
    service = BackendAgentEntityService(store=store)

    result = service.get_entity(entity.id)

    activity = result["agentEntityImportActivity"]
    assert result["agentEntityRecord"]["id"] == entity.id
    assert result["mode"] == "MOCK_ONLY"
    assert activity["component"] == "AgentEntityImportActivitySummary"
    assert activity["dryRunTotal"] == 1
    assert activity["artifactTotal"] == 1
    assert activity["latestDryRun"]["id"] == event.id
    assert activity["artifacts"][0]["id"] == artifact.id
    assert activity["summary"]["dryRunPrepared"] is True
    assert activity["safety"]["readOnly"] is True


def test_backend_agent_entity_service_get_missing_entity(tmp_path):
    service = BackendAgentEntityService(store=JsonTaskStore(tmp_path / "store.json"))

    try:
        service.get_entity("agent_entity_missing")
    except BackendAgentEntityServiceError as exc:
        assert exc.code == "NOT_FOUND"
        assert exc.errors == [{"field": "id", "reason": "未找到实体"}]
    else:
        raise AssertionError("expected BackendAgentEntityServiceError")


def test_backend_agent_entity_service_builds_readiness_report(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity, _artifact, _event = _seed_agent_entity(store)
    service = BackendAgentEntityService(store=store)

    result = service.readiness_report({"sourceTaskId": entity.sourceTaskId})
    report = result["agentEntityReadinessReport"]

    assert report["component"] == "AgentEntityReadinessReport"
    assert report["sourceTaskId"] == entity.sourceTaskId
    assert report["summary"]["mockImportCreatedTotal"] == 0
    assert report["items"][0]["agentEntityId"] == entity.id
    assert report["safety"]["readOnly"] is True


def test_backend_agent_entity_service_readiness_includes_grading_record_review_evidence(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity = _seed_grading_rule_agent_entity(store)
    record = GradingRecord(
        submissionId="submission_grading_readiness_001",
        gradingId="grading_rule_service_001",
        reportPath="examples/output/grading-evidence-auto.json",
        reportMode="GRADING_EVIDENCE_AUTO",
        status=GradingRecordStatus.READY_FOR_HUMAN_REVIEW,
        totalScore=100,
        earnedScore=90,
        coveredScore=100,
        missingScore=0,
        coverageRatio=1.0,
        taskId=entity.sourceTaskId,
        candidateId="candidate_grading_readiness_001",
        reviewer="teacher_1",
        scorePreviewStatus="READY_FOR_DECISION_NOTE",
        decisionNoteRecommendation="approve-ready",
        manualReviewChecklistStatus="READY_FOR_DECISION",
    )
    store.save_grading_record(record)
    service = BackendAgentEntityService(store=store)

    waiting = service.readiness_report({"sourceTaskId": entity.sourceTaskId})["agentEntityReadinessReport"]
    waiting_item = next(item for item in waiting["items"] if item["agentEntity"] == "grading_rule")
    waiting_evidence = waiting_item["gradingRecordReviewEvidence"]

    assert waiting_item["readyForManualAgentReview"] is True
    assert waiting_evidence["applicable"] is True
    assert waiting_evidence["state"] == "WAITING_GRADING_RECORD_REVIEW"
    assert waiting_evidence["readyForAgentReview"] is False
    assert waiting_evidence["latestRecordId"] == record.id
    assert waiting_evidence["reviewCommand"].startswith("python lab_cli.py grade record-review")
    assert waiting["summary"]["gradingRecordReviewApplicableTotal"] == 1
    assert waiting["summary"]["gradingRecordReviewReadyTotal"] == 0
    assert waiting["summary"]["gradingRecordReviewBlockedTotal"] == 1

    record.status = GradingRecordStatus.HUMAN_APPROVED
    record.reviewDecision = "approve-ready"
    record.reviewedBy = "teacher_2"
    record.reviewedAt = "2026-06-30T00:00:00Z"
    store.save_grading_record(record)
    ready = service.readiness_report({"sourceTaskId": entity.sourceTaskId})["agentEntityReadinessReport"]
    ready_item = next(item for item in ready["items"] if item["agentEntity"] == "grading_rule")
    ready_evidence = ready_item["gradingRecordReviewEvidence"]

    assert ready_evidence["state"] == "READY_FOR_PLATFORM_REVIEW"
    assert ready_evidence["readyForAgentReview"] is True
    assert ready_evidence["latestReviewedBy"] == "teacher_2"
    assert ready_evidence["nextRequiredAction"] == "continue_platform_review_after_grading_record_approved"
    assert ready_evidence["reviewCommand"] is None
    assert ready["summary"]["gradingRecordReviewApplicableTotal"] == 1
    assert ready["summary"]["gradingRecordReviewReadyTotal"] == 1
    assert ready["summary"]["gradingRecordReviewBlockedTotal"] == 0


def test_backend_agent_entity_service_builds_import_dry_run(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity, _artifact, _event = _seed_agent_entity(store)
    service = BackendAgentEntityService(store=store, root=tmp_path)

    result = service.build_publish_preview(
        entity.id,
        {"reviewer": "teacher_2", "output": "service-dry-run.json"},
        trace_id="trace_service_dry_run",
    )

    output = tmp_path / "service-dry-run.json"
    dry_run = result["agentEntityImportDryRun"]
    assert output.exists()
    assert dry_run["component"] == "AgentEntityImportDryRun"
    assert dry_run["agentEntityId"] == entity.id
    assert dry_run["platformApiContract"]["contractVersion"] == "platform-import-contract/v1"
    assert dry_run["platformApiContract"]["draftImportEndpoint"] == dry_run["targetEndpoint"]
    assert dry_run["requestPreview"]["entityType"] == "lab_template"
    assert dry_run["safety"]["requestSent"] is False
    assert dry_run["safety"]["realAgentImport"] is False
    assert result["artifact"]["mode"] == "REAL_PLATFORM_IMPORT_DRY_RUN_ONLY"
    assert result["operationAuditEvent"]["action"] == "PLATFORM_ENTITY_IMPORT_DRY_RUN"


def test_backend_agent_entity_service_builds_import_dry_run_with_contract_config(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity, _artifact, _event = _seed_agent_entity(store)
    config = tmp_path / "platform-contract.json"
    config.write_text(
        json.dumps(
            {
                "entities": {
                    "lab_template": {
                        "draftImportPath": "/open/lab-imports",
                        "statusPathTemplate": "/open/lab-imports/{agentDraftId}/status",
                        "requestBodyMapping": {
                            "lab.title": {"source": "payload.title", "required": True},
                            "lab.duration": "payload.durationMinutes",
                            "workflow.idempotencyKey": "idempotencyKey",
                            "review.status": {"value": "PENDING_MANUAL_PLATFORM_REVIEW"},
                        },
                    }
                },
                "draftIdResponseKeys": ["jobId"],
                "statusResponseKeys": ["reviewState"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = BackendAgentEntityService(store=store, root=tmp_path)

    result = service.build_publish_preview(
        entity.id,
        {"reviewer": "teacher_2", "output": "service-dry-run.json", "contractConfig": "platform-contract.json"},
        trace_id="trace_service_contract_dry_run",
    )

    dry_run = result["agentEntityImportDryRun"]
    assert dry_run["targetEndpoint"] == {"method": "POST", "path": "/open/lab-imports"}
    assert dry_run["platformApiContract"]["configApplied"] is True
    assert dry_run["platformApiContract"]["statusPathTemplate"] == "/open/lab-imports/{agentDraftId}/status"
    assert dry_run["platformApiContract"]["draftIdResponseKeys"] == ["jobId"]
    assert dry_run["platformApiContract"]["statusResponseKeys"] == ["reviewState"]
    assert dry_run["platformApiContract"]["requestBodyMapping"]["configured"] is True
    assert dry_run["requestBodyMapping"]["mode"] == "CONFIGURED_FIELD_MAPPING"
    assert dry_run["requestBody"]["lab"]["title"] == "Service Lab Template"
    assert dry_run["requestBody"]["workflow"]["idempotencyKey"] == f"dryrun:{entity.id}"
    assert dry_run["requestBody"]["review"]["status"] == "PENDING_MANUAL_PLATFORM_REVIEW"
    assert dry_run["validation"]["requestBodyMappingConfigured"] is True
    assert dry_run["validation"]["requestBodyReady"] is True


def test_backend_agent_entity_service_builds_import_dry_run_from_repository(tmp_path):
    source_store = JsonTaskStore(tmp_path / "source-store.json")
    entity, _artifact, _event = _seed_agent_entity(source_store)
    core_service = BackendCoreService(tmp_path)
    repository, write_summary = core_service.prepare_write_through({"coreDbPath": str(tmp_path / "core.sqlite3")})
    assert repository is not None
    repository.initialize_schema()
    repository.save_agent_entity(entity)
    service = BackendAgentEntityService(store=JsonTaskStore(tmp_path / "empty-store.json"), root=tmp_path)

    result = service.build_publish_preview_from_repository(
        entity.id,
        {"reviewer": "teacher_2", "output": "repository-dry-run.json"},
        trace_id="trace_service_repository_dry_run",
        repository=repository,
        write_summary=write_summary,
    )

    summary = result["backendCoreAgentEntityImportDryRun"]
    assert (tmp_path / "repository-dry-run.json").exists()
    assert result["agentEntityImportDryRun"]["agentEntityId"] == entity.id
    assert result["agentEntityImportDryRun"]["requestPreview"]["entityType"] == "lab_template"
    assert summary["repositoryContractUsed"] is True
    assert summary["agentEntityRead"] is True
    assert summary["jsonStoreSourceRead"] is False
    assert summary["artifactWritten"] is True
    assert summary["operationAuditEventWritten"] is True
    assert summary["localSqliteWritten"] is True
    assert core_service.list_artifact_payloads(repository, task_id=entity.sourceTaskId)[0]["id"] == result["artifact"]["id"]
    assert core_service.list_operation_audit_event_payloads(
        repository,
        resource_type="PLATFORM_ENTITY",
        resource_id=entity.id,
    )[0]["id"] == result["operationAuditEvent"]["id"]


def test_backend_agent_entity_service_send_import_rejects_invalid_timeout(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity, _artifact, _event = _seed_agent_entity(store)
    service = BackendAgentEntityService(store=store, root=tmp_path)

    try:
        service.publish_entity(
            entity.id,
            {"reviewer": "teacher_2", "timeoutSeconds": "bad"},
            trace_id="trace_service_bad_send_timeout",
        )
    except BackendAgentEntityServiceError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors == [{"field": "timeoutSeconds", "reason": "必须是整数"}]
    else:
        raise AssertionError("expected BackendAgentEntityServiceError")


def test_backend_agent_entity_service_send_import_rejects_invalid_max_retries(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity, _artifact, _event = _seed_agent_entity(store)
    service = BackendAgentEntityService(store=store, root=tmp_path)

    try:
        service.publish_entity(
            entity.id,
            {"reviewer": "teacher_2", "maxRetries": -1},
            trace_id="trace_service_bad_send_retries",
        )
    except BackendAgentEntityServiceError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors == [{"field": "maxRetries", "reason": "必须大于等于 0"}]
    else:
        raise AssertionError("expected BackendAgentEntityServiceError")


def test_backend_agent_entity_service_query_status_rejects_invalid_timeout(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity, _artifact, _event = _seed_agent_entity(store)
    service = BackendAgentEntityService(store=store, root=tmp_path)

    try:
        service.query_publish_status(
            entity.id,
            {"reviewer": "teacher_2", "timeoutSeconds": "bad"},
            trace_id="trace_service_bad_status_timeout",
        )
    except BackendAgentEntityServiceError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors == [{"field": "timeoutSeconds", "reason": "必须是整数"}]
    else:
        raise AssertionError("expected BackendAgentEntityServiceError")


def test_backend_agent_entity_service_query_status_rejects_invalid_max_retries(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity, _artifact, _event = _seed_agent_entity(store)
    service = BackendAgentEntityService(store=store, root=tmp_path)

    try:
        service.query_publish_status(
            entity.id,
            {"reviewer": "teacher_2", "maxRetries": "bad"},
            trace_id="trace_service_bad_status_retries",
        )
    except BackendAgentEntityServiceError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors == [{"field": "maxRetries", "reason": "必须是整数"}]
    else:
        raise AssertionError("expected BackendAgentEntityServiceError")


def test_backend_agent_entity_service_records_import_result(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity, _artifact, _event = _seed_agent_entity(store)
    service = BackendAgentEntityService(store=store, root=tmp_path)
    send_report = tmp_path / "send.json"
    send_report.write_text(
        json.dumps(
            {
                "component": "AgentEntityImportSendResult",
                "mode": "REAL_PLATFORM_IMPORT_REQUEST_SENT",
                "agentEntityId": entity.id,
                "entityType": "lab_template",
                "response": {"ok": True, "statusCode": 202, "body": {"json": {"draftImportId": "draft_service"}}},
                "request": {"idempotencyKey": "dryrun:service"},
                "targetEndpoint": {"method": "POST", "path": "/api/platform/lab-template/draft-imports"},
                "safety": {"requestSent": True},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = service.record_publish_result(
        entity.id,
        {
            "reviewer": "teacher_3",
            "sendResult": "send.json",
            "agentStatus": "ACCEPTED_FOR_DRAFT",
            "output": "service-result.json",
        },
        trace_id="trace_service_result",
    )

    output = tmp_path / "service-result.json"
    record = result["agentEntityImportResultRecord"]
    assert output.exists()
    assert record["component"] == "AgentEntityImportResultRecord"
    assert record["agentEntityId"] == entity.id
    assert record["agentDraftId"] == "draft_service"
    assert record["agentStatus"] == "ACCEPTED_FOR_DRAFT"
    assert result["agentEntityRecord"]["status"] == "REAL_IMPORT_DRAFT_ACCEPTED"
    assert result["artifact"]["mode"] == "LOCAL_PLATFORM_IMPORT_RESULT_RECORD"
    assert result["operationAuditEvent"]["action"] == "PLATFORM_ENTITY_IMPORT_RESULT_RECORD"


def test_backend_agent_entity_service_records_import_result_from_repository(tmp_path):
    source_store = JsonTaskStore(tmp_path / "source-store.json")
    entity, _artifact, _event = _seed_agent_entity(source_store)
    core_service = BackendCoreService(tmp_path)
    repository, write_summary = core_service.prepare_write_through({"coreDbPath": str(tmp_path / "core.sqlite3")})
    assert repository is not None
    repository.initialize_schema()
    repository.save_agent_entity(entity)
    service = BackendAgentEntityService(store=JsonTaskStore(tmp_path / "empty-store.json"), root=tmp_path)
    send_report = tmp_path / "repository-send.json"
    send_report.write_text(
        json.dumps(
            {
                "component": "AgentEntityImportSendResult",
                "mode": "REAL_PLATFORM_IMPORT_REQUEST_SENT",
                "agentEntityId": entity.id,
                "entityType": "lab_template",
                "response": {"ok": True, "statusCode": 202, "body": {"json": {"draftImportId": "draft_repo"}}},
                "request": {"idempotencyKey": "dryrun:repository"},
                "targetEndpoint": {"method": "POST", "path": "/api/platform/lab-template/draft-imports"},
                "safety": {"requestSent": True},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = service.record_publish_result_from_repository(
        entity.id,
        {
            "reviewer": "teacher_3",
            "sendResult": "repository-send.json",
            "agentStatus": "ACCEPTED_FOR_DRAFT",
            "output": "repository-result.json",
        },
        trace_id="trace_service_repository_result",
        repository=repository,
        write_summary=write_summary,
    )

    summary = result["backendCoreAgentEntityImportResult"]
    assert (tmp_path / "repository-result.json").exists()
    assert result["agentEntityImportResultRecord"]["agentEntityId"] == entity.id
    assert result["agentEntityImportResultRecord"]["agentDraftId"] == "draft_repo"
    assert result["agentEntityImportResultRecord"]["safety"]["mockStoreUpdated"] is False
    assert result["agentEntityImportResultRecord"]["safety"]["databaseWrittenByLocalSystem"] is True
    assert result["agentEntityRecord"]["status"] == "REAL_IMPORT_DRAFT_ACCEPTED"
    assert summary["repositoryContractUsed"] is True
    assert summary["agentEntityRead"] is True
    assert summary["agentEntityWritten"] is True
    assert summary["jsonStoreSourceRead"] is False
    assert summary["artifactWritten"] is True
    assert summary["operationAuditEventWritten"] is True
    assert summary["localSqliteWritten"] is True
    stored_entity = repository.get_agent_entity(entity.id)
    assert stored_entity is not None
    assert stored_entity.status.value == "REAL_IMPORT_DRAFT_ACCEPTED"
    assert core_service.list_artifact_payloads(repository, task_id=entity.sourceTaskId)[0]["id"] == result["artifact"]["id"]
    assert core_service.list_operation_audit_event_payloads(
        repository,
        resource_type="PLATFORM_ENTITY",
        resource_id=entity.id,
    )[0]["id"] == result["operationAuditEvent"]["id"]


def test_backend_agent_entity_service_records_signoff_and_final_review_from_repository(tmp_path):
    source_store = JsonTaskStore(tmp_path / "source-store.json")
    entity, _artifact, _event = _seed_agent_entity(source_store)
    core_service = BackendCoreService(tmp_path)
    repository, write_summary = core_service.prepare_write_through({"coreDbPath": str(tmp_path / "core.sqlite3")})
    assert repository is not None
    repository.initialize_schema()
    preview = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path="examples/output/lab-preview.json",
        title="Repository signoff preview",
        status=ArtifactStatus.COMPLETED,
        task_id=entity.sourceTaskId,
        trace_id=entity.traceId,
        metadata={"component": "LabTemplateImportPreview", "agentEntity": "lab_template"},
        mode="LOCAL_PLATFORM_IMPORT_PREVIEW",
    )
    mock_import = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path="examples/output/lab-mock-import.json",
        title="Repository signoff mock import",
        status=ArtifactStatus.COMPLETED,
        task_id=entity.sourceTaskId,
        trace_id=entity.traceId,
        metadata={
            "component": "LabTemplateMockImport",
            "agentEntity": "lab_template",
            "agentEntityId": entity.id,
            "entityType": "lab_template",
        },
        mode="LOCAL_PLATFORM_ENTITY_MOCK_IMPORT",
    )
    accepted_result = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path="examples/output/lab-result.json",
        title="Repository accepted draft result",
        status=ArtifactStatus.READY,
        task_id=entity.sourceTaskId,
        trace_id=entity.traceId,
        metadata={
            "component": "AgentEntityImportResultRecord",
            "agentEntityId": entity.id,
            "entityType": "lab_template",
            "agentDraftId": "draft_repo_signoff",
            "agentStatus": "ACCEPTED_FOR_DRAFT",
        },
        mode="LOCAL_PLATFORM_IMPORT_RESULT_RECORD",
    )
    result_event = create_operation_audit_event(
        action=OperationAction.PLATFORM_ENTITY_IMPORT_RESULT_RECORD,
        resource_type=OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor="teacher_3",
        trace_id=entity.traceId,
        before_state="PUBLISH_PENDING",
        after_state="PUBLISH_ACCEPTED",
        detail={
            "component": "AgentEntityImportResultRecord",
            "artifactId": accepted_result.id,
            "outputPath": accepted_result.path,
            "agentDraftId": "draft_repo_signoff",
            "agentStatus": "ACCEPTED_FOR_DRAFT",
            "agentSideReviewed": True,
            "acceptedForDraft": True,
            "sourceRequestSent": True,
            "requestSent": False,
            "networkAccess": False,
            "databaseWrittenByLocalSystem": True,
            "realPublish": False,
        },
    )
    result_event.mode = "LOCAL_PLATFORM_IMPORT_RESULT_RECORD"
    repository.save_agent_entity(entity)
    repository.save_artifact(preview)
    repository.save_artifact(mock_import)
    repository.save_artifact(accepted_result)
    send_event = create_operation_audit_event(
        action=OperationAction.PLATFORM_ENTITY_IMPORT_SEND,
        resource_type=OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor="teacher_2",
        trace_id=entity.traceId,
        before_state="DRAFT_CREATED",
        after_state="PUBLISH_PENDING",
        detail={
            "component": "AgentEntityImportSendResult",
            "artifactId": "artifact_repo_send",
            "outputPath": "examples/output/lab-send.json",
            "targetEndpoint": {"method": "POST", "path": "/api/platform/lab-template/draft-imports"},
            "statusCode": 202,
            "agentDraftId": "draft_repo_signoff",
            "requestSent": True,
            "networkAccess": True,
            "secretsRead": True,
            "realPublish": False,
        },
    )
    send_event.mode = "REAL_PLATFORM_IMPORT_REQUEST_SENT"
    status_event = create_operation_audit_event(
        action=OperationAction.PLATFORM_ENTITY_IMPORT_STATUS_QUERY,
        resource_type=OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor="teacher_2",
        trace_id=entity.traceId,
        before_state="PUBLISH_PENDING",
        after_state="ACCEPTED_FOR_DRAFT",
        detail={
            "component": "AgentEntityImportStatusQuery",
            "artifactId": "artifact_repo_status",
            "outputPath": "examples/output/lab-status.json",
            "agentDraftId": "draft_repo_signoff",
            "agentStatus": "ACCEPTED_FOR_DRAFT",
            "querySucceeded": True,
            "suggestedImportResultStatus": "ACCEPTED_FOR_DRAFT",
            "requestSent": True,
            "networkAccess": True,
            "secretsRead": True,
            "realPublish": False,
        },
    )
    status_event.mode = "REAL_PLATFORM_IMPORT_STATUS_QUERY"
    repository.save_operation_audit_event(send_event)
    repository.save_operation_audit_event(status_event)
    repository.save_operation_audit_event(result_event)
    service = BackendAgentEntityService(store=JsonTaskStore(tmp_path / "empty-store.json"), root=tmp_path)

    signoff = service.record_signoff_from_repository(
        entity.id,
        {"reviewer": "teacher_4", "output": "repository-signoff.json"},
        trace_id="trace_service_repository_signoff",
        repository=repository,
        write_summary=write_summary,
    )
    assert (tmp_path / "repository-signoff.json").exists()
    assert signoff["agentEntitySignoffRecord"]["readyStateBeforeSignoff"] == "READY_FOR_PLATFORM_ENTITY_SIGNOFF"
    assert signoff["agentEntitySignoffRecord"]["safety"]["mockStoreUpdated"] is False
    assert signoff["agentEntitySignoffRecord"]["safety"]["databaseWrittenByLocalSystem"] is True
    assert signoff["backendCoreAgentEntitySignoff"]["repositoryContractUsed"] is True
    assert signoff["backendCoreAgentEntitySignoff"]["artifactWritten"] is True
    assert signoff["backendCoreAgentEntitySignoff"]["operationAuditEventWritten"] is True

    final_review = service.record_final_publish_review_decision_from_repository(
        entity.id,
        {
            "reviewer": "teacher_5",
            "decision": "NEEDS_REVISION",
            "output": "repository-final-review.json",
            "confirmNoAutoPublish": True,
            "confirmNoRealPublish": True,
            "confirmFinalHumanReview": True,
        },
        trace_id="trace_service_repository_final_review",
        repository=repository,
        write_summary=write_summary,
    )
    assert (tmp_path / "repository-final-review.json").exists()
    assert final_review["finalPublishReviewDecision"]["decision"] == "NEEDS_REVISION"
    assert final_review["finalPublishReviewDecision"]["safety"]["databaseWrittenByLocalSystem"] is True
    assert final_review["backendCoreAgentEntityFinalPublishReviewDecision"]["repositoryContractUsed"] is True
    artifact_ids = {
        item["id"]
        for item in core_service.list_artifact_payloads(repository, task_id=entity.sourceTaskId)
    }
    assert signoff["artifact"]["id"] in artifact_ids
    assert final_review["artifact"]["id"] in artifact_ids


def test_backend_agent_entity_service_wraps_import_result_validation_error(tmp_path):
    store = JsonTaskStore(tmp_path / "store.json")
    entity, _artifact, _event = _seed_agent_entity(store)
    service = BackendAgentEntityService(store=store, root=tmp_path)
    send_report = tmp_path / "send.json"
    send_report.write_text(
        json.dumps(
            {
                "component": "AgentEntityImportSendResult",
                "mode": "REAL_PLATFORM_IMPORT_REQUEST_SENT",
                "agentEntityId": entity.id,
                "safety": {"requestSent": True},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    try:
        service.record_publish_result(
            entity.id,
            {"reviewer": "teacher_3", "sendResult": "send.json", "agentStatus": "BAD_STATUS"},
            trace_id="trace_service_bad_status",
        )
    except BackendAgentEntityServiceError as exc:
        assert exc.code == "VALIDATION_ERROR"
        assert exc.errors == [{"field": "agentStatus", "reason": "不在允许枚举中"}]
    else:
        raise AssertionError("expected BackendAgentEntityServiceError")
