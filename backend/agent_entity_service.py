"""Backend platform entity service.

This service centralizes platform entity HTTP business logic. It owns local
read paths, import record write paths, and explicitly confirmed platform
send/status operations used by the mock backend.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.core_contract import BackendCoreRepositoryContract
from backend.core_repository import CoreRepositoryError
from backend.core_service import BackendCoreService
from cli.artifact import ArtifactRecord
from cli.audit import OperationAuditEvent
from cli.agent_api_contract import (
    AgentApiContractError,
    load_agent_api_contract_config,
    validate_agent_api_contract_config,
)
from cli.agent_entity import AgentEntityType
from cli.agent_entity import AgentEntityRecord
from cli.agent_entity_readiness import build_agent_entity_readiness_report, agent_entities_for_task_type
from cli.agent_publish_adapter import (
    DEFAULT_AGENT_PUBLISH_PREVIEW_PATH,
    AgentPublishPreviewError,
    build_agent_entity_publish_preview,
    build_agent_entity_publish_preview_from_entity,
)
from cli.agent_publish_activity import build_agent_entity_publish_activity_summary
from cli.agent_publish_activity import build_agent_entity_publish_activity_summary_from_records
from cli.agent_publish_result import (
    DEFAULT_AGENT_PUBLISH_RESULT_PATH,
    AgentPublishResultError,
    record_agent_entity_publish_result,
    record_agent_entity_publish_result_for_entity,
)
from cli.agent_internal_publisher import (
    DEFAULT_AGENT_PUBLISH_REPORT_PATH,
    AgentPublishError,
    agent_internal_publish,
)
from cli.agent_publish_status import (
    DEFAULT_AGENT_PUBLISH_STATUS_REPORT_PATH,
    AgentPublishStatusError,
    query_agent_publish_status,
)
from cli.agent_entity_publish_review import (
    DEFAULT_AGENT_ENTITY_PUBLISH_REVIEW_DECISION_PATH,
    AgentEntityPublishReviewError,
    record_agent_entity_final_publish_review_decision,
    record_agent_entity_final_publish_review_decision_for_entity,
)
from cli.agent_entity_signoff import (
    DEFAULT_AGENT_ENTITY_SIGNOFF_RECORD_PATH,
    AgentEntitySignoffError,
    record_agent_entity_signoff,
    record_agent_entity_signoff_for_entity,
)
from cli.store import JsonTaskStore


class BackendAgentEntityServiceError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


class BackendAgentEntityService:
    def __init__(
        self,
        *,
        store: JsonTaskStore,
        root: Path | None = None,
        core_service: BackendCoreService | None = None,
    ) -> None:
        self.store = store
        self.root = Path(root or Path.cwd())
        self.core_service = core_service or BackendCoreService(self.root)

    def _resolve_local_path(self, value: str | Path) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return self.root / path

    def _optional_local_path(self, value: Any, *, field: str) -> Path | None:
        if value in (None, ""):
            return None
        if not isinstance(value, (str, Path)):
            raise BackendAgentEntityServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": field, "reason": "必须是文件路径字符串"}],
            )
        return self._resolve_local_path(value)

    def list_entities(self, query: dict[str, str]) -> dict[str, Any]:
        entity_type = query.get("entityType")
        if entity_type and entity_type not in {item.value for item in AgentEntityType}:
            raise BackendAgentEntityServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "entityType", "reason": "非法实体类型"}],
            )
        entities = self.store.list_agent_entities(
            entity_type=entity_type,
            source_task_id=query.get("sourceTaskId"),
            trace_id=query.get("traceId"),
        )
        return {
            "items": [entity.to_dict() for entity in entities],
            "total": len(entities),
            "filters": {
                "entityType": entity_type,
                "sourceTaskId": query.get("sourceTaskId"),
                "traceId": query.get("traceId"),
            },
            "mode": "MOCK_ONLY",
            "databaseWritten": False,
            "agentPublished": False,
            "realAgentImport": False,
        }

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        entity = self.store.get_agent_entity(entity_id)
        if entity is None:
            raise BackendAgentEntityServiceError(
                "NOT_FOUND",
                "平台实体不存在",
                [{"field": "id", "reason": "未找到实体"}],
            )
        return {
            "agentEntityRecord": entity.to_dict(),
            "agentEntityImportActivity": build_agent_entity_publish_activity_summary(self.store, entity_id),
            "mode": "MOCK_ONLY",
            "databaseWritten": False,
            "agentPublished": False,
            "realAgentImport": False,
        }

    def get_entity_from_repository(
        self,
        entity_id: str,
        *,
        repository: BackendCoreRepositoryContract,
        db_path_source: str | None = None,
    ) -> dict[str, Any]:
        entity = self._get_repository_entity(entity_id, repository=repository)
        activity = build_agent_entity_publish_activity_summary_from_records(
            entity_id=entity_id,
            operation_events=repository.list_operation_audit_events(
                resource_type="PLATFORM_ENTITY",
                resource_id=entity_id,
            ),
            artifacts=repository.list_artifacts(kind="WORKFLOW_REPORT"),
        )
        activity["mode"] = "LOCAL_SQLITE_BACKEND_CORE_READONLY"
        return {
            "agentEntityRecord": entity.to_dict(),
            "agentEntityImportActivity": activity,
            "mode": "LOCAL_SQLITE_BACKEND_CORE_READONLY",
            "coreDbPath": str(repository.db_path) if repository.db_path is not None else None,
            "dbPathSource": db_path_source,
            "localSqliteRead": repository.db_path is not None,
            "databaseWritten": False,
            "agentPublished": False,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
        }

    def readiness_report(self, query: dict[str, str]) -> dict[str, Any]:
        source_task_id = query.get("sourceTaskId")
        task = self.store.get(source_task_id) if source_task_id else None
        return {
            "agentEntityReadinessReport": build_agent_entity_readiness_report(
                self.store,
                source_task_id=source_task_id,
                agent_entities=agent_entities_for_task_type(task.taskType) if task else None,
            )
        }

    def validate_agent_entity_schema(self, payload: dict[str, Any]) -> dict[str, Any]:
        contract_config_path = self._optional_local_path(payload.get("contractConfig"), field="contractConfig")
        if contract_config_path is None:
            raise BackendAgentEntityServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "contractConfig", "reason": "缺少参数"}],
            )
        entity_type = payload.get("entityType")
        if entity_type not in (None, "") and entity_type not in {item.value for item in AgentEntityType}:
            raise BackendAgentEntityServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "entityType", "reason": "非法实体类型"}],
            )
        try:
            contract_config = load_agent_api_contract_config(contract_config_path)
            validation = validate_agent_api_contract_config(
                contract_config,
                entity_types=[entity_type] if entity_type else None,
            )
        except AgentApiContractError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc
        return {
            "platformApiContractValidation": validation,
            "mode": "LOCAL_PLATFORM_API_CONTRACT_VALIDATION",
            "contractConfigPath": str(contract_config_path),
            "entityType": entity_type or None,
            "requestSent": False,
            "networkAccess": False,
            "secretsRead": False,
            "secretValueReturned": False,
            "databaseWritten": False,
            "agentPublished": False,
            "realAgentImport": False,
            "realPublish": False,
        }

    def readiness_report_from_repository(
        self,
        query: dict[str, str],
        *,
        repository: BackendCoreRepositoryContract,
        db_path_source: str | None = None,
        grading_records_override: list[Any] | None = None,
        grading_record_source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source_task_id = query.get("sourceTaskId")
        task = repository.get_ai_task(source_task_id) if source_task_id else None
        agent_entities = repository.list_agent_entities(source_task_id=source_task_id)
        artifacts = repository.list_artifacts(kind="WORKFLOW_REPORT", task_id=source_task_id)
        list_grading_records = getattr(repository, "list_grading_records", None)
        if grading_records_override is not None:
            grading_records = grading_records_override
        elif callable(list_grading_records):
            grading_records = list_grading_records(task_id=source_task_id)
        else:
            grading_records = []
        grading_records_from_external_source = grading_records_override is not None

        def build_activity(entity_id: str) -> dict[str, Any]:
            return build_agent_entity_publish_activity_summary_from_records(
                entity_id=entity_id,
                operation_events=repository.list_operation_audit_events(
                    resource_type="PLATFORM_ENTITY",
                    resource_id=entity_id,
                ),
                artifacts=repository.list_artifacts(kind="WORKFLOW_REPORT"),
            )

        report = build_agent_entity_readiness_report(
            self.store,
            source_task_id=source_task_id,
            agent_entities=agent_entities_for_task_type(task.taskType) if task else None,
            artifacts_override=artifacts,
            entities_override=agent_entities,
            grading_records_override=grading_records,
            import_activity_builder=build_activity,
            source_mode="BACKEND_CORE_PLATFORM_ENTITY_READINESS_REPORT",
            repository_backed=True,
        )
        return {
            "agentEntityReadinessReport": report,
            "backendCoreAgentEntityReadiness": {
                "mode": "BACKEND_CORE_PLATFORM_ENTITY_READINESS",
                "repositoryContractUsed": True,
                "coreDbPath": str(repository.db_path) if repository.db_path is not None else None,
                "dbPathSource": db_path_source,
                "sourceTaskId": source_task_id,
                "agentEntityRead": True,
                "agentEntityTotal": len(agent_entities),
                "artifactRead": True,
                "artifactTotal": len(artifacts),
                "gradingRecordRead": True,
                "gradingRecordTotal": len(grading_records),
                "gradingRecordRepositoryAvailable": callable(list_grading_records),
                "gradingRecordExternalSourceUsed": grading_records_from_external_source,
                "gradingRecordSource": grading_record_source
                or {
                    "mode": "BACKEND_CORE_REPOSITORY",
                    "repositoryAvailable": callable(list_grading_records),
                },
                "operationAuditEventRead": True,
                "jsonStoreSourceRead": False,
                "localSqliteRead": repository.db_path is not None,
                "databaseWritten": False,
                "productionDatabaseWritten": False,
                "productionQueueUsed": False,
                "autoPublishAllowed": False,
                "realPublish": False,
            },
        }

    def build_publish_preview(
        self,
        entity_id: str,
        payload: dict[str, Any],
        *,
        trace_id: str,
    ) -> dict[str, Any]:
        output = str(payload.get("output") or DEFAULT_AGENT_PUBLISH_PREVIEW_PATH)
        contract_config = self._optional_local_path(payload.get("contractConfig"), field="contractConfig")
        try:
            return build_agent_entity_publish_preview(
                self.store,
                entity_id=entity_id,
                reviewer=str(payload.get("reviewer", "")),
                output_path=self._resolve_local_path(output),
                trace_id=trace_id,
                contract_config_path=contract_config,
            )
        except AgentPublishPreviewError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc

    def build_publish_preview_from_repository(
        self,
        entity_id: str,
        payload: dict[str, Any],
        *,
        trace_id: str,
        repository: BackendCoreRepositoryContract,
        write_summary: dict[str, Any] | None,
    ) -> dict[str, Any]:
        output = str(payload.get("output") or DEFAULT_AGENT_PUBLISH_PREVIEW_PATH)
        contract_config = self._optional_local_path(payload.get("contractConfig"), field="contractConfig")
        try:
            entity = self._get_repository_entity(entity_id, repository=repository)
            result = build_agent_entity_publish_preview_from_entity(
                entity,
                reviewer=str(payload.get("reviewer", "")),
                output_path=self._resolve_local_path(output),
                trace_id=trace_id,
                contract_config_path=contract_config,
            )
        except AgentPublishPreviewError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc
        except CoreRepositoryError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc
        self._write_repository_import_artifacts(repository, write_summary, result)
        result["backendCoreAgentEntityImportDryRun"] = self._repository_import_summary(
            repository,
            write_summary,
            source="REQUEST_CORE_DB_PATH",
        )
        return result

    def publish_entity(
        self,
        entity_id: str,
        payload: dict[str, Any],
        *,
        trace_id: str,
    ) -> dict[str, Any]:
        dry_run = str(payload.get("dryRun") or DEFAULT_AGENT_PUBLISH_PREVIEW_PATH)
        dry_run_output = str(payload.get("dryRunOutput") or DEFAULT_AGENT_PUBLISH_PREVIEW_PATH)
        output = str(payload.get("output") or DEFAULT_AGENT_PUBLISH_REPORT_PATH)
        contract_config = self._optional_local_path(payload.get("contractConfig"), field="contractConfig")
        dry_run_path = self._resolve_local_path(dry_run)
        timeout_seconds = self._parse_timeout_seconds(payload.get("timeoutSeconds"))
        max_retries = self._parse_max_retries(payload.get("maxRetries"))
        try:
            if payload.get("createDryRunIfMissing") is True and not dry_run_path.exists():
                build_agent_entity_publish_preview(
                    self.store,
                    entity_id=entity_id,
                    reviewer=str(payload.get("reviewer", "")),
                    output_path=self._resolve_local_path(dry_run_output),
                    trace_id=trace_id,
                    contract_config_path=contract_config,
                )
                dry_run_path = self._resolve_local_path(dry_run_output)
            return agent_internal_publish(
                self.store,
                entity_id=entity_id,
                dry_run_path=dry_run_path,
                reviewer=str(payload.get("reviewer", "")),
                output_path=self._resolve_local_path(output),
                trace_id=trace_id,
                base_url=payload.get("baseUrl"),
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                explicit_platform_call_opt_in=payload.get("explicitPlatformCallOptIn") is True,
                confirm_dry_run_reviewed=payload.get("confirmDryRunReviewed") is True,
                confirm_manual_platform_review=payload.get("confirmManualPlatformReview") is True,
                confirm_no_auto_publish=payload.get("confirmNoAutoPublish") is True,
            )
        except (AgentPublishPreviewError, AgentPublishError) as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc

    def query_publish_status(
        self,
        entity_id: str,
        payload: dict[str, Any],
        *,
        trace_id: str,
    ) -> dict[str, Any]:
        output = str(payload.get("output") or DEFAULT_AGENT_PUBLISH_STATUS_REPORT_PATH)
        send_result = str(payload.get("sendResult") or DEFAULT_AGENT_PUBLISH_REPORT_PATH)
        contract_config = self._optional_local_path(payload.get("contractConfig"), field="contractConfig")
        timeout_seconds = self._parse_timeout_seconds(payload.get("timeoutSeconds"))
        max_retries = self._parse_max_retries(payload.get("maxRetries"))
        try:
            return query_agent_publish_status(
                self.store,
                entity_id=entity_id,
                send_result_path=self._resolve_local_path(send_result),
                reviewer=str(payload.get("reviewer", "")),
                output_path=self._resolve_local_path(output),
                trace_id=trace_id,
                agent_draft_id=payload.get("agentDraftId"),
                status_path_template=payload.get("statusPathTemplate"),
                contract_config_path=contract_config,
                base_url=payload.get("baseUrl"),
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                explicit_platform_query_opt_in=payload.get("explicitPlatformQueryOptIn") is True,
            )
        except AgentPublishStatusError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc

    def record_publish_result(
        self,
        entity_id: str,
        payload: dict[str, Any],
        *,
        trace_id: str,
    ) -> dict[str, Any]:
        output = str(payload.get("output") or DEFAULT_AGENT_PUBLISH_RESULT_PATH)
        send_result = str(payload.get("sendResult") or DEFAULT_AGENT_PUBLISH_REPORT_PATH)
        try:
            return record_agent_entity_publish_result(
                self.store,
                entity_id=entity_id,
                send_result_path=self._resolve_local_path(send_result),
                reviewer=str(payload.get("reviewer", "")),
                platform_status=str(payload.get("agentStatus", "")),
                agent_draft_id=payload.get("agentDraftId"),
                message=payload.get("message"),
                output_path=self._resolve_local_path(output),
                trace_id=trace_id,
            )
        except AgentPublishResultError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc

    def record_publish_result_from_repository(
        self,
        entity_id: str,
        payload: dict[str, Any],
        *,
        trace_id: str,
        repository: BackendCoreRepositoryContract,
        write_summary: dict[str, Any] | None,
    ) -> dict[str, Any]:
        output = str(payload.get("output") or DEFAULT_AGENT_PUBLISH_RESULT_PATH)
        send_result = str(payload.get("sendResult") or DEFAULT_AGENT_PUBLISH_REPORT_PATH)
        try:
            entity = self._get_repository_entity(entity_id, repository=repository)
            result = record_agent_entity_publish_result_for_entity(
                entity,
                send_result_path=self._resolve_local_path(send_result),
                reviewer=str(payload.get("reviewer", "")),
                platform_status=str(payload.get("agentStatus", "")),
                agent_draft_id=payload.get("agentDraftId"),
                message=payload.get("message"),
                output_path=self._resolve_local_path(output),
                trace_id=trace_id,
                mock_store_updated=False,
                database_written_by_local_system=True,
            )
        except AgentPublishResultError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc
        except CoreRepositoryError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc
        self._write_repository_import_artifacts(repository, write_summary, result)
        result["backendCoreAgentEntityImportResult"] = self._repository_import_summary(
            repository,
            write_summary,
            source="REQUEST_CORE_DB_PATH",
            mode="BACKEND_CORE_PLATFORM_ENTITY_IMPORT_RESULT",
        )
        return result

    def record_signoff(
        self,
        entity_id: str,
        payload: dict[str, Any],
        *,
        trace_id: str,
    ) -> dict[str, Any]:
        output = str(payload.get("output") or DEFAULT_AGENT_ENTITY_SIGNOFF_RECORD_PATH)
        try:
            return record_agent_entity_signoff(
                self.store,
                entity_id=entity_id,
                reviewer=str(payload.get("reviewer", "")),
                comment=payload.get("comment"),
                output_path=self._resolve_local_path(output),
                trace_id=trace_id,
            )
        except AgentEntitySignoffError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc

    def record_signoff_from_repository(
        self,
        entity_id: str,
        payload: dict[str, Any],
        *,
        trace_id: str,
        repository: BackendCoreRepositoryContract,
        write_summary: dict[str, Any] | None,
    ) -> dict[str, Any]:
        output = str(payload.get("output") or DEFAULT_AGENT_ENTITY_SIGNOFF_RECORD_PATH)
        try:
            entity = self._get_repository_entity(entity_id, repository=repository)
            readiness_report = self.readiness_report_from_repository(
                {"sourceTaskId": entity.sourceTaskId},
                repository=repository,
                db_path_source=write_summary.get("dbPathSource") if write_summary else None,
            )["agentEntityReadinessReport"]
            result = record_agent_entity_signoff_for_entity(
                entity,
                readiness_report=readiness_report,
                reviewer=str(payload.get("reviewer", "")),
                comment=payload.get("comment"),
                output_path=self._resolve_local_path(output),
                trace_id=trace_id,
                mock_store_updated=False,
                database_written_by_local_system=True,
            )
        except AgentEntitySignoffError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc
        except CoreRepositoryError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc
        self._write_repository_import_artifacts(repository, write_summary, result)
        result["backendCoreAgentEntitySignoff"] = self._repository_import_summary(
            repository,
            write_summary,
            source="REQUEST_CORE_DB_PATH",
            mode="BACKEND_CORE_PLATFORM_ENTITY_SIGNOFF_RECORD",
        )
        return result

    def record_final_publish_review_decision(
        self,
        entity_id: str,
        payload: dict[str, Any],
        *,
        trace_id: str,
    ) -> dict[str, Any]:
        output = str(payload.get("output") or DEFAULT_AGENT_ENTITY_PUBLISH_REVIEW_DECISION_PATH)
        try:
            return record_agent_entity_final_publish_review_decision(
                self.store,
                entity_id=entity_id,
                reviewer=str(payload.get("reviewer", "")),
                decision=str(payload.get("decision", "")),
                comment=payload.get("comment"),
                output_path=self._resolve_local_path(output),
                trace_id=trace_id,
                confirm_no_auto_publish=payload.get("confirmNoAutoPublish") is True,
                confirm_no_real_publish=payload.get("confirmNoRealPublish") is True,
                confirm_final_human_review=payload.get("confirmFinalHumanReview") is True,
            )
        except AgentEntityPublishReviewError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc

    def record_final_publish_review_decision_from_repository(
        self,
        entity_id: str,
        payload: dict[str, Any],
        *,
        trace_id: str,
        repository: BackendCoreRepositoryContract,
        write_summary: dict[str, Any] | None,
    ) -> dict[str, Any]:
        output = str(payload.get("output") or DEFAULT_AGENT_ENTITY_PUBLISH_REVIEW_DECISION_PATH)
        try:
            entity = self._get_repository_entity(entity_id, repository=repository)
            readiness_report = self.readiness_report_from_repository(
                {"sourceTaskId": entity.sourceTaskId},
                repository=repository,
                db_path_source=write_summary.get("dbPathSource") if write_summary else None,
            )["agentEntityReadinessReport"]
            result = record_agent_entity_final_publish_review_decision_for_entity(
                entity,
                readiness_report=readiness_report,
                reviewer=str(payload.get("reviewer", "")),
                decision=str(payload.get("decision", "")),
                comment=payload.get("comment"),
                output_path=self._resolve_local_path(output),
                trace_id=trace_id,
                confirm_no_auto_publish=payload.get("confirmNoAutoPublish") is True,
                confirm_no_real_publish=payload.get("confirmNoRealPublish") is True,
                confirm_final_human_review=payload.get("confirmFinalHumanReview") is True,
                database_written_by_local_system=True,
            )
        except AgentEntityPublishReviewError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc
        except CoreRepositoryError as exc:
            raise BackendAgentEntityServiceError(exc.code, exc.message, exc.errors) from exc
        self._write_repository_import_artifacts(repository, write_summary, result)
        result["backendCoreAgentEntityFinalPublishReviewDecision"] = self._repository_import_summary(
            repository,
            write_summary,
            source="REQUEST_CORE_DB_PATH",
            mode="BACKEND_CORE_PLATFORM_ENTITY_FINAL_PUBLISH_REVIEW_DECISION",
        )
        return result

    def _parse_timeout_seconds(self, value: Any) -> int:
        try:
            return int(value or 30)
        except (TypeError, ValueError) as exc:
            raise BackendAgentEntityServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "timeoutSeconds", "reason": "必须是整数"}],
            ) from exc

    def _parse_max_retries(self, value: Any) -> int:
        try:
            max_retries = int(value or 0)
        except (TypeError, ValueError) as exc:
            raise BackendAgentEntityServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "maxRetries", "reason": "必须是整数"}],
            ) from exc
        if max_retries < 0:
            raise BackendAgentEntityServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "maxRetries", "reason": "必须大于等于 0"}],
            )
        return max_retries

    def _get_repository_entity(
        self,
        entity_id: str,
        *,
        repository: BackendCoreRepositoryContract,
    ) -> AgentEntityRecord:
        entity = repository.get_agent_entity(entity_id)
        if entity is None:
            raise BackendAgentEntityServiceError(
                "NOT_FOUND",
                "平台实体不存在",
                [{"field": "id", "reason": "未找到实体"}],
            )
        return entity

    def _write_repository_import_artifacts(
        self,
        repository: BackendCoreRepositoryContract,
        write_summary: dict[str, Any] | None,
        result: dict[str, Any],
    ) -> None:
        artifact_payload = result.get("artifact")
        operation_event_payload = result.get("operationAuditEvent")
        self.core_service.write_through(
            repository,
            write_summary,
            agent_entity=(
                AgentEntityRecord.from_dict(result["agentEntityRecord"])
                if isinstance(result.get("agentEntityRecord"), dict)
                else None
            ),
            artifacts=[ArtifactRecord.from_dict(artifact_payload)] if isinstance(artifact_payload, dict) else [],
            operation_audit_event=(
                OperationAuditEvent.from_dict(operation_event_payload)
                if isinstance(operation_event_payload, dict)
                else None
            ),
        )

    def _repository_import_summary(
        self,
        repository: BackendCoreRepositoryContract,
        write_summary: dict[str, Any] | None,
        *,
        source: str,
        mode: str = "BACKEND_CORE_PLATFORM_ENTITY_IMPORT_DRY_RUN",
    ) -> dict[str, Any]:
        return {
            "mode": mode,
            "repositoryContractUsed": True,
            "coreDbPath": str(repository.db_path) if repository.db_path is not None else None,
            "source": source,
            "agentEntityRead": True,
            "agentEntityWritten": bool(write_summary and write_summary.get("agentEntityWritten")),
            "jsonStoreSourceRead": False,
            "artifactWritten": bool(write_summary and int(write_summary.get("artifactsWritten", 0)) > 0),
            "operationAuditEventWritten": bool(write_summary and write_summary.get("operationAuditEventWritten")),
            "localSqliteWritten": bool(write_summary and write_summary.get("localSqliteWritten")),
            "externalDatabaseWritten": bool(write_summary and write_summary.get("externalDatabaseWritten")),
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        }
