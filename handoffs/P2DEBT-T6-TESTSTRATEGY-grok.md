# P2DEBT-T6 TESTSTRATEGY — Grok 獨立建議
Task-id: t6-strat-grok | Date: 2026-07-12 | 唯讀 | 禁改碼

## 一句話結論
採 **C（分層）= 精化後的 B**，並 **把「真 kline 共用 fixture + 去重」從票 6 拆成獨立 test-modernization epic**；票 6 勿再用合成噪音逐層補洞。

## 證據基線（本輪實讀）
- 主席檔：`handoffs/P2DEBT-T6-TESTSTRATEGY-CHAIR.md`；impl 卡點：`P2DEBT-T6-IMPL-RESULT-codex.md`（rename `return_5` 後 23 全卡 `cadence mismatch: expected 12h, got 0 days 00:00:01`）。
- 三 fixture 同源病：`rng.normal` 特徵/標籤 + `np.arange` 1 秒 timestamp + meta `timeframe=12h` + 舊欄名 `label`（export 180×8 / api 120×6 / deep 140×8）。
- 生產護欄（會連撞）：`return_(\d+)` resolver；`contracts.validate_alignment` cadence（freq 來自 meta）+ **尾端連續 NaN 數必須 == lag** + coverage；IC1A 先例已證「只改欄名→下一層 cadence 紅」（`IC1A-ALIGN-FIXTUREMIG-RESULT.md`）。
- 真資料：`data_cache/feature_klines/kline_cache.h5` 存在；`ETHUSDT/12h` shape 1696，timestamp 為 epoch **秒**、間隔 12h；manifest 已凍 sha256（`tests/fixtures/DATA_MANIFEST.json`）。
- 參照：phase6 用 kline 切片但路徑是舊 `data_cache/kline_cache.h5`（**勿照抄路徑**）；`test_ic_1eb_b4_fullstack` 明示 `return_5` + `label_vals[-5:]=nan`；IC1A 對 momentum 測試採「契約合法合成」（12h cadence + tail NaN），**未**改真值——API 層若要守「禁合成」鐵律，應比 IC1A 更嚴。

---

## (1) A / B / C / 第四選項

| 選項 | 判定 | 理由 |
|------|------|------|
| **A 全刪** | 否 | 匯出 content-type、task 生命週期、numpy 序列化、422/404 有真實回歸價值；刪=覆蓋真空。 |
| **B 共用 fixture 改真 kline** | 方向對、粒度粗 | 三 fixture 一改 23 受益；但 404/422/config 測不需資料；且「真 kline」必須是 **衍生 features+labels**，不是裸 OHLCV 塞進 features.h5。 |
| **C 分類處理** | **採納（主建議）** | B 的正確實作：依測試意圖分層，見下。 |
| **D 兩段式（第四選項）** | 採納為排程 | 票 6 只負責「停損+基線/scope 裁決」；真 kline builder+去重+鐵律閉合走 epic。**禁止**在票 6 內用「再 patch 一層合成（改 arange×43200 + 人工 tail NaN + 仍 rng.normal）」當終態——那是 IC1A 式權宜，能綠但**仍違反**主席/鐵律對本 23 測的定位，且 CE-1（錯 N 仍結構綠）未解。 |

### C 分層表（必遵）

| 層 | 測例類型 | 資料策略 |
|----|----------|----------|
| **L0 純契約** | 404/422/缺欄驗證、`test_ic_config_update` | **無 fixture、無合成、無 kline**；保留。 |
| **L1 API 表面** | status/result/summary/export 格式/grouped/refilter/top_features… | **一個** session-scope「真 kline 衍生 + 已 completed 的 analyze task」共用（export/ic_analysis/deep 的 `export_task`/`ic_analysis_task`/`completed_ic_task` 同源 builder）。斷言維持 HTTP/schema；**不得**宣稱 IC 數值正確。 |
| **L2 真管線** | `full_analysis*`、需真 orchestrator 的 deep 生命週期 | 同 L1 資料源；日後可加 falsifiable 斷言（欄名 `return_5`、tail NaN==5、caplog effective_horizon）；數值 oracle 另票。 |

---

## (2) 真 kline fixture 切片建議

| 參數 | 建議 | 理由 |
|------|------|------|
| **路徑** | `data_cache/feature_klines/kline_cache.h5` | 鐵律與 `DATA_MANIFEST` 權威路徑；勿用 phase6 的 `data_cache/kline_cache.h5`。 |
| **symbol** | `ETHUSDT` | 既有測試/原子指標慣用；manifest 有 12h 指紋。 |
| **TF** | **`12h`** | 三檔 meta 已寫 `12h`；比 1h 同曆時更短、更快；cadence 與 `_cadence_report` 對齊。 |
| **列數** | **256–384 bars**（下限 ≥ 約 128 有效 label 列） | 現 fixture 120–180；horizon=5 吃尾；IC/IR 統計要足夠；12h×384 ≈ 半年、載入可忽略。全量 1696 可跑但無必要。 |
| **切片位置** | **尾端連續窗**（`data[-N:]`） | 最近段通常連續；避開任意 mid-slice 撞 gap 機率（若 gap_rate 觸發後續 gate 再退 mid 連續段）。 |
| **timestamps** | **直接用 kline 的 epoch 秒** | 禁止 `np.arange`；禁止毫秒。 |
| **features** | 由 close **PIT 向量化**衍生 4–8 欄（例：`logret_1`、`logret_5`、`rvol_20`、`zscore_20`、`range_pct`…）一律 `shift` 不看未來 | 禁 `rng.normal`；禁把 open/high 當「特徵」卻標假名。warmup 前段 NaN 可 drop 或與 label 對齊後再寫 h5。 |
| **labels** | `return_5` = 前瞻報酬（simple 或 log，**全專案釘一種並寫進 builder docstring**）；**最後 5 列強制 NaN** | 對齊 `default_horizon=5` + `validate_alignment` tail==lag；與 1eb_b4 契約一致。 |
| **meta** | `symbol=ETHUSDT`, `timeframe=12h`, feature 元資料真實 category 可簡 | 必須與 timestamp cadence 一致。 |
| **門檻** | 沿用現有 lenient `config_override`（ic_mean_min=-1…） | L1 目標是 task completed，不是過嚴格 IC 篩選。 |
| **速度** | session（或 module）scope **建檔 1 次 + analyze 1 次**；三檔共享 helper 於 `tests/fixtures/` 或 `tests/api/conftest` | 避免每 test 重跑 orchestrator；深析 export 可再 inject 最小 deep stub（現 `export_task` 已有，保留）。 |
| **可選護欄** | fixture setup 讀 manifest 指紋或 `min_row_count`；`assert label_names==["return_5"]`；可選 assert tail NaN==5 | 閉 CE-1 的「誤改 return_1」+ 結構 gate。 |
| **PIT 底線** | label 只由 future close 算且尾 NaN；feature 無 future peek；features/labels **同一 timestamp 軸** | Tier-2 close oracle 非 L1 必做；L2 可另開。 |

