from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import QTimer, Qt, Signal
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


class VideoPlayerPanel(QFrame):
    """Video playback panel.

    When ``python-vlc`` is installed we drive a real ``vlc.MediaPlayer`` and
    attach it to an embedded ``QFrame`` surface. Otherwise we keep the
    placeholder behaviour so the desktop demo still runs headless.
    """

    seek_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "panel")
        self._video: VideoRecord | None = None
        self._current_sec = 0
        self._duration_sec = 0
        self._playing = False
        self._vlc_instance: Any = None
        self._vlc_player: Any = None
        self._vlc_module: Any = self._probe_vlc()
        self._vlc_available = self._vlc_module is not None

        # video surface — a native widget VLC can paint onto
        self.video_frame = QFrame()
        self.video_frame.setObjectName("videoSurface")
        self.video_frame.setMinimumHeight(420)
        self.video_frame.setStyleSheet(
            "#videoSurface { background: #020617; border-radius: 18px; "
            "border: 1px solid #1E293B; }"
        )
        # disable Qt's own painting so VLC can hand-draw the frame
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True)

        # placeholder label shown when no video / no VLC available
        self.surface_label = QLabel("No video selected")
        self.surface_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.surface_label.setStyleSheet(
            "QLabel { background: #020617; border-radius: 18px; "
            "border: 1px solid #1E293B; color: #CBD5E1; font-size: 18px; }"
        )

        # stack surface_label on top of video_frame; flip between them
        self.surface_container = QWidget()
        self._surface_stack = QStackedLayout(self.surface_container)
        self._surface_stack.setContentsMargins(0, 0, 0, 0)
        self._surface_stack.addWidget(self.video_frame)
        self._surface_stack.addWidget(self.surface_label)
        self._surface_stack.setCurrentWidget(self.surface_label)

        # legacy alias retained for any external lookups
        self.surface = self.surface_label

        self.title = QLabel("Playback")
        self.title.setProperty("role", "panelTitle")
        self.timecode = QLabel("00:00")
        self.timecode.setProperty("role", "timecode")
        status_text = "VLC ready" if self._vlc_available else "VLC not installed — mock playback mode"
        self.status = QLabel(status_text)
        self.status.setProperty("role", "muted")

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_playback)
        self.back_button = QPushButton("-5s")
        self.back_button.clicked.connect(lambda: self.seek(max(0, self._current_sec - 5)))
        self.forward_button = QPushButton("+5s")
        self.forward_button.clicked.connect(lambda: self.seek(self._current_sec + 5))

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1)
        self.slider.sliderMoved.connect(self.seek)

        header = QHBoxLayout()
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(self.timecode)

        controls = QHBoxLayout()
        controls.addWidget(self.play_button)
        controls.addWidget(self.back_button)
        controls.addWidget(self.forward_button)
        controls.addWidget(self.slider, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(header)
        layout.addWidget(self.surface_container, 1)
        layout.addLayout(controls)
        layout.addWidget(self.status)

        # poll vlc state every 500ms when a real player is active; 1s otherwise
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
                self.status.setText(f"VLC init failed: {exc}")

    # --- vlc bootstrap ----------------------------------------------------
    @staticmethod
    def _probe_vlc() -> Any:
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
            self.status.setText(f"VLC surface bind failed: {exc}")

    # --- public API --------------------------------------------------------
    def load_video(self, video: VideoRecord) -> None:
        """Backwards-compatible entry: load a record without a real URL."""
        self._video = video
        self._current_sec = 0
        self._duration_sec = max(1, int(video.duration_sec))
        self.slider.setRange(0, self._duration_sec)
        self.title.setText(video.title)
        self.surface_label.setText(
            f"{video.title}\n\n"
            + ("VLC ready — pass a stream URL via load_video_url()."
               if self._vlc_available else "VLC not installed — placeholder playback.")
        )
        self._surface_stack.setCurrentWidget(self.surface_label)
        self.status.setText(f"Loaded {video.id} · status {video.status}")
        self._sync_time()

    def load_video_url(self, url: str, duration_sec: int, title: str) -> None:
        """Load a real media URL into VLC and bind to the surface."""
        self._current_sec = 0
        self._duration_sec = max(1, int(duration_sec))
        self.slider.setRange(0, self._duration_sec)
        self.title.setText(title)

        if not self._vlc_available or not self._vlc_player:
            self.surface_label.setText(
                f"{title}\n\nVLC not installed — cannot play stream.\n{url}"
            )
            self._surface_stack.setCurrentWidget(self.surface_label)
            self.status.setText("VLC not installed — playback disabled")
            self._sync_time()
            return

        try:
            media = self._vlc_instance.media_new(url)
            self._vlc_player.set_media(media)
            self._attach_player_surface()
            self._surface_stack.setCurrentWidget(self.video_frame)
            self.status.setText(f"Streaming {url}")
        except Exception as exc:  # pragma: no cover - runtime failure
            self.status.setText(f"VLC load failed: {exc}")
            self.surface_label.setText(f"VLC load failed:\n{exc}")
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
                self.play_button.setText("Play")
                self.timer.stop()
            else:
                try:
                    self._vlc_player.play()
                except Exception as exc:  # pragma: no cover
                    self.status.setText(f"VLC play failed: {exc}")
                    return
                self._playing = True
                self.play_button.setText("Pause")
                self.timer.start()
            return

        # placeholder mode
        self._playing = not self._playing
        self.play_button.setText("Pause" if self._playing else "Play")
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
            f"Seek -> {event.title} · {event.time_range} · confidence {event.confidence_percent}"
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

        # placeholder fallback: advance a virtual cursor
        if self._duration_sec <= 0:
            return
        if self._current_sec >= self._duration_sec:
            self.toggle_playback()
            return
        self._current_sec += 1
        self._sync_time()

    def _sync_time(self) -> None:
        duration = self._duration_sec if self._duration_sec else (self._video.duration_sec if self._video else 0)
        self.timecode.setText(f"{format_time(self._current_sec)} / {format_time(duration)}")
        self.slider.blockSignals(True)
        self.slider.setValue(self._current_sec)
        self.slider.blockSignals(False)
