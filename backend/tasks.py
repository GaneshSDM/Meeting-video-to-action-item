import os
import asyncio
import uuid
import shutil
from typing import Dict
from .utils import extract_audio
from .transcriber import Transcriber
from .processor import ActionItemProcessor
from .crm_connector import CRMConnector

# Global job store and log store
jobs: Dict[str, dict] = {}
logs: Dict[str, list] = {}

async def run_pipeline(job_id: str, video_path: str):
    jobs[job_id]["status"] = "processing"
    logs[job_id] = []

    def log(msg):
        logs[job_id].append(msg)
        print(f"[{job_id}] {msg}")

    try:
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_dir = "audio"
        transcript_dir = "transcripts"
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(transcript_dir, exist_ok=True)

        audio_path = os.path.join(audio_dir, f"{base_name}.mp3")
        transcript_path = os.path.join(transcript_dir, f"{base_name}.txt")

        # 1. Extract Audio
        log("Extracting audio...")
        extract_audio(video_path, audio_path)
        jobs[job_id]["progress"] = 30

        # 2. Transcribe
        log("Loading Whisper model and transcribing...")
        # Note: In a real app, load model once at startup
        transcriber = Transcriber(model_name="base")
        transcript_text = transcriber.transcribe(audio_path)
        if not transcript_text:
            raise Exception("Transcription failed.")
        transcriber.save_transcript(transcript_text, transcript_path)
        jobs[job_id]["progress"] = 60

        # 3. Process Action Items
        log("Extracting action items with LLM...")
        processor = ActionItemProcessor()
        action_items = processor.process_transcript(transcript_text)
        jobs[job_id]["progress"] = 90

        # 4. Update CRM (Mock)
        log("Updating CRM...")
        crm = CRMConnector()
        crm.update_action_items(action_items)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["result"] = action_items
        log("Processing complete.")

    except Exception as e:
        log(f"Error: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
