(function () {
  "use strict";

  const state = {
    generatePath: "/api/phase2/workflows/content-generation/run",
    coreDbPath: "",
    gradingDbPath: "",
    agentReport: "",
    lastTaskIds: {},
  };

  const kinds = {
    lab: { taskType: "LAB_GENERATION", reviewPage: "lab-review.html" },
    exam: { taskType: "EXAM_GENERATION", reviewPage: "exam-review.html" },
    grading: { taskType: "GRADING_GENERATION", reviewPage: "grading-review.html" },
  };

  function $(id) {
    return document.getElementById(id);
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function setText(id, value) {
    const node = $(id);
    if (node) {
      node.textContent = value == null || value === "" ? "-" : String(value);
    }
  }

  function queryParam(name) {
    try {
      return new URLSearchParams(window.location.search || "").get(name) || "";
    } catch (error) {
      return "";
    }
  }

  function configureLocalContextFromQuery() {
    state.coreDbPath = queryParam("coreDbPath");
    state.gradingDbPath = queryParam("gradingDbPath") || queryParam("dbPath");
    state.agentReport = queryParam("agentReport");
  }

  function withLocalContext(params) {
    const next = Object.assign({}, params || {});
    if (state.coreDbPath) {
      next.coreDbPath = state.coreDbPath;
    }
    if (state.gradingDbPath) {
      next.gradingDbPath = state.gradingDbPath;
    }
    if (state.agentReport) {
      next.agentReport = state.agentReport;
    }
    return next;
  }

  function withQuery(path, params) {
    const query = new URLSearchParams();
    Object.keys(params || {}).forEach(function (key) {
      const value = params[key];
      if (value !== undefined && value !== null && String(value) !== "") {
        query.set(key, String(value));
      }
    });
    const value = query.toString();
    return value ? path + "?" + value : path;
  }

  function setApiState(message, tone) {
    const node = $("generation-api-state");
    if (!node) {
      return;
    }
    node.textContent = message;
    node.classList.remove("pending", "error");
    if (tone) {
      node.classList.add(tone);
    }
  }

  function setProgress(completed) {
    const normalized = Math.max(0, Math.min(3, Number(completed) || 0));
    const bar = $("generation-progress-bar");
    if (bar) {
      bar.style.width = String((normalized / 3) * 100) + "%";
    }
    setText("generation-progress-label", normalized + " / 3");
  }

  function setLink(id, href, enabled) {
    const node = $(id);
    if (!node) {
      return;
    }
    node.href = enabled ? href : "#";
    node.setAttribute("aria-disabled", enabled ? "false" : "true");
    node.tabIndex = enabled ? 0 : -1;
  }

  function setTaskState(kind, status, message) {
    const row = document.querySelector('[data-kind="' + kind + '"]');
    if (row) {
      row.setAttribute("data-state", status);
    }
    setText("generation-" + kind + "-status", status);
    if (message) {
      setText("generation-" + kind + "-quality", message);
    }
  }

  function setAllTaskStates(status, message) {
    Object.keys(kinds).forEach(function (kind) {
      setTaskState(kind, status, message);
      if (status !== "WAITING_REVIEW") {
        setText("generation-" + kind + "-task", "task=not_created");
        setText("generation-" + kind + "-path", "dslPath=none");
        setLink("generation-" + kind + "-review", "#", false);
      }
    });
  }

  function providerRequestOptions() {
    const mode = $("generation-provider-mode").value === "real-llm" ? "real-llm" : "mock";
    const confirmed = $("generation-real-confirmation").checked === true;
    return {
      providerMode: mode,
      model: $("generation-model").value.trim(),
      baseUrl: $("generation-base-url").value.trim(),
      explicitRealCallOptIn: mode === "real-llm" && confirmed,
      confirmRealDsl: mode === "real-llm" && confirmed,
      confirmWaitingReview: mode === "real-llm" && confirmed,
      confirmNoAutoPublish: mode === "real-llm" && confirmed,
      repairOnSchemaFailure: $("generation-repair-schema").checked === true,
    };
  }

  function requestBody() {
    return Object.assign(
      {
        input: $("generation-source").value.trim(),
        reviewer: $("generation-reviewer").value.trim(),
        artifactProfile: "teaching-core",
        targetUsers: $("generation-target-users").value.trim(),
        durationMinutes: Number($("generation-duration").value),
        difficulty: $("generation-difficulty").value,
        teachingStyle: $("generation-teaching-style").value,
        techTags: $("generation-tech-tags").value.trim(),
      },
      providerRequestOptions()
    );
  }

  function validationError(body) {
    if (!body.input) {
      return { code: "VALIDATION_ERROR", message: "素材路径不能为空", errors: [{ field: "input", reason: "required" }] };
    }
    if (!body.reviewer) {
      return { code: "VALIDATION_ERROR", message: "审核人不能为空", errors: [{ field: "reviewer", reason: "required" }] };
    }
    if (!Number.isFinite(body.durationMinutes) || body.durationMinutes < 15 || body.durationMinutes > 480) {
      return { code: "VALIDATION_ERROR", message: "课时必须在 15 到 480 分钟之间", errors: [{ field: "durationMinutes", reason: "out_of_range" }] };
    }
    if (body.providerMode === "real-llm" && body.explicitRealCallOptIn !== true) {
      return {
        code: "REAL_LLM_CONFIRMATION_REQUIRED",
        message: "真实 LLM 模式需要显式确认",
        errors: [{ field: "explicitRealCallOptIn", reason: "required" }],
      };
    }
    return null;
  }

  function taskByType(tasks, taskType) {
    return safeArray(tasks).find(function (task) {
      return task && task.taskType === taskType;
    }) || {};
  }

  function qualityText(dsl) {
    const schema = dsl && dsl.schemaValidated === true ? "passed" : "needs_review";
    const content = dsl && dsl.contentQualitySummary ? dsl.contentQualitySummary : {};
    const quality = content.decisionStatus || content.status || "manual_review_required";
    return "schema=" + schema + " · quality=" + quality;
  }

  function renderTask(kind, task, dsl) {
    const config = kinds[kind];
    const taskId = task.id || dsl.taskId || "";
    const status = task.status || dsl.status || "NOT_CREATED";
    state.lastTaskIds[kind] = taskId;
    setTaskState(kind, status, qualityText(dsl));
    setText("generation-" + kind + "-task", "task=" + (taskId || "not_created"));
    setText("generation-" + kind + "-path", "dslPath=" + (dsl.dslPath || task.finalResultPath || "none"));
    setLink(
      "generation-" + kind + "-review",
      withQuery(config.reviewPage, withLocalContext({ taskId: taskId })),
      Boolean(taskId)
    );
  }

  function safeResult(payload) {
    const data = payload && payload.data ? payload.data : {};
    const generatedDsl = data.generatedDsl || {};
    return {
      success: payload && payload.success === true,
      code: payload && payload.code ? payload.code : "-",
      traceId: payload && payload.traceId ? payload.traceId : "-",
      mode: data.mode || "-",
      providerMode: data.providerMode || "-",
      artifactProfile: data.artifactProfile || "-",
      workflow: data.workflowRun
        ? {
            id: data.workflowRun.id || "-",
            status: data.workflowRun.status || "-",
            reviewRequired: data.workflowRun.reviewRequired === true,
            publishBlockedUntilApproved: data.workflowRun.publishBlockedUntilApproved === true,
          }
        : null,
      tasks: safeArray(data.createdTasks).map(function (task) {
        return {
          id: task.id || "-",
          taskType: task.taskType || "-",
          status: task.status || "-",
          finalResultPath: task.finalResultPath || "-",
        };
      }),
      generatedDsl: Object.keys(kinds).reduce(function (summary, kind) {
        const dsl = generatedDsl[kind] || {};
        summary[kind] = {
          taskId: dsl.taskId || "-",
          status: dsl.status || "-",
          dslPath: dsl.dslPath || "-",
          schemaValidated: dsl.schemaValidated === true,
          contentQualityStatus:
            dsl.contentQualitySummary && (dsl.contentQualitySummary.decisionStatus || dsl.contentQualitySummary.status)
              ? dsl.contentQualitySummary.decisionStatus || dsl.contentQualitySummary.status
              : "-",
        };
        return summary;
      }, {}),
      teachingPackageSummary: data.teachingPackageSummary || null,
      candidateSafeExamPreview: data.candidateSafeExamPreview || null,
      safety: {
        frontendDirectRealLlmCall: false,
        autoPublishAllowed: false,
        answerVisibleToCandidate: false,
        sandboxExecuted: false,
        realPublish: false,
      },
    };
  }

  function renderPayload(payload) {
    const data = payload && payload.data ? payload.data : {};
    const tasks = safeArray(data.createdTasks);
    const generatedDsl = data.generatedDsl || {};
    let completed = 0;
    let waitingReview = 0;

    Object.keys(kinds).forEach(function (kind) {
      const task = taskByType(tasks, kinds[kind].taskType);
      const dsl = generatedDsl[kind] || {};
      renderTask(kind, task, dsl);
      if (dsl.dslPath) {
        completed += 1;
      }
      if ((task.status || dsl.status) === "WAITING_REVIEW") {
        waitingReview += 1;
      }
    });

    const workflow = data.workflowRun || {};
    const firstTaskId = state.lastTaskIds.lab || state.lastTaskIds.exam || state.lastTaskIds.grading || "";
    setProgress(completed);
    setText("generation-workflow-status", workflow.status || "COMPLETED");
    setText("generation-dsl-total", completed + " / 3");
    setText("generation-review-total", waitingReview);
    setText("generation-provider-summary", data.providerMode || data.mode || "-");
    setText(
      "generation-safety-summary",
      "autoPublishAllowed=false · answerVisibleToCandidate=false · frontendDirectRealLlmCall=false"
    );
    setLink(
      "generation-review-center",
      withQuery("review-center.html", withLocalContext({ taskId: firstTaskId })),
      Boolean(firstTaskId)
    );
    setText("generation-result-json", JSON.stringify(safeResult(payload), null, 2));
    setApiState(
      completed === 3 && waitingReview === 3
        ? "COMPLETED · 教学包已生成，3 个任务等待人工审核"
        : "COMPLETED_WITH_REVIEW_REQUIRED · 请检查生成结果",
      ""
    );
  }

  function renderError(errorPayload) {
    const code = errorPayload && errorPayload.code ? errorPayload.code : "GENERATION_REQUEST_FAILED";
    const message = errorPayload && errorPayload.message ? errorPayload.message : "生成请求失败";
    const errors = safeArray(errorPayload && errorPayload.errors);
    const detail = errors
      .map(function (item) {
        return (item.field || "request") + ": " + (item.reason || "invalid");
      })
      .join(" · ");
    state.lastTaskIds = {};
    setAllTaskStates("ERROR", "generation failed · review task not created");
    setProgress(0);
    setText("generation-workflow-status", "FAILED");
    setText("generation-dsl-total", "0 / 3");
    setText("generation-review-total", "0");
    setLink("generation-review-center", "review-center.html", false);
    setText(
      "generation-result-json",
      JSON.stringify(
        {
          success: false,
          code: code,
          message: message,
          errors: errors,
          safety: {
            frontendDirectRealLlmCall: false,
            autoPublishAllowed: false,
            answerVisibleToCandidate: false,
          },
        },
        null,
        2
      )
    );
    setApiState(code + " · " + message + (detail ? " · " + detail : ""), "error");
  }

  async function postJson(path, body) {
    const response = await fetch(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok || payload.success === false) {
      throw payload;
    }
    return payload;
  }

  async function runGenerate(event) {
    if (event) {
      event.preventDefault();
    }
    const body = requestBody();
    const invalid = validationError(body);
    if (invalid) {
      renderError(invalid);
      return;
    }

    const button = $("generation-run");
    button.disabled = true;
    button.textContent = "生成中...";
    state.lastTaskIds = {};
    setAllTaskStates("GENERATING", "request submitted · waiting for schema validation");
    setProgress(0);
    setText("generation-workflow-status", "RUNNING");
    setText("generation-dsl-total", "0 / 3");
    setText("generation-review-total", "0");
    setText("generation-provider-summary", body.providerMode);
    setLink("generation-review-center", "review-center.html", false);
    setApiState("RUNNING · 后端正在生成并校验 Lab + Exam/Grading", "pending");

    try {
      const payload = await postJson(state.generatePath, body);
      renderPayload(payload);
    } catch (errorPayload) {
      renderError(errorPayload);
    } finally {
      button.disabled = false;
      button.textContent = "生成教学包";
    }
  }

  function syncProviderControls() {
    const realMode = $("generation-provider-mode").value === "real-llm";
    $("generation-model").disabled = !realMode;
    $("generation-base-url").disabled = !realMode;
    $("generation-real-confirmation").disabled = !realMode;
    if (!realMode) {
      $("generation-real-confirmation").checked = false;
    }
  }

  function init() {
    configureLocalContextFromQuery();
    syncProviderControls();
    $("generation-workspace-form").addEventListener("submit", runGenerate);
    $("generation-provider-mode").addEventListener("change", syncProviderControls);
  }

  window.generationWorkspaceDataLoader = {
    runGenerate: runGenerate,
    renderPayload: renderPayload,
    renderError: renderError,
    providerRequestOptions: providerRequestOptions,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
