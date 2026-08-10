# Post-switch hooks

Executables claude-swap runs after it switches the active account. Configure one
by pointing `hooks.postSwitch` at its absolute path in
`~/.claude-swap-backup/settings.json`:

```json
{
  "schemaVersion": 1,
  "hooks": { "postSwitch": "/Users/<you>/.local/bin/cswap-cliproxy-sync" }
}
```

The hook receives the switch event as JSON on stdin and runs with
`CLAUDE_SWAP_POST_SWITCH_HOOK_ACTIVE=1` in its environment.

## cswap-cliproxy-sync

Keeps a local [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI)
gateway pointed at the same Claude account claude-swap just switched to.

Switching the account claude-swap manages does not, on its own, change which
credential the gateway prefers. Without this hook the two drift: Claude Code
talks to one account while anything routed through the gateway keeps using
whichever credential the gateway happened to rank highest.

The hook resolves the switch event's target email against the gateway's
credential list and rewrites priorities so that account wins.

**Requirements**, all of which fail quietly if missed:

- The gateway's Management API must be reachable at
  `http://127.0.0.1:8317/v0/management`.
- `remote-management.secret-key` must be **non-empty** in the gateway's config
  (`/opt/homebrew/etc/cliproxyapi.conf` under Homebrew). An empty value disables
  the Management API entirely and every route returns 404.
- `~/.cli-proxy-api-management-key` must hold that same key. The hook reads it
  from disk at runtime and contains no credential itself.
- The gateway needs a credential for each account you intend to switch between
  (`cliproxyapi -claude-login`, once per account).

Provisioning a new machine means carrying the config's `secret-key`, the key
file, and a gateway login per account — not just this script.
