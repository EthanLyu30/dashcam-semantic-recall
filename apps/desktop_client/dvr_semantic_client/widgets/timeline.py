from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..models import SemanticEvent, VideoRecord, format_time


class EventTimeline(QWidget):
    event_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(112)
        self._video: VideoRecord | None = None
        self._events: tuple[SemanticEvent, ...] = ()
        self._selected_id = ""
        self._current_sec = 0
        self._dark = False

    def set_dark(self, dark: bool) -> None:
        """嵌到视频卡片底部时切到深色 palette。"""
        self._dark = dark
        self.update()

    def set_video(self, video: VideoRecord) -> None:
        self._video = video
        self._current_sec = 0
        self.update()

    def set_events(self, events: tuple[SemanticEvent, ...]) -> None:
        self._events = events
        self.update()

    def select_event(self, event: SemanticEvent) -> None:
        self._selected_id = event.id
        self._current_sec = event.start_sec
        self.update()

    def set_current_second(self, seconds: int) -> None:
        self._current_sec = seconds
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor("#0F172A") if self._dark else QColor("#FFFFFF")
        rail_bg = QColor("#1E293B") if self._dark else QColor("#E2E8F0")
        tick_color = QColor("#475569") if self._dark else QColor("#CBD5E1")
        label_color = QColor("#94A3B8") if self._dark else QColor("#64748B")
        empty_color = QColor("#94A3B8") if self._dark else QColor("#64748B")
        painter.fillRect(self.rect(), bg)

        margin = 18
        rail_y = self.height() // 2
        rail_rect = QRectF(margin, rail_y - 7, self.width() - margin * 2, 14)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(rail_bg)
        painter.drawRoundedRect(rail_rect, 7, 7)

        if self._video is None or self._video.duration_sec <= 0:
            painter.setPen(empty_color)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "暂未加载视频")
            return

        duration = self._video.duration_sec

        # 主刻度：起点 / 终点 + 中间 3 个等分刻度
        tick_count = 4  # 切成 4 段，得 5 个刻度
        usable = max(1, self.width() - margin * 2)
        for i in range(tick_count + 1):
            ratio = i / tick_count
            tick_sec = int(duration * ratio)
            tick_x = margin + usable * ratio
            painter.setPen(tick_color)
            painter.drawLine(int(tick_x), rail_y + 12, int(tick_x), rail_y + 18)
            painter.setPen(label_color)
            label = format_time(tick_sec)
            metrics = painter.fontMetrics()
            text_width = metrics.horizontalAdvance(label)
            text_x = tick_x - text_width / 2
            text_x = max(margin - 4, min(self.width() - margin - text_width + 4, text_x))
            painter.drawText(int(text_x), rail_y + 34, label)

        for event in self._events:
            start_x = self._x_for_second(event.start_sec, margin, duration)
            end_x = self._x_for_second(event.end_sec, margin, duration)
            width = max(8.0, end_x - start_x)
            color = QColor("#F59E0B")
            if event.confidence >= 0.88:
                color = QColor("#22C55E")
            elif event.review_status == "reviewing":
                color = QColor("#EF4444")
            if event.id == self._selected_id:
                painter.setPen(QPen(QColor("#2563EB"), 2))
                painter.setBrush(color)
                painter.drawRoundedRect(QRectF(start_x, rail_y - 16, width, 32), 6, 6)
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(QRectF(start_x, rail_y - 12, width, 24), 5, 5)

        current_x = self._x_for_second(self._current_sec, margin, duration)
        painter.setPen(QPen(QColor("#2563EB"), 2))
        painter.drawLine(int(current_x), rail_y - 30, int(current_x), rail_y + 30)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if self._video is None:
            return
        clicked_sec = self._second_for_x(event.position().x(), 18, self._video.duration_sec)
        nearest = None
        nearest_distance = 999999
        for semantic_event in self._events:
            if semantic_event.start_sec <= clicked_sec <= semantic_event.end_sec:
                nearest = semantic_event
                nearest_distance = 0
                break
            distance = min(
                abs(clicked_sec - semantic_event.start_sec),
                abs(clicked_sec - semantic_event.end_sec),
            )
            if distance < nearest_distance:
                nearest = semantic_event
                nearest_distance = distance
        if nearest is not None and nearest_distance <= max(20, self._video.duration_sec // 20):
            self.event_selected.emit(nearest)

    def _x_for_second(self, second: int, margin: int, duration: int) -> float:
        usable = max(1, self.width() - margin * 2)
        return margin + usable * (max(0, min(second, duration)) / duration)

    def _second_for_x(self, x: float, margin: int, duration: int) -> int:
        usable = max(1, self.width() - margin * 2)
        ratio = max(0.0, min(1.0, (x - margin) / usable))
        return int(duration * ratio)
