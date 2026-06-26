# IC Phase 1 — 1a 第一刀（單幣縱向接線）MANIFEST

> 範圍鎖定（使用者 2026-06-26 拍板）：切兩刀，**本刀=cut1=單幣縱向 `analyze()` 主流程**；橫截面 `analyze_cross_sectional()` 留 cut2。
> 預設策略：三方簽核 PASS 後**新算法預設開啟**；flag 只當逃生口/對照（[[feedback_no_default_off_after_validation]]）。
> 來源：BRIEF（20260626-1a-BRIEF）+ CONVERGED §Phase1 + 1-contract SPEC 殘留清單（B3-FINAL-SIGNOFF §殘留）。
> 已驗證錨點（實讀）：`analyze()` 8 階段流程 orchestrator:94；winsor/standardize 現對全資料 fit data_preprocessor.py:154/136；`metadata["symbol"/"timeframe"]` 主流程可取 orchestrator:1039；adapter/factory 殘留 factories.py:574（未轉 allowed_symbols）。

## 本刀目標（一句）
讓 1-contract 的防洩漏紅線**真正生效於單幣縱向主流程**：切分由主流程產生並校驗 → 清洗（winsor/standardize）只用訓練段 fit → IC/統計在測試段（OOS）報告。簽核 PASS 後預設開啟。

## 扁平項目（每項將落進 SPEC 一個 Task；gate coverage_check 對此清單逐 ID 驗）

### A. 契約啟用前置（補完 1-contract 三殘留）
- **[A-1]** `create_ic_split_adapter()` 轉傳 `allowed_symbols`（factories.py 現僅轉 expected_freq/strict_embargo，drop 掉 allowed_symbols → L4 allowlist 權威防線在接線端失效）。對應殘留 R-L4-allowlist。
- **[A-2]** 主流程從 `metadata["timeframe"]`（如 "1h"/"4h"/"12h"）推導 `expected_freq` 傳入 adapter/validate（現預設 None → gap fail-closed 不生效）。對應殘留 R-expected_freq。含非法/缺 timeframe → fail-closed（不得靜默回退 None）。
- **[A-3]** 主流程從真實 symbol universe 傳入 `allowed_symbols`（單幣＝{該 symbol}）至切分校驗。**範圍更正（雙家族 adversarial）**：`analyze()` 單幣輸入無 row-level symbol 欄 → allowlist 僅驗 **metadata symbol**（缺/不在 allowlist→fail-closed）；row-level 跨 symbol 污染 cut1 **N/A**，留 cut2/multi-symbol。

### B. 切分產生 + 紅線接進主流程
- **[B-1]** 在 `analyze()` ingestion 後、preprocessing 前，由 features_df 的 timestamp index + `metadata["symbol"]` 產生單幣 train/test `SplitPlan`（複用 ML 孤島切分索引邏輯，不重寫切分數學）。
- **[B-2]** 對產生的 split 套 `validate_split_integrity`/`validate_split_pair_integrity`（帶 [A-2] expected_freq + [A-3] allowed_symbols）；單幣時間軸不連續/重複/亂序 → fail-closed raise（接 1-contract C-3 紅線）。
- **[B-3]** SplitPlan 用 `index_kind="positional"`（stage0 整數位置，與既有 validator/adapter 相容）；遮罩跨 stage 重導 `_derive_stage_masks` 用 **train/test `time_bounds`（timestamp 區段）∩ current index**；每個會改 row 的 stage（event_filter）後重導，不靠 positional 直貫。不變量＝train/test 時間互斥 + purge，row 移除不破壞。（第二輪 adversarial 修正：移除自相矛盾的 timestamp index_kind）
- **[B-4]** holdout `purge_gap >= 實際 label horizon`；杜絕 train 末段 forward-return 標籤用到 test 段價格（前瞻偏誤，`validate_split_pair_integrity` 數字檢查擋不住語義洩漏）。（雙家族 adversarial 新增）
- **[B-5]** pipeline 順序重排：stage0 後 `_resolve_effective_label_horizon(config, labels_df)`（解 stage2 fallback `default_horizon not in horizons→horizons[0]` 綁錯）→ 建 split（purge=該 horizon）→ 才 stage1 train-fit；禁先全段 preprocess 再補 mask。（第二輪 adversarial 新增，解依賴倒置）

