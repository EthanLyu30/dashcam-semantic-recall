# 阶段二汇报 PPT — 每页生成提示词

本文件给出 12 页 PPT 每一页对应的生成提示词。你可以把它们喂给任何 LLM（推荐 Claude 4.7 / GPT-4o / 通义千问 max）来重生某一页，也可以整篇喂给"代码生成 + 前端"型助手做整体改版。

## 通用风格约束（每个 prompt 都先贴这一段）

```
你在帮我做"基于多模态大模型的行车记录仪视频语义检索与精准回放系统"的阶段二汇报 PPT，技术栈：Python + FastAPI + PySide6 + ffmpeg + SQLAlchemy + python-vlc + JWT。

视觉风格固定如下（与阶段一保持一致）：
- 1280×720 单页 HTML section，顶部 8px / 底部 6px 四色彩条（蓝 #2563EB → 红 #EF4444 → 黄 #F59E0B → 绿 #22C55E 四等分）
- 背景 #F8FAFC，卡片 #FFFFFF 圆角 22px，1px #E2E8F0 描边
- 正文字体使用系统 sans，标题 800 weight，副标题用浅蓝胶囊 (#EFF6FF + #BFDBFE 边框)
- 调色板：蓝 #2563EB（主） / 红 #EF4444（风险） / 黄 #F59E0B（注意） / 绿 #22C55E（已完成） / 靛 #4F46E5 / 青 #06B6D4
- 段落项目符号用 7px 实心圆点，颜色对应类别（已完成绿、风险红、注意黄、流程蓝）
- 不要用 emoji 表情包，只允许少量功能性 emoji（如 📦 📸 📝 📹），整页最多 4 个
- 底部居中放 12 个小圆点表示当前页码（当前页用对应颜色高亮），右下角用 2 位数字标页码
- 不允许出现"AI 大模型 / 智慧大脑 / 颠覆"等空洞营销词，只描述可验证的事实
- 内容必须诚实，区分"已实现 / 等价替代 / 未实现"
```

---

## Slide 1 — 封面

**用途**：开场，给出项目全称、阶段、贡献度、视觉锚点。

```
帮我生成 PPT 第 1 页 HTML：
- 居中一张白色大圆角卡片，内含：
  - 顶部一个浅蓝胶囊"综合项目实践 · 阶段二进度汇报"
  - 主标题（44px、800 weight）："基于多模态大模型的"换行"行车记录仪视频语义检索与精准回放系统"，后半句用主蓝色
  - 副标题（17px 浅灰）："从原型复刻到端到端服务落地 · 主链路真实跑通"
  - 一根 280px 宽的四色彩条作为视觉分隔
  - 一行作者贡献度："吕霄阳 (本期贡献 70%) / 倪羽辰 (30%)"，姓名用主蓝色
  - 学校与日期："苏州大学 · 综合项目实践 · 2026 年 5 月"
- 不需要图标插画，纯排版即可
```

---

## Slide 2 — 阶段成果总览

**用途**：一页让评审看清楚"完成了什么"。

```
生成 PPT 第 2 页 HTML，主题"阶段二已形成可运行的端到端主链路"。
要求：
- 顶部一个浅蓝胶囊副标题："本阶段已完成上传→预处理→分析→检索→回放→导出 全链路落地。"
- 上半部：4 张并排的指标卡，每张含 label + 大号数字 + 一个圆角彩色徽章
  1) 后端服务模块：7（蓝徽章列出 media / model / search / export / auth / audit / aggregator）
  2) 业务数据表：9（绿徽章"对齐概要设计 V4.0"）
  3) 自动化测试：39 +1 skip（黄徽章"含端到端集成"）
  4) 真实组件：5（红徽章"ffmpeg / VLC / JWT / SQLAlchemy / 模型适配"）
- 下半部：左右两张白卡，左卡《阶段结论》列 4 条带颜色圆点的 li，右卡《当前进展判断》画 4 条蓝→青渐变进度条（需求实现 92% / 数据持久化+鉴权 95% / 真模型+向量库+异步 55% / 辅助页面 45%）
```

---

## Slide 3 — 与阶段一对比

