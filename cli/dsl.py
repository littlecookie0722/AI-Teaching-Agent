"""Draft 2020-12 JSON Schema validation for project DSL documents."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


class DslValidationError(ValueError):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__("DSL schema validation failed")
        self.errors = errors


@dataclass(frozen=True)
class _NormalizedError:
    path: tuple[Any, ...]
    reason: str


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_schema(kind: str, root: Path) -> dict[str, Any]:
    schema_path = root / "templates" / kind / f"{kind}.schema.json"
    with schema_path.open("r", encoding="utf-8") as file:
        schema = json.load(file)
    _build_validator(schema)
    return schema


def validate_dsl(document: Any, schema: dict[str, Any]) -> None:
    validator = _build_validator(schema)
    raw_errors = sorted(validator.iter_errors(document), key=_validation_error_sort_key)
    errors = _normalize_validation_errors(raw_errors)
    if errors:
        raise DslValidationError(errors)


def _build_validator(schema: dict[str, Any]) -> Draft202012Validator:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        path = tuple(exc.absolute_path)
        reason = f"invalid Draft 2020-12 schema: {_single_line(exc.message)}"
        raise DslValidationError([{"field": _format_path(path), "reason": reason}]) from exc
    return Draft202012Validator(schema)


def _normalize_validation_errors(raw_errors: list[ValidationError]) -> list[dict[str, str]]:
    normalized: list[_NormalizedError] = []
    handled_groups: set[tuple[str, tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]] = set()

    for error in raw_errors:
        path = tuple(error.absolute_path)
        keyword = str(error.validator or "")

        if keyword == "required" and isinstance(error.instance, dict):
            group = _error_group_key(error)
            if group in handled_groups:
                continue
            handled_groups.add(group)
            required = error.validator_value if isinstance(error.validator_value, list) else []
            missing = sorted((name for name in required if name not in error.instance), key=str)
            normalized.extend(
                _NormalizedError(path + (name,), "required field missing")
                for name in missing
            )
            continue

        if keyword == "additionalProperties" and isinstance(error.instance, dict):
            extras = _find_additional_properties(error.instance, error.schema)
            if extras:
                normalized.extend(
                    _NormalizedError(path + (name,), "additional field is not allowed")
                    for name in extras
                )
                continue

        normalized.append(_NormalizedError(path, _validation_reason(error)))

    normalized.sort(key=lambda item: (_path_sort_key(item.path), item.reason))
    return [
        {"field": _format_path(item.path), "reason": item.reason}
        for item in normalized
    ]


def _validation_reason(error: ValidationError) -> str:
    keyword = error.validator
    limit = error.validator_value

    if keyword == "const":
        return f"expected {limit!r}"
    if keyword == "enum":
        return f"expected one of {limit}"
    if keyword == "type":
        if isinstance(limit, list):
            return f"expected one of types {limit}"
        return f"expected {limit}"
    if keyword == "minItems":
        return f"expected at least {limit} item(s)"
    if keyword == "maxItems":
        return f"expected at most {limit} item(s)"
    if keyword == "minimum":
        return f"expected >= {limit}"
    if keyword == "maximum":
        return f"expected <= {limit}"
    if keyword == "exclusiveMinimum":
        return f"expected > {limit}"
    if keyword == "exclusiveMaximum":
        return f"expected < {limit}"
    if keyword == "minLength":
        return f"expected length >= {limit}"
    if keyword == "maxLength":
        return f"expected length <= {limit}"
    if keyword == "pattern":
        return f"expected string matching pattern {limit!r}"
    if keyword == "oneOf":
        return "expected exactly one schema in oneOf to match"
    return _single_line(error.message)


def _find_additional_properties(instance: dict[Any, Any], schema: Any) -> list[Any]:
    if not isinstance(schema, dict):
        return []
    properties = schema.get("properties")
    known = properties if isinstance(properties, dict) else {}
    pattern_properties = schema.get("patternProperties")
    patterns = list(pattern_properties) if isinstance(pattern_properties, dict) else []

    extras: list[Any] = []
    for name in instance:
        if name in known:
            continue
        if isinstance(name, str) and any(re.search(pattern, name) for pattern in patterns):
            continue
        extras.append(name)
    return sorted(extras, key=lambda item: (type(item).__name__, str(item)))


def _validation_error_sort_key(error: ValidationError) -> tuple[Any, ...]:
    return (
        _path_sort_key(error.absolute_path),
        _path_sort_key(error.absolute_schema_path),
        str(error.validator or ""),
        _single_line(error.message),
    )


def _error_group_key(
    error: ValidationError,
) -> tuple[str, tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    return (
        str(error.validator or ""),
        _path_identity(error.absolute_path),
        _path_identity(error.absolute_schema_path),
    )


def _path_identity(path: Iterable[Any]) -> tuple[tuple[str, str], ...]:
    return tuple((type(part).__name__, repr(part)) for part in path)


def _path_sort_key(path: Iterable[Any]) -> tuple[tuple[int, Any], ...]:
    return tuple(
        (0, part) if isinstance(part, int) and not isinstance(part, bool) else (1, str(part))
        for part in path
    )


def _format_path(path: Iterable[Any]) -> str:
    field = "$"
    for part in path:
        if isinstance(part, int) and not isinstance(part, bool):
            field += f"[{part}]"
        else:
            field += f".{part}"
    return field


def _single_line(message: str) -> str:
    return " ".join(message.split())
