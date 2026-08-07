"""Public façade for the native macOS ``cswap menubar`` surface.

Import-safe presentation helpers remain available to CLI and test callers on
all platforms. The PyObjC implementation is imported only at launch time.
"""

from __future__ import annotations

import logging
import os
import plistlib
import sys
from pathlib import Path

from claude_swap.menubar_controller import MenuBarController
from claude_swap.menubar_viewmodel import (
    AUTO_THRESHOLD_CHOICES,
    EMPTY_SNAPSHOT,
    REFRESH_CHOICES,
    SWITCH_HISTORY_LIMIT,
    CapacityState,
    FreshnessState,
    MenuBarPopoverViewModel,
    MenuBarSettings,
    PopoverAccountViewModel,
    UsageRowViewModel,
    UsageScope,
    _account_display_usage,
    _adapt_snapshot,
    _live_countdown,
    _local_part,
    _resets_at_ts,
    _rolled_weekly_window,
    _usage_log_key,
    _window_pct,
    format_account_label,
    format_title,
    format_usage_log,
    parse_switch_history,
    popover_view_model,
    tightest_pct,
    usage_summary,
)
from claude_swap.switcher import SENTINEL_NOTES

NOTIFICATION_BUNDLE_ID = "com.claude-swap.menubar"


def ensure_notification_identity(
    executable: Path | None = None,
    *,
    platform: str = sys.platform,
) -> Path | None:
    """Ensure macOS can resolve a bundle identifier for notifications."""
    if platform != "darwin":
        return None
    path = (executable or Path(sys.executable)).parent / "Info.plist"
    data: dict = {}
    try:
        if path.exists():
            try:
                loaded = plistlib.loads(path.read_bytes())
            except Exception:
                loaded = None
            if isinstance(loaded, dict):
                data = loaded
        changed = False
        if not data.get("CFBundleIdentifier"):
            data["CFBundleIdentifier"] = NOTIFICATION_BUNDLE_ID
            changed = True
        if not data.get("CFBundleName"):
            data["CFBundleName"] = "claude-swap"
            changed = True
        if changed or not path.exists():
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_bytes(plistlib.dumps(data))
            os.replace(tmp, path)
    except (OSError, plistlib.InvalidFileException, ValueError) as exc:
        logging.getLogger("claude-swap").warning(
            "Could not prepare menu-bar notification identity: %s", exc
        )
        return None
    return path


def run(switcher) -> int:
    """Launch the native AppKit status item and transient compact popover."""
    from claude_swap.menubar_appkit import run_native_menubar

    ensure_notification_identity()
    return run_native_menubar(switcher)


__all__ = [
    "AUTO_THRESHOLD_CHOICES",
    "CapacityState",
    "EMPTY_SNAPSHOT",
    "FreshnessState",
    "MenuBarController",
    "MenuBarPopoverViewModel",
    "MenuBarSettings",
    "PopoverAccountViewModel",
    "REFRESH_CHOICES",
    "SENTINEL_NOTES",
    "SWITCH_HISTORY_LIMIT",
    "UsageRowViewModel",
    "UsageScope",
    "_account_display_usage",
    "_adapt_snapshot",
    "_live_countdown",
    "_local_part",
    "_resets_at_ts",
    "_rolled_weekly_window",
    "_usage_log_key",
    "_window_pct",
    "ensure_notification_identity",
    "format_account_label",
    "format_title",
    "format_usage_log",
    "parse_switch_history",
    "popover_view_model",
    "run",
    "tightest_pct",
    "usage_summary",
]
