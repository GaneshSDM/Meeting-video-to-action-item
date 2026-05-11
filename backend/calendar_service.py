import os
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build

class CalendarService:
    """Simple wrapper around Google Calendar API. Stub methods for Teams can be added later."""

    def __init__(self):
        # Load service account credentials from env var
        cred_path = os.getenv("GOOGLE_SERVICE_ACCOUNT")
        if not cred_path or not os.path.isfile(cred_path):
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT env var must point to a valid service account JSON file")
        scopes = ["https://www.googleapis.com/auth/calendar"]
        credentials = service_account.Credentials.from_service_account_file(cred_path, scopes=scopes)
        self.service = build("calendar", "v3", credentials=credentials)
        # Use a default calendar (primary)
        self.calendar_id = "primary"

    # ---------- Google Calendar methods ----------
    def create_event(self, event_body: Dict[str, Any], recurrence: Optional[str] = None) -> str:
        """Create an event and return its Google event ID. If recurrence is provided, add RRULE."""
        if recurrence:
            event_body.setdefault("recurrence", []).append(recurrence)
        created = self.service.events().insert(calendarId=self.calendar_id, body=event_body).execute()
        return created.get("id")

    def update_event(self, event_id: str, updates: Dict[str, Any]) -> None:
        """Patch an existing event with the provided fields."""
        self.service.events().patch(calendarId=self.calendar_id, eventId=event_id, body=updates).execute()

    def delete_event(self, event_id: str) -> None:
        """Delete the event identified by event_id."""
        self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()

    def list_events(self, time_min: str = None, time_max: str = None) -> List[Dict[str, Any]]:
        """Return a list of events in the given time window (ISO strings)."""
        params = {"calendarId": self.calendar_id, "singleEvents": True, "orderBy": "startTime"}
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        result = self.service.events().list(**params).execute()
        return result.get("items", [])

    # ---------- Teams stubs ----------
    def create_event_teams(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError("Teams integration not implemented yet")

    def update_event_teams(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError("Teams implementation not implemented yet")

    def delete_event_teams(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError("Teams integration not implemented too yet")
