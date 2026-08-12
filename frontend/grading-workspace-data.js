(function () {
  "use strict";

  var state = { jobId: "", taskId: "", recordId: "", reportPath: "", coreDbPath: "", gradingDbPath: "", agentReport: "" };

  function byId(id) { return document.getElementById(id); }
  function value(id) { var node = byId(id); return node && node.value ? node.value.trim() : ""; }
  function checked(id) { var node = byId(id); return Boolean(node && node.checked); }
  function setText(id, text) { var node = byId(id); if (node) { node.textContent = text == null || text === "" ? "-" : String(text); } }
  function setState(text, tone) { var node = byId("grading-workspace-api-state"); if (!node) { return; } node.textContent = text; node.classList.remove("pending", "error"); if (tone) { node.classList.add(tone); } }
  function query(name) { try { return new URLSearchParams(window.location.search || "").get(name) || ""; } catch (error) { return ""; } }
  function withQuery(path, params) { var query = new URLSearchParams(); Object.keys(params || {}).forEach(function (key) { if (params[key] !== undefined && params[key] !== null && String(params[key]) !== "") { query.set(key, String(params[key])); } }); return query.toString() ? path + "?" + query.toString() : path; }
  function context(params) { var result = Object.assign({}, params || {}); if (state.coreDbPath) { result.coreDbPath = state.coreDbPath; } if (state.gradingDbPath) { result.gradingDbPath = state.gradingDbPath; } if (state.agentReport) { result.agentReport = state.agentReport; } return result; }
  function setLink(id, href, label, enabled) { var node = byId(id); if (!node) { return; } node.href = enabled ? href : "#"; node.textContent = label; node.setAttribute("aria-disabled", enabled ? "false" : "true"); }

  function configureContext() {
    state.taskId = query("taskId") || query("id");
    state.coreDbPath = query("coreDbPath");
    state.gradingDbPath = query("gradingDbPath") || query("dbPath");
    state.agentReport = query("agentReport");
    if (state.taskId) { byId("grading-workspace-task-id").value = state.taskId; }
    if (state.gradingDbPath) { byId("grading-workspace-db-path").value = state.gradingDbPath; }
    refreshLinks();
  }

  function dbPath() { return value("grading-workspace-db-path") || state.gradingDbPath; }
  function requestBody(body) { var result = Object.assign({}, body || {}); if (dbPath()) { result.dbPath = dbPath(); } return result; }
  function runPath() { var path = "/api/grading/jobs/" + encodeURIComponent(state.jobId) + "/run"; return dbPath() ? path + "?" + new URLSearchParams({dbPath:dbPath()}).toString() : path; }
  function recordsPath() { var params = {}; if (state.taskId) { params.taskId = state.taskId; } if (dbPath()) { params.dbPath = dbPath(); } return withQuery("/api/grading/records", params); }

  function refreshLinks() {
    setLink("grading-workspace-report-link", withQuery("grading-report.html", context({taskId:state.taskId, file:state.reportPath})), state.reportPath ? "打开评分报告" : "等待评分报告", Boolean(state.reportPath));
    setLink("grading-workspace-review-link", withQuery("review-center.html", context({taskId:state.taskId})), state.taskId ? "打开审核中心" : "未关联审核任务", Boolean(state.taskId));
    setLink("grading-workspace-task-link", withQuery("ai-tasks.html", context({taskId:state.taskId})), state.taskId ? "打开 AI Task" : "未关联 AI Task", Boolean(state.taskId));
  }

  function render(payload) { var output = byId("grading-workspace-result-json"); if (output) { output.textContent = JSON.stringify(payload, null, 2); } }
  function error(payload, fallback) { render({success:false, code:payload && payload.code || fallback, message:payload && payload.message || "本地评分请求失败", errors:payload && payload.errors || []}); setState(payload && payload.code || fallback, "error"); }
  async function post(path, body) { var response = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json", "Accept":"application/json"}, body:JSON.stringify(body || {})}); var payload = await response.json(); if (!response.ok || payload.success === false) { throw payload; } return payload; }
  async function get(path) { var response = await fetch(path, {headers:{"Accept":"application/json"}}); var payload = await response.json(); if (!response.ok || payload.success === false) { throw payload; } return payload; }

  function renderJob(job) {
    job = job || {};
    state.jobId = job.id || state.jobId;
    state.taskId = job.taskId || value("grading-workspace-task-id") || state.taskId;
    setText("grading-workspace-job", "job=" + (state.jobId || "not_created"));
    setText("grading-workspace-job-status", job.status || "NOT_CREATED");
    if (job.reportPath) { state.reportPath = job.reportPath; }
    setText("grading-workspace-report", "report=" + (state.reportPath || "none"));
    byId("grading-workspace-run").disabled = !state.jobId || job.status !== "QUEUED";
    refreshLinks();
  }

  function renderRecord(record) {
    record = record || {};
    state.recordId = record.id || state.recordId;
    if (state.recordId) { byId("grading-workspace-record-id").value = state.recordId; }
    setText("grading-workspace-record", "record=" + (state.recordId || "not_created") + " · " + (record.status || "-"));
    setText("grading-workspace-score", record.earnedScore == null ? "-" : String(record.earnedScore) + " / " + String(record.totalScore || 0));
    setText("grading-workspace-review-status", "recordReview=" + (record.status || "WAITING_RECORD") + " · decision=" + (record.reviewDecision || "none"));
    byId("grading-workspace-review-record").disabled = !state.recordId;
    byId("grading-workspace-reload").disabled = !state.taskId;
  }

  async function createJob() {
    var body = requestBody({grading:value("grading-workspace-grading"), submission:value("grading-workspace-submission"), output:value("grading-workspace-output"), submissionId:value("grading-workspace-submission-id"), taskId:value("grading-workspace-task-id"), candidateId:value("grading-workspace-candidate-id"), reviewer:value("grading-workspace-reviewer"), includeControlledCommand:checked("grading-workspace-controlled"), failOnControlledUnavailable:checked("grading-workspace-fail-unavailable")});
    byId("grading-workspace-create").disabled = true; setState("API_ACTION_PENDING · POST /api/grading/jobs", "pending");
    try { var payload = await post("/api/grading/jobs", body); renderJob(payload.data && payload.data.gradingJob); setText("grading-workspace-next", "run_controlled_grading_job"); render(payload); setState("API_ACTION_COMPLETED · QUEUED", ""); } catch (payload) { error(payload, "GRADING_JOB_CREATE_FAILED"); } finally { byId("grading-workspace-create").disabled = false; }
  }

  async function runJob() {
    if (!state.jobId) { return; }
    byId("grading-workspace-run").disabled = true; setState("API_ACTION_PENDING · POST /api/grading/jobs/{id}/run", "pending");
    try { var payload = await post(runPath(), requestBody({})); var data = payload.data || {}; renderJob(data.gradingJob); renderRecord(data.gradingRecord); state.reportPath = data.gradingJob && data.gradingJob.reportPath || state.reportPath; setText("grading-workspace-report", "report=" + (state.reportPath || "none")); setText("grading-workspace-next", "review_grading_record_manually"); refreshLinks(); render(payload); setState("API_ACTION_COMPLETED · WAITING_REVIEW", ""); } catch (payload) { error(payload, "GRADING_JOB_RUN_FAILED"); } finally { byId("grading-workspace-run").disabled = !(state.jobId && byId("grading-workspace-job-status").textContent === "QUEUED"); }
  }

  async function loadRecords() {
    if (!state.taskId) { return; }
    setState("API_ACTION_PENDING · GET /api/grading/records", "pending");
    try { var payload = await get(recordsPath()); var items = payload.data && payload.data.items || []; if (items.length) { renderRecord(items[0]); setText("grading-workspace-next", "record_manual_review"); } render(payload); setState("API_READONLY_LOADED", ""); } catch (payload) { error(payload, "GRADING_RECORD_LOAD_FAILED"); }
  }

  async function reviewRecord() {
    var recordId = value("grading-workspace-record-id") || state.recordId;
    if (!recordId) { return; }
    var body = requestBody({reviewer:value("grading-workspace-reviewer"), decision:value("grading-workspace-decision"), reason:value("grading-workspace-reason")});
    byId("grading-workspace-review-record").disabled = true; setState("API_ACTION_PENDING · POST /api/grading/records/{id}/review", "pending");
    try { var path = "/api/grading/records/" + encodeURIComponent(recordId) + "/review"; var payload = await post(path, body); renderRecord(payload.data && payload.data.gradingRecord); setText("grading-workspace-next", "open_review_center_for_human_task_decision"); render(payload); setState("API_ACTION_COMPLETED · RECORD_REVIEWED", ""); } catch (payload) { error(payload, "GRADING_RECORD_REVIEW_FAILED"); } finally { byId("grading-workspace-review-record").disabled = !state.recordId; }
  }

  function init() { configureContext(); byId("grading-workspace-create").addEventListener("click", createJob); byId("grading-workspace-run").addEventListener("click", runJob); byId("grading-workspace-reload").addEventListener("click", loadRecords); byId("grading-workspace-review-record").addEventListener("click", reviewRecord); }
  window.gradingWorkspaceDataLoader = {createJob:createJob, runJob:runJob, loadRecords:loadRecords, reviewRecord:reviewRecord};
  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); } else { init(); }
})();
