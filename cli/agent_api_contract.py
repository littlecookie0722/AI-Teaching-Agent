"""Minimal agent API contract helpers for draft import integration."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .agent_entity import AgentEntityType


PLATFORM_IMPORT_CONTRACT_VERSION = "platform-import-contract/v1"
DEFAULT_STATUS_PATH_TEMPLATE = "{targetEndpointPath}/{agentDraftId}"
DEFAULT_DRAFT_ID_RESPONSE_KEYS = ("draftImportId", "draftId", "importId", "id")
DEFAULT_STATUS_RESPONSE_KEYS = ("agentStatus", "status", "state", "draftStatus")
ALLOWED_CONTRACT_CONFIG_KEYS = {
    "statusPathTemplate",
    "draftIdResponseKeys",
    "statusResponseKeys",
    "statusMapping",
    "requestBodyMapping",
    "entities",
}

_DRAFT_IMPORT_ENDPOINT_PATHS = {
    AgentEntityType.LAB_TEMPLATE.value: "/api/platform/lab-template/draft-imports",
    AgentEntityType.EXAM_QUESTION.value: "/api/platform/exam-question/draft-imports",
    AgentEntityType.GRADING_RULE.value: "/api/platform/grading-rule/draft-imports",
    AgentEntityType.PPT_DECK.value: "/api/platform/ppt-deck/draft-imports",
}

_SUGGESTED_IMPORT_RESULT_STATUS = {
    "PENDING": "PENDING_MANUAL_PLATFORM_REVIEW",
    "PENDING_MANUAL_PLATFORM_REVIEW": "PENDING_MANUAL_PLATFORM_REVIEW",
    "WAITING_REVIEW": "PENDING_MANUAL_PLATFORM_REVIEW",
    "IN_REVIEW": "PENDING_MANUAL_PLATFORM_REVIEW",
    "ACCEPTED": "ACCEPTED_FOR_DRAFT",
    "ACCEPTED_FOR_DRAFT": "ACCEPTED_FOR_DRAFT",
    "DRAFT_ACCEPTED": "ACCEPTED_FOR_DRAFT",
    "READY_FOR_DRAFT": "ACCEPTED_FOR_DRAFT",
    "APPROVED": "ACCEPTED_FOR_DRAFT",
    "REJECTED": "REJECTED_BY_PLATFORM",
    "REJECTED_BY_PLATFORM": "REJECTED_BY_PLATFORM",
    "REJECTED_FOR_DRAFT": "REJECTED_BY_PLATFORM",
    "FAILED": "FAILED",
    "ERROR": "FAILED",
    "IMPORT_FAILED": "FAILED",
}

_MISSING = object()


class AgentApiContractError(ValueError):
    def __init__(self, code: str, message: str, errors: list[dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors


def load_agent_api_contract_config(path: Path | str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    config_path = Path(path)
    if not config_path.exists() or not config_path.is_file():
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置文件不存在",
            [{"field": "contractConfig", "reason": "文件不存在"}],
        )
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置不是合法 JSON",
            [{"field": "contractConfig", "reason": str(exc)}],
        ) from exc
    if not isinstance(payload, dict):
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置必须是 JSON object",
            [{"field": "contractConfig", "reason": "expected object"}],
        )
    return payload


def _contract_entity_overrides(config: dict[str, Any] | None, entity_type: str) -> dict[str, Any]:
    if not config:
        return {}
    entities = config.get("entities")
    if not isinstance(entities, dict):
        return {}
    item = entities.get(entity_type)
    return item if isinstance(item, dict) else {}


def _path_segments(value: str, *, field: str) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段格式错误",
            [{"field": field, "reason": "expected non-empty dot path"}],
        )
    normalized = value.strip()
    if normalized.startswith("$."):
        normalized = normalized[2:]
    elif normalized == "$":
        normalized = ""
    if not normalized:
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段格式错误",
            [{"field": field, "reason": "expected non-empty dot path"}],
        )
    segments = normalized.split(".")
    if any(not segment for segment in segments):
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段格式错误",
            [{"field": field, "reason": "invalid dot path"}],
        )
    return segments


def _read_path(payload: dict[str, Any], path: str, *, field: str) -> Any:
    current: Any = payload
    for segment in _path_segments(path, field=field):
        if not isinstance(current, dict) or segment not in current:
            return _MISSING
        current = current[segment]
    return deepcopy(current)


def _write_path(target: dict[str, Any], path: str, value: Any, *, field: str) -> None:
    segments = _path_segments(path, field=field)
    current = target
    for segment in segments[:-1]:
        existing = current.get(segment)
        if existing is None:
            current[segment] = {}
            existing = current[segment]
        if not isinstance(existing, dict):
            raise AgentApiContractError(
                "VALIDATION_ERROR",
                "平台 API 契约配置字段格式错误",
                [{"field": field, "reason": f"target path conflicts at {segment}"}],
            )
        current = existing
    current[segments[-1]] = deepcopy(value)


def _request_body_mapping(config: dict[str, Any] | None, entity_type: str) -> dict[str, Any] | None:
    if not config:
        return None
    mapping: dict[str, Any] = {}
    global_mapping = config.get("requestBodyMapping")
    if global_mapping is not None:
        if not isinstance(global_mapping, dict):
            raise AgentApiContractError(
                "VALIDATION_ERROR",
                "平台 API 契约配置字段格式错误",
                [{"field": "requestBodyMapping", "reason": "expected object"}],
            )
        mapping.update(global_mapping)
    overrides = _contract_entity_overrides(config, entity_type)
    entity_mapping = overrides.get("requestBodyMapping")
    if entity_mapping is not None:
        if not isinstance(entity_mapping, dict):
            raise AgentApiContractError(
                "VALIDATION_ERROR",
                "平台 API 契约配置字段格式错误",
                [{"field": f"entities.{entity_type}.requestBodyMapping", "reason": "expected object"}],
            )
        mapping.update(entity_mapping)
    return mapping or None


def _normalize_mapping_rule(rule: Any, *, target_path: str, field: str) -> dict[str, Any]:
    if isinstance(rule, str):
        return {"source": rule, "required": False}
    if not isinstance(rule, dict):
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段格式错误",
            [{"field": field, "reason": "expected source path string or object rule"}],
        )
    has_source = "source" in rule
    has_value = "value" in rule
    if has_source and has_value:
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段格式错误",
            [{"field": field, "reason": "source and value cannot both be set"}],
        )
    if not has_source and not has_value:
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段格式错误",
            [{"field": field, "reason": "source or value is required"}],
        )
    required = rule.get("required", False)
    if not isinstance(required, bool):
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段格式错误",
            [{"field": f"{field}.required", "reason": "expected boolean"}],
        )
    normalized: dict[str, Any] = {"required": required}
    if has_source:
        _path_segments(rule["source"], field=f"{field}.source")
        normalized["source"] = rule["source"]
    if has_value:
        normalized["value"] = deepcopy(rule["value"])
    if "default" in rule:
        normalized["default"] = deepcopy(rule["default"])
    _path_segments(target_path, field=field)
    return normalized


def _describe_request_body_mapping(config: dict[str, Any] | None, entity_type: str) -> dict[str, Any]:
    mapping = _request_body_mapping(config, entity_type)
    if not mapping:
        return {
            "mode": "DEFAULT_INTERNAL_DTO",
            "configured": False,
            "fieldTotal": 0,
            "requiredTargetFields": [],
        }
    required_targets: list[str] = []
    for target_path, rule in mapping.items():
        normalized = _normalize_mapping_rule(
            rule,
            target_path=target_path,
            field=f"requestBodyMapping.{target_path}",
        )
        if normalized["required"]:
            required_targets.append(target_path)
    return {
        "mode": "CONFIGURED_FIELD_MAPPING",
        "configured": True,
        "fieldTotal": len(mapping),
        "requiredTargetFields": required_targets,
    }


def _string_list(value: Any, *, field: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段格式错误",
            [{"field": field, "reason": "expected non-empty string list"}],
        )
    return [item.strip() for item in value]


def _status_mapping(config: dict[str, Any] | None) -> dict[str, str]:
    mapping = dict(_SUGGESTED_IMPORT_RESULT_STATUS)
    value = config.get("statusMapping") if isinstance(config, dict) else None
    if value is None:
        return mapping
    if not isinstance(value, dict):
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段格式错误",
            [{"field": "statusMapping", "reason": "expected object"}],
        )
    allowed = {"PENDING_MANUAL_PLATFORM_REVIEW", "ACCEPTED_FOR_DRAFT", "REJECTED_BY_PLATFORM", "FAILED"}
    for raw_status, result_status in value.items():
        if not isinstance(raw_status, str) or not raw_status.strip():
            raise AgentApiContractError(
                "VALIDATION_ERROR",
                "平台 API 契约配置字段格式错误",
                [{"field": "statusMapping", "reason": "keys must be non-empty strings"}],
            )
        if result_status not in allowed:
            raise AgentApiContractError(
                "VALIDATION_ERROR",
                "平台 API 契约配置字段格式错误",
                [{"field": f"statusMapping.{raw_status}", "reason": "不在允许枚举中"}],
            )
        mapping[raw_status.strip().upper()] = result_status
    return mapping


def normalize_agent_entity_type(entity_type: AgentEntityType | str) -> str:
    value = entity_type.value if isinstance(entity_type, AgentEntityType) else str(entity_type or "")
    normalized = value.strip()
    if normalized not in _DRAFT_IMPORT_ENDPOINT_PATHS:
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "不支持的平台实体类型",
            [{"field": "entityType", "reason": normalized or "缺少参数"}],
        )
    return normalized


def _normalize_entity_type_list(entity_types: list[AgentEntityType | str] | tuple[AgentEntityType | str, ...] | AgentEntityType | str | None) -> list[str]:
    if entity_types is None:
        return list(_DRAFT_IMPORT_ENDPOINT_PATHS)
    values: list[AgentEntityType | str]
    if isinstance(entity_types, (str, AgentEntityType)):
        values = [entity_types]
    else:
        values = list(entity_types)
    normalized: list[str] = []
    for value in values:
        item = normalize_agent_entity_type(value)
        if item not in normalized:
            normalized.append(item)
    return normalized


def _validate_contract_config_shape(config: dict[str, Any] | None) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    if not config:
        return errors, warnings
    for key in sorted(config):
        if key not in ALLOWED_CONTRACT_CONFIG_KEYS:
            warnings.append({"field": key, "reason": "unknown top-level key ignored"})
    entities = config.get("entities")
    if entities is None:
        return errors, warnings
    if not isinstance(entities, dict):
        errors.append({"field": "entities", "reason": "expected object"})
        return errors, warnings
    for entity_type, overrides in entities.items():
        if entity_type not in _DRAFT_IMPORT_ENDPOINT_PATHS:
            errors.append({"field": f"entities.{entity_type}", "reason": "unsupported entity type override"})
            continue
        if not isinstance(overrides, dict):
            errors.append({"field": f"entities.{entity_type}", "reason": "expected object"})
    return errors, warnings


def validate_agent_api_contract_config(
    config: dict[str, Any] | None,
    *,
    entity_types: list[AgentEntityType | str] | tuple[AgentEntityType | str, ...] | AgentEntityType | str | None = None,
    request_previews: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate local platform API contract config without network or secrets."""

    errors, warnings = _validate_contract_config_shape(config)
    if errors:
        raise AgentApiContractError("VALIDATION_ERROR", "平台 API 契约配置字段格式错误", errors)

    normalized_entity_types = _normalize_entity_type_list(entity_types)
    request_previews = request_previews or {}
    entity_reports: dict[str, Any] = {}
    request_body_mapping_total = 0
    default_internal_dto_total = 0
    sample_validated_total = 0
    for entity_type in normalized_entity_types:
        try:
            contract = describe_agent_publish_contract(entity_type, config)
        except AgentApiContractError as exc:
            errors.extend(exc.errors)
            continue
        mapping = contract["requestBodyMapping"]
        mapping_configured = bool(mapping.get("configured"))
        if mapping_configured:
            request_body_mapping_total += 1
        else:
            default_internal_dto_total += 1
        preview = request_previews.get(entity_type)
        mapping_result: dict[str, Any] | None = None
        if isinstance(preview, dict):
            sample_validated_total += 1
            try:
                _body, mapping_result = build_agent_request_body(preview, entity_type, config)
            except AgentApiContractError as exc:
                errors.extend(exc.errors)
                continue
        entity_reports[entity_type] = {
            "entityType": entity_type,
            "draftImportEndpoint": contract["draftImportEndpoint"],
            "statusPathTemplate": contract["statusPathTemplate"],
            "draftIdResponseKeys": contract["draftIdResponseKeys"],
            "statusResponseKeys": contract["statusResponseKeys"],
            "statusMappingTotal": len(contract["statusMapping"]),
            "suggestedImportResultStatuses": contract["suggestedImportResultStatuses"],
            "requestBodyMapping": mapping,
            "requestBodySource": "requestBody" if mapping_configured else "requestPreview",
            "requestBodyMappingSampleValidated": isinstance(preview, dict),
            "requestBodyMappingResult": mapping_result,
            "requestBodySourcePathCoverage": "CHECKED_WITH_DRY_RUN_SAMPLE"
            if isinstance(preview, dict)
            else "STRUCTURE_ONLY",
        }

    if errors:
        raise AgentApiContractError("VALIDATION_ERROR", "平台 API 契约配置校验失败", errors)

    configured_overrides = []
    entities = config.get("entities") if isinstance(config, dict) else None
    if isinstance(entities, dict):
        configured_overrides = sorted(entities)
    unknown_top_level_keys = [item["field"] for item in warnings if item["reason"] == "unknown top-level key ignored"]
    return {
        "component": "AgentApiContractValidation",
        "contractVersion": PLATFORM_IMPORT_CONTRACT_VERSION,
        "valid": True,
        "configApplied": bool(config),
        "checkedEntityTypes": normalized_entity_types,
        "entityTotal": len(normalized_entity_types),
        "configuredEntityOverrideTypes": configured_overrides,
        "configuredEntityOverrideTotal": len(configured_overrides),
        "unknownTopLevelKeys": unknown_top_level_keys,
        "entities": entity_reports,
        "summary": {
            "requestBodyMappingConfiguredEntityTotal": request_body_mapping_total,
            "defaultInternalDtoEntityTotal": default_internal_dto_total,
            "sampleValidatedEntityTotal": sample_validated_total,
            "warningTotal": len(warnings),
            "errorTotal": 0,
        },
        "warnings": warnings,
        "errors": [],
        "safety": {
            "localConfigOnly": True,
            "requestSent": False,
            "networkAccess": False,
            "secretsRead": False,
            "secretValueReturned": False,
            "databaseWritten": False,
            "realPlatformImport": False,
            "realPublish": False,
        },
    }


