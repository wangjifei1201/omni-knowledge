"""
Reranker Service
Calls DashScope text-rerank API for result reranking.
"""

from typing import Optional

import httpx
from core.config import get_settings
from loguru import logger

settings = get_settings()


class RerankerService:
    """
    Reranker service using DashScope API.
    Reranks search results based on relevance to query.
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._available: Optional[bool] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: Optional[int] = None,
    ) -> list[dict]:
        """
        Rerank documents based on query relevance.

        Args:
            query: Search query
            documents: List of document texts to rerank
            top_n: Number of top results to return (default: all)

        Returns:
            List of dicts with 'index' and 'relevance_score', sorted by score descending
        """
        if not documents:
            return []

        if top_n is None:
            top_n = len(documents)

        # If reranker is known unavailable, use fallback
        if self._available is False:
            return self._fallback_ranking(documents, top_n)

        client = await self._get_client()

        try:
            # DashScope text-rerank API
            # Docs: https://help.aliyun.com/zh/model-studio/developer-reference/text-rerank-api
            response = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
                headers={
                    "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gte-rerank",
                    "input": {
                        "query": query,
                        "documents": documents,
                    },
                    "parameters": {
                        "top_n": top_n,
                        "return_documents": False,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()

            self._available = True

            # DashScope format: {"output": {"results": [{"index": 0, "relevance_score": 0.95}, ...]}}
            output = result.get("output", {})
            results = output.get("results", [])

            if results:
                logger.debug(f"Reranker returned {len(results)} results")
                return sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)

            return self._fallback_ranking(documents, top_n)

        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:200] if e.response.text else ""
            logger.warning(f"Reranker API error {e.response.status_code}: {error_text}")
            if e.response.status_code in [404, 403]:
                self._available = False
            return self._fallback_ranking(documents, top_n)
        except Exception as e:
            logger.warning(f"Reranker error: {e}")
            return self._fallback_ranking(documents, top_n)

    def _fallback_ranking(self, documents: list[str], top_n: int) -> list[dict]:
        """Fallback: use original order with decaying scores."""
        return [{"index": i, "relevance_score": 1.0 / (1.0 + i * 0.1)} for i in range(min(len(documents), top_n))]

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
reranker_service = RerankerService()
