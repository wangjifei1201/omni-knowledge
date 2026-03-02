const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("token");
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        window.location.href = "/login";
      }
      throw new Error("未授权，请重新登录");
    }

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: "请求失败" }));
      throw new Error(error.detail || `HTTP ${res.status}`);
    }

    if (res.status === 204) return {} as T;
    return res.json();
  }

  // 认证相关
  login(data: { username: string; password: string }) {
    return this.request<{
      access_token: string;
      token_type: string;
      user: any;
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  register(data: any) {
    return this.request<any>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getMe() {
    return this.request<any>("/auth/me");
  }

  updateMe(data: any) {
    return this.request<any>("/auth/me", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  changePassword(data: { old_password: string; new_password: string }) {
    return this.request<any>("/auth/me/password", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  getSystemConfig() {
    return this.request<{
      llm: { api_base: string; model_name: string };
      embedding: { api_base: string; model_name: string; dimension: number };
      reranker: { api_base: string; model_name: string };
      database: { type: string; host: string; port: number; name: string };
      vector_store: { type: string; index_path: string };
      storage: { type: string; path: string };
    }>("/auth/system-config");
  }

  // 文档管理
  uploadDocument(formData: FormData) {
    return this.request<any>("/documents", {
      method: "POST",
      body: formData,
    });
  }

  getDocuments(params: Record<string, string | number> = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== "" && v !== undefined) query.set(k, String(v));
    });
    return this.request<any>(`/documents?${query.toString()}`);
  }

  getDocument(id: string) {
    return this.request<any>(`/documents/${id}`);
  }

  updateDocument(id: string, data: any) {
    return this.request<any>(`/documents/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  deleteDocument(id: string) {
    return this.request<any>(`/documents/${id}`, { method: "DELETE" });
  }

  getDocumentDownloadUrl(id: string): string {
    const token = this.getToken();
    return `${this.baseUrl}/documents/${id}/download${token ? `?token=${token}` : ''}`;
  }

  getDocumentPreviewUrl(id: string): string {
    const token = this.getToken();
    return `${this.baseUrl}/documents/${id}/preview${token ? `?token=${token}` : ''}`;
  }

  async downloadDocument(id: string, filename: string) {
    const token = this.getToken();
    const res = await fetch(`${this.baseUrl}/documents/${id}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      throw new Error("下载失败");
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  reparseDocument(id: string) {
    return this.request<any>(`/documents/${id}/reparse`, { method: "POST" });
  }

  // Chunking strategy
  getChunkingStrategies() {
    return this.request<{ strategies: any[] }>("/documents/chunking-strategies");
  }

  updateChunkingConfig(id: string, config: { chunking_strategy: string; chunking_params: Record<string, any> }) {
    return this.request<any>(`/documents/${id}/chunking-config`, {
      method: "PUT",
      body: JSON.stringify(config),
    });
  }

  getDocumentChunks(id: string, page = 1, pageSize = 20) {
    return this.request<{
      items: any[];
      total: number;
      page: number;
      page_size: number;
    }>(`/documents/${id}/chunks?page=${page}&page_size=${pageSize}`);
  }

  retrainDocument(id: string, config?: { chunking_strategy: string; chunking_params: Record<string, any> }) {
    return this.request<any>(`/documents/${id}/retrain`, {
      method: "POST",
      body: config ? JSON.stringify(config) : JSON.stringify({}),
    });
  }

  // Multi-document upload: Extract metadata using LLM
  extractDocumentMetadata(formData: FormData) {
    return this.request<{
      results: Array<{
        file_index: number;
        filename: string;
        doc_name: string;
        department: string;
        category: string;
        security_level: string;
        tags: string[];
        description: string;
      }>;
    }>("/documents/extract-metadata", {
      method: "POST",
      body: formData,
    });
  }

  // Batch training: Start training for multiple documents
  batchTrainDocuments(docIds: string[]) {
    return this.request<{
      task_id: string;
      total: number;
      message: string;
    }>("/documents/batch-train", {
      method: "POST",
      body: JSON.stringify({ doc_ids: docIds }),
    });
  }

  // Batch training: Get task status
  getBatchTrainStatus(taskId: string) {
    return this.request<{
      task_id: string;
      status: "pending" | "running" | "completed";
      total: number;
      completed: number;
      failed: number;
      results: Array<{
        doc_id: string;
        doc_name: string;
        status: "pending" | "processing" | "completed" | "failed";
        error?: string;
      }>;
    }>(`/documents/batch-train/${taskId}/status`);
  }

  async previewDocument(id: string): Promise<string> {
    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${this.baseUrl}/documents/${id}/preview`, {
      headers,
    });
    
    if (!res.ok) {
      throw new Error("预览失败");
    }
    
    return res.text();
  }

  getDocumentStats() {
    return this.request<any>("/documents/stats/overview");
  }

  // 对话相关
  sendMessage(data: any) {
    return this.request<any>("/chat", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * 发送流式消息（SSE）
   * @param data 对话请求数据
   * @param callbacks.onToken 接收到 token 的回调
   * @param callbacks.onCitations 接收到引用的回调
   * @param callbacks.onDone 流式传输完成的回调
   * @param callbacks.onError 错误回调
   */
  async sendMessageStream(
    data: any,
    callbacks: {
      onStatus?: (status: string) => void;
      onToken?: (token: string) => void;
      onCitations?: (citations: any[]) => void;
      onDone?: (data: { conversation_id: string; response_time_ms?: number }) => void;
      onError?: (error: string) => void;
    }
  ): Promise<void> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${this.baseUrl}/chat/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "请求失败" }));
        callbacks.onError?.(error.detail || `HTTP ${response.status}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks.onError?.("无法获取响应流");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const event = JSON.parse(jsonStr);
              
              switch (event.type) {
                case "status":
                  callbacks.onStatus?.(event.content);
                  break;
                case "token":
                  callbacks.onToken?.(event.content);
                  break;
                case "citations":
                  callbacks.onCitations?.(event.citations);
                  break;
                case "done":
                  callbacks.onDone?.({
                    conversation_id: event.conversation_id,
                    response_time_ms: event.response_time_ms,
                  });
                  break;
                case "error":
                  callbacks.onError?.(event.content);
                  break;
              }
            } catch (e) {
              // 忽略不完整数据的 JSON 解析错误
            }
          }
        }
      }
    } catch (error: any) {
      callbacks.onError?.(error.message || "网络错误");
    }
  }

  getConversations(page = 1, pageSize = 50) {
    return this.request<any>(
      `/chat/conversations?page=${page}&page_size=${pageSize}`
    );
  }

  getConversationMessages(conversationId: string) {
    return this.request<any[]>(
      `/chat/conversations/${conversationId}/messages`
    );
  }

  renameConversation(conversationId: string, title: string) {
    return this.request<any>(`/chat/conversations/${conversationId}`, {
      method: "PUT",
      body: JSON.stringify({ title }),
    });
  }

  deleteConversation(conversationId: string) {
    return this.request<any>(`/chat/conversations/${conversationId}`, {
      method: "DELETE",
    });
  }

  submitFeedback(messageId: string, feedback: "like" | "dislike") {
    return this.request<any>(`/chat/messages/${messageId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ feedback }),
    });
  }

  // 用户管理（管理员）
  getUsers(params: Record<string, string | number> = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== "" && v !== undefined) query.set(k, String(v));
    });
    return this.request<any[]>(`/users?${query.toString()}`);
  }

  createUser(data: any) {
    return this.request<any>("/users", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  updateUser(id: string, data: any) {
    return this.request<any>(`/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  deleteUser(id: string) {
    return this.request<any>(`/users/${id}`, { method: "DELETE" });
  }

  getUserStats() {
    return this.request<any>("/users/stats");
  }

  // 统计相关
  getStatsOverview() {
    return this.request<any>("/statistics/overview");
  }

  getQueryTrends(days = 7) {
    return this.request<any>(`/statistics/query-trends?days=${days}`);
  }

  getTopQueries(limit = 10) {
    return this.request<any>(`/statistics/top-queries?limit=${limit}`);
  }

  getDocumentStatistics() {
    return this.request<any>("/statistics/document-stats");
  }
}

export const api = new ApiClient(API_BASE);
