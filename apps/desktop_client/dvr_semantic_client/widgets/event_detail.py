from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..models import SemanticEvent


class EventDetailPanel(QFrame):
    export_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "panel")
        self._event: SemanticEvent | None = None

        self.title = QLabel("Selected Event")
        self.title.setProperty("role", "panelTitle")
        self.time_label = QLabel("No event selected")
        self.time_label.setProperty("role", "muted")
        self.summary = QLabel("Click a search result to inspect timestamps, tags, confidence, and export actions.")
        self.summary.setWordWrap(True)
        self.summary.setProperty("role", "muted")
        self.tags = QLabel("")
        self.tags.setStyleSheet("color: #42D9F5;")
        self.confidence = QLabel("")
        self.confidence.setProperty("role", "muted")

        self.export_button = QPushButton("Export Evidence")
        self.export_button.setProperty("variant", "evidence")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._emit_export)

        header = QHBoxLayout()
        header.addWidget(self.title, 1)
        header.addWidget(self.export_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self.time_label)
        layout.addWidget(self.summary)
        layout.addWidget(self.tags)
        layout.addWidget(self.confidence)
        layout.addStretch()

    def set_event(self, event: SemanticEvent) -> None:
        self._event = event
        self.title.setText(event.title)
        self.time_label.setText(f"{event.time_range} · {event.event_type}")
        self.summary.setText(event.summary)
        self.tags.setText("  ".join(f"#{tag}" for tag in event.tags))
        self.confidence.setText(
            f"confidence {event.confidence_percent} · relevance {event.similarity_percent} · review {event.review_status}"
        )
        self.export_button.setEnabled(True)

    def _emit_export(self) -> None:
        if self._event is not None:
            self.export_requested.emit(self._event)
