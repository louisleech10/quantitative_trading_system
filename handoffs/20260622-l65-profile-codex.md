# 20260622 L6.5 native-tf profiling (Codex)
Scope: read-only profiling; product code unchanged. Added temp harness `scripts/l65_native_tf_profile.py`; outputs under `/private/tmp/l65_profile_native_tf_run2`.

## Run
- Real data: `data_cache/feature_klines/kline_cache.h5`, BTCUSDT, primary=12h, secondary=1h.
- Config: 3 L1 indicators (EMA21/SMA21/RSI14) + L3 rolling enabled (30 groups/TF), L6.5 winsor only.
- Env: `FFACT_USE_CGSA=1`, `FFACT_L65_NATIVE_TF=1`, `FFACT_MULTI_TF_COMPACT_ALIGNMENT=1`, `FFACT_MULTI_TF_PARALLEL=0`, tmp `FFACT_CGSA_WORK_DIR`.
- Output: 66 total groups; 33 native-tf groups (3 L1 + 30 L3); 186 features; 1h rows=20352, 12h rows=1696.

## Profiling Table
| Scope | groups | wall_sum | load | transform | idx_map | sink | mean wall | p95 wall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| native all | 33 | 5.358s | 0.159s | 5.083s | 0.008s | 0.080s | 0.162s | n/a |
| native L1 | 3 | 0.192s | 0.015s | 0.168s | 0.0007s | 0.006s | 0.064s | 0.067s |
| native L3 | 30 | 5.166s | 0.144s | 4.915s | 0.0076s | 0.075s | 0.172s | 0.189s |

Summary: total wall 11.250s; multi_tf stage seconds: L1-L6=2.608s, alignment=0.005s, L6.5+L7=8.408s.

## CPU/IO Verdict
- CPU-bound: native accounted time = 5.331s; `_transform_single` = 95.35%.
- I/O not main cause: `load_data_native + sink` = 4.49%; idx_map = 0.16%.
- Per-group overhead outside measured stages = 0.027s total / 0.5% of native wall, so not `new FeaturePreprocessor`/idx_map/load overhead.

## 32x Root-Cause Conclusion
- The measured bottleneck is repeated winsor transform CPU inside `_transform_single` per native group.
- The suspected disk load / per-group object / idx_map overhead is falsified for this run.
- 99-group production case should scale mostly with native transform count; expected speedup comes from parallelizing compute, not batching I/O.

## Parallel Plan
- Use `ThreadPoolExecutor` for narrow native-tf compute; parent keeps single ordered sink in deterministic `group_plan` order.
- Narrow gate: `working_peak = native_rows*cols*4*3 + primary_rows*cols*4 + idx_map_bytes`; parallel only if `working_peak <= min(512MiB, rss_budget/(workers+1))` and `cols <= split_threshold/2`.
- Wide/serial: sharded total >1GiB, `cols > split_threshold/2`, slow-path fracdiff/ADF/gaussian non-all, unknown shape, or RSS gate unavailable.
- Worker formula: `cpu_cap=min(max(os.cpu_count()-1,1), 8)`; tier base narrow workers `{8GB:2, 16GB:4, 24GB:6, 32GB:8}`; `effective=min(base, cpu_cap, floor(rss_budget / p95_task_peak))`.
- RSS gate: `rss_budget=tier_gb*0.55-current_rss_gb-reserve_gb`; reserves `{8:2,16:3,24:4,32:5}` GiB; pause submits above soft cap, drain ordered sink queue.
- If future full-prod profiling shows load+sink >=35%, hold parallelism and investigate I/O batching; current evidence does not support that.

## Hermetic Proof
- Before checksum: 8741 files, sha256 `6d04795e15d8f287a7d0b0f0cc1a10c29e6aef71c2e713618a6ffd61b1c89ed6`.
- After checksum: 8741 files, same sha256; `diff -q` empty.
- Generated artifacts only under `/private/tmp/l65_profile_native_tf_run1` and `/private/tmp/l65_profile_native_tf_run2`.
