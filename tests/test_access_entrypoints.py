import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    with (ROOT / path).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_access_entrypoints_is_phase5_mock_only():
    contract = load_json("delivery/access-entrypoints.json")

    assert contract["phase"] == "Phase 5"
    assert contract["mode"] == "MOCK_ONLY"
    assert contract["id"] == "phase5_access_entrypoints_delivery"
    assert contract["safety"]["manualOnly"] is True
    assert contract["safety"]["readOnly"] is True
    assert contract["safety"]["realHttpServerStarted"] is False
    assert contract["safety"]["portListening"] is False
    assert contract["safety"]["externalIpBound"] is False
    assert contract["safety"]["lanAccessEnabled"] is False
    assert contract["safety"]["publicUrlGenerated"] is False
    assert contract["safety"]["networkAccess"] is False
    assert contract["safety"]["realFrontendServerStarted"] is False
    assert contract["safety"]["realBackendStarted"] is False
    assert contract["safety"]["realMcpServerStarted"] is False
    assert contract["safety"]["realAgentStarted"] is False
    assert contract["safety"]["realLlmCalled"] is False
    assert contract["safety"]["realCloudResourceCreated"] is False
    assert contract["safety"]["sandboxExecuted"] is False
    assert contract["safety"]["contestantCodeExecuted"] is False
    assert contract["safety"]["unknownShellExecuted"] is False
    assert contract["safety"]["autoPublishAllowed"] is False
    assert contract["safety"]["realPublish"] is False
    assert contract["safety"]["remoteUploadAllowed"] is False
    assert contract["safety"]["secretVisibleInFrontend"] is False


def test_access_entrypoints_inputs_outputs_exist_and_are_local():
    contract = load_json("delivery/access-entrypoints.json")

    for entry in [*contract["inputs"], *contract["outputs"]]:
        assert entry.get("required") is True or entry.get("requiredForOperation") is True
        assert (ROOT / entry["path"]).exists(), entry["path"]
        assert not entry["path"].startswith(("http://", "https://"))

    primary = contract["accessPlan"]["primaryStaticPreview"]
    assert primary["route"] == "/access"
    assert primary["path"] == "frontend/access.html"
    assert primary["manualOnly"] is True
    assert primary["startsServer"] is False
    assert primary["bindsPort"] is False


def test_access_entrypoints_planned_urls_are_disabled_localhost_only():
    contract = load_json("delivery/access-entrypoints.json")
    plan = contract["accessPlan"]

    assert plan["externalUrlGenerated"] is False
    assert plan["tlsConfigured"] is False
    assert plan["reverseProxyConfigured"] is False
    assert plan["deploymentPackageGenerated"] is False
    assert set(plan["allowedHostsWhenRealDeploymentIsApproved"]) == {"127.0.0.1", "localhost"}
    assert {"0.0.0.0", "public-ip", "lan-ip"} <= set(plan["blockedHosts"])

    for entry in plan["plannedLocalUrls"]:
        parsed = urlparse(entry["url"])
        assert parsed.scheme == "http"
        assert parsed.hostname == entry["host"] == "127.0.0.1"
        assert parsed.port == entry["port"]
        assert entry["enabled"] is False
        assert entry["portListening"] is False
        assert entry["externalIpBound"] is False
        assert entry["externalNetworkAllowed"] is False


def test_access_entrypoints_commands_are_allowlisted():
    contract = load_json("delivery/access-entrypoints.json")
    manifest = load_json("scripts/manifest.json")
    allowed = {command["id"]: command for command in manifest["allowedCommands"]}

    assert set(contract["recommendedCommandIds"]).issubset(allowed)
    assert "test_access_entrypoints" in contract["recommendedCommandIds"]

    for command_id in contract["recommendedCommandIds"]:
        command = allowed[command_id]
        assert command["requiresNetwork"] is False
        assert command["command"].startswith("python ")
        assert "|" not in command["command"]
        assert "docker run" not in command["command"]


