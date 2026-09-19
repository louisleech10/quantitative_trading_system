import type { ICAnalysisConfig } from './types';

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
 */
export const buildConfigOverride = (config: ICAnalysisConfig) => {
  const thresholds: Record<string, number> = {
    ic_mean_min: config.thresholds.ic_mean_min,
    icir_min: config.thresholds.icir_min,
    p_value_max: config.thresholds.p_value_max,
  };

  if (typeof config.thresholds.monotonicity_score_min === 'number') {
    thresholds.monotonicity_score_min = config.thresholds.monotonicity_score_min;
  }

  return {
    thresholds,
    redundancy: {
      correlation_threshold: config.thresholds.correlation_threshold,
    },
    labels: {
      horizons: config.horizons,
    },
  };
};
