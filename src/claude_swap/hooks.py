"""Executable hooks invoked after claude-swap operations commit."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import BinaryIO

POST_SWITCH_TIMEOUT_SECONDS = 10.0
HOOK_ORDER_LOCK_TIMEOUT_SECONDS = 30.0
HOOK_ACTIVE_ENV = "CLAUDE_SWAP_POST_SWITCH_HOOK_ACTIVE"
_MAX_STDERR_BYTES = 4096
_MAX_WARNING_LINE_CHARS = 200
_TERMINATE_GRACE_SECONDS = 0.5
_WINDOWS_TASKKILL_TIMEOUT_SECONDS = 5.0


def _bounded_line(text: str) -> str:
    """Return one bounded, printable line suitable for a warning."""
    first_line = text.splitlines()[0].strip() if text else ""
    sanitized = "".join(char if char.isprintable() else "?" for char in first_line)
    if len(sanitized) > _MAX_WARNING_LINE_CHARS:
        sanitized = sanitized[: _MAX_WARNING_LINE_CHARS - 1] + "…"
    return sanitized


def _runtime_path_warning(executable: str) -> str | None:
    """Validate hand-edited settings without ever resolving through PATH."""
    if "\x00" in executable:
        return "Post-switch hook path contains an embedded NUL"
    path = Path(executable)
    if not path.is_absolute():
        return "Post-switch hook is not an absolute executable path"
    try:
        if not path.exists():
            return "Post-switch hook executable does not exist"
        if not path.is_file():
            return "Post-switch hook path is not a file"
        if not os.access(path, os.X_OK):
            return "Post-switch hook file is not executable"
    except (OSError, ValueError) as exc:
        detail = _bounded_line(str(exc))
        return f"Post-switch hook path is invalid: {detail}"
    return None


def _drain_stderr(pipe: BinaryIO, retained: bytearray) -> None:
    """Continuously drain stderr while retaining only a bounded prefix."""
    try:
        while True:
            chunk = pipe.read(4096)
            if not chunk:
                return
            remaining = _MAX_STDERR_BYTES - len(retained)
            if remaining > 0:
                retained.extend(chunk[:remaining])
    except (OSError, ValueError):
        return


def _posix_process_group_exists(process_group_id: int) -> bool:
    """Whether the dedicated POSIX process group still has any members."""
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True
    return True


def _wait_for_posix_process_group_exit(process_group_id: int) -> None:
    """Bound how long cleanup waits for killed group members to disappear."""
    deadline = time.monotonic() + _TERMINATE_GRACE_SECONDS
    while _posix_process_group_exists(process_group_id):
        if time.monotonic() >= deadline:
            return
        time.sleep(0.01)


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Best-effort termination of the hook and its descendants."""
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=_WINDOWS_TASKKILL_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        try:
            process.kill()
        except OSError:
            pass
        return

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.terminate()
        except OSError:
            pass
    try:
        process.wait(timeout=_TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    # The group leader may exit on TERM while a descendant ignores it. Always
    # follow with KILL for any surviving member of the dedicated process group.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=_TERMINATE_GRACE_SECONDS)
    except (subprocess.TimeoutExpired, OSError):
        pass
    _wait_for_posix_process_group_exit(process.pid)


def run_post_switch_hook(
    executable: str,
    from_ref: dict | None,
    to_ref: dict,
) -> str | None:
    """Run the configured executable and return a warning on failure."""
    path_warning = _runtime_path_warning(executable)
    if path_warning is not None:
        return path_warning

    payload = json.dumps(
        {
            "schemaVersion": 1,
            "event": "postSwitch",
            "from": from_ref,
            "to": to_ref,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    environment = os.environ.copy()
    environment[HOOK_ACTIVE_ENV] = "1"
    popen_kwargs: dict = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.PIPE,
        "env": environment,
        "shell": False,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    try:
        process = subprocess.Popen([executable], **popen_kwargs)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        detail = _bounded_line(str(exc))
        return f"Post-switch hook could not start: {detail}"

    retained = bytearray()
    assert process.stderr is not None
    stderr_thread = threading.Thread(
        target=_drain_stderr,
        args=(process.stderr, retained),
        daemon=True,
    )
    stderr_thread.start()
    try:
        assert process.stdin is not None
        try:
            process.stdin.write(payload)
            process.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            pass
        try:
            return_code = process.wait(timeout=POST_SWITCH_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            _terminate_process_tree(process)
            stderr_thread.join(timeout=_TERMINATE_GRACE_SECONDS)
            return "Post-switch hook timed out after 10 seconds"
        if sys.platform != "win32" and _posix_process_group_exists(process.pid):
            _terminate_process_tree(process)
    finally:
        try:
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
        except OSError:
            pass

    stderr_thread.join(timeout=_TERMINATE_GRACE_SECONDS)
    if return_code == 0:
        return None
    detail = _bounded_line(retained.decode("utf-8", errors="replace"))
    warning = f"Post-switch hook exited with status {return_code}"
    return f"{warning}: {detail}" if detail else warning
