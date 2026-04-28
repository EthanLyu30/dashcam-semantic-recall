from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


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


def metric_card(label: str, value: str, note: str, accent: str = "#2563EB") -> QFrame:
    card = panel()
    card.setStyleSheet(
        f"QFrame {{ background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 22px; }}"
        f"QLabel#accent {{ color: {accent}; font-size: 28px; font-weight: 800; }}"
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    label_widget = muted(label)
    value_widget = QLabel(value)
    value_widget.setObjectName("accent")
    note_widget = muted(note)
    layout.addWidget(label_widget)
    layout.addWidget(value_widget)
    layout.addWidget(note_widget)
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
    widget.resizeColumnsToContents()
    return widget


def overview_page() -> QWidget:
    page, root = page_shell("系统状态概览", "2026年03月27日 · 系统运行正常 · 多模态节点 8/8")
    metrics = QGridLayout()
    metrics.setSpacing(12)
    metrics.addWidget(metric_card("总处理视频", "8,429", "+12% 本周增长"), 0, 0)
    metrics.addWidget(metric_card("语义检索次数", "1,204", "响应稳定", "#4F46E5"), 0, 1)
    metrics.addWidget(metric_card("识别关键事件", "342", "+5.4% 今日新增", "#F59E0B"), 0, 2)
    metrics.addWidget(metric_card("待人工复核", "12", "低置信事件队列", "#EF4444"), 0, 3)
    root.addLayout(metrics)

    lower = QHBoxLayout()
    trend = panel()
    trend_layout = QVBoxLayout(trend)
    trend_layout.addWidget(title("识别趋势与并发负载 (7日)"))
    trend_layout.addWidget(muted("这里在 Qt 版中预留 ECharts/QtCharts 图表区域，先用可读数据列表承接原型图表。"))
    trend_layout.addWidget(
        table(
            ["日期", "事件数", "查询数", "负载"],
            [["03-21", "28", "120", "42%"], ["03-22", "34", "146", "58%"], ["03-23", "31", "132", "51%"]],
        )
    )
    lower.addWidget(trend, 3)

    distribution = panel()
    dist_layout = QVBoxLayout(distribution)
    dist_layout.addWidget(title("多模态分类分布"))
    dist_layout.addWidget(table(["类型", "数量"], [["剐蹭", "86"], ["违停", "74"], ["道路障碍", "58"], ["异常停车", "41"]]))
    lower.addWidget(distribution, 2)
    root.addLayout(lower, 1)
    return page


def video_library_page() -> QWidget:
    page, root = page_shell("视频库管理", "上传、处理状态、缩略图封面和任务进度管理")
    upload = panel()
    upload_layout = QHBoxLayout(upload)
    upload_layout.setContentsMargins(16, 14, 16, 14)
    upload_layout.addWidget(title("导入行车记录仪视频"))
    upload_layout.addWidget(action_button("选择文件", "primary"))
    upload_layout.addWidget(action_button("开始分析"))
    upload_layout.addWidget(action_button("重试失败任务"))
    root.addWidget(upload)

    progress = panel()
    progress_layout = QVBoxLayout(progress)
    progress_layout.addWidget(title("处理任务"))
    bar = QProgressBar()
    bar.setValue(68)
    progress_layout.addWidget(bar)
    progress_layout.addWidget(muted("VID_20260327_1422 · 正在抽取关键帧 · 68%"))
    root.addWidget(progress)

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


def review_page() -> QWidget:
    page, root = page_shell("人工复核中心", "低置信事件确认、修正标签和复核提交")
    body = QHBoxLayout()
    queue = panel()
    queue_layout = QVBoxLayout(queue)
    queue_layout.addWidget(title("任务队列"))
    tasks = QListWidget()
    for item in ["施工围挡占道 · 79%", "异常停车与连续鸣笛 · 74%", "疑似路口擦碰 · 68%"]:
        tasks.addItem(QListWidgetItem(item))
    queue_layout.addWidget(tasks)
    body.addWidget(queue, 2)

    form = panel()
    form_layout = QVBoxLayout(form)
    form_layout.addWidget(title("复核判定与标注"))
    form_layout.addWidget(QLineEdit("施工围挡占用右侧车道"))
    event_type = QComboBox()
    event_type.addItems(["road_obstacle", "scratch", "illegal_parking", "abnormal_stop"])
    form_layout.addWidget(event_type)
    note = QTextEdit("画面清晰，确认属于道路障碍事件。")
    form_layout.addWidget(note, 1)
    form_layout.addWidget(action_button("提交复核", "primary"))
    body.addWidget(form, 3)
    root.addLayout(body, 1)
    return page


def alerts_page() -> QWidget:
    page, root = page_shell("告警管理中心", "高风险事件告警、确认、关闭和处置备注")
    metrics = QGridLayout()
    metrics.addWidget(metric_card("未处理告警", "12", "open", "#EF4444"), 0, 0)
    metrics.addWidget(metric_card("今日告警", "45", "today", "#F59E0B"), 0, 1)
    metrics.addWidget(metric_card("已关闭", "128", "resolved", "#22C55E"), 0, 2)
    metrics.addWidget(metric_card("平均响应", "1.5 min", "response", "#2563EB"), 0, 3)
    root.addLayout(metrics)
    root.addWidget(table(["告警", "等级", "状态", "操作"], [["高置信剐蹭事件", "高", "open", "确认"], ["道路障碍风险", "中", "acknowledged", "关闭"]]), 1)
    return page


def accidents_page() -> QWidget:
    page, root = page_shell("事故摘要预览", "事故与风险发现面板，支持摘要生成和证据联动")
    grid = QGridLayout()
    grid.addWidget(metric_card("南山区深南大道科苑立交段侧向碰撞", "高风险", "疑似侧向剐蹭，建议导出片段与关键帧", "#EF4444"), 0, 0)
    grid.addWidget(metric_card("滨河大道行人横穿导致急刹", "中风险", "行人快速横穿，车辆明显减速", "#F59E0B"), 0, 1)
    root.addLayout(grid)
    root.addWidget(table(["事故", "时间段", "状态"], [["侧向碰撞", "14:22:15-14:22:45", "待归档"], ["行人横穿", "09:15:34-09:15:58", "已复核"]]), 1)
    return page


def evidence_page() -> QWidget:
    page, root = page_shell("证据与日志归档", "证据包导出、下载和系统交互日志")
    controls = panel()
    controls_layout = QHBoxLayout(controls)
    controls_layout.addWidget(title("近期证据保全队列"))
    controls_layout.addWidget(action_button("导出证据包", "evidence"))
    controls_layout.addWidget(action_button("下载选中项"))
    root.addWidget(controls)
    root.addWidget(table(["导出ID", "事件", "类型", "状态", "路径"], [["exp-evt-scratch-001", "疑似侧向剐蹭", "package", "success", "media/exports/evt-scratch-001.zip"], ["exp-report-20260327", "全天业务报告", "pdf", "queued", "-"]]), 1)
    root.addWidget(table(["时间", "用户", "动作", "说明"], [["09:00", "admin", "event.export", "导出证据包"], ["09:02", "reviewer", "event.review", "确认道路障碍事件"]]))
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
