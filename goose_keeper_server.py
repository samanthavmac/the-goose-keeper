import os
from contextvars import ContextVar
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


DATABASE_URL = os.getenv("DATABASE_URL")
EGG_LIMIT = int(os.getenv("GOOSE_EGG_LIMIT", "10"))
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "GOOSE_ALLOWED_HOSTS",
        "127.0.0.1:*,localhost:*,[::1]:*,goose-keeper-golden-eggs.onrender.com",
    ).split(",")
    if host.strip()
]

current_poke_user_id: ContextVar[Optional[str]] = ContextVar(
    "current_poke_user_id", default=None
)

mcp = FastMCP(
    "Goose Keeper Golden Eggs",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(allowed_hosts=ALLOWED_HOSTS),
)


def require_database_url() -> str:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required.")
    return DATABASE_URL


def init_db() -> None:
    import psycopg

    with psycopg.connect(require_database_url()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS winners (
                poke_user_id TEXT PRIMARY KEY,
                claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


def award_text() -> str:
    return "🥚 YOU WON A GOLDEN EGG! 🥚\n\nVisit the Goose Games desk on PSE Floor 1 to redeem your prize."


def log_tool_result(tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
    print(f"Goose Keeper tool={tool_name} result={result}", flush=True)
    return result


def get_user_id() -> str:
    user_id = current_poke_user_id.get()
    if not user_id:
        raise ValueError("Missing X-Poke-User-Id header.")
    return user_id


def egg_status(user_id: str) -> dict[str, Any]:
    import psycopg

    with psycopg.connect(require_database_url()) as conn:
        winner_count = conn.execute("SELECT COUNT(*) FROM winners").fetchone()[0]
        already_won = (
            conn.execute(
                "SELECT 1 FROM winners WHERE poke_user_id = %s",
                (user_id,),
            ).fetchone()
            is not None
        )

    return {
        "status": "ok",
        "remaining": max(EGG_LIMIT - winner_count, 0),
        "already_won": already_won,
        "limit": EGG_LIMIT,
    }


def claim_for_user(user_id: str) -> dict[str, Any]:
    import psycopg

    with psycopg.connect(require_database_url()) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('goose_keeper_eggs'))")

        if (
            conn.execute(
                "SELECT 1 FROM winners WHERE poke_user_id = %s",
                (user_id,),
            ).fetchone()
            is not None
        ):
            remaining = max(
                EGG_LIMIT - conn.execute("SELECT COUNT(*) FROM winners").fetchone()[0],
                0,
            )
            return {
                "status": "already_won",
                "remaining": remaining,
                "message": "This Poke user has already claimed a golden egg.",
            }

        winner_count = conn.execute("SELECT COUNT(*) FROM winners").fetchone()[0]
        if winner_count >= EGG_LIMIT:
            return {
                "status": "sold_out",
                "remaining": 0,
                "message": "All golden eggs have already been claimed.",
            }

        conn.execute("INSERT INTO winners (poke_user_id) VALUES (%s)", (user_id,))

    return {
        "status": "success",
        "remaining": max(EGG_LIMIT - winner_count - 1, 0),
        "message": award_text(),
        "award_text": award_text(),
    }


@mcp.tool()
def get_egg_status() -> dict[str, Any]:
    """Check remaining eggs and whether the current Poke user already won."""
    try:
        return log_tool_result("get_egg_status", egg_status(get_user_id()))
    except Exception as error:
        return log_tool_result(
            "get_egg_status",
            {"status": "error", "message": str(error)},
        )


@mcp.tool()
def claim_egg() -> dict[str, Any]:
    """Award a golden egg to the current Poke user and return the redemption text."""
    try:
        return log_tool_result("claim_egg", claim_for_user(get_user_id()))
    except Exception as error:
        return log_tool_result(
            "claim_egg",
            {"status": "error", "message": str(error)},
        )


class PokeUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = current_poke_user_id.set(request.headers.get("x-poke-user-id"))
        try:
            return await call_next(request)
        finally:
            current_poke_user_id.reset(token)


async def health(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "name": "Goose Keeper Golden Eggs",
            "mcp_url": "/mcp",
            "tools": ["get_egg_status", "claim_egg"],
        }
    )


init_db()
app: Starlette = mcp.streamable_http_app()
app.add_middleware(PokeUserMiddleware)
app.add_route("/", health, methods=["GET"])
app.add_route("/health", health, methods=["GET"])
