from __future__ import annotations

import json
from typing import Any


class MCPFacadeError(RuntimeError):
    """封裝應用層錯誤，避免在 MCP 介面直接暴露底層例外。"""


def dumps_json(payload: Any) -> str:
    """將資料穩定轉為 UTF-8 友善的 JSON 文字。"""

    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
