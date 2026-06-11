from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


@pytest.fixture()
def final_stage_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "final_stage.db"
    monkeypatch.setenv("DVR_SEMANTIC_DB_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("MODEL_PROVIDER", "deepseek")
    monkeypatch.setenv("MODEL_API_KEY", "")
    monkeypatch.setenv("MODEL_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("DVR_SEMANTIC_JWT_SECRET", "final-stage-secret-32-bytes-ok-for-tests")

    for name in list(sys.modules):
        if name.startswith("dvr_semantic_backend"):
            del sys.modules[name]

    api = importlib.import_module("dvr_semantic_backend.api")
    db = importlib.import_module("dvr_semantic_backend.db")
    client = TestClient(api.create_app())

    video_id = "vid-final-stage"
    event_id = "evt-final-stage"
    export_id = "exp-final-stage"

    with db.session_scope() as session:
        session.add(
            db.Video(
                id=video_id,
                title="Final stage dashcam clip",
                source_path=str(tmp_path / "source.mp4"),
                duration_sec=60,
                process_status="indexed",
            )
        )
        session.add(
            db.SemanticEvent(
                id=event_id,
                video_id=video_id,
                event_type="scratch",
                title="疑似侧向剐蹭",
                summary="车辆右侧出现疑似剐蹭风险，需要复核并导出证据。",
                start_sec=12,
                end_sec=20,
                confidence=0.88,
                tags_json=["剐蹭", "右侧接触"],
                vector_text="疑似侧向剐蹭 右侧接触",
                embedding=[],
                review_status="pending",
            )
        )
        session.add(
            db.SearchQuery(
                id="qry-final-stage",
                video_id=video_id,
                query_text="找一下剐蹭",
                mode="hybrid",
                elapsed_ms=12,
                result_count=1,
            )
        )

    with db.session_scope() as session:
        session.add(
            db.EventExport(
                id=export_id,
                event_id=event_id,
                export_type="package",
                export_path=str(tmp_path / "package.zip"),
                status="success",
            )
        )

    return client, event_id


def _headers(client: TestClient, username: str = "admin", password: str = "admin123") -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


def test_final_stage_dashboard_report_and_settings(final_stage_client) -> None:
    client, _ = final_stage_client
    headers = _headers(client)

    overview = client.get("/api/dashboard/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    assert overview.json()["processed_video_count"] == 1
    assert overview.json()["identified_event_count"] == 1
    assert overview.json()["model_nodes"]["provider"] == "deepseek"

    trends = client.get("/api/dashboard/trends?days=3", headers=headers)
    assert trends.status_code == 200, trends.text
    assert len(trends.json()["days"]) == 3

    distribution = client.get("/api/dashboard/event-distribution", headers=headers)
    assert distribution.status_code == 200, distribution.text
    assert distribution.json()["items"][0]["key"] == "scratch"

    report = client.get("/api/reports/daily", headers=headers)
    assert report.status_code == 200, report.text
    assert report.json()["identified_event_count"] == 1
    assert report.json()["evidence_export_count"] == 1

    export = client.post("/api/reports/daily/export", headers=headers)
    assert export.status_code == 200, export.text
    assert Path(export.json()["export_path"]).exists()

    model = client.get("/api/settings/model", headers=headers)
    assert model.status_code == 200, model.text
    assert model.json()["provider"] == "deepseek"
    assert model.json()["api_key_configured"] is False

    model_test = client.post("/api/settings/model/test", headers=headers)
    assert model_test.status_code == 200, model_test.text
    assert model_test.json()["status"] == "fallback"

    security = client.get("/api/settings/security", headers=headers)
    assert security.status_code == 200, security.text
    assert security.json()["bearer_auth_enabled"] is True


def test_final_stage_alerts_accidents_and_admin_catalogs(final_stage_client) -> None:
    client, event_id = final_stage_client
    headers = _headers(client)

    alerts = client.get("/api/alerts", headers=headers)
    assert alerts.status_code == 200, alerts.text
    assert alerts.json()["total"] == 1
    alert_id = alerts.json()["items"][0]["id"]

    ack = client.post(f"/api/alerts/{alert_id}/ack", headers=headers)
    assert ack.status_code == 200, ack.text
    assert ack.json()["status"] == "acknowledged"

    resolve = client.post(f"/api/alerts/{alert_id}/resolve", headers=headers)
    assert resolve.status_code == 200, resolve.text
    assert resolve.json()["status"] == "resolved"

    accidents = client.get("/api/accidents", headers=headers)
    assert accidents.status_code == 200, accidents.text
    assert accidents.json()["items"][0]["event_id"] == event_id

    accident_id = accidents.json()["items"][0]["id"]
    detail = client.get(f"/api/accidents/{accident_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["evidence_ready"] is True

    summary = client.post(f"/api/accidents/{accident_id}/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert event_id in summary.json()["summary"]

    users = client.get("/api/users", headers=headers)
    assert users.status_code == 200, users.text
    assert {item["username"] for item in users.json()["items"]} >= {"admin", "reviewer", "demo"}

    roles = client.get("/api/roles", headers=headers)
    assert roles.status_code == 200, roles.text
    assert {item["id"] for item in roles.json()["items"]} == {"admin", "reviewer", "user"}

    permissions = client.get("/api/permissions", headers=headers)
    assert permissions.status_code == 200, permissions.text
    assert "event:review" in permissions.json()["permissions"]

    user_headers = _headers(client, "demo", "demo123")
    forbidden = client.get("/api/users", headers=user_headers)
    assert forbidden.status_code == 403


def test_alert_rules_get_update_and_severity_effect(final_stage_client) -> None:
    client, _ = final_stage_client
    headers = _headers(client)

    # Defaults come back when no rules file has been written yet.
    rules = client.get("/api/alerts/rules", headers=headers)
    assert rules.status_code == 200, rules.text
    assert rules.json()["high_confidence"] == 0.85
    assert rules.json()["medium_confidence"] == 0.7
    assert "scratch" in rules.json()["high_risk_types"]

    # Invalid thresholds are rejected.
    bad = client.put(
        "/api/alerts/rules",
        json={"high_confidence": 0.6, "medium_confidence": 0.9},
        headers=headers,
    )
    assert bad.status_code == 400

    # Non-admin cannot edit rules.
    user_headers = _headers(client, "demo", "demo123")
    forbidden = client.put(
        "/api/alerts/rules",
        json={"high_confidence": 0.9, "medium_confidence": 0.5},
        headers=user_headers,
    )
    assert forbidden.status_code == 403

    # A valid update persists and immediately changes alert severity: the
    # seeded scratch event (confidence 0.88) drops to "medium" once scratch is
    # no longer a high-risk type and the high threshold rises above 0.88.
    saved = client.put(
        "/api/alerts/rules",
        json={
            "high_confidence": 0.95,
            "medium_confidence": 0.5,
            "high_risk_types": ["pedestrian_risk"],
        },
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["high_confidence"] == 0.95
    assert saved.json()["high_risk_types"] == ["pedestrian_risk"]

    again = client.get("/api/alerts/rules", headers=headers)
    assert again.json()["high_confidence"] == 0.95

    alerts = client.get("/api/alerts", headers=headers)
    assert alerts.status_code == 200, alerts.text
    assert alerts.json()["items"][0]["severity"] == "medium"


def test_create_user_route(final_stage_client) -> None:
    client, _ = final_stage_client
    headers = _headers(client)

    created = client.post(
        "/api/users",
        json={
            "username": "patrol01",
            "password": "patrol-pass-123",
            "role": "reviewer",
            "display_name": "巡查员一号",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["username"] == "patrol01"
    assert created.json()["role"] == "reviewer"

    # The new account can log in immediately.
    login = client.post(
        "/api/auth/login",
        json={"username": "patrol01", "password": "patrol-pass-123"},
    )
    assert login.status_code == 200, login.text
    assert login.json()["role"] == "reviewer"

    # Duplicate username -> 409; unknown role -> 400; non-admin -> 403.
    dup = client.post(
        "/api/users",
        json={"username": "patrol01", "password": "x", "role": "user"},
        headers=headers,
    )
    assert dup.status_code == 409

    bad_role = client.post(
        "/api/users",
        json={"username": "patrol02", "password": "x", "role": "superadmin"},
        headers=headers,
    )
    assert bad_role.status_code == 400

    user_headers = _headers(client, "demo", "demo123")
    forbidden = client.post(
        "/api/users",
        json={"username": "patrol03", "password": "x", "role": "user"},
        headers=user_headers,
    )
    assert forbidden.status_code == 403
