(function () {
  "use strict";

  var state = {
    summaryPath: "/api/review-task-summary?limit=3&detailMode=light",
    detailPathTemplate: "/api/review-tasks/{id}",
    backendCoreTaskPathTemplate: "/api/backend/core-tasks/{id}",
    coreReadinessPathTemplate: "/api/review-tasks/{id}/core-readiness",
    decisionNotePathTemplate: "/api/review-tasks/{id}/decision-note",
    workflowReportPathTemplate: "/api/workflow/report?file={file}",
    evidenceAutoPath: "/api/grading/evidence-auto",
    evidenceAutoDefaults: {
      grading: "examples/output/real-llm-grading.json",
      submission: "examples/submissions/readonly-demo",
      output: "examples/output/grading-evidence-auto.json",
      taskId: "real_demo_grading"
    },
    selectedTaskId: "",
    suggestedDecision: null,
    lastSuggestedCliCommand: "",
    lastAgentReportSuggestedCliCommand: "",
    lastSuggestedReviewUrl: "",
    loadedFromApi: false,
    fallbackMode: "STATIC_HTML_FALLBACK",
    agentEntityRefreshRequested: false,
    coreDbPath: "",
    gradingDbPath: ""
  };
  var AGENT_CORE_NEXT_TOOL_OUTPUT_PREFIX = "examples/output/demo-agent-core-next-tool-execution-";
  var AGENT_CORE_NEXT_TOOL_OUTPUT_ARG_PREFIX = " --output examples/output/demo-agent-core-next-tool-execution-";

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

  function clearNode(id) {
    var node = byId(id);
    if (node) {
      node.innerHTML = "";
    }
    return node;
  }

  function primitiveText(value) {
    if (value === null || typeof value === "undefined") {
      return "none";
    }
    if (Array.isArray(value)) {
      return "array(" + value.length + ")";
    }
    if (typeof value === "object") {
      return "object";
    }
    return String(value);
  }

  function objectSummary(value, limit) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return primitiveText(value);
    }
    var keys = Object.keys(value).slice(0, limit || 6);
    if (!keys.length) {
      return "empty";
    }
    return keys.map(function (key) {
      return key + "=" + primitiveText(value[key]);
    }).join(" · ");
  }

  function replaceGuidePlaceholders(value, taskId) {
    if (Array.isArray(value)) {
      return value.map(function (item) {
        return replaceGuidePlaceholders(item, taskId);
      });
    }
    if (value && typeof value === "object") {
      var result = {};
      Object.keys(value).forEach(function (key) {
        result[key] = replaceGuidePlaceholders(value[key], taskId);
      });
      return result;
    }
    if (value === "<taskId>") {
      return taskId || "";
    }
    if (value === "<reviewer>") {
      return "teacher_1";
    }
    return value;
  }

  function hasGuidePlaceholder(value) {
    if (Array.isArray(value)) {
      return value.some(hasGuidePlaceholder);
    }
    if (value && typeof value === "object") {
      return Object.keys(value).some(function (key) {
        return hasGuidePlaceholder(value[key]);
      });
    }
    return typeof value === "string" && value.charAt(0) === "<" && value.charAt(value.length - 1) === ">";
  }

  function buildNextSingleStepGuide(report, recommendation) {
    var taskId = report && report.taskId ? report.taskId : state.selectedTaskId;
    var outputPath = taskId ? AGENT_CORE_NEXT_TOOL_OUTPUT_PREFIX + taskId + ".json" : "";
    var args = replaceGuidePlaceholders(recommendation.argumentsPreview || {}, taskId);
    var requiresAdditionalArguments = hasGuidePlaceholder(args);
    var canContinue = recommendation.toolAvailable === true
      && recommendation.toolName
      && recommendation.autoExecuteAllowed === false
      && !requiresAdditionalArguments;
    var manualCommand = recommendation.cliCommand || "";
    if (manualCommand) {
      manualCommand = manualCommand
        .replace(/<reviewer>/g, "teacher_1")
        .replace(/<content_quality_revision_comment>/g, "\"请根据内容质量摘要修订后再进入导入预览\"");
    } else if (recommendation.reasonCode === "CONTENT_QUALITY_REVISION_REQUIRED") {
      manualCommand = "python lab_cli.py review revision-request --task-id "
        + taskId
        + " --reviewer teacher_1 --comment \"请根据内容质量摘要修订后再进入导入预览\" --priority HIGH";
    } else if (recommendation.reasonCode === "CONTENT_QUALITY_REVISION_REGENERATION_PENDING") {
      manualCommand = "recommendedTool=regenerate_from_revision_mock";
    }
    var command = canContinue
      ? "python lab_cli.py agent real-demo execute-core-next-tool --task-id "
        + taskId
        + " --reviewer teacher_1 --arguments "
        + JSON.stringify(args)
        + AGENT_CORE_NEXT_TOOL_OUTPUT_ARG_PREFIX + taskId + ".json"
        + " --confirm-execute-recommended-tool"
      : (manualCommand || "manualAction=" + (recommendation.recommendedNextAction || "open_review_detail"));
    return {
      canContinueWithSameCommand: canContinue,
      taskId: taskId,
      nextToolName: recommendation.toolName || "manual_action",
      reasonCode: recommendation.reasonCode || "NO_RECOMMENDATION",
      actionType: recommendation.actionType || "manual_action",
      requiresHumanManualAction: recommendation.toolAvailable !== true,
      requiresAdditionalArguments: requiresAdditionalArguments,
      suggestedCliCommand: command,
      suggestedOutputPath: outputPath,
      suggestedArguments: args,
      contentQualityReadiness: recommendation.contentQualityReadiness || {}
    };
  }

  function buildReviewCenterAgentReportUrl(taskId, reportPath) {
    if (!taskId || !reportPath) {
      return "";
    }
    var url = new URL(window.location.href);
    url.searchParams.set("taskId", taskId);
    url.searchParams.set("agentReport", reportPath);
    return url.pathname + url.search + url.hash;
  }

  function setCoreNextStepCopyStatus(commandAvailable, detail) {
    setText(
      "review-detail-core-next-step-copy-status",
      "copyCommandEnabled=" + boolText(commandAvailable)
        + " · commandExecuted=false"
        + " · stateChanged=false"
        + " · " + (detail || "copyStatus=idle")
    );
  }

  function setCoreReviewUrlCopyStatus(urlAvailable, detail) {
    setText(
      "review-detail-core-review-url-copy-status",
      "copyReviewUrlEnabled=" + boolText(urlAvailable)
        + " · commandExecuted=false"
        + " · stateChanged=false"
        + " · " + (detail || "copyStatus=idle")
    );
  }

  function applyCoreReviewUrlCopyGuide(guide) {
    var url = guide && guide.canContinueWithSameCommand === true
      ? buildReviewCenterAgentReportUrl(guide.taskId || state.selectedTaskId, guide.suggestedOutputPath)
      : "";
    var button = byId("review-detail-core-review-url-copy");
    state.lastSuggestedReviewUrl = url || "";
    if (button) {
      button.disabled = !state.lastSuggestedReviewUrl;
      button.setAttribute("aria-disabled", boolText(!state.lastSuggestedReviewUrl));
      button.setAttribute("data-url-available", boolText(!!state.lastSuggestedReviewUrl));
    }
    setCoreReviewUrlCopyStatus(
      !!state.lastSuggestedReviewUrl,
      state.lastSuggestedReviewUrl ? "copyStatus=ready" : "copyStatus=waiting_for_recommendation"
    );
  }

  function applyCoreNextStepCopyGuide(guide) {
    var command = guide && guide.canContinueWithSameCommand === true
      ? guide.suggestedCliCommand
      : "";
    var button = byId("review-detail-core-next-step-copy");
    state.lastSuggestedCliCommand = command || "";
    if (button) {
      button.disabled = !state.lastSuggestedCliCommand;
      button.setAttribute("aria-disabled", boolText(!state.lastSuggestedCliCommand));
      button.setAttribute("data-command-available", boolText(!!state.lastSuggestedCliCommand));
    }
    setCoreNextStepCopyStatus(
      !!state.lastSuggestedCliCommand,
      state.lastSuggestedCliCommand ? "copyStatus=ready" : "copyStatus=waiting_for_recommendation"
    );
    applyCoreReviewUrlCopyGuide(guide || {});
  }

  function fallbackCopyText(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "readonly");
    area.style.position = "fixed";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    try {
      return document.execCommand("copy");
    } finally {
      document.body.removeChild(area);
    }
  }

  function copySuggestedCoreNextCommand() {
    var command = state.lastSuggestedCliCommand || "";
    if (!command) {
      setCoreNextStepCopyStatus(false, "copyStatus=no_command");
      return;
    }
    function markCopied(ok, label) {
      setCoreNextStepCopyStatus(
        true,
        "copyStatus=" + (ok ? "copied" : "failed")
          + " · method=" + label
          + " · readOnlyCopyOnly=true"
      );
    }
    if (typeof navigator !== "undefined" && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(command)
        .then(function () {
          markCopied(true, "navigator.clipboard.writeText");
        })
        .catch(function () {
          markCopied(fallbackCopyText(command), "document.execCommand(copy)");
        });
      return;
    }
    markCopied(fallbackCopyText(command), "document.execCommand(copy)");
  }

  function copySuggestedCoreReviewUrl() {
    var url = state.lastSuggestedReviewUrl || "";
    if (!url) {
      setCoreReviewUrlCopyStatus(false, "copyStatus=no_url");
      return;
    }
    function markCopied(ok, label) {
      setCoreReviewUrlCopyStatus(
        true,
        "copyStatus=" + (ok ? "copied" : "failed")
          + " · method=" + label
          + " · readOnlyCopyOnly=true"
      );
    }
    if (typeof navigator !== "undefined" && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url)
        .then(function () {
          markCopied(true, "navigator.clipboard.writeText");
        })
        .catch(function () {
          markCopied(fallbackCopyText(url), "document.execCommand(copy)");
        });
      return;
    }
    markCopied(fallbackCopyText(url), "document.execCommand(copy)");
  }

  function setAgentReportNextStepCopyStatus(commandAvailable, detail) {
    setText(
      "review-detail-agent-core-next-step-copy-status",
      "copyAgentReportCommandEnabled=" + boolText(commandAvailable)
        + " · commandExecuted=false"
        + " · stateChanged=false"
        + " · " + (detail || "copyStatus=idle")
    );
  }

  function applyAgentReportNextStepCopyGuide(guide) {
    var command = guide && guide.canContinueWithSameCommand === true
      ? guide.suggestedCliCommand
      : "";
    var button = byId("review-detail-agent-core-next-step-copy");
    state.lastAgentReportSuggestedCliCommand = command || "";
    if (button) {
      button.disabled = !state.lastAgentReportSuggestedCliCommand;
      button.setAttribute("aria-disabled", boolText(!state.lastAgentReportSuggestedCliCommand));
      button.setAttribute("data-command-available", boolText(!!state.lastAgentReportSuggestedCliCommand));
    }
    setAgentReportNextStepCopyStatus(
      !!state.lastAgentReportSuggestedCliCommand,
      state.lastAgentReportSuggestedCliCommand
        ? "copyStatus=ready_from_agent_report"
        : "copyStatus=waiting_for_agent_report_next_step"
    );
  }

  function copyAgentReportSuggestedCoreNextCommand() {
    var command = state.lastAgentReportSuggestedCliCommand || "";
    if (!command) {
      setAgentReportNextStepCopyStatus(false, "copyStatus=no_command");
      return;
    }
    function markCopied(ok, label) {
      setAgentReportNextStepCopyStatus(
        true,
        "copyStatus=" + (ok ? "copied" : "failed")
          + " · method=" + label
          + " · readOnlyCopyOnly=true"
      );
    }
    if (typeof navigator !== "undefined" && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(command)
        .then(function () {
          markCopied(true, "navigator.clipboard.writeText");
        })
        .catch(function () {
          markCopied(fallbackCopyText(command), "document.execCommand(copy)");
        });
      return;
    }
    markCopied(fallbackCopyText(command), "document.execCommand(copy)");
  }

  function appendPill(parent, value, strong) {
    var pill = document.createElement("span");
    pill.className = strong ? "pill strong" : "pill";
    pill.textContent = String(value);
    parent.appendChild(pill);
  }

  function appendSignalItem(parent, rank, titleText, pills, bodyText) {
    var item = document.createElement("div");
    item.className = "signal-item";

    var title = document.createElement("h3");
    var rankNode = document.createElement("span");
    rankNode.className = "priority-rank";
    rankNode.textContent = String(rank);
    title.appendChild(rankNode);
    title.appendChild(document.createTextNode(" " + titleText));
    item.appendChild(title);

    if (pills && pills.length) {
      var meta = document.createElement("div");
      meta.className = "meta-row";
      pills.forEach(function (pill, index) {
        appendPill(meta, pill, index === 0);
      });
      item.appendChild(meta);
    }

    var body = document.createElement("p");
    body.textContent = bodyText;
    item.appendChild(body);
    parent.appendChild(item);
    return item;
  }

  function agentEntityKind(value) {
    if (value === "lab_template") {
      return "lab";
    }
    if (value === "exam_question") {
      return "exam";
    }
    if (value === "grading_rule") {
      return "grading";
    }
    if (value === "ppt_deck") {
      return "ppt";
    }
    return "";
  }

  function agentEntityHref(entityId, sourceTaskId, entityType, action) {
    var params = new URLSearchParams();
    params.set("entityId", entityId || "");
    params.set("sourceTaskId", sourceTaskId || "");
    params.set("entityKind", agentEntityKind(entityType) || "");
    if (action) {
      params.set("action", action);
    }
    appendLocalContextParams(params);
    return "agent-entities.html?" + params.toString();
  }

  function agentEntityActivitySummary(item) {
    var activity = item && item.importActivity ? item.importActivity : {};
    var summary = activity.summary || {};
    var latestDryRun = activity.latestDryRun || {};
    var latestSend = activity.latestSend || {};
    var latestStatusQuery = activity.latestStatusQuery || {};
    var latestResult = activity.latestResult || {};
    var latestSignoff = activity.latestSignoff || {};
    return "activitySummary"
      + " · latestDryRunArtifact=" + (latestDryRun.artifactId || latestDryRun.id || "none")
      + " · latestSendStatusCode=" + (summary.latestStatusCode || latestSend.statusCode || "none")
      + " · latestStatusQuery=" + (summary.latestQueriedPlatformStatus || latestStatusQuery.agentStatus || "none")
      + " · latestResultStatus=" + (summary.latestPlatformStatus || latestResult.agentStatus || item.latestPlatformStatus || "none")
      + " · agentDraftId=" + (summary.latestPlatformDraftId || latestResult.agentDraftId || "none")
      + " · signoffRecorded=" + boolText(summary.signoffRecorded === true || latestSignoff.signoffRecorded === true)
      + " · secretValueReturned=false"
      + " · autoPublishAllowed=false";
  }

  function postSignoffChecklistSummary(item) {
    var checklist = item && item.postSignoffPrePublishChecklist ? item.postSignoffPrePublishChecklist : {};
    if (!checklist || !checklist.component) {
      return "postSignoffPrePublishChecklist=none";
    }
    var safety = checklist.safety || {};
    var focus = checklist.entitySpecificReviewFocus || {};
    return "postSignoffPrePublishChecklist=" + (checklist.status || "UNKNOWN")
      + " · component=" + (checklist.component || "AgentEntityPostSignoffPrePublishChecklist")
      + " · nextRequiredAction=" + (checklist.nextRequiredAction || "final_human_publish_review_before_any_real_publish")
      + " · postSignoffMatched=" + (checklist.matchedTotal || 0) + "/" + (checklist.total || 0)
      + " · entitySpecificReviewFocus=" + (focus.primaryReviewFocus || "none")
      + " · entitySpecificMatched=" + (focus.matchedTotal || 0) + "/" + (focus.total || 0)
      + " · finalHumanReviewRequired=" + boolText(safety.requiresFinalHumanReview === true)
      + " · realPublish=" + boolText(safety.realPublish === true);
  }

  function finalPublishReviewDecisionSummary(item) {
    var decision = item && item.finalPublishReviewDecision ? item.finalPublishReviewDecision : {};
    var safety = decision.safety || {};
    if (!decision || !decision.component) {
      return "finalPublishReviewDecision=none · autoPublishAllowed=false · realPublish=false";
    }
    return "finalPublishReviewDecision=" + (decision.decision || "NOT_RECORDED")
      + " · recorded=" + boolText(decision.recorded === true)
      + " · approvedForPublishPlanning=" + boolText(decision.approvedForPublishPlanning === true)
      + " · needsRevision=" + boolText(decision.needsRevision === true)
      + " · artifactId=" + (decision.artifactId || "none")
      + " · requestSent=" + boolText(safety.requestSent === true)
      + " · autoPublishAllowed=" + boolText(safety.autoPublishAllowed === true)
      + " · realPublish=" + boolText(safety.realPublish === true);
  }

  function readinessItemByEntityId(readinessReport) {
    var map = {};
    var items = Array.isArray(readinessReport.items) ? readinessReport.items : [];
    items.forEach(function (item) {
      var id = item.agentEntityId || item.id || "";
      if (id) {
        map[id] = item;
      }
    });
    return map;
  }

  function agentEntitySignoffState(item) {
    if (item && item.signoffState === "READY_FOR_PLATFORM_ENTITY_SIGNOFF") {
      return "READY_FOR_PLATFORM_ENTITY_SIGNOFF";
    }
    return "WAITING_PLATFORM_ENTITY_IMPORT_ACTIVITY";
  }

  function normalizeLocalPath(pathValue) {
    var value = String(pathValue || "").replace(/\\/g, "/");
    var marker = "/examples/";
    var markerIndex = value.lastIndexOf(marker);
    if (markerIndex >= 0) {
      return value.slice(markerIndex + 1);
    }
    if (value.indexOf("examples/") === 0) {
      return value;
    }
    return value;
  }

  function gradingReportHref(reportPath, taskId) {
    var href = "grading-report.html";
    var params = new URLSearchParams();
    if (reportPath) {
      params.set("file", normalizeLocalPath(reportPath));
    }
    if (taskId) {
      params.set("taskId", taskId);
    }
    appendLocalContextParams(params);
    var query = params.toString();
    return query ? href + "?" + query : href;
  }

  function gradingRecordsPath(taskId) {
    var params = new URLSearchParams();
    params.set("taskId", taskId);
    var gradingDbPath = state.gradingDbPath || getQueryGradingDbPath();
    if (gradingDbPath) {
      params.set("dbPath", gradingDbPath);
    }
    return "/api/grading/records?" + params.toString();
  }

  function applyGradingRecordReportLink(taskId, record) {
    var reportPath = record && record.reportPath ? record.reportPath : "";
    if (!taskId || !reportPath) {
      return;
    }
    var href = gradingReportHref(reportPath, taskId);
    setWorkspaceLink("mvp-workspace-grading-report-link", href, "打开评分报告", true);
    setText(
      "mvp-workspace-evidence-state",
      "gradingRecord=true · latestReportPath=" + normalizeLocalPath(reportPath)
    );
    var link = byId("review-detail-grading-report-entry-link");
    var summaryNode = byId("review-detail-grading-report-entry-summary");
    if (link) {
      link.href = href;
      link.textContent = "打开评分报告";
      link.removeAttribute("aria-disabled");
      link.title = "GET /api/grading/records?taskId={id}.latest.reportPath";
    }
    if (summaryNode) {
      summaryNode.textContent = "source=GET /api/grading/records?taskId={id}.latest.reportPath"
        + " · latestReportPath=" + normalizeLocalPath(reportPath)
        + " · taskId=" + taskId
        + " · entryHref=" + href
        + " · autoApproveAllowed=false · realPublishAllowed=false";
    }
  }

  function loadGradingRecordReportLink(taskId) {
    if (!taskId) {
      return Promise.resolve(null);
    }
    return safeFetchJson(gradingRecordsPath(taskId))
      .then(function (payload) {
        var items = payload && payload.data && Array.isArray(payload.data.items) ? payload.data.items : [];
        var latest = items[0] || null;
        applyGradingRecordReportLink(taskId, latest);
        return latest;
      })
      .catch(function () {
        return null;
      });
  }

  function reviewPageHref(kind, taskId) {
    if (!taskId) {
      return "";
    }
    var pageByKind = {
      lab: "lab-review.html",
      exam: "exam-review.html",
      grading: "grading-review.html",
      ppt: "ppt-review.html"
    };
    var page = pageByKind[kind] || "review-center.html";
    var params = new URLSearchParams();
    params.set("taskId", taskId);
    var agentReport = getQueryAgentReport();
    var coreDbPath = state.coreDbPath || getQueryCoreDbPath();
    var workflowRunId = getQueryWorkflowRunId();
    if (agentReport) {
      params.set("agentReport", agentReport);
    }
    if (coreDbPath) {
      params.set("coreDbPath", coreDbPath);
    }
    if (workflowRunId) {
      params.set("workflowRunId", workflowRunId);
    }
    if (state.gradingDbPath || getQueryGradingDbPath()) {
      params.set("gradingDbPath", state.gradingDbPath || getQueryGradingDbPath());
    }
    return page + "?" + params.toString();
  }

  function workflowReportHref(reportPath) {
    if (!reportPath) {
      return "";
    }
    return state.workflowReportPathTemplate.replace("{file}", encodeURIComponent(normalizeLocalPath(reportPath)));
  }

  function reviewDetailHref(taskId) {
    if (!taskId) {
      return "";
    }
    var params = new URLSearchParams();
    params.set("taskId", taskId);
    var agentReport = getQueryAgentReport();
    var coreDbPath = state.coreDbPath || getQueryCoreDbPath();
    var workflowRunId = getQueryWorkflowRunId();
    if (agentReport) {
      params.set("agentReport", agentReport);
    }
    if (coreDbPath) {
      params.set("coreDbPath", coreDbPath);
    }
    if (workflowRunId) {
      params.set("workflowRunId", workflowRunId);
    }
    if (state.gradingDbPath || getQueryGradingDbPath()) {
      params.set("gradingDbPath", state.gradingDbPath || getQueryGradingDbPath());
    }
    return "review-center.html?" + params.toString();
  }

  function artifactHref(item, taskId) {
    var kind = item && item.kind ? String(item.kind) : "";
    var path = item && item.path ? String(item.path) : "";
    if (!path && taskId) {
      return reviewDetailHref(taskId);
    }
    if (kind === "WORKFLOW_REPORT") {
      return workflowReportHref(path);
    }
    if (kind.indexOf("GRADING_EVIDENCE") >= 0 || kind.indexOf("GRADING_REPORT") >= 0) {
      return gradingReportHref(path, taskId);
    }
    if (/_DSL$/.test(kind)) {
      return reviewDetailHref(taskId);
    }
    return "";
  }

  function reviewKindFromRealDemoItem(item) {
    var taskType = String(item && item.taskType ? item.taskType : "").toUpperCase();
    var artifactKind = String(item && item.artifactKind ? item.artifactKind : "").toUpperCase();
    var taskId = String(item && item.taskId ? item.taskId : "").toLowerCase();
    var value = taskType + " " + artifactKind + " " + taskId;
    if (value.indexOf("LAB") >= 0) {
      return "lab";
    }
    if (value.indexOf("EXAM") >= 0) {
      return "exam";
    }
    if (value.indexOf("GRADING") >= 0) {
      return "grading";
    }
    if (value.indexOf("PPT") >= 0) {
      return "ppt";
    }
    return "";
  }

  function reviewPageLabel(kind) {
    if (kind === "lab") {
      return "打开 Lab 审核";
    }
    if (kind === "exam") {
      return "打开 Exam 审核";
    }
    if (kind === "grading") {
      return "打开 Grading 审核";
    }
    if (kind === "ppt") {
      return "打开 PPT 审核";
    }
    return "打开审核页";
  }

  function setWorkspaceLink(id, href, label, enabled) {
    var link = byId(id);
    if (!link) {
      return;
    }
    link.href = href || "#";
    if (label) {
      link.textContent = label;
    }
    if (enabled === false || !href) {
      link.setAttribute("aria-disabled", "true");
    } else {
      link.removeAttribute("aria-disabled");
    }
  }

  function refreshMvpWorkspaceContextLinks(taskId) {
    var currentTaskId = taskId || state.selectedTaskId || getQueryTaskId() || "";
    if (!currentTaskId) {
      return;
    }
    setWorkspaceLink(
      "mvp-workspace-review-link",
      reviewDetailHref(currentTaskId),
      "打开当前审核页",
      true
    );
    setWorkspaceLink(
      "mvp-workspace-grading-report-link",
      "",
      "等待评分 evidence",
      false
    );
  }

  function reviewKindFromTask(task, preview) {
    var taskType = String(task && task.taskType ? task.taskType : "").toUpperCase();
    var previewKind = String(preview && preview.kind ? preview.kind : "").toUpperCase();
    var artifactKind = String(preview && preview.artifactKind ? preview.artifactKind : "").toUpperCase();
    var finalResultPath = String(task && task.finalResultPath ? task.finalResultPath : "").toUpperCase();
    var taskId = String(task && task.id ? task.id : "").toUpperCase();
    var value = [taskType, previewKind, artifactKind, finalResultPath, taskId].join(" ");
    if (taskType.indexOf("GRADING") >= 0 || previewKind === "GRADING" || artifactKind.indexOf("GRADING") >= 0) {
      return "grading";
    }
    if (taskType.indexOf("PPT") >= 0 || previewKind === "PPT" || artifactKind.indexOf("PPT") >= 0) {
      return "ppt";
    }
    if (taskType.indexOf("EXAM") >= 0 || previewKind === "EXAM" || artifactKind.indexOf("EXAM") >= 0) {
      return "exam";
    }
    if (taskType.indexOf("LAB") >= 0 || previewKind === "LAB" || artifactKind.indexOf("LAB") >= 0) {
      return "lab";
    }
    if (value.indexOf("GRADING") >= 0) {
      return "grading";
    }
    if (value.indexOf("PPT") >= 0) {
      return "ppt";
    }
    return "";
  }

  function workspaceImportState(detail) {
    var actions = reviewPageValue(detail, "platformImportPreviewActions");
    var preview = reviewPageValue(detail, "platformImportPreview");
    var signoff = reviewPageValue(detail, "platformImportPreviewSignoff");
    var readiness = reviewPageValue(detail, "agentEntityReadinessReport");
    var actionItems = Array.isArray(actions.items) ? actions.items : [];
    var previewItems = Array.isArray(preview.items) ? preview.items : [];
    var readinessItems = Array.isArray(readiness.items) ? readiness.items : [];
    var previewTotal = preview.total || previewItems.length || 0;
    var previewCreatedTotal = actions.previewAlreadyCreatedTotal || actionItems.filter(function (item) {
      return item.previewAlreadyCreated === true;
    }).length;
    var readyForSignoff = signoff.readyForHumanSignoff === true;
    var readinessReadyTotal = readiness.readyTotal || readinessItems.filter(function (item) {
      return item.ready === true || item.readyForSignoff === true || item.signoffRecorded === true;
    }).length;
    if (readyForSignoff) {
      return "signoffReady=true · previewTotal=" + previewTotal;
    }
    if (previewTotal > 0) {
      return "previewTotal=" + previewTotal + " · readinessReadyTotal=" + readinessReadyTotal;
    }
    if (previewCreatedTotal > 0) {
      return "previewAlreadyCreatedTotal=" + previewCreatedTotal;
    }
    if (actionItems.length) {
      return "previewActions=" + actionItems.length + " · previewWaiting=true";
    }
    return "previewWaiting=true";
  }

  function workspaceEvidenceStateFromSummary(summary) {
    var readiness = summary && summary.gradingEvidenceReadinessSignal
      ? summary.gradingEvidenceReadinessSignal
      : {};
    var merged = summary && summary.mergedGradingEvidenceReviewSignal
      ? summary.mergedGradingEvidenceReviewSignal
      : {};
    var controlled = summary && summary.controlledDockerEvidenceReviewSignal
      ? summary.controlledDockerEvidenceReviewSignal
      : {};
    if (readiness.enabled === true || readiness.availableTotal) {
      return "evidenceReadyTotal=" + (readiness.evidenceReadyTotal || 0)
        + " · missingEvidenceTotal=" + (readiness.missingEvidenceTotal || 0);
    }
    if (merged.available === true) {
      return "mergedEvidence=true · coverageRatio=" + primitiveText(merged.coverageRatio);
    }
    if (controlled.available === true) {
      return "controlledEvidence=" + (controlled.executed || 0) + "/" + (controlled.totalControlledScore || controlled.executed || 0);
    }
    return "waiting";
  }

  function applyMvpReviewWorkspaceFromSummary(summary) {
    var queue = summary && summary.realDemoReviewQueue ? summary.realDemoReviewQueue : {};
    var items = Array.isArray(queue.items) ? queue.items : [];
    var total = queue.taskTotal || queue.localArtifactTotal || items.length || 0;
    var schemaTotal = queue.schemaValidatedTotal || items.filter(function (item) {
      return item.schemaValidated === true;
    }).length;
    var waitingTotal = queue.waitingReviewTotal || items.filter(function (item) {
      return item.status === "WAITING_REVIEW";
    }).length;
    var dynamicTaskTotal = queue.dynamicTaskTotal || items.filter(function (item) {
      return item.dynamicTaskAvailable === true || item.syntheticTaskAvailable === true;
    }).length;
    var displayTotal = total || schemaTotal || waitingTotal || 0;
    setText("mvp-workspace-real-dsl-total", schemaTotal + "/" + displayTotal);
    setText(
      "mvp-workspace-summary",
      "source=GET /api/review-task-summary.mvpReviewWorkspace"
        + " · sourceMode=" + (queue.sourceMode || "STATIC_OR_API")
        + " · waitingReviewTotal=" + waitingTotal
        + " · schemaValidatedTotal=" + schemaTotal
        + " · dynamicTaskTotal=" + dynamicTaskTotal
        + " · readOnly=true"
    );
    setText(
      "mvp-workspace-evidence-state",
      workspaceEvidenceStateFromSummary(summary)
    );
    setText(
      "mvp-workspace-safety",
      "autoApproveAllowed=false · realPublishAllowed=false · commandExecuted=false · source=summary"
    );
  }

  function applyMvpReviewWorkspaceFromDetail(detail) {
    var task = detail && detail.task ? detail.task : {};
    var page = detail && detail.reviewPage ? detail.reviewPage : {};
    var preview = page.dslPreview || {};
    var policy = detail && detail.reviewPolicy ? detail.reviewPolicy : {};
    var safety = detail && detail.safety ? detail.safety : {};
    var evidence = detail && detail.mergedGradingEvidence ? detail.mergedGradingEvidence : {};
    var evidenceSummary = evidence.summary || {};
    var latestReport = evidence.latestReport || {};
    var latestReportPath = evidenceSummary.latestReportPath || latestReport.artifactPath || latestReport.reportPath || "";
    var taskId = task.id || state.selectedTaskId || "";
    var kind = reviewKindFromTask(task, preview);
    var reviewHref = kind ? reviewPageHref(kind, taskId) : reviewDetailHref(taskId);
    var reportHref = latestReportPath ? gradingReportHref(latestReportPath, taskId) : "";
    var evidenceState = evidence.visible === true
      ? "mergedEvidence=true · latestReportPath=" + normalizeLocalPath(latestReportPath || "none")
      : "mergedEvidence=false · next=run_grade_evidence_auto";
    setText("mvp-workspace-state", task.status || policy.generatedContentStatus || "WAITING_REVIEW");
    setText("mvp-workspace-selected-task", taskId || "none");
    setText("mvp-workspace-evidence-state", evidenceState);
    setText("mvp-workspace-import-state", workspaceImportState(detail));
    setText(
      "mvp-workspace-summary",
      "source=GET /api/review-tasks/{id}.mvpReviewWorkspace"
        + " · taskType=" + (task.taskType || "UNKNOWN_TASK")
        + " · dslKind=" + (preview.kind || "UNKNOWN_DSL")
        + " · schemaValidated=" + boolText(preview.schemaValidated === true)
        + " · candidateAnswerVisible=" + boolText(((preview.candidateSafety || {}).answerVisibleToCandidate) === true)
        + " · readOnly=true"
    );
    setWorkspaceLink("mvp-workspace-review-link", reviewHref, reviewPageLabel(kind), !!reviewHref);
    setWorkspaceLink(
      "mvp-workspace-grading-report-link",
      reportHref,
      reportHref ? "打开评分报告" : "等待评分 evidence",
      !!reportHref
    );
    setText(
      "mvp-workspace-safety",
      "autoApproveAllowed=" + boolText(policy.autoApproveAllowed === true)
        + " · realPublishAllowed=" + boolText(policy.realPublishAllowed === true)
        + " · sandboxExecuted=" + boolText(safety.sandboxExecuted === true)
        + " · commandExecuted=false"
    );
  }

  function applyMvpReviewWorkspaceFromCoreReadiness(report, nextAction, status, readyTotal, stepTotal) {
    var summary = report && report.summary ? report.summary : {};
    var importPending = summary.platformImportPreviewPendingTotal || 0;
    setText("mvp-workspace-state", status || "CORE_DEMO_NEEDS_ACTION");
    setText(
      "mvp-workspace-next-action",
      "nextAction=" + (nextAction || "manual_review_required")
        + " · ready=" + readyTotal + "/" + stepTotal
    );
    if (importPending || typeof summary.platformImportPreviewPendingTotal !== "undefined") {
      setText(
        "mvp-workspace-import-state",
        "importPreviewPendingTotal=" + importPending
          + " · platformRequiredTotal=" + (summary.platformRequiredTotal || 0)
      );
    }
  }

  function updateRealDemoReviewPageLink(kind, taskId) {
    var href = reviewPageHref(kind, taskId);
    var link = byId("real-demo-" + kind + "-review-link");
    var label = byId("real-demo-" + kind + "-review-entry-href");
    if (link && href) {
      link.href = href;
      link.textContent = reviewPageLabel(kind);
      link.title = "GET /api/review-tasks/{id}?agentReport={workflowReport}";
      link.setAttribute("data-agent-report-preserved", boolText(!!getQueryAgentReport()));
      link.setAttribute("data-core-db-path-preserved", boolText(!!(state.coreDbPath || getQueryCoreDbPath())));
    }
    if (label && href) {
      label.textContent = "entryHref=" + href;
    }
    return href;
  }

  function refreshStaticRealDemoReviewLinks() {
    [
      ["lab", "real_demo_lab"],
      ["exam", "real_demo_exam"],
      ["grading", "real_demo_grading"],
      ["ppt", "real_demo_ppt"]
    ].forEach(function (pair) {
      updateRealDemoReviewPageLink(pair[0], pair[1]);
    });
  }

  function artifactLinkLabel(item) {
    var kind = item && item.kind ? String(item.kind) : "";
    if (kind === "WORKFLOW_REPORT") {
      return "打开 Workflow Report";
    }
    if (kind.indexOf("GRADING_EVIDENCE") >= 0 || kind.indexOf("GRADING_REPORT") >= 0) {
      return "打开评分报告";
    }
    if (/_DSL$/.test(kind)) {
      return "打开 DSL Preview";
    }
    return "打开产物";
  }

  function updateEvidenceAutoReportLink(reportPath, taskId) {
    var link = byId("run-evidence-auto-report-link");
    if (!link) {
      return;
    }
    link.href = gradingReportHref(reportPath || state.evidenceAutoDefaults.output, taskId || state.evidenceAutoDefaults.taskId);
    link.textContent = "打开最新证据报告";
  }

  function applyEvidenceAutoSuccess(data) {
    var report = data.gradingEvidenceAutoReport || data.report || {};
    var reportPath = data.reportPath || report.reportPath || state.evidenceAutoDefaults.output;
    var taskId = data.taskId || state.evidenceAutoDefaults.taskId;
    var summary = report.summary || report.executionSummary || report.checkSummary || {};
    var steps = Array.isArray(report.steps) ? report.steps : [];
    var warnings = Array.isArray(report.warnings) ? report.warnings : [];
    var checkItems = Array.isArray(report.checkEvidenceReviewItems)
      ? report.checkEvidenceReviewItems
      : Array.isArray(report.checks)
      ? report.checks
      : [];
    var executed = summary.executedTotal || summary.executed || 0;
    var passed = summary.passedCheckTotal || summary.passedTotal || summary.passed || 0;
    var failed = summary.failedCheckTotal || summary.failedTotal || summary.failed || 0;
    var earnedScore = summary.earnedScore || 0;
    var totalScore = summary.totalScore || 0;
    var coverageRatio = totalScore ? Math.round((Number(earnedScore || 0) / Number(totalScore || 1)) * 10000) / 10000 : 0;
    var syntheticDetail = {
      task: { id: taskId, taskType: "GRADING_GENERATION" },
      mergedGradingEvidence: {
        visible: true,
        reportTotal: 1,
        latestReportType: report.reportType || "GRADING_EVIDENCE_AUTO",
        latestReportMode: report.mode || "GRADING_EVIDENCE_AUTO_REPORT",
        summary: {
          latestReportPath: reportPath,
          checkEvidenceReviewItemTotal: checkItems.length,
          manualCheckReviewTotal: 0,
          executedTotal: executed,
          passedCheckTotal: passed,
          failedCheckTotal: failed,
          deferredCheckTotal: 0,
          earnedScore: earnedScore,
          totalScore: totalScore,
          coverageRatio: coverageRatio,
          autoEvidenceReport: true,
          autoEvidenceStepTotal: steps.length,
          autoEvidenceWarningTotal: warnings.length
        },
        latestReport: {
          artifactPath: reportPath,
          artifactReportType: report.reportType || "GRADING_EVIDENCE_AUTO",
          mode: report.mode || "GRADING_EVIDENCE_AUTO_REPORT",
          steps: steps,
          warnings: warnings
        },
        checkEvidenceReviewItems: checkItems,
        reviewDecisionHints: {
          overallHint: checkItems.length ? "READY_FOR_MANUAL_REVIEW_DECISION" : "NEEDS_EVIDENCE",
          hintTotal: checkItems.length,
          approveReadyTotal: checkItems.length,
          reviseRequiredTotal: 0,
          evidenceMissingTotal: 0
        },
        safety: {
          mergeExecutedOnlyExistingReports: true,
          sandboxExecuted: false,
          contestantCodeExecuted: false,
          commandExecuted: false,
          pytestExecuted: false,
          networkAllowed: false
        }
      },
      reviewDecisionNotes: { total: 0, latest: {} }
    };
    updateEvidenceAutoReportLink(reportPath, taskId);
    updateGradingReportEntry(syntheticDetail);
    summarizeMergedEvidence({}, syntheticDetail.mergedGradingEvidence);
    applyGradingEvidenceReadiness(syntheticDetail);
    applyPreApproveReviewCheck(syntheticDetail);
    setText(
      "run-evidence-auto-status",
      "OK · reportPath=" + normalizeLocalPath(reportPath)
        + " · readinessUpdated=true"
        + " · reportEntryUpdated=true"
        + " · preApproveWarningRefreshed=true"
        + " · autoApproveAllowed=false"
    );
  }

  function runEvidenceAuto() {
    var button = byId("run-evidence-auto-button");
    if (!window.fetch || !button) {
      setText("run-evidence-auto-status", "fetch unavailable · 请使用 CLI grade evidence-auto");
      return;
    }
    button.disabled = true;
    setText("run-evidence-auto-status", "POST /api/grading/evidence-auto · running");
    fetch(state.evidenceAutoPath, {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      credentials: "same-origin",
      body: JSON.stringify({
        taskId: state.evidenceAutoDefaults.taskId,
        grading: state.evidenceAutoDefaults.grading,
        submission: state.evidenceAutoDefaults.submission,
        output: state.evidenceAutoDefaults.output,
        includeControlledCommand: false,
        failOnControlledUnavailable: false
      })
    })
      .then(function (response) {
        return response.json().then(function (payload) {
          if (!response.ok || !payload || payload.success !== true) {
            var code = payload && payload.code ? payload.code : "HTTP_" + response.status;
            throw new Error(code);
          }
          return payload;
        });
      })
      .then(function (payload) {
        var data = payload.data || {};
        var report = data.gradingEvidenceAutoReport || data.report || {};
        var reportPath = data.reportPath || report.reportPath || state.evidenceAutoDefaults.output;
        var taskId = data.taskId || state.evidenceAutoDefaults.taskId;
        applyEvidenceAutoSuccess(data);
        return loadTaskDetail(taskId, { updateUrl: true });
      })
      .catch(function (error) {
        setText("run-evidence-auto-status", "FAILED · " + error.message + " · 可使用 CLI grade evidence-auto 重试");
      })
      .finally(function () {
        button.disabled = false;
      });
  }

  function setupEvidenceAutoAction() {
    var button = byId("run-evidence-auto-button");
    if (!button) {
      return;
    }
    updateEvidenceAutoReportLink(state.evidenceAutoDefaults.output, state.evidenceAutoDefaults.taskId);
    button.addEventListener("click", runEvidenceAuto);
  }

  function applyGradingEvidenceActionGuide(task, status, missingTotal, actionGuide) {
    var taskId = task.id || state.evidenceAutoDefaults.taskId;
    var guide = actionGuide || {};
    var primaryAction = guide.primaryAction || (
      missingTotal > 0 || status === "NO_MERGED_EVIDENCE_REPORT"
        ? "run_grade_evidence_auto_then_review_report"
        : "review_ready_score_and_evidence_before_approval"
    );
    var cli = guide.cli || ("python lab_cli.py grade evidence-auto --task-id " + taskId + " --include-controlled-command false");
    var api = guide.api || { method: "POST", path: state.evidenceAutoPath };
    var followUp = Array.isArray(guide.followUp) && guide.followUp.length
      ? guide.followUp
      : [
        "open_latest_grading_report",
        "verify_grading_evidence_readiness",
        "record_review_decision_note_before_manual_approve"
      ];
    setText("review-detail-evidence-action-primary", "primaryAction=" + primaryAction);
    setText("review-detail-evidence-action-api", "api=" + (api.method || "POST") + " " + (api.path || state.evidenceAutoPath));
    setText("review-detail-evidence-action-cli", "cli=" + cli);
    setText(
      "review-detail-evidence-action-summary",
      "status=" + (guide.status || status)
        + " · missingEvidenceTotal=" + missingTotal
        + " · followUp=" + followUp.join(",")
        + " · controlledCommandOptInRequired=true"
        + " · autoApproveAllowed=false"
    );
    state.evidenceAutoDefaults.taskId = taskId;
    updateEvidenceAutoReportLink(state.evidenceAutoDefaults.output, taskId);
  }

  function decisionNoteReason(decision) {
    if (state.suggestedDecision && state.suggestedDecision.decision === decision && state.suggestedDecision.reason) {
      return state.suggestedDecision.reason;
    }
    if (decision === "approve-ready") {
      return "reviewDecisionHints indicate all checks are ready for manual approval review.";
    }
    if (decision === "needs-revision") {
      return "Reviewer marked merged grading evidence as requiring DSL or scoring revision.";
    }
    return "Reviewer marked merged grading evidence as requiring additional evidence before approval.";
  }

  function resolveSuggestedDecision() {
    var params = new URLSearchParams(window.location.search || "");
    var decision = params.get("decision") || "";
    if (["approve-ready", "needs-revision", "needs-evidence"].indexOf(decision) >= 0) {
      return {
        decision: decision,
        source: params.get("source") || "url",
        nextCoreAction: params.get("nextCoreAction") || "none",
        reason: params.get("reason") || ""
      };
    }
    return null;
  }

  function suggestedDecisionButtonId(decision) {
    return decision === "approve-ready"
      ? "record-decision-approve-ready-button"
      : decision === "needs-revision"
      ? "record-decision-needs-revision-button"
      : "record-decision-needs-evidence-button";
  }

  function applySuggestedDecision(suggestion) {
    if (!suggestion) {
      return;
    }
    state.suggestedDecision = suggestion;
    ["record-decision-approve-ready-button", "record-decision-needs-revision-button", "record-decision-needs-evidence-button"].forEach(function (id) {
      var item = byId(id);
      if (item) {
        item.classList.remove("primary");
        item.removeAttribute("aria-current");
      }
    });
    var button = byId(suggestedDecisionButtonId(suggestion.decision));
    if (button) {
      button.classList.add("primary");
      button.setAttribute("aria-current", "true");
      button.title = "来自评分报告或 core-readiness 的建议，仍需人工点击确认";
    }
    setText(
      "record-decision-note-status",
      "suggestedDecision=" + suggestion.decision
        + " · source=" + suggestion.source
        + " · nextCoreAction=" + suggestion.nextCoreAction
        + " · reason=" + (suggestion.reason || "use_default_reason")
        + " · manualClickRequired=true"
    );
    setText(
      "review-detail-decision-note-next-step-status",
      "nextRequiredAction=record_" + suggestion.decision + "_decision_note"
    );
    setText(
      "review-detail-decision-note-next-step-summary",
      "suggestedDecision=" + suggestion.decision
        + " · source=" + suggestion.source
        + " · nextCoreAction=" + suggestion.nextCoreAction
        + " · reason=" + (suggestion.reason || "use_default_reason")
        + " · autoApproveAllowed=false"
    );
  }

  function applySuggestedDecisionFromUrl() {
    applySuggestedDecision(resolveSuggestedDecision());
  }

  function decisionFromRecommendation(value) {
    return ["approve-ready", "needs-revision", "needs-evidence"].indexOf(value) >= 0 ? value : "";
  }

  function recordReviewDecisionNote(decision) {
    var taskId = state.selectedTaskId || "";
    var path = state.decisionNotePathTemplate.replace("{id}", encodeURIComponent(taskId));
    if (!window.fetch || !taskId) {
      setText("record-decision-note-status", "taskId unavailable · use CLI review decision-note");
      return;
    }
    setText("record-decision-note-status", "POST /api/review-tasks/{id}/decision-note · running");
    fetch(path, {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      credentials: "same-origin",
      body: JSON.stringify({
        reviewer: "teacher_1",
        decision: decision,
        reason: decisionNoteReason(decision)
      })
    })
      .then(function (response) {
        return response.json().then(function (payload) {
          if (!response.ok || !payload || payload.success !== true) {
            var code = payload && payload.code ? payload.code : "HTTP_" + response.status;
            throw new Error(code);
          }
          return payload;
        });
      })
      .then(function (payload) {
        var data = payload.data || {};
        var note = data.decisionNote || {};
        applyDecisionNoteRecorded(note, data.reviewDetail || null);
        if (data.reviewDetail) {
          applyDetail(data.reviewDetail);
        } else {
          loadTaskDetail(taskId);
        }
      })
      .catch(function (error) {
        setText("record-decision-note-status", "decision-note failed=" + error.message);
      });
  }

  function setupDecisionNoteAction() {
    var approveReadyButton = byId("record-decision-approve-ready-button");
    if (approveReadyButton) {
      approveReadyButton.addEventListener("click", function () {
        recordReviewDecisionNote("approve-ready");
      });
    }
    var needsRevisionButton = byId("record-decision-needs-revision-button");
    if (needsRevisionButton) {
      needsRevisionButton.addEventListener("click", function () {
        recordReviewDecisionNote("needs-revision");
      });
    }
    var needsEvidenceButton = byId("record-decision-needs-evidence-button");
    if (needsEvidenceButton) {
      needsEvidenceButton.addEventListener("click", function () {
        recordReviewDecisionNote("needs-evidence");
      });
    }
    applySuggestedDecisionFromUrl();
  }

  function setupCoreNextStepCopyAction() {
    var button = byId("review-detail-core-next-step-copy");
    if (button) {
      button.addEventListener("click", copySuggestedCoreNextCommand);
    }
    var reviewUrlButton = byId("review-detail-core-review-url-copy");
    if (reviewUrlButton) {
      reviewUrlButton.addEventListener("click", copySuggestedCoreReviewUrl);
    }
  }

  function setupAgentReportNextStepCopyAction() {
    var button = byId("review-detail-agent-core-next-step-copy");
    if (!button) {
      return;
    }
    button.addEventListener("click", copyAgentReportSuggestedCoreNextCommand);
  }

  function reviewPageValue(detail, key) {
    var page = detail.reviewPage || {};
    return page[key] || detail[key] || {};
  }

  function setState(status, source, detail) {
    setText("review-center-api-status", status);
    setText("review-center-api-source", source);
    setText("review-center-api-detail", detail);
  }

  function getQueryParam(name) {
    var params = new URLSearchParams(window.location.search);
    return params.get(name) || "";
  }

  function getQueryTaskId() {
    return getQueryParam("taskId");
  }

  function getQueryWorkflowRunId() {
    return getQueryParam("workflowRunId");
  }

  function getQueryAgentReport() {
    return getQueryParam("agentReport");
  }

  function getQueryCoreDbPath() {
    return getQueryParam("coreDbPath");
  }

  function getQueryGradingDbPath() {
    return getQueryParam("gradingDbPath") || getQueryParam("dbPath");
  }

  function getQueryAgentEntityRefreshRequested() {
    var params = new URLSearchParams(window.location.search);
    return params.get("agentEntityRefresh") === "1";
  }

  function appendLocalContextParams(params) {
    var agentReport = getQueryAgentReport();
    var coreDbPath = state.coreDbPath || getQueryCoreDbPath();
    var gradingDbPath = state.gradingDbPath || getQueryGradingDbPath();
    var workflowRunId = getQueryWorkflowRunId();
    if (agentReport) {
      params.set("agentReport", agentReport);
    }
    if (coreDbPath) {
      params.set("coreDbPath", coreDbPath);
    }
    if (gradingDbPath) {
      params.set("gradingDbPath", gradingDbPath);
    }
    if (workflowRunId) {
      params.set("workflowRunId", workflowRunId);
    }
    return params;
  }

  function updateQueryTaskId(taskId) {
    if (!window.history || !window.history.replaceState) {
      return;
    }
    var url = new URL(window.location.href);
    if (taskId) {
      url.searchParams.set("taskId", taskId);
    } else {
      url.searchParams.delete("taskId");
    }
    window.history.replaceState({}, "", url.toString());
  }

  function withCoreDbPath(path) {
    if (!state.coreDbPath) {
      return path;
    }
    return path
      + (path.indexOf("?") === -1 ? "?" : "&")
      + "coreDbPath="
      + encodeURIComponent(state.coreDbPath);
  }

  function withGradingDbPath(path) {
    var gradingDbPath = state.gradingDbPath || getQueryGradingDbPath();
    if (!gradingDbPath) {
      return path;
    }
    return path
      + (path.indexOf("?") === -1 ? "?" : "&")
      + "gradingDbPath="
      + encodeURIComponent(gradingDbPath);
  }

  function withAgentReport(path) {
    var reportPath = getQueryAgentReport();
    if (!reportPath) {
      return path;
    }
    return path
      + (path.indexOf("?") === -1 ? "?" : "&")
      + "agentReport="
      + encodeURIComponent(reportPath);
  }

  function withWorkflowRunId(path) {
    var workflowRunId = getQueryWorkflowRunId();
    if (!workflowRunId) {
      return path;
    }
    return path
      + (path.indexOf("?") === -1 ? "?" : "&")
      + "workflowRunId="
      + encodeURIComponent(workflowRunId);
  }

  function summaryPath() {
    return withAgentReport(withWorkflowRunId(state.summaryPath));
  }

  function detailPath(taskId) {
    return withAgentReport(withGradingDbPath(withCoreDbPath(
      state.detailPathTemplate.replace("{id}", encodeURIComponent(taskId))
    )));
  }

  function backendCoreTaskPath(taskId) {
    return withCoreDbPath(state.backendCoreTaskPathTemplate.replace("{id}", encodeURIComponent(taskId)));
  }

  function coreReadinessPath(taskId) {
    return withGradingDbPath(withCoreDbPath(
      state.coreReadinessPathTemplate.replace("{id}", encodeURIComponent(taskId))
    ));
  }

  function safeFetchJson(url) {
    return fetch(url, {
      method: "GET",
      headers: {
        "Accept": "application/json"
      },
      credentials: "same-origin"
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("HTTP_" + response.status);
      }
      return response.json();
    });
  }

  function setApiLoaded(source, detailStatus) {
    state.loadedFromApi = true;
    setState("API_READONLY_LOADED", source, detailStatus + " · autoPublishAllowed=false · batchStateChangeAllowed=false");
  }

  function applyBackendCoreTaskDetail(data, sourceLabel) {
    var task = data && data.task ? data.task : {};
    var taskId = task.id || state.selectedTaskId || "none";
    var artifactIds = Array.isArray(task.artifactIds) ? task.artifactIds : [];
    state.selectedTaskId = task.id || state.selectedTaskId || "";
    setText("review-center-selected-task", taskId);
    setText("detail-title", task.title || "Backend Core 任务详情");
    setText(
      "review-detail-subtitle",
      taskId + " · " + (task.taskType || "UNKNOWN_TASK") + " · " + (task.status || "UNKNOWN_STATUS")
    );
    setText("review-detail-artifact-total", artifactIds.length || 0);
    setText("review-detail-workflow-step-total", 0);
    setText("review-detail-status", task.status || "UNKNOWN_STATUS");
    setText("review-detail-auto-approve", "false");
    setText("review-detail-task-type", task.taskType || "UNKNOWN_TASK");
    setText(
      "review-detail-api-summary",
      sourceLabel
        + " · repositoryBacked=true"
        + " · jsonStoreRead=false"
        + " · reviewRequired=true"
        + " · generatedContentStatus=" + (task.status || "UNKNOWN_STATUS")
        + " · finalResultPath=" + (task.finalResultPath || "none")
        + " · artifactTotal=" + (artifactIds.length || 0)
        + " · backendCoreTaskFallback=true"
        + " · autoApproveAllowed=false · realPublishAllowed=false"
    );
  }

  function loadBackendCoreTaskDetail(taskId, options) {
    if (!taskId || !state.coreDbPath || !window.fetch) {
      return Promise.resolve(null);
    }
    return safeFetchJson(backendCoreTaskPath(taskId))
      .then(function (payload) {
        if (payload && payload.success === true && payload.data && payload.data.task) {
          if (options && options.renderFallback === true) {
            applyBackendCoreTaskDetail(
              payload.data,
              "source=GET /api/backend/core-tasks/{id}?coreDbPath={path}"
            );
          }
          return payload;
        }
        throw new Error("INVALID_BACKEND_CORE_TASK_PAYLOAD");
      })
      .catch(function () {
        return null;
      });
  }

  function setSelectedQueueItem(taskId) {
    var queue = byId("review-center-dynamic-queue");
    if (!queue) {
      return;
    }
    Array.prototype.forEach.call(queue.querySelectorAll("[data-api-task-id]"), function (node) {
      node.setAttribute("aria-current", node.getAttribute("data-api-task-id") === taskId ? "true" : "false");
    });
  }

  function loadTaskDetail(taskId, options) {
    state.selectedTaskId = taskId || "";
    if (!taskId) {
      setText("review-center-selected-task", "none");
      setApiLoaded("GET /api/review-task-summary?limit=3&detailMode=light", "summaryLoaded=true · detailLoadStatus=DETAIL_LOAD_SKIPPED");
      return Promise.resolve(null);
    }
    refreshMvpWorkspaceContextLinks(taskId);
    var shouldUpdateUrl = !options || options.updateUrl !== false;
    setText("review-center-selected-task", taskId);
    setSelectedQueueItem(taskId);
    if (shouldUpdateUrl) {
      updateQueryTaskId(taskId);
    }
    var agentReport = getQueryAgentReport();
    var detailSource = state.coreDbPath
      ? "GET /api/review-task-summary?limit=3&detailMode=light + GET /api/review-tasks/{id}?coreDbPath={path} + GET /api/backend/core-tasks/{id}?coreDbPath={path}"
      : "GET /api/review-task-summary?limit=3&detailMode=light + GET /api/review-tasks/{id}";
    if (agentReport) {
      detailSource += " + agentReport=" + agentReport;
    }
    setApiLoaded(
      detailSource,
      "summaryLoaded=true · selectedTaskId=" + taskId + " · detailLoadStatus=PENDING"
    );
    return safeFetchJson(detailPath(taskId))
      .then(function (detailPayload) {
        if (detailPayload && detailPayload.success === true && detailPayload.data) {
          applyDetail(detailPayload.data.reviewDetail || {});
          setSelectedQueueItem(taskId);
          setApiLoaded(
            detailSource,
            "summaryLoaded=true · selectedTaskId=" + taskId + " · detailLoadStatus=DETAIL_LOADED"
          );
          return loadGradingRecordReportLink(taskId).then(function () {
            return loadCoreWorkflowReadiness(taskId).then(function () {
              return detailPayload;
            });
          });
        }
        return loadCoreWorkflowReadiness(taskId).then(function () {
          return detailPayload;
        });
      })
      .catch(function (detailError) {
        setText("controlled-evidence-detail-visible", "reviewDetail.controlledGradingEvidence.visible=unavailable");
        return loadBackendCoreTaskDetail(taskId, { renderFallback: true })
          .then(function (backendCorePayload) {
            setApiLoaded(
              backendCorePayload ? detailSource : "GET /api/review-task-summary?limit=3&detailMode=light",
              "summaryLoaded=true · selectedTaskId=" + taskId
                + " · detailLoadStatus=DETAIL_LOAD_FAILED:" + detailError.message
                + " · backendCoreTaskLoadStatus=" + (backendCorePayload ? "LOADED" : "UNAVAILABLE")
            );
            return loadCoreWorkflowReadiness(taskId).then(function () {
              return backendCorePayload;
            });
          });
      });
  }

  function applyCoreWorkflowReadiness(report, sourceLabel) {
    var list = clearNode("review-detail-core-readiness-list");
    var summary = report && report.summary ? report.summary : {};
    var safety = report && report.safety ? report.safety : {};
    var steps = report && Array.isArray(report.steps) ? report.steps : [];
    var blockedSteps = report && Array.isArray(report.blockedSteps) ? report.blockedSteps : [];
    var stepTotal = summary.stepTotal || steps.length || 0;
    var readyTotal = summary.readyTotal || 0;
    var status = report && report.status ? report.status : "CORE_DEMO_NEEDS_ACTION";
    var nextAction = report && report.recommendedNextAction
      ? report.recommendedNextAction
      : "approve_generated_content_after_manual_review";
    var recommendedDecision = decisionFromRecommendation(summary.gradingDecisionNoteRecommendation || "");
    var importActionSummary = report && report.platformImportPreviewActionSummary
      ? report.platformImportPreviewActionSummary
      : {};
    var contentQualityReadiness = report && report.contentQualityReadiness
      ? report.contentQualityReadiness
      : {};
    var nextToolRecommendation = report && report.nextToolRecommendation
      ? report.nextToolRecommendation
      : {};
    var recommendedToolName = nextToolRecommendation.toolName || "manual_action";
    var recommendedReason = nextToolRecommendation.reasonCode || "NO_RECOMMENDATION";
    var nextStepGuide = buildNextSingleStepGuide(report, nextToolRecommendation);
    applyCoreNextStepCopyGuide(nextStepGuide);

    setText("review-detail-core-readiness-status", status);
    setText(
      "review-detail-core-readiness-next-action",
      "recommendedNextAction=" + nextAction
        + " · nextTool=" + recommendedToolName
        + " · reasonCode=" + recommendedReason
    );
    setText("review-detail-core-readiness-progress", "ready=" + readyTotal + "/" + stepTotal);
    setText(
      "review-detail-core-readiness-summary",
      sourceLabel
        + " · component=" + (report && report.component ? report.component : "CoreWorkflowReadinessReport")
        + " · taskId=" + (report && report.taskId ? report.taskId : "none")
        + " · taskStatus=" + (report && report.taskStatus ? report.taskStatus : "UNKNOWN_STATUS")
        + " · ready=" + boolText(report && report.ready === true)
        + " · blockedTotal=" + (summary.blockedTotal || blockedSteps.length)
        + " · platformRequiredTotal=" + (summary.platformRequiredTotal || 0)
        + " · importPreviewPendingTotal=" + (summary.platformImportPreviewPendingTotal || 0)
        + " · contentQualityAvailable=" + boolText(contentQualityReadiness.available === true)
        + " · contentQualityReadyForImportPreview="
        + boolText(contentQualityReadiness.readyForImportPreview === true)
        + " · contentQualityRevisionRequired="
        + boolText(contentQualityReadiness.requiresRevisionBeforeImportPreview === true)
        + " · contentQualityDecisionStatus=" + primitiveText(contentQualityReadiness.decisionStatus)
        + " · contentQualityBlockedKinds="
        + (contentQualityReadiness.blockedForImportPreviewKinds || []).join(",")
        + " · nextTool=" + recommendedToolName
        + " · toolAvailable=" + boolText(nextToolRecommendation.toolAvailable === true)
        + " · autoExecuteAllowed=" + boolText(nextToolRecommendation.autoExecuteAllowed === true)
        + " · gradingEvidenceReady=" + primitiveText(summary.gradingEvidenceReady)
        + " · gradingApproveReadyDecision=" + primitiveText(summary.gradingApproveReadyDecision)
        + " · gradingManualReviewChecklistStatus=" + primitiveText(summary.gradingManualReviewChecklistStatus)
        + " · gradingScorePreviewStatus=" + primitiveText(summary.gradingScorePreviewStatus)
        + " · gradingScorePreview="
        + primitiveText(summary.gradingScorePreviewEarnedScore)
        + "/" + primitiveText(summary.gradingScorePreviewTotalScore)
        + " · gradingScorePreviewReadyForDecisionNote="
        + primitiveText(summary.gradingScorePreviewReadyForDecisionNote)
        + " · gradingDecisionNoteRecommendation=" + primitiveText(summary.gradingDecisionNoteRecommendation)
        + " · gradingNextDecisionNoteAction=" + primitiveText(summary.gradingNextDecisionNoteAction)
    );
    setText(
      "review-detail-core-readiness-safety",
      "readOnly=" + boolText(safety.readOnly !== false)
        + " · realLlmCalled=" + boolText(safety.realLlmCalled === true)
        + " · secretsRead=" + boolText(safety.secretsRead === true)
        + " · networkAccess=" + boolText(safety.networkAccess === true)
        + " · sandboxExecutedByReport=" + boolText(safety.sandboxExecutedByReport === true)
        + " · autoApproveAllowed=" + boolText(safety.autoApproveAllowed === true)
        + " · autoPublishAllowed=" + boolText(safety.autoPublishAllowed === true)
        + " · realPublish=" + boolText(safety.realPublish === true)
    );
    setText(
      "review-detail-core-next-step-guide-status",
      "canContinueWithSameCommand=" + boolText(nextStepGuide.canContinueWithSameCommand)
        + " · requiresAdditionalArguments=" + boolText(nextStepGuide.requiresAdditionalArguments)
    );
    setText(
      "review-detail-core-next-step-guide-tool",
      "nextTool=" + nextStepGuide.nextToolName
        + " · reasonCode=" + nextStepGuide.reasonCode
    );
    setText(
      "review-detail-core-next-step-guide-command",
      "suggestedCliCommand=" + nextStepGuide.suggestedCliCommand
        + " · requiresHumanManualAction=" + boolText(nextStepGuide.requiresHumanManualAction)
        + " · autoExecuteAllowed=false"
    );
    applyMvpReviewWorkspaceFromCoreReadiness(report, nextAction, status, readyTotal, stepTotal);
    if (recommendedDecision) {
      applySuggestedDecision({
        decision: recommendedDecision,
        source: "core-readiness",
        nextCoreAction: nextAction,
        reason: summary.gradingDecisionNoteRecommendationReason
          || ("Core readiness recommends " + recommendedDecision + " based on grading evidence checklist.")
      });
    }

    if (!list) {
      return;
    }
    if (!blockedSteps.length && !steps.length) {
      appendSignalItem(
        list,
        0,
        "core readiness unavailable",
        ["readOnly=true", "autoPublishAllowed=false"],
        "No core workflow readiness report is available; manual review remains required."
      );
      return;
    }
    var visibleSteps = blockedSteps.length ? blockedSteps : steps.slice(0, 4);
    visibleSteps.slice(0, 6).forEach(function (step, index) {
      appendSignalItem(
        list,
        index + 1,
        (step.label || step.id || "core_readiness_step"),
        [
          "ready=" + boolText(step.ready === true),
          "stepId=" + (step.id || "unknown"),
          "source=" + (step.source || "CoreWorkflowReadinessReport")
        ],
        "nextAction=" + (step.nextAction || "none")
          + " · recommendedNextAction=" + nextAction
          + (
            step.actionSummary && step.actionSummary.pendingPreviewTotal
              ? " · pendingPreviewEntities=" + step.actionSummary.pendingPlatformEntities.join(",")
              : ""
          )
          + " · manualReviewRequired=true"
      );
    });
    if (importActionSummary.pendingPreviewTotal) {
      appendSignalItem(
        list,
        visibleSteps.length + 1,
        "import preview pending actions",
        [
          "pendingPreviewTotal=" + importActionSummary.pendingPreviewTotal,
          "enabledTotal=" + (importActionSummary.enabledTotal || 0),
          "contentQualityReadyTotal=" + (importActionSummary.contentQualityReadyTotal || 0)
        ],
        "pendingPlatformEntities=" + (importActionSummary.pendingPlatformEntities || []).join(",")
          + " · nextActions=" + (importActionSummary.pendingNextRequiredActions || []).join(",")
          + " · autoApproveAllowed=false · realPublishAllowed=false"
      );
    }
    if (nextToolRecommendation.reasonCode) {
      appendSignalItem(
        list,
        visibleSteps.length + (importActionSummary.pendingPreviewTotal ? 2 : 1),
        "next tool recommendation",
        [
          "reasonCode=" + recommendedReason,
          "toolName=" + recommendedToolName,
          "toolAvailable=" + boolText(nextToolRecommendation.toolAvailable === true)
        ],
        "actionType=" + (nextToolRecommendation.actionType || "manual_action")
          + " · cliCommand=" + (nextToolRecommendation.cliCommand || "none")
          + " · contentQualityReadyForImportPreview="
          + boolText(
            nextToolRecommendation.contentQualityReadiness
              && nextToolRecommendation.contentQualityReadiness.readyForImportPreview === true
          )
          + " · autoExecuteAllowed=" + boolText(nextToolRecommendation.autoExecuteAllowed === true)
          + " · autoApproveAllowed=" + boolText(nextToolRecommendation.autoApproveAllowed === true)
          + " · autoPublishAllowed=" + boolText(nextToolRecommendation.autoPublishAllowed === true)
          + " · realPublishAllowed=" + boolText(nextToolRecommendation.realPublishAllowed === true)
      );
    }
    appendSignalItem(
      list,
      visibleSteps.length + (importActionSummary.pendingPreviewTotal ? 3 : 2),
      "next single-step action guide",
      [
        "canContinueWithSameCommand=" + boolText(nextStepGuide.canContinueWithSameCommand),
        "nextTool=" + nextStepGuide.nextToolName,
        "actionType=" + nextStepGuide.actionType,
        "requiresAdditionalArguments=" + boolText(nextStepGuide.requiresAdditionalArguments)
      ],
      "suggestedCliCommand=" + nextStepGuide.suggestedCliCommand
        + " · suggestedArguments=" + objectSummary(nextStepGuide.suggestedArguments, 4)
        + " · contentQualityReadyForImportPreview="
        + boolText(
          nextStepGuide.contentQualityReadiness
            && nextStepGuide.contentQualityReadiness.readyForImportPreview === true
        )
        + " · autoApproveAllowed=false · autoPublishAllowed=false"
    );
  }

  function loadCoreWorkflowReadiness(taskId) {
    if (!taskId || !window.fetch) {
      applyCoreWorkflowReadiness(null, "source=GET /api/review-tasks/{id}/core-readiness · skipped");
      return Promise.resolve(null);
    }
    return safeFetchJson(coreReadinessPath(taskId))
      .then(function (payload) {
        var report = payload && payload.data ? payload.data.coreWorkflowReadinessReport : null;
        if (payload && payload.success === true && report) {
          applyCoreWorkflowReadiness(report, "source=GET /api/review-tasks/{id}/core-readiness");
          return report;
        }
        throw new Error("INVALID_CORE_READINESS_PAYLOAD");
      })
      .catch(function (error) {
        applyCoreWorkflowReadiness(null, "source=GET /api/review-tasks/{id}/core-readiness · loadFailed=" + error.message);
        return null;
      });
  }

  function agentExecutionSafeStatus(report) {
    var safety = report && report.safety ? report.safety : {};
    return "realAgentStarted=" + boolText(safety.realAgentStarted === true)
      + " · realLlmCalled=" + boolText(safety.realLlmCalled === true)
      + " · autoApproveAllowed=" + boolText(safety.autoApproveAllowed === true)
      + " · autoPublishAllowed=" + boolText(safety.autoPublishAllowed === true)
      + " · realPublishAllowed=" + boolText(safety.realPublishAllowed === true);
  }

  function applyAgentCoreExecutionReport(report, sourceLabel) {
    var list = clearNode("review-detail-agent-core-execution-list");
    var execution = report && report.agentCoreNextToolExecution ? report.agentCoreNextToolExecution : {};
    var plan = report && report.agentCoreNextToolPlan ? report.agentCoreNextToolPlan : {};
    var postPlan = report && report.postExecutionCoreNextToolPlan ? report.postExecutionCoreNextToolPlan : {};
    var guide = report && report.nextSingleStepActionGuide ? report.nextSingleStepActionGuide : {};
    var currentStop = guide && guide.currentStop ? guide.currentStop : {};
    applyAgentReportNextStepCopyGuide(guide);
    var status = report && report.component
      ? "AGENT_EXECUTION_REPORT_LOADED"
      : "NO_AGENT_REPORT_LOADED";
    setText("review-detail-agent-core-execution-status", status);
    setText(
      "review-detail-agent-core-execution-summary",
      sourceLabel
        + " · component=" + (report && report.component ? report.component : "none")
        + " · taskId=" + (report && report.taskId ? report.taskId : "none")
        + " · traceId=" + (report && report.traceId ? report.traceId : "none")
        + " · toolName=" + (execution.toolName || plan.toolName || "none")
        + " · toolCallSucceeded=" + boolText(execution.toolCallSucceeded === true)
        + " · nextTool=" + (guide.nextToolName || postPlan.toolName || "manual_action")
        + " · stopReason=" + (currentStop.reasonCode || "none")
        + " · canContinueWithSameCommand=" + boolText(guide.canContinueWithSameCommand === true)
        + " · operatorSummary=" + (guide.operatorSummary || "none")
        + " · reviewCenterReportUrl=" + (report && report.reviewCenterReportUrl ? report.reviewCenterReportUrl : "none")
        + " · readOnlyReport=true"
    );
    if (!list) {
      return;
    }
    if (!report || !report.component) {
      appendSignalItem(
        list,
        "A",
        "no execution report selected",
        ["readOnly=true", "commandExecutedByPage=false"],
        "Add ?agentReport=examples/output/demo-agent-core-next-tool-execution-{taskId}.json to read an existing Agent execution report."
      );
      return;
    }
    appendSignalItem(
      list,
      1,
      "executed recommended tool",
      [
        "toolName=" + (execution.toolName || plan.toolName || "none"),
        "toolCallSucceeded=" + boolText(execution.toolCallSucceeded === true),
        "recommendedToolCalled=" + boolText(execution.recommendedToolCalled === true)
      ],
      "toolCallStatus=" + (execution.toolCallStatus || "unknown")
        + " · outputPath=" + (execution.outputPath || "none")
        + " · commandExecutedByPage=false"
    );
    appendSignalItem(
      list,
      2,
      "post execution next plan",
      [
        "nextTool=" + (postPlan.toolName || guide.nextToolName || "manual_action"),
        "reasonCode=" + (postPlan.reasonCode || guide.reasonCode || "none"),
        "stopReason=" + (currentStop.reasonCode || "none"),
        "manualActionRequired=" + boolText(postPlan.manualActionRequired === true || guide.requiresHumanManualAction === true)
      ],
      "recommendedNextAction=" + (postPlan.recommendedNextAction || guide.recommendedNextAction || "none")
        + " · canContinueWithSameCommand=" + boolText(guide.canContinueWithSameCommand === true)
        + " · operatorSummary=" + (guide.operatorSummary || "none")
        + " · suggestedCliCommand=" + (guide.suggestedCliCommand || "none")
    );
    appendSignalItem(
      list,
      3,
      "review center report link",
      [
        "reportLinkAvailable=" + boolText(!!report.reviewCenterReportUrl),
        "readOnlyReport=true",
        "commandExecutedByPage=false"
      ],
      "reviewCenterReportUrl=" + (report.reviewCenterReportUrl || "none")
    );
    appendSignalItem(
      list,
      4,
      "agent execution safety",
      [
        "autoApproveAllowed=false",
        "autoPublishAllowed=false",
        "realPublishAllowed=false"
      ],
      agentExecutionSafeStatus(report)
    );
  }

  function loadAgentCoreExecutionReport() {
    var reportPath = getQueryAgentReport();
    if (!reportPath || !window.fetch) {
      applyAgentCoreExecutionReport(null, "source=GET /api/workflow/report?file={agentReport} · skipped");
      return Promise.resolve(null);
    }
    return safeFetchJson(state.workflowReportPathTemplate.replace("{file}", encodeURIComponent(reportPath)))
      .then(function (payload) {
        var report = payload && payload.data ? payload.data.report : null;
        if (payload && payload.success === true && report) {
          applyAgentCoreExecutionReport(
            report,
            "source=GET /api/workflow/report?file={agentReport} · agentReport=" + reportPath
          );
          return report;
        }
        throw new Error("INVALID_AGENT_EXECUTION_REPORT_PAYLOAD");
      })
      .catch(function (error) {
        applyAgentCoreExecutionReport(
          null,
          "source=GET /api/workflow/report?file={agentReport} · loadFailed=" + error.message
        );
        return null;
      });
  }

  function applyAgentEntityReadiness(report, sourceLabel) {
    var list = clearNode("review-detail-platform-readiness-list");
    var items = report && Array.isArray(report.items) ? report.items : [];
    var summary = report && report.summary ? report.summary : {};
    var readyTotal = summary.readyForManualAgentReviewTotal || 0;
    var requiredTotal = summary.requiredTotal || items.length || 3;

    setText("review-detail-platform-readiness-total", "ready=" + readyTotal + "/" + requiredTotal);
    setText(
      "review-detail-platform-readiness-summary",
      sourceLabel
        + " · component=" + (report && report.component ? report.component : "AgentEntityReadinessReport")
        + " · sourceTaskId=" + (report && report.sourceTaskId ? report.sourceTaskId : "none")
        + " · agentEntityRefreshRequested=" + boolText(state.agentEntityRefreshRequested === true)
        + " · refreshQuery=agentEntityRefresh=1"
        + " · refreshedAfterAgentEntityReturn=" + boolText(state.agentEntityRefreshRequested === true)
        + " · allReadyForManualPlatformReview=" + boolText(summary.allReadyForManualPlatformReview === true)
        + " · dryRunPreparedTotal=" + (summary.dryRunPreparedTotal || 0)
        + " · requestSentTotal=" + (summary.requestSentTotal || 0)
        + " · resultRecordedTotal=" + (summary.resultRecordedTotal || 0)
        + " · agentEntitySignoffReadyTotal=" + (summary.agentEntitySignoffReadyTotal || 0)
        + " · agentEntitySignoffRecordedTotal=" + (summary.agentEntitySignoffRecordedTotal || 0)
        + " · postSignoffPrePublishReadyTotal=" + (summary.postSignoffPrePublishReadyTotal || 0)
        + " · allPostSignoffPrePublishReady=" + boolText(summary.allPostSignoffPrePublishReady === true)
        + " · databaseWritten=false"
        + " · realAgentImport=false"
        + " · realPublish=false"
    );

    if (!list) {
      return;
    }
    if (!items.length) {
      appendSignalItem(
        list,
        0,
        "platform entity readiness unavailable",
        ["ready=0/4", "readOnly=true", "databaseWritten=false"],
        "No readiness report is available; manual review remains required."
      );
      return;
    }
    items.slice(0, 6).forEach(function (item, index) {
      var entityId = item.agentEntityId || "";
      var sourceTaskId = item.sourceTaskId || "";
      var signoffActionAvailable = item.readyForAgentEntitySignoff === true && item.signoffRecorded !== true;
      var signoffRecorded = item.signoffRecorded === true;
      var postSignoffChecklist = item.postSignoffPrePublishChecklist || {};
      var entitySpecificFocus = postSignoffChecklist.entitySpecificReviewFocus || {};
      var postSignoffSafety = postSignoffChecklist.safety || {};
      var href = agentEntityHref(
        entityId,
        sourceTaskId,
        item.agentEntity,
        ""
      );
      appendSignalItem(
        list,
        index + 1,
        (item.agentEntity || "agent_entity") + " · " + (item.sourceArtifactKind || "UNKNOWN_ARTIFACT"),
        [
          "readyForManualAgentReview=" + boolText(item.readyForManualAgentReview === true),
          "previewCreated=" + boolText(item.previewCreated === true),
          "mockImportCreated=" + boolText(item.mockImportCreated === true),
          "dryRunPrepared=" + boolText(item.dryRunPrepared === true),
          "requestSent=" + boolText(item.requestSent === true),
          "resultRecorded=" + boolText(item.resultRecorded === true),
          "signoffState=" + agentEntitySignoffState(item),
          "readyForAgentEntitySignoff=" + boolText(item.readyForAgentEntitySignoff === true),
          "signoffRecorded=" + boolText(item.signoffRecorded === true),
          "postSignoffPrePublishStatus=" + (postSignoffChecklist.status || "none"),
          "entitySpecificReviewFocus=" + (entitySpecificFocus.primaryReviewFocus || "none"),
          "finalHumanReviewRequired=" + boolText(postSignoffSafety.requiresFinalHumanReview === true),
          "databaseWritten=false",
          "realAgentImport=false"
        ],
        "entityId=" + (entityId || "none")
          + " · sourceTaskId=" + (sourceTaskId || "none")
          + " · latestPlatformStatus=" + (item.latestPlatformStatus || item.latestQueriedPlatformStatus || "none")
          + " · blockers=" + (Array.isArray(item.blockers) && item.blockers.length ? item.blockers.join(",") : "none")
          + " · manualSignoffChecklist="
          + (Array.isArray(item.manualSignoffChecklist)
            ? item.manualSignoffChecklist.map(function (check) {
              return check.id + ":" + boolText(check.matched === true);
            }).join(",")
            : "none")
          + " · " + agentEntityActivitySummary(item)
          + " · " + postSignoffChecklistSummary(item)
          + " · detailRoute=" + href
      );
      if (list.lastElementChild && entityId) {
        var link = document.createElement("a");
        link.className = "pill strong";
        link.href = href;
        link.textContent = signoffActionAvailable
          ? "查看本地实体（平台签收暂停）"
          : (signoffRecorded ? "查看本地实体记录" : "查看就绪实体");
        link.setAttribute(
          "aria-label",
          (signoffActionAvailable ? "查看本地平台实体并阅读平台签收暂停说明 " : (signoffRecorded ? "查看本地平台实体记录 " : "查看就绪平台实体 ")) + entityId
        );
        link.title = signoffActionAvailable
          ? "platform signoff paused · local detail only · autoPost=false"
          : (signoffRecorded
            ? "local signoff evidence recorded · postSignoffPrePublishChecklist · finalHumanReviewRequired=true · realPublish=false"
            : "open platform entity detail");
        list.lastElementChild.appendChild(link);
      }
    });
  }

  function loadAgentEntityReadiness(taskId) {
    if (!taskId) {
      applyAgentEntityReadiness(
        null,
        "source=GET /api/platform-entities/readiness-report?sourceTaskId={id} · detailLoadStatus=SKIPPED"
      );
      return Promise.resolve(null);
    }
    var params = new URLSearchParams();
    params.set("sourceTaskId", taskId);
    appendLocalContextParams(params);
    return safeFetchJson("/api/platform-entities/readiness-report?" + params.toString())
      .then(function (payload) {
        var report = payload && payload.data ? payload.data.agentEntityReadinessReport : null;
        if (!report) {
          throw new Error("READINESS_REPORT_MISSING");
        }
        applyAgentEntityReadiness(
          report,
          "source=GET /api/platform-entities/readiness-report?sourceTaskId={id}"
            + (state.coreDbPath ? "&coreDbPath={path}" : "")
            + (state.gradingDbPath ? "&gradingDbPath={path}" : "")
        );
        return report;
      })
      .catch(function () {
        return safeFetchJson("mock-data.json")
          .then(function (payload) {
            var fallback = payload.reviewCenterPrototype && payload.reviewCenterPrototype.agentEntityReadinessReport
              ? payload.reviewCenterPrototype.agentEntityReadinessReport
              : payload.agentEntitiesPrototype
              ? payload.agentEntitiesPrototype.readinessReport
              : null;
            applyAgentEntityReadiness(
              fallback,
              "source=frontend/mock-data.json.reviewCenterPrototype.agentEntityReadinessReport"
            );
            return fallback;
          })
          .catch(function () {
            applyAgentEntityReadiness(
              null,
              "source=GET /api/platform-entities/readiness-report?sourceTaskId={id} · fallbackLoadStatus=FAILED"
            );
            return null;
          });
      });
  }

  function renderDynamicQueue(summary, selectedTaskId) {
    var queue = byId("review-center-dynamic-queue");
    var status = byId("review-center-dynamic-queue-status");
    if (!queue) {
      return;
    }
    var priorityQueue = summary && summary.reviewPriorityQueue ? summary.reviewPriorityQueue : {};
    var realDemoQueue = summary && summary.realDemoReviewQueue ? summary.realDemoReviewQueue : {};
    var teachingPackageReview = summary && summary.teachingPackageReview ? summary.teachingPackageReview : {};
    var priorityItems = Array.isArray(priorityQueue.items) ? priorityQueue.items : [];
    var realDemoItems = teachingPackageReview.available === true
      ? []
      : (Array.isArray(realDemoQueue.items) ? realDemoQueue.items : []);
    var items = priorityItems.slice();
    realDemoItems.forEach(function (item) {
      items.push({
        rank: "R" + (item.rank || "-"),
        title: "真实产物 · " + (item.artifactKind || item.taskType || item.taskId || "DSL"),
        taskId: item.taskId || "",
        taskType: item.taskType || "REAL_DEMO_ARTIFACT",
        status: item.status || "WAITING_REVIEW",
        priority: item.dynamicTaskAvailable === true || item.syntheticTaskAvailable === true ? "HIGH" : "NORMAL",
        reasonCode: item.syntheticTaskAvailable === true
          ? "REAL_LLM_AGENT_REPORT_ARTIFACT_TASK"
          : (item.dynamicTaskAvailable === true ? "REAL_LLM_ARTIFACT_TASK" : "REAL_LLM_ARTIFACT_ONLY"),
        recommendedAction: item.recommendedAction || "review_real_llm_artifact",
        realDemoArtifact: true,
        dynamicTaskAvailable: item.dynamicTaskAvailable === true,
        syntheticTaskAvailable: item.syntheticTaskAvailable === true,
        localArtifactExists: item.localArtifactExists === true,
        artifactKind: item.artifactKind || "",
        path: item.path || "",
        pptxArtifactPath: item.pptxArtifactPath || "",
        agentReportPath: item.agentReportPath || "",
        schemaValidated: item.schemaValidated === true
      });
    });
    queue.innerHTML = "";
    if (status) {
      status.textContent = items.length
        ? "loaded=" + items.length
          + " · priorityTasks=" + priorityItems.length
          + " · realDemoArtifacts=" + realDemoItems.length
          + " · sourceMode=" + (realDemoQueue.sourceMode || "UNKNOWN")
          + " · click dynamic task to load GET /api/review-tasks/{id}"
        : "loaded=0 · no WAITING_REVIEW tasks";
    }
    items.forEach(function (item) {
      var button = document.createElement("button");
      var taskId = item.taskId || "";
      button.className = "queue-item";
      button.type = "button";
      button.setAttribute("data-api-task-id", taskId);
      button.setAttribute("aria-current", taskId === selectedTaskId ? "true" : "false");
      if (item.realDemoArtifact === true) {
        button.setAttribute("data-real-demo-artifact", "true");
      }

      var title = document.createElement("h3");
      var rank = document.createElement("span");
      rank.className = "priority-rank";
      rank.textContent = item.rank || "-";
      title.appendChild(rank);
      title.appendChild(document.createTextNode(" " + (item.title || taskId || "review task")));

      var meta = document.createElement("div");
      meta.className = "meta-row";
      [
        item.taskType || "UNKNOWN_TASK",
        item.status || "WAITING_REVIEW",
        "priority=" + (item.priority || "LOW"),
        item.reasonCode || "DETAIL_REQUIRED"
      ].forEach(function (value, index) {
        var pill = document.createElement("span");
        pill.className = index === 1 || index === 2 ? "pill strong" : "pill";
        pill.textContent = value;
        meta.appendChild(pill);
      });

      var desc = document.createElement("p");
      desc.textContent = item.realDemoArtifact === true
        ? "taskId=" + taskId
          + " · artifactKind=" + (item.artifactKind || "UNKNOWN_ARTIFACT")
          + " · path=" + (item.path || "none")
          + " · agentReport=" + (item.agentReportPath || "none")
          + " · localArtifactExists=" + boolText(item.localArtifactExists === true)
          + " · dynamicTaskAvailable=" + boolText(item.dynamicTaskAvailable === true)
          + " · syntheticTaskAvailable=" + boolText(item.syntheticTaskAvailable === true)
          + " · recommendedAction=" + (item.recommendedAction || "review_real_llm_artifact")
        : "taskId=" + taskId + " · recommendedAction=" + (item.recommendedAction || "open_review_detail_before_approval");
      var decisionHints = item.mergedGradingEvidenceSummary
        && item.mergedGradingEvidenceSummary.reviewDecisionHintsSummary
        ? item.mergedGradingEvidenceSummary.reviewDecisionHintsSummary
        : null;
      var decision = document.createElement("p");
      decision.textContent = decisionHints
        ? "reviewDecisionHint=" + (decisionHints.overallHint || "NEEDS_EVIDENCE")
          + " · approveReady=" + (decisionHints.approveReadyTotal || 0)
          + " · reviseRequired=" + (decisionHints.reviseRequiredTotal || 0)
          + " · evidenceMissing=" + (decisionHints.evidenceMissingTotal || 0)
          + " · autoApproveAllowed=false"
        : "reviewDecisionHint=unavailable · autoApproveAllowed=false";
      var readiness = item.gradingEvidenceReadinessSummary && item.gradingEvidenceReadinessSummary.summary
        ? item.gradingEvidenceReadinessSummary
        : null;
      var readinessSummary = readiness ? readiness.summary : {};
      var readinessText = document.createElement("p");
      readinessText.textContent = readiness
        ? "GradingEvidenceReadiness=" + (readiness.status || "UNKNOWN")
          + " · evidenceReadyTotal=" + (readinessSummary.evidenceReadyTotal || 0)
          + " · missingEvidenceTotal=" + (readinessSummary.missingEvidenceTotal || 0)
          + " · controlledCommandMissingTotal=" + (readinessSummary.controlledCommandMissingTotal || 0)
          + " · readonlyStaticMissingTotal=" + (readinessSummary.readonlyStaticMissingTotal || 0)
          + " · autoApproveAllowed=false"
        : "GradingEvidenceReadiness=unavailable · autoApproveAllowed=false";

      button.appendChild(title);
      button.appendChild(meta);
      button.appendChild(desc);
      button.appendChild(decision);
      button.appendChild(readinessText);
      var reviewKind = item.realDemoArtifact === true ? reviewKindFromRealDemoItem(item) : "";
      var reviewHref = reviewKind ? reviewPageHref(reviewKind, taskId) : "";
      if (item.realDemoArtifact === true && item.dynamicTaskAvailable !== true && item.syntheticTaskAvailable !== true) {
        button.disabled = true;
        button.title = "本地产物存在，但当前 store 没有对应 WAITING_REVIEW 任务；先运行真实 workflow 或 one-click 写入 store。";
      } else {
        button.addEventListener("click", function () {
          loadTaskDetail(taskId, { updateUrl: true });
        });
      }
      queue.appendChild(button);
      if (reviewHref) {
        var reviewLink = document.createElement("a");
        reviewLink.className = "pill strong";
        reviewLink.href = reviewHref;
        reviewLink.textContent = reviewPageLabel(reviewKind);
        reviewLink.setAttribute("data-review-page-link", reviewKind);
        reviewLink.setAttribute("data-agent-report-preserved", boolText(!!getQueryAgentReport()));
        reviewLink.setAttribute("data-core-db-path-preserved", boolText(!!(state.coreDbPath || getQueryCoreDbPath())));
        queue.appendChild(reviewLink);
      }
    });
  }

  function summarizeControlledEvidence(signal, detailEvidence) {
    var sourceMode = signal && signal.sourceMode ? signal.sourceMode : "STATIC_HTML_FALLBACK";
    var executed = signal && typeof signal.executed !== "undefined" ? signal.executed : 0;
    var passed = signal && typeof signal.passed !== "undefined" ? signal.passed : 0;
    var earnedScore = signal && typeof signal.earnedScore !== "undefined" ? signal.earnedScore : 0;
    var totalScore = signal && typeof signal.totalControlledScore !== "undefined" ? signal.totalControlledScore : 0;
    var visible = detailEvidence && detailEvidence.visible === true;
    setText("controlled-evidence-source-mode", sourceMode);
    setText("controlled-evidence-summary", "executed=" + executed + " · passed=" + passed + " · earnedScore=" + earnedScore + "/" + totalScore);
    setText("controlled-evidence-detail-visible", "reviewDetail.controlledGradingEvidence.visible=" + visible);
  }

  function summarizeMergedEvidence(signal, detailEvidence) {
    if ((!signal || !signal.available) && detailEvidence && detailEvidence.visible === true) {
      var detailSummary = detailEvidence.summary || {};
      var latestReport = detailEvidence.latestReport || {};
      var coverage = latestReport.evidenceCoverage || {};
      signal = {
        sourceMode: "DETAIL_MERGED_GRADING_EVIDENCE",
        status: "MERGED_EVIDENCE_COLLECTED",
        available: true,
        reportTotal: detailEvidence.reportTotal || 0,
        latestReportType: detailEvidence.latestReportType,
        latestReportMode: detailEvidence.latestReportMode,
        latestSourceMode: detailEvidence.latestSourceMode,
        coveredCheckIds: coverage.coveredCheckIds || [],
        controlledDockerCheckTotal: detailSummary.controlledDockerCheckTotal || 0,
        readonlyStaticCheckTotal: detailSummary.readonlyStaticCheckTotal || 0,
        executed: detailSummary.executedTotal || 0,
        passedCheckTotal: detailSummary.passedCheckTotal || 0,
        failedCheckTotal: detailSummary.failedCheckTotal || 0,
        deferredCheckTotal: detailSummary.deferredCheckTotal || 0,
        earnedScore: detailSummary.earnedScore || 0,
        totalScore: detailSummary.totalScore || 0,
        coverageRatio: detailSummary.coverageRatio || 0,
        checkEvidenceReviewItemTotal: detailSummary.checkEvidenceReviewItemTotal || 0,
        manualCheckReviewTotal: detailSummary.manualCheckReviewTotal || 0,
        autoEvidenceReport: detailSummary.autoEvidenceReport === true,
        autoEvidenceStepTotal: detailSummary.autoEvidenceStepTotal || 0,
        autoEvidenceWarningTotal: detailSummary.autoEvidenceWarningTotal || 0,
        checkEvidenceReviewItems: Array.isArray(detailEvidence.checkEvidenceReviewItems)
          ? detailEvidence.checkEvidenceReviewItems
          : [],
        latestReport: latestReport,
        reviewDecisionHints: detailEvidence.reviewDecisionHints || {},
        safety: detailEvidence.safety || {}
      };
    }
    var sourceMode = signal && signal.sourceMode ? signal.sourceMode : "NO_MERGED_EVIDENCE_REPORT";
    var status = signal && signal.status ? signal.status : sourceMode;
    var available = signal && signal.available === true;
    var reportTotal = signal && typeof signal.reportTotal !== "undefined" ? signal.reportTotal : 0;
    var executed = signal && typeof signal.executed !== "undefined" ? signal.executed : 0;
    var passed = signal && typeof signal.passedCheckTotal !== "undefined" ? signal.passedCheckTotal : 0;
    var failed = signal && typeof signal.failedCheckTotal !== "undefined" ? signal.failedCheckTotal : 0;
    var deferred = signal && typeof signal.deferredCheckTotal !== "undefined" ? signal.deferredCheckTotal : 0;
    var earnedScore = signal && typeof signal.earnedScore !== "undefined" ? signal.earnedScore : 0;
    var totalScore = signal && typeof signal.totalScore !== "undefined" ? signal.totalScore : 0;
    var coverageRatio = signal && typeof signal.coverageRatio !== "undefined" ? signal.coverageRatio : 0;
    var controlledTotal = signal && typeof signal.controlledDockerCheckTotal !== "undefined" ? signal.controlledDockerCheckTotal : 0;
    var readonlyTotal = signal && typeof signal.readonlyStaticCheckTotal !== "undefined" ? signal.readonlyStaticCheckTotal : 0;
    var checkTotal = signal && typeof signal.checkEvidenceReviewItemTotal !== "undefined" ? signal.checkEvidenceReviewItemTotal : 0;
    var manualCheckTotal = signal && typeof signal.manualCheckReviewTotal !== "undefined" ? signal.manualCheckReviewTotal : 0;
    var checkItems = signal && Array.isArray(signal.checkEvidenceReviewItems) ? signal.checkEvidenceReviewItems : [];
    var coveredCheckIds = signal && Array.isArray(signal.coveredCheckIds) ? signal.coveredCheckIds : [];
    var latestReport = signal && signal.latestReport ? signal.latestReport : {};
    var reportType = (signal && signal.latestReportType) || latestReport.artifactReportType || "none";
    var latestSourceMode = (signal && signal.latestSourceMode) || latestReport.sourceMode || "none";
    var autoEvidenceReport = signal && signal.autoEvidenceReport === true;
    var autoStepTotal = signal && typeof signal.autoEvidenceStepTotal !== "undefined" ? signal.autoEvidenceStepTotal : 0;
    var autoWarningTotal = signal && typeof signal.autoEvidenceWarningTotal !== "undefined" ? signal.autoEvidenceWarningTotal : 0;
    var reviewDecisionHints = signal && signal.reviewDecisionHints ? signal.reviewDecisionHints : {};
    if (detailEvidence && detailEvidence.reviewDecisionHints) {
      reviewDecisionHints = detailEvidence.reviewDecisionHints;
    }
    var safety = signal && signal.safety ? signal.safety : {};
    var detailVisible = detailEvidence && detailEvidence.visible === true;
    setText("merged-evidence-status", status);
    setText("merged-evidence-source-mode", "sourceMode=" + sourceMode + " · latestSourceMode=" + latestSourceMode);
    setText("merged-evidence-report-type", "reportType=" + reportType);
    setText("merged-evidence-available", "available=" + boolText(available));
    setText("merged-evidence-report-total", "reportTotal=" + reportTotal);
    setText("merged-evidence-coverage-ratio", "coverageRatio=" + coverageRatio);
    setText(
      "merged-evidence-summary",
      "executed=" + executed
        + " · passed=" + passed
        + " · failed=" + failed
        + " · deferred=" + deferred
        + " · earnedScore=" + earnedScore + "/" + totalScore
    );
    setText("merged-evidence-detail-visible", "reviewDetail.mergedGradingEvidence.visible=" + detailVisible);
    setText("merged-evidence-controlled-total", "controlledDockerCheckTotal=" + controlledTotal);
    setText("merged-evidence-readonly-total", "readonlyStaticCheckTotal=" + readonlyTotal);
    setText("merged-evidence-check-total", "checkEvidenceReviewItemTotal=" + checkTotal);
    setText("merged-evidence-manual-check-total", "manualCheckReviewTotal=" + manualCheckTotal);
    setText("merged-evidence-covered-checks", "coveredCheckIds=" + (coveredCheckIds.length ? coveredCheckIds.join(",") : "none"));
    setText("merged-evidence-network", "networkAllowed=" + boolText(safety.networkAllowed === true));
    setText(
      "merged-evidence-auto-summary",
      "autoEvidenceReport=" + boolText(autoEvidenceReport)
        + " · stepTotal=" + autoStepTotal
        + " · warningTotal=" + autoWarningTotal
    );
    setText(
      "merged-evidence-review-decision-summary",
      "reviewDecisionHint=" + (reviewDecisionHints.overallHint || "NEEDS_EVIDENCE")
        + " · hintTotal=" + (reviewDecisionHints.hintTotal || 0)
        + " · approveReady=" + (reviewDecisionHints.approveReadyTotal || 0)
        + " · reviseRequired=" + (reviewDecisionHints.reviseRequiredTotal || 0)
        + " · evidenceMissing=" + (reviewDecisionHints.evidenceMissingTotal || 0)
        + " · autoApproveAllowed=false"
    );
    renderMergedEvidenceAutoSteps(latestReport.steps || [], latestReport.warnings || []);
    renderMergedEvidenceCheckItems(checkItems);
  }

  function summarizeReviewDecisionNotes(notes) {
    var summary = notes || {};
    var latest = summary.latest || {};
    setText(
      "review-decision-note-summary",
      "reviewDecisionNoteTotal=" + (summary.total || 0)
        + " · latestDecision=" + (latest.decision || "none")
        + " · reviewer=" + (latest.reviewer || "none")
        + " · statusChanged=false"
    );
  }

  function approveReadyDecision(latestDecision) {
    return latestDecision === "approve-ready";
  }

  function applyDecisionNoteNextStep(evidenceReady, noteRecorded, warningTotal, latestDecision) {
    var approveReady = approveReadyDecision(latestDecision);
    var nextAction = evidenceReady && !noteRecorded
      ? "record_review_decision_note_before_manual_approve"
      : evidenceReady && noteRecorded && approveReady
      ? "ready_for_human_approve"
      : evidenceReady && latestDecision === "needs-revision"
      ? "revise_grading_dsl_or_scoring_evidence"
      : evidenceReady && latestDecision === "needs-evidence"
      ? "collect_or_review_additional_grading_evidence"
      : "wait_for_grading_evidence";
    setText("review-detail-decision-note-next-step-status", "nextRequiredAction=" + nextAction);
    setText(
      "review-detail-decision-note-next-step-summary",
      "evidenceReady=" + boolText(evidenceReady)
        + " · reviewDecisionNoteRecorded=" + boolText(noteRecorded)
        + " · latestDecision=" + (latestDecision || "none")
        + " · approveReadyDecision=" + boolText(approveReady)
        + " · warningTotal=" + warningTotal
        + " · autoApproveAllowed=false"
    );
  }

  function applyFinalHumanApproveReadiness(evidenceReady, noteRecorded, warningTotal, applicable, latestDecision) {
    var approveReady = approveReadyDecision(latestDecision);
    var precheck = arguments.length > 5 && arguments[5] ? arguments[5] : {};
    var scorePreviewReady = precheck.scorePreviewReadyForDecisionNote;
    var scorePreviewStatus = precheck.scorePreviewStatus || "none";
    var scoreEarned = typeof precheck.scorePreviewEarnedScore === "undefined" ? "none" : precheck.scorePreviewEarnedScore;
    var scoreTotal = typeof precheck.scorePreviewTotalScore === "undefined" ? "none" : precheck.scorePreviewTotalScore;
    var scoreMissing = typeof precheck.scorePreviewMissingScore === "undefined" ? "none" : precheck.scorePreviewMissingScore;
    var finalReviewState = approveReady
      ? "READY_FOR_HUMAN_APPROVE"
      : latestDecision === "needs-revision"
      ? "NEEDS_REVISION"
      : latestDecision === "needs-evidence" || scorePreviewReady === false
      ? "NEEDS_MORE_EVIDENCE"
      : evidenceReady && noteRecorded !== true
      ? "WAITING_DECISION_NOTE"
      : "WAITING_EVIDENCE";
    var humanApproveReady = applicable === true
      && evidenceReady === true
      && noteRecorded === true
      && approveReady === true
      && warningTotal === 0;
    var status = humanApproveReady ? "READY_FOR_HUMAN_APPROVE" : "WAITING_REVIEW_INPUTS";
    var nextAction = humanApproveReady
      ? "human_may_call_single_task_approve_after_final_review"
      : noteRecorded && latestDecision === "needs-revision"
      ? "revise_grading_dsl_or_scoring_evidence"
      : noteRecorded && latestDecision === "needs-evidence"
      ? "collect_or_review_additional_grading_evidence"
      : evidenceReady
      ? "record_review_decision_note_before_manual_approve"
      : "complete_grading_evidence_before_manual_approve";
    setText("review-detail-final-approve-status", status);
    setText(
      "review-detail-final-approve-summary",
      "source=PreApproveReviewCheck + DecisionNoteNextStep"
        + " · finalReviewState=" + finalReviewState
        + " · humanApproveReady=" + boolText(humanApproveReady)
        + " · evidenceReady=" + boolText(evidenceReady)
        + " · reviewDecisionNoteRecorded=" + boolText(noteRecorded)
        + " · latestDecision=" + (latestDecision || "none")
        + " · approveReadyDecision=" + boolText(approveReady)
        + " · scorePreviewStatus=" + scorePreviewStatus
        + " · scorePreview=" + scoreEarned + "/" + scoreTotal
        + " · scorePreviewMissingScore=" + scoreMissing
        + " · scorePreviewReadyForDecisionNote=" + primitiveText(scorePreviewReady)
        + " · warningTotal=" + warningTotal
        + " · approveApiNotCalled=true"
    );
    setText("review-detail-final-approve-next-action", "nextRequiredAction=" + nextAction);
    setText(
      "review-detail-final-approve-safety",
      "singleTaskManualApproveOnly=" + boolText(humanApproveReady)
        + " · autoApproveAllowed=false"
        + " · batchStateChangeAllowed=false"
        + " · autoPublishAllowed=false"
        + " · realPublishAllowed=false"
    );
  }

  function readinessItemFromMergedEvidence(item) {
    var checkType = item.checkType || item.type || "unknown";
    var status = item.status || "";
    var evidenceReady = status === "PASSED" || status === "FAILED" || status === "ERROR" || typeof item.passed !== "undefined";
    var nextEvidence = evidenceReady
      ? "manual_review"
      : checkType === "stdout_contains" || checkType === "pytest"
      ? "controlled_command_evidence"
      : checkType === "file_exists" || checkType === "json_field" || checkType === "notebook_cell" || checkType === "log_keyword"
      ? "readonly_static_evidence"
      : "manual_review_only";
    return {
      checkId: item.checkId || item.id || "",
      checkType: checkType,
      status: status || (evidenceReady ? "COLLECTED" : "MISSING"),
      score: item.score || 0,
      earnedScore: item.earnedScore || 0,
      evidenceReady: evidenceReady,
      evidenceSourceKind: item.evidenceSourceKind || "unknown",
      recommendedNextEvidence: nextEvidence,
      recommendedAction: item.recommendedAction || (evidenceReady ? "verify_existing_evidence_and_score" : "collect_missing_grading_evidence"),
      manualReviewRequired: true
    };
  }

  function applyGradingEvidenceReadiness(detail) {
    var task = detail.task || {};
    var evidence = detail.mergedGradingEvidence || {};
    var rawItems = Array.isArray(evidence.checkEvidenceReviewItems) ? evidence.checkEvidenceReviewItems : [];
    var items = rawItems.map(readinessItemFromMergedEvidence);
    var ready = items.filter(function (item) { return item.evidenceReady === true; });
    var missing = items.filter(function (item) { return item.evidenceReady !== true; });
    var controlledMissing = missing.filter(function (item) { return item.recommendedNextEvidence === "controlled_command_evidence"; });
    var readonlyMissing = missing.filter(function (item) { return item.recommendedNextEvidence === "readonly_static_evidence"; });
    var totalScore = items.reduce(function (total, item) { return total + Number(item.score || 0); }, 0);
    var coveredScore = ready.reduce(function (total, item) { return total + Number(item.score || 0); }, 0);
    var coverageRatio = totalScore ? Math.round((coveredScore / totalScore) * 10000) / 10000 : 0;
    var available = evidence.visible === true && items.length > 0;
    var status = available && missing.length === 0
      ? "READY_FOR_APPROVAL_RECOMMENDATION"
      : available
      ? "MISSING_EVIDENCE"
      : "NO_MERGED_EVIDENCE_REPORT";
    setText(
      "review-detail-evidence-readiness-summary",
      "source=GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence.checkEvidenceReviewItems"
        + " · taskId=" + (task.id || "none")
        + " · status=" + status
        + " · missingEvidenceTotal=" + missing.length
        + " · coverageRatio=" + coverageRatio
        + " · readExistingReportsOnly=true"
    );
    setText("review-detail-evidence-readiness-total", "evidenceReadyTotal=" + ready.length);
    applyGradingEvidenceActionGuide(task, status, missing.length, evidence.actionGuide || null);

    var list = clearNode("review-detail-evidence-readiness-list");
    if (!list) {
      return;
    }
    if (!items.length) {
      appendSignalItem(
        list,
        0,
        "no grading evidence readiness",
        [
          "available=false",
          "status=NO_MERGED_EVIDENCE_REPORT",
          "sandboxExecutedByReadiness=false"
        ],
        "recommendedAction=run_grade_evidence_merge_or_auto_before_approval · autoApproveAllowed=false"
      );
      return;
    }
    items.slice(0, 6).forEach(function (item, index) {
      appendSignalItem(
        list,
        index + 1,
        (item.checkId || "unknown_check") + " · " + item.checkType,
        [
          "evidenceReady=" + boolText(item.evidenceReady === true),
          "status=" + item.status,
          "source=" + item.evidenceSourceKind,
          "nextEvidence=" + item.recommendedNextEvidence
        ],
        "recommendedAction=" + item.recommendedAction
          + " · sandboxExecutedByReadiness=false · contestantCodeExecutedByReadiness=false"
      );
    });
  }

  function applyPreApproveReviewCheck(detail) {
    var task = detail.task || {};
    var evidence = detail.mergedGradingEvidence || {};
    var evidenceSummary = evidence.summary || {};
    var notes = detail.reviewDecisionNotes || (detail.reviewPage || {}).reviewDecisionNotes || {};
    var serverPrecheck = detail.preApproveReviewCheck || (detail.reviewPage || {}).preApproveReviewCheck || {};
    var serverSummary = serverPrecheck.summary || {};
    var applicable = task.taskType === "GRADING_GENERATION";
    var serverWarnings = Array.isArray(serverSummary.recommendedWarnings)
      ? serverSummary.recommendedWarnings
      : null;
    var evidenceReady = typeof serverSummary.evidenceReady === "boolean"
      ? serverSummary.evidenceReady
      : evidence.visible === true && (evidenceSummary.checkEvidenceReviewItemTotal || 0) > 0;
    var noteRecorded = typeof serverSummary.reviewDecisionNoteRecorded === "boolean"
      ? serverSummary.reviewDecisionNoteRecorded
      : (notes.total || 0) > 0;
    var warnings = serverWarnings || [];
    if (!serverWarnings) {
      if (applicable && !evidenceReady) {
        warnings.push("grading_evidence_missing_before_approve");
      }
      if (applicable && !noteRecorded) {
        warnings.push("review_decision_note_missing_before_approve");
      }
    }
    var status = serverPrecheck.status || (warnings.length ? "APPROVE_ALLOWED_WITH_WARNINGS" : "READY_FOR_HUMAN_APPROVE");
    setText("review-detail-pre-approve-status", status);
    setText(
      "review-detail-pre-approve-summary",
      "source=GET /api/review-tasks/{id}.reviewDetail"
        + " · applicable=" + boolText(applicable)
        + " · evidenceReady=" + boolText(evidenceReady)
        + " · reviewDecisionNoteRecorded=" + boolText(noteRecorded)
        + " · scorePreviewStatus=" + primitiveText(serverSummary.scorePreviewStatus)
        + " · scorePreviewReadyForDecisionNote=" + primitiveText(serverSummary.scorePreviewReadyForDecisionNote)
        + " · warningTotal=" + warnings.length
        + " · approvalStillAllowed=true"
    );
    var latestDecision = (notes.latest || {}).decision || "none";
    var recommendedDecision = decisionFromRecommendation(evidenceSummary.decisionNoteRecommendation || "");
    if (recommendedDecision && !noteRecorded) {
      applySuggestedDecision({
        decision: recommendedDecision,
        source: "reviewDetail.mergedGradingEvidence.summary.decisionNoteRecommendation",
        nextCoreAction: evidenceSummary.nextDecisionNoteAction || "record_review_decision_note_before_manual_approve",
        reason: evidenceSummary.decisionNoteRecommendationReason
          || ("Evidence report recommends " + recommendedDecision + " before manual approve.")
      });
    }
    applyDecisionNoteNextStep(evidenceReady, noteRecorded, warnings.length, latestDecision);
    applyFinalHumanApproveReadiness(evidenceReady, noteRecorded, warnings.length, applicable, latestDecision, serverSummary);

    var list = clearNode("review-detail-pre-approve-list");
    if (!list) {
      return;
    }
    appendSignalItem(
      list,
      1,
      "merged evidence readiness",
      [
        "evidenceReady=" + boolText(evidenceReady),
        "checkEvidenceReviewItemTotal=" + (evidenceSummary.checkEvidenceReviewItemTotal || 0),
        "reportTotal=" + (evidence.reportTotal || 0),
        "scorePreviewReadyForDecisionNote=" + primitiveText(serverSummary.scorePreviewReadyForDecisionNote)
      ],
      "approvalStillAllowed=true · autoApproveAllowed=false · realPublishAllowed=false"
    );
    appendSignalItem(
      list,
      "S",
      "score preview readiness",
      [
        "scorePreviewStatus=" + primitiveText(serverSummary.scorePreviewStatus),
        "scorePreview=" + primitiveText(serverSummary.scorePreviewEarnedScore)
          + "/" + primitiveText(serverSummary.scorePreviewTotalScore),
        "missingScore=" + primitiveText(serverSummary.scorePreviewMissingScore),
        "missingEvidenceTotal=" + primitiveText(serverSummary.scorePreviewMissingEvidenceTotal)
      ],
      "scorePreviewReadyForDecisionNote="
        + primitiveText(serverSummary.scorePreviewReadyForDecisionNote)
        + " · manualReviewRequired=true · autoApproveAllowed=false"
    );
    appendSignalItem(
      list,
      2,
      "decision note readiness",
      [
        "reviewDecisionNoteRecorded=" + boolText(noteRecorded),
        "noteTotal=" + (notes.total || 0),
        "latestDecision=" + ((notes.latest || {}).decision || "none")
      ],
      "warningCodes=" + (warnings.length ? warnings.join(",") : "none")
        + " · blocking=false · batchStateChangeAllowed=false"
    );
  }

  function applyGradingRecordReviewIntegration(detail) {
    var gradingRecords = detail.gradingRecords || {};
    var summary = gradingRecords.summary || {};
    var integration = gradingRecords.reviewIntegration || {};
    var latest = gradingRecords.latest || {};
    var stateValue = integration.state || summary.platformReviewState || "NO_GRADING_RECORD";
    var latestRecordId = integration.latestRecordId || latest.id || "none";
    var latestStatus = integration.latestStatus || latest.status || summary.latestStatus || "none";
    var latestDecision = integration.latestDecision || latest.reviewDecision || summary.latestReviewDecision || "none";
    var ready = integration.readyForAgentReview === true || summary.readyForAgentReview === true;
    var manualRequired = integration.manualRecordReviewRequired === true;
    var nextAction = integration.nextRequiredAction || summary.platformReviewNextRequiredAction || "create_grading_record_from_latest_evidence_report";
    var reviewCommand = integration.reviewCommand || (
      latestRecordId !== "none"
        ? "python lab_cli.py grade record-review --id " + latestRecordId + " --reviewer <reviewer> --decision approve-ready"
        : "python lab_cli.py grade record-create --report <grading_report> --submission-id <submission_id>"
    );
    var latestEarnedScore = typeof integration.latestEarnedScore === "undefined"
      ? summary.latestEarnedScore
      : integration.latestEarnedScore;
    var latestTotalScore = typeof integration.latestTotalScore === "undefined"
      ? summary.latestTotalScore
      : integration.latestTotalScore;
    var latestCoverageRatio = typeof integration.latestCoverageRatio === "undefined"
      ? summary.latestCoverageRatio
      : integration.latestCoverageRatio;
    var recordSource = integration.source || gradingRecords.source || "JsonTaskStore.gradingRecords";
    var scoreText = primitiveText(latestEarnedScore) + "/" + primitiveText(latestTotalScore);
    var coverage = primitiveText(latestCoverageRatio);
    var blockers = Array.isArray(integration.blockingReasons) ? integration.blockingReasons : [];
    var total = typeof gradingRecords.total === "undefined" ? 0 : gradingRecords.total;

    setText("review-detail-grading-record-status", stateValue);
    setText(
      "review-detail-grading-record-summary",
      "source=GET /api/review-tasks/{id}.reviewDetail.gradingRecords.reviewIntegration"
        + " · state=" + stateValue
        + " · recordSource=" + recordSource
        + " · readyForAgentReview=" + boolText(ready)
        + " · latestRecordId=" + latestRecordId
        + " · latestStatus=" + latestStatus
        + " · latestDecision=" + latestDecision
        + " · localOnly=true"
    );

    var list = clearNode("review-detail-grading-record-list");
    if (!list) {
      return;
    }
    appendSignalItem(
      list,
      "R",
      "grading record human review",
      [
        "recordTotal=" + total,
        "humanReviewRecordedTotal=" + (integration.humanReviewRecordedTotal || summary.humanReviewRecordedTotal || 0),
        "manualRecordReviewRequired=" + boolText(manualRequired),
        "readyForAgentReview=" + boolText(ready)
      ],
      "nextRequiredAction=" + nextAction
        + " · taskStatusChanged=false · autoApproveAllowed=false · realPublishAllowed=false"
    );
    appendSignalItem(
      list,
      "S",
      "latest grading record score",
      [
        "latestRecordId=" + latestRecordId,
        "score=" + scoreText,
        "coverageRatio=" + coverage,
        "reviewedBy=" + (integration.latestReviewedBy || summary.latestReviewedBy || "none")
      ],
      "reviewCommand=" + reviewCommand + " · commandExecutedFromPage=false"
    );
    appendSignalItem(
      list,
      "B",
      "grading record blockers",
      [
        "blockingReasons=" + (blockers.length ? blockers.join(",") : "none"),
        "nextRequiredAction=" + nextAction,
        "recordReviewChangesTaskStatus=" + boolText(integration.recordReviewChangesTaskStatus === true)
      ],
      "networkAccess=false · agentApiRequired=false · realPublish=false"
    );
  }

  function applyDecisionNoteRecorded(note, existingDetail) {
    var detail = existingDetail || {};
    var task = detail.task || { id: state.selectedTaskId || "", taskType: "GRADING_GENERATION" };
    var evidence = detail.mergedGradingEvidence || {};
    var syntheticDetail = {
      task: task,
      mergedGradingEvidence: evidence,
      reviewDecisionNotes: {
        visible: true,
        total: 1,
        latest: {
          decision: note.decision || "approve-ready",
          reviewer: note.reviewer || "teacher_1"
        }
      }
    };
    if (!evidence.visible && detail.reviewPage && detail.reviewPage.mergedGradingEvidence) {
      syntheticDetail.mergedGradingEvidence = detail.reviewPage.mergedGradingEvidence;
    }
    summarizeReviewDecisionNotes(syntheticDetail.reviewDecisionNotes);
    applyPreApproveReviewCheck(syntheticDetail);
    setText(
      "record-decision-note-status",
      "recorded=" + (note.decision || "approve-ready")
        + " · preApproveWarningRefreshed=true"
        + " · nextRequiredAction=ready_for_human_approve"
        + " · realPublishAllowed=false"
    );
  }

  function renderMergedEvidenceAutoSteps(steps, warnings) {
    var list = byId("merged-evidence-auto-step-list");
    if (!list) {
      return;
    }
    list.innerHTML = "";
    var renderedSteps = Array.isArray(steps) ? steps : [];
    var renderedWarnings = Array.isArray(warnings) ? warnings : [];
    if (!renderedSteps.length && !renderedWarnings.length) {
      var empty = document.createElement("div");
      empty.className = "artifact-item";
      empty.innerHTML = "<strong>no auto evidence steps</strong><span>等待 GRADING_EVIDENCE_AUTO_REPORT。</span>";
      list.appendChild(empty);
      return;
    }
    renderedSteps.slice(0, 6).forEach(function (step) {
      var node = document.createElement("div");
      node.className = "artifact-item";
      var title = document.createElement("strong");
      title.textContent = (step.id || "unknown_step") + " · " + (step.status || "UNKNOWN");
      var meta = document.createElement("span");
      meta.textContent = "mode=" + (step.mode || "none")
        + " · executed=" + (step.executed || 0)
        + " · passed=" + (step.passed || 0)
        + " · commandExecuted=" + boolText(step.commandExecuted === true);
      var safety = document.createElement("span");
      safety.textContent = "contestantCodeExecuted=" + boolText(step.contestantCodeExecuted === true)
        + " · reason=" + (step.reason || step.message || "none")
        + " · autoApproveAllowed=false";
      node.appendChild(title);
      node.appendChild(meta);
      node.appendChild(safety);
      list.appendChild(node);
    });
    renderedWarnings.slice(0, 4).forEach(function (warning) {
      var node = document.createElement("div");
      node.className = "artifact-item";
      var title = document.createElement("strong");
      title.textContent = "warning · " + (warning.code || warning.status || "UNKNOWN");
      var body = document.createElement("span");
      body.textContent = warning.message || warning.reason || "controlled evidence warning";
      node.appendChild(title);
      node.appendChild(body);
      list.appendChild(node);
    });
  }

  function renderMergedEvidenceCheckItems(items) {
    var list = byId("merged-evidence-check-list");
    if (!list) {
      return;
    }
    list.innerHTML = "";
    if (!Array.isArray(items) || items.length === 0) {
      var empty = document.createElement("div");
      empty.className = "artifact-item";
      empty.innerHTML = "<strong>no merged check evidence</strong><span>等待运行 merge_grading_evidence_reports 或 grade evidence-merge。</span>";
      list.appendChild(empty);
      return;
    }
    items.slice(0, 8).forEach(function (item) {
      var node = document.createElement("div");
      node.className = "artifact-item";
      var source = item.evidenceSource || {};
      var title = document.createElement("strong");
      title.textContent = (item.checkId || "unknown_check")
        + " · " + (item.checkType || "unknown")
        + " · " + (item.status || "UNKNOWN");
      var meta = document.createElement("span");
      meta.textContent = "source=" + (item.evidenceSourceKind || "unknown")
        + " · score=" + (item.earnedScore || 0) + "/" + (item.score || 0)
        + " · reportMode=" + (source.reportMode || "unknown")
        + " · action=" + (item.recommendedAction || "manual_review");
      var safety = document.createElement("span");
      safety.textContent = "manualReviewRequired=" + boolText(item.manualReviewRequired === true)
        + " · autoApproveAllowed=false · realPublishAllowed=false";
      node.appendChild(title);
      node.appendChild(meta);
      node.appendChild(safety);
      list.appendChild(node);
    });
  }

  function updateGradingReportEntry(detail) {
    var task = detail.task || {};
    var evidence = detail.mergedGradingEvidence || {};
    var summary = evidence.summary || {};
    var latestReport = evidence.latestReport || {};
    var latestReportPath = summary.latestReportPath || latestReport.artifactPath || latestReport.reportPath || "";
    var taskId = task.id || evidence.taskId || "";
    var link = byId("review-detail-grading-report-entry-link");
    var summaryNode = byId("review-detail-grading-report-entry-summary");
    if (!link || !summaryNode) {
      return;
    }
    if (evidence.visible === true && latestReportPath) {
      var href = gradingReportHref(latestReportPath, taskId);
      link.href = href;
      link.textContent = "打开评分报告";
      link.removeAttribute("aria-disabled");
      link.title = "GET /api/grading/report?file={file}&taskId={id}";
      summaryNode.textContent = "source=GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence.summary.latestReportPath"
        + " · latestReportPath=" + normalizeLocalPath(latestReportPath)
        + " · taskId=" + (taskId || "none")
        + " · entryHref=" + href
        + " · autoApproveAllowed=false · realPublishAllowed=false";
      return;
    }
    link.removeAttribute("href");
    link.textContent = "等待评分 evidence";
    link.setAttribute("aria-disabled", "true");
    link.title = "mergedGradingEvidence.visible=false · no grading report is available";
    summaryNode.textContent = "source=GET /api/review-tasks/{id}.reviewDetail.mergedGradingEvidence"
      + " · mergedEvidenceVisible=false"
      + " · taskId=" + (taskId || "none")
      + " · reportEntry=unavailable"
      + " · nextRequiredAction=run_grade_evidence_merge_before_final_grading_review";
  }

  function applyDslPreview(detail) {
    var page = detail.reviewPage || {};
    var preview = page.dslPreview || {};
    var task = detail.task || {};
    var previewSummary = preview.summary || {};
    var safePreview = preview.safePreview || {};
    var candidateSafety = preview.candidateSafety || {};
    var reviewSafety = preview.reviewSafety || {};
    var lines = [
      "source: GET /api/review-tasks/{id}.reviewPage.dslPreview",
      "taskId: " + (task.id || "none"),
      "taskType: " + (task.taskType || "UNKNOWN_TASK"),
      "kind: " + (preview.kind || "UNKNOWN_DSL"),
      "artifactKind: " + (preview.artifactKind || "UNKNOWN_ARTIFACT"),
      "artifactId: " + (preview.artifactId || "none"),
      "status: " + (preview.status || task.status || "UNKNOWN_STATUS"),
      "path: " + (preview.path || task.finalResultPath || "none"),
      "contentLoaded: " + boolText(preview.contentLoaded === true),
      "contentSource: " + (preview.contentSource || "none"),
      "schemaKind: " + (preview.schemaKind || "none"),
      "schemaValidated: " + boolText(preview.schemaValidated === true),
      "schemaValidationErrorTotal: " + (Array.isArray(preview.schemaValidationErrors) ? preview.schemaValidationErrors.length : 0),
      "documentKind: " + (preview.documentKind || "none"),
      "documentStatus: " + (preview.documentStatus || "none"),
      "title: " + (preview.title || "none"),
      "summary: " + objectSummary(previewSummary, 10),
      "safePreview: " + objectSummary(safePreview, 10),
      "candidateSafety: answerVisibleToCandidate=" + boolText(candidateSafety.answerVisibleToCandidate === true)
        + " · gradingRefVisibleToCandidate=" + boolText(candidateSafety.gradingRefVisibleToCandidate === true)
        + " · standardAnswerVisibleToCandidate=" + boolText(candidateSafety.standardAnswerVisibleToCandidate === true),
      "reviewSafety: readOnly=" + boolText(reviewSafety.readOnly !== false)
        + " · secretsRead=" + boolText(reviewSafety.secretsRead === true)
        + " · networkAccess=" + boolText(reviewSafety.networkAccess === true)
        + " · sandboxExecuted=" + boolText(reviewSafety.sandboxExecuted === true)
        + " · autoPublishAllowed=" + boolText(reviewSafety.autoPublishAllowed === true),
      "autoPublishAllowed: false",
      "realPublishAllowed: false"
    ];
    setText("review-detail-dsl-title", (preview.kind || "DSL") + " DSL Preview");
    setText("review-detail-dsl-status", preview.status || task.status || "UNKNOWN_STATUS");
    setText("review-detail-dsl-preview", lines.join("\n"));
  }

  function applyTimeline(detail) {
    var task = detail.task || {};
    var timeline = detail.reviewPage && Array.isArray(detail.reviewPage.timeline)
      ? detail.reviewPage.timeline
      : [];
    var list = byId("review-detail-timeline-list");
    setText("review-detail-timeline-trace", task.traceId || "trace_unknown");
    if (!list) {
      return;
    }
    list.innerHTML = "";
    if (!timeline.length) {
      var empty = document.createElement("li");
      empty.textContent = "No timeline events · source=GET /api/review-tasks/{id}.reviewPage.timeline";
      list.appendChild(empty);
      return;
    }
    timeline.slice(0, 8).forEach(function (event) {
      var item = document.createElement("li");
      var prefix = event.order ? "#" + event.order + " " : "";
      item.textContent = prefix
        + (event.type || "EVENT")
        + " · " + (event.title || "untitled")
        + " · status=" + (event.status || "UNKNOWN")
        + " · refId=" + (event.refId || "none")
        + (event.actor ? " · actor=" + event.actor : "")
        + (event.occurredAt ? " · occurredAt=" + event.occurredAt : "");
      list.appendChild(item);
    });
  }

  function applyArtifactGroups(detail) {
    var page = detail.reviewPage || {};
    var groups = Array.isArray(page.artifactGroups) ? page.artifactGroups : [];
    var list = clearNode("review-detail-artifacts-list");
    var artifactTotal = groups.reduce(function (total, group) {
      var items = Array.isArray(group.items) ? group.items.length : 0;
      return total + (typeof group.total === "number" ? group.total : items);
    }, 0);

    setText("review-detail-artifacts-total", "artifactGroups=" + groups.length);
    setText(
      "review-detail-artifacts-summary",
      "source=GET /api/review-tasks/{id}.reviewPage.artifactGroups"
        + " · groupTotal=" + groups.length
        + " · artifactTotal=" + artifactTotal
        + " · autoPublishAllowed=false"
        + " · realPublishAllowed=false"
    );

    if (!list) {
      return;
    }
    if (!groups.length) {
      appendSignalItem(
        list,
        0,
        "artifactGroups unavailable",
        ["source=reviewPage.artifactGroups", "artifactTotal=0"],
        "No dynamic artifact groups are available for this review task."
      );
      return;
    }

    groups.slice(0, 6).forEach(function (group, groupIndex) {
      var items = Array.isArray(group.items) ? group.items : [];
      var firstItem = items[0] || {};
      var artifactLink = artifactHref(firstItem, detail.task && detail.task.id ? detail.task.id : state.selectedTaskId);
      var signalItem = appendSignalItem(
        list,
        groupIndex + 1,
        (group.kind || firstItem.kind || "ARTIFACT_GROUP") + " · total=" + (group.total || items.length),
        [
          "kind=" + (group.kind || firstItem.kind || "UNKNOWN_ARTIFACT"),
          "items=" + items.length,
          "status=" + (firstItem.status || "UNKNOWN_STATUS"),
          "realLlmCalled=" + boolText(firstItem.realLlmCalled === true),
          "artifactLink=" + (artifactLink || "none"),
          "realPublish=false"
        ],
        "artifactId=" + (firstItem.id || "none")
          + " · title=" + (firstItem.title || "untitled")
          + " · path=" + (firstItem.path || "none")
          + " · mode=" + (firstItem.mode || "UNKNOWN_MODE")
          + " · sandboxExecuted=" + boolText(firstItem.sandboxExecuted === true)
      );
      if (artifactLink) {
        var link = document.createElement("a");
        link.className = "pill strong";
        link.href = artifactLink;
        link.textContent = artifactLinkLabel(firstItem);
        link.setAttribute("data-artifact-link", "true");
        link.setAttribute("data-artifact-kind", group.kind || firstItem.kind || "UNKNOWN_ARTIFACT");
        signalItem.appendChild(link);
      }
    });
  }

  function applyQualitySignals(detail) {
    var page = detail.reviewPage || {};
    var signals = page.qualitySignals && typeof page.qualitySignals === "object" ? page.qualitySignals : {};
    var highlights = Array.isArray(signals.reviewHighlights) ? signals.reviewHighlights : [];
    var list = clearNode("review-detail-quality-list");
    var available = signals.available === true;

    setText("review-detail-quality-available", "available=" + boolText(available));
    setText(
      "review-detail-quality-summary",
      "source=GET /api/review-tasks/{id}.reviewPage.qualitySignals"
        + " · available=" + boolText(available)
        + " · reviewHighlights=" + highlights.length
        + " · autoApproveAllowed=false"
    );

    if (!list) {
      return;
    }

    var rendered = 0;
    highlights.slice(0, 4).forEach(function (highlight, index) {
      rendered += 1;
      appendSignalItem(
        list,
        index + 1,
        "reviewHighlight · " + (highlight.title || highlight.code || "quality_signal"),
        [
          "status=" + (highlight.status || "NEEDS_REVIEW"),
          "severity=" + (highlight.severity || "info"),
          "source=reviewHighlights"
        ],
        typeof highlight === "object" ? objectSummary(highlight, 6) : String(highlight)
      );
    });

    [
      ["overall", signals.overall],
      ["lab", signals.lab],
      ["materialCoverage", signals.materialCoverage],
      ["coverage", signals.coverage]
    ].forEach(function (entry) {
      if (rendered >= 8 || !entry[1] || typeof entry[1] !== "object") {
        return;
      }
      rendered += 1;
      appendSignalItem(
        list,
        rendered,
        entry[0] + " quality",
        ["source=qualitySignals." + entry[0], "available=" + boolText(available)],
        objectSummary(entry[1], 8)
      );
    });

    if (rendered === 0) {
      appendSignalItem(
        list,
        0,
        "qualitySignals unavailable",
        ["available=false", "reviewHighlights=0"],
        "No dynamic quality signals are available for this review task; manual review remains required."
      );
    }
  }

  function contentQualityItemSummary(item) {
    var blockers = Array.isArray(item.blockers) ? item.blockers : [];
    var warnings = Array.isArray(item.warnings) ? item.warnings : [];
    return "readyForManualReview=" + boolText(item.readyForManualReview === true)
      + " · readyForImportPreview=" + boolText(item.readyForImportPreview === true)
      + " · requiresRevisionBeforeImportPreview=" + boolText(item.requiresRevisionBeforeImportPreview === true)
      + " · requiresEvidenceBeforeFinalApproval=" + boolText(item.requiresEvidenceBeforeFinalApproval === true)
      + " · blockerTotal=" + blockers.length
      + " · warningTotal=" + warnings.length
      + " · evidenceStatus=" + (item.evidenceStatus || "NOT_REQUIRED")
      + " · next=" + (item.recommendedAction || "manual_review_required");
  }

  function appendContentQualityIssues(parent, item, offset) {
    var issues = [];
    if (Array.isArray(item.blockers)) {
      item.blockers.forEach(function (issue) {
        issues.push({ severity: "BLOCKER", issue: issue });
      });
    }
    if (Array.isArray(item.warnings)) {
      item.warnings.forEach(function (issue) {
        issues.push({ severity: "WARNING", issue: issue });
      });
    }
    issues.slice(0, 4).forEach(function (entry, index) {
      var issue = entry.issue || {};
      appendSignalItem(
        parent,
        offset + index + 1,
        (item.kind || "dsl") + " issue · " + (issue.code || issue.field || "content_quality_issue"),
        [
          "severity=" + entry.severity,
          "field=" + (issue.field || "none"),
          "reason=" + (issue.reason || "manual_review_required")
        ],
        objectSummary(issue, 6)
      );
    });
    return issues.length;
  }

  function applyContentQualityDecision(detail) {
    var summary = reviewPageValue(detail, "contentQualitySummary");
    var list = clearNode("review-detail-content-quality-list");
    var items = summary && summary.items && typeof summary.items === "object" ? summary.items : {};
    var itemKeys = Object.keys(items);
    var decision = summary.decision || {};
    var decisionStatus = summary.decisionStatus || decision.decisionStatus || "UNKNOWN";
    var available = summary.available === true || itemKeys.length > 0;

    setText("review-detail-content-quality-status", "decisionStatus=" + decisionStatus);
    setText(
      "review-detail-content-quality-summary",
      "source=GET /api/review-tasks/{id}.reviewDetail.contentQualitySummary"
        + " + reviewPage.contentQualitySummary"
        + " · available=" + boolText(available)
        + " · decisionStatus=" + decisionStatus
        + " · recommendedAction=" + (summary.recommendedAction || decision.recommendedAction || "manual_review_required")
        + " · readyForImportPreviewKinds=" + (
          Array.isArray(summary.readyForImportPreviewKinds) ? summary.readyForImportPreviewKinds.join(",") : "none"
        )
        + " · blockedKinds=" + (
          Array.isArray(decision.blockedKinds) ? decision.blockedKinds.join(",") : "none"
        )
        + " · evidenceRequiredKinds=" + (
          Array.isArray(decision.evidenceRequiredKinds) ? decision.evidenceRequiredKinds.join(",") : "none"
        )
        + " · autoApproveAllowed=false"
    );

    if (!list) {
      return;
    }

    if (!available) {
      appendSignalItem(
        list,
        0,
        "contentQualitySummary unavailable",
        ["available=false", "manualReviewRequired=true"],
        "No Real DSL content quality decision is available for this task; keep manual review before import preview."
      );
      return;
    }

    appendSignalItem(
      list,
      "D",
      "summary decision · " + decisionStatus,
      [
        "recommendedAction=" + (summary.recommendedAction || decision.recommendedAction || "manual_review_required"),
        "requiresRevisionBeforeImportPreview=" + boolText(summary.requiresRevisionBeforeImportPreview === true),
        "requiresEvidenceBeforeFinalApproval=" + boolText(summary.requiresEvidenceBeforeFinalApproval === true),
        "manualReviewRequired=" + boolText(summary.manualReviewRequired !== false),
        "realPublishAllowed=false"
      ],
      "blockingIssueTotal=" + (summary.blockingIssueTotal || decision.blockingIssueTotal || 0)
        + " · warningIssueTotal=" + (summary.warningIssueTotal || decision.warningIssueTotal || 0)
        + " · createImportPreviewOnlyAfterApproved=true"
        + " · finalApprovalStillManual=true"
    );

    itemKeys.slice(0, 6).forEach(function (key, index) {
      var item = items[key] || {};
      appendSignalItem(
        list,
        index + 1,
        (item.kind || key) + " · " + (item.decisionStatus || item.status || "CONTENT_QUALITY_REVIEW"),
        [
          "kind=" + (item.kind || key),
          "readyForImportPreview=" + boolText(item.readyForImportPreview === true),
          "requiresRevision=" + boolText(item.requiresRevisionBeforeImportPreview === true),
          "requiresEvidence=" + boolText(item.requiresEvidenceBeforeFinalApproval === true),
          "recommendedAction=" + (item.recommendedAction || "manual_review_required")
        ],
        contentQualityItemSummary(item)
      );
      appendContentQualityIssues(list, item, itemKeys.length + index * 4);
    });
  }

  function applyPlatformImportPreviews(detail) {
    var actions = reviewPageValue(detail, "platformImportPreviewActions");
    var preview = reviewPageValue(detail, "platformImportPreview");
    var signoff = reviewPageValue(detail, "platformImportPreviewSignoff");
    var mockImport = reviewPageValue(detail, "agentEntityMockImport");
    var readinessReport = reviewPageValue(detail, "agentEntityReadinessReport");
    var readinessByEntityId = readinessItemByEntityId(readinessReport);
    var actionItems = Array.isArray(actions.items) ? actions.items : [];
    var previewItems = Array.isArray(preview.items) ? preview.items : [];
    var signoffItems = Array.isArray(signoff.items) ? signoff.items : [];
    var missingPreviewActions = Array.isArray(signoff.missingPreviewActions) ? signoff.missingPreviewActions : [];
    var mockImportItems = Array.isArray(mockImport.items) ? mockImport.items : [];
    var actionList = clearNode("review-detail-import-actions-list");
    var previewList = clearNode("review-detail-import-preview-list");
    var signoffList = clearNode("review-detail-import-signoff-list");
    var mockImportList = clearNode("review-detail-platform-entity-list");

    setText("review-detail-import-actions-total", "enabledTotal=" + (actions.enabledTotal || 0));
    setText(
      "review-detail-import-actions-summary",
      "source=GET /api/review-tasks/{id}.reviewPage.platformImportPreviewActions"
        + " · visible=" + boolText(actions.visible === true)
        + " · enabled=" + boolText(actions.enabled === true)
        + " · total=" + (actions.total || actionItems.length)
        + " · previewAlreadyCreatedTotal=" + (actions.previewAlreadyCreatedTotal || 0)
        + " · contentQualityReadyTotal=" + (actions.contentQualityReadyTotal || 0)
        + " · contentQualityBlockedTotal=" + (actions.contentQualityBlockedTotal || 0)
        + " · databaseWritten=" + boolText(actions.databaseWritten === true)
        + " · realAgentImport=" + boolText(actions.realAgentImport === true)
    );

    if (actionList) {
      if (!actionItems.length) {
        appendSignalItem(
          actionList,
          0,
          "import preview actions unavailable",
          ["enabled=false", "total=0"],
          "No platform import preview action is available for this review task."
        );
      }
      actionItems.slice(0, 6).forEach(function (item, index) {
        appendSignalItem(
          actionList,
          index + 1,
          (item.previewComponent || item.component || "ImportPreviewAction") + " · " + (item.agentEntity || "agent_entity"),
          [
            "enabled=" + boolText(item.enabled === true),
            "requiresApprovedTask=" + boolText(item.requiresApprovedTask === true),
            "previewAlreadyCreated=" + boolText(item.previewAlreadyCreated === true),
            "contentQualityReady=" + boolText(item.contentQualityReadyForImportPreview === true),
            "databaseWritten=" + boolText(item.databaseWritten === true),
            "realAgentImport=" + boolText(item.realAgentImport === true)
          ],
          "taskStatus=" + (item.taskStatus || actions.taskStatus || "UNKNOWN_STATUS")
            + " · artifactKind=" + (item.sourceArtifactKind || "UNKNOWN_ARTIFACT")
            + " · apiEndpoint=" + (item.apiEndpoint || "none")
            + " · mcpTool=" + (item.mcpTool || "none")
            + " · nextRequiredAction=" + (item.nextRequiredAction || "manual_review_required")
            + " · contentQualityStatus=" + (item.contentQualityStatus || "UNKNOWN")
            + " · contentQualityRecommendedAction=" + (
              item.contentQualityRecommendedAction || "review_source_dsl_content_before_import_preview"
            )
        );
      });
    }

    setText("review-detail-import-preview-total", "previewTotal=" + (preview.total || previewItems.length));
    setText(
      "review-detail-import-preview-summary",
      "source=GET /api/review-tasks/{id}.reviewPage.platformImportPreview"
        + " · visible=" + boolText(preview.visible === true)
        + " · total=" + (preview.total || previewItems.length)
        + " · agentEntities=" + (Array.isArray(preview.agentEntities) ? preview.agentEntities.join(",") : "none")
        + " · controlledEvidenceNextActionTotal=" + (preview.controlledEvidenceNextActionTotal || 0)
        + " · databaseWritten=" + boolText(preview.databaseWritten === true)
        + " · realAgentImport=" + boolText(preview.realAgentImport === true)
        + " · realPublishAllowed=" + boolText(preview.realPublishAllowed === true)
    );

    if (previewList) {
      if (!previewItems.length) {
        appendSignalItem(
          previewList,
          0,
          "platform import preview not created",
          ["previewTotal=0", "databaseWritten=false", "realAgentImport=false"],
          "Create an import preview after the task is approved; this read-only page does not write platform drafts."
        );
      }
      previewItems.slice(0, 6).forEach(function (item, index) {
        appendSignalItem(
          previewList,
          index + 1,
          (item.component || "PlatformImportPreview") + " · " + (item.agentEntity || "agent_entity"),
          [
            "sourceArtifactKind=" + (item.sourceArtifactKind || "UNKNOWN_ARTIFACT"),
            "draftStatus=" + (item.draftStatus || item.status || "UNKNOWN_STATUS"),
            "controlledEvidenceNextAction=" + boolText(!!item.controlledEvidenceNextAction),
            "databaseWritten=" + boolText(item.databaseWritten === true),
            "realPublishAllowed=" + boolText(item.realPublishAllowed === true)
          ],
          "nextRequiredAction=" + (item.nextRequiredAction || "review_platform_import_preview")
            + " · evidenceAction=" + ((item.controlledEvidenceNextAction || {}).nextRequiredAction || "none")
            + " · summary=" + objectSummary(item.summary || item.importPlan || item, 5)
        );
      });
    }

    setText("review-detail-import-signoff-ready", "readyForHumanSignoff=" + boolText(signoff.readyForHumanSignoff === true));
    setText(
      "review-detail-import-signoff-summary",
      "source=GET /api/review-tasks/{id}.reviewPage.platformImportPreviewSignoff"
        + " · readyForHumanSignoff=" + boolText(signoff.readyForHumanSignoff === true)
        + " · passedTotal=" + (signoff.passedTotal || 0)
        + " · missingPreviewTotal=" + (signoff.missingPreviewTotal || missingPreviewActions.length)
        + " · blockedTotal=" + (signoff.blockedTotal || 0)
        + " · preApproveReviewCheckWarningTotal="
        + (((signoff.preApproveReviewCheckSummary || {}).warningTotal) || 0)
        + " · approveReadyDecision="
        + boolText(((signoff.preApproveReviewCheckSummary || {}).approveReadyDecision) === true)
        + " · controlledEvidenceNextActionTotal="
        + (((signoff.summary || {}).controlledEvidenceNextActionTotal) || 0)
        + " · gradingEvidenceReportAvailable="
        + boolText(((signoff.gradingEvidenceReportSummary || {}).available) === true)
        + " · gradingEvidenceReadyForDecisionNote="
        + boolText(((signoff.gradingEvidenceReportSummary || {}).readyForDecisionNote) === true)
        + " · realAgentImport=" + boolText(signoff.realAgentImport === true)
    );

    if (signoffList) {
      if (!signoffItems.length && !missingPreviewActions.length) {
        appendSignalItem(
          signoffList,
          0,
          "platform import signoff unavailable",
          ["readyForHumanSignoff=false", "missingPreviewTotal=0"],
          "No signoff items are available for this review task."
        );
      }
      missingPreviewActions.slice(0, 4).forEach(function (item, index) {
        appendSignalItem(
          signoffList,
          index + 1,
          "missing preview · " + (item.previewComponent || item.component || "ImportPreview"),
          [
            "agentEntity=" + (item.agentEntity || "agent_entity"),
            "sourceArtifactKind=" + (item.sourceArtifactKind || "UNKNOWN_ARTIFACT"),
            "mcpTool=" + (item.mcpTool || "none")
          ],
          "apiEndpoint=" + (item.apiEndpoint || "none")
            + " · nextRequiredAction=" + (item.nextRequiredAction || "create_import_preview_for_manual_review")
        );
      });
      signoffItems.slice(0, 4).forEach(function (item, index) {
        appendSignalItem(
          signoffList,
          missingPreviewActions.length + index + 1,
          (item.component || "PlatformImportPreviewSignoff") + " · " + (item.agentEntity || "agent_entity"),
          [
            "status=" + (item.status || "NEEDS_HUMAN_SIGNOFF"),
            "passed=" + boolText(item.passed === true),
            "approveReadyDecision="
              + boolText(((item.preApproveReviewCheckSummary || {}).approveReadyDecision) === true),
            "controlledEvidenceNextAction=" + boolText(!!item.controlledEvidenceNextAction),
            "gradingEvidenceReport="
              + (((item.gradingEvidenceReportSummary || {}).status) || "NOT_AVAILABLE"),
            "databaseWritten=" + boolText(item.databaseWritten === true)
          ],
          "checks=" + (Array.isArray(item.checks) ? item.checks.join(",") : objectSummary(item, 4))
            + " · latestEvidenceReport=" + (((item.gradingEvidenceReportSummary || {}).latestReportPath) || "none")
            + " · evidenceCli=" + ((item.controlledEvidenceNextAction || {}).cliCommand || "none")
        );
      });
    }

    setText("review-detail-platform-entity-total", "mockImportTotal=" + (mockImport.total || mockImportItems.length));
    setText(
      "review-detail-platform-entity-summary",
      "source=GET /api/review-tasks/{id}.reviewPage.agentEntityMockImport"
        + " · visible=" + boolText(mockImport.visible === true)
        + " · total=" + (mockImport.total || mockImportItems.length)
        + " · listApi=GET /api/platform-entities?sourceTaskId={id}"
        + " · detailApi=GET /api/platform-entities/{id}"
        + " · mockStoreWritten=" + boolText(mockImport.safety && mockImport.safety.mockStoreWritten === true)
        + " · databaseWritten=" + boolText(mockImport.summary && mockImport.summary.databaseWritten === true)
        + " · realAgentImport=" + boolText(mockImport.summary && mockImport.summary.realAgentImport === true)
        + " · realPublishAllowed=" + boolText(mockImport.summary && mockImport.summary.realPublishAllowed === true)
    );

    if (mockImportList) {
      if (!mockImportItems.length) {
        appendSignalItem(
          mockImportList,
          0,
          "platform entity mock import not created",
          ["mockImportTotal=0", "databaseWritten=false", "realAgentImport=false"],
          "Run lab/exam/grade mock-import after import preview signoff; this page only reads local mock entity records."
        );
      }
      mockImportItems.slice(0, 6).forEach(function (item, index) {
        var entityId = item.id || "";
        var sourceTaskId = item.sourceTaskId || "";
        var href = agentEntityHref(entityId, sourceTaskId, item.entityType);
        var readinessItem = readinessByEntityId[entityId] || {};
        var pausedHandoffHref = href;
        appendSignalItem(
          mockImportList,
          index + 1,
          (item.entityType || "agent_entity") + " · " + (item.title || entityId || "local draft"),
          [
            "entityId=" + (entityId || "none"),
            "status=" + (item.status || "LOCAL_DRAFT_IMPORTED"),
            "sourceTaskId=" + (sourceTaskId || "none"),
            "signoffState=" + agentEntitySignoffState(readinessItem),
            "readyForSignoff=" + boolText(readinessItem.readyForAgentEntitySignoff === true),
            "signoffRecorded=" + boolText(readinessItem.signoffRecorded === true),
            "mockStoreWritten=" + boolText(item.mockStoreWritten === true),
            "databaseWritten=" + boolText(item.databaseWritten === true),
            "realAgentImport=" + boolText(item.realAgentImport === true),
            "realPublishAllowed=" + boolText(item.realPublishAllowed === true)
          ],
          "openDetail=" + href
            + " · pausedPlatformHandoffRoute=" + (pausedHandoffHref || "none")
            + " · signoffActionRoute=paused"
            + " · finalReviewRoute=paused"
            + " · listApi=GET /api/platform-entities?sourceTaskId=" + (sourceTaskId || "{taskId}")
            + " · detailApi=GET /api/platform-entities/" + (entityId || "{id}")
            + " · sourcePreviewArtifactId=" + (item.sourcePreviewArtifactId || "none")
            + " · sourceDslPath=" + (item.sourceDslPath || "none")
            + " · reviewer=" + (item.reviewer || "none")
            + " · " + agentEntityActivitySummary(readinessItem)
            + " · " + postSignoffChecklistSummary(readinessItem)
            + " · " + finalPublishReviewDecisionSummary(readinessItem)
        );
        if (mockImportList.lastElementChild && entityId) {
          var link = document.createElement("a");
          link.className = "pill strong";
          link.href = href;
          link.textContent = "打开实体详情";
          link.setAttribute("aria-label", "打开本地平台实体详情 " + entityId);
          mockImportList.lastElementChild.appendChild(link);
          var signoffLink = document.createElement("a");
          signoffLink.className = "pill";
          signoffLink.href = pausedHandoffHref;
          signoffLink.textContent = readinessItem.signoffRecorded === true ? "查看本地记录" : "平台签收暂停";
          signoffLink.setAttribute("aria-label", "查看平台实体暂停对接说明 " + entityId);
          mockImportList.lastElementChild.appendChild(signoffLink);
        }
      });
    }
  }

  function packagePill(value, strong) {
    var pill = document.createElement("span");
    pill.className = strong ? "pill strong" : "pill";
    pill.textContent = String(value || "-");
    return pill;
  }

  function renderTeachingPackageArtifact(kind, item) {
    var row = document.createElement("div");
    var taskId = item.taskId || "";
    var waitingReview = item.status === "WAITING_REVIEW";
    row.className = "teaching-package-row";
    row.setAttribute("data-package-kind", kind);
    row.setAttribute("data-package-task-id", taskId);

    var identity = document.createElement("div");
    var title = document.createElement("h3");
    var path = document.createElement("p");
    title.textContent = (item.label || kind) + " · " + (item.taskType || "UNKNOWN_TASK");
    path.textContent = "taskId=" + (taskId || "none") + " · " + (item.dslPath || "path unavailable");
    identity.appendChild(title);
    identity.appendChild(path);

    var validation = document.createElement("div");
    var contentQuality = item.contentQuality || {};
    validation.className = "package-validation";
    validation.appendChild(packagePill(item.status || "UNKNOWN_STATUS", item.status !== "REJECTED"));
    validation.appendChild(packagePill(
      "Schema=" + (item.schemaValidated === true ? "PASS" : "FAIL"),
      item.schemaValidated === true
    ));
    validation.appendChild(packagePill(
      "Quality=" + (contentQuality.status || "UNKNOWN"),
      contentQuality.blockingIssueTotal === 0
    ));

    var reasonField = document.createElement("label");
    var reasonInput = document.createElement("input");
    reasonField.className = "package-reason-field";
    reasonField.textContent = "退回原因";
    reasonInput.type = "text";
    reasonInput.placeholder = "退回时必填";
    reasonInput.setAttribute("data-package-reject-reason", kind);
    reasonInput.setAttribute("aria-label", (item.label || kind) + " 退回原因");
    reasonInput.disabled = !waitingReview;
    reasonField.appendChild(reasonInput);

    var actions = document.createElement("div");
    var detailButton = document.createElement("button");
    var approveButton = document.createElement("button");
    var rejectButton = document.createElement("button");
    actions.className = "package-artifact-actions";
    detailButton.type = "button";
    detailButton.textContent = "查看";
    detailButton.disabled = !taskId;
    detailButton.addEventListener("click", function () {
      loadTaskDetail(taskId);
    });
    approveButton.type = "button";
    approveButton.className = "primary";
    approveButton.textContent = "通过";
    approveButton.setAttribute("data-package-review-action", "approve");
    approveButton.setAttribute("data-task-id", taskId);
    approveButton.setAttribute("data-package-kind", kind);
    approveButton.setAttribute("data-package-action-enabled", waitingReview ? "true" : "false");
    approveButton.disabled = !waitingReview;
    rejectButton.type = "button";
    rejectButton.className = "danger";
    rejectButton.textContent = "退回";
    rejectButton.setAttribute("data-package-review-action", "reject");
    rejectButton.setAttribute("data-task-id", taskId);
    rejectButton.setAttribute("data-package-kind", kind);
    rejectButton.setAttribute("data-package-action-enabled", waitingReview ? "true" : "false");
    rejectButton.disabled = !waitingReview;
    actions.appendChild(detailButton);
    actions.appendChild(approveButton);
    actions.appendChild(rejectButton);

    var actionStatus = document.createElement("p");
    actionStatus.setAttribute("data-package-row-status", kind);
    actionStatus.textContent = waitingReview ? "等待人工决定" : "审核结论=" + item.status;
    identity.appendChild(actionStatus);

    row.appendChild(identity);
    row.appendChild(validation);
    row.appendChild(reasonField);
    row.appendChild(actions);
    return row;
  }

  function renderTeachingPackageReview(packageReview) {
    var panel = byId("teaching-package-review");
    var list = clearNode("teaching-package-artifacts");
    if (!panel) {
      return;
    }
    if (!packageReview || packageReview.available !== true) {
      panel.hidden = true;
      return;
    }

    panel.hidden = false;
    var progress = packageReview.reviewProgress || {};
    var validation = packageReview.validation || {};
    var candidateSafety = packageReview.candidateSafeExamPreview || {};
    var reviewedTotal = (progress.approved || 0) + (progress.rejected || 0);
    setText("teaching-package-status", packageReview.status || "WAITING_REVIEW");
    setText(
      "teaching-package-summary",
      "workflowRunId=" + (packageReview.workflowRunId || "none")
        + " · sourceRef=" + (packageReview.sourceRef || "none")
        + " · nextAction=" + (packageReview.nextAction || "review_remaining_artifacts")
    );
    setText("teaching-package-progress", reviewedTotal + " / " + (progress.total || 3));
    setText(
      "teaching-package-schema",
      (validation.schemaValidatedTotal || 0) + " / " + (validation.total || 3)
    );
    setText(
      "teaching-package-candidate-safety",
      candidateSafety.candidateSafe === true ? "SAFE" : "BLOCKED"
    );
    setText(
      "teaching-package-export-ready",
      packageReview.exportReady === true ? "READY" : "NOT_READY"
    );
    setText(
      "teaching-package-action-status",
      packageReview.status === "APPROVED"
        ? "ACTION_COMPLETE · 三项均已人工批准"
        : (packageReview.status === "NEEDS_REVISION"
          ? "ACTION_REJECTED_RECORDED · 教学包需要修订"
          : "ACTION_READY · 逐项人工审核")
    );
    var statusNode = byId("teaching-package-status");
    if (statusNode) {
      statusNode.className = packageReview.status === "NEEDS_REVISION"
        ? "pill blocked"
        : "pill strong";
    }
    if (list) {
      ["lab", "exam", "grading"].forEach(function (kind) {
        var item = packageReview.artifacts && packageReview.artifacts[kind];
        if (item) {
          list.appendChild(renderTeachingPackageArtifact(kind, item));
        }
      });
    }
  }

  function applySummary(summary) {
    if (!summary || typeof summary !== "object") {
      return;
    }
    var queue = summary.queueSummary || {};
    var priorityQueue = summary.reviewPriorityQueue || {};
    var controlledSignal = summary.controlledDockerEvidenceReviewSignal || {};
    var mergedSignal = summary.mergedGradingEvidenceReviewSignal || {};
    var readinessSignal = summary.gradingEvidenceReadinessSignal || {};
    renderTeachingPackageReview(summary.teachingPackageReview || null);
    setText("review-center-queue-total", queue.waitingReviewTotal || summary.total || 0);
    setText("review-center-priority-total", priorityQueue.summary ? priorityQueue.summary.queueTotal : 0);
    applyMvpReviewWorkspaceFromSummary(summary);
    summarizeControlledEvidence(controlledSignal, null);
    summarizeMergedEvidence(mergedSignal, null);
    if (readinessSignal && readinessSignal.enabled) {
      setText(
        "review-detail-evidence-readiness-summary",
        "source=GET /api/review-task-summary.reviewTaskSummary.gradingEvidenceReadinessSignal"
          + " · availableTotal=" + (readinessSignal.availableTotal || 0)
          + " · evidenceReadyTotal=" + (readinessSignal.evidenceReadyTotal || 0)
          + " · missingEvidenceTotal=" + (readinessSignal.missingEvidenceTotal || 0)
          + " · autoApproveAllowed=false"
      );
      setText("review-detail-evidence-readiness-total", "evidenceReadyTotal=" + (readinessSignal.evidenceReadyTotal || 0));
    }
  }

  function applyDetail(detail) {
    if (!detail || typeof detail !== "object") {
      return;
    }
    var task = detail.task || {};
    var summary = detail.summary || {};
    var policy = detail.reviewPolicy || {};
    var safety = detail.safety || {};
    var page = detail.reviewPage || {};
    var riskSummary = page.riskSummary || {};
    var taskId = task.id || "none";
    state.selectedTaskId = task.id || state.selectedTaskId || "";
    var taskTitle = task.title || "任务详情";
    setText("review-center-selected-task", taskId);
    setText("detail-title", taskTitle);
    setText("review-detail-subtitle", taskId + " · " + (task.taskType || "UNKNOWN_TASK") + " · " + (task.status || "UNKNOWN_STATUS"));
    setText("review-detail-artifact-total", summary.artifactTotal || 0);
    setText("review-detail-workflow-step-total", summary.workflowStepTotal || 0);
    setText("review-detail-status", policy.generatedContentStatus || task.status || "UNKNOWN_STATUS");
    setText("review-detail-auto-approve", boolText(policy.autoPublishAllowed === true || policy.autoApproveAllowed === true));
    setText("review-detail-task-type", task.taskType || "UNKNOWN_TASK");
    setText(
      "review-detail-api-summary",
      "source=GET /api/review-tasks/{id}"
        + " · reviewRequired=" + boolText(policy.reviewRequired)
        + " · rejectRequiresReason=" + boolText(policy.rejectRequiresReason)
        + " · artifactTotal=" + (summary.artifactTotal || 0)
        + " · workflowStepTotal=" + (summary.workflowStepTotal || 0)
        + " · riskLevel=" + (riskSummary.riskLevel || "unknown")
        + " · autoPublishAllowed=" + boolText(policy.autoPublishAllowed)
        + " · realPublishAllowed=" + boolText(policy.realPublishAllowed)
        + " · sandboxExecuted=" + boolText(safety.sandboxExecuted)
    );
    applyMvpReviewWorkspaceFromDetail(detail);
    applyDslPreview(detail);
    applyTimeline(detail);
    applyArtifactGroups(detail);
    applyQualitySignals(detail);
    applyContentQualityDecision(detail);
    applyPlatformImportPreviews(detail);
    updateGradingReportEntry(detail);
    if (page.agentEntityReadinessReport) {
      applyAgentEntityReadiness(
        page.agentEntityReadinessReport,
        "source=GET /api/review-tasks/{id}.reviewDetail.reviewPage.agentEntityReadinessReport"
      );
    } else {
      loadAgentEntityReadiness(task.id || "");
    }
    var evidence = detail.controlledGradingEvidence || null;
    var visible = evidence && evidence.visible === true;
    setText("controlled-evidence-detail-visible", "reviewDetail.controlledGradingEvidence.visible=" + visible);
    summarizeMergedEvidence({}, detail.mergedGradingEvidence || null);
    summarizeReviewDecisionNotes(detail.reviewDecisionNotes || page.reviewDecisionNotes || null);
    applyGradingEvidenceReadiness(detail);
    applyPreApproveReviewCheck(detail);
    applyGradingRecordReviewIntegration(detail);
  }

  function loadReviewCenterData() {
    state.coreDbPath = getQueryCoreDbPath();
    state.gradingDbPath = getQueryGradingDbPath();
    state.agentEntityRefreshRequested = getQueryAgentEntityRefreshRequested();
    refreshMvpWorkspaceContextLinks(getQueryTaskId());
    refreshStaticRealDemoReviewLinks();

    if (!window.fetch) {
      setState("STATIC_HTML_FALLBACK", "fetch unavailable", "page remains read-only");
      return;
    }

    var taskId = getQueryTaskId();
    safeFetchJson(summaryPath())
      .then(function (payload) {
        if (!payload || payload.success !== true || !payload.data) {
          throw new Error("INVALID_SUMMARY_PAYLOAD");
        }
        var summary = payload.data.reviewTaskSummary || {};
        if (!taskId) {
          var realDemoItem = summary.realDemoReviewQueue
            && summary.realDemoReviewQueue.items
            && summary.realDemoReviewQueue.items.filter(function (item) {
              return (item.dynamicTaskAvailable === true || item.syntheticTaskAvailable === true) && item.taskId;
            })[0];
          var firstItem = realDemoItem || (summary.reviewPriorityQueue
            && summary.reviewPriorityQueue.items
            && summary.reviewPriorityQueue.items[0]);
          taskId = firstItem && firstItem.taskId ? firstItem.taskId : "";
        }
        applySummary(summary);
        renderDynamicQueue(summary, taskId);
        return loadTaskDetail(taskId, { updateUrl: false });
      })
      .catch(function (error) {
        setState("STATIC_HTML_FALLBACK", "frontend/mock-data.json + static HTML", "apiLoadError=" + error.message);
      });
  }

  window.reviewCenterDataLoader = {
    state: state,
    load: loadReviewCenterData,
    loadTaskDetail: loadTaskDetail,
    renderDynamicQueue: renderDynamicQueue,
    applySummary: applySummary,
    applyDetail: applyDetail,
    applyGradingEvidenceReadiness: applyGradingEvidenceReadiness,
    applyGradingRecordReviewIntegration: applyGradingRecordReviewIntegration,
    applyContentQualityDecision: applyContentQualityDecision,
    updateGradingReportEntry: updateGradingReportEntry,
    runEvidenceAuto: runEvidenceAuto,
    gradingReportHref: gradingReportHref,
    loadAgentEntityReadiness: loadAgentEntityReadiness,
    applyAgentEntityReadiness: applyAgentEntityReadiness,
    loadCoreWorkflowReadiness: loadCoreWorkflowReadiness,
    applyCoreWorkflowReadiness: applyCoreWorkflowReadiness,
    loadAgentCoreExecutionReport: loadAgentCoreExecutionReport,
    applyAgentCoreExecutionReport: applyAgentCoreExecutionReport,
    copySuggestedCoreNextCommand: copySuggestedCoreNextCommand,
    copySuggestedCoreReviewUrl: copySuggestedCoreReviewUrl,
    copyAgentReportSuggestedCoreNextCommand: copyAgentReportSuggestedCoreNextCommand,
    reviewPageHref: reviewPageHref,
    refreshStaticRealDemoReviewLinks: refreshStaticRealDemoReviewLinks
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      setupEvidenceAutoAction();
      setupDecisionNoteAction();
      setupCoreNextStepCopyAction();
      setupAgentReportNextStepCopyAction();
      loadAgentCoreExecutionReport();
      loadReviewCenterData();
    });
  } else {
    setupEvidenceAutoAction();
    setupDecisionNoteAction();
    setupCoreNextStepCopyAction();
    setupAgentReportNextStepCopyAction();
    loadAgentCoreExecutionReport();
    loadReviewCenterData();
  }
}());
