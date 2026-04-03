from __future__ import annotations

from mcp_services.common.errors import MCPFacadeError

from .facade import InferenceMCPFacade
from .schemas import RunInferenceInput


def register_inference_tools(mcp, facade: InferenceMCPFacade) -> None:
    """註冊 inference MCP tools。"""

    @mcp.tool()
    def run_inference(
        image_path: str,
        task_no: str = "",
        recognition_mode: str = "image",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        scene: str = "unknown",
        preprocess_mode: str = "off",
        preprocess_profile: str = "",
        preprocess_algorithms: list[str] | None = None,
        preprocess_algorithm_params: dict | None = None,
        preprocess_enable_gamma: bool = False,
        runtime_options: dict | None = None,
        mock: bool = True,
    ):
        """執行單張圖片推理並返回結構化結果。"""

        payload = RunInferenceInput(
            task_no=task_no,
            image_path=image_path,
            recognition_mode=recognition_mode,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            scene=scene,
            preprocess_mode=preprocess_mode,
            preprocess_profile=preprocess_profile,
            preprocess_algorithms=list(preprocess_algorithms or []),
            preprocess_algorithm_params=dict(preprocess_algorithm_params or {}),
            preprocess_enable_gamma=preprocess_enable_gamma,
            runtime_options=dict(runtime_options or {}),
            mock=mock,
        )
        try:
            return facade.run_inference(payload)
        except MCPFacadeError as exc:
            raise ValueError(str(exc)) from exc

    @mcp.tool()
    def get_current_model():
        """讀取目前載入中的推理模型資訊。"""

        return facade.get_current_model()

    @mcp.tool()
    def get_runtime_health():
        """讀取推理 MCP 服務健康狀態。"""

        return facade.get_runtime_health()
