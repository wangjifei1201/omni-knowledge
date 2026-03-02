"""
RAG Pipeline Service
Handles the core RAG workflow:
1. Intent classification (content / metadata / hybrid)
2. Query rewriting & entity recognition
3. Hybrid retrieval (Vector + BM25)
4. Rerank
5. LLM generation with citations
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator, Optional

from core.config import get_settings
from loguru import logger
from services.llm.embedding import embedding_service
from services.llm.llm import llm_service
from services.llm.reranker import reranker_service
from services.rag.vector_store import VectorSearchResult, faiss_vector_store

settings = get_settings()


class IntentType(str, Enum):
    CONTENT = "content"  # Content-based query -> RAG
    METADATA = "metadata"  # Statistics query -> Text-to-SQL
    HYBRID = "hybrid"  # Both


@dataclass
class RetrievalResult:
    chunk_id: str = ""
    doc_id: str = ""
    doc_name: str = ""
    chapter: str = ""
    section: str = ""
    page: int = 0
    content: str = ""
    score: float = 0.0
    position: dict = field(default_factory=dict)


@dataclass
class Citation:
    doc_id: str = ""
    doc_name: str = ""
    chapter: str = ""
    section: str = ""
    page: int = 0
    original_text: str = ""
    confidence: float = 0.0


@dataclass
class RAGResponse:
    answer: str = ""
    citations: list = field(default_factory=list)
    confidence: float = 0.0
    intent_type: str = "content"
    related_questions: list = field(default_factory=list)


# RAG System Prompt with citation requirements
RAG_SYSTEM_PROMPT = """你是一个专业的企业知识库问答助手。请根据提供的文档内容回答用户问题。

## 回答要求
1. 只基于提供的文档内容回答，不要编造信息
2. 使用 [引用N] 格式标注信息来源，N为文档编号（从1开始）
3. 如果文档中没有相关信息，请明确告知
4. 回答要准确、专业、条理清晰
5. 对于涉及流程、步骤的问题，请分点说明

## 引用格式示例
"根据规定，员工请假需要提前3天提交申请 [引用1]，超过3天需要部门经理审批 [引用2]。"

## 注意事项
- 多个来源证实同一信息时，可以合并引用如 [引用1][引用2]
- 不确定的内容不要回答
- 保持客观中立的语气
"""

QUERY_REWRITE_PROMPT = """请帮我改写以下查询，使其更适合进行文档检索。要求：
1. 提取核心关键词和实体
2. 展开可能的同义词
3. 去除口语化表达
4. 保持问题本意

原始查询: {query}

对话历史:
{history}

只输出改写后的查询，不要解释。"""

INTENT_CLASSIFICATION_PROMPT = """请判断以下查询的意图类型：

查询: {query}

意图类型说明：
- content: 内容查询，需要检索文档内容来回答（如：什么是XX、如何做XX、XX的规定是什么）
- metadata: 元数据/统计查询，需要查询数据库（如：有多少文档、哪些部门的文档、文档列表）
- hybrid: 混合查询，既需要统计又需要内容（如：技术部门有哪些制度，具体内容是什么）

