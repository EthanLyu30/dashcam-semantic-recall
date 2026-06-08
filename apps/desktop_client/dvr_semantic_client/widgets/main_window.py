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
        self.detail.set_dark(True)
        self.query_id_label = QLabel("QueryID: -")
        self.stack = QStackedWidget()
        self.nav_buttons: list[QPushButton] = []

        self.search_panel.search_requested.connect(self.run_search)
        self.search_panel.event_selected.connect(self.select_event)
        self.timeline.event_selected.connect(self.select_event)
        self.timeline.seek_requested.connect(self.player.seek)
        self.detail.export_requested.connect(self.export_event)
        self.player.seek_requested.connect(self.timeline.set_current_second)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        self._build_pages()
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)
        self._load_initial_state()

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setProperty("role", "appHeader")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(96, 12, 96, 12)
        layout.setSpacing(18)

        # 左：品牌 logo 块（程序绘制的放大镜 logo + 文字标题）
        from .branding import make_logo_pixmap

        logo_chip = QLabel()
        logo_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_chip.setFixedSize(38, 38)
        logo_chip.setPixmap(make_logo_pixmap(38))
        logo_chip.setScaledContents(True)

        brand_name = QLabel("DVR-S")
        brand_name.setStyleSheet(
            "QLabel { color: #0F172A; font-size: 17px; font-weight: 800; "
            "letter-spacing: 0.2px; }"
        )
        brand_subtitle = QLabel("Semantic Recall")
        brand_subtitle.setStyleSheet("color: #94A3B8; font-size: 10px;")
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

        secondary_labels = ["模型配置", "权限"]
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
        logout_btn.setToolTip("退出登录")
        logout_btn.clicked.connect(self._on_logout)

        layout.addSpacing(4)
        layout.addWidget(settings_btn)
        layout.addWidget(user_btn)
        layout.addWidget(logout_btn)
        return frame

    def _build_pages(self) -> None:
        self.stack.addWidget(overview_page(self.api_client))
        self.stack.addWidget(self._build_search_workspace())
        self.stack.addWidget(video_library_page(self.api_client))
        self.stack.addWidget(review_page(self.api_client))
        self.stack.addWidget(alerts_page(self.api_client))
        self.stack.addWidget(accidents_page(self.api_client))
        self.stack.addWidget(evidence_page())
        self.stack.addWidget(daily_report_page(self.api_client))
        self.stack.addWidget(settings_page(self.api_client))
        self.stack.addWidget(roles_page(self.api_client))
        self.stack.addWidget(login_page())
        self.show_page(1)

    def _build_search_workspace(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(96, 30, 96, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setProperty("role", "searchHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(32, 18, 32, 18)
        page_title = QLabel("多模态语义检索")
        page_title.setStyleSheet(
            "color: #0F172A; font-size: 22px; font-weight: 800; "
            "background: transparent; border: none;"
        )
        self.query_id_label.setStyleSheet(
            "color: #64748B; font-size: 11px; font-family: Consolas, monospace; "
            "background: transparent; border: none;"
        )
        header_layout.addWidget(page_title)
        header_layout.addStretch()
        header_layout.addWidget(self.query_id_label)
        layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("searchSplitter")
        splitter.setHandleWidth(0)
        splitter.addWidget(self.search_panel)

        right_panel = QFrame()
        right_panel.setProperty("role", "searchRight")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(24, 24, 24, 24)
        right_layout.setSpacing(18)
        right_layout.addWidget(self.player, 3)
        self.detail.setMaximumHeight(200)
        right_layout.addWidget(self.detail, 1)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)
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

        # Refresh search panel video dropdown when entering the search page
        if index == 1:
            try:
                self.videos = self.api_client.list_videos()
                self.search_panel.set_videos(self.videos)
            except Exception:
                pass

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
        self.query_id_label.setText(f"QueryID: {response.query_id or '-'}")
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

    def _on_logout(self) -> None:
        name = getattr(self.login_ctx, "display_name", "") or getattr(self.login_ctx, "username", "演示用户")
        reply = QMessageBox.question(
            self,
            "退出登录",
            f"确定要退出当前账号吗？\n当前用户：{name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
