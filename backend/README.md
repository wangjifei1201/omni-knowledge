# Omni-Knowledge Backend

企业级智能知识库问答系统后端服务。基于 FastAPI + SQLAlchemy + LlamaIndex 构建，支持 RAG (检索增强生成)。

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI + Uvicorn | 0.109.2 / 0.27.1 |
| 数据库 | SQLAlchemy 2.0 | 支持 MySQL / PostgreSQL |
| ORM | SQLAlchemy Async | 异步数据库操作 |
| RAG | LlamaIndex | 0.10.12 |
| 向量数据库 | FAISS (本地) | 1.7.4 |
| 文档解析 | Unstructured + python-docx + pdfplumber | - |
| 缓存/队列 | Redis + Celery | 5.0.1 / 5.3.6 |
| 认证 | JWT (python-jose + passlib) | - |

## 项目结构

```
backend/
├── app.py                      # FastAPI 入口, 端口 8000
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量示例
│
├── api/
│   └── routes/                  # API 路由
│       ├── auth.py             # 认证 (登录/注册/JWT)
│       ├── chat.py             # 聊天接口 (SSE 流式)
│       ├── documents.py         # 文档管理 CRUD
│       ├── retrieval.py         # RAG 检索接口
│       ├── statistics.py        # 统计接口
│       └── users.py             # 用户管理
│
├── core/                       # 核心模块
│   ├── config.py               # 配置管理 (Settings)
│   ├── database.py             # SQLAlchemy 初始化
│   └── security.py             # JWT / 密码哈希
│
├── models/                     # SQLAlchemy 模型
│   ├── chat.py                 # ChatHistory, ChatMessage
│   ├── document.py             # Document, DocumentChunk
│   └── user.py                 # User 模型
│
├── schemas/                    # Pydantic 请求/响应模型
│   ├── chat.py
│   ├── document.py
│   └── user.py
│
├── services/                   # 业务逻辑服务
│   ├── chat/                   # 聊天服务
│   │   └── ...
│   ├── document/               # 文档处理服务
│   │   ├── parser.py           # 文档解析 (PDF/Word/TXT)
│   │   ├── processor.py        # 文档处理主逻辑
│   │   ├── chunking_strategy.py # 分块策略
│   │   ├── metadata_extractor.py # 元数据提取
│   │   └── batch_train_manager.py # 批量训练管理
│   │
│   ├── llm/                    # LLM 服务
│   │   ├── llm.py              # 大语言模型调用
│   │   ├── embedding.py        # Embedding 服务
│   │   └── reranker.py         # 重排序服务
│   │
│   ├── rag/                    # RAG 核心
│   │   ├── pipeline.py         # RAG 流程 (意图分类 → 检索 → 重排 → 生成)
│   │   └── vector_store.py     # FAISS 向量存储
│   │
│   └── storage/                # 存储服务
│       └── local_storage.py    # 本地文件存储
│
├── schemas/                    # Pydantic 模型
├── utils/                      # 工具函数
├── tests/                      # 单元测试
└── data/                       # 数据存储目录
    ├── faiss_index/           # FAISS 索引
    └── storage/               # 上传文件存储
```

## 核心模块

### 1. API 路由 (`api/routes/`)

| 文件 | 路径前缀 | 功能 |
|------|----------|------|
| `auth.py` | `/api/v1/auth` | 登录、注册、JWT Token、用户信息 |
| `chat.py` | `/api/v1/chat` | 聊天消息、SSE 流式响应 |
| `documents.py` | `/api/v1/documents` | 文档上传、解析、分块、训练 |
| `retrieval.py` | `/api/v1/retrieval` | RAG 检索接口 |
| `statistics.py` | `/api/v1/statistics` | 统计接口 |
| `users.py` | `/api/v1/users` | 用户管理 |

### 2. RAG 流程 (`services/rag/pipeline.py`)

完整 RAG 流程包含 5 个阶段:

1. **意图分类 (Intent Classification)**
   - `CONTENT`: 内容查询 → RAG
   - `METADATA`: 统计查询 → Text-to-SQL
   - `HYBRID`: 混合查询

2. **查询改写 (Query Rewriting)**
   - 提取关键词和实体
   - 展开同义词
   - 结合对话历史

3. **混合检索 (Hybrid Retrieval)**
   - 向量检索 (FAISS)
   - BM25 关键词检索

4. **重排序 (Rerank)**
   - 使用 BGE-Reranker 模型

5. **LLM 生成**
   - 带引用标注的答案生成

### 3. 文档处理 (`services/document/`)

| 模块 | 功能 |
|------|------|
| `parser.py` | 解析 PDF/Word/TXT/HTML/Markdown |
| `chunking_strategy.py` | 多种分块策略 (Recursive, Token, Section) |
| `metadata_extractor.py` | 提取标题、章节、页码等元数据 |
| `processor.py` | 文档处理主逻辑 |
| `batch_train_manager.py` | 批量文档训练管理 |

### 4. LLM 服务 (`services/llm/`)

| 模块 | 功能 |
|------|------|
| `llm.py` | LLM API 调用 (OpenAI 兼容接口) |
| `embedding.py` | Embedding 生成 |
| `reranker.py` | 重排序模型调用 |

