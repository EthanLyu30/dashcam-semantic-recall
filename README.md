# 行车记录仪视频语义检索与精准回放系统

> **项目英文名**：`dashcam-semantic-recall`
> **仓库地址**：<https://github.com/EthanLyu30/dashcam-semantic-recall>
> **当前分支**：`lxy`（阶段二开发分支）

本项目是苏州大学综合项目实践课题——**基于多模态大模型的行车记录仪视频语义检索与精准回放系统**——的实现仓库。系统把长时段行车记录仪视频转换成可被自然语言检索的语义事件，让用户用一句"找一下白色车违停的片段"就能跳到对应时间点，并导出包含视频片段、截图、摘要的证据包。

需求文档、概要设计、原型设计、阶段一报告均位于父目录 `D:\苏大\综合项目实践\`。

---

## 项目分工

> 详细任务清单见 [`docs/ni-yuchen-todolist.md`](docs/ni-yuchen-todolist.md) 和 [`docs/lv-xiaoyang-completed.md`](docs/lv-xiaoyang-completed.md)。

**吕霄阳** —— 桌面客户端、完整后端服务、原型迁移、演示层
- Qt6 桌面端复刻 DVR-Semantic 交互原型（11 个页面全量落地）
- 完整后端服务层：auth / audit / media\_pipeline / model\_adapter / hybrid\_search / exporter / event\_aggregator
- SQLite 核心数据库（9 张业务表）+ 40 个自动化测试
- Mock 数据、REST 契约对接、最终演示流程

**倪羽辰** —— 真实链路验证、数据库升级、复核接口
- **必做**：用真实行车视频 + 真实模型 API Key 跑通完整演示链路
- **必做**：将 SQLite 升级为 PostgreSQL + pgvector（真实向量检索）
- **必做**：补全人工复核 API（`POST /review/tasks/{id}/decision` 真实写库）
- **建议做**：后端技术实现说明文档、Docker Compose 一键启动

---

## 阶段二已实现（`lxy` 分支当前状态）

阶段一已完成（`main` 分支保留）：原型复刻、Qt6 多页面、Mock 数据契约。

阶段二在 `lxy` 分支新增：

| 模块 | 内容 |
|---|---|
| 真实后端 | SQLAlchemy + SQLite，9 张业务表对齐《概要设计 V4.0》第 4 章；FastAPI 整合所有服务 |
| ffmpeg 媒体流水线 | 上传 → 转码 → 30s 切片 → 1 帧/3s 抽取 → 640px 缩略图 |
| 多模态模型适配层 | mock / DeepSeek-VL / 通义千问 Qwen-VL 一键切换，OpenAI 兼容协议 |
| 语义事件聚合 | 相邻 ≤10s 同类型帧合并，置信度阈值进复核队列 |
| 混合检索 | 向量召回（sentence-transformers 可选 + hash-ngram 降级）+ 关键词重排 |
| 证据导出 | ffmpeg 真切片 + 截图 + JSON/Markdown 摘要 + zip 打包 |
| 鉴权与审计 | bcrypt + PyJWT Bearer Token，三个种子账号，写操作全部留痕 |
| 真 VLC 播放 | `python-vlc` 嵌入 QFrame；未装 VLC 自动降级到占位提示 |
| 测试 | 40 个测试全部通过，含端到端 `test_api_integration.py` 串通 login → upload → process → search → export |
| UI 滚动 | 所有内容页包裹 `QScrollArea`，窗口较小时可纵向滚动，内容不再被截断 |
| 登录流程规范化 | 登录已从顶部导航栏移除；启动时若设置 `DVR_SEMANTIC_API_BASE` 则弹登录对话框，⏻ 按钮改为退出确认 |
| 按钮响应 | 所有展示型按钮接入 `_wip_button()`，点击弹"功能开发中"提示，不再静默无响应 |

详细进度与剩余事项见 `plans/IMPL_PLAN.md`，需求实现状态见 `docs/requirements-trace.md`。

---

## 如何运行项目

### 一、环境准备（首次运行需要）

#### 1. Python 3.10+
```powershell
python --version    # 应当 ≥ 3.10
```

#### 2. ffmpeg（视频预处理 / 证据导出必需）
- Windows：`winget install Gyan.FFmpeg` 或者从 <https://ffmpeg.org/download.html> 下载放进 PATH
- 验证：`ffmpeg -version` 能看到版本号即可

#### 3. VLC media player（真实视频播放，可选）
- Windows：`winget install VideoLAN.VLC`
- 不装也能跑——客户端会自动降级到占位提示，但视频区不会真播放

#### 4. 创建虚拟环境并安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e ".[dev,desktop,backend,media,ai]"
```

