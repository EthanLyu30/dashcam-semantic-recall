# Phase 2 Implementation Plan — lxy 分支

本文件追踪 `lxy` 分支上对应"第二阶段实现"的工作清单。打钩项已落代码 + 单测；未打钩项是阶段汇报当周不打算硬塞的部分。

## 已实现

### 后端 / 数据层
- [x] SQLAlchemy + SQLite，9 张业务表（users / videos / video_segments / frame_analysis / semantic_events / search_queries / search_results / event_exports / audit_logs），字段命名与概要设计 V4.0 第 4 章一致。
- [x] ffmpeg 真实媒体预处理：上传保存 → ffprobe 元数据 → H.264/AAC 转码 → 30s 切片 → 1 帧/3s 抽取 → Pillow 640px 缩略图。
- [x] 多模态模型适配层 `services/model_adapter.py`：Protocol + `MockAdapter`（基于文件名启发式 + 确定性散列）+ `OpenAICompatibleAdapter`（同时支持 DeepSeek-VL 和 Qwen-VL，OpenAI 兼容协议、懒加载 SDK、网络失败静默 fallback）。`MODEL_PROVIDER` 环境变量切换。
- [x] 帧分析驱动 + 语义事件聚合：滑窗合并相邻同类型帧（≤10s），低置信进 `reviewing`，状态机推进到 `indexed`。
- [x] 向量+关键词混合检索：sentence-transformers 可用时走真 embedding，否则字符 n-gram 哈希 384 维降级；`final = 0.6*vec + 0.4*keyword`；写 `SearchQuery` 和 `SearchResult` 留痕。
- [x] 证据导出：ffmpeg 真切片 + 截图 + JSON/Markdown 摘要 + zip 打包；写 `event_exports` 表。
- [x] 鉴权：bcrypt 密码 + PyJWT Bearer Token；三个种子账号（admin/reviewer/demo）；`require_auth` / `require_role` FastAPI 依赖。
- [x] 审计日志中间件：写操作全部进 `audit_logs`，每次请求带 `X-Request-Id` 头便于排障。
- [x] FastAPI 路由整合：login / videos / upload / preprocess / analyze / one-shot process / stream / events / review / search / export / audit logs。

### 桌面端
- [x] `python-vlc` 真播放：`vlc.MediaPlayer` 嵌入 QFrame，Windows `set_hwnd` / X11 `set_xwindow` / mac `set_nsobject`；500ms 进度同步；VLC 未装时降级 QLabel + 虚拟时间游标。
- [x] LoginDialog + LoginContext：非 mock 模式启动时拉取 token。
- [x] 视频库管理页改成真上传 + 处理 + 实时刷新（QFileDialog → `POST /api/videos/upload` → `POST /api/videos/{id}/process`）。
- [x] RestApiClient 全面带 Bearer 头；MockApiClient 保留所有路径可演示。

### 测试
- [x] 单测覆盖：media_pipeline / model_adapter / event_aggregator / hybrid_search / exporter / auth+audit / login_dialog / client_api。
- [x] 端到端集成测试 `test_api_integration.py`：login → upload → process → search → export 真跑通 FastAPI TestClient。
- [x] 39 passed / 1 skipped（PySide6 在 headless 环境跳过）。

## 暂未实现 / 阶段汇报要诚实说明

- [ ] **真正的多模态模型调用**：代码路径完整可跑通，但默认环境用 `MODEL_PROVIDER=mock`。要演示真模型只需 `.env` 写 DeepSeek 或千问 key，但本周课程演示用 mock 保稳定性。
- [ ] **pgvector / PostgreSQL**：本期统一走 SQLite + 内存余弦相似度，切换到 pgvector 只需要改 DATABASE_URL 和 ensure_embeddings 写库逻辑。
- [ ] **sentence-transformers 真 embedding**：依赖未默认安装（~400MB 模型），代码 `ensure_embeddings` 已支持，启用方式 `pip install sentence-transformers + DVR_SEMANTIC_USE_EMBEDDINGS=1`。
- [ ] **HLS 点播**：视频流目前直接 `FileResponse` 整文件，未做 HLS 切片对外。VLC 拉本地或 stream URL 都能播。
- [ ] **批量上传**：现在一次一个视频；批量上传与并发任务队列未做。
- [ ] **告警管理 / 全天业务报告 / 模型与安全配置**：页面仍是静态展示，未接真数据。
- [ ] **PDF 摘要**：导出包里目前是 Markdown + JSON，PDF 渲染留到后续。
- [ ] **任务异步队列**：upload/process 是同步阻塞调用，长视频会卡住请求。后续应该上 Celery 或 asyncio.create_task + WebSocket 进度推送。
- [ ] **权限页 / 角色编辑 UI**：仅后端 `users.role` 字段就绪，UI 没接。
- [ ] **检索结果中的"命中理由"**：现在只是按事件类型拼模板话术，未让模型生成"为什么命中"。

## 演示链路（下周阶段汇报建议演示路径）

```
.env 设置 MODEL_PROVIDER=mock
uvicorn apps.backend.main:app --reload --port 8000
DVR_SEMANTIC_API_BASE=http://127.0.0.1:8000 python apps/desktop_client/main.py
→ 登录 demo/demo123
→ 视频库管理 → 上传一段 10–60s 测试视频 → 等 frames_analyzed > 0 / status=indexed
→ 语义检索中心 → 输入"找一下违停"或"剐蹭"
→ 选中一个结果 → 真 VLC seek 到事件起点
→ 右下角"导出证据包" → 弹出 zip 路径，含 clip.mp4 / snapshot.jpg / report.md / report.json
```

## 已知风险

- mock adapter 是基于文件名 + 时间散列的伪标签，事件分布**不稳定**：用同一段视频跑两次可能出不同事件。演示时建议固定一段视频先跑一次，库里有事件后再演示检索。
- 第一次安装时 `pip install -e .[backend,desktop,media,dev]` 必须装齐，否则导出 / 上传 / 播放任一环节会缺包。
- 长视频（>5 分钟）首次 process 比较慢，演示建议截 30–90s 的素材。
