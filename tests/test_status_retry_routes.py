"""Route tests for FR-01 status polling and NFR-02 retry endpoint."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


@pytest.fixture()
def client_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DVR_SEMANTIC_DB_URL", f"sqlite:///{(tmp_path / 'sr.db').as_posix()}")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("DVR_SEMANTIC_JWT_SECRET", "sr-test-secret-32-bytes-stable-okay")
    for name in list(sys.modules):
        if name.startswith("dvr_semantic_backend"):
            del sys.modules[name]
    api = importlib.import_module("dvr_semantic_backend.api")
    db = importlib.import_module("dvr_semantic_backend.db")
    client = TestClient(api.create_app())
    with db.session_scope() as session:
        session.add(
            db.Video(
                id="vid-sr", title="status video",
                source_path=str(tmp_path / "missing.mp4"),
                duration_sec=42, process_status="failed", fail_reason="boom",
            )
        )
    return client


def _headers(client: TestClient, user: str, pw: str) -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"username": user, "password": pw})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


def test_status_returns_counts(client_env) -> None:
    client = client_env
    resp = client.get("/api/videos/vid-sr/status", headers=_headers(client, "demo", "demo123"))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["video_id"] == "vid-sr"
    assert body["process_status"] == "failed"
    assert body["fail_reason"] == "boom"
    assert body["duration_sec"] == 42
    assert body["segments"] == 0
    assert body["frames_total"] == 0
    assert body["events"] == 0


def test_status_unknown_video_404(client_env) -> None:
    client = client_env
    resp = client.get("/api/videos/nope/status", headers=_headers(client, "demo", "demo123"))
    assert resp.status_code == 404


def test_status_requires_auth(client_env) -> None:
    assert client_env.get("/api/videos/vid-sr/status").status_code == 401


def test_retry_requires_reviewer_or_admin(client_env) -> None:
    client = client_env
    # plain user is forbidden from retrying
    resp = client.post("/api/videos/vid-sr/retry", headers=_headers(client, "demo", "demo123"))
    assert resp.status_code == 403


def test_retry_unknown_video_404(client_env) -> None:
    client = client_env
    resp = client.post("/api/videos/nope/retry", headers=_headers(client, "admin", "admin123"))
    assert resp.status_code == 404


def test_retry_failed_video_surfaces_error(client_env) -> None:
    client = client_env
    # The source file is missing on disk, so a real retry fails with 500 and is
    # audited rather than silently swallowed (the path still exercises the route
    # + RBAC without needing ffmpeg).
    resp = client.post("/api/videos/vid-sr/retry", headers=_headers(client, "admin", "admin123"))
    assert resp.status_code == 500
