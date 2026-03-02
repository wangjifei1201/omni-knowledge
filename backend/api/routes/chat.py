import json
import time

from core.database import get_db
from core.security import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from loguru import logger
from models.chat import ChatMessage, Conversation, QueryLog
from models.user import User
from schemas.chat import (
    ChatRequest,
    ChatResponse,
    Citation,
    ConversationListResponse,
    ConversationRename,
    ConversationResponse,
    FeedbackRequest,
    MessageResponse,
)
from services.rag.pipeline import rag_pipeline
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/chat", tags=["智能问答"])


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a chat query using RAG pipeline.

    Flow:
    1. Get or create conversation
    2. Save user message
    3. Run RAG pipeline (intent classification -> retrieval -> rerank -> generation)
    4. Save assistant response with citations
    5. Return response
    """
    start_time = time.time()

    # Get or create conversation
    if req.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == req.conversation_id,
                Conversation.user_id == current_user.id,
                Conversation.is_deleted == False,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        conversation = Conversation(
            user_id=current_user.id,
            title=req.question[:50] + ("..." if len(req.question) > 50 else ""),
        )
        db.add(conversation)
        await db.flush()

    # Save user message
    user_msg = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=req.question,
        search_mode=req.search_mode,
    )
    db.add(user_msg)
    await db.flush()

    # Get conversation history for context
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at)
        .limit(10)
    )
    history_messages = history_result.scalars().all()
    history = [{"role": m.role, "content": m.content} for m in history_messages]

    # Run RAG pipeline
    try:
        rag_response = await rag_pipeline.process_query(
            query=req.question,
            search_mode=req.search_mode,
            doc_scope=req.doc_scope,
            detail_level=req.detail_level,
            history=history,
        )
    except Exception as e:
        logger.error(f"RAG pipeline error: {e}")
        rag_response = None

    if rag_response:
        answer = rag_response.answer
        citations = [
            Citation(
                doc_id=c.doc_id,
                doc_name=c.doc_name,
                chapter=c.chapter,
                section=c.section,
                page=c.page,
                original_text=c.original_text,
                confidence=c.confidence,
            )
            for c in rag_response.citations
        ]
        confidence = rag_response.confidence
        intent_type = rag_response.intent_type
        related_questions = rag_response.related_questions
    else:
        answer = "抱歉，处理您的问题时发生了错误，请稍后重试。"
        citations = []
        confidence = 0.0
        intent_type = "content"
        related_questions = []

    elapsed_ms = int((time.time() - start_time) * 1000)

    # Save assistant message
    assistant_msg = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        citations=json.dumps([c.model_dump() for c in citations], ensure_ascii=False),
        confidence=confidence,
    )
    db.add(assistant_msg)

    # Log query
    query_log = QueryLog(
        user_id=current_user.id,
        conversation_id=conversation.id,
        query=req.question,
        intent_type=intent_type,
        response_time_ms=elapsed_ms,
        result_count=len(citations),
    )
    db.add(query_log)
    await db.flush()

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
        answer=answer,
        citations=citations,
        confidence=confidence,
        intent_type=intent_type,
        response_time_ms=elapsed_ms,
        related_questions=related_questions,
    )


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    SSE streaming chat endpoint.

    Streams tokens as they are generated, then sends citations at the end.
    """
    # Get or create conversation
    if req.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == req.conversation_id,
                Conversation.user_id == current_user.id,
                Conversation.is_deleted == False,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        conversation = Conversation(
            user_id=current_user.id,
            title=req.question[:50] + ("..." if len(req.question) > 50 else ""),
        )
        db.add(conversation)
        await db.flush()

    # Save user message
    user_msg = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=req.question,
        search_mode=req.search_mode,
    )
    db.add(user_msg)
    await db.flush()

    # Get conversation history
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at)
        .limit(10)
    )
    history_messages = history_result.scalars().all()
    history = [{"role": m.role, "content": m.content} for m in history_messages]

    # Store conversation_id and db session for use in generator
    conv_id = conversation.id

    async def event_generator():
        full_answer = ""
        citations_data = []
        start_time = time.time()

        try:
            # Initialize RAG pipeline
            await rag_pipeline.initialize()

            # Send retrieval status
            yield f"data: {json.dumps({'type': 'status', 'content': '正在检索相关文档...'}, ensure_ascii=False)}\n\n"

            # Get streaming response and retrieval results
            stream, results, intent = await rag_pipeline.process_query_stream(
                query=req.question,
                search_mode=req.search_mode,
                doc_scope=req.doc_scope,
                detail_level=req.detail_level,
                history=history,
            )

            # Send generation status
            if intent.value == "metadata":
                yield f"data: {json.dumps({'type': 'status', 'content': '正在处理统计查询...'}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'status', 'content': f'找到 {len(results)} 个相关片段，正在生成回答...'}, ensure_ascii=False)}\n\n"

            # Stream answer tokens
            async for chunk in stream:
                full_answer += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"

            # Extract citations from results
            for i, result in enumerate(results[:5]):
                citations_data.append(
                    {
                        "doc_id": result.doc_id,
                        "doc_name": result.doc_name,
                        "chapter": result.chapter,
                        "section": result.section,
                        "page": result.page,
                        "original_text": result.content[:500],
                        "confidence": result.score,
                    }
                )

            # Send citations
            yield f"data: {json.dumps({'type': 'citations', 'citations': citations_data}, ensure_ascii=False)}\n\n"

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Send completion
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id, 'response_time_ms': elapsed_ms}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'处理请求时发生错误: {str(e)}'}, ensure_ascii=False)}\n\n"
            full_answer = f"抱歉，处理您的问题时发生错误: {str(e)}"

        # Save assistant message after streaming completes
        # Note: We need to create a new db session for this
        from core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as save_db:
            assistant_msg = ChatMessage(
                conversation_id=conv_id,
                role="assistant",
                content=full_answer,
                citations=json.dumps(citations_data, ensure_ascii=False),
                confidence=0.85 if citations_data else 0.0,
            )
            save_db.add(assistant_msg)
            await save_db.commit()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(Conversation).where(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False,
    )

    total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        base_query.order_by(desc(Conversation.is_pinned), desc(Conversation.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        msg_count_result = await db.execute(select(func.count()).where(ChatMessage.conversation_id == conv.id))
        msg_count = msg_count_result.scalar() or 0
        item = ConversationResponse.model_validate(conv)
        item.message_count = msg_count
        items.append(item)

    return ConversationListResponse(items=items, total=total)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    if not conv_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="会话不存在")

    result = await db.execute(
        select(ChatMessage).where(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    return [MessageResponse.model_validate(m) for m in messages]


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def rename_conversation(
    conversation_id: str,
    req: ConversationRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.is_deleted == False,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    conv.title = req.title
    await db.flush()
    await db.refresh(conv)
    return ConversationResponse.model_validate(conv)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    conv.is_deleted = True
    await db.flush()
    return {"message": "会话已删除"}


@router.post("/messages/{message_id}/feedback")
async def submit_feedback(
    message_id: str,
    req: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")

    msg.feedback = req.feedback
    await db.flush()
    return {"message": "反馈已记录"}
