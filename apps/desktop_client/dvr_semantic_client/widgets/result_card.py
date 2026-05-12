from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..models import SemanticEvent


class ResultCard(QFrame):
    """检索结果卡片：左侧大号置信度色块 + 右侧标题/时间/摘要/tags。

    hover 时通过 QGraphicsDropShadowEffect 给出"浮起"阴影感，以补偿
    Qt 没有 CSS transition 的不足。

    严格保持 ``self.event = event`` 放在构造函数最后赋值——这条不能动，
    否则会触发 PySide6 6.x 在 Windows 上的构造期 segfault（详见仓库历史）。
    """

    selected = Signal(object)

    def __init__(self, event: SemanticEvent, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selected = False
        self._confidence_color = "#2563EB" if event.confidence >= 0.85 else "#64748B"

        self.color_bar = QFrame()
        self.color_bar.setFixedWidth(4)
        self.color_bar.setMinimumHeight(96)

        confidence = QLabel(f"命中率 {event.confidence_percent}")
        confidence.setStyleSheet(
            f"color: {self._confidence_color}; font-size: 10px; "
            "font-weight: 800; background: transparent; border: none;"
        )
        event_id = QLabel(event.id[:10].upper())
        event_id.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        event_id.setStyleSheet(
            "color: #94A3B8; font-size: 10px; font-family: Consolas, monospace; "
            "background: transparent; border: none;"
        )
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.addWidget(confidence)
        meta_row.addStretch()
        meta_row.addWidget(event_id)

        title = QLabel(event.title)
        title.setWordWrap(True)
        title.setStyleSheet(
            "color: #0F172A; font-size: 14px; font-weight: 800; "
            "background: transparent; border: none;"
        )

        time = QLabel(f"◷ {event.time_range}")
        time.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent; border: none;"
        )
        jump = QLabel("跳转回放 ▶")
        jump.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        jump.setStyleSheet(
            "color: #2563EB; font-size: 12px; font-weight: 800; "
            "background: transparent; border: none;"
        )
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.addWidget(time)
        action_row.addStretch()
        action_row.addWidget(jump)

        tag_text = "  ".join(f"#{tag}" for tag in event.tags)
        tags = QLabel(tag_text)
        tags.setWordWrap(True)
        tags.setStyleSheet(
            "color: #2563EB; font-size: 11px; font-weight: 700; "
            "background: transparent; border: none;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 14, 16, 14)
        layout.setSpacing(12)
        layout.addWidget(self.color_bar)

        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(8)
        body.addLayout(meta_row)
        body.addWidget(title)
        body.addLayout(action_row)
        if tag_text:
            body.addWidget(tags)
        layout.addLayout(body, 1)

        self._apply_style()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 关键：event 字段必须最后赋值，避免 PySide6 构造期 segfault
        self.event = event

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style()

    def _apply_style(self, hover: bool = False) -> None:
        if self._selected:
            bg = "#EFF6FF"
            bar = "#2563EB"
        elif hover:
            bg = "#F8FAFC"
            bar = "#E2E8F0"
        else:
            bg = "#FFFFFF"
            bar = "transparent"
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border-radius: 0px; border: none; }}"
        )
        self.color_bar.setStyleSheet(
            f"QFrame {{ background: {bar}; border-radius: 0px; border: none; }}"
        )

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._apply_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._apply_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.event)
        super().mousePressEvent(event)
