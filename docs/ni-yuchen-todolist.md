# 倪羽辰后端与 AI 部分 TODO List（更新版）

> **背景说明**：lxy 分支在开发过程中已将原分工中大部分后端基础设施实现完毕（auth、db、media_pipeline、model_adapter、hybrid_search、exporter、event_aggregator、audit、40 个测试）。倪羽辰不需要重复实现这些，直接在此基础上承担以下任务即可。
>
> **2026-05-16 更新**：leonore 分支已合入 main。任务 2（PostgreSQL 双引擎）和任务 3（复核 API）✅ 已完成；后端技术说明文档和 ffmpeg 安装脚本也已提交。

---

## ★ 必做（答辩核心）

### 1. 用真实数据跑通主链路

这是倪羽辰最重要的贡献，直接决定答辩能否演示真实效果。

- [ ] 配置真实模型 API Key（`MODEL_PROVIDER=qwen` + `MODEL_API_KEY=sk-xxx`）。
- [ ] 准备 1-3 段真实行车记录仪视频（含剐蹭、违停、行人鬼探头场景）。
- [ ] 上传视频、触发后端处理、确认帧分析和事件生成正常写库。
- [ ] 在 Qt 客户端输入自然语言查询，验证检索结果返回正确事件和时间戳。
- [ ] 确认点击结果后播放器跳转误差在 2 秒以内。
- [ ] 触发证据导出，确认文件生成在 `media/exports/`。
- [ ] 整理跑通截图和日志，供答辩和文档引用。

### 2. ✅ 替换数据库为 PostgreSQL + pgvector（已完成）

- [x] `db.py` 改为双引擎：`IS_SQLITE` 标志自动路由；默认连接 `postgresql://postgres:postgres@localhost:5432/dvr_semantic`，测试环境通过 `pytest-env` 强制 SQLite 内存库。
- [x] `semantic_events.embedding` 列：SQLite 用 `JSON`，PostgreSQL 用 `REAL[]` 原生数组。
- [x] `init_db()` 在 PG 上自动创建 `cosine_similarity(double precision[], double precision[])` PL/pgSQL 存储函数。
- [x] `hybrid_search.py` 分叉：PG 使用 `cosine_similarity()` 存储函数在库内做向量排序；SQLite 继续用 Python numpy 余弦降级。
- [x] `pyproject.toml` 新增 `pytest-env`，`DVR_SEMANTIC_DB_URL=sqlite:///:memory:` 确保 40 个测试不依赖 PG。

### 3. ✅ 补全人工复核 API（已完成）

- [x] `GET /api/review/tasks`：按 `review_status` 过滤，支持 `event_type` 筛选与分页（`page` + `page_size`），返回 `ReviewTaskListResponse`。
- [x] `POST /api/review/tasks/{event_id}/decision`：接收 `decision`（confirmed/rejected/pending）+ 可选的修正 `event_type`/`title`/`tags` + `note`，更新 `semantic_events` 并记录 `review.decision` 审计日志。
- [x] 新增 Pydantic schema：`ReviewDecisionRequest`、`ReviewTaskItem`、`ReviewTaskListResponse`、`ReviewDecisionResponse`。
- [ ] Qt 复核页任务列表接入真实接口（待与吕霄阳联调）。

---

## 建议做（加分项）

### 4. 视频流接口对接 VLC

- [ ] 确认 `GET /api/videos/{video_id}/stream` 返回可播放的 URL（本地 HTTP 或文件路径）。
- [ ] 与吕霄阳联调：在 Qt 客户端设置 `DVR_SEMANTIC_API_BASE` 后，VLC 能实际播放视频而不是占位模式。

### 5. ✅ 后端技术实现说明（已完成）

- [x] `docs/backend-tech-notes.md`（298 行）：涵盖 PG 双引擎设计、向量存储、Qwen-VL 接入、事件聚合算法、复核 API、证据导出、鉴权与审计。

---

## 可选（时间充裕再做）

### 6. Docker Compose 一键启动

- [ ] 编写 `docker-compose.yml`：包含 PostgreSQL、pgvector 插件、FastAPI 后端三个服务。
- [ ] 确保 `docker compose up` 后不需要额外配置即可启动后端。
- [ ] 更新 README 启动说明。

---

## 不需要再做（lxy 已实现）

以下内容已在 lxy 分支实现并通过测试，倪羽辰无需重复：

| 模块 | 文件 | 状态 |
|---|---|---|
| FastAPI 框架 + CORS + 错误响应 | `api.py` | ✅ |
| JWT + bcrypt 鉴权 | `services/auth.py` | ✅ |
| 审计日志 | `services/audit.py` | ✅ |
| 视频上传 + ffprobe + ffmpeg 转码/抽帧 | `services/media_pipeline.py` | ✅ |
| 多模态模型接入（Qwen-VL / mock） | `services/model_adapter.py` | ✅ |
| 帧分析聚合为语义事件 | `services/event_aggregator.py` | ✅ |
| 混合检索（向量 + 关键词） | `services/hybrid_search.py` | ✅ |
| 证据导出（snapshot/clip/package） | `services/exporter.py` | ✅ |
| 核心数据库层（双引擎 PG/SQLite） | `db.py` | ✅ lxy 建表 → 倪羽辰升级为 PG 双引擎 |
| 后端单元测试 + 集成测试 40 个 | `tests/` | ✅ |

---

## 与吕霄阳的联调约定

- 接口字段不随意改动：`video_id`、`event_id`、`start_sec`、`end_sec`、`confidence`、`thumbnail_url`。
- 如必须改接口，先改 `docs/api-contract.md`，再通知吕霄阳同步客户端 DTO。
- 联调时吕霄阳设置环境变量 `DVR_SEMANTIC_API_BASE=http://localhost:8000` 切换到真实后端。
