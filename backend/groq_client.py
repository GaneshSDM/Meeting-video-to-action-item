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


class GroqActionItemExtractor:
    """High-velocity structured action item extraction via Groq Llama 3.3 70B."""

    SYSTEM_PROMPT = """You are an expert meeting analyst. Extract structured action items from the transcript.

For each action item, identify:
- owner: The person responsible (use exact name from transcript)
- task: Clear, specific action description
- deadline: Due date/time if mentioned (null if not specified)
- priority: "high" if urgent/blocking, "medium" if normal, "low" if nice-to-have or later
- confidence: Your certainty 0.0-1.0 based on how clearly it was stated
- context: The exact quote or sentences from the transcript supporting this item

Also provide:
- meeting_summary: 2-3 sentence summary
- participants: All person names mentioned

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
