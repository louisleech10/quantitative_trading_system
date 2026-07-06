# IC Phase1 1a 第二刀首項 — feature_library.load 貼回時間軸（row_index attach） — SPEC

> 來源 PLAN/診斷：HANDOFF.md「★下一站 = IC 1a 第二刀」首項 bug 段　|　日期：2026-07-06　|　對應 TODO：docs/IC_PHASE1_1a_CUT2_ROWINDEX_TODO.md

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大（消費端共用 load 路徑；命中高風險原則）。
- **命中高風險原則**：(a) 資料品質——載入特徵掉失真時間軸→下游收到偽時間；(d) ML/回測正確性——時間軸錯誤使 IC 切分/purge/embargo 校驗誤判，可能誤擋或（更糟）誤放洩漏。
- **RISK-HIT 宣告**（機檢行）：
RISK-HIT: a,d
- 命中 (a)(d) → §G Golden 必填、adversarial review 必跑；使用者裁定走**全三方數據正確性簽核**（Claude+GPT-5.5+Composer 各獨立簽「資料正確」，任一有疑不過）。

## §A 假設與待使用者確認
- **FACT-RECEIPT**（作者 Claude 實跑 2026-07-06，`python` on venv）：
  - `lib.load("BTCUSDT","12h",config_hash="e53e22906c35363757f4cd49d27f973e")` → shape `(1696, 218369)`，`index type: RangeIndex`，`index head: [0,1,2,3,4]`（**位置整數,非時間軸=bug**）。
  - `lib._reader.load_row_index_v2("BTCUSDT","12h","e53e2290…")` → `DatetimeIndex`，len `1696`，head `[2024-01-01 00:00, 2024-01-01 12:00, 2024-01-02 00:00]`（真 12h 時間軸），`len match: True`。
  - `_write_features_h5`（ic_analysis_service.py:1291-1295）：index 非 DatetimeIndex → 寫 `np.arange` 偽 timestamps（1s 間隔）→ `_validate_expected_frequency` 見 `|1s−12h|≫tol` → raise。
- **待確認：無**（root cause 已用實跑 receipt 三段閉合；修法鏡像已簽核 `_attach_cgsa_row_index`）。
- **已確認結果**：2026-07-06 使用者裁定「排入第二刀首項、走全三方數據正確性簽核」（AskUserQuestion 阻塞答覆）。

## §C 約束
- 解耦 7 條：`feature_library.py` 屬 `momentum/`，不得 `from api.` （grep=0 保持）；改動只在 `momentum/FeatureEngineering/feature_library.py`（reader 既有 `load_row_index_v2` 複用，不新增跨界 import）。
- 不弱化 NaN/inf gate；不改輸出特徵值/欄位/列數/大小——**只補 index**。
- 本任務下游消費者：`ic_analysis_service._materialize_features_for_ic`（→`_write_features_h5`）、`load_multi`、以及所有 `load()/load_for_training()` 的 ML/training 呼叫端。attach 對「已用位置 index 但不依賴時間軸」的呼叫端須無害（值不變、僅 index 由 0..N-1 變真時間）。

## §G Golden / Baseline（(a)(d) 必填）
- **feature/kline 條件**：涉 feature load/split→洩漏,用真實已物化 12h run（`data_cache/features/` 下 e53e2290、對照 f754aad4）+ 真實 `timestamps.parquet` sidecar；禁合成 fixture；三方簽核。
- **凍結時機 / reference**：動工前對 `BTCUSDT/12h/e53e2290` 與 `ETH?/12h/f754aad4`（若可）跑 baseline，存 `data_cache/reports/knife2_baseline/`（測試內生成、路徑寫死於測試常數）。
- **baseline 內容**（抓值重排/局部錯位/漂移，非只 aggregate）：改前 `load` 回傳的 **DataFrame 值** → 欄名集合 sha256 + shape + 每欄（抽樣 N 欄）mean/std/nan_ratio + 抽樣 value hash + NaN mask hash；另存 `load_row_index_v2` 的 timestamps int64 陣列 sha256。
- **通過條件（可證偽）**：
  1. **值守恆**：改後 `load` 的 `.to_numpy()` 值 / NaN mask / shape / 欄名 sha256 **與改前 byte-equal**（只 index 變）。任一欄 diff 超 float32 容差 → 列出該欄 + 實際 diff = FAIL。
  2. **時間軸正確**：改後 `load(...).index` 為 `DatetimeIndex`，且其 int64(秒) 與 `timestamps.parquet`/`load_row_index_v2` **byte-equal**；`index.name == "timestamp"`。
  3. **端到端（斷言在失敗邊界)**：追蹤測試 `test_analyze_real_run_split_validation_passes_with_real_axis`(取代原 `..._completes` xfail):`_materialize_features_for_ic`→h5 timestamps **非 arange 偽軸**(首兩點差=43200s)→`_validate_expected_frequency` **不 raise**。
     **為何不斷言 full analyze `completed`**:此 run 218,369 特徵 full analyze 需 >17min,屬與本 bug 正交的效能/實資料遷移 epic 範疇;原 bug 失敗點就是 materialize→split 校驗,在該邊界斷言即完整閉合。三方(Claude+Codex+Composer)確認此 retarget 對本 finding 忠實、未放寬既有斷言(舊 assert 整段移除非降門檻)。full-analyze 完成驗收改由「79 測試換真實資料」epic 承接(慢測 mark)。

