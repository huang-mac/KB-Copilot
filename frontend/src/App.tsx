import {
  CloudUploadOutlined,
  DatabaseOutlined,
  MessageOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  InputNumber,
  Layout,
  List,
  message,
  Row,
  Space,
  Statistic,
  Tag,
  Typography,
  Upload,
} from "antd";
import type { UploadProps } from "antd";
import { useEffect, useMemo, useState } from "react";

import { askQuestion, healthCheck, uploadDocument } from "./api/client";
import type { ChatResponse, DocumentUploadResponse } from "./types/api";

const { Header, Content } = Layout;
const { Paragraph, Text, Title } = Typography;

function App() {
  const [kbId, setKbId] = useState("default");
  const [question, setQuestion] = useState("KB Copilot 是什么？");
  const [topK, setTopK] = useState(5);
  const [serviceStatus, setServiceStatus] = useState("checking");
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [uploadedDocs, setUploadedDocs] = useState<DocumentUploadResponse[]>([]);
  const [chatResult, setChatResult] = useState<ChatResponse | null>(null);

  useEffect(() => {
    healthCheck()
      .then((result) => setServiceStatus(result.status))
      .catch(() => setServiceStatus("unavailable"));
  }, []);

  const uploadProps: UploadProps = useMemo(
    () => ({
      beforeUpload: async (file) => {
        setUploading(true);
        try {
          const result = await uploadDocument(kbId, file);
          setUploadedDocs((current) => [result, ...current]);
          message.success(`已索引 ${result.filename}，共 ${result.chunk_count} 个片段`);
        } catch (error) {
          message.error(error instanceof Error ? error.message : "上传失败");
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

  async function handleAsk() {
    if (!question.trim()) {
      message.warning("请输入问题");
      return;
    }

    setAsking(true);
    try {
      const result = await askQuestion(kbId, question.trim(), topK);
      setChatResult(result);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "问答失败");
    } finally {
      setAsking(false);
    }
  }

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
        <section className="hero-section">
          <Title level={2}>面向中小企业的通用知识库 RAG 系统</Title>
          <Paragraph type="secondary">
            上传企业文档，构建向量索引，通过语义检索和大模型生成带引用来源的回答。
            MVP1 先提供可演示的 Web 界面，便于 GitHub 展示和简历包装。
          </Paragraph>
        </section>

        <Row gutter={[24, 24]}>
          <Col xs={24} lg={8}>
            <Card title="知识库配置" className="panel-card">
              <Form layout="vertical">
                <Form.Item label="知识库 ID">
                  <Input
                    value={kbId}
                    onChange={(event) => setKbId(event.target.value || "default")}
                    placeholder="default"
                    prefix={<DatabaseOutlined />}
                  />
                </Form.Item>
                <Alert
                  type="info"
                  showIcon
                  message="MVP1 默认使用一个轻量知识库 ID"
                  description="后续 MVP1.5 会增加知识库列表、文档列表、删除和重新索引。"
                />
              </Form>

              <Divider />

              <Row gutter={12}>
                <Col span={12}>
                  <Statistic title="已上传文档" value={uploadedDocs.length} />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="最新片段数"
                    value={uploadedDocs[0]?.chunk_count ?? 0}
                  />
                </Col>
              </Row>
            </Card>

            <Card title="文档上传" className="panel-card">
              <Upload.Dragger {...uploadProps} disabled={uploading}>
                <p className="ant-upload-drag-icon">
                  <CloudUploadOutlined />
                </p>
                <p className="ant-upload-text">点击或拖拽文档到这里</p>
                <p className="ant-upload-hint">MVP1 当前支持 TXT、Markdown</p>
              </Upload.Dragger>

              <List
                className="doc-list"
                size="small"
                dataSource={uploadedDocs}
                locale={{ emptyText: "暂无上传记录" }}
                renderItem={(doc) => (
                  <List.Item>
                    <List.Item.Meta
                      title={doc.filename}
                      description={`doc_id: ${doc.doc_id} · chunks: ${doc.chunk_count}`}
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>

          <Col xs={24} lg={16}>
            <Card
              title={
                <Space>
                  <MessageOutlined />
                  智能问答
                </Space>
              }
              className="panel-card"
            >
              <Form layout="vertical">
                <Form.Item label="问题">
                  <Input.TextArea
                    rows={4}
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="请输入要查询的问题"
                  />
                </Form.Item>
                <Space>
                  <Text>Top K</Text>
                  <InputNumber min={1} max={20} value={topK} onChange={(value) => setTopK(value ?? 5)} />
                  <Button type="primary" loading={asking} onClick={handleAsk}>
                    开始问答
                  </Button>
                </Space>
              </Form>

              {chatResult && (
                <div className="answer-section">
                  <Title level={4}>回答</Title>
                  <Card className="answer-card">
                    <Paragraph>{chatResult.answer}</Paragraph>
                  </Card>

                  <Title level={4}>引用来源</Title>
                  <List
                    dataSource={chatResult.sources}
                    locale={{ emptyText: "本次回答没有返回引用来源" }}
                    renderItem={(source) => (
                      <List.Item>
                        <Card className="source-card">
                          <Space direction="vertical" size={8}>
                            <Space wrap>
                              <Tag color="blue">{source.filename}</Tag>
                              <Tag>chunk #{source.chunk_index}</Tag>
                              <Tag color="green">score {source.score.toFixed(4)}</Tag>
                            </Space>
                            <Paragraph ellipsis={{ rows: 5, expandable: true }}>
                              {source.content}
                            </Paragraph>
                          </Space>
                        </Card>
                      </List.Item>
                    )}
                  />
                </div>
              )}
            </Card>
          </Col>
        </Row>
      </Content>
    </Layout>
  );
}

export default App;
