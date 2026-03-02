# 多文档上传与批量训练功能实现方案

## 需求概述

1. **多文档上传**：支持一次选择最多10个文件，使用LLM自动提取文档属性
2. **批量训练**：在文档列表页面支持批量选择，对选中文档重新执行向量化
3. **默认值策略**：LLM提取失败时使用空值或通用值

---

## 实现方案

### 一、后端改动

#### 1.1 新增元数据提取服务

**新建文件**: `backend/services/document/metadata_extractor.py`

```python
# 核心功能：
# - extract_metadata_batch(file_previews: list) -> list[dict]
# - 调用LLM提取文档属性
# - 返回：doc_name, department, category, security_level, tags, description
```

**LLM Prompt 设计**:
```
你是文档元数据提取专家。请分析以下文档内容，为每个文档提取元数据。

要求返回JSON数组，每个元素包含：
- doc_name: 文档标题（简洁，不超过50字）
- department: 所属部门（如技术部、安全部、人事部等，无法判断则为空）
- category: 文档类别（如管理制度、操作规程、培训教材等，无法判断则为空）
- security_level: 密级（公开/内部/机密，默认"内部"）
- tags: 标签列表（3-5个关键词）
- description: 文档描述（100字以内）

文档列表：
[文档0] 文件名: {filename}
内容预览:
{preview_text}
---
...

请仅返回JSON数组，不要其他内容。
```

**默认值规则**：
- doc_name: 文件名去除扩展名
- department: ""
- category: ""
- security_level: "内部"
- tags: []
- description: ""

#### 1.2 新增API接口

**文件**: `backend/api/routes/documents.py`

**接口1: 批量元数据提取**
```
POST /documents/extract-metadata
Content-Type: multipart/form-data

Request: files: List[UploadFile] (最多10个)

Response:
{
  "results": [
    {
      "file_index": 0,
      "filename": "原始文件名.pdf",
      "doc_name": "提取的标题",
      "department": "安全部",
      "category": "应急预案",
      "security_level": "内部",
      "tags": ["安全", "应急"],
      "description": "文档描述..."
    }
  ]
}
```

**接口2: 批量训练**
```
POST /documents/batch-train
Content-Type: application/json

Request:
{
  "doc_ids": ["id1", "id2", ...]
}

Response:
{
  "task_id": "uuid",
  "total": 5,
  "message": "批量训练任务已创建"
}
```

**接口3: 批量训练进度查询**
```
GET /documents/batch-train/{task_id}/status

Response:
{
  "task_id": "uuid",
  "status": "running",  // pending/running/completed
  "total": 5,
  "completed": 3,
  "failed": 0,
  "results": [
    {"doc_id": "...", "doc_name": "...", "status": "completed"},
    {"doc_id": "...", "doc_name": "...", "status": "processing"},
    ...
  ]
}
```

#### 1.3 新增批量训练管理器

**新建文件**: `backend/services/document/batch_train_manager.py`

```python
# 核心功能：
# - 内存存储任务状态 (dict)
# - create_task(doc_ids) -> task_id
# - get_task_status(task_id) -> dict
# - 后台异步执行批量reparse
# - 使用Semaphore限制并发数(3-5)
```

---

### 二、前端改动

#### 2.1 改造上传组件

**文件**: `frontend/src/app/(main)/documents/page.tsx`

**UploadForm 组件改造**:

1. 文件选择改为多选 (`multiple` 属性)
2. 限制最多10个文件
3. 移除手动填写属性的表单字段
4. 新增文件列表展示区，显示：
   - 文件名、大小、类型图标
   - 状态：待上传 / 提取中 / 上传中 / 成功 / 失败
   - 移除按钮

**上传流程**:
```
用户选择文件(1-10个)
  ↓
点击"开始上传"
  ↓
调用 POST /documents/extract-metadata (所有文件)
  ↓
获取元数据后，逐个调用 POST /documents 上传
  ↓
实时更新每个文件的状态
```

**状态管理**:
```typescript
interface UploadFileItem {
  id: string;           // 临时ID
  file: File;
  status: 'pending' | 'extracting' | 'uploading' | 'success' | 'failed';
  metadata?: {
    doc_name: string;
    department: string;
    category: string;
    security_level: string;
    tags: string[];
    description: string;
  };
  error?: string;
}
```

#### 2.2 添加批量选择和训练功能

**文件**: `frontend/src/app/(main)/documents/page.tsx`

**改动点**:

1. 表格添加复选框列
2. 添加全选/取消全选功能
3. 选中文档后显示操作工具栏：
   - "已选择 X 个文档"
   - "批量训练" 按钮
   - "取消选择" 按钮
4. 点击"批量训练"后：
   - 弹出确认对话框
   - 确认后调用 API
   - 显示进度对话框，轮询状态直到完成

**新增状态**:
```typescript
const [selectedIds, setSelectedIds] = useState<string[]>([]);
const [batchTrainOpen, setBatchTrainOpen] = useState(false);
const [batchTrainTaskId, setBatchTrainTaskId] = useState<string | null>(null);
```

#### 2.3 前端API客户端

**文件**: `frontend/src/lib/api.ts`

**新增方法**:
```typescript
// 批量提取元数据
extractDocumentMetadata(formData: FormData) {
  return this.request<any>("/documents/extract-metadata", {
    method: "POST",
    body: formData,
  });
}

// 批量训练
batchTrainDocuments(docIds: string[]) {
  return this.request<any>("/documents/batch-train", {
    method: "POST",
    body: JSON.stringify({ doc_ids: docIds }),
  });
}

// 查询批量训练进度
getBatchTrainStatus(taskId: string) {
  return this.request<any>(`/documents/batch-train/${taskId}/status`);
}
```

---

### 三、关键文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/services/document/metadata_extractor.py` | 新建 | LLM元数据提取服务 |
| `backend/services/document/batch_train_manager.py` | 新建 | 批量训练任务管理 |
| `backend/api/routes/documents.py` | 修改 | 新增3个API接口 |
| `frontend/src/app/(main)/documents/page.tsx` | 修改 | 改造上传组件、添加批量选择 |
| `frontend/src/lib/api.ts` | 修改 | 新增3个API方法 |

---

### 四、验证方案

1. **多文档上传测试**:
   - 选择3-5个不同类型文档上传
   - 验证LLM自动提取属性是否正确
   - 验证上传进度和状态显示
   - 验证提取失败时的默认值

2. **批量训练测试**:
   - 选择多个已完成文档
   - 触发批量训练
   - 验证进度显示和状态更新
   - 验证训练完成后文档状态

3. **边界情况**:
   - 上传超过10个文件（应被拦截）
   - LLM服务不可用时的降级处理
   - 网络中断后的错误提示
