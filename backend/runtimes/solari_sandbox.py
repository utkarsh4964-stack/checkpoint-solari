"""
Checkpoint runtime adapters.

This module provides two runtime implementations behind one interface:

1. SolariSandboxRuntime
   - Runs the agent inside a real Solari Sandbox.
   - Uses the Solari Python SDK.
   - Maintains a local mirror of /project for Checkpoint's filesystem
     diff engine.
   - Creates real Solari snapshots at checkpoint time.
   - Uses Checkpoint's transactional filesystem mirror for recovery.

2. LocalFallbackRuntime
   - Cross-platform local runtime for development/testing.
   - Does not require a Solari API key.

The rest of Checkpoint does not need to know which runtime is active.
"""

from __future__ import annotations

import base64
import json
import os
import posixpath
import shutil
import subprocess
import tempfile
import threading
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


# ============================================================================
# BASE RUNTIME
# ============================================================================


class SandboxRuntime(ABC):
    """Small runtime interface consumed by Checkpoint."""

    @abstractmethod
    def boot(self) -> str:
        """Start the runtime and return its handle."""

    @abstractmethod
    def run_command(
        self,
        command: str,
        args: list[str] | None = None,
    ) -> dict:
        """Execute a command and return exit_code/stdout/stderr."""

    @abstractmethod
    def write_file(
        self,
        path: str,
        content: str,
    ) -> None:
        """Write a file."""

    @abstractmethod
    def delete_path(self, path: str) -> None:
        """Delete a file or directory."""

    @abstractmethod
    def move_path(
        self,
        src: str,
        dst: str,
    ) -> None:
        """Move a file or directory."""

    @abstractmethod
    def make_dir(self, path: str) -> None:
        """Create a directory."""

    @abstractmethod
    def snapshot(self, note: str = "") -> str:
        """Create a checkpoint and return its ID."""

    @abstractmethod
    def restore(self, snapshot_id: str) -> None:
        """Restore a previous checkpoint."""

    @abstractmethod
    def root_path(self) -> Path:
        """Return the local filesystem root used by the diff engine."""

    @abstractmethod
    def teardown(self) -> None:
        """Clean up runtime resources."""


# ============================================================================
# LOCAL FALLBACK RUNTIME
# ============================================================================


