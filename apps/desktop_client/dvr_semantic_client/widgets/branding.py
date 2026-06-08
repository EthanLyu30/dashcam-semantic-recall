"""Programmatic app logo (no binary asset needed).

Distinctive, on-theme mark: a dashcam point-of-view road in perspective,
converging to a glowing amber focal point — the "recalled moment" the semantic
search surfaces. The dashed centre line doubles as a film/timeline strip
(dashcam ⇄ dashes ⇄ frames). Reads down to 16 px because the road trapezoid and
the amber focal dot stay legible at small sizes.
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


def _lerp(a: QPointF, b: QPointF, t: float) -> QPointF:
    return QPointF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t)


def make_logo_pixmap(size: int = 64) -> QPixmap:
    s = float(size)
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # --- rounded "dusk drive" tile ---
    tile = QRectF(0, 0, s, s)
    bg = QLinearGradient(0, 0, s, s)
    bg.setColorAt(0.0, QColor("#4F46E5"))   # indigo (sky)
    bg.setColorAt(0.55, QColor("#2563EB"))  # blue
    bg.setColorAt(1.0, QColor("#0F2A6B"))   # deep navy (foreground road)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(bg))
    p.drawRoundedRect(tile, s * 0.28, s * 0.28)

    # Clip subsequent road art to the rounded tile.
    clip = QPainterPath()
    clip.addRoundedRect(tile, s * 0.28, s * 0.28)
    p.setClipPath(clip)

    vp = QPointF(s * 0.50, s * 0.34)          # vanishing point
    bl = QPointF(s * 0.18, s * 1.02)          # road base left
    br = QPointF(s * 0.82, s * 1.02)          # road base right
    tl = _lerp(bl, vp, 0.82)                   # road top-left (near VP)
    tr = _lerp(br, vp, 0.82)                   # road top-right

    # --- road surface trapezoid ---
    road = QPainterPath()
    road.moveTo(bl)
    road.lineTo(br)
    road.lineTo(tr)
    road.lineTo(tl)
    road.closeSubpath()
    p.setBrush(QColor(255, 255, 255, 38))
    p.drawPath(road)

    # --- lane edges (converging) ---
    edge = QPen(QColor(255, 255, 255, 200))
    edge.setWidthF(max(1.2, s * 0.045))
    edge.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(edge)
    p.drawLine(bl, tl)
    p.drawLine(br, tr)

    # --- dashed centre line (timeline / frames motif) ---
    dash = QPen(QColor(255, 255, 255, 235))
    dash.setWidthF(max(1.4, s * 0.055))
    dash.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(dash)
    base_mid = QPointF(s * 0.50, s * 1.00)
    for t0, t1 in ((0.05, 0.20), (0.34, 0.49), (0.62, 0.74)):
        p.drawLine(_lerp(base_mid, vp, t0), _lerp(base_mid, vp, t1))

    # --- amber focal point: the "recalled moment" ---
    glow = QRadialGradient(vp, s * 0.20)
    glow.setColorAt(0.0, QColor(251, 191, 36, 200))
    glow.setColorAt(1.0, QColor(251, 191, 36, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(glow))
    p.drawEllipse(vp, s * 0.20, s * 0.20)

    ring = QPen(QColor("#FBBF24"))
    ring.setWidthF(max(1.0, s * 0.03))
    p.setPen(ring)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(vp, s * 0.115, s * 0.115)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(vp, s * 0.052, s * 0.052)

    p.end()
    return pm


def make_logo_icon() -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(make_logo_pixmap(s))
    return icon
