import React from "react";
import { Link, Upload } from "lucide-react";

interface TabSelectorProps {
  activeTab: "sharepoint" | "upload";
  onTabChange: (tab: "sharepoint" | "upload") => void;
}

const TabSelector: React.FC<TabSelectorProps> = ({ activeTab, onTabChange }) => {
  const activeClass = "bg-[#F26A21] text-white shadow-button";
  const inactiveClass =
    "bg-white text-[#6B7280] hover:text-[#0B1633] border border-[#E5E7EB]";

  return (
    <div className="flex gap-3 mb-6">
      <button
        onClick={() => onTabChange("sharepoint")}
        className={`flex items-center gap-2 px-5 py-3 rounded-full text-sm font-semibold transition-all duration-200 ${
          activeTab === "sharepoint" ? activeClass : inactiveClass
        }`}
      >
        <Link size={16} />
        SharePoint Link
      </button>
      <button
        onClick={() => onTabChange("upload")}
        className={`flex items-center gap-2 px-5 py-3 rounded-full text-sm font-semibold transition-all duration-200 ${
          activeTab === "upload" ? activeClass : inactiveClass
        }`}
      >
        <Upload size={16} />
        File Upload
      </button>
    </div>
  );
};

export default TabSelector;
