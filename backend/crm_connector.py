import json
from typing import List, Optional
from .models import ActionItem, AnalysisOutput


class CRMConnector:
    """CRM integration — local logging + optional SharePoint export."""

    def __init__(self, crm_type: str = "Generic"):
        self.crm_type = crm_type

    def update_action_items(self, analysis: AnalysisOutput) -> bool:
        """Log structured action items locally."""
        log_path = "action_items_log.jsonl"
        entry = analysis.model_dump()
        entry["crm_type"] = self.crm_type

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

        print(f"Action items logged to {log_path}")
        return True

    def export_results(
        self,
        analysis: AnalysisOutput,
        target: str = "local_log",
        sharepoint_url: Optional[str] = None,
    ) -> dict:
        """Export results to the chosen target."""
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
