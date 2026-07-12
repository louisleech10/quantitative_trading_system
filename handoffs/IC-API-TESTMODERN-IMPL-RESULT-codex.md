# IC API Test Modernization Phase 1 — Codex result
Task-id: icatm-impl-codex | Date: 2026-07-12 | Status: BLOCKED

## 正在做
- 新增真 ETHUSDT/12h builder、三個 API 測試檔接線、兩個 PIT mutation 測試。
- R2-7 採 API serialization stub；task 使用 deepcopy 並於測後 restore。

## 阻塞
- 同一 failure 已達 debug 2 輪上限：mid[200:712] feature finite assertion 失敗。
- 輪 1 假設：volume_zscore_20 的 rolling std=0；改動：新增 builder/PIT/接線後首跑。
- 輪 1 命令：`venv/bin/pytest tests/momentum/Analysis/test_ic_api_real_kline_pit.py::{兩個 nodeid} -q`。
- 輪 1 摘要：feature shift mutation PASS；backward label FAIL，先撞 feature finite assert。
- 輪 2 假設：移除 volume_zscore_20 可消除非 finite；改 `tests/fixtures/ic_api_real_kline.py`。
- 輪 2 同命令；摘要仍為 1 passed/1 failed，同一 finite assertion。
- 需委員會決定第三輪診斷/公式調整；API nodeid 未執行。

## 本次決策
- 未動 `momentum/`、`api/` 生產碼；未動 `data_cache/`。
- 刪除 nodeid：test_feature_list（對照 list_available_features_success 的 total+membership）；
  test_full_analysis（對照 test_full_analysis_endpoint 的 POST/task/result summary）；
  test_deep_analysis_result（對照 start_and_get_result 的 results+summary）。

## 產出
- `tests/fixtures/ic_api_real_kline.py`
- `tests/momentum/Analysis/test_ic_api_real_kline_pit.py`
- `tests/api/test_ic_analysis_api.py`; `test_ic_deep_analysis.py`; `test_export_api.py`

## 踩坑提醒
- 直接遞迴掃 HDF5 在 60 秒內終止，schema 探查標 DELEGATED；指定 reader 在 pytest 0.009s 讀 1696 列。
- 系統 Python py_compile 因 workspace 外 pyc 權限失敗；改用 venv + `/tmp` pycache 後編譯通過。

## icatm-impl-fix closure (append 2026-07-12)
- Root fix: `MAX_FEATURE_LOOKBACK=21`; `calculation_start=MID_START-MAX_FEATURE_LOOKBACK`; finite 守衛與 `mid[200:712]` 保留。
- 同步修正 test fixture 真 timestamp index/HDF5 epoch-second serialization、`AlignmentSpec` 必填欄位，以及 `TestClient` background-task lifecycle。
- PIT receipt: `venv/bin/pytest tests/momentum/Analysis/test_ic_api_real_kline_pit.py -v --tb=short` → 2 passed；兩 mutation 均被 self-test 拒絕。
- API receipt: `venv/bin/pytest tests/api/test_ic_analysis_api.py tests/api/test_ic_deep_analysis.py tests/api/test_export_api.py -v --tb=short` → 29 passed in 6.78s。
- Analyze receipt: 同上 `test_ic_task_status` 等 analyze-backed nodeids PASS；log 有 `IC analysis task completed`。
- Full receipts: 同上 `test_full_analysis_endpoint`、`test_full_analysis_with_deep_analysis_config` 各 PASS。
- IC input grep: `rg -n "rng\\.normal|np\\.arange" <5 scope files>` → exit 1 / 0 matches。
- Production diff: `git diff -- momentum/ api/` → empty。
- 去重: `test_feature_list`→較強 list success；`test_full_analysis`→endpoint；`test_deep_analysis_result`→start-and-get-result。
- R2-7: serialization stub 保留但 deepcopy/restore；filtered artifact 取真 feature 值。
- NUMERIC_OR_SCHEMA_IMPACT: production none；test HDF5 timestamp 修為真 epoch 秒，512 rows/schema 不變。
- STATUS: DONE
