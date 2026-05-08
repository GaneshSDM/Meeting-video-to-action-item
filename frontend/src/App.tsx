import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileVideo, Terminal, CheckCircle2, Loader2, AlertCircle, ExternalLink } from 'lucide-react';

interface JobStatus {
  job_id: string;
  status: string;
  progress: number;
  result?: string;
  error?: string;
}

const App: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    let interval: number;
    if (jobId && status?.status !== 'completed' && status?.status !== 'failed') {
      interval = window.setInterval(async () => {
        try {
          const res = await fetch(`/api/status/${jobId}`);
          const data = await res.json();
          setStatus(data);
        } catch (err) {
          console.error('Failed to fetch status', err);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [jobId, status]);

  useEffect(() => {
    let eventSource: EventSource;
    if (jobId) {
      eventSource = new EventSource(`/api/logs/${jobId}`);
      eventSource.onmessage = (event) => {
        if (event.data === '[DONE]') {
          eventSource.close();
        } else {
          setLogs((prev) => [...prev, event.data]);
        }
      };
      eventSource.onerror = () => eventSource.close();
    }
    return () => eventSource?.close();
  }, [jobId]);

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setLogs([]);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setJobId(data.job_id);
      setStatus(data);
    } catch (err) {
      console.error('Upload failed', err);
      setLogs(['Error: Upload failed. Please try again.']);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col p-8 bg-[#0A192F] text-[#CCD6F6]">
      <header className="flex justify-between items-center mb-12">
        <div>
          <h1 className="text-3xl font-bold text-[#64FFDA] tracking-tight">Decision Minds</h1>
          <p className="text-[#8892B0] mt-1 text-lg">Meeting Intelligence Platform</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-[#8892B0]">
          <span className="w-2 h-2 rounded-full bg-[#64FFDA] animate-pulse"></span>
          System Active
        </div>
      </header>

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-7xl mx-auto w-full">
        {/* Left Column: Upload & Logs */}
        <div className="flex flex-col gap-8">
          <section className="bg-[#112240] rounded-xl p-8 border border-[#233554] shadow-xl">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2 text-[#CCD6F6]">
              <Upload size={20} className="text-[#64FFDA]" />
              Upload Meeting Video
            </h2>

            <div className="border-2 border-dashed border-[#8892B0]/30 rounded-lg p-12 flex flex-col items-center justify-center gap-4 hover:border-[#64FFDA]/50 transition-colors group cursor-pointer relative">
              <input
                type="file"
                accept="video/*"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
              <FileVideo size={48} className="text-[#8892B0] group-hover:text-[#64FFDA] transition-colors" />
              <div className="text-center">
                <p className="text-[#CCD6F6] font-medium">{file ? file.name : "Drag and drop or click to upload"}</p>
                <p className="text-sm text-[#8892B0]">MP4, MKV, AVI, MOV up to 500MB</p>
              </div>
            </div>

            <button
              onClick={handleUpload}
              disabled={!file || isUploading || !!(jobId && status?.status !== 'completed' && status?.status !== 'failed')}
              className="w-full mt-6 bg-[#0070f3] hover:bg-blue-600 disabled:bg-[#8892B0]/20 disabled:text-[#8892B0] text-white font-semibold py-4 px-6 rounded-lg transition-all flex items-center justify-center gap-2 shadow-lg"
            >
              {isUploading ? <Loader2 className="animate-spin" size={20} /> : "Start AI Analysis"}
            </button>
          </section>

          <section className="bg-black/20 rounded-xl p-6 border border-[#233554] shadow-xl flex-1 flex flex-col min-h-[300px]">
            <h2 className="text-xs font-bold uppercase tracking-widest text-[#8892B0] mb-4 flex items-center gap-2">
              <Terminal size={14} />
              Process Timeline
            </h2>
            <div className="flex-1 bg-black/40 rounded-lg p-4 font-mono text-xs overflow-y-auto max-h-[400px]">
              {logs.length === 0 && !jobId && <div className="text-[#8892B0]/30 italic">Awaiting input...</div>}
              {logs.map((log, i) => (
                <div key={i} className="mb-1 border-l border-[#233554] pl-3 py-1 ml-1">
                  <span className={log.startsWith('Error') ? 'text-red-400' : 'text-[#8892B0]'}>{log}</span>
                </div>
              ))}
              {status?.status === 'processing' && (
                <div className="flex items-center gap-2 text-[#64FFDA] mt-2 animate-pulse">
                  <Loader2 size={12} className="animate-spin" />
                  <span>Processing... {status.progress}%</span>
                </div>
              )}
              <div ref={logEndRef} />
            </div>
          </section>
        </div>

        {/* Right Column: Action Items */}
        <section className="bg-[#112240] rounded-xl p-8 border border-[#233554] shadow-xl flex flex-col min-h-[600px]">
          <div className="flex justify-between items-center mb-6 pb-4 border-b border-[#233554]">
            <h2 className="text-xl font-semibold flex items-center gap-2 text-[#CCD6F6]">
              <CheckCircle2 size={20} className="text-[#64FFDA]" />
              AI Action Insights
            </h2>
            {status?.status === 'completed' && (
              <span className="bg-[#64FFDA]/10 text-[#64FFDA] text-[10px] font-bold px-2 py-0.5 rounded border border-[#64FFDA]/20 tracking-widest">
                VERIFIED
              </span>
            )}
          </div>

          {!jobId && (
            <div className="flex-1 flex flex-col items-center justify-center text-[#8892B0] opacity-30 text-center px-12">
              <CheckCircle2 size={64} className="mb-4 stroke-[1px]" />
              <p className="text-lg">Intelligent extraction active</p>
              <p className="text-sm">Action items will populate automatically upon processing completion.</p>
            </div>
          )}

          {status?.status === 'processing' && (
            <div className="flex-1 flex flex-col items-center justify-center text-[#8892B0] text-center">
              <div className="relative mb-6">
                <Loader2 size={64} className="animate-spin text-[#64FFDA]" />
                <div className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-[#64FFDA]">
                  {status.progress}%
                </div>
              </div>
              <p className="text-[#CCD6F6] font-medium text-lg mb-1">Synthesizing Meeting Data</p>
              <p className="text-sm">Whisper & Mistral-7B working in sync...</p>
            </div>
          )}

          {status?.status === 'failed' && (
            <div className="flex-1 flex flex-col items-center justify-center text-red-400 text-center px-8">
              <AlertCircle size={48} className="mb-4" />
              <p className="font-bold text-lg">Analysis Interrupted</p>
              <p className="text-sm mt-2 opacity-80">{status.error}</p>
            </div>
          )}

          {status?.status === 'completed' && status.result && (
            <div className="flex-1 flex flex-col h-full">
              <div className="flex-1 bg-black/20 rounded-lg p-6 whitespace-pre-wrap text-[#CCD6F6] border border-[#233554] leading-relaxed font-sans text-sm mb-6 overflow-y-auto">
                {status.result}
              </div>
              <button className="w-full py-4 px-4 border border-[#64FFDA]/30 text-[#64FFDA] hover:bg-[#64FFDA]/10 rounded-lg transition-all flex items-center justify-center gap-2 text-sm font-semibold tracking-wide">
                EXPORT TO ENTERPRISE CRM
                <ExternalLink size={14} />
              </button>
            </div>
          )}
        </section>
      </main>

      <footer className="mt-12 text-center text-[#8892B0] text-[10px] border-t border-[#233554] pt-8 tracking-[0.2em] uppercase">
        Decision Minds &bull; Proprietary Intelligent Systems &bull; 2026
      </footer>
    </div>
  );
};

export default App;