### C. 訓練段 fit 防洩漏（核心正確性）
- **[C-1]** stage1 winsorize 的 clip 邊界（percentile/std/mad）**只從 train rows 學**，再套用到 train+test 全段（現 `series.quantile()` 對全段 → 洩漏）。
- **[C-2]** stage1 standardize 的 mean/std **只從 train rows 學**再套全段（現 `df.mean/std` 對全段 → 洩漏）。
- **[C-3]** preprocessing 介面接受 train 遮罩；無遮罩（legacy/flag off）時維持現行為（全段 fit）以保舊數字可重現。
- **[C-4]** `handle_missing` 的 coverage（缺失率刪欄）**只從 train rows 算**（現 `notna().mean()` 全段＝特徵選擇洩漏）；flag-off 保全段。（雙家族 adversarial 新增）
- **[C-5]** `remove_constant_features` 的常數判定**只從 train rows 算**（現 `nunique` 全段＝特徵選擇洩漏）；flag-off 保全段。（雙家族 adversarial 新增）

### D. 測試段 OOS 報告
- **[D-1]** stage4 IC / stage5 統計（icir/p 值/monotonicity 等）在**測試段（OOS）**計算與報告；selection scope 標記為 test（為 1b FDR 預留正確 scope，本刀不實作 FDR）。
- **[D-2]** summary_table / passed_features 的數值來源切到 OOS；threshold 套用對象一致（防 train 上挑、test 上報的混用）。
- **[D-3]** **所有進 summary_table/threshold/passed_features 的指標一律 test scope**（icir/p/monotonicity/coverage/turnover），不得任一全段。（雙家族 adversarial 新增，補 OOS 口徑完整性）
- **[D-4]** rolling IC OOS 語義（option A）：rolling_ic 在 train+test 連續算（warmup 用 train，無洩漏），icir/p/threshold/summary **只取 test 時間索引上的值**；`min_test_rows >= max(rolling_windows)+purge_gap` 否則 `SkippedResult`。（第二輪 adversarial 新增，定義 OOS rolling 語義）
- **[D-5]** decay/grouped/stage6-redundancy flag-on 不得以全段值入 summary/passed/filtered：進選擇/輸出的一律 test scope（含 stage6 corr 對 test 算），decay/grouped informational 且 report metadata 標 `scope=test`。（第二輪 adversarial 新增）

### E. Flag、預設、Golden
- **[E-1]** 新增 config flag（如 `ic_train_test_split`）作為**逃生口**；簽核 PASS 後**預設開啟**（新算法＝正常行為）。
- **[E-2]** **舊數字重現 golden**：flag 明確關閉時，`analyze()` 輸出與既有 baseline **逐位元組一致**（保護既有結果可重現/緊急回退）。
- **[E-3]** **新預設 golden**：flag 開啟（新算法）的 OOS 輸出另凍一份 golden，**三方簽核驗過才凍**；之後迴歸以此為準。

### F. 測試與簽核（真實 kline，可證偽）
- **[F-1]** 防洩漏可證偽測試（真實 `kline_cache.h5`）：單幣 winsor/standardize 在含 test 極端值的資料上，**train-fit 結果不受 test 段極端值影響**（注入 test 段離群 → clip 邊界不變 → PASS；若變動＝洩漏＝FAIL）。
- **[F-2]** 單幣時間軸 gap/重複/亂序反例 → 主流程 `pytest.raises`（fail-closed，不得降級 warning）；連續正例 → 正常切、symbol 純度==1.0。
- **[F-3]** flag-off byte 等價（[E-2]）：deep-equal 既有 baseline。
- **[F-4]** 解耦：`grep "from api\." momentum/`==0；`./scripts/check_decoupling_phase4.sh` exit 0。
- **[F-5]** 三方數據正確性簽核（Claude+Codex+Composer 獨立簽「split/fit/OOS 無洩漏」），真實 kline，不靠使用者驗收（鐵律 2026-06-09）。

## 明確不在本刀（cut1）
- 橫截面 `analyze_cross_sectional()` 防洩漏（→ cut2；1-contract §N 已登記留 1a）。
- FDR 接線（1b）、Net IC 量綱（1c）、factor_attribution（1d）、HAC/bootstrap（1e）、空圖（1f）。
- 重寫 CPCV/WF 切分數學（複用既有，僅 adapter 層讀取）。
- 前端接線（另刀）；artifact HTTP 篩選端點（Phase 3）。

## 高風險原則命中（決定走完整大管線）
(b) 跨模組/共用路徑：`ic_filter_orchestrator.analyze`、`data_preprocessor`、`factories`、`contracts`、多下游讀 get_result。
(d) ML 正確性/防洩漏：train-only fit、OOS 報告、時間軸 purge、單幣連續性。
→ §G Golden 必填、SPEC 前雙家族 adversarial 必跑、三方數據簽核必跑。

## 依賴與順序
A（前置）→ B（切分接線）→ C（train-fit）→ D（OOS 報告）→ E（flag/golden）→ F（測試/簽核）。E-3/F-5 在最後：簽核 PASS 才凍新 golden、才切預設 ON。
