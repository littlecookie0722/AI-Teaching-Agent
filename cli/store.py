"""JSON-file backed mock store for Phase 1 CLI data."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .artifact import ArtifactRecord
from .ai_task import AiTask, ReviewAuditEvent
from .audit import OperationAuditEvent
from .environment import EnvironmentInstance
from .grading_job import GradingJob
from .grading_record import GradingRecord
from .mcp_audit import McpToolCallRecord
from .agent_entity import AgentEntityRecord
from .provider_audit import ProviderCallAuditEvent
from .workflow import WorkflowRun


def _empty_store_data() -> dict[str, dict]:
    return {
        "tasks": {},
        "environments": {},
        "reviewAuditEvents": {},
        "operationAuditEvents": {},
        "providerCallAuditEvents": {},
        "gradingJobs": {},
        "gradingRecords": {},
        "mcpToolCallRecords": {},
        "agentEntities": {},
        "workflowRuns": {},
        "artifacts": {},
    }


def default_store_path() -> Path:
    configured = os.environ.get("LAB_CLI_STORE")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent / ".lab_cli_store.json"


class JsonTaskStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_store_path()

    def _read(self) -> dict[str, dict]:
        if not self.path.exists():
            return _empty_store_data()
        with self.path.open("r", encoding="utf-8") as file:
            try:
                data = json.load(file)
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._backup_corrupt_store()
                return _empty_store_data()
        data.setdefault("tasks", {})
        data.setdefault("environments", {})
        data.setdefault("reviewAuditEvents", {})
        data.setdefault("operationAuditEvents", {})
        data.setdefault("providerCallAuditEvents", {})
        data.setdefault("gradingJobs", {})
        data.setdefault("gradingRecords", {})
        data.setdefault("mcpToolCallRecords", {})
        data.setdefault("agentEntities", {})
        data.setdefault("workflowRuns", {})
        data.setdefault("artifacts", {})
        # Backward compatibility: migrate old platformEntities to agentEntities
        if "platformEntities" in data and "agentEntities" not in data:
            data["agentEntities"] = data.pop("platformEntities")
        elif "platformEntities" in data:
            del data["platformEntities"]
        return data

    def _backup_corrupt_store(self) -> None:
        if not self.path.exists():
            return
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        backup_path = self.path.with_name(f"{self.path.name}.corrupt-{timestamp}")
        counter = 1
        while backup_path.exists():
            backup_path = self.path.with_name(f"{self.path.name}.corrupt-{timestamp}-{counter}")
            counter += 1
        try:
            shutil.copy2(self.path, backup_path)
        except OSError:
            return
        try:
            self.path.write_text(json.dumps(_empty_store_data(), ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            return

    def _write(self, data: dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def save(self, task: AiTask) -> AiTask:
        data = self._read()
        data.setdefault("tasks", {})[task.id] = task.to_dict()
        self._write(data)
        return task

    def get(self, task_id: str) -> AiTask | None:
        data = self._read()
        payload = data.get("tasks", {}).get(task_id)
        if payload is None:
            return None
        return AiTask.from_dict(payload)

    def list(self, *, status: str | None = None, task_type: str | None = None) -> list[AiTask]:
        data = self._read()
        tasks = [AiTask.from_dict(payload) for payload in data.get("tasks", {}).values()]
        if status:
            tasks = [task for task in tasks if task.status.value == status]
        if task_type:
            tasks = [task for task in tasks if task.taskType == task_type]
        return sorted(tasks, key=lambda task: task.createdAt, reverse=True)

    def save_environment(self, environment: EnvironmentInstance) -> EnvironmentInstance:
        data = self._read()
        data.setdefault("environments", {})[environment.id] = environment.to_dict()
        self._write(data)
        return environment

    def get_environment(self, env_id: str) -> EnvironmentInstance | None:
        data = self._read()
        payload = data.get("environments", {}).get(env_id)
        if payload is None:
            return None
        return EnvironmentInstance.from_dict(payload)

    def list_environments(self, *, status: str | None = None, env_type: str | None = None) -> list[EnvironmentInstance]:
        data = self._read()
        environments = [
            EnvironmentInstance.from_dict(payload) for payload in data.get("environments", {}).values()
        ]
        if status:
            environments = [environment for environment in environments if environment.status.value == status]
        if env_type:
            environments = [environment for environment in environments if environment.envType.value == env_type]
        return sorted(environments, key=lambda environment: environment.createdAt, reverse=True)

    def save_review_audit_event(self, event: ReviewAuditEvent) -> ReviewAuditEvent:
        data = self._read()
        data.setdefault("reviewAuditEvents", {})[event.id] = event.to_dict()
        self._write(data)
        return event

    def list_review_audit_events(
        self,
        *,
        task_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[ReviewAuditEvent]:
        data = self._read()
        events = [
            ReviewAuditEvent.from_dict(payload)
            for payload in data.get("reviewAuditEvents", {}).values()
        ]
        if task_id:
            events = [event for event in events if event.taskId == task_id]
        if action:
            events = [event for event in events if event.action.value == action]
        if actor:
            events = [event for event in events if event.actor == actor]
        return sorted(events, key=lambda event: event.occurredAt, reverse=True)

    def save_operation_audit_event(self, event: OperationAuditEvent) -> OperationAuditEvent:
        data = self._read()
        data.setdefault("operationAuditEvents", {})[event.id] = event.to_dict()
        self._write(data)
        return event

    def list_operation_audit_events(
        self,
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        actor: str | None = None,
    ) -> list[OperationAuditEvent]:
        data = self._read()
        events = [
            OperationAuditEvent.from_dict(payload)
            for payload in data.get("operationAuditEvents", {}).values()
        ]
        if resource_type:
            events = [event for event in events if event.resourceType.value == resource_type]
        if resource_id:
            events = [event for event in events if event.resourceId == resource_id]
        if action:
            events = [event for event in events if event.action.value == action]
        if actor:
            events = [event for event in events if event.actor == actor]
        return sorted(events, key=lambda event: event.occurredAt, reverse=True)

    def save_provider_call_audit_event(self, event: ProviderCallAuditEvent) -> ProviderCallAuditEvent:
        data = self._read()
        data.setdefault("providerCallAuditEvents", {})[event.id] = event.to_dict()
        self._write(data)
        return event

    def list_provider_call_audit_events(
        self,
        *,
        provider_id: str | None = None,
        operation: str | None = None,
        status: str | None = None,
        prompt_id: str | None = None,
        trace_id: str | None = None,
        actor: str | None = None,
    ) -> list[ProviderCallAuditEvent]:
        data = self._read()
        events = [
            ProviderCallAuditEvent.from_dict(payload)
            for payload in data.get("providerCallAuditEvents", {}).values()
        ]
        if provider_id:
            events = [event for event in events if event.providerId == provider_id]
        if operation:
            events = [event for event in events if event.operation == operation]
        if status:
            events = [event for event in events if event.status.value == status]
        if prompt_id:
            events = [event for event in events if event.promptId == prompt_id]
        if trace_id:
            events = [event for event in events if event.traceId == trace_id]
        if actor:
            events = [event for event in events if event.actor == actor]
        return sorted(events, key=lambda event: event.occurredAt, reverse=True)

    def save_grading_record(self, record: GradingRecord) -> GradingRecord:
        data = self._read()
        data.setdefault("gradingRecords", {})[record.id] = record.to_dict()
        self._write(data)
        return record

    def save_grading_job(self, job: GradingJob) -> GradingJob:
        data = self._read()
        data.setdefault("gradingJobs", {})[job.id] = job.to_dict()
        self._write(data)
        return job

    def get_grading_job(self, job_id: str) -> GradingJob | None:
        data = self._read()
        payload = data.get("gradingJobs", {}).get(job_id)
        if payload is None:
            return None
        return GradingJob.from_dict(payload)

    def list_grading_jobs(
        self,
        *,
        task_id: str | None = None,
        submission_id: str | None = None,
        status: str | None = None,
        candidate_id: str | None = None,
    ) -> list[GradingJob]:
        data = self._read()
        jobs = [GradingJob.from_dict(payload) for payload in data.get("gradingJobs", {}).values()]
        if task_id:
            jobs = [job for job in jobs if job.taskId == task_id]
        if submission_id:
            jobs = [job for job in jobs if job.submissionId == submission_id]
        if status:
            jobs = [job for job in jobs if job.status.value == status]
        if candidate_id:
            jobs = [job for job in jobs if job.candidateId == candidate_id]
        return sorted(jobs, key=lambda job: job.createdAt, reverse=True)

    def get_grading_record(self, record_id: str) -> GradingRecord | None:
        data = self._read()
        payload = data.get("gradingRecords", {}).get(record_id)
        if payload is None:
            return None
        return GradingRecord.from_dict(payload)

    def list_grading_records(
        self,
        *,
        task_id: str | None = None,
        submission_id: str | None = None,
        status: str | None = None,
        candidate_id: str | None = None,
    ) -> list[GradingRecord]:
        data = self._read()
        records = [
            GradingRecord.from_dict(payload)
            for payload in data.get("gradingRecords", {}).values()
        ]
        if task_id:
            records = [record for record in records if record.taskId == task_id]
        if submission_id:
            records = [record for record in records if record.submissionId == submission_id]
        if status:
            records = [record for record in records if record.status.value == status]
        if candidate_id:
            records = [record for record in records if record.candidateId == candidate_id]
        return sorted(records, key=lambda record: record.createdAt, reverse=True)

    def save_mcp_tool_call_record(self, record: McpToolCallRecord) -> McpToolCallRecord:
        data = self._read()
        data.setdefault("mcpToolCallRecords", {})[record.id] = record.to_dict()
        self._write(data)
        return record

    def list_mcp_tool_call_records(
        self,
        *,
        tool_name: str | None = None,
        status: str | None = None,
        trace_id: str | None = None,
        actor: str | None = None,
        backend_path: str | None = None,
    ) -> list[McpToolCallRecord]:
        data = self._read()
        records = [
            McpToolCallRecord.from_dict(payload)
            for payload in data.get("mcpToolCallRecords", {}).values()
        ]
        if tool_name:
            records = [record for record in records if record.toolName == tool_name]
        if status:
            records = [record for record in records if record.status.value == status]
        if trace_id:
            records = [record for record in records if record.traceId == trace_id]
        if actor:
            records = [record for record in records if record.actor == actor]
        if backend_path:
            records = [record for record in records if record.backendPath == backend_path]
        return sorted(records, key=lambda record: record.occurredAt, reverse=True)

    def save_agent_entity(self, entity: AgentEntityRecord) -> AgentEntityRecord:
        data = self._read()
        data.setdefault("agentEntities", {})[entity.id] = entity.to_dict()
        self._write(data)
        return entity

    def get_agent_entity(self, entity_id: str) -> AgentEntityRecord | None:
        data = self._read()
        payload = data.get("agentEntities", {}).get(entity_id)
        if payload is None:
            return None
        return AgentEntityRecord.from_dict(payload)

    def list_agent_entities(
        self,
        *,
        entity_type: str | None = None,
        source_task_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[AgentEntityRecord]:
        data = self._read()
        entities = [
            AgentEntityRecord.from_dict(payload)
            for payload in data.get("agentEntities", {}).values()
        ]
        if entity_type:
            entities = [entity for entity in entities if entity.entityType.value == entity_type]
        if source_task_id:
            entities = [entity for entity in entities if entity.sourceTaskId == source_task_id]
        if trace_id:
            entities = [entity for entity in entities if entity.traceId == trace_id]
        return sorted(entities, key=lambda entity: entity.createdAt, reverse=True)

    def save_workflow_run(self, run: WorkflowRun) -> WorkflowRun:
        data = self._read()
        data.setdefault("workflowRuns", {})[run.id] = run.to_dict()
        self._write(data)
        return run

    def get_workflow_run(self, run_id: str) -> WorkflowRun | None:
        data = self._read()
        payload = data.get("workflowRuns", {}).get(run_id)
        if payload is None:
            return None
        return WorkflowRun.from_dict(payload)

    def list_workflow_runs(
        self,
        *,
        workflow_id: str | None = None,
        status: str | None = None,
        trace_id: str | None = None,
    ) -> list[WorkflowRun]:
        data = self._read()
        runs = [WorkflowRun.from_dict(payload) for payload in data.get("workflowRuns", {}).values()]
        if workflow_id:
            runs = [run for run in runs if run.workflowId == workflow_id]
        if status:
            runs = [run for run in runs if run.status.value == status]
        if trace_id:
            runs = [run for run in runs if run.traceId == trace_id]
        return sorted(runs, key=lambda run: run.createdAt, reverse=True)

    def save_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        data = self._read()
        data.setdefault("artifacts", {})[artifact.id] = artifact.to_dict()
        self._write(data)
        return artifact

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        data = self._read()
        payload = data.get("artifacts", {}).get(artifact_id)
        if payload is None:
            return None
        return ArtifactRecord.from_dict(payload)

    def list_artifacts(
        self,
        *,
        kind: str | None = None,
        task_id: str | None = None,
        workflow_run_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[ArtifactRecord]:
        data = self._read()
        artifacts = [ArtifactRecord.from_dict(payload) for payload in data.get("artifacts", {}).values()]
        if kind:
            artifacts = [artifact for artifact in artifacts if artifact.kind.value == kind]
        if task_id:
            artifacts = [artifact for artifact in artifacts if artifact.taskId == task_id]
        if workflow_run_id:
            artifacts = [artifact for artifact in artifacts if artifact.workflowRunId == workflow_run_id]
        if trace_id:
            artifacts = [artifact for artifact in artifacts if artifact.traceId == trace_id]
        return sorted(artifacts, key=lambda artifact: artifact.createdAt, reverse=True)
