from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_services.common.settings import TrainingMCPSettings

from .facade import TrainingMCPFacade
from .prompts import register_training_prompts
from .resources import register_training_resources
from .tools import register_training_tools


def create_training_server(settings: TrainingMCPSettings | None = None) -> FastMCP:
    """建立 training MCP server。"""

    resolved_settings = settings or TrainingMCPSettings()
    facade = TrainingMCPFacade(resolved_settings)
    mcp = FastMCP(resolved_settings.app_name, json_response=resolved_settings.json_response)
    register_training_tools(mcp, facade)
    register_training_resources(mcp, facade)
    register_training_prompts(mcp)
    return mcp
