(function () {
  "use strict";

  var state = {
    actionPathTemplate: "/api/ai-tasks/{id}/{action}",
    autoPublishAllowed: false,
    realPublishAllowed: false,
    coreDbPath: ""
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

  function resolveTaskId() {
    if (window.reviewDetailDataLoader && window.reviewDetailDataLoader.resolveTaskId) {
      return window.reviewDetailDataLoader.resolveTaskId();
    }
    var params = new URLSearchParams(window.location.search);
    return params.get("taskId") || params.get("id") || "";
  }

  function actionPath(taskId, action) {
    return state.actionPathTemplate
      .replace("{id}", encodeURIComponent(taskId))
      .replace("{action}", encodeURIComponent(action));
  }

  function readValue(id) {
    var node = byId(id);
    return node ? String(node.value || "").trim() : "";
  }

  function resolveCoreDbPath() {
    if (state.coreDbPath) {
      return state.coreDbPath;
    }
    var params = new URLSearchParams(window.location.search);
    return params.get("coreDbPath") || "";
  }

  function setActionStatus(status, detail) {
    setText("review-action-status", status);
    setText("review-action-detail", detail);
  }

  function setButtonsDisabled(disabled) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-review-action]"), function (button) {
      button.disabled = disabled;
    });
  }

  function applyTaskStatus(payload, action) {
    var data = payload.data || {};
    var task = data.task || {};
    var status = task.status || (action === "approve" ? "APPROVED" : "REJECTED");
    setText("review-detail-status", status);
    setText("review-detail-dsl-status", status);
    setActionStatus(
      action === "approve" ? "ACTION_APPROVED_RECORDED" : "ACTION_REJECTED_RECORDED",
      "taskStatus=" + status
        + " · auditEventWritten=true"
        + " · autoPublishAllowed=" + String(state.autoPublishAllowed)
        + " · realPublishAllowed=" + String(state.realPublishAllowed)
    );
  }

  function postReviewAction(action) {
    var taskId = resolveTaskId();
    var reviewer = readValue("review-action-reviewer");
    var reason = readValue("review-action-reason");

    if (!taskId) {
      setActionStatus("ACTION_VALIDATION_ERROR", "taskId is required");
      return Promise.resolve(null);
    }
    if (!reviewer) {
      setActionStatus("ACTION_VALIDATION_ERROR", "reviewer is required");
      return Promise.resolve(null);
    }
    if (action === "reject" && !reason) {
      setActionStatus("ACTION_VALIDATION_ERROR", "rejectRequiresReason=true");
      return Promise.resolve(null);
    }

    setButtonsDisabled(true);
    setActionStatus(
      action === "approve" ? "ACTION_APPROVE_PENDING" : "ACTION_REJECT_PENDING",
      "POST /api/ai-tasks/{id}/" + action + " · taskId=" + taskId
    );

    return fetch(actionPath(taskId, action), {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      credentials: "same-origin",
      body: JSON.stringify({
        reviewer: reviewer,
        reason: reason || undefined,
        coreDbPath: resolveCoreDbPath() || undefined
      })
    }).then(function (response) {
      return response.json().then(function (payload) {
        if (!response.ok || !payload || payload.success !== true) {
          var code = payload && payload.code ? payload.code : "HTTP_" + response.status;
          throw new Error(code);
        }
        applyTaskStatus(payload, action);
        if (window.reviewDetailDataLoader && window.reviewDetailDataLoader.load) {
          window.reviewDetailDataLoader.load();
        }
        return payload;
      });
    }).catch(function (error) {
      setActionStatus(
        "ACTION_FAILED",
        error.message + " · autoPublishAllowed=false · realPublishAllowed=false"
      );
      return null;
    }).finally(function () {
      setButtonsDisabled(false);
    });
  }

  function bind() {
    state.coreDbPath = resolveCoreDbPath();
    setActionStatus(
      "ACTION_READY",
      "POST /api/ai-tasks/{id}/approve · POST /api/ai-tasks/{id}/reject · rejectRequiresReason=true"
    );
    Array.prototype.forEach.call(document.querySelectorAll("[data-review-action]"), function (button) {
      button.addEventListener("click", function () {
        postReviewAction(button.getAttribute("data-review-action"));
      });
    });
  }

  window.reviewActionDataLoader = {
    resolveTaskId: resolveTaskId,
    actionPath: actionPath,
    postReviewAction: postReviewAction
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
}());
