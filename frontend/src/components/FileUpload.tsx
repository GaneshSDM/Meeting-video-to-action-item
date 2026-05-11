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
      <div className="border-2 border-dashed border-[#E5E7EB] rounded-2xl p-12 flex flex-col items-center justify-center gap-4 hover:border-[#F26A21]/40 hover:bg-[#F26A21]/[0.03] transition-all group cursor-pointer relative">
        <input
          type="file"
          accept="video/*"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onFileSelect(f);
          }}
          className="absolute inset-0 opacity-0 cursor-pointer"
        />
        <div className="w-16 h-16 rounded-2xl bg-[#F26A21]/10 flex items-center justify-center">
          <FileVideo size={32} className="text-[#F26A21]" />
        </div>
        <div className="text-center">
          <p className="text-[#0B1633] font-semibold text-base">
            {file ? file.name : "Drag and drop or click to upload"}
          </p>
          <p className="text-sm text-[#6B7280] mt-1">
            MP4, MKV, AVI, MOV up to 500MB
          </p>
        </div>
      </div>
      <button
        onClick={onSubmit}
        disabled={!file || disabled || isProcessing}
        className="w-full bg-[#F26A21] hover:bg-[#E55D1B] disabled:bg-[#E5E7EB] disabled:text-[#9CA3AF] text-white font-semibold py-4 px-6 rounded-full transition-all duration-200 flex items-center justify-center gap-2 shadow-button disabled:shadow-none text-base"
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
