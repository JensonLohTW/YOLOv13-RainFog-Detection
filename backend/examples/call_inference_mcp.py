"""最小可執行的 inference MCP 調用示例。"""

from __future__ import annotations

import argparse
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path")
    parser.add_argument("--base-url", default="http://127.0.0.1:9100/mcp")
    args = parser.parse_args()

    async with streamable_http_client(args.base_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "run_inference",
                {
                    "image_path": args.image_path,
                    "scene": "rain_fog",
                    "recognition_mode": "image",
                },
            )
            print(json.dumps(result.structuredContent, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
