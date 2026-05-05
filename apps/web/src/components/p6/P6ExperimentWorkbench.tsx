import type {
  P6DisplayExperimentRecord,
  P6DisplayPromotionCandidate,
} from "../../lib/p6";
import { P6BlueprintNode } from "./P6BlueprintNode";
import type {
  P6ExperimentDraft,
  P6ExperimentRecord,
  P6OptionItem,
  P6ResolvedNodeCard,
  P6TargetOption,
} from "./p6ExperimentConfig";

type P6ExperimentPreviewEntry = {
  id: string;
  label: string;
  node: P6PortalViewNode;
  resolvedCard: P6ResolvedNodeCard;
};

type P6ExperimentWorkbenchProps = {
  draft: P6ExperimentDraft;
  targetOptions: P6TargetOption[];
  moduleTemplateOptions: P6OptionItem<string>[];
  userTemplateOptions: P6OptionItem<string>[];
  bindingPresetOptions: P6OptionItem<string>[];
  layoutPresetOptions: P6OptionItem<string>[];
  previewEntries: P6ExperimentPreviewEntry[];
  record: P6ExperimentRecord;
  savedRecords: P6DisplayExperimentRecord[];
  promotionCandidates: P6DisplayPromotionCandidate[];
  saving: boolean;
  saveError: string | null;
  onClose: () => void;
  onTargetChange: (targetId: string) => void;
  onModuleTemplateChange: (templateId: string) => void;
  onUserTemplateChange: (templateId: string) => void;
  onBindingPresetChange: (bindingPresetId: string) => void;
  onLayoutPresetChange: (layoutPresetId: string) => void;
  onPromotionDecisionChange: (decision: "hold" | "candidate") => void;
  onTargetStageToggle: (stageId: string) => void;
  onSave: () => void;
};

type P6PortalViewNode =
  import("./p6PortalData").P6PortalViewNode;

const promotionStageOptions = ["P3", "P4", "P5"];

