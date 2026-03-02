# Omni-Knowledge

企业级智能知识库问答系统

> 基于 RAG (检索增强生成) 技术的企业知识库解决方案，支持文档智能解析、混合检索、引用溯源。

## 项目概述

Omni-Knowledge 是一个面向企业的智能知识库问答系统，旨在帮助企业高效管理和检索内部文档知识。通过 RAG 技术，用户可以上传各类文档（制度手册、操作规程、培训资料等），系统自动进行文档解析、分块、向量化，并提供智能问答功能。

### 核心特性

- 📄 **多格式文档支持**: PDF、Word、TXT、HTML、Markdown
- 🔍 **混合检索**: 向量检索 + BM25 关键词检索 + 重排序
- 📑 **智能分块**: 多种分块策略（字符、段落、标题）
- 🔎 **引用溯源**: 答案附带文档引用标注
- 👥 **多用户支持**: JWT 认证、用户管理
- 📊 **统计报表**: 文档统计、聊天统计

### 目标用户

- 企业内部员工（知识查询）
- 行政部门（文档管理）
- IT 运维（系统部署维护）

---

## 技术架构

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | Next.js 14 + TypeScript | App Router, Tailwind CSS |
| **UI 组件** | Radix UI + shadcn/ui | 现代化 UI 组件库 |
| **状态管理** | Zustand | 轻量级状态管理 |
| **后端框架** | FastAPI + Uvicorn | 异步 HTTP + SSE |
| **数据库** | MySQL / PostgreSQL + SQLAlchemy | 异步 ORM |
| **向量库** | FAISS (本地) | 高效向量检索 |
| **RAG** | LlamaIndex | 检索增强生成 |
| **LLM** | OpenAI 兼容接口 (Qwen 等) | 大语言模型 |
| **Embedding** | BGE 系列 | 向量化模型 |
| **缓存** | Redis | 会话缓存 |
| **认证** | JWT | Token 鉴权 |

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│                   http://localhost:3000                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                         │
│                    http://localhost:8000                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  Auth API   │  │  Chat API   │  │  Documents API          │ │
│  │  (JWT)      │  │  (SSE)      │  │  Upload/Train/Retrieval │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              RAG Pipeline                                    ││
│  │  Intent Classification → Query Rewriting → Hybrid Retrieval ││
│  │  → Rerank → LLM Generation                                  ││
│  └─────────────────────────────────────────────────────────────┘│
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   MySQL/      │    │    FAISS     │    │    Redis      │
│   PostgreSQL  │    │  (Vectors)   │    │   (Cache)     │
└───────────────┘    └───────────────┘    └───────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Documents    │    │   Chunks      │    │  Sessions     │
│  Metadata     │    │   Embeddings  │    │   Cache       │
└───────────────┘    └───────────────┘    └───────────────┘
```

---

## 项目结构

```
omni-knowledge/
├── backend/                 # FastAPI 后端服务 (端口 8000)
│   ├── app.py              # 入口文件
│   ├── config.py           # 配置管理
│   ├── api/routes/         # API 路由
│   │   ├── auth.py         # 认证接口
│   │   ├── chat.py         # 聊天接口
│   │   ├── documents.py    # 文档管理
│   │   ├── retrieval.py    # RAG 检索
│   │   └── statistics.py   # 统计接口
│   ├── core/               # 核心模块
│   │   ├── config.py       # 配置
│   │   ├── database.py    # 数据库
│   │   └── security.py    # 安全
│   ├── models/             # SQLAlchemy 模型
│   ├── schemas/            # Pydantic 模型
│   ├── services/           # 业务服务
│   │   ├── document/       # 文档处理
│   │   ├── llm/            # LLM 服务
│   │   ├── rag/            # RAG 核心
│   │   └── storage/        # 存储服务
│   └── data/               # 数据存储
│       ├── faiss_index/   # 向量索引
│       └── storage/        # 文件存储
│
├── frontend/               # Next.js 前端 (端口 3000)
│   ├── src/
│   │   ├── app/           # 页面路由
│   │   ├── components/    # React 组件
│   │   │   ├── ui/       # UI 基础组件
│   │   │   ├── chat/     # 聊天组件
│   │   │   └── layout/   # 布局组件
│   │   ├── lib/          # 工具库
│   │   └── store/        # Zustand 状态
│   └── package.json
│
├── start.sh               # 一键启动脚本
├── start-backend.sh       # 后端启动脚本
├── start-frontend.sh      # 前端启动脚本
│
├── omni-knowledge开发需求文档.pdf   # 开发需求文档
├── document-chunking-strategy.md   # 分块策略设计
├── multi-doc-upload-and-training.md # 批量上传设计
└── chat-citation-and-settings-optimization.md # 聊天优化设计
```

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- MySQL 8.0+ 或 PostgreSQL 14+
- Redis 6.0+

### 前置服务

需要先启动以下外部服务（本地或远程）:

| 服务 | 用途 | 默认地址 |
|------|------|----------|
| LLM API | 大语言模型 | http://localhost:8080/v1 |
| Embedding API | 向量化 | http://localhost:8081/v1 |
| Reranker API | 重排序 | http://localhost:8082/v1 |
| MySQL | 主数据库 | localhost:3306 |
| Redis | 缓存 | localhost:6379 |

### 启动步骤

#### 1. 克隆项目

```bash
cd omni-knowledge
```

#### 2. 配置后端

```bash
cd backend
cp .env.example .env
```

编辑 `.env`:

```env
# 数据库
DB_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=omni_knowledge
MYSQL_USER=root
MYSQL_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM
LLM_API_BASE=http://localhost:8080/v1
LLM_API_KEY=your-api-key
LLM_MODEL_NAME=qwen2.5-72b-instruct

