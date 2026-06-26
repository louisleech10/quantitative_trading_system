# IC Phase 1 — 1a cut1 SPEC+TODO 第二輪 Adversarial Review（Composer 2.5，獨立）

> 審查對象：`docs/IC_PHASE1_1a_CUT1_SPEC.md` + `docs/IC_PHASE1_1a_CUT1_TODO.md`（對照第一輪 reconcile + 實讀接線程式）
> 對照：`handoffs/20260626-1a-cut1-ADVERSARIAL-RECONCILE.md`
> 嚴格度：MAXIMUM | 焦點：完整審查（train/test 洩漏 + OOS 口徑 + pipeline 順序 + TODO 批次可執行性）| 日期：2026-06-26

## Verdict：需修補後派工

第一輪 4 BLOCKING 在文件層已大部分落地（holdout 裁決、purge≥horizon、C-4/C-5、D-3），但仍有 **契約層 `index_kind` 與 `validate_split_pair_integrity` 不相容**、**rolling IC 的 OOS 語義未定義**、**B2 依賴 B5 才新增的 config 欄位**、**G-OLD 仍無寫死 config_hash/凍結腳本路徑** 等會讓實作者猜測或產出假 OOS 的缺口。修補後可派工；不建議整份重作。

---

## 第一輪 4 BLOCKING 修補核對（逐一：已解決/未解決/部分 + 證據）

### [BLK-1] split × event_filter 順序 → timestamp identity 遮罩重導（Task 2.3）

**判定：部分解決**

- **已解決部分**：RECONCILE 的修法已寫入 SPEC §P Task 2.3 / TODO Task 2.3——split 以 stage0 timestamp 定義、event_filter 後 `_derive_stage_masks(split_plan, current_index)` 用 `current_index.isin(train_timestamps)` 重導，不用 positional mask 直貫（SPEC L81-86；TODO L77-84）。與實讀 `analyze()` stage1→stage3→stage4 順序（`ic_filter_orchestrator.py:114-134`）及 event_filter `loc[idx]`（`:1096-1097`）一致。
- **未解決部分**：
  1. **`index_kind="timestamp"` 與契約校驗不相容**：Task 2.1 要求 `index_kind="timestamp"`、`row_index=<timestamp 或可映射>`（SPEC L69；TODO L62），但 `validate_split_integrity` 一律 `row_index = np.asarray(plan.row_index, dtype=int)` 並當 positional index 索引 `symbol_arr`/`ts_arr`（`contracts.py:511-537`）。`ICSplitAdapter` 實際用 `index_kind="positional"`（`ic_split_adapter.py:234-246`）。若 `row_index` 真存 timestamp，`dtype=int` 會截斷或 raise；若仍存 positional 則 `index_kind="timestamp"` 為假標籤。
  2. **split 插入點未在 TODO 寫死**：MANIFEST [B-1] 要求「ingestion 後、preprocessing 前」（`cut1-MANIFEST.md:19`），Task 3.5 要求 stage1 用 train 遮罩（TODO L122），但 Task 2.1 只寫「analyze 呼叫」、未明確「stage0 與 stage1 之間重排 pipeline」。現行 `analyze()` 先 `_stage1_preprocessing`（`:114-115`）。冷啟動 agent 可能把 split 放在 event_filter 之後。
  3. **`_derive_stage_masks` 輸入契約未定型**：未規定 train/test timestamp 集合從 `SplitPlan.row_index`、`time_bounds` 還是平行欄位取得；`base_universe_hash` 在單幣無 symbol 欄的 `features_df` 上如何計算（對照 adapter 的 `_base_universe_hash`，`ic_split_adapter.py:189-199`）未給公式。

### [BLK-2] purge_gap ≥ label horizon（Task 2.2）

**判定：部分解決**

