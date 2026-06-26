# IC Phase 1 B3 Leakage + Adapter Handoff

## 正在做
- B3 已實作：`validate_split_integrity` / `split_per_symbol` / `ICSplitAdapter` / `create_ic_split_adapter`。

## 待辦
- Claude 接回後做三方 split/leakage 正確性簽核與 Composer code review。

## 阻塞
- none。

## 本次決策
- 真實 kline 測試用 `h5py` 讀 `data_cache/feature_klines/kline_cache.h5`，避開本機 PyTables/HDF5 dylib 失效。
- gap 連續性檢查套在 base symbol timeline；selected train rows 仍檢查嚴格遞增，避免 CPCV train subset 因合法 test/purge 洞被誤殺。
- CPCV strict embargo 用 requested config 重算 expected train set，returned train 不完全相等即 raise `EmbargoRelaxedError`。

## 踩坑提醒
- `pandas.HDFStore` 目前會因 `libhdf5.310.dylib` 缺失失敗。
- CPCV 小樣本 relaxation 可用 BTCUSDT 1h 60 rows + `n_groups=3,n_test_groups=2,purge_gap=15,embargo_pct=0.1` 穩定觸發。

## 驗證
- `pytest tests/momentum/core/test_split_contract.py tests/momentum/Analysis/test_ic_split_adapter.py -q` → 13 passed。
- `grep -rE 'from api\.' momentum/ | wc -l` → 0。
