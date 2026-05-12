"""Render the Qt6 desktop client and dump real screenshots.

Strategy:
- Use the native Windows backend (offscreen is unstable here).
- NEVER call window.show() — grab() works on hidden widgets after layout.
- Replace ResultCard with a screenshot-safe stand-in, because the
  production card crashes during a hidden-widget grab due to its hover
  stylesheet + pointer cursor.
- Force DVR_DISABLE_VLC=1 so the player renders its placeholder.

Outputs:
    docs/phase2-report/shots/qt-*.png
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "apps" / "desktop_client"))

os.environ["DVR_DISABLE_VLC"] = "1"

# Important: defer all PySide6 imports until after QApplication is up.
# We deliberately do NOT call app.setStyleSheet() — combined with hidden-widget
# grab the global QSS has been seen to crash.

SHOTS_DIR = REPO_ROOT / "docs" / "phase2-report" / "shots"
SHOTS_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    from PySide6.QtWidgets import (
        QApplication, QFrame, QLabel, QVBoxLayout,
    )
    from PySide6.QtCore import Signal, Qt, QSize

    # High-DPI antialiasing setup — must happen before any window is shown.
    # Qt6 enables HiDPI support by default; we only need to set the font
    # antialiasing strategy here.
    from PySide6.QtGui import QFont
    app = QApplication(sys.argv)
    # Set global font strategy to prefer smooth antialiasing
    base_font = QFont("Microsoft YaHei UI", 10)
    base_font.setStyleStrategy(
        QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality
    )
    app.setFont(base_font)
    print(">>> QApplication ready (HiDPI + AA font)", flush=True)

    # Load the light operational stylesheet so screenshots match the
    # prototype's visual language. Earlier instability was tracked down to
    # ResultCard's :hover rule + cursor, not to the global QSS — so the
    # stylesheet is fine to apply now.
    theme_path = REPO_ROOT / "apps" / "desktop_client" / "dvr_semantic_client" / "resources" / "theme.qss"
    if theme_path.exists():
        app.setStyleSheet(theme_path.read_text(encoding="utf-8"))
        print(">>> theme.qss applied", flush=True)

    # ---- Inline ResultCard stand-in -----------------------------------------
    class CaptureCard(QFrame):
        selected = Signal(object)

        def __init__(self, event, parent=None):
            super().__init__(parent)
            if event.confidence >= 0.85:
                color = "#22C55E"
            elif event.confidence >= 0.78:
                color = "#F59E0B"
            else:
                color = "#EF4444"
            html = (
                f"<div><b style='font-size:14pt;color:#1E293B;'>{event.title}</b>"
                f" &nbsp; <span style='color:{color};font-weight:700;"
                f"border:1px solid {color};border-radius:5px;padding:1px 8px;'>"
                f"{event.confidence_percent}</span>"
                f"<br><span style='color:#64748B;'>{event.time_range}  ·  "
                f"相关度 {event.similarity_percent or '-'}</span>"
                f"<br><span style='color:#334155;'>{event.summary}</span>"
                f"<br><span style='color:#2563EB;'>"
                f"{'  '.join('#'+t for t in event.tags)}</span></div>"
            )
            l = QLabel(html)
            l.setTextFormat(Qt.TextFormat.RichText)
            l.setWordWrap(True)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.addWidget(l)

    # Production ResultCard is now stable (the `self.event = event` line is
    # assigned AFTER the layout is wired, which sidesteps a PySide6 6.x bug).
    # Keep the CaptureCard class above defined in case we ever need to swap
    # back in for a clean-room screenshot pass.
    _ = CaptureCard  # silence unused warning

    from dvr_semantic_client.widgets.main_window import MainWindow
    from dvr_semantic_client.api import MockApiClient

    window = MainWindow(MockApiClient())
    print(">>> MainWindow constructed", flush=True)

    # Larger base resolution → more pixels in PNG → browser/slide downscale
    # produces crisp text rather than upscale blur.
    window.resize(1920, 1080)
    window.ensurePolished()
    for _ in range(20):
        app.processEvents()
    print(">>> initial layout ready (1920×1080)", flush=True)

    def grab(widget, name, size=None):
        if size is not None:
            widget.resize(QSize(*size))
            widget.ensurePolished()
            for _ in range(8):
                app.processEvents()
        pix = widget.grab()
        out = SHOTS_DIR / name
        pix.save(str(out), "PNG")
        print(f"  {out.relative_to(REPO_ROOT)}  {out.stat().st_size // 1024} KB",
              flush=True)

    # 01. Search workspace with default search applied
    window.show_page(1)
    for _ in range(12):
        app.processEvents()
    grab(window, "qt-01-search-workspace.png")

    # 02. Click the illegal-parking result (index 1) to highlight selection
    events = window.current_events
    if len(events) >= 2:
        window.select_event(events[1])
        for _ in range(8):
            app.processEvents()
        grab(window, "qt-02-search-illegal-parking.png")

    # 03–08. The static prototype pages
    for idx, name in [
        (0, "qt-03-overview.png"),
        (2, "qt-04-video-library.png"),
        (3, "qt-05-review.png"),
        (4, "qt-06-alerts.png"),
        (5, "qt-07-accidents.png"),
        (6, "qt-08-evidence.png"),
        (7, "qt-09-daily-report.png"),
        (8, "qt-10-settings.png"),
        (9, "qt-11-roles.png"),
        (10, "qt-12-login.png"),
    ]:
        window.show_page(idx)
        for _ in range(8):
            app.processEvents()
        grab(window, name)

    # Re-enter the search workspace for tight crops
    window.show_page(1)
    for _ in range(12):
        app.processEvents()
    if events:
        window.select_event(events[0])
        for _ in range(8):
            app.processEvents()

    workspace = window.stack.currentWidget()
    if workspace is not None:
        grab(workspace, "qt-13-search-only.png", size=(1760, 1040))

    # Result list (the search panel) at a tighter width
    grab(window.search_panel, "qt-14-result-list.png", size=(640, 900))
    # Detail panel with export button enabled
    grab(window.detail, "qt-15-event-detail.png", size=(640, 440))

    total = len(list(SHOTS_DIR.glob("qt-*.png")))
    print(f"\n>>> wrote {total} screenshots to "
          f"{SHOTS_DIR.relative_to(REPO_ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException:
        traceback.print_exc()
        raise
