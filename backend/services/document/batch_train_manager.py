"""
Batch Training Manager
Manages batch document training tasks
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from loguru import logger


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DocStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocTrainResult:
    doc_id: str
    doc_name: str
    status: DocStatus = DocStatus.PENDING
    error: Optional[str] = None


@dataclass
class BatchTrainTask:
    task_id: str
    doc_ids: list[str]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    results: dict[str, DocTrainResult] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.doc_ids)

    @property
    def completed(self) -> int:
        return sum(1 for r in self.results.values() if r.status == DocStatus.COMPLETED)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results.values() if r.status == DocStatus.FAILED)


class BatchTrainManager:
    """
    Manages batch training tasks for documents.
    Uses in-memory storage for task status tracking.
    """

    def __init__(self):
        self._tasks: dict[str, BatchTrainTask] = {}
        self._semaphore = asyncio.Semaphore(3)  # Limit concurrent processing
        self._cleanup_interval = 3600  # 1 hour
        self._task_ttl = 86400  # 24 hours

    def create_task(self, doc_ids: list[str], doc_names: dict[str, str]) -> str:
        """
        Create a new batch training task.

        Args:
            doc_ids: List of document IDs to train
            doc_names: Dict mapping doc_id to doc_name

        Returns:
            task_id
        """
        task_id = str(uuid.uuid4())
        task = BatchTrainTask(
            task_id=task_id,
            doc_ids=doc_ids,
            status=TaskStatus.PENDING,
            results={
                doc_id: DocTrainResult(
                    doc_id=doc_id,
                    doc_name=doc_names.get(doc_id, "未知文档"),
                    status=DocStatus.PENDING,
                )
                for doc_id in doc_ids
            },
        )
        self._tasks[task_id] = task
        logger.info(f"Created batch train task {task_id} with {len(doc_ids)} documents")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """
        Get the status of a batch training task.

        Returns:
            Task status dict or None if not found
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "total": task.total,
            "completed": task.completed,
            "failed": task.failed,
            "results": [
                {
                    "doc_id": r.doc_id,
                    "doc_name": r.doc_name,
                    "status": r.status.value,
                    "error": r.error,
                }
                for r in task.results.values()
            ],
        }

    def update_doc_status(
        self,
        task_id: str,
        doc_id: str,
        status: DocStatus,
        error: Optional[str] = None,
    ):
        """Update the status of a document in a task"""
        task = self._tasks.get(task_id)
        if task and doc_id in task.results:
            task.results[doc_id].status = status
            task.results[doc_id].error = error

    def update_task_status(self, task_id: str, status: TaskStatus):
        """Update the overall task status"""
        task = self._tasks.get(task_id)
        if task:
            task.status = status

    async def execute_batch_train(self, task_id: str):
        """
        Execute batch training for all documents in a task.
        This should be called as a background task.
        """
        from core.database import AsyncSessionLocal
        from models.document import Document
        from services.document.processor import document_processor
        from services.rag.vector_store import faiss_vector_store
        from sqlalchemy import select

        task = self._tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        task.status = TaskStatus.RUNNING
        logger.info(f"Starting batch train task {task_id}")

        async def process_single_doc(doc_id: str):
            """Process a single document with semaphore"""
            async with self._semaphore:
                self.update_doc_status(task_id, doc_id, DocStatus.PROCESSING)

                try:
                    async with AsyncSessionLocal() as db:
                        # Get document info
                        result = await db.execute(
                            select(Document).where(Document.id == doc_id, Document.is_deleted == False)
                        )
                        doc = result.scalar_one_or_none()

                        if not doc:
                            self.update_doc_status(task_id, doc_id, DocStatus.FAILED, "文档不存在")
                            return

                        if not doc.file_path:
                            self.update_doc_status(task_id, doc_id, DocStatus.FAILED, "文件不存在")
                            return

                        # Delete existing vectors
                        await faiss_vector_store.delete_by_doc_id(doc_id)

                        # Update document status to processing
                        doc.status = "processing"
                        await db.commit()

                        # Process document
                        process_result = await document_processor.process_document(
                            doc_id=doc.id,
                            file_path=doc.file_path,
                            file_type=doc.file_type,
                            doc_name=doc.doc_name,
                        )

                        # Update document status in database
                        doc.status = process_result.get("status", "failed")
                        doc.chunk_count = process_result.get("chunk_count", 0)
                        doc.page_count = process_result.get("page_count", 0)
                        await db.commit()

                        if process_result.get("status") == "completed":
                            self.update_doc_status(task_id, doc_id, DocStatus.COMPLETED)
                            logger.info(f"Document {doc_id} training completed")
                        else:
                            self.update_doc_status(
                                task_id,
                                doc_id,
                                DocStatus.FAILED,
                                process_result.get("error", "处理失败"),
                            )

                except Exception as e:
                    logger.error(f"Error processing document {doc_id}: {e}")
                    self.update_doc_status(task_id, doc_id, DocStatus.FAILED, str(e))

        # Process all documents concurrently (with semaphore limiting)
        await asyncio.gather(
            *[process_single_doc(doc_id) for doc_id in task.doc_ids],
            return_exceptions=True,
        )

        # Update overall task status
        task.status = TaskStatus.COMPLETED
        logger.info(f"Batch train task {task_id} completed: " f"{task.completed} succeeded, {task.failed} failed")

    def cleanup_old_tasks(self):
        """Remove tasks older than TTL"""
        now = datetime.now()
        expired_ids = [
            task_id for task_id, task in self._tasks.items() if (now - task.created_at).total_seconds() > self._task_ttl
        ]
        for task_id in expired_ids:
            del self._tasks[task_id]
            logger.debug(f"Cleaned up expired task {task_id}")


# Singleton instance
batch_train_manager = BatchTrainManager()
