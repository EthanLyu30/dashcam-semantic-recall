"""Regression tests for the final-stage security hardening.

Covers:
- SEC-01  default JWT secret is refused in production / warned in dev
- SEC-02  raw originals/exports are not reachable via the public static mount
- SEC-03  /stream requires a bearer header or a signed stream ticket
- SEC-04  uploads above the configured size cap are rejected with 413
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


@pytest.fixture()
def client_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "sec.db"
    media_root = tmp_path / "media"
    monkeypatch.setenv("DVR_SEMANTIC_DB_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("MEDIA_ROOT", str(media_root))
    monkeypatch.setenv("DVR_SEMANTIC_JWT_SECRET", "sec-test-secret-32-bytes-stable-ok")
    # Tiny cap so we can exercise the 413 path without large fixtures.
    monkeypatch.setenv("DVR_SEMANTIC_MAX_UPLOAD_BYTES", "64")

    for name in list(sys.modules):
        if name.startswith("dvr_semantic_backend"):
            del sys.modules[name]

    api = importlib.import_module("dvr_semantic_backend.api")
    db = importlib.import_module("dvr_semantic_backend.db")

    # A real source file on disk so the stream route can return 200.
    source = media_root / "originals" / "vid-secret.mp4"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"\x00\x00\x00\x18ftypmp42fake-bytes")

    client = TestClient(api.create_app())
    with db.session_scope() as session:
        session.add(
            db.Video(
                id="vid-secret",
                title="secret",
                source_path=str(source),
                duration_sec=10,
                process_status="indexed",
            )
        )
    return client, "vid-secret", source


def _auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


# ---- SEC-03: stream auth ---------------------------------------------------
def test_stream_requires_credentials(client_env) -> None:
    client, video_id, _ = client_env
    resp = client.get(f"/api/videos/{video_id}/stream")
    assert resp.status_code == 401


def test_stream_accepts_bearer_header(client_env) -> None:
    client, video_id, _ = client_env
    resp = client.get(f"/api/videos/{video_id}/stream", headers=_auth_headers(client))
    assert resp.status_code == 200


def test_stream_ticket_yields_working_signed_url(client_env) -> None:
    client, video_id, _ = client_env
    ticket = client.get(
        f"/api/videos/{video_id}/stream-ticket", headers=_auth_headers(client)
    )
    assert ticket.status_code == 200, ticket.text
    url = ticket.json()["url"]
    assert url.startswith(f"/api/videos/{video_id}/stream?token=")
    # The signed URL works without any Authorization header (as VLC would use it).
    resp = client.get(url)
    assert resp.status_code == 200


def test_stream_rejects_token_for_other_video(client_env) -> None:
    client, video_id, _ = client_env
    ticket = client.get(
        f"/api/videos/{video_id}/stream-ticket", headers=_auth_headers(client)
    )
    token = ticket.json()["url"].split("token=")[1]
    # Same signed token must not unlock a different video id.
    resp = client.get(f"/api/videos/vid-other/stream?token={token}")
    assert resp.status_code == 401


# ---- SEC-02: static mount narrowed ----------------------------------------
def test_originals_not_publicly_served(client_env) -> None:
    client, _, _ = client_env
    # The raw upload exists on disk but must not be reachable via /media.
    resp = client.get("/media/originals/vid-secret.mp4")
    assert resp.status_code != 200


# ---- SEC-04: upload size cap ----------------------------------------------
def test_oversized_upload_rejected(client_env) -> None:
    client, _, _ = client_env
    big = b"x" * 200  # cap is 64 bytes in this fixture
    resp = client.post(
        "/api/videos/upload",
        headers=_auth_headers(client),
        files={"file": ("big.mp4", big, "video/mp4")},
        data={"title": "too big"},
    )
    assert resp.status_code == 413


def test_small_upload_within_cap_accepted(client_env) -> None:
    client, _, _ = client_env
    small = b"x" * 16  # under the 64-byte cap
    resp = client.post(
        "/api/videos/upload",
        headers=_auth_headers(client),
        files={"file": ("small.mp4", small, "video/mp4")},
        data={"title": "ok"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["video_id"].startswith("vid-")


# ---- SEC-01: JWT secret policy --------------------------------------------
def test_default_secret_refused_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(sys.modules):
        if name.startswith("dvr_semantic_backend"):
            del sys.modules[name]
    # Empty (not deleted) so db.py's load_dotenv(override=False) can't re-inject a
    # value from a developer's local .env — keeps the test hermetic.
    monkeypatch.setenv("DVR_SEMANTIC_JWT_SECRET", "")
    monkeypatch.setenv("DVR_SEMANTIC_ENV", "production")
    auth = importlib.import_module("dvr_semantic_backend.services.auth")
    assert auth.using_default_jwt_secret() is True
    with pytest.raises(RuntimeError):
        auth.enforce_secret_policy()


def test_custom_secret_passes_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(sys.modules):
        if name.startswith("dvr_semantic_backend"):
            del sys.modules[name]
    monkeypatch.setenv("DVR_SEMANTIC_JWT_SECRET", "a-real-strong-secret-value-1234567890")
    monkeypatch.setenv("DVR_SEMANTIC_ENV", "production")
    auth = importlib.import_module("dvr_semantic_backend.services.auth")
    assert auth.using_default_jwt_secret() is False
    auth.enforce_secret_policy()  # must not raise