`pyproject.toml` 里的 extras 含义：
- `dev` — pytest 等测试依赖
- `desktop` — PySide6（Qt6 客户端）+ python-vlc
- `backend` — FastAPI、uvicorn、Pydantic
- `media` — ffmpeg-python、Pillow
- `ai` — sentence-transformers（可选；不装会自动用 hash-ngram 降级）

---

### 二、两种运行方式

#### 方式 A：Mock 模式（最快，无需后端）

桌面客户端使用内置 mock 数据，**不连接后端**，适合快速演示界面。

```powershell
python apps/desktop_client/main.py
```

启动后直接进入主界面（不弹登录窗），看到两段 demo 视频和 5 条预置事件。

#### 方式 B：真后端模式（完整链路）

需要分别启动后端和客户端，**两个终端窗口**。

**终端 1 — 启动后端**：

```powershell
.\.venv\Scripts\activate
uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000
```

成功后访问 <http://127.0.0.1:8000/health> 应看到 `{"status":"ok","version":"0.2.0"}`。

API 接口文档自动生成：<http://127.0.0.1:8000/docs>

**终端 2 — 启动桌面客户端并指向后端**：

```powershell
.\.venv\Scripts\activate
$env:DVR_SEMANTIC_API_BASE="http://127.0.0.1:8000"
python apps/desktop_client/main.py
```

弹出登录窗后用以下任一种子账号登录：

| 用户名 | 密码 | 角色 | 权限 |
|---|---|---|---|
| `admin` | `admin123` | 管理员 | 全部接口 |
| `reviewer` | `review123` | 审核员 | 复核相关接口 + 审计日志 |
| `demo` | `demo123` | 普通用户 | 检索、上传、导出 |

---

### 三、演示主流程（真后端模式）

登录后按这个顺序操作可以走通一条完整链路：

1. **顶部导航点"视频流"** → 视频库管理页
2. 点 **"上传视频"** → 选一段 30~90 秒的 mp4（建议短视频，首次处理较慢）
3. 等待状态变成 `indexed`（后端会自动执行：ffprobe → 切片 → 抽帧 → 模型分析 → 事件聚合）
4. **顶部点"检索"** 进入语义检索中心
5. 在搜索框输入 **"找一下违停"** 或点击推荐场景 **「违停」** 芯片，回车
6. 左侧出现命中结果卡片（左色块显示置信度，右侧标题/时间/相关度/摘要/标签）
7. 点击任一结果 → 右侧 **VLC 真实播放视频** 并 seek 到事件起点
8. 同时**时间轴**高亮该事件，**详情面板**显示三个 metric（置信度/相关度/复核状态）
9. 点 **"导出证据包"** → 后端用 ffmpeg 切一段视频 + 抽帧截图 + 生成 JSON/Markdown 摘要 → 打成 zip
10. 弹窗提示导出路径（`var/media/exports/<eventId>/package.zip`），解压即可看到 4 个文件

---

### 四、可选：接入真实多模态模型

默认使用 `mock` 适配器，输出确定性的伪标签用于演示。要接真模型：

```powershell
# 接 DeepSeek-VL
$env:MODEL_PROVIDER="deepseek"
$env:MODEL_API_KEY="sk-xxxxx"
$env:MODEL_BASE_URL="https://api.deepseek.com/v1"

# 或接通义千问 Qwen-VL
$env:MODEL_PROVIDER="qwen"
$env:MODEL_API_KEY="sk-xxxxx"
$env:MODEL_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

# 之后正常启动后端
uvicorn apps.backend.main:app --port 8000
```

模型层是 OpenAI 兼容协议，DeepSeek 和千问都直接接入；网络失败时静默回退到 mock 标签，不会让 demo 崩溃。

---

### 五、运行测试

```powershell
python -m pytest -q
```

预期输出：`40 passed in ~25s`。

测试覆盖：

