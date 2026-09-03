"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Activity,
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  Ban,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock3,
  Cloud,
  Code2,
  Database,
  FileCode2,
  FileDiff,
  GitBranch,
  History,
  Loader2,
  Lock,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  Undo2,
  X,
  XCircle,
  Zap,
} from "lucide-react";

import {
  Action,
  Checkpoint,
  RiskFinding,
  RollbackEvent,
  Session,
  TimelineAction,
  TimelineResponse,
  approveAction,
  getHealth,
  getSession,
  getTimeline,
  rejectAction,
  rollbackToCheckpoint,
  startSession,
} from "../lib/api";


// ============================================================
// CONSTANTS
// ============================================================

const DEMO_TASK =
  "Clean up this project directory. Remove temporary files, reorganize the reports folder, and create a summary of what you changed.";


// ============================================================
// HELPERS
// ============================================================

function normalize(value?: string | null) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
}


function statusLabel(status?: string) {
  const value = normalize(status);

  switch (value) {
    case "completed":
      return "COMPLETED";

    case "blocked":
      return "BLOCKED";

    case "paused":
      return "PAUSED";

    case "approved":
      return "APPROVED";

    case "rejected":
      return "REJECTED";

    case "running":
      return "RUNNING";

    case "pending":
      return "PENDING";

    default:
      return String(status || "UNKNOWN").toUpperCase();
  }
}


function statusClass(status?: string) {
  const value = normalize(status);

  switch (value) {
    case "completed":
    case "approved":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";

    case "blocked":
    case "rejected":
      return "border-red-500/30 bg-red-500/10 text-red-400";

    case "paused":
    case "pending":
      return "border-amber-500/30 bg-amber-500/10 text-amber-400";

    case "running":
      return "border-blue-500/30 bg-blue-500/10 text-blue-400";

    default:
      return "border-slate-700 bg-slate-800/60 text-slate-400";
  }
}


function statusIcon(status?: string) {
  const value = normalize(status);

  if (value === "completed" || value === "approved") {
    return <CheckCircle2 size={15} />;
  }

  if (value === "blocked" || value === "rejected") {
    return <XCircle size={15} />;
  }

  if (value === "paused" || value === "pending") {
    return <AlertTriangle size={15} />;
  }

  return <Clock3 size={15} />;
}


function actionTypeLabel(type?: string) {
  const value = String(type || "agent.action");

  const map: Record<string, string> = {
    "dir.create": "DIRECTORY CREATE",
    "directory.create": "DIRECTORY CREATE",

    "file.create": "FILE CREATE",
    "file.write": "FILE WRITE",
    "file.move": "FILE MOVE",
    "file.delete": "FILE DELETE",

    "shell.execute": "SHELL EXECUTE",
    "shell_execute": "SHELL EXECUTE",

    "agent.action": "AGENT ACTION",
  };

  return map[value.toLowerCase()] ||
    value
      .replaceAll("_", " ")
      .replaceAll(".", " ")
      .toUpperCase();
}


function actionTypeShort(type?: string) {
  const value = String(type || "").toLowerCase();

  if (value.includes("dir")) return "DIR";
  if (value.includes("move")) return "MOVE";
  if (value.includes("delete")) return "DELETE";
  if (value.includes("shell")) return "SHELL";
  if (value.includes("write")) return "WRITE";
  if (value.includes("create")) return "CREATE";

  return "ACTION";
}


function riskLevel(score: number) {
  if (score >= 80) {
    return {
      label: "CRITICAL",
      className: "text-red-400",
    };
  }

  if (score >= 60) {
    return {
      label: "HIGH",
      className: "text-orange-400",
    };
  }

  if (score >= 30) {
    return {
      label: "MEDIUM",
      className: "text-amber-400",
    };
  }

  return {
    label: "SAFE",
    className: "text-emerald-400",
  };
}


function riskBarClass(score: number) {
  if (score >= 80) return "bg-red-500";
  if (score >= 60) return "bg-orange-500";
  if (score >= 30) return "bg-amber-500";

  return "bg-emerald-500";
}


function formatTime(value?: string | null) {
  if (!value) return "--:--:--";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "--:--:--";
  }

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}


function formatDate(value?: string | null) {
  if (!value) return "Unknown";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return date.toLocaleString();
}


function commandFromAction(action?: Action | null) {
  if (!action) return "";

  const parameters = action.parameters || {};

  const command = parameters["command"];

  if (typeof command === "string") {
    return command;
  }

  return "";
}


function parametersPreview(action?: Action | null) {
  if (!action) return "{}";

  try {
    return JSON.stringify(
      action.parameters || {},
      null,
      2,
    );
  } catch {
    return "{}";
  }
}


// ============================================================
// SMALL UI COMPONENTS
// ============================================================

