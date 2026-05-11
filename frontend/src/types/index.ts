export interface ActionItem {
  owner: string;
  task: string;
  deadline: string | null;
  priority: "high" | "medium" | "low";
  confidence: number;
  context?: string;
}

export interface AnalysisOutput {
  transcript?: string;
  meeting_summary?: string;
  participants: string[];
  action_items: ActionItem[];
  raw_result?: string;
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  result?: AnalysisOutput;
  error?: string;
}

export interface ExportRequest {
  target: "sharepoint_list" | "sharepoint_document" | "local_log";
  sharepoint_url?: string;
}