| 测试文件 | 覆盖范围 |
|---|---|
| `test_media_pipeline.py` | 上传 / probe / 切片 / 抽帧 / 缩略图 |
| `test_model_adapter.py` | mock 适配器 + OpenAI 协议解析 + 网络 fallback |
| `test_event_aggregator.py` | 帧分析驱动 + 滑窗合并 + 状态推进 |
| `test_hybrid_search.py` | encode + ensure_embeddings + 关键词重排 |
| `test_exporter.py` | 真 ffmpeg 切片 + zip 打包验证 |
| `test_auth_audit.py` | JWT 闭环 + bcrypt + 角色 + 审计日志 |
| `test_api_integration.py` | 端到端 login→upload→process→search→export |
| `test_login_dialog.py` | PySide6 登录对话框（headless 环境跳过） |
| `test_client_api.py` / `test_backend_search.py` | 已有契约保持兼容 |

---

## 真实跑通 vs mock 一览

> 这一节回答：「现在哪些是真的能跑、哪些用的是 mock？」
> 不夸大、不藏丑，按模块列。

| 模块 | 状态 | 说明 |
|---|---|---|
| FastAPI 后端 + SQLite 9 表 | ✅ 真跑 | `uvicorn` 启动后，所有 REST API 都是真路由 + 真数据库 |
| JWT 登录 / bcrypt / 审计日志 | ✅ 真跑 | 登录返回真 token；每次操作写 `audit_logs` |
| 视频上传 / ffmpeg 抽帧/切片/缩略图 | ✅ 真跑 | `apps/backend/dvr_semantic_backend/services/media_pipeline.py` 调真 ffmpeg |
| 嵌入检索（向量召回 + 关键词） | ✅ 真跑 | 装了 `sentence-transformers` 走真向量；没装走 hash-ngram fallback（也是真计算，不是预写答案） |
| 证据导出 zip 打包 | ✅ 真跑 | 真把片段 + 关键帧 + 元数据打 zip 到 `media/exports/` |
| 多模态视觉理解（DeepSeek-VL / 通义千问 VL） | ⚠️ 默认 mock，配 API key 后真跑 | `MockAdapter` 基于文件名+SHA-256 给确定性伪标签；配 `MODEL_PROVIDER=qwen` + `MODEL_API_KEY=sk-...` 后走 `OpenAICompatibleAdapter` 真请求通义千问 VL，DeepSeek 同理 |
| VLC 视频回放 | ✅ 真跑 | 你已经装了 VLC 3.0.23；客户端用 `python-vlc` 真嵌入播放 |
| 桌面客户端默认数据源 | mock | 不传 `--base-url` 时用 `apps/desktop_client/dvr_semantic_client/mock_client.py` 的演示数据 |

### 想要"真后端 + 真视频 + 真视觉模型"全链路跑通，4 步：

```powershell
# 1. 启 backend（默认 mock 模型适配器；下一步会切真模型）
$env:MODEL_PROVIDER = "qwen"          # 或 "deepseek"
$env:MODEL_API_KEY  = "sk-xxxxxxxx"   # 通义千问的 dashscope key，或 deepseek key
# $env:MODEL_NAME   = "qwen-vl-plus"  # 可选，默认 qwen-vl-plus / deepseek-vl
python -m apps.backend.main           # 监听 8000

# 2. 另开一个 PowerShell 启客户端，连真后端
python tools/run_qt_client.py --base-url http://localhost:8000

# 3. 用客户端登录（默认账户 admin / admin123），到「视频流」页面上传一段 mp4
#    ffmpeg 抽帧 + 通义/DeepSeek 视觉理解会真打远程 API，处理完状态变 "searchable"

# 4. 回「检索」页面，输入自然语言查询，看到的就是真模型识别的事件
```

### 不想花钱调真模型，只想看演示？

直接 `python tools/run_qt_client.py`（不带 `--base-url`），全部走 mock，5 秒就能看到完整 UI 联动。**这也是阶段二汇报演示推荐的路径**——稳定、确定性、不依赖外网。

---

## 项目结构速查

