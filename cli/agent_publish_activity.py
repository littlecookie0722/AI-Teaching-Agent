"""Read-only summaries for platform entity import dry-run/send activity."""

from __future__ import annotations

from typing import Any

from .store import JsonTaskStore


IMPORT_ACTIVITY_ACTIONS = {
    "PLATFORM_ENTITY_IMPORT_DRY_RUN",
    "PLATFORM_ENTITY_IMPORT_SEND",
    "PLATFORM_ENTITY_IMPORT_STATUS_QUERY",
    "PLATFORM_ENTITY_IMPORT_RESULT_RECORD",
    "PLATFORM_ENTITY_SIGNOFF_RECORD",
}

IMPORT_ACTIVITY_COMPONENTS = {
    "AgentEntityImportDryRun",
    "AgentEntityImportSendResult",
    "AgentEntityImportStatusQuery",
    "AgentEntityImportResultRecord",
    "AgentEntitySignoffRecord",
}


def _operation_item(event: dict[str, Any]) -> dict[str, Any]:
    detail = event.get("detail") if isinstance(event.get("detail"), dict) else {}
    return {
        "id": event.get("id"),
        "action": event.get("action"),
        "mode": event.get("mode"),
        "actor": event.get("actor"),
        "occurredAt": event.get("occurredAt"),
        "beforeState": event.get("beforeState"),
        "afterState": event.get("afterState"),
        "artifactId": detail.get("artifactId"),
        "outputPath": detail.get("outputPath"),
        "targetEndpoint": detail.get("targetEndpoint"),
        "statusCode": detail.get("statusCode"),
        "agentDraftId": detail.get("agentDraftId"),
        "agentStatus": detail.get("agentStatus"),
        "signoffRecorded": bool(detail.get("signoffRecorded")),
        "agentSideReviewed": bool(detail.get("agentSideReviewed")),
        "acceptedForDraft": bool(detail.get("acceptedForDraft")),
        "rejectedByPlatform": bool(detail.get("rejectedByPlatform")),
        "failed": bool(detail.get("failed")),
        "querySucceeded": bool(detail.get("querySucceeded")),
        "suggestedImportResultStatus": detail.get("suggestedImportResultStatus"),
        "requestSent": bool(detail.get("requestSent")),
        "sourceRequestSent": bool(detail.get("sourceRequestSent")),
        "networkAccess": bool(detail.get("networkAccess")),
        "secretsRead": bool(detail.get("secretsRead")),
        "secretValueReturned": bool(detail.get("secretValueReturned")),
        "mockStoreUpdated": bool(detail.get("mockStoreUpdated")),
        "databaseWrittenByLocalSystem": bool(detail.get("databaseWrittenByLocalSystem")),
        "realAgentImportAttempted": bool(detail.get("realAgentImportAttempted")),
        "realAgentImportAccepted": bool(detail.get("realAgentImportAccepted")),
        "realPublish": bool(detail.get("realPublish")),
    }


def _artifact_item(artifact: dict[str, Any]) -> dict[str, Any]:
    metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
    return {
        "id": artifact.get("id"),
        "kind": artifact.get("kind"),
        "path": artifact.get("path"),
        "title": artifact.get("title"),
        "mode": artifact.get("mode"),
        "status": artifact.get("status"),
        "createdAt": artifact.get("createdAt"),
        "component": metadata.get("component"),
        "agentEntityId": metadata.get("agentEntityId"),
        "entityType": metadata.get("entityType"),
        "agentDraftId": metadata.get("agentDraftId"),
        "agentStatus": metadata.get("agentStatus"),
        "signoffRecorded": bool(metadata.get("signoffRecorded")),
        "suggestedImportResultStatus": metadata.get("suggestedImportResultStatus"),
        "sourceRequestSent": bool(metadata.get("sourceRequestSent")),
        "requestSent": bool(metadata.get("requestSent")),
        "networkAccess": bool(metadata.get("networkAccess")),
        "secretsRead": bool(metadata.get("secretsRead")),
        "secretValueReturned": bool(metadata.get("secretValueReturned")),
        "mockStoreUpdated": bool(metadata.get("mockStoreUpdated")),
        "databaseWrittenByLocalSystem": bool(metadata.get("databaseWrittenByLocalSystem")),
        "realAgentImportAttempted": bool(metadata.get("realAgentImportAttempted")),
        "realAgentImportAccepted": bool(metadata.get("realAgentImportAccepted")),
        "realPublish": bool(metadata.get("realPublish")),
    }


def _record_payload(record: Any) -> dict[str, Any]:
    if isinstance(record, dict):
        return record
    if hasattr(record, "to_dict"):
        payload = record.to_dict()
        if isinstance(payload, dict):
            return payload
    return {}


