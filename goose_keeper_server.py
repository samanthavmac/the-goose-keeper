import os
import sqlite3
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


DB_PATH = Path(os.getenv("GOOSE_EGG_DB", "goose_keeper.db"))
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


def init_db() -> None:
    if DATABASE_URL:
        import psycopg

        with psycopg.connect(DATABASE_URL) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS winners (
                    poke_user_id TEXT PRIMARY KEY,
                    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS winners (
                poke_user_id TEXT PRIMARY KEY,
                claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def get_user_id() -> str:
    user_id = current_poke_user_id.get()
    if not user_id:
        raise ValueError("Missing X-Poke-User-Id header.")
    return user_id


def count_winners(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM winners").fetchone()[0]


def user_has_won(conn: sqlite3.Connection, user_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM winners WHERE poke_user_id = ?",
        (user_id,),
    ).fetchone()
    return row is not None


def get_postgres_status(user_id: str) -> dict[str, Any]:
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
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


def claim_postgres_egg(user_id: str) -> dict[str, Any]:
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
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

        conn.execute(
            "INSERT INTO winners (poke_user_id) VALUES (%s)",
            (user_id,),
        )

    return {
        "status": "success",
        "remaining": max(EGG_LIMIT - winner_count - 1, 0),
        "message": "Golden egg claimed.",
    }


@mcp.tool()
def get_egg_status() -> dict[str, Any]:
    """Return egg availability and whether the current Poke user already won."""
    try:
        user_id = get_user_id()
    except ValueError as error:
        return {"status": "error", "message": str(error)}

    if DATABASE_URL:
        return get_postgres_status(user_id)

    with sqlite3.connect(DB_PATH) as conn:
        winner_count = count_winners(conn)
        return {
            "status": "ok",
            "remaining": max(EGG_LIMIT - winner_count, 0),
            "already_won": user_has_won(conn, user_id),
            "limit": EGG_LIMIT,
        }


@mcp.tool()
def claim_egg() -> dict[str, Any]:
    """Claim one golden egg for the current Poke user if any remain."""
    try:
        user_id = get_user_id()
    except ValueError as error:
        return {"status": "error", "message": str(error)}

    if DATABASE_URL:
        return claim_postgres_egg(user_id)

    with sqlite3.connect(DB_PATH, isolation_level=None) as conn:
        conn.execute("BEGIN IMMEDIATE")

        if user_has_won(conn, user_id):
            remaining = max(EGG_LIMIT - count_winners(conn), 0)
            conn.execute("COMMIT")
            return {
                "status": "already_won",
                "remaining": remaining,
                "message": "This Poke user has already claimed a golden egg.",
            }

        winner_count = count_winners(conn)
        if winner_count >= EGG_LIMIT:
            conn.execute("COMMIT")
            return {
                "status": "sold_out",
                "remaining": 0,
                "message": "All golden eggs have already been claimed.",
            }

        conn.execute(
            "INSERT INTO winners (poke_user_id) VALUES (?)",
            (user_id,),
        )
        remaining = max(EGG_LIMIT - winner_count - 1, 0)
        conn.execute("COMMIT")

        return {
            "status": "success",
            "remaining": remaining,
            "message": "Golden egg claimed.",
        }


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
for route in mcp.sse_app().routes:
    app.routes.append(route)
app.add_middleware(PokeUserMiddleware)
app.add_route("/", health, methods=["GET"])
app.add_route("/health", health, methods=["GET"])
