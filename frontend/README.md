# Omni-Knowledge Frontend

企业级智能知识库问答系统前端。基于 Next.js 14 + TypeScript + Tailwind CSS 构建。

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 框架 | Next.js | 14.2.35 |
| 语言 | TypeScript | 5.x |
| UI 框架 | React | 18 |
| 样式 | Tailwind CSS | 3.4.1 |
| UI 组件库 | Radix UI | 多组件 |
| 状态管理 | Zustand | 5.0.11 |
| Markdown | react-markdown | 10.1.0 |
| 代码编辑 | Monaco Editor | 4.7.0 |

## 项目结构

```
frontend/
├── package.json                # 依赖配置
├── tsconfig.json               # TypeScript 配置
├── tailwind.config.ts          # Tailwind 配置
├── next.config.mjs             # Next.js 配置
├── postcss.config.mjs          # PostCSS 配置
├── components.json             # shadcn/ui 组件配置
│
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/             # 认证页面
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (dashboard)/        # 仪表盘页面
│   │   │   ├── chat/
│   │   │   ├── documents/
│   │   │   └── settings/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   │
│   ├── components/             # React 组件
│   │   ├── ui/                 # shadcn/ui 基础组件
│   │   │   ├── button.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── switch.tsx
│   │   │   ├── tabs.tsx
│   │   │   └── ...
│   │   │
│   │   ├── chat/               # 聊天相关组件
│   │   │   ├── chat-container.tsx
│   │   │   ├── chat-input.tsx
│   │   │   ├── chat-message.tsx
│   │   │   └── ...
│   │   │
│   │   └── layout/             # 布局组件
│   │       ├── header.tsx
│   │       ├── sidebar.tsx
│   │       └── chat-history.tsx
│   │
│   ├── lib/                    # 工具库
│   │   ├── api.ts              # API 客户端 (Axios 风格)
│   │   ├── utils.ts            # 工具函数 (clsx, tailwind-merge)
│   │   └── ...
│   │
│   ├── store/                  # Zustand 状态管理
│   │   └── index.ts
│   │
│   └── types/                  # TypeScript 类型定义
│       └── ...
│
└── .next/                      # Next.js 构建输出
```

## 核心组件

### 1. UI 组件 (`components/ui/`)

基于 shadcn/ui 的基础组件:

| 组件 | 说明 |
|------|------|
| Button | 按钮 |
| Input | 输入框 |
| Dialog | 对话框 |
| DropdownMenu | 下拉菜单 |
| Select | 选择器 |
| Switch | 开关 |
| Tabs | 标签页 |
| Card | 卡片 |
| Avatar | 头像 |
| Progress | 进度条 |
| ScrollArea | 滚动区域 |
| Tooltip | 提示 |

### 2. 聊天组件 (`components/chat/`)

| 组件 | 功能 |
|------|------|
| `chat-container.tsx` | 聊天主容器 |
| `chat-input.tsx` | 消息输入框 |
| `chat-message.tsx` | 单条消息渲染 |
| `chat-toolbar.tsx` | 工具栏 |

### 3. 布局组件 (`components/layout/`)

| 组件 | 功能 |
|------|------|
| `header.tsx` | 顶部导航栏 |
| `sidebar.tsx` | 侧边栏导航 |
| `chat-history.tsx` | 聊天历史列表 |

## 状态管理 (`store/index.ts`)

使用 Zustand 管理全局状态:

```typescript
interface AppState {
  // 用户状态
  user: User | null;
  token: string | null;
  
  // 聊天状态
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  messages: ChatMessage[];
  
  // 文档状态
  documents: Document[];
  
  // UI 状态
  isLoading: boolean;
  
  // Actions
  setUser: (user: User) => void;
  login: (credentials) => void;
  logout: () => void;
  // ...
}
```

## API 客户端 (`lib/api.ts`)

封装后端 REST API:

### 认证方法

```typescript
// 登录
api.login({ username, password })

// 注册
api.register({ username, email, password })

// 获取当前用户
api.getMe()

// 修改密码
api.changePassword({ old_password, new_password })
```

### 文档方法

```typescript
// 获取文档列表
api.getDocuments()

// 上传文档
api.uploadDocument(file, onProgress)

// 获取文档详情
api.getDocument(id)

// 删除文档
api.deleteDocument(id)

// 训练文档
api.trainDocument(id)

// 批量训练
api.batchTrainDocuments(files)
```

### 聊天方法

```typescript
// 获取会话列表
api.getChatSessions()

// 创建会话
api.createChatSession({ title })

// 获取消息历史
api.getChatMessages(sessionId)

// 发送消息 (SSE 流式)
api.chat(sessionId, message, {
  onMessage: (data) => {},
  onCitations: (citations) => {},
  onDone: () => {},
  onError: (error) => {}
})
```

### 检索方法

```typescript
// RAG 检索
api.retrievalSearch({ query, topK })

// RAG 问答
api.retrievalChat({ query, sessionId })
```

## 页面结构

### 认证页面

- `/login` - 登录页
- `/register` - 注册页

### 仪表盘页面

- `/` - 首页/概览
- `/chat` - 聊天页面
- `/chat/[id]` - 特定会话
- `/documents` - 文档管理
- `/documents/[id]` - 文档详情
- `/settings` - 系统设置

## 启动方式

### 安装依赖

```bash
cd frontend
npm install
```

### 启动开发服务器

```bash
# 默认端口 3000
npm run dev

# 或使用脚本
../start-frontend.sh
```

访问: http://localhost:3000

### 环境变量

可选配置 (默认连接 localhost:8000):

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
```

### 构建生产版本

```bash
npm run build
npm start
```

## 样式说明

### Tailwind 配置

使用 Tailwind CSS + shadcn/ui 风格:

- 颜色系统: zinc, primary, secondary, destructive, muted
- 圆角: rounded-lg
- 暗色主题支持

### 工具函数 (`lib/utils.ts`)

```typescript
// 合并 className
cn(...inputs)

// 格式化日期
formatDate(date)

// 格式化文件大小
formatFileSize(bytes)
```

## 开发说明

### 添加新页面

1. 在 `app/` 下创建目录
2. 添加 `page.tsx` 或 `layout.tsx`
3. 使用布局组件包装

### 添加新组件

1. 使用 shadcn/ui CLI 添加:

```bash
npx shadcn-ui@latest add button
```

2. 或手动创建组件放入 `components/ui/`

### 添加 API 方法

在 `lib/api.ts` 中添加:

```typescript
// 新方法
async yourMethod(params) {
  return this.request('/your/endpoint', {
    method: 'POST',
    body: JSON.stringify(params)
  });
}
```

### 调试技巧

- 打开浏览器开发者工具 → Network 查看 API 请求
- 后端控制台查看日志
- Zustand DevTools (生产环境禁用)

---

由 [wangjifei]() 提供技术支持