def build_agent_publish_endpoint(
    entity_type: AgentEntityType | str,
    config: dict[str, Any] | None = None,
) -> dict[str, str]:
    normalized = normalize_agent_entity_type(entity_type)
    overrides = _contract_entity_overrides(config, normalized)
    endpoint_path = overrides.get("draftImportPath")
    if endpoint_path is not None and (not isinstance(endpoint_path, str) or not endpoint_path.strip()):
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段格式错误",
            [{"field": f"entities.{normalized}.draftImportPath", "reason": "expected non-empty string"}],
        )
    return {
        "method": "POST",
        "path": endpoint_path.strip() if isinstance(endpoint_path, str) else _DRAFT_IMPORT_ENDPOINT_PATHS[normalized],
    }


def describe_agent_publish_contract(
    entity_type: AgentEntityType | str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normalize_agent_entity_type(entity_type)
    overrides = _contract_entity_overrides(config, normalized)
    status_path_template = overrides.get("statusPathTemplate") or (config or {}).get("statusPathTemplate")
    if status_path_template is not None and (
        not isinstance(status_path_template, str)
        or ("{agentDraftId}" not in status_path_template and "{draftImportId}" not in status_path_template)
    ):
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段格式错误",
            [{"field": "statusPathTemplate", "reason": "must contain {agentDraftId} or {draftImportId}"}],
        )
    draft_id_keys = _string_list(
        overrides.get("draftIdResponseKeys") or (config or {}).get("draftIdResponseKeys"),
        field="draftIdResponseKeys",
    ) or list(DEFAULT_DRAFT_ID_RESPONSE_KEYS)
    status_keys = _string_list(
        overrides.get("statusResponseKeys") or (config or {}).get("statusResponseKeys"),
        field="statusResponseKeys",
    ) or list(DEFAULT_STATUS_RESPONSE_KEYS)
    status_mapping = _status_mapping(config)
    return {
        "contractVersion": PLATFORM_IMPORT_CONTRACT_VERSION,
        "entityType": normalized,
        "draftImportEndpoint": build_agent_publish_endpoint(normalized, config),
        "statusPathTemplate": status_path_template or DEFAULT_STATUS_PATH_TEMPLATE,
        "draftIdResponseKeys": draft_id_keys,
        "statusResponseKeys": status_keys,
        "statusMapping": status_mapping,
        "requestBodyMapping": _describe_request_body_mapping(config, normalized),
        "suggestedImportResultStatuses": sorted(set(status_mapping.values())),
        "configApplied": bool(config),
    }


