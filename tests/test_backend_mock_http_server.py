import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.mock_api import handle_request
from backend.mock_http_server import build_server, is_loopback_host, validate_bind_auth


def read_json(url):
    with urlopen(url, timeout=5) as response:
        assert response.headers["Content-Type"].startswith("application/json")
        return json.loads(response.read().decode("utf-8"))


def read_text(url):
    with urlopen(url, timeout=5) as response:
        return response.headers["Content-Type"], response.read().decode("utf-8")


def post_json(url, payload):
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        assert response.headers["Content-Type"].startswith("application/json")
        return json.loads(response.read().decode("utf-8"))


def start_server(store_path):
    server = build_server(host="127.0.0.1", port=0, store_path=store_path, quiet=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}"


def stop_server(server, thread):
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


def test_bind_auth_accepts_loopback_hosts_without_token(monkeypatch):
    monkeypatch.delenv("LAB_BACKEND_API_TOKEN", raising=False)

    assert is_loopback_host("127.0.0.1") is True
    assert is_loopback_host("::1") is True
    assert is_loopback_host("localhost") is True
    validate_bind_auth("127.0.0.1")
    validate_bind_auth("localhost")


def test_bind_auth_rejects_non_loopback_without_token(monkeypatch):
    monkeypatch.delenv("LAB_BACKEND_API_TOKEN", raising=False)

    try:
        validate_bind_auth("0.0.0.0")
    except ValueError as exc:
        assert "token" in str(exc).lower()
        assert "127.0.0.1" in str(exc)
    else:
        raise AssertionError("expected non-loopback unauthenticated bind rejection")


def test_bind_auth_accepts_non_loopback_with_token(monkeypatch):
    monkeypatch.setenv("LAB_BACKEND_API_TOKEN", "test-bind-token")
    validate_bind_auth("0.0.0.0")


def test_mock_http_server_serves_api_and_review_center(tmp_path):
    store_path = tmp_path / "store.json"
    source = tmp_path / "source.md"
    source.write_text("# Demo Source", encoding="utf-8")
    handle_request("POST", "/api/labs/generate", store_path=store_path, body={"input": str(source)})

    server, thread, base_url = start_server(store_path)
    try:
        health = read_json(f"{base_url}/api/health")
        summary = read_json(f"{base_url}/api/review-task-summary")
        content_type, html = read_text(f"{base_url}/review-center.html")
        js_type, js = read_text(f"{base_url}/review-center-data.js")
    finally:
        stop_server(server, thread)

    assert health["success"] is True
    assert health["data"]["mode"] == "MOCK_ONLY"
    assert summary["success"] is True
    assert summary["data"]["reviewTaskSummary"]["queueSummary"]["waitingReviewTotal"] == 1
    assert content_type.startswith("text/html")
    assert "review-center-data.js" in html
    assert js_type.startswith("text/javascript") or js_type.startswith("application/javascript")
    assert "/api/review-task-summary" in js
    assert "/api/review-tasks/{id}" in js


def test_mock_http_server_serves_agent_entities_page_and_api(tmp_path):
    store_path = tmp_path / "store.json"
    server, thread, base_url = start_server(store_path)
    try:
        content_type, html = read_text(f"{base_url}/platform-entities.html")
        entities = read_json(f"{base_url}/api/platform-entities")
    finally:
        stop_server(server, thread)

    assert content_type.startswith("text/html")
    assert "GET /api/platform-entities" in html
    assert "POST /api/platform-entities/{id}/import-dry-run" in html
    assert "POST /api/platform-entities/{id}/import-send" not in html
    assert "POST /api/platform-entities/{id}/import-status" not in html
    assert "POST /api/platform-entities/{id}/import-result" not in html
    assert "secretVisibleInFrontend=false" in html
    assert "realAgentImport=false" in html
    assert "realPublish=false" in html
    assert entities["success"] is True
    assert entities["data"]["total"] == 0


def test_mock_http_server_serves_ppt_generate_page_and_creates_review_task(tmp_path):
    store_path = tmp_path / "store.json"
    server, thread, base_url = start_server(store_path)
    try:
        content_type, html = read_text(f"{base_url}/ppt-generate.html")
        generated = post_json(f"{base_url}/api/ppt/generate", {"input": "examples/input/demo-source.md"})
        task_id = generated["data"]["task"]["id"]
        detail = read_json(f"{base_url}/api/review-tasks/{task_id}")
    finally:
        stop_server(server, thread)

    assert content_type.startswith("text/html")
    assert "ppt-generate-data.js" in html
    assert generated["success"] is True
    assert generated["data"]["task"]["status"] == "WAITING_REVIEW"
    assert generated["data"]["pptDsl"]["kind"] == "PPT"
    assert generated["data"]["artifact"]["kind"] == "PPT_DSL"
    assert generated["data"]["providerGeneration"]["provider"]["realLlmCalled"] is False
    assert detail["data"]["reviewDetail"]["task"]["status"] == "WAITING_REVIEW"


