import React, { useState, useEffect } from "react";
import { CheckCircle2, Loader2, AlertCircle, Sparkles } from "lucide-react";
import Logo from "./components/Logo";
import TabSelector from "./components/TabSelector";
import SharePointInput from "./components/SharePointInput";
import FileUpload from "./components/FileUpload";
import LogTerminal from "./components/LogTerminal";
import ResultsPanel from "./components/ResultsPanel";
import {
  uploadVideo,
  analyzeSharePointUrl,
  getJobStatus,
  createLogStream,
} from "./services/api";
import type { JobStatus } from "./types";

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"sharepoint" | "upload">("sharepoint");
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

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
      } else {
        setLogs((prev) => [...prev, event.data]);
      }
    };
    eventSource.onerror = () => eventSource.close();
    return () => eventSource.close();
  }, [jobId]);

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
      setLogs([
        `Error: ${err instanceof Error ? err.message : "Upload failed."}`,
      ]);
      setIsProcessing(false);
    }
  };

  const isRunning =
    !!jobId && status?.status !== "completed" && status?.status !== "failed";

  return (
    <div className="min-h-screen bg-[#F8F7F5] flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-[#F3F4F6] shadow-nav">
        <div className="max-w-7xl mx-auto px-8 h-16 flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-3">
            <span className="hidden sm:inline text-sm text-[#6B7280] font-medium">
              Enterprise AI
            </span>
            <span className="w-2 h-2 rounded-full bg-[#F26A21] animate-pulse shadow-[0_0_8px_rgba(242,106,33,0.4)]" />
            <span className="text-sm text-[#0B1633] font-semibold">Active</span>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-gradient-to-b from-white to-[#F8F7F5] border-b border-[#F3F4F6]">
        <div className="max-w-7xl mx-auto px-8 py-12 text-center">
          <div className="inline-flex items-center gap-2 bg-white border border-[#E5E7EB] rounded-full px-5 py-2.5 mb-6 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#6B7280] shadow-sm">
            <Sparkles size={13} className="text-[#F26A21]" />
            AI-Powered Meeting Intelligence
          </div>
          <h1 className="text-5xl lg:text-6xl font-extrabold tracking-tight text-[#0B1633] leading-[1.05] -tracking-[0.02em]">
            Turn meetings into
            <br />
            <span className="text-[#0a5791]">actionable insights</span>
          </h1>
          <p className="mt-4 text-lg text-[#6B7280] max-w-2xl mx-auto font-medium leading-relaxed">
            Share a SharePoint link or upload a meeting recording. Our AI
            transcribes and extracts per-person action items in seconds.
          </p>
        </div>
      </section>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Input + Logs */}
          <div className="flex flex-col gap-6">
            {/* Input Card */}
            <div className="bg-white rounded-3xl p-8 border border-[#E5E7EB] shadow-card">
              <h2 className="text-lg font-bold text-[#0B1633] mb-6">
                Upload Meeting Video
              </h2>
              <TabSelector activeTab={activeTab} onTabChange={setActiveTab} />
              {activeTab === "sharepoint" ? (
                <SharePointInput
                  onSubmit={handleSharePointSubmit}
                  disabled={isRunning}
                  isProcessing={isProcessing}
                />
              ) : (
                <FileUpload
                  file={file}
                  onFileSelect={setFile}
                  onSubmit={handleFileUpload}
                  disabled={isRunning}
                  isProcessing={isProcessing}
                />
              )}
            </div>

            <LogTerminal
              logs={logs}
              status={status?.status || ""}
              progress={status?.progress || 0}
              hasStarted={!!jobId}
            />
          </div>

          {/* Right: Results */}
          <div className="bg-white rounded-3xl p-8 border border-[#E5E7EB] shadow-card flex flex-col min-h-[600px]">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-[#F3F4F6]">
              <h2 className="text-lg font-bold text-[#0B1633] flex items-center gap-2.5">
                <CheckCircle2 size={20} className="text-[#F26A21]" />
                AI Action Insights
              </h2>
              {status?.status === "completed" && (
                <span className="bg-[#F26A21]/10 text-[#F26A21] text-[10px] font-bold px-3 py-1 rounded-full border border-[#F26A21]/20 tracking-[0.1em] uppercase">
                  Verified
                </span>
              )}
            </div>

            {/* Empty state */}
            {!jobId && (
              <div className="flex-1 flex flex-col items-center justify-center text-[#9CA3AF] text-center px-8">
                <div className="w-20 h-20 rounded-2xl bg-[#F8F7F5] flex items-center justify-center mb-5">
                  <CheckCircle2 size={36} className="text-[#D1D5DB]" />
                </div>
                <p className="text-[#0B1633] font-semibold text-lg mb-1">
                  Ready to analyze
                </p>
                <p className="text-sm max-w-xs">
                  Paste a SharePoint link or upload a video to extract
                  AI-powered action items.
                </p>
              </div>
            )}

            {/* Processing */}
            {status?.status === "processing" && (
              <div className="flex-1 flex flex-col items-center justify-center text-center">
                <div className="relative mb-6">
                  <div className="w-20 h-20 rounded-2xl bg-[#F26A21]/5 flex items-center justify-center">
                    <Loader2 size={40} className="animate-spin text-[#F26A21]" />
                  </div>
                  <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-[#F26A21]">
                    {status.progress}%
                  </div>
                </div>
                <p className="text-[#0B1633] font-semibold text-lg mb-1">
                  Analyzing Meeting
                </p>
                <p className="text-sm text-[#6B7280]">
                  High-velocity Groq AI processing in progress...
                </p>
              </div>
            )}

            {/* Error */}
            {status?.status === "failed" && (
              <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
                <div className="w-20 h-20 rounded-2xl bg-red-50 flex items-center justify-center mb-5">
                  <AlertCircle size={36} className="text-red-500" />
                </div>
                <p className="font-bold text-lg text-[#0B1633]">
                  Analysis Interrupted
                </p>
                <p className="text-sm text-[#6B7280] mt-2">{status.error}</p>
              </div>
            )}

            {/* Results */}
            {status?.status === "completed" && status.result && (
              <ResultsPanel jobId={jobId!} result={status.result} />
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#F3F4F6] bg-white">
        <div className="max-w-7xl mx-auto px-8 py-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <Logo className="opacity-60" />
          <p className="text-[11px] text-[#9CA3AF] font-medium tracking-[0.15em] uppercase">
            &copy; {new Date().getFullYear()} Decision Minds &bull; Intelligent
            Systems
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
