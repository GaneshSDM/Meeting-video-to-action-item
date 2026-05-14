import os
import uuid
import shutil
import asyncio
import json
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from .models import JobStatus, AnalysisOutput, ExportRequest, AnalysisRequest
from .tasks import run_pipeline, run_sharepoint_pipeline, jobs, logs

app = FastAPI(title="Decision Minds - Meeting AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.on_event("startup")
async def startup():
    try:
        from .database import init_db
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database init failed (will use JSONL fallback): {e}")

    try:
        from .scheduler import start as sched_start
        if sched_start():
            print("Autonomous scheduler started")
        else:
            print("Autonomous mode not enabled (set ENABLE_AUTONOMOUS=true)")
    except Exception as e:
        print(f"Scheduler init failed: {e}")


def _cleanup_old_files(exclude_paths: set[str] | None = None) -> None:
    exclude_paths = {os.path.abspath(p) for p in (exclude_paths or set())}
    for directory in ("videos", "audio", "audio_chunks", "transcripts"):
        if not os.path.isdir(directory):
            continue
        for name in os.listdir(directory):
            path = os.path.abspath(os.path.join(directory, name))
            if path in exclude_paths:
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception:
                pass


@app.get("/")
async def root():
    return {
        "service": "Decision Minds Meeting AI API",
        "status": "ok",
        "frontend": "http://localhost:3000",
        "docs": "/docs",
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.post("/upload", response_model=JobStatus)
async def upload_video(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    job_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")

    active_paths = {
        os.path.abspath(job["file_path"])
        for job in jobs.values()
        if job.get("file_path") and job["status"] in {"pending", "processing"}
    }
    _cleanup_old_files(exclude_paths=active_paths)

    with open(file_path, "wb") as buffer:
        while content := await file.read(1024 * 1024):
            buffer.write(content)

    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "result": None,
        "error": None,
        "file_path": file_path,
    }

    background_tasks.add_task(run_pipeline, job_id, file_path)
    return jobs[job_id]


@app.post("/analyze", response_model=JobStatus)
async def analyze_sharepoint(
    background_tasks: BackgroundTasks, body: AnalysisRequest
):
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "result": None,
        "error": None,
    }

    background_tasks.add_task(run_sharepoint_pipeline, job_id, body.sharepoint_url)
    return jobs[job_id]


@app.get("/download/{job_id}")
async def download_json(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    entry = jobs[job_id]
    if entry["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not yet completed")

    result = entry.get("result")
    if not result:
        raise HTTPException(status_code=400, detail="No results to download")

    json_str = result.model_dump_json(indent=2)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=\"action_items_{job_id[:8]}.json\""
        },
    )


@app.get("/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    entry = jobs[job_id]
    result = entry.get("result")
    if result is not None and isinstance(result, AnalysisOutput):
        entry["result"] = result
    return entry


@app.get("/logs/{job_id}")
async def stream_logs(job_id: str):
    async def event_generator():
        last_idx = 0
        while True:
            if job_id in logs:
                current_logs = logs[job_id]
                if len(current_logs) > last_idx:
                    for i in range(last_idx, len(current_logs)):
                        yield f"data: {current_logs[i]}\n\n"
                    last_idx = len(current_logs)

            if (
                job_id in jobs
                and jobs[job_id]["status"] in ["completed", "failed"]
            ):
                yield "data: [DONE]\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/export/{job_id}")
async def export_results(job_id: str, body: ExportRequest, background_tasks: BackgroundTasks):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    entry = jobs[job_id]
    if entry["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not yet completed")

    result = entry.get("result")
    if not result:
        raise HTTPException(status_code=400, detail="No results to export")

    from .crm_connector import CRMConnector

    crm = CRMConnector()
    export_result = crm.export_results(
        result,
        target=body.target,
        sharepoint_url=body.sharepoint_url,
    )

    return export_result


