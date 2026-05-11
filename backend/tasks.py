import os
import sys
from typing import Dict

from dotenv import load_dotenv

load_dotenv()

# Ensure ffmpeg is on PATH (needed by whisper + moviepy)
from .utils import _FFMPEG_PATH

_ffmpeg_dir = os.path.dirname(_FFMPEG_PATH)
if _ffmpeg_dir and _ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

from .utils import get_audio_path
from .transcriber import create_transcriber
from .processor import create_processor
from .crm_connector import CRMConnector
from .models import AnalysisOutput

# Global job and log stores
jobs: Dict[str, dict] = {}
logs: Dict[str, list] = {}


def _log(job_id: str, msg: str):
    logs[job_id].append(msg)
    print(f"[{job_id}] {msg}")


def _process_audio(job_id: str, audio_path: str, progress_base: int = 60):
    """Shared transcription + action item extraction. Returns AnalysisOutput."""
    transcript_dir = "transcripts"
    os.makedirs(transcript_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    transcript_path = os.path.join(transcript_dir, f"{base_name}.txt")

    # Transcribe
    _log(job_id, "Transcribing audio...")
    transcriber = create_transcriber(prefer_groq=True)
    transcript_text = transcriber.transcribe(audio_path)
    if not transcript_text:
        raise Exception("Transcription returned empty text.")

    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript_text)
    jobs[job_id]["progress"] = progress_base

    # Extract action items
    _log(job_id, "Extracting per-person action items...")
    processor = create_processor(prefer_groq=True)

    if hasattr(processor, "extract_full"):
        data = processor.extract_full(transcript_text)
        action_items = data["action_items"]
        meeting_summary = data.get("meeting_summary", "")
        participants = data.get("participants", [])
    else:
        action_items = processor.extract_action_items(transcript_text)
        meeting_summary = ""
        participants = []

    jobs[job_id]["progress"] = progress_base + 30

    return AnalysisOutput(
        transcript=transcript_text,
        meeting_summary=meeting_summary,
        participants=participants,
        action_items=action_items,
    )


async def run_pipeline(job_id: str, video_path: str):
    jobs[job_id]["status"] = "processing"
    logs[job_id] = []

    try:
        # 1. Extract/get audio
        _log(job_id, "Preparing audio from video...")
        audio_path = get_audio_path(video_path, "audio")
        jobs[job_id]["progress"] = 30

        # 2. Transcribe + extract action items
        analysis = _process_audio(job_id, audio_path, progress_base=60)
        jobs[job_id]["progress"] = 90

        # 3. Save
        _log(job_id, "Saving results...")
        crm = CRMConnector()
        crm.update_action_items(analysis)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["result"] = analysis
        _log(
            job_id,
            f"Done. {len(analysis.action_items)} action items for "
            f"{len(analysis.participants)} participants.",
        )

    except Exception as e:
        _log(job_id, f"Error: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


async def run_sharepoint_pipeline(job_id: str, sharepoint_url: str):
    jobs[job_id]["status"] = "processing"
    logs[job_id] = []

    try:
        # 1. Download video from SharePoint
        _log(job_id, "Downloading video from SharePoint...")
        from .sharepoint import SharePointClient

        sp = SharePointClient()
        video_path = sp.download_file(sharepoint_url, "videos")
        _log(job_id, f"Downloaded: {os.path.basename(video_path)}")
        jobs[job_id]["progress"] = 20

        # 2. Extract/get audio
        _log(job_id, "Preparing audio...")
        audio_path = get_audio_path(video_path, "audio")
        jobs[job_id]["progress"] = 40

        # 3. Transcribe + extract action items
        analysis = _process_audio(job_id, audio_path, progress_base=65)
        jobs[job_id]["progress"] = 90

        # 4. Save
        _log(job_id, "Saving results...")
        crm = CRMConnector()
        crm.update_action_items(analysis)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["result"] = analysis
        _log(
            job_id,
            f"Done. {len(analysis.action_items)} action items for "
            f"{len(analysis.participants)} participants.",
        )

    except Exception as e:
        _log(job_id, f"Error: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
