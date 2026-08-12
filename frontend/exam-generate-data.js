(function () {
  "use strict";

  const state = {
    generatePath: "/api/exams/generate-from-lab",
    defaultLabId: "lab_demo",
    lastTaskId: "",
    coreDbPath: "",
    gradingDbPath: "",
    agentReport: "",
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

  function setApiState(message, tone) {
    const node = $("exam-generate-api-state");
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
    const providerMode = $("exam-generate-provider-mode");
    const model = $("exam-generate-model");
    const baseUrl = $("exam-generate-base-url");
    const explicitRealCall = $("exam-generate-explicit-real-call");
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
      workflowStep: audit.detail && audit.detail.workflowStep ? audit.detail.workflowStep : "-",
    };
  }

  function candidateSafeQuestion(question) {
    return {
      id: question.id || "-",
      title: question.title || "-",
      score: question.score == null ? 0 : question.score,
      answerVisibleToCandidate: false,
      gradingRefVisibleToCandidate: false,
    };
  }

  function updateCloseLoopAction(view) {
    const task = view && view.task ? view.task : {};
    const taskId = task.id && task.id !== "-" ? task.id : "";
    const examDslPath = view && view.exam && view.exam.dslPath ? view.exam.dslPath : "";
    const gradingDslPath = view && view.grading && view.grading.dslPath ? view.grading.dslPath : "";
    setText(
      "exam-generate-next-summary",
      "source=POST /api/exams/generate-from-lab"
        + " · next=review_center_candidate_safe_preview_and_local_import_preview"
        + " · taskId=" + (taskId || "not_created")
    );
    setText("exam-generate-next-status", task.status || "WAITING_REVIEW");
    setText("exam-generate-next-task", "task=" + (taskId || "not_created"));
    setText("exam-generate-next-exam-artifact", "examDslPath=" + (examDslPath || "none"));
    setText("exam-generate-next-grading-artifact", "gradingDslPath=" + (gradingDslPath || "none"));
    setText(
      "exam-generate-next-candidate-safety",
      "answersHidden=true · gradingRefHidden=true"
    );
    setText(
      "exam-generate-next-boundary",
      "answerVisibleToCandidate=false · gradingRefVisibleToCandidate=false"
        + " · sandboxExecuted=false · realPublishAllowed=false"
        + " · coreDbPath=" + (state.coreDbPath || "none")
    );
    setHref(
      "exam-generate-review-center-link",
      withQuery("review-center.html", withLocalContext({ taskId })),
      "打开审核中心"
    );
    setHref(
      "exam-generate-review-page-link",
      withQuery("exam-review.html", withLocalContext({ taskId })),
      "打开 Exam 审核页"
    );
    setHref(
      "exam-generate-grading-review-link",
      withQuery("grading-review.html", withLocalContext({ taskId })),
      "打开 Grading 审核页"
    );
    setHref(
      "exam-generate-exam-import-preview-link",
      withQuery("agent-entities.html", withLocalContext({ sourceTaskId: taskId, entityKind: "exam" })),
      "Exam 导入预览"
    );
    setHref(
      "exam-generate-grading-import-preview-link",
      withQuery("agent-entities.html", withLocalContext({ sourceTaskId: taskId, entityKind: "grading" })),
      "Grading 导入预览"
    );
  }

  function buildExamView(payload) {
    const data = payload && payload.data ? payload.data : {};
    const task = data.task || {};
    const examDsl = data.examDsl || {};
    const gradingDsl = data.gradingDsl || {};
    const examSpec = examDsl.spec || {};
    const gradingSpec = gradingDsl.spec || {};
    const examMetadata = examDsl.metadata || {};
    const gradingMetadata = gradingDsl.metadata || {};
    const providers = data.providerGenerations || {};
    const questions = safeArray(examSpec.questions);
    const checks = safeArray(gradingSpec.checks);
    const artifacts = safeArray(data.artifacts);

    state.lastTaskId = task.id || "";

    setText("exam-generate-source-lab", examMetadata.sourceLabId || task.inputRef || state.defaultLabId);
    setText("exam-generate-question-type", examSpec.questionType || "-");
    setText("exam-generate-total-score", examSpec.totalScore == null ? gradingSpec.totalScore : examSpec.totalScore);
    setText("exam-generate-status", task.status || data.status || "-");

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
        finalResultPath: task.finalResultPath || data.examDslPath || "-",
      },
      exam: {
        kind: examDsl.kind || "-",
        dslPath: data.examDslPath || task.finalResultPath || "",
        id: examMetadata.id || "-",
        title: examMetadata.title || "-",
        sourceLabId: examMetadata.sourceLabId || task.inputRef || "-",
        questionType: examSpec.questionType || "-",
        totalScore: examSpec.totalScore == null ? 0 : examSpec.totalScore,
        questionTotal: questions.length,
        candidateSafeQuestions: questions.map(candidateSafeQuestion),
      },
      grading: {
        kind: gradingDsl.kind || "-",
        dslPath: data.gradingDslPath || "",
        id: gradingMetadata.id || "-",
        title: gradingMetadata.title || "-",
        totalScore: gradingSpec.totalScore == null ? 0 : gradingSpec.totalScore,
        checkTotal: checks.length,
        checkTypes: checks.map(function (check) {
          return check.type || "-";
        }),
      },
      provider: {
        exam: providerContext(providers.exam || {}),
        grading: providerContext(providers.grading || {}),
      },
      review: {
        reviewRequired: data.reviewRequired === true,
        generatedStatus: task.status || data.status || "-",
        answerVisibleToCandidate: false,
        gradingRefVisibleToCandidate: false,
        autoPublishAllowed: false,
        realPublish: false,
        sandboxExecuted: false,
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
    const view = buildExamView(payload);
    updateCloseLoopAction(view);
    const examPre = $("exam-generate-exam-json");
    const gradingPre = $("exam-generate-grading-json");
    if (examPre) {
      examPre.textContent = JSON.stringify(
        {
          task: view.task,
          exam: view.exam,
          review: view.review,
          provider: view.provider.exam,
        },
        null,
        2
      );
    }
    if (gradingPre) {
      gradingPre.textContent = JSON.stringify(
        {
          grading: view.grading,
          review: view.review,
          provider: view.provider.grading,
          artifacts: view.artifacts,
        },
        null,
        2
      );
    }
    const status =
      view.task.status === "WAITING_REVIEW" ? "API_ACTION_COMPLETED · WAITING_REVIEW" : "API_ACTION_COMPLETED";
    setApiState(status, "");
  }

  function renderError(errorPayload) {
    const view = {
      api: state.generatePath,
      success: false,
      code: errorPayload && errorPayload.code ? errorPayload.code : "EXAM_GENERATE_REQUEST_FAILED",
      message: errorPayload && errorPayload.message ? errorPayload.message : "本地 Exam 生成请求失败",
      traceId: errorPayload && errorPayload.traceId ? errorPayload.traceId : "-",
      errors: safeArray(errorPayload && errorPayload.errors),
      review: {
        answerVisibleToCandidate: false,
        gradingRefVisibleToCandidate: false,
        autoPublishAllowed: false,
        realPublish: false,
      },
    };
    const examPre = $("exam-generate-exam-json");
    const gradingPre = $("exam-generate-grading-json");
    if (examPre) {
      examPre.textContent = JSON.stringify(view, null, 2);
    }
    if (gradingPre) {
      gradingPre.textContent = JSON.stringify({ gradingGenerated: false, reason: view.code }, null, 2);
    }
    updateCloseLoopAction({
      task: {
        id: "",
        status: "NOT_CREATED",
      },
      exam: {
        dslPath: "",
      },
      grading: {
        dslPath: "",
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
    const input = $("exam-generate-lab-id");
    const labDslPathInput = $("exam-generate-lab-dsl-path");
    const button = $("exam-generate-run");
    const labId = input ? input.value.trim() : state.defaultLabId;
    const labDslPath = labDslPathInput && labDslPathInput.value ? labDslPathInput.value.trim() : "";
    if (!labId) {
      renderError({ code: "VALIDATION_ERROR", message: "Lab ID 不能为空", errors: [{ field: "labId", reason: "required" }] });
      return;
    }

    if (button) {
      button.disabled = true;
    }
    setApiState("API_ACTION_PENDING · POST /api/exams/generate-from-lab", "pending");
    try {
      const payload = await postJson(
        state.generatePath,
        requestBodyWithLocalContext(Object.assign({ labId, labDslPath }, providerRequestOptions()))
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
      ? withQuery("exam-review.html", withLocalContext({ taskId: state.lastTaskId }))
      : withQuery("review-center.html", withLocalContext({}));
    window.location.href = target;
  }

  function init() {
    configureLocalContextFromQuery();
    updateCloseLoopAction({
      task: {
        id: "",
        status: "NOT_CREATED",
      },
      exam: {
        dslPath: "",
      },
      grading: {
        dslPath: "",
      },
    });
    const runButton = $("exam-generate-run");
    const reviewButton = $("exam-generate-review-link");
    if (runButton) {
      runButton.addEventListener("click", runGenerate);
    }
    if (reviewButton) {
      reviewButton.addEventListener("click", openReviewDetail);
    }
  }

  window.examGenerateDataLoader = {
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
