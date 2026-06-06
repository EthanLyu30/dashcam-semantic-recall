from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


@pytest.fixture()
def export_route_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "exports.db"
    monkeypatch.setenv("DVR_SEMANTIC_DB_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("DVR_SEMANTIC_JWT_SECRET", "export-route-test-secret-32-bytes-ok")

    for name in list(sys.modules):
        if name.startswith("dvr_semantic_backend"):
            del sys.modules[name]

    api = importlib.import_module("dvr_semantic_backend.api")
    db = importlib.import_module("dvr_semantic_backend.db")
    client = TestClient(api.create_app())

    video_id = "vid-export-route"
    event_id = "evt-export-route"
    export_id = "exp-export-route"
    with db.session_scope() as session:
        session.add(
            db.Video(
                id=video_id,
                title="Export route fixture",
                source_path=str(tmp_path / "source.mp4"),
                duration_sec=12,
                process_status="indexed",
            )
        )
        session.add(
            db.SemanticEvent(
                id=event_id,
                video_id=video_id,
                event_type="scratch",
                title="Route export event",
                summary="Fixture event for export listing.",
                start_sec=2,
                end_sec=6,
                confidence=0.91,
                tags_json=["scratch"],
                vector_text="scratch route export",
                embedding=[],
                review_status="confirmed",
            )
        )

    export_path = tmp_path / "package.zip"
    with db.session_scope() as session:
        session.add(
            db.EventExport(
                id=export_id,
                event_id=event_id,
                export_type="package",
                export_path=str(export_path),
                status="success",
            )
        )

    return client, event_id, export_id, export_path


def _auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


def test_list_exports_route_returns_contract_shape(export_route_client) -> None:
    client, event_id, export_id, export_path = export_route_client

    resp = client.get(f"/api/exports?event_id={event_id}", headers=_auth_headers(client))

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert list(payload) == ["items"]
    assert payload["items"] == [
        {
            "id": export_id,
            "event_id": event_id,
            "export_type": "package",
            "status": "success",
            "export_path": str(export_path),
            "created_at": payload["items"][0]["created_at"],
        }
    ]
    assert payload["items"][0]["export_path"].endswith("package.zip")
    assert payload["items"][0]["created_at"]


def test_export_unknown_event_returns_404(export_route_client) -> None:
    client, _, _, _ = export_route_client

    resp = client.post(
        "/api/events/evt-missing/export",
        headers=_auth_headers(client),
        json={"export_type": "package"},
    )

    assert resp.status_code == 404
