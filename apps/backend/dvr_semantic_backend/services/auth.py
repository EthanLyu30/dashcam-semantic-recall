"""Authentication service: password hashing, JWT issuance/decoding, FastAPI deps.

The schema we rely on lives in :mod:`dvr_semantic_backend.db` (the ``users``
table). We never raise during audit-style side-effects; auth failures, however,
must surface clearly so the route layer can translate them into HTTP errors.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone  # noqa: F401  (datetime kept for type clarity)
from typing import Callable

import bcrypt
import jwt
from fastapi import Header, HTTPException

from ..db import User, init_db, session_scope

_ALLOWED_ROLES = ("user", "reviewer", "admin")
_DEFAULT_JWT_SECRET = "dvr-semantic-dev-secret-change-me"
_DEFAULT_TTL_MIN = 720  # 12 hours

# bcrypt accepts at most 72 bytes; we hash longer secrets through SHA-256 first
# so users are never surprised by silent truncation.
_BCRYPT_MAX_BYTES = 72


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    username: str
    role: str


def _jwt_secret() -> str:
    return os.getenv("DVR_SEMANTIC_JWT_SECRET", _DEFAULT_JWT_SECRET).strip() or _DEFAULT_JWT_SECRET


def _jwt_ttl_minutes() -> int:
    raw = os.getenv("DVR_SEMANTIC_JWT_TTL_MIN", "").strip()
    if not raw:
        return _DEFAULT_TTL_MIN
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_TTL_MIN
    return value if value > 0 else _DEFAULT_TTL_MIN


def _prepare_secret(plain: str) -> bytes:
    """bcrypt has a 72-byte limit; pre-hash long inputs via SHA-256 hex."""
    import hashlib

    raw = plain.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_BYTES:
        raw = hashlib.sha256(raw).hexdigest().encode("ascii")
    return raw


def hash_password(plain: str) -> str:
    if plain is None:
        raise ValueError("password is required")
    secret = _prepare_secret(plain)
    return bcrypt.hashpw(secret, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        secret = _prepare_secret(plain)
        return bcrypt.checkpw(secret, hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


def create_user(
    username: str,
    password: str,
    role: str = "user",
    display_name: str = "",
) -> str:
    """Persist a new user row and return the new user id."""
    username = (username or "").strip()
    if not username:
        raise ValueError("username is required")
    if not password:
        raise ValueError("password is required")
    if role not in _ALLOWED_ROLES:
        raise ValueError(f"unsupported role: {role}")

    init_db()
    with session_scope() as session:
        existing = session.query(User).filter(User.username == username).one_or_none()
        if existing is not None:
            raise ValueError(f"username already exists: {username}")
        user_id = uuid.uuid4().hex
        session.add(
            User(
                id=user_id,
                username=username,
                password_hash=hash_password(password),
                role=role,
                display_name=display_name or username,
            )
        )
    return user_id


def authenticate(username: str, password: str) -> AuthContext:
    """Look up a user by name + password. Raises ``ValueError`` on failure."""
    username = (username or "").strip()
    if not username or not password:
        raise ValueError("username and password are required")
    init_db()
    with session_scope() as session:
        user = session.query(User).filter(User.username == username).one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise ValueError("invalid username or password")
        return AuthContext(user_id=user.id, username=user.username, role=user.role)


def issue_token(ctx: AuthContext) -> str:
    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(minutes=_jwt_ttl_minutes())
    payload = {
        "sub": ctx.user_id,
        "username": ctx.username,
        "role": ctx.role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, _jwt_secret(), algorithm="HS256")
    # PyJWT >=2 returns str; older versions returned bytes -- normalise just in case.
    if isinstance(token, bytes):  # pragma: no cover - safety net
        token = token.decode("utf-8")
    return token


def decode_token(token: str) -> AuthContext:
    if not token:
        raise ValueError("empty token")
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError(f"invalid token: {exc}") from exc

    user_id = payload.get("sub") or ""
    username = payload.get("username") or ""
    role = payload.get("role") or ""
    if not user_id or not username or role not in _ALLOWED_ROLES:
        raise ValueError("token payload missing required claims")
    return AuthContext(user_id=user_id, username=username, role=role)


def require_auth(authorization: str = Header(default="")) -> AuthContext:
    """FastAPI dependency: parse ``Authorization: Bearer <token>`` -> AuthContext."""
    header = (authorization or "").strip()
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = header[len("bearer ") :].strip()
    try:
        return decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_role(*allowed_roles: str) -> Callable[..., AuthContext]:
    """Return a FastAPI dependency enforcing ``ctx.role in allowed_roles``."""
    allowed = tuple(allowed_roles)
    if not allowed:
        raise ValueError("require_role needs at least one role")
    for role in allowed:
        if role not in _ALLOWED_ROLES:
            raise ValueError(f"unsupported role: {role}")

    def dependency(authorization: str = Header(default="")) -> AuthContext:
        ctx = require_auth(authorization=authorization)
        if ctx.role not in allowed:
            raise HTTPException(status_code=403, detail="insufficient role")
        return ctx

    dependency.__name__ = f"require_role_{'_'.join(allowed)}"
    return dependency


_SEED_USERS = (
    ("admin", "admin123", "admin", "Administrator"),
    ("reviewer", "review123", "reviewer", "Reviewer"),
    ("demo", "demo123", "user", "Demo User"),
)


def ensure_seed_users() -> None:
    """Insert the demo accounts if the users table is empty. Idempotent."""
    init_db()
    with session_scope() as session:
        if session.query(User).count() > 0:
            return
        for username, password, role, display_name in _SEED_USERS:
            session.add(
                User(
                    id=uuid.uuid4().hex,
                    username=username,
                    password_hash=hash_password(password),
                    role=role,
                    display_name=display_name,
                )
            )
