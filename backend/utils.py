import os
import sys
import glob as glob_mod
import shutil


def _find_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found

    if sys.platform == "win32":
        base = os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Microsoft", "WinGet", "Packages",
            "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
        )
        if os.path.isdir(base):
            bins = glob_mod.glob(os.path.join(base, "ffmpeg-*", "bin", "ffmpeg.exe"))
            if bins:
                return bins[0]

    return "ffmpeg"


_FFMPEG_PATH = _find_ffmpeg()

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma", ".opus"}


def get_audio_path(video_path, audio_dir="audio"):
    """Extract audio from video, or return the path directly if already audio."""
    os.makedirs(audio_dir, exist_ok=True)
    ext = os.path.splitext(video_path)[1].lower()
    base_name = os.path.splitext(os.path.basename(video_path))[0]

    if ext in AUDIO_EXTENSIONS:
        print(f"File is already audio ({ext}), skipping extraction")
        return video_path

    audio_path = os.path.join(audio_dir, f"{base_name}.mp3")

    import moviepy.config as mpcfg

    if _FFMPEG_PATH != "ffmpeg":
        mpcfg.FFMPEG_BINARY = _FFMPEG_PATH

    from moviepy import VideoFileClip

    print(f"Extracting audio from {video_path}...")
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)
    video.close()
    print(f"Audio saved to {audio_path}")

def _find_ffmpeg() -> str:
    # First try WinGet location
    if sys.platform == "win32":
        base = os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Microsoft", "WinGet", "Packages",
            "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
        )
        if os.path.isdir(base):
            bins = glob_mod.glob(os.path.join(base, "ffmpeg-*", "bin", "ffmpeg.exe"))
            if bins:
                return bins[0]

    # Fallback to PATH
    found = shutil.which("ffmpeg")
    if found:
        return found

    return "ffmpeg"

_FFMPEG_PATH = _find_ffmpeg()

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma", ".opus"}

def split_audio_into_chunks(audio_path: str, chunk_dir: str = "audio_chunks", max_chunk_seconds: int = 600) -> list:
    """Split a long audio file into ~max_chunk_seconds pieces using ffmpeg.
    Returns a list of file paths to the created chunks.
    """
    os.makedirs(chunk_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    out_pattern = os.path.join(chunk_dir, f"{base_name}_%03d.mp3")
    import subprocess
    cmd = [
        _FFMPEG_PATH,
        "-i",
        audio_path,
        "-f",
        "segment",
        "-segment_time",
        str(max_chunk_seconds),
        "-c",
        "copy",
        out_pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg chunking failed: {result.stderr}")
    chunks = sorted([os.path.join(chunk_dir, f) for f in os.listdir(chunk_dir) if f.startswith(base_name) and f.endswith('.mp3')])
    return chunks

def get_audio_path(video_path: str, audio_dir: str = "audio") -> str:
    """Extract audio from video, or return the path directly if already audio."""
    os.makedirs(audio_dir, exist_ok=True)
    ext = os.path.splitext(video_path)[1].lower()
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    if ext in AUDIO_EXTENSIONS:
        return video_path
    audio_path = os.path.join(audio_dir, f"{base_name}.mp3")
    import moviepy.config as mpcfg
    if _FFMPEG_PATH != "ffmpeg":
        mpcfg.FFMPEG_BINARY = _FFMPEG_PATH
    from moviepy import VideoFileClip
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(
        audio_path,
        fps=16000,
        bitrate="64k",
        ffmpeg_params=["-ac", "1"],
    )
    video.close()
    return audio_path
