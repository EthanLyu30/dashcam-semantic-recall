from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..demo_data import SUGGESTED_QUERIES
from ..models import SearchResponse, SemanticEvent, VideoRecord
from .result_card import ResultCard


class SearchPanel(QFrame):
    search_requested = Signal(str, str)
    event_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "panel")
        self._videos: tuple[VideoRecord, ...] = ()

        title = QLabel("语义检索")
        title.setProperty("role", "panelTitle")

        self.video_select = QComboBox()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("输入自然语言问题，例如：帮我找出疑似剐蹭的时间段")
        self.query_input.returnPressed.connect(self._emit_search)

        search_button = QPushButton("搜索")
        search_button.setProperty("variant", "primary")
        search_button.clicked.connect(self._emit_search)

        query_row = QHBoxLayout()
        query_row.addWidget(self.query_input, 1)
        query_row.addWidget(search_button)

        # 推荐查询芯片：用短标签 + tooltip 显示完整文本，避免横向截断
        suggestion_shortcuts: tuple[tuple[str, str], ...] = (
            ("剐蹭", SUGGESTED_QUERIES[0] if len(SUGGESTED_QUERIES) > 0 else "剐蹭"),
            ("违停", SUGGESTED_QUERIES[1] if len(SUGGESTED_QUERIES) > 1 else "违停"),
            ("路障", SUGGESTED_QUERIES[2] if len(SUGGESTED_QUERIES) > 2 else "路障"),
            ("异常停车", SUGGESTED_QUERIES[3] if len(SUGGESTED_QUERIES) > 3 else "异常停车"),
        )
        self.suggested_layout = QHBoxLayout()
        self.suggested_layout.setSpacing(8)
        suggest_label = QLabel("推荐场景：")
        suggest_label.setStyleSheet("color: #64748B; font-size: 11px;")
        self.suggested_layout.addWidget(suggest_label)
        for short, full in suggestion_shortcuts:
            button = QPushButton(short)
            button.setToolTip(full)
            button.setStyleSheet(
                "QPushButton { background: #F1F5F9; color: #1E293B; "
                "border: 1px solid #E2E8F0; border-radius: 14px; "
                "padding: 5px 14px; font-size: 12px; }"
                "QPushButton:hover { background: #E0E7FF; "
                "border-color: #6366F1; color: #4338CA; }"
            )
            button.clicked.connect(
                lambda _checked=False, text=full: self._use_suggestion(text)
            )
            self.suggested_layout.addWidget(button)
        self.suggested_layout.addStretch()

        self.status = QLabel("等待检索")
        self.status.setProperty("role", "muted")

        self.result_container = QWidget()
        self.result_layout = QVBoxLayout(self.result_container)
        self.result_layout.setContentsMargins(0, 0, 0, 0)
        self.result_layout.setSpacing(10)
        self.result_layout.addStretch()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.result_container)
        self.scroll.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(self.video_select)
        layout.addLayout(query_row)
        layout.addLayout(self.suggested_layout)
        layout.addWidget(self.status)
        layout.addWidget(self.scroll, 1)

    @property
    def selected_video_id(self) -> str:
        return str(self.video_select.currentData() or "")

    def set_videos(self, videos: tuple[VideoRecord, ...]) -> None:
        self._videos = videos
        self.video_select.clear()
        for video in videos:
            self.video_select.addItem(f"{video.title} · {video.status}", video.id)

    def set_response(self, response: SearchResponse) -> None:
        self._clear_results()
        elapsed = f"{response.elapsed_ms} ms" if response.elapsed_ms else "-"
        self.status.setText(
            f"命中 {len(response.results)} 条 · 耗时 {elapsed} · 查询「{response.query}」"
        )
        for event in response.results:
            card = ResultCard(event)
            card.selected.connect(self.event_selected.emit)
            self.result_layout.insertWidget(self.result_layout.count() - 1, card)

    def select_event(self, event: SemanticEvent) -> None:
        self.status.setText(f"已选中事件：{event.title}  ·  {event.time_range}")

    def _emit_search(self) -> None:
        query = self.query_input.text().strip()
        if query and self.selected_video_id:
            self.search_requested.emit(self.selected_video_id, query)

    def _use_suggestion(self, text: str) -> None:
        self.query_input.setText(text)
        self._emit_search()

    def _clear_results(self) -> None:
        while self.result_layout.count() > 1:
            item = self.result_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
