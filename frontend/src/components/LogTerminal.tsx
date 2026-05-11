import React, { useRef, useEffect } from "react";
import { Terminal, Loader2 } from "lucide-react";

interface LogTerminalProps {
  logs: string[];
  status: string;
  progress: number;
  hasStarted: boolean;
}

const LogTerminal: React.FC<LogTerminalProps> = ({
  logs,
  status,
  progress,
  hasStarted,
}) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <section className="bg-white rounded-2xl p-6 border border-[#E5E7EB] shadow-card flex flex-col min-h-[300px]">
      <h2 className="text-xs font-bold uppercase tracking-[0.15em] text-[#6B7280] mb-4 flex items-center gap-2">
        <Terminal size={14} />
        Process Timeline
      </h2>
      <div className="flex-1 bg-[#F8F7F5] rounded-xl p-4 font-mono text-xs overflow-y-auto max-h-[400px]">
        {!hasStarted && (
          <div className="text-[#9CA3AF] italic">Awaiting input...</div>
        )}
        {logs.map((log, i) => (
          <div
            key={i}
            className="mb-1 border-l-2 border-[#E5E7EB] pl-3 py-1"
          >
            <span className={log.startsWith("Error") ? "text-red-500" : "text-[#6B7280]"}>
              {log}
            </span>
          </div>
        ))}
        {status === "processing" && (
          <div className="flex items-center gap-2 text-[#F26A21] mt-2">
            <Loader2 size={12} className="animate-spin" />
            <span>Processing... {progress}%</span>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </section>
  );
};

export default LogTerminal;
