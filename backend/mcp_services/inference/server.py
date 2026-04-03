from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_services.common.settings import InferenceMCPSettings

from .facade import InferenceMCPFacade
from .prompts import register_inference_prompts
from .resources import register_inference_resources
from .tools import register_inference_tools


def create_inference_server(settings: InferenceMCPSettings | None = None) -> FastMCP:
    """建立 inference MCP server。"""

    resolved_settings = settings or InferenceMCPSettings()
    mcp = FastMCP(resolved_settings.app_name, json_response=resolved_settings.json_response)
    facade = InferenceMCPFacade()
    register_inference_tools(mcp, facade)
    register_inference_resources(mcp, facade)
    register_inference_prompts(mcp)
    return mcp
