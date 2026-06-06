"""Final-stage operational views derived from the core DVR tables.

These helpers intentionally avoid new persistence tables. The final delivery
needs dashboard/report/alert/settings/user-role APIs to reflect real project
state, and the existing videos/events/search/export/audit/users tables already
contain enough information for a deterministic operational view.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import func

from ..db import (
    EventExport,
    IS_SQLITE,
    SearchQuery,
    SemanticEvent,
    User,
    Video,
    session_scope,
)
from .media_pipeline import media_root


EVENT_LABELS = {
    "scratch": "剐蹭",
    "illegal_parking": "违停",
    "road_obstacle": "道路障碍",
    "abnormal_stop": "异常停车",
    "pedestrian_risk": "行人风险",
    "normal": "正常",
}

ROLE_DEFS = {
    "admin": {
        "name": "管理员",
        "permissions": ["*"],
    },
    "reviewer": {
        "name": "审核人员",
        "permissions": [
            "video:read",
            "event:read",
            "event:review",
            "export:read",
            "audit:read",
        ],
    },
    "user": {
        "name": "普通用户",
        "permissions": [
            "video:read",
            "video:upload",
            "search:create",
            "event:export",
        ],
    },
}

PERMISSIONS = sorted(
    {
        "video:read",
        "video:upload",
        "video:process",
        "search:create",
        "event:read",
        "event:review",
        "event:export",
        "export:read",
        "audit:read",
        "settings:read",
        "user:read",
    }
)


def _today_bounds(target: date | None = None) -> tuple[datetime, datetime]:
    day = target or datetime.utcnow().date()
    start = datetime.combine(day, time.min)
    return start, start + timedelta(days=1)


def _iso(dt) -> str:
    return dt.isoformat() if dt else ""


def _count_items(rows: list[tuple[str, int]]) -> list[dict]:
    return [
        {
            "key": key or "unknown",
            "label": EVENT_LABELS.get(key or "", key or "未知"),
            "count": int(count or 0),
        }
        for key, count in rows
    ]


def event_distribution() -> list[dict]:
    with session_scope() as session:
        rows = (
            session.query(SemanticEvent.event_type, func.count(SemanticEvent.id))
            .group_by(SemanticEvent.event_type)
            .order_by(func.count(SemanticEvent.id).desc())
            .all()
        )
    return _count_items([(str(key), int(count)) for key, count in rows])


def dashboard_overview() -> dict:
    with session_scope() as session:
        processed = session.query(Video).filter(Video.process_status == "indexed").count()
        queries = session.query(SearchQuery).count()
        events = session.query(SemanticEvent).count()
        pending = (
            session.query(SemanticEvent)
            .filter(SemanticEvent.review_status.in_(("pending", "reviewing")))
            .count()
        )
        failures = session.query(Video).filter(Video.process_status.like("%fail%")).count()

    provider = (os.getenv("MODEL_PROVIDER") or "mock").strip().lower() or "mock"
    api_key_configured = bool(os.getenv("MODEL_API_KEY", "").strip())
    return {
        "processed_video_count": processed,
        "semantic_query_count": queries,
        "identified_event_count": events,
        "pending_review_count": pending,
        "engine_status": "degraded" if failures else "healthy",
        "model_nodes": {
            "online": 1,
            "total": 1,
            "provider": provider,
            "api_key_configured": api_key_configured,
        },
    }


def dashboard_trends(days: int = 7) -> dict:
    days = max(1, min(int(days or 7), 30))
    today = datetime.utcnow().date()
    labels: list[str] = []
    event_counts: list[int] = []
    query_counts: list[int] = []
    worker_load: list[float] = []

    with session_scope() as session:
        for offset in range(days - 1, -1, -1):
            day = today - timedelta(days=offset)
            start, end = _today_bounds(day)
            labels.append(day.strftime("%m-%d"))
            event_count = (
                session.query(SemanticEvent)
                .filter(SemanticEvent.created_at >= start, SemanticEvent.created_at < end)
                .count()
            )
            query_count = (
                session.query(SearchQuery)
                .filter(SearchQuery.created_at >= start, SearchQuery.created_at < end)
                .count()
            )
            event_counts.append(event_count)
            query_counts.append(query_count)
            worker_load.append(round(min(0.95, (event_count * 0.08) + (query_count * 0.02)), 2))

    return {
        "days": labels,
        "event_counts": event_counts,
        "query_counts": query_counts,
        "worker_load": worker_load,
    }


def review_feed(limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit or 20), 100))
    with session_scope() as session:
        rows = (
            session.query(SemanticEvent)
            .filter(SemanticEvent.review_status.in_(("pending", "reviewing")))
            .order_by(SemanticEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "event_id": row.id,
                "title": row.title,
                "confidence": float(row.confidence or 0.0),
                "created_at": _iso(row.created_at),
            }
            for row in rows
        ]


def _alert_status(event: SemanticEvent) -> str:
    if event.review_status == "confirmed":
        return "resolved"
    if event.review_status == "rejected":
        return "ignored"
    if event.review_status == "reviewing":
        return "acknowledged"
    return "open"


def _severity(event: SemanticEvent) -> str:
    confidence = float(event.confidence or 0.0)
    if event.event_type in {"scratch", "pedestrian_risk"} or confidence >= 0.85:
        return "high"
    if confidence >= 0.7:
        return "medium"
    return "low"


def _alert_item(event: SemanticEvent) -> dict:
    return {
        "id": f"alt-{event.id}",
        "event_id": event.id,
        "title": event.title,
        "severity": _severity(event),
        "status": _alert_status(event),
        "created_at": _iso(event.created_at),
    }


def alert_summary() -> dict:
    start, end = _today_bounds()
    with session_scope() as session:
        open_count = (
            session.query(SemanticEvent)
            .filter(SemanticEvent.review_status.in_(("pending", "reviewing")))
            .count()
        )
        today_count = (
            session.query(SemanticEvent)
            .filter(SemanticEvent.created_at >= start, SemanticEvent.created_at < end)
            .count()
        )
        resolved_count = (
            session.query(SemanticEvent)
            .filter(SemanticEvent.review_status == "confirmed")
            .count()
        )
    return {
        "open_count": open_count,
        "today_count": today_count,
        "resolved_count": resolved_count,
        "avg_response_minutes": 2.0 if resolved_count else 0.0,
    }


def list_alerts(status: str | None = None, event_type: str | None = None) -> dict:
    with session_scope() as session:
        query = session.query(SemanticEvent).filter(SemanticEvent.event_type != "normal")
        if event_type:
            query = query.filter(SemanticEvent.event_type == event_type)
        events = query.order_by(SemanticEvent.created_at.desc()).all()
        items = [_alert_item(event) for event in events]
    if status:
        items = [item for item in items if item["status"] == status]
    return {"items": items, "total": len(items)}


def _event_id_from_external(prefix: str, external_id: str) -> str:
    value = external_id or ""
    return value[len(prefix):] if value.startswith(prefix) else value


def update_alert(alert_id: str, status: str) -> dict:
    event_id = _event_id_from_external("alt-", alert_id)
    review_status = "reviewing" if status == "acknowledged" else "confirmed"
    with session_scope() as session:
        event = session.get(SemanticEvent, event_id)
        if event is None:
            raise ValueError(f"unknown alert: {alert_id}")
        event.review_status = review_status
    return {"id": alert_id, "status": status}


def _risk_level(event: SemanticEvent) -> str:
    severity = _severity(event)
    return {"high": "high", "medium": "medium", "low": "low"}[severity]


def _accident_item(event: SemanticEvent) -> dict:
    return {
        "id": f"acc-{event.id}",
        "event_id": event.id,
        "title": event.title,
        "risk_level": _risk_level(event),
        "summary": event.summary or "",
        "created_at": _iso(event.created_at),
    }


def list_accidents() -> list[dict]:
    risk_types = ("scratch", "pedestrian_risk", "abnormal_stop", "road_obstacle")
    with session_scope() as session:
        events = (
            session.query(SemanticEvent)
            .filter(SemanticEvent.event_type.in_(risk_types))
            .order_by(SemanticEvent.confidence.desc(), SemanticEvent.created_at.desc())
            .all()
        )
        return [_accident_item(event) for event in events]


def accident_detail(accident_id: str) -> dict:
    event_id = _event_id_from_external("acc-", accident_id)
    with session_scope() as session:
        event = session.get(SemanticEvent, event_id)
        if event is None:
            raise ValueError(f"unknown accident: {accident_id}")
        export_exists = session.query(EventExport).filter(EventExport.event_id == event.id).count() > 0
        item = _accident_item(event)
        item.update(
            {
                "video_id": event.video_id,
                "start_sec": int(event.start_sec or 0),
                "end_sec": int(event.end_sec or 0),
                "confidence": float(event.confidence or 0.0),
                "tags": list(event.tags_json or []),
                "evidence_ready": export_exists,
            }
        )
        return item


def accident_summary(accident_id: str) -> dict:
    detail = accident_detail(accident_id)
    summary = (
        f"事件 {detail['event_id']} 发生在 {detail['start_sec']}s-"
        f"{detail['end_sec']}s，风险等级为 {detail['risk_level']}，"
        f"置信度 {detail['confidence']:.2f}。建议保留原视频、关键帧和导出证据包。"
    )
    return {
        "accident_id": accident_id,
        "summary": summary,
        "updated_at": datetime.utcnow().isoformat(),
    }


def daily_report(target_date: date | None = None) -> dict:
    day = target_date or datetime.utcnow().date()
    start, end = _today_bounds(day)
    with session_scope() as session:
        processed = (
            session.query(Video)
            .filter(Video.created_at >= start, Video.created_at < end)
            .count()
        )
        events = (
            session.query(SemanticEvent)
            .filter(SemanticEvent.created_at >= start, SemanticEvent.created_at < end)
            .count()
        )
        queries = (
            session.query(SearchQuery)
            .filter(SearchQuery.created_at >= start, SearchQuery.created_at < end)
            .count()
        )
        exports = (
            session.query(EventExport)
            .filter(EventExport.created_at >= start, EventExport.created_at < end)
            .count()
        )
        pending = (
            session.query(SemanticEvent)
            .filter(
                SemanticEvent.review_status.in_(("pending", "reviewing")),
                SemanticEvent.created_at >= start,
                SemanticEvent.created_at < end,
            )
            .count()
        )
        rows = (
            session.query(SemanticEvent.event_type, func.count(SemanticEvent.id))
            .filter(SemanticEvent.created_at >= start, SemanticEvent.created_at < end)
            .group_by(SemanticEvent.event_type)
            .all()
        )
    distribution = _count_items([(str(key), int(count)) for key, count in rows])
    top = distribution[0]["label"] if distribution else "暂无事件"
    return {
        "date": day.isoformat(),
        "processed_video_count": processed,
        "identified_event_count": events,
        "semantic_query_count": queries,
        "evidence_export_count": exports,
        "pending_review_count": pending,
        "event_distribution": distribution,
        "risk_summary": f"当日主要风险类型：{top}；待复核 {pending} 条。",
    }


def export_daily_report(target_date: date | None = None) -> dict:
    report = daily_report(target_date)
    out_dir = media_root() / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_id = f"rpt-{report['date']}"
    json_path = out_dir / f"{report_id}.json"
    md_path = out_dir / f"{report_id}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(
        "\n".join(
            [
                f"# 全天业务报告 {report['date']}",
                "",
                f"- 处理视频: {report['processed_video_count']}",
                f"- 关键事件: {report['identified_event_count']}",
                f"- 语义检索: {report['semantic_query_count']}",
                f"- 证据导出: {report['evidence_export_count']}",
                f"- 待复核: {report['pending_review_count']}",
                "",
                report["risk_summary"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"report_id": report_id, "status": "success", "export_path": str(md_path.resolve())}


def model_settings() -> dict:
    provider = (os.getenv("MODEL_PROVIDER") or "mock").strip().lower() or "mock"
    return {
        "provider": provider,
        "model_name": os.getenv("MODEL_NAME", "").strip()
        or ("deepseek-vl" if provider == "deepseek" else "qwen-vl-plus"),
        "base_url": os.getenv("MODEL_BASE_URL", "").strip(),
        "api_key_configured": bool(os.getenv("MODEL_API_KEY", "").strip()),
        "use_embeddings": os.getenv("DVR_SEMANTIC_USE_EMBEDDINGS", "").strip().lower()
        in {"1", "true", "yes"},
        "media_root": str(media_root()),
        "db_engine": "sqlite" if IS_SQLITE else "postgresql",
    }


def model_test() -> dict:
    settings = model_settings()
    if settings["provider"] == "mock":
        return {
            "provider": "mock",
            "status": "ok",
            "message": "当前使用确定性 mock 适配器，适合离线演示。",
        }
    if not settings["api_key_configured"]:
        return {
            "provider": settings["provider"],
            "status": "fallback",
            "message": "未检测到 MODEL_API_KEY，运行时会自动回退到 mock。",
        }
    return {
        "provider": settings["provider"],
        "status": "configured",
        "message": "模型环境变量已配置；真实请求将在视频帧分析时发起。",
    }


def security_settings() -> dict:
    ttl_raw = os.getenv("DVR_SEMANTIC_JWT_TTL_MIN", "720").strip()
    try:
        ttl = int(ttl_raw)
    except ValueError:
        ttl = 720
    return {
        "bearer_auth_enabled": True,
        "audit_enabled": True,
        "jwt_ttl_min": ttl,
        "roles": list(ROLE_DEFS),
    }


def list_users() -> list[dict]:
    with session_scope() as session:
        users = session.query(User).order_by(User.created_at.asc(), User.username.asc()).all()
        return [
            {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "display_name": user.display_name or user.username,
                "created_at": _iso(user.created_at),
            }
            for user in users
        ]


def roles() -> list[dict]:
    return [
        {"id": role_id, "name": data["name"], "permissions": list(data["permissions"])}
        for role_id, data in ROLE_DEFS.items()
    ]


def permissions() -> list[str]:
    return list(PERMISSIONS)
