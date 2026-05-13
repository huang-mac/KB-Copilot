import { Popover, Space, Tag, Typography } from "antd";
import { useState } from "react";
import type { Source } from "../types/api";

const { Text, Paragraph } = Typography;

interface Props {
  sources: Source[];
}

export function SourcePopover({ sources }: Props) {
  const [openSourceId, setOpenSourceId] = useState<string | null>(null);

  if (!sources?.length) return null;

  // Deduplicate by doc_id + chunk_index
  const unique = new Map<string, Source>();
  for (const s of sources) {
    const key = `${s.doc_id}-${s.chunk_index}`;
    if (!unique.has(key)) {
      unique.set(key, s);
    }
  }

  return (
    <div className="message-sources">
      <Text type="secondary" style={{ fontSize: 12 }}>
        参考来源：
      </Text>
      <div style={{ marginTop: 4, display: "flex", flexWrap: "wrap", gap: 4 }}>
        {[...unique.values()].map((s) => {
          const key = `${s.doc_id}-${s.chunk_index}`;
          const isOpen = openSourceId === key;
          return (
            <Popover
              key={key}
              open={isOpen}
              onOpenChange={(visible) => setOpenSourceId(visible ? key : null)}
              trigger="click"
              placement="bottomLeft"
              title={
                <Text strong style={{ fontSize: 13 }}>
                  {s.filename}
                </Text>
              }
              content={
                <div style={{ maxWidth: 420 }}>
                  <Space size={4} style={{ marginBottom: 8 }}>
                    <Tag color="blue">
                      相关度：{(s.score * 100).toFixed(1)}%
                    </Tag>
                    {s.source_type && (
                      <Tag color={s.source_type === "fusion" ? "green" : "default"}>
                        {s.source_type === "fusion" ? "混合检索" :
                         s.source_type === "vector" ? "语义" : "关键词"}
                      </Tag>
                    )}
                  </Space>
                  <Paragraph
                    style={{
                      fontSize: 13,
                      lineHeight: 1.7,
                      margin: 0,
                      padding: 10,
                      background: "#f0f7ff",
                      borderRadius: 6,
                      borderLeft: "3px solid #60a5fa",
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {s.content}
                  </Paragraph>
                </div>
              }
            >
              <Tag
                color="blue"
                style={{ cursor: "pointer" }}
              >
                {s.filename} #{s.chunk_index + 1}
              </Tag>
            </Popover>
          );
        })}
      </div>
    </div>
  );
}
