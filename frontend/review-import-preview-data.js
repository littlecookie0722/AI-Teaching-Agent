(function () {
  "use strict";

  var currentScript = document.currentScript || document.querySelector("script[src$='review-import-preview-data.js']");
  var importKind = currentScript ? currentScript.getAttribute("data-import-kind") || "" : "";
  var endpoints = {
    lab: "/api/labs/import-preview",
    exam: "/api/exams/import-preview",
    grading: "/api/grading/import-preview"
  };
  var mockImportEndpoints = {
    lab: "/api/labs/mock-import",
    exam: "/api/exams/mock-import",
    grading: "/api/grading/mock-import"
  };
  var outputs = {
    lab: "examples/output/lab-template-import-preview.json",
    exam: "examples/output/exam-question-import-preview.json",
    grading: "examples/output/grading-rule-import-preview.json"
  };
  var mockImportOutputs = {
    lab: "examples/output/lab-template-mock-import.json",
    exam: "examples/output/exam-question-mock-import.json",
    grading: "examples/output/grading-rule-mock-import.json"
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

  function readValue(id) {
    var node = byId(id);
    return node ? String(node.value || "").trim() : "";
  }

  function resolveTaskId() {
    if (window.reviewDetailDataLoader && window.reviewDetailDataLoader.resolveTaskId) {
      return window.reviewDetailDataLoader.resolveTaskId();
    }
    var params = new URLSearchParams(window.location.search);
    return params.get("taskId") || params.get("id") || "";
  }

  function setImportStatus(status, detail) {
    setText("agent-import-preview-status", status);
    setText("agent-import-preview-detail", detail);
  }

  function setMockImportStatus(status, detail) {
    setText("agent-mock-import-status", status);
    setText("agent-mock-import-detail", detail);
  }

  function previewSummary(payload) {
    var data = payload.data || {};
    var preview = data.labTemplateImportPreview || data.examQuestionImportPreview || data.gradingRuleImportPreview || {};
    var entity = preview.agentEntity || "agent_entity";
    var artifact = data.artifact || {};
    return "agentEntity=" + entity
      + " · artifactId=" + (artifact.id || "none")
      + " · databaseWritten=false"
      + " · realAgentImport=false"
      + " · realPublishAllowed=false";
  }

  function setButtonDisabled(disabled) {
    var button = byId("agent-import-preview-button");
    if (button) {
      button.disabled = disabled;
    }
  }

  function setMockImportButtonDisabled(disabled) {
    var button = byId("agent-mock-import-button");
    if (button) {
      button.disabled = disabled;
    }
  }

  function entityKindForRoute(record) {
    var entityType = record && record.entityType ? record.entityType : "";
    if (entityType === "lab_template") {
      return "lab";
    }
    if (entityType === "exam_question") {
      return "exam";
    }
    if (entityType === "grading_rule") {
      return "grading";
    }
    return importKind || "lab";
  }

  function updateAgentEntityLink(record) {
    var link = byId("agent-mock-import-link");
    if (!link || !record || !record.id) {
      return;
    }
    var taskId = resolveTaskId();
    var params = new URLSearchParams();
    params.set("entityId", record.id);
    if (taskId) {
      params.set("sourceTaskId", taskId);
    }
    params.set("entityKind", entityKindForRoute(record));
    link.href = "agent-entities.html?" + params.toString();
    link.textContent = "打开平台实体页：" + record.id;
  }

  function createImportPreview() {
    var endpoint = endpoints[importKind];
    var taskId = resolveTaskId();
    var reviewer = readValue("review-action-reviewer") || "teacher_1";

    if (!endpoint) {
      setImportStatus("IMPORT_PREVIEW_UNSUPPORTED", "PPT does not create platform entity import preview");
      return Promise.resolve(null);
    }
    if (!taskId) {
      setImportStatus("IMPORT_PREVIEW_VALIDATION_ERROR", "taskId is required");
      return Promise.resolve(null);
    }
    if (!reviewer) {
      setImportStatus("IMPORT_PREVIEW_VALIDATION_ERROR", "reviewer is required");
      return Promise.resolve(null);
    }

    setButtonDisabled(true);
    setImportStatus(
      "IMPORT_PREVIEW_PENDING",
      "POST " + endpoint + " · taskId=" + taskId + " · requiresApprovedTask=true"
    );

    return fetch(endpoint, {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      credentials: "same-origin",
      body: JSON.stringify({
        taskId: taskId,
        reviewer: reviewer,
        output: outputs[importKind]
      })
    }).then(function (response) {
      return response.json().then(function (payload) {
        if (!response.ok || !payload || payload.success !== true) {
          var code = payload && payload.code ? payload.code : "HTTP_" + response.status;
          throw new Error(code);
        }
        setImportStatus("IMPORT_PREVIEW_CREATED", previewSummary(payload));
        setMockImportStatus(
          "MOCK_IMPORT_READY",
          "POST " + mockImportEndpoints[importKind] + " · requiresImportPreview=true · mockStoreWritten=true · databaseWritten=false"
        );
        setMockImportButtonDisabled(false);
        if (window.reviewDetailDataLoader && window.reviewDetailDataLoader.load) {
          window.reviewDetailDataLoader.load();
        }
        return payload;
      });
    }).catch(function (error) {
      setImportStatus(
        "IMPORT_PREVIEW_FAILED",
        error.message + " · requiresApprovedTask=true · databaseWritten=false · realPublishAllowed=false"
      );
      return null;
    }).finally(function () {
      setButtonDisabled(false);
      });
  }

  function createMockImport() {
    var endpoint = mockImportEndpoints[importKind];
    var taskId = resolveTaskId();
    var reviewer = readValue("review-action-reviewer") || "teacher_1";

    if (!endpoint) {
      setMockImportStatus("MOCK_IMPORT_UNSUPPORTED", "PPT does not create platform entity mock import");
      return Promise.resolve(null);
    }
    if (!taskId) {
      setMockImportStatus("MOCK_IMPORT_VALIDATION_ERROR", "taskId is required");
      return Promise.resolve(null);
    }
    if (!reviewer) {
      setMockImportStatus("MOCK_IMPORT_VALIDATION_ERROR", "reviewer is required");
      return Promise.resolve(null);
    }

    setMockImportButtonDisabled(true);
    setMockImportStatus(
      "MOCK_IMPORT_PENDING",
      "POST " + endpoint + " · taskId=" + taskId + " · requiresImportPreview=true"
    );

    return fetch(endpoint, {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      credentials: "same-origin",
      body: JSON.stringify({
        taskId: taskId,
        reviewer: reviewer,
        output: mockImportOutputs[importKind]
      })
    }).then(function (response) {
      return response.json().then(function (payload) {
        if (!response.ok || !payload || payload.success !== true) {
          var code = payload && payload.code ? payload.code : "HTTP_" + response.status;
          throw new Error(code);
        }
        var record = payload.data ? payload.data.agentEntityRecord : null;
        updateAgentEntityLink(record);
        setMockImportStatus(
          "MOCK_IMPORT_CREATED",
          "agentEntityId=" + (record && record.id ? record.id : "none")
            + " · mockStoreWritten=true"
            + " · databaseWritten=false"
            + " · realAgentImport=false"
            + " · realPublish=false"
        );
        if (window.reviewDetailDataLoader && window.reviewDetailDataLoader.load) {
          window.reviewDetailDataLoader.load();
        }
        return payload;
      });
    }).catch(function (error) {
      setMockImportStatus(
        "MOCK_IMPORT_FAILED",
        error.message + " · requiresImportPreview=true · databaseWritten=false · realPublish=false"
      );
      return null;
    }).finally(function () {
      setMockImportButtonDisabled(false);
    });
  }

  function bind() {
    var endpoint = endpoints[importKind];
    setImportStatus(
      endpoint ? "IMPORT_PREVIEW_READY" : "IMPORT_PREVIEW_UNSUPPORTED",
      endpoint
        ? "POST " + endpoint + " · requiresApprovedTask=true · databaseWritten=false"
        : "PPT review keeps platform import preview unavailable"
    );
    setMockImportStatus(
      mockImportEndpoints[importKind] ? "MOCK_IMPORT_WAITING_PREVIEW" : "MOCK_IMPORT_UNSUPPORTED",
      mockImportEndpoints[importKind]
        ? "POST " + mockImportEndpoints[importKind] + " · requiresImportPreview=true · mockStoreWritten=true"
        : "PPT review keeps platform entity mock import unavailable"
    );
    setMockImportButtonDisabled(true);
    var button = byId("agent-import-preview-button");
    if (button) {
      button.addEventListener("click", createImportPreview);
    }
    var mockButton = byId("agent-mock-import-button");
    if (mockButton) {
      mockButton.addEventListener("click", createMockImport);
    }
  }

  window.reviewImportPreviewDataLoader = {
    resolveTaskId: resolveTaskId,
    createImportPreview: createImportPreview,
    createMockImport: createMockImport
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
}());
