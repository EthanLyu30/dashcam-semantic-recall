# Final Stage Delivery Checklist

本清单用于最终答辩和交付验收，不再按阶段二口径组织。

## 交付范围

- [x] Qt6 桌面端：11 个原型页面**全部与真实后端联调**（切页实时刷新）、语义检索工作台、视频库上传处理与筛选、复核工作台（真实关键帧 + 结论写库）、VLC 精准回放、证据导出入口、真实审计日志展示。最终演示截图：`docs/final-demo-shots/`。
- [x] FastAPI 主链路：登录、视频上传、预处理、帧分析、事件聚合、混合检索、事件详情、证据导出、审计日志。
- [x] 数据库：SQLite / PostgreSQL 双引擎，9 张核心业务表，PG `REAL[]` 向量列 + `cosine_similarity()` 存储函数。
- [x] AI 模型：确定性 mock 适配器 + OpenAI-compatible DeepSeek / Qwen-VL 适配器；真实 key 通过本机环境变量注入，不提交。
- [x] 人工复核：复核任务列表、复核决策、修正事件类型/标题/标签、审计留痕。
- [x] 管理面 API：dashboard、alerts、accidents、reports、settings、users、roles、permissions 均由真实数据库派生。
- [x] 导出归档：事件证据包 `clip.mp4` / `snapshot.jpg` / `report.json` / `report.md` / `package.zip`；24h 去重复用；受控批量导出 `POST /api/exports/batch`（≤50，失败隔离）；日报 Markdown/JSON 导出。
- [x] 文档：README、API contract、requirements trace、handoff、backend notes、final-stage checklist。

## 验收命令

```powershell
python -m compileall apps tests
python -m pytest -q
```

当前本机验证口径：完整环境（PySide6 + ffmpeg + VLC）`86 passed`（共 86 个用例）；最小环境为 `80 passed, 6 skipped`，跳过项与可选桌面/媒体环境及 ffmpeg 相关，不影响后端主链路和 final-stage API 验收。

后端启动后可运行 REST smoke：

```powershell
python tools/final_demo_smoke.py --base-url http://127.0.0.1:8000
```

该脚本覆盖登录、dashboard、alerts、accidents、reports、settings、users、roles、permissions 和审计日志；它不会读取或输出模型 API key。

## Final Demo 路径

### 离线稳定演示

```powershell
python apps/desktop_client/main.py
```

未设置 `DVR_SEMANTIC_API_BASE` 时，客户端使用内置 mock 数据，可稳定展示 11 个页面、检索、时间轴、详情和导出入口。

### 真后端 + 真视频演示

```powershell
$env:DVR_SEMANTIC_DB_URL="sqlite:///./var/dvr_semantic.db"
$env:MODEL_PROVIDER="mock"
uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000
```

另开终端：

```powershell
$env:DVR_SEMANTIC_API_BASE="http://127.0.0.1:8000"
python apps/desktop_client/main.py
```

登录 `admin / admin123`，进入「视频流」上传 30-90 秒 mp4，处理完成后到「检索」搜索并导出证据包。

### 真模型演示

不要把 API key 写入任何仓库文件。只在本机终端设置：

```powershell
$env:MODEL_PROVIDER="deepseek"
$env:MODEL_BASE_URL="https://api.deepseek.com/v1"
$env:MODEL_API_KEY="<your-local-key>"
```

然后启动后端并按真后端路径演示。若网络或模型调用失败，后端会回退到 mock 标签，保证现场演示不崩。

## 分工口径

最终汇报按模块责任归属表达：

- 吕霄阳：约 60%，负责桌面端、主链路集成、服务框架、演示体验、最终交付文档。
- 倪羽辰：约 40%，负责 PostgreSQL/向量检索增强、复核 API、后端技术说明、真实模型与真实视频联调支撑。

## 仍可增强但不阻塞交付

- 批量上传和异步队列：当前为同步处理，短视频演示稳定；生产环境可加 Celery/Redis 或 FastAPI background task。
- HLS 流媒体：当前用 `FileResponse` + VLC 播放，课程演示足够；生产环境可加 HLS 切片。
- ~~管理面写操作~~：已完成——批量导入视频、告警分级规则编辑（`PUT /api/alerts/rules`，持久化 + 审计 + 实时影响分级）、新增用户（`POST /api/users`，bcrypt 入库可立即登录）、事故页一键建证据包、证据页批量归档（`/api/exports/batch`）、权限矩阵 CSV 导出、模型连通性自检均接真实后端。剩余产品化空间：用户的 PATCH/DELETE、角色自定义编辑。
