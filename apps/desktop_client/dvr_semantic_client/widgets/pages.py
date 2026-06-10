from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QScrollArea,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .charts import BarPoint, CategoryPieChart, PieSlice, TrendBarChart


def _safe_call(api_client: Any | None, method: str, default: Any):
    """Call ``api_client.method()`` defensively.

    Returns ``default`` when there is no client, the method is missing (e.g.
    MockApiClient), or the call raises (offline / backend error). Lets the
    management pages bind real backend data without breaking mock/offline mode.
    """
    if api_client is None:
        return default
    fn = getattr(api_client, method, None)
    if fn is None:
        return default
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def _has_action(api_client: Any | None, method: str) -> bool:
    return api_client is not None and callable(getattr(api_client, method, None))


def panel() -> QFrame:
    frame = QFrame()
    frame.setProperty("role", "panel")
    return frame


def title(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "panelTitle")
    return label


def muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "muted")
    label.setWordWrap(True)
    return label


def page_shell(title_text: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
    """Returns (scroll_area, content_layout) so pages can scroll vertically."""
    inner = QWidget()
    root = QVBoxLayout(inner)
    root.setContentsMargins(18, 18, 18, 18)
    root.setSpacing(14)

    header = panel()
    header_layout = QVBoxLayout(header)
    header_layout.setContentsMargins(18, 14, 18, 14)
    page_title = QLabel(title_text)
    page_title.setProperty("role", "title")
    header_layout.addWidget(page_title)
    header_layout.addWidget(muted(subtitle))
    root.addWidget(header)

    scroll = QScrollArea()
    scroll.setWidget(inner)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    return scroll, root


_ICON_PALETTE = {
    "#2563EB": ("#EFF6FF", "▶"),
    "#4F46E5": ("#EEF2FF", "◈"),
    "#F59E0B": ("#FFFBEB", "⚡"),
    "#EF4444": ("#FEF2F2", "⚠"),
    "#22C55E": ("#F0FDF4", "✓"),
}

_LABEL_EN = {
    "总处理视频": "Total Processed", "语义检索次数": "Semantic Queries",
    "识别关键事件": "Key Events", "待人工复核": "Pending Review",
    "待复核": "Pending Review", "今日已复核": "Reviewed Today",
    "平均耗时": "Avg Duration", "复核同意率": "Approval Rate",
    "未处理告警": "Open Alerts", "今日告警": "Today Alerts",
    "已关闭": "Resolved", "平均响应": "Avg Response",
    "处理视频": "Processed", "关键事件": "Key Events",
    "检索次数": "Queries", "导出证据": "Exports",
}


def metric_card(label: str, value: str, note: str, accent: str = "#2563EB") -> QFrame:
    """对齐原型的 KPI 卡片：图标块 + 英文副标题 + 大号黑色数字 + 彩色趋势注释。"""
    card = panel()
    card.setStyleSheet(
        "QFrame[role='panel'] { background: #F8FAFC; "
        "border: 1px solid #E8EDF2; border-radius: 24px; }"
        "QLabel { background: transparent; border: none; }"
    )

    icon_bg, icon_char = _ICON_PALETTE.get(accent, ("#EFF6FF", "●"))
    icon_frame = QFrame()
    icon_frame.setFixedSize(48, 48)
    icon_frame.setStyleSheet(
        f"QFrame {{ background: {icon_bg}; border-radius: 14px; border: none; }}"
    )
    icon_lbl = QLabel(icon_char)
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_lbl.setStyleSheet(
        f"color: {accent}; font-size: 18px; background: transparent; border: none;"
    )
    icon_inner = QVBoxLayout(icon_frame)
    icon_inner.setContentsMargins(0, 0, 0, 0)
    icon_inner.addWidget(icon_lbl)

    icon_row = QHBoxLayout()
    icon_row.addWidget(icon_frame)
    icon_row.addStretch()

    lbl_main = QLabel(label)
    lbl_main.setStyleSheet(
        "font-size:13px;font-weight:700;color:#1E293B;"
        "background:transparent;border:none;"
    )
    lbl_en = QLabel(_LABEL_EN.get(label, ""))
    lbl_en.setStyleSheet(
        "font-size:10px;font-weight:700;color:#94A3B8;letter-spacing:1px;"
        "background:transparent;border:none;"
    )
    lbl_value = QLabel(value)
    lbl_value.setStyleSheet(
        "font-size:32px;font-weight:800;color:#0F172A;letter-spacing:-1px;"
        "background:transparent;border:none;"
    )
    lbl_note = QLabel(note)
    lbl_note.setStyleSheet(
        f"font-size:12px;font-weight:700;color:{accent};"
        "background:transparent;border:none;"
    )

    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(0)
    layout.addLayout(icon_row)
    layout.addSpacing(12)
    layout.addWidget(lbl_main)
    layout.addWidget(lbl_en)
    layout.addSpacing(8)
    layout.addWidget(lbl_value)
    layout.addWidget(lbl_note)
    return card


def action_button(text: str, variant: str = "") -> QPushButton:
    button = QPushButton(text)
    if variant:
        button.setProperty("variant", variant)
    return button


def _wip_button(text: str, variant: str = "") -> QPushButton:
    """Button for management-面 write actions that are still UI-only prototypes."""
    btn = action_button(text, variant)

    def _notify() -> None:
        QMessageBox.information(
            btn.window(),
            "原型功能（未接入写操作）",
            f"「{text}」是管理面的写入/操作类功能，目前仍是界面原型，尚未接入后端写接口。\n\n"
            "本版本已真实跑通的链路：登录鉴权、视频上传与预处理、Qwen-VL 语义分析、"
            "自然语言检索、证据导出、操作审计，以及「概览」页的实时后端数据。",
        )

    btn.clicked.connect(_notify)
    return btn


def section_header(text: str, note: str = "") -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.addWidget(title(text))
    layout.addStretch()
    if note:
        layout.addWidget(status_chip(note, "info"))
    return layout


def compact_card(heading: str, body: str, accent: str = "#2563EB") -> QFrame:
    card = panel()
    card.setStyleSheet(
        "QFrame[role='panel'] { background: #FFFFFF; border: 1px solid #E8EDF2; "
        "border-radius: 18px; } QLabel { background: transparent; border: none; }"
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(8)
    label = QLabel(heading)
    label.setStyleSheet(
        f"color: {accent}; font-size: 12px; font-weight: 800; "
        "letter-spacing: 0.5px;"
    )
    desc = muted(body)
    layout.addWidget(label)
    layout.addWidget(desc)
    return card


def dark_panel() -> QFrame:
    frame = QFrame()
    frame.setStyleSheet(
        "QFrame { background: #0F172A; border: 1px solid #1E293B; "
        "border-radius: 22px; } QLabel { background: transparent; border: none; }"
    )
    return frame


def table(headers: list[str], rows: list[list[str]]) -> QTableWidget:
    widget = QTableWidget(len(rows), len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.verticalHeader().setVisible(False)
    widget.setAlternatingRowColors(True)
    widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    for row_idx, row in enumerate(rows):
        for col_idx, value in enumerate(row):
            widget.setItem(row_idx, col_idx, QTableWidgetItem(value))
    header = widget.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    widget.setMinimumHeight(160)
    return widget


_STATUS_PALETTE = {
    "high": ("#FEE2E2", "#B91C1C"),
    "mid": ("#FEF3C7", "#92400E"),
    "low": ("#DCFCE7", "#15803D"),
    "info": ("#DBEAFE", "#1D4ED8"),
    "muted": ("#E2E8F0", "#475569"),
}


def status_chip(text: str, kind: str = "info") -> QLabel:
    bg, fg = _STATUS_PALETTE.get(kind, _STATUS_PALETTE["info"])
    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(
        f"QLabel {{ background: {bg}; color: {fg}; border-radius: 999px; "
        f"padding: 4px 12px; font-size: 11px; font-weight: 700; }}"
    )
    return label


def overview_page(api_client: Any | None = None) -> QWidget:
    # Pull live numbers from the backend when a client is wired; fall back to
    # representative demo values in mock/offline mode.
    data: dict[str, Any] = {}
    if api_client is not None and hasattr(api_client, "dashboard_overview"):
        try:
            data = api_client.dashboard_overview() or {}
        except Exception:
            data = {}

    def _num(key: str, default: int) -> str:
        value = data.get(key, default)
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return str(value)

    nodes = data.get("model_nodes") or {}
    online, total = nodes.get("online", 8), nodes.get("total", 8)
    engine = data.get("engine_status", "健康")
    subtitle = f"系统运行 {engine} · 多模态节点 {online}/{total} · 模型 {nodes.get('provider', '—')}"

    page, root = page_shell("系统状态概览", subtitle)
    # 原型是 3 列 KPI（不是 4 列）
    metrics = QGridLayout()
    metrics.setSpacing(14)
    metrics.addWidget(metric_card("总处理视频", _num("processed_video_count", 8429), f"待复核 {_num('pending_review_count', 18)}"), 0, 0)
    metrics.addWidget(metric_card("语义检索次数", _num("semantic_query_count", 1204), "实时统计", "#4F46E5"), 0, 1)
    metrics.addWidget(metric_card("识别关键事件", _num("identified_event_count", 342), "多模态聚合", "#F59E0B"), 0, 2)
    root.addLayout(metrics)

    lower = QHBoxLayout()
    lower.setSpacing(14)

    trend = panel()
    trend_layout = QVBoxLayout(trend)
    trend_layout.setContentsMargins(22, 20, 22, 20)
    trend_layout.setSpacing(10)
    trend_header = QHBoxLayout()
    trend_header.addWidget(title("识别趋势与并发负载 (7日)"))
    trend_header.addStretch()
    trend_header.addWidget(muted("点击柱体可查看明细"))
    trend_layout.addLayout(trend_header)
    bar_chart = TrendBarChart()
    # 真实后端 7 日趋势（dashboard_trends）；离线 / Mock 或全空时回退到示例曲线
    trends = _safe_call(api_client, "dashboard_trends", {}) or {}
    t_days = trends.get("days") or []
    t_events = trends.get("event_counts") or []
    t_queries = trends.get("query_counts") or []
    t_load = trends.get("worker_load") or []
    if t_days and (any(t_events) or any(t_queries)):
        bar_chart.set_points([
            BarPoint(
                t_days[i],
                int(t_events[i]) if i < len(t_events) else 0,
                int(t_queries[i]) if i < len(t_queries) else 0,
                int(float(t_load[i]) * 100) if i < len(t_load) else 0,
            )
            for i in range(len(t_days))
        ])
    else:
        bar_chart.set_points([
            BarPoint("03-21", 28, 120, 42),
            BarPoint("03-22", 34, 146, 58),
            BarPoint("03-23", 31, 132, 51),
            BarPoint("03-24", 39, 158, 66),
            BarPoint("03-25", 42, 167, 71),
            BarPoint("03-26", 37, 152, 63),
            BarPoint("03-27", 48, 184, 82),
        ])
    trend_layout.addWidget(bar_chart, 1)
    lower.addWidget(trend, 3)

    distribution = panel()
    dist_layout = QVBoxLayout(distribution)
    dist_layout.setContentsMargins(22, 20, 22, 20)
    dist_layout.setSpacing(10)
    dist_layout.addWidget(title("多模态分类分布"))
    dist_layout.addWidget(muted("近 7 天识别到的事件类型占比"))
    pie = CategoryPieChart()
    # 真实后端分类分布（event_distribution）；离线 / Mock 或全空时回退示例
    _pie_palette = ["#2563EB", "#F59E0B", "#EF4444", "#22C55E", "#A855F7", "#0EA5E9", "#64748B"]
    dist_items = (_safe_call(api_client, "event_distribution", {}) or {}).get("items") or []
    if dist_items and any(int(it.get("count", 0) or 0) for it in dist_items):
        pie.set_slices([
            PieSlice(
                str(it.get("label", "未知")),
                int(it.get("count", 0) or 0),
                _pie_palette[i % len(_pie_palette)],
            )
            for i, it in enumerate(dist_items[:7])
        ])
    else:
        pie.set_slices([
            PieSlice("剐蹭", 86, "#2563EB"),
            PieSlice("违停", 74, "#F59E0B"),
            PieSlice("道路障碍", 58, "#EF4444"),
            PieSlice("异常停车", 41, "#22C55E"),
            PieSlice("其它", 23, "#A855F7"),
        ])
    dist_layout.addWidget(pie, 1)
    lower.addWidget(distribution, 2)
    root.addLayout(lower, 1)

    bottom = QHBoxLayout()
    bottom.setSpacing(14)
    # 真实流水线状态：来自 list_videos 的库内视频与结构化进度（原型里这块是
    # 模拟 GPS 轨迹，系统没有定位数据，改为展示真实的处理链路状态）。
    route = panel()
    route_layout = QVBoxLayout(route)
    route_layout.setContentsMargins(22, 20, 22, 20)
    _videos = list(_safe_call(api_client, "list_videos", ()) or ())
    _total_v = len(_videos)
    _indexed_v = sum(1 for v in _videos if str(getattr(v, "status", "")) == "indexed")
    _latest = max(_videos, key=lambda v: str(getattr(v, "created_at", "") or ""), default=None)
    route_layout.addLayout(section_header("视频处理流水线", f"已结构化 {_indexed_v}/{_total_v}"))
    if _latest is not None:
        _mm, _ss = divmod(int(getattr(_latest, "duration_sec", 0) or 0), 60)
        _up = str(getattr(_latest, "created_at", "") or "")[:16].replace("T", " ") or "—"
        route_layout.addWidget(muted(
            f"最新入库: {getattr(_latest, 'title', '—')} · 状态 {getattr(_latest, 'status', '—')} · "
            f"时长 {_mm:02d}:{_ss:02d} · 上传 {_up}"
        ))
        route_info = QLabel(
            f"📼 {getattr(_latest, 'title', '—')}  |  {_indexed_v}/{_total_v} 可检索  |  "
            f"上传→转码→抽帧→模型分析→事件聚合"
        )
    else:
        route_layout.addWidget(muted("视频库为空：到「视频流」页上传一段 mp4，流水线状态会实时显示在这里。"))
        route_info = QLabel("📼 暂无视频  |  上传→转码→抽帧→模型分析→事件聚合")
    route_info.setStyleSheet(
        "color:#2563EB;font-size:13px;font-weight:700;"
        "background:#EFF6FF;border:1px solid #BFDBFE;"
        "border-radius:10px;padding:8px 14px;"
    )
    route_layout.addWidget(route_info)
    route_bar = QProgressBar()
    route_bar.setRange(0, 100)
    route_bar.setValue(int(_indexed_v * 100 / _total_v) if _total_v else 0)
    route_bar.setTextVisible(False)
    route_bar.setFixedHeight(8)
    route_bar.setStyleSheet(
        "QProgressBar{background:#E2E8F0;border-radius:4px;border:none;}"
        "QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
        "stop:0 #2563EB,stop:1 #4F46E5);border-radius:4px;}"
    )
    route_layout.addWidget(route_bar)
    bottom.addWidget(route, 3)

    review = panel()
    review_layout = QVBoxLayout(review)
    review_layout.setContentsMargins(22, 20, 22, 20)
    # 真实后端待复核队列（review_feed）；离线 / Mock 或空时回退示例
    feed_items = (_safe_call(api_client, "review_feed", {}) or {}).get("items") or []
    review_layout.addLayout(section_header("待复核实时动态", f"{len(feed_items)} 待处理" if feed_items else "12 待处理"))
    if feed_items:
        for it in feed_items[:4]:
            conf = int(float(it.get("confidence", 0) or 0) * 100)
            accent = "#EF4444" if conf < 75 else "#F59E0B"
            review_layout.addWidget(compact_card(
                str(it.get("title", "待复核事件")),
                f"{it.get('event_id', '')} · 置信度 {conf}% · {str(it.get('created_at', ''))[:16].replace('T', ' ')}",
                accent,
            ))
    else:
        review_layout.addWidget(compact_card("检测到车辆侧面剐蹭事件", "VID_20260327_1422 · 置信度 68% · 等待复核", "#EF4444"))
        review_layout.addWidget(compact_card("禁停区域异常停留检测", "VID_20260327_1310 · 置信度 72% · 普通", "#F59E0B"))
    bottom.addWidget(review, 2)
    root.addLayout(bottom, 1)
    return page


class VideoLibraryPage(QWidget):
    """Video library tab: upload, process and list videos via api_client."""

    def __init__(self, api_client: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._api_client = api_client

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        header = panel()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_text = QVBoxLayout()
        page_title = QLabel("视频库管理")
        page_title.setProperty("role", "title")
        header_text.addWidget(page_title)
        header_text.addWidget(muted("批量导入、单个视频处理、状态筛选和语义检索入口"))
        header_layout.addLayout(header_text)
        header_layout.addStretch()
        batch_button = _wip_button("批量导入视频")
        self.upload_button = action_button("单个视频处理", "primary")
        self.upload_button.clicked.connect(self._on_upload_clicked)
        self.refresh_button = action_button("刷新列表")
        self.refresh_button.clicked.connect(self.refresh)
        header_layout.addWidget(batch_button)
        header_layout.addWidget(self.upload_button)
        header_layout.addWidget(self.refresh_button)
        root.addWidget(header)

        # 真实统计：视频总数来自 list_videos，其余来自后端 dashboard_overview。
        # 离线 / Mock 取不到时回退到示例数字。
        _ov: dict[str, Any] = {}
        try:
            if hasattr(self._api_client, "dashboard_overview"):
                _ov = self._api_client.dashboard_overview() or {}
        except Exception:
            _ov = {}
        try:
            _total_videos = len(self._api_client.list_videos())
        except Exception:
            _total_videos = 0

        def _ovn(key: str, default: int) -> str:
            v = _ov.get(key, default)
            try:
                return f"{int(v):,}"
            except (TypeError, ValueError):
                return str(v)

        if _ov or _total_videos:
            stat_cards = [
                ("全部视频", f"{_total_videos:,}", "库内视频总数", "#2563EB"),
                ("已完成结构化", _ovn("processed_video_count", 0), "可检索", "#22C55E"),
                ("识别关键事件", _ovn("identified_event_count", 0), "多模态聚合", "#F59E0B"),
                ("待人工复核", _ovn("pending_review_count", 0), "低置信片段", "#EF4444"),
                ("语义检索次数", _ovn("semantic_query_count", 0), "累计查询", "#4F46E5"),
            ]
        else:
            stat_cards = [
                ("全部视频", "3,482", "车队库总量", "#2563EB"),
                ("正在处理中", "18", "识别队列 65%", "#2563EB"),
                ("待人工复核", "24", "低置信片段", "#F59E0B"),
                ("处理失败", "3", "等待重试", "#EF4444"),
                ("已完成结构化", "3,421", "可检索", "#22C55E"),
            ]

        stats = QHBoxLayout()
        stats.setSpacing(10)
        for label, value, note, accent in stat_cards:
            sc = QFrame()
            sc.setProperty("role", "panel")
            sc.setStyleSheet(
                f"QFrame[role='panel'] {{ background:#FFFFFF; border:1px solid #E2E8F0; "
                f"border-radius:14px; border-left:4px solid {accent}; }}"
                "QLabel { background:transparent; border:none; }"
            )
            sl = QVBoxLayout(sc)
            sl.setContentsMargins(16, 14, 16, 14)
            sl.setSpacing(4)
            val_lbl = QLabel(value)
            val_lbl.setStyleSheet(f"color:{accent};font-size:26px;font-weight:900;")
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet("color:#0F172A;font-size:12px;font-weight:700;")
            note_lbl = QLabel(note)
            note_lbl.setStyleSheet("color:#64748B;font-size:11px;")
            sl.addWidget(val_lbl)
            sl.addWidget(name_lbl)
            sl.addWidget(note_lbl)
            stats.addWidget(sc)
        root.addLayout(stats)

        filters = panel()
        filter_layout = QHBoxLayout(filters)
        filter_layout.setContentsMargins(18, 14, 18, 14)
        filter_layout.setSpacing(10)
        self.filter_name = QLineEdit()
        self.filter_name.setPlaceholderText("文件名 / VideoID，例如 vid-…")
        self.filter_status = QComboBox()
        self.filter_status.addItems(["全部状态", "已完成识别", "正在识别", "处理失败"])
        self.filter_keyword = QLineEdit()
        self.filter_keyword.setPlaceholderText("标题关键词，例如 重庆 / Dashcam")
        self.filter_date = QLineEdit()
        self.filter_date.setPlaceholderText("起始日期 2026-06-01")
        filter_layout.addWidget(self.filter_name, 2)
        filter_layout.addWidget(self.filter_status, 1)
        filter_layout.addWidget(self.filter_keyword, 1)
        filter_layout.addWidget(self.filter_date, 1)
        query_btn = action_button("查询", "primary")
        query_btn.clicked.connect(self._apply_filters)
        self.filter_name.returnPressed.connect(self._apply_filters)
        self.filter_keyword.returnPressed.connect(self._apply_filters)
        self.filter_date.returnPressed.connect(self._apply_filters)
        self.filter_status.currentIndexChanged.connect(lambda _i: self._apply_filters())
        filter_layout.addWidget(query_btn)
        root.addWidget(filters)

        progress = panel()
        progress_layout = QVBoxLayout(progress)
        progress_layout.addWidget(title("处理任务"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_label = muted("空闲")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        root.addWidget(progress)

        self.video_table = QTableWidget(0, 6)
        self.video_table.setHorizontalHeaderLabels(
            ["Video ID / 文件名", "上传时间", "处理状态", "时长", "负责人", "操作"]
        )
        self.video_table.verticalHeader().setVisible(False)
        self.video_table.setAlternatingRowColors(True)
        self.video_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.video_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root.addWidget(self.video_table, 1)

        self.refresh()

    # --- helpers ------------------------------------------------------------
    def _set_busy(self, busy: bool, message: str = "") -> None:
        self.progress_bar.setVisible(busy)
        self.progress_label.setText(message or "空闲")
        self.upload_button.setDisabled(busy)
        self.refresh_button.setDisabled(busy)

    _STATUS_GROUPS = {
        "已完成识别": ("indexed",),
        "正在识别": ("uploaded", "preprocessing", "preprocessed", "analyzing"),
        "处理失败": ("failed",),
    }

    def refresh(self) -> None:
        try:
            self._all_videos = tuple(self._api_client.list_videos())
        except Exception as exc:
            QMessageBox.warning(self, "加载失败", f"无法读取视频列表：\n{exc}")
            return
        self._apply_filters()

    def _apply_filters(self) -> None:
        videos = list(getattr(self, "_all_videos", ()) or ())
        name_q = self.filter_name.text().strip().lower()
        keyword_q = self.filter_keyword.text().strip().lower()
        date_q = self.filter_date.text().strip()
        status_label = self.filter_status.currentText()
        allowed = self._STATUS_GROUPS.get(status_label)

        def _keep(video) -> bool:
            vid = str(getattr(video, "id", "")).lower()
            vtitle = str(getattr(video, "title", "")).lower()
            if name_q and name_q not in vid and name_q not in vtitle:
                return False
            if keyword_q and keyword_q not in vtitle:
                return False
            if allowed is not None:
                vstatus = str(getattr(video, "status", "")).lower()
                if not any(vstatus.startswith(s) for s in allowed):
                    return False
            if date_q:
                created = str(getattr(video, "created_at", "") or "")[:10]
                if created and created < date_q:
                    return False
            return True

        filtered = [v for v in videos if _keep(v)]
        self._render_rows(filtered)
        self.progress_label.setText(
            f"筛选结果：{len(filtered)}/{len(videos)} 条"
            if len(filtered) != len(videos) else "空闲"
        )

    def _render_rows(self, videos) -> None:
        self.video_table.setRowCount(len(videos))
        for row, video in enumerate(videos):
            mm, ss = divmod(int(getattr(video, "duration_sec", 0) or 0), 60)
            duration = f"{mm:02d}:{ss:02d}"
            uploaded = str(getattr(video, "created_at", "") or "")[:16].replace("T", " ") or "—"
            cells = [
                f"{getattr(video, 'id', '')}\n{getattr(video, 'title', '')}",
                uploaded,
                str(getattr(video, "status", "")),
                duration,
                "system",
                "检索 / 更多",
            ]
            for col, value in enumerate(cells):
                self.video_table.setItem(row, col, QTableWidgetItem(value))
        self.video_table.resizeColumnsToContents()

    def _on_upload_clicked(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "选择要上传的视频",
            "",
            "Video files (*.mp4 *.mov *.mkv *.avi *.m4v);;All files (*.*)",
        )
        if not path_str:
            return
        path = Path(path_str)
        title_text = path.stem or path.name

        self._set_busy(True, f"上传中：{path.name}")
        try:
            upload_result = self._api_client.upload_video(path, title=title_text)
        except Exception as exc:
            self._set_busy(False)
            QMessageBox.critical(self, "上传失败", f"上传 {path.name} 失败：\n{exc}")
            return

        video_id = ""
        if isinstance(upload_result, dict):
            video_id = str(upload_result.get("video_id", ""))

        if not video_id:
            self._set_busy(False)
            QMessageBox.warning(self, "上传异常", "服务端未返回 video_id。")
            self.refresh()
            return

        self._set_busy(True, f"处理中：{video_id}")
        try:
            self._api_client.process_video(video_id)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "处理失败",
                f"上传成功但处理失败（video_id={video_id}）：\n{exc}",
            )
        finally:
            self._set_busy(False)
            self.refresh()


def video_library_page(api_client: Any | None = None) -> QWidget:
    """Factory kept for compatibility; api_client is required for live data."""
    if api_client is None:
        # Fallback static rendering for environments without an api client.
        page, root = page_shell("视频库管理", "上传、处理状态、缩略图封面和任务进度管理")
        root.addWidget(
            table(
                ["视频", "时长", "状态", "事件数", "更新时间"],
                [
                    ["VID_20260327_1422 南山区巡查", "30:30", "可检索", "3", "14:35"],
                    ["VID_20260328_0908 滨河大道早高峰", "36:00", "可检索", "2", "09:18"],
                    ["VID_20260329_1810 高架入口", "22:45", "分析中", "-", "18:12"],
                ],
            ),
            1,
        )
        return page
    return VideoLibraryPage(api_client)


def review_page(api_client: Any | None = None) -> QWidget:
    page, root = page_shell("人工复核中心", "低置信事件人工确认（实时后端队列）")
    _state = {"event_id": "", "title": ""}
    _refs: dict = {}

    _REVIEW_CN = {
        "pending": "待复核",
        "reviewing": "复核中",
        "confirmed": "已确认",
        "rejected": "已驳回",
    }

    def _conf_pct(value) -> int:
        try:
            return int(float(value) * 100)
        except (TypeError, ValueError):
            return 0

    def _load_thumbnail(task: dict) -> bool:
        """Fetch the selected event's real keyframe into the workbench surface."""
        url = str(task.get("thumbnail_url", "") or "")
        base = str(getattr(api_client, "base_url", "") or "")
        surface = _refs.get("surface")
        if not url or not base or surface is None:
            return False
        try:
            from PySide6.QtGui import QPixmap

            from ..api import requests as _http

            resp = _http.get(f"{base}{url}" if url.startswith("/") else url, timeout=6)
            resp.raise_for_status()
            pixmap = QPixmap()
            if not pixmap.loadFromData(resp.content):
                return False
            surface.setPixmap(pixmap.scaled(
                max(surface.width(), 480),
                max(surface.height(), 300),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            return True
        except Exception:
            return False

    def _select(task: dict) -> None:
        _state["event_id"] = task.get("event_id", "")
        _state["title"] = task.get("title", "")
        conf = _conf_pct(task.get("confidence"))
        surface = _refs.get("surface")
        if surface is not None and not _load_thumbnail(task):
            surface.setText(
                f"{task.get('title','事件')}\n\n置信度 {conf}% · {task.get('event_type','')}\n"
                "（该事件没有可加载的关键帧）"
            )
        if _refs.get("chip") is not None:
            _refs["chip"].setText(f"当前: {task.get('title','—')}")
        # 工作台下方三个 chip 显示该事件的真实元数据
        for key, text in (
            ("meta_type", f"类型 {task.get('event_type','—')}"),
            ("meta_conf", f"AI 置信度 {conf}%"),
            ("meta_time", f"入库 {str(task.get('created_at',''))[:16].replace('T', ' ') or '—'}"),
        ):
            if _refs.get(key) is not None:
                _refs[key].setText(text)
        history = _refs.get("history")
        if history is not None:
            history.clear()
            history.addItems([
                f"{str(task.get('created_at',''))[:19].replace('T', ' ')} · AI 识别入库 · 置信度 {conf}%",
                f"当前状态 · {_REVIEW_CN.get(task.get('review_status', ''), task.get('review_status', '待复核'))}"
                f" · 事件 {task.get('event_id','')}",
            ])

    body = QHBoxLayout()
    body.setSpacing(14)

    queue = panel()
    queue_layout = QVBoxLayout(queue)
    queue_layout.setContentsMargins(22, 20, 22, 20)
    queue_layout.setSpacing(10)
    queue_header = QHBoxLayout()
    queue_header.addWidget(title("任务队列"))
    queue_header.addStretch()
    remaining_chip = status_chip("剩余 0", "low")
    queue_header.addWidget(remaining_chip)
    refresh_queue_btn = action_button("刷新")
    queue_header.addWidget(refresh_queue_btn)
    queue_layout.addLayout(queue_header)
    queue_layout.addWidget(muted("低置信事件自动入队，点击「复核」选中后在右侧提交结论"))
    tasks_widget = QWidget()
    tasks_widget.setObjectName("reviewTasksHost")
    tasks_widget.setStyleSheet("#reviewTasksHost { background: transparent; }")
    tasks_inner = QVBoxLayout(tasks_widget)
    tasks_inner.setContentsMargins(0, 0, 0, 0)
    tasks_inner.setSpacing(6)

    def _reload_queue() -> None:
        while tasks_inner.count():
            item = tasks_inner.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        payload = _safe_call(api_client, "review_tasks", {}) or {}
        tasks_data = payload.get("items", [])
        try:
            total = int(payload.get("total", len(tasks_data)) or 0)
        except (TypeError, ValueError):
            total = len(tasks_data)
        remaining_chip.setText(f"剩余 {total}")
        bg, fg = _STATUS_PALETTE["high" if total else "low"]
        remaining_chip.setStyleSheet(
            f"QLabel {{ background: {bg}; color: {fg}; border-radius: 999px; "
            f"padding: 4px 12px; font-size: 11px; font-weight: 700; }}"
        )
        if not tasks_data:
            tasks_inner.addWidget(muted("队列为空（或离线 / Mock 模式，连接真实后端后显示）。"))
        for task in tasks_data:
            item_frame = QFrame()
            item_frame.setStyleSheet(
                "QFrame { background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; }"
                "QLabel { background:transparent; border:none; }"
            )
            item_lay = QHBoxLayout(item_frame)
            item_lay.setContentsMargins(10, 8, 10, 8)
            item_lay.setSpacing(8)
            conf = _conf_pct(task.get("confidence"))
            item_lay.addWidget(status_chip(f"{conf}%", "high" if conf < 75 else "mid"))
            info = QVBoxLayout()
            top_lbl = QLabel(task.get("title", "事件"))
            top_lbl.setStyleSheet("color:#0F172A;font-size:12px;font-weight:700;")
            bot_lbl = QLabel(f"{task.get('event_type','')} · {str(task.get('created_at',''))[:16].replace('T',' ')}")
            bot_lbl.setStyleSheet("color:#64748B;font-size:11px;")
            info.addWidget(top_lbl)
            info.addWidget(bot_lbl)
            item_lay.addLayout(info, 1)
            pick = action_button("复核")
            pick.clicked.connect(lambda _c=False, t=task: _select(t))
            item_lay.addWidget(pick)
            tasks_inner.addWidget(item_frame)
        tasks_inner.addStretch()

    refresh_queue_btn.clicked.connect(_reload_queue)
    _reload_queue()
    tasks_scroll = QScrollArea()
    tasks_scroll.setWidget(tasks_widget)
    tasks_scroll.setWidgetResizable(True)
    tasks_scroll.setFrameShape(QFrame.Shape.NoFrame)
    # No horizontal scrollbar: let the row compress so the 复核 button stays
    # visible instead of being pushed off behind a sideways scroll.
    tasks_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    queue_layout.addWidget(tasks_scroll, 1)
    body.addWidget(queue, 2)

    workbench = dark_panel()
    workbench_layout = QVBoxLayout(workbench)
    workbench_layout.setContentsMargins(20, 18, 20, 18)
    workbench_layout.setSpacing(12)
    wb_title = QLabel("复核视频工作台")
    wb_title.setStyleSheet("color:#E2E8F0;font-size:16px;font-weight:800;")
    workbench_layout.addWidget(wb_title)
    surface = QLabel("点击左侧「复核」选择一条待确认事件\n选中后这里加载该事件的真实关键帧")
    surface.setAlignment(Qt.AlignmentFlag.AlignCenter)
    surface.setMinimumHeight(300)
    surface.setWordWrap(True)
    surface.setStyleSheet(
        "QLabel { background:#020617; color:#CBD5E1; border-radius:18px; "
        "border:1px solid #334155; font-size:18px; font-weight:700; }"
    )
    _refs["surface"] = surface
    workbench_layout.addWidget(surface, 1)
    frame_row = QHBoxLayout()
    for key, placeholder in (
        ("meta_type", "类型 —"),
        ("meta_conf", "AI 置信度 —"),
        ("meta_time", "入库 —"),
    ):
        chip = QLabel(placeholder)
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip.setMinimumHeight(56)
        chip.setStyleSheet(
            "QLabel { background:#1E293B; color:#93C5FD; border-radius:12px; "
            "border:1px solid #334155; font-size:12px; font-weight:800; }"
        )
        _refs[key] = chip
        frame_row.addWidget(chip)
    workbench_layout.addLayout(frame_row)
    body.addWidget(workbench, 4)

    form = panel()
    form_layout = QVBoxLayout(form)
    form_layout.setContentsMargins(22, 20, 22, 20)
    form_layout.setSpacing(10)
    form_header = QHBoxLayout()
    form_header.addWidget(title("复核判定与标注"))
    form_header.addStretch()
    current_chip = status_chip("当前: 未选择", "info")
    _refs["chip"] = current_chip
    form_header.addWidget(current_chip)
    form_layout.addLayout(form_header)
    form_layout.addWidget(muted("选择复核结论、补充备注，提交后写入审计日志"))
    radio_buttons = []
    for option, chip in [
        ("通过识别结果", "AI准确"),
        ("驳回 / 误报", "模型误判"),
        ("标记为存疑点", "需二次复核"),
    ]:
        row = QHBoxLayout()
        check = QRadioButton(option)
        radio_buttons.append(check)
        row.addWidget(check)
        row.addStretch()
        row.addWidget(status_chip(chip, "low" if "通过" in option else "mid"))
        form_layout.addLayout(row)
    radio_buttons[0].setChecked(True)
    note = QTextEdit()
    note.setPlaceholderText("复核备注（可选）：记录误判原因、补充人工标注……")
    form_layout.addWidget(note, 1)
    history = QListWidget()
    history.addItem("选中左侧任务后，这里显示该事件的真实流转记录")
    _refs["history"] = history
    form_layout.addWidget(history, 1)
    action_row = QHBoxLayout()
    action_row.addWidget(_wip_button("保存草稿"))
    action_row.addStretch()
    submit_btn = action_button("提交复核结果", "primary")

    def _submit() -> None:
        if not _state["event_id"]:
            QMessageBox.information(page.window(), "请选择任务", "请先在左侧任务队列点击「复核」选中一条事件。")
            return
        if not _has_action(api_client, "submit_review"):
            QMessageBox.information(page.window(), "离线模式", "Mock 模式下不写入真实复核结论。")
            return
        if radio_buttons[1].isChecked():
            decision = "rejected"
        elif radio_buttons[2].isChecked():
            decision = "pending"
        else:
            decision = "confirmed"
        try:
            api_client.submit_review(_state["event_id"], decision, note.toPlainText())
        except Exception as exc:  # pragma: no cover - UI path
            QMessageBox.warning(page.window(), "提交失败", str(exc))
            return
        history.addItem(f"刚刚 · 人工复核提交 · {decision} · {_state['event_id']}")
        QMessageBox.information(
            page.window(), "提交成功", f"已写入复核结论「{decision}」：{_state['title']}"
        )
        _state["event_id"] = ""
        if _refs.get("chip") is not None:
            _refs["chip"].setText("当前: 未选择")
        note.clear()
        _reload_queue()

    submit_btn.clicked.connect(_submit)
    action_row.addWidget(submit_btn)
    form_layout.addLayout(action_row)
    body.addWidget(form, 3)
    root.addLayout(body, 1)
    return page


def alerts_page(api_client: Any | None = None) -> QWidget:
    summary = _safe_call(api_client, "alerts_summary", {}) or {}
    page, root = page_shell("告警管理中心", "告警引擎在线 · 实时后端数据")
    metrics = QGridLayout()
    metrics.setSpacing(14)
    try:
        avg_txt = f"{float(summary.get('avg_response_minutes', 0) or 0):.1f} min"
    except (TypeError, ValueError):
        avg_txt = "—"
    metrics.addWidget(metric_card("未处理告警", str(summary.get("open_count", "—")), "Open", "#EF4444"), 0, 0)
    metrics.addWidget(metric_card("今日告警", str(summary.get("today_count", "—")), "Today", "#F59E0B"), 0, 1)
    metrics.addWidget(metric_card("已处理", str(summary.get("resolved_count", "—")), "Resolved", "#2563EB"), 0, 2)
    metrics.addWidget(metric_card("平均响应", avg_txt, "Efficiency", "#4F46E5"), 0, 3)
    root.addLayout(metrics)

    list_panel = panel()
    list_layout = QVBoxLayout(list_panel)
    list_layout.setContentsMargins(22, 20, 22, 20)
    list_layout.setSpacing(10)
    list_header = QHBoxLayout()
    list_header.addWidget(title("实时告警列表"))
    list_header.addStretch()
    refresh_btn = action_button("刷新")
    list_header.addWidget(refresh_btn)
    list_layout.addLayout(list_header)

    rows_host = QWidget()
    # Scope to this widget — a bare ``background: transparent`` cascades onto
    # descendant buttons and clobbers the primary 处置 button's blue fill.
    rows_host.setObjectName("alertsRowsHost")
    rows_host.setStyleSheet("#alertsRowsHost { background: transparent; }")
    rows_layout = QVBoxLayout(rows_host)
    rows_layout.setContentsMargins(0, 0, 0, 0)
    rows_layout.setSpacing(8)
    list_layout.addWidget(rows_host)

    sev_cn = {"high": "严重", "medium": "普通", "low": "低危"}
    sev_kind = {"high": "high", "medium": "mid", "low": "info"}
    status_cn = {"open": "待处理", "acknowledged": "处理中", "resolved": "已归档"}

    def _do(fn, alert_id: str, ok_msg: str) -> None:
        try:
            fn(alert_id)
            QMessageBox.information(page.window(), "操作成功", ok_msg)
        except Exception as exc:  # pragma: no cover - UI path
            QMessageBox.warning(page.window(), "操作失败", str(exc))
        _rebuild()

    def _rebuild() -> None:
        while rows_layout.count():
            item = rows_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        items = (_safe_call(api_client, "list_alerts", {}) or {}).get("items", [])
        if not items:
            rows_layout.addWidget(muted("暂无告警（或处于离线 / Mock 模式，连接真实后端后显示）"))
            return
        for a in items:
            row = QFrame()
            row.setStyleSheet(
                "QFrame{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;}"
                "QLabel{background:transparent;border:none;}"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(10)
            sev = a.get("severity", "")
            rl.addWidget(status_chip(sev_cn.get(sev, sev or "—"), sev_kind.get(sev, "info")))
            info = QVBoxLayout()
            t = QLabel(a.get("title", "事件"))
            t.setStyleSheet("color:#0F172A;font-size:13px;font-weight:700;")
            sub = QLabel(f"{str(a.get('created_at',''))[:19].replace('T',' ')} · {a.get('event_id','')}")
            sub.setStyleSheet("color:#64748B;font-size:11px;")
            info.addWidget(t)
            info.addWidget(sub)
            rl.addLayout(info, 1)
            st = a.get("status", "")
            rl.addWidget(status_chip(status_cn.get(st, st or "—"), "low" if st == "resolved" else "mid"))
            if st != "resolved" and _has_action(api_client, "ack_alert"):
                if st == "open":
                    ack = action_button("确认")
                    ack.clicked.connect(lambda _c=False, i=a.get("id", ""): _do(api_client.ack_alert, i, "已确认告警"))
                    rl.addWidget(ack)
                res = action_button("处置", "primary")
                res.clicked.connect(lambda _c=False, i=a.get("id", ""): _do(api_client.resolve_alert, i, "已处置告警"))
                rl.addWidget(res)
            rows_layout.addWidget(row)

    refresh_btn.clicked.connect(_rebuild)
    _rebuild()
    root.addWidget(list_panel, 2)

    lower = QHBoxLayout()
    lower.setSpacing(14)
    # 告警分级规则：展示后端 final_stage._severity 的真实判定逻辑，
    # 与上方告警列表里看到的严重度完全一致（不是虚构的「配置项」）。
    rules = panel()
    rules_layout = QVBoxLayout(rules)
    rules_layout.setContentsMargins(22, 20, 22, 20)
    rules_layout.addLayout(section_header("告警分级规则", "引擎内置 3 条"))
    for rule, desc in [
        ("高危 · 剐蹭 / 行人风险，或置信度 ≥ 85%", "命中后立即入告警队列，列表中标红"),
        ("普通 · 置信度 ≥ 70% 的其它风险事件", "入队列等待确认，列表中标黄"),
        ("低危 · 其余识别事件", "记录备查，复核确认后归档"),
    ]:
        rules_layout.addWidget(compact_card(rule, desc))
    rules_layout.addWidget(_wip_button("编辑告警规则", "primary"))
    lower.addWidget(rules, 2)

    type_dist = panel()
    type_layout = QVBoxLayout(type_dist)
    type_layout.setContentsMargins(22, 20, 22, 20)
    type_layout.addWidget(title("事件类型分布"))
    pie2 = CategoryPieChart()
    # 真实后端事件类型分布；离线 / Mock 或全空时回退示例
    _apal = ["#EF4444", "#F59E0B", "#4F46E5", "#22C55E", "#A855F7", "#0EA5E9", "#64748B"]
    _aitems = (_safe_call(api_client, "event_distribution", {}) or {}).get("items") or []
    if _aitems and any(int(it.get("count", 0) or 0) for it in _aitems):
        pie2.set_slices([
            PieSlice(
                str(it.get("label", "未知")),
                int(it.get("count", 0) or 0),
                _apal[i % len(_apal)],
            )
            for i, it in enumerate(_aitems[:7])
        ])
    else:
        pie2.set_slices([
            PieSlice("剧烈碰撞", 38, "#EF4444"),
            PieSlice("违规停靠", 29, "#F59E0B"),
            PieSlice("逆行行为", 21, "#4F46E5"),
            PieSlice("物体掉落", 12, "#22C55E"),
        ])
    type_layout.addWidget(pie2, 1)
    lower.addWidget(type_dist, 2)

    trend = panel()
    trend_layout = QVBoxLayout(trend)
    trend_layout.setContentsMargins(22, 20, 22, 20)
    trend_layout.addWidget(title("告警分级趋势 (近7日)"))
    chart = TrendBarChart()
    # 真实趋势：把告警列表按创建日期分桶，统计 高危数 / 当日总数。
    _alerts_all = (_safe_call(api_client, "list_alerts", {}) or {}).get("items", [])
    if _alerts_all:
        from datetime import date as _date, timedelta as _timedelta

        _buckets: dict[str, list[int]] = {}
        _order: list[str] = []
        for _off in range(6, -1, -1):
            _label = (_date.today() - _timedelta(days=_off)).strftime("%m-%d")
            _buckets[_label] = [0, 0]
            _order.append(_label)
        for _a in _alerts_all:
            _created = str(_a.get("created_at", ""))
            _label = f"{_created[5:7]}-{_created[8:10]}" if len(_created) >= 10 else ""
            if _label in _buckets:
                _buckets[_label][1] += 1
                if _a.get("severity") == "high":
                    _buckets[_label][0] += 1
        chart.set_points([
            BarPoint(_label, _buckets[_label][0], _buckets[_label][1], 0)
            for _label in _order
        ])
    else:
        chart.set_points([
            BarPoint("03-21", 4, 14, 0),
            BarPoint("03-22", 6, 18, 0),
            BarPoint("03-23", 5, 16, 0),
            BarPoint("03-24", 9, 22, 0),
            BarPoint("03-25", 7, 20, 0),
            BarPoint("03-26", 10, 24, 0),
            BarPoint("03-27", 12, 45, 0),
        ])
    trend_layout.addWidget(chart, 1)
    lower.addWidget(trend, 3)
    root.addLayout(lower, 2)
    return page


def accidents_page(api_client: Any | None = None) -> QWidget:
    page, root = page_shell("事故与风险发现面板", "业务视角的自动化事故摘要与态势分布（实时后端数据）")
    body = QHBoxLayout()
    body.setSpacing(14)

    feed_host = QWidget()
    # Scope so the transparent host doesn't cascade onto the primary
    # 重新生成摘要 button (would turn its blue fill transparent).
    feed_host.setObjectName("accidentsFeedHost")
    feed_host.setStyleSheet("#accidentsFeedHost { background: transparent; }")
    feed = QVBoxLayout(feed_host)
    feed.setContentsMargins(0, 0, 0, 0)
    feed.setSpacing(14)

    risk_accent = {"high": "#EF4444", "medium": "#F59E0B", "low": "#22C55E"}
    risk_kind = {"high": "high", "medium": "mid", "low": "low"}
    risk_cn = {"high": "高危", "medium": "中危", "low": "低危"}

    def _summarize(acc_id: str, label: QLabel) -> None:
        try:
            res = api_client.generate_accident_summary(acc_id) or {}
            label.setText(res.get("summary", "") or "（已生成）")
            QMessageBox.information(page.window(), "摘要已生成", "大模型事故摘要已更新。")
        except Exception as exc:  # pragma: no cover - UI path
            QMessageBox.warning(page.window(), "生成失败", str(exc))

    items = (_safe_call(api_client, "list_accidents", {}) or {}).get("items", [])
    if not items:
        feed.addWidget(muted("暂无事故 / 风险记录（或处于离线 / Mock 模式，连接真实后端后显示）。"))
    for a in items:
        risk = a.get("risk_level", "medium")
        accent = risk_accent.get(risk, "#F59E0B")
        card = QFrame()
        card.setProperty("role", "panel")
        card.setStyleSheet(
            f"QFrame[role='panel'] {{ background:#FFFFFF; border:1px solid #E2E8F0; "
            f"border-radius:18px; border-left:5px solid {accent}; }}"
            "QLabel { background:transparent; border:none; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 18, 22, 18)
        top = QHBoxLayout()
        icon_lbl = QLabel("⚠")
        icon_lbl.setStyleSheet(f"color:{accent}; font-size:20px; padding-right:6px;")
        title_label = QLabel(a.get("title", "风险事件"))
        title_label.setStyleSheet("color:#0F172A;font-size:16px;font-weight:800;")
        title_label.setWordWrap(True)
        top.addWidget(icon_lbl)
        top.addWidget(title_label, 1)
        top.addWidget(status_chip(risk_cn.get(risk, "风险"), risk_kind.get(risk, "mid")))
        layout.addLayout(top)
        time_row = QHBoxLayout()
        time_row.addWidget(muted(f"{str(a.get('created_at',''))[:19].replace('T',' ')} · {a.get('event_id','')}"))
        time_row.addStretch()
        layout.addLayout(time_row)
        summary_title = QLabel("大语言模型自动浓缩摘要")
        summary_title.setStyleSheet(f"color:{accent};font-size:12px;font-weight:700;")
        layout.addWidget(summary_title)
        summary_lbl = muted(a.get("summary", "") or "（点击下方按钮生成摘要）")
        layout.addWidget(summary_lbl)
        actions = QHBoxLayout()
        if _has_action(api_client, "generate_accident_summary"):
            gen = action_button("重新生成摘要", "primary")
            gen.clicked.connect(lambda _c=False, i=a.get("id", ""), lbl=summary_lbl: _summarize(i, lbl))
            actions.addWidget(gen)
        actions.addWidget(_wip_button("建立证据包并归档"))
        actions.addStretch()
        layout.addLayout(actions)
        feed.addWidget(card)
    feed.addStretch()
    body.addWidget(feed_host, 3)

    side = dark_panel()
    side_layout = QVBoxLayout(side)
    side_layout.setContentsMargins(22, 20, 22, 20)
    side_layout.setSpacing(14)
    heat_title = QLabel("风险等级分布（实时）")
    heat_title.setStyleSheet("color:#CBD5E1;font-size:12px;font-weight:800;letter-spacing:1px;")
    side_layout.addWidget(heat_title)
    # 由真实事故列表统计风险等级占比（系统没有 GPS 数据，不展示虚构的区域热力）。
    _risk_counts = {"high": 0, "medium": 0, "low": 0}
    for _a in items:
        _risk_counts[_a.get("risk_level", "medium")] = (
            _risk_counts.get(_a.get("risk_level", "medium"), 0) + 1
        )
    heat = QLabel(
        f"高危事故     {_risk_counts['high']:>4} 起\n"
        f"中危事故     {_risk_counts['medium']:>4} 起\n"
        f"低危事故     {_risk_counts['low']:>4} 起\n"
        f"累计风险事件 {len(items):>4} 起"
    )
    heat.setStyleSheet("color:#E2E8F0;font-size:14px;line-height:1.6;")
    side_layout.addWidget(heat)
    _rep = _safe_call(api_client, "daily_report", {}) or {}
    _risk_text = _rep.get("risk_summary") or (
        "连接真实后端后，这里显示由当日事件聚合生成的风险总结。"
    )
    side_layout.addWidget(compact_card("全局风险指征（当日实时）", _risk_text, "#F59E0B"))
    side_layout.addStretch()
    side_layout.addWidget(_wip_button("查看全天业务报告", "primary"))
    body.addWidget(side, 2)
    root.addLayout(body, 1)
    return page


def evidence_page(api_client: Any | None = None) -> QWidget:
    page, root = page_shell("证据与日志归档", "真实导出记录与操作审计日志（实时后端数据）")

    exports_data = (_safe_call(api_client, "list_exports", {}) or {}).get("items", [])
    logs_data = (_safe_call(api_client, "list_audit_logs", {}) or {}).get("items", [])

    controls = panel()
    controls_layout = QHBoxLayout(controls)
    controls_layout.setContentsMargins(22, 16, 22, 16)
    search = QLineEdit()
    search.setPlaceholderText("按导出ID / 事件ID / 文件路径过滤……")
    controls_layout.addWidget(search, 1)
    controls_layout.addWidget(_wip_button("打包备份归档", "primary"))
    root.addWidget(controls)

    body = QHBoxLayout()
    body.setSpacing(14)
    left = QVBoxLayout()

    from datetime import date as _date

    _today = _date.today().isoformat()
    _today_count = sum(
        1 for it in exports_data if str(it.get("created_at", ""))[:10] == _today
    )
    _ok_count = sum(1 for it in exports_data if it.get("status") in ("success", "completed"))
    stats = QGridLayout()
    stats.setSpacing(14)
    stats.addWidget(metric_card("今日新增证据", f"{_today_count} 卷", "ffmpeg 切片+截图+摘要"), 0, 0)
    stats.addWidget(metric_card("累计固证", f"{len(exports_data)} 卷", "media/exports 下可解压"), 0, 1)
    stats.addWidget(metric_card("导出成功", f"{_ok_count} 卷", "24h 内重复导出自动复用", "#4F46E5"), 0, 2)
    left.addLayout(stats)

    queue = panel()
    queue_layout = QVBoxLayout(queue)
    queue_layout.setContentsMargins(22, 18, 22, 18)
    queue_layout.addLayout(section_header("证据导出记录", f"共 {len(exports_data)} 卷"))
    rows_host = QWidget()
    rows_host.setObjectName("evidenceRowsHost")
    rows_host.setStyleSheet("#evidenceRowsHost { background: transparent; }")
    rows_layout = QVBoxLayout(rows_host)
    rows_layout.setContentsMargins(0, 0, 0, 0)
    rows_layout.setSpacing(8)

    def _render_exports(keyword: str = "") -> None:
        while rows_layout.count():
            item = rows_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        kw = keyword.strip().lower()
        shown = [
            it for it in exports_data
            if not kw or kw in " ".join(
                str(it.get(k, "")) for k in ("id", "event_id", "export_path")
            ).lower()
        ]
        if not shown:
            rows_layout.addWidget(muted(
                "暂无匹配的导出记录。在「检索」页选中事件点「导出证据包」后，"
                "记录会实时出现在这里（离线 / Mock 模式不展示）。"
            ))
        for it in shown:
            created = str(it.get("created_at", ""))[:19].replace("T", " ")
            row = QHBoxLayout()
            row.addWidget(compact_card(
                f"{it.get('event_id', '')} · {it.get('export_type', 'package')}",
                f"{created} 生成 · {it.get('export_path', '')}",
            ), 1)
            ok = it.get("status") in ("success", "completed")
            row.addWidget(status_chip("已固证" if ok else str(it.get("status", "—")),
                                      "low" if ok else "mid"))
            row_w = QWidget()
            row_w.setStyleSheet("background: transparent;")
            row_w.setLayout(row)
            rows_layout.addWidget(row_w)
        rows_layout.addStretch()

    _render_exports()
    search.textChanged.connect(_render_exports)

    rows_scroll = QScrollArea()
    rows_scroll.setWidget(rows_host)
    rows_scroll.setWidgetResizable(True)
    rows_scroll.setFrameShape(QFrame.Shape.NoFrame)
    rows_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    queue_layout.addWidget(rows_scroll, 1)
    left.addWidget(queue, 1)
    body.addLayout(left, 3)

    log_panel = panel()
    log_layout = QVBoxLayout(log_panel)
    log_layout.setContentsMargins(22, 18, 22, 18)
    log_layout.addLayout(section_header("系统审计日志", f"最近 {len(logs_data)} 条"))
    logs = QListWidget()
    if logs_data:
        _action_cn = {
            "auth.login": "登录鉴权",
            "video.upload": "视频上传",
            "video.process": "视频处理",
            "search.query": "语义检索",
            "event.export": "证据导出",
            "review.decision": "复核结论",
            "report.export": "日报导出",
            "alert.ack": "告警确认",
            "alert.resolve": "告警处置",
        }
        for entry in logs_data:
            created = str(entry.get("created_at", ""))[:19].replace("T", " ")
            action = str(entry.get("action", ""))
            target = f"{entry.get('target_type', '')}:{entry.get('target_id', '')}".strip(":")
            message = str(entry.get("message", ""))[:60]
            logs.addItem(
                f"{created} · {_action_cn.get(action, action)} · {target} · {message}"
            )
    else:
        logs.addItem("暂无可见日志（需要 admin / reviewer 权限，或处于离线 / Mock 模式）")
    log_layout.addWidget(logs, 1)
    body.addWidget(log_panel, 2)
    root.addLayout(body, 1)
    return page


def daily_report_page(api_client: Any | None = None) -> QWidget:
    report = _safe_call(api_client, "daily_report", {}) or {}

    def _n(key: str, default: int) -> str:
        v = report.get(key, default)
        try:
            return f"{int(v):,}"
        except (TypeError, ValueError):
            return str(v)

    date_txt = report.get("date", "今日")
    page, root = page_shell("全天业务报告", f"{date_txt} 业务汇总与趋势分析（实时后端数据）")
    metrics = QGridLayout()
    metrics.setSpacing(14)
    metrics.addWidget(metric_card("处理视频", _n("processed_video_count", 127), date_txt), 0, 0)
    metrics.addWidget(metric_card("关键事件", _n("identified_event_count", 342), date_txt), 0, 1)
    metrics.addWidget(metric_card("检索次数", _n("semantic_query_count", 1204), date_txt), 0, 2)
    metrics.addWidget(metric_card("导出证据", _n("evidence_export_count", 89), date_txt, "#F59E0B"), 0, 3)
    root.addLayout(metrics)

    body = QHBoxLayout()
    body.setSpacing(14)
    left = QVBoxLayout()
    trend = panel()
    trend_layout = QVBoxLayout(trend)
    trend_layout.setContentsMargins(22, 20, 22, 20)
    trend_layout.addLayout(section_header("事件识别趋势 (7日)", "报告生成时间: 23:59"))
    chart = TrendBarChart()
    _tr = _safe_call(api_client, "dashboard_trends", {}) or {}
    _td = _tr.get("days") or []
    _tev = _tr.get("event_counts") or []
    _tq = _tr.get("query_counts") or []
    _tl = _tr.get("worker_load") or []
    if _td and (any(_tev) or any(_tq)):
        chart.set_points([
            BarPoint(
                _td[i],
                int(_tev[i]) if i < len(_tev) else 0,
                int(_tq[i]) if i < len(_tq) else 0,
                int(float(_tl[i]) * 100) if i < len(_tl) else 0,
            )
            for i in range(len(_td))
        ])
    else:
        chart.set_points([
            BarPoint("03-21", 120, 28, 0),
            BarPoint("03-22", 138, 31, 0),
            BarPoint("03-23", 146, 34, 0),
            BarPoint("03-24", 160, 37, 0),
            BarPoint("03-25", 174, 41, 0),
            BarPoint("03-26", 188, 45, 0),
            BarPoint("03-27", 204, 52, 0),
        ])
    trend_layout.addWidget(chart, 1)
    left.addWidget(trend, 2)

    dist = panel()
    dist_layout = QVBoxLayout(dist)
    dist_layout.setContentsMargins(22, 20, 22, 20)
    dist_layout.addWidget(title("事件类型分布"))
    _dpal = ["#EF4444", "#F59E0B", "#2563EB", "#22C55E", "#A855F7", "#64748B"]
    _ditems = (_safe_call(api_client, "event_distribution", {}) or {}).get("items") or []
    _dtotal = sum(int(it.get("count", 0) or 0) for it in _ditems)
    if _ditems and _dtotal > 0:
        dist_rows = [
            (str(it.get("label", "未知")),
             round(int(it.get("count", 0) or 0) * 100 / _dtotal),
             _dpal[i % len(_dpal)])
            for i, it in enumerate(_ditems[:5])
        ]
    else:
        dist_rows = [
            ("侧向碰撞", 45, "#EF4444"),
            ("行人鬼探头", 30, "#F59E0B"),
            ("违停", 15, "#2563EB"),
            ("其他", 10, "#64748B"),
        ]
    for name, pct_int, color in dist_rows:
        row = QHBoxLayout()
        name_lbl = muted(name)
        pct_lbl = QLabel(f"{pct_int}%")
        pct_lbl.setStyleSheet(f"color:{color};font-weight:800;font-size:12px;")
        pct_lbl.setFixedWidth(38)
        row.addWidget(name_lbl)
        row.addWidget(pct_lbl)
        dist_layout.addLayout(row)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(pct_int)
        bar.setTextVisible(False)
        bar.setFixedHeight(6)
        bar.setStyleSheet(
            f"QProgressBar {{ background:#E2E8F0; border-radius:3px; border:none; }}"
            f"QProgressBar::chunk {{ background:{color}; border-radius:3px; }}"
        )
        dist_layout.addWidget(bar)
    left.addWidget(dist, 1)
    body.addLayout(left, 3)

    right = QVBoxLayout()
    # 真实视频源统计（系统没有 GPS 区域数据，不展示虚构的区域分布）。
    region = dark_panel()
    region_layout = QVBoxLayout(region)
    region_layout.setContentsMargins(22, 20, 22, 20)
    region_title = QLabel("视频源统计（实时）")
    region_title.setStyleSheet("color:#CBD5E1;font-size:12px;font-weight:800;letter-spacing:1px;")
    region_layout.addWidget(region_title)
    _vids = sorted(
        list(_safe_call(api_client, "list_videos", ()) or ()),
        key=lambda v: getattr(v, "duration_sec", 0) or 0,
        reverse=True,
    )
    if _vids:
        _v_lines = []
        for _v in _vids[:4]:
            _vm = int((getattr(_v, "duration_sec", 0) or 0) / 60)
            _vt = str(getattr(_v, "title", "未命名"))
            _vt = _vt if len(_vt) <= 14 else _vt[:13] + "…"
            _vs = "可检索" if str(getattr(_v, "status", "")) == "indexed" else str(getattr(_v, "status", "—"))
            _v_lines.append(f"{_vt}    {_vm} 分钟 · {_vs}")
        region_stats = QLabel("\n".join(_v_lines))
    else:
        region_stats = QLabel("视频库为空，上传后这里显示真实视频源。")
    region_stats.setStyleSheet("color:#E2E8F0;font-size:14px;line-height:1.6;")
    region_layout.addWidget(region_stats)
    right.addWidget(region, 1)

    summary = panel()
    summary_layout = QVBoxLayout(summary)
    summary_layout.setContentsMargins(22, 20, 22, 20)
    summary_layout.addWidget(title("业务总结"))
    summary_text = report.get("risk_summary") or (
        "系统运行稳定。连接真实后端后，本段展示由当日事件聚合得到的风险总结。"
    )
    summary_layout.addWidget(muted(summary_text))
    if _has_action(api_client, "export_daily_report"):
        export_btn = action_button("导出日报", "primary")

        def _export() -> None:
            try:
                res = api_client.export_daily_report() or {}
                path = res.get("export_path", "") if isinstance(res, dict) else ""
                QMessageBox.information(page.window(), "导出成功", f"全天业务日报已生成：\n{path}")
            except Exception as exc:  # pragma: no cover - UI path
                QMessageBox.warning(page.window(), "导出失败", str(exc))

        export_btn.clicked.connect(_export)
        summary_layout.addWidget(export_btn)
    else:
        summary_layout.addWidget(_wip_button("导出PDF报告", "primary"))
    right.addWidget(summary, 1)
    body.addLayout(right, 2)
    root.addLayout(body, 1)
    return page


def settings_page(api_client: Any | None = None) -> QWidget:
    model_cfg = _safe_call(api_client, "model_settings", {}) or {}
    sec_cfg = _safe_call(api_client, "security_settings", {}) or {}
    page, root = page_shell("系统参数与模型配置", "模型、存储与接口安全策略（实时后端配置）")
    body = QVBoxLayout()
    body.setSpacing(14)

    def _ro(text: str) -> QLineEdit:
        edit = QLineEdit(str(text) if text not in (None, "") else "—")
        edit.setReadOnly(True)
        return edit

    model = panel()
    model_layout = QVBoxLayout(model)
    model_layout.setContentsMargins(22, 20, 22, 20)
    model_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    model_layout.addWidget(title("多模态大模型引擎 (LLM/VLM)"))
    model_layout.addWidget(muted("用于视频帧理解与语义标签生成的底层模型接口（后端实时配置）。"))
    model_layout.addWidget(muted("模型服务商 / 模型"))
    model_layout.addWidget(_ro(f"{model_cfg.get('provider','—')} · {model_cfg.get('model_name','—')}"))
    model_layout.addWidget(muted("API Endpoint"))
    model_layout.addWidget(_ro(model_cfg.get("base_url", "—")))
    model_layout.addWidget(muted("模型 API Key 状态"))
    key_ok = bool(model_cfg.get("api_key_configured", False))
    model_layout.addWidget(status_chip(
        "已配置（仅本机环境变量，界面不回传明文）" if key_ok else "未配置 · 走 Mock 规则分析",
        "low" if key_ok else "mid",
    ))
    body.addWidget(model)

    pipeline = panel()
    pipe_layout = QVBoxLayout(pipeline)
    pipe_layout.setContentsMargins(22, 20, 22, 20)
    pipe_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    pipe_layout.addWidget(title("存储与向量检索"))
    pipe_layout.addWidget(muted("向量嵌入策略"))
    pipe_layout.addWidget(status_chip(
        "sentence-transformers 真实嵌入" if model_cfg.get("use_embeddings") else "哈希向量降级（默认，离线可复现）",
        "low" if model_cfg.get("use_embeddings") else "info",
    ))
    pipe_layout.addWidget(muted("数据库引擎"))
    pipe_layout.addWidget(_ro(model_cfg.get("db_engine", "—")))
    pipe_layout.addWidget(muted("存储根目录 (Media Root)"))
    pipe_layout.addWidget(_ro(model_cfg.get("media_root", "—")))
    body.addWidget(pipeline)

    security = panel()
    sec_layout = QVBoxLayout(security)
    sec_layout.setContentsMargins(22, 20, 22, 20)
    sec_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    sec_layout.addWidget(title("接口安全鉴权 (Security)"))
    sec_layout.addWidget(status_chip(
        f"Bearer Token {'启用' if sec_cfg.get('bearer_auth_enabled', True) else '关闭'}", "low"))
    sec_layout.addWidget(status_chip(
        f"操作审计 {'启用' if sec_cfg.get('audit_enabled', True) else '关闭'}", "low"))
    sec_layout.addWidget(muted(f"令牌有效期：{sec_cfg.get('jwt_ttl_min', '—')} 分钟"))
    sec_layout.addWidget(muted(f"已配置角色：{', '.join(sec_cfg.get('roles', [])) or '—'}"))
    sec_layout.addStretch()
    sec_layout.addWidget(_wip_button("保存所有全局设置", "primary"))
    body.addWidget(security)
    root.addLayout(body, 1)
    return page


def roles_page(api_client: Any | None = None) -> QWidget:
    page, root = page_shell("角色与权限管理", "角色 / 权限 / 用户维护（实时后端数据）")

    roles_data = (_safe_call(api_client, "list_roles", {}) or {}).get("items", [])
    users_data = (_safe_call(api_client, "list_users", {}) or {}).get("items", [])
    _counts: dict[str, int] = {}
    for _u in users_data:
        _counts[_u.get("role", "")] = _counts.get(_u.get("role", ""), 0) + 1

    hdr_row = QHBoxLayout()
    hdr_row.addWidget(muted(f"共 {len(roles_data) or '—'} 个角色 · {len(users_data)} 个用户"))
    hdr_row.addStretch()
    hdr_row.addWidget(_wip_button("新增用户", "primary"))
    root.addLayout(hdr_row)

    roles_layout = QHBoxLayout()
    roles_layout.setSpacing(14)

    _accents = ["#2563EB", "#F59E0B", "#EF4444", "#16A34A", "#7C3AED"]
    _role_rows: list = []
    for _i, _r in enumerate(roles_data):
        _rid = _r.get("id", "")
        _perms = _r.get("permissions", [])
        if _perms == ["*"]:
            _perm_pairs = [("✓ 全部权限（管理员）", True)]
        else:
            _perm_pairs = [(f"✓ {p}", True) for p in _perms[:6]]
        _role_rows.append((
            (_r.get("name", _rid), _rid.upper(), (_rid[:1] or "?").upper(),
             f"系统角色 {_rid}，共 {len(_perms)} 项权限。", "用户数",
             str(_counts.get(_rid, 0)), _accents[_i % len(_accents)], "#EFF6FF"),
            _perm_pairs,
        ))
    if not _role_rows:  # offline / mock fallback
        _role_rows = [
            (("管理员", "ADMIN", "A", "系统管理员，全部权限。", "用户数", "1", "#2563EB", "#EFF6FF"),
             [("✓ 全部权限（管理员）", True)]),
            (("审核人员", "REVIEWER", "R", "复核与审计权限。", "用户数", "1", "#F59E0B", "#FFFBEB"),
             [("✓ 事件复核", True), ("✓ 审计日志查看", True), ("✗ 用户管理", False)]),
            (("普通用户", "USER", "U", "检索 / 上传 / 导出权限。", "用户数", "1", "#16A34A", "#F0FDF4"),
             [("✓ 视频上传", True), ("✓ 语义检索", True), ("✗ 审计日志查看", False)]),
        ]

    for (name, code, letter, desc, users, count, accent, bg), perms in _role_rows:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame[role='panel'] {{ background:#FFFFFF; border:1px solid #E2E8F0; "
            f"border-radius:20px; border-top:4px solid {accent}; }}"
            "QLabel { background:transparent; border:none; }"
        )
        card.setProperty("role", "panel")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(10)

        # Badge + title row
        top = QHBoxLayout()
        badge = QLabel(letter)
        badge.setFixedSize(44, 44)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"QLabel {{ background:{accent}; color:#FFFFFF; border-radius:12px; "
            f"font-size:20px; font-weight:900; border:none; }}"
        )
        top.addWidget(badge)
        title_col = QVBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color:{accent}; font-size:14px; font-weight:800;")
        code_lbl = QLabel(code)
        code_lbl.setStyleSheet("color:#94A3B8; font-size:11px; font-weight:600; letter-spacing:0.5px;")
        title_col.addWidget(name_lbl)
        title_col.addWidget(code_lbl)
        top.addLayout(title_col)
        top.addStretch()
        cl.addLayout(top)

        desc_lbl = muted(desc)
        cl.addWidget(desc_lbl)

        # Permission list
        for perm_text, allowed in perms:
            perm_row = QHBoxLayout()
            dot = QLabel("✓" if allowed else "✗")
            dot.setStyleSheet(
                f"color:{'#22C55E' if allowed else '#94A3B8'}; font-weight:700; font-size:13px;"
            )
            dot.setFixedWidth(18)
            txt = QLabel(perm_text[2:])  # strip "✓ " or "✗ "
            txt.setStyleSheet(f"color:{'#374151' if allowed else '#94A3B8'}; font-size:12px;")
            perm_row.addWidget(dot)
            perm_row.addWidget(txt)
            perm_row.addStretch()
            cl.addLayout(perm_row)

        cl.addStretch()
        cl.addWidget(_wip_button(f"{users} ({count})"))
        roles_layout.addWidget(card)

    root.addLayout(roles_layout)

    matrix = panel()
    matrix_layout = QVBoxLayout(matrix)
    matrix_layout.setContentsMargins(22, 20, 22, 20)
    header = section_header("功能模块权限矩阵 (Matrix)")
    header.addWidget(_wip_button("批量同步", "primary"))
    header.addWidget(_wip_button("导出记录"))
    matrix_layout.addLayout(header)

    # 真实权限矩阵：行 = 后端权限目录（/api/permissions），列 = 真实角色，
    # 单元格按各角色的 permissions 列表逐项判定。离线 / Mock 回退示例表。
    _PERM_CN = {
        "audit:read": "审计日志查看",
        "event:export": "证据导出",
        "event:read": "事件查看",
        "event:review": "事件复核",
        "export:read": "导出记录查看",
        "search:create": "语义检索",
        "settings:read": "系统配置查看",
        "user:read": "用户查看",
        "video:process": "视频处理",
        "video:read": "视频查看",
        "video:upload": "视频上传",
    }
    _PERM_RISK = {
        "audit:read": "HIGH",
        "event:review": "MED",
        "video:process": "MED",
        "user:read": "MED",
        "settings:read": "MED",
        "event:export": "MED",
    }
    perm_catalog = (_safe_call(api_client, "list_permissions", {}) or {}).get("permissions", [])
    if perm_catalog and roles_data:
        headers = (
            ["功能模块 / 权限点"]
            + [str(r.get("name", r.get("id", "?"))) for r in roles_data]
            + ["风险等级"]
        )
        matrix_rows = []
        for perm in perm_catalog:
            row_cells = [f"{_PERM_CN.get(perm, perm)} ({perm})"]
            for r in roles_data:
                perms = r.get("permissions", [])
                allowed = "*" in perms or perm in perms
                row_cells.append("✓ 允许" if allowed else "✗ 禁止")
            row_cells.append(_PERM_RISK.get(perm, "LOW"))
            matrix_rows.append(row_cells)
        tbl = table(headers, matrix_rows)
    else:
        tbl = table(
            ["功能模块 / 权限点", "管理员", "审核人员", "普通用户", "风险等级"],
            [
                ["语义检索 (search:create)", "✓ 允许", "✗ 禁止", "✓ 允许", "LOW"],
                ["事件复核 (event:review)", "✓ 允许", "✓ 允许", "✗ 禁止", "MED"],
                ["证据导出 (event:export)", "✓ 允许", "✗ 禁止", "✓ 允许", "MED"],
                ["审计日志查看 (audit:read)", "✓ 允许", "✓ 允许", "✗ 禁止", "HIGH"],
            ],
        )
    # Color cells
    _perm_colors = {"✓ 允许": "#15803D", "✗ 禁止": "#9CA3AF"}
    _risk_colors = {"LOW": "#15803D", "MED": "#B45309", "HIGH": "#B91C1C", "CRITICAL": "#7C3AED"}
    for row in range(tbl.rowCount()):
        for col in range(1, tbl.columnCount()):
            item = tbl.item(row, col)
            if item:
                text = item.text()
                from PySide6.QtGui import QColor, QBrush
                color = _risk_colors.get(text) or _perm_colors.get(text)
                if color:
                    item.setForeground(QBrush(QColor(color)))

    matrix_layout.addWidget(tbl)
    root.addWidget(matrix, 1)
    return page


def login_page() -> QWidget:
    page = QWidget()
    page.setStyleSheet("QWidget { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                       "stop:0 #0F172A, stop:1 #1E293B); }")
    root = QHBoxLayout(page)
    root.setContentsMargins(160, 90, 160, 90)
    root.setSpacing(0)
    root.addStretch()
    login = QFrame()
    login.setFixedWidth(460)
    login.setStyleSheet(
        "QFrame { background: rgba(15,23,42,0.96); border: 1px solid rgba(255,255,255,0.10);"
        " border-radius: 28px; }"
        "QLabel { background: transparent; border: none; color: #E2E8F0; }"
        "QLineEdit { background: #1E293B; border: 1px solid #334155; border-radius: 10px;"
        " color: #F1F5F9; padding: 10px 14px; font-size: 14px; }"
        "QPushButton[role='role-btn'] { background: #1E293B; border: 1px solid #334155;"
        " border-radius: 10px; color: #94A3B8; font-size: 12px; padding: 8px 16px; }"
        "QPushButton[role='role-btn'][selected='true'] { background: #2563EB; border-color: #2563EB;"
        " color: #FFFFFF; font-weight: 700; }"
    )
    layout = QVBoxLayout(login)
    layout.setContentsMargins(34, 32, 34, 32)
    layout.setSpacing(14)
    logo = QLabel("📷 DVR-S")
    logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
    logo.setStyleSheet("color:#FFFFFF;font-size:28px;font-weight:900;letter-spacing:4px;"
                       "background:transparent;border:none;")
    layout.addWidget(logo)
    subtitle = muted("多模态行车记录仪视频语义检索与精准回放系统")
    subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(subtitle)
    layout.addSpacing(8)

    # Role selector chips
    role_row = QHBoxLayout()
    role_row.setSpacing(8)
    _role_btns = []
    for role_name in ["巡查员", "车队管理", "驾驶员"]:
        rb = QPushButton(role_name)
        rb.setProperty("role", "role-btn")
        _role_btns.append(rb)
        role_row.addWidget(rb)

    def _select_role(btn: QPushButton) -> None:
        for b in _role_btns:
            b.setProperty("selected", "false")
            b.style().unpolish(b)
            b.style().polish(b)
        btn.setProperty("selected", "true")
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    for rb in _role_btns:
        rb.clicked.connect(lambda checked=False, b=rb: _select_role(b))
    _role_btns[0].setProperty("selected", "true")
    layout.addLayout(role_row)
    layout.addSpacing(8)

    layout.addWidget(muted("工号 / 手机号 (Account)"))
    layout.addWidget(QLineEdit("admin"))
    layout.addWidget(muted("安全登录密码 (Password)"))
    password = QLineEdit()
    password.setPlaceholderText("密码")
    password.setEchoMode(QLineEdit.EchoMode.Password)
    layout.addWidget(password)
    row = QHBoxLayout()
    remember = QCheckBox("记住登录状态")
    row.addWidget(remember)
    row.addStretch()
    row.addWidget(muted("忘记密码？"))
    layout.addLayout(row)
    signin = action_button("安全登录 (Sign In)", "primary")
    signin.setMinimumHeight(44)
    layout.addWidget(signin)

    # Compliance footer chips
    compliance_row = QHBoxLayout()
    compliance_row.setSpacing(6)
    for chip_text in ["🔒 OAuth2.0", "🔐 TLS 1.3", "📋 Audit Log"]:
        chip = QLabel(chip_text)
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip.setStyleSheet(
            "QLabel { background: rgba(37,99,235,0.18); color: #93C5FD;"
            " border: 1px solid rgba(147,197,253,0.25); border-radius: 999px;"
            " padding: 3px 10px; font-size: 10px; font-weight: 700; }"
        )
        compliance_row.addWidget(chip)
    layout.addLayout(compliance_row)

    footer = QLabel("© 2026 DVR-Semantic System. All Rights Reserved.")
    footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
    footer.setStyleSheet("color:#475569;font-size:11px;background:transparent;border:none;")
    layout.addWidget(footer)
    root.addWidget(login)
    root.addStretch()
    return page
