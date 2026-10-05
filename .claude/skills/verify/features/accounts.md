# Account store

Managed accounts in numbered slots, with aliases, reordering, and switching of the active credential. Source: `add_account_from_token`, `set_alias`, `swap`/`move`, `switch_to` in `src/claude_swap/switcher.py`.

## Sub-features

- `add-token TOKEN --email E [--slot N]`: an `sk-ant-api…` value registers an API-key account.
- `alias N NAME`, `alias --unset N`, `swap A B`, `move A SLOT`.
- `list [--json]`, `status [--json]`, `switch N [--json]`.
- `remove`, `disable`, `enable`.
- `add` (OAuth capture of the logged-in account), `export`, and `import`, which `cswapbox` refuses and are unverified here.

## How to get to it (user POV)

`cswap add-token <key> --email me@example.com`, `cswap list`, `cswap switch 2`.

## Driving it with cswapbox

```sh
cswapbox run $S $P add-token sk-ant-api03-VERIFYFAKE0000000000000000000000000000 --email verify-a@token.local
cswapbox run $S $P add-token sk-ant-api03-VERIFYFAKE1111111111111111111111111111 --email verify-b@token.local
cswapbox run $S $P alias 2 bee
cswapbox run $S $P swap 1 bee
cswapbox run $S $P switch 2 --json
cswapbox run $S $P status --json
```

Proof: `list` shows `1: bee (verify-b@token.local)` after the swap; `switch` returns `"switched": true`; `status --json` names account 2 active; `<scratch>/home/.claude.json` holds the fake key as `primaryApiKey` (redact it before copying); `credentials/*.enc` files exist under the scratch backup root; the log shows each Keychain call denied.

## Gotchas

- `cswapbox` accepts only `add-token sk-ant-api03-VERIFYFAKE… --email …@token.local`. `add` captures whatever account is logged in, and an OAuth setup token triggers usage and refresh calls.
- The ".prev retention" and "migration deferred" warnings in the log are the expected Keychain-denied fallback, not failures.
- `remove N` asks `[y/N]` on stdin and waits forever without an answer. Drive it as `echo y | cswapbox run $S $P remove N`; with no argument it also prompts for the slot.
