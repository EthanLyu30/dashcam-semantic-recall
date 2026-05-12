from __future__ import annotations

import os
import sys
from pathlib import Path

from .api import MockApiClient, RestApiClient


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "PySide6 is required for the desktop client. "
            'Install it with: python -m pip install -e ".[desktop]"'
        ) from exc

    from .widgets.login_dialog import LoginContext, LoginDialog
    from .widgets.main_window import MainWindow

    from PySide6.QtGui import QFont

    app = QApplication(sys.argv)
    app.setApplicationName("Dashcam Semantic Recall")

    base_font = QFont("Microsoft YaHei UI", 10)
    base_font.setStyleStrategy(
        QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality
    )
    app.setFont(base_font)

    theme_path = Path(__file__).with_name("resources") / "theme.qss"
    if theme_path.exists():
        app.setStyleSheet(theme_path.read_text(encoding="utf-8"))

    base_url = os.getenv("DVR_SEMANTIC_API_BASE", "").strip()

    if base_url:
        api_client: object = RestApiClient(base_url)
        dialog = LoginDialog(api_client)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return 0
        login_ctx = dialog.context()
        if login_ctx is None:
            return 0
    else:
        api_client = MockApiClient()
        login_ctx = LoginContext(
            token="mock-token",
            user_id="mock-user",
            username="demo",
            role="admin",
            display_name="Mock 演示用户",
        )

    window = MainWindow(api_client, login_ctx, base_url=base_url)
    window.resize(1440, 920)
    window.show()
    return app.exec()
