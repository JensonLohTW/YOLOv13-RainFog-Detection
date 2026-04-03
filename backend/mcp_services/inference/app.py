from __future__ import annotations

from mcp_services.common.bootstrap import build_streamable_http_app
from mcp_services.common.logging import configure_logging
from mcp_services.common.settings import InferenceMCPSettings

from .server import create_inference_server


def create_app():
    """建立 inference MCP ASGI 應用。"""

    settings = InferenceMCPSettings()
    configure_logging(settings.log_level)
    server = create_inference_server(settings)
    return build_streamable_http_app(server, settings.streamable_http_path)


app = create_app()
