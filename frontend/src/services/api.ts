import type { AnalyticsSummary, AnalyticsTimeSeries, AppNotification, AutonomousStatus, CrossMeetingInsights, JobStatus, ExportRequest, MeetingInfo, TaskInfo, DashboardData } from "../types";

const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function fetchAnalyticsTimeSeries(): Promise<AnalyticsTimeSeries> {
  const res = await fetch(`${BASE}/analytics/timeseries`);
  if (!res.ok) throw new Error("Failed to fetch timeseries analytics");
  return res.json();
}

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  const res = await fetch(`${BASE}/analytics/summary`);
  if (!res.ok) throw new Error("Failed to fetch analytics summary");
  return res.json();
}

export async function fetchMeetings(): Promise<MeetingInfo[]> {
  const res = await fetch(`${BASE}/meetings`);
  if (!res.ok) throw new Error("Failed to fetch meetings");
  return res.json();
}

export async function fetchTasks(): Promise<TaskInfo[]> {
  const res = await fetch(`${BASE}/tasks`);
  if (!res.ok) throw new Error("Failed to fetch tasks");
  return res.json();
}

export async function fetchDashboard(): Promise<DashboardData> {
  const res = await fetch(`${BASE}/dashboard`);
  if (!res.ok) throw new Error("Failed to fetch dashboard");
  return res.json();
}

export async function uploadVideo(file: File): Promise<JobStatus> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    if (res.status === 413) {
      throw new Error("Upload is too large for the server proxy.");
    }
    throw new Error(`Upload failed with status ${res.status}`);
  }
  return res.json();
}

export async function analyzeSharePointUrl(
  sharepointUrl: string
): Promise<JobStatus> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sharepoint_url: sharepointUrl }),
  });
  if (!res.ok) throw new Error("Analysis request failed");
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/status/${jobId}`);
  if (!res.ok) throw new Error("Status check failed");
  return res.json();
}

export function createLogStream(jobId: string): EventSource {
  return new EventSource(`${BASE}/logs/${jobId}`);
}

export async function exportResults(
  jobId: string,
  target: ExportRequest["target"],
  sharepointUrl?: string
): Promise<{ status: string; detail?: string; url?: string }> {
  const res = await fetch(`${BASE}/export/${jobId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, sharepoint_url: sharepointUrl }),
  });
  if (!res.ok) throw new Error("Export failed");
  return res.json();
}

export async function updateTaskStatus(
  taskId: string,
  status: "todo" | "progress" | "done"
): Promise<{ task_id: string; status: string }> {
  const res = await fetch(`${BASE}/tasks/${taskId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error("Failed to update task status");
  return res.json();
}

export async function fetchInsights(): Promise<CrossMeetingInsights> {
  const res = await fetch(`${BASE}/insights`);
  if (!res.ok) throw new Error("Failed to fetch insights");
  return res.json();
}

export async function refreshInsights(): Promise<CrossMeetingInsights> {
  const res = await fetch(`${BASE}/insights/refresh`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to refresh insights");
  return res.json();
}

export async function fetchNotifications(unreadOnly = false): Promise<AppNotification[]> {
  const res = await fetch(`${BASE}/notifications${unreadOnly ? "?unread_only=true" : ""}`);
  if (!res.ok) throw new Error("Failed to fetch notifications");
  return res.json();
}

export async function markNotificationRead(id: string): Promise<void> {
  const res = await fetch(`${BASE}/notifications/${id}/read`, { method: "PATCH" });
  if (!res.ok) throw new Error("Failed to mark notification read");
}

export async function fetchAutonomousStatus(): Promise<AutonomousStatus> {
  const res = await fetch(`${BASE}/autonomous/status`);
  if (!res.ok) throw new Error("Failed to fetch autonomous status");
  return res.json();
}

export async function toggleAutonomous(): Promise<{ running: boolean; message: string }> {
  const res = await fetch(`${BASE}/autonomous/toggle`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to toggle autonomous mode");
  return res.json();
}

export const getDownloadUrl = (jobId: string): string => `${BASE}/download/${jobId}`;
