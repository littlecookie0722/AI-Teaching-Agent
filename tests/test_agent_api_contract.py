import pytest

from cli.agent_api_contract import (
    PLATFORM_IMPORT_CONTRACT_VERSION,
    AgentApiContractError,
    build_agent_publish_endpoint,
    build_agent_request_body,
    build_status_path,
    describe_agent_publish_contract,
    extract_agent_status,
    infer_agent_draft_id,
    load_agent_api_contract_config,
    suggest_publish_result_status,
    validate_agent_api_contract_config,
)
from cli.agent_entity import AgentEntityType


def test_platform_api_contract_example_config_covers_all_entity_mappings():
    config = load_agent_api_contract_config("examples/input/platform-contract.json")
    validation = validate_agent_api_contract_config(config)

    assert validation["valid"] is True
    assert validation["checkedEntityTypes"] == ["lab_template", "exam_question", "grading_rule", "ppt_deck"]
    assert validation["configuredEntityOverrideTypes"] == [
        "exam_question",
        "grading_rule",
        "lab_template",
        "ppt_deck",
    ]
    assert validation["summary"]["requestBodyMappingConfiguredEntityTotal"] == 4
    assert validation["summary"]["defaultInternalDtoEntityTotal"] == 0
    assert validation["summary"]["warningTotal"] == 0
    assert validation["safety"]["requestSent"] is False
    assert validation["safety"]["secretsRead"] is False

    for entity_type in validation["checkedEntityTypes"]:
        entity = validation["entities"][entity_type]
        assert entity["requestBodySource"] == "requestBody"
        assert entity["requestBodyMapping"]["configured"] is True
        assert entity["draftImportEndpoint"]["path"].startswith("/open/staging/")
        assert entity["statusPathTemplate"].startswith("/open/staging/")


def test_platform_api_contract_describes_all_draft_import_endpoints():
    expected_paths = {
        AgentEntityType.LAB_TEMPLATE: "/api/platform/lab-template/draft-imports",
        AgentEntityType.EXAM_QUESTION: "/api/platform/exam-question/draft-imports",
        AgentEntityType.GRADING_RULE: "/api/platform/grading-rule/draft-imports",
        AgentEntityType.PPT_DECK: "/api/platform/ppt-deck/draft-imports",
    }

    for entity_type, path in expected_paths.items():
        endpoint = build_agent_publish_endpoint(entity_type)
        contract = describe_agent_publish_contract(entity_type)

        assert endpoint == {"method": "POST", "path": path}
        assert contract["contractVersion"] == PLATFORM_IMPORT_CONTRACT_VERSION
        assert contract["entityType"] == entity_type.value
        assert contract["draftImportEndpoint"] == endpoint
        assert contract["statusPathTemplate"] == "{targetEndpointPath}/{agentDraftId}"
        assert "draftImportId" in contract["draftIdResponseKeys"]
        assert "agentStatus" in contract["statusResponseKeys"]


def test_platform_api_contract_rejects_unknown_entity_type():
    with pytest.raises(AgentApiContractError) as exc_info:
        build_agent_publish_endpoint("unknown_entity")

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.errors == [{"field": "entityType", "reason": "unknown_entity"}]


def test_platform_api_contract_infers_draft_id_from_response_aliases():
    for key in ("draftImportId", "draftId", "importId", "id"):
        response = {"body": {"json": {key: "draft_123"}}}

        assert infer_agent_draft_id(response) == "draft_123"

    assert infer_agent_draft_id({"body": {"json": {"other": "draft_123"}}}) is None
    assert infer_agent_draft_id({"body": {"json": ["draft_123"]}}) is None


def test_platform_api_contract_extracts_status_and_suggests_result_status():
    assert extract_agent_status({"body": {"json": {"agentStatus": "ACCEPTED"}}}) == "ACCEPTED"
    assert extract_agent_status({"body": {"json": {"state": "ERROR"}}}) == "ERROR"
    assert extract_agent_status({"body": {"json": {"other": "ACCEPTED"}}}) is None

    assert suggest_publish_result_status("WAITING_REVIEW") == "PENDING_MANUAL_PLATFORM_REVIEW"
    assert suggest_publish_result_status("approved") == "ACCEPTED_FOR_DRAFT"
    assert suggest_publish_result_status("rejected_for_draft") == "REJECTED_BY_PLATFORM"
    assert suggest_publish_result_status("error") == "FAILED"
    assert suggest_publish_result_status("unknown") is None


