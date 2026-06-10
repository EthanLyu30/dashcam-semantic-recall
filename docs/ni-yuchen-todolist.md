# 倪羽辰后端与 AI 部分最终交付记录

> **背景说明**：final-stage 已把后端主链路和管理面 API 收口到可交付状态。本文档保留倪羽辰侧数据库、检索、复核、真实模型联调责任口径，不再作为未完成 TODO 清单。
>
> **2026-05-16 更新**：leonore 分支已合入 main。任务 2（PostgreSQL 双引擎）和任务 3（复核 API）✅ 已完成；后端技术说明文档和 ffmpeg 安装脚本也已提交。
>
> **2026-06-10 更新**：桌面端 11 个页面已全部与真实接口联调完成（含复核页任务列表 + 真实关键帧工作台）；`/api/review/tasks` 默认改为 `pending,reviewing` 全量队列；真实视频（4 段，含约 3 小时重庆路况）已入库，最终演示截图留档在 `docs/final-demo-shots/`。

---

## ★ 答辩核心能力

### 1. 用真实数据跑通主链路

这是最终演示建议动作，API key 只在本机环境变量设置，不提交仓库。

- [x] 后端已支持 `MODEL_PROVIDER=deepseek/qwen` + `MODEL_API_KEY` 的 OpenAI-compatible 调用路径。
- [x] 网络或模型失败时自动回退 mock，保证现场演示不崩。
- [x] Qt 客户端可通过 `DVR_SEMANTIC_API_BASE` 切换真实后端。
- [x] 证据导出、审计日志、复核 API、管理面 API 已完成。
- [x] 答辩前本机准备 1-3 段真实行车记录仪视频并截图留档。（已入库 4 段真实视频：约 3 小时重庆复杂路况、2 分钟 UK 城市道路等，经 Qwen-VL 真实分析出 21 个语义事件；真实数据演示截图存于 `docs/final-demo-shots/`）

### 2. ✅ 替换数据库为 PostgreSQL 双引擎（已完成）

- [x] `db.py` 改为双引擎：`IS_SQLITE` 标志自动路由；默认连接 `postgresql://postgres:postgres@localhost:5432/dvr_semantic`，测试环境通过 `pytest-env` 强制 SQLite 内存库。
- [x] `semantic_events.embedding` 列：SQLite 用 `JSON`，PostgreSQL 用 `REAL[]` 原生数组。
- [x] `init_db()` 在 PG 上自动创建 `cosine_similarity(double precision[], double precision[])` PL/pgSQL 存储函数。
- [x] `hybrid_search.py` 分叉：PG 使用 `cosine_similarity()` 存储函数在库内做向量排序；SQLite 继续用 Python numpy 余弦降级。
- [x] `pyproject.toml` 新增 `pytest-env`，`DVR_SEMANTIC_DB_URL=sqlite:///:memory:` 确保 51 个测试不依赖 PG。

### 3. ✅ 补全人工复核 API（已完成）

- [x] `GET /api/review/tasks`：按 `review_status` 过滤，支持 `event_type` 筛选与分页（`page` + `page_size`），返回 `ReviewTaskListResponse`。
- [x] `POST /api/review/tasks/{event_id}/decision`：接收 `decision`（confirmed/rejected/pending）+ 可选的修正 `event_type`/`title`/`tags` + `note`，更新 `semantic_events` 并记录 `review.decision` 审计日志。
- [x] 新增 Pydantic schema：`ReviewDecisionRequest`、`ReviewTaskItem`、`ReviewTaskListResponse`、`ReviewDecisionResponse`。
- [x] Qt 复核页任务列表接入真实接口（已联调：队列实时拉取 pending+reviewing 全量，选中任务加载真实关键帧，提交结论写库 + 审计留痕 + 队列即时刷新）。

---

## 建议做（加分项）

### 4. 视频流接口对接 VLC

- [x] `GET /api/videos/{video_id}/stream` 返回 `FileResponse`；最终阶段已加鉴权，客户端 `RestApiClient.stream_url()` 先取 `/stream-ticket` 签名 URL 再交给 VLC。
- [x] Qt 客户端设置 `DVR_SEMANTIC_API_BASE` 后走真实 HTTP 视频流；未装 VLC 时自动降级占位。

### 5. ✅ 后端技术实现说明（已完成）

- [x] `docs/backend-tech-notes.md`（298 行）：涵盖 PG 双引擎设计、向量存储、Qwen-VL 接入、事件聚合算法、复核 API、证据导出、鉴权与审计。

### 6. ✅ 证据导出 24h 去重（最终阶段新增，已完成）

落实 SRS FR-05 "24h 内同事件去重，返回已有结果而非重复生成"：

- [x] `services/exporter._recent_success()`：查询 `event_exports` 中同事件、`status=success`、`created_at` 在 24h 窗口内且 zip 仍在磁盘上的最近一条，命中则复用。
- [x] `export_package(..., force=False)` 默认走去重，`force=True` 强制重新生成；返回新增 `reused` 字段。
- [x] 接口 `POST /api/events/{id}/export` 透传 `force` 并回传 `reused`，审计日志记录 `reused=...`。
- [x] 测试：`test_exporter.test_export_package_dedups_within_window`、`test_export_routes.test_export_reuses_recent_package`。

