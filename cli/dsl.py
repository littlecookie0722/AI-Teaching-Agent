"""Small JSON Schema subset validator for Phase 1 DSL examples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


class DslValidationError(ValueError):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__("DSL schema validation failed")
        self.errors = errors


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_schema(kind: str, root: Path) -> dict[str, Any]:
    schema_path = root / "templates" / kind / f"{kind}.schema.json"
    with schema_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_dsl(document: Any, schema: dict[str, Any]) -> None:
    errors: list[dict[str, str]] = []
    _validate(document, schema, "$", errors)
    if errors:
        raise DslValidationError(errors)


def _validate(value: Any, schema: dict[str, Any], path: str, errors: list[dict[str, str]]) -> None:
    if "const" in schema and value != schema["const"]:
        errors.append({"field": path, "reason": f"expected {schema['const']!r}"})
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append({"field": path, "reason": f"expected one of {schema['enum']}"})
        return

    expected_type = schema.get("type")
    if expected_type and not _matches_type(value, expected_type):
        errors.append({"field": path, "reason": f"expected {expected_type}"})
        return

    if expected_type == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(value, dict):
            return
        for key in required:
            if key not in value:
                errors.append({"field": f"{path}.{key}", "reason": "required field missing"})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append({"field": f"{path}.{key}", "reason": "additional field is not allowed"})
        for key, property_schema in properties.items():
            if key in value:
                _validate(value[key], property_schema, f"{path}.{key}", errors)

    if expected_type == "array":
        if not isinstance(value, list):
            return
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            errors.append({"field": path, "reason": f"expected at least {min_items} item(s)"})
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _validate(item, item_schema, f"{path}[{index}]", errors)

    if expected_type == "integer" and isinstance(value, int):
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            errors.append({"field": path, "reason": f"expected >= {minimum}"})


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return True
