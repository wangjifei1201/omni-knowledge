export interface User {
  id: string;
  username: string;
  email: string;
  display_name: string;
  department: string;
  role: "admin" | "user";
  avatar: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Document {
  id: string;
  doc_name: string;
  file_type: string;
  file_size: number;
  department: string;
  category: string;
  security_level: string;
  version: string;
  description: string;
  page_count: number;
  chunk_count: number;
  status: "pending" | "processing" | "completed" | "failed";
  parse_progress: number;
  tags: string[] | null;
  effective_date: string;
  chunking_strategy: string;
  chunking_params: Record<string, any> | null;
  uploaded_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  chunk_type: string;
  created_at: string;
}

export interface ChunkListResponse {
  items: DocumentChunk[];
  total: number;
  page: number;
  page_size: number;
}

export interface ChunkingStrategyParam {
  key: string;
  label: string;
  type: string;
  default: number;
  min: number;
  max: number;
}

export interface ChunkingStrategyDef {
  name: string;
  label: string;
  description: string;
  params: ChunkingStrategyParam[];
}

export interface Citation {
  doc_id?: string;
  doc_name: string;
  chapter: string;
  section: string;
  page: number;
  original_text: string;
  confidence: number;
  chunk_id?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[] | null;
  confidence: number;
  feedback: "like" | "dislike" | null;
  created_at: string;
}

export interface ChatRequest {
  conversation_id?: string;
  question: string;
  search_mode: "hybrid" | "semantic" | "keyword";
  doc_scope: string[];
  detail_level: "brief" | "normal" | "detailed";
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
  confidence: number;
  intent_type: string;
  response_time_ms: number;
  related_questions: string[];
}

export interface Conversation {
  id: string;
  title: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface StatsOverview {
  total_documents: number;
  total_queries: number;
  total_conversations: number;
  total_users: number;
  avg_response_time_ms: number;
  today_queries: number;
  feedback: {
    likes: number;
    dislikes: number;
  };
}
