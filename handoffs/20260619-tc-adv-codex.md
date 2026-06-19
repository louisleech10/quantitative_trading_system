# T-C adversarial review — Codex — 2026-06-19

SPEC: `docs/CGSA_L3_DISK_PRECHECK_SPEC.md`
TODO: `docs/CGSA_L3_DISK_PRECHECK_TODO.md`

## Verdict
需修補後派工。

## Findings
1. BLOCKING High — L3 precheck compares wrong quantity to current free space.
   Evidence: SPEC line 35/TODO line 33 define `needed = registry_occupied_bytes + planned + max_shard_bytes×2 + reserve_floor`; current `free = disk_usage().free` already excludes existing registry files. Adding registry_occupied again turns "future incremental bytes" into "total footprint", causing false abort on long runs.
   Fix: compare `free` against incremental requirement only: `planned_remaining_bytes + max_inflight_tmp_bytes + reserve_floor`, or explicitly compute filesystem capacity/budget if total footprint is intended.

2. MAJOR High — `reserve_floor` value/source is undefined and can become arbitrary.
   Evidence: SPEC line 35 says "沿用 L7 既有常數風格"; L7 uses `_resolve_l7_min_free_bytes()` and env-tuned safety/floor (feature_storage.py:2770-2774), but no T-C env/default is specified.
   Fix: specify exact default, env name, min/max, and tests. Prefer conservative but small floor for L3 or use same resolved L7 min-free helper only if dependency is acceptable.

3. MAJOR High — planned shard/temp model underspecified for layer chunking.
   Evidence: `_persist_layer_output_groups` splits layers into 5000-col groups (feature_factory.py:1159-1200), then registry may shard each group (column_group_registry.py:772-827). SPEC/TODO say `max_shard_bytes×2` but not whether max covers planned chunks/shards or existing groups.
   Fix: define planned chunks exactly: simulate `range(0,n_cols,chunk_cols)` plus `_compute_shard_slices`, sum final planned bytes once, and max temp as largest planned shard/file, not largest existing group.

4. MAJOR Medium — "persist 前 abort" only covers serial multi-TF path.
   Evidence: SPEC points to multi_tf_generator.py:204-212; parallel path also persists primary L3-L6 at lines 432-441 and worker registration later. Single-TF path persists in feature_factory.py:2949-2966.
   Fix: either scope T-C explicitly to serial multi-TF only, or add TODO tasks/tests for parallel primary, worker-registered groups, and single-TF CGSA persist.

5. MAJOR Medium — compact non-primary false-abort guard is stated but not operational before L3 persist.
   Evidence: compact marking happens after persist (`_mark_existing_groups_compact_aligned`, multi_tf_generator.py:790-833); before L3 persist the DataFrame is source rows. The spec says "compact 非 primary 用 source_n_rows", but does not tell implementer how to distinguish planned physical rows from logical rows.
   Fix: precheck planned bytes from the actual DataFrame shape before compact marking; existing registry occupancy must use `ColumnGroup.total_shard_bytes`, which is physical bytes and compact-safe.

6. MINOR High — "估不到 cols" degradation only covers empty DataFrame.
   Evidence: TODO line 35 says empty -> return None; no behavior for non-DataFrame, missing `.columns`, object dtype, or failed coercion.
   Fix: define fallback: if shape/cols cannot be read, log/return and rely on existing per-shard guard; do not raise unless free is definitely insufficient.

## Positive Checks
- Pure guard/no numeric mutation is adequately specified: SPEC lines 23, 27, 52; TODO lines 16, 49, 54.
- Env disable back to old behavior is specified: SPEC lines 44, 57; TODO lines 46, 50.

STATUS: DONE
