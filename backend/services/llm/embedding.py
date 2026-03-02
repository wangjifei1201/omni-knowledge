"""
Embedding Service
Calls DashScope/OpenAI-compatible embedding API
"""

import asyncio
from typing import Optional

import httpx
from core.config import get_settings
from loguru import logger

settings = get_settings()


class EmbeddingService:
    """
    Embedding service using DashScope API.
    Compatible with OpenAI embedding API format.
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        embeddings = await self.embed_batch([text])
        return embeddings[0] if embeddings else []

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 10,
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        client = await self._get_client()
        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            try:
                response = await client.post(
                    f"{settings.EMBEDDING_API_BASE}/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.EMBEDDING_MODEL_NAME,
                        "input": batch,
                        "encoding_format": "float",
                    },
                )
                response.raise_for_status()
                result = response.json()

                # Extract embeddings from response
                # DashScope returns format: {"data": [{"embedding": [...], "index": 0}, ...]}
                batch_embeddings = [None] * len(batch)
                for item in result.get("data", []):
                    idx = item.get("index", 0)
                    if idx < len(batch_embeddings):
                        batch_embeddings[idx] = item.get("embedding", [])

                all_embeddings.extend(batch_embeddings)

            except httpx.HTTPStatusError as e:
                logger.error(f"Embedding API error: {e.response.status_code} - {e.response.text}")
                # Return empty embeddings for failed batch
                all_embeddings.extend([[] for _ in batch])
            except Exception as e:
                logger.error(f"Embedding error: {e}")
                all_embeddings.extend([[] for _ in batch])

        return all_embeddings

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
embedding_service = EmbeddingService()
