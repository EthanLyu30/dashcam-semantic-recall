"""FastAPI app wiring all services. Owns no business logic itself."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .db import (
    AuditLog,
    EventExport,
    SemanticEvent,
    Video,
    init_db,
    session_scope,
)
from .schemas import (
    AccidentDetailResponse,
    AccidentListResponse,
    AccidentSummaryResponse,
    ActionStatusResponse,
    AnalysisReport,
    AlertListResponse,
    AlertSummaryResponse,
    AuditLogOut,
    BatchExportItem,
    BatchExportRequest,
    BatchExportResponse,
    DashboardDistributionResponse,
    DashboardOverviewResponse,
    DashboardTrendResponse,
    DailyReportResponse,
    EventOut,
    ExportListItem,
    ExportListResponse,
    ExportRequest,
    ExportResponse,
    LoginRequest,
    LoginResponse,
    ModelSettingsResponse,
    ModelTestResponse,
    PermissionListResponse,
    ProcessReport,
    ReportExportResponse,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewFeedResponse,
    ReviewRequest,
    ReviewTaskItem,
    ReviewTaskListResponse,
    RoleListResponse,
    SecuritySettingsResponse,
    SearchRequest,
    SearchResponse,
    UploadResponse,
    UserListResponse,
    VideoListResponse,
    VideoOut,
)
from .services import audit as audit_service
from .services import auth as auth_service
from .services import event_aggregator
from .services import exporter as exporter_service
from .services import final_stage
from .services import hybrid_search
from .services import media_pipeline


def _video_to_out(v: Video) -> VideoOut:
    thumb = ""
    if v.thumbnail_path:
        thumb = f"/media/thumbnails/{v.id}.jpg"
    return VideoOut(
        id=v.id,
        title=v.title,
        duration_sec=v.duration_sec or 0,
        status=v.process_status,
        thumbnail_url=thumb,
        source_path=v.source_path or "",
        fail_reason=v.fail_reason or "",
    )


def _event_to_out(event: SemanticEvent, similarity: float = 0.0, rank_no: int = 0,
                  answer_text: str = "") -> EventOut:
    return EventOut(
        id=event.id,
        video_id=event.video_id,
        event_type=event.event_type,
        title=event.title,
        summary=event.summary or "",
        start_sec=event.start_sec,
        end_sec=event.end_sec,
        confidence=event.confidence or 0.0,
        tags=list(event.tags_json or []),
        thumbnail_url=f"/media/frames/{event.video_id}/{Path(event.thumbnail_path).name}"
        if event.thumbnail_path else "",
        review_status=event.review_status or "pending",
        similarity_score=similarity,
        rank_no=rank_no,
        answer_text=answer_text,
    )


def create_app() -> FastAPI:
    init_db()
    auth_service.ensure_seed_users()

    app = FastAPI(
        title="Dashcam Semantic Recall API",
        version="0.2.0",
        description="REST contract for the DVR-Semantic desktop client.",
    )

    media_root = media_pipeline.media_root()
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_root)), name="media")

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "request_id": request_id,
                "code": f"0{exc.status_code}",
                "message": exc.detail if isinstance(exc.detail, str) else "request rejected",
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": app.version}

    # ---- dashboard / operational views ----
    @app.get("/api/dashboard/overview", response_model=DashboardOverviewResponse)
    def dashboard_overview(
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> dict[str, Any]:
        return final_stage.dashboard_overview()

    @app.get("/api/dashboard/trends", response_model=DashboardTrendResponse)
    def dashboard_trends(
        days: int = 7,
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> dict[str, Any]:
        return final_stage.dashboard_trends(days=days)

    @app.get(
        "/api/dashboard/event-distribution",
        response_model=DashboardDistributionResponse,
    )
    def dashboard_distribution(
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> DashboardDistributionResponse:
        return DashboardDistributionResponse(items=final_stage.event_distribution())

    @app.get("/api/dashboard/review-feed", response_model=ReviewFeedResponse)
    def dashboard_review_feed(
        limit: int = 20,
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> ReviewFeedResponse:
        return ReviewFeedResponse(items=final_stage.review_feed(limit=limit))

    # ---- auth ----
    @app.post("/api/auth/login", response_model=LoginResponse)
    def login(body: LoginRequest, request: Request) -> LoginResponse:
        try:
            ctx = auth_service.authenticate(body.username, body.password)
        except ValueError as exc:
            audit_service.log_action(
                request_id=request.state.request_id,
                user_id=None,
                action="auth.login",
                result_code="06001",
                message=f"login failed for {body.username}",
            )
            raise HTTPException(status_code=401, detail=str(exc))
        token = auth_service.issue_token(ctx)
        with session_scope() as session:
            from .db import User
            user = session.query(User).filter(User.id == ctx.user_id).one_or_none()
            display = user.display_name if user else ctx.username
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="auth.login",
            result_code="00000",
            message=f"login success role={ctx.role}",
        )
        return LoginResponse(
            token=token,
            user_id=ctx.user_id,
            username=ctx.username,
            role=ctx.role,
            display_name=display,
        )

    # ---- videos ----
    @app.get("/api/videos", response_model=VideoListResponse)
    def list_videos(ctx: auth_service.AuthContext = Depends(auth_service.require_auth)) -> VideoListResponse:
        with session_scope() as session:
            videos = session.query(Video).order_by(Video.created_at.desc()).all()
            items = [_video_to_out(v) for v in videos]
        return VideoListResponse(items=items)

    @app.get("/api/videos/{video_id}", response_model=VideoOut)
    def get_video(video_id: str,
                  ctx: auth_service.AuthContext = Depends(auth_service.require_auth)) -> VideoOut:
        with session_scope() as session:
            v = session.query(Video).filter(Video.id == video_id).one_or_none()
            if v is None:
                raise HTTPException(status_code=404, detail="video not found")
            return _video_to_out(v)

    @app.post("/api/videos/upload", response_model=UploadResponse)
    async def upload_video(
        request: Request,
        file: UploadFile = File(...),
        title: str = Form(""),
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> UploadResponse:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="empty file")
        video_title = title or file.filename or "Untitled"
        video_id = media_pipeline.save_upload(
            file_bytes=contents,
            original_filename=file.filename or "video.mp4",
            title=video_title,
            owner_id=ctx.user_id,
        )
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="video.upload",
            target_type="video",
            target_id=video_id,
            message=f"uploaded {file.filename or ''} ({len(contents)} bytes)",
        )
        return UploadResponse(video_id=video_id, status="uploaded",
                               request_id=request.state.request_id)

    @app.post("/api/videos/{video_id}/preprocess", response_model=ProcessReport)
    def preprocess(video_id: str, request: Request,
                   ctx: auth_service.AuthContext = Depends(auth_service.require_auth)) -> ProcessReport:
        try:
            stats = media_pipeline.run_preprocess(video_id)
        except Exception as exc:
            audit_service.log_action(
                request_id=request.state.request_id,
                user_id=ctx.user_id,
                action="video.preprocess",
                target_type="video",
                target_id=video_id,
                result_code="01001",
                message=str(exc),
            )
            raise HTTPException(status_code=500, detail=f"preprocess failed: {exc}")
        with session_scope() as session:
            v = session.query(Video).filter(Video.id == video_id).one_or_none()
            status = v.process_status if v else "unknown"
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="video.preprocess",
            target_type="video",
            target_id=video_id,
            message=f"segments={stats.get('segments', 0)} frames={stats.get('frames', 0)}",
        )
        return ProcessReport(
            video_id=video_id,
            segments=stats.get("segments", 0),
            frames=stats.get("frames", 0),
            duration_sec=stats.get("duration_sec", 0),
            status=status,
        )

    @app.post("/api/videos/{video_id}/analyze", response_model=AnalysisReport)
    def analyze(video_id: str, request: Request,
                ctx: auth_service.AuthContext = Depends(auth_service.require_auth)) -> AnalysisReport:
        try:
            stats = event_aggregator.run_full_analysis(video_id)
        except Exception as exc:
            audit_service.log_action(
                request_id=request.state.request_id,
                user_id=ctx.user_id,
                action="video.analyze",
                target_type="video",
                target_id=video_id,
                result_code="02001",
                message=str(exc),
            )
            raise HTTPException(status_code=500, detail=f"analyze failed: {exc}")
        with session_scope() as session:
            v = session.query(Video).filter(Video.id == video_id).one_or_none()
            status = v.process_status if v else "unknown"
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="video.analyze",
            target_type="video",
            target_id=video_id,
            message=f"frames={stats.get('frames_analyzed',0)} events={stats.get('events_created',0)}",
        )
        return AnalysisReport(
            video_id=video_id,
            frames_analyzed=stats.get("frames_analyzed", 0),
            events_created=stats.get("events_created", 0),
            status=status,
        )

    @app.post("/api/videos/{video_id}/process", response_model=AnalysisReport)
    def upload_to_indexed(video_id: str, request: Request,
                          ctx: auth_service.AuthContext = Depends(auth_service.require_auth)) -> AnalysisReport:
        """便利方法：preprocess + analyze 一次跑完。"""
        try:
            media_pipeline.run_preprocess(video_id)
            stats = event_aggregator.run_full_analysis(video_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        with session_scope() as session:
            v = session.query(Video).filter(Video.id == video_id).one_or_none()
            status = v.process_status if v else "unknown"
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="video.process",
            target_type="video",
            target_id=video_id,
            message=f"frames={stats.get('frames_analyzed',0)} events={stats.get('events_created',0)}",
        )
        return AnalysisReport(
            video_id=video_id,
            frames_analyzed=stats.get("frames_analyzed", 0),
            events_created=stats.get("events_created", 0),
            status=status,
        )

    @app.get("/api/videos/{video_id}/stream")
    def stream_video(video_id: str):
        with session_scope() as session:
            v = session.query(Video).filter(Video.id == video_id).one_or_none()
            if v is None or not v.source_path:
                raise HTTPException(status_code=404, detail="video file missing")
            path = Path(v.source_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="video file missing on disk")
        return FileResponse(str(path), media_type="video/mp4", filename=path.name)

    # ---- events ----
    @app.get("/api/events/{event_id}", response_model=EventOut)
    def event_detail(event_id: str,
                     ctx: auth_service.AuthContext = Depends(auth_service.require_auth)) -> EventOut:
        with session_scope() as session:
            event = session.query(SemanticEvent).filter(SemanticEvent.id == event_id).one_or_none()
            if event is None:
                raise HTTPException(status_code=404, detail="event not found")
            return _event_to_out(event)

    @app.post("/api/events/{event_id}/review", response_model=EventOut)
    def review_event(event_id: str, body: ReviewRequest, request: Request,
                     ctx: auth_service.AuthContext = Depends(
                         auth_service.require_role("reviewer", "admin")
                     )) -> EventOut:
        if body.review_status not in ("confirmed", "rejected", "reviewing", "pending"):
            raise HTTPException(status_code=400, detail="invalid review_status")
        with session_scope() as session:
            event = session.query(SemanticEvent).filter(SemanticEvent.id == event_id).one_or_none()
            if event is None:
                raise HTTPException(status_code=404, detail="event not found")
            event.review_status = body.review_status
            session.flush()
            out = _event_to_out(event)
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="event.review",
            target_type="event",
            target_id=event_id,
            message=f"status={body.review_status} note={body.note[:64]}",
        )
        return out

    # ---- review tasks (full decision API) ----

    @app.get("/api/review/tasks", response_model=ReviewTaskListResponse)
    def list_review_tasks(
        status: str = "reviewing",
        event_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
        ctx: auth_service.AuthContext = Depends(
            auth_service.require_role("reviewer", "admin")
        ),
    ) -> ReviewTaskListResponse:
        with session_scope() as session:
            q = session.query(SemanticEvent).filter(SemanticEvent.review_status == status)
            if event_type:
                q = q.filter(SemanticEvent.event_type == event_type)
            total = q.count()
            events = (
                q.order_by(SemanticEvent.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            items = [
                ReviewTaskItem(
                    event_id=e.id,
                    video_id=e.video_id,
                    event_type=e.event_type,
                    title=e.title,
                    confidence=e.confidence or 0.0,
                    review_status=e.review_status or "pending",
                    thumbnail_url=f"/media/frames/{e.video_id}/{Path(e.thumbnail_path).name}"
                    if e.thumbnail_path else "",
                    created_at=str(e.created_at),
                )
                for e in events
            ]
        return ReviewTaskListResponse(items=items, total=total)

    @app.post(
        "/api/review/tasks/{event_id}/decision",
        response_model=ReviewDecisionResponse,
    )
    def submit_review_decision(
        event_id: str,
        body: ReviewDecisionRequest,
        request: Request,
        ctx: auth_service.AuthContext = Depends(
            auth_service.require_role("reviewer", "admin")
        ),
    ) -> ReviewDecisionResponse:
        if body.decision not in ("confirmed", "rejected", "pending"):
            raise HTTPException(status_code=400, detail="invalid decision")

        with session_scope() as session:
            event = session.query(SemanticEvent).filter(
                SemanticEvent.id == event_id
            ).one_or_none()
            if event is None:
                raise HTTPException(status_code=404, detail="event not found")

            event.review_status = body.decision
            if body.corrected_event_type:
                event.event_type = body.corrected_event_type
            if body.corrected_title:
                event.title = body.corrected_title
            if body.corrected_tags:
                event.tags_json = body.corrected_tags

            session.flush()
            reviewed_at = str(event.updated_at)

        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="review.decision",
            target_type="event",
            target_id=event_id,
            message=f"decision={body.decision} note={body.note[:64]}",
        )
        return ReviewDecisionResponse(
            event_id=event_id,
            review_status=body.decision,
            reviewer_id=ctx.user_id,
            reviewed_at=reviewed_at,
        )

    @app.get("/api/events", response_model=list[EventOut])
    def list_events(video_id: str | None = None, review_status: str | None = None,
                    ctx: auth_service.AuthContext = Depends(auth_service.require_auth)) -> list[EventOut]:
        with session_scope() as session:
            q = session.query(SemanticEvent)
            if video_id:
                q = q.filter(SemanticEvent.video_id == video_id)
            if review_status:
                q = q.filter(SemanticEvent.review_status == review_status)
            events = q.order_by(SemanticEvent.start_sec.asc()).all()
            return [_event_to_out(e) for e in events]

    # ---- search ----
    @app.post("/api/search", response_model=SearchResponse)
    def search(body: SearchRequest, request: Request,
               ctx: auth_service.AuthContext = Depends(auth_service.require_auth)) -> SearchResponse:
        result = hybrid_search.hybrid_search(
            query=body.query,
            video_id=body.video_id,
            top_k=body.top_k,
            user_id=ctx.user_id,
            mode=body.mode,
        )
        # rebuild EventOut objects (the service returned a list of dicts)
        events = [
            EventOut(
                id=r["event_id"],
                video_id=body.video_id or r.get("video_id", ""),
                event_type=r["event_type"],
                title=r["title"],
                summary=r["summary"],
                start_sec=r["start_sec"],
                end_sec=r["end_sec"],
                confidence=r["confidence"],
                tags=list(r.get("tags", [])),
                thumbnail_url=f"/media/frames/{r.get('video_id', body.video_id or '')}/{Path(r['thumbnail_path']).name}"
                if r.get("thumbnail_path") else "",
                review_status=r.get("review_status", "pending"),
                similarity_score=r["similarity_score"],
                rank_no=r["rank_no"],
                answer_text=r["answer_text"],
            )
            for r in result["results"]
        ]
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="search.execute",
            target_type="query",
            target_id=result["query_id"],
            message=f"q='{body.query[:80]}' results={len(events)}",
        )
        return SearchResponse(
            query_id=result["query_id"],
            query=result["query"],
            video_id=result["video_id"],
            mode=result["mode"],
            elapsed_ms=result["elapsed_ms"],
            results=events,
        )

    # ---- export ----
    @app.post("/api/events/{event_id}/export", response_model=ExportResponse)
    def export_event(event_id: str, body: ExportRequest, request: Request,
                     ctx: auth_service.AuthContext = Depends(auth_service.require_auth)) -> ExportResponse:
        try:
            result = exporter_service.export_package(
                event_id=event_id,
                operator_id=ctx.user_id,
                include_video=body.include_video,
                include_snapshot=body.include_snapshot,
                include_report=body.include_report,
                force=body.force,
            )
        except (KeyError, ValueError):
            raise HTTPException(status_code=404, detail="event not found")
        except Exception as exc:
            audit_service.log_action(
                request_id=request.state.request_id,
                user_id=ctx.user_id,
                action="event.export",
                target_type="event",
                target_id=event_id,
                result_code="05001",
                message=str(exc),
            )
            raise HTTPException(status_code=500, detail=f"export failed: {exc}")
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="event.export",
            target_type="event",
            target_id=event_id,
            message=f"export_id={result['export_id']} type={body.export_type} "
                    f"reused={result.get('reused', False)}",
        )
        return ExportResponse(
            event_id=result["event_id"],
            export_id=result["export_id"],
            status=result["status"],
            export_path=result["export_path"],
            reused=result.get("reused", False),
        )

    @app.post("/api/exports/batch", response_model=BatchExportResponse)
    def export_batch(body: BatchExportRequest, request: Request,
                     ctx: auth_service.AuthContext = Depends(auth_service.require_auth)
                     ) -> BatchExportResponse:
        """Controlled batch export (FR-05): export multiple events at once."""
        try:
            result = exporter_service.export_batch(
                event_ids=body.event_ids,
                operator_id=ctx.user_id,
                include_video=body.include_video,
                include_snapshot=body.include_snapshot,
                include_report=body.include_report,
                force=body.force,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="event.export.batch",
            target_type="event",
            target_id=",".join(body.event_ids[:5]),
            message=f"total={result['total']} ok={result['succeeded']} "
                    f"fail={result['failed']}",
        )
        return BatchExportResponse(
            total=result["total"],
            succeeded=result["succeeded"],
            failed=result["failed"],
            items=[BatchExportItem(**item) for item in result["items"]],
        )

    @app.get("/api/exports", response_model=ExportListResponse)
    def list_exports(event_id: str | None = None,
                     ctx: auth_service.AuthContext = Depends(auth_service.require_auth)) -> ExportListResponse:
        rows = exporter_service.list_exports(event_id=event_id)
        return ExportListResponse(
            items=[
                ExportListItem(
                    id=r["id"],
                    event_id=r["event_id"],
                    export_type=r["export_type"],
                    status=r["status"],
                    export_path=r["export_path"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        )

    # ---- alerts / accidents / reports ----
    @app.get("/api/alerts/summary", response_model=AlertSummaryResponse)
    def alerts_summary(
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> dict[str, Any]:
        return final_stage.alert_summary()

    @app.get("/api/alerts", response_model=AlertListResponse)
    def list_alerts(
        status: str | None = None,
        event_type: str | None = None,
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> dict[str, Any]:
        return final_stage.list_alerts(status=status, event_type=event_type)

    @app.post("/api/alerts/{alert_id}/ack", response_model=ActionStatusResponse)
    def ack_alert(
        alert_id: str,
        request: Request,
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> dict[str, str]:
        try:
            result = final_stage.update_alert(alert_id, "acknowledged")
        except ValueError:
            raise HTTPException(status_code=404, detail="alert not found")
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="alert.ack",
            target_type="alert",
            target_id=alert_id,
        )
        return result

    @app.post("/api/alerts/{alert_id}/resolve", response_model=ActionStatusResponse)
    def resolve_alert(
        alert_id: str,
        request: Request,
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> dict[str, str]:
        try:
            result = final_stage.update_alert(alert_id, "resolved")
        except ValueError:
            raise HTTPException(status_code=404, detail="alert not found")
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="alert.resolve",
            target_type="alert",
            target_id=alert_id,
        )
        return result

    @app.get("/api/accidents", response_model=AccidentListResponse)
    def list_accidents(
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> AccidentListResponse:
        return AccidentListResponse(items=final_stage.list_accidents())

    @app.get("/api/accidents/{accident_id}", response_model=AccidentDetailResponse)
    def accident_detail(
        accident_id: str,
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> dict[str, Any]:
        try:
            return final_stage.accident_detail(accident_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="accident not found")

    @app.post(
        "/api/accidents/{accident_id}/summary",
        response_model=AccidentSummaryResponse,
    )
    def generate_accident_summary(
        accident_id: str,
        request: Request,
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> dict[str, str]:
        try:
            result = final_stage.accident_summary(accident_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="accident not found")
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="accident.summary",
            target_type="accident",
            target_id=accident_id,
        )
        return result

    @app.get("/api/reports/daily", response_model=DailyReportResponse)
    def daily_report(
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> dict[str, Any]:
        return final_stage.daily_report()

    @app.post("/api/reports/daily/export", response_model=ReportExportResponse)
    def export_daily_report(
        request: Request,
        ctx: auth_service.AuthContext = Depends(auth_service.require_auth),
    ) -> dict[str, str]:
        result = final_stage.export_daily_report()
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="report.daily.export",
            target_type="report",
            target_id=result["report_id"],
        )
        return result

    # ---- settings / users / roles ----
    @app.get("/api/settings/model", response_model=ModelSettingsResponse)
    def model_settings(
        ctx: auth_service.AuthContext = Depends(
            auth_service.require_role("admin", "reviewer")
        ),
    ) -> dict[str, Any]:
        return final_stage.model_settings()

    @app.post("/api/settings/model/test", response_model=ModelTestResponse)
    def model_test(
        request: Request,
        ctx: auth_service.AuthContext = Depends(
            auth_service.require_role("admin", "reviewer")
        ),
    ) -> dict[str, str]:
        result = final_stage.model_test()
        audit_service.log_action(
            request_id=request.state.request_id,
            user_id=ctx.user_id,
            action="settings.model.test",
            target_type="settings",
            target_id="model",
            message=f"provider={result['provider']} status={result['status']}",
        )
        return result

    @app.get("/api/settings/security", response_model=SecuritySettingsResponse)
    def security_settings(
        ctx: auth_service.AuthContext = Depends(
            auth_service.require_role("admin", "reviewer")
        ),
    ) -> dict[str, Any]:
        return final_stage.security_settings()

    @app.get("/api/users", response_model=UserListResponse)
    def list_users(
        ctx: auth_service.AuthContext = Depends(auth_service.require_role("admin")),
    ) -> UserListResponse:
        return UserListResponse(items=final_stage.list_users())

    @app.get("/api/roles", response_model=RoleListResponse)
    def list_roles(
        ctx: auth_service.AuthContext = Depends(auth_service.require_role("admin")),
    ) -> RoleListResponse:
        return RoleListResponse(items=final_stage.roles())

    @app.get("/api/permissions", response_model=PermissionListResponse)
    def list_permissions(
        ctx: auth_service.AuthContext = Depends(auth_service.require_role("admin")),
    ) -> PermissionListResponse:
        return PermissionListResponse(permissions=final_stage.permissions())

    # ---- audit ----
    @app.get("/api/audit/logs", response_model=list[AuditLogOut])
    def get_audit_logs(limit: int = 100,
                       ctx: auth_service.AuthContext = Depends(
                           auth_service.require_role("admin", "reviewer")
                       )) -> list[AuditLogOut]:
        rows = audit_service.recent_logs(limit=limit)
        return [AuditLogOut(**r) for r in rows]

    return app
