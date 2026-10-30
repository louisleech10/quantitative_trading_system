import { describe, expect, it } from 'vitest';
import { buildConfigOverride, DEFAULT_DIVERSIFICATION } from '@/lib/icConfigOverride';
import type { ICAnalysisConfig } from '@/lib/types';

// ICPERF Task 0.4 ㊲：多元化約束之 config_override 組裝（未設定 ⇒ payload 與改前逐字相同；設定 ⇒ 整組四鍵明送）。

const base: ICAnalysisConfig = {
  features_path: '',
  mode: 'global',
  horizons: [1, 2, 3, 5, 8, 13, 21],
  thresholds: {
    ic_mean_min: 0.02,
    icir_min: 0.5,
    p_value_max: 0.05,
    monotonicity_score_min: 0.6,
    correlation_threshold: 0.7,
  },
};

describe('buildConfigOverride diversification', () => {
  it('omits diversification when unset (initial payload unchanged)', () => {
    expect(buildConfigOverride(base)).toEqual({
      thresholds: { ic_mean_min: 0.02, icir_min: 0.5, p_value_max: 0.05, monotonicity_score_min: 0.6 },
      redundancy: { correlation_threshold: 0.7 },
      labels: { horizons: [1, 2, 3, 5, 8, 13, 21] },
    });
  });

  it('sends all four keys including enabled=false explicitly once set', () => {
    const off = buildConfigOverride({ ...base, diversification: { ...DEFAULT_DIVERSIFICATION } });
    expect(off.redundancy).toEqual({
      correlation_threshold: 0.7,
      diversification: { enabled: false, min_categories: 3, min_data_sources: 2, max_same_category_pct: 0.4 },
    });
    const on = buildConfigOverride({
      ...base,
      diversification: { enabled: true, min_categories: 4, min_data_sources: 3, max_same_category_pct: 0.25 },
    });
    expect(on.redundancy.diversification).toEqual({
      enabled: true, min_categories: 4, min_data_sources: 3, max_same_category_pct: 0.25,
    });
  });

  it('display defaults mirror backend schema defaults (enabled off)', () => {
    expect(DEFAULT_DIVERSIFICATION).toEqual({
      enabled: false, min_categories: 3, min_data_sources: 2, max_same_category_pct: 0.4,
    });
  });
});
