from datetime import datetime, timezone
from typing import Any


_notifications: list[dict[str, Any]] = []


def push(event_type: str, message: str, metadata: dict[str, Any] | None = None) -> None:
    _notifications.append({
        "id": str(abs(hash(f"{event_type}:{message}:{datetime.now(timezone.utc).isoformat()}")) % 10_000_000).zfill(7),
        "type": event_type,
        "message": message,
        "metadata": metadata or {},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # Keep max 100 in memory
    if len(_notifications) > 100:
        _notifications.pop(0)


def get_all(unread_only: bool = False, limit: int = 50) -> list[dict[str, Any]]:
    items = [n for n in _notifications if not unread_only or not n["read"]]
    return sorted(items, key=lambda n: n["created_at"], reverse=True)[:limit]


def mark_read(notification_id: str) -> bool:
    for n in _notifications:
        if n["id"] == notification_id:
            n["read"] = True
            return True
    return False


def clear_all() -> None:
    _notifications.clear()
