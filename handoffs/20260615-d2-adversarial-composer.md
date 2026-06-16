# BATCH2D d* / FracDiff 非 CGSA 對齊 — Adversarial Review（Composer 2.5 獨立）

> 審查對象：`docs/BATCH2D_DSTAR_ALIGN_SPEC.md`、`docs/BATCH2D_DSTAR_ALIGN_TODO.md`、`docs/BATCH2D_DSTAR_ALIGN_MANIFEST.md`  
> 範本：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0+§1  
> 角色：獨立 adversarial（**不**附和 `handoffs/20260615-d2-design-composer.md`；交叉參考 Codex 設計與實際 code）  
> 日期：2026-06-15

## Verdict：需修補後派工

核心修復方向（column_layer_map + filter 優先序 + tier2a export）與根因證據一致，**可實作**。但 P0/P4 的 **L7 雙路徑抽取契約未寫死**，加上 §A 行號錨點有誤、P0 golden 統計量偏弱，派工後高機率卡在 freeze/parity 或假綠。**先補 SPEC §G + Task 0.1/4.1 的 loader 段落再派 Codex。**

---

## 被當成事實的未驗證假設（§0，挑戰前提優先）

| # | 文件陳述 | fact / assumption | 驗證 |
|---|----------|-------------------|------|
| A1 | 「parity 比對點必為 **L7_raw 產物**」（雙路徑同義） | **部分 assumption** | CGSA：`write_raw_from_registry_stream` → `run_dir/raw/*.parquet`，`generate_features` 回傳 **空** `features_df`（僅 index），oracle 在 `metadata.raw_path`（`feature_factory.py:3163-3164,3072-3086`）。非 CGSA：**無** L7_raw parquet，走 `_layer7_validate_and_persist` → `save_factory_output` HDF5（`feature_factory.py:3339-3448`）。兩路徑 **artifact 形狀不同**，不能共用「讀 L7_raw 目錄」一句話。 |
| A2 | §A「三方覆核行號為錨」含 `feature_preprocessor.py:2481-2510` 為 `transform()` 鏈 | **部分 false** | `transform()` 在 `:183-215`；`:2481` 是 `_transform_single` 定義；frame 入口是 `feature_factory._run_layer6_5_preprocessor` → `preprocessor.transform`（`feature_factory.py:2517`）。 |
| A3 | D2-9「CGSA==非 CGSA float32 exact **不預設**」但流程仍可派工 | **已標 assumption（0.70）** | 誠實；但 Task 4.1 若無「不 exact → BLOCKED 分案」的 **具體 loader + 欄名對齊** 步驟，agent 易用 `generate_features().features_df` 對 CGSA（設計 doc 舊 pseudocode 錯誤，`handoffs/20260615-d2-design-composer.md:115-124`）→ 假綠或假紅。 |
| A4 | P0 golden（mean/std + sample hash）可支撐「L3-L6 不動」 | **assumption** | 聚合統計 **不能** 保證 per-column exact；值重排若保持 marginal 統計可能漏（機率低但 §2 要求 value/mask）。真正 gate 在 P4 control **欄級 exact**（§G #5）— P0 單獨不足。 |
| A5 | `post_ic` 需「全量 map 子查詢」（`feature_factory.py:2460-2464`） | **misleading** | `post_ic` 明確 **關閉** fracdiff/ADF（`:2462-2464`）；map 對 fracdiff 無效。非 blocking，但 §A/D2-3 暗示接線必要。 |

---

## Findings

### [BLOCKING] 信心 High — 非 CGSA 無 L7_raw artifact，P0/P4 未給雙路徑抽取 API

