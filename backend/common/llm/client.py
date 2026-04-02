from __future__ import annotations

from typing import Any

import httpx

from .types import LLMResponse, LLMSettings


class LLMProviderError(Exception):
    """Base error for LLM provider failures."""


class LLMConfigurationError(LLMProviderError):
    """Raised when the LLM provider is missing required configuration."""


class LLMTimeoutError(LLMProviderError):
    """Raised when the upstream LLM request times out."""


class LLMRequestError(LLMProviderError):
    """Raised when the upstream LLM request fails."""


class BaseLLMProvider:
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        settings: LLMSettings,
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        raise NotImplementedError


class MockLLMProvider(BaseLLMProvider):
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        settings: LLMSettings,
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        grounding = dict((metadata or {}).get("grounding") or {})
        class_summary = grounding.get("class_summary") or []
        warnings = grounding.get("warnings") or []
        lowest_confidence = grounding.get("lowest_confidence_objects") or []
        question = str((metadata or {}).get("question") or "").strip()

        if grounding.get("object_count", 0) <= 0:
            conclusion = "這張圖片的目前檢測結果沒有偵測到任何目標。"
        else:
            classes = ", ".join(
                f"{item['class_name']} x{item['count']}" for item in class_summary[:4] if item.get("class_name")
            )
            conclusion = (
                f"根據目前檢測結果，共偵測到 {grounding.get('object_count', 0)} 個目標，"
                f"主要類別為 {classes or '未提供'}。"
            )

        evidence = []
        if class_summary:
            evidence.append(
                "各類別平均置信度為 "
                + "；".join(
                    f"{item['class_name']} {item['avg_confidence']:.2f}" for item in class_summary[:4]
                )
                + "。"
            )
        if lowest_confidence:
            evidence.append(
                "較不確定的目標包括 "
                + "；".join(
                    f"{item['class_name']} ({item['confidence']:.2f})" for item in lowest_confidence[:3]
                )
                + "。"
            )
        if not evidence:
            evidence.append("目前可用證據僅包含任務設定與推理結果摘要。")

        reason = "目前沒有足夠訊號指出明確誤判原因。"
        if warnings:
            reason = "；".join(warnings[:3]) + "。"

        next_step = (
            "建議人工複核低置信度框、重新檢視原圖與結果圖，必要時調整 confidence / IOU 閾值後重跑一次。"
        )

        answer = "\n".join(
            [
                "### 結論",
                conclusion,
                "",
                "### 依據",
                " ".join(evidence),
                "",
                "### 可能誤判原因",
                reason,
                "",
                "### 建議下一步",
                next_step,
                "",
                f"補充問題：{question or '未提供'}",
            ]
        )
        return LLMResponse(
            text=answer.strip(),
            provider=settings.provider,
            model=settings.model or "mock-llm",
            finish_reason="stop",
            raw={"mock": True},
        )


class OpenAICompatibleLLMProvider(BaseLLMProvider):
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        settings: LLMSettings,
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        del metadata

        if not settings.base_url:
            raise LLMConfigurationError("LLM_BASE_URL 尚未配置。")
        if not settings.model:
            raise LLMConfigurationError("LLM_MODEL 尚未配置。")
        if not settings.api_key:
            raise LLMConfigurationError("LLM_API_KEY 尚未配置。")

        url = f"{settings.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": settings.model,
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            with httpx.Client(timeout=settings.timeout) as client:
                response = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {settings.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("LLM 請求逾時，請稍後再試。") from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise LLMRequestError(f"LLM 服務返回錯誤：{detail}") from exc
        except httpx.HTTPError as exc:
            raise LLMRequestError("無法連接 LLM 服務。") from exc

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise LLMRequestError("LLM 未返回可用結果。")

        choice = choices[0]
        message = choice.get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        else:
            text = str(content)

        text = text.strip()
        if not text:
            raise LLMRequestError("LLM 返回了空內容。")

        return LLMResponse(
            text=text,
            provider=settings.provider,
            model=str(data.get("model") or settings.model),
            finish_reason=str(choice.get("finish_reason") or ""),
            raw=data,
        )


class LLMClient:
    PROVIDER_ALIASES = {
        "mock": "mock",
        "openai": "openai_compatible",
        "openai_compatible": "openai_compatible",
    }

    def __init__(self) -> None:
        self._providers = {
            "mock": MockLLMProvider(),
            "openai_compatible": OpenAICompatibleLLMProvider(),
        }

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        settings: LLMSettings,
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        provider_key = self.PROVIDER_ALIASES.get(settings.provider.strip().lower(), settings.provider.strip().lower())
        provider = self._providers.get(provider_key)
        if provider is None:
            raise LLMConfigurationError(f"不支援的 LLM_PROVIDER：{settings.provider}")
        return provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            settings=settings,
            metadata=metadata,
        )
