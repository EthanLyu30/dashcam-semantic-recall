# Requirements Trace

最后更新：2026-06-08（final-stage 交付 + 导出去重/批量 + P0 安全加固 + FR-06 第三方接口 + NFR-02 重试 + 检索召回/性能基准）

| 需求 | 当前状态 | 主要落点 | 责任人 |
| --- | --- | --- | --- |
| FR-01 视频接入与预处理 | 已实现（同步处理 + 进度轮询；上传 10GB 上限校验） | `services/media_pipeline.py`、`POST /api/videos/upload`（≤10GB/413）、`POST /api/videos/{id}/preprocess`、`GET /api/videos/{id}/status` 进度轮询 | 吕霄阳 |
| FR-02 关键帧分析 + 语义事件聚合 | 已实现（模型默认走 mock，可一键切 DeepSeek/千问） | `services/model_adapter.py`、`services/event_aggregator.py`、`POST /api/videos/{id}/analyze` | 吕霄阳（mock 通路） / 倪羽辰（真模型） |
| FR-03 自然语言检索 | 已实现 | `services/hybrid_search.py`、`POST /api/search`；向量降级 + 关键词混合 | 吕霄阳 |
| FR-04 精准回放 | 已实现（功能真实；跳转≤1s/启动≤2s 性能未实测） | `widgets/video_player.py` 真 VLC 播放 + seek_to_event；`GET /api/videos/{id}/stream`（已加鉴权，VLC 经 `/stream-ticket` 签名 URL 直连） | 吕霄阳 |
| FR-05 搜索结果展示 + 时间轴 | 已实现 | `widgets/search_panel.py` + `widgets/timeline.py` + `EventOut.rank_no/similarity_score/answer_text` | 吕霄阳 |
| FR-06 证据导出（单事件 + 24h 去重 + 受控批量） | 已实现 | `services/exporter.py` 真 ffmpeg 切片 + zip 打包；`POST /api/events/{id}/export`（`reused`/`force`，24h 去重）；`POST /api/exports/batch`（受控批量，≤50，失败隔离）；`GET /api/exports` 契约列表 | 吕霄阳（批量导出 + 路由） / 倪羽辰（24h 去重） |
| FR-07 操作日志 / 查询留痕 | 已实现 | `services/audit.py`、`audit_logs` 表、`X-Request-Id` 中间件、`GET /api/audit/logs` | 吕霄阳 |
| FR-08 看板 / 告警 / 事故 / 日报 | 后端已实现 / 桌面端未联调 | `services/final_stage.py`、dashboard / alerts / accidents / reports API（真实库派生，已测）；桌面端对应页面仍为静态原型布局 | 吕霄阳（框架） / 倪羽辰（数据口径） |
| FR-09 模型配置 / 用户角色权限 | 后端已实现 / 桌面端未联调 | settings / users / roles / permissions API；密钥只读配置状态，不返回明文 | 吕霄阳 |
| NFR 鉴权 + 角色 | 已实现 | `services/auth.py` bcrypt + PyJWT；`require_auth` / `require_role` | 吕霄阳 |
| NFR-05 输入校验 / 资源保护 | 已加固（HTTPS 部署期提供） | `/stream` 鉴权 + 短时效签名 ticket；`/media` 仅公开 `frames`/`thumbnails`；上传 ≤10GB（`DVR_SEMANTIC_MAX_UPLOAD_BYTES`，超限 413）；生产强制非默认 `DVR_SEMANTIC_JWT_SECRET`；HTTPS 由反代终止（代码内未内建） | 吕霄阳 |
| NFR-04 性能指标 | 检索已基准 / 其余未实测 | `test_perf_benchmark.py` 对 300 条事件断言检索 <4s；跳转≤1s/导出≤30s/2h 预处理≤8min/50 并发仍需真实负载压测，列为后续验证项 | 倪羽辰 |
| FR-03 检索召回质量 | 已加测 | `test_search_recall.py`：自然语言（不含类别名词）top-1 + 负样本断言；关键词别名扩充自然语句同义词 | 倪羽辰 |
| FR-06 第三方接口 | 已实现（API-Key 鉴权，默认关闭） | `GET /api/integration/events[/{id}]` 只读已确认事件；`X-Api-Key` 校验，`DVR_SEMANTIC_INTEGRATION_API_KEYS` 配置，未配置返回 503 | 倪羽辰 |
| NFR-02 任务可靠性 / 重试 | 已实现 | `services/retry.py` 指数退避（已接入模型调用）；`POST /api/videos/{id}/retry` 幂等重投失败任务（reviewer/admin） | 倪羽辰 |
| NFR 处理任务模式 | 可交付同步实现 | 短视频演示走同步 upload/process；生产异步队列列为后续增强 | 吕霄阳 / 倪羽辰 |
| NFR PostgreSQL 向量检索 | 已实现 | PG `REAL[]` + `cosine_similarity()` 存储函数；SQLite JSON + numpy 降级 | 倪羽辰 |
| 真多模态模型接入 | 已实现配置路径 | OpenAI 兼容协议，DeepSeek/Qwen key 通过本机环境变量启用，失败自动回退 mock | 倪羽辰 |

测试覆盖：84 个自动化测试；当前环境 `78 passed, 6 skipped`（跳过项为可选桌面/媒体环境与 ffmpeg 相关用例）。端到端 `test_api_integration.py` 串通 login → upload → process → search → export；`test_export_routes.py` 覆盖 `/api/exports`、`/api/exports/batch` 批量导出与 24h 去重复用；`test_exporter.py` 覆盖单事件导出、去重窗口、批量失败隔离；`test_security_hardening.py` 覆盖 `/stream` 鉴权 + 签名 ticket、`/media` 收窄、上传 413 上限、生产 JWT 密钥策略；`test_retry.py` 覆盖指数退避重试；`test_status_retry_routes.py` 覆盖进度轮询与重试 RBAC；`test_integration_api.py` 覆盖 FR-06 API-Key 接口；`test_search_recall.py` 覆盖自然语言召回与负样本；`test_perf_benchmark.py` 检索性能基准；`test_final_stage_api.py` 覆盖 dashboard / alerts / accidents / reports / settings / users / roles；`test_client_api.py` 覆盖 final-stage REST client。
