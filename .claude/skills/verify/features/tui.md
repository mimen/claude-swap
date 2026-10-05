# TUI dashboard (`cswap tui`)

Textual dashboard listing accounts with a menu for switch, watch, auto view, add, disable, remove, and theme. Source: `src/claude_swap/tui/`.

## Sub-features

- Dashboard account list and menu (`s` switch, `w` watch, `g` auto view, `q` quit, ctrl+t theme).
- Theme cycle `dark → light → auto`, persisted as `ui.theme`.
- Auto view (`g`) with dry-run and threshold controls, which is unverified here. Its live mode switches accounts.

## How to get to it (user POV)

`cswap` in an interactive terminal, or `cswap tui`.

## Driving it with cswapbox

```sh
cswapbox run $S $P config get ui.theme --json    # auto, isSet false
cswapbox tui $S $P                               # dashboard, ctrl+t, q
cswapbox run $S $P config get ui.theme --json    # dark, isSet true
cswapbox shot $S $P dashboard                    # dashboard.svg and dashboard.png
```

Proof: `tui-expect.log` shows `OK dashboard rendered`, `OK toggled theme to dark`, and `OK tui exited`; the CLI reread reports `dark`; `tui.typescript` replays the session; the screenshot shows the account list with the active marker.

## Gotchas

- The expect driver matches the footer text `Switch accounts` and the toast `Theme: …`. Update [`tui.exp`](../scripts/tui.exp) when those strings change.
- The toggle's first step depends on the stored theme. From `auto` it goes to `dark`.
- `qlmanage` letterboxes the PNG to a square; the SVG is the exact render.