### 7. ✅ 文档诚实度对齐（最终阶段新增，已完成）

对抗性审计发现部分文档口径强于实现，已据实修正：

- [x] `requirements-trace.md` / README：FR-08/FR-09 标注「后端已实现 / 桌面端管理页未联调」；新增 NFR-05 资源保护与 NFR-04「性能未实测」行。
- [x] `api-contract.md`：19 个仅契约/未实现端点逐条标注 🔵 规划中，Section 16 增加「已实现 vs 仅契约」对照。
- [x] 测试计数同步为 84 个（`78 passed, 6 skipped`）。

### 8. ✅ FR-06 第三方接口（最终阶段新增，已完成）

- [x] `GET /api/integration/events[/{id}]`：对外只读已确认事件，`X-Api-Key` 鉴权（constant-time 比较）。
- [x] 密钥来自 `DVR_SEMANTIC_INTEGRATION_API_KEYS`（逗号分隔多把）；未配置整组返回 503（默认关闭）。
- [x] 审计留痕 `integration.events.list/detail`；测试 `tests/test_integration_api.py`。

### 9. ✅ NFR-02 任务可靠性 / 重试（最终阶段新增，已完成）

- [x] `services/retry.py`：有限次指数退避，`sleep` 可注入便于测试；已接入模型 API 调用（失败先重试再回退 mock）。
- [x] `POST /api/videos/{id}/retry`：reviewer/admin 幂等重投失败任务；`GET /api/videos/{id}/status` 进度轮询。
- [x] 测试 `tests/test_retry.py`、`tests/test_status_retry_routes.py`。

### 10. ✅ 检索召回质量 + 性能基准（最终阶段新增，已完成）

- [x] `hybrid_search.KEYWORD_ALIASES` 扩充自然语句同义词；`tests/test_search_recall.py` 用不含类别名词的自然语句断言 top-1 + 负样本。
- [x] `tests/test_perf_benchmark.py`：300 条事件检索 <4s（NFR-04 检索阈值）。
- [x] `tools/load_test.py` + 实跑：50 并发 500 请求实测 p50≈2.5s / **p95≈6.9s（超 4s）** / 错误率 0.2%；结论已如实写入 requirements-trace（单 worker + SQLite 写串行瓶颈）。
- [ ] 改善并发性能：多 worker + PostgreSQL + 检索写库异步化后复测达标（后续）。
- [ ] 2h/4K 预处理≤8min、跳转≤1s 仍需真机 + ffmpeg + 真实长视频，列为后续。

### 12. ✅ ffmpeg 二进制路径可配（最终阶段新增，已完成）

- [x] `media_pipeline` / `exporter` 的 `ffmpeg.probe` 与 `.run()` 改为传 `cmd=`，真正读取 `FFMPEG_BIN` / `FFPROBE_BIN` 环境变量（此前 `.env.example` 列了这两个变量但代码只认 PATH，属文档与实现不符的 bug）。
- [x] 本机已落地可用 ffmpeg 6.0（`D:\ffmpeg\bin`），经 API 端到端验证：上传 → preprocess → analyze → `frames_analyzed=4 / events_created=1 / status=indexed`。

### 11. ✅ Docker Compose 一键启动（最终阶段新增，已完成）

- [x] `Dockerfile.backend`（含 ffmpeg）+ `docker-compose.yml`（postgres:16 + 后端，健康检查 + 数据卷）。
- [x] README 增加 `docker compose up --build` 启动路径。
- [ ] 注：本机未装 Docker，compose 文件未在本环境实跑验证（需在装有 Docker 的机器 `docker compose up` 确认）。

---

## 可选（时间充裕再做）

### 6. Docker Compose 一键启动 ✅ 已完成（见第 11 节）

- [x] 编写 `docker-compose.yml`：PostgreSQL + FastAPI 后端两个服务（健康检查 + 数据卷）；不依赖 pgvector 扩展。
- [x] `Dockerfile.backend` 内置 ffmpeg，`docker compose up --build` 即可启动后端。
- [x] 更新 README 启动说明。

> Docker Compose 属于部署便利项，不阻塞课程 final-stage 交付；README 现提供 SQLite 零安装、PostgreSQL 手动、Docker Compose 三条路径。

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
| 证据导出（snapshot/clip/package + 批量 + 24h 去重） | `services/exporter.py` | ✅ lxy 批量导出 + 倪羽辰 24h 去重 |
| 核心数据库层（双引擎 PG/SQLite） | `db.py` | ✅ lxy 建表 → 倪羽辰升级为 PG 双引擎 |
| 自动化测试 84 个 | `tests/` | ✅ |

---

## 与吕霄阳的联调约定

- 接口字段不随意改动：`video_id`、`event_id`、`start_sec`、`end_sec`、`confidence`、`thumbnail_url`。
- 如必须改接口，先改 `docs/api-contract.md`，再通知吕霄阳同步客户端 DTO。
- 联调时吕霄阳设置环境变量 `DVR_SEMANTIC_API_BASE=http://localhost:8000` 切换到真实后端。
