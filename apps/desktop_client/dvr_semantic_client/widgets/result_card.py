from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
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
            bar_color = "#16A34A"
            conf_css = "color:#16A34A;"
        elif event.confidence >= 0.78:
            bar_color = "#F59E0B"
            conf_css = "color:#F59E0B;"
        else:
            bar_color = "#EF4444"
            conf_css = "color:#EF4444;"

        # 外层卡片：左侧 4px 竖线 + 圆角（对齐原型 border-l-4 效果）
        # Qt 里用 "border-left: Npx solid color; border-radius: 8px" 不太可靠，
        # 改为在 HBox 里加一个 4px 宽的 QFrame 色条代替。
        color_bar = QFrame()
        color_bar.setFixedWidth(4)
        color_bar.setMinimumHeight(60)
        color_bar.setStyleSheet(
            f"QFrame {{ background: {bar_color}; border-radius: 2px; border: none; }}"
        )

        # 右侧内容区
        relevance = event.similarity_percent if event.similarity_score > 0 else "—"
        body_html = (
            f"<div style='margin-bottom:2px;'>"
            f"<span style='{conf_css}font-size:10pt;font-weight:800;'>"
            f"命中率 {event.confidence_percent}</span>"
            f"&nbsp;&nbsp;<span style='color:#94A3B8;font-size:9pt;'>{event.id[:10]}</span>"
            f"</div>"
            f"<div style='color:#1E293B;font-size:12pt;font-weight:700;margin-bottom:4px;'>"
            f"{event.title}</div>"
            f"<div style='color:#64748B;font-size:10pt;'>"
            f"⏱ {event.time_range}</div>"
            f"<div style='color:#2563EB;font-size:10pt;margin-top:4px;font-weight:600;'>"
            f"{'  '.join('#' + t for t in event.tags) or ''}</div>"
        )
        body_label = QLabel(body_html)
        body_label.setTextFormat(Qt.TextFormat.RichText)
        body_label.setWordWrap(True)
        body_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        body_label.setStyleSheet("QLabel { background: transparent; border: none; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 14, 10)
        layout.setSpacing(12)
        layout.addWidget(color_bar)
        layout.addWidget(body_label, 1)

        self._bar_color = bar_color
        self._default_bg = "background: #FFFFFF; border-radius: 8px; border: none;"
        self._hover_bg = "background: #EFF6FF; border-radius: 8px; border: none;"
        self.setStyleSheet(f"QFrame {{ {self._default_bg} }}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 关键：event 字段必须最后赋值，避免 PySide6 构造期 segfault
        self.event = event

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self.setStyleSheet(f"QFrame {{ {self._hover_bg} }}")
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self.setStyleSheet(f"QFrame {{ {self._default_bg} }}")
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.event)
        super().mousePressEvent(event)
