/**
 * 票 TIERTOGGLE（使用者 2026-09-10：「前後端務必同步，不能再有幽靈狀態」）。
 *
 * 守三件事：
 * 1. 前端送出的鍵集 == 契約檔（＝後端兩張表；後端側由 pytest 同檔對證）。
 * 2. **具名 preset 也送出全部 stage 開關**（舊版只送 2 鍵 ⇒ 基礎 preset 關不掉 IC Decay／Grouped IC）。
 * 3. UI 開關表裡的每個鍵，都能被歸到 stage／module／ui_only 三類之一——新增鍵而未歸類即紅（防新幽靈）。
 */
import { readFileSync } from 'fs';
import path from 'path';
import { describe, expect, it } from 'vitest';

import { MODULE_TOGGLE_KEYS, STAGE_TOGGLE_KEYS, useICAnalysisStore } from './icAnalysisStore';

const contract = JSON.parse(
  readFileSync(
    path.resolve(__dirname, '../../../momentum/Analysis/contracts/ui_stage_toggles.json'),
    'utf-8',
  ),
) as {
  stage_keys: string[];
  module_keys: string[];
  locked_stage_keys: string[];
  ui_only_keys: string[];
};

const sorted = (xs: readonly string[]) => [...xs].sort();

describe('TIERTOGGLE 前後端開關同步', () => {
  it('前端鍵集 == 契約鍵集', () => {
    expect(sorted(STAGE_TOGGLE_KEYS)).toEqual(sorted(contract.stage_keys));
    expect(sorted(MODULE_TOGGLE_KEYS)).toEqual(sorted(contract.module_keys));
  });

  it('UI 開關表每個鍵都已歸類（stage／module／ui_only），無未歸類幽靈', () => {
    // 四類：stage（可改）／module（可改）／locked（UI 可見但後端一律忽略，如 ic_calculation）／ui_only（後端無對應旗標）
    const known = new Set([
      ...contract.stage_keys,
      ...contract.module_keys,
      ...contract.locked_stage_keys,
      ...contract.ui_only_keys,
    ]);
    const store = useICAnalysisStore.getState();
    store.setFeatureTier('foundation');
    const uiKeys = Object.keys(useICAnalysisStore.getState().featureToggles);
    const unclassified = uiKeys.filter((k) => !known.has(k));
    expect(unclassified).toEqual([]);
  });

  it.each(['foundation', 'intermediate', 'advanced'] as const)(
    '具名 preset %s 送出全部 stage 開關（且值＝該 preset 的表）',
    (tier) => {
      const store = useICAnalysisStore.getState();
      store.setFeatureTier(tier);
      const cfg = useICAnalysisStore.getState().getEffectiveConfig();
      const sent = cfg.feature_tiers?.custom_overrides?.stage_overrides ?? {};
      expect(sorted(Object.keys(sent))).toEqual(sorted(contract.stage_keys));
      const toggles = useICAnalysisStore.getState().featureToggles as Record<string, boolean>;
      for (const key of contract.stage_keys) {
        expect(sent[key]).toBe(Boolean(toggles[key]));
      }
    },
  );

  it('基礎 preset 必須把 ic_decay／grouped_ic 送成 false（幽靈開關回歸）', () => {
    useICAnalysisStore.getState().setFeatureTier('foundation');
    const sent =
      useICAnalysisStore.getState().getEffectiveConfig().feature_tiers?.custom_overrides
        ?.stage_overrides ?? {};
    expect(sent.ic_decay).toBe(false);
    expect(sent.grouped_ic).toBe(false);
  });

  it('custom preset 仍同時送 stage 與 module 開關', () => {
    useICAnalysisStore.getState().setFeatureTier('custom');
    const overrides =
      useICAnalysisStore.getState().getEffectiveConfig().feature_tiers?.custom_overrides ?? {};
    expect(sorted(Object.keys(overrides.stage_overrides ?? {}))).toEqual(sorted(contract.stage_keys));
    expect(sorted(Object.keys(overrides.module_overrides ?? {}))).toEqual(sorted(contract.module_keys));
  });
});
