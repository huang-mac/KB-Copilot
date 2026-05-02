export interface DocumentUploadResponse {
  kb_id: string;
  doc_id: string;
  filename: string;
  chunk_count: number;
  message: string;
}

export interface Source {
  doc_id: string;
  filename: string;
  chunk_index: number;
  score: number;
  content: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
}
