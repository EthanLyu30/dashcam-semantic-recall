"""Programmatic app logo (no binary asset needed).

Paints a rounded indigo→blue gradient tile with a white magnifier glyph (the
"semantic recall / search" motif). Used for the window/taskbar icon and the
header brand chip so the app no longer shows the generic Python icon.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)


def make_logo_pixmap(size: int = 64) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Rounded gradient tile.
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor("#4F46E5"))
    gradient.setColorAt(1.0, QColor("#2563EB"))
    radius = size * 0.28
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(gradient))
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    # White magnifier: ring + handle.
    pen = QPen(QColor("#FFFFFF"))
    pen.setWidthF(max(2.0, size * 0.085))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    d = size * 0.42
    ring = QRectF(size * 0.22, size * 0.20, d, d)
    painter.drawEllipse(ring)
    painter.drawLine(
        QPointF(size * 0.60, size * 0.58),
        QPointF(size * 0.78, size * 0.78),
    )
    painter.end()
    return pm


def make_logo_icon() -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(make_logo_pixmap(s))
    return icon