- **證據**：§G「凍結 … L7_raw」；Task 0.1/4.1「依 L7_raw 產物」；§V「比對點鐵律」。  
- **實測**：CGSA `_layer7_raw_from_cgsa_pipeline` 寫 `raw_path` parquet（`feature_factory.py:3063-3086`），`FeatureGenerationResult.features_df` 為空（`:3163-3164`）。非 CGSA `_layer7_validate_and_persist` 寫 HDF5（`:3447-3448`），無 `write_raw_from_registry_stream`。  
- **會怎麼失敗**：`freeze_batch2d_baseline.py` / parity 測試無法對稱凍結；agent 用 CGSA `FeatureReader.load_columns_v2`（`feature_reader.py:115+`）一側、另一側用 `result.features_df` → **階段不對齊**（CGSA=stream L7_raw；非 CGSA=含 `_apply_timeframe_tag` 的 L7 persist 產物，`feature_factory.py:3370-3371`）或欄序/ dead-drop 時序差。  
- **修法**：在 §G + Task 0.1/4.1 **新增不可選的 Logical L7 契約**，例如：  
  - **CGSA**：`FeatureReader(base).load_columns_v2(symbol, tf, config_hash, cols, artifact_kind="raw")`，欄名取自 manifest。  
  - **非 CGSA**：`generate_features(..., persist=True/False).features_df`（或明訂讀 HDF5 的 helper），並聲明是否含 timeframe tag、是否與 CGSA stream 欄名對齊規則一致（單 TF 12h 需實測交集欄名集合）。  
  - 禁止：用 CGSA 的 `features_df`；禁止未寫明的 `assert_allclose(rtol=…)` 預設。

### [BLOCKING] 信心 High — Task 0.1「非 CGSA fracdiff-off L7_raw control」語意與 HEAD 現狀混淆

- **證據**：§G #1「fracdiff-off control」；§G #5「修後僅 L1/L2 變、L3-L6 exact」。  
- **實測**：HEAD 非 CGSA 已 **啟用** fracdiff，但因 regex 對裸欄名 **no-op**（`_filter_fracdiff_target_columns` `:2905-2927`）。fracdiff-off control ≠ 現行 HEAD 輸出（config 不同，winsor/ADF 路徑語意亦可能不同）。  
- **會怎麼失敗**：control baseline 與「修復前 no-op 快照」混用；L1/L2「相對 control 變」的因果不清。  
- **修法**：明寫 control = **`fractional_differencing.enabled=False`（+ 可選 adf off）** 的獨立 run，**不是** HEAD 預設；凍結腳本必須強制該 config。

### [MAJOR] 信心 High — §A 行號抽查多處錨點錯檔/錯行（agent 可接錯線）

- **證據**：§A「`transform()→_transform_single(source_layer=None)`（feature_preprocessor.py:**2481-2490,2505**）」；manifest [D2-1] 同引。  
- **實測**：`transform()` → `:215` `_transform_single()`；`:2505-2508` 是 `_transform_single_legacy` 內 fracdiff；factory 呼叫鏈在 `feature_factory.py:2478-2517`。  
- **其他抽查**：`:66` `_FRACDIFF_LAYER_RE` ✓；`:3170-3188` fracdiff filter ✓；`:3637-3651` dedup keep-first ✓；`column_group.py:66-85` `ColumnGroup.layer` ✓；`build_l65_golden.py:236-241` tier2a ✓；`feature_factory.py:2508-2511` CGSA 空 frame ✓。  
- **修法**：§A 拆成 **factory 接線**（2478-2517）與 **preprocessor 過濾**（183-215, 2886-2929, 3170+）兩段行號。

### [MAJOR] 信心 High — P0 golden canonical 以 aggregate 為主，單獨難抓 L3-L6 誤動/欄序漂移

- **證據**：§G / Task 0.1「欄集 sha + mean/std/nan_ratio + 抽樣 value/mask hash」。  
- **會怎麼失敗**：L3-L6 若被誤改但 marginal 統計碰巧不變（或 sample 未覆蓋），P0 `TestGolden` 仍綠；依賴 P4 才抓 — 但 P4 同受 BLOCKING#1 loader 影響。  
- **修法**：P0 對 **control** 至少存 **per-column float32 bytes hash 或全欄 np.testing** 子集（可 slow）；或明訂 P0 只驗「檔案存在+冪等」，**L3-L6 exact 僅 P4**（寫進 §G，避免 agent 以 P0 自滿）。

