"""Validate serializable domain inputs without interpreting them as authority."""

import json

from ..shared.errors import HandrailError


_OUTCOMES = {"passed", "failed", "blocked", "not_run", "missing"}


def fail(code, message, **details):
    raise HandrailError(code, message, details=details)


def text(value, name):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        fail("WORKFLOW_INVALID_INPUT", name + " must be nonempty text", field=name)
    return value.strip()


def json_value(value, name):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (ValueError, TypeError, OverflowError):
        fail("WORKFLOW_INVALID_INPUT", name + " must be JSON serializable", field=name)


def criteria(value):
    if not isinstance(value, dict) or not value:
        fail("WORKFLOW_CRITERIA_REQUIRED", "Supply at least one stable criterion ID and description")
    result = {}
    for key, description in value.items():
        if text(key, "criterion_id") != key:
            fail("WORKFLOW_CRITERION_INVALID", "Criterion IDs must not have surrounding whitespace")
        result[key] = text(description, "criterion description")
    return result


def approval(value):
    """Normalize an attestation, not a permission grant or authenticated identity."""
    if isinstance(value, str):
        return {"text": text(value, "approval"), "source": "user_instruction"}
    if not isinstance(value, dict):
        fail("WORKFLOW_APPROVAL_REQUIRED", "Supply the user's approval text and optional provenance")
    result = json_value(value, "approval")
    result["text"] = text(result.get("text"), "approval.text")
    if "source" in result:
        result["source"] = text(result["source"], "approval.source")
    # All additional fields are opaque provenance, never host permission flags.
    return result


def evidence(value):
    """Text is a passing observation; structured evidence can retain failures.

Structured observations use text/observation/summary/output/description and an
optional status (passed by default). A source or status alone is not evidence.
"""
    if isinstance(value, str):
        return {"status": "passed", "text": text(value, "evidence")}
    if not isinstance(value, dict):
        fail("WORKFLOW_EVIDENCE_REQUIRED", "Supply a nonempty observed result")
    result = json_value(value, "evidence")
    if not any(isinstance(result.get(key), str) and result[key].strip()
               for key in ("text", "observation", "summary", "output", "description")):
        fail("WORKFLOW_EVIDENCE_REQUIRED", "A status or source alone is not an observed result")
    status = result.get("status", "passed")
    if not isinstance(status, str) or status not in _OUTCOMES:
        fail("WORKFLOW_EVIDENCE_INVALID", "Unsupported evidence status")
    result["status"] = status
    return result
