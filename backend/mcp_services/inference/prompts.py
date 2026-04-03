from __future__ import annotations


def register_inference_prompts(mcp) -> None:
    """註冊 inference MCP prompts。"""

    @mcp.prompt()
    def summarize_inference_result(result_json: str, audience: str = "工程師") -> str:
        """產生推理結果摘要提示。"""

        return (
            f"請以{audience}可快速理解的方式，整理以下 YOLO 推理結果。"
            "請說明偵測類別、置信度、預處理影響與可能的誤判風險。\n\n"
            f"{result_json}"
        )

    @mcp.prompt()
    def diagnose_inference_failure(error_message: str, request_json: str = "") -> str:
        """產生推理失敗診斷提示。"""

        return (
            "請根據以下錯誤訊息與請求內容，分析 YOLO 推理失敗的可能原因，"
            "並提出依序排查建議。\n\n"
            f"錯誤訊息：{error_message}\n"
            f"請求內容：{request_json}"
        )
