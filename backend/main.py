import os
import uuid
import shutil
import asyncio
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

    from fastapi.responses import Response

    json_str = result.model_dump_json(indent=2)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="action_items_{job_id[:8]}.json"'
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
async def export_results(job_id: str, body: ExportRequest):
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


# Two‑way sync endpoints

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
    # Prepare updates for Google Calendar
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
            # Update Teams if this item has a Teams event ID
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
    # Delete Teams event if it existed
    if team_event_id:
        try:
            teams = TeamsService()
            teams.delete_event(team_event_id)
        except Exception as te:
            raise HTTPException(status_code=500, detail=f"Teams delete failed: {te}")
    analysis.action_items = new_items
    # Log deletion for audit
    log_path = "action_items_log.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"job_id": job_id, "deleted_event": event_id}, default=str) + "\n")
    return {"status": "deleted", "event_id": event_id}


    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