只输出意图类型（content/metadata/hybrid），不要解释。"""


class RAGPipeline:
    """Core RAG pipeline with real LLM integration"""

    def __init__(self):
        self._initialized = False

    async def initialize(self):
        """Initialize components"""
        if self._initialized:
            return

        # Initialize FAISS vector store
        await faiss_vector_store.initialize()
        self._initialized = True

    async def classify_intent(self, query: str) -> IntentType:
        """Classify user query intent using LLM"""
        logger.info(f"Classifying intent for query: {query}")
        
        # Quick keyword-based classification first
        metadata_keywords = [
            "多少",
            "几份",
            "数量",
            "统计",
            "列表",
            "有哪些文档",
            "清单",
            "目录",
            "汇总",
            "总计",
            "平均",
            "所有文档",
        ]
        for kw in metadata_keywords:
            if kw in query:
                logger.info(f"Matched metadata keyword: '{kw}'")
                # Check if also needs content
                content_keywords = ["具体", "内容", "说明", "介绍", "详细"]
                for ck in content_keywords:
                    if ck in query:
                        logger.info(f"Also matched content keyword: '{ck}', returning HYBRID")
                        return IntentType.HYBRID
                logger.info(f"Returning METADATA intent")
                return IntentType.METADATA

        # For more complex cases, use LLM classification
        try:
            prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
            result = await llm_service.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50,
            )
            result = result.strip().lower()
            if "metadata" in result:
                return IntentType.METADATA
            elif "hybrid" in result:
                return IntentType.HYBRID
        except Exception as e:
            logger.warning(f"Intent classification failed, defaulting to content: {e}")

        return IntentType.CONTENT

    async def rewrite_query(self, query: str, history: list[dict] = None) -> str:
        """Rewrite query for better retrieval using LLM"""
        if not history:
            # No history, return original query
            return query

        try:
            # Format history
            history_str = "\n".join(
                [f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:200]}" for m in history[-4:]]
            )

            prompt = QUERY_REWRITE_PROMPT.format(query=query, history=history_str)
            result = await llm_service.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
            )
            rewritten = result.strip()
            if rewritten and len(rewritten) > 5:
                logger.info(f"Query rewritten: '{query}' -> '{rewritten}'")
                return rewritten
        except Exception as e:
            logger.warning(f"Query rewrite failed: {e}")

        return query

    async def vector_search(
        self,
        query: str,
        top_k: int = 50,
        filters: dict = None,
    ) -> list[RetrievalResult]:
        """Vector similarity search using FAISS"""
        # Get query embedding
        query_embedding = await embedding_service.embed_text(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []

        # Search in FAISS
        results = await faiss_vector_store.search(
            query_vector=query_embedding,
            top_k=top_k,
            filters=filters,
        )

        return [
            RetrievalResult(
                chunk_id=r.chunk_id,
                doc_id=r.doc_id,
                doc_name=r.doc_name,
                chapter=r.chapter,
                section=r.section,
                page=r.page,
                content=r.content,
                score=r.score,
                position=r.position,
            )
            for r in results
        ]

    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Rerank results using reranker model"""
        if not results:
            return []

        # Extract document texts for reranking
        documents = [r.content for r in results]

        # Call reranker service
        reranked = await reranker_service.rerank(
            query=query,
            documents=documents,
            top_n=top_k,
        )

        # Reorder results based on reranking
        reranked_results = []
        for item in reranked:
            idx = item.get("index", 0)
            if idx < len(results):
                result = results[idx]
                result.score = item.get("relevance_score", result.score)
                reranked_results.append(result)

        return reranked_results[:top_k]

    async def hybrid_retrieve(
        self,
        query: str,
        top_k: int = 10,
        doc_scope: list[str] = None,
    ) -> list[RetrievalResult]:
        """Hybrid retrieval: Vector search + Rerank"""
        filters = {}
        if doc_scope:
            filters["doc_ids"] = doc_scope

        # Vector search - get more candidates for reranking
        vector_results = await self.vector_search(query, top_k=50, filters=filters)

        if not vector_results:
            logger.warning("No vector search results")
            return []

        # Rerank results
        reranked_results = await self.rerank(query, vector_results, top_k=top_k)

        return reranked_results

    async def generate_answer(
        self,
        query: str,
        context: list[RetrievalResult],
        detail_level: str = "normal",
    ) -> RAGResponse:
        """Generate answer using LLM with citation requirements"""
        if not context:
            return RAGResponse(
                answer="抱歉，未找到与您问题相关的文档内容。请尝试使用不同的关键词，或确认相关文档已上传到知识库。",
                citations=[],
                confidence=0.0,
                intent_type="content",
            )

        # Build context with document markers
        context_parts = []
        for i, result in enumerate(context, 1):
            doc_info = f"[文档{i}: {result.doc_name}]"
            context_parts.append(f"{doc_info}\n{result.content}")

        context_text = "\n\n---\n\n".join(context_parts)

        # Build messages
        messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"## 参考文档\n\n{context_text}\n\n## 用户问题\n\n{query}",
            },
        ]

        # Call LLM
        try:
            answer = await llm_service.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return RAGResponse(
                answer=f"抱歉，生成回答时发生错误: {str(e)}",
                citations=[],
                confidence=0.0,
                intent_type="content",
            )

        # Extract citations from answer
        citations = self._extract_citations(answer, context)

        # Calculate confidence based on citation count and relevance scores
        avg_score = sum(r.score for r in context[:5]) / min(len(context), 5) if context else 0
        confidence = min(0.95, max(0.5, avg_score))

        return RAGResponse(
            answer=answer,
            citations=citations,
            confidence=confidence,
            intent_type="content",
            related_questions=self._generate_related_questions(query, context),
        )

    async def generate_answer_stream(
        self,
        query: str,
        context: list[RetrievalResult],
        detail_level: str = "normal",
    ) -> AsyncGenerator[str, None]:
        """Generate streaming answer using LLM"""
        if not context:
            yield "抱歉，未找到与您问题相关的文档内容。请尝试使用不同的关键词，或确认相关文档已上传到知识库。"
            return

        # Build context with document markers
        context_parts = []
        for i, result in enumerate(context, 1):
            doc_info = f"[文档{i}: {result.doc_name}]"
            context_parts.append(f"{doc_info}\n{result.content}")

        context_text = "\n\n---\n\n".join(context_parts)

        # Build messages
        messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"## 参考文档\n\n{context_text}\n\n## 用户问题\n\n{query}",
            },
        ]

        # Stream from LLM
        try:
            async for chunk in llm_service.chat_stream(
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            ):
                yield chunk
        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            yield f"\n\n[错误: {str(e)}]"

    def _extract_citations(
        self,
        answer: str,
        context: list[RetrievalResult],
    ) -> list[Citation]:
        """Extract citation information from answer"""
        citations = []
        seen_docs = set()

        # Find all citation markers like [引用1], [引用2] etc.
        citation_pattern = r"\[引用(\d+)\]"
        matches = re.findall(citation_pattern, answer)

        for match in matches:
            idx = int(match) - 1  # Convert to 0-based index
            if 0 <= idx < len(context) and idx not in seen_docs:
                result = context[idx]
                citations.append(
                    Citation(
                        doc_id=result.doc_id,
                        doc_name=result.doc_name,
                        chapter=result.chapter,
                        section=result.section,
                        page=result.page,
                        original_text=result.content[:500],  # Limit text length
                        confidence=result.score,
                    )
                )
                seen_docs.add(idx)

        # If no explicit citations found, include top results as references
        if not citations and context:
            for i, result in enumerate(context[:3]):
                citations.append(
                    Citation(
                        doc_id=result.doc_id,
                        doc_name=result.doc_name,
                        chapter=result.chapter,
                        section=result.section,
                        page=result.page,
                        original_text=result.content[:500],
                        confidence=result.score,
                    )
                )

        return citations

    def _generate_related_questions(
        self,
        query: str,
        context: list[RetrievalResult],
    ) -> list[str]:
        """Generate related questions based on context"""
        # Simple rule-based related questions
        related = []

        # Extract document names from context
        doc_names = list(set(r.doc_name for r in context[:5]))

        if doc_names:
            related.append(f"关于《{doc_names[0]}》还有哪些重要内容？")
            if len(doc_names) > 1:
                related.append(f"《{doc_names[0]}》和《{doc_names[1]}》有什么关联？")

        # Add generic related questions
        if "流程" in query or "步骤" in query:
            related.append("这个流程有哪些注意事项？")
        if "规定" in query or "制度" in query:
            related.append("违反规定会有什么后果？")

        return related[:3]

    async def process_query(
        self,
        query: str,
        search_mode: str = "hybrid",
        doc_scope: list[str] = None,
        detail_level: str = "normal",
        history: list[dict] = None,
    ) -> RAGResponse:
        """Full RAG pipeline execution"""
        await self.initialize()

        logger.info(f"Processing query: {query}")

        # 1. Intent classification
        intent = await self.classify_intent(query)
        logger.info(f"Intent classified: {intent}")

        # 2. Query rewriting (if there's history)
        rewritten_query = await self.rewrite_query(query, history)

        # 3. Route and retrieve
        if intent == IntentType.METADATA:
            # For metadata queries, return a hint to use database
            return RAGResponse(
                answer="您的问题涉及文档统计信息，请查看文档管理页面获取详细统计数据。",
                intent_type="metadata",
                confidence=0.85,
            )

        # Content or hybrid query
        results = await self.hybrid_retrieve(rewritten_query, doc_scope=doc_scope)
        logger.info(f"Retrieved {len(results)} results")

        # Generate answer
        response = await self.generate_answer(rewritten_query, results, detail_level)
        response.intent_type = intent.value

        return response

    async def process_query_stream(
        self,
        query: str,
        search_mode: str = "hybrid",
        doc_scope: list[str] = None,
        detail_level: str = "normal",
        history: list[dict] = None,
    ) -> tuple[AsyncGenerator[str, None], list[RetrievalResult], IntentType]:
        """Streaming RAG pipeline execution
        
        Returns:
            tuple: (stream generator, retrieval results, intent type)
        """
        await self.initialize()

        logger.info(f"Processing streaming query: {query}")

        # 1. Intent classification (quick)
        intent = await self.classify_intent(query)
        logger.info(f"Stream intent classified: {intent}")

        # 2. Handle METADATA intent - no retrieval needed
        if intent == IntentType.METADATA:
            async def metadata_stream():
                yield "您的问题涉及文档统计信息，请查看文档管理页面获取详细统计数据。"
            return metadata_stream(), [], intent

        # 3. Query rewriting
        rewritten_query = await self.rewrite_query(query, history)

        # 4. Retrieve
        results = await self.hybrid_retrieve(rewritten_query, doc_scope=doc_scope)
        logger.info(f"Retrieved {len(results)} results for streaming")

        # 5. Return stream generator and results for citation extraction later
        stream = self.generate_answer_stream(rewritten_query, results, detail_level)
        return stream, results, intent


# Singleton
rag_pipeline = RAGPipeline()
