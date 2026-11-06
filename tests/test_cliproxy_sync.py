"""Tests for the vendored contrib/hooks/cswap-cliproxy-sync adapter."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
import time
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parent.parent / "contrib" / "hooks" / "cswap-cliproxy-sync"


def _load_hook():
    loader = importlib.machinery.SourceFileLoader("cswap_cliproxy_sync", str(HOOK_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


def test_auth_files_listing_with_extra_top_level_keys_is_accepted():
    # CLIProxyAPI's GET /auth-files returns {"files": [...], "observed_at": ...}.
    hook = _load_hook()
    client = hook.ManagementClient(
        hook.MANAGEMENT_BASE_URL, "key", deadline=time.monotonic() + 8
    )
    listing = {
        "files": [
            {"name": "claude-a.json", "email": "a@example.com", "provider": "claude",
             "type": "claude", "disabled": False, "priority": 100},
            {"name": "codex-a.json", "email": "a@example.com", "provider": "codex",
             "type": "codex", "disabled": False},
        ],
        "observed_at": "2026-11-06T22:30:00Z",
    }
    client._request = lambda method, path, body=None: json.dumps(listing).encode()

    assert client.get_auth_files() == [
        hook.Credential("claude-a.json", "a@example.com", False, 100)
    ]
