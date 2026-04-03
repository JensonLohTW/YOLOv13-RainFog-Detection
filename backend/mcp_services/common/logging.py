from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """初始化 MCP 服務日誌設定。"""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
