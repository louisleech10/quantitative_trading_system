#!/bin/zsh
# TODO 審查 r5 修補：契約加 registry 三個 sink 分支與三個真實 L1 特徵欄（TA-Lib 於真實 kline 上計算）
cd /Users/louis/Desktop/quantitative_trading_system || exit 1
F=tests/_golden/icpostleak/contract.json
T=$(mktemp)
jq '.branches += {
      "registry_sink": {"env": {}, "entry": "transform_registry_groups_to_sink"},
      "registry_sink_sharded": {"env": {"FFACT_CGSA_SHARD_BYTES": "4096"}, "entry": "transform_registry_groups_to_sink"},
      "registry_sink_chunked": {"env": {"FFACT_L65_SPLIT_THRESHOLD": "2"}, "entry": "transform_registry_groups_to_sink"}
    }
    | .kline.l1_features = [
      {"name": "close_trend_EMA_21", "fn": "EMA", "inputs": ["close"], "args": {"timeperiod": 21}},
      {"name": "close_momentum_RSI_14", "fn": "RSI", "inputs": ["close"], "args": {"timeperiod": 14}},
      {"name": "hlc_volatility_ATR_14", "fn": "ATR", "inputs": ["high", "low", "close"], "args": {"timeperiod": 14}}
    ]
    | .kline.l1_features_note = "§G「3 個真實 L1 特徵欄」：以 TA-Lib（生產 L1 同一程式庫）於真實 kline 計算；首段 NaN 為各指標自然暖身（晚生欄）；另保留人工晚生欄 close_late 驗錨點非 0"' $F > $T && mv $T $F
jq -r '.branches | keys | join(",")' $F
jq -r '.kline.l1_features[].name' $F
