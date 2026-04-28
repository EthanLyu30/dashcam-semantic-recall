from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..api import ApiClient
from ..models import SemanticEvent, VideoRecord
from .event_detail import EventDetailPanel
from .search_panel import SearchPanel
from .timeline import EventTimeline
from .video_player import VideoPlayerPanel


class MainWindow(QMainWindow):
    def __init__(self, api_client: ApiClient) -> None:
        super().__init__()
        self.api_client = api_client
        self.videos: tuple[VideoRecord, ...] = ()
        self.current_events: tuple[SemanticEvent, ...] = ()

        self.setWindowTitle("Dashcam Semantic Recall")
        self.setStatusBar(QStatusBar())

        self.player = VideoPlayerPanel()
        self.search_panel = SearchPanel()
        self.timeline = EventTimeline()
        self.detail = EventDetailPanel()

        self.search_panel.search_requested.connect(self.run_search)
        self.search_panel.event_selected.connect(self.select_event)
        self.timeline.event_selected.connect(self.select_event)
        self.detail.export_requested.connect(self.export_event)
        self.player.seek_requested.connect(self.timeline.set_current_second)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)
        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.player)
        splitter.addWidget(self.search_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, 1)

        bottom = QSplitter(Qt.Orientation.Horizontal)
        bottom.addWidget(self._wrap_timeline())
        bottom.addWidget(self.detail)
        bottom.setStretchFactor(0, 3)
        bottom.setStretchFactor(1, 2)
        bottom.setMaximumHeight(230)
        root.addWidget(bottom)

        self.setCentralWidget(central)
        self._load_initial_state()

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setProperty("role", "panel")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("DVR-S")
        title.setProperty("role", "title")
        subtitle = QLabel("多模态行车记录仪视频语义检索与精准回放")
        subtitle.setProperty("role", "muted")
        nav = QLabel("概览   检索   视频流   复核   告警   事故   证据与日志   全天业务报告")
        nav.setStyleSheet("color: #2563EB; font-weight: 650;")

        text_stack = QVBoxLayout()
        text_stack.addWidget(title)
        text_stack.addWidget(subtitle)
        text_stack.addWidget(nav)

        state = QLabel("原型搬运中 · 当前页：语义检索中心")
        state.setStyleSheet(
            "color: #2563EB; background: #EFF6FF; border: 1px solid #BFDBFE; "
            "border-radius: 12px; padding: 8px 12px;"
        )

        layout.addLayout(text_stack, 1)
        layout.addWidget(state)
        return frame

    def _wrap_timeline(self) -> QFrame:
        frame = QFrame()
        frame.setProperty("role", "panel")
        title = QLabel("Event Timeline")
        title.setProperty("role", "panelTitle")
        hint = QLabel("Click highlighted intervals to jump playback.")
        hint.setProperty("role", "muted")

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        header.addWidget(hint)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addLayout(header)
        layout.addWidget(self.timeline)
        return frame

    def _load_initial_state(self) -> None:
        try:
            self.videos = self.api_client.list_videos()
        except Exception as exc:  # pragma: no cover - manual UI recovery
            QMessageBox.warning(self, "API error", f"Failed to load videos:\n{exc}")
            self.videos = ()

        self.search_panel.set_videos(self.videos)
        if self.videos:
            self.player.load_video(self.videos[0])
            self.timeline.set_video(self.videos[0])
            self.run_search(self.videos[0].id, "帮我找出疑似剐蹭的时间段")

    def run_search(self, video_id: str, query: str) -> None:
        try:
            response = self.api_client.search(video_id, query)
        except Exception as exc:  # pragma: no cover - manual UI recovery
            QMessageBox.warning(self, "Search error", str(exc))
            return

        selected_video = next((video for video in self.videos if video.id == video_id), None)
        if selected_video is not None:
            self.player.load_video(selected_video)
            self.timeline.set_video(selected_video)

        self.current_events = response.results
        self.search_panel.set_response(response)
        self.timeline.set_events(response.results)
        self.statusBar().showMessage(f"Search completed: {len(response.results)} results")
        if response.results:
            self.select_event(response.results[0])

    def select_event(self, event: SemanticEvent) -> None:
        self.search_panel.select_event(event)
        self.detail.set_event(event)
        self.timeline.select_event(event)
        self.player.seek_to_event(event)
        self.statusBar().showMessage(f"Selected {event.title} at {event.time_range}")

    def export_event(self, event: SemanticEvent) -> None:
        try:
            response = self.api_client.export_event(event.id)
        except Exception as exc:  # pragma: no cover - manual UI recovery
            QMessageBox.warning(self, "Export error", str(exc))
            return
        QMessageBox.information(
            self,
            "Evidence export queued",
            f"{response.status}: {response.export_path}",
        )
        self.statusBar().showMessage(f"Evidence export queued for {event.id}")
