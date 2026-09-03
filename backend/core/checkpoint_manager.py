"""
Checkpoint manager — the orchestration core.

This is where the architecture-review fix lives: risk is assessed BEFORE
execution (static, on the proposed action) so DANGEROUS actions can be
blocked without ever touching the sandbox, and AGAIN after execution
(diff-based) to catch damage that couldn't have been predicted statically.

Flow per action:

    1. pre-execution risk check (rules.py, no diff)
       -> DANGEROUS: BLOCK. Never touches the runtime. Action status =
          BLOCKED, findings stored, no snapshot needed.
       -> SAFE/SUSPICIOUS: continue.

    2. risk-based checkpointing: decide whether this action type
       warrants a snapshot before it runs (reads/lists: no; writes/
       moves/deletes/shell: yes).

    3. execute the action against the runtime.

    4. diff before/after.

    5. post-execution risk check (rules.py, with diff).
       -> DANGEROUS: action already ran — this is now a candidate for
          rollback, not a block. Caller decides (auto-rollback or
          surface for human approval) via the returned RiskResult.
       -> otherwise: mark COMPLETED.

The execution layer also validates shell-command exit codes so a command
that fails inside the runtime is never silently recorded as successful.
"""

from __future__ import annotations

from backend.core import diff_engine
from backend.db import repositories as repo
from backend.models.schemas import (
    ActionStatus,
    ActionType,
    AgentAction,
    Checkpoint,
    RiskResult,
    RiskTier,
    RollbackEvent,
    RollbackTrigger,
    RuntimeType,
    Session,
)
from backend.risk import engine as risk_engine
from backend.runtimes.solari_sandbox import (
    SandboxRuntime,
    get_runtime,
)


# Action types that don't warrant a snapshot:
# nothing destructive can come from reading.
#
# Everything else gets checkpointed.
NO_SNAPSHOT_TYPES = {
    ActionType.FILE_READ
}


class ActionBlocked(Exception):
    """Raised when a pre-execution check blocks the action."""

    def __init__(self, risk: RiskResult):
        self.risk = risk
        super().__init__(
            f"Action blocked, risk={risk.score}"
        )


