# IC Phase 1 1-contract TODO Adversarial Review — CODEX

## Verdict：需修補後派工

TODO 已覆蓋 [C-1..C-12] 與 R1-R9 的大部分表面，但尚不可派工。主要問題不是缺標題，而是幾個「看似有測試，實際會假綠」的契約洞：G1 baseline 批次順序錯、`ICResult.eval_status` 會被 dataclass `asdict()` 洩進 v1 JSON、HTTP `schema_version` 沒接到 route、CPCV effective embargo 定義不可執行、tier/RSS 門檻仍是空值。

## Findings

### [BLOCKING][High] G1 baseline 被排到 B5，會在改完程式後才凍結，失去「改前==改後」意義
- 證據：TODO §B 將 `B5 Golden+測試集` 依賴設為 `B1-B4`（`docs/IC_PHASE1_CONTRACT_TODO.md:21-23`）；Task 4.1 又說「凍結前：跑 BTC/1h ... 存 baseline」（line 167）。SPEC §G 明確說 baseline「凍結時機：動工前」（`docs/IC_PHASE1_CONTRACT_SPEC.md:34-36`）。
- 會怎麼失敗：執行端先改 `ICResult`/`get_result`/writer，再於 B5 生成 baseline，G1 deep-equal 只會比較「改後 vs 改後」，R2/R7 的 byte-stability gate 變成假綠。
- 修法：新增 **B0 baseline freeze**，在任何程式碼改動前產生 `tests/golden/ic_phase1_contract/baseline_btc_1h.json`，寫死 `symbol/timeframe/mode/config_hash/生成命令/輸出 sha256`。B1-B4 的 gate 均可引用 B0 baseline；B5 只驗證與補齊測試，不再生成 v1 baseline。

### [BLOCKING][High] Task 2.2 的 `eval_status` 會污染 v1 JSON，且 B1「純 dataclass」與 JSON flag-off 要求互相矛盾
- 證據：TODO Task 2.2 要在 B1 對 `ICResult` 加 `eval_status`（lines 104-112），同時要求「JSON 序列化 flag off 不輸出 eval_status」（line 111），但 B1 被定義為「全是 `contracts.py` 純 dataclass」（line 19）。現有 `IcAnalysisService._to_json_compatible()` 對 dataclass 直接 `asdict(value)`（`api/services/ic_analysis_service.py:1098-1099`），因此新增 dataclass 欄位會自然進 JSON。
- 會怎麼失敗：只改 `contracts.py` 後，任何結果 payload 若包含 `ICResult` dataclass，v1 JSON 都會多 `eval_status`。若 executor 為了修正而改 API serializer，則已超出 B1「純 dataclass」與 Task 2.2 修改檔範圍。
- 修法：把「新增欄位 + v1 序列化排除 + G1 flag-off 測試」放同一批次，或在 B1 明確允許修改 `api/services/ic_analysis_service.py::_to_json_compatible` 並新增覆蓋 dataclass `ICResult` 的 regression test。驗收不可只測 helper；要測真實 `get_result()` v1 payload 不含新鍵。

### [BLOCKING][High] API negotiation 只改 service 簽名，沒有把 `schema_version` 接到 FastAPI route，v2 HTTP 路徑不可達
- 證據：TODO Task 3.2 寫 `get_result(task_id, schema_version=None)`（line 150），但修改檔只粗列 service；現有 route 是 `async def get_result(task_id: str)` 並直接呼叫 `ic_analysis_service.get_result(task_id)`（`api/routes/ic_analysis.py:62-67`），沒有 `Query` 參數。
- 會怎麼失敗：service-level test 可以綠，但 `/api/v1/ic/result/{task_id}?schema_version=2` 仍不會把 query 傳入 service，前端/HTTP caller 永遠拿不到 v2 envelope。
- 修法：Task 3.2 必須明列修改 `api/routes/ic_analysis.py::get_result(task_id, schema_version: Optional[int] = Query(None))`，並新增 route-level 測試：flag on + `?schema_version=2` 回 v2；flag on + 無參仍 v1；flag off + `?schema_version=2` 仍 v1 deep-equal。

