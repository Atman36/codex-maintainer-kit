from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple
from urllib.parse import urljoin


_MISSING_PROPERTY_RX = re.compile(r"'([^']+)' is a required property")
_ADDITIONAL_PROPERTY_RX = re.compile(r"Additional properties are not allowed \('([^']+)'")
_EXECUTION_STAGE_ALIASES = {
    "analyst": "analysis",
    "architect": "analysis",
}


class SchemaValidationError(ValueError):
    def __init__(
        self,
        *,
        schema_name: str,
        context: str,
        instance_path: str,
        schema_path: str,
        field_name: str,
        detail: str,
    ) -> None:
        field_text = f", field: {field_name}" if field_name else ""
        super().__init__(
            f"{context} failed {schema_name} validation at {instance_path} "
            f"(schema: {schema_path}{field_text}): {detail}"
        )


def validate_stage_payload(payload: Dict[str, Any], expected_stage: str) -> None:
    validation_payload = _normalize_execution_result_stage(payload=payload, expected_stage=expected_stage)
    _validate_instance(
        schema_key="execution_result",
        schema_name="ExecutionResult",
        instance=validation_payload,
        context=f"Stage '{expected_stage}' output",
    )

    for location, pr_spec in _iter_pr_spec_payloads(payload):
        _validate_instance(
            schema_key="prspec",
            schema_name="PRSpec",
            instance=pr_spec,
            context=f"Stage '{expected_stage}' output at {location}",
        )


def _normalize_execution_result_stage(payload: Dict[str, Any], expected_stage: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    normalized = dict(payload)
    stage_value = normalized.get("stage")
    if isinstance(stage_value, str):
        normalized["stage"] = _EXECUTION_STAGE_ALIASES.get(stage_value, stage_value)
    elif expected_stage in _EXECUTION_STAGE_ALIASES:
        normalized["stage"] = _EXECUTION_STAGE_ALIASES[expected_stage]
    return normalized


def _iter_pr_spec_payloads(payload: Dict[str, Any]) -> Iterable[Tuple[str, Any]]:
    if "pr_spec" in payload:
        yield "pr_spec", payload.get("pr_spec")

    top_level_pr_specs = payload.get("pr_specs")
    if isinstance(top_level_pr_specs, list):
        for index, item in enumerate(top_level_pr_specs):
            yield f"pr_specs[{index}]", item

    data = payload.get("data")
    if not isinstance(data, dict):
        return

    data_pr_specs = data.get("pr_specs")
    if isinstance(data_pr_specs, list):
        for index, item in enumerate(data_pr_specs):
            yield f"data.pr_specs[{index}]", item

    selected = data.get("selected")
    if isinstance(selected, list):
        for index, item in enumerate(selected):
            if isinstance(item, dict) and "pr_spec" in item:
                yield f"data.selected[{index}].pr_spec", item.get("pr_spec")


def _validate_instance(schema_key: str, schema_name: str, instance: Any, context: str) -> None:
    validator = _load_validators()[schema_key]
    error = next(iter(sorted(validator.iter_errors(instance), key=_error_sort_key)), None)
    if error is None:
        return

    raise SchemaValidationError(
        schema_name=schema_name,
        context=context,
        instance_path=_json_path(tuple(error.path)),
        schema_path=_schema_path(tuple(error.schema_path)),
        field_name=_field_name(error),
        detail=error.message,
    )


def _error_sort_key(error: Any) -> Tuple[str, str, str]:
    return (_json_path(tuple(error.path)), _schema_path(tuple(error.schema_path)), str(error.message))


def _json_path(parts: Tuple[Any, ...]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def _schema_path(parts: Tuple[Any, ...]) -> str:
    if not parts:
        return "$"
    return "/".join(str(part) for part in parts)


def _field_name(error: Any) -> str:
    if error.validator == "required":
        match = _MISSING_PROPERTY_RX.search(str(error.message))
        if match:
            return match.group(1)

    if error.validator == "additionalProperties":
        match = _ADDITIONAL_PROPERTY_RX.search(str(error.message))
        if match:
            return match.group(1)

    if error.path:
        return str(list(error.path)[-1])
    return ""


def _schema_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas"


def _import_jsonschema():
    try:
        import jsonschema  # type: ignore
        from jsonschema.validators import validator_for  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Runtime schema validation requires the 'jsonschema' package. "
            "Install it with `pip install jsonschema`."
        ) from exc

    return jsonschema, validator_for


@lru_cache(maxsize=1)
def _load_validators() -> Dict[str, Any]:
    jsonschema, validator_for = _import_jsonschema()

    schema_dir = _schema_dir()
    execution_result_path = schema_dir / "execution_result.schema.json"
    prspec_path = schema_dir / "prspec.schema.json"

    execution_result_schema = json.loads(execution_result_path.read_text(encoding="utf-8"))
    prspec_schema = json.loads(prspec_path.read_text(encoding="utf-8"))

    store = {
        execution_result_path.resolve().as_uri(): execution_result_schema,
        prspec_path.resolve().as_uri(): prspec_schema,
    }
    for schema in (execution_result_schema, prspec_schema):
        schema_id = schema.get("$id")
        if isinstance(schema_id, str) and schema_id:
            store[schema_id] = schema

    execution_result_id = execution_result_schema.get("$id")
    if isinstance(execution_result_id, str) and execution_result_id:
        store[urljoin(execution_result_id, "./prspec.schema.json")] = prspec_schema

    format_checker = jsonschema.FormatChecker()
    resolver_cls = getattr(jsonschema, "RefResolver", None)

    execution_result_cls = validator_for(execution_result_schema)
    execution_result_cls.check_schema(execution_result_schema)
    execution_result_kwargs = {"format_checker": format_checker}
    if resolver_cls is not None:
        execution_result_kwargs["resolver"] = resolver_cls(
            base_uri=execution_result_path.resolve().as_uri(),
            referrer=execution_result_schema,
            store=store,
        )

    prspec_cls = validator_for(prspec_schema)
    prspec_cls.check_schema(prspec_schema)
    prspec_kwargs = {"format_checker": format_checker}
    if resolver_cls is not None:
        prspec_kwargs["resolver"] = resolver_cls(
            base_uri=prspec_path.resolve().as_uri(),
            referrer=prspec_schema,
            store=store,
        )

    return {
        "execution_result": execution_result_cls(execution_result_schema, **execution_result_kwargs),
        "prspec": prspec_cls(prspec_schema, **prspec_kwargs),
    }