## §P Phase 與依賴

### Phase 1 — load 路徑貼回時間軸（依賴：無）
**Task 1.1 — `_load_internal` V2 path attach row_index**
- 目標：V2 reader 成功載入 `features_df` 後、`return` 前,以 `load_row_index_v2` 貼回真時間軸。　檔案：`momentum/FeatureEngineering/feature_library.py::_load_internal`（return 於 line ~164 前）。　既有 caller/影響面：`load`/`load_for_training`/`load_multi` 全部；下游 `_materialize_features_for_ic`。
- 改法（鏡像 `feature_factory_service._attach_cgsa_row_index`）：
  - 於 `if not features_df.empty:` 區塊內，`return features_df` 之前呼叫新 private helper `_attach_row_index(symbol, timeframe, resolved_hash, features_df, for_training, allow_partial_training)`。
  - helper：`ri = self._reader.load_row_index_v2(symbol, timeframe, resolved_hash, artifact_kind="raw")`；`ri is None` → 直接 return（舊 run 無 row_index，向後相容不動 index）；`len(ri) != len(features_df)` → `raise ValueError(f"row_index length mismatch ...")`；否則 `features_df.index = ri; features_df.index.name = "timestamp"`。
  - **不改**值、欄位、列數、輸出檔。
- 驗證（可證偽）：Golden §G 三條件；`pytest tests/momentum/test_feature_library*.py -k row_index`（新測試）；`pytest tests/api/test_ic_analysis_service.py -k analyze_real_run`（xfail→xpass）。
- 邊界（≥2）：① 舊 run 無 `row_index`（manifest 無鍵）→ helper no-op，index 維持 RangeIndex，`load` 不 raise。② `len(ri) != len(df)`（人為截斷 sidecar）→ `raise ValueError`，不靜默貼錯位時間。③ 空 DF（`features_df.empty`）→ 早已在既有分支外,不進 attach。
- 不可做：不改 HDF5 fallback 路徑（line 180+ 另有 index 語意）；不擴寫 reader；不動 `_write_features_h5`；不改任何特徵值。

## §V 驗證策略與邊界測試目錄
- **mutation 設計**：還原 attach（把 `features_df.index = ri` 註掉/改回 no-op）→ ①§G「時間軸正確」測試須 FAIL ②`test_analyze_real_run...` xfail(strict) 維持 xfail（不 xpass）。長度守衛 mutation：移除 `len` 檢查 + 餵短 sidecar → 邊界②測試須 FAIL。引 `docs/TEST_DESIGN_CHARTER.md`。
- 測試層級：單元（helper attach/no-op/length-guard，`tests/momentum/`，不需 run_api.py）+ 整合 Golden 值守恆（真 12h run）+ 端到端 IC（`tests/api/`）。
- **防假綠**：diff 既有 `test_analyze_real_run...` 斷言不放寬；xfail(strict) 移除即代表 xpass 真發生;新測試斷言對應「index 由 RangeIndex→DatetimeIndex 且值不變」。
- **邊界目錄**（打勾）：☑ 空DF ☑ 重複/亂序 timestamp（sidecar 已 strictly-increasing，attach 不重排，交由既有 split validator）☑ 長度不符（sidecar 截斷）☐ Inf/std=0（不涉，值不變）。

## §R 回退
- 單一 commit，可單獨 revert（僅 feature_library.py + 測試）。無 feature flag（正確性修復,不藏預設關閉——見 memory「驗過就別預設關閉」）；Golden FAIL → 不 merge。

## §N N/A 登記
- **1d 頻率地圖缺口**：`EXPECTED_FREQ_BY_TIMEFRAME` 僅 1h/4h/12h、缺 1d — **本刀不修**（HANDOFF 已列;無真實 1d 已物化 run 可驗，盲加 = 未實測假設,違「實測>假設」）→ 登記為相鄰 deferred，另 Task/另 run 補。
- **P2 features_path vs config_hash 一致性校驗**（run_selector 重凍殘留）：與本 index-attach 無關,維持另立不動。
