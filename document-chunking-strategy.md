# 文档分段策略功能实现方案

## 概述
为 omni-knowledge 企业 RAG 系统添加可配置的文档分段策略功能，支持文档级别配置、分段结果持久化到数据库、独立文档详情页展示和调整分段。

## 分段策略类型
- **character** (字符拆分): 按固定字符数 + 重叠切割，参数: `chunk_size`(默认500), `overlap`(默认50)
- **paragraph** (段落拆分): 按 `\n\n` 分自然段落，过长段落二次切割，参数: `max_paragraph_size`(默认1000), `overlap`(默认50)
- **heading** (标题拆分): 识别 Markdown `#`、数字编号 `1.2`、中文序号 `一、` 等标题，按章节切分，参数: `max_section_size`(默认2000), `overlap`(默认50)

---

## 后端变更

### 1. 数据库模型 - `backend/models/document.py`

Document 模型新增 2 个字段:
```python
chunking_strategy: Mapped[str] = mapped_column(String(20), default="paragraph")
chunking_params: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
```

DocumentChunk 模型已存在，无需修改。项目使用 `Base.metadata.create_all()` 自动建表。

### 2. 分段策略引擎 - `backend/services/document/chunking_strategy.py` (新建)

策略模式设计:
```
ChunkingStrategyBase (ABC)
├── CharacterChunkingStrategy
├── ParagraphChunkingStrategy
└── HeadingChunkingStrategy

ChunkingEngine
└── chunk_document(text, doc_id, doc_name, strategy, params) -> list[ChunkResult]
```

**ChunkResult** 数据类: content, chunk_index, token_count, metadata

**CharacterChunkingStrategy**: 按 chunk_size 固定切割 + overlap 重叠

**ParagraphChunkingStrategy**: 
- 按 `\n\n` 分段落
- 短段落合并(直到达到 max_paragraph_size)
- 过长段落按句子边界切割(中文句号/问号/叹号，英文 `.?!`)
- 段落间 overlap

**HeadingChunkingStrategy**:
- 正则识别标题: `^#{1,6}\s+`, `^(\d+\.)+\s+`, `^[一二三四五六七八九十]+[、．]`
- 按标题层级切分，每个 section 包含标题文本
- 超过 max_section_size 的 section 二次切割(按段落)
- section 间 overlap

**Token 计数**: 简化版 `len(text)` 作为 token_count (中文场景直接用字符数)

### 3. 修改文档处理器 - `backend/services/document/processor.py`

改造 `process_document` 方法签名，接收分段策略参数:
```python
async def process_document(self, doc_id, file_path, file_type, doc_name, 
                           chunking_strategy="paragraph", chunking_params=None) -> dict
```

改造 `_split_into_chunks`: 调用 `ChunkingEngine.chunk_document()`

改造 `_index_chunks`: 
1. 接收 db session 参数
2. 删除旧的 DocumentChunk 记录 (`DELETE WHERE doc_id = ?`)
3. 批量插入新 DocumentChunk 记录 (`db.add_all()`)
4. 生成向量 + 存储 FAISS (现有逻辑)

### 4. Schemas - `backend/schemas/document.py`

新增:
```python
class ChunkResponse(BaseModel):
    id: str
    chunk_index: int
    content: str
    token_count: int
    chunk_type: str
    created_at: datetime

class ChunkListResponse(BaseModel):
    items: list[ChunkResponse]
    total: int
    page: int
    page_size: int

class ChunkingConfigUpdate(BaseModel):
    chunking_strategy: str  # character / paragraph / heading
    chunking_params: dict = {}
```

扩展 DocumentResponse 增加 `chunking_strategy` 和 `chunking_params` 字段。

### 5. API 路由 - `backend/api/routes/documents.py`

**新增接口:**

`GET /documents/chunking-strategies` - 返回可用策略列表(静态数据，包含策略名、描述、参数定义和默认值)

