import type { JobStatus, ExportRequest } from "../types";

const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

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

export const getDownloadUrl = (jobId: string): string => `${BASE}/download/${jobId}`;
