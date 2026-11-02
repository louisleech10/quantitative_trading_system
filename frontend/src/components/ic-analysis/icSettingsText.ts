import type { ICMethodSettings } from '@/lib/types';

/**
 * ICPERF Task 0.4 ㊸：IC 頁方法選擇與門檻開關之顯示文字（面板與報告頂端「本次設定」共用）。
 *
 * ⓘ 文案（`IC_SETTING_TIPS`）依真實資料實測寫成（收據 `handoffs/run_receipts/20261101-icperf-toggle-impact.json`：
 * L 格 BTCUSDT 4h、200 欄 seeded 子集、同切分與其他設定固定，預設 vs 各選項之通過數與差集）；只描述方向，不保證普遍結果。
 */

export const IC_SETTING_LABELS: Record<keyof ICMethodSettings, string> = {
  ic_method_selection: 'IC 方法',
  winsorization_method: '縮尾方法',
  return_type_selection: '收益率類型',
  redundancy_method_selection: '去重方法',
  monotonicity_test: '單調性門檻',
};

export const IC_SETTING_OPTION_LABELS: Record<string, string> = {
  spearman: 'Spearman（秩）',
  pearson: 'Pearson（線性）',
  kendall: 'Kendall（秩）',
  percentile: '百分位 1–99%',
  mad: 'MAD',
  zscore: 'Z 分數',
  none: '不縮尾',
  simple: '簡單報酬',
  log: '對數報酬',
  risk_adjusted: '除以波動',
  greedy: '貪婪（相關）',
  hierarchical: '階層分群',
  vif: 'VIF（共線性）',
};

/** 每個設定一句話（滑鼠移入 ⓘ 顯示）。 */
export const IC_SETTING_TIPS: Record<keyof ICMethodSettings, string> = {
  ic_method_selection: '換估計量會改 IC 值與排序；實測 Kendall 結果較接近預設，Pearson 倖存集合變動較大，依資料而異',
  winsorization_method: '決定極端值如何截斷；實測換方法後第 5 段通過集合約二至四成不同，增減方向依資料而異',
  return_type_selection: '標籤報酬之定義；實測對數報酬與簡單報酬幾乎相同，除以波動時通過集合差異較大',
  redundancy_method_selection: '高相關特徵只留代表之方法；實測階層分群倖存數略少、VIF 倖存較多但耗時明顯較長',
  monotonicity_test: '關閉後不再以分位單調性剔除；實測預設門檻下無差，放寬 p 值時通過數明顯增加',
};

/**
 * v5.58 (v)：跨標的模式下仍生效之設定之 ⓘ（該模式之消費點與預設不同處；依 `handoffs/run_receipts/20261101-icperf-toggle-impact.json`
 * 之 `v558_cross_sectional` 實測寫成）。未列者沿用 `IC_SETTING_TIPS`。
 */
export const IC_SETTING_TIPS_XSEC: Partial<Record<keyof ICMethodSettings, string>> = {
  ic_method_selection: '換估計量改每截面 IC、逐標的 IC 與衰減；標的僅兩個時每截面三法皆為 ±1，只逐標的 IC 不同',
  return_type_selection: '跨標的只影響 IC 衰減與半衰期（主 IC 標籤固定為一根 K 線對數報酬）；秩方法下對數與簡單報酬相同',
};

/** v5.58 (v)：該模式不適用之標示與 ⓘ（跨標的路徑不做預處理、去重與門檻篩選）。 */
export const IC_SETTING_NOT_APPLICABLE_LABEL = '此模式不適用';
export const IC_SETTING_NOT_APPLICABLE_TIPS: Partial<Record<keyof ICMethodSettings, string>> = {
  winsorization_method: '跨標的模式不做縮尾預處理，此設定不影響結果',
  redundancy_method_selection: '跨標的模式不做去重，輸出全部特徵，此設定不影響結果',
  monotonicity_test: '跨標的模式不設篩選門檻（只排序），此設定不影響結果',
};

/** v5.58 (v)：依分析模式取一個設定之 ⓘ 文案。 */
export const settingTip = (key: keyof ICMethodSettings, mode: string | undefined, applicable: boolean): string => {
  if (!applicable) {
    return IC_SETTING_NOT_APPLICABLE_TIPS[key] ?? `${IC_SETTING_NOT_APPLICABLE_LABEL}`;
  }
  if (mode === 'cross_sectional') {
    return IC_SETTING_TIPS_XSEC[key] ?? IC_SETTING_TIPS[key];
  }
  return IC_SETTING_TIPS[key];
};

/** v5.58 (w)：報告表 IC 自相關欄（契約 `report_keys.ic_autocorrelation`）。 */
export const IC_AUTOCORR_LABEL = 'IC 自相關';
export const IC_AUTOCORR_TIP = 'IC 序列前後期之相關，越高 IC 越持續、ICIR 之獨立樣本越少；滾動窗重疊時實測多近 1';
/** v5.58 (w)：`ic_autocorr_reason`（值為空時之原因，封閉集合）之顯示。 */
export const IC_AUTOCORR_REASON_LABELS: Record<string, string> = {
  insufficient_samples: 'IC 序列有效值不足 3 個',
  no_adjacent_pairs: 'IC 序列無相鄰兩期皆有值',
  constant_series: 'IC 序列為常數',
};

/** toggle 值之顯示。 */
export const onOffLabel = (value: boolean) => (value ? '開' : '關');

/** 設定值之顯示文字。 */
export const settingValueLabel = (key: keyof ICMethodSettings, value: ICMethodSettings[keyof ICMethodSettings]) =>
  key === 'monotonicity_test' ? onOffLabel(Boolean(value)) : IC_SETTING_OPTION_LABELS[String(value)] ?? String(value);
