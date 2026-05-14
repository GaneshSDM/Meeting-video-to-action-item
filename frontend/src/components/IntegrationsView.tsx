import React, { useEffect, useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  ExternalLink,
  Loader2,
  RefreshCw,
  Share2,
  Users,
  XCircle,
  type LucideIcon,
} from "lucide-react";

interface IntegrationStatus {
  status: "connected" | "not_configured" | "error";
  detail: string;
}

interface IntegrationsStatusResponse {
  google_calendar: IntegrationStatus;
  microsoft_teams: IntegrationStatus;
  sharepoint: IntegrationStatus;
}

const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const statusMeta: Record<string, { dot: string; label: string; color: string }> = {
  connected: { dot: "bg-emerald-500", label: "Connected", color: "text-emerald-600" },
  not_configured: { dot: "bg-[#9CA3AF]", label: "Not Configured", color: "text-[#6B7280]" },
  error: { dot: "bg-red-500", label: "Error", color: "text-red-600" },
};

interface IntegrationDef {
  id: string;
  name: string;
  icon: LucideIcon;
  description: string;
  setupTitle: string;
  setupSteps: string[];
  comingSoon?: boolean;
}

const INTEGRATIONS: IntegrationDef[] = [
  {
    id: "google_calendar",
    name: "Google Calendar",
    icon: CalendarDays,
    description: "Sync meeting recordings with Google Calendar. Auto-create events from action items.",
    setupTitle: "Connect Google Calendar",
    setupSteps: [
      "Go to Google Cloud Console → APIs & Services → Credentials",
      "Create a Service Account with Calendar API access",
      "Download the JSON key file",
      "Set GOOGLE_SERVICE_ACCOUNT=/path/to/key.json in backend .env",
      "Share your calendar with the service account email",
    ],
  },
  {
    id: "microsoft_teams",
    name: "Microsoft Teams",
    icon: Users,
    description: "Pull meeting recordings, create invites, and sync action items with Teams.",
    setupTitle: "Connect Microsoft Teams",
    setupSteps: [
      "Go to Azure Portal → App Registrations → New Registration",
      "Add Microsoft Graph permissions: Calendars.ReadWrite, OnlineMeetings.Read.All",
      "Create a client secret under Certificates & Secrets",
      "Set MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT_ID in backend .env",
      "Or set TEAMS_TOKEN directly if you already have a bearer token",
    ],
  },
  {
    id: "sharepoint",
    name: "SharePoint",
    icon: Share2,
    description: "Download meeting recordings from SharePoint and export reports back.",
    setupTitle: "Connect SharePoint",
    setupSteps: [
      "Use the same Azure AD app as Teams (same MS_CLIENT_ID)",
      "Add Microsoft Graph permissions: Sites.Read.All, Files.ReadWrite.All",
      "Ensure MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT_ID are set in backend .env",
      "Grant admin consent for the required permissions",
    ],
  },
  {
    id: "slack",
    name: "Slack",
    icon: ExternalLink,
    description: "Post meeting summaries and action items directly to Slack channels.",
    setupTitle: "Connect Slack (Coming Soon)",
    setupSteps: [],
    comingSoon: true,
  },
  {
    id: "jira",
    name: "Jira",
    icon: ExternalLink,
    description: "Auto-create Jira tickets from meeting action items.",
    setupTitle: "Connect Jira (Coming Soon)",
    setupSteps: [],
    comingSoon: true,
  },
  {
    id: "notion",
    name: "Notion",
    icon: ExternalLink,
    description: "Sync meeting notes and action items to Notion databases.",
    setupTitle: "Connect Notion (Coming Soon)",
    setupSteps: [],
    comingSoon: true,
  },
];