class CheckpointManager:

    def __init__(self, task_description: str = ""):
        self.task_description = task_description
        self.runtime: SandboxRuntime | None = None
        self.session: Session | None = None

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(self, agent_id: str) -> Session:
        self.runtime = get_runtime()

        handle = self.runtime.boot()

        session = Session(
            agent_id=agent_id,
            runtime=RuntimeType.SOLARI_SANDBOX,
            runtime_handle=handle,
        )

        repo.create_session(session)

        self.session = session

        # Checkpoint #0:
        # Initial state is always taken so rollback-to-start is possible.
        self._checkpoint(
            note="Initial state"
        )

        return session

    def end_session(
        self,
        status_ok: bool = True,
    ) -> None:

        from datetime import datetime, timezone
        from backend.models.schemas import SessionStatus

        assert self.session is not None

        self.session.status = (
            SessionStatus.COMPLETED
            if status_ok
            else SessionStatus.FAILED
        )

        self.session.ended_at = datetime.now(
            timezone.utc
        )

        repo.update_session(
            self.session
        )

        if self.runtime:
            self.runtime.teardown()

    # ------------------------------------------------------------------
    # Checkpointing
    # ------------------------------------------------------------------

    def _checkpoint(
        self,
        note: str = "",
    ) -> Checkpoint:

        assert (
            self.session is not None
            and self.runtime is not None
        )

        snap_id = self.runtime.snapshot(
            note=note
        )

        seq = repo.next_checkpoint_sequence(
            self.session.id
        )

        cp = Checkpoint(
            session_id=self.session.id,
            sequence=seq,
            snapshot_id=snap_id,
            note=note,
        )

        repo.create_checkpoint(cp)

        return cp

    # ------------------------------------------------------------------
    # Main action entry point
    # ------------------------------------------------------------------

    def submit_action(
        self,
        type: ActionType,
        intent: str,
        target: str | None = None,
        parameters: dict | None = None,
    ) -> AgentAction:

        assert (
            self.session is not None
            and self.runtime is not None
        )

        action = AgentAction(
            session_id=self.session.id,
            type=type,
            intent=intent,
            target=target,
            parameters=parameters or {},
        )

        repo.create_action(
            action
        )

        # --------------------------------------------------------------
        # STEP 1
        # Pre-execution risk check
        # --------------------------------------------------------------

        pre_risk = (
            risk_engine.assess_pre_execution(
                action,
                self.task_description,
            )
        )

        if pre_risk.tier == RiskTier.DANGEROUS:

            action.status = (
                ActionStatus.BLOCKED
            )

            action.risk_score = (
                pre_risk.score
            )

            repo.update_action(
                action
            )

            repo.create_findings(
                pre_risk.findings
            )

            # BLOCKED:
            # runtime was never touched.
            return action

        # --------------------------------------------------------------
        # STEP 2
        # Risk-based checkpointing
        # --------------------------------------------------------------

        checkpoint = None

        if type not in NO_SNAPSHOT_TYPES:

            checkpoint = self._checkpoint(
                note=f"Before: {intent}"
            )

            action.checkpoint_id = (
                checkpoint.id
            )

        # --------------------------------------------------------------
        # STEP 3
        # Execute
        # --------------------------------------------------------------

        before_tree = (
            diff_engine.snapshot_tree(
                self.runtime.root_path()
            )
        )

        self._execute(
            action
        )

        # --------------------------------------------------------------
        # STEP 4
        # Filesystem diff
        # --------------------------------------------------------------

        after_tree = (
            diff_engine.snapshot_tree(
                self.runtime.root_path()
            )
        )

        diff = (
            diff_engine.diff_trees(
                before_tree,
                after_tree,
                self.runtime.root_path(),
            )
        )

        action.diff = diff

        # --------------------------------------------------------------
        # STEP 5
        # Post-execution risk check
        # --------------------------------------------------------------

        post_risk = (
            risk_engine.assess_post_execution(
                action,
                diff,
                self.task_description,
            )
        )

        action.risk_score = max(
            pre_risk.score,
            post_risk.score,
        )

        repo.create_findings(
            post_risk.findings
        )

        if post_risk.tier == RiskTier.DANGEROUS:

            # The action already happened.
            #
            # Therefore we DO NOT block it here.
            # We pause it and allow the human approval/rejection
            # path to decide whether to roll back.
            action.status = (
                ActionStatus.PAUSED
            )

        else:

            action.status = (
                ActionStatus.COMPLETED
            )

        action.completed_at = _now()

        repo.update_action(
            action
        )

        return action

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def _execute(
        self,
        action: AgentAction,
    ) -> None:

        assert self.runtime is not None

        if action.type == ActionType.FILE_WRITE:

            self.runtime.write_file(
                action.target,
                action.parameters.get(
                    "content",
                    "",
                ),
            )

        elif action.type == ActionType.FILE_DELETE:

            self.runtime.delete_path(
                action.target
            )

        elif action.type == ActionType.FILE_MOVE:

            self.runtime.move_path(
                action.target,
                action.parameters[
                    "destination"
                ],
            )

        elif action.type == ActionType.DIR_CREATE:

            self.runtime.make_dir(
                action.target
            )

        elif action.type == ActionType.SHELL_EXECUTE:

            command = action.parameters.get(
                "command",
                "",
            )

            # Always execute through sh so the command behaves
            # consistently for both the local fallback and Solari.
            result = self.runtime.run_command(
                "sh",
                [
                    "-c",
                    command,
                ],
            )

            # ----------------------------------------------------------
            # IMPORTANT:
            #
            # Never silently treat a failed shell command as successful.
            #
            # Different runtime implementations may expose the exit
            # code under slightly different result shapes, so handle
            # both dictionary-style and object-style responses.
            # ----------------------------------------------------------

            if isinstance(result, dict):

                exit_code = result.get(
                    "exit_code"
                )

                stderr = result.get(
                    "stderr",
                    "",
                )

                stdout = result.get(
                    "stdout",
                    "",
                )

            else:

                exit_code = getattr(
                    result,
                    "exit_code",
                    None,
                )

                stderr = getattr(
                    result,
                    "stderr",
                    "",
                )

                stdout = getattr(
                    result,
                    "stdout",
                    "",
                )

            if exit_code not in (
                0,
                None,
            ):

                raise RuntimeError(
                    "Shell command failed "
                    f"with exit code {exit_code}. "
                    f"stdout={stdout!r} "
                    f"stderr={stderr!r}"
                )

        elif action.type == ActionType.FILE_READ:

            # Reading does not mutate filesystem state.
            pass

        else:

            raise ValueError(
                f"Unsupported action type: "
                f"{action.type}"
            )

    # ------------------------------------------------------------------
    # Human approval path
    # ------------------------------------------------------------------

    def approve_action(
        self,
        action_id: str,
    ) -> AgentAction:

        action = repo.get_action(
            action_id
        )

        assert action is not None

        action.status = (
            ActionStatus.APPROVED
        )

        repo.update_action(
            action
        )

        return action

    def reject_action(
        self,
        action_id: str,
        rollback: bool = True,
    ) -> AgentAction:

        action = repo.get_action(
            action_id
        )

        assert action is not None

        action.status = (
            ActionStatus.REJECTED
        )

        repo.update_action(
            action
        )

        if (
            rollback
            and action.checkpoint_id
        ):

            self.rollback(
                action.checkpoint_id,
                reason=(
                    f"Rejected action "
                    f"{action.id}"
                ),
                trigger=(
                    RollbackTrigger.MANUAL
                ),
            )

        return action

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def rollback(
        self,
        checkpoint_id: str,
        reason: str,
        trigger: RollbackTrigger = (
            RollbackTrigger.MANUAL
        ),
    ) -> RollbackEvent:

        assert (
            self.session is not None
            and self.runtime is not None
        )

        checkpoint = repo.get_checkpoint(
            checkpoint_id
        )

        assert checkpoint is not None

        self.runtime.restore(
            checkpoint.snapshot_id
        )

        event = RollbackEvent(
            session_id=self.session.id,
            checkpoint_id=checkpoint_id,
            trigger=trigger,
            reason=reason,
        )

        repo.create_rollback_event(
            event
        )

        return event


def _now():
    from datetime import datetime, timezone

    return datetime.now(
        timezone.utc
    )