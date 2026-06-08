# Historical Implementation Plan

本文件保留阶段二实施记录。最终交付验收以 `plans/final-stage-delivery.md` 为准。

## 已实现

### 后端 / 数据层
- [x] SQLAlchemy + SQLite/PostgreSQL 双引擎，9 张业务表（users / videos / video_segments / frame_analysis / semantic_events / search_queries / search_results / event_exports / audit_logs），字段命名与概要设计 V4.0 第 4 章一致。
- [x] PostgreSQL 原生 `REAL[]` 向量存储 + `cosine_similarity()` 存储函数；SQLite 自动降级为 JSON embedding + Python numpy 余弦，测试环境不依赖 PG。
- [x] ffmpeg 真实媒体预处理：上传保存 → ffprobe 元数据 → H.264/AAC 转码 → 30s 切片 → 1 帧/3s 抽取 → Pillow 640px 缩略图。
- [x] 多模态模型适配层 `services/model_adapter.py`：Protocol + `MockAdapter`（基于文件名启发式 + 确定性散列）+ `OpenAICompatibleAdapter`（同时支持 DeepSeek-VL 和 Qwen-VL，OpenAI 兼容协议、懒加载 SDK、网络失败静默 fallback）。`MODEL_PROVIDER` 环境变量切换。
- [x] 帧分析驱动 + 语义事件聚合：滑窗合并相邻同类型帧（≤10s），低置信进 `reviewing`，状态机推进到 `indexed`。
- [x] 向量+关键词混合检索：sentence-transformers 可用时走真 embedding，否则字符 n-gram 哈希 384 维降级；`final = 0.6*vec + 0.4*keyword`；写 `SearchQuery` 和 `SearchResult` 留痕。
- [x] 证据导出：ffmpeg 真切片 + 截图 + JSON/Markdown 摘要 + zip 打包；写 `event_exports` 表；`/api/exports` 返回契约化列表。
- [x] 鉴权：bcrypt 密码 + PyJWT Bearer Token；三个种子账号（admin/reviewer/demo）；`require_auth` / `require_role` FastAPI 依赖。
- [x] 审计日志中间件：写操作全部进 `audit_logs`，每次请求带 `X-Request-Id` 头便于排障。
- [x] FastAPI 路由整合：login / videos / upload / preprocess / analyze / one-shot process / stream / events / review / search / export / audit logs。
- [x] Final-stage 管理面 API：dashboard / alerts / accidents / reports / settings / users / roles / permissions。

### 桌面端
- [x] `python-vlc` 真播放：`vlc.MediaPlayer` 嵌入 QFrame，Windows `set_hwnd` / X11 `set_xwindow` / mac `set_nsobject`；500ms 进度同步；VLC 未装时降级 QLabel + 虚拟时间游标。
- [x] LoginDialog + LoginContext：非 mock 模式启动时拉取 token。
- [x] 视频库管理页改成真上传 + 处理 + 实时刷新（QFileDialog → `POST /api/videos/upload` → `POST /api/videos/{id}/process`）。
- [x] RestApiClient 全面带 Bearer 头；MockApiClient 保留所有路径可演示。

### 测试
- [x] 单测覆盖：media_pipeline / model_adapter / event_aggregator / hybrid_search / exporter / export_routes / final_stage_api / auth+audit / login_dialog / client_api。
- [x] 端到端集成测试 `test_api_integration.py`：login → upload → process → search → export 真跑通 FastAPI TestClient。
- [x] 51 个自动化用例；当前环境 `45 passed, 6 skipped`（可选桌面/媒体环境与 ffmpeg 相关用例会按依赖自动跳过）。

## 后续产品化增强（不阻塞课程 final-stage 交付）

- [ ] **sentence-transformers 真 embedding**：依赖未默认安装（~400MB 模型），代码 `ensure_embeddings` 已支持，启用方式 `pip install sentence-transformers + DVR_SEMANTIC_USE_EMBEDDINGS=1`。
- [ ] **HLS 点播**：视频流目前直接 `FileResponse` 整文件，未做 HLS 切片对外。VLC 拉本地或 stream URL 都能播。
- [ ] **批量上传**：现在一次一个视频；批量上传与并发任务队列未做。
- [ ] **证据包 PDF 摘要**：导出包里目前是 Markdown + JSON，PDF 渲染留到后续。
- [ ] **任务异步队列**：upload/process 是同步阻塞调用，长视频会卡住请求。后续应该上 Celery 或 asyncio.create_task + WebSocket 进度推送。
- [ ] **权限页 / 角色编辑 UI**：后端角色/权限字典已完成，复杂编辑流可后续产品化。
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

- mock adapter 是基于文件名 / hint 的 SHA-256 确定性伪标签：同一段视频重复处理结果稳定，但不代表真实视觉理解效果。答辩如要展示识别质量，应使用真实模型 API Key 跑一遍样例视频。
- 第一次安装时 `pip install -e .[backend,desktop,media,dev]` 必须装齐，否则导出 / 上传 / 播放任一环节会缺包。
- 长视频（>5 分钟）首次 process 比较慢，演示建议截 30–90s 的素材。
