from datetime import datetime, timezone

from core.config import get_settings
from core.database import get_db
from core.security import (
    create_access_token,
    get_current_admin,
    get_current_user,
    get_password_hash,
    verify_password,
)
from fastapi import APIRouter, Depends, HTTPException, status
from models.user import User
from schemas.user import (
    LoginRequest,
    LoginResponse,
    PasswordChange,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")

    user.last_login = datetime.now(timezone.utc)
    await db.flush()

    token = create_access_token(data={"sub": user.id})
    return LoginResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=UserResponse)
async def register(req: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    existing = await db.execute(select(User).where((User.username == req.username) | (User.email == req.email)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=get_password_hash(req.password),
        display_name=req.display_name or req.username,
        department=req.department,
        role=req.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    req: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    update_data = req.model_dump(exclude_unset=True)
    # Regular users cannot change their own role
    update_data.pop("role", None)
    update_data.pop("is_active", None)

    # Check email uniqueness if email is being updated
    if "email" in update_data and update_data["email"] != current_user.email:
        existing = await db.execute(select(User).where(User.email == update_data["email"]))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该邮箱已被使用")

    for key, value in update_data.items():
        setattr(current_user, key, value)
    await db.flush()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.put("/me/password")
async def change_password(
    req: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    current_user.hashed_password = get_password_hash(req.new_password)
    await db.flush()
    return {"message": "密码修改成功"}


@router.get("/system-config")
async def get_system_config(current_user: User = Depends(get_current_admin)):
    """Get system configuration (admin only). Returns sanitized config without secrets."""
    settings = get_settings()
    return {
        "llm": {
            "api_base": settings.LLM_API_BASE,
            "model_name": settings.LLM_MODEL_NAME,
        },
        "embedding": {
            "api_base": settings.EMBEDDING_API_BASE,
            "model_name": settings.EMBEDDING_MODEL_NAME,
            "dimension": settings.EMBEDDING_DIMENSION,
        },
        "reranker": {
            "api_base": settings.RERANKER_API_BASE,
            "model_name": settings.RERANKER_MODEL_NAME,
        },
        "database": {
            "type": settings.DB_TYPE,
            "host": settings.MYSQL_HOST if settings.DB_TYPE == "mysql" else settings.POSTGRES_HOST,
            "port": settings.MYSQL_PORT if settings.DB_TYPE == "mysql" else settings.POSTGRES_PORT,
            "name": settings.MYSQL_DB if settings.DB_TYPE == "mysql" else settings.POSTGRES_DB,
        },
        "vector_store": {
            "type": "faiss",
            "index_path": settings.FAISS_INDEX_PATH,
        },
        "storage": {
            "type": "local",
            "path": settings.LOCAL_STORAGE_PATH,
        },
    }
