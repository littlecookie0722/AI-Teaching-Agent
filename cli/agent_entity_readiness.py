"""Read-only readiness report for local platform entity mock imports."""

from __future__ import annotations

from typing import Any, Callable

from .artifact import ArtifactKind
from .agent_publish_activity import build_agent_entity_publish_activity_summary
from .store import JsonTaskStore


ENTITY_REQUIREMENTS = [
    {
        "agentEntity": "lab_template",
        "sourceArtifactKind": ArtifactKind.LAB_DSL.value,
        "previewComponent": "LabTemplateImportPreview",
        "mockImportComponent": "LabTemplateMockImport",
    },
    {
        "agentEntity": "exam_question",
        "sourceArtifactKind": ArtifactKind.EXAM_DSL.value,
        "previewComponent": "ExamQuestionImportPreview",
        "mockImportComponent": "ExamQuestionMockImport",
    },
    {
        "agentEntity": "grading_rule",
        "sourceArtifactKind": ArtifactKind.GRADING_DSL.value,
        "previewComponent": "GradingRuleImportPreview",
        "mockImportComponent": "GradingRuleMockImport",
    },
    {
        "agentEntity": "ppt_deck",
        "sourceArtifactKind": ArtifactKind.PPT_DSL.value,
        "previewComponent": "PptDeckImportPreview",
        "mockImportComponent": "PptDeckMockImport",
    },
]

# A generation task only owns the platform entities derived from its DSL output.
# Keep this mapping shared by readiness callers so an Exam task cannot be blocked
# by unrelated Lab or PPT import work.
AGENT_ENTITIES_BY_TASK_TYPE = {
    "LAB_GENERATION": {"lab_template"},
    "LAB_GENERATION_REVISION": {"lab_template"},
    "EXAM_GENERATION": {"exam_question", "grading_rule"},
    "EXAM_GENERATION_REVISION": {"exam_question"},
    "GRADING_GENERATION": {"grading_rule"},
    "GRADING_GENERATION_REVISION": {"grading_rule"},
    "PPT_GENERATION": {"ppt_deck"},
    "PPT_GENERATION_REVISION": {"ppt_deck"},
    "PPT_ARTIFACT_GENERATION": {"ppt_deck"},
}


def agent_entities_for_task_type(task_type: str | None) -> set[str] | None:
    """Return the local import entities applicable to a known task type."""

    normalized = str(task_type or "").strip().upper()
    entities = AGENT_ENTITIES_BY_TASK_TYPE.get(normalized)
    return set(entities) if entities is not None else None


def _artifact_matches(artifact: Any, *, mode: str, agent_entity: str, component: str) -> bool:
    metadata = artifact.metadata or {}
    return (
        artifact.kind.value == ArtifactKind.WORKFLOW_REPORT.value
        and artifact.mode == mode
        and metadata.get("agentEntity") == agent_entity
        and metadata.get("component") == component
    )


def _latest_artifact(artifacts: list[Any], *, mode: str, agent_entity: str, component: str) -> Any | None:
    matches = [
        artifact
        for artifact in artifacts
        if _artifact_matches(artifact, mode=mode, agent_entity=agent_entity, component=component)
    ]
    return matches[0] if matches else None


def _latest_final_publish_review_decision(artifacts: list[Any], agent_entity_id: str | None) -> Any | None:
    if not agent_entity_id:
        return None
    matches = [
        artifact
        for artifact in artifacts
        if artifact.kind.value == ArtifactKind.WORKFLOW_REPORT.value
        and artifact.mode == "LOCAL_FINAL_HUMAN_PUBLISH_REVIEW_DECISION"
        and (artifact.metadata or {}).get("agentEntityId") == agent_entity_id
    ]
    return matches[0] if matches else None


def _build_final_publish_review_decision_summary(artifact: Any | None) -> dict[str, Any]:
    metadata = artifact.metadata if artifact else {}
    return {
        "component": "FinalPublishReviewDecisionSummary",
        "mode": "LOCAL_FINAL_HUMAN_PUBLISH_REVIEW_DECISION_SUMMARY",
        "recorded": artifact is not None,
        "artifactId": artifact.id if artifact else None,
        "path": artifact.path if artifact else None,
        "decision": metadata.get("decision") if artifact else None,
        "approvedForPublishPlanning": bool(metadata.get("approvedForPublishPlanning")) if artifact else False,
        "needsRevision": bool(metadata.get("needsRevision")) if artifact else False,
        "safety": {
            "readOnly": True,
            "requestSent": False,
            "networkAccess": False,
            "secretsRead": False,
            "databaseWritten": False,
            "autoPublishAllowed": False,
            "realPublish": False,
            "publishExecuted": False,
            "requiresSeparatePublishAuthorization": True,
        },
    }


