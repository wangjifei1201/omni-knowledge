# Chat Citation & Settings Optimization Plan

## Overview

实现4项产品功能优化：
1. 聊天回答中的 `[引用N]` 内联标记可点击
2. 修复个人信息修改不生效问题
3. 优化密码修改的 UI 反馈
4. 系统配置从后端动态读取（只读）

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/schemas/user.py` | Add `email` field to `UserUpdate` |
| `backend/api/routes/auth.py` | Add `GET /auth/system-config` endpoint |
| `frontend/src/store/index.ts` | Add `updateUser` method to AuthStore |
| `frontend/src/lib/api.ts` | Add `getSystemConfig()` method |
| `frontend/src/app/(main)/chat/page.tsx` | Inline citation click handling |
| `frontend/src/app/(main)/settings/page.tsx` | Profile update, password UI, system config |

---

## Feature 1: Inline Citation Markers Clickable

**Problem**: Answer text contains `[引用N]` markers rendered as plain text via ReactMarkdown.

**Solution**: Use custom ReactMarkdown `components` prop to render `[引用N]` as clickable buttons.

### Implementation

1. Create helper function `createCitationRenderer(citations, onCitationClick)`:
   - Returns custom `components` object for ReactMarkdown
   - Override text node rendering
   - Use regex `/\[引用(\d+)\]/g` to detect citation markers
   - Split text, replace markers with `<button>` elements
   - Button click calls `onCitationClick(citations[N-1])`

2. Apply to `MessageBubble` component (saved messages):
   ```tsx
   <ReactMarkdown
     remarkPlugins={[remarkGfm]}
     components={createCitationRenderer(message.citations, onCitationClick)}
   >
     {message.content}
   </ReactMarkdown>
   ```

3. Apply to streaming message section using `streamingCitations`

### Button Style
- `inline-flex text-primary underline hover:bg-primary/10 px-0.5 rounded cursor-pointer`
- Font size matches surrounding text

---

## Feature 2: Personal Info Modification Fix

**Root Cause**: 
- Backend `UserUpdate` schema missing `email` field
- Frontend doesn't update store after successful save

### Backend Changes (`backend/schemas/user.py`)

```python
class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None        # ADD THIS
    department: Optional[str] = None
    avatar: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None
```

### Frontend Changes

**Store (`frontend/src/store/index.ts`)**:
```typescript
interface AuthStore {
  // ... existing
  updateUser: (updates: Partial<User>) => void;
}

// In implementation:
updateUser: (updates) => {
  set((state) => {
    if (!state.user) return state;
    const newUser = { ...state.user, ...updates };
    localStorage.setItem("user", JSON.stringify(newUser));
    return { user: newUser };
  });
}
```

**Settings Page**:
- After successful `api.updateMe()`, call `useAuthStore.getState().updateUser(response)`
- Use message object `{ text: string, type: 'success' | 'error' }` for colored feedback

---

## Feature 3: Password Change UI Improvement

**Problem**: Success/error messages both use same color, hard to distinguish.

### Changes (`settings/page.tsx`)

1. Change message state structure:
   ```typescript
   const [profileMsg, setProfileMsg] = useState<{ text: string; type: 'success' | 'error' | '' }>({ text: '', type: '' });
   const [passwordMsg, setPasswordMsg] = useState<{ text: string; type: 'success' | 'error' | '' }>({ text: '', type: '' });
   ```

2. Apply conditional styling:
   ```tsx
   {msg.text && (
     <p className={cn("text-sm", msg.type === 'success' ? "text-green-600" : "text-red-600")}>
       {msg.text}
     </p>
   )}
   ```

3. Set appropriate type on success/error

---

## Feature 4: System Config from Backend

**Problem**: Settings page shows hardcoded fake values (PostgreSQL, Milvus, MinIO) instead of actual config (MySQL, FAISS, local storage).

### Backend Endpoint (`backend/api/routes/auth.py`)

```python
@router.get("/system-config")
async def get_system_config(current_user: User = Depends(get_current_admin)):
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
```

**IMPORTANT**: Do NOT return passwords, API keys, or SECRET_KEY.

### Frontend API (`api.ts`)

```typescript
getSystemConfig() {
  return this.request<SystemConfig>("/auth/system-config");
}
```

### Settings Page Rewrite

1. Add state: `systemConfig`, `configLoading`
2. Fetch on mount (admin only)
3. Replace all `<Input>` with disabled inputs or plain text
4. Remove all "保存配置" buttons
5. Display actual tech stack: MySQL, FAISS, Local Storage

---

## Implementation Order

1. **Feature 2** - Personal info fix (backend schema + frontend store)
2. **Feature 3** - Password UI (extends Feature 2 message handling)
3. **Feature 4** - System config (new endpoint + frontend rewrite)
4. **Feature 1** - Inline citations (most complex, independent)

---

## Verification

### Feature 1
- [ ] Ask a question, get answer with `[引用N]` markers
- [ ] Click inline `[引用1]` - right panel opens with correct citation
- [ ] Click inline `[引用2]` - panel updates to second citation
- [ ] Streaming message citations also clickable

### Feature 2
- [ ] Edit display_name, save - sidebar user name updates immediately
- [ ] Edit email, save - refresh page, email persists
- [ ] Success shows green message, error shows red

### Feature 3
- [ ] Enter wrong old password - red error message
- [ ] Enter correct password - green success message
- [ ] New password too short - red error message

### Feature 4
- [ ] Login as admin, go to Settings > System Config
- [ ] See actual config values (MySQL, FAISS, local storage)
- [ ] All fields are read-only (no edit, no save buttons)
- [ ] No passwords or API keys visible
- [ ] Non-admin user cannot see System Config tab
