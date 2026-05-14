import os
import asyncio
import threading
import time
from datetime import datetime, timezone

from .notification_service import push

_running = False
_threads: list[threading.Thread] = []

WATCH_DIR = "watch"
os.makedirs(WATCH_DIR, exist_ok=True)


def _watch_folder_loop():
    """Auto-process new video files dropped into ./watch/ directory."""
    processed: set[str] = set()
    while _running:
        try:
            for name in os.listdir(WATCH_DIR):
                path = os.path.join(WATCH_DIR, name)
                if not os.path.isfile(path) or name in processed:
                    continue
                if name.lower().endswith((".mp4", ".mov", ".webm", ".mkv", ".avi")):
                    processed.add(name)
                    push(
                        "meeting_detected",
                        f"New video detected in watch folder: {name}",
                        {"file": name},
                    )
        except Exception:
            pass
        time.sleep(300)  # 5 minutes


def _calendar_sync_loop():
    """Periodically pull meeting recordings from connected calendars."""
    while _running:
        try:
            from .calendar_service import CalendarService
            cal = CalendarService()
            if cal.connected:
                now = datetime.now(timezone.utc).isoformat()
                events = cal.list_events(time_min=now)
                if events:
                    push(
                        "calendar_sync",
                        f"Calendar sync: {len(events)} upcoming events found",
                        {"count": len(events)},
                    )
        except Exception:
            pass
        time.sleep(900)  # 15 minutes


def _insights_refresh_loop():
    """Regenerate cross-meeting AI insights periodically."""
    while _running:
        time.sleep(21600)  # 6 hours
        try:
            from .insights_service import CrossMeetingAnalyzer
            analyzer = CrossMeetingAnalyzer()
            analyzer.get_or_refresh(force=True)
            push("insights_refreshed", "Cross-meeting AI insights regenerated")
        except Exception:
            pass


def _deadline_check_loop():
    """Daily check for overdue tasks at ~8am."""
    while _running:
        now = datetime.now()
        next_check = now.replace(hour=8, minute=3, second=0, microsecond=0)
        if now >= next_check:
            from datetime import timedelta
            next_check += timedelta(days=1)
        wait = (next_check - now).total_seconds()
        time.sleep(max(wait, 60))

        try:
            from .database import _get_conn
            conn = _get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM action_items WHERE priority = 'high' AND status != 'done'"
                )
                overdue = cur.fetchone()[0]
            if overdue > 0:
                push(
                    "overdue_tasks",
                    f"{overdue} high-priority tasks overdue or pending",
                    {"count": overdue},
                )
        except Exception:
            pass


def start() -> bool:
    global _running, _threads
    if _running:
        return False

    enable = os.getenv("ENABLE_AUTONOMOUS", "").lower() == "true"
    if not enable:
        return False

    _running = True

    jobs = [
        ("watch_folder", _watch_folder_loop),
        ("calendar_sync", _calendar_sync_loop),
        ("insights_refresh", _insights_refresh_loop),
        ("deadline_check", _deadline_check_loop),
    ]

    for name, target in jobs:
        t = threading.Thread(target=target, name=name, daemon=True)
        t.start()
        _threads.append(t)

    push("autonomous_started", "Autonomous mode activated")
    return True


def stop() -> bool:
    global _running, _threads
    if not _running:
        return False

    _running = False
    _threads.clear()
    push("autonomous_stopped", "Autonomous mode deactivated")
    return True


def get_status() -> dict:
    return {
        "running": _running,
        "enabled_env": os.getenv("ENABLE_AUTONOMOUS", "").lower() == "true",
        "jobs": [
            {"name": "Watch Folder (every 5 min)", "status": "active" if _running else "stopped"},
            {"name": "Calendar Sync (every 15 min)", "status": "active" if _running else "stopped"},
            {"name": "Insights Refresh (every 6 hours)", "status": "active" if _running else "stopped"},
            {"name": "Deadline Check (daily 8am)", "status": "active" if _running else "stopped"},
        ],
    }
