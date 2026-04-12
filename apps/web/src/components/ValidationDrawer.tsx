import type { ReactNode } from "react";
import { Alert, Drawer, Empty, Space, Spin, Typography } from "antd";

type ValidationDrawerProps = {
  title: string;
  open: boolean;
  onClose: () => void;
  loading: boolean;
  loadingText: string;
  error: string | null;
  errorMessage: string;
  emptyDescription?: string;
  width?: number;
  children?: ReactNode;
};

export function ValidationDrawer({
  title,
  open,
  onClose,
  loading,
  loadingText,
  error,
  errorMessage,
  emptyDescription = "暂无详情数据",
  width = 720,
  children,
}: ValidationDrawerProps) {
  const hasContent = children !== undefined && children !== null;

  return (
    <Drawer title={title} open={open} onClose={onClose} width={width}>
      {loading ? (
        <Space direction="vertical" size={8} style={{ display: "flex" }}>
          <Spin />
          <Typography.Text type="secondary">{loadingText}</Typography.Text>
        </Space>
      ) : null}

      {error ? <Alert type="error" message={errorMessage} description={error} showIcon /> : null}

      {!loading && !error ? hasContent ? children : <Empty description={emptyDescription} /> : null}
    </Drawer>
  );
}
