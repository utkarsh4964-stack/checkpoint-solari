# Checkpoint — 90-second demo

## 0–10s — What it is

Show the title screen:

> **Checkpoint — Git for AI agent actions.**

Say:

> Autonomous agents can take real actions. Checkpoint adds a safety and recovery layer around those actions.

## 10–25s — Agent in Solari

Start the Workspace Agent and show the Solari sandbox/project files.

Task:

> Clean up this project directory. Remove temporary files, organize the reports folder, and create a summary of what you changed.

Show the timeline updating.

## 25–45s — Prevention

Show the agent attempting:

```text
Intent: Organize the reports folder
Actual: rm -rf reports
```

Checkpoint should show:

```text
RISK: 75+/100
Destructive operation
Scope violation / intent mismatch
BLOCKED
```

Then show `secrets.env` deletion being blocked before execution.

## 45–70s — Detection after execution

Trigger the separate bulk-delete scenario.

Show:

```text
25 files removed
↓
Filesystem diff
↓
Bulk modification detected
↓
RISK: 80/100
↓
PAUSED — human review required
```

## 70–85s — Recovery

Click **Reject & Roll Back**.

Show the Solari sandbox returning to the previous checkpoint and verify the 25 files are back.

Say:

> The rollback is not a fake copy-back. Checkpoint calls Solari's real snapshot revert.

## 85–90s — Close

Show the final timeline.

Say:

> Autonomous agents shouldn't just be able to act. They should be able to prove what they did — and recover when they get it wrong.
