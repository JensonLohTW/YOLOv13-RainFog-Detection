from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from starlette.applications import Starlette
from starlette.routing import Mount


def build_streamable_http_app(mcp_server: Any, path: str = "/mcp") -> Starlette:
    """建立可掛載於 Uvicorn 的 Streamable HTTP ASGI 應用。"""

    @asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp_server.session_manager.run():
            yield

    return Starlette(
        routes=[Mount(path, app=mcp_server.streamable_http_app())],
        lifespan=lifespan,
    )
