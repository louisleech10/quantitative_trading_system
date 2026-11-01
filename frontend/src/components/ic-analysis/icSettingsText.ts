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

/** 只揭露、不設開關之項（契約 `disclosed_keys`）。 */
export const IC_AUTOCORR_LABEL = 'IC 自相關';
export const IC_AUTOCORR_TIP = '後端有算 IC 一階自相關，但不進報告也不參與篩選，故不設開關（待決定加入報告或移除）';

/** toggle 值之顯示。 */
export const onOffLabel = (value: boolean) => (value ? '開' : '關');

/** 設定值之顯示文字。 */
export const settingValueLabel = (key: keyof ICMethodSettings, value: ICMethodSettings[keyof ICMethodSettings]) =>
  key === 'monotonicity_test' ? onOffLabel(Boolean(value)) : IC_SETTING_OPTION_LABELS[String(value)] ?? String(value);
