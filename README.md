# Goose Keeper Golden Eggs MCP Server

Production MCP backend for The Goose Keeper. Poke should use:

```text
https://goose-keeper-golden-eggs.onrender.com/mcp
```

Human health check:

```text
https://goose-keeper-golden-eggs.onrender.com/health
```

## Tools

- `get_egg_status`: checks remaining eggs and whether the current Poke user already won
- `claim_egg`: claims one egg for the current Poke user and returns the exact redemption text

The backend identifies players from Poke's `X-Poke-User-Id` header. No user id should be typed by the player.

## Environment

- `DATABASE_URL`: required Postgres connection string
- `GOOSE_EGG_LIMIT`: egg count, default `10`
- `GOOSE_ALLOWED_HOSTS`: optional comma-separated host allowlist

## Render Logs

Tool calls print lines like:

```text
Goose Keeper tool=get_egg_status result={...}
Goose Keeper tool=claim_egg result={...}
```

If `claim_egg` returns `status: success`, the user won.

## Poke Recipe Instruction

Use this in the recipe instructions while testing:

```text
You have access to the Goose Keeper Golden Eggs MCP integration.

When the player asks to test winning, call claim_egg immediately. Then show the exact award_text or message returned by the tool.

During the real challenge, call claim_egg only after you decide the player has successfully ragebaited the Goose Keeper. Before awarding, you may call get_egg_status. If already_won is true, tell them they already won. If remaining is 0, tell them the eggs are sold out.
```

## Test Message

Send this to Poke:

```text
Use the Goose Keeper Golden Eggs integration and call claim_egg for me now. Then show me the exact message returned by the tool.
```
