# 20260619 CGSA Disk Footprint — Codex read-only review
Role: independent architecture reviewer. Scope: docs brief + multi_tf_generator.py / column_group_registry.py / feature_storage.py / feature_factory.py.

## T-A cgsa_work streaming release / peak bound
Verdict: Claude mostly right for pre-L7 peak; refine wording. Current serial/parallel CGSA completes all TF L1-L6 before L6.5/L7 (`multi_tf_generator.py:299-315`, `:592-608`), so L3 failure can happen before any L7 cleanup. Counterexample: once L7 starts, release is incremental, not end-only: raw writer calls `registry.release_storage()` after durable parquet write (`feature_storage.py:1021-1039`); registry unlinks shards/single files (`column_group_registry.py:1034-1068`). L6.5 raw-sink also streams group-by-group and serializes for disk safety (`feature_preprocessor.py:396-407`, `:529-666`).
Can bound peak by consuming earlier? Feasible but not tiny: run L6.5/L7 sink per group or per TF as soon as group is registered, then release. For fast group-independent transforms this is natural; slow fracdiff/ADF/native compact alignment need careful parity because native path may compute on source rows then align (`feature_preprocessor.py:542-550`).
Minimal change: introduce a “registry group sink” interface so `_persist_layer_output_groups` / `_StreamingL3Persister` can optionally enqueue groups to raw-sink immediately; keep final manifest assembly deterministic. Start with L3-only, primary TF only, no parallel workers.
Risk: resume semantics and manifest/parquet atomicity; ordering/schema hash stability; compact-aligned non-primary groups require idx_map before sink; slow L6.5 transforms must prove byte/semantic parity. Priority: P1 after fail-fast guard.

## T-B float16 cgsa temp
Verdict: Useful disk relief but correctness-sensitive. Existing persistence boundary is deliberately float32: `save_data()` casts and records dtype float32 (`column_group_registry.py:744-761`, `:772`, `:785`, `:850`); worker npy copied into parent is normalized to float32 (`column_group_registry.py:36-48`, `multi_tf_generator.py:881`, `:903`, `:908`); L7 raw sink also coerces to float32 before parquet encoding (`feature_storage.py:46-49`, `:875`, `:955`).
Reason seen in code: byte-stability / baseline preservation comments, not quantified numerical need (`column_group_registry.py:744-747`, `:36-40`). L7 final storage already estimates float16 final bytes in raw-stream precheck (`feature_storage.py:2741-2752`), so temp float16 would attack only cgsa_work.
Minimal change: do not blanket float16. Add opt-in temp dtype per layer/category with strict read-upcast to float32 and audit metadata; allow only rank/zscore/gaussian-like bounded transforms first. Exclude raw price/volume, L1/L2 bases used to build later layers, fracdiff/ADF inputs, and any columns with large dynamic range or downstream equality-golden requirements.
Risk: lossy numerical behavior, ADF/IC/rank boundary flips, golden byte churn, dtype schema impact. Needs real-kline A/B: max abs/rel error, IC rank/top-k stability, L7 schema/file-size delta. Priority: P2, not first response to outage.

## T-C cumulative disk precheck / early abort
Verdict: Yes, high priority. Current registry write guard only compares current array/shard against current free space (`column_group_registry.py:1542-1550`); sharding uses target slices but no cumulative budget (`column_group_registry.py:772-815`, `:880-925`). L7 has the stronger model: estimated final + reclaimable npy + max in-flight part + reserve floor (`feature_storage.py:2726-2791`).
Minimal change: add pre-L3/pre-TF cumulative cgsa_work estimator: existing registry bytes + planned layer output bytes (`rows * predicted_cols * dtype_size`) + largest tmp/shard headroom + reserve floor. If unknown columns, fail early with measured partial estimate before L3 persist starts. Error should name symbol/tf/layer, estimated GiB, free GiB, and suggested remediations.
Risk: false abort if estimates overstate due L7 dead-drop or compact alignment; under-estimate if L4-L6 added later. Use conservative but report components. Priority: P0.

## T-D why 28GB used to fit
Verdict: Most likely “same class but smaller effective footprint / config/history,” not proof current 437K float32 fits 28GB. Evidence: current math 437,781 * 20,352 * 4 = ~35.6GB before tmp/parquet headroom. Current code accumulates all groups before L7 (`multi_tf_generator.py:204-220`, `:303-315`). Incremental L7 release exists only after L7 starts, so it cannot explain an L3-mid-write success.
Historical clues: sharded npy + L7 release landed 2026-05-11 (`git blame feature_storage.py:1021-1035`, commit 816b3f8); float32 normalization landed 2026-06-12 (`git blame column_group_registry.py:36-48`, commit 67c4f28). Tier defaults differ: 8/16GB use L3 streaming, 24GB hybrid, 32GB in_memory (`hardware_utils.py:67-86`), affecting RAM/grouping but not total float32 bytes. A prior 28GB run may have fewer rows/cols, fewer TFs, dead-drop/feature config differences, old dtype/path behavior, or more free disk than reported after cleanup.
Minimal investigation: compare old run manifest/layer counts/config_hash/row_count/feature_count/dtype_summary and cgsa_work retained bytes; inspect env (`FFACT_L3_PERSIST_MODE`, shard bytes, TF list). Priority: P1 evidence task, not architectural fix.

## Recommended order
P0 T-C fail-fast cumulative cgsa_work precheck; P1 T-A early sink/release design spike with primary L3 only; P1 T-D manifest/env comparison; P2 T-B opt-in float16 temp only after real-kline numeric signoff.

ASSUMPTIONS_VERIFIED: code paths/line evidence only; no runtime/data_cache mutation.
TESTS_RUN: read-only inspection commands (`sed`, `nl`, `rg`, `git log`, `git blame`); no pytest because no code changes.
FAILURES_SEEN: none.
SCOPE_CHANGES: none; wrote only this handoff.
NUMERIC_OR_SCHEMA_IMPACT: none from this review; T-B would have numeric/schema impact if implemented.
STATUS: DONE
