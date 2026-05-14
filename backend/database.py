import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection

_conn: PgConnection | None = None


def _get_conn() -> PgConnection:
    global _conn
    if _conn is None or _conn.closed:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL environment variable not set")
        _conn = psycopg2.connect(url)
        _conn.autocommit = True
    return _conn


def init_db() -> None:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                title TEXT,
                team TEXT DEFAULT 'dev-team-001',
                source TEXT DEFAULT 'Upload',
                transcript TEXT,
                meeting_summary TEXT,
                participants JSONB DEFAULT '[]',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                status TEXT DEFAULT 'completed'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS action_items (
                id TEXT PRIMARY KEY,
                meeting_id TEXT REFERENCES meetings(id) ON DELETE CASCADE,
                owner TEXT,
                task TEXT NOT NULL,
                deadline TEXT,
                priority TEXT DEFAULT 'medium',
                confidence FLOAT DEFAULT 0.5,
                context TEXT,
                status TEXT DEFAULT 'todo',
                event_id TEXT,
                teams_event_id TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS insights_cache (
                id SERIAL PRIMARY KEY,
                data JSONB NOT NULL,
                generated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)


def _make_task_id(task_title: str, meeting_id: str, owner: str | None) -> str:
    raw = f"{task_title}|{meeting_id}|{owner or 'unassigned'}"
    return str(abs(hash(raw)) % 10_000_000).zfill(7)


def save_meeting(job_id: str, title: str, team: str, source: str,
                 transcript: str | None, meeting_summary: str | None,
                 participants: list[str], action_items: list[dict]) -> None:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO meetings (id, title, team, source, transcript, meeting_summary, participants, created_at, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), 'completed')
               ON CONFLICT (id) DO UPDATE SET
                 title=EXCLUDED.title, transcript=EXCLUDED.transcript,
                 meeting_summary=EXCLUDED.meeting_summary, participants=EXCLUDED.participants""",
            (job_id, title[:250], team, source, transcript, meeting_summary, json.dumps(participants))
        )
        for item in action_items:
            owner = item.get("owner", "Unknown")
            task_owner = owner if owner != "Unknown" else None
            task_id = item.get("id") or _make_task_id(item.get("task", ""), job_id, task_owner)
            cur.execute(
                """INSERT INTO action_items (id, meeting_id, owner, task, deadline, priority, confidence, context, status, event_id, teams_event_id, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'todo', %s, %s, NOW())
                   ON CONFLICT (id) DO UPDATE SET
                     owner=EXCLUDED.owner, task=EXCLUDED.task, deadline=EXCLUDED.deadline,
                     priority=EXCLUDED.priority, confidence=EXCLUDED.confidence, context=EXCLUDED.context""",
                (task_id, job_id, task_owner, item.get("task", ""), item.get("deadline"),
                 item.get("priority", "medium"), item.get("confidence", 0.5), item.get("context", ""),
                 item.get("event_id"), item.get("teams_event_id"))
            )


def get_meetings() -> list[dict[str, Any]]:
    conn = _get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT m.*, COUNT(ai.id) FILTER (WHERE ai.id IS NOT NULL) as tasks
            FROM meetings m
            LEFT JOIN action_items ai ON ai.meeting_id = m.id
            GROUP BY m.id
            ORDER BY m.created_at DESC
        """)
        rows = cur.fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        participants = row.get("participants")
        if isinstance(participants, str):
            participants = json.loads(participants)
        result.append({
            "job_id": row["id"],
            "title": row.get("title") or "Untitled"[:120],
            "team": row.get("team", "dev-team-001"),
            "source": row.get("source", "Transcript"),
            "tasks": row.get("tasks", 0),
            "status": (row.get("status") or "completed").capitalize(),
            "date": row.get("created_at", datetime.now(timezone.utc)).strftime("%b %d") if row.get("created_at") else "Unknown",
            "participants": participants or [],
            "summary": row.get("meeting_summary") or "",
        })
    return result


