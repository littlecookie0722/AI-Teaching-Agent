"""Backend audit query service.

This service centralizes read-only audit queries for the HTTP adapter. It keeps
filter validation and JSON/Core SQLite branching out of the router while
preserving the existing local staging response shape.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from cli.ai_task import ReviewAction
from cli.audit import OperationAction, OperationResourceType
from cli.provider_audit import ProviderCallStatus
from cli.store import JsonTaskStore

from backend.core_repository import CoreRepositoryError
from backend.core_service import BackendCoreService


class BackendAuditQueryServiceError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


class BackendAuditQueryService:
    def __init__(self, *, store: JsonTaskStore, core_service: BackendCoreService) -> None:
        self.store = store
        self.core_service = core_service

    def list_provider_call_audit_events(self, query: dict[str, str]) -> dict[str, Any]:
        status = query.get("status")
        if status and status not in {item.value for item in ProviderCallStatus}:
            raise BackendAuditQueryServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "status", "reason": "非法状态"}],
            )
        events = self.store.list_provider_call_audit_events(
            provider_id=query.get("providerId"),
            operation=query.get("operation"),
            status=status,
            prompt_id=query.get("promptId"),
            trace_id=query.get("traceId"),
            actor=query.get("actor"),
        )
        filters = {
            "providerId": query.get("providerId"),
            "operation": query.get("operation"),
            "status": status,
            "promptId": query.get("promptId"),
            "traceId": query.get("traceId"),
            "actor": query.get("actor"),
        }
        return self._local_payload([event.to_dict() for event in events], filters)

    def list_review_audit_events(self, query: dict[str, str]) -> dict[str, Any]:
        action = query.get("action")
        if action and action not in {item.value for item in ReviewAction}:
            raise BackendAuditQueryServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "action", "reason": "非法动作"}],
            )
        filters = {"taskId": query.get("taskId"), "action": action, "actor": query.get("actor")}
        repository, policy = self._resolve_core_repository(query)
        if repository is not None:
            try:
                event_payloads = self.core_service.list_review_audit_event_payloads(
                    repository,
                    task_id=query.get("taskId"),
                    action=action,
                    actor=query.get("actor"),
                )
            except (sqlite3.Error, CoreRepositoryError) as exc:
                raise self._core_read_error(exc) from exc
            return self._core_payload(event_payloads, filters, repository.db_path, policy)
        events = self.store.list_review_audit_events(
            task_id=query.get("taskId"),
            action=action,
            actor=query.get("actor"),
        )
        return self._local_payload([event.to_dict() for event in events], filters)

    def list_operation_audit_events(self, query: dict[str, str]) -> dict[str, Any]:
        action = query.get("action")
        resource_type = query.get("resourceType")
        if action and action not in {item.value for item in OperationAction}:
            raise BackendAuditQueryServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "action", "reason": "非法动作"}],
            )
        if resource_type and resource_type not in {item.value for item in OperationResourceType}:
            raise BackendAuditQueryServiceError(
                "VALIDATION_ERROR",
                "参数错误",
                [{"field": "resourceType", "reason": "非法资源类型"}],
            )
        filters = {
            "resourceType": resource_type,
            "resourceId": query.get("resourceId"),
            "action": action,
            "actor": query.get("actor"),
        }
        repository, policy = self._resolve_core_repository(query)
        if repository is not None:
            try:
                event_payloads = self.core_service.list_operation_audit_event_payloads(
                    repository,
                    resource_type=resource_type,
                    resource_id=query.get("resourceId"),
                    action=action,
                    actor=query.get("actor"),
                )
            except (sqlite3.Error, CoreRepositoryError) as exc:
                raise self._core_read_error(exc) from exc
            return self._core_payload(event_payloads, filters, repository.db_path, policy)
        events = self.store.list_operation_audit_events(
            resource_type=resource_type,
            resource_id=query.get("resourceId"),
            action=action,
            actor=query.get("actor"),
        )
        return self._local_payload([event.to_dict() for event in events], filters)

    def _resolve_core_repository(self, query: dict[str, str]):
        try:
            return self.core_service.resolve_repository(query)
        except CoreRepositoryError as exc:
            raise BackendAuditQueryServiceError(exc.code, exc.message, exc.errors) from exc

    def _core_read_error(self, exc: Exception) -> BackendAuditQueryServiceError:
        if isinstance(exc, CoreRepositoryError):
            return BackendAuditQueryServiceError(exc.code, exc.message, exc.errors)
        return BackendAuditQueryServiceError(
            "BACKEND_CORE_SQLITE_READONLY_ERROR",
            "Backend Core 本地 SQLite 只读查询失败",
            [{"field": "coreDbPath", "reason": str(exc)}],
        )

    def _local_payload(self, items: list[dict[str, Any]], filters: dict[str, Any]) -> dict[str, Any]:
        return {
            "items": items,
            "total": len(items),
            "filters": filters,
            "mode": "MOCK_ONLY",
        }

    def _core_payload(
        self,
        items: list[dict[str, Any]],
        filters: dict[str, Any],
        db_path: Any,
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "items": items,
            "total": len(items),
            "filters": filters,
            "mode": (
                "LOCAL_SQLITE_BACKEND_CORE_READONLY"
                if db_path is not None
                else "BACKEND_CORE_REPOSITORY_READONLY"
            ),
            "repositoryKind": policy["repositoryKind"],
            "coreDbPath": str(db_path) if db_path is not None else None,
            "dbPathSource": policy["dbPathSource"],
            "databaseUrlSummary": policy.get("databaseUrlSummary"),
            "localSqliteRead": db_path is not None,
            "externalDatabaseRead": db_path is None,
            "productionDatabaseWritten": False,
            "productionQueueUsed": False,
        }
