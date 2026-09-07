# Goose Keeper Golden Eggs MCP Server

Tiny MCP server for the Goose Keeper challenge. It exposes two tools:

- `get_egg_status`
- `claim_egg`

The server uses the `X-Poke-User-Id` request header to enforce one golden egg per Poke account. It uses Postgres when `DATABASE_URL` is set and SQLite as a local fallback.

## Local Setup

```bash
deactivate 2>/dev/null || true
rm -rf .venv
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
python --version
pip install -r requirements.txt
uvicorn goose_keeper_server:app --reload --port 8000
```

Your MCP endpoint will be:

```text
http://127.0.0.1:8000/mcp
```

For Poke, deploy behind HTTPS and use:

```text
https://your-server.example/mcp
```

## Environment

- `GOOSE_EGG_DB`: SQLite path, default `goose_keeper.db`
- `DATABASE_URL`: optional Postgres connection string for hosted deployment
- `GOOSE_EGG_LIMIT`: number of eggs, default `10`

## Simple HTTPS Deployment

One straightforward path is Render:

1. Push this folder to a GitHub repo.
2. Create a new Render Blueprint from the repo.
3. Render will read `render.yaml`, install `requirements.txt`, provision Postgres, and start Uvicorn.
4. Use the Render service URL plus `/mcp` as the Poke MCP Server URL.

Render's free web services have an ephemeral filesystem, so do not rely on local SQLite for a hosted prize counter. The included blueprint uses Postgres for persistence.

## Poke Integration

On `poke.com/integrations/new`:

- Name: `Goose Keeper Golden Eggs`
- MCP Server URL: `https://your-server.example/mcp`
- API Key: blank unless you add your own gateway auth

Poke should send `X-Poke-User-Id` on requests. If that header is missing, the tools return an explicit error instead of accepting a claim.

## Goose Keeper Prompt Snippet

```text
You are the Goose Keeper. You must only call claim_egg after you privately decide the hacker has successfully ragebaited you under the game rules.

Before awarding, call get_egg_status. If already_won is true, tell them they already won. If remaining is 0, tell them the eggs are sold out.

When claim_egg returns status="success", reply exactly:

🥚 YOU WON A GOLDEN EGG! 🥚

Visit the Goose Games desk on PSE Floor 1 to redeem your prize.
```
