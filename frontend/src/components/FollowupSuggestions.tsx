import { Button, Space } from "antd";
import { useEffect, useState } from "react";
import { getSuggestions } from "../api/client";

interface Props {
  kbId: string;
  question: string;
  answer: string;
  conversationId: string | null;
  onSelect: (question: string) => void;
}

export function FollowupSuggestions({
  kbId,
  question,
  answer,
  conversationId,
  onSelect,
}: Props) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!answer) return;
    let cancelled = false;

    async function fetch() {
      setLoading(true);
      try {
        const result = await getSuggestions(kbId, question, answer, conversationId);
        if (!cancelled) {
          setSuggestions(result.suggestions);
        }
      } catch {
        // silently ignore — suggestions are best-effort
        if (!cancelled) setSuggestions([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetch();
    return () => {
      cancelled = true;
    };
  }, [kbId, question, answer, conversationId]);

  if (!suggestions.length && !loading) return null;

  return (
    <div style={{ marginTop: 8 }}>
      <Space wrap size={[8, 8]}>
        {suggestions.map((s, i) => (
          <Button
            key={i}
            size="small"
            onClick={() => onSelect(s)}
          >
            {s}
          </Button>
        ))}
      </Space>
    </div>
  );
}
