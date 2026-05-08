import os
import uuid
import asyncio
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from .models import JobStatus
from .tasks import run_pipeline, jobs, logs

app = FastAPI(title="Decision Minds - Meeting AI")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload", response_model=JobStatus)
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")

    # Use a chunked write for safety
    with open(file_path, "wb") as buffer:
        while content := await file.read(1024 * 1024):  # 1MB chunks
            buffer.write(content)

    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "result": None,
        "error": None
    }

    background_tasks.add_task(run_pipeline, job_id, file_path)
    return jobs[job_id]

@app.get("/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

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

            if job_id in jobs and jobs[job_id]["status"] in ["completed", "failed"]:
                # Send final logs if any
                yield "data: [DONE]\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