- **已解決部分**：`purge_gap = 所用 horizon`、holdout 公式 `train=idx[:split_point]`、`test=idx[split_point+purge_gap:]`、`split_point=floor((1-oos_test_size)*n)` 已凍結（SPEC L69-78；TODO L62-75）。對 forward-return horizon=5，purge 區間 5 列可阻擋 train 末列 label 用到 test 價格（算術上 purge_gap≥5 時 split_point-1 的 +5 價格落在 purge 區）。
- **未解決部分**：
  1. **split 在 stage2 label 之前產生**，purge 取 `config.global_settings.default_horizon`，但 stage2 若 `default_horizon not in labels_cfg.horizons` 會改取 `horizons[0]`（`ic_filter_orchestrator.py:1049-1051`）——purge 可能綁錯 horizon。
  2. **`config.embargo` 不存在**：Task 2.1 寫 `embargo=config.embargo`（SPEC L69；TODO L62），`ICConfig` 頂層無 `embargo` 欄（`ic_config_schema.py:330-365`）；僅 `RollingOOSConfig` 有無關的 `min_splits`。
  3. **Task 2.2 反例驗證依賴未指明的 raise 來源**：「`purge_gap < horizon` → raise」未寫是 `validate_split_pair_integrity`、自建語義檢查，還是 `SplitPlan.__post_init__`；契約層 purge 檢查是 train 踩 test 禁區（`contracts.py:586-595`），**不保證**偵測「forward-return 語義前瞻」除非 holdout 公式正確——需與 Task 2.1 公式連動測試，文件未鎖死。

### [BLK-3] handle_missing / remove_constant train-only（Task 3.3/3.4）

**判定：大部分解決**

- **已解決部分**：[C-4]/[C-5] 已入 SPEC/TODO，`fit_mask` 透過 Task 3.5 `preprocess(..., fit_mask)` 貫穿四類統計（SPEC L103-122；TODO L104-126）。與實讀洩漏點 `handle_missing` `:113-116`、`remove_constant` `:120-124` 對齊。
- **殘留缺口**：
  1. **`handle_missing` 的 `ffill` 仍對全段**：coverage 改 train-only，但 `filled = df.ffill(...)` 在算 coverage 前對全列（`data_preprocessor.py:113`）。ffill 僅向後看，通常無 lookahead，但 test 段 NaN 會被 train 尾端值填入後參與**後續** winsor/standardize 的全段套用——文件未討論是否接受。
  2. **feature_filter 在 stage3 之後、stage4 之前**（`ic_filter_orchestrator.py:127-129`）——屬 config 驅動欄位篩選，非數據統計，cut1 可接受，但 TODO 未註明。
  3. **`_ic_cache` 未要求 flag/split 變更時清除**（§N 僅註記；`ic_filter_orchestrator.py:1414-1429` 無 split-aware key）——同 orchestrator 實例連跑 flag on/off 可能污染 deep analysis 路徑。

### [BLK-4] D-3 全 stage5 指標 OOS

**判定：部分解決**

- **已解決部分**：Task 4.3 明列 monotonicity/coverage/turnover/`compute_ic_statistics(rolling_ic)` 一律 test scope（SPEC L139-144；TODO L146-152）。`_apply_thresholds` 門檻欄位為 ic_mean/icir/p_value/ic_hit_rate/monotonicity/coverage（`ic_filter_orchestrator.py:1546-1571`），與 D-3 對齊。
- **未解決部分**：
  1. **`ic_half_life`（decay）仍進 summary_table**（`_build_summary_table` `:1518` 取自全段 `ic_decay`），Task 4.3 僅說 informational「不進 threshold」——若 decay 仍全段計算（stage4 `:1233-1241`），summary 仍混 train 資訊，報告語義與 OOS 宣稱不一致（§N 登記為 non-blocking，但三方簽核時會被挑戰）。
  2. **stage6 redundancy 對全段 `features_df[passed_features]` 算相關矩陣**（`:1335-1340`）——passed_features 雖 OOS 篩出，相關性仍含 train 列；§N 標 informational，但文件未禁止其進 `get_result()` 下游。
  3. **Task 4.1 與 rolling IC 語義衝突**（見下方挑戰前提）——D-3 假設 OOS `rolling_ic` 已有正確語義，但 4.1 未定義。

---

## Findings（挑戰前提置頂）

### [BLOCKING | High] holdout +「僅 test subset 算 rolling_ic」在量化語義上不成立，且與 icir/p-value 鏈條矛盾

