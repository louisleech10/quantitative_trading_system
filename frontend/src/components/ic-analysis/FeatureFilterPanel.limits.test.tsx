import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import FeatureFilterPanel from '@/components/ic-analysis/FeatureFilterPanel';
import { FeatureFilterConfig, FeatureListItem } from '@/lib/types';

// ICPERF SPEC v5.86 Task 0.6 (h) L1b：IC 預過濾「最大因子數」輸入之無數學依據上界 max=500（② 參數上界）。
// L0 機讀表（git 物件 1eeef821）落點寫在 describe 名稱之 [rows:…]（`檔:L0 行:code_sha256 前 12 碼`），
// 由 tests/momentum/Analysis/test_icperf_limit_l1_coverage.py 自 vitest 實際執行之測試名稱取用。
// f1（SPEC (h)）：預設 max_features 未設（顯示 30、實際取全部匹配），舊界 500 只約束使用者明填之值 ⇒
// 越舊界之合法值（501）經「套用預過濾」實際送出 501 個特徵；整數下限 1 保留；預設請求送出之清單不變。
// 計算端消費點：onFilteredFeaturesChange → ic-analysis page setSelectedFeatures → 請求 selected_features
// （api/models/ic_models.py selected_features 無長度上界）。

afterEach(() => {
  cleanup();
});

const N_AVAILABLE = 600;
const available: FeatureListItem[] = Array.from({ length: N_AVAILABLE }, (_, i) => ({
  feature_name: `feat_${String(i).padStart(4, '0')}`,
  category: 'momentum',
  data_source: 'kline',
}));

function renderPanel(filter: FeatureFilterConfig) {
  const onFilterChange = vi.fn();
  const onFilteredFeaturesChange = vi.fn();
  render(
    <FeatureFilterPanel
      availableFeatures={available}
      filter={filter}
      onFilterChange={onFilterChange}
      onFilteredFeaturesChange={onFilteredFeaturesChange}
    />,
  );
  fireEvent.click(screen.getByText('Feature 預過濾'));
  const input = screen.getByPlaceholderText('最大因子數') as HTMLInputElement;
  return { input, onFilterChange, onFilteredFeaturesChange };
}

describe('FeatureFilterPanel L1b max_features [rows:frontend/src/components/ic-analysis/FeatureFilterPanel.tsx:99:343dd1a589c8]', () => {
  it('越舊界之合法值 501 無 max 約束、套用後實際送出 501 個特徵', () => {
    const { input, onFilteredFeaturesChange } = renderPanel({ max_features: 501 });
    expect(input.hasAttribute('max')).toBe(false);
    expect(input.validity.rangeOverflow).toBe(false);
    fireEvent.click(screen.getByText('套用預過濾'));
    expect(onFilteredFeaturesChange).toHaveBeenCalledTimes(1);
    const sent = onFilteredFeaturesChange.mock.calls[0][0] as string[];
    expect(sent).toHaveLength(501);
    expect(sent).toEqual(available.slice(0, 501).map((item) => item.feature_name));
  });

  it('輸入 5000 照原值傳出、不夾回', () => {
    const { input, onFilterChange } = renderPanel({});
    fireEvent.change(input, { target: { value: '5000' } });
    expect(onFilterChange).toHaveBeenLastCalledWith({ max_features: 5000 });
  });

  it('整數下限 1 保留；預設（未設）顯示 30、套用送出全部匹配', () => {
    const { input, onFilteredFeaturesChange } = renderPanel({});
    expect(input.getAttribute('min')).toBe('1');
    expect(input.value).toBe('30');
    fireEvent.click(screen.getByText('套用預過濾'));
    expect((onFilteredFeaturesChange.mock.calls[0][0] as string[]).length).toBe(N_AVAILABLE);
  });
});
