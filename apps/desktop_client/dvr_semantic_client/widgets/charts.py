"""自绘图表 widget：柱状图与饼图，不依赖 QtCharts/matplotlib。

设计目标：让概览页的"识别趋势"和"多模态分类分布"两个区域看起来
更接近原型里的 ECharts 视觉，而不是空荡荡的小表格。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class BarPoint:
    label: str            # 横轴标签，例如 "03-21"
    value: int            # 主数值（事件数）
    secondary: int = 0    # 次数值，叠加显示（查询数）
    load_percent: int = 0 # 负载百分比，用细色带显示


@dataclass(frozen=True)
class PieSlice:
    label: str
    value: int
    color: str            # 16 进制颜色


class TrendBarChart(QWidget):
    """识别趋势柱状图：7 天 × (事件数 + 查询数) 双柱 + 负载色带。

    - 纵向双柱：主数值（事件）蓝色，次数值（查询）淡靛
    - 顶部数值标注
    - 底部 X 轴标签
    - 右侧自动 Y 轴刻度（自适应最大值）
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._points: tuple[BarPoint, ...] = ()
        self.setMinimumHeight(220)

    def set_points(self, points: Sequence[BarPoint]) -> None:
        self._points = tuple(points)
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 — Qt API
        if not self._points:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        margin_left = 38
        margin_right = 12
        margin_top = 24
        margin_bottom = 28
        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom
        if w <= 0 or h <= 0:
            return

        max_value = max(
            (max(p.value, p.secondary) for p in self._points),
            default=1,
        )
        # Y 轴上限取整到 10 的倍数，避免顶部贴边
        y_max = max(10, ((max_value // 10) + 1) * 10)

        # 网格 + Y 轴标签
        grid_pen = QPen(QColor("#E2E8F0"))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        for i in range(5):
            y = margin_top + h * i / 4
            painter.drawLine(margin_left, int(y), margin_left + w, int(y))
            tick_value = int(y_max * (1 - i / 4))
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(QRectF(0, y - 8, margin_left - 6, 16),
                             int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                             str(tick_value))
            painter.setPen(grid_pen)

        # 柱
        n = len(self._points)
        slot_w = w / n
        bar_pair_w = min(slot_w * 0.55, 36)
        bar_w = bar_pair_w / 2 - 2

        for index, point in enumerate(self._points):
            slot_left = margin_left + slot_w * index
            slot_center = slot_left + slot_w / 2

            # 主柱（事件数，品牌蓝）
            h_main = h * (point.value / y_max)
            rect_main = QRectF(
                slot_center - bar_pair_w / 2,
                margin_top + h - h_main,
                bar_w,
                h_main,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#2563EB")))
            painter.drawRoundedRect(rect_main, 4, 4)

            # 次柱（查询数，淡靛）
            h_sec = h * (point.secondary / y_max) if point.secondary else 0
            rect_sec = QRectF(
                slot_center - bar_pair_w / 2 + bar_w + 4,
                margin_top + h - h_sec,
                bar_w,
                h_sec,
            )
            painter.setBrush(QBrush(QColor("#A5B4FC")))
            painter.drawRoundedRect(rect_sec, 4, 4)

            # 顶部主数值
            painter.setPen(QColor("#0F172A"))
            painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.Weight.Bold))
            painter.drawText(
                QRectF(slot_center - bar_pair_w / 2 - 4, rect_main.top() - 16,
                       bar_pair_w + 8, 14),
                int(Qt.AlignmentFlag.AlignCenter),
                str(point.value),
            )

            # X 轴标签
            painter.setPen(QColor("#64748B"))
            painter.setFont(QFont("Microsoft YaHei UI", 8))
            painter.drawText(
                QRectF(slot_left, margin_top + h + 6, slot_w, 16),
                int(Qt.AlignmentFlag.AlignCenter),
                point.label,
            )

            # 负载色带（底部细线，绿→橙→红，按 load_percent 着色）
            if point.load_percent:
                load_color = (
                    "#22C55E" if point.load_percent < 50
                    else "#F59E0B" if point.load_percent < 75
                    else "#EF4444"
                )
                painter.setPen(QPen(QColor(load_color), 3))
                painter.drawLine(
                    QPoint(int(slot_left + slot_w * 0.18),
                           margin_top + h + 22),
                    QPoint(int(slot_left + slot_w * 0.18
                               + slot_w * 0.64 * point.load_percent / 100),
                           margin_top + h + 22),
                )

        # 图例（顶部右侧）
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        legend_y = 6
        # 主：事件数
        painter.setBrush(QBrush(QColor("#2563EB")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(margin_left, legend_y, 14, 8), 2, 2)
        painter.setPen(QColor("#475569"))
        painter.drawText(QPoint(margin_left + 20, legend_y + 8), "事件数")
        # 次：查询数
        painter.setBrush(QBrush(QColor("#A5B4FC")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(margin_left + 80, legend_y, 14, 8), 2, 2)
        painter.setPen(QColor("#475569"))
        painter.drawText(QPoint(margin_left + 100, legend_y + 8), "查询数")
        # 负载色带
        painter.setPen(QPen(QColor("#94A3B8"), 3))
        painter.drawLine(QPoint(margin_left + 165, legend_y + 4),
                         QPoint(margin_left + 179, legend_y + 4))
        painter.setPen(QColor("#475569"))
        painter.drawText(QPoint(margin_left + 185, legend_y + 8), "并发负载")

        painter.end()


class CategoryPieChart(QWidget):
    """分类分布饼图：固定颜色 + 右侧图例 + 中央总数。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._slices: tuple[PieSlice, ...] = ()
        self.setMinimumHeight(220)

    def set_slices(self, slices: Sequence[PieSlice]) -> None:
        self._slices = tuple(slices)
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 — Qt API
        if not self._slices:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        total = sum(s.value for s in self._slices) or 1
        # 左侧饼，右侧图例
        chart_size = min(self.width() * 0.5, self.height() - 20)
        chart_x = 18
        chart_y = (self.height() - chart_size) / 2
        ring = QRectF(chart_x, chart_y, chart_size, chart_size)
        inner = chart_size * 0.55
        inner_rect = QRectF(
            chart_x + (chart_size - inner) / 2,
            chart_y + (chart_size - inner) / 2,
            inner,
            inner,
        )

        # 饼瓣
        start_angle = 90 * 16  # 12 点钟方向
        painter.setPen(Qt.PenStyle.NoPen)
        for sl in self._slices:
            sweep = int(sl.value / total * 360 * 16)
            painter.setBrush(QBrush(QColor(sl.color)))
            painter.drawPie(ring, start_angle, -sweep)
            start_angle -= sweep

        # 中央挖空（环形图效果）
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(inner_rect)

        # 中央总数文字
        painter.setPen(QColor("#0F172A"))
        painter.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.Bold))
        painter.drawText(inner_rect, int(Qt.AlignmentFlag.AlignCenter), str(total))
        painter.setPen(QColor("#64748B"))
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(
            QRectF(inner_rect.x(), inner_rect.bottom() - 26,
                   inner_rect.width(), 14),
            int(Qt.AlignmentFlag.AlignCenter),
            "事件总数",
        )

        # 右侧图例
        legend_x = chart_x + chart_size + 24
        legend_w = self.width() - legend_x - 12
        line_h = max(22, (self.height() - 24) / max(len(self._slices), 1))
        painter.setFont(QFont("Microsoft YaHei UI", 10))
        for i, sl in enumerate(self._slices):
            y = 14 + line_h * i
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(sl.color)))
            painter.drawRoundedRect(QRectF(legend_x, y + 2, 12, 12), 3, 3)
            painter.setPen(QColor("#0F172A"))
            painter.drawText(QPoint(int(legend_x + 22), int(y + 12)), sl.label)
            percent = sl.value * 100 / total
            painter.setPen(QColor("#64748B"))
            painter.drawText(
                QRectF(legend_x, y, legend_w, 16),
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                f"{sl.value} · {percent:.0f}%",
            )

        painter.end()
