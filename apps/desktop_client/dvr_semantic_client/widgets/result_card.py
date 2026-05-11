from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from ..models import SemanticEvent


class ResultCard(QFrame):
    """Search-result card — must mirror the CaptureCard pattern exactly.

    Any deviation (e.g. `setStyleSheet` on self, `QLabel(html, self)`,
    `<table>` in the HTML) has been observed to crash during construction
    on Windows / Python 3.11 / PySide6 6.x. Keep this minimal.
    """

    selected = Signal(object)

    def __init__(self, event, parent=None):  # type: ignore[no-untyped-def]
        super().__init__(parent)
        if event.confidence >= 0.85:
            color = "#22C55E"
        elif event.confidence >= 0.78:
            color = "#F59E0B"
        else:
            color = "#EF4444"
        relevance = event.similarity_percent if event.similarity_score else "-"
        html = (
            f"<div><b style='font-size:14pt;color:#1E293B;'>{event.title}</b>"
            f" &nbsp; <span style='color:{color};font-weight:700;"
            f"border:1px solid {color};border-radius:5px;padding:1px 8px;'>"
            f"{event.confidence_percent}</span>"
            f"<br><span style='color:#64748B;'>{event.time_range}  ·  "
            f"相关度 {relevance}</span>"
            f"<br><span style='color:#334155;'>{event.summary}</span>"
            f"<br><span style='color:#2563EB;'>"
            f"{'  '.join('#' + t for t in event.tags)}</span></div>"
        )
        l = QLabel(html)
        l.setTextFormat(Qt.TextFormat.RichText)
        l.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(l)
        # store event AFTER layout is built (some PySide6 internal state
        # is sensitive to attribute assignment during __init__)
        self.event = event

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.event)
        super().mousePressEvent(event)
