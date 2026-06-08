"""Programmatic app logo (no binary asset needed).

Concept: an "AI eye" — the system *sees* (multimodal vision) and what it surfaces
is *video* (the pupil is a play triangle). One clever dual-meaning glyph: vision
⨉ playback ⨉ recall. Drawn on a glossy squircle, legible from 16px to 256px.
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


def make_logo_pixmap(size: int = 64) -> QPixmap:
    s = float(size)
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # --- glossy squircle ---
    tile = QRectF(s * 0.02, s * 0.02, s * 0.96, s * 0.96)
    radius = s * 0.30
    grad = QLinearGradient(tile.topLeft(), tile.bottomRight())
    grad.setColorAt(0.0, QColor("#7C3AED"))   # violet
    grad.setColorAt(0.55, QColor("#4F46E5"))  # indigo
    grad.setColorAt(1.0, QColor("#2563EB"))   # blue
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(tile, radius, radius)

    clip = QPainterPath()
    clip.addRoundedRect(tile, radius, radius)
    p.setClipPath(clip)
    gloss = QRadialGradient(QPointF(tile.left() + s * 0.3, tile.top() + s * 0.22), s * 0.62)
    gloss.setColorAt(0.0, QColor(255, 255, 255, 64))
    gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setBrush(QBrush(gloss))
    p.drawRect(tile)
    p.setClipping(False)

    cx, cy = s * 0.5, s * 0.5
    ew, eh = s * 0.64, s * 0.40  # eye width / height

    # --- eye almond outline ---
    eye = QPainterPath()
    left = QPointF(cx - ew / 2, cy)
    right = QPointF(cx + ew / 2, cy)
    eye.moveTo(left)
    eye.quadTo(QPointF(cx, cy - eh), right)
    eye.quadTo(QPointF(cx, cy + eh), left)
    pen = QPen(QColor(255, 255, 255, 240))
    pen.setWidthF(max(1.6, s * 0.060))
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(eye)

    # --- iris ring ---
    iris_r = s * 0.155
    ring = QPen(QColor(255, 255, 255, 235))
    ring.setWidthF(max(1.4, s * 0.052))
    p.setPen(ring)
    p.drawEllipse(QPointF(cx, cy), iris_r, iris_r)

    # --- pupil = play triangle ---
    r = s * 0.092
    tri = QPainterPath()
    tri.moveTo(cx - r * 0.55, cy - r)
    tri.lineTo(cx - r * 0.55, cy + r)
    tri.lineTo(cx + r * 0.95, cy)
    tri.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    p.drawPath(tri)

    p.end()
    return pm


def make_logo_icon() -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(make_logo_pixmap(s))
    return icon
