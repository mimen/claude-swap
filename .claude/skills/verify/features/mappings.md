# Directory mappings (`cswap map`)

Binds a directory to an account so `cswap run` with no account launches that account there. Source: `_map_command`, `_unmap_command` in `src/claude_swap/cli.py`, `src/claude_swap/mappings.py`.

## Sub-features

- `map NUM|EMAIL [PATH]`, `map` (list), `unmap [PATH]`, `unclaimed`.
- The consumer, `cswap run` with no account, is not drivable here because it launches `claude`.

## How to get to it (user POV)

`cswap map 2 ~/work/client-app`, then `cswap map`.

## Driving it with cswapbox

Requires at least one account (see [accounts](accounts.md)).

```sh
mkdir -p $S/work/proj
cswapbox run $S $P map verify-a@token.local $S/work/proj
cswapbox run $S $P map
cswapbox run $S $P unmap $S/work/proj
```

Proof: the list shows `<scratch>/work/proj → N: verify-a@token.local`, and `<scratch>/home/.claude-swap-backup/mappings.json` holds the entry keyed by the normalized path.

## Gotchas

- Mappings are keyed by email and org, so they follow an account through `swap`.
- macOS paths under `/tmp` normalize to `/private/tmp`.
