import os
import json
import re
from typing import List, Dict, Any, Optional
from .models import ActionItem
from .hf_client import HFClient

class HFActionItemExtractor:
    """High-velocity structured action item extraction via HF Llama 3.3 70B."""

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
        self.client = HFClient()
        self.model_id = "unsloth/Llama-3.3-70B-Instruct-GGUF"

    def _parse_json(self, raw_text: str) -> Dict[str, Any]:
        try:
            match = re.search(r"\{[\s\S]*\}", raw_text)
            if match:
                return json.loads(match.group(0))
            return {}
        except (json.JSONDecodeError, KeyError):
            return {}

    def extract_action_items(self, transcript: str) -> List[ActionItem]:
        prompt = f"{self.SYSTEM_PROMPT}\n\nTRANSCRIPT:\n{transcript}"
        raw_text = self.client.chat_completion(prompt, model_id=self.model_id)
        data = self._parse_json(raw_text)

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

    def extract_full(self, transcript: str) -> Dict[str, Any]:
        """Returns full analysis including summary and participants."""
        prompt = f"{self.SYSTEM_PROMPT}\n\nTRANSCRIPT:\n{transcript}"
        raw_text = self.client.chat_completion(prompt, model_id=self.model_id)
        data = self._parse_json(raw_text)

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

class AdaptiveProcessor:
    """Tries HF first for action item extraction, auto-switches to Groq on failure."""

    def __init__(self):
        self._hf: Optional[HFActionItemExtractor] = None
        self._groq: Optional[Any] = None
        self._using_groq = False

        # Try initializing HF
        if os.getenv("HF_TOKEN"):
            try:
                self._hf = HFActionItemExtractor()
                print("AdaptiveProcessor: HF ready, will try first.")
            except Exception as e:
                print(f"AdaptiveProcessor: HF init failed ({e})")

        # Pre-init Groq as fallback
        if os.getenv("GROQ_API_KEY"):
            try:
                from .groq_client import GroqActionItemExtractor
                self._groq = GroqActionItemExtractor()
                print("AdaptiveProcessor: Groq ready as fallback.")
            except Exception:
                pass

        if not self._hf and not self._groq:
            raise RuntimeError("No processor available. Set HF_TOKEN or GROQ_API_KEY in .env")

    def extract_full(self, transcript: str) -> Dict[str, Any]:
        if self._using_groq and self._groq:
            return self._groq.extract_full(transcript)

        try:
            return self._hf.extract_full(transcript)
        except Exception as e:
            print(f"AdaptiveProcessor: ⚡ HF failed ({e}). Switching to Groq!")
            if self._groq:
                self._using_groq = True
                return self._groq.extract_full(transcript)
            raise

    def extract_action_items(self, transcript: str) -> List[ActionItem]:
        if self._using_groq and self._groq:
            return self._groq.extract_action_items(transcript)

        try:
            return self._hf.extract_action_items(transcript)
        except Exception as e:
            print(f"AdaptiveProcessor: ⚡ HF failed ({e}). Switching to Groq!")
            if self._groq:
                self._using_groq = True
                return self._groq.extract_action_items(transcript)
            raise


def create_processor(prefer_groq: bool = False, adaptive_switch: bool = True):
    """Factory: returns AdaptiveProcessor (with HF→Groq fallback) or specific backend."""
    if adaptive_switch:
        return AdaptiveProcessor()
    if prefer_groq and os.getenv("GROQ_API_KEY"):
        from .groq_client import GroqActionItemExtractor
        return GroqActionItemExtractor()
    if os.getenv("HF_TOKEN"):
        return HFActionItemExtractor()
    raise RuntimeError("No suitable LLM processor available. Set HF_TOKEN or GROQ_API_KEY in .env")