### [BLOCKING][High] CPCV strict embargo 偵測定義不足，`effective < requested` 會誤判或漏判 silent relaxation
- 證據：TODO Task 1.4 只說「重算 effective embargo（train 與 test 最近邊界的實際距離）」並比較 requested（lines 75-77）。現有 CPCV 實作是 `purge_start=start-purge_gap`、`purge_end=end+purge_gap+embargo_len`（`momentum/Analysis/model_validation/combinatorial_purged_cv.py:191-195`），且 silent relaxation 僅在 train 空時把 `embargo_pct` 暫時 `/2`（lines 75-80）。
- 會怎麼失敗：若用「train/test 最近距離」當 effective，左側最近距離通常只反映 `purge_gap`，不是 post-test embargo；若把 purge 與 embargo 混在同一距離比較，會 false positive/false negative。小樣本測試可能只證明有 raise，不證明 strict 計算正確。
- 修法：TODO 要寫死演算法：用原始 requested config 重新計算每個 test range 的 expected excluded interval `[start-purge_gap, end+purge_gap+requested_embargo_len)`，assert returned `train_indices` 與 expected train set 完全一致；或至少分別檢查 pre-test purge、post-test purge+embargo，不用單一 nearest-boundary metric。

### [BLOCKING][High] `validate_split_integrity` 對多 symbol 的通過條件太弱，sorted/grouped 不等於 per-symbol split
- 證據：TODO Task 1.3 說「多 symbol 且未 sorted by (symbol,time) 或未 grouped→raise」（lines 61-64），正例只要求 symbol 純度==1.0（line 69）。Manifest [C-3] 要「per-symbol 套用或 fail-closed」，不是僅排序。
- 會怎麼失敗：一個按 `(symbol,time)` 排好但仍把 BTC+ETH 當單一 frame 丟給 CPCV 的 plan 可能通過 sorted/grouped 檢查；CPCV group boundary 仍可能跨 symbol 邊界，或同一 SplitPlan 同時含多 symbol，造成 [C-3] 假綠。
- 修法：對 `SplitPlan` 明確要求 `symbol is not None` 且 `symbols[plan.row_index]` 唯一等於 `plan.symbol`；若 plan 表示多 symbol，必須攜帶 per-symbol child plans 並逐一驗證。G3 要新增「已 sorted/grouped 但未 per-symbol split」反例，必 raise。

### [BLOCKING][High] 使用者橫向要求仍是空殼：tier/RSS/page_size 沒有數值，`tracemalloc` 也量不到 pyarrow native RSS
- 證據：SPEC §V tier 表仍是「8GB 待 TODO 量測寫死 / page_size 小」（`docs/IC_PHASE1_CONTRACT_SPEC.md:130-135`）；TODO Task 3.1 驗證只寫 `tracemalloc peak < 門檻`（line 143），但沒有門檻數值。pyarrow/parquet 大量 memory 在 native allocator，`tracemalloc` 不足以代表 RSS。
- 會怎麼失敗：executor 無法知道 pass/fail 門檻，只能自訂或跳過；8GB tier OOM 風險無法被測試抓到。這直接違反本輪必查第 7 點。
- 修法：在 TODO 寫死 per-tier 數字：artifact write peak RSS、filter read peak RSS、page_size cap、測試資料規模（N rows/features）。驗證改用 `psutil.Process().memory_info().rss` 或既有 hardware tier helper；`tracemalloc` 可輔助但不能作為唯一 gate。

### [MAJOR][High] G1 config_hash 仍留 placeholder，冷啟動 agent 會自行選 baseline
- 證據：Task 4.1 寫 `config_hash` 為 `<TODO: 執行端凍結前用 feature_library 最新 BTC/1h run hash 填入...>`（line 167）。SPEC §G 說 TODO 凍結前要寫死，且「不得實作者自選」（`docs/IC_PHASE1_CONTRACT_SPEC.md:34-36`）。
- 會怎麼失敗：不同 executor/不同時間點的「最新」run 不一致，G1 baseline 不可重現；也可能挑到已受改動影響的 run。
- 修法：TODO adversarial 修補後、派工前，由規劃端填入具體 `config_hash`、生成命令、baseline sha256。若現在無法取得，標 BLOCKED，不把選擇權交給實作者。

