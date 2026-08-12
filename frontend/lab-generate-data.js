(function () {
  "use strict";

  const state = {
    generatePath: "/api/labs/generate",
    defaultInput: "examples/input/demo-source.md",
    lastTaskId: "",
    coreDbPath: "",
    gradingDbPath: "",
    agentReport: "",
  };

  function $(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    const node = $(id);
    if (node) {
      node.textContent = value == null || value === "" ? "-" : String(value);
    }
  }

  function setApiState(message, tone) {
    const node = $("lab-generate-api-state");
    if (!node) {
      return;
    }
    node.textContent = message;
    node.classList.remove("pending", "error");
    if (tone) {
      node.classList.add(tone);
    }
  }

  function setHref(id, href, text) {
    const node = $(id);
    if (!node) {
      return;
    }
    node.href = href;
    if (text) {
      node.textContent = text;
    }
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
    const nextParams = Object.assign({}, params || {});
    if (state.coreDbPath) {
      nextParams.coreDbPath = state.coreDbPath;
    }
    if (state.gradingDbPath) {
      nextParams.gradingDbPath = state.gradingDbPath;
    }
    if (state.agentReport) {
      nextParams.agentReport = state.agentReport;
    }
    return nextParams;
  }

  function requestBodyWithLocalContext(body) {
    const nextBody = Object.assign({}, body || {});
    if (state.coreDbPath) {
      nextBody.coreDbPath = state.coreDbPath;
    }
    return nextBody;
  }

  function providerRequestOptions() {
    const providerMode = $("lab-generate-provider-mode");
    const model = $("lab-generate-model");
    const baseUrl = $("lab-generate-base-url");
    const explicitRealCall = $("lab-generate-explicit-real-call");
    const mode = providerMode && providerMode.value === "real-llm" ? "real-llm" : "mock";
    return {
      providerMode: mode,
      model: model && model.value ? model.value.trim() : "",
      baseUrl: baseUrl && baseUrl.value ? baseUrl.value.trim() : "",
      explicitRealCallOptIn: mode === "real-llm" && explicitRealCall && explicitRealCall.checked === true,
      confirmWaitingReview: mode === "real-llm",
      confirmNoAutoPublish: mode === "real-llm",
    };
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function providerContext(providerGeneration) {
    const provider = providerGeneration && providerGeneration.provider ? providerGeneration.provider : {};
    const audit =
      providerGeneration && providerGeneration.providerCallAuditEvent
        ? providerGeneration.providerCallAuditEvent
        : {};
    return {
      adapterId: provider.adapterId || "unknown",
      realLlmCalled: provider.realLlmCalled === true,
      networkAccess: provider.networkAccess === true,
      secretsRead: provider.secretsRead === true,
      providerAuditStatus: audit.status || "-",
      workflowId: audit.detail && audit.detail.workflowId ? audit.detail.workflowId : "-",
    };
  }

  function updateCloseLoopAction(view) {
    const task = view && view.task ? view.task : {};
    const taskId = task.id && task.id !== "-" ? task.id : "";
    const finalResultPath = task.finalResultPath && task.finalResultPath !== "-" ? task.finalResultPath : "";
    setText(
      "lab-generate-next-summary",
      "source=POST /api/labs/generate"
        + " · next=review_center_then_local_import_preview"
        + " · taskId=" + (taskId || "not_created")
    );
    setText("lab-generate-next-status", task.status || "WAITING_REVIEW");
    setText("lab-generate-next-task", "task=" + (taskId || "not_created"));
    setText("lab-generate-next-artifact", "finalResultPath=" + (finalResultPath || "none"));
    setText(
      "lab-generate-next-boundary",
      "autoPublishAllowed=false · realPublishAllowed=false"
        + " · coreDbPath=" + (state.coreDbPath || "none")
    );
    setText(
      "lab-generate-next-safety",
      "generatedStatus=" + (task.status || "WAITING_REVIEW")
        + " · requiresHumanReview=true"
        + " · realAgentImport=false"
        + " · realPublishAllowed=false"
    );
    setHref(
      "lab-generate-review-center-link",
      withQuery("review-center.html", withLocalContext({ taskId })),
      "打开审核中心"
    );
    setHref(
      "lab-generate-review-page-link",
      withQuery("lab-review.html", withLocalContext({ taskId })),
      "打开 Lab 审核页"
    );
    setHref(
      "lab-generate-import-preview-link",
      withQuery("agent-entities.html", withLocalContext({ sourceTaskId: taskId, entityKind: "lab" })),
      "打开本地导入预览"
    );
  }

  function buildResultView(payload) {
    const data = payload && payload.data ? payload.data : {};
    const task = data.task || {};
    const dsl = data.dsl || {};
    const material = data.materialAnalysis || {};
    const provider = providerContext(data.providerGeneration || {});
    const artifacts = safeArray(data.artifacts);
    const readiness = data.labFeatureReadiness || (data.providerGeneration && data.providerGeneration.labFeatureReadiness) || {};
    const spec = dsl.spec || {};
    const metadata = dsl.metadata || {};

    state.lastTaskId = task.id || "";

    setText("lab-generate-file-type", material.fileType || task.inputType || "markdown");
    setText("lab-generate-risk-count", material.riskCount == null ? 0 : material.riskCount);
    setText("lab-generate-tech-tags", safeArray(material.technologyTags).join(" / ") || "AI / Python / pytest");

    return {
      api: state.generatePath,
      success: payload.success === true,
      code: payload.code || "-",
      traceId: payload.traceId || "-",
      task: {
        id: task.id || "-",
        type: task.taskType || "-",
        status: task.status || data.status || "-",
        inputRef: task.inputRef || "-",
        finalResultPath: task.finalResultPath || data.dslPath || "-",
      },
      dsl: {
        kind: dsl.kind || "-",
        title: metadata.title || "-",
        objectiveTotal: safeArray(spec.objectives).length,
        materialTotal: safeArray(spec.materials).length,
      },
      materialAnalysis: {
        mode: material.mode || data.mode || "MOCK_ONLY",
        riskCount: material.riskCount == null ? 0 : material.riskCount,
        unknownShellExecuted: material.unknownShellExecuted === true,
      },
      provider,
      review: {
        reviewRequired: data.reviewRequired === true,
        generatedStatus: task.status || data.status || "-",
        autoPublishAllowed: false,
        realPublish: false,
      },
      labFeatureReadiness: {
        status: readiness.status || "-",
        completeForStableV1: readiness.completeForStableV1 === true,
        objectiveTotal: readiness.summary && readiness.summary.objectiveTotal != null ? readiness.summary.objectiveTotal : 0,
        stepTotal: readiness.summary && readiness.summary.stepTotal != null ? readiness.summary.stepTotal : 0,
        taskSpecificOutputCreated:
          readiness.requirements && readiness.requirements.taskSpecificOutputCreated === true,
        sourceMaterialReferenced:
          readiness.requirements && readiness.requirements.sourceMaterialReferenced === true,
        minimumTeachingQualityMet:
          readiness.requirements && readiness.requirements.minimumTeachingQualityMet === true,
      },
      artifacts: artifacts.map(function (artifact) {
        return {
          id: artifact.id || "-",
          kind: artifact.kind || "-",
          status: artifact.status || "-",
          path: artifact.path || "-",
        };
      }),
    };
  }

  function renderPayload(payload) {
    const view = buildResultView(payload);
    updateCloseLoopAction(view);
    const pre = $("lab-generate-result-json");
    if (pre) {
      pre.textContent = JSON.stringify(view, null, 2);
    }
    const status = view.task.status === "WAITING_REVIEW" ? "API_ACTION_COMPLETED · WAITING_REVIEW" : "API_ACTION_COMPLETED";
    setApiState(status, "");
  }

  function renderError(errorPayload) {
    const pre = $("lab-generate-result-json");
    const view = {
      api: state.generatePath,
      success: false,
      code: errorPayload && errorPayload.code ? errorPayload.code : "LAB_GENERATE_REQUEST_FAILED",
      message: errorPayload && errorPayload.message ? errorPayload.message : "本地生成请求失败",
      traceId: errorPayload && errorPayload.traceId ? errorPayload.traceId : "-",
      errors: safeArray(errorPayload && errorPayload.errors),
      review: {
        autoPublishAllowed: false,
        realPublish: false,
      },
    };
    if (pre) {
      pre.textContent = JSON.stringify(view, null, 2);
    }
    updateCloseLoopAction({
      task: {
        id: "",
        status: "NOT_CREATED",
        finalResultPath: "",
      },
    });
    setApiState(view.code, "error");
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

  async function runGenerate() {
    const input = $("lab-generate-input");
    const button = $("lab-generate-run");
    const inputPath = input ? input.value.trim() : state.defaultInput;
    if (!inputPath) {
      renderError({ code: "VALIDATION_ERROR", message: "素材路径不能为空", errors: [{ field: "input", reason: "required" }] });
      return;
    }

    if (button) {
      button.disabled = true;
    }
    setApiState("API_ACTION_PENDING · POST /api/labs/generate", "pending");
    try {
      const payload = await postJson(
        state.generatePath,
        requestBodyWithLocalContext(Object.assign({ input: inputPath }, providerRequestOptions()))
      );
      renderPayload(payload);
    } catch (errorPayload) {
      renderError(errorPayload);
    } finally {
      if (button) {
        button.disabled = false;
      }
    }
  }

  function openReviewDetail() {
    const target = state.lastTaskId
      ? withQuery("lab-review.html", withLocalContext({ taskId: state.lastTaskId }))
      : withQuery("review-center.html", withLocalContext({}));
    window.location.href = target;
  }

  function init() {
    configureLocalContextFromQuery();
    updateCloseLoopAction({
      task: {
        id: "",
        status: "NOT_CREATED",
        finalResultPath: "",
      },
    });
    const runButton = $("lab-generate-run");
    const reviewButton = $("lab-generate-review-link");
    if (runButton) {
      runButton.addEventListener("click", runGenerate);
    }
    if (reviewButton) {
      reviewButton.addEventListener("click", openReviewDetail);
    }
  }

  window.labGenerateDataLoader = {
    runGenerate,
    renderPayload,
    renderError,
    updateCloseLoopAction,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
