from __future__ import annotations


def register_training_prompts(mcp) -> None:
    """註冊 training MCP prompts。"""

    @mcp.prompt()
    def summarize_training_progress(job_json: str, focus: str = "整體收斂情況") -> str:
        """產生訓練進度摘要提示。"""

        return (
            "請閱讀以下訓練任務資訊，整理目前進度、關鍵指標、風險與下一步建議。"
            f"請特別聚焦：{focus}。\n\n{job_json}"
        )

    @mcp.prompt()
    def compare_training_with_baseline(visualization_json: str) -> str:
        """產生訓練結果與基線比較提示。"""

        return (
            "請根據以下訓練視覺化資料，比較目前模型與 baseline 的差異，"
            "並指出是否值得部署到推理服務。\n\n"
            f"{visualization_json}"
        )
