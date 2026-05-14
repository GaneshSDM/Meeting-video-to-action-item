import React, { useEffect, useRef, useState } from "react";
import {
  Bell,
  Brain,
  CalendarDays,
  CheckCheck,
  FileVideo,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { fetchNotifications, markNotificationRead } from "../services/api";
import type { AppNotification } from "../types";

const iconMap: Record<string, React.ElementType> = {
  meeting_detected: FileVideo,
  calendar_sync: CalendarDays,
  insights_refreshed: Brain,
  overdue_tasks: AlertTriangle,
  autonomous_started: CheckCheck,
  autonomous_stopped: CheckCheck,
};

const NotificationDropdown: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      setNotifications(await fetchNotifications());
    } catch (err) {
      console.error("Failed to load notifications", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const handleMarkRead = async (id: string) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
    } catch (err) {
      console.error("Failed to mark read", err);
    }
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative flex h-11 w-11 items-center justify-center rounded-xl border border-[#E5E7EB] bg-white text-[#6B7280] transition hover:border-[#F26A21]/40 hover:text-[#F26A21]"
        aria-label="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white ring-2 ring-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-2xl border border-[#E5E7EB] bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-[#F3F4F6] px-5 py-4">
            <h3 className="text-base font-bold text-[#0B1633]">Notifications</h3>
            {unreadCount > 0 && (
              <span className="rounded-full bg-[#F26A21]/10 px-2 py-0.5 text-xs font-bold text-[#F26A21]">
                {unreadCount} new
              </span>
            )}
          </div>

          <div className="max-h-[400px] overflow-y-auto">
            {loading && notifications.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 size={22} className="animate-spin text-[#F26A21]" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <Bell size={32} className="mx-auto mb-3 text-[#9CA3AF]" />
                <p className="text-sm font-medium text-[#6B7280]">No notifications yet</p>
                <p className="mt-1 text-xs text-[#9CA3AF]">
                  Enable autonomous mode to receive updates
                </p>
              </div>
            ) : (
              notifications.map((n) => {
                const Icon = iconMap[n.type] || Bell;
                return (
                  <div
                    key={n.id}
                    className={`flex gap-3 border-b border-[#F3F4F6] px-5 py-4 last:border-b-0 cursor-pointer transition ${
                      !n.read ? "bg-[#F26A21]/5" : "bg-white"
                    }`}
                    onClick={() => handleMarkRead(n.id)}
                  >
                    <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${!n.read ? "bg-[#F26A21]/10 text-[#F26A21]" : "bg-[#F8F7F5] text-[#6B7280]"}`}>
                      <Icon size={15} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${!n.read ? "font-semibold text-[#0B1633]" : "text-[#5C667A]"}`}>
                        {n.message}
                      </p>
                      <p className="mt-0.5 text-xs text-[#9CA3AF]">{formatTime(n.created_at)}</p>
                    </div>
                    {!n.read && (
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#F26A21]" />
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationDropdown;
