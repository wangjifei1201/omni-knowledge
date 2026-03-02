from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text

from core.database import get_db
from core.security import get_current_user, get_current_admin
from models.user import User
from models.document import Document
from models.chat import QueryLog, Conversation, ChatMessage

router = APIRouter(prefix="/statistics", tags=["使用统计"])


@router.get("/overview")
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard overview stats"""
    total_docs = await db.execute(
        select(func.count()).where(Document.is_deleted == False)
    )
    total_queries = await db.execute(select(func.count()).select_from(QueryLog))
    total_conversations = await db.execute(
        select(func.count()).where(Conversation.is_deleted == False)
    )
    total_users = await db.execute(select(func.count()).select_from(User))

    # Average response time
    avg_time = await db.execute(
        select(func.avg(QueryLog.response_time_ms))
    )

    # Today's queries
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today_queries = await db.execute(
        select(func.count()).where(QueryLog.created_at >= today_start)
    )

    # Feedback stats
    likes = await db.execute(
        select(func.count()).where(ChatMessage.feedback == "like")
    )
    dislikes = await db.execute(
        select(func.count()).where(ChatMessage.feedback == "dislike")
    )

    return {
        "total_documents": total_docs.scalar() or 0,
        "total_queries": total_queries.scalar() or 0,
        "total_conversations": total_conversations.scalar() or 0,
        "total_users": total_users.scalar() or 0,
        "avg_response_time_ms": round(avg_time.scalar() or 0, 1),
        "today_queries": today_queries.scalar() or 0,
        "feedback": {
            "likes": likes.scalar() or 0,
            "dislikes": dislikes.scalar() or 0,
        },
    }


@router.get("/query-trends")
async def get_query_trends(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query volume trend over past N days"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc("day", QueryLog.created_at).label("date"),
            func.count().label("count"),
        )
        .where(QueryLog.created_at >= start_date)
        .group_by("date")
        .order_by("date")
    )
    rows = result.all()
    return {
        "trends": [
            {"date": row.date.isoformat() if row.date else "", "count": row.count}
            for row in rows
        ]
    }


@router.get("/top-queries")
async def get_top_queries(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Most frequent queries"""
    result = await db.execute(
        select(QueryLog.query, func.count().label("count"))
        .group_by(QueryLog.query)
        .order_by(desc("count"))
        .limit(limit)
    )
    rows = result.all()
    return {"top_queries": [{"query": r.query, "count": r.count} for r in rows]}


@router.get("/document-stats")
async def get_document_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Document statistics by various dimensions"""
    by_type = await db.execute(
        select(Document.file_type, func.count(), func.sum(Document.file_size))
        .where(Document.is_deleted == False)
        .group_by(Document.file_type)
    )
    by_dept = await db.execute(
        select(Document.department, func.count())
        .where(Document.is_deleted == False)
        .group_by(Document.department)
    )
    by_category = await db.execute(
        select(Document.category, func.count())
        .where(Document.is_deleted == False)
        .group_by(Document.category)
    )

    return {
        "by_type": [
            {"type": r[0], "count": r[1], "total_size": r[2] or 0}
            for r in by_type.all()
        ],
        "by_department": [
            {"department": r[0], "count": r[1]} for r in by_dept.all()
        ],
        "by_category": [
            {"category": r[0], "count": r[1]} for r in by_category.all()
        ],
    }