def _payload_from_record(record: Any) -> dict[str, Any]:
    if hasattr(record, "to_dict"):
        return record.to_dict()
    return dict(record or {})


def _build_grading_record_review_evidence(
    store: JsonTaskStore,
    *,
    task_id: str | None,
    agent_entity: str,
    records_override: list[Any] | None = None,
    repository_backed: bool = False,
) -> dict[str, Any]:
    if agent_entity != "grading_rule":
        return {
            "component": "GradingRecordReviewEvidence",
            "mode": "LOCAL_GRADING_RECORD_REVIEW_EVIDENCE",
            "applicable": False,
            "state": "NOT_GRADING_RULE",
            "readyForAgentReview": True,
            "blockingReasons": [],
            "nextRequiredAction": None,
            "safety": {
                "readOnly": True,
                "repositoryBacked": repository_backed,
                "databaseWritten": False,
                "sandboxExecuted": False,
                "contestantCodeExecuted": False,
                "autoPublishAllowed": False,
                "realPublish": False,
            },
        }
    if not task_id:
        return {
            "component": "GradingRecordReviewEvidence",
            "mode": "LOCAL_GRADING_RECORD_REVIEW_EVIDENCE",
            "applicable": True,
            "state": "NO_SOURCE_TASK",
            "readyForAgentReview": False,
            "recordTotal": 0,
            "latestRecordId": None,
            "latestStatus": None,
            "latestDecision": None,
            "blockingReasons": ["grading_rule_source_task_missing"],
            "nextRequiredAction": "link_grading_rule_to_source_task_before_platform_review",
            "safety": {
                "readOnly": True,
                "repositoryBacked": repository_backed,
                "databaseWritten": False,
                "sandboxExecuted": False,
                "contestantCodeExecuted": False,
                "autoPublishAllowed": False,
                "realPublish": False,
            },
        }

    if records_override is None:
        records = [_payload_from_record(record) for record in store.list_grading_records(task_id=task_id)]
        source = "JsonTaskStore.gradingRecords"
    else:
        records = [_payload_from_record(record) for record in records_override]
        records = [record for record in records if record.get("taskId") == task_id]
        records = sorted(records, key=lambda record: str(record.get("createdAt") or ""), reverse=True)
        source = "records_override"
    latest = records[0] if records else None
    latest_status = str(latest.get("status") or "") if latest else None
    latest_decision = latest.get("reviewDecision") if latest else None
    ready = latest_status == "HUMAN_APPROVED" and latest_decision == "approve-ready"
    if ready:
        state = "READY_FOR_PLATFORM_REVIEW"
        blocking_reasons: list[str] = []
        next_required_action = "continue_platform_review_after_grading_record_approved"
    elif latest is None:
        state = "NO_GRADING_RECORD"
        blocking_reasons = ["grading_record_missing"]
        next_required_action = "create_grading_record_from_latest_evidence_report"
    elif latest_status == "NEEDS_EVIDENCE" or latest_decision == "needs-evidence":
        state = "NEEDS_MORE_EVIDENCE"
        blocking_reasons = ["latest_grading_record_needs_more_evidence"]
        next_required_action = "collect_more_evidence_for_grading_record_review"
    elif latest_status == "NEEDS_REVISION" or latest_decision == "needs-revision":
        state = "NEEDS_REVISION"
        blocking_reasons = ["latest_grading_record_needs_revision"]
        next_required_action = "revise_grading_or_submission_before_platform_review"
    else:
        state = "WAITING_GRADING_RECORD_REVIEW"
        blocking_reasons = ["latest_grading_record_waiting_human_review"]
        next_required_action = "review_latest_grading_record_for_platform_review"
    return {
        "component": "GradingRecordReviewEvidence",
        "mode": "LOCAL_GRADING_RECORD_REVIEW_EVIDENCE",
        "source": source,
        "applicable": True,
        "taskId": task_id,
        "state": state,
        "readyForAgentReview": ready,
        "recordTotal": len(records),
        "latestRecordId": latest.get("id") if latest else None,
        "latestSubmissionId": latest.get("submissionId") if latest else None,
        "latestCandidateId": latest.get("candidateId") if latest else None,
        "latestReportPath": latest.get("reportPath") if latest else None,
        "latestStatus": latest_status,
        "latestDecision": latest_decision,
        "latestReason": latest.get("reviewReason") if latest else None,
        "latestReviewedBy": latest.get("reviewedBy") if latest else None,
        "latestReviewedAt": latest.get("reviewedAt") if latest else None,
        "latestEarnedScore": latest.get("earnedScore") if latest else None,
        "latestTotalScore": latest.get("totalScore") if latest else None,
        "latestCoverageRatio": latest.get("coverageRatio") if latest else None,
        "blockingReasons": blocking_reasons,
        "nextRequiredAction": next_required_action,
        "reviewCommand": (
            f"python lab_cli.py grade record-review --id {latest.get('id')} "
            "--reviewer <reviewer> --decision approve-ready"
        )
        if latest and not ready
        else None,
        "safety": {
            "readOnly": True,
            "repositoryBacked": repository_backed,
            "databaseWritten": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
            "autoPublishAllowed": False,
            "realPublish": False,
        },
    }


