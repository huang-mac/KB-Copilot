import {
  CloudUploadOutlined,
  DeleteOutlined,
  LoadingOutlined,
  MessageOutlined,
  ReloadOutlined,
  RobotOutlined,
  StopOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Layout,
  List,
  message,
  Popconfirm,
  Row,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
} from "antd";
import type { TableProps, UploadProps } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  askQuestion,
  createConversation,
  deleteConversation,
  deleteDocument,
  healthCheck,
  listConversationMessages,
  listConversations,
  listDocuments,
  reindexDocument,
  uploadDocument,
} from "./api/client";
import { CopyButton } from "./components/CopyButton";
import { FeedbackButtons } from "./components/FeedbackButtons";
import { SourcePopover } from "./components/SourcePopover";
import { useAutoScroll } from "./hooks/useAutoScroll";
import { useChatStream } from "./hooks/useChatStream";
import type { ConversationMessage, ConversationRecord, DocumentRecord, Source } from "./types/api";

const { Header, Content } = Layout;
const { Paragraph, Text } = Typography;

function App() {
  const kbId = "default";
  const [question, setQuestion] = useState("KB Copilot 是什么？");
  const [topK, setTopK] = useState(5);
  const [serviceStatus, setServiceStatus] = useState("checking");
  const [uploading, setUploading] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);
  const [reindexingDocId, setReindexingDocId] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [conversationMessages, setConversationMessages] = useState<ConversationMessage[]>([]);
  const [lastResponseIntent, setLastResponseIntent] = useState<string | null>(null);
  const [lastResponseToolResult, setLastResponseToolResult] = useState<Record<string, unknown> | null>(null);
  const streamQuestionRef = useRef<string>("");

  const {
    state: streamState,
    startStream,
    startRegenerate,
    stop: stopStream,
    reset: resetStream,
  } = useChatStream(kbId);

  useEffect(() => {
    healthCheck()
      .then((result) => setServiceStatus(result.status))
      .catch(() => setServiceStatus("unavailable"));
  }, []);

  useEffect(() => {
    void refreshDocuments();
    void refreshConversations();
  }, [kbId]);

  // When streaming completes, append messages locally (no flash)
  useEffect(() => {
    if (streamState.status === "done" && streamState.conversationId) {
      const convId = streamState.conversationId;
      const question = streamQuestionRef.current;
      const answer = streamState.tokens.join("");
      const sources = streamState.sources;

      // Append messages to local state — only add user message for new questions
      if (answer) {
        const now = new Date().toISOString();
        const msgs: ConversationMessage[] = [];
        if (question) {
          msgs.push({
            kb_id: kbId,
            conversation_id: convId,
            message_id: crypto.randomUUID?.() || `${Date.now()}-user`,
            role: "user",
            content: question,
            created_at: now,
          });
        }
        msgs.push({
          kb_id: kbId,
          conversation_id: convId,
          message_id: crypto.randomUUID?.() || `${Date.now()}-assistant`,
          role: "assistant",
          content: answer,
          sources: sources ?? undefined,
          created_at: now,
        });
        setConversationMessages((prev) => [...prev, ...msgs]);
      }

      setActiveConversationId(convId);
      refreshConversations();
      resetStream();
      streamQuestionRef.current = "";
    }
  }, [streamState.status, streamState.conversationId]);

  async function refreshDocuments() {
    setLoadingDocuments(true);
    try {
      const result = await listDocuments(kbId);
      setDocuments(result.documents);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载文档列表失败");
    } finally {
      setLoadingDocuments(false);
    }
  }

  async function refreshConversations() {
    setLoadingConversations(true);
    try {
      const result = await listConversations(kbId);
      setConversations(result.conversations);
      if (!activeConversationId && result.conversations.length > 0) {
        const firstConversationId = result.conversations[0].conversation_id;
        setActiveConversationId(firstConversationId);
        await loadConversationMessages(firstConversationId);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载会话列表失败");
    } finally {
      setLoadingConversations(false);
    }
  }

  async function loadConversationMessages(conversationId: string) {
    setLoadingMessages(true);
    try {
      const result = await listConversationMessages(kbId, conversationId);
      setConversationMessages(result.messages);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载会话消息失败");
    } finally {
      setLoadingMessages(false);
    }
  }

  async function handleSelectConversation(conversationId: string) {
    setActiveConversationId(conversationId);
    await loadConversationMessages(conversationId);
  }

  async function handleCreateConversation() {
    try {
      const conversation = await createConversation(kbId);
      setActiveConversationId(conversation.conversation_id);
      setConversationMessages([]);
      await refreshConversations();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "新建会话失败");
    }
  }

  async function handleDeleteConversation(conversationId: string) {
    try {
      await deleteConversation(kbId, conversationId);
      message.success("会话已删除");
      // If the deleted conversation was active, switch to another one
      if (activeConversationId === conversationId) {
        const remaining = conversations.filter((c) => c.conversation_id !== conversationId);
        if (remaining.length > 0) {
          setActiveConversationId(remaining[0].conversation_id);
          await loadConversationMessages(remaining[0].conversation_id);
        } else {
          setActiveConversationId(null);
          setConversationMessages([]);
        }
      }
      await refreshConversations();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除会话失败");
    }
  }

  const uploadProps: UploadProps = useMemo(
    () => ({
      beforeUpload: async (file) => {
        setUploading(true);
        try {
          const result = await uploadDocument(kbId, file);
          await refreshDocuments();
          message.success(`已索引 ${result.filename}，共 ${result.chunk_count} 个片段`);
        } catch (error) {
          message.error(error instanceof Error ? error.message : "上传失败");
          await refreshDocuments();
        } finally {
          setUploading(false);
        }
        return false;
      },
      maxCount: 1,
      accept: ".txt,.md,.markdown",
      showUploadList: false,
    }),
    [kbId],
  );

  async function handleDeleteDocument(docId: string) {
    setDeletingDocId(docId);
    try {
      await deleteDocument(kbId, docId);
      message.success("文档已删除");
      await refreshDocuments();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除失败");
    } finally {
      setDeletingDocId(null);
    }
  }

  async function handleReindexDocument(docId: string) {
    setReindexingDocId(docId);
    try {
      const result = await reindexDocument(kbId, docId);
      message.success(`已重新索引 ${result.filename}，共 ${result.chunk_count} 个片段`);
      await refreshDocuments();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "重新索引失败");
      await refreshDocuments();
    } finally {
      setReindexingDocId(null);
    }
  }

  async function handleAsk() {
    if (!question.trim()) {
      message.warning("请输入问题");
      return;
    }

    setAsking(true);
    resetStream();
    setQuestion("");

    const currentQuestion = question.trim();
    const currentConversationId = activeConversationId;

    // Use non-streaming fallback when SSE is not available
    try {
      const result = await askQuestion(kbId, currentQuestion, topK, currentConversationId);
      setActiveConversationId(result.conversation_id);
      setLastResponseIntent(result.intent ?? null);
      setLastResponseToolResult(result.tool_result ?? null);
      await refreshConversations();
      await loadConversationMessages(result.conversation_id);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "问答失败");
    } finally {
      setAsking(false);
    }
  }

  async function handleAskStream() {
    if (!question.trim()) {
      message.warning("请输入问题");
      return;
    }

    console.log("[App] handleAskStream called, question:", question.trim());
    setAsking(true);
    setQuestion("");

    const currentQuestion = question.trim();
    streamQuestionRef.current = currentQuestion;
    await startStream(currentQuestion, topK, activeConversationId);
    console.log("[App] startStream completed, final status:", streamState.status);
    setAsking(false);
  }

  async function handleStopStream() {
    stopStream();
    setAsking(false);
    // Append partial message locally to avoid reload flash
    if (streamState.tokens.length > 0 && activeConversationId) {
      const now = new Date().toISOString();
      const userMsg: ConversationMessage = {
        kb_id: kbId,
        conversation_id: activeConversationId,
        message_id: crypto.randomUUID?.() || `${Date.now()}-user`,
        role: "user",
        content: streamQuestionRef.current,
        created_at: now,
      };
      const assistantMsg: ConversationMessage = {
        kb_id: kbId,
        conversation_id: activeConversationId,
        message_id: crypto.randomUUID?.() || `${Date.now()}-assistant`,
        role: "assistant",
        content: streamState.tokens.join("") + " [已中断]",
        sources: streamState.sources ?? undefined,
        created_at: now,
      };
      setConversationMessages((prev) => [...prev, userMsg, assistantMsg]);
      streamQuestionRef.current = "";
    }
    await refreshConversations();
  }

  async function handleRegenerate(conversationId: string) {
    setAsking(true);
    resetStream();
    try {
      await startRegenerate(conversationId, topK);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "重新生成失败");
    }
    setAsking(false);
  }

  function renderMessageContent(content: string) {
    return (
      <div className="markdown-body">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    );
  }

  const isStreaming = streamState.status === "streaming";
  const fullStreamingText = streamState.tokens.join("");

  // Auto-scroll: re-scroll when messages grow or new tokens arrive
  const { containerRef } = useAutoScroll(
    conversationMessages.length + fullStreamingText.length + (isStreaming ? 1 : 0),
  );

  const documentColumns: TableProps<DocumentRecord>["columns"] = [
    {
      title: "文档",
      dataIndex: "filename",
      render: (filename: string, record) => (
        <Space direction="vertical" size={2}>
          <Text strong>{filename}</Text>
          <Text type="secondary" className="mono-text">
            {record.doc_id}
          </Text>
        </Space>
      ),
    },
    {
      title: "片段数",
      dataIndex: "chunk_count",
      align: "right",
      width: 96,
    },
    {
      title: "索引状态",
      dataIndex: "status",
      render: (status: DocumentRecord["status"]) => {
        const statusMap = {
          indexing: { color: "processing", text: "索引中" },
          completed: { color: "success", text: "已完成" },
          failed: { color: "error", text: "失败" },
        } as const;
        const meta = statusMap[status];
        return <Tag color={meta.color}>{meta.text}</Tag>;
      },
    },
    {
      title: "上传时间",
      dataIndex: "created_at",
      responsive: ["lg"],
      render: (value: string) => new Date(value).toLocaleString("zh-CN"),
    },
    {
      title: "失败原因",
      dataIndex: "error_message",
      ellipsis: true,
      render: (error?: string | null) => error || "-",
    },
    {
      title: "操作",
      key: "actions",
      width: 180,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<ReloadOutlined />}
            loading={reindexingDocId === record.doc_id}
            disabled={record.status === "indexing" || deletingDocId === record.doc_id}
            onClick={() => handleReindexDocument(record.doc_id)}
          >
            重新索引
          </Button>
          <Popconfirm
            title="确认删除文档？"
            description="会同步删除 MinIO 原文件和 Qdrant 中的文档片段。"
            okText="删除"
            cancelText="取消"
            onConfirm={() => handleDeleteDocument(record.doc_id)}
          >
            <Button
              danger
              type="link"
              icon={<DeleteOutlined />}
              loading={deletingDocId === record.doc_id}
              disabled={reindexingDocId === record.doc_id}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <Space size={12}>
          <RobotOutlined className="brand-icon" />
          <div>
            <div className="brand-title">KB Copilot</div>
            <div className="brand-subtitle">智能知识库问答助手</div>
          </div>
        </Space>
        <Tag color={serviceStatus === "ok" ? "green" : "orange"}>
          API: {serviceStatus}
        </Tag>
      </Header>

      <Content className="app-content">
        <Tabs
          className="main-tabs"
          defaultActiveKey="chat"
          items={[
            {
              key: "chat",
              label: "智能问答",
              children: (
                <Row gutter={[24, 24]}>
                  <Col xs={24} lg={7}>
                    <Card
                      title="历史会话"
                      className="panel-card"
                      extra={
                        <Button size="small" onClick={handleCreateConversation}>
                          新建会话
                        </Button>
                      }
                    >
                      <List
                        loading={loadingConversations}
                        dataSource={conversations}
                        locale={{ emptyText: "暂无会话，直接提问会自动创建" }}
                        renderItem={(conversation) => (
                          <List.Item
                            className={
                              activeConversationId === conversation.conversation_id
                                ? "conversation-item active"
                                : "conversation-item"
                            }
                            onClick={() => handleSelectConversation(conversation.conversation_id)}
                            actions={[
                              <Popconfirm
                                key="delete"
                                title="确认删除会话？"
                                description="将同时删除该会话下的所有消息。"
                                okText="删除"
                                cancelText="取消"
                                onConfirm={(e) => {
                                  e?.stopPropagation();
                                  handleDeleteConversation(conversation.conversation_id);
                                }}
                                onCancel={(e) => e?.stopPropagation()}
                              >
                                <Button
                                  type="link"
                                  danger
                                  size="small"
                                  icon={<DeleteOutlined />}
                                  onClick={(e) => e.stopPropagation()}
                                />
                              </Popconfirm>,
                            ]}
                          >
                            <Space direction="vertical" size={2}>
                              <Text strong>{conversation.title}</Text>
                              <Text type="secondary">
                                {new Date(conversation.updated_at).toLocaleString("zh-CN")}
                              </Text>
                            </Space>
                          </List.Item>
                        )}
                      />
                    </Card>
                  </Col>

                  <Col xs={24} lg={17}>
                    <Card
                      title={
                        <Space>
                          <MessageOutlined />
                          智能问答
                        </Space>
                      }
                      className="panel-card"
                    >

                      <div
                        ref={containerRef}
                        className="message-scroll-area"
                      >
                        <List
                          className="message-list"
                          loading={loadingMessages}
                          dataSource={conversationMessages}
                          locale={{ emptyText: "当前会话暂无消息" }}
                          renderItem={(item) => (
                            <List.Item className={`chat-message ${item.role}`}>
                              <Card className="answer-card">
                                <Space direction="vertical" size={8} style={{ width: "100%" }}>
                                  <Space>
                                    <Tag color={item.role === "user" ? "blue" : "green"}>
                                      {item.role === "user" ? "用户" : "助手"}
                                    </Tag>
                                    {item.role === "assistant" && (
                                      <Button
                                        size="small"
                                        type="link"
                                        icon={<ReloadOutlined />}
                                        disabled={isStreaming}
                                        onClick={() => handleRegenerate(
                                          activeConversationId || "",
                                        )}
                                      >
                                        重新生成
                                      </Button>
                                    )}
                                    {item.role === "assistant" && (
                                      <CopyButton content={item.content} />
                                    )}
                                    {item.role === "assistant" && (
                                      <FeedbackButtons kbId={kbId} messageId={item.message_id} />
                                    )}
                                  </Space>
                                  {item.role === "user"
                                    ? <Paragraph>{item.content}</Paragraph>
                                    : (item.content
                                      ? renderMessageContent(item.content)
                                      : <Alert type="info" showIcon message="知识库中暂无相关信息，建议尝试换个问法或联系人工客服。" />
                                    )
                                  }
                                  {item.role === "assistant" && lastResponseIntent && (
                                    <Tag color={
                                      lastResponseIntent === "order_query" ? "orange" :
                                      lastResponseIntent === "clarification_required" ? "default" :
                                      "processing"
                                    }>
                                      意图：{lastResponseIntent === "kb_qa" ? "知识库问答" :
                                             lastResponseIntent === "order_query" ? "订单查询" :
                                             lastResponseIntent === "clarification_required" ? "需要澄清" :
                                             lastResponseIntent}
                                    </Tag>
                                  )}
                                  {item.role === "assistant" && lastResponseToolResult && (
                                    <Card size="small" title="工具调用结果" style={{ marginTop: 8 }}>
                                      <pre style={{ fontSize: 12, margin: 0, whiteSpace: "pre-wrap" }}>
                                        {JSON.stringify(lastResponseToolResult, null, 2)}
                                      </pre>
                                    </Card>
                                  )}
                                  {item.role === "assistant" && item.sources?.length ? (
                                    <SourcePopover sources={item.sources} />
                                  ) : null}
                                </Space>
                              </Card>
                            </List.Item>
                          )}
                        />

                        {/* Streaming message — rendered outside List for reliable display */}
                        {isStreaming && (
                          <div className="chat-message assistant" style={{ marginBottom: 12 }}>
                            <Card className="answer-card">
                              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                                <Space>
                                  <Tag color="green">助手</Tag>
                                  <LoadingOutlined style={{ color: "#1677ff" }} />
                                  <Text type="secondary">正在生成...</Text>
                                </Space>
                                {fullStreamingText ? (
                                  renderMessageContent(fullStreamingText)
                                ) : (
                                  <Text type="secondary" italic>等待回答...</Text>
                                )}
                                {streamState.sources?.length ? <SourcePopover sources={streamState.sources} /> : null}
                              </Space>
                            </Card>
                          </div>
                        )}

                        {(streamState.status === "aborted" || streamState.status === "error") && fullStreamingText && (
                          <div className="chat-message assistant" style={{ marginBottom: 12 }}>
                            <Card className="answer-card">
                              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                                <Space>
                                  <Tag color="green">助手</Tag>
                                  {streamState.status === "aborted" && (
                                    <Tag color="orange">已中断</Tag>
                                  )}
                                  {streamState.status === "error" && (
                                    <Tag color="red">错误</Tag>
                                  )}
                                </Space>
                                {renderMessageContent(fullStreamingText)}
                                {streamState.sources?.length ? <SourcePopover sources={streamState.sources} /> : null}
                                {streamState.status === "error" && streamState.error && (
                                  <Alert
                                    type="error"
                                    message={streamState.error}
                                    showIcon
                                  />
                                )}
                              </Space>
                            </Card>
                          </div>
                        )}

                        {/* Follow-up suggestions — shown after last assistant message */}
                        {null}
                      </div>

                      <Form layout="vertical">
                        <Form.Item label="问题">
                          <Input.TextArea
                            rows={4}
                            value={question}
                            onChange={(event) => setQuestion(event.target.value)}
                            placeholder="请输入要查询的问题"
                            disabled={isStreaming}
                          />
                        </Form.Item>
                        <Space>
                          <Text>Top K</Text>
                          <InputNumber
                            min={1}
                            max={20}
                            value={topK}
                            onChange={(value) => setTopK(value ?? 5)}
                            disabled={isStreaming}
                          />
                          {isStreaming ? (
                            <Button
                              danger
                              icon={<StopOutlined />}
                              onClick={handleStopStream}
                            >
                              停止生成
                            </Button>
                          ) : (
                            <Button
                              type="primary"
                              loading={asking}
                              onClick={handleAskStream}
                            >
                              发送
                            </Button>
                          )}
                        </Space>
                      </Form>
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: "documents",
              label: "文档管理",
              children: (
                <>
                  <Card title="文档管理" className="panel-card">
                    <Row gutter={[24, 16]} align="middle">
                      <Col xs={12} md={6}>
                        <Statistic title="当前知识库" value={kbId} />
                      </Col>
                      <Col xs={12} md={6}>
                        <Statistic title="文档总数" value={documents.length} />
                      </Col>
                      <Col xs={12} md={6}>
                        <Statistic
                          title="已完成索引"
                          value={documents.filter((doc) => doc.status === "completed").length}
                        />
                      </Col>
                      <Col xs={24} md={6}>
                        <Button
                          icon={<ReloadOutlined />}
                          loading={loadingDocuments}
                          onClick={refreshDocuments}
                        >
                          刷新列表
                        </Button>
                      </Col>
                    </Row>
                  </Card>

                  <Row gutter={[24, 24]}>
                    <Col xs={24} lg={8}>
                      <Card title="文档上传" className="panel-card">
                        <Upload.Dragger {...uploadProps} disabled={uploading}>
                          <p className="ant-upload-drag-icon">
                            <CloudUploadOutlined />
                          </p>
                          <p className="ant-upload-text">
                            {uploading ? "正在上传文档" : "点击或拖拽文档到这里"}
                          </p>
                          <p className="ant-upload-hint">当前支持 TXT、Markdown</p>
                        </Upload.Dragger>

                        <Alert
                          className="upload-tip"
                          type="info"
                          showIcon
                          message="上传后会立即解析、切分并写入 Qdrant"
                          description="索引失败的文档也会保留在列表中，便于查看失败原因。"
                        />
                      </Card>
                    </Col>

                    <Col xs={24} lg={16}>
                      <Card title="文档列表" className="panel-card">
                        <Table<DocumentRecord>
                          rowKey="doc_id"
                          loading={loadingDocuments}
                          columns={documentColumns}
                          dataSource={documents}
                          pagination={{ pageSize: 8 }}
                          scroll={{ x: 860 }}
                        />
                      </Card>
                    </Col>
                  </Row>
                </>
              ),
            },
          ]}
        />
      </Content>
    </Layout>
  );
}

export default App;
