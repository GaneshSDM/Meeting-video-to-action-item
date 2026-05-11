import os
import re
import time
import requests
from typing import List, Optional
from urllib.parse import urlparse, unquote

import msal

from .models import ActionItem


class SharePointClient:
    """Microsoft Graph API client for SharePoint video download and export."""

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    SCOPES = ["https://graph.microsoft.com/.default"]

    def __init__(self):
        self.client_id = os.getenv("MS_CLIENT_ID")
        self.client_secret = os.getenv("MS_CLIENT_SECRET")
        self.tenant_id = os.getenv("MS_TENANT_ID")
        self._token = None

        if not all([self.client_id, self.client_secret, self.tenant_id]):
            raise ValueError(
                "MS_CLIENT_ID, MS_CLIENT_SECRET, and MS_TENANT_ID must be set "
                "for SharePoint integration"
            )

        self._app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
        )

    @property
    def token(self) -> str:
        if not self._token:
            result = self._app.acquire_token_silent(self.SCOPES, account=None)
            if not result:
                result = self._app.acquire_token_for_client(scopes=self.SCOPES)
            if "access_token" not in result:
                raise PermissionError(
                    f"Failed to acquire MS Graph token: {result.get('error_description', 'Unknown error')}"
                )
            self._token = result["access_token"]
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def parse_url(self, sharepoint_url: str) -> dict:
        """Parse a SharePoint URL into components for Graph API.

        Handles:
        - https://tenant.sharepoint.com/sites/site/Docs/folder/file.mp4
        - https://tenant.sharepoint.com/:v:/s/site/guid
        """
        parsed = urlparse(sharepoint_url)
        hostname = parsed.hostname or ""

        if "sharepoint.com" not in hostname:
            raise ValueError(f"Not a SharePoint URL: {sharepoint_url}")

        path = unquote(parsed.path)

        # Format: /sites/<site>/<drive>/<folder...>/<file>
        match = re.match(r"/sites/([^/]+)/(.*)", path)
        if match:
            site_name = match.group(1)
            rest = match.group(2)

            parts = rest.split("/")
            drive_name = parts[0] if parts else "Shared Documents"
            file_path = "/".join(parts[1:]) if len(parts) > 1 else ""
            file_name = parts[-1] if len(parts) > 1 else ""

            return {
                "hostname": hostname,
                "site_path": f"/sites/{site_name}",
                "site_name": site_name,
                "drive_name": drive_name,
                "item_path": rest,
                "file_name": file_name,
            }

        raise ValueError(f"Unsupported SharePoint URL format: {sharepoint_url}")

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.GRAPH_BASE}{path}"
        kwargs.setdefault("timeout", 60)
        for attempt in range(3):
            try:
                resp = requests.request(method, url, headers=self._headers(), **kwargs)
                if resp.status_code == 401:
                    self._token = None
                    resp = requests.request(
                        method, url, headers=self._headers(), **kwargs
                    )
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)

    def get_site_id(self, hostname: str, site_path: str) -> str:
        path = f"/sites/{hostname}:{site_path}"
        resp = self._request("GET", path)
        return resp.json()["id"]

    def download_file(self, sharepoint_url: str, output_dir: str) -> str:
        """Download a video file from SharePoint and save it locally.

        Returns the local file path.
        """
        info = self.parse_url(sharepoint_url)
        site_id = self.get_site_id(info["hostname"], info["site_path"])

        encoded_path = info["item_path"]
        download_url = (
            f"/sites/{site_id}/drive/root:/{encoded_path}:/content"
        )

        resp = self._request("GET", download_url, stream=True)
        os.makedirs(output_dir, exist_ok=True)

        local_path = os.path.join(output_dir, info["file_name"])

        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)

        return local_path

    def create_results_document(
        self,
        site_id: str,
        folder_path: str,
        filename: str,
        html_content: str,
    ) -> str:
        """Create an HTML document in SharePoint with meeting analysis results."""
        path = f"/sites/{site_id}/drive/root:/{folder_path}/{filename}:/content"
        resp = self._request("PUT", path, data=html_content.encode("utf-8"))
        return resp.json().get("webUrl", "")

    def export_to_list(
        self,
        site_id: str,
        list_id: str,
        action_items: List[ActionItem],
    ) -> list:
        """Create list items in SharePoint for each action item."""
        results = []
        for item in action_items:
            body = {
                "fields": {
                    "Title": item.task,
                    "Owner": item.owner,
                    "Deadline": item.deadline or "",
                    "Priority": item.priority,
                    "Confidence": item.confidence,
                }
            }
            resp = self._request(
                "POST", f"/sites/{site_id}/lists/{list_id}/items", json=body
            )
            results.append(resp.json())
        return results

    def build_results_html(self, analysis: dict) -> str:
        """Build a clean HTML report from analysis results."""
        items_html = ""
        for item in analysis.get("action_items", []):
            if hasattr(item, "model_dump"):
                item = item.model_dump()
            priority_color = {"high": "#ef4444", "medium": "#eab308", "low": "#6b7280"}
            items_html += f"""
            <tr>
              <td style="font-weight:600">{item.get('owner', '')}</td>
              <td>{item.get('task', '')}</td>
              <td>{item.get('deadline') or '-'}</td>
              <td style="color:{priority_color.get(item.get('priority', 'medium'), '#eab308')}">
                {item.get('priority', 'medium').upper()}
              </td>
              <td>{int(item.get('confidence', 0) * 100)}%</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Meeting Action Items Report</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1a1a2e; }}
  h1 {{ color: #0070f3; border-bottom: 2px solid #0070f3; padding-bottom: 8px; }}
  h2 {{ color: #333; margin-top: 24px; }}
  .summary {{ background: #f0f7ff; padding: 16px; border-radius: 8px; margin: 16px 0; }}
  .participants {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .participant {{ background: #e0e7ff; padding: 4px 12px; border-radius: 16px; font-size: 14px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
  th {{ background: #f8fafc; text-align: left; padding: 10px 12px; border-bottom: 2px solid #e2e8f0; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }}
  .footer {{ margin-top: 40px; color: #94a3b8; font-size: 12px; text-align: center; }}
</style></head><body>
<h1>Meeting Action Items Report</h1>
<div class="summary"><strong>Summary:</strong> {analysis.get('meeting_summary', '')}</div>
<h2>Participants</h2>
<div class="participants">
  {''.join(f'<span class="participant">{p}</span>' for p in analysis.get('participants', []))}
</div>
<h2>Action Items ({len(analysis.get('action_items', []))})</h2>
<table>
  <tr><th>Owner</th><th>Task</th><th>Deadline</th><th>Priority</th><th>Confidence</th></tr>
  {items_html}
</table>
<p class="footer">Generated by Decision Minds &bull; Meeting Intelligence Platform</p>
</body></html>"""
