# 倪羽辰后端与 AI 部分 TODO List

本清单是重新平衡后的版本。倪羽辰不再承担原型页面、展示看板、报告页、权限页等前端展示工作；这些由吕霄阳先用原型和 mock 数据完成。倪羽辰聚焦真实后端主链路：视频处理、模型分析、检索、数据持久化和证据导出。

## 0. 接口契约对齐

- [ ] 阅读 `docs/api-contract.md`，确认核心字段和状态枚举。
- [ ] 不随意改 `video_id`、`event_id`、`start_sec`、`end_sec`、`confidence`、`thumbnail_url`。
- [ ] 若必须改接口，先改 `docs/api-contract.md`，再通知吕霄阳同步客户端模型。

## 1. 后端基础框架

- [ ] 完善 FastAPI 项目结构。
- [ ] 实现统一错误响应。
- [ ] 接入 CORS，保证 Qt/Web 原型能访问接口。
- [ ] 接入请求日志和耗时记录。
- [ ] 保留当前 mock endpoint，逐步替换为真实实现。

## 2. 数据库核心表

只先实现主链路需要的表：

- [ ] `users`
- [ ] `videos`
- [ ] `processing_tasks`
- [ ] `video_segments`
- [ ] `frame_analysis`
- [ ] `semantic_events`
- [ ] `search_queries`
- [ ] `search_results`
- [ ] `event_exports`
- [ ] `audit_logs`

暂缓：

- [ ] `alerts`、`reports`、`roles`、`permissions`、`settings` 可先用 mock 或配置文件，不作为第一阶段后端重点。

## 3. 视频上传与预处理

- [ ] 实现 `POST /api/videos/upload`。
- [ ] 保存原始视频到 `media/originals/`。
- [ ] 使用 ffprobe 读取时长、分辨率、编码、文件大小。
- [ ] 使用 ffmpeg 转码为统一可播放格式。
- [ ] 生成封面图和关键帧。
- [ ] 按固定粒度生成切片，写入 `video_segments`。
- [ ] 实现 `GET /api/videos/{video_id}/status`。
- [ ] 实现失败重试，处理中任务禁止重复触发。

## 4. 多模态模型分析

- [ ] 设计关键帧分析 prompt。
- [ ] 调用成熟多模态模型 API。
- [ ] 要求模型返回结构化 JSON。
- [ ] 将 `description`、`tags`、`event_type`、`confidence`、`reason` 写入 `frame_analysis`。
- [ ] 聚合连续帧结果，生成 `semantic_events`。
- [ ] 对低置信事件设置 `review_status=reviewing`。

## 5. 语义检索

- [ ] 实现 `POST /api/search`。
- [ ] 第一版可以先做关键词 + 文本相似度。
- [ ] 第二版接 pgvector embedding 召回。
- [ ] 支持 `hybrid` 模式：向量召回 + 关键词回退。
- [ ] 写入 `search_queries` 和 `search_results`。
- [ ] 返回吕霄阳客户端所需字段：事件标题、摘要、标签、置信度、缩略图、开始/结束秒数。

## 6. 播放与时间轴接口

- [ ] 实现 `GET /api/videos/{video_id}/stream`。
- [ ] 实现 `GET /api/videos/{video_id}/timeline`。
- [ ] 确保时间戳基于原始视频时间轴。
- [ ] 与吕霄阳联调，点击结果后播放器跳转误差控制在 2 秒内。

## 7. 证据导出

- [ ] 实现 `POST /api/events/{event_id}/export`。
- [ ] 支持截图 `snapshot`。
- [ ] 支持短视频 `clip`。
- [ ] 支持证据包 `package`。
- [ ] 使用 ffmpeg 按事件时间段加前后缓冲裁剪。
- [ ] 写入 `event_exports`。
- [ ] 实现 `GET /api/exports`、`GET /api/exports/{export_id}`、`GET /api/exports/{export_id}/download`。

## 8. 人工复核接口

- [ ] 实现 `GET /api/review/tasks`。
- [ ] 实现 `POST /api/review/tasks/{event_id}/decision`。
- [ ] 支持修正事件类型、标题、摘要和标签。
- [ ] 复核结果写入审计日志。

## 9. 可先交给吕霄阳 mock 的接口

这些页面主要用于展示，倪羽辰第一阶段不用投入太多：

- [ ] `/api/dashboard/*`
- [ ] `/api/alerts/*`
- [ ] `/api/accidents/*`
- [ ] `/api/reports/daily`
- [ ] `/api/settings/*`
- [ ] `/api/users`
- [ ] `/api/roles`
- [ ] `/api/permissions`

第一阶段只需要保持 mock 数据字段符合 `docs/api-contract.md`，等主链路稳定后再逐步真实化。

## 10. 测试与验收

- [ ] 写后端单元测试：检索排序、时间戳映射、状态流、导出路径。
- [ ] 写接口测试：上传、状态、检索、事件详情、导出。
- [ ] 准备三类演示查询：剐蹭、违停、道路障碍/异常停车。
- [ ] 用样例视频跑通完整链路。
- [ ] 输出后端实现说明，供答辩和最终文档引用。

