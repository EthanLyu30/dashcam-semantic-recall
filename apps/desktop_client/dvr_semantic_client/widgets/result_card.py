from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..models import SemanticEvent


class ResultCard(QFrame):
    selected = Signal(object)

    def __init__(self, event: SemanticEvent, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.event = event
        self.setObjectName("resultCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "#resultCard { background: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 14px; }"
            "#resultCard:hover { border-color: #2563EB; background: #EFF6FF; }"
        )

        title = QLabel(event.title)
        title.setStyleSheet("font-size: 15px; font-weight: 700;")
        time_label = QLabel(event.time_range)
        time_label.setProperty("role", "muted")

        confidence = QLabel(event.confidence_percent)
        confidence.setAlignment(Qt.AlignmentFlag.AlignCenter)
        confidence.setFixedWidth(54)
        confidence.setStyleSheet(self._confidence_style(event.confidence))

        summary = QLabel(event.summary)
        summary.setWordWrap(True)
        summary.setProperty("role", "muted")

        tags = QLabel("  ".join(f"#{tag}" for tag in event.tags))
        tags.setStyleSheet("color: #2563EB; font-size: 12px;")

        seek_button = QPushButton("Seek")
        seek_button.setProperty("variant", "primary")
        seek_button.clicked.connect(lambda: self.selected.emit(self.event))

        top = QHBoxLayout()
        top.addWidget(title, 1)
        top.addWidget(confidence)

        bottom = QHBoxLayout()
        bottom.addWidget(time_label)
        bottom.addStretch()
        bottom.addWidget(seek_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(top)
        layout.addWidget(summary)
        layout.addWidget(tags)
        layout.addLayout(bottom)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.event)
        super().mousePressEvent(event)

    def _confidence_style(self, confidence: float) -> str:
        if confidence >= 0.85:
            color = "#63D471"
        elif confidence >= 0.78:
            color = "#F59E0B"
        else:
            color = "#EF4444"
        return (
            f"color: {color}; border: 1px solid {color}; border-radius: 5px; "
            "padding: 4px; font-weight: 700;"
        )