`PUT /documents/{doc_id}/chunking-config` - 更新分段策略配置(仅保存，不触发重新训练)

`POST /documents/{doc_id}/retrain` - 保存策略配置 + 触发后台重新处理(删除旧向量 -> 重新解析分段 -> 重新向量化)

**修改接口:**

`GET /documents/{doc_id}/chunks` - 改为从 DocumentChunk 数据库表查询，支持分页(`page`, `page_size`)，返回 `ChunkListResponse`

`process_document_task` - 传入 chunking_strategy/params，处理完后写入 DocumentChunk 表

---

## 前端变更

### 6. 类型定义 - `frontend/src/types/index.ts`

新增:
```typescript
interface DocumentChunk {
  id: string; chunk_index: number; content: string; 
  token_count: number; chunk_type: string; created_at: string;
}
interface ChunkingStrategyDef {
  name: string; label: string; description: string;
  params: { key: string; label: string; type: string; default: number; min: number; max: number; }[];
}
```

扩展 Document 接口增加 `chunking_strategy` 和 `chunking_params`。

### 7. API 客户端 - `frontend/src/lib/api.ts`

新增方法:
- `getChunkingStrategies()` → GET /documents/chunking-strategies
- `updateChunkingConfig(id, config)` → PUT /documents/{id}/chunking-config
- `getDocumentChunks(id, page, pageSize)` → GET /documents/{id}/chunks
- `retrainDocument(id, config?)` → POST /documents/{id}/retrain

### 8. 文档详情页 - `frontend/src/app/(main)/documents/[id]/page.tsx` (新建)

页面布局:
```
[面包屑] 文档管理 > 文档名称
[基本信息卡片] 名称、类型、大小、部门、状态、标签等
[分段策略卡片]
  - 策略下拉选择 (Select): 字符拆分 / 段落拆分 / 标题拆分
  - 动态参数表单: 根据策略类型渲染对应参数 Input
  - [保存配置] 按钮 + [重新训练] 按钮
[分段结果卡片]
  - 统计: 共 N 个分段
  - 分段卡片列表: 每个显示 #序号 + token数 + 内容预览(可展开)
  - 分页组件
```

训练中状态: 轮询 `GET /documents/{id}` 检查 status，completed 后刷新分段列表。

### 9. 文档列表页 - `frontend/src/app/(main)/documents/page.tsx`

修改: 文档名称点击跳转到 `/documents/[id]` 详情页(使用 `useRouter` 或 `Link`)。保留现有的预览弹窗功能作为快捷操作。

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/models/document.py` | 修改 | Document 新增 chunking_strategy, chunking_params |
| `backend/services/document/chunking_strategy.py` | 新建 | 分段策略引擎(3种策略 + 引擎) |
| `backend/services/document/processor.py` | 修改 | 集成分段引擎，持久化 chunk 到 DB |
| `backend/schemas/document.py` | 修改 | 新增 ChunkResponse 等 schema |
| `backend/api/routes/documents.py` | 修改 | 新增/修改 API 路由 |
| `frontend/src/types/index.ts` | 修改 | 新增 DocumentChunk 等类型 |
| `frontend/src/lib/api.ts` | 修改 | 新增 API 方法 |
| `frontend/src/app/(main)/documents/[id]/page.tsx` | 新建 | 文档详情页 |
| `frontend/src/app/(main)/documents/page.tsx` | 修改 | 跳转详情页 |

---

## 验证步骤

1. 重启后端，确认数据库表自动更新(新增列)
2. `GET /documents/chunking-strategies` 返回 3 种策略定义
3. 上传文档，确认默认使用 paragraph 策略分段，chunk 写入 DB
4. `GET /documents/{id}/chunks` 返回分段列表(从数据库)
5. 前端访问 `/documents/{id}` 详情页，查看分段结果
6. 修改策略为 character/heading，点击重新训练
7. 训练完成后分段列表刷新，显示新的分段结果
8. `npm run build` 前端构建通过
9. 后端模块导入无报错
