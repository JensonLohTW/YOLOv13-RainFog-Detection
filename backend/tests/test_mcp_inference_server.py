import json
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

mcp = pytest.importorskip("mcp")
from mcp.shared.memory import create_connected_server_and_client_session

import inference_service.core.config as inference_config
from mcp_services.inference.server import create_inference_server


def _extract_payload(result):
    structured = getattr(result, "structuredContent", None)
    if structured:
        if isinstance(structured, dict) and set(structured.keys()) == {"result"}:
            return structured["result"]
        return structured
    return json.loads(result.content[0].text)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_inference_mcp_run_inference_and_read_resource(tmp_path: Path):
    image_path = tmp_path / "demo.jpg"
    Image.new("RGB", (64, 64), color=(20, 40, 60)).save(image_path, format="JPEG")

    with patch.object(inference_config.settings, "model_mode", "mock"):
        async with create_connected_server_and_client_session(
            create_inference_server(), raise_exceptions=True
        ) as client:
            result = await client.call_tool(
                "run_inference",
                {
                    "image_path": str(image_path),
                    "scene": "rain_fog",
                    "recognition_mode": "image",
                },
            )
            payload = _extract_payload(result)
            assert payload["success"] is True
            assert payload["objects"][0]["class_name"] == "car"

            resource = await client.read_resource("rainfog://inference/model/current")
            model_payload = json.loads(resource.contents[0].text)
            assert model_payload["engine_type"] == "mock"


@pytest.mark.anyio
async def test_inference_mcp_exposes_capabilities_resource():
    async with create_connected_server_and_client_session(
        create_inference_server(), raise_exceptions=True
    ) as client:
        resource = await client.read_resource("rainfog://inference/runtime/capabilities")
        payload = json.loads(resource.contents[0].text)
        assert "manual" in payload["preprocess_modes"]
        assert payload["supports_mock"] is True
