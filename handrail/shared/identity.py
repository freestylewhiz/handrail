"""Stable serialized identifiers and UTC timestamps."""
import hashlib
import json
import uuid
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def new_id(prefix=""):
    return prefix + uuid.uuid4().hex


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()
