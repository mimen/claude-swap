---
deployment_status: partial
deployment_last_assessed: 2026-10-03
deployment_targets:
  - component: claude-swap
    where: local-install
    detail: editable source install in the M5 checkout's .venv, with claude-swap and cswap entry points
  - component: claude-swap menubar
    where: none
    detail: com.cswap.menubar LaunchAgent is absent on the inspected M5 and Mini; M5 lacks rumps
  - component: post-switch hooks
    where: none
    detail: hooks.postSwitch is not configured on the inspected M5
---

# Deployment

`claude-swap` is installed locally in the M5 checkout's `.venv`, with editable package metadata pointing to `/Users/mimen/Programming/Repos/claude-swap-menubar-prototype`. `README.md` documents source installation with `uv sync`. The upstream PyPI release workflow exists, but `PROJECT.md` states that this fork does not publish.

`claude-swap menubar` requires the optional `menubar` extra and can install `com.cswap.menubar` through `cswap menubar --install-service`. The M5's editable install lacks `rumps`, and neither the M5 nor Mini has that LaunchAgent. No deployed menu-bar target was established.

`post-switch hooks` are standalone executables installed by hand and configured through `hooks.postSwitch`, as documented in `contrib/hooks/README.md`. The inspected M5 settings contain no configured hook, and `/Users/mimen/.local/bin/cswap-cliproxy-sync` is absent. Deployment on other hosts was not established.
