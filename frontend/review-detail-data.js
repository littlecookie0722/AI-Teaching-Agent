(function () {
  "use strict";

  var currentScript = document.currentScript || document.querySelector("script[src$='review-detail-data.js']");
  var state = {
    detailPathTemplate: "/api/review-tasks/{id}",
    defaultTaskId: currentScript ? currentScript.getAttribute("data-default-task-id") || "" : "",
    reviewKind: currentScript ? currentScript.getAttribute("data-review-kind") || "review" : "review",
    autoPublishAllowed: false,
    realPublishAllowed: false
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    var node = byId(id);
    if (node && value !== null && typeof value !== "undefined") {
      node.textContent = String(value);
    }
  }

  function boolText(value) {
    return value === true ? "true" : "false";
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

  function resolveTaskId() {
    var params = new URLSearchParams(window.location.search);
    return params.get("taskId") || params.get("id") || state.defaultTaskId;
  }

  function getQueryParam(name) {
    var params = new URLSearchParams(window.location.search);
    return params.get(name) || "";
  }

  function getQueryAgentReport() {
    return getQueryParam("agentReport");
  }

  function getQueryCoreDbPath() {
    return getQueryParam("coreDbPath");
  }

  function detailSourceLabel() {
    var label = "GET /api/review-tasks/{id}";
    if (getQueryAgentReport()) {
      label += "?agentReport={workflowReport}";
    }
    if (getQueryCoreDbPath()) {
      label += (label.indexOf("?") === -1 ? "?" : "&") + "coreDbPath={path}";
    }
    return label;
  }

  function detailPath(taskId) {
    var path = state.detailPathTemplate.replace("{id}", encodeURIComponent(taskId));
    var params = new URLSearchParams();
    var agentReport = getQueryAgentReport();
    var coreDbPath = getQueryCoreDbPath();
    if (agentReport) {
      params.set("agentReport", agentReport);
    }
    if (coreDbPath) {
      params.set("coreDbPath", coreDbPath);
    }
    var query = params.toString();
    return query ? path + "?" + query : path;
  }

  function setApiState(status, source, detail) {
    setText("review-detail-api-status", status);
    setText("review-detail-api-source", source);
    setText("review-detail-api-detail", detail);
  }

  function safeFetchJson(taskId) {
    return fetch(detailPath(taskId), {
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

  function primaryArtifact(detail) {
    var page = detail.reviewPage || {};
    var preview = page.dslPreview || {};
    var artifacts = detail.artifacts || [];
    if (preview.artifactId) {
      var matched = artifacts.filter(function (artifact) {
        return artifact.id === preview.artifactId;
      })[0];
      if (matched) {
        return matched;
      }
    }
    return artifacts.filter(function (artifact) {
      return String(artifact.kind || "").indexOf("_DSL") >= 0;
    })[0] || artifacts[0] || {};
  }

  function previewLines(detail) {
    var page = detail.reviewPage || {};
    var preview = page.dslPreview || {};
    var task = detail.task || {};
    var summary = detail.summary || {};
    var safety = detail.safety || {};
    var policy = detail.reviewPolicy || {};
    var artifact = primaryArtifact(detail);
    var candidatePreview = page.candidatePreview || detail.candidatePreview || {};
    var providerSummary = page.providerSummary || {};
    var qualitySummary = providerSummary.qualitySummary || {};
    var qualitySignals = page.qualitySignals || detail.qualitySignals || {};
    var pptPageReview = page.pptPageReview || detail.pptPageReview || {};

    var lines = [
      "source: GET /api/review-tasks/{id}.reviewDetail.reviewPage.dslPreview",
      "taskId: " + (task.id || preview.taskId || "none"),
      "taskType: " + (task.taskType || "none"),
      "title: " + (task.title || "none"),
      "status: " + (task.status || preview.status || "none"),
      "kind: " + (preview.kind || artifact.metadata && artifact.metadata.dslKind || "none"),
      "artifactKind: " + (preview.artifactKind || artifact.kind || "none"),
      "artifactId: " + (preview.artifactId || artifact.id || "none"),
      "path: " + (preview.path || artifact.path || task.finalResultPath || "none"),
      "artifactTotal: " + (summary.artifactTotal || (detail.artifacts || []).length || 0),
      "workflowStepTotal: " + (summary.workflowStepTotal || (detail.workflowSteps || []).length || 0),
      "reviewRequired: " + boolText(policy.reviewRequired === true),
      "autoPublishAllowed: " + boolText(state.autoPublishAllowed === true),
      "realPublishAllowed: " + boolText(state.realPublishAllowed === true),
      "sandboxExecuted: " + boolText(safety.sandboxExecuted === true)
    ];

    if (candidatePreview.answerVisibleToCandidate !== null && typeof candidatePreview.answerVisibleToCandidate !== "undefined") {
      lines.push("answerVisibleToCandidate: " + boolText(candidatePreview.answerVisibleToCandidate === true));
    }
    if (candidatePreview.standardAnswerRevealToCandidate !== null && typeof candidatePreview.standardAnswerRevealToCandidate !== "undefined") {
      lines.push("standardAnswerRevealToCandidate: " + boolText(candidatePreview.standardAnswerRevealToCandidate === true));
    }
    if (providerSummary.providerAdapters || providerSummary.providerIds || providerSummary.realLlmCalled !== null) {
      lines.push("providerSummary: " + objectSummary(providerSummary, 5));
    }
    if (Object.keys(qualitySummary).length) {
      lines.push("qualitySummary: " + objectSummary(qualitySummary, 6));
    }
    if (Object.keys(qualitySignals).length) {
      lines.push("qualitySignals: " + objectSummary(qualitySignals, 6));
    }
    if (pptPageReview.pageReviewSummary) {
      lines.push("pptPageReview: " + objectSummary(pptPageReview.pageReviewSummary, 6));
    }

    return lines.join("\n");
  }

  function renderTimeline(detail) {
    var list = byId("review-detail-timeline-list");
    if (!list) {
      return;
    }
    var page = detail.reviewPage || {};
    var timeline = page.timeline || [];
    if (!timeline.length) {
      return;
    }
    list.innerHTML = "";
    timeline.slice(0, 10).forEach(function (item) {
      var li = document.createElement("li");
      var parts = [
        item.title || item.type || "event",
        item.status || "UNKNOWN"
      ];
      if (item.refId) {
        parts.push(item.refId);
      }
      if (item.actor) {
        parts.push("actor=" + item.actor);
      }
      li.textContent = parts.join(" · ");
      list.appendChild(li);
    });
  }

  function applyDetail(detail, taskId) {
    var page = detail.reviewPage || {};
    var header = page.header || {};
    var task = detail.task || {};
    var summary = detail.summary || {};
    var preview = page.dslPreview || {};
    var artifact = primaryArtifact(detail);

    setApiState(
      "API_READONLY_LOADED",
      detailSourceLabel(),
      "taskId=" + taskId + " · autoPublishAllowed=false · realPublishAllowed=false"
    );
    setText("review-detail-selected-task", taskId);
    setText("review-detail-status", header.status || task.status || preview.status);
    setText("review-detail-task-id", header.taskId || task.id || taskId);
    setText("review-detail-task-type", header.taskType || task.taskType);
    setText("review-detail-artifact-total", summary.artifactTotal || (detail.artifacts || []).length || 0);
    setText("review-detail-title", header.title || task.title || "审核任务");
    setText("review-detail-dsl-path", preview.path || artifact.path || task.finalResultPath);
    setText("review-detail-dsl-title", (preview.kind || state.reviewKind).toUpperCase() + " DSL Preview");
    setText("review-detail-dsl-status", preview.status || artifact.status || task.status);
    setText("review-detail-dsl-preview", previewLines(detail));
    renderTimeline(detail);
  }

  function load() {
    var taskId = resolveTaskId();
    setText("review-detail-selected-task", taskId || "none");
    if (!taskId) {
      setApiState("STATIC_HTML_FALLBACK", "static HTML", "missing taskId · readOnly=true");
      return;
    }
    setApiState("DETAIL_LOAD_PENDING", detailSourceLabel(), "taskId=" + taskId + " · readOnly=true");
    safeFetchJson(taskId).then(function (payload) {
      if (!payload || payload.success !== true || !payload.data || !payload.data.reviewDetail) {
        throw new Error("INVALID_REVIEW_DETAIL_RESPONSE");
      }
      applyDetail(payload.data.reviewDetail, taskId);
    }).catch(function (error) {
      setApiState(
        "STATIC_HTML_FALLBACK",
        "static HTML + " + detailSourceLabel(),
        "DETAIL_LOAD_FAILED=" + error.message + " · readOnly=true · autoPublishAllowed=false"
      );
    });
  }

  window.reviewDetailDataLoader = {
    resolveTaskId: resolveTaskId,
    getQueryAgentReport: getQueryAgentReport,
    getQueryCoreDbPath: getQueryCoreDbPath,
    detailPath: detailPath,
    load: load
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }
}());
