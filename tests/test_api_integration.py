"""End-to-end smoke test for the FastAPI app.

This test only exercises the contract we care about for the desktop demo:
login -> upload -> process -> search -> export. It uses a real ffmpeg-generated
clip and the mock model adapter, so no external services are required.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    db_path = tmp_path / "dvr_semantic.db"
    media_root = tmp_path / "media"
    monkeypatch.setenv("DVR_SEMANTIC_DB_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("MEDIA_ROOT", str(media_root))
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("DVR_SEMANTIC_JWT_SECRET", "test-secret-keep-it-stable")

    # Force re-import of modules that captured env at import time.
    import importlib
    import sys

    for name in list(sys.modules):
        if name.startswith("dvr_semantic_backend"):
            del sys.modules[name]

    from dvr_semantic_backend import api  # noqa: WPS433
    from dvr_semantic_backend.services import model_adapter

    model_adapter.reset_adapter()
    app = api.create_app()
    return TestClient(app)


def _make_video(path: Path, duration: int = 8) -> None:
    cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size=320x240:rate=10",
        "-y",
        str(path),
    ]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_login_upload_process_search_export(isolated_env: TestClient, tmp_path: Path) -> None:
    client = isolated_env

    # health works without auth
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # protected endpoint without auth -> 401
    assert client.get("/api/videos").status_code == 401

    # login
    resp = client.post("/api/auth/login", json={"username": "demo", "password": "demo123"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    token = body["token"]
    assert body["role"] == "user"
    headers = {"Authorization": f"Bearer {token}"}

    # initial list is empty
    resp = client.get("/api/videos", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []

    # upload
    video_path = tmp_path / "clip.mp4"
    _make_video(video_path, duration=6)
    with video_path.open("rb") as fh:
        resp = client.post(
            "/api/videos/upload",
            headers=headers,
            files={"file": ("clip.mp4", fh, "video/mp4")},
            data={"title": "Smoke clip"},
        )
    assert resp.status_code == 200, resp.text
    video_id = resp.json()["video_id"]
    assert video_id.startswith("vid-")

    # one-shot process
    resp = client.post(f"/api/videos/{video_id}/process", headers=headers)
    assert resp.status_code == 200, resp.text
    report = resp.json()
    assert report["frames_analyzed"] > 0
    assert report["status"] == "indexed"

    # search (mock adapter may or may not generate events; the route must still
    # respond with a stable contract even when there are zero hits).
    resp = client.post(
        "/api/search",
        headers=headers,
        json={"video_id": video_id, "query": "找一下违停", "mode": "hybrid", "top_k": 5},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "results" in payload
    assert payload["query_id"].startswith("qry-")

    # if any events did get produced, export the first one end-to-end
    resp = client.get(f"/api/events?video_id={video_id}", headers=headers)
    assert resp.status_code == 200
    events = resp.json()
    if events:
        event_id = events[0]["id"]
        resp = client.post(
            f"/api/events/{event_id}/export",
            headers=headers,
            json={"export_type": "package", "include_video": True,
                  "include_snapshot": True, "include_report": True},
        )
        assert resp.status_code == 200, resp.text
        export = resp.json()
        assert export["status"] == "success"
        assert Path(export["export_path"]).exists()
