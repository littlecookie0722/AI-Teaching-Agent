import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import backend.mock_api as mock_api
import backend.mock_http_server as mock_http_server
from backend.mock_api import handle_request
from cli.artifact import ArtifactKind, ArtifactStatus, create_artifact_record
from cli.ai_task import AiTask, TaskStatus, create_waiting_review_task
from cli.environment import EnvironmentInstance, EnvironmentStatus, EnvironmentType
from cli.grading_record import GradingRecord, GradingRecordStatus
from cli.mcp_audit import McpToolCallStatus, create_mcp_tool_call_record
from cli.agent_entity import AgentEntityType, create_agent_entity_record
from cli.store import JsonTaskStore


SUPPORTED_GRADING_CHECK_TYPES = ["file_exists", "stdout_contains", "pytest", "notebook_cell", "json_field", "log_keyword"]


def _create_reviewed_revision_task(
    tmp_path,
    *,
    store_path,
    source_task_id: str,
    reviewer: str = "teacher_1",
) -> str:
    revision = handle_request(
        "POST",
        f"/api/review-tasks/{source_task_id}/revision-request",
        store_path=store_path,
        body={"reviewer": reviewer, "comment": "按内容质量摘要生成修订草稿。", "priority": "HIGH"},
    )
    regeneration = handle_request(
        "POST",
        f"/api/review-tasks/{source_task_id}/regenerate-mock",
        store_path=store_path,
        body={
            "reviewer": reviewer,
            "revisionRequestId": revision["data"]["revisionRequest"]["id"],
            "output": str(tmp_path / f"{source_task_id}-revision.json"),
        },
    )
    revision_task_id = regeneration["data"]["mockRegeneration"]["newTask"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{revision_task_id}/approve",
        store_path=store_path,
        body={"reviewer": reviewer},
    )
    assert_api_envelope(revision)
    assert_api_envelope(regeneration)
    assert_api_envelope(approved)
    assert approved["data"]["task"]["status"] == "APPROVED"
    return revision_task_id


def _attach_ready_grading_evidence(store_path, tmp_path, *, task_id: str) -> None:
    report_path = tmp_path / f"{task_id}-ready-grading-evidence.json"
    report = {
        "id": f"ready_evidence_{task_id}",
        "mode": "GRADING_EVIDENCE_MERGE_REPORT",
        "summary": {
            "checkTotal": 1,
            "executedTotal": 1,
            "passedTotal": 1,
            "earnedScore": 100,
            "totalScore": 100,
            "coverageRatio": 1.0,
        },
        "evidenceCoverage": {
            "controlledDocker": {"checkTotal": 1},
            "readonlyStatic": {"checkTotal": 0},
        },
        "checks": [
            {
                "id": "check_ready",
                "checkId": "check_ready",
                "type": "pytest",
                "score": 100,
                "earnedScore": 100,
                "passed": True,
                "executed": True,
                "evidenceSourceKind": "controlledDocker",
                "manualReviewRequired": False,
            }
        ],
        "scorePreview": {
            "status": "READY_FOR_HUMAN_SCORE_REVIEW",
            "earnedScore": 100,
            "totalScore": 100,
            "coveredScore": 100,
            "missingScore": 0,
            "coverageRatio": 1.0,
            "passRate": 1.0,
            "readyForDecisionNote": True,
            "missingEvidenceTotal": 0,
            "missingCheckIds": [],
        },
        "safety": {
            "mergeExecutedOnlyExistingReports": True,
            "hostExecutionAllowed": False,
            "networkAllowed": False,
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    store = JsonTaskStore(store_path)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.GRADING_REPORT,
            path=str(report_path),
            title="Ready Grading Evidence Merge",
            status=ArtifactStatus.COMPLETED,
            trace_id="trace_ready_grading_evidence",
            task_id=task_id,
            source_ref=str(report_path),
            metadata={
                "reportType": "GRADING_EVIDENCE_MERGE",
                "summary": report["summary"],
                "evidenceCoverage": report["evidenceCoverage"],
                "scorePreview": report["scorePreview"],
                "safety": report["safety"],
            },
        )
    )


class RecordingPlatformImportHandler(BaseHTTPRequestHandler):
    requests = []
    quiet = True

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length)
        body = json.loads(raw.decode("utf-8"))
        self.__class__.requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "contentType": self.headers.get("Content-Type"),
                "body": body,
            }
        )
        response = {
            "draftImportId": "draft_import_api_test",
            "status": "PENDING_MANUAL_PLATFORM_REVIEW",
            "receivedEntityType": body.get("entityType"),
        }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        self.__class__.requests.append(
            {
                "method": "GET",
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "contentType": self.headers.get("Content-Type"),
            }
        )
        response = {
            "draftImportId": "draft_import_api_test",
            "status": "ACCEPTED_FOR_DRAFT",
            "message": "draft import accepted for manual publish review",
        }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        if self.quiet:
            return
        super().log_message(format, *args)


def start_recording_platform_server():
    RecordingPlatformImportHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), RecordingPlatformImportHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}"


def stop_recording_platform_server(server, thread):
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


def assert_api_envelope(payload):
    assert set(payload) >= {"success", "code", "message", "traceId"}
    assert payload["traceId"].startswith("trace_")
    if payload["success"]:
        assert "data" in payload
    else:
        assert "errors" in payload


def test_health_returns_mock_status():
    payload = handle_request("GET", "/api/health")

    assert_api_envelope(payload)
    assert payload["data"]["mode"] == "MOCK_ONLY"


def test_backend_api_token_auth_is_optional_until_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("LAB_BACKEND_API_TOKEN", raising=False)

    payload = handle_request("GET", "/api/ai-tasks", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is True


def test_backend_api_token_auth_blocks_non_health_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_BACKEND_API_TOKEN", "local-backend-token")
    store_path = tmp_path / "store.json"

    health = handle_request("GET", "/api/health", store_path=store_path)
    missing = handle_request("GET", "/api/ai-tasks", store_path=store_path)
    malformed = handle_request(
        "GET",
        "/api/ai-tasks",
        store_path=store_path,
        headers={"Authorization": "Token local-backend-token"},
    )
    invalid = handle_request(
        "GET",
        "/api/ai-tasks",
        store_path=store_path,
        headers={"Authorization": "Bearer wrong-token"},
    )
    authorized = handle_request(
        "GET",
        "/api/ai-tasks",
        store_path=store_path,
        headers={"Authorization": "Bearer local-backend-token"},
    )

    assert_api_envelope(health)
    assert health["success"] is True
    assert_api_envelope(missing)
    assert missing["success"] is False
    assert missing["code"] == "AUTH_REQUIRED"
    assert missing["errors"] == [{"field": "Authorization", "reason": "missing bearer token"}]
    assert_api_envelope(malformed)
    assert malformed["code"] == "AUTH_INVALID"
    assert malformed["errors"] == [{"field": "Authorization", "reason": "expected Bearer token"}]
    assert_api_envelope(invalid)
    assert invalid["code"] == "AUTH_INVALID"
    assert invalid["errors"] == [{"field": "Authorization", "reason": "invalid bearer token"}]
    assert_api_envelope(authorized)
    assert authorized["success"] is True
    assert authorized["data"]["total"] == 0


def test_backend_http_server_passes_authorization_header(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_BACKEND_API_TOKEN", "local-backend-token")
    server = mock_http_server.build_server(host="127.0.0.1", port=0, store_path=tmp_path / "store.json", quiet=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(f"{base_url}/api/health", timeout=5) as response:
            health = json.loads(response.read().decode("utf-8"))
        try:
            urlopen(f"{base_url}/api/ai-tasks", timeout=5)
            unauthorized = None
        except HTTPError as exc:
            unauthorized = exc
            unauthorized_body = json.loads(exc.read().decode("utf-8"))
        request = Request(f"{base_url}/api/ai-tasks", headers={"Authorization": "Bearer local-backend-token"})
        with urlopen(request, timeout=5) as response:
            authorized = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert_api_envelope(health)
    assert health["success"] is True
    assert unauthorized is not None
    assert unauthorized.code == 401
    assert unauthorized_body["code"] == "AUTH_REQUIRED"
    assert_api_envelope(authorized)
    assert authorized["success"] is True


def test_ai_tasks_list_and_get(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Mock lab",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    JsonTaskStore(store_path).save(task)

    listed = handle_request("GET", "/api/ai-tasks?status=WAITING_REVIEW", store_path=store_path)
    fetched = handle_request("GET", f"/api/ai-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(listed)
    assert listed["data"]["total"] == 1
    assert fetched["data"]["task"]["id"] == task.id


def test_review_detail_page_action_api_records_manual_approve_and_reject_validation(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Manual review target",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    JsonTaskStore(store_path).save(task)

    reject_without_reason = handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/reject",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    detail = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(reject_without_reason)
    assert reject_without_reason["success"] is False
    assert reject_without_reason["code"] == "VALIDATION_ERROR"
    assert reject_without_reason["errors"][0]["field"] == "reason"
    assert_api_envelope(approved)
    assert approved["data"]["task"]["status"] == "APPROVED"
    assert approved["data"]["auditEvent"]["action"] == "APPROVE"
    assert approved["data"]["operationAuditEvent"]["action"] == "REVIEW_APPROVE"
    assert approved["data"]["preApproveReviewCheck"]["applicable"] is False
    assert approved["data"]["preApproveReviewCheck"]["approvalStillAllowed"] is True
    assert approved["data"]["mode"] == "MOCK_ONLY"
    assert detail["data"]["reviewDetail"]["task"]["status"] == "APPROVED"
    assert detail["data"]["reviewDetail"]["summary"]["reviewAuditEventTotal"] == 1


def test_lab_generate_creates_waiting_review_task(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": str(source)},
    )
    task_id = payload["data"]["task"]["id"]
    fetched = handle_request("GET", f"/api/ai-tasks/{task_id}", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["task"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["task"]["taskType"] == "LAB_GENERATION"
    expected_lab_output = f"examples/output/{task_id}-lab.json"
    assert payload["data"]["task"]["finalResultPath"] == expected_lab_output
    assert payload["data"]["dslPath"] == expected_lab_output
    assert payload["data"]["providerGeneration"]["dslPath"] == expected_lab_output
    assert payload["data"]["dsl"]["kind"] == "Lab"
    assert payload["data"]["dsl"]["spec"]["materials"][0]["path"] == str(source)
    assert len(payload["data"]["dsl"]["spec"]["objectives"]) >= 2
    assert len(payload["data"]["dsl"]["spec"]["steps"]) >= 3
    assert (mock_api.ROOT / expected_lab_output).exists()
    assert payload["data"]["providerGeneration"]["provider"]["adapterId"] == "mock_provider_adapter"
    assert payload["data"]["providerGeneration"]["provider"]["realLlmCalled"] is False
    assert payload["data"]["providerGeneration"]["providerCallAuditEvent"]["status"] == "SUCCESS"
    assert payload["data"]["providerGeneration"]["providerCallAuditEvent"]["detail"]["workflowId"] == "lab_generate"
    assert payload["data"]["providerGeneration"]["providerCallAuditEvent"]["taskCreated"] is False
    assert payload["data"]["providerGeneration"]["providerCallAuditEvent"]["realLlmCalled"] is False
    assert payload["data"]["reviewRequired"] is True
    assert payload["data"]["materialAnalysis"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["materialAnalysis"]["unknownShellExecuted"] is False
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} == {"MATERIAL_ANALYSIS", "LAB_DSL"}
    readiness = payload["data"]["labFeatureReadiness"]
    assert readiness["component"] == "LabGenerationV1Readiness"
    assert readiness["completeForStableV1"] is True
    assert readiness["requirements"]["taskSpecificOutputCreated"] is True
    assert readiness["requirements"]["sourceMaterialReferenced"] is True
    assert readiness["requirements"]["minimumTeachingQualityMet"] is True
    lab_artifact = next(artifact for artifact in payload["data"]["artifacts"] if artifact["kind"] == "LAB_DSL")
    assert lab_artifact["metadata"]["labFeatureReadiness"]["completeForStableV1"] is True
    assert fetched["data"]["task"]["id"] == task_id
    audit = handle_request("GET", "/api/provider-audit-events?promptId=lab_generation_v0", store_path=store_path)
    assert audit["data"]["total"] == 1
    assert audit["data"]["items"][0]["detail"]["workflowStep"] == "generate_lab_dsl"
    (mock_api.ROOT / expected_lab_output).unlink(missing_ok=True)


def test_lab_generate_requires_input(tmp_path):
    payload = handle_request("POST", "/api/labs/generate", store_path=tmp_path / "store.json", body={})

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"


def test_lab_generate_recovers_invalid_utf8_local_store(tmp_path):
    store_path = tmp_path / "store.json"
    store_path.write_bytes(b'{"tasks": \xff}')

    payload = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is True
    assert list(tmp_path.glob("store.json.corrupt-*"))


def test_lab_generate_requires_existing_input_file(tmp_path):
    payload = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=tmp_path / "store.json",
        body={"input": str(tmp_path / "missing.md")},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"


def test_lab_generate_requires_post(tmp_path):
    payload = handle_request("GET", "/api/labs/generate", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_generation_endpoints_forward_explicit_real_llm_options_and_keep_review_status(tmp_path, monkeypatch):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# UI real LLM source", encoding="utf-8")
    captured = []

    def fake_real_generation(kind, **kwargs):
        captured.append({"kind": kind, **kwargs})
        generation = mock_api.generate_mock_dsl_via_adapter(
            kind,
            input_ref=str(kwargs.get("input_ref") or "ui-test"),
            trace_id=str(kwargs["trace_id"]),
            root=kwargs["root"],
        )
        generation["dslPath"] = kwargs["output_ref"]
        generation["provider"] = {
            "adapterId": "openai_responses_sdk_adapter",
            "interfaceName": "LLMProvider",
            "operation": "generateJson",
            "providerId": "openai",
            "mode": "REAL_LLM",
            "realLlmCalled": True,
            "secretsRead": True,
            "networkAccess": True,
        }
        return generation

    monkeypatch.setattr(mock_api, "generate_real_llm_demo_dsl_via_provider", fake_real_generation)
    options = {
        "providerMode": "real-llm",
        "model": "ui-test-model",
        "baseUrl": "https://example.test/v1",
        "explicitRealCallOptIn": True,
        "confirmWaitingReview": True,
        "confirmNoAutoPublish": True,
    }

    lab = handle_request("POST", "/api/labs/generate", store_path=store_path, body={"input": str(source), **options})
    exam = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo", "labDslPath": "templates/lab/examples/basic-lab.yaml", **options},
    )
    ppt = handle_request("POST", "/api/ppt/generate", store_path=store_path, body={"input": str(source), **options})

    for payload in (lab, exam, ppt):
        assert_api_envelope(payload)
        assert payload["data"]["mode"] == "REAL_LLM"
        assert payload["data"]["task"]["status"] == "WAITING_REVIEW"
    assert [item["kind"] for item in captured] == ["lab", "exam", "grading", "ppt"]
    assert all(item["model"] == "ui-test-model" for item in captured)
    assert all(item["base_url"] == "https://example.test/v1" for item in captured)
    assert all(item["explicit_real_call_opt_in"] is True for item in captured)
    assert all(item["confirm_waiting_review"] is True for item in captured)
    assert all(item["confirm_no_auto_publish"] is True for item in captured)
    (mock_api.ROOT / lab["data"]["task"]["finalResultPath"]).unlink(missing_ok=True)


def test_exam_generate_from_lab_creates_waiting_review_task(tmp_path):
    store_path = tmp_path / "store.json"

    payload = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    task_id = payload["data"]["task"]["id"]
    fetched = handle_request("GET", f"/api/ai-tasks/{task_id}", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["task"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["task"]["taskType"] == "EXAM_GENERATION"
    assert payload["data"]["examDsl"]["kind"] == "Exam"
    assert payload["data"]["gradingDsl"]["kind"] == "Grading"
    assert payload["data"]["providerGenerations"]["exam"]["provider"]["adapterId"] == "mock_provider_adapter"
    assert payload["data"]["providerGenerations"]["grading"]["provider"]["networkAccess"] is False
    assert payload["data"]["providerGenerations"]["exam"]["providerCallAuditEvent"]["detail"]["workflowStep"] == "generate_exam_dsl"
    assert payload["data"]["providerGenerations"]["grading"]["providerCallAuditEvent"]["detail"]["workflowStep"] == "generate_grading_dsl"
    assert payload["data"]["answerVisibleToCandidate"] is False
    assert fetched["data"]["task"]["id"] == task_id


def test_exam_generate_from_lab_requires_lab_id(tmp_path):
    payload = handle_request("POST", "/api/exams/generate-from-lab", store_path=tmp_path / "store.json", body={})

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "labId"


def test_exam_generate_from_lab_requires_post(tmp_path):
    payload = handle_request("GET", "/api/exams/generate-from-lab", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_ppt_generate_creates_waiting_review_task(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# PPT Source", encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/ppt/generate",
        store_path=store_path,
        body={"input": str(source)},
    )
    task_id = payload["data"]["task"]["id"]
    fetched = handle_request("GET", f"/api/ai-tasks/{task_id}", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["task"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["task"]["taskType"] == "PPT_GENERATION"
    assert payload["data"]["pptDsl"]["kind"] == "PPT"
    assert payload["data"]["providerGeneration"]["provider"]["adapterId"] == "mock_provider_adapter"
    assert payload["data"]["providerGeneration"]["provider"]["secretsRead"] is False
    assert payload["data"]["providerGeneration"]["providerCallAuditEvent"]["detail"]["workflowId"] == "ppt_generate"
    assert payload["data"]["providerGeneration"]["providerCallAuditEvent"]["mockOutputCreated"] is True
    assert payload["data"]["artifactGenerated"] is False
    assert fetched["data"]["task"]["id"] == task_id


def test_ppt_generate_requires_input(tmp_path):
    payload = handle_request("POST", "/api/ppt/generate", store_path=tmp_path / "store.json", body={})

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"


def test_ppt_generate_requires_existing_input_file(tmp_path):
    payload = handle_request(
        "POST",
        "/api/ppt/generate",
        store_path=tmp_path / "store.json",
        body={"input": str(tmp_path / "missing.md")},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"


def test_ppt_generate_requires_post(tmp_path):
    payload = handle_request("GET", "/api/ppt/generate", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_ai_task_not_found_returns_json(tmp_path):
    payload = handle_request("GET", "/api/ai-tasks/missing", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"


def test_ai_task_approve_updates_review_status(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Mock lab",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    JsonTaskStore(store_path).save(task)

    payload = handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    fetched = handle_request("GET", f"/api/ai-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["task"]["status"] == "APPROVED"
    assert payload["data"]["task"]["reviewer"] == "teacher_1"
    assert payload["data"]["auditEvent"]["action"] == "APPROVE"
    assert payload["data"]["auditEvent"]["actor"] == "teacher_1"
    assert payload["data"]["auditEvent"]["realPublish"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "REVIEW_APPROVE"
    assert payload["data"]["operationAuditEvent"]["realPublish"] is False
    assert fetched["data"]["task"]["status"] == "APPROVED"


def test_review_audit_events_list_filters_by_task_and_action(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Mock lab",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    JsonTaskStore(store_path).save(task)
    handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )

    payload = handle_request(
        "GET",
        f"/api/review-audit-events?taskId={task.id}&action=APPROVE",
        store_path=store_path,
    )

    assert_api_envelope(payload)
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["taskId"] == task.id
    assert payload["data"]["items"][0]["action"] == "APPROVE"
    assert payload["data"]["items"][0]["mode"] == "MOCK_ONLY"


def test_review_audit_events_rejects_unknown_action(tmp_path):
    payload = handle_request("GET", "/api/review-audit-events?action=UNKNOWN", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "action"


def test_operation_audit_events_list_filters_by_resource_and_action(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Mock lab",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    JsonTaskStore(store_path).save(task)
    handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )

    payload = handle_request(
        "GET",
        f"/api/audit-events?resourceType=AI_TASK&resourceId={task.id}&action=REVIEW_APPROVE",
        store_path=store_path,
    )

    assert_api_envelope(payload)
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["resourceId"] == task.id
    assert payload["data"]["items"][0]["action"] == "REVIEW_APPROVE"
    assert payload["data"]["items"][0]["realPublish"] is False


def test_operation_audit_events_rejects_unknown_resource_type(tmp_path):
    payload = handle_request("GET", "/api/audit-events?resourceType=UNKNOWN", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "resourceType"


def test_providers_list_returns_mock_registry(tmp_path):
    payload = handle_request("GET", "/api/providers", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["activeProvider"] == "mock"
    assert payload["data"]["realLlmCalled"] is False
    assert payload["data"]["secretsRead"] is False
    assert [provider["id"] for provider in payload["data"]["providers"] if provider["enabled"]] == ["mock"]


def test_provider_health_returns_mock_status(tmp_path):
    payload = handle_request("GET", "/api/providers/mock/health", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["data"]["providerId"] == "mock"
    assert payload["data"]["status"] == "UP"
    assert payload["data"]["realLlmCalled"] is False
    assert payload["data"]["networkAccess"] is False


def test_provider_real_llm_runtime_config_api_is_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-never-return")
    monkeypatch.setenv("OPENAI_MODEL", "mimo-v2.5-pro")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.test/v1")

    payload = handle_request("GET", "/api/providers/real-llm-runtime-config", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    config = payload["data"]["realLlmRuntimeConfig"]
    assert config["component"] == "RealLlmRuntimeConfigSummary"
    assert config["env"]["OPENAI_API_KEY"]["present"] is True
    assert config["env"]["OPENAI_API_KEY"]["valueReturned"] is False
    assert "value" not in config["env"]["OPENAI_API_KEY"]
    assert config["env"]["OPENAI_MODEL"]["value"] == "mimo-v2.5-pro"
    assert config["readyForRealLlmCommand"] is True
    assert config["safety"]["requestSent"] is False
    assert config["safety"]["realLlmCalled"] is False
    assert "sk-test-never-return" not in json.dumps(payload)


def test_provider_health_rejects_disabled_provider(tmp_path):
    payload = handle_request("GET", "/api/providers/openai/health", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "PROVIDER_DISABLED"
    assert payload["errors"][0]["field"] == "provider"
    assert payload["providerErrorContext"]["adapterId"] == "mock_provider_adapter"
    assert payload["providerErrorContext"]["operation"] == "health"
    assert payload["providerErrorContext"]["providerId"] == "openai"
    assert payload["providerErrorContext"]["realLlmCalled"] is False
    assert payload["providerErrorContext"]["secretsRead"] is False
    assert payload["providerErrorContext"]["networkAccess"] is False
    assert payload["providerErrorContext"]["taskCreated"] is False


def test_provider_mock_generate_returns_waiting_review_dsl(tmp_path):
    payload = handle_request(
        "POST",
        "/api/providers/mock/generate",
        store_path=tmp_path / "store.json",
        body={"promptId": "exam_generation_v0", "outputKind": "Exam", "inputRef": "lab_demo"},
    )

    assert_api_envelope(payload)
    assert payload["data"]["providerId"] == "mock"
    assert payload["data"]["adapterId"] == "mock_provider_adapter"
    assert payload["data"]["interfaceName"] == "LLMProvider"
    assert payload["data"]["operation"] == "generateJson"
    assert payload["data"]["outputKind"] == "Exam"
    assert payload["data"]["dslPath"] == "templates/exam/examples/notebook-fill-blank.yaml"
    assert payload["data"]["dsl"]["kind"] == "Exam"
    assert payload["data"]["generatedStatus"] == "WAITING_REVIEW"
    assert payload["data"]["reviewRequired"] is True
    assert payload["data"]["publishBlockedUntilApproved"] is True
    assert payload["data"]["answerVisibleToCandidate"] is False
    assert payload["data"]["realLlmCalled"] is False
    assert payload["data"]["secretsRead"] is False


def test_provider_mock_generate_requires_prompt_id(tmp_path):
    payload = handle_request("POST", "/api/providers/mock/generate", store_path=tmp_path / "store.json", body={})

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "promptId"
    assert "providerErrorContext" not in payload


def test_provider_audit_events_record_backend_provider_calls(tmp_path):
    store_path = tmp_path / "store.json"

    health = handle_request("GET", "/api/providers/mock/health", store_path=store_path)
    failed = handle_request(
        "POST",
        "/api/providers/mock/generate",
        store_path=store_path,
        body={"promptId": "missing_prompt"},
    )
    listed = handle_request("GET", "/api/provider-audit-events?status=FAILED&operation=generateJson", store_path=store_path)

    assert_api_envelope(health)
    assert health["data"]["providerCallAuditEvent"]["status"] == "SUCCESS"
    assert health["data"]["providerCallAuditEvent"]["operation"] == "health"
    assert failed["success"] is False
    assert failed["code"] == "NOT_FOUND"
    assert_api_envelope(listed)
    assert listed["data"]["total"] == 1
    event = listed["data"]["items"][0]
    assert event["providerId"] == "mock"
    assert event["promptId"] == "missing_prompt"
    assert event["errorCode"] == "NOT_FOUND"
    assert event["generatedContentCreated"] is False
    assert event["realLlmCalled"] is False
    assert event["networkAccess"] is False


def test_provider_audit_events_reject_invalid_status(tmp_path):
    payload = handle_request("GET", "/api/provider-audit-events?status=BAD", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "status"


def test_mcp_tool_call_records_endpoint_lists_and_filters_records(tmp_path):
    store_path = tmp_path / "store.json"
    record = create_mcp_tool_call_record(
        tool_name="analyze_material",
        status=McpToolCallStatus.SUCCESS,
        actor="mcp-mock",
        backend_method="POST",
        backend_path="/api/materials/analyze",
        risk_level="low",
        review_required=False,
        trace_id="trace_mcp_api",
        argument_keys=["input"],
        argument_preview={"input": "examples/input/demo-source.md"},
        backend_called=True,
        response_code="OK",
        response_message="素材分析完成",
        backend_trace_id="trace_backend_api",
    )
    JsonTaskStore(store_path).save_mcp_tool_call_record(record)

    payload = handle_request(
        "GET",
        "/api/mcp-tool-call-records?toolName=analyze_material&status=SUCCESS&traceId=trace_mcp_api",
        store_path=store_path,
    )

    assert_api_envelope(payload)
    assert payload["data"]["total"] == 1
    item = payload["data"]["items"][0]
    assert item["toolName"] == "analyze_material"
    assert item["status"] == "SUCCESS"
    assert item["backendCalled"] is True
    assert item["realMcpServerStarted"] is False


def test_mcp_tool_call_records_endpoint_rejects_invalid_status(tmp_path):
    payload = handle_request("GET", "/api/mcp-tool-call-records?status=BAD", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "status"


def test_mcp_server_mock_endpoints_return_info_and_tools(tmp_path):
    info = handle_request("GET", "/api/mcp/server/info", store_path=tmp_path / "store.json")
    tools = handle_request("GET", "/api/mcp/server/tools", store_path=tmp_path / "store.json")

    assert_api_envelope(info)
    assert_api_envelope(tools)
    assert info["data"]["server"]["phase"] == "Phase 4"
    assert info["data"]["server"]["transport"] == "local_function_only"
    assert info["data"]["server"]["toolProfile"] == "local-core-mvp"
    assert info["data"]["server"]["manifestToolCount"] > info["data"]["server"]["toolCount"]
    assert info["data"]["safety"]["realMcpServerStarted"] is False
    assert info["data"]["safety"]["networkListenerStarted"] is False
    assert tools["data"]["total"] == tools["data"]["server"]["toolCount"]
    names = {tool["name"] for tool in tools["data"]["items"]}
    assert "analyze_material" in names
    assert "run_grading_evidence_auto" in names
    assert "create_agent_entity_import_dry_run" in names
    assert "agent_internal_publish_request" not in names
    assert "query_agent_publish_status" not in names
    assert "publish_lab" not in names
    assert "destroy_environment" not in names
    assert tools["data"]["toolPolicy"]["realPlatformBackendToolsEnabledByDefault"] is False


def test_mcp_server_mock_call_endpoint_invokes_tool_and_records_audit(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/mcp/server/call",
        store_path=store_path,
        body={"tool": "analyze_material", "arguments": {"input": str(source)}},
    )

    assert_api_envelope(payload)
    assert payload["data"]["networkListenerStarted"] is False
    response = payload["data"]["response"]
    assert response["success"] is True
    assert response["data"]["analysis"]["mode"] == "MOCK_ONLY"
    assert response["data"]["mcpServer"]["id"] == "ai_training_platform_mcp_mock"
    assert response["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    assert response["data"]["mcpToolCallRecord"]["actor"] == "backend-mcp-server"

    records = JsonTaskStore(store_path).list_mcp_tool_call_records(actor="backend-mcp-server")
    assert len(records) == 1
    assert records[0].toolName == "analyze_material"


def test_mcp_server_mock_call_endpoint_invokes_review_revision_loop(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    created = handle_request("POST", "/api/labs/generate", store_path=store_path, body={"input": str(source)})
    source_task_id = created["data"]["task"]["id"]

    revision = handle_request(
        "POST",
        "/api/mcp/server/call",
        store_path=store_path,
        body={
            "tool": "request_review_revision",
            "profile": "all",
            "arguments": {
                "taskId": source_task_id,
                "reviewer": "teacher_1",
                "comment": "补充步骤截图验收标准。",
                "priority": "HIGH",
            },
        },
    )
    revision_request_id = revision["data"]["response"]["data"]["revisionRequest"]["id"]
    regeneration = handle_request(
        "POST",
        "/api/mcp/server/call",
        store_path=store_path,
        body={
            "tool": "regenerate_from_revision_mock",
            "profile": "all",
            "arguments": {
                "taskId": source_task_id,
                "reviewer": "teacher_1",
                "revisionRequestId": revision_request_id,
            },
        },
    )

    assert_api_envelope(revision)
    assert revision["data"]["response"]["success"] is True
    assert revision["data"]["response"]["data"]["revisionRequest"]["taskStatusChanged"] is False
    assert revision["data"]["response"]["data"]["revisionRequest"]["newLlmRequestSent"] is False
    assert revision["data"]["response"]["data"]["mcpToolCallRecord"]["actor"] == "backend-mcp-server"
    assert_api_envelope(regeneration)
    response = regeneration["data"]["response"]
    assert response["success"] is True
    assert response["data"]["mockRegeneration"]["sourceTask"]["status"] == "WAITING_REVIEW"
    assert response["data"]["mockRegeneration"]["newTask"]["status"] == "WAITING_REVIEW"
    assert response["data"]["mockRegeneration"]["safety"]["newLlmRequestSent"] is False
    assert response["data"]["mcpServerSafety"]["networkListenerStarted"] is False
    assert response["data"]["mcpToolCallRecord"]["toolName"] == "regenerate_from_revision_mock"


def test_mcp_server_mock_call_endpoint_rejects_bad_arguments(tmp_path):
    missing_tool = handle_request("POST", "/api/mcp/server/call", store_path=tmp_path / "store.json", body={"arguments": {}})
    bad_arguments = handle_request(
        "POST",
        "/api/mcp/server/call",
        store_path=tmp_path / "store.json",
        body={"tool": "analyze_material", "arguments": []},
    )

    assert_api_envelope(missing_tool)
    assert missing_tool["success"] is False
    assert missing_tool["code"] == "VALIDATION_ERROR"
    assert missing_tool["errors"][0]["field"] == "tool"
    assert_api_envelope(bad_arguments)
    assert bad_arguments["success"] is False
    assert bad_arguments["code"] == "VALIDATION_ERROR"
    assert bad_arguments["errors"][0]["field"] == "arguments"


def test_high_risk_mcp_publish_lab_intent_creates_waiting_review_task(tmp_path):
    store_path = tmp_path / "store.json"

    payload = handle_request(
        "POST",
        "/api/mcp/intents/publish-lab",
        store_path=store_path,
        body={"labId": "lab_demo", "reason": "运营申请发布", "actor": "operator_1"},
    )

    assert_api_envelope(payload)
    assert payload["data"]["intent"]["type"] == "publish_lab"
    assert payload["data"]["intent"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["intent"]["realPublish"] is False
    assert payload["data"]["intent"]["autoPublishAllowed"] is False
    assert payload["data"]["task"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["task"]["taskType"] == "MCP_PUBLISH_LAB_INTENT"
    assert payload["data"]["operationAuditEvent"]["action"] == "PUBLISH_LAB_INTENT"
    assert payload["data"]["operationAuditEvent"]["resourceType"] == "LAB"
    assert payload["data"]["operationAuditEvent"]["realPublish"] is False
    assert payload["data"]["operationAuditEvent"]["detail"]["realActionExecuted"] is False
    assert payload["data"]["operationAuditEvent"]["detail"]["blockedUntilApproved"] is True
    tasks = JsonTaskStore(store_path).list(status="WAITING_REVIEW", task_type="MCP_PUBLISH_LAB_INTENT")
    assert len(tasks) == 1


def test_high_risk_mcp_destroy_environment_intent_does_not_change_environment(tmp_path):
    store_path = tmp_path / "store.json"
    environment = EnvironmentInstance(envType=EnvironmentType.VM, title="Ubuntu VM", image="ubuntu-22.04")
    JsonTaskStore(store_path).save_environment(environment)

    payload = handle_request(
        "POST",
        "/api/mcp/intents/destroy-environment",
        store_path=store_path,
        body={"environmentId": environment.id, "reason": "清理申请", "actor": "operator_1"},
    )
    fetched = handle_request("GET", f"/api/environments/{environment.id}", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["intent"]["type"] == "destroy_environment"
    assert payload["data"]["intent"]["requiresSecondConfirmation"] is True
    assert payload["data"]["intent"]["environmentDestroyed"] is False
    assert payload["data"]["intent"]["realCloudResourceChanged"] is False
    assert payload["data"]["task"]["taskType"] == "MCP_DESTROY_ENVIRONMENT_INTENT"
    assert payload["data"]["operationAuditEvent"]["action"] == "DESTROY_ENVIRONMENT_INTENT"
    assert payload["data"]["operationAuditEvent"]["detail"]["requiresSecondConfirmation"] is True
    assert fetched["data"]["environment"]["status"] == "CREATED"


def test_high_risk_mcp_intent_requires_parameters_and_post(tmp_path):
    missing = handle_request("POST", "/api/mcp/intents/publish-exam", store_path=tmp_path / "store.json", body={"reason": "发布"})
    wrong_method = handle_request("GET", "/api/mcp/intents/publish-lab", store_path=tmp_path / "store.json")

    assert_api_envelope(missing)
    assert missing["success"] is False
    assert missing["code"] == "VALIDATION_ERROR"
    assert missing["errors"][0]["field"] == "examId"
    assert_api_envelope(wrong_method)
    assert wrong_method["success"] is False
    assert wrong_method["code"] == "METHOD_NOT_ALLOWED"


def test_provider_generate_rejects_disabled_provider(tmp_path):
    payload = handle_request(
        "POST",
        "/api/providers/openai/generate",
        store_path=tmp_path / "store.json",
        body={"promptId": "lab_generation_v0"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "PROVIDER_DISABLED"
    assert payload["errors"][0]["field"] == "provider"
    assert payload["providerErrorContext"]["operation"] == "generateJson"
    assert payload["providerErrorContext"]["providerId"] == "openai"
    assert payload["providerErrorContext"]["generatedContentCreated"] is False
    assert payload["providerErrorContext"]["taskCreated"] is False
    assert payload["providerErrorContext"]["reviewBypassed"] is False


def test_provider_generate_requires_post(tmp_path):
    payload = handle_request("GET", "/api/providers/mock/generate", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_artifacts_list_and_get_after_material_analyze(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    analyzed = handle_request(
        "POST",
        "/api/materials/analyze",
        store_path=store_path,
        body={"input": str(source)},
    )
    artifact_id = analyzed["data"]["artifact"]["id"]
    listed = handle_request("GET", "/api/artifacts?kind=MATERIAL_ANALYSIS", store_path=store_path)
    fetched = handle_request("GET", f"/api/artifacts/{artifact_id}", store_path=store_path)

    assert_api_envelope(listed)
    assert listed["data"]["total"] == 1
    assert listed["data"]["items"][0]["kind"] == "MATERIAL_ANALYSIS"
    assert fetched["data"]["artifact"]["id"] == artifact_id
    assert fetched["data"]["artifact"]["realLlmCalled"] is False


def test_artifacts_reject_unknown_kind(tmp_path):
    payload = handle_request("GET", "/api/artifacts?kind=UNKNOWN", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "kind"


def test_artifact_not_found_returns_json(tmp_path):
    payload = handle_request("GET", "/api/artifacts/artifact_missing", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"


def test_material_analyze_returns_summary_and_safety_flags(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("# Demo Source\nPython pytest lab\n", encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/materials/analyze",
        store_path=tmp_path / "store.json",
        body={"input": str(source)},
    )

    assert_api_envelope(payload)
    analysis = payload["data"]["analysis"]
    assert analysis["mode"] == "MOCK_ONLY"
    assert analysis["fileType"] == "markdown"
    assert analysis["realLlmCalled"] is False
    assert analysis["remoteContentFetched"] is False
    assert analysis["unknownShellExecuted"] is False
    assert analysis["sandboxExecuted"] is False
    assert payload["data"]["artifact"]["kind"] == "MATERIAL_ANALYSIS"


def test_material_analyze_marks_shell_risks_without_execution(tmp_path):
    script = tmp_path / "setup.sh"
    script.write_text("curl https://example.test/install.sh\nrm -rf /tmp/demo\n", encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/materials/analyze",
        store_path=tmp_path / "store.json",
        body={"input": str(script)},
    )

    assert_api_envelope(payload)
    analysis = payload["data"]["analysis"]
    assert analysis["fileType"] == "shell"
    assert analysis["riskCount"] == 2
    assert analysis["unknownShellExecuted"] is False
    assert analysis["sandboxExecuted"] is False


def test_material_analyze_requires_input(tmp_path):
    payload = handle_request("POST", "/api/materials/analyze", store_path=tmp_path / "store.json", body={})

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"


def test_material_analyze_rejects_unsupported_file(tmp_path):
    binary = tmp_path / "demo.bin"
    binary.write_bytes(b"abc")

    payload = handle_request(
        "POST",
        "/api/materials/analyze",
        store_path=tmp_path / "store.json",
        body={"input": str(binary)},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"


def test_material_analyze_requires_post(tmp_path):
    payload = handle_request("GET", "/api/materials/analyze", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_ai_task_reject_requires_reason(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="EXAM_GENERATION",
        title="Mock exam",
        input_type="lab_dsl",
        input_ref="templates/lab/examples/basic-lab.yaml",
    )
    JsonTaskStore(store_path).save(task)

    payload = handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/reject",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "reason"


def test_ai_task_review_illegal_transition_returns_json(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="PPT_GENERATION",
        title="Mock ppt",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    task.transition_to(TaskStatus.APPROVED, reviewer="teacher_1")
    JsonTaskStore(store_path).save(task)

    payload = handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/reject",
        store_path=store_path,
        body={"reviewer": "teacher_2", "reason": "不符合要求"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "STATE_TRANSITION_ERROR"


def test_ai_task_review_action_requires_post(tmp_path):
    payload = handle_request("GET", "/api/ai-tasks/task_demo/approve", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_review_tasks_defaults_to_waiting_review(tmp_path):
    store_path = tmp_path / "store.json"
    waiting = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Mock lab",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    approved = create_waiting_review_task(
        task_type="PPT_GENERATION",
        title="Mock ppt",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    approved.transition_to(TaskStatus.APPROVED, reviewer="teacher_1")
    store = JsonTaskStore(store_path)
    store.save(waiting)
    store.save(approved)

    payload = handle_request("GET", "/api/review-tasks", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["total"] == 1
    assert payload["data"]["reviewRequired"] is True
    assert payload["data"]["items"][0]["id"] == waiting.id


def test_review_tasks_filters_by_task_type(tmp_path):
    store_path = tmp_path / "store.json"
    lab = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Mock lab",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    ppt = create_waiting_review_task(
        task_type="PPT_GENERATION",
        title="Mock ppt",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    store = JsonTaskStore(store_path)
    store.save(lab)
    store.save(ppt)

    payload = handle_request("GET", "/api/review-tasks?taskType=PPT_GENERATION", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["taskType"] == "PPT_GENERATION"


def test_review_tasks_rejects_unknown_status(tmp_path):
    payload = handle_request("GET", "/api/review-tasks?status=UNKNOWN", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "status"


def test_review_task_summary_returns_batch_cards(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    handle_request("POST", "/api/labs/generate", store_path=store_path, body={"input": str(source)})
    handle_request("POST", "/api/ppt/generate", store_path=store_path, body={"input": str(source)})

    payload = handle_request("GET", "/api/review-task-summary", store_path=store_path)

    assert_api_envelope(payload)
    summary = payload["data"]["reviewTaskSummary"]
    assert summary["mode"] == "MOCK_ONLY"
    assert summary["total"] == 2
    assert summary["queueSummary"]["waitingReviewTotal"] == 2
    assert summary["batchActionPolicy"]["batchApproveAllowed"] is False
    assert summary["batchActionPolicy"]["batchPublishAllowed"] is False
    assert summary["safety"]["realPublish"] is False
    assert {item["task"]["taskType"] for item in summary["items"]} == {"LAB_GENERATION", "PPT_GENERATION"}
    priority_queue = summary["reviewPriorityQueue"]
    assert priority_queue["enabled"] is True
    assert priority_queue["summary"]["queueTotal"] == 2
    assert priority_queue["summary"]["normalTotal"] == 2
    assert priority_queue["summary"]["batchStateChangeAllowed"] is False
    assert [item["rank"] for item in priority_queue["items"]] == [1, 2]
    assert {item["reasonCode"] for item in priority_queue["items"]} == {
        "LAB_QUALITY_NEEDS_REVIEW",
        "PPT_SLIDE_PLAN_REVIEW",
    }
    real_demo_queue = summary["realDemoReviewQueue"]
    assert real_demo_queue["component"] == "RealDemoReviewQueue"
    assert real_demo_queue["source"] == "reviewTaskSummary.realDemoReviewQueue + local examples/output real LLM artifacts"
    assert real_demo_queue["fallbackSource"] == (
        "realDemoPrototype.generatedDsl + realDemoPrototype.coreBusinessDemoPath + "
        "realDemoPrototype.readonlyEvidenceDemo.reportDetail"
    )
    assert real_demo_queue["sourceMode"] in {"LOCAL_REAL_LLM_ARTIFACTS", "STATIC_DEMO_FALLBACK"}
    assert real_demo_queue["taskTotal"] == 4
    assert real_demo_queue["waitingReviewTotal"] == 4
    assert real_demo_queue["schemaValidatedTotal"] >= 0
    assert real_demo_queue["localArtifactTotal"] >= 0
    assert real_demo_queue["dynamicTaskTotal"] == 0
    assert real_demo_queue["readonlyEvidenceReportDetailSource"] == "realDemoPrototype.readonlyEvidenceDemo.reportDetail"
    assert real_demo_queue["readonlyEvidenceCollectedTotal"] == 2
    assert real_demo_queue["answerVisibleToCandidate"] is False
    assert real_demo_queue["manualReviewRequired"] is True
    assert real_demo_queue["autoApproveAllowed"] is False
    assert real_demo_queue["batchStateChangeAllowed"] is False
    assert real_demo_queue["realPublishAllowed"] is False
    assert [item["taskId"] for item in real_demo_queue["items"]] == [
        "real_demo_lab",
        "real_demo_exam",
        "real_demo_grading",
        "real_demo_ppt",
    ]
    assert all(item["status"] == "WAITING_REVIEW" for item in real_demo_queue["items"])
    assert all("localArtifactExists" in item for item in real_demo_queue["items"])
    assert all(item["dynamicTaskAvailable"] is False for item in real_demo_queue["items"])
    assert real_demo_queue["items"][1]["candidatePreviewAnswersRemoved"] is True
    assert real_demo_queue["items"][2]["readonlyEvidenceStatus"] == "COLLECTED"
    assert real_demo_queue["items"][3]["pptPageReviewActionVisible"] is True
    controlled_signal = summary["controlledDockerEvidenceReviewSignal"]
    assert controlled_signal["component"] == "ControlledDockerEvidenceReviewSignal"
    assert controlled_signal["source"] == "realDemoPrototype.controlledDockerEvidenceDemo"
    assert controlled_signal["dynamicSource"] == "reviewDetail.controlledGradingEvidence"
    assert controlled_signal["fallbackSource"] == "realDemoPrototype.controlledDockerEvidenceDemo"
    assert controlled_signal["sourceMode"] == "STATIC_DEMO_FALLBACK"
    assert controlled_signal["taskId"] == "real_demo_grading"
    assert controlled_signal["status"] == "PARTIAL_CONTROLLED_EVIDENCE_COLLECTED"
    assert controlled_signal["available"] is True
    assert controlled_signal["taskTotal"] == 1
    assert controlled_signal["planTotal"] == 1
    assert controlled_signal["reportTotal"] == 1
    assert controlled_signal["controlledPlanPath"] == "examples/output/mimo-real-demo-controlled-plan.json"
    assert controlled_signal["controlledReportPath"] == "examples/output/mimo-real-demo-controlled-sandbox-report.json"
    assert controlled_signal["coveredCheckIds"] == ["check_q1", "check_q4"]
    assert controlled_signal["coveredCheckTypes"] == ["stdout_contains", "pytest"]
    assert controlled_signal["executed"] == 2
    assert controlled_signal["passed"] == 2
    assert controlled_signal["earnedScore"] == 40
    assert controlled_signal["totalControlledScore"] == 40
    assert controlled_signal["items"][0]["source"] == "realDemoPrototype.controlledDockerEvidenceDemo"
    assert controlled_signal["items"][0]["planPath"] == "examples/output/mimo-real-demo-controlled-plan.json"
    assert controlled_signal["items"][0]["reportPath"] == "examples/output/mimo-real-demo-controlled-sandbox-report.json"
    assert controlled_signal["items"][0]["networkEnabled"] is False
    assert controlled_signal["remainingCheckIds"] == ["check_q2", "check_q3"]
    assert controlled_signal["remainingCheckTypes"] == ["notebook_cell"]
    assert controlled_signal["remainingStatus"] == "STATIC_NOTEBOOK_EVIDENCE_READY_FOR_REVIEW"
    assert controlled_signal["notebookEvidenceReviewPlanSource"] == "reviewTaskSummary.notebookEvidenceReviewPlan"
    assert controlled_signal["remainingReviewPlanStatus"] == "NOTEBOOK_STATIC_EVIDENCE_COLLECTED"
    assert controlled_signal["remainingScore"] == 60
    assert controlled_signal["recommendedAction"] == "review_container_and_static_notebook_evidence_before_approval"
    assert controlled_signal["manualReviewRequired"] is True
    assert controlled_signal["autoApproveAllowed"] is False
    assert controlled_signal["batchStateChangeAllowed"] is False
    assert controlled_signal["realPublishAllowed"] is False
    assert controlled_signal["safety"]["hostExecutionAllowed"] is False
    assert controlled_signal["safety"]["networkAllowed"] is False
    notebook_plan = summary["notebookEvidenceReviewPlan"]
    assert notebook_plan["component"] == "NotebookEvidenceReviewPlan"
    assert notebook_plan["status"] == "NOTEBOOK_STATIC_EVIDENCE_COLLECTED"
    assert notebook_plan["remainingCheckIds"] == ["check_q2", "check_q3"]
    assert notebook_plan["checkTypes"] == ["notebook_cell"]
    assert notebook_plan["checkTotal"] == 2
    assert notebook_plan["scoreTotal"] == 60
    assert notebook_plan["evidenceStatus"] == "STATIC_NOTEBOOK_EVIDENCE_COLLECTED"
    assert notebook_plan["reviewStrategy"] == "STATIC_NOTEBOOK_JSON_PARSE_REVIEW"
    assert notebook_plan["requiredReviewerActions"] == [
        "verify_notebook_cell_targets",
        "verify_expected_output_tokens",
        "review_static_notebook_evidence_matches_expected_tokens",
        "confirm_no_notebook_kernel_started",
    ]
    assert [item["checkId"] for item in notebook_plan["items"]] == ["check_q2", "check_q3"]
    assert all(item["type"] == "notebook_cell" for item in notebook_plan["items"])
    assert all(item["runner"] == "NotebookGrader" for item in notebook_plan["items"])
    assert all(item["evidenceStatus"] == "STATIC_NOTEBOOK_EVIDENCE_COLLECTED" for item in notebook_plan["items"])
    assert all(item["sandboxRequiredBeforeRealExecution"] is True for item in notebook_plan["items"])
    assert notebook_plan["safety"]["notebookKernelStarted"] is False
    assert notebook_plan["safety"]["notebookExecuted"] is False
    assert notebook_plan["safety"]["contestantCodeExecuted"] is False
    assert notebook_plan["safety"]["autoApproveAllowed"] is False


def test_review_task_summary_binds_real_demo_queue_to_latest_real_output_tasks(tmp_path):
    store_path = tmp_path / "store.json"
    store = JsonTaskStore(store_path)
    lab_task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Real LLM Lab",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/real-llm-lab.json",
    )
    exam_task = create_waiting_review_task(
        task_type="EXAM_GENERATION",
        title="Real LLM Exam",
        input_type="lab-dsl",
        input_ref="examples/output/real-llm-lab.json",
        final_result_path=str((mock_api.ROOT / "examples/output/real-llm-exam.json").resolve()),
    )
    store.save(lab_task)
    store.save(exam_task)

    payload = handle_request("GET", "/api/review-task-summary?detailMode=light", store_path=store_path)

    assert_api_envelope(payload)
    real_demo_queue = payload["data"]["reviewTaskSummary"]["realDemoReviewQueue"]
    assert real_demo_queue["source"] == "reviewTaskSummary.realDemoReviewQueue + local examples/output real LLM artifacts"
    assert real_demo_queue["dynamicTaskTotal"] == 2
    items_by_kind = {item["artifactKind"]: item for item in real_demo_queue["items"]}
    assert items_by_kind["LAB_DSL"]["taskId"] == lab_task.id
    assert items_by_kind["LAB_DSL"]["dynamicTaskId"] == lab_task.id
    assert items_by_kind["LAB_DSL"]["fallbackTaskId"] == "real_demo_lab"
    assert items_by_kind["LAB_DSL"]["dynamicTaskAvailable"] is True
    assert items_by_kind["EXAM_DSL"]["taskId"] == exam_task.id
    assert items_by_kind["EXAM_DSL"]["dynamicTaskAvailable"] is True
    assert items_by_kind["GRADING_DSL"]["taskId"] == "real_demo_grading"
    assert items_by_kind["GRADING_DSL"]["dynamicTaskAvailable"] is False
    assert real_demo_queue["autoApproveAllowed"] is False
    assert real_demo_queue["realPublishAllowed"] is False


def test_review_center_maps_agent_report_batch_to_queue_and_synthetic_detail(tmp_path):
    store_path = tmp_path / "store.json"
    lab_path = tmp_path / "batch-lab.json"
    exam_path = tmp_path / "batch-exam.json"
    grading_path = tmp_path / "batch-grading.json"
    ppt_path = tmp_path / "batch-ppt.json"
    report_path = tmp_path / "batch-workflow-report.json"
    lab_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "kind": "Lab",
                "status": "WAITING_REVIEW",
                "metadata": {"id": "lab_batch", "title": "批次实验"},
                "spec": {
                    "objectives": ["理解批次映射"],
                    "targetUsers": ["teacher"],
                    "environment": {"type": "python", "image": "python:3.11", "resources": {"cpu": "1", "memoryGb": 2}},
                    "materials": [{"type": "markdown", "path": "examples/input/demo-source.md"}],
                    "steps": [
                        {"id": "s1", "title": "读取数据", "instruction": "读取 CSV", "expectedResult": "数据加载成功"}
                    ],
                    "grading": {"ref": "grading_batch"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    exam_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "kind": "Exam",
                "status": "WAITING_REVIEW",
                "metadata": {
                    "id": "exam_batch",
                    "title": "批次试题",
                    "sourceLabId": "lab_batch",
                    "difficulty": "beginner",
                },
                "spec": {
                    "questionType": "coding_task",
                    "totalScore": 100,
                    "questions": [
                        {
                            "id": "q1",
                            "title": "补全清洗逻辑",
                            "stem": "请补全缺失值清洗逻辑",
                            "answer": "df.dropna()",
                            "gradingRef": "check_clean",
                            "score": 100,
                        }
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    grading_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "kind": "Grading",
                "status": "WAITING_REVIEW",
                "metadata": {"id": "grading_batch", "title": "批次评分"},
                "spec": {
                    "totalScore": 100,
                    "timeoutSeconds": 30,
                    "checks": [{"id": "check_clean", "type": "file_exists", "path": "result.csv", "score": 100}],
                    "assessmentPlan": [
                        {
                            "checkId": "check_clean",
                            "inputSummary": "检查结果文件",
                            "executionPlan": {"strategy": "readonly_review"},
                            "requiredLimits": {"cpu": "1", "timeout": "30s"},
                            "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
                        }
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    ppt_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "kind": "PPT",
                "status": "WAITING_REVIEW",
                "metadata": {"id": "ppt_batch", "title": "批次课件", "audience": "teacher", "durationMinutes": 20},
                "spec": {
                    "theme": {"style": "clean", "language": "zh-CN"},
                    "slides": [
                        {"id": "slide_1", "type": "title", "title": "批次课件"},
                        {"id": "slide_2", "type": "content", "title": "学习目标", "bullets": ["理解映射"]},
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    report = {
        "id": "phase2_report_batch_test",
        "workflowId": "phase2_content_generation",
        "mode": "REAL_LLM_WORKFLOW",
        "providerMode": "real-llm",
        "input": "examples/input/demo-source.md",
        "reviewer": "teacher_1",
        "traceId": "trace_batch_test",
        "contentQualitySummary": {
            "available": True,
            "status": "READY_FOR_MANUAL_REVIEW",
            "issueTotal": 0,
            "blockingIssueTotal": 0,
            "items": {
                "exam": {"kind": "exam", "readyForImportPreview": True, "issueTotal": 0, "blockingIssueTotal": 0}
            },
        },
        "steps": [
            {"name": "generate_lab_dsl", "kind": "lab", "status": "COMPLETED", "taskId": "task_batch_lab"},
            {"name": "generate_exam_dsl", "kind": "exam", "status": "COMPLETED", "taskId": "task_batch_exam"},
            {"name": "generate_grading_dsl", "kind": "grading", "status": "COMPLETED", "taskId": "task_batch_grading"},
            {"name": "generate_ppt_dsl", "kind": "ppt", "status": "COMPLETED", "taskId": "task_batch_ppt"},
        ],
        "generatedDsl": {
            "lab": {
                "taskId": "task_batch_lab",
                "dslId": "lab_batch",
                "dslPath": str(lab_path),
                "status": "WAITING_REVIEW",
                "schemaValidated": True,
                "promptId": "lab_generation_v0",
                "provider": {"adapterId": "openai_responses_sdk_adapter", "model": "deepseek-v4-flash"},
            },
            "exam": {
                "taskId": "task_batch_exam",
                "dslId": "exam_batch",
                "dslPath": str(exam_path),
                "status": "WAITING_REVIEW",
                "schemaValidated": True,
                "promptId": "exam_generation_v0",
                "provider": {"adapterId": "openai_responses_sdk_adapter", "model": "deepseek-v4-flash"},
            },
            "grading": {
                "taskId": "task_batch_grading",
                "dslId": "grading_batch",
                "dslPath": str(grading_path),
                "status": "WAITING_REVIEW",
                "schemaValidated": True,
                "promptId": "grading_generation_v0",
                "provider": {"adapterId": "openai_responses_sdk_adapter", "model": "deepseek-v4-flash"},
            },
            "ppt": {
                "taskId": "task_batch_ppt",
                "dslId": "ppt_batch",
                "dslPath": str(ppt_path),
                "status": "WAITING_REVIEW",
                "schemaValidated": True,
                "promptId": "ppt_generation_v0",
                "provider": {"adapterId": "openai_responses_sdk_adapter", "model": "deepseek-v4-flash"},
            },
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    summary_payload = handle_request(
        "GET",
        "/api/review-task-summary?" + urlencode({"detailMode": "light", "agentReport": str(report_path)}),
        store_path=store_path,
    )

    assert_api_envelope(summary_payload)
    queue = summary_payload["data"]["reviewTaskSummary"]["realDemoReviewQueue"]
    assert queue["sourceMode"] == "AGENT_REPORT_REAL_LLM_ARTIFACTS"
    assert queue["agentReport"]["agentReportLoadStatus"] == "LOADED"
    assert queue["dynamicTaskTotal"] == 4
    assert queue["syntheticTaskTotal"] == 4
    items_by_kind = {item["artifactKind"]: item for item in queue["items"]}
    assert items_by_kind["EXAM_DSL"]["taskId"] == "task_batch_exam"
    assert items_by_kind["EXAM_DSL"]["dynamicTaskAvailable"] is True
    assert items_by_kind["EXAM_DSL"]["syntheticTaskAvailable"] is True
    assert items_by_kind["EXAM_DSL"]["agentReportPath"] == str(report_path)

    JsonTaskStore(store_path).save(
        AiTask(
            id="task_batch_exam",
            taskType="EXAM_GENERATION",
            title="Store shadow task should not override agentReport",
            inputType="lab_dsl",
            inputRef="store-shadow",
            finalResultPath=str(tmp_path / "store-shadow-exam.json"),
        )
    )

    detail_payload = handle_request(
        "GET",
        "/api/review-tasks/task_batch_exam?" + urlencode({"agentReport": str(report_path)}),
        store_path=store_path,
    )

    assert_api_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    preview = detail["reviewPage"]["dslPreview"]
    assert detail["source"] == "agentReport.generatedDsl"
    assert detail["task"]["id"] == "task_batch_exam"
    assert detail["task"]["finalResultPath"] == str(exam_path)
    assert preview["artifactKind"] == "EXAM_DSL"
    assert preview["path"] == str(exam_path)
    assert preview["contentLoaded"] is True
    assert preview["schemaValidated"] is True
    assert preview["safePreview"]["questions"][0]["answerPresent"] is True
    assert "answer" not in preview["safePreview"]["questions"][0]
    assert preview["candidateSafety"]["answerVisibleToCandidate"] is False
    assert preview["candidateSafety"]["gradingRefVisibleToCandidate"] is False
    artifact_groups = {group["kind"]: group for group in detail["reviewPage"]["artifactGroups"]}
    assert artifact_groups["EXAM_DSL"]["items"][0]["path"] == str(exam_path)
    assert artifact_groups["WORKFLOW_REPORT"]["items"][0]["path"] == str(report_path)
    assert detail["reviewPage"]["actionBar"]["mockPublish"]["enabled"] is False
    assert detail["safety"]["realPublishAllowed"] is False

    path_only_report = json.loads(json.dumps(report))
    path_only_report["id"] = "phase2_report_path_only"
    for generated_item in path_only_report["generatedDsl"].values():
        generated_item.pop("taskId", None)
    path_only_report["steps"] = [
        {key: value for key, value in step.items() if key != "taskId"}
        for step in path_only_report["steps"]
    ]
    path_only_report_path = tmp_path / "real-workflow-report-path-only.json"
    path_only_report_path.write_text(json.dumps(path_only_report, ensure_ascii=False), encoding="utf-8")

    fallback_summary_payload = handle_request(
        "GET",
        "/api/review-task-summary?"
        + urlencode({"detailMode": "light", "agentReport": str(path_only_report_path)}),
        store_path=store_path,
    )

    assert_api_envelope(fallback_summary_payload)
    fallback_queue = fallback_summary_payload["data"]["reviewTaskSummary"]["realDemoReviewQueue"]
    fallback_items_by_kind = {item["artifactKind"]: item for item in fallback_queue["items"]}
    assert fallback_queue["sourceMode"] == "AGENT_REPORT_REAL_LLM_ARTIFACTS"
    assert fallback_items_by_kind["EXAM_DSL"]["taskId"] == "real_demo_exam"
    assert fallback_items_by_kind["EXAM_DSL"]["dynamicTaskAvailable"] is True
    assert fallback_items_by_kind["EXAM_DSL"]["syntheticTaskAvailable"] is True

    fallback_detail_payload = handle_request(
        "GET",
        "/api/review-tasks/real_demo_exam?" + urlencode({"agentReport": str(path_only_report_path)}),
        store_path=store_path,
    )

    assert_api_envelope(fallback_detail_payload)
    fallback_detail = fallback_detail_payload["data"]["reviewDetail"]
    fallback_preview = fallback_detail["reviewPage"]["dslPreview"]
    fallback_artifact_groups = {
        group["kind"]: group for group in fallback_detail["reviewPage"]["artifactGroups"]
    }
    assert fallback_detail["source"] == "agentReport.generatedDsl"
    assert fallback_detail["task"]["id"] == "real_demo_exam"
    assert fallback_preview["artifactKind"] == "EXAM_DSL"
    assert fallback_preview["path"] == str(exam_path)
    assert fallback_preview["contentLoaded"] is True
    assert fallback_preview["candidateSafety"]["answerVisibleToCandidate"] is False
    assert fallback_preview["candidateSafety"]["gradingRefVisibleToCandidate"] is False
    assert fallback_artifact_groups["WORKFLOW_REPORT"]["items"][0]["path"] == str(path_only_report_path)
    assert fallback_detail["safety"]["realPublishAllowed"] is False


def test_real_dsl_review_preview_api_returns_static_review_model(tmp_path):
    payload = handle_request("GET", "/api/review/real-dsl-preview", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is True
    preview = payload["data"]["realDslReviewPreview"]
    assert preview["component"] == "RealDslReviewPreview"
    assert preview["summary"]["labStepTotal"] == len(preview["labReview"]["steps"])
    assert preview["summary"]["examQuestionTotal"] == len(preview["examReview"]["candidateQuestions"])
    assert preview["summary"]["gradingPlanTotal"] == len(preview["gradingReview"]["assessmentPlan"])
    assert preview["summary"]["pptSlideTotal"] == len(preview["pptReview"]["slides"])
    assert preview["summary"]["qualityIssueTotal"] == len(preview["reviewIssues"])
    assert preview["summary"]["revisionSuggestionTotal"] == len(preview["revisionSuggestions"])
    assert preview["qualitySignals"]["summary"]["manualReviewRequired"] is True
    assert preview["qualitySignals"]["summary"]["autoApproveAllowed"] is False
    assert preview["qualitySignals"]["summary"]["realPublishAllowed"] is False
    assert preview["revisionSuggestions"]
    assert preview["examReview"]["candidateSafety"]["answerVisibleToCandidate"] is False
    assert preview["examReview"]["candidateSafety"]["gradingRefVisibleToCandidate"] is False
    assert preview["safety"]["teacherOnlyGradingRefVisibleInReview"] is True
    assert payload["data"]["safety"]["newLlmRequestSent"] is False
    assert payload["data"]["safety"]["secretsRead"] is False
    assert payload["data"]["safety"]["networkAccess"] is False
    assert payload["data"]["safety"]["realPublishAllowed"] is False


def test_real_dsl_review_preview_api_rejects_post(tmp_path):
    payload = handle_request("POST", "/api/review/real-dsl-preview", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"
    assert payload["errors"][0]["field"] == "method"


def test_real_dsl_review_preview_api_missing_lab_returns_json(tmp_path):
    payload = handle_request(
        "GET",
        f"/api/review/real-dsl-preview?lab={tmp_path / 'missing-lab.json'}",
        store_path=tmp_path / "store.json",
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "lab"


def test_real_dsl_revision_api_creates_waiting_review_draft(tmp_path):
    output = tmp_path / "api-lab-revision.json"
    report_output = tmp_path / "api-lab-revision-report.json"

    payload = handle_request(
        "POST",
        "/api/review/real-dsl-revision",
        store_path=tmp_path / "store.json",
        body={
            "kind": "lab",
            "source": "examples/output/real-llm-lab.json",
            "reviewer": "teacher_1",
            "comment": "请补充验收说明，并保持人工审核。",
            "targetSections": ["steps"],
            "requestedChanges": ["补充验收说明"],
            "output": str(output),
            "reportOutput": str(report_output),
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is True
    assert output.exists()
    assert report_output.exists()
    draft = payload["data"]["realDslRevisionDraft"]
    assert draft["component"] == "RealDslRevisionDraft"
    assert draft["kind"] == "lab"
    assert draft["revisedStatus"] == "WAITING_REVIEW"
    assert draft["schemaValidated"] is True
    assert draft["manualReviewRequired"] is True
    assert draft["safety"]["realLlmCalled"] is False
    assert draft["safety"]["newLlmRequestSent"] is False
    assert draft["safety"]["secretsRead"] is False
    assert draft["safety"]["networkAccess"] is False
    assert draft["safety"]["realPublishAllowed"] is False


def test_real_dsl_revision_api_requires_comment(tmp_path):
    payload = handle_request(
        "POST",
        "/api/review/real-dsl-revision",
        store_path=tmp_path / "store.json",
        body={
            "kind": "lab",
            "source": "examples/output/real-llm-lab.json",
            "reviewer": "teacher_1",
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "comment"


def test_real_dsl_revision_batch_api_creates_waiting_review_drafts(tmp_path):
    report_output = tmp_path / "api-revision-batch-report.json"

    payload = handle_request(
        "POST",
        "/api/review/real-dsl-revision-batch",
        store_path=tmp_path / "store.json",
        body={
            "preview": "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "reviewer": "teacher_1",
            "outputDir": str(tmp_path),
            "reportOutput": str(report_output),
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is True
    assert report_output.exists()
    batch = payload["data"]["realDslRevisionBatch"]
    assert batch["component"] == "RealDslRevisionBatch"
    assert batch["draftTotal"] == 3
    assert batch["schemaValidatedTotal"] == 3
    assert batch["allDraftsWaitingReview"] is True
    assert batch["draftKinds"] == ["grading", "lab", "ppt"]
    assert batch["safety"]["realLlmCalled"] is False
    assert batch["safety"]["newLlmRequestSent"] is False
    assert batch["safety"]["realPublishAllowed"] is False


def test_real_dsl_revision_diff_preview_api_returns_readonly_summary(tmp_path):
    report_output = tmp_path / "api-revision-batch-report.json"
    batch_payload = handle_request(
        "POST",
        "/api/review/real-dsl-revision-batch",
        store_path=tmp_path / "store.json",
        body={
            "preview": "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "reviewer": "teacher_1",
            "outputDir": str(tmp_path),
            "reportOutput": str(report_output),
        },
    )
    assert batch_payload["success"] is True

    payload = handle_request(
        "GET",
        f"/api/review/real-dsl-revision-diff-preview?batchReport={report_output}",
        store_path=tmp_path / "store.json",
    )

    assert_api_envelope(payload)
    assert payload["success"] is True
    preview = payload["data"]["realDslRevisionDiffPreview"]
    assert preview["component"] == "RealDslRevisionDiffPreview"
    assert preview["summary"]["draftTotal"] == 3
    assert preview["summary"]["allDraftsWaitingReview"] is True
    assert preview["safety"]["realLlmCalled"] is False
    assert preview["safety"]["newLlmRequestSent"] is False
    assert preview["safety"]["realPublishAllowed"] is False


def test_real_dsl_revision_decision_api_records_manual_decision(tmp_path):
    report_output = tmp_path / "api-revision-batch-report.json"
    diff_output = tmp_path / "api-revision-diff-preview.json"
    decision_output = tmp_path / "api-revision-decision.json"
    batch_payload = handle_request(
        "POST",
        "/api/review/real-dsl-revision-batch",
        store_path=tmp_path / "store.json",
        body={
            "preview": "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "reviewer": "teacher_1",
            "outputDir": str(tmp_path),
            "reportOutput": str(report_output),
        },
    )
    assert batch_payload["success"] is True
    diff_payload = handle_request(
        "GET",
        f"/api/review/real-dsl-revision-diff-preview?batchReport={report_output}&output={diff_output}",
        store_path=tmp_path / "store.json",
    )
    assert diff_payload["success"] is True

    payload = handle_request(
        "POST",
        "/api/review/real-dsl-revision-decision",
        store_path=tmp_path / "store.json",
        body={
            "diffPreview": str(diff_output),
            "suggestionId": "revise_lab_objective_depth",
            "reviewer": "teacher_1",
            "decision": "approve",
            "reason": "人工确认该修订可进入后续手动合并。",
            "output": str(decision_output),
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is True
    assert decision_output.exists()
    decision = payload["data"]["realDslRevisionDecision"]
    assert decision["component"] == "RealDslRevisionDecision"
    assert decision["decision"] == "approve"
    assert decision["decisionStatus"] == "REVISION_APPROVED_FOR_MANUAL_MERGE"
    assert decision["safety"]["newLlmRequestSent"] is False
    assert decision["safety"]["sourceDslModified"] is False
    assert decision["safety"]["realPublishAllowed"] is False


def test_real_dsl_revision_promote_api_creates_waiting_review_candidate(tmp_path):
    report_output = tmp_path / "api-revision-batch-report.json"
    diff_output = tmp_path / "api-revision-diff-preview.json"
    decision_output = tmp_path / "api-revision-decision.json"
    promoted_output = tmp_path / "api-revision-promoted.json"
    promotion_report = tmp_path / "api-revision-promotion-report.json"
    batch_payload = handle_request(
        "POST",
        "/api/review/real-dsl-revision-batch",
        store_path=tmp_path / "store.json",
        body={
            "preview": "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "reviewer": "teacher_1",
            "outputDir": str(tmp_path),
            "reportOutput": str(report_output),
        },
    )
    assert batch_payload["success"] is True
    diff_payload = handle_request(
        "GET",
        f"/api/review/real-dsl-revision-diff-preview?batchReport={report_output}&output={diff_output}",
        store_path=tmp_path / "store.json",
    )
    assert diff_payload["success"] is True
    decision_payload = handle_request(
        "POST",
        "/api/review/real-dsl-revision-decision",
        store_path=tmp_path / "store.json",
        body={
            "diffPreview": str(diff_output),
            "suggestionId": "revise_lab_objective_depth",
            "reviewer": "teacher_1",
            "decision": "approve",
            "output": str(decision_output),
        },
    )
    assert decision_payload["success"] is True

    payload = handle_request(
        "POST",
        "/api/review/real-dsl-revision-promote",
        store_path=tmp_path / "store.json",
        body={
            "decisionReport": str(decision_output),
            "reviewer": "teacher_2",
            "output": str(promoted_output),
            "reportOutput": str(promotion_report),
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is True
    assert promoted_output.exists()
    assert promotion_report.exists()
    promotion = payload["data"]["realDslRevisionPromotion"]
    assert promotion["component"] == "RealDslRevisionPromotion"
    assert promotion["promotedStatus"] == "WAITING_REVIEW"
    assert promotion["schemaValidated"] is True
    assert promotion["safety"]["sourceDslModified"] is False
    assert promotion["safety"]["revisedDslModified"] is False
    assert promotion["safety"]["newLlmRequestSent"] is False
    assert promotion["safety"]["realPublishAllowed"] is False


def test_real_dsl_revision_enqueue_api_adds_candidate_to_review_queue(tmp_path):
    store_path = tmp_path / "store.json"
    report_output = tmp_path / "api-revision-batch-report.json"
    diff_output = tmp_path / "api-revision-diff-preview.json"
    decision_output = tmp_path / "api-revision-decision.json"
    promoted_output = tmp_path / "api-revision-promoted.json"
    promotion_report = tmp_path / "api-revision-promotion-report.json"
    assert handle_request(
        "POST",
        "/api/review/real-dsl-revision-batch",
        store_path=store_path,
        body={
            "preview": "examples/output/real-llm-demo-real-dsl-review-preview.json",
            "reviewer": "teacher_1",
            "outputDir": str(tmp_path),
            "reportOutput": str(report_output),
        },
    )["success"] is True
    assert handle_request(
        "GET",
        f"/api/review/real-dsl-revision-diff-preview?batchReport={report_output}&output={diff_output}",
        store_path=store_path,
    )["success"] is True
    assert handle_request(
        "POST",
        "/api/review/real-dsl-revision-decision",
        store_path=store_path,
        body={
            "diffPreview": str(diff_output),
            "suggestionId": "revise_lab_objective_depth",
            "reviewer": "teacher_1",
            "decision": "approve",
            "output": str(decision_output),
        },
    )["success"] is True
    assert handle_request(
        "POST",
        "/api/review/real-dsl-revision-promote",
        store_path=store_path,
        body={
            "decisionReport": str(decision_output),
            "reviewer": "teacher_2",
            "output": str(promoted_output),
            "reportOutput": str(promotion_report),
        },
    )["success"] is True

    payload = handle_request(
        "POST",
        "/api/review/real-dsl-revision-enqueue",
        store_path=store_path,
        body={"promotionReport": str(promotion_report), "reviewer": "teacher_3"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is True
    queue_item = payload["data"]["promotionReviewQueueItem"]
    assert queue_item["taskStatus"] == "WAITING_REVIEW"
    assert queue_item["artifactKind"] == "LAB_DSL"
    assert queue_item["safety"]["realPublishAllowed"] is False
    listed = handle_request("GET", "/api/ai-tasks?status=WAITING_REVIEW&taskType=LAB_GENERATION_REVISION", store_path=store_path)
    assert any(task["id"] == queue_item["taskId"] for task in listed["data"]["items"])
    detail = handle_request("GET", f"/api/review-tasks/{queue_item['taskId']}", store_path=store_path)
    assert detail["success"] is True
    assert detail["data"]["reviewDetail"]["reviewPage"]["dslPreview"]["artifactKind"] == "LAB_DSL"
    assert detail["data"]["reviewDetail"]["reviewPage"]["actionBar"]["approve"]["enabled"] is True
    assert detail["data"]["reviewDetail"]["promotionReviewDisposition"]["state"] == "WAITING_HUMAN_REVIEW"

    rejected = handle_request(
        "POST",
        f"/api/ai-tasks/{queue_item['taskId']}/reject",
        store_path=store_path,
        body={"reviewer": "teacher_4", "reason": "候选版目标仍不够可验收。"},
    )
    rejected_detail = handle_request("GET", f"/api/review-tasks/{queue_item['taskId']}", store_path=store_path)

    assert_api_envelope(rejected)
    assert rejected["data"]["task"]["status"] == "REJECTED"
    disposition = rejected_detail["data"]["reviewDetail"]["promotionReviewDisposition"]
    assert disposition["state"] == "REJECTED_CLOSED"
    assert disposition["reviewCompleted"] is True
    assert disposition["mockPublishAvailable"] is False
    assert disposition["realPublishAllowed"] is False
    assert rejected_detail["data"]["reviewDetail"]["reviewPage"]["promotionReviewDisposition"]["nextRequiredAction"] == "revise_again_or_stop"


def test_lab_template_import_preview_api_requires_approved_lab_task(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]

    blocked = handle_request(
        "POST",
        "/api/labs/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "blocked-preview.json")},
    )
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    payload = handle_request(
        "POST",
        "/api/labs/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "lab-template-import-preview.json")},
    )

    assert_api_envelope(blocked)
    assert blocked["success"] is False
    assert blocked["code"] == "STATE_TRANSITION_ERROR"
    assert approved["data"]["task"]["status"] == "APPROVED"
    assert_api_envelope(payload)
    preview = payload["data"]["labTemplateImportPreview"]
    assert preview["component"] == "LabTemplateImportPreview"
    assert preview["sourceTaskStatus"] == "APPROVED"
    assert preview["agentEntity"] == "lab_template"
    assert preview["labTemplateDraft"]["status"] == "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW"
    assert preview["importPlan"]["realAgentImport"] is False
    assert preview["safety"]["databaseWritten"] is False
    assert preview["safety"]["realPublishAllowed"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "LAB_TEMPLATE_IMPORT_PREVIEW"

    detail_payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)
    assert_api_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    import_summary = detail["platformImportPreview"]
    assert import_summary["visible"] is True
    assert import_summary["total"] == 1
    assert import_summary["items"][0]["component"] == "LabTemplateImportPreview"
    assert import_summary["items"][0]["agentEntity"] == "lab_template"
    assert import_summary["items"][0]["draftStatus"] == "DRAFT_PENDING_PLATFORM_IMPORT_REVIEW"
    assert detail["reviewPage"]["platformImportPreview"] == import_summary
    assert detail["summary"]["platformImportPreviewTotal"] == 1
    action_panel = detail["platformImportPreviewActions"]
    assert action_panel["visible"] is True
    assert action_panel["enabledTotal"] == 1
    assert action_panel["previewAlreadyCreatedTotal"] == 1
    assert action_panel["items"][0]["component"] == "LabTemplateImportPreviewAction"
    assert action_panel["items"][0]["previewAlreadyCreated"] is True
    assert action_panel["items"][0]["apiEndpoint"] == "POST /api/labs/import-preview"
    assert detail["reviewPage"]["platformImportPreviewActions"] == action_panel
    signoff = detail["platformImportPreviewSignoff"]
    assert signoff["component"] == "AgentImportPreviewSignoffChecklist"
    assert signoff["visible"] is True
    assert signoff["readyForHumanSignoff"] is True
    assert signoff["total"] == 1
    assert signoff["blockedTotal"] == 0
    assert signoff["items"][0]["component"] == "LabTemplateImportPreviewSignoff"
    assert signoff["items"][0]["agentEntity"] == "lab_template"
    assert detail["reviewPage"]["platformImportPreviewSignoff"] == signoff
    assert detail["summary"]["platformImportPreviewSignoffTotal"] == 1


def test_exam_and_grading_import_preview_api_require_approved_tasks(tmp_path):
    store_path = tmp_path / "store.json"
    report = handle_request(
        "POST",
        "/api/phase2/workflows/exam-conversion/run",
        store_path=store_path,
        body={
            "lab": "templates/lab/examples/basic-lab.yaml",
            "notebook": "examples/notebooks/demo-lab.ipynb",
            "reviewer": "teacher_1",
        },
    )
    created_tasks = {task["taskType"]: task["id"] for task in report["data"]["createdTasks"]}
    exam_task_id = created_tasks["EXAM_GENERATION"]
    grading_task_id = created_tasks["GRADING_GENERATION"]

    blocked = handle_request(
        "POST",
        "/api/exams/import-preview",
        store_path=store_path,
        body={"taskId": exam_task_id, "reviewer": "teacher_2", "output": str(tmp_path / "blocked-exam.json")},
    )
    handle_request("POST", f"/api/ai-tasks/{exam_task_id}/approve", store_path=store_path, body={"reviewer": "teacher_2"})
    handle_request(
        "POST",
        f"/api/ai-tasks/{grading_task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_2"},
    )
    exam_payload = handle_request(
        "POST",
        "/api/exams/import-preview",
        store_path=store_path,
        body={"taskId": exam_task_id, "reviewer": "teacher_2", "output": str(tmp_path / "exam-preview.json")},
    )
    grading_payload = handle_request(
        "POST",
        "/api/grading/import-preview",
        store_path=store_path,
        body={"taskId": grading_task_id, "reviewer": "teacher_2", "output": str(tmp_path / "grading-preview.json")},
    )

    assert blocked["success"] is False
    assert blocked["code"] == "STATE_TRANSITION_ERROR"
    assert_api_envelope(exam_payload)
    assert_api_envelope(grading_payload)
    assert exam_payload["data"]["examQuestionImportPreview"]["component"] == "ExamQuestionImportPreview"
    assert exam_payload["data"]["examQuestionImportPreview"]["agentEntity"] == "exam_question"
    assert exam_payload["data"]["examQuestionImportPreview"]["safety"]["databaseWritten"] is False
    assert exam_payload["data"]["examQuestionImportPreview"]["safety"]["realPublishAllowed"] is False
    assert grading_payload["data"]["gradingRuleImportPreview"]["component"] == "GradingRuleImportPreview"
    assert grading_payload["data"]["gradingRuleImportPreview"]["agentEntity"] == "grading_rule"
    controlled_next_action = grading_payload["data"]["gradingRuleImportPreview"]["controlledEvidenceNextAction"]
    assert controlled_next_action["apiEndpoint"] == "POST /api/grading/evidence-auto"
    assert "grade evidence-auto" in controlled_next_action["cliCommand"]
    assert "--include-controlled-command" in controlled_next_action["cliCommand"]
    assert controlled_next_action["safety"]["sandboxExecutedByPreview"] is False
    assert grading_payload["data"]["gradingRuleImportPreview"]["safety"]["databaseWritten"] is False
    assert grading_payload["data"]["gradingRuleImportPreview"]["safety"]["realPublishAllowed"] is False
    detail_payload = handle_request("GET", f"/api/review-tasks/{grading_task_id}", store_path=store_path)
    detail = detail_payload["data"]["reviewDetail"]
    import_summary = detail["platformImportPreview"]
    assert import_summary["controlledEvidenceNextActionTotal"] == 1
    grading_preview_item = next(item for item in import_summary["items"] if item["agentEntity"] == "grading_rule")
    assert grading_preview_item["controlledEvidenceNextAction"]["apiEndpoint"] == "POST /api/grading/evidence-auto"
    signoff = detail["platformImportPreviewSignoff"]
    grading_signoff = next(item for item in signoff["items"] if item["agentEntity"] == "grading_rule")
    assert grading_signoff["controlledEvidenceNextAction"]["nextRequiredAction"] == (
        "run_grading_evidence_auto_before_final_grading_rule_import_review"
    )


def test_lab_template_mock_import_api_creates_agent_entity(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{task_id}/approve", store_path=store_path, body={"reviewer": "teacher_1"})

    blocked = handle_request(
        "POST",
        "/api/labs/mock-import",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "blocked.json")},
    )
    handle_request(
        "POST",
        "/api/labs/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "preview.json")},
    )
    payload = handle_request(
        "POST",
        "/api/labs/mock-import",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "mock-import.json")},
    )

    assert blocked["success"] is False
    assert blocked["code"] == "VALIDATION_ERROR"
    assert blocked["errors"][0]["field"] == "platformImportPreview"
    assert_api_envelope(payload)
    entity = payload["data"]["agentEntityRecord"]
    assert entity["entityType"] == "lab_template"
    assert entity["mockStoreWritten"] is True
    assert entity["databaseWritten"] is False
    assert payload["data"]["agentEntityMockImport"]["safety"]["realAgentImport"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "LAB_TEMPLATE_MOCK_IMPORT"

    listed = handle_request("GET", f"/api/platform-entities?sourceTaskId={task_id}", store_path=store_path)
    fetched = handle_request("GET", f"/api/platform-entities/{entity['id']}", store_path=store_path)
    detail_payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)

    assert listed["data"]["total"] == 1
    assert fetched["data"]["agentEntityRecord"]["id"] == entity["id"]
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["agentEntityMockImport"]["visible"] is True
    assert detail["agentEntityMockImport"]["total"] == 1
    assert detail["summary"]["agentEntityMockImportTotal"] == 1


def test_agent_entity_import_dry_run_api_builds_payload_without_sending(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{task_id}/approve", store_path=store_path, body={"reviewer": "teacher_1"})
    handle_request(
        "POST",
        "/api/labs/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "preview.json")},
    )
    imported = handle_request(
        "POST",
        "/api/labs/mock-import",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "mock-import.json")},
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]
    output = tmp_path / "platform-import-dry-run.json"

    payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/import-dry-run",
        store_path=store_path,
        body={"reviewer": "teacher_2", "output": str(output)},
    )

    assert_api_envelope(payload)
    assert output.exists()
    dry_run = payload["data"]["agentEntityImportDryRun"]
    assert dry_run["component"] == "AgentEntityImportDryRun"
    assert dry_run["mode"] == "REAL_PLATFORM_IMPORT_DRY_RUN_ONLY"
    assert dry_run["agentEntityId"] == entity_id
    assert dry_run["targetEndpoint"]["method"] == "POST"
    assert dry_run["requestPreview"]["entityType"] == "lab_template"
    assert dry_run["requestPreview"]["payload"]["reviewStatus"] == "PENDING_MANUAL_PLATFORM_REVIEW"
    assert dry_run["validation"]["readyForRealApiImplementation"] is True
    assert dry_run["validation"]["readyForRealApiCall"] is False
    assert dry_run["safety"]["requestSent"] is False
    assert dry_run["safety"]["databaseWritten"] is False
    assert dry_run["safety"]["realAgentImport"] is False
    assert payload["data"]["artifact"]["mode"] == "REAL_PLATFORM_IMPORT_DRY_RUN_ONLY"
    assert payload["data"]["operationAuditEvent"]["action"] == "PLATFORM_ENTITY_IMPORT_DRY_RUN"


def test_agent_entity_contract_validate_api_reports_local_contract_summary(tmp_path):
    store_path = tmp_path / "store.json"
    contract_config = tmp_path / "platform-contract.json"
    contract_config.write_text(
        json.dumps(
            {
                "ignoredNote": "for local docs only",
                "entities": {
                    "lab_template": {
                        "draftImportPath": "/open/lab-imports",
                        "requestBodyMapping": {
                            "lab.title": {"source": "payload.title", "required": True},
                            "workflow.idempotencyKey": "idempotencyKey",
                        },
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    payload = handle_request(
        "POST",
        "/api/platform-entities/contract-validate",
        store_path=store_path,
        body={"contractConfig": str(contract_config), "entityType": "lab_template"},
    )

    assert_api_envelope(payload)
    data = payload["data"]
    validation = data["platformApiContractValidation"]
    assert data["mode"] == "LOCAL_PLATFORM_API_CONTRACT_VALIDATION"
    assert data["requestSent"] is False
    assert data["networkAccess"] is False
    assert data["secretsRead"] is False
    assert validation["valid"] is True
    assert validation["checkedEntityTypes"] == ["lab_template"]
    assert validation["summary"]["requestBodyMappingConfiguredEntityTotal"] == 1
    assert validation["summary"]["warningTotal"] == 1
    assert validation["unknownTopLevelKeys"] == ["ignoredNote"]
    assert validation["entities"]["lab_template"]["draftImportEndpoint"] == {
        "method": "POST",
        "path": "/open/lab-imports",
    }
    assert validation["safety"]["requestSent"] is False
    assert validation["safety"]["secretsRead"] is False


def test_agent_entity_contract_validate_api_accepts_example_contract_config(tmp_path):
    store_path = tmp_path / "store.json"

    payload = handle_request(
        "POST",
        "/api/platform-entities/contract-validate",
        store_path=store_path,
        body={"contractConfig": "examples/input/platform-contract.json"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is True
    data = payload["data"]
    validation = data["platformApiContractValidation"]
    assert data["mode"] == "LOCAL_PLATFORM_API_CONTRACT_VALIDATION"
    assert data["contractConfigPath"].endswith("examples\\input\\platform-contract.json") or data[
        "contractConfigPath"
    ].endswith("examples/input/platform-contract.json")
    assert validation["checkedEntityTypes"] == ["lab_template", "exam_question", "grading_rule", "ppt_deck"]
    assert validation["summary"]["requestBodyMappingConfiguredEntityTotal"] == 4
    assert validation["summary"]["defaultInternalDtoEntityTotal"] == 0
    assert validation["summary"]["warningTotal"] == 0
    assert validation["entities"]["grading_rule"]["draftImportEndpoint"]["path"] == (
        "/open/staging/grading-rule-draft-imports"
    )
    assert validation["safety"]["requestSent"] is False
    assert validation["safety"]["networkAccess"] is False
    assert validation["safety"]["secretsRead"] is False


def test_agent_entity_contract_validate_api_rejects_invalid_entity_type(tmp_path):
    store_path = tmp_path / "store.json"
    contract_config = tmp_path / "platform-contract.json"
    contract_config.write_text('{"entities":{}}', encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/platform-entities/contract-validate",
        store_path=store_path,
        body={"contractConfig": str(contract_config), "entityType": "bad_entity"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"] == [{"field": "entityType", "reason": "非法实体类型"}]


def test_agent_entity_contract_validate_api_rejects_bad_contract_config(tmp_path):
    store_path = tmp_path / "store.json"
    contract_config = tmp_path / "bad-platform-contract.json"
    contract_config.write_text('{"entities":{"bad_entity":{}}}', encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/platform-entities/contract-validate",
        store_path=store_path,
        body={"contractConfig": str(contract_config)},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"] == [{"field": "entities.bad_entity", "reason": "unsupported entity type override"}]


def test_agent_entity_import_dry_run_api_reads_backend_core_entity(tmp_path):
    store_path = tmp_path / "store.json"
    core_db_path = tmp_path / "backend-core-platform-dry-run.sqlite3"
    source_store = JsonTaskStore(tmp_path / "source-store.json")
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Backend Core platform dry-run task",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/real-llm-lab.json",
        trace_id="trace_backend_core_platform_dry_run",
    )
    artifact = create_artifact_record(
        kind=ArtifactKind.LAB_DSL,
        path="examples/output/real-llm-lab.json",
        title="Backend Core platform dry-run lab DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        task_id=task.id,
        trace_id=task.traceId,
    )
    entity = create_agent_entity_record(
        entity_type=AgentEntityType.LAB_TEMPLATE,
        title="Backend Core platform dry-run entity",
        payload={"title": "Backend Core platform dry-run entity", "durationMinutes": 45},
        source_task_id=task.id,
        source_preview_artifact_id=artifact.id,
        source_preview_path="examples/output/lab-template-import-preview.json",
        reviewer="teacher_1",
        trace_id=task.traceId,
        source_dsl_path="examples/output/real-llm-lab.json",
        source_artifact_id=artifact.id,
        source_artifact_kind="LAB_DSL",
    )
    source_store.save(task)
    source_store.save_artifact(artifact)
    source_store.save_agent_entity(entity)
    init_payload = handle_request(
        "POST",
        "/api/backend/core-db/init",
        store_path=source_store.path,
        body={"coreDbPath": str(core_db_path), "actor": "teacher_1"},
    )
    sync_payload = handle_request(
        "POST",
        "/api/backend/core-db/sync-local",
        store_path=source_store.path,
        body={"coreDbPath": str(core_db_path), "actor": "teacher_1"},
    )
    output = tmp_path / "backend-core-platform-dry-run.json"

    payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity.id}/import-dry-run",
        store_path=store_path,
        body={"reviewer": "teacher_2", "output": str(output), "coreDbPath": str(core_db_path)},
    )
    artifact_query = urlencode({"coreDbPath": str(core_db_path), "taskId": task.id})
    audit_query = urlencode(
        {
            "coreDbPath": str(core_db_path),
            "resourceType": "PLATFORM_ENTITY",
            "resourceId": entity.id,
            "action": "PLATFORM_ENTITY_IMPORT_DRY_RUN",
        }
    )
    artifact_payload = handle_request("GET", f"/api/artifacts?{artifact_query}", store_path=store_path)
    audit_payload = handle_request("GET", f"/api/audit-events?{audit_query}", store_path=store_path)
    mock_store_list = handle_request("GET", "/api/platform-entities", store_path=store_path)

    assert_api_envelope(init_payload)
    assert_api_envelope(sync_payload)
    assert_api_envelope(payload)
    assert output.exists()
    dry_run = payload["data"]["agentEntityImportDryRun"]
    backend_core = payload["data"]["backendCoreAgentEntityImportDryRun"]
    assert dry_run["agentEntityId"] == entity.id
    assert dry_run["requestPreview"]["entityType"] == "lab_template"
    assert dry_run["safety"]["requestSent"] is False
    assert backend_core["repositoryContractUsed"] is True
    assert backend_core["agentEntityRead"] is True
    assert backend_core["jsonStoreSourceRead"] is False
    assert backend_core["artifactWritten"] is True
    assert backend_core["operationAuditEventWritten"] is True
    assert backend_core["localSqliteWritten"] is True
    assert_api_envelope(artifact_payload)
    assert any(item["id"] == payload["data"]["artifact"]["id"] for item in artifact_payload["data"]["items"])
    assert_api_envelope(audit_payload)
    assert any(item["id"] == payload["data"]["operationAuditEvent"]["id"] for item in audit_payload["data"]["items"])
    assert_api_envelope(mock_store_list)
    assert mock_store_list["data"]["total"] == 0


def test_agent_entity_import_result_api_reads_backend_core_entity(tmp_path):
    store_path = tmp_path / "store.json"
    core_db_path = tmp_path / "backend-core-platform-result.sqlite3"
    source_store = JsonTaskStore(tmp_path / "source-store.json")
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Backend Core platform result task",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/real-llm-lab.json",
        trace_id="trace_backend_core_platform_result",
    )
    artifact = create_artifact_record(
        kind=ArtifactKind.LAB_DSL,
        path="examples/output/real-llm-lab.json",
        title="Backend Core platform result lab DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        task_id=task.id,
        trace_id=task.traceId,
    )
    preview_artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path="examples/output/lab-template-import-preview.json",
        title="Backend Core platform result preview",
        status=ArtifactStatus.COMPLETED,
        task_id=task.id,
        trace_id=task.traceId,
        metadata={
            "component": "LabTemplateImportPreview",
            "agentEntity": "lab_template",
        },
        mode="LOCAL_PLATFORM_IMPORT_PREVIEW",
    )
    entity = create_agent_entity_record(
        entity_type=AgentEntityType.LAB_TEMPLATE,
        title="Backend Core platform result entity",
        payload={"title": "Backend Core platform result entity", "durationMinutes": 45},
        source_task_id=task.id,
        source_preview_artifact_id=artifact.id,
        source_preview_path="examples/output/lab-template-import-preview.json",
        reviewer="teacher_1",
        trace_id=task.traceId,
        source_dsl_path="examples/output/real-llm-lab.json",
        source_artifact_id=artifact.id,
        source_artifact_kind="LAB_DSL",
    )
    mock_import_artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path="examples/output/lab-template-mock-import.json",
        title="Backend Core platform result mock import",
        status=ArtifactStatus.COMPLETED,
        task_id=task.id,
        trace_id=task.traceId,
        metadata={
            "component": "LabTemplateMockImport",
            "agentEntity": "lab_template",
            "agentEntityId": entity.id,
            "entityType": "lab_template",
        },
        mode="LOCAL_PLATFORM_ENTITY_MOCK_IMPORT",
    )
    source_store.save(task)
    source_store.save_artifact(artifact)
    source_store.save_artifact(preview_artifact)
    source_store.save_artifact(mock_import_artifact)
    source_store.save_agent_entity(entity)
    init_payload = handle_request(
        "POST",
        "/api/backend/core-db/init",
        store_path=source_store.path,
        body={"coreDbPath": str(core_db_path), "actor": "teacher_1"},
    )
    sync_payload = handle_request(
        "POST",
        "/api/backend/core-db/sync-local",
        store_path=source_store.path,
        body={"coreDbPath": str(core_db_path), "actor": "teacher_1"},
    )
    send_report = tmp_path / "backend-core-platform-send-report.json"
    send_report.write_text(
        json.dumps(
            {
                "component": "AgentEntityImportSendResult",
                "mode": "REAL_PLATFORM_IMPORT_REQUEST_SENT",
                "agentEntityId": entity.id,
                "entityType": "lab_template",
                "response": {"ok": True, "statusCode": 202, "body": {"json": {"draftImportId": "draft_core"}}},
                "request": {"idempotencyKey": "dryrun:backend-core-result"},
                "targetEndpoint": {"method": "POST", "path": "/api/platform/lab-template/draft-imports"},
                "safety": {"requestSent": True},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "backend-core-platform-result-record.json"
    dry_run_output = tmp_path / "backend-core-platform-result-dry-run.json"

    dry_run_payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity.id}/import-dry-run",
        store_path=store_path,
        body={"reviewer": "teacher_2", "output": str(dry_run_output), "coreDbPath": str(core_db_path)},
    )

    payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity.id}/import-result",
        store_path=store_path,
        body={
            "reviewer": "teacher_3",
            "sendResult": str(send_report),
            "agentStatus": "ACCEPTED_FOR_DRAFT",
            "output": str(output),
            "coreDbPath": str(core_db_path),
        },
    )
    core_query = urlencode({"coreDbPath": str(core_db_path)})
    artifact_query = urlencode({"coreDbPath": str(core_db_path), "taskId": task.id})
    audit_query = urlencode(
        {
            "coreDbPath": str(core_db_path),
            "resourceType": "PLATFORM_ENTITY",
            "resourceId": entity.id,
            "action": "PLATFORM_ENTITY_IMPORT_RESULT_RECORD",
        }
    )
    signoff_output = tmp_path / "backend-core-platform-signoff.json"
    final_review_output = tmp_path / "backend-core-platform-final-review.json"
    entity_payload = handle_request("GET", f"/api/platform-entities/{entity.id}?{core_query}", store_path=store_path)
    readiness_payload = handle_request(
        "GET",
        f"/api/platform-entities/readiness-report?{urlencode({'coreDbPath': str(core_db_path), 'sourceTaskId': task.id})}",
        store_path=store_path,
    )
    artifact_payload = handle_request("GET", f"/api/artifacts?{artifact_query}", store_path=store_path)
    audit_payload = handle_request("GET", f"/api/audit-events?{audit_query}", store_path=store_path)
    mock_store_list = handle_request("GET", "/api/platform-entities", store_path=store_path)

    assert_api_envelope(init_payload)
    assert_api_envelope(sync_payload)
    assert_api_envelope(dry_run_payload)
    assert_api_envelope(payload)
    assert output.exists()
    result_record = payload["data"]["agentEntityImportResultRecord"]
    backend_core = payload["data"]["backendCoreAgentEntityImportResult"]
    assert result_record["agentEntityId"] == entity.id
    assert result_record["agentDraftId"] == "draft_core"
    assert result_record["agentStatus"] == "ACCEPTED_FOR_DRAFT"
    assert result_record["localEntityStatus"]["after"] == "REAL_IMPORT_DRAFT_ACCEPTED"
    assert payload["data"]["agentEntityRecord"]["status"] == "REAL_IMPORT_DRAFT_ACCEPTED"
    assert backend_core["repositoryContractUsed"] is True
    assert backend_core["agentEntityRead"] is True
    assert backend_core["agentEntityWritten"] is True
    assert backend_core["jsonStoreSourceRead"] is False
    assert backend_core["artifactWritten"] is True
    assert backend_core["operationAuditEventWritten"] is True
    assert backend_core["localSqliteWritten"] is True
    assert_api_envelope(entity_payload)
    assert entity_payload["data"]["agentEntityRecord"]["status"] == "REAL_IMPORT_DRAFT_ACCEPTED"
    assert entity_payload["data"]["agentEntityImportActivity"]["repositoryBacked"] is True
    assert entity_payload["data"]["agentEntityImportActivity"]["dryRunTotal"] == 1
    assert entity_payload["data"]["agentEntityImportActivity"]["resultTotal"] == 1
    assert entity_payload["data"]["agentEntityImportActivity"]["summary"]["resultRecorded"] is True
    assert_api_envelope(readiness_payload)
    readiness = readiness_payload["data"]["agentEntityReadinessReport"]
    readiness_core = readiness_payload["data"]["backendCoreAgentEntityReadiness"]
    readiness_item = next(item for item in readiness["items"] if item["agentEntityId"] == entity.id)
    assert readiness["mode"] == "BACKEND_CORE_PLATFORM_ENTITY_READINESS_REPORT"
    assert readiness["repositoryBacked"] is True
    assert readiness["summary"]["previewCreatedTotal"] == 1
    assert readiness["summary"]["mockImportCreatedTotal"] == 1
    assert readiness["summary"]["readyForManualAgentReviewTotal"] == 1
    assert readiness["summary"]["dryRunPreparedTotal"] == 1
    assert readiness["summary"]["resultRecordedTotal"] == 1
    assert readiness_item["repositoryBacked"] is True
    assert readiness_item["dryRunPrepared"] is True
    assert readiness_item["resultRecorded"] is True
    assert readiness_item["acceptedForDraft"] is True
    assert readiness_item["safety"]["jsonStoreSourceRead"] is False
    assert readiness_core["repositoryContractUsed"] is True
    assert readiness_core["jsonStoreSourceRead"] is False
    assert readiness_core["agentEntityRead"] is True
    assert readiness_core["operationAuditEventRead"] is True
    assert_api_envelope(artifact_payload)
    assert any(item["id"] == payload["data"]["artifact"]["id"] for item in artifact_payload["data"]["items"])
    assert_api_envelope(audit_payload)
    assert any(item["id"] == payload["data"]["operationAuditEvent"]["id"] for item in audit_payload["data"]["items"])
    assert_api_envelope(mock_store_list)
    assert mock_store_list["data"]["total"] == 0

    send_seed_payload = handle_request(
        "POST",
        "/api/backend/core-db/sync-local",
        store_path=store_path,
        body={"coreDbPath": str(core_db_path), "actor": "teacher_1"},
    )
    assert_api_envelope(send_seed_payload)
    # Seed the two platform-side observation events that would normally be
    # produced by import-send and import-status. The signoff path must still
    # require them before accepting a final local signoff.
    core_repository, _policy = mock_api.resolve_backend_core_repository({"coreDbPath": str(core_db_path)})
    send_event = mock_api.create_operation_audit_event(
        action=mock_api.OperationAction.PLATFORM_ENTITY_IMPORT_SEND,
        resource_type=mock_api.OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor="teacher_2",
        trace_id=task.traceId,
        before_state="DRAFT_CREATED",
        after_state="PUBLISH_PENDING",
        detail={
            "component": "AgentEntityImportSendResult",
            "artifactId": "artifact_backend_core_send",
            "outputPath": str(send_report),
            "targetEndpoint": {"method": "POST", "path": "/api/platform/lab-template/draft-imports"},
            "statusCode": 202,
            "agentDraftId": "draft_core",
            "requestSent": True,
            "networkAccess": True,
            "secretsRead": True,
            "realPublish": False,
        },
    )
    send_event.mode = "REAL_PLATFORM_IMPORT_REQUEST_SENT"
    status_event = mock_api.create_operation_audit_event(
        action=mock_api.OperationAction.PLATFORM_ENTITY_IMPORT_STATUS_QUERY,
        resource_type=mock_api.OperationResourceType.PLATFORM_ENTITY,
        resource_id=entity.id,
        actor="teacher_2",
        trace_id=task.traceId,
        before_state="PUBLISH_PENDING",
        after_state="ACCEPTED_FOR_DRAFT",
        detail={
            "component": "AgentEntityImportStatusQuery",
            "artifactId": "artifact_backend_core_status",
            "outputPath": str(tmp_path / "backend-core-platform-status-report.json"),
            "agentDraftId": "draft_core",
            "agentStatus": "ACCEPTED_FOR_DRAFT",
            "querySucceeded": True,
            "suggestedImportResultStatus": "ACCEPTED_FOR_DRAFT",
            "requestSent": True,
            "networkAccess": True,
            "secretsRead": True,
            "realPublish": False,
        },
    )
    status_event.mode = "REAL_PLATFORM_IMPORT_STATUS_QUERY"
    core_repository.save_operation_audit_event(send_event)
    core_repository.save_operation_audit_event(status_event)

    signoff_payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity.id}/signoff",
        store_path=store_path,
        body={
            "reviewer": "teacher_4",
            "comment": "repository-backed signoff after accepted draft",
            "output": str(signoff_output),
            "coreDbPath": str(core_db_path),
        },
    )
    assert_api_envelope(signoff_payload)
    signoff = signoff_payload["data"]["agentEntitySignoffRecord"]
    signoff_core = signoff_payload["data"]["backendCoreAgentEntitySignoff"]
    assert signoff_output.exists()
    assert signoff["agentEntityId"] == entity.id
    assert signoff["readyStateBeforeSignoff"] == "READY_FOR_PLATFORM_ENTITY_SIGNOFF"
    assert signoff["summary"]["signoffRecorded"] is True
    assert signoff["safety"]["mockStoreUpdated"] is False
    assert signoff["safety"]["databaseWrittenByLocalSystem"] is True
    assert signoff_core["repositoryContractUsed"] is True
    assert signoff_core["artifactWritten"] is True
    assert signoff_core["operationAuditEventWritten"] is True
    assert signoff_core["localSqliteWritten"] is True

    readiness_after_signoff = handle_request(
        "GET",
        f"/api/platform-entities/readiness-report?{urlencode({'coreDbPath': str(core_db_path), 'sourceTaskId': task.id})}",
        store_path=store_path,
    )["data"]["agentEntityReadinessReport"]
    signed_item = next(item for item in readiness_after_signoff["items"] if item["agentEntityId"] == entity.id)
    assert signed_item["repositoryBacked"] is True
    assert signed_item["signoffRecorded"] is True
    assert signed_item["latestSignoffArtifactId"] == signoff_payload["data"]["artifact"]["id"]
    assert signed_item["postSignoffPrePublishChecklist"]["status"] == "READY_FOR_FINAL_HUMAN_PUBLISH_REVIEW"
    assert readiness_after_signoff["summary"]["agentEntitySignoffRecordedTotal"] == 1
    assert readiness_after_signoff["summary"]["postSignoffPrePublishReadyTotal"] == 1

    final_review_payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity.id}/final-publish-review-decision",
        store_path=store_path,
        body={
            "reviewer": "teacher_5",
            "decision": "APPROVED_FOR_PUBLISH_PLANNING",
            "comment": "repository-backed final review, no publish execution",
            "output": str(final_review_output),
            "confirmNoAutoPublish": True,
            "confirmNoRealPublish": True,
            "confirmFinalHumanReview": True,
            "coreDbPath": str(core_db_path),
        },
    )
    assert_api_envelope(final_review_payload)
    final_review = final_review_payload["data"]["finalPublishReviewDecision"]
    final_core = final_review_payload["data"]["backendCoreAgentEntityFinalPublishReviewDecision"]
    assert final_review_output.exists()
    assert final_review["agentEntityId"] == entity.id
    assert final_review["decision"] == "APPROVED_FOR_PUBLISH_PLANNING"
    assert final_review["summary"]["approvedForPublishPlanning"] is True
    assert final_review["summary"]["publishExecuted"] is False
    assert final_review["safety"]["databaseWrittenByLocalSystem"] is True
    assert final_review["safety"]["realPublish"] is False
    assert final_core["repositoryContractUsed"] is True
    assert final_core["artifactWritten"] is True
    assert final_core["operationAuditEventWritten"] is True
    assert final_core["localSqliteWritten"] is True

    readiness_after_final = handle_request(
        "GET",
        f"/api/platform-entities/readiness-report?{urlencode({'coreDbPath': str(core_db_path), 'sourceTaskId': task.id})}",
        store_path=store_path,
    )["data"]["agentEntityReadinessReport"]
    final_item = next(item for item in readiness_after_final["items"] if item["agentEntityId"] == entity.id)
    assert final_item["latestFinalPublishReviewDecisionArtifactId"] == final_review_payload["data"]["artifact"]["id"]
    assert final_item["finalPublishReviewDecision"]["recorded"] is True
    assert final_item["finalPublishReviewDecision"]["approvedForPublishPlanning"] is True
    assert readiness_after_final["summary"]["finalPublishReviewDecisionRecordedTotal"] == 1
    assert readiness_after_final["summary"]["approvedForPublishPlanningTotal"] == 1


def test_agent_entity_readiness_api_combines_backend_core_entities_with_grading_sqlite_records(tmp_path):
    store_path = tmp_path / "store.json"
    core_db_path = tmp_path / "backend-core-platform-grading-readiness.sqlite3"
    grading_db_path = tmp_path / "grading-platform-readiness.sqlite3"
    source_store = JsonTaskStore(tmp_path / "source-store.json")
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Backend Core grading readiness task",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_backend_core_grading_readiness",
    )
    preview_artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path="examples/output/grading-rule-import-preview.json",
        title="Backend Core Grading Rule Import Preview",
        status=ArtifactStatus.COMPLETED,
        task_id=task.id,
        trace_id=task.traceId,
        metadata={"component": "GradingRuleImportPreview", "agentEntity": "grading_rule"},
        mode="LOCAL_PLATFORM_IMPORT_PREVIEW",
    )
    mock_import_artifact = create_artifact_record(
        kind=ArtifactKind.WORKFLOW_REPORT,
        path="examples/output/grading-rule-mock-import.json",
        title="Backend Core Grading Rule Mock Import",
        status=ArtifactStatus.COMPLETED,
        task_id=task.id,
        trace_id=task.traceId,
        metadata={
            "component": "GradingRuleMockImport",
            "agentEntity": "grading_rule",
            "agentEntityId": "agent_entity_backend_core_grading",
            "entityType": "grading_rule",
        },
        mode="LOCAL_PLATFORM_ENTITY_MOCK_IMPORT",
    )
    entity = create_agent_entity_record(
        entity_type=AgentEntityType.GRADING_RULE,
        title="Backend Core Grading Rule Entity",
        payload={"title": "Backend Core Grading Rule Entity"},
        source_task_id=task.id,
        source_preview_artifact_id=preview_artifact.id,
        source_preview_path=preview_artifact.path,
        reviewer="teacher_1",
        trace_id=task.traceId,
        source_dsl_path="templates/grading/examples/mixed-checks.yaml",
        source_artifact_id="artifact_grading_dsl_backend_core",
        source_artifact_kind="GRADING_DSL",
    )
    entity.id = "agent_entity_backend_core_grading"
    source_store.save(task)
    source_store.save_artifact(preview_artifact)
    source_store.save_artifact(mock_import_artifact)
    source_store.save_agent_entity(entity)
    init_payload = handle_request(
        "POST",
        "/api/backend/core-db/init",
        store_path=source_store.path,
        body={"coreDbPath": str(core_db_path), "actor": "teacher_1"},
    )
    sync_payload = handle_request(
        "POST",
        "/api/backend/core-db/sync-local",
        store_path=source_store.path,
        body={"coreDbPath": str(core_db_path), "actor": "teacher_1"},
    )
    grading_repository = mock_api.GradingSQLiteRepository(grading_db_path)
    grading_repository.initialize_schema()
    grading_repository.save_grading_record(
        GradingRecord(
            submissionId="submission_backend_core_grading_ready_001",
            gradingId="grading_backend_core_ready_001",
            reportPath="examples/output/grading-evidence-auto.json",
            reportMode="GRADING_EVIDENCE_AUTO",
            status=GradingRecordStatus.HUMAN_APPROVED,
            totalScore=100,
            earnedScore=96,
            coveredScore=100,
            missingScore=0,
            coverageRatio=1.0,
            taskId=task.id,
            candidateId="candidate_backend_core_grading_ready_001",
            reviewer="teacher_1",
            reviewedBy="teacher_2",
            reviewedAt="2026-06-30T00:00:00Z",
            reviewDecision="approve-ready",
            scorePreviewStatus="READY_FOR_DECISION_NOTE",
            decisionNoteRecommendation="approve-ready",
            manualReviewChecklistStatus="READY_FOR_DECISION",
            traceId=task.traceId,
        )
    )
    query = urlencode(
        {
            "coreDbPath": str(core_db_path),
            "gradingDbPath": str(grading_db_path),
            "sourceTaskId": task.id,
        }
    )

    payload = handle_request(
        "GET",
        f"/api/platform-entities/readiness-report?{query}",
        store_path=store_path,
    )

    assert_api_envelope(init_payload)
    assert_api_envelope(sync_payload)
    assert_api_envelope(payload)
    report = payload["data"]["agentEntityReadinessReport"]
    backend_core = payload["data"]["backendCoreAgentEntityReadiness"]
    grading_item = next(item for item in report["items"] if item["agentEntity"] == "grading_rule")
    grading_evidence = grading_item["gradingRecordReviewEvidence"]
    assert report["repositoryBacked"] is True
    assert report["summary"]["gradingRecordReviewApplicableTotal"] == 1
    assert report["summary"]["gradingRecordReviewReadyTotal"] == 1
    assert report["summary"]["gradingRecordReviewBlockedTotal"] == 0
    assert grading_item["agentEntityId"] == entity.id
    assert grading_evidence["source"] == "records_override"
    assert grading_evidence["state"] == "READY_FOR_PLATFORM_REVIEW"
    assert grading_evidence["readyForAgentReview"] is True
    assert grading_evidence["latestSubmissionId"] == "submission_backend_core_grading_ready_001"
    assert grading_evidence["latestReviewedBy"] == "teacher_2"
    assert backend_core["repositoryContractUsed"] is True
    assert backend_core["gradingRecordExternalSourceUsed"] is True
    assert backend_core["gradingRecordSource"]["mode"] == "LOCAL_SQLITE_GRADING_RECORD_READINESS_BRIDGE"
    assert backend_core["gradingRecordSource"]["available"] is True
    assert backend_core["gradingRecordSource"]["dbPath"] == str(grading_db_path)
    assert backend_core["gradingRecordSource"]["recordTotal"] == 1
    assert backend_core["jsonStoreSourceRead"] is False
    assert backend_core["databaseWritten"] is False
    assert backend_core["realPublish"] is False

    missing_grading_db_path = tmp_path / "missing-grading-readiness.sqlite3"
    missing_query = urlencode(
        {
            "coreDbPath": str(core_db_path),
            "gradingDbPath": str(missing_grading_db_path),
            "sourceTaskId": task.id,
        }
    )
    missing_payload = handle_request(
        "GET",
        f"/api/platform-entities/readiness-report?{missing_query}",
        store_path=store_path,
    )
    assert_api_envelope(missing_payload)
    missing_backend_core = missing_payload["data"]["backendCoreAgentEntityReadiness"]
    assert missing_backend_core["gradingRecordExternalSourceUsed"] is True
    assert missing_backend_core["gradingRecordSource"]["available"] is False
    assert missing_backend_core["gradingRecordSource"]["reason"] == "grading sqlite file does not exist"
    assert missing_backend_core["gradingRecordSource"]["recordTotal"] == 0
    assert missing_grading_db_path.exists() is False


def test_ppt_deck_import_preview_mock_import_and_dry_run_api(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/ppt/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{task_id}/approve", store_path=store_path, body={"reviewer": "teacher_1"})

    preview = handle_request(
        "POST",
        "/api/ppt/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "ppt-preview.json")},
    )
    imported = handle_request(
        "POST",
        "/api/ppt/mock-import",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "ppt-import.json")},
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]
    dry_run = handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/import-dry-run",
        store_path=store_path,
        body={"reviewer": "teacher_2", "output": str(tmp_path / "ppt-dry-run.json")},
    )

    assert_api_envelope(preview)
    assert preview["data"]["pptDeckImportPreview"]["agentEntity"] == "ppt_deck"
    assert preview["data"]["pptDeckImportPreview"]["pptDeckDraft"]["slideTotal"] >= 1
    assert preview["data"]["pptDeckImportPreview"]["pptDeckDraft"]["pptxArtifactRequiredBeforePublish"] is True
    assert preview["data"]["operationAuditEvent"]["action"] == "PPT_DECK_IMPORT_PREVIEW"
    assert imported["data"]["agentEntityRecord"]["entityType"] == "ppt_deck"
    assert imported["data"]["agentEntityRecord"]["payload"]["pptxArtifactImported"] is False
    assert imported["data"]["operationAuditEvent"]["action"] == "PPT_DECK_MOCK_IMPORT"
    assert dry_run["data"]["agentEntityImportDryRun"]["entityType"] == "ppt_deck"
    assert dry_run["data"]["agentEntityImportDryRun"]["targetEndpoint"]["path"] == "/api/platform/ppt-deck/draft-imports"
    assert dry_run["data"]["agentEntityImportDryRun"]["requestPreview"]["payload"]["pptxArtifactImported"] is False
    assert dry_run["data"]["agentEntityImportDryRun"]["safety"]["requestSent"] is False


def test_agent_entity_import_send_api_requires_explicit_confirmations(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "platform-secret-token")
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{task_id}/approve", store_path=store_path, body={"reviewer": "teacher_1"})
    handle_request(
        "POST",
        "/api/labs/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "preview.json")},
    )
    imported = handle_request(
        "POST",
        "/api/labs/mock-import",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "mock-import.json")},
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]
    dry_run = tmp_path / "platform-import-dry-run.json"
    handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/import-dry-run",
        store_path=store_path,
        body={"reviewer": "teacher_2", "output": str(dry_run)},
    )

    payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/import-send",
        store_path=store_path,
        body={
            "reviewer": "teacher_3",
            "dryRun": str(dry_run),
            "output": str(tmp_path / "send-report.json"),
            "baseUrl": "http://127.0.0.1:9",
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "PLATFORM_IMPORT_SEND_CONFIRMATION_REQUIRED"
    assert payload["errors"][0]["field"] == "explicitPlatformCallOptIn"


def test_agent_entity_import_send_api_posts_dry_run_payload_to_configured_platform(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "platform-secret-token")
    store_path = tmp_path / "store.json"
    server, thread, base_url = start_recording_platform_server()
    try:
        generated = handle_request(
            "POST",
            "/api/labs/generate",
            store_path=store_path,
            body={"input": "examples/input/demo-source.md"},
        )
        task_id = generated["data"]["task"]["id"]
        handle_request("POST", f"/api/ai-tasks/{task_id}/approve", store_path=store_path, body={"reviewer": "teacher_1"})
        handle_request(
            "POST",
            "/api/labs/import-preview",
            store_path=store_path,
            body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "preview.json")},
        )
        imported = handle_request(
            "POST",
            "/api/labs/mock-import",
            store_path=store_path,
            body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "mock-import.json")},
        )
        entity_id = imported["data"]["agentEntityRecord"]["id"]
        dry_run = tmp_path / "platform-import-dry-run.json"
        send_report = tmp_path / "platform-import-send-report.json"
        handle_request(
            "POST",
            f"/api/platform-entities/{entity_id}/import-dry-run",
            store_path=store_path,
            body={"reviewer": "teacher_2", "output": str(dry_run)},
        )

        payload = handle_request(
            "POST",
            f"/api/platform-entities/{entity_id}/import-send",
            store_path=store_path,
            body={
                "reviewer": "teacher_3",
                "dryRun": str(dry_run),
                "output": str(send_report),
                "baseUrl": base_url,
                "explicitPlatformCallOptIn": True,
                "confirmDryRunReviewed": True,
                "confirmManualPlatformReview": True,
                "confirmNoAutoPublish": True,
            },
        )
        status_report = tmp_path / "platform-import-status-query.json"
        status_payload = handle_request(
            "POST",
            f"/api/platform-entities/{entity_id}/import-status",
            store_path=store_path,
            body={
                "reviewer": "teacher_4",
                "sendResult": str(send_report),
                "output": str(status_report),
                "explicitPlatformQueryOptIn": True,
            },
        )
    finally:
        stop_recording_platform_server(server, thread)

    assert_api_envelope(payload)
    assert send_report.exists()
    post_requests = [item for item in RecordingPlatformImportHandler.requests if item.get("method") != "GET"]
    assert len(post_requests) == 1
    recorded = post_requests[0]
    assert recorded["path"] == "/api/platform/lab-template/draft-imports"
    assert recorded["authorization"] == "Bearer platform-secret-token"
    assert recorded["body"]["entityType"] == "lab_template"
    result = payload["data"]["agentEntityImportSendResult"]
    assert result["component"] == "AgentEntityImportSendResult"
    assert result["mode"] == "REAL_PLATFORM_IMPORT_REQUEST_SENT"
    assert result["agentEntityId"] == entity_id
    assert result["response"]["statusCode"] == 202
    assert result["response"]["body"]["json"]["status"] == "PENDING_MANUAL_PLATFORM_REVIEW"
    assert result["safety"]["requestSent"] is True
    assert result["safety"]["networkAccess"] is True
    assert result["safety"]["secretsRead"] is True
    assert result["safety"]["secretValueReturned"] is False
    assert result["safety"]["databaseWrittenByLocalSystem"] is False
    assert result["safety"]["realAgentImportAttempted"] is True
    assert result["safety"]["realAgentImportAccepted"] is True
    assert result["safety"]["autoPublishAllowed"] is False
    assert result["safety"]["realPublish"] is False
    assert payload["data"]["artifact"]["mode"] == "REAL_PLATFORM_IMPORT_REQUEST_SENT"
    assert payload["data"]["operationAuditEvent"]["action"] == "PLATFORM_ENTITY_IMPORT_SEND"
    entity_payload = handle_request("GET", f"/api/platform-entities/{entity_id}", store_path=store_path)
    activity = entity_payload["data"]["agentEntityImportActivity"]
    assert activity["component"] == "AgentEntityImportActivitySummary"
    assert activity["summary"]["dryRunPrepared"] is True
    assert activity["summary"]["requestSent"] is True
    assert activity["summary"]["latestStatusCode"] == 202
    assert activity["summary"]["secretValueReturned"] is False
    assert activity["summary"]["databaseWrittenByLocalSystem"] is False
    assert activity["summary"]["realPublish"] is False
    detail_payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)
    task_activity = detail_payload["data"]["reviewDetail"]["agentEntityImportActivity"]
    assert task_activity["visible"] is True
    assert task_activity["sendTotal"] == 1
    assert task_activity["summary"]["latestStatusCode"] == 202
    assert detail_payload["data"]["reviewDetail"]["reviewPage"]["agentEntityImportActivity"]["sendTotal"] == 1
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "platform-secret-token" not in serialized

    assert_api_envelope(status_payload)
    assert status_report.exists()
    get_requests = [item for item in RecordingPlatformImportHandler.requests if item.get("method") == "GET"]
    assert len(get_requests) == 1
    assert get_requests[0]["path"] == "/api/platform/lab-template/draft-imports/draft_import_api_test"
    assert get_requests[0]["authorization"] == "Bearer platform-secret-token"
    status_query = status_payload["data"]["agentEntityImportStatusQuery"]
    assert status_query["component"] == "AgentEntityImportStatusQuery"
    assert status_query["mode"] == "REAL_PLATFORM_IMPORT_STATUS_QUERY"
    assert status_query["agentDraftId"] == "draft_import_api_test"
    assert status_query["agentStatus"] == "ACCEPTED_FOR_DRAFT"
    assert status_query["suggestedImportResultStatus"] == "ACCEPTED_FOR_DRAFT"
    assert status_query["response"]["statusCode"] == 200
    assert status_query["summary"]["localEntityStatusChanged"] is False
    assert status_query["safety"]["requestSent"] is True
    assert status_query["safety"]["networkAccess"] is True
    assert status_query["safety"]["mockStoreUpdated"] is False
    assert status_query["safety"]["secretValueReturned"] is False
    assert status_query["safety"]["realPublish"] is False
    assert status_payload["data"]["agentEntityRecord"]["status"] == "DRAFT_CREATED"

    entity_payload_after_status = handle_request("GET", f"/api/platform-entities/{entity_id}", store_path=store_path)
    status_activity = entity_payload_after_status["data"]["agentEntityImportActivity"]
    assert status_activity["statusQueryTotal"] == 1
    assert status_activity["summary"]["statusQueried"] is True
    assert status_activity["summary"]["latestQueriedPlatformStatus"] == "ACCEPTED_FOR_DRAFT"
    assert status_activity["summary"]["latestSuggestedImportResultStatus"] == "ACCEPTED_FOR_DRAFT"

    result_record = tmp_path / "platform-import-result-record.json"
    result_payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/import-result",
        store_path=store_path,
        body={
            "reviewer": "teacher_4",
            "sendResult": str(send_report),
            "agentStatus": "ACCEPTED_FOR_DRAFT",
            "output": str(result_record),
        },
    )
    assert_api_envelope(result_payload)
    assert result_record.exists()
    result_record_payload = result_payload["data"]["agentEntityImportResultRecord"]
    assert result_record_payload["component"] == "AgentEntityImportResultRecord"
    assert result_record_payload["agentEntityId"] == entity_id
    assert result_record_payload["agentDraftId"] == "draft_import_api_test"
    assert result_record_payload["agentStatus"] == "ACCEPTED_FOR_DRAFT"
    assert result_record_payload["localEntityStatus"]["before"] == "DRAFT_CREATED"
    assert result_record_payload["localEntityStatus"]["after"] == "REAL_IMPORT_DRAFT_ACCEPTED"
    assert result_record_payload["summary"]["acceptedForDraft"] is True
    assert result_record_payload["safety"]["requestSent"] is False
    assert result_record_payload["safety"]["networkAccess"] is False
    assert result_record_payload["safety"]["secretValueReturned"] is False
    assert result_record_payload["safety"]["realPublish"] is False
    assert result_payload["data"]["agentEntityRecord"]["status"] == "REAL_IMPORT_DRAFT_ACCEPTED"
    assert result_payload["data"]["operationAuditEvent"]["action"] == "PLATFORM_ENTITY_IMPORT_RESULT_RECORD"
    entity_payload_after_result = handle_request("GET", f"/api/platform-entities/{entity_id}", store_path=store_path)
    post_activity = entity_payload_after_result["data"]["agentEntityImportActivity"]
    assert post_activity["resultTotal"] == 1
    assert post_activity["summary"]["resultRecorded"] is True
    assert post_activity["summary"]["latestPlatformDraftId"] == "draft_import_api_test"
    assert post_activity["summary"]["latestPlatformStatus"] == "ACCEPTED_FOR_DRAFT"
    assert post_activity["summary"]["acceptedForDraft"] is True
    post_detail_payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)
    assert post_detail_payload["data"]["reviewDetail"]["agentEntityImportActivity"]["resultTotal"] == 1
    assert (
        post_detail_payload["data"]["reviewDetail"]["reviewPage"]["agentEntityImportActivity"]["summary"][
            "latestPlatformStatus"
        ]
        == "ACCEPTED_FOR_DRAFT"
    )
    detail_readiness = post_detail_payload["data"]["reviewDetail"]["agentEntityReadinessReport"]
    page_readiness = post_detail_payload["data"]["reviewDetail"]["reviewPage"]["agentEntityReadinessReport"]
    assert detail_readiness == page_readiness
    assert detail_readiness["component"] == "AgentEntityReadinessReport"
    assert detail_readiness["summary"]["agentEntitySignoffReadyTotal"] == 1
    assert detail_readiness["summary"]["agentEntitySignoffRecordedTotal"] == 0
    readiness_payload = handle_request(
        "GET",
        f"/api/platform-entities/readiness-report?sourceTaskId={task_id}",
        store_path=store_path,
    )
    readiness_report = readiness_payload["data"]["agentEntityReadinessReport"]
    readiness_item = next(item for item in readiness_report["items"] if item["agentEntityId"] == entity_id)
    assert readiness_report["summary"]["dryRunPreparedTotal"] == 1
    assert readiness_report["summary"]["requestSentTotal"] == 1
    assert readiness_report["summary"]["statusQueriedTotal"] == 1
    assert readiness_report["summary"]["resultRecordedTotal"] == 1
    assert readiness_item["dryRunPrepared"] is True
    assert readiness_item["requestSent"] is True
    assert readiness_item["statusQueried"] is True
    assert readiness_item["resultRecorded"] is True
    assert readiness_item["latestPlatformStatus"] == "ACCEPTED_FOR_DRAFT"
    assert readiness_item["agentSideReviewed"] is True
    assert readiness_item["acceptedForDraft"] is True
    assert readiness_item["signoffState"] == "READY_FOR_PLATFORM_ENTITY_SIGNOFF"
    assert readiness_item["readyForAgentEntitySignoff"] is True
    assert {check["id"] for check in readiness_item["manualSignoffChecklist"]} == {
        "confirm_local_preview_and_mock_import_ready",
        "confirm_platform_send_recorded",
        "confirm_platform_status_queried",
        "confirm_platform_result_recorded",
        "confirm_accepted_for_draft_only",
    }
    assert all(check["matched"] is True for check in readiness_item["manualSignoffChecklist"])
    assert readiness_report["summary"]["agentEntitySignoffReadyTotal"] == 1
    assert readiness_report["summary"]["allPlatformEntitiesReadyForSignoff"] is False
    assert readiness_item["safety"]["realPublish"] is False

    signoff_record = tmp_path / "platform-entity-signoff-record.json"
    signoff_payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/signoff",
        store_path=store_path,
        body={
            "reviewer": "teacher_5",
            "comment": "reviewed accepted draft before local signoff",
            "output": str(signoff_record),
        },
    )
    assert_api_envelope(signoff_payload)
    assert signoff_record.exists()
    signoff = signoff_payload["data"]["agentEntitySignoffRecord"]
    assert signoff["component"] == "AgentEntitySignoffRecord"
    assert signoff["mode"] == "LOCAL_PLATFORM_ENTITY_SIGNOFF_RECORD"
    assert signoff["agentEntityId"] == entity_id
    assert signoff["signoffState"] == "PLATFORM_ENTITY_SIGNOFF_RECORDED"
    assert signoff["readyStateBeforeSignoff"] == "READY_FOR_PLATFORM_ENTITY_SIGNOFF"
    assert signoff["summary"]["signoffRecorded"] is True
    assert signoff["summary"]["localEntityStatusChanged"] is False
    assert signoff["safety"]["requestSent"] is False
    assert signoff["safety"]["networkAccess"] is False
    assert signoff["safety"]["secretsRead"] is False
    assert signoff["safety"]["realPublish"] is False
    assert signoff_payload["data"]["agentEntityRecord"]["status"] == "REAL_IMPORT_DRAFT_ACCEPTED"
    assert signoff_payload["data"]["artifact"]["mode"] == "LOCAL_PLATFORM_ENTITY_SIGNOFF_RECORD"
    assert signoff_payload["data"]["operationAuditEvent"]["action"] == "PLATFORM_ENTITY_SIGNOFF_RECORD"
    entity_payload_after_signoff = handle_request("GET", f"/api/platform-entities/{entity_id}", store_path=store_path)
    signoff_activity = entity_payload_after_signoff["data"]["agentEntityImportActivity"]
    assert signoff_activity["signoffTotal"] == 1
    assert signoff_activity["latestSignoff"]["signoffRecorded"] is True
    assert signoff_activity["summary"]["signoffRecorded"] is True
    signoff_detail_payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)
    signoff_detail_readiness = signoff_detail_payload["data"]["reviewDetail"]["agentEntityReadinessReport"]
    assert signoff_detail_readiness["summary"]["agentEntitySignoffRecordedTotal"] == 1
    assert signoff_detail_payload["data"]["reviewDetail"]["summary"]["agentEntitySignoffRecordedTotal"] == 1
    signed_detail_item = next(
        item for item in signoff_detail_readiness["items"] if item["agentEntityId"] == entity_id
    )
    assert signed_detail_item["signoffRecorded"] is True

    readiness_after_signoff = handle_request(
        "GET",
        f"/api/platform-entities/readiness-report?sourceTaskId={task_id}",
        store_path=store_path,
    )["data"]["agentEntityReadinessReport"]
    signed_item = next(item for item in readiness_after_signoff["items"] if item["agentEntityId"] == entity_id)
    assert signed_item["signoffRecorded"] is True
    assert signed_item["latestSignoffArtifactId"] == signoff_payload["data"]["artifact"]["id"]
    assert signed_item["finalPublishReviewDecision"]["recorded"] is False
    assert readiness_after_signoff["summary"]["agentEntitySignoffRecordedTotal"] == 1
    assert readiness_after_signoff["summary"]["allPlatformEntitiesSignoffRecorded"] is False
    assert readiness_after_signoff["summary"]["finalPublishReviewDecisionRecordedTotal"] == 0

    missing_confirm_payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/final-publish-review-decision",
        store_path=store_path,
        body={
            "reviewer": "teacher_5",
            "decision": "APPROVED_FOR_PUBLISH_PLANNING",
            "output": str(tmp_path / "missing-confirm-final-review.json"),
        },
    )
    assert missing_confirm_payload["success"] is False
    assert missing_confirm_payload["code"] == "VALIDATION_ERROR"
    assert missing_confirm_payload["errors"][0]["field"] == "confirmNoAutoPublish"

    final_review_record = tmp_path / "platform-entity-final-publish-review-decision.json"
    final_review_payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/final-publish-review-decision",
        store_path=store_path,
        body={
            "reviewer": "teacher_5",
            "decision": "APPROVED_FOR_PUBLISH_PLANNING",
            "comment": "approved for later publish planning only",
            "output": str(final_review_record),
            "confirmNoAutoPublish": True,
            "confirmNoRealPublish": True,
            "confirmFinalHumanReview": True,
        },
    )
    assert_api_envelope(final_review_payload)
    assert final_review_record.exists()
    final_review = final_review_payload["data"]["finalPublishReviewDecision"]
    assert final_review["component"] == "FinalPublishReviewDecision"
    assert final_review["mode"] == "LOCAL_FINAL_HUMAN_PUBLISH_REVIEW_DECISION"
    assert final_review["decision"] == "APPROVED_FOR_PUBLISH_PLANNING"
    assert final_review["summary"]["approvedForPublishPlanning"] is True
    assert final_review["summary"]["publishExecuted"] is False
    assert final_review["safety"]["requestSent"] is False
    assert final_review["safety"]["realPublish"] is False
    assert final_review["safety"]["requiresSeparatePublishAuthorization"] is True
    assert final_review_payload["data"]["artifact"]["mode"] == "LOCAL_FINAL_HUMAN_PUBLISH_REVIEW_DECISION"
    assert (
        final_review_payload["data"]["operationAuditEvent"]["action"]
        == "PLATFORM_ENTITY_FINAL_PUBLISH_REVIEW_DECISION"
    )

    readiness_after_final_review = handle_request(
        "GET",
        f"/api/platform-entities/readiness-report?sourceTaskId={task_id}",
        store_path=store_path,
    )["data"]["agentEntityReadinessReport"]
    final_review_item = next(
        item for item in readiness_after_final_review["items"] if item["agentEntityId"] == entity_id
    )
    assert final_review_item["latestFinalPublishReviewDecisionArtifactId"] == final_review_payload["data"]["artifact"]["id"]
    assert final_review_item["finalPublishReviewDecision"]["recorded"] is True
    assert final_review_item["finalPublishReviewDecision"]["decision"] == "APPROVED_FOR_PUBLISH_PLANNING"
    assert readiness_after_final_review["summary"]["finalPublishReviewDecisionRecordedTotal"] == 1
    assert readiness_after_final_review["summary"]["approvedForPublishPlanningTotal"] == 1
    assert readiness_after_final_review["summary"]["needsRevisionTotal"] == 0


def test_agent_entity_import_send_api_rejects_invalid_timeout(tmp_path):
    payload = handle_request(
        "POST",
        "/api/platform-entities/agent_entity_missing/import-send",
        store_path=tmp_path / "store.json",
        body={"reviewer": "teacher_3", "timeoutSeconds": "bad"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "timeoutSeconds"


def test_agent_entity_import_result_api_rejects_invalid_status(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    handle_request(
        "POST",
        "/api/labs/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "preview.json")},
    )
    imported = handle_request(
        "POST",
        "/api/labs/mock-import",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "mock-import.json")},
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]
    send_report = tmp_path / "send.json"
    send_report.write_text(
        json.dumps(
            {
                "component": "AgentEntityImportSendResult",
                "mode": "REAL_PLATFORM_IMPORT_REQUEST_SENT",
                "agentEntityId": entity_id,
                "entityType": "lab_template",
                "response": {"ok": True, "statusCode": 202, "body": {"json": {"draftImportId": "draft_bad"}}},
                "request": {"idempotencyKey": "dryrun:test"},
                "targetEndpoint": {"method": "POST", "path": "/api/platform/lab-template/draft-imports"},
                "safety": {"requestSent": True},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    payload = handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/import-result",
        store_path=store_path,
        body={
            "reviewer": "teacher_4",
            "sendResult": str(send_report),
            "agentStatus": "BAD_STATUS",
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "agentStatus"


def test_exam_and_grading_import_preview_api_requires_approved_task(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    task_id = generated["data"]["task"]["id"]
    blocked = handle_request(
        "POST",
        "/api/exams/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "blocked-exam.json")},
    )
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    approved_detail_payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)
    assert_api_envelope(approved_detail_payload)
    approved_action_panel = approved_detail_payload["data"]["reviewDetail"]["platformImportPreviewActions"]
    assert approved_action_panel["visible"] is True
    assert approved_action_panel["total"] == 2
    assert approved_action_panel["enabledTotal"] == 2
    assert approved_action_panel["previewAlreadyCreatedTotal"] == 0
    assert {item["component"] for item in approved_action_panel["items"]} == {
        "ExamQuestionImportPreviewAction",
        "GradingRuleImportPreviewAction",
    }
    core_before_preview = handle_request("GET", f"/api/review-tasks/{task_id}/core-readiness", store_path=store_path)
    assert_api_envelope(core_before_preview)
    core_report = core_before_preview["data"]["coreWorkflowReadinessReport"]
    assert core_report["summary"]["platformImportPreviewActionTotal"] == 2
    assert core_report["summary"]["platformImportPreviewPendingTotal"] == 2
    assert core_report["summary"]["platformImportPreviewPendingEntities"] == ["exam_question", "grading_rule"]
    assert core_report["platformImportPreviewActionSummary"]["pendingPreviewComponents"] == [
        "ExamQuestionImportPreview",
        "GradingRuleImportPreview",
    ]
    assert core_report["nextToolRecommendation"]["reasonCode"] == "PLATFORM_IMPORT_PREVIEW_PENDING"
    assert core_report["nextToolRecommendation"]["toolName"] == "create_exam_question_import_preview"
    assert core_report["nextToolRecommendation"]["argumentsPreview"]["taskId"] == task_id
    assert core_report["nextToolRecommendation"]["autoExecuteAllowed"] is False
    assert core_report["nextToolRecommendation"]["realPublishAllowed"] is False
    approved_signoff = approved_detail_payload["data"]["reviewDetail"]["platformImportPreviewSignoff"]
    assert approved_signoff["visible"] is True
    assert approved_signoff["readyForHumanSignoff"] is False
    assert approved_signoff["total"] == 0
    assert approved_signoff["missingPreviewTotal"] == 2
    assert {
        item["component"] for item in approved_signoff["missingPreviewActions"]
    } == {
        "ExamQuestionImportPreviewAction",
        "GradingRuleImportPreviewAction",
    }
    exam_payload = handle_request(
        "POST",
        "/api/exams/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "exam-question-import-preview.json")},
    )
    grading_payload = handle_request(
        "POST",
        "/api/grading/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "grading-rule-import-preview.json")},
    )

    assert_api_envelope(blocked)
    assert blocked["success"] is False
    assert blocked["code"] == "STATE_TRANSITION_ERROR"
    assert approved["data"]["task"]["status"] == "APPROVED"
    assert_api_envelope(exam_payload)
    exam_preview = exam_payload["data"]["examQuestionImportPreview"]
    assert exam_preview["component"] == "ExamQuestionImportPreview"
    assert exam_preview["sourceTaskStatus"] == "APPROVED"
    assert exam_preview["sourceArtifactKind"] == "EXAM_DSL"
    assert exam_preview["agentEntity"] == "exam_question"
    assert exam_preview["examQuestionDraft"]["candidateAnswerVisible"] is False
    assert exam_preview["safety"]["answerVisibleToCandidate"] is False
    assert exam_payload["data"]["operationAuditEvent"]["action"] == "EXAM_QUESTION_IMPORT_PREVIEW"
    assert_api_envelope(grading_payload)
    grading_preview = grading_payload["data"]["gradingRuleImportPreview"]
    assert grading_preview["component"] == "GradingRuleImportPreview"
    assert grading_preview["sourceTaskStatus"] == "APPROVED"
    assert grading_preview["sourceArtifactKind"] == "GRADING_DSL"
    assert grading_preview["agentEntity"] == "grading_rule"
    assert grading_preview["gradingRuleDraft"]["sandboxRequiredBeforeRealExecution"] is True
    assert grading_preview["safety"]["databaseWritten"] is False
    assert grading_payload["data"]["operationAuditEvent"]["action"] == "GRADING_RULE_IMPORT_PREVIEW"

    detail_payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)
    assert_api_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    import_summary = detail["platformImportPreview"]
    assert import_summary["visible"] is True
    assert import_summary["total"] == 2
    assert import_summary["agentEntities"] == ["exam_question", "grading_rule"]
    assert {item["component"] for item in import_summary["items"]} == {
        "ExamQuestionImportPreview",
        "GradingRuleImportPreview",
    }
    assert {item["sourceArtifactKind"] for item in import_summary["items"]} == {"EXAM_DSL", "GRADING_DSL"}
    assert import_summary["databaseWritten"] is False
    assert import_summary["realPublishAllowed"] is False
    assert detail["reviewPage"]["platformImportPreview"] == import_summary
    assert detail["summary"]["platformImportPreviewVisible"] is True
    assert detail["summary"]["platformImportPreviewTotal"] == 2
    action_panel = detail["platformImportPreviewActions"]
    assert action_panel["visible"] is True
    assert action_panel["enabledTotal"] == 2
    assert action_panel["previewAlreadyCreatedTotal"] == 2
    assert {item["apiEndpoint"] for item in action_panel["items"]} == {
        "POST /api/exams/import-preview",
        "POST /api/grading/import-preview",
    }
    assert all(item["previewAlreadyCreated"] is True for item in action_panel["items"])
    assert detail["reviewPage"]["platformImportPreviewActions"] == action_panel
    signoff = detail["platformImportPreviewSignoff"]
    assert signoff["visible"] is True
    assert signoff["readyForHumanSignoff"] is True
    assert signoff["total"] == 2
    assert signoff["missingPreviewTotal"] == 0
    assert {item["component"] for item in signoff["items"]} == {
        "ExamQuestionImportPreviewSignoff",
        "GradingRuleImportPreviewSignoff",
    }
    signoff_check_ids = {
        check["id"] for item in signoff["items"] for check in item["checks"]
    }
    assert "confirm_pre_approve_review_check_before_grading_rule_import" in signoff_check_ids
    assert signoff["preApproveReviewCheckSummary"]["applicable"] is True
    assert signoff["preApproveReviewCheckSummary"]["approveReadyDecision"] is False
    assert signoff["preApproveReviewCheckSummary"]["warningTotal"] == 2
    assert detail["reviewPage"]["platformImportPreviewSignoff"] == signoff
    assert detail["summary"]["platformImportPreviewSignoffReady"] is True


def test_grading_result_preview_api_reads_existing_report_without_execution(tmp_path):
    store_path = tmp_path / "store.json"
    report_path = tmp_path / "readonly-sandbox-report.json"
    run_payload = handle_request(
        "POST",
        "/api/grading/readonly-evidence",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/readonly-sandbox.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(report_path),
        },
    )
    assert_api_envelope(run_payload)
    assert run_payload["success"] is True

    payload = handle_request(
        "GET",
        f"/api/grading/result-preview?report={report_path}&candidateId=candidate_001&maxItems=2",
        store_path=store_path,
    )

    assert_api_envelope(payload)
    preview = payload["data"]["gradingResultPreview"]
    assert preview["component"] == "GradingResultPreview"
    assert preview["mode"] == "READ_EXISTING_GRADING_REPORT_ONLY"
    assert preview["candidateId"] == "candidate_001"
    assert preview["score"]["earnedScore"] == 120
    assert preview["summary"]["executed"] == 4
    assert preview["evidencePreview"]["totalVisible"] == 2
    assert preview["safety"]["sandboxExecutedByPreview"] is False
    assert preview["safety"]["sourceSandboxExecuted"] is True
    assert preview["safety"]["answerVisibleToCandidate"] is False


def test_exam_and_grading_mock_import_api_creates_agent_entities(tmp_path):
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{task_id}/approve", store_path=store_path, body={"reviewer": "teacher_1"})
    handle_request(
        "POST",
        "/api/exams/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "exam-preview.json")},
    )
    handle_request(
        "POST",
        "/api/grading/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "grading-preview.json")},
    )

    exam_payload = handle_request(
        "POST",
        "/api/exams/mock-import",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "exam-import.json")},
    )
    grading_payload = handle_request(
        "POST",
        "/api/grading/mock-import",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_2", "output": str(tmp_path / "grading-import.json")},
    )
    listed = handle_request("GET", f"/api/platform-entities?sourceTaskId={task_id}", store_path=store_path)

    assert_api_envelope(exam_payload)
    assert_api_envelope(grading_payload)
    assert exam_payload["data"]["agentEntityRecord"]["entityType"] == "exam_question"
    assert exam_payload["data"]["agentEntityRecord"]["payload"]["candidateAnswerVisible"] is False
    assert grading_payload["data"]["agentEntityRecord"]["entityType"] == "grading_rule"
    assert grading_payload["data"]["agentEntityRecord"]["payload"]["sandboxRequiredBeforeRealExecution"] is True
    assert {item["entityType"] for item in listed["data"]["items"]} == {"exam_question", "grading_rule"}


def test_agent_entity_readiness_report_api_summarizes_mock_imports(tmp_path):
    store_path = tmp_path / "store.json"
    lab_generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    lab_task_id = lab_generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{lab_task_id}/approve", store_path=store_path, body={"reviewer": "teacher_1"})
    handle_request(
        "POST",
        "/api/labs/import-preview",
        store_path=store_path,
        body={"taskId": lab_task_id, "reviewer": "teacher_1", "output": str(tmp_path / "lab-preview.json")},
    )
    handle_request(
        "POST",
        "/api/labs/mock-import",
        store_path=store_path,
        body={"taskId": lab_task_id, "reviewer": "teacher_1", "output": str(tmp_path / "lab-import.json")},
    )

    exam_generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    exam_task_id = exam_generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{exam_task_id}/approve", store_path=store_path, body={"reviewer": "teacher_2"})
    handle_request(
        "POST",
        "/api/exams/import-preview",
        store_path=store_path,
        body={"taskId": exam_task_id, "reviewer": "teacher_2", "output": str(tmp_path / "exam-preview.json")},
    )
    handle_request(
        "POST",
        "/api/grading/import-preview",
        store_path=store_path,
        body={"taskId": exam_task_id, "reviewer": "teacher_2", "output": str(tmp_path / "grading-preview.json")},
    )
    handle_request(
        "POST",
        "/api/exams/mock-import",
        store_path=store_path,
        body={"taskId": exam_task_id, "reviewer": "teacher_2", "output": str(tmp_path / "exam-import.json")},
    )
    handle_request(
        "POST",
        "/api/grading/mock-import",
        store_path=store_path,
        body={"taskId": exam_task_id, "reviewer": "teacher_2", "output": str(tmp_path / "grading-import.json")},
    )

    ppt_generated = handle_request(
        "POST",
        "/api/ppt/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    ppt_task_id = ppt_generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{ppt_task_id}/approve", store_path=store_path, body={"reviewer": "teacher_3"})
    handle_request(
        "POST",
        "/api/ppt/import-preview",
        store_path=store_path,
        body={"taskId": ppt_task_id, "reviewer": "teacher_3", "output": str(tmp_path / "ppt-preview.json")},
    )
    handle_request(
        "POST",
        "/api/ppt/mock-import",
        store_path=store_path,
        body={"taskId": ppt_task_id, "reviewer": "teacher_3", "output": str(tmp_path / "ppt-import.json")},
    )

    payload = handle_request("GET", "/api/platform-entities/readiness-report", store_path=store_path)
    filtered = handle_request("GET", f"/api/platform-entities/readiness-report?sourceTaskId={lab_task_id}", store_path=store_path)

    assert_api_envelope(payload)
    report = payload["data"]["agentEntityReadinessReport"]
    assert report["summary"]["requiredTotal"] == 4
    assert report["summary"]["readyForManualAgentReviewTotal"] == 4
    assert report["summary"]["dryRunPreparedTotal"] == 0
    assert report["summary"]["requestSentTotal"] == 0
    assert report["summary"]["statusQueriedTotal"] == 0
    assert report["summary"]["resultRecordedTotal"] == 0
    assert report["summary"]["agentEntitySignoffReadyTotal"] == 0
    assert report["summary"]["allPlatformEntitiesReadyForSignoff"] is False
    assert report["summary"]["allReadyForManualPlatformReview"] is True
    assert report["safety"]["readOnly"] is True
    assert report["safety"]["databaseWritten"] is False
    assert report["safety"]["realAgentImport"] is False
    assert {item["agentEntity"] for item in report["items"]} == {
        "lab_template",
        "exam_question",
        "grading_rule",
        "ppt_deck",
    }
    assert all(item["mockImportCreated"] is True for item in report["items"])
    assert all(item["dryRunPrepared"] is False for item in report["items"])
    assert all(item["requestSent"] is False for item in report["items"])
    assert all(item["resultRecorded"] is False for item in report["items"])
    assert all(item["signoffState"] == "WAITING_PLATFORM_ENTITY_IMPORT_ACTIVITY" for item in report["items"])
    assert all(item["readyForAgentEntitySignoff"] is False for item in report["items"])

    assert_api_envelope(filtered)
    filtered_report = filtered["data"]["agentEntityReadinessReport"]
    assert filtered_report["sourceTaskId"] == lab_task_id
    assert filtered_report["summary"]["readyForManualAgentReviewTotal"] == 1
    assert filtered_report["summary"]["missingPreviewTotal"] == 3
    assert filtered_report["summary"]["missingMockImportTotal"] == 3


def test_review_task_core_readiness_api_summarizes_platform_closure(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "platform-secret-token")
    store_path = tmp_path / "store.json"
    generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    task_id = generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{task_id}/approve", store_path=store_path, body={"reviewer": "teacher_1"})
    handle_request(
        "POST",
        "/api/labs/import-preview",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "lab-preview.json")},
    )
    imported = handle_request(
        "POST",
        "/api/labs/mock-import",
        store_path=store_path,
        body={"taskId": task_id, "reviewer": "teacher_1", "output": str(tmp_path / "lab-import.json")},
    )
    entity_id = imported["data"]["agentEntityRecord"]["id"]
    dry_run = tmp_path / "dry-run.json"
    send_report = tmp_path / "send-report.json"
    handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/import-dry-run",
        store_path=store_path,
        body={"reviewer": "teacher_1", "output": str(dry_run)},
    )
    server, thread, base_url = start_recording_platform_server()
    try:
        handle_request(
            "POST",
            f"/api/platform-entities/{entity_id}/import-send",
            store_path=store_path,
            body={
                "reviewer": "teacher_1",
                "dryRun": str(dry_run),
                "output": str(send_report),
                "baseUrl": base_url,
                "explicitPlatformCallOptIn": True,
                "confirmDryRunReviewed": True,
                "confirmManualPlatformReview": True,
                "confirmNoAutoPublish": True,
            },
        )
        handle_request(
            "POST",
            f"/api/platform-entities/{entity_id}/import-status",
            store_path=store_path,
            body={
                "reviewer": "teacher_1",
                "sendResult": str(send_report),
                "output": str(tmp_path / "status-report.json"),
                "baseUrl": base_url,
                "explicitPlatformQueryOptIn": True,
            },
        )
    finally:
        stop_recording_platform_server(server, thread)
    handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/import-result",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "sendResult": str(send_report),
            "agentStatus": "ACCEPTED_FOR_DRAFT",
            "output": str(tmp_path / "result-record.json"),
        },
    )
    handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/signoff",
        store_path=store_path,
        body={"reviewer": "teacher_1", "output": str(tmp_path / "signoff.json")},
    )
    handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/final-publish-review-decision",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "decision": "APPROVED_FOR_PUBLISH_PLANNING",
            "output": str(tmp_path / "final-review.json"),
            "confirmNoAutoPublish": True,
            "confirmNoRealPublish": True,
            "confirmFinalHumanReview": True,
        },
    )

    payload = handle_request("GET", f"/api/review-tasks/{task_id}/core-readiness", store_path=store_path)

    assert_api_envelope(payload)
    report = payload["data"]["coreWorkflowReadinessReport"]
    assert report["component"] == "CoreWorkflowReadinessReport"
    assert report["taskId"] == task_id
    assert report["status"] == "CORE_DEMO_READY_FOR_FINAL_REVIEW"
    assert report["ready"] is True
    assert report["summary"]["platformRequiredTotal"] == 1
    assert report["summary"]["readyTotal"] == report["summary"]["stepTotal"]
    assert report["safety"]["readOnly"] is True
    assert report["safety"]["networkAccess"] is False
    assert report["safety"]["realPublish"] is False


def test_agent_entity_readiness_report_api_summarizes_all_entity_signoffs(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "platform-secret-token")
    store_path = tmp_path / "store.json"

    lab_generated = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    lab_task_id = lab_generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{lab_task_id}/approve", store_path=store_path, body={"reviewer": "teacher_1"})
    handle_request(
        "POST",
        "/api/labs/import-preview",
        store_path=store_path,
        body={"taskId": lab_task_id, "reviewer": "teacher_1", "output": str(tmp_path / "lab-preview.json")},
    )
    lab_imported = handle_request(
        "POST",
        "/api/labs/mock-import",
        store_path=store_path,
        body={"taskId": lab_task_id, "reviewer": "teacher_1", "output": str(tmp_path / "lab-import.json")},
    )

    exam_generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    exam_task_id = exam_generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{exam_task_id}/approve", store_path=store_path, body={"reviewer": "teacher_2"})
    handle_request(
        "POST",
        "/api/exams/import-preview",
        store_path=store_path,
        body={"taskId": exam_task_id, "reviewer": "teacher_2", "output": str(tmp_path / "exam-preview.json")},
    )
    handle_request(
        "POST",
        "/api/grading/import-preview",
        store_path=store_path,
        body={"taskId": exam_task_id, "reviewer": "teacher_2", "output": str(tmp_path / "grading-preview.json")},
    )
    exam_imported = handle_request(
        "POST",
        "/api/exams/mock-import",
        store_path=store_path,
        body={"taskId": exam_task_id, "reviewer": "teacher_2", "output": str(tmp_path / "exam-import.json")},
    )
    grading_imported = handle_request(
        "POST",
        "/api/grading/mock-import",
        store_path=store_path,
        body={"taskId": exam_task_id, "reviewer": "teacher_2", "output": str(tmp_path / "grading-import.json")},
    )

    ppt_generated = handle_request(
        "POST",
        "/api/ppt/generate",
        store_path=store_path,
        body={"input": "examples/input/demo-source.md"},
    )
    ppt_task_id = ppt_generated["data"]["task"]["id"]
    handle_request("POST", f"/api/ai-tasks/{ppt_task_id}/approve", store_path=store_path, body={"reviewer": "teacher_6"})
    handle_request(
        "POST",
        "/api/ppt/import-preview",
        store_path=store_path,
        body={"taskId": ppt_task_id, "reviewer": "teacher_6", "output": str(tmp_path / "ppt-preview.json")},
    )
    ppt_imported = handle_request(
        "POST",
        "/api/ppt/mock-import",
        store_path=store_path,
        body={"taskId": ppt_task_id, "reviewer": "teacher_6", "output": str(tmp_path / "ppt-import.json")},
    )
    entities = [
        lab_imported["data"]["agentEntityRecord"],
        exam_imported["data"]["agentEntityRecord"],
        grading_imported["data"]["agentEntityRecord"],
        ppt_imported["data"]["agentEntityRecord"],
    ]

    server, thread, base_url = start_recording_platform_server()
    try:
        signoff_artifact_ids = {}
        for entity in entities:
            entity_id = entity["id"]
            entity_type = entity["entityType"]
            dry_run = tmp_path / f"{entity_type}-dry-run.json"
            send_report = tmp_path / f"{entity_type}-send.json"
            status_report = tmp_path / f"{entity_type}-status.json"
            result_report = tmp_path / f"{entity_type}-result.json"
            signoff_report = tmp_path / f"{entity_type}-signoff.json"

            handle_request(
                "POST",
                f"/api/platform-entities/{entity_id}/import-dry-run",
                store_path=store_path,
                body={"reviewer": "teacher_3", "output": str(dry_run)},
            )
            handle_request(
                "POST",
                f"/api/platform-entities/{entity_id}/import-send",
                store_path=store_path,
                body={
                    "reviewer": "teacher_3",
                    "dryRun": str(dry_run),
                    "output": str(send_report),
                    "baseUrl": base_url,
                    "explicitPlatformCallOptIn": True,
                    "confirmDryRunReviewed": True,
                    "confirmManualPlatformReview": True,
                    "confirmNoAutoPublish": True,
                },
            )
            handle_request(
                "POST",
                f"/api/platform-entities/{entity_id}/import-status",
                store_path=store_path,
                body={
                    "reviewer": "teacher_4",
                    "sendResult": str(send_report),
                    "output": str(status_report),
                    "explicitPlatformQueryOptIn": True,
                },
            )
            handle_request(
                "POST",
                f"/api/platform-entities/{entity_id}/import-result",
                store_path=store_path,
                body={
                    "reviewer": "teacher_4",
                    "sendResult": str(send_report),
                    "agentStatus": "ACCEPTED_FOR_DRAFT",
                    "output": str(result_report),
                },
            )
            signoff_payload = handle_request(
                "POST",
                f"/api/platform-entities/{entity_id}/signoff",
                store_path=store_path,
                body={
                    "reviewer": "teacher_5",
                    "comment": f"{entity_type} accepted draft checked before local signoff",
                    "output": str(signoff_report),
                },
            )
            assert_api_envelope(signoff_payload)
            assert signoff_payload["data"]["agentEntitySignoffRecord"]["summary"]["signoffRecorded"] is True
            signoff_artifact_ids[entity_id] = signoff_payload["data"]["artifact"]["id"]
    finally:
        stop_recording_platform_server(server, thread)

    payload = handle_request("GET", "/api/platform-entities/readiness-report", store_path=store_path)

    assert_api_envelope(payload)
    report = payload["data"]["agentEntityReadinessReport"]
    assert report["summary"]["requiredTotal"] == 4
    assert report["summary"]["readyForManualAgentReviewTotal"] == 4
    assert report["summary"]["dryRunPreparedTotal"] == 4
    assert report["summary"]["requestSentTotal"] == 4
    assert report["summary"]["statusQueriedTotal"] == 4
    assert report["summary"]["resultRecordedTotal"] == 4
    assert report["summary"]["agentEntitySignoffReadyTotal"] == 0
    assert report["summary"]["agentEntitySignoffRecordedTotal"] == 4
    assert report["summary"]["postSignoffPrePublishReadyTotal"] == 4
    assert report["summary"]["finalPublishReviewDecisionRecordedTotal"] == 0
    assert report["summary"]["approvedForPublishPlanningTotal"] == 0
    assert report["summary"]["needsRevisionTotal"] == 0
    assert report["summary"]["allReadyForManualPlatformReview"] is True
    assert report["summary"]["allPlatformEntitiesReadyForSignoff"] is False
    assert report["summary"]["allPlatformEntitiesSignoffRecorded"] is True
    assert report["summary"]["allPostSignoffPrePublishReady"] is True
    assert report["summary"]["allFinalPublishReviewDecisionsRecorded"] is False
    assert {item["agentEntity"] for item in report["items"]} == {
        "lab_template",
        "exam_question",
        "grading_rule",
        "ppt_deck",
    }
    focus_by_entity = {
        "lab_template": {
            "primary": "review_lab_objectives_environment_and_grading_ref_before_publish",
            "checks": {
                "verify_lab_objectives_and_steps_publishable",
                "verify_lab_environment_and_materials_resolved",
                "confirm_lab_grading_ref_and_duration_reasonable",
            },
        },
        "exam_question": {
            "primary": "review_candidate_safe_exam_preview_and_scoring_before_publish",
            "checks": {
                "confirm_candidate_preview_hides_answers",
                "verify_question_score_and_grading_ref_coverage",
                "confirm_exam_source_lab_traceable",
            },
        },
        "grading_rule": {
            "primary": "review_grading_plan_sandbox_limits_and_evidence_before_publish",
            "checks": {
                "verify_assessment_plan_aligned_with_checks",
                "confirm_sandbox_limits_and_evidence_requirements",
                "confirm_no_contestant_code_execution_before_publish",
            },
        },
        "ppt_deck": {
            "primary": "review_ppt_deck_content_artifact_and_classroom_readiness_before_publish",
            "checks": {
                "verify_ppt_slide_plan_and_titles_publishable",
                "confirm_pptx_artifact_generated_and_reviewed",
                "confirm_ppt_deck_not_auto_published",
            },
        },
    }
    for item in report["items"]:
        assert item["readyForAgentEntitySignoff"] is False
        assert item["signoffRecorded"] is True
        assert item["signoffState"] == "PLATFORM_ENTITY_SIGNOFF_RECORDED"
        assert item["latestSignoffArtifactId"] == signoff_artifact_ids[item["agentEntityId"]]
        assert item["finalPublishReviewDecision"]["component"] == "FinalPublishReviewDecisionSummary"
        assert item["finalPublishReviewDecision"]["recorded"] is False
        assert item["finalPublishReviewDecision"]["safety"]["realPublish"] is False
        checklist = item["postSignoffPrePublishChecklist"]
        assert checklist["component"] == "AgentEntityPostSignoffPrePublishChecklist"
        assert checklist["visible"] is True
        assert checklist["status"] == "READY_FOR_FINAL_HUMAN_PUBLISH_REVIEW"
        assert checklist["matchedTotal"] == checklist["total"]
        assert checklist["blockedTotal"] == 0
        assert checklist["nextRequiredAction"] == "final_human_publish_review_before_any_real_publish"
        assert checklist["safety"]["requiresFinalHumanReview"] is True
        assert checklist["safety"]["realPublish"] is False
        focus = checklist["entitySpecificReviewFocus"]
        expected_focus = focus_by_entity[item["agentEntity"]]
        assert focus["component"] == "AgentEntitySpecificPrePublishReviewFocus"
        assert focus["primaryReviewFocus"] == expected_focus["primary"]
        assert focus["status"] == "READY_FOR_FINAL_HUMAN_REVIEW"
        assert focus["matchedTotal"] == focus["total"] == 3
        assert {check["id"] for check in focus["checks"]} == expected_focus["checks"]
        assert all(check["matched"] is True for check in focus["checks"])
        assert focus["safety"]["answerVisibleToCandidate"] is False
        assert focus["safety"]["contestantCodeExecuted"] is False
        assert focus["safety"]["realPublish"] is False
        assert {check["id"] for check in checklist["checks"]} == {
            "confirm_agent_entity_signoff_recorded",
            "confirm_local_preview_and_mock_import_preserved",
            "confirm_platform_result_accepted_for_draft",
            "confirm_no_auto_publish_or_real_publish",
            "confirm_local_system_did_not_write_real_database",
            "confirm_final_human_publish_review_required",
        }
        assert item["safety"]["realPublish"] is False

    lab_detail = handle_request("GET", f"/api/review-tasks/{lab_task_id}", store_path=store_path)
    exam_detail = handle_request("GET", f"/api/review-tasks/{exam_task_id}", store_path=store_path)

    assert lab_detail["data"]["reviewDetail"]["summary"]["agentEntitySignoffRecordedTotal"] == 1
    assert exam_detail["data"]["reviewDetail"]["summary"]["agentEntitySignoffRecordedTotal"] == 2
    assert (
        lab_detail["data"]["reviewDetail"]["reviewPage"]["agentEntityReadinessReport"]["summary"][
            "allPlatformEntitiesSignoffRecorded"
        ]
        is False
    )
    assert (
        exam_detail["data"]["reviewDetail"]["reviewPage"]["agentEntityReadinessReport"]["summary"][
            "allPlatformEntitiesSignoffRecorded"
        ]
        is False
    )
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "platform-secret-token" not in serialized


def test_real_dsl_revision_api_real_llm_requires_confirmations(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-redacted")
    output = tmp_path / "api-real-provider-revision.json"

    payload = handle_request(
        "POST",
        "/api/review/real-dsl-revision",
        store_path=tmp_path / "store.json",
        body={
            "kind": "lab",
            "source": "examples/output/real-llm-lab.json",
            "reviewer": "teacher_1",
            "comment": "请用真实 LLM 重新组织步骤说明。",
            "providerMode": "real-llm",
            "model": "test-model",
            "baseUrl": "https://example.test/v1",
            "output": str(output),
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "REAL_LLM_DEMO_DSL_CONFIRMATION_REQUIRED"
    assert payload["providerErrorContext"]["adapterId"] == "mock_provider_adapter"
    assert payload["providerErrorContext"]["operation"] == "reviseDsl"
    assert payload["providerErrorContext"]["providerId"] == "openai"
    assert payload["providerErrorContext"]["realLlmCalled"] is False
    assert payload["providerErrorContext"]["autoPublishAllowed"] is False
    assert not output.exists()


def test_real_dsl_revision_api_rejects_get(tmp_path):
    payload = handle_request("GET", "/api/review/real-dsl-revision", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"
    assert payload["errors"][0]["field"] == "method"


def test_review_task_summary_filters_and_limits(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    handle_request("POST", "/api/labs/generate", store_path=store_path, body={"input": str(source)})
    handle_request("POST", "/api/ppt/generate", store_path=store_path, body={"input": str(source)})

    payload = handle_request(
        "GET",
        "/api/review-task-summary?taskType=PPT_GENERATION&limit=1",
        store_path=store_path,
    )

    assert_api_envelope(payload)
    summary = payload["data"]["reviewTaskSummary"]
    assert summary["total"] == 1
    assert summary["filters"]["taskType"] == "PPT_GENERATION"
    assert summary["filters"]["limit"] == 1
    assert summary["items"][0]["task"]["taskType"] == "PPT_GENERATION"
    assert summary["items"][0]["reviewPageSummary"]["providerQualitySummary"]["available"] is False
    provider_signal = summary["providerQualityTaskSignal"]
    assert provider_signal["taskTotal"] == 1
    assert provider_signal["availableTotal"] == 0
    assert provider_signal["autoApproveAllowed"] is False
    assert provider_signal["realPublishAllowed"] is False
    priority_queue = summary["reviewPriorityQueue"]
    assert priority_queue["summary"]["queueTotal"] == 1
    assert priority_queue["summary"]["providerQualityAvailableTotal"] == 0
    assert priority_queue["summary"]["providerQualityReadyForReviewTotal"] == 0
    assert priority_queue["items"][0]["taskType"] == "PPT_GENERATION"
    assert priority_queue["items"][0]["reasonCode"] == "PPT_SLIDE_PLAN_REVIEW"
    assert priority_queue["items"][0]["providerQualitySummary"]["available"] is False


def test_review_task_summary_supports_light_detail_mode(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    handle_request("POST", "/api/labs/generate", store_path=store_path, body={"input": str(source)})
    handle_request("POST", "/api/ppt/generate", store_path=store_path, body={"input": str(source)})

    payload = handle_request(
        "GET",
        "/api/review-task-summary?limit=1&detailMode=light",
        store_path=store_path,
    )

    assert_api_envelope(payload)
    summary = payload["data"]["reviewTaskSummary"]
    assert summary["detailMode"] == "LIGHT"
    assert summary["filters"]["detailMode"] == "light"
    assert summary["total"] == 1
    assert summary["queueSummary"]["waitingReviewTotal"] == 2
    assert summary["items"][0]["reviewPolicy"]["detailMode"] == "LIGHT"
    assert summary["items"][0]["reviewPolicy"]["detailApi"] == "GET /api/review-tasks/{id}"
    assert summary["items"][0]["reviewPageSummary"]["detailMode"] == "LIGHT"
    assert summary["items"][0]["reviewPageSummary"]["providerQualitySummary"]["source"] == (
        "reviewTaskSummary.detailMode=light"
    )
    priority_queue = summary["reviewPriorityQueue"]
    assert priority_queue["summary"]["detailMode"] == "LIGHT"
    assert priority_queue["summary"]["queueTotal"] == 1
    assert priority_queue["items"][0]["recommendedAction"] == "open_review_detail_before_approval"
    assert summary["providerQualityTaskSignal"]["source"] == "reviewTaskSummary.detailMode=light"
    assert summary["batchActionPolicy"]["batchApproveAllowed"] is False
    assert summary["safety"]["realPublish"] is False


def test_review_task_summary_includes_grading_manual_checklist_summary(tmp_path):
    store_path = tmp_path / "store.json"
    handle_request(
        "POST",
        "/api/phase2/workflows/grading-generation/run",
        store_path=store_path,
        body={
            "exam": "templates/exam/examples/notebook-fill-blank.yaml",
            "reviewer": "teacher_1",
        },
    )

    payload = handle_request(
        "GET",
        "/api/review-task-summary?taskType=GRADING_GENERATION",
        store_path=store_path,
    )

    assert_api_envelope(payload)
    summary = payload["data"]["reviewTaskSummary"]
    priority_queue = summary["reviewPriorityQueue"]
    assert priority_queue["summary"]["queueTotal"] == 1
    assert priority_queue["summary"]["urgentTotal"] == 1
    assert priority_queue["summary"]["manualReviewChecklistTaskTotal"] == 1
    assert priority_queue["summary"]["manualReviewChecklistNeedsHumanReviewTotal"] == 5
    item = priority_queue["items"][0]
    assert item["reasonCode"] == "HIGH_RISK_MOCK_EVIDENCE_REQUIRED"
    assert item["recommendedAction"] == "review_assessment_plan_before_approval"
    assert item["providerQualitySummary"]["source"] == "reviewDetail.reviewPage.providerSummary.qualitySummary"
    assert item["providerQualitySummary"]["available"] is False
    assert item["providerQualitySummary"]["autoPublishAllowed"] is False
    assert item["providerQualitySummary"]["realPublishAllowed"] is False
    checklist_summary = item["manualReviewChecklistSummary"]
    assert checklist_summary["enabled"] is True
    assert checklist_summary["taskId"] == item["taskId"]
    assert checklist_summary["status"] == "NEEDS_HUMAN_REVIEW"
    assert checklist_summary["checklistTotal"] == 5
    assert checklist_summary["matchedTotal"] == 5
    assert checklist_summary["needsHumanReviewTotal"] == 5
    assert checklist_summary["checklistIds"] == checklist_summary["nextReviewChecklistIds"]
    assert checklist_summary["operatorDecision"]["manualDecisionRequired"] is True
    assert checklist_summary["operatorDecision"]["autoApproveAllowed"] is False
    assert checklist_summary["operatorDecision"]["batchStateChangeAllowed"] is False
    assert checklist_summary["operatorDecision"]["contestantCodeExecuted"] is False
    readiness = item["gradingEvidenceReadinessSummary"]
    assert readiness["component"] == "GradingEvidenceReadiness"
    assert readiness["available"] is False
    assert readiness["status"] == "NO_MERGED_EVIDENCE_REPORT"
    assert readiness["summary"]["evidenceReadyTotal"] == 0
    assert readiness["summary"]["missingEvidenceTotal"] == 0
    assert readiness["safety"]["sandboxExecutedByReadiness"] is False
    assert readiness["actionGuide"]["component"] == "GradingEvidenceActionGuide"
    assert readiness["actionGuide"]["status"] == "EVIDENCE_COLLECTION_RECOMMENDED"
    assert readiness["actionGuide"]["api"]["path"] == "/api/grading/evidence-auto"
    assert "grade evidence-auto" in readiness["actionGuide"]["cli"]
    assert readiness["actionGuide"]["safety"]["autoApproveAllowed"] is False
    readiness_signal = summary["gradingEvidenceReadinessSignal"]
    assert readiness_signal["component"] == "GradingEvidenceReadinessSignal"
    assert readiness_signal["taskTotal"] == 1
    assert readiness_signal["availableTotal"] == 0
    assert readiness_signal["autoApproveAllowed"] is False


def test_review_task_summary_rejects_invalid_limit(tmp_path):
    payload = handle_request("GET", "/api/review-task-summary?limit=0", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "limit"


def test_review_task_summary_rejects_unknown_status(tmp_path):
    payload = handle_request("GET", "/api/review-task-summary?status=UNKNOWN", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "status"


def test_review_task_summary_rejects_unknown_detail_mode(tmp_path):
    payload = handle_request(
        "GET",
        "/api/review-task-summary?detailMode=unknown",
        store_path=tmp_path / "store.json",
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "detailMode"


def test_review_task_detail_returns_artifacts_and_policy(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    created = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": str(source)},
    )
    task_id = created["data"]["task"]["id"]

    payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)

    assert_api_envelope(payload)
    detail = payload["data"]["reviewDetail"]
    assert detail["mode"] == "MOCK_ONLY"
    assert detail["task"]["id"] == task_id
    assert detail["summary"]["artifactTotal"] == 2
    assert {artifact["kind"] for artifact in detail["artifacts"]} == {"MATERIAL_ANALYSIS", "LAB_DSL"}
    assert detail["reviewPolicy"]["reviewRequired"] is True
    assert detail["reviewPolicy"]["allowedActions"] == ["approve", "reject", "request_revision"]
    assert detail["safety"]["realPublish"] is False
    assert detail["reviewPage"]["header"]["taskId"] == task_id
    assert detail["reviewPage"]["dslPreview"]["artifactKind"] == "LAB_DSL"
    assert detail["reviewPage"]["riskSummary"]["unknownShellExecuted"] is False
    assert detail["reviewPage"]["actionBar"]["approve"]["enabled"] is True
    assert detail["reviewPage"]["actionBar"]["requestRevision"]["enabled"] is True
    assert detail["reviewPage"]["actionBar"]["mockPublish"]["enabled"] is False
    assert detail["preApproveReviewCheck"]["applicable"] is False
    assert detail["preApproveReviewCheck"]["summary"]["approveReadyDecision"] is False
    assert detail["reviewPage"]["preApproveReviewCheck"] == detail["preApproveReviewCheck"]


def test_review_task_detail_loads_real_dsl_preview_summary(tmp_path):
    store_path = tmp_path / "store.json"
    lab_path = tmp_path / "real-lab.json"
    lab_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "kind": "Lab",
                "status": "WAITING_REVIEW",
                "metadata": {
                    "id": "lab_real_preview",
                    "title": "真实预览实验",
                    "category": "ai-platform",
                    "difficulty": "beginner",
                    "durationMinutes": 45,
                },
                "spec": {
                    "steps": [
                        {"id": "step_1", "title": "环境检查", "instruction": "检查 Python", "expectedResult": "可运行"},
                        {"id": "step_2", "title": "运行代码", "instruction": "执行脚本", "expectedResult": "输出正确"},
                    ],
                    "objectives": ["理解真实 DSL 预览"],
                    "targetUsers": ["teacher"],
                    "environment": {"type": "notebook", "image": "python:3.11"},
                    "materials": [{"type": "markdown", "path": "examples/input/demo-source.md"}],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Real DSL preview task",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path=str(lab_path),
    )
    artifact = create_artifact_record(
        kind=ArtifactKind.LAB_DSL,
        path=str(lab_path),
        title="Real Lab DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        task_id=task.id,
        trace_id=task.traceId,
        metadata={"dslKind": "Lab", "providerAdapter": "openai_responses_sdk_demo_adapter"},
    )
    store = JsonTaskStore(store_path)
    store.save(task)
    store.save_artifact(artifact)

    payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(payload)
    detail = payload["data"]["reviewDetail"]
    preview = detail["reviewPage"]["dslPreview"]
    assert detail["mode"] == "REAL_LLM_DEMO_WORKFLOW"
    assert preview["contentLoaded"] is True
    assert preview["contentSource"] == "local_dsl_file"
    assert preview["schemaKind"] == "lab"
    assert preview["schemaValidated"] is True
    assert preview["documentKind"] == "Lab"
    assert preview["documentStatus"] == "WAITING_REVIEW"
    assert preview["title"] == "真实预览实验"
    assert preview["summary"]["stepTotal"] == 2
    assert preview["summary"]["objectiveTotal"] == 1
    assert preview["summary"]["environmentType"] == "notebook"
    assert preview["safePreview"]["stepTitles"] == ["环境检查", "运行代码"]
    assert preview["candidateSafety"]["answerVisibleToCandidate"] is False
    assert preview["candidateSafety"]["gradingRefVisibleToCandidate"] is False
    assert preview["reviewSafety"]["readOnly"] is True
    assert preview["reviewSafety"]["networkAccess"] is False
    assert preview["reviewSafety"]["autoPublishAllowed"] is False
    assert detail["summary"]["dslPreviewContentLoaded"] is True
    assert detail["summary"]["dslPreviewSchemaValidated"] is True
    assert detail["summary"]["dslPreviewTitle"] == "真实预览实验"


def test_review_task_detail_redacts_exam_answers_from_dsl_safe_preview(tmp_path):
    store_path = tmp_path / "store.json"
    exam_path = tmp_path / "real-exam.json"
    exam_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "kind": "Exam",
                "status": "WAITING_REVIEW",
                "metadata": {"id": "exam_real_preview", "title": "真实预览试题"},
                "spec": {
                    "questionType": "coding_task",
                    "totalScore": 100,
                    "questions": [
                        {
                            "id": "q1",
                            "title": "实现函数",
                            "stem": "请实现 add 函数",
                            "score": 100,
                            "answer": "return a + b",
                            "gradingRef": "check_add",
                        }
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    task = create_waiting_review_task(
        task_type="EXAM_GENERATION",
        title="Real Exam preview task",
        input_type="lab-dsl",
        input_ref="examples/output/real-llm-lab.json",
        final_result_path=str(exam_path),
    )
    artifact = create_artifact_record(
        kind=ArtifactKind.EXAM_DSL,
        path=str(exam_path),
        title="Real Exam DSL",
        status=ArtifactStatus.WAITING_REVIEW,
        task_id=task.id,
        trace_id=task.traceId,
        metadata={"dslKind": "Exam", "answerVisibleToCandidate": False},
    )
    store = JsonTaskStore(store_path)
    store.save(task)
    store.save_artifact(artifact)

    payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(payload)
    preview = payload["data"]["reviewDetail"]["reviewPage"]["dslPreview"]
    assert preview["contentLoaded"] is True
    assert preview["summary"]["questionTotal"] == 1
    assert preview["summary"]["answerFieldTotal"] == 1
    assert preview["summary"]["teacherGradingRefTotal"] == 1
    assert preview["safePreview"]["questions"][0]["answerPresent"] is True
    assert "answer" not in preview["safePreview"]["questions"][0]
    assert "gradingRef" not in preview["safePreview"]["questions"][0]
    assert preview["candidateSafety"]["answersRemovedFromSafePreview"] is True
    assert preview["candidateSafety"]["answerVisibleToCandidate"] is False
    assert preview["candidateSafety"]["gradingRefVisibleToCandidate"] is False


def test_review_task_revision_request_records_feedback_without_status_change(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Mock Lab Review",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/lab-dsl.yaml",
    )
    store = JsonTaskStore(store_path)
    store.save(task)

    payload = handle_request(
        "POST",
        f"/api/review-tasks/{task.id}/revision-request",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "comment": "补充评分点说明。",
            "priority": "HIGH",
            "targetSections": ["grading"],
            "requestedChanges": ["增加评分 rubrics"],
        },
    )

    assert_api_envelope(payload)
    assert payload["data"]["task"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["revisionRequest"]["taskId"] == task.id
    assert payload["data"]["revisionRequest"]["priority"] == "HIGH"
    assert payload["data"]["revisionRequest"]["targetSections"] == ["grading"]
    assert payload["data"]["revisionRequest"]["newLlmRequestSent"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "REVIEW_REVISION_REQUEST"
    assert payload["data"]["operationAuditEvent"]["beforeState"] == "WAITING_REVIEW"
    assert payload["data"]["operationAuditEvent"]["afterState"] == "WAITING_REVIEW"

    list_payload = handle_request("GET", f"/api/review-tasks/{task.id}/revision-requests", store_path=store_path)
    assert_api_envelope(list_payload)
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["comment"] == "补充评分点说明。"

    detail_payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["revisionRequests"]["total"] == 1
    assert detail["reviewPage"]["revisionRequests"]["highPriorityCount"] == 1
    assert detail["reviewPage"]["actionBar"]["requestRevision"]["enabled"] is True
    assert detail["reviewPage"]["actionBar"]["requestRevision"]["changesTaskStatus"] is False


def test_review_task_revision_request_requires_comment(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Mock Lab Review",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    JsonTaskStore(store_path).save(task)

    payload = handle_request(
        "POST",
        f"/api/review-tasks/{task.id}/revision-request",
        store_path=store_path,
        body={"reviewer": "teacher_1", "comment": ""},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "comment"


def test_review_task_regenerate_mock_creates_new_review_task(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    created = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": str(source)},
    )
    source_task_id = created["data"]["task"]["id"]
    revision_payload = handle_request(
        "POST",
        f"/api/review-tasks/{source_task_id}/revision-request",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "comment": "补充截图验收标准。",
            "targetSections": ["steps"],
        },
    )
    revision_request_id = revision_payload["data"]["revisionRequest"]["id"]
    output_path = tmp_path / "api-lab-revision.json"

    payload = handle_request(
        "POST",
        f"/api/review-tasks/{source_task_id}/regenerate-mock",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "revisionRequestId": revision_request_id,
            "output": str(output_path),
        },
    )

    assert_api_envelope(payload)
    regeneration = payload["data"]["mockRegeneration"]
    assert regeneration["sourceTask"]["id"] == source_task_id
    assert regeneration["sourceTask"]["status"] == "WAITING_REVIEW"
    assert regeneration["newTask"]["status"] == "WAITING_REVIEW"
    assert regeneration["newTask"]["taskType"] == "LAB_GENERATION_REVISION"
    assert regeneration["artifact"]["metadata"]["sourceRevisionRequestId"] == revision_request_id
    assert regeneration["artifact"]["metadata"]["contentQualitySummary"]["readyForImportPreview"] is True
    assert regeneration["artifact"]["metadata"]["workflowContentQualitySummary"]["requiresRevisionBeforeImportPreview"] is False
    assert regeneration["workflowRun"]["workflowId"] == "review_mock_regeneration"
    assert regeneration["operationAuditEvent"]["action"] == "REVIEW_MOCK_REGENERATE"
    assert regeneration["safety"]["newLlmRequestSent"] is False
    assert output_path.exists()

    detail_payload = handle_request("GET", f"/api/review-tasks/{regeneration['newTask']['id']}", store_path=store_path)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["summary"]["artifactTotal"] == 1
    assert detail["summary"]["workflowRunTotal"] == 1
    assert detail["reviewPage"]["dslPreview"]["artifactKind"] == "LAB_DSL"
    assert detail["reviewPage"]["contentQualitySummary"]["available"] is True
    assert detail["reviewPage"]["contentQualitySummary"]["requiresRevisionBeforeImportPreview"] is False
    assert detail["reviewPage"]["contentQualitySummary"]["items"]["lab"]["readyForImportPreview"] is True

    core_payload = handle_request(
        "GET",
        f"/api/review-tasks/{regeneration['newTask']['id']}/core-readiness",
        store_path=store_path,
    )
    core_report = core_payload["data"]["coreWorkflowReadinessReport"]
    assert core_report["contentQualityReadiness"]["readyForImportPreview"] is True
    assert core_report["nextToolRecommendation"]["reasonCode"] == "HUMAN_APPROVAL_REQUIRED"


def test_review_task_regenerate_mock_requires_revision_request(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    created = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": str(source)},
    )
    source_task_id = created["data"]["task"]["id"]

    payload = handle_request(
        "POST",
        f"/api/review-tasks/{source_task_id}/regenerate-mock",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "REVISION_REQUEST_NOT_FOUND"


def test_review_task_ppt_page_status_returns_page_review_model(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="PPT_ARTIFACT_GENERATION",
        title="Mock PPTX artifact review",
        input_type="ppt_dsl",
        input_ref="templates/ppt/examples/course-ppt.yaml",
        final_result_path="examples/output/ppt-artifact-demo.pptx",
    )
    store = JsonTaskStore(store_path)
    store.save(task)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.PPTX_FILE,
            path="examples/output/ppt-artifact-demo.pptx",
            title="Mock PPTX Artifact",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id=task.traceId,
            task_id=task.id,
            source_ref="templates/ppt/examples/course-ppt.yaml",
            metadata={
                "slideCount": 2,
                "pageReviewSummary": {
                    "status": "NEEDS_REVIEW",
                    "total": 2,
                    "approved": 0,
                    "needsReview": 2,
                    "reviseRequired": 0,
                    "manualCommentTotal": 2,
                    "qaSignalStatus": "NEEDS_REVIEW",
                    "autoApproveAllowed": False,
                    "realPublishAllowed": False,
                },
                "slidePreviews": [
                    {
                        "index": 1,
                        "id": "slide_1",
                        "title": "AI 工具应用课程",
                        "imagePath": "examples/output/ppt-artifact-demo-slide-01.png",
                        "reviewStatus": "NEEDS_REVIEW",
                        "manualComment": {"required": True, "text": "请确认封面。"},
                        "qaSignals": {"layout": "NEEDS_REVIEW", "reviewFocus": "cover"},
                    }
                ],
            },
        )
    )

    detail_payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)
    status_payload = handle_request(
        "GET",
        f"/api/review-tasks/{task.id}/ppt-page-review-status",
        store_path=store_path,
    )

    assert_api_envelope(detail_payload)
    assert_api_envelope(status_payload)
    detail_review = detail_payload["data"]["reviewDetail"]["pptPageReview"]
    page_review = status_payload["data"]["pptPageReview"]
    assert detail_review["available"] is True
    assert detail_review["pageReviewSummary"]["status"] == "NEEDS_REVIEW"
    assert page_review["artifactKind"] == "PPTX_FILE"
    assert page_review["pageReviewSummary"]["total"] == 2
    assert page_review["slideReviews"][0]["reviewStatus"] == "NEEDS_REVIEW"
    assert page_review["slideReviews"][0]["manualComment"]["required"] is True
    assert page_review["operatorDecision"]["autoApproveAllowed"] is False
    assert page_review["operatorDecision"]["realPublishAllowed"] is False

    update_payload = handle_request(
        "POST",
        f"/api/review-tasks/{task.id}/ppt-page-review-status",
        store_path=store_path,
        body={
            "slideIndex": 1,
            "reviewStatus": "REVISE_REQUIRED",
            "reviewer": "teacher_1",
            "comment": "需要补充操作截图。",
        },
    )
    audit_payload = handle_request(
        "GET",
        "/api/audit-events?action=PPT_PAGE_REVIEW_UPDATE",
        store_path=store_path,
    )
    updated_status = handle_request(
        "GET",
        f"/api/review-tasks/{task.id}/ppt-page-review-status",
        store_path=store_path,
    )

    assert_api_envelope(update_payload)
    updated_review = update_payload["data"]["pptPageReviewUpdate"]["pptPageReview"]
    assert updated_review["pageReviewSummary"]["status"] == "REVISE_REQUIRED"
    assert updated_review["pageReviewSummary"]["reviseRequired"] == 1
    assert updated_review["slideReviews"][0]["reviewStatus"] == "REVISE_REQUIRED"
    assert updated_review["slideReviews"][0]["manualComment"]["text"] == "需要补充操作截图。"
    assert update_payload["data"]["pptPageReviewUpdate"]["operationAuditEvent"]["action"] == "PPT_PAGE_REVIEW_UPDATE"
    assert update_payload["data"]["pptPageReviewUpdate"]["safety"]["taskStatusChanged"] is False
    assert audit_payload["data"]["total"] == 1
    assert audit_payload["data"]["items"][0]["detail"]["toReviewStatus"] == "REVISE_REQUIRED"
    assert updated_status["data"]["pptPageReview"]["pageReviewSummary"]["status"] == "REVISE_REQUIRED"


def test_review_task_detail_after_approval_includes_audit(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Mock lab",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
    )
    JsonTaskStore(store_path).save(task)
    handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )

    payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(payload)
    detail = payload["data"]["reviewDetail"]
    assert detail["task"]["status"] == "APPROVED"
    assert detail["reviewPolicy"]["publishBlockedUntilApproved"] is False
    assert detail["reviewPolicy"]["allowedActions"] == ["mock_publish"]
    assert detail["summary"]["reviewAuditEventTotal"] == 1
    assert detail["summary"]["operationAuditEventTotal"] == 1
    assert detail["reviewAuditEvents"][0]["action"] == "APPROVE"
    assert detail["operationAuditEvents"][0]["action"] == "REVIEW_APPROVE"


def test_review_task_detail_includes_high_risk_mcp_intent_audit(tmp_path):
    store_path = tmp_path / "store.json"
    created = handle_request(
        "POST",
        "/api/mcp/intents/publish-lab",
        store_path=store_path,
        body={"labId": "lab_demo", "reason": "运营申请发布", "actor": "operator_1"},
    )
    task_id = created["data"]["task"]["id"]

    payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)

    assert_api_envelope(payload)
    detail = payload["data"]["reviewDetail"]
    assert detail["task"]["taskType"] == "MCP_PUBLISH_LAB_INTENT"
    assert detail["reviewPolicy"]["highRiskIntent"] is True
    assert detail["reviewPolicy"]["reviewIntentOnly"] is True
    assert detail["highRiskIntent"]["intentType"] == "publish_lab"
    assert detail["highRiskIntent"]["resourceType"] == "LAB"
    assert detail["highRiskIntent"]["resourceId"] == "lab_demo"
    assert detail["highRiskIntent"]["realActionExecuted"] is False
    assert detail["highRiskIntent"]["realPublish"] is False
    disposition = detail["highRiskIntent"]["postReviewDisposition"]
    assert disposition["state"] == "WAITING_HUMAN_REVIEW"
    assert disposition["nextRequiredAction"] == "approve_or_reject"
    assert disposition["executionBlocked"] is True
    assert disposition["executeRealActionAllowed"] is False
    assert detail["reviewPolicy"]["postReviewDispositionState"] == "WAITING_HUMAN_REVIEW"
    assert detail["summary"]["operationAuditEventTotal"] == 1
    assert detail["summary"]["highRiskIntentAuditEventTotal"] == 1
    assert detail["operationAuditEvents"][0]["action"] == "PUBLISH_LAB_INTENT"
    assert detail["operationAuditEvents"][0]["detail"]["createdTaskId"] == task_id
    assert detail["reviewPage"]["highRiskIntentPanel"]["visible"] is True
    assert detail["reviewPage"]["highRiskIntentPanel"]["postReviewState"] == "WAITING_HUMAN_REVIEW"
    assert detail["reviewPage"]["highRiskIntentPanel"]["executionBlocked"] is True
    assert detail["reviewPage"]["highRiskIntentPanel"]["executeRealPublishEnabled"] is False
    assert detail["safety"]["highRiskIntentExecutionAllowed"] is False


def test_review_task_detail_for_approved_publish_intent_keeps_real_publish_blocked(tmp_path):
    store_path = tmp_path / "store.json"
    created = handle_request(
        "POST",
        "/api/mcp/intents/publish-lab",
        store_path=store_path,
        body={"labId": "lab_demo", "reason": "运营申请发布", "actor": "operator_1"},
    )
    task_id = created["data"]["task"]["id"]
    handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )

    payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)

    assert_api_envelope(payload)
    detail = payload["data"]["reviewDetail"]
    assert detail["task"]["status"] == "APPROVED"
    assert detail["reviewPolicy"]["allowedActions"] == []
    assert detail["reviewPolicy"]["postReviewDispositionState"] == "APPROVED_EXECUTION_BLOCKED"
    disposition = detail["highRiskIntent"]["postReviewDisposition"]
    assert disposition["state"] == "APPROVED_EXECUTION_BLOCKED"
    assert disposition["nextRequiredAction"] == "mock_disposition_only"
    assert disposition["executionBlocked"] is True
    assert disposition["executeRealPublishEnabled"] is False
    assert disposition["realPublish"] is False
    assert detail["reviewPage"]["actionBar"]["mockPublish"]["enabled"] is False
    assert detail["reviewPage"]["highRiskIntentPanel"]["postReviewState"] == "APPROVED_EXECUTION_BLOCKED"
    assert detail["reviewPage"]["highRiskIntentPanel"]["executeRealPublishEnabled"] is False


def test_review_task_detail_for_destroy_environment_intent_requires_second_confirmation(tmp_path):
    store_path = tmp_path / "store.json"
    created = handle_request(
        "POST",
        "/api/mcp/intents/destroy-environment",
        store_path=store_path,
        body={"environmentId": "env_demo", "reason": "清理申请", "actor": "operator_1"},
    )
    task_id = created["data"]["task"]["id"]
    handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )

    payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)

    assert_api_envelope(payload)
    detail = payload["data"]["reviewDetail"]
    assert detail["task"]["status"] == "APPROVED"
    assert detail["reviewPolicy"]["allowedActions"] == []
    assert detail["reviewPolicy"]["postReviewDispositionState"] == "APPROVED_PENDING_SECOND_CONFIRMATION"
    assert detail["reviewPolicy"]["secondConfirmationRequired"] is True
    assert detail["highRiskIntent"]["intentType"] == "destroy_environment"
    assert detail["highRiskIntent"]["requiresSecondConfirmation"] is True
    disposition = detail["highRiskIntent"]["postReviewDisposition"]
    assert disposition["state"] == "APPROVED_PENDING_SECOND_CONFIRMATION"
    assert disposition["nextRequiredAction"] == "second_confirmation"
    assert disposition["secondConfirmationRequired"] is True
    assert disposition["secondConfirmationSatisfied"] is False
    assert disposition["executionBlocked"] is True
    assert detail["highRiskIntent"]["environmentDestroyed"] is False
    assert detail["highRiskIntent"]["realCloudResourceChanged"] is False
    assert detail["reviewPage"]["actionBar"]["mockPublish"]["enabled"] is False
    assert (
        detail["reviewPage"]["highRiskIntentPanel"]["postReviewState"]
        == "APPROVED_PENDING_SECOND_CONFIRMATION"
    )
    assert detail["reviewPage"]["highRiskIntentPanel"]["secondConfirmationRequired"] is True
    assert detail["reviewPage"]["highRiskIntentPanel"]["secondConfirmationSatisfied"] is False
    assert detail["reviewPage"]["highRiskIntentPanel"]["destroyRealEnvironmentEnabled"] is False


def test_review_task_second_confirmation_status_for_destroy_intent_is_read_only(tmp_path):
    store_path = tmp_path / "store.json"
    created = handle_request(
        "POST",
        "/api/mcp/intents/destroy-environment",
        store_path=store_path,
        body={"environmentId": "env_demo", "reason": "清理申请", "actor": "operator_1"},
    )
    task_id = created["data"]["task"]["id"]
    handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )

    payload = handle_request(
        "GET",
        f"/api/review-tasks/{task_id}/second-confirmation-status",
        store_path=store_path,
    )

    assert_api_envelope(payload)
    status = payload["data"]["secondConfirmationStatus"]
    assert status["mode"] == "MOCK_ONLY"
    assert status["eligible"] is True
    assert status["intent"]["intentType"] == "destroy_environment"
    assert status["state"] == "APPROVED_PENDING_SECOND_CONFIRMATION"
    assert status["nextRequiredAction"] == "second_confirmation"
    assert status["secondConfirmationRequired"] is True
    assert status["secondConfirmationSatisfied"] is False
    assert status["readOnly"] is True
    assert status["confirmationActionAvailable"] is False
    assert status["confirmationEndpointEnabled"] is False
    assert status["executeRealActionAllowed"] is False
    assert status["destroyRealEnvironmentEnabled"] is False
    assert status["realCloudResourceChanged"] is False
    assert status["environmentDestroyed"] is False
    assert "destroyRealEnvironment" in status["blockedActions"]


def test_review_task_second_confirmation_status_rejects_non_second_confirmation_intent(tmp_path):
    store_path = tmp_path / "store.json"
    created = handle_request(
        "POST",
        "/api/mcp/intents/publish-lab",
        store_path=store_path,
        body={"labId": "lab_demo", "reason": "运营申请发布", "actor": "operator_1"},
    )
    task_id = created["data"]["task"]["id"]

    payload = handle_request(
        "GET",
        f"/api/review-tasks/{task_id}/second-confirmation-status",
        store_path=store_path,
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "taskId"


def test_review_task_second_confirmation_status_not_found_returns_json(tmp_path):
    payload = handle_request(
        "GET",
        "/api/review-tasks/task_missing/second-confirmation-status",
        store_path=tmp_path / "store.json",
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"][0]["field"] == "taskId"


def test_review_task_detail_includes_workflow_steps(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    demo = handle_request(
        "POST",
        "/api/workflow/demo",
        store_path=store_path,
        body={"input": str(source), "reviewer": "teacher_1"},
    )
    task_id = demo["data"]["createdTasks"][0]["id"]
    run_id = demo["data"]["workflowRun"]["id"]

    payload = handle_request("GET", f"/api/review-tasks/{task_id}", store_path=store_path)

    assert_api_envelope(payload)
    detail = payload["data"]["reviewDetail"]
    assert detail["summary"]["workflowRunTotal"] == 1
    assert detail["workflowRuns"][0]["id"] == run_id
    assert detail["workflowSteps"][0]["workflowRunId"] == run_id
    assert detail["workflowSteps"][0]["name"] == "generate_lab_dsl"
    assert detail["workflowSteps"][0]["detail"]["taskId"] == task_id


def test_review_task_detail_not_found_returns_json(tmp_path):
    payload = handle_request("GET", "/api/review-tasks/task_missing", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"][0]["field"] == "taskId"


def test_environments_list_and_get(tmp_path):
    store_path = tmp_path / "store.json"
    environment = EnvironmentInstance(envType=EnvironmentType.VM, title="Ubuntu VM", image="ubuntu-22.04")
    JsonTaskStore(store_path).save_environment(environment)

    listed = handle_request("GET", "/api/environments?type=vm", store_path=store_path)
    fetched = handle_request("GET", f"/api/environments/{environment.id}", store_path=store_path)

    assert_api_envelope(listed)
    assert listed["data"]["total"] == 1
    assert fetched["data"]["environment"]["id"] == environment.id


def test_environment_create_vm_persists_mock_record(tmp_path):
    store_path = tmp_path / "store.json"

    payload = handle_request(
        "POST",
        "/api/environments/vm",
        store_path=store_path,
        body={
            "title": "Ubuntu VM",
            "image": "ubuntu-22.04",
            "resources": {"cpu": 4, "memoryGb": 8},
        },
    )
    env_id = payload["data"]["environment"]["id"]
    fetched = handle_request("GET", f"/api/environments/{env_id}", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["environment"]["envType"] == "vm"
    assert payload["data"]["environment"]["status"] == "CREATED"
    assert payload["data"]["environment"]["resources"] == {"cpu": 4, "memoryGb": 8}
    assert payload["data"]["operationAuditEvent"]["action"] == "ENV_CREATE"
    assert payload["data"]["operationAuditEvent"]["realCloudResourceChanged"] is False
    assert fetched["data"]["environment"]["id"] == env_id


def test_environment_create_notebook_uses_default_resources(tmp_path):
    payload = handle_request(
        "POST",
        "/api/environments/notebook",
        store_path=tmp_path / "store.json",
        body={"title": "Notebook", "image": "python-3.11"},
    )

    assert_api_envelope(payload)
    assert payload["data"]["environment"]["envType"] == "notebook"
    assert payload["data"]["environment"]["resources"] == {"cpu": 2, "memoryGb": 4}


def test_environment_create_requires_image(tmp_path):
    payload = handle_request(
        "POST",
        "/api/environments/vm",
        store_path=tmp_path / "store.json",
        body={"title": "Ubuntu VM"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "image"


def test_environment_create_rejects_invalid_resources(tmp_path):
    payload = handle_request(
        "POST",
        "/api/environments/notebook",
        store_path=tmp_path / "store.json",
        body={"title": "Notebook", "image": "python-3.11", "resources": {"cpu": 0}},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "cpu"


def test_environment_create_requires_post(tmp_path):
    payload = handle_request("GET", "/api/environments/vm", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_environment_start_updates_status(tmp_path):
    store_path = tmp_path / "store.json"
    environment = EnvironmentInstance(envType=EnvironmentType.VM, title="Ubuntu VM", image="ubuntu-22.04")
    JsonTaskStore(store_path).save_environment(environment)

    payload = handle_request("POST", f"/api/environments/{environment.id}/start", store_path=store_path)
    fetched = handle_request("GET", f"/api/environments/{environment.id}", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["environment"]["status"] == "RUNNING"
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["operationAuditEvent"]["action"] == "ENV_START"
    assert payload["data"]["operationAuditEvent"]["realCloudResourceChanged"] is False
    assert fetched["data"]["environment"]["status"] == "RUNNING"


def test_environment_reset_finishes_stopped(tmp_path):
    store_path = tmp_path / "store.json"
    environment = EnvironmentInstance(
        envType=EnvironmentType.NOTEBOOK,
        title="Notebook",
        image="python-3.11",
        status=EnvironmentStatus.RUNNING,
    )
    JsonTaskStore(store_path).save_environment(environment)

    payload = handle_request("POST", f"/api/environments/{environment.id}/reset", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["environment"]["status"] == "STOPPED"


def test_environment_illegal_transition_returns_json(tmp_path):
    store_path = tmp_path / "store.json"
    environment = EnvironmentInstance(
        envType=EnvironmentType.VM,
        title="Ubuntu VM",
        image="ubuntu-22.04",
        status=EnvironmentStatus.STOPPED,
    )
    JsonTaskStore(store_path).save_environment(environment)

    payload = handle_request("POST", f"/api/environments/{environment.id}/stop", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "STATE_TRANSITION_ERROR"


def test_environment_action_requires_post(tmp_path):
    payload = handle_request("GET", "/api/environments/env_demo/start", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_workflow_report_reads_local_json(tmp_path):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps({"mode": "MOCK_ONLY", "steps": []}), encoding="utf-8")

    payload = handle_request("GET", f"/api/workflow/report?file={report_path}")

    assert_api_envelope(payload)
    assert payload["data"]["report"]["mode"] == "MOCK_ONLY"


def test_workflow_report_reads_urlencoded_file_query(tmp_path):
    report_path = tmp_path / "agent report with space.json"
    report_path.write_text(json.dumps({"mode": "MOCK_ONLY", "encoded": True}), encoding="utf-8")

    payload = handle_request("GET", "/api/workflow/report?" + urlencode({"file": str(report_path)}))

    assert_api_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["report"]["encoded"] is True


def test_workflow_report_reads_agent_core_next_tool_execution_json(tmp_path):
    report_path = tmp_path / "agent-core-next-tool-execution.json"
    report_path.write_text(
        json.dumps(
            {
                "component": "RealDemoAgentCoreNextToolExecutor",
                "taskId": "task_lab_demo",
                "agentCoreNextToolExecution": {
                    "toolName": "create_lab_template_mock_import",
                    "toolCallSucceeded": True,
                    "recommendedToolCalled": True,
                },
                "postExecutionCoreNextToolPlan": {
                    "toolName": "create_exam_question_import_preview",
                    "reasonCode": "NEXT_CORE_TOOL_AVAILABLE",
                },
                "nextSingleStepActionGuide": {
                    "nextToolName": "create_exam_question_import_preview",
                    "canContinueWithSameCommand": True,
                },
                "safety": {
                    "realAgentStarted": False,
                    "autoApproveAllowed": False,
                    "autoPublishAllowed": False,
                    "realPublishAllowed": False,
                },
            }
        ),
        encoding="utf-8",
    )

    payload = handle_request("GET", f"/api/workflow/report?file={report_path}")

    assert_api_envelope(payload)
    report = payload["data"]["report"]
    assert report["component"] == "RealDemoAgentCoreNextToolExecutor"
    assert report["agentCoreNextToolExecution"]["toolCallSucceeded"] is True
    assert report["postExecutionCoreNextToolPlan"]["toolName"] == "create_exam_question_import_preview"
    assert report["nextSingleStepActionGuide"]["canContinueWithSameCommand"] is True
    assert report["safety"]["realAgentStarted"] is False


def test_workflow_demo_runs_mock_chain_and_creates_review_tasks(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/workflow/demo",
        store_path=store_path,
        body={"input": str(source), "reviewer": "teacher_1"},
    )
    listed = handle_request("GET", "/api/ai-tasks?status=WAITING_REVIEW", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["reviewRequired"] is True
    assert payload["data"]["publishBlockedUntilApproved"] is True
    assert payload["data"]["answerVisibleToCandidate"] is False
    assert payload["data"]["sandboxExecuted"] is False
    assert payload["data"]["materialAnalysis"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["materialAnalysis"]["unknownShellExecuted"] is False
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} >= {
        "MATERIAL_ANALYSIS",
        "LAB_DSL",
        "EXAM_DSL",
        "GRADING_DSL",
        "PPT_DSL",
        "GRADING_REPORT",
        "WORKFLOW_REPORT",
    }
    assert all(artifact["workflowRunId"] == payload["data"]["workflowRun"]["id"] for artifact in payload["data"]["artifacts"])
    assert [task["taskType"] for task in payload["data"]["createdTasks"]] == [
        "LAB_GENERATION",
        "EXAM_GENERATION",
        "GRADING_GENERATION",
        "PPT_GENERATION",
    ]
    assert {task["status"] for task in payload["data"]["createdTasks"]} == {"WAITING_REVIEW"}
    assert [step["name"] for step in payload["data"]["report"]["steps"]] == [
        "generate_lab_dsl",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "generate_ppt_dsl",
        "mock_grade_run",
    ]
    assert payload["data"]["report"]["steps"][0]["materialAnalysis"]["unknownShellExecuted"] is False
    assert payload["data"]["report"]["providerAdapter"] == "mock_provider_adapter"
    assert payload["data"]["report"]["steps"][0]["provider"]["adapterId"] == "mock_provider_adapter"
    assert payload["data"]["report"]["steps"][1]["provider"]["providerId"] == "mock"
    assert payload["data"]["report"]["steps"][2]["provider"]["networkAccess"] is False
    assert payload["data"]["report"]["steps"][3]["provider"]["realLlmCalled"] is False
    assert set(payload["data"]["report"]["providerCallAuditEvents"]) == {"lab", "exam", "grading", "ppt"}
    assert [payload["data"]["report"]["steps"][index]["providerCallAuditEvent"]["detail"]["workflowStep"] for index in range(4)] == [
        "generate_lab_dsl",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "generate_ppt_dsl",
    ]
    assert payload["data"]["report"]["steps"][0]["providerCallAuditEvent"]["promptId"] == "lab_generation_v0"
    assert payload["data"]["report"]["steps"][1]["providerCallAuditEvent"]["inputRef"] == "lab_demo"
    assert payload["data"]["report"]["steps"][2]["providerCallAuditEvent"]["inputRef"] == "exam_demo"
    assert payload["data"]["report"]["steps"][3]["providerCallAuditEvent"]["realLlmCalled"] is False
    assert payload["data"]["workflowRun"]["steps"][0]["detail"]["materialAnalysis"]["unknownShellExecuted"] is False
    assert all("providerCallAuditEvent" in step["detail"] for step in payload["data"]["workflowRun"]["steps"][:4])
    assert payload["data"]["report"]["steps"][-1]["sandboxExecuted"] is False
    assert payload["data"]["report"]["steps"][-1]["report"]["passed"] is True
    assert payload["data"]["workflowRun"]["workflowId"] == "phase1_main_demo"
    assert payload["data"]["workflowRun"]["status"] == "COMPLETED"
    assert payload["data"]["workflowRun"]["realLlmCalled"] is False
    assert listed["data"]["total"] == 4
    audit = handle_request("GET", f"/api/provider-audit-events?traceId={payload['traceId']}", store_path=store_path)
    assert audit["data"]["total"] == 4
    assert {item["detail"]["workflowId"] for item in audit["data"]["items"]} == {"phase1_main_demo"}


def test_workflow_runs_list_and_get(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    demo = handle_request(
        "POST",
        "/api/workflow/demo",
        store_path=store_path,
        body={"input": str(source), "reviewer": "teacher_1"},
    )
    run_id = demo["data"]["workflowRun"]["id"]

    listed = handle_request("GET", "/api/workflow-runs?workflowId=phase1_main_demo&status=COMPLETED", store_path=store_path)
    fetched = handle_request("GET", f"/api/workflow-runs/{run_id}", store_path=store_path)

    assert_api_envelope(listed)
    assert listed["data"]["total"] == 1
    assert listed["data"]["items"][0]["id"] == run_id
    assert listed["data"]["items"][0]["steps"][0]["name"] == "generate_lab_dsl"
    assert fetched["data"]["workflowRun"]["id"] == run_id
    assert fetched["data"]["workflowRun"]["publishBlockedUntilApproved"] is True


def test_workflow_registry_list_and_get_return_mock_capabilities(tmp_path):
    store_path = tmp_path / "store.json"

    listed = handle_request("GET", "/api/workflow-registry", store_path=store_path)
    filtered = handle_request("GET", "/api/workflow-registry?category=ppt_generation", store_path=store_path)
    detail = handle_request("GET", "/api/workflow-registry/phase2_ppt_generation", store_path=store_path)

    assert_api_envelope(listed)
    assert_api_envelope(filtered)
    assert_api_envelope(detail)
    assert listed["data"]["registryId"] == "phase2_workflow_registry"
    assert listed["data"]["total"] == 4
    assert {item["workflowId"] for item in listed["data"]["items"]} == {
        "phase2_content_generation",
        "phase2_exam_conversion",
        "phase2_ppt_generation",
        "phase2_grading_generation",
    }
    assert filtered["data"]["total"] == 1
    assert filtered["data"]["items"][0]["workflowId"] == "phase2_ppt_generation"
    assert detail["data"]["workflow"]["workflowId"] == "phase2_ppt_generation"
    assert detail["data"]["contract"]["workflowId"] == "phase2_ppt_generation"
    assert detail["data"]["contract"]["documentPolicy"]["pptFileGenerated"] is False
    assert detail["data"]["safety"]["realLlmCalled"] is False


def test_workflow_registry_errors_are_json(tmp_path):
    store_path = tmp_path / "store.json"

    missing = handle_request("GET", "/api/workflow-registry/missing_workflow", store_path=store_path)
    wrong_method = handle_request("POST", "/api/workflow-registry", store_path=store_path, body={})

    assert_api_envelope(missing)
    assert missing["success"] is False
    assert missing["code"] == "NOT_FOUND"
    assert missing["errors"][0]["field"] == "workflowId"
    assert_api_envelope(wrong_method)
    assert wrong_method["success"] is False
    assert wrong_method["code"] == "METHOD_NOT_ALLOWED"


def test_phase2_content_generation_workflow_creates_review_bundle(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/phase2/workflows/content-generation/run",
        store_path=store_path,
        body={"input": str(source), "reviewer": "teacher_1"},
    )

    assert_api_envelope(payload)
    assert payload["data"]["report"]["workflowId"] == "phase2_content_generation"
    assert payload["data"]["report"]["phase"] == "Phase 2"
    assert payload["data"]["report"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["report"]["contentQualitySummary"]["component"] == "RealDslContentQualitySummary"
    assert payload["data"]["report"]["contentQualitySummary"]["manualReviewRequired"] is True
    assert payload["data"]["report"]["contentQualitySummary"]["autoApproveAllowed"] is False
    assert payload["data"]["report"]["generatedDsl"]["lab"]["contentQualitySummary"]["kind"] == "lab"
    assert [step["name"] for step in payload["data"]["report"]["steps"]] == [
        "validate_input",
        "analyze_material",
        "generate_lab_dsl",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "generate_ppt_dsl",
        "assemble_review_bundle",
    ]
    assert {item["status"] for item in payload["data"]["report"]["generatedDsl"].values()} == {"WAITING_REVIEW"}
    assert payload["data"]["report"]["generatedDsl"]["exam"]["answerVisibleToCandidate"] is False
    assert payload["data"]["reviewSummary"]["publishBlockedUntilApproved"] is True
    assert payload["data"]["safety"]["realLlmCalled"] is False
    assert payload["data"]["safety"]["realAgentStarted"] is False
    assert payload["data"]["safety"]["realCloudResourceCreated"] is False
    assert payload["data"]["safety"]["sandboxExecuted"] is False
    assert payload["data"]["safety"]["realPublish"] is False
    assert [task["taskType"] for task in payload["data"]["createdTasks"]] == [
        "LAB_GENERATION",
        "EXAM_GENERATION",
        "GRADING_GENERATION",
        "PPT_GENERATION",
    ]
    assert {task["status"] for task in payload["data"]["createdTasks"]} == {"WAITING_REVIEW"}
    assert payload["data"]["workflowRun"]["workflowId"] == "phase2_content_generation"
    assert payload["data"]["workflowRun"]["realLlmCalled"] is False
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} >= {
        "MATERIAL_ANALYSIS",
        "LAB_DSL",
        "EXAM_DSL",
        "GRADING_DSL",
        "PPT_DSL",
        "WORKFLOW_REPORT",
    }
    dsl_artifact = next(artifact for artifact in payload["data"]["artifacts"] if artifact["kind"] == "LAB_DSL")
    assert dsl_artifact["metadata"]["contentQualitySummary"]["readyForManualReview"] is True
    assert dsl_artifact["metadata"]["workflowContentQualitySummary"]["component"] == "RealDslContentQualitySummary"
    lab_task = next(task for task in payload["data"]["createdTasks"] if task["taskType"] == "LAB_GENERATION")
    detail_payload = handle_request("GET", f"/api/review-tasks/{lab_task['id']}", store_path=store_path)
    assert detail_payload["data"]["reviewDetail"]["contentQualitySummary"]["available"] is True
    assert detail_payload["data"]["reviewDetail"]["reviewPage"]["contentQualitySummary"]["items"]["lab"]["kind"] == "lab"
    action_panel = detail_payload["data"]["reviewDetail"]["platformImportPreviewActions"]
    assert action_panel["contentQualityAvailable"] is True
    assert action_panel["contentQualityReadyTotal"] == 1
    assert action_panel["contentQualityBlockedTotal"] == 0
    assert action_panel["items"][0]["contentQualityReadyForImportPreview"] is True
    assert action_panel["items"][0]["contentQualityRecommendedAction"] == "approve_task_then_create_import_preview"
    assert detail_payload["data"]["reviewDetail"]["reviewPage"]["platformImportPreviewActions"] == action_panel
    assert detail_payload["data"]["reviewDetail"]["summary"]["contentQualityAvailable"] is True

    core_payload = handle_request("GET", f"/api/review-tasks/{lab_task['id']}/core-readiness", store_path=store_path)
    assert_api_envelope(core_payload)
    core_report = core_payload["data"]["coreWorkflowReadinessReport"]
    assert core_report["contentQualityReadiness"]["available"] is True
    assert core_report["contentQualityReadiness"]["readyForImportPreview"] is True
    assert core_report["summary"]["contentQualityAvailable"] is True
    assert core_report["summary"]["contentQualityReadyForImportPreview"] is True
    assert core_report["summary"]["contentQualityRevisionRequired"] is False
    assert core_report["steps"][0]["id"] == "content_quality_ready_for_import_preview"
    assert core_report["steps"][0]["ready"] is True
    assert core_report["nextToolRecommendation"]["reasonCode"] == "HUMAN_APPROVAL_REQUIRED"

    audit = handle_request("GET", f"/api/provider-audit-events?traceId={payload['traceId']}", store_path=store_path)
    runs = handle_request("GET", "/api/workflow-runs?workflowId=phase2_content_generation", store_path=store_path)
    assert audit["data"]["total"] == 4
    assert {item["detail"]["workflowId"] for item in audit["data"]["items"]} == {"phase2_content_generation"}
    assert runs["data"]["total"] == 1


def test_phase2_content_generation_workflow_validates_required_frontend_inputs(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    missing_input = handle_request(
        "POST",
        "/api/phase2/workflows/content-generation/run",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    missing_reviewer = handle_request(
        "POST",
        "/api/phase2/workflows/content-generation/run",
        store_path=store_path,
        body={"input": str(source)},
    )

    assert_api_envelope(missing_input)
    assert missing_input["success"] is False
    assert missing_input["code"] == "VALIDATION_ERROR"
    assert missing_input["errors"] == [{"field": "input", "reason": "缺少参数"}]
    assert_api_envelope(missing_reviewer)
    assert missing_reviewer["success"] is False
    assert missing_reviewer["code"] == "VALIDATION_ERROR"
    assert missing_reviewer["errors"] == [{"field": "reviewer", "reason": "缺少参数"}]


def test_core_readiness_prioritizes_content_quality_revision_before_approval(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/phase2/workflows/content-generation/run",
        store_path=store_path,
        body={"input": str(source), "reviewer": "teacher_1"},
    )
    lab_task = next(task for task in payload["data"]["createdTasks"] if task["taskType"] == "LAB_GENERATION")
    store = JsonTaskStore(store_path)
    lab_artifact = next(
        artifact
        for artifact in store.list_artifacts(task_id=lab_task["id"])
        if artifact.kind == ArtifactKind.LAB_DSL
    )
    lab_artifact.metadata["contentQualitySummary"].update(
        {
            "readyForImportPreview": False,
            "decisionStatus": "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW",
            "recommendedAction": "revise_blocked_dsl_before_import_preview",
            "requiresRevisionBeforeImportPreview": True,
            "blockingIssueTotal": 1,
            "warningIssueTotal": 0,
        }
    )
    lab_artifact.metadata["workflowContentQualitySummary"].update(
        {
            "decisionStatus": "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW",
            "recommendedAction": "revise_blocked_dsl_before_import_preview",
            "requiresRevisionBeforeImportPreview": True,
            "blockingIssueTotal": 1,
            "warningIssueTotal": 0,
            "readyForImportPreviewKinds": [],
            "blockedForImportPreviewKinds": ["lab"],
        }
    )
    store.save_artifact(lab_artifact)

    core_payload = handle_request("GET", f"/api/review-tasks/{lab_task['id']}/core-readiness", store_path=store_path)

    assert_api_envelope(core_payload)
    core_report = core_payload["data"]["coreWorkflowReadinessReport"]
    assert core_report["contentQualityReadiness"]["available"] is True
    assert core_report["contentQualityReadiness"]["readyForImportPreview"] is False
    assert core_report["summary"]["contentQualityRevisionRequired"] is True
    assert core_report["summary"]["contentQualityBlockedForImportPreviewKinds"] == ["lab"]
    assert core_report["recommendedNextAction"] == "request_content_revision_before_import_preview"
    assert core_report["blockedSteps"][0]["id"] == "content_quality_ready_for_import_preview"
    recommendation = core_report["nextToolRecommendation"]
    assert recommendation["reasonCode"] == "CONTENT_QUALITY_REVISION_REQUIRED"
    assert recommendation["actionType"] == "manual_revision_request"
    assert recommendation["toolAvailable"] is False
    assert recommendation["contentQualityReadiness"]["decisionStatus"] == "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW"
    assert "review revision-request" in recommendation["cliCommand"]
    assert recommendation["autoExecuteAllowed"] is False
    assert recommendation["realPublishAllowed"] is False


def test_core_readiness_recommends_mock_regeneration_after_revision_request(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/phase2/workflows/content-generation/run",
        store_path=store_path,
        body={"input": str(source), "reviewer": "teacher_1"},
    )
    lab_task = next(task for task in payload["data"]["createdTasks"] if task["taskType"] == "LAB_GENERATION")
    store = JsonTaskStore(store_path)
    lab_artifact = next(
        artifact
        for artifact in store.list_artifacts(task_id=lab_task["id"])
        if artifact.kind == ArtifactKind.LAB_DSL
    )
    lab_artifact.metadata["contentQualitySummary"].update(
        {
            "readyForImportPreview": False,
            "decisionStatus": "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW",
            "recommendedAction": "revise_blocked_dsl_before_import_preview",
            "requiresRevisionBeforeImportPreview": True,
            "blockingIssueTotal": 1,
            "warningIssueTotal": 0,
        }
    )
    lab_artifact.metadata["workflowContentQualitySummary"].update(
        {
            "decisionStatus": "NEEDS_REVISION_BEFORE_IMPORT_PREVIEW",
            "recommendedAction": "revise_blocked_dsl_before_import_preview",
            "requiresRevisionBeforeImportPreview": True,
            "blockingIssueTotal": 1,
            "warningIssueTotal": 0,
            "readyForImportPreviewKinds": [],
            "blockedForImportPreviewKinds": ["lab"],
        }
    )
    store.save_artifact(lab_artifact)
    revision = handle_request(
        "POST",
        f"/api/review-tasks/{lab_task['id']}/revision-request",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "comment": "请补充目标深度后再进入导入预览。",
            "priority": "HIGH",
        },
    )

    assert_api_envelope(revision)
    core_payload = handle_request("GET", f"/api/review-tasks/{lab_task['id']}/core-readiness", store_path=store_path)
    core_report = core_payload["data"]["coreWorkflowReadinessReport"]
    recommendation = core_report["nextToolRecommendation"]
    assert core_report["summary"]["revisionRequestTotal"] == 1
    assert core_report["summary"]["revisionRequestPendingRegeneration"] is True
    assert recommendation["reasonCode"] == "CONTENT_QUALITY_REVISION_REGENERATION_PENDING"
    assert recommendation["toolName"] == "regenerate_from_revision_mock"
    assert recommendation["argumentsPreview"]["taskId"] == lab_task["id"]
    assert recommendation["argumentsPreview"]["revisionRequestId"] == revision["data"]["revisionRequest"]["id"]
    assert recommendation["autoExecuteAllowed"] is False

    regeneration = handle_request(
        "POST",
        f"/api/review-tasks/{lab_task['id']}/regenerate-mock",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "revisionRequestId": revision["data"]["revisionRequest"]["id"],
            "output": str(tmp_path / "content-quality-revision.json"),
        },
    )
    post_core_payload = handle_request(
        "GET", f"/api/review-tasks/{lab_task['id']}/core-readiness", store_path=store_path
    )
    post_core = post_core_payload["data"]["coreWorkflowReadinessReport"]
    post_recommendation = post_core["nextToolRecommendation"]

    assert_api_envelope(regeneration)
    assert post_core["summary"]["mockRevisionAlreadyGenerated"] is True
    assert post_core["summary"]["latestMockRevisionTaskId"] == regeneration["data"]["mockRegeneration"]["newTask"]["id"]
    assert post_recommendation["reasonCode"] == "CONTENT_QUALITY_REVISION_REVIEW_PENDING"
    assert post_recommendation["actionType"] == "manual_review_revised_task"
    assert regeneration["data"]["mockRegeneration"]["newTask"]["status"] == "WAITING_REVIEW"
    assert post_recommendation["autoExecuteAllowed"] is False

    revision_core_payload = handle_request(
        "GET",
        f"/api/review-tasks/{regeneration['data']['mockRegeneration']['newTask']['id']}/core-readiness",
        store_path=store_path,
    )
    revision_core = revision_core_payload["data"]["coreWorkflowReadinessReport"]
    assert revision_core["contentQualityReadiness"]["readyForImportPreview"] is True
    assert revision_core["contentQualityReadiness"]["requiresRevisionBeforeImportPreview"] is False
    assert revision_core["nextToolRecommendation"]["reasonCode"] == "HUMAN_APPROVAL_REQUIRED"


def test_reviewed_revision_tasks_continue_to_import_preview_recommendations(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    lab_created = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={"input": str(source)},
    )
    lab_revision_task_id = _create_reviewed_revision_task(
        tmp_path,
        store_path=store_path,
        source_task_id=lab_created["data"]["task"]["id"],
    )
    lab_core = handle_request(
        "GET",
        f"/api/review-tasks/{lab_revision_task_id}/core-readiness",
        store_path=store_path,
    )["data"]["coreWorkflowReadinessReport"]

    assert lab_core["contentQualityReadiness"]["readyForImportPreview"] is True
    assert lab_core["nextToolRecommendation"]["reasonCode"] == "PLATFORM_IMPORT_PREVIEW_PENDING"
    assert lab_core["nextToolRecommendation"]["toolName"] == "create_lab_template_import_preview"

    exam_created = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    exam_revision_task_id = _create_reviewed_revision_task(
        tmp_path,
        store_path=store_path,
        source_task_id=exam_created["data"]["task"]["id"],
    )
    exam_core = handle_request(
        "GET",
        f"/api/review-tasks/{exam_revision_task_id}/core-readiness",
        store_path=store_path,
    )["data"]["coreWorkflowReadinessReport"]

    assert exam_core["contentQualityReadiness"]["readyForImportPreview"] is True
    assert exam_core["nextToolRecommendation"]["reasonCode"] == "PLATFORM_IMPORT_PREVIEW_PENDING"
    assert exam_core["nextToolRecommendation"]["toolName"] == "create_exam_question_import_preview"

    grading_task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Mock Grading revision source",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_grading_revision_source",
    )
    store = JsonTaskStore(store_path)
    store.save(grading_task)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.GRADING_DSL,
            path="templates/grading/examples/mixed-checks.yaml",
            title="Mock Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id="trace_grading_revision_source",
            task_id=grading_task.id,
            source_ref="templates/grading/examples/mixed-checks.yaml",
            metadata={"dslKind": "Grading", "reviewRequired": True},
        )
    )
    grading_revision_task_id = _create_reviewed_revision_task(
        tmp_path,
        store_path=store_path,
        source_task_id=grading_task.id,
    )
    _attach_ready_grading_evidence(store_path, tmp_path, task_id=grading_revision_task_id)
    note = handle_request(
        "POST",
        f"/api/review-tasks/{grading_revision_task_id}/decision-note",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "decision": "approve-ready",
            "output": str(tmp_path / "grading-revision-decision-note.json"),
        },
    )
    grading_core = handle_request(
        "GET",
        f"/api/review-tasks/{grading_revision_task_id}/core-readiness",
        store_path=store_path,
    )["data"]["coreWorkflowReadinessReport"]

    assert_api_envelope(note)
    assert grading_core["contentQualityReadiness"]["readyForImportPreview"] is True
    assert grading_core["summary"]["gradingEvidenceReady"] is True
    assert grading_core["summary"]["gradingApproveReadyDecision"] is True
    assert grading_core["nextToolRecommendation"]["reasonCode"] == "PLATFORM_IMPORT_PREVIEW_PENDING"
    assert grading_core["nextToolRecommendation"]["toolName"] == "create_grading_rule_import_preview"


def test_phase2_content_generation_api_passes_real_llm_options(tmp_path, monkeypatch):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    captured = {}

    def fake_run_phase2_content_generation(**kwargs):
        captured.update(kwargs)
        raise mock_api.ProviderError("STOP_TEST", "stop after argument capture", [])

    monkeypatch.setattr(mock_api, "run_phase2_content_generation", fake_run_phase2_content_generation)

    payload = handle_request(
        "POST",
        "/api/phase2/workflows/content-generation/run",
        store_path=store_path,
        body={
            "input": str(source),
            "reviewer": "teacher_1",
            "providerMode": "real-llm",
            "model": "test-model",
            "baseUrl": "https://example.test/v1",
            "apiSurface": "chat.completions",
            "maxOutputTokens": 2600,
            "repairOnSchemaFailure": True,
            "explicitRealCallOptIn": True,
            "confirmRealDsl": True,
            "confirmWaitingReview": True,
            "confirmNoAutoPublish": True,
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "STOP_TEST"
    assert captured["provider_mode"] == "real-llm"
    assert captured["real_llm_model"] == "test-model"
    assert captured["real_llm_base_url"] == "https://example.test/v1"
    assert captured["api_surface"] == "chat.completions"
    assert captured["max_output_tokens"] == 2600
    assert captured["repair_on_schema_failure"] is True
    assert captured["explicit_real_call_opt_in"] is True
    assert captured["confirm_lab_only"] is True
    assert captured["confirm_waiting_review"] is True
    assert captured["confirm_no_auto_publish"] is True
    assert payload["providerErrorContext"]["providerId"] == "openai"
    assert payload["providerErrorContext"]["mode"] == "MOCK_ONLY"


def test_phase2_exam_conversion_workflow_creates_review_bundle(tmp_path):
    store_path = tmp_path / "store.json"

    payload = handle_request(
        "POST",
        "/api/phase2/workflows/exam-conversion/run",
        store_path=store_path,
        body={
            "lab": "templates/lab/examples/basic-lab.yaml",
            "notebook": "examples/notebooks/demo-lab.ipynb",
            "reviewer": "teacher_1",
        },
    )

    assert_api_envelope(payload)
    assert payload["data"]["report"]["workflowId"] == "phase2_exam_conversion"
    assert payload["data"]["report"]["phase"] == "Phase 2"
    assert payload["data"]["report"]["mode"] == "MOCK_ONLY"
    assert [step["name"] for step in payload["data"]["report"]["steps"]] == [
        "validate_lab_dsl",
        "analyze_notebook",
        "generate_exam_dsl",
        "generate_grading_dsl",
        "assemble_exam_review_bundle",
    ]
    assert payload["data"]["candidateSafeExamPreview"]["answersRemoved"] is True
    assert "answer" not in payload["data"]["candidateSafeExamPreview"]["questions"][0]
    assert {item["status"] for item in payload["data"]["generatedDsl"].values()} == {"WAITING_REVIEW"}
    assert payload["data"]["reviewSummary"]["answerVisibleToCandidate"] is False
    assert payload["data"]["safety"]["realLlmCalled"] is False
    assert payload["data"]["safety"]["sandboxExecuted"] is False
    assert payload["data"]["safety"]["contestantCodeExecuted"] is False
    assert [task["taskType"] for task in payload["data"]["createdTasks"]] == [
        "EXAM_GENERATION",
        "GRADING_GENERATION",
    ]
    assert {task["status"] for task in payload["data"]["createdTasks"]} == {"WAITING_REVIEW"}
    assert payload["data"]["workflowRun"]["workflowId"] == "phase2_exam_conversion"
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} >= {
        "LAB_DSL",
        "MATERIAL_ANALYSIS",
        "EXAM_DSL",
        "GRADING_DSL",
        "WORKFLOW_REPORT",
    }

    audit = handle_request("GET", f"/api/provider-audit-events?traceId={payload['traceId']}", store_path=store_path)
    runs = handle_request("GET", "/api/workflow-runs?workflowId=phase2_exam_conversion", store_path=store_path)
    assert audit["data"]["total"] == 2
    assert {item["detail"]["workflowId"] for item in audit["data"]["items"]} == {"phase2_exam_conversion"}
    assert runs["data"]["total"] == 1


def test_phase2_exam_conversion_grading_review_detail_includes_assessment_plan(tmp_path):
    store_path = tmp_path / "store.json"

    payload = handle_request(
        "POST",
        "/api/phase2/workflows/exam-conversion/run",
        store_path=store_path,
        body={
            "lab": "templates/lab/examples/basic-lab.yaml",
            "notebook": "examples/notebooks/demo-lab.ipynb",
            "reviewer": "teacher_1",
        },
    )
    grading_task = next(
        task for task in payload["data"]["createdTasks"] if task["taskType"] == "GRADING_GENERATION"
    )

    detail_payload = handle_request(
        "GET",
        f"/api/review-tasks/{grading_task['id']}",
        store_path=store_path,
    )

    assert_api_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    assessment_plan = detail["assessmentPlan"]
    assert assessment_plan["visible"] is True
    assert assessment_plan["emptyState"] is False
    assert assessment_plan["summary"]["available"] is True
    assert assessment_plan["summary"]["source"] == "artifact.metadata.workflowQualitySignals"
    assert assessment_plan["summary"]["planTotal"] == 1
    assert assessment_plan["summary"]["checkIds"] == ["check_pytest"]
    assert assessment_plan["summary"]["checkTypes"] == ["pytest"]
    assert assessment_plan["summary"]["runnerTypes"] == ["PytestGrader"]
    assert assessment_plan["summary"]["alignedWithChecks"] is True
    assert assessment_plan["summary"]["mockEvidenceStatuses"] == ["MOCK_EVIDENCE_NOT_COLLECTED"]
    assert assessment_plan["summary"]["executionStrategies"] == ["MOCK_PLAN_ONLY"]
    assert assessment_plan["summary"]["sandboxRequiredBeforeRealExecution"] is True
    assert assessment_plan["items"][0]["executionPlan"]["requiredLimits"]["network"] == "disabled_by_default"
    manual_checklist = assessment_plan["manualReviewChecklist"]
    assert manual_checklist["enabled"] is True
    assert manual_checklist["source"] == "reviewDetail.assessmentPlan"
    assert manual_checklist["taskId"] == grading_task["id"]
    assert manual_checklist["entryRoute"] == f"/grading/:id/review?taskId={grading_task['id']}"
    assert manual_checklist["primaryReviewFocus"] == "review_assessment_plan_before_approval"
    assert manual_checklist["status"] == "NEEDS_HUMAN_REVIEW"
    assert [item["id"] for item in manual_checklist["checklist"]] == [
        "verify_assessment_plan_aligned_with_checks",
        "confirm_mock_evidence_not_collected",
        "confirm_real_sandbox_evidence_required_before_real_execution",
        "verify_required_limits_present",
        "confirm_no_execution_or_publish",
    ]
    assert all(item["status"] == "NEEDS_HUMAN_REVIEW" for item in manual_checklist["checklist"])
    assert all(item["matched"] is True for item in manual_checklist["checklist"])
    assert manual_checklist["operatorDecision"]["manualDecisionRequired"] is True
    assert manual_checklist["operatorDecision"]["approveAllowedAfterChecklist"] is True
    assert manual_checklist["operatorDecision"]["autoApproveAllowed"] is False
    assert manual_checklist["operatorDecision"]["batchStateChangeAllowed"] is False
    assert manual_checklist["operatorDecision"]["realSandboxRunEnabled"] is False
    assert manual_checklist["operatorDecision"]["contestantCodeExecuted"] is False
    assert manual_checklist["operatorDecision"]["realPublishAllowed"] is False
    assert detail["reviewPage"]["assessmentPlan"] == assessment_plan
    assert detail["reviewPage"]["assessmentPlanManualReviewChecklist"] == manual_checklist
    assert detail["reviewPage"]["dslPreview"]["artifactKind"] == "GRADING_DSL"
    assert detail["reviewPage"]["dslPreview"]["assessmentPlanTotal"] == 1
    assert detail["reviewPage"]["dslPreview"]["assessmentPlanAlignedWithChecks"] is True


def test_phase2_ppt_generation_workflow_creates_review_bundle(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# PPT Source\n\n- point one\n- point two", encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/phase2/workflows/ppt-generation/run",
        store_path=store_path,
        body={"input": str(source), "reviewer": "teacher_1"},
    )

    assert_api_envelope(payload)
    assert payload["data"]["report"]["workflowId"] == "phase2_ppt_generation"
    assert payload["data"]["report"]["phase"] == "Phase 2"
    assert payload["data"]["report"]["mode"] == "MOCK_ONLY"
    assert [step["name"] for step in payload["data"]["report"]["steps"]] == [
        "validate_input",
        "analyze_material",
        "build_chapter_tree",
        "extract_key_points",
        "build_slide_plan",
        "generate_ppt_dsl",
        "assemble_ppt_review_bundle",
    ]
    assert payload["data"]["slidePlan"]["slides"]
    assert payload["data"]["slidePlan"]["artifactGenerated"] is False
    assert payload["data"]["slidePlan"]["pptFileGenerated"] is False
    assert set(payload["data"]["generatedDsl"]) == {"ppt"}
    assert payload["data"]["generatedDsl"]["ppt"]["status"] == "WAITING_REVIEW"
    assert payload["data"]["reviewSummary"]["publishBlockedUntilApproved"] is True
    assert payload["data"]["reviewSummary"]["artifactGenerated"] is False
    assert payload["data"]["reviewSummary"]["pptFileGenerated"] is False
    assert payload["data"]["safety"]["realLlmCalled"] is False
    assert payload["data"]["safety"]["realPptFileCreated"] is False
    assert [task["taskType"] for task in payload["data"]["createdTasks"]] == ["PPT_GENERATION"]
    assert {task["status"] for task in payload["data"]["createdTasks"]} == {"WAITING_REVIEW"}
    assert payload["data"]["workflowRun"]["workflowId"] == "phase2_ppt_generation"
    assert {artifact["kind"] for artifact in payload["data"]["artifacts"]} >= {
        "MATERIAL_ANALYSIS",
        "PPT_DSL",
        "WORKFLOW_REPORT",
    }
    assert any(
        artifact["metadata"].get("artifactType") == "slide_plan"
        for artifact in payload["data"]["artifacts"]
    )

    audit = handle_request("GET", f"/api/provider-audit-events?traceId={payload['traceId']}", store_path=store_path)
    runs = handle_request("GET", "/api/workflow-runs?workflowId=phase2_ppt_generation", store_path=store_path)
    assert audit["data"]["total"] == 1
    assert {item["detail"]["workflowId"] for item in audit["data"]["items"]} == {"phase2_ppt_generation"}
    assert runs["data"]["total"] == 1


def test_artifacts_list_filters_by_workflow_run(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    demo = handle_request(
        "POST",
        "/api/workflow/demo",
        store_path=store_path,
        body={"input": str(source), "reviewer": "teacher_1"},
    )
    run_id = demo["data"]["workflowRun"]["id"]

    payload = handle_request("GET", f"/api/artifacts?workflowRunId={run_id}", store_path=store_path)

    assert_api_envelope(payload)
    assert payload["data"]["total"] == len(demo["data"]["artifacts"])
    assert {artifact["workflowRunId"] for artifact in payload["data"]["items"]} == {run_id}


def test_workflow_runs_rejects_unknown_status(tmp_path):
    payload = handle_request("GET", "/api/workflow-runs?status=UNKNOWN", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "status"


def test_workflow_run_not_found_returns_json(tmp_path):
    payload = handle_request("GET", "/api/workflow-runs/workflow_run_missing", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"


def test_workflow_demo_requires_input(tmp_path):
    payload = handle_request(
        "POST",
        "/api/workflow/demo",
        store_path=tmp_path / "store.json",
        body={"reviewer": "teacher_1"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"


def test_workflow_demo_requires_reviewer(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")

    payload = handle_request(
        "POST",
        "/api/workflow/demo",
        store_path=tmp_path / "store.json",
        body={"input": str(source)},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "reviewer"


def test_workflow_demo_requires_existing_input_file(tmp_path):
    payload = handle_request(
        "POST",
        "/api/workflow/demo",
        store_path=tmp_path / "store.json",
        body={"input": str(tmp_path / "missing.md"), "reviewer": "teacher_1"},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "input"


def test_workflow_demo_requires_post(tmp_path):
    payload = handle_request("GET", "/api/workflow/demo", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_grading_report_reads_local_json(tmp_path):
    report_path = tmp_path / "grading-report.json"
    report_path.write_text(
        json.dumps(
            {
                "mode": "MOCK_ONLY",
                "phase": "Phase 3",
                "gradingId": "grading_python_basic",
                "passed": True,
                "totalScore": 100,
                "earnedScore": 100,
                "runner": {"id": "mock_grading_runner"},
                "sandboxPolicy": {"executorBoundary": "SandboxExecutor", "hostExecutionAllowed": False},
                "checkSummary": {"executed": 0, "scoreTotalMatchesSpec": True},
                "explainability": {"status": "EXPLAINABLE_MOCK_PLAN"},
                "checks": [
                    {
                        "id": "check_pytest",
                        "type": "pytest",
                        "runner": "PytestGrader",
                        "score": 100,
                        "earnedScore": 100,
                        "passed": True,
                        "riskLevel": "MEDIUM",
                        "inputSummary": {"path": "tests/test_main.py"},
                        "executionPlan": {"strategy": "MOCK_PLAN_ONLY"},
                        "mockEvidence": {"status": "MOCK_EVIDENCE_NOT_COLLECTED"},
                    }
                ],
                "sandboxExecuted": False,
                "contestantCodeExecuted": False,
                "commandExecuted": False,
                "unknownShellExecuted": False,
                "networkEnabled": False,
            }
        ),
        encoding="utf-8",
    )

    payload = handle_request("GET", f"/api/grading/report?file={report_path}")

    assert_api_envelope(payload)
    assert payload["data"]["report"]["gradingId"] == "grading_python_basic"
    assert payload["data"]["report"]["passed"] is True
    assert payload["data"]["reportDetail"]["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert payload["data"]["reportDetail"]["source"] == "sandbox.grade_runner.build_grading_report_detail"
    assert payload["data"]["reportDetail"]["checkPlans"][0]["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED"
    assert payload["data"]["reportDetail"]["safety"]["sandboxExecuted"] is False


def test_grading_controlled_evidence_api_returns_isolation_summary(tmp_path, monkeypatch):
    store_path = tmp_path / "store.json"
    output_path = tmp_path / "controlled-report.json"

    def fake_run(args, **kwargs):
        if args[:2] == ["docker", "info"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout='"29.5.3"', stderr="")
        if args[:3] == ["docker", "image", "inspect"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="sha256:demo", stderr="")
        if "main.py" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="accuracy=0.90\n", stderr="")
        if "pytest" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="1 passed\n", stderr="")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr("sandbox.controlled_command_executor.subprocess.run", fake_run)

    payload = handle_request(
        "POST",
        "/api/grading/controlled-evidence",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/controlled-command-sandbox.yaml",
            "submission": "examples/submissions/controlled-command-demo",
            "image": "local-python:demo",
            "output": str(output_path),
        },
    )

    assert_api_envelope(payload)
    assert output_path.exists()
    report = payload["data"]["report"]
    assert report["mode"] == "CONTROLLED_DOCKER_SANDBOX_POC"
    assert report["executionSummary"]["executed"] == 2
    assert report["isolation"]["submissionMount"]["mode"] == "ro"
    assert report["isolation"]["outputPolicy"]["maxOutputChars"] == 12000
    assert report["isolationQuality"]["qualityState"] == "CONTROLLED_DOCKER_ISOLATION_READY"
    assert report["isolationQuality"]["readyForLocalControlledEvidence"] is True
    assert report["imageSupplyChain"]["inspection"]["imageId"] == "sha256:demo"
    assert report["imageSupplyChain"]["allowlist"]["status"] == "MATCHED"
    assert report["imageSupplyChain"]["registry"]["automaticPullDisabled"] is True
    assert payload["data"]["reportDetail"]["isolation"]["networkEnabled"] is False
    assert payload["data"]["reportDetail"]["isolationQuality"]["criticalIsolationReady"] is True
    assert payload["data"]["reportDetail"]["imageSupplyChain"]["allowlist"]["matched"] is True
    assert payload["data"]["operationAuditEvent"]["detail"]["isolation"]["submissionMount"]["mode"] == "ro"
    assert payload["data"]["operationAuditEvent"]["detail"]["isolationQuality"]["qualityState"] == "CONTROLLED_DOCKER_ISOLATION_READY"
    assert payload["data"]["operationAuditEvent"]["detail"]["imageSupplyChain"]["inspection"]["digest"] == "sha256:demo"
    assert payload["data"]["artifact"]["metadata"]["isolation"]["containerReadOnlyRootFilesystem"] is True
    assert payload["data"]["artifact"]["metadata"]["isolationQuality"]["reviewBoundary"]["autoApproveAllowed"] is False
    assert payload["data"]["artifact"]["metadata"]["imageSupplyChain"]["registry"]["registryAuthUsed"] is False
    assert payload["data"]["sandboxExecuted"] is True
    assert payload["data"]["contestantCodeExecuted"] is True


def test_grading_report_can_include_merged_review_evidence_by_task_id(tmp_path):
    store_path = tmp_path / "store.json"
    store = JsonTaskStore(store_path)
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="Mock grading evidence review",
        input_type="grading_dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="examples/output/grading-report.json",
    )
    store.save(task)
    readonly_report = tmp_path / "readonly-report.json"
    controlled_report = tmp_path / "controlled-report.json"
    grading_report = tmp_path / "grading-report.json"
    merged_report = tmp_path / "merged-evidence-report.json"
    readonly_report.write_text(
        json.dumps(
            {
                "id": "readonly_report",
                "mode": "READONLY_REAL_SANDBOX_POC",
                "checks": [
                    {
                        "id": "check_static",
                        "type": "json_field",
                        "status": "PASSED",
                        "passed": True,
                        "score": 40,
                        "earnedScore": 40,
                    }
                ],
                "safety": {
                    "sandboxExecuted": False,
                    "contestantCodeExecuted": False,
                    "commandExecuted": False,
                    "networkEnabled": False,
                    "realPublish": False,
                },
            }
        ),
        encoding="utf-8",
    )
    controlled_report.write_text(
        json.dumps(
            {
                "id": "controlled_report",
                "mode": "CONTROLLED_DOCKER_SANDBOX_POC",
                "runner": {"id": "controlled_command_executor"},
                "checks": [
                    {
                        "id": "check_pytest",
                        "type": "pytest",
                        "status": "PASSED",
                        "passed": True,
                        "score": 60,
                        "earnedScore": 60,
                    }
                ],
                "safety": {
                    "sandboxExecuted": True,
                    "contestantCodeExecuted": False,
                    "commandExecuted": True,
                    "networkEnabled": False,
                    "realPublish": False,
                },
            }
        ),
        encoding="utf-8",
    )
    grading_report.write_text(
        json.dumps(
            {
                "mode": "MOCK_ONLY",
                "gradingId": "grading_python_basic",
                "passed": True,
                "totalScore": 100,
                "earnedScore": 100,
                "runner": {"id": "mock_grading_runner"},
                "sandboxPolicy": {"executorBoundary": "SandboxExecutor", "hostExecutionAllowed": False},
                "checkSummary": {"executed": 0},
                "explainability": {"status": "EXPLAINABLE_MOCK_PLAN"},
                "checks": [],
                "sandboxExecuted": False,
                "contestantCodeExecuted": False,
                "commandExecuted": False,
                "unknownShellExecuted": False,
            }
        ),
        encoding="utf-8",
    )

    merge_payload = handle_request(
        "POST",
        "/api/grading/evidence-merge",
        store_path=store_path,
        body={
            "reports": [str(readonly_report), str(controlled_report)],
            "output": str(merged_report),
            "taskId": task.id,
        },
    )
    payload = handle_request("GET", f"/api/grading/report?file={grading_report}&taskId={task.id}", store_path=store_path)

    assert_api_envelope(merge_payload)
    assert_api_envelope(payload)
    assert payload["data"]["reviewTaskId"] == task.id
    assert payload["data"]["report"]["gradingId"] == "grading_python_basic"
    assert payload["data"]["mergedGradingEvidence"]["visible"] is True
    assert payload["data"]["mergedGradingEvidenceSummary"]["available"] is True
    assert payload["data"]["mergedGradingEvidenceSummary"]["checkEvidenceReviewItemTotal"] == 2
    assert payload["data"]["mergedGradingEvidenceSummary"]["manualCheckReviewTotal"] == 0
    assert {item["checkId"] for item in payload["data"]["mergedGradingEvidenceCheckItems"]} == {
        "check_static",
        "check_pytest",
    }
    pytest_item = next(item for item in payload["data"]["mergedGradingEvidenceCheckItems"] if item["checkId"] == "check_pytest")
    assert pytest_item["evidenceSourceKind"] == "controlledDocker"
    assert pytest_item["recommendedAction"] == "verify_controlled_docker_output_and_score"
    assert payload["data"]["reviewDecisionHints"]["overallHint"] == "READY_FOR_MANUAL_REVIEW_DECISION"
    assert payload["data"]["reviewDecisionHints"]["hintTotal"] == 2


    note_payload = handle_request(
        "POST",
        f"/api/review-tasks/{task.id}/decision-note",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "decision": "needs-evidence",
            "reason": "请补充 notebook_cell 的受控证据。",
            "output": str(tmp_path / "review-decision-note.json"),
        },
    )
    assert_api_envelope(note_payload)
    assert note_payload["success"] is True
    note = note_payload["data"]["decisionNote"]
    assert note["decision"] == "needs-evidence"
    assert note["taskStatusBefore"] == "WAITING_REVIEW"
    assert note["taskStatusAfter"] == "WAITING_REVIEW"
    assert note["statusChanged"] is False
    assert note["safety"]["autoApproveAllowed"] is False
    assert note_payload["data"]["artifact"]["kind"] == "REVIEW_DECISION_NOTE"
    assert note_payload["data"]["operationAuditEvent"]["action"] == "REVIEW_DECISION_NOTE_RECORD"
    detail = note_payload["data"]["reviewDetail"]
    assert detail["task"]["status"] == "WAITING_REVIEW"
    assert detail["reviewDecisionNotes"]["total"] == 1
    assert detail["reviewPage"]["reviewDecisionNotes"]["latest"]["decision"] == "needs-evidence"

    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_2"},
    )
    assert_api_envelope(approved)
    assert approved["data"]["task"]["status"] == "APPROVED"
    precheck = approved["data"]["preApproveReviewCheck"]
    assert precheck["applicable"] is True
    assert precheck["status"] == "APPROVE_ALLOWED_WITH_WARNINGS"
    assert precheck["approvalStillAllowed"] is True
    assert precheck["summary"]["evidenceReady"] is True
    assert precheck["summary"]["reviewDecisionNoteRecorded"] is True
    assert precheck["summary"]["approveReadyDecision"] is False
    assert precheck["summary"]["latestDecision"] == "needs-evidence"
    assert precheck["summary"]["warningTotal"] == 1
    assert precheck["summary"]["recommendedWarnings"] == [
        "review_decision_note_not_approve_ready_before_approve"
    ]
    assert precheck["safety"]["autoApproveAllowed"] is False

    report_with_note = handle_request(
        "GET",
        f"/api/grading/report?file={grading_report}&taskId={task.id}",
        store_path=store_path,
    )
    assert_api_envelope(report_with_note)
    assert report_with_note["data"]["reviewDecisionNotes"]["total"] == 1
    assert report_with_note["data"]["reviewDecisionNotes"]["latest"]["decision"] == "needs-evidence"
    assert report_with_note["data"]["reviewDecisionNotes"]["safety"]["autoApproveAllowed"] is False


def test_grading_evidence_readiness_api_reads_existing_reports(tmp_path):
    report_path = tmp_path / "readiness-source.json"
    report_path.write_text(
        json.dumps(
            {
                "id": "readiness_source",
                "mode": "READONLY_REAL_SANDBOX_POC",
                "checks": [
                    {
                        "id": "check_metrics",
                        "type": "json_field",
                        "status": "PASSED",
                        "passed": True,
                        "score": 50,
                        "earnedScore": 50,
                    },
                    {
                        "id": "check_stdout",
                        "type": "stdout_contains",
                        "status": "DEFERRED",
                        "score": 50,
                        "earnedScore": 0,
                    },
                ],
                "safety": {
                    "sandboxExecuted": False,
                    "contestantCodeExecuted": False,
                    "commandExecuted": False,
                },
            }
        ),
        encoding="utf-8",
    )

    payload = handle_request("GET", f"/api/grading/evidence-readiness?report={report_path}")

    assert_api_envelope(payload)
    readiness = payload["data"]["gradingEvidenceReadiness"]
    assert readiness["mode"] == "GRADING_EVIDENCE_READINESS"
    assert readiness["summary"]["checkTotal"] == 2
    assert readiness["summary"]["evidenceReadyTotal"] == 1
    assert readiness["summary"]["missingEvidenceTotal"] == 1
    assert readiness["summary"]["controlledCommandMissingTotal"] == 1
    assert readiness["items"][1]["recommendedNextEvidence"] == "controlled_command_evidence"
    assert readiness["nextActions"][0]["id"] == "run_controlled_command_evidence_after_review"
    assert readiness["safety"]["readExistingReportsOnly"] is True
    assert readiness["safety"]["sandboxExecutedByReadiness"] is False


def test_grading_report_task_id_missing_returns_empty_evidence_summary(tmp_path):
    report_path = tmp_path / "grading-report.json"
    report_path.write_text(
        json.dumps(
            {
                "mode": "MOCK_ONLY",
                "gradingId": "grading_python_basic",
                "runner": {"id": "mock_grading_runner"},
                "sandboxPolicy": {"executorBoundary": "SandboxExecutor", "hostExecutionAllowed": False},
                "checkSummary": {"executed": 0},
                "explainability": {"status": "EXPLAINABLE_MOCK_PLAN"},
                "checks": [],
            }
        ),
        encoding="utf-8",
    )

    payload = handle_request("GET", f"/api/grading/report?file={report_path}&taskId=missing_task", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["mergedGradingEvidence"]["visible"] is False
    assert payload["data"]["mergedGradingEvidence"]["summary"]["available"] is False
    assert payload["data"]["mergedGradingEvidenceCheckItems"] == []
    assert payload["data"]["reviewDecisionNotes"]["visible"] is False
    assert payload["data"]["reviewDecisionNotes"]["total"] == 0


def test_grading_run_returns_mock_report(tmp_path):
    payload = handle_request(
        "POST",
        "/api/grading/run",
        store_path=tmp_path / "store.json",
        body={"grading": "templates/grading/examples/python-pytest.yaml"},
    )

    assert_api_envelope(payload)
    assert payload["data"]["report"]["mode"] == "MOCK_ONLY"
    assert payload["data"]["report"]["gradingId"] == "grading_demo"
    assert payload["data"]["report"]["passed"] is True
    assert payload["data"]["report"]["runner"]["id"] == "mock_grading_runner"
    assert payload["data"]["reportDetail"]["runner"]["id"] == "mock_grading_runner"
    assert payload["data"]["reportDetail"]["source"] == "sandbox.grade_runner.build_grading_report_detail"
    assert payload["data"]["reportDetail"]["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert payload["data"]["reportDetail"]["explainability"]["status"] == "EXPLAINABLE_MOCK_PLAN"
    assert payload["data"]["report"]["checkSummary"]["byType"]["pytest"] == 1
    assert payload["data"]["sandboxExecuted"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "MOCK_GRADING_RUN"
    assert payload["data"]["operationAuditEvent"]["contestantCodeExecuted"] is False
    audit_detail = payload["data"]["operationAuditEvent"]["detail"]
    assert audit_detail["runner"]["id"] == "mock_grading_runner"
    assert audit_detail["checkSummary"]["executed"] == 0
    assert audit_detail["runRealPytestEnabled"] is False
    assert payload["data"]["reportDetail"]["audit"]["operationAuditEventId"] == payload["data"]["operationAuditEvent"]["id"]
    assert payload["data"]["reportDetail"]["audit"]["runRealPytestEnabled"] is False
    assert payload["data"]["artifact"]["kind"] == "GRADING_REPORT"
    assert payload["data"]["artifact"]["sandboxExecuted"] is False
    assert payload["data"]["artifact"]["metadata"]["sandboxPolicy"]["executorBoundary"] == "SandboxExecutor"
    assert payload["data"]["artifact"]["metadata"]["explainability"]["status"] == "EXPLAINABLE_MOCK_PLAN"


def test_grading_run_mixed_checks_returns_phase3_runner_plan(tmp_path):
    payload = handle_request(
        "POST",
        "/api/grading/run",
        store_path=tmp_path / "store.json",
        body={"grading": "templates/grading/examples/mixed-checks.yaml"},
    )

    assert_api_envelope(payload)
    report = payload["data"]["report"]
    assert report["phase"] == "Phase 3"
    assert report["runner"]["supportedCheckTypes"] == SUPPORTED_GRADING_CHECK_TYPES
    assert report["checkSummary"]["byType"] == {
        "file_exists": 1,
        "stdout_contains": 1,
        "pytest": 1,
        "notebook_cell": 1,
        "json_field": 1,
        "log_keyword": 1,
    }
    assert report["checkSummary"]["executed"] == 0
    assert payload["data"]["reportDetail"]["checkSummary"]["executed"] == 0
    assert payload["data"]["reportDetail"]["explainability"]["eachCheckHasMockEvidencePlaceholder"] is True
    assert report["sandboxExecuted"] is False
    assert report["contestantCodeExecuted"] is False
    assert report["commandExecuted"] is False
    assert all(check["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for check in report["checks"])
    assert all(check["sandboxExecutionRequest"]["mode"] == "REAL_SANDBOX_REQUIRED" for check in report["checks"])
    assert all(check["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY" for check in report["checks"])
    assert all(check["containerSandboxPlan"]["safety"]["containerStarted"] is False for check in report["checks"])
    assert all(check["containerSandboxPlan"]["resultPlaceholder"]["status"] == "NOT_EXECUTED" for check in report["checks"])
    assert all(
        plan["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY"
        for plan in payload["data"]["reportDetail"]["checkPlans"]
    )
    assert all(plan["mockEvidence"]["status"] == "MOCK_EVIDENCE_NOT_COLLECTED" for plan in payload["data"]["reportDetail"]["checkPlans"])
    audit_detail = payload["data"]["operationAuditEvent"]["detail"]
    assert audit_detail["phase"] == "Phase 3"
    assert audit_detail["runner"]["id"] == "mock_grading_runner"
    assert audit_detail["checkSummary"]["byType"] == {
        "file_exists": 1,
        "stdout_contains": 1,
        "pytest": 1,
        "notebook_cell": 1,
        "json_field": 1,
        "log_keyword": 1,
    }
    assert audit_detail["checkSummary"]["executed"] == 0
    assert len(audit_detail["checkPlans"]) == 6
    assert all(plan["executionPlan"]["strategy"] == "MOCK_PLAN_ONLY" for plan in audit_detail["checkPlans"])
    assert all(plan["containerSandboxPlan"]["mode"] == "CONTAINER_PLAN_ONLY" for plan in audit_detail["checkPlans"])
    assert all(plan["commandExecuted"] is False for plan in audit_detail["checkPlans"])
    assert "runRealPytest" in audit_detail["blockedActions"]
    assert audit_detail["hostExecutionAllowed"] is False


def test_grading_evidence_auto_api_runs_readonly_and_writes_report(tmp_path):
    output_path = tmp_path / "grading-evidence-auto.json"

    payload = handle_request(
        "POST",
        "/api/grading/evidence-auto",
        store_path=tmp_path / "store.json",
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output_path),
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is True
    assert output_path.exists()
    report = payload["data"]["gradingEvidenceAutoReport"]
    written_report = json.loads(output_path.read_text(encoding="utf-8"))
    assert written_report["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert report["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert report["sourceMode"] == "EVIDENCE_AUTO"
    assert report["summary"]["readonlyReportIncluded"] is True
    assert report["summary"]["controlledCommandRequested"] is False
    assert report["summary"]["controlledCommandIncluded"] is False
    assert report["summary"]["nextCoreActionId"] == "run_evidence_auto_with_controlled_command"
    assert report["summary"]["scorePreviewStatus"] == "PARTIAL_SCORE_PREVIEW_NEEDS_MORE_EVIDENCE"
    assert report["summary"]["scorePreviewEarnedScore"] == 40
    assert report["summary"]["scorePreviewTotalScore"] == 100
    assert report["summary"]["scorePreviewCoverageRatio"] == 0.5
    assert report["summary"]["gradingDslCoverageStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert report["summary"]["gradingDslEvidenceReadyTotal"] == 4
    assert report["summary"]["gradingDslMissingEvidenceTotal"] == 2
    assert report["scorePreview"]["component"] == "GradingEvidenceAutoScorePreview"
    assert report["scorePreview"]["earnedScore"] == 40
    assert report["scorePreview"]["coveredScore"] == 50
    assert report["scorePreview"]["missingScore"] == 50
    assert report["scorePreview"]["readyForDecisionNote"] is False
    assert written_report["scorePreview"] == report["scorePreview"]
    assert report["executionMatrix"]["mode"] == "GRADING_EVIDENCE_AUTO_EXECUTION_MATRIX"
    assert report["executionMatrix"]["summary"]["evidenceReadyTotal"] == 4
    assert report["executionMatrix"]["summary"]["missingEvidenceTotal"] == 2
    assert report["gradingDslCoverageSummary"]["status"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert set(report["gradingDslCoverageSummary"]["controlledCommandMissingCheckIds"]) == {
        "check_stdout_accuracy",
        "check_pytest",
    }
    assert written_report["gradingDslCoverageSummary"] == report["gradingDslCoverageSummary"]
    assert report["nextCoreAction"]["id"] == "run_evidence_auto_with_controlled_command"
    checklist = report["manualReviewChecklist"]
    assert checklist["component"] == "GradingEvidenceAutoManualReviewChecklist"
    assert checklist["status"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert checklist["summary"]["readyForDecisionTotal"] == 4
    assert checklist["decisionNoteRecommendation"]["decision"] == "needs-evidence"
    assert report["summary"]["manualReviewChecklistStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert written_report["manualReviewChecklist"]["status"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert report["safety"]["controlledCommandRequiresExplicitFlag"] is True
    assert report["safety"]["autoApproveAllowed"] is False
    assert report["safety"]["realPublishAllowed"] is False
    assert payload["data"]["operationAuditEvent"]["action"] == "GRADING_EVIDENCE_MERGE"
    assert payload["data"]["operationAuditEvent"]["detail"]["reportType"] == "GRADING_EVIDENCE_AUTO"
    assert payload["data"]["operationAuditEvent"]["detail"]["scorePreview"] == report["scorePreview"]
    assert payload["data"]["operationAuditEvent"]["detail"]["gradingDslCoverageSummary"] == (
        report["gradingDslCoverageSummary"]
    )
    assert payload["data"]["artifact"]["kind"] == "GRADING_REPORT"
    assert payload["data"]["artifact"]["metadata"]["reportType"] == "GRADING_EVIDENCE_AUTO"
    assert payload["data"]["artifact"]["metadata"]["scorePreview"] == report["scorePreview"]
    assert payload["data"]["artifact"]["metadata"]["gradingDslCoverageSummary"] == report["gradingDslCoverageSummary"]
    assert payload["data"]["autoApproveAllowed"] is False
    assert payload["data"]["realPublish"] is False


def test_grading_record_api_creates_lists_and_gets_record_from_report(tmp_path):
    store_path = tmp_path / "store.json"
    report_path = tmp_path / "grading-evidence-auto.json"
    evidence_payload = handle_request(
        "POST",
        "/api/grading/evidence-auto",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(report_path),
        },
    )

    create_payload = handle_request(
        "POST",
        "/api/grading/records",
        store_path=store_path,
        body={
            "report": str(report_path),
            "submissionId": "submission_api_001",
            "candidateId": "candidate_api_001",
            "reviewer": "teacher_1",
        },
    )
    record = create_payload["data"]["gradingRecord"]
    list_payload = handle_request(
        "GET",
        "/api/grading/records?submissionId=submission_api_001",
        store_path=store_path,
    )
    get_payload = handle_request(
        "GET",
        f"/api/grading/records/{record['id']}",
        store_path=store_path,
    )

    assert_api_envelope(evidence_payload)
    assert_api_envelope(create_payload)
    assert record["status"] == "NEEDS_EVIDENCE"
    assert record["earnedScore"] == 40
    assert record["totalScore"] == 100
    assert record["coveredScore"] == 50
    assert record["missingScore"] == 50
    assert record["coverageRatio"] == 0.5
    assert record["decisionNoteRecommendation"] == "needs-evidence"
    assert record["manualReviewChecklistStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert record["safety"]["derivedFromExistingReport"] is True
    assert record["safety"]["recordCreatesNewExecution"] is False
    assert record["safety"]["sandboxExecutedByRecord"] is False
    assert create_payload["data"]["operationAuditEvent"]["action"] == "GRADING_RECORD_CREATE"
    assert create_payload["data"]["recordCreatesNewExecution"] is False
    assert create_payload["data"]["autoApproveAllowed"] is False

    assert_api_envelope(list_payload)
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["id"] == record["id"]
    assert_api_envelope(get_payload)
    assert get_payload["data"]["gradingRecord"]["id"] == record["id"]


def test_grading_record_api_reads_records_from_sqlite_db_path_without_json_mirror(tmp_path):
    store_path = tmp_path / "store.json"
    empty_store_path = tmp_path / "empty-store.json"
    db_path = tmp_path / "grading-record-read.sqlite3"
    report_path = tmp_path / "sqlite-grading-record-evidence-auto.json"
    evidence_payload = handle_request(
        "POST",
        "/api/grading/evidence-auto",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(report_path),
        },
    )
    create_payload = handle_request(
        "POST",
        "/api/grading/records",
        store_path=store_path,
        body={
            "report": str(report_path),
            "submissionId": "submission_sqlite_record_api_001",
            "candidateId": "candidate_sqlite_record_api_001",
            "reviewer": "teacher_1",
            "dbPath": str(db_path),
        },
    )
    record = create_payload["data"]["gradingRecord"]
    query = urlencode({"submissionId": "submission_sqlite_record_api_001", "dbPath": str(db_path)})
    list_payload = handle_request(
        "GET",
        f"/api/grading/records?{query}",
        store_path=empty_store_path,
    )
    get_payload = handle_request(
        "GET",
        f"/api/grading/records/{record['id']}?{urlencode({'dbPath': str(db_path)})}",
        store_path=empty_store_path,
    )

    assert_api_envelope(evidence_payload)
    assert_api_envelope(create_payload)
    assert create_payload["data"]["mode"] == "LOCAL_SQLITE_GRADING_RECORD"
    assert create_payload["data"]["localSqliteWritten"] is True
    assert create_payload["data"]["dbPathSource"] == "REQUEST_DB_PATH"
    assert empty_store_path.exists() is False

    assert_api_envelope(list_payload)
    assert list_payload["data"]["mode"] == "LOCAL_SQLITE_GRADING_RECORD"
    assert list_payload["data"]["localSqliteRead"] is True
    assert list_payload["data"]["dbPathSource"] == "REQUEST_DB_PATH"
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["id"] == record["id"]
    assert list_payload["data"]["items"][0]["submissionId"] == "submission_sqlite_record_api_001"

    assert_api_envelope(get_payload)
    assert get_payload["data"]["mode"] == "LOCAL_SQLITE_GRADING_RECORD"
    assert get_payload["data"]["localSqliteRead"] is True
    assert get_payload["data"]["dbPathSource"] == "REQUEST_DB_PATH"
    assert get_payload["data"]["gradingRecord"]["id"] == record["id"]
    assert empty_store_path.exists() is False


def test_review_task_detail_api_includes_local_grading_record_summary(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="API grading record review detail",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_api_grading_record_detail",
    )
    JsonTaskStore(store_path).save(task)
    report_path = tmp_path / "grading-record-detail-evidence-auto.json"
    handle_request(
        "POST",
        "/api/grading/evidence-auto",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(report_path),
            "taskId": task.id,
        },
    )
    create_payload = handle_request(
        "POST",
        "/api/grading/records",
        store_path=store_path,
        body={
            "report": str(report_path),
            "submissionId": "submission_detail_api_001",
            "taskId": task.id,
            "reviewer": "teacher_1",
        },
    )
    detail_payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(create_payload)
    assert_api_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["gradingRecords"]["visible"] is True
    assert detail["gradingRecords"]["total"] == 1
    assert detail["gradingRecords"]["latest"]["id"] == create_payload["data"]["gradingRecord"]["id"]
    assert detail["gradingRecords"]["summary"]["latestStatus"] == "NEEDS_EVIDENCE"
    assert detail["reviewPage"]["gradingRecords"]["total"] == 1
    assert detail["summary"]["gradingRecordTotal"] == 1


def test_review_task_detail_api_reads_requested_sqlite_grading_record_summary(tmp_path):
    store_path = tmp_path / "store.json"
    grading_db_path = tmp_path / "grading-records.sqlite3"
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="SQLite grading record review detail",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_api_sqlite_grading_record_detail",
    )
    JsonTaskStore(store_path).save(task)
    record = GradingRecord(
        submissionId="submission_sqlite_detail_001",
        gradingId="grading_sqlite_detail_001",
        reportPath="examples/output/mimo-real-demo-controlled-sandbox-report.json",
        reportMode="GRADING_EVIDENCE_AUTO",
        status=GradingRecordStatus.NEEDS_REVISION,
        totalScore=100,
        earnedScore=68,
        coveredScore=80,
        missingScore=20,
        coverageRatio=0.8,
        taskId=task.id,
        candidateId="candidate_sqlite_detail_001",
        reviewer="teacher_1",
        reviewedBy="teacher_1",
        reviewedAt="2026-07-12T00:00:00Z",
        reviewDecision="needs-revision",
        reviewReason="评分 evidence 需要修订后再复核",
        traceId=task.traceId,
    )
    mock_api.GradingSQLiteRepository(grading_db_path).save_grading_record(record)

    detail_payload = handle_request(
        "GET",
        f"/api/review-tasks/{task.id}?{urlencode({'gradingDbPath': str(grading_db_path)})}",
        store_path=store_path,
    )

    assert_api_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    records = detail["gradingRecords"]
    assert records["source"] == "LOCAL_SQLITE_GRADING_RECORDS"
    assert records["reviewIntegration"]["source"] == "LOCAL_SQLITE_GRADING_RECORDS"
    assert records["total"] == 1
    assert records["latest"]["id"] == record.id
    assert records["summary"]["latestStatus"] == "NEEDS_REVISION"
    assert records["summary"]["latestReviewDecision"] == "needs-revision"
    assert records["reviewIntegration"]["state"] == "NEEDS_REVISION"
    assert detail["reviewPage"]["gradingRecords"]["source"] == "LOCAL_SQLITE_GRADING_RECORDS"
    assert detail["summary"]["gradingRecordTotal"] == 1
    assert detail["summary"]["gradingRecordPlatformReviewState"] == "NEEDS_REVISION"


def test_grading_record_review_api_uses_sqlite_db_path_from_query(tmp_path):
    store_path = tmp_path / "store.json"
    grading_db_path = tmp_path / "grading-record-review.sqlite3"
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="SQLite grading record review update",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_api_sqlite_grading_record_review",
    )
    JsonTaskStore(store_path).save(task)
    record = GradingRecord(
        submissionId="submission_sqlite_review_001",
        gradingId="grading_sqlite_review_001",
        reportPath="examples/output/mimo-real-demo-controlled-sandbox-report.json",
        reportMode="GRADING_EVIDENCE_AUTO",
        status=GradingRecordStatus.WAITING_REVIEW,
        totalScore=100,
        earnedScore=88,
        coveredScore=100,
        missingScore=0,
        coverageRatio=1.0,
        taskId=task.id,
        traceId=task.traceId,
    )
    mock_api.GradingSQLiteRepository(grading_db_path).save_grading_record(record)

    review_payload = handle_request(
        "POST",
        f"/api/grading/records/{record.id}/review?{urlencode({'dbPath': str(grading_db_path)})}",
        store_path=store_path,
        body={"reviewer": "teacher_1", "decision": "approve-ready"},
    )
    detail_payload = handle_request(
        "GET",
        f"/api/review-tasks/{task.id}?{urlencode({'gradingDbPath': str(grading_db_path)})}",
        store_path=store_path,
    )

    assert_api_envelope(review_payload)
    assert review_payload["data"]["mode"] == "LOCAL_SQLITE_GRADING_RECORD_REVIEW"
    assert review_payload["data"]["gradingRecord"]["status"] == "HUMAN_APPROVED"
    assert review_payload["data"]["gradingRecord"]["reviewDecision"] == "approve-ready"
    assert review_payload["data"]["taskStatusChanged"] is False

    assert_api_envelope(detail_payload)
    integration = detail_payload["data"]["reviewDetail"]["gradingRecords"]["reviewIntegration"]
    assert integration["source"] == "LOCAL_SQLITE_GRADING_RECORDS"
    assert integration["state"] == "READY_FOR_PLATFORM_REVIEW"
    assert integration["latestDecision"] == "approve-ready"


def test_grading_record_review_api_updates_record_without_task_transition(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="API grading record human review",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_api_grading_record_review",
    )
    JsonTaskStore(store_path).save(task)
    report_path = tmp_path / "grading-record-review-evidence-auto.json"
    handle_request(
        "POST",
        "/api/grading/evidence-auto",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(report_path),
            "taskId": task.id,
        },
    )
    create_payload = handle_request(
        "POST",
        "/api/grading/records",
        store_path=store_path,
        body={
            "report": str(report_path),
            "submissionId": "submission_review_api_001",
            "taskId": task.id,
        },
    )
    record_id = create_payload["data"]["gradingRecord"]["id"]
    review_payload = handle_request(
        "POST",
        f"/api/grading/records/{record_id}/review",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "decision": "approve-ready",
        },
    )
    detail_payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(create_payload)
    assert_api_envelope(review_payload)
    assert review_payload["data"]["gradingRecord"]["status"] == "HUMAN_APPROVED"
    assert review_payload["data"]["gradingRecord"]["reviewDecision"] == "approve-ready"
    assert review_payload["data"]["gradingRecord"]["reviewedBy"] == "teacher_1"
    assert review_payload["data"]["operationAuditEvent"]["action"] == "GRADING_RECORD_REVIEW"
    assert review_payload["data"]["taskStatusChanged"] is False
    assert JsonTaskStore(store_path).get(task.id).status.value == "WAITING_REVIEW"

    assert_api_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["gradingRecords"]["summary"]["humanApprovedTotal"] == 1
    assert detail["gradingRecords"]["summary"]["latestReviewDecision"] == "approve-ready"
    assert detail["gradingRecords"]["summary"]["readyForAgentReview"] is True
    assert detail["gradingRecords"]["summary"]["platformReviewState"] == "READY_FOR_PLATFORM_REVIEW"
    assert detail["gradingRecords"]["reviewIntegration"]["readyForAgentReview"] is True
    assert detail["gradingRecords"]["reviewIntegration"]["recordReviewChangesTaskStatus"] is False
    assert detail["summary"]["gradingRecordLatestStatus"] == "HUMAN_APPROVED"
    assert detail["summary"]["gradingRecordReadyForPlatformReview"] is True
    assert detail["summary"]["gradingRecordPlatformReviewState"] == "READY_FOR_PLATFORM_REVIEW"


def test_grading_record_review_api_requires_reason_for_needs_revision(tmp_path):
    store_path = tmp_path / "store.json"
    report_path = tmp_path / "grading-record-review-invalid-evidence-auto.json"
    handle_request(
        "POST",
        "/api/grading/evidence-auto",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(report_path),
        },
    )
    create_payload = handle_request(
        "POST",
        "/api/grading/records",
        store_path=store_path,
        body={
            "report": str(report_path),
            "submissionId": "submission_review_invalid_api_001",
        },
    )
    record_id = create_payload["data"]["gradingRecord"]["id"]
    payload = handle_request(
        "POST",
        f"/api/grading/records/{record_id}/review",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "decision": "needs-revision",
        },
    )

    assert_api_envelope(create_payload)
    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"] == [{"field": "reason", "reason": "该复核决策必须填写原因"}]


def test_backend_core_readiness_api_reports_local_staging_boundaries(tmp_path):
    store_path = tmp_path / "store.json"
    missing_db_path = tmp_path / "missing-readiness.sqlite3"

    payload = handle_request("GET", "/api/backend/core-readiness", store_path=store_path)
    missing_sqlite_payload = handle_request(
        "GET",
        f"/api/backend/core-readiness?{urlencode({'dbPath': str(missing_db_path)})}",
        store_path=store_path,
    )
    method_payload = handle_request("POST", "/api/backend/core-readiness", store_path=store_path)

    assert_api_envelope(payload)
    readiness = payload["data"]["backendCoreReadiness"]
    assert readiness["component"] == "BackendCoreReadinessReport"
    assert readiness["mode"] == "BACKEND_CORE_READINESS_LOCAL_STAGING"
    assert readiness["summary"]["readyForRealBackendMvp"] is True
    assert readiness["summary"]["readyForProduction"] is False
    assert readiness["summary"]["nextStage"] == "REAL_BACKEND_API_MVP"
    assert readiness["dataSnapshot"]["taskTotal"] == 0
    assert readiness["sqliteStaging"]["enabled"] is False
    assert readiness["sqliteStaging"]["summary"]["available"] is False
    assert readiness["safety"]["readOnly"] is True
    assert readiness["safety"]["storeMutated"] is False
    assert readiness["safety"]["workerStarted"] is False
    assert readiness["safety"]["sandboxExecuted"] is False
    assert readiness["safety"]["productionDatabaseWritten"] is False
    assert {item["id"] for item in readiness["capabilities"]} >= {
        "aiTaskApi",
        "artifactApi",
        "reviewApi",
        "agentEntityImportApi",
        "gradingJobApi",
        "gradingRecordApi",
        "gradingWorkerApi",
        "auditApi",
    }
    assert all(item["implemented"] is True for item in readiness["capabilities"])
    assert all(item["productionReady"] is False for item in readiness["capabilities"])
    assert all(item["stopLine"] == "do_not_add_more_mock_shells_for_this_capability" for item in readiness["capabilities"])

    assert_api_envelope(missing_sqlite_payload)
    missing_sqlite = missing_sqlite_payload["data"]["backendCoreReadiness"]["sqliteStaging"]
    assert missing_sqlite["enabled"] is True
    assert missing_sqlite["summary"]["available"] is False
    assert missing_sqlite["summary"]["reason"] == "sqlite staging file does not exist"
    assert missing_db_path.exists() is False

    assert_api_envelope(method_payload)
    assert method_payload["success"] is False
    assert method_payload["code"] == "METHOD_NOT_ALLOWED"


def test_backend_core_readiness_api_summarizes_grading_staging_data(tmp_path):
    store_path = tmp_path / "store.json"
    db_path = tmp_path / "grading-readiness.sqlite3"
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="API readiness grading task",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_backend_readiness_grading",
    )
    JsonTaskStore(store_path).save(task)
    output = tmp_path / "backend-readiness-grading-evidence-auto.json"
    create_payload = handle_request(
        "POST",
        "/api/grading/jobs",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output),
            "submissionId": "submission_backend_readiness_001",
            "taskId": task.id,
            "reviewer": "teacher_1",
            "dbPath": str(db_path),
        },
    )
    job_id = create_payload["data"]["gradingJob"]["id"]
    run_payload = handle_request(
        "POST",
        f"/api/grading/jobs/{job_id}/run?{urlencode({'dbPath': str(db_path)})}",
        store_path=store_path,
    )
    payload = handle_request(
        "GET",
        f"/api/backend/core-readiness?{urlencode({'taskId': task.id, 'dbPath': str(db_path)})}",
        store_path=store_path,
    )

    assert_api_envelope(create_payload)
    assert_api_envelope(run_payload)
    assert_api_envelope(payload)
    readiness = payload["data"]["backendCoreReadiness"]
    assert readiness["filters"]["taskId"] == task.id
    assert readiness["sqliteStaging"]["enabled"] is True
    assert readiness["sqliteStaging"]["policy"]["dbPathSource"] == "REQUEST_DB_PATH"
    assert readiness["sqliteStaging"]["summary"]["available"] is True
    assert readiness["sqliteStaging"]["summary"]["jobTotal"] == 1
    assert readiness["sqliteStaging"]["summary"]["recordTotal"] == 1
    assert readiness["dataSnapshot"]["gradingJobTotal"] == 1
    assert readiness["dataSnapshot"]["gradingRecordTotal"] == 1
    assert readiness["dataSnapshot"]["gradingJobsByStatus"] == {"WAITING_REVIEW": 1}
    assert readiness["dataSnapshot"]["gradingRecordsByStatus"] == {"NEEDS_EVIDENCE": 1}
    capability_by_id = {item["id"]: item for item in readiness["capabilities"]}
    assert capability_by_id["gradingJobApi"]["storedTotal"] == 1
    assert capability_by_id["gradingRecordApi"]["storedTotal"] == 1
    assert capability_by_id["gradingWorkerApi"]["storedTotal"] == 1
    assert "replace_sync_worker_with_queue_consumer" in capability_by_id["gradingJobApi"]["remainingForProduction"]
    assert readiness["migrationBoundary"]["target"] == "real backend database + authenticated API + managed queue"
    assert "JsonTaskStore" in readiness["migrationBoundary"]["replaceImplementations"]
    assert readiness["safety"]["workerStarted"] is False


def test_backend_core_db_api_init_sync_summary_and_readiness(tmp_path):
    store_path = tmp_path / "store.json"
    db_path = tmp_path / "backend-core.sqlite3"
    missing_db_path = tmp_path / "missing-backend-core.sqlite3"
    missing_read_db_path = tmp_path / "missing-backend-core-read.sqlite3"
    task = create_waiting_review_task(
        task_type="LAB_GENERATION",
        title="Backend core db API task",
        input_type="markdown",
        input_ref="examples/input/demo-source.md",
        final_result_path="examples/output/real-llm-lab.json",
        trace_id="trace_backend_core_db_api",
    )
    artifact = create_artifact_record(
        kind=ArtifactKind.LAB_DSL,
        path="examples/output/real-llm-lab.json",
        title="Backend core db API artifact",
        status=ArtifactStatus.WAITING_REVIEW,
        task_id=task.id,
        trace_id=task.traceId,
    )
    agent_entity = create_agent_entity_record(
        entity_type=AgentEntityType.LAB_TEMPLATE,
        title="Backend core db API platform entity",
        payload={"title": "Backend core db API platform entity"},
        source_task_id=task.id,
        source_preview_artifact_id=artifact.id,
        source_preview_path="examples/output/lab-template-import-preview.json",
        reviewer="teacher_1",
        trace_id=task.traceId,
        source_dsl_path="examples/output/real-llm-lab.json",
        source_artifact_id=artifact.id,
        source_artifact_kind="LAB_DSL",
    )
    store = JsonTaskStore(store_path)
    store.save(task)
    store.save_artifact(artifact)
    store.save_agent_entity(agent_entity)
    approve_payload = handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    missing_summary_payload = handle_request(
        "GET",
        f"/api/backend/core-db/summary?{urlencode({'coreDbPath': str(missing_db_path)})}",
        store_path=store_path,
    )
    missing_read_payload = handle_request(
        "GET",
        f"/api/ai-tasks?{urlencode({'coreDbPath': str(missing_read_db_path)})}",
        store_path=store_path,
    )
    init_payload = handle_request(
        "POST",
        "/api/backend/core-db/init",
        store_path=store_path,
        body={"coreDbPath": str(db_path), "actor": "teacher_1"},
    )
    sync_payload = handle_request(
        "POST",
        "/api/backend/core-db/sync-local",
        store_path=store_path,
        body={"coreDbPath": str(db_path), "actor": "teacher_1"},
    )
    summary_payload = handle_request(
        "GET",
        f"/api/backend/core-db/summary?{urlencode({'coreDbPath': str(db_path)})}",
        store_path=store_path,
    )
    core_query = urlencode({"coreDbPath": str(db_path)})
    core_task_list_query = urlencode({"coreDbPath": str(db_path), "status": "APPROVED", "taskType": "LAB_GENERATION"})
    core_artifact_list_query = urlencode({"coreDbPath": str(db_path), "kind": "LAB_DSL", "taskId": task.id})
    core_review_audit_query = urlencode({"coreDbPath": str(db_path), "taskId": task.id, "action": "APPROVE"})
    core_operation_audit_query = urlencode(
        {
            "coreDbPath": str(db_path),
            "resourceType": "AI_TASK",
            "resourceId": task.id,
            "action": "REVIEW_APPROVE",
        }
    )
    core_agent_entity_query = urlencode(
        {
            "coreDbPath": str(db_path),
            "entityType": "lab_template",
            "sourceTaskId": task.id,
        }
    )
    sqlite_task_list_payload = handle_request("GET", f"/api/ai-tasks?{core_task_list_query}", store_path=store_path)
    sqlite_task_get_payload = handle_request("GET", f"/api/ai-tasks/{task.id}?{core_query}", store_path=store_path)
    sqlite_artifact_list_payload = handle_request("GET", f"/api/artifacts?{core_artifact_list_query}", store_path=store_path)
    sqlite_artifact_get_payload = handle_request(
        "GET",
        f"/api/artifacts/{artifact.id}?{core_query}",
        store_path=store_path,
    )
    sqlite_review_audit_payload = handle_request(
        "GET",
        f"/api/review-audit-events?{core_review_audit_query}",
        store_path=store_path,
    )
    sqlite_operation_audit_payload = handle_request(
        "GET",
        f"/api/audit-events?{core_operation_audit_query}",
        store_path=store_path,
    )
    sqlite_agent_entity_list_payload = handle_request(
        "GET",
        f"/api/platform-entities?{core_agent_entity_query}",
        store_path=store_path,
    )
    sqlite_agent_entity_get_payload = handle_request(
        "GET",
        f"/api/platform-entities/{agent_entity.id}?{core_query}",
        store_path=store_path,
    )
    readiness_payload = handle_request(
        "GET",
        f"/api/backend/core-readiness?{urlencode({'coreDbPath': str(db_path)})}",
        store_path=store_path,
    )
    method_payload = handle_request("GET", "/api/backend/core-db/init", store_path=store_path)

    assert_api_envelope(approve_payload)
    assert approve_payload["data"]["task"]["status"] == "APPROVED"

    assert_api_envelope(missing_summary_payload)
    missing_summary = missing_summary_payload["data"]["backendCoreRepository"]
    assert missing_summary["available"] is False
    assert missing_summary["reason"] == "backend core sqlite staging file does not exist"
    assert missing_db_path.exists() is False

    assert_api_envelope(missing_read_payload)
    assert missing_read_payload["success"] is False
    assert missing_read_payload["code"] == "BACKEND_CORE_SQLITE_READONLY_ERROR"
    assert missing_read_db_path.exists() is False

    assert_api_envelope(init_payload)
    assert init_payload["data"]["backendCoreRepository"]["schemaVersion"] == "1"
    assert init_payload["data"]["operationAuditEvent"]["action"] == "BACKEND_CORE_REPOSITORY_INIT"
    assert init_payload["data"]["productionDatabaseWritten"] is False

    assert_api_envelope(sync_payload)
    sync = sync_payload["data"]["backendCoreRepositorySync"]
    assert sync["tasksSynced"] == 1
    assert sync["artifactsSynced"] == 1
    assert sync["reviewAuditEventsSynced"] == 1
    assert sync["operationAuditEventsSynced"] == 2
    assert sync["agentEntitiesSynced"] == 1
    assert sync_payload["data"]["operationAuditEvent"]["action"] == "BACKEND_CORE_REPOSITORY_SYNC_LOCAL"
    assert db_path.exists()

    assert_api_envelope(summary_payload)
    summary = summary_payload["data"]["backendCoreRepository"]
    assert summary["available"] is True
    assert summary["taskTotal"] == 1
    assert summary["artifactTotal"] == 1
    assert summary["reviewAuditTotal"] == 1
    assert summary["operationAuditTotal"] == 2
    assert summary["agentEntityTotal"] == 1
    assert summary["tasksByStatus"] == {"APPROVED": 1}
    assert summary["artifactsByKind"] == {"LAB_DSL": 1}
    assert summary["agentEntitiesByType"] == {"lab_template": 1}

    assert_api_envelope(sqlite_task_list_payload)
    assert sqlite_task_list_payload["data"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert sqlite_task_list_payload["data"]["localSqliteRead"] is True
    assert sqlite_task_list_payload["data"]["total"] == 1
    assert sqlite_task_list_payload["data"]["items"][0]["id"] == task.id
    assert sqlite_task_list_payload["data"]["items"][0]["status"] == "APPROVED"
    assert sqlite_task_list_payload["data"]["productionDatabaseWritten"] is False

    assert_api_envelope(sqlite_task_get_payload)
    assert sqlite_task_get_payload["data"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert sqlite_task_get_payload["data"]["task"]["id"] == task.id
    assert sqlite_task_get_payload["data"]["task"]["status"] == "APPROVED"

    assert_api_envelope(sqlite_artifact_list_payload)
    assert sqlite_artifact_list_payload["data"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert sqlite_artifact_list_payload["data"]["total"] == 1
    assert sqlite_artifact_list_payload["data"]["items"][0]["id"] == artifact.id
    assert sqlite_artifact_list_payload["data"]["items"][0]["taskId"] == task.id

    assert_api_envelope(sqlite_artifact_get_payload)
    assert sqlite_artifact_get_payload["data"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert sqlite_artifact_get_payload["data"]["artifact"]["id"] == artifact.id

    assert_api_envelope(sqlite_review_audit_payload)
    assert sqlite_review_audit_payload["data"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert sqlite_review_audit_payload["data"]["total"] == 1
    assert sqlite_review_audit_payload["data"]["items"][0]["taskId"] == task.id
    assert sqlite_review_audit_payload["data"]["items"][0]["action"] == "APPROVE"

    assert_api_envelope(sqlite_operation_audit_payload)
    assert sqlite_operation_audit_payload["data"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert sqlite_operation_audit_payload["data"]["total"] == 1
    assert sqlite_operation_audit_payload["data"]["items"][0]["resourceId"] == task.id
    assert sqlite_operation_audit_payload["data"]["items"][0]["action"] == "REVIEW_APPROVE"

    assert_api_envelope(sqlite_agent_entity_list_payload)
    assert sqlite_agent_entity_list_payload["data"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert sqlite_agent_entity_list_payload["data"]["localSqliteRead"] is True
    assert sqlite_agent_entity_list_payload["data"]["total"] == 1
    assert sqlite_agent_entity_list_payload["data"]["items"][0]["id"] == agent_entity.id
    assert sqlite_agent_entity_list_payload["data"]["items"][0]["sourceTaskId"] == task.id
    assert sqlite_agent_entity_list_payload["data"]["productionDatabaseWritten"] is False

    assert_api_envelope(sqlite_agent_entity_get_payload)
    assert sqlite_agent_entity_get_payload["data"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert sqlite_agent_entity_get_payload["data"]["agentEntityRecord"]["id"] == agent_entity.id
    assert sqlite_agent_entity_get_payload["data"]["agentEntityImportActivity"]["mode"] == (
        "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    )
    assert sqlite_agent_entity_get_payload["data"]["productionDatabaseWritten"] is False

    assert_api_envelope(readiness_payload)
    readiness = readiness_payload["data"]["backendCoreReadiness"]
    assert readiness["coreSqliteStaging"]["enabled"] is True
    assert readiness["coreSqliteStaging"]["policy"]["dbPathSource"] == "REQUEST_CORE_DB_PATH"
    assert readiness["coreSqliteStaging"]["summary"]["available"] is True
    assert readiness["coreSqliteStaging"]["summary"]["taskTotal"] == 1
    assert readiness["coreSqliteStaging"]["summary"]["agentEntityTotal"] == 1
    assert readiness["coreSqliteStaging"]["summary"]["productionDatabaseWritten"] is False

    assert_api_envelope(method_payload)
    assert method_payload["success"] is False
    assert method_payload["code"] == "METHOD_NOT_ALLOWED"


def test_backend_core_db_api_rejects_unsupported_repository_kind_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_BACKEND_CORE_REPOSITORY_KIND", "postgres")
    db_path = tmp_path / "backend-core.sqlite3"

    payload = handle_request(
        "GET",
        f"/api/backend/core-db/summary?{urlencode({'coreDbPath': str(db_path)})}",
        store_path=tmp_path / "store.json",
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "BACKEND_CORE_REPOSITORY_KIND_UNSUPPORTED"
    assert payload["errors"][0]["field"] == "LAB_BACKEND_CORE_REPOSITORY_KIND"
    assert db_path.exists() is False


def test_backend_core_db_api_uses_database_url_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", f"sqlite:///{(tmp_path / 'backend-core-url.sqlite3').as_posix()}")
    store_path = tmp_path / "store.json"
    db_path = tmp_path / "backend-core-url.sqlite3"

    missing_summary_payload = handle_request(
        "GET",
        "/api/backend/core-db/summary",
        store_path=store_path,
    )
    assert_api_envelope(missing_summary_payload)
    missing_summary = missing_summary_payload["data"]["backendCoreRepository"]
    assert missing_summary["available"] is False
    assert missing_summary["dbPath"] == str(db_path)
    assert missing_summary_payload["data"]["policy"]["dbPathSource"] == "ENV_DATABASE_URL"
    assert missing_summary_payload["data"]["policy"]["databaseUrlConfigured"] is True
    assert db_path.exists() is False

    init_payload = handle_request(
        "POST",
        "/api/backend/core-db/init",
        store_path=store_path,
        body={"actor": "teacher_1"},
    )
    summary_payload = handle_request(
        "GET",
        "/api/backend/core-db/summary",
        store_path=store_path,
    )

    assert_api_envelope(init_payload)
    assert init_payload["data"]["backendCoreRepository"]["dbPath"] == str(db_path)
    assert init_payload["data"]["operationAuditEvent"]["resourceId"] == str(db_path)
    assert db_path.exists()

    assert_api_envelope(summary_payload)
    summary = summary_payload["data"]["backendCoreRepository"]
    assert summary["available"] is True
    assert summary["dbPath"] == str(db_path)
    assert summary_payload["data"]["policy"]["dbPathSource"] == "ENV_DATABASE_URL"
    assert summary_payload["data"]["productionDatabaseWritten"] is False


def test_backend_core_db_api_reports_unregistered_external_database_adapter_without_secret_leak(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_BACKEND_CORE_DATABASE_URL", "postgresql://user:secret@example.invalid/prod")

    payload = handle_request(
        "GET",
        "/api/backend/core-db/summary",
        store_path=tmp_path / "store.json",
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "BACKEND_CORE_REPOSITORY_ADAPTER_UNAVAILABLE"
    assert payload["errors"] == [{"field": "repositoryKind", "reason": "postgresql adapter not registered"}]
    assert "secret" not in json.dumps(payload, ensure_ascii=False)
    assert "example.invalid" not in json.dumps(payload, ensure_ascii=False)


def test_backend_core_write_through_generation_and_review_api(tmp_path):
    store_path = tmp_path / "store.json"
    db_path = tmp_path / "backend-core-write-through.sqlite3"
    generate_payload = handle_request(
        "POST",
        "/api/labs/generate",
        store_path=store_path,
        body={
            "input": "examples/input/demo-source.md",
            "coreDbPath": str(db_path),
        },
    )
    task_id = generate_payload["data"]["task"]["id"]
    approve_payload = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1", "coreDbPath": str(db_path)},
    )
    core_query = urlencode({"coreDbPath": str(db_path)})
    task_payload = handle_request("GET", f"/api/ai-tasks/{task_id}?{core_query}", store_path=store_path)
    task_list_payload = handle_request(
        "GET",
        f"/api/ai-tasks?{urlencode({'coreDbPath': str(db_path), 'status': 'APPROVED'})}",
        store_path=store_path,
    )
    artifact_payload = handle_request(
        "GET",
        f"/api/artifacts?{urlencode({'coreDbPath': str(db_path), 'taskId': task_id})}",
        store_path=store_path,
    )
    review_audit_payload = handle_request(
        "GET",
        f"/api/review-audit-events?{urlencode({'coreDbPath': str(db_path), 'taskId': task_id})}",
        store_path=store_path,
    )
    operation_audit_payload = handle_request(
        "GET",
        f"/api/audit-events?{urlencode({'coreDbPath': str(db_path), 'resourceType': 'AI_TASK', 'resourceId': task_id})}",
        store_path=store_path,
    )
    summary_payload = handle_request(
        "GET",
        f"/api/backend/core-db/summary?{urlencode({'coreDbPath': str(db_path)})}",
        store_path=store_path,
    )

    assert_api_envelope(generate_payload)
    generate_write = generate_payload["data"]["backendCoreWriteThrough"]
    assert generate_write["mode"] == "LOCAL_SQLITE_BACKEND_CORE_WRITE_THROUGH"
    assert generate_write["localSqliteWritten"] is True
    assert generate_write["taskWritten"] is True
    assert generate_write["artifactsWritten"] == 2
    assert generate_write["productionDatabaseWritten"] is False
    assert db_path.exists()

    assert_api_envelope(approve_payload)
    approve_write = approve_payload["data"]["backendCoreWriteThrough"]
    assert approve_write["localSqliteWritten"] is True
    assert approve_write["taskWritten"] is True
    assert approve_write["reviewAuditEventWritten"] is True
    assert approve_write["operationAuditEventWritten"] is True
    assert approve_write["artifactsWritten"] == 0

    assert_api_envelope(task_payload)
    assert task_payload["data"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert task_payload["data"]["task"]["id"] == task_id
    assert task_payload["data"]["task"]["status"] == "APPROVED"
    assert task_payload["data"]["task"]["reviewer"] == "teacher_1"

    assert_api_envelope(task_list_payload)
    assert task_list_payload["data"]["total"] == 1
    assert task_list_payload["data"]["items"][0]["id"] == task_id

    assert_api_envelope(artifact_payload)
    assert artifact_payload["data"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert artifact_payload["data"]["total"] == 2
    assert {item["kind"] for item in artifact_payload["data"]["items"]} == {"MATERIAL_ANALYSIS", "LAB_DSL"}

    assert_api_envelope(review_audit_payload)
    assert review_audit_payload["data"]["total"] == 1
    assert review_audit_payload["data"]["items"][0]["action"] == "APPROVE"

    assert_api_envelope(operation_audit_payload)
    assert operation_audit_payload["data"]["total"] == 1
    assert operation_audit_payload["data"]["items"][0]["action"] == "REVIEW_APPROVE"

    assert_api_envelope(summary_payload)
    summary = summary_payload["data"]["backendCoreRepository"]
    assert summary["taskTotal"] == 1
    assert summary["artifactTotal"] == 2
    assert summary["reviewAuditTotal"] == 1
    assert summary["operationAuditTotal"] == 1
    assert summary["tasksByStatus"] == {"APPROVED": 1}


def test_backend_core_task_service_api_create_review_and_readonly_queries(tmp_path):
    store_path = tmp_path / "store.json"
    db_path = tmp_path / "backend-core-task-service-api.sqlite3"
    create_payload = handle_request(
        "POST",
        "/api/backend/core-tasks",
        store_path=store_path,
        body={
            "coreDbPath": str(db_path),
            "taskType": "LAB_GENERATION",
            "title": "Backend Core API Lab",
            "inputType": "markdown",
            "inputRef": "examples/input/demo-source.md",
            "finalResultPath": "examples/output/backend-core-api-lab.json",
            "actor": "teacher_1",
            "artifacts": [
                {
                    "kind": "LAB_DSL",
                    "path": "examples/output/backend-core-api-lab.json",
                    "title": "Backend Core API Lab DSL",
                    "metadata": {"schemaValidated": True},
                }
            ],
        },
    )
    task_id = create_payload["data"]["task"]["id"]
    approve_payload = handle_request(
        "POST",
        f"/api/backend/core-tasks/{task_id}/approve",
        store_path=store_path,
        body={"coreDbPath": str(db_path), "reviewer": "teacher_2"},
    )
    core_query = urlencode({"coreDbPath": str(db_path)})
    task_payload = handle_request("GET", f"/api/ai-tasks/{task_id}?{core_query}", store_path=store_path)
    core_task_list_payload = handle_request(
        "GET",
        f"/api/backend/core-tasks?{urlencode({'coreDbPath': str(db_path), 'status': 'APPROVED'})}",
        store_path=store_path,
    )
    core_task_get_payload = handle_request(
        "GET",
        f"/api/backend/core-tasks/{task_id}?{core_query}",
        store_path=store_path,
    )
    artifact_payload = handle_request(
        "GET",
        f"/api/artifacts?{urlencode({'coreDbPath': str(db_path), 'taskId': task_id})}",
        store_path=store_path,
    )
    review_audit_payload = handle_request(
        "GET",
        f"/api/review-audit-events?{urlencode({'coreDbPath': str(db_path), 'taskId': task_id})}",
        store_path=store_path,
    )
    operation_audit_payload = handle_request(
        "GET",
        f"/api/audit-events?{urlencode({'coreDbPath': str(db_path), 'resourceType': 'AI_TASK', 'resourceId': task_id})}",
        store_path=store_path,
    )
    mock_store_list = handle_request("GET", "/api/ai-tasks", store_path=store_path)

    assert_api_envelope(create_payload)
    create_service = create_payload["data"]["backendCoreTaskService"]
    assert create_payload["data"]["task"]["status"] == "WAITING_REVIEW"
    assert create_payload["data"]["task"]["createdBy"] == "teacher_1"
    assert create_payload["data"]["artifacts"][0]["kind"] == "LAB_DSL"
    assert create_payload["data"]["operationAuditEvent"]["action"] == "BACKEND_CORE_TASK_CREATE"
    assert create_service["mode"] == "LOCAL_SQLITE_BACKEND_CORE_SERVICE"
    assert create_service["repositoryContractUsed"] is True
    assert create_service["jsonStoreWritten"] is False
    assert create_service["taskWritten"] is True
    assert create_service["artifactsWritten"] == 1

    assert_api_envelope(approve_payload)
    approve_service = approve_payload["data"]["backendCoreTaskService"]
    assert approve_payload["data"]["task"]["status"] == "APPROVED"
    assert approve_payload["data"]["task"]["reviewer"] == "teacher_2"
    assert approve_payload["data"]["reviewAuditEvent"]["action"] == "APPROVE"
    assert approve_payload["data"]["operationAuditEvent"]["action"] == "REVIEW_APPROVE"
    assert approve_service["reviewAuditEventWritten"] is True
    assert approve_service["operationAuditEventWritten"] is True
    assert approve_service["realPublish"] is False

    assert_api_envelope(task_payload)
    assert task_payload["data"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_READONLY"
    assert task_payload["data"]["task"]["status"] == "APPROVED"
    assert_api_envelope(core_task_list_payload)
    assert core_task_list_payload["data"]["backendCoreTaskService"]["mode"] == "LOCAL_SQLITE_BACKEND_CORE_SERVICE_READONLY"
    assert core_task_list_payload["data"]["backendCoreTaskService"]["repositoryContractUsed"] is True
    assert core_task_list_payload["data"]["backendCoreTaskService"]["jsonStoreRead"] is False
    assert core_task_list_payload["data"]["total"] == 1
    assert core_task_list_payload["data"]["items"][0]["id"] == task_id
    assert core_task_list_payload["data"]["items"][0]["status"] == "APPROVED"
    assert_api_envelope(core_task_get_payload)
    assert core_task_get_payload["data"]["task"]["id"] == task_id
    assert core_task_get_payload["data"]["task"]["status"] == "APPROVED"
    assert core_task_get_payload["data"]["backendCoreTaskService"]["localSqliteRead"] is True
    assert_api_envelope(artifact_payload)
    assert artifact_payload["data"]["total"] == 1
    assert artifact_payload["data"]["items"][0]["metadata"]["schemaValidated"] is True
    assert_api_envelope(review_audit_payload)
    assert review_audit_payload["data"]["total"] == 1
    assert_api_envelope(operation_audit_payload)
    assert {item["action"] for item in operation_audit_payload["data"]["items"]} == {
        "BACKEND_CORE_TASK_CREATE",
        "REVIEW_APPROVE",
    }
    assert_api_envelope(mock_store_list)
    assert mock_store_list["data"]["total"] == 0


def test_backend_core_task_service_api_validates_input_and_method(tmp_path):
    db_path = tmp_path / "backend-core-task-service-validation.sqlite3"

    missing_actor = handle_request(
        "POST",
        "/api/backend/core-tasks",
        store_path=tmp_path / "store.json",
        body={
            "coreDbPath": str(db_path),
            "taskType": "LAB_GENERATION",
            "title": "Missing actor",
            "inputType": "markdown",
            "inputRef": "examples/input/demo-source.md",
        },
    )
    method_payload = handle_request(
        "DELETE",
        f"/api/backend/core-tasks?{urlencode({'coreDbPath': str(db_path)})}",
        store_path=tmp_path / "store.json",
    )

    assert_api_envelope(missing_actor)
    assert missing_actor["success"] is False
    assert missing_actor["code"] == "BACKEND_CORE_TASK_VALIDATION_ERROR"
    assert missing_actor["errors"][0]["field"] == "actor"
    assert_api_envelope(method_payload)
    assert method_payload["code"] == "METHOD_NOT_ALLOWED"


def test_backend_core_task_service_api_review_requires_supported_decision(tmp_path):
    store_path = tmp_path / "store.json"
    db_path = tmp_path / "backend-core-task-service-invalid-review.sqlite3"
    create_payload = handle_request(
        "POST",
        "/api/backend/core-tasks",
        store_path=store_path,
        body={
            "coreDbPath": str(db_path),
            "taskType": "PPT_GENERATION",
            "title": "Backend Core API PPT",
            "inputType": "markdown",
            "inputRef": "examples/input/demo-source.md",
            "actor": "teacher_1",
        },
    )
    task_id = create_payload["data"]["task"]["id"]

    invalid_review = handle_request(
        "POST",
        f"/api/backend/core-tasks/{task_id}/review",
        store_path=store_path,
        body={"coreDbPath": str(db_path), "reviewer": "teacher_2", "decision": "publish"},
    )

    assert_api_envelope(create_payload)
    assert_api_envelope(invalid_review)
    assert invalid_review["success"] is False
    assert invalid_review["code"] == "BACKEND_CORE_TASK_REVIEW_DECISION_UNSUPPORTED"
    assert invalid_review["errors"][0]["field"] == "decision"


def test_exam_mock_import_mirrors_entity_to_core_repository_for_dry_run(tmp_path):
    store_path = tmp_path / "store.json"
    core_db_path = tmp_path / "core.sqlite3"
    generated = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo", "coreDbPath": str(core_db_path)},
    )
    task_id = generated["data"]["task"]["id"]
    approved = handle_request(
        "POST",
        f"/api/ai-tasks/{task_id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1", "coreDbPath": str(core_db_path)},
    )
    preview = handle_request(
        "POST",
        "/api/exams/import-preview",
        store_path=store_path,
        body={
            "taskId": task_id,
            "reviewer": "teacher_1",
            "output": str(tmp_path / "exam-preview.json"),
            "coreDbPath": str(core_db_path),
        },
    )
    mock_import = handle_request(
        "POST",
        "/api/exams/mock-import",
        store_path=store_path,
        body={
            "taskId": task_id,
            "reviewer": "teacher_1",
            "output": str(tmp_path / "exam-mock-import.json"),
            "coreDbPath": str(core_db_path),
        },
    )
    entity_id = mock_import["data"]["agentEntityRecord"]["id"]
    core_query = urlencode({"coreDbPath": str(core_db_path)})
    core_entity = handle_request(
        "GET",
        f"/api/platform-entities/{entity_id}?{core_query}",
        store_path=store_path,
    )
    dry_run = handle_request(
        "POST",
        f"/api/platform-entities/{entity_id}/import-dry-run",
        store_path=store_path,
        body={
            "reviewer": "teacher_1",
            "output": str(tmp_path / "exam-dry-run.json"),
            "contractConfig": "examples/input/platform-contract.json",
            "coreDbPath": str(core_db_path),
        },
    )

    assert generated["success"] is True
    assert approved["data"]["task"]["status"] == "APPROVED"
    assert preview["success"] is True
    assert preview["data"]["backendCoreWriteThrough"]["artifactsWritten"] == 1
    assert mock_import["success"] is True
    assert mock_import["data"]["backendCoreWriteThrough"]["agentEntityWritten"] is True
    assert core_entity["data"]["agentEntityRecord"]["id"] == entity_id
    assert dry_run["success"] is True
    assert dry_run["data"]["agentEntityImportDryRun"]["agentEntityId"] == entity_id
    assert dry_run["data"]["agentEntityImportDryRun"]["safety"]["realAgentImport"] is False

    readiness = handle_request(
        "GET",
        f"/api/review-tasks/{task_id}/core-readiness?{core_query}",
        store_path=store_path,
    )
    report = readiness["data"]["coreWorkflowReadinessReport"]
    assert report["summary"]["platformRequiredTotal"] == 2
    assert report["summary"]["platformPreviewCreatedTotal"] == 1
    assert report["summary"]["platformMockImportCreatedTotal"] == 1
    assert report["summary"]["stepTotal"] == 4
    assert report["recommendedNextAction"] == "create_platform_import_preview"
    assert report["nextToolRecommendation"]["reasonCode"] == "PLATFORM_IMPORT_PREVIEW_PENDING"


def test_grading_job_api_create_run_list_get_and_review_detail(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="API local grading job",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_api_grading_job",
    )
    JsonTaskStore(store_path).save(task)
    output = tmp_path / "api-grading-job-evidence-auto.json"

    create_payload = handle_request(
        "POST",
        "/api/grading/jobs",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output),
            "submissionId": "submission_job_api_001",
            "taskId": task.id,
            "candidateId": "candidate_job_api_001",
            "reviewer": "teacher_1",
        },
    )
    job_id = create_payload["data"]["gradingJob"]["id"]
    run_payload = handle_request("POST", f"/api/grading/jobs/{job_id}/run", store_path=store_path)
    list_payload = handle_request("GET", f"/api/grading/jobs?taskId={task.id}", store_path=store_path)
    get_payload = handle_request("GET", f"/api/grading/jobs/{job_id}", store_path=store_path)
    detail_payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(create_payload)
    assert create_payload["data"]["gradingJob"]["status"] == "QUEUED"
    assert create_payload["data"]["queuePersistedToProduction"] is False
    assert_api_envelope(run_payload)
    job = run_payload["data"]["gradingJob"]
    record = run_payload["data"]["gradingRecord"]
    assert job["status"] == "WAITING_REVIEW"
    assert job["gradingRecordId"] == record["id"]
    assert record["submissionId"] == "submission_job_api_001"
    assert record["status"] == "NEEDS_EVIDENCE"
    assert run_payload["data"]["operationAuditEvent"]["action"] == "GRADING_JOB_RUN"
    assert run_payload["data"]["workerStarted"] is False
    assert output.exists()

    assert_api_envelope(list_payload)
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["id"] == job_id
    assert_api_envelope(get_payload)
    assert get_payload["data"]["gradingJob"]["id"] == job_id
    assert_api_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["gradingJobs"]["visible"] is True
    assert detail["gradingJobs"]["summary"]["waitingReviewTotal"] == 1
    assert detail["gradingJobs"]["summary"]["latestGradingRecordId"] == record["id"]
    assert detail["gradingRecords"]["total"] == 1
    assert detail["summary"]["gradingJobTotal"] == 1
    assert detail["summary"]["gradingJobLatestStatus"] == "WAITING_REVIEW"


def test_grading_worker_api_runs_sqlite_job_once_and_updates_review_detail(tmp_path):
    store_path = tmp_path / "store.json"
    db_path = tmp_path / "grading.sqlite3"
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="API local grading worker",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_api_grading_worker",
    )
    JsonTaskStore(store_path).save(task)
    output = tmp_path / "api-worker-evidence-auto.json"
    create_payload = handle_request(
        "POST",
        "/api/grading/jobs",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output),
            "submissionId": "submission_worker_api_001",
            "taskId": task.id,
            "reviewer": "teacher_1",
        },
    )
    job_id = create_payload["data"]["gradingJob"]["id"]
    sync_payload = handle_request(
        "POST",
        "/api/grading/db/sync-local",
        store_path=store_path,
        body={"dbPath": str(db_path), "actor": "teacher_1"},
    )
    worker_payload = handle_request(
        "POST",
        "/api/grading/workers/run-once",
        store_path=store_path,
        body={"dbPath": str(db_path), "jobId": job_id, "actor": "worker_1", "leaseSeconds": 90, "maxAttempts": 5},
    )
    detail_payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(create_payload)
    assert_api_envelope(sync_payload)
    assert sync_payload["data"]["gradingRepositorySync"]["jobsSynced"] == 1
    assert_api_envelope(worker_payload)
    result = worker_payload["data"]
    assert result["workerRun"]["status"] == "COMPLETED"
    assert result["workerRun"]["claimOwner"] == "worker_1"
    assert result["workerRun"]["attemptCount"] == 1
    assert result["workerRun"]["leaseSeconds"] == 90
    assert result["workerRun"]["maxAttempts"] == 5
    assert result["claimRecovery"]["expiredClaimTotal"] == 0
    assert result["gradingJob"]["status"] == "WAITING_REVIEW"
    assert result["gradingJob"]["claimOwner"] == "worker_1"
    assert result["gradingJob"]["attemptCount"] == 1
    assert result["gradingRecord"]["submissionId"] == "submission_worker_api_001"
    assert result["operationAuditEvent"]["action"] == "GRADING_JOB_RUN"
    assert result["safety"]["workerStarted"] is True
    assert result["safety"]["claimLeaseUsed"] is True
    assert result["safety"]["expiredClaimRecoveryEnabled"] is True
    assert result["safety"]["productionQueueUsed"] is False
    assert output.exists()

    assert_api_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["gradingJobs"]["summary"]["latestGradingRecordId"] == result["gradingRecord"]["id"]
    assert detail["gradingRecords"]["total"] == 1


def test_grading_worker_api_drains_sqlite_jobs_with_backend_default_db(tmp_path, monkeypatch):
    store_path = tmp_path / "store.json"
    db_path = tmp_path / "backend-default-drain-grading.sqlite3"
    monkeypatch.setenv("LAB_BACKEND_GRADING_DB_PATH", str(db_path))
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="API local grading worker drain",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_api_grading_worker_drain",
    )
    JsonTaskStore(store_path).save(task)
    for index in range(2):
        create_payload = handle_request(
            "POST",
            "/api/grading/jobs",
            store_path=store_path,
            body={
                "grading": "templates/grading/examples/mixed-checks.yaml",
                "submission": "examples/submissions/readonly-demo",
                "output": str(tmp_path / f"api-worker-drain-evidence-auto-{index}.json"),
                "submissionId": f"submission_worker_drain_api_{index}",
                "taskId": task.id,
                "reviewer": "teacher_1",
            },
        )
        assert_api_envelope(create_payload)
        assert create_payload["data"]["dbPathSource"] == "BACKEND_DEFAULT_ENV"

    worker_payload = handle_request(
        "POST",
        "/api/grading/workers/drain-once",
        store_path=store_path,
        body={"actor": "worker_1", "limit": 5, "leaseSeconds": 90, "maxAttempts": 5},
    )
    list_payload = handle_request("GET", f"/api/grading/jobs?taskId={task.id}", store_path=store_path)
    detail_payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(worker_payload)
    result = worker_payload["data"]
    assert result["workerDrain"]["status"] == "COMPLETED"
    assert result["workerDrain"]["executedTotal"] == 2
    assert result["workerDrain"]["noopReached"] is True
    assert result["workerDrain"]["limit"] == 5
    assert result["workerDrain"]["leaseSeconds"] == 90
    assert result["workerDrain"]["maxAttempts"] == 5
    assert result["workerDrain"]["quota"]["limitReached"] is False
    assert result["workerDrain"]["quota"]["queueMayStillHaveRunnableJobs"] is False
    assert result["workerDrain"]["resourceCleanup"]["retainedReportTotal"] == 2
    assert result["workerDrain"]["resourceCleanup"]["cleanupExecuted"] is False
    assert [item["status"] for item in result["workerRuns"]] == ["COMPLETED", "COMPLETED", "NOOP"]
    assert result["operationAuditEvent"]["action"] == "GRADING_WORKER_DRAIN"
    assert result["operationAuditEvent"]["detail"]["resourceCleanup"]["productionResourceDeleted"] is False
    assert result["safety"]["singleProcessSequentialDrain"] is True
    assert result["safety"]["quotaEnforced"] is True
    assert result["safety"]["resourceCleanupPlanned"] is True
    assert result["safety"]["persistentBackgroundWorker"] is False
    assert result["safety"]["productionQueueUsed"] is False
    assert db_path.exists()

    assert_api_envelope(list_payload)
    assert list_payload["data"]["dbPathSource"] == "BACKEND_DEFAULT_ENV"
    assert sorted(item["status"] for item in list_payload["data"]["items"]) == ["WAITING_REVIEW", "WAITING_REVIEW"]
    assert_api_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["gradingRecords"]["total"] == 2
    assert detail["gradingJobs"]["summary"]["waitingReviewTotal"] == 2


def test_grading_worker_api_drain_rejects_invalid_limit(tmp_path):
    store_path = tmp_path / "store.json"
    payload = handle_request(
        "POST",
        "/api/grading/workers/drain-once",
        store_path=store_path,
        body={"dbPath": str(tmp_path / "grading.sqlite3"), "limit": 21},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "limit"


def test_grading_job_api_sqlite_mode_create_run_list_get_and_review_detail(tmp_path):
    store_path = tmp_path / "store.json"
    db_path = tmp_path / "grading.sqlite3"
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="API local grading job sqlite mode",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_api_grading_job_sqlite",
    )
    JsonTaskStore(store_path).save(task)
    output = tmp_path / "api-sqlite-job-evidence-auto.json"

    create_payload = handle_request(
        "POST",
        "/api/grading/jobs",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output),
            "submissionId": "submission_sqlite_api_001",
            "taskId": task.id,
            "candidateId": "candidate_sqlite_api_001",
            "reviewer": "teacher_1",
            "dbPath": str(db_path),
        },
    )
    job_id = create_payload["data"]["gradingJob"]["id"]
    query = urlencode({"taskId": task.id, "dbPath": str(db_path)})
    get_query = urlencode({"dbPath": str(db_path)})
    list_payload = handle_request("GET", f"/api/grading/jobs?{query}", store_path=store_path)
    get_payload = handle_request("GET", f"/api/grading/jobs/{job_id}?{get_query}", store_path=store_path)
    run_payload = handle_request(
        "POST",
        f"/api/grading/jobs/{job_id}/run?{get_query}",
        store_path=store_path,
    )
    detail_payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(create_payload)
    assert create_payload["data"]["mode"] == "LOCAL_SQLITE_GRADING_JOB"
    assert create_payload["data"]["localSqliteWritten"] is True
    assert create_payload["data"]["databaseWritten"] is False
    assert create_payload["data"]["productionDatabaseWritten"] is False
    assert create_payload["data"]["gradingJob"]["safety"]["localSqliteWritten"] is True
    assert db_path.exists()

    assert_api_envelope(list_payload)
    assert list_payload["data"]["mode"] == "LOCAL_SQLITE_GRADING_JOB"
    assert list_payload["data"]["total"] == 1
    assert list_payload["data"]["items"][0]["id"] == job_id
    assert list_payload["data"]["localSqliteRead"] is True
    assert_api_envelope(get_payload)
    assert get_payload["data"]["gradingJob"]["id"] == job_id
    assert get_payload["data"]["localSqliteRead"] is True

    assert_api_envelope(run_payload)
    result = run_payload["data"]
    assert result["mode"] == "LOCAL_SQLITE_GRADING_WORKER_ONCE"
    assert result["workerRun"]["status"] == "COMPLETED"
    assert result["workerRun"]["claimOwner"] == "backend-grading-worker"
    assert result["workerRun"]["attemptCount"] == 1
    assert result["gradingJob"]["status"] == "WAITING_REVIEW"
    assert result["gradingJob"]["claimOwner"] == "backend-grading-worker"
    assert result["gradingJob"]["attemptCount"] == 1
    assert result["gradingRecord"]["submissionId"] == "submission_sqlite_api_001"
    assert result["safety"]["workerStarted"] is True
    assert result["safety"]["claimLeaseUsed"] is True
    assert result["productionDatabaseWritten"] is False
    assert output.exists()

    assert_api_envelope(detail_payload)
    detail = detail_payload["data"]["reviewDetail"]
    assert detail["gradingJobs"]["summary"]["latestGradingRecordId"] == result["gradingRecord"]["id"]
    assert detail["gradingRecords"]["total"] == 1


def test_grading_job_api_uses_backend_default_sqlite_without_request_db_path(tmp_path, monkeypatch):
    store_path = tmp_path / "store.json"
    db_path = tmp_path / "backend-default-grading.sqlite3"
    monkeypatch.setenv("LAB_BACKEND_GRADING_DB_PATH", str(db_path))
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="API backend default grading db",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_api_backend_default_grading_db",
    )
    JsonTaskStore(store_path).save(task)
    output = tmp_path / "api-backend-default-job-evidence-auto.json"

    create_payload = handle_request(
        "POST",
        "/api/grading/jobs",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output),
            "submissionId": "submission_backend_default_api_001",
            "taskId": task.id,
            "reviewer": "teacher_1",
        },
    )
    job_id = create_payload["data"]["gradingJob"]["id"]
    list_payload = handle_request("GET", f"/api/grading/jobs?taskId={task.id}", store_path=store_path)
    get_payload = handle_request("GET", f"/api/grading/jobs/{job_id}", store_path=store_path)
    run_payload = handle_request("POST", f"/api/grading/jobs/{job_id}/run", store_path=store_path)

    assert_api_envelope(create_payload)
    assert create_payload["data"]["mode"] == "LOCAL_SQLITE_GRADING_JOB"
    assert create_payload["data"]["dbPath"] == str(db_path)
    assert create_payload["data"]["dbPathSource"] == "BACKEND_DEFAULT_ENV"
    assert create_payload["data"]["backendDefaultSqliteEnabled"] is True
    assert create_payload["data"]["localSqliteWritten"] is True

    assert_api_envelope(list_payload)
    assert list_payload["data"]["mode"] == "LOCAL_SQLITE_GRADING_JOB"
    assert list_payload["data"]["dbPath"] == str(db_path)
    assert list_payload["data"]["dbPathSource"] == "BACKEND_DEFAULT_ENV"
    assert list_payload["data"]["items"][0]["id"] == job_id
    assert_api_envelope(get_payload)
    assert get_payload["data"]["dbPathSource"] == "BACKEND_DEFAULT_ENV"
    assert get_payload["data"]["gradingJob"]["id"] == job_id

    assert_api_envelope(run_payload)
    result = run_payload["data"]
    assert result["mode"] == "LOCAL_SQLITE_GRADING_WORKER_ONCE"
    assert result["dbPath"] == str(db_path)
    assert result["dbPathSource"] == "BACKEND_DEFAULT_ENV"
    assert result["workerRun"]["status"] == "COMPLETED"
    assert result["gradingJob"]["status"] == "WAITING_REVIEW"
    assert db_path.exists()
    assert output.exists()


def test_grading_job_api_request_db_path_overrides_backend_default_sqlite(tmp_path, monkeypatch):
    store_path = tmp_path / "store.json"
    backend_default_db = tmp_path / "backend-default-unused.sqlite3"
    request_db = tmp_path / "request-grading.sqlite3"
    monkeypatch.setenv("LAB_BACKEND_GRADING_DB_PATH", str(backend_default_db))
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="API request db overrides backend default",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_api_request_db_override",
    )
    JsonTaskStore(store_path).save(task)
    output = tmp_path / "api-request-db-override-evidence-auto.json"

    create_payload = handle_request(
        "POST",
        "/api/grading/jobs",
        store_path=store_path,
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output),
            "submissionId": "submission_request_db_override_001",
            "taskId": task.id,
            "dbPath": str(request_db),
        },
    )

    assert_api_envelope(create_payload)
    assert create_payload["data"]["dbPath"] == str(request_db)
    assert create_payload["data"]["dbPathSource"] == "REQUEST_DB_PATH"
    assert create_payload["data"]["backendDefaultSqliteEnabled"] is True
    assert request_db.exists()
    assert not backend_default_db.exists()


def test_grading_import_signoff_api_shows_evidence_auto_report_summary(tmp_path):
    store_path = tmp_path / "store.json"
    task = create_waiting_review_task(
        task_type="GRADING_GENERATION",
        title="API grading import signoff evidence auto",
        input_type="grading-dsl",
        input_ref="templates/grading/examples/mixed-checks.yaml",
        final_result_path="templates/grading/examples/mixed-checks.yaml",
        trace_id="trace_api_import_signoff_auto_evidence",
    )
    store = JsonTaskStore(store_path)
    store.save(task)
    store.save_artifact(
        create_artifact_record(
            kind=ArtifactKind.GRADING_DSL,
            path="templates/grading/examples/mixed-checks.yaml",
            title="Mixed Checks Grading DSL",
            status=ArtifactStatus.WAITING_REVIEW,
            trace_id="trace_api_import_signoff_auto_evidence",
            task_id=task.id,
            source_ref="templates/grading/examples/mixed-checks.yaml",
            metadata={"dslKind": "Grading", "reviewRequired": True},
        )
    )
    handle_request(
        "POST",
        f"/api/ai-tasks/{task.id}/approve",
        store_path=store_path,
        body={"reviewer": "teacher_1"},
    )
    handle_request(
        "POST",
        "/api/grading/import-preview",
        store_path=store_path,
        body={"taskId": task.id, "reviewer": "teacher_1", "output": str(tmp_path / "grading-preview.json")},
    )
    output_path = tmp_path / "grading-evidence-auto.json"
    evidence_payload = handle_request(
        "POST",
        "/api/grading/evidence-auto",
        store_path=store_path,
        body={
            "taskId": task.id,
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output_path),
        },
    )
    detail_payload = handle_request("GET", f"/api/review-tasks/{task.id}", store_path=store_path)

    assert_api_envelope(evidence_payload)
    assert evidence_payload["success"] is True
    assert_api_envelope(detail_payload)
    signoff = detail_payload["data"]["reviewDetail"]["platformImportPreviewSignoff"]
    report_summary = signoff["gradingEvidenceReportSummary"]
    assert report_summary["available"] is True
    assert report_summary["latestReportType"] == "GRADING_EVIDENCE_AUTO"
    assert report_summary["latestReportPath"] == str(output_path)
    assert report_summary["checkEvidenceReviewItemTotal"] == 6
    assert report_summary["manualReviewChecklistStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert report_summary["decisionNoteRecommendation"] == "needs-evidence"
    assert report_summary["nextRequiredAction"] == "record_needs_evidence_decision_note_or_collect_more_evidence"
    assert report_summary["autoApproveAllowed"] is False
    grading_signoff = next(item for item in signoff["items"] if item["agentEntity"] == "grading_rule")
    assert grading_signoff["gradingEvidenceReportSummary"] == report_summary
    assert signoff["summary"]["gradingEvidenceReportAvailable"] is True

    precheck = detail_payload["data"]["reviewDetail"]["preApproveReviewCheck"]
    assert precheck["summary"]["scorePreviewAvailable"] is True
    assert precheck["summary"]["scorePreviewStatus"] == "PARTIAL_SCORE_PREVIEW_NEEDS_MORE_EVIDENCE"
    assert precheck["summary"]["scorePreviewEarnedScore"] == 40
    assert precheck["summary"]["scorePreviewTotalScore"] == 100
    assert precheck["summary"]["scorePreviewCoveredScore"] == 50
    assert precheck["summary"]["scorePreviewMissingScore"] == 50
    assert precheck["summary"]["scorePreviewCoverageRatio"] == 0.5
    assert precheck["summary"]["scorePreviewReadyForDecisionNote"] is False
    assert precheck["summary"]["scorePreviewMissingEvidenceTotal"] == 2
    assert set(precheck["summary"]["scorePreviewMissingCheckIds"]) == {"check_stdout_accuracy", "check_pytest"}
    assert precheck["summary"]["manualReviewChecklistStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert precheck["summary"]["decisionNoteRecommendation"] == "needs-evidence"
    assert precheck["summary"]["decisionNoteRecommendationReason"] == (
        "Controlled command evidence is missing or runtime is unavailable."
    )
    assert precheck["summary"]["nextDecisionNoteAction"] == "collect_or_review_grading_evidence_before_decision_note"

    core_payload = handle_request("GET", f"/api/review-tasks/{task.id}/core-readiness", store_path=store_path)
    assert_api_envelope(core_payload)
    core = core_payload["data"]["coreWorkflowReadinessReport"]
    assert core["summary"]["gradingManualReviewChecklistStatus"] == "NEEDS_CONTROLLED_COMMAND_EVIDENCE"
    assert core["summary"]["finalReviewState"] == "NEEDS_MORE_EVIDENCE"
    assert core["summary"]["gradingScorePreviewAvailable"] is True
    assert core["summary"]["gradingScorePreviewStatus"] == "PARTIAL_SCORE_PREVIEW_NEEDS_MORE_EVIDENCE"
    assert core["summary"]["gradingScorePreviewEarnedScore"] == 40
    assert core["summary"]["gradingScorePreviewTotalScore"] == 100
    assert core["summary"]["gradingScorePreviewCoveredScore"] == 50
    assert core["summary"]["gradingScorePreviewMissingScore"] == 50
    assert core["summary"]["gradingScorePreviewCoverageRatio"] == 0.5
    assert core["summary"]["gradingScorePreviewReadyForDecisionNote"] is False
    assert core["summary"]["gradingScorePreviewMissingEvidenceTotal"] == 2
    assert set(core["summary"]["gradingScorePreviewMissingCheckIds"]) == {"check_stdout_accuracy", "check_pytest"}
    assert core["summary"]["gradingDecisionNoteRecommendation"] == "needs-evidence"
    assert core["summary"]["gradingDecisionNoteRecommendationReason"] == (
        "Controlled command evidence is missing or runtime is unavailable."
    )
    assert core["summary"]["gradingNextDecisionNoteAction"] == "collect_or_review_grading_evidence_before_decision_note"
    assert core["recommendedNextAction"] == "collect_or_review_grading_evidence_before_decision_note"
    assert core["nextToolRecommendation"]["reasonCode"] == "GRADING_ADDITIONAL_EVIDENCE_RECOMMENDED"
    assert core["nextToolRecommendation"]["finalReviewState"] == "NEEDS_MORE_EVIDENCE"
    assert core["nextToolRecommendation"]["toolName"] == "run_grading_evidence_auto"
    assert core["nextToolRecommendation"]["argumentsPreview"]["taskId"] == task.id
    assert core["nextToolRecommendation"]["argumentsPreview"]["includeControlledCommand"] is True
    assert core["nextToolRecommendation"]["autoExecuteAllowed"] is False


def test_grading_report_api_reads_evidence_auto_report_file(tmp_path):
    output_path = tmp_path / "grading-evidence-auto.json"
    create_payload = handle_request(
        "POST",
        "/api/grading/evidence-auto",
        store_path=tmp_path / "store.json",
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output_path),
        },
    )

    payload = handle_request("GET", f"/api/grading/report?file={output_path}", store_path=tmp_path / "store.json")

    assert_api_envelope(create_payload)
    assert_api_envelope(payload)
    assert payload["success"] is True
    assert payload["data"]["report"]["mode"] == "GRADING_EVIDENCE_AUTO_REPORT"
    assert payload["data"]["report"]["sourceMode"] == "EVIDENCE_AUTO"
    assert payload["data"]["report"]["summary"]["readonlyReportIncluded"] is True
    assert payload["data"]["report"]["safety"]["autoApproveAllowed"] is False


def test_grading_evidence_auto_api_requires_output(tmp_path):
    payload = handle_request(
        "POST",
        "/api/grading/evidence-auto",
        store_path=tmp_path / "store.json",
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"] == [{"field": "output", "reason": "缺少参数"}]


def test_grading_evidence_auto_api_degrades_when_controlled_unavailable(tmp_path, monkeypatch):
    import sandbox.controlled_command_executor as controlled_executor

    def fake_docker_unavailable(*args, **kwargs):
        raise FileNotFoundError("docker not found")

    monkeypatch.setattr(controlled_executor.subprocess, "run", fake_docker_unavailable)
    output_path = tmp_path / "grading-evidence-auto-controlled.json"

    payload = handle_request(
        "POST",
        "/api/grading/evidence-auto",
        store_path=tmp_path / "store.json",
        body={
            "grading": "templates/grading/examples/mixed-checks.yaml",
            "submission": "examples/submissions/readonly-demo",
            "output": str(output_path),
            "includeControlledCommand": True,
        },
    )

    assert_api_envelope(payload)
    assert payload["success"] is True
    report = payload["data"]["gradingEvidenceAutoReport"]
    assert report["summary"]["controlledCommandRequested"] is True
    assert report["summary"]["controlledCommandIncluded"] is False
    assert report["summary"]["controlledCommandWarningTotal"] == 1
    assert report["summary"]["nextCoreActionId"] == "prepare_controlled_docker_runtime_or_manual_review"
    assert report["executionMatrix"]["summary"]["controlledCommandRuntimeWarning"] is True
    assert report["nextCoreAction"]["id"] == "prepare_controlled_docker_runtime_or_manual_review"
    assert report["manualReviewChecklist"]["status"] == "CONTROLLED_RUNTIME_UNAVAILABLE"
    assert report["manualReviewChecklist"]["decisionNoteRecommendation"]["decision"] == "needs-evidence"
    assert report["summary"]["manualReviewChecklistStatus"] == "CONTROLLED_RUNTIME_UNAVAILABLE"
    assert report["warnings"][0]["code"] == "DOCKER_RUNTIME_UNAVAILABLE"
    assert report["controlledExecutionDiagnostic"]["code"] == "DOCKER_RUNTIME_UNAVAILABLE"
    assert report["controlledExecutionProfile"]["id"] == "local-python-pytest-controlled-v1"
    assert report["steps"][1]["status"] == "SKIPPED"
    assert output_path.exists()


def test_grading_run_requires_grading(tmp_path):
    payload = handle_request("POST", "/api/grading/run", store_path=tmp_path / "store.json", body={})

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "grading"


def test_grading_run_requires_existing_file(tmp_path):
    payload = handle_request(
        "POST",
        "/api/grading/run",
        store_path=tmp_path / "store.json",
        body={"grading": str(tmp_path / "missing.yaml")},
    )

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "grading"


def test_grading_run_requires_post(tmp_path):
    payload = handle_request("GET", "/api/grading/run", store_path=tmp_path / "store.json")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_grading_report_requires_existing_file(tmp_path):
    payload = handle_request("GET", f"/api/grading/report?file={tmp_path / 'missing.json'}")

    assert_api_envelope(payload)
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "file"


def test_non_get_method_is_blocked():
    payload = handle_request("POST", "/api/ai-tasks")

    assert_api_envelope(payload)
    assert payload["code"] == "METHOD_NOT_ALLOWED"


def test_unknown_route_returns_json():
    payload = handle_request("GET", "/api/missing")

    assert_api_envelope(payload)
    assert payload["code"] == "NOT_FOUND"
