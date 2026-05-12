from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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
    page = QWidget()
    root = QVBoxLayout(page)
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
    return page, root


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


def overview_page() -> QWidget:
    page, root = page_shell("系统状态概览", "2026年03月27日 · 系统运行正常 · 多模态节点 8/8")
    # 原型是 3 列 KPI（不是 4 列）
    metrics = QGridLayout()
    metrics.setSpacing(14)
    metrics.addWidget(metric_card("总处理视频", "8,429", "+12% 本周增长"), 0, 0)
    metrics.addWidget(metric_card("语义检索次数", "1,204", "响应稳定", "#4F46E5"), 0, 1)
    metrics.addWidget(metric_card("识别关键事件", "342", "+5.4% 今日新增", "#F59E0B"), 0, 2)
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
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        page_title = QLabel("视频库管理")
        page_title.setProperty("role", "title")
        header_layout.addWidget(page_title)
        header_layout.addWidget(muted("上传、处理状态、缩略图封面和任务进度管理"))
        root.addWidget(header)

        upload = panel()
        upload_layout = QHBoxLayout(upload)
        upload_layout.setContentsMargins(16, 14, 16, 14)
        upload_layout.addWidget(title("导入行车记录仪视频"))
        self.upload_button = action_button("上传视频", "primary")
        self.upload_button.clicked.connect(self._on_upload_clicked)
        self.refresh_button = action_button("刷新列表")
        self.refresh_button.clicked.connect(self.refresh)
        upload_layout.addWidget(self.upload_button)
        upload_layout.addWidget(self.refresh_button)
        root.addWidget(upload)

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

        self.video_table = QTableWidget(0, 5)
        self.video_table.setHorizontalHeaderLabels(
            ["视频", "时长", "状态", "ID", "失败原因"]
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
                str(getattr(video, "title", "")),
                duration,
                str(getattr(video, "status", "")),
                str(getattr(video, "id", "")),
                str(getattr(video, "fail_reason", "")),
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
    page, root = page_shell("人工复核中心", "低置信事件确认、修正标签和复核提交")

    metrics = QGridLayout()
    metrics.setSpacing(14)
    metrics.addWidget(metric_card("待复核", "12", "低置信事件队列", "#EF4444"), 0, 0)
    metrics.addWidget(metric_card("今日已复核", "27", "确认 21 · 驳回 6", "#22C55E"), 0, 1)
    metrics.addWidget(metric_card("平均耗时", "1.2 min", "单事件均值", "#2563EB"), 0, 2)
    metrics.addWidget(metric_card("复核同意率", "78%", "近 7 日", "#4F46E5"), 0, 3)
    root.addLayout(metrics)

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
    queue_layout.addWidget(muted("置信度 < 80% 自动入队，按时间倒序"))
    tasks = QListWidget()
    for item in [
        "施工围挡占道 · 79%  ·  14:22 - 14:23",
        "异常停车与连续鸣笛 · 74%  ·  09:15 - 09:16",
        "疑似路口擦碰 · 68%  ·  18:33 - 18:34",
        "夜间逆行 · 71%  ·  21:08 - 21:09",
        "环岛违停 · 73%  ·  11:42 - 11:43",
    ]:
        tasks.addItem(QListWidgetItem(item))
    queue_layout.addWidget(tasks, 1)
    body.addWidget(queue, 2)

    form = panel()
    form_layout = QVBoxLayout(form)
    form_layout.setContentsMargins(22, 20, 22, 20)
    form_layout.setSpacing(10)
    form_header = QHBoxLayout()
    form_header.addWidget(title("复核判定与标注"))
    form_header.addStretch()
    form_header.addWidget(status_chip("当前: 施工围挡占道", "info"))
    form_layout.addLayout(form_header)
    form_layout.addWidget(muted("修正标题、调整事件类型、补充复核备注，提交后写入审计日志"))
    form_layout.addWidget(QLineEdit("施工围挡占用右侧车道"))
    event_type = QComboBox()
    event_type.addItems(["road_obstacle", "scratch", "illegal_parking", "abnormal_stop"])
    form_layout.addWidget(event_type)
    note = QTextEdit("画面清晰，确认属于道路障碍事件。建议导出 13s 片段。")
    form_layout.addWidget(note, 1)
    action_row = QHBoxLayout()
    action_row.addWidget(action_button("驳回"))
    action_row.addStretch()
    action_row.addWidget(action_button("提交复核", "primary"))
    form_layout.addLayout(action_row)
    body.addWidget(form, 3)
    root.addLayout(body, 1)
    return page


def alerts_page() -> QWidget:
    page, root = page_shell("告警管理中心", "高风险事件告警、确认、关闭和处置备注")
    metrics = QGridLayout()
    metrics.setSpacing(14)
    metrics.addWidget(metric_card("未处理告警", "12", "高优先级 5 条", "#EF4444"), 0, 0)
    metrics.addWidget(metric_card("今日告警", "45", "+8 较昨日", "#F59E0B"), 0, 1)
    metrics.addWidget(metric_card("已关闭", "128", "本周累计", "#22C55E"), 0, 2)
    metrics.addWidget(metric_card("平均响应", "1.5 min", "高优先级 <2 min", "#2563EB"), 0, 3)
    root.addLayout(metrics)

    list_panel = panel()
    list_layout = QVBoxLayout(list_panel)
    list_layout.setContentsMargins(22, 20, 22, 20)
    list_layout.setSpacing(10)
    list_header = QHBoxLayout()
    list_header.addWidget(title("告警事件列表"))
    list_header.addStretch()
    list_header.addWidget(status_chip("12 待确认", "high"))
    list_header.addWidget(status_chip("33 处置中", "mid"))
    list_header.addWidget(status_chip("128 已关闭", "low"))
    list_layout.addLayout(list_header)
    list_layout.addWidget(
        table(
            ["告警ID", "事件", "等级", "状态", "触发时间", "负责人"],
            [
                ["ALT-2026-0431", "高置信剐蹭事件 · 南山区", "高", "待确认", "14:22:18", "—"],
                ["ALT-2026-0430", "道路障碍风险 · 滨河大道", "中", "处置中", "13:55:02", "reviewer01"],
                ["ALT-2026-0429", "异常停车 · 高架入口", "中", "处置中", "13:11:46", "reviewer02"],
                ["ALT-2026-0428", "夜间逆行 · 福田",       "高", "待确认", "12:48:33", "—"],
                ["ALT-2026-0427", "环岛违停 · 龙岗",       "低", "已关闭", "11:42:11", "admin"],
                ["ALT-2026-0426", "施工围挡占道 · 罗湖",   "中", "已关闭", "10:30:09", "reviewer01"],
            ],
        )
    )
    root.addWidget(list_panel, 1)
    return page


def accidents_page() -> QWidget:
    page, root = page_shell("事故摘要预览", "事故与风险发现面板，支持摘要生成和证据联动")
    grid = QGridLayout()
    grid.setSpacing(14)
    grid.addWidget(
        metric_card("侧向碰撞 · 南山", "高风险",
                    "深南大道科苑立交段，疑似侧向剐蹭，建议导出 15s 片段与关键帧", "#EF4444"),
        0, 0,
    )
    grid.addWidget(
        metric_card("行人横穿 · 滨河", "中风险",
                    "滨河大道，行人快速横穿，车辆明显减速但未碰撞", "#F59E0B"),
        0, 1,
    )
    grid.addWidget(
        metric_card("夜间逆行 · 福田", "高风险",
                    "深南中路夜间发现逆行车辆，建议通知交管联动处置", "#EF4444"),
        0, 2,
    )
    root.addLayout(grid)

    list_panel = panel()
    list_layout = QVBoxLayout(list_panel)
    list_layout.setContentsMargins(22, 20, 22, 20)
    list_layout.setSpacing(10)
    list_layout.addWidget(title("事故归档队列"))
    list_layout.addWidget(muted("综合识别 + 人工复核结果，按风险等级排序"))
    list_layout.addWidget(
        table(
            ["事故ID", "类型", "时间段", "地点", "风险", "状态"],
            [
                ["ACC-0327-001", "侧向碰撞", "14:22:15-14:22:45", "南山区", "高", "待归档"],
                ["ACC-0327-002", "行人横穿", "09:15:34-09:15:58", "滨河大道", "中", "已复核"],
                ["ACC-0327-003", "夜间逆行", "21:08:11-21:09:02", "福田", "高", "待归档"],
                ["ACC-0327-004", "施工围挡占道", "11:42:30-11:43:11", "龙岗", "中", "已归档"],
            ],
        )
    )
    root.addWidget(list_panel, 1)
    return page


def evidence_page() -> QWidget:
    page, root = page_shell("证据与日志归档", "证据包导出、下载和系统交互日志")

    controls = panel()
    controls_layout = QHBoxLayout(controls)
    controls_layout.setContentsMargins(22, 16, 22, 16)
    controls_layout.setSpacing(10)
    controls_layout.addWidget(title("近期证据保全队列"))
    controls_layout.addStretch()
    controls_layout.addWidget(status_chip("队列 14", "info"))
    controls_layout.addWidget(action_button("下载选中项"))
    controls_layout.addWidget(action_button("导出证据包", "evidence"))
    root.addWidget(controls)

    exp_panel = panel()
    exp_layout = QVBoxLayout(exp_panel)
    exp_layout.setContentsMargins(22, 16, 22, 20)
    exp_layout.setSpacing(8)
    exp_layout.addWidget(title("证据导出记录"))
    exp_layout.addWidget(
        table(
            ["导出ID", "事件", "类型", "状态", "路径"],
            [
                ["exp-evt-scratch-001", "疑似侧向剐蹭", "package", "success",
                 "media/exports/evt-scratch-001.zip"],
                ["exp-report-20260327", "全天业务报告", "pdf", "queued", "-"],
                ["exp-evt-obstacle-014", "施工围挡占道", "package", "success",
                 "media/exports/evt-obstacle-014.zip"],
                ["exp-evt-parking-009", "异常停车", "package", "processing", "-"],
            ],
        )
    )
    root.addWidget(exp_panel, 1)

    log_panel = panel()
    log_layout = QVBoxLayout(log_panel)
    log_layout.setContentsMargins(22, 16, 22, 20)
    log_layout.setSpacing(8)
    log_layout.addWidget(title("审计日志"))
    log_layout.addWidget(
        table(
            ["时间", "用户", "动作", "说明"],
            [
                ["09:00:21", "admin", "event.export", "导出证据包 evt-scratch-001"],
                ["09:02:48", "reviewer01", "event.review", "确认道路障碍事件"],
                ["09:14:09", "user01", "search.create", "查询：疑似剐蹭的时间段"],
                ["10:30:12", "reviewer02", "event.review", "驳回低置信告警 ALT-0427"],
                ["11:08:44", "admin", "video.upload", "上传 VID_20260327_1422"],
            ],
        )
    )
    root.addWidget(log_panel, 1)
    return page


def daily_report_page() -> QWidget:
    page, root = page_shell("全天业务报告", "事件识别趋势、类型分布、区域统计和业务总结")
    metrics = QGridLayout()
    metrics.addWidget(metric_card("处理视频", "124", "今日"), 0, 0)
    metrics.addWidget(metric_card("关键事件", "18", "今日"), 0, 1)
    metrics.addWidget(metric_card("检索次数", "86", "今日"), 0, 2)
    metrics.addWidget(metric_card("导出证据", "7", "今日", "#F59E0B"), 0, 3)
    root.addLayout(metrics)
    summary = panel()
    summary_layout = QVBoxLayout(summary)
    summary_layout.addWidget(title("业务总结"))
    summary_layout.addWidget(muted("全天共处理 124 个视频，识别 18 个关键事件，重点集中在南山区与滨河大道。"))
    summary_layout.addWidget(action_button("导出日报 PDF", "evidence"))
    root.addWidget(summary, 1)
    return page


def settings_page() -> QWidget:
    page, root = page_shell("模型与安全配置", "模型供应商、抽帧间隔、置信阈值和安全策略")
    form = panel()
    layout = QVBoxLayout(form)
    layout.addWidget(title("系统参数与模型配置"))
    for label, value in [
        ("视觉模型", "qwen-vl-max"),
        ("Embedding 模型", "text-embedding-v3"),
        ("抽帧间隔", "5 秒"),
        ("置信阈值", "0.72"),
    ]:
        row = QHBoxLayout()
        row.addWidget(muted(label))
        row.addWidget(QLineEdit(value))
        layout.addLayout(row)
    layout.addWidget(action_button("测试模型连通性", "primary"))
    root.addWidget(form, 1)
    return page


def roles_page() -> QWidget:
    page, root = page_shell("角色与权限管理", "管理员、审核人员、普通用户的权限维护")
    root.addWidget(table(["用户", "真实姓名", "角色", "状态"], [["admin", "管理员", "admin", "启用"], ["reviewer01", "复核员", "reviewer", "启用"], ["user01", "普通用户", "user", "启用"]]), 1)
    root.addWidget(table(["角色", "权限"], [["admin", "*"], ["reviewer", "event:read,event:review"], ["user", "video:upload,search:create"]]))
    return page


def login_page() -> QWidget:
    page, root = page_shell("系统登录", "DVR-Semantic 安全登录入口")
    login = panel()
    layout = QVBoxLayout(login)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    layout.addWidget(title("DVR-S"))
    layout.addWidget(muted("多模态行车记录仪视频语义检索与精准回放系统"))
    layout.addWidget(QLineEdit("admin"))
    password = QLineEdit()
    password.setPlaceholderText("密码")
    password.setEchoMode(QLineEdit.EchoMode.Password)
    layout.addWidget(password)
    layout.addWidget(action_button("安全登录 (Sign In)", "primary"))
    root.addWidget(login, 1)
    return page
