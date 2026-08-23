import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_GRADING_CHECK_TYPES = ["file_exists", "stdout_contains", "pytest", "notebook_cell", "json_field", "log_keyword"]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def read_text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_one_click_generation_workspace_has_single_workflow_request_and_review_routes():
    html = read_text("frontend/generation-workspace.html")
    script = read_text("frontend/generation-workspace-data.js")
    manifest = load_json("frontend/ui.manifest.json")
    pages = {page["route"]: page for page in manifest["pages"]}
    prototypes = {prototype["route"]: prototype for prototype in manifest["staticPrototypes"]}

    assert 'id="generation-workspace-form"' in html
    assert 'id="generation-source"' in html
    assert 'id="generation-reviewer"' in html
    assert 'id="generation-provider-mode"' in html
    assert 'id="generation-real-confirmation"' in html
    assert 'id="generation-run"' in html
    assert 'id="generation-api-state"' in html
    assert 'id="generation-progress-bar"' in html
    assert '<script src="generation-workspace-data.js"></script>' in html
    assert "Lab + Exam/Grading" in html
    for kind in ("lab", "exam", "grading"):
        assert f'id="generation-{kind}-status"' in html
        assert f'id="generation-{kind}-task"' in html
        assert f'id="generation-{kind}-path"' in html
        assert f'id="generation-{kind}-review"' in html

    assert 'generatePath: "/api/phase2/workflows/content-generation/run"' in script
    assert script.count('method: "POST"') == 1
    assert "createdTasks" in script
    assert "generatedDsl" in script
    assert "workflowRun" in script
    assert 'setAllTaskStates("GENERATING"' in script
    assert 'setAllTaskStates("ERROR"' in script
    assert 'artifactProfile: "teaching-core"' in script
    assert 'completed === 3 && waitingReview === 3' in script
    assert "VALIDATION_ERROR" in script
    assert "REAL_LLM_CONFIRMATION_REQUIRED" in script
    assert "lab-review.html" in script
    assert "exam-review.html" in script
    assert "grading-review.html" in script
    assert "ppt-review.html" not in script
    assert "review-center.html" in script
    assert "autoPublishAllowed: false" in script
    assert "answerVisibleToCandidate: false" in script
    assert "frontendDirectRealLlmCall: false" in script
    assert "apiKey" not in script
    assert "OPENAI_API_KEY" not in html
    assert "/import-send" not in html
    assert "/publish" not in script

    page = pages["/generation-workspace"]
    prototype = prototypes["/generation-workspace"]
    assert page["prototypePath"] == "frontend/generation-workspace.html"
    assert page["apiDependencies"] == [
        {"method": "POST", "path": "/api/phase2/workflows/content-generation/run"}
    ]
    assert "request.artifactProfile=teaching-core" in page["dataSources"]
    assert "POST /api/phase2/workflows/content-generation/run.teachingPackageSummary" in page["dataSources"]
    assert "POST /api/phase2/workflows/content-generation/run.candidateSafeExamPreview" in page["dataSources"]
    assert all("ppt-review.html" not in source for source in page["dataSources"])
    assert "OneClickGenerationWorkspace" in page["components"]
    assert page["safety"]["generatedStatus"] == "WAITING_REVIEW"
    assert page["safety"]["frontendDirectRealLlmCall"] is False
    assert page["safety"]["answerVisibleToCandidate"] is False
    assert page["safety"]["autoPublishAllowed"] is False
    assert prototype["path"] == "frontend/generation-workspace.html"
    assert "request.artifactProfile=teaching-core" in prototype["dataSources"]
    assert prototype["safety"] == page["safety"]
    assert "generation-workspace.html" in read_text("frontend/review-center.html")
    assert "generation-workspace.html" in read_text("frontend/README.md")
    assert "generation-workspace.html" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")
    assert ".section-head > .pill" in html.split("@media (max-width: 620px)", 1)[1]


def test_review_center_aggregates_teaching_package_and_uses_per_task_review_actions():
    generation_script = read_text("frontend/generation-workspace-data.js")
    html = read_text("frontend/review-center.html")
    loader_js = read_text("frontend/review-center-data.js")
    action_js = read_text("frontend/review-action-data.js")
    manifest = load_json("frontend/ui.manifest.json")
    pages = {page["route"]: page for page in manifest["pages"]}
    prototypes = {prototype["route"]: prototype for prototype in manifest["staticPrototypes"]}

    assert "workflowRunId: workflow.id" in generation_script
    assert 'id="teaching-package-review"' in html
    assert 'id="teaching-package-progress"' in html
    assert 'id="teaching-package-schema"' in html
    assert 'id="teaching-package-candidate-safety"' in html
    assert 'id="teaching-package-export-ready"' in html
    assert 'id="teaching-package-reviewer"' in html
    assert 'id="teaching-package-artifacts"' in html
    assert '<script src="review-action-data.js"></script>' in html

    assert "getQueryWorkflowRunId" in loader_js
    assert "withWorkflowRunId" in loader_js
    assert "teachingPackageReview" in loader_js
    assert "renderTeachingPackageReview" in loader_js
    assert "renderTeachingPackageArtifact" in loader_js
    assert 'data-package-review-action' in loader_js
    assert 'data-package-reject-reason' in loader_js
    assert "loadTaskDetail(taskId)" in loader_js
    assert "POST /api/ai-tasks/{id}/approve" not in loader_js
    assert "POST /api/ai-tasks/{id}/reject" not in loader_js

    assert "postPackageReviewAction" in action_js
    assert "data-package-review-action" in action_js
    assert "data-package-reject-reason" in action_js
    assert "teaching-package-reviewer" in action_js
    assert "rejectRequiresReason=true" in action_js
    assert "window.reviewCenterDataLoader.load()" in action_js
    assert "/api/ai-tasks/{id}/{action}" in action_js
    assert "/publish" not in action_js

    page = pages["/review-center"]
    prototype = prototypes["/review-center"]
    assert "TeachingPackageReviewWorkspace" in page["components"]
    assert "TeachingPackageArtifactReviewRow" in page["components"]
    assert "query: workflowRunId" in page["dataSources"]
    assert (
        "GET /api/review-task-summary?workflowRunId={workflowRunId}.reviewTaskSummary.teachingPackageReview"
        in page["dataSources"]
    )
    assert "frontend/review-action-data.js" in page["dataSources"]
    assert "POST /api/ai-tasks/{id}/approve" in page["dataSources"]
    assert "POST /api/ai-tasks/{id}/reject" in page["dataSources"]
    assert {dependency["path"] for dependency in page["apiDependencies"]} >= {
        "/api/review-task-summary",
        "/api/ai-tasks/{id}/approve",
        "/api/ai-tasks/{id}/reject",
    }
    assert page["safety"]["reviewActionsArePerTask"] is True
    assert page["safety"]["rejectRequiresReason"] is True
    assert page["safety"]["batchStateChangeAllowed"] is False
    assert "query: workflowRunId" in prototype["dataSources"]
    assert "POST /api/ai-tasks/{id}/approve" in prototype["dataSources"]
    assert "POST /api/ai-tasks/{id}/reject" in prototype["dataSources"]
    assert ".runtime-strip," in html.split("@media (max-width: 920px)", 1)[1]


def test_frontend_manifest_is_phase1_mock_contract():
    manifest = load_json("frontend/ui.manifest.json")

    assert manifest["phase"] == "Phase 1"
    assert manifest["mode"] == "MOCK_ONLY"
    assert manifest["globalRules"]["realBackendRequired"] is False
    assert manifest["globalRules"]["realLlmCalled"] is False
    assert manifest["globalRules"]["autoPublishAllowed"] is False
    assert manifest["globalRules"]["secretVisibleInFrontend"] is False
    prototypes = {prototype["route"]: prototype for prototype in manifest["staticPrototypes"]}
    assert prototypes["/review-center"]["mode"] == "LOCAL_CORE_MVP"
    assert prototypes["/review-center"]["title"] == "Review Center Local Core"
    assert "frontend/mock-data.json.highRiskMcpIntentPrototype" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.secondConfirmationStatusPrototype" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.pptReviewPrototype.pageReviewUpdateAction" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.reviewCenterPrototype.qualitySignalQueueSummary" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.reviewCenterPrototype.reviewPriorityQueue" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.reviewCenterPrototype.realDemoReviewQueue" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.reviewCenterPrototype.realDemoReviewQueue.items[].entryHref" in prototypes["/review-center"]["dataSources"]
    assert "review-center.html -> lab-review.html?taskId={id}" in prototypes["/review-center"]["dataSources"]
    assert "review-center.html -> exam-review.html?taskId={id}" in prototypes["/review-center"]["dataSources"]
    assert "review-center.html -> ppt-review.html?taskId={id}" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.reviewDetail.reviewPage.providerSummary" in prototypes["/review-center"]["dataSources"]
    assert (
        "frontend/mock-data.json.reviewDetail.reviewPage.providerSummary.qualitySummary"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewDetail.reviewPage.providerSummary.calls[].qualitySummary"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "frontend/mock-data.json.reviewDetail.contentQualitySummary" in prototypes["/review-center"]["dataSources"]
    assert "GET /api/review-tasks/{id}.reviewDetail.contentQualitySummary" in prototypes["/review-center"]["dataSources"]
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.contentQualitySummary"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "frontend/review-center-data.js" in prototypes["/review-center"]["dataSources"]
    assert "GET /api/review-tasks/{id}.reviewDetail.controlledGradingEvidence" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.reviewDetail.controlledGradingEvidence" in prototypes["/review-center"]["dataSources"]
    assert "GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence" in prototypes["/review-center"]["dataSources"]
    assert (
        "GET /api/review-task-summary.reviewTaskSummary.mergedGradingEvidenceReviewSignal"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "GET /api/review-task-summary.reviewTaskSummary.gradingEvidenceReadinessSignal"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "GET /api/review-task-summary.reviewTaskSummary.reviewPriorityQueue.items[].gradingEvidenceReadinessSummary"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "GET /api/review-task-summary.reviewTaskSummary.reviewPriorityQueue.items[].gradingEvidenceReadinessSummary.actionGuide"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.controlledDockerEvidenceReviewSignal"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.mergedGradingEvidenceReviewSignal"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.notebookEvidenceReviewPlan"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "frontend/mock-data.json.realDemoPrototype.coreBusinessDemoPath" in prototypes["/review-center"]["dataSources"]
    assert (
        "frontend/mock-data.json.realDemoPrototype.readonlyEvidenceDemo.reportDetail"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.realDemoPrototype.controlledDockerEvidenceDemo"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "frontend/mock-data.json.realDemoPrototype.realDslReviewPreview" in prototypes["/review-center"]["dataSources"]
    assert "examples/output/real-llm-demo-real-dsl-review-preview.json" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.realDemoPrototype.realDslRevisionDiffPreview" in prototypes["/review-center"]["dataSources"]
    assert "examples/output/real-llm-demo-revision-diff-preview.json" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.realDemoPrototype.realDslRevisionDecision" in prototypes["/review-center"]["dataSources"]
    assert "examples/output/real-llm-demo-revision-decision-report.json" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.realDemoPrototype.realDslRevisionPromotion" in prototypes["/review-center"]["dataSources"]
    assert "examples/output/real-llm-demo-revision-promotion-report.json" in prototypes["/review-center"]["dataSources"]
    assert (
        "frontend/mock-data.json.realDemoPrototype.realDslRevisionPromotionReviewQueueItem"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.realDemoPrototype.realDslRevisionPromotionReviewDisposition"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.realDemoPrototype.labTemplateImportPreview"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.labTemplateImportPreviewSignal"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.examQuestionImportPreviewSignal"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.gradingRuleImportPreviewSignal"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.platformImportPreviewSummary"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.platformImportPreviewActions"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.platformImportPreviewSignoffChecklist"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.agentEntityMockImportSummary"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.agentEntityReadinessReport"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "GET /api/review-tasks/{id}.reviewDetail.platformImportPreviewActions" in prototypes["/review-center"]["dataSources"]
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.platformImportPreviewActions"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "GET /api/review-tasks/{id}.reviewDetail.platformImportPreview" in prototypes["/review-center"]["dataSources"]
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.platformImportPreview"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "GET /api/review-tasks/{id}.reviewDetail.platformImportPreviewSignoff" in prototypes["/review-center"]["dataSources"]
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.platformImportPreviewSignoff"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "GET /api/review-tasks/{id}.reviewDetail.agentEntityMockImport" in prototypes["/review-center"]["dataSources"]
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.agentEntityMockImport"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "GET /api/review-tasks/{id}.reviewDetail.agentEntityReadinessReport" in prototypes["/review-center"]["dataSources"]
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.agentEntityReadinessReport"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "GET /api/platform-entities/readiness-report?sourceTaskId={id}" in prototypes["/review-center"]["dataSources"]
    assert "query: agentEntityRefresh=1" in prototypes["/review-center"]["dataSources"]
    assert "GET /api/review-tasks/{id}/core-readiness" in prototypes["/review-center"]["dataSources"]
    assert (
        "GET /api/review-tasks/{id}/core-readiness.coreWorkflowReadinessReport"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "GET /api/workflow/report?file={agentReport}.agentCoreNextToolExecution"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "GET /api/workflow/report?file={agentReport}.postExecutionCoreNextToolPlan"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "GET /api/workflow/report?file={agentReport}.nextSingleStepActionGuide"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "query: agentReport" in prototypes["/review-center"]["dataSources"]
    assert (
        "GET /api/review-task-summary?detailMode=light&agentReport={workflowReport}.reviewTaskSummary.realDemoReviewQueue"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "GET /api/review-tasks/{id}?agentReport={workflowReport}.reviewDetail.reviewPage.dslPreview"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "GET /api/review-tasks/{id}?agentReport={workflowReport}.reviewDetail.reviewPage.artifactGroups"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "POST /api/labs/import-preview" in prototypes["/review-center"]["dataSources"]
    assert "POST /api/exams/import-preview" in prototypes["/review-center"]["dataSources"]
    assert "POST /api/grading/import-preview" in prototypes["/review-center"]["dataSources"]
    assert (
        "mcp-server/tools.manifest.json.create_lab_template_import_preview"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "mcp-server/tools.manifest.json.create_exam_question_import_preview"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "mcp-server/tools.manifest.json.create_grading_rule_import_preview"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.realDslRevisionPromotionReviewQueueSignal"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "POST /api/review/real-dsl-revision-enqueue" in prototypes["/review-center"]["dataSources"]
    assert "GET /api/review-tasks/{id}" in prototypes["/review-center"]["dataSources"]
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.assessmentPlanManualReviewQueueSignal"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "frontend/mock-data.json.examReviewPrototype.qualitySignals" in prototypes["/review-center"]["dataSources"]
    assert (
        "frontend/mock-data.json.examReviewPrototype.dslPreview.candidateSafeExamPreview"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "frontend/mock-data.json.gradingReviewPrototype.qualitySignals" in prototypes["/review-center"]["dataSources"]
    assert "frontend/mock-data.json.gradingReviewPrototype.assessmentPlanSummary" in prototypes["/review-center"]["dataSources"]
    assert "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary" in prototypes["/review-center"]["dataSources"]
    assert prototypes["/review-center"]["safety"]["batchStateChangeAllowed"] is False
    assert prototypes["/review-center"]["safety"]["secondConfirmationStatusReadOnly"] is True
    assert prototypes["/review-center"]["safety"]["confirmationEndpointEnabled"] is False
    assert prototypes["/review-center"]["safety"]["highRiskIntentExecutionAllowed"] is False
    assert prototypes["/review-center"]["safety"]["environmentDestroyed"] is False
    assert prototypes["/labs/generate"]["mode"] == "MOCK_ONLY"
    assert prototypes["/labs/generate"]["safety"]["generatedStatus"] == "WAITING_REVIEW"
    assert prototypes["/labs/generate"]["safety"]["apiMockGenerationEnabled"] is True
    assert prototypes["/labs/generate"]["safety"]["localCoreGenerationWorkspace"] is True
    assert prototypes["/labs/generate"]["safety"]["frontendDirectRealLlmCall"] is False
    assert prototypes["/labs/generate"]["safety"]["realLlmResultCanEnterViaCliOrBackend"] is True
    assert prototypes["/labs/generate"]["safety"]["realLlmCalled"] is False
    assert prototypes["/labs/generate"]["safety"]["realPublish"] is False
    assert "frontend/lab-generate-data.js" in prototypes["/labs/generate"]["dataSources"]
    assert "LocalCoreGenerationWorkspace" in prototypes["/labs/generate"]["dataSources"]
    assert "frontendDirectRealLlmCall=false" in prototypes["/labs/generate"]["dataSources"]
    assert "realLlmResultCanEnterViaCliOrBackend=true" in prototypes["/labs/generate"]["dataSources"]
    assert "LabGenerationCloseLoopAction" in prototypes["/labs/generate"]["dataSources"]
    assert "query: coreDbPath, gradingDbPath, agentReport" in prototypes["/labs/generate"]["dataSources"]
    assert "POST /api/labs/generate.task" in prototypes["/labs/generate"]["dataSources"]
    assert "POST /api/labs/generate.materialAnalysis" in prototypes["/labs/generate"]["dataSources"]
    assert "POST /api/labs/generate.providerGeneration" in prototypes["/labs/generate"]["dataSources"]
    assert "POST /api/labs/generate.closeLoopAction" in prototypes["/labs/generate"]["dataSources"]
    assert "POST /api/labs/generate body.coreDbPath" in prototypes["/labs/generate"]["dataSources"]
    assert "review-center.html?taskId={taskId}" in prototypes["/labs/generate"]["dataSources"]
    assert (
        "review-center.html?taskId={taskId}&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in prototypes["/labs/generate"]["dataSources"]
    )
    assert "lab-review.html?taskId={taskId}" in prototypes["/labs/generate"]["dataSources"]
    assert (
        "lab-review.html?taskId={taskId}&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in prototypes["/labs/generate"]["dataSources"]
    )
    assert "agent-entities.html?sourceTaskId={taskId}&entityKind=lab" in prototypes["/labs/generate"]["dataSources"]
    assert (
        "agent-entities.html?sourceTaskId={taskId}&entityKind=lab&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in prototypes["/labs/generate"]["dataSources"]
    )
    assert prototypes["/labs/:id/review"]["mode"] == "MOCK_ONLY"
    assert (
        "frontend/mock-data.json.reviewDetail.reviewPage.providerSummary.qualitySummary"
        in prototypes["/labs/:id/review"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewDetail.reviewPage.providerSummary.calls[].qualitySummary"
        in prototypes["/labs/:id/review"]["dataSources"]
    )
    assert prototypes["/labs/:id/review"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/labs/:id/review"]["safety"]["batchStateChangeAllowed"] is False
    assert prototypes["/labs/:id/review"]["safety"]["realPublish"] is False
    assert prototypes["/grading"]["mode"] == "MOCK_ONLY"
    assert prototypes["/grading"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/grading"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/grading"]["safety"]["realRegradeEnabled"] is False
    assert prototypes["/grading/:id/review"]["mode"] == "MOCK_ONLY"
    assert prototypes["/grading/:id/review"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/grading/:id/review"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/grading/:id/review"]["safety"]["realRegradeEnabled"] is False
    assert prototypes["/grading/:id/review"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/grading/:id/report"]["mode"] == "LOCAL_CORE_MVP"
    assert prototypes["/grading/:id/report"]["safety"]["sandboxExecuted"] is False
    assert (
        "GET /api/grading/report?file={file}&taskId={id}.mergedGradingEvidence"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert (
        "GET /api/grading/report?file={file}&taskId={id}.mergedGradingEvidenceCheckItems"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert (
        "GET /api/grading/report?file={file}&taskId={id}.reviewDecisionNotes"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.reviewDecisionNotes"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence.checkEvidenceReviewItems"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence.checkEvidenceReviewItems[].recommendedAction"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert (
        "GET /api/grading/report?file={file}&taskId={id}.mergedGradingEvidenceCheckItems[].recommendedAction"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert (
        "GET /api/grading/records?taskId={id}.items"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert (
        "GET /api/grading/records?taskId={id}.GradingRecordReviewIntegration"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert prototypes["/ai-tasks"]["mode"] == "MOCK_ONLY"
    assert "frontend/mock-data.json.aiTaskCenterPrototype.qualitySignalTaskSignal" in prototypes["/ai-tasks"]["dataSources"]
    assert "frontend/mock-data.json.aiTaskCenterPrototype.providerQualityTaskSignal" in prototypes["/ai-tasks"]["dataSources"]
    assert (
        "frontend/mock-data.json.reviewDetail.reviewPage.providerSummary.qualitySummary"
        in prototypes["/ai-tasks"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.reviewDetail.reviewPage.providerSummary.calls[].qualitySummary"
        in prototypes["/ai-tasks"]["dataSources"]
    )
    assert "frontend/mock-data.json.aiTaskCenterPrototype.reviewPrioritySignal" in prototypes["/ai-tasks"]["dataSources"]
    assert "frontend/mock-data.json.reviewCenterPrototype.reviewPriorityQueue" in prototypes["/ai-tasks"]["dataSources"]
    assert (
        "frontend/mock-data.json.reviewCenterPrototype.assessmentPlanManualReviewQueueSignal"
        in prototypes["/ai-tasks"]["dataSources"]
    )
    assert "frontend/mock-data.json.examReviewPrototype.qualitySignals" in prototypes["/ai-tasks"]["dataSources"]
    assert (
        "frontend/mock-data.json.examReviewPrototype.dslPreview.candidateSafeExamPreview"
        in prototypes["/ai-tasks"]["dataSources"]
    )
    assert "frontend/mock-data.json.gradingReviewPrototype.qualitySignals" in prototypes["/ai-tasks"]["dataSources"]
    assert "frontend/mock-data.json.gradingReviewPrototype.assessmentPlanSummary" in prototypes["/ai-tasks"]["dataSources"]
    assert "AiTaskExecutionWorkspace" in prototypes["/ai-tasks"]["dataSources"]
    assert "frontend/ai-tasks-data.js" in prototypes["/ai-tasks"]["dataSources"]
    assert "query: coreDbPath" in prototypes["/ai-tasks"]["dataSources"]
    assert "GET /api/backend/core-tasks?coreDbPath={path}" in prototypes["/ai-tasks"]["dataSources"]
    assert "GET /api/backend/core-tasks?coreDbPath={path}&status=WAITING_REVIEW" in prototypes["/ai-tasks"]["dataSources"]
    assert "GET /api/backend/core-tasks/{id}.taskExecutionWorkspace" in prototypes["/ai-tasks"]["dataSources"]
    assert "GET /api/backend/core-tasks/{id}.task" in prototypes["/ai-tasks"]["dataSources"]
    assert "GET /api/ai-tasks?status=WAITING_REVIEW" in prototypes["/ai-tasks"]["dataSources"]
    assert "GET /api/ai-tasks/{id}.taskExecutionWorkspace" in prototypes["/ai-tasks"]["dataSources"]
    assert "GET /api/ai-tasks/{id}.task" in prototypes["/ai-tasks"]["dataSources"]
    assert "GET /api/review-task-summary.taskExecutionWorkspace" in prototypes["/ai-tasks"]["dataSources"]
    assert (
        "GET /api/review-task-summary.reviewTaskSummary.reviewPriorityQueue"
        in prototypes["/ai-tasks"]["dataSources"]
    )
    assert "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary" in prototypes["/ai-tasks"]["dataSources"]
    assert prototypes["/ai-tasks"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/dashboard"]["mode"] == "MOCK_ONLY"
    assert "frontend/mock-data.json.gradingReviewPrototype.assessmentPlanSummary" in prototypes["/dashboard"]["dataSources"]
    assert "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary" in prototypes["/dashboard"]["dataSources"]
    assert prototypes["/dashboard"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/console"]["mode"] == "MOCK_ONLY"
    assert prototypes["/console"]["safety"]["realAgentStarted"] is False
    assert prototypes["/console"]["safety"]["realLlmCalled"] is False
    assert prototypes["/console"]["safety"]["realCloudResourceCreated"] is False
    assert prototypes["/console"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/console"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/console"]["safety"]["unknownShellExecuted"] is False
    assert prototypes["/console"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/console"]["safety"]["batchStateChangeAllowed"] is False
    assert prototypes["/console"]["safety"]["realPublish"] is False
    assert prototypes["/console"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert prototypes["/console"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/workflows"]["mode"] == "MOCK_ONLY"
    assert prototypes["/workflows"]["safety"]["readOnly"] is True
    assert prototypes["/workflows"]["safety"]["realLlmCalled"] is False
    assert prototypes["/workflows"]["safety"]["realMcpServerStarted"] is False
    assert prototypes["/workflows"]["safety"]["realAgentStarted"] is False
    assert prototypes["/workflows"]["safety"]["workflowExecuted"] is False
    assert prototypes["/workflows"]["safety"]["taskCreated"] is False
    assert prototypes["/workflows"]["safety"]["artifactCreated"] is False
    assert prototypes["/workflows"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/workflows"]["safety"]["realPublish"] is False
    assert prototypes["/workflows"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/workflows"]["safety"]["answerVisibleToCandidate"] is False
    assert prototypes["/real-demo"]["mode"] == "REAL_LLM_DEMO_REPLAY_STATIC"
    assert "frontend/mock-data.json.realDemoPrototype" in prototypes["/real-demo"]["dataSources"]
    assert "frontend/mock-data.json.realDemoPrototype.coreBusinessDemoPath" in prototypes["/real-demo"]["dataSources"]
    assert (
        "frontend/mock-data.json.realDemoPrototype.realDemoAcceptanceSummary"
        in prototypes["/real-demo"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.realDemoPrototype.oneClickDemoChecklist"
        in prototypes["/real-demo"]["dataSources"]
    )
    assert "frontend/mock-data.json.realDemoPrototype.realDslReviewPreview" in prototypes["/real-demo"]["dataSources"]
    assert "examples/output/real-llm-demo-real-dsl-review-preview.json" in prototypes["/real-demo"]["dataSources"]
    assert "frontend/mock-data.json.realDemoPrototype.realDslRevisionDiffPreview" in prototypes["/real-demo"]["dataSources"]
    assert "examples/output/real-llm-demo-revision-diff-preview.json" in prototypes["/real-demo"]["dataSources"]
    assert "frontend/mock-data.json.realDemoPrototype.realDslRevisionDecision" in prototypes["/real-demo"]["dataSources"]
    assert "examples/output/real-llm-demo-revision-decision-report.json" in prototypes["/real-demo"]["dataSources"]
    assert "frontend/mock-data.json.realDemoPrototype.realDslRevisionPromotion" in prototypes["/real-demo"]["dataSources"]
    assert "examples/output/real-llm-demo-revision-promotion-report.json" in prototypes["/real-demo"]["dataSources"]
    assert (
        "frontend/mock-data.json.realDemoPrototype.realDslRevisionPromotionReviewQueueItem"
        in prototypes["/real-demo"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.realDemoPrototype.realDslRevisionPromotionReviewDisposition"
        in prototypes["/real-demo"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.realDemoPrototype.labTemplateImportPreview"
        in prototypes["/real-demo"]["dataSources"]
    )
    assert "POST /api/labs/import-preview" in prototypes["/real-demo"]["dataSources"]
    assert "POST /api/review/real-dsl-revision-enqueue" in prototypes["/real-demo"]["dataSources"]
    assert "examples/output/real-llm-demo-bundle.json" in prototypes["/real-demo"]["dataSources"]
    assert "examples/output/real-llm-demo-acceptance-summary.json" in prototypes["/real-demo"]["dataSources"]
    assert "examples/output/real-llm-demo-checklist.json" in prototypes["/real-demo"]["dataSources"]
    assert prototypes["/real-demo"]["safety"]["realLlmCalled"] is True
    assert prototypes["/real-demo"]["safety"]["newLlmRequestSent"] is False
    assert prototypes["/real-demo"]["safety"]["secretsRead"] is False
    assert prototypes["/real-demo"]["safety"]["readonlyEvidenceDemoExecuted"] is True
    assert prototypes["/real-demo"]["safety"]["sourceGradingModified"] is False
    assert prototypes["/real-demo"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/real-demo"]["safety"]["realPublish"] is False
    pages = {page["route"]: page for page in manifest["pages"]}
    assert "RealDemoOneClickChecklist" in pages["/real-demo"]["components"]
    assert "RealDemoMcpRevisionLoop" in pages["/real-demo"]["components"]
    assert "RealDslReviewPreview" in pages["/real-demo"]["components"]
    assert "RealDslRevisionPromotionReviewQueueItem" in pages["/real-demo"]["components"]
    assert "RealDslRevisionPromotionReviewDisposition" in pages["/real-demo"]["components"]
    assert prototypes["/audit"]["mode"] == "MOCK_ONLY"
    assert "frontend/mock-data.json.highRiskMcpIntentPrototype" in prototypes["/audit"]["dataSources"]
    assert "frontend/mock-data.json.secondConfirmationStatusPrototype" in prototypes["/audit"]["dataSources"]
    assert prototypes["/audit"]["safety"]["realLlmCalled"] is False
    assert prototypes["/audit"]["safety"]["realMcpServerStarted"] is False
    assert prototypes["/audit"]["safety"]["realAgentStarted"] is False
    assert prototypes["/audit"]["safety"]["secretsRead"] is False
    assert prototypes["/audit"]["safety"]["networkAccess"] is False
    assert prototypes["/audit"]["safety"]["realCloudResourceChanged"] is False
    assert prototypes["/audit"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/audit"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/audit"]["safety"]["secondConfirmationStatusReadOnly"] is True
    assert prototypes["/audit"]["safety"]["confirmationEndpointEnabled"] is False
    assert prototypes["/audit"]["safety"]["highRiskIntentExecutionAllowed"] is False
    assert prototypes["/audit"]["safety"]["environmentDestroyed"] is False
    assert prototypes["/audit"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/audit"]["safety"]["realPublish"] is False
    assert prototypes["/audit"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/audit/:id"]["mode"] == "MOCK_ONLY"
    assert prototypes["/audit/:id"]["safety"]["readOnly"] is True
    assert prototypes["/audit/:id"]["safety"]["realLlmCalled"] is False
    assert prototypes["/audit/:id"]["safety"]["realMcpServerStarted"] is False
    assert prototypes["/audit/:id"]["safety"]["realAgentStarted"] is False
    assert prototypes["/audit/:id"]["safety"]["secretsRead"] is False
    assert prototypes["/audit/:id"]["safety"]["networkAccess"] is False
    assert prototypes["/audit/:id"]["safety"]["realCloudResourceChanged"] is False
    assert prototypes["/audit/:id"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/audit/:id"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/audit/:id"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/audit/:id"]["safety"]["realPublish"] is False
    assert prototypes["/audit/:id"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/audit/incidents"]["mode"] == "MOCK_ONLY"
    assert prototypes["/audit/incidents"]["safety"]["readOnly"] is True
    assert prototypes["/audit/incidents"]["safety"]["realLlmCalled"] is False
    assert prototypes["/audit/incidents"]["safety"]["realMcpServerStarted"] is False
    assert prototypes["/audit/incidents"]["safety"]["realAgentStarted"] is False
    assert prototypes["/audit/incidents"]["safety"]["secretsRead"] is False
    assert prototypes["/audit/incidents"]["safety"]["networkAccess"] is False
    assert prototypes["/audit/incidents"]["safety"]["realCloudResourceChanged"] is False
    assert prototypes["/audit/incidents"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/audit/incidents"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/audit/incidents"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/audit/incidents"]["safety"]["realPublish"] is False
    assert prototypes["/audit/incidents"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/operations/runbook"]["mode"] == "MOCK_ONLY"
    assert prototypes["/operations/runbook"]["safety"]["readOnly"] is True
    assert prototypes["/operations/runbook"]["safety"]["realLlmCalled"] is False
    assert prototypes["/operations/runbook"]["safety"]["realMcpServerStarted"] is False
    assert prototypes["/operations/runbook"]["safety"]["realAgentStarted"] is False
    assert prototypes["/operations/runbook"]["safety"]["secretsRead"] is False
    assert prototypes["/operations/runbook"]["safety"]["networkAccess"] is False
    assert prototypes["/operations/runbook"]["safety"]["realCloudResourceChanged"] is False
    assert prototypes["/operations/runbook"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/operations/runbook"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/operations/runbook"]["safety"]["unknownShellExecuted"] is False
    assert prototypes["/operations/runbook"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/operations/runbook"]["safety"]["realPublish"] is False
    assert prototypes["/operations/runbook"]["safety"]["remoteUploadAllowed"] is False
    assert prototypes["/operations/runbook"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/operations/acceptance"]["mode"] == "MOCK_ONLY"
    assert (
        "frontend/mock-data.json.auditObservabilityPrototype.assessmentPlanAuditSignal"
        in prototypes["/operations/acceptance"]["dataSources"]
    )
    assert "frontend/mock-data.json.gradingReport.assessmentPlanSummary" in prototypes["/operations/acceptance"]["dataSources"]
    assert (
        "frontend/mock-data.json.operationAuditEvents.detail.assessmentPlanSummary"
        in prototypes["/operations/acceptance"]["dataSources"]
    )
    assert prototypes["/operations/acceptance"]["safety"]["readOnly"] is True
    assert prototypes["/operations/acceptance"]["safety"]["realLlmCalled"] is False
    assert prototypes["/operations/acceptance"]["safety"]["realMcpServerStarted"] is False
    assert prototypes["/operations/acceptance"]["safety"]["realAgentStarted"] is False
    assert prototypes["/operations/acceptance"]["safety"]["secretsRead"] is False
    assert prototypes["/operations/acceptance"]["safety"]["networkAccess"] is False
    assert prototypes["/operations/acceptance"]["safety"]["realCloudResourceChanged"] is False
    assert prototypes["/operations/acceptance"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/operations/acceptance"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/operations/acceptance"]["safety"]["unknownShellExecuted"] is False
    assert prototypes["/operations/acceptance"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/operations/acceptance"]["safety"]["realPublish"] is False
    assert prototypes["/operations/acceptance"]["safety"]["remoteUploadAllowed"] is False
    assert prototypes["/operations/acceptance"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/operations/demo-map"]["mode"] == "MOCK_ONLY"
    assert prototypes["/operations/demo-map"]["safety"]["readOnly"] is True
    assert prototypes["/operations/demo-map"]["safety"]["realLlmCalled"] is False
    assert prototypes["/operations/demo-map"]["safety"]["realMcpServerStarted"] is False
    assert prototypes["/operations/demo-map"]["safety"]["realAgentStarted"] is False
    assert prototypes["/operations/demo-map"]["safety"]["secretsRead"] is False
    assert prototypes["/operations/demo-map"]["safety"]["networkAccess"] is False
    assert prototypes["/operations/demo-map"]["safety"]["realCloudResourceChanged"] is False
    assert prototypes["/operations/demo-map"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/operations/demo-map"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/operations/demo-map"]["safety"]["unknownShellExecuted"] is False
    assert prototypes["/operations/demo-map"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/operations/demo-map"]["safety"]["realPublish"] is False
    assert prototypes["/operations/demo-map"]["safety"]["remoteUploadAllowed"] is False
    assert prototypes["/operations/demo-map"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/operations/presenter"]["mode"] == "MOCK_ONLY"
    assert (
        "frontend/mock-data.json.auditObservabilityPrototype.assessmentPlanAuditSignal"
        in prototypes["/operations/presenter"]["dataSources"]
    )
    assert "frontend/mock-data.json.gradingReport.assessmentPlanSummary" in prototypes["/operations/presenter"]["dataSources"]
    assert (
        "frontend/mock-data.json.operationAuditEvents.detail.assessmentPlanSummary"
        in prototypes["/operations/presenter"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.realDemoPrototype.coreBusinessDemoPath"
        in prototypes["/operations/presenter"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.realDemoPrototype.realDemoAcceptanceSummary"
        in prototypes["/operations/presenter"]["dataSources"]
    )
    assert prototypes["/operations/presenter"]["safety"]["readOnly"] is True
    assert prototypes["/operations/presenter"]["safety"]["realLlmCalled"] is False
    assert prototypes["/operations/presenter"]["safety"]["realMcpServerStarted"] is False
    assert prototypes["/operations/presenter"]["safety"]["realAgentStarted"] is False
    assert prototypes["/operations/presenter"]["safety"]["secretsRead"] is False
    assert prototypes["/operations/presenter"]["safety"]["networkAccess"] is False
    assert prototypes["/operations/presenter"]["safety"]["realCloudResourceChanged"] is False
    assert prototypes["/operations/presenter"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/operations/presenter"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/operations/presenter"]["safety"]["unknownShellExecuted"] is False
    assert prototypes["/operations/presenter"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/operations/presenter"]["safety"]["realPublish"] is False
    assert prototypes["/operations/presenter"]["safety"]["remoteUploadAllowed"] is False
    assert prototypes["/operations/presenter"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/operations/presenter"]["safety"]["answerVisibleToCandidate"] is False
    assert prototypes["/operations/signoff"]["mode"] == "MOCK_ONLY"
    assert "frontend/mock-data.json.reviewCenterPrototype.reviewPriorityQueue" in prototypes["/operations/signoff"]["dataSources"]
    assert "frontend/mock-data.json.realDemoPrototype.coreBusinessDemoPath" in prototypes["/operations/signoff"]["dataSources"]
    assert (
        "frontend/mock-data.json.realDemoPrototype.realDemoAcceptanceSummary"
        in prototypes["/operations/signoff"]["dataSources"]
    )
    assert "GET /api/review-task-summary" in prototypes["/operations/signoff"]["dataSources"]
    assert "mcp-server/tools.manifest.json.get_review_task_summary.outputContract" in prototypes["/operations/signoff"]["dataSources"]
    assert prototypes["/operations/signoff"]["safety"]["readOnly"] is True
    assert prototypes["/operations/signoff"]["safety"]["realLlmCalled"] is False
    assert prototypes["/operations/signoff"]["safety"]["realMcpServerStarted"] is False
    assert prototypes["/operations/signoff"]["safety"]["realAgentStarted"] is False
    assert prototypes["/operations/signoff"]["safety"]["secretsRead"] is False
    assert prototypes["/operations/signoff"]["safety"]["networkAccess"] is False
    assert prototypes["/operations/signoff"]["safety"]["realCloudResourceChanged"] is False
    assert prototypes["/operations/signoff"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/operations/signoff"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/operations/signoff"]["safety"]["unknownShellExecuted"] is False
    assert prototypes["/operations/signoff"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/operations/signoff"]["safety"]["realPublish"] is False
    assert prototypes["/operations/signoff"]["safety"]["remoteUploadAllowed"] is False
    assert prototypes["/operations/signoff"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/operations/signoff"]["safety"]["answerVisibleToCandidate"] is False
    assert prototypes["/operations/demo-script"]["mode"] == "MOCK_ONLY"
    assert (
        "frontend/mock-data.json.auditObservabilityPrototype.assessmentPlanAuditSignal"
        in prototypes["/operations/demo-script"]["dataSources"]
    )
    assert "frontend/mock-data.json.gradingReport.assessmentPlanSummary" in prototypes["/operations/demo-script"]["dataSources"]
    assert (
        "frontend/mock-data.json.operationAuditEvents.detail.assessmentPlanSummary"
        in prototypes["/operations/demo-script"]["dataSources"]
    )
    assert prototypes["/operations/demo-script"]["safety"]["readOnly"] is True
    assert prototypes["/operations/demo-script"]["safety"]["realLlmCalled"] is False
    assert prototypes["/operations/demo-script"]["safety"]["realMcpServerStarted"] is False
    assert prototypes["/operations/demo-script"]["safety"]["realAgentStarted"] is False
    assert prototypes["/operations/demo-script"]["safety"]["secretsRead"] is False
    assert prototypes["/operations/demo-script"]["safety"]["networkAccess"] is False
    assert prototypes["/operations/demo-script"]["safety"]["realCloudResourceChanged"] is False
    assert prototypes["/operations/demo-script"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/operations/demo-script"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/operations/demo-script"]["safety"]["unknownShellExecuted"] is False
    assert prototypes["/operations/demo-script"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/operations/demo-script"]["safety"]["realPublish"] is False
    assert prototypes["/operations/demo-script"]["safety"]["remoteUploadAllowed"] is False
    assert prototypes["/operations/demo-script"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/operations/demo-script"]["safety"]["answerVisibleToCandidate"] is False
    assert prototypes["/operations/launchpad"]["mode"] == "MOCK_ONLY"
    assert prototypes["/operations/launchpad"]["safety"]["readOnly"] is True
    assert prototypes["/operations/launchpad"]["safety"]["realLlmCalled"] is False
    assert prototypes["/operations/launchpad"]["safety"]["realMcpServerStarted"] is False
    assert prototypes["/operations/launchpad"]["safety"]["realAgentStarted"] is False
    assert prototypes["/operations/launchpad"]["safety"]["secretsRead"] is False
    assert prototypes["/operations/launchpad"]["safety"]["networkAccess"] is False
    assert prototypes["/operations/launchpad"]["safety"]["realCloudResourceChanged"] is False
    assert prototypes["/operations/launchpad"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/operations/launchpad"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/operations/launchpad"]["safety"]["unknownShellExecuted"] is False
    assert prototypes["/operations/launchpad"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/operations/launchpad"]["safety"]["realPublish"] is False
    assert prototypes["/operations/launchpad"]["safety"]["remoteUploadAllowed"] is False
    assert prototypes["/operations/launchpad"]["safety"]["secretVisibleInFrontend"] is False
    assert prototypes["/access"]["mode"] == "MOCK_ONLY"
    assert prototypes["/access"]["path"] == "frontend/access.html"
    assert "frontend/mock-data.json.accessEntrypointsPrototype" in prototypes["/access"]["dataSources"]
    assert prototypes["/access"]["safety"]["readOnly"] is True
    assert prototypes["/access"]["safety"]["realHttpServerStarted"] is False
    assert prototypes["/access"]["safety"]["portListening"] is False
    assert prototypes["/access"]["safety"]["externalIpBound"] is False
    assert prototypes["/access"]["safety"]["networkAccess"] is False
    assert prototypes["/access"]["safety"]["realAgentStarted"] is False
    assert prototypes["/delivery"]["mode"] == "MOCK_ONLY"
    assert prototypes["/delivery"]["safety"]["realLlmCalled"] is False
    assert prototypes["/delivery"]["safety"]["realCloudResourceChanged"] is False
    assert prototypes["/delivery"]["safety"]["sandboxExecuted"] is False
    assert prototypes["/delivery"]["safety"]["contestantCodeExecuted"] is False
    assert prototypes["/delivery"]["safety"]["unknownShellExecuted"] is False
    assert prototypes["/delivery"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/delivery"]["safety"]["realPublish"] is False
    assert prototypes["/delivery"]["safety"]["remoteUploadAllowed"] is False
    assert prototypes["/labs"]["mode"] == "MOCK_ONLY"
    assert prototypes["/labs"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/labs"]["safety"]["batchStateChangeAllowed"] is False
    assert prototypes["/labs"]["safety"]["realPublish"] is False
    assert prototypes["/ppt"]["mode"] == "MOCK_ONLY"
    assert prototypes["/ppt"]["safety"]["realLlmCalled"] is False
    assert prototypes["/ppt"]["safety"]["artifactGenerated"] is False
    assert prototypes["/ppt"]["safety"]["realPptFileGenerated"] is False
    assert prototypes["/ppt"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/ppt/:id/review"]["mode"] == "MOCK_ONLY"
    assert prototypes["/ppt/:id/review"]["safety"]["realLlmCalled"] is False
    assert prototypes["/ppt/:id/review"]["safety"]["artifactGenerated"] is False
    assert prototypes["/ppt/:id/review"]["safety"]["realPptFileGenerated"] is False
    assert prototypes["/ppt/:id/review"]["safety"]["pageReviewUpdateTaskStatusChanged"] is False
    assert prototypes["/ppt/:id/review"]["safety"]["pageReviewUpdateAutoApproveAllowed"] is False
    assert prototypes["/ppt/:id/review"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/exams"]["mode"] == "MOCK_ONLY"
    assert prototypes["/exams"]["safety"]["answerVisibleToCandidate"] is False
    assert prototypes["/exams"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert prototypes["/exams"]["safety"]["realPublish"] is False
    assert prototypes["/exams/:id/review"]["mode"] == "MOCK_ONLY"
    assert prototypes["/exams/:id/review"]["safety"]["answerVisibleToCandidate"] is False
    assert prototypes["/exams/:id/review"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert prototypes["/exams/:id/review"]["safety"]["autoPublishAllowed"] is False
    assert prototypes["/exams/:id/review"]["safety"]["realPublish"] is False
    assert prototypes["/exams/generate"]["mode"] == "MOCK_ONLY"
    assert prototypes["/exams/generate"]["safety"]["answerVisibleToCandidate"] is False
    assert prototypes["/exams/generate"]["safety"]["generatedStatus"] == "WAITING_REVIEW"
    assert prototypes["/exams/generate"]["safety"]["apiMockGenerationEnabled"] is True
    assert prototypes["/exams/generate"]["safety"]["localCoreGenerationWorkspace"] is True
    assert prototypes["/exams/generate"]["safety"]["frontendDirectRealLlmCall"] is False
    assert prototypes["/exams/generate"]["safety"]["realLlmResultCanEnterViaCliOrBackend"] is True
    assert prototypes["/exams/generate"]["safety"]["gradingRefVisibleToCandidate"] is False
    assert prototypes["/exams/generate"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert "frontend/exam-generate-data.js" in prototypes["/exams/generate"]["dataSources"]
    assert "LocalCoreGenerationWorkspace" in prototypes["/exams/generate"]["dataSources"]
    assert "frontendDirectRealLlmCall=false" in prototypes["/exams/generate"]["dataSources"]
    assert "realLlmResultCanEnterViaCliOrBackend=true" in prototypes["/exams/generate"]["dataSources"]
    assert "ExamGenerationCloseLoopAction" in prototypes["/exams/generate"]["dataSources"]
    assert "query: coreDbPath, gradingDbPath, agentReport" in prototypes["/exams/generate"]["dataSources"]
    assert "POST /api/exams/generate-from-lab.examDsl" in prototypes["/exams/generate"]["dataSources"]
    assert "POST /api/exams/generate-from-lab.gradingDsl" in prototypes["/exams/generate"]["dataSources"]
    assert "POST /api/exams/generate-from-lab.closeLoopAction" in prototypes["/exams/generate"]["dataSources"]
    assert "POST /api/exams/generate-from-lab body.coreDbPath" in prototypes["/exams/generate"]["dataSources"]
    assert "exam-review.html?taskId={taskId}" in prototypes["/exams/generate"]["dataSources"]
    assert (
        "exam-review.html?taskId={taskId}&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in prototypes["/exams/generate"]["dataSources"]
    )
    assert "grading-review.html?taskId={taskId}" in prototypes["/exams/generate"]["dataSources"]
    assert (
        "grading-review.html?taskId={taskId}&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in prototypes["/exams/generate"]["dataSources"]
    )
    assert "agent-entities.html?sourceTaskId={taskId}&entityKind=exam" in prototypes["/exams/generate"]["dataSources"]
    assert "agent-entities.html?sourceTaskId={taskId}&entityKind=grading" in prototypes["/exams/generate"]["dataSources"]
    assert (
        "agent-entities.html?sourceTaskId={taskId}&entityKind=exam&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in prototypes["/exams/generate"]["dataSources"]
    )
    assert (
        "agent-entities.html?sourceTaskId={taskId}&entityKind=grading&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in prototypes["/exams/generate"]["dataSources"]
    )
    assert prototypes["/environments"]["mode"] == "MOCK_ONLY"
    assert prototypes["/environments"]["safety"]["realCloudResourceCreated"] is False
    assert prototypes["/environments"]["safety"]["destroyRealResourceAllowed"] is False
    assert prototypes["/skills"]["mode"] == "MOCK_ONLY"
    assert prototypes["/skills"]["safety"]["realAgentStarted"] is False
    assert prototypes["/skills"]["safety"]["businessCodeMayEmbedPrompts"] is False
    assert prototypes["/settings/providers"]["mode"] == "MOCK_ONLY"
    assert prototypes["/settings/providers"]["safety"]["realProviderEnabled"] is False
    assert prototypes["/settings/providers"]["safety"]["secretsRead"] is False
    assert prototypes["/settings/providers"]["safety"]["secretVisibleInFrontend"] is False
    assert "PptDslPreview" in manifest["components"]
    assert "AuditTrailPanel" in manifest["components"]
    assert "DeliveryChecklistPanel" in manifest["components"]
    assert "ConsoleNavPanel" in manifest["components"]
    assert "AgentEntityPausedBackendHandoffNotice" in manifest["components"]
    assert "AgentEntityImportSendAction" not in manifest["components"]
    assert "AgentEntityFinalPublishReviewPanel" not in manifest["components"]
    assert "FinalPublishReviewDecision" not in manifest["components"]


def test_frontend_manifest_routes_are_unique_and_have_mock_data():
    manifest = load_json("frontend/ui.manifest.json")
    routes = [page["route"] for page in manifest["pages"]]

    assert len(routes) == len(set(routes))
    for page in manifest["pages"]:
        assert (ROOT / page["mockDataPath"]).exists()
        if "prototypePath" in page:
            assert (ROOT / page["prototypePath"]).exists()
        assert page["route"].startswith("/")
        assert page["priority"] in {1, 2}

    for prototype in manifest["staticPrototypes"]:
        assert (ROOT / prototype["path"]).exists()
        assert prototype["route"].startswith("/")


def test_frontend_manifest_uses_known_components():
    manifest = load_json("frontend/ui.manifest.json")
    known_components = set(manifest["components"])

    for page in manifest["pages"]:
        assert set(page["components"]) <= known_components


def test_frontend_manifest_api_dependencies_map_to_mock_api():
    manifest = load_json("frontend/ui.manifest.json")

    for page in manifest["pages"]:
        for dependency in page["apiDependencies"]:
            assert dependency["method"] in {"GET", "POST"}
            assert dependency["path"].startswith("/api/")


def test_frontend_manifest_enforces_review_and_answer_safety():
    manifest = load_json("frontend/ui.manifest.json")
    prototypes = {prototype["route"]: prototype for prototype in manifest["staticPrototypes"]}
    pages = {page["route"]: page for page in manifest["pages"]}

    review_center_deps = {dependency["path"] for dependency in pages["/review-center"]["apiDependencies"]}
    assert review_center_deps == {
        "/api/review-task-summary",
        "/api/review-tasks/{id}",
        "/api/grading/records",
        "/api/backend/core-tasks/{id}",
        "/api/ai-tasks/{id}/approve",
        "/api/ai-tasks/{id}/reject",
        "/api/platform-entities/readiness-report",
        "/api/review-tasks/{id}/ppt-page-review-status",
        "/api/grading/evidence-auto",
        "/api/review-audit-events",
    }
    assert pages["/review-center"]["prototypePath"] == "frontend/review-center.html"
    assert "MvpReviewWorkspace" in pages["/review-center"]["components"]
    assert "RealDemoReviewQueue" in pages["/review-center"]["components"]
    assert "ReviewCenterDataLoader" in pages["/review-center"]["components"]
    assert "RealDslContentQualityDecision" in pages["/review-center"]["components"]
    assert "ControlledDockerEvidenceReviewSignal" in pages["/review-center"]["components"]
    assert "GradingEvidenceReadiness" in pages["/review-center"]["components"]
    assert "GradingEvidenceActionGuide" in pages["/review-center"]["components"]
    assert "NotebookEvidenceReviewPlan" in pages["/review-center"]["components"]
    assert "CoreBusinessDemoPath" in pages["/review-center"]["components"]
    assert "RealDslRevisionDiffPreview" in pages["/review-center"]["components"]
    assert "RealDslRevisionDecision" in pages["/review-center"]["components"]
    assert "RealDslRevisionPromotion" in pages["/review-center"]["components"]
    assert "AgentImportPreviewActionPanel" in pages["/review-center"]["components"]
    assert "LabTemplateImportPreview" in pages["/review-center"]["components"]
    assert "AgentImportPreviewSummary" in pages["/review-center"]["components"]
    assert "AgentImportPreviewSignoffChecklist" in pages["/review-center"]["components"]
    assert "AgentEntityReadinessReport" in pages["/review-center"]["components"]
    assert "ExamQuestionImportPreview" in pages["/review-center"]["components"]
    assert "GradingRuleImportPreview" in pages["/review-center"]["components"]
    assert "GradingEvidenceAutoAction" in pages["/review-center"]["components"]
    assert pages["/review-center"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/review-center"]["safety"]["realPublishAllowed"] is False
    agent_entity_deps = {dependency["path"] for dependency in pages["/platform-entities"]["apiDependencies"]}
    assert agent_entity_deps == {
        "/api/platform-entities",
        "/api/platform-entities/{id}",
        "/api/platform-entities/readiness-report",
        "/api/platform-entities/contract-validate",
        "/api/labs/import-preview",
        "/api/labs/mock-import",
        "/api/exams/import-preview",
        "/api/exams/mock-import",
        "/api/grading/import-preview",
        "/api/grading/mock-import",
        "/api/ppt/import-preview",
        "/api/ppt/mock-import",
        "/api/platform-entities/{id}/import-dry-run",
    }
    assert pages["/platform-entities"]["prototypePath"] == "frontend/agent-entities.html"
    assert "AgentEntityMockStore" in pages["/platform-entities"]["components"]
    assert "AgentEntityReadinessReport" in pages["/platform-entities"]["components"]
    assert "AgentEntityImportStepper" in pages["/platform-entities"]["components"]
    assert "AgentEntityDemoDataPrepareAction" in pages["/platform-entities"]["components"]
    assert "AgentEntityImportDryRunAction" in pages["/platform-entities"]["components"]
    assert "AgentEntityPausedBackendHandoffNotice" in pages["/platform-entities"]["components"]
    assert "AgentEntityImportSendAction" not in pages["/platform-entities"]["components"]
    assert "AgentEntityImportStatusQueryAction" not in pages["/platform-entities"]["components"]
    assert "AgentEntityImportResultRecordAction" not in pages["/platform-entities"]["components"]
    assert "AgentEntitySignoffRecordAction" not in pages["/platform-entities"]["components"]
    assert "AgentEntityFinalPublishReviewPanel" not in pages["/platform-entities"]["components"]
    assert pages["/platform-entities"]["safety"]["readOnly"] is True
    assert pages["/platform-entities"]["safety"]["databaseWritten"] is False
    assert pages["/platform-entities"]["safety"]["realAgentImport"] is False
    assert pages["/platform-entities"]["safety"]["demoDataPrepareEnabled"] is True
    assert pages["/platform-entities"]["safety"]["realAgentImportDryRunEnabled"] is True
    assert pages["/platform-entities"]["safety"]["realAgentImportSendEnabled"] is False
    assert pages["/platform-entities"]["safety"]["realAgentImportStatusQueryEnabled"] is False
    assert pages["/platform-entities"]["safety"]["manualImportResultRecordEnabled"] is False
    assert pages["/platform-entities"]["safety"]["manualAgentEntitySignoffEnabled"] is False
    assert pages["/platform-entities"]["safety"]["requiresFinalHumanReviewBeforePublish"] is False
    assert pages["/platform-entities"]["safety"]["platformBackendRequired"] is False
    assert pages["/platform-entities"]["safety"]["pausedPlatformBackendHandoff"] is True
    assert pages["/platform-entities"]["safety"]["realPublish"] is False
    assert "GET /api/platform-entities" in prototypes["/platform-entities"]["dataSources"]
    assert (
        "query: entityId, sourceTaskId, entityKind, coreDbPath, gradingDbPath, agentReport"
        in prototypes["/platform-entities"]["dataSources"]
    )
    assert "GET /api/platform-entities/{id}" in prototypes["/platform-entities"]["dataSources"]
    assert "GET /api/platform-entities/{id}.agentEntityImportActivity" in prototypes["/platform-entities"]["dataSources"]
    assert "GET /api/platform-entities/readiness-report" in prototypes["/platform-entities"]["dataSources"]
    assert "GET /api/ai-tasks?status=APPROVED&taskType={taskType}" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/platform-entities/contract-validate" in prototypes["/platform-entities"]["dataSources"]
    assert "examples/input/platform-contract.json" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/labs/import-preview" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/labs/import-preview body.coreDbPath" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/labs/mock-import" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/labs/mock-import body.coreDbPath" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/exams/import-preview" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/exams/import-preview body.coreDbPath" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/exams/mock-import" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/exams/mock-import body.coreDbPath" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/grading/import-preview" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/grading/import-preview body.coreDbPath" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/grading/mock-import" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/grading/mock-import body.coreDbPath" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/ppt/import-preview" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/ppt/import-preview body.coreDbPath" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/ppt/mock-import" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/ppt/mock-import body.coreDbPath" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/platform-entities/{id}/import-dry-run" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/platform-entities/{id}/import-dry-run body.contractConfig" in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/platform-entities/{id}/import-send" not in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/platform-entities/{id}/import-status" not in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/platform-entities/{id}/import-result" not in prototypes["/platform-entities"]["dataSources"]
    assert "POST /api/platform-entities/{id}/signoff" not in prototypes["/platform-entities"]["dataSources"]
    assert "future handoff paused: import-send, import-status, import-result, platform signoff, final publish" in prototypes["/platform-entities"]["dataSources"]
    assert "review-center.html?taskId={sourceTaskId}&agentEntityRefresh=1" in prototypes["/platform-entities"]["dataSources"]
    assert pages["/labs/generate"]["safety"]["generatedStatus"] == "WAITING_REVIEW"
    assert pages["/labs/generate"]["prototypePath"] == "frontend/lab-generate.html"
    assert "LabGenerationCloseLoopAction" in pages["/labs/generate"]["components"]
    assert "LabGenerateDataLoader" in pages["/labs/generate"]["components"]
    assert "frontend/lab-generate-data.js" in pages["/labs/generate"]["dataSources"]
    assert "query: coreDbPath, gradingDbPath, agentReport" in pages["/labs/generate"]["dataSources"]
    assert "POST /api/labs/generate.task" in pages["/labs/generate"]["dataSources"]
    assert "POST /api/labs/generate.dsl" in pages["/labs/generate"]["dataSources"]
    assert "POST /api/labs/generate.closeLoopAction" in pages["/labs/generate"]["dataSources"]
    assert "POST /api/labs/generate body.coreDbPath" in pages["/labs/generate"]["dataSources"]
    assert "agent-entities.html?sourceTaskId={taskId}&entityKind=lab" in pages["/labs/generate"]["dataSources"]
    assert (
        "agent-entities.html?sourceTaskId={taskId}&entityKind=lab&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in pages["/labs/generate"]["dataSources"]
    )
    assert pages["/labs/generate"]["safety"]["apiMockGenerationEnabled"] is True
    assert pages["/labs/generate"]["safety"]["realLlmCalled"] is False
    assert pages["/labs/generate"]["safety"]["remoteContentFetched"] is False
    assert pages["/labs/generate"]["safety"]["realPublish"] is False
    assert pages["/labs/generate"]["safety"]["secretVisibleInFrontend"] is False
    lab_generate_deps = {dependency["path"] for dependency in pages["/labs/generate"]["apiDependencies"]}
    assert "/api/materials/analyze" in lab_generate_deps
    assert "/api/labs/generate" in lab_generate_deps
    assert pages["/labs"]["prototypePath"] == "frontend/labs.html"
    assert pages["/labs"]["safety"]["autoPublishAllowed"] is False
    assert pages["/labs"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/labs"]["safety"]["realPublish"] is False
    assert pages["/labs"]["safety"]["realLlmCalled"] is False
    labs_deps = {dependency["path"] for dependency in pages["/labs"]["apiDependencies"]}
    assert labs_deps == {"/api/labs", "/api/review-task-summary", "/api/artifacts"}
    assert pages["/grading/:id/report"]["prototypePath"] == "frontend/grading-report.html"
    assert pages["/grading/:id/report"]["safety"]["sandboxExecuted"] is False
    assert pages["/grading/:id/report"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/grading/:id/report"]["safety"]["unknownShellExecuted"] is False
    assert pages["/grading/:id/report"]["safety"]["commandExecuted"] is False
    assert pages["/grading/:id/report"]["safety"]["realSandboxRunEnabled"] is False
    assert pages["/grading/:id/report"]["safety"]["realPytestRun"] is False
    assert pages["/grading/:id/report"]["safety"]["hostExecutionAllowed"] is False
    assert "ControlledDockerEvidenceDemo" in manifest["components"]
    assert (
        "frontend/mock-data.json.realDemoPrototype.controlledDockerEvidenceDemo"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert (
        "frontend/mock-data.json.realDemoPrototype.controlledDockerEvidenceDemo"
        in prototypes["/real-demo"]["dataSources"]
    )
    assert "examples/output/mimo-real-demo-controlled-plan.json" in prototypes["/real-demo"]["dataSources"]
    assert "examples/output/mimo-real-demo-controlled-sandbox-report.json" in prototypes["/real-demo"]["dataSources"]
    assert "examples/output/grading-sandbox-image-verify.json" in prototypes["/real-demo"]["dataSources"]
    grading_report_deps = {dependency["path"] for dependency in pages["/grading/:id/report"]["apiDependencies"]}
    assert grading_report_deps == {
        "/api/grading/report",
        "/api/grading/result-preview",
        "/api/grading/evidence-readiness",
        "/api/grading/records",
        "/api/audit-events",
        "/api/review-tasks/{id}",
    }
    assert "EvidenceAutoSummary" in pages["/grading/:id/report"]["components"]
    assert "EvidenceAutoExecutionMatrix" in pages["/grading/:id/report"]["components"]
    assert "EvidenceAutoScorePreview" in pages["/grading/:id/report"]["components"]
    assert "ReviewDecisionOutcome" in pages["/grading/:id/report"]["components"]
    assert "GradingResultPreview" in pages["/grading/:id/report"]["components"]
    assert "GradingEvidenceReadiness" in pages["/grading/:id/report"]["components"]
    assert "MergedEvidenceSourceChain" in pages["/grading/:id/report"]["components"]
    assert "ManualReviewActionChecklist" in pages["/grading/:id/report"]["components"]
    assert "frontend/grading-report-data.js" in pages["/grading/:id/report"]["dataSources"]
    assert "GET /api/grading/report?file={file}.report" in pages["/grading/:id/report"]["dataSources"]
    assert "GET /api/grading/report?file={file}.reportDetail" in pages["/grading/:id/report"]["dataSources"]
    assert pages["/ai-tasks"]["prototypePath"] == "frontend/ai-tasks.html"
    assert "AiTaskExecutionWorkspace" in pages["/ai-tasks"]["components"]
    assert {dependency["path"] for dependency in pages["/ai-tasks"]["apiDependencies"]} >= {"/api/grading/records"}
    assert "AiTaskCenterDataLoader" in pages["/ai-tasks"]["components"]
    assert "frontend/ai-tasks-data.js" in pages["/ai-tasks"]["dataSources"]
    assert "GET /api/ai-tasks?status=WAITING_REVIEW" in pages["/ai-tasks"]["dataSources"]
    assert "GET /api/ai-tasks/{id}.taskExecutionWorkspace" in pages["/ai-tasks"]["dataSources"]
    assert "GET /api/ai-tasks/{id}.task" in pages["/ai-tasks"]["dataSources"]
    assert "GET /api/backend/core-tasks?coreDbPath={path}" in pages["/ai-tasks"]["dataSources"]
    assert "GET /api/backend/core-tasks?coreDbPath={path}&status=WAITING_REVIEW" in pages["/ai-tasks"]["dataSources"]
    assert "GET /api/backend/core-tasks/{id}.taskExecutionWorkspace" in pages["/ai-tasks"]["dataSources"]
    assert "GET /api/backend/core-tasks/{id}.task" in pages["/ai-tasks"]["dataSources"]
    assert "GET /api/review-task-summary.taskExecutionWorkspace" in pages["/ai-tasks"]["dataSources"]
    assert pages["/ai-tasks"]["safety"]["autoPublishAllowed"] is False
    assert pages["/ai-tasks"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/ai-tasks"]["safety"]["realAgentStarted"] is False
    assert pages["/ai-tasks"]["safety"]["readOnly"] is True
    assert pages["/ai-tasks"]["safety"]["apiReadonlyEnhancement"] is True
    ai_task_deps = {dependency["path"] for dependency in pages["/ai-tasks"]["apiDependencies"]}
    assert "/api/ai-tasks" in ai_task_deps
    assert "/api/backend/core-tasks" in ai_task_deps
    assert "/api/backend/core-tasks/{id}" in ai_task_deps
    assert "/api/review-task-summary" in ai_task_deps
    assert "/api/review-tasks/{id}.reviewDetail.assessmentPlan.summary" in ai_task_deps
    assert "/api/workflow-runs" in ai_task_deps
    assert pages["/dashboard"]["prototypePath"] == "frontend/dashboard.html"
    assert pages["/dashboard"]["safety"]["autoPublishAllowed"] is False
    assert pages["/dashboard"]["safety"]["realLlmCalled"] is False
    assert pages["/dashboard"]["safety"]["realCloudResourceChanged"] is False
    dashboard_deps = {dependency["path"] for dependency in pages["/dashboard"]["apiDependencies"]}
    assert "/api/health" in dashboard_deps
    assert "/api/review-task-summary" in dashboard_deps
    assert "/api/review-tasks/{id}.reviewDetail.assessmentPlan.summary" in dashboard_deps
    assert "/api/workflow-runs" in dashboard_deps
    assert "/api/artifacts" in dashboard_deps
    assert pages["/console"]["prototypePath"] == "frontend/console.html"
    assert pages["/console"]["safety"]["realAgentStarted"] is False
    assert pages["/console"]["safety"]["realLlmCalled"] is False
    assert pages["/console"]["safety"]["realCloudResourceCreated"] is False
    assert pages["/console"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/console"]["safety"]["sandboxExecuted"] is False
    assert pages["/console"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/console"]["safety"]["unknownShellExecuted"] is False
    assert pages["/console"]["safety"]["autoPublishAllowed"] is False
    assert pages["/console"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/console"]["safety"]["realPublish"] is False
    assert pages["/console"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert pages["/console"]["safety"]["remoteUploadAllowed"] is False
    assert pages["/console"]["safety"]["secretVisibleInFrontend"] is False
    console_deps = {dependency["path"] for dependency in pages["/console"]["apiDependencies"]}
    assert console_deps == {
        "/api/health",
        "/api/review-task-summary",
        "/api/workflow-runs",
        "/api/artifacts",
        "/api/providers",
        "/api/workflow-registry",
    }
    workflow_registry_deps = {dependency["path"] for dependency in pages["/workflows"]["apiDependencies"]}
    assert workflow_registry_deps == {
        "/api/workflow-registry",
        "/api/workflow-registry/{workflowId}",
        "/api/mcp-tool-call-records",
    }
    assert pages["/workflows"]["prototypePath"] == "frontend/workflows.html"
    assert pages["/workflows"]["safety"]["readOnly"] is True
    assert pages["/workflows"]["safety"]["realLlmCalled"] is False
    assert pages["/workflows"]["safety"]["realMcpServerStarted"] is False
    assert pages["/workflows"]["safety"]["realAgentStarted"] is False
    assert pages["/workflows"]["safety"]["workflowExecuted"] is False
    assert pages["/workflows"]["safety"]["taskCreated"] is False
    assert pages["/workflows"]["safety"]["artifactCreated"] is False
    assert pages["/workflows"]["safety"]["autoPublishAllowed"] is False
    assert pages["/workflows"]["safety"]["realPublish"] is False
    assert pages["/workflows"]["safety"]["secretVisibleInFrontend"] is False
    audit_deps = {dependency["path"] for dependency in pages["/audit"]["apiDependencies"]}
    assert audit_deps == {
        "/api/provider-audit-events",
        "/api/mcp-tool-call-records",
        "/api/workflow-runs",
        "/api/audit-events",
        "/api/review-audit-events",
    }
    assert pages["/audit"]["prototypePath"] == "frontend/audit.html"
    assert pages["/audit"]["safety"]["readOnly"] is True
    assert pages["/audit"]["safety"]["realLlmCalled"] is False
    assert pages["/audit"]["safety"]["realMcpServerStarted"] is False
    assert pages["/audit"]["safety"]["realAgentStarted"] is False
    assert pages["/audit"]["safety"]["secretsRead"] is False
    assert pages["/audit"]["safety"]["networkAccess"] is False
    assert pages["/audit"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/audit"]["safety"]["sandboxExecuted"] is False
    assert pages["/audit"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/audit"]["safety"]["autoPublishAllowed"] is False
    assert pages["/audit"]["safety"]["realPublish"] is False
    assert pages["/audit"]["safety"]["secretVisibleInFrontend"] is False
    audit_detail_deps = {dependency["path"] for dependency in pages["/audit/:id"]["apiDependencies"]}
    assert audit_detail_deps == {
        "/api/provider-audit-events",
        "/api/mcp-tool-call-records",
        "/api/workflow-runs/{id}",
        "/api/audit-events",
    }
    assert pages["/audit/:id"]["prototypePath"] == "frontend/audit-detail.html"
    assert pages["/audit/:id"]["safety"]["readOnly"] is True
    assert pages["/audit/:id"]["safety"]["realLlmCalled"] is False
    assert pages["/audit/:id"]["safety"]["realMcpServerStarted"] is False
    assert pages["/audit/:id"]["safety"]["realAgentStarted"] is False
    assert pages["/audit/:id"]["safety"]["secretsRead"] is False
    assert pages["/audit/:id"]["safety"]["networkAccess"] is False
    assert pages["/audit/:id"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/audit/:id"]["safety"]["sandboxExecuted"] is False
    assert pages["/audit/:id"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/audit/:id"]["safety"]["autoPublishAllowed"] is False
    assert pages["/audit/:id"]["safety"]["realPublish"] is False
    assert pages["/audit/:id"]["safety"]["secretVisibleInFrontend"] is False
    audit_incident_deps = {dependency["path"] for dependency in pages["/audit/incidents"]["apiDependencies"]}
    assert audit_incident_deps == {
        "/api/provider-audit-events",
        "/api/mcp-tool-call-records",
        "/api/workflow-runs",
        "/api/audit-events",
    }
    assert pages["/audit/incidents"]["prototypePath"] == "frontend/audit-incidents.html"
    assert pages["/audit/incidents"]["safety"]["readOnly"] is True
    assert pages["/audit/incidents"]["safety"]["autoFixEnabled"] is False
    assert pages["/audit/incidents"]["safety"]["realLlmCalled"] is False
    assert pages["/audit/incidents"]["safety"]["realMcpServerStarted"] is False
    assert pages["/audit/incidents"]["safety"]["realAgentStarted"] is False
    assert pages["/audit/incidents"]["safety"]["secretsRead"] is False
    assert pages["/audit/incidents"]["safety"]["networkAccess"] is False
    assert pages["/audit/incidents"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/audit/incidents"]["safety"]["sandboxExecuted"] is False
    assert pages["/audit/incidents"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/audit/incidents"]["safety"]["autoPublishAllowed"] is False
    assert pages["/audit/incidents"]["safety"]["realPublish"] is False
    assert pages["/audit/incidents"]["safety"]["secretVisibleInFrontend"] is False
    operations_runbook_deps = {dependency["path"] for dependency in pages["/operations/runbook"]["apiDependencies"]}
    assert operations_runbook_deps == {
        "/api/health",
        "/api/provider-audit-events",
        "/api/mcp-tool-call-records",
        "/api/audit-events",
    }
    assert pages["/operations/runbook"]["prototypePath"] == "frontend/operations-runbook.html"
    assert pages["/operations/runbook"]["safety"]["readOnly"] is True
    assert pages["/operations/runbook"]["safety"]["runCommandEnabled"] is False
    assert pages["/operations/runbook"]["safety"]["realLlmCalled"] is False
    assert pages["/operations/runbook"]["safety"]["realMcpServerStarted"] is False
    assert pages["/operations/runbook"]["safety"]["realAgentStarted"] is False
    assert pages["/operations/runbook"]["safety"]["secretsRead"] is False
    assert pages["/operations/runbook"]["safety"]["networkAccess"] is False
    assert pages["/operations/runbook"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/operations/runbook"]["safety"]["sandboxExecuted"] is False
    assert pages["/operations/runbook"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/operations/runbook"]["safety"]["unknownShellExecuted"] is False
    assert pages["/operations/runbook"]["safety"]["autoPublishAllowed"] is False
    assert pages["/operations/runbook"]["safety"]["realPublish"] is False
    assert pages["/operations/runbook"]["safety"]["remoteUploadAllowed"] is False
    assert pages["/operations/runbook"]["safety"]["secretVisibleInFrontend"] is False
    operations_acceptance_deps = {dependency["path"] for dependency in pages["/operations/acceptance"]["apiDependencies"]}
    assert operations_acceptance_deps == {
        "/api/health",
        "/api/workflow-runs",
        "/api/artifacts",
        "/api/audit-events",
    }
    assert pages["/operations/acceptance"]["prototypePath"] == "frontend/operations-acceptance.html"
    assert pages["/operations/acceptance"]["safety"]["readOnly"] is True
    assert pages["/operations/acceptance"]["safety"]["runCommandEnabled"] is False
    assert pages["/operations/acceptance"]["safety"]["uploadPackageEnabled"] is False
    assert pages["/operations/acceptance"]["safety"]["realLlmCalled"] is False
    assert pages["/operations/acceptance"]["safety"]["realMcpServerStarted"] is False
    assert pages["/operations/acceptance"]["safety"]["realAgentStarted"] is False
    assert pages["/operations/acceptance"]["safety"]["secretsRead"] is False
    assert pages["/operations/acceptance"]["safety"]["networkAccess"] is False
    assert pages["/operations/acceptance"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/operations/acceptance"]["safety"]["sandboxExecuted"] is False
    assert pages["/operations/acceptance"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/operations/acceptance"]["safety"]["unknownShellExecuted"] is False
    assert pages["/operations/acceptance"]["safety"]["autoPublishAllowed"] is False
    assert pages["/operations/acceptance"]["safety"]["realPublish"] is False
    assert pages["/operations/acceptance"]["safety"]["remoteUploadAllowed"] is False
    assert pages["/operations/acceptance"]["safety"]["secretVisibleInFrontend"] is False
    operations_demo_map_deps = {dependency["path"] for dependency in pages["/operations/demo-map"]["apiDependencies"]}
    assert operations_demo_map_deps == {
        "/api/health",
        "/api/review-task-summary",
        "/api/workflow-runs",
        "/api/audit-events",
    }
    assert pages["/operations/demo-map"]["prototypePath"] == "frontend/operations-demo-map.html"
    assert pages["/operations/demo-map"]["safety"]["readOnly"] is True
    assert pages["/operations/demo-map"]["safety"]["runCommandEnabled"] is False
    assert pages["/operations/demo-map"]["safety"]["uploadPackageEnabled"] is False
    assert pages["/operations/demo-map"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/operations/demo-map"]["safety"]["realLlmCalled"] is False
    assert pages["/operations/demo-map"]["safety"]["realMcpServerStarted"] is False
    assert pages["/operations/demo-map"]["safety"]["realAgentStarted"] is False
    assert pages["/operations/demo-map"]["safety"]["secretsRead"] is False
    assert pages["/operations/demo-map"]["safety"]["networkAccess"] is False
    assert pages["/operations/demo-map"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/operations/demo-map"]["safety"]["sandboxExecuted"] is False
    assert pages["/operations/demo-map"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/operations/demo-map"]["safety"]["unknownShellExecuted"] is False
    assert pages["/operations/demo-map"]["safety"]["autoPublishAllowed"] is False
    assert pages["/operations/demo-map"]["safety"]["realPublish"] is False
    assert pages["/operations/demo-map"]["safety"]["remoteUploadAllowed"] is False
    assert pages["/operations/demo-map"]["safety"]["secretVisibleInFrontend"] is False
    operations_presenter_deps = {dependency["path"] for dependency in pages["/operations/presenter"]["apiDependencies"]}
    assert operations_presenter_deps == {
        "/api/health",
        "/api/review-task-summary",
        "/api/workflow-runs",
        "/api/artifacts",
        "/api/audit-events",
    }
    assert pages["/operations/presenter"]["prototypePath"] == "frontend/operations-presenter.html"
    assert "CoreBusinessDemoPath" in pages["/operations/presenter"]["components"]
    assert "RealDemoAcceptanceSummary" in pages["/operations/presenter"]["components"]
    assert pages["/operations/signoff"]["prototypePath"] == "frontend/operations-signoff.html"
    assert "CoreBusinessDemoPath" in pages["/operations/signoff"]["components"]
    assert "RealDemoAcceptanceSummary" in pages["/operations/signoff"]["components"]
    signoff_deps = {dependency["path"] for dependency in pages["/operations/signoff"]["apiDependencies"]}
    assert signoff_deps == {
        "/api/health",
        "/api/review-task-summary",
        "/api/workflow-runs",
        "/api/artifacts",
        "/api/audit-events",
    }
    assert pages["/operations/signoff"]["safety"]["readOnly"] is True
    assert pages["/operations/signoff"]["safety"]["realLlmCalled"] is False
    assert pages["/operations/signoff"]["safety"]["realMcpServerStarted"] is False
    assert pages["/operations/signoff"]["safety"]["realAgentStarted"] is False
    assert pages["/operations/signoff"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/operations/signoff"]["safety"]["sandboxExecuted"] is False
    assert pages["/operations/signoff"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/operations/signoff"]["safety"]["unknownShellExecuted"] is False
    assert pages["/operations/signoff"]["safety"]["autoPublishAllowed"] is False
    assert pages["/operations/signoff"]["safety"]["realPublish"] is False
    assert pages["/operations/signoff"]["safety"]["remoteUploadAllowed"] is False
    assert pages["/operations/signoff"]["safety"]["secretVisibleInFrontend"] is False
    assert pages["/operations/signoff"]["safety"]["answerVisibleToCandidate"] is False
    assert pages["/operations/presenter"]["safety"]["readOnly"] is True
    assert pages["/operations/presenter"]["safety"]["runCommandEnabled"] is False
    assert pages["/operations/presenter"]["safety"]["uploadPackageEnabled"] is False
    assert pages["/operations/presenter"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/operations/presenter"]["safety"]["realLlmCalled"] is False
    assert pages["/operations/presenter"]["safety"]["realMcpServerStarted"] is False
    assert pages["/operations/presenter"]["safety"]["realAgentStarted"] is False
    assert pages["/operations/presenter"]["safety"]["secretsRead"] is False
    assert pages["/operations/presenter"]["safety"]["networkAccess"] is False
    assert pages["/operations/presenter"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/operations/presenter"]["safety"]["sandboxExecuted"] is False
    assert pages["/operations/presenter"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/operations/presenter"]["safety"]["unknownShellExecuted"] is False
    assert pages["/operations/presenter"]["safety"]["autoPublishAllowed"] is False
    assert pages["/operations/presenter"]["safety"]["realPublish"] is False
    assert pages["/operations/presenter"]["safety"]["remoteUploadAllowed"] is False
    assert pages["/operations/presenter"]["safety"]["secretVisibleInFrontend"] is False
    assert pages["/operations/presenter"]["safety"]["answerVisibleToCandidate"] is False
    operations_demo_script_deps = {dependency["path"] for dependency in pages["/operations/demo-script"]["apiDependencies"]}
    assert operations_demo_script_deps == {
        "/api/health",
        "/api/review-task-summary",
        "/api/workflow-runs",
        "/api/artifacts",
        "/api/audit-events",
    }
    assert pages["/operations/demo-script"]["prototypePath"] == "frontend/operations-demo-script.html"
    assert pages["/operations/demo-script"]["safety"]["readOnly"] is True
    assert pages["/operations/demo-script"]["safety"]["runCommandEnabled"] is False
    assert pages["/operations/demo-script"]["safety"]["uploadPackageEnabled"] is False
    assert pages["/operations/demo-script"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/operations/demo-script"]["safety"]["realLlmCalled"] is False
    assert pages["/operations/demo-script"]["safety"]["realMcpServerStarted"] is False
    assert pages["/operations/demo-script"]["safety"]["realAgentStarted"] is False
    assert pages["/operations/demo-script"]["safety"]["secretsRead"] is False
    assert pages["/operations/demo-script"]["safety"]["networkAccess"] is False
    assert pages["/operations/demo-script"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/operations/demo-script"]["safety"]["sandboxExecuted"] is False
    assert pages["/operations/demo-script"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/operations/demo-script"]["safety"]["unknownShellExecuted"] is False
    assert pages["/operations/demo-script"]["safety"]["autoPublishAllowed"] is False
    assert pages["/operations/demo-script"]["safety"]["realPublish"] is False
    assert pages["/operations/demo-script"]["safety"]["remoteUploadAllowed"] is False
    assert pages["/operations/demo-script"]["safety"]["secretVisibleInFrontend"] is False
    assert pages["/operations/demo-script"]["safety"]["answerVisibleToCandidate"] is False
    operations_launchpad_deps = {dependency["path"] for dependency in pages["/operations/launchpad"]["apiDependencies"]}
    assert operations_launchpad_deps == {
        "/api/health",
        "/api/workflow-runs",
        "/api/artifacts",
        "/api/audit-events",
    }
    assert pages["/operations/launchpad"]["prototypePath"] == "frontend/operations-launchpad.html"
    assert pages["/operations/launchpad"]["safety"]["readOnly"] is True
    assert pages["/operations/launchpad"]["safety"]["runCommandEnabled"] is False
    assert pages["/operations/launchpad"]["safety"]["uploadPackageEnabled"] is False
    assert pages["/operations/launchpad"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/operations/launchpad"]["safety"]["realLlmCalled"] is False
    assert pages["/operations/launchpad"]["safety"]["realMcpServerStarted"] is False
    assert pages["/operations/launchpad"]["safety"]["realAgentStarted"] is False
    assert pages["/operations/launchpad"]["safety"]["secretsRead"] is False
    assert pages["/operations/launchpad"]["safety"]["networkAccess"] is False
    assert pages["/operations/launchpad"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/operations/launchpad"]["safety"]["sandboxExecuted"] is False
    assert pages["/operations/launchpad"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/operations/launchpad"]["safety"]["unknownShellExecuted"] is False
    assert pages["/operations/launchpad"]["safety"]["autoPublishAllowed"] is False
    assert pages["/operations/launchpad"]["safety"]["realPublish"] is False
    assert pages["/operations/launchpad"]["safety"]["remoteUploadAllowed"] is False
    assert pages["/operations/launchpad"]["safety"]["secretVisibleInFrontend"] is False
    assert pages["/access"]["prototypePath"] == "frontend/access.html"
    assert pages["/access"]["apiDependencies"] == []
    assert pages["/access"]["safety"]["readOnly"] is True
    assert pages["/access"]["safety"]["realHttpServerStarted"] is False
    assert pages["/access"]["safety"]["portListening"] is False
    assert pages["/access"]["safety"]["externalIpBound"] is False
    assert pages["/access"]["safety"]["networkAccess"] is False
    assert pages["/access"]["safety"]["realAgentStarted"] is False
    assert pages["/delivery"]["prototypePath"] == "frontend/delivery.html"
    assert pages["/delivery"]["safety"]["realLlmCalled"] is False
    assert pages["/delivery"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/delivery"]["safety"]["sandboxExecuted"] is False
    assert pages["/delivery"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/delivery"]["safety"]["unknownShellExecuted"] is False
    assert pages["/delivery"]["safety"]["autoPublishAllowed"] is False
    assert pages["/delivery"]["safety"]["realPublish"] is False
    assert pages["/delivery"]["safety"]["remoteUploadAllowed"] is False
    assert pages["/delivery"]["safety"]["secretVisibleInFrontend"] is False
    delivery_deps = {dependency["path"] for dependency in pages["/delivery"]["apiDependencies"]}
    assert delivery_deps == {"/api/health", "/api/workflow-runs", "/api/artifacts"}
    lab_review_deps = {dependency["path"] for dependency in pages["/labs/:id/review"]["apiDependencies"]}
    assert "/api/review-tasks/{id}" in lab_review_deps
    assert "/api/labs/import-preview" in lab_review_deps
    assert "/api/labs/mock-import" in lab_review_deps
    assert pages["/labs/:id/review"]["prototypePath"] == "frontend/lab-review.html"
    assert "ReviewDetailDataLoader" in pages["/labs/:id/review"]["components"]
    assert "ReviewActionDataLoader" in pages["/labs/:id/review"]["components"]
    assert "AgentImportPreviewActionPanel" in pages["/labs/:id/review"]["components"]
    assert "AgentEntityMockImportActionPanel" in pages["/labs/:id/review"]["components"]
    assert "frontend/review-detail-data.js" in pages["/labs/:id/review"]["dataSources"]
    assert "frontend/review-action-data.js" in pages["/labs/:id/review"]["dataSources"]
    assert "frontend/review-import-preview-data.js" in pages["/labs/:id/review"]["dataSources"]
    assert "GET /api/review-tasks/{id}.reviewDetail.reviewPage.dslPreview" in pages["/labs/:id/review"]["dataSources"]
    assert "GET /api/review-tasks/{id}.reviewDetail.reviewPage.timeline" in pages["/labs/:id/review"]["dataSources"]
    assert "POST /api/ai-tasks/{id}/approve" in pages["/labs/:id/review"]["dataSources"]
    assert "POST /api/ai-tasks/{id}/reject" in pages["/labs/:id/review"]["dataSources"]
    assert "POST /api/labs/import-preview" in pages["/labs/:id/review"]["dataSources"]
    assert "POST /api/labs/mock-import" in pages["/labs/:id/review"]["dataSources"]
    assert (
        "agent-entities.html?entityId={id}&sourceTaskId={taskId}&entityKind=lab"
        in pages["/labs/:id/review"]["dataSources"]
    )
    assert pages["/labs/:id/review"]["safety"]["rejectRequiresReason"] is True
    assert pages["/labs/:id/review"]["safety"]["auditTrailRequired"] is True
    assert pages["/labs/:id/review"]["safety"]["autoPublishAllowed"] is False
    assert pages["/labs/:id/review"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/labs/:id/review"]["safety"]["realPublish"] is False
    assert pages["/labs/:id/review"]["safety"]["answerVisibleToCandidate"] is False
    assert pages["/grading"]["prototypePath"] == "frontend/grading.html"
    assert pages["/grading"]["safety"]["sandboxExecuted"] is False
    assert pages["/grading"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/grading"]["safety"]["unknownShellExecuted"] is False
    assert pages["/grading"]["safety"]["realRegradeEnabled"] is False
    assert pages["/grading"]["safety"]["realPublish"] is False
    grading_list_deps = {dependency["path"] for dependency in pages["/grading"]["apiDependencies"]}
    assert grading_list_deps == {
        "/api/grading",
        "/api/grading/run",
        "/api/grading/report",
        "/api/phase2/workflows/grading-generation/run",
        "/api/audit-events",
    }
    assert pages["/grading/:id/review"]["prototypePath"] == "frontend/grading-review.html"
    assert pages["/grading/:id/review"]["safety"]["rejectRequiresReason"] is True
    assert pages["/grading/:id/review"]["safety"]["auditTrailRequired"] is True
    assert pages["/grading/:id/review"]["safety"]["sandboxExecuted"] is False
    assert pages["/grading/:id/review"]["safety"]["contestantCodeExecuted"] is False
    assert pages["/grading/:id/review"]["safety"]["unknownShellExecuted"] is False
    assert pages["/grading/:id/review"]["safety"]["realRegradeEnabled"] is False
    assert pages["/grading/:id/review"]["safety"]["realSandboxRunEnabled"] is False
    assert pages["/grading/:id/review"]["safety"]["autoPublishAllowed"] is False
    assert pages["/grading/:id/review"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/grading/:id/review"]["safety"]["realPublish"] is False
    assert "ReviewDetailDataLoader" in pages["/grading/:id/review"]["components"]
    assert "ReviewActionDataLoader" in pages["/grading/:id/review"]["components"]
    assert "AgentImportPreviewActionPanel" in pages["/grading/:id/review"]["components"]
    assert "AgentEntityMockImportActionPanel" in pages["/grading/:id/review"]["components"]
    assert "frontend/review-detail-data.js" in pages["/grading/:id/review"]["dataSources"]
    assert "frontend/review-action-data.js" in pages["/grading/:id/review"]["dataSources"]
    assert "frontend/review-import-preview-data.js" in pages["/grading/:id/review"]["dataSources"]
    assert "POST /api/grading/import-preview" in pages["/grading/:id/review"]["dataSources"]
    assert "POST /api/grading/mock-import" in pages["/grading/:id/review"]["dataSources"]
    assert (
        "agent-entities.html?entityId={id}&sourceTaskId={taskId}&entityKind=grading"
        in pages["/grading/:id/review"]["dataSources"]
    )
    assert "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan" in pages["/grading/:id/review"]["dataSources"]
    assert (
        "frontend/mock-data.json.gradingReviewPrototype.assessmentPlanManualReviewChecklist"
        in pages["/grading/:id/review"]["dataSources"]
    )
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.assessmentPlan"
        in pages["/grading/:id/review"]["dataSources"]
    )
    grading_review_deps = {dependency["path"] for dependency in pages["/grading/:id/review"]["apiDependencies"]}
    assert grading_review_deps == {
        "/api/review-tasks/{id}",
        "/api/ai-tasks/{id}/approve",
        "/api/ai-tasks/{id}/reject",
        "/api/grading/import-preview",
        "/api/grading/mock-import",
        "/api/audit-events",
    }
    assert "AssessmentPlanManualReviewTrace" in pages["/audit/:id"]["components"]
    assert pages["/exams"]["prototypePath"] == "frontend/exams.html"
    assert pages["/exams"]["safety"]["answerVisibleToCandidate"] is False
    assert pages["/exams"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert pages["/exams"]["safety"]["autoPublishAllowed"] is False
    assert pages["/exams"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/exams"]["safety"]["realPublish"] is False
    assert pages["/exams"]["safety"]["sandboxExecuted"] is False
    exam_list_deps = {dependency["path"] for dependency in pages["/exams"]["apiDependencies"]}
    assert exam_list_deps == {"/api/exams", "/api/review-task-summary", "/api/exams/generate-from-lab"}
    assert pages["/exams/:id/review"]["prototypePath"] == "frontend/exam-review.html"
    assert "ReviewDetailDataLoader" in pages["/exams/:id/review"]["components"]
    assert "ReviewActionDataLoader" in pages["/exams/:id/review"]["components"]
    assert "AgentImportPreviewActionPanel" in pages["/exams/:id/review"]["components"]
    assert "AgentEntityMockImportActionPanel" in pages["/exams/:id/review"]["components"]
    assert "frontend/review-detail-data.js" in pages["/exams/:id/review"]["dataSources"]
    assert "frontend/review-action-data.js" in pages["/exams/:id/review"]["dataSources"]
    assert "frontend/review-import-preview-data.js" in pages["/exams/:id/review"]["dataSources"]
    assert "GET /api/review-tasks/{id}.reviewDetail.reviewPage.dslPreview" in pages["/exams/:id/review"]["dataSources"]
    assert "GET /api/review-tasks/{id}.reviewDetail.reviewPage.timeline" in pages["/exams/:id/review"]["dataSources"]
    assert "POST /api/ai-tasks/{id}/approve" in pages["/exams/:id/review"]["dataSources"]
    assert "POST /api/ai-tasks/{id}/reject" in pages["/exams/:id/review"]["dataSources"]
    assert "POST /api/exams/import-preview" in pages["/exams/:id/review"]["dataSources"]
    assert "POST /api/exams/mock-import" in pages["/exams/:id/review"]["dataSources"]
    assert (
        "agent-entities.html?entityId={id}&sourceTaskId={taskId}&entityKind=exam"
        in pages["/exams/:id/review"]["dataSources"]
    )
    assert pages["/exams/:id/review"]["safety"]["rejectRequiresReason"] is True
    assert pages["/exams/:id/review"]["safety"]["auditTrailRequired"] is True
    assert pages["/exams/:id/review"]["safety"]["answerVisibleToCandidate"] is False
    assert pages["/exams/:id/review"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert pages["/exams/:id/review"]["safety"]["autoPublishAllowed"] is False
    assert pages["/exams/:id/review"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/exams/:id/review"]["safety"]["realSandboxRunEnabled"] is False
    assert pages["/exams/:id/review"]["safety"]["realPublish"] is False
    exam_review_deps = {dependency["path"] for dependency in pages["/exams/:id/review"]["apiDependencies"]}
    assert exam_review_deps == {
        "/api/review-tasks/{id}",
        "/api/ai-tasks/{id}/approve",
        "/api/ai-tasks/{id}/reject",
        "/api/exams/import-preview",
        "/api/exams/mock-import",
    }
    assert pages["/exams/generate"]["safety"]["answerVisibleToCandidate"] is False
    assert pages["/exams/generate"]["prototypePath"] == "frontend/exam-generate.html"
    assert pages["/exams/generate"]["safety"]["generatedStatus"] == "WAITING_REVIEW"
    assert "ExamGenerationCloseLoopAction" in pages["/exams/generate"]["components"]
    assert "ExamGenerateDataLoader" in pages["/exams/generate"]["components"]
    assert "frontend/exam-generate-data.js" in pages["/exams/generate"]["dataSources"]
    assert "query: coreDbPath, gradingDbPath, agentReport" in pages["/exams/generate"]["dataSources"]
    assert "POST /api/exams/generate-from-lab.examDsl" in pages["/exams/generate"]["dataSources"]
    assert "POST /api/exams/generate-from-lab.gradingDsl" in pages["/exams/generate"]["dataSources"]
    assert "POST /api/exams/generate-from-lab.closeLoopAction" in pages["/exams/generate"]["dataSources"]
    assert "POST /api/exams/generate-from-lab body.coreDbPath" in pages["/exams/generate"]["dataSources"]
    assert "agent-entities.html?sourceTaskId={taskId}&entityKind=exam" in pages["/exams/generate"]["dataSources"]
    assert "agent-entities.html?sourceTaskId={taskId}&entityKind=grading" in pages["/exams/generate"]["dataSources"]
    assert (
        "agent-entities.html?sourceTaskId={taskId}&entityKind=exam&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in pages["/exams/generate"]["dataSources"]
    )
    assert (
        "agent-entities.html?sourceTaskId={taskId}&entityKind=grading&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in pages["/exams/generate"]["dataSources"]
    )
    assert pages["/exams/generate"]["safety"]["apiMockGenerationEnabled"] is True
    assert pages["/exams/generate"]["safety"]["autoPublishAllowed"] is False
    assert pages["/exams/generate"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert pages["/exams/generate"]["safety"]["gradingRefVisibleToCandidate"] is False
    assert pages["/exams/generate"]["safety"]["realPublish"] is False
    assert pages["/exams/generate"]["safety"]["secretVisibleInFrontend"] is False
    exam_generate_deps = {dependency["path"] for dependency in pages["/exams/generate"]["apiDependencies"]}
    assert exam_generate_deps == {"/api/exams/generate-from-lab"}
    assert pages["/ppt/generate"]["prototypePath"] == "frontend/ppt-generate.html"
    assert "PptGenerateDataLoader" in pages["/ppt/generate"]["components"]
    assert "frontend/ppt-generate-data.js" in pages["/ppt/generate"]["dataSources"]
    assert pages["/ppt/generate"]["safety"]["generatedStatus"] == "WAITING_REVIEW"
    assert pages["/ppt/generate"]["safety"]["apiMockGenerationEnabled"] is True
    assert pages["/ppt/generate"]["safety"]["frontendDirectRealLlmCall"] is False
    assert pages["/ppt/generate"]["safety"]["secretVisibleInFrontend"] is False
    assert pages["/ppt/generate"]["safety"]["autoPublishAllowed"] is False
    assert pages["/ppt/generate"]["safety"]["realPublish"] is False
    ppt_generate_deps = {dependency["path"] for dependency in pages["/ppt/generate"]["apiDependencies"]}
    assert ppt_generate_deps == {"/api/ppt/generate"}
    assert pages["/ppt"]["prototypePath"] == "frontend/ppt.html"
    assert pages["/ppt"]["safety"]["realLlmCalled"] is False
    assert pages["/ppt"]["safety"]["artifactGenerated"] is False
    assert pages["/ppt"]["safety"]["realPptFileGenerated"] is False
    assert pages["/ppt"]["safety"]["autoPublishAllowed"] is False
    assert pages["/ppt"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/ppt"]["safety"]["realPublish"] is False
    assert pages["/ppt"]["safety"]["secretVisibleInFrontend"] is False
    ppt_deps = {dependency["path"] for dependency in pages["/ppt"]["apiDependencies"]}
    assert ppt_deps == {"/api/ppt", "/api/ppt/generate", "/api/review-task-summary"}
    assert pages["/ppt/:id/review"]["prototypePath"] == "frontend/ppt-review.html"
    assert "ReviewDetailDataLoader" in pages["/ppt/:id/review"]["components"]
    assert "ReviewActionDataLoader" in pages["/ppt/:id/review"]["components"]
    assert "AgentImportPreviewActionPanel" in pages["/ppt/:id/review"]["components"]
    assert "AgentEntityMockImportActionPanel" in pages["/ppt/:id/review"]["components"]
    assert "frontend/review-detail-data.js" in pages["/ppt/:id/review"]["dataSources"]
    assert "frontend/review-action-data.js" in pages["/ppt/:id/review"]["dataSources"]
    assert "frontend/review-import-preview-data.js" in pages["/ppt/:id/review"]["dataSources"]
    assert "GET /api/review-tasks/{id}.reviewDetail.reviewPage.dslPreview" in pages["/ppt/:id/review"]["dataSources"]
    assert "GET /api/review-tasks/{id}.reviewDetail.reviewPage.timeline" in pages["/ppt/:id/review"]["dataSources"]
    assert "POST /api/ai-tasks/{id}/approve" in pages["/ppt/:id/review"]["dataSources"]
    assert "POST /api/ai-tasks/{id}/reject" in pages["/ppt/:id/review"]["dataSources"]
    assert "POST /api/ppt/import-preview" in pages["/ppt/:id/review"]["dataSources"]
    assert "POST /api/ppt/mock-import" in pages["/ppt/:id/review"]["dataSources"]
    assert pages["/ppt/:id/review"]["safety"]["rejectRequiresReason"] is True
    assert pages["/ppt/:id/review"]["safety"]["auditTrailRequired"] is True
    assert pages["/ppt/:id/review"]["safety"]["realLlmCalled"] is False
    assert pages["/ppt/:id/review"]["safety"]["artifactGenerated"] is False
    assert pages["/ppt/:id/review"]["safety"]["realPptFileGenerated"] is False
    assert pages["/ppt/:id/review"]["safety"]["pageReviewUpdateTaskStatusChanged"] is False
    assert pages["/ppt/:id/review"]["safety"]["pageReviewUpdateAutoApproveAllowed"] is False
    assert pages["/ppt/:id/review"]["safety"]["autoPublishAllowed"] is False
    assert pages["/ppt/:id/review"]["safety"]["batchStateChangeAllowed"] is False
    assert pages["/ppt/:id/review"]["safety"]["realPublish"] is False
    assert pages["/ppt/:id/review"]["safety"]["secretVisibleInFrontend"] is False
    ppt_review_deps = {dependency["path"] for dependency in pages["/ppt/:id/review"]["apiDependencies"]}
    assert ppt_review_deps == {
        "/api/review-tasks/{id}",
        "/api/ai-tasks/{id}/approve",
        "/api/ai-tasks/{id}/reject",
        "/api/review-tasks/{id}/ppt-page-review-status",
        "/api/ppt/import-preview",
        "/api/ppt/mock-import",
        "/api/audit-events",
    }
    assert pages["/environments"]["prototypePath"] == "frontend/environments.html"
    assert pages["/environments"]["safety"]["realCloudResourceCreated"] is False
    assert pages["/environments"]["safety"]["realCloudResourceChanged"] is False
    assert pages["/environments"]["safety"]["destroyRealResourceAllowed"] is False
    assert pages["/environments"]["safety"]["sandboxExecuted"] is False
    environment_deps = {dependency["path"] for dependency in pages["/environments"]["apiDependencies"]}
    assert environment_deps == {
        "/api/environments",
        "/api/audit-events",
        "/api/environments/vm",
        "/api/environments/notebook",
    }
    assert pages["/settings/providers"]["safety"]["secretVisibleInFrontend"] is False
    assert pages["/settings/providers"]["safety"]["networkAccess"] is False
    assert pages["/settings/providers"]["prototypePath"] == "frontend/provider-settings.html"
    assert pages["/settings/providers"]["safety"]["secretsRead"] is False
    assert pages["/settings/providers"]["safety"]["realProviderEnabled"] is False
    assert pages["/settings/providers"]["safety"]["apiKeysFromEnvOnly"] is True
    assert pages["/settings/providers"]["safety"]["businessCodeMayEmbedPrompts"] is False
    provider_deps = {dependency["path"] for dependency in pages["/settings/providers"]["apiDependencies"]}
    assert provider_deps == {"/api/providers", "/api/providers/mock/health"}
    assert pages["/skills"]["prototypePath"] == "frontend/skills.html"
    assert pages["/skills"]["safety"]["realAgentStarted"] is False
    assert pages["/skills"]["safety"]["realLlmCalled"] is False
    assert pages["/skills"]["safety"]["businessCodeMayEmbedPrompts"] is False
    assert pages["/skills"]["safety"]["autoPublishAllowed"] is False


def test_frontend_mock_data_avoids_real_execution_and_publish():
    mock_data = load_json("frontend/mock-data.json")

    assert mock_data["mode"] == "MOCK_ONLY"
    assert mock_data["reviewActions"]["publish"]["enabled"] is False
    assert mock_data["reviewActions"]["publish"]["blockedUntilApproved"] is True
    assert mock_data["reviewTaskSummary"]["mode"] == "MOCK_ONLY"
    assert mock_data["reviewTaskSummary"]["queueSummary"]["reviewRequired"] is True
    assert mock_data["reviewTaskSummary"]["batchActionPolicy"]["batchApproveAllowed"] is False
    assert mock_data["reviewTaskSummary"]["batchActionPolicy"]["batchRejectAllowed"] is False
    assert mock_data["reviewTaskSummary"]["batchActionPolicy"]["batchPublishAllowed"] is False
    assert mock_data["reviewTaskSummary"]["safety"]["realPublish"] is False
    assert mock_data["reviewTaskSummary"]["items"][0]["reviewPageSummary"]["actionBar"]["mockPublish"]["enabled"] is False
    assert mock_data["reviewTaskSummary"]["highRiskMcpIntentSummary"]["waitingReviewTotal"] == 1
    assert mock_data["reviewTaskSummary"]["highRiskMcpIntentSummary"]["approvedIntentTotal"] == 2
    assert mock_data["reviewTaskSummary"]["highRiskMcpIntentSummary"]["approvedExecutionBlockedTotal"] == 1
    assert mock_data["reviewTaskSummary"]["highRiskMcpIntentSummary"]["approvedPendingSecondConfirmationTotal"] == 1
    assert mock_data["reviewTaskSummary"]["highRiskMcpIntentSummary"]["secondConfirmationPendingTotal"] == 1
    assert mock_data["reviewTaskSummary"]["highRiskMcpIntentSummary"]["secondConfirmationSatisfiedTotal"] == 0
    assert set(mock_data["reviewTaskSummary"]["highRiskMcpIntentSummary"]["postReviewDispositionStates"]) == {
        "WAITING_HUMAN_REVIEW",
        "APPROVED_EXECUTION_BLOCKED",
        "APPROVED_PENDING_SECOND_CONFIRMATION",
    }
    assert mock_data["reviewTaskSummary"]["highRiskMcpIntentSummary"]["reviewIntentOnly"] is True
    assert mock_data["reviewTaskSummary"]["highRiskMcpIntentSummary"]["executeRealPublishEnabled"] is False
    assert mock_data["reviewTaskSummary"]["highRiskMcpIntentSummary"]["destroyRealEnvironmentEnabled"] is False
    assert mock_data["reviewTaskSummary"]["highRiskMcpIntentSummary"]["environmentDestroyedTotal"] == 0
    assert mock_data["reviewCenterPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["reviewCenterPrototype"]["actionPolicy"]["batchApproveEnabled"] is False
    assert mock_data["reviewCenterPrototype"]["actionPolicy"]["batchRejectEnabled"] is False
    assert mock_data["reviewCenterPrototype"]["actionPolicy"]["batchPublishEnabled"] is False
    assert mock_data["reviewCenterPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["reviewCenterPrototype"]["actionPolicy"]["executeRealPublishEnabled"] is False
    assert mock_data["reviewCenterPrototype"]["actionPolicy"]["destroyRealEnvironmentEnabled"] is False
    assert mock_data["reviewCenterPrototype"]["highRiskIntentPanel"]["reviewIntentOnly"] is True
    assert mock_data["reviewCenterPrototype"]["highRiskIntentPanel"]["approvedExecutionBlockedTotal"] == 1
    assert mock_data["reviewCenterPrototype"]["highRiskIntentPanel"]["approvedPendingSecondConfirmationTotal"] == 1
    assert mock_data["reviewCenterPrototype"]["highRiskIntentPanel"]["secondConfirmationSatisfiedTotal"] == 0
    assert mock_data["reviewCenterPrototype"]["highRiskIntentPanel"]["secondConfirmationStatusTool"] == "get_second_confirmation_status"
    assert mock_data["reviewCenterPrototype"]["highRiskIntentPanel"]["secondConfirmationStatusReadOnly"] is True
    assert mock_data["reviewCenterPrototype"]["highRiskIntentPanel"]["confirmationActionAvailable"] is False
    assert mock_data["reviewCenterPrototype"]["highRiskIntentPanel"]["confirmationEndpointEnabled"] is False
    assert set(mock_data["reviewCenterPrototype"]["highRiskIntentPanel"]["postReviewDispositionStates"]) == {
        "WAITING_HUMAN_REVIEW",
        "APPROVED_EXECUTION_BLOCKED",
        "APPROVED_PENDING_SECOND_CONFIRMATION",
    }
    assert mock_data["reviewCenterPrototype"]["qualitySignalQueueSummary"]["enabled"] is True
    assert (
        mock_data["reviewCenterPrototype"]["qualitySignalQueueSummary"]["source"]
        == "examReviewPrototype.qualitySignals + gradingReviewPrototype.qualitySignals"
    )
    assert mock_data["reviewCenterPrototype"]["qualitySignalQueueSummary"]["visibleForTaskTypes"] == [
        "EXAM_GENERATION",
        "GRADING_GENERATION",
    ]
    assert mock_data["reviewCenterPrototype"]["qualitySignalQueueSummary"]["matchedCoverageTotal"] == 4
    assert mock_data["reviewCenterPrototype"]["qualitySignalQueueSummary"]["explainablePlanTotal"] == 2
    assert mock_data["reviewCenterPrototype"]["qualitySignalQueueSummary"]["candidateSafeExamPreviewTotal"] == 1
    queue_signals = {
        signal["taskId"]: signal
        for signal in mock_data["reviewCenterPrototype"]["qualitySignalQueueSummary"]["signals"]
    }
    assert queue_signals["task_exam_demo"]["candidateSafeExamPreviewAnswersRemoved"] is True
    assert queue_signals["task_exam_demo"]["questionGradingRefCoverageStatus"] == "MATCHED"
    assert queue_signals["task_exam_demo"]["scoreCoverageStatus"] == "MATCHED"
    assert queue_signals["task_exam_demo"]["explainabilityStatus"] == "EXPLAINABLE"
    assert queue_signals["task_exam_demo"]["assessmentPlanAlignedWithChecks"] is True
    assert queue_signals["task_grading_demo"]["gradingRefCoverageStatus"] == "MATCHED"
    assert queue_signals["task_grading_demo"]["scoreCoverageStatus"] == "MATCHED"
    assert queue_signals["task_grading_demo"]["explainabilityStatus"] == "EXPLAINABLE"
    assert queue_signals["task_grading_demo"]["assessmentPlanAlignedWithChecks"] is True
    assert queue_signals["task_grading_demo"]["mockEvidenceStatus"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    priority_queue = mock_data["reviewCenterPrototype"]["reviewPriorityQueue"]
    assert priority_queue["enabled"] is True
    assert (
        priority_queue["source"]
        == "reviewTaskSummary.items + reviewDetail.qualitySignals + reviewDetail.assessmentPlan + reviewDetail.assessmentPlan.manualReviewChecklist"
    )
    assert priority_queue["sortPolicy"] == [
        "riskLevel=high",
        "mockEvidenceStatus=MOCK_EVIDENCE_NOT_COLLECTED",
        "manualReviewChecklist.status=NEEDS_HUMAN_REVIEW",
        "candidateSafeExamPreview.answersRemoved=true",
        "qualitySignalStatus=NEEDS_REVIEW",
        "taskTypePriority=GRADING_GENERATION/EXAM_GENERATION/LAB_GENERATION/PPT_GENERATION",
    ]
    assert priority_queue["summary"]["queueTotal"] == 3
    assert priority_queue["summary"]["urgentTotal"] == 1
    assert priority_queue["summary"]["highTotal"] == 1
    assert priority_queue["summary"]["normalTotal"] == 1
    assert priority_queue["summary"]["manualReviewChecklistTaskTotal"] == 1
    assert priority_queue["summary"]["manualReviewChecklistNeedsHumanReviewTotal"] == 5
    assert priority_queue["summary"]["autoApproveAllowed"] is False
    assert priority_queue["summary"]["batchStateChangeAllowed"] is False
    assert [item["taskId"] for item in priority_queue["items"]] == [
        "task_grading_demo",
        "task_exam_demo",
        "task_lab_demo",
    ]
    assert [item["priority"] for item in priority_queue["items"]] == ["URGENT", "HIGH", "NORMAL"]
    assert priority_queue["items"][0]["reasonCode"] == "HIGH_RISK_MOCK_EVIDENCE_REQUIRED"
    assert priority_queue["items"][0]["mockEvidenceStatus"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    checklist_summary = priority_queue["items"][0]["manualReviewChecklistSummary"]
    assert checklist_summary["enabled"] is True
    assert checklist_summary["source"] == "reviewDetail.assessmentPlan.manualReviewChecklist"
    assert checklist_summary["checklistTotal"] == 5
    assert checklist_summary["matchedTotal"] == 5
    assert checklist_summary["needsHumanReviewTotal"] == 5
    assert checklist_summary["nextReviewChecklistIds"] == [
        "verify_assessment_plan_aligned_with_checks",
        "confirm_mock_evidence_not_collected",
        "confirm_real_sandbox_evidence_required_before_real_execution",
        "verify_required_limits_present",
        "confirm_no_execution_or_publish",
    ]
    assert checklist_summary["operatorDecision"]["autoApproveAllowed"] is False
    assert checklist_summary["operatorDecision"]["batchStateChangeAllowed"] is False
    assert checklist_summary["operatorDecision"]["realSandboxRunEnabled"] is False
    assert checklist_summary["operatorDecision"]["realPublishAllowed"] is False
    assert priority_queue["items"][1]["reasonCode"] == "CANDIDATE_SAFE_EXAM_PREVIEW"
    assert priority_queue["items"][1]["candidateSafeExamPreviewAnswersRemoved"] is True
    assert priority_queue["items"][1]["manualReviewChecklistSummary"]["enabled"] is False
    assert priority_queue["items"][2]["reasonCode"] == "LAB_QUALITY_NEEDS_REVIEW"
    assert priority_queue["items"][2]["qualitySignalStatus"] == "NEEDS_REVIEW"
    assert priority_queue["items"][2]["manualReviewChecklistSummary"]["enabled"] is False
    next_action = mock_data["reviewCenterPrototype"]["nextManualReviewAction"]
    assert next_action["enabled"] is True
    assert next_action["source"] == "reviewCenterPrototype.reviewPriorityQueue.items[0]"
    assert next_action["taskId"] == "task_grading_demo"
    assert next_action["taskType"] == "GRADING_GENERATION"
    assert next_action["priority"] == "URGENT"
    assert next_action["reasonCode"] == "HIGH_RISK_MOCK_EVIDENCE_REQUIRED"
    assert next_action["entryRoute"] == "/review-center?taskId=task_grading_demo"
    assert next_action["entryApi"] == "GET /api/review-tasks/{id}"
    assert (
        next_action["checklistSource"]
        == "reviewCenterPrototype.reviewPriorityQueue.items[0].manualReviewChecklistSummary"
    )
    assert next_action["primaryReviewFocus"] == "review_assessment_plan_before_approval"
    assert next_action["checklistTotal"] == 5
    assert next_action["needsHumanReviewTotal"] == 5
    assert next_action["requiredEvidence"] == [
        "reviewDetail.assessmentPlan.summary",
        "gradingReviewPrototype.assessmentPlanSummary",
        "mockEvidence.status=MOCK_EVIDENCE_NOT_COLLECTED",
    ]
    assert next_action["operatorChecklist"] == [
        "open_task_grading_demo_review_detail",
        "verify_assessment_plan_aligned_with_checks",
        "confirm_mock_evidence_not_collected",
        "confirm_real_sandbox_evidence_required_before_real_execution",
        "verify_required_limits_present",
        "confirm_no_execution_or_publish",
    ]
    assert next_action["autoApproveAllowed"] is False
    assert next_action["batchStateChangeAllowed"] is False
    assert next_action["realPublishAllowed"] is False
    assert mock_data["reviewCenterPrototype"]["actionPolicy"]["viewSecondConfirmationStatusEnabled"] is True
    assert mock_data["reviewCenterPrototype"]["actionPolicy"]["confirmSecondFactorEnabled"] is False
    assert mock_data["reviewCenterPrototype"]["actionPolicy"]["confirmationEndpointEnabled"] is False
    assert mock_data["reviewCenterPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["reviewCenterPrototype"]["safety"]["secondConfirmationStatusReadOnly"] is True
    assert mock_data["reviewCenterPrototype"]["safety"]["confirmationEndpointEnabled"] is False
    assert mock_data["reviewCenterPrototype"]["safety"]["highRiskIntentExecutionAllowed"] is False
    assert mock_data["reviewCenterPrototype"]["safety"]["environmentDestroyed"] is False
    assert mock_data["reviewCenterPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["labsPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["labsPrototype"]["summary"]["labTotal"] == len(mock_data["labs"])
    assert mock_data["labsPrototype"]["summary"]["waitingReviewTotal"] == 1
    assert mock_data["labsPrototype"]["summary"]["approvedTotal"] == 1
    assert mock_data["labsPrototype"]["summary"]["publishedTotal"] == 0
    assert mock_data["labsPrototype"]["summary"]["reviewRequired"] is True
    assert mock_data["labsPrototype"]["summary"]["publishBlockedUntilApproved"] is True
    assert mock_data["labsPrototype"]["actionPolicy"]["openGenerateEnabled"] is True
    assert mock_data["labsPrototype"]["actionPolicy"]["openReviewDetailEnabled"] is True
    assert mock_data["labsPrototype"]["actionPolicy"]["viewDslPreviewEnabled"] is True
    assert mock_data["labsPrototype"]["actionPolicy"]["batchApproveEnabled"] is False
    assert mock_data["labsPrototype"]["actionPolicy"]["batchRejectEnabled"] is False
    assert mock_data["labsPrototype"]["actionPolicy"]["batchPublishEnabled"] is False
    assert mock_data["labsPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["labsPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["labsPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["labsPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["labsPrototype"]["safety"]["batchStateChangeAllowed"] is False
    assert mock_data["labsPrototype"]["safety"]["realPublish"] is False
    assert mock_data["labsPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert [lab["id"] for lab in mock_data["labs"]] == ["lab_demo", "lab_reviewed_demo"]
    assert [lab["id"] for lab in mock_data["labs"] if lab["status"] == "WAITING_REVIEW"] == ["lab_demo"]
    assert all(lab["mode"] == "MOCK_ONLY" for lab in mock_data["labs"])
    assert all(lab["autoPublishAllowed"] is False and lab["realPublish"] is False for lab in mock_data["labs"])
    assert mock_data["pptPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["pptPrototype"]["summary"]["pptTotal"] == len(mock_data["ppts"])
    assert mock_data["pptPrototype"]["summary"]["waitingReviewTotal"] == 1
    assert mock_data["pptPrototype"]["summary"]["approvedTotal"] == 1
    assert mock_data["pptPrototype"]["summary"]["slideTotal"] == sum(ppt["slideCount"] for ppt in mock_data["ppts"])
    assert mock_data["pptPrototype"]["summary"]["artifactGenerated"] is False
    assert mock_data["pptPrototype"]["summary"]["realPptFileGenerated"] is False
    assert mock_data["pptPrototype"]["summary"]["reviewRequired"] is True
    assert mock_data["pptPrototype"]["actionPolicy"]["openGenerateEnabled"] is True
    assert mock_data["pptPrototype"]["actionPolicy"]["openReviewDetailEnabled"] is True
    assert mock_data["pptPrototype"]["actionPolicy"]["viewPptDslPreviewEnabled"] is True
    assert mock_data["pptPrototype"]["actionPolicy"]["generateMockDslEnabled"] is True
    assert mock_data["pptPrototype"]["actionPolicy"]["generateRealPptFileEnabled"] is False
    assert mock_data["pptPrototype"]["actionPolicy"]["batchApproveEnabled"] is False
    assert mock_data["pptPrototype"]["actionPolicy"]["batchRejectEnabled"] is False
    assert mock_data["pptPrototype"]["actionPolicy"]["batchPublishEnabled"] is False
    assert mock_data["pptPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["pptPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["pptPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["pptPrototype"]["safety"]["artifactGenerated"] is False
    assert mock_data["pptPrototype"]["safety"]["realPptFileGenerated"] is False
    assert mock_data["pptPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["pptPrototype"]["safety"]["batchStateChangeAllowed"] is False
    assert mock_data["pptPrototype"]["safety"]["realPublish"] is False
    assert mock_data["pptPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert [ppt["id"] for ppt in mock_data["ppts"]] == ["ppt_demo", "ppt_reviewed_demo"]
    assert [ppt["id"] for ppt in mock_data["ppts"] if ppt["status"] == "WAITING_REVIEW"] == ["ppt_demo"]
    assert all(ppt["mode"] == "MOCK_ONLY" for ppt in mock_data["ppts"])
    assert all(
        ppt["artifactGenerated"] is False
        and ppt["realPptFileGenerated"] is False
        and ppt["autoPublishAllowed"] is False
        and ppt["realPublish"] is False
        for ppt in mock_data["ppts"]
    )
    assert mock_data["pptReviewPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["pptReviewPrototype"]["input"]["taskId"] == "task_ppt_demo"
    assert mock_data["pptReviewPrototype"]["input"]["pptId"] == "ppt_demo"
    assert mock_data["pptReviewPrototype"]["input"]["detailApi"] == "GET /api/review-tasks/{id}"
    assert mock_data["pptReviewPrototype"]["input"]["approveApi"] == "POST /api/ai-tasks/{id}/approve"
    assert mock_data["pptReviewPrototype"]["input"]["rejectApi"] == "POST /api/ai-tasks/{id}/reject"
    assert mock_data["pptReviewPrototype"]["input"]["auditApi"] == "GET /api/audit-events"
    assert mock_data["pptReviewPrototype"]["summary"]["taskType"] == "PPT_GENERATION"
    assert mock_data["pptReviewPrototype"]["summary"]["taskStatus"] == "WAITING_REVIEW"
    assert mock_data["pptReviewPrototype"]["summary"]["artifactTotal"] == 1
    assert mock_data["pptReviewPrototype"]["summary"]["workflowStepTotal"] == 3
    assert mock_data["pptReviewPrototype"]["summary"]["slideTotal"] == 2
    assert mock_data["pptReviewPrototype"]["summary"]["artifactGenerated"] is False
    assert mock_data["pptReviewPrototype"]["summary"]["realPptFileGenerated"] is False
    assert mock_data["pptReviewPrototype"]["summary"]["pptxArtifactGenerated"] is True
    assert mock_data["pptReviewPrototype"]["summary"]["reviewRequired"] is True
    assert mock_data["pptReviewPrototype"]["summary"]["publishBlockedUntilApproved"] is True
    assert mock_data["pptReviewPrototype"]["dslPreview"]["pptDslPath"] == mock_data["dslPreviews"]["ppt"]["path"]
    assert mock_data["pptReviewPrototype"]["dslPreview"]["slideCount"] == 2
    assert mock_data["pptReviewPrototype"]["dslPreview"]["artifactGenerated"] is False
    assert mock_data["pptReviewPrototype"]["dslPreview"]["realPptFileGenerated"] is False
    assert mock_data["pptReviewPrototype"]["dslPreview"]["pptxArtifactGenerated"] is True
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["kind"] == "PPTX_FILE"
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["status"] == "WAITING_REVIEW"
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["path"].endswith("real-llm-demo-ppt-artifact.pptx")
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["manifestPath"].endswith("real-llm-demo-ppt-artifact-manifest.json")
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["slideCount"] == 5
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["bytes"] > 0
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["previewAvailable"] is True
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["renderAttempted"] is True
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["preview"]["reason"] == "PREVIEW_RENDERED"
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["firstSlidePreview"]["title"] == "AI 工具应用课程"
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["firstSlidePreview"]["imagePath"].endswith("real-llm-demo-ppt-artifact-slide-01.png")
    assert len(mock_data["pptReviewPrototype"]["pptxArtifact"]["slidePreviews"]) == 5
    page_review = mock_data["pptReviewPrototype"]["pptxArtifact"]["pageReviewSummary"]
    slide_reviews = mock_data["pptReviewPrototype"]["pptxArtifact"]["slidePreviews"]
    assert page_review["status"] == "NEEDS_REVIEW"
    assert page_review["total"] == 5
    assert page_review["approved"] == 2
    assert page_review["needsReview"] == 2
    assert page_review["reviseRequired"] == 1
    assert page_review["manualCommentTotal"] == 3
    assert page_review["qaSignalStatus"] == "NEEDS_REVIEW"
    assert page_review["autoApproveAllowed"] is False
    assert page_review["realPublishAllowed"] is False
    assert {slide["reviewStatus"] for slide in slide_reviews} == {"APPROVED", "NEEDS_REVIEW", "REVISE_REQUIRED"}
    assert sum(1 for slide in slide_reviews if slide["manualComment"]["required"]) == 3
    assert all("reviewFocus" in slide["qaSignals"] for slide in slide_reviews)
    assert any(slide["qaSignals"]["layout"] == "NEEDS_REVIEW" for slide in slide_reviews)
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["contactSheet"]["path"].endswith("real-llm-demo-ppt-artifact-contact-sheet.png")
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["contactSheet"]["slideCount"] == 5
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["autoPublishAllowed"] is False
    assert mock_data["pptReviewPrototype"]["pptxArtifact"]["realPublish"] is False
    page_update = mock_data["pptReviewPrototype"]["pageReviewUpdateAction"]
    assert page_update["component"] == "PptPageReviewUpdateAction"
    assert page_update["taskId"] == "task_ppt_demo"
    assert page_update["artifactKind"] == "PPTX_FILE"
    assert page_update["api"] == "POST /api/review-tasks/{id}/ppt-page-review-status"
    assert "python lab_cli.py review ppt-page-update" in page_update["cli"]
    assert page_update["targetSlideIndex"] == 4
    assert page_update["allowedReviewStatuses"] == ["APPROVED", "NEEDS_REVIEW", "REVISE_REQUIRED"]
    assert page_update["targetReviewStatus"] == "REVISE_REQUIRED"
    assert page_update["reviewerRequired"] is True
    assert page_update["reviseRequiresComment"] is True
    assert page_update["writesOperationAudit"] is True
    assert page_update["operationAuditAction"] == "PPT_PAGE_REVIEW_UPDATE"
    assert page_update["returnsPageReviewSummary"] is True
    assert page_update["taskStatusChanged"] is False
    assert page_update["artifactStatusChanged"] is False
    assert page_update["autoApproveAllowed"] is False
    assert page_update["autoPublishAllowed"] is False
    assert page_update["realPublishAllowed"] is False
    assert len(mock_data["pptReviewPrototype"]["slidePlan"]["slides"]) == 2
    assert mock_data["pptReviewPrototype"]["slidePlan"]["artifactGenerated"] is False
    assert mock_data["pptReviewPrototype"]["slidePlan"]["realPptFileGenerated"] is False
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["singleApproveEnabled"] is True
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["singleRejectEnabled"] is True
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["singleRejectRequiresReason"] is True
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["pageReviewUpdateEnabled"] is True
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["viewPptDslEnabled"] is True
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["viewSlidePlanEnabled"] is True
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["viewPptxArtifactEnabled"] is True
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["viewAuditEventsEnabled"] is True
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["mockPublishEnabled"] is False
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["generateRealPptFileEnabled"] is False
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["batchApproveEnabled"] is False
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["batchRejectEnabled"] is False
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["batchPublishEnabled"] is False
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["pptReviewPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["pptReviewPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["pptReviewPrototype"]["safety"]["artifactGenerated"] is False
    assert mock_data["pptReviewPrototype"]["safety"]["realPptFileGenerated"] is False
    assert mock_data["pptReviewPrototype"]["safety"]["pptxArtifactGenerated"] is True
    assert mock_data["pptReviewPrototype"]["safety"]["pptxArtifactAutoPublishAllowed"] is False
    assert mock_data["pptReviewPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["pptReviewPrototype"]["safety"]["batchStateChangeAllowed"] is False
    assert mock_data["pptReviewPrototype"]["safety"]["realPublish"] is False
    assert mock_data["pptReviewPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["labGeneratePrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["labGeneratePrototype"]["input"]["remoteContentFetched"] is False
    assert mock_data["labGeneratePrototype"]["input"]["unknownShellExecuted"] is False
    assert mock_data["labGeneratePrototype"]["promptSelection"]["promptPath"].startswith("prompts/")
    assert mock_data["labGeneratePrototype"]["promptSelection"]["promptEditableInBusinessCode"] is False
    assert mock_data["labGeneratePrototype"]["output"]["taskStatus"] == "WAITING_REVIEW"
    assert mock_data["labGeneratePrototype"]["output"]["reviewRequired"] is True
    assert mock_data["labGeneratePrototype"]["output"]["publishBlockedUntilApproved"] is True
    assert mock_data["labGeneratePrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["labGeneratePrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["labGeneratePrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["labGeneratePrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["labReviewPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["labReviewPrototype"]["input"]["taskId"] == "task_lab_demo"
    assert mock_data["labReviewPrototype"]["input"]["detailApi"] == "GET /api/review-tasks/{id}"
    assert mock_data["labReviewPrototype"]["input"]["approveApi"] == "POST /api/ai-tasks/{id}/approve"
    assert mock_data["labReviewPrototype"]["input"]["rejectApi"] == "POST /api/ai-tasks/{id}/reject"
    assert mock_data["labReviewPrototype"]["summary"]["taskType"] == "LAB_GENERATION"
    assert mock_data["labReviewPrototype"]["summary"]["taskStatus"] == "WAITING_REVIEW"
    assert mock_data["labReviewPrototype"]["summary"]["artifactTotal"] == mock_data["reviewDetail"]["summary"]["artifactTotal"]
    assert mock_data["labReviewPrototype"]["summary"]["workflowStepTotal"] == mock_data["reviewDetail"]["summary"]["workflowStepTotal"]
    assert mock_data["labReviewPrototype"]["summary"]["riskCount"] == mock_data["reviewDetail"]["reviewPage"]["riskSummary"]["riskCount"]
    assert mock_data["labReviewPrototype"]["summary"]["qualitySignalStatus"] == "NEEDS_REVIEW"
    assert mock_data["labReviewPrototype"]["summary"]["providerSummaryVisible"] is True
    assert mock_data["labReviewPrototype"]["summary"]["providerQualitySummaryVisible"] is True
    assert mock_data["labReviewPrototype"]["summary"]["providerReadyForReview"] is True
    assert mock_data["labReviewPrototype"]["summary"]["providerNormalizationPatchCount"] == 1
    assert mock_data["labReviewPrototype"]["summary"]["reviewRequired"] is True
    assert mock_data["labReviewPrototype"]["summary"]["publishBlockedUntilApproved"] is True
    assert mock_data["labReviewPrototype"]["generationProfile"]["available"] is True
    assert mock_data["labReviewPrototype"]["generationProfile"]["context"]["targetUsers"] == ["高职学生", "教师"]
    assert mock_data["labReviewPrototype"]["generationProfile"]["context"]["durationMinutes"] == 90
    assert mock_data["labReviewPrototype"]["qualitySignals"]["lab"]["matching"]["status"] == "NEEDS_REVIEW"
    assert mock_data["labReviewPrototype"]["qualitySignals"]["lab"]["matching"]["durationMinutes"]["matched"] is False
    assert mock_data["labReviewPrototype"]["qualitySignals"]["lab"]["matching"]["stepGranularity"]["matched"] is True
    assert mock_data["labReviewPrototype"]["qualitySignals"]["materialCoverage"]["status"] == "LINKED"
    assert mock_data["labReviewPrototype"]["qualitySignals"]["materialCoverage"]["sourceReferencedInDsl"] is True
    assert mock_data["labReviewPrototype"]["providerSummary"] == mock_data["reviewDetail"]["reviewPage"]["providerSummary"]
    assert mock_data["labReviewPrototype"]["providerSummary"]["realLlmCalled"] is True
    assert mock_data["labReviewPrototype"]["providerSummary"]["providerAdapters"] == ["openai_responses_sdk_adapter"]
    provider_quality = mock_data["labReviewPrototype"]["providerSummary"]["qualitySummary"]
    assert provider_quality["readyForReview"] is True
    assert provider_quality["normalizationPatchCount"] == 1
    assert provider_quality["normalizationPatches"] == ["set.metadata.category"]
    assert mock_data["labReviewPrototype"]["providerSummary"]["calls"][0]["qualitySummary"] == provider_quality
    assert mock_data["reviewDetail"]["providerCallAuditEvents"][0]["detail"]["qualitySummary"] == provider_quality
    assert mock_data["labReviewPrototype"]["actionPolicy"]["singleApproveEnabled"] is True
    assert mock_data["labReviewPrototype"]["actionPolicy"]["singleRejectEnabled"] is True
    assert mock_data["labReviewPrototype"]["actionPolicy"]["singleRejectRequiresReason"] is True
    assert mock_data["labReviewPrototype"]["actionPolicy"]["mockPublishEnabled"] is False
    assert mock_data["labReviewPrototype"]["actionPolicy"]["batchApproveEnabled"] is False
    assert mock_data["labReviewPrototype"]["actionPolicy"]["batchRejectEnabled"] is False
    assert mock_data["labReviewPrototype"]["actionPolicy"]["batchPublishEnabled"] is False
    assert mock_data["labReviewPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["labReviewPrototype"]["safety"]["realLlmCalled"] is True
    assert mock_data["labReviewPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["labReviewPrototype"]["safety"]["batchStateChangeAllowed"] is False
    assert mock_data["labReviewPrototype"]["safety"]["realPublish"] is False
    assert mock_data["labReviewPrototype"]["safety"]["answerVisibleToCandidate"] is False
    assert mock_data["examGeneratePrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["examGeneratePrototype"]["input"]["labId"] == "lab_demo"
    assert mock_data["examGeneratePrototype"]["promptSelection"]["examPromptPath"].startswith("prompts/")
    assert mock_data["examGeneratePrototype"]["promptSelection"]["gradingPromptPath"].startswith("prompts/")
    assert mock_data["examGeneratePrototype"]["promptSelection"]["promptEditableInBusinessCode"] is False
    assert mock_data["examGeneratePrototype"]["output"]["taskStatus"] == "WAITING_REVIEW"
    assert mock_data["examGeneratePrototype"]["output"]["examDslPath"] == mock_data["dslPreviews"]["exam"]["path"]
    assert mock_data["examGeneratePrototype"]["output"]["gradingDslPath"] == mock_data["dslPreviews"]["grading"]["path"]
    assert mock_data["examGeneratePrototype"]["output"]["answerVisibleToCandidate"] is False
    assert mock_data["examGeneratePrototype"]["output"]["candidatePreviewAnswer"] == "[REDACTED_FOR_CANDIDATE]"
    assert mock_data["examGeneratePrototype"]["actionPolicy"]["showStandardAnswerEnabled"] is False
    assert mock_data["examGeneratePrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["examGeneratePrototype"]["actionPolicy"]["realSandboxRunEnabled"] is False
    assert mock_data["examGeneratePrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["examGeneratePrototype"]["safety"]["answerVisibleToCandidate"] is False
    assert mock_data["examGeneratePrototype"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert mock_data["examGeneratePrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["examsPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["examsPrototype"]["summary"]["examTotal"] == len(mock_data["exams"])
    assert mock_data["examsPrototype"]["summary"]["waitingReviewTotal"] == 1
    assert mock_data["examsPrototype"]["summary"]["approvedTotal"] == 1
    assert mock_data["examsPrototype"]["summary"]["gradingDslTotal"] == len(mock_data["exams"])
    assert mock_data["examsPrototype"]["summary"]["answerVisibleToCandidate"] is False
    assert mock_data["examsPrototype"]["summary"]["reviewRequired"] is True
    assert mock_data["examsPrototype"]["actionPolicy"]["openGenerateEnabled"] is True
    assert mock_data["examsPrototype"]["actionPolicy"]["openReviewDetailEnabled"] is True
    assert mock_data["examsPrototype"]["actionPolicy"]["viewExamDslPreviewEnabled"] is True
    assert mock_data["examsPrototype"]["actionPolicy"]["viewGradingDslPreviewEnabled"] is True
    assert mock_data["examsPrototype"]["actionPolicy"]["showStandardAnswerEnabled"] is False
    assert mock_data["examsPrototype"]["actionPolicy"]["batchApproveEnabled"] is False
    assert mock_data["examsPrototype"]["actionPolicy"]["batchRejectEnabled"] is False
    assert mock_data["examsPrototype"]["actionPolicy"]["batchPublishEnabled"] is False
    assert mock_data["examsPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["examsPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["examsPrototype"]["actionPolicy"]["realSandboxRunEnabled"] is False
    assert mock_data["examsPrototype"]["safety"]["answerVisibleToCandidate"] is False
    assert mock_data["examsPrototype"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert mock_data["examsPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["examsPrototype"]["safety"]["batchStateChangeAllowed"] is False
    assert mock_data["examsPrototype"]["safety"]["realPublish"] is False
    assert [exam["id"] for exam in mock_data["exams"]] == ["exam_demo", "exam_reviewed_demo"]
    assert [exam["id"] for exam in mock_data["exams"] if exam["status"] == "WAITING_REVIEW"] == ["exam_demo"]
    assert all(exam["mode"] == "MOCK_ONLY" for exam in mock_data["exams"])
    assert all(
        exam["answerVisibleToCandidate"] is False and exam["standardAnswerRevealToCandidate"] is False
        for exam in mock_data["exams"]
    )
    assert all(
        exam["autoPublishAllowed"] is False
        and exam["realPublish"] is False
        and exam["realSandboxRunEnabled"] is False
        for exam in mock_data["exams"]
    )
    assert mock_data["examReviewPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["examReviewPrototype"]["input"]["taskId"] == "task_exam_demo"
    assert mock_data["examReviewPrototype"]["input"]["examId"] == "exam_demo"
    assert mock_data["examReviewPrototype"]["input"]["detailApi"] == "GET /api/review-tasks/{id}"
    assert mock_data["examReviewPrototype"]["input"]["approveApi"] == "POST /api/ai-tasks/{id}/approve"
    assert mock_data["examReviewPrototype"]["input"]["rejectApi"] == "POST /api/ai-tasks/{id}/reject"
    assert mock_data["examReviewPrototype"]["summary"]["taskType"] == "EXAM_GENERATION"
    assert mock_data["examReviewPrototype"]["summary"]["taskStatus"] == "WAITING_REVIEW"
    assert mock_data["examReviewPrototype"]["summary"]["artifactTotal"] == 2
    assert mock_data["examReviewPrototype"]["summary"]["workflowStepTotal"] == 3
    assert mock_data["examReviewPrototype"]["summary"]["answerVisibleToCandidate"] is False
    assert mock_data["examReviewPrototype"]["summary"]["standardAnswerRevealToCandidate"] is False
    assert mock_data["examReviewPrototype"]["summary"]["answerHiddenFromCandidatePreview"] is True
    assert mock_data["examReviewPrototype"]["summary"]["questionGradingRefCoverageStatus"] == "MATCHED"
    assert mock_data["examReviewPrototype"]["summary"]["scoreCoverageStatus"] == "MATCHED"
    assert mock_data["examReviewPrototype"]["summary"]["gradingPlanExplainable"] is True
    assert mock_data["examReviewPrototype"]["summary"]["reviewRequired"] is True
    assert mock_data["examReviewPrototype"]["summary"]["publishBlockedUntilApproved"] is True
    assert mock_data["examReviewPrototype"]["dslPreview"]["examDslPath"] == mock_data["dslPreviews"]["exam"]["path"]
    assert mock_data["examReviewPrototype"]["dslPreview"]["gradingDslPath"] == mock_data["dslPreviews"]["grading"]["path"]
    assert mock_data["examReviewPrototype"]["dslPreview"]["candidatePreviewAnswer"] == "[REDACTED_FOR_CANDIDATE]"
    assert mock_data["examReviewPrototype"]["dslPreview"]["candidateSafeExamPreview"]["answersRemoved"] is True
    assert mock_data["examReviewPrototype"]["dslPreview"]["answerVisibleToCandidate"] is False
    assert mock_data["examReviewPrototype"]["dslPreview"]["standardAnswerRevealToCandidate"] is False
    assert mock_data["examReviewPrototype"]["qualitySignals"]["coverage"]["questionGradingRefCoverage"]["matched"] is True
    assert mock_data["examReviewPrototype"]["qualitySignals"]["coverage"]["questionGradingRefCoverage"]["status"] == "MATCHED"
    assert mock_data["examReviewPrototype"]["qualitySignals"]["coverage"]["scoreCoverage"]["matched"] is True
    assert mock_data["examReviewPrototype"]["qualitySignals"]["coverage"]["explainability"]["status"] == "EXPLAINABLE"
    assert (
        mock_data["examReviewPrototype"]["qualitySignals"]["coverage"]["explainability"][
            "assessmentPlanAlignedWithChecks"
        ]
        is True
    )
    assert mock_data["examReviewPrototype"]["actionPolicy"]["singleApproveEnabled"] is True
    assert mock_data["examReviewPrototype"]["actionPolicy"]["singleRejectEnabled"] is True
    assert mock_data["examReviewPrototype"]["actionPolicy"]["singleRejectRequiresReason"] is True
    assert mock_data["examReviewPrototype"]["actionPolicy"]["viewExamDslEnabled"] is True
    assert mock_data["examReviewPrototype"]["actionPolicy"]["viewGradingDslEnabled"] is True
    assert mock_data["examReviewPrototype"]["actionPolicy"]["showStandardAnswerEnabled"] is False
    assert mock_data["examReviewPrototype"]["actionPolicy"]["mockPublishEnabled"] is False
    assert mock_data["examReviewPrototype"]["actionPolicy"]["batchApproveEnabled"] is False
    assert mock_data["examReviewPrototype"]["actionPolicy"]["batchRejectEnabled"] is False
    assert mock_data["examReviewPrototype"]["actionPolicy"]["batchPublishEnabled"] is False
    assert mock_data["examReviewPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["examReviewPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["examReviewPrototype"]["actionPolicy"]["realSandboxRunEnabled"] is False
    assert mock_data["examReviewPrototype"]["safety"]["answerVisibleToCandidate"] is False
    assert mock_data["examReviewPrototype"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert mock_data["examReviewPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["examReviewPrototype"]["safety"]["batchStateChangeAllowed"] is False
    assert mock_data["examReviewPrototype"]["safety"]["realPublish"] is False
    assert mock_data["gradingPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["gradingPrototype"]["summary"]["gradingTotal"] == len(mock_data["gradings"])
    assert mock_data["gradingPrototype"]["summary"]["waitingReviewTotal"] == 1
    assert mock_data["gradingPrototype"]["summary"]["approvedTotal"] == 1
    assert mock_data["gradingPrototype"]["summary"]["reportTotal"] == len(mock_data["gradings"])
    assert mock_data["gradingPrototype"]["summary"]["sandboxExecuted"] is False
    assert mock_data["gradingPrototype"]["summary"]["contestantCodeExecuted"] is False
    assert mock_data["gradingPrototype"]["summary"]["reportDetailVisible"] is True
    assert mock_data["gradingPrototype"]["summary"]["reportDetailCheckPlans"] == 6
    assert mock_data["gradingPrototype"]["summary"]["assessmentPlanVisible"] is True
    assert mock_data["gradingPrototype"]["summary"]["assessmentPlanTotal"] == 1
    assert mock_data["gradingPrototype"]["summary"]["mockEvidenceStatus"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    assert "dslPreviews.grading.spec.assessmentPlan" in mock_data["gradingPrototype"]["uses"]
    assert mock_data["gradingPrototype"]["assessmentPlanSummary"]["source"] == "templates/grading/examples/python-pytest.yaml.spec.assessmentPlan"
    assert mock_data["gradingPrototype"]["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert mock_data["gradingPrototype"]["assessmentPlanSummary"]["executionStrategy"] == "MOCK_PLAN_ONLY"
    assert mock_data["gradingPrototype"]["assessmentPlanSummary"]["mockEvidenceStatus"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    assert mock_data["gradingPrototype"]["assessmentPlanSummary"]["riskLevels"] == ["high"]
    assert "executionPlan.requiredLimits" in mock_data["gradingPrototype"]["assessmentPlanSummary"]["reviewFocus"]
    assert mock_data["gradingPrototype"]["generationWorkflowSignal"]["workflowId"] == "phase2_grading_generation"
    assert mock_data["gradingPrototype"]["generationWorkflowSignal"]["backend"] == (
        "POST /api/phase2/workflows/grading-generation/run"
    )
    assert mock_data["gradingPrototype"]["generationWorkflowSignal"]["qualitySignals"]["gradingRefCoverageMatched"] is True
    assert mock_data["gradingPrototype"]["generationWorkflowSignal"]["qualitySignals"]["scoreCoverageMatched"] is True
    assert (
        mock_data["gradingPrototype"]["generationWorkflowSignal"]["qualitySignals"][
            "assessmentPlanAlignedWithChecks"
        ]
        is True
    )
    assert mock_data["gradingPrototype"]["reportDetailSummary"]["source"] == "gradingReport.reportDetail"
    assert mock_data["gradingPrototype"]["reportDetailSummary"]["checkPlanTotal"] == 6
    assert mock_data["gradingPrototype"]["reportDetailSummary"]["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert mock_data["gradingPrototype"]["reportDetailSummary"]["sandboxPolicy"]["hostExecutionAllowed"] is False
    assert mock_data["gradingPrototype"]["reportDetailSummary"]["sandboxPolicy"]["networkAccess"] == "disabled_by_default"
    assert mock_data["gradingPrototype"]["reportDetailSummary"]["explainability"]["status"] == "EXPLAINABLE_MOCK_PLAN"
    assert mock_data["gradingPrototype"]["reportDetailSummary"]["explainability"]["eachCheckHasInputSummary"] is True
    assert mock_data["gradingPrototype"]["reportDetailSummary"]["mockEvidenceStatus"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    assert "timeout" in mock_data["gradingPrototype"]["reportDetailSummary"]["requiredLimits"]
    assert mock_data["gradingPrototype"]["actionPolicy"]["runMockGradingEnabled"] is True
    assert mock_data["gradingPrototype"]["actionPolicy"]["viewGradingDslEnabled"] is True
    assert mock_data["gradingPrototype"]["actionPolicy"]["runMockGradingGenerationEnabled"] is True
    assert mock_data["gradingPrototype"]["actionPolicy"]["openReportEnabled"] is True
    assert mock_data["gradingPrototype"]["actionPolicy"]["viewAuditEventsEnabled"] is True
    assert mock_data["gradingPrototype"]["actionPolicy"]["realRegradeEnabled"] is False
    assert mock_data["gradingPrototype"]["actionPolicy"]["realSandboxRunEnabled"] is False
    assert mock_data["gradingPrototype"]["actionPolicy"]["contestantCodeExecutionEnabled"] is False
    assert mock_data["gradingPrototype"]["actionPolicy"]["unknownShellExecuteEnabled"] is False
    assert mock_data["gradingPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["gradingPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["gradingPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["gradingPrototype"]["safety"]["unknownShellExecuted"] is False
    assert mock_data["gradingPrototype"]["safety"]["realRegradeEnabled"] is False
    assert mock_data["gradingPrototype"]["safety"]["realPublish"] is False
    assert [grading["id"] for grading in mock_data["gradings"]] == ["grading_demo", "grading_reviewed_demo"]
    assert [grading["id"] for grading in mock_data["gradings"] if grading["status"] == "WAITING_REVIEW"] == ["grading_demo"]
    assert all(grading["mode"] == "MOCK_ONLY" for grading in mock_data["gradings"])
    assert all(
        grading["sandboxExecuted"] is False
        and grading["contestantCodeExecuted"] is False
        and grading["unknownShellExecuted"] is False
        and grading["realRegradeEnabled"] is False
        and grading["realPublish"] is False
        for grading in mock_data["gradings"]
    )
    assert mock_data["gradingReviewPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["gradingReviewPrototype"]["input"]["taskId"] == "task_grading_demo"
    assert mock_data["gradingReviewPrototype"]["input"]["gradingId"] == "grading_demo"
    assert mock_data["gradingReviewPrototype"]["input"]["detailApi"] == "GET /api/review-tasks/{id}"
    assert mock_data["gradingReviewPrototype"]["input"]["approveApi"] == "POST /api/ai-tasks/{id}/approve"
    assert mock_data["gradingReviewPrototype"]["input"]["rejectApi"] == "POST /api/ai-tasks/{id}/reject"
    assert mock_data["gradingReviewPrototype"]["input"]["auditApi"] == "GET /api/audit-events"
    assert mock_data["gradingReviewPrototype"]["summary"]["taskType"] == "GRADING_GENERATION"
    assert mock_data["gradingReviewPrototype"]["summary"]["taskStatus"] == "WAITING_REVIEW"
    assert mock_data["gradingReviewPrototype"]["summary"]["artifactTotal"] == 2
    assert mock_data["gradingReviewPrototype"]["summary"]["workflowStepTotal"] == 4
    assert mock_data["gradingReviewPrototype"]["summary"]["checkTypeTotal"] == 1
    assert mock_data["gradingReviewPrototype"]["summary"]["reportDetailVisible"] is True
    assert mock_data["gradingReviewPrototype"]["summary"]["reportDetailCheckPlans"] == 6
    assert mock_data["gradingReviewPrototype"]["summary"]["assessmentPlanVisible"] is True
    assert mock_data["gradingReviewPrototype"]["summary"]["assessmentPlanTotal"] == 1
    assert mock_data["gradingReviewPrototype"]["summary"]["assessmentPlanAlignedWithChecks"] is True
    assert mock_data["gradingReviewPrototype"]["summary"]["gradingRefCoverageStatus"] == "MATCHED"
    assert mock_data["gradingReviewPrototype"]["summary"]["scoreCoverageStatus"] == "MATCHED"
    assert mock_data["gradingReviewPrototype"]["summary"]["gradingPlanExplainable"] is True
    assert mock_data["gradingReviewPrototype"]["summary"]["assessmentPlanRiskLevels"] == ["high"]
    assert mock_data["gradingReviewPrototype"]["summary"]["mockEvidenceStatus"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    assert mock_data["gradingReviewPrototype"]["summary"]["sandboxExecuted"] is False
    assert mock_data["gradingReviewPrototype"]["summary"]["contestantCodeExecuted"] is False
    assert mock_data["gradingReviewPrototype"]["summary"]["unknownShellExecuted"] is False
    assert mock_data["gradingReviewPrototype"]["summary"]["reviewRequired"] is True
    assert mock_data["gradingReviewPrototype"]["summary"]["publishBlockedUntilApproved"] is True
    assert mock_data["gradingReviewPrototype"]["dslPreview"]["gradingDslPath"] == mock_data["dslPreviews"]["grading"]["path"]
    assert mock_data["gradingReviewPrototype"]["dslPreview"]["reportRoute"] == "/grading/:id/report"
    assert mock_data["gradingReviewPrototype"]["dslPreview"]["reportId"] == "grading_report_demo"
    assert mock_data["gradingReviewPrototype"]["dslPreview"]["checkTypes"] == ["pytest"]
    assert mock_data["gradingReviewPrototype"]["dslPreview"]["assessmentPlanTotal"] == 1
    assert mock_data["gradingReviewPrototype"]["dslPreview"]["assessmentPlanSource"] == "reviewDetail.assessmentPlan.summary"
    assert mock_data["gradingReviewPrototype"]["dslPreview"]["assessmentPlanAlignedWithChecks"] is True
    assert mock_data["gradingReviewPrototype"]["dslPreview"]["sandboxExecuted"] is False
    assert mock_data["gradingReviewPrototype"]["dslPreview"]["contestantCodeExecuted"] is False
    assert mock_data["gradingReviewPrototype"]["dslPreview"]["unknownShellExecuted"] is False
    assert mock_data["gradingReviewPrototype"]["reportDetailSummary"]["source"] == "gradingReport.reportDetail"
    assert mock_data["gradingReviewPrototype"]["reportDetailSummary"]["checkPlanTotal"] == 6
    assert mock_data["gradingReviewPrototype"]["reportDetailSummary"]["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert mock_data["gradingReviewPrototype"]["reportDetailSummary"]["sandboxPolicy"]["hostExecutionAllowed"] is False
    assert mock_data["gradingReviewPrototype"]["reportDetailSummary"]["explainability"]["status"] == "EXPLAINABLE_MOCK_PLAN"
    assert mock_data["gradingReviewPrototype"]["reportDetailSummary"]["mockEvidenceStatus"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    assert mock_data["gradingReviewPrototype"]["reportDetailSummary"]["reviewFocus"] == [
        "inputSummary",
        "mockEvidence",
        "requiredLimits",
        "hostExecutionAllowed",
    ]
    assert "dslPreviews.grading.spec.assessmentPlan" in mock_data["gradingReviewPrototype"]["uses"]
    assert "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan" in mock_data["gradingReviewPrototype"]["uses"]
    assert mock_data["gradingReviewPrototype"]["assessmentPlanSummary"]["source"] == "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary"
    assert mock_data["gradingReviewPrototype"]["assessmentPlanSummary"]["fallbackSource"] == "templates/grading/examples/python-pytest.yaml.spec.assessmentPlan"
    assert mock_data["gradingReviewPrototype"]["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert mock_data["gradingReviewPrototype"]["assessmentPlanSummary"]["sandboxRequiredBeforeRealExecution"] is True
    assert mock_data["gradingReviewPrototype"]["assessmentPlanSummary"]["realSandboxEvidenceRequired"] is True
    assert "reviewCenterPrototype.nextManualReviewAction" in mock_data["gradingReviewPrototype"]["uses"]
    manual_checklist = mock_data["gradingReviewPrototype"]["assessmentPlanManualReviewChecklist"]
    assert manual_checklist["enabled"] is True
    assert manual_checklist["source"] == "reviewCenterPrototype.nextManualReviewAction"
    assert manual_checklist["taskId"] == "task_grading_demo"
    assert manual_checklist["entryRoute"] == "/grading/:id/review?taskId=task_grading_demo"
    assert manual_checklist["primaryReviewFocus"] == "review_assessment_plan_before_approval"
    assert manual_checklist["status"] == "NEEDS_HUMAN_REVIEW"
    assert [item["id"] for item in manual_checklist["checklist"]] == [
        "verify_assessment_plan_aligned_with_checks",
        "confirm_mock_evidence_not_collected",
        "confirm_real_sandbox_evidence_required_before_real_execution",
        "verify_required_limits_present",
        "confirm_no_execution_or_publish",
    ]
    assert manual_checklist["checklist"][0]["expected"] == "assessmentPlanAlignedWithChecks=true"
    assert "reviewDetail.assessmentPlan.summary" in manual_checklist["checklist"][0]["evidence"]
    assert manual_checklist["checklist"][1]["expected"] == "mockEvidence.status=MOCK_EVIDENCE_NOT_COLLECTED"
    assert manual_checklist["checklist"][2]["expected"] == "realSandboxEvidenceRequired=true"
    assert (
        manual_checklist["checklist"][3]["expected"]
        == "requiredLimits=timeout/cpu/memory/network/filesystem/process"
    )
    assert "realPublishAllowed=false" in manual_checklist["checklist"][4]["expected"]
    assert all(item["status"] == "NEEDS_HUMAN_REVIEW" for item in manual_checklist["checklist"])
    assert manual_checklist["operatorDecision"]["manualDecisionRequired"] is True
    assert manual_checklist["operatorDecision"]["approveAllowedAfterChecklist"] is True
    assert manual_checklist["operatorDecision"]["rejectRequiresReason"] is True
    assert manual_checklist["operatorDecision"]["autoApproveAllowed"] is False
    assert manual_checklist["operatorDecision"]["batchStateChangeAllowed"] is False
    assert manual_checklist["operatorDecision"]["realSandboxRunEnabled"] is False
    assert manual_checklist["operatorDecision"]["contestantCodeExecuted"] is False
    assert manual_checklist["operatorDecision"]["realPublishAllowed"] is False
    assert mock_data["gradingReviewPrototype"]["assessmentPlan"][0]["checkId"] == "check_pytest"
    assert mock_data["gradingReviewPrototype"]["assessmentPlan"][0]["sourceField"] == "reviewDetail.assessmentPlan.items[0]"
    assert mock_data["gradingReviewPrototype"]["assessmentPlan"][0]["runner"] == "PytestGrader"
    assert mock_data["gradingReviewPrototype"]["assessmentPlan"][0]["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY"
    assert mock_data["gradingReviewPrototype"]["assessmentPlan"][0]["executionPlan"]["requiredLimits"]["network"] == "disabled_by_default"
    assert mock_data["gradingReviewPrototype"]["assessmentPlan"][0]["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    assert mock_data["gradingReviewPrototype"]["assessmentPlan"][0]["riskLevel"] == "high"
    assert mock_data["gradingReviewPrototype"]["qualitySignals"]["coverage"]["gradingRefCoverage"]["matched"] is True
    assert mock_data["gradingReviewPrototype"]["qualitySignals"]["coverage"]["gradingRefCoverage"]["status"] == "MATCHED"
    assert mock_data["gradingReviewPrototype"]["qualitySignals"]["coverage"]["scoreCoverage"]["matched"] is True
    assert mock_data["gradingReviewPrototype"]["qualitySignals"]["coverage"]["explainability"]["status"] == "EXPLAINABLE"
    assert (
        mock_data["gradingReviewPrototype"]["qualitySignals"]["coverage"]["explainability"][
            "assessmentPlanAlignedWithChecks"
        ]
        is True
    )
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["singleApproveEnabled"] is True
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["singleRejectEnabled"] is True
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["singleRejectRequiresReason"] is True
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["viewGradingDslEnabled"] is True
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["openReportEnabled"] is True
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["viewAuditEventsEnabled"] is True
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["mockPublishEnabled"] is False
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["batchApproveEnabled"] is False
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["batchRejectEnabled"] is False
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["batchPublishEnabled"] is False
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["realRegradeEnabled"] is False
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["realSandboxRunEnabled"] is False
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["contestantCodeExecutionEnabled"] is False
    assert mock_data["gradingReviewPrototype"]["actionPolicy"]["unknownShellExecuteEnabled"] is False
    assert mock_data["gradingReviewPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["gradingReviewPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["gradingReviewPrototype"]["safety"]["unknownShellExecuted"] is False
    assert mock_data["gradingReviewPrototype"]["safety"]["realRegradeEnabled"] is False
    assert mock_data["gradingReviewPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["gradingReviewPrototype"]["safety"]["batchStateChangeAllowed"] is False
    assert mock_data["gradingReviewPrototype"]["safety"]["realPublish"] is False
    assert mock_data["gradingReportPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["gradingReportPrototype"]["phase"] == "Phase 3"
    assert mock_data["gradingReportPrototype"]["input"]["gradingDslPath"] == "templates/grading/examples/mixed-checks.yaml"
    assert mock_data["gradingReportPrototype"]["scoreSummary"]["earnedScore"] == mock_data["gradingReport"]["earnedScore"]
    assert mock_data["gradingReportPrototype"]["scoreSummary"]["passed"] is True
    assert mock_data["gradingReportPrototype"]["scoreSummary"]["checkTotal"] == 6
    assert mock_data["gradingReportPrototype"]["scoreSummary"]["executedCheckTotal"] == 0
    assert mock_data["gradingReportPrototype"]["runnerSummary"]["id"] == "mock_grading_runner"
    assert mock_data["gradingReportPrototype"]["runnerSummary"]["strategy"] == "MOCK_PLAN_ONLY"
    assert mock_data["gradingReportPrototype"]["runnerSummary"]["supportedCheckTypes"] == SUPPORTED_GRADING_CHECK_TYPES
    assert "gradingReport.assessmentPlanSummary" in mock_data["gradingReportPrototype"]["uses"]
    assert "gradingReport.reportDetail.assessmentPlanSummary" in mock_data["gradingReportPrototype"]["uses"]
    assert "realDemoPrototype.readonlyEvidenceDemo.reportDetail" in mock_data["gradingReportPrototype"]["uses"]
    assert "containerSandboxPlan" in mock_data["gradingReportPrototype"]["checkColumns"]
    assert mock_data["gradingReportPrototype"]["assessmentPlanTraceSummary"]["source"] == "grading.spec.assessmentPlan"
    assert mock_data["gradingReportPrototype"]["assessmentPlanTraceSummary"]["planTotal"] == 6
    assert mock_data["gradingReportPrototype"]["assessmentPlanTraceSummary"]["checkTotal"] == 6
    assert mock_data["gradingReportPrototype"]["assessmentPlanTraceSummary"]["alignedWithChecks"] is True
    assert mock_data["gradingReportPrototype"]["assessmentPlanTraceSummary"]["executionStrategies"] == ["MOCK_PLAN_ONLY"]
    assert mock_data["gradingReportPrototype"]["assessmentPlanTraceSummary"]["mockEvidenceStatuses"] == ["MOCK_EVIDENCE_NOT_COLLECTED"]
    assert mock_data["gradingReportPrototype"]["assessmentPlanTraceSummary"]["riskLevels"] == ["high", "low", "medium"]
    assert "assessmentPlanSourceField" in mock_data["gradingReportPrototype"]["assessmentPlanTraceSummary"]["checkPlanFields"]
    assert "containerSandboxPlan" in mock_data["gradingReportPrototype"]["assessmentPlanTraceSummary"]["checkPlanFields"]
    assert "assessmentPlanAlignedWithCheck" in mock_data["gradingReportPrototype"]["checkColumns"]
    assert mock_data["gradingReportPrototype"]["detailSummary"]["assessmentPlanTraceVisible"] is True
    assert mock_data["gradingReportPrototype"]["detailSummary"]["assessmentPlanAlignedWithChecks"] is True
    assert mock_data["gradingReportPrototype"]["detailSummary"]["containerSandboxPlanVisible"] is True
    readonly_report_detail = mock_data["gradingReportPrototype"]["readonlyReportDetailSummary"]
    assert readonly_report_detail["source"] == "realDemoPrototype.readonlyEvidenceDemo.reportDetail"
    assert readonly_report_detail["visibleInDemoLoop"] is True
    assert readonly_report_detail["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert readonly_report_detail["checkSummary"]["executed"] == 2
    assert readonly_report_detail["checkSummary"]["deferred"] == 0
    assert readonly_report_detail["readonlyEvidenceStatus"] == "COLLECTED"
    assert readonly_report_detail["readonlyEvidenceCollectedTotal"] == 2
    assert readonly_report_detail["safety"]["contestantCodeExecuted"] is False
    assert readonly_report_detail["safety"]["sourceGradingModified"] is False
    assert mock_data["gradingReportPrototype"]["containerPlanSummary"]["mode"] == "CONTAINER_PLAN_ONLY"
    assert mock_data["gradingReportPrototype"]["containerPlanSummary"]["image"] == "python:3.11-slim"
    assert mock_data["gradingReportPrototype"]["containerPlanSummary"]["submissionMountMode"] == "read_only"
    assert mock_data["gradingReportPrototype"]["containerPlanSummary"]["networkEnabled"] is False
    assert mock_data["gradingReportPrototype"]["containerPlanSummary"]["resultPlaceholderStatus"] == "NOT_EXECUTED"
    assert mock_data["gradingReportPrototype"]["actionPolicy"]["realRegradeEnabled"] is False
    assert mock_data["gradingReportPrototype"]["actionPolicy"]["realSandboxRunEnabled"] is False
    assert mock_data["gradingReportPrototype"]["actionPolicy"]["contestantCodeExecutionEnabled"] is False
    assert mock_data["gradingReportPrototype"]["actionPolicy"]["executeCommandEnabled"] is False
    assert mock_data["gradingReportPrototype"]["actionPolicy"]["runRealPytestEnabled"] is False
    assert mock_data["gradingReportPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["gradingReportPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["gradingReportPrototype"]["safety"]["unknownShellExecuted"] is False
    assert mock_data["gradingReportPrototype"]["safety"]["commandExecuted"] is False
    assert mock_data["gradingReportPrototype"]["safety"]["realPytestRun"] is False
    assert mock_data["gradingReportPrototype"]["safety"]["hostExecutionAllowed"] is False
    assert mock_data["aiTaskCenterPrototype"]["mode"] == "MOCK_ONLY"
    assert "gradingReviewPrototype.assessmentPlanSummary" in mock_data["aiTaskCenterPrototype"]["uses"]
    assert "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary" in mock_data["aiTaskCenterPrototype"]["uses"]
    assert "examReviewPrototype.qualitySignals" in mock_data["aiTaskCenterPrototype"]["uses"]
    assert "examReviewPrototype.dslPreview.candidateSafeExamPreview" in mock_data["aiTaskCenterPrototype"]["uses"]
    assert "gradingReviewPrototype.qualitySignals" in mock_data["aiTaskCenterPrototype"]["uses"]
    assert "reviewDetail.reviewPage.providerSummary.qualitySummary" in mock_data["aiTaskCenterPrototype"]["uses"]
    assert "reviewDetail.reviewPage.providerSummary.calls[].qualitySummary" in mock_data["aiTaskCenterPrototype"]["uses"]
    assert mock_data["aiTaskCenterPrototype"]["summary"]["taskTotal"] == len(mock_data["aiTasks"])
    assert mock_data["aiTaskCenterPrototype"]["summary"]["waitingReviewTotal"] == mock_data["reviewTaskSummary"]["queueSummary"]["waitingReviewTotal"]
    assert mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["enabled"] is True
    assert (
        mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["source"]
        == "reviewCenterPrototype.reviewPriorityQueue"
    )
    assert mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["defaultSort"] == "priorityRankAsc"
    assert mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["topPriorityTaskId"] == "task_grading_demo"
    assert (
        mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["topPriorityReasonCode"]
        == "HIGH_RISK_MOCK_EVIDENCE_REQUIRED"
    )
    assert mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["queueTotal"] == 3
    assert mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["urgentTotal"] == 1
    assert mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["highTotal"] == 1
    assert mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["normalTotal"] == 1
    assert mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["manualReviewChecklistTaskTotal"] == 1
    assert (
        mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"][
            "manualReviewChecklistNeedsHumanReviewTotal"
        ]
        == 5
    )
    assert mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["autoApproveAllowed"] is False
    assert mock_data["aiTaskCenterPrototype"]["reviewPrioritySignal"]["batchStateChangeAllowed"] is False
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["enabled"] is True
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["source"] == "reviewCenterPrototype.nextManualReviewAction"
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["taskId"] == "task_grading_demo"
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["taskType"] == "GRADING_GENERATION"
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["priority"] == "URGENT"
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["entryRoute"] == "/review-center?taskId=task_grading_demo"
    assert (
        mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["checklistSource"]
        == "reviewCenterPrototype.reviewPriorityQueue.items[0].manualReviewChecklistSummary"
    )
    assert (
        mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["primaryReviewFocus"]
        == "review_assessment_plan_before_approval"
    )
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["checklistTotal"] == 5
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["needsHumanReviewTotal"] == 5
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["nextReviewChecklistIds"] == [
        "verify_assessment_plan_aligned_with_checks",
        "confirm_mock_evidence_not_collected",
        "confirm_real_sandbox_evidence_required_before_real_execution",
        "verify_required_limits_present",
        "confirm_no_execution_or_publish",
    ]
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["operatorChecklist"] == [
        "open_task_grading_demo_review_detail",
        "verify_assessment_plan_aligned_with_checks",
        "confirm_real_sandbox_evidence_required_before_real_execution",
    ]
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["autoApproveAllowed"] is False
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["batchStateChangeAllowed"] is False
    assert mock_data["aiTaskCenterPrototype"]["nextManualReviewAction"]["realPublishAllowed"] is False
    assert mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["enabled"] is True
    assert (
        mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["source"]
        == "examReviewPrototype.qualitySignals + gradingReviewPrototype.qualitySignals"
    )
    assert mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["visibleForTaskTypes"] == [
        "EXAM_GENERATION",
        "GRADING_GENERATION",
    ]
    assert mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["matchedCoverageTotal"] == 4
    assert mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["explainablePlanTotal"] == 2
    assert mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["candidateSafeExamPreviewTotal"] == 1
    assert (
        mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["exam"][
            "candidateSafeExamPreviewAnswersRemoved"
        ]
        is True
    )
    assert (
        mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["exam"][
            "questionGradingRefCoverageStatus"
        ]
        == "MATCHED"
    )
    assert mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["exam"]["scoreCoverageStatus"] == "MATCHED"
    assert (
        mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["grading"]["gradingRefCoverageStatus"]
        == "MATCHED"
    )
    assert (
        mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["grading"]["scoreCoverageStatus"]
        == "MATCHED"
    )
    assert (
        mock_data["aiTaskCenterPrototype"]["qualitySignalTaskSignal"]["grading"][
            "assessmentPlanAlignedWithChecks"
        ]
        is True
    )
    provider_signal = mock_data["aiTaskCenterPrototype"]["providerQualityTaskSignal"]
    provider_quality = mock_data["reviewDetail"]["reviewPage"]["providerSummary"]["qualitySummary"]
    assert provider_signal["enabled"] is True
    assert provider_signal["source"] == "reviewDetail.reviewPage.providerSummary.qualitySummary"
    assert provider_signal["callSource"] == "reviewDetail.reviewPage.providerSummary.calls[].qualitySummary"
    assert provider_signal["visibleForTaskTypes"] == ["LAB_GENERATION"]
    assert provider_signal["taskId"] == "task_lab_demo"
    assert provider_signal["readyForReview"] == provider_quality["readyForReview"]
    assert provider_signal["normalizationPatchCount"] == provider_quality["normalizationPatchCount"]
    assert provider_signal["normalizationPatches"] == provider_quality["normalizationPatches"]
    assert provider_signal["schemaRepairApplied"] == provider_quality["schemaRepairApplied"]
    assert provider_signal["responseId"] == provider_quality["responseId"]
    assert provider_signal["totalTokens"] == 1234
    assert provider_signal["autoApproveAllowed"] is False
    assert provider_signal["autoPublishAllowed"] is False
    assert provider_signal["realPublishAllowed"] is False
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["enabled"] is True
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["source"] == "gradingReviewPrototype.assessmentPlanSummary"
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["backendSource"] == "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary"
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["visibleForTaskTypes"] == ["GRADING_GENERATION"]
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["planTotal"] == 1
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["alignedWithChecks"] is True
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["riskLevels"] == ["high"]
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["executionStrategies"] == ["MOCK_PLAN_ONLY"]
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["mockEvidenceStatuses"] == ["MOCK_EVIDENCE_NOT_COLLECTED"]
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["requiredLimits"] == [
        "timeout",
        "cpu",
        "memory",
        "network",
        "filesystem",
        "process",
    ]
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["realSandboxEvidenceRequired"] is True
    assert mock_data["aiTaskCenterPrototype"]["assessmentPlanTaskSignal"]["sandboxRequiredBeforeRealExecution"] is True
    grading_task = next(task for task in mock_data["aiTasks"] if task["taskType"] == "GRADING_GENERATION")
    assert grading_task["id"] == "task_grading_demo"
    assert grading_task["assessmentPlanSummary"]["source"] == "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary"
    assert grading_task["assessmentPlanSummary"]["planTotal"] == 1
    assert grading_task["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert grading_task["assessmentPlanSummary"]["riskLevels"] == ["high"]
    assert grading_task["assessmentPlanSummary"]["mockEvidenceStatuses"] == ["MOCK_EVIDENCE_NOT_COLLECTED"]
    assert grading_task["assessmentPlanSummary"]["realSandboxEvidenceRequired"] is True
    lab_task = next(task for task in mock_data["aiTasks"] if task["id"] == "task_lab_demo")
    assert lab_task["providerQualitySummary"] == provider_signal
    assert mock_data["aiTaskCenterPrototype"]["selectedTask"]["reviewRequired"] is True
    assert mock_data["aiTaskCenterPrototype"]["selectedTask"]["autoPublishAllowed"] is False
    assert mock_data["aiTaskCenterPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["aiTaskCenterPrototype"]["actionPolicy"]["batchApproveEnabled"] is False
    assert mock_data["aiTaskCenterPrototype"]["actionPolicy"]["realAgentRunEnabled"] is False
    assert mock_data["aiTaskCenterPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["aiTaskCenterPrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["aiTaskCenterPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["dashboardPrototype"]["mode"] == "MOCK_ONLY"
    assert "gradingReviewPrototype.assessmentPlanSummary" in mock_data["dashboardPrototype"]["uses"]
    assert "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary" in mock_data["dashboardPrototype"]["uses"]
    assert mock_data["dashboardPrototype"]["summary"]["healthStatus"] == mock_data["dashboard"]["health"]["status"]
    assert mock_data["dashboardPrototype"]["summary"]["aiTaskTotal"] == len(mock_data["aiTasks"])
    assert mock_data["dashboardPrototype"]["summary"]["workflowRunTotal"] == len(mock_data["workflowRuns"])
    assert mock_data["dashboardPrototype"]["summary"]["artifactTotal"] == len(mock_data["artifacts"])
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["enabled"] is True
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["source"] == "gradingReviewPrototype.assessmentPlanSummary"
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["backendSource"] == "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary"
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["visibleForTaskTypes"] == ["GRADING_GENERATION"]
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["planTotal"] == 1
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["alignedWithChecks"] is True
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["riskLevels"] == ["high"]
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["executionStrategies"] == ["MOCK_PLAN_ONLY"]
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["mockEvidenceStatuses"] == ["MOCK_EVIDENCE_NOT_COLLECTED"]
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["requiredLimits"] == [
        "timeout",
        "cpu",
        "memory",
        "network",
        "filesystem",
        "process",
    ]
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["realSandboxEvidenceRequired"] is True
    assert mock_data["dashboardPrototype"]["assessmentPlanDashboardSignal"]["sandboxRequiredBeforeRealExecution"] is True
    assert mock_data["dashboardPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["dashboardPrototype"]["actionPolicy"]["batchApproveEnabled"] is False
    assert mock_data["dashboardPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["dashboardPrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["dashboardPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["consolePrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["consolePrototype"]["summary"]["routeTotal"] == len(mock_data["consolePrototype"]["routeCards"])
    assert mock_data["consolePrototype"]["summary"]["mockOnlyRouteTotal"] == 31
    assert mock_data["consolePrototype"]["summary"]["deliveryReady"] == 175
    assert mock_data["consolePrototype"]["summary"]["deliveryRequired"] == 175
    assert mock_data["consolePrototype"]["summary"]["phase1CheckTotal"] == 20
    assert mock_data["consolePrototype"]["summary"]["phase1CheckPassed"] == 20
    assert mock_data["consolePrototype"]["summary"]["autoPublishAllowed"] is False
    assert mock_data["consolePrototype"]["summary"]["realPublish"] is False
    assert {card["route"] for card in mock_data["consolePrototype"]["routeCards"]} >= {
        "/console",
        "/dashboard",
        "/audit",
        "/audit/:id",
        "/audit/incidents",
        "/operations/launchpad",
        "/access",
        "/operations/runbook",
        "/operations/acceptance",
        "/operations/demo-map",
        "/operations/presenter",
        "/operations/signoff",
        "/operations/demo-script",
        "/delivery",
        "/ai-tasks",
        "/review-center",
        "/workflows",
        "/labs",
        "/labs/generate",
        "/labs/:id/review",
        "/exams",
        "/exams/generate",
        "/exams/:id/review",
        "/grading",
        "/grading/:id/review",
        "/grading/:id/report",
        "/ppt",
        "/ppt/:id/review",
        "/environments",
        "/skills",
        "/settings/providers",
    }
    assert all((ROOT / card["path"]).exists() for card in mock_data["consolePrototype"]["routeCards"])
    assert mock_data["consolePrototype"]["actionPolicy"]["startRealAgentEnabled"] is False
    assert mock_data["consolePrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["consolePrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["consolePrototype"]["actionPolicy"]["createRealCloudResourceEnabled"] is False
    assert mock_data["consolePrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["consolePrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["consolePrototype"]["actionPolicy"]["secretDisplayEnabled"] is False
    assert mock_data["consolePrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["consolePrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["consolePrototype"]["safety"]["realCloudResourceCreated"] is False
    assert mock_data["consolePrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["consolePrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["consolePrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["consolePrototype"]["safety"]["unknownShellExecuted"] is False
    assert mock_data["consolePrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["consolePrototype"]["safety"]["batchStateChangeAllowed"] is False
    assert mock_data["consolePrototype"]["safety"]["realPublish"] is False
    assert mock_data["consolePrototype"]["safety"]["standardAnswerRevealToCandidate"] is False
    assert mock_data["consolePrototype"]["safety"]["remoteUploadAllowed"] is False
    assert mock_data["consolePrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["workflowRegistryPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["workflowRegistryPrototype"]["route"] == "/workflows"
    assert mock_data["workflowRegistryPrototype"]["summary"]["workflowTotal"] == len(
        mock_data["workflowRegistryPrototype"]["workflows"]
    )
    assert mock_data["workflowRegistryPrototype"]["summary"]["workflowTotal"] == 4
    assert mock_data["workflowRegistryPrototype"]["summary"]["mcpToolTotal"] == len(
        mock_data["workflowRegistryPrototype"]["mcpTools"]
    )
    assert {workflow["workflowId"] for workflow in mock_data["workflowRegistryPrototype"]["workflows"]} == {
        "phase2_content_generation",
        "phase2_exam_conversion",
        "phase2_ppt_generation",
        "phase2_grading_generation",
    }
    assert {tool["name"] for tool in mock_data["workflowRegistryPrototype"]["mcpTools"]} == {
        "list_workflows",
        "get_workflow",
    }
    assert mock_data["workflowRegistryPrototype"]["actionPolicy"]["runWorkflowEnabled"] is False
    assert mock_data["workflowRegistryPrototype"]["actionPolicy"]["startRealMcpServerEnabled"] is False
    assert mock_data["workflowRegistryPrototype"]["actionPolicy"]["startRealAgentEnabled"] is False
    assert mock_data["workflowRegistryPrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["workflowRegistryPrototype"]["actionPolicy"]["createAiTaskEnabled"] is False
    assert mock_data["workflowRegistryPrototype"]["actionPolicy"]["createArtifactEnabled"] is False
    assert mock_data["workflowRegistryPrototype"]["safety"]["readOnly"] is True
    assert mock_data["workflowRegistryPrototype"]["safety"]["workflowExecuted"] is False
    assert mock_data["workflowRegistryPrototype"]["safety"]["taskCreated"] is False
    assert mock_data["workflowRegistryPrototype"]["safety"]["artifactCreated"] is False
    assert mock_data["workflowRegistryPrototype"]["safety"]["realMcpServerStarted"] is False
    assert mock_data["workflowRegistryPrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["workflowRegistryPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["workflowRegistryPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["workflowRegistryPrototype"]["safety"]["realPublish"] is False
    assert mock_data["auditObservabilityPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["auditObservabilityPrototype"]["summary"]["providerCallTotal"] == len(mock_data["providerCallAuditEvents"])
    assert mock_data["auditObservabilityPrototype"]["summary"]["mcpToolCallTotal"] == len(mock_data["mcpToolCallRecords"])
    assert mock_data["auditObservabilityPrototype"]["summary"]["workflowRunTotal"] == len(mock_data["workflowRuns"])
    assert mock_data["auditObservabilityPrototype"]["summary"]["operationAuditEventTotal"] == len(mock_data["operationAuditEvents"])
    assert mock_data["auditObservabilityPrototype"]["summary"]["reviewAuditEventTotal"] == len(mock_data["reviewAuditEvents"])
    assert mock_data["auditObservabilityPrototype"]["summary"]["highRiskIntentTotal"] == len(
        mock_data["highRiskMcpIntentPrototype"]["items"]
    )
    assert mock_data["auditObservabilityPrototype"]["summary"]["criticalIntentTotal"] == 1
    assert mock_data["auditObservabilityPrototype"]["summary"]["secondConfirmationStatusQueryTotal"] == 1
    assert mock_data["auditObservabilityPrototype"]["summary"]["secondConfirmationStatusReadOnly"] is True
    assert mock_data["auditObservabilityPrototype"]["summary"]["failedTotal"] == 2
    assert mock_data["auditObservabilityPrototype"]["summary"]["readOnly"] is True
    assert "operationAuditEvents.detail.assessmentPlanSummary" in mock_data["auditObservabilityPrototype"]["uses"]
    assert "operationAuditEvents.detail.checkPlans[].assessmentPlanSourceField" in mock_data["auditObservabilityPrototype"]["uses"]
    assert "gradingReport.assessmentPlanSummary" in mock_data["auditObservabilityPrototype"]["uses"]
    assessment_plan_audit_signal = mock_data["auditObservabilityPrototype"]["assessmentPlanAuditSignal"]
    assert assessment_plan_audit_signal["enabled"] is True
    assert assessment_plan_audit_signal["source"] == "operationAuditEvents.detail.assessmentPlanSummary"
    assert assessment_plan_audit_signal["reportSource"] == "gradingReport.assessmentPlanSummary"
    assert assessment_plan_audit_signal["visibleForActions"] == ["MOCK_GRADING_RUN"]
    assert assessment_plan_audit_signal["planTotal"] == 6
    assert assessment_plan_audit_signal["checkTotal"] == 6
    assert assessment_plan_audit_signal["alignedWithChecks"] is True
    assert assessment_plan_audit_signal["executionStrategies"] == ["MOCK_PLAN_ONLY"]
    assert assessment_plan_audit_signal["mockEvidenceStatuses"] == ["MOCK_EVIDENCE_NOT_COLLECTED"]
    assert assessment_plan_audit_signal["riskLevels"] == ["high", "low", "medium"]
    assert "assessmentPlanSourceField" in assessment_plan_audit_signal["checkPlanFields"]
    assert assessment_plan_audit_signal["realSandboxEvidenceRequired"] is True
    assert assessment_plan_audit_signal["sandboxRequiredBeforeRealExecution"] is True
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["viewProviderAuditEnabled"] is True
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["viewMcpAuditEnabled"] is True
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["viewSecondConfirmationStatusEnabled"] is True
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["exportAuditEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["startRealAgentEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["createRealCloudResourceEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["runRealSandboxEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["executeHighRiskIntentEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["confirmSecondFactorEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["confirmationEndpointEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["destroyRealEnvironmentEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["actionPolicy"]["secretDisplayEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["realMcpServerStarted"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["secretsRead"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["networkAccess"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["secondConfirmationStatusReadOnly"] is True
    assert mock_data["auditObservabilityPrototype"]["safety"]["confirmationEndpointEnabled"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["realPublish"] is False
    assert mock_data["auditObservabilityPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert all(event["mode"] == "MOCK_ONLY" for event in mock_data["providerCallAuditEvents"])
    assert all(event["realLlmCalled"] is False for event in mock_data["providerCallAuditEvents"])
    assert all(event["secretsRead"] is False for event in mock_data["providerCallAuditEvents"])
    assert all(event["networkAccess"] is False for event in mock_data["providerCallAuditEvents"])
    assert all(
        event["generatedStatus"] == "WAITING_REVIEW"
        for event in mock_data["providerCallAuditEvents"]
        if event["status"] == "SUCCESS"
    )
    assert any(event["id"] == "provider_audit_missing_prompt_demo" for event in mock_data["providerCallAuditEvents"])
    assert any(event.get("errorCode") == "PROMPT_NOT_FOUND" for event in mock_data["providerCallAuditEvents"])
    assert all(event["autoPublishAllowed"] is False for event in mock_data["providerCallAuditEvents"])
    assert all(event["realPublish"] is False for event in mock_data["providerCallAuditEvents"])
    assert all(record["mode"] == "MOCK_ONLY" for record in mock_data["mcpToolCallRecords"])
    assert all(record["realMcpServerStarted"] is False for record in mock_data["mcpToolCallRecords"])
    assert all(record["realAgentStarted"] is False for record in mock_data["mcpToolCallRecords"])
    assert all(record["realLlmCalled"] is False for record in mock_data["mcpToolCallRecords"])
    assert all(record["secretsRead"] is False for record in mock_data["mcpToolCallRecords"])
    assert all(record["networkAccess"] is False for record in mock_data["mcpToolCallRecords"])
    assert all(record["argumentPreviewRedactsSecrets"] is True for record in mock_data["mcpToolCallRecords"])
    assert all(record["autoPublishAllowed"] is False for record in mock_data["mcpToolCallRecords"])
    assert all(record["realPublish"] is False for record in mock_data["mcpToolCallRecords"])
    assert {record["status"] for record in mock_data["mcpToolCallRecords"]} == {"SUCCESS", "FAILED"}
    high_risk_intents = mock_data["highRiskMcpIntentPrototype"]
    assert high_risk_intents["mode"] == "MOCK_ONLY"
    assert high_risk_intents["summary"]["total"] == 3
    assert high_risk_intents["summary"]["waitingReviewTotal"] == 1
    assert high_risk_intents["summary"]["approvedIntentTotal"] == 2
    assert high_risk_intents["summary"]["criticalTotal"] == 1
    assert high_risk_intents["summary"]["approvedExecutionBlockedTotal"] == 1
    assert high_risk_intents["summary"]["approvedPendingSecondConfirmationTotal"] == 1
    assert high_risk_intents["summary"]["secondConfirmationPendingTotal"] == 1
    assert high_risk_intents["summary"]["secondConfirmationSatisfiedTotal"] == 0
    assert high_risk_intents["summary"]["realActionExecutedTotal"] == 0
    assert high_risk_intents["summary"]["realPublishTotal"] == 0
    assert high_risk_intents["summary"]["environmentDestroyedTotal"] == 0
    assert high_risk_intents["actionPolicy"]["reviewIntentOnly"] is True
    assert high_risk_intents["actionPolicy"]["postReviewDispositionRequired"] is True
    assert high_risk_intents["actionPolicy"]["executeRealPublishEnabled"] is False
    assert high_risk_intents["actionPolicy"]["destroyRealEnvironmentEnabled"] is False
    assert high_risk_intents["safety"]["reviewIntentOnly"] is True
    assert high_risk_intents["safety"]["realMcpServerStarted"] is False
    assert high_risk_intents["safety"]["realAgentStarted"] is False
    assert high_risk_intents["safety"]["realLlmCalled"] is False
    assert high_risk_intents["safety"]["realCloudResourceChanged"] is False
    assert high_risk_intents["safety"]["environmentDestroyed"] is False
    assert high_risk_intents["safety"]["realPublish"] is False
    assert {item["toolName"] for item in high_risk_intents["items"]} == {
        "publish_lab",
        "publish_exam",
        "destroy_environment",
    }
    assert {item["status"] for item in high_risk_intents["items"]} == {"WAITING_REVIEW", "APPROVED"}
    disposition_by_tool = {
        item["toolName"]: item["postReviewDisposition"] for item in high_risk_intents["items"]
    }
    assert disposition_by_tool["publish_lab"]["state"] == "WAITING_HUMAN_REVIEW"
    assert disposition_by_tool["publish_lab"]["nextRequiredAction"] == "approve_or_reject"
    assert disposition_by_tool["publish_exam"]["state"] == "APPROVED_EXECUTION_BLOCKED"
    assert disposition_by_tool["publish_exam"]["nextRequiredAction"] == "mock_disposition_only"
    assert disposition_by_tool["destroy_environment"]["state"] == "APPROVED_PENDING_SECOND_CONFIRMATION"
    assert disposition_by_tool["destroy_environment"]["nextRequiredAction"] == "second_confirmation"
    assert all(item["postReviewDisposition"]["executionBlocked"] is True for item in high_risk_intents["items"])
    assert all(item["postReviewDisposition"]["executeRealActionAllowed"] is False for item in high_risk_intents["items"])
    assert all(item["postReviewDisposition"]["executeRealPublishEnabled"] is False for item in high_risk_intents["items"])
    assert all(item["postReviewDisposition"]["destroyRealEnvironmentEnabled"] is False for item in high_risk_intents["items"])
    assert all(item["realActionExecuted"] is False for item in high_risk_intents["items"])
    assert all(item["realPublish"] is False for item in high_risk_intents["items"])
    assert all(item["autoPublishAllowed"] is False for item in high_risk_intents["items"])
    publish_lab_intent = next(item for item in high_risk_intents["items"] if item["toolName"] == "publish_lab")
    assert publish_lab_intent["reviewRequired"] is True
    assert publish_lab_intent["blockedUntilApproved"] is True
    publish_exam_intent = next(item for item in high_risk_intents["items"] if item["toolName"] == "publish_exam")
    assert publish_exam_intent["reviewRequired"] is False
    assert publish_exam_intent["blockedUntilApproved"] is False
    destroy_intent = next(item for item in high_risk_intents["items"] if item["toolName"] == "destroy_environment")
    assert destroy_intent["riskLevel"] == "critical"
    assert destroy_intent["requiresSecondConfirmation"] is True
    assert destroy_intent["reviewRequired"] is False
    assert destroy_intent["blockedUntilApproved"] is False
    assert destroy_intent["postReviewDisposition"]["secondConfirmationRequired"] is True
    assert destroy_intent["postReviewDisposition"]["secondConfirmationSatisfied"] is False
    assert destroy_intent["environmentDestroyed"] is False
    second_confirmation = mock_data["secondConfirmationStatusPrototype"]
    assert second_confirmation["mode"] == "MOCK_ONLY"
    assert second_confirmation["mcpToolName"] == "get_second_confirmation_status"
    assert second_confirmation["taskId"] == "task_mcp_destroy_environment_intent_demo"
    assert second_confirmation["intent"]["intentType"] == "destroy_environment"
    assert second_confirmation["state"] == "APPROVED_PENDING_SECOND_CONFIRMATION"
    assert second_confirmation["readOnly"] is True
    assert second_confirmation["secondConfirmationRequired"] is True
    assert second_confirmation["secondConfirmationSatisfied"] is False
    assert second_confirmation["confirmationActionAvailable"] is False
    assert second_confirmation["confirmationEndpointEnabled"] is False
    assert second_confirmation["confirmationEndpoint"] is None
    assert second_confirmation["executeRealActionAllowed"] is False
    assert second_confirmation["destroyRealEnvironmentEnabled"] is False
    assert second_confirmation["environmentDestroyed"] is False
    assert "confirmSecondFactor" in second_confirmation["blockedActions"]
    assert second_confirmation["actionPolicy"]["viewStatusEnabled"] is True
    assert second_confirmation["actionPolicy"]["confirmSecondFactorEnabled"] is False
    assert second_confirmation["actionPolicy"]["destroyRealEnvironmentEnabled"] is False
    assert second_confirmation["safety"]["readOnly"] is True
    assert second_confirmation["safety"]["confirmationEndpointEnabled"] is False
    assert second_confirmation["safety"]["environmentDestroyed"] is False
    mcp_records_by_tool = {record["toolName"]: record for record in mock_data["mcpToolCallRecords"]}
    assert mcp_records_by_tool["publish_lab"]["reviewRequired"] is True
    assert mcp_records_by_tool["publish_lab"]["riskLevel"] == "high"
    assert mcp_records_by_tool["publish_exam"]["reviewRequired"] is True
    assert mcp_records_by_tool["publish_exam"]["postReviewDispositionState"] == "APPROVED_EXECUTION_BLOCKED"
    assert mcp_records_by_tool["publish_exam"]["executeRealPublishEnabled"] is False
    assert mcp_records_by_tool["destroy_environment"]["riskLevel"] == "critical"
    assert mcp_records_by_tool["destroy_environment"]["requiresSecondConfirmation"] is True
    assert (
        mcp_records_by_tool["destroy_environment"]["postReviewDispositionState"]
        == "APPROVED_PENDING_SECOND_CONFIRMATION"
    )
    assert mcp_records_by_tool["destroy_environment"]["secondConfirmationSatisfied"] is False
    assert mcp_records_by_tool["destroy_environment"]["destroyRealEnvironmentEnabled"] is False
    assert mcp_records_by_tool["destroy_environment"]["environmentDestroyed"] is False
    assert mcp_records_by_tool["get_second_confirmation_status"]["riskLevel"] == "critical"
    assert mcp_records_by_tool["get_second_confirmation_status"]["reviewRequired"] is False
    assert mcp_records_by_tool["get_second_confirmation_status"]["backendMethod"] == "GET"
    assert mcp_records_by_tool["get_second_confirmation_status"]["readOnly"] is True
    assert mcp_records_by_tool["get_second_confirmation_status"]["confirmationActionAvailable"] is False
    assert mcp_records_by_tool["get_second_confirmation_status"]["confirmationEndpointEnabled"] is False
    assert mcp_records_by_tool["get_second_confirmation_status"]["executeRealActionAllowed"] is False
    assert mcp_records_by_tool["get_second_confirmation_status"]["destroyRealEnvironmentEnabled"] is False
    assert mcp_records_by_tool["get_second_confirmation_status"]["environmentDestroyed"] is False
    assert mcp_records_by_tool["get_second_confirmation_status"]["linkedSecondConfirmationStatusPrototype"] is True
    assert mock_data["auditDetailPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["auditDetailPrototype"]["summary"]["selectedRecordTotal"] == len(mock_data["auditDetailPrototype"]["selectedRecords"])
    assert mock_data["auditDetailPrototype"]["summary"]["providerRecordTotal"] == 1
    assert mock_data["auditDetailPrototype"]["summary"]["mcpRecordTotal"] == 1
    assert mock_data["auditDetailPrototype"]["summary"]["failedRecordTotal"] == 1
    assert mock_data["auditDetailPrototype"]["summary"]["redactedPreviewTotal"] == 1
    assert mock_data["auditDetailPrototype"]["summary"]["readOnly"] is True
    assert mock_data["auditDetailPrototype"]["input"]["detailLookup"] == "localMockDataOnly"
    assert mock_data["auditDetailPrototype"]["correlation"]["workflowRunId"] == "workflow_run_demo"
    assert mock_data["auditDetailPrototype"]["correlation"]["providerAuditEventId"] == "provider_audit_lab_demo"
    assert mock_data["auditDetailPrototype"]["correlation"]["mcpToolCallRecordId"] == "mcp_call_analyze_demo"
    assert mock_data["auditDetailPrototype"]["correlation"]["publishBlockedUntilApproved"] is True
    assert "gradingReviewPrototype.assessmentPlanManualReviewChecklist" in mock_data["auditDetailPrototype"]["uses"]
    assert "reviewCenterPrototype.nextManualReviewAction" in mock_data["auditDetailPrototype"]["uses"]
    review_trace = mock_data["auditDetailPrototype"]["assessmentPlanManualReviewTrace"]
    assert review_trace["enabled"] is True
    assert review_trace["source"] == "gradingReviewPrototype.assessmentPlanManualReviewChecklist"
    assert review_trace["queueSource"] == "reviewCenterPrototype.nextManualReviewAction"
    assert review_trace["taskId"] == "task_grading_demo"
    assert review_trace["entryRoute"] == "/grading/:id/review?taskId=task_grading_demo"
    assert (
        review_trace["auditSource"]
        == "operationAuditEvents[action=MOCK_GRADING_RUN].detail.assessmentPlanSummary"
    )
    assert review_trace["primaryReviewFocus"] == "review_assessment_plan_before_approval"
    assert review_trace["checklistIds"] == [
        "verify_assessment_plan_aligned_with_checks",
        "confirm_mock_evidence_not_collected",
        "confirm_real_sandbox_evidence_required_before_real_execution",
        "verify_required_limits_present",
        "confirm_no_execution_or_publish",
    ]
    assert "operationAuditEvents.detail.assessmentPlanSummary" in review_trace["evidence"]
    assert review_trace["status"] == "TRACE_ONLY"
    assert review_trace["readOnly"] is True
    assert review_trace["autoApproveAllowed"] is False
    assert review_trace["batchStateChangeAllowed"] is False
    assert review_trace["realSandboxRunEnabled"] is False
    assert review_trace["contestantCodeExecuted"] is False
    assert review_trace["realPublishAllowed"] is False
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["openAuditIndexEnabled"] is True
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["viewSourceMockDataEnabled"] is True
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["copyTraceIdEnabled"] is True
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["retryRealCallEnabled"] is False
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["startRealAgentEnabled"] is False
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["readSecretEnabled"] is False
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["runRealSandboxEnabled"] is False
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["executeContestantCodeEnabled"] is False
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["auditDetailPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["auditDetailPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["auditDetailPrototype"]["safety"]["realMcpServerStarted"] is False
    assert mock_data["auditDetailPrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["auditDetailPrototype"]["safety"]["secretsRead"] is False
    assert mock_data["auditDetailPrototype"]["safety"]["networkAccess"] is False
    assert mock_data["auditDetailPrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["auditDetailPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["auditDetailPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["auditDetailPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["auditDetailPrototype"]["safety"]["realPublish"] is False
    assert mock_data["auditDetailPrototype"]["safety"]["secretVisibleInFrontend"] is False
    provider_detail = mock_data["auditDetailPrototype"]["selectedRecords"][0]
    mcp_detail = mock_data["auditDetailPrototype"]["selectedRecords"][1]
    assert provider_detail["recordType"] == "provider"
    assert provider_detail["generatedStatus"] == "WAITING_REVIEW"
    assert provider_detail["linkedWorkflowStep"] == "generate_lab_dsl"
    assert mcp_detail["recordType"] == "mcp"
    assert mcp_detail["status"] == "FAILED"
    assert mcp_detail["backendCalled"] is False
    assert mcp_detail["argumentPreviewRedactsSecrets"] is True
    assert mcp_detail["errorCode"] == "VALIDATION_ERROR"
    assert mock_data["auditIncidentReviewPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["auditIncidentReviewPrototype"]["summary"]["incidentTotal"] == len(mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert mock_data["auditIncidentReviewPrototype"]["summary"]["providerIncidentTotal"] == 1
    assert mock_data["auditIncidentReviewPrototype"]["summary"]["mcpIncidentTotal"] == 1
    assert mock_data["auditIncidentReviewPrototype"]["summary"]["validationErrorTotal"] == 1
    assert mock_data["auditIncidentReviewPrototype"]["summary"]["promptConfigErrorTotal"] == 1
    assert mock_data["auditIncidentReviewPrototype"]["summary"]["safeMockCommandTotal"] == 2
    assert mock_data["auditIncidentReviewPrototype"]["summary"]["readOnly"] is True
    assert {rule["id"] for rule in mock_data["auditIncidentReviewPrototype"]["incidentRules"]} == {
        "rule_mcp_validation_error",
        "rule_provider_prompt_missing",
    }
    assert {incident["category"] for incident in mock_data["auditIncidentReviewPrototype"]["incidents"]} == {
        "INPUT_VALIDATION",
        "PROMPT_CONFIG",
    }
    assert {incident["sourceRecordId"] for incident in mock_data["auditIncidentReviewPrototype"]["incidents"]} == {
        "mcp_call_missing_input_demo",
        "provider_audit_missing_prompt_demo",
    }
    assert all(incident["status"] == "OPEN" for incident in mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert all(incident["mode"] == "MOCK_ONLY" for incident in mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert all(incident["realLlmCalled"] is False for incident in mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert all(incident["realMcpServerStarted"] is False for incident in mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert all(incident["realAgentStarted"] is False for incident in mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert all(incident["secretsRead"] is False for incident in mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert all(incident["networkAccess"] is False for incident in mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert all(incident["sandboxExecuted"] is False for incident in mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert all(incident["contestantCodeExecuted"] is False for incident in mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert all(incident["autoPublishAllowed"] is False for incident in mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert all(incident["realPublish"] is False for incident in mock_data["auditIncidentReviewPrototype"]["incidents"])
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["viewIncidentDetailEnabled"] is True
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["copySafeMockCommandEnabled"] is True
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["exportIncidentReportEnabled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["autoFixEnabled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["retryRealCallEnabled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["startRealAgentEnabled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["readSecretEnabled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["runRealSandboxEnabled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["executeContestantCodeEnabled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["auditIncidentReviewPrototype"]["safety"]["realMcpServerStarted"] is False
    assert mock_data["auditIncidentReviewPrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["auditIncidentReviewPrototype"]["safety"]["secretsRead"] is False
    assert mock_data["auditIncidentReviewPrototype"]["safety"]["networkAccess"] is False
    assert mock_data["auditIncidentReviewPrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["auditIncidentReviewPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["auditIncidentReviewPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["auditIncidentReviewPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["auditIncidentReviewPrototype"]["safety"]["realPublish"] is False
    assert mock_data["auditIncidentReviewPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["operationsRunbookPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["operationsRunbookPrototype"]["summary"]["sectionTotal"] == len(mock_data["operationsRunbookPrototype"]["sections"])
    assert mock_data["operationsRunbookPrototype"]["summary"]["safeCommandTotal"] == len(mock_data["operationsRunbookPrototype"]["safeCommands"])
    assert mock_data["operationsRunbookPrototype"]["summary"]["staticPageEntryTotal"] == 6
    assert mock_data["operationsRunbookPrototype"]["summary"]["auditEntryTotal"] == 3
    assert mock_data["operationsRunbookPrototype"]["summary"]["readOnly"] is True
    assert {section["id"] for section in mock_data["operationsRunbookPrototype"]["sections"]} == {
        "start_here",
        "local_preview",
        "validation_commands",
        "audit_review",
        "handoff_limits",
    }
    assert "scripts/phase1-demo.runbook.json" in mock_data["operationsRunbookPrototype"]["uses"]
    assert "scripts/manifest.json" in mock_data["operationsRunbookPrototype"]["uses"]
    assert "python lab_cli.py phase1 check" in mock_data["operationsRunbookPrototype"]["safeCommands"]
    assert (
        "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json"
        in mock_data["operationsRunbookPrototype"]["safeCommands"]
    )
    assert "python -m pytest" in mock_data["operationsRunbookPrototype"]["safeCommands"]
    assert "python lab_cli.py provider audit --operation generateJson" in mock_data["operationsRunbookPrototype"]["safeCommands"]
    assert "python lab_cli.py mcp audit --tool analyze_material" in mock_data["operationsRunbookPrototype"]["safeCommands"]
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["openLocalPageEnabled"] is True
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["copyCommandEnabled"] is True
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["runCommandEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["startRealAgentEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["createRealCloudResourceEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["runRealSandboxEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["executeContestantCodeEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["unknownShellExecutionEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["batchStateChangeEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["secretDisplayEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["actionPolicy"]["remoteUploadEnabled"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["readOnly"] is True
    assert mock_data["operationsRunbookPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["realMcpServerStarted"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["secretsRead"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["networkAccess"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["realCloudResourceCreated"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["unknownShellExecuted"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["realPublish"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["remoteUploadAllowed"] is False
    assert mock_data["operationsRunbookPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["operationsAcceptancePrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["operationsAcceptancePrototype"]["summary"]["acceptanceItemTotal"] == len(
        mock_data["operationsAcceptancePrototype"]["acceptanceItems"]
    )
    assert mock_data["operationsAcceptancePrototype"]["summary"]["passedTotal"] == 8
    assert mock_data["operationsAcceptancePrototype"]["summary"]["requiredTotal"] == 8
    assert mock_data["operationsAcceptancePrototype"]["summary"]["missingRequired"] == 0
    assert mock_data["operationsAcceptancePrototype"]["summary"]["linkedStaticPageTotal"] == len(
        mock_data["operationsAcceptancePrototype"]["linkedPages"]
    )
    assert mock_data["operationsAcceptancePrototype"]["summary"]["safeCommandTotal"] == len(
        mock_data["operationsAcceptancePrototype"]["safeCommands"]
    )
    assert mock_data["operationsAcceptancePrototype"]["summary"]["readOnly"] is True
    assert mock_data["operationsAcceptancePrototype"]["summary"]["readyForPhase2MockHandoff"] is True
    assert {item["id"] for item in mock_data["operationsAcceptancePrototype"]["acceptanceItems"]} == {
        "delivery_manifest_ready",
        "phase1_check_passed",
        "runbook_present",
        "demo_script_checklist_present",
        "faq_present",
        "handoff_present",
        "phase2_gate_present",
        "assessment_plan_audit_trace_visible",
    }
    assert all(item["required"] is True for item in mock_data["operationsAcceptancePrototype"]["acceptanceItems"])
    assert all(item["passed"] is True for item in mock_data["operationsAcceptancePrototype"]["acceptanceItems"])
    assert {page["route"] for page in mock_data["operationsAcceptancePrototype"]["linkedPages"]} == {
        "/operations/launchpad",
        "/access",
        "/operations/presenter",
        "/operations/signoff",
        "/operations/demo-script",
        "/operations/runbook",
        "/delivery",
        "/audit",
        "/audit/incidents",
    }
    assert "config/delivery-package.contract.json" in mock_data["operationsAcceptancePrototype"]["uses"]
    assert "delivery/DEMO_SCRIPT_CHECKLIST.md" in mock_data["operationsAcceptancePrototype"]["uses"]
    assert "delivery/FAQ.md" in mock_data["operationsAcceptancePrototype"]["uses"]
    assert "delivery/HANDOFF.md" in mock_data["operationsAcceptancePrototype"]["uses"]
    assert "delivery/PHASE2_READINESS.md" in mock_data["operationsAcceptancePrototype"]["uses"]
    assert "auditObservabilityPrototype" in mock_data["operationsAcceptancePrototype"]["uses"]
    assert "gradingReport.assessmentPlanSummary" in mock_data["operationsAcceptancePrototype"]["uses"]
    assert "operationAuditEvents.detail.assessmentPlanSummary" in mock_data["operationsAcceptancePrototype"]["uses"]
    assessment_acceptance_item = next(
        item
        for item in mock_data["operationsAcceptancePrototype"]["acceptanceItems"]
        if item["id"] == "assessment_plan_audit_trace_visible"
    )
    assert assessment_acceptance_item["source"] == "auditObservabilityPrototype.assessmentPlanAuditSignal"
    assert assessment_acceptance_item["evidence"]["reportSource"] == "gradingReport.assessmentPlanSummary"
    assert assessment_acceptance_item["evidence"]["auditSource"] == "operationAuditEvents.detail.assessmentPlanSummary"
    assert assessment_acceptance_item["evidence"]["sourceField"] == "grading.spec.assessmentPlan"
    assert assessment_acceptance_item["evidence"]["alignedWithChecks"] is True
    assert assessment_acceptance_item["evidence"]["mockEvidenceStatus"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    assert "python lab_cli.py phase1 check" in mock_data["operationsAcceptancePrototype"]["safeCommands"]
    assert (
        "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md"
        in mock_data["operationsAcceptancePrototype"]["safeCommands"]
    )
    assert "python -m pytest" in mock_data["operationsAcceptancePrototype"]["safeCommands"]
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["viewAcceptanceSummaryEnabled"] is True
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["openLinkedStaticPageEnabled"] is True
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["copySafeCommandEnabled"] is True
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["runCommandEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["uploadPackageEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["startRealAgentEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["createRealCloudResourceEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["runRealSandboxEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["executeContestantCodeEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["secretDisplayEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["actionPolicy"]["remoteUploadEnabled"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["readOnly"] is True
    assert mock_data["operationsAcceptancePrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["realMcpServerStarted"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["secretsRead"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["networkAccess"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["realCloudResourceCreated"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["unknownShellExecuted"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["realPublish"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["remoteUploadAllowed"] is False
    assert mock_data["operationsAcceptancePrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["operationsDemoMapPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["operationsDemoMapPrototype"]["summary"]["sequenceTotal"] == len(
        mock_data["operationsDemoMapPrototype"]["demoSequences"]
    )
    assert mock_data["operationsDemoMapPrototype"]["summary"]["roleTotal"] == len(mock_data["operationsDemoMapPrototype"]["roles"])
    assert mock_data["operationsDemoMapPrototype"]["summary"]["safeCommandTotal"] == len(
        mock_data["operationsDemoMapPrototype"]["safeCommands"]
    )
    assert mock_data["operationsDemoMapPrototype"]["summary"]["routeEntryTotal"] == sum(
        len(sequence["routes"]) for sequence in mock_data["operationsDemoMapPrototype"]["demoSequences"]
    )
    assert mock_data["operationsDemoMapPrototype"]["summary"]["routeEntryTotal"] == 30
    assert {role["id"] for role in mock_data["operationsDemoMapPrototype"]["roles"]} == {
        "operator",
        "reviewer",
        "teacher",
        "developer",
    }
    assert {sequence["id"] for sequence in mock_data["operationsDemoMapPrototype"]["demoSequences"]} == {
        "entry_acceptance",
        "audit_observability",
        "review_tasks",
        "content_generation",
        "grading_environment",
        "operation_config",
    }
    assert "/operations/launchpad" in mock_data["operationsDemoMapPrototype"]["demoSequences"][0]["routes"]
    assert "/operations/demo-map" in mock_data["operationsDemoMapPrototype"]["demoSequences"][0]["routes"]
    assert "/operations/presenter" in mock_data["operationsDemoMapPrototype"]["demoSequences"][0]["routes"]
    assert "/operations/signoff" in mock_data["operationsDemoMapPrototype"]["demoSequences"][0]["routes"]
    assert "/operations/demo-script" in mock_data["operationsDemoMapPrototype"]["demoSequences"][0]["routes"]
    assert "/workflows" in mock_data["operationsDemoMapPrototype"]["demoSequences"][2]["routes"]
    assert "frontend/ui.manifest.json" in mock_data["operationsDemoMapPrototype"]["uses"]
    assert "frontend/mock-data.json" in mock_data["operationsDemoMapPrototype"]["uses"]
    assert "start .\\frontend\\operations-demo-map.html" in mock_data["operationsDemoMapPrototype"]["safeCommands"]
    assert "start .\\frontend\\operations-presenter.html" in mock_data["operationsDemoMapPrototype"]["safeCommands"]
    assert "start .\\frontend\\operations-signoff.html" in mock_data["operationsDemoMapPrototype"]["safeCommands"]
    assert "start .\\frontend\\operations-launchpad.html" in mock_data["operationsDemoMapPrototype"]["safeCommands"]
    assert "start .\\frontend\\operations-demo-script.html" in mock_data["operationsDemoMapPrototype"]["safeCommands"]
    assert "python lab_cli.py phase1 check" in mock_data["operationsDemoMapPrototype"]["safeCommands"]
    assert "python -m pytest tests/test_frontend_manifest.py" in mock_data["operationsDemoMapPrototype"]["safeCommands"]
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["openStaticPageEnabled"] is True
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["copyRouteEnabled"] is True
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["copySafeCommandEnabled"] is True
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["runCommandEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["uploadPackageEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["startRealAgentEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["createRealCloudResourceEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["runRealSandboxEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["executeContestantCodeEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["batchStateChangeEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["secretDisplayEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["actionPolicy"]["remoteUploadEnabled"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["readOnly"] is True
    assert mock_data["operationsDemoMapPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["realMcpServerStarted"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["secretsRead"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["networkAccess"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["realCloudResourceCreated"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["unknownShellExecuted"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["realPublish"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["remoteUploadAllowed"] is False
    assert mock_data["operationsDemoMapPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["operationsDemoScriptPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["operationsDemoScriptPrototype"]["summary"]["demoStepTotal"] == len(
        mock_data["operationsDemoScriptPrototype"]["demoSteps"]
    )
    assert mock_data["operationsDemoScriptPrototype"]["summary"]["acceptanceSignalTotal"] == len(
        mock_data["operationsDemoScriptPrototype"]["acceptanceSignals"]
    )
    assert mock_data["operationsDemoScriptPrototype"]["summary"]["blockedActionTotal"] == len(
        mock_data["operationsDemoScriptPrototype"]["blockedActions"]
    )
    assert mock_data["operationsDemoScriptPrototype"]["summary"]["safeCommandTotal"] == len(
        mock_data["operationsDemoScriptPrototype"]["safeCommands"]
    )
    assert mock_data["operationsDemoScriptPrototype"]["summary"]["deliveryReady"] == 175
    assert mock_data["operationsDemoScriptPrototype"]["summary"]["deliveryRequired"] == 175
    assert mock_data["operationsDemoScriptPrototype"]["summary"]["phase1CheckTotal"] == 20
    assert mock_data["operationsDemoScriptPrototype"]["summary"]["phase1CheckPassed"] == 20
    assert {step["id"] for step in mock_data["operationsDemoScriptPrototype"]["demoSteps"]} == {
        "read_rules",
        "open_launchpad",
        "open_demo_map",
        "open_runbook",
        "run_phase1_check",
        "export_delivery_package",
        "render_acceptance_report",
        "open_acceptance",
        "open_delivery",
        "open_incident_review",
        "validate_cli_review_priority_queue",
        "validate_backend_mcp_review_priority_queue",
        "confirm_review_gate",
        "confirm_blocked_actions",
    }
    assert [step["order"] for step in mock_data["operationsDemoScriptPrototype"]["demoSteps"]] == list(range(1, 15))
    assert {signal["id"] for signal in mock_data["operationsDemoScriptPrototype"]["acceptanceSignals"]} == {
        "launchpad_first",
        "phase1_check_passed",
        "delivery_manifest_ready",
        "acceptance_report_ready",
        "review_gate_visible",
        "review_priority_queue_visible",
        "real_actions_disabled",
        "assessment_plan_audit_trace_visible",
    }
    assert "delivery/phase1-demo-script-checklist.json" in mock_data["operationsDemoScriptPrototype"]["uses"]
    assert "delivery/DEMO_SCRIPT_CHECKLIST.md" in mock_data["operationsDemoScriptPrototype"]["uses"]
    assert "operationsPresenterPrototype" in mock_data["operationsDemoScriptPrototype"]["uses"]
    assert "auditObservabilityPrototype" in mock_data["operationsDemoScriptPrototype"]["uses"]
    assert "gradingReport.assessmentPlanSummary" in mock_data["operationsDemoScriptPrototype"]["uses"]
    assert "operationAuditEvents.detail.assessmentPlanSummary" in mock_data["operationsDemoScriptPrototype"]["uses"]
    assert "reviewCenterPrototype.reviewPriorityQueue" in mock_data["operationsDemoScriptPrototype"]["uses"]
    assert "GET /api/review-task-summary" in mock_data["operationsDemoScriptPrototype"]["uses"]
    assert "mcp-server/tools.manifest.json.get_review_task_summary.outputContract" in mock_data["operationsDemoScriptPrototype"]["uses"]
    assert "start .\\frontend\\operations-presenter.html" in mock_data["operationsDemoScriptPrototype"]["safeCommands"]
    assert "start .\\frontend\\operations-signoff.html" in mock_data["operationsDemoScriptPrototype"]["safeCommands"]
    assert "start .\\frontend\\operations-demo-script.html" in mock_data["operationsDemoScriptPrototype"]["safeCommands"]
    assert "python lab_cli.py phase1 check" in mock_data["operationsDemoScriptPrototype"]["safeCommands"]
    assert "python lab_cli.py review batch-summary" in mock_data["operationsDemoScriptPrototype"]["safeCommands"]
    assert "python lab_cli.py mcp call --tool get_review_task_summary --arguments \"{}\"" in mock_data["operationsDemoScriptPrototype"]["safeCommands"]
    assert "python -m pytest tests/test_backend_mock_api.py tests/test_mcp_mock_tools.py tests/test_cli.py" in mock_data["operationsDemoScriptPrototype"]["safeCommands"]
    assert "python -m pytest tests/test_demo_script_checklist.py" in mock_data["operationsDemoScriptPrototype"]["safeCommands"]
    assert all(
        (ROOT / step["evidencePath"]).exists()
        for step in mock_data["operationsDemoScriptPrototype"]["demoSteps"]
        if step.get("evidencePath")
    )
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["viewDemoScriptSummaryEnabled"] is True
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["openLinkedStaticPageEnabled"] is True
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["copySafeCommandEnabled"] is True
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["runCommandEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["uploadPackageEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["batchStateChangeEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["startRealAgentEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["createRealCloudResourceEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["runRealSandboxEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["executeContestantCodeEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["secretDisplayEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["actionPolicy"]["remoteUploadEnabled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["readOnly"] is True
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["realMcpServerStarted"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["secretsRead"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["networkAccess"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["realCloudResourceCreated"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["unknownShellExecuted"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["realPublish"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["remoteUploadAllowed"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["operationsDemoScriptPrototype"]["safety"]["answerVisibleToCandidate"] is False
    assert mock_data["operationsPresenterPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["operationsPresenterPrototype"]["summary"]["presenterSectionTotal"] == len(
        mock_data["operationsPresenterPrototype"]["presenterSections"]
    )
    assert mock_data["operationsPresenterPrototype"]["summary"]["demoStepTotal"] == len(
        mock_data["operationsPresenterPrototype"]["speakerTimeline"]
    )
    assert mock_data["operationsPresenterPrototype"]["summary"]["speakerCueTotal"] == len(
        [step for step in mock_data["operationsPresenterPrototype"]["speakerTimeline"] if step["speakerCue"]]
    )
    assert mock_data["operationsPresenterPrototype"]["summary"]["acceptanceSignalTotal"] == len(
        mock_data["operationsPresenterPrototype"]["acceptanceSignals"]
    )
    assert mock_data["operationsPresenterPrototype"]["summary"]["blockedActionTotal"] == len(
        mock_data["operationsPresenterPrototype"]["blockedActions"]
    )
    assert mock_data["operationsPresenterPrototype"]["summary"]["safeCommandTotal"] == len(
        mock_data["operationsPresenterPrototype"]["safeCommands"]
    )
    assert mock_data["operationsPresenterPrototype"]["summary"]["deliveryReady"] == 175
    assert mock_data["operationsPresenterPrototype"]["summary"]["deliveryRequired"] == 175
    assert mock_data["operationsPresenterPrototype"]["summary"]["phase1CheckTotal"] == 20
    assert mock_data["operationsPresenterPrototype"]["summary"]["phase1CheckPassed"] == 20
    assert {section["id"] for section in mock_data["operationsPresenterPrototype"]["presenterSections"]} == {
        "opening",
        "navigation",
        "validation",
        "acceptance_delivery_audit",
        "safety_close",
    }
    assert {step["id"] for step in mock_data["operationsPresenterPrototype"]["speakerTimeline"]} == {
        "read_rules",
        "open_launchpad",
        "open_demo_map",
        "open_runbook",
        "run_phase1_check",
        "export_delivery_package",
        "render_acceptance_report",
        "open_acceptance",
        "open_delivery",
        "open_incident_review",
        "validate_cli_review_priority_queue",
        "validate_backend_mcp_review_priority_queue",
        "confirm_review_gate",
        "confirm_blocked_actions",
    }
    assert [step["order"] for step in mock_data["operationsPresenterPrototype"]["speakerTimeline"]] == list(range(1, 15))
    assert all(step["speakerCue"] for step in mock_data["operationsPresenterPrototype"]["speakerTimeline"])
    assert "operationsDemoScriptPrototype" in mock_data["operationsPresenterPrototype"]["uses"]
    assert "delivery/phase1-demo-script-checklist.json" in mock_data["operationsPresenterPrototype"]["uses"]
    assert "delivery/DEMO_SCRIPT_CHECKLIST.md" in mock_data["operationsPresenterPrototype"]["uses"]
    assert "auditObservabilityPrototype" in mock_data["operationsPresenterPrototype"]["uses"]
    assert "gradingReport.assessmentPlanSummary" in mock_data["operationsPresenterPrototype"]["uses"]
    assert "operationAuditEvents.detail.assessmentPlanSummary" in mock_data["operationsPresenterPrototype"]["uses"]
    assert "reviewCenterPrototype.reviewPriorityQueue" in mock_data["operationsPresenterPrototype"]["uses"]
    assert "GET /api/review-task-summary" in mock_data["operationsPresenterPrototype"]["uses"]
    assert "mcp-server/tools.manifest.json.get_review_task_summary.outputContract" in mock_data["operationsPresenterPrototype"]["uses"]
    assert "realDemoPrototype.coreBusinessDemoPath" in mock_data["operationsPresenterPrototype"]["uses"]
    assert "realDemoPrototype.realDemoAcceptanceSummary" in mock_data["operationsPresenterPrototype"]["uses"]
    presenter_core_path = mock_data["operationsPresenterPrototype"]["coreBusinessDemoPathSignal"]
    assert presenter_core_path["component"] == "CoreBusinessDemoPath"
    assert presenter_core_path["source"] == "realDemoPrototype.coreBusinessDemoPath"
    assert presenter_core_path["bundlePath"] == "examples/output/real-llm-demo-bundle.json"
    assert presenter_core_path["route"] == "/real-demo -> /review-center -> /ppt/:id/review -> /grading/:id/report"
    assert presenter_core_path["stepTotal"] == 6
    assert presenter_core_path["dslValidatedTotal"] == 4
    assert presenter_core_path["waitingReviewDslTotal"] == 4
    assert presenter_core_path["readonlyEvidenceDemoExecuted"] is True
    assert presenter_core_path["readonlyEvidenceDemoEarnedScore"] == 70
    assert presenter_core_path["reviewCenterLinked"] is True
    assert presenter_core_path["pptPageReviewActionVisible"] is True
    assert presenter_core_path["reviewRequiredBeforePublish"] is True
    assert presenter_core_path["autoApproveAllowed"] is False
    assert presenter_core_path["autoPublishAllowed"] is False
    assert presenter_core_path["realPublish"] is False
    presenter_acceptance = mock_data["operationsPresenterPrototype"]["realDemoAcceptanceSummarySignal"]
    assert presenter_acceptance["component"] == "RealDemoAcceptanceSummary"
    assert presenter_acceptance["source"] == "realDemoPrototype.realDemoAcceptanceSummary"
    assert presenter_acceptance["summaryPath"] == "examples/output/real-llm-demo-acceptance-summary.json"
    assert presenter_acceptance["bundlePath"] == "examples/output/real-llm-demo-bundle.json"
    assert presenter_acceptance["route"] == "/real-demo -> /review-center -> /ppt/:id/review -> /grading/:id/report"
    assert presenter_acceptance["acceptancePassed"] is True
    assert presenter_acceptance["passedCount"] == 7
    assert presenter_acceptance["total"] == 7
    assert presenter_acceptance["failedStepIds"] == []
    assert presenter_acceptance["mcpOutputContractIncludesRealDemoReviewQueue"] is True
    assert presenter_acceptance["readonlyEvidenceCollectedTotal"] == 2
    assert presenter_acceptance["readonlyEvidenceDemoEarnedScore"] == 70
    assert presenter_acceptance["pptPageReviewActionVisible"] is True
    assert presenter_acceptance["candidatePreviewAnswerSafe"] is True
    assert presenter_acceptance["newLlmRequestSent"] is False
    assert presenter_acceptance["secretsRead"] is False
    assert presenter_acceptance["networkAccess"] is False
    assert presenter_acceptance["batchStateChangeAllowed"] is False
    assert presenter_acceptance["realPublishAllowed"] is False
    assert {
        signal["id"] for signal in mock_data["operationsPresenterPrototype"]["acceptanceSignals"]
    } == {
        "launchpad_first",
        "phase1_check_passed",
        "delivery_manifest_ready",
        "acceptance_report_ready",
        "review_gate_visible",
        "review_priority_queue_visible",
        "real_actions_disabled",
        "assessment_plan_audit_trace_visible",
    }
    assert "start .\\frontend\\operations-presenter.html" in mock_data["operationsPresenterPrototype"]["safeCommands"]
    assert "start .\\frontend\\operations-signoff.html" in mock_data["operationsPresenterPrototype"]["safeCommands"]
    assert "start .\\frontend\\operations-demo-script.html" in mock_data["operationsPresenterPrototype"]["safeCommands"]
    assert "python lab_cli.py phase1 check" in mock_data["operationsPresenterPrototype"]["safeCommands"]
    assert "python lab_cli.py review batch-summary" in mock_data["operationsPresenterPrototype"]["safeCommands"]
    assert "python lab_cli.py mcp call --tool get_review_task_summary --arguments \"{}\"" in mock_data["operationsPresenterPrototype"]["safeCommands"]
    assert "python -m pytest tests/test_backend_mock_api.py tests/test_mcp_mock_tools.py tests/test_cli.py" in mock_data["operationsPresenterPrototype"]["safeCommands"]
    assert "python -m pytest tests/test_frontend_manifest.py" in mock_data["operationsPresenterPrototype"]["safeCommands"]
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["viewPresenterSummaryEnabled"] is True
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["openLinkedStaticPageEnabled"] is True
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["copySafeCommandEnabled"] is True
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["runCommandEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["uploadPackageEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["batchStateChangeEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["startRealAgentEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["createRealCloudResourceEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["runRealSandboxEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["executeContestantCodeEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["secretDisplayEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["actionPolicy"]["remoteUploadEnabled"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["readOnly"] is True
    assert mock_data["operationsPresenterPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["realMcpServerStarted"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["secretsRead"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["networkAccess"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["realCloudResourceCreated"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["unknownShellExecuted"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["realPublish"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["remoteUploadAllowed"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["operationsPresenterPrototype"]["safety"]["answerVisibleToCandidate"] is False
    assert mock_data["operationsLaunchpadPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["operationsLaunchpadPrototype"]["summary"]["entryCardTotal"] == len(
        mock_data["operationsLaunchpadPrototype"]["entryCards"]
    )
    assert mock_data["operationsLaunchpadPrototype"]["summary"]["validationCommandTotal"] == len(
        mock_data["operationsLaunchpadPrototype"]["validationCommands"]
    )
    assert mock_data["operationsLaunchpadPrototype"]["summary"]["handoffNoteTotal"] == len(
        mock_data["operationsLaunchpadPrototype"]["handoffNotes"]
    )
    assert mock_data["operationsLaunchpadPrototype"]["summary"]["deliveryReady"] == 175
    assert mock_data["operationsLaunchpadPrototype"]["summary"]["deliveryRequired"] == 175
    assert {card["route"] for card in mock_data["operationsLaunchpadPrototype"]["entryCards"]} == {
        "/console",
        "/operations/demo-map",
        "/operations/presenter",
        "/operations/signoff",
        "/operations/demo-script",
        "/operations/runbook",
        "/operations/acceptance",
        "/delivery",
        "/audit",
        "/review-center",
    }
    assert all((ROOT / card["path"]).exists() for card in mock_data["operationsLaunchpadPrototype"]["entryCards"])
    assert "frontend/ui.manifest.json" in mock_data["operationsLaunchpadPrototype"]["uses"]
    assert "frontend/mock-data.json" in mock_data["operationsLaunchpadPrototype"]["uses"]
    assert "start .\\frontend\\operations-launchpad.html" in mock_data["operationsLaunchpadPrototype"]["validationCommands"]
    assert "start .\\frontend\\operations-presenter.html" in mock_data["operationsLaunchpadPrototype"]["validationCommands"]
    assert "start .\\frontend\\operations-signoff.html" in mock_data["operationsLaunchpadPrototype"]["validationCommands"]
    assert "start .\\frontend\\operations-demo-script.html" in mock_data["operationsLaunchpadPrototype"]["validationCommands"]
    assert "python lab_cli.py phase1 check" in mock_data["operationsLaunchpadPrototype"]["validationCommands"]
    assert "python -m pytest" in mock_data["operationsLaunchpadPrototype"]["validationCommands"]
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["openStaticPageEnabled"] is True
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["copySafeCommandEnabled"] is True
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["viewDeliveryEnabled"] is True
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["runCommandEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["uploadPackageEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["batchStateChangeEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["startRealAgentEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["createRealCloudResourceEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["runRealSandboxEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["executeContestantCodeEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["secretDisplayEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["actionPolicy"]["remoteUploadEnabled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["readOnly"] is True
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["realMcpServerStarted"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["secretsRead"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["networkAccess"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["realCloudResourceCreated"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["unknownShellExecuted"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["realPublish"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["remoteUploadAllowed"] is False
    assert mock_data["operationsLaunchpadPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["deliveryPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["deliveryPrototype"]["reportCommand"] == (
        "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json "
        "--output examples/output/phase1-acceptance-report.md"
    )
    assert mock_data["deliveryPrototype"]["summary"]["deliverableTotal"] == 175
    assert (
        mock_data["deliveryPrototype"]["summary"]["deliverableTotal"]
        == mock_data["deliveryPrototype"]["summary"]["requiredTotal"]
        == mock_data["deliveryPrototype"]["summary"]["readyTotal"]
    )
    assert mock_data["deliveryPrototype"]["summary"]["missingRequired"] == 0
    assert mock_data["deliveryPrototype"]["summary"]["acceptancePassed"] is True
    assert mock_data["deliveryPrototype"]["summary"]["safetyAssertionsPassed"] is True
    assert mock_data["deliveryPrototype"]["summary"]["phase1CheckTotal"] == 20
    assert mock_data["deliveryPrototype"]["summary"]["phase1CheckPassed"] == 20
    assert mock_data["deliveryPrototype"]["deliveryManifest"]["missingRequired"] == 0
    assert "frontend_console_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_audit_observability_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_audit_detail_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_audit_incident_review_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_operations_launchpad_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_operations_runbook_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_operations_acceptance_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_operations_demo_map_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_operations_presenter_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_operations_signoff_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_operations_demo_script_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "real_provider_shell" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "real_provider_shell_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "real_llm_poc_adapter" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "real_llm_poc_adapter_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "real_llm_dry_run_plan" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "real_llm_dry_run_plan_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "real_llm_approval_gate" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "real_llm_approval_gate_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_delivery_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_ppt_review_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "delivery_index_readme" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "delivery_index_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "delivery_faq_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "delivery_faq_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "delivery_handoff_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "delivery_handoff_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "demo_script_checklist_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "demo_script_checklist_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "phase2_readiness_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "phase2_readiness_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "phase2_provider_plan_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "phase2_provider_plan_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "provider_adapter" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "real_provider_gate" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "real_provider_gate_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "provider_adapter_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "provider_adapter_errors_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "provider_call_audit_model" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "provider_audit_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "provider_audit_workflow_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "provider_adapter_workflow_helper" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "mcp_mock_tools" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "mcp_tool_call_audit_model" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "mcp_tool_call_audit_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "high_risk_mcp_safety_matrix" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "high_risk_mcp_handoff_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "high_risk_mcp_handoff_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "final_signoff_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "final_signoff_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "operations_manual_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "operations_manual_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "operations_skill_pack_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "operations_skill_pack_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "standalone_agent_delivery_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "standalone_agent_delivery_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "frontend_access_entrypoints_prototype" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "access_entrypoints_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "access_entrypoints_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "phase5_mock_baseline_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "phase5_mock_baseline_contract" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "mcp_mock_tools_tests" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "scripts_phase1_demo_runbook_json" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert "scripts_phase1_demo_runbook_md" in mock_data["deliveryPrototype"]["deliveryManifest"]["trackedDeliverableIds"]
    assert mock_data["deliveryPrototype"]["acceptanceSummary"]["passed"] is True
    assert mock_data["deliveryPrototype"]["acceptanceSummary"]["requiredPassed"] == 14
    assert mock_data["deliveryPrototype"]["acceptanceSummary"]["readyForPhase2MockHandoff"] is True
    assert all(item["passed"] is True for item in mock_data["deliveryPrototype"]["acceptanceChecklist"])
    assert "core_deliverables_present" in {item["id"] for item in mock_data["deliveryPrototype"]["acceptanceChecklist"]}
    assert "phase1_demo_runbook_present" in {item["id"] for item in mock_data["deliveryPrototype"]["acceptanceChecklist"]}
    assert "demo_script_checklist_present" in {item["id"] for item in mock_data["deliveryPrototype"]["acceptanceChecklist"]}
    assert all(
        assertion["passed"] is True and assertion["actual"] is False
        for assertion in mock_data["deliveryPrototype"]["safetyAssertions"]
    )
    assert mock_data["deliveryPrototype"]["actionPolicy"]["uploadPackageEnabled"] is False
    assert mock_data["deliveryPrototype"]["actionPolicy"]["realPublishEnabled"] is False
    assert mock_data["deliveryPrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["deliveryPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["deliveryPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["deliveryPrototype"]["safety"]["realCloudResourceCreated"] is False
    assert mock_data["deliveryPrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["deliveryPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["deliveryPrototype"]["safety"]["contestantCodeExecuted"] is False
    assert mock_data["deliveryPrototype"]["safety"]["unknownShellExecuted"] is False
    assert mock_data["deliveryPrototype"]["safety"]["autoPublishAllowed"] is False
    assert mock_data["deliveryPrototype"]["safety"]["realPublish"] is False
    assert mock_data["deliveryPrototype"]["safety"]["remoteUploadAllowed"] is False
    assert mock_data["deliveryPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["environmentManagementPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["environmentManagementPrototype"]["summary"]["environmentTotal"] == len(mock_data["environments"])
    assert mock_data["environmentManagementPrototype"]["summary"]["vmTotal"] == 1
    assert mock_data["environmentManagementPrototype"]["summary"]["notebookTotal"] == 1
    assert mock_data["environmentManagementPrototype"]["summary"]["runningTotal"] == 1
    assert mock_data["environmentManagementPrototype"]["actionPolicy"]["createVmMockEnabled"] is True
    assert mock_data["environmentManagementPrototype"]["actionPolicy"]["createNotebookMockEnabled"] is True
    assert mock_data["environmentManagementPrototype"]["actionPolicy"]["realCloudCreateEnabled"] is False
    assert mock_data["environmentManagementPrototype"]["actionPolicy"]["realCloudStartEnabled"] is False
    assert mock_data["environmentManagementPrototype"]["actionPolicy"]["destroyRealResourceEnabled"] is False
    assert mock_data["environmentManagementPrototype"]["safety"]["realCloudResourceCreated"] is False
    assert mock_data["environmentManagementPrototype"]["safety"]["realCloudResourceChanged"] is False
    assert mock_data["environmentManagementPrototype"]["safety"]["sandboxExecuted"] is False
    assert mock_data["environmentManagementPrototype"]["safety"]["destroyRealResourceAllowed"] is False
    assert mock_data["environmentManagementPrototype"]["safety"]["secretVisibleInFrontend"] is False
    assert mock_data["skillManagementPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["skillManagementPrototype"]["summary"]["skillTotal"] == len(mock_data["skills"])
    assert mock_data["skillManagementPrototype"]["summary"]["promptTotal"] == 4
    assert mock_data["skillManagementPrototype"]["summary"]["outputKindTotal"] == 4
    assert mock_data["skillManagementPrototype"]["summary"]["reviewRequiredTotal"] == 4
    assert set(mock_data["skillManagementPrototype"]["outputKinds"]) == {"Lab", "Exam", "Grading", "PPT"}
    assert mock_data["skillManagementPrototype"]["actionPolicy"]["viewSkillManifestEnabled"] is True
    assert mock_data["skillManagementPrototype"]["actionPolicy"]["realAgentStartEnabled"] is False
    assert mock_data["skillManagementPrototype"]["actionPolicy"]["realLlmCallEnabled"] is False
    assert mock_data["skillManagementPrototype"]["actionPolicy"]["promptEmbedInBusinessCodeEnabled"] is False
    assert mock_data["skillManagementPrototype"]["actionPolicy"]["autoPublishEnabled"] is False
    assert mock_data["skillManagementPrototype"]["safety"]["realAgentStarted"] is False
    assert mock_data["skillManagementPrototype"]["safety"]["realLlmCalled"] is False
    assert mock_data["skillManagementPrototype"]["safety"]["businessCodeMayEmbedPrompts"] is False
    assert mock_data["skillManagementPrototype"]["safety"]["outputMustBeDsl"] is True
    assert mock_data["skillManagementPrototype"]["safety"]["generatedContentDefaultStatus"] == "WAITING_REVIEW"
    assert mock_data["skillManagementPrototype"]["safety"]["publishBlockedUntilApproved"] is True
    assert mock_data["providerSettingsPrototype"]["mode"] == "MOCK_ONLY"
    assert mock_data["providerSettingsPrototype"]["summary"]["activeProvider"] == "mock"
    assert mock_data["providerSettingsPrototype"]["summary"]["enabledProviderTotal"] == 1
    assert mock_data["providerSettingsPrototype"]["summary"]["disabledRealProviderTotal"] == 3
    assert mock_data["providerSettingsPrototype"]["summary"]["secretsRead"] is False
    assert mock_data["providerSettingsPrototype"]["summary"]["networkAccess"] is False
    assert mock_data["providerSettingsPrototype"]["summary"]["secretVisibleInFrontend"] is False
    assert mock_data["providerSettingsPrototype"]["actionPolicy"]["viewProviderListEnabled"] is True
    assert mock_data["providerSettingsPrototype"]["actionPolicy"]["viewMockHealthEnabled"] is True
    assert mock_data["providerSettingsPrototype"]["actionPolicy"]["mockGenerateEnabled"] is True
    assert mock_data["providerSettingsPrototype"]["actionPolicy"]["enableRealProviderEnabled"] is False
    assert mock_data["providerSettingsPrototype"]["actionPolicy"]["callRealLlmEnabled"] is False
    assert mock_data["providerSettingsPrototype"]["actionPolicy"]["revealApiKeyEnabled"] is False
    assert mock_data["providerSettingsPrototype"]["actionPolicy"]["persistSecretEnabled"] is False
    assert mock_data["providerSettingsPrototype"]["runtimeGuards"]["envExamplePath"] == ".env.example"
    assert mock_data["providerSettingsPrototype"]["runtimeGuards"]["enableRealLlm"] is False
    assert mock_data["providerSettingsPrototype"]["runtimeGuards"]["enableRealCloud"] is False
    assert mock_data["providerSettingsPrototype"]["runtimeGuards"]["enableRealSandbox"] is False
    assert mock_data["providerSettingsPrototype"]["runtimeGuards"]["enableAutoPublish"] is False
    assert mock_data["providerSettingsPrototype"]["runtimeGuards"]["apiKeysFromEnvironmentOnly"] is True
    assert mock_data["providerSettingsPrototype"]["safety"]["realProviderEnabled"] is False
    assert mock_data["providerSettingsPrototype"]["safety"]["businessCodeMayEmbedPrompts"] is False
    assert mock_data["reviewDetail"]["mode"] == "MOCK_ONLY"
    assert mock_data["reviewDetail"]["reviewPolicy"]["rejectRequiresReason"] is True
    assert mock_data["reviewDetail"]["reviewPolicy"]["publishBlockedUntilApproved"] is True
    assert mock_data["reviewDetail"]["reviewPolicy"]["autoPublishAllowed"] is False
    assert mock_data["reviewDetail"]["safety"]["realPublish"] is False
    assert mock_data["reviewDetail"]["safety"]["answerVisibleToCandidate"] is False
    assert mock_data["reviewDetail"]["reviewPage"]["dslPreview"]["artifactKind"] == "LAB_DSL"
    assert mock_data["reviewDetail"]["reviewPage"]["actionBar"]["approve"]["enabled"] is True
    assert mock_data["reviewDetail"]["reviewPage"]["actionBar"]["requestRevision"]["enabled"] is True
    assert mock_data["reviewDetail"]["reviewPage"]["actionBar"]["requestRevision"]["triggersLlm"] is False
    assert mock_data["reviewDetail"]["reviewPage"]["actionBar"]["mockPublish"]["enabled"] is False
    assert mock_data["reviewDetail"]["reviewPage"]["revisionRequests"]["total"] == 1
    assert mock_data["reviewDetail"]["reviewPage"]["revisionRequests"]["highPriorityCount"] == 1
    assert mock_data["reviewDetail"]["reviewPage"]["riskSummary"]["answerVisibleToCandidate"] is False
    revision = mock_data["reviewRevisionPrototype"]
    assert revision["sourceTaskId"] == "task_lab_demo"
    assert revision["sourceTaskStatusUnchanged"] is True
    assert revision["revisionRequestApi"] == "POST /api/review-tasks/{id}/revision-request"
    assert revision["revisionListApi"] == "GET /api/review-tasks/{id}/revision-requests"
    assert revision["mockRegenerationApi"] == "POST /api/review-tasks/{id}/regenerate-mock"
    assert revision["revisionRequests"][0]["taskStatusChanged"] is False
    assert revision["revisionRequests"][0]["newLlmRequestSent"] is False
    assert revision["mockRegenerationAction"]["enabled"] is True
    assert revision["mockRegenerationAction"]["newTaskStatus"] == "WAITING_REVIEW"
    assert revision["mockRegenerationAction"]["sourceTaskStatusUnchanged"] is True
    assert revision["mockRegenerationAction"]["realLlmCalled"] is False
    assert revision["mockRegenerationAction"]["newLlmRequestSent"] is False
    assert revision["mockRegenerationAction"]["autoApproveAllowed"] is False
    assert revision["mockRegenerationAction"]["realPublishAllowed"] is False
    assert revision["safety"]["newTaskWaitingReview"] is True
    assert revision["safety"]["realPublish"] is False
    assert mock_data["reviewCenterPrototype"]["assessmentPlanQueueSignal"]["enabled"] is True
    assert mock_data["reviewCenterPrototype"]["assessmentPlanQueueSignal"]["source"] == "gradingReviewPrototype.assessmentPlanSummary"
    assert mock_data["reviewCenterPrototype"]["assessmentPlanQueueSignal"]["backendSource"] == "GET /api/review-tasks/{id}.reviewDetail.assessmentPlan.summary"
    assert mock_data["reviewCenterPrototype"]["assessmentPlanQueueSignal"]["visibleForTaskTypes"] == ["GRADING_GENERATION"]
    assert mock_data["reviewCenterPrototype"]["assessmentPlanQueueSignal"]["planTotal"] == 1
    assert mock_data["reviewCenterPrototype"]["assessmentPlanQueueSignal"]["alignedWithChecks"] is True
    assert mock_data["reviewCenterPrototype"]["assessmentPlanQueueSignal"]["riskLevels"] == ["high"]
    assert mock_data["reviewCenterPrototype"]["assessmentPlanQueueSignal"]["mockEvidenceStatuses"] == ["MOCK_EVIDENCE_NOT_COLLECTED"]
    assert mock_data["reviewCenterPrototype"]["assessmentPlanQueueSignal"]["realSandboxEvidenceRequired"] is True
    manual_queue_signal = mock_data["reviewCenterPrototype"]["assessmentPlanManualReviewQueueSignal"]
    assert manual_queue_signal["enabled"] is True
    assert manual_queue_signal["source"] == "reviewCenterPrototype.reviewPriorityQueue.items[0].manualReviewChecklistSummary"
    assert (
        manual_queue_signal["backendSource"]
        == "GET /api/review-task-summary.reviewTaskSummary.reviewPriorityQueue.items[].manualReviewChecklistSummary"
    )
    assert (
        manual_queue_signal["mcpSource"]
        == "get_review_task_summary.outputContract.reviewPriorityQueue.manualReviewChecklistSummary"
    )
    assert manual_queue_signal["visibleForTaskTypes"] == ["GRADING_GENERATION"]
    assert manual_queue_signal["checklistTotal"] == 5
    assert manual_queue_signal["matchedTotal"] == 5
    assert manual_queue_signal["needsHumanReviewTotal"] == 5
    assert manual_queue_signal["nextReviewChecklistIds"] == [
        "verify_assessment_plan_aligned_with_checks",
        "confirm_mock_evidence_not_collected",
        "confirm_real_sandbox_evidence_required_before_real_execution",
        "verify_required_limits_present",
        "confirm_no_execution_or_publish",
    ]
    assert manual_queue_signal["autoApproveAllowed"] is False
    assert manual_queue_signal["batchStateChangeAllowed"] is False
    assert manual_queue_signal["realSandboxRunEnabled"] is False
    assert manual_queue_signal["realPublishAllowed"] is False
    grading_queue_item = next(
        item for item in mock_data["reviewTaskSummary"]["items"] if item["task"]["taskType"] == "GRADING_GENERATION"
    )
    assert grading_queue_item["reviewPageSummary"]["dslPreview"]["assessmentPlanTotal"] == 1
    assert grading_queue_item["reviewPageSummary"]["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert grading_queue_item["reviewPageSummary"]["assessmentPlanSummary"]["riskLevels"] == ["high"]
    assert grading_queue_item["reviewPageSummary"]["assessmentPlanSummary"]["realSandboxEvidenceRequired"] is True
    assert mock_data["reviewAuditEvents"][0]["mode"] == "MOCK_ONLY"
    assert mock_data["reviewAuditEvents"][0]["realPublish"] is False
    for event in mock_data["operationAuditEvents"]:
        assert event["mode"] == "MOCK_ONLY"
        assert event["realLlmCalled"] is False
        assert event["realCloudResourceChanged"] is False
        assert event["contestantCodeExecuted"] is False
        assert event["realPublish"] is False
    operation_events_by_action = {event["action"]: event for event in mock_data["operationAuditEvents"]}
    assert {
        "PUBLISH_LAB_INTENT",
        "PUBLISH_EXAM_INTENT",
        "DESTROY_ENVIRONMENT_INTENT",
    } <= set(operation_events_by_action)
    assert operation_events_by_action["PUBLISH_LAB_INTENT"]["detail"]["reviewIntentOnly"] is True
    assert operation_events_by_action["PUBLISH_LAB_INTENT"]["detail"]["executeRealPublishEnabled"] is False
    assert operation_events_by_action["PUBLISH_LAB_INTENT"]["detail"]["postReviewDispositionState"] == "WAITING_HUMAN_REVIEW"
    assert operation_events_by_action["PUBLISH_EXAM_INTENT"]["detail"]["realPublish"] is False
    assert (
        operation_events_by_action["PUBLISH_EXAM_INTENT"]["detail"]["postReviewDispositionState"]
        == "APPROVED_EXECUTION_BLOCKED"
    )
    destroy_audit_detail = operation_events_by_action["DESTROY_ENVIRONMENT_INTENT"]["detail"]
    assert destroy_audit_detail["reviewIntentOnly"] is True
    assert destroy_audit_detail["requiresSecondConfirmation"] is True
    assert destroy_audit_detail["postReviewDispositionState"] == "APPROVED_PENDING_SECOND_CONFIRMATION"
    assert destroy_audit_detail["secondConfirmationSatisfied"] is False
    assert destroy_audit_detail["destroyRealEnvironmentEnabled"] is False
    assert destroy_audit_detail["realCloudResourceChanged"] is False
    assert destroy_audit_detail["environmentDestroyed"] is False
    grading_audit_event = next(event for event in mock_data["operationAuditEvents"] if event["action"] == "MOCK_GRADING_RUN")
    grading_audit_detail = grading_audit_event["detail"]
    assert grading_audit_detail["phase"] == "Phase 3"
    assert grading_audit_detail["runner"]["id"] == "mock_grading_runner"
    assert grading_audit_detail["checkSummary"]["executed"] == 0
    assert grading_audit_detail["checkSummary"]["plannedOnly"] == 6
    assert grading_audit_detail["checkSummary"]["byType"] == {
        "file_exists": 1,
        "stdout_contains": 1,
        "pytest": 1,
        "notebook_cell": 1,
        "json_field": 1,
        "log_keyword": 1,
    }
    assert grading_audit_detail["assessmentPlanSummary"]["source"] == "grading.spec.assessmentPlan"
    assert grading_audit_detail["assessmentPlanSummary"]["planTotal"] == 6
    assert grading_audit_detail["assessmentPlanSummary"]["checkTotal"] == 6
    assert grading_audit_detail["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert grading_audit_detail["assessmentPlanSummary"]["missingPlanForChecks"] == []
    assert grading_audit_detail["assessmentPlanSummary"]["orphanPlanCheckIds"] == []
    assert grading_audit_detail["assessmentPlanSummary"]["executionStrategies"] == ["MOCK_PLAN_ONLY"]
    assert grading_audit_detail["assessmentPlanSummary"]["mockEvidenceStatuses"] == ["MOCK_EVIDENCE_NOT_COLLECTED"]
    assert grading_audit_detail["assessmentPlanSummary"]["riskLevels"] == ["high", "low", "medium"]
    assert grading_audit_detail["assessmentPlanSummary"]["realSandboxEvidenceRequired"] is True
    assert grading_audit_detail["assessmentPlanSummary"]["sandboxRequiredBeforeRealExecution"] is True
    assert [plan["type"] for plan in grading_audit_detail["checkPlans"]] == SUPPORTED_GRADING_CHECK_TYPES
    assert all(plan["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for plan in grading_audit_detail["checkPlans"])
    assert all(plan["commandExecuted"] is False for plan in grading_audit_detail["checkPlans"])
    assert all(plan["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY" for plan in grading_audit_detail["checkPlans"])
    assert all(
        plan["containerSandboxPlan"]["containerPlan"]["image"] == "python:3.11-slim"
        for plan in grading_audit_detail["checkPlans"]
    )
    assert all(
        plan["containerSandboxPlan"]["resultPlaceholder"]["status"] == "NOT_EXECUTED"
        for plan in grading_audit_detail["checkPlans"]
    )
    assert grading_audit_detail["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert grading_audit_detail["sandboxPolicy"]["hostExecutionAllowed"] is False
    assert grading_audit_detail["sandboxPolicy"]["networkAccess"] == "disabled_by_default"
    assert grading_audit_detail["explainability"]["status"] == "EXPLAINABLE_MOCK_PLAN"
    assert grading_audit_detail["explainability"]["eachCheckHasInputSummary"] is True
    assert grading_audit_detail["explainability"]["eachCheckHasMockEvidence"] is True
    assert grading_audit_detail["explainability"]["assessmentPlanSource"] == "grading.spec.assessmentPlan"
    assert grading_audit_detail["explainability"]["assessmentPlanAlignedWithChecks"] is True
    assert all(plan["inputSummary"] for plan in grading_audit_detail["checkPlans"])
    assert all(plan["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED" for plan in grading_audit_detail["checkPlans"])
    assert all(plan["assessmentPlanSource"] == "grading.spec.assessmentPlan" for plan in grading_audit_detail["checkPlans"])
    assert all(
        plan["assessmentPlanSourceField"].startswith("spec.assessmentPlan[checkId=")
        for plan in grading_audit_detail["checkPlans"]
    )
    assert all(plan["assessmentPlanAlignedWithCheck"] is True for plan in grading_audit_detail["checkPlans"])
    assert all(plan["assessmentPlanExecutionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for plan in grading_audit_detail["checkPlans"])
    assert all(
        plan["assessmentPlanMockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED"
        for plan in grading_audit_detail["checkPlans"]
    )
    assert all(plan["assessmentPlanSandboxRequiredBeforeRealExecution"] is True for plan in grading_audit_detail["checkPlans"])
    assert all("requiredLimits" in plan["executionPlan"] for plan in grading_audit_detail["checkPlans"])
    assert "runRealPytest" in grading_audit_detail["blockedActions"]
    assert grading_audit_detail["runRealPytestEnabled"] is False
    assert grading_audit_detail["hostExecutionAllowed"] is False
    for artifact in mock_data["artifacts"]:
        assert artifact["mode"] == "MOCK_ONLY"
        assert artifact["realLlmCalled"] is False
        assert artifact["realCloudResourceChanged"] is False
        assert artifact["sandboxExecuted"] is False
        assert artifact["contestantCodeExecuted"] is False
        assert artifact["realPublish"] is False
    for run in mock_data["workflowRuns"]:
        assert run["mode"] == "MOCK_ONLY"
        assert run["reviewRequired"] is True
        assert run["publishBlockedUntilApproved"] is True
        assert run["realLlmCalled"] is False
        assert run["realCloudResourceChanged"] is False
        assert run["sandboxExecuted"] is False
        assert run["contestantCodeExecuted"] is False
        assert run["realPublish"] is False
        assert [step["order"] for step in run["steps"]] == list(range(1, len(run["steps"]) + 1))
    assert mock_data["dslPreviews"]["exam"]["answerVisibleToCandidate"] is False
    assert mock_data["gradingReport"]["sandboxExecuted"] is False
    assert mock_data["gradingReport"]["contestantCodeExecuted"] is False
    assert mock_data["gradingReport"]["commandExecuted"] is False
    assert mock_data["gradingReport"]["runner"]["id"] == "mock_grading_runner"
    assert mock_data["gradingReport"]["checkSummary"]["executed"] == 0
    assert mock_data["gradingReport"]["checkSummary"]["plannedOnly"] == 6
    assert mock_data["gradingReport"]["checkSummary"]["byType"] == {
        "file_exists": 1,
        "stdout_contains": 1,
        "pytest": 1,
        "notebook_cell": 1,
        "json_field": 1,
        "log_keyword": 1,
    }
    assert mock_data["gradingReport"]["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert mock_data["gradingReport"]["sandboxPolicy"]["hostExecutionAllowed"] is False
    assert mock_data["gradingReport"]["sandboxPolicy"]["realSandboxRunEnabled"] is False
    assert mock_data["gradingReport"]["explainability"]["status"] == "EXPLAINABLE_MOCK_PLAN"
    assert mock_data["gradingReport"]["explainability"]["realSandboxEvidenceRequired"] is True
    assert mock_data["gradingReport"]["explainability"]["assessmentPlanSource"] == "grading.spec.assessmentPlan"
    assert mock_data["gradingReport"]["explainability"]["assessmentPlanAlignedWithChecks"] is True
    assert mock_data["gradingReport"]["assessmentPlanSummary"]["source"] == "grading.spec.assessmentPlan"
    assert mock_data["gradingReport"]["assessmentPlanSummary"]["planTotal"] == 6
    assert mock_data["gradingReport"]["assessmentPlanSummary"]["checkTotal"] == 6
    assert mock_data["gradingReport"]["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert mock_data["gradingReport"]["assessmentPlanSummary"]["missingPlanForChecks"] == []
    assert mock_data["gradingReport"]["assessmentPlanSummary"]["orphanPlanCheckIds"] == []
    assert mock_data["gradingReport"]["assessmentPlanSummary"]["executionStrategies"] == ["MOCK_PLAN_ONLY"]
    assert mock_data["gradingReport"]["assessmentPlanSummary"]["mockEvidenceStatuses"] == ["MOCK_EVIDENCE_NOT_COLLECTED"]
    assert mock_data["gradingReport"]["reportDetail"]["audit"]["action"] == "MOCK_GRADING_RUN"
    assert mock_data["gradingReport"]["reportDetail"]["audit"]["runRealPytestEnabled"] is False
    assert mock_data["gradingReport"]["reportDetail"]["explainability"]["assessmentPlanAlignedWithChecks"] is True
    assert mock_data["gradingReport"]["reportDetail"]["assessmentPlanSummary"] == mock_data["gradingReport"]["assessmentPlanSummary"]
    assert [plan["type"] for plan in mock_data["gradingReport"]["reportDetail"]["checkPlans"]] == SUPPORTED_GRADING_CHECK_TYPES
    assert all(plan["inputSummary"] for plan in mock_data["gradingReport"]["reportDetail"]["checkPlans"])
    assert all(
        plan["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED"
        for plan in mock_data["gradingReport"]["reportDetail"]["checkPlans"]
    )
    assert all(
        plan["assessmentPlanSource"] == "grading.spec.assessmentPlan"
        for plan in mock_data["gradingReport"]["reportDetail"]["checkPlans"]
    )
    assert all(
        plan["assessmentPlanSourceField"].startswith("spec.assessmentPlan[checkId=")
        for plan in mock_data["gradingReport"]["reportDetail"]["checkPlans"]
    )
    assert all(
        plan["assessmentPlanAlignedWithCheck"] is True
        for plan in mock_data["gradingReport"]["reportDetail"]["checkPlans"]
    )
    assert all(
        plan["assessmentPlanExecutionPlan"]["strategy"] == "MOCK_PLAN_ONLY"
        for plan in mock_data["gradingReport"]["reportDetail"]["checkPlans"]
    )
    assert all(
        plan["assessmentPlanMockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED"
        for plan in mock_data["gradingReport"]["reportDetail"]["checkPlans"]
    )
    assert all(
        plan["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY"
        for plan in mock_data["gradingReport"]["reportDetail"]["checkPlans"]
    )
    assert all(
        plan["containerSandboxPlan"]["containerPlan"]["mounts"][0]["mode"] == "read_only"
        for plan in mock_data["gradingReport"]["reportDetail"]["checkPlans"]
    )
    assert all(
        plan["containerSandboxPlan"]["safety"]["commandExecuted"] is False
        for plan in mock_data["gradingReport"]["reportDetail"]["checkPlans"]
    )
    assert [check["type"] for check in mock_data["gradingReport"]["checks"]] == SUPPORTED_GRADING_CHECK_TYPES
    assert all(check["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for check in mock_data["gradingReport"]["checks"])
    assert all(check["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY" for check in mock_data["gradingReport"]["checks"])
    assert all(check["commandExecuted"] is False for check in mock_data["gradingReport"]["checks"])
    assert all(check["inputSummary"] for check in mock_data["gradingReport"]["checks"])
    assert all(check["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED" for check in mock_data["gradingReport"]["checks"])
    assert all("requiredLimits" in check["executionPlan"] for check in mock_data["gradingReport"]["checks"])
    assert all(check["assessmentPlanAlignedWithCheck"] is True for check in mock_data["gradingReport"]["checks"])
    for environment in mock_data["environments"]:
        assert environment["provider"] == "mock"
        assert environment["realCloudResourceCreated"] is False
        assert environment["realCloudResourceChanged"] is False
        assert environment["sandboxExecuted"] is False
        assert environment["contestantCodeExecuted"] is False
    for skill in mock_data["skills"]:
        assert skill["mode"] == "MOCK_ONLY"
        assert skill["reviewRequired"] is True
        assert skill["promptPath"].startswith("prompts/")
        assert skill["outputKind"] in {"Lab", "Exam", "Grading", "PPT"}
    assert mock_data["providerSettings"]["secretVisibleInFrontend"] is False
    assert mock_data["providerSettings"]["activeProvider"] == "mock"
    assert mock_data["providerSettings"]["secretsRead"] is False
    assert mock_data["providerSettings"]["networkAccess"] is False
    assert [provider["id"] for provider in mock_data["providerSettings"]["configuredProviders"] if provider["enabled"]] == ["mock"]
    assert all(
        provider["realLlmCalled"] is False and provider["networkAccess"] is False and provider["secretVisibleInFrontend"] is False
        for provider in mock_data["providerSettings"]["configuredProviders"]
    )
    assert [provider["secretEnv"] for provider in mock_data["providerSettings"]["configuredProviders"] if provider["requiresApiKey"]] == [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]
    assert mock_data["providerSettings"]["mockGeneration"]["generatedStatus"] == "WAITING_REVIEW"
    assert mock_data["materialAnalysis"]["mode"] == "MOCK_ONLY"
    assert mock_data["materialAnalysis"]["realLlmCalled"] is False
    assert mock_data["materialAnalysis"]["remoteContentFetched"] is False
    assert mock_data["materialAnalysis"]["unknownShellExecuted"] is False
    assert mock_data["materialAnalysis"]["sandboxExecuted"] is False


def test_frontend_mock_data_references_existing_dsl_paths():
    mock_data = load_json("frontend/mock-data.json")

    for preview in mock_data["dslPreviews"].values():
        assert (ROOT / preview["path"]).exists(), preview["path"]

    assert (ROOT / mock_data["reviewCenterPrototype"]["path"]).exists()
    assert (ROOT / mock_data["labsPrototype"]["path"]).exists()
    for lab in mock_data["labs"]:
        assert (ROOT / lab["dslPath"]).exists()
    assert (ROOT / mock_data["pptPrototype"]["path"]).exists()
    assert (ROOT / mock_data["pptReviewPrototype"]["path"]).exists()
    assert (ROOT / mock_data["pptReviewPrototype"]["dslPreview"]["pptDslPath"]).exists()
    for ppt in mock_data["ppts"]:
        assert (ROOT / ppt["dslPath"]).exists()
    assert (ROOT / mock_data["labGeneratePrototype"]["path"]).exists()
    assert (ROOT / mock_data["labGeneratePrototype"]["input"]["inputRef"]).exists()
    assert (ROOT / mock_data["labGeneratePrototype"]["promptSelection"]["promptPath"]).exists()
    assert (ROOT / mock_data["labGeneratePrototype"]["output"]["dslPath"]).exists()
    assert (ROOT / mock_data["labReviewPrototype"]["path"]).exists()
    assert (ROOT / "examples/review-detail/lab-review-detail.json").exists()
    assert (ROOT / mock_data["examGeneratePrototype"]["path"]).exists()
    assert (ROOT / mock_data["examGeneratePrototype"]["input"]["labDslPath"]).exists()
    assert (ROOT / mock_data["examGeneratePrototype"]["promptSelection"]["examPromptPath"]).exists()
    assert (ROOT / mock_data["examGeneratePrototype"]["promptSelection"]["gradingPromptPath"]).exists()
    assert (ROOT / mock_data["examGeneratePrototype"]["output"]["examDslPath"]).exists()
    assert (ROOT / mock_data["examGeneratePrototype"]["output"]["gradingDslPath"]).exists()
    assert (ROOT / mock_data["examsPrototype"]["path"]).exists()
    for exam in mock_data["exams"]:
        assert (ROOT / exam["examDslPath"]).exists()
        assert (ROOT / exam["gradingDslPath"]).exists()
    assert (ROOT / mock_data["examReviewPrototype"]["path"]).exists()
    assert (ROOT / mock_data["examReviewPrototype"]["dslPreview"]["examDslPath"]).exists()
    assert (ROOT / mock_data["examReviewPrototype"]["dslPreview"]["gradingDslPath"]).exists()
    assert (ROOT / mock_data["gradingPrototype"]["path"]).exists()
    for grading in mock_data["gradings"]:
        assert (ROOT / grading["dslPath"]).exists()
    assert (ROOT / mock_data["gradingReviewPrototype"]["path"]).exists()
    assert (ROOT / mock_data["gradingReviewPrototype"]["dslPreview"]["gradingDslPath"]).exists()
    assert (ROOT / mock_data["gradingReportPrototype"]["path"]).exists()
    assert (ROOT / mock_data["gradingReportPrototype"]["input"]["gradingDslPath"]).exists()
    assert (ROOT / mock_data["aiTaskCenterPrototype"]["path"]).exists()
    assert (ROOT / mock_data["dashboardPrototype"]["path"]).exists()
    assert (ROOT / mock_data["consolePrototype"]["path"]).exists()
    assert (ROOT / mock_data["auditObservabilityPrototype"]["path"]).exists()
    assert (ROOT / mock_data["auditDetailPrototype"]["path"]).exists()
    assert (ROOT / mock_data["auditIncidentReviewPrototype"]["path"]).exists()
    assert (ROOT / mock_data["operationsLaunchpadPrototype"]["path"]).exists()
    assert (ROOT / mock_data["operationsRunbookPrototype"]["path"]).exists()
    assert (ROOT / mock_data["operationsAcceptancePrototype"]["path"]).exists()
    assert (ROOT / mock_data["operationsDemoMapPrototype"]["path"]).exists()
    assert (ROOT / mock_data["operationsPresenterPrototype"]["path"]).exists()
    assert (ROOT / mock_data["operationsSignoffPrototype"]["path"]).exists()
    assert (ROOT / mock_data["operationsDemoScriptPrototype"]["path"]).exists()
    assert (ROOT / mock_data["deliveryPrototype"]["path"]).exists()
    assert (ROOT / mock_data["environmentManagementPrototype"]["path"]).exists()
    assert (ROOT / mock_data["skillManagementPrototype"]["path"]).exists()
    assert (ROOT / mock_data["providerSettingsPrototype"]["path"]).exists()
    assert (ROOT / mock_data["providerSettingsPrototype"]["runtimeGuards"]["envExamplePath"]).exists()
    for skill in mock_data["skills"]:
        assert (ROOT / skill["promptPath"]).exists()
        assert (ROOT / skill["outputSchema"]).exists()
        assert (ROOT / skill["exampleOutput"]).exists()


def test_review_center_static_prototype_has_local_core_safety_text():
    mock_data = load_json("frontend/mock-data.json")
    real_demo_queue = mock_data["reviewCenterPrototype"]["realDemoReviewQueue"]
    controlled_signal = mock_data["reviewCenterPrototype"]["controlledDockerEvidenceReviewSignal"]
    merged_signal = mock_data["reviewCenterPrototype"]["mergedGradingEvidenceReviewSignal"]
    notebook_plan = mock_data["reviewCenterPrototype"]["notebookEvidenceReviewPlan"]
    manifest = load_json("frontend/ui.manifest.json")
    prototypes = {prototype["route"]: prototype for prototype in manifest["staticPrototypes"]}
    pages = {page["route"]: page for page in manifest["pages"]}
    html = (ROOT / "frontend/review-center.html").read_text(encoding="utf-8")
    loader_js = (ROOT / "frontend/review-center-data.js").read_text(encoding="utf-8")

    assert real_demo_queue["component"] == "RealDemoReviewQueue"
    assert real_demo_queue["source"] == (
        "realDemoPrototype.generatedDsl + realDemoPrototype.coreBusinessDemoPath + "
        "realDemoPrototype.readonlyEvidenceDemo.reportDetail"
    )
    assert real_demo_queue["taskTotal"] == 4
    assert real_demo_queue["waitingReviewTotal"] == 4
    assert real_demo_queue["schemaValidatedTotal"] == 4
    assert real_demo_queue["readonlyEvidenceVisible"] is True
    assert real_demo_queue["readonlyEvidenceReportDetailSource"] == "realDemoPrototype.readonlyEvidenceDemo.reportDetail"
    assert real_demo_queue["readonlyEvidenceCollectedTotal"] == 2
    assert real_demo_queue["candidatePreviewAnswerSafe"] is True
    assert real_demo_queue["answerVisibleToCandidate"] is False
    assert real_demo_queue["manualReviewRequired"] is True
    assert real_demo_queue["autoApproveAllowed"] is False
    assert real_demo_queue["batchStateChangeAllowed"] is False
    assert real_demo_queue["realPublishAllowed"] is False
    assert [item["taskId"] for item in real_demo_queue["items"]] == [
        "real_demo_lab",
        "real_demo_exam",
        "real_demo_grading",
        "real_demo_ppt",
    ]
    assert all(item["status"] == "WAITING_REVIEW" for item in real_demo_queue["items"])
    assert real_demo_queue["items"][0]["entryHref"] == "lab-review.html?taskId=real_demo_lab"
    assert real_demo_queue["items"][1]["entryHref"] == "exam-review.html?taskId=real_demo_exam"
    assert real_demo_queue["items"][1]["candidatePreviewAnswersRemoved"] is True
    assert real_demo_queue["items"][2]["readonlyEvidenceStatus"] == "COLLECTED"
    assert real_demo_queue["items"][2]["entryHref"] == (
        "grading-report.html?file=examples/output/merged-evidence-report.json&taskId=real_demo_grading"
    )
    assert real_demo_queue["items"][3]["pptPageReviewActionVisible"] is True
    assert real_demo_queue["items"][3]["entryHref"] == "ppt-review.html?taskId=real_demo_ppt"
    assert controlled_signal["component"] == "ControlledDockerEvidenceReviewSignal"
    assert controlled_signal["source"] == "reviewDetail.controlledGradingEvidence"
    assert controlled_signal["dynamicSource"] == "GET /api/review-tasks/{id}.reviewDetail.controlledGradingEvidence"
    assert controlled_signal["fallbackSource"] == "realDemoPrototype.controlledDockerEvidenceDemo"
    assert controlled_signal["sourceMode"] == "STATIC_DEMO_FALLBACK"
    assert controlled_signal["taskId"] == "real_demo_grading"
    assert controlled_signal["status"] == "PARTIAL_CONTROLLED_EVIDENCE_COLLECTED"
    assert controlled_signal["available"] is True
    assert controlled_signal["taskTotal"] == 1
    assert controlled_signal["planTotal"] == 1
    assert controlled_signal["reportTotal"] == 1
    assert controlled_signal["controlledPlanPath"] == "examples/output/mimo-real-demo-controlled-plan.json"
    assert controlled_signal["controlledReportPath"] == "examples/output/mimo-real-demo-controlled-sandbox-report.json"
    assert controlled_signal["coveredCheckIds"] == ["check_q1", "check_q4"]
    assert controlled_signal["coveredCheckTypes"] == ["stdout_contains", "pytest"]
    assert controlled_signal["executed"] == 2
    assert controlled_signal["passed"] == 2
    assert controlled_signal["earnedScore"] == 40
    assert controlled_signal["totalControlledScore"] == 40
    assert controlled_signal["items"][0]["sourceGradingPath"] == "examples/output/real-llm-grading.json"
    assert controlled_signal["items"][0]["submissionRoot"] == "examples/submissions/real-demo-controlled"
    assert controlled_signal["items"][0]["hostExecutionAllowed"] is False
    assert controlled_signal["remainingCheckIds"] == ["check_q2", "check_q3"]
    assert controlled_signal["remainingCheckTypes"] == ["notebook_cell"]
    assert controlled_signal["remainingScore"] == 60
    assert controlled_signal["remainingStatus"] == "STATIC_NOTEBOOK_EVIDENCE_READY_FOR_REVIEW"
    assert controlled_signal["notebookEvidenceReviewPlanSource"] == "reviewTaskSummary.notebookEvidenceReviewPlan"
    assert controlled_signal["remainingReviewPlanStatus"] == "NOTEBOOK_STATIC_EVIDENCE_COLLECTED"
    assert controlled_signal["recommendedAction"] == "review_container_and_static_notebook_evidence_before_approval"
    assert controlled_signal["autoApproveAllowed"] is False
    assert controlled_signal["batchStateChangeAllowed"] is False
    assert controlled_signal["realPublishAllowed"] is False
    assert controlled_signal["safety"]["hostExecutionAllowed"] is False
    assert controlled_signal["safety"]["networkAllowed"] is False
    assert merged_signal["component"] == "MergedGradingEvidenceReviewSignal"
    assert merged_signal["source"] == "reviewDetail.mergedGradingEvidence"
    assert merged_signal["dynamicSource"] == "GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence"
    assert merged_signal["sourceMode"] == "NO_MERGED_EVIDENCE_REPORT"
    assert merged_signal["available"] is False
    assert merged_signal["reportTotal"] == 0
    assert merged_signal["coverageRatio"] == 0
    assert merged_signal["recommendedAction"] == "run_grade_evidence_merge_before_final_grading_review"
    assert merged_signal["autoApproveAllowed"] is False
    assert merged_signal["batchStateChangeAllowed"] is False
    assert merged_signal["realPublishAllowed"] is False
    assert merged_signal["safety"]["mergeExecutedOnlyExistingReports"] is True
    assert merged_signal["safety"]["hostExecutionAllowed"] is False
    assert merged_signal["safety"]["networkAllowed"] is False
    assert "run-evidence-auto-button" in html
    assert "POST /api/grading/evidence-auto" in html
    assert 'evidenceAutoPath: "/api/grading/evidence-auto"' in loader_js
    assert "taskId: state.evidenceAutoDefaults.taskId" in loader_js
    assert 'output: "examples/output/grading-evidence-auto.json"' in loader_js
    assert 'includeControlledCommand: false' in loader_js
    assert "runEvidenceAuto" in loader_js
    assert "applyEvidenceAutoSuccess" in loader_js
    assert "readinessUpdated=true" in loader_js
    assert "reportEntryUpdated=true" in loader_js
    assert "preApproveWarningRefreshed=true" in loader_js
    assert "record-decision-approve-ready-button" in html
    assert "record-decision-needs-revision-button" in html
    assert "record-decision-needs-evidence-button" in html
    assert "POST /api/review-tasks/{id}/decision-note" in html
    assert "review-detail-pre-approve-summary" in html
    assert "review-detail-pre-approve-status" in html
    assert "review-detail-pre-approve-list" in html
    assert "scorePreviewStatus=waiting" in html
    assert "scorePreviewReadyForDecisionNote=waiting" in html
    assert "DecisionNoteNextStep" in html
    assert "review-detail-decision-note-next-step-list" in html
    assert "review-detail-decision-note-next-step-status" in html
    assert "review-detail-decision-note-next-step-summary" in html
    assert "approveReadyDecision=false" in html
    assert "FinalHumanApproveReadiness" in html
    assert "review-detail-final-approve-status" in html
    assert "review-detail-final-approve-summary" in html
    assert "review-detail-final-approve-next-action" in html
    assert "review-detail-final-approve-safety" in html
    assert "finalReviewState=WAITING_EVIDENCE" in html
    assert "GradingRecordReviewIntegration" in html
    assert "review-detail-grading-record-summary" in html
    assert "review-detail-grading-record-status" in html
    assert "review-detail-grading-record-list" in html
    assert "GET /api/grading/records?taskId={id}" in html
    assert 'decisionNotePathTemplate: "/api/review-tasks/{id}/decision-note"' in loader_js
    assert "recordReviewDecisionNote" in loader_js
    assert "reviewDecisionNotes" in loader_js
    assert "applyGradingRecordReviewIntegration" in loader_js
    assert "var gradingRecords = detail.gradingRecords || {}" in loader_js
    assert "gradingRecords.reviewIntegration || {}" in loader_js
    assert "readyForAgentReview=" in loader_js
    assert "agentApiRequired=false" in loader_js
    assert "commandExecutedFromPage=false" in loader_js
    assert "applyPreApproveReviewCheck" in loader_js
    assert "approveReadyDecision" in loader_js
    assert "serverPrecheck" in loader_js
    assert "serverSummary.scorePreviewStatus" in loader_js
    assert "scorePreviewReadyForDecisionNote" in loader_js
    assert "score preview readiness" in loader_js
    assert "finalReviewState=" in loader_js
    assert "NEEDS_MORE_EVIDENCE" in loader_js
    assert "NEEDS_REVISION" in loader_js
    assert "WAITING_DECISION_NOTE" in loader_js
    assert "applyDecisionNoteNextStep" in loader_js
    assert "applyDecisionNoteRecorded" in loader_js
    assert "applyFinalHumanApproveReadiness" in loader_js
    assert "resolveSuggestedDecision" in loader_js
    assert "state.suggestedDecision" in loader_js
    assert "applySuggestedDecision" in loader_js
    assert "applySuggestedDecisionFromUrl" in loader_js
    assert "suggestedDecision=" in loader_js
    assert "summary.gradingDecisionNoteRecommendation" in loader_js
    assert "summary.gradingDecisionNoteRecommendationReason" in loader_js
    assert "evidenceSummary.decisionNoteRecommendation" in loader_js
    assert "evidenceSummary.decisionNoteRecommendationReason" in loader_js
    assert 'source: "core-readiness"' in loader_js
    assert "reason: decisionNoteReason(decision)" in loader_js
    assert "manualClickRequired=true" in loader_js
    assert "record_\" + suggestion.decision + \"_decision_note" in loader_js
    assert "record_review_decision_note_before_manual_approve" in loader_js
    assert "ready_for_human_approve" in loader_js
    assert "human_may_call_single_task_approve_after_final_review" in loader_js
    assert "revise_grading_dsl_or_scoring_evidence" in loader_js
    assert "collect_or_review_additional_grading_evidence" in loader_js
    assert "singleTaskManualApproveOnly=" in loader_js
    assert "approveApiNotCalled=true" in loader_js
    assert "approvalStillAllowed=true" in loader_js
    assert "GET /api/review-tasks/{id}.reviewDetail.preApproveReviewCheck" in prototypes["/review-center"]["dataSources"]
    assert "query: coreDbPath" in prototypes["/review-center"]["dataSources"]
    assert "GET /api/review-tasks/{id}?coreDbPath={path}" in prototypes["/review-center"]["dataSources"]
    assert "GET /api/backend/core-tasks/{id}?coreDbPath={path}" in prototypes["/review-center"]["dataSources"]
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.preApproveReviewCheck"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.preApproveReviewCheck.summary.scorePreviewStatus"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "GET /api/review-tasks/{id}.reviewDetail.preApproveReviewCheck.summary.scorePreviewReadyForDecisionNote"
        in prototypes["/review-center"]["dataSources"]
    )
    assert notebook_plan["component"] == "NotebookEvidenceReviewPlan"
    assert notebook_plan["source"] == (
        "realDemoPrototype.generatedDsl.grading.spec.assessmentPlan + "
        "reviewTaskSummary.controlledDockerEvidenceReviewSignal"
    )
    assert notebook_plan["status"] == "NOTEBOOK_STATIC_EVIDENCE_COLLECTED"
    assert notebook_plan["staticEvidencePlanPath"] == "examples/output/mimo-real-demo-notebook-static-plan.json"
    assert notebook_plan["staticEvidenceReportPath"] == "examples/output/mimo-real-demo-notebook-static-report.json"
    assert notebook_plan["remainingCheckIds"] == ["check_q2", "check_q3"]
    assert notebook_plan["checkTypes"] == ["notebook_cell"]
    assert notebook_plan["checkTotal"] == 2
    assert notebook_plan["scoreTotal"] == 60
    assert notebook_plan["evidenceStatus"] == "STATIC_NOTEBOOK_EVIDENCE_COLLECTED"
    assert notebook_plan["reviewStrategy"] == "STATIC_NOTEBOOK_JSON_PARSE_REVIEW"
    assert notebook_plan["executed"] == 2
    assert notebook_plan["earnedScore"] == 60
    assert notebook_plan["staticEvidenceMethod"] == "STATIC_NOTEBOOK_JSON_PARSE"
    assert notebook_plan["requiredReviewerActions"] == [
        "verify_notebook_cell_targets",
        "verify_expected_output_tokens",
        "review_static_notebook_evidence_matches_expected_tokens",
        "confirm_no_notebook_kernel_started",
    ]
    assert [item["checkId"] for item in notebook_plan["items"]] == ["check_q2", "check_q3"]
    assert all(item["runner"] == "NotebookGrader" for item in notebook_plan["items"])
    assert all(item["evidenceStatus"] == "STATIC_NOTEBOOK_EVIDENCE_COLLECTED" for item in notebook_plan["items"])
    assert notebook_plan["safety"]["notebookKernelStarted"] is False
    assert notebook_plan["safety"]["notebookExecuted"] is False
    assert notebook_plan["safety"]["contestantCodeExecuted"] is False
    assert notebook_plan["safety"]["realPublishAllowed"] is False

    assert "LOCAL_CORE_MVP" in html
    assert "真实 LLM 产物：只读加载" in html
    assert "真实 LLM 请求：本页不发起" in html
    assert "真实大模型：禁用" not in html
    assert "真实云资源：禁用" in html
    assert "自动发布：禁用" in html
    assert "批量状态变更：禁用" in html
    assert "GET /api/review-task-summary" in html
    assert "GET /api/review-tasks/{id}" in html
    assert "MVP Review Workspace" in html
    assert ".section-head > *" in html
    assert "overflow-wrap: anywhere" in html
    assert "white-space: normal" in html
    assert "mvp-workspace-summary" in html
    assert "mvp-workspace-state" in html
    assert "mvp-workspace-real-dsl-total" in html
    assert "mvp-workspace-selected-task" in html
    assert "mvp-workspace-evidence-state" in html
    assert "mvp-workspace-import-state" in html
    assert "mvp-workspace-review-link" in html
    assert "mvp-workspace-grading-report-link" in html
    assert "mvp-workspace-next-action" in html
    assert "mvp-workspace-safety" in html
    assert "applyMvpReviewWorkspaceFromSummary" in loader_js
    assert "applyMvpReviewWorkspaceFromDetail" in loader_js
    assert "applyMvpReviewWorkspaceFromCoreReadiness" in loader_js
    assert "refreshMvpWorkspaceContextLinks" in loader_js
    assert "refreshMvpWorkspaceContextLinks(getQueryTaskId())" in loader_js
    assert '"mvp-workspace-grading-report-link"' in loader_js
    assert '"等待评分 evidence"' in loader_js
    assert 'reportHref ? "打开评分报告" : "等待评分 evidence"' in loader_js
    assert "loadGradingRecordReportLink" in loader_js
    assert "applyGradingRecordReportLink" in loader_js
    assert "GET /api/grading/records?taskId={id}.latest.reportPath" in loader_js
    assert "link.removeAttribute(\"href\");" in loader_js
    assert "reportEntry=unavailable" in loader_js
    assert "fallbackEntryHref=" not in loader_js
    assert "GET /api/review-task-summary.mvpReviewWorkspace" in loader_js
    assert "GET /api/review-tasks/{id}.mvpReviewWorkspace" in loader_js
    assert "function reviewKindFromTask" in loader_js
    assert "taskType.indexOf(\"GRADING\")" in loader_js
    assert "previewKind === \"GRADING\"" in loader_js
    assert "autoApproveAllowed=false · realPublishAllowed=false · commandExecuted=false" in html
    assert "MvpReviewWorkspace" in prototypes["/review-center"]["dataSources"]
    assert "MvpReviewWorkspace.staticFallbackContextLinks" in prototypes["/review-center"]["dataSources"]
    assert "MvpReviewWorkspace.noHorizontalOverflow" in prototypes["/review-center"]["dataSources"]
    assert "GET /api/review-task-summary.mvpReviewWorkspace" in prototypes["/review-center"]["dataSources"]
    assert "GET /api/review-tasks/{id}.mvpReviewWorkspace" in prototypes["/review-center"]["dataSources"]
    assert "GET /api/review-tasks/{id}/core-readiness.mvpReviewWorkspace" in prototypes["/review-center"]["dataSources"]
    assert "query: coreDbPath, gradingDbPath, agentReport" in prototypes["/review-center"]["dataSources"]
    assert (
        "review-center.html?taskId={taskId}&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in prototypes["/review-center"]["dataSources"]
    )
    assert (
        "grading-report.html?file={file}&taskId={taskId}&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in prototypes["/review-center"]["dataSources"]
    )
    assert "GET /api/grading/records?taskId={id}&dbPath={path}.latest.reportPath" in prototypes["/review-center"]["dataSources"]
    assert "MvpReviewWorkspace.staticFallbackContextLinks" in pages["/review-center"]["dataSources"]
    assert "MvpReviewWorkspace.noHorizontalOverflow" in pages["/review-center"]["dataSources"]
    assert "query: gradingDbPath" in pages["/review-center"]["dataSources"]
    assert "query: agentReport" in pages["/review-center"]["dataSources"]
    assert "realLlmArtifacts=readonly-via-agentReport" in pages["/review-center"]["dataSources"]
    assert "frontendDirectRealLlmCall=false" in pages["/review-center"]["dataSources"]
    assert "GET /api/grading/records?taskId={id}&dbPath={path}.latest.reportPath" in pages["/review-center"]["dataSources"]
    assert {dependency["path"] for dependency in pages["/review-center"]["apiDependencies"]} >= {"/api/grading/records"}
    assert pages["/review-center"]["safety"]["realLlmArtifactsReadOnly"] is True
    assert pages["/review-center"]["safety"]["frontendDirectRealLlmCall"] is False
    assert prototypes["/review-center"]["safety"]["realLlmArtifactsReadOnly"] is True
    assert prototypes["/review-center"]["safety"]["frontendDirectRealLlmCall"] is False
    frontend_readme = read_text("frontend/README.md")
    assert "coreDbPath" in frontend_readme
    assert "GET /api/backend/core-tasks/{id}?coreDbPath=..." in frontend_readme
    assert "review-center.html?agentReport=examples/output/p0-deepseek-v4-flash-live-workflow-report.json" in frontend_readme
    assert "GET /api/review-task-summary?detailMode=light&agentReport={workflowReport}" in frontend_readme
    assert "GET /api/review-tasks/{id}?agentReport={workflowReport}" in frontend_readme
    assert "MVP Review Workspace" in frontend_readme
    assert "MvpReviewWorkspace.staticFallbackContextLinks" in frontend_readme
    assert "MvpReviewWorkspace.noHorizontalOverflow" in frontend_readme
    assert "GET /api/review-tasks/{id}/core-readiness" in frontend_readme
    assert "real_demo_lab` / `real_demo_exam` / `real_demo_grading` / `real_demo_ppt` fallback" in frontend_readme
    assert "Workflow Report 链接" in frontend_readme
    assert "answersRemovedFromSafePreview=true" in frontend_readme
    assert "RealDemoReviewQueue" in html
    assert (
        "source=realDemoPrototype.generatedDsl + realDemoPrototype.coreBusinessDemoPath + "
        "realDemoPrototype.readonlyEvidenceDemo.reportDetail"
    ) in html
    assert "/real-demo -&gt; /review-center -&gt; /ppt/:id/review -&gt; /grading/:id/report" in html
    assert "WAITING_REVIEW=4" in html
    assert "real_demo_lab" in html
    assert "real_demo_exam" in html
    assert "real_demo_grading" in html
    assert "real_demo_ppt" in html
    assert "entryHref=lab-review.html?taskId=real_demo_lab" in html
    assert "entryHref=exam-review.html?taskId=real_demo_exam" in html
    assert "examples/output/real-llm-lab.json" in html
    assert "examples/output/real-llm-exam.json" in html
    assert "examples/output/real-llm-grading.json" in html
    assert "examples/output/real-llm-demo-ppt-artifact.pptx" in html
    assert "entryHref=ppt-review.html?taskId=real_demo_ppt" in html
    assert 'id="real-demo-lab-review-link"' in html
    assert 'id="real-demo-exam-review-link"' in html
    assert 'id="real-demo-grading-review-link"' in html
    assert 'id="real-demo-ppt-review-link"' in html
    assert 'href="lab-review.html?taskId=real_demo_lab"' in html
    assert 'href="exam-review.html?taskId=real_demo_exam"' in html
    assert 'href="grading-review.html?taskId=real_demo_grading"' in html
    assert 'href="ppt-review.html?taskId=real_demo_ppt"' in html
    assert "readonlyEvidenceReportDetailSource=realDemoPrototype.readonlyEvidenceDemo.reportDetail" in html
    assert "readonlyEvidenceCollectedTotal=2" in html
    assert "Grading Report Entry" in html
    assert "review-detail-grading-report-entry-link" in html
    assert "GET /api/grading/report?file={file}&amp;taskId={id}" in html
    assert "entryHref=grading-report.html?file=examples/output/merged-evidence-report.json&amp;taskId=real_demo_grading" in html
    assert "grading-report.html?file=examples%2Foutput%2Fmerged-evidence-report.json&amp;taskId=real_demo_grading" in html
    assert "updateGradingReportEntry" in loader_js
    assert "gradingReportHref" in loader_js
    assert "latestReportPath" in loader_js
    assert "summary.realDemoReviewQueue" in loader_js
    assert "data-real-demo-artifact" in loader_js
    assert "reviewPageHref" in loader_js
    assert "refreshStaticRealDemoReviewLinks" in loader_js
    assert "data-agent-report-preserved" in loader_js
    assert "data-review-page-link" in loader_js
    assert "grading-review.html" in loader_js
    assert "agentReport" in loader_js
    assert "REAL_LLM_ARTIFACT_TASK" in loader_js
    assert "dynamicTaskAvailable === true" in loader_js
    assert "GET /api/grading/report?file={file}&taskId={id}" in loader_js
    assert 'fetch(state.evidenceAutoPath' in loader_js
    assert "POST /api/ai-tasks/{id}/approve" not in loader_js
    assert "POST /api/ai-tasks/{id}/reject" not in loader_js
    assert "/publish" not in loader_js.lower()
    assert "readonlyEvidence.status=COLLECTED" in html
    assert "recommendedAction=review_assessment_plan_and_readonly_evidence_before_approval" in html
    assert "manualReviewRequired=true" in html
    assert "Revision Decision · revise_lab_objective_depth" in html
    assert "realDemoPrototype.realDslRevisionDecision" in html
    assert "REVISION_APPROVED_FOR_MANUAL_MERGE" in html
    assert "decision=approve" in html
    assert "manualMergeRequired=true" in html
    assert "sourceDslModified=false" in html
    assert "Revision Promotion · WAITING_REVIEW candidate" in html
    assert "realDemoPrototype.realDslRevisionPromotion" in html
    assert "promotedStatus=WAITING_REVIEW" in html
    assert "promotedCandidateWritten=true" in html
    assert "Promotion Review Queue · LAB_GENERATION_REVISION" in html
    assert "realDemoPrototype.realDslRevisionPromotionReviewQueueItem" in html
    assert "POST /api/review/real-dsl-revision-enqueue" in html
    assert "reviewDetailAvailable=true" in html
    assert "Promotion Review Disposition · approved mock-only" in html
    assert "realDemoPrototype.realDslRevisionPromotionReviewDisposition" in html
    assert "state=APPROVED_FOR_MOCK_PUBLISH_ONLY" in html
    assert "mockPublishAvailable=true" in html
    assert "LabTemplateImportPreview · local platform draft" in html
    assert "source=realDemoPrototype.labTemplateImportPreview" in html
    assert "POST /api/labs/import-preview" in html
    assert "mcp=create_lab_template_import_preview" in html
    assert "databaseWritten=false" in html
    assert "realAgentImport=false" in html
    assert "AgentImportPreviewActionPanel · import preview entrypoints" in html
    assert "GET /api/review-tasks/{id}.reviewDetail.platformImportPreviewActions" in html
    assert "reviewPage.platformImportPreviewActions" in html
    assert "previewAlreadyCreatedTotal=1" in html
    assert "python lab_cli.py lab import-preview --task-id task_3b98ff60d482" in html
    assert "python lab_cli.py exam import-preview --task-id task_exam_demo" in html
    assert "python lab_cli.py grade import-preview --task-id task_grading_demo" in html
    assert "previewAlreadyCreated=true" in html
    assert "previewAlreadyCreated=false" in html
    assert "AgentImportPreviewSummary · review detail aggregation" in html
    assert "GET /api/review-tasks/{id}.reviewDetail.platformImportPreview" in html
    assert "reviewPage.platformImportPreview" in html
    assert "agentEntities=lab_template,exam_question,grading_rule" in html
    assert "sourceArtifactKinds=LAB_DSL,EXAM_DSL,GRADING_DSL" in html
    assert "AgentImportPreviewSignoffChecklist · manual import signoff" in html
    assert "GET /api/review-tasks/{id}.reviewDetail.platformImportPreviewSignoff" in html
    assert "reviewPage.platformImportPreviewSignoff" in html
    assert "readyForHumanSignoff=true" in html
    assert "missingPreviewTotal=0" in html
    assert "preApproveReviewCheckWarningTotal=" in loader_js
    assert "approveReadyDecision=" in loader_js
    assert "confirm_candidate_answer_hidden_and_grading_refs_teacher_only" in html
    assert "confirm_sandbox_required_before_real_execution" in html
    assert "ExamQuestionImportPreview · candidate safe draft" in html
    assert "POST /api/exams/import-preview" in html
    assert "mcp=create_exam_question_import_preview" in html
    assert "candidateAnswerVisible=false" in html
    assert "GradingRuleImportPreview · sandbox review draft" in html
    assert "POST /api/grading/import-preview" in html
    assert "mcp=create_grading_rule_import_preview" in html
    assert "sandboxRequiredBeforeRealExecution=true" in html
    assert "ControlledDockerEvidenceReviewSignal" in html
    assert "review-center-data.js" in html
    assert "API 动态队列" in html
    assert "review-center-dynamic-queue" in html
    assert "review-center-dynamic-queue-status" in html
    assert "review-center-api-status" in html
    assert "review-detail-subtitle" in html
    assert "review-detail-artifact-total" in html
    assert "review-detail-workflow-step-total" in html
    assert "review-detail-status" in html
    assert "review-detail-auto-approve" in html
    assert "review-detail-api-summary" in html
    assert "review-detail-task-type" in html
    assert "CoreWorkflowReadiness" in html
    assert "review-detail-core-readiness-summary" in html
    assert "review-detail-core-readiness-status" in html
    assert "review-detail-core-readiness-next-action" in html
    assert "review-detail-core-readiness-progress" in html
    assert "review-detail-core-readiness-safety" in html
    assert "review-detail-core-readiness-list" in html
    assert "next single-step action guide" in html
    assert "review-detail-core-next-step-guide-status" in html
    assert "review-detail-core-next-step-guide-tool" in html
    assert "review-detail-core-next-step-guide-command" in html
    assert "review-detail-core-next-step-copy" in html
    assert "review-detail-core-next-step-copy-status" in html
    assert "review-detail-core-review-url-copy" in html
    assert "review-detail-core-review-url-copy-status" in html
    assert "复制建议命令" in html
    assert "复制执行后回看链接" in html
    assert "copyCommandEnabled=false" in html
    assert "copyReviewUrlEnabled=false" in html
    assert "commandExecuted=false" in html
    assert "stateChanged=false" in html
    assert "AgentCoreNextToolExecutionReport" in html
    assert "review-detail-agent-core-execution-summary" in html
    assert "review-detail-agent-core-execution-status" in html
    assert "review-detail-agent-core-execution-list" in html
    assert "review-detail-agent-core-next-step-copy" in html
    assert "review-detail-agent-core-next-step-copy-status" in html
    assert "复制报告下一步命令" in html
    assert "copyAgentReportCommandEnabled=false" in html
    assert "NO_AGENT_REPORT_LOADED" in html
    assert "GET /api/workflow/report?file={agentReport}" in html
    assert "GET /api/review-tasks/{id}/core-readiness" in html
    assert "gradingManualReviewChecklistStatus=waiting" in html
    assert "gradingScorePreviewStatus=waiting" in html
    assert "gradingScorePreviewReadyForDecisionNote=waiting" in html
    assert "gradingDecisionNoteRecommendation=waiting" in html
    assert "review-detail-artifacts-summary" in html
    assert "review-detail-artifacts-total" in html
    assert "review-detail-artifacts-list" in html
    assert "review-detail-quality-summary" in html
    assert "review-detail-quality-available" in html
    assert "review-detail-quality-list" in html
    assert "RealDslContentQualityDecision" in html
    assert "review-detail-content-quality-summary" in html
    assert "review-detail-content-quality-status" in html
    assert "review-detail-content-quality-list" in html
    assert "requiresRevisionBeforeImportPreview" in html
    assert "requiresEvidenceBeforeFinalApproval" in html
    assert "review-detail-import-actions-summary" in html
    assert "review-detail-import-actions-total" in html
    assert "review-detail-import-actions-list" in html
    assert "review-detail-import-preview-summary" in html
    assert "review-detail-import-preview-total" in html
    assert "review-detail-import-preview-list" in html
    assert "review-detail-import-signoff-summary" in html
    assert "review-detail-import-signoff-ready" in html
    assert "review-detail-import-signoff-list" in html
    assert "review-detail-platform-entity-summary" in html
    assert "review-detail-platform-entity-total" in html
    assert "review-detail-platform-entity-list" in html
    assert "API Platform Entity Readiness" in html
    assert "review-detail-platform-readiness-summary" in html
    assert "review-detail-platform-readiness-total" in html
    assert "review-detail-platform-readiness-list" in html
    assert "GET /api/platform-entities/readiness-report?sourceTaskId={id}" in html
    assert "review-detail-dsl-title" in html
    assert "review-detail-dsl-status" in html
    assert "review-detail-dsl-preview" in html
    assert "review-detail-timeline-trace" in html
    assert "review-detail-timeline-list" in html
    assert "STATIC_HTML_FALLBACK" in html
    assert "API_READONLY_LOADED" in loader_js
    assert "/api/review-task-summary?limit=3&detailMode=light" in loader_js
    assert "/api/review-tasks/{id}" in loader_js
    assert "coreDbPath" in loader_js
    assert "backendCoreTaskPathTemplate: \"/api/backend/core-tasks/{id}\"" in loader_js
    assert "GET /api/backend/core-tasks/{id}?coreDbPath={path}" in loader_js
    assert "backendCoreTaskFallback=true" in loader_js
    assert "jsonStoreRead=false" in loader_js
    assert "coreReadinessPathTemplate" in loader_js
    assert "/api/review-tasks/{id}/core-readiness" in loader_js
    assert "loadCoreWorkflowReadiness" in loader_js
    assert "return loadCoreWorkflowReadiness(taskId).then(function ()" in loader_js
    assert "applyCoreWorkflowReadiness" in loader_js
    assert "applyContentQualityDecision" in loader_js
    assert "contentQualityItemSummary" in loader_js
    assert "appendContentQualityIssues" in loader_js
    assert "reviewPage.contentQualitySummary" in loader_js
    assert "readyForImportPreviewKinds=" in loader_js
    assert "evidenceRequiredKinds=" in loader_js
    assert "coreWorkflowReadinessReport" in loader_js
    assert "recommendedNextAction=" in loader_js
    assert "nextToolRecommendation" in loader_js
    assert "CONTENT_QUALITY_REVISION_REQUIRED" in loader_js or "contentQualityReadiness" in loader_js
    assert "contentQualityReadyForImportPreview=" in loader_js
    assert "contentQualityBlockedKinds=" in loader_js
    assert "review revision-request" in loader_js
    assert "CONTENT_QUALITY_REVISION_REGENERATION_PENDING" in loader_js or "regenerate_from_revision_mock" in loader_js
    assert "nextTool=" in loader_js
    assert "autoExecuteAllowed=" in loader_js
    assert "buildNextSingleStepGuide" in loader_js
    assert "applyCoreNextStepCopyGuide" in loader_js
    assert "copySuggestedCoreNextCommand" in loader_js
    assert "lastSuggestedCliCommand" in loader_js
    assert "navigator.clipboard.writeText" in loader_js
    assert "document.execCommand(\"copy\")" in loader_js
    assert "copyCommandEnabled=" in loader_js
    assert "copyReviewUrlEnabled=" in loader_js
    assert "commandExecuted=false" in loader_js
    assert "stateChanged=false" in loader_js
    assert "--output examples/output/demo-agent-core-next-tool-execution-" in loader_js
    assert "buildReviewCenterAgentReportUrl" in loader_js
    assert "lastSuggestedReviewUrl" in loader_js
    assert "copySuggestedCoreReviewUrl" in loader_js
    assert "review-detail-core-review-url-copy" in loader_js
    assert "agentReport" in loader_js
    assert "setupCoreNextStepCopyAction" in loader_js
    assert "workflowReportPathTemplate" in loader_js
    assert "getQueryAgentReport" in loader_js
    assert "loadAgentCoreExecutionReport" in loader_js
    assert "applyAgentCoreExecutionReport" in loader_js
    assert "applyAgentReportNextStepCopyGuide" in loader_js
    assert "copyAgentReportSuggestedCoreNextCommand" in loader_js
    assert "lastAgentReportSuggestedCliCommand" in loader_js
    assert "setupAgentReportNextStepCopyAction" in loader_js
    assert "copyAgentReportCommandEnabled=" in loader_js
    assert "ready_from_agent_report" in loader_js
    assert "agentCoreNextToolExecution" in loader_js
    assert "postExecutionCoreNextToolPlan" in loader_js
    assert "nextSingleStepActionGuide" in loader_js
    assert "toolCallSucceeded=" in loader_js
    assert "commandExecutedByPage=false" in loader_js
    assert "readOnlyReport=true" in loader_js
    assert "reviewCenterReportUrl=" in loader_js
    assert "reportLinkAvailable=" in loader_js
    assert "canContinueWithSameCommand=" in loader_js
    assert "stopReason=" in loader_js
    assert "operatorSummary=" in loader_js
    assert "currentStop" in loader_js
    assert "suggestedCliCommand=" in loader_js
    assert "execute-core-next-tool" in loader_js
    assert "importPreviewPendingTotal=" in loader_js
    assert "pendingPreviewEntities=" in loader_js
    assert "import preview pending actions" in loader_js
    assert "gradingManualReviewChecklistStatus=" in loader_js
    assert "gradingScorePreviewStatus=" in loader_js
    assert "gradingScorePreview=" in loader_js
    assert "gradingScorePreviewReadyForDecisionNote=" in loader_js
    assert "gradingDecisionNoteRecommendation=" in loader_js
    assert "gradingNextDecisionNoteAction=" in loader_js
    assert "sandboxExecutedByReport=" in loader_js
    assert "renderDynamicQueue" in loader_js
    assert "loadTaskDetail" in loader_js
    assert "data-api-task-id" in loader_js
    assert "history.replaceState" in loader_js
    assert "review-detail-api-summary" in loader_js
    assert "artifactTotal=" in loader_js
    assert "workflowStepTotal=" in loader_js
    assert "rejectRequiresReason=" in loader_js
    assert "realPublishAllowed=" in loader_js
    assert "applyDslPreview" in loader_js
    assert "applyTimeline" in loader_js
    assert "applyArtifactGroups" in loader_js
    assert "artifactHref" in loader_js
    assert "workflowReportHref" in loader_js
    assert "reviewDetailHref" in loader_js
    assert "artifactLink=" in loader_js
    assert "data-artifact-link" in loader_js
    assert "打开 DSL Preview" in loader_js
    assert "打开 Workflow Report" in loader_js
    assert "applyQualitySignals" in loader_js
    assert "applyPlatformImportPreviews" in loader_js
    assert "reviewPage.dslPreview" in loader_js
    assert "contentLoaded: " in loader_js
    assert "schemaValidated: " in loader_js
    assert "candidateSafety: answerVisibleToCandidate=" in loader_js
    assert "reviewSafety: readOnly=" in loader_js
    assert "reviewPage.timeline" in loader_js
    assert "reviewPage.artifactGroups" in loader_js
    assert "reviewPage.qualitySignals" in loader_js
    assert "reviewPage.platformImportPreviewActions" in loader_js
    assert "reviewPage.platformImportPreview" in loader_js
    assert "reviewPage.platformImportPreviewSignoff" in loader_js
    assert "reviewPage.agentEntityReadinessReport" in loader_js
    assert "readinessItemByEntityId" in loader_js
    assert "agentEntityActivitySummary" in loader_js
    assert "postSignoffChecklistSummary" in loader_js
    assert "finalPublishReviewDecisionSummary" in loader_js
    assert "signoffActionRoute=paused" in loader_js
    assert "finalReviewRoute=paused" in loader_js
    assert "pausedPlatformHandoffRoute=" in loader_js
    assert "readyForSignoff=" in loader_js
    assert "finalPublishReviewDecision=" in loader_js
    assert "平台签收暂停" in loader_js
    assert "查看本地实体（平台签收暂停）" in loader_js
    assert "controlledEvidenceNextActionTotal=" in loader_js
    assert "controlledEvidenceNextAction=" in loader_js
    assert "gradingEvidenceReportAvailable=" in loader_js
    assert "gradingEvidenceReadyForDecisionNote=" in loader_js
    assert "latestEvidenceReport=" in loader_js
    assert "evidenceCli=" in loader_js
    assert "evidenceAction=" in loader_js
    assert "reviewPage.agentEntityMockImport" in loader_js
    assert "reviewPage.agentEntityReadinessReport" in loader_js
    assert "GET /api/review-tasks/{id}.reviewDetail.reviewPage.agentEntityReadinessReport" in loader_js
    assert "getQueryAgentEntityRefreshRequested" in loader_js
    assert "agentEntityRefreshRequested=" in loader_js
    assert "refreshedAfterAgentEntityReturn=" in loader_js
    assert "agentEntityRefresh=1" in loader_js
    assert "platformImportPreviewActions" in loader_js
    assert "agentEntityMockImport" in loader_js
    assert "loadAgentEntityReadiness" in loader_js
    assert "applyAgentEntityReadiness" in loader_js
    assert "agentEntityActivitySummary" in loader_js
    assert "/api/platform-entities/readiness-report?sourceTaskId=" in loader_js
    assert "reviewCenterPrototype.agentEntityReadinessReport" in loader_js
    assert "AgentEntityReadinessReport" in loader_js
    assert "readyForManualAgentReview=" in loader_js
    assert "dryRunPreparedTotal=" in loader_js
    assert "requestSentTotal=" in loader_js
    assert "resultRecordedTotal=" in loader_js
    assert "latestPlatformStatus=" in loader_js
    assert "latestDryRunArtifact=" in loader_js
    assert "latestSendStatusCode=" in loader_js
    assert "latestStatusQuery=" in loader_js
    assert "latestResultStatus=" in loader_js
    assert "agentDraftId=" in loader_js
    assert "signoffState=" in loader_js
    assert "READY_FOR_PLATFORM_ENTITY_SIGNOFF" in loader_js
    assert "WAITING_PLATFORM_ENTITY_IMPORT_ACTIVITY" in loader_js
    assert "readyForAgentEntitySignoff=" in loader_js
    assert "signoffRecorded=" in loader_js
    assert "agentEntitySignoffRecordedTotal=" in loader_js
    assert "manualSignoffChecklist=" in loader_js
    assert "postSignoffPrePublishChecklist" in loader_js
    assert "AgentEntityPostSignoffPrePublishChecklist" in loader_js
    assert "AgentEntitySpecificPrePublishReviewFocus" in loader_js or "entitySpecificReviewFocus" in loader_js
    assert "postSignoffPrePublishReadyTotal=" in loader_js
    assert "allPostSignoffPrePublishReady=" in loader_js
    assert "postSignoffPrePublishStatus=" in loader_js
    assert "entitySpecificReviewFocus=" in loader_js
    assert "finalHumanReviewRequired=" in loader_js
    assert "final_human_publish_review_before_any_real_publish" in loader_js
    assert "secretValueReturned=false" in loader_js
    assert "action=signoff" not in loader_js
    assert "去签收" not in loader_js
    assert "查看本地实体记录" in loader_js
    assert "查看就绪实体" in loader_js
    assert "GET /api/platform-entities?sourceTaskId={id}" in loader_js
    assert "GET /api/platform-entities/{id}" in loader_js
    assert "detailApi=GET /api/platform-entities/" in loader_js
    assert "agent-entities.html" in loader_js
    assert "entityId=" in loader_js
    assert "params.set(\"entityKind\", agentEntityKind(entityType) || \"\")" in loader_js
    assert "agentEntityKind" in loader_js
    assert "agentEntityHref" in loader_js
    assert "打开实体详情" in loader_js
    assert "sourceTaskId=" in loader_js
    assert "missingPreviewActions" in loader_js
    assert "mockStoreWritten=" in loader_js
    assert "readyForHumanSignoff=" in loader_js
    assert "realAgentImport=" in loader_js
    assert "databaseWritten=" in loader_js
    assert "reviewHighlights" in loader_js
    assert "realPublish=false" in loader_js
    assert "autoPublishAllowed: false" in loader_js
    assert "timeline.slice(0, 8)" in loader_js
    assert "DETAIL_LOAD_SKIPPED" in loader_js
    assert "DETAIL_LOAD_FAILED" in loader_js
    assert "summaryLoaded=true" in loader_js
    assert "method: \"GET\"" in loader_js
    assert "autoPublishAllowed=false" in loader_js
    assert "batchStateChangeAllowed=false" in loader_js
    assert "method: \"POST\"" in loader_js
    assert 'fetch(state.evidenceAutoPath' in loader_js
    assert "POST /api/ai-tasks/{id}/approve" not in loader_js
    assert "POST /api/ai-tasks/{id}/reject" not in loader_js
    assert "/approve" not in loader_js
    assert "/reject" not in loader_js
    assert "/publish" not in loader_js.lower()
    assert "source=reviewDetail.controlledGradingEvidence" in html
    assert "dynamicSource=GET /api/review-tasks/{id}.reviewDetail.controlledGradingEvidence" in html
    assert "fallbackSource=realDemoPrototype.controlledDockerEvidenceDemo" in html
    assert "sourceMode=STATIC_DEMO_FALLBACK" in html
    assert "available=true" in html
    assert "planTotal=1 · reportTotal=1" in html
    assert "planPath=examples/output/mimo-real-demo-controlled-plan.json" in html
    assert "reportPath=examples/output/mimo-real-demo-controlled-sandbox-report.json" in html
    assert "PARTIAL_CONTROLLED_EVIDENCE_COLLECTED" in html
    assert "taskId=real_demo_grading" in html
    assert "CONTROLLED_DOCKER_SANDBOX_POC" in html
    assert "imageTag=ai-grading-python:0.1" in html
    assert "submissionPath=examples/submissions/real-demo-controlled" in html
    assert "coveredCheckIds=check_q1,check_q4" in html
    assert "coveredCheckTypes=stdout_contains,pytest" in html
    assert "executed=2" in html
    assert "passed=2" in html
    assert "earnedScore=40/40" in html
    assert "remainingCheckIds=check_q2,check_q3" in html
    assert "remainingCheckTypes=notebook_cell" in html
    assert "remainingScore=60" in html
    assert "STATIC_NOTEBOOK_EVIDENCE_READY_FOR_REVIEW" in html
    assert "notebookEvidenceReviewPlanSource=reviewTaskSummary.notebookEvidenceReviewPlan" in html
    assert "remainingReviewPlanStatus=NOTEBOOK_STATIC_EVIDENCE_COLLECTED" in html
    assert "recommendedAction=review_container_and_static_notebook_evidence_before_approval" in html
    assert "hostExecutionAllowed=false" in html
    assert "networkAllowed=false" in html
    assert "MergedGradingEvidenceReviewSignal" in html
    assert "source=reviewDetail.mergedGradingEvidence" in html
    assert "dynamicSource=GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence" in html
    assert "reportType=GRADING_EVIDENCE_MERGE" in html
    assert "merged-evidence-report-type" in html
    assert "merged-evidence-auto-summary" in html
    assert "merged-evidence-auto-step-list" in html
    assert "merged-evidence-review-decision-summary" in html
    assert "reviewDecisionHint=NEEDS_EVIDENCE" in html
    assert "autoEvidenceReport=false" in html
    assert "NO_MERGED_EVIDENCE_REPORT" in html
    assert "reviewDetail.mergedGradingEvidence.visible=false" in html
    assert "coverageRatio=0" in html
    assert "controlledDockerCheckTotal=0" in html
    assert "readonlyStaticCheckTotal=0" in html
    assert "check evidence review" in html
    assert "checkEvidenceReviewItemTotal=0" in html
    assert "manualCheckReviewTotal=0" in html
    assert "merged-evidence-check-list" in html
    assert "run_grade_evidence_merge_before_final_grading_review" in html
    assert "mergeExecutedOnlyExistingReports=true" in html
    assert "summarizeMergedEvidence" in loader_js
    assert "renderMergedEvidenceAutoSteps" in loader_js
    assert "latestReportType" in loader_js
    assert "autoEvidenceStepTotal" in loader_js
    assert "reviewDecisionHintsSummary" in loader_js
    assert "reviewDecisionHint=" in loader_js
    assert "renderMergedEvidenceCheckItems" in loader_js
    assert "item.recommendedAction" in loader_js
    assert "item.evidenceSourceKind" in loader_js
    assert "mergedGradingEvidenceReviewSignal" in loader_js
    assert "GradingEvidenceReadiness" in html
    assert "GradingEvidenceActionGuide" in html
    assert "review-detail-evidence-readiness-summary" in html
    assert "review-detail-evidence-readiness-list" in html
    assert "review-detail-evidence-action-guide-list" in html
    assert "review-detail-evidence-action-primary" in html
    assert "review-detail-evidence-action-api" in html
    assert "review-detail-evidence-action-cli" in html
    assert "reviewTaskSummary.gradingEvidenceReadinessSignal" in html
    assert "applyGradingEvidenceReadiness" in loader_js
    assert "applyGradingEvidenceActionGuide" in loader_js
    assert "gradingEvidenceReadinessSummary" in loader_js
    assert "controlledCommandOptInRequired=true" in loader_js
    assert "sandboxExecutedByReadiness=false" in loader_js
    assert "NotebookEvidenceReviewPlan" in html
    assert "realDemoPrototype.generatedDsl.grading.spec.assessmentPlan" in html
    assert "RealDslReviewPreview" in html
    assert "source=realDemoPrototype.realDslReviewPreview" in html
    assert "AI 工具应用入门实验" in html
    assert "stepTotal=4" in html
    assert "questionTotal=1" in html
    assert "gradingRefVisibleToCandidate=false" in html
    assert "TeacherOnlyGradingRefs" in html
    assert "assessmentPlanTotal=1" in html
    assert "slideTotal=4" in html
    assert "QualitySignals" in html
    assert "qualityIssueTotal=3" in html
    assert "ProviderQualitySummary" in html
    assert "source=reviewDetail.reviewPage.providerSummary.qualitySummary" in html
    assert "readyForReview=true" in html
    assert "realLlmCalled=true" in html
    assert "apiSurface=chat.completions" in html
    assert "responseId=resp_demo_lab_quality" in html
    assert "normalizationPatchCount=1" in html
    assert "schemaRepairApplied=false" in html
    assert "calls[0].qualitySummary.normalizationPatches=set.metadata.category" in html
    assert "providerQuality.readyForReview=true" in html
    assert "providerQuality.normalizationPatchCount=1" in html
    assert "qualitySummary 只辅助人工审核排序" in html
    assert "realSandboxRunEnabled=false" in html
    assert "NOTEBOOK_STATIC_EVIDENCE_COLLECTED" in html
    assert "evidenceStatus=STATIC_NOTEBOOK_EVIDENCE_COLLECTED" in html
    assert "strategy=STATIC_NOTEBOOK_JSON_PARSE_REVIEW" in html
    assert "check_q2" in html
    assert "check_q3" in html
    assert "NotebookGrader" in html
    assert "notebookKernelStarted=false" in html
    assert "notebookExecuted=false" in html
    assert "review_static_notebook_evidence_matches_expected_tokens" in html
    assert "confirm_no_notebook_kernel_started" in html
    assert "ReviewPriorityQueue" in html
    assert "reviewDetail.assessmentPlan.manualReviewChecklist" in html
    assert "manualReviewChecklistSummary.needsHumanReviewTotal=5" in html
    assert "checklistSource=reviewCenterPrototype.reviewPriorityQueue.items[0].manualReviewChecklistSummary" in html
    assert "checklistTotal=5" in html
    assert "needsHumanReviewTotal=5" in html
    assert "defaultSort=priorityRankAsc" in html
    assert "priority=URGENT" in html
    assert "priority=HIGH" in html
    assert "priority=NORMAL" in html
    assert "reasonCode=HIGH_RISK_MOCK_EVIDENCE_REQUIRED" in html
    assert "reasonCode=CANDIDATE_SAFE_EXAM_PREVIEW" in html
    assert "reasonCode=LAB_QUALITY_NEEDS_REVIEW" in html
    assert "recommendedAction=review_assessment_plan_before_approval" in html
    assert "recommendedAction=verify_candidate_preview_and_grading_refs" in html
    assert "recommendedAction=review_generation_profile_and_material_coverage" in html
    assert "PptPageReviewUpdateAction" in html
    assert "entryRoute=/ppt/:id/review?taskId=task_ppt_demo" in html
    assert "entryApi=POST /api/review-tasks/{id}/ppt-page-review-status" in html
    assert "cli=python lab_cli.py review ppt-page-update" in html
    assert "slideIndex=4" in html
    assert "reviewStatus=REVISE_REQUIRED" in html
    assert "reviseRequiresComment=true" in html
    assert "writesOperationAudit=true" in html
    assert "operationAuditAction=PPT_PAGE_REVIEW_UPDATE" in html
    assert "taskStatusChanged=false" in html
    assert "NextManualReviewAction" in html
    assert "reviewCenterPrototype.reviewPriorityQueue.items[0]" in html
    assert "entryRoute=/review-center?taskId=task_grading_demo" in html
    assert "entryApi=GET /api/review-tasks/{id}" in html
    assert "taskId=task_grading_demo" in html
    assert "primaryReviewFocus=review_assessment_plan_before_approval" in html
    assert "requiredEvidence=reviewDetail.assessmentPlan.summary" in html
    assert "open_task_grading_demo_review_detail" in html
    assert "verify_assessment_plan_aligned_with_checks" in html
    assert "confirm_mock_evidence_not_collected" in html
    assert "confirm_real_sandbox_evidence_required_before_real_execution" in html
    assert "verify_required_limits_present" in html
    assert "confirm_no_execution_or_publish" in html
    assert "realPublishAllowed=false" in html
    assert "batchStateChangeAllowed=false" in html
    assert "autoApproveAllowed=false" in html
    assert "QualitySignalQueueSummary" in html
    assert "examReviewPrototype.qualitySignals + gradingReviewPrototype.qualitySignals" in html
    assert "candidateSafeExamPreview.answersRemoved=true" in html
    assert "questionGradingRefCoverage.status=MATCHED" in html
    assert "gradingRefCoverage.status=MATCHED" in html
    assert "scoreCoverage.status=MATCHED" in html
    assert "explainability.status=EXPLAINABLE" in html
    assert "matchedCoverageTotal=4" in html
    assert "explainablePlanTotal=2" in html
    assert "candidateSafeExamPreviewTotal=1" in html
    assert "质量信号只辅助人工审核" in html
    assert "AssessmentPlanQueueSignal" in html
    assert "reviewDetail.assessmentPlan" in html
    assert "gradingReviewPrototype.assessmentPlanSummary" in html
    assert "GRADING_GENERATION" in html
    assert "planTotal=1" in html
    assert "alignedWithChecks=true" in html
    assert "riskLevel=high" in html
    assert "MOCK_EVIDENCE_NOT_COLLECTED" in html
    assert "realSandboxEvidenceRequired=true" in html
    assert "HighRiskMcpIntentPanel" in html
    assert "frontend/mock-data.json.highRiskMcpIntentPrototype" in html
    assert "SecondConfirmationStatusPanel" in html
    assert "frontend/mock-data.json.secondConfirmationStatusPrototype" in html
    assert "get_second_confirmation_status" in html
    assert "GET /api/review-tasks/{id}/second-confirmation-status" in html
    assert "readOnly=true" in html
    assert "confirmationActionAvailable=false" in html
    assert "confirmationEndpointEnabled=false" in html
    assert "mcp_call_get_second_confirmation_status_demo" in html
    assert "publish_lab" in html
    assert "publish_exam" in html
    assert "destroy_environment" in html
    assert "MCP_PUBLISH_LAB_INTENT" in html
    assert "MCP_PUBLISH_EXAM_INTENT" in html
    assert "MCP_DESTROY_ENVIRONMENT_INTENT" in html
    assert "postReviewDisposition" in html
    assert "WAITING_HUMAN_REVIEW" in html
    assert "APPROVED_EXECUTION_BLOCKED" in html
    assert "APPROVED_PENDING_SECOND_CONFIRMATION" in html
    assert "nextRequiredAction=approve_or_reject" in html
    assert "nextRequiredAction=mock_disposition_only" in html
    assert "secondConfirmationSatisfied=false" in html
    assert "reviewIntentOnly=true" in html
    assert "requiresSecondConfirmation=true" in html
    assert "realPublish=false" in html
    assert "environmentDestroyed=false" in html
    assert "executeRealPublishEnabled=false" in html
    assert "destroyRealEnvironmentEnabled=false" in html
    assert "disabled" in html


def test_lab_generate_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/lab-generate.html").read_text(encoding="utf-8")
    script = (ROOT / "frontend/lab-generate-data.js").read_text(encoding="utf-8")
    ui_manifest = load_json("frontend/ui.manifest.json")
    pages = {page["route"]: page for page in ui_manifest["pages"]}

    assert "LOCAL_CORE_MVP" in html
    assert "真实 LLM：通过后端/CLI 显式接入" in html
    assert "远程素材抓取：禁用" in html
    assert "未知 Shell 执行：禁用" in html
    assert "自动发布：禁用" in html
    assert "POST /api/materials/analyze" in html
    assert "POST /api/labs/generate" in html
    assert "WAITING_REVIEW" in html
    assert "Local Backend API" in html
    assert "LocalCoreGenerationWorkspace" in read_text("frontend/README.md")
    assert "LabGenerationCloseLoopAction" in html
    assert ".section-head > *" in html
    assert "overflow-wrap: anywhere" in html
    assert "white-space: normal" in html
    assert "lab-generate-next-summary" in html
    assert "lab-generate-next-status" in html
    assert "lab-generate-next-task" in html
    assert "lab-generate-next-artifact" in html
    assert "lab-generate-review-center-link" in html
    assert "lab-generate-review-page-link" in html
    assert "lab-generate-import-preview-link" in html
    assert "review-center.html" in html
    assert "lab-review.html" in html
    assert "agent-entities.html?entityKind=lab" in html
    assert "requiresHumanReview=true" in html
    assert "realAgentImport=false" in html
    assert 'id="lab-generate-input"' in html
    assert 'id="lab-generate-run"' in html
    assert '<script src="lab-generate-data.js"></script>' in html
    assert 'generatePath: "/api/labs/generate"' in script
    assert 'method: "POST"' in script
    assert "updateCloseLoopAction" in script
    assert "withQuery" in script
    assert "queryParam" in script
    assert "configureLocalContextFromQuery" in script
    assert 'configureLocalContextFromQuery();\n    updateCloseLoopAction({' in script
    assert 'status: "NOT_CREATED"' in script
    assert "withLocalContext" in script
    assert "requestBodyWithLocalContext" in script
    assert "nextParams.coreDbPath = state.coreDbPath" in script
    assert "nextParams.gradingDbPath = state.gradingDbPath" in script
    assert "nextParams.agentReport = state.agentReport" in script
    assert 'id="lab-generate-provider-mode"' in html
    assert 'id="lab-generate-explicit-real-call"' in html
    assert "providerRequestOptions" in script
    assert "providerMode: mode" in script
    assert "explicitRealCallOptIn" in script
    assert "confirmWaitingReview" in script
    assert "Object.assign({ input: inputPath }, providerRequestOptions())" in script
    assert "const inputPath = input ? input.value.trim() : state.defaultInput" in script
    assert "lab-generate-review-center-link" in script
    assert "lab-generate-import-preview-link" in script
    assert "agent-entities.html" in script
    assert "WAITING_REVIEW" in script
    assert "autoPublishAllowed: false" in script
    assert "realPublish: false" in script
    assert "realLlmCalled" in script
    assert "unknownShellExecuted" in script
    assert "labFeatureReadiness" in script
    assert "completeForStableV1" in script
    assert "minimumTeachingQualityMet" in script
    assert "apiKey" not in script
    assert "POST /api/ai-tasks/{id}/approve" not in script
    assert "POST /api/ai-tasks/{id}/reject" not in script
    assert "disabled" in html
    assert "LabGenerationCloseLoopAction" in read_text("frontend/README.md")
    assert "LabGenerationCloseLoopAction" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")
    assert "前端不直接调用真实 LLM" in read_text("frontend/README.md")
    assert "LocalCoreGenerationWorkspace" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")
    assert "页面初始化和生成成功后" in read_text("frontend/README.md")
    assert "页面初始化和 `POST /api/labs/generate` 成功后" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")
    assert "LocalCoreGenerationWorkspace" in pages["/labs/generate"]["components"]
    assert "LocalCoreGenerationWorkspace" in pages["/labs/generate"]["dataSources"]
    assert "frontendDirectRealLlmCall=false" in pages["/labs/generate"]["dataSources"]
    assert "realLlmResultCanEnterViaCliOrBackend=true" in pages["/labs/generate"]["dataSources"]
    assert pages["/labs/generate"]["safety"]["localCoreGenerationWorkspace"] is True
    assert pages["/labs/generate"]["safety"]["frontendDirectRealLlmCall"] is False
    assert pages["/labs/generate"]["safety"]["realLlmResultCanEnterViaCliOrBackend"] is True
    assert "LabGenerationCloseLoopAction.initialContextLinks" in pages["/labs/generate"]["dataSources"]


def test_labs_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/labs.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型：禁用" in html
    assert "自动发布：禁用" in html
    assert "批量状态变更：禁用" in html
    assert "真实发布：禁用" in html
    assert "密钥展示：禁用" in html
    assert "GET /api/labs" in html
    assert "GET /api/review-task-summary" in html
    assert "/labs/generate" in html
    assert "/labs/:id/review" in html
    assert "LabDslPreview" in html
    assert "WAITING_REVIEW" in html
    assert "autoPublishAllowed=false" in html
    assert "batchStateChangeAllowed=false" in html
    assert "realPublish=false" in html
    assert "disabled" in html


def test_agent_entities_static_prototype_is_readonly_mock_store():
    html = (ROOT / "frontend/agent-entities.html").read_text(encoding="utf-8")
    mock_data = load_json("frontend/mock-data.json")
    manifest = load_json("frontend/ui.manifest.json")
    prototype = mock_data["agentEntitiesPrototype"]
    pages = {page["route"]: page for page in manifest["pages"]}
    prototypes = {page["route"]: page for page in manifest["staticPrototypes"]}

    assert "平台实体草稿 Mock Store" in html
    assert "GET /api/platform-entities" in html
    assert "GET /api/platform-entities/{id}" in html
    assert "GET /api/platform-entities/readiness-report" in html
    assert "平台导入核查报告" in html
    assert "AgentEntityReadinessReport" in html
    assert "READY_FOR_MANUAL_PLATFORM_REVIEW" in html
    assert "NEEDS_PREVIEW_OR_MOCK_IMPORT" in html
    assert "dryRunPrepared=" in html
    assert "requestSent=" in html
    assert "resultRecorded=" in html
    assert "AgentEntityPausedBackendHandoffNotice" in html
    assert "platform-paused-backend-handoff-panel" in html
    assert "platform-paused-backend-handoff-summary" in html
    assert "platform-paused-backend-handoff-detail" in html
    assert "renderPausedBackendHandoffPanel" in html
    assert "local_core_mvp_stop_line=import-dry-run" in html
    assert "platformBackendRequired=false" in html
    assert "future-platform-handoff" in html
    assert "PLATFORM_BACKEND_ACTION_PAUSED" in html
    assert "AgentEntityFinalPublishReviewPanel" not in html
    assert "FinalPublishReviewDecision" not in html
    assert "platform-final-publish-review-panel" not in html
    assert "handleFinalPublishReviewDecision" not in html
    assert "readyForAgentEntitySignoff" in html
    assert "latestPlatformStatus=" in html
    assert "frontend/mock-data.json.agentEntitiesPrototype.readinessReport" in html
    assert "URLSearchParams(window.location.search)" in html
    assert "params.get(\"entityId\")" in html
    assert "params.get(\"sourceTaskId\")" in html
    assert "params.get(\"entityKind\")" in html
    assert "params.get(\"action\")" in html
    assert "params.get(\"coreDbPath\")" in html
    assert "params.get(\"gradingDbPath\")" in html
    assert "params.get(\"agentReport\")" in html
    assert "withReadinessQuery" in html
    assert "withCoreDbQuery" in html
    assert "withCoreDbBody" in html
    assert "coreDbPath: state.coreDbPath" in html
    assert "gradingDbPath: state.gradingDbPath" in html
    assert "agentReport: state.agentReport" in html
    assert "loadedFromFallback: false" in html
    assert "state.loadedFromFallback = true" in html
    assert "if (state.loadedFromFallback)" in html
    assert "source=GET /api/platform-entities" in html
    assert "detail=GET /api/platform-entities/{id}" in html
    assert "?coreDbPath={path}" in html
    assert "requestedEntityId" in html
    assert "requestedSourceTaskId" in html
    assert "requestedEntityKind" in html
    assert "requestedAction" in html
    assert "PAUSED_ACTION_REQUESTED" in html
    assert "autoPost=false" in html
    assert "frontend/mock-data.json.reviewCenterPrototype.agentEntityMockImportSummary" in html
    assert "lab_template" in html
    assert "exam_question" in html
    assert "grading_rule" in html
    assert "ppt_deck" in html
    assert "mockStoreWritten=true" in html
    assert "databaseWritten=false" in html
    assert "realAgentImport=false" in html
    assert "realPublish=false" in html
    assert "method: \"GET\"" in html
    assert "method: \"POST\"" in html
    assert "POST /api/platform-entities/contract-validate" in html
    assert "platform-contract-config" in html
    assert "platform-contract-validate-button" in html
    assert "handleContractValidate" in html
    assert "examples/input/platform-contract.json" in html
    assert "latestContractValidation" in html
    assert "CONTRACT_VALIDATED_LOCALLY" in html
    assert "localConfigOnly=true" in html
    assert "secretsRead=false" in html
    assert "contractConfig: contractConfig" in html
    assert "POST /api/platform-entities/{id}/import-dry-run" in html
    assert "POST /api/platform-entities/{id}/import-send" not in html
    assert "POST /api/platform-entities/{id}/import-status" not in html
    assert "POST /api/platform-entities/{id}/import-result" not in html
    assert "POST /api/platform-entities/{id}/signoff" not in html
    assert "POST /api/platform-entities/{id}/final-publish-review-decision" not in html
    assert "return loadReadiness()" in html
    assert "readinessUpdated=true" in html
    assert "准备演示草稿" in html
    assert "AgentEntityDemoDataPrepareAction" in html
    assert "platform-demo-prepare-task-select" in html
    assert "platform-demo-load-approved-tasks-button" in html
    assert "GET /api/ai-tasks?status=APPROVED&amp;taskType={taskType}" in html
    assert "loadApprovedTaskCandidates" in html
    assert "APPROVED_TASKS_LOADED" in html
    assert "platform-demo-prepare-button" in html
    assert "POST /api/labs/import-preview" in html
    assert "POST /api/labs/mock-import" in html
    assert "POST /api/exams/import-preview" in html
    assert "POST /api/exams/mock-import" in html
    assert "POST /api/grading/import-preview" in html
    assert "POST /api/grading/mock-import" in html
    assert "POST /api/ppt/import-preview" in html
    assert "POST /api/ppt/mock-import" in html
    assert 'ppt: "PPT_GENERATION"' in html
    assert "safePostJson(config.previewApi, withCoreDbBody({" in html
    assert "safePostJson(config.mockImportApi, withCoreDbBody({" in html
    assert '"/import-dry-run", withCoreDbBody({' in html
    assert 'var contractConfig = fieldValue("platform-contract-config")' in html
    assert "repositoryContext" in html
    assert "autoApproveAllowed=false" in html
    assert "DEMO_DRAFT_READY" in html
    assert "platform-import-dry-run-button" in html
    assert "platform-import-send-button" not in html
    assert "platform-import-status-button" not in html
    assert "platform-import-result-button" not in html
    assert "platform-signoff-button" not in html
    assert "platform-final-review-decision-button" not in html
    assert "explicitPlatformCallOptIn: true" not in html
    assert "explicitPlatformQueryOptIn: true" not in html
    assert "secretInputInFrontend=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "AgentEntityImportStatusQuery" not in html
    assert "AgentEntityImportResultRecord" not in html
    assert "AgentEntitySignoffRecord" not in html
    assert "AgentEntityImportStepper" in html or "platform-import-stepper" in html
    assert "platform-review-center-return-link" in html
    assert "appendQuery(\"review-center.html\"" in html
    assert "taskId: sourceTaskId" in html
    assert "demoKindFromEntityKind" in html
    assert "requestedEntityType" in html
    assert "findRequestedContextEntity" in html
    assert "LOCAL_ENTITY_NOT_PREPARED" in html
    assert "RequestedEntityPlaceholder" in html
    assert "isRequestedContextPlaceholder" in html
    assert "NEEDS_LOCAL_DRAFT" in html
    assert "nextLocalAction=prepare_demo_draft_or_run_mock_import" in html
    assert "blockedAction: \"POST /api/platform-entities/{id}/import-dry-run\"" in html
    assert "overflow-wrap: anywhere" in html
    assert "white-space: normal" in html
    assert ".entity-row {" in html
    assert "box-sizing: border-box" in html
    assert ".entity-row span,\n    .entity-row strong" in html
    assert "agentEntityRefresh: \"1\"" in html
    assert "coreDbPath: state.coreDbPath" in html
    assert "reviewCenterReturnRoute" in html
    assert "1 · mock-import" in html
    assert "2 · dry-run" in html
    assert "3 · review-return" in html
    assert "4 · future-platform-handoff" in html
    assert "3 · import-send" not in html
    assert "4 · import-status" not in html
    assert "platform-signoff-button" not in html
    assert "handleAgentEntitySignoff" not in html
    assert "agentEntityImportActivity" in html
    assert "latestDryRun" in html
    assert "导入真实平台" in html
    assert "发布实体" in html
    assert "disabled" in html
    assert prototype["route"] == "/platform-entities"
    assert prototype["deepLinkQueryParams"] == [
        "entityId",
        "sourceTaskId",
        "entityKind",
        "action",
        "coreDbPath",
        "gradingDbPath",
        "agentReport",
    ]
    assert prototype["source"] == "GET /api/platform-entities"
    assert prototype["coreSource"] == "GET /api/platform-entities?coreDbPath={path}"
    assert prototype["detailSource"] == "GET /api/platform-entities/{id}"
    assert prototype["coreDetailSource"] == "GET /api/platform-entities/{id}?coreDbPath={path}"
    assert prototype["readinessSource"] == "GET /api/platform-entities/readiness-report"
    assert prototype["coreReadinessSource"] == "GET /api/platform-entities/readiness-report?sourceTaskId={id}&coreDbPath={path}"
    assert (
        prototype["gradingRecordReadinessSource"]
        == "GET /api/platform-entities/readiness-report?sourceTaskId={id}&coreDbPath={path}&gradingDbPath={path}"
    )
    assert prototype["approvedTaskCandidateSource"] == "GET /api/ai-tasks?status=APPROVED&taskType={taskType}"
    assert prototype["contractValidateSource"] == "POST /api/platform-entities/contract-validate"
    assert prototype["contractConfigExamplePath"] == "examples/input/platform-contract.json"
    assert "statusQuerySource" not in prototype
    assert "resultRecordSource" not in prototype
    assert "coreResultRecordSource" not in prototype
    assert "signoffSource" not in prototype
    assert "coreSignoffSource" not in prototype
    assert "signoffDeepLinkSource" not in prototype
    assert prototype["reviewCenterReturnRouteSource"] == "review-center.html?taskId={sourceTaskId}&agentEntityRefresh=1"
    assert prototype["coreReviewCenterReturnRouteSource"] == "review-center.html?taskId={sourceTaskId}&agentEntityRefresh=1&coreDbPath={path}"
    assert (
        prototype["localContextReviewCenterReturnRouteSource"]
        == "review-center.html?taskId={sourceTaskId}&agentEntityRefresh=1&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
    )
    assert "LocalAgentEntityList.noHorizontalOverflow" in pages["/platform-entities"]["dataSources"]
    assert "LocalAgentEntityList.noHorizontalOverflow" in prototypes["/platform-entities"]["dataSources"]
    assert prototype["dryRunSource"] == "POST /api/platform-entities/{id}/import-dry-run"
    assert prototype["coreDryRunSource"] == "POST /api/platform-entities/{id}/import-dry-run body.coreDbPath"
    requested_placeholder = prototype["requestedEntityPlaceholder"]
    assert requested_placeholder["component"] == "RequestedEntityPlaceholder"
    assert requested_placeholder["status"] == "LOCAL_ENTITY_NOT_PREPARED"
    assert requested_placeholder["id"] == "requested_entity_not_prepared"
    assert requested_placeholder["nextLocalAction"] == "prepare_demo_draft_or_run_mock_import"
    assert requested_placeholder["blockedAction"] == "POST /api/platform-entities/{id}/import-dry-run"
    assert requested_placeholder["returnRoutePreservesContext"] is True
    assert requested_placeholder["safety"]["requestSent"] is False
    assert requested_placeholder["safety"]["realAgentImport"] is False
    assert requested_placeholder["safety"]["realPublish"] is False
    assert prototype["corePrepareDemoDataSource"] == (
        "POST /api/{lab|exam|grading|ppt}/import-preview body.coreDbPath -> "
        "POST /api/{lab|exam|grading|ppt}/mock-import body.coreDbPath -> "
        "POST /api/platform-entities/{id}/import-dry-run body.coreDbPath"
    )
    assert prototype["prepareDemoDataCoreBodyForwarding"] == [
        "import-preview body.coreDbPath",
        "mock-import body.coreDbPath",
        "import-dry-run body.coreDbPath",
        "import-dry-run body.contractConfig",
    ]
    paused_handoff = prototype["pausedPlatformBackendHandoff"]
    assert paused_handoff["component"] == "AgentEntityPausedBackendHandoffNotice"
    assert paused_handoff["platformBackendRequired"] is False
    assert paused_handoff["platformApiTokenRequired"] is False
    assert paused_handoff["defaultActionEnabled"] is False
    assert paused_handoff["pausedActions"] == [
        "import-send",
        "import-status",
        "import-result",
        "platform-signoff",
        "final-publish",
    ]
    assert prototype["prepareDemoDataSource"].startswith("POST /api/{lab|exam|grading|ppt}/import-preview")
    assert prototype["activitySource"] == "GET /api/platform-entities/{id}.agentEntityImportActivity"
    assert prototype["coreActivitySource"] == "GET /api/platform-entities/{id}?coreDbPath={path}.agentEntityImportActivity"
    assert prototype["stepperComponent"] == "AgentEntityImportStepper"
    contract_validate_action = prototype["contractValidateAction"]
    assert contract_validate_action["component"] == "PlatformApiContractValidateAction"
    assert contract_validate_action["source"] == "POST /api/platform-entities/contract-validate"
    assert contract_validate_action["contractConfigExamplePath"] == "examples/input/platform-contract.json"
    assert contract_validate_action["mode"] == "LOCAL_PLATFORM_API_CONTRACT_VALIDATION"
    assert contract_validate_action["nextAction"] == "use_same_contract_config_for_local_dry_run"
    assert contract_validate_action["safety"]["requestSent"] is False
    assert contract_validate_action["safety"]["secretsRead"] is False
    assert contract_validate_action["safety"]["realAgentImport"] is False
    assert contract_validate_action["safety"]["realPublish"] is False
    paused_notice = prototype["pausedBackendHandoffNotice"]
    assert paused_notice["component"] == "AgentEntityPausedBackendHandoffNotice"
    assert paused_notice["mode"] == "LOCAL_CORE_MVP_STOP_LINE"
    assert paused_notice["stopLine"] == "mock-import + import-dry-run DTO"
    assert paused_notice["safety"]["platformBackendRequired"] is False
    assert paused_notice["safety"]["platformApiTokenRequired"] is False
    assert paused_notice["safety"]["requestSent"] is False
    assert prototype["fallbackSource"] == "frontend/mock-data.json.reviewCenterPrototype.agentEntityMockImportSummary"
    assert prototype["summary"]["total"] == 3
    import_stepper = prototype["importStepper"]
    assert import_stepper["component"] == "AgentEntityImportStepper"
    assert import_stepper["steps"] == [
        "mock-import",
        "dry-run",
        "review-return",
        "future-platform-handoff",
    ]
    assert "agentEntityImportActivity.latestDryRun" in import_stepper["uses"]
    assert "pausedPlatformBackendHandoff.pausedActions" in import_stepper["uses"]
    assert import_stepper["safety"]["platformBackendRequired"] is False
    assert import_stepper["safety"]["requiresFinalHumanReview"] is False
    assert import_stepper["safety"]["secretVisibleInFrontend"] is False
    assert import_stepper["safety"]["realPublish"] is False
    prepare_action = prototype["prepareDemoDataAction"]
    assert prepare_action["component"] == "AgentEntityDemoDataPrepareAction"
    assert prepare_action["approvedTaskCandidateSource"] == "GET /api/ai-tasks?status=APPROVED&taskType={taskType}"
    assert prepare_action["taskTypeMapping"] == {
        "lab": "LAB_GENERATION",
        "exam": "EXAM_GENERATION",
        "grading": "GRADING_GENERATION",
    }
    assert prepare_action["sequence"] == ["import-preview", "mock-import", "import-dry-run"]
    assert prepare_action["coreBodyForwarding"] == [
        "import-preview body.coreDbPath",
        "mock-import body.coreDbPath",
        "import-dry-run body.coreDbPath",
        "import-dry-run body.contractConfig",
    ]
    assert prepare_action["contractConfigSource"] == "examples/input/platform-contract.json"
    assert "POST /api/labs/import-preview" in prepare_action["apiOptions"]["lab"]
    assert "POST /api/exams/mock-import" in prepare_action["apiOptions"]["exam"]
    assert "POST /api/grading/mock-import" in prepare_action["apiOptions"]["grading"]
    assert prepare_action["safety"]["approvedTaskQueryReadOnly"] is True
    assert prepare_action["safety"]["autoApproveAllowed"] is False
    assert prepare_action["safety"]["realAgentImport"] is False
    assert prepare_action["safety"]["requestSent"] is False
    assert prepare_action["safety"]["realPublish"] is False
    readiness_report = prototype["readinessReport"]
    assert readiness_report["component"] == "AgentEntityReadinessReport"
    assert readiness_report["summary"]["requiredTotal"] == 3
    assert readiness_report["summary"]["allReadyForManualPlatformReview"] is True
    assert "dryRunPreparedTotal" in readiness_report["summary"]
    assert "requestSentTotal" in readiness_report["summary"]
    assert "statusQueriedTotal" in readiness_report["summary"]
    assert "resultRecordedTotal" in readiness_report["summary"]
    assert "agentEntitySignoffRecordedTotal" in readiness_report["summary"]
    assert "postSignoffPrePublishReadyTotal" in readiness_report["summary"]
    assert "finalPublishReviewDecisionRecordedTotal" in readiness_report["summary"]
    assert "allFinalPublishReviewDecisionsRecorded" in readiness_report["summary"]
    assert readiness_report["summary"]["allPostSignoffPrePublishReady"] is False
    assert {item["agentEntity"] for item in readiness_report["items"]} == {
        "lab_template",
        "exam_question",
        "grading_rule",
    }
    assert all("dryRunPrepared" in item for item in readiness_report["items"])
    assert all("requestSent" in item for item in readiness_report["items"])
    assert all("resultRecorded" in item for item in readiness_report["items"])
    assert all("signoffRecorded" in item for item in readiness_report["items"])
    assert all("postSignoffPrePublishChecklist" in item for item in readiness_report["items"])
    assert all("finalPublishReviewDecision" in item for item in readiness_report["items"])
    assert all(item["finalPublishReviewDecision"]["component"] == "FinalPublishReviewDecisionSummary" for item in readiness_report["items"])
    assert all(
        item["postSignoffPrePublishChecklist"]["component"] == "AgentEntityPostSignoffPrePublishChecklist"
        for item in readiness_report["items"]
    )
    assert all(
        item["postSignoffPrePublishChecklist"]["entitySpecificReviewFocus"]["component"]
        == "AgentEntitySpecificPrePublishReviewFocus"
        for item in readiness_report["items"]
    )
    assert all(item["readyForManualAgentReview"] is True for item in readiness_report["items"])
    assert readiness_report["safety"]["databaseWritten"] is False
    assert readiness_report["safety"]["realAgentImport"] is False
    assert readiness_report["safety"]["realPublish"] is False
    assert prototype["summary"]["databaseWritten"] is False
    assert prototype["summary"]["realAgentImport"] is False
    assert prototype["summary"]["realPublish"] is False
    assert prototype["actions"]["viewListEnabled"] is True
    assert prototype["actions"]["viewDetailEnabled"] is True
    assert prototype["actions"]["demoDataPrepareEnabled"] is True
    assert prototype["actions"]["realAgentImportDryRunEnabled"] is True
    assert prototype["actions"]["realAgentImportSendEnabled"] is False
    assert prototype["actions"]["realAgentImportStatusQueryEnabled"] is False
    assert prototype["actions"]["manualImportResultRecordEnabled"] is False
    assert prototype["actions"]["manualAgentEntitySignoffEnabled"] is False
    assert prototype["actions"]["manualSignoffActionDeepLinkEnabled"] is False
    assert prototype["actions"]["pausedPlatformBackendHandoffVisible"] is True
    assert prototype["actions"]["realAgentImportEnabled"] is False
    assert prototype["actions"]["realPublishEnabled"] is False
    assert prototype["safety"]["readOnly"] is True
    assert prototype["safety"]["demoDataPrepareEnabled"] is True
    assert prototype["safety"]["realAgentImportDryRunEnabled"] is True
    assert prototype["safety"]["realAgentImportSendEnabled"] is False
    assert prototype["safety"]["realAgentImportStatusQueryEnabled"] is False
    assert prototype["safety"]["manualImportResultRecordEnabled"] is False
    assert prototype["safety"]["manualAgentEntitySignoffEnabled"] is False
    assert prototype["safety"]["manualSignoffActionDeepLinkEnabled"] is False
    assert prototype["safety"]["manualSignoffActionDeepLinkAutoPost"] is False
    assert prototype["safety"]["platformBackendRequired"] is False
    assert prototype["safety"]["pausedPlatformBackendHandoff"] is True
    assert prototype["safety"]["secretInputInFrontend"] is False
    assert prototype["safety"]["answerVisibleToCandidate"] is False


def test_ppt_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/ppt.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型：禁用" in html
    assert "真实 PPT 文件生成：禁用" in html
    assert "自动发布：禁用" in html
    assert "真实发布：禁用" in html
    assert "密钥展示：禁用" in html
    assert "GET /api/ppt" in html
    assert "POST /api/ppt/generate" in html
    assert "GET /api/review-task-summary" in html
    assert "/ppt/generate" in html
    assert "/ppt/:id/review" in html
    assert "PptDslPreview" in html
    assert "WAITING_REVIEW" in html
    assert "realLlmCalled=false" in html
    assert "artifactGenerated=false" in html
    assert "realPptFileGenerated=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "disabled" in html


def test_ppt_review_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/ppt-review.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型：禁用" in html
    assert "真实 PPT 文件生成：禁用" in html
    assert "自动发布：禁用" in html
    assert "真实发布：禁用" in html
    assert "批量状态变更：禁用" in html
    assert "密钥展示：禁用" in html
    assert "GET /api/review-tasks/{id}" in html
    assert "review-detail-data.js" in html
    assert "review-action-data.js" in html
    assert "POST /api/ai-tasks/{id}/approve" in html
    assert "POST /api/ai-tasks/{id}/reject" in html
    assert "GET /api/audit-events" in html
    assert "PPT DSL" in html
    assert "PptDslPreview" in html
    assert "Slide Plan" in html
    assert "AiTaskTimeline" in html
    assert "WAITING_REVIEW" in html
    assert "reviewRequired=true" in html
    assert "rejectRequiresReason=true" in html
    assert "auditTrailRequired=true" in html
    assert "artifactGenerated=false" in html
    assert "realPptFileGenerated=false" in html
    assert "pptxArtifactGenerated=true" in html
    assert "PPTX Artifact" in html
    assert "PPTX_FILE" in html
    assert "real-llm-demo-ppt-artifact.pptx" in html
    assert "real-llm-demo-ppt-artifact-manifest.json" in html
    assert "slideCount" in html
    assert "bytes" in html
    assert "previewAvailable" in html
    assert "renderAttempted" in html
    assert "firstSlidePreview" in html
    assert "imagePath=examples/output/real-llm-demo-ppt-artifact-slide-01.png" in html
    assert "../examples/output/real-llm-demo-ppt-artifact-slide-01.png" in html
    assert "PageReviewStatus" in html


def test_review_center_static_prototype_has_revision_loop_panel():
    html = (ROOT / "frontend/review-center.html").read_text(encoding="utf-8")

    assert "ReviewRevisionLoopPanel" in html
    assert "frontend/mock-data.json.reviewRevisionPrototype" in html
    assert "POST /api/review-tasks/{id}/revision-request" in html
    assert "GET /api/review-tasks/{id}/revision-requests" in html or "revision-requests" in html
    assert "POST /api/review-tasks/{id}/regenerate-mock" in html
    assert "REVIEW_REVISION_REQUEST" in html
    assert "REVIEW_MOCK_REGENERATE" in html
    assert "task_lab_demo_revision" in html
    assert "workflow_run_review_mock_regeneration_demo" in html
    assert "artifact_lab_revision_demo" in html
    assert "sourceTaskStatusUnchanged=true" in html
    assert "newLlmRequestSent=false" in html
    assert "realLlmCalled=false" in html
    assert "autoApproveAllowed=false" in html
    assert "realPublishAllowed=false" in html


def test_lab_review_static_prototype_has_revision_loop_controls():
    html = (ROOT / "frontend/lab-review.html").read_text(encoding="utf-8")

    assert "POST /api/review-tasks/{id}/revision-request" in html
    assert "POST /api/review-tasks/{id}/regenerate-mock" in html
    assert "reviewPage.actionBar.requestRevision.enabled=true" in html
    assert "reviewRevisionPrototype.revisionRequests[0].priority=HIGH" in html
    assert "sourceRevisionRequestId=op_audit_review_revision_request_demo" in html
    assert "newTaskId=task_lab_demo_revision" in html
    assert "newTaskStatus=WAITING_REVIEW" in html
    assert "newDslPath=examples/output/task_lab_demo-lab-revision.json" in html
    assert "sourceTaskStatusUnchanged=true" in html
    assert "newLlmRequestSent=false" in html
    assert "realLlmCalled=false" in html
    assert "autoApproveAllowed=false" in html
    assert "realPublishAllowed=false" in html
    assert "Mock 再生成" in html


def test_lab_review_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/lab-review.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型结果：只读" in html
    assert "真实云资源：禁用" in html
    assert "自动发布：禁用" in html
    assert "真实发布：禁用" in html
    assert "批量状态变更：禁用" in html
    assert "GET /api/review-tasks/{id}" in html
    assert "POST /api/ai-tasks/{id}/approve" in html or "通过" in html
    assert "POST /api/ai-tasks/{id}/reject" in html or "驳回" in html
    assert "LabDslPreview" in html
    assert "AiTaskTimeline" in html
    assert "generationProfile" in html
    assert "reviewPage.generationProfile.context" in html
    assert "qualitySignals.lab.matching" in html
    assert "materialCoverage.status=LINKED" in html
    assert "providerSummary" in html
    assert "openai_responses_sdk_adapter" in html
    assert "providerSummary.qualitySummary" in html
    assert "reviewPage.providerSummary.qualitySummary.readyForReview=true" in html
    assert "reviewPage.providerSummary.calls[0].qualitySummary.normalizationPatchCount=1" in html
    assert "calls[0].qualitySummary.readyForReview" in html
    assert "calls[0].responseId" in html
    assert "resp_demo_lab_quality" in html
    assert "set.metadata.category" in html
    assert "normalizationPatchCount" in html
    assert "schemaRepairApplied" in html
    assert "providerIds" in html
    assert "NEEDS_REVIEW" in html
    assert "stepGranularity.matched" in html
    assert "qualitySummary / qualitySignals 只辅助人工审核" in html
    assert "WAITING_REVIEW" in html
    assert "rejectRequiresReason=true" in html
    assert "auditTrailRequired=true" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublishAllowed=false" in html
    assert "answerVisibleToCandidate" in html or "选手" not in html
    assert "disabled" in html


def test_ppt_generate_local_core_workspace_has_api_loader_and_review_stop():
    html = (ROOT / "frontend/ppt-generate.html").read_text(encoding="utf-8")
    script = (ROOT / "frontend/ppt-generate-data.js").read_text(encoding="utf-8")

    assert "LOCAL_CORE_MVP" in html
    assert 'id="ppt-generate-input"' in html
    assert 'id="ppt-generate-run"' in html
    assert 'id="ppt-generate-api-state"' in html
    assert 'id="ppt-generate-review-center-link"' in html
    assert 'id="ppt-generate-review-page-link"' in html
    assert 'id="ppt-generate-import-preview-link"' in html
    assert '<script src="ppt-generate-data.js"></script>' in html
    assert 'id="ppt-generate-provider-mode"' in html
    assert 'id="ppt-generate-explicit-real-call"' in html
    assert "真实 PPT 文件：禁用" in html
    assert "自动发布：禁用" in html
    assert 'generatePath: "/api/ppt/generate"' in script
    assert "fetch(path" in script
    assert "providerRequestOptions" in script
    assert "providerMode: mode" in script
    assert "Object.assign({ input: inputPath }, providerRequestOptions())" in script
    assert "const inputPath = input ? input.value.trim() : state.defaultInput" in script
    assert "WAITING_REVIEW" in script
    assert "review-center.html" in script
    assert "ppt-review.html" in script
    assert "agent-entities.html" in script
    assert 'entityKind: "ppt"' in script
    assert "frontendDirectRealLlmCall" not in script
    assert "OPENAI_API_KEY" not in html
    assert "AGENT_API_TOKEN" not in html
    assert "/import-send" not in html
    assert "/import-status" not in html


def test_local_grading_workspace_declares_controlled_job_and_manual_record_review_contract():
    manifest = json.loads((ROOT / "frontend/ui.manifest.json").read_text(encoding="utf-8"))
    pages = {page["route"]: page for page in manifest["pages"]}
    prototypes = {prototype["route"]: prototype for prototype in manifest["staticPrototypes"]}
    html = (ROOT / "frontend/grading-workspace.html").read_text(encoding="utf-8")
    script = (ROOT / "frontend/grading-workspace-data.js").read_text(encoding="utf-8")

    assert pages["/grading/workspace"]["prototypePath"] == "frontend/grading-workspace.html"
    assert {dependency["path"] for dependency in pages["/grading/workspace"]["apiDependencies"]} == {
        "/api/grading/jobs",
        "/api/grading/jobs/{id}/run",
        "/api/grading/records",
        "/api/grading/records/{id}/review",
    }
    assert "LocalGradingWorkspace" in pages["/grading/workspace"]["components"]
    assert prototypes["/grading/workspace"]["safety"]["autoApproveAllowed"] is False
    assert prototypes["/grading/workspace"]["safety"]["realAgentImport"] is False
    assert prototypes["/grading/workspace"]["safety"]["secretVisibleInFrontend"] is False
    assert 'id="grading-workspace-create"' in html
    assert 'id="grading-workspace-run"' in html
    assert 'id="grading-workspace-review-record"' in html
    assert "POST /api/grading/jobs" in html
    assert "OPENAI_API_KEY" not in html
    assert "AGENT_API_TOKEN" not in html
    assert "/import-send" not in html
    assert "includeControlledCommand" in script
    assert '"/api/grading/jobs"' in script
    assert "/api/grading/records/" in script
    assert "autoApproveAllowed" not in script


def test_review_detail_pages_have_readonly_api_loader():
    loader_js = read_text("frontend/review-detail-data.js")

    assert "resolveTaskId" in loader_js
    assert "fetch(detailPath(taskId)" in loader_js
    assert "getQueryAgentReport" in loader_js
    assert "getQueryCoreDbPath" in loader_js
    assert "params.set(\"agentReport\", agentReport)" in loader_js
    assert "GET /api/review-tasks/{id}" in loader_js
    assert "agentReport={workflowReport}" in loader_js
    assert "coreDbPath={path}" in loader_js
    assert 'method: "GET"' in loader_js
    assert 'method: "POST"' not in loader_js
    assert "API_READONLY_LOADED" in loader_js
    assert "STATIC_HTML_FALLBACK" in loader_js
    assert "DETAIL_LOAD_FAILED" in loader_js
    assert "autoPublishAllowed: false" in loader_js
    assert "realPublishAllowed: false" in loader_js

    page_specs = [
        ("frontend/lab-review.html", "lab", "task_lab_demo"),
        ("frontend/exam-review.html", "exam", "task_exam_demo"),
        ("frontend/ppt-review.html", "ppt", "task_ppt_demo"),
        ("frontend/grading-review.html", "grading", "task_grading_demo"),
    ]
    for page_path, review_kind, default_task_id in page_specs:
        html = read_text(page_path)
        assert 'id="review-detail-api-status">STATIC_HTML_FALLBACK' in html
        assert 'id="review-detail-selected-task"' in html
        assert 'id="review-detail-task-id"' in html
        assert 'id="review-detail-task-type"' in html
        assert 'id="review-detail-artifact-total"' in html
        assert 'id="review-detail-dsl-preview"' in html
        assert 'id="review-detail-timeline-list"' in html
        assert "GET /api/review-tasks/{id}" in html
        assert (
            f'<script src="review-detail-data.js" data-review-kind="{review_kind}" '
            f'data-default-task-id="{default_task_id}"></script>'
        ) in html


def test_review_detail_routes_preserve_agent_report_query_contract():
    manifest = json.loads(read_text("frontend/ui.manifest.json"))
    routes = {
        "/labs/:id/review",
        "/exams/:id/review",
        "/grading/:id/review",
        "/ppt/:id/review",
    }
    matched_routes = set()
    for section in ("prototypes", "pages"):
        for page in manifest.get(section, []):
            if page.get("route") not in routes:
                continue
            matched_routes.add(page["route"])
            data_sources = page.get("dataSources", [])
            assert "query: agentReport" in data_sources
            assert "GET /api/review-tasks/{id}?agentReport={workflowReport}.reviewDetail" in data_sources
    assert matched_routes == routes


def test_review_detail_pages_have_manual_review_action_loader():
    action_js = read_text("frontend/review-action-data.js")

    assert "postReviewAction" in action_js
    assert "/api/ai-tasks/{id}/{action}" in action_js
    assert 'method: "POST"' in action_js
    assert '"Content-Type": "application/json"' in action_js
    assert "reviewer is required" in action_js
    assert "rejectRequiresReason=true" in action_js
    assert "ACTION_APPROVED_RECORDED" in action_js
    assert "ACTION_REJECTED_RECORDED" in action_js
    assert "autoPublishAllowed: false" in action_js
    assert "realPublishAllowed: false" in action_js
    assert "/publish" not in action_js
    assert "batch" not in action_js.lower()

    for page_path in ["frontend/lab-review.html", "frontend/exam-review.html", "frontend/ppt-review.html"]:
        html = read_text(page_path)
        assert "ManualReviewAction" in html
        assert 'id="review-action-status">ACTION_STATIC_FALLBACK' in html
        assert 'id="review-action-reviewer"' in html
        assert 'id="review-action-reason"' in html
        assert 'data-review-action="approve"' in html
        assert 'data-review-action="reject"' in html
        assert "review-action-data.js" in html
        assert "POST /api/ai-tasks/{id}/approve" in html
        assert "POST /api/ai-tasks/{id}/reject" in html
        assert "rejectRequiresReason=true" in html
        assert "autoPublishAllowed=false" in html
        assert "realPublishAllowed=false" in html


def test_review_pages_have_platform_import_preview_action_loader():
    import_js = read_text("frontend/review-import-preview-data.js")

    assert "createImportPreview" in import_js
    assert "createMockImport" in import_js
    assert "/api/labs/import-preview" in import_js
    assert "/api/exams/import-preview" in import_js
    assert "/api/grading/import-preview" in import_js
    assert "/api/ppt/import-preview" in import_js
    assert "/api/labs/mock-import" in import_js
    assert "/api/exams/mock-import" in import_js
    assert "/api/grading/mock-import" in import_js
    assert "/api/ppt/mock-import" in import_js
    assert 'if (entityType === "ppt_deck")' in import_js
    assert '["coreDbPath", "gradingDbPath", "agentReport"]' in import_js
    assert 'next.coreDbPath = coreDbPath' in import_js
    assert "JSON.stringify(requestBody({" in import_js
    assert "agent-entities.html?" in import_js
    assert "sourceTaskId" in import_js
    assert "entityKind" in import_js
    assert 'method: "POST"' in import_js
    assert "requiresApprovedTask=true" in import_js
    assert "requiresImportPreview=true" in import_js
    assert "IMPORT_PREVIEW_CREATED" in import_js
    assert "IMPORT_PREVIEW_FAILED" in import_js
    assert "MOCK_IMPORT_CREATED" in import_js
    assert "MOCK_IMPORT_FAILED" in import_js
    assert "databaseWritten=false" in import_js
    assert "realAgentImport=false" in import_js
    assert "realPublishAllowed=false" in import_js
    assert "realPublish=false" in import_js
    assert "/publish" not in import_js

    page_specs = [
        ("frontend/lab-review.html", "lab", "/api/labs/import-preview", "/api/labs/mock-import"),
        ("frontend/exam-review.html", "exam", "/api/exams/import-preview", "/api/exams/mock-import"),
        ("frontend/grading-review.html", "grading", "/api/grading/import-preview", "/api/grading/mock-import"),
        ("frontend/ppt-review.html", "ppt", "/api/ppt/import-preview", "/api/ppt/mock-import"),
    ]
    for page_path, import_kind, endpoint, mock_endpoint in page_specs:
        html = read_text(page_path)
        assert "AgentImportPreviewAction" in html
        assert "AgentEntityMockImportAction" in html
        assert 'id="agent-import-preview-status">IMPORT_PREVIEW_STATIC_FALLBACK' in html
        assert 'id="agent-import-preview-detail"' in html
        assert 'id="agent-import-preview-button"' in html
        assert 'id="agent-mock-import-status">MOCK_IMPORT_STATIC_FALLBACK' in html
        assert 'id="agent-mock-import-detail"' in html
        assert 'id="agent-mock-import-button"' in html
        assert 'id="agent-mock-import-link"' in html
        assert endpoint in html
        assert mock_endpoint in html
        assert "agent-entities.html?entityKind=" in html
        assert "requiresApprovedTask=true" in html
        assert "requiresImportPreview=true" in html
        assert "mockStoreWritten=true" in html
        assert "databaseWritten=false" in html
        assert "realAgentImport=false" in html
        assert "realPublishAllowed=false" in html
        assert "realPublish=false" in html
        assert f'<script src="review-import-preview-data.js" data-import-kind="{import_kind}"></script>' in html

def test_grading_report_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/grading-report.html").read_text(encoding="utf-8")
    loader_js = (ROOT / "frontend/grading-report-data.js").read_text(encoding="utf-8")

    assert "persistResolvedReportFile" in loader_js
    assert "latestRecordReportPath" in loader_js

    assert "LOCAL_CORE_MVP" in html
    assert "本地评分报告：只读加载" in html
    assert "评分执行：本页不发起" in html
    assert "选手代码：本页不执行" in html
    assert "未知 Shell：本页不执行" in html
    assert "真实发布：禁用" in html
    assert "GET /api/grading/report" in html
    assert "GET /api/audit-events" in html
    assert "本地核心评分报告" in html
    assert "mock_grading_runner" in html
    assert "MOCK_PLAN_ONLY" in html
    assert "CONTAINER_PLAN_ONLY" in html
    assert "containerSandboxPlan" in html
    assert "containerPlan.image" in html
    assert "python:3.11-slim" in html
    assert "mounts[0].mode" in html
    assert "read_only" in html
    assert "resultPlaceholder.status" in html
    assert "NOT_EXECUTED" in html
    assert "containerStarted" in html
    assert "commandPreview" in html
    assert "reportDetail" in html
    assert "ReadonlyReportDetail" in html
    assert "ControlledDockerEvidence" in html
    assert "ControlledDockerEvidenceDemo.source=grade sandbox-run --execution-mode controlled-command" in html
    assert "realDemoPrototype.controlledDockerEvidenceDemo" in html
    assert "CONTROLLED_DOCKER_SANDBOX_POC" in html
    assert "EvidenceAutoSummary" in html
    assert "EvidenceAutoExecutionMatrix" in html
    assert "EvidenceAutoScorePreview" in html
    assert "ReviewerSafetySummary" in html
    assert "reviewer-safety-summary-list" in html
    assert "reviewer-safety-summary-status" in html
    assert "GET /api/grading/report?file={file}.report.reviewerSafetySummary" in html
    assert "readyForApproveReadyDecision=false" in html
    assert "evidence-auto-matrix-status" in html
    assert "evidence-auto-matrix-list" in html
    assert "evidence-auto-next-action-detail" in html
    assert "GRADING_EVIDENCE_AUTO_EXECUTION_MATRIX" in html
    assert "evidence-auto-score-preview-status" in html
    assert "evidence-auto-score-preview-summary" in html
    assert "evidence-auto-score-preview-missing-list" in html
    assert "GRADING_EVIDENCE_AUTO_SCORE_PREVIEW" in html
    assert "PARTIAL_SCORE_PREVIEW_NEEDS_MORE_EVIDENCE" in html
    assert "GET /api/grading/report?file={file}.report.scorePreview" in html
    assert "nextCoreAction=run_evidence_auto_with_controlled_command" in html
    assert "evidence-auto-review-center-link" in html
    assert "review-center.html?taskId=task_grading_demo&amp;decision=needs-evidence&amp;source=grading-report-next-core-action" in html
    assert "setEvidenceAutoReviewCenterLink" in loader_js
    assert "byId(\"evidence-auto-review-center-link\")" in loader_js
    assert "ReviewerReportWorkspace" in html
    assert ".reviewer-workspace > *" in html
    assert ".reviewer-actions > *" in html
    assert ".section-head > *" in html
    assert "overflow-wrap: anywhere" in html
    assert "white-space: normal" in html
    assert ".content-grid > *" in html
    assert "max-width: 100%;" in html
    assert ".callout h3" in html
    assert ".callout p" in html
    assert "reviewer-workspace-summary" in html
    assert "reviewer-workspace-state" in html
    assert "reviewer-workspace-score" in html
    assert "reviewer-workspace-evidence" in html
    assert "reviewer-workspace-decision" in html
    assert "reviewer-workspace-record" in html
    assert "reviewer-workspace-candidate-safety" in html
    assert "reviewer-workspace-next-action" in html
    assert "reviewer-workspace-review-center-link" in html
    assert "reviewer-workspace-safety" in html
    assert "grading-report-reviewer-workspace" in html
    assert "GradingResultPreview" in html
    assert "grading-result-preview-status" in html
    assert "grading-result-preview-summary" in html
    assert "grading-result-preview-list" in html
    assert "GET /api/grading/result-preview?report={file}&amp;taskId={id}" in html
    assert "candidateSafe=true" in html
    assert "READ_EXISTING_GRADING_REPORT_ONLY" in html
    assert "answerVisibleToCandidate=false" in html
    assert "gradingRefVisibleToCandidate=false" in html
    assert "GradingEvidenceReadiness" in html
    assert "grading-evidence-readiness-status" in html
    assert "grading-evidence-readiness-summary" in html
    assert "grading-evidence-readiness-list" in html
    assert "grading-evidence-readiness-actions" in html
    assert "GET /api/grading/evidence-readiness?report={file}" in html
    assert "readExistingReportsOnly=true" in html
    assert "GRADING_EVIDENCE_READINESS" in html
    assert "sandboxExecutedByReadiness=false" in html
    assert "contestantCodeExecutedByReadiness=false" in html
    assert "evidence-auto-status" in html
    assert "evidence-auto-summary" in html
    assert "evidence-auto-step-list" in html
    assert "GRADING_EVIDENCE_AUTO_REPORT" in html
    assert "MergedEvidenceSourceChain" in html
    assert "ManualReviewActionChecklist" in html
    assert "GET /api/grading/report?file={file}.report.manualReviewChecklist" in html
    assert "manualChecklistStatus=STATIC_HTML_FALLBACK" in html
    assert "decisionNoteRecommendation=needs-evidence" in html
    assert "collect_controlled_command_evidence_before_decision_note" in html
    assert "recommendedDecision=needs-evidence" in html
    assert "ReviewDecisionHints" in html
    assert "review-decision-hint-list" in html
    assert "review-decision-hint-summary" in html
    assert "ReviewDecisionNotes" in html
    assert "ReviewDecisionOutcome" in html
    assert "GradingRecordReviewSummary" in html
    assert "grading-record-review-status" in html
    assert "grading-record-review-summary" in html
    assert "grading-record-review-list" in html
    assert "GET /api/grading/records?taskId={id}" in html
    assert "fallbackSource=GET /api/review-tasks/{id}.reviewDetail.gradingRecords.reviewIntegration" in html
    assert "recordReviewState=STATIC_HTML_FALLBACK" in html
    assert "agentApiRequired=false" in html
    assert "commandExecutedFromPage=false" in html
    assert "review-decision-note-list" in html
    assert "review-decision-note-summary" in html
    assert "review-decision-outcome-status" in html
    assert "review-decision-outcome-list" in html
    assert "WAITING_REVIEW_DECISION_NOTE" in html
    assert "manualApproveStillRequired=true" in html
    assert "GET /api/grading/report?file={file}&amp;taskId={id}.reviewDecisionNotes" in html
    assert "reviewerKeepsFinalDecision=true" in html
    assert "overallHint=NEEDS_EVIDENCE" in html
    assert "CheckEvidenceDetailPanel" in html
    assert "check-evidence-detail-list" in html
    assert "check-evidence-detail-summary" in html
    assert "detailItemTotal=4" in html
    assert "inputSummary=stdout_contains expected token" in html
    assert "grading-report-data.js" in html
    assert "grading-report-api-state" in html
    assert "grading-report-total-score" in html
    assert "grading-report-earned-score" in html
    assert "grading-report-check-summary" in html
    assert "grading-report-reportPath" not in html
    assert "apiStatus=STATIC_HTML_FALLBACK" in html
    assert "API_READONLY_LOADED" in loader_js
    assert "/api/grading/report" in loader_js
    assert "renderReportSummary" in loader_js
    assert 'function renderReportSummary(reportData, taskId, sourceLabel) {\n    var report = reportData && reportData.report ? reportData.report : {};\n    var detail = reportData && reportData.reportDetail ? reportData.reportDetail : {};\n    var reportSummary = report.summary || {};\n    var scorePreview = report.scorePreview || {};' in loader_js
    assert "reportSummary.totalScore" in loader_js
    assert "scorePreview.earnedScore" in loader_js
    assert 'document.readyState === "loading"' in loader_js
    assert "grading-report-api-state" in loader_js
    assert "grading-report-total-score" in loader_js
    assert "grading-report-earned-score" in loader_js
    assert "grading-report-check-summary" in loader_js
    assert "grading-report-executed-total" in loader_js
    assert "noExecutionFromPage=true" in loader_js
    assert "resolveReportFile" in loader_js
    assert "gradingReportPath" in loader_js
    assert "gradingResultPreviewPath" in loader_js
    assert "shouldSendAuxiliaryTaskId" in loader_js
    assert "value.indexOf(\"task_\") === 0" in loader_js
    assert "value.indexOf(\"real_demo_\") === 0" in loader_js
    assert "renderGradingResultPreview" in loader_js
    assert "loadGradingResultPreview" in loader_js
    assert "/api/grading/result-preview" in loader_js
    assert "resultPreviewStatus=API_READONLY_LOADED" in loader_js
    assert "gradingEvidenceReadinessPath" in loader_js
    assert "renderGradingEvidenceReadiness" in loader_js
    assert "loadGradingEvidenceReadiness" in loader_js
    assert "/api/grading/evidence-readiness" in loader_js
    assert "readinessStatus=API_READONLY_LOADED" in loader_js
    assert "GRADING_REPORT_LOADED_WITHOUT_MERGED_EVIDENCE" in loader_js
    assert "GRADING_REPORT_LOAD_FAILED" in loader_js
    assert "applyAutoEvidenceReport" in loader_js
    assert "autoEvidenceItems" in loader_js
    assert "renderAutoSteps" in loader_js
    assert "renderAutoExecutionMatrix" in loader_js
    assert "renderAutoScorePreview" in loader_js
    assert "renderReviewerSafetySummary" in loader_js
    assert "reviewerSafetySummary" in loader_js
    assert "reviewer-safety-summary-list" in loader_js
    assert "reviewer-safety-summary-status" in loader_js
    assert "readyForApproveReadyDecision" in loader_js
    assert "contestantCodeExecutedInControlledSandbox" in loader_js
    assert "executionMatrix" in loader_js
    assert "scorePreview" in loader_js
    assert "scorePreviewStatus=API_READONLY_LOADED" in loader_js
    assert "GradingEvidenceAutoScorePreview" in loader_js
    assert "nextCoreAction" in loader_js
    assert "reviewDecisionFromNextAction" in loader_js
    assert "reviewCenterDecisionHref" in loader_js
    assert "appendReviewContext" in loader_js
    assert "resolveCoreDbPath" in loader_js
    assert "resolveGradingDbPath" in loader_js
    assert "resolveAgentReport" in loader_js
    assert "params.set(\"coreDbPath\", coreDbPath)" in loader_js
    assert "params.set(\"gradingDbPath\", gradingDbPath)" in loader_js
    assert "params.set(\"agentReport\", agentReport)" in loader_js
    assert "setReviewerWorkspaceReviewLink" in loader_js
    assert "updateReviewerWorkspaceFromReport" in loader_js
    assert "updateReviewerWorkspaceFromAutoEvidence" in loader_js
    assert "updateReviewerWorkspaceFromEvidenceReadiness" in loader_js
    assert "updateReviewerWorkspaceFromResultPreview" in loader_js
    assert "updateReviewerWorkspaceFromDecisionNotes" in loader_js
    assert "updateReviewerWorkspaceFromGradingRecord" in loader_js
    assert "grading-report-next-core-action" in loader_js
    assert "grading-report-reviewer-workspace" in loader_js
    assert "evidence-auto-matrix-ready" in loader_js
    assert "evidence-auto-next-action" in loader_js
    assert "GRADING_EVIDENCE_AUTO_REPORT" in loader_js
    assert "readonlyReportIncluded=" in loader_js
    assert "controlledCommandRequested=" in loader_js
    assert "/api/review-tasks/{id}" in loader_js
    assert "mergedGradingEvidence" in loader_js
    assert "checkEvidenceReviewItems" in loader_js
    assert "renderManualReviewActions" in loader_js
    assert "renderManualReviewChecklist" in loader_js
    assert "manualReviewChecklist" in loader_js
    assert "decisionNoteRecommendation=" in loader_js
    assert "collect_controlled_command_evidence_before_decision_note" in loader_js
    assert "renderReviewDecisionHints" in loader_js
    assert "reviewDecisionHints" in loader_js
    assert "renderReviewDecisionNotes" in loader_js
    assert "renderReviewDecisionOutcome" in loader_js
    assert "reviewDecisionOutcome" in loader_js
    assert "READY_FOR_FINAL_HUMAN_APPROVE_REVIEW" in loader_js
    assert "NEEDS_REVISION_BEFORE_APPROVE" in loader_js
    assert "NEEDS_MORE_EVIDENCE_BEFORE_APPROVE" in loader_js
    assert "reviewDecisionNotes" in loader_js
    assert "gradingRecordsPath" in loader_js
    assert "/api/grading/records" in loader_js
    assert "GET /api/grading/records?taskId={id}" in loader_js
    assert "GradingRecordReviewIntegration" in loader_js
    assert "renderGradingRecordReviewIntegration" in loader_js
    assert "loadGradingRecordReview" in loader_js
    assert "applyGradingRecordReviewFromDetail" in loader_js
    assert "grading-record-review-status" in loader_js
    assert "grading-record-review-summary" in loader_js
    assert "grading-record-review-list" in loader_js
    assert "recordReviewState=LOAD_FAILED" in loader_js
    assert "agentApiRequired=false" in loader_js
    assert "commandExecutedFromPage=false" in loader_js
    assert "renderCheckEvidenceDetails" in loader_js
    assert "checkInputSummary" in loader_js
    assert "checkStatus" in loader_js
    assert "manual-review-action-list" in loader_js
    assert "manual-review-action-summary" in html
    assert "manualChecklistStatus=STATIC_HTML_FALLBACK" in html
    assert "expectedReviewerAction=confirm_stdout_contains_expected_token" in html
    assert "expectedReviewerAction=confirm_pytest_passed_in_controlled_container" in html
    assert "expectedReviewerAction=verify_notebook_cell_targets_and_expected_output_tokens" in html
    assert "expectedReviewerAction=confirm_assessment_plan_alignment_before_publish_review" in html
    assert "fallbackSource=GET /api/grading/report?file={file}&amp;taskId={id}.mergedGradingEvidenceCheckItems[].recommendedAction" in html
    assert "fetch(detailPath(taskId)" in loader_js
    assert "method: \"POST\"" not in loader_js
    assert "autoApproveAllowed=false" in loader_js
    assert "realPublishAllowed=false" in loader_js
    assert "source=GET /api/grading/report?file={file}&amp;taskId={id}.mergedGradingEvidenceCheckItems" in html
    assert "dynamicSource=GET /api/grading/report?file={file}&amp;taskId={id}.mergedGradingEvidence" in html
    assert "fallbackDynamicSource=GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence" in html
    assert "GET /api/grading/report?file={file}&amp;taskId={id}.mergedGradingEvidenceCheckItems[].recommendedAction" in html
    assert "checkEvidenceReviewItemTotal=4" in html
    assert "manualCheckReviewTotal=0" in html
    assert "mergeExecutedOnlyExistingReports=true" in html
    assert "evidenceSourceKind=controlledDocker" in html
    assert "evidenceSourceKind=notebookStatic" in html
    assert "reportMode=CONTROLLED_DOCKER_SANDBOX_POC" in html
    assert "reportMode=STATIC_NOTEBOOK_JSON_PARSE" in html
    assert "recommendedAction=verify_controlled_docker_output_and_score" in html
    assert "recommendedAction=review_static_notebook_evidence_matches_expected_tokens" in html
    assert "check_q1" in html
    assert "check_q2" in html
    assert "check_q3" in html
    assert "check_q4" in html
    assert "examples/output/mimo-real-demo-controlled-plan.json" in html
    assert "examples/output/mimo-real-demo-controlled-sandbox-report.json" in html
    assert "examples/output/mimo-real-demo-notebook-static-report.json" in html
    assert "examples/output/grading-sandbox-image-verify.json" in html
    assert "ai-grading-python:0.1" in html
    assert "stdout_contains=1" in html
    assert "pytest=1" in html
    assert "earnedScore=40/40" in html
    assert "realDemoPrototype.readonlyEvidenceDemo.reportDetail" in html
    assert "READONLY_REAL_SANDBOX_POC" in html
    assert "checkSummary.executed" in html
    assert "readonlyEvidence.status" in html
    assert "readonlyEvidenceCollectedTotal=2" in html
    assert "checkPlans[].readonlyEvidence.status=COLLECTED" in html
    assert "sandboxExecutionRequest.mode=REAL_SANDBOX_REQUIRED" in html
    assert "/real-demo -&gt; /grading/:id/report" in html
    assert "sourceGradingModified=false" in html
    assert "assessmentPlanSummary" in html
    assert "assessmentPlanSummary.source" in html
    assert "grading.spec.assessmentPlan" in html
    assert "assessmentPlanAlignedWithChecks" in html
    assert "assessmentPlanSourceField" in html
    assert "assessmentPlanAlignedWithCheck=true" in html
    assert "spec.assessmentPlan[checkId=check_result_file]" in html
    assert "assessmentPlanExecutionPlan" in html
    assert "assessmentPlanMockEvidence" in html
    assert "sandboxPolicy.executorBoundary" in html
    assert "SandboxExecutor" in html
    assert "EXPLAINABLE_MOCK_PLAN" in html
    assert "MOCK_EVIDENCE_NOT_COLLECTED" in html
    assert "inputSummary" in html
    assert "mockEvidence" in html
    assert "requiredLimits" in html
    assert "hostExecutionAllowed=false" in html
    assert "runRealPytestEnabled" in html
    assert "MOCK_GRADING_RUN" in html
    assert "file_exists" in html
    assert "stdout_contains" in html
    assert "pytest" in html
    assert "命令 / Pytest：本页不运行" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "commandExecuted=false" in html
    assert "checkSummary.executed=0" in html
    assert "disabled" in html
    manifest = load_json("frontend/ui.manifest.json")
    prototypes = {prototype["route"]: prototype for prototype in manifest["staticPrototypes"]}
    pages = {page["route"]: page for page in manifest["pages"]}
    assert prototypes["/grading/:id/report"]["mode"] == "LOCAL_CORE_MVP"
    assert prototypes["/grading/:id/report"]["safety"]["localCoreGradingReportReadOnly"] is True
    assert prototypes["/grading/:id/report"]["safety"]["frontendDirectGradingExecution"] is False
    assert pages["/grading/:id/report"]["safety"]["localCoreGradingReportReadOnly"] is True
    assert pages["/grading/:id/report"]["safety"]["frontendDirectGradingExecution"] is False
    assert "local grading evidence reports (readonly)" in prototypes["/grading/:id/report"]["dataSources"]
    assert "local grading evidence reports (readonly)" in pages["/grading/:id/report"]["dataSources"]
    assert "ReviewerReportWorkspace" in prototypes["/grading/:id/report"]["dataSources"]
    assert "ReviewerSafetySummary" in prototypes["/grading/:id/report"]["dataSources"]
    assert "ReviewerReportWorkspace.noHorizontalOverflow" in prototypes["/grading/:id/report"]["dataSources"]
    assert "query: coreDbPath" in prototypes["/grading/:id/report"]["dataSources"]
    assert "query: gradingDbPath" in prototypes["/grading/:id/report"]["dataSources"]
    assert "query: agentReport" in prototypes["/grading/:id/report"]["dataSources"]
    assert (
        "review-center.html?taskId={taskId}&decision={decision}&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert "GET /api/grading/report?file={file}.ReviewerReportWorkspace" in prototypes["/grading/:id/report"]["dataSources"]
    assert (
        "GET /api/grading/report?file={file}.report.reviewerSafetySummary"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert (
        "GET /api/grading/evidence-readiness?report={file}.ReviewerReportWorkspace"
        in prototypes["/grading/:id/report"]["dataSources"]
    )
    assert "GET /api/grading/records?taskId={id}.ReviewerReportWorkspace" in prototypes["/grading/:id/report"]["dataSources"]
    assert "GET /api/grading/records?taskId={id}.latest.reportPathFallback" in prototypes["/grading/:id/report"]["dataSources"]
    assert "ReviewerReportWorkspace" in pages["/grading/:id/report"]["components"]
    assert "ReviewerSafetySummary" in pages["/grading/:id/report"]["components"]
    assert "ReviewerReportWorkspace.noHorizontalOverflow" in pages["/grading/:id/report"]["dataSources"]
    assert "query: coreDbPath" in pages["/grading/:id/report"]["dataSources"]
    assert "query: gradingDbPath" in pages["/grading/:id/report"]["dataSources"]
    assert "query: agentReport" in pages["/grading/:id/report"]["dataSources"]
    assert (
        "review-center.html?taskId={taskId}&decision={decision}&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in pages["/grading/:id/report"]["dataSources"]
    )
    assert "GET /api/grading/report?file={file}.ReviewerReportWorkspace" in pages["/grading/:id/report"]["dataSources"]
    assert (
        "GET /api/grading/report?file={file}.report.reviewerSafetySummary"
        in pages["/grading/:id/report"]["dataSources"]
    )
    assert "GET /api/grading/records?taskId={id}.ReviewerReportWorkspace" in pages["/grading/:id/report"]["dataSources"]
    assert "GET /api/grading/records?taskId={id}.latest.reportPathFallback" in pages["/grading/:id/report"]["dataSources"]
    assert "ReviewerReportWorkspace" in read_text("frontend/README.md")
    assert "ReviewerSafetySummary" in read_text("frontend/README.md")
    assert "ReviewerReportWorkspace" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")
    assert "ReviewerSafetySummary" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")


def test_grading_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/grading.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实沙箱：禁用" in html
    assert "选手代码执行：禁用" in html
    assert "未知 Shell 执行：禁用" in html
    assert "真实重评：禁用" in html
    assert "真实发布：禁用" in html
    assert "GET /api/grading" in html
    assert "POST /api/grading/run" in html
    assert "GET /api/grading/report" in html
    assert "POST /api/phase2/workflows/grading-generation/run" in html
    assert "phase2_grading_generation" in html
    assert "python lab_cli.py phase2 grading-generate run" in html
    assert "gradingRefCoverage.matched" in html
    assert "scoreCoverage.matched" in html
    assert "assessmentPlanAlignedWithChecks" in html
    assert "GET /api/audit-events" in html
    assert "/grading/:id/report" in html
    assert "GradingReportPanel" in html
    assert "reportDetail" in html
    assert "reportDetail.checkPlans" in html
    assert "containerSandboxPlan：只读" in html
    assert "containerSandboxPlan.mode" in html
    assert "CONTAINER_PLAN_ONLY" in html
    assert "containerSandboxPlan.containerPlan.image" in html
    assert "python:3.11-slim" in html
    assert "containerSandboxPlan.containerPlan.mounts[0].mode" in html
    assert "read_only" in html
    assert "containerSandboxPlan.resultPlaceholder.status" in html
    assert "NOT_EXECUTED" in html
    assert "sandboxPolicy.executorBoundary" in html
    assert "SandboxExecutor" in html
    assert "EXPLAINABLE_MOCK_PLAN" in html
    assert "MOCK_EVIDENCE_NOT_COLLECTED" in html
    assert "requiredLimits" in html
    assert "hostExecutionAllowed" in html
    assert "runRealPytestEnabled" in html
    assert "WAITING_REVIEW" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "unknownShellExecuted=false" in html
    assert "realRegradeEnabled=false" in html
    assert "realPublish=false" in html
    assert "disabled" in html


def test_grading_review_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/grading-review.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型：禁用" in html
    assert "真实沙箱：禁用" in html
    assert "选手代码执行：禁用" in html
    assert "未知 Shell 执行：禁用" in html
    assert "真实重评：禁用" in html
    assert "真实发布：禁用" in html
    assert "批量状态变更：禁用" in html
    assert "GET /api/review-tasks/{id}" in html
    assert "POST /api/ai-tasks/{id}/approve" in html
    assert "POST /api/ai-tasks/{id}/reject" in html
    assert "GET /api/audit-events" in html
    assert "Grading DSL" in html
    assert "GradingReportPanel" in html
    assert "评分计划审核" in html
    assert "AssessmentPlanManualReviewChecklist" in html
    assert "ManualReviewAction" in html
    assert "AgentImportPreviewAction" in html
    assert "reviewCenterPrototype.nextManualReviewAction" in html
    assert "task_grading_demo" in html
    assert "/grading/:id/review?taskId=task_grading_demo" in html
    assert "review_assessment_plan_before_approval" in html
    assert "verify_assessment_plan_aligned_with_checks" in html
    assert "confirm_mock_evidence_not_collected" in html
    assert "confirm_real_sandbox_evidence_required_before_real_execution" in html
    assert "verify_required_limits_present" in html
    assert "confirm_no_execution_or_publish" in html
    assert "assessmentPlanAlignedWithChecks=true" in html
    assert "mockEvidence.status=MOCK_EVIDENCE_NOT_COLLECTED" in html
    assert "realSandboxEvidenceRequired=true" in html
    assert "requiredLimits=timeout/cpu/memory/network/filesystem/process" in html
    assert "manualDecisionRequired: true" in html
    assert "approveAllowedAfterChecklist: true" in html
    assert "qualitySignals：只读" in html
    assert "qualitySignals.coverage.gradingRefCoverage.status" in html
    assert "qualitySignals.coverage.gradingRefCoverage.matched=true" in html
    assert "qualitySignals.coverage.scoreCoverage.status=MATCHED" in html
    assert "qualitySignals.coverage.explainability.assessmentPlanAlignedWithChecks=true" in html
    assert "assessmentPlanHasReportDetailFields" in html
    assert "评分计划可解释性只辅助人工审核" in html
    assert "reviewDetail.assessmentPlan" in html
    assert "spec.assessmentPlan" in html
    assert "assessmentPlanAlignedWithChecks" in html
    assert "executionPlan.requiredLimits.network" in html
    assert "riskLevel" in html
    assert "reportDetail" in html
    assert "reportDetail.checkPlans" in html
    assert "containerSandboxPlan" in html
    assert "CONTAINER_PLAN_ONLY" in html
    assert "containerSandboxPlan.containerPlan.image" in html
    assert "python:3.11-slim" in html
    assert "containerSandboxPlan.containerPlan.mounts[0].mode" in html
    assert "read_only" in html
    assert "containerSandboxPlan.resultPlaceholder.status" in html
    assert "NOT_EXECUTED" in html
    assert "sandboxPolicy.executorBoundary" in html
    assert "SandboxExecutor" in html
    assert "EXPLAINABLE_MOCK_PLAN" in html
    assert "MOCK_EVIDENCE_NOT_COLLECTED" in html
    assert "inputSummary" in html
    assert "mockEvidence" in html
    assert "requiredLimits" in html
    assert "hostExecutionAllowed" in html
    assert "AiTaskTimeline" in html
    assert "WAITING_REVIEW" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "unknownShellExecuted=false" in html
    assert "realRegradeEnabled=false" in html
    assert "realSandboxRunEnabled=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublishAllowed=false" in html
    assert "rejectRequiresReason=true" in html
    assert "auditTrailRequired=true" in html
    assert "disabled" in html


def test_ai_tasks_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/ai-tasks.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型：禁用" in html
    assert "自动发布：禁用" in html
    assert "批量状态变更：禁用" in html
    assert "密钥展示：禁用" in html
    assert "GET /api/ai-tasks" in html
    assert "GET /api/review-task-summary" in html
    assert "GET /api/review-tasks/{id}" in html
    assert "TaskExecutionWorkspace" in html
    assert ".section-head > *" in html
    assert "overflow-wrap: anywhere" in html
    assert "white-space: normal" in html
    assert "task-workspace-summary" in html
    assert "task-workspace-selected" in html
    assert "task-workspace-review-state" in html
    assert "task-workspace-artifact" in html
    assert "task-workspace-safety" in html
    assert "task-workspace-next-action" in html
    assert "task-workspace-review-link" in html
    assert "task-workspace-grading-report-link" in html
    assert "task-workspace-import-preview-link" in html
    assert "task-workspace-boundary" in html
    assert "method=GET only" in html
    assert "no approve/reject" in html
    assert "no real platform API" in html
    assert "grading-report.html?taskId=task_grading_demo" in html
    assert "agent-entities.html?sourceTaskId=task_grading_demo" in html
    assert "ReviewPrioritySignal" in html
    assert "reviewCenterPrototype.reviewPriorityQueue" in html
    assert "NextManualReviewAction" in html
    assert "reviewCenterPrototype.nextManualReviewAction" in html
    assert "defaultSort=priorityRankAsc" in html
    assert "topPriorityTaskId=task_grading_demo" in html
    assert "entryRoute=/review-center?taskId=task_grading_demo" in html
    assert "taskId=task_grading_demo" in html
    assert "primaryReviewFocus=review_assessment_plan_before_approval" in html
    assert "open_task_grading_demo_review_detail" in html
    assert "verify_assessment_plan_aligned_with_checks" in html
    assert "confirm_real_sandbox_evidence_required_before_real_execution" in html
    assert "realPublishAllowed=false" in html
    assert "HIGH_RISK_MOCK_EVIDENCE_REQUIRED" in html
    assert "CANDIDATE_SAFE_EXAM_PREVIEW" in html
    assert "priority=URGENT" in html
    assert "priority=HIGH" in html
    assert "priority=NORMAL" in html
    assert "urgentTotal=1" in html
    assert "highTotal=1" in html
    assert "normalTotal=1" in html
    assert "batchStateChangeAllowed" in html
    assert "ProviderQualityTaskSignal" in html
    assert "source=reviewDetail.reviewPage.providerSummary.qualitySummary" in html
    assert "callSource=reviewDetail.reviewPage.providerSummary.calls[].qualitySummary" in html
    assert "visibleForTaskTypes=LAB_GENERATION" in html
    assert "readyForReview=true" in html
    assert "realLlmCalled=true" in html
    assert "openai_responses_sdk_adapter" in html
    assert "normalizationPatchCount=1" in html
    assert "normalizationPatches=set.metadata.category" in html
    assert "schemaRepairApplied=false" in html
    assert "apiSurface=chat.completions" in html
    assert "responseId=resp_demo_lab_quality" in html
    assert "totalTokens=1234" in html
    assert "autoPublishAllowed=false" in html
    assert "QualitySignalTaskSignal" in html
    assert "examReviewPrototype.qualitySignals + gradingReviewPrototype.qualitySignals" in html
    assert "candidateSafeExamPreview.answersRemoved=true" in html
    assert "questionGradingRefCoverage.status=MATCHED" in html
    assert "gradingRefCoverage.status=MATCHED" in html
    assert "scoreCoverage.status=MATCHED" in html
    assert "explainability.status=EXPLAINABLE" in html
    assert "matchedCoverageTotal=4" in html
    assert "explainablePlanTotal=2" in html
    assert "candidateSafeExamPreviewTotal=1" in html
    assert "AssessmentPlanTaskSignal" in html
    assert "reviewDetail.assessmentPlan" in html
    assert "gradingReviewPrototype.assessmentPlanSummary" in html
    assert "GRADING_GENERATION" in html
    assert "planTotal=1" in html
    assert "alignedWithChecks=true" in html
    assert "riskLevel=high" in html
    assert "MOCK_EVIDENCE_NOT_COLLECTED" in html
    assert "realSandboxEvidenceRequired=true" in html
    assert "sandboxRequiredBeforeRealExecution=true" in html
    assert "MOCK_PLAN_ONLY" in html
    assert "requiredLimits=timeout/cpu/memory/network/filesystem/process" in html
    assert "WAITING_REVIEW" in html
    assert "disabled" in html


def test_dashboard_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/dashboard.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型：禁用" in html
    assert "真实云资源：禁用" in html
    assert "真实沙箱：禁用" in html
    assert "自动发布：禁用" in html
    assert "GET /api/health" in html
    assert "GET /api/review-task-summary" in html
    assert "AssessmentPlanDashboardSignal" in html
    assert "gradingReviewPrototype.assessmentPlanSummary" in html
    assert "reviewDetail.assessmentPlan" in html
    assert "GRADING_GENERATION" in html
    assert "planTotal=1" in html
    assert "alignedWithChecks=true" in html
    assert "riskLevel=high" in html
    assert "MOCK_EVIDENCE_NOT_COLLECTED" in html
    assert "realSandboxEvidenceRequired=true" in html
    assert "requiredLimits=timeout/cpu/memory/network/filesystem/process" in html
    assert "realLlmCalled=false" in html
    assert "sandboxExecuted=false" in html
    assert "disabled" in html


def test_console_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/console.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型：禁用" in html
    assert "真实云资源：禁用" in html
    assert "真实智能体：禁用" in html
    assert "真实沙箱：禁用" in html
    assert "自动发布：禁用" in html
    assert "真实发布：禁用" in html
    assert "密钥展示：禁用" in html
    assert "标准答案选手端：隐藏" in html
    assert "ConsoleNavPanel" in html
    assert "GET /api/health" in html
    assert "GET /api/review-task-summary" in html
    assert "GET /api/workflow-runs" in html
    assert "GET /api/artifacts" in html
    assert "GET /api/providers" in html
    assert "/console" in html
    assert "/dashboard" in html
    assert "/delivery" in html
    assert "/ai-tasks" in html
    assert "/review-center" in html
    assert "/workflows" in html
    assert "start .\\frontend\\workflows.html" in html
    assert "GET /api/workflow-registry" in html
    assert "/labs/generate" in html
    assert "/exams/generate" in html
    assert "/grading/:id/report" in html
    assert "/ppt/:id/review" in html
    assert "/settings/providers" in html
    assert "python lab_cli.py phase1 check" in html
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in html
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in html
    assert "python -m pytest tests/test_frontend_manifest.py" in html
    assert "/operations/runbook" in html
    assert "start .\\frontend\\operations-runbook.html" in html
    assert "/operations/acceptance" in html
    assert "start .\\frontend\\operations-acceptance.html" in html
    assert "/operations/demo-map" in html
    assert "start .\\frontend\\operations-demo-map.html" in html
    assert "/operations/presenter" in html
    assert "start .\\frontend\\operations-presenter.html" in html
    assert "/operations/demo-script" in html
    assert "start .\\frontend\\operations-demo-script.html" in html
    assert "realAgentStarted=false" in html
    assert "realLlmCalled=false" in html
    assert "realCloudResourceCreated=false" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "unknownShellExecuted=false" in html
    assert "autoPublishAllowed=false" in html
    assert "standardAnswerRevealToCandidate=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "remoteUploadAllowed=false" in html
    assert "disabled" in html


def test_workflow_registry_static_prototype_has_phase2_safety_text():
    html = (ROOT / "frontend/workflows.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "/workflows" in html
    assert "frontend/mock-data.json.workflowRegistryPrototype" in html
    assert "ai-workflows/phase2-workflow-registry.contract.json" in html
    assert "mcp-server/tools.manifest.json" in html
    assert "ConsoleNavPanel" in html
    assert "WorkflowLogViewer" in html
    assert "AuditTrailPanel" in html
    assert "GET /api/workflow-registry" in html
    assert "GET /api/workflow-registry/{workflowId}" in html
    assert "GET /api/mcp-tool-call-records" in html
    assert "phase2_content_generation" in html
    assert "phase2_exam_conversion" in html
    assert "phase2_ppt_generation" in html
    assert "phase2_grading_generation" in html
    assert "ai-workflows/phase2-grading-generation.contract.json" in html
    assert "python lab_cli.py phase2 grading-generate run" in html
    assert "POST /api/phase2/workflows/grading-generation/run" in html
    assert "grading_generation" in html
    assert "assessmentPlan" in html
    assert "list_workflows" in html
    assert "get_workflow" in html
    assert "python lab_cli.py mcp call --tool list_workflows" in html
    assert "python lab_cli.py mcp call --tool get_workflow" in html
    assert "WAITING_REVIEW" in html
    assert "workflowExecuted=false" in html
    assert "taskCreated=false" in html
    assert "artifactCreated=false" in html
    assert "runWorkflowEnabled=false" in html
    assert "startRealMcpServerEnabled=false" in html
    assert "startRealAgentEnabled=false" in html
    assert "callRealLlmEnabled=false" in html
    assert "createAiTaskEnabled=false" in html
    assert "createArtifactEnabled=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "answerVisibleToCandidate=false" in html
    assert "disabled" in html


def test_real_demo_static_prototype_has_readonly_evidence_and_safety_text():
    mock_data = load_json("frontend/mock-data.json")
    real_demo = mock_data["realDemoPrototype"]
    html = (ROOT / "frontend/real-demo.html").read_text(encoding="utf-8")

    assert real_demo["mode"] == "REAL_LLM_DEMO_REPLAY_STATIC"
    core_path = real_demo["coreBusinessDemoPath"]
    assert core_path["component"] == "CoreBusinessDemoPath"
    assert core_path["source"] == "examples/output/real-llm-demo-bundle.json"
    assert core_path["route"] == "/real-demo -> /review-center -> /ppt/:id/review -> /grading/:id/report"
    assert core_path["stepTotal"] == 6
    assert len(core_path["steps"]) == 6
    assert [step["id"] for step in core_path["steps"]] == [
        "real_lab_dsl",
        "real_exam_dsl_candidate_safe",
        "real_grading_dsl_preserved",
        "readonly_evidence_score",
        "pptx_artifact_review",
        "ppt_page_review_update",
    ]
    assert core_path["manualReviewRequired"] is True
    assert core_path["reviewCenterLinked"] is True
    assert core_path["pptPageReviewActionVisible"] is True
    assert core_path["autoApproveAllowed"] is False
    assert core_path["autoPublishAllowed"] is False
    assert core_path["realPublish"] is False
    assert core_path["steps"][1]["acceptanceSignal"] == "candidatePreview.answersRemoved=true"
    assert core_path["steps"][3]["acceptanceSignal"] == "readonlyEvidenceDemo.executed=2 earnedScore=70"
    assert core_path["steps"][5]["acceptanceSignal"] == "PPT_PAGE_REVIEW_UPDATE writesOperationAudit=true"
    assert core_path["acceptanceSignals"]["dslValidatedTotal"] == 4
    assert core_path["acceptanceSignals"]["waitingReviewDslTotal"] == 4
    assert core_path["acceptanceSignals"]["pptPageReviewActionVisible"] is True
    assert core_path["acceptanceSignals"]["reviewRequiredBeforePublish"] is True
    assert core_path["safety"]["newLlmRequestSent"] is False
    assert core_path["safety"]["sourceGradingModified"] is False
    assert core_path["safety"]["contestantCodeExecuted"] is False
    assert core_path["safety"]["autoApproveAllowed"] is False
    assert core_path["safety"]["autoPublishAllowed"] is False
    assert core_path["safety"]["realPublish"] is False
    assert real_demo["generatedDsl"]["lab"]["status"] == "WAITING_REVIEW"
    assert real_demo["generatedDsl"]["exam"]["answerVisibleToCandidate"] is False
    assert real_demo["generatedDsl"]["grading"]["sourcePreserved"] is True
    assert real_demo["generatedDsl"]["ppt"]["artifactGenerated"] is True
    assert real_demo["pptArtifact"]["kind"] == "PPTX_FILE"
    assert real_demo["pptArtifact"]["status"] == "WAITING_REVIEW"
    assert real_demo["pptArtifact"]["slideCount"] == 5
    assert real_demo["pptArtifact"]["autoPublishAllowed"] is False
    real_dsl_preview = real_demo["realDslReviewPreview"]
    assert real_dsl_preview["component"] == "RealDslReviewPreview"
    assert real_dsl_preview["mode"] == "STATIC_REAL_LLM_DSL_REVIEW_PREVIEW"
    assert real_dsl_preview["summary"]["labStepTotal"] == len(real_dsl_preview["labReview"]["steps"])
    assert real_dsl_preview["summary"]["examQuestionTotal"] == len(real_dsl_preview["examReview"]["candidateQuestions"])
    assert real_dsl_preview["summary"]["gradingPlanTotal"] == len(real_dsl_preview["gradingReview"]["assessmentPlan"])
    assert real_dsl_preview["summary"]["gradingCheckTotal"] == len(real_dsl_preview["gradingReview"]["checks"])
    assert real_dsl_preview["summary"]["pptSlideTotal"] == len(real_dsl_preview["pptReview"]["slides"])
    assert real_dsl_preview["summary"]["qualityIssueTotal"] == len(real_dsl_preview["reviewIssues"])
    assert real_dsl_preview["summary"]["revisionSuggestionTotal"] == len(real_dsl_preview["revisionSuggestions"])
    assert real_dsl_preview["qualitySignals"]["summary"]["status"] == "NEEDS_REVIEW"
    assert real_dsl_preview["qualitySignals"]["summary"]["manualReviewRequired"] is True
    assert real_dsl_preview["qualitySignals"]["summary"]["autoApproveAllowed"] is False
    assert real_dsl_preview["qualitySignals"]["summary"]["realPublishAllowed"] is False
    assert real_dsl_preview["labReview"]["title"] == "AI 工具应用入门实验"
    assert [step["id"] for step in real_dsl_preview["labReview"]["steps"]] == ["step-1", "step-2", "step-3", "step-4"]
    assert [question["id"] for question in real_dsl_preview["examReview"]["candidateQuestions"]] == ["q1"]
    assert all(
        question["answerVisibleToCandidate"] is False
        and question["gradingRefVisibleToCandidate"] is False
        for question in real_dsl_preview["examReview"]["candidateQuestions"]
    )
    assert real_dsl_preview["examReview"]["candidateSafety"]["answersRemoved"] is True
    assert real_dsl_preview["examReview"]["candidateSafety"]["answerVisibleToCandidate"] is False
    assert real_dsl_preview["examReview"]["candidateSafety"]["gradingRefVisibleToCandidate"] is False
    assert "questions[].gradingRef" in real_dsl_preview["examReview"]["candidateSafety"]["removedFields"]
    assert all(ref["teacherOnly"] is True and ref["candidateVisible"] is False for ref in real_dsl_preview["examReview"]["teacherQuestionRefs"])
    assert [plan["checkId"] for plan in real_dsl_preview["gradingReview"]["assessmentPlan"]] == ["check_waiting_review"]
    assert real_dsl_preview["gradingReview"]["precheckStatus"] == "READY_FOR_MANUAL_SANDBOX_REVIEW"
    assert real_dsl_preview["gradingReview"]["commandExecutionAllowedFromPage"] is False
    assert real_dsl_preview["pptReview"]["slideTotal"] == 4
    assert [slide["id"] for slide in real_dsl_preview["pptReview"]["slides"]] == [
        "slide_title",
        "slide_goals",
        "slide_steps",
        "slide_summary",
    ]
    assert any(issue["id"] == "lab_objective_depth" for issue in real_dsl_preview["reviewIssues"])
    assert any(issue["id"] == "grading_sandbox_execution_required" for issue in real_dsl_preview["reviewIssues"])
    assert all(suggestion["keepsWaitingReview"] is True for suggestion in real_dsl_preview["revisionSuggestions"])
    assert real_dsl_preview["safety"]["gradingRefVisibleToCandidate"] is False
    assert real_dsl_preview["safety"]["teacherOnlyGradingRefVisibleInReview"] is True
    assert real_dsl_preview["safety"]["commandExecutedFromPage"] is False
    assert real_dsl_preview["safety"]["realPublishAllowed"] is False
    diff_preview = real_demo["realDslRevisionDiffPreview"]
    assert diff_preview["component"] == "RealDslRevisionDiffPreview"
    assert diff_preview["mode"] == "LOCAL_REAL_DSL_REVISION_DIFF_PREVIEW"
    assert diff_preview["sourceBatchReportPath"] == "examples/output/real-llm-demo-revision-batch-report.json"
    assert diff_preview["summary"]["draftTotal"] == 3
    assert diff_preview["summary"]["diffTotal"] == 12
    assert diff_preview["summary"]["allDraftsWaitingReview"] is True
    assert {draft["kind"] for draft in diff_preview["draftDiffs"]} == {"lab", "grading", "ppt"}
    assert any(
        field["field"] == "$.spec.assessmentPlan[0].inputSummary"
        for draft in diff_preview["draftDiffs"]
        for field in draft["fieldDiffs"]
    )
    assert diff_preview["safety"]["newLlmRequestSent"] is False
    assert diff_preview["safety"]["secretsRead"] is False
    assert diff_preview["safety"]["networkAccess"] is False
    assert diff_preview["safety"]["realPublishAllowed"] is False
    revision_decision = real_demo["realDslRevisionDecision"]
    assert revision_decision["component"] == "RealDslRevisionDecision"
    assert revision_decision["mode"] == "LOCAL_REAL_DSL_REVISION_DECISION"
    assert revision_decision["suggestionId"] == "revise_lab_objective_depth"
    assert revision_decision["decision"] == "approve"
    assert revision_decision["decisionStatus"] == "REVISION_APPROVED_FOR_MANUAL_MERGE"
    assert revision_decision["manualMergeRequired"] is True
    assert revision_decision["sourceDslModified"] is False
    assert revision_decision["revisedDslModified"] is False
    assert revision_decision["safety"]["newLlmRequestSent"] is False
    assert revision_decision["safety"]["realPublishAllowed"] is False
    revision_promotion = real_demo["realDslRevisionPromotion"]
    assert revision_promotion["component"] == "RealDslRevisionPromotion"
    assert revision_promotion["mode"] == "LOCAL_REAL_DSL_REVISION_PROMOTION"
    assert revision_promotion["suggestionId"] == "revise_lab_objective_depth"
    assert revision_promotion["promotedStatus"] == "WAITING_REVIEW"
    assert revision_promotion["schemaValidated"] is True
    assert revision_promotion["manualReviewRequired"] is True
    assert revision_promotion["safety"]["sourceDslModified"] is False
    assert revision_promotion["safety"]["revisedDslModified"] is False
    assert revision_promotion["safety"]["promotedCandidateWritten"] is True
    assert revision_promotion["safety"]["newLlmRequestSent"] is False
    assert revision_promotion["safety"]["realPublishAllowed"] is False
    promotion_queue_item = real_demo["realDslRevisionPromotionReviewQueueItem"]
    assert promotion_queue_item["component"] == "RealDslRevisionPromotionReviewQueueItem"
    assert promotion_queue_item["mode"] == "LOCAL_REAL_DSL_REVISION_PROMOTION_REVIEW_QUEUE"
    assert promotion_queue_item["taskType"] == "LAB_GENERATION_REVISION"
    assert promotion_queue_item["taskStatus"] == "WAITING_REVIEW"
    assert promotion_queue_item["artifactKind"] == "LAB_DSL"
    assert promotion_queue_item["artifactStatus"] == "WAITING_REVIEW"
    assert promotion_queue_item["schemaValidated"] is True
    assert promotion_queue_item["reviewDetailAvailable"] is True
    assert promotion_queue_item["reviewDetailSource"] == "GET /api/review-tasks/{id}"
    assert promotion_queue_item["safety"]["newLlmRequestSent"] is False
    assert promotion_queue_item["safety"]["realPublishAllowed"] is False
    review_queue_signal = mock_data["reviewCenterPrototype"]["realDslRevisionPromotionReviewQueueSignal"]
    assert review_queue_signal["component"] == "RealDslRevisionPromotionReviewQueueItem"
    assert review_queue_signal["api"] == "POST /api/review/real-dsl-revision-enqueue"
    assert review_queue_signal["mcpTool"] == "enqueue_real_dsl_revision_candidate_review"
    assert review_queue_signal["taskStatus"] == "WAITING_REVIEW"
    assert review_queue_signal["artifactKind"] == "LAB_DSL"
    assert review_queue_signal["autoPublishAllowed"] is False
    assert review_queue_signal["realPublishAllowed"] is False
    promotion_disposition = real_demo["realDslRevisionPromotionReviewDisposition"]
    assert promotion_disposition["component"] == "RealDslRevisionPromotionReviewDisposition"
    assert promotion_disposition["state"] == "APPROVED_FOR_MOCK_PUBLISH_ONLY"
    assert promotion_disposition["reviewCompleted"] is True
    assert promotion_disposition["mockPublishAvailable"] is True
    assert promotion_disposition["autoPublishAllowed"] is False
    assert promotion_disposition["realPublishAllowed"] is False
    lab_import_preview = real_demo["labTemplateImportPreview"]
    assert lab_import_preview["component"] == "LabTemplateImportPreview"
    assert lab_import_preview["mode"] == "LOCAL_PLATFORM_IMPORT_PREVIEW"
    assert lab_import_preview["sourceTaskStatus"] == "APPROVED"
    assert lab_import_preview["sourceArtifactKind"] == "LAB_DSL"
    assert lab_import_preview["schemaValidated"] is True
    assert lab_import_preview["agentEntity"] == "lab_template"
    assert lab_import_preview["labTemplateDraft"]["status"] == "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW"
    assert lab_import_preview["importPlan"]["databaseWritePlanned"] is False
    assert lab_import_preview["safety"]["databaseWritten"] is False
    assert lab_import_preview["safety"]["realAgentImport"] is False
    assert lab_import_preview["safety"]["realPublishAllowed"] is False
    lab_import_signal = mock_data["reviewCenterPrototype"]["labTemplateImportPreviewSignal"]
    assert lab_import_signal["component"] == "LabTemplateImportPreview"
    assert lab_import_signal["api"] == "POST /api/labs/import-preview"
    assert lab_import_signal["mcpTool"] == "create_lab_template_import_preview"
    assert lab_import_signal["sourceTaskStatus"] == "APPROVED"
    assert lab_import_signal["agentEntity"] == "lab_template"
    assert lab_import_signal["databaseWritten"] is False
    assert lab_import_signal["realAgentImport"] is False
    assert lab_import_signal["realPublishAllowed"] is False
    exam_import_signal = mock_data["reviewCenterPrototype"]["examQuestionImportPreviewSignal"]
    assert exam_import_signal["component"] == "ExamQuestionImportPreview"
    assert exam_import_signal["api"] == "POST /api/exams/import-preview"
    assert exam_import_signal["mcpTool"] == "create_exam_question_import_preview"
    assert exam_import_signal["sourceArtifactKind"] == "EXAM_DSL"
    assert exam_import_signal["agentEntity"] == "exam_question"
    assert exam_import_signal["candidateAnswerVisible"] is False
    assert exam_import_signal["realPublishAllowed"] is False
    grading_import_signal = mock_data["reviewCenterPrototype"]["gradingRuleImportPreviewSignal"]
    assert grading_import_signal["component"] == "GradingRuleImportPreview"
    assert grading_import_signal["api"] == "POST /api/grading/import-preview"
    assert grading_import_signal["mcpTool"] == "create_grading_rule_import_preview"
    assert grading_import_signal["sourceArtifactKind"] == "GRADING_DSL"
    assert grading_import_signal["agentEntity"] == "grading_rule"
    assert grading_import_signal["sandboxRequiredBeforeRealExecution"] is True
    assert grading_import_signal["realPublishAllowed"] is False
    platform_import_actions = mock_data["reviewCenterPrototype"]["platformImportPreviewActions"]
    assert platform_import_actions["component"] == "AgentImportPreviewActionPanel"
    assert platform_import_actions["source"] == "GET /api/review-tasks/{id}.reviewDetail.platformImportPreviewActions"
    assert platform_import_actions["reviewPageSource"] == (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.platformImportPreviewActions"
    )
    assert platform_import_actions["visible"] is True
    assert platform_import_actions["enabled"] is True
    assert platform_import_actions["total"] == 3
    assert platform_import_actions["enabledTotal"] == 3
    assert platform_import_actions["previewAlreadyCreatedTotal"] == 1
    assert platform_import_actions["contentQualityAvailable"] is True
    assert platform_import_actions["contentQualityAdvisoryOnly"] is True
    assert platform_import_actions["approvalStillRequired"] is True
    assert platform_import_actions["contentQualityReadyTotal"] == 3
    assert platform_import_actions["contentQualityBlockedTotal"] == 0
    assert platform_import_actions["contentQualityReadyForImportPreviewKinds"] == ["lab", "exam", "grading"]
    assert {item["component"] for item in platform_import_actions["items"]} == {
        "LabTemplateImportPreviewAction",
        "ExamQuestionImportPreviewAction",
        "GradingRuleImportPreviewAction",
    }
    assert {item["apiEndpoint"] for item in platform_import_actions["items"]} == {
        "POST /api/labs/import-preview",
        "POST /api/exams/import-preview",
        "POST /api/grading/import-preview",
    }
    assert all(item["enabled"] is True for item in platform_import_actions["items"])
    assert all(item["contentQualityReadyForImportPreview"] is True for item in platform_import_actions["items"])
    assert all(item["contentQualityAdvisoryOnly"] is True for item in platform_import_actions["items"])
    assert all(item["databaseWritten"] is False for item in platform_import_actions["items"])
    assert platform_import_actions["safety"]["realAgentImport"] is False
    assert platform_import_actions["safety"]["realPublishAllowed"] is False
    platform_import_summary = mock_data["reviewCenterPrototype"]["platformImportPreviewSummary"]
    assert platform_import_summary["component"] == "AgentImportPreviewSummary"
    assert platform_import_summary["source"] == "GET /api/review-tasks/{id}.reviewDetail.platformImportPreview"
    assert platform_import_summary["reviewPageSource"] == (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.platformImportPreview"
    )
    assert platform_import_summary["visible"] is True
    assert platform_import_summary["total"] == 3
    assert platform_import_summary["agentEntities"] == ["lab_template", "exam_question", "grading_rule"]
    assert platform_import_summary["sourceArtifactKinds"] == ["LAB_DSL", "EXAM_DSL", "GRADING_DSL"]
    assert {item["component"] for item in platform_import_summary["items"]} == {
        "LabTemplateImportPreview",
        "ExamQuestionImportPreview",
        "GradingRuleImportPreview",
    }
    assert platform_import_summary["databaseWritten"] is False
    assert platform_import_summary["realAgentImport"] is False
    assert platform_import_summary["realPublishAllowed"] is False
    assert platform_import_summary["safety"]["databaseWritten"] is False
    assert platform_import_summary["safety"]["realPublishAllowed"] is False
    platform_import_signoff = mock_data["reviewCenterPrototype"]["platformImportPreviewSignoffChecklist"]
    assert platform_import_signoff["component"] == "AgentImportPreviewSignoffChecklist"
    assert platform_import_signoff["source"] == "GET /api/review-tasks/{id}.reviewDetail.platformImportPreviewSignoff"
    assert platform_import_signoff["reviewPageSource"] == (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.platformImportPreviewSignoff"
    )
    assert platform_import_signoff["visible"] is True
    assert platform_import_signoff["readyForHumanSignoff"] is True
    assert platform_import_signoff["total"] == 3
    assert platform_import_signoff["missingPreviewTotal"] == 0
    assert {item["component"] for item in platform_import_signoff["items"]} == {
        "LabTemplateImportPreviewSignoff",
        "ExamQuestionImportPreviewSignoff",
        "GradingRuleImportPreviewSignoff",
    }
    signoff_checks = {
        check for item in platform_import_signoff["items"] for check in item["checks"]
    }
    assert "confirm_candidate_answer_hidden_and_grading_refs_teacher_only" in signoff_checks
    assert "confirm_sandbox_required_before_real_execution" in signoff_checks
    assert platform_import_signoff["databaseWritten"] is False
    assert platform_import_signoff["realAgentImport"] is False
    assert platform_import_signoff["realPublishAllowed"] is False
    agent_entity_mock_import = mock_data["reviewCenterPrototype"]["agentEntityMockImportSummary"]
    assert agent_entity_mock_import["component"] == "AgentEntityMockImportSummary"
    assert agent_entity_mock_import["source"] == "GET /api/review-tasks/{id}.reviewDetail.agentEntityMockImport"
    assert agent_entity_mock_import["reviewPageSource"] == (
        "GET /api/review-tasks/{id}.reviewDetail.reviewPage.agentEntityMockImport"
    )
    assert agent_entity_mock_import["visible"] is True
    assert agent_entity_mock_import["total"] == 3
    assert agent_entity_mock_import["entityTypes"] == ["lab_template", "exam_question", "grading_rule"]
    assert {item["entityType"] for item in agent_entity_mock_import["items"]} == {
        "lab_template",
        "exam_question",
        "grading_rule",
    }
    assert all(item["mockStoreWritten"] is True for item in agent_entity_mock_import["items"])
    assert all(item["databaseWritten"] is False for item in agent_entity_mock_import["items"])
    assert all(item["id"].startswith("entity_") for item in agent_entity_mock_import["items"])
    assert all(item["sourceTaskId"].startswith("real_demo_") for item in agent_entity_mock_import["items"])
    assert all(item["sourcePreviewArtifactId"].startswith("artifact_") for item in agent_entity_mock_import["items"])
    assert all(item["sourceDslPath"].startswith("examples/output/real-llm-") for item in agent_entity_mock_import["items"])
    assert all(item["listApi"].startswith("GET /api/platform-entities?sourceTaskId=") for item in agent_entity_mock_import["items"])
    assert all(item["detailApi"].startswith("GET /api/platform-entities/entity_") for item in agent_entity_mock_import["items"])
    assert all(item["detailRoute"].startswith("agent-entities.html?entityId=entity_") for item in agent_entity_mock_import["items"])
    assert all("sourceTaskId=real_demo_" in item["detailRoute"] for item in agent_entity_mock_import["items"])
    assert all("entityKind=" in item["detailRoute"] for item in agent_entity_mock_import["items"])

    agent_entity_readiness = mock_data["reviewCenterPrototype"]["agentEntityReadinessReport"]
    assert mock_data["reviewDetail"]["agentEntityReadinessReport"] == agent_entity_readiness
    assert mock_data["reviewDetail"]["reviewPage"]["agentEntityReadinessReport"] == agent_entity_readiness
    assert mock_data["reviewDetail"]["summary"]["agentEntitySignoffReadyTotal"] == 1
    assert mock_data["reviewDetail"]["summary"]["agentEntitySignoffRecordedTotal"] == 0
    assert agent_entity_readiness["component"] == "AgentEntityReadinessReport"
    assert agent_entity_readiness["source"] == "GET /api/platform-entities/readiness-report?sourceTaskId={id}"
    assert agent_entity_readiness["summary"]["requiredTotal"] == 3
    assert agent_entity_readiness["summary"]["allReadyForManualPlatformReview"] is True
    assert {item["agentEntity"] for item in agent_entity_readiness["items"]} == {
        "lab_template",
        "exam_question",
        "grading_rule",
    }
    assert all(item["readyForManualAgentReview"] is True for item in agent_entity_readiness["items"])
    assert agent_entity_readiness["summary"]["dryRunPreparedTotal"] == 1
    assert agent_entity_readiness["summary"]["requestSentTotal"] == 1
    assert agent_entity_readiness["summary"]["statusQueriedTotal"] == 1
    assert agent_entity_readiness["summary"]["resultRecordedTotal"] == 1
    assert agent_entity_readiness["summary"]["agentEntitySignoffReadyTotal"] == 1
    assert agent_entity_readiness["summary"]["agentEntitySignoffRecordedTotal"] == 0
    assert agent_entity_readiness["summary"]["postSignoffPrePublishReadyTotal"] == 0
    assert agent_entity_readiness["summary"]["allPlatformEntitiesReadyForSignoff"] is False
    assert agent_entity_readiness["summary"]["allPlatformEntitiesSignoffRecorded"] is False
    assert agent_entity_readiness["summary"]["allPostSignoffPrePublishReady"] is False
    lab_readiness = next(item for item in agent_entity_readiness["items"] if item["agentEntity"] == "lab_template")
    assert lab_readiness["importActivity"]["component"] == "AgentEntityImportActivitySummary"
    assert lab_readiness["importActivity"]["latestDryRun"]["artifactId"] == "artifact_lab_dry_run_demo"
    assert lab_readiness["importActivity"]["latestSend"]["statusCode"] == 202
    assert lab_readiness["importActivity"]["latestStatusQuery"]["agentStatus"] == "ACCEPTED_FOR_DRAFT"
    assert lab_readiness["importActivity"]["latestResult"]["agentDraftId"] == "draft_lab_template_demo"
    assert lab_readiness["importActivity"]["summary"]["secretValueReturned"] is False
    assert lab_readiness["importActivity"]["summary"]["realPublish"] is False
    assert lab_readiness["signoffState"] == "READY_FOR_PLATFORM_ENTITY_SIGNOFF"
    assert lab_readiness["readyForAgentEntitySignoff"] is True
    assert lab_readiness["signoffRecorded"] is False
    assert lab_readiness["postSignoffPrePublishChecklist"]["component"] == "AgentEntityPostSignoffPrePublishChecklist"
    assert lab_readiness["postSignoffPrePublishChecklist"]["status"] == "NEEDS_SIGNOFF_BEFORE_PRE_PUBLISH_REVIEW"
    assert lab_readiness["postSignoffPrePublishChecklist"]["nextRequiredAction"] == "final_human_publish_review_before_any_real_publish"
    assert (
        lab_readiness["postSignoffPrePublishChecklist"]["entitySpecificReviewFocus"]["primaryReviewFocus"]
        == "review_lab_objectives_environment_and_grading_ref_before_publish"
    )
    assert {
        item["agentEntity"]: item["postSignoffPrePublishChecklist"]["entitySpecificReviewFocus"][
            "primaryReviewFocus"
        ]
        for item in agent_entity_readiness["items"]
    } == {
        "lab_template": "review_lab_objectives_environment_and_grading_ref_before_publish",
        "exam_question": "review_candidate_safe_exam_preview_and_scoring_before_publish",
        "grading_rule": "review_grading_plan_sandbox_limits_and_evidence_before_publish",
    }
    assert lab_readiness["postSignoffPrePublishChecklist"]["safety"]["requiresFinalHumanReview"] is True
    assert lab_readiness["postSignoffPrePublishChecklist"]["safety"]["realPublish"] is False
    assert lab_readiness["signoffActionRoute"] is None
    assert {check["id"] for check in lab_readiness["manualSignoffChecklist"]} == {
        "confirm_local_preview_and_mock_import_ready",
        "confirm_platform_send_recorded",
        "confirm_platform_status_queried",
        "confirm_platform_result_recorded",
        "confirm_accepted_for_draft_only",
    }
    assert all(check["matched"] is True for check in lab_readiness["manualSignoffChecklist"])
    assert all("sourceTaskId=real_demo_" in item["detailRoute"] for item in agent_entity_readiness["items"])
    assert all("entityKind=" in item["detailRoute"] for item in agent_entity_readiness["items"])
    assert agent_entity_readiness["safety"]["databaseWritten"] is False
    assert agent_entity_readiness["safety"]["realAgentImport"] is False
    assert agent_entity_readiness["safety"]["realPublish"] is False
    assert agent_entity_readiness["safety"]["requiresFinalHumanReviewBeforePublish"] is True
    assert agent_entity_mock_import["summary"]["databaseWritten"] is False
    assert agent_entity_mock_import["summary"]["realAgentImport"] is False
    assert agent_entity_mock_import["safety"]["realPublish"] is False
    assert real_demo["candidatePreview"]["answersRemoved"] is True
    assert real_demo["readonlyEvidenceDemo"]["doesNotModifySourceGrading"] is True
    assert real_demo["readonlyEvidenceDemo"]["executionSummary"]["executed"] == 2
    assert real_demo["readonlyEvidenceDemo"]["executionSummary"]["deferred"] == 0
    assert real_demo["readonlyEvidenceDemo"]["score"]["earnedScore"] == 70
    readonly_report_detail = real_demo["readonlyEvidenceDemo"]["reportDetail"]
    assert readonly_report_detail["source"] == "sandbox.grade_runner.build_grading_report_detail"
    assert readonly_report_detail["mode"] == "READONLY_REAL_SANDBOX_POC"
    assert readonly_report_detail["checkSummary"]["executed"] == 2
    assert readonly_report_detail["checkSummary"]["deferred"] == 0
    assert readonly_report_detail["assessmentPlanSummary"]["alignedWithChecks"] is True
    assert readonly_report_detail["explainability"]["status"] == "EXPLAINABLE_READONLY_EVIDENCE"
    assert readonly_report_detail["readonlyEvidence"]["status"] == "COLLECTED"
    assert readonly_report_detail["readonlyEvidence"]["collectedTotal"] == 2
    assert [plan["type"] for plan in readonly_report_detail["checkPlans"]] == ["file_exists", "json_field"]
    assert all(plan["readonlyEvidence"]["status"] == "COLLECTED" for plan in readonly_report_detail["checkPlans"])
    assert all(
        plan["sandboxExecutionRequest"]["mode"] == "REAL_SANDBOX_REQUIRED"
        for plan in readonly_report_detail["checkPlans"]
    )
    assert all(
        plan["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY"
        for plan in readonly_report_detail["checkPlans"]
    )
    assert readonly_report_detail["safety"]["sourceGradingModified"] is False
    assert real_demo["readonlyEvidenceDemo"]["safety"]["contestantCodeExecuted"] is False
    controlled_evidence = real_demo["controlledDockerEvidenceDemo"]
    assert controlled_evidence["component"] == "ControlledDockerEvidenceDemo"
    assert controlled_evidence["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert controlled_evidence["planMode"] == "CONTROLLED_DOCKER_GRADING_PLAN"
    assert controlled_evidence["sourceGradingPath"] == "examples/output/real-llm-grading.json"
    assert controlled_evidence["gradingPath"] == "examples/output/mimo-real-demo-controlled-plan.json"
    assert controlled_evidence["submissionPath"] == "examples/submissions/real-demo-controlled"
    assert controlled_evidence["reportPath"] == "examples/output/mimo-real-demo-controlled-sandbox-report.json"
    assert controlled_evidence["imageVerifyPath"] == "examples/output/grading-sandbox-image-verify.json"
    assert controlled_evidence["image"]["tag"] == "ai-grading-python:0.1"
    assert controlled_evidence["image"]["pytestAvailable"] is True
    assert controlled_evidence["image"]["networkEnabledForGrading"] is False
    assert controlled_evidence["runner"]["hostExecutionAllowed"] is False
    assert controlled_evidence["runner"]["supportedCheckTypes"] == ["stdout_contains", "pytest"]
    assert controlled_evidence["checkSummary"]["executed"] == 2
    assert controlled_evidence["checkSummary"]["passed"] == 2
    assert controlled_evidence["checkSummary"]["byType"] == {"stdout_contains": 1, "pytest": 1}
    assert controlled_evidence["score"]["totalScore"] == 40
    assert controlled_evidence["score"]["earnedScore"] == 40
    assert [check["id"] for check in controlled_evidence["checks"]] == ["check_q1", "check_q4"]
    assert [check["type"] for check in controlled_evidence["checks"]] == ["stdout_contains", "pytest"]
    assert controlled_evidence["safety"]["sandboxExecuted"] is True
    assert controlled_evidence["safety"]["contestantCodeExecutedInContainer"] is True
    assert controlled_evidence["safety"]["hostExecutionAllowed"] is False
    assert controlled_evidence["safety"]["unknownShellExecuted"] is False
    assert controlled_evidence["safety"]["networkEnabled"] is False
    assert controlled_evidence["safety"]["autoApproveAllowed"] is False
    assert controlled_evidence["safety"]["realPublish"] is False
    assert real_demo["acceptanceSignals"]["readonlyEvidenceDemoExecuted"] is True
    assert real_demo["acceptanceSignals"]["pptxArtifactGenerated"] is True
    assert real_demo["acceptanceSignals"]["controlledDockerEvidenceExecuted"] is True
    assert real_demo["acceptanceSignals"]["controlledDockerEvidenceEarnedScore"] == 40
    assert real_demo["acceptanceSignals"]["notebookStaticEvidenceEarnedScore"] == 60
    assert real_demo["acceptanceSignals"]["gradingEvidenceCoverageEarnedScore"] == 100
    assert real_demo["acceptanceSignals"]["gradingEvidenceCoverageTotalScore"] == 100
    assert real_demo["acceptanceSignals"]["gradingEvidenceCoverageStatus"] == "GRADING_EVIDENCE_COVERAGE_COMPLETE"
    acceptance_summary = real_demo["realDemoAcceptanceSummary"]
    assert acceptance_summary["component"] == "RealDemoAcceptanceSummary"
    assert acceptance_summary["source"] == "phase2 demo-bundle acceptance"
    assert acceptance_summary["summaryPath"] == "examples/output/real-llm-demo-acceptance-summary.json"
    assert acceptance_summary["mode"] == "REAL_LLM_DEMO_ACCEPTANCE_STATIC"
    assert acceptance_summary["route"] == "/real-demo -> /review-center -> /ppt/:id/review -> /grading/:id/report"
    assert acceptance_summary["acceptance"]["passed"] is True
    assert acceptance_summary["acceptance"]["passedCount"] == 7
    assert acceptance_summary["acceptance"]["total"] == 7
    assert acceptance_summary["acceptance"]["failedStepIds"] == []
    assert acceptance_summary["signals"]["dslValidatedTotal"] == 4
    assert acceptance_summary["signals"]["waitingReviewDslTotal"] == 4
    assert acceptance_summary["signals"]["realDemoReviewQueueTaskTotal"] == 4
    assert acceptance_summary["signals"]["mcpOutputContractIncludesRealDemoReviewQueue"] is True
    assert acceptance_summary["signals"]["readonlyEvidenceCollectedTotal"] == 2
    assert acceptance_summary["signals"]["readonlyEvidenceDemoEarnedScore"] == 70
    assert acceptance_summary["signals"]["controlledDockerEvidenceEarnedScore"] == 40
    assert acceptance_summary["signals"]["notebookStaticEvidenceEarnedScore"] == 60
    assert acceptance_summary["signals"]["gradingEvidenceCoverageEarnedScore"] == 100
    assert acceptance_summary["signals"]["gradingEvidenceCoverageTotalScore"] == 100
    assert acceptance_summary["signals"]["gradingEvidenceCoverageStatus"] == "GRADING_EVIDENCE_COVERAGE_COMPLETE"
    assert acceptance_summary["gradingEvidenceCoverage"]["earnedScore"] == 100
    assert acceptance_summary["gradingEvidenceCoverage"]["totalScore"] == 100
    assert acceptance_summary["gradingEvidenceCoverage"]["manualReviewRequired"] is True
    assert acceptance_summary["gradingEvidenceCoverage"]["autoApproveAllowed"] is False
    assert acceptance_summary["signals"]["pptPageReviewActionVisible"] is True
    assert acceptance_summary["signals"]["candidatePreviewAnswerSafe"] is True
    assert [step["id"] for step in acceptance_summary["steps"]] == [
        "real_demo_bundle_valid",
        "real_demo_page_visible",
        "review_center_real_demo_queue_visible",
        "mcp_get_review_task_summary_contract_visible",
        "grading_report_readonly_report_detail_visible",
        "grading_evidence_coverage_complete",
        "ppt_artifact_review_action_visible",
    ]
    assert all(step["passed"] is True for step in acceptance_summary["steps"])
    assert acceptance_summary["safety"]["newLlmRequestSent"] is False
    assert acceptance_summary["safety"]["secretsRead"] is False
    assert acceptance_summary["safety"]["networkAccess"] is False
    assert acceptance_summary["safety"]["batchStateChangeAllowed"] is False
    assert acceptance_summary["safety"]["realPublishAllowed"] is False
    checklist = real_demo["oneClickDemoChecklist"]
    assert checklist["component"] == "RealDemoOneClickChecklist"
    assert checklist["source"] == "phase2 demo-bundle checklist"
    assert checklist["checklistPath"] == "examples/output/real-llm-demo-checklist.json"
    assert checklist["mode"] == "REAL_LLM_DEMO_CHECKLIST_STATIC"
    assert checklist["summary"]["readyForDemo"] is True
    assert checklist["summary"]["acceptancePassed"] is True
    assert checklist["summary"]["acceptancePassedCount"] == 7
    assert checklist["summary"]["acceptanceTotal"] == 7
    assert checklist["summary"]["sectionPassedCount"] == checklist["summary"]["sectionTotal"] == 6
    assert checklist["summary"]["gradingEvidenceCoverageEarnedScore"] == 100
    assert checklist["summary"]["gradingEvidenceCoverageTotalScore"] == 100
    assert checklist["summary"]["manualReviewRequired"] is True
    assert checklist["summary"]["autoApproveAllowed"] is False
    assert checklist["summary"]["realPublishAllowed"] is False
    assert [section["id"] for section in checklist["sections"]] == [
        "generated_dsl",
        "candidate_preview",
        "grading_evidence_coverage",
        "pptx_artifact",
        "review_and_mcp",
        "safety_boundaries",
    ]
    assert all(section["passed"] is True for section in checklist["sections"])
    assert checklist["sections"][2]["evidence"]["controlledDockerScore"] == 40
    assert checklist["sections"][2]["evidence"]["notebookStaticScore"] == 60
    assert checklist["safety"]["newLlmRequestSent"] is False
    assert checklist["safety"]["secretsRead"] is False
    assert checklist["safety"]["sandboxExecutedByChecklist"] is False
    assert checklist["safety"]["commandExecutedByChecklist"] is False
    assert checklist["safety"]["notebookExecutedByChecklist"] is False
    assert checklist["safety"]["realPublishAllowed"] is False
    mcp_revision_loop = real_demo["mcpRevisionLoop"]
    assert mcp_revision_loop["component"] == "RealDemoMcpRevisionLoop"
    assert mcp_revision_loop["visibleInDemo"] is True
    assert [tool["toolName"] for tool in mcp_revision_loop["toolChain"]] == [
        "request_review_revision",
        "regenerate_from_revision_mock",
    ]
    assert mcp_revision_loop["example"]["sourceTaskStatus"] == "WAITING_REVIEW"
    assert mcp_revision_loop["example"]["newTaskStatus"] == "WAITING_REVIEW"
    assert mcp_revision_loop["example"]["newTaskId"] == "task_lab_demo_revision"
    assert mcp_revision_loop["example"]["newArtifactId"] == "artifact_lab_revision_demo"
    assert mcp_revision_loop["safety"]["sourceTaskStatusUnchanged"] is True
    assert mcp_revision_loop["safety"]["newTaskWaitingReview"] is True
    assert mcp_revision_loop["safety"]["newLlmRequestSent"] is False
    assert mcp_revision_loop["safety"]["realLlmCalled"] is False
    assert mcp_revision_loop["safety"]["autoApproveAllowed"] is False
    assert mcp_revision_loop["safety"]["realPublish"] is False
    assert real_demo["safety"]["newLlmRequestSent"] is False
    assert real_demo["safety"]["secretsRead"] is False
    assert real_demo["safety"]["pptxArtifactGenerated"] is True
    assert real_demo["safety"]["pptxArtifactAutoPublishAllowed"] is False
    assert real_demo["safety"]["realPublish"] is False

    assert "真实 LLM Demo Evidence" in html
    assert "REAL_LLM_DEMO_REPLAY" in html
    assert "CoreBusinessDemoPath" in html
    assert "RealDemoAcceptanceSummary" in html
    assert "RealDemoOneClickChecklist" in html
    assert "RealDemoMcpRevisionLoop" in html
    assert "RealDslReviewPreview" in html
    assert "STATIC_REAL_LLM_DSL_REVIEW_PREVIEW" in html
    assert "TeacherOnlyGradingRefs" in html
    assert "gradingRefVisibleToCandidate=false" in html
    assert "teacherOnlyGradingRefVisibleInReview=true" in html
    assert "AI 工具应用入门实验" in html
    assert "check_waiting_review" in html
    assert "slideTotal=4" in html
    assert "Quality Signals" in html
    assert "lab_objective_depth" in html
    assert "request_review_revision -&gt; regenerate_from_revision_mock" in html
    assert "POST /api/review-tasks/{taskId}/revision-request" in html
    assert "POST /api/review-tasks/{taskId}/regenerate-mock" in html
    assert "newTaskId=task_lab_demo_revision" in html
    assert "artifact_lab_revision_demo" in html
    assert "sourceTaskStatusUnchanged=true" in html
    assert "realLlmCalled=false" in html
    assert "examples/output/real-llm-demo-checklist.json" in html
    assert "readyForDemo" in html
    assert "acceptance=7/7" in html
    assert "sections=6/6" in html
    assert "generated_dsl" in html
    assert "candidate_preview" in html
    assert "grading_evidence_coverage" in html
    assert "pptx_artifact" in html
    assert "review_and_mcp" in html
    assert "safety_boundaries" in html
    assert "ControlledDockerEvidenceDemo" in html
    assert "CONTROLLED_DOCKER_SANDBOX_POC" in html
    assert "examples/output/mimo-real-demo-controlled-plan.json" in html
    assert "examples/output/mimo-real-demo-controlled-sandbox-report.json" in html
    assert "examples/output/grading-sandbox-image-verify.json" in html
    assert "ai-grading-python:0.1" in html
    assert "stdout_contains=1" in html
    assert "pytest=1" in html
    assert "controlledDockerEvidenceEarnedScore" in html
    assert "gradingEvidenceCoverage=100/100" in html
    assert "sandboxExecutedByChecklist=false" in html
    assert "commandExecutedByChecklist=false" in html
    assert "GRADING_EVIDENCE_COVERAGE_COMPLETE" in html
    assert "staticNotebook=60/60" in html
    assert "sourceGradingPath=examples/output/real-llm-grading.json" in html
    assert "submissionMountMode=read_only" in html
    assert "phase2 demo-bundle acceptance" in html
    assert "examples/output/real-llm-demo-acceptance-summary.json" in html
    assert "acceptance.passed" in html
    assert "passedCount=7" in html
    assert "failedStepIds=[]" in html
    assert "real_demo_bundle_valid" in html
    assert "review_center_real_demo_queue_visible" in html
    assert "mcp_get_review_task_summary_contract_visible" in html
    assert "mcpOutputContractIncludesRealDemoReviewQueue=true" in html
    assert "readonlyEvidenceCollectedTotal=2" in html
    assert "real_lab_dsl" in html
    assert "real_exam_dsl_candidate_safe" in html
    assert "real_grading_dsl_preserved" in html
    assert "readonly_evidence_score" in html
    assert "pptx_artifact_review" in html
    assert "ppt_page_review_update" in html
    assert "stepTotal" in html
    assert "reviewCenterLinked=true" in html
    assert "pptPageReviewActionVisible=true" in html
    assert "reviewRequiredBeforePublish=true" in html
    assert "/real-demo -&gt; /review-center -&gt; /ppt/:id/review -&gt; /grading/:id/report" in html
    assert "PPT_PAGE_REVIEW_UPDATE writesOperationAudit=true" in html
    assert "sourceGradingModified=false" in html
    assert "Revision Decision" in html
    assert "realDemoPrototype.realDslRevisionDecision" in html
    assert "decisionStatus=REVISION_APPROVED_FOR_MANUAL_MERGE" in html
    assert "manualMergeRequired=true" in html
    assert "revisedDslModified=false" in html
    assert "Revision Promotion" in html
    assert "realDemoPrototype.realDslRevisionPromotion" in html
    assert "promotedStatus=WAITING_REVIEW" in html
    assert "promotedCandidateWritten=true" in html
    assert "Promotion Review Queue" in html
    assert "realDemoPrototype.realDslRevisionPromotionReviewQueueItem" in html
    assert "POST /api/review/real-dsl-revision-enqueue" in html
    assert "taskType=LAB_GENERATION_REVISION" in html
    assert "reviewDetailAvailable=true" in html
    assert "Promotion Review Disposition" in html
    assert "realDemoPrototype.realDslRevisionPromotionReviewDisposition" in html
    assert "state=APPROVED_FOR_MOCK_PUBLISH_ONLY" in html
    assert "mockPublishAvailable=true" in html
    assert "Lab Template Import Preview" in html
    assert "realDemoPrototype.labTemplateImportPreview" in html
    assert "POST /api/labs/import-preview" in html
    assert "create_lab_template_import_preview" in html
    assert "databaseWritten=false" in html
    assert "realAgentImport=false" in html
    assert "autoApproveAllowed=false" in html
    assert "WAITING_REVIEW" in html
    assert "answerVisibleToCandidate=false" in html
    assert "ReadonlyEvidenceDemo" in html
    assert "ReadonlyReportDetail" in html
    assert "sandbox.grade_runner.build_grading_report_detail" in html
    assert "READONLY_REAL_SANDBOX_POC" in html
    assert "reportDetail.checkSummary" in html
    assert "checkPlans[].readonlyEvidence.status" in html
    assert "readonlyEvidenceCollectedTotal=2" in html
    assert "sandboxExecutionRequest.mode" in html
    assert "REAL_SANDBOX_REQUIRED" in html
    assert "doesNotModifySourceGrading=true" in html
    assert "check_result_file" in html
    assert "check_accuracy_metric" in html
    assert "earnedScore=70" in html
    assert "PPTX Artifact" in html
    assert "real-llm-demo-ppt-artifact.pptx" in html
    assert "autoPublishAllowed=false" in html
    assert "newLlmRequestSent=false" in html
    assert "secretsRead=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "commandExecuted=false" in html
    assert "realPublish=false" in html
    assert "python lab_cli.py phase2 demo-bundle report" in html
    assert "python lab_cli.py phase2 demo-bundle acceptance" in html


def test_audit_observability_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/audit.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "GET /api/provider-audit-events" in html
    assert "GET /api/mcp-tool-call-records" in html
    assert "GET /api/workflow-runs" in html
    assert "GET /api/audit-events" in html
    assert "GET /api/review-audit-events" in html
    assert "providerCallAuditEvents" in html
    assert "mcpToolCallRecords" in html
    assert "AuditTrailPanel" in html
    assert "WorkflowLogViewer" in html
    assert "provider_audit_lab_demo" in html
    assert "mcp_call_analyze_demo" in html
    assert "mcp_call_missing_input_demo" in html
    assert "mcp_call_publish_lab_intent_demo" in html
    assert "mcp_call_publish_exam_intent_demo" in html
    assert "mcp_call_destroy_environment_intent_demo" in html
    assert "mcp_call_get_second_confirmation_status_demo" in html
    assert "publish_lab" in html
    assert "publish_exam" in html
    assert "destroy_environment" in html
    assert "get_second_confirmation_status" in html
    assert "Second Confirmation Status" in html
    assert "GET /api/review-tasks/{id}/second-confirmation-status" in html
    assert "readOnly=true" in html
    assert "confirmationActionAvailable=false" in html
    assert "confirmationEndpointEnabled=false" in html
    assert "PUBLISH_LAB_INTENT" in html
    assert "PUBLISH_EXAM_INTENT" in html
    assert "DESTROY_ENVIRONMENT_INTENT" in html
    assert "postReviewDisposition=APPROVED_EXECUTION_BLOCKED" in html
    assert "postReviewDisposition=APPROVED_PENDING_SECOND_CONFIRMATION" in html
    assert "secondConfirmationSatisfied=false" in html
    assert "reviewIntentOnly=true" in html
    assert "requiresSecondConfirmation=true" in html
    assert "realActionExecuted=false" in html
    assert "destroyRealEnvironmentEnabled=false" in html
    assert "environmentDestroyed=false" in html
    assert "argumentPreviewRedactsSecrets=true" in html
    assert "generatedStatus=WAITING_REVIEW" in html
    assert "MOCK_GRADING_RUN" in html
    assert "mock_grading_runner" in html
    assert "checkSummary.executed=0" in html
    assert "MOCK_PLAN_ONLY" in html
    assert "AssessmentPlanAuditSignal" in html
    assert "operationAuditEvents.detail.assessmentPlanSummary" in html
    assert "assessmentPlanSummary.source=grading.spec.assessmentPlan" in html
    assert "planTotal=6" in html
    assert "checkTotal=6" in html
    assert "spec.assessmentPlan[checkId=check_notebook_accuracy]" in html
    assert "spec.assessmentPlan[checkId=check_metrics_json]" in html
    assert "spec.assessmentPlan[checkId=check_training_log]" in html
    assert "assessmentPlanAlignedWithChecks=true" in html
    assert "checkPlans[].assessmentPlanSourceField" in html
    assert "spec.assessmentPlan[checkId=check_result_file]" in html
    assert "spec.assessmentPlan[checkId=check_stdout_accuracy]" in html
    assert "spec.assessmentPlan[checkId=check_pytest]" in html
    assert "assessmentPlanExecutionPlan" in html
    assert "assessmentPlanMockEvidence" in html
    assert "checkPlans[].containerSandboxPlan" in html
    assert "CONTAINER_PLAN_ONLY" in html
    assert "image=python:3.11-slim" in html
    assert "mount=read_only" in html
    assert "resultPlaceholder.status=NOT_EXECUTED" in html
    assert "containerSandboxPlan.safety" in html
    assert "containerStarted=false" in html
    assert "MOCK_EVIDENCE_NOT_COLLECTED" in html
    assert "assessmentPlanSandboxRequiredBeforeRealExecution=true" in html
    assert "runRealPytestEnabled=false" in html
    assert "commandExecuted=false" in html
    assert "realLlmCalled=false" in html
    assert "realMcpServerStarted=false" in html
    assert "realAgentStarted=false" in html
    assert "secretsRead=false" in html
    assert "networkAccess=false" in html
    assert "realCloudResourceChanged=false" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "disabled" in html


def test_audit_detail_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/audit-detail.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "GET /api/provider-audit-events" in html
    assert "GET /api/mcp-tool-call-records" in html
    assert "GET /api/workflow-runs/{id}" in html
    assert "GET /api/audit-events" in html
    assert "frontend/mock-data.json.auditDetailPrototype" in html
    assert "providerCallAuditEvents" in html
    assert "mcpToolCallRecords" in html
    assert "AuditTrailPanel" in html
    assert "WorkflowLogViewer" in html
    assert "provider_audit_lab_demo" in html
    assert "mcp_call_missing_input_demo" in html
    assert "workflow_run_demo" in html
    assert "traceId=trace_demo" in html
    assert "traceId=trace_demo_failed" in html
    assert "errorCode=VALIDATION_ERROR" in html
    assert "errorField=input" in html
    assert "argumentPreview={}" in html
    assert "argumentPreviewRedactsSecrets=true" in html
    assert "generatedStatus=WAITING_REVIEW" in html
    assert "AssessmentPlanManualReviewTrace" in html
    assert "source=gradingReviewPrototype.assessmentPlanManualReviewChecklist" in html
    assert "queueSource=reviewCenterPrototype.nextManualReviewAction" in html
    assert "entryRoute=/grading/:id/review?taskId=task_grading_demo" in html
    assert "primaryReviewFocus=review_assessment_plan_before_approval" in html
    assert "auditSource=operationAuditEvents[action=MOCK_GRADING_RUN].detail.assessmentPlanSummary" in html
    assert "verify_assessment_plan_aligned_with_checks" in html
    assert "confirm_mock_evidence_not_collected" in html
    assert "confirm_real_sandbox_evidence_required_before_real_execution" in html
    assert "verify_required_limits_present" in html
    assert "confirm_no_execution_or_publish" in html
    assert "TRACE_ONLY" in html
    assert "realSandboxRunEnabled=false" in html
    assert "realPublishAllowed=false" in html
    assert "retryRealCallEnabled=false" in html
    assert "readSecretEnabled=false" in html
    assert "realLlmCalled=false" in html
    assert "realMcpServerStarted=false" in html
    assert "realAgentStarted=false" in html
    assert "secretsRead=false" in html
    assert "networkAccess=false" in html
    assert "realCloudResourceChanged=false" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "disabled" in html


def test_audit_incident_review_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/audit-incidents.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "GET /api/provider-audit-events" in html
    assert "GET /api/mcp-tool-call-records" in html
    assert "GET /api/workflow-runs" in html
    assert "GET /api/audit-events" in html
    assert "frontend/mock-data.json.auditIncidentReviewPrototype" in html
    assert "AuditTrailPanel" in html
    assert "WorkflowLogViewer" in html
    assert "incident_mcp_missing_input_demo" in html
    assert "incident_provider_missing_prompt_demo" in html
    assert "mcp_call_missing_input_demo" in html
    assert "provider_audit_missing_prompt_demo" in html
    assert "category=INPUT_VALIDATION" in html
    assert "category=PROMPT_CONFIG" in html
    assert "errorCode=VALIDATION_ERROR" in html
    assert "errorCode=PROMPT_NOT_FOUND" in html
    assert "rule_mcp_validation_error" in html
    assert "rule_provider_prompt_missing" in html
    assert "safeMockCommand" in html
    assert "python lab_cli.py mcp call --tool analyze_material" in html
    assert "python lab_cli.py provider mock-generate --prompt-id lab_generation_v0" in html
    assert "exportIncidentReportEnabled=false" in html
    assert "autoFixEnabled=false" in html
    assert "retryRealCallEnabled=false" in html
    assert "realLlmCalled=false" in html
    assert "realMcpServerStarted=false" in html
    assert "realAgentStarted=false" in html
    assert "secretsRead=false" in html
    assert "networkAccess=false" in html
    assert "realCloudResourceChanged=false" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "disabled" in html


def test_operations_runbook_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/operations-runbook.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "/operations/runbook" in html
    assert "frontend/mock-data.json.operationsRunbookPrototype" in html
    assert "scripts/phase1-demo.runbook.json" in html
    assert "scripts/manifest.json" in html
    assert "ConsoleNavPanel" in html
    assert "DeliveryChecklistPanel" in html
    assert "AuditTrailPanel" in html
    assert "GET /api/health" in html
    assert "GET /api/provider-audit-events" in html
    assert "GET /api/mcp-tool-call-records" in html
    assert "GET /api/audit-events" in html
    assert "AGENTS.md" in html
    assert "docs/AI_PLATFORM_CODEX_FULL_GUIDE.md" in html
    assert "delivery/HANDOFF.md" in html
    assert "delivery/FAQ.md" in html
    assert "start .\\frontend\\console.html" in html
    assert "start .\\frontend\\audit.html" in html
    assert "start .\\frontend\\audit-detail.html" in html
    assert "start .\\frontend\\audit-incidents.html" in html
    assert "start .\\frontend\\delivery.html" in html
    assert "python lab_cli.py phase1 check" in html
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in html
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in html
    assert "python -m pytest tests/test_frontend_manifest.py" in html
    assert "python -m pytest" in html
    assert "python lab_cli.py provider audit --operation generateJson" in html
    assert "python lab_cli.py mcp audit --tool analyze_material" in html
    assert "python lab_cli.py audit list --resource-type ENVIRONMENT" in html
    assert "runCommandEnabled=false" in html
    assert "startRealAgentEnabled=false" in html
    assert "enableRealProviderEnabled=false" in html
    assert "callRealLlmEnabled=false" in html
    assert "remoteUploadEnabled=false" in html
    assert "realLlmCalled=false" in html
    assert "realAgentStarted=false" in html
    assert "realCloudResourceChanged=false" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "unknownShellExecuted=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "remoteUploadAllowed=false" in html
    assert "disabled" in html


def test_operations_acceptance_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/operations-acceptance.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "/operations/acceptance" in html
    assert "frontend/mock-data.json.operationsAcceptancePrototype" in html
    assert "config/delivery-package.contract.json" in html
    assert "delivery/FAQ.md" in html
    assert "delivery/HANDOFF.md" in html
    assert "delivery/PHASE2_READINESS.md" in html
    assert "DeliveryChecklistPanel" in html
    assert "ConsoleNavPanel" in html
    assert "AuditTrailPanel" in html
    assert "GET /api/health" in html
    assert "GET /api/workflow-runs" in html
    assert "GET /api/artifacts" in html
    assert "GET /api/audit-events" in html
    assert "readyForPhase2MockHandoff=true" in html
    assert "Acceptance" in html
    assert "8 / 8" in html
    assert "Missing" in html
    assert "0" in html
    assert "deliveryManifest.summary.missingRequired=0" in html
    assert "delivery_manifest_ready" in html
    assert "Delivery Manifest ready=127 required=127" in html
    assert "phase1_check_passed" in html
    assert "Phase 1 check 20/20" in html
    assert "runbook_present" in html
    assert "demo_script_checklist_present" in html
    assert "faq_present" in html
    assert "handoff_present" in html
    assert "phase2_gate_present" in html
    assert "assessment_plan_audit_trace_visible" in html
    assert "AssessmentPlanAuditSignal" in html
    assert "gradingReport.assessmentPlanSummary" in html
    assert "operationAuditEvents.detail.assessmentPlanSummary" in html
    assert "assessmentPlanSummary.source=grading.spec.assessmentPlan" in html
    assert "checkPlans[].assessmentPlanSourceField" in html
    assert "assessmentPlanAlignedWithChecks=true" in html
    assert "MOCK_EVIDENCE_NOT_COLLECTED" in html
    assert "/operations/launchpad" in html
    assert "/operations/presenter" in html
    assert "/operations/demo-script" in html
    assert "/operations/runbook" in html
    assert "/delivery" in html
    assert "/audit" in html
    assert "/audit/incidents" in html
    assert "python lab_cli.py phase1 check" in html
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in html
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in html
    assert "python -m pytest tests/test_frontend_manifest.py" in html
    assert "python -m pytest" in html
    assert "runCommandEnabled=false" in html
    assert "uploadPackageEnabled=false" in html
    assert "startRealAgentEnabled=false" in html
    assert "enableRealProviderEnabled=false" in html
    assert "callRealLlmEnabled=false" in html
    assert "realPublishEnabled=false" in html
    assert "realLlmCalled=false" in html
    assert "realAgentStarted=false" in html
    assert "realCloudResourceChanged=false" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "unknownShellExecuted=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "remoteUploadAllowed=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "disabled" in html


def test_operations_demo_map_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/operations-demo-map.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "/operations/demo-map" in html
    assert "frontend/mock-data.json.operationsDemoMapPrototype" in html
    assert "frontend/ui.manifest.json" in html
    assert "frontend/mock-data.json" in html
    assert "ConsoleNavPanel" in html
    assert "DeliveryChecklistPanel" in html
    assert "AuditTrailPanel" in html
    assert "GET /api/health" in html
    assert "GET /api/review-task-summary" in html
    assert "GET /api/workflow-runs" in html
    assert "GET /api/audit-events" in html
    assert "Sequences" in html
    assert "Route Entries" in html
    assert "30" in html
    assert "Roles" in html
    assert "entry_acceptance" in html
    assert "real_llm_demo_evidence" in html
    assert "/real-demo" in html
    assert "/workflows" in html
    assert "/console" in html
    assert "/operations/presenter" in html
    assert "/operations/demo-script" in html
    assert "/operations/runbook" in html
    assert "/operations/acceptance" in html
    assert "/delivery" in html
    assert "audit_observability" in html
    assert "/audit/:id" in html
    assert "/audit/incidents" in html
    assert "review_tasks" in html
    assert "/ai-tasks" in html
    assert "/review-center" in html
    assert "/labs/:id/review" in html
    assert "/exams/:id/review" in html
    assert "/grading/:id/review" in html
    assert "/ppt/:id/review" in html
    assert "content_generation" in html
    assert "/dashboard" in html
    assert "/labs/generate" in html
    assert "/exams/generate" in html
    assert "/ppt" in html
    assert "grading_environment" in html
    assert "/grading/:id/report" in html
    assert "/environments" in html
    assert "operation_config" in html
    assert "/skills" in html
    assert "/settings/providers" in html
    assert "operator" in html
    assert "reviewer" in html
    assert "teacher" in html
    assert "developer" in html
    assert "start .\\frontend\\operations-demo-map.html" in html
    assert "start .\\frontend\\real-demo.html" in html
    assert "start .\\frontend\\operations-presenter.html" in html
    assert "start .\\frontend\\operations-demo-script.html" in html
    assert "start .\\frontend\\console.html" in html
    assert "python lab_cli.py phase1 check" in html
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in html
    assert "python -m pytest tests/test_frontend_manifest.py" in html
    assert "runCommandEnabled=false" in html
    assert "batchStateChangeEnabled=false" in html
    assert "uploadPackageEnabled=false" in html
    assert "startRealAgentEnabled=false" in html
    assert "enableRealProviderEnabled=false" in html
    assert "callRealLlmEnabled=false" in html
    assert "realPublishEnabled=false" in html
    assert "realLlmCalled=false" in html
    assert "realMcpServerStarted=false" in html
    assert "realAgentStarted=false" in html
    assert "realCloudResourceChanged=false" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "unknownShellExecuted=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "remoteUploadAllowed=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "disabled" in html


def test_operations_demo_script_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/operations-demo-script.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "/operations/demo-script" in html
    assert "frontend/mock-data.json.operationsDemoScriptPrototype" in html
    assert "frontend/mock-data.json.operationsPresenterPrototype" in html
    assert "delivery/phase1-demo-script-checklist.json" in html
    assert "delivery/DEMO_SCRIPT_CHECKLIST.md" in html
    assert "ConsoleNavPanel" in html
    assert "DeliveryChecklistPanel" in html
    assert "AuditTrailPanel" in html
    assert "GET /api/health" in html
    assert "GET /api/review-task-summary" in html
    assert "GET /api/workflow-runs" in html
    assert "GET /api/artifacts" in html
    assert "GET /api/audit-events" in html
    assert "MCP get_review_task_summary" in html
    assert "reviewPriorityQueue" in html
    assert "Steps" in html
    assert "15" in html
    assert "Signals" in html
    assert "8" in html
    assert "Blocked Actions" in html
    assert "8" in html
    assert "175 / 175" in html
    assert "20 / 20" in html
    assert "read_rules" in html
    assert "open_launchpad" in html
    assert "open_demo_map" in html
    assert "open_real_demo_evidence" in html
    assert "readonlyEvidenceDemo.executed=2" in html
    assert "newLlmRequestSent=false" in html
    assert "open_runbook" in html
    assert "run_phase1_check" in html
    assert "export_delivery_package" in html
    assert "render_acceptance_report" in html
    assert "open_acceptance" in html
    assert "open_delivery" in html
    assert "open_incident_review" in html
    assert "validate_cli_review_priority_queue" in html
    assert "validate_backend_mcp_review_priority_queue" in html
    assert "confirm_review_gate" in html
    assert "confirm_blocked_actions" in html
    assert "review_priority_queue_visible" in html
    assert "topPriorityTaskId=task_grading_demo" in html
    assert "reasonCode=HIGH_RISK_MOCK_EVIDENCE_REQUIRED" in html
    assert "recommendedAction=review_grading_plan_before_publish" in html
    assert "assessment_plan_audit_trace_visible" in html
    assert "AssessmentPlanAuditSignal" in html
    assert "gradingReport.assessmentPlanSummary" in html
    assert "operationAuditEvents.detail.assessmentPlanSummary" in html
    assert "assessmentPlanSummary.source=grading.spec.assessmentPlan" in html
    assert "checkPlans[].assessmentPlanSourceField" in html
    assert "assessmentPlanAlignedWithChecks=true" in html
    assert "/operations/launchpad" in html
    assert "/operations/demo-map" in html
    assert "/operations/runbook" in html
    assert "/operations/acceptance" in html
    assert "/delivery" in html
    assert "/audit/incidents" in html
    assert "WAITING_REVIEW" in html
    assert "start .\\frontend\\operations-presenter.html" in html
    assert "start .\\frontend\\operations-demo-script.html" in html
    assert "start .\\frontend\\operations-launchpad.html" in html
    assert "start .\\frontend\\operations-demo-map.html" in html
    assert "start .\\frontend\\real-demo.html" in html
    assert "start .\\frontend\\operations-runbook.html" in html
    assert "python lab_cli.py phase1 check" in html
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in html
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in html
    assert "python lab_cli.py review batch-summary" in html
    assert "python lab_cli.py mcp call --tool get_review_task_summary --arguments" in html
    assert "python -m pytest tests/test_demo_script_checklist.py" in html
    assert "python -m pytest tests/test_backend_mock_api.py tests/test_mcp_mock_tools.py tests/test_cli.py" in html
    assert "viewDemoScriptSummaryEnabled=true" in html
    assert "runCommandEnabled=false" in html
    assert "uploadPackageEnabled=false" in html
    assert "batchStateChangeEnabled=false" in html
    assert "batchStateChangeAllowed=false" in html
    assert "startRealAgentEnabled=false" in html
    assert "enableRealProviderEnabled=false" in html
    assert "callRealLlmEnabled=false" in html
    assert "runRealSandboxEnabled=false" in html
    assert "executeContestantCodeEnabled=false" in html
    assert "realPublishEnabled=false" in html
    assert "realLlmCalled=false" in html
    assert "realMcpServerStarted=false" in html
    assert "realAgentStarted=false" in html
    assert "realCloudResourceChanged=false" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "unknownShellExecuted=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "remoteUploadAllowed=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "answerVisibleToCandidate=false" in html
    assert "disabled" in html


def test_operations_presenter_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/operations-presenter.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "/operations/presenter" in html
    assert "frontend/mock-data.json.operationsPresenterPrototype" in html
    assert "frontend/mock-data.json.operationsDemoScriptPrototype" in html
    assert "frontend/mock-data.json.realDemoPrototype.coreBusinessDemoPath" in html
    assert "CoreBusinessDemoPath" in html
    assert "RealDemoAcceptanceSummary" in html
    assert "source=realDemoPrototype.realDemoAcceptanceSummary" in html
    assert "summaryPath=examples/output/real-llm-demo-acceptance-summary.json" in html
    assert "acceptancePassed=true" in html
    assert "passedCount=7" in html
    assert "failedStepIds=[]" in html
    assert "mcpOutputContractIncludesRealDemoReviewQueue=true" in html
    assert "readonlyEvidenceCollectedTotal=2" in html
    assert "realPublishAllowed=false" in html
    assert "delivery/phase1-demo-script-checklist.json" in html
    assert "delivery/DEMO_SCRIPT_CHECKLIST.md" in html
    assert "Presenter View" in html
    assert "manualOnly=true" in html
    assert "ConsoleNavPanel" in html
    assert "DeliveryChecklistPanel" in html
    assert "AuditTrailPanel" in html
    assert "GET /api/health" in html
    assert "GET /api/review-task-summary" in html
    assert "GET /api/workflow-runs" in html
    assert "GET /api/artifacts" in html
    assert "GET /api/audit-events" in html
    assert "MCP get_review_task_summary" in html
    assert "reviewPriorityQueue" in html
    assert "Steps" in html
    assert "Speaker Cues" in html
    assert "14" in html
    assert "Signals" in html
    assert "8" in html
    assert "Blocked Actions" in html
    assert "8" in html
    assert "175 / 175" in html
    assert "20 / 20" in html
    assert "speakerCue" in html
    assert "read_rules" in html
    assert "open_launchpad" in html
    assert "open_demo_map" in html
    assert "open_runbook" in html
    assert "run_phase1_check" in html
    assert "export_delivery_package" in html
    assert "render_acceptance_report" in html
    assert "open_acceptance" in html
    assert "open_delivery" in html
    assert "open_incident_review" in html
    assert "validate_cli_review_priority_queue" in html
    assert "validate_backend_mcp_review_priority_queue" in html
    assert "confirm_review_gate" in html
    assert "confirm_blocked_actions" in html
    assert "review_priority_queue_visible" in html
    assert "topPriorityTaskId=task_grading_demo" in html
    assert "reasonCode=HIGH_RISK_MOCK_EVIDENCE_REQUIRED" in html
    assert "recommendedAction=review_grading_plan_before_publish" in html
    assert "source=realDemoPrototype.coreBusinessDemoPath" in html
    assert "bundlePath=examples/output/real-llm-demo-bundle.json" in html
    assert "/real-demo -&gt; /review-center -&gt; /ppt/:id/review -&gt; /grading/:id/report" in html
    assert "stepTotal=6" in html
    assert "dslValidatedTotal=4" in html
    assert "waitingReviewDslTotal=4" in html
    assert "readonlyEvidenceDemoExecuted=true" in html
    assert "readonlyEvidenceDemoEarnedScore=70" in html
    assert "reviewCenterLinked=true" in html
    assert "pptPageReviewActionVisible=true" in html
    assert "reviewRequiredBeforePublish=true" in html
    assert "assessment_plan_audit_trace_visible" in html
    assert "AssessmentPlanAuditSignal" in html
    assert "gradingReport.assessmentPlanSummary" in html
    assert "operationAuditEvents.detail.assessmentPlanSummary" in html
    assert "assessmentPlanSummary.source=grading.spec.assessmentPlan" in html
    assert "checkPlans[].assessmentPlanSourceField" in html
    assert "assessmentPlanAlignedWithChecks=true" in html
    assert "/operations/launchpad" in html
    assert "/operations/demo-map" in html
    assert "/operations/runbook" in html
    assert "/operations/acceptance" in html
    assert "/delivery" in html
    assert "/audit/incidents" in html
    assert "WAITING_REVIEW" in html
    assert "start .\\frontend\\operations-presenter.html" in html
    assert "start .\\frontend\\operations-demo-script.html" in html
    assert "start .\\frontend\\operations-launchpad.html" in html
    assert "python lab_cli.py phase1 check" in html
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in html
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in html
    assert "python lab_cli.py review batch-summary" in html
    assert "python lab_cli.py mcp call --tool get_review_task_summary --arguments" in html
    assert "python -m pytest tests/test_frontend_manifest.py" in html
    assert "python -m pytest tests/test_backend_mock_api.py tests/test_mcp_mock_tools.py tests/test_cli.py" in html
    assert "viewPresenterSummaryEnabled=true" in html
    assert "runCommandEnabled=false" in html
    assert "uploadPackageEnabled=false" in html
    assert "batchStateChangeEnabled=false" in html
    assert "batchStateChangeAllowed=false" in html
    assert "startRealAgentEnabled=false" in html
    assert "enableRealProviderEnabled=false" in html
    assert "callRealLlmEnabled=false" in html
    assert "runRealSandboxEnabled=false" in html
    assert "executeContestantCodeEnabled=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "realLlmCalled=false" in html
    assert "realMcpServerStarted=false" in html
    assert "realAgentStarted=false" in html
    assert "realCloudResourceChanged=false" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "unknownShellExecuted=false" in html
    assert "remoteUploadAllowed=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "answerVisibleToCandidate=false" in html
    assert "disabled" in html



def test_operations_signoff_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/operations-signoff.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "/operations/signoff" in html
    assert "frontend/mock-data.json.operationsSignoffPrototype" in html
    assert "frontend/mock-data.json.deliveryPrototype" in html
    assert "frontend/mock-data.json.operationsAcceptancePrototype" in html
    assert "config/delivery-package.contract.json" in html
    assert "delivery/phase1-delivery-index.json" in html
    assert "delivery/HANDOFF.md" in html
    assert "scripts/phase1-demo.runbook.json" in html
    assert "frontend/mock-data.json.reviewCenterPrototype.reviewPriorityQueue" in html
    assert "frontend/mock-data.json.realDemoPrototype.coreBusinessDemoPath" in html
    assert "CoreBusinessDemoPath" in html
    assert "RealDemoAcceptanceSummary" in html
    assert "real_demo_acceptance_summary_passed" in html
    assert "source=realDemoPrototype.realDemoAcceptanceSummary" in html
    assert "summaryPath=examples/output/real-llm-demo-acceptance-summary.json" in html
    assert "acceptancePassed=true" in html
    assert "passedCount=7" in html
    assert "failedStepIds=[]" in html
    assert "mcpOutputContractIncludesRealDemoReviewQueue=true" in html
    assert "readonlyEvidenceCollectedTotal=2" in html
    assert "realPublishAllowed=false" in html
    assert "ConsoleNavPanel" in html
    assert "DeliveryChecklistPanel" in html
    assert "AuditTrailPanel" in html
    assert "GET /api/health" in html
    assert "GET /api/review-task-summary" in html
    assert "GET /api/workflow-runs" in html
    assert "GET /api/artifacts" in html
    assert "GET /api/audit-events" in html
    assert "MCP get_review_task_summary" in html
    assert "7 / 7" in html
    assert "175 / 175" in html
    assert "20 / 20" in html
    assert "14 / 14" in html
    assert "phase1_self_check" in html
    assert "delivery_manifest_ready" in html
    assert "acceptance_summary_passed" in html
    assert "safety_assertions_passed" in html
    assert "review_gate_visible" in html
    assert "demo_entrypoints_ready" in html
    assert "WAITING_REVIEW" in html
    assert "review_priority_queue" in html
    assert "审核优先队列签收" in html
    assert "topPriorityTaskId=task_grading_demo" in html
    assert "topPriorityLevel=URGENT" in html
    assert "topPriorityReasonCode=HIGH_RISK_MOCK_EVIDENCE_REQUIRED" in html
    assert "recommendedAction=review_grading_plan_before_publish" in html
    assert "queueTotal=3" in html
    assert "autoApproveAllowed=false" in html
    assert "batchStateChangeAllowed=false" in html
    assert "realPublishAllowed=false" in html
    assert "core_business_demo_path_visible" in html
    assert "source=realDemoPrototype.coreBusinessDemoPath" in html
    assert "bundlePath=examples/output/real-llm-demo-bundle.json" in html
    assert "/real-demo -&gt; /review-center -&gt; /ppt/:id/review -&gt; /grading/:id/report" in html
    assert "stepTotal=6" in html
    assert "dslValidatedTotal=4" in html
    assert "waitingReviewDslTotal=4" in html
    assert "readonlyEvidenceDemoExecuted=true" in html
    assert "readonlyEvidenceDemoEarnedScore=70" in html
    assert "reviewCenterLinked=true" in html
    assert "pptPageReviewActionVisible=true" in html
    assert "reviewRequiredBeforePublish=true" in html
    assert "14-step script" in html
    assert "start .\\frontend\\operations-signoff.html" in html
    assert "python lab_cli.py phase1 check" in html
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in html
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in html
    assert "python lab_cli.py review batch-summary" in html
    assert "python lab_cli.py mcp call --tool get_review_task_summary --arguments" in html
    assert "python -m pytest tests/test_frontend_manifest.py" in html
    assert "python -m pytest tests/test_backend_mock_api.py tests/test_mcp_mock_tools.py tests/test_cli.py" in html
    assert "runCommandEnabled=false" in html
    assert "uploadPackageEnabled=false" in html
    assert "batchStateChangeEnabled=false" in html
    assert "startRealAgentEnabled=false" in html
    assert "enableRealProviderEnabled=false" in html
    assert "callRealLlmEnabled=false" in html
    assert "runRealSandboxEnabled=false" in html
    assert "executeContestantCodeEnabled=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "realLlmCalled=false" in html
    assert "realMcpServerStarted=false" in html
    assert "realAgentStarted=false" in html
    assert "realCloudResourceChanged=false" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "unknownShellExecuted=false" in html
    assert "remoteUploadAllowed=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "answerVisibleToCandidate=false" in html
    assert "disabled" in html

def test_operations_launchpad_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/operations-launchpad.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "/operations/launchpad" in html
    assert "frontend/mock-data.json.operationsLaunchpadPrototype" in html
    assert "frontend/mock-data.json.consolePrototype" in html
    assert "frontend/mock-data.json.deliveryPrototype" in html
    assert "frontend/ui.manifest.json" in html
    assert "ConsoleNavPanel" in html
    assert "DeliveryChecklistPanel" in html
    assert "AuditTrailPanel" in html
    assert "GET /api/health" in html
    assert "GET /api/workflow-runs" in html
    assert "GET /api/artifacts" in html
    assert "GET /api/audit-events" in html
    assert "Entry Cards" in html
    assert "Validation Commands" in html
    assert "175 / 175" in html
    assert "/console" in html
    assert "real-demo.html" in html
    assert "readonlyEvidenceDemo" in html
    assert "/operations/demo-map" in html
    assert "/operations/presenter" in html
    assert "/operations/demo-script" in html
    assert "/operations/runbook" in html
    assert "/operations/acceptance" in html
    assert "/delivery" in html
    assert "/audit" in html
    assert "/review-center" in html
    assert "start .\\frontend\\operations-launchpad.html" in html
    assert "start .\\frontend\\real-demo.html" in html
    assert "start .\\frontend\\operations-presenter.html" in html
    assert "start .\\frontend\\operations-demo-script.html" in html
    assert "python lab_cli.py phase1 check" in html
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in html
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in html
    assert "python -m pytest" in html
    assert "runCommandEnabled=false" in html
    assert "uploadPackageEnabled=false" in html
    assert "batchStateChangeEnabled=false" in html
    assert "startRealAgentEnabled=false" in html
    assert "enableRealProviderEnabled=false" in html
    assert "callRealLlmEnabled=false" in html
    assert "realPublishEnabled=false" in html
    assert "realLlmCalled=false" in html
    assert "realMcpServerStarted=false" in html
    assert "realCloudResourceChanged=false" in html
    assert "sandboxExecuted=false" in html
    assert "contestantCodeExecuted=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "disabled" in html



def test_access_entrypoints_frontend_mock_data_is_safe():
    mock_data = load_json("frontend/mock-data.json")
    access = mock_data["accessEntrypointsPrototype"]

    assert access["mode"] == "MOCK_ONLY"
    assert access["route"] == "/access"
    assert access["path"] == "frontend/access.html"
    assert access["summary"]["deliveryReady"] == 175
    assert access["summary"]["deliveryRequired"] == 175
    assert access["summary"]["plannedUrlTotal"] == len(access["plannedLocalUrls"])
    assert access["summary"]["enabledUrlTotal"] == 0
    assert access["summary"]["portListeningTotal"] == 0
    assert {entry["route"] for entry in access["staticEntrypoints"]} >= {
        "/access",
        "/operations/launchpad",
        "/operations/signoff",
        "/delivery",
        "/console",
    }
    assert all((ROOT / entry["path"]).exists() for entry in access["staticEntrypoints"])
    assert {entry["url"] for entry in access["plannedLocalUrls"]} == {
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
    }
    assert all(entry["enabled"] is False for entry in access["plannedLocalUrls"])
    assert all(entry["portListening"] is False for entry in access["plannedLocalUrls"])
    assert access["actionPolicy"]["startServerEnabled"] is False
    assert access["actionPolicy"]["bindExternalIpEnabled"] is False
    assert access["actionPolicy"]["generatePublicUrlEnabled"] is False
    assert access["safety"]["realHttpServerStarted"] is False
    assert access["safety"]["portListening"] is False
    assert access["safety"]["externalIpBound"] is False
    assert access["safety"]["networkAccess"] is False
    assert access["safety"]["realMcpServerStarted"] is False
    assert access["safety"]["realAgentStarted"] is False
    assert access["safety"]["realLlmCalled"] is False
    assert access["safety"]["autoPublishAllowed"] is False
    assert access["safety"]["realPublish"] is False


def test_operations_signoff_prototype_contract_is_mock_only():
    mock_data = load_json("frontend/mock-data.json")
    signoff = mock_data["operationsSignoffPrototype"]

    assert signoff["mode"] == "MOCK_ONLY"
    assert signoff["route"] == "/operations/signoff"
    assert signoff["summary"]["signoffGateTotal"] == len(signoff["signoffGates"])
    assert signoff["summary"]["signoffGatePassed"] == 6
    assert signoff["summary"]["deliveryReady"] == 175
    assert signoff["summary"]["deliveryRequired"] == 175
    assert signoff["summary"]["phase1CheckPassed"] == 20
    assert signoff["summary"]["acceptancePassed"] == 14
    assert signoff["summary"]["safetyAssertionPassed"] == 6
    assert signoff["summary"]["safeCommandTotal"] == len(signoff["safeCommands"])
    assert signoff["summary"]["reviewPriorityQueueTotal"] == 3
    assert signoff["summary"]["urgentReviewTotal"] == 1
    assert {gate["id"] for gate in signoff["signoffGates"]} == {
        "phase1_self_check",
        "delivery_manifest_ready",
        "acceptance_summary_passed",
        "safety_assertions_passed",
        "review_gate_visible",
        "demo_entrypoints_ready",
    }
    assert all(gate["passed"] is True for gate in signoff["signoffGates"])
    assert "deliveryPrototype" in signoff["uses"]
    assert "operationsAcceptancePrototype" in signoff["uses"]
    assert "reviewCenterPrototype.reviewPriorityQueue" in signoff["uses"]
    assert "realDemoPrototype.coreBusinessDemoPath" in signoff["uses"]
    assert "realDemoPrototype.realDemoAcceptanceSummary" in signoff["uses"]
    assert "GET /api/review-task-summary" in signoff["uses"]
    assert "mcp-server/tools.manifest.json.get_review_task_summary.outputContract" in signoff["uses"]
    assert signoff["reviewPrioritySignoff"]["source"] == "reviewCenterPrototype.reviewPriorityQueue"
    assert signoff["reviewPrioritySignoff"]["api"] == "GET /api/review-task-summary"
    assert signoff["reviewPrioritySignoff"]["mcpTool"] == "get_review_task_summary"
    assert signoff["reviewPrioritySignoff"]["topPriorityTaskId"] == "task_grading_demo"
    assert signoff["reviewPrioritySignoff"]["topPriorityLevel"] == "URGENT"
    assert signoff["reviewPrioritySignoff"]["topPriorityReasonCode"] == "HIGH_RISK_MOCK_EVIDENCE_REQUIRED"
    assert signoff["reviewPrioritySignoff"]["recommendedAction"] == "review_grading_plan_before_publish"
    assert signoff["reviewPrioritySignoff"]["queueTotal"] == 3
    assert signoff["reviewPrioritySignoff"]["urgentTotal"] == 1
    assert signoff["reviewPrioritySignoff"]["highTotal"] == 1
    assert signoff["reviewPrioritySignoff"]["normalTotal"] == 1
    assert signoff["reviewPrioritySignoff"]["autoApproveAllowed"] is False
    assert signoff["reviewPrioritySignoff"]["batchStateChangeAllowed"] is False
    assert signoff["reviewPrioritySignoff"]["realPublishAllowed"] is False
    core_path_signoff = signoff["coreBusinessDemoPathSignoff"]
    assert core_path_signoff["component"] == "CoreBusinessDemoPath"
    assert core_path_signoff["source"] == "realDemoPrototype.coreBusinessDemoPath"
    assert core_path_signoff["bundlePath"] == "examples/output/real-llm-demo-bundle.json"
    assert core_path_signoff["route"] == "/real-demo -> /review-center -> /ppt/:id/review -> /grading/:id/report"
    assert core_path_signoff["stepTotal"] == 6
    assert core_path_signoff["dslValidatedTotal"] == 4
    assert core_path_signoff["waitingReviewDslTotal"] == 4
    assert core_path_signoff["readonlyEvidenceDemoExecuted"] is True
    assert core_path_signoff["readonlyEvidenceDemoEarnedScore"] == 70
    assert core_path_signoff["reviewCenterLinked"] is True
    assert core_path_signoff["pptPageReviewActionVisible"] is True
    assert core_path_signoff["reviewRequiredBeforePublish"] is True
    assert core_path_signoff["autoApproveAllowed"] is False
    assert core_path_signoff["autoPublishAllowed"] is False
    assert core_path_signoff["realPublish"] is False
    acceptance_signoff = signoff["realDemoAcceptanceSummarySignoff"]
    assert acceptance_signoff["component"] == "RealDemoAcceptanceSummary"
    assert acceptance_signoff["source"] == "realDemoPrototype.realDemoAcceptanceSummary"
    assert acceptance_signoff["summaryPath"] == "examples/output/real-llm-demo-acceptance-summary.json"
    assert acceptance_signoff["bundlePath"] == "examples/output/real-llm-demo-bundle.json"
    assert acceptance_signoff["route"] == "/real-demo -> /review-center -> /ppt/:id/review -> /grading/:id/report"
    assert acceptance_signoff["acceptancePassed"] is True
    assert acceptance_signoff["passedCount"] == 7
    assert acceptance_signoff["total"] == 7
    assert acceptance_signoff["failedStepIds"] == []
    assert acceptance_signoff["mcpOutputContractIncludesRealDemoReviewQueue"] is True
    assert acceptance_signoff["readonlyEvidenceCollectedTotal"] == 2
    assert acceptance_signoff["readonlyEvidenceDemoEarnedScore"] == 70
    assert acceptance_signoff["pptPageReviewActionVisible"] is True
    assert acceptance_signoff["candidatePreviewAnswerSafe"] is True
    assert acceptance_signoff["newLlmRequestSent"] is False
    assert acceptance_signoff["secretsRead"] is False
    assert acceptance_signoff["networkAccess"] is False
    assert acceptance_signoff["batchStateChangeAllowed"] is False
    assert acceptance_signoff["realPublishAllowed"] is False
    assert "start .\\frontend\\operations-signoff.html" in signoff["safeCommands"]
    assert "python lab_cli.py review batch-summary" in signoff["safeCommands"]
    assert "python lab_cli.py mcp call --tool get_review_task_summary --arguments \"{}\"" in signoff["safeCommands"]
    assert "python -m pytest tests/test_backend_mock_api.py tests/test_mcp_mock_tools.py tests/test_cli.py" in signoff["safeCommands"]
    assert signoff["actionPolicy"]["runCommandEnabled"] is False
    assert signoff["actionPolicy"]["uploadPackageEnabled"] is False
    assert signoff["actionPolicy"]["batchStateChangeEnabled"] is False
    assert signoff["actionPolicy"]["startRealAgentEnabled"] is False
    assert signoff["actionPolicy"]["enableRealProviderEnabled"] is False
    assert signoff["actionPolicy"]["callRealLlmEnabled"] is False
    assert signoff["actionPolicy"]["runRealSandboxEnabled"] is False
    assert signoff["actionPolicy"]["executeContestantCodeEnabled"] is False
    assert signoff["safety"]["readOnly"] is True
    assert signoff["safety"]["realLlmCalled"] is False
    assert signoff["safety"]["realMcpServerStarted"] is False
    assert signoff["safety"]["realAgentStarted"] is False
    assert signoff["safety"]["realCloudResourceChanged"] is False
    assert signoff["safety"]["sandboxExecuted"] is False
    assert signoff["safety"]["contestantCodeExecuted"] is False
    assert signoff["safety"]["unknownShellExecuted"] is False
    assert signoff["safety"]["autoPublishAllowed"] is False
    assert signoff["safety"]["realPublish"] is False
    assert signoff["safety"]["remoteUploadAllowed"] is False
    assert signoff["safety"]["secretVisibleInFrontend"] is False
    assert signoff["safety"]["answerVisibleToCandidate"] is False

def test_delivery_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/delivery.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型：禁用" in html
    assert "真实云资源：禁用" in html
    assert "真实沙箱：禁用" in html
    assert "自动发布：禁用" in html
    assert "真实发布：禁用" in html
    assert "密钥展示：禁用" in html
    assert "python lab_cli.py phase1 check" in html
    assert "python lab_cli.py phase1 export --output examples/output/phase1-delivery-package.json" in html
    assert "python lab_cli.py phase1 report --package examples/output/phase1-delivery-package.json --output examples/output/phase1-acceptance-report.md" in html
    assert "python -m pytest" in html
    assert "deliveryManifest.summary.missingRequired=0" in html
    assert "acceptanceSummary.passed=true" in html
    assert "safetyAssertions" in html
    assert "phase1Check.total=20" in html
    assert "DeliveryChecklistPanel" in html
    assert "frontend_console_prototype" in html
    assert "frontend_audit_observability_prototype" in html
    assert "frontend_audit_detail_prototype" in html
    assert "frontend_audit_incident_review_prototype" in html
    assert "frontend_operations_launchpad_prototype" in html
    assert "frontend_operations_runbook_prototype" in html
    assert "frontend_operations_acceptance_prototype" in html
    assert "frontend_operations_demo_map_prototype" in html
    assert "frontend_operations_presenter_prototype" in html
    assert "frontend_operations_demo_script_prototype" in html
    assert "frontend_ppt_review_prototype" in html
    assert "frontend_delivery_prototype" in html
    assert "delivery_index_readme" in html
    assert "delivery_index_contract" in html
    assert "delivery_faq_md" in html
    assert "delivery_faq_contract" in html
    assert "delivery_handoff_md" in html
    assert "delivery_handoff_contract" in html
    assert "demo_script_checklist_md" in html
    assert "demo_script_checklist_contract" in html
    assert "phase2_readiness_md" in html
    assert "phase2_readiness_contract" in html
    assert "phase2_provider_plan_md" in html
    assert "phase2_provider_plan_contract" in html
    assert "provider_adapter" in html
    assert "provider_adapter_contract" in html
    assert "provider_adapter_errors_contract" in html
    assert "provider_call_audit_model" in html
    assert "provider_audit_contract" in html
    assert "provider_audit_workflow_contract" in html
    assert "provider_adapter_workflow_helper" in html
    assert "mcp_mock_tools" in html
    assert "mcp_tool_call_audit_model" in html
    assert "mcp_tool_call_audit_contract" in html
    assert "high_risk_mcp_safety_matrix" in html
    assert "high_risk_mcp_handoff_md" in html
    assert "high_risk_mcp_handoff_contract" in html
    assert "final_signoff_md" in html
    assert "final_signoff_contract" in html
    assert "operations_manual_md" in html
    assert "operations_manual_contract" in html
    assert "operations_skill_pack_md" in html
    assert "operations_skill_pack_contract" in html
    assert "standalone_agent_delivery_md" in html
    assert "standalone_agent_delivery_contract" in html
    assert "mcp_mock_tools_tests" in html
    assert "scripts_phase1_demo_runbook_json" in html
    assert "scripts_phase1_demo_runbook_md" in html
    assert "phase1_demo_runbook_present" in html
    assert "demo_script_checklist_present" in html
    assert "core_deliverables_present" in html
    assert "real_llm_disabled" in html
    assert "real_cloud_disabled" in html
    assert "real_sandbox_disabled" in html
    assert "auto_publish_disabled" in html
    assert "contestant_code_execution_disabled" in html
    assert "unknown_shell_execution_disabled" in html
    assert "realLlmCalled=false" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublish=false" in html
    assert "secretVisibleInFrontend=false" in html
    assert "disabled" in html


def test_exam_generate_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/exam-generate.html").read_text(encoding="utf-8")
    script = (ROOT / "frontend/exam-generate-data.js").read_text(encoding="utf-8")
    ui_manifest = load_json("frontend/ui.manifest.json")
    pages = {page["route"]: page for page in ui_manifest["pages"]}

    assert "LOCAL_CORE_MVP" in html
    assert "真实 LLM：通过后端/CLI 显式接入" in html
    assert "标准答案选手端：隐藏" in html
    assert "真实沙箱：禁用" in html
    assert "自动发布：禁用" in html
    assert "POST /api/exams/generate-from-lab" in html
    assert "WAITING_REVIEW" in html
    assert "answerVisibleToCandidate=false" in html
    assert "Local Backend API" in html
    assert "LocalCoreGenerationWorkspace" in read_text("frontend/README.md")
    assert "ExamGenerationCloseLoopAction" in html
    assert ".section-head > *" in html
    assert "overflow-wrap: anywhere" in html
    assert "white-space: normal" in html
    assert "exam-generate-next-summary" in html
    assert "exam-generate-next-status" in html
    assert "exam-generate-next-task" in html
    assert "exam-generate-next-exam-artifact" in html
    assert "exam-generate-next-grading-artifact" in html
    assert "exam-generate-next-candidate-safety" in html
    assert "exam-generate-review-center-link" in html
    assert "exam-generate-review-page-link" in html
    assert "exam-generate-grading-review-link" in html
    assert "exam-generate-exam-import-preview-link" in html
    assert "exam-generate-grading-import-preview-link" in html
    assert "exam-review.html" in html
    assert "grading-review.html" in html
    assert "agent-entities.html?entityKind=exam" in html
    assert "agent-entities.html?entityKind=grading" in html
    assert "answersHidden=true" in html
    assert 'id="exam-generate-lab-id"' in html
    assert 'id="exam-generate-lab-dsl-path"' in html
    assert 'id="exam-generate-provider-mode"' in html
    assert 'id="exam-generate-explicit-real-call"' in html
    assert 'id="exam-generate-run"' in html
    assert '<script src="exam-generate-data.js"></script>' in html
    assert "[REDACTED_FOR_CANDIDATE]" not in html
    assert "sandboxExecuted=false" in html
    assert 'generatePath: "/api/exams/generate-from-lab"' in script
    assert 'method: "POST"' in script
    assert "updateCloseLoopAction" in script
    assert "withQuery" in script
    assert "queryParam" in script
    assert "configureLocalContextFromQuery" in script
    assert 'configureLocalContextFromQuery();\n    updateCloseLoopAction({' in script
    assert 'status: "NOT_CREATED"' in script
    assert "withLocalContext" in script
    assert "requestBodyWithLocalContext" in script
    assert "nextParams.coreDbPath = state.coreDbPath" in script
    assert "nextParams.gradingDbPath = state.gradingDbPath" in script
    assert "nextParams.agentReport = state.agentReport" in script
    assert "providerRequestOptions" in script
    assert "providerMode: mode" in script
    assert "labDslPath" in script
    assert "Object.assign({ labId, labDslPath }, providerRequestOptions())" in script
    assert "const labId = input ? input.value.trim() : state.defaultLabId" in script
    assert "exam-generate-review-center-link" in script
    assert "exam-generate-grading-review-link" in script
    assert "exam-generate-grading-import-preview-link" in script
    assert "agent-entities.html" in script
    assert "WAITING_REVIEW" in script
    assert "answerVisibleToCandidate: false" in script
    assert "gradingRefVisibleToCandidate: false" in script
    assert "[REDACTED_FOR_CANDIDATE]" not in script
    assert 'answer: "[REDACTED_FOR_CANDIDATE]"' not in script
    assert 'gradingRef: "[TEACHER_ONLY]"' not in script
    assert "autoPublishAllowed: false" in script
    assert "realPublish: false" in script
    assert "sandboxExecuted: false" in script
    assert "POST /api/ai-tasks/{id}/approve" not in script
    assert "POST /api/ai-tasks/{id}/reject" not in script
    assert "apiKey" not in script
    assert "disabled" in html
    assert "ExamGenerationCloseLoopAction" in read_text("frontend/README.md")
    assert "ExamGenerationCloseLoopAction" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")
    assert "前端不直接调用真实 LLM" in read_text("frontend/README.md")
    assert "LocalCoreGenerationWorkspace" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")
    assert "页面初始化和生成成功后" in read_text("frontend/README.md")
    assert "页面初始化和 `POST /api/exams/generate-from-lab` 成功后" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")
    assert "LocalCoreGenerationWorkspace" in pages["/exams/generate"]["components"]
    assert "LocalCoreGenerationWorkspace" in pages["/exams/generate"]["dataSources"]
    assert "frontendDirectRealLlmCall=false" in pages["/exams/generate"]["dataSources"]
    assert "realLlmResultCanEnterViaCliOrBackend=true" in pages["/exams/generate"]["dataSources"]
    assert pages["/exams/generate"]["safety"]["localCoreGenerationWorkspace"] is True
    assert pages["/exams/generate"]["safety"]["frontendDirectRealLlmCall"] is False
    assert pages["/exams/generate"]["safety"]["realLlmResultCanEnterViaCliOrBackend"] is True
    assert "ExamGenerationCloseLoopAction.initialContextLinks" in pages["/exams/generate"]["dataSources"]


def test_exams_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/exams.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型：禁用" in html
    assert "真实沙箱：禁用" in html
    assert "标准答案选手端：隐藏" in html
    assert "自动发布：禁用" in html
    assert "真实发布：禁用" in html
    assert "GET /api/exams" in html
    assert "POST /api/exams/generate-from-lab" in html
    assert "/exams/generate" in html
    assert "ExamDslPreview" in html
    assert "Grading DSL" in html
    assert "WAITING_REVIEW" in html
    assert "answerVisibleToCandidate=false" in html
    assert "standardAnswerRevealToCandidate=false" in html
    assert "[REDACTED_FOR_CANDIDATE]" in html
    assert "realSandboxRunEnabled=false" in html
    assert "realPublish=false" in html
    assert "disabled" in html


def test_exam_review_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/exam-review.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型：禁用" in html
    assert "标准答案选手端：隐藏" in html
    assert "真实沙箱：禁用" in html
    assert "自动发布：禁用" in html
    assert "真实发布：禁用" in html
    assert "批量状态变更：禁用" in html
    assert "GET /api/review-tasks/{id}" in html
    assert "POST /api/ai-tasks/{id}/approve" in html
    assert "POST /api/ai-tasks/{id}/reject" in html
    assert "ExamDslPreview" in html
    assert "Grading DSL" in html
    assert "AiTaskTimeline" in html
    assert "qualitySignals：只读" in html
    assert "candidateSafeExamPreview.answersRemoved=true" in html
    assert "questionGradingRefCoverage" in html
    assert "qualitySignals.coverage.questionGradingRefCoverage.status=MATCHED" in html
    assert "qualitySignals.coverage.scoreCoverage.status=MATCHED" in html
    assert "assessmentPlanAlignedWithChecks" in html
    assert "scoreCoverage.matched" in html
    assert "explainability.status" in html
    assert "MOCK_EVIDENCE_NOT_COLLECTED" in html
    assert "WAITING_REVIEW" in html
    assert "answerVisibleToCandidate=false" in html
    assert "standardAnswerRevealToCandidate=false" in html
    assert "[REDACTED_FOR_CANDIDATE]" in html
    assert "rejectRequiresReason=true" in html
    assert "auditTrailRequired=true" in html
    assert "autoPublishAllowed=false" in html
    assert "realPublishAllowed=false" in html
    assert "realSandboxRunEnabled=false" in html
    assert "disabled" in html


def test_environment_management_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/environments.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实云资源：禁用" in html
    assert "真实 VM / Notebook：禁用" in html
    assert "销毁真实资源：禁用" in html
    assert "GET /api/environments" in html
    assert "GET /api/audit-events" in html
    assert "POST /api/environments/vm" in html
    assert "POST /api/environments/notebook" in html
    assert "realCloudResourceCreated=false" in html
    assert "realCloudResourceChanged=false" in html
    assert "provider=mock" in html
    assert "disabled" in html


def test_skills_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/skills.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实智能体：禁用" in html
    assert "真实大模型：禁用" in html
    assert "自动发布：禁用" in html
    assert "Prompt 散落：禁用" in html
    assert "skills/manifest.json" in html
    assert "prompts/manifest.json" in html
    assert "ai-workflows/workflow.manifest.json" in html
    assert "businessCodeMayEmbedPrompts=false" in html
    assert "outputMustBeDsl=true" in html
    assert "realAgentStarted=false" in html
    assert "realLlmCalled=false" in html
    assert "WAITING_REVIEW" in html
    assert "disabled" in html


def test_provider_settings_static_prototype_has_phase1_safety_text():
    html = (ROOT / "frontend/provider-settings.html").read_text(encoding="utf-8")

    assert "MOCK_ONLY" in html
    assert "真实大模型：禁用" in html
    assert "真实 Provider：禁用" in html
    assert "网络访问：禁用" in html
    assert "密钥展示：禁用" in html
    assert "GET /api/providers" in html
    assert "GET /api/providers/mock/health" in html
    assert "POST /api/providers/mock/generate" in html
    assert "MockProvider" in html
    assert "ENABLE_REAL_LLM=false" in html
    assert "OPENAI_API_KEY" in html
    assert "ANTHROPIC_API_KEY" in html
    assert "[HIDDEN]" in html
    assert "secretVisibleInFrontend=false" in html
    assert "realLlmCalled" in html
    assert "WAITING_REVIEW" in html
    assert "disabled" in html


def test_ai_tasks_static_page_has_readonly_api_loader():
    html = read_text("frontend/ai-tasks.html")
    script = read_text("frontend/ai-tasks-data.js")

    assert 'id="ai-task-api-status"' in html
    assert 'id="ai-task-list"' in html
    assert 'id="ai-task-selected-json"' in html
    assert '<script src="ai-tasks-data.js"></script>' in html
    assert "GET /api/ai-tasks + GET /api/review-task-summary" in script
    assert "GET /api/backend/core-tasks + GET /api/review-task-summary" in script
    assert "requestedTaskId" in script
    assert "queryParam(\"taskId\") || queryParam(\"id\")" in script
    assert "fallbackWorkspaceTask" in script
    assert "fallbackTaskType" in script
    assert "updateTaskExecutionWorkspace(fallbackWorkspaceTask())" in script
    assert "task.id === state.selectedTaskId" in script
    assert "TaskExecutionWorkspace" in html
    assert "updateTaskExecutionWorkspace" in script
    assert "entityKindFromTask" in script
    assert "taskReviewHref" in script
    assert "taskGradingReportHref" in script
    assert "loadLatestGradingRecord" in script
    assert "gradingRecordLoadStateByTaskId" in script
    assert "check_grading_record_api" in script
    assert "supportsGradingWorkspace" in script
    assert 'type.indexOf("EXAM") >= 0' in script
    assert "if (gradingReportPath)" in script
    assert "gradingRecordsPath" in script
    assert "latest.reportPath" in script
    assert "taskImportPreviewHref" in script
    assert "nextTaskWorkspaceAction" in script
    assert "task-workspace-review-link" in script
    assert "task-workspace-grading-report-link" in script
    assert "task-workspace-grading-workspace-link" in script
    assert "task-workspace-import-preview-link" in script
    assert "method=GET only" in script
    assert "coreDbPath" in script
    assert "gradingDbPath" in script
    assert "agentReport" in script
    assert 'state.summaryPath = withQuery("/api/review-task-summary"' in script
    assert "agentReportTasks(summary)" in script
    assert "AGENT_REPORT_REAL_LLM_ARTIFACTS" in script
    assert "AGENT_REPORT_READONLY_LOADED" in script
    assert "function reviewDetailPath(taskId)" in script
    assert "function taskFromDetailPayload(payload)" in script
    assert "safeFetchJson(taskDetailPath(task))" in script
    assert "payload.data.reviewDetail.task" in script
    assert "realDemoQueueItem" in script
    assert "function withGradingDbPath(path)" in read_text("frontend/review-center-data.js")
    assert "return withAgentReport(withGradingDbPath(withCoreDbPath(" in read_text("frontend/review-center-data.js")
    assert "taskReviewHref(task)" in script
    assert "review-center.html" in script
    assert "grading-report.html" in script
    assert "agent-entities.html" in script
    assert "/api/backend/core-tasks" in script
    assert "BACKEND_CORE_TASKS_READONLY_LOADED" in script
    assert "/api/ai-tasks?status=WAITING_REVIEW" in script
    assert "API_READONLY_LOADED" in script
    assert "API_READONLY_LOADED_WITH_TASK_NOT_FOUND" in script
    assert "taskNotFound=true" in script
    assert "STATIC_HTML_FALLBACK" in script
    assert "method: \"GET\"" in script
    assert "method: \"POST\"" not in script
    assert "autoPublishAllowed: false" in script
    assert "batchStateChangeAllowed: false" in script
    assert "secretVisibleInFrontend: false" in script
    manifest = load_json("frontend/ui.manifest.json")
    pages = {page["route"]: page for page in manifest["pages"]}
    assert "AiTaskExecutionWorkspace" in pages["/ai-tasks"]["components"]
    assert "AiTaskExecutionWorkspace.staticFallbackContextLinks" in pages["/ai-tasks"]["dataSources"]
    assert "AiTaskExecutionWorkspace.noHorizontalOverflow" in pages["/ai-tasks"]["dataSources"]
    assert "query: gradingDbPath" in pages["/ai-tasks"]["dataSources"]
    assert "query: agentReport" in pages["/ai-tasks"]["dataSources"]
    assert (
        "review-center.html?taskId={taskId}&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in pages["/ai-tasks"]["dataSources"]
    )
    assert (
        "GET /api/grading/records?taskId={taskId}&dbPath={path}.latest.reportPath"
        in pages["/ai-tasks"]["dataSources"]
    )
    assert "requested taskId not found -> visible fallback selected task" in pages["/ai-tasks"]["dataSources"]
    assert (
        "grading-report.html?taskId={taskId}&file={reportPath}&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in pages["/ai-tasks"]["dataSources"]
    )
    assert (
        "agent-entities.html?sourceTaskId={taskId}&entityKind={kind}&coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in pages["/ai-tasks"]["dataSources"]
    )
    assert (
        "GET /api/review-task-summary?limit=5&detailMode=light&agentReport={workflowReport}"
        in pages["/ai-tasks"]["dataSources"]
    )
    assert (
        "GET /api/review-tasks/{id}?coreDbPath={path}&gradingDbPath={path}&agentReport={workflowReport}"
        in pages["/ai-tasks"]["dataSources"]
    )
    assert "realDemoReviewQueue.items[] -> synthetic read-only AI Task cards" in pages["/ai-tasks"]["dataSources"]
    assert "GET /api/ai-tasks/{id}.taskExecutionWorkspace" in pages["/ai-tasks"]["dataSources"]
    assert "GET /api/backend/core-tasks/{id}.taskExecutionWorkspace" in pages["/ai-tasks"]["dataSources"]
    assert "TaskExecutionWorkspace" in read_text("frontend/README.md")
    assert "TaskExecutionWorkspace" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")
    assert "静态 fallback" in read_text("frontend/README.md")
    assert "静态 fallback" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")
    assert "避免 1280px 宽度下横向滚动" in read_text("docs/24_PROJECT_PROGRESS_MAP.md")


def test_local_review_and_import_pages_forward_core_db_context():
    review_action_script = read_text("frontend/review-action-data.js")
    platform_html = read_text("frontend/agent-entities.html")

    assert "function resolveCoreDbPath()" in review_action_script
    assert "coreDbPath: resolveCoreDbPath() || undefined" in review_action_script
    assert "state.coreDbPath = resolveCoreDbPath();" in review_action_script
    assert "{ coreDbPath: state.coreDbPath }" in platform_html
    assert '"&coreDbPath={path}"' in platform_html


def test_agent_entity_page_wraps_long_local_context_on_mobile():
    html = read_text("frontend/agent-entities.html")

    assert ".section-head > * {\n      min-width: 0;" in html
    assert ".section-head p {\n      overflow-wrap: anywhere;" in html
    assert "input,\n    select {\n      width: 100%;\n      min-width: 0;\n      max-width: 100%;\n      overflow: hidden;" in html
    assert ".content-grid > * {\n      min-width: 0;" in html
    assert ".entity-list,\n    .detail-stack {\n      display: grid;\n      gap: 12px;\n      min-width: 0;" in html
    assert ".detail-stack > *,\n    .detail-card > *,\n    .pill-row > * {\n      min-width: 0;\n      max-width: 100%;" in html
    assert ".detail-card {\n      display: grid;\n      gap: 10px;\n      padding: 12px;\n      overflow-x: hidden;" in html


def test_review_detail_pages_wrap_long_task_identifiers():
    for page in ["lab-review.html", "exam-review.html", "grading-review.html", "ppt-review.html"]:
        html = read_text("frontend/" + page)
        assert ".metric strong,\n    .card strong" in html
        assert "overflow-wrap: anywhere;" in html
        assert ".stack {\n      display: grid;\n      gap: 12px;\n      min-width: 0;" in html
        assert ".content-grid > * {\n      min-width: 0;" in html
        assert ".card {\n      display: grid;\n      gap: 10px;\n      padding: 12px;\n      min-width: 0;" in html
