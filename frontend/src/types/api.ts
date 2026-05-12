export type DocumentStatus = "indexing" | "completed" | "failed";

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
}

export interface ChatResponse {
  conversation_id: string;
  answer: string;
  sources: Source[];
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
