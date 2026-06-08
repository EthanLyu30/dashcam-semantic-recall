"""Programmatic app logo (no binary asset needed).

A clean, modern mark: a camera/dashcam **focus viewfinder** — four rounded
corner brackets framing a central play glyph — set on a glossy squircle. It
reads as "camera framing + playback/recall", stays crisp from 16px to 256px,
and avoids the generic-magnifier cliché.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)


def _bracket(path: QPainterPath, cx: float, cy: float, hx: float, hy: float, arm: float) -> None:
    """Add an L-shaped corner bracket whose elbow is at (cx,cy).

    hx/hy are +/-1 indicating which way the two arms extend.
    """
    path.moveTo(cx + hx * arm, cy)
    path.lineTo(cx, cy)
    path.lineTo(cx, cy + hy * arm)


def make_logo_pixmap(size: int = 64) -> QPixmap:
    s = float(size)
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # --- glossy squircle tile ---
    tile = QRectF(s * 0.02, s * 0.02, s * 0.96, s * 0.96)
    radius = s * 0.30
    grad = QLinearGradient(tile.topLeft(), tile.bottomRight())
    grad.setColorAt(0.0, QColor("#6366F1"))   # indigo
    grad.setColorAt(1.0, QColor("#2563EB"))   # blue
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(tile, radius, radius)

    # soft top-left gloss for depth
    gloss = QRadialGradient(QPointF(tile.left() + s * 0.30, tile.top() + s * 0.24), s * 0.6)
    gloss.setColorAt(0.0, QColor(255, 255, 255, 60))
    gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
    clip = QPainterPath()
    clip.addRoundedRect(tile, radius, radius)
    p.setClipPath(clip)
    p.setBrush(QBrush(gloss))
    p.drawRect(tile)
    p.setClipping(False)

    cx, cy = s * 0.5, s * 0.5
    half = s * 0.255           # inner frame half-size
    arm = s * 0.135            # bracket arm length

    # --- four focus brackets ---
    brackets = QPainterPath()
    _bracket(brackets, cx - half, cy - half, +1, +1, arm)  # top-left
    _bracket(brackets, cx + half, cy - half, -1, +1, arm)  # top-right
    _bracket(brackets, cx - half, cy + half, +1, -1, arm)  # bottom-left
    _bracket(brackets, cx + half, cy + half, -1, -1, arm)  # bottom-right
    pen = QPen(QColor(255, 255, 255, 235))
    pen.setWidthF(max(1.6, s * 0.072))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(brackets)

    # --- centre play triangle (rounded) ---
    tri = QPainterPath()
    r = s * 0.135
    tri.moveTo(cx - r * 0.62, cy - r)
    tri.lineTo(cx - r * 0.62, cy + r)
    tri.lineTo(cx + r * 0.95, cy)
    tri.closeSubpath()
    play_pen = QPen(QColor("#FFFFFF"))
    play_pen.setWidthF(max(1.2, s * 0.05))
    play_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(play_pen)
    p.setBrush(QColor("#FFFFFF"))
    p.drawPath(tri)

    p.end()
    return pm


def make_logo_icon() -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(make_logo_pixmap(s))
    return icon
