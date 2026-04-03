from __future__ import annotations

from mcp_services.common.errors import dumps_json

from .facade import InferenceMCPFacade


def register_inference_resources(mcp, facade: InferenceMCPFacade) -> None:
    """註冊 inference MCP resources。"""

    @mcp.resource("rainfog://inference/model/current")
    def current_model_resource() -> str:
        return dumps_json(facade.get_current_model())

    @mcp.resource("rainfog://inference/runtime/health")
    def runtime_health_resource() -> str:
        return dumps_json(facade.get_runtime_health().model_dump())

    @mcp.resource("rainfog://inference/runtime/capabilities")
    def runtime_capabilities_resource() -> str:
        return dumps_json(facade.get_runtime_capabilities().model_dump())