class LocalFallbackRuntime(SandboxRuntime):
    """
    Local filesystem implementation.

    This is useful when SOLARI_API_KEY is not configured.

    Snapshots are copied into a temporary snapshot directory.
    """

    def __init__(self, workdir: Optional[Path] = None):
        base = Path(tempfile.gettempdir())

        self._workdir = (
            workdir
            or base / f"checkpoint_sandbox_{uuid.uuid4().hex[:8]}"
        )

        self._snapshot_dir = (
            self._workdir.parent
            / f"{self._workdir.name}_snapshots"
        )

        self._handle = f"local_{uuid.uuid4().hex[:8]}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def boot(self) -> str:
        self._workdir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._snapshot_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        return self._handle

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def run_command(
        self,
        command: str,
        args: list[str] | None = None,
    ) -> dict:
        """
        Execute a command locally.

        Internal shell convention:

            run_command("sh", ["-c", "rm -rf reports"])

        On Windows this uses cmd.exe through shell=True.
        On Unix it uses the system shell.
        """

        # Shell command convention.
        if command == "sh" and args and args[0] == "-c":
            actual_command = args[1] if len(args) > 1 else ""

            try:
                proc = subprocess.run(
                    actual_command,
                    cwd=self._workdir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=True,
                )

                return {
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                }

            except subprocess.TimeoutExpired:
                return {
                    "exit_code": 124,
                    "stdout": "",
                    "stderr": "command timed out",
                }

        # Direct binary invocation.
        full_args = [
            command,
            *(args or []),
        ]

        try:
            proc = subprocess.run(
                full_args,
                cwd=self._workdir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            return {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }

        except FileNotFoundError as exc:
            return {
                "exit_code": 127,
                "stdout": "",
                "stderr": str(exc),
            }

        except subprocess.TimeoutExpired:
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": "command timed out",
            }

    # ------------------------------------------------------------------
    # Filesystem
    # ------------------------------------------------------------------

    def write_file(
        self,
        path: str,
        content: str,
    ) -> None:
        full = self._workdir / path

        full.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        full.write_text(
            content,
            encoding="utf-8",
        )

    def delete_path(self, path: str) -> None:
        full = self._workdir / path

        if full.is_dir():
            shutil.rmtree(
                full,
                ignore_errors=True,
            )

        elif full.exists():
            full.unlink()

    def move_path(
        self,
        src: str,
        dst: str,
    ) -> None:
        full_src = self._workdir / src
        full_dst = self._workdir / dst

        full_dst.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.move(
            str(full_src),
            str(full_dst),
        )

    def make_dir(self, path: str) -> None:
        (
            self._workdir / path
        ).mkdir(
            parents=True,
            exist_ok=True,
        )

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def snapshot(self, note: str = "") -> str:
        snapshot_id = (
            f"snap_{uuid.uuid4().hex[:10]}"
        )

        destination = (
            self._snapshot_dir / snapshot_id
        )

        shutil.copytree(
            self._workdir,
            destination,
        )

        return snapshot_id

    def restore(self, snapshot_id: str) -> None:
        source = (
            self._snapshot_dir / snapshot_id
        )

        if not source.exists():
            raise ValueError(
                f"Unknown snapshot: {snapshot_id}"
            )

        if self._workdir.exists():
            shutil.rmtree(
                self._workdir,
                ignore_errors=True,
            )

        shutil.copytree(
            source,
            self._workdir,
        )

    # ------------------------------------------------------------------
    # Diff root
    # ------------------------------------------------------------------

    def root_path(self) -> Path:
        return self._workdir

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def teardown(self) -> None:
        shutil.rmtree(
            self._workdir,
            ignore_errors=True,
        )

        shutil.rmtree(
            self._snapshot_dir,
            ignore_errors=True,
        )


# ============================================================================
# SOLARI SANDBOX RUNTIME
# ============================================================================


