# 原型搬运说明

## 当前状态说明

上一版脚手架不是严格复现原型，而是按需求文档重新搭了一个 Qt6 客户端框架。现在已调整为“原型作为 UI 设计稿”的策略：视觉、页面、导航、接口和 TODO 都以你完成的 `DVR-Semantic` 原型为准，但最终实现必须在 Qt6 桌面端技术栈里完成。

原型源文件已复制到：

```text
docs/prototype-source/
```

可以打开原始原型作为设计参考：

```bash
python apps/desktop_client/run_prototype.py
```

如果安装了 PySide6 + QtWebEngine，也可以用 Qt 壳打开原型参考：

```bash
python apps/desktop_client/prototype_shell.py
```

## 页面搬运映射

| 原型页面 | Qt/工程目标 | 后端 API |
| --- | --- | --- |
| `系统登录.html` | 登录页/会话状态 | `/api/auth/login`, `/api/auth/me`, `/api/auth/logout` |
| `系统状态概览.html` | 仪表盘页 | `/api/dashboard/overview`, `/api/dashboard/trends`, `/api/dashboard/event-distribution`, `/api/dashboard/review-feed` |
| `视频库管理.html` | 视频库与上传任务页 | `/api/videos`, `/api/videos/upload`, `/api/videos/{id}/status`, `/api/videos/{id}/segments` |
| `语义检索中心.html` | 当前重点实现页：检索、结果、播放器、证据控制 | `/api/search`, `/api/events/{id}`, `/api/videos/{id}/stream`, `/api/videos/{id}/timeline`, `/api/events/{id}/export` |
| `人工复核中心.html` | 低置信事件复核页 | `/api/review/tasks`, `/api/review/tasks/{event_id}/decision`, `/api/events/{id}/labels` |
| `告警管理中心.html` | 告警列表与确认页 | `/api/alerts/summary`, `/api/alerts`, `/api/alerts/{id}/ack`, `/api/alerts/{id}/resolve` |
| `事故摘要预览.html` | 事故/风险摘要页 | `/api/accidents`, `/api/accidents/{id}`, `/api/accidents/{id}/summary` |
| `证据与日志归档.html` | 证据包与日志页 | `/api/events/{id}/export`, `/api/exports`, `/api/audit/logs` |
| `全天业务报告.html` | 日报页 | `/api/reports/daily`, `/api/reports/daily/export` |
| `模型与安全配置.html` | 模型参数和安全设置页 | `/api/settings/model`, `/api/settings/model/test`, `/api/settings/security` |
| `角色与权限管理.html` | 用户、角色、权限页 | `/api/users`, `/api/roles`, `/api/permissions` |

## 视觉搬运规则

- 顶部导航沿用原型的 `DVR-S` 标识和导航文案。
- 主色沿用蓝色 `#2563EB`，背景沿用 `#F8FAFC`。
- 卡片、面板、指标块保留原型的大圆角和浅色玻璃感。
- `语义检索中心` 保留左侧查询/结果、右侧视频/证据、深色视频区域的结构。
- 原型中的演示文案、查询样例、状态标签优先保留，后续接真实接口替换数据。
- 不把 HTML 原型作为最终客户端交付；HTML 只用于对照视觉和交互。
- Qt6 实现优先使用 `QWidget`、`QStackedWidget`、`QTableWidget`、`QFrame`、`QPushButton` 等原生组件复现。

## 实现顺序

1. 已完成：把 11 个原型页面完整接入仓库作为 UI 参考。
2. 已完成：提供原型参考运行入口，方便开发时对照。
3. 已完成：提供 Qt6 多页面工作台，按原型复现概览、检索、视频流、复核、告警、事故、证据日志、报告、配置、权限、登录页面。
4. 继续事项：把复核、告警、报告、配置、权限等展示型页面逐步绑定到真实后端接口。
5. 继续事项：使用 `DVR_SEMANTIC_API_BASE` 切换真实后端，配真实视频和模型 API Key 做答辩样例验证。