```
dashcam-semantic-recall/
├── apps/
│   ├── backend/                    # FastAPI 后端
│   │   ├── main.py                 # 应用入口
│   │   └── dvr_semantic_backend/
│   │       ├── api.py              # 所有路由整合
│   │       ├── db.py               # SQLAlchemy ORM (9 张表)
│   │       ├── schemas.py          # Pydantic 模型
│   │       └── services/           # 业务服务层
│   │           ├── media_pipeline.py    # ffmpeg 流水线
│   │           ├── model_adapter.py     # 多模态模型适配
│   │           ├── event_aggregator.py  # 事件聚合
│   │           ├── hybrid_search.py     # 混合检索
│   │           ├── exporter.py          # 证据导出
│   │           ├── auth.py              # JWT 鉴权
│   │           └── audit.py             # 审计日志
│   └── desktop_client/             # Qt6 桌面端
│       ├── main.py                 # 应用入口
│       └── dvr_semantic_client/
│           ├── app.py              # 启动流程（mock vs REST 判定）
│           ├── api.py              # MockApiClient + RestApiClient
│           ├── models.py           # dataclass 模型
│           ├── resources/theme.qss # 全局样式
│           └── widgets/            # 各 UI 组件
│               ├── main_window.py
│               ├── search_panel.py
│               ├── video_player.py     # python-vlc 嵌入
│               ├── timeline.py
│               ├── event_detail.py
│               ├── result_card.py
│               ├── login_dialog.py
│               └── pages.py            # 11 个原型页面
├── docs/
│   ├── prototype-source/           # 阶段一原型 (HTML+Tailwind)
│   ├── phase2-report/              # 阶段二汇报 (HTML PPT + 截图)
│   ├── requirements-trace.md       # 需求实现追踪
│   └── api-contract.md
├── plans/
│   ├── IMPL_PLAN.md                # 阶段二实施清单
│   └── phase-2-roadmap.md
├── tests/                          # 40 个自动化测试
├── tools/
│   └── capture_screenshots.py      # 自动抓取 Qt 客户端截图
├── var/                            # 运行时产物（git ignore）
│   ├── dvr_semantic.db             # SQLite 数据
│   └── media/                      # ffmpeg 中间产物
│       ├── originals/
│       ├── segments/
│       ├── frames/
│       ├── thumbnails/
│       └── exports/
├── pyproject.toml
├── README.md                       # 本文件
├── DESIGN.md                       # 视觉设计参考
└── AGENTS.md                       # AI 协作指南
```

---

## 常见问题

**Q：客户端启动报"libvlc.dll not found"？**
A：python-vlc 安装了但系统 VLC 没装。`winget install VideoLAN.VLC` 装好就行；或者临时设置 `$env:DVR_DISABLE_VLC="1"` 跳过 VLC（视频区显示占位提示）。

**Q：上传视频后状态一直停在 `preprocessing` 或 `analyzing`？**
A：检查 ffmpeg 是否在 PATH（`ffmpeg -version`）。上传是同步的，长视频可能需要等几十秒。

**Q：检索时报"401 Unauthorized"？**
A：Bearer Token 过期。退出客户端重新登录即可。

**Q：mock 适配器输出的事件不稳定？**
A：mock 是基于文件名 + SHA-256 散列的伪标签，**对同一段视频会输出确定性结果**。但不同视频间会有差异。演示前建议先固定一段视频处理一次，库里有事件后再演示检索。

**Q：想关闭真 VLC，只看占位界面？**
A：`$env:DVR_DISABLE_VLC="1"` 启动客户端。

**Q：顶部导航找不到"登录"按钮？**
A：登录入口已从导航栏移除。设置 `DVR_SEMANTIC_API_BASE` 后启动客户端，程序启动时会自动弹出登录对话框。不设置则直接以演示用户进入 mock 模式。右上角 ⏻ 按钮现在是退出登录确认对话框。

---

## 参考资料

- 需求规格说明书：`D:\苏大\综合项目实践\SRS_v6_editable - v3.0.docx`
- 概要设计说明书 V4.0：`D:\苏大\综合项目实践\output\doc\概要设计说明书-V4.0.docx`
- 阶段一报告：`D:\苏大\综合项目实践\output\1stage-report-dashcam-ai.pdf`
- 开题报告：`D:\苏大\综合项目实践\output\opening-report-dashcam-ai.pptx`
- 交互原型源码：`docs/prototype-source/`
- 阶段二汇报 PPT：`docs/phase2-report/phase2-report.html`（浏览器打开）

---

## 开发原则

参考以下范式：

- **Hermes Agent**：明确的项目指南、skills、工具/服务、计划与稳定契约
- **Karpathy 规范**：最小作用域、外科级改动、明确成功标准、闭环验证
- **DESIGN.md 模式**：根目录的设计系统文档，让 AI 协作者保持一致的输出

新增模块或修改 API 前请先看 `AGENTS.md`。
