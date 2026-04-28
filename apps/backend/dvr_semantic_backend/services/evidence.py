from __future__ import annotations

from dvr_semantic_backend.schemas import ExportResponse


def queue_export(event_id: str, export_type: str = "package") -> ExportResponse:
    # TODO(倪羽辰): replace this with ffmpeg snapshot/clip export plus audit persistence.
    extension = "zip" if export_type == "package" else export_type
    return ExportResponse(
        event_id=event_id,
        export_id=f"exp-{event_id}",
        status="queued",
        export_path=f"media/exports/{event_id}.{extension}",
    )

