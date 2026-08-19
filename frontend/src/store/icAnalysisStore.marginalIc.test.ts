/**
 * GAP-2 Task 5.1 ⑤ — marginal_ic toggle 送出 config：custom／intermediate／advanced 三條路徑（foundation 亦驗）。
 */
import { afterEach, describe, expect, it } from 'vitest';
import { useICAnalysisStore } from '@/store/icAnalysisStore';

afterEach(() => {
  useICAnalysisStore.getState().setFeatureTier('intermediate');
});

function stageOverrides(): Record<string, boolean> {
  const cfg = useICAnalysisStore.getState().getEffectiveConfig() as {
    feature_tiers?: { custom_overrides?: { stage_overrides?: Record<string, boolean> } };
  };
  return cfg.feature_tiers?.custom_overrides?.stage_overrides ?? {};
}

describe('icAnalysisStore marginal_ic toggle', () => {
  it('三 preset 預設 marginal_ic=true 且送出', () => {
    for (const tier of ['foundation', 'intermediate', 'advanced'] as const) {
      useICAnalysisStore.getState().setFeatureTier(tier);
      expect(useICAnalysisStore.getState().featureToggles.marginal_ic).toBe(true);
      expect(stageOverrides().marginal_ic).toBe(true);
    }
  });

  it('具名 preset（intermediate／advanced）分支：toggle 關 ⇒ stage_overrides.marginal_ic=false（不切 custom 亦送出）', () => {
    for (const tier of ['intermediate', 'advanced'] as const) {
      useICAnalysisStore.getState().setFeatureTier(tier);
      // toggleFeature 會切成 custom（既有行為）；此處直接改 toggles 以驗具名 preset 分支
      useICAnalysisStore.setState((s) => ({ featureToggles: { ...s.featureToggles, marginal_ic: false } }));
      expect(useICAnalysisStore.getState().featureTier).toBe(tier);
      expect(stageOverrides().marginal_ic).toBe(false);
      expect(stageOverrides().fdr_correction).toBe(true);
    }
    // toggleFeature 路徑（切 custom）亦送出 false
    useICAnalysisStore.getState().setFeatureTier('intermediate');
    useICAnalysisStore.getState().toggleFeature('marginal_ic');
    expect(useICAnalysisStore.getState().featureTier).toBe('custom');
    expect(stageOverrides().marginal_ic).toBe(false);
  });

  it('custom 路徑：toggle 關 ⇒ stage_overrides.marginal_ic=false；開 ⇒ true', () => {
    useICAnalysisStore.getState().setFeatureTier('custom');
    if (useICAnalysisStore.getState().featureToggles.marginal_ic) {
      useICAnalysisStore.getState().toggleFeature('marginal_ic');
    }
    expect(stageOverrides().marginal_ic).toBe(false);
    useICAnalysisStore.getState().toggleFeature('marginal_ic');
    expect(stageOverrides().marginal_ic).toBe(true);
  });
});