### [MAJOR] 信心 Medium — D2-9「實測誤差定 gate」邊界仍可能被偷渡寬容差

- **證據**：§G T3「不 exact → …確認非 provenance 修復造成才以實測誤差定 gate」；TODO §0 禁寬 tolerance。  
- **風險**：流程允許 **事後** 發明 rtol/atol；若無「分案必須 BLOCKED + 新 SPEC 修訂」機械門檻，執行端可能放寬 assert。  
- **修法**：§G 加硬規則：**禁止**在 batch2d 測試新增 `rtol/atol>0` 除非另開任務；不 exact 只能 `pytest.fail` + 分案 ID，不得在本 PR 改 gate。

### [MAJOR] 信心 Medium — TODO 偽碼 `str(col)` 與 SPEC「非字串欄名用實際 key」矛盾

- **證據**：TODO Task 1.1 `m.setdefault(str(col), label)`；SPEC Task 1.1「非字串欄名以實際 key 建 map 不 str() collision」。  
- **修法**：TODO 偽碼改為 `key = col if isinstance(col, str) else col` 或與 `_combine_layers` dedup key 一致之單一路徑。

### [MAJOR] 信心 Medium — Manifest D2-8「T5 golden 重生 tier2a+tier2b」未落入 SPEC/TODO Task

- **證據**：manifest [D2-8] T5；SPEC §G 只列 6 項（無 tier2b 重生）。  
- **會怎麼失敗**：執行端 scope 膨脹或遺漏；與「同 PR 修 tier2a」邊界不清。  
- **修法**：要麼 SPEC 增 Task 3.2 tier2b，要麼 manifest 刪 T5 並標 tier2b 另批。

### [MINOR] 信心 High — chunked / post_ic / dedup 接線：chunked OK，post_ic 可省略，dedup 需驗證測試

- **chunked**（重點 7）：`_transform_chunked` → `_transform_single(chunk_df)` 無 `source_layer`（`:2650-2651`）。map 若為 **instance attr**（SPEC Task 2.1）則 chunked 自動覆蓋；**不必**顯式參數傳遞，但 Task 2.1「全鏈傳遞」易誤導實作 param drilling。  
- **post_ic**：fracdiff 已關，**可不**傳 map；IC-first `pre_ic`（`feature_factory.py:2023-2024`）**必須**傳 map — SPEC 僅覆蓋 `generate_features` frame path `:363-378`，未列 `ic_first_l65_pre_input` combine（若 parity 用 legacy 可 N/A）。  
- **dedup keep-first**：`_combine_layers` `keep="first"`（`:3637-3651`）與 `setdefault` map 語意一致 ✓；Task 1.1 要求 map 與 surviving cols 一致 — **需**測試斷言，否則 dedup 後 orphan col 無 map 時 fail-closed 行為未指定。

### [MINOR] 信心 High — CGSA 禁改：可守但靠紀律，非結構隔離

- **證據**：§C / TODO §0「CGSA 主路徑禁改」；改動點在 `_filter_fracdiff_target_columns` 的 `source_layer is None` 分支（CGSA 走 `:2894-2903`）。  
- **風險**：同一函式、同一測試檔；agent 若重排優先序或改 `source_layer` 分支 → CGSA 回歸。  
- **緩解**：既有 `test_fracdiff_registry_layer_filter_uses_group_metadata`（`tests/test_l65_parallel.py:214`）+ SPEC 禁弱化 — **足夠但非鐵閘**；建議 Task 2.1 驗證命令 **顯式**包含該測試名。

### [MINOR] 信心 High — tier2a 分案修復完整度良好