class SolariSandboxRuntime(SandboxRuntime):
    """
    Real Solari-backed runtime.

    Important implementation details:

    - Solari's Python SDK is asynchronous.
    - Checkpoint's manager is synchronous.
    - A dedicated asyncio event-loop thread therefore owns the Solari
      client/sandbox connection for the lifetime of this runtime.

    Remote filesystem:

        Solari Sandbox
             |
             +---- /project
                       |
                       v
                 local mirror

    The local mirror exists because Checkpoint's existing diff engine
    expects a pathlib.Path.

    Recovery:

        checkpoint
            |
            +---- real Solari snapshot
            |
            +---- local filesystem mirror

    The real Solari snapshot is created and retained.

    However, the current Solari environment used by this project has
    returned "Not revertable" from the native revert endpoint. Native
    revert can also leave the WebSocket control channel disconnected.

    Therefore restore() deliberately uses the Checkpoint filesystem
    checkpoint mirror instead of attempting native Sandbox.revert().

    This gives the MVP deterministic transactional filesystem recovery
    without depending on the failing native revert connection.

    Honest product claim:

        "Checkpoint provides transactional recovery for supported runtimes."

    Do NOT claim that Checkpoint can rollback arbitrary external/browser
    state.
    """

    BASE_URL = "https://api.getsolari.com"

    PROJECT_ROOT = "/project"

    def __init__(
        self,
        api_key: Optional[str] = None,
        template: str = "base",
    ):
        self._api_key = (
            api_key
            or os.environ.get("SOLARI_API_KEY")
        )

        if not self._api_key:
            raise RuntimeError(
                "SOLARI_API_KEY is required for SolariSandboxRuntime."
            )

        self._template = template

        # Created during boot.
        self._sandbox = None
        self._client = None

        # Dedicated async event loop.
        self._loop = None
        self._loop_thread = None

        # Local mirror used by Checkpoint's diff engine.
        self._mirror = Path(
            tempfile.mkdtemp(
                prefix="checkpoint_solari_mirror_"
            )
        )

        # Local copies of the filesystem at each checkpoint.
        #
        # {
        #     "snap_xxx": Path(...)
        # }
        #
        # These are NOT used for executing agent actions.
        # They are used exclusively for transactional filesystem recovery.
        self._checkpoint_mirrors: dict[str, Path] = {}

        self._booted = False

    # ==================================================================
    # ASYNC BRIDGE
    # ==================================================================

    def _ensure_loop(self) -> None:
        """
        Start the dedicated asyncio event loop.

        The Solari sandbox and its transport stay attached to this loop.
        """

        if (
            self._loop is not None
            and self._loop.is_running()
        ):
            return

        ready = threading.Event()

        def runner() -> None:
            import asyncio

            loop = asyncio.new_event_loop()

            asyncio.set_event_loop(loop)

            self._loop = loop

            ready.set()

            loop.run_forever()

            loop.close()

        self._loop_thread = threading.Thread(
            target=runner,
            name="checkpoint-solari-loop",
            daemon=True,
        )

        self._loop_thread.start()

        if not ready.wait(timeout=5):
            raise RuntimeError(
                "Timed out starting Solari event loop."
            )

        if self._loop is None:
            raise RuntimeError(
                "Failed to start Solari event loop."
            )

    def _run_async(self, coro):
        """
        Execute a coroutine on the dedicated Solari event loop.
        """

        import asyncio

        self._ensure_loop()

        future = asyncio.run_coroutine_threadsafe(
            coro,
            self._loop,
        )

        return future.result()

    # ==================================================================
    # SOLARI CLIENT CONFIG
    # ==================================================================

    def _client_options(self) -> dict:
        return {
            "api_key": self._api_key,
            "base_url": os.environ.get(
                "SOLARI_BASE_URL",
                self.BASE_URL,
            ),
        }

    # ==================================================================
    # BOOT
    # ==================================================================

    def boot(self) -> str:
        """
        Create and connect a real Solari sandbox.

        /project is explicitly created inside the sandbox because the
        base template does not necessarily contain it.
        """

        if self._booted and self._sandbox is not None:
            return self._sandbox_id()

        from solari_sandbox import SandboxClient

        async def _boot():
            client = SandboxClient(
                **self._client_options()
            )

            sandbox = await client.create(
                template=self._template,
                timeout_ms=15 * 60 * 1000,
            )

            await sandbox.connect()

            # The base sandbox does not guarantee /project exists.
            # Create it from the root directory.
            result = await sandbox.commands.run(
                "mkdir",
                args=[
                    "-p",
                    self.PROJECT_ROOT,
                ],
                cwd="/",
            )

            exit_code = getattr(
                result,
                "exitCode",
                getattr(
                    result,
                    "exit_code",
                    None,
                ),
            )

            if exit_code not in (0, None):
                stderr = getattr(
                    result,
                    "stderr",
                    "",
                )

                raise RuntimeError(
                    "Failed to create Solari project root: "
                    + str(stderr)
                )

            return client, sandbox

        self._client, self._sandbox = (
            self._run_async(_boot())
        )

        self._booted = True

        return self._sandbox_id()

    # ==================================================================
    # SANDBOX ID
    # ==================================================================

    def _sandbox_id(self) -> str:
        if self._sandbox is None:
            return "unknown"

        return str(
            getattr(
                self._sandbox,
                "sandboxId",
                getattr(
                    self._sandbox,
                    "id",
                    "unknown",
                ),
            )
        )

    # ==================================================================
    # COMMAND EXECUTION
    # ==================================================================

    def run_command(
        self,
        command: str,
        args: list[str] | None = None,
    ) -> dict:
        """
        Execute a command inside /project.

        Solari commands are argv-based and are NOT automatically
        shell-interpreted.

        Therefore:

            run_command("rm", ["-rf", "/project/reports"])

        is preferred for direct commands.

        For a genuine shell expression:

            run_command(
                "sh",
                ["-c", "some shell expression"]
            )
        """

        if self._sandbox is None:
            raise RuntimeError(
                "Solari sandbox is not booted."
            )

        async def _run():
            return await self._sandbox.commands.run(
                command,
                args=args or [],
                cwd=self.PROJECT_ROOT,
            )

        result = self._run_async(_run())

        # Solari SDK 0.2.0 exposes exitCode.
        #
        # Some newer versions/documentation use exit_code.
        exit_code = getattr(
            result,
            "exitCode",
            getattr(
                result,
                "exit_code",
                None,
            ),
        )

        stdout = getattr(
            result,
            "stdout",
            "",
        )

        stderr = getattr(
            result,
            "stderr",
            "",
        )

        return {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        }

    # ==================================================================
    # SAFE REMOTE PATH HANDLING
    # ==================================================================

    def _remote_path(self, path: str) -> str:
        """
        Convert a Checkpoint path into a safe path under /project.

        Examples:

            "app.py"
                -> /project/app.py

            "reports/a.csv"
                -> /project/reports/a.csv

            "/project/app.py"
                -> /project/app.py

        Attempts to escape /project are rejected.
        """

        raw = str(path).replace(
            "\\",
            "/",
        )

        if (
            raw == self.PROJECT_ROOT
            or raw.startswith(
                self.PROJECT_ROOT + "/"
            )
        ):
            candidate = posixpath.normpath(
                raw
            )

        else:
            candidate = posixpath.normpath(
                f"{self.PROJECT_ROOT}/"
                f"{raw.lstrip('/')}"
            )

        if (
            candidate != self.PROJECT_ROOT
            and not candidate.startswith(
                self.PROJECT_ROOT + "/"
            )
        ):
            raise ValueError(
                "Path escapes the Checkpoint "
                f"project root: {path}"
            )

        return candidate

    # ==================================================================
    # WRITE FILE
    # ==================================================================

    def write_file(
        self,
        path: str,
        content: str,
    ) -> None:
        """
        Write a file into the Solari sandbox.

        Uses the Solari SDK's files.write API.
        """

        if self._sandbox is None:
            raise RuntimeError(
                "Solari sandbox is not booted."
            )

        remote = self._remote_path(path)

        parent = remote.rsplit(
            "/",
            1,
        )[0]

        async def _write():
            mkdir_result = (
                await self._sandbox.commands.run(
                    "mkdir",
                    args=[
                        "-p",
                        parent,
                    ],
                    cwd="/",
                )
            )

            mkdir_exit = getattr(
                mkdir_result,
                "exitCode",
                getattr(
                    mkdir_result,
                    "exit_code",
                    None,
                ),
            )

            if mkdir_exit not in (0, None):
                stderr = getattr(
                    mkdir_result,
                    "stderr",
                    "",
                )

                raise RuntimeError(
                    "Failed to create parent directory: "
                    + str(stderr)
                )

            await self._sandbox.files.write(
                remote,
                content,
            )

        self._run_async(_write())

    # ==================================================================
    # DELETE
    # ==================================================================

    def delete_path(
        self,
        path: str,
    ) -> None:
        remote = self._remote_path(path)

        result = self.run_command(
            "rm",
            [
                "-rf",
                remote,
            ],
        )

        if result["exit_code"] not in (
            0,
            None,
        ):
            raise RuntimeError(
                "Solari delete failed: "
                + str(result["stderr"])
            )

    # ==================================================================
    # MOVE
    # ==================================================================

    def move_path(
        self,
        src: str,
        dst: str,
    ) -> None:
        remote_src = self._remote_path(src)
        remote_dst = self._remote_path(dst)

        # Make sure destination parent exists.
        parent = remote_dst.rsplit(
            "/",
            1,
        )[0]

        mkdir_result = self.run_command(
            "mkdir",
            [
                "-p",
                parent,
            ],
        )

        if mkdir_result["exit_code"] not in (
            0,
            None,
        ):
            raise RuntimeError(
                "Failed to create move destination: "
                + str(mkdir_result["stderr"])
            )

        result = self.run_command(
            "mv",
            [
                remote_src,
                remote_dst,
            ],
        )

        if result["exit_code"] not in (
            0,
            None,
        ):
            raise RuntimeError(
                "Solari move failed: "
                + str(result["stderr"])
            )

    # ==================================================================
    # MAKE DIRECTORY
    # ==================================================================

    def make_dir(
        self,
        path: str,
    ) -> None:
        remote = self._remote_path(path)

        result = self.run_command(
            "mkdir",
            [
                "-p",
                remote,
            ],
        )

        if result["exit_code"] not in (
            0,
            None,
        ):
            raise RuntimeError(
                "Solari mkdir failed: "
                + str(result["stderr"])
            )

    # ==================================================================
    # SNAPSHOT
    # ==================================================================

    def snapshot(
        self,
        note: str = "",
    ) -> str:
        """
        Create a real Solari snapshot and a local filesystem checkpoint.

        The Solari snapshot is still created as part of the runtime
        integration.

        The local checkpoint mirror is additionally retained so Checkpoint
        can deterministically recover the /project filesystem even when
        native Solari revert is unavailable.
        """

        if self._sandbox is None:
            raise RuntimeError(
                "Solari sandbox is not booted."
            )

        # First synchronize the current remote filesystem.
        self._sync_mirror()

        # --------------------------------------------------------------
        # Real Solari snapshot
        # --------------------------------------------------------------

        async def _snap():
            return await self._sandbox.snapshot(
                note or "checkpoint"
            )

        solari_snapshot = self._run_async(
            _snap()
        )

        snapshot_id = str(
            getattr(
                solari_snapshot,
                "snapshotId",
                getattr(
                    solari_snapshot,
                    "id",
                    solari_snapshot,
                ),
            )
        )

        # --------------------------------------------------------------
        # Local transactional filesystem checkpoint
        # --------------------------------------------------------------

        checkpoint_dir = Path(
            tempfile.mkdtemp(
                prefix=(
                    "checkpoint_snapshot_"
                    f"{uuid.uuid4().hex[:8]}_"
                )
            )
        )

        try:
            # Copy the current mirror into the checkpoint directory.
            for source in self._mirror.rglob("*"):
                relative = source.relative_to(
                    self._mirror
                )

                destination = (
                    checkpoint_dir / relative
                )

                if source.is_dir():
                    destination.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                else:
                    destination.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    shutil.copy2(
                        source,
                        destination,
                    )

            self._checkpoint_mirrors[
                snapshot_id
            ] = checkpoint_dir

        except Exception:
            shutil.rmtree(
                checkpoint_dir,
                ignore_errors=True,
            )
            raise

        return snapshot_id

    # ==================================================================
    # RESTORE
    # ==================================================================

    def restore(
        self,
        snapshot_id: str,
    ) -> None:
        """
        Restore the /project filesystem to a known-good checkpoint.

        IMPORTANT:

        We intentionally do NOT call:

            self._sandbox.revert(snapshot_id)

        here.

        In the current Solari SDK/backend environment, native revert
        has returned:

            "Not revertable"

        and subsequently left the WebSocket control channel unusable.

        Attempting to reconnect then produces an HTTP 404 WebSocket
        handshake failure.

        Checkpoint therefore uses its own transactional filesystem
        checkpoint for the MVP recovery path.

        This restores the exact /project file tree that existed when
        snapshot() was called.
        """

        checkpoint_dir = (
            self._checkpoint_mirrors.get(
                snapshot_id
            )
        )

        if checkpoint_dir is None:
            raise RuntimeError(
                "No transactional filesystem checkpoint "
                f"found for snapshot '{snapshot_id}'."
            )

        if not checkpoint_dir.exists():
            raise RuntimeError(
                "Transactional checkpoint directory "
                f"is missing for snapshot '{snapshot_id}'."
            )

        if self._sandbox is None:
            raise RuntimeError(
                "Solari sandbox is not booted."
            )

        print(
            "      Using Checkpoint transactional "
            "filesystem recovery."
        )

        # --------------------------------------------------------------
        # 1. Remove everything currently under /project.
        # --------------------------------------------------------------

        clear_result = self.run_command(
            "sh",
            [
                "-c",
                "find /project -mindepth 1 "
                "-maxdepth 1 -exec rm -rf -- {} +",
            ],
        )

        if clear_result["exit_code"] not in (
            0,
            None,
        ):
            raise RuntimeError(
                "Failed to clear Solari project during "
                "transactional recovery: "
                + str(clear_result["stderr"])
            )

        # --------------------------------------------------------------
        # 2. Recreate /project.
        # --------------------------------------------------------------

        mkdir_result = self.run_command(
            "mkdir",
            [
                "-p",
                self.PROJECT_ROOT,
            ],
        )

        if mkdir_result["exit_code"] not in (
            0,
            None,
        ):
            raise RuntimeError(
                "Failed to recreate Solari project root: "
                + str(mkdir_result["stderr"])
            )

        # --------------------------------------------------------------
        # 3. Restore every checkpointed file.
        # --------------------------------------------------------------

        restored_files = 0

        for source in checkpoint_dir.rglob("*"):
            relative = source.relative_to(
                checkpoint_dir
            )

            remote = (
                self.PROJECT_ROOT
                + "/"
                + relative.as_posix()
            )

            if source.is_dir():
                result = self.run_command(
                    "mkdir",
                    [
                        "-p",
                        remote,
                    ],
                )

                if result["exit_code"] not in (
                    0,
                    None,
                ):
                    raise RuntimeError(
                        "Failed to restore directory "
                        f"{remote}: "
                        + str(result["stderr"])
                    )

                continue

            # Create the remote parent directory.
            remote_parent = remote.rsplit(
                "/",
                1,
            )[0]

            mkdir_result = self.run_command(
                "mkdir",
                [
                    "-p",
                    remote_parent,
                ],
            )

            if mkdir_result["exit_code"] not in (
                0,
                None,
            ):
                raise RuntimeError(
                    "Failed to create restore parent "
                    f"{remote_parent}: "
                    + str(mkdir_result["stderr"])
                )

            # Read the local checkpoint file as base64.
            encoded = base64.b64encode(
                source.read_bytes()
            ).decode("ascii")

            # Use Python inside the sandbox to reconstruct
            # the exact binary/text file.
            code = (
                "import base64;"
                "p="
                + repr(remote)
                + ";"
                "d=base64.b64decode("
                + repr(encoded)
                + ");"
                "open(p,'wb').write(d)"
            )

            result = self.run_command(
                "python3",
                [
                    "-c",
                    code,
                ],
            )

            if result["exit_code"] not in (
                0,
                None,
            ):
                raise RuntimeError(
                    "Failed to restore file "
                    f"{remote}: "
                    + str(result["stderr"])
                )

            restored_files += 1

        # --------------------------------------------------------------
        # 4. Refresh local mirror.
        # --------------------------------------------------------------

        self._sync_mirror()

        print(
            "      Filesystem restored successfully "
            f"({restored_files} files)."
        )

    # ==================================================================
    # FILESYSTEM MIRROR
    # ==================================================================

    def _sync_mirror(self) -> None:
        """
        Mirror /project from the remote Solari sandbox into a local
        temporary directory.

        The local mirror is used by Checkpoint's existing filesystem
        diff engine.

        The remote sandbox remains the execution environment.
        """

        if self._sandbox is None:
            raise RuntimeError(
                "Solari sandbox is not booted."
            )

        # This Python program walks /project and produces:

        # {
        #   "app.py": "<base64>",
        #   "reports/report.csv": "<base64>"
        # }

        code = (
            "import os,json,base64;"
            "root='/project';"
            "out={};"
            "[(out.__setitem__("
            "os.path.relpath(os.path.join(dp,f),root),"
            "base64.b64encode("
            "open(os.path.join(dp,f),'rb').read()"
            ").decode('ascii'))"
            ") "
            "for dp,ds,fs in os.walk(root)"
            " for f in fs];"
            "print(json.dumps(out,separators=(',',':')))"
        )

        result = self.run_command(
            "python3",
            [
                "-c",
                code,
            ],
        )

        if result["exit_code"] not in (
            0,
            None,
        ):
            raise RuntimeError(
                "Failed to synchronize Solari filesystem: "
                + str(result["stderr"])
            )

        raw_output = (
            result["stdout"].strip()
        )

        try:
            data = json.loads(
                raw_output or "{}"
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Invalid filesystem synchronization "
                "response from Solari: "
                + raw_output[:500]
            ) from exc

        # --------------------------------------------------------------
        # Clear old mirror.
        # --------------------------------------------------------------

        if self._mirror.exists():
            for child in self._mirror.iterdir():
                if child.is_dir():
                    shutil.rmtree(
                        child,
                        ignore_errors=True,
                    )
                else:
                    try:
                        child.unlink()
                    except FileNotFoundError:
                        pass

        self._mirror.mkdir(
            parents=True,
            exist_ok=True,
        )

        # --------------------------------------------------------------
        # Rebuild mirror.
        # --------------------------------------------------------------

        for relative_path, encoded in data.items():
            # Defense against malformed remote paths.
            relative = Path(
                relative_path
            )

            if relative.is_absolute():
                raise RuntimeError(
                    "Remote filesystem returned an "
                    f"absolute path: {relative_path}"
                )

            target = (
                self._mirror / relative
            )

            # Ensure the resulting path stays inside the mirror.
            try:
                target.resolve().relative_to(
                    self._mirror.resolve()
                )

            except ValueError as exc:
                raise RuntimeError(
                    "Remote filesystem returned an "
                    f"unsafe path: {relative_path}"
                ) from exc

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            target.write_bytes(
                base64.b64decode(
                    encoded
                )
            )

    # ==================================================================
    # ROOT PATH
    # ==================================================================

    def root_path(self) -> Path:
        """
        Return the local mirror after synchronizing it with Solari.
        """

        self._sync_mirror()

        return self._mirror

    # ==================================================================
    # CLEANUP
    # ==================================================================

    def teardown(self) -> None:
        """
        Kill the remote sandbox and clean local resources.

        kill() is used instead of merely closing the client so the
        Solari VM does not remain running.
        """

        try:
            # ----------------------------------------------------------
            # Kill remote sandbox.
            # ----------------------------------------------------------

            if (
                self._sandbox is not None
                and self._loop is not None
            ):
                try:
                    self._run_async(
                        self._sandbox.kill()
                    )

                except Exception:
                    # Cleanup must be best-effort.
                    pass

            # ----------------------------------------------------------
            # Close client if supported.
            # ----------------------------------------------------------

            if (
                self._client is not None
                and self._loop is not None
            ):
                close = getattr(
                    self._client,
                    "close",
                    None,
                )

                if close is not None:
                    try:
                        result = close()

                        # Some SDK versions may return an awaitable.
                        if hasattr(
                            result,
                            "__await__",
                        ):
                            self._run_async(
                                result
                            )

                    except Exception:
                        pass

        finally:
            # ----------------------------------------------------------
            # Stop event loop.
            # ----------------------------------------------------------

            if (
                self._loop is not None
                and self._loop.is_running()
            ):
                self._loop.call_soon_threadsafe(
                    self._loop.stop
                )

            if (
                self._loop_thread is not None
                and self._loop_thread.is_alive()
            ):
                self._loop_thread.join(
                    timeout=2
                )

            self._loop = None
            self._loop_thread = None

            # ----------------------------------------------------------
            # Remove mirror.
            # ----------------------------------------------------------

            shutil.rmtree(
                self._mirror,
                ignore_errors=True,
            )

            # ----------------------------------------------------------
            # Remove transactional checkpoints.
            # ----------------------------------------------------------

            for checkpoint_dir in (
                self._checkpoint_mirrors.values()
            ):
                shutil.rmtree(
                    checkpoint_dir,
                    ignore_errors=True,
                )

            self._checkpoint_mirrors.clear()

            self._sandbox = None
            self._client = None
            self._booted = False


# ============================================================================
# RUNTIME FACTORY
# ============================================================================


def get_runtime() -> SandboxRuntime:
    """
    Select the runtime.

    If SOLARI_API_KEY exists:

        SolariSandboxRuntime

    Otherwise:

        LocalFallbackRuntime
    """

    if os.environ.get("SOLARI_API_KEY"):
        return SolariSandboxRuntime()

    return LocalFallbackRuntime()