# native-tf profile analysis — Codex 2026-06-21

Scope: read-only root-cause analysis; no code changes.
Inputs: user timing facts: 167d/1 symbol, primary 12h L6.5=85s with 1h secondary native_rows=4009; primary 1h L6.5=39s with 12h secondary native_rows=335.

Findings:
- Native path currently loads native matrix once (`load_data_native`) then runs full `_transform_single()` on source rows, then expands results with `idx_map`.
- For sharded groups, `load_data_native` mmap-loads each shard and copies into one `(source_n_rows, n_cols)` array; this is I/O + memory copy, but not per-transform repeated.
- Transform cost is row-sensitive because `_transform_single_legacy` applies winsor/fracdiff/ADF/rank/gaussian/zscore over the full native DataFrame.
- Observed 12h-primary case has ~12x more secondary native rows than 1h-primary case (4009 vs 335), but only 2.2x runtime, so fixed costs and other groups dominate; still directionally consistent with native transform row-count cost.
- No evidence from code alone that disk I/O is the primary cause; need instrumentation around `load_data_native`, `_transform_single`, and `apply_idx_map_to_array` to prove shares.

Correctness:
- Native-tf was added to avoid expand-before-transform bias: plateau overweighting, fracdiff d_star bias, and wrong rolling-window time semantics.
- `idx_map` is as-of aligned using source close time <= primary decision time, with -1 before source availability; native transform then forward-fills processed source rows.
- A gate `native_rows <= primary_rows` is performance-plausible but correctness-regressive for fine secondary TF, because fallback returns to transform-after-expansion bias.

Recommendation:
- Do not gate solely on `native_rows > primary_rows` unless accepted as an explicit quality/perf tradeoff.
- First profile per group: timings for native load, idx_map load, `_transform_single`, original/new `apply_idx_map`, sink/write; include n_rows/n_cols/shards/bytes/config path.
- If perf gate is needed, prefer an opt-in policy with reason tags, e.g. only fallback for fine-secondary groups when native transform estimated cost exceeds threshold and L6.5 steps are limited to transforms where expanded semantics are acceptable.
- Safer default: keep native-tf for all compact cross-TF groups; optimize fine-secondary path by shard/chunk streaming or fast-path support before disabling correctness-preserving native computation.

Blocked: none.
