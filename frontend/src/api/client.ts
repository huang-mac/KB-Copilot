import type { ChatResponse, DocumentUploadResponse } from "../types/api";

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

export function askQuestion(kbId: string, question: string, topK: number) {
  return request<ChatResponse>(
    `/api/v1/kbs/${encodeURIComponent(kbId)}/chat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question, top_k: topK }),
    },
  );
}

export function healthCheck() {
  return request<{ status: string; service: string }>("/api/v1/health");
}