```
生成 PPT 第 3 页 HTML，主题"从原型复刻走到主链路落地"。
左卡《阶段一（已完成）》用灰色标题，5 条 li，最后一条用红圆点点明问题（"语义检索是关键词匹配；视频播放是 QLabel 占位；导出返回假路径"）。
右卡《阶段二（本期新增）》用主蓝色标题，7 条 li 全部用绿圆点：SQLAlchemy 9 张表 / ffmpeg 真预处理 / 模型适配 mock+DeepSeek+千问 / 事件聚合 / 混合检索 / 真证据切片+zip / JWT+审计 / 真 VLC + 上传 + 登录。
副标题用浅蓝胶囊："阶段一交付了需求、原型和技术预研；阶段二把这些图纸翻译成可运行的代码。"
```

---

## Slide 4 — 系统架构落地

```
生成 PPT 第 4 页 HTML，主题"后端服务层架构（7 个服务 + FastAPI 编排）"。
副标题胶囊："每个服务都对应概要设计 V4.0 中的一个业务模块，按 videoId / eventId / queryId / exportId 串联。"

中部：横向 6 张服务卡片用 ▶ 串成流水线（背景白色、左边一条彩色 4px 边）：
1. media_pipeline（蓝边）副标"FFmpeg 转码/切片/抽帧"
2. model_adapter（靛边）副标"Mock / DeepSeek / 千问"
3. event_aggregator（绿边）副标"滑窗合并候选事件"
4. hybrid_search（黄边）副标"向量召回 + 关键词重排"
5. exporter（红边）副标"切片 + 截图 + zip"
6. auth + audit（青边）副标"JWT + 操作留痕"

下半两张白卡：
左卡《调用链路》— 黑底 monospace pre 块，按 1～6 步展示 6 个 API 调用链
右卡《分层职责》— 5 条带颜色圆点的 li：桌面交互层 / 接口契约层 / 业务编排层 / 媒体处理层 / 数据存储层
```

---

## Slide 5 — 媒体流水线

```
生成 PPT 第 5 页 HTML，主题"关键落地 ① — FFmpeg 真媒体流水线"。
副标题胶囊："用户上传一个 mp4，系统自动产生切片、关键帧和缩略图，并写入 video_segments / frame_analysis。"

左卡《处理顺序》5 条蓝圆点 li：
  save_upload — SHA-256 校验 + 文件落 originals/
  probe_metadata — ffprobe 拿 duration/fps/分辨率
  slice_video — 30s 一段，写 video_segments
  extract_frames — 1 帧/3 秒，写 frame_analysis（pending）
  generate_thumbnail — Pillow 缩到 640px
脚注（浅灰 muted）："非 mp4 上传自动 H.264/AAC 转码，保证下游能播。"

右卡《关键代码片段》— 黑底 pre 块展示 run_preprocess 函数签名与状态推进注释。脚注："失败路径走 _mark_failed，写 fail_reason 到 videos.fail_reason 后 raise。"
```

---

## Slide 6 — 模型适配 + 事件聚合

```
生成 PPT 第 6 页 HTML，主题"关键落地 ② — 模型适配器 + 语义事件聚合"。
副标题胶囊："两阶段策略：先逐帧分析、再滑窗合并。模型层走适配器，演示用 mock，真模型只需改环境变量。"

左卡《三套适配器》3 条 li：
  蓝圆点·MockAdapter — 基于文件名 + SHA-256 散列，确定性输出，演示稳定不抖
  靛圆点·OpenAICompatibleAdapter — 同时跑 DeepSeek-VL 和 Qwen-VL（两家都暴露 OpenAI 兼容 messages 协议），base64 图 + 强约束 JSON 提示词
  红圆点·网络/解析失败 → 静默 fallback 到 confidence=0、event_type=normal，不抛错

右卡《事件聚合规则》5 条 li：
  绿·扫描 frame_analysis.status='done' 的帧
  绿·相邻 ≤10 秒且 event_type 相同 → 合并为一个 SemanticEvent
  绿·confidence 取参与帧均值
  黄·均值 < 0.75 → review_status='reviewing'（进复核队列）
  蓝·最终 Video.process_status 推进到 'indexed'
```

---

## Slide 7 — 混合检索

