(function () {
  "use strict";

  var state = {
    gradingReportPath: "/api/grading/report",
    gradingRecordsPath: "/api/grading/records",
    detailPathTemplate: "/api/review-tasks/{id}",
    defaultTaskId: "task_grading_demo"
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    var node = byId(id);
    if (node) {
      node.textContent = String(value);
    }
  }

  function boolText(value) {
    return value === true ? "true" : "false";
  }

  function numberText(value) {
    return typeof value === "number" ? String(value) : String(value || 0);
  }

  function firstStatus(items, fallback) {
    if (!Array.isArray(items) || items.length === 0) {
      return fallback;
    }
    for (var index = 0; index < items.length; index += 1) {
      var item = items[index] || {};
      var evidence = item.mockEvidence || item.evidence || {};
      if (evidence.status) {
        return evidence.status;
      }
    }
    return fallback;
  }

  function escapeText(value) {
    return String(value === null || typeof value === "undefined" ? "" : value);
  }

  function resolveTaskId() {
    var params = new URLSearchParams(window.location.search || "");
    return params.get("taskId") || params.get("id") || state.defaultTaskId;
  }

  function resolveReportFile() {
    var params = new URLSearchParams(window.location.search || "");
    return params.get("file") || params.get("reportFile") || "";
  }

  function resolveGradingDbPath() {
    var params = new URLSearchParams(window.location.search || "");
    return params.get("gradingDbPath") || params.get("dbPath") || "";
  }

  function resolveCoreDbPath() {
    var params = new URLSearchParams(window.location.search || "");
    return params.get("coreDbPath") || "";
  }

  function resolveAgentReport() {
    var params = new URLSearchParams(window.location.search || "");
    return params.get("agentReport") || "";
  }

  function appendReviewContext(params) {
    var coreDbPath = resolveCoreDbPath();
    var gradingDbPath = resolveGradingDbPath();
    var agentReport = resolveAgentReport();
    if (coreDbPath) {
      params.set("coreDbPath", coreDbPath);
    }
    if (gradingDbPath) {
      params.set("gradingDbPath", gradingDbPath);
    }
    if (agentReport) {
      params.set("agentReport", agentReport);
    }
    return params;
  }

  function gradingWorkspaceHref(taskId) {
    var params = new URLSearchParams();
    if (taskId) {
      params.set("taskId", taskId);
    }
    appendReviewContext(params);
    var query = params.toString();
    return query ? "grading-workspace.html?" + query : "grading-workspace.html";
  }

  function setGradingWorkspaceLink(taskId) {
    var link = byId("grading-report-workspace-link");
    if (!link) {
      return;
    }
    link.href = gradingWorkspaceHref(taskId || resolveTaskId());
    link.textContent = "打开评分工作台";
  }

  function detailPath(taskId) {
    var path = state.detailPathTemplate.replace("{id}", encodeURIComponent(taskId));
    var params = appendReviewContext(new URLSearchParams());
    var query = params.toString();
    return query ? path + "?" + query : path;
  }

  function gradingReportPath(reportFile, taskId) {
    var params = new URLSearchParams();
    params.set("file", reportFile);
    params.set("taskId", taskId);
    return state.gradingReportPath + "?" + params.toString();
  }

  function gradingRecordsPath(taskId) {
    var params = new URLSearchParams();
    params.set("taskId", taskId);
    var dbPath = resolveGradingDbPath();
    if (dbPath) {
      params.set("dbPath", dbPath);
    }
    return state.gradingRecordsPath + "?" + params.toString();
  }

  function gradingResultPreviewPath(reportFile, taskId) {
    var params = new URLSearchParams();
    params.set("report", reportFile);
    if (shouldSendAuxiliaryTaskId(taskId)) {
      params.set("taskId", taskId);
    }
    params.set("maxItems", "6");
    return "/api/grading/result-preview?" + params.toString();
  }

  function gradingEvidenceReadinessPath(reportFile, taskId) {
    var params = new URLSearchParams();
    params.append("report", reportFile);
    if (shouldSendAuxiliaryTaskId(taskId)) {
      params.set("taskId", taskId);
    }
    return "/api/grading/evidence-readiness?" + params.toString();
  }

  function shouldSendAuxiliaryTaskId(taskId) {
    var value = String(taskId || "");
    return value.indexOf("task_") === 0 || value.indexOf("real_demo_") === 0;
  }

  function reviewDecisionFromNextAction(nextAction) {
    var actionId = nextAction && nextAction.id ? nextAction.id : "";
    if (actionId === "review_score_and_record_decision_note") {
      return "approve-ready";
    }
    if (actionId === "fix_submission_or_grading_static_evidence") {
      return "needs-revision";
    }
    return "needs-evidence";
  }

  function reviewCenterDecisionHref(taskId, nextAction) {
    var params = new URLSearchParams();
    params.set("taskId", taskId || "task_grading_demo");
    params.set("decision", reviewDecisionFromNextAction(nextAction));
    params.set("source", "grading-report-next-core-action");
    if (nextAction && nextAction.id) {
      params.set("nextCoreAction", nextAction.id);
    }
    appendReviewContext(params);
    return "review-center.html?" + params.toString();
  }

  function setReviewerWorkspaceReviewLink(taskId, nextAction, source) {
    var link = byId("reviewer-workspace-review-center-link");
    if (!link) {
      return;
    }
    var href = reviewCenterDecisionHref(taskId || resolveTaskId(), nextAction || {});
    if (source) {
      var parts = href.split("?");
      var params = new URLSearchParams(parts[1] || "");
      params.set("source", source);
      href = parts[0] + "?" + params.toString();
    }
    link.href = href;
    link.textContent = "打开审核中心记录结论";
  }

  function setEvidenceAutoReviewCenterLink(taskId, nextAction) {
    var link = byId("evidence-auto-review-center-link");
    if (!link) {
      return;
    }
    link.href = reviewCenterDecisionHref(taskId || resolveTaskId(), nextAction || {});
    link.textContent = "打开审核中心记录结论";
  }

  function setReviewerWorkspaceSummary(sourceLabel, detail) {
    setText(
      "reviewer-workspace-summary",
      "source=" + sourceLabel
        + " · " + (detail || "readonly=true")
        + " · coreDbPath=" + (resolveCoreDbPath() || "none")
        + " · gradingDbPath=" + (resolveGradingDbPath() || "none")
        + " · agentReport=" + (resolveAgentReport() || "none")
        + " · noExecutionFromPage=true"
    );
  }

  function updateReviewerWorkspaceFromReport(reportData, taskId, sourceLabel) {
    var report = reportData && reportData.report ? reportData.report : {};
    var detail = reportData && reportData.reportDetail ? reportData.reportDetail : {};
    var reportSummary = report.summary || {};
    var scorePreview = report.scorePreview || {};
    var checkSummary = report.checkSummary || {};
    var checks = Array.isArray(report.checks) ? report.checks : [];
    var totalScore = report.totalScore || report.scoreTotal || report.maxScore || 0;
    var earnedScore = report.earnedScore || report.score || 0;
    var passed = checkSummary.passed || checks.filter(function (check) {
      return check.passed === true || String(check.status || "").toUpperCase() === "PASSED";
    }).length;
    var checkTotal = checkSummary.total || checkSummary.checkTotal || checks.length || 0;
    var detailSafety = detail.safety || {};
    setReviewerWorkspaceSummary(
      sourceLabel,
      "taskId=" + (taskId || "none")
        + " · reportMode=" + (report.mode || "GRADING_REPORT")
        + " · reportPath=" + (reportData.reportPath || resolveReportFile() || "none")
    );
    setText("reviewer-workspace-score", earnedScore + " / " + totalScore);
    setText("reviewer-workspace-evidence", "checksPassed=" + passed + "/" + checkTotal);
    setText(
      "reviewer-workspace-safety",
      "noExecutionFromPage=true"
        + " · sandboxExecuted=" + boolText((report.sandboxExecuted || detailSafety.sandboxExecuted) === true)
        + " · contestantCodeExecuted=" + boolText((report.contestantCodeExecuted || detailSafety.contestantCodeExecuted) === true)
        + " · autoApproveAllowed=false · realPublishAllowed=false"
    );
    setReviewerWorkspaceReviewLink(taskId, report.nextCoreAction || {}, "grading-report-reviewer-workspace");
  }

  function updateReviewerWorkspaceFromAutoEvidence(report) {
    var summary = report && report.summary ? report.summary : {};
    var scorePreview = report && report.scorePreview ? report.scorePreview : {};
    var matrix = report && report.executionMatrix ? report.executionMatrix : {};
    var matrixSummary = matrix.summary || {};
    var nextAction = report && report.nextCoreAction ? report.nextCoreAction : {};
    setText(
      "reviewer-workspace-evidence",
      "evidenceReady=" + (matrixSummary.evidenceReadyTotal || summary.evidenceReadyTotal || 0)
        + "/" + (matrixSummary.checkTotal || summary.checkTotal || 0)
    );
    if (typeof scorePreview.earnedScore !== "undefined" || typeof summary.earnedScore !== "undefined") {
      setText(
        "reviewer-workspace-score",
        (scorePreview.earnedScore || summary.earnedScore || 0)
          + " / "
          + (scorePreview.totalScore || summary.totalScore || 0)
      );
    }
    setText(
      "reviewer-workspace-next-action",
      "nextAction=" + (nextAction.id || "record_review_decision_note")
        + " · readyForDecisionNote=" + boolText(scorePreview.readyForDecisionNote === true)
    );
    setReviewerWorkspaceReviewLink(resolveTaskId(), nextAction, "grading-report-reviewer-workspace");
  }

  function renderReviewerSafetySummary(reviewerSummary) {
    var data = reviewerSummary && typeof reviewerSummary === "object" ? reviewerSummary : null;
    if (!data) {
      return false;
    }
    var score = data.score || {};
    var evidence = data.evidence || {};
    var safety = data.safety || {};
    var nextAction = data.nextCoreAction || {};
    var blockingReasons = Array.isArray(data.blockingReasons) ? data.blockingReasons : [];
    var requiredChecks = Array.isArray(data.requiredManualChecks) ? data.requiredManualChecks : [];
    setText("reviewer-workspace-state", data.status || "NEEDS_HUMAN_REVIEW");
    setText(
      "reviewer-workspace-score",
      (score.earnedScore || 0) + " / " + (score.totalScore || 0)
        + " · covered=" + (score.coveredScore || 0)
    );
    setText(
      "reviewer-workspace-evidence",
      "evidenceReady=" + (evidence.evidenceReadyTotal || 0)
        + "/" + (evidence.checkTotal || 0)
        + " · controlledIncluded=" + boolText(evidence.controlledCommandIncluded === true)
    );
    setText(
      "reviewer-workspace-next-action",
      "nextAction=" + (nextAction.id || "record_review_decision_note")
        + " · readyForApproveReady=" + boolText(data.readyForApproveReadyDecision === true)
    );
    setText(
      "reviewer-workspace-safety",
      "noExecutionFromPage=true"
        + " · controlledSandboxExecution=" + boolText(safety.contestantCodeExecutedInControlledSandbox === true)
        + " · hostExecutionAllowed=" + boolText(safety.hostExecutionAllowed === true)
        + " · autoApproveAllowed=false · realPublishAllowed=false"
    );
    setText(
      "reviewer-safety-summary-status",
      "source=GET /api/grading/report?file={file}.report.reviewerSafetySummary"
        + " · status=" + (data.status || "UNKNOWN")
        + " · readyForApproveReadyDecision=" + boolText(data.readyForApproveReadyDecision === true)
        + " · blockingReasonTotal=" + blockingReasons.length
    );
    setReviewerWorkspaceReviewLink(resolveTaskId(), nextAction, "grading-report-reviewer-safety-summary");

    var list = byId("reviewer-safety-summary-list");
    if (!list) {
      return true;
    }
    list.innerHTML = "";
    var statusCard = document.createElement("div");
    statusCard.className = "callout";
    var statusTitle = document.createElement("h3");
    statusTitle.textContent = "ReviewerSafetySummary · " + (data.status || "UNKNOWN");
    var statusBody = document.createElement("p");
    statusBody.textContent = "readyForHumanReview=" + boolText(data.readyForHumanReview === true)
      + " · readyForHumanScoreReview=" + boolText(data.readyForHumanScoreReview === true)
      + " · readyForApproveReadyDecision=" + boolText(data.readyForApproveReadyDecision === true);
    var evidenceBody = document.createElement("p");
    evidenceBody.textContent = "evidenceReady=" + (evidence.evidenceReadyTotal || 0)
      + "/" + (evidence.checkTotal || 0)
      + " · missingEvidenceTotal=" + (evidence.missingEvidenceTotal || 0)
      + " · controlledCommandMissingTotal=" + (evidence.controlledCommandMissingTotal || 0);
    statusCard.appendChild(statusTitle);
    statusCard.appendChild(statusBody);
    statusCard.appendChild(evidenceBody);
    list.appendChild(statusCard);

    if (blockingReasons.length) {
      blockingReasons.slice(0, 4).forEach(function (reason) {
        var card = document.createElement("div");
        card.className = "callout";
        var title = document.createElement("h3");
        title.textContent = "blockingReason · " + (reason.id || "manual_review_required");
        var body = document.createElement("p");
        body.textContent = "severity=" + (reason.severity || "info")
          + " · nextCoreAction=" + (reason.nextCoreActionId || (nextAction.id || "none"));
        var message = document.createElement("p");
        message.textContent = reason.message || "Review the grading evidence before recording a decision note.";
        card.appendChild(title);
        card.appendChild(body);
        card.appendChild(message);
        list.appendChild(card);
      });
    } else {
      var clearCard = document.createElement("div");
      clearCard.className = "callout";
      clearCard.innerHTML = "<h3>blockingReason · none</h3><p>当前摘要没有阻断原因，但仍需人工记录审核结论。</p>";
      list.appendChild(clearCard);
    }

    requiredChecks.slice(0, 4).forEach(function (item) {
      var card = document.createElement("div");
      card.className = "callout";
      var title = document.createElement("h3");
      title.textContent = "manualCheck · " + (item.id || "manual_review");
      var body = document.createElement("p");
      body.textContent = "status=" + (item.status || "NEEDS_REVIEW")
        + " · description=" + (item.description || "Review score and evidence.");
      card.appendChild(title);
      card.appendChild(body);
      list.appendChild(card);
    });
    return true;
  }

  function updateReviewerWorkspaceFromEvidenceReadiness(readiness) {
    var summary = readiness && readiness.summary ? readiness.summary : {};
    var ready = summary.readyForApprovalRecommendation === true;
    setText(
      "reviewer-workspace-evidence",
      "evidenceReady=" + (summary.evidenceReadyTotal || 0)
        + "/" + ((summary.evidenceReadyTotal || 0) + (summary.missingEvidenceTotal || 0))
        + " · missing=" + (summary.missingEvidenceTotal || 0)
    );
    setText(
      "reviewer-workspace-next-action",
      "nextAction=" + (ready
        ? "record_approve_ready_decision_note"
        : "collect_or_review_additional_grading_evidence")
    );
    setReviewerWorkspaceReviewLink(
      resolveTaskId(),
      { id: ready ? "review_score_and_record_decision_note" : "collect_or_review_additional_grading_evidence" },
      "grading-report-reviewer-workspace"
    );
    setEvidenceAutoReviewCenterLink(
      resolveTaskId(),
      { id: ready ? "review_score_and_record_decision_note" : "collect_or_review_additional_grading_evidence" }
    );
  }

  function updateReviewerWorkspaceFromResultPreview(preview) {
    var score = preview && preview.score ? preview.score : {};
    var safety = preview && preview.safety ? preview.safety : {};
    if (typeof score.earnedScore !== "undefined" || typeof score.totalScore !== "undefined") {
      setText("reviewer-workspace-score", (score.earnedScore || 0) + " / " + (score.totalScore || 0));
    }
    setText(
      "reviewer-workspace-candidate-safety",
      "candidateSafe=" + boolText(preview && preview.candidateSafe !== false)
        + " · answerVisibleToCandidate=" + boolText(safety.answerVisibleToCandidate === true)
        + " · gradingRefVisibleToCandidate=" + boolText(safety.gradingRefVisibleToCandidate === true)
    );
  }

  function updateReviewerWorkspaceFromDecisionNotes(notes) {
    var outcome = reviewDecisionOutcome(notes || {});
    setText("reviewer-workspace-state", outcome.status);
    setText(
      "reviewer-workspace-decision",
      "latestDecision=" + outcome.latestDecision
        + " · noteRecorded=" + boolText(outcome.reviewDecisionNoteRecorded)
    );
    setText("reviewer-workspace-next-action", "nextAction=" + outcome.nextRequiredAction);
  }

  function updateReviewerWorkspaceFromGradingRecord(integration) {
    var data = integration || {};
    var recordTotal = typeof data.total === "undefined" ? 0 : data.total;
    var ready = data.readyForAgentReview === true;
    var nextActionId = ready
      ? "review_score_and_record_decision_note"
      : (data.nextRequiredAction || "review_latest_grading_record_for_platform_review");
    setText(
      "reviewer-workspace-record",
      (data.state || "NO_GRADING_RECORD")
        + " · latestDecision=" + (data.latestDecision || "none")
        + " · recordTotal=" + recordTotal
        + " · readyForAgentReview=" + boolText(ready)
    );
    setText(
      "reviewer-workspace-next-action",
      "nextAction=" + nextActionId
        + " · agentApiRequired=false"
    );
    if (recordTotal > 0) {
      setText(
        "reviewer-workspace-state",
        ready ? "GRADING_RECORD_APPROVE_READY_RECORDED" : "WAITING_GRADING_RECORD_REVIEW"
      );
    }
    setReviewerWorkspaceReviewLink(resolveTaskId(), { id: nextActionId }, "grading-report-reviewer-workspace");
  }

  function renderReportSummary(reportData, taskId, sourceLabel) {
    var report = reportData && reportData.report ? reportData.report : {};
    var detail = reportData && reportData.reportDetail ? reportData.reportDetail : {};
    var reportSummary = report.summary || {};
    var scorePreview = report.scorePreview || {};
    var checkSummary = report.checkSummary || {};
    var checks = Array.isArray(report.checks) ? report.checks : [];
    var sandboxPolicy = detail.sandboxPolicy || report.sandboxPolicy || {};
    var explainability = report.explainability || {};
    var detailSafety = detail.safety || {};
    var totalScore = report.totalScore || report.scoreTotal || report.maxScore || reportSummary.totalScore || scorePreview.totalScore || 0;
    var earnedScore = report.earnedScore || report.score || reportSummary.earnedScore || scorePreview.earnedScore || 0;
    var executed = checkSummary.executed || report.executed || reportSummary.executed || scorePreview.evidenceReadyTotal || 0;
    var passed = checkSummary.passed || reportSummary.passedCheckTotal || scorePreview.passedCheckTotal || checks.filter(function (check) {
      return check.passed === true || String(check.status || "").toUpperCase() === "PASSED";
    }).length;
    var checkTotal = checkSummary.total || checkSummary.checkTotal || reportSummary.checkTotal || scorePreview.checkTotal || checks.length;
    var requiredLimits = sandboxPolicy.requiredLimits || [];
    var requiredLimitText = Array.isArray(requiredLimits) ? requiredLimits.join("/") : requiredLimits || "timeout/cpu/memory/process";

    setText(
      "grading-report-api-state",
      "API_READONLY_LOADED · source=" + sourceLabel + " · taskId=" + (taskId || "none") + " · noExecutionFromPage=true"
    );
    setText("grading-report-total-score", numberText(totalScore));
    setText("grading-report-earned-score", numberText(earnedScore));
    setText("grading-report-check-summary", numberText(passed) + " / " + numberText(checkTotal));
    setText("grading-report-executed-total", numberText(executed));
    setText("grading-report-executor-boundary", sandboxPolicy.executorBoundary || "SandboxExecutor");
    setText("grading-report-host-execution", boolText(sandboxPolicy.hostExecutionAllowed === true));
    setText("grading-report-network-access", sandboxPolicy.networkAccess || (report.networkEnabled === true ? "enabled" : "disabled_by_default"));
    setText("grading-report-required-limits", requiredLimitText);
    setText("grading-report-explainability-status", explainability.status || "EXPLAINABLE_MOCK_PLAN");
    setText("grading-report-each-check-plan", boolText(explainability.eachCheckHasPlan !== false));
    setText("grading-report-each-check-input", boolText(explainability.eachCheckHasInputSummary !== false));
    setText("grading-report-assessment-aligned", boolText(explainability.assessmentPlanAlignedWithChecks !== false));
    setText("grading-report-real-evidence-required", boolText(explainability.realSandboxEvidenceRequired === true));
    setText("grading-report-path", reportData.reportPath || resolveReportFile() || "none");
    setText("grading-report-real-pytest", boolText(report.runRealPytestEnabled === true));
    setText("grading-report-mock-evidence", firstStatus(detail.checkPlans || checks, "MOCK_EVIDENCE_NOT_COLLECTED"));
    setText(
      "grading-report-blocked-actions",
      [
        "sandboxExecuted=" + boolText((report.sandboxExecuted || detailSafety.sandboxExecuted) === true),
        "contestantCodeExecuted=" + boolText((report.contestantCodeExecuted || detailSafety.contestantCodeExecuted) === true),
        "commandExecuted=" + boolText((report.commandExecuted || detailSafety.commandExecuted) === true),
        "realPublishAllowed=false"
      ].join(" · ")
    );
    setGradingWorkspaceLink(taskId);
    updateReviewerWorkspaceFromReport(reportData, taskId, sourceLabel);
  }

  function evidenceReportMode(item) {
    var source = item && item.evidenceSource ? item.evidenceSource : {};
    return source.reportMode || item.reportMode || "UNKNOWN_REPORT_MODE";
  }

  function evidenceReportPath(item) {
    var source = item && item.evidenceSource ? item.evidenceSource : {};
    return source.reportPath || source.path || item.reportPath || "none";
  }

  function renderRows(items) {
    var body = byId("merged-evidence-source-chain-body");
    if (!body || !Array.isArray(items) || items.length === 0) {
      return;
    }
    body.innerHTML = "";
    items.slice(0, 12).forEach(function (item) {
      var row = document.createElement("tr");
      var sourceKind = item.evidenceSourceKind || "unknown";
      var reportMode = evidenceReportMode(item);
      var reportPath = evidenceReportPath(item);
      var score = (item.earnedScore || 0) + " / " + (item.score || 0);
      var action = item.recommendedAction || "manual_review";
      var safety = [
        "manualReviewRequired=" + boolText(item.manualReviewRequired === true),
        "autoApproveAllowed=false",
        "realPublishAllowed=false"
      ].join(" · ");
      [
        item.checkId || "unknown_check",
        item.checkType || "unknown",
        "evidenceSourceKind=" + sourceKind,
        "reportMode=" + reportMode,
        reportPath,
        score,
        "recommendedAction=" + action,
        safety
      ].forEach(function (value, index) {
        var cell = document.createElement("td");
        cell.textContent = escapeText(value);
        if (index >= 2) {
          cell.className = "mono";
        }
        if (index === 5 && String(item.status || "").toUpperCase() !== "FAILED") {
          cell.className = "ok";
        }
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
  }

  function reviewerActionText(item) {
    var action = item.recommendedAction || "manual_review";
    var checkType = item.checkType || "unknown";
    if (action === "verify_controlled_docker_output_and_score") {
      return "核对受控 Docker 证据、执行摘要、输出/pytest 结果和 score，确认报告来自已存在的受控 evidence。";
    }
    if (action === "review_static_notebook_evidence_matches_expected_tokens") {
      return "核对 Notebook 静态 evidence 的 cell 目标、expected output tokens 和 score，确认未启动 kernel。";
    }
    if (checkType === "notebook_cell") {
      return "核对 Notebook 证据与 assessmentPlan 是否一致，必要时要求人工复核。";
    }
    return "核对该 check 的 evidenceSource、reportMode、score 和安全边界，再进入后续人工审核。";
  }

  function manualChecklistActionText(item) {
    var action = item.recommendedReviewAction || item.recommendedAction || "manual_review";
    if (action === "collect_controlled_command_evidence_before_decision_note") {
      return "先补采受控 Docker command evidence，再记录 needs-evidence 或 approve-ready decision note。";
    }
    if (action === "prepare_controlled_docker_runtime_or_record_needs_evidence") {
      return "先准备受控 Docker runtime；若当前不可用，记录 needs-evidence decision note。";
    }
    if (action === "request_static_submission_or_grading_revision") {
      return "要求修订提交材料或 Grading DSL 静态 evidence 配置后再复核。";
    }
    if (action === "verify_static_evidence_and_score") {
      return "核对只读静态 evidence、得分和 assessmentPlan 对齐状态。";
    }
    if (action === "verify_controlled_docker_output_and_score") {
      return "核对受控 Docker 输出、pytest/stdout 证据和得分。";
    }
    return "核对 evidence、score 和安全边界，再记录人工审核结论。";
  }

  function normalizeManualChecklistItems(checklist) {
    if (!checklist || !Array.isArray(checklist.items)) {
      return [];
    }
    return checklist.items.map(function (item) {
      return {
        checkId: item.checkId || "unknown_check",
        checkType: item.checkType || "unknown",
        status: item.status || (item.readyForDecision === true ? "READY_FOR_DECISION" : "NEEDS_REVIEW"),
        score: item.score || 0,
        earnedScore: item.earnedScore || 0,
        evidenceSourceKind: item.evidenceSourceKind || item.selectedEvidenceMode || "manualChecklist",
        reportMode: item.reportMode || "GRADING_EVIDENCE_AUTO_REPORT",
        recommendedAction: item.recommendedReviewAction || item.recommendedAction || "manual_review",
        recommendedDecision: item.recommendedDecision || "needs-evidence",
        reviewReason: item.reviewReason || item.reason || "manual_review_required",
        manualReviewRequired: item.manualReviewRequired !== false,
        readyForDecision: item.readyForDecision === true
      };
    });
  }

  function renderManualReviewChecklist(checklist) {
    var items = normalizeManualChecklistItems(checklist);
    if (!checklist || !items.length) {
      return false;
    }
    var summary = checklist.summary || {};
    var decision = checklist.decisionNoteRecommendation || {};
    setText(
      "manual-review-action-summary",
      "manualChecklistStatus=" + (checklist.status || "NEEDS_REVIEW")
        + " · readyForDecision=" + (summary.readyForDecisionTotal || 0) + "/" + (summary.itemTotal || items.length)
        + " · decisionNoteRecommendation=" + (decision.decision || "needs-evidence")
        + " · autoApproveAllowed=false"
    );
    var list = byId("manual-review-action-list");
    if (!list) {
      return true;
    }
    list.innerHTML = "";
    items.slice(0, 12).forEach(function (item) {
      var card = document.createElement("div");
      card.className = "callout";
      var title = document.createElement("h3");
      title.textContent = item.checkId + " · " + item.recommendedAction;
      var action = document.createElement("p");
      action.textContent = manualChecklistActionText(item);
      var evidence = document.createElement("p");
      evidence.textContent = "status=" + item.status
        + " · selectedEvidenceMode=" + item.evidenceSourceKind
        + " · score=" + item.earnedScore + "/" + item.score;
      var decisionLine = document.createElement("p");
      decisionLine.textContent = "recommendedDecision=" + item.recommendedDecision
        + " · readyForDecision=" + boolText(item.readyForDecision)
        + " · reason=" + item.reviewReason;
      var safety = document.createElement("p");
      safety.textContent = "manualReviewRequired=true · autoApproveAllowed=false · realPublishAllowed=false";
      card.appendChild(title);
      card.appendChild(action);
      card.appendChild(evidence);
      card.appendChild(decisionLine);
      card.appendChild(safety);
      list.appendChild(card);
    });
    return true;
  }

  function checkInputSummary(item) {
    return item.inputSummary
      || item.description
      || item.expectedSummary
      || item.reviewFocus
      || item.checkTitle
      || item.checkId
      || "no input summary";
  }

  function checkStatus(item) {
    return item.status || item.resultStatus || (item.passed === true ? "PASSED" : "NEEDS_REVIEW");
  }

  function renderCheckEvidenceDetails(items) {
    var list = byId("check-evidence-detail-list");
    if (!list || !Array.isArray(items) || items.length === 0) {
      return;
    }
    list.innerHTML = "";
    items.slice(0, 12).forEach(function (item) {
      var card = document.createElement("div");
      card.className = "callout";

      var title = document.createElement("h3");
      title.textContent = (item.checkId || "unknown_check")
        + " · " + (item.checkType || "unknown")
        + " · " + checkStatus(item);

      var input = document.createElement("p");
      input.textContent = "inputSummary=" + checkInputSummary(item)
        + " · evidenceSourceKind=" + (item.evidenceSourceKind || "unknown")
        + " · reportMode=" + evidenceReportMode(item);

      var score = document.createElement("p");
      score.textContent = "score=" + (item.earnedScore || 0) + "/" + (item.score || 0)
        + " · recommendedAction=" + (item.recommendedAction || "manual_review")
        + " · manualReviewRequired=" + boolText(item.manualReviewRequired === true);

      var safety = document.createElement("p");
      safety.textContent = "reportPath=" + evidenceReportPath(item)
        + " · commandExecuted=" + boolText(item.commandExecuted === true)
        + " · contestantCodeExecuted=" + boolText(item.contestantCodeExecuted === true)
        + " · autoApproveAllowed=false · realPublishAllowed=false";

      card.appendChild(title);
      card.appendChild(input);
      card.appendChild(score);
      card.appendChild(safety);
      list.appendChild(card);
    });
    setText(
      "check-evidence-detail-summary",
      "detailItemTotal=" + items.length
        + " · failedTotal=" + items.filter(function (item) {
          return String(checkStatus(item)).toUpperCase() === "FAILED";
        }).length
        + " · autoApproveAllowed=false · realPublishAllowed=false"
    );
  }

  function renderReviewDecisionHints(hints) {
    var list = byId("review-decision-hint-list");
    var items = hints && Array.isArray(hints.items) ? hints.items : [];
    if (!list) {
      return;
    }
    list.innerHTML = "";
    if (!items.length) {
      var empty = document.createElement("div");
      empty.className = "callout";
      empty.innerHTML = "<h3>reviewDecisionHints unavailable</h3><p>等待评分证据生成后再给出确定性审核建议。</p>";
      list.appendChild(empty);
    } else {
      items.slice(0, 12).forEach(function (item) {
        var card = document.createElement("div");
        card.className = "callout";
        var title = document.createElement("h3");
        title.textContent = (item.checkId || "unknown_check")
          + " · " + (item.decisionHint || "NEEDS_MANUAL_REVIEW");
        var reason = document.createElement("p");
        reason.textContent = "reason=" + (item.reason || "manual_review_required")
          + " · severity=" + (item.severity || "info")
          + " · evidenceSourceKind=" + (item.evidenceSourceKind || "unknown");
        var action = document.createElement("p");
        action.textContent = "recommendedAction=" + (item.recommendedAction || "manual_review")
          + " · score=" + (item.earnedScore || 0) + "/" + (item.score || 0);
        var safety = document.createElement("p");
        safety.textContent = "manualReviewRequired=true · autoApproveAllowed=false · realPublishAllowed=false";
        card.appendChild(title);
        card.appendChild(reason);
        card.appendChild(action);
        card.appendChild(safety);
        list.appendChild(card);
      });
    }
    setText(
      "review-decision-hint-summary",
      "overallHint=" + (hints && hints.overallHint ? hints.overallHint : "NEEDS_EVIDENCE")
        + " · hintTotal=" + (hints && typeof hints.hintTotal !== "undefined" ? hints.hintTotal : items.length)
        + " · reviseRequiredTotal=" + (hints && hints.reviseRequiredTotal ? hints.reviseRequiredTotal : 0)
        + " · evidenceMissingTotal=" + (hints && hints.evidenceMissingTotal ? hints.evidenceMissingTotal : 0)
        + " · autoApproveAllowed=false"
    );
  }

  function renderReviewDecisionNotes(notes) {
    updateReviewerWorkspaceFromDecisionNotes(notes || {});
    var list = byId("review-decision-note-list");
    var items = notes && Array.isArray(notes.items) ? notes.items : [];
    var latest = notes && notes.latest ? notes.latest : {};
    if (!list) {
      return;
    }
    list.innerHTML = "";
    if (!items.length) {
      var empty = document.createElement("div");
      empty.className = "callout";
      empty.innerHTML = "<h3>no review decision note</h3><p>等待审核中心记录 approve-ready / needs-revision / needs-evidence。</p><p>autoApproveAllowed=false · realPublishAllowed=false</p>";
      list.appendChild(empty);
    } else {
      items.slice(0, 6).forEach(function (item) {
        var card = document.createElement("div");
        card.className = "callout";
        var title = document.createElement("h3");
        title.textContent = (item.decision || "unknown-decision") + " · " + (item.reviewer || "unknown-reviewer");
        var reason = document.createElement("p");
        reason.textContent = "reason=" + (item.reason || "none")
          + " · source=" + (item.source || "reviewDecisionHints");
        var status = document.createElement("p");
        status.textContent = "taskStatusBefore=" + (item.taskStatusBefore || "unknown")
          + " · taskStatusAfter=" + (item.taskStatusAfter || "unknown")
          + " · statusChanged=" + boolText(item.statusChanged === true);
        var safety = document.createElement("p");
        safety.textContent = "autoApproveAllowed=false · batchStateChangeAllowed=false · realPublishAllowed=false";
        card.appendChild(title);
        card.appendChild(reason);
        card.appendChild(status);
        card.appendChild(safety);
        list.appendChild(card);
      });
    }
    setText(
      "review-decision-note-summary",
      "reviewDecisionNoteTotal=" + (notes && typeof notes.total !== "undefined" ? notes.total : items.length)
        + " · latestDecision=" + (latest.decision || "none")
        + " · reviewer=" + (latest.reviewer || "none")
        + " · statusChanged=false"
    );
    renderReviewDecisionOutcome(notes);
  }

  function reviewDecisionOutcome(notes) {
    var latest = notes && notes.latest ? notes.latest : {};
    var decision = latest.decision || "none";
    if (decision === "approve-ready") {
      return {
        status: "READY_FOR_FINAL_HUMAN_APPROVE_REVIEW",
        nextRequiredAction: "human_review_can_consider_manual_approve",
        reviewDecisionNoteRecorded: true,
        latestDecision: decision,
        reviewer: latest.reviewer || "unknown-reviewer"
      };
    }
    if (decision === "needs-revision") {
      return {
        status: "NEEDS_REVISION_BEFORE_APPROVE",
        nextRequiredAction: "revise_grading_dsl_or_scoring_evidence",
        reviewDecisionNoteRecorded: true,
        latestDecision: decision,
        reviewer: latest.reviewer || "unknown-reviewer"
      };
    }
    if (decision === "needs-evidence") {
      return {
        status: "NEEDS_MORE_EVIDENCE_BEFORE_APPROVE",
        nextRequiredAction: "collect_or_review_additional_grading_evidence",
        reviewDecisionNoteRecorded: true,
        latestDecision: decision,
        reviewer: latest.reviewer || "unknown-reviewer"
      };
    }
    return {
      status: "WAITING_REVIEW_DECISION_NOTE",
      nextRequiredAction: "record_review_decision_note",
      reviewDecisionNoteRecorded: false,
      latestDecision: "none",
      reviewer: "none"
    };
  }

  function renderReviewDecisionOutcome(notes) {
    var outcome = reviewDecisionOutcome(notes || {});
    var list = byId("review-decision-outcome-list");
    setText("review-decision-outcome-status", "outcome=" + outcome.status);
    setText(
      "review-decision-outcome-summary",
      "reviewDecisionNoteRecorded=" + boolText(outcome.reviewDecisionNoteRecorded)
        + " · latestDecision=" + outcome.latestDecision
        + " · reviewer=" + outcome.reviewer
        + " · nextRequiredAction=" + outcome.nextRequiredAction
    );
    setText(
      "review-decision-outcome-safety",
      "autoApproveAllowed=false · manualApproveStillRequired=true · realPublishAllowed=false"
    );
    if (!list) {
      return;
    }
    list.innerHTML = "";
    var card = document.createElement("div");
    card.className = "callout";
    var title = document.createElement("h3");
    title.textContent = outcome.status;
    var summary = document.createElement("p");
    summary.textContent = "reviewDecisionNoteRecorded=" + boolText(outcome.reviewDecisionNoteRecorded)
      + " · latestDecision=" + outcome.latestDecision
      + " · reviewer=" + outcome.reviewer;
    var action = document.createElement("p");
    action.textContent = "nextRequiredAction=" + outcome.nextRequiredAction
      + " · taskStatusChanged=false"
      + " · manualApproveStillRequired=true";
    var safety = document.createElement("p");
    safety.textContent = "autoApproveAllowed=false · batchStateChangeAllowed=false · realPublishAllowed=false";
    card.appendChild(title);
    card.appendChild(summary);
    card.appendChild(action);
    card.appendChild(safety);
    list.appendChild(card);
  }

  function renderManualReviewActions(items) {
    var list = byId("manual-review-action-list");
    if (!list || !Array.isArray(items) || items.length === 0) {
      return;
    }
    list.innerHTML = "";
    items.slice(0, 12).forEach(function (item) {
      var card = document.createElement("div");
      card.className = "callout";
      var title = document.createElement("h3");
      title.textContent = (item.checkId || "unknown_check") + " · " + (item.recommendedAction || "manual_review");
      var body = document.createElement("p");
      body.textContent = reviewerActionText(item);
      var evidence = document.createElement("p");
      evidence.textContent = "evidenceSourceKind=" + (item.evidenceSourceKind || "unknown")
        + " · reportMode=" + evidenceReportMode(item)
        + " · score=" + (item.earnedScore || 0) + "/" + (item.score || 0);
      var safety = document.createElement("p");
      safety.textContent = "manualReviewRequired=" + boolText(item.manualReviewRequired === true)
        + " · autoApproveAllowed=false · realPublishAllowed=false";
      card.appendChild(title);
      card.appendChild(body);
      card.appendChild(evidence);
      card.appendChild(safety);
      list.appendChild(card);
    });
    setText(
      "manual-review-action-summary",
      "manualActionTotal=" + items.length + " · autoApproveAllowed=false · realPublishAllowed=false"
    );
  }

  function renderAutoSteps(steps, warnings) {
    var list = byId("evidence-auto-step-list");
    if (!list) {
      return;
    }
    list.innerHTML = "";
    var renderedSteps = Array.isArray(steps) ? steps : [];
    if (renderedSteps.length === 0) {
      var empty = document.createElement("div");
      empty.className = "callout";
      empty.innerHTML = "<h3>no evidence auto steps</h3><p>等待 GRADING_EVIDENCE_AUTO_REPORT。</p>";
      list.appendChild(empty);
    } else {
      renderedSteps.forEach(function (step) {
        var card = document.createElement("div");
        card.className = "callout";
        var title = document.createElement("h3");
        title.textContent = (step.id || "unknown_step") + " · " + (step.status || "UNKNOWN");
        var meta = document.createElement("p");
        meta.textContent = "mode=" + (step.mode || "none")
          + " · executed=" + (step.executed || 0)
          + " · passed=" + (step.passed || 0)
          + " · commandExecuted=" + boolText(step.commandExecuted === true);
        var reason = document.createElement("p");
        reason.textContent = "reason=" + (step.reason || step.message || "none")
          + " · contestantCodeExecuted=" + boolText(step.contestantCodeExecuted === true)
          + " · autoApproveAllowed=false";
        card.appendChild(title);
        card.appendChild(meta);
        card.appendChild(reason);
        list.appendChild(card);
      });
    }
    if (Array.isArray(warnings) && warnings.length > 0) {
      warnings.forEach(function (warning) {
        var card = document.createElement("div");
        card.className = "callout";
        var title = document.createElement("h3");
        title.textContent = "warning · " + (warning.code || warning.status || "UNKNOWN");
        var body = document.createElement("p");
        body.textContent = warning.message || warning.reason || "controlled evidence warning";
        card.appendChild(title);
        card.appendChild(body);
        list.appendChild(card);
      });
    }
  }

  function evidenceStatus(value) {
    if (!value || typeof value !== "object") {
      return "NOT_COLLECTED";
    }
    return value.status || "UNKNOWN";
  }

  function renderAutoExecutionMatrix(matrix, nextAction) {
    var summary = matrix && matrix.summary ? matrix.summary : {};
    var items = matrix && Array.isArray(matrix.items) ? matrix.items : [];
    setText(
      "evidence-auto-matrix-status",
      "matrixStatus=API_READONLY_LOADED"
        + " · mode=" + (matrix && matrix.mode ? matrix.mode : "GRADING_EVIDENCE_AUTO_EXECUTION_MATRIX")
        + " · noExecutionFromPage=true"
    );
    setText(
      "evidence-auto-matrix-ready",
      (summary.evidenceReadyTotal || 0) + " / " + (summary.checkTotal || items.length || 0)
    );
    setText(
      "evidence-auto-matrix-controlled",
      (summary.controlledCommandCoveredTotal || 0) + " / " + (summary.controlledCommandCheckTotal || 0)
    );
    setText(
      "evidence-auto-matrix-readonly",
      (summary.readonlyStaticCoveredTotal || 0) + " / " + (summary.readonlyStaticCheckTotal || 0)
    );
    setText("evidence-auto-matrix-approval", boolText(summary.readyForApprovalRecommendation === true));
    setText("evidence-auto-next-action", "nextCoreAction=" + (nextAction && nextAction.id ? nextAction.id : "none"));

    var list = byId("evidence-auto-matrix-list");
    if (list) {
      list.innerHTML = "";
      if (!items.length) {
        var empty = document.createElement("div");
        empty.className = "callout";
        empty.innerHTML = "<h3>no execution matrix</h3><p>等待 GRADING_EVIDENCE_AUTO_REPORT.executionMatrix。</p>";
        list.appendChild(empty);
      } else {
        items.slice(0, 12).forEach(function (item) {
          var readonly = item.readonlyEvidence || {};
          var controlled = item.controlledCommandEvidence || {};
          var selected = item.selectedEvidence || {};
          var card = document.createElement("div");
          card.className = "callout";
          var title = document.createElement("h3");
          title.textContent = (item.checkId || "unknown_check")
            + " · " + (item.checkType || "unknown")
            + " · evidenceReady=" + boolText(item.evidenceReady === true);
          var evidence = document.createElement("p");
          evidence.textContent = "readonlyEvidence=" + evidenceStatus(readonly)
            + " · controlledCommandEvidence=" + evidenceStatus(controlled)
            + " · selectedEvidence=" + evidenceStatus(selected);
          var score = document.createElement("p");
          score.textContent = "score=" + ((selected && selected.earnedScore) || 0) + "/" + (item.score || 0)
            + " · recommendedNextEvidence=" + (item.recommendedNextEvidence || "manual_review")
            + " · manualReviewRequired=" + boolText(item.manualReviewRequired === true);
          card.appendChild(title);
          card.appendChild(evidence);
          card.appendChild(score);
          list.appendChild(card);
        });
      }
    }

    var actionList = byId("evidence-auto-next-action-detail");
    if (actionList) {
      actionList.innerHTML = "";
      var card = document.createElement("div");
      card.className = "callout";
      var title = document.createElement("h3");
      title.textContent = "nextCoreAction · " + (nextAction && nextAction.id ? nextAction.id : "none");
      var reason = document.createElement("p");
      reason.textContent = "reason=" + (nextAction && nextAction.reason ? nextAction.reason : "none")
        + " · label=" + (nextAction && nextAction.label ? nextAction.label : "none");
      var api = document.createElement("p");
      var apiInfo = nextAction && nextAction.api ? nextAction.api : {};
      api.textContent = "api=" + (apiInfo.method || "GET") + " " + (apiInfo.path || "none")
        + " · cli=" + (nextAction && nextAction.cli ? nextAction.cli : "none");
      var linkLine = document.createElement("p");
      var link = document.createElement("a");
      link.className = "pill strong";
      link.id = "evidence-auto-review-center-link";
      link.href = reviewCenterDecisionHref(resolveTaskId(), nextAction || {});
      link.textContent = "打开审核中心记录结论";
      var safety = document.createElement("p");
      safety.textContent = "manualReviewRequired=true · autoApproveAllowed=false · realPublishAllowed=false";
      card.appendChild(title);
      card.appendChild(reason);
      card.appendChild(api);
      linkLine.appendChild(link);
      card.appendChild(linkLine);
      card.appendChild(safety);
      actionList.appendChild(card);
    }
    setEvidenceAutoReviewCenterLink(resolveTaskId(), nextAction || {});
  }

  function renderAutoScorePreview(scorePreview) {
    var preview = scorePreview && typeof scorePreview === "object" ? scorePreview : {};
    setText(
      "evidence-auto-score-preview-status",
      "scorePreviewStatus=API_READONLY_LOADED"
        + " · mode=" + (preview.mode || "GRADING_EVIDENCE_AUTO_SCORE_PREVIEW")
        + " · source=" + (preview.source || "GRADING_EVIDENCE_AUTO_REPORT.executionMatrix.selectedEvidence")
        + " · manualReviewRequired=" + boolText(preview.manualReviewRequired !== false)
    );
    setText(
      "evidence-auto-score-preview-summary",
      "earnedScore=" + (preview.earnedScore || 0) + "/" + (preview.totalScore || 0)
        + " · coveredScore=" + (preview.coveredScore || 0)
        + " · missingScore=" + (preview.missingScore || 0)
        + " · readyForDecisionNote=" + boolText(preview.readyForDecisionNote === true)
    );
    setText("evidence-auto-score-preview-score", (preview.earnedScore || 0) + " / " + (preview.totalScore || 0));
    setText("evidence-auto-score-preview-coverage", String(preview.coverageRatio || 0));
    setText("evidence-auto-score-preview-passrate", String(preview.passRate || 0));
    setText("evidence-auto-score-preview-missing", String(preview.missingEvidenceTotal || 0));

    var missing = byId("evidence-auto-score-preview-missing-list");
    if (missing) {
      missing.innerHTML = "";
      var card = document.createElement("div");
      card.className = "callout";
      var title = document.createElement("h3");
      title.textContent = "GradingEvidenceAutoScorePreview · " + (preview.status || "UNKNOWN");
      var ids = Array.isArray(preview.missingCheckIds) ? preview.missingCheckIds.join(", ") : "";
      var body = document.createElement("p");
      body.textContent = "missingCheckIds=" + (ids || "none")
        + " · autoApproveAllowed=" + boolText(preview.autoApproveAllowed === true)
        + " · realPublishAllowed=" + boolText(preview.realPublishAllowed === true);
      card.appendChild(title);
      card.appendChild(body);
      missing.appendChild(card);
    }
  }

  function renderGradingResultPreview(preview) {
    if (!preview) {
      return;
    }
    updateReviewerWorkspaceFromResultPreview(preview);
    var summary = preview.summary || {};
    var score = preview.score || {};
    var safety = preview.safety || {};
    var evidence = preview.evidencePreview || {};
    var items = Array.isArray(evidence.items) ? evidence.items : [];
    setText(
      "grading-result-preview-status",
      "resultPreviewStatus=API_READONLY_LOADED"
        + " · mode=" + (preview.mode || "READ_EXISTING_GRADING_REPORT_ONLY")
        + " · reportType=" + (preview.reportType || "GRADING_REPORT")
        + " · noExecutionFromPage=true"
    );
    setText(
      "grading-result-preview-summary",
      "summary.executed=" + (summary.executed || 0)
        + " · passed=" + (summary.passed || 0)
        + " · failed=" + (summary.failed || 0)
        + " · deferred=" + (summary.deferred || 0)
        + " · resultStatus=" + (preview.resultStatus || "UNKNOWN")
    );
    setText("grading-result-preview-score", (score.earnedScore || 0) + " / " + (score.totalScore || 0));
    setText("grading-result-preview-result", preview.resultStatus || "UNKNOWN");
    setText("grading-result-preview-answer-visible", boolText(safety.answerVisibleToCandidate === true));
    setText("grading-result-preview-execution", boolText(safety.sandboxExecutedByPreview === true));

    var list = byId("grading-result-preview-list");
    if (!list) {
      return;
    }
    list.innerHTML = "";
    if (!items.length) {
      var empty = document.createElement("div");
      empty.className = "callout";
      empty.innerHTML = "<h3>no preview evidence</h3><p>等待评分报告生成 evidencePreview。</p>";
      list.appendChild(empty);
      return;
    }
    items.slice(0, 6).forEach(function (item) {
      var card = document.createElement("div");
      card.className = "callout";
      var title = document.createElement("h3");
      title.textContent = (item.checkId || "unknown_check")
        + " · " + (item.checkType || "unknown")
        + " · " + (item.status || "UNKNOWN");
      var scoreLine = document.createElement("p");
      scoreLine.textContent = "score=" + (item.earnedScore || 0) + "/" + (item.score || 0)
        + " · evidenceSourceKind=" + (item.evidenceSourceKind || "unknown")
        + " · recommendedAction=" + (item.recommendedAction || "manual_review");
      var safetyLine = document.createElement("p");
      safetyLine.textContent = "manualReviewRequired=" + boolText(item.manualReviewRequired === true)
        + " · answerVisibleToCandidate=false · gradingRefVisibleToCandidate=false";
      card.appendChild(title);
      card.appendChild(scoreLine);
      card.appendChild(safetyLine);
      list.appendChild(card);
    });
  }

  async function loadGradingResultPreview(reportFile, taskId) {
    if (!window.fetch || !reportFile) {
      return;
    }
    try {
      var response = await fetch(gradingResultPreviewPath(reportFile, taskId), { headers: { "Accept": "application/json" } });
      if (!response.ok) {
        setText("grading-result-preview-status", "resultPreviewStatus=LOAD_FAILED · status=" + response.status + " · fallback=STATIC_HTML");
        return;
      }
      var payload = await response.json();
      var preview = payload && payload.data ? payload.data.gradingResultPreview : null;
      renderGradingResultPreview(preview);
    } catch (error) {
      setText("grading-result-preview-status", "resultPreviewStatus=LOAD_FAILED · reason=fetch_error · fallback=STATIC_HTML");
    }
  }

  function renderGradingEvidenceReadiness(readiness) {
    if (!readiness) {
      return;
    }
    updateReviewerWorkspaceFromEvidenceReadiness(readiness);
    var summary = readiness.summary || {};
    var safety = readiness.safety || {};
    var items = Array.isArray(readiness.items) ? readiness.items : [];
    var actions = Array.isArray(readiness.nextActions) ? readiness.nextActions : [];
    var ratio = Number(summary.coverageRatio || 0);
    setText(
      "grading-evidence-readiness-status",
      "readinessStatus=API_READONLY_LOADED"
        + " · mode=" + (readiness.mode || "GRADING_EVIDENCE_READINESS")
        + " · sourceReportTotal=" + (readiness.sourceReportTotal || 0)
        + " · noExecutionFromPage=true"
    );
    setText(
      "grading-evidence-readiness-summary",
      "evidenceReadyTotal=" + (summary.evidenceReadyTotal || 0)
        + " · missingEvidenceTotal=" + (summary.missingEvidenceTotal || 0)
        + " · controlledCommandMissingTotal=" + (summary.controlledCommandMissingTotal || 0)
        + " · readonlyStaticMissingTotal=" + (summary.readonlyStaticMissingTotal || 0)
    );
    setText("grading-evidence-readiness-coverage", Math.round(ratio * 100) + "%");
    setText("grading-evidence-readiness-missing", summary.missingEvidenceTotal || 0);
    setText("grading-evidence-readiness-approval", boolText(summary.readyForApprovalRecommendation === true));
    setText("grading-evidence-readiness-execution", boolText(safety.sandboxExecutedByReadiness === true));

    var list = byId("grading-evidence-readiness-list");
    if (list) {
      list.innerHTML = "";
      if (!items.length) {
        var empty = document.createElement("div");
        empty.className = "callout";
        empty.innerHTML = "<h3>no readiness items</h3><p>等待评分 evidence 报告生成 check 级摘要。</p>";
        list.appendChild(empty);
      } else {
        items.slice(0, 8).forEach(function (item) {
          var card = document.createElement("div");
          card.className = "callout";
          var title = document.createElement("h3");
          title.textContent = (item.checkId || "unknown_check")
            + " · " + (item.checkType || "unknown")
            + " · evidenceReady=" + boolText(item.evidenceReady === true);
          var meta = document.createElement("p");
          meta.textContent = "score=" + (item.earnedScore || 0) + "/" + (item.score || 0)
            + " · source=" + (item.evidenceSourceKind || "unknown")
            + " · next=" + (item.recommendedNextEvidence || "manual_review");
          var action = document.createElement("p");
          action.textContent = "recommendedAction=" + (item.recommendedAction || "manual_review")
            + " · manualReviewRequired=" + boolText(item.manualReviewRequired === true);
          card.appendChild(title);
          card.appendChild(meta);
          card.appendChild(action);
          list.appendChild(card);
        });
      }
    }

    var actionList = byId("grading-evidence-readiness-actions");
    if (actionList) {
      actionList.innerHTML = "";
      actions.slice(0, 6).forEach(function (item) {
        var card = document.createElement("div");
        card.className = "callout";
        var title = document.createElement("h3");
        title.textContent = item.id || "review_ready_score_and_evidence";
        var label = document.createElement("p");
        label.textContent = item.label || "Review ready score and evidence";
        var checks = document.createElement("p");
        checks.textContent = "checkIds=" + (Array.isArray(item.checkIds) ? item.checkIds.join(",") : "");
        card.appendChild(title);
        card.appendChild(label);
        card.appendChild(checks);
        actionList.appendChild(card);
      });
    }
  }

  async function loadGradingEvidenceReadiness(reportFile, taskId) {
    if (!window.fetch || !reportFile) {
      return;
    }
    try {
      var response = await fetch(gradingEvidenceReadinessPath(reportFile, taskId), { headers: { "Accept": "application/json" } });
      if (!response.ok) {
        setText("grading-evidence-readiness-status", "readinessStatus=LOAD_FAILED · status=" + response.status + " · fallback=STATIC_HTML");
        return;
      }
      var payload = await response.json();
      var readiness = payload && payload.data ? payload.data.gradingEvidenceReadiness : null;
      renderGradingEvidenceReadiness(readiness);
    } catch (error) {
      setText("grading-evidence-readiness-status", "readinessStatus=LOAD_FAILED · reason=fetch_error · fallback=STATIC_HTML");
    }
  }

  function autoEvidenceItems(report) {
    if (Array.isArray(report.checkEvidenceReviewItems)) {
      return report.checkEvidenceReviewItems;
    }
    if (Array.isArray(report.checks)) {
      return report.checks.map(function (check) {
        return {
          checkId: check.checkId || check.id,
          checkType: check.checkType || check.type,
          status: check.status,
          inputSummary: check.inputSummary || check.description || check.expectedSummary,
          score: check.score,
          earnedScore: check.earnedScore,
          evidenceSourceKind: check.evidenceSourceKind || "evidenceAuto",
          reportMode: report.mode,
          reportPath: report.reportPath || "none",
          recommendedAction: check.recommendedAction || "review_evidence_auto_check",
          commandExecuted: check.commandExecuted === true,
          contestantCodeExecuted: check.contestantCodeExecuted === true,
          manualReviewRequired: true
        };
      });
    }
    return [];
  }

  function applyAutoEvidenceReport(report, sourceLabel, reviewDecisionNotes) {
    var summary = report.summary || {};
    var coverage = report.evidenceCoverage || {};
    var safety = report.safety || {};
    var items = autoEvidenceItems(report);
    renderRows(items);
    renderCheckEvidenceDetails(items);
    renderReviewDecisionHints(report.reviewDecisionHints || {});
    renderReviewDecisionNotes(reviewDecisionNotes || report.reviewDecisionNotes || {});
    if (!renderManualReviewChecklist(report.manualReviewChecklist || null)) {
      renderManualReviewActions(items);
    }
    renderAutoSteps(report.steps || [], report.warnings || []);
    renderAutoExecutionMatrix(report.executionMatrix || {}, report.nextCoreAction || {});
    renderAutoScorePreview(report.scorePreview || {});
    updateReviewerWorkspaceFromAutoEvidence(report);
    renderReviewerSafetySummary(report.reviewerSafetySummary || null);
    setText(
      "evidence-auto-status",
      "autoReportStatus=API_READONLY_LOADED"
        + " · source=" + sourceLabel
        + " · mode=" + (report.mode || "GRADING_EVIDENCE_AUTO_REPORT")
        + " · sourceMode=" + (report.sourceMode || summary.sourceMode || "EVIDENCE_AUTO")
        + " · noExecutionFromPage=true"
    );
    setText(
      "evidence-auto-summary",
      "readonlyReportIncluded=" + boolText(summary.readonlyReportIncluded === true)
        + " · controlledCommandRequested=" + boolText(summary.controlledCommandRequested === true)
        + " · controlledCommandIncluded=" + boolText(summary.controlledCommandIncluded === true)
        + " · warningTotal=" + ((report.warnings || []).length)
    );
    setText(
      "merged-evidence-api-status",
      "apiStatus=API_READONLY_LOADED · dynamicSource=" + sourceLabel + " · mode=GRADING_EVIDENCE_AUTO_REPORT"
    );
    setText(
      "merged-evidence-api-summary",
      "checkEvidenceReviewItemTotal=" + items.length
        + " · executed=" + (summary.executed || 0)
        + " · deferred=" + (summary.deferred || summary.deferredCheckTotal || 0)
        + " · earnedScore=" + (summary.earnedScore || 0) + "/" + (summary.totalScore || coverage.totalScore || 0)
        + " · autoApproveAllowed=" + boolText(safety.autoApproveAllowed === true)
    );
  }

  function applyMergedEvidence(evidence, taskId, sourceLabel) {
    sourceLabel = sourceLabel || "GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence";
    if (!evidence || evidence.visible !== true) {
      setText(
        "merged-evidence-api-status",
        "apiStatus=DETAIL_LOADED_WITHOUT_MERGED_EVIDENCE · dynamicSource=" + sourceLabel + " · taskId=" + taskId + " · fallback=STATIC_HTML"
      );
      return;
    }
    var summary = evidence.summary || {};
    var items = Array.isArray(evidence.checkEvidenceReviewItems) ? evidence.checkEvidenceReviewItems : [];
    var safety = evidence.safety || {};
    renderRows(items);
    renderCheckEvidenceDetails(items);
    renderReviewDecisionHints(evidence.reviewDecisionHints || {});
    renderReviewDecisionNotes(evidence.reviewDecisionNotes || {});
    renderManualReviewActions(items);
    setText(
      "merged-evidence-api-status",
      "apiStatus=API_READONLY_LOADED · dynamicSource=" + sourceLabel + " · taskId=" + taskId + " · visible=true"
    );
    setText(
      "merged-evidence-api-summary",
      "checkEvidenceReviewItemTotal=" + (summary.checkEvidenceReviewItemTotal || items.length)
        + " · manualCheckReviewTotal=" + (summary.manualCheckReviewTotal || 0)
        + " · earnedScore=" + (summary.earnedScore || 0) + "/" + (summary.totalScore || 0)
        + " · mergeExecutedOnlyExistingReports=" + boolText(safety.mergeExecutedOnlyExistingReports === true)
    );
    setText(
      "reviewer-workspace-evidence",
      "mergedEvidenceItems=" + (summary.checkEvidenceReviewItemTotal || items.length)
        + " · manualCheckReviewTotal=" + (summary.manualCheckReviewTotal || 0)
        + " · score=" + (summary.earnedScore || 0) + "/" + (summary.totalScore || 0)
    );
    setText("reviewer-workspace-next-action", "nextAction=review_merged_evidence_and_record_decision_note");
    setReviewerWorkspaceReviewLink(
      taskId,
      { id: "review_merged_evidence_and_record_decision_note" },
      "grading-report-reviewer-workspace"
    );
  }

  function gradingRecordReviewState(latest) {
    if (!latest) {
      return {
        state: "NO_GRADING_RECORD",
        readyForAgentReview: false,
        manualRecordReviewRequired: false,
        nextRequiredAction: "create_grading_record_from_latest_evidence_report",
        blockingReasons: ["grading_record_missing"]
      };
    }
    var status = String(latest.status || "");
    var decision = latest.reviewDecision || "none";
    if (status === "HUMAN_APPROVED" && decision === "approve-ready") {
      return {
        state: "READY_FOR_PLATFORM_REVIEW",
        readyForAgentReview: true,
        manualRecordReviewRequired: false,
        nextRequiredAction: "continue_platform_review_after_grading_record_approved",
        blockingReasons: []
      };
    }
    if (status === "NEEDS_EVIDENCE" || decision === "needs-evidence") {
      return {
        state: "NEEDS_MORE_EVIDENCE",
        readyForAgentReview: false,
        manualRecordReviewRequired: true,
        nextRequiredAction: "collect_more_evidence_for_grading_record_review",
        blockingReasons: ["latest_grading_record_needs_more_evidence"]
      };
    }
    if (status === "NEEDS_REVISION" || decision === "needs-revision") {
      return {
        state: "NEEDS_REVISION",
        readyForAgentReview: false,
        manualRecordReviewRequired: true,
        nextRequiredAction: "revise_grading_or_submission_before_platform_review",
        blockingReasons: ["latest_grading_record_needs_revision"]
      };
    }
    return {
      state: "WAITING_GRADING_RECORD_REVIEW",
      readyForAgentReview: false,
      manualRecordReviewRequired: true,
      nextRequiredAction: "review_latest_grading_record_for_platform_review",
      blockingReasons: ["latest_grading_record_waiting_human_review"]
    };
  }

  function gradingRecordIntegrationFromRecords(items, taskId, sourceLabel) {
    var records = Array.isArray(items) ? items : [];
    var latest = records.length ? records[0] : null;
    var reviewState = gradingRecordReviewState(latest);
    return {
      component: "GradingRecordReviewIntegration",
      source: sourceLabel,
      taskId: taskId,
      total: records.length,
      latestRecordId: latest && latest.id ? latest.id : "none",
      latestStatus: latest && latest.status ? latest.status : "none",
      latestDecision: latest && latest.reviewDecision ? latest.reviewDecision : "none",
      latestReviewedBy: latest && latest.reviewedBy ? latest.reviewedBy : "none",
      latestReportPath: latest && latest.reportPath ? latest.reportPath : "none",
      latestEarnedScore: latest && typeof latest.earnedScore !== "undefined" ? latest.earnedScore : 0,
      latestTotalScore: latest && typeof latest.totalScore !== "undefined" ? latest.totalScore : 0,
      latestCoverageRatio: latest && typeof latest.coverageRatio !== "undefined" ? latest.coverageRatio : 0,
      humanReviewRecordedTotal: records.filter(function (record) {
        return !!record.reviewDecision;
      }).length,
      state: reviewState.state,
      readyForAgentReview: reviewState.readyForAgentReview,
      manualRecordReviewRequired: reviewState.manualRecordReviewRequired,
      nextRequiredAction: reviewState.nextRequiredAction,
      blockingReasons: reviewState.blockingReasons,
      recordReviewChangesTaskStatus: false,
      autoApproveAllowed: false,
      realPublishAllowed: false,
      realPublish: false
    };
  }

  function renderGradingRecordReviewIntegration(integration, sourceLabel) {
    var data = integration || {};
    var stateValue = data.state || "NO_GRADING_RECORD";
    var total = typeof data.total === "undefined" ? 0 : data.total;
    var latestRecordId = data.latestRecordId || "none";
    var latestStatus = data.latestStatus || "none";
    var latestDecision = data.latestDecision || "none";
    var ready = data.readyForAgentReview === true;
    var blockers = Array.isArray(data.blockingReasons) ? data.blockingReasons : [];
    var reviewCommand = latestRecordId !== "none"
      ? "python lab_cli.py grade record-review --id " + latestRecordId + " --reviewer <reviewer> --decision approve-ready"
      : "python lab_cli.py grade record-create --report <grading_report> --submission-id <submission_id>";

    setText(
      "grading-record-review-status",
      "recordReviewState=" + stateValue
        + " · source=" + (sourceLabel || data.source || "GET /api/grading/records?taskId={id}")
    );
    setText("grading-record-review-total", total);
    setText("grading-record-review-latest-status", latestStatus);
    setText("grading-record-review-latest-decision", latestDecision);
    setText("grading-record-review-ready", boolText(ready));
    setText(
      "grading-record-review-summary",
      "recordTotal=" + total
        + " · latestRecordId=" + latestRecordId
        + " · latestStatus=" + latestStatus
        + " · latestDecision=" + latestDecision
        + " · readyForAgentReview=" + boolText(ready)
        + " · agentApiRequired=false"
    );
    updateReviewerWorkspaceFromGradingRecord(data);

    var list = byId("grading-record-review-list");
    if (!list) {
      return;
    }
    list.innerHTML = "";

    var recordCard = document.createElement("div");
    recordCard.className = "callout";
    var recordTitle = document.createElement("h3");
    recordTitle.textContent = "GradingRecordReviewIntegration · " + stateValue;
    var score = document.createElement("p");
    score.textContent = "latestRecordId=" + latestRecordId
      + " · score=" + (data.latestEarnedScore || 0) + "/" + (data.latestTotalScore || 0)
      + " · coverageRatio=" + (data.latestCoverageRatio || 0);
    var reviewer = document.createElement("p");
    reviewer.textContent = "humanReviewRecordedTotal=" + (data.humanReviewRecordedTotal || 0)
      + " · reviewedBy=" + (data.latestReviewedBy || "none")
      + " · reportPath=" + (data.latestReportPath || "none");
    var safety = document.createElement("p");
    safety.textContent = "taskStatusChanged=false · autoApproveAllowed=false · realPublishAllowed=false";
    recordCard.appendChild(recordTitle);
    recordCard.appendChild(score);
    recordCard.appendChild(reviewer);
    recordCard.appendChild(safety);
    list.appendChild(recordCard);

    var actionCard = document.createElement("div");
    actionCard.className = "callout";
    var actionTitle = document.createElement("h3");
    actionTitle.textContent = "nextRequiredAction · " + (data.nextRequiredAction || "review_latest_grading_record_for_platform_review");
    var blockersLine = document.createElement("p");
    blockersLine.textContent = "blockingReasons=" + (blockers.length ? blockers.join(",") : "none")
      + " · manualRecordReviewRequired=" + boolText(data.manualRecordReviewRequired === true);
    var commandLine = document.createElement("p");
    commandLine.textContent = "reviewCommand=" + reviewCommand + " · commandExecutedFromPage=false";
    var boundaryLine = document.createElement("p");
    boundaryLine.textContent = "localOnly=true · networkAccess=false · agentApiRequired=false · realPublish=false";
    actionCard.appendChild(actionTitle);
    actionCard.appendChild(blockersLine);
    actionCard.appendChild(commandLine);
    actionCard.appendChild(boundaryLine);
    list.appendChild(actionCard);
  }

  function applyGradingRecordReviewFromDetail(detail, taskId) {
    var gradingRecords = detail && detail.gradingRecords ? detail.gradingRecords : {};
    var summary = gradingRecords.summary || {};
    var integration = gradingRecords.reviewIntegration || {};
    var latest = gradingRecords.latest || {};
    var detailSource = "GET /api/review-tasks/{id}.reviewDetail.gradingRecords.reviewIntegration";
    var recordSource = integration.source || gradingRecords.source || "JsonTaskStore.gradingRecords";
    if (!integration.component && !latest.id) {
      return;
    }
    renderGradingRecordReviewIntegration(
      {
        component: "GradingRecordReviewIntegration",
        source: detailSource + " · recordSource=" + recordSource,
        taskId: taskId,
        total: typeof gradingRecords.total === "undefined" ? 0 : gradingRecords.total,
        latestRecordId: integration.latestRecordId || latest.id || "none",
        latestStatus: integration.latestStatus || latest.status || summary.latestStatus || "none",
        latestDecision: integration.latestDecision || latest.reviewDecision || summary.latestReviewDecision || "none",
        latestReviewedBy: integration.latestReviewedBy || summary.latestReviewedBy || "none",
        latestReportPath: integration.latestReportPath || latest.reportPath || "none",
        latestEarnedScore: typeof integration.latestEarnedScore === "undefined" ? summary.latestEarnedScore : integration.latestEarnedScore,
        latestTotalScore: typeof integration.latestTotalScore === "undefined" ? summary.latestTotalScore : integration.latestTotalScore,
        latestCoverageRatio: typeof integration.latestCoverageRatio === "undefined" ? summary.latestCoverageRatio : integration.latestCoverageRatio,
        humanReviewRecordedTotal: integration.humanReviewRecordedTotal || summary.humanReviewRecordedTotal || 0,
        state: integration.state || summary.platformReviewState || "NO_GRADING_RECORD",
        readyForAgentReview: integration.readyForAgentReview === true || summary.readyForAgentReview === true,
        manualRecordReviewRequired: integration.manualRecordReviewRequired === true,
        nextRequiredAction: integration.nextRequiredAction || summary.platformReviewNextRequiredAction || "review_latest_grading_record_for_platform_review",
        blockingReasons: Array.isArray(integration.blockingReasons) ? integration.blockingReasons : [],
        recordReviewChangesTaskStatus: false,
        autoApproveAllowed: false,
        realPublishAllowed: false,
        realPublish: false
      },
      detailSource + " · recordSource=" + recordSource
    );
  }

  async function loadGradingRecordReview(taskId) {
    if (!window.fetch || !taskId) {
      return "";
    }
    try {
      var response = await fetch(gradingRecordsPath(taskId), { headers: { "Accept": "application/json" } });
      if (!response.ok) {
        setText("grading-record-review-status", "recordReviewState=LOAD_FAILED · status=" + response.status + " · fallback=GET /api/review-tasks/{id}");
        return "";
      }
      var payload = await response.json();
      var data = payload && payload.data ? payload.data : {};
      var items = Array.isArray(data.items) ? data.items : [];
      var source = "GET /api/grading/records?taskId={id}";
      if (data.mode) {
        source += " · " + data.mode;
      }
      if (data.dbPath) {
        source += " · dbPath=" + data.dbPath;
      }
      renderGradingRecordReviewIntegration(
        gradingRecordIntegrationFromRecords(items, taskId, source),
        source
      );
      return items.length && items[0].reportPath ? items[0].reportPath : "";
    } catch (error) {
      setText("grading-record-review-status", "recordReviewState=LOAD_FAILED · reason=fetch_error · fallback=GET /api/review-tasks/{id}");
      return "";
    }
  }

  function persistResolvedReportFile(reportFile) {
    if (!reportFile || resolveReportFile()) {
      return;
    }
    try {
      var url = new URL(window.location.href);
      url.searchParams.set("file", reportFile);
      window.history.replaceState({}, "", url.pathname + "?" + url.searchParams.toString());
    } catch (error) {
      // The report is still rendered even when history updates are unavailable.
    }
  }

  async function loadMergedEvidence() {
    if (!window.fetch) {
      return;
    }
    var taskId = resolveTaskId();
    var reportFile = resolveReportFile();
    setEvidenceAutoReviewCenterLink(taskId, {});
    var latestRecordReportPath = await loadGradingRecordReview(taskId);
    if (!reportFile && latestRecordReportPath) {
      reportFile = latestRecordReportPath;
      persistResolvedReportFile(reportFile);
    }
    if (reportFile) {
      try {
        var reportResponse = await fetch(gradingReportPath(reportFile, taskId), { headers: { "Accept": "application/json" } });
        if (reportResponse.ok) {
          var reportPayload = await reportResponse.json();
          var reportData = reportPayload && reportPayload.data ? reportPayload.data : {};
          renderReportSummary(reportData, taskId, "GET /api/grading/report?file={file}&taskId={id}");
          await loadGradingResultPreview(reportFile, taskId);
          await loadGradingEvidenceReadiness(reportFile, taskId);
          if (reportData.report && reportData.report.mode === "GRADING_EVIDENCE_AUTO_REPORT") {
            renderReviewDecisionHints(reportData.reviewDecisionHints || {});
            renderReviewDecisionNotes(reportData.reviewDecisionNotes || {});
            applyAutoEvidenceReport(
              reportData.report,
              "GET /api/grading/report?file={file}.report",
              reportData.reviewDecisionNotes || {}
            );
            return;
          }
          if (reportData.mergedGradingEvidence && reportData.mergedGradingEvidence.visible === true) {
            if (reportData.reviewDecisionHints) {
              reportData.mergedGradingEvidence.reviewDecisionHints = reportData.reviewDecisionHints;
            }
            if (reportData.reviewDecisionNotes) {
              reportData.mergedGradingEvidence.reviewDecisionNotes = reportData.reviewDecisionNotes;
            }
            applyMergedEvidence(reportData.mergedGradingEvidence, taskId, "GET /api/grading/report?file={file}&taskId={id}.mergedGradingEvidence");
            return;
          }
          setText(
            "merged-evidence-api-status",
            "apiStatus=GRADING_REPORT_LOADED_WITHOUT_MERGED_EVIDENCE · dynamicSource=GET /api/grading/report?file={file}&taskId={id}.mergedGradingEvidence · taskId=" + taskId + " · fallback=GET /api/review-tasks/{id}"
          );
        } else {
          setText(
            "merged-evidence-api-status",
            "apiStatus=GRADING_REPORT_LOAD_FAILED · status=" + reportResponse.status + " · fallback=GET /api/review-tasks/{id}"
          );
        }
      } catch (error) {
        setText(
          "merged-evidence-api-status",
          "apiStatus=GRADING_REPORT_LOAD_FAILED · reason=fetch_error · fallback=GET /api/review-tasks/{id}"
        );
      }
    }
    try {
      var response = await fetch(detailPath(taskId), { headers: { "Accept": "application/json" } });
      if (!response.ok) {
        setText("merged-evidence-api-status", "apiStatus=DETAIL_LOAD_FAILED · status=" + response.status + " · fallback=STATIC_HTML");
        return;
      }
      var payload = await response.json();
      var detail = payload && payload.data ? payload.data.reviewDetail : null;
      var detailEvidence = detail && detail.mergedGradingEvidence ? detail.mergedGradingEvidence : null;
      if (detailEvidence && detail && detail.reviewDecisionNotes) {
        detailEvidence.reviewDecisionNotes = detail.reviewDecisionNotes;
      }
      applyGradingRecordReviewFromDetail(detail, taskId);
      applyMergedEvidence(detailEvidence, taskId, "GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence");
    } catch (error) {
      setText("merged-evidence-api-status", "apiStatus=DETAIL_LOAD_FAILED · reason=fetch_error · fallback=STATIC_HTML");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadMergedEvidence);
  } else {
    loadMergedEvidence();
  }
})();