def get_tasks() -> list[dict[str, Any]]:
    conn = _get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT ai.*, m.title as meeting_title
            FROM action_items ai
            JOIN meetings m ON m.id = ai.meeting_id
            ORDER BY ai.created_at DESC
        """)
        rows = cur.fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        owner = row.get("owner") or "Unknown"
        initials = "".join([p[0] for p in owner.split()[:2]]).upper() if owner != "Unknown" else None
        result.append({
            "id": row["id"],
            "title": row["task"],
            "meeting": (row.get("meeting_title") or "Untitled")[:80],
            "owner": owner if owner != "Unknown" else None,
            "initials": initials,
            "due": row.get("deadline"),
            "priority": (row.get("priority") or "medium").capitalize(),
            "confidence": row.get("confidence", 0.5),
            "context": row.get("context") or "",
            "status": row.get("status", "todo"),
        })
    return result


def update_task_status(task_id: str, new_status: str) -> None:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE action_items SET status = %s WHERE id = %s",
            (new_status, task_id)
        )


def get_dashboard_stats() -> dict[str, Any]:
    conn = _get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM meetings WHERE status != 'failed'")
        total_meetings = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM action_items")
        total_tasks = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM action_items WHERE status = 'progress'")
        in_progress = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM action_items WHERE status = 'done'")
        completed = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM action_items WHERE priority = 'high' AND status != 'done'")
        overdue = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(DISTINCT owner) as cnt FROM action_items WHERE owner IS NOT NULL AND owner != 'Unknown'")
        total_owners = cur.fetchone()["cnt"]

        cur.execute("SELECT owner, COUNT(*) as cnt FROM action_items WHERE owner IS NOT NULL AND owner != 'Unknown' GROUP BY owner ORDER BY cnt DESC")
        owner_stats = [{"owner": r["owner"], "total": r["cnt"]} for r in cur.fetchall()]

        cur.execute("SELECT AVG(confidence) as avg FROM action_items")
        avg_confidence = cur.fetchone()["avg"] or 0

        cur.execute("SELECT m.title, m.created_at, COUNT(ai.id) as tasks FROM meetings m LEFT JOIN action_items ai ON ai.meeting_id = m.id WHERE m.status != 'failed' GROUP BY m.id ORDER BY m.created_at DESC LIMIT 5")
        recent = [{"title": (r["title"] or "Untitled")[:80], "date": r["created_at"].strftime("%b %d") if r["created_at"] else "Unknown", "tasks": r["tasks"]} for r in cur.fetchall()]

    return {
        "total_tasks": total_tasks,
        "in_progress": in_progress,
        "completed": completed,
        "overdue": overdue,
        "total_meetings": total_meetings,
        "total_participants": total_owners,
        "recent_meetings": recent,
        "activity": [
            {"title": f"{total_tasks} total action items extracted", "time": "across all meetings"},
            {"title": f"{total_meetings} meetings processed", "time": "from video recordings"},
            {"title": f"{total_owners} unique participants", "time": "identified across meetings"},
        ],
    }


def get_analytics_timeseries() -> dict[str, Any]:
    conn = _get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as created, COUNT(*) FILTER (WHERE status = 'done') as completed
            FROM action_items
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """)
        daily = [{"date": str(r["date"]), "created": r["created"], "completed": r["completed"]} for r in cur.fetchall()]

        cur.execute("SELECT priority, COUNT(*) as cnt FROM action_items GROUP BY priority")
        priority_dist = [{"name": r["priority"].capitalize(), "value": r["cnt"]} for r in cur.fetchall()]

        cur.execute("""
            SELECT owner, COUNT(*) as tasks, COUNT(*) FILTER (WHERE status = 'done') as completed
            FROM action_items WHERE owner IS NOT NULL AND owner != 'Unknown'
            GROUP BY owner ORDER BY tasks DESC LIMIT 10
        """)
        owner_workload = [{"owner": r["owner"], "tasks": r["tasks"], "completed": r["completed"]} for r in cur.fetchall()]

        cur.execute("""
            SELECT DATE_TRUNC('week', created_at) as week, COUNT(*) as cnt
            FROM meetings WHERE status != 'failed'
            GROUP BY week ORDER BY week DESC LIMIT 12
        """)
        meeting_freq = [{"week": str(r["week"])[:10], "count": r["cnt"]} for r in cur.fetchall()]

        cur.execute("""
            SELECT CASE
              WHEN confidence >= 0.8 THEN '80-100%'
              WHEN confidence >= 0.6 THEN '60-80%'
              WHEN confidence >= 0.4 THEN '40-60%'
              WHEN confidence >= 0.2 THEN '20-40%'
              ELSE '0-20%'
            END as range, COUNT(*) as cnt
            FROM action_items GROUP BY range ORDER BY range
        """)
        confidence_dist = [{"range": r["range"], "count": r["cnt"]} for r in cur.fetchall()]

    return {
        "dailyTasks": daily,
        "priorityDistribution": priority_dist,
        "ownerWorkload": owner_workload,
        "meetingFrequency": meeting_freq,
        "confidenceDistribution": confidence_dist,
    }
