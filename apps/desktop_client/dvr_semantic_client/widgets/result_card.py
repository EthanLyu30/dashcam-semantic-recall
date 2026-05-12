from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
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
        # 颜色策略：高=绿（≥0.85）/ 中=黄（≥0.78）/ 低=红
        if event.confidence >= 0.85:
            color = "#16A34A"
            bg, border = "rgba(22, 163, 74, 0.10)", "rgba(22, 163, 74, 0.40)"
        elif event.confidence >= 0.78:
            color = "#F59E0B"
            bg, border = "rgba(245, 158, 11, 0.12)", "rgba(245, 158, 11, 0.40)"
        else:
            color = "#EF4444"
            bg, border = "rgba(239, 68, 68, 0.10)", "rgba(239, 68, 68, 0.40)"

        # 左侧：大号置信度色块（百分比 + 文字标识）
        score_label = QLabel(
            f"<div align='center' style='line-height:1.05;'>"
            f"<span style='color:{color};font-size:22pt;font-weight:800;'>"
            f"{event.confidence_percent}</span><br>"
            f"<span style='color:#64748B;font-size:10pt;'>置信度</span></div>"
        )
        score_label.setTextFormat(Qt.TextFormat.RichText)
        score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_label.setFixedWidth(80)
        score_label.setStyleSheet(
            f"QLabel {{ background: {bg}; border: 1px solid {border}; "
            "border-radius: 10px; padding: 8px 4px; }}"
        )

        # 右侧：标题 + 元信息 + 摘要 + tags（用一个 rich-text Label 承载）
        relevance = event.similarity_percent if event.similarity_score > 0 else "—"
        body_html = (
            f"<div style='color:#1E293B;font-size:14pt;font-weight:700;'>"
            f"{event.title}</div>"
            f"<div style='color:#64748B;font-size:11pt;margin-top:3px;'>"
            f"{event.time_range}  ·  相关度 {relevance}</div>"
            f"<div style='color:#334155;font-size:11pt;margin-top:6px;'>"
            f"{event.summary or '（无摘要）'}</div>"
            f"<div style='color:#2563EB;font-size:11pt;margin-top:6px;'>"
            f"{'  '.join('#' + t for t in event.tags) or ''}</div>"
        )
        body_label = QLabel(body_html)
        body_label.setTextFormat(Qt.TextFormat.RichText)
        body_label.setWordWrap(True)
        body_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # 左右横向布局，赋给外层 QFrame
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(14)
        layout.addWidget(score_label, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(body_label, 1)

        # Hover shadow effect — 用 QGraphicsDropShadowEffect 模拟 hover 浮起
        # enterEvent 激活阴影，leaveEvent 移除，替代 CSS transition。
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 2)
        self._shadow.setColor(QColor(0, 0, 0, 0))
        self.setGraphicsEffect(self._shadow)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 关键：event 字段必须最后赋值，避免 PySide6 构造期 segfault
        self.event = event

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._shadow.setBlurRadius(16)
        self._shadow.setColor(QColor(0, 0, 0, 40))
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._shadow.setBlurRadius(0)
        self._shadow.setColor(QColor(0, 0, 0, 0))
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.event)
        super().mousePressEvent(event)
