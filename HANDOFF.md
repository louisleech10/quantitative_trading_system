# Handoff
**Agent**: Codex | **Time**: 2026-06-02 | **Branch**: main

## 正在做
- Multi-symbol fix **Phase 4（C3 IC-First 清理）已完成**；建於 Phase 1-3 工作樹上。

## 本次決策
- P4-1 golden 使用本批指令指定的最小可重現 config：BTCUSDT 1h、IC-First on、L1 trend EMA(21)、L2-6.5 最小集合。
- golden 只寫 `tests/fixtures/golden/multi_symbol_c3/`；計算時 `persist=False`、`FFACT_USE_CGSA=0`、registry 指到 temp，避免寫 data_cache 作 golden。
- P4-2 batch compute 統一走 `_compute_single`；IC-First 由 `config_override.preprocessing.ic_first_pipeline` 路由。
- `_resolve_concurrent_symbols(config_override)` 在 config IC-First 時 force `concurrent_symbols=1`；不再靠 `FFACT_MULTI_SYMBOL_IC_FIRST` 選 compute function。
- `create_feature_factory_for_ic_batch` 已移除（無 caller）。

## 待辦
- Claude 驗收 diff 時注意工作樹含 Phase 1-3 既有變更，本批新增/修改重點：golden script+fixture、batch service P4-2、factory cleanup、multi-symbol IC-first tests。

## 阻塞
- 無。

## 驗證摘要
- PASS: `python scripts/golden_multi_symbol_c3.py freeze` 產 `baseline.parquet` + `env_snapshot.json`，ETH/BTC/DOGE 1h smoke 讀真實 kline。
- PASS: `python scripts/golden_multi_symbol_c3.py compare`（P4-2 改後 == P4-1 baseline）。
- PASS: `python -m pytest tests/feature_engineering/test_multi_symbol_ic_first.py tests/api/test_feature_factory_batch_resume.py -q`（36 passed, 1 warning）。
- PASS: `grep -rn _compute_single_ic_first momentum api` → 0；`grep -r "from api\." momentum/` → 0。

## 踩坑提醒
- `persist=False` 仍會更新預設 `FeatureRegistry`，golden 腳本已把 `_registry` 指到 temp；後續改腳本勿移除。
- `pyarrow` compare 會印 macOS sandbox `sysctlbyname` IOError，但命令 exit 0 且 PASS。
