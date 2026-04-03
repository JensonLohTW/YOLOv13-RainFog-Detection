from __future__ import annotations

from mcp_services.common.errors import MCPFacadeError, dumps_json

from .facade import TrainingMCPFacade


def register_training_resources(mcp, facade: TrainingMCPFacade) -> None:
    """註冊 training MCP resources。"""

    @mcp.resource("rainfog://training/datasets")
    def training_datasets_resource() -> str:
        return dumps_json(facade.list_datasets())

    @mcp.resource("rainfog://training/jobs")
    def training_jobs_resource() -> str:
        return dumps_json(facade.list_jobs())

    @mcp.resource("rainfog://training/jobs/{job_id}")
    def training_job_resource(job_id: str) -> str:
        try:
            return dumps_json(facade.get_job_detail(int(job_id)))
        except MCPFacadeError as exc:
            raise ValueError(str(exc)) from exc

    @mcp.resource("rainfog://training/jobs/{job_id}/log")
    def training_job_log_resource(job_id: str) -> str:
        try:
            return dumps_json(facade.get_job_log(int(job_id)))
        except MCPFacadeError as exc:
            raise ValueError(str(exc)) from exc

    @mcp.resource("rainfog://training/jobs/{job_id}/visualization")
    def training_job_visualization_resource(job_id: str) -> str:
        try:
            return dumps_json(facade.get_job_visualization(int(job_id)))
        except MCPFacadeError as exc:
            raise ValueError(str(exc)) from exc