const IntegrationsView: React.FC = () => {
  const [statuses, setStatuses] = useState<IntegrationsStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modalDef, setModalDef] = useState<IntegrationDef | null>(null);

  const fetchStatus = async () => {
    const res = await fetch(`${BASE}/integrations/status`);
    if (!res.ok) throw new Error("Failed to fetch integration status");
    return res.json();
  };

  const load = async () => {
    setLoading(true);
    try {
      setStatuses(await fetchStatus());
    } catch (err) {
      console.error("Failed to load integration status", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      setStatuses(await fetchStatus());
    } catch (err) {
      console.error("Failed to refresh", err);
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loader2 size={32} className="animate-spin text-[#F26A21]" />
      </div>
    );
  }

  return (
    <div className="space-y-7">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#0B1633]">Integrations Hub</h2>
          <p className="mt-1 text-sm text-[#6B7280]">
            Connect MeetFlow to your existing tool ecosystem
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 rounded-lg border border-[#E5E7EB] bg-white px-4 py-2 text-sm font-medium text-[#5C667A] transition hover:border-[#F26A21]/40 hover:text-[#F26A21] disabled:opacity-50"
        >
          <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} />
          {refreshing ? "Checking..." : "Refresh Status"}
        </button>
      </div>

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {INTEGRATIONS.map((def) => {
          const isComingSoon = def.comingSoon;
          const status = statuses?.[def.id as keyof IntegrationsStatusResponse] ?? null;
          const meta = status ? statusMeta[status.status] : statusMeta.not_configured;

          return (
            <article
              key={def.id}
              className={`rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-card transition ${
                isComingSoon ? "opacity-70" : ""
              }`}
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#0a5791]/10 text-[#0a5791]">
                  <def.icon size={20} />
                </div>
                <div>
                  <h3 className="font-bold text-[#0B1633]">{def.name}</h3>
                  {isComingSoon ? (
                    <span className="text-xs font-medium text-[#9CA3AF]">Coming Soon</span>
                  ) : (
                    <div className="flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                      <span className={`text-xs font-medium ${meta.color}`}>{meta.label}</span>
                    </div>
                  )}
                </div>
              </div>

              <p className="mb-5 text-sm leading-6 text-[#5C667A]">{def.description}</p>

              {status?.detail && !isComingSoon && (
                <p className="mb-4 rounded-lg bg-[#F8F7F5] p-3 font-mono text-xs text-[#6B7280]">
                  {status.detail.length > 120
                    ? `${status.detail.slice(0, 120)}...`
                    : status.detail}
                </p>
              )}

              {isComingSoon ? (
                <button
                  disabled
                  className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[#E5E7EB] bg-[#F8F7F5] px-4 py-2.5 text-sm font-medium text-[#9CA3AF] cursor-not-allowed"
                >
                  Available Soon
                </button>
              ) : (
                <button
                  onClick={() => setModalDef(def)}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-xl border-2 border-[#F26A21] px-4 py-2.5 text-sm font-bold text-[#F26A21] transition hover:bg-[#F26A21] hover:text-white"
                >
                  {status?.status === "connected" ? (
                    <>
                      <CheckCircle2 size={15} />
                      Reconfigure
                    </>
                  ) : status?.status === "error" ? (
                    <>
                      <XCircle size={15} />
                      Fix Connection
                    </>
                  ) : (
                    <>
                      <ExternalLink size={15} />
                      Connect
                    </>
                  )}
                </button>
              )}
            </article>
          );
        })}
      </div>

      {modalDef && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setModalDef(null)}
        >
          <div
            className="mx-4 max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-[#E5E7EB] bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 border-b border-[#F3F4F6] bg-white px-6 py-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#0a5791]/10 text-[#0a5791]">
                  <modalDef.icon size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-[#0B1633]">{modalDef.setupTitle}</h3>
                  <p className="text-xs text-[#6B7280]">Step-by-step setup guide</p>
                </div>
                <button
                  onClick={() => setModalDef(null)}
                  className="ml-auto text-[#9CA3AF] hover:text-[#0B1633]"
                >
                  <XCircle size={22} />
                </button>
              </div>
            </div>

            <div className="px-6 py-5">
              <ol className="space-y-4">
                {modalDef.setupSteps.map((step, i) => (
                  <li key={i} className="flex gap-4">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#F26A21] text-xs font-bold text-white">
                      {i + 1}
                    </span>
                    <p className="text-sm leading-6 text-[#5C667A] pt-0.5">{step}</p>
                  </li>
                ))}
              </ol>
            </div>

            <div className="border-t border-[#F3F4F6] px-6 py-4">
              <button
                onClick={() => {
                  setModalDef(null);
                  handleRefresh();
                }}
                className="w-full rounded-xl bg-[#F26A21] py-3 text-sm font-bold text-white shadow-button transition hover:bg-[#E55D1B]"
              >
                Done — Check Status
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IntegrationsView;
