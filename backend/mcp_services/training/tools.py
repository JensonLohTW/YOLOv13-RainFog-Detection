from __future__ import annotations

from mcp_services.common.errors import MCPFacadeError

from .facade import TrainingMCPFacade
from .schemas import CreateTrainingJobInput


def register_training_tools(mcp, facade: TrainingMCPFacade) -> None:
    """註冊 training MCP tools。"""

    @mcp.tool()
    def list_datasets():
        """列出可用訓練資料集。"""

        return facade.list_datasets()

    @mcp.tool()
    def list_training_jobs(status_filter: str = ""):
        """列出訓練任務，可依狀態過濾。"""

        return facade.list_jobs(status_filter=status_filter)

    @mcp.tool()
    def create_training_job(
        dataset_id: int,
        model_file: str = "yolov13l.pt",
        epochs: int = 50,
        batch: int = 4,
        imgsz: int = 640,
        device: str = "0",
        workers: int = 0,
        patience: int = 20,
        preprocess_mode: str = "off",
        preprocess_profile: str = "",
        preprocess_algorithms: list[str] | None = None,
        preprocess_algorithm_params: dict | None = None,
        preprocess_enable_gamma: bool = False,
    ):
        """建立並啟動訓練任務。"""

        payload = CreateTrainingJobInput(
            dataset_id=dataset_id,
            model_file=model_file,
            epochs=epochs,
            batch=batch,
            imgsz=imgsz,
            device=device,
            workers=workers,
            patience=patience,
            preprocess_mode=preprocess_mode,
            preprocess_profile=preprocess_profile,
            preprocess_algorithms=list(preprocess_algorithms or []),
            preprocess_algorithm_params=dict(preprocess_algorithm_params or {}),
            preprocess_enable_gamma=preprocess_enable_gamma,
        )
        try:
            return facade.create_job(payload)
        except MCPFacadeError as exc:
            raise ValueError(str(exc)) from exc

    @mcp.tool()
    def cancel_training_job(job_id: int):
        """取消指定訓練任務。"""

        try:
            return facade.cancel_job(job_id)
        except MCPFacadeError as exc:
            raise ValueError(str(exc)) from exc

    @mcp.tool()
    def retry_training_job(job_id: int):
        """重試既有訓練任務。"""

        try:
            return facade.retry_job(job_id)
        except MCPFacadeError as exc:
            raise ValueError(str(exc)) from exc

    @mcp.tool()
    def deploy_training_model(job_id: int, model_alias: str = ""):
        """將訓練完成的模型部署到推理模型目錄。"""

        try:
            return facade.deploy_job(job_id, model_alias)
        except MCPFacadeError as exc:
            raise ValueError(str(exc)) from exc

    @mcp.tool()
    def validate_training_baseline(job_id: int):
        """對指定任務執行基線驗證。"""

        try:
            return facade.validate_baseline(job_id)
        except MCPFacadeError as exc:
            raise ValueError(str(exc)) from exc
