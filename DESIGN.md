# DVR-Semantic Prototype Design System

This project must migrate the completed `DVR-Semantic` prototype, not invent a new visual system. Use the HTML prototype in `docs/prototype-source/` as the visual source of truth.

## 1. Prototype Source

The client design follows these prototype files:

- `系统状态概览.html`
- `语义检索中心.html`
- `视频库管理.html`
- `人工复核中心.html`
- `告警管理中心.html`
- `事故摘要预览.html`
- `证据与日志归档.html`
- `全天业务报告.html`
- `模型与安全配置.html`
- `角色与权限管理.html`
- `系统登录.html`

If the Qt implementation cannot reproduce a Tailwind/HTML effect exactly, keep the same information hierarchy, navigation label, status color, spacing rhythm, and interaction meaning.

## 2. Visual Language

The prototype uses a light operational dashboard style:

| Token | Hex | Prototype role |
| --- | --- | --- |
| App Background | `#F8FAFC` | Main page background |
| Panel | `#FFFFFF` | Page panels and cards |
| Soft Panel | `#F1F5F9` | Secondary cards and list backgrounds |
| Text | `#1E293B` | Primary slate text |
| Muted | `#64748B` | Secondary slate text |
| Border | `#E2E8F0` | Thin separators |
| Primary Blue | `#2563EB` | Active nav, search, primary actions |
| Indigo | `#4F46E5` | Logo gradient companion |
| Cyan | `#06B6D4` | Secondary AI/data accent |
| Amber | `#F59E0B` | Warning and export evidence |
| Red | `#EF4444` | Alerts, risk, rejected review |
| Green | `#22C55E` | Healthy, completed, confirmed |

The original prototype includes soft blue/indigo/cyan background glows and glass-like header behavior. In Qt, this can be approximated with a light background, white panels, blue active states, and subtle borders.

## 3. Navigation

Use the exact prototype navigation labels:

`概览`、`检索`、`视频流`、`复核`、`告警`、`事故`、`证据与日志`、`全天业务报告`

Right-side icon entries:

`模型与安全配置`、`角色与权限管理`、`系统登录`

## 4. Component Rules

- Page panels and cards may use large radii because the supplied prototype uses rounded-xl / rounded-3xl / rounded-[40px].
- Search result cards follow the prototype pattern: left confidence/status, title, event id, timestamp range, and jump playback action.
- The video/search page follows the prototype: left search/results area and right dark playback/evidence area.
- Dashboard cards use icon + metric + trend text.
- Review, alert, accident, evidence, report, settings, and role pages should keep the same section names and table/list density as the prototype.

## 5. Interaction Rules

- Clicking a result must call playback seek with `videoId + startSec + endSec`.
- Export buttons must call the evidence export API and show queued/success/failure state.
- Low-confidence events enter the manual review page.
- Active nav state is blue, normal nav state is slate, risky state is red, completed state is green.

## 6. Implementation Priority

1. `语义检索中心` as the main demonstration page.
2. `视频库管理` for upload and task state.
3. `系统状态概览` for dashboard metrics.
4. `人工复核中心` and `证据与日志归档` for closed-loop evidence.
5. Other pages can be implemented after the main chain is stable.
