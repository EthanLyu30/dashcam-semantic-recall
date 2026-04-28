from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path


def prototype_root() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "prototype-source"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the completed DVR-Semantic prototype pages."
    )
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    root = prototype_root()
    if not root.exists():
        print(f"Prototype source not found: {root}", file=sys.stderr)
        return 1

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(root),
    )

    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as server:
        url = f"http://127.0.0.1:{args.port}/原型总览.html"
        print(f"DVR-Semantic prototype is running at {url}")
        print("Press Ctrl+C to stop.")
        if not args.no_open:
            threading.Timer(0.4, lambda: webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

