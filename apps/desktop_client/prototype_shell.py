from __future__ import annotations

import sys
import webbrowser
from pathlib import Path


def prototype_home() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "prototype-source" / "原型总览.html"


def main() -> int:
    html_path = prototype_home()
    if not html_path.exists():
        print(f"Prototype home not found: {html_path}", file=sys.stderr)
        return 1

    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtWidgets import QApplication, QMainWindow
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except Exception:
        webbrowser.open(html_path.as_uri())
        print("PySide6 QtWebEngine is not available; opened the prototype in the browser.")
        return 0

    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("DVR-Semantic Prototype Shell")
    view = QWebEngineView()
    view.load(QUrl.fromLocalFile(str(html_path)))
    window.setCentralWidget(view)
    window.resize(1440, 920)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