def _build_signoff_checklist(
    *,
    ready_for_manual_platform_review: bool,
    import_activity_summary: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    checks = [
        {
            "id": "confirm_local_preview_and_mock_import_ready",
            "label": "确认本地导入预览与 mock-import 草稿已生成",
            "matched": ready_for_manual_platform_review,
        },
        {
            "id": "confirm_platform_send_recorded",
            "label": "确认平台 draft import 请求已有审计记录",
            "matched": bool(import_activity_summary.get("requestSent")),
        },
        {
            "id": "confirm_platform_status_queried",
            "label": "确认平台侧导入状态已查询",
            "matched": bool(import_activity_summary.get("statusQueried")),
        },
        {
            "id": "confirm_platform_result_recorded",
            "label": "确认平台导入结果已人工登记",
            "matched": bool(import_activity_summary.get("resultRecorded")),
        },
        {
            "id": "confirm_accepted_for_draft_only",
            "label": "确认平台侧仅接受为草稿且未自动发布",
            "matched": bool(import_activity_summary.get("acceptedForDraft"))
            and not bool(import_activity_summary.get("realPublish")),
        },
    ]
    signoff_state = (
        "READY_FOR_PLATFORM_ENTITY_SIGNOFF"
        if all(check["matched"] for check in checks)
        else "WAITING_PLATFORM_ENTITY_IMPORT_ACTIVITY"
    )
    return signoff_state, checks


def _build_post_signoff_pre_publish_checklist(
    *,
    agent_entity: str,
    signoff_recorded: bool,
    ready_for_manual_platform_review: bool,
    import_activity_summary: dict[str, Any],
) -> dict[str, Any]:
    """Build a read-only checklist for humans before any real publish planning."""

    checks = [
        {
            "id": "confirm_agent_entity_signoff_recorded",
            "label": "确认本地平台实体人工签收记录已存在",
            "matched": signoff_recorded,
        },
        {
            "id": "confirm_local_preview_and_mock_import_preserved",
            "label": "确认本地导入预览与 mock-import 草稿仍可追溯",
            "matched": ready_for_manual_platform_review,
        },
        {
            "id": "confirm_platform_result_accepted_for_draft",
            "label": "确认平台侧结果仅为草稿接受",
            "matched": bool(import_activity_summary.get("acceptedForDraft")),
        },
        {
            "id": "confirm_no_auto_publish_or_real_publish",
            "label": "确认没有自动发布或真实发布",
            "matched": not bool(import_activity_summary.get("autoPublishAllowed"))
            and not bool(import_activity_summary.get("realPublish")),
        },
        {
            "id": "confirm_local_system_did_not_write_real_database",
            "label": "确认本地系统没有写入真实平台数据库",
            "matched": not bool(import_activity_summary.get("databaseWrittenByLocalSystem")),
        },
        {
            "id": "confirm_final_human_publish_review_required",
            "label": "确认后续真实发布前仍需人工最终复核",
            "matched": signoff_recorded,
        },
    ]
    matched_total = sum(1 for check in checks if check["matched"])
    entity_specific_review_focus = _build_entity_specific_review_focus(
        agent_entity=agent_entity,
        signoff_recorded=signoff_recorded,
        import_activity_summary=import_activity_summary,
    )
    return {
        "component": "AgentEntityPostSignoffPrePublishChecklist",
        "mode": "LOCAL_POST_SIGNOFF_PRE_PUBLISH_REVIEW",
        "agentEntity": agent_entity,
        "visible": signoff_recorded,
        "status": "READY_FOR_FINAL_HUMAN_PUBLISH_REVIEW" if matched_total == len(checks) else "NEEDS_MANUAL_REVIEW",
        "total": len(checks),
        "matchedTotal": matched_total,
        "blockedTotal": len(checks) - matched_total,
        "checks": checks,
        "entitySpecificReviewFocus": entity_specific_review_focus,
        "nextRequiredAction": "final_human_publish_review_before_any_real_publish",
        "safety": {
            "readOnly": True,
            "databaseWritten": False,
            "realAgentImport": False,
            "autoPublishAllowed": False,
            "realPublish": False,
            "requiresFinalHumanReview": True,
        },
    }


def _build_entity_specific_review_focus(
    *,
    agent_entity: str,
    signoff_recorded: bool,
    import_activity_summary: dict[str, Any],
) -> dict[str, Any]:
    """Return entity-specific human review focus before any real publish."""

    focus_by_entity = {
        "lab_template": {
            "primaryReviewFocus": "review_lab_objectives_environment_and_grading_ref_before_publish",
            "checks": [
                {
                    "id": "verify_lab_objectives_and_steps_publishable",
                    "label": "复核实验目标、步骤和预期结果适合发布",
                },
                {
                    "id": "verify_lab_environment_and_materials_resolved",
                    "label": "复核实验环境、素材路径和依赖说明可被平台承载",
                },
                {
                    "id": "confirm_lab_grading_ref_and_duration_reasonable",
                    "label": "复核实验评分引用、时长和难度设置合理",
                },
            ],
        },
        "exam_question": {
            "primaryReviewFocus": "review_candidate_safe_exam_preview_and_scoring_before_publish",
            "checks": [
                {
                    "id": "confirm_candidate_preview_hides_answers",
                    "label": "复核选手预览不展示标准答案、gradingRef 或教师专用信息",
                },
                {
                    "id": "verify_question_score_and_grading_ref_coverage",
                    "label": "复核题目分值、gradingRef 覆盖和总分一致",
                },
                {
                    "id": "confirm_exam_source_lab_traceable",
                    "label": "复核试题来源实验和导入草稿可追溯",
                },
            ],
        },
        "grading_rule": {
            "primaryReviewFocus": "review_grading_plan_sandbox_limits_and_evidence_before_publish",
            "checks": [
                {
                    "id": "verify_assessment_plan_aligned_with_checks",
                    "label": "复核评分计划与 checks、分值和解释性信号一致",
                },
                {
                    "id": "confirm_sandbox_limits_and_evidence_requirements",
                    "label": "复核沙箱限制、证据要求和真实执行前置条件",
                },
                {
                    "id": "confirm_no_contestant_code_execution_before_publish",
                    "label": "确认发布前没有绕过沙箱执行选手代码",
                },
            ],
        },
        "ppt_deck": {
            "primaryReviewFocus": "review_ppt_deck_content_artifact_and_classroom_readiness_before_publish",
            "checks": [
                {
                    "id": "verify_ppt_slide_plan_and_titles_publishable",
                    "label": "复核 PPT slide plan、标题和课堂讲授顺序适合发布",
                },
                {
                    "id": "confirm_pptx_artifact_generated_and_reviewed",
                    "label": "确认 PPTX Artifact 已生成并完成页级人工审核",
                },
                {
                    "id": "confirm_ppt_deck_not_auto_published",
                    "label": "确认课件草稿未自动发布且仍需最终人工复核",
                },
            ],
        },
    }
    focus = focus_by_entity.get(
        agent_entity,
        {
            "primaryReviewFocus": "review_agent_entity_before_publish",
            "checks": [
                {
                    "id": "review_agent_entity_payload_before_publish",
                    "label": "复核平台实体草稿内容后再进入发布评审",
                }
            ],
        },
    )
    real_publish = bool(import_activity_summary.get("realPublish"))
    checks = [
        {
            **check,
            "matched": signoff_recorded and not real_publish,
            "status": "READY_FOR_FINAL_HUMAN_REVIEW" if signoff_recorded and not real_publish else "WAITING_SIGNOFF",
        }
        for check in focus["checks"]
    ]
    matched_total = sum(1 for check in checks if check["matched"])
    return {
        "component": "AgentEntitySpecificPrePublishReviewFocus",
        "mode": "LOCAL_ENTITY_SPECIFIC_PRE_PUBLISH_REVIEW",
        "agentEntity": agent_entity,
        "primaryReviewFocus": focus["primaryReviewFocus"],
        "status": "READY_FOR_FINAL_HUMAN_REVIEW" if matched_total == len(checks) else "WAITING_SIGNOFF",
        "total": len(checks),
        "matchedTotal": matched_total,
        "checks": checks,
        "safety": {
            "readOnly": True,
            "answerVisibleToCandidate": False,
            "contestantCodeExecuted": False,
            "autoPublishAllowed": False,
            "realPublish": False,
            "requiresFinalHumanReview": True,
        },
    }


def build_agent_entity_readiness_report(
    store: JsonTaskStore,
    *,
    source_task_id: str | None = None,
    agent_entities: set[str] | None = None,
    artifacts_override: list[Any] | None = None,
    entities_override: list[Any] | None = None,
    grading_records_override: list[Any] | None = None,
    import_activity_builder: Callable[[str], dict[str, Any]] | None = None,
    source_mode: str = "LOCAL_AGENT_ENTITY_READINESS_REPORT",
    repository_backed: bool = False,
) -> dict[str, Any]:
    """Build a deterministic read-only report for mock platform entity imports."""

    artifacts = artifacts_override if artifacts_override is not None else store.list_artifacts(task_id=source_task_id)
    entities = (
        entities_override
        if entities_override is not None
        else store.list_agent_entities(source_task_id=source_task_id)
    )
    activity_builder = import_activity_builder or (
        lambda entity_id: build_agent_entity_publish_activity_summary(store, entity_id)
    )
    items: list[dict[str, Any]] = []
    # When a source task filter is applied, surface every entity type so the
    # report can highlight which entities are still missing for that task.
    # Otherwise callers that pass task-type-scoped agent_entities would hide
    # gaps for entities the task does not own (e.g. a Lab task would only show
    # lab_template and never reveal missing exam/grading/ppt imports).
    effective_agent_entities = agent_entities if source_task_id is None else None
    requirements = [
        requirement
        for requirement in ENTITY_REQUIREMENTS
        if effective_agent_entities is None or requirement["agentEntity"] in effective_agent_entities
    ]

    for requirement in requirements:
        agent_entity = requirement["agentEntity"]
        preview_artifact = _latest_artifact(
            artifacts,
            mode="LOCAL_PLATFORM_IMPORT_PREVIEW",
            agent_entity=agent_entity,
            component=requirement["previewComponent"],
        )
        mock_import_artifact = _latest_artifact(
            artifacts,
            mode="LOCAL_PLATFORM_ENTITY_MOCK_IMPORT",
            agent_entity=agent_entity,
            component=requirement["mockImportComponent"],
        )
        entity_records = [entity for entity in entities if entity.entityType.value == agent_entity]
        latest_entity = entity_records[0] if entity_records else None
        import_activity = activity_builder(latest_entity.id) if latest_entity else None
        import_activity_summary = import_activity.get("summary", {}) if import_activity else {}
        preview_created = preview_artifact is not None
        mock_import_created = mock_import_artifact is not None and latest_entity is not None
        ready_for_manual_platform_review = preview_created and mock_import_created
        item_source_task_id = (
            latest_entity.sourceTaskId
            if latest_entity
            else preview_artifact.taskId
            if preview_artifact
            else source_task_id
        )
        blockers: list[str] = []
        if not preview_created:
            blockers.append("IMPORT_PREVIEW_MISSING")
        if not latest_entity:
            blockers.append("MOCK_IMPORT_ENTITY_MISSING")
        grading_record_review_evidence = _build_grading_record_review_evidence(
            store,
            task_id=item_source_task_id,
            agent_entity=agent_entity,
            records_override=grading_records_override,
            repository_backed=repository_backed,
        )
        signoff_state, manual_signoff_checklist = _build_signoff_checklist(
            ready_for_manual_platform_review=ready_for_manual_platform_review,
            import_activity_summary=import_activity_summary,
        )
        signoff_recorded = bool(import_activity_summary.get("signoffRecorded"))
        if signoff_recorded:
            signoff_state = "PLATFORM_ENTITY_SIGNOFF_RECORDED"
        ready_for_agent_entity_signoff = (
            signoff_state == "READY_FOR_PLATFORM_ENTITY_SIGNOFF" and not signoff_recorded
        )
        post_signoff_pre_publish_checklist = _build_post_signoff_pre_publish_checklist(
            agent_entity=agent_entity,
            signoff_recorded=signoff_recorded,
            ready_for_manual_platform_review=ready_for_manual_platform_review,
            import_activity_summary=import_activity_summary,
        )
        final_review_decision_artifact = _latest_final_publish_review_decision(
            artifacts,
            latest_entity.id if latest_entity else None,
        )
        final_publish_review_decision = _build_final_publish_review_decision_summary(final_review_decision_artifact)

        items.append(
            {
                "component": "AgentEntityReadinessItem",
                "agentEntity": agent_entity,
                "sourceArtifactKind": requirement["sourceArtifactKind"],
                "previewComponent": requirement["previewComponent"],
                "mockImportComponent": requirement["mockImportComponent"],
                "previewCreated": preview_created,
                "previewArtifactId": preview_artifact.id if preview_artifact else None,
                "previewPath": preview_artifact.path if preview_artifact else None,
                "mockImportCreated": mock_import_created,
                "mockImportArtifactId": mock_import_artifact.id if mock_import_artifact else None,
                "agentEntityId": latest_entity.id if latest_entity else None,
                "agentEntityStatus": latest_entity.status.value if latest_entity else None,
                "importActivity": import_activity,
                "dryRunPrepared": bool(import_activity_summary.get("dryRunPrepared")),
                "requestSent": bool(import_activity_summary.get("requestSent")),
                "statusQueried": bool(import_activity_summary.get("statusQueried")),
                "resultRecorded": bool(import_activity_summary.get("resultRecorded")),
                "signoffRecorded": signoff_recorded,
                "latestSignoffArtifactId": import_activity_summary.get("latestSignoffArtifactId"),
                "latestPlatformStatus": import_activity_summary.get("latestPlatformStatus"),
                "latestQueriedPlatformStatus": import_activity_summary.get("latestQueriedPlatformStatus"),
                "latestSuggestedImportResultStatus": import_activity_summary.get(
                    "latestSuggestedImportResultStatus"
                ),
                "agentSideReviewed": bool(import_activity_summary.get("agentSideReviewed")),
                "acceptedForDraft": bool(import_activity_summary.get("acceptedForDraft")),
                "rejectedByPlatform": bool(import_activity_summary.get("rejectedByPlatform")),
                "gradingRecordReviewEvidence": grading_record_review_evidence,
                "signoffState": signoff_state,
                "readyForAgentEntitySignoff": ready_for_agent_entity_signoff,
                "manualSignoffChecklist": manual_signoff_checklist,
                "postSignoffPrePublishChecklist": post_signoff_pre_publish_checklist,
                "latestFinalPublishReviewDecisionArtifactId": (
                    final_review_decision_artifact.id if final_review_decision_artifact else None
                ),
                "finalPublishReviewDecision": final_publish_review_decision,
                "sourceTaskId": item_source_task_id,
                "repositoryBacked": repository_backed,
                "readyForManualAgentReview": ready_for_manual_platform_review,
                "blockers": blockers,
                "safety": {
                    "readOnly": True,
                    "jsonStoreSourceRead": not repository_backed,
                    "repositoryBacked": repository_backed,
                    "mockStoreWritten": bool(latest_entity) and not repository_backed,
                    "databaseWritten": False,
                    "realAgentImport": False,
                    "autoPublishAllowed": False,
                    "realPublish": False,
                },
            }
        )

    ready_total = sum(1 for item in items if item["readyForManualAgentReview"])
    preview_total = sum(1 for item in items if item["previewCreated"])
    mock_import_total = sum(1 for item in items if item["mockImportCreated"])
    dry_run_total = sum(1 for item in items if item["dryRunPrepared"])
    request_sent_total = sum(1 for item in items if item["requestSent"])
    status_queried_total = sum(1 for item in items if item["statusQueried"])
    result_recorded_total = sum(1 for item in items if item["resultRecorded"])
    signoff_ready_total = sum(1 for item in items if item["readyForAgentEntitySignoff"])
    signoff_recorded_total = sum(1 for item in items if item["signoffRecorded"])
    post_signoff_pre_publish_ready_total = sum(
        1
        for item in items
        if item["postSignoffPrePublishChecklist"]["status"] == "READY_FOR_FINAL_HUMAN_PUBLISH_REVIEW"
    )
    final_publish_review_decision_recorded_total = sum(
        1 for item in items if item["finalPublishReviewDecision"]["recorded"]
    )
    grading_record_review_applicable_total = sum(
        1 for item in items if item["gradingRecordReviewEvidence"]["applicable"]
    )
    grading_record_review_ready_total = sum(
        1
        for item in items
        if item["gradingRecordReviewEvidence"]["applicable"]
        and item["gradingRecordReviewEvidence"]["readyForAgentReview"]
    )
    grading_record_review_blocked_total = sum(
        1
        for item in items
        if item["gradingRecordReviewEvidence"]["applicable"]
        and not item["gradingRecordReviewEvidence"]["readyForAgentReview"]
    )
    approved_for_publish_planning_total = sum(
        1 for item in items if item["finalPublishReviewDecision"]["approvedForPublishPlanning"]
    )
    needs_revision_total = sum(1 for item in items if item["finalPublishReviewDecision"]["needsRevision"])
    return {
        "component": "AgentEntityReadinessReport",
        "mode": source_mode,
        "sourceTaskId": source_task_id,
        "repositoryBacked": repository_backed,
        "scope": {
            "agentEntities": [requirement["agentEntity"] for requirement in requirements],
            "filtered": effective_agent_entities is not None,
        },
        "items": items,
        "summary": {
            "requiredTotal": len(items),
            "previewCreatedTotal": preview_total,
            "mockImportCreatedTotal": mock_import_total,
            "readyForManualAgentReviewTotal": ready_total,
            "missingPreviewTotal": len(items) - preview_total,
            "missingMockImportTotal": len(items) - mock_import_total,
            "dryRunPreparedTotal": dry_run_total,
            "requestSentTotal": request_sent_total,
            "statusQueriedTotal": status_queried_total,
            "resultRecordedTotal": result_recorded_total,
            "agentEntitySignoffReadyTotal": signoff_ready_total,
            "agentEntitySignoffRecordedTotal": signoff_recorded_total,
            "postSignoffPrePublishReadyTotal": post_signoff_pre_publish_ready_total,
            "finalPublishReviewDecisionRecordedTotal": final_publish_review_decision_recorded_total,
            "gradingRecordReviewApplicableTotal": grading_record_review_applicable_total,
            "gradingRecordReviewReadyTotal": grading_record_review_ready_total,
            "gradingRecordReviewBlockedTotal": grading_record_review_blocked_total,
            "approvedForPublishPlanningTotal": approved_for_publish_planning_total,
            "needsRevisionTotal": needs_revision_total,
            "allPlatformEntitiesReadyForSignoff": signoff_ready_total == len(items),
            "allPlatformEntitiesSignoffRecorded": signoff_recorded_total == len(items),
            "allPostSignoffPrePublishReady": post_signoff_pre_publish_ready_total == len(items),
            "allFinalPublishReviewDecisionsRecorded": final_publish_review_decision_recorded_total == len(items),
            "allReadyForManualPlatformReview": ready_total == len(items),
        },
        "safety": {
            "readOnly": True,
            "jsonStoreSourceRead": not repository_backed,
            "repositoryBacked": repository_backed,
            "newLlmRequestSent": False,
            "secretsRead": False,
            "networkAccess": False,
            "databaseWritten": False,
            "realAgentImport": False,
            "autoPublishAllowed": False,
            "realPublish": False,
            "sandboxExecuted": False,
            "contestantCodeExecuted": False,
        },
    }
