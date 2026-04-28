from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..api import ApiClient
from ..models import SemanticEvent, VideoRecord
from .event_detail import EventDetailPanel
from .pages import (
    accidents_page,
    alerts_page,
    daily_report_page,
    evidence_page,
    login_page,
    overview_page,
    review_page,
    roles_page,
    settings_page,
    video_library_page,
)
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
        self.stack = QStackedWidget()
        self.nav_buttons: list[QPushButton] = []

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
        self._build_pages()
        root.addWidget(self.stack, 1)

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
        text_stack = QVBoxLayout()
        text_stack.addWidget(title)
        text_stack.addWidget(subtitle)

        state = QLabel("Qt6 复现原型 · 当前数据源：mock")
        state.setStyleSheet(
            "color: #2563EB; background: #EFF6FF; border: 1px solid #BFDBFE; "
            "border-radius: 12px; padding: 8px 12px;"
        )

        layout.addLayout(text_stack, 1)
        for index, label in enumerate(
            ["概览", "检索", "视频流", "复核", "告警", "事故", "证据与日志", "全天业务报告"]
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, idx=index: self.show_page(idx))
            self.nav_buttons.append(button)
            layout.addWidget(button)
        for offset, label in enumerate(["模型配置", "权限", "登录"], start=8):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, idx=offset: self.show_page(idx))
            self.nav_buttons.append(button)
            layout.addWidget(button)
        layout.addWidget(state)
        return frame

    def _build_pages(self) -> None:
        self.stack.addWidget(overview_page())
        self.stack.addWidget(self._build_search_workspace())
        self.stack.addWidget(video_library_page())
        self.stack.addWidget(review_page())
        self.stack.addWidget(alerts_page())
        self.stack.addWidget(accidents_page())
        self.stack.addWidget(evidence_page())
        self.stack.addWidget(daily_report_page())
        self.stack.addWidget(settings_page())
        self.stack.addWidget(roles_page())
        self.stack.addWidget(login_page())
        self.show_page(1)

    def _build_search_workspace(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.search_panel)
        splitter.addWidget(self.player)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

        bottom = QSplitter(Qt.Orientation.Horizontal)
        bottom.addWidget(self._wrap_timeline())
        bottom.addWidget(self.detail)
        bottom.setStretchFactor(0, 3)
        bottom.setStretchFactor(1, 2)
        bottom.setMaximumHeight(230)
        layout.addWidget(bottom)
        return page

    def show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            active = button_index == index
            button.setProperty("variant", "primary" if active else "")
            button.style().unpolish(button)
            button.style().polish(button)
        names = ["概览", "检索", "视频流", "复核", "告警", "事故", "证据与日志", "全天业务报告", "模型配置", "权限", "登录"]
        if 0 <= index < len(names):
            self.statusBar().showMessage(f"当前页面：{names[index]}")

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
