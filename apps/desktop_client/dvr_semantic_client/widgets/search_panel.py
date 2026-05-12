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
        self.setObjectName("semanticSearchPanel")
        self._videos: tuple[VideoRecord, ...] = ()
        self._cards: dict[str, ResultCard] = {}

        title = QLabel("多模态语义检索")
        title.setProperty("role", "panelTitle")
        subtitle = QLabel("输入自然语言描述 (多模态检索)")
        subtitle.setStyleSheet(
            "color: #64748B; font-size: 11px; font-weight: 800; "
            "letter-spacing: 1px; background: transparent; border: none;"
        )

        self.video_select = QComboBox()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("例如：查找3月27日下午14点左右，路口发生白色SUV剐蹭的画面")
        self.query_input.returnPressed.connect(self._emit_search)

        search_button = QPushButton("检索")
        search_button.setProperty("variant", "primary")
        search_button.clicked.connect(self._emit_search)

        query_row = QHBoxLayout()
        query_row.addWidget(self.query_input, 1)
        query_row.addWidget(search_button)

        # 推荐查询芯片：用短标签 + tooltip 显示完整文本，避免横向截断
        suggestion_shortcuts: tuple[tuple[str, str, str, str], ...] = (
            ("# 白色SUV", SUGGESTED_QUERIES[0] if len(SUGGESTED_QUERIES) > 0 else "剐蹭", "#EFF6FF", "#2563EB"),
            ("# 剐蹭事故", SUGGESTED_QUERIES[0] if len(SUGGESTED_QUERIES) > 0 else "剐蹭", "#FEF2F2", "#DC2626"),
            ("# 十字路口", "十字路口发生碰撞或侧切的片段", "#F1F5F9", "#475569"),
            ("# 晴天", "晴天白天道路场景中的异常事件", "#F0FDF4", "#16A34A"),
        )
        self.suggested_layout = QHBoxLayout()
        self.suggested_layout.setSpacing(8)
        for short, full, bg, fg in suggestion_shortcuts:
            button = QPushButton(short)
            button.setToolTip(full)
            button.setStyleSheet(
                f"QPushButton {{ background: {bg}; color: {fg}; border: none; "
                "border-radius: 4px; padding: 5px 9px; font-size: 11px; "
                "font-weight: 800; }}"
                "QPushButton:hover { background: #DBEAFE; color: #1D4ED8; }"
            )
            button.clicked.connect(
                lambda _checked=False, text=full: self._use_suggestion(text)
            )
            self.suggested_layout.addWidget(button)
        self.suggested_layout.addStretch()

        self.status = QLabel("命中片段 (置信度降序)")
        self.status.setStyleSheet(
            "QLabel { background: #F8FAFC; color: #94A3B8; font-size: 10px; "
            "font-weight: 800; padding: 10px 14px; letter-spacing: 0.5px; "
            "border: none; }"
        )

        self.result_container = QWidget()
        self.result_layout = QVBoxLayout(self.result_container)
        self.result_layout.setContentsMargins(0, 0, 0, 0)
        self.result_layout.setSpacing(10)
        self.result_layout.addStretch()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.result_container)
        self.scroll.setMinimumWidth(430)
        self.scroll.setStyleSheet(
            "QScrollArea { background: #FFFFFF; border: none; }"
            "QWidget { background: #FFFFFF; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        search_box = QWidget()
        search_box.setStyleSheet("QWidget { background: #FFFFFF; }")
        search_layout = QVBoxLayout(search_box)
        search_layout.setContentsMargins(24, 22, 24, 22)
        search_layout.setSpacing(12)
        search_layout.addWidget(title)
        search_layout.addWidget(subtitle)
        search_layout.addWidget(self.video_select)
        search_layout.addLayout(query_row)
        search_layout.addLayout(self.suggested_layout)
        layout.addWidget(search_box)
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
        self._cards = {}
        elapsed = f"{response.elapsed_ms} ms" if response.elapsed_ms else "-"
        self.status.setText(
            f"命中片段 {len(response.results)} 条 · 耗时 {elapsed} · 置信度降序"
        )
        for event in response.results:
            card = ResultCard(event)
            card.selected.connect(self.event_selected.emit)
            self._cards[event.id] = card
            self.result_layout.insertWidget(self.result_layout.count() - 1, card)

    def select_event(self, event: SemanticEvent) -> None:
        for event_id, card in self._cards.items():
            card.set_selected(event_id == event.id)

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
