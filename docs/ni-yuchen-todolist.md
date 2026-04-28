# 倪羽辰后端与 AI 部分 TODO List

本清单只列倪羽辰负责的后端、AI、数据库、视频处理和接口测试工作。吕霄阳侧已经先完成客户端脚手架和 mock 联调入口。

## 0. 接口契约对齐

- [ ] 阅读 `docs/api-contract.md`，确认字段名、状态枚举和错误格式。
- [ ] 不随意改 `video_id`、`event_id`、`start_sec`、`end_sec`、`confidence` 等客户端必需字段。
- [ ] 若必须改接口，先改 `docs/api-contract.md`，再同步客户端模型。

## 1. FastAPI 基础服务

- [ ] 搭建生产版 `FastAPI` 应用结构。
- [ ] 接入统一错误响应。
- [ ] 接入 CORS、日志中间件、请求耗时记录。
- [ ] 实现 token 登录、用户身份获取、退出登录。
- [ ] 为所有接口补 Pydantic request/response schema。

## 2. 数据库与表结构

- [ ] 建立 PostgreSQL 数据库。
- [ ] 按文档落表：`users`、`videos`、`video_segments`、`frame_analysis`、`semantic_events`、`search_queries`、`search_results`、`event_exports`。
- [ ] 补充 `processing_tasks`、`audit_logs`、`alerts`、`model_settings`、`roles`、`permissions`。
- [ ] 配置 pgvector 扩展和向量索引。
- [ ] 写初始化脚本和样例数据脚本。

## 3. 视频上传与预处理

- [ ] 实现 `POST /api/videos/upload`。
- [ ] 保存原始视频到 `media/originals/`。
- [ ] 调用 ffprobe 读取时长、分辨率、编码、文件大小。
- [ ] 调用 ffmpeg 统一转码格式。
- [ ] 按固定粒度切片，生成 `video_segments`。
- [ ] 抽取关键帧与缩略图，生成可访问 URL。
- [ ] 实现 `GET /api/videos/{video_id}/status` 供客户端轮询。
- [ ] 失败任务允许重试，处理中任务禁止重复触发。

## 4. 多模态模型分析

- [ ] 实现模型配置读取和密钥管理。
- [ ] 设计关键帧分析 prompt，要求模型返回 JSON。
- [ ] 返回字段至少包含 `description`、`tags`、`event_type`、`confidence`、`reason`。
- [ ] 将分析结果写入 `frame_analysis`。
- [ ] 聚合连续帧结果，生成 `semantic_events`。
- [ ] 对低置信事件设置 `review_status=reviewing`。
- [ ] 实现模型不可用时的重试和错误日志。

## 5. 语义检索与结果排序

- [ ] 实现 embedding 生成。
- [ ] 将事件摘要、标签、帧描述写入 pgvector。
- [ ] 实现 `POST /api/search`。
- [ ] 支持 `hybrid` 检索：向量召回 + 关键词回退。
- [ ] 结果按相似度、置信度、事件完整性重排。
- [ ] 写入 `search_queries` 和 `search_results`。
- [ ] 返回客户端需要的 `start_sec`、`end_sec`、`summary`、`thumbnail_url`。

## 6. 精准回放资源接口

- [ ] 实现 `GET /api/videos/{video_id}/stream`。
- [ ] 实现 `GET /api/videos/{video_id}/timeline`。
- [ ] 确保返回时间戳基于原始视频时间轴。
- [ ] 联调客户端点击事件后跳转误差不超过 2 秒。

## 7. 证据导出与日志归档

- [ ] 实现 `POST /api/events/{event_id}/export`。
- [ ] 支持截图 `snapshot`、短视频 `clip`、报告 `report`、证据包 `package`。
- [ ] 使用 ffmpeg 按事件时间段加前后缓冲裁剪。
- [ ] 生成证据摘要 JSON 或 PDF。
- [ ] 写入 `event_exports`。
- [ ] 实现 `GET /api/exports`、`GET /api/exports/{export_id}`、`GET /api/exports/{export_id}/download`。
- [ ] 实现 `GET /api/logs/audit` 和 `GET /api/logs/system`。

## 8. 人工复核

- [ ] 实现 `GET /api/review/tasks`。
- [ ] 实现 `POST /api/review/tasks/{event_id}/decision`。
- [ ] 支持修正事件类型、标题、摘要、标签。
- [ ] 复核后写审计日志。

## 9. 原型剩余页面接口

- [ ] 系统状态概览：`/api/dashboard/*`。
- [ ] 告警管理中心：`/api/alerts/*`。
- [ ] 事故摘要预览：`/api/accidents/*`。
- [ ] 全天业务报告：`/api/reports/daily`。
- [ ] 模型与安全配置：`/api/settings/*`。
- [ ] 角色与权限管理：`/api/users`、`/api/roles`、`/api/permissions`。

## 10. 测试与验收

- [ ] 写后端单元测试：检索排序、时间戳映射、导出路径、状态流。
- [ ] 写接口测试：上传、状态、检索、事件详情、导出。
- [ ] 准备三类演示查询：剐蹭、违停、道路障碍/异常停车。
- [ ] 用真实或样例视频跑通完整链路。
- [ ] 输出一份后端实现说明，供答辩和最终文档引用。
