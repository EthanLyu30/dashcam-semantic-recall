---
name: evidence-export
description: Use when implementing screenshots, clip export, evidence packages, or audit records.
owner: 倪羽辰
---

# Evidence Export Skill

## Goal

Export a reproducible evidence package for a selected semantic event.

## Package Contents

- One key snapshot.
- Optional short video clip from `start_sec` to `end_sec`.
- A text or JSON report with video id, event id, title, summary, confidence, timestamps, and export time.
- Audit record in `event_exports`.

## Guardrails

- Use original timeline seconds.
- Clip boundaries should include a small configurable pre/post buffer.
- Failed exports must leave an audit log with the failure reason.

