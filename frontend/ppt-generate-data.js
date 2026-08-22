(function () {
  "use strict";

  const state = {
    generatePath: "/api/ppt/generate",
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

  function setState(message, tone) {
    const node = $("ppt-generate-api-state");
    if (!node) {
      return;
    }
    node.textContent = message;
    node.classList.remove("pending", "error");
    if (tone) {
      node.classList.add(tone);
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

  function configureLocalContext() {
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

  function requestBody(body) {
    const next = Object.assign({}, body || {});
    if (state.coreDbPath) {
      next.coreDbPath = state.coreDbPath;
    }
    return next;
  }

  function providerRequestOptions() {
    const providerMode = $("ppt-generate-provider-mode");
    const model = $("ppt-generate-model");
    const baseUrl = $("ppt-generate-base-url");
    const explicitRealCall = $("ppt-generate-explicit-real-call");
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

  function setHref(id, path, label) {
    const node = $(id);
    if (!node) {
      return;
    }
    node.href = path;
    node.textContent = label;
  }

  function updateActions(view) {
    const task = view && view.task ? view.task : {};
    const taskId = task.id && task.id !== "-" ? task.id : "";
    setText("ppt-generate-next-status", task.status || "WAITING_REVIEW");
    setText("ppt-generate-next-task", "task=" + (taskId || "not_created"));
    setText("ppt-generate-next-artifact", "pptDslPath=" + (view.pptDslPath || "none"));
    setText(
      "ppt-generate-next-boundary",
      "artifactGenerated=false · autoPublishAllowed=false · coreDbPath=" + (state.coreDbPath || "none")
    );
    setHref(
      "ppt-generate-review-center-link",
      withQuery("review-center.html", withLocalContext({ taskId })),
      "打开审核中心"
    );
    setHref(
      "ppt-generate-review-page-link",
      withQuery("ppt-review.html", withLocalContext({ taskId })),
      "打开 PPT 审核页"
    );
    setHref(
      "ppt-generate-import-preview-link",
      withQuery("agent-entities.html", withLocalContext({ sourceTaskId: taskId, entityKind: "ppt" })),
      "打开 PPT 导入预览"
    );
    setHref("ppt-generate-list-link", withQuery("ppt.html", withLocalContext({})), "返回 PPT 清单");
  }

  function buildView(payload) {
    const data = payload && payload.data ? payload.data : {};
    const task = data.task || {};
    const dsl = data.pptDsl || {};
    const metadata = dsl.metadata || {};
    const spec = dsl.spec || {};
    const providerGeneration = data.providerGeneration || {};
    const provider = providerGeneration.provider || {};
    const artifact = data.artifact || {};

    state.lastTaskId = task.id || "";
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
      },
      pptDslPath: data.pptDslPath || task.finalResultPath || "",
      ppt: {
        kind: dsl.kind || "-",
        id: metadata.id || "-",
        title: metadata.title || "-",
        slideTotal: Array.isArray(spec.slides) ? spec.slides.length : 0,
      },
      artifact: {
        id: artifact.id || "-",
        kind: artifact.kind || "PPT_DSL",
        status: artifact.status || task.status || "-",
        path: artifact.path || data.pptDslPath || "-",
      },
      provider: {
        adapterId: provider.adapterId || "unknown",
        realLlmCalled: provider.realLlmCalled === true,
        secretsRead: provider.secretsRead === true,
        networkAccess: provider.networkAccess === true,
      },
      review: {
        reviewRequired: data.reviewRequired === true,
        generatedStatus: task.status || data.status || "-",
        artifactGenerated: data.artifactGenerated === true,
        autoPublishAllowed: false,
        realPublish: false,
      },
    };
  }

  function renderPayload(payload) {
    const view = buildView(payload);
    const output = $("ppt-generate-result-json");
    if (output) {
      output.textContent = JSON.stringify(view, null, 2);
    }
    updateActions(view);
    setState(
      view.task.status === "WAITING_REVIEW" ? "API_ACTION_COMPLETED · WAITING_REVIEW" : "API_ACTION_COMPLETED",
      ""
    );
  }

  function renderError(errorPayload) {
    const view = {
      api: state.generatePath,
      success: false,
      code: errorPayload && errorPayload.code ? errorPayload.code : "PPT_GENERATE_REQUEST_FAILED",
      message: errorPayload && errorPayload.message ? errorPayload.message : "本地 PPT 生成请求失败",
      traceId: errorPayload && errorPayload.traceId ? errorPayload.traceId : "-",
      errors: Array.isArray(errorPayload && errorPayload.errors) ? errorPayload.errors : [],
      review: { autoPublishAllowed: false, realPublish: false },
    };
    const output = $("ppt-generate-result-json");
    if (output) {
      output.textContent = JSON.stringify(view, null, 2);
    }
    updateActions({ task: { id: "", status: "NOT_CREATED" }, pptDslPath: "" });
    setState(view.code, "error");
  }

  async function postJson(path, body) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok || payload.success === false) {
      throw payload;
    }
    return payload;
  }

  async function runGenerate() {
    const input = $("ppt-generate-input");
    const button = $("ppt-generate-run");
    const inputPath = input ? input.value.trim() : state.defaultInput;
    if (!inputPath) {
      renderError({ code: "VALIDATION_ERROR", message: "素材路径不能为空", errors: [{ field: "input", reason: "required" }] });
      return;
    }
    if (button) {
      button.disabled = true;
    }
    setState("API_ACTION_PENDING · POST /api/ppt/generate", "pending");
    try {
      renderPayload(
        await postJson(state.generatePath, requestBody(Object.assign({ input: inputPath }, providerRequestOptions())))
      );
    } catch (errorPayload) {
      renderError(errorPayload);
    } finally {
      if (button) {
        button.disabled = false;
      }
    }
  }

  function openReview() {
    window.location.href = state.lastTaskId
      ? withQuery("ppt-review.html", withLocalContext({ taskId: state.lastTaskId }))
      : withQuery("review-center.html", withLocalContext({}));
  }

  function init() {
    configureLocalContext();
    updateActions({ task: { id: "", status: "NOT_CREATED" }, pptDslPath: "" });
    $("ppt-generate-run").addEventListener("click", runGenerate);
    $("ppt-generate-review-link").addEventListener("click", openReview);
  }

  window.pptGenerateDataLoader = { runGenerate, renderPayload, renderError, updateActions };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
