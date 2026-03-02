"""
FAISS Vector Store Service
Local vector storage using FAISS for similarity search
"""

import os
import json
import asyncio
from typing import Optional
from dataclasses import dataclass, field
import numpy as np

from core.config import get_settings

settings = get_settings()


@dataclass
class VectorSearchResult:
    """Vector search result with metadata"""
    chunk_id: str = ""
    doc_id: str = ""
    doc_name: str = ""
    chapter: str = ""
    section: str = ""
    page: int = 0
    content: str = ""
    score: float = 0.0
    position: dict = field(default_factory=dict)


class FAISSVectorStore:
    """
    FAISS-based vector store for local similarity search.
    Supports:
    - Add vectors with metadata
    - Delete vectors by ID
    - Similarity search with optional filters
    - Persistence to disk
    """

    def __init__(self):
        self._initialized = False
        self._index = None
        self._id_map: dict[int, str] = {}  # faiss_id -> chunk_id
        self._chunk_id_to_faiss_id: dict[str, int] = {}  # chunk_id -> faiss_id
        self._metadata: dict[str, dict] = {}  # chunk_id -> metadata
        self._next_id = 0
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize FAISS index"""
        if self._initialized:
            return

        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu is required. Install it with: pip install faiss-cpu")

        # Create or load index
        index_path = settings.FAISS_INDEX_PATH
        os.makedirs(os.path.dirname(index_path), exist_ok=True)

        index_file = f"{index_path}/faiss.index"
        meta_file = f"{index_path}/metadata.json"

        if os.path.exists(index_file) and os.path.exists(meta_file):
            # Load existing index
            self._index = faiss.read_index(index_file)
            with open(meta_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._id_map = {int(k): v for k, v in data.get('id_map', {}).items()}
                self._chunk_id_to_faiss_id = data.get('chunk_id_to_faiss_id', {})
                self._metadata = data.get('metadata', {})
                self._next_id = data.get('next_id', 0)
        else:
            # Create new index with L2 distance
            dimension = settings.EMBEDDING_DIMENSION
            self._index = faiss.IndexFlatIP(dimension)  # Inner Product for cosine similarity

        self._initialized = True

    async def save(self):
        """Persist index to disk"""
        if not self._initialized or self._index is None:
            return

        try:
            import faiss
        except ImportError:
            return

        async with self._lock:
            index_path = settings.FAISS_INDEX_PATH
            os.makedirs(index_path, exist_ok=True)

            index_file = f"{index_path}/faiss.index"
            meta_file = f"{index_path}/metadata.json"

            faiss.write_index(self._index, index_file)
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'id_map': {str(k): v for k, v in self._id_map.items()},
                    'chunk_id_to_faiss_id': self._chunk_id_to_faiss_id,
                    'metadata': self._metadata,
                    'next_id': self._next_id,
                }, f, ensure_ascii=False, indent=2)

    async def add_vectors(
        self,
        vectors: list[list[float]],
        chunk_ids: list[str],
        metadatas: list[dict],
    ) -> list[str]:
        """
        Add vectors with metadata to the index.

        Args:
            vectors: List of embedding vectors
            chunk_ids: Unique identifiers for each chunk
            metadatas: Metadata for each chunk (doc_id, content, etc.)

        Returns:
            List of added chunk_ids
        """
        await self.initialize()

        if len(vectors) != len(chunk_ids) or len(vectors) != len(metadatas):
            raise ValueError("vectors, chunk_ids, and metadatas must have the same length")

        if not vectors:
            return []

        async with self._lock:
            # Normalize vectors for cosine similarity
            vectors_np = np.array(vectors, dtype=np.float32)
            faiss_module = __import__('faiss')
            faiss_module.normalize_L2(vectors_np)

            # Add to index
            self._index.add(vectors_np)

            # Update mappings
            added_ids = []
            for i, (chunk_id, metadata) in enumerate(zip(chunk_ids, metadatas)):
                faiss_id = self._next_id + i
                self._id_map[faiss_id] = chunk_id
                self._chunk_id_to_faiss_id[chunk_id] = faiss_id
                self._metadata[chunk_id] = metadata
                added_ids.append(chunk_id)

            self._next_id += len(vectors)

        # Auto-save after adding
        await self.save()

        return added_ids

    async def delete_vectors(self, chunk_ids: list[str]) -> int:
        """
        Delete vectors by chunk_ids.
        Note: FAISS IndexFlatIP doesn't support direct deletion.
        We mark them as deleted and rebuild periodically.
        """
        await self.initialize()

        deleted_count = 0
        async with self._lock:
            for chunk_id in chunk_ids:
                if chunk_id in self._chunk_id_to_faiss_id:
                    faiss_id = self._chunk_id_to_faiss_id.pop(chunk_id)
                    self._id_map.pop(faiss_id, None)
                    self._metadata.pop(chunk_id, None)
                    deleted_count += 1

        await self.save()
        return deleted_count

    async def delete_by_doc_id(self, doc_id: str) -> int:
        """Delete all vectors belonging to a document"""
        await self.initialize()

        chunk_ids_to_delete = [
            chunk_id for chunk_id, meta in self._metadata.items()
            if meta.get('doc_id') == doc_id
        ]

        return await self.delete_vectors(chunk_ids_to_delete)

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filters: Optional[dict] = None,
    ) -> list[VectorSearchResult]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional filters (doc_ids, etc.)

        Returns:
            List of VectorSearchResult sorted by similarity
        """
        await self.initialize()

        if self._index.ntotal == 0:
            return []

        # Normalize query vector for cosine similarity
        query_np = np.array([query_vector], dtype=np.float32)
        faiss_module = __import__('faiss')
        faiss_module.normalize_L2(query_np)

        # Search more than top_k to account for filtering and deleted vectors
        search_k = min(top_k * 3, self._index.ntotal)
        distances, indices = self._index.search(query_np, search_k)

        results = []
        for score, faiss_id in zip(distances[0], indices[0]):
            if faiss_id == -1:
                continue

            chunk_id = self._id_map.get(faiss_id)
            if not chunk_id:
                continue  # Deleted vector

            metadata = self._metadata.get(chunk_id, {})

            # Apply filters
            if filters:
                doc_ids = filters.get('doc_ids')
                if doc_ids and metadata.get('doc_id') not in doc_ids:
                    continue

            results.append(VectorSearchResult(
                chunk_id=chunk_id,
                doc_id=metadata.get('doc_id', ''),
                doc_name=metadata.get('doc_name', ''),
                chapter=metadata.get('chapter', ''),
                section=metadata.get('section', ''),
                page=metadata.get('page', 0),
                content=metadata.get('content', ''),
                score=float(score),
                position=metadata.get('position', {}),
            ))

            if len(results) >= top_k:
                break

        return results

    async def get_vector_count(self) -> int:
        """Get total number of vectors in index"""
        await self.initialize()
        return len(self._chunk_id_to_faiss_id)

    async def get_doc_chunk_count(self, doc_id: str) -> int:
        """Get number of chunks for a specific document"""
        await self.initialize()
        return sum(
            1 for meta in self._metadata.values()
            if meta.get('doc_id') == doc_id
        )

    async def rebuild_index(self):
        """
        Rebuild index to reclaim space from deleted vectors.
        Call this periodically when many vectors have been deleted.
        """
        await self.initialize()

        if not self._chunk_id_to_faiss_id:
            return

        faiss_module = __import__('faiss')

        async with self._lock:
            # Collect all valid vectors
            valid_chunk_ids = list(self._chunk_id_to_faiss_id.keys())
            if not valid_chunk_ids:
                # Reset to empty index
                dimension = settings.EMBEDDING_DIMENSION
                self._index = faiss_module.IndexFlatIP(dimension)
                self._id_map = {}
                self._chunk_id_to_faiss_id = {}
                self._next_id = 0
                return

            # For now, we can't easily extract vectors from FAISS IndexFlat
            # A full rebuild would require re-embedding all chunks
            # This is a placeholder for future optimization
            pass

        await self.save()


# Singleton instance
faiss_vector_store = FAISSVectorStore()