def test_access_entrypoints_frontend_contract_and_mock_data_are_registered():
    manifest = load_json("frontend/ui.manifest.json")
    mock_data = load_json("frontend/mock-data.json")
    prototypes = {prototype["route"]: prototype for prototype in manifest["staticPrototypes"]}
    pages = {page["route"]: page for page in manifest["pages"]}

    assert "/access" in prototypes
    assert prototypes["/access"]["path"] == "frontend/access.html"
    assert "frontend/mock-data.json.accessEntrypointsPrototype" in prototypes["/access"]["dataSources"]
    assert prototypes["/access"]["safety"]["readOnly"] is True
    assert prototypes["/access"]["safety"]["realHttpServerStarted"] is False
    assert prototypes["/access"]["safety"]["portListening"] is False
    assert prototypes["/access"]["safety"]["externalIpBound"] is False
    assert prototypes["/access"]["safety"]["networkAccess"] is False
    assert prototypes["/access"]["safety"]["realAgentStarted"] is False

    assert pages["/access"]["prototypePath"] == "frontend/access.html"
    assert pages["/access"]["apiDependencies"] == []
    assert pages["/access"]["safety"]["readOnly"] is True
    assert pages["/access"]["safety"]["realHttpServerStarted"] is False
    assert pages["/access"]["safety"]["portListening"] is False
    assert pages["/access"]["safety"]["externalIpBound"] is False
    assert pages["/access"]["safety"]["networkAccess"] is False

    access = mock_data["accessEntrypointsPrototype"]
    assert access["route"] == "/access"
    assert access["path"] == "frontend/access.html"
    assert access["summary"]["deliveryReady"] == 175
    assert access["summary"]["deliveryRequired"] == 175
    assert access["summary"]["portListeningTotal"] == 0
    assert access["safety"]["realHttpServerStarted"] is False
    assert access["safety"]["externalIpBound"] is False
    assert access["safety"]["networkAccess"] is False


def test_access_entrypoints_is_registered_for_delivery_handoff_and_signoff():
    delivery_contract = load_json("config/delivery-package.contract.json")
    delivery_index = load_json("delivery/phase1-delivery-index.json")
    handoff = load_json("delivery/phase1-handoff.json")
    operations_manual = load_json("delivery/operations-manual.json")
    final_signoff = load_json("delivery/final-signoff.json")

    deliverable_ids = {item["id"] for item in delivery_contract["deliverables"]}
    core = next(item for item in delivery_contract["acceptanceChecklist"] if item["id"] == "core_deliverables_present")
    entry_ids = {item["id"] for item in delivery_index["entryPoints"]}
    handoff_input_ids = {item["id"] for item in handoff["inputs"]}
    handoff_item_ids = {item["id"] for item in handoff["handoffItems"]}
    operations_input_ids = {item["id"] for item in operations_manual["inputs"]}
    signoff_input_ids = {item["id"] for item in final_signoff["inputs"]}
    signoff_sequence_ids = {item["id"] for item in final_signoff["signoffSequence"]}

    assert {"access_entrypoints_md", "access_entrypoints_contract", "frontend_access_entrypoints_prototype"} <= deliverable_ids
    assert {"access_entrypoints_md", "access_entrypoints_contract", "frontend_access_entrypoints_prototype"} <= set(
        core["source"]["ids"]
    )
    assert {"access_entrypoints", "access_entrypoints_contract", "access_preview"} <= entry_ids
    assert {"access_entrypoints", "access_entrypoints_contract", "access_preview"} <= handoff_input_ids
    assert {"read_access_entrypoints", "open_access_preview", "run_access_entrypoints_tests"} <= handoff_item_ids
    assert {"access_entrypoints", "access_entrypoints_contract", "access_preview"} <= operations_input_ids
    assert {"access_entrypoints", "access_entrypoints_contract", "access_preview"} <= signoff_input_ids
    assert {"read_access_entrypoints", "open_access_preview", "run_access_entrypoints_tests"} <= signoff_sequence_ids
    assert "test_access_entrypoints" in delivery_index["recommendedCommandIds"]
    assert "test_access_entrypoints" in handoff["recommendedCommandIds"]
    assert "test_access_entrypoints" in operations_manual["recommendedCommandIds"]
    assert "test_access_entrypoints" in final_signoff["recommendedCommandIds"]
    assert "python -m pytest tests/test_access_entrypoints.py" in delivery_contract["recommendedCommands"]


def test_access_entrypoints_markdown_and_html_document_usage_and_limits():
    markdown = (ROOT / "delivery/ACCESS_ENTRYPOINTS.md").read_text(encoding="utf-8")
    html = (ROOT / "frontend/access.html").read_text(encoding="utf-8")

    for heading in ["## 输入说明", "## 输出说明", "## Mock 访问入口", "## 命令示例", "## 测试方式", "## 限制说明"]:
        assert heading in markdown

    assert "frontend/access.html" in markdown
    assert "http://127.0.0.1:3000" in markdown
    assert "http://127.0.0.1:8000" in markdown
    assert "http://127.0.0.1:8080" in markdown
    assert "python -m pytest tests/test_access_entrypoints.py" in markdown
    assert "不启动真实 HTTP 服务" in markdown
    assert "不绑定 `0.0.0.0`、公网 IP 或内网 IP" in markdown
    assert "不连接真实外部平台" in markdown

    assert "Access Entrypoints" in html
    assert "175 / 175" in html
    assert "Ports Listening" in html
    assert "http://127.0.0.1:3000" in html
    assert "python -m pytest tests/test_access_entrypoints.py" in html
    assert "不绑定 0.0.0.0、公网 IP 或内网 IP" in html
