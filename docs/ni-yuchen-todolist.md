# 倪羽辰后端与 AI 部分最终交付记录

> **背景说明**：final-stage 已把后端主链路和管理面 API 收口到可交付状态。本文档保留倪羽辰侧数据库、检索、复核、真实模型联调责任口径，不再作为未完成 TODO 清单。
>
> **2026-05-16 更新**：leonore 分支已合入 main。任务 2（PostgreSQL 双引擎）和任务 3（复核 API）✅ 已完成；后端技术说明文档和 ffmpeg 安装脚本也已提交。

---

## ★ 答辩核心能力

### 1. 用真实数据跑通主链路

这是最终演示建议动作，API key 只在本机环境变量设置，不提交仓库。

- [x] 后端已支持 `MODEL_PROVIDER=deepseek/qwen` + `MODEL_API_KEY` 的 OpenAI-compatible 调用路径。
- [x] 网络或模型失败时自动回退 mock，保证现场演示不崩。
- [x] Qt 客户端可通过 `DVR_SEMANTIC_API_BASE` 切换真实后端。
- [x] 证据导出、审计日志、复核 API、管理面 API 已完成。
- [ ] 答辩前本机准备 1-3 段真实行车记录仪视频并截图留档。

### 2. ✅ 替换数据库为 PostgreSQL 双引擎（已完成）

- [x] `db.py` 改为双引擎：`IS_SQLITE` 标志自动路由；默认连接 `postgresql://postgres:postgres@localhost:5432/dvr_semantic`，测试环境通过 `pytest-env` 强制 SQLite 内存库。
- [x] `semantic_events.embedding` 列：SQLite 用 `JSON`，PostgreSQL 用 `REAL[]` 原生数组。
- [x] `init_db()` 在 PG 上自动创建 `cosine_similarity(double precision[], double precision[])` PL/pgSQL 存储函数。
- [x] `hybrid_search.py` 分叉：PG 使用 `cosine_similarity()` 存储函数在库内做向量排序；SQLite 继续用 Python numpy 余弦降级。
- [x] `pyproject.toml` 新增 `pytest-env`，`DVR_SEMANTIC_DB_URL=sqlite:///:memory:` 确保 44 个测试不依赖 PG。

### 3. ✅ 补全人工复核 API（已完成）

- [x] `GET /api/review/tasks`：按 `review_status` 过滤，支持 `event_type` 筛选与分页（`page` + `page_size`），返回 `ReviewTaskListResponse`。
- [x] `POST /api/review/tasks/{event_id}/decision`：接收 `decision`（confirmed/rejected/pending）+ 可选的修正 `event_type`/`title`/`tags` + `note`，更新 `semantic_events` 并记录 `review.decision` 审计日志。
- [x] 新增 Pydantic schema：`ReviewDecisionRequest`、`ReviewTaskItem`、`ReviewTaskListResponse`、`ReviewDecisionResponse`。
- [ ] Qt 复核页任务列表接入真实接口（待与吕霄阳联调）。

---

## 建议做（加分项）

### 4. 视频流接口对接 VLC

- [x] `GET /api/videos/{video_id}/stream` 返回 `FileResponse`，客户端 `RestApiClient.stream_url()` 直接交给 VLC。
- [x] Qt 客户端设置 `DVR_SEMANTIC_API_BASE` 后走真实 HTTP 视频流；未装 VLC 时自动降级占位。

### 5. ✅ 后端技术实现说明（已完成）

- [x] `docs/backend-tech-notes.md`（298 行）：涵盖 PG 双引擎设计、向量存储、Qwen-VL 接入、事件聚合算法、复核 API、证据导出、鉴权与审计。

---

## 可选（时间充裕再做）

### 6. Docker Compose 一键启动

- [ ] 编写 `docker-compose.yml`：包含 PostgreSQL、FastAPI 后端两个服务；当前实现不依赖 pgvector 扩展。
- [ ] 确保 `docker compose up` 后不需要额外配置即可启动后端。
- [ ] 更新 README 启动说明。

> Docker Compose 属于部署便利项，不阻塞课程 final-stage 交付；当前 README 已提供 SQLite 零安装和 PostgreSQL 手动启动两条路径。

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
| 后端单元测试 + 集成测试 44 个 | `tests/` | ✅ |

---

## 与吕霄阳的联调约定

- 接口字段不随意改动：`video_id`、`event_id`、`start_sec`、`end_sec`、`confidence`、`thumbnail_url`。
- 如必须改接口，先改 `docs/api-contract.md`，再通知吕霄阳同步客户端 DTO。
- 联调时吕霄阳设置环境变量 `DVR_SEMANTIC_API_BASE=http://localhost:8000` 切换到真实后端。
