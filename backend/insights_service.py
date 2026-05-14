import os
import json
from datetime import datetime, timezone
from groq import Groq


INSIGHTS_SYSTEM_PROMPT = """You are an expert organizational analyst. Analyze the provided meeting data and action items to extract cross-meeting insights.

For each category, provide actionable findings:

1. **recurring_topics**: Topics that appear across multiple meetings. Include frequency count and which meetings.
2. **bottlenecks**: Tasks or patterns that consistently cause delays — overdue items, tasks without deadlines, owners with many incomplete tasks.
3. **owner_workload**: Identify who is overloaded (many tasks, mostly high priority) and who has capacity.
4. **patterns**: Organizational patterns like "meetings with team X always generate high-priority tasks" or "Friday meetings have better follow-through."
5. **recommendations**: 2-3 specific, actionable recommendations for the team.

Return ONLY valid JSON:
{
  "recurring_topics": [{"topic": "...", "frequency": 3, "meetings": ["..."]}],
  "bottlenecks": [{"description": "...", "severity": "high|medium|low", "affected_items": 2}],
  "owner_workload": [{"owner": "...", "total_tasks": 5, "completed": 2, "high_priority": 3, "assessment": "overloaded|balanced|underutilized"}],
  "patterns": [{"pattern": "...", "confidence": "high|medium|low"}],
  "recommendations": ["...", "...", "..."]
}"""


class CrossMeetingAnalyzer:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")
        self.client = Groq(api_key=api_key)

    def _build_context(self) -> str:
        try:
            from .database import get_meetings, get_tasks
            meetings = get_meetings()
            tasks = get_tasks()
        except Exception:
            return ""

        if len(meetings) < 2:
            return ""

        lines = [f"=== MEETINGS ({len(meetings)}) ==="]
        for m in meetings:
            lines.append(f"\nTitle: {m.get('title', 'Untitled')}")
            lines.append(f"Date: {m.get('date', 'Unknown')}")
            lines.append(f"Team: {m.get('team', 'Unknown')}")
            lines.append(f"Summary: {m.get('summary', 'No summary')}")
            lines.append(f"Participants: {', '.join(m.get('participants', []))}")

        lines.append(f"\n=== ACTION ITEMS ({len(tasks)}) ===")
        for t in tasks:
            lines.append(f"\nTask: {t.get('title', '')}")
            lines.append(f"Owner: {t.get('owner', 'Unassigned')}")
            lines.append(f"Priority: {t.get('priority', 'Unknown')}")
            lines.append(f"Status: {t.get('status', 'todo')}")
            lines.append(f"Due: {t.get('due', 'None')}")
            lines.append(f"Meeting: {t.get('meeting', 'Unknown')}")

        return "\n".join(lines)

    def analyze(self, model: str = "llama-3.3-70b-versatile") -> dict:
        context = self._build_context()
        if not context:
            return {
                "recurring_topics": [],
                "bottlenecks": [],
                "owner_workload": [],
                "patterns": [],
                "recommendations": ["Process at least 2 meetings to unlock cross-meeting insights."],
                "_insufficient_data": True,
            }

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": INSIGHTS_SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze these meetings and action items:\n\n{context}"},
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        data["_generated_at"] = datetime.now(timezone.utc).isoformat()
        data["_insufficient_data"] = False
        return data

    def get_or_refresh(self, force: bool = False) -> dict:
        if not force:
            try:
                from .database import _get_conn
                conn = _get_conn()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT data FROM insights_cache ORDER BY generated_at DESC LIMIT 1"
                    )
                    row = cur.fetchone()
                    if row:
                        cached = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                        return cached
            except Exception:
                pass

        insights = self.analyze()

        try:
            from .database import _get_conn
            conn = _get_conn()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM insights_cache")
                cur.execute(
                    "INSERT INTO insights_cache (data, generated_at) VALUES (%s, NOW())",
                    (json.dumps(insights),),
                )
        except Exception:
            pass

        return insights
