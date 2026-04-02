from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolExecutionTrace:
    tool_name: str
    latency_ms: int
    status: str = "success"
    version: str = "v1"
    error_code: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentAskRequest:
    agent_type: str
    question: str
    task_no: str = ""
    image_id: int | None = None


@dataclass(frozen=True)
class AgentAskResult:
    agent_type: str
    question: str
    answer: str
    grounding: dict[str, Any]
    llm: dict[str, Any]
    trace: list[ToolExecutionTrace]
    task_no: str = ""
    image_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "task_no": self.task_no,
            "image_id": self.image_id,
            "question": self.question,
            "answer": self.answer,
            "grounding": self.grounding,
            "llm": self.llm,
            "trace": [item.to_dict() for item in self.trace],
        }
