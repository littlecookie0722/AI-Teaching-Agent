(function () {
  "use strict";

  var state = {
    listPath: "/api/ai-tasks",
    waitingListPath: "/api/ai-tasks?status=WAITING_REVIEW",
    summaryPath: "/api/review-task-summary?limit=5&detailMode=light",
    detailPathTemplate: "/api/ai-tasks/{id}",
    coreDbPath: "",
    gradingDbPath: "",
    agentReport: "",
    requestedTaskId: "",
    coreTaskMode: false,
    selectedTaskId: "",
    loadedFromApi: false,
    gradingReportByTaskId: {},
    gradingRecordLoadStateByTaskId: {}
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

  function safeFetchJson(path) {
    return fetch(path, {
      method: "GET",
      headers: {"Accept": "application/json"},
      credentials: "same-origin"
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("HTTP_" + response.status);
      }
      return response.json();
    });
  }

  function queryParam(name) {
    try {
      return new URLSearchParams(window.location.search).get(name) || "";
    } catch (error) {
      return "";
    }
  }

  function withQuery(path, params) {
    var query = new URLSearchParams();
    Object.keys(params || {}).forEach(function (key) {
      var value = params[key];
      if (value !== undefined && value !== null && String(value) !== "") {
        query.set(key, String(value));
      }
    });
    var value = query.toString();
    return value ? path + "?" + value : path;
  }

  function configureDataSourceFromQuery() {
    var coreDbPath = queryParam("coreDbPath");
    var gradingDbPath = queryParam("gradingDbPath") || queryParam("dbPath");
    var agentReport = queryParam("agentReport");
    var requestedTaskId = queryParam("taskId") || queryParam("id");
    state.coreDbPath = coreDbPath;
    state.gradingDbPath = gradingDbPath;
    state.agentReport = agentReport;
    state.requestedTaskId = requestedTaskId;
    if (requestedTaskId) {
      state.selectedTaskId = requestedTaskId;
    }
    state.coreTaskMode = Boolean(coreDbPath);
    if (!state.coreTaskMode) {
      return;
    }
    state.listPath = withQuery("/api/backend/core-tasks", {coreDbPath: coreDbPath});
    state.waitingListPath = withQuery("/api/backend/core-tasks", {
      coreDbPath: coreDbPath,
      status: "WAITING_REVIEW"
    });
    state.detailPathTemplate = withQuery("/api/backend/core-tasks/{id}", {coreDbPath: coreDbPath});
  }

  function setApiState(status, source, detail) {
    setText("ai-task-api-status", status);
    setText("ai-task-api-source", source);
    setText("ai-task-api-detail", detail);
  }

  function detailPath(taskId) {
    return state.detailPathTemplate.replace("{id}", encodeURIComponent(taskId));
  }

  function setHref(id, href, text, disabled) {
    var link = byId(id);
    if (!link) {
      return;
    }
    link.href = disabled ? "#" : href;
    link.textContent = text;
    link.setAttribute("aria-disabled", disabled ? "true" : "false");
  }

  function taskType(task) {
    return String(task && (task.taskType || task.type) ? (task.taskType || task.type) : "").toUpperCase();
  }

  function fallbackTaskType(taskId) {
    var id = String(taskId || "").toLowerCase();
    if (id.indexOf("grading") >= 0 || id.indexOf("grade") >= 0) {
      return "GRADING_GENERATION";
    }
    if (id.indexOf("exam") >= 0) {
      return "EXAM_GENERATION";
    }
    if (id.indexOf("ppt") >= 0) {
      return "PPT_GENERATION";
    }
    return "LAB_GENERATION";
  }

  function fallbackWorkspaceTask() {
    var taskId = state.selectedTaskId || state.requestedTaskId || "task_grading_demo";
    return {
      id: taskId,
      taskType: fallbackTaskType(taskId),
      status: "WAITING_REVIEW",
      finalResultPath: "none"
    };
  }

  function entityKindFromTask(task) {
    var type = taskType(task);
    if (type.indexOf("LAB") >= 0) {
      return "lab";
    }
    if (type.indexOf("EXAM") >= 0) {
      return "exam";
    }
    if (type.indexOf("GRADING") >= 0 || type.indexOf("GRADE") >= 0) {
      return "grading";
    }
    if (type.indexOf("PPT") >= 0) {
      return "ppt";
    }
    return "";
  }

  function taskReviewHref(task) {
    return withQuery("review-center.html", {
      taskId: task && task.id ? task.id : "",
      coreDbPath: state.coreDbPath,
      gradingDbPath: state.gradingDbPath,
      agentReport: state.agentReport
    });
  }

  function taskGradingReportHref(task, reportPath) {
    return withQuery("grading-report.html", {
      taskId: task && task.id ? task.id : "",
      file: reportPath || "",
      coreDbPath: state.coreDbPath,
      gradingDbPath: state.gradingDbPath,
      agentReport: state.agentReport
    });
  }

  function gradingRecordsPath(taskId) {
    return withQuery("/api/grading/records", {
      taskId: taskId,
      dbPath: state.gradingDbPath
    });
  }

  function taskGradingWorkspaceHref(task) {
    return withQuery("grading-workspace.html", {
      taskId: task && task.id ? task.id : "",
      coreDbPath: state.coreDbPath,
      gradingDbPath: state.gradingDbPath,
      agentReport: state.agentReport
    });
  }

  function taskImportPreviewHref(task) {
    var entityKind = entityKindFromTask(task);
    return withQuery("agent-entities.html", {
      sourceTaskId: task && task.id ? task.id : "",
      entityKind: entityKind,
      coreDbPath: state.coreDbPath,
      gradingDbPath: state.gradingDbPath,
      agentReport: state.agentReport
    });
  }

  function supportsGradingWorkspace(task) {
    var type = taskType(task);
    return type.indexOf("GRADING") >= 0
      || type.indexOf("EXAM") >= 0
      || entityKindFromTask(task) === "grading";
  }

  function nextTaskWorkspaceAction(task, gradingReportPath, gradingRecordLoadState) {
    var status = String(task && task.status ? task.status : "").toUpperCase();
    if (status === "APPROVED" && entityKindFromTask(task)) {
      return "open_local_import_preview";
    }
    if (supportsGradingWorkspace(task) && gradingRecordLoadState === "LOAD_FAILED") {
      return "check_grading_record_api";
    }
    if (gradingReportPath) {
      return "open_grading_report_and_record_review_note";
    }
    if (supportsGradingWorkspace(task)) {
      return "open_grading_workspace";
    }
    return "open_review_center";
  }

  function taskTitle(task) {
    return task.title || task.name || task.id || "AI Task";
  }

  function taskBody(task, priorityItem) {
    var parts = [
      "inputRef=" + (task.inputRef || "none"),
      "finalResultPath=" + (task.finalResultPath || "none"),
      "reviewer=" + (task.reviewer || task.reviewedBy || "none")
    ];
    if (priorityItem) {
      parts.push("priority=" + (priorityItem.priority || priorityItem.priorityLevel || "UNKNOWN"));
      parts.push("recommendedAction=" + (priorityItem.recommendedAction || "open_review_detail"));
    }
    return parts.join(" · ");
  }

  function priorityByTaskId(summary) {
    var queue = summary && summary.reviewPriorityQueue ? summary.reviewPriorityQueue : {};
    var items = Array.isArray(queue.items) ? queue.items : [];
    var map = {};
    items.forEach(function (item) {
      if (item.taskId) {
        map[item.taskId] = item;
      }
    });
    return map;
  }

  function renderTaskCard(task, index, priorityItem) {
    var article = document.createElement("article");
    article.className = "task-card";
    article.setAttribute("tabindex", "0");
    article.setAttribute("data-task-id", task.id || "");
    if (state.selectedTaskId === task.id) {
      state.selectedTaskId = task.id || state.selectedTaskId;
      article.setAttribute("aria-current", "true");
    }

    var title = document.createElement("h3");
    var rank = document.createElement("span");
    rank.className = "rank";
    rank.textContent = String(index + 1);
    title.appendChild(rank);
    title.appendChild(document.createTextNode(" " + taskTitle(task)));
    article.appendChild(title);

    var meta = document.createElement("div");
    meta.className = "task-meta";
    [task.id || "none", task.taskType || "UNKNOWN_TASK", task.status || "UNKNOWN_STATUS"].forEach(function (value, pillIndex) {
      var pill = document.createElement("span");
      pill.className = pillIndex === 2 ? "pill strong" : "pill";
      pill.textContent = value;
      meta.appendChild(pill);
    });
    article.appendChild(meta);

    var body = document.createElement("p");
    body.textContent = taskBody(task, priorityItem);
    article.appendChild(body);

    article.addEventListener("click", function () {
      selectTask(task);
    });
    article.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectTask(task);
      }
    });
    return article;
  }

  function selectTask(task) {
    if (!task || !task.id) {
      return;
    }
    state.selectedTaskId = task.id;
    Array.prototype.forEach.call(document.querySelectorAll(".task-card[aria-current='true']"), function (node) {
      node.removeAttribute("aria-current");
    });
    Array.prototype.some.call(document.querySelectorAll(".task-card[data-task-id]"), function (node) {
      if (node.getAttribute("data-task-id") === task.id) {
        node.setAttribute("aria-current", "true");
        return true;
      }
      return false;
    });
    renderSelectedTask(task);
    safeFetchJson(detailPath(task.id))
      .then(function (payload) {
        var loadedTask = payload && payload.success === true && payload.data ? payload.data.task : null;
        if (loadedTask) {
          renderSelectedTask(loadedTask);
        }
      })
      .catch(function () {
        renderSelectedTask(task);
      });
  }

  function renderSelectedTask(task) {
    updateTaskExecutionWorkspace(task);
    loadLatestGradingRecord(task);
    var safePayload = {
      id: task.id || "none",
      taskType: task.taskType || "UNKNOWN_TASK",
      title: task.title || "none",
      status: task.status || "UNKNOWN_STATUS",
      inputRef: task.inputRef || "none",
      finalResultPath: task.finalResultPath || "none",
      traceId: task.traceId || "none",
      reviewRequired: task.status === "WAITING_REVIEW",
      autoPublishAllowed: false,
      batchStateChangeAllowed: false,
      realPublish: false,
      secretVisibleInFrontend: false
    };
    var pre = byId("ai-task-selected-json");
    if (pre) {
      pre.textContent = JSON.stringify(safePayload, null, 2);
    }
    var button = byId("ai-task-review-link");
    if (button) {
      button.onclick = function () {
        window.location.href = taskReviewHref(task);
      };
    }
  }

  function updateTaskExecutionWorkspace(task) {
    if (!task || !task.id) {
      return;
    }
    var type = taskType(task) || "UNKNOWN_TASK";
    var entityKind = entityKindFromTask(task);
    var supportsGrading = supportsGradingWorkspace(task);
    var gradingReportPath = state.gradingReportByTaskId[task.id] || "";
    var gradingRecordLoadState = state.gradingRecordLoadStateByTaskId[task.id] || "LOADING";
    var finalResultPath = task.finalResultPath || task.outputPath || "none";
    var nextAction = nextTaskWorkspaceAction(task, gradingReportPath, gradingRecordLoadState);
    setText(
      "task-workspace-summary",
      "source=" + (state.coreTaskMode ? "GET /api/backend/core-tasks" : "GET /api/ai-tasks")
        + " + GET /api/review-task-summary"
        + " · readonly=true"
        + " · selectedTask=" + task.id
        + " · coreDbPath=" + (state.coreDbPath || "none")
        + " · gradingDbPath=" + (state.gradingDbPath || "none")
        + " · agentReport=" + (state.agentReport || "none")
    );
    setText("task-workspace-selected", task.id);
    setText("task-workspace-review-state", (task.status || "UNKNOWN_STATUS") + " · " + type);
    setText("task-workspace-artifact", "finalResultPath=" + finalResultPath);
    setText(
      "task-workspace-safety",
      "candidateSafe=true · answerVisibleToCandidate=false · gradingRefVisibleToCandidate=false"
    );
    setText(
      "task-workspace-next-action",
      "nextAction=" + nextAction
        + " · entityKind=" + (entityKind || "none")
        + " · gradingRecordLoadState=" + gradingRecordLoadState
    );
    setText(
      "task-workspace-boundary",
      "method=GET only · no approve/reject · no publish · no real platform API"
    );
    setHref("task-workspace-review-link", taskReviewHref(task), "打开审核中心", false);
    setHref(
      "task-workspace-grading-report-link",
      taskGradingReportHref(task, gradingReportPath),
      gradingReportPath
        ? "打开评分报告"
        : (gradingRecordLoadState === "LOAD_FAILED" ? "评分记录加载失败" : (supportsGrading ? "等待评分 evidence" : "评分报告不适用")),
      !gradingReportPath
    );
    setHref(
      "task-workspace-grading-workspace-link",
      taskGradingWorkspaceHref(task),
      supportsGrading ? "打开评分工作台" : "评分工作台不适用",
      !supportsGrading
    );
    setHref(
      "task-workspace-import-preview-link",
      taskImportPreviewHref(task),
      entityKind ? "打开导入预览" : "导入预览不适用",
      !entityKind
    );
  }

  function loadLatestGradingRecord(task) {
    if (!task || !task.id) {
      return;
    }
    safeFetchJson(gradingRecordsPath(task.id))
      .then(function (payload) {
        var data = payload && payload.data ? payload.data : {};
        var items = Array.isArray(data.items) ? data.items : [];
        var latest = items[0] || {};
        state.gradingReportByTaskId[task.id] = latest.reportPath || "";
        state.gradingRecordLoadStateByTaskId[task.id] = items.length
          ? (data.mode === "LOCAL_SQLITE_GRADING_RECORD" ? "LOADED_LOCAL_SQLITE" : "LOADED_JSON_STAGING")
          : "EMPTY";
        if (state.selectedTaskId === task.id) {
          updateTaskExecutionWorkspace(task);
        }
      })
      .catch(function () {
        state.gradingReportByTaskId[task.id] = "";
        state.gradingRecordLoadStateByTaskId[task.id] = "LOAD_FAILED";
        if (state.selectedTaskId === task.id) {
          updateTaskExecutionWorkspace(task);
        }
      });
  }

  function renderTasks(tasks, summary) {
    var list = byId("ai-task-list");
    if (!list) {
      return;
    }
    var priorityMap = priorityByTaskId(summary);
    list.innerHTML = "";
    if (!tasks.length) {
      var empty = document.createElement("article");
      empty.className = "task-card";
      empty.innerHTML = "<h3>暂无 AI Task</h3><p>source=" + state.listPath + " · total=0 · readOnly=true</p>";
      list.appendChild(empty);
      return;
    }
    var requestedTask = tasks.filter(function (task) {
      return task.id === state.selectedTaskId;
    })[0];
    var selectedTask = requestedTask || tasks[0];
    if (state.requestedTaskId && !requestedTask) {
      setApiState(
        "API_READONLY_LOADED_WITH_TASK_NOT_FOUND",
        state.coreTaskMode ? "GET /api/backend/core-tasks" : "GET /api/ai-tasks",
        "requestedTaskId=" + state.requestedTaskId + " · taskNotFound=true · fallbackSelectedTask=" + (selectedTask.id || "none")
      );
    }
    state.selectedTaskId = selectedTask.id || state.selectedTaskId;
    tasks.forEach(function (task, index) {
      list.appendChild(renderTaskCard(task, index, priorityMap[task.id]));
    });
    renderSelectedTask(selectedTask);
  }

  function applySummary(allPayload, waitingPayload, summaryPayload) {
    var allTasks = allPayload && allPayload.data && Array.isArray(allPayload.data.items) ? allPayload.data.items : [];
    var waitingTasks = waitingPayload && waitingPayload.data && Array.isArray(waitingPayload.data.items)
      ? waitingPayload.data.items
      : [];
    var summary = summaryPayload && summaryPayload.data ? summaryPayload.data.reviewTaskSummary || {} : {};
    var queueSummary = summary.queueSummary || {};
    var priorityQueue = summary.reviewPriorityQueue || {};
    var prioritySummary = priorityQueue.summary || {};
    setText("ai-task-total", allPayload.data.total || allTasks.length);
    setText("ai-task-waiting-total", waitingPayload.data.total || waitingTasks.length || queueSummary.waitingReviewTotal || 0);
    setText("ai-task-urgent-total", prioritySummary.urgentTotal || 0);
    setText("ai-task-batch-state-change", boolText(false));
    setText("ai-task-list-filter", "状态过滤：WAITING_REVIEW · source=" + state.waitingListPath);
    renderTasks(waitingTasks.length ? waitingTasks : allTasks, summary);
  }

  function load() {
    configureDataSourceFromQuery();
    updateTaskExecutionWorkspace(fallbackWorkspaceTask());
    if (!window.fetch) {
      setApiState("STATIC_HTML_FALLBACK", "frontend/mock-data.json + static HTML", "fetch unavailable");
      return;
    }
    Promise.all([
      safeFetchJson(state.listPath),
      safeFetchJson(state.waitingListPath),
      safeFetchJson(state.summaryPath)
    ]).then(function (payloads) {
      payloads.forEach(function (payload) {
        if (!payload || payload.success !== true || !payload.data) {
          throw new Error("INVALID_API_RESPONSE");
        }
      });
      state.loadedFromApi = true;
      setApiState(
        state.coreTaskMode ? "BACKEND_CORE_TASKS_READONLY_LOADED" : "API_READONLY_LOADED",
        state.coreTaskMode
          ? "GET /api/backend/core-tasks + GET /api/review-task-summary"
          : "GET /api/ai-tasks + GET /api/review-task-summary",
        "readOnly=true · coreDbPath=" + (state.coreDbPath || "none") + " · autoPublishAllowed=false · batchStateChangeAllowed=false"
      );
      applySummary(payloads[0], payloads[1], payloads[2]);
    }).catch(function (error) {
      setApiState(
        "STATIC_HTML_FALLBACK",
        "frontend/mock-data.json + static HTML",
        "apiLoadError=" + error.message + " · readOnly=true"
      );
    });
  }

  window.aiTasksDataLoader = {
    state: state,
    load: load,
    renderTasks: renderTasks,
    renderSelectedTask: renderSelectedTask,
    updateTaskExecutionWorkspace: updateTaskExecutionWorkspace
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }
}());
