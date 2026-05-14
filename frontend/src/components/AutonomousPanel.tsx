import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  Clock,
  Loader2,
  Play,
  RefreshCw,
  Shield,
  Square,
  Zap,
} from "lucide-react";
import { fetchAutonomousStatus, refreshInsights, toggleAutonomous } from "../services/api";
import type { AutonomousStatus } from "../types";

const AutonomousPanel: React.FC = () => {
  const [status, setStatus] = useState<AutonomousStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);

  const load = async () => {
    try {
      setStatus(await fetchAutonomousStatus());
    } catch (err) {
      console.error("Failed to load autonomous status", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleToggle = async () => {
    setToggling(true);
    try {
      const result = await toggleAutonomous();
      setStatus((prev) => prev ? { ...prev, running: result.running } : null);
    } catch (err) {
      console.error("Toggle failed", err);
    } finally {
      setToggling(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={28} className="animate-spin text-[#F26A21]" />
      </div>
    );
  }

  const isRunning = status?.running ?? false;

  return (
    <div className="space-y-6">
      {/* Toggle Hero */}
      <div className={`rounded-2xl border p-6 shadow-card ${isRunning ? "border-emerald-500/20 bg-gradient-to-r from-emerald-50 to-white" : "border-[#E5E7EB] bg-white"}`}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${isRunning ? "bg-emerald-500/10 text-emerald-600" : "bg-[#F8F7F5] text-[#6B7280]"}`}>
              <Shield size={24} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[#0B1633]">Autonomous Mode</h3>
              <p className="text-sm text-[#6B7280]">
                {isRunning
                  ? "Auto-processing, calendar sync, and insights refresh are active"
                  : "Enable continuous background processing"}
              </p>
            </div>
          </div>
          <button
            onClick={handleToggle}
            disabled={toggling || !status?.enabled_env}
            className={`flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-bold transition disabled:opacity-50 ${
              isRunning
                ? "border-2 border-red-500/30 bg-red-50 text-red-600 hover:bg-red-100"
                : "bg-[#F26A21] text-white hover:bg-[#E55D1B] shadow-button"
            }`}
          >
            {toggling ? (
              <Loader2 size={15} className="animate-spin" />
            ) : isRunning ? (
              <Square size={15} />
            ) : (
              <Play size={15} />
            )}
            {isRunning ? "Stop Autonomous" : "Start Autonomous"}
          </button>
        </div>
        {!status?.enabled_env && (
          <p className="mt-4 rounded-lg bg-amber-50 px-4 py-2.5 text-sm font-medium text-amber-700">
            Set <code className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-xs">ENABLE_AUTONOMOUS=true</code> in your backend .env to enable this feature.
          </p>
        )}
      </div>

      {/* Job Status Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {status?.jobs.map((job) => (
          <div key={job.name} className="flex items-center gap-4 rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-card">
            <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${job.status === "active" ? "bg-emerald-500/10 text-emerald-600" : "bg-[#F8F7F5] text-[#9CA3AF]"}`}>
              {job.status === "active" ? <RefreshCw size={18} className="animate-spin-slow" /> : <Clock size={18} />}
            </div>
            <div>
              <p className="font-semibold text-[#0B1633] text-sm">{job.name}</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className={`h-2 w-2 rounded-full ${job.status === "active" ? "bg-emerald-500" : "bg-[#9CA3AF]"}`} />
                <span className="text-xs font-medium text-[#6B7280] capitalize">{job.status}</span>
              </div>
            </div>
            {job.status === "active" ? (
              <CheckCircle2 size={18} className="ml-auto text-emerald-500" />
            ) : null}
          </div>
        ))}
      </div>

      {/* Manual Actions */}
      <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card">
        <h3 className="mb-4 flex items-center gap-2 text-base font-bold text-[#0B1633]">
          <Zap size={17} className="text-[#F26A21]" />
          Manual Triggers
        </h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={async () => {
              try {
                await refreshInsights();
              } catch (err) {
                console.error(err);
              }
            }}
            className="inline-flex items-center gap-2 rounded-xl border border-[#E5E7EB] bg-white px-4 py-2.5 text-sm font-medium text-[#5C667A] hover:border-[#F26A21]/40 hover:text-[#F26A21] transition"
          >
            <RefreshCw size={15} />
            Regenerate Insights
          </button>
        </div>
      </div>
    </div>
  );
};

export default AutonomousPanel;
