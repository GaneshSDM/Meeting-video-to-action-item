import json
import os
from typing import List, Optional
from .models import ActionItem, AnalysisOutput
from .calendar_service import CalendarService

class CRMConnector:
    """CRM integration - logs to a local file and optionally syncs to Google Calendar and Microsoft Teams."""

    def __init__(self, crm_type: str = "Generic"):
        self.crm_type = crm_type
        self._calendar_service = None
        self._teams_service = None

    def update_action_items(self, analysis: AnalysisOutput) -> bool:
        """Create calendar events for each action item and log locally."""
        log_path = "action_items_log.jsonl"
        for item in analysis.action_items:
            self._create_event(item)
        entry = analysis.model_dump()
        entry["crm_type"] = self.crm_type
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        print(f"Action items logged to {log_path}")
        return True

    @property
    def calendar(self) -> CalendarService:
        if self._calendar_service is None:
            self._calendar_service = CalendarService()
        return self._calendar_service

    @property
    def teams(self) -> Optional[object]:
        if self._teams_service is None:
            try:
                from .teams_service import TeamsService
                self._teams_service = TeamsService()
            except RuntimeError:
                self._teams_service = None
            except Exception as e:
                print(f"TeamsService init failed: {e}")
                self._teams_service = None
        return self._teams_service

    def _create_event(self, item: ActionItem) -> None:
        """Create calendar events for an ActionItem."""
        event_body = {
            "summary": item.task,
            "description": "",
            "start": {"dateTime": "2026-01-01T09:00:00Z", "timeZone": "UTC"},
            "end": {"dateTime": "2026-01-01T10:00:00Z", "timeZone": "UTC"},
        }
        try:
            cred_path = os.getenv("GOOGLE_SERVICE_ACCOUNT")
            if cred_path and os.path.isfile(cred_path):
                ev_id = self.calendar.create_event(event_body, recurrence=item.recurrence)
                item.event_id = ev_id
        except Exception as e:
            print(f"Google event creation skipped/failed for '{item.task}': {e}")
        
        if self.teams:
            try:
                teams_ev_id = self.teams.create_event(event_body)
                item.teams_event_id = teams_ev_id
            except Exception as e:
                print(f"Teams event creation failed for '{item.task}': {e}")

    def export_results(
        self,
        analysis: AnalysisOutput,
        target: str = "local_log",
        sharepoint_url: Optional[str] = None,
    ) -> dict:
        """Export results to the chosen target (local log or SharePoint)."""
        if target == "local_log":
            self.update_action_items(analysis)
            return {"status": "ok", "target": "local_log"}
        
        if target in ("sharepoint_list", "sharepoint_document"):
            if not sharepoint_url:
                return {"status": "error", "detail": "sharepoint_url required for SharePoint export"}
            try:
                from .sharepoint import SharePointClient
                sp = SharePointClient()
                info = sp.parse_url(sharepoint_url)
                site_id = sp.get_site_id(info["hostname"], info["site_path"])
                if target == "sharepoint_document":
                    html = sp.build_results_html(analysis.model_dump())
                    web_url = sp.create_results_document(
                        site_id,
                        info["drive_name"],
                        f"Meeting_Action_Items_{analysis.model_dump().get('meeting_summary', '')[:30]}.html",
                        html,
                    )
                    return {"status": "ok", "target": "sharepoint_document", "url": web_url}
                if target == "sharepoint_list":
                    items = sp.export_to_list(
                        site_id,
                        "Meeting Action Items",
                        analysis.action_items,
                    )
                    return {"status": "ok", "target": "sharepoint_list", "count": len(items)}
            except Exception as e:
                return {"status": "error", "detail": str(e)}
        return {"status": "error", "detail": f"Unknown target: {target}"}
