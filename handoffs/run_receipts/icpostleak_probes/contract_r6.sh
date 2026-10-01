#!/bin/zsh
# TODO 審查 r6 修補：sharded 改以 monkeypatch 分片大小（繞過 32 MiB 下限）＋spy；chunked 移出逐組合分支，改 append 專屬測試
cd /Users/louis/Desktop/quantitative_trading_system || exit 1
F=tests/_golden/icpostleak/contract.json
T=$(mktemp)
jq 'del(.branches.registry_sink_chunked)
    | .branches.registry_sink_sharded = {"env": {}, "entry": "transform_registry_groups_to_sink",
        "patch_shard_bytes": 4096, "spy": "_stream_sharded_group_to_sink"}
    | .branches.registry_sink.spy = "_transform_single_group_to_arrays"
    | .registry_chunked_append = {"env": {"FFACT_L65_SPLIT_THRESHOLD": "2"}, "mode": "append", "steps": ["zscore"],
        "spy": "_stream_single_group_chunked_to_sink",
        "note": "chunked 僅於 requires_slow（append 模式或 ADF／fracdiff）時觸發；每塊呼叫 _transform_single（legacy，append 停用 optimized）"}' $F > $T && mv $T $F
jq -c '.branches | to_entries | map({(.key): (.value.spy // "")}) | add' $F
jq -c '.registry_chunked_append | {mode, steps, spy}' $F
