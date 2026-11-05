/**
 * ICPERF Task 0.4 ㊻（SPEC v5.81）：深度分析候選欄之請求欄位。
 *
 * - 手選（manual）⇒ 送 `selected_features`（原樣），`top_n` 為其數量。
 * - 頁面自動預選（auto）⇒ **不送** `selected_features`，只送 `top_n`：由後端對完整 summary_table 依排序鍵全域選取
 *   （有倖存 ⇒ 倖存中前 n；無倖存 ⇒ 全域前 n 並標診斷模式）。自動預選只看當頁列，不得當成手選送出。
 */
export type FeatureSelectionSource = 'auto' | 'manual';

/** 未手選時可選之診斷候選數（預設 30；30 為呈現與相容之選擇、非統計最佳值） */
export const DEEP_TOP_N_OPTIONS = [30, 50, 100] as const;

export function buildDeepCandidateFields(
  source: FeatureSelectionSource,
  selectedFeatures: string[],
  topN: number,
): { selected_features?: string[]; top_n: number } {
  if (source === 'manual' && selectedFeatures.length > 0) {
    return { selected_features: [...selectedFeatures], top_n: selectedFeatures.length };
  }
  return { top_n: topN };
}