@app.patch("/events/{event_id}")
async def update_event(event_id: str, job_id: str, update: dict):
    """Update a calendar event identified by event_id for a completed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    entry = jobs[job_id]
    if entry["status"] != "completed" or not entry.get("result"):
        raise HTTPException(status_code=400, detail="Job not completed")
    analysis: AnalysisOutput = entry["result"]
    target_item = None
    for item in analysis.action_items:
        if getattr(item, "event_id", None) == event_id:
            target_item = item
            break
    if not target_item:
        raise HTTPException(status_code=404, detail="Event not found in job results")
    from .calendar_service import CalendarService
    from .teams_service import TeamsService
    calendar = CalendarService()
    calendar_updates = {}
    if "title" in update:
        calendar_updates["summary"] = update["title"]
        target_item.task = update["title"]
    if "start" in update:
        calendar_updates["start"] = {"dateTime": update["start"], "timeZone": "UTC"}
    if "end" in update:
        calendar_updates["end"] = {"dateTime": update["end"], "timeZone": "UTC"}
    if "participants" in update:
        calendar_updates["guests"] = update["participants"]
        target_item.context = f"Participants: {', '.join(update['participants'])}"
    try:
        calendar.update_event(event_id, calendar_updates)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calendar update failed: {e}")
    
    if getattr(target_item, "teams_event_id", None):
        try:
            teams = TeamsService()
            teams_updates = {}
            if "title" in update:
                teams_updates["subject"] = update["title"]
            if "start" in update:
                teams_updates["start"] = {"dateTime": update["start"], "timeZone": "UTC"}
            if "end" in update:
                teams_updates["end"] = {"dateTime": update["end"], "timeZone": "UTC"}
            if "participants" in update:
                teams_updates["attendees"] = [{"emailAddress": {"address": p}} for p in update["participants"]]
            teams.update_event(target_item.teams_event_id, teams_updates)
        except Exception as te:
            raise HTTPException(status_code=500, detail=f"Teams update failed: {te}")
    return {"status": "updated", "event_id": event_id}


@app.delete("/events/{event_id}")
async def delete_event(event_id: str, job_id: str):
    """Delete a calendar event and remove it from job results."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    entry = jobs[job_id]
    if entry["status"] != "completed" or not entry.get("result"):
        raise HTTPException(status_code=400, detail="Job not completed")
    analysis: AnalysisOutput = entry["result"]
    new_items = []
    found = False
    team_event_id = None
    for item in analysis.action_items:
        if getattr(item, "event_id", None) == event_id:
            found = True
            team_event_id = getattr(item, "teams_event_id", None)
            continue
        new_items.append(item)
    if not found:
        raise HTTPException(status_code=404, detail="Event not found in job results")
    from .calendar_service import CalendarService
    from .teams_service import TeamsService
    calendar = CalendarService()
    try:
        calendar.delete_event(event_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calendar delete failed: {e}")
    if team_event_id:
        try:
            teams = TeamsService()
            teams.delete_event(team_event_id)
        except Exception as te:
            raise HTTPException(status_code=500, detail=f"Teams delete failed: {te}")
    analysis.action_items = new_items
    log_path = "action_items_log.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"job_id": job_id, "deleted_event": event_id}, default=str) + "\n")
    return {"status": "deleted", "event_id": event_id}


@app.get("/meetings")
async def get_meetings():
    """Return all meetings from database, with in-memory job fallback."""
    meetings: list[dict] = []
    seen_ids: set[str] = set()

    # Primary: read from Supabase
    try:
        from .database import get_meetings as db_get_meetings
        meetings = db_get_meetings()
        for m in meetings:
            seen_ids.add(m["job_id"])
    except Exception as e:
        print(f"Database meetings read failed: {e}")

    # Fallback: JSONL log
    if not meetings:
        log_path = "action_items_log.jsonl"
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    action_items = entry.get("action_items", [])
                    participants = entry.get("participants", [])
                    log_job_id = entry.get("job_id") or f"log_{idx}"
                    meetings.append({
                        "job_id": log_job_id,
                        "title": entry.get("meeting_summary", "Untitled Meeting")[:120],
                        "team": "dev-team-001",
                        "source": "Transcript",
                        "tasks": len(action_items),
                        "status": "Processed",
                        "date": entry.get("created_at", "Unknown")[:10] if entry.get("created_at") else "Unknown",
                        "participants": participants,
                        "summary": entry.get("meeting_summary", ""),
                    })
                    seen_ids.add(log_job_id)

    # Include in-progress/pending jobs from memory
    for job_id, job in jobs.items():
        if job_id in seen_ids:
            continue
        result = job.get("result")
        action_items = result.action_items if result and hasattr(result, "action_items") else []
        meetings.append({
            "job_id": job_id,
            "title": os.path.basename(job.get("file_path", "Meeting")),
            "team": "dev-team-001",
            "source": "Upload",
            "tasks": len(action_items),
            "status": "Processed" if job["status"] == "completed" else "Failed" if job["status"] == "failed" else "Processing",
            "date": "Now",
            "participants": result.participants if result and hasattr(result, "participants") else [],
            "summary": result.meeting_summary if result and hasattr(result, "meeting_summary") else "",
        })

    return sorted(meetings, key=lambda m: m["date"], reverse=True)


@app.get("/tasks")
async def get_tasks():
    """Return all action items across all completed meetings."""
    try:
        from .database import get_tasks as db_get_tasks
        return db_get_tasks()
    except Exception as e:
        print(f"Database tasks read failed: {e}")

    # Fallback to JSONL
    all_tasks: list[dict] = []
    log_path = "action_items_log.jsonl"
    if os.path.isfile(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                meeting_title = entry.get("meeting_summary", "Untitled")[:80]
                for item in entry.get("action_items", []):
                    owner = item.get("owner", "Unknown")
                    initials = "".join([p[0] for p in owner.split()[:2]]).upper() if owner != "Unknown" else "??"
                    task_title = item.get("task", "")
                    task_owner = owner if owner != "Unknown" else None
                    all_tasks.append({
                        "id": str(abs(hash(f"{task_title}|{meeting_title}|{task_owner or 'unassigned'}")) % 10_000_000).zfill(7),
                        "title": task_title,
                        "meeting": meeting_title,
                        "owner": task_owner,
                        "initials": initials if owner != "Unknown" else None,
                        "due": item.get("deadline"),
                        "priority": item.get("priority", "medium").capitalize(),
                        "confidence": item.get("confidence", 0.5),
                        "context": item.get("context", ""),
                        "status": "todo",
                    })
    return all_tasks


@app.patch("/tasks/{task_id}")
async def update_task_status(task_id: str, body: dict):
    """Update a task's status (todo, progress, done)."""
    new_status = body.get("status")
    if new_status not in ("todo", "progress", "done"):
        raise HTTPException(status_code=400, detail="Status must be todo, progress, or done")

    try:
        from .database import update_task_status as db_update
        db_update(task_id, new_status)
    except Exception as e:
        print(f"Database task update failed: {e}")

    return {"task_id": task_id, "status": new_status}


@app.get("/dashboard")
async def get_dashboard():
    """Return aggregated dashboard metrics from database."""
    try:
        from .database import get_dashboard_stats
        return get_dashboard_stats()
    except Exception as e:
        print(f"Database dashboard read failed: {e}")

    # JSONL fallback
    all_tasks_list: list[dict] = []
    all_meetings: list[dict] = []
    total_participants: set[str] = set()
    log_path = "action_items_log.jsonl"
    if os.path.isfile(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                meeting_title = entry.get("meeting_summary", "Untitled")[:80]
                for item in entry.get("action_items", []):
                    all_tasks_list.append({"title": item.get("task", ""), "meeting": meeting_title, "owner": item.get("owner", "Unknown"), "priority": item.get("priority", "medium")})
                for p in entry.get("participants", []):
                    total_participants.add(p)
                all_meetings.append({"title": meeting_title, "date": entry.get("created_at", "Unknown"), "tasks": len(entry.get("action_items", []))})

    total_tasks = len(all_tasks_list)
    high_priority = sum(1 for t in all_tasks_list if t["priority"] == "high")

    return {
        "total_tasks": total_tasks,
        "in_progress": 0,
        "completed": 0,
        "overdue": high_priority,
        "total_meetings": len(all_meetings),
        "total_participants": len(total_participants),
        "recent_meetings": sorted(all_meetings, key=lambda m: m["date"], reverse=True)[:5],
        "activity": [
            {"title": f"{total_tasks} total action items extracted", "time": "across all meetings"},
            {"title": f"{len(all_meetings)} meetings processed", "time": "from video recordings"},
            {"title": f"{len(total_participants)} unique participants", "time": "identified across meetings"},
        ],
    }


@app.get("/analytics/timeseries")
async def get_analytics_timeseries():
    try:
        from .database import get_analytics_timeseries
        return get_analytics_timeseries()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics unavailable: {e}")


@app.get("/analytics/summary")
async def get_analytics_summary():
    try:
        from .database import get_dashboard_stats
        stats = get_dashboard_stats()
        return {
            "tasksByPriority": {"high": stats["overdue"], "medium": stats["total_tasks"] - stats["overdue"] - stats["completed"], "low": 0},
            "tasksByStatus": {"todo": stats["total_tasks"] - stats["in_progress"] - stats["completed"], "in_progress": stats["in_progress"], "done": stats["completed"]},
            "completionRate": round((stats["completed"] / stats["total_tasks"] * 100)) if stats["total_tasks"] > 0 else 0,
            "avgConfidence": 0,
            "totalMeetings": stats["total_meetings"],
            "totalParticipants": stats["total_participants"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics unavailable: {e}")


@app.get("/integrations/status")
async def get_integrations_status():
    """Return connection status for all integrations."""

    # Google Calendar
    google_status = "not_configured"
    google_detail = "Service account JSON not found. Set GOOGLE_SERVICE_ACCOUNT env var."
    try:
        from .calendar_service import CalendarService
        cal = CalendarService()
        if cal.connected:
            google_status = "connected"
            google_detail = "Google Calendar API connected via service account."
        else:
            google_status = "error"
            google_detail = "Credentials found but connection failed. Check your service account JSON."
    except Exception:
        pass

    # Microsoft Teams
    teams_status = "not_configured"
    teams_detail = "Azure AD credentials not set. Configure MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT_ID."
    if os.getenv("TEAMS_TOKEN") or (os.getenv("MS_CLIENT_ID") and os.getenv("MS_CLIENT_SECRET") and os.getenv("MS_TENANT_ID")):
        try:
            from .teams_service import TeamsService
            teams = TeamsService()
            teams_status = "connected"
            teams_detail = "Microsoft Teams (Graph API) connected."
        except Exception as e:
            teams_status = "error"
            teams_detail = f"Teams connection failed: {e}"

    # SharePoint
    sharepoint_status = "not_configured"
    sharepoint_detail = "Azure AD credentials not set. Configure MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT_ID."
    if os.getenv("MS_CLIENT_ID") and os.getenv("MS_CLIENT_SECRET") and os.getenv("MS_TENANT_ID"):
        sharepoint_status = "connected"
        sharepoint_detail = "SharePoint (Graph API) connected."

    return {
        "google_calendar": {"status": google_status, "detail": google_detail},
        "microsoft_teams": {"status": teams_status, "detail": teams_detail},
        "sharepoint": {"status": sharepoint_status, "detail": sharepoint_detail},
    }


@app.get("/insights")
async def get_insights():
    """Return cached cross-meeting AI insights."""
    try:
        from .insights_service import CrossMeetingAnalyzer
        analyzer = CrossMeetingAnalyzer()
        return analyzer.get_or_refresh(force=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insights unavailable: {e}")


@app.post("/insights/refresh")
async def refresh_insights():
    """Force regeneration of cross-meeting AI insights."""
    try:
        from .insights_service import CrossMeetingAnalyzer
        analyzer = CrossMeetingAnalyzer()
        return analyzer.get_or_refresh(force=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insights refresh failed: {e}")


@app.get("/notifications")
async def get_notifications(unread_only: bool = False):
    from .notification_service import get_all
    return get_all(unread_only=unread_only)


@app.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    from .notification_service import mark_read
    if not mark_read(notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"id": notification_id, "read": True}


@app.get("/autonomous/status")
async def autonomous_status():
    from .scheduler import get_status
    return get_status()


@app.post("/autonomous/toggle")
async def autonomous_toggle():
    from .scheduler import get_status, start, stop
    current = get_status()
    if current["running"]:
        stop()
        return {"running": False, "message": "Autonomous mode stopped"}
    else:
        started = start()
        return {"running": started, "message": "Autonomous mode started" if started else "Set ENABLE_AUTONOMOUS=true to enable"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