```
生成 PPT 第 7 页 HTML，主题"关键落地 ③ — 向量 + 关键词混合检索"。
副标题胶囊："用 sentence-transformers 把事件文本变向量做余弦召回，再叠加关键词分数重排；首次运行无需下载模型也能跑。"

左卡《计算管线》— 黑底 pre 块展示打分公式 final = 0.6 * cos(q_vec, ev_vec) + 0.4 * keyword_score；下方注释"启用真 embedding 时：paraphrase-multilingual-MiniLM-L12-v2 (384d)；未启用时：字符 1/2-gram → hash → 384 维 → L2 归一"。

右卡《关键词词典》5 条 li，每条左边一个对应颜色圆点：
  红·scratch ← 剐蹭 / 刮蹭 / 碰撞 / 擦碰
  黄·illegal_parking ← 违停 / 停车 / 占道
  蓝·road_obstacle ← 障碍 / 施工 / 围挡 / 路障
  靛·abnormal_stop ← 急停 / 急刹 / 鸣笛
  绿·pedestrian_risk ← 行人 / 横穿 / 鬼探头
脚注："每次查询同时落 search_queries + search_results 表，留 query_id 便于日志排障。"
```

---

## Slide 8 — 证据导出

```
生成 PPT 第 8 页 HTML，主题"关键落地 ④ — FFmpeg 真证据切片 + zip 打包"。
副标题胶囊："点击导出证据包后系统真的会切一段 mp4、抽一张关键截图、生成 JSON+Markdown 摘要并打包，不再是假路径。"

上半部 3 张并排白卡：
  📹 clip.mp4（蓝标题）：按 start-5s ~ end+5s 切片 / 优先 -c copy / 失败回退 libx264+aac 重编码
  📸 snapshot.jpg（绿标题）：事件中点 ffmpeg -ss 抓帧 / Pillow JPEG 保存 / 作为证据封面图
  📝 report.json + report.md（黄标题）：event 全字段 + 源视频元数据 / 中文 Markdown 给人看 / JSON 给下游程序消费

下半部一张大白卡《落地状态》— 黑底 pre 块：
  EventExport.status:  queued → exporting → success
                                          ↘ failed (fail_reason 留底)
  zip 路径：  media/exports/{event_id}/package.zip
  审计：    每次导出写 audit_logs，包含 operator_id / export_type
```

---

## Slide 9 — 桌面端

```
生成 PPT 第 9 页 HTML，主题"桌面端落地 — 真 VLC 播放 + 上传 + 登录"。
副标题胶囊："原型在阶段一已经搬到 Qt6，本期把看得见的占位换成真的能跑。"

左卡《VideoPlayerPanel》5 条 li：
  蓝·vlc.MediaPlayer 嵌入 QFrame
  蓝·Win set_hwnd / X11 set_xwindow / mac set_nsobject 一键多平台
  蓝·seek(sec) 调 player.set_time(ms)
  蓝·QTimer 500ms 同步进度条
  红·python-vlc 未装 → 降级 QLabel 占位 + 虚拟游标，不崩

右卡《视频库管理页 + 登录》5 条 li：
  绿·"上传视频"按钮 → QFileDialog → multipart 上传
  绿·上传成功自动 process，状态变 indexed 后入库
  绿·列表从 GET /api/videos 实时拉
  靛·LoginDialog：username + password → POST /api/auth/login → 存 token
  靛·Mock 模式跳过登录（demo 仍可演示）
```

---

## Slide 10 — 测试矩阵

```
生成 PPT 第 10 页 HTML，主题"测试矩阵 — 39 通过 / 1 跳过"。
副标题胶囊："每个服务有专属单测，再用 TestClient 串一条端到端用例验证主链路。"

主体一张大白卡，里面一张表格，3 列：测试文件 / 覆盖范围 / 结果。

行：
- test_media_pipeline.py：上传/probe/切片/抽帧/缩略图/失败路径 — 2 PASS（绿粗体）
- test_model_adapter.py：Mock 决定性 + 关键词强制 + OpenAI 协议 JSON 解析 + fallback — 13 PASS
- test_event_aggregator.py：逐帧分析 + 滑窗合并 + 状态推进 — 2 PASS
- test_hybrid_search.py：encode / ensure_embeddings / 关键词 + 向量重排 — 5 PASS
- test_exporter.py：真 ffmpeg 切片 + zip 内容校验 + 失败 fail_reason — 2 PASS
- test_auth_audit.py：JWT 闭环 + bcrypt 校验 + 角色 + 审计写读 — 8 PASS
- test_api_integration.py：login → upload → process → search → export — 1 PASS
- test_login_dialog.py：PySide6 LoginDialog 构造（headless 跳过）— 1 SKIP（橙粗体）
- test_client_api.py / test_backend_search.py：已有契约保持兼容 — 6 PASS

表头浅灰小写大写字母排版（letter-spacing 0.04em），表行交替仅靠 1px 底分隔，避免厚重感。
```

