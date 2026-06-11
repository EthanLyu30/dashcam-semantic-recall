"""Alert severity rules: persisted, admin-editable thresholds.

The alert engine (``final_stage._severity``) grades every event by these
rules. They live in a small JSON file under the media root (config-as-file,
same lifecycle as the rest of the runtime state in ``var/``), so editing them
from the management UI is a real write that survives restarts — no new
database table needed.
"""
from __future__ import annotations

import json
from pathlib import Path

from .media_pipeline import media_root

KNOWN_EVENT_TYPES = (
    "scratch",
    "illegal_parking",
    "road_obstacle",
    "abnormal_stop",
    "pedestrian_risk",
)

DEFAULT_RULES: dict = {
    "high_risk_types": ["scratch", "pedestrian_risk"],
    "high_confidence": 0.85,
    "medium_confidence": 0.70,
}

# (path, mtime) -> rules cache so per-event severity checks don't re-read the
# file inside list loops.
_cache: tuple[str, float, dict] | None = None


def _rules_path() -> Path:
    return media_root() / "config" / "alert_rules.json"


def _validated(data: dict) -> dict:
    rules = dict(DEFAULT_RULES)
    try:
        high = float(data.get("high_confidence", rules["high_confidence"]))
        medium = float(data.get("medium_confidence", rules["medium_confidence"]))
    except (TypeError, ValueError):
        return rules
    if not (0.0 < medium < high <= 1.0):
        return rules
    types = [
        t for t in (data.get("high_risk_types") or [])
        if isinstance(t, str) and t in KNOWN_EVENT_TYPES
    ]
    rules["high_confidence"] = high
    rules["medium_confidence"] = medium
    rules["high_risk_types"] = types or list(DEFAULT_RULES["high_risk_types"])
    return rules


def load_rules() -> dict:
    """Current rules; falls back to the defaults when the file is absent/bad."""
    global _cache
    path = _rules_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return dict(DEFAULT_RULES)
    if _cache is not None and _cache[0] == str(path) and _cache[1] == mtime:
        return dict(_cache[2])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(DEFAULT_RULES)
    rules = _validated(data if isinstance(data, dict) else {})
    _cache = (str(path), mtime, rules)
    return dict(rules)


def save_rules(
    high_confidence: float,
    medium_confidence: float,
    high_risk_types: list[str] | None = None,
) -> dict:
    """Validate and persist new rules. Raises ``ValueError`` on bad input."""
    try:
        high = float(high_confidence)
        medium = float(medium_confidence)
    except (TypeError, ValueError) as exc:
        raise ValueError("thresholds must be numbers") from exc
    if not (0.0 < medium < high <= 1.0):
        raise ValueError(
            "thresholds must satisfy 0 < medium_confidence < high_confidence <= 1"
        )
    types = list(high_risk_types or DEFAULT_RULES["high_risk_types"])
    unknown = [t for t in types if t not in KNOWN_EVENT_TYPES]
    if unknown:
        raise ValueError(f"unknown event types: {', '.join(unknown)}")

    rules = {
        "high_risk_types": types,
        "high_confidence": high,
        "medium_confidence": medium,
    }
    path = _rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(rules, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    global _cache
    _cache = None
    return rules