- **證據**：`build_l65_golden.py:238-241` 將 `_d_star_cache={}` 當 dict；實際 `Optional[DStarCache]`（`feature_preprocessor.py:147-148`）；transform 在 `_d_star_cache_shared=False` 用 ephemeral cache（`:3225-3231`）。  
- **SPEC Task 3.1**：`export_d_star_values()` + `_d_star_cache_shared=True` + keys ⊆ {L1,L2} — **根因對症**；與 frame map 正交 ✓。  
- **殘留**：synthetic 欄名 `L1_*` 走 regex 本來可選中（`:164-166`），tier2a 失敗點確實是 **讀 cache** 而非 filter。

---

## §1 十類快掃（無問題標「無」）

| 類別 | 結論 |
|------|------|
| 1 矛盾/互斥 | TODO `str(col)` vs SPEC 非 str key；manifest T5 vs SPEC 無 tier2b |
| 2 漏項/端到端 | **BLOCKING**：L7 雙路徑 loader；ic_first combine 未列（parity 若 legacy 可 N/A） |
| 3 不可測驗收 | P0/P4 缺 loader → 不可執行；其餘 Task 有 pytest 錨點 |
| 4 可疑 quant | ADF 不經 layer gate（兩路徑同）；fracdiff 修復後 L3-L6 依 map — 合理 |
| 5 過度工程 | 無 |
| 6 OOM/並行 | chunked 共用 d* cache（`:2625-2670`）已考慮；未改 scope |
| 7 Cache | d* 跨 chunk flush；cache invariant 在 §G #4/#6 — 可測 |
| 8 API/相容 | map 預設 None → 現行行為；export API 新增 — OK |
| 9 測試品質 | 禁弱化 CGSA 測試 ✓；P0 aggregate 偏弱（見 MAJOR） |
| 10 Agent 可執行 | map/filter 函式級清楚；**freeze/parity loader 不清** |

---

## 七項重點結論（使用者檢查清單）

1. **L7_raw 比對點**：CGSA 端正確（registry stream → parquet）；非 CGSA **沒有** 同名 artifact — 必改為「Logical L7 契約」並寫清 reader。  
2. **誠實容差 exact-first**：文字方向正確；需禁止本 PR 內事後 rtol/atol。  
3. **CGSA 禁改**：可行，靠既有 CGSA 測試 + code review。  
4. **Golden 抓 L3-L6/重排**：P4 control 欄級 exact 可抓；P0 aggregate **單獨不足**。  
5. **tier2a**：分案完整，與 map 正交。  
6. **§A 行號**：多處錯誤，需修正後再當派工錨點。  
7. **chunked/post_ic/dedup**：chunked 靠 instance map 即可；post_ic 可不接 map；dedup 需 map↔survivor 測試。

---

## 與設計 doc 的刻意分歧（非附和）

- 設計 doc T3 pseudocode 用 `generate_features` 兩路 `out_cgsa/out_frame` 比對 — **CGSA 側 features_df 為空**，SPEC 已改口「L7_raw」但 **未補 loader**，比設計 doc 更危險（名稱像已解決）。  
- 設計 doc 建議「test-only 抽樣 API」；SPEC 未採用也未指定 `FeatureReader` — 派工缺口。

---

ASSUMPTIONS_VERIFIED: CGSA L6.5 回空 frame（factory:2508-2511）；非 CGSA 無 L7_raw parquet（factory:3339-3448 vs 3063-3086）；regex no-op（preprocessor:2905-2927）；tier2a dict 注入失效（build_l65_golden:238-241 + preprocessor:3225-3231）；dedup keep-first（factory:3637-3651）  
TESTS_RUN: none（讀取型 adversarial；未跑 pytest / 未寫 data_cache）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（僅本 handoff）  
NUMERIC_OR_SCHEMA_IMPACT: 無代碼變更；審查結論：修復後非 CGSA L1/L2 數值變、schema 不變（與 SPEC 一致）

STATUS: FAIL — 需先補 §G/Task0.1/4.1 的 CGSA vs 非 CGSA Logical L7 抽取契約、修正 §A 行號、釐清 fracdiff-off control 定義後再派工
