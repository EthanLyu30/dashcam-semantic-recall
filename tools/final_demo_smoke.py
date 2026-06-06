"""Final-stage REST smoke check for a running backend.

This script does not read or print model API keys. Configure keys only through
the backend process environment, then run this checker against that backend.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

import requests


CHECKS: tuple[tuple[str, str], ...] = (
    ("GET", "/health"),
    ("GET", "/api/dashboard/overview"),
    ("GET", "/api/dashboard/trends?days=3"),
    ("GET", "/api/dashboard/event-distribution"),
    ("GET", "/api/dashboard/review-feed?limit=5"),
    ("GET", "/api/alerts/summary"),
    ("GET", "/api/alerts"),
    ("GET", "/api/accidents"),
    ("GET", "/api/reports/daily"),
    ("GET", "/api/settings/model"),
    ("POST", "/api/settings/model/test"),
    ("GET", "/api/settings/security"),
    ("GET", "/api/users"),
    ("GET", "/api/roles"),
    ("GET", "/api/permissions"),
    ("GET", "/api/audit/logs?limit=5"),
)


def _request(
    method: str,
    base_url: str,
    path: str,
    token: str = "",
    timeout: float = 10.0,
) -> tuple[int, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{base_url.rstrip('/')}{path}"
    if method == "POST":
        resp = requests.post(url, headers=headers, json={}, timeout=timeout)
    else:
        resp = requests.get(url, headers=headers, timeout=timeout)
    try:
        payload = resp.json()
    except ValueError:
        payload = resp.text[:200]
    return resp.status_code, payload


def _login(base_url: str, username: str, password: str, timeout: float) -> str:
    resp = requests.post(
        f"{base_url.rstrip('/')}/api/auth/login",
        json={"username": username, "password": password},
        timeout=timeout,
    )
    resp.raise_for_status()
    payload = resp.json() or {}
    token = str(payload.get("token", ""))
    if not token:
        raise RuntimeError("login response did not include token")
    return token


def main() -> int:
    parser = argparse.ArgumentParser(description="Check final-stage backend APIs.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    failures: list[str] = []

    try:
        health_status, health = _request("GET", base_url, "/health", timeout=args.timeout)
    except Exception as exc:
        print(f"[FAIL] backend unreachable: {exc}")
        return 2
    if health_status != 200:
        print(f"[FAIL] /health -> {health_status}: {health}")
        return 2
    print(f"[OK] /health -> {health_status}")

    try:
        token = _login(base_url, args.username, args.password, args.timeout)
    except Exception as exc:
        print(f"[FAIL] login failed: {exc}")
        return 2
    print(f"[OK] login as {args.username}")

    for method, path in CHECKS:
        if path == "/health":
            continue
        try:
            status, payload = _request(method, base_url, path, token, args.timeout)
        except Exception as exc:
            failures.append(f"{method} {path}: {exc}")
            print(f"[FAIL] {method} {path}: {exc}")
            continue
        if status >= 400:
            failures.append(f"{method} {path}: HTTP {status} {payload}")
            print(f"[FAIL] {method} {path} -> {status}: {payload}")
            continue
        if isinstance(payload, dict):
            keys = ", ".join(list(payload.keys())[:5])
            print(f"[OK] {method} {path} -> {status} ({keys})")
        else:
            print(f"[OK] {method} {path} -> {status}")

    if failures:
        print("\nFinal-stage smoke failed:")
        for item in failures:
            print(f"- {item}")
        return 1
    print("\nFinal-stage smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
