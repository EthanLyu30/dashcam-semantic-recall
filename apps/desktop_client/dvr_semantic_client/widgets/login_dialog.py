from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .branding import make_logo_pixmap


@dataclass(frozen=True)
class LoginContext:
    """Result of a successful login bound to the RestApiClient."""

    token: str
    user_id: str
    username: str
    role: str
    display_name: str


class LoginDialog(QDialog):
    """Polished, branded username/password dialog that drives ``api_client.login``.

    On success stores the resolved :class:`LoginContext` (via :meth:`context`).
    """

    def __init__(self, api_client: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._api_client = api_client
        self._context: LoginContext | None = None

        self.setWindowTitle("DVR-Semantic 登录")
        self.setModal(True)
        self.setFixedSize(440, 560)
        self.setStyleSheet(
            "QDialog { background: #FFFFFF; }"
            "QLineEdit { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;"
            " min-height: 46px; padding: 6px 16px 6px 14px; font-size: 14px; color: #0F172A; }"
            "QLineEdit:focus { border: 1px solid #6366F1; background: #FFFFFF; }"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(self._build_form(), 1)

    # ------------------------------------------------------------------ header
    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("loginHeader")
        header.setFixedHeight(208)
        header.setStyleSheet(
            "#loginHeader { background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            " stop:0 #6366F1, stop:1 #2563EB); border: none; }"
            "QLabel { background: transparent; border: none; }"
        )
        lay = QVBoxLayout(header)
        lay.setContentsMargins(0, 30, 0, 24)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = QLabel()
        logo.setPixmap(make_logo_pixmap(76))
        logo.setFixedSize(76, 76)
        logo.setScaledContents(True)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)

        brand = QLabel("DVR-Semantic")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet("color: #FFFFFF; font-size: 25px; font-weight: 800; letter-spacing: 0.5px;")
        lay.addWidget(brand)

        tagline = QLabel("多模态行车记录仪语义检索系统")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet("color: rgba(255,255,255,0.82); font-size: 12px; letter-spacing: 1px;")
        lay.addWidget(tagline)
        return header

    # -------------------------------------------------------------------- form
    def _build_form(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame { background: #FFFFFF; } QLabel { background: transparent; border: none; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(36, 28, 36, 28)
        lay.setSpacing(12)

        welcome = QLabel("欢迎回来")
        welcome.setStyleSheet("color: #0F172A; font-size: 17px; font-weight: 800;")
        lay.addWidget(welcome)
        sub = QLabel("使用后端账号登录以获取访问令牌")
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        lay.addWidget(sub)
        lay.addSpacing(6)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("用户名")
        self.username_edit.setClearButtonEnabled(True)
        lay.addWidget(self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("密码")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        lay.addWidget(self.password_edit)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #DC2626; font-size: 12px; background: transparent;")
        self.error_label.setVisible(False)
        lay.addWidget(self.error_label)

        self.login_button = QPushButton("登 录")
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.setDefault(True)
        self.login_button.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            " stop:0 #6366F1, stop:1 #2563EB); color: #FFFFFF; border: none;"
            " border-radius: 12px; min-height: 48px; font-size: 15px; font-weight: 700; }"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            " stop:0 #4F46E5, stop:1 #1D4ED8); }"
            "QPushButton:pressed { background: #1D4ED8; }"
            "QPushButton:disabled { background: #93C5FD; color: #EFF6FF; }"
        )
        self.login_button.clicked.connect(self._on_accept)
        lay.addSpacing(4)
        lay.addWidget(self.login_button)

        lay.addStretch(1)

        hint = QLabel("演示账号    admin / admin123      reviewer / review123")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(
            "color: #64748B; font-size: 11px; background: #F1F5F9;"
            " border-radius: 8px; padding: 9px 12px;"
        )
        lay.addWidget(hint)

        # Enter advances / submits.
        self.username_edit.returnPressed.connect(self.password_edit.setFocus)
        self.password_edit.returnPressed.connect(self._on_accept)
        return card

    # ----------------------------------------------------------------------
    def context(self) -> LoginContext | None:
        return self._context

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def _on_accept(self) -> None:
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            self._show_error("请输入用户名和密码。")
            return

        self.login_button.setEnabled(False)
        self.login_button.setText("登录中…")
        try:
            payload = self._api_client.login(username, password)
        except Exception as exc:  # pragma: no cover - UI feedback path
            self.login_button.setEnabled(True)
            self.login_button.setText("登 录")
            self._show_error(f"调用登录接口失败：{exc}")
            return

        if not isinstance(payload, dict) or not payload.get("token"):
            self.login_button.setEnabled(True)
            self.login_button.setText("登 录")
            self._show_error("用户名或密码错误，未获取到访问令牌。")
            return

        self._context = LoginContext(
            token=str(payload.get("token", "")),
            user_id=str(payload.get("user_id", "")),
            username=str(payload.get("username", username)),
            role=str(payload.get("role", "")),
            display_name=str(payload.get("display_name", "")),
        )
        self.accept()