### 5. 存储服务 (`services/storage/`)

- `local_storage.py`: 本地文件系统存储 (替代 MinIO)

## 启动方式

### 环境配置

```bash
cd backend
cp .env.example .env
```

编辑 `.env`:

```env
# 应用配置
APP_NAME=omni-knowledge
APP_ENV=development
APP_DEBUG=true
SECRET_KEY=your-secret-key

# 数据库 (二选一)
DB_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=omni_knowledge
MYSQL_USER=root
MYSQL_PASSWORD=root

# 或 PostgreSQL
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=omni_knowledge

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM (OpenAI 兼容接口)
LLM_API_BASE=http://localhost:8080/v1
LLM_API_KEY=your-llm-api-key
LLM_MODEL_NAME=qwen2.5-72b-instruct

# Embedding
EMBEDDING_API_BASE=http://localhost:8081/v1
EMBEDDING_API_KEY=your-embedding-api-key
EMBEDDING_MODEL_NAME=bge-large-zh-v1.5

# Reranker
RERANKER_API_BASE=http://localhost:8082/v1
RERANKER_MODEL_NAME=bge-reranker-large

# 默认管理员
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
# 方式一: 直接运行
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# 方式二: 使用脚本
../start-backend.sh
```

### 初始化

启动时自动:
1. 创建数据库表
2. 初始化 FAISS 向量存储
3. 初始化本地文件存储
4. 创建默认管理员账户 (admin/admin123)

## API 接口

### 认证接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/login` | POST | 登录 (JWT) |
| `/api/v1/auth/register` | POST | 注册 |
| `/api/v1/auth/me` | GET | 获取当前用户 |
| `/api/v1/auth/me` | PUT | 更新用户信息 |
| `/api/v1/auth/me/password` | PUT | 修改密码 |
| `/api/v1/auth/system-config` | GET | 获取系统配置 |

### 聊天接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/v1/chat/sessions` | GET | 获取会话列表 |
| `/api/v1/chat/sessions` | POST | 创建会话 |
| `/api/v1/chat/sessions/{id}/messages` | GET | 获取会话消息 |
| `/api/v1/chat/sessions/{id}/chat` | POST | 聊天 (SSE 流式) |

### 文档接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/v1/documents` | GET | 文档列表 |
| `/api/v1/documents` | POST | 上传文档 |
| `/api/v1/documents/{id}` | GET | 文档详情 |
| `/api/v1/documents/{id}` | DELETE | 删除文档 |
| `/api/v1/documents/{id}/chunks` | GET | 文档分块列表 |
| `/api/v1/documents/{id}/train` | POST | 训练文档 |
| `/api/v1/documents/{id}/status` | GET | 训练状态 |
| `/api/v1/documents/batch-train` | POST | 批量训练 |

### 检索接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/v1/retrieval/search` | POST | RAG 检索 |
| `/api/v1/retrieval/chat` | POST | RAG 问答 |

### 统计接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/v1/statistics/overview` | GET | 统计概览 |
| `/api/v1/statistics/documents` | GET | 文档统计 |
| `/api/v1/statistics/chats` | GET | 聊天统计 |

## 配置说明

`core/config.py` 中的 `Settings` 类:

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `APP_PORT` | 8000 | 服务端口 |
| `DB_TYPE` | mysql | 数据库类型 (mysql/postgresql) |
| `LLM_MODEL_NAME` | qwen2.5-72b-instruct | LLM 模型名称 |
| `EMBEDDING_MODEL_NAME` | bge-large-zh-v1.5 | Embedding 模型 |
| `EMBEDDING_DIMENSION` | 1024 | Embedding 维度 |
| `RERANKER_MODEL_NAME` | bge-reranker-large | 重排序模型 |
| `FAISS_INDEX_PATH` | ./data/faiss_index | FAISS 索引路径 |
| `LOCAL_STORAGE_PATH` | ./data/storage | 本地存储路径 |

## 分块策略

支持多种文档分块策略 (`services/document/chunking_strategy.py`):

1. **RecursiveCharacterTextSplitter** - 按字符递归分割
2. **TokenTextSplitter** - 按 Token 数量分割
3. **SectionTextSplitter** - 按章节分割
4. **SentenceTextSplitter** - 按句子分割

详见: `document-chunking-strategy.md`

## 开发说明

### 添加新文档类型

在 `services/document/parser.py` 中添加解析器:

```python
@register_parser(".xxx")
def parse_xxx(file_path: str) -> str:
    # 解析逻辑
    return content
```

### 添加新 API 路由

1. 在 `api/routes/` 创建路由文件
2. 在 `app.py` 中注册:

```python
app.include_router(your_router, prefix="/api/v1")
```

### 修改 RAG 流程

编辑 `services/rag/pipeline.py` 中的 `RAGPipeline` 类:

- `classify_intent()`: 意图分类
- `rewrite_query()`: 查询改写
- `retrieve()`: 检索
- `rerank()`: 重排序
- `generate()`: 生成答案

---

由 [wangjifei]() 提供技术支持
