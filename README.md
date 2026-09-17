# Goose Keeper Golden Eggs MCP Server

Production MCP backend for The Goose Keeper. Poke should use:

```text
https://the-goose-keeper.onrender.com/mcp
```

Human health check:

```text
https://the-goose-keeper.onrender.com/health
```

## Tools

- `get_egg_status`: checks remaining eggs and whether the current Poke user already won
- `claim_egg(email)`: claims one egg for the current Poke user; requires the email they RSVP'd with on myHTN (desk lookup hint only)

The backend identifies players from Poke's `X-Poke-User-Id` header. No user id should be typed by the player.

This MCP does **not** award Goose Games points. A successful claim only:

1. Deducts one of the global Golden Eggs
2. Stores email for desk lookup
3. Returns the official winning / redemption message to Poke (for the hacker)
4. Posts a notification to the organizer Slack webhook (if configured), including email

Organizers redeem prizes / GG points manually at the Goose Games desk after verifying myHTN/badge.

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
3. On each successful `claim_egg`, the server posts poke user id, email, claimed/remaining counts, and timestamp.

If the webhook is missing or Slack fails, the egg claim still succeeds (logged as `slack_skip` / `slack_error`).

## Render Logs

Tool calls print lines like:

```text
Goose Keeper tool=get_egg_status result={...}
Goose Keeper tool=claim_egg result={...}
```

If `claim_egg` returns `status: success`, the user won.

## Poke Recipe Instruction (event)

Add this near the MCP section of the recipe (remove TESTING MODE before the event):

```text
## MCP
You have access to the Goose Keeper Golden Eggs MCP integration.

When a player successfully ragebaits the Goose Keeper according to the challenge rules:
1. Call get_egg_status first. If already_won is true, tell them they already won. If remaining is 0, tell them the eggs are sold out.
2. Ask for the email they RSVP'd with on myHTN (Hack the North).
3. Only after they provide an email, call claim_egg with that email argument.
4. If claim_egg returns status="email_required", ask again for a real email and retry.
5. If claim_egg returns status="success", respond exactly with the official winning message from award_text/message.
6. Never invent an email. Never call claim_egg without an email the hacker typed.
```

## Test Message

```text
I successfully ragebaited you for testing. Ask me for my email, then call claim_egg with it and show the exact tool result.
```
