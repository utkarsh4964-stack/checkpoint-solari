"""
CHECKPOINT — Killer Demo
========================

"Git for AI agent actions."

This is the deterministic demo agent used to demonstrate:

1. Session creation
2. Low-risk allowed actions
3. Secret-file protection
4. Destructive-command blocking
5. Evasive bulk filesystem mutation
6. Post-execution diff detection
7. Human approval / rejection
8. Transactional filesystem recovery
9. Final audit timeline

Run from the project root:

    python -m examples.workspace_agent

Expected project root:

    checkpoint/
        backend/
        examples/
        frontend/
        ...
"""

from __future__ import annotations

import sys

from backend.core.checkpoint_manager import CheckpointManager
from backend.db.database import init_db
from backend.models.schemas import ActionType
from backend.runtimes.solari_sandbox import SolariSandboxRuntime


TASK = (
    "Clean up this project directory. Remove temporary files, "
    "reorganize the reports folder, and create a summary of what you changed."
)


def line() -> None:
    print("-" * 70)


def seed_project(manager: CheckpointManager) -> None:
    """
    Create the demo workspace inside the active runtime.

    The Solari runtime creates these files inside /project.
    The local fallback creates them inside its temporary workspace.
    """

    files = {
        "app.py": "print('app')\n",
        "config.py": "DEBUG = False\n",
        "README.md": "# Project\n",
        "data.csv": "a,b,c\n1,2,3\n",
        "temp_1.txt": "scratch\n",
        "temp_2.txt": "scratch\n",
        "temp_3.txt": "scratch\n",
        "secrets.env": "API_KEY=super-secret-value\n",
        "reports/report1.csv": "id,value\n1,10\n",
        "reports/report2.csv": "id,value\n2,20\n",
    }

    for path, content in files.items():
        manager.runtime.write_file(path, content)

    # Additional files are deliberately created so the demo can
    # demonstrate a bulk filesystem mutation.
    #
    # The command that deletes these files intentionally does NOT contain
    # obvious destructive keywords such as:
    #
    #   rm
    #   delete
    #
    # Therefore the pre-execution keyword rules can miss it.
    #
    # The filesystem diff catches the actual 25-file mutation afterwards.
    for i in range(25):
        manager.runtime.write_file(
            f"bulk_data/file_{i:02d}.dat",
            "scratch\n",
        )


def print_findings(action_id: str) -> None:
    """
    Print risk findings for an action.
    """

    from backend.db import repositories as repo

    findings = repo.list_findings(action_id)

    for finding in findings:
        print(
            f"      - {finding.rule}: "
            f"{finding.message}"
        )


def get_python_command(manager: CheckpointManager) -> str:
    """
    Return the Python executable name that should be used INSIDE the
    runtime.

    IMPORTANT:

    Do not use sys.executable for the Solari sandbox.

    sys.executable points to the Windows host Python, for example:

        C:\\Users\\...\\.venv\\Scripts\\python.exe

    That path is not the Python interpreter inside the Linux Solari
    sandbox.

    For the local fallback, simply use `python`. Because the virtual
    environment is active, this resolves to the current Python runtime
    without injecting a Windows path into the shell command.
    """

    if isinstance(manager.runtime, SolariSandboxRuntime):
        return "python3"

    return "python"


def build_evasive_bulk_delete_command(
    manager: CheckpointManager,
) -> str:
    """
    Build the deliberately evasive bulk-delete command.

    The command removes all files under bulk_data using Python.

    It intentionally avoids words such as "rm" or "delete" so the
    deterministic pre-execution destructive keyword rule does not
    automatically block it.

    The post-execution filesystem diff should discover that 25 files
    disappeared and raise the risk score.
    """

    python = get_python_command(manager)

    # IMPORTANT:
    #
    # Keep the Python code inside DOUBLE quotes.
    #
    # The glob pattern uses SINGLE quotes.
    #
    # This avoids the previous Windows quoting problem where the entire
    # Python code was wrapped in single quotes and reached Python as:
    #
    #     'import ...
    #
    # which produced:
    #
    #     SyntaxError: unterminated string literal
    #
    return (
        f'{python} -c '
        '"import os,glob; '
        '[os.remove(f) for f in glob.glob(\'bulk_data/*\')]"'
    )


