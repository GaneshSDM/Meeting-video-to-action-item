import React, { useState } from "react";
import { ExternalLink, Download, Loader2, CheckCircle2 } from "lucide-react";
import { exportResults } from "../services/api";
import { exportResults, getDownloadUrl } from "../services/api";

interface ExportButtonProps {
  jobId: string;
}

const ExportButton: React.FC<ExportButtonProps> = ({ jobId }) => {
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const handleExport = async (target: "local_log" | "sharepoint_document") => {
    setLoading(true);
    try {
      if (target === "local_log") {
        const a = document.createElement("a");
        a.href = `/api/download/${jobId}`;
        a.href = getDownloadUrl(jobId);
        a.download = `action_items_${jobId.slice(0, 8)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } else {
        await exportResults(jobId, target);
      }
      setDone(true);
      setTimeout(() => setDone(false), 3000);
    } catch (e) {
      console.error("Export failed", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex gap-3">
      <button
        onClick={() => handleExport("local_log")}
        disabled={loading}
        className="flex-1 py-3.5 px-4 border-2 border-[#F26A21] text-[#F26A21] hover:bg-[#F26A21] hover:text-white rounded-full transition-all duration-200 flex items-center justify-center gap-2 text-sm font-semibold disabled:opacity-50"
      >
        {loading ? (
          <Loader2 size={14} className="animate-spin" />
        ) : done ? (
          <CheckCircle2 size={14} />
        ) : (
          <Download size={14} />
        )}
        {done ? "Downloaded!" : "Download JSON"}
      </button>
      <button
        onClick={() => handleExport("sharepoint_document")}
        disabled={loading}
        className="flex-1 py-3.5 px-4 bg-[#0a5791] hover:bg-[#E55D1B] text-white rounded-full transition-all duration-200 flex items-center justify-center gap-2 text-sm font-semibold shadow-button disabled:opacity-50"
      >
        <ExternalLink size={14} />
        Export to SharePoint
      </button>
    </div>
  );
};

export default ExportButton;
