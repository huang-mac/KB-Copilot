import { CheckOutlined, CopyOutlined } from "@ant-design/icons";
import { Button, Tooltip } from "antd";
import { useState } from "react";

interface Props {
  content: string;
}

export function CopyButton({ content }: Props) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(content).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => {
        // Fallback for environments without clipboard API
        const textarea = document.createElement("textarea");
        textarea.value = content;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
    );
  }

  return (
    <Tooltip title={copied ? "已复制" : "复制回答"}>
      <Button
        type="text"
        size="small"
        icon={copied ? <CheckOutlined style={{ color: "#52c41a" }} /> : <CopyOutlined />}
        onClick={handleCopy}
      />
    </Tooltip>
  );
}
