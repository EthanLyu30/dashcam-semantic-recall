from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QPolygon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from ..models import SemanticEvent, VideoRecord, format_time


class _PrototypeSurface(QLabel):
    """Clean dark video placeholder (a soft gradient + play glyph + caption).

    Deliberately draws no external screenshot — earlier builds blitted a stock
    traffic photo here, which read as a confusing "stitched screenshot".
    """

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)

    def set_scene_image(self, path: Path) -> None:  # kept for call-site compatibility
        return None

    def paintEvent(self, event) -> None:  # type: ignore[override]
        from PySide6.QtGui import QBrush, QLinearGradient

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        target = self.rect()

        grad = QLinearGradient(target.topLeft(), target.bottomRight())
        grad.setColorAt(0.0, QColor("#0B1220"))
        grad.setColorAt(1.0, QColor("#020617"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(target, 18, 18)

        center = target.center()
        painter.setBrush(QColor(255, 255, 255, 22))
        painter.drawEllipse(center, 38, 38)
        painter.setBrush(QColor(255, 255, 255, 230))
        painter.drawPolygon(QPolygon([
            center + QPoint(-10, -16),
            center + QPoint(-10, 16),
            center + QPoint(18, 0),
        ]))

        painter.setPen(QColor("#94A3B8"))
        font = QFont("Microsoft YaHei UI", 10)
        painter.setFont(font)
        caption = target.adjusted(24, center.y() + 56 - target.top(), -24, -20)
        painter.drawText(caption, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.text())

class VideoPlayerPanel(QFrame):
    """视频回放面板。

    安装了 ``python-vlc`` 与系统级 VLC 时，将 ``vlc.MediaPlayer`` 嵌入到一个
    原生 ``QFrame`` 上并真实播放视频；否则降级为静态占位提示，方便仍能演示
    选中事件后的 seek 联动行为。
    """

    seek_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "panel-dark")
        self.setStyleSheet(
            "QFrame[role='panel-dark'] { background: transparent; "
            "border: none; border-radius: 0px; }"
        )
        self._video: VideoRecord | None = None
        self._current_sec = 0
        self._duration_sec = 0
        self._playing = False
        self._vlc_instance: Any = None
        self._vlc_player: Any = None
        self._vlc_module: Any = self._probe_vlc()
        self._vlc_available = self._vlc_module is not None
        self._timeline_slot: QVBoxLayout | None = None

        # 视频画面承载面板（VLC 可以将 surface 直接绑到原生窗口）
        self.video_frame = QFrame()
        self.video_frame.setObjectName("videoSurface")
        self.video_frame.setMinimumHeight(200)
        self.video_frame.setStyleSheet(
            "#videoSurface { background: #020617; border-radius: 18px; "
            "border: 1px solid #1E293B; }"
        )
        if self._vlc_available:
            self.video_frame.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
            self.video_frame.setAttribute(
                Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True
            )

        # 占位 Label，未加载视频或 VLC 不可用时显示
        self.surface_label = _PrototypeSurface(self._placeholder_text("idle"))
        self.surface_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.surface_label.setWordWrap(True)
        self.surface_label.setStyleSheet(
            "QLabel { background: #020617; border-radius: 18px; "
            "border: 1px solid #1E293B; color: #CBD5E1; "
            "font-size: 16px; padding: 28px; line-height: 1.6; }"
        )
        # 用 QStackedLayout 在 video_frame 和占位 Label 之间切换
        self.surface_container = QWidget()
        # Transparent so the dark right-panel shows through the surface's rounded
        # corners (otherwise the global light background leaks as white corners).
        self.surface_container.setStyleSheet("background: transparent;")
        self.surface_container.setMinimumHeight(220)
        self._surface_stack = QStackedLayout(self.surface_container)
        self._surface_stack.setContentsMargins(0, 0, 0, 0)
        self._surface_stack.addWidget(self.video_frame)
        self._surface_stack.addWidget(self.surface_label)
        self._surface_stack.setCurrentWidget(self.surface_label)
        self.surface = self.surface_label  # 兼容旧引用

        self.title = QLabel("视频回放")
        self.title.setStyleSheet(
            "QLabel { color: #F8FAFC; font-size: 16px; font-weight: 800; "
            "background: transparent; }"
        )
        self.timecode = QLabel("00:00")
        self.timecode.setStyleSheet(
            "QLabel { color: #60A5FA; "
            "font-family: 'Cascadia Mono', 'Consolas', monospace; "
            "font-size: 18px; font-weight: 700; letter-spacing: 1px; "
            "background: transparent; }"
        )
        status_text = "VLC 已就绪 · 等待视频流" if self._vlc_available else "占位模式 · 点击检索结果可同步跳转"
        self.status = QLabel(status_text)
        self.status.setStyleSheet(
            "QLabel { color: #94A3B8; font-size: 12px; background: transparent; }"
        )

        dark_button_qss = (
            "QPushButton { background: #1E293B; border: 1px solid #334155; "
            "color: #E2E8F0; border-radius: 10px; padding: 6px 14px; }"
            "QPushButton:hover { background: #2563EB; border-color: #2563EB; "
            "color: #FFFFFF; }"
            "QPushButton:pressed { background: #1D4ED8; }"
        )
        self.play_button = QPushButton("播放")
        self.play_button.setStyleSheet(dark_button_qss)
        self.play_button.clicked.connect(self.toggle_playback)
        self.back_button = QPushButton("-5 秒")
        self.back_button.setStyleSheet(dark_button_qss)
        self.back_button.clicked.connect(lambda: self.seek(max(0, self._current_sec - 5)))
        self.forward_button = QPushButton("+5 秒")
        self.forward_button.setStyleSheet(dark_button_qss)
        self.forward_button.clicked.connect(lambda: self.seek(self._current_sec + 5))

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1)
        self.slider.sliderMoved.connect(self.seek)
        self.slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #1E293B; height: 6px; "
            "border-radius: 3px; }"
            "QSlider::sub-page:horizontal { background: #2563EB; height: 6px; "
            "border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #60A5FA; width: 14px; "
            "margin: -4px 0; border-radius: 7px; }"
        )

        header = QHBoxLayout()
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(self.timecode)

        controls = QHBoxLayout()
        controls.addWidget(self.play_button)
        controls.addWidget(self.back_button)
        controls.addWidget(self.forward_button)
        controls.addWidget(self.slider, 1)

        # 时间轴 slot：默认空，主窗口可调用 attach_timeline 注入
        self._timeline_host = QWidget()
        self._timeline_host.setStyleSheet("background: transparent;")
        self._timeline_slot = QVBoxLayout(self._timeline_host)
        self._timeline_slot.setContentsMargins(0, 6, 0, 0)
        self._timeline_slot.setSpacing(4)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addLayout(header)
        layout.addWidget(self.surface_container, 1)
        layout.addLayout(controls)
        layout.addWidget(self._timeline_host)
        layout.addWidget(self.status)

        self.timer = QTimer(self)
        self.timer.setInterval(500 if self._vlc_available else 1000)
        self.timer.timeout.connect(self._tick)

        if self._vlc_available:
            try:
                self._vlc_instance = self._vlc_module.Instance()
                self._vlc_player = self._vlc_instance.media_player_new()
            except Exception as exc:  # pragma: no cover - vlc runtime missing
                self._vlc_available = False
                self._vlc_instance = None
                self._vlc_player = None
                self.status.setText(f"VLC 初始化失败：{exc}")

    def attach_timeline(self, timeline_widget: QWidget) -> None:
        """主窗口把全局 EventTimeline 嵌进来。深色 palette 与卡片融合。"""
        if hasattr(timeline_widget, "set_dark"):
            timeline_widget.set_dark(True)
        timeline_widget.setStyleSheet("background: transparent;")
        timeline_widget.setMinimumHeight(96)
        timeline_widget.setMaximumHeight(110)
        if self._timeline_slot is not None:
            self._timeline_slot.addWidget(timeline_widget)

    # --- vlc bootstrap ----------------------------------------------------
    @staticmethod
    def _probe_vlc() -> Any:
        import os as _os
        if _os.environ.get("DVR_DISABLE_VLC", "").strip() in ("1", "true", "yes"):
            return None
        try:
            import vlc  # type: ignore
        except Exception:
            return None
        return vlc

    def _attach_player_surface(self) -> None:
        if not self._vlc_player:
            return
        try:
            win_id = int(self.video_frame.winId())
        except Exception:
            return
        try:
            if sys.platform.startswith("win"):
                self._vlc_player.set_hwnd(win_id)
            elif sys.platform == "darwin":
                self._vlc_player.set_nsobject(win_id)
            else:
                self._vlc_player.set_xwindow(win_id)
        except Exception as exc:  # pragma: no cover - depends on host OS
            self.status.setText(f"VLC 视频窗口绑定失败：{exc}")

    # --- placeholder copy --------------------------------------------------
    def _placeholder_text(self, mode: str, title: str = "") -> str:
        if mode == "idle":
            return "尚未选择视频\n\n在左侧检索结果或视频库中点击一项即可加载"
        if mode == "loaded-novlc":
            return (
                f"{title}\n\n占位模式：未检测到 VLC，无法实际播放\n"
                "可通过点击事件触发 seek，时间轴会同步移动"
            )
        if mode == "loaded-vlc":
            return f"{title}\n\nVLC 已就绪，等待后端提供视频流地址"
        if mode == "stream-failed":
            return f"{title}\n\nVLC 加载视频流失败，请检查后端 stream URL"
        return ""

    # --- public API --------------------------------------------------------
    def load_video(self, video: VideoRecord) -> None:
        """以 VideoRecord 形式加载（mock 模式入口）。"""
        self._video = video
        self._current_sec = 0
        self._duration_sec = max(1, int(video.duration_sec))
        self.slider.setRange(0, self._duration_sec)
        self.title.setText(video.title)
        mode = "loaded-vlc" if self._vlc_available else "loaded-novlc"
        self.surface_label.setText(self._placeholder_text(mode, video.title))
        self._surface_stack.setCurrentWidget(self.surface_label)
        self.status.setText(f"已加载：{video.title} · 状态 {video.status}")
        self._sync_time()

    def load_video_url(self, url: str, duration_sec: int, title: str) -> None:
        """将真实视频流交给 VLC 播放（RestApiClient 模式入口）。"""
        self._current_sec = 0
        self._duration_sec = max(1, int(duration_sec))
        self.slider.setRange(0, self._duration_sec)
        self.title.setText(title)

        if not self._vlc_available or not self._vlc_player:
            self.surface_label.setText(
                self._placeholder_text("loaded-novlc", title)
                + f"\n后端视频流地址：{url}"
            )
            self._surface_stack.setCurrentWidget(self.surface_label)
            self.status.setText("未检测到 VLC，无法实际播放视频流")
            self._sync_time()
            return

        try:
            media = self._vlc_instance.media_new(url)
            self._vlc_player.set_media(media)
            self._attach_player_surface()
            self._surface_stack.setCurrentWidget(self.video_frame)
            self.status.setText(f"已连接视频流：{title}")
        except Exception as exc:  # pragma: no cover - runtime failure
            self.status.setText(f"VLC 加载视频失败：{exc}")
            self.surface_label.setText(self._placeholder_text("stream-failed", title))
            self._surface_stack.setCurrentWidget(self.surface_label)
        self._sync_time()

    def toggle_playback(self) -> None:
        if self._vlc_available and self._vlc_player and self._vlc_player.get_media():
            if self._playing:
                try:
                    self._vlc_player.pause()
                except Exception:
                    pass
                self._playing = False
                self.play_button.setText("播放")
                self.timer.stop()
            else:
                try:
                    self._vlc_player.play()
                except Exception as exc:  # pragma: no cover
                    self.status.setText(f"VLC 播放失败：{exc}")
                    return
                self._playing = True
                self.play_button.setText("暂停")
                self.timer.start()
            return

        # 占位模式：虚拟进度条
        self._playing = not self._playing
        self.play_button.setText("暂停" if self._playing else "播放")
        if self._playing:
            self.timer.start()
        else:
            self.timer.stop()

    def seek(self, seconds: int) -> None:
        target = max(0, int(seconds))
        if self._duration_sec:
            target = min(target, self._duration_sec)
        self._current_sec = target
        if self._vlc_available and self._vlc_player and self._vlc_player.get_media():
            try:
                self._vlc_player.set_time(target * 1000)
            except Exception:
                pass
        self.seek_requested.emit(self._current_sec)
        self._sync_time()

    def seek_to_event(self, event: SemanticEvent) -> None:
        self.seek(event.start_sec)
        self.status.setText(
            f"已跳转到事件：{event.title} · {event.time_range} · 置信度 {event.confidence_percent}"
        )

    # --- internals ---------------------------------------------------------
    def _tick(self) -> None:
        if self._vlc_available and self._vlc_player and self._vlc_player.get_media():
            try:
                ms = self._vlc_player.get_time()
            except Exception:
                ms = -1
            if ms is not None and ms >= 0:
                self._current_sec = int(ms / 1000)
            self._sync_time()
            return

        if self._duration_sec <= 0:
            return
        if self._current_sec >= self._duration_sec:
            self.toggle_playback()
            return
        self._current_sec += 1
        self._sync_time()

    def _sync_time(self) -> None:
        duration = self._duration_sec if self._duration_sec else (
            self._video.duration_sec if self._video else 0
        )
        self.timecode.setText(f"{format_time(self._current_sec)} / {format_time(duration)}")
        self.slider.blockSignals(True)
        self.slider.setValue(self._current_sec)
        self.slider.blockSignals(False)