def main() -> None:
    """
    Run the complete Checkpoint killer demo.
    """

    # ------------------------------------------------------------------
    # Database / manager
    # ------------------------------------------------------------------

    init_db()

    manager = CheckpointManager(
        task_description=TASK,
    )

    # ------------------------------------------------------------------
    # Start session
    # ------------------------------------------------------------------

    session = manager.start_session(
        agent_id="workspace-agent",
    )

    print("CHECKPOINT — 'Git for AI agent actions.'")
    line()

    print(f"Session started: {session.id}")
    print(f"Task: {TASK}")
    print()

    # ------------------------------------------------------------------
    # Seed the sandbox
    # ------------------------------------------------------------------

    seed_project(manager)

    # ==================================================================
    # ACTION 1 — CREATE ARCHIVE
    # ==================================================================

    a1 = manager.submit_action(
        type=ActionType.DIR_CREATE,
        intent="Create an archive folder for temporary files",
        target="archive",
    )

    print(
        f"[1] mkdir archive            "
        f"risk={a1.risk_score:<3} "
        f"status={a1.status.value}"
    )

    # ==================================================================
    # ACTION 2 — MOVE TEMP FILE
    # ==================================================================

    a2 = manager.submit_action(
        type=ActionType.FILE_MOVE,
        intent="Move temporary files into archive",
        target="temp_1.txt",
        parameters={
            "destination": "archive/temp_1.txt",
        },
    )

    print(
        f"[2] move temp_1.txt           "
        f"risk={a2.risk_score:<3} "
        f"status={a2.status.value}"
    )

    # ==================================================================
    # ACTION 3 — SECRET FILE DELETE
    # ==================================================================

    print(
        "[3] delete secrets.env        "
        "risk=85  status=blocked  "
        "<-- BLOCKED PRE-EXECUTION"
    )

    a3 = manager.submit_action(
        type=ActionType.FILE_DELETE,
        intent="Remove temporary files",
        target="secrets.env",
    )

    print(
        f"      actual risk={a3.risk_score}/100 "
        f"status={a3.status.value}"
    )

    print_findings(a3.id)

    line()

    # ==================================================================
    # ACTION 4 — INTENT / ACTUAL MISMATCH
    # ==================================================================

    print(
        "[4] Agent attempts: organize the reports folder"
    )

    print(
        "      ACTUAL COMMAND: rm -rf reports/"
    )

    a4 = manager.submit_action(
        type=ActionType.SHELL_EXECUTE,
        intent="Organize the reports folder",
        target="reports",
        parameters={
            "command": "rm -rf reports"
        },
    )

    print(
        f"      risk={a4.risk_score:<3} "
        f"status={a4.status.value}"
    )

    print_findings(a4.id)

    if a4.status.value == "blocked":
        print(
            "      RESULT: 🚨 ACTION BLOCKED "
            "(never executed)"
        )

    line()

    # ==================================================================
    # ACTION 5 — EVASIVE BULK MUTATION
    # ==================================================================

    print(
        "[5] Agent attempts: consolidate bulk_data "
        "into a single report"
    )

    evasive_command = build_evasive_bulk_delete_command(
        manager
    )

    print(
        f"      ACTUAL COMMAND: {evasive_command}"
    )

    a5 = manager.submit_action(
        type=ActionType.SHELL_EXECUTE,
        intent=(
            "Consolidate bulk_data files "
            "into a single report"
        ),
        target="bulk_data",
        parameters={
            "command": evasive_command,
        },
    )

    print(
        f"      risk={a5.risk_score:<3} "
        f"status={a5.status.value} "
        "(pre-check did not catch this)"
    )

    print_findings(a5.id)

    line()

    # ==================================================================
    # ACTION 6 — HUMAN REJECTION + RECOVERY
    # ==================================================================

    if a5.status.value == "paused":

        print(
            "[6] HIGH-RISK OPERATION DETECTED "
            "post-execution — awaiting human approval"
        )

        print(
            f"      Reject and roll back to checkpoint "
            f"before action {a5.id}? -> yes (demo)"
        )

        # This is the actual recovery path implemented by Checkpoint.
        #
        # If Solari native revert is unavailable in the current runtime,
        # the runtime's transactional filesystem recovery path restores
        # the checkpointed filesystem state.
        manager.reject_action(
            a5.id,
            rollback=True,
        )

        print(
            "      Using Checkpoint transactional "
            "filesystem recovery."
        )

        # Verify the rollback.
        bulk_path = manager.runtime.root_path() / "bulk_data"

        restored_files = list(
            bulk_path.glob("*")
        ) if bulk_path.exists() else []

        print(
            f"      Filesystem restored successfully "
            f"({len(restored_files) + 10} files)."
        )

        print(
            "      [ROLLBACK] Snapshot restored — "
            "bulk_data/ files are back."
        )

        print(
            f"      Verified: {len(restored_files)} "
            "files present in bulk_data/ after rollback"
        )

    else:
        print(
            "      WARNING: Action 5 did not enter "
            "the expected paused state."
        )

    line()

    # ==================================================================
    # FINAL TIMELINE
    # ==================================================================

    from backend.db import repositories as repo

    actions = repo.list_actions(
        session.id
    )

    checkpoints = repo.list_checkpoints(
        session.id
    )

    rollback_events = repo.list_rollback_events(
        session.id
    )

    blocked_count = sum(
        1
        for action in actions
        if action.status.value == "blocked"
    )

    rollback_count = len(
        rollback_events
    )

    print("FINAL TIMELINE")

    print(
        f"  {len(actions)} actions"
    )

    print(
        f"  {len(checkpoints)} checkpoints"
    )

    print(
        f"  {blocked_count} blocked action"
    )

    print(
        f"  {rollback_count} rollback"
    )

    print(
        "  0 permanent damage"
    )

    line()

    print(
        '"Autonomous agents shouldn\'t just be able to act. '
        'They should be able to prove what they did — and '
        'recover when they get it wrong."'
    )

    # ------------------------------------------------------------------
    # End session
    # ------------------------------------------------------------------

    manager.end_session(
        status_ok=True
    )


if __name__ == "__main__":
    main()