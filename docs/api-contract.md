# 后端 API 接口完整契约

本文档是倪羽辰后端实现与吕霄阳 Qt6 客户端联调的主接口文档。接口按原型页面组织，覆盖 `系统登录`、`系统状态概览`、`视频库管理`、`语义检索中心`、`人工复核中心`、`告警管理中心`、`事故摘要预览`、`证据与日志归档`、`全天业务报告`、`模型与安全配置`、`角色与权限管理`。

Base URL 由客户端环境变量 `DVR_SEMANTIC_API_BASE` 配置。示例：`http://127.0.0.1:8000`。

## 1. 通用约定

### 1.1 认证

除登录接口外，请求头统一携带：

```http
Authorization: Bearer <accessToken>
Content-Type: application/json
```

文件上传使用：

```http
Content-Type: multipart/form-data
```

### 1.2 通用响应

成功响应直接返回业务对象。错误响应统一为：

```json
{
  "error": {
    "code": "VIDEO_NOT_SEARCHABLE",
    "message": "视频尚未完成语义分析，不能检索",
    "detail": {}
  }
}
```

### 1.3 核心枚举

```text
VideoStatus:
uploaded | preprocessing | preprocessing_failed | analyzing | analyze_failed | indexed | searchable | archived

TaskStatus:
queued | running | success | failed | canceled

EventReviewStatus:
pending | reviewing | confirmed | rejected

AlertStatus:
open | acknowledged | resolved | ignored

ExportStatus:
queued | running | success | failed

ExportType:
snapshot | clip | report | package

SearchMode:
hybrid | vector | keyword
```

## 2. 数据模型

### 2.1 User

```json
{
  "id": "usr-001",
  "username": "admin",
  "real_name": "管理员",
  "role": "admin",
  "permissions": ["video:read", "video:upload", "event:review"],
  "created_at": "2026-04-28T08:00:00+08:00"
}
```

### 2.2 Video

```json
{
  "id": "vid-20260327-1422",
  "title": "VID_20260327_1422 南山区巡查",
  "file_name": "VID_20260327_1422.mp4",
  "duration_sec": 1830,
  "file_size_mb": 812.4,
  "resolution": "1920x1080",
  "status": "searchable",
  "thumbnail_url": "/api/media/thumbnails/vid-20260327-1422.jpg",
  "source_path": "media/originals/VID_20260327_1422.mp4",
  "created_at": "2026-03-27T14:22:00+08:00",
  "updated_at": "2026-03-27T14:35:00+08:00"
}
```

### 2.3 ProcessingTask

```json
{
  "id": "task-001",
  "video_id": "vid-20260327-1422",
  "type": "preprocess",
  "status": "running",
  "progress": 62,
  "current_step": "extracting_keyframes",
  "message": "正在抽取关键帧",
  "error_message": "",
  "created_at": "2026-03-27T14:25:00+08:00",
  "updated_at": "2026-03-27T14:26:30+08:00"
}
```

### 2.4 VideoSegment

```json
{
  "id": "seg-001",
  "video_id": "vid-20260327-1422",
  "segment_index": 1,
  "start_sec": 300,
  "end_sec": 360,
  "segment_url": "/api/media/segments/vid-20260327-1422/seg-001.mp4",
  "preview_image_url": "/api/media/frames/vid-20260327-1422/seg-001.jpg"
}
```

### 2.5 SemanticEvent

```json
{
  "id": "evt-scratch-001",
  "video_id": "vid-20260327-1422",
  "event_type": "scratch",
  "title": "白色SUV在转弯处与直行轿车发生侧切剐蹭",
  "summary": "白色SUV由于未注意侧方来车，在路口右转时与直行黑色轿车发生刮擦。",
  "start_sec": 342,
  "end_sec": 361,
  "confidence": 0.942,
  "tags": ["白色SUV", "剐蹭事故", "十字路口"],
  "thumbnail_url": "/api/media/events/evt-scratch-001.jpg",
  "review_status": "pending",
  "evidence_count": 0,
  "created_at": "2026-03-27T14:35:00+08:00"
}
```

## 3. 系统登录

