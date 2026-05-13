import {
  DislikeOutlined,
  LikeOutlined,
} from "@ant-design/icons";
import { Button, Space, message } from "antd";
import { useState } from "react";
import { submitFeedback } from "../api/client";

interface Props {
  kbId: string;
  messageId: string;
}

type Rating = "helpful" | "not_helpful" | null;

export function FeedbackButtons({ kbId, messageId }: Props) {
  const [rating, setRating] = useState<Rating>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleRate(value: "helpful" | "not_helpful") {
    if (rating !== null) return; // already rated
    setSubmitting(true);
    try {
      await submitFeedback(kbId, messageId, value);
      setRating(value);
      message.success("感谢反馈");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "反馈提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Space size={4}>
      <Button
        type="text"
        size="small"
        icon={<LikeOutlined style={rating === "helpful" ? { color: "#1677ff" } : undefined} />}
        disabled={rating !== null || submitting}
        onClick={() => handleRate("helpful")}
      />
      <Button
        type="text"
        size="small"
        icon={<DislikeOutlined style={rating === "not_helpful" ? { color: "#ff4d4f" } : undefined} />}
        disabled={rating !== null || submitting}
        onClick={() => handleRate("not_helpful")}
      />
    </Space>
  );
}