def test_mock_http_server_runs_all_core_generation_workspaces(tmp_path):
    """The three generation pages use the same local HTTP boundary as the browser."""
    store_path = tmp_path / "store.json"
    server, thread, base_url = start_server(store_path)
    try:
        pages = {
            "lab": read_text(f"{base_url}/lab-generate.html")[1],
            "exam": read_text(f"{base_url}/exam-generate.html")[1],
            "ppt": read_text(f"{base_url}/ppt-generate.html")[1],
        }
        lab = post_json(f"{base_url}/api/labs/generate", {"input": "examples/input/demo-source.md"})
        exam = post_json(f"{base_url}/api/exams/generate-from-lab", {"labId": "lab_demo"})
        ppt = post_json(f"{base_url}/api/ppt/generate", {"input": "examples/input/demo-source.md"})
        details = [
            read_json(f"{base_url}/api/review-tasks/{payload['data']['task']['id']}")
            for payload in (lab, exam, ppt)
        ]
    finally:
        stop_server(server, thread)

    assert "lab-generate-data.js" in pages["lab"]
    assert "exam-generate-data.js" in pages["exam"]
    assert "ppt-generate-data.js" in pages["ppt"]
    assert lab["data"]["task"]["status"] == "WAITING_REVIEW"
    assert lab["data"]["dslPath"]
    assert exam["data"]["task"]["status"] == "WAITING_REVIEW"
    assert exam["data"]["examDslPath"]
    assert exam["data"]["gradingDslPath"]
    assert exam["data"]["answerVisibleToCandidate"] is False
    assert ppt["data"]["task"]["status"] == "WAITING_REVIEW"
    assert ppt["data"]["pptDslPath"]
    assert all(detail["data"]["reviewDetail"]["task"]["status"] == "WAITING_REVIEW" for detail in details)


def test_mock_http_server_runs_local_grading_workspace_job_and_record_review(tmp_path):
    store_path = tmp_path / "store.json"
    task_payload = handle_request(
        "POST",
        "/api/exams/generate-from-lab",
        store_path=store_path,
        body={"labId": "lab_demo"},
    )
    task_id = task_payload["data"]["task"]["id"]
    output_path = tmp_path / "grading-workspace-evidence.json"
    server, thread, base_url = start_server(store_path)
    try:
        content_type, html = read_text(f"{base_url}/grading-workspace.html")
        created = post_json(
            f"{base_url}/api/grading/jobs",
            {
                "grading": "templates/grading/examples/mixed-checks.yaml",
                "submission": "examples/submissions/readonly-demo",
                "output": str(output_path),
                "submissionId": "submission_workspace_http_001",
                "taskId": task_id,
                "candidateId": "candidate_workspace_http_001",
                "reviewer": "teacher_1",
                "includeControlledCommand": False,
            },
        )
        job_id = created["data"]["gradingJob"]["id"]
        executed = post_json(f"{base_url}/api/grading/jobs/{job_id}/run", {})
        record_id = executed["data"]["gradingRecord"]["id"]
        records = read_json(f"{base_url}/api/grading/records?taskId={task_id}")
        reviewed = post_json(
            f"{base_url}/api/grading/records/{record_id}/review",
            {"reviewer": "teacher_1", "decision": "needs-evidence", "reason": "controlled Docker evidence required before approval"},
        )
    finally:
        stop_server(server, thread)

    assert content_type.startswith("text/html")
    assert "grading-workspace-data.js" in html
    assert created["data"]["gradingJob"]["status"] == "QUEUED"
    assert executed["data"]["gradingJob"]["status"] == "WAITING_REVIEW"
    assert executed["data"]["gradingRecord"]["taskId"] == task_id
    assert output_path.exists()
    assert records["data"]["total"] == 1
    assert records["data"]["items"][0]["id"] == record_id
    assert reviewed["data"]["gradingRecord"]["status"] == "NEEDS_EVIDENCE"
    assert reviewed["data"]["taskStatusChanged"] is False


