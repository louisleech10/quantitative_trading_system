# Handoff
**Agent**: Cursor | **Time**: 2026-06-03 | **Branch**: main

## 正在做
- **dq nan_ratio + stats_warmup 還原完成**（`feature_factory_service.py` 被誤還原後補回）。

## 本次決策
- dq report `_assemble_data_quality_report` 自 `nan_ratios` 寫 `nan_ratio_mean/max`；schema `dq_v4`→`dq_v5` 失效舊 disk cache。
- `browse_summary` 回傳 `stats_warmup{computed,total,pct,complete}`（`_get_stats_warmup_progress`）。
- catalog cache load：`fast` 無 `nan_ratios` 時跳過 backfill（修 roundtrip test）。

## 待辦
- Claude 驗收 diff + 實機：舊 dq_v4 批次 NaN均/峰非 0；Feature Table 暖機進度條。
- Batch Discovery 實機驗收（若尚未做）。

## 阻塞
- 無。

## 驗證摘要
- PASS: `pytest tests/api/ -q -k "quality or batch or browse or dq"`（124 passed）
- PASS: `./scripts/check_decoupling_phase4.sh`
- PASS: `npm run build`
- 詳細：`handoffs/20260603-dq-nanratio-stats-warmup-restore.md`

## 踩坑提醒
- unit test `_build_service_for_unit` 須有 `_lock`+`_coalesce_browse` 才能測 `browse_summary`。
- `test_feature_export` mock 須收 `compute_adf` kw（route 已有，與本次無關）。