### [MAJOR][High] 既有 caller 覆蓋不足；只測 `/result` baseline 不足以證明 flag-off/flag-on 不破 decay/quantile/grouped/export
- 證據：TODO Task 3.2 承認 caller 包含 route `/result/{task_id}`、decay/quantile/correlation/grouped/export（line 153），但驗證只有 `test_flag_off_deep_equal_baseline`、v2 envelope、SSOT、no artifact（line 157）。現有 routes 直接從 `get_result()` 的 v1 dict 取 `ic_decay`/`quantile_returns`/`correlation_matrix`/`grouped_ic`/`metadata`（`api/routes/ic_analysis.py:179-187,215-277,317-326`）。
- 會怎麼失敗：`get_result()` 加 schema/version branch 後 `/result` 測試綠，但 `/summary`、`/decay`、`/quantile`、`/correlation`、`/grouped`、legacy export 在 flag on/off 的預設語義可能變 404、空 dict 或 v2 envelope shape mismatch。
- 修法：Task 3.2 增加 route regression matrix：flag off 全既有 caller golden；flag on + 無 `schema_version` 全既有 caller仍 v1；flag on + `schema_version=2` 僅 `/result` 回 v2，其他 caller 不受 v2 envelope 影響或明確拒絕 v2。

### [MAJOR][Medium] Artifact schema 的 input mapping 不足；現有 `ICResult` 無 `horizon`，TODO 卻要求 long layout `horizon:int`
- 證據：SPEC §A 已確認既有 `ICResult` 無 horizon 維度（`docs/IC_PHASE1_CONTRACT_SPEC.md:18`）；TODO Task 3.1 schema 要 `horizon:int`（line 136），輸入只寫「IC results（含 eval_status/scope_id）」（line 134）。
- 會怎麼失敗：executor 不知道 longitudinal 現有單 horizon、decay horizons、rolling windows、或 future multi-horizon 應如何映射到 artifact rows，可能硬填 `horizon=1` 或從錯欄推導，造成 G2 對錯資料全等。
- 修法：新增 `build_ic_artifact_rows(results, default_horizon: int | None, selection_scope_id: str)` 的明確 mapping；若 Phase 1 只支援單 horizon，寫死 `horizon=1` 的來源與限制，並在 §N 登記 multi-horizon artifact 補完。

### [MINOR][High] Logging 規則會誘導 momentum/core 反向 import api
- 證據：TODO §0 寫「Logging：`from api.core.logging import get_logger`；契約層（momentum/core）不在熱迴圈 log」（line 9），但同 §0 又要求 `momentum/` 不得 `from api.`（line 7）。現有 momentum modules 使用 `momentum.core.logging.get_logger`。
- 會怎麼失敗：冷啟動 executor 可能在 `momentum/core/contracts.py` 或 `momentum/Analysis/ic_split_adapter.py` 引入 `api.core.logging`，直接違反解耦 Rule 1。
- 修法：改成「API 層用 `api.core.logging`；momentum 層用 `momentum.core.logging`；contracts.py 優先不 log」。

### 無問題類別摘要
- 覆蓋追溯：[C-1..C-12]、R1-R9 均有 Task 名義覆蓋；問題在可執行細節與 gate 順序，不是掉 ID。
- WF 無 `split()`：TODO 已在 Task 1.4 明確包 `_generate_rolling_splits` 且不改 WF 內部，方向正確；仍需修正實際檔案路徑/測試路徑到 `momentum/Analysis/model_validation/`。
- 單 symbol gap：Task 1.3 有真實 kline 刪 3 bar 的 fail-closed 測試，方向正確；需補 sorted/grouped-but-not-per-symbol 反例。
- flag-off 不污染 v1：意圖正確，但目前因 B1/B5 順序與 dataclass serializer 問題不可派工。

## 被當成事實的未驗證假設（§0）
- 「B5 生成 baseline 仍能保證改前 byte-stability」：未成立；B5 在 B1-B4 後。
- 「新增 `ICResult.eval_status` 有預設就向後相容」：對建構相容，但對 dataclass JSON 序列化不相容；現有 `_to_json_compatible(asdict)` 會暴露新欄。
- 「`schema_version=2` negotiation 改 service 即可」：未驗證 route 會傳 query；現有 route 不傳。
- 「train/test 最近邊界距離能代表 CPCV effective embargo」：未驗證，且與現有 purge+post-test embargo 實作不等價。
- 「tracemalloc peak 能代表 parquet filter/read 的跨 tier memory」：未驗證；pyarrow native memory/RSS 不被完整覆蓋。

STATUS: DONE
