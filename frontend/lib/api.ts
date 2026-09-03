export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";


// ============================================================
// TYPES
// ============================================================

export type Session = {
  id: string;
  agent_id: string;
  runtime: string;
  status: string;
  started_at: string;
  ended_at?: string | null;
  runtime_handle?: string | null;
};

export type RiskFinding = {
  id: string;
  action_id: string;
  rule: string;
  severity: number;
  message: string;
  confidence: number;
};

export type DiffEntry = {
  path: string;
  change: string;
  before_preview?: string | null;
  after_preview?: string | null;
};

export type DiffResult = {
  files_added: string[];
  files_removed: string[];
  files_modified: string[];
  entries: DiffEntry[];
};

export type Action = {
  id: string;
  session_id: string;

  checkpoint_id?: string | null;

  type: string;
  intent: string;
  target?: string | null;

  parameters: Record<string, unknown>;

  reversible: boolean;

  status: string;
  risk_score: number;

  started_at: string;
  completed_at?: string | null;

  diff?: DiffResult | null;
};

export type TimelineAction = {
  action: Action;
  findings: RiskFinding[];
};

export type Checkpoint = {
  id: string;
  session_id: string;

  sequence: number;
  snapshot_id: string;

  created_at: string;

  note?: string | null;
};

export type RollbackEvent = {
  id: string;
  session_id: string;

  checkpoint_id: string;

  trigger: string;
  reason: string;

  created_at: string;
};

export type TimelineSummary = {
  total_actions: number;
  total_checkpoints: number;
  blocked_actions: number;
  rollbacks: number;
};

export type TimelineResponse = {
  session_id: string;

  actions: TimelineAction[];

  checkpoints: Checkpoint[];

  rollback_events: RollbackEvent[];

  summary: TimelineSummary;
};


// ============================================================
// GENERIC REQUEST
// ============================================================

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,

    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },

    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();

    throw new Error(
      `${response.status}: ${text || response.statusText}`,
    );
  }

  return response.json();
}


// ============================================================
// HEALTH
// ============================================================

export async function getHealth() {
  return request<{ status: string }>("/api/health");
}


// ============================================================
// SESSIONS
// ============================================================

export async function getSession(
  sessionId: string,
) {
  return request<Session>(
    `/api/sessions/${encodeURIComponent(sessionId)}`,
  );
}


export async function startSession(
  agentId: string,
  taskDescription: string,
) {
  return request<Session>("/api/sessions", {
    method: "POST",

    body: JSON.stringify({
      agent_id: agentId,
      task_description: taskDescription,
    }),
  });
}


export async function endSession(
  sessionId: string,
) {
  return request<{ status: string }>(
    `/api/sessions/${encodeURIComponent(sessionId)}/end?status_ok=true`,
    {
      method: "POST",
    },
  );
}


// ============================================================
// TIMELINE
// ============================================================

export async function getTimeline(
  sessionId: string,
) {
  return request<TimelineResponse>(
    `/api/sessions/${encodeURIComponent(sessionId)}/timeline`,
  );
}


// ============================================================
// CHECKPOINTS
// ============================================================

export async function getCheckpoints(
  sessionId: string,
) {
  return request<Checkpoint[]>(
    `/api/sessions/${encodeURIComponent(sessionId)}/checkpoints`,
  );
}


export async function getCheckpoint(
  checkpointId: string,
) {
  return request<Checkpoint>(
    `/api/sessions/checkpoints/${encodeURIComponent(checkpointId)}`,
  );
}


// ============================================================
// ACTIONS
// ============================================================

export async function getAction(
  actionId: string,
) {
  return request<Action>(
    `/api/actions/${encodeURIComponent(actionId)}`,
  );
}


export async function getActionRisk(
  actionId: string,
) {
  return request<{
    action_id: string;
    risk_score: number;
    status: string;
    findings: RiskFinding[];
  }>(
    `/api/actions/${encodeURIComponent(actionId)}/risk`,
  );
}


// ============================================================
// APPROVAL
// ============================================================

export async function approveAction(
  actionId: string,
) {
  return request<Action>(
    `/api/actions/${encodeURIComponent(actionId)}/approve`,
    {
      method: "POST",
    },
  );
}


// ============================================================
// REJECTION
// ============================================================

export async function rejectAction(
  actionId: string,
  rollback = true,
) {
  return request<Action>(
    `/api/actions/${encodeURIComponent(actionId)}/reject?rollback=${rollback}`,
    {
      method: "POST",
    },
  );
}


// ============================================================
// MANUAL ROLLBACK
// ============================================================

export async function rollbackToCheckpoint(
  sessionId: string,
  checkpointId: string,
  reason = "Manual rollback requested from Checkpoint UI",
) {
  return request<RollbackEvent>(
    `/api/sessions/${encodeURIComponent(
      sessionId,
    )}/rollback/${encodeURIComponent(checkpointId)}`,
    {
      method: "POST",

      body: JSON.stringify({
        reason,
      }),
    },
  );
}