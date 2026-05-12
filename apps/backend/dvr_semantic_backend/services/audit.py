"""Audit log helpers.

These helpers never raise: an audit failure must never break the business
request that triggered it. Errors are swallowed (and printed to stderr in dev
builds) so callers can stay unconditional.
"""
from __future__ import annotations

import sys
import uuid
from typing import Optional

from sqlalchemy import desc

from ..db import AuditLog, init_db, session_scope


def log_action(
    *,
    request_id: str,
    user_id: Optional[str],
    action: str,
    target_type: str = "",
    target_id: str = "",
    result_code: str = "00000",
    message: str = "",
) -> None:
    """Append one row to ``audit_logs``. Failures are swallowed."""
    try:
        init_db()
        with session_scope() as session:
            session.add(
                AuditLog(
                    id=uuid.uuid4().hex,
                    request_id=request_id or "",
                    user_id=user_id,
                    action=action or "",
                    target_type=target_type or "",
                    target_id=target_id or "",
                    result_code=result_code or "00000",
                    message=message or "",
                )
            )
    except Exception as exc:  # pragma: no cover - defensive, must not propagate
        print(f"[audit] failed to write log: {exc}", file=sys.stderr)


def recent_logs(limit: int = 100, user_id: Optional[str] = None) -> list[dict]:
    """Return the latest audit rows (newest first) as plain dicts."""
    try:
        limit = max(1, min(int(limit), 1000))
    except (TypeError, ValueError):
        limit = 100

    init_db()
    with session_scope() as session:
        query = session.query(AuditLog)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        rows = query.order_by(desc(AuditLog.created_at), desc(AuditLog.id)).limit(limit).all()
        return [
            {
                "id": row.id,
                "request_id": row.request_id or "",
                "user_id": row.user_id,
                "action": row.action,
                "target_type": row.target_type or "",
                "target_id": row.target_id or "",
                "result_code": row.result_code or "00000",
                "message": row.message or "",
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ]
