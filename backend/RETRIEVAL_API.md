# RAG 检索 API 接口文档

## 概述

该接口提供匿名开放的 RAG（检索增强生成）文档片段检索功能。执行向量检索 + 重排序后返回 TOP-n 相关片段，**不进行大模型总结回答**。

## 基础信息

| 属性 | 值 |
|------|-----|
| **Base URL** | `http://{host}:{port}/api/v1` |
| **认证方式** | 无需认证（匿名开放） |
| **数据格式** | JSON |
| **字符编码** | UTF-8 |

---

## 接口详情

### POST /retrieval/search

执行 RAG 检索，返回重排序后的 TOP-n 片段。

#### 请求

**Content-Type**: `application/json`

**请求体参数**:

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `query` | string | 是 | - | 用户查询问题，1-2000字符 |
| `top_k` | integer | 否 | 10 | 返回的片段数量，范围 1-50 |
| `doc_scope` | array[string] | 否 | null | 限定检索的文档ID列表，为空时检索全部文档 |

**请求示例**:

```json
{
  "query": "员工请假流程是什么？",
  "top_k": 5,
  "doc_scope": null
}
```

#### 响应

**Content-Type**: `application/json`

**响应体结构**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `query` | string | 原始查询问题 |
| `total_chunks` | integer | 返回的片段总数 |
| `contents` | array[ChunkContent] | 召回的片段内容列表（按相关性降序） |
| `documents` | array[DocumentMeta] | 去重后的文档元数据列表 |

**ChunkContent 对象**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `chunk_id` | string | 片段唯一标识 |
| `content` | string | 片段文本内容 |
| `doc_id` | string | 所属文档ID |
| `doc_name` | string | 所属文档名称 |
| `chapter` | string | 章节 |
| `section` | string | 小节 |
| `page` | integer | 页码（0表示未知） |
| `score` | float | 相关性分数（0-1，越高越相关） |

**DocumentMeta 对象**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `doc_id` | string | 文档唯一标识 |
| `file_name` | string | 文件名称 |
| `file_path` | string | 文件存储路径 |
| `file_format` | string | 文件格式（pdf/docx/xlsx等） |
| `department` | string | 所属部门 |
| `category` | string | 文档分类 |

**响应示例**:

```json
{
  "query": "员工请假流程是什么？",
  "total_chunks": 5,
  "contents": [
    {
      "chunk_id": "chunk_001",
      "content": "员工请假需提前3个工作日提交申请，填写《请假申请表》，经部门主管审批后生效。病假需附医院证明...",
      "doc_id": "doc_abc123",
      "doc_name": "员工手册.pdf",
      "chapter": "第三章 考勤管理",
      "section": "3.2 请假制度",
      "page": 15,
      "score": 0.92
    },
    {
      "chunk_id": "chunk_002",
      "content": "请假审批流程：1.员工提交申请 2.直属主管审批 3.人事部备案 4.超过3天需部门经理审批...",
      "doc_id": "doc_abc123",
      "doc_name": "员工手册.pdf",
      "chapter": "第三章 考勤管理",
      "section": "3.2 请假制度",
      "page": 16,
      "score": 0.88
    }
  ],
  "documents": [
    {
      "doc_id": "doc_abc123",
      "file_name": "员工手册.pdf",
      "file_path": "/documents/hr/员工手册.pdf",
      "file_format": "pdf",
      "department": "人力资源部",
      "category": "制度文件"
    }
  ]
}
```

---

### GET /retrieval/search

GET 方式的检索接口，功能与 POST 相同，参数通过 URL Query 传递。

#### 请求

**URL 参数**:

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `query` | string | 是 | - | 用户查询问题，1-2000字符 |
| `top_k` | integer | 否 | 10 | 返回的片段数量，范围 1-50 |

**请求示例**:

```
GET /api/v1/retrieval/search?query=员工请假流程是什么&top_k=5
```

#### 响应

与 POST 方式相同。

---

## 错误处理

### HTTP 状态码

| 状态码 | 描述 |
|--------|------|
| 200 | 请求成功 |
| 422 | 请求参数验证失败 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 使用示例

### cURL

```bash
# POST 方式
curl -X POST "http://localhost:8000/api/v1/retrieval/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "员工请假流程是什么？",
    "top_k": 5
  }'

# GET 方式
curl "http://localhost:8000/api/v1/retrieval/search?query=员工请假流程&top_k=5"
```

### Python

```python
import requests

# POST 方式
response = requests.post(
    "http://localhost:8000/api/v1/retrieval/search",
    json={
        "query": "员工请假流程是什么？",
        "top_k": 5
    }
)
result = response.json()

print(f"找到 {result['total_chunks']} 个相关片段")
for chunk in result['contents']:
    print(f"[{chunk['doc_name']}] {chunk['content'][:100]}...")
```

### JavaScript

```javascript
// POST 方式
const response = await fetch('http://localhost:8000/api/v1/retrieval/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: '员工请假流程是什么？',
    top_k: 5
  })
});
const result = await response.json();

console.log(`找到 ${result.total_chunks} 个相关片段`);
result.contents.forEach(chunk => {
  console.log(`[${chunk.doc_name}] ${chunk.content.slice(0, 100)}...`);
});
```

---

## 技术说明

### 检索流程

1. **向量检索**: 将查询文本转换为向量，在 FAISS 索引中进行相似度搜索，返回 TOP-50 候选片段
2. **重排序**: 使用 Reranker 模型对候选片段进行精排，返回 TOP-k 最相关片段
3. **元数据聚合**: 对返回片段按文档去重，提取文档元数据

### 性能指标

- 平均响应时间: < 500ms（取决于向量库规模）
- 支持并发: 依赖服务器配置
- 最大返回片段数: 50

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2024-02-27 | 初始版本 |
