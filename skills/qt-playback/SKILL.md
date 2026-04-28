---
name: qt-playback
description: Use when changing the Qt6 desktop playback, result selection, timeline, or evidence demo flow.
owner: 吕霄阳
---

# Qt Playback Skill

## Goal

Keep the desktop workflow centered on "search -> click result -> seek playback -> inspect detail -> export evidence".

## Steps

1. Update DTOs in `dvr_semantic_client/models.py` only when the API contract changes.
2. Keep playback behavior in `widgets/video_player.py`.
3. Keep result rendering in `widgets/search_panel.py` and `widgets/result_card.py`.
4. Keep timeline rendering in `widgets/timeline.py`.
5. Verify event selection emits one seek command with `start_sec`.

## Checks

- Result cards show title, time range, confidence, tags, and summary.
- The selected event is visible in the detail panel and highlighted on the timeline.
- No UI component depends directly on backend database fields.

