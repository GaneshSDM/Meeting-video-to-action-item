import os
import sys
import re
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

# Ensure ffmpeg is on PATH (needed by whisper + moviepy)
from .utils import _FFMPEG_PATH

_ffmpeg_dir = os.path.dirname(_FFMPEG_PATH)
if _ffmpeg_dir and _ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

from .utils import get_audio_path, split_audio_into_chunks
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


def _extract_names(text: str) -> List[str]:
    """Lightweight heuristic to pull likely person names from transcript text."""
    exclude = {
        "I", "The", "We", "It", "This", "That", "They", "He", "She", "You",
        "A", "An", "And", "But", "Or", "So", "If", "In", "On", "At", "To",
        "For", "With", "As", "Is", "Are", "Was", "Were", "Be", "Been",
        "Have", "Has", "Had", "Do", "Does", "Did", "Will", "Would", "Could",
        "Should", "Can", "May", "Might", "Must", "Shall", "Monday", "Tuesday",
        "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "January",
        "February", "March", "April", "May", "June", "July", "August",
        "September", "October", "November", "December", "Today", "Tomorrow",
        "Yesterday", "Next", "Last", "Morning", "Afternoon", "Evening",
        "Thanks", "Thank", "Please", "Ok", "Okay", "Yes", "No", "Not",
        "Great", "Good", "Well", "Just", "Only", "Also", "Then", "Now",
        "Here", "There", "Where", "When", "What", "How", "Why", "Who",
        "All", "Any", "Both", "Each", "Few", "More", "Most", "Other",
        "Some", "Such", "No", "Nor", "Not", "Only", "Own", "Same", "So",
        "Than", "Too", "Very", "Just", "But", "Don", "Should", "Now",
        "Mr", "Mrs", "Ms", "Dr", "Prof", "Sir", "Madam",
    }
    candidates = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", text)
    names = []
    for candidate in candidates:
        parts = candidate.split()
        if all(p not in exclude for p in parts):
            names.append(candidate)
    seen = set()
    unique = []
    for n in names:
        if n.lower() not in seen:
            seen.add(n.lower())
            unique.append(n)
    return unique


def _process_audio(job_id: str, audio_path: str, progress_base: int = 60) -> AnalysisOutput:
    """Transcribe (with optional chunking) and extract action items. Returns AnalysisOutput."""
    import os
    from .utils import split_audio_into_chunks, get_audio_path
    max_chunk_seconds = 300 
    audio_files = [audio_path]
    if os.path.getsize(audio_path) > 20 * 1024 * 1024:
        audio_files = split_audio_into_chunks(audio_path, max_chunk_seconds=max_chunk_seconds)
        _log(job_id, f"Split audio into {len(audio_files)} chunks for processing.")
    
    _log(job_id, "Transcribing audio...")
    transcriber = create_transcriber(prefer_groq=True)
    _log(job_id, f"Using transcription backend: {type(transcriber).__name__}")
    transcript_text = ""
    if hasattr(transcriber, "parallel_transcribe"):
        _log(job_id, "Transcribing chunks in parallel...")
        transcript_text = transcriber.parallel_transcribe(audio_files, max_workers=3)
    else:
        for idx, chunk in enumerate(audio_files, 1):
            _log(job_id, f"Transcribing chunk {idx}/{len(audio_files)}")
            chunk_text = transcriber.transcribe(chunk)
            transcript_text += chunk_text + "\n"
    
    if not transcript_text:
        raise Exception("Transcription returned empty text.")
    
    transcript_dir = "transcripts"
    os.makedirs(transcript_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    transcript_path = os.path.join(transcript_dir, f"{base_name}.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript_text)
    
    jobs[job_id]["progress"] = progress_base
    
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
    
    if not participants and action_items:
        participants = list({item.owner for item in action_items if item.owner and item.owner != "Unknown"})
    if not participants:
        participants = _extract_names(transcript_text)
        
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
        _log(job_id, "Preparing audio from video...")
        audio_path = get_audio_path(video_path, "audio")
        jobs[job_id]["progress"] = 30

        analysis = _process_audio(job_id, audio_path, progress_base=60)
        jobs[job_id]["progress"] = 90

        _log(job_id, "Saving results...")
        crm = CRMConnector()
        crm.update_action_items(analysis)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["result"] = analysis
        _log(
            job_id,
            f"Done. {len(analysis.action_items)} action items for {len(analysis.participants)} participants.",
        )

    except Exception as e:
        _log(job_id, f"Error: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


async def run_sharepoint_pipeline(job_id: str, sharepoint_url: str):
    jobs[job_id]["status"] = "processing"
    logs[job_id] = []

    try:
        _log(job_id, "Downloading video from SharePoint...")
        from .sharepoint import SharePointClient

        sp = SharePointClient()
        video_path = sp.download_file(sharepoint_url, "videos")
        _log(job_id, f"Downloaded: {os.path.basename(video_path)}")
        jobs[job_id]["progress"] = 20

        _log(job_id, "Preparing audio...")
        audio_path = get_audio_path(video_path, "audio")
        jobs[job_id]["progress"] = 40

        analysis = _process_audio(job_id, audio_path, progress_base=65)
        jobs[job_id]["progress"] = 90

        _log(job_id, "Saving results...")
        crm = CRMConnector()
        crm.update_action_items(analysis)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["result"] = analysis
        _log(
            job_id,
            f"Done. {len(analysis.action_items)} action items for {len(analysis.participants)} participants.",
        )

    except Exception as e:
        _log(job_id, f"Error: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
