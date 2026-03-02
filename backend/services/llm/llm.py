"""
LLM Service
Calls DashScope/OpenAI-compatible LLM API
"""

import json
from typing import AsyncGenerator, Optional

import httpx
from core.config import get_settings
from loguru import logger

settings = get_settings()


class LLMService:
    """
    LLM service using DashScope API.
    Compatible with OpenAI chat completions API format.
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
    ) -> str:
        """
        Generate chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            top_p: Top-p sampling parameter

        Returns:
            Generated text response
        """
        client = await self._get_client()

        try:
            response = await client.post(
                f"{settings.LLM_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.LLM_MODEL_NAME,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json()

            # Extract response content
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""

        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"LLM API 调用失败: {e.response.status_code}")
        except Exception as e:
            logger.error(f"LLM error: {e}")
            raise

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            top_p: Top-p sampling parameter

        Yields:
            Generated text chunks
        """
        client = await self._get_client()

        try:
            async with client.stream(
                "POST",
                f"{settings.LLM_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.LLM_MODEL_NAME,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # SSE format: "data: {...}"
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            logger.error(f"LLM streaming error: {e.response.status_code}")
            yield f"\n\n[错误: LLM API 调用失败]"
        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            yield f"\n\n[错误: {str(e)}]"

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
llm_service = LLMService()
