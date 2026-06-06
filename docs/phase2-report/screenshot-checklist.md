# 阶段汇报演练 — 截图 / 录屏清单

PPT 里已经用 HTML/SVG 画好了 mockup 和模拟终端输出，但**真截图永远比 mockup 更可信**。下面这份清单告诉你"该截哪几张、按什么顺序、放进 PPT 哪一页"。

下周演练时按这个清单走一遍，把截图保存到 `docs/phase2-report/shots/` 目录下，按文件名替换 PPT 里的 mockup 即可。

---

## 准备工作（一次性）

```powershell
# 1. 装齐依赖
python -m pip install -e ".[dev,desktop,backend,media,ai]"

# 2. 准备一段测试视频（建议 30~90s 的真实行车视频或随便一段 mp4）
#    放到 var/demo-clips/ 下，命名为 demo-driving.mp4

# 3. 起后端
uvicorn apps.backend.main:app --reload --port 8000

# 4. 新开终端，起客户端
$env:DVR_SEMANTIC_API_BASE="http://127.0.0.1:8000"
python apps/desktop_client/main.py
```

截图工具推荐 Windows 自带 `Win+Shift+S`（区域截图）或 ShareX。录 GIF 推荐 [ScreenToGif](https://www.screentogif.com/)。

---

## 静态截图清单（9 张）

> 命名规范：`shots/NN-<场景>.png`，编号对应 PPT 页码。

### shot 01-cover-real.png — 封面背景（可选）
- **拍**：一张真行车记录仪截图或一帧驾驶画面，灰度处理后做封面背景。
- **用途**：替换 PPT slide 1 居中卡片后的背景。
- **不做也行**：当前封面就足够"汇报感"。

### shot 02-test-output.png — pytest 真输出
- **场景**：终端跑 `python -m pytest -v --tb=short`，截到 `42 passed, 4 skipped` 那一行。
- **替换位置**：PPT slide 10 右侧的"pytest 实际输出"终端块。
- **小诀窍**：用 Windows Terminal 黑色主题截，跟 PPT 里的终端样式接得上。

### shot 03-login.png — 登录窗口
- **场景**：客户端启动后弹出的 LoginDialog，输入 `demo / demo123` 但**先别点登录**。
- **替换位置**：PPT slide 9 可以拼一张缩略图角标。

### shot 04-video-library.png — 视频库管理页（上传后）
- **场景**：登录后切到"视频流"页，已经上传完一段视频，看到表格里有一行状态 = `indexed`。
- **替换位置**：PPT slide 5 媒体目录布局旁边补一张缩略。

### shot 05-upload-progress.png — 上传中
- **场景**：刚点完"上传视频"，文件正在 POST 时的进度条/状态。
- **可选**：演示动态感时配。

### shot 06-search-result.png — 检索页全屏（**核心一张**）
- **场景**：检索"找一下违停"，左侧出现 2-3 个结果卡片，右侧 VLC 在播放，时间轴有彩色事件块。
- **替换位置**：PPT slide 9 的整个 mockup 区域。
- **注意**：等播到事件起点附近再截，画面更生动。

### shot 07-vlc-seek.png — VLC seek 到事件起点
- **场景**：点击结果卡片后，VLC 真的跳到 `event.start_sec`，进度条蓝色 marker 在事件位置。
- **替换位置**：和 shot 06 二选一，或放成 GIF（见下）。

### shot 08-export-dialog.png — 导出弹窗
- **场景**：点"导出证据包"后弹出的 QMessageBox，显示 zip 路径。
- **替换位置**：PPT slide 8 标题旁边贴一张缩略。

### shot 09-zip-contents.png — 解压后的证据包
- **场景**：用 Windows 资源管理器解压 `package.zip`，截到 `clip.mp4 + snapshot.jpg + report.md + report.json` 四个文件。
- **替换位置**：PPT slide 8 左卡的"导出包真实生成结构"终端块旁边。

### shot 10-report-md-preview.png — report.md 在 VS Code 预览
- **场景**：VS Code 打开 `report.md`，右侧预览渲染出来的中文摘要。
- **替换位置**：PPT slide 8 右卡。

### shot 11-audit-logs.png — 审计日志表
- **场景**：用 DBeaver/DataGrip/SQLite Browser 打开 `var/dvr_semantic.db`，截 `audit_logs` 表里最近 20 行。
- **替换位置**：PPT slide 4 架构图角落或者新加一页"操作留痕"。

---

## 动图清单（3 段，**最有冲击力**）

### gif 01-end-to-end.gif — 端到端 20 秒演示（**重点**）
**录这一段就值回票价。** 按这个脚本：

```
0:00  桌面端启动，弹出登录窗
0:02  输入 demo / demo123 → 登录
0:04  切到视频库管理页
0:05  点"上传视频" → 选 demo-driving.mp4
0:08  上传完成，看到状态变 indexed
0:11  切到检索页
0:12  输入"找一下白色车违停" → 回车
0:14  左侧出来 3 个结果，自动选中第 1 个
0:15  右侧 VLC 跳转到事件起点开始播
0:18  点"导出证据包"
0:19  弹出 zip 路径
0:20  结束
```

**录制要点**：
- 用 ScreenToGif 录 1280×720 区域，15fps 足够
- 鼠标点击高亮打开
- 录完压到 5MB 以下放进 git，超过 10MB 单独放网盘

### gif 02-vlc-seek-loop.gif — VLC seek 反复跳事件
- **场景**：点 3 个不同结果卡片，VLC 依次跳到 3 个事件起点。
- **替换位置**：PPT slide 9 右上角内嵌或者全屏替换 mockup。

### gif 03-timeline-highlight.gif — 时间轴事件高亮
- **场景**：鼠标移过时间轴，不同颜色事件块依次高亮，点击哪个就跳哪个。
- **替换位置**：PPT slide 9 时间轴区域。

---

## 把截图塞进 PPT 的最快做法

PPT 是单文件 HTML，**没用任何打包工具**。塞图就两步：

```bash
# 1. 截图保存到 shots/ 目录
mv ~/Pictures/Screenshot.png docs/phase2-report/shots/06-search-result.png

# 2. 在 phase2-report.html 里找到对应 slide 的占位元素
#    例如 slide 9 的整个 .desktop 块，直接替换成：
<img src="shots/06-search-result.png" style="width:100%;border-radius:12px;" />
```

如果不想动 HTML，最简单的办法：**在 PPT 旁边放一个 `shots/` 目录，演示时另开图片预览**——评委想看真实截图时你直接切窗口给他看。

---

## 演练 checklist（演示当天）

- [ ] 后端起好，`curl http://127.0.0.1:8000/health` 返回 ok
- [ ] 至少预先 process 完 1 段视频（避免现场上传等太久）
- [ ] 客户端能登录、能 seek、能导出
- [ ] `shots/` 目录里至少有 02 / 06 / 09 三张关键截图
- [ ] PPT 在 Chrome 全屏播放正常，F11 隐藏地址栏
- [ ] 准备一份 `report.md` 打印件，老师拿在手里看
