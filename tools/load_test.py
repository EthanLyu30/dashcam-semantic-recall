"""Concurrency / latency smoke for the running backend (SRS NFR-04).

Fires N search requests across C concurrent workers against a live backend and
reports throughput, error rate and latency percentiles. Dependency-free
(stdlib only) so it runs anywhere the project does.

Usage:
    python tools/load_test.py --base http://127.0.0.1:8000 \
        --user admin --password admin123 --requests 500 --concurrency 50
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def _post(base: str, path: str, payload: dict, token: str = "") -> tuple[int, float, bytes]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return resp.status, (time.perf_counter() - started) * 1000, body
    except Exception as exc:  # noqa: BLE001 - load tools report, don't crash
        return 0, (time.perf_counter() - started) * 1000, str(exc).encode()


def _login(base: str, user: str, password: str) -> str:
    status, _, body = _post(base, "/api/auth/login", {"username": user, "password": password})
    if status != 200:
        raise SystemExit(f"login failed ({status}): {body[:200]!r}")
    return json.loads(body)["token"]


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1))))
    return s[idx]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", default="admin123")
    ap.add_argument("--requests", type=int, default=500)
    ap.add_argument("--concurrency", type=int, default=50)
    ap.add_argument("--query", default="找一下违停")
    args = ap.parse_args()

    token = _login(args.base, args.user, args.password)
    payload = {"query": args.query, "mode": "hybrid", "top_k": 10}

    def task(_i: int) -> tuple[int, float]:
        status, ms, _ = _post(args.base, "/api/search", payload, token)
        return status, ms

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(task, range(args.requests)))
    wall = time.perf_counter() - wall_start

    latencies = [ms for status, ms in results if status == 200]
    errors = sum(1 for status, _ in results if status != 200)
    rps = args.requests / wall if wall > 0 else 0.0

    print(f"requests={args.requests} concurrency={args.concurrency}")
    print(f"wall={wall:.2f}s throughput={rps:.1f} req/s")
    print(f"errors={errors} ({errors / args.requests * 100:.1f}%)")
    print(f"latency ms: p50={_pct(latencies,50):.0f} p95={_pct(latencies,95):.0f} "
          f"p99={_pct(latencies,99):.0f} max={max(latencies, default=0):.0f}")
    # NFR-04: search budget is 4000ms.
    ok = errors == 0 and _pct(latencies, 95) < 4000
    print("VERDICT:", "PASS (p95<4s, 0 errors)" if ok else "REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
