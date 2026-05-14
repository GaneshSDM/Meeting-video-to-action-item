import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  Brain,
  ChevronRight,
  Lightbulb,
  Loader2,
  RefreshCw,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import { fetchInsights, refreshInsights } from "../services/api";
import type { CrossMeetingInsights } from "../types";

const severityColors: Record<string, string> = {
  high: "border-red-500/20 bg-red-50 text-red-700",
  medium: "border-amber-500/20 bg-amber-50 text-amber-700",
  low: "border-blue-500/20 bg-blue-50 text-blue-700",
};

const severityDots: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-blue-500",
};

const confidenceColors: Record<string, string> = {
  high: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
  medium: "bg-amber-500/10 text-amber-600 border-amber-500/20",
  low: "bg-blue-500/10 text-blue-600 border-blue-500/20",
};

const assessmentColors: Record<string, string> = {
  overloaded: "text-red-600 bg-red-50",
  balanced: "text-emerald-600 bg-emerald-50",
  underutilized: "text-blue-600 bg-blue-50",
};

const InsightsPanel: React.FC = () => {
  const [insights, setInsights] = useState<CrossMeetingInsights | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInsights();
      setInsights(data);
    } catch (err) {
      setError("Failed to load insights");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const data = await refreshInsights();
      setInsights(data);
    } catch (err) {
      setError("Failed to refresh insights");
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-[#0B1633]">AI Insights</h2>
            <p className="mt-1 text-sm text-[#6B7280]">Analyzing cross-meeting patterns...</p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-[#E5E7EB] bg-white p-6">
              <div className="mb-3 h-4 w-20 rounded bg-[#F3F4F6]" />
              <div className="mb-2 h-6 w-3/4 rounded bg-[#F3F4F6]" />
              <div className="h-4 w-full rounded bg-[#F3F4F6]" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error && !insights) {
    return (
      <div className="rounded-2xl border border-red-500/20 bg-red-50 p-6">
        <div className="flex items-center gap-3">
          <AlertTriangle size={20} className="text-red-500" />
          <p className="text-sm font-medium text-red-700">{error}</p>
          <button onClick={load} className="ml-auto text-sm font-bold text-red-600 hover:underline">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (insights?._insufficient_data) {
    return (
      <section>
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-[#0B1633]">AI Insights</h2>
            <p className="mt-1 text-sm text-[#6B7280]">
              Process more meetings to unlock cross-meeting intelligence
            </p>
          </div>
        </div>
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 text-center shadow-card">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F26A21]/10">
            <Brain size={32} className="text-[#F26A21]" />
          </div>
          <p className="text-lg font-bold text-[#0B1633]">Not Enough Data</p>
          <p className="mt-2 max-w-md mx-auto text-sm leading-6 text-[#6B7280]">
            Process at least 2 meeting recordings to generate AI-powered cross-meeting
            insights about recurring topics, bottlenecks, and organizational patterns.
          </p>
          {insights.recommendations?.[0] ? (
            <p className="mt-3 text-sm font-medium text-[#F26A21]">
              {insights.recommendations[0]}
            </p>
          ) : null}
        </div>
      </section>
    );
  }

  if (!insights) return null;

  const hasTopics = insights.recurring_topics.length > 0;
  const hasBottlenecks = insights.bottlenecks.length > 0;
  const hasWorkload = insights.owner_workload.length > 0;
  const hasPatterns = insights.patterns.length > 0;

  return (
    <section>
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#0B1633]">AI Insights</h2>
          <p className="mt-1 text-sm text-[#6B7280]">
            Generated from cross-meeting analysis
            {insights._generated_at
              ? ` (${new Date(insights._generated_at).toLocaleDateString()})`
              : ""}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 rounded-lg border border-[#E5E7EB] bg-white px-4 py-2 text-sm font-medium text-[#5C667A] transition hover:border-[#F26A21]/40 hover:text-[#F26A21] disabled:opacity-50"
        >
          <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} />
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* Recurring Topics */}
      {hasTopics && (
        <div className="mb-5 rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
          <h3 className="mb-4 flex items-center gap-2 text-base font-bold text-[#0B1633]">
            <Zap size={17} className="text-[#F26A21]" />
            Recurring Topics
          </h3>
          <div className="flex flex-wrap gap-2">
            {insights.recurring_topics.map((t, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-2 rounded-full border border-[#F26A21]/20 bg-[#F26A21]/5 px-4 py-2 text-sm font-medium text-[#F26A21]"
              >
                {t.topic}
                <span className="rounded-full bg-[#F26A21]/15 px-2 py-0.5 text-xs font-bold">
                  {t.frequency}x
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        {/* Bottlenecks */}
        {hasBottlenecks && (
          <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
            <h3 className="mb-4 flex items-center gap-2 text-base font-bold text-[#0B1633]">
              <AlertTriangle size={17} className="text-red-500" />
              Bottlenecks
            </h3>
            <div className="space-y-3">
              {insights.bottlenecks.map((b, i) => (
                <div
                  key={i}
                  className={`rounded-xl border p-4 ${severityColors[b.severity] || severityColors.medium}`}
                >
                  <div className="flex items-start gap-3">
                    <span
                      className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${severityDots[b.severity] || severityDots.medium}`}
                    />
                    <div>
                      <p className="text-sm font-semibold">{b.description}</p>
                      <p className="mt-1 text-xs opacity-60">
                        {b.affected_items} affected items · {b.severity} severity
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Owner Workload */}
        {hasWorkload && (
          <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
            <h3 className="mb-4 flex items-center gap-2 text-base font-bold text-[#0B1633]">
              <Users size={17} className="text-[#F26A21]" />
              Owner Workload
            </h3>
            <div className="space-y-3">
              {insights.owner_workload.map((w, i) => (
                <div key={i} className="flex items-center justify-between rounded-xl border border-[#E5E7EB] p-4">
                  <div>
                    <p className="font-semibold text-[#0B1633]">{w.owner}</p>
                    <p className="mt-0.5 text-xs text-[#6B7280]">
                      {w.total_tasks} tasks · {w.completed} done · {w.high_priority} high
                    </p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-bold ${assessmentColors[w.assessment] || assessmentColors.balanced}`}>
                    {w.assessment}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Patterns & Recommendations */}
      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        {hasPatterns && (
          <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
            <h3 className="mb-4 flex items-center gap-2 text-base font-bold text-[#0B1633]">
              <TrendingUp size={17} className="text-[#F26A21]" />
              Identified Patterns
            </h3>
            <div className="space-y-3">
              {insights.patterns.map((p, i) => (
                <div
                  key={i}
                  className={`rounded-xl border p-4 ${confidenceColors[p.confidence] || confidenceColors.medium}`}
                >
                  <div className="flex items-start gap-3">
                    <BarChart3 size={16} className="mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-medium">{p.pattern}</p>
                      <p className="mt-1 text-xs opacity-60">{p.confidence} confidence</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {insights.recommendations.length > 0 && (
          <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
            <h3 className="mb-4 flex items-center gap-2 text-base font-bold text-[#0B1633]">
              <Lightbulb size={17} className="text-[#F26A21]" />
              Recommendations
            </h3>
            <div className="space-y-3">
              {insights.recommendations.map((r, i) => (
                <div key={i} className="flex gap-3 rounded-xl bg-[#F8F7F5] p-4">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#F26A21] text-xs font-bold text-white">
                    {i + 1}
                  </span>
                  <p className="text-sm leading-6 text-[#5C667A]">{r}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export default InsightsPanel;
