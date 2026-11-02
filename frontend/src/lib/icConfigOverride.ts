import type { ICAnalysisConfig, ICDiversificationConfig, ICMethodSettings } from './types';

/** ㊸：IC 頁設定鍵之規格（kind／後端 config path／選項／預設）。 */
export interface ICSettingSpec {
  kind: 'select' | 'toggle';
  /** `config_override` 之巢狀路徑（ICConfig alias 形狀，如 `global.default_method`）。 */
  path: readonly string[];
  options?: readonly string[];
  default: string | boolean;
  /**
   * ICPERF Task 0.2 v5.58 (v)：該設定於其路徑無消費點之分析模式（契約 `not_applicable_modes`）——該模式下控制項停用並標
   * 「此模式不適用」、不送出、「本次設定」不列。
   */
  not_applicable_modes?: readonly string[];
}

/**
 * ICPERF Task 0.4 ㊸：IC 頁方法選擇與門檻開關之規格——須與 `momentum/Analysis/contracts/ui_stage_toggles.json` 之
 * `setting_keys` **逐值相同**（`icSettings.test.ts` 對證；契約 ⇔ 後端由 pytest `test_icperf_ui_toggles.py` 對證）。
 * 原 `vif_filter` 併入去重方法之 `vif` 選項；`ic_autocorrelation` 後端算出但無消費者，只揭露不設開關（契約 `disclosed_keys`）。
 */
export const IC_SETTING_SPECS: Record<keyof ICMethodSettings, ICSettingSpec> = {
  ic_method_selection: {
    kind: 'select',
    path: ['global', 'default_method'],
    options: ['spearman', 'pearson', 'kendall'],
    default: 'spearman',
  },
  winsorization_method: {
    kind: 'select',
    path: ['preprocessing', 'winsorization', 'method'],
    options: ['percentile', 'mad', 'zscore', 'none'],
    default: 'percentile',
    not_applicable_modes: ['cross_sectional'],
  },
  return_type_selection: {
    kind: 'select',
    path: ['labels', 'return_type'],
    options: ['simple', 'log', 'risk_adjusted'],
    default: 'simple',
  },
  redundancy_method_selection: {
    kind: 'select',
    path: ['redundancy', 'method'],
    options: ['greedy', 'hierarchical', 'vif'],
    default: 'greedy',
    not_applicable_modes: ['cross_sectional'],
  },
  monotonicity_test: {
    kind: 'toggle',
    path: ['thresholds', 'monotonicity_gate_enabled'],
    default: true,
    not_applicable_modes: ['cross_sectional'],
  },
};

/** ㊸：設定鍵之顯示順序（＝`IC_SETTING_SPECS` 之鍵）。 */
export const IC_SETTING_KEYS = Object.keys(IC_SETTING_SPECS) as (keyof ICMethodSettings)[];

/** ㊸：全部取預設之設定（＝後端 `load_ic_config()` 之現行值，經契約對證）。 */
export const DEFAULT_IC_SETTINGS: ICMethodSettings = {
  ic_method_selection: 'spearman',
  winsorization_method: 'percentile',
  return_type_selection: 'simple',
  redundancy_method_selection: 'greedy',
  monotonicity_test: true,
};

/** ㊸：補齊未設定之鍵（未設定＝預設）。 */
export const resolveICSettings = (settings?: Partial<ICMethodSettings> | null): ICMethodSettings => ({
  ...DEFAULT_IC_SETTINGS,
  ...(settings ?? {}),
});

/** ㊸：值≠預設之鍵（送出與「本次設定」標色皆依此）。 */
export const nonDefaultICSettingKeys = (settings?: Partial<ICMethodSettings> | null): (keyof ICMethodSettings)[] => {
  const full = resolveICSettings(settings);
  return IC_SETTING_KEYS.filter((key) => full[key] !== IC_SETTING_SPECS[key].default);
};

/** v5.58 (v)：該設定於此分析模式是否生效（未給模式＝生效）。 */
export const isICSettingApplicable = (key: keyof ICMethodSettings, mode?: string | null): boolean =>
  !mode || !(IC_SETTING_SPECS[key].not_applicable_modes ?? []).includes(mode);

