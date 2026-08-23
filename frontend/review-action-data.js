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
    Array.prototype.forEach.call(document.querySelectorAll("[data-review-action], [data-package-review-action]"), function (button) {
      button.disabled = disabled || (
        button.hasAttribute("data-package-review-action")
        && button.getAttribute("data-package-action-enabled") !== "true"
      );
    });
  }

  function setPackageActionStatus(kind, status, detail) {
    setText("teaching-package-action-status", status + (detail ? " · " + detail : ""));
    var rowStatus = document.querySelector('[data-package-row-status="' + kind + '"]');
    if (rowStatus) {
      rowStatus.textContent = status + (detail ? " · " + detail : "");
    }
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

  function postPackageReviewAction(button) {
    var taskId = String(button.getAttribute("data-task-id") || "");
    var kind = String(button.getAttribute("data-package-kind") || "artifact");
    var action = String(button.getAttribute("data-package-review-action") || "");
    var reviewer = readValue("teaching-package-reviewer");
    var reasonInput = document.querySelector('[data-package-reject-reason="' + kind + '"]');
    var reason = reasonInput ? String(reasonInput.value || "").trim() : "";

    if (!taskId || ["approve", "reject"].indexOf(action) === -1) {
      setPackageActionStatus(kind, "ACTION_VALIDATION_ERROR", "taskId and action are required");
      return Promise.resolve(null);
    }
    if (!reviewer) {
      setPackageActionStatus(kind, "ACTION_VALIDATION_ERROR", "reviewer is required");
      return Promise.resolve(null);
    }
    if (action === "reject" && !reason) {
      setPackageActionStatus(kind, "ACTION_VALIDATION_ERROR", "rejectRequiresReason=true");
      if (reasonInput) {
        reasonInput.focus();
      }
      return Promise.resolve(null);
    }

    setButtonsDisabled(true);
    setPackageActionStatus(
      kind,
      action === "approve" ? "ACTION_APPROVE_PENDING" : "ACTION_REJECT_PENDING",
      "taskId=" + taskId
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
        if (resolveTaskId() === taskId) {
          applyTaskStatus(payload, action);
        }
        setPackageActionStatus(
          kind,
          action === "approve" ? "ACTION_APPROVED_RECORDED" : "ACTION_REJECTED_RECORDED",
          "taskId=" + taskId + " · auditEventWritten=true"
        );
        Array.prototype.forEach.call(
          document.querySelectorAll('[data-package-kind="' + kind + '"][data-package-review-action]'),
          function (actionButton) {
            actionButton.setAttribute("data-package-action-enabled", "false");
            actionButton.disabled = true;
          }
        );
        if (window.reviewCenterDataLoader && window.reviewCenterDataLoader.load) {
          window.reviewCenterDataLoader.load();
        }
        return payload;
      });
    }).catch(function (error) {
      setPackageActionStatus(
        kind,
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
    document.addEventListener("click", function (event) {
      var target = event.target;
      var button = target && target.closest ? target.closest("[data-package-review-action]") : null;
      if (button) {
        postPackageReviewAction(button);
      }
    });
  }

  window.reviewActionDataLoader = {
    resolveTaskId: resolveTaskId,
    actionPath: actionPath,
    postReviewAction: postReviewAction,
    postPackageReviewAction: postPackageReviewAction
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
}());