- **證據**：Task 4.1「flag on→對 test 布林遮罩 subset features_df/label 再算 rolling_ic」（SPEC L126-127；TODO L132）。`compute_rolling_ic` 用 `_rolling_corr_matrix` 需每 window 至少 `window` 列歷史（`ic_engine.py:268-302`）；預設 `rolling_windows=[21,63,126]`（`ic_config_schema.py:66-67`）。test=20% 時，**純 test 子集**前 62/125 列無有效 rolling IC。
- **會怎麼失敗**：實作者照字面只做 test subset → icir/p-value 基於大量 NaN/短窗 → 或實作者擅自用 train+test 算 rolling 再切片但未寫進 SPEC → 三方簽核對「何謂 OOS IC」無一致標準；`test_stage5_metrics_all_oos` 改 train 不動 test 可能 PASS 但 rolling 窗語義錯。
- **修法**：在 Task 4.1/4.3 **寫死一種**（二選一，不得留給實作者）：(A) **warmup 允許**：用 train+test 算 rolling_ic，但 icir/p-value/threshold **只取 test 時間索引上的 rolling 值**；或 (B) **purge 後 test 內自含 warmup**（需 `len(test) >= max(window)+1` 否則 `SkippedResult`）。補可證偽測試：test 前 `window-1` 列 rolling_ic 為 NaN/或明確標記 in-sample warmup。

### [BLOCKING | High] `index_kind="timestamp"` 與 `validate_split_pair_integrity` 契約不相容，Task 2.1/2.3 無法同時滿足

- **證據**：SPEC/TODO 要求 `index_kind="timestamp"`（SPEC L69；TODO L62）；校驗路徑 `validate_split_integrity` 強制 `row_index` 為 `int` positional（`contracts.py:511,528-529`）；adapter 先例全用 `positional`（`ic_split_adapter.py:234-246`）。
- **會怎麼失敗**：實作者存 timestamp→校驗 crash 或靜默錯 index；存 positional 卻標 timestamp→`_derive_stage_masks` 與校驗假設分裂；golden split 邊界 timestamp 無法從 plan 穩定導出。
- **修法**：要麼 (1) holdout `SplitPlan` 改 `index_kind="positional"` + `row_index`=stage0 整數位置，**遮罩層**單獨用 timestamp identity（與 adapter 一致）；要麼 (2) 擴充 `validate_split_integrity` 支援 `index_kind="timestamp"` 並寫測試。不得兩套語義並存無文件。

### [BLOCKING | High] TODO 批次拓撲矛盾：B2 需要 `ic_train_test_split`/`oos_test_size`，但 Task 5.1 在 B5 才新增

- **證據**：§B 表：B2=Task 2.1-2.3，B5=Task 5.1（`IC_PHASE1_1a_CUT1_TODO.md:18-24`）。Task 2.1 讀 `config.oos_test_size`（TODO L62）；Task 2.3/3.5/4.x 皆「flag on→新路徑」（TODO L81,122,132）。Task 5.1 才「`ICConfig` 新增 `ic_train_test_split` + `oos_test_size`」（TODO L156-158）。
- **會怎麼失敗**：冷啟動 agent 跑 B2 時 ICConfig 無欄位 → 硬編常數或擅自加欄位 → 與 B5 衝突；或 B2 全開無 flag 守衛 → G-OLD 在 B5 前已破。
- **修法**：將 `ic_train_test_split`/`oos_test_size`（及 `embargo` 若需要）**移至 B1 或 B2 開頭**（僅 config 欄位 + 預設 OFF，不改行為）；B5 保留 G-OLD 與文件化。§B 表與 Task 5.1 同步改。

### [BLOCKING | High] §G G-OLD 仍不可派工：config_hash 佔位、凍結腳本路徑錯誤、golden 目錄不存在

- **證據**：§G L36-37 `config-hash <寫死>` 仍為佔位；`tests/golden/ic_phase1_1a_cut1/` 不存在（glob 0 files）；凍結命令指向 `scripts/freeze_baseline.py`，repo 僅有 `tests/golden/ic_phase1_contract/freeze_baseline.py`（含寫死 hash `a384e6d22ca15fc639757cb3162e7cb3`）。HANDOFF L25 要求動工前凍 G-OLD。
- **會怎麼失敗**：dispatch gate 應擋；實作者自選 hash → G-OLD 不可比；CI skip-if-absent 假綠。
- **修法**：規劃端動工前寫死 cut1 專用 `config_hash` + 修正 freeze 腳本路徑（或複用 1-contract 腳本並新 out 目錄）+ 產出 `baseline_old_btc_1h.json`；§G/TODO Task 5.2 填入實測 hash 與 sha256。

