import React, { useState } from "react";
import { Calendar, ChevronDown, ChevronUp } from "lucide-react";
import type { ActionItem as ActionItemType } from "../types";

interface ActionItemCardProps {
  item: ActionItemType;
}

const priorityConfig = {
  high: {
    bg: "bg-red-50",
    text: "text-red-600",
    border: "border-red-200",
    dot: "bg-red-500",
  },
  medium: {
    bg: "bg-amber-50",
    text: "text-amber-600",
    border: "border-amber-200",
    dot: "bg-amber-500",
  },
  low: {
    bg: "bg-gray-50",
    text: "text-gray-500",
    border: "border-gray-200",
    dot: "bg-gray-400",
  },
};

const ActionItemCard: React.FC<ActionItemCardProps> = ({ item }) => {
  const [expanded, setExpanded] = useState(false);
  const config = priorityConfig[item.priority];

  const initials = item.owner
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-2xl p-5 hover:shadow-card-hover hover:border-[#F26A21]/20 transition-all duration-200">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#F26A21]/10 text-[#F26A21] flex items-center justify-center text-sm font-bold flex-shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[#0B1633] font-semibold text-sm leading-snug">
            {item.task}
          </p>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className="text-xs text-[#6B7280] font-medium">
              {item.owner}
            </span>
            <span
              className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${config.bg} ${config.text} ${config.border} uppercase tracking-wide`}
            >
              {item.priority}
            </span>
            {item.deadline && (
              <span className="text-[11px] text-[#6B7280] flex items-center gap-1.5">
                <Calendar size={11} />
                {item.deadline}
              </span>
            )}
          </div>

          {/* Confidence bar */}
          <div className="mt-3 flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-[#F3F4F6] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${item.confidence * 100}%`,
                  background:
                    item.confidence > 0.7
                      ? "linear-gradient(90deg, #34D399, #10B981)"
                      : item.confidence > 0.4
                      ? "linear-gradient(90deg, #FBBF24, #F59E0B)"
                      : "linear-gradient(90deg, #F87171, #EF4444)",
                }}
              />
            </div>
            <span className="text-[11px] font-medium text-[#9CA3AF] w-8 text-right">
              {Math.round(item.confidence * 100)}%
            </span>
          </div>

          {item.context && (
            <>
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-[11px] text-[#F26A21]/70 hover:text-[#F26A21] mt-2 transition-colors font-medium"
              >
                {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                {expanded ? "Hide context" : "Show context"}
              </button>
              {expanded && (
                <p className="mt-2 text-xs text-[#6B7280] italic border-l-2 border-[#F26A21]/20 pl-3 leading-relaxed">
                  "{item.context}"
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ActionItemCard;