def build_agent_request_body(
    request_preview: dict[str, Any],
    entity_type: AgentEntityType | str,
    config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the platform-facing request body from the internal dry-run DTO."""

    normalized = normalize_agent_entity_type(entity_type)
    mapping = _request_body_mapping(config, normalized)
    if not mapping:
        return deepcopy(request_preview), {
            "component": "PlatformRequestBodyMapping",
            "mode": "DEFAULT_INTERNAL_DTO",
            "applied": False,
            "entityType": normalized,
            "fieldTotal": 0,
            "mappedTotal": 0,
            "skippedOptionalTotal": 0,
            "requiredMissingTotal": 0,
            "targetFields": [],
            "skippedOptionalFields": [],
            "requiredMissingFields": [],
        }

    body: dict[str, Any] = {}
    target_fields: list[str] = []
    skipped_optional: list[str] = []
    missing_required: list[str] = []
    for target_path, rule in mapping.items():
        field = f"requestBodyMapping.{target_path}"
        normalized_rule = _normalize_mapping_rule(rule, target_path=target_path, field=field)
        if "value" in normalized_rule:
            value = normalized_rule["value"]
        else:
            value = _read_path(request_preview, normalized_rule["source"], field=f"{field}.source")
            if value is _MISSING and "default" in normalized_rule:
                value = normalized_rule["default"]
            if value is _MISSING and normalized_rule["required"]:
                missing_required.append(target_path)
                continue
            if value is _MISSING:
                skipped_optional.append(target_path)
                continue
        _write_path(body, target_path, value, field=field)
        target_fields.append(target_path)

    if missing_required:
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台 API 契约配置字段映射缺少必填源字段",
            [
                {
                    "field": f"requestBodyMapping.{target_path}",
                    "reason": "required source missing",
                }
                for target_path in missing_required
            ],
        )
    return body, {
        "component": "PlatformRequestBodyMapping",
        "mode": "CONFIGURED_FIELD_MAPPING",
        "applied": True,
        "entityType": normalized,
        "fieldTotal": len(mapping),
        "mappedTotal": len(target_fields),
        "skippedOptionalTotal": len(skipped_optional),
        "requiredMissingTotal": 0,
        "targetFields": target_fields,
        "skippedOptionalFields": skipped_optional,
        "requiredMissingFields": [],
    }


def extract_response_json(response: dict[str, Any]) -> Any:
    body = response.get("body") if isinstance(response.get("body"), dict) else {}
    return body.get("json")


def infer_agent_draft_id(
    response: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
) -> str | None:
    parsed = extract_response_json(response)
    if not isinstance(parsed, dict):
        return None
    keys = contract.get("draftIdResponseKeys") if isinstance(contract, dict) else None
    for key in keys if isinstance(keys, list) else DEFAULT_DRAFT_ID_RESPONSE_KEYS:
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def extract_agent_status(
    response: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
) -> str | None:
    parsed = extract_response_json(response)
    if not isinstance(parsed, dict):
        return None
    keys = contract.get("statusResponseKeys") if isinstance(contract, dict) else None
    for key in keys if isinstance(keys, list) else DEFAULT_STATUS_RESPONSE_KEYS:
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def suggest_publish_result_status(
    platform_status: str | None,
    config: dict[str, Any] | None = None,
) -> str | None:
    if not platform_status:
        return None
    return _status_mapping(config).get(platform_status.strip().upper())


def build_status_path(
    target_endpoint_path: str | None,
    platform_draft_id: str,
    status_path_template: str | None = None,
) -> str:
    normalized_endpoint = str(target_endpoint_path or "").strip()
    if not normalized_endpoint:
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台导入发送报告缺少 targetEndpoint.path",
            [{"field": "sendResult.targetEndpoint.path", "reason": "缺少字段"}],
        )
    normalized_draft_id = str(platform_draft_id or "").strip()
    if not normalized_draft_id:
        raise AgentApiContractError(
            "VALIDATION_ERROR",
            "平台导入状态查询缺少平台 draft id",
            [{"field": "agentDraftId", "reason": "缺少参数"}],
        )
    template = status_path_template or DEFAULT_STATUS_PATH_TEMPLATE
    encoded_draft_id = quote(normalized_draft_id, safe="")
    return (
        template.replace("{targetEndpointPath}", normalized_endpoint.rstrip("/"))
        .replace("{agentDraftId}", encoded_draft_id)
        .replace("{draftImportId}", encoded_draft_id)
    )