def test_platform_api_contract_builds_status_path_with_encoding_and_template_override():
    assert (
        build_status_path("/api/platform/lab-template/draft-imports", "draft 1")
        == "/api/platform/lab-template/draft-imports/draft%201"
    )
    assert (
        build_status_path(
            "/api/platform/lab-template/draft-imports/",
            "draft/1",
            "/api/platform/import-status/{draftImportId}",
        )
        == "/api/platform/import-status/draft%2F1"
    )


def test_platform_api_contract_rejects_status_path_missing_inputs():
    with pytest.raises(AgentApiContractError) as missing_endpoint:
        build_status_path("", "draft_1")
    assert missing_endpoint.value.errors == [{"field": "sendResult.targetEndpoint.path", "reason": "缺少字段"}]

    with pytest.raises(AgentApiContractError) as missing_draft_id:
        build_status_path("/api/platform/lab-template/draft-imports", "")
    assert missing_draft_id.value.errors == [{"field": "agentDraftId", "reason": "缺少参数"}]


def test_platform_api_contract_loads_config_and_applies_overrides(tmp_path):
    config_path = tmp_path / "platform-contract.json"
    config_path.write_text(
        """
{
  "statusPathTemplate": "/api/import-status/{draftImportId}",
  "draftIdResponseKeys": ["jobId"],
  "statusResponseKeys": ["reviewState"],
  "statusMapping": {
    "QUEUED": "PENDING_MANUAL_PLATFORM_REVIEW",
    "DONE": "ACCEPTED_FOR_DRAFT"
  },
  "entities": {
    "lab_template": {
      "draftImportPath": "/open/labs/imports",
      "statusPathTemplate": "/open/labs/imports/{agentDraftId}/state",
      "requestBodyMapping": {
        "lab.title": {"source": "payload.title", "required": true},
        "lab.minutes": "payload.durationMinutes",
        "lab.reviewState": {"value": "PENDING_MANUAL_PLATFORM_REVIEW"},
        "source.taskId": {"source": "source.sourceTaskId", "required": true}
      }
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    config = load_agent_api_contract_config(config_path)
    endpoint = build_agent_publish_endpoint(AgentEntityType.LAB_TEMPLATE, config)
    contract = describe_agent_publish_contract(AgentEntityType.LAB_TEMPLATE, config)

    assert endpoint == {"method": "POST", "path": "/open/labs/imports"}
    assert contract["draftImportEndpoint"] == endpoint
    assert contract["statusPathTemplate"] == "/open/labs/imports/{agentDraftId}/state"
    assert contract["draftIdResponseKeys"] == ["jobId"]
    assert contract["statusResponseKeys"] == ["reviewState"]
    assert contract["statusMapping"]["DONE"] == "ACCEPTED_FOR_DRAFT"
    assert contract["requestBodyMapping"]["configured"] is True
    assert contract["requestBodyMapping"]["fieldTotal"] == 4
    assert contract["requestBodyMapping"]["requiredTargetFields"] == ["lab.title", "source.taskId"]
    assert contract["configApplied"] is True
    assert infer_agent_draft_id({"body": {"json": {"jobId": "job_1"}}}, contract=contract) == "job_1"
    assert extract_agent_status({"body": {"json": {"reviewState": "DONE"}}}, contract=contract) == "DONE"
    assert suggest_publish_result_status("QUEUED", config) == "PENDING_MANUAL_PLATFORM_REVIEW"
    assert suggest_publish_result_status("DONE", config) == "ACCEPTED_FOR_DRAFT"
    assert suggest_publish_result_status("DONE", contract) == "ACCEPTED_FOR_DRAFT"


def test_platform_api_contract_builds_mapped_request_body():
    request_preview = {
        "apiVersion": "platform-import-dry-run/v1",
        "entityType": "lab_template",
        "idempotencyKey": "dryrun:entity_1",
        "source": {"sourceTaskId": "task_1"},
        "payload": {"title": "Lab 1", "durationMinutes": 45},
    }
    config = {
        "entities": {
            "lab_template": {
                "requestBodyMapping": {
                    "lab.title": {"source": "payload.title", "required": True},
                    "lab.minutes": "payload.durationMinutes",
                    "lab.tags": {"source": "payload.tags", "default": []},
                    "workflow.idempotencyKey": "idempotencyKey",
                    "source.taskId": {"source": "source.sourceTaskId", "required": True},
                    "review.status": {"value": "PENDING_MANUAL_PLATFORM_REVIEW"},
                    "optional.missing": "payload.notHere",
                }
            }
        }
    }

    body, summary = build_agent_request_body(request_preview, AgentEntityType.LAB_TEMPLATE, config)

    assert body == {
        "lab": {"title": "Lab 1", "minutes": 45, "tags": []},
        "workflow": {"idempotencyKey": "dryrun:entity_1"},
        "source": {"taskId": "task_1"},
        "review": {"status": "PENDING_MANUAL_PLATFORM_REVIEW"},
    }
    assert summary["mode"] == "CONFIGURED_FIELD_MAPPING"
    assert summary["applied"] is True
    assert summary["mappedTotal"] == 6
    assert summary["skippedOptionalFields"] == ["optional.missing"]


def test_platform_api_contract_validates_config_for_all_entities_with_warnings():
    config = {
        "unexpected": True,
        "requestBodyMapping": {
            "workflow.idempotencyKey": "idempotencyKey",
        },
        "entities": {
            "lab_template": {
                "draftImportPath": "/open/lab-imports",
                "requestBodyMapping": {
                    "lab.title": {"source": "payload.title", "required": True},
                },
            },
            "grading_rule": {
                "statusResponseKeys": ["reviewState"],
            },
        },
    }
    request_preview = {
        "apiVersion": "platform-import-dry-run/v1",
        "entityType": "lab_template",
        "idempotencyKey": "dryrun:entity_1",
        "payload": {"title": "Lab 1"},
    }

    validation = validate_agent_api_contract_config(
        config,
        request_previews={"lab_template": request_preview},
    )

    assert validation["valid"] is True
    assert validation["summary"]["warningTotal"] == 1
    assert validation["unknownTopLevelKeys"] == ["unexpected"]
    assert validation["checkedEntityTypes"] == ["lab_template", "exam_question", "grading_rule", "ppt_deck"]
    assert validation["entities"]["lab_template"]["requestBodyMappingSampleValidated"] is True
    assert validation["entities"]["lab_template"]["requestBodyMappingResult"]["mappedTotal"] == 2
    assert validation["entities"]["exam_question"]["requestBodySource"] == "requestBody"
    assert validation["entities"]["grading_rule"]["statusResponseKeys"] == ["reviewState"]
    assert validation["safety"]["requestSent"] is False
    assert validation["safety"]["secretsRead"] is False


def test_platform_api_contract_validation_rejects_unknown_entity_override():
    with pytest.raises(AgentApiContractError) as exc_info:
        validate_agent_api_contract_config({"entities": {"unknown_entity": {}}})

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.errors == [
        {"field": "entities.unknown_entity", "reason": "unsupported entity type override"}
    ]


def test_platform_api_contract_rejects_missing_required_mapping_source():
    request_preview = {"payload": {}}
    config = {
        "entities": {
            "lab_template": {
                "requestBodyMapping": {
                    "lab.title": {"source": "payload.title", "required": True},
                }
            }
        }
    }

    with pytest.raises(AgentApiContractError) as exc_info:
        build_agent_request_body(request_preview, AgentEntityType.LAB_TEMPLATE, config)

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.errors == [
        {"field": "requestBodyMapping.lab.title", "reason": "required source missing"}
    ]


def test_platform_api_contract_rejects_invalid_config_shape(tmp_path):
    config_path = tmp_path / "bad-platform-contract.json"
    config_path.write_text('{"draftIdResponseKeys": "jobId"}', encoding="utf-8")
    config = load_agent_api_contract_config(config_path)

    with pytest.raises(AgentApiContractError) as exc_info:
        describe_agent_publish_contract(AgentEntityType.LAB_TEMPLATE, config)

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.errors == [{"field": "draftIdResponseKeys", "reason": "expected non-empty string list"}]
