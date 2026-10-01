#!/bin/zsh
# TODO 審查 r5 修補：manifest 之 risk_mitigation／coverage_risk 同步（服務模組層 helper、registry 三 sink 分支、Polars 轉換、append 全陣列）
cd /Users/louis/Desktop/quantitative_trading_system || exit 1
F=docs/manifests/ICPOSTLEAK.json
T=$(mktemp)
jq '.batch_card.risk_mitigation += [
      "ic_analysis_service.py ← Task 2.1：zscore 窗正規化與保序去重須為模組層函式 _normalize_zscore_windows(windows)、_dedupe_preserve_order(names)，_apply_transforms_sync 經模組屬性呼叫（test_mutation_unsorted_zscore_windows_is_caught／test_mutation_dedup_removed_is_caught 依此 monkeypatch）",
      "feature_preprocessor.py ← Task 1.1 registry 分支含 transform_registry_groups（in-place）與 transform_registry_groups_to_sink 之三路（_transform_single_group_to_arrays、_stream_sharded_group_to_sink、_stream_single_group_chunked_to_sink），契約 branches 以 FFACT_CGSA_SHARD_BYTES／FFACT_L65_SPLIT_THRESHOLD 切換"
    ]
    | .batch_card.coverage_risk += [
      "r5 修補：Polars oracle 經 pandas_to_polars（float32＋NaN→null，同生產入口）；append 驗收改全陣列 oracle（_rolling_zscore_2d append＋各窗輸入錨點遮罩）；§G 輸入加 3 個真實 L1 特徵欄（TA-Lib EMA21／RSI14／ATR14 於真實 kline）；收集 89＋31 項"
    ]' $F > $T && mv $T $F
bash scripts/template_check.sh todofmt $F | tail -1
