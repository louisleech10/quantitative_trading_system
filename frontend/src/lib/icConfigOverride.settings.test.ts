/**
 * ICPERF Task 0.4 ㊸（SPEC v5.57）：IC 頁方法選擇與門檻開關之前端側對證。
 *
 * 使用者 2026-09-10：「前後端務必同步，不能再有幽靈狀態」。契約檔 `momentum/Analysis/contracts/ui_stage_toggles.json`
 * 之 `setting_keys` 為單一真相源；後端側（契約 ⇔ ICConfig ⇔ 消費點）由 pytest `test_icperf_ui_toggles.py` 對證。
 *
 * 守四件事：
 * 1. `IC_SETTING_SPECS`／`DEFAULT_IC_SETTINGS` == 契約 `setting_keys`（kind、path、options、default 逐值相同）。
 * 2. 預設（未設定或全為預設值）⇒ `buildConfigOverride` 與改前逐字相同（§G 凍結請求不變）。
 * 3. 每個非預設值 ⇒ 寫到契約 path，且不吃掉同節既有鍵（thresholds 數值、redundancy.correlation_threshold）。
 *    mutation：拿掉送出或寫錯 path ⇒ 本節紅。
 * 4. 七鍵全歸類：store 之 featureToggles 不再含七鍵；契約 merged／disclosed 與前端一致。
 */
import { readFileSync } from 'fs';
import path from 'path';
import { describe, expect, it } from 'vitest';

import {
  buildConfigOverride,
  DEFAULT_IC_SETTINGS,
  IC_SETTING_KEYS,
  IC_SETTING_SPECS,
  nonDefaultICSettingKeys,
  resolveICSettings,
} from '@/lib/icConfigOverride';
import type { ICAnalysisConfig, ICMethodSettings } from '@/lib/types';
import { useICAnalysisStore } from '@/store/icAnalysisStore';

const contract = JSON.parse(
  readFileSync(path.resolve(__dirname, '../../../momentum/Analysis/contracts/ui_stage_toggles.json'), 'utf-8'),
) as {
  ui_only_keys: string[];
  setting_keys: Record<string, { kind: string; path: string[]; options?: string[]; default: string | boolean }>;
  merged_keys: Record<string, string>;
  disclosed_keys: Record<string, string>;
};

const SEVEN = [
  'ic_method_selection',
  'winsorization_method',
  'monotonicity_test',
  'return_type_selection',
  'ic_autocorrelation',
  'redundancy_method_selection',
  'vif_filter',
];

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

/** 改前之 IC 頁初始 config_override（與 `icConfigOverride.diversification.test.ts` 同一份期望值）。 */
const BEFORE = {
  thresholds: { ic_mean_min: 0.02, icir_min: 0.5, p_value_max: 0.05, monotonicity_score_min: 0.6 },
  redundancy: { correlation_threshold: 0.7 },
  labels: { horizons: [1, 2, 3, 5, 8, 13, 21] },
};

const nonDefaultValues = (key: keyof ICMethodSettings): (string | boolean)[] => {
  const spec = IC_SETTING_SPECS[key];
  return spec.kind === 'toggle' ? [!spec.default] : (spec.options ?? []).filter((v) => v !== spec.default);
};

const atPath = (obj: unknown, p: readonly string[]): unknown =>
  p.reduce<unknown>((cur, part) => (cur && typeof cur === 'object' ? (cur as Record<string, unknown>)[part] : undefined), obj);

describe('㊸ 前端設定規格 == 契約', () => {
  it('IC_SETTING_SPECS 之鍵、kind、path、options、default 與契約 setting_keys 逐值相同', () => {
    expect([...IC_SETTING_KEYS].sort()).toEqual(Object.keys(contract.setting_keys).sort());
    for (const key of IC_SETTING_KEYS) {
      const c = contract.setting_keys[key];
      const f = IC_SETTING_SPECS[key];
      expect(f.kind).toBe(c.kind);
      expect([...f.path]).toEqual(c.path);
      expect(f.default).toBe(c.default);
      expect(DEFAULT_IC_SETTINGS[key]).toBe(c.default);
      if (c.kind === 'select') {
        expect([...(f.options ?? [])]).toEqual(c.options);
      } else {
        expect(f.options).toBeUndefined();
      }
    }
  });

  it('七鍵全歸類：ui_only 為空、契約 setting／merged／disclosed 聯集＝七鍵、vif 併入去重選單', () => {
    expect(contract.ui_only_keys).toEqual([]);
    const all = [
      ...Object.keys(contract.setting_keys),
      ...Object.keys(contract.merged_keys),
      ...Object.keys(contract.disclosed_keys),
    ];
    expect([...all].sort()).toEqual([...SEVEN].sort());
    expect(contract.merged_keys.vif_filter).toBe('redundancy_method_selection');
    expect(IC_SETTING_SPECS.redundancy_method_selection.options).toContain('vif');
  });

  it('store 之 featureToggles（三個具名 preset）不再含七鍵（不再是 tier 布林開關）', () => {
    for (const tier of ['foundation', 'intermediate', 'advanced'] as const) {
      useICAnalysisStore.getState().setFeatureTier(tier);
      const keys = Object.keys(useICAnalysisStore.getState().featureToggles);
      expect(keys.filter((k) => SEVEN.includes(k))).toEqual([]);
    }
  });
});

describe('㊸ buildConfigOverride 送出', () => {
  it('未設定 ⇒ 與改前逐字相同', () => {
    expect(buildConfigOverride(base)).toEqual(BEFORE);
  });

  it('全部設為預設值 ⇒ 仍與改前逐字相同（只送非預設）', () => {
    expect(buildConfigOverride({ ...base, ic_settings: { ...DEFAULT_IC_SETTINGS } })).toEqual(BEFORE);
    expect(nonDefaultICSettingKeys(DEFAULT_IC_SETTINGS)).toEqual([]);
  });

  for (const key of IC_SETTING_KEYS) {
    for (const value of nonDefaultValues(key)) {
      it(`${key}=${String(value)} ⇒ 寫到契約 path ${contract.setting_keys[key].path.join('.')}，同節其他鍵保留`, () => {
        const out = buildConfigOverride({ ...base, ic_settings: { [key]: value } as Partial<ICMethodSettings> });
        expect(atPath(out, contract.setting_keys[key].path)).toBe(value);
        expect(out.thresholds).toMatchObject(BEFORE.thresholds);
        expect(out.redundancy).toMatchObject(BEFORE.redundancy);
        expect(out.labels).toMatchObject(BEFORE.labels);
        expect(nonDefaultICSettingKeys({ [key]: value } as Partial<ICMethodSettings>)).toEqual([key]);
      });
    }
  }

  it('多鍵同時非預設 ⇒ 各自寫到其 path', () => {
    const settings: ICMethodSettings = {
      ic_method_selection: 'kendall',
      winsorization_method: 'mad',
      return_type_selection: 'log',
      redundancy_method_selection: 'vif',
      monotonicity_test: false,
    };
    const out = buildConfigOverride({ ...base, ic_settings: settings });
    for (const key of IC_SETTING_KEYS) {
      expect(atPath(out, contract.setting_keys[key].path)).toBe(settings[key]);
    }
    expect(resolveICSettings({ ic_method_selection: 'pearson' }).winsorization_method).toBe('percentile');
  });
});
