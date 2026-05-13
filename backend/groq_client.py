import os
import json
from typing import List
from groq import Groq
from .models import ActionItem


class GroqTranscriber:
    """Ultra-fast transcription via Groq LPU (Whisper Large v3 Turbo). ~50x realtime."""

    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

    def __init__(self):
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

        workers = min(max_workers, len(audio_paths)) or 1
        results = [None] * len(audio_paths)

        def _transcribe_chunk(path: str) -> str:
            return self.transcribe(path)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_transcribe_chunk, path): idx
                for idx, path in enumerate(audio_paths)
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    raise RuntimeError(f"Chunk transcription failed: {e}")

        return "\n".join(results)


class GroqActionItemExtractor:
    """High-velocity structured action item extraction via Groq Llama 3.3 70B."""

    # In backend/groq_client.py, line 32 - update the SYSTEM_PROMPT
    SYSTEM_PROMPT = """You are an expert meeting analyst. Extract structured action items from the transcript.

For each action item, identify:
- owner: The person responsible (use exact name from transcript)
- task: Clear, specific action description
- deadline: Due date/time if mentioned (null if not specified)
- priority: "high" if urgent/blocking, "medium" if normal, "low" if nice-to-have or later
- confidence: Your certainty 0.0-1.0 based on how clearly it was stated
- context: The exact quote or sentences from the transcript supporting this item

Also provide:
- meeting_summary: 2-3 sentence summary with PROPER SPELLING and GRAMMAR
- participants: All person names mentioned

IMPORTANT: Review your meeting_summary for spelling accuracy before returning. Use spell-check carefully.
- meeting_summary: 2-3 sentence summary
- participants: List EVERY person name mentioned in the transcript, including meeting attendees, people referenced, and action item owners. Do not omit names even if they have no explicit task.

Return ONLY valid JSON:
{
  "meeting_summary": "...",
  "participants": ["Name1", "Name2"],
  "action_items": [
    {"owner": "Name", "task": "...", "deadline": "..." or null, "priority": "high|medium|low", "confidence": 0.95, "context": "..."}
  ]
}"""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")
        self.client = Groq(api_key=api_key)

    def extract_action_items(
        self, transcript: str, model: str = "llama-3.3-70b-versatile"
    ) -> List[ActionItem]:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"TRANSCRIPT:\n{transcript}"},
            ],
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        action_items = []
        for item in data.get("action_items", []):
            owner = item.get("owner") or "Unknown"
            task = item.get("task") or ""
            if not task:
                continue
            action_items.append(
                ActionItem(
                    owner=owner,
                    task=task,
                    deadline=item.get("deadline"),
                    priority=item.get("priority") or "medium",
                    confidence=item.get("confidence") if item.get("confidence") is not None else 0.5,
                    context=item.get("context"),
                )
            )

        return action_items

    def extract_full(
        self, transcript: str, model: str = "llama-3.3-70b-versatile"
    ) -> dict:
        """Returns full analysis including summary and participants."""
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"TRANSCRIPT:\n{transcript}"},
            ],
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        action_items = []
        for item in data.get("action_items", []):
            owner = item.get("owner") or "Unknown"
            task = item.get("task") or ""
            if not task:
                continue
            action_items.append(
                ActionItem(
                    owner=owner,
                    task=task,
                    deadline=item.get("deadline"),
                    priority=item.get("priority") or "medium",
                    confidence=item.get("confidence") if item.get("confidence") is not None else 0.5,
                    context=item.get("context"),
                )
            )

        return {
            "meeting_summary": data.get("meeting_summary", ""),
            "participants": data.get("participants", []),
            "action_items": action_items,
        }
