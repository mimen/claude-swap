---
name: verify
description: Drive this checkout's real claude-swap (`cswap` CLI and Textual TUI) against a disposable account store in a macOS sandbox that denies the Keychain, network, and real-HOME writes, and capture transcripts, a TUI recording, and screenshots. Use when proving a cswap change works as a user sees it: config, accounts (add-token, alias, swap, switch), directory mappings, the TUI dashboard, or menu bar service status.
---

# Verify claude-swap

Proves cswap behavior by running the checkout's own `cswap` entry point against a throwaway store. The [feature map](features/README.md) lists what to drive and what each flow proves.

## Safety boundary

`HOME` isolation alone does not protect the user: on macOS cswap reads and writes the login Keychain through `/usr/bin/security` regardless of `HOME`. [`scripts/cswapbox`](scripts/cswapbox) therefore runs every cswap call under `sandbox-exec` with a generated profile that:

- **Denies** exec of `/usr/bin/security`, the Security server mach services, outbound IP, reads of the real `~/.claude-swap-backup`, `~/.claude`, `~/.claude.json`, `~/Library/Keychains`, and every write outside the run's scratch directory.
- **Runs** with `env -i`, `HOME=<scratch>/home`, `USER=cswap-verify`, so no inherited `CLAUDE_CONFIG_DIR` or token leaks in.

cswap's credential store falls back to `.enc` files under the scratch `HOME` when the Keychain is denied; the log shows `Operation not permitted: '/usr/bin/security'` for each attempt. That fallback is the product's own path, not a mock.

The sandbox still allows `launchctl`, and `launch_agent` targets the real `gui/<uid>` domain whatever `HOME` says, so `cswapbox` also enforces an allowlist before it executes anything. `run` and `boxed-cswap` refuse with exit 3 unless the command is one of these:

- `list`, `status`, `alias`, `swap`, `move`, `map`, `unmap`, `unclaimed`, `disable`, `enable`, `switch`, `tui`, `remove <one account>`.
- `add-token sk-ant-api03-VERIFYFAKE… --email …@token.local`, exactly.
- `config` `list`, `get`, or `path`, plus `set` and `unset` of `autoswitch.*` and `ui.theme` only. `hooks.postSwitch` is refused because a hook runs an arbitrary executable.
- `menubar --service-status`, exactly.

Every flag other than `--json`, `--email`, `--slot`, and `--unset` is refused, which covers abbreviations such as `--uninst`, `--force`, and `--debug`. Everything else is refused too, including `add`, `auto`, `run`, `purge`, `upgrade`, `update`, `export`, `import`, `watch`, every `--flag` spelling of a command, and `menubar` in any other form. Never call `.venv/bin/cswap` directly from this skill.

## Launch

1. `uv sync --locked` in the repo root once. It creates `.venv/bin/cswap` as an editable install of this checkout. Never install over a resident `cswap`.
2. `S=$(.claude/skills/verify/scripts/cswapbox new <proof-dir>)`. This creates `/private/tmp/cswap-verify.XXXXXX` with an owner marker and writes `<proof-dir>/manifest.txt` (source SHA, branch, dirty files, helper hashes).

## Doctor

`cswapbox doctor $S` fails closed unless all of these hold:

- `claude_swap` imports from this checkout's `src/`, and `cswap config path` resolves inside the scratch `HOME`.
- The sandbox refuses `/usr/bin/security`, an HTTPS request, and a read of the real `~/.claude-swap-backup/sequence.json`.
- The sandbox refuses to create a file in a fresh `/private/tmp/cswap-verify-probe.*` directory outside scratch, and leaves its sentinel's hash unchanged. The probe never targets the real `HOME`, so a regressed sandbox cannot damage a user file.
- The scratch `settings.json` has no `hooks` section.

On success it stamps the scratch directory with the helper's hash. `run`, `tui`, `shot`, and `boxed-cswap` refuse to drive until that stamp is present and matches the current helper. Stop on any failure; never fall back to the user's runtime.

## Drive

| Command | What it does |
|---|---|
| `cswapbox run $S <proof> <cswap args…>` | One CLI call with the caller's stdin; appends command, output, and exit code to `<proof>/transcript.txt` with `sk-ant-…` values redacted, returns cswap's exit code |
| `cswapbox tui $S <proof>` | Starts `cswap tui` under `script -r` via [`scripts/tui.exp`](scripts/tui.exp), waits for the dashboard, sends ctrl+t, waits for `Theme: …`, sends `q`. Writes `<proof>/tui.typescript` (replay with `script -p`) and `<proof>/tui-expect.log` |
| `cswapbox shot $S <proof> <name>` | Starts `cswap tui` with `TEXTUAL_SCREENSHOT=4`; saves `<name>.svg` and a Quick Look `<name>.png` to the proof dir |

Prove persistence through a second CLI read (`config get … --json`, `list --json`, `status --json`, `map`), not by reading files alone. Then copy the relevant scratch files into the proof directory with any `sk-ant-` value replaced by `<redacted-fake>`.

## Evidence

- **Location.** `<proof-dir>` must be a canonical absolute path that is not a symlink, is owned by you, and lies outside both the checkout and scratch; `cswapbox` refuses any other. For example `~/Documents/verification-proofs/<wave>/claude-swap/attempt-N/`. Keep failed attempts in their own `attempt-N` with a `failures.txt` line per failure.
- **Every flow records** the action (the transcript command line), the observed state (the reread output or screenshot), and the side effect (the scratch file it wrote).
- **Real-store check.** Hash `~/.claude-swap-backup/{sequence,settings}.json` before the drive and confirm the hashes match after. A mismatch is a failed run.

## Cleanup

`cswapbox cleanup $S` checks the owner marker and refuses if any process holds a file under `$S` (`lsof +D`), printing the PIDs and leaving the directory. It removes only `$S`; the proof directory is never touched. Afterwards, `ls <proof-dir>` must still show the manifest and transcript.

## Not drivable here

- **Menu bar UI.** Needs the `menubar` extra (`rumps`, absent from the locked env), an Aqua session, and a non-framework Python on macOS 26. Clicking its native menu would switch the user's real account. Only `menubar --service-status` is in scope; see [menubar](features/menubar.md) for why its output is a split read of scratch and real state.
- **OAuth add, refresh, usage, auto-switch, `run`.** All need a real account, network, or a launched `claude`. Report them as unverified rather than substituting a unit test.
