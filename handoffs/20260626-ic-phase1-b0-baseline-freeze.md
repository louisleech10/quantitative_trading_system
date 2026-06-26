# IC Phase 1 B0 Baseline Freeze

## 正在做
- B0 已完成：v1 longitudinal golden baseline 已凍結於 `tests/golden/ic_phase1_contract/baseline_btc_1h.json`。

## 待辦
- B1 可接續；G1 後續重跑需照 `baseline_meta.json` 的 materialized input + request config。

## 阻塞
- none

## 本次決策
- reference run：BTCUSDT / 1h / longitudinal / config_hash `a384e6d22ca15fc639757cb3162e7cb3`。
- 全量 90857 x 20352 本機 materialize 過慢且高風險，baseline 使用確定性子集：`sorted(feature_names)[:50]`。
- 仍透過 `ICAnalysisService.start_analysis()` + `get_result(task_id)` 取得 v1 dict。
- baseline sha256：`25aee97f97797af60c60cb16ff4709ecf93017d54dadb5461668f6434991522f`。

## 踩坑提醒
- 第一次全量嘗試卡在 `data_cache/reports/ic_ingest_cache/...h5` dataset write；中斷後補齊該 HDF5 的 `timestamps`/`feature_names` 與 companion meta，避免壞 cache 殘留。
- baseline v1 payload 含現有 `generated_at` 動態欄位；若 G1 要重跑 deep-equal，需明確處理這個既有欄位。
- 驗證：`pytest tests/golden/ic_phase1_contract/test_baseline_frozen.py` PASS。