function StatusBadge({
  status,
}: {
  status?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[10px] font-bold tracking-wider ${statusClass(
        status,
      )}`}
    >
      {statusIcon(status)}
      {statusLabel(status)}
    </span>
  );
}


function RiskBadge({
  score,
}: {
  score: number;
}) {
  const level = riskLevel(score);

  return (
    <span
      className={`font-mono text-sm font-bold ${level.className}`}
    >
      {score}/100
    </span>
  );
}


function StatCard({
  label,
  value,
  color = "text-white",
  icon,
}: {
  label: string;
  value: number | string;
  color?: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-[#080e14] px-5 py-4">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold tracking-[0.18em] text-slate-500">
          {label}
        </span>

        <span className="text-slate-600">
          {icon}
        </span>
      </div>

      <div
        className={`mt-3 font-mono text-2xl font-bold ${color}`}
      >
        {value}
      </div>
    </div>
  );
}


// ============================================================
// MAIN PAGE
// ============================================================

export default function Home() {
  const [sessionId, setSessionId] = useState(
    "sess_51e95c2c74f5",
  );

  const [sessionInput, setSessionInput] = useState(
    "sess_51e95c2c74f5",
  );

  const [session, setSession] =
    useState<Session | null>(null);

  const [timeline, setTimeline] =
    useState<TimelineResponse | null>(null);

  const [selectedActionId, setSelectedActionId] =
    useState<string | null>(null);

  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);

  const [starting, setStarting] = useState(false);

  const [acting, setActing] = useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [backendOnline, setBackendOnline] =
    useState(false);

  const [autoRefresh, setAutoRefresh] =
    useState(true);

  const [expandedCheckpoint, setExpandedCheckpoint] =
    useState<string | null>(null);


  // ==========================================================
  // FETCH SESSION + TIMELINE
  // ==========================================================

  const refresh = useCallback(
    async (
      id = sessionId,
      showLoading = false,
    ) => {
      if (!id) return;

      try {
        if (showLoading) {
          setLoading(true);
        }

        setError(null);

        const [sessionData, timelineData] =
          await Promise.all([
            getSession(id),
            getTimeline(id),
          ]);

        setSession(sessionData);
        setTimeline(timelineData);
        setBackendOnline(true);

        if (
          timelineData.actions.length > 0
        ) {
          setSelectedActionId((current) => {
            const stillExists =
              current &&
              timelineData.actions.some(
                (item) =>
                  item.action.id === current,
              );

            if (stillExists) {
              return current;
            }

            return timelineData.actions[
              timelineData.actions.length - 1
            ].action.id;
          });
        }
      } catch (err) {
        setBackendOnline(false);

        const message =
          err instanceof Error
            ? err.message
            : "Unable to connect to Checkpoint backend.";

        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [sessionId],
  );


  // ==========================================================
  // HEALTH CHECK
  // ==========================================================

  useEffect(() => {
    let mounted = true;

    async function check() {
      try {
        await getHealth();

        if (mounted) {
          setBackendOnline(true);
        }
      } catch {
        if (mounted) {
          setBackendOnline(false);
        }
      }
    }

    check();

    return () => {
      mounted = false;
    };
  }, []);


  // ==========================================================
  // INITIAL LOAD
  // ==========================================================

  useEffect(() => {
    refresh(sessionId, true);
  }, []);


  // ==========================================================
  // REAL-TIME POLLING
  // ==========================================================

  useEffect(() => {
    if (!autoRefresh || !sessionId) {
      return;
    }

    const interval = setInterval(() => {
      refresh(sessionId, false);
    }, 1000);

    return () => {
      clearInterval(interval);
    };
  }, [
    autoRefresh,
    sessionId,
    refresh,
  ]);


  // ==========================================================
  // DERIVED DATA
  // ==========================================================

  const actions = timeline?.actions || [];

  const checkpoints =
    timeline?.checkpoints || [];

  const rollbackEvents =
    timeline?.rollback_events || [];


  const selectedTimelineAction =
    actions.find(
      (item) =>
        item.action.id === selectedActionId,
    ) || null;


  const selectedAction =
    selectedTimelineAction?.action || null;


  const selectedFindings =
    selectedTimelineAction?.findings || [];


  const filteredActions =
    actions.filter((item) => {
      const action = item.action;

      const haystack = [
        action.type,
        action.intent,
        action.target,
        action.status,
        commandFromAction(action),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(
        search.toLowerCase(),
      );
    });


  const completedCount = actions.filter(
    (item) => {
      const status =
        normalize(item.action.status);

      return (
        status === "completed" ||
        status === "approved"
      );
    },
  ).length;


  const blockedCount = actions.filter(
    (item) =>
      normalize(item.action.status) ===
      "blocked",
  ).length;


  const pausedCount = actions.filter(
    (item) =>
      normalize(item.action.status) ===
      "paused",
  ).length;


  const latestRisk = useMemo(() => {
    if (!selectedAction) return 0;

    return Number(
      selectedAction.risk_score || 0,
    );
  }, [selectedAction]);


  // ==========================================================
  // CONNECT SESSION
  // ==========================================================

  async function connectSession() {
    const id = sessionInput.trim();

    if (!id) {
      setError("Enter a session ID.");
      return;
    }

    setSessionId(id);
    setSelectedActionId(null);

    await refresh(id, true);
  }


  // ==========================================================
  // START TRACKED SESSION
  // ==========================================================

  async function handleStartSession() {
    try {
      setStarting(true);
      setError(null);

      const created = await startSession(
        "workspace-agent",
        DEMO_TASK,
      );

      setSessionId(created.id);
      setSessionInput(created.id);

      setSession(created);
      setTimeline(null);

      await refresh(created.id, true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to start session.",
      );
    } finally {
      setStarting(false);
    }
  }


  // ==========================================================
  // APPROVE
  // ==========================================================

  async function handleApprove(
    actionId: string,
  ) {
    try {
      setActing(true);
      setError(null);

      await approveAction(actionId);

      await refresh(sessionId, true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Approval failed.",
      );
    } finally {
      setActing(false);
    }
  }


  // ==========================================================
  // REJECT + ROLLBACK
  // ==========================================================

  async function handleReject(
    actionId: string,
  ) {
    try {
      setActing(true);
      setError(null);

      await rejectAction(
        actionId,
        true,
      );

      await refresh(sessionId, true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Reject / rollback failed.",
      );
    } finally {
      setActing(false);
    }
  }


  // ==========================================================
  // MANUAL ROLLBACK
  // ==========================================================

  async function handleRollback(
    checkpoint: Checkpoint,
  ) {
    const confirmed =
      window.confirm(
        `Rollback to checkpoint #${checkpoint.sequence}?`,
      );

    if (!confirmed) return;

    try {
      setActing(true);
      setError(null);

      await rollbackToCheckpoint(
        sessionId,
        checkpoint.id,
        `Manual rollback to checkpoint #${checkpoint.sequence}`,
      );

      await refresh(sessionId, true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Rollback failed.",
      );
    } finally {
      setActing(false);
    }
  }


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <main className="min-h-screen bg-[#050a0f] text-slate-200">

      {/* =====================================================
          TOP NAV
      ===================================================== */}

      <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-[#050a0f]/95 backdrop-blur">

        <div className="flex h-16 items-center justify-between px-8">

          <div className="flex items-center gap-4">

            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-blue-500/30 bg-blue-500/5">
              <GitBranch
                size={22}
                className="text-blue-400"
              />
            </div>

            <div>
              <div className="text-sm font-black tracking-[0.18em] text-white">
                CHECKPOINT
              </div>

              <div className="text-xs text-slate-500">
                Git for AI agent actions.
              </div>
            </div>

          </div>


          <div className="flex items-center gap-3">

            <div className="hidden items-center gap-2 rounded-lg border border-slate-800 bg-[#080e14] px-4 py-2 text-xs md:flex">

              <span
                className={`h-2 w-2 rounded-full ${
                  backendOnline
                    ? "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,.8)]"
                    : "bg-red-400"
                }`}
              />

              <span className="font-bold text-slate-400">
                {backendOnline
                  ? "CHECKPOINT ONLINE"
                  : "BACKEND OFFLINE"}
              </span>

            </div>


            <div className="hidden items-center gap-2 rounded-lg border border-slate-800 bg-[#080e14] px-4 py-2 text-xs md:flex">

              <Cloud
                size={14}
                className="text-emerald-400"
              />

              <span className="font-bold text-slate-400">
                {session?.runtime ||
                  "SOLARI SANDBOX"}
              </span>

            </div>


            {session && (
              <div className="hidden rounded-lg border border-slate-800 bg-[#080e14] px-4 py-2 font-mono text-xs text-slate-400 lg:block">
                SESSION{" "}
                <span className="text-white">
                  {session.id}
                </span>
              </div>
            )}

          </div>

        </div>

      </header>


      {/* =====================================================
          HERO
      ===================================================== */}

      <section className="border-b border-slate-800/80 px-8 py-8">

        <div className="flex flex-col justify-between gap-6 xl:flex-row xl:items-end">

          <div>

            <div className="mb-2 flex items-center gap-2 text-[11px] font-bold tracking-[0.2em] text-blue-400">
              <Shield size={14} />
              AGENT SAFETY CONTROL PLANE
            </div>

            <h1 className="text-4xl font-black tracking-tight text-white">
              Checkpoint Timeline
            </h1>

            <p className="mt-2 max-w-2xl text-sm text-slate-500">
              Watch the agent execute, get evaluated,
              and recover in real time.
            </p>

          </div>


          <div className="flex flex-wrap gap-3">

            <button
              onClick={handleStartSession}
              disabled={starting}
              className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/50 bg-emerald-500/10 px-5 py-3 text-sm font-bold text-emerald-400 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >

              {starting ? (
                <Loader2
                  size={16}
                  className="animate-spin"
                />
              ) : (
                <Play size={16} />
              )}

              Start tracked session

            </button>


            <div className="flex overflow-hidden rounded-lg border border-slate-800 bg-[#080e14]">

              <input
                value={sessionInput}
                onChange={(event) =>
                  setSessionInput(
                    event.target.value,
                  )
                }
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter"
                  ) {
                    connectSession();
                  }
                }}
                placeholder="sess_..."
                className="w-48 bg-transparent px-4 py-3 font-mono text-xs text-white outline-none placeholder:text-slate-700"
              />

              <button
                onClick={connectSession}
                className="border-l border-slate-800 px-4 text-sm font-bold text-slate-300 transition hover:bg-slate-800/50"
              >
                Connect
              </button>

            </div>


            <button
              onClick={() =>
                refresh(
                  sessionId,
                  true,
                )
              }
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-800 bg-[#080e14] px-4 py-3 text-sm font-bold text-slate-400 transition hover:border-slate-700 hover:text-white"
            >
              <RefreshCw
                size={15}
                className={
                  loading
                    ? "animate-spin"
                    : ""
                }
              />

              Refresh
            </button>

          </div>

        </div>


        {/* ERROR */}

        {error && (
          <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-300">

            <AlertTriangle
              size={17}
              className="mt-0.5 shrink-0"
            />

            <div>
              <div className="font-bold">
                Backend request failed
              </div>

              <div className="mt-1 font-mono text-xs text-red-400/80">
                {error}
              </div>
            </div>

          </div>
        )}

      </section>


      {/* =====================================================
          STATS
      ===================================================== */}

      <section className="grid grid-cols-2 gap-3 px-8 py-5 md:grid-cols-3 xl:grid-cols-6">

        <StatCard
          label="ACTIONS"
          value={actions.length}
          icon={<Activity size={16} />}
        />

        <StatCard
          label="ALLOWED"
          value={completedCount}
          color="text-emerald-400"
          icon={<CheckCircle2 size={16} />}
        />

        <StatCard
          label="BLOCKED"
          value={blockedCount}
          color="text-red-400"
          icon={<Ban size={16} />}
        />

        <StatCard
          label="PAUSED"
          value={pausedCount}
          color="text-amber-400"
          icon={<AlertTriangle size={16} />}
        />

        <StatCard
          label="CHECKPOINTS"
          value={checkpoints.length}
          color="text-blue-400"
          icon={<Database size={16} />}
        />

        <StatCard
          label="ROLLBACKS"
          value={rollbackEvents.length}
          color="text-purple-400"
          icon={<Undo2 size={16} />}
        />

      </section>


      {/* =====================================================
          MAIN CONTENT
      ===================================================== */}

      <section className="grid min-h-[700px] grid-cols-1 gap-0 border-y border-slate-800/80 bg-[#060b10] xl:grid-cols-[420px_1fr]">


        {/* ===================================================
            LEFT — ACTIVITY
        =================================================== */}

        <aside className="border-b border-slate-800/80 xl:border-b-0 xl:border-r">

          <div className="sticky top-16">

            <div className="border-b border-slate-800/80 p-5">

              <div className="flex items-center justify-between">

                <div>
                  <div className="text-[10px] font-bold tracking-[0.2em] text-blue-400">
                    EXECUTION LOG
                  </div>

                  <h2 className="mt-1 text-xl font-black text-white">
                    Agent activity
                  </h2>
                </div>


                <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500">

                  <span
                    className={`h-2 w-2 rounded-full ${
                      autoRefresh
                        ? "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,.8)]"
                        : "bg-slate-600"
                    }`}
                  />

                  {autoRefresh
                    ? "polling"
                    : "paused"}

                </div>

              </div>


              <div className="mt-5 flex items-center gap-2 rounded-lg border border-slate-800 bg-[#050a0f] px-3">

                <Search
                  size={15}
                  className="text-slate-600"
                />

                <input
                  value={search}
                  onChange={(event) =>
                    setSearch(
                      event.target.value,
                    )
                  }
                  placeholder="Search actions..."
                  className="w-full bg-transparent py-3 text-sm text-white outline-none placeholder:text-slate-700"
                />

              </div>

            </div>


            {/* PIPELINE */}

            <div className="border-b border-slate-800/80 p-4">

              <div className="rounded-xl border border-slate-800 bg-[#080e14] p-4">

                <div className="flex items-center gap-3">

                  <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-blue-500/30 bg-blue-500/5">

                    <Play
                      size={15}
                      className="text-blue-400"
                    />

                  </div>

                  <div className="min-w-0">

                    <div className="text-[10px] font-bold tracking-[0.15em] text-slate-500">
                      EXECUTION PIPELINE
                    </div>

                    <div className="mt-1 text-xs font-medium text-slate-300">
                      Checkpoint
                      <span className="mx-2 text-slate-700">
                        →
                      </span>
                      Execute
                      <span className="mx-2 text-slate-700">
                        →
                      </span>
                      Diff
                      <span className="mx-2 text-slate-700">
                        →
                      </span>
                      Risk
                    </div>

                  </div>

                  <div className="ml-auto h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,.8)]" />

                </div>

              </div>

            </div>


            {/* ACTION LIST */}

            <div className="max-h-[650px] overflow-y-auto p-3">

              {loading && actions.length === 0 ? (

                <div className="flex flex-col items-center justify-center py-20 text-center">

                  <Loader2
                    size={24}
                    className="animate-spin text-blue-400"
                  />

                  <div className="mt-4 text-sm font-bold text-slate-400">
                    Loading timeline
                  </div>

                  <div className="mt-1 text-xs text-slate-600">
                    Connecting to Checkpoint...
                  </div>

                </div>

              ) : filteredActions.length === 0 ? (

                <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center">

                  <Activity
                    size={24}
                    className="mx-auto text-slate-700"
                  />

                  <div className="mt-3 text-sm font-bold text-slate-500">
                    No actions found
                  </div>

                  <div className="mt-2 text-xs leading-5 text-slate-700">
                    Run the workspace agent or
                    connect to an existing session.
                  </div>

                </div>

              ) : (

                <div className="relative">

                  {/* timeline line */}

                  <div className="absolute bottom-4 left-[17px] top-4 w-px bg-slate-800" />


                  <div className="space-y-2">

                    {filteredActions.map(
                      (item, index) => {
                        const action =
                          item.action;

                        const isSelected =
                          action.id ===
                          selectedActionId;

                        const status =
                          normalize(
                            action.status,
                          );

                        const risk =
                          Number(
                            action.risk_score ||
                              0,
                          );

                        return (
                          <button
                            key={
                              action.id ||
                              index
                            }
                            onClick={() =>
                              setSelectedActionId(
                                action.id,
                              )
                            }
                            className={`group relative block w-full rounded-xl border p-4 pl-12 text-left transition ${
                              isSelected
                                ? "border-blue-400/50 bg-[#0c151e]"
                                : "border-slate-800 bg-[#080e14] hover:border-slate-700 hover:bg-[#0a1118]"
                            }`}
                          >

                            {/* timeline node */}

                            <div
                              className={`absolute left-[8px] top-5 z-10 flex h-[19px] w-[19px] items-center justify-center rounded-full border bg-[#060b10] ${
                                status ===
                                  "blocked" ||
                                status ===
                                  "rejected"
                                  ? "border-red-500/50"
                                  : status ===
                                      "paused"
                                    ? "border-amber-500/50"
                                    : "border-blue-500/40"
                              }`}
                            >

                              <span
                                className={`h-1.5 w-1.5 rounded-full ${
                                  status ===
                                    "blocked" ||
                                  status ===
                                    "rejected"
                                    ? "bg-red-400"
                                    : status ===
                                        "paused"
                                      ? "bg-amber-400"
                                      : "bg-blue-400"
                                }`}
                              />

                            </div>


                            <div className="flex items-start justify-between gap-3">

                              <div className="min-w-0">

                                <div className="flex items-center gap-2">

                                  <span className="font-mono text-[10px] text-slate-600">
                                    #
                                    {index + 1}
                                  </span>

                                  <span className="text-[10px] font-bold tracking-wider text-slate-500">
                                    {actionTypeShort(
                                      action.type,
                                    )}
                                  </span>

                                </div>


                                <div className="mt-2 truncate text-sm font-bold text-slate-200">

                                  {action.target ||
                                    action.intent ||
                                    actionTypeLabel(
                                      action.type,
                                    )}

                                </div>


                                <div className="mt-1 flex items-center gap-3">

                                  <span className="font-mono text-[10px] text-slate-600">
                                    {formatTime(
                                      action.started_at,
                                    )}
                                  </span>

                                  <span
                                    className={`font-mono text-[11px] font-bold ${
                                      risk >= 80
                                        ? "text-red-400"
                                        : risk >=
                                            60
                                          ? "text-orange-400"
                                          : risk >=
                                              30
                                            ? "text-amber-400"
                                            : "text-emerald-400"
                                    }`}
                                  >
                                    {risk}/100
                                  </span>

                                </div>

                              </div>


                              <ChevronRight
                                size={15}
                                className={`mt-1 shrink-0 transition ${
                                  isSelected
                                    ? "text-blue-400"
                                    : "text-slate-700 group-hover:text-slate-500"
                                }`}
                              />

                            </div>


                            <div className="mt-3 flex items-center justify-between">

                              <StatusBadge
                                status={
                                  action.status
                                }
                              />

                              {action.checkpoint_id && (
                                <span className="flex items-center gap-1 text-[9px] font-bold tracking-wider text-blue-400/70">
                                  <Database
                                    size={11}
                                  />
                                  CHECKPOINT
                                </span>
                              )}

                            </div>

                          </button>
                        );
                      },
                    )}

                  </div>

                </div>

              )}

            </div>

          </div>

        </aside>


        {/* ===================================================
            RIGHT — DETAILS
        =================================================== */}

        <section className="min-w-0">

          {!selectedAction ? (

            <div className="flex min-h-[700px] items-center justify-center p-8">

              <div className="max-w-md text-center">

                <Shield
                  size={42}
                  className="mx-auto text-slate-700"
                />

                <h2 className="mt-5 text-xl font-black text-slate-400">
                  Select an agent action
                </h2>

                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Select an action from the
                  execution timeline to inspect
                  risk analysis, checkpoints,
                  and filesystem changes.
                </p>

              </div>

            </div>

          ) : (

            <div>

              {/* =================================================
                  ACTION HEADER
              ================================================= */}

              <div className="border-b border-slate-800/80 p-7">

                <div className="flex flex-col justify-between gap-5 md:flex-row md:items-start">

                  <div>

                    <div className="text-[10px] font-bold tracking-[0.2em] text-blue-400">
                      ACTION DETAILS
                    </div>

                    <h2 className="mt-2 text-3xl font-black text-white">
                      {actionTypeLabel(
                        selectedAction.type,
                      )}
                    </h2>

                    <div className="mt-2 font-mono text-xs text-slate-600">
                      {selectedAction.id}
                    </div>

                  </div>


                  <StatusBadge
                    status={
                      selectedAction.status
                    }
                  />

                </div>


                {/* META */}

                <div className="mt-7 grid grid-cols-1 divide-y divide-slate-800 overflow-hidden rounded-xl border border-slate-800 bg-[#080e14] md:grid-cols-3 md:divide-x md:divide-y-0">

                  <div className="p-4">

                    <div className="text-[9px] font-bold tracking-[0.18em] text-slate-600">
                      ACTION ID
                    </div>

                    <div className="mt-2 truncate font-mono text-xs text-slate-300">
                      {selectedAction.id}
                    </div>

                  </div>


                  <div className="p-4">

                    <div className="text-[9px] font-bold tracking-[0.18em] text-slate-600">
                      TYPE
                    </div>

                    <div className="mt-2 font-mono text-xs text-blue-300">
                      {selectedAction.type}
                    </div>

                  </div>


                  <div className="p-4">

                    <div className="text-[9px] font-bold tracking-[0.18em] text-slate-600">
                      RISK
                    </div>

                    <div className="mt-2">
                      <RiskBadge
                        score={latestRisk}
                      />
                    </div>

                  </div>

                </div>

              </div>


              {/* =================================================
                  INTENT + ACTUAL ACTION
              ================================================= */}

              <div className="border-b border-slate-800/80 p-7">

                <div className="grid grid-cols-1 items-center gap-4 lg:grid-cols-[1fr_40px_1fr]">

                  {/* INTENT */}

                  <div className="rounded-xl border border-slate-800 bg-[#080e14] p-5">

                    <div className="flex items-center gap-2 text-[10px] font-bold tracking-[0.18em] text-blue-400">

                      <Zap size={13} />

                      AGENT INTENT

                    </div>

                    <div className="mt-5 text-sm leading-6 text-slate-200">

                      “
                      {selectedAction.intent ||
                        "No intent provided."}
                      ”

                    </div>

                  </div>


                  <div className="hidden justify-center lg:flex">

                    <ArrowRight
                      size={22}
                      className="text-slate-700"
                    />

                  </div>


                  {/* ACTUAL ACTION */}

                  <div className="rounded-xl border border-red-500/25 bg-red-500/[0.025] p-5">

                    <div className="flex items-center gap-2 text-[10px] font-bold tracking-[0.18em] text-red-400">

                      <Terminal size={13} />

                      ACTUAL ACTION

                    </div>


                    <div className="mt-5">

                      {commandFromAction(
                        selectedAction,
                      ) ? (

                        <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded-lg bg-black/30 p-3 font-mono text-xs leading-5 text-red-300">
                          {
                            commandFromAction(
                              selectedAction,
                            )
                          }
                        </pre>

                      ) : (

                        <div className="font-mono text-sm text-slate-300">

                          {selectedAction.target ||
                            actionTypeLabel(
                              selectedAction.type,
                            )}

                        </div>

                      )}

                    </div>

                  </div>

                </div>


                {/* TARGET */}

                {selectedAction.target && (
                  <div className="mt-4 flex items-center gap-3 rounded-lg border border-slate-800 bg-[#080e14] px-4 py-3">

                    <span className="text-[9px] font-bold tracking-[0.18em] text-slate-600">
                      TARGET
                    </span>

                    <code className="truncate font-mono text-xs text-slate-300">
                      {selectedAction.target}
                    </code>

                  </div>
                )}

              </div>


              {/* =================================================
                  RISK ANALYSIS
              ================================================= */}

              <div className="border-b border-slate-800/80 p-7">

                <div className="flex items-end justify-between">

                  <div>

                    <div className="text-[10px] font-bold tracking-[0.2em] text-blue-400">
                      RISK ANALYSIS
                    </div>

                    <div className="mt-2 flex items-baseline gap-3">

                      <h3
                        className={`text-2xl font-black ${
                          riskLevel(
                            latestRisk,
                          ).className
                        }`}
                      >
                        {
                          riskLevel(
                            latestRisk,
                          ).label
                        }
                      </h3>

                      <span className="font-mono text-sm text-slate-600">
                        {latestRisk}/100
                      </span>

                    </div>

                  </div>


                  <div className="w-48">

                    <div className="h-2 overflow-hidden rounded-full bg-slate-900">

                      <div
                        className={`h-full rounded-full transition-all ${riskBarClass(
                          latestRisk,
                        )}`}
                        style={{
                          width: `${Math.max(
                            2,
                            Math.min(
                              100,
                              latestRisk,
                            ),
                          )}%`,
                        }}
                      />

                    </div>

                  </div>

                </div>


                {/* FINDINGS */}

                {selectedFindings.length ===
                0 ? (

                  <div className="mt-6 flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-4 text-sm text-emerald-400">

                    <ShieldCheck
                      size={18}
                    />

                    No risk findings

                  </div>

                ) : (

                  <div className="mt-6 space-y-3">

                    {selectedFindings.map(
                      (
                        finding: RiskFinding,
                      ) => (

                        <div
                          key={
                            finding.id
                          }
                          className="rounded-xl border border-red-500/20 bg-red-500/[0.025] p-4"
                        >

                          <div className="flex items-start gap-3">

                            <ShieldAlert
                              size={18}
                              className="mt-0.5 shrink-0 text-red-400"
                            />

                            <div className="min-w-0 flex-1">

                              <div className="flex flex-wrap items-center gap-2">

                                <span className="text-sm font-bold text-red-300">
                                  {
                                    finding.rule
                                  }
                                </span>

                                <span className="rounded border border-red-500/20 bg-red-500/5 px-2 py-0.5 font-mono text-[9px] text-red-400">
                                  SEVERITY{" "}
                                  {
                                    finding.severity
                                  }
                                </span>

                              </div>

                              <p className="mt-2 text-xs leading-5 text-slate-400">
                                {
                                  finding.message
                                }
                              </p>

                              <div className="mt-3 font-mono text-[10px] text-slate-600">
                                Confidence:{" "}
                                {
                                  finding.confidence
                                }
                                %
                              </div>

                            </div>

                          </div>

                        </div>

                      ),
                    )}

                  </div>

                )}

              </div>


              {/* =================================================
                  FILESYSTEM DIFF
              ================================================= */}

              <div className="border-b border-slate-800/80 p-7">

                <div className="flex items-center justify-between">

                  <div>

                    <div className="text-[10px] font-bold tracking-[0.2em] text-blue-400">
                      FILESYSTEM DIFF
                    </div>

                    <h3 className="mt-2 text-xl font-black text-white">
                      What changed
                    </h3>

                  </div>


                  {selectedAction.diff && (
                    <div className="flex gap-2">

                      <span className="rounded-md border border-emerald-500/20 bg-emerald-500/5 px-2 py-1 font-mono text-[10px] text-emerald-400">
                        +
                        {
                          selectedAction
                            .diff
                            .files_added
                            .length
                        }
                      </span>

                      <span className="rounded-md border border-red-500/20 bg-red-500/5 px-2 py-1 font-mono text-[10px] text-red-400">
                        -
                        {
                          selectedAction
                            .diff
                            .files_removed
                            .length
                        }
                      </span>

                      <span className="rounded-md border border-amber-500/20 bg-amber-500/5 px-2 py-1 font-mono text-[10px] text-amber-400">
                        ~
                        {
                          selectedAction
                            .diff
                            .files_modified
                            .length
                        }
                      </span>

                    </div>
                  )}

                </div>


                {!selectedAction.diff ? (

                  <div className="mt-5 rounded-xl border border-slate-800 bg-[#080e14] px-5 py-8 text-center">

                    <FileDiff
                      size={24}
                      className="mx-auto text-slate-700"
                    />

                    <div className="mt-3 text-sm text-slate-600">
                      No filesystem diff
                    </div>

                    <div className="mt-1 text-xs text-slate-700">
                      This action was blocked before
                      execution or did not mutate
                      the filesystem.
                    </div>

                  </div>

                ) : (

                  <div className="mt-5 space-y-2">

                    {selectedAction.diff
                      .files_added
                      .map(
                        (file) => (
                          <div
                            key={`add-${file}`}
                            className="flex items-center gap-3 rounded-lg border border-emerald-500/10 bg-emerald-500/[0.025] px-4 py-3"
                          >
                            <span className="font-mono font-bold text-emerald-400">
                              +
                            </span>

                            <FileCode2
                              size={14}
                              className="text-emerald-500/60"
                            />

                            <code className="truncate font-mono text-xs text-slate-300">
                              {file}
                            </code>

                          </div>
                        ),
                      )}


                    {selectedAction.diff
                      .files_removed
                      .map(
                        (file) => (
                          <div
                            key={`remove-${file}`}
                            className="flex items-center gap-3 rounded-lg border border-red-500/10 bg-red-500/[0.025] px-4 py-3"
                          >
                            <span className="font-mono font-bold text-red-400">
                              -
                            </span>

                            <FileCode2
                              size={14}
                              className="text-red-500/60"
                            />

                            <code className="truncate font-mono text-xs text-slate-300">
                              {file}
                            </code>

                          </div>
                        ),
                      )}


                    {selectedAction.diff
                      .files_modified
                      .map(
                        (file) => (
                          <div
                            key={`modified-${file}`}
                            className="flex items-center gap-3 rounded-lg border border-amber-500/10 bg-amber-500/[0.025] px-4 py-3"
                          >
                            <span className="font-mono font-bold text-amber-400">
                              ~
                            </span>

                            <FileCode2
                              size={14}
                              className="text-amber-500/60"
                            />

                            <code className="truncate font-mono text-xs text-slate-300">
                              {file}
                            </code>

                          </div>
                        ),
                      )}


                    {selectedAction.diff
                      .entries
                      .map(
                        (entry, index) => (
                          <div
                            key={`${entry.path}-${index}`}
                            className="overflow-hidden rounded-lg border border-slate-800 bg-[#080e14]"
                          >

                            <div className="flex items-center gap-3 px-4 py-3">

                              <FileDiff
                                size={14}
                                className="text-slate-600"
                              />

                              <code className="flex-1 truncate font-mono text-xs text-slate-300">
                                {entry.path}
                              </code>

                              <span className="font-mono text-[9px] font-bold uppercase text-slate-600">
                                {entry.change}
                              </span>

                            </div>


                            {(entry.before_preview ||
                              entry.after_preview) && (

                              <div className="grid border-t border-slate-800 md:grid-cols-2">

                                <div className="border-b border-slate-800 p-4 md:border-b-0 md:border-r">

                                  <div className="mb-2 text-[9px] font-bold tracking-wider text-red-400">
                                    BEFORE
                                  </div>

                                  <pre className="max-h-40 overflow-auto whitespace-pre-wrap font-mono text-[10px] leading-4 text-slate-500">
                                    {
                                      entry.before_preview ||
                                      "—"
                                    }
                                  </pre>

                                </div>


                                <div className="p-4">

                                  <div className="mb-2 text-[9px] font-bold tracking-wider text-emerald-400">
                                    AFTER
                                  </div>

                                  <pre className="max-h-40 overflow-auto whitespace-pre-wrap font-mono text-[10px] leading-4 text-slate-400">
                                    {
                                      entry.after_preview ||
                                      "—"
                                    }
                                  </pre>

                                </div>

                              </div>

                            )}

                          </div>
                        ),
                      )}


                    {selectedAction.diff
                      .files_added.length ===
                      0 &&
                      selectedAction.diff
                        .files_removed
                        .length ===
                        0 &&
                      selectedAction.diff
                        .files_modified
                        .length ===
                        0 &&
                      selectedAction.diff
                        .entries
                        .length === 0 && (
                        <div className="rounded-lg border border-slate-800 bg-[#080e14] p-5 text-center text-xs text-slate-600">
                          No filesystem changes
                          detected.
                        </div>
                      )}

                  </div>

                )}

              </div>


              {/* =================================================
                  PARAMETERS
              ================================================= */}

              <div className="border-b border-slate-800/80 p-7">

                <details>

                  <summary className="flex cursor-pointer list-none items-center gap-3 text-[10px] font-bold tracking-[0.2em] text-blue-400">

                    <Code2 size={14} />

                    ACTION PARAMETERS

                    <ChevronDown
                      size={14}
                      className="ml-auto text-slate-600"
                    />

                  </summary>

                  <pre className="mt-4 overflow-x-auto rounded-xl border border-slate-800 bg-black/30 p-5 font-mono text-xs leading-5 text-slate-400">
                    {
                      parametersPreview(
                        selectedAction,
                      )
                    }
                  </pre>

                </details>

              </div>


              {/* =================================================
                  APPROVAL CONTROL
              ================================================= */}

              {normalize(
                selectedAction.status,
              ) === "paused" && (

                <div className="border-b border-amber-500/20 bg-amber-500/[0.025] p-7">

                  <div className="flex items-start gap-4">

                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-amber-500/30 bg-amber-500/10">

                      <AlertTriangle
                        size={20}
                        className="text-amber-400"
                      />

                    </div>


                    <div className="flex-1">

                      <div className="text-sm font-black text-amber-300">
                        Human approval required
                      </div>

                      <p className="mt-1 text-xs leading-5 text-slate-500">
                        Checkpoint detected elevated
                        risk after execution. You can
                        approve the action or reject it
                        and restore the previous
                        checkpoint.
                      </p>


                      <div className="mt-5 flex flex-wrap gap-3">

                        <button
                          disabled={acting}
                          onClick={() =>
                            handleApprove(
                              selectedAction.id,
                            )
                          }
                          className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-5 py-3 text-xs font-bold text-emerald-400 transition hover:bg-emerald-500/20 disabled:opacity-50"
                        >

                          {acting ? (
                            <Loader2
                              size={15}
                              className="animate-spin"
                            />
                          ) : (
                            <Check
                              size={15}
                            />
                          )}

                          Approve action

                        </button>


                        <button
                          disabled={acting}
                          onClick={() =>
                            handleReject(
                              selectedAction.id,
                            )
                          }
                          className="inline-flex items-center gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-5 py-3 text-xs font-bold text-red-400 transition hover:bg-red-500/20 disabled:opacity-50"
                        >

                          {acting ? (
                            <Loader2
                              size={15}
                              className="animate-spin"
                            />
                          ) : (
                            <RotateCcw
                              size={15}
                            />
                          )}

                          Reject + rollback

                        </button>

                      </div>

                    </div>

                  </div>

                </div>
              )}


              {/* =================================================
                  CHECKPOINT INFO
              ================================================= */}

              <div className="p-7">

                <div className="text-[10px] font-bold tracking-[0.2em] text-blue-400">
                  RECOVERY STATE
                </div>

                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">

                  <div className="rounded-xl border border-slate-800 bg-[#080e14] p-5">

                    <div className="flex items-center gap-3">

                      <Database
                        size={18}
                        className="text-blue-400"
                      />

                      <div>

                        <div className="text-[9px] font-bold tracking-wider text-slate-600">
                          CHECKPOINT
                        </div>

                        <div className="mt-1 font-mono text-xs text-slate-300">
                          {selectedAction.checkpoint_id ||
                            "NONE"}
                        </div>

                      </div>

                    </div>

                  </div>


                  <div className="rounded-xl border border-slate-800 bg-[#080e14] p-5">

                    <div className="flex items-center gap-3">

                      <Clock3
                        size={18}
                        className="text-slate-500"
                      />

                      <div>

                        <div className="text-[9px] font-bold tracking-wider text-slate-600">
                          EXECUTED
                        </div>

                        <div className="mt-1 font-mono text-xs text-slate-300">
                          {formatDate(
                            selectedAction.started_at,
                          )}
                        </div>

                      </div>

                    </div>

                  </div>

                </div>

              </div>

            </div>

          )}

        </section>

      </section>


      {/* =====================================================
          CHECKPOINTS
      ===================================================== */}

      <section className="border-b border-slate-800/80 px-8 py-8">

        <div className="flex items-end justify-between">

          <div>

            <div className="text-[10px] font-bold tracking-[0.2em] text-blue-400">
              RECOVERY
            </div>

            <h2 className="mt-2 text-2xl font-black text-white">
              Checkpoints
            </h2>

            <p className="mt-2 text-sm text-slate-600">
              Transactional filesystem recovery
              points created before mutating
              actions.
            </p>

          </div>


          <span className="font-mono text-xs text-slate-600">
            {checkpoints.length} checkpoints
          </span>

        </div>


        {checkpoints.length === 0 ? (

          <div className="mt-5 rounded-xl border border-dashed border-slate-800 bg-[#080e14] p-8 text-center">

            <Database
              size={25}
              className="mx-auto text-slate-700"
            />

            <div className="mt-3 text-sm font-bold text-slate-500">
              No checkpoints found
            </div>

            <div className="mt-1 text-xs text-slate-700">
              Mutating actions create recovery
              points before execution.
            </div>

          </div>

        ) : (

          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">

            {checkpoints.map(
              (
                checkpoint,
              ) => {

                const isExpanded =
                  expandedCheckpoint ===
                  checkpoint.id;

                return (
                  <div
                    key={checkpoint.id}
                    className="rounded-xl border border-slate-800 bg-[#080e14]"
                  >

                    <button
                      onClick={() =>
                        setExpandedCheckpoint(
                          isExpanded
                            ? null
                            : checkpoint.id,
                        )
                      }
                      className="w-full p-5 text-left"
                    >

                      <div className="flex items-center justify-between">

                        <div className="flex items-center gap-3">

                          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-blue-500/20 bg-blue-500/5 font-mono text-xs font-bold text-blue-400">
                            #
                            {
                              checkpoint.sequence
                            }
                          </div>

                          <div>

                            <div className="text-xs font-bold text-slate-300">
                              Checkpoint
                            </div>

                            <div className="mt-1 font-mono text-[9px] text-slate-600">
                              {formatTime(
                                checkpoint.created_at,
                              )}
                            </div>

                          </div>

                        </div>


                        {isExpanded ? (
                          <ChevronDown
                            size={15}
                            className="text-slate-600"
                          />
                        ) : (
                          <ChevronRight
                            size={15}
                            className="text-slate-600"
                          />
                        )}

                      </div>

                    </button>


                    {isExpanded && (
                      <div className="border-t border-slate-800 p-5">

                        <div className="text-[9px] font-bold tracking-wider text-slate-600">
                          SNAPSHOT
                        </div>

                        <div className="mt-2 break-all font-mono text-[10px] text-slate-400">
                          {
                            checkpoint.snapshot_id
                          }
                        </div>


                        <button
                          disabled={acting}
                          onClick={() =>
                            handleRollback(
                              checkpoint,
                            )
                          }
                          className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-2.5 text-xs font-bold text-red-400 transition hover:bg-red-500/10 disabled:opacity-50"
                        >

                          <RotateCcw
                            size={14}
                          />

                          Rollback here

                        </button>

                      </div>
                    )}

                  </div>
                );
              },
            )}

          </div>

        )}

      </section>


      {/* =====================================================
          ROLLBACK HISTORY
      ===================================================== */}

      <section className="px-8 py-8">

        <div className="text-[10px] font-bold tracking-[0.2em] text-blue-400">
          AUDIT TRAIL
        </div>

        <h2 className="mt-2 text-2xl font-black text-white">
          Rollback history
        </h2>


        {rollbackEvents.length === 0 ? (

          <div className="mt-5 rounded-xl border border-slate-800 bg-[#080e14] p-6 text-sm text-slate-600">
            No rollback events yet.
          </div>

        ) : (

          <div className="mt-5 space-y-3">

            {rollbackEvents.map(
              (
                event: RollbackEvent,
              ) => (

                <div
                  key={event.id}
                  className="flex flex-col gap-4 rounded-xl border border-purple-500/20 bg-purple-500/[0.025] p-5 md:flex-row md:items-center"
                >

                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-purple-500/30 bg-purple-500/10">

                    <Undo2
                      size={18}
                      className="text-purple-400"
                    />

                  </div>


                  <div className="min-w-0 flex-1">

                    <div className="flex flex-wrap items-center gap-3">

                      <span className="text-sm font-bold text-slate-200">
                        Filesystem restored
                      </span>

                      <span className="rounded-md border border-purple-500/20 bg-purple-500/5 px-2 py-1 font-mono text-[9px] text-purple-400">
                        {
                          event.trigger
                        }
                      </span>

                    </div>


                    <div className="mt-2 text-xs text-slate-500">
                      {event.reason}
                    </div>


                    <div className="mt-2 font-mono text-[10px] text-slate-700">
                      checkpoint:{" "}
                      {
                        event.checkpoint_id
                      }
                    </div>

                  </div>


                  <div className="shrink-0 font-mono text-[10px] text-slate-600">
                    {formatDate(
                      event.created_at,
                    )}
                  </div>

                </div>

              ),
            )}

          </div>

        )}

      </section>


      {/* =====================================================
          FOOTER
      ===================================================== */}

      <footer className="border-t border-slate-800/80 px-8 py-6">

        <div className="flex flex-col justify-between gap-3 text-[10px] text-slate-700 md:flex-row">

          <div className="font-mono">
            CHECKPOINT · AGENT SAFETY RUNTIME
          </div>

          <div className="flex items-center gap-4">

            <span>
              ACTIONS ARE INTERCEPTED
            </span>

            <span>
              →
            </span>

            <span>
              RISK EVALUATED
            </span>

            <span>
              →
            </span>

            <span>
              RECOVERY AVAILABLE
            </span>

          </div>

        </div>

      </footer>

    </main>
  );
}