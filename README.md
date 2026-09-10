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

This MCP does **not** award Goose Games points. A successful claim only:

1. Deducts one of the global Golden Eggs
2. Returns the official winning / redemption message to Poke (for the hacker)
3. Posts a notification to the organizer Slack webhook (if configured)

Organizers redeem prizes / GG points manually at the Goose Games desk.

## Environment

- `DATABASE_URL`: required Postgres connection string
- `GOOSE_EGG_LIMIT`: total eggs available globally, default `10`
- `SLACK_WEBHOOK_URL`: Incoming Webhook for the organizer-only Slack channel
- `GOOSE_ALLOWED_HOSTS`: optional comma-separated host allowlist

### Local vs Render

- **Local:** copy [`.env.example`](.env.example) → `.env` and fill values. `.env` is gitignored; never commit secrets.
- **Production (Render):** do **not** rely on a committed env file. In the Render dashboard → your web service → **Environment** → add `SLACK_WEBHOOK_URL` (and `GOOSE_EGG_LIMIT` if needed) → **Save** → redeploy. `render.yaml` marks `SLACK_WEBHOOK_URL` as `sync: false` so you paste the secret in the UI.

### Slack setup

1. Create an Incoming Webhook for the organizer-only channel.
2. Put the URL in local `.env` and/or Render **Environment** as `SLACK_WEBHOOK_URL`.
3. On each successful `claim_egg`, the server posts poke user id, claimed/remaining counts, and timestamp.

If the webhook is missing or Slack fails, the egg claim still succeeds (logged as `slack_skip` / `slack_error`).

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
