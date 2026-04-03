import json
from pathlib import Path
from unittest.mock import patch

import pytest

mcp = pytest.importorskip("mcp")
from mcp import Client

from apps.training.models import TrainingDataset, TrainingJob
from mcp_services.training.app import create_app


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
@pytest.mark.django_db
async def test_training_mcp_lists_datasets():
    TrainingDataset.objects.create(
        name="toy-dataset",
        description="demo",
        dataset_path="/tmp/datasets/toy",
        num_train=8,
        num_val=2,
        num_classes=2,
        status=TrainingDataset.Status.READY,
    )

    async with Client(create_app(), raise_exceptions=True) as client:
        result = await client.call_tool("list_datasets", {})
        payload = _extract_payload(result)
        assert payload["total"] == 1
        assert payload["items"][0]["name"] == "toy-dataset"


@pytest.mark.anyio
@pytest.mark.django_db
@patch("apps.training.services.job_service.TrainingJobService.start_job")
async def test_training_mcp_creates_job_and_reads_resource(mock_start_job, tmp_path: Path):
    dataset = TrainingDataset.objects.create(
        name="ready-dataset",
        description="demo",
        dataset_path=str(tmp_path / "dataset"),
        num_train=10,
        num_val=2,
        num_classes=3,
        status=TrainingDataset.Status.READY,
    )

    def fake_start_job(job):
        Path(job.run_dir).mkdir(parents=True, exist_ok=True)
        Path(job.log_path).write_text("training started\n", encoding="utf-8")
        job.status = TrainingJob.Status.RUNNING
        job.started_at = job.started_at
        job.save(update_fields=["status", "updated_at"])
        return job

    mock_start_job.side_effect = fake_start_job

    async with Client(create_app(), raise_exceptions=True) as client:
        created = await client.call_tool(
            "create_training_job",
            {
                "dataset_id": dataset.id,
                "epochs": 3,
                "batch": 2,
                "imgsz": 640,
            },
        )
        created_payload = _extract_payload(created)
        assert created_payload["dataset_id"] == dataset.id
        assert created_payload["status"] == "RUNNING"

        resource = await client.read_resource(f"rainfog://training/jobs/{created_payload['id']}")
        resource_payload = json.loads(resource.contents[0].text)
        assert resource_payload["job_no"].startswith("TJ")

        log_resource = await client.read_resource(
            f"rainfog://training/jobs/{created_payload['id']}/log"
        )
        log_payload = json.loads(log_resource.contents[0].text)
        assert "training started" in log_payload["log"]