**不建議**：BTC+1h 大窗（慢、與現 meta 12h 不一致）；多 symbol 進本 API fixture（範圍膨脹）；把完整 Feature Factory L1–L6 管線塞進 API fixture（那是 e2e epic）。

---

## (3) 真該刪 / 合併的測

**建議合併（刪冗餘、留一代表）** — 皆在 `test_ic_deep_analysis.py`：
1. `test_feature_list` ≈ `test_list_available_features_success` → **留一個**。
2. `test_full_analysis` ≈ `test_full_analysis_endpoint` → **留一個**（較完整斷言者）。
3. `test_deep_analysis_start` + `test_deep_analysis_result` 與 `test_start_deep_analysis_and_get_result` 高度重疊 → **留組合測一個 + 可選 invalid 路徑**。

**建議保留**：
- L0：`*_invalid_*`、`*_422`、`test_export_unknown_task_404`（若有）、`test_ic_config_update`。
- `test_deep_analysis_result_serializes_numpy_scalars`（獨特回歸，防 numpy 標量炸 JSON）。
- `test_export_api` 全套格式（csv/md/ai_json/hdf5 + 422）— 與 `test_ic_analysis_api` 的 export 路徑不同（`/export-csv/` vs `/export/{id}/…`），**不是簡單重複**；兩邊都留，但共用同一 completed task fixture。

**不建議刪**：整檔或「凡合成即刪」——覆蓋損失 > 清理收益。

---

## (4) 是否從票 6 拆 epic？

**是，應拆。**

| | 票 6（原 P2 債） | 新 epic（建議名） |
|--|------------------|-------------------|
| 原意圖 | label→`return_5` 契約對齊、23 紅止血 | API IC fixture 現代化 + 鐵律閉合 |
| 實際面 | 多層 stale（名/cadence/NaN/…）+ 鐵律 | 共用 builder、L0/L1/L2 分層、去重、manifest 釘扎 |
| 風險 | 繼續塞合成=假綠+違鐵律 | 中（a 相鄰、測側為主）；完整管線但不碰生產 resolver |
| 建議處置 | **BLOCK/範圍重裁**：記錄 rename 已做、cadence 為下一層、23 入 known-baseline 或明確「epic 閉合前不強制票 6 全綠」 | 交付 C：真 kline 衍生 fixture + 去重 + 23→綠 + 誠實邊界（無 e2e horizon 數值 oracle） |

**不拆的唯一合理理由**：使用者要「一包做完變綠」。即便如此，文件上仍應標 **epic 級工作量**，勿寫成「小 rename」。

**明確反對**：在票 6 內用 IC1A 式「43200 cadence + 人工 5 尾 NaN + 仍 `rng.normal`」當結案——那是**過渡綠**，會把鐵律違規洗成 DONE，並重演「下一護欄再紅」的 whack-a-mole。

---

## 給主委的可執行裁決摘要
1. **策略 = C（=分層 B）**；A 否；純 B 補「L0 不碰資料、L1/L2 共用真衍生」。
2. **切片 = ETHUSDT / 12h / 256–384 / feature_klines 路徑 / return_5 + 尾 5 NaN / session 一次 analyze**。
3. **刪併 deep 檔 2–3 組重複**；保留 export 全格式與 numpy 序列化。
4. **拆 epic**；票 6 停損於發現多層 rot + rename 進度，不強行合成補洞閉合。

## 狀態
STATUS: DONE（唯讀諮詢；無碼變更；無測試實跑本輪——切片列數/速度為建議值，實作 epic 時以一次 analyze 時延校準）

```
ASSUMPTIONS_VERIFIED: 三 fixture 合成+1s ts+12h meta；impl 已證 cadence 為 rename 後第一紅；validate_alignment 要 tail NaN==lag；ETHUSDT/12h 真檔 1696 秒級 ts；IC1A 曾用契約合成非真值
TESTS_RUN: none（諮詢指定唯讀）
FAILURES_SEEN: none
SCOPE_CHANGES: none（建議拆 epic，非本輪改碼）
NUMERIC_OR_SCHEMA_IMPACT: none（建議若落地：fixture 由合成→真 kline 衍生，API 斷言面可不變）
HANDOFF_PATH: handoffs/P2DEBT-T6-TESTSTRATEGY-grok.md
```
