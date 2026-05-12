from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class LoginContext:
    """Result of a successful login bound to the RestApiClient."""

    token: str
    user_id: str
    username: str
    role: str
    display_name: str


class LoginDialog(QDialog):
    """Modal username/password dialog that drives ``api_client.login(...)``.

    The supplied ``api_client`` must expose ``login(username, password)`` that
    returns a payload dict (and stores the token internally for RestApiClient).
    On success the dialog stores the resolved :class:`LoginContext` accessible
    via :meth:`context`.
    """

    def __init__(self, api_client: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._api_client = api_client
        self._context: LoginContext | None = None

        self.setWindowTitle("DVR-Semantic 登录")
        self.setModal(True)
        self.setMinimumWidth(360)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("用户名")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("密码")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        intro = QLabel("使用后端账号登录以获取访问令牌。")
        intro.setWordWrap(True)

        form = QFormLayout()
        form.addRow("用户名", self.username_edit)
        form.addRow("密码", self.password_edit)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setText("登录")
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button is not None:
            cancel_button.setText("取消")
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)
        root.addWidget(intro)
        root.addLayout(form)
        root.addWidget(self.button_box, alignment=Qt.AlignmentFlag.AlignRight)

    # ----------------------------------------------------------------------
    def context(self) -> LoginContext | None:
        return self._context

    def _on_accept(self) -> None:
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            QMessageBox.warning(self, "登录失败", "请输入用户名和密码。")
            return
        try:
            payload = self._api_client.login(username, password)
        except Exception as exc:  # pragma: no cover - UI feedback path
            QMessageBox.critical(self, "登录失败", f"调用登录接口失败：\n{exc}")
            return

        if not isinstance(payload, dict) or not payload.get("token"):
            QMessageBox.critical(self, "登录失败", "未获取到访问令牌，请检查账号。")
            return

        self._context = LoginContext(
            token=str(payload.get("token", "")),
            user_id=str(payload.get("user_id", "")),
            username=str(payload.get("username", username)),
            role=str(payload.get("role", "")),
            display_name=str(payload.get("display_name", "")),
        )
        self.accept()
