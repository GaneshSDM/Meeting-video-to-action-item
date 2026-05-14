import React, { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  ClipboardList,
  Code2,
  FileText,
  FolderInput,
  LayoutDashboard,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  Users,
  Video,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import AnalyticsView from "./components/AnalyticsView";
import AutonomousPanel from "./components/AutonomousPanel";
import FileUpload from "./components/FileUpload";
import InsightsPanel from "./components/InsightsPanel";
import IntegrationsView from "./components/IntegrationsView";
import NotificationDropdown from "./components/NotificationDropdown";
import LogTerminal from "./components/LogTerminal";
import ResultsPanel from "./components/ResultsPanel";
import SharePointInput from "./components/SharePointInput";
import TabSelector from "./components/TabSelector";
import {
  analyzeSharePointUrl,
  createLogStream,
  fetchDashboard,
  fetchMeetings,
  fetchTasks,
  getJobStatus,
  updateTaskStatus,
  uploadVideo,
} from "./services/api";
import type { DashboardData, JobStatus, MeetingInfo, TaskInfo } from "./types";

type View = "overview" | "tasks" | "meetings" | "analytics" | "upload" | "integrations" | "autonomous";
type Priority = "High" | "Medium" | "Low";
type TaskStatus = "todo" | "progress" | "done";

interface NavItem {
  id: View;
  label: string;
  icon: LucideIcon;
  count?: number;
}

const navGroups: Array<{ label: string; items: NavItem[] }> = [
  {
    label: "Main",
    items: [
      { id: "overview" as const, label: "Overview", icon: LayoutDashboard },
      { id: "tasks" as const, label: "Task Board", icon: ClipboardList },
      { id: "meetings" as const, label: "Meetings", icon: Video },
      { id: "analytics" as const, label: "Analytics", icon: BarChart3 },
    ],
  },
  {
    label: "Ingest",
    items: [
      { id: "upload" as const, label: "Upload Meeting", icon: Upload },
      { id: "integrations" as const, label: "Integrations", icon: Wrench },
      { id: "autonomous" as const, label: "Autonomous", icon: ShieldCheck },
    ],
  },
];

const teamLinks = [
  { label: "All Teams", icon: Users, count: undefined },
  { label: "Engineering", icon: Code2, count: 8 },
  { label: "Product", icon: Sparkles, count: 5 },
  { label: "Design", icon: Circle, count: 3 },
];

const priorityClasses: Record<Priority, string> = {
  High: "bg-red-500",
  Medium: "bg-amber-500",
  Low: "bg-emerald-500",
};

const App: React.FC = () => {
  const [activeView, setActiveView] = useState<View>("overview");
  const [activeTab, setActiveTab] = useState<"sharepoint" | "upload">("sharepoint");
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [meetingsData, setMeetingsData] = useState<MeetingInfo[]>([]);
  const [tasksData, setTasksData] = useState<TaskInfo[]>([]);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [dataLoading, setDataLoading] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    if (status?.status === "completed" || status?.status === "failed") return;

    const interval = window.setInterval(async () => {
      try {
        const data = await getJobStatus(jobId);
        setStatus(data);
        if (data.status === "completed" || data.status === "failed") {
          setIsProcessing(false);
        }
      } catch (err) {
        console.error("Failed to fetch status", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, status?.status]);

  useEffect(() => {
    if (!jobId) return;

    setLogs([]);
    const eventSource = createLogStream(jobId);
    eventSource.onmessage = (event) => {
      if (event.data === "[DONE]") {
        eventSource.close();
        return;
      }
      setLogs((prev) => [...prev, event.data]);
    };
    eventSource.onerror = () => eventSource.close();

    return () => eventSource.close();
  }, [jobId]);

  const loadData = async () => {
    setDataLoading(true);
    try {
      const [meetings, tasks, dashboard] = await Promise.all([
        fetchMeetings(),
        fetchTasks(),
        fetchDashboard(),
      ]);
      setMeetingsData(meetings);
      setTasksData(tasks);
      setDashboardData(dashboard);
    } catch (err) {
      console.error("Failed to load data", err);
    } finally {
      setDataLoading(false);
    }
  };

  const handleMoveTask = async (taskId: string, newStatus: TaskStatus) => {
    setTasksData((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } satisfies TaskInfo : t))
    );
    try {
      await updateTaskStatus(taskId, newStatus);
    } catch (err) {
      console.error("Failed to persist task move", err);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeView]);

  // Refresh data after job completion
  useEffect(() => {
    if (status?.status === "completed" || status?.status === "failed") {
      loadData();
    }
  }, [status?.status]);

  const taskCountByStatus = useMemo(() => ({
    todo: tasksData.filter((t) => t.status === "todo").length,
    progress: tasksData.filter((t) => t.status === "progress").length,
    done: tasksData.filter((t) => t.status === "done").length,
  }), [tasksData]);

  const totalTasks = tasksData.length;
  const isRunning =
    !!jobId && status?.status !== "completed" && status?.status !== "failed";

  const currentTitle =
    activeView === "tasks"
      ? "Task Board"
      : activeView === "meetings"
      ? "Meetings"
      : activeView === "upload"
      ? "Upload Meeting"
      : activeView === "integrations"
      ? "Integrations"
      : activeView === "analytics"
      ? "Analytics"
      : activeView === "autonomous"
      ? "Autonomous Mode"
      : "Overview";

  const handleSharePointSubmit = async (url: string) => {
    setIsProcessing(true);
    setLogs([]);
    setJobId(null);
    setStatus(null);
    try {
      const data = await analyzeSharePointUrl(url);
      setJobId(data.job_id);
      setStatus(data);
    } catch (err) {
      console.error("SharePoint analysis failed", err);
      setLogs(["Error: Failed to analyze SharePoint URL."]);
      setIsProcessing(false);
    }
  };

  const handleFileUpload = async () => {
    if (!file) return;

    setIsProcessing(true);
    setLogs([]);
    setJobId(null);
    setStatus(null);
    try {
      const data = await uploadVideo(file);
      setJobId(data.job_id);
      setStatus(data);
    } catch (err) {
      console.error("Upload failed", err);
      setLogs([`Error: ${err instanceof Error ? err.message : "Upload failed."}`]);
      setIsProcessing(false);
    }
  };

  const openUpload = () => {
    setActiveView("upload");
    setActiveTab("upload");
  };

  return (
    <div className="min-h-screen bg-[#F8F7F5] text-[#0B1633]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[288px] border-r border-[#E5E7EB] bg-white lg:flex lg:flex-col">
        <div className="flex h-[72px] items-center border-b border-[#F3F4F6] px-5">
          <BrandMark />
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-7">
          <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F7F5] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#6B7280]">
                  Workspace
                </p>
                <p className="mt-2 text-base font-semibold text-[#0B1633]">Decision Minds</p>
                <span className="mt-2 inline-flex rounded bg-[#F26A21]/10 px-2 py-0.5 font-mono text-xs text-[#F26A21]">
                  Super Admin
                </span>
              </div>
              <ChevronDown size={17} className="mt-8 text-[#9CA3AF]" />
            </div>
          </div>

          <nav className="mt-10 space-y-8">
            {navGroups.map((group) => (
              <div key={group.label}>
                <p className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-[#6B7280]">
                  {group.label}
                </p>
                <div className="space-y-1">
                  {group.items.map((item) => {
                    const displayCount = item.id === "tasks" ? totalTasks || undefined : item.count;
                    return (
                      <button
                        key={item.id}
                        onClick={() => setActiveView(item.id)}
                        className={`group flex h-[46px] w-full items-center gap-3 rounded-lg border px-3 text-left text-sm font-medium transition ${
                          activeView === item.id
                            ? "border-[#F26A21]/35 bg-[#F26A21]/10 text-[#F26A21]"
                            : "border-transparent text-[#5C667A] hover:bg-[#F8F7F5] hover:text-[#0B1633]"
                        }`}
                      >
                        <item.icon size={18} />
                        <span className="flex-1">{item.label}</span>
                        {displayCount ? (
                          <span className="rounded-full bg-[#0B1633]/5 px-2 py-0.5 text-xs text-[#6B7280]">
                            {displayCount}
                          </span>
                        ) : null}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}

            <div>
              <p className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-[#6B7280]">
                Teams
              </p>
              <div className="space-y-1">
                {teamLinks.map((team, index) => (
                  <button
                    key={team.label}
                    className={`flex h-[46px] w-full items-center gap-3 rounded-lg border px-3 text-left text-sm font-medium transition ${
                      index === 0
                        ? "border-[#F26A21]/35 bg-[#F26A21]/10 text-[#F26A21]"
                        : "border-transparent text-[#5C667A] hover:bg-[#F8F7F5] hover:text-[#0B1633]"
                    }`}
                  >
                    <team.icon size={18} />
                    <span className="flex-1">{team.label}</span>
                    {team.count ? (
                      <span className="rounded-full bg-[#0B1633]/5 px-2 py-0.5 text-xs text-[#6B7280]">
                        {team.count}
                      </span>
                    ) : null}
                  </button>
                ))}
              </div>
            </div>
          </nav>
        </div>
      </aside>

      <main className="lg:pl-[288px]">
        <header className="sticky top-0 z-30 flex h-[58px] items-center justify-between border-b border-[#E5E7EB] bg-white/90 px-5 backdrop-blur md:px-8">
          <h1 className="text-xl font-bold tracking-normal text-[#0B1633]">{currentTitle}</h1>
          <div className="flex items-center gap-3">
            <span className="hidden border-r border-[#E5E7EB] pr-5 font-mono text-sm text-[#6B7280] sm:block">
              All Teams
            </span>
            <button
              onClick={openUpload}
              className="hidden h-9 items-center gap-2 rounded-lg border border-[#E5E7EB] px-4 text-sm font-medium text-[#0B1633] transition hover:border-[#F26A21]/40 hover:text-[#F26A21] md:flex"
            >
              <Plus size={16} />
              New Meeting
            </button>
            <NotificationDropdown />
            <IconButton label="Search">
              <Search size={20} />
            </IconButton>
          </div>
        </header>

        <div className="min-h-[calc(100vh-58px)] bg-[#F8F7F5] px-5 py-7 md:px-8">
          {activeView === "overview" && (
            <OverviewView
              dashboard={dashboardData}
              loading={dataLoading}
              meetings={meetingsData}
              onProcessMeeting={openUpload}
            />
          )}
          {activeView === "tasks" && (
            <TaskBoardView
              taskCountByStatus={taskCountByStatus}
              tasks={tasksData}
              loading={dataLoading}
              onMoveTask={handleMoveTask}
            />
          )}
          {activeView === "meetings" && (
            <MeetingsView
              meetings={meetingsData}
              loading={dataLoading}
              onProcessMeeting={openUpload}
            />
          )}
          {activeView === "upload" && (
            <UploadView
              activeTab={activeTab}
              file={file}
              isProcessing={isProcessing}
              isRunning={isRunning}
              jobId={jobId}
              logs={logs}
              status={status}
              onFileSelect={setFile}
              onFileUpload={handleFileUpload}
              onSharePointSubmit={handleSharePointSubmit}
              onTabChange={setActiveTab}
            />
          )}
          {activeView === "analytics" && <AnalyticsView onNavigate={(view: string) => setActiveView(view as View)} />}
          {activeView === "integrations" && <IntegrationsView />}
          {activeView === "autonomous" && <AutonomousPanel />}
        </div>
      </main>
    </div>
  );
};

const BrandMark = () => (
  <div className="flex items-center gap-3">
    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#F26A21] text-2xl font-black text-white">
      M
    </div>
    <span className="text-2xl font-bold tracking-normal text-[#0B1633]">
      Meet<span className="text-[#F26A21]">Flow</span>
    </span>
  </div>
);

const IconButton: React.FC<{ children: React.ReactNode; label: string }> = ({ children, label }) => (
  <button
    aria-label={label}
    className="relative flex h-11 w-11 items-center justify-center rounded-xl border border-[#E5E7EB] bg-white text-[#6B7280] transition hover:border-[#F26A21]/40 hover:text-[#F26A21]"
  >
    {children}
  </button>
);

const OverviewView: React.FC<{
  dashboard: DashboardData | null;
  loading: boolean;
  meetings: MeetingInfo[];
  onProcessMeeting: () => void;
}> = ({ dashboard, loading, meetings, onProcessMeeting }) => {
  if (loading && !dashboard) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loader2 size={32} className="animate-spin text-[#F26A21]" />
      </div>
    );
  }

  const d = dashboard || { total_tasks: 0, in_progress: 0, completed: 0, overdue: 0, total_meetings: 0, total_participants: 0, recent_meetings: [], activity: [] };
  const completionRate = d.total_tasks > 0 ? Math.round((d.completed / d.total_tasks) * 100) : 0;

  return (
    <div className="space-y-7">
      <section className="flex items-center gap-4 rounded-2xl border border-[#F26A21]/25 bg-gradient-to-r from-[#F26A21]/10 to-white px-6 py-5 shadow-card">
        <ShieldCheck size={24} className="text-[#F26A21]" />
        <p className="text-sm font-medium text-[#0B1633] md:text-base">
          You are signed in as <span className="font-bold text-[#F26A21]">Super Admin</span> -
          viewing data across {d.total_meetings} meetings and {d.total_participants} participants
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={ClipboardList} label="Total Tasks" value={String(d.total_tasks)} detail={`from ${d.total_meetings} meetings`} tone="orange" />
        <MetricCard icon={Loader2} label="In Progress" value={String(d.in_progress)} detail="across all teams" tone="amber" />
        <MetricCard icon={CheckCircle2} label="Completed" value={String(d.completed)} detail={`${completionRate}% completion rate`} tone="green" />
        <MetricCard icon={AlertTriangle} label="Overdue" value={String(d.overdue)} detail="need attention" tone="red" />
      </section>

      <InsightsPanel />

      <section className="grid gap-5 xl:grid-cols-[1.45fr_1fr]">
        <div className="rounded-2xl border border-[#E5E7EB] bg-white shadow-card">
          <PanelHeader title="Recent Meetings" action="View all" />
          <MeetingsTable meetings={meetings} compact />
        </div>
        <div className="rounded-2xl border border-[#E5E7EB] bg-white shadow-card">
          <PanelHeader title="Activity Timeline" icon={<RefreshCw size={17} />} />
          <div className="space-y-5 p-6">
            {d.activity.length > 0 ? (
              d.activity.map((item, i) => (
                <TimelineItem key={i} title={item.title} time={item.time} />
              ))
            ) : (
              <TimelineItem title="No activity yet" time="Process a meeting to get started" />
            )}
          </div>
        </div>
      </section>
    </div>
  );
};

const TaskBoardView: React.FC<{
  taskCountByStatus: Record<TaskStatus, number>;
  tasks: TaskInfo[];
  loading: boolean;
  onMoveTask: (taskId: string, newStatus: TaskStatus) => void;
}> = ({ taskCountByStatus, tasks, loading, onMoveTask }) => {
  const [priorityFilter, setPriorityFilter] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredTasks = tasks.filter((t) => {
    if (priorityFilter !== "All" && t.priority !== priorityFilter) return false;
    if (searchQuery && !t.title.toLowerCase().includes(searchQuery.toLowerCase()) && !(t.meeting || "").toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loader2 size={32} className="animate-spin text-[#F26A21]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3 border-b border-[#E5E7EB] pb-5">
        <span className="text-sm font-bold text-[#0B1633]">Priority:</span>
        <FilterButton active={priorityFilter === "All"} label="All" onClick={() => setPriorityFilter("All")} />
        <FilterButton active={priorityFilter === "High"} dot="bg-red-500" label="High" onClick={() => setPriorityFilter("High")} />
        <FilterButton active={priorityFilter === "Medium"} dot="bg-amber-500" label="Medium" onClick={() => setPriorityFilter("Medium")} />
        <FilterButton active={priorityFilter === "Low"} dot="bg-emerald-500" label="Low" onClick={() => setPriorityFilter("Low")} />
        <div className="hidden h-8 w-px bg-[#E5E7EB] md:block" />
        <div className="relative min-w-[250px]">
          <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
          <input
            className="h-10 w-full rounded-xl border border-[#E5E7EB] bg-white pl-11 pr-4 text-sm text-[#0B1633] outline-none placeholder:text-[#9CA3AF] focus:border-[#F26A21]/50 focus:ring-2 focus:ring-[#F26A21]/10"
            placeholder="Search tasks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="ml-auto flex items-center gap-5">
          <span className="font-mono text-sm text-[#6B7280]">{filteredTasks.length} tasks</span>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <TaskColumn title="To Do" dot="bg-[#9CA3AF]" count={taskCountByStatus.todo} status="todo" tasks={filteredTasks} onMoveTask={onMoveTask} />
        <TaskColumn title="In Progress" dot="bg-amber-500" count={taskCountByStatus.progress} status="progress" tasks={filteredTasks} onMoveTask={onMoveTask} />
        <TaskColumn title="Done" dot="bg-emerald-500" count={taskCountByStatus.done} status="done" tasks={filteredTasks} onMoveTask={onMoveTask} />
      </div>
    </div>
  );
};

const MeetingsView: React.FC<{
  meetings: MeetingInfo[];
  loading: boolean;
  onProcessMeeting: () => void;
}> = ({ meetings, loading, onProcessMeeting }) => {
  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loader2 size={32} className="animate-spin text-[#F26A21]" />
      </div>
    );
  }

  const processedCount = meetings.filter((m) => m.status === "Processed").length;

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#0B1633]">All Meetings</h2>
          <p className="mt-1 text-sm text-[#6B7280]">{processedCount} meetings processed</p>
        </div>
        <button
          onClick={onProcessMeeting}
          className="inline-flex h-9 items-center gap-2 rounded-xl bg-[#F26A21] px-4 text-sm font-bold text-white shadow-button transition hover:bg-[#E55D1B]"
        >
          <Plus size={17} />
          Process Meeting
        </button>
      </div>
      <div className="rounded-2xl border border-[#E5E7EB] bg-white shadow-card">
        <MeetingsTable meetings={meetings} />
      </div>
    </div>
  );
};

interface UploadViewProps {
  activeTab: "sharepoint" | "upload";
  file: File | null;
  isProcessing: boolean;
  isRunning: boolean;
  jobId: string | null;
  logs: string[];
  status: JobStatus | null;
  onFileSelect: (file: File) => void;
  onFileUpload: () => void;
  onSharePointSubmit: (url: string) => void;
  onTabChange: (tab: "sharepoint" | "upload") => void;
}

const UploadView: React.FC<UploadViewProps> = ({
  activeTab,
  file,
  isProcessing,
  isRunning,
  jobId,
  logs,
  status,
  onFileSelect,
  onFileUpload,
  onSharePointSubmit,
  onTabChange,
}) => (
  <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
    <section className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-[#0B1633]">Process Meeting</h2>
        <p className="mt-1 text-sm text-[#6B7280]">
          Upload a recording or process a SharePoint meeting link.
        </p>
      </div>
      <TabSelector activeTab={activeTab} onTabChange={onTabChange} />
      {activeTab === "sharepoint" ? (
        <SharePointInput
          disabled={isRunning}
          isProcessing={isProcessing}
          onSubmit={onSharePointSubmit}
        />
      ) : (
        <FileUpload
          disabled={isRunning}
          file={file}
          isProcessing={isProcessing}
          onFileSelect={onFileSelect}
          onSubmit={onFileUpload}
        />
      )}
      <div className="mt-6">
        <LogTerminal
          hasStarted={!!jobId}
          logs={logs}
          progress={status?.progress || 0}
          status={status?.status || ""}
        />
      </div>
    </section>

    <section className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
      <div className="mb-6 flex items-center justify-between border-b border-[#F3F4F6] pb-4">
        <h2 className="flex items-center gap-2 text-lg font-bold text-[#0B1633]">
          <CheckCircle2 size={20} className="text-[#F26A21]" />
          AI Action Insights
        </h2>
        {status?.status === "completed" ? (
          <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-600">
            Verified
          </span>
        ) : null}
      </div>
      {!jobId ? <EmptyUploadState /> : null}
      {status?.status === "processing" ? <ProcessingState progress={status.progress} /> : null}
      {status?.status === "failed" ? <FailedState error={status.error} /> : null}
      {status?.status === "completed" && status.result ? (
        <ResultsPanel jobId={jobId!} result={status.result} />
      ) : null}
    </section>
  </div>
);

const MetricCard: React.FC<{
  detail: string;
  icon: React.ElementType;
  label: string;
  tone: "orange" | "amber" | "green" | "red";
  value: string;
}> = ({ detail, icon: Icon, label, tone, value }) => {
  const valueClass = {
    orange: "text-[#F26A21]",
    amber: "text-amber-500",
    green: "text-emerald-500",
    red: "text-red-500",
  }[tone];

  return (
    <article className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
      <div className="mb-4 flex items-center gap-3 text-xs font-bold uppercase tracking-[0.14em] text-[#6B7280]">
        <Icon size={15} />
        {label}
      </div>
      <p className={`text-5xl font-bold ${valueClass}`}>{value}</p>
      <p className="mt-2 font-mono text-sm text-[#6B7280]">{detail}</p>
    </article>
  );
};
const MeetingsTable: React.FC<{ meetings: MeetingInfo[]; compact?: boolean }> = ({ meetings, compact = false }) => {
  const rows = compact ? meetings.slice(0, 4) : meetings;

  if (rows.length === 0) {
    return (
      <div className="flex min-h-[200px] items-center justify-center p-6 text-[#6B7280]">
        <p>No meetings yet. Process a meeting recording to get started.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[780px] border-collapse">
        <thead>
          <tr className="border-b border-[#F3F4F6] text-left text-xs font-black uppercase tracking-[0.16em] text-[#6B7280]">
            <th className="px-6 py-5">Meeting</th>
            <th className="px-6 py-5">Source</th>
            <th className="px-6 py-5">Tasks</th>
            <th className="px-6 py-5">Status</th>
            <th className="px-6 py-5">Date</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((meeting) => (
            <tr key={meeting.job_id} className="border-b border-[#F3F4F6] last:border-b-0">
              <td className="px-6 py-5">
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#0a5791]/10 text-[#0a5791]">
                    <FileText size={17} />
                  </div>
                  <div>
                    <p className="max-w-[520px] truncate font-bold text-[#0B1633]">{meeting.title}</p>
                    <p className="mt-1 font-mono text-sm text-[#6B7280]">{meeting.team} - {meeting.participants.length} participants</p>
                  </div>
                </div>
              </td>
              <td className="px-6 py-5">
                <span className="inline-flex items-center rounded-full bg-[#0a5791]/10 px-3 py-1 font-mono text-xs font-bold text-[#0a5791]">
                  <span className="mr-2 h-2 w-2 rounded-full bg-[#0a5791]" />
                  {meeting.source}
                </span>
              </td>
              <td className="px-6 py-5 font-mono text-sm text-[#6B7280]">{meeting.tasks}</td>
              <td className="px-6 py-5">
                <StatusBadge status={meeting.status} />
              </td>
              <td className="px-6 py-5">
                <div className="flex items-center gap-2 font-mono text-sm text-[#6B7280]">
                  {meeting.date}
                  {meeting.status === "Processed" ? <ChevronRight size={16} /> : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const TaskColumn: React.FC<{
  count: number;
  dot: string;
  status: TaskStatus;
  tasks: TaskInfo[];
  title: string;
  onMoveTask: (taskId: string, newStatus: TaskStatus) => void;
}> = ({ count, dot, status, tasks, title, onMoveTask }) => {
  const columnTasks = tasks.filter((task) => task.status === status);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const taskId = e.dataTransfer.getData("text/plain");
    if (taskId) {
      onMoveTask(taskId, status);
    }
  };

  return (
    <section
      className={`min-h-[560px] rounded-2xl border bg-white shadow-card transition-colors ${
        isDragOver ? "border-[#F26A21] bg-[#F26A21]/5" : "border-[#E5E7EB]"
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <header className="flex items-center gap-3 border-b border-[#F3F4F6] px-5 py-5">
        <span className={`h-3 w-3 rounded-full ${dot}`} />
        <h2 className="flex-1 text-lg font-bold text-[#0B1633]">{title}</h2>
        <span className="rounded-full bg-[#F8F7F5] px-3 py-1 font-mono text-sm text-[#6B7280]">
          {columnTasks.length}
        </span>
      </header>
      <div className="max-h-[614px] space-y-3 overflow-y-auto p-4">
        {columnTasks.length > 0 ? (
          columnTasks.map((task) => <TaskCard key={task.id} task={task} />)
        ) : (
          <div className="flex min-h-[320px] flex-col items-center justify-center text-[#9CA3AF]">
            <ClipboardList size={28} />
            <p className="mt-3 text-sm">Drop tasks here</p>
          </div>
        )}
      </div>
    </section>
  );
};

const TaskCard: React.FC<{ task: TaskInfo }> = ({ task }) => {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData("text/plain", task.id);
    e.dataTransfer.effectAllowed = "move";
  };

  return (
    <article
      draggable
      onDragStart={handleDragStart}
      className="cursor-grab rounded-xl border border-[#E5E7EB] bg-[#F8F7F5] p-5 transition hover:border-[#F26A21]/30 hover:bg-white hover:shadow-card active:cursor-grabbing active:shadow-card"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-bold leading-6 text-[#0B1633]">{task.title}</h3>
        <span className={`mt-1 h-3 w-3 shrink-0 rounded-full ${priorityClasses[task.priority]}`} />
      </div>
      {task.owner ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-[#5C667A]">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#F26A21] text-xs font-bold text-white">
            {task.initials}
          </span>
          {task.owner}
        </div>
      ) : null}
      {task.due ? (
        <p className="mt-3 flex items-center gap-2 font-mono text-sm font-bold text-red-500">
          <CalendarDays size={14} />
          {task.due}
        </p>
      ) : null}
      <p className="mt-4 flex items-center gap-1 truncate font-mono text-xs text-[#6B7280]">
        <Video size={13} />
        {task.meeting}
      </p>
    </article>
  );
};

const FilterButton: React.FC<{ active?: boolean; dot?: string; label: string; onClick?: () => void }> = ({
  active,
  dot,
  label,
  onClick,
}) => (
  <button
    onClick={onClick}
    className={`flex h-10 items-center gap-2 rounded-xl border px-4 text-sm font-medium transition ${
      active
        ? "border-[#F26A21]/40 bg-[#F26A21]/10 text-[#F26A21]"
        : "border-[#E5E7EB] bg-white text-[#5C667A] hover:border-[#F26A21]/40 hover:text-[#F26A21]"
    }`}
  >
    {dot ? <span className={`h-2.5 w-2.5 rounded-full ${dot}`} /> : null}
    {label}
  </button>
);

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const isProcessed = status === "Processed";
  const isFailed = status === "Failed";
  const colorClass = isProcessed
    ? "bg-emerald-500/10 text-emerald-600"
    : isFailed
    ? "bg-red-500/10 text-red-600"
    : "bg-amber-500/10 text-amber-600";
  const dotClass = isProcessed
    ? "bg-emerald-500"
    : isFailed
    ? "bg-red-500"
    : "bg-amber-500";

  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 font-mono text-xs font-bold ${colorClass}`}>
      <span className={`mr-2 h-2 w-2 rounded-full ${dotClass}`} />
      {status}
    </span>
  );
};

const PanelHeader: React.FC<{ action?: string; icon?: React.ReactNode; title: string }> = ({
  action,
  icon,
  title,
}) => (
  <div className="flex items-center justify-between border-b border-[#F3F4F6] px-6 py-5">
    <h2 className="text-xl font-bold text-[#0B1633]">{title}</h2>
    {action ? (
      <button className="flex items-center gap-2 rounded-xl border border-[#E5E7EB] px-4 py-2 text-sm font-medium text-[#5C667A] transition hover:border-[#F26A21]/40 hover:text-[#F26A21]">
        {action}
        <ChevronRight size={16} />
      </button>
    ) : (
      <span className="text-[#9CA3AF]">{icon}</span>
    )}
  </div>
);

const TimelineItem: React.FC<{ time: string; title: string }> = ({ time, title }) => (
  <div className="flex gap-4">
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-emerald-500/25 bg-emerald-500/10 text-emerald-600">
      <CheckCircle2 size={17} />
    </span>
    <div>
      <p className="font-semibold text-[#0B1633]">{title}</p>
      <p className="mt-1 font-mono text-sm text-[#6B7280]">{time}</p>
    </div>
  </div>
);

const EmptyUploadState = () => (
  <div className="flex min-h-[440px] flex-col items-center justify-center text-center text-[#6B7280]">
    <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-[#F8F7F5]">
      <FolderInput size={36} />
    </div>
    <p className="text-lg font-bold text-[#0B1633]">Ready to analyze</p>
    <p className="mt-2 max-w-sm text-sm leading-6">
      Paste a SharePoint link or upload a video to extract action items.
    </p>
  </div>
);

const ProcessingState: React.FC<{ progress: number }> = ({ progress }) => (
  <div className="flex min-h-[440px] flex-col items-center justify-center text-center">
    <div className="relative mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-[#F26A21]/10 text-[#F26A21]">
      <Loader2 size={40} className="animate-spin" />
      <span className="absolute text-xs font-bold">{progress}%</span>
    </div>
    <p className="text-lg font-bold text-[#0B1633]">Analyzing Meeting</p>
    <p className="mt-2 text-sm text-[#6B7280]">AI processing is in progress.</p>
  </div>
);

const FailedState: React.FC<{ error?: string }> = ({ error }) => (
  <div className="flex min-h-[440px] flex-col items-center justify-center text-center">
    <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-red-500/10 text-red-500">
      <AlertCircle size={36} />
    </div>
    <p className="text-lg font-bold text-[#0B1633]">Analysis Interrupted</p>
    <p className="mt-2 max-w-sm text-sm text-[#5C667A]">{error || "The meeting could not be processed."}</p>
  </div>
);
export default App;