/** v5.58 (v)：此分析模式實際生效之設定鍵（顯示順序同 `IC_SETTING_KEYS`）。 */
export const applicableICSettingKeys = (mode?: string | null): (keyof ICMethodSettings)[] =>
  IC_SETTING_KEYS.filter((key) => isICSettingApplicable(key, mode));

/** 依路徑寫入巢狀物件（中途節點不存在則建立；既有節點之其他鍵保留）。 */
const setNested = (target: Record<string, unknown>, path: readonly string[], value: unknown) => {
  let cursor = target;
  path.slice(0, -1).forEach((part) => {
    const next = cursor[part];
    if (typeof next !== 'object' || next === null) {
      cursor[part] = {};
    }
    cursor = cursor[part] as Record<string, unknown>;
  });
  cursor[path[path.length - 1]] = value;
};

/**
 * ICPERF Task 0.4 ㊲：多元化約束之顯示用預設（＝後端 `momentum/Analysis/ic_config_schema.py`
 * `RedundancyConfig.DiversificationConfig` 之預設；`enabled` 預設關，三數值預設待使用者定）。
 * 只在使用者尚未調整時作為面板之初始顯示值；未調整前不送出（後端沿用其設定）。
 */
export const DEFAULT_DIVERSIFICATION: ICDiversificationConfig = {
  enabled: false,
  min_categories: 3,
  min_data_sources: 2,
  max_same_category_pct: 0.4,
};

/**
 * IC 分析請求之 `config_override` 之**唯一**產生點。
 *
 * 🔴 SPLITUNIFY `Task 10.6`：本函式原本是 `hooks/useICAnalysis.ts` 的模組私有常數。
 * 事件掃描端（`buildEventScanRequest`）要送**同一份** `config_override` 才可能取得同一條
 * canonical 邊界，而複製一份到第二個檔案就是本票要消滅的「兩份真相源」——兩份一旦漂移
 * （例：門檻鍵少一個），兩端會各自算出合法但不同的切分，且兩份數字都看起來正常。
 * ⇒ 抽到 `lib/` 讓兩個入口共用；抽出時**行為逐字不變**（鍵、條件、型別皆原樣搬移）。
 *
 * 🔴 放在 `lib/` 而不是留在 hooks：`lib/api.ts` 需要它，而 `api.ts` 匯入 hooks 模組會把
 * React 拉進所有 api 消費者（含可能的 server 端匯入路徑）。本檔無 React 相依。
 *
 * ICPERF Task 0.4 ㊲：`config.diversification` 有值時才送 `redundancy.diversification`（整組四鍵）；
 * 初始狀態（未設定）之 payload 與改前逐字相同。
 *
 * ICPERF Task 0.4 ㊸：`config.ic_settings` 中值≠預設之鍵，依 `IC_SETTING_SPECS[鍵].path` 寫入（與既有 thresholds／
 * redundancy／labels 節合併，不覆蓋其他鍵）；全為預設或未設定 ⇒ payload 與改前逐字相同。
 */
export const buildConfigOverride = (config: ICAnalysisConfig) => {
  const thresholds: Record<string, number | boolean> = {
    ic_mean_min: config.thresholds.ic_mean_min,
    icir_min: config.thresholds.icir_min,
    p_value_max: config.thresholds.p_value_max,
  };

  if (typeof config.thresholds.monotonicity_score_min === 'number') {
    thresholds.monotonicity_score_min = config.thresholds.monotonicity_score_min;
  }

  const override = {
    thresholds,
    redundancy: {
      correlation_threshold: config.thresholds.correlation_threshold,
      ...(config.diversification
        ? {
            diversification: {
              enabled: config.diversification.enabled,
              min_categories: config.diversification.min_categories,
              min_data_sources: config.diversification.min_data_sources,
              max_same_category_pct: config.diversification.max_same_category_pct,
            },
          }
        : {}),
    },
    labels: {
      horizons: config.horizons,
    },
  };
  // ㊸：只送值≠預設之設定鍵（寫入其 path；與上列三節合併）；v5.58 (v)：該模式不適用之設定不送
  const settings = resolveICSettings(config.ic_settings);
  nonDefaultICSettingKeys(settings)
    .filter((key) => isICSettingApplicable(key, config.mode))
    .forEach((key) => {
      setNested(override as Record<string, unknown>, IC_SETTING_SPECS[key].path, settings[key]);
    });
  return override;
};
