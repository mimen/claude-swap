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
credential list, then enables and promotes that credential while disabling and
demoting every other Claude credential. Priority alone is not enough. The
gateway's failover is always on, so a dead target would silently serve requests
from the other account. A disabled credential cannot be failed over to, so a
dead target fails loudly instead.

### Repairing drift

claude-swap runs this hook whenever the active account changes. That includes
`cswap add` and the menu bar's "Add account" and "Refresh current credentials",
which move the active account without going through a switch.

When the two have drifted anyway, because the gateway restarted, a credential
was added outside cswap, or an earlier hook run failed, reconcile them with:

```
cswap switch <num|email> --force
```

Plain `cswap switch <num>` answers "Already on" and returns without running the
hook, which is useless precisely when a repair is needed. `--force`
re-establishes the identity and runs the hook even when the account did not
change.

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
