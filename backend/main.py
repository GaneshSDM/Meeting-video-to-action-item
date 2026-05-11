import os
import uuid
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

    with open(file_path, "wb") as buffer:
        while content := await file.read(1024 * 1024):
            buffer.write(content)

    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "result": None,
        "error": None,
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