### [MAJOR | High] `oos_test_size=0.2` 預設未驗證對 crypto 樣本量 / rolling 窗是否足夠

- **證據**：預設 0.2 凍結（SPEC L69；RECONCILE L13）；event_filter 可大幅縮減列（`ic_filter_orchestrator.py:1092-1094` tier insufficient fallback）；Task 2.1 邊界寫 `test<min`→`SkippedResult` 但 **未定義 min**（TODO L65；`min_splits` 屬 `RollingOOSConfig` `:216`，與 holdout 無關）。
- **會怎麼失敗**：BTC/1h 在 event_filter 開啟時 test 有效列 <126 → rolling IC 全 NaN → 靜默空 passed_features 或 SkippedResult 行為不一致。
- **修法**：寫死 `min_test_rows`（建議 `>= max(rolling_windows)+purge_gap` 或引用 `ic_calculation.rolling_windows` max）；與 `InsufficientDataError`（現行 `<100` 列，`:1442-1443`）關係寫清。

### [MAJOR | High] split 產生時機 vs label horizon 時序：purge 可能早於實際所用 horizon

- **證據**：Task 2.1/2.2 在 analyze 早期產 split（manifest：preprocessing 前）；label horizon 最終在 stage2 才確定（`ic_filter_orchestrator.py:1049-1051`）。
- **會怎麼失敗**：`default_horizon=5` 不在 `horizons` 時實際用 `horizons[0]=1`，purge 仍=5（過度保守，可接受）或若實作錯綁 default 而實際 horizon=21 → purge 不足 → label lookahead。
- **修法**：Task 2.1 改為 **stage2 之後、stage3 之前**產 split（已知實際 horizon），或 Task 2.2 明確「purge_gap = stage2 回傳的實際 horizon」並調整 manifest [B-1] 順序。

### [MAJOR | Medium] Task 4.3 / §N 對 decay/grouped/redundancy 的「informational」與 summary/report 輸出不一致

- **證據**：§N L201「decay/grouped…不進 threshold」；但 `_build_summary_table` 含 `ic_half_life`（`:1518`）；stage7 report 輸出 `ic_decay`/`grouped_ic` 全段（`:1382-1384`）。
- **會怎麼失敗**：三方簽核認定「報告仍洩漏」；使用者看 decay 圖以為 OOS。
- **修法**：flag on 時 decay/grouped 要麼 test-only 計算，要麼從 summary/report 剝離並在 report metadata 標 `scope=train_full`。

### [MAJOR | Medium] §B 缺可複製派工 prompt，冷啟動執行條件未達 prompt 要求

- **證據**：ADVERSARIAL2-PROMPT §1-10 要求「§B 批次派工 prompt 可直接複製」；TODO §B 僅依賴表（L15-24），無 per-batch scope/驗收/禁止事項模板。
- **會怎麼失敗**：派 Codex B1-B6 時 scope 漂移；與 gate `dispatch` 所需參數不一致。
- **修法**：每 Batch 增 5-10 行派工塊（允許檔、驗收 pytest 列表、禁止改 API 前端等）。

### [MAJOR | Medium] Task 6.3 仍不可機械檢，且與 B6 gate 循環依賴

- **證據**：Task 6.3 驗證=「三方齊簽 PASS」（SPEC L184-186；TODO L204）；無 pytest/assert 可證偽。
- **會怎麼失敗**：confirm-review 代替 adversarial；B6 要求簽核 PASS 才凍 G-NEW，但簽核標準主觀。
- **修法**：增 checklist 機械項（kline 路徑、purge 反例 pytest 名、G-OLD diff 0、grep 不弱化 assert）+ 指定 handoffs 檔名模板；簽核項必須映射到已存在測試。

### [MINOR | Medium] API `config_override` 路徑已存在，但前端型別 / ICAnalyzeRequest 未列入 Task 5.1

