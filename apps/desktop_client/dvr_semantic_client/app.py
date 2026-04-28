from __future__ import annotations

import os
import sys
from pathlib import Path

from .api import create_api_client


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "PySide6 is required for the desktop client. "
            'Install it with: python -m pip install -e ".[desktop]"'
        ) from exc

    from .widgets.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Dashcam Semantic Recall")

    theme_path = Path(__file__).with_name("resources") / "theme.qss"
    if theme_path.exists():
        app.setStyleSheet(theme_path.read_text(encoding="utf-8"))

    base_url = os.getenv("DVR_SEMANTIC_API_BASE", "").strip()
    window = MainWindow(create_api_client(base_url))
    window.resize(1440, 920)
    window.show()
    return app.exec()

