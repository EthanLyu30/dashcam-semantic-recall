from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..models import SemanticEvent, VideoRecord, format_time


class VideoPlayerPanel(QFrame):
    seek_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "panel")
        self._video: VideoRecord | None = None
        self._current_sec = 0
        self._playing = False
        self._vlc_available = self._probe_vlc()

        self.surface = QLabel("No video selected")
        self.surface.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.surface.setMinimumHeight(420)
        self.surface.setObjectName("videoSurface")
        self.surface.setStyleSheet(
            "#videoSurface { background: #020617; border-radius: 18px; "
            "border: 1px solid #1E293B; color: #CBD5E1; font-size: 18px; }"
        )

        self.title = QLabel("Playback")
        self.title.setProperty("role", "panelTitle")
        self.timecode = QLabel("00:00")
        self.timecode.setProperty("role", "timecode")
        self.status = QLabel("Mock playback mode" if not self._vlc_available else "VLC ready")
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
        layout.addWidget(self.surface, 1)
        layout.addLayout(controls)
        layout.addWidget(self.status)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

    def _probe_vlc(self) -> bool:
        try:
            import vlc  # noqa: F401
        except Exception:
            return False
        return True

    def load_video(self, video: VideoRecord) -> None:
        self._video = video
        self._current_sec = 0
        self.slider.setRange(0, max(1, video.duration_sec))
        self.title.setText(video.title)
        self.surface.setText(
            f"{video.title}\n\nVLC surface placeholder\n"
            "Real media binding is ready for 倪羽辰's processed stream URL."
        )
        self.status.setText(f"Loaded {video.id} · status {video.status}")
        self._sync_time()

    def toggle_playback(self) -> None:
        self._playing = not self._playing
        self.play_button.setText("Pause" if self._playing else "Play")
        if self._playing:
            self.timer.start()
        else:
            self.timer.stop()

    def seek(self, seconds: int) -> None:
        if self._video is None:
            return
        self._current_sec = min(max(0, int(seconds)), self._video.duration_sec)
        self.seek_requested.emit(self._current_sec)
        self._sync_time()

    def seek_to_event(self, event: SemanticEvent) -> None:
        self.seek(event.start_sec)
        self.status.setText(
            f"Seek -> {event.title} · {event.time_range} · confidence {event.confidence_percent}"
        )

    def _tick(self) -> None:
        if self._video is None:
            return
        if self._current_sec >= self._video.duration_sec:
            self.toggle_playback()
            return
        self._current_sec += 1
        self._sync_time()

    def _sync_time(self) -> None:
        duration = self._video.duration_sec if self._video else 0
        self.timecode.setText(f"{format_time(self._current_sec)} / {format_time(duration)}")
        self.slider.blockSignals(True)
        self.slider.setValue(self._current_sec)
        self.slider.blockSignals(False)
