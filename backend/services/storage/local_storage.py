"""
Local File Storage Service
Replaces MinIO with local filesystem storage for documents
"""

import os
import shutil
import hashlib
import aiofiles
import aiofiles.os
import uuid
from datetime import datetime
from typing import Optional, BinaryIO
from pathlib import Path

from core.config import get_settings

settings = get_settings()


class LocalStorageService:
    """
    Local filesystem storage service for documents.
    Provides:
    - File upload/download
    - File deletion
    - Directory management
    - File metadata
    """

    def __init__(self):
        self._initialized = False
        self._base_path: Path = None

    async def initialize(self):
        """Initialize storage directories"""
        if self._initialized:
            return

        self._base_path = Path(settings.LOCAL_STORAGE_PATH)

        # Create base directories
        directories = [
            self._base_path / "documents",      # Original uploaded files
            self._base_path / "processed",      # Processed/parsed content
            self._base_path / "thumbnails",     # Document thumbnails
            self._base_path / "temp",           # Temporary files
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        self._initialized = True

    def _get_file_path(self, category: str, filename: str) -> Path:
        """Get full file path for a category and filename"""
        return self._base_path / category / filename

    def _generate_storage_name(self, original_name: str, doc_id: str) -> str:
        """Generate unique storage filename preserving extension"""
        ext = Path(original_name).suffix.lower()
        # Use doc_id + short uuid for uniqueness
        short_id = uuid.uuid4().hex[:8]
        return f"{doc_id}_{short_id}{ext}"

    async def upload_file(
        self,
        file_content: bytes,
        original_name: str,
        doc_id: str,
        category: str = "documents",
    ) -> dict:
        """
        Upload a file to local storage.

        Args:
            file_content: File content as bytes
            original_name: Original filename
            doc_id: Document ID for organizing files
            category: Storage category (documents, processed, etc.)

        Returns:
            Dict with storage info: path, size, hash, etc.
        """
        await self.initialize()

        storage_name = self._generate_storage_name(original_name, doc_id)
        file_path = self._get_file_path(category, storage_name)

        # Write file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)

        # Calculate hash
        file_hash = hashlib.md5(file_content).hexdigest()

        return {
            "storage_path": str(file_path),
            "storage_name": storage_name,
            "original_name": original_name,
            "category": category,
            "size": len(file_content),
            "hash": file_hash,
            "uploaded_at": datetime.now().isoformat(),
        }

    async def upload_file_stream(
        self,
        file_stream: BinaryIO,
        original_name: str,
        doc_id: str,
        category: str = "documents",
        chunk_size: int = 1024 * 1024,  # 1MB chunks
    ) -> dict:
        """
        Upload a file from stream (for large files).

        Args:
            file_stream: File-like object
            original_name: Original filename
            doc_id: Document ID
            category: Storage category
            chunk_size: Read chunk size

        Returns:
            Dict with storage info
        """
        await self.initialize()

        storage_name = self._generate_storage_name(original_name, doc_id)
        file_path = self._get_file_path(category, storage_name)

        total_size = 0
        hasher = hashlib.md5()

        async with aiofiles.open(file_path, 'wb') as f:
            while True:
                chunk = file_stream.read(chunk_size)
                if not chunk:
                    break
                await f.write(chunk)
                hasher.update(chunk)
                total_size += len(chunk)

        return {
            "storage_path": str(file_path),
            "storage_name": storage_name,
            "original_name": original_name,
            "category": category,
            "size": total_size,
            "hash": hasher.hexdigest(),
            "uploaded_at": datetime.now().isoformat(),
        }

    async def download_file(
        self,
        storage_path: str,
    ) -> Optional[bytes]:
        """
        Download a file by storage path.

        Args:
            storage_path: Full storage path

        Returns:
            File content as bytes, or None if not found
        """
        await self.initialize()

        path = Path(storage_path)
        if not path.exists():
            return None

        async with aiofiles.open(path, 'rb') as f:
            return await f.read()

    async def get_file_stream(
        self,
        storage_path: str,
        chunk_size: int = 1024 * 1024,
    ):
        """
        Get file as async generator for streaming.

        Args:
            storage_path: Full storage path
            chunk_size: Chunk size for streaming

        Yields:
            File content chunks
        """
        await self.initialize()

        path = Path(storage_path)
        if not path.exists():
            return

        async with aiofiles.open(path, 'rb') as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    async def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file by storage path.

        Args:
            storage_path: Full storage path

        Returns:
            True if deleted, False if not found
        """
        await self.initialize()

        path = Path(storage_path)
        if not path.exists():
            return False

        await aiofiles.os.remove(path)
        return True

    async def delete_doc_files(self, doc_id: str) -> int:
        """
        Delete all files associated with a document ID.

        Args:
            doc_id: Document ID

        Returns:
            Number of files deleted
        """
        await self.initialize()

        deleted_count = 0
        categories = ["documents", "processed", "thumbnails"]

        for category in categories:
            category_path = self._base_path / category
            if not category_path.exists():
                continue

            for file_path in category_path.iterdir():
                if file_path.is_file() and file_path.name.startswith(doc_id):
                    await aiofiles.os.remove(file_path)
                    deleted_count += 1

        return deleted_count

    async def file_exists(self, storage_path: str) -> bool:
        """Check if a file exists"""
        await self.initialize()
        return Path(storage_path).exists()

    async def get_file_info(self, storage_path: str) -> Optional[dict]:
        """
        Get file metadata.

        Args:
            storage_path: Full storage path

        Returns:
            Dict with file info, or None if not found
        """
        await self.initialize()

        path = Path(storage_path)
        if not path.exists():
            return None

        stat = path.stat()
        return {
            "storage_path": str(path),
            "filename": path.name,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    async def list_files(
        self,
        category: str = "documents",
        prefix: Optional[str] = None,
    ) -> list[dict]:
        """
        List files in a category.

        Args:
            category: Storage category
            prefix: Optional filename prefix filter

        Returns:
            List of file info dicts
        """
        await self.initialize()

        category_path = self._base_path / category
        if not category_path.exists():
            return []

        files = []
        for file_path in category_path.iterdir():
            if not file_path.is_file():
                continue
            if prefix and not file_path.name.startswith(prefix):
                continue

            stat = file_path.stat()
            files.append({
                "storage_path": str(file_path),
                "filename": file_path.name,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

        return sorted(files, key=lambda x: x['modified_at'], reverse=True)

    async def get_storage_stats(self) -> dict:
        """Get storage usage statistics"""
        await self.initialize()

        stats = {
            "total_size": 0,
            "file_count": 0,
            "categories": {},
        }

        for category in ["documents", "processed", "thumbnails", "temp"]:
            category_path = self._base_path / category
            if not category_path.exists():
                continue

            category_size = 0
            category_count = 0

            for file_path in category_path.iterdir():
                if file_path.is_file():
                    category_size += file_path.stat().st_size
                    category_count += 1

            stats["categories"][category] = {
                "size": category_size,
                "count": category_count,
            }
            stats["total_size"] += category_size
            stats["file_count"] += category_count

        return stats

    async def cleanup_temp(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of files deleted
        """
        await self.initialize()

        temp_path = self._base_path / "temp"
        if not temp_path.exists():
            return 0

        deleted_count = 0
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)

        for file_path in temp_path.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff:
                await aiofiles.os.remove(file_path)
                deleted_count += 1

        return deleted_count


# Singleton instance
local_storage = LocalStorageService()
