import os
import json
from typing import Dict, Any, Optional
import requests


class TeamsService:
    """Simple wrapper for Microsoft Graph calendar operations using plain HTTP requests.
    Expected env vars:
      TEAMS_CLIENT_ID, TEAMS_TENANT_ID, TEAMS_CLIENT_SECRET (or TEAMS_TOKEN for a pre‑generated bearer token).
    """

    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self):
        self._token = os.getenv("TEAMS_TOKEN")
        if not self._token:
            # Accept both TEAMS_* and MS_* naming conventions
            client_id = os.getenv("TEAMS_CLIENT_ID") or os.getenv("MS_CLIENT_ID")
            tenant_id = os.getenv("TEAMS_TENANT_ID") or os.getenv("MS_TENANT_ID")
            client_secret = os.getenv("TEAMS_CLIENT_SECRET") or os.getenv("MS_CLIENT_SECRET")
            if all([client_id, tenant_id, client_secret]):
                self._token = self._fetch_token(client_id, tenant_id, client_secret)
            else:
                raise RuntimeError(
                    "Microsoft Teams credentials not configured in env vars. "
                    "Set TEAMS_TOKEN or TEAMS_CLIENT_ID/MS_CLIENT_ID + TEAMS_TENANT_ID/MS_TENANT_ID + TEAMS_CLIENT_SECRET/MS_CLIENT_SECRET."
                )
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        # Use the primary calendar of the signed‑in user
        self.calendar_id = "primary"

    def _fetch_token(self, client_id: str, tenant_id: str, client_secret: str) -> str:
        url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        resp = requests.post(url, data=data)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.BASE_URL}{path}"
        resp = requests.request(method, url, headers=self._headers, **kwargs)
        resp.raise_for_status()
        return resp

    # ---------- Event helpers ----------
    def _event_body(self, event: Dict[str, Any]) -> Dict[str, Any]:
        # Build Graph event payload from our generic dict (same shape as Google payload)
        body = {
            "subject": event.get("summary"),
            "body": {"contentType": "HTML", "content": event.get("description", "")},
            "start": {"dateTime": event["start"]["dateTime"], "timeZone": event["start"]["timeZone"]},
            "end": {"dateTime": event["end"]["dateTime"], "timeZone": event["end"]["timeZone"]},
        }
        if event.get("recurrence"):
            # Graph expects a recurrence object; we store RRULE string and forward as is for simplicity.
            body["recurrence"] = {
                "pattern": {"type": "daily"},
                "range": {
                    "type": "endDate",
                    "startDate": event["start"]["dateTime"][:10],
                    "endDate": event["end"]["dateTime"][:10],
                },
            }
        return body

    def create_event(self, event: Dict[str, Any]) -> str:
        payload = self._event_body(event)
        resp = self._request("POST", f"/me/calendars/{self.calendar_id}/events", json=payload)
        return resp.json().get("id")

    def update_event(self, event_id: str, updates: Dict[str, Any]) -> None:
        # updates should be in the same shape as create_event payload (partial)
        self._request("PATCH", f"/me/calendars/{self.calendar_id}/events/{event_id}", json=updates)

    def delete_event(self, event_id: str) -> None:
        self._request("DELETE", f"/me/calendars/{self.calendar_id}/events/{event_id}")

    def list_events(self, start: str, end: str) -> list:
        params = {"startDateTime": start, "endDateTime": end}
        resp = self._request("GET", f"/me/calendars/{self.calendar_id}/events", params=params)
        return resp.json().get("value", [])
