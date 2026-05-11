import os
import json
import re
from typing import List
import requests
from .models import ActionItem


class HuggingFaceProcessor:
    """Action item extraction via HuggingFace Inference API (fallback)."""

    def __init__(self, model_id: str = "mistralai/Mistral-7B-Instruct-v0.2"):
        self.model_id = model_id
        self.api_url = f"https://api-inference.huggingface.co/models/{model_id}"
        self.headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}

    def extract_action_items(self, transcript: str) -> List[ActionItem]:
        prompt = f"""The following is a meeting transcript. Identify action items per person.

Return ONLY valid JSON:
{{
  "meeting_summary": "Brief summary",
  "participants": ["Name"],
  "action_items": [
    {{"owner": "Name", "task": "Task", "deadline": null, "priority": "medium", "confidence": 0.8, "context": "Quote"}}
  ]
}}

Transcript:
{transcript}"""

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 800,
                "temperature": 0.3,
                "return_full_text": False,
            },
        }

        print(f"Processing transcript with LLM ({self.model_id})...")
        response = requests.post(self.api_url, headers=self.headers, json=payload)
        response.raise_for_status()
        result = response.json()

        raw_text = ""
        if isinstance(result, list) and len(result) > 0:
            raw_text = result[0].get("generated_text", "").strip()

        return self._parse_json(raw_text)

    def _parse_json(self, raw_text: str) -> List[ActionItem]:
        try:
            match = re.search(r"\{[\s\S]*\}", raw_text)
            if match:
                data = json.loads(match.group(0))
            else:
                return []

            items = []
            for item in data.get("action_items", []):
                # If no owner is provided, treat the task as a general item
                owner = item.get("owner") or "General"
                task = item.get("task") or ""
                if not task:
                    continue
                items.append(
                    ActionItem(
                        owner=owner,
                        task=task,
                        deadline=item.get("deadline"),
                        priority=item.get("priority") or "medium",
                        confidence=item.get("confidence") if item.get("confidence") is not None else 0.5,
                        context=item.get("context"),
                    )
                )
            return items
        except (json.JSONDecodeError, KeyError):
            return []

    def process_transcript(self, transcript: str) -> str:
        """Legacy method: returns raw text. Kept for backward compat."""
        items = self.extract_action_items(transcript)
        if not items:
            return "No action items found."
        lines = []
        for item in items:
            deadline = f" (by {item.deadline})" if item.deadline else ""
            lines.append(
                f"- **{item.owner}**: {item.task}{deadline} [{item.priority}]"
            )
        return "\n".join(lines)


def create_processor(prefer_groq: bool = True):
    """Factory: returns GroqActionItemExtractor if available, else HuggingFace."""
    if prefer_groq and os.getenv("GROQ_API_KEY"):
        try:
            from .groq_client import GroqActionItemExtractor

            print("Using Groq Llama 3.3 70B for action item extraction")
            return GroqActionItemExtractor()
        except Exception as e:
            print(f"Groq init failed ({e}), falling back to HuggingFace")

    print("Using HuggingFace for action item extraction")
    return HuggingFaceProcessor()
