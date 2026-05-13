import os
import torch
import time
from typing import Optional, List
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

# Global caches to avoid reloading models
_CACHED_HF_TRANSCRIBER = None
_CACHED_GROQ_TRANSCRIBER = None

class HFLocalTranscriber:
    """Local Whisper transcription using transformers pipeline (Whisper Large v3 Turbo)."""

    def __init__(self, model_id: str = "openai/whisper-large-v3-turbo"):
        print(f"Loading local Whisper model: {model_id}...")
        cuda_available = torch.cuda.is_available()
        self.device = "cuda:0" if cuda_available else "cpu"
        self.torch_dtype = torch.float16 if cuda_available else torch.float32
        
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id, 
            torch_dtype=self.torch_dtype, 
            low_cpu_mem_usage=True, 
            use_safetensors=True
        ).to(self.device)
        
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=self.model,
            tokenizer=self.processor.tokenizer,
            feature_extractor=self.processor.feature_extractor,
            chunk_length_s=30,
            batch_size=16,
            torch_dtype=self.torch_dtype,
            device=self.device,
            ignore_warning=True 
        )
        self.generate_kwargs = {"language": "english", "task": "transcribe"}

    def transcribe(self, audio_path: str) -> str:
        result = self.pipe(audio_path, generate_kwargs=self.generate_kwargs)
        return result["text"]

    def parallel_transcribe(self, audio_paths: list[str], max_workers: int = 3) -> str:
        results = self.pipe(audio_paths, batch_size=16, generate_kwargs=self.generate_kwargs)
        if isinstance(results, list):
            return "\n".join([r["text"] for r in results])
        return results["text"]

class GroqTranscriber:
    """Ultra-fast transcription via Groq LPU."""
    def __init__(self):
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")
        self.client = Groq(api_key=api_key)

    def transcribe(self, audio_path: str, model: str = "whisper-large-v3-turbo") -> str:
        with open(audio_path, "rb") as f:
            transcription = self.client.audio.transcriptions.create(
                model=model,
                file=(os.path.basename(audio_path), f.read()),
                response_format="verbose_json",
            )
        return transcription.text

    def parallel_transcribe(self, audio_paths: list[str], max_workers: int = 3) -> str:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = [None] * len(audio_paths)
        def _transcribe_chunk(path: str) -> str:
            return self.transcribe(path)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_transcribe_chunk, path): idx for idx, path in enumerate(audio_paths)}
            for future in as_completed(futures):
                idx = futures[future]
                results[idx] = future.result()
        return "\n".join(results)

def create_transcriber(prefer_groq: bool = False):
    global _CACHED_HF_TRANSCRIBER, _CACHED_GROQ_TRANSCRIBER
    
    # 1. If Groq is requested and available, use it (Fastest)
    if prefer_groq and os.getenv("GROQ_API_KEY"):
        if _CACHED_GROQ_TRANSCRIBER is None:
            try:
                _CACHED_GROQ_TRANSCRIBER = GroqTranscriber()
            except Exception as e:
                print(f"Groq init failed: {e}")
        if _CACHED_GROQ_TRANSCRIBER:
            return _CACHED_GROQ_TRANSCRIBER

    # 2. Use HF Local (Good quality, medium speed)
    if _CACHED_HF_TRANSCRIBER is None:
        try:
            _CACHED_HF_TRANSCRIBER = HFLocalTranscriber()
        except Exception as e:
            print(f"HF Local init failed: {e}")

    if _CACHED_HF_TRANSCRIBER:
        return _CACHED_HF_TRANSCRIBER

    # 3. Final fallback to basic whisper
    try:
        import whisper
        return type("FallbackTranscriber", (), {"transcribe": lambda self, p: whisper.load_model("base").transcribe(p)["text"], "__init__": lambda self: None})()
    except:
        raise RuntimeError("No transcription backend available.")
