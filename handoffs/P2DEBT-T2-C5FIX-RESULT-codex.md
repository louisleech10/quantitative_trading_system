# p2debt-t2-c5fix result — Codex — 2026-07-12

## 正在做
- C-5 修法已完成；完整 V7 驗收依分工交 grok。

## 寫路徑定位證據
- `test_lightgbm_analyzer.py::test_save_load_format_error_branches` 原直接 open `data_cache/models/lightgbm_bad_payload.pkl`；讀端才經 S10 resolver，造成寫真讀假。
- `ICFilterOrchestrator._persist_outputs` 直接傳 `output_dir="data_cache/reports"` 給 `save_report`/`save_filter_log`；原 S1 manifest 未列此 caller 寫點。
- final5 V7 receipt 的 8 個 Feature Factory tests 全因缺 kline skip，V7 區段未出現 `IC report saved`；無法把三報告歸因至其中某個已執行 V7 body。

## 本次決策 / diff 摘要
- LightGBM bad payload 改寫 `get_active_redirect_root()/models`；S10 resolver接受已在 active models 根的合法路徑。
- S1 新增 `_persist_outputs` installer，以 reporter adapter 重寫硬編 reports/features 路徑；新增 caller-level 正向測試與 S1 subtarget mutation。
- SPEC §SEAM 加 `AMENDED C-5` 與 finding 出處；未改 `momentum/`、`api/`、schema、數值或輸出大小。
- 產出：`tests/fixtures/ic_persist_redirect.py`、`tests/momentum/Analysis/test_ic_persist_redirect_unit.py`、`tests/momentum/Analysis/test_lightgbm_analyzer.py`、`docs/P2DEBT_T2_DCREDIRECT_SPEC.md`、本檔。

## 驗收
- `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py tests/momentum/Analysis/test_lightgbm_analyzer.py::test_save_load_format_error_branches -q` → 43 passed, 5 warnings, rc=0。
- `git diff --check -- <四個變更檔>` → rc=0。
- 四個 C-5 production 洩漏檔逐一 `test -e` → 全 ABSENT。
- `bash scripts/run_ic_persist_hermetic.sh --set V7` → DELEGATED(grok)；期望 133 passed、DIGEST_DIFF_EMPTY[V7]=1。

## 待辦 / 阻塞 / 踩坑提醒
- 待 grok 回填 V7 receipt；目前無實作阻塞。
- active-root 直寫若未同步讓 S10 接受 redirect root，resolver 仍會誤判為 allowed production root 外。