def test_mock_http_server_returns_json_errors_for_missing_api(tmp_path):
    server, thread, base_url = start_server(tmp_path / "store.json")
    try:
        try:
            read_json(f"{base_url}/api/review-tasks/missing")
        except HTTPError as exc:
            payload = json.loads(exc.read().decode("utf-8"))
            status = exc.code
        else:
            raise AssertionError("expected HTTPError")
    finally:
        stop_server(server, thread)

    assert status == 404
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"
    assert payload["errors"][0]["field"] == "taskId"


def test_mock_http_server_returns_json_error_for_invalid_post_body(tmp_path):
    server, thread, base_url = start_server(tmp_path / "store.json")
    try:
        request = Request(
            f"{base_url}/api/labs/generate",
            data=b"{not-json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(request, timeout=5)
        except HTTPError as exc:
            payload = json.loads(exc.read().decode("utf-8"))
            status = exc.code
        else:
            raise AssertionError("expected HTTPError")
    finally:
        stop_server(server, thread)

    assert status == 400
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["errors"][0]["field"] == "body"


def test_mock_http_server_import_preview_updates_review_detail(tmp_path):
    store_path = tmp_path / "store.json"
    output = tmp_path / "http-lab-template-import-preview.json"
    server, thread, base_url = start_server(store_path)
    try:
        generated = post_json(f"{base_url}/api/labs/generate", {"input": "examples/input/demo-source.md"})
        task_id = generated["data"]["task"]["id"]
        pre_detail = read_json(f"{base_url}/api/review-tasks/{task_id}")
        approved = post_json(f"{base_url}/api/ai-tasks/{task_id}/approve", {"reviewer": "teacher_http"})
        approved_detail = read_json(f"{base_url}/api/review-tasks/{task_id}")
        preview = post_json(
            f"{base_url}/api/labs/import-preview",
            {"taskId": task_id, "reviewer": "teacher_http", "output": str(output)},
        )
        post_detail = read_json(f"{base_url}/api/review-tasks/{task_id}")
    finally:
        stop_server(server, thread)

    assert generated["success"] is True
    assert pre_detail["data"]["reviewDetail"]["platformImportPreviewActions"]["enabled"] is False
    assert pre_detail["data"]["reviewDetail"]["platformImportPreviewSignoff"]["missingPreviewTotal"] == 1
    assert approved["data"]["task"]["status"] == "APPROVED"
    assert approved_detail["data"]["reviewDetail"]["platformImportPreviewActions"]["enabled"] is True
    assert approved_detail["data"]["reviewDetail"]["platformImportPreviewActions"]["enabledTotal"] == 1
    assert approved_detail["data"]["reviewDetail"]["platformImportPreviewSignoff"]["readyForHumanSignoff"] is False
    assert preview["success"] is True
    assert preview["data"]["labTemplateImportPreview"]["component"] == "LabTemplateImportPreview"
    assert preview["data"]["labTemplateImportPreview"]["safety"]["databaseWritten"] is False
    assert preview["data"]["labTemplateImportPreview"]["safety"]["realAgentImport"] is False
    assert preview["data"]["labTemplateImportPreview"]["safety"]["realPublishAllowed"] is False
    assert preview["data"]["operationAuditEvent"]["action"] == "LAB_TEMPLATE_IMPORT_PREVIEW"
    assert output.exists()
    detail = post_detail["data"]["reviewDetail"]
    assert detail["platformImportPreview"]["visible"] is True
    assert detail["platformImportPreview"]["total"] == 1
    assert detail["platformImportPreview"]["items"][0]["component"] == "LabTemplateImportPreview"
    assert detail["platformImportPreview"]["items"][0]["databaseWritten"] is False
    assert detail["platformImportPreviewActions"]["previewAlreadyCreatedTotal"] == 1
    assert detail["platformImportPreviewActions"]["items"][0]["previewAlreadyCreated"] is True
    assert detail["platformImportPreviewSignoff"]["readyForHumanSignoff"] is True
    assert detail["platformImportPreviewSignoff"]["missingPreviewTotal"] == 0
    assert detail["reviewPage"]["platformImportPreview"] == detail["platformImportPreview"]
    assert detail["reviewPage"]["platformImportPreviewActions"] == detail["platformImportPreviewActions"]
    assert detail["reviewPage"]["platformImportPreviewSignoff"] == detail["platformImportPreviewSignoff"]
