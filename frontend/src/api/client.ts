import type {
  ChatResponse,
  ConversationListResponse,
  ConversationMessagesResponse,
  ConversationRecord,
  DocumentListResponse,
  DocumentUploadResponse,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof error.detail === "string" ? error.detail : JSON.stringify(error.detail));
  }
  return response.json() as Promise<T>;
}

export function uploadDocument(kbId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return request<DocumentUploadResponse>(
    `/api/v1/kbs/${encodeURIComponent(kbId)}/documents`,
    {
      method: "POST",
      body: formData,
    },
  );
}

export function listDocuments(kbId: string) {
  return request<DocumentListResponse>(`/api/v1/kbs/${encodeURIComponent(kbId)}/documents`);
}

export function deleteDocument(kbId: string, docId: string) {
  return request<{ kb_id: string; doc_id: string; message: string }>(
    `/api/v1/kbs/${encodeURIComponent(kbId)}/documents/${encodeURIComponent(docId)}`,
    {
      method: "DELETE",
    },
  );
}

export function reindexDocument(kbId: string, docId: string) {
  return request<DocumentUploadResponse>(
    `/api/v1/kbs/${encodeURIComponent(kbId)}/documents/${encodeURIComponent(docId)}/reindex`,
    {
      method: "POST",
    },
  );
}

export function listConversations(kbId: string) {
  return request<ConversationListResponse>(
    `/api/v1/kbs/${encodeURIComponent(kbId)}/conversations`,
  );
}

export function createConversation(kbId: string, title?: string) {
  return request<ConversationRecord>(
    `/api/v1/kbs/${encodeURIComponent(kbId)}/conversations`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title }),
    },
  );
}

export function listConversationMessages(kbId: string, conversationId: string) {
  return request<ConversationMessagesResponse>(
    `/api/v1/kbs/${encodeURIComponent(kbId)}/conversations/${encodeURIComponent(
      conversationId,
    )}/messages`,
  );
}

export function askQuestion(
  kbId: string,
  question: string,
  topK: number,
  conversationId?: string | null,
) {
  return request<ChatResponse>(
    `/api/v1/kbs/${encodeURIComponent(kbId)}/chat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question, top_k: topK, conversation_id: conversationId }),
    },
  );
}

export function healthCheck() {
  return request<{ status: string; service: string }>("/api/v1/health");
}
