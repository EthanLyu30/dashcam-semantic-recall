# Dashcam Semantic Recall

English project name: `dashcam-semantic-recall`

Dashcam Semantic Recall is a course project scaffold for a multimodal AI system that turns long dashcam videos into searchable semantic events, then lets users jump to the exact playback segment and export evidence.

The project is derived from the completed SRS, outline design document, first-stage report, opening report, and DVR-Semantic interaction prototype in the parent workspace.

## Scope

This repository is intentionally split by the two-person team boundary from the opening report.

吕霄阳 owns the desktop client, prototype migration, and presentation layer:

- Reproduce the completed DVR-Semantic prototype inside the Qt6 desktop stack
- Keep `docs/prototype-source` as the UI design reference, not as the final implementation
- Qt6 desktop multi-page scaffold, playback/seek flow, search results, event detail, and timeline
- Mock data, REST contract integration, and final demo flow

倪羽辰 owns the real backend and AI implementation:

- Video upload, transcoding, slicing, frame extraction, and thumbnails
- Multimodal model API integration and structured labels
- Semantic retrieval, event summaries, timestamp return logic
- Core database persistence, evidence export implementation, tests, and technical docs

## What Is Implemented Now (lxy branch, phase 2)

阶段一已完成（main 分支保留）：原型复刻、Qt6 多页面、mock 数据契约。

阶段二在 `lxy` 分支新增：

- **真实后端**：SQLAlchemy + SQLite，9 张业务表对齐概要设计 V4.0；FastAPI 整合所有服务。
- **ffmpeg 媒体流水线**：上传 → 转码 → 切片 → 抽帧 → 缩略图。
- **多模态模型适配层**：mock / DeepSeek-VL / 千问 Qwen-VL 一键切换，OpenAI 兼容协议。
- **语义事件聚合**：相邻同类型帧合并，置信度阈值进复核队列。
- **混合检索**：向量召回（sentence-transformers 可选 + hash-ngram 降级）+ 关键词重排。
- **证据导出**：ffmpeg 真切片 + 截图 + JSON/Markdown 摘要 + zip 打包。
- **鉴权与审计**：bcrypt + PyJWT Bearer Token，三个种子账号，写操作全部留痕。
- **真 VLC 播放**：`python-vlc` 嵌入 QFrame，未装 VLC 时降级到原 QLabel 占位。
- **测试**：39 通过 + 1 跳过；端到端 `test_api_integration.py` 串通 login → upload → process → search → export。

详细进度与剩余事项见 `plans/IMPL_PLAN.md`。

Important design note: the desktop client must reproduce the completed DVR-Semantic prototype in the required Qt6 desktop stack rather than directly ship the HTML prototype. The source prototype is copied under `docs/prototype-source/` as the UI design reference, and the page/API mapping is documented in `docs/prototype-migration.md`.

## Quick Start

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e ".[dev,desktop,backend,media,ai]"
```

Open the original prototype reference pages:

```bash
python apps/desktop_client/run_prototype.py
```

Open the original prototype inside a Qt WebEngine reference shell if PySide6/QtWebEngine is installed:

```bash
python apps/desktop_client/prototype_shell.py
```

Run the native Qt multi-page reproduction:

```bash
python apps/desktop_client/main.py
```

Run the mock backend:

```bash
uvicorn apps.backend.main:app --reload --port 8000
```

Point the desktop client at the backend:

```bash
$env:DVR_SEMANTIC_API_BASE="http://127.0.0.1:8000"
python apps/desktop_client/main.py
```

Run tests:

```bash
python -m pytest
```

## Reference Style

The scaffold borrows the following ideas from the requested references:

- Hermes Agent: explicit project guide, skills, tools/services, plans, and stable contracts.
- Karpathy guidelines: minimal scope, surgical changes, success criteria, and verification loops.
- DESIGN.md pattern: a root design-system document that coding agents can follow consistently.

## Mock Data

`mock` means fake API/data used before the real backend is finished. See `docs/mock-explained.md`.
