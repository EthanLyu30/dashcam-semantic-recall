# 吕霄阳负责部分完成清单

本清单按重新调整后的分工记录吕霄阳负责的客户端、原型搬运、展示层和联调准备工作。

## 已完成

- [x] 确定项目英文名和 GitHub 目录名：`dashcam-semantic-recall`。
- [x] 搭建项目结构：`apps/desktop_client`、`apps/backend`、`docs`、`skills`、`tests`。
- [x] 将完整 DVR-Semantic 原型资产接入仓库作为 UI 设计参考：`docs/prototype-source/`。
- [x] 保留原型中的 11 个核心页面、预览图、图片、Tailwind、Iconify、ECharts 等资源，供实现时对照。
- [x] 编写原型搬运说明：`docs/prototype-migration.md`。
- [x] 编写设计系统：`DESIGN.md`，明确后续开发必须沿用原型视觉和导航。
- [x] 编写开发约定：`开发技巧.md`。
- [x] 编写无依赖原型参考运行入口：`python apps/desktop_client/run_prototype.py`。
- [x] 编写 Qt WebEngine 原型参考壳入口：`python apps/desktop_client/prototype_shell.py`。
- [x] 编写 Qt 客户端多页面工作台，复现原型导航和 11 个页面的信息结构。
- [x] 编写 Qt 语义检索页，包含搜索、结果卡片、事件详情、时间轴和播放器占位。
- [x] 编写客户端 DTO、mock API 客户端和演示数据，便于后端未完成时先演示。
- [x] 编写完整前后端 API 契约：`docs/api-contract.md`。
- [x] 编写团队交接文档和需求追踪文档。
- [x] 编写客户端/搜索基础测试并验证通过。

## 新增完成（后端主链路与 final-stage 收口）

- [x] 完整后端服务实现：auth、audit、media_pipeline、model_adapter、hybrid_search、exporter、event_aggregator。
- [x] SQLite 核心数据库层（videos/events/search/export/audit 表）。
- [x] 84 个自动化测试已验证（当前环境 `78 passed, 6 skipped`）。
- [x] Qt6 全部 11 个页面精化：QPainter 自绘图表、VLC 视频播放、登录对话框。
- [x] 主题样式对齐原型（nav active、border-l-4 结果卡、KPI 图标块、panel 圆角）。
- [x] 页面滚动修复：`page_shell` 包装 `QScrollArea`，内容不再被截断。
- [x] 登录模块规范化：从导航栏移除，⏻ 按钮改为退出确认对话框。
- [x] 无响应按钮修复：所有展示型按钮接入 `_wip_button()` 统一提示。
- [x] Phase 2 HTML 报告（15 张截图、幻灯片框架）。
- [x] README 中文版 + mock vs 真实对照表。

## 最终阶段新增（FR-05 导出收口）

- [x] 受控批量导出：`services/exporter.export_batch()` + `POST /api/exports/batch`，单次 ≤50 个事件、失败隔离、自动去重请求列表。
- [x] 批量导出客户端方法：`RestApiClient.export_batch()`。
- [x] 批量导出测试：`test_exporter.test_export_batch_exports_multiple_events`、`test_export_routes.test_batch_export_route_isolates_failures` / `test_batch_export_empty_request_returns_400`。
- [x] 同步更新 README / api-contract / requirements-trace / final-stage-delivery 文档。

## 最终阶段新增（桌面端 UI 修复）

- [x] 应用 logo：新增 `widgets/branding.py` 程序绘制放大镜 logo，设为窗口/任务栏图标（`app.setWindowIcon`）并替换顶栏文字方块，修复"缺少 logo"。
- [x] 页面滚动/截断修复：窗口启动尺寸改为按可用屏幕自适应（`availableGeometry` 取 min 并居中 + `setMinimumSize`），避免窗口高于屏幕导致底部内容被推出屏幕外、看似无法滚动；各页 `page_shell` 的 `QScrollArea` 在视口小于内容时正常出现滚动条（offscreen 实测 scrollMax>0）。

## 最终阶段新增（P0 安全加固，对抗性审计后收口）

- [x] `/api/videos/{id}/stream` 增加鉴权：接受 Bearer 头或短时效签名 ticket（`/stream-ticket`），供 VLC 直连仍受控（修复 SEC-03）。
- [x] `/media` 静态挂载收窄为仅 `frames` / `thumbnails`，原视频 / 分段 / 证据 zip / 日报不再无鉴权静态暴露（修复 SEC-02）。
- [x] 上传增加分块读取 + 大小上限（默认 10GB，`DVR_SEMANTIC_MAX_UPLOAD_BYTES` 可配，超限 413），消除内存型 DoS（修复 SEC-04）。
- [x] JWT 默认密钥策略：生产环境（`DVR_SEMANTIC_ENV=production`）强制非默认密钥否则拒绝启动，开发环境告警（修复 SEC-01）。
- [x] 桌面端 `RestApiClient.stream_url()` 改为先取签名 ticket。
- [x] 安全回归测试：`tests/test_security_hardening.py`（9 个用例）。
- [x] FR-01 进度轮询：`GET /api/videos/{id}/status` 返回 process_status + 分段/帧/事件计数。
- [x] CQ-07：`/process` 失败分支补审计日志，与 preprocess/analyze 对齐。

## 吕霄阳后续只需联调/完善的事项

- [ ] 使用真实行车视频 + 真实模型 API Key 确认检索结果质量。
- [ ] 在 Qt 复核页的任务列表接入真实数据（`GET /api/review/tasks` 已完成）。
- [ ] 设置 `DVR_SEMANTIC_API_BASE` 切换到真实后端，端到端验证搜索 → 播放 → 导出流程。
- [ ] 视频库页"检索 / 更多"操作列改成真实跳转按钮（目前是纯文字）。
- [ ] 答辩演示脚本准备。

## 验收方式

打开原始原型设计参考：

```bash
python apps/desktop_client/run_prototype.py
```

打开 Qt WebEngine 参考壳：

```bash
python apps/desktop_client/prototype_shell.py
```

运行 Qt6 原生复现工作台：

```bash
python apps/desktop_client/main.py
```

运行已有测试：

```bash
python -m pytest
```
