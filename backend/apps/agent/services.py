from __future__ import annotations

from common.llm import LLMConfigurationError, LLMProviderError, LLMRequestError, LLMTimeoutError

from .contracts import AgentAskRequest, AgentAskResult
from .tools import (
    AgentToolError,
    AnalyticsIntentTool,
    AnalyticsQueryTool,
    DetectionGroundingTool,
    LLMAnswerTool,
)


class AgentServiceError(Exception):
    def __init__(self, message: str, *, status: int = 400, code: int = 400) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class AgentOrchestratorService:
    def __init__(self) -> None:
        self.detection_grounding_tool = DetectionGroundingTool()
        self.analytics_intent_tool = AnalyticsIntentTool()
        self.analytics_query_tool = AnalyticsQueryTool()
        self.llm_answer_tool = LLMAnswerTool()

    def ask(self, request: AgentAskRequest) -> AgentAskResult:
        try:
            if request.agent_type == "analytics_qa":
                return self._ask_analytics(request)
            if request.agent_type == "detection_explanation":
                return self._ask_detection(request)
        except AgentToolError as exc:
            raise AgentServiceError(str(exc), status=exc.status, code=400) from exc
        except LLMConfigurationError as exc:
            raise AgentServiceError(str(exc), status=503, code=503) from exc
        except LLMTimeoutError as exc:
            raise AgentServiceError(str(exc), status=504, code=504) from exc
        except (LLMRequestError, LLMProviderError) as exc:
            raise AgentServiceError(str(exc), status=502, code=502) from exc

        raise AgentServiceError(f"不支援的 agent_type：{request.agent_type}", status=400, code=400)

    def _ask_detection(self, request: AgentAskRequest) -> AgentAskResult:
        grounding_result = self.detection_grounding_tool.execute(
            task_no=request.task_no,
            image_id=request.image_id,
        )
        llm_result = self.llm_answer_tool.execute(
            agent_type=request.agent_type,
            question=request.question,
            grounding=grounding_result.payload["grounding"],
        )
        return AgentAskResult(
            agent_type=request.agent_type,
            task_no=grounding_result.payload["task_no"],
            image_id=grounding_result.payload["image_id"],
            question=request.question,
            answer=llm_result.payload["answer"],
            grounding=grounding_result.payload["grounding"],
            llm=llm_result.payload["llm"],
            trace=[grounding_result.trace, llm_result.trace],
        )

    def _ask_analytics(self, request: AgentAskRequest) -> AgentAskResult:
        intent_result = self.analytics_intent_tool.execute(question=request.question)
        grounding_result = self.analytics_query_tool.execute(spec=intent_result.payload)
        llm_result = self.llm_answer_tool.execute(
            agent_type=request.agent_type,
            question=request.question,
            grounding=grounding_result.payload,
        )
        return AgentAskResult(
            agent_type=request.agent_type,
            question=request.question,
            answer=llm_result.payload["answer"],
            grounding=grounding_result.payload,
            llm=llm_result.payload["llm"],
            trace=[intent_result.trace, grounding_result.trace, llm_result.trace],
        )