- **證據**：Task 5.1 只列 `ic_analysis_service.py`（TODO L159）；`ICAnalyzeRequest.config_override` 已通用（`ic_analysis_service.py:1061-1097`）；前端 `frontend/src/lib/types.ts` 未提及。
- **會怎麼失敗**：cut1 後端可 override，前端不知新欄位——cut1 若宣稱 API 完備則過早。
- **修法**：Task 5.1 加註「cut1 僅引擎+service；前端接線 cut2/另刀」或列 N/A。

### [MINOR | Low] Golden 檔名規則 SPEC/TODO 不一致

- **證據**：§G FIX-CACHE「`symbol_timeframe_confighash_splitid`」；Task 5.3 TODO L174「`BTC_1h_<config_hash>_<split_id>`」；Task 5.2 仍寫 `baseline_old_btc_1h.json`（無 hash 嵌入）。
- **修法**：統一一種命名並寫進 freeze 腳本。

---

## §1 必查 10 類（摘要）

| # | 類別 | 判定 |
|---|------|------|
| 1 | 矛盾/互斥 | **有** — B2/B5 config 依賴；`index_kind` vs 校驗；manifest preprocessing 前 vs analyze 現序；embargo 幽靈欄位 |
| 2 | 漏項/端到端 | **部分** — 23 manifest ID 均落 Task；缺 `min_test_rows`、freeze 實體、pipeline 重排明令 |
| 3 | 不可測驗收 | **有** — config_hash 未寫死；Task 6.3 非機械；rolling OOS 缺可證偽定義 |
| 4 | 可疑 quant 假設 | **有（重災區）** — rolling IC warmup；單切點 holdout；oos_test_size=0.2；purge 與 horizon 時序 |
| 5 | 過度工程 | **無** — holdout + `_derive_stage_masks` 合理 |
| 6 | OOM/並行 | **無** — 單幣 cut1，無新巢狀並行 |
| 7 | Cache 正確性 | **有（輕）** — `_ic_cache` 無 split/flag key；golden 命名未統一 |
| 8 | API/型別/相容 | **部分** — config_override 可透傳；前端未列；flag-off byte 守恆意圖清楚 |
| 9 | 測試品質 | **部分** — 要求真實 kline 明確；pytest 檔尚未存在（預期）；缺 rolling warmup 測試 |
| 10 | Agent 可執行性 | **有（本輪核心）** — 多 Task ≥3 要點達標，但 B2/B5 依賴、split 插入點、`base_universe_hash` 公式、§B 無派工 prompt 未達「拿了就能寫」 |

## §2 範本錨點 + 獵空殼

- SPEC §RISK/§A/§C/§G/§P/§V/§R/§N、TODO §0/§B：**皆有實質內容**，非表頭空殼。
- **半空殼**：§G `config-hash <寫死>`（SPEC L36-37）；Task 2.1 `row_index=<timestamp 或可映射>`（TODO L62）；Task 2.1 `test<min` 未定 min（TODO L65）。
- §G 凍結順序（G-OLD 動工前、G-NEW 簽核後、default ON 在 B6）自洽，但 **G-OLD 前置條件尚不可執行**。

---

## 被當成事實的未驗證假設（逐一）

1. **`oos_test_size=0.2` 對 BTC/1h + 預設 rolling_windows 足夠 OOS** — 未附實跑有效 test 列數 / event_filter 後剩餘列數。
2. **「test subset 上算 rolling_ic」等同 OOS IC 報告** — 與 `ic_engine.compute_rolling_ic` 窗口感知不符，未驗證。
3. **`purge_gap = default_horizon` 恒等於 stage2 實際 label horizon** — stage2 fallback 邏輯可能推翻（`ic_filter_orchestrator.py:1049-1051`）。
4. **`validate_split_pair_integrity` 可擋住所有 label lookahead** — 契約僅檢查 positional purge/embargo 禁區（`contracts.py:586-595`），語義前瞻依賴 holdout 公式正確，未端到端實跑。
5. **`scripts/freeze_baseline.py` 存在且適用 cut1** — 實際僅 `tests/golden/ic_phase1_contract/freeze_baseline.py`。
6. **§A「timeframe→expected_freq 已實跑」** — 文件已貼輸出（SPEC L18），**此項已驗證**，非未驗證假設。
7. **decay/grouped 標 informational 後下游無害** — 未驗證 report/export 是否仍暴露全段 decay 給使用者解讀為 OOS。

---

STATUS: DONE
