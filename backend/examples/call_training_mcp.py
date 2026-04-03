"""最小可執行的 training MCP 調用示例。"""

from __future__ import annotations

import argparse
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:9101/mcp")
    parser.add_argument("--dataset-id", type=int, default=0)
    args = parser.parse_args()

    async with streamable_http_client(args.base_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            datasets = await session.call_tool("list_datasets", {})
            print("=== datasets ===")
            print(json.dumps(datasets.structuredContent, ensure_ascii=False, indent=2))

            if args.dataset_id > 0:
                job = await session.call_tool(
                    "create_training_job",
                    {
                        "dataset_id": args.dataset_id,
                        "epochs": 5,
                        "batch": 2,
                        "imgsz": 640,
                    },
                )
                print("=== created job ===")
                print(json.dumps(job.structuredContent, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
