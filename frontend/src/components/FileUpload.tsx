import React from "react";
import { FileVideo, Loader2 } from "lucide-react";

interface FileUploadProps {
  file: File | null;
  onFileSelect: (file: File) => void;
  onSubmit: () => void;
  disabled: boolean;
  isProcessing: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({
  file,
  onFileSelect,
  onSubmit,
  disabled,
  isProcessing,
}) => {
  return (
    <div className="space-y-4">
      <div className="group relative flex cursor-pointer flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed border-[#E5E7EB] bg-white p-12 transition-all hover:border-[#F26A21]/40 hover:bg-[#F26A21]/[0.03]">
        <input
          type="file"
          accept="video/*"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onFileSelect(f);
          }}
          className="absolute inset-0 opacity-0 cursor-pointer"
        />
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F26A21]/10">
          <FileVideo size={32} className="text-[#F26A21]" />
        </div>
        <div className="text-center">
          <p className="text-base font-semibold text-[#0B1633]">
            {file ? file.name : "Drag and drop or click to upload"}
          </p>
          <p className="mt-1 text-sm text-[#6B7280]">
            MP4, MKV, AVI, MOV up to 500MB
          </p>
        </div>
      </div>
      <button
        onClick={onSubmit}
        disabled={!file || disabled || isProcessing}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#F26A21] px-6 py-4 text-base font-semibold text-white shadow-button transition-all duration-200 hover:bg-[#E55D1B] disabled:bg-[#E5E7EB] disabled:text-[#9CA3AF] disabled:shadow-none"
      >
        {isProcessing ? (
          <>
            <Loader2 className="animate-spin" size={20} />
            Processing...
          </>
        ) : (
          "Start AI Analysis"
        )}
      </button>
    </div>
  );
};

export default FileUpload;
