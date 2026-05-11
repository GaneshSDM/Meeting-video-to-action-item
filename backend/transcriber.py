import os
from typing import Optional


class WhisperLocalTranscriber:
    """Local Whisper transcription (fallback when Groq unavailable)."""

    def __init__(self, model_name: str = "base"):
        import whisper

        print(f"Loading Whisper model: {model_name}...")
        self.model = whisper.load_model(model_name)

    def transcribe(self, audio_path: str) -> str:
        print(f"Transcribing {audio_path} locally...")
        result = self.model.transcribe(audio_path)
        return result["text"]


def create_transcriber(prefer_groq: bool = True):
    """Factory: returns GroqTranscriber if available, else local Whisper."""
    if prefer_groq and os.getenv("GROQ_API_KEY"):
        try:
            from .groq_client import GroqTranscriber

            print("Using Groq LPU for ultra-fast transcription")
            return GroqTranscriber()
        except Exception as e:
            print(f"Groq init failed ({e}), falling back to local Whisper")

    print("Using local Whisper for transcription")
    try:
        return WhisperLocalTranscriber(model_name="base")
    except ImportError:
        raise RuntimeError(
            "No transcription backend available. "
            "Set GROQ_API_KEY in .env, or install openai-whisper + torch."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to initialize local Whisper: {e}")