def _build_import_activity_summary(
    *,
    entity_id: str,
    operation_events: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    mode: str,
    repository_backed: bool = False,
) -> dict[str, Any]:
    dry_run_events = [item for item in operation_events if item.get("action") == "PLATFORM_ENTITY_IMPORT_DRY_RUN"]
    send_events = [item for item in operation_events if item.get("action") == "PLATFORM_ENTITY_IMPORT_SEND"]
    status_query_events = [
        item for item in operation_events if item.get("action") == "PLATFORM_ENTITY_IMPORT_STATUS_QUERY"
    ]
    result_events = [
        item for item in operation_events if item.get("action") == "PLATFORM_ENTITY_IMPORT_RESULT_RECORD"
    ]
    signoff_events = [
        item for item in operation_events if item.get("action") == "PLATFORM_ENTITY_SIGNOFF_RECORD"
    ]
    dry_run_artifacts = [item for item in artifacts if item.get("component") == "AgentEntityImportDryRun"]
    send_artifacts = [item for item in artifacts if item.get("component") == "AgentEntityImportSendResult"]
    status_query_artifacts = [
        item for item in artifacts if item.get("component") == "AgentEntityImportStatusQuery"
    ]
    result_artifacts = [
        item for item in artifacts if item.get("component") == "AgentEntityImportResultRecord"
    ]
    signoff_artifacts = [
        item for item in artifacts if item.get("component") == "AgentEntitySignoffRecord"
    ]
    latest_send = send_events[0] if send_events else None
    latest_status_query = status_query_events[0] if status_query_events else None
    latest_dry_run = dry_run_events[0] if dry_run_events else None
    latest_result = result_events[0] if result_events else None
    latest_signoff = signoff_events[0] if signoff_events else None

    return {
        "component": "AgentEntityImportActivitySummary",
        "mode": mode,
        "agentEntityId": entity_id,
        "repositoryBacked": repository_backed,
        "visible": bool(operation_events or artifacts),
        "dryRunTotal": len(dry_run_events),
        "sendTotal": len(send_events),
        "statusQueryTotal": len(status_query_events),
        "resultTotal": len(result_events),
        "signoffTotal": len(signoff_events),
        "artifactTotal": len(artifacts),
        "latestDryRun": latest_dry_run,
        "latestSend": latest_send,
        "latestStatusQuery": latest_status_query,
        "latestResult": latest_result,
        "latestSignoff": latest_signoff,
        "operationEvents": operation_events,
        "artifacts": artifacts,
        "summary": {
            "dryRunPrepared": bool(dry_run_events or dry_run_artifacts),
            "requestSent": bool(send_events),
            "statusQueried": bool(status_query_events or status_query_artifacts),
            "resultRecorded": bool(result_events or result_artifacts),
            "signoffRecorded": bool(signoff_events or signoff_artifacts),
            "latestSignoffArtifactId": latest_signoff.get("artifactId") if latest_signoff else None,
            "latestStatusCode": latest_send.get("statusCode") if latest_send else None,
            "latestQueryStatusCode": latest_status_query.get("statusCode") if latest_status_query else None,
            "latestQueriedPlatformStatus": latest_status_query.get("agentStatus") if latest_status_query else None,
            "latestSuggestedImportResultStatus": (
                latest_status_query.get("suggestedImportResultStatus") if latest_status_query else None
            ),
            "latestPlatformDraftId": latest_result.get("agentDraftId") if latest_result else None,
            "latestPlatformStatus": latest_result.get("agentStatus") if latest_result else None,
            "agentSideReviewed": bool(latest_result and latest_result.get("agentSideReviewed") is True),
            "acceptedForDraft": bool(latest_result and latest_result.get("acceptedForDraft") is True),
            "rejectedByPlatform": bool(latest_result and latest_result.get("rejectedByPlatform") is True),
            "latestRealPlatformImportAccepted": bool(
                latest_send and latest_send.get("realAgentImportAccepted") is True
            ),
            "secretValueReturned": False,
            "databaseWrittenByLocalSystem": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
        "safety": {
            "readOnly": True,
            "reportContentRead": False,
            "newLlmRequestSent": False,
            "realLlmCalled": False,
            "secretsRead": bool(send_events or status_query_events),
            "secretValueReturned": False,
            "requestSent": bool(send_events or status_query_events),
            "networkAccess": bool(send_events or status_query_events),
            "mockStoreUpdated": bool(result_events) and not repository_backed,
            "databaseWrittenByLocalSystem": bool(result_events) and repository_backed,
            "manualPlatformReviewRequired": True,
            "autoPublishAllowed": False,
            "realPublish": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
        },
    }


def build_agent_entity_publish_activity_summary_from_records(
    *,
    entity_id: str,
    operation_events: list[Any],
    artifacts: list[Any],
    mode: str = "BACKEND_CORE_PLATFORM_ENTITY_IMPORT_ACTIVITY_SUMMARY",
    repository_backed: bool = True,
) -> dict[str, Any]:
    operation_items = [
        _operation_item(payload)
        for payload in (_record_payload(event) for event in operation_events)
        if payload.get("action") in IMPORT_ACTIVITY_ACTIONS
    ]
    artifact_items = [
        _artifact_item(payload)
        for payload in (_record_payload(artifact) for artifact in artifacts)
        if isinstance(payload.get("metadata"), dict)
        and payload.get("kind") == "WORKFLOW_REPORT"
        and payload["metadata"].get("agentEntityId") == entity_id
        and payload["metadata"].get("component") in IMPORT_ACTIVITY_COMPONENTS
    ]
    return _build_import_activity_summary(
        entity_id=entity_id,
        operation_events=operation_items,
        artifacts=artifact_items,
        mode=mode,
        repository_backed=repository_backed,
    )


def build_agent_entity_publish_activity_summary(
    store: JsonTaskStore,
    entity_id: str,
) -> dict[str, Any]:
    return build_agent_entity_publish_activity_summary_from_records(
        entity_id=entity_id,
        operation_events=store.list_operation_audit_events(
            resource_type="PLATFORM_ENTITY",
            resource_id=entity_id,
        ),
        artifacts=store.list_artifacts(kind="WORKFLOW_REPORT"),
        mode="LOCAL_PLATFORM_ENTITY_IMPORT_ACTIVITY_SUMMARY",
        repository_backed=False,
    )


def build_agent_entity_publish_activity_summary_for_task(
    store: JsonTaskStore,
    task_id: str,
) -> dict[str, Any]:
    items = [
        build_agent_entity_publish_activity_summary(store, entity.id)
        for entity in store.list_agent_entities(source_task_id=task_id)
    ]
    visible_items = [item for item in items if item.get("visible")]
    latest_sends = sorted(
        (item.get("latestSend") for item in visible_items if item.get("latestSend")),
        key=lambda item: item.get("occurredAt") or "",
        reverse=True,
    )
    latest_results = sorted(
        (item.get("latestResult") for item in visible_items if item.get("latestResult")),
        key=lambda item: item.get("occurredAt") or "",
        reverse=True,
    )
    latest_status_queries = sorted(
        (item.get("latestStatusQuery") for item in visible_items if item.get("latestStatusQuery")),
        key=lambda item: item.get("occurredAt") or "",
        reverse=True,
    )
    latest_send = latest_sends[0] if latest_sends else None
    latest_result = latest_results[0] if latest_results else None
    latest_status_query = latest_status_queries[0] if latest_status_queries else None
    return {
        "component": "AgentEntityImportActivityTaskSummary",
        "mode": "LOCAL_PLATFORM_ENTITY_IMPORT_ACTIVITY_SUMMARY",
        "taskId": task_id,
        "visible": bool(visible_items),
        "entityTotal": len(items),
        "activityEntityTotal": len(visible_items),
        "dryRunTotal": sum(int(item.get("dryRunTotal", 0)) for item in items),
        "sendTotal": sum(int(item.get("sendTotal", 0)) for item in items),
        "statusQueryTotal": sum(int(item.get("statusQueryTotal", 0)) for item in items),
        "resultTotal": sum(int(item.get("resultTotal", 0)) for item in items),
        "signoffTotal": sum(int(item.get("signoffTotal", 0)) for item in items),
        "latestSend": latest_send,
        "latestStatusQuery": latest_status_query,
        "latestResult": latest_result,
        "items": items,
        "summary": {
            "requestSentTotal": sum(1 for item in items if item.get("summary", {}).get("requestSent") is True),
            "statusQueriedTotal": sum(
                1 for item in items if item.get("summary", {}).get("statusQueried") is True
            ),
            "resultRecordedTotal": sum(
                1 for item in items if item.get("summary", {}).get("resultRecorded") is True
            ),
            "signoffRecordedTotal": sum(
                1 for item in items if item.get("summary", {}).get("signoffRecorded") is True
            ),
            "latestStatusCode": latest_send.get("statusCode") if latest_send else None,
            "latestQueryStatusCode": latest_status_query.get("statusCode") if latest_status_query else None,
            "latestQueriedPlatformStatus": latest_status_query.get("agentStatus") if latest_status_query else None,
            "latestSuggestedImportResultStatus": (
                latest_status_query.get("suggestedImportResultStatus") if latest_status_query else None
            ),
            "latestPlatformDraftId": latest_result.get("agentDraftId") if latest_result else None,
            "latestPlatformStatus": latest_result.get("agentStatus") if latest_result else None,
            "agentSideReviewed": bool(latest_result and latest_result.get("agentSideReviewed") is True),
            "acceptedForDraft": bool(latest_result and latest_result.get("acceptedForDraft") is True),
            "rejectedByPlatform": bool(latest_result and latest_result.get("rejectedByPlatform") is True),
            "latestRealPlatformImportAccepted": bool(
                latest_send and latest_send.get("realAgentImportAccepted") is True
            ),
            "secretValueReturned": False,
            "databaseWrittenByLocalSystem": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
        "safety": {
            "readOnly": True,
            "reportContentRead": False,
            "secretValueReturned": False,
            "databaseWrittenByLocalSystem": False,
            "manualPlatformReviewRequired": True,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    }