export function P6ExperimentWorkbench({
  draft,
  targetOptions,
  moduleTemplateOptions,
  userTemplateOptions,
  bindingPresetOptions,
  layoutPresetOptions,
  previewEntries,
  record,
  savedRecords,
  promotionCandidates,
  saving,
  saveError,
  onClose,
  onTargetChange,
  onModuleTemplateChange,
  onUserTemplateChange,
  onBindingPresetChange,
  onLayoutPresetChange,
  onPromotionDecisionChange,
  onTargetStageToggle,
  onSave,
}: P6ExperimentWorkbenchProps) {
  const isUserTarget = draft.selectedTargetId === "user";
  const selectedTarget = targetOptions.find((item) => item.id === draft.selectedTargetId) ?? targetOptions[0];

  return (
    <aside data-testid="p6-experiment-workbench" className="p6-experiment-workbench">
      <div className="p6-experiment-workbench__topline">
        <div>
          <div className="p6-experiment-workbench__badge">P6.4</div>
          <h2 className="p6-experiment-workbench__title">卡片配置实验台</h2>
        </div>
        <button type="button" className="p6-experiment-workbench__close" onClick={onClose}>
          收起
        </button>
      </div>

      <div className="p6-experiment-workbench__section">
        <div className="p6-experiment-workbench__section-title">模板选择区</div>
        <label className="p6-experiment-workbench__field">
          <span className="p6-experiment-workbench__label">配置对象</span>
          <select
            aria-label="配置对象"
            className="p6-experiment-workbench__select"
            value={draft.selectedTargetId}
            onChange={(event) => onTargetChange(event.target.value)}
          >
            {targetOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <div className="p6-experiment-workbench__hint">{selectedTarget?.detail}</div>
        <div className="p6-experiment-workbench__option-grid">
          {(isUserTarget ? userTemplateOptions : moduleTemplateOptions).map((option) => (
            <button
              key={option.id}
              type="button"
              className={[
                "p6-experiment-workbench__option",
                (isUserTarget ? draft.userProfile.templateId : previewEntries[0]?.resolvedCard.templateId) === option.id
                  ? "is-active"
                  : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => (isUserTarget ? onUserTemplateChange(option.id) : onModuleTemplateChange(option.id))}
            >
              <span>{option.label}</span>
              <small>{option.description}</small>
            </button>
          ))}
        </div>
      </div>

      <div className="p6-experiment-workbench__section">
        <div className="p6-experiment-workbench__section-title">绑定配置区</div>
        <div className="p6-experiment-workbench__field-row">
          <span className="p6-experiment-workbench__label">投影来源</span>
          <span className="p6-experiment-workbench__pill">PortalProjection</span>
        </div>
        {isUserTarget ? (
          <div className="p6-experiment-workbench__hint">参与用户节点维持轻量绑定，不消费阶段状态卡字段。</div>
        ) : (
          <div className="p6-experiment-workbench__option-grid">
            {bindingPresetOptions.map((option) => (
              <button
                key={option.id}
                type="button"
                className={[
                  "p6-experiment-workbench__option",
                  previewEntries[0]?.resolvedCard.bindingPresetId === option.id ? "is-active" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => onBindingPresetChange(option.id)}
              >
                <span>{option.label}</span>
                <small>{option.description}</small>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="p6-experiment-workbench__section">
        <div className="p6-experiment-workbench__section-title">布局组合区</div>
        <div className="p6-experiment-workbench__option-grid">
          {layoutPresetOptions.map((option) => (
            <button
              key={option.id}
              type="button"
              className={[
                "p6-experiment-workbench__option",
                draft.layoutPresetId === option.id ? "is-active" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => onLayoutPresetChange(option.id)}
            >
              <span>{option.label}</span>
              <small>{option.description}</small>
            </button>
          ))}
        </div>
      </div>

      <div className="p6-experiment-workbench__section">
        <div className="p6-experiment-workbench__section-title">实时预览区</div>
        <div className={["p6-experiment-workbench__preview-grid", draft.layoutPresetId.includes("compare") ? "is-compare" : ""].join(" ")}>
          {previewEntries.map((entry) => (
            <div key={entry.id} className="p6-experiment-workbench__preview-card">
              <div className="p6-experiment-workbench__preview-label">{entry.label}</div>
              <div className="p6-experiment-workbench__preview-stage">
                <P6BlueprintNode
                  node={entry.node}
                  position={{ x: 0, y: 0 }}
                  active={false}
                  emphasized={false}
                  visiblePins={[]}
                  onClick={() => undefined}
                  onDoubleClick={() => undefined}
                  onMouseDown={() => undefined}
                  onMouseEnter={() => undefined}
                  onMouseLeave={() => undefined}
                  preview
                  cardPresentation={entry.resolvedCard}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="p6-experiment-workbench__section">
        <div className="p6-experiment-workbench__section-title">实验记录区</div>
        <div className="p6-experiment-workbench__record-title">{record.title}</div>
        <div className="p6-experiment-workbench__record-summary">{record.summary}</div>
        <div className="p6-experiment-workbench__subgroup">
          <strong>问题清单</strong>
          <ul className="p6-experiment-workbench__list">
            {record.issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        </div>
        <div className="p6-experiment-workbench__subgroup">
          <strong>证据引用</strong>
          <ul className="p6-experiment-workbench__list">
            {record.evidenceRefs.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div className="p6-experiment-workbench__subgroup">
          <strong>已登记记录</strong>
          <ul className="p6-experiment-workbench__list">
            {savedRecords.map((item) => (
              <li key={item.experiment_id}>{item.result_summary}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="p6-experiment-workbench__section">
        <div className="p6-experiment-workbench__section-title">晋升评估区</div>
        <div className="p6-experiment-workbench__option-grid">
          <button
            type="button"
            className={[
              "p6-experiment-workbench__option",
              draft.promotionDecision === "hold" ? "is-active" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => onPromotionDecisionChange("hold")}
          >
            <span>保留实验</span>
            <small>继续留在 P6.4，不进入正式候选。</small>
          </button>
          <button
            type="button"
            className={[
              "p6-experiment-workbench__option",
              draft.promotionDecision === "candidate" ? "is-active" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => onPromotionDecisionChange("candidate")}
          >
            <span>进入候选</span>
            <small>形成正式候选，后续反哺 P3 / P4 / P5。</small>
          </button>
        </div>
        <div className="p6-experiment-workbench__check-grid">
          {promotionStageOptions.map((stageId) => (
            <label key={stageId} className="p6-experiment-workbench__checkbox">
              <input
                type="checkbox"
                checked={draft.targetStages.includes(stageId)}
                onChange={() => onTargetStageToggle(stageId)}
              />
              <span>{stageId}</span>
            </label>
          ))}
        </div>
        <div className="p6-experiment-workbench__recommendation">{record.recommendation}</div>
        <div className="p6-experiment-workbench__subgroup">
          <strong>候选输出</strong>
          <ul className="p6-experiment-workbench__list">
            {promotionCandidates.map((item) => (
              <li key={item.promotion_candidate_id}>{item.adoption_reason}</li>
            ))}
          </ul>
        </div>
        {saveError ? <div className="p6-experiment-workbench__recommendation">{saveError}</div> : null}
        <button type="button" className="p6-portal-source-control__button" onClick={onSave} disabled={saving}>
          {saving ? "登记中" : "登记实验"}
        </button>
      </div>
    </aside>
  );
}
