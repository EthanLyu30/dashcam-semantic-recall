from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..models import SemanticEvent


_REVIEW_LABELS = {
    "pending": "待复核",
    "reviewing": "复核中",
    "confirmed": "已确认",
    "rejected": "已驳回",
}


def _review_label(status: str) -> str:
    return _REVIEW_LABELS.get(status, status or "未知")


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


class _MetricBlock(QFrame):
    """持久化的 metric 色块。三个 block 只在初始化时创建一次；
    切换事件时 ``set_state(label, value, color)`` 只更新文字与颜色，
    避免 ``deleteLater()`` 的异步行为引起视觉残留。"""

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(70)
        self._dark = False
        self._label = QLabel(label)
        self._value = QLabel("—")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        layout.addWidget(self._label)
        layout.addWidget(self._value)
        self.set_state(label, "—", "#94A3B8")

    def set_dark(self, dark: bool) -> None:
        self._dark = dark
        self.set_state(self._label.text(), self._value.text(), "#94A3B8")

    def set_state(self, label: str, value: str, color: str) -> None:
        bg = _hex_to_rgba(color, 0.10)
        border = _hex_to_rgba(color, 0.40)
        if self._dark:
            bg = "rgba(30, 41, 59, 0.72)"
            border = "rgba(255, 255, 255, 0.08)"
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border: 1px solid {border}; "
            f"border-radius: 12px; }}"
            "QLabel { background: transparent; border: none; }"
        )
        self._label.setText(label)
        self._label.setStyleSheet(
            f"color: {'#94A3B8' if self._dark else '#64748B'}; "
            "font-size: 11px; font-weight: 600;"
        )
        self._value.setText(value)
        self._value.setStyleSheet(
            f"color: {color}; font-size: 20px; font-weight: 800;"
        )


class EventDetailPanel(QFrame):
    """选中事件的详情面板：标题 + 三指标块 + 摘要 + tags + 导出按钮。"""

    export_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "panel")
        self._event: SemanticEvent | None = None
        self._dark = False

        self.title = QLabel("事件详情")
        self.title.setProperty("role", "panelTitle")
        self.subtitle = QLabel("尚未选中事件")
        self.subtitle.setProperty("role", "muted")
        self.summary = QLabel("请在左侧检索结果中点击一条，查看完整时间、标签、置信度和导出操作。")
        self.summary.setWordWrap(True)
        self.summary.setProperty("role", "muted")
        self.tags = QLabel("")
        self.tags.setStyleSheet("color: #2563EB; font-size: 12px;")
        self.tags.setWordWrap(True)

        self.export_button = QPushButton("导出证据包")
        self.export_button.setProperty("variant", "evidence")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._emit_export)

        # 三个 metric 色块——只创建一次，后续调 set_state 更新
        self._metric_confidence = _MetricBlock("置信度")
        self._metric_relevance = _MetricBlock("相关度")
        self._metric_review = _MetricBlock("复核状态")
        self._metrics_container = QWidget()
        # Transparent so the dark panel shows in the gaps/rounded corners between
        # the three metric blocks (otherwise the global light bg leaks as white).
        self._metrics_container.setStyleSheet("background: transparent;")
        self._metrics_layout = QHBoxLayout(self._metrics_container)
        self._metrics_layout.setContentsMargins(0, 0, 0, 0)
        self._metrics_layout.setSpacing(8)
        self._metrics_layout.addWidget(self._metric_confidence)
        self._metrics_layout.addWidget(self._metric_relevance)
        self._metrics_layout.addWidget(self._metric_review)

        header = QHBoxLayout()
        header.addWidget(self.title, 1)
        header.addWidget(self.export_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addLayout(header)
        layout.addWidget(self.subtitle)
        layout.addWidget(self._metrics_container)
        layout.addWidget(self.summary)
        layout.addWidget(self.tags)
        layout.addStretch()
        self._apply_palette()

    def set_dark(self, dark: bool) -> None:
        self._dark = dark
        self.setProperty("role", "panel-dark-card" if dark else "panel")
        for block in (
            self._metric_confidence,
            self._metric_relevance,
            self._metric_review,
        ):
            block.set_dark(dark)
        self._apply_palette()
        if self._event is not None:
            self.set_event(self._event)

    def _apply_palette(self) -> None:
        if self._dark:
            self.setStyleSheet(
                "QFrame { background: transparent; border: none; }"
                "QLabel { background: transparent; border: none; }"
            )
            self.title.setStyleSheet(
                "color: #E2E8F0; font-size: 16px; font-weight: 800;"
            )
            self.subtitle.setStyleSheet("color: #94A3B8; font-size: 12px;")
            self.summary.setStyleSheet("color: #F8FAFC; font-size: 12px;")
            self.tags.setStyleSheet(
                "color: #93C5FD; font-size: 12px; font-weight: 700;"
            )
            self.export_button.setStyleSheet(
                "QPushButton { background: #2563EB; border: 1px solid #2563EB; "
                "color: #FFFFFF; border-radius: 9px; padding: 8px 14px; "
                "font-size: 12px; font-weight: 800; }"
                "QPushButton:hover { background: #1D4ED8; border-color: #1D4ED8; }"
                "QPushButton:disabled { background: #334155; border-color: #334155; "
                "color: #94A3B8; }"
            )
            return

        self.setStyleSheet("")
        self.title.setStyleSheet("")
        self.subtitle.setStyleSheet("")
        self.summary.setStyleSheet("")
        self.tags.setStyleSheet("color: #2563EB; font-size: 12px;")
        self.export_button.setStyleSheet("")

    def set_event(self, event: SemanticEvent) -> None:
        self._event = event
        self.title.setText(event.title)
        self.subtitle.setText(f"{event.time_range}  ·  事件类型 {event.event_type}")
        self.summary.setText(event.summary or "（无摘要）")
        self.tags.setText("  ".join(f"#{tag}" for tag in event.tags) or "（无标签）")
        self._apply_palette()

        # 置信度色：高=绿、中=黄、低=红
        if event.confidence >= 0.85:
            conf_color = "#16A34A"
        elif event.confidence >= 0.78:
            conf_color = "#F59E0B"
        else:
            conf_color = "#EF4444"
        self._metric_confidence.set_state("置信度", event.confidence_percent, conf_color)

        # 相关度色：品牌蓝（无相关度时灰）
        if event.similarity_score > 0:
            self._metric_relevance.set_state("相关度", event.similarity_percent, "#2563EB")
        else:
            self._metric_relevance.set_state("相关度", "—", "#94A3B8")

        # 复核状态色
        review_colors = {
            "confirmed": "#16A34A",
            "reviewing": "#F59E0B",
            "rejected": "#EF4444",
            "pending": "#6366F1",
        }
        review_color = review_colors.get(event.review_status, "#6366F1")
        self._metric_review.set_state(
            "复核状态", _review_label(event.review_status), review_color
        )

        self.export_button.setEnabled(True)

    def _emit_export(self) -> None:
        if self._event is not None:
            self.export_requested.emit(self._event)
