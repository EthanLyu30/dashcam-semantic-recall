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
    route = panel()
    route_layout = QVBoxLayout(route)
    route_layout.setContentsMargins(22, 20, 22, 20)
    route_layout.addLayout(section_header("实时车辆轨迹状态", "实时速度 45 km/h"))
    route_layout.addWidget(muted("当前位置: 深南大道科苑段 · 起始: 14:15:00 科技园站 · 预达: 14:25:30 车公庙站 · 里程: 4.2 km"))
    route_info = QLabel("📍 深南大道科苑段  →  车公庙站  |  45 km/h  |  行程 48%")
    route_info.setStyleSheet(
        "color:#2563EB;font-size:13px;font-weight:700;"
        "background:#EFF6FF;border:1px solid #BFDBFE;"
        "border-radius:10px;padding:8px 14px;"
    )
    route_layout.addWidget(route_info)
    route_bar = QProgressBar()
    route_bar.setRange(0, 100)
    route_bar.setValue(48)
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
    review_layout.addLayout(section_header("待复核实时动态", "12 待处理"))
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

        stats = QHBoxLayout()
        stats.setSpacing(10)
        for label, value, note, accent in [
            ("全部视频", "3,482", "车队库总量", "#2563EB"),
            ("正在处理中", "18", "识别队列 65%", "#2563EB"),
            ("待人工复核", "24", "低置信片段", "#F59E0B"),
            ("处理失败", "3", "等待重试", "#EF4444"),
            ("已完成结构化", "3,421", "可检索", "#22C55E"),
        ]:
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
        filename = QLineEdit()
        filename.setPlaceholderText("文件名 / VideoID，例如 VID_2026...")
        status = QComboBox()
        status.addItems(["全部状态", "已完成识别", "正在识别", "待人工复核", "处理失败"])
        vehicle = QLineEdit()
        vehicle.setPlaceholderText("车队 / 车辆编号")
        date_start = QLineEdit()
        date_start.setPlaceholderText("开始日期 2026-03-01")
        filter_layout.addWidget(filename, 2)
        filter_layout.addWidget(status, 1)
        filter_layout.addWidget(vehicle, 1)
        filter_layout.addWidget(date_start, 1)
        filter_layout.addWidget(_wip_button("查询", "primary"))
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
            ["Video ID / 文件名", "上传时间", "处理状态", "关键事件", "负责人", "操作"]
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

    def refresh(self) -> None:
        try:
            videos = self._api_client.list_videos()
        except Exception as exc:
            QMessageBox.warning(self, "加载失败", f"无法读取视频列表：\n{exc}")
            return

        self.video_table.setRowCount(len(videos))
        for row, video in enumerate(videos):
            mm, ss = divmod(int(getattr(video, "duration_sec", 0) or 0), 60)
            duration = f"{mm:02d}:{ss:02d}"
            cells = [
                f"{getattr(video, 'id', '')}\n{getattr(video, 'title', '')}",
                "2026-03-27 14:00",
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


def review_page() -> QWidget:
    page, root = page_shell("人工复核中心", "2026年03月27日 · 审核员 reviewer01 · 低置信事件确认")

    body = QHBoxLayout()
    body.setSpacing(14)

    queue = panel()
    queue_layout = QVBoxLayout(queue)
    queue_layout.setContentsMargins(22, 20, 22, 20)
    queue_layout.setSpacing(10)
    queue_header = QHBoxLayout()
    queue_header.addWidget(title("任务队列"))
    queue_header.addStretch()
    queue_header.addWidget(status_chip("剩余 12", "high"))
    queue_layout.addLayout(queue_header)
    queue_layout.addWidget(muted("置信度 < 80% 自动入队，紧急事件置顶"))
    tasks_widget = QWidget()
    tasks_inner = QVBoxLayout(tasks_widget)
    tasks_inner.setContentsMargins(0, 0, 0, 0)
    tasks_inner.setSpacing(6)
    for priority, plate, event, conf, time_str, kind in [
        ("紧急", "沪A·88888", "疑似路口碰撞事件", "68%", "03-27 10:22", "high"),
        ("普通", "粤B·00001", "违章掉头识别", "72%", "03-27 11:15", "mid"),
        ("普通", "—", "施工围挡占道检测", "79%", "14:22–14:23", "mid"),
        ("普通", "—", "异常停车与连续鸣笛", "74%", "09:15–09:16", "mid"),
        ("存疑", "—", "夜间逆行行为记录", "71%", "21:08–21:09", "info"),
    ]:
        item_frame = QFrame()
        item_frame.setStyleSheet(
            "QFrame { background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; }"
            "QLabel { background:transparent; border:none; }"
        )
        item_lay = QHBoxLayout(item_frame)
        item_lay.setContentsMargins(10, 8, 10, 8)
        item_lay.setSpacing(8)
        item_lay.addWidget(status_chip(priority, kind))
        info = QVBoxLayout()
        top_lbl = QLabel(f"{plate}  {event}")
        top_lbl.setStyleSheet("color:#0F172A;font-size:12px;font-weight:700;")
        bot_lbl = QLabel(f"置信度 {conf} · {time_str}")
        bot_lbl.setStyleSheet("color:#64748B;font-size:11px;")
        info.addWidget(top_lbl)
        info.addWidget(bot_lbl)
        item_lay.addLayout(info, 1)
        tasks_inner.addWidget(item_frame)
    tasks_inner.addStretch()
    tasks_scroll = QScrollArea()
    tasks_scroll.setWidget(tasks_widget)
    tasks_scroll.setWidgetResizable(True)
    tasks_scroll.setFrameShape(QFrame.Shape.NoFrame)
    queue_layout.addWidget(tasks_scroll, 1)
    body.addWidget(queue, 2)

    workbench = dark_panel()
    workbench_layout = QVBoxLayout(workbench)
    workbench_layout.setContentsMargins(20, 18, 20, 18)
    workbench_layout.setSpacing(12)
    wb_title = QLabel("复核视频工作台")
    wb_title.setStyleSheet("color:#E2E8F0;font-size:16px;font-weight:800;")
    workbench_layout.addWidget(wb_title)
    surface = QLabel("碰撞主体 (89%)\n\n02:14 / 05:00")
    surface.setAlignment(Qt.AlignmentFlag.AlignCenter)
    surface.setMinimumHeight(300)
    surface.setStyleSheet(
        "QLabel { background:#020617; color:#CBD5E1; border-radius:18px; "
        "border:1px solid #334155; font-size:18px; font-weight:700; }"
    )
    workbench_layout.addWidget(surface, 1)
    frame_row = QHBoxLayout()
    for text in ["关键帧 02:14", "遮挡帧 02:18", "远景帧 02:25"]:
        thumb = QLabel(text)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setMinimumHeight(72)
        thumb.setStyleSheet(
            "QLabel { background:#1E293B; color:#93C5FD; border-radius:12px; "
            "border:1px solid #334155; font-size:12px; font-weight:800; }"
        )
        frame_row.addWidget(thumb)
    workbench_layout.addLayout(frame_row)
    body.addWidget(workbench, 4)

    form = panel()
    form_layout = QVBoxLayout(form)
    form_layout.setContentsMargins(22, 20, 22, 20)
    form_layout.setSpacing(10)
    form_header = QHBoxLayout()
    form_header.addWidget(title("复核判定与标注"))
    form_header.addStretch()
    form_header.addWidget(status_chip("当前: 施工围挡占道", "info"))
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
    note = QTextEdit("AI未识别出侧方变道的遮挡车辆，建议追加人工标注并保留关键帧。")
    form_layout.addWidget(note, 1)
    history = QListWidget()
    history.addItems(["10:22:15 · AI 系统识别 · 置信度 68%", "进行中 · 等待人工复核"])
    form_layout.addWidget(history, 1)
    action_row = QHBoxLayout()
    action_row.addWidget(_wip_button("保存草稿"))
    action_row.addStretch()
    action_row.addWidget(_wip_button("提交复核结果", "primary"))
    form_layout.addLayout(action_row)
    body.addWidget(form, 3)
    root.addLayout(body, 1)
    return page


def alerts_page() -> QWidget:
    page, root = page_shell("告警管理中心", "告警引擎在线 · 2026年03月27日")
    metrics = QGridLayout()
    metrics.setSpacing(14)
    metrics.addWidget(metric_card("今日严重告警", "12", "High Risk", "#EF4444"), 0, 0)
    metrics.addWidget(metric_card("普通告警", "45", "Warning", "#F59E0B"), 0, 1)
    metrics.addWidget(metric_card("今日已处理", "128", "Completed", "#2563EB"), 0, 2)
    metrics.addWidget(metric_card("响应平均耗时", "1.5 min", "Efficiency", "#4F46E5"), 0, 3)
    root.addLayout(metrics)

    list_panel = panel()
    list_layout = QVBoxLayout(list_panel)
    list_layout.setContentsMargins(22, 20, 22, 20)
    list_layout.setSpacing(10)
    list_header = QHBoxLayout()
    list_header.addWidget(title("实时告警列表"))
    list_header.addStretch()
    list_header.addWidget(_wip_button("全部"))
    list_header.addWidget(_wip_button("严重", "primary"))
    list_layout.addLayout(list_header)
    list_layout.addWidget(
        table(
            ["告警时间", "事件类型", "视频源", "置信度", "状态", "操作"],
            [
                ["13:45:22", "剧烈碰撞检测", "VID_0327_112", "98.5%", "待处理", "查看 / 确认"],
                ["13:30:15", "车辆刮擦风险", "VID_0327_109", "82.1%", "处理中", "查看"],
                ["12:10:44", "违章停车检测", "VID_0327_088", "75.4%", "已归档", "-"],
                ["11:42:01", "道路障碍物", "VID_0327_072", "88.7%", "待处理", "查看 / 确认"],
            ],
        )
    )
    root.addWidget(list_panel, 2)

    lower = QHBoxLayout()
    lower.setSpacing(14)
    rules = panel()
    rules_layout = QVBoxLayout(rules)
    rules_layout.setContentsMargins(22, 20, 22, 20)
    rules_layout.addLayout(section_header("告警规则配置", "3 条启用"))
    for rule in [
        "剧烈碰撞 (重型) · 阈值 90% · 通知 全平台",
        "车辆刮擦 (多模态) · 阈值 75% · 通知 网页端",
        "违章停车检测 · 阈值 60% · 通知 关闭",
    ]:
        rules_layout.addWidget(compact_card(rule, "规则命中后自动推送告警队列并记录审计日志"))
    rules_layout.addWidget(_wip_button("编辑告警规则", "primary"))
    lower.addWidget(rules, 2)

    type_dist = panel()
    type_layout = QVBoxLayout(type_dist)
    type_layout.setContentsMargins(22, 20, 22, 20)
    type_layout.addWidget(title("事件类型分布"))
    pie2 = CategoryPieChart()
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
    trend_layout.addWidget(title("告警分级趋势"))
    chart = TrendBarChart()
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


def accidents_page() -> QWidget:
    page, root = page_shell("事故与风险发现面板", "业务视角的自动化事故摘要呈现与空间态势分布")
    body = QHBoxLayout()
    body.setSpacing(14)

    feed = QVBoxLayout()
    feed.setSpacing(14)
    for heading, chip, time_text, plate, summary, accent, kind in [
        (
            "南山区深南大道科苑立交段侧向碰撞",
            "高危变道",
            "14:22:15 · 2026-03-27",
            "粤B·88888 · 94% 置信度",
            "白色 SUV 在路口右转时未充分观察侧方来车，与直行黑色轿车发生侧向剐蹭。系统建议回放原片、建立证据包并进入归档流程。",
            "#EF4444",
            "high",
        ),
        (
            "滨河大道行人鬼探头横穿致紧急刹车",
            "行人鬼探头",
            "09:15:33 · 2026-03-27",
            "Near-miss · 87% 置信度",
            "画面左前方绿化带区域突然跑出行人，本车触发车道偏离警告并紧急制动，最终在约 1.2 米处停稳。",
            "#F59E0B",
            "mid",
        ),
    ]:
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
        icon_lbl = QLabel("⚠" if accent == "#EF4444" else "⚡")
        icon_lbl.setStyleSheet(
            f"color:{accent}; font-size:20px; padding-right:6px;"
        )
        title_label = QLabel(heading)
        title_label.setStyleSheet("color:#0F172A;font-size:16px;font-weight:800;")
        title_label.setWordWrap(True)
        top.addWidget(icon_lbl)
        top.addWidget(title_label, 1)
        top.addWidget(status_chip(chip, kind))
        layout.addLayout(top)
        time_row = QHBoxLayout()
        time_row.addWidget(muted(time_text))
        plate_chip = status_chip(plate, "muted")
        time_row.addWidget(plate_chip)
        time_row.addStretch()
        layout.addLayout(time_row)
        summary_title = QLabel("大语言模型自动浓缩摘要")
        summary_title.setStyleSheet(f"color:{accent};font-size:12px;font-weight:700;")
        layout.addWidget(summary_title)
        layout.addWidget(muted(summary))
        actions = QHBoxLayout()
        actions.addWidget(_wip_button("回放原片与标注", "primary"))
        actions.addWidget(_wip_button("建立证据包并归档"))
        actions.addStretch()
        layout.addLayout(actions)
        feed.addWidget(card)
    body.addLayout(feed, 3)

    side = dark_panel()
    side_layout = QVBoxLayout(side)
    side_layout.setContentsMargins(22, 20, 22, 20)
    side_layout.setSpacing(14)
    heat_title = QLabel("事件热力空间分布")
    heat_title.setStyleSheet("color:#CBD5E1;font-size:12px;font-weight:800;letter-spacing:1px;")
    side_layout.addWidget(heat_title)
    heat = QLabel("南山区段       12起\n福田区段        5起\n罗湖区段        4起\n宝安区段        3起")
    heat.setStyleSheet("color:#E2E8F0;font-size:14px;line-height:1.6;")
    side_layout.addWidget(heat)
    side_layout.addWidget(compact_card("全局风险指征", "侧向碰撞与行人横穿为今日主要风险类型，建议导出日报并同步车队培训库。", "#F59E0B"))
    side_layout.addStretch()
    side_layout.addWidget(_wip_button("查看全天业务报告", "primary"))
    body.addWidget(side, 2)
    root.addLayout(body, 1)
    return page


def evidence_page() -> QWidget:
    page, root = page_shell("证据与日志归档", "统一管理系统流转日志与涉案证据包")

    controls = panel()
    controls_layout = QHBoxLayout(controls)
    controls_layout.setContentsMargins(22, 16, 22, 16)
    search = QLineEdit()
    search.setPlaceholderText("搜索案件编号、日志凭点...")
    controls_layout.addWidget(search, 1)
    controls_layout.addWidget(_wip_button("打包备份归档", "primary"))
    root.addWidget(controls)

    body = QHBoxLayout()
    body.setSpacing(14)
    left = QVBoxLayout()
    stats = QGridLayout()
    stats.setSpacing(14)
    stats.addWidget(metric_card("今日新增证据", "42 卷", "签名队列 3"), 0, 0)
    stats.addWidget(metric_card("累计固证", "128 卷", "近 7 日"), 0, 1)
    stats.addWidget(metric_card("归档存储空间", "64%", "已用 12TB", "#4F46E5"), 0, 2)
    left.addLayout(stats)

    queue = panel()
    queue_layout = QVBoxLayout(queue)
    queue_layout.setContentsMargins(22, 18, 22, 18)
    queue_layout.addLayout(section_header("近期证据保全队列", "队列 14"))
    for item, desc, status in [
        ("EVT-0822-完整证据包.zip", "14:30 生成 · 包含视频源、抽帧截图、文本总结", "正在签名审计"),
        ("EVT-0810-快速摘要.pdf", "11:20 生成 · 包含 AI 文本描述分析、时间线", "已固证"),
        ("SYS-ERR-001-排错录像.zip", "09:12 生成 · 包含原始接入异常视频", "已固证"),
    ]:
        row = QHBoxLayout()
        row.addWidget(compact_card(item, desc))
        row.addWidget(status_chip(status, "mid" if "签名" in status else "low"))
        queue_layout.addLayout(row)
    left.addWidget(queue, 1)
    body.addLayout(left, 3)

    log_panel = panel()
    log_layout = QVBoxLayout(log_panel)
    log_layout.setContentsMargins(22, 18, 22, 18)
    log_layout.addLayout(section_header("系统交互日志", "审计"))
    logs = QListWidget()
    logs.addItems([
        "14:30:11 · 证据导出 · EVT-0822 生成完整证据包",
        "14:00:00 · 鉴权日志 · admin 刷新 Bearer Token",
        "11:20:03 · 摘要导出 · EVT-0810 生成快速摘要",
        "09:12:45 · 系统日志 · 原始接入异常录像已归档",
        "08:44:29 · 检索日志 · 创建查询 QRY-20260327-009",
    ])
    log_layout.addWidget(logs, 1)
    body.addWidget(log_panel, 2)
    root.addLayout(body, 1)
    return page


def daily_report_page() -> QWidget:
    page, root = page_shell("全天业务报告", "2026年03月27日业务汇总与趋势分析")
    metrics = QGridLayout()
    metrics.setSpacing(14)
    metrics.addWidget(metric_card("处理视频", "127", "今日"), 0, 0)
    metrics.addWidget(metric_card("关键事件", "342", "今日"), 0, 1)
    metrics.addWidget(metric_card("检索次数", "1,204", "今日"), 0, 2)
    metrics.addWidget(metric_card("导出证据", "89", "今日", "#F59E0B"), 0, 3)
    root.addLayout(metrics)

    body = QHBoxLayout()
    body.setSpacing(14)
    left = QVBoxLayout()
    trend = panel()
    trend_layout = QVBoxLayout(trend)
    trend_layout.setContentsMargins(22, 20, 22, 20)
    trend_layout.addLayout(section_header("事件识别趋势 (7日)", "报告生成时间: 23:59"))
    chart = TrendBarChart()
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
    for name, pct_int, color in [
        ("侧向碰撞", 45, "#EF4444"),
        ("行人鬼探头", 30, "#F59E0B"),
        ("违停", 15, "#2563EB"),
        ("其他", 10, "#64748B"),
    ]:
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
    region = dark_panel()
    region_layout = QVBoxLayout(region)
    region_layout.setContentsMargins(22, 20, 22, 20)
    region_title = QLabel("区域事件统计")
    region_title.setStyleSheet("color:#CBD5E1;font-size:12px;font-weight:800;letter-spacing:1px;")
    region_layout.addWidget(region_title)
    region_stats = QLabel("南山区段     127起\n福田区段      89起\n罗湖区段      56起\n宝安区段      34起")
    region_stats.setStyleSheet("color:#E2E8F0;font-size:14px;line-height:1.6;")
    region_layout.addWidget(region_stats)
    right.addWidget(region, 1)

    summary = panel()
    summary_layout = QVBoxLayout(summary)
    summary_layout.setContentsMargins(22, 20, 22, 20)
    summary_layout.addWidget(title("业务总结"))
    summary_layout.addWidget(muted("今日系统处理视频127个，识别关键事件342起，检索请求1204次，证据导出89份。事件主要集中在南山区和福田区，侧向碰撞和行人鬼探头为主要类型。系统运行稳定，无重大异常。"))
    summary_layout.addWidget(_wip_button("导出PDF报告", "primary"))
    right.addWidget(summary, 1)
    body.addLayout(right, 2)
    root.addLayout(body, 1)
    return page


def settings_page() -> QWidget:
    page, root = page_shell("系统参数与模型配置", "模型供应商、抽帧间隔、置信阈值和接口安全策略")
    body = QVBoxLayout()
    body.setSpacing(14)

    model = panel()
    model_layout = QVBoxLayout(model)
    model_layout.setContentsMargins(22, 20, 22, 20)
    model_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    model_layout.addWidget(title("多模态大模型引擎 (LLM/VLM)"))
    model_layout.addWidget(muted("配置用于视频帧理解及语义标签生成的底层模型接口参数。"))
    provider = QComboBox()
    provider.addItems(["本地自研多模态模型 (DVR-L1)", "Qwen-VL", "OpenAI Vision", "Mock Adapter"])
    model_layout.addWidget(muted("模型服务商"))
    model_layout.addWidget(provider)
    api_key = QLineEdit("••••••••••••••••••••")
    api_key.setEchoMode(QLineEdit.EchoMode.Password)
    model_layout.addWidget(muted("模型 API Key / 安全令牌"))
    model_layout.addWidget(api_key)
    model_layout.addWidget(muted("API Endpoint"))
    endpoint = QLineEdit("https://api.internal-dvr.net/v1/semantic")
    model_layout.addWidget(endpoint)
    model_layout.addWidget(muted("提示：Key 仅在服务端安全容器内解密使用。"))
    body.addWidget(model)

    pipeline = panel()
    pipe_layout = QVBoxLayout(pipeline)
    pipe_layout.setContentsMargins(22, 20, 22, 20)
    pipe_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    pipe_layout.addWidget(title("视频处理与检索阈值"))
    for label, value in [("抽帧间隔", "5 秒"), ("Embedding 模型", "text-embedding-v3")]:
        pipe_layout.addWidget(muted(label))
        pipe_layout.addWidget(QLineEdit(value))
    pipe_layout.addWidget(muted("语义识别阈值"))
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, 100)
    slider.setValue(72)
    pipe_layout.addWidget(slider)
    pipe_layout.addWidget(status_chip("当前阈值 0.72", "info"))
    pipe_layout.addWidget(muted("存储根目录 (Media Root)"))
    pipe_layout.addWidget(QLineEdit("./var/media"))
    body.addWidget(pipeline)

    security = panel()
    sec_layout = QVBoxLayout(security)
    sec_layout.setContentsMargins(22, 20, 22, 20)
    sec_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    sec_layout.addWidget(title("接口安全鉴权 (Security)"))
    sec_layout.addWidget(status_chip("Bearer Token 模式启用", "low"))
    for item in ["OAuth2.0 登录态校验", "证据导出审计日志", "管理员危险操作二次确认", "模型 Key 服务端解密"]:
        check = QCheckBox(item)
        check.setChecked(True)
        sec_layout.addWidget(check)
    sec_layout.addStretch()
    sec_layout.addWidget(_wip_button("保存所有全局设置", "primary"))
    sec_layout.addWidget(_wip_button("恢复出厂默认值"))
    body.addWidget(security)
    root.addLayout(body, 1)
    return page