### POST `/api/auth/login`

登录并返回 token。

Request:

```json
{
  "username": "admin",
  "password": "123456"
}
```

当前实现 Response:

```json
{
  "token": "jwt-token",
  "user_id": "usr-001",
  "username": "admin",
  "role": "admin",
  "display_name": "管理员"
}
```

### POST `/api/auth/logout` 🔵 规划中(planned，后端未实现)

退出登录。

Response:

```json
{ "success": true }
```

### GET `/api/auth/me` 🔵 规划中(planned，后端未实现)

获取当前用户。

Response: `User`

## 4. 系统状态概览

### GET `/api/dashboard/overview`

用于原型 `系统状态概览` 顶部指标。

Response:

```json
{
  "processed_video_count": 8429,
  "semantic_query_count": 1204,
  "identified_event_count": 342,
  "pending_review_count": 12,
  "engine_status": "healthy",
  "model_nodes": { "online": 8, "total": 8 }
}
```

### GET `/api/dashboard/trends?days=7`

识别趋势与并发负载。

Response:

```json
{
  "days": ["03-21", "03-22", "03-23"],
  "event_counts": [28, 34, 31],
  "query_counts": [120, 146, 132],
  "worker_load": [0.42, 0.58, 0.51]
}
```

### GET `/api/dashboard/event-distribution`

多模态分类分布。

Response:

```json
{
  "items": [
    { "event_type": "scratch", "label": "剐蹭", "count": 86 },
    { "event_type": "illegal_parking", "label": "违停", "count": 74 }
  ]
}
```

### GET `/api/dashboard/review-feed?limit=20`

待复核实时动态。

Response:

```json
{
  "items": [
    {
      "event_id": "evt-scratch-001",
      "title": "疑似侧向剐蹭",
      "confidence": 0.74,
      "created_at": "2026-03-27T14:35:00+08:00"
    }
  ]
}
```

## 5. 视频库管理

### GET `/api/videos`

视频列表，支持筛选。

Query:

```text
keyword?: string
status?: VideoStatus
page?: int
page_size?: int
```

Response:

