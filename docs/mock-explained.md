# Mock 是什么

`mock` 可以理解成“假接口 / 假后端 / 假数据”。

在本项目里，倪羽辰的真实后端还没有完全实现时，吕霄阳的客户端不能一直等着。于是客户端先用 mock 数据模拟真实接口返回，例如：

- 模拟视频列表。
- 模拟语义检索结果。
- 模拟事件详情。
- 模拟证据导出排队状态。

这样前端可以先完成页面、点击、跳转、展示和演示流程。等真实后端完成后，只需要把数据来源从 `MockApiClient` 切换为 `RestApiClient`，页面结构和交互逻辑不用推倒重来。

## 本项目里的 mock 在哪里

- 客户端 mock 数据：`apps/desktop_client/dvr_semantic_client/demo_data.py`
- 客户端 mock 接口：`apps/desktop_client/dvr_semantic_client/api.py`
- 后端 mock 数据：`apps/backend/dvr_semantic_backend/demo_store.py`
- 后端 mock API：`apps/backend/dvr_semantic_backend/api.py`

## 为什么需要 mock

- 前后端可以并行开发。
- 吕霄阳可以先完成原型搬运和交互演示。
- 倪羽辰可以专注视频处理、模型分析和数据库。
- 答辩前即使模型接口或数据库临时不可用，也能保留稳定演示。

## mock 和真实接口的关系

mock 的字段必须和 `docs/api-contract.md` 保持一致。真实后端完成后，客户端不改页面，只改数据来源。

