import { useEffect, useState } from "react";
import { Alert, Card, Space, Typography } from "antd";

import { P3BlueForceGenerator } from "../components/p3/P3BlueForceGenerator";
import type { MockDemandScenarioId, ToolDemandSheet } from "../lib/api";
import {
  createMockDemandSheet,
  getDemandSheet,
  getDemandSheets,
  withdrawDemandSheet,
} from "../lib/toolHub";

export function XXP3SimPage() {
  const [sheets, setSheets] = useState<ToolDemandSheet[]>([]);
  const [activeSheet, setActiveSheet] = useState<ToolDemandSheet | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState<MockDemandScenarioId>("simulated_blue_force");
  const [loadingSheets, setLoadingSheets] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [withdrawing, setWithdrawing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadDemandSheets();
  }, []);

  async function loadDemandSheets(preferredSheetId?: string | null) {
    try {
      setLoadingSheets(true);
      setError(null);
      const response = await getDemandSheets();
      const nextSheets = response.data.items;
      setSheets(nextSheets);

      const nextSheetId =
        preferredSheetId === null
          ? null
          : preferredSheetId ?? activeSheet?.sheet_id ?? nextSheets[0]?.sheet_id ?? null;
      if (!nextSheetId) {
        setActiveSheet(null);
        return;
      }
      await handleSelectSheet(nextSheetId, nextSheets);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载已生成工单失败");
    } finally {
      setLoadingSheets(false);
    }
  }

  function replaceSheetInList(detail: ToolDemandSheet, moveToFront = false) {
    setSheets((currentSheets) => {
      const hasExisting = currentSheets.some((sheet) => sheet.sheet_id === detail.sheet_id);
      const existing = currentSheets.filter((sheet) => sheet.sheet_id !== detail.sheet_id);
      if (moveToFront || currentSheets.length === 0 || !hasExisting) {
        return [detail, ...existing];
      }
      return currentSheets.map((sheet) => (sheet.sheet_id === detail.sheet_id ? detail : sheet));
    });
  }

  async function handleSelectSheet(sheetId: string, availableSheets?: ToolDemandSheet[]) {
    const targetSheet = (availableSheets ?? sheets).find((sheet) => sheet.sheet_id === sheetId);
    if (!targetSheet) {
      setActiveSheet(null);
      return;
    }

    try {
      setError(null);
      setActiveSheet(targetSheet);
      const response = await getDemandSheet(sheetId);
      const detail = response.data;
      setActiveSheet(detail);
      replaceSheetInList(detail);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载工单详情失败");
    }
  }

  async function handleGenerate(scenarioId: MockDemandScenarioId) {
    try {
      setGenerating(true);
      setError(null);
      const response = await createMockDemandSheet(scenarioId);
      setActiveSheet(response.data);
      replaceSheetInList(response.data, true);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "生成模拟工单失败");
    } finally {
      setGenerating(false);
    }
  }

  async function handleWithdraw() {
    if (!activeSheet) {
      return;
    }

    const previousSheet = activeSheet;
    const optimisticSheet: ToolDemandSheet = {
      ...activeSheet,
      lifecycle_status: "withdrawn",
      terminal_reason_code: "manual_withdraw",
      terminal_reason_message: "P3 模拟页撤销当前工单，准备重新测试构单。",
    };

    try {
      setWithdrawing(true);
      setError(null);
      setActiveSheet(optimisticSheet);
      replaceSheetInList(optimisticSheet);
      const response = await withdrawDemandSheet(activeSheet.sheet_id, {
        actor_id: "p3-sim",
        actor_phase: "P3",
        reason_code: "manual_withdraw",
        reason_message: "P3 模拟页撤销当前工单，准备重新测试构单。",
      });
      setActiveSheet(response.data);
      replaceSheetInList(response.data);
    } catch (withdrawError) {
      setActiveSheet(previousSheet);
      replaceSheetInList(previousSheet);
      setError(withdrawError instanceof Error ? withdrawError.message : "撤销当前工单失败");
    } finally {
      setWithdrawing(false);
    }
  }

  return (
    <div id="xx-p3-page" style={{ minHeight: "100vh", background: "#f6f8fa", padding: "24px 24px 32px" }}>
      <div id="xx-p3-shell" style={{ maxWidth: 1200, margin: "0 auto" }}>
        <Card
          id="xx-p3-hero"
          style={{
            borderRadius: 24,
            border: "1px solid #d0d7de",
            background: "linear-gradient(180deg, #ffffff 0%, #f6f8fa 100%)",
            boxShadow: "0 10px 24px rgba(31, 35, 40, 0.06)",
            marginBottom: 20,
          }}
        >
          <Space direction="vertical" size={8} style={{ display: "flex" }}>
            <Typography.Title level={2} style={{ margin: 0 }}>
              P3 模拟发生器
            </Typography.Title>
            <Typography.Paragraph style={{ margin: 0, color: "#57606a", maxWidth: 760 }}>
              独立模拟 P3 阶段生成 `工具需求单` 的入口页。它不展示 P4 内部处理细节，只负责把标准输入对象发出去。
            </Typography.Paragraph>
          </Space>
        </Card>

        {error ? (
          <Alert id="xx-p3-page-error" type="error" showIcon message={error} style={{ marginBottom: 16 }} />
        ) : null}

        <P3BlueForceGenerator
          sheets={sheets}
          activeSheet={activeSheet}
          selectedScenarioId={selectedScenarioId}
          loadingSheets={loadingSheets}
          generating={generating}
          withdrawing={withdrawing}
          error={error}
          onGenerate={handleGenerate}
          onScenarioChange={setSelectedScenarioId}
          onSelectSheet={handleSelectSheet}
          onWithdraw={handleWithdraw}
        />
      </div>
    </div>
  );
}