def roles_page() -> QWidget:
    page, root = page_shell("角色与权限管理", "管理员、审核人员、普通用户的权限维护")

    # Page header button
    hdr_row = QHBoxLayout()
    hdr_row.addStretch()
    hdr_row.addWidget(_wip_button("新增管理员", "primary"))
    root.addLayout(hdr_row)

    roles_layout = QHBoxLayout()
    roles_layout.setSpacing(14)

    _role_perms = [
        [("✓ 查看绑定车辆视频", True), ("✓ 个人证据链导出", True),
         ("✗ 跨车队检索", False), ("✗ 审计日志查看", False)],
        [("✓ 车队视频管理", True), ("✓ 任务与分组管理", True),
         ("✓ 成员授权管理", True), ("✗ 审计日志查看", False)],
        [("✓ 跨平台视频检索", True), ("✓ 事故证据收集", True),
         ("✓ 审计日志查看", True), ("✗ 模型参数微调", False)],
    ]

    for (name, code, letter, desc, users, count, accent, bg), perms in zip([
        ("车主 / 驾驶员", "OWNER / DRIVER", "U", "仅可查看及检索与其驾驶证/行驶证绑定的车辆视频。具备个人证据链导出权限。", "管理用户列表", "124", "#2563EB", "#EFF6FF"),
        ("车队管理员", "FLEET MANAGER", "M", "可管理车队视频源、处理任务、车辆分组与成员授权。", "管理用户列表", "8", "#F59E0B", "#FFFBEB"),
        ("交通巡查员", "TRAFFIC INSPECTOR", "I", "具备跨平台视频检索权限，用于事故复盘及违章证据收集，受审计日志监控。", "管理用户列表", "4", "#EF4444", "#FEF2F2"),
    ], _role_perms):
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

    # Color-coded permission table
    tbl = table(
        ["功能模块 / 权限点", "车主", "车队管理员", "交通巡查员", "风险等级"],
        [
            ["语义检索 (Natural Language Query)", "✓ 允许", "✓ 允许", "✓ 允许", "LOW"],
            ["原始视频文件下载 (H.264/265)", "✗ 禁止", "✓ 允许", "✓ 允许", "MED"],
            ["证据链多模态摘要导出", "✓ 允许", "✓ 允许", "✓ 允许", "LOW"],
            ["系统审计日志 (Audit Log) 查看", "✗ 禁止", "✗ 禁止", "✓ 允许", "HIGH"],
            ["多模态模型 API 参数微调", "✗ 禁止", "✗ 禁止", "✗ 禁止", "CRITICAL"],
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
