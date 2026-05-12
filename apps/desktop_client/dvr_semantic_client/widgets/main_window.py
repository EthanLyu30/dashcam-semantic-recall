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

from ..api import ApiClient, RestApiClient
from ..models import SemanticEvent, VideoRecord
from .event_detail import EventDetailPanel
from .login_dialog import LoginContext
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
    def __init__(
        self,
        api_client: ApiClient,
        login_ctx: LoginContext | None = None,
        base_url: str = "",
    ) -> None:
        super().__init__()
        self.api_client = api_client
        self.login_ctx = login_ctx
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.videos: tuple[VideoRecord, ...] = ()
        self.current_events: tuple[SemanticEvent, ...] = ()

        self.setWindowTitle("Dashcam Semantic Recall")
        self.setStatusBar(QStatusBar())

        self.player = VideoPlayerPanel()
        self.search_panel = SearchPanel()
        self.timeline = EventTimeline()
        self.player.attach_timeline(self.timeline)
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
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(18)
        root.addWidget(self._build_header())
        self._build_pages()
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)
        self._load_initial_state()

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setProperty("role", "panel")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(26, 16, 22, 16)
        layout.setSpacing(18)

        # 左：品牌 logo 块（圆角彩色方块 + 文字标题）
        logo_chip = QLabel("DVR")
        logo_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_chip.setFixedSize(38, 38)
        logo_chip.setStyleSheet(
            "QLabel { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #4F46E5, stop:1 #2563EB); color: #FFFFFF; "
            "border-radius: 10px; font-weight: 800; font-size: 11px; "
            "letter-spacing: 0.5px; }"
        )

        brand_name = QLabel("DVR-Semantic")
        brand_name.setStyleSheet(
            "QLabel { color: #0F172A; font-size: 17px; font-weight: 800; "
            "letter-spacing: 0.2px; }"
        )
        brand_subtitle = QLabel("行车记录仪视频语义检索与精准回放")
        brand_subtitle.setStyleSheet("color: #64748B; font-size: 11px;")
        brand_text = QVBoxLayout()
        brand_text.setContentsMargins(0, 0, 0, 0)
        brand_text.setSpacing(1)
        brand_text.addWidget(brand_name)
        brand_text.addWidget(brand_subtitle)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(10)
        brand_row.addWidget(logo_chip)
        brand_row.addLayout(brand_text)
        brand_container = QWidget()
        brand_container.setLayout(brand_row)

        layout.addWidget(brand_container)
        layout.addSpacing(12)

        # 中：导航（flat nav 风格，由 theme.qss 控制 variant=nav / nav-active）
        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(0, 0, 0, 0)
        nav_row.setSpacing(2)

        primary_labels = ["概览", "检索", "视频流", "复核", "告警", "事故", "证据与日志", "全天业务报告"]
        for index, label in enumerate(primary_labels):
            button = QPushButton(label)
            button.setProperty("variant", "nav")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, idx=index: self.show_page(idx))
            self.nav_buttons.append(button)
            nav_row.addWidget(button)

        # 视觉分隔（细竖线）
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("color: #E2E8F0;")
        separator.setFixedHeight(18)
        nav_row.addSpacing(8)
        nav_row.addWidget(separator)
        nav_row.addSpacing(8)

        secondary_labels = ["模型配置", "权限", "登录"]
        for offset, label in enumerate(secondary_labels, start=8):
            button = QPushButton(label)
            button.setProperty("variant", "nav")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, idx=offset: self.show_page(idx))
            self.nav_buttons.append(button)
            nav_row.addWidget(button)

        layout.addLayout(nav_row, 1)

        # 右：设置 / 用户 / 注销 三个图标圆按钮（对齐原型右上角）
        icon_btn_qss = (
            "QPushButton { background: transparent; border: none; border-radius: 20px; "
            "color: #64748B; font-size: 16px; min-width: 36px; min-height: 36px; "
            "max-width: 36px; max-height: 36px; padding: 0; }"
            "QPushButton:hover { background: #F1F5F9; color: #2563EB; }"
        )
        settings_btn = QPushButton("⚙")
        settings_btn.setStyleSheet(icon_btn_qss)
        settings_btn.setToolTip("模型与安全配置")
        settings_btn.clicked.connect(lambda: self.show_page(8))

        user_btn = QPushButton("👤")
        user_btn.setStyleSheet(icon_btn_qss)
        user_btn.setToolTip("角色与权限管理")
        user_btn.clicked.connect(lambda: self.show_page(9))

        logout_btn = QPushButton("⏻")
        logout_btn.setStyleSheet(
            icon_btn_qss.replace("color: #64748B", "color: #94A3B8")
            + "QPushButton:hover { background: #FEF2F2; color: #EF4444; }"
        )
        logout_btn.setToolTip("登录 / 注销")
        logout_btn.clicked.connect(lambda: self.show_page(10))

        layout.addSpacing(4)
        layout.addWidget(settings_btn)
        layout.addWidget(user_btn)
        layout.addWidget(logout_btn)
        return frame

    def _build_pages(self) -> None:
        self.stack.addWidget(overview_page())
        self.stack.addWidget(self._build_search_workspace())
        self.stack.addWidget(video_library_page(self.api_client))
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
        layout.setSpacing(16)

        # 上：检索结果 | 视频回放（时间轴已经在 player 内部）
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(16)
        splitter.addWidget(self.search_panel)
        splitter.addWidget(self.player)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 3)

        # 下：事件详情独占一行
        self.detail.setMaximumHeight(320)
        layout.addWidget(self.detail, 1)
        return page

    def show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            variant = "nav-active" if button_index == index else "nav"
            button.setProperty("variant", variant)
            button.style().unpolish(button)
            button.style().polish(button)
        names = ["概览", "检索", "视频流", "复核", "告警", "事故", "证据与日志", "全天业务报告", "模型配置", "权限", "登录"]
        if 0 <= index < len(names):
            self.statusBar().showMessage(f"当前页面：{names[index]}")

    def _load_video_into_player(self, video: VideoRecord) -> None:
        """Hand the video to the player, using the streaming URL if available."""
        if isinstance(self.api_client, RestApiClient) and video.id:
            url = self.api_client.stream_url(video.id)
            self.player.load_video_url(url, video.duration_sec, video.title)
        else:
            self.player.load_video(video)

    def _load_initial_state(self) -> None:
        try:
            self.videos = self.api_client.list_videos()
        except Exception as exc:  # pragma: no cover - manual UI recovery
            QMessageBox.warning(self, "API error", f"Failed to load videos:\n{exc}")
            self.videos = ()

        self.search_panel.set_videos(self.videos)
        if self.videos:
            self._load_video_into_player(self.videos[0])
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
            self._load_video_into_player(selected_video)
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
