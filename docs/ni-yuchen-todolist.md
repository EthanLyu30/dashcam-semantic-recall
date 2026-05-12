# 倪羽辰后端与 AI 部分 TODO List（更新版）

> **背景说明**：lxy 分支在开发过程中已将原分工中大部分后端基础设施实现完毕（auth、db、media_pipeline、model_adapter、hybrid_search、exporter、event_aggregator、audit、40 个测试）。倪羽辰不需要重复实现这些，直接在此基础上承担以下任务即可。

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

### 2. 替换数据库为 PostgreSQL + pgvector

当前 lxy 实现使用 SQLite（降级方案），原分工要求 pgvector 向量检索。

- [ ] 本地或 Docker 搭建 PostgreSQL + pgvector。
- [ ] 将 `apps/backend/dvr_semantic_backend/db.py` 中的 SQLite 连接替换为 psycopg2/asyncpg。
- [ ] 为 `semantic_events` 表的 embedding 字段启用 `vector` 类型和 HNSW 索引。
- [ ] 将 `hybrid_search.py` 中的余弦相似度 fallback 替换为真实 pgvector `<=>` 查询。
- [ ] 确认 40 个现有测试在新数据库下仍然通过。

### 3. 补全人工复核 API

复核接口目前是 stub，Qt 复核页的"提交复核结果"需要真实逻辑。

- [ ] 实现 `POST /api/review/tasks/{event_id}/decision`：接收 `verdict`（pass/reject/doubt）、`notes`、修正后的 `title`/`tags`，写入 `semantic_events` 并记录审计日志。
- [ ] 实现 `GET /api/review/tasks`：返回 `review_status=reviewing` 的事件列表，供 Qt 复核页加载队列。
- [ ] 在 Qt 复核页的任务列表点击时调用此接口（与吕霄阳联调）。

---

## 建议做（加分项）

### 4. 视频流接口对接 VLC

- [ ] 确认 `GET /api/videos/{video_id}/stream` 返回可播放的 URL（本地 HTTP 或文件路径）。
- [ ] 与吕霄阳联调：在 Qt 客户端设置 `DVR_SEMANTIC_API_BASE` 后，VLC 能实际播放视频而不是占位模式。

### 5. 后端技术实现说明

- [ ] 写 1-2 页文档（Markdown 或 PDF），说明：模型 Prompt 设计、帧分析到事件聚合逻辑、检索排序策略、证据导出流程。
- [ ] 供答辩时解释自己实现的代码，以及最终报告引用。

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
| 核心数据库表（SQLite） | `db.py` | ✅（待替换为 PostgreSQL） |
| 后端单元测试 + 集成测试 40 个 | `tests/` | ✅ |

---

## 与吕霄阳的联调约定

- 接口字段不随意改动：`video_id`、`event_id`、`start_sec`、`end_sec`、`confidence`、`thumbnail_url`。
- 如必须改接口，先改 `docs/api-contract.md`，再通知吕霄阳同步客户端 DTO。
- 联调时吕霄阳设置环境变量 `DVR_SEMANTIC_API_BASE=http://localhost:8000` 切换到真实后端。
