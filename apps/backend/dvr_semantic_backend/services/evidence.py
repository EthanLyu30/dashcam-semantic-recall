from __future__ import annotations

from dvr_semantic_backend.schemas import ExportResponse

from .exporter import export_package


def queue_export(event_id: str, export_type: str = "package") -> ExportResponse:
    """Compatibility wrapper for the old queued-export API.

    The current course demo runs export synchronously, so this delegates to the
    real ffmpeg-backed package exporter and returns the finished artifact.
    """
    if export_type != "package":
        raise ValueError("Only package export is supported by the current exporter")
    result = export_package(event_id=event_id)
    return ExportResponse(
        event_id=result["event_id"],
        export_id=result["export_id"],
        status=result["status"],
        export_path=result["export_path"],
    )
