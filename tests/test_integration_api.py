"""Tests for the FR-06 third-party integration surface (API-key auth)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

_API_KEY = "integration-key-abc123"


def _fresh_modules() -> None:
    for name in list(sys.modules):
        if name.startswith("dvr_semantic_backend"):
            del sys.modules[name]


@pytest.fixture()
def integ_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DVR_SEMANTIC_DB_URL", f"sqlite:///{(tmp_path / 'integ.db').as_posix()}")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("DVR_SEMANTIC_JWT_SECRET", "integ-test-secret-32-bytes-stable-ok")
    monkeypatch.setenv("DVR_SEMANTIC_INTEGRATION_API_KEYS", f"{_API_KEY}, second-key")
    _fresh_modules()

    api = importlib.import_module("dvr_semantic_backend.api")
    db = importlib.import_module("dvr_semantic_backend.db")
    client = TestClient(api.create_app())

    with db.session_scope() as session:
        session.add(
            db.Video(id="vid-i", title="v", source_path=str(tmp_path / "s.mp4"),
                     duration_sec=10, process_status="indexed")
        )
        session.add(
            db.SemanticEvent(
                id="evt-confirmed", video_id="vid-i", event_type="scratch",
                title="确认事件", summary="已复核确认的剐蹭事件。",
                start_sec=2, end_sec=6, confidence=0.9, tags_json=["剐蹭"],
                vector_text="确认事件", embedding=[], review_status="confirmed",
            )
        )
        session.add(
            db.SemanticEvent(
                id="evt-pending", video_id="vid-i", event_type="scratch",
                title="待复核", summary="尚未复核。", start_sec=7, end_sec=9,
                confidence=0.5, tags_json=[], vector_text="待复核",
                embedding=[], review_status="pending",
            )
        )
    return client


def test_missing_api_key_rejected(integ_client) -> None:
    resp = integ_client.get("/api/integration/events")
    assert resp.status_code == 401


def test_wrong_api_key_rejected(integ_client) -> None:
    resp = integ_client.get(
        "/api/integration/events", headers={"X-Api-Key": "totally-wrong"}
    )
    assert resp.status_code == 401


def test_valid_api_key_returns_only_confirmed_events(integ_client) -> None:
    resp = integ_client.get(
        "/api/integration/events", headers={"X-Api-Key": _API_KEY}
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    ids = {item["event_id"] for item in payload["items"]}
    assert ids == {"evt-confirmed"}  # pending event is not exposed
    assert payload["total"] == 1


def test_event_detail_requires_key_and_confirmed(integ_client) -> None:
    ok = integ_client.get(
        "/api/integration/events/evt-confirmed", headers={"X-Api-Key": _API_KEY}
    )
    assert ok.status_code == 200
    assert ok.json()["event_id"] == "evt-confirmed"

    # pending event is hidden from the integration surface
    hidden = integ_client.get(
        "/api/integration/events/evt-pending", headers={"X-Api-Key": _API_KEY}
    )
    assert hidden.status_code == 404


def test_integration_disabled_without_configured_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DVR_SEMANTIC_DB_URL", f"sqlite:///{(tmp_path / 'off.db').as_posix()}")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("DVR_SEMANTIC_JWT_SECRET", "integ-off-secret-32-bytes-stable-ok")
    monkeypatch.delenv("DVR_SEMANTIC_INTEGRATION_API_KEYS", raising=False)
    _fresh_modules()
    api = importlib.import_module("dvr_semantic_backend.api")
    client = TestClient(api.create_app())
    resp = client.get("/api/integration/events", headers={"X-Api-Key": "anything"})
    assert resp.status_code == 503