```json
{
  "items": [ { "id": "vid-20260327-1422", "title": "VID_20260327_1422 南山区巡查", "duration_sec": 1830, "status": "searchable", "thumbnail_url": "" } ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

### POST `/api/videos/upload`

上传视频并创建处理任务。

Form Data:

```text
file: binary
title: string
device_no?: string
recorded_at?: datetime
```

Response:

```json
{
  "video": { "id": "vid-001", "title": "测试视频", "duration_sec": 0, "status": "uploaded" },
  "task": { "id": "task-001", "video_id": "vid-001", "type": "preprocess", "status": "queued", "progress": 0 }
}
```

### GET `/api/videos/{video_id}`

获取视频详情。

Response: `Video`

### PATCH `/api/videos/{video_id}` 🔵 规划中(planned，后端未实现)

修改标题、备注、保留策略等元信息。

Request:

```json
{
  "title": "南山区巡查视频",
  "remark": "课程演示样例"
}
```

### DELETE `/api/videos/{video_id}` 🔵 规划中(planned，后端未实现)

删除视频及关联任务、事件、导出记录。课程演示可先做软删除。

Response:

```json
{ "success": true }
```

### POST `/api/videos/{video_id}/process`

重新触发预处理或语义分析。

Request:

```json
{
  "steps": ["preprocess", "analyze", "index"],
  "force": false
}
```

Response: `ProcessingTask`

### GET `/api/videos/{video_id}/status` ✅ 已实现

客户端轮询处理进度：返回 `process_status` + `segments` / `frames_total` / `frames_analyzed` / `events` 计数，对应 `VideoStatusResponse`。

Response:

```json
{
  "video_id": "vid-001",
  "status": "analyzing",
  "tasks": [
    { "id": "task-001", "type": "preprocess", "status": "success", "progress": 100 },
    { "id": "task-002", "type": "analyze", "status": "running", "progress": 47 }
  ]
}
```

### GET `/api/videos/{video_id}/segments` 🔵 规划中(planned，后端未实现)

获取视频切片列表。

Response:

```json
{ "items": [ { "id": "seg-001", "start_sec": 0, "end_sec": 60, "segment_url": "/api/media/segments/seg-001.mp4" } ] }
```

### GET `/api/videos/{video_id}/timeline` 🔵 规划中(planned，后端未实现)

获取时间轴事件标记。

Response:

```json
{
  "video_id": "vid-20260327-1422",
  "duration_sec": 1830,
  "events": [
    { "id": "evt-scratch-001", "start_sec": 342, "end_sec": 361, "event_type": "scratch", "confidence": 0.942 }
  ]
}
```

### GET `/api/videos/{video_id}/stream` ✅ 已实现（需鉴权）

直接以 `FileResponse` 返回视频字节流，供 VLC/Qt 播放器加载。**需鉴权**：接受
`Authorization: Bearer <token>` 头，或查询参数 `?token=<签名 ticket>`（VLC 直连场景）。
无凭据返回 401。

### GET `/api/videos/{video_id}/stream-ticket` ✅ 已实现

为无法携带 Authorization 头的播放器（VLC）签发短时效（默认 300s）签名 URL。

Response:

```json
{
  "url": "/api/videos/vid-20260327-1422/stream?token=<signed>",
  "expires_in": 300
}
```

### POST `/api/videos/{video_id}/retry` ✅ 已实现（reviewer/admin）

幂等地重新执行 preprocess + analyze（NFR-02 任务恢复）。失败任务可由 reviewer/admin 重投，
返回 `RetryResponse`（`process_status` + `frames_analyzed` + `events_created` + `retried`）。
普通 user 调用返回 403，未知视频返回 404。

## 6. 语义检索中心

### POST `/api/search`

自然语言检索。

Request:

```json
{
  "video_id": "vid-20260327-1422",
  "query": "寻找白色SUV与黑色轿车在十字路口发生轻微碰撞的瞬间",
  "mode": "hybrid",
  "top_k": 10,
  "filters": {
    "event_types": ["scratch", "illegal_parking"],
    "min_confidence": 0.5
  }
}
```

Response:

```json
{
  "query_id": "qry-20260327-009",
  "query": "寻找白色SUV与黑色轿车在十字路口发生轻微碰撞的瞬间",
  "video_id": "vid-20260327-1422",
  "elapsed_ms": 86,
  "results": [
    {
      "id": "evt-scratch-001",
      "video_id": "vid-20260327-1422",
      "event_type": "scratch",
      "title": "白色SUV在转弯处与直行轿车发生侧切剐蹭",
      "summary": "白色SUV由于未注意侧方来车，在路口右转时与直行黑色轿车发生刮擦。",
      "start_sec": 342,
      "end_sec": 361,
      "confidence": 0.942,
      "similarity_score": 0.913,
      "tags": ["白色SUV", "剐蹭事故", "十字路口"],
      "thumbnail_url": "/api/media/events/evt-scratch-001.jpg",
      "review_status": "pending"
    }
  ]
}
```

### GET `/api/search/history` 🔵 规划中(planned，后端未实现)

查询历史。

Query:

```text
video_id?: string
user_id?: string
page?: int
page_size?: int
```

Response:

```json
{
  "items": [
    {
      "id": "qry-20260327-009",
      "query": "白色SUV剐蹭",
      "video_id": "vid-20260327-1422",
      "result_count": 3,
      "elapsed_ms": 86,
      "created_at": "2026-03-27T14:40:00+08:00"
    }
  ],
  "total": 1
}
```

### GET `/api/events/{event_id}`

获取事件详情。

Response: `SemanticEvent`

### GET `/api/events`

事件列表，支持原型各页面复用。

Query:

```text
video_id?: string
event_type?: string
review_status?: EventReviewStatus
min_confidence?: float
page?: int
page_size?: int
```

Response:

```json
{
  "items": [ { "id": "evt-scratch-001", "title": "疑似侧向剐蹭", "start_sec": 342, "end_sec": 361, "confidence": 0.942 } ],
  "total": 1
}
```

## 7. 人工复核中心

### GET `/api/review/tasks`

复核任务队列。

Query:

```text
status?: EventReviewStatus
event_type?: string
page?: int
page_size?: int
```

Response:

```json
{
  "items": [
    {
      "event_id": "evt-obstacle-003",
      "video_id": "vid-20260327-1422",
      "title": "施工围挡占道",
      "confidence": 0.79,
      "review_status": "reviewing",
      "thumbnail_url": "",
      "created_at": "2026-03-27T14:50:00+08:00"
    }
  ],
  "total": 1
}
```

### POST `/api/review/tasks/{event_id}/decision`

提交复核结论。

Request:

```json
{
  "decision": "confirmed",
  "corrected_event_type": "road_obstacle",
  "corrected_title": "施工围挡占用右侧车道",
  "corrected_tags": ["施工", "围挡", "道路障碍"],
  "note": "画面清晰，确认属于道路障碍事件"
}
```

Response:

```json
{
  "event_id": "evt-obstacle-003",
  "review_status": "confirmed",
  "reviewer_id": "usr-002",
  "reviewed_at": "2026-04-28T09:00:00+08:00"
}
```

### PATCH `/api/events/{event_id}/labels` 🔵 规划中(planned，后端未实现)

修改事件标签。

Request:

```json
{
  "title": "白色SUV轻微剐蹭",
  "summary": "复核后确认车辆右侧发生轻微剐蹭。",
  "tags": ["白色SUV", "剐蹭", "轻微事故"],
  "event_type": "scratch"
}
```

## 8. 告警管理中心

### GET `/api/alerts/summary`

告警统计。

Response:

```json
{
  "open_count": 12,
  "today_count": 45,
  "resolved_count": 128,
  "avg_response_minutes": 1.5
}
```

### GET `/api/alerts`

告警列表。

Query:

```text
status?: AlertStatus
event_type?: string
severity?: low|medium|high
page?: int
page_size?: int
```

Response:

```json
{
  "items": [
    {
      "id": "alt-001",
      "event_id": "evt-scratch-001",
      "title": "高置信剐蹭事件",
      "severity": "high",
      "status": "open",
      "created_at": "2026-03-27T14:35:00+08:00"
    }
  ],
  "total": 1
}
```

### POST `/api/alerts/{alert_id}/ack`

确认告警。

Response:

```json
{ "alert_id": "alt-001", "status": "acknowledged" }
```

### POST `/api/alerts/{alert_id}/resolve`

关闭告警。

Request:

```json
{ "resolution_note": "已导出证据并归档" }
```

## 9. 事故摘要预览

### GET `/api/accidents`

事故/风险摘要列表。

Response:

```json
{
  "items": [
    {
      "id": "acc-001",
      "event_id": "evt-scratch-001",
      "title": "南山区深南大道科苑立交段侧向碰撞",
      "risk_level": "high",
      "summary": "疑似侧向剐蹭，建议导出片段与关键帧。",
      "created_at": "2026-03-27T14:35:00+08:00"
    }
  ]
}
```

### GET `/api/accidents/{accident_id}`

事故详情。

### POST `/api/accidents/{accident_id}/summary`

重新生成事故摘要。

Request:

```json
{
  "style": "brief",
  "include_evidence": true
}
```

Response:

```json
{
  "accident_id": "acc-001",
  "summary": "本事件发生在 14:22:15 至 14:22:45，疑似白色SUV与黑色轿车侧向剐蹭。",
  "updated_at": "2026-04-28T09:00:00+08:00"
}
```

## 10. 证据与日志归档

### POST `/api/events/{event_id}/export`

当前实现为同步创建证据导出包。**24h 去重（FR-05）**：同一事件在 24 小时内已成功导出且包文件仍在磁盘上时，直接复用既有包（`reused=true`），不再重复跑 ffmpeg；传 `force=true` 可强制重新生成。

Request:

```json
{
  "export_type": "package",
  "include_video": true,
  "include_snapshot": true,
  "include_report": true,
  "force": false
}
```

Response:

```json
{
  "event_id": "evt-scratch-001",
  "export_id": "exp-evt-scratch-001",
  "status": "success",
  "export_path": "D:/.../var/media/exports/evt-scratch-001/package.zip",
  "reused": false
}
```

### POST `/api/exports/batch`

受控批量导出（FR-05 "single **or controlled-batch** export"）。单次最多 50 个事件；逐个独立导出（沿用 24h 去重），单个失败不影响其余，失败项在 `items` 中以 `status="failed"` + `fail_reason` 标注。空列表或超量返回 400。

Request:

```json
{
  "event_ids": ["evt-scratch-001", "evt-obstacle-003"],
  "include_video": true,
  "include_snapshot": true,
  "include_report": true,
  "force": false
}
```

Response:

```json
{
  "total": 2,
  "succeeded": 2,
  "failed": 0,
  "items": [
    { "event_id": "evt-scratch-001", "export_id": "exp-aaa", "status": "success", "export_path": ".../package.zip", "reused": false, "fail_reason": "" },
    { "event_id": "evt-obstacle-003", "export_id": "exp-bbb", "status": "success", "export_path": ".../package.zip", "reused": false, "fail_reason": "" }
  ]
}
```

### GET `/api/exports`

导出记录列表。

Response:

```json
{
  "items": [
    {
      "id": "exp-evt-scratch-001",
      "event_id": "evt-scratch-001",
      "export_type": "package",
      "status": "success",
      "export_path": "media/exports/evt-scratch-001.zip",
      "created_at": "2026-04-28T09:00:00+08:00"
    }
  ]
}
```

### GET `/api/exports/{export_id}` 🔵 规划中(planned，后端未实现)

导出详情和状态。（当前用 `GET /api/exports?event_id=...` 列表替代）

### GET `/api/exports/{export_id}/download` 🔵 规划中(planned，后端未实现)

下载导出文件。返回二进制文件流。

### GET `/api/audit/logs`

操作日志。

Query:

```text
user_id?: string
action?: string
start_at?: datetime
end_at?: datetime
page?: int
page_size?: int
```

Response:

```json
{
  "items": [
    {
      "id": "log-001",
      "user_id": "usr-001",
      "action": "event.export",
      "target_id": "evt-scratch-001",
      "message": "导出证据包",
      "created_at": "2026-04-28T09:00:00+08:00"
    }
  ]
}
```

### GET `/api/logs/system` 🔵 规划中(planned，后端未实现)

系统日志，用于排查模型调用、转码、检索异常。

## 11. 全天业务报告

### GET `/api/reports/daily?date=2026-03-27`

业务日报。

Response:

```json
{
  "date": "2026-03-27",
  "summary": "全天共处理 124 个视频，识别 18 个关键事件。",
  "metrics": {
    "video_count": 124,
    "event_count": 18,
    "query_count": 86,
    "export_count": 7
  },
  "event_trend": [
    { "hour": "08:00", "count": 2 },
    { "hour": "09:00", "count": 4 }
  ],
  "event_type_distribution": [
    { "event_type": "scratch", "count": 5 }
  ],
  "area_statistics": [
    { "area": "南山区", "count": 8 }
  ]
}
```

### POST `/api/reports/daily/export`

导出日报。

Request:

```json
{
  "date": "2026-03-27",
  "format": "pdf"
}
```

Response:

```json
{
  "export_id": "exp-report-20260327",
  "status": "queued"
}
```

## 12. 模型与安全配置

### GET `/api/settings/model`

模型配置。

Response:

```json
{
  "provider": "qwen-vl",
  "vision_model": "qwen-vl-max",
  "embedding_model": "text-embedding-v3",
  "frame_interval_sec": 5,
  "candidate_window_sec": 8,
  "confidence_threshold": 0.72,
  "api_key_masked": "sk-****"
}
```

### PATCH `/api/settings/model` 🔵 规划中(planned，后端未实现)

更新模型配置。

Request:

```json
{
  "provider": "qwen-vl",
  "vision_model": "qwen-vl-max",
  "embedding_model": "text-embedding-v3",
  "frame_interval_sec": 5,
  "confidence_threshold": 0.72
}
```

### POST `/api/settings/model/test`

测试模型连通性。

Response:

```json
{
  "success": true,
  "latency_ms": 420,
  "message": "模型接口连通"
}
```

### GET `/api/settings/security`

安全配置。

### PATCH `/api/settings/security` 🔵 规划中(planned，后端未实现)

更新安全配置。

## 13. 角色与权限管理

### GET `/api/users`

用户列表。

### POST `/api/users` 🔵 规划中(planned，后端未实现)

创建用户。

Request:

```json
{
  "username": "reviewer01",
  "password": "123456",
  "real_name": "复核员",
  "role": "reviewer"
}
```

### PATCH `/api/users/{user_id}` 🔵 规划中(planned，后端未实现)

更新用户资料、角色、启用状态。

### DELETE `/api/users/{user_id}` 🔵 规划中(planned，后端未实现)

禁用或删除用户。

### GET `/api/roles`

角色列表。

Response:

```json
{
  "items": [
    { "id": "admin", "name": "管理员", "permissions": ["*"] },
    { "id": "reviewer", "name": "审核人员", "permissions": ["event:read", "event:review"] },
    { "id": "user", "name": "普通用户", "permissions": ["video:upload", "search:create"] }
  ]
}
```

### POST `/api/roles` 🔵 规划中(planned，后端未实现)

创建角色。

### PATCH `/api/roles/{role_id}` 🔵 规划中(planned，后端未实现)

更新角色权限。

### GET `/api/permissions`

权限字典。

## 14. 媒体资源

### GET `/media/frames/{...}` · `/media/thumbnails/{...}` ✅ 已实现（公开静态）

仅公开**非敏感图片**（关键帧、缩略图）两个子目录的静态挂载。原始视频
（`originals`/`segments`）、证据 zip（`exports`）、日报（`reports`）**不再**经
静态挂载暴露，须走带鉴权的路由（如 `GET /api/videos/{id}/stream` + ticket）。

## 15. 第三方集成接口（FR-06，API-Key 鉴权）✅ 已实现

对外只读事件接口，供保险/车队等第三方系统拉取已复核确认的事件。通过
`X-Api-Key` 头鉴权，密钥来自环境变量 `DVR_SEMANTIC_INTEGRATION_API_KEYS`
（逗号分隔，可配多把）；未配置时整组接口返回 503（默认关闭，opt-in）。

### GET `/api/integration/events?event_type=&limit=50`

返回 `review_status=confirmed` 的事件列表（`IntegrationEventListResponse`，`limit` 上限 200）。

### GET `/api/integration/events/{event_id}`

返回单条已确认事件（`IntegrationEventItem`）；未确认或不存在返回 404。

错误：缺失/错误 key → 401；未配置集成 key → 503。

## 16. Final-stage 实现状态

`main` 当前 final-stage 版本已实现以下接口组：

1. 主链路：`auth`、`videos`、`process/analyze`、`status`、`retry`、`search`、`events`、`export`（单事件 + 24h 去重 + `POST /api/exports/batch` 批量）、`audit`。
2. 复核链路：`GET /api/review/tasks`、`POST /api/review/tasks/{event_id}/decision`。
3. 管理面：`dashboard`、`alerts`、`accidents`、`reports`、`settings`（只读 GET）、`users`/`roles`/`permissions`（只读 GET）。
4. 媒体与回放：`/media/frames`、`/media/thumbnails` 公开静态；`GET /api/videos/{id}/stream`（鉴权 + 签名 ticket）。
5. 第三方集成：`GET /api/integration/events`、`/api/integration/events/{id}`（API-Key）。

**仅契约、后端未实现（标注 🔵 规划中）**：`auth/logout`、`auth/me`、`videos` 的 PATCH/DELETE/segments/timeline、`search/history`、`events/{id}/labels`、`exports/{id}` 及 `/download`、`logs/system`、`settings` 的 PATCH、`users`/`roles` 的写操作。读者请以本节与各端点标记为准，不要把契约示例当作现状。

管理面接口由现有核心表实时派生，不额外引入迁移表；后续生产化可再把 alerts/settings/report jobs 独立成持久化模块。
