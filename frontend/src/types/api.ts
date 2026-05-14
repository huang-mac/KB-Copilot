export type DocumentStatus = "queued" | "processing" | "indexing" | "completed" | "failed";

export interface DocumentRecord {
  kb_id: string;
  doc_id: string;
  filename: string;
  chunk_count: number;
  status: DocumentStatus;
  created_at: string;
  error_message?: string | null;
}

export interface DocumentUploadResponse extends DocumentRecord {
  message: string;
  job_id?: string | null;
  job_status?: string | null;
}

export interface IndexJobResponse {
  kb_id: string;
  job_id: string;
  doc_id: string;
  filename: string;
  status: "queued" | "processing" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  content_type?: string | null;
  error_message?: string | null;
}

export interface DocumentListResponse {
  documents: DocumentRecord[];
}

export interface Source {
  doc_id: string;
  filename: string;
  chunk_index: number;
  score: number;
  content: string;
  source_type?: string;  // "vector" | "keyword" | "fusion"
}

export interface ChatResponse {
  conversation_id: string;
  answer: string;
  sources: Source[];
  intent?: string;
  tool_result?: Record<string, unknown>;
}

export interface ConversationRecord {
  kb_id: string;
  conversation_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  conversations: ConversationRecord[];
}

export interface ConversationMessage {
  kb_id: string;
  conversation_id: string;
  message_id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[] | null;
  created_at: string;
}

export interface ConversationMessagesResponse {
  messages: ConversationMessage[];
}

export interface TimingMetric {
  count: number;
  avg_ms: number;
  p95_ms: number;
  max_ms: number;
}

export interface MetricsResponse {
  enabled: boolean;
  counters: Record<string, number>;
  timings: Record<string, TimingMetric>;
}
