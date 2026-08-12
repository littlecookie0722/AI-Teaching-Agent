"""Dry-run adapter from local platform entity records to future platform API payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifact import ArtifactKind, ArtifactRecord, ArtifactStatus, create_artifact_record
from .audit import OperationAction, OperationAuditEvent, OperationResourceType, create_operation_audit_event
from .agent_api_contract import (
    AgentApiContractError,
    build_agent_request_body,
    build_agent_publish_endpoint,
    describe_agent_publish_contract,
    load_agent_api_contract_config,
    validate_agent_api_contract_config,
)
from .agent_entity import AgentEntityRecord, AgentEntityType
from .store import JsonTaskStore


DEFAULT_AGENT_PUBLISH_PREVIEW_PATH = Path("examples/output/platform-entity-import-dry-run.json")


class AgentPublishPreviewError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def _ensure_manual_context(value: str, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise AgentPublishPreviewError(
            "VALIDATION_ERROR",
            "参数错误",
            [{"field": field, "reason": "缺少参数"}],
        )
    return normalized


def _list_payload_values(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _build_lab_template_dto(entity: AgentEntityRecord) -> dict[str, Any]:
    payload = entity.payload if isinstance(entity.payload, dict) else {}
    environment = payload.get("environment") if isinstance(payload.get("environment"), dict) else {}
    return {
        "apiVersion": "platform-import-dry-run/v1",
        "entityType": "lab_template",
        "operation": "create_or_update_draft",
        "idempotencyKey": f"dryrun:{entity.id}",
        "source": {
            "agentEntityId": entity.id,
            "sourceTaskId": entity.sourceTaskId,
            "sourcePreviewArtifactId": entity.sourcePreviewArtifactId,
            "sourceArtifactKind": entity.sourceArtifactKind,
            "sourceDslPath": entity.sourceDslPath,
        },
        "payload": {
            "externalId": payload.get("id"),
            "title": payload.get("title"),
            "category": payload.get("category"),
            "difficulty": payload.get("difficulty"),
            "durationMinutes": payload.get("durationMinutes"),
            "tags": _list_payload_values(payload, "tags"),
            "objectiveTotal": payload.get("objectiveTotal"),
            "stepTotal": payload.get("stepTotal"),
            "materialTotal": payload.get("materialTotal"),
            "environment": {
                "type": environment.get("type"),
                "image": environment.get("image"),
                "resources": environment.get("resources", {}),
            },
            "gradingRef": payload.get("gradingRef"),
            "reviewStatus": "PENDING_MANUAL_PLATFORM_REVIEW",
        },
    }


def _build_exam_question_dto(entity: AgentEntityRecord) -> dict[str, Any]:
    payload = entity.payload if isinstance(entity.payload, dict) else {}
    return {
        "apiVersion": "platform-import-dry-run/v1",
        "entityType": "exam_question",
        "operation": "create_or_update_draft",
        "idempotencyKey": f"dryrun:{entity.id}",
        "source": {
            "agentEntityId": entity.id,
            "sourceTaskId": entity.sourceTaskId,
            "sourcePreviewArtifactId": entity.sourcePreviewArtifactId,
            "sourceArtifactKind": entity.sourceArtifactKind,
            "sourceDslPath": entity.sourceDslPath,
        },
        "payload": {
            "externalId": payload.get("id"),
            "title": payload.get("title"),
            "sourceLabId": payload.get("sourceLabId"),
            "difficulty": payload.get("difficulty"),
            "questionType": payload.get("questionType"),
            "totalScore": payload.get("totalScore"),
            "questionTotal": payload.get("questionTotal"),
            "questionIds": _list_payload_values(payload, "questionIds"),
            "gradingRefs": _list_payload_values(payload, "gradingRefs"),
            "answerStoragePolicy": payload.get("answerStoragePolicy"),
            "candidateAnswerVisible": False,
            "reviewStatus": "PENDING_MANUAL_PLATFORM_REVIEW",
        },
    }


def _build_grading_rule_dto(entity: AgentEntityRecord) -> dict[str, Any]:
    payload = entity.payload if isinstance(entity.payload, dict) else {}
    return {
        "apiVersion": "platform-import-dry-run/v1",
        "entityType": "grading_rule",
        "operation": "create_or_update_draft",
        "idempotencyKey": f"dryrun:{entity.id}",
        "source": {
            "agentEntityId": entity.id,
            "sourceTaskId": entity.sourceTaskId,
            "sourcePreviewArtifactId": entity.sourcePreviewArtifactId,
            "sourceArtifactKind": entity.sourceArtifactKind,
            "sourceDslPath": entity.sourceDslPath,
        },
        "payload": {
            "externalId": payload.get("id"),
            "title": payload.get("title"),
            "sourceExamId": payload.get("sourceExamId"),
            "totalScore": payload.get("totalScore"),
            "timeoutSeconds": payload.get("timeoutSeconds"),
            "checkTotal": payload.get("checkTotal"),
            "checkIds": _list_payload_values(payload, "checkIds"),
            "runnerTypes": _list_payload_values(payload, "runnerTypes"),
            "assessmentPlanTotal": payload.get("assessmentPlanTotal"),
            "sandboxRequiredBeforeRealExecution": True,
            "reviewStatus": "PENDING_MANUAL_PLATFORM_REVIEW",
        },
    }


def _build_ppt_deck_dto(entity: AgentEntityRecord) -> dict[str, Any]:
    payload = entity.payload if isinstance(entity.payload, dict) else {}
    theme = payload.get("theme") if isinstance(payload.get("theme"), dict) else {}
    return {
        "apiVersion": "platform-import-dry-run/v1",
        "entityType": "ppt_deck",
        "operation": "create_or_update_draft",
        "idempotencyKey": f"dryrun:{entity.id}",
        "source": {
            "agentEntityId": entity.id,
            "sourceTaskId": entity.sourceTaskId,
            "sourcePreviewArtifactId": entity.sourcePreviewArtifactId,
            "sourceArtifactKind": entity.sourceArtifactKind,
            "sourceDslPath": entity.sourceDslPath,
        },
        "payload": {
            "externalId": payload.get("id"),
            "title": payload.get("title"),
            "audience": payload.get("audience"),
            "durationMinutes": payload.get("durationMinutes"),
            "theme": {
                "style": theme.get("style"),
                "language": theme.get("language"),
            },
            "slideTotal": payload.get("slideTotal"),
            "slideIds": _list_payload_values(payload, "slideIds"),
            "slideTypes": _list_payload_values(payload, "slideTypes"),
            "firstSlideTitle": payload.get("firstSlideTitle"),
            "pptxArtifactRequiredBeforePublish": True,
            "pptxArtifactImported": False,
            "reviewStatus": "PENDING_MANUAL_PLATFORM_REVIEW",
        },
    }


def _build_agent_api_payload(entity: AgentEntityRecord) -> dict[str, Any]:
    if entity.entityType == AgentEntityType.LAB_TEMPLATE:
        return _build_lab_template_dto(entity)
    if entity.entityType == AgentEntityType.EXAM_QUESTION:
        return _build_exam_question_dto(entity)
    if entity.entityType == AgentEntityType.GRADING_RULE:
        return _build_grading_rule_dto(entity)
    if entity.entityType == AgentEntityType.PPT_DECK:
        return _build_ppt_deck_dto(entity)
    raise AgentPublishPreviewError(
        "VALIDATION_ERROR",
        "不支持的平台实体类型",
        [{"field": "entityType", "reason": str(entity.entityType)}],
    )


def build_agent_entity_publish_preview(
    store: JsonTaskStore,
    *,
    entity_id: str,
    reviewer: str,
    output_path: Path,
    trace_id: str,
    contract_config_path: Path | None = None,
) -> dict[str, Any]:
    reviewer = _ensure_manual_context(reviewer, "reviewer")
    entity_id = _ensure_manual_context(entity_id, "id")
    entity = store.get_agent_entity(entity_id)
    if entity is None:
        raise AgentPublishPreviewError(
            "NOT_FOUND",
            "平台实体不存在",
            [{"field": "id", "reason": "未找到实体"}],
        )
    result = build_agent_entity_publish_preview_from_entity(
        entity,
        reviewer=reviewer,
        output_path=output_path,
        trace_id=trace_id,
        contract_config_path=contract_config_path,
    )
    store.save_artifact(ArtifactRecord.from_dict(result["artifact"]))
    store.save_operation_audit_event(OperationAuditEvent.from_dict(result["operationAuditEvent"]))
    return result


def build_agent_entity_publish_preview_from_entity(
    entity: AgentEntityRecord,
    *,
    reviewer: str,
    output_path: Path,
    trace_id: str,
    contract_config_path: Path | None = None,
) -> dict[str, Any]:
    reviewer = _ensure_manual_context(reviewer, "reviewer")
    if entity.realAgentImport is not False or entity.databaseWritten is not False:
        raise AgentPublishPreviewError(
            "VALIDATION_ERROR",
            "平台实体安全标记不允许生成真实导入 dry-run",
            [{"field": "agentEntityRecord", "reason": "expected databaseWritten=false and realAgentImport=false"}],
        )
    try:
        contract_config = load_agent_api_contract_config(contract_config_path)
        endpoint = build_agent_publish_endpoint(entity.entityType, contract_config)
        contract = describe_agent_publish_contract(entity.entityType, contract_config)
    except AgentApiContractError as exc:
        raise AgentPublishPreviewError(exc.code, exc.message, exc.errors) from exc
    dto = _build_agent_api_payload(entity)
    try:
        request_body, request_body_mapping = build_agent_request_body(dto, entity.entityType, contract_config)
        contract_validation = validate_agent_api_contract_config(
            contract_config,
            entity_types=[entity.entityType],
            request_previews={entity.entityType.value: dto},
        )
    except AgentApiContractError as exc:
        raise AgentPublishPreviewError(exc.code, exc.message, exc.errors) from exc
    report = {
        "component": "AgentEntityImportDryRun",
        "mode": "REAL_PLATFORM_IMPORT_DRY_RUN_ONLY",
        "agentEntityId": entity.id,
        "entityType": entity.entityType.value,
        "reviewer": reviewer,
        "platformApiContract": contract,
        "contractValidation": contract_validation,
        "targetEndpoint": endpoint,
        "requestPreview": dto,
        "requestBody": request_body,
        "requestBodyMapping": request_body_mapping,
        "validation": {
            "sourceMockImportRequired": True,
            "sourceMockImportPresent": entity.mockStoreWritten is True,
            "idempotencyKeyPresent": bool(dto.get("idempotencyKey")),
            "contractConfigValid": contract_validation["valid"],
            "contractWarningTotal": contract_validation["summary"]["warningTotal"],
            "requestBodyMappingConfigured": bool(request_body_mapping.get("applied")),
            "requestBodyReady": True,
            "manualPlatformReviewRequired": True,
            "readyForRealApiImplementation": True,
            "readyForRealApiCall": False,
        },
        "safety": {
            "dryRunOnly": True,
            "requestSent": False,
            "networkAccess": False,
            "secretsRead": False,
            "databaseWritten": False,
            "realAgentImport": False,
            "realPublish": False,
            "autoPublishAllowed": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
        },
        "traceId": trace_id,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path=str(output_path),
        title="Platform Entity Import Dry Run",
        status=ArtifactStatus.READY,
        trace_id=trace_id,
        task_id=entity.sourceTaskId,
        source_ref=entity.sourcePreviewPath,
        metadata={
            "component": "AgentEntityImportDryRun",
            "agentEntityId": entity.id,
            "entityType": entity.entityType.value,
            "dryRunOnly": True,
            "requestSent": False,
            "databaseWritten": False,
            "realAgentImport": False,
            "realPublish": False,
        },
        mode="REAL_PLATFORM_IMPORT_DRY_RUN_ONLY",
    )
    operation_event = create_operation_audit_event(
        action=OperationAction.PLATFORM_ENTITY_IMPORT_DRY_RUN,
        resource_type=OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor=reviewer,
        trace_id=trace_id,
        before_state=entity.status.value,
        after_state="IMPORT_DRY_RUN_PREPARED",
        detail={
            "component": "AgentEntityImportDryRun",
            "artifactId": artifact.id,
            "outputPath": str(output_path),
            "targetEndpoint": report["targetEndpoint"],
            "dryRunOnly": True,
            "requestSent": False,
            "databaseWritten": False,
            "realAgentImport": False,
            "realPublish": False,
        },
    )
    return {
        "agentEntityImportDryRun": report,
        "artifact": artifact.to_dict(),
        "operationAuditEvent": operation_event.to_dict(),
    }
