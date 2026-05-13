from __future__ import annotations

import difflib
import json
import re
import xml.etree.ElementTree as ET
from typing import Any

from .security import sanitize_obj, sanitize_text


EVALUATION_VERSION = "quality_eval.v1"
CONTRADICTION_MARKERS = ("correction:", "instead of", "supersedes", "not ", "changed to", "replace ")


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _line_repetition_ratio(text: str) -> float:
    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    return max(0.0, 1.0 - (len(set(lines)) / len(lines)))


def _check(passed: bool | None, value: Any = None, applicable: bool = True, detail: str | None = None) -> dict[str, Any]:
    return {"passed": passed, "value": value, "applicable": applicable, "detail": detail}


def _try_parse_structured(text: str, fmt: str) -> tuple[bool, Any, str | None]:
    fmt = fmt.lower()
    try:
        if fmt == "json":
            return True, json.loads(text), None
        if fmt == "xml":
            return True, ET.fromstring(text), None
        if fmt == "yaml":
            payload: dict[str, Any] = {}
            for line in text.splitlines():
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if ":" not in line:
                    return False, None, "YAML fallback only supports simple key/value mappings"
                key, value = line.split(":", 1)
                payload[key.strip()] = value.strip()
            return True, payload, None
    except Exception as exc:  # noqa: BLE001 - returned as eval detail
        return False, None, sanitize_text(str(exc))
    return False, None, f"Unsupported structured format: {fmt}"


def _get_key(payload: Any, key: str) -> Any:
    if isinstance(payload, dict):
        return payload.get(key)
    if isinstance(payload, ET.Element):
        child = payload.find(key)
        return child.text if child is not None else None
    return None


def _type_matches(value: Any, expected_type: str) -> bool:
    type_map = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    expected = type_map.get(expected_type)
    if expected is None:
        return True
    if expected_type == "number" and isinstance(value, bool):
        return False
    return isinstance(value, expected)


