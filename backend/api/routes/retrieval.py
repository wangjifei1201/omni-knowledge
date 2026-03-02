"""
Anonymous RAG Retrieval API
Provides document chunk retrieval without LLM summarization.
"""

from typing import Optional

from core.database import AsyncSessionLocal
from fastapi import APIRouter, Query
from loguru import logger
from models.document import Document
from pydantic import BaseModel, Field
from services.rag.pipeline import rag_pipeline
from sqlalchemy import select

router = APIRouter(prefix="/retrieval", tags=["检索"])


class ChunkContent(BaseModel):
    """Single chunk content with metadata"""

    chunk_id: str = Field(..., description="片段唯一标识")
    content: str = Field(..., description="片段文本内容")
    doc_id: str = Field(..., description="所属文档ID")
    doc_name: str = Field(..., description="所属文档名称")
    chapter: str = Field("", description="章节")
    section: str = Field("", description="小节")
    page: int = Field(0, description="页码")
    score: float = Field(0.0, description="相关性分数")


class DocumentMeta(BaseModel):
    """Document metadata (deduplicated)"""

    doc_id: str = Field(..., description="文档唯一标识")
    file_name: str = Field(..., description="文件名称")
    file_path: str = Field("", description="文件存储路径")
    file_format: str = Field("", description="文件格式 (pdf/docx/xlsx等)")
    department: str = Field("", description="所属部门")
    category: str = Field("", description="文档分类")


class RetrievalRequest(BaseModel):
    """Retrieval request body"""

    query: str = Field(..., min_length=1, max_length=2000, description="用户查询问题")
    top_k: int = Field(10, ge=1, le=50, description="返回的片段数量")
    doc_scope: Optional[list[str]] = Field(None, description="限定检索的文档ID列表")


class RetrievalResponse(BaseModel):
    """Retrieval response"""

    query: str = Field(..., description="原始查询")
    total_chunks: int = Field(..., description="返回的片段总数")
    contents: list[ChunkContent] = Field(..., description="召回的片段内容列表")
    documents: list[DocumentMeta] = Field(..., description="去重后的文档元数据列表")


@router.post("/search", response_model=RetrievalResponse, summary="RAG检索接口")
async def search_chunks(request: RetrievalRequest):
    """
    执行RAG检索，返回重排序后的TOP-n片段。

    该接口匿名开放，无需认证。执行向量检索 + 重排序，但不进行大模型总结。

    - **query**: 用户查询问题
    - **top_k**: 返回的片段数量，默认10，最大50
    - **doc_scope**: 可选，限定检索的文档ID列表

    返回:
    - **contents**: 召回的片段内容列表，按相关性分数降序排列
    - **documents**: 去重后的文档元数据列表
    """
    logger.info(f"Retrieval search: query='{request.query[:50]}...', top_k={request.top_k}")

    # Initialize pipeline if needed
    await rag_pipeline.initialize()

    # Execute hybrid retrieval (vector search + rerank)
    results = await rag_pipeline.hybrid_retrieve(
        query=request.query,
        top_k=request.top_k,
        doc_scope=request.doc_scope,
    )

    # Build chunk contents
    contents = [
        ChunkContent(
            chunk_id=r.chunk_id,
            content=r.content,
            doc_id=r.doc_id,
            doc_name=r.doc_name,
            chapter=r.chapter,
            section=r.section,
            page=r.page,
            score=r.score,
        )
        for r in results
    ]

    # Collect unique doc_ids from results
    seen_docs = set()
    unique_doc_ids = []
    for r in results:
        if r.doc_id not in seen_docs:
            seen_docs.add(r.doc_id)
            unique_doc_ids.append(r.doc_id)

    # Query database for document metadata
    doc_meta_map: dict[str, Document] = {}
    if unique_doc_ids:
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(Document).where(Document.id.in_(unique_doc_ids))
                result = await db.execute(stmt)
                for doc in result.scalars().all():
                    doc_meta_map[doc.id] = doc
        except Exception as e:
            logger.warning(f"Failed to query document metadata: {e}")

    # Build deduplicated document metadata
    documents = []
    for doc_id in unique_doc_ids:
        db_doc = doc_meta_map.get(doc_id)

        if db_doc:
            file_name = db_doc.doc_name
            file_format = db_doc.file_type or ""
            file_path = db_doc.file_path or ""
            department = db_doc.department or ""
            category = db_doc.category or ""
        else:
            # Fallback: use info from retrieval results
            r = next(r for r in results if r.doc_id == doc_id)
            file_name = r.doc_name
            file_format = ""
            if "." in file_name:
                file_format = file_name.rsplit(".", 1)[-1].lower()
            file_path = r.position.get("file_path", "") if r.position else ""
            department = r.position.get("department", "") if r.position else ""
            category = r.position.get("category", "") if r.position else ""

        documents.append(
            DocumentMeta(
                doc_id=doc_id,
                file_name=file_name,
                file_path=file_path,
                file_format=file_format,
                department=department,
                category=category,
            )
        )

    logger.info(f"Retrieval completed: {len(contents)} chunks from {len(documents)} documents")

    return RetrievalResponse(
        query=request.query,
        total_chunks=len(contents),
        contents=[],
        # contents=contents,
        documents=documents,
    )


@router.get("/search", response_model=RetrievalResponse, summary="RAG检索接口(GET)")
async def search_chunks_get(
    query: str = Query(..., min_length=1, max_length=2000, description="用户查询问题"),
    top_k: int = Query(10, ge=1, le=50, description="返回的片段数量"),
):
    """
    执行RAG检索，返回重排序后的TOP-n片段（GET方式）。

    该接口匿名开放，无需认证。功能与POST方式相同，但使用URL参数传递查询。
    """
    request = RetrievalRequest(query=query, top_k=top_k)
    return await search_chunks(request)
