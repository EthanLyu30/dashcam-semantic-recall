# Requirements Trace

最后更新：2026-06-06（final-stage 交付状态）

| 需求 | 当前状态 | 主要落点 | 责任人 |
| --- | --- | --- | --- |
| FR-01 视频接入与预处理 | 已实现 | `services/media_pipeline.py`、`POST /api/videos/upload`、`POST /api/videos/{id}/preprocess` | 吕霄阳 |
| FR-02 关键帧分析 + 语义事件聚合 | 已实现（模型默认走 mock，可一键切 DeepSeek/千问） | `services/model_adapter.py`、`services/event_aggregator.py`、`POST /api/videos/{id}/analyze` | 吕霄阳（mock 通路） / 倪羽辰（真模型） |
| FR-03 自然语言检索 | 已实现 | `services/hybrid_search.py`、`POST /api/search`；向量降级 + 关键词混合 | 吕霄阳 |
| FR-04 精准回放 | 已实现 | `widgets/video_player.py` 真 VLC 播放 + seek_to_event；`GET /api/videos/{id}/stream` | 吕霄阳 |
| FR-05 搜索结果展示 + 时间轴 | 已实现 | `widgets/search_panel.py` + `widgets/timeline.py` + `EventOut.rank_no/similarity_score/answer_text` | 吕霄阳 |
| FR-06 证据导出 | 已实现 | `services/exporter.py` 真 ffmpeg 切片 + zip 打包；`POST /api/events/{id}/export`；`GET /api/exports` 契约列表 | 吕霄阳 |
| FR-07 操作日志 / 查询留痕 | 已实现 | `services/audit.py`、`audit_logs` 表、`X-Request-Id` 中间件、`GET /api/audit/logs` | 吕霄阳 |
| FR-08 看板 / 告警 / 事故 / 日报 | 已实现 | `services/final_stage.py`、dashboard / alerts / accidents / reports API | 吕霄阳（框架） / 倪羽辰（数据口径） |
| FR-09 模型配置 / 用户角色权限 | 已实现 | settings / users / roles / permissions API；密钥只读配置状态，不返回明文 | 吕霄阳 |
| NFR 鉴权 + 角色 | 已实现 | `services/auth.py` bcrypt + PyJWT；`require_auth` / `require_role` | 吕霄阳 |
| NFR 处理任务模式 | 可交付同步实现 | 短视频演示走同步 upload/process；生产异步队列列为后续增强 | 吕霄阳 / 倪羽辰 |
| NFR PostgreSQL 向量检索 | 已实现 | PG `REAL[]` + `cosine_similarity()` 存储函数；SQLite JSON + numpy 降级 | 倪羽辰 |
| 真多模态模型接入 | 已实现配置路径 | OpenAI 兼容协议，DeepSeek/Qwen key 通过本机环境变量启用，失败自动回退 mock | 倪羽辰 |

测试覆盖：44 个自动化测试；当前环境预期 `40 passed, 4 skipped`。端到端 `test_api_integration.py` 串通 login → upload → process → search → export；`test_export_routes.py` 覆盖 `/api/exports`；`test_final_stage_api.py` 覆盖 dashboard / alerts / accidents / reports / settings / users / roles。
