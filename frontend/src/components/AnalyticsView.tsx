import React, { useEffect, useState } from "react";
import {
  BarChart3,
  CheckCircle2,
  ClipboardList,
  Loader2,
  TrendingUp,
  Users,
  Video,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { fetchAnalyticsTimeSeries, fetchAnalyticsSummary } from "../services/api";
import type { AnalyticsSummary, AnalyticsTimeSeries } from "../types";

const PRIORITY_COLORS: Record<string, string> = {
  High: "#EF4444",
  Medium: "#F59E0B",
  Low: "#10B981",
};

const CONFIDENCE_COLORS = ["#F26A21", "#F59E0B", "#FBBF24", "#34D399", "#10B981"];

const AnalyticsView: React.FC<{ onNavigate?: (view: string) => void }> = ({ onNavigate }) => {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [timeseries, setTimeseries] = useState<AnalyticsTimeSeries | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ts, s] = await Promise.all([
        fetchAnalyticsTimeSeries(),
        fetchAnalyticsSummary(),
      ]);
      setTimeseries(ts);
      setSummary(s);
    } catch (err) {
      setError("Failed to load analytics data. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[500px] items-center justify-center">
        <div className="text-center">
          <Loader2 size={40} className="animate-spin text-[#F26A21] mx-auto mb-4" />
          <p className="text-[#6B7280]">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[500px] items-center justify-center">
        <div className="text-center max-w-md">
          <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-red-500/10 mx-auto mb-4">
            <BarChart3 size={36} className="text-red-500" />
          </div>
          <p className="text-lg font-bold text-[#0B1633] mb-2">Analytics Unavailable</p>
          <p className="text-sm text-[#6B7280] mb-4">{error}</p>
          <button onClick={loadData} className="inline-flex items-center gap-2 rounded-xl bg-[#F26A21] px-4 py-2 text-sm font-bold text-white hover:bg-[#E55D1B] transition">
            <Loader2 size={15} /> Retry
          </button>
        </div>
      </div>
    );
  }

  if (!summary || !timeseries) {
    return (
      <div className="flex min-h-[500px] items-center justify-center">
        <div className="text-center max-w-md">
          <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-[#F8F7F5] mx-auto mb-4">
            <Video size={36} className="text-[#6B7280]" />
          </div>
          <p className="text-lg font-bold text-[#0B1633] mb-2">No Data Yet</p>
          <p className="text-sm text-[#6B7280] mb-4">
            Process some meeting recordings to see analytics and charts here.
          </p>
          {onNavigate ? (
            <button
              onClick={() => onNavigate("upload")}
              className="inline-flex items-center gap-2 rounded-xl bg-[#F26A21] px-4 py-2 text-sm font-bold text-white hover:bg-[#E55D1B] transition"
            >
              Process Meeting
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  const priorityData = timeseries.priorityDistribution.length > 0
    ? timeseries.priorityDistribution
    : [
        { name: "High", value: summary.tasksByPriority.high || 0 },
        { name: "Medium", value: summary.tasksByPriority.medium || 0 },
        { name: "Low", value: summary.tasksByPriority.low || 0 },
      ];

  return (
    <div className="space-y-7">
      {/* Summary Metrics */}
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={CheckCircle2}
          label="Completion Rate"
          value={`${summary.completionRate}%`}
          tone="green"
        />
        <MetricCard
          icon={ClipboardList}
          label="Total Tasks"
          value={String(
            summary.tasksByStatus.todo +
              (summary.tasksByStatus.in_progress || 0) +
              (summary.tasksByStatus.done || 0) || "0"
          )}
          tone="orange"
        />
        <MetricCard
          icon={TrendingUp}
          label="Avg Confidence"
          value={`${Math.round(summary.avgConfidence * 100) || 0}%`}
          tone="amber"
        />
        <MetricCard
          icon={Users}
          label="Participants"
          value={String(summary.totalParticipants || 0)}
          tone="green"
        />
      </section>

      {/* Task Trends */}
      <section className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
        <h2 className="text-lg font-bold text-[#0B1633] mb-4">Task Trends</h2>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={timeseries.dailyTasks.slice().reverse()}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis dataKey="date" tick={{ fontSize: 12, fill: "#6B7280" }} />
            <YAxis tick={{ fontSize: 12, fill: "#6B7280" }} />
            <Tooltip
              contentStyle={{
                borderRadius: "12px",
                border: "1px solid #E5E7EB",
                background: "#fff",
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="created"
              name="Tasks Created"
              stroke="#F26A21"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
            <Line
              type="monotone"
              dataKey="completed"
              name="Tasks Completed"
              stroke="#10B981"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </section>

      {/* Priority + Owner Workload */}
      <section className="grid gap-5 xl:grid-cols-2">
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
          <h2 className="text-lg font-bold text-[#0B1633] mb-4">
            Priority Distribution
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={priorityData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={4}
                dataKey="value"
              >
                {priorityData.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={
                      PRIORITY_COLORS[entry.name] ||
                      CONFIDENCE_COLORS[priorityData.indexOf(entry) % 5]
                    }
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  borderRadius: "12px",
                  border: "1px solid #E5E7EB",
                }}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
          <h2 className="text-lg font-bold text-[#0B1633] mb-4">
            Owner Workload (Top 10)
          </h2>
          {timeseries.ownerWorkload.length === 0 ? (
            <div className="flex min-h-[300px] items-center justify-center text-[#9CA3AF]">
              <p>No owner data available yet.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={timeseries.ownerWorkload}
                layout="vertical"
                margin={{ left: 60 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis type="number" tick={{ fontSize: 12, fill: "#6B7280" }} />
                <YAxis
                  type="category"
                  dataKey="owner"
                  tick={{ fontSize: 12, fill: "#6B7280" }}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: "12px",
                    border: "1px solid #E5E7EB",
                  }}
                />
                <Legend />
                <Bar dataKey="tasks" name="Total Tasks" fill="#F26A21" radius={[0, 4, 4, 0]} />
                <Bar
                  dataKey="completed"
                  name="Completed"
                  fill="#10B981"
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      {/* Meeting Frequency + Confidence Distribution */}
      <section className="grid gap-5 xl:grid-cols-2">
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
          <h2 className="text-lg font-bold text-[#0B1633] mb-4">
            Meetings Per Week
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={timeseries.meetingFrequency.slice().reverse()}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
              <XAxis
                dataKey="week"
                tick={{ fontSize: 12, fill: "#6B7280" }}
              />
              <YAxis tick={{ fontSize: 12, fill: "#6B7280" }} />
              <Tooltip
                contentStyle={{
                  borderRadius: "12px",
                  border: "1px solid #E5E7EB",
                }}
              />
              <Bar dataKey="count" name="Meetings" fill="#0a5791" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
          <h2 className="text-lg font-bold text-[#0B1633] mb-4">
            Confidence Distribution
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={timeseries.confidenceDistribution}
              margin={{ left: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
              <XAxis
                dataKey="range"
                tick={{ fontSize: 12, fill: "#6B7280" }}
              />
              <YAxis tick={{ fontSize: 12, fill: "#6B7280" }} />
              <Tooltip
                contentStyle={{
                  borderRadius: "12px",
                  border: "1px solid #E5E7EB",
                }}
              />
              <Bar dataKey="count" name="Tasks" fill="#F26A21" radius={[4, 4, 0, 0]}>
                {timeseries.confidenceDistribution.map((_, index) => (
                  <Cell
                    key={index}
                    fill={CONFIDENCE_COLORS[index % CONFIDENCE_COLORS.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
};

const MetricCard: React.FC<{
  icon: React.ElementType;
  label: string;
  tone: "orange" | "amber" | "green" | "red";
  value: string;
}> = ({ icon: Icon, label, tone, value }) => {
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
    </article>
  );
};

export default AnalyticsView;
