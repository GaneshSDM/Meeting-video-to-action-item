export interface ActionItem {
  owner: string;
  task: string;
  deadline: string | null;
  priority: "high" | "medium" | "low";
  confidence: number;
  context?: string;
  eventId?: string;
  teamsEventId?: string;
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

export interface MeetingInfo {
  job_id: string;
  title: string;
  team: string;
  source: string;
  tasks: number;
  status: "Processed" | "Failed" | "Processing";
  date: string;
  participants: string[];
  summary: string;
}

export interface TaskInfo {
  id: string;
  title: string;
  meeting: string;
  owner?: string | null;
  initials?: string | null;
  due?: string | null;
  priority: "High" | "Medium" | "Low";
  confidence: number;
  context: string;
  status: "todo" | "progress" | "done";
}

export interface DashboardData {
  total_tasks: number;
  in_progress: number;
  completed: number;
  overdue: number;
  total_meetings: number;
  total_participants: number;
  recent_meetings: Array<{ title: string; date: string; tasks: number }>;
  activity: Array<{ title: string; time: string }>;
}

export interface AnalyticsTimeSeries {
  dailyTasks: Array<{ date: string; created: number; completed: number }>;
  priorityDistribution: Array<{ name: string; value: number }>;
  ownerWorkload: Array<{ owner: string; tasks: number; completed: number }>;
  meetingFrequency: Array<{ week: string; count: number }>;
  confidenceDistribution: Array<{ range: string; count: number }>;
}

export interface AnalyticsSummary {
  tasksByPriority: Record<string, number>;
  tasksByStatus: Record<string, number>;
  completionRate: number;
  avgConfidence: number;
  totalMeetings: number;
  totalParticipants: number;
}

export interface CrossMeetingInsights {
  recurring_topics: Array<{ topic: string; frequency: number; meetings: string[] }>;
  bottlenecks: Array<{ description: string; severity: "high" | "medium" | "low"; affected_items: number }>;
  owner_workload: Array<{ owner: string; total_tasks: number; completed: number; high_priority: number; assessment: "overloaded" | "balanced" | "underutilized" }>;
  patterns: Array<{ pattern: string; confidence: "high" | "medium" | "low" }>;
  recommendations: string[];
  _generated_at?: string;
  _insufficient_data?: boolean;
}

export interface AppNotification {
  id: string;
  type: string;
  message: string;
  metadata: Record<string, unknown>;
  read: boolean;
  created_at: string;
}

export interface AutonomousStatus {
  running: boolean;
  enabled_env: boolean;
  jobs: Array<{ name: string; status: string }>;
}
