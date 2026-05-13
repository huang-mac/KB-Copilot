import { useCallback, useRef, useState } from "react";
import type { Source } from "../types/api";
import { askQuestionStream, regenerateAnswer } from "../api/client";

export interface StreamState {
  status: "idle" | "streaming" | "done" | "error" | "aborted";
  tokens: string[];
  sources: Source[] | null;
  conversationId: string | null;
  error: string | null;
}

const SSE_LINE_REGEX = /^(event|data):\s?(.*)$/;

// Small delay between token renders to ensure typewriter effect
async function tick(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

export function useChatStream(kbId: string) {
  const [state, setState] = useState<StreamState>({
    status: "idle",
    tokens: [],
    sources: null,
    conversationId: null,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  const reset = useCallback(() => {
    setState({
      status: "idle",
      tokens: [],
      sources: null,
      conversationId: null,
      error: null,
    });
  }, []);

  const stop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setState((prev) => {
      if (prev.status === "streaming") {
        return { ...prev, status: "aborted" as const, error: null };
      }
      return prev;
    });
  }, []);

  async function startStream(
    question: string,
    topK: number,
    conversationId?: string | null,
  ) {
    console.log("[useChatStream] startStream called, question:", question);
    setState({
      status: "streaming",
      tokens: [],
      sources: null,
      conversationId: null,
      error: null,
    });

    const abortController = new AbortController();
    abortRef.current = abortController;

    try {
      console.log("[useChatStream] fetching SSE stream...");
      const body = await askQuestionStream(kbId, question, topK, conversationId, abortController.signal);
      console.log("[useChatStream] got response body, getting reader...");
      const reader = body.getReader();
      readerRef.current = reader;

      const decoder = new TextDecoder();
      let buffer = "";
      let eventCount = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log("[useChatStream] stream done, total events:", eventCount);
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          const match = line.match(SSE_LINE_REGEX);
          if (!match) continue;

          const [, field, value] = match;
          if (field === "event") {
            currentEvent = value;
          } else if (field === "data" && currentEvent) {
            try {
              const parsed = JSON.parse(value);
              eventCount++;
              console.log("[useChatStream] event:", currentEvent, "data:", parsed);
              processEvent(currentEvent, parsed);
              // Yield to React so it can render each token individually
              if (currentEvent === "token") {
                await tick();
              }
            } catch (e) {
              console.warn("[useChatStream] malformed JSON:", value, e);
            }
            currentEvent = "";
          }
        }
      }
    } catch (err) {
      console.error("[useChatStream] error:", err);
      if (abortController.signal.aborted) {
        setState((prev) => ({ ...prev, status: "aborted" as const }));
      } else {
        setState((prev) => ({
          ...prev,
          status: "error" as const,
          error: err instanceof Error ? err.message : "连接中断",
        }));
      }
    } finally {
      abortRef.current = null;
      readerRef.current = null;
    }
  }

  function processEvent(event: string, data: Record<string, unknown>) {
    switch (event) {
      case "token": {
        const token = data.token as string;
        setState((prev) => ({
          ...prev,
          tokens: [...prev.tokens, token],
        }));
        break;
      }
      case "sources":
        setState((prev) => ({
          ...prev,
          sources: (data.sources as Source[]) || [],
        }));
        break;
      case "done":
        setState((prev) => ({
          ...prev,
          status: "done" as const,
          conversationId: data.conversation_id as string,
        }));
        break;
      case "error":
        setState((prev) => ({
          ...prev,
          status: "error" as const,
          error: (data.detail as string) || "未知错误",
        }));
        break;
    }
  }

  async function startRegenerate(
    conversationId: string,
    topK: number,
  ) {
    console.log("[useChatStream] startRegenerate called, conversationId:", conversationId);
    setState({
      status: "streaming",
      tokens: [],
      sources: null,
      conversationId: null,
      error: null,
    });

    const abortController = new AbortController();
    abortRef.current = abortController;

    try {
      const body = await regenerateAnswer(kbId, conversationId, topK, abortController.signal);
      const reader = body.getReader();
      readerRef.current = reader;

      const decoder = new TextDecoder();
      let buffer = "";
      let eventCount = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log("[useChatStream] regenerate done, total events:", eventCount);
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          const match = line.match(SSE_LINE_REGEX);
          if (!match) continue;

          const [, field, value] = match;
          if (field === "event") {
            currentEvent = value;
          } else if (field === "data" && currentEvent) {
            try {
              const parsed = JSON.parse(value);
              eventCount++;
              processEvent(currentEvent, parsed);
              if (currentEvent === "token") {
                await tick();
              }
            } catch {
              // skip malformed JSON
            }
            currentEvent = "";
          }
        }
      }
    } catch (err) {
      console.error("[useChatStream] regenerate error:", err);
      if (abortController.signal.aborted) {
        setState((prev) => ({ ...prev, status: "aborted" as const }));
      } else {
        setState((prev) => ({
          ...prev,
          status: "error" as const,
          error: err instanceof Error ? err.message : "连接中断",
        }));
      }
    } finally {
      abortRef.current = null;
      readerRef.current = null;
    }
  }

  return {
    state,
    startStream,
    startRegenerate,
    stop,
    reset,
  };
}