# Embedding
EMBEDDING_API_BASE=http://localhost:8081/v1
EMBEDDING_MODEL_NAME=bge-large-zh-v1.5
EMBEDDING_DIMENSION=1024

# Reranker
RERANKER_API_BASE=http://localhost:8082/v1
RERANKER_MODEL_NAME=bge-reranker-large
```

#### 3. 安装依赖

**后端**:
```bash
cd backend
pip install -r requirements.txt
```

**前端**:
```bash
cd frontend
npm install
```

#### 4. 启动服务

```bash
# 一键启动 (推荐)
./start.sh

# 或分别启动
./start-backend.sh  # 后端: http://localhost:8000
./start-frontend.sh # 前端: http://localhost:3000
```

#### 5. 访问系统

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- 默认管理员: `admin` / `admin123`

---

## 功能说明

### 1. 文档管理

#### 支持格式
- PDF (.pdf)
- Word (.docx, .doc)
- 纯文本 (.txt)
- HTML (.html)
- Markdown (.md)

#### 文档上传流程
1. 选择文件（支持多选，最多 10 个）
2. 系统自动解析文档内容
3. LLM 提取元数据（标题、部门、类别、标签等）
4. 用户确认/编辑元数据
5. 选择分块策略
6. 执行向量化训练

#### 分块策略
| 策略 | 说明 | 适用场景 |
|------|------|----------|
| 段落 | 按自然段落分割 | 制度文档、说明书 |
| 字符 | 固定字符数 + 重叠 | 通用场景 |
| 标题 | 按章节标题分割 | 结构化文档 |

### 2. 智能问答

#### RAG 流程
1. **意图分类**: 判断是内容查询还是统计查询
2. **查询改写**: 提取关键词、展开同义词
3. **混合检索**: 向量 + BM25 召回相关片段
4. **重排序**: BGE-Reranker 优化排序
5. **答案生成**: LLM 生成带引用的答案

#### 引用标注
答案中以 `[引用N]` 格式标注信息来源:

> 根据规定，员工请假需要提前3天提交申请 [引用1]，超过3天需要部门经理审批 [引用2]。

### 3. 用户管理

- 用户注册/登录 (JWT Token)
- 角色管理 (管理员/普通用户)
- 修改密码
- 个人资料维护

### 4. 统计报表

- 文档总数、已训练数
- 聊天会话数、消息数
- 知识库使用情况

---

## API 接口概览

### 认证接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/login` | POST | 登录 |
| `/api/v1/auth/register` | POST | 注册 |
| `/api/v1/auth/me` | GET | 当前用户 |
| `/api/v1/auth/system-config` | GET | 系统配置 |

### 文档接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/documents` | GET | 文档列表 |
| `/api/v1/documents` | POST | 上传文档 |
| `/api/v1/documents/{id}` | DELETE | 删除文档 |
| `/api/v1/documents/{id}/train` | POST | 训练文档 |
| `/api/v1/documents/batch-train` | POST | 批量训练 |

### 聊天接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/chat/sessions` | GET/POST | 会话管理 |
| `/api/v1/chat/sessions/{id}/chat` | POST | 聊天 (SSE) |

### 检索接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/retrieval/search` | POST | RAG 检索 |
| `/api/v1/retrieval/chat` | POST | RAG 问答 |

详见: `backend/RETRIEVAL_API.md`

---

## 配置说明

### 后端配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `APP_PORT` | 8000 | 服务端口 |
| `DB_TYPE` | mysql | 数据库类型 |
| `LLM_MODEL_NAME` | qwen2.5-72b-instruct | LLM 模型 |
| `EMBEDDING_MODEL_NAME` | bge-large-zh-v1.5 | Embedding 模型 |
| `EMBEDDING_DIMENSION` | 1024 | 向量维度 |
| `FAISS_INDEX_PATH` | ./data/faiss_index | 向量索引路径 |

---

## 开发说明

### 添加新文档类型

编辑 `backend/services/document/parser.py`:

```python
@register_parser(".xxx")
def parse_xxx(file_path: str) -> str:
    # 解析逻辑
    return content
```

### 添加新分块策略

编辑 `backend/services/document/chunking_strategy.py`:

```python
class CustomChunkingStrategy(ChunkingStrategyBase):
    def chunk(self, text: str, params: dict) -> list[ChunkResult]:
        # 分块逻辑
        return chunks
```

### 前端组件开发

使用 shadcn/ui 添加组件:

```bash
cd frontend
npx shadcn-ui@latest add button
```

---

## 相关文档

- [后端 README](backend/README.md)
- [前端 README](frontend/README.md)
- [RAG 检索 API](backend/RETRIEVAL_API.md)
- [文档分块策略](document-chunking-strategy.md)
- [批量上传设计](multi-doc-upload-and-training.md)
- [聊天优化设计](chat-citation-and-settings-optimization.md)

---

## 许可证

MIT License

---

由 [wangjifei]() 提供技术支持
