import type { HacDataWarningDetail, ICAnalysisConfig, ICMethodSettings } from '@/lib/types';

/** ICPERF ㊹：縱向顯著性無法計算之顯示（封閉集合，p／q 欄）。 */
export const HAC_NOT_COMPUTABLE_LABELS: Record<'insufficient_sample' | 'degenerate', string> = {
  insufficient_sample: '無法計算：樣本不足',
  degenerate: '無法計算：序列退化',
};

/** ICPERF ㊹：持續性不可估（p 照常、資料是否足夠無法判定）之 ⓘ。 */
export const HAC_PERSISTENCE_NOT_ESTIMABLE_TIP =
  '無法評估資料是否足夠：此特徵之一階自相關無法估計（例如滯後段為常數），故未做資料不足模擬；p 值照常計算與篩選';

/** ICPERF ㊹：資料不足判定未執行（當下記憶體不足以模擬，可重跑）之 ⓘ。 */
export const HAC_WARNING_NOT_EVALUATED_TIP =
  '資料是否足夠之判定未執行：當下可用記憶體不足以完成模擬，可稍後重跑；p 值照常計算與篩選';

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

/** ICPERF ㊹：資料不足警示之 ⓘ 文案（數值取自 `data_warning_detail` 封閉八鍵）。 */
export const hacDataWarningTip = (d: HacDataWarningDetail): string =>
  `資料不足以可靠檢定：樣本外段 ${d.n_obs} 根、標籤 ${d.horizon} 根（約相當於 ${Math.round(d.approx_independent_n)} 筆獨立資料），` +
  `特徵一階自相關 ${d.phi_hat.toFixed(3)}（中位數不偏估計）；在你設定之顯著水準 ${d.alpha} 下，以同樣本數、同標籤長度、同自相關之簡化模型` +
  `（特徵 AR(1)、報酬獨立）模擬 ${d.replications} 次，單一檢定之誤判率約 ${pct(d.estimated_null_reject_rate)}（應為 ${pct(d.alpha)}；` +
  `同條件下設計邊界之對照為 ${pct(d.reference_reject_rate)}）；此為模型近似、非此特徵之實測誤判率，p 值可能偏樂觀`;

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
  ic_method_selection: '換估計量會改 IC 值、排序與顯著性 p 值（p 依所選方法檢定）；實測 Kendall 結果較接近預設，Pearson 倖存集合變動較大，依資料而異',
  winsorization_method: '決定極端值如何截斷；實測換方法後第 5 段通過集合約二至四成不同，增減方向依資料而異',
  return_type_selection: '標籤報酬之定義；實測對數報酬與簡單報酬幾乎相同，除以波動時通過集合差異較大',
  redundancy_method_selection: '高相關特徵只留代表之方法；實測階層分群倖存數略少、VIF 倖存較多但耗時明顯較長',
  monotonicity_test: '關閉後不再以分位單調性剔除；實測預設門檻下無差，放寬 p 值時通過數明顯增加',
};

/**
 * v5.58 (v)：跨標的模式下仍生效之設定之 ⓘ（該模式之消費點與預設不同處；依 `handoffs/run_receipts/20261101-icperf-toggle-impact.json`
 * 之 `v558_cross_sectional` 實測寫成）。未列者沿用 `IC_SETTING_TIPS`。
 * v5.59 (ae)：跨標的主 IC 標籤改依收益率類型（與 IC 衰減同一定義）；收益率類型句依 kline 4h 10 標的完整歷史實測
 * （`runs/icperf/task04/v559/xsec_return_type_impact.json`：對數 vs 簡單之截面排序 5,087 截面全同、Spearman／Kendall 主 IC
 * 逐值相同；除以波動 97% 截面排序改變、主 IC 絕對值明顯變小）。
 */
export const IC_SETTING_TIPS_XSEC: Partial<Record<keyof ICMethodSettings, string>> = {
  ic_method_selection: '換估計量改每截面 IC、逐標的 IC 與衰減；標的僅兩個時每截面三法皆為 ±1，只逐標的 IC 不同',
  return_type_selection: '主 IC 標籤與 IC 衰減同依此定義；實測秩方法下對數與簡單報酬結果相同，除以波動約九成七截面排序改變',
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
/**
 * v5.59 (aj)：IC 自相關 ⓘ 依分析模式分句——縱向為滾動 IC 序列（滾動窗重疊）、跨標的為逐時點截面 IC 序列（各時點獨立算）、
 * 事件型之滾動窗依事件先後成窗（`ic_filter_orchestrator._ic_autocorr_by_feature`），前後期為事件序而非日曆時間。
 * 跨標的「實測多近 0」：kline 4h 10 標的完整歷史、三因果特徵 × 三方法 × 三收益率類型之 |IC 自相關| ≤ 0.034
 * （`runs/icperf/task04/v559/xsec_return_type_impact.json`）。
 */
export const IC_AUTOCORR_TIPS: Record<ICAnalysisConfig['mode'], string> = {
  global: 'IC 序列前後期之相關，越高 IC 越持續、ICIR 之獨立樣本越少；滾動窗重疊時實測多近 1',
  event: '事件序上 IC 前後期之相關（依事件先後，非日曆時間），越高越持續、ICIR 之獨立樣本越少；滾動窗重疊時多近 1',
  cross_sectional: '逐時點截面 IC 前後期之相關（未成立之截面計為缺值），越高越持續、ICIR 之獨立樣本越少；實測多近 0',
};
/** v5.59 (aj)：依分析模式取 IC 自相關 ⓘ；未知或未給 ⇒ 縱向句（同 `ICSummaryTable` 之 `analysisMode` 預設 global）。 */
export const icAutocorrTip = (mode: string | undefined): string =>
  mode === 'cross_sectional' || mode === 'event' ? IC_AUTOCORR_TIPS[mode] : IC_AUTOCORR_TIPS.global;
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
