# Requirements Trace

最后更新：2026-05-11（lxy 分支阶段二）

| 需求 | 当前状态 | 主要落点 | 责任人 |
| --- | --- | --- | --- |
| FR-01 视频接入与预处理 | 已实现 | `services/media_pipeline.py`、`POST /api/videos/upload`、`POST /api/videos/{id}/preprocess` | 吕霄阳 |
| FR-02 关键帧分析 + 语义事件聚合 | 已实现（模型默认走 mock，可一键切 DeepSeek/千问） | `services/model_adapter.py`、`services/event_aggregator.py`、`POST /api/videos/{id}/analyze` | 吕霄阳（mock 通路） / 倪羽辰（真模型） |
| FR-03 自然语言检索 | 已实现 | `services/hybrid_search.py`、`POST /api/search`；向量降级 + 关键词混合 | 吕霄阳 |
| FR-04 精准回放 | 已实现 | `widgets/video_player.py` 真 VLC 播放 + seek_to_event；`GET /api/videos/{id}/stream` | 吕霄阳 |
| FR-05 搜索结果展示 + 时间轴 | 已实现 | `widgets/search_panel.py` + `widgets/timeline.py` + `EventOut.rank_no/similarity_score/answer_text` | 吕霄阳 |
| FR-06 证据导出 | 已实现 | `services/exporter.py` 真 ffmpeg 切片 + zip 打包；`POST /api/events/{id}/export` | 吕霄阳 |
| FR-07 操作日志 / 查询留痕 | 已实现 | `services/audit.py`、`audit_logs` 表、`X-Request-Id` 中间件、`GET /api/audit/logs` | 吕霄阳 |
| NFR 鉴权 + 角色 | 已实现 | `services/auth.py` bcrypt + PyJWT；`require_auth` / `require_role` | 吕霄阳 |
| NFR 异步任务队列 | 未实现 | 后续 Celery / asyncio queue | 倪羽辰 |
| NFR pgvector / PostgreSQL | 未实现（SQLite 等价替代） | 切换只改 DATABASE_URL | 倪羽辰 |
| 真多模态模型接入 | 代码就绪，演示走 mock | OpenAI 兼容协议，填 `MODEL_API_KEY` 即可启用 | 倪羽辰 |

测试覆盖：39 通过 + 1 跳过（PySide6 headless）。端到端 `test_api_integration.py` 串通 login → upload → process → search → export。