---

## Slide 11 — 诚实清单（未实现 / 风险）

```
生成 PPT 第 11 页 HTML，主题"诚实清单 — 这周没做完的部分"。
副标题胶囊："下周阶段汇报时主动说明，避免老师追问时被动。"

左卡《技术性未实现》标题用红色，5 条红圆点 li：
  真多模态模型调用：演示走 mock；接 DeepSeek/千问只需填 .env 中的 KEY
  pgvector / PostgreSQL：用 SQLite + 内存余弦等价替代
  sentence-transformers 真 embedding：默认未装，hash-ngram 兜底
  HLS 点播 / 异步任务队列：当前同步 FileResponse，长视频会阻塞
  PDF 摘要：导出包里目前是 Markdown + JSON

右卡上半《辅助页面未接》标题用黄色，4 条黄圆点 li：
  告警管理中心：静态展示，未接 audit_logs
  全天业务报告 / 模型与安全配置：仍是阶段一的页面雏形
  权限管理 UI：后端 users.role 字段就绪，前端编辑界面未做
  复核中心：API 已支持 review_status 改写，但页面未把它接上

右卡下半《已知风险》标题用蓝色，2 条蓝圆点 li：
  Mock 模型输出有随机性，演示前建议先固定一段视频跑一次
  长视频首次 process 偏慢，建议演示用 30–90s 素材

整页保持坦诚语气，不要任何遮掩或销售口吻。
```

---

## Slide 12 — 演示路径 + 阶段三

```
生成 PPT 第 12 页 HTML，主题"下一步路线图与演示路径"。
副标题胶囊："下周可直接演示完整链路；阶段三聚焦真模型接入、性能与辅助页面闭环。"

左卡《下周可演示路径》— 黑底 pre 块按 # 1. 起后端 / # 2. 起客户端（指向后端）/ # 3. 演示步骤 三段排列：
  uvicorn apps.backend.main:app --reload --port 8000
  $env:DVR_SEMANTIC_API_BASE="http://127.0.0.1:8000"
  python apps/desktop_client/main.py
  登录 demo / demo123 → 视频库 → 上传 30–60s 测试视频 → 等 status=indexed
  → 检索"找一下违停" → 选中事件 → 真 VLC seek 到事件起点
  → 右下角"导出证据包" → 弹出 zip 路径

右卡《阶段三计划》6 条 li：
  蓝·接真模型：填入 DeepSeek 或千问 API KEY，比较两家精度
  蓝·向量库：SQLite-vector / pgvector 二选一，正式上 embedding
  绿·异步任务队列：长视频处理走后台 + WebSocket 进度推
  绿·辅助页面：告警/报告/复核/权限 全部接真数据
  黄·指标埋点：检索响应时间、模型成本、导出耗时
  红·压力测试：单服务 ≤10 客户端并发的非功能性指标
```

---

## 整页重新生成

如果想一次性重生整套 PPT，把上面 12 段提示词依次拼接，再加一句封套：

```
请生成一个完整的 HTML 文件，包含 12 个 1280×720 的 <section class="slide"> 单页 PPT，共用一份 <style> 内联样式。视觉风格与作答规则严格按照"通用风格约束"。每页末尾放页码圆点（当前页对应颜色高亮）和右下角两位数字页码。文件应在浏览器中直接打开就能浏览，按 Cmd/Ctrl+P 打印导出 PDF 时每页占一张 A4 横向。
```

## 想转成真 PPTX 怎么做

- 浏览器打开 `phase2-report.html` → 打印 → 另存为 PDF（A4 横向 / 边距 0）
- 用 [pptxgenjs](https://github.com/gitbrent/PPTXGenJS) 或 [pdf2pptx](https://www.ilovepdf.com/pdf_to_powerpoint) 转 .pptx
- 也可以让 Claude 把上面每页提示词直接生成 `python-pptx` 代码，需要的话再来一轮即可
