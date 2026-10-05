# Settings (`cswap config`)

Reads and edits `settings.json` in the backup root with strict validation. Source: `_config_command` in `src/claude_swap/cli.py`, `src/claude_swap/settings.py`.

## Sub-features

- `config` / `config list [--json]`, `config get KEY [--json]`, `config set KEY VALUE`, `config unset KEY`, `config path`.
- Keys and ranges are listed by `cswap config --help`. `cswapbox` lets `set` and `unset` touch only `autoswitch.*` and `ui.theme`; `hooks.postSwitch` is refused because a hook runs an arbitrary executable.

## How to get to it (user POV)

`cswap config set autoswitch.threshold 80`, then `cswap config get autoswitch.threshold`.

## Driving it with cswapbox

```sh
cswapbox run $S $P config get autoswitch.threshold --json   # isSet false, 90.0
cswapbox run $S $P config set autoswitch.threshold 77
cswapbox run $S $P config get autoswitch.threshold --json   # isSet true, 77.0
cswapbox run $S $P config set autoswitch.threshold 150      # exit 1, range error
cswapbox run $S $P config unset autoswitch.threshold
```

Proof: the second `get` reports `isSet: true`, `<scratch>/home/.claude-swap-backup/settings.json` holds only `schemaVersion` and the key, and the out-of-range set exits 1 without changing the file.

## Gotchas

- `config` must be the first argument; `cswap --debug config` is not parsed as config.
- `--json` works only with `list` and `get`.
