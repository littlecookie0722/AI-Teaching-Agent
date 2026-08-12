"""Local SQLite repository for grading jobs and grading records.

This module is a development/staging persistence boundary. It writes only to a
local SQLite file and must not be treated as a production database adapter.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cli.ai_task import utc_now
from cli.grading_job import GradingJob
from cli.grading_record import GradingRecord
from cli.store import JsonTaskStore


DEFAULT_GRADING_DB_PATH = "examples/output/grading-local.sqlite3"
DEFAULT_CLAIM_LEASE_SECONDS = 300
DEFAULT_MAX_ATTEMPTS = 3
SCHEMA_VERSION = "2"


class GradingRepositoryError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


class GradingSQLiteRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize_schema(self) -> dict[str, Any]:
        try:
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS grading_repository_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS grading_jobs (
                        id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        task_id TEXT,
                        submission_id TEXT NOT NULL,
                        candidate_id TEXT,
                        reviewer TEXT,
                        grading_path TEXT NOT NULL,
                        submission_path TEXT NOT NULL,
                        output_path TEXT NOT NULL,
                        report_id TEXT,
                        report_path TEXT,
                        grading_record_id TEXT,
                        include_controlled_command INTEGER NOT NULL,
                        fail_on_controlled_unavailable INTEGER NOT NULL,
                        image TEXT NOT NULL,
                        error_code TEXT,
                        error_message TEXT,
                        errors_json TEXT NOT NULL,
                        summary_json TEXT NOT NULL,
                        safety_json TEXT NOT NULL,
                        trace_id TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        started_at TEXT,
                        finished_at TEXT,
                        claim_owner TEXT,
                        claimed_at TEXT,
                        claim_expires_at TEXT,
                        attempt_count INTEGER NOT NULL DEFAULT 0,
                        raw_json TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_grading_jobs_task_id
                        ON grading_jobs(task_id);
                    CREATE INDEX IF NOT EXISTS idx_grading_jobs_submission_id
                        ON grading_jobs(submission_id);
                    CREATE INDEX IF NOT EXISTS idx_grading_jobs_candidate_id
                        ON grading_jobs(candidate_id);
                    CREATE INDEX IF NOT EXISTS idx_grading_jobs_status
                        ON grading_jobs(status);
                    CREATE INDEX IF NOT EXISTS idx_grading_jobs_claim_expires_at
                        ON grading_jobs(claim_expires_at);

                    CREATE TABLE IF NOT EXISTS grading_records (
                        id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        submission_id TEXT NOT NULL,
                        grading_id TEXT,
                        report_path TEXT NOT NULL,
                        report_mode TEXT NOT NULL,
                        source_report_id TEXT,
                        task_id TEXT,
                        candidate_id TEXT,
                        reviewer TEXT,
                        reviewed_by TEXT,
                        reviewed_at TEXT,
                        review_decision TEXT,
                        review_reason TEXT,
                        total_score INTEGER NOT NULL,
                        earned_score INTEGER NOT NULL,
                        covered_score INTEGER NOT NULL,
                        missing_score INTEGER NOT NULL,
                        coverage_ratio REAL NOT NULL,
                        score_preview_status TEXT,
                        decision_note_recommendation TEXT,
                        manual_review_checklist_status TEXT,
                        evidence_summary_json TEXT NOT NULL,
                        safety_json TEXT NOT NULL,
                        trace_id TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        raw_json TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_grading_records_task_id
                        ON grading_records(task_id);
                    CREATE INDEX IF NOT EXISTS idx_grading_records_submission_id
                        ON grading_records(submission_id);
                    CREATE INDEX IF NOT EXISTS idx_grading_records_candidate_id
                        ON grading_records(candidate_id);
                    CREATE INDEX IF NOT EXISTS idx_grading_records_status
                        ON grading_records(status);
                    """
                )
                _ensure_column(connection, "grading_jobs", "claim_owner", "TEXT")
                _ensure_column(connection, "grading_jobs", "claimed_at", "TEXT")
                _ensure_column(connection, "grading_jobs", "claim_expires_at", "TEXT")
                _ensure_column(connection, "grading_jobs", "attempt_count", "INTEGER NOT NULL DEFAULT 0")
                connection.execute(
                    """
                    INSERT OR REPLACE INTO grading_repository_meta(key, value, updated_at)
                    VALUES ('schema_version', ?, CURRENT_TIMESTAMP)
                    """,
                    (SCHEMA_VERSION,),
                )
            return self._schema_summary()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc

    def save_grading_job(self, job: GradingJob) -> GradingJob:
        self.initialize_schema()
        payload = job.to_dict()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO grading_jobs (
                        id, status, task_id, submission_id, candidate_id, reviewer,
                        grading_path, submission_path, output_path, report_id, report_path,
                        grading_record_id, include_controlled_command,
                        fail_on_controlled_unavailable, image, error_code, error_message,
                        errors_json, summary_json, safety_json, trace_id, created_at,
                        updated_at, started_at, finished_at, claim_owner, claimed_at,
                        claim_expires_at, attempt_count, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["id"],
                        payload["status"],
                        payload.get("taskId"),
                        payload["submissionId"],
                        payload.get("candidateId"),
                        payload.get("reviewer"),
                        payload["gradingPath"],
                        payload["submissionPath"],
                        payload["outputPath"],
                        payload.get("reportId"),
                        payload.get("reportPath"),
                        payload.get("gradingRecordId"),
                        _bool_to_int(payload.get("includeControlledCommand")),
                        _bool_to_int(payload.get("failOnControlledUnavailable")),
                        payload["image"],
                        payload.get("errorCode"),
                        payload.get("errorMessage"),
                        _dump_json(payload.get("errors", [])),
                        _dump_json(payload.get("summary", {})),
                        _dump_json(payload.get("safety", {})),
                        payload["traceId"],
                        payload["createdAt"],
                        payload["updatedAt"],
                        payload.get("startedAt"),
                        payload.get("finishedAt"),
                        payload.get("claimOwner"),
                        payload.get("claimedAt"),
                        payload.get("claimExpiresAt"),
                        int(payload.get("attemptCount") or 0),
                        _dump_json(payload),
                    ),
                )
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return job

    def get_grading_job(self, job_id: str) -> GradingJob | None:
        self.initialize_schema()
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT raw_json FROM grading_jobs WHERE id = ?",
                    (job_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        if row is None:
            return None
        return GradingJob.from_dict(_load_json(row["raw_json"]))

    def list_grading_jobs(
        self,
        *,
        task_id: str | None = None,
        submission_id: str | None = None,
        status: str | None = None,
        candidate_id: str | None = None,
    ) -> list[GradingJob]:
        self.initialize_schema()
        query = "SELECT raw_json FROM grading_jobs"
        where, values = _filters(
            {
                "task_id": task_id,
                "submission_id": submission_id,
                "status": status,
                "candidate_id": candidate_id,
            }
        )
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY created_at DESC"
        try:
            with self._connect() as connection:
                rows = connection.execute(query, values).fetchall()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return [GradingJob.from_dict(_load_json(row["raw_json"])) for row in rows]

    def get_next_runnable_grading_job(self) -> GradingJob | None:
        return self.claim_next_runnable_grading_job(actor="local-grading-worker")

    def claim_next_runnable_grading_job(
        self,
        *,
        actor: str,
        job_id: str | None = None,
        lease_seconds: int = DEFAULT_CLAIM_LEASE_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> GradingJob | None:
        self.initialize_schema()
        now = utc_now()
        expires_at = _utc_after_seconds(lease_seconds)
        max_attempts = _positive_int(max_attempts, DEFAULT_MAX_ATTEMPTS)
        selector = """
            SELECT id, raw_json FROM grading_jobs
            WHERE status IN ('QUEUED', 'FAILED')
              AND (claim_expires_at IS NULL OR claim_expires_at <= ?)
              AND attempt_count < ?
        """
        values: list[Any] = [now, max_attempts]
        if job_id:
            selector += " AND id = ?"
            values.append(job_id)
        selector += " ORDER BY created_at ASC LIMIT 1"
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(selector, values).fetchone()
                if row is None:
                    connection.commit()
                    return None
                payload = _load_json(row["raw_json"])
                job = GradingJob.from_dict(payload)
                before_status = job.status.value
                job.status = type(job.status).RUNNING
                job.claimOwner = actor
                job.claimedAt = now
                job.claimExpiresAt = expires_at
                job.attemptCount = int(job.attemptCount or 0) + 1
                job.errorCode = None
                job.errorMessage = None
                job.errors = []
                job.finishedAt = None
                job.updatedAt = now
                job.safety = {
                    **job.safety,
                    "claimLeaseActive": True,
                    "claimOwner": actor,
                    "claimedAt": now,
                    "claimExpiresAt": expires_at,
                    "claimBeforeStatus": before_status,
                    "claimAttemptCount": job.attemptCount,
                    "maxAttempts": max_attempts,
                    "productionQueueUsed": False,
                }
                raw_json = _dump_json(job.to_dict())
                updated = connection.execute(
                    """
                    UPDATE grading_jobs
                    SET status = 'RUNNING',
                        claim_owner = ?,
                        claimed_at = ?,
                        claim_expires_at = ?,
                        attempt_count = ?,
                        error_code = NULL,
                        error_message = NULL,
                        errors_json = ?,
                        safety_json = ?,
                        finished_at = NULL,
                        updated_at = ?,
                        raw_json = ?
                    WHERE id = ?
                      AND status IN ('QUEUED', 'FAILED')
                      AND (claim_expires_at IS NULL OR claim_expires_at <= ?)
                      AND attempt_count < ?
                    """,
                    (
                        actor,
                        now,
                        expires_at,
                        job.attemptCount,
                        _dump_json([]),
                        _dump_json(job.safety),
                        now,
                        raw_json,
                        row["id"],
                        now,
                        max_attempts,
                    ),
                ).rowcount
                connection.commit()
                if updated != 1:
                    return None
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return job

    def recover_expired_grading_job_claims(
        self,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> dict[str, Any]:
        self.initialize_schema()
        now = utc_now()
        max_attempts = _positive_int(max_attempts, DEFAULT_MAX_ATTEMPTS)
        requeued: list[str] = []
        failed: list[str] = []
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                rows = connection.execute(
                    """
                    SELECT id, raw_json FROM grading_jobs
                    WHERE status = 'RUNNING'
                      AND claim_expires_at IS NOT NULL
                      AND claim_expires_at <= ?
                    ORDER BY claim_expires_at ASC, created_at ASC
                    """,
                    (now,),
                ).fetchall()
                for row in rows:
                    job = GradingJob.from_dict(_load_json(row["raw_json"]))
                    attempt_count = int(job.attemptCount or 0)
                    if attempt_count >= max_attempts:
                        job.status = type(job.status).FAILED
                        job.errorCode = "GRADING_JOB_RETRY_LIMIT_EXCEEDED"
                        job.errorMessage = "Grading 评分任务重试次数已达上限"
                        job.errors = [
                            {
                                "field": "attemptCount",
                                "reason": f"max attempts {max_attempts} reached",
                            }
                        ]
                        job.finishedAt = now
                        failed.append(job.id)
                        recover_action = "FAILED_MAX_ATTEMPTS"
                    else:
                        job.status = type(job.status).QUEUED
                        job.errorCode = None
                        job.errorMessage = None
                        job.errors = []
                        job.finishedAt = None
                        recover_action = "REQUEUED"
                        requeued.append(job.id)
                    job.claimOwner = None
                    job.claimedAt = None
                    job.claimExpiresAt = None
                    job.updatedAt = now
                    job.safety = {
                        **job.safety,
                        "claimLeaseActive": False,
                        "expiredClaimRecovered": True,
                        "expiredClaimRecoveredAt": now,
                        "expiredClaimRecoveryAction": recover_action,
                        "maxAttempts": max_attempts,
                        "productionQueueUsed": False,
                    }
                    payload = job.to_dict()
                    connection.execute(
                        """
                        UPDATE grading_jobs
                        SET status = ?,
                            claim_owner = NULL,
                            claimed_at = NULL,
                            claim_expires_at = NULL,
                            error_code = ?,
                            error_message = ?,
                            errors_json = ?,
                            summary_json = ?,
                            safety_json = ?,
                            updated_at = ?,
                            finished_at = ?,
                            raw_json = ?
                        WHERE id = ?
                          AND status = 'RUNNING'
                          AND claim_expires_at IS NOT NULL
                          AND claim_expires_at <= ?
                        """,
                        (
                            payload["status"],
                            payload.get("errorCode"),
                            payload.get("errorMessage"),
                            _dump_json(payload.get("errors", [])),
                            _dump_json(payload.get("summary", {})),
                            _dump_json(payload.get("safety", {})),
                            now,
                            payload.get("finishedAt"),
                            _dump_json(payload),
                            row["id"],
                            now,
                        ),
                    )
                connection.commit()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return {
            "expiredClaimTotal": len(requeued) + len(failed),
            "requeuedTotal": len(requeued),
            "failedTotal": len(failed),
            "requeuedJobIds": requeued,
            "failedJobIds": failed,
            "maxAttempts": max_attempts,
            "mode": "LOCAL_SQLITE_GRADING_CLAIM_RECOVERY",
            "safety": {
                "localSqliteOnly": True,
                "expiredClaimRecoveryEnabled": True,
                "productionDatabaseWritten": False,
                "productionQueueUsed": False,
                "persistentBackgroundWorker": False,
                "autoApproveAllowed": False,
                "realPublish": False,
            },
        }

    def save_grading_record(self, record: GradingRecord) -> GradingRecord:
        self.initialize_schema()
        payload = record.to_dict()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO grading_records (
                        id, status, submission_id, grading_id, report_path, report_mode,
                        source_report_id, task_id, candidate_id, reviewer, reviewed_by,
                        reviewed_at, review_decision, review_reason, total_score,
                        earned_score, covered_score, missing_score, coverage_ratio,
                        score_preview_status, decision_note_recommendation,
                        manual_review_checklist_status, evidence_summary_json,
                        safety_json, trace_id, created_at, updated_at, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["id"],
                        payload["status"],
                        payload["submissionId"],
                        payload.get("gradingId"),
                        payload["reportPath"],
                        payload["reportMode"],
                        payload.get("sourceReportId"),
                        payload.get("taskId"),
                        payload.get("candidateId"),
                        payload.get("reviewer"),
                        payload.get("reviewedBy"),
                        payload.get("reviewedAt"),
                        payload.get("reviewDecision"),
                        payload.get("reviewReason"),
                        payload["totalScore"],
                        payload["earnedScore"],
                        payload["coveredScore"],
                        payload["missingScore"],
                        payload["coverageRatio"],
                        payload.get("scorePreviewStatus"),
                        payload.get("decisionNoteRecommendation"),
                        payload.get("manualReviewChecklistStatus"),
                        _dump_json(payload.get("evidenceSummary", {})),
                        _dump_json(payload.get("safety", {})),
                        payload["traceId"],
                        payload["createdAt"],
                        payload["updatedAt"],
                        _dump_json(payload),
                    ),
                )
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return record

    def get_grading_record(self, record_id: str) -> GradingRecord | None:
        self.initialize_schema()
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT raw_json FROM grading_records WHERE id = ?",
                    (record_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        if row is None:
            return None
        return GradingRecord.from_dict(_load_json(row["raw_json"]))

    def list_grading_records(
        self,
        *,
        task_id: str | None = None,
        submission_id: str | None = None,
        status: str | None = None,
        candidate_id: str | None = None,
    ) -> list[GradingRecord]:
        self.initialize_schema()
        query = "SELECT raw_json FROM grading_records"
        where, values = _filters(
            {
                "task_id": task_id,
                "submission_id": submission_id,
                "status": status,
                "candidate_id": candidate_id,
            }
        )
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY created_at DESC"
        try:
            with self._connect() as connection:
                rows = connection.execute(query, values).fetchall()
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return [GradingRecord.from_dict(_load_json(row["raw_json"])) for row in rows]

    def summary(self) -> dict[str, Any]:
        self.initialize_schema()
        try:
            with self._connect() as connection:
                job_total = _count(connection, "grading_jobs")
                record_total = _count(connection, "grading_records")
                jobs_by_status = _count_by_status(connection, "grading_jobs")
                records_by_status = _count_by_status(connection, "grading_records")
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc) from exc
        return {
            **self._schema_summary(),
            "jobTotal": job_total,
            "recordTotal": record_total,
            "jobsByStatus": jobs_by_status,
            "recordsByStatus": records_by_status,
        }

    def _connect(self) -> sqlite3.Connection:
        if self.db_path.exists() and self.db_path.is_dir():
            raise GradingRepositoryError(
                "LOCAL_SQLITE_PATH_ERROR",
                "本地 SQLite 路径不能是目录",
                [{"field": "dbPath", "reason": "path is directory"}],
            )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _schema_summary(self) -> dict[str, Any]:
        return {
            "dbPath": str(self.db_path),
            "schemaVersion": SCHEMA_VERSION,
            "tables": ["grading_repository_meta", "grading_jobs", "grading_records"],
            "claimLeaseSeconds": DEFAULT_CLAIM_LEASE_SECONDS,
            "maxAttempts": DEFAULT_MAX_ATTEMPTS,
            "mode": "LOCAL_SQLITE_GRADING_REPOSITORY",
            "safety": {
                "localSqliteOnly": True,
                "claimLeaseEnabled": True,
                "expiredClaimRecoveryEnabled": True,
                "productionDatabaseWritten": False,
                "queuePersistedToProduction": False,
                "workerStarted": False,
                "autoApproveAllowed": False,
                "realPublish": False,
            },
        }

    def _sqlite_error(self, exc: sqlite3.Error) -> GradingRepositoryError:
        return GradingRepositoryError(
            "LOCAL_SQLITE_ERROR",
            "本地 SQLite 操作失败",
            [{"field": "dbPath", "reason": str(exc)}],
        )


def sync_grading_repository_from_store(
    *,
    repository: GradingSQLiteRepository,
    store: JsonTaskStore,
) -> dict[str, Any]:
    repository.initialize_schema()
    jobs = store.list_grading_jobs()
    records = store.list_grading_records()
    for job in jobs:
        repository.save_grading_job(job)
    for record in records:
        repository.save_grading_record(record)
    return {
        "jobsSynced": len(jobs),
        "recordsSynced": len(records),
        "summary": repository.summary(),
        "mode": "LOCAL_JSON_STORE_TO_SQLITE_SYNC",
        "safety": {
            "source": "JsonTaskStore.gradingJobs + JsonTaskStore.gradingRecords",
            "localSqliteOnly": True,
            "productionDatabaseWritten": False,
            "queuePersistedToProduction": False,
            "workerStarted": False,
            "autoApproveAllowed": False,
            "realPublish": False,
        },
    }


def _filters(values: dict[str, str | None]) -> tuple[list[str], list[str]]:
    where: list[str] = []
    parameters: list[str] = []
    for field, value in values.items():
        if value is None:
            continue
        where.append(f"{field} = ?")
        parameters.append(value)
    return where, parameters


def _count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
    return int(row["total"] or 0)


def _count_by_status(connection: sqlite3.Connection, table: str) -> dict[str, int]:
    rows = connection.execute(
        f"SELECT status, COUNT(*) AS total FROM {table} GROUP BY status ORDER BY status"
    ).fetchall()
    return {str(row["status"]): int(row["total"] or 0) for row in rows}


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {str(row["name"]) for row in rows}
    if column in existing:
        return
    connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _utc_after_seconds(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=max(1, seconds))).isoformat().replace("+00:00", "Z")


def _positive_int(value: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load_json(value: str) -> dict[str, Any]:
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise GradingRepositoryError(
            "LOCAL_SQLITE_DATA_ERROR",
            "本地 SQLite 记录格式错误",
            [{"field": "rawJson", "reason": "expected object"}],
        )
    return payload


def _bool_to_int(value: Any) -> int:
    return 1 if bool(value) else 0