def _schema_valid(payload: Any, schema: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return False, ["schema validation currently requires object output"]
    for key in schema.get("required", []):
        if key not in payload:
            errors.append(f"missing required key: {key}")
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        for key, descriptor in properties.items():
            if key not in payload or not isinstance(descriptor, dict) or "type" not in descriptor:
                continue
            if not _type_matches(payload[key], str(descriptor["type"])):
                errors.append(f"key {key} expected {descriptor['type']}")
    return not errors, errors


def _score(checks: dict[str, dict[str, Any]]) -> float | None:
    applicable = [check for check in checks.values() if check.get("applicable") and check.get("passed") is not None]
    if not applicable:
        return None
    passed = sum(1 for check in applicable if check.get("passed") is True)
    return passed / len(applicable)


def evaluate_quality(
    output: str,
    evaluator_config: dict[str, Any] | None = None,
    compression: dict[str, Any] | None = None,
    workflow_trace: list[dict[str, Any]] | None = None,
    workflow_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = dict(evaluator_config or {})
    output = str(output or "")
    checks: dict[str, dict[str, Any]] = {}
    modes = ["general_text"]

    checks["nonempty_output"] = _check(bool(output.strip()), bool(output.strip()))
    checks["output_length"] = _check(len(output.strip()) > 0, {"chars": len(output), "words": len(output.split())})
    repetition_ratio = _line_repetition_ratio(output)
    max_repetition = float(config.get("max_repetition_ratio", 0.4))
    checks["repetition_ratio"] = _check(repetition_ratio <= max_repetition, repetition_ratio)
    contradiction_count = sum(1 for marker in CONTRADICTION_MARKERS if marker in output.lower())
    checks["contradiction_flag_count"] = _check(contradiction_count == 0, contradiction_count)

    format_requirement = str(config.get("format_requirement") or config.get("format") or "").lower()
    parsed: Any = None
    if format_requirement in {"json", "yaml", "xml"}:
        ok, parsed, error = _try_parse_structured(output, format_requirement)
        checks["format_compliance"] = _check(ok, format_requirement, detail=error)
    else:
        checks["format_compliance"] = _check(None, "not_requested", applicable=False)

    expected_terms = [str(term) for term in config.get("expected_terms", []) if str(term)]
    if expected_terms:
        lowered = output.lower()
        matched = [term for term in expected_terms if term.lower() in lowered]
        coverage = len(matched) / max(1, len(expected_terms))
        checks["keyword_coverage"] = _check(coverage >= float(config.get("keyword_threshold", 1.0)), coverage)
    else:
        checks["keyword_coverage"] = _check(None, "not_configured", applicable=False)

    expected_answer = config.get("expected_answer")
    if expected_answer is not None:
        expected = str(expected_answer)
        checks["exact_match"] = _check(output.strip() == expected.strip(), output.strip() == expected.strip())
        normalized_match = _normalize(output) == _normalize(expected)
        checks["normalized_match"] = _check(normalized_match, normalized_match)
        fuzzy = difflib.SequenceMatcher(None, _normalize(output), _normalize(expected)).ratio()
        checks["fuzzy_match"] = _check(fuzzy >= float(config.get("fuzzy_threshold", 0.92)), fuzzy)
    else:
        checks["exact_match"] = _check(None, "not_configured", applicable=False)
        checks["normalized_match"] = _check(None, "not_configured", applicable=False)
        checks["fuzzy_match"] = _check(None, "not_configured", applicable=False)

    checks["unsafe_or_invalid_output"] = _check(True, False, detail="placeholder hook; no unsafe output detector configured")

    required_keys = [str(key) for key in config.get("expected_keys", []) or config.get("required_keys", []) if str(key)]
    schema = config.get("schema")
    if format_requirement in {"json", "yaml", "xml"} or required_keys or schema:
        modes.append("structured_output")
        if parsed is None and format_requirement in {"json", "yaml", "xml"}:
            ok, parsed, _error = _try_parse_structured(output, format_requirement)
        parse_valid = parsed is not None
        checks["parse_validity"] = _check(parse_valid, parse_valid)
        if schema and isinstance(schema, dict) and parse_valid:
            valid, errors = _schema_valid(parsed, schema)
            checks["schema_validity"] = _check(valid, errors)
        elif schema:
            checks["schema_validity"] = _check(False, ["parse failed before schema validation"])
        else:
            checks["schema_validity"] = _check(None, "not_configured", applicable=False)
        if required_keys and parse_valid:
            present = [key for key in required_keys if _get_key(parsed, key) not in (None, "")]
            checks["required_key_coverage"] = _check(len(present) == len(required_keys), len(present) / max(1, len(required_keys)))
        else:
            checks["required_key_coverage"] = _check(None, "not_configured", applicable=False)
        if parse_valid and isinstance(parsed, dict):
            values = list(parsed.values())
            complete = [value for value in values if value not in (None, "", [], {})]
            checks["field_completeness"] = _check(True, len(complete) / max(1, len(values)))
        else:
            checks["field_completeness"] = _check(None, "not_applicable", applicable=False)

    if compression:
        modes.append("compression_aware")
        raw = str(compression.get("raw_text") or "")
        canonical = str(compression.get("canonical_text") or "")
        raw_lines = [line.strip().lower() for line in raw.splitlines() if line.strip()]
        unique_lines = set(raw_lines)
        duplicate_reduction = 0.0 if not raw_lines else 1.0 - (len(unique_lines) / len(raw_lines))
        steps = [str(step) for step in compression.get("steps", [])]
        checks["compression_ratio"] = _check(compression.get("compression_ratio") is not None, compression.get("compression_ratio"))
        checks["duplicate_line_reduction"] = _check(True, duplicate_reduction)
        checks["canonicalization_applied"] = _check("canonicalize" in steps or "canonicalization" in steps, "canonicalize" in steps)
        checks["contradiction_candidates_found"] = _check(True, len(compression.get("contradiction_candidates", []) or []))
        checks["raw_vs_canonical_diff_size"] = _check(True, abs(len(raw) - len(canonical)))

    if workflow_trace is not None:
        modes.append("workflow")
        trace = workflow_trace or []
        success_count = sum(1 for item in trace if item.get("status") in {"ok", "warning"})
        failure_count = sum(1 for item in trace if item.get("status") == "error")
        final_output = ""
        if isinstance(workflow_outputs, dict):
            final_output = str(workflow_outputs.get("final") or "")
        outbound_receipts = [item.get("receipt") for item in trace if isinstance(item.get("receipt"), dict)]
        outbound_failures = [
            receipt for receipt in outbound_receipts if str(receipt.get("status", "")).lower() in {"error", "failed", "failure"}
        ]
        checks["node_success_count"] = _check(failure_count == 0, success_count)
        checks["node_failure_count"] = _check(failure_count == 0, failure_count)
        checks["final_output_available"] = _check(bool(final_output.strip() or output.strip()), bool(final_output.strip() or output.strip()))
        checks["outbound_delivery"] = _check(len(outbound_failures) == 0, {"receipts": len(outbound_receipts), "failures": len(outbound_failures)})
        checks["pipeline_completeness"] = _check(bool(trace) and failure_count == 0, {"nodes": len(trace), "failures": failure_count})

    summary_score = _score(checks)
    return sanitize_obj(
        {
            "version": EVALUATION_VERSION,
            "modes": sorted(set(modes)),
            "summary_score": summary_score,
            "checks": checks,
            "booleans": {key: value["passed"] for key, value in checks.items() if value.get("applicable") and isinstance(value.get("passed"), bool)},
            "numeric_values": {
                key: value["value"]
                for key, value in checks.items()
                if isinstance(value.get("value"), (int, float)) and not isinstance(value.get("value"), bool)
            },
            "reference_provided": bool(expected_terms or expected_answer is not None or required_keys or schema),
            "notes": "Structural/process checks only when no reference is configured.",
        }
    )
