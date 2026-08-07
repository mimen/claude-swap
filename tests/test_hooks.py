"""Tests for bounded, tree-safe post-switch executable handling."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_swap.hooks import (
    HOOK_ACTIVE_ENV,
    _terminate_process_tree,
    run_post_switch_hook,
)


FROM_REF = {"number": 1, "email": "a@example.com"}
TO_REF = {"number": 2, "email": "b@example.com"}


def _executable(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env python3\n" + body)
    path.chmod(0o755)
    return path


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX executable helper")
def test_noisy_stderr_is_drained_but_warning_is_bounded(tmp_path: Path):
    hook = _executable(
        tmp_path / "hook",
        "import os, sys\n"
        "chunk = b'x' * 65536\n"
        "for _ in range(128): os.write(sys.stderr.fileno(), chunk)\n"
        "raise SystemExit(9)\n",
    )

    result = run_post_switch_hook(str(hook), FROM_REF, TO_REF)

    assert result is not None
    assert result.startswith("Post-switch hook exited with status 9: ")
    assert len(result) <= 260


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX executable helper")
def test_child_receives_recursive_hook_guard(tmp_path: Path):
    observed = tmp_path / "guard"
    hook = _executable(
        tmp_path / "hook",
        "import os, pathlib\n"
        f"pathlib.Path({str(observed)!r}).write_text("
        f"os.environ.get({HOOK_ACTIVE_ENV!r}, ''))\n",
    )

    assert run_post_switch_hook(str(hook), FROM_REF, TO_REF) is None
    assert observed.read_text() == "1"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups")
def test_timeout_terminates_descendant_process_group(tmp_path: Path):
    child_pid_path = tmp_path / "child.pid"
    hook = _executable(
        tmp_path / "hook",
        "import pathlib, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])\n"
        f"pathlib.Path({str(child_pid_path)!r}).write_text(str(child.pid))\n"
        "time.sleep(60)\n",
    )

    with patch("claude_swap.hooks.POST_SWITCH_TIMEOUT_SECONDS", 2.0), patch(
        "claude_swap.hooks._TERMINATE_GRACE_SECONDS", 0.1,
    ):
        result = run_post_switch_hook(str(hook), FROM_REF, TO_REF)

    assert result == "Post-switch hook timed out after 10 seconds"
    child_pid = int(child_pid_path.read_text())
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.02)
    else:
        os.kill(child_pid, signal.SIGKILL)
        pytest.fail("timed-out hook descendant remained alive")


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups")
def test_successful_parent_cleans_up_lingering_descendant(tmp_path: Path):
    child_pid_path = tmp_path / "child.pid"
    hook = _executable(
        tmp_path / "hook",
        "import pathlib, subprocess, sys\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"pathlib.Path({str(child_pid_path)!r}).write_text(str(child.pid))\n",
    )

    with patch("claude_swap.hooks._TERMINATE_GRACE_SECONDS", 0.1):
        result = run_post_switch_hook(str(hook), FROM_REF, TO_REF)

    assert result is None
    child_pid = int(child_pid_path.read_text())
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.02)
    else:
        os.kill(child_pid, signal.SIGKILL)
        pytest.fail("successful hook left a descendant running")


def test_windows_tree_cleanup_invokes_taskkill_with_practical_timeout():
    process = Mock(pid=321)

    with patch("claude_swap.hooks.sys.platform", "win32"), patch(
        "claude_swap.hooks.subprocess.run"
    ) as run:
        _terminate_process_tree(process)

    run.assert_called_once_with(
        ["taskkill", "/PID", "321", "/T", "/F"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5.0,
        check=False,
    )


def test_windows_tree_cleanup_falls_back_when_taskkill_fails():
    process = Mock(pid=654)

    with patch("claude_swap.hooks.sys.platform", "win32"), patch(
        "claude_swap.hooks.subprocess.run",
        side_effect=subprocess.TimeoutExpired("taskkill", 5.0),
    ):
        _terminate_process_tree(process)

    process.kill.assert_called_once_with()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX executable mode")
def test_runtime_path_validation_is_warning_only(tmp_path: Path):
    missing = tmp_path / "missing"
    directory = tmp_path / "directory"
    directory.mkdir()
    non_executable = tmp_path / "non-executable"
    non_executable.write_text("pass")

    cases = [
        ("relative", "Post-switch hook is not an absolute executable path"),
        (str(missing), "Post-switch hook executable does not exist"),
        (str(directory), "Post-switch hook path is not a file"),
        (str(non_executable), "Post-switch hook file is not executable"),
        (str(tmp_path / "bad\x00path"), "Post-switch hook path contains an embedded NUL"),
    ]
    for executable, expected in cases:
        assert run_post_switch_hook(executable, FROM_REF, TO_REF) == expected


def test_payload_shape_constant_is_unchanged(tmp_path: Path):
    if sys.platform == "win32":
        pytest.skip("POSIX executable helper")
    received = tmp_path / "payload"
    hook = _executable(
        tmp_path / "hook",
        "import pathlib, sys\n"
        f"pathlib.Path({str(received)!r}).write_bytes(sys.stdin.buffer.read())\n",
    )

    assert run_post_switch_hook(str(hook), FROM_REF, TO_REF) is None
    assert json.loads(received.read_text()) == {
        "schemaVersion": 1,
        "event": "postSwitch",
        "from": FROM_REF,
        "to": TO_REF,
    }
    assert received.read_bytes() == (
        b'{"schemaVersion":1,"event":"postSwitch",'
        b'"from":{"number":1,"email":"a@example.com"},'
        b'"to":{"number":2,"email":"b@example.com"}}'
    )
