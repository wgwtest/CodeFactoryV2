import { Alert, Badge, Button, Card, Col, Divider, Progress, Row, Space, Statistic, Steps, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { getP1RefactorBootstrap } from "../api/p1RefactorApi";
import type { P1RefactorBootstrap, P1ResponseEnvelope } from "../contracts";
import { p1R0Bootstrap } from "../fixtures/p1R0Fixtures";
import { QualityDashboardPage } from "../quality/QualityDashboardPage";
import "./P1RefactorShell.css";

const statusColor: Record<P1RefactorBootstrap["navigation"][number]["status"], string> = {
  existing_page: "green",
  r0_shell: "blue",
  to_build: "orange",
};

const statusText: Record<P1RefactorBootstrap["navigation"][number]["status"], string> = {
  existing_page: "已有页面",
  r0_shell: "R0 骨架",
  to_build: "待实现",
};

const stageItems = [
  { title: "文档接入", description: "上传、解析、结构化预检" },
  { title: "策略适配", description: "选择策略包并冻结版本" },
  { title: "机器抽取", description: "实时生成知识与语义图谱" },
  { title: "质量评估", description: "规则命中、证据覆盖、图谱质量" },
  { title: "发布候选", description: "等待治理确认后正式入库" },
];

const runningDocuments = [
  {
    name: "业务资料包/供货协议_华东区_2026Q1.pdf",
    stage: "候选合并",
    progress: 68,
    stream: "已连接 Stream",
    quality: "带警告通过",
  },
  {
    name: "业务资料包/销售框架协议_北区_2026.docx",
    stage: "实体抽取",
    progress: 56,
    stream: "已回退轮询",
    quality: "评估中",
  },
  {
    name: "业务资料包/补充协议_项目A_2026Q1.pdf",
    stage: "规则清洗",
    progress: 42,
    stream: "已连接 Stream",
    quality: "需重算",
  },
];

export function P1RefactorShell() {
  const location = useLocation();
  const [bootstrap, setBootstrap] = useState<P1ResponseEnvelope<P1RefactorBootstrap>>(p1R0Bootstrap);
  const [apiWarning, setApiWarning] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    void getP1RefactorBootstrap()
      .then((response) => {
        if (!cancelled) {
          setBootstrap(response);
          setApiWarning(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "未知错误";
          setApiWarning(`后端 P1 adapter 暂不可用，当前显示前端示例数据：${message}`);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (location.pathname.startsWith("/p1/quality")) {
    return <QualityDashboardPage />;
  }

  if (location.pathname.startsWith("/p1/dev")) {
    return <P1DevShell bootstrap={bootstrap} apiWarning={apiWarning} />;
  }

  return <P1UserLanding sourceKind={bootstrap.source_kind} apiWarning={apiWarning} />;
}

function P1UserLanding({ sourceKind, apiWarning }: { sourceKind: string; apiWarning: string | null }) {
  return (
    <main className="p1-user-shell">
      <section className="p1-user-hero">
        <div>
          <Tag color="blue">P1 业务知识库</Tag>
          <Typography.Title className="p1-user-title">面向业务使用者的知识生成工作台</Typography.Title>
          <Typography.Paragraph className="p1-user-subtitle">
            从文档接入、策略选择、机器抽取、质量评估到发布候选，一屏看清知识库当前状态。复杂合同、规则和图谱细节保留在后台，
            默认入口优先回答业务用户最关心的三个问题：这个文件夹抽到哪了、结果质量如何、能不能交给下游系统使用。
          </Typography.Paragraph>
        </div>
        <Space wrap>
          <Tag color={sourceKind === "live" ? "green" : "orange"}>{sourceKind}</Tag>
          <Button>
            <Link to="/p1/dev">开发边界视图</Link>
          </Button>
          <Button type="primary">
            <Link to="/documents/intake">选择文件夹/导入资料</Link>
          </Button>
        </Space>
      </section>

      {apiWarning ? <Alert type="warning" showIcon message={apiWarning} style={{ marginBottom: 16 }} /> : null}

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={16}>
          <Card className="p1-user-panel">
            <div className="p1-user-panel-head">
              <div>
                <Typography.Title level={3}>从选中文件夹生成业务知识库</Typography.Title>
                <Typography.Text type="secondary">
                  来源文件夹：业务资料包 · 系统识别主题：合同与履约资料 · 推荐策略包：合同通用抽取 v3.12
                </Typography.Text>
              </div>
              <Badge status="processing" text="机器抽取中" />
            </div>
            <Divider />
            <Steps current={2} items={stageItems} />
            <div className="p1-user-action-row">
              <Button type="primary">
                <Link to="/archives">进入生成结果总览</Link>
              </Button>
              <Button>
                <Link to="/documents">查看文档清单</Link>
              </Button>
              <Button>
                <Link to="/policies">选择/调整策略包</Link>
              </Button>
              <Button>
                <Link to="/p1/quality">查看质量评估</Link>
              </Button>
            </div>
          </Card>
        </Col>

        <Col xs={24} xl={8}>
          <Card className="p1-user-panel p1-user-summary">
            <Typography.Title level={4}>今天的知识库状态</Typography.Title>
            <Row gutter={[12, 12]}>
              <Col span={12}>
                <Statistic title="文档总数" value={1248} />
              </Col>
              <Col span={12}>
                <Statistic title="运行中" value={36} valueStyle={{ color: "#2563eb" }} />
              </Col>
              <Col span={12}>
                <Statistic title="需重算" value={58} valueStyle={{ color: "#f97316" }} />
              </Col>
              <Col span={12}>
                <Statistic title="正式知识" value={24631} />
              </Col>
            </Row>
            <Divider />
            <Alert
              type="warning"
              showIcon
              message="规则版本已变化"
              description="部分候选知识需要按新策略增量重算；正式入库知识不会被直接覆盖。"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={16}>
          <Card className="p1-user-panel" title="正在抽取的文档">
            <div className="p1-doc-list">
              {runningDocuments.map((document) => (
                <div className="p1-doc-item" key={document.name}>
                  <div className="p1-doc-main">
                    <Typography.Text strong>{document.name}</Typography.Text>
                    <Typography.Text type="secondary">
                      当前阶段：{document.stage} · {document.stream}
                    </Typography.Text>
                  </div>
                  <div className="p1-doc-progress">
                    <Progress percent={document.progress} size="small" />
                    <Tag color={document.quality === "需重算" ? "orange" : document.quality === "评估中" ? "blue" : "green"}>
                      {document.quality}
                    </Tag>
                  </div>
                  <Button size="small">
                    <Link to="/archives">进入实时工作台</Link>
                  </Button>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        <Col xs={24} xl={8}>
          <Card className="p1-user-panel" title="下一步建议">
            <Space direction="vertical" size={12} style={{ width: "100%" }}>
              <Alert
                type="info"
                showIcon
                message="先验收用户入口"
                description="确认新建知识库、文档清单、启动抽取和实时工作台之间的跳转是否顺手。"
              />
              <Alert
                type="success"
                showIcon
                message="再验收质量解释"
                description="进入质量页确认规则命中、指标阈值、影响对象是否能看懂。"
              />
              <Alert
                type="warning"
                showIcon
                message="最后看正式输出"
                description="候选知识与正式知识供应接口已经分离，避免后续系统误读临时节点。"
              />
            </Space>
          </Card>
        </Col>
      </Row>
    </main>
  );
}

function P1DevShell({
  bootstrap,
  apiWarning,
}: {
  bootstrap: P1ResponseEnvelope<P1RefactorBootstrap>;
  apiWarning: string | null;
}) {
  const data = bootstrap.data;

  return (
    <main className="p1-refactor-shell">
      <section className="p1-refactor-hero">
        <div>
          <Tag color="geekblue">R0 / R1 Developer Shell</Tag>
          <Typography.Title className="p1-refactor-title">P1 重构开发边界视图</Typography.Title>
          <div className="p1-refactor-subtitle">
            这里保留给并行开发线程查看模块边界、合同输入输出和验收责任。终端用户默认入口已经移动到 /p1。
          </div>
        </div>
        <Space wrap>
          <Tag color={bootstrap.source_kind === "live" ? "green" : "orange"}>{bootstrap.source_kind}</Tag>
          <Button>
            <Link to="/p1">返回用户入口</Link>
          </Button>
          <Button type="primary">
            <Link to="/policies">进入策略配置</Link>
          </Button>
        </Space>
      </section>

      {apiWarning ? <Alert type="warning" showIcon message={apiWarning} style={{ marginBottom: 16 }} /> : null}

      <Card className="p1-refactor-panel">
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Statistic title="建议并行线程数" value={data.next_parallel_threads} suffix="条" />
          </Col>
          <Col xs={24} md={8}>
            <Statistic title="导航入口" value={data.navigation.length} suffix="个" />
          </Col>
          <Col xs={24} md={8}>
            <Statistic title="边界工作线" value={data.work_lines.length} suffix="条" />
          </Col>
        </Row>
        <Divider />
        <Typography.Title level={4}>P1 模块导航壳</Typography.Title>
        <Row gutter={[16, 16]}>
          {data.navigation.map((entry) => (
            <Col xs={24} md={12} xl={8} key={entry.key}>
              <Card
                className="p1-refactor-card"
                title={
                  <div className="p1-refactor-card-title">
                    <span>{entry.title}</span>
                    <Tag color={statusColor[entry.status]}>{statusText[entry.status]}</Tag>
                  </div>
                }
                extra={<span className="p1-refactor-route">{entry.route}</span>}
              >
                <Typography.Text type="secondary">责任线：{entry.owner_line}</Typography.Text>
                <div className="p1-refactor-contract-list">
                  {entry.contract_refs.map((contract) => (
                    <Tag key={contract}>{contract}</Tag>
                  ))}
                </div>
                <Divider />
                <Button type={entry.status === "existing_page" ? "primary" : "default"} block>
                  <Link to={entry.route}>打开入口</Link>
                </Button>
              </Card>
            </Col>
          ))}
        </Row>

        <Divider />
        <Typography.Title level={4}>并行开发工作线</Typography.Title>
        <Row gutter={[16, 16]}>
          {data.work_lines.map((line) => (
            <Col xs={24} md={12} xl={8} key={line.line_id}>
              <Card
                className="p1-refactor-workline"
                title={
                  <Space>
                    <Tag color="blue">{line.line_id}</Tag>
                    <span>{line.title}</span>
                  </Space>
                }
              >
                <Typography.Paragraph>{line.responsibility}</Typography.Paragraph>
                <Typography.Text strong>输入合同</Typography.Text>
                <div className="p1-refactor-contract-list">
                  {line.input_contracts.map((contract) => (
                    <Tag color="purple" key={contract}>
                      {contract}
                    </Tag>
                  ))}
                </div>
                <Divider />
                <Typography.Text strong>输出合同</Typography.Text>
                <div className="p1-refactor-contract-list">
                  {line.output_contracts.map((contract) => (
                    <Tag color="cyan" key={contract}>
                      {contract}
                    </Tag>
                  ))}
                </div>
                <Divider />
                <Typography.Text strong>验收方式</Typography.Text>
                {line.verification.map((item) => (
                  <Typography.Paragraph key={item} type="secondary" style={{ marginBottom: 4 }}>
                    {item}
                  </Typography.Paragraph>
                ))}
              </Card>
            </Col>
          ))}
        </Row>
      </Card>
    </main>
  );
}
