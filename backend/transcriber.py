import os
import time
from typing import Optional, List

# Global caches to avoid reloading models
_CACHED_HF_TRANSCRIBER = None
_CACHED_GROQ_TRANSCRIBER = None

class HFLocalTranscriber:
    """Local Whisper transcription using transformers pipeline (Whisper Large v3 Turbo).
    Heavy imports (torch, transformers) are lazy to keep the Docker image lightweight
    when using Groq as the transcription backend."""

    def __init__(self, model_id: str = "openai/whisper-large-v3-turbo"):
        import torch
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

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

class AdaptiveTranscriber:
    """Starts with local HF Whisper, times each chunk, and auto-switches to Groq if too slow."""

    def __init__(self, timeout_per_chunk: int = 120):
        """
        Args:
            timeout_per_chunk: Max seconds allowed per chunk before switching to Groq.
                               Default 120s (for a ~300s chunk that's ~0.4x realtime).
        """
        self.timeout_per_chunk = timeout_per_chunk
        self._hf: Optional[HFLocalTranscriber] = None
        self._groq: Optional[GroqTranscriber] = None
        self._using_groq = False
        self._chunk_times: list[float] = []

        # Attempt to init HF local first
        self._hf_device = "cpu"
        try:
            self._hf = HFLocalTranscriber()
            self._hf_device = self._hf.device
            if self._hf_device == "cpu":
                print("AdaptiveTranscriber: HF loaded on CPU — will be slow.")
            else:
                print("AdaptiveTranscriber: HF Local Whisper loaded on GPU, will monitor speed.")
        except Exception as e:
            print(f"AdaptiveTranscriber: HF Local init failed ({e}), falling back to Groq.")
            self._groq = GroqTranscriber()
            self._using_groq = True

        # Pre-init Groq as fallback if available
        if not self._using_groq and os.getenv("GROQ_API_KEY"):
            try:
                self._groq = GroqTranscriber()
                print("AdaptiveTranscriber: Groq ready as fallback.")
            except Exception:
                pass

        # On CPU, HF local Whisper is unusably slow for long audio — switch to Groq immediately
        if self._hf_device == "cpu" and self._groq and not self._using_groq:
            print("AdaptiveTranscriber: ⚡ Running on CPU. Switching to Groq immediately (~50x faster)!")
            self._using_groq = True
            self._hf = None  # Free memory

    def transcribe(self, audio_path: str) -> str:
        if self._using_groq and self._groq:
            return self._groq.transcribe(audio_path)

        # Time this HF chunk
        start = time.time()
        result = self._hf.transcribe(audio_path)
        elapsed = time.time() - start
        self._chunk_times.append(elapsed)

        avg_time = sum(self._chunk_times) / len(self._chunk_times)
        print(f"AdaptiveTranscriber: chunk took {elapsed:.1f}s (avg {avg_time:.1f}s, threshold {self.timeout_per_chunk}s)")

        if elapsed > self.timeout_per_chunk and self._groq:
            print(f"AdaptiveTranscriber: ⚡ Chunk too slow ({elapsed:.1f}s > {self.timeout_per_chunk}s). Switching to Groq for remaining chunks!")
            self._using_groq = True
        return result

    def parallel_transcribe(self, audio_paths: list[str], max_workers: int = 3) -> str:
        """Process first chunk singly to measure speed, then decide backend for rest."""
        if not audio_paths:
            return ""

        # Process first chunk to gauge speed
        first_result = self.transcribe(audio_paths[0])
        if len(audio_paths) == 1:
            return first_result

        remaining = audio_paths[1:]

        if self._using_groq and self._groq:
            print(f"AdaptiveTranscriber: Using Groq for remaining {len(remaining)} chunk(s).")
            rest_results = self._groq.parallel_transcribe(remaining, max_workers)
        else:
            print(f"AdaptiveTranscriber: HF fast enough, using HF for remaining {len(remaining)} chunk(s).")
            rest_results = self._hf.parallel_transcribe(remaining, max_workers)

        return first_result + "\n" + rest_results


def create_transcriber(prefer_groq: bool = False, time_based_switch: bool = False, timeout_per_chunk: int = 120):
    global _CACHED_HF_TRANSCRIBER, _CACHED_GROQ_TRANSCRIBER

    # 0. Adaptive time-based switching mode
    if time_based_switch:
        return AdaptiveTranscriber(timeout_per_chunk=timeout_per_chunk)

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
