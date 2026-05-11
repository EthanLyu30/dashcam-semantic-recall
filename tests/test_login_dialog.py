"""Smoke test: ensure ``LoginDialog`` can be constructed without opening UI."""
from __future__ import annotations

import pytest


def test_login_dialog_imports_and_constructs() -> None:
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    from dvr_semantic_client.api import MockApiClient
    from dvr_semantic_client.widgets.login_dialog import LoginContext, LoginDialog

    # QApplication is required even for non-shown dialogs in headless CI.
    app = QApplication.instance() or QApplication([])
    assert app is not None

    dialog = LoginDialog(MockApiClient())
    assert dialog.windowTitle()
    assert dialog.context() is None

    # Sanity check on the dataclass too.
    ctx = LoginContext(
        token="t",
        user_id="u",
        username="demo",
        role="admin",
        display_name="Demo",
    )
    assert ctx.token == "t"
