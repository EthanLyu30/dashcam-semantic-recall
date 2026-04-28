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

## 吕霄阳后续只需联调/完善的事项

- [ ] 等倪羽辰真实后端接口完成后，将 mock 数据源切换为 `DVR_SEMANTIC_API_BASE`。
- [ ] 把原型中的上传按钮、检索按钮、导出按钮逐步绑定到真实接口。
- [ ] 如果课程要求必须是 Qt 原生窗口展示，安装 `PySide6` 后使用 `apps/desktop_client/main.py`。
- [ ] 答辩时优先展示 `语义检索中心.html`、`视频库管理.html`、`系统状态概览.html`、`证据与日志归档.html` 四个页面。

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
