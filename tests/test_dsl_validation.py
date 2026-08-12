from pathlib import Path

import pytest

from cli.dsl import DslValidationError, load_schema, validate_dsl


DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def test_standard_draft_2020_12_keywords_are_enforced_in_stable_path_order():
    schema = {
        "$schema": DRAFT_2020_12,
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "score", "code", "choice"],
        "properties": {
            "name": {"type": "string", "minLength": 3},
            "score": {"type": "integer", "maximum": 10},
            "code": {"type": "string", "pattern": "^[A-Z]{3}$"},
            "choice": {"oneOf": [{"type": "integer"}, {"type": "number"}]},
        },
    }
    document = {"score": 11, "choice": 1, "name": "x", "code": "abc"}

    with pytest.raises(DslValidationError) as first:
        validate_dsl(document, schema)
    with pytest.raises(DslValidationError) as second:
        validate_dsl(document, schema)

    assert first.value.errors == second.value.errors
    assert first.value.errors == [
        {"field": "$.choice", "reason": "expected exactly one schema in oneOf to match"},
        {"field": "$.code", "reason": "expected string matching pattern '^[A-Z]{3}$'"},
        {"field": "$.name", "reason": "expected length >= 3"},
        {"field": "$.score", "reason": "expected <= 10"},
    ]


def test_required_and_additional_property_errors_keep_existing_dollar_paths():
    schema = {
        "$schema": DRAFT_2020_12,
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name"],
                    "properties": {"name": {"type": "string"}},
                },
            }
        },
    }

    with pytest.raises(DslValidationError) as exc_info:
        validate_dsl({"items": [{"extra": True}]}, schema)

    assert exc_info.value.errors == [
        {"field": "$.items[0].extra", "reason": "additional field is not allowed"},
        {"field": "$.items[0].name", "reason": "required field missing"},
    ]


def test_load_schema_rejects_invalid_schema_before_document_validation(tmp_path: Path):
    schema_dir = tmp_path / "templates" / "invalid"
    schema_dir.mkdir(parents=True)
    (schema_dir / "invalid.schema.json").write_text(
        '{"$schema":"https://json-schema.org/draft/2020-12/schema",'
        '"type":"object","properties":{"score":{"type":"integer","maximum":"ten"}}}',
        encoding="utf-8",
    )

    with pytest.raises(DslValidationError) as exc_info:
        load_schema("invalid", tmp_path)

    assert exc_info.value.errors[0]["field"] == "$.properties.score.maximum"
    assert exc_info.value.errors[0]["reason"].startswith("invalid Draft 2020-12 schema:")


def test_boolean_is_not_accepted_as_json_schema_integer():
    schema = {
        "$schema": DRAFT_2020_12,
        "type": "object",
        "properties": {"count": {"type": "integer"}},
    }

    with pytest.raises(DslValidationError) as exc_info:
        validate_dsl({"count": True}, schema)

    assert exc_info.value.errors == [{"field": "$.count", "reason": "expected integer"}]
