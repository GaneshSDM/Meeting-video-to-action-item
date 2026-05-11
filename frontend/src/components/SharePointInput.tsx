import React, { useState } from "react";
import { Globe, Loader2, ArrowRight } from "lucide-react";

interface SharePointInputProps {
  onSubmit: (url: string) => void;
  disabled: boolean;
  isProcessing: boolean;
}

const SharePointInput: React.FC<SharePointInputProps> = ({
  onSubmit,
  disabled,
  isProcessing,
}) => {
  const [url, setUrl] = useState("");
  const isValid = url.trim().includes("sharepoint.com");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isValid && !disabled) onSubmit(url.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="relative">
        <Globe
          size={18}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-[#9CA3AF]"
        />
        <input
          type="url"
          placeholder="https://yourtenant.sharepoint.com/sites/team/Shared Documents/meeting.mp4"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={disabled}
          className="w-full pl-11 pr-4 py-4 bg-white border border-[#E5E7EB] rounded-2xl text-[#0B1633] placeholder-[#9CA3AF] text-sm focus:outline-none focus:border-[#F26A21]/40 focus:ring-2 focus:ring-[#F26A21]/10 transition-all disabled:opacity-50"
        />
      </div>
      <button
        type="submit"
        disabled={!isValid || disabled || isProcessing}
        className="w-full bg-[#F26A21] hover:bg-[#E55D1B] disabled:bg-[#E5E7EB] disabled:text-[#9CA3AF] text-white font-semibold py-4 px-6 rounded-full transition-all duration-200 flex items-center justify-center gap-2 shadow-button disabled:shadow-none text-base"
      >
        {isProcessing ? (
          <>
            <Loader2 className="animate-spin" size={20} />
            Analyzing Meeting...
          </>
        ) : (
          <>
            Analyze Meeting
            <ArrowRight size={18} />
          </>
        )}
      </button>
    </form>
  );
};

export default SharePointInput;
