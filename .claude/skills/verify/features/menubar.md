# Menu bar (`cswap menubar`)

macOS status item through `rumps` and AppKit, kept alive by the `com.cswap.menubar` LaunchAgent. Source: `src/claude_swap/menubar.py`, `src/claude_swap/launch_agent.py`.

## Sub-features

- `menubar --service-status`: a read-only check. `installed` tests for the plist under `HOME`, which is the scratch home here. `loaded`, `state`, and `pid` come from `launchctl print` in the real `gui/<uid>` domain.
- `menubar`, `--install-service`, `--uninstall-service`: refused by `cswapbox` before exec. Both service operations act on the real GUI domain even with a scratch `HOME`.

## How to get to it (user POV)

`uv sync --extra menubar`, then `cswap menubar` from an Aqua session.

## Driving it with cswapbox

```sh
cswapbox run $S $P menubar --service-status
```

Proof: the command exits 0 and prints a status. "Menu bar service is not installed." means only that there is no plist in the scratch home and no `com.cswap.menubar` job in the real GUI domain. It is not evidence about the resident app's plist. For resident state, read `launchctl print gui/$(id -u)/com.cswap.menubar` and `~/Library/LaunchAgents/com.cswap.menubar.plist` directly, outside the sandbox.

## Gotchas

- The status item itself is unverified. The locked environment has no `rumps`, a framework Python on macOS 26 stops drawing the item, and its menu acts on the user's real Keychain account.
- `--install-service` writes `~/Library/LaunchAgents` and loads a resident job. It is out of scope for verification.
