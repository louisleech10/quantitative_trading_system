## Verdict：需修補後派工

## Findings（每條：[BLOCKING|MAJOR|MINOR] + 信心度 + 證據 + 會怎麼失敗 + 修法）

### 挑戰前提 findings

1. [MAJOR] High — §A 把 timeframe 解析列入「已查證事實」，但原文同句承認未實跑  
證據：`handoffs/20260626-ic-PHASE1-1a-cut1-SPEC-DRAFT.md:21`：「`pd.Timedelta("1h")` 可解析（待 TODO 凍結前實跑確認三值皆可解析）」；我本次實跑 `pd.Timedelta("1h"/"4h"/"12h")` 均可解析。  
會怎麼失敗：SPEC 自身把未驗證內容放進「已查證」，違反反幻覺契約；下一位 agent 可能照樣寫「已驗證」但不留輸出證據。  
修法：§A 改成已驗證並貼實跑命令與輸出：`1h 0 days 01:00:00`、`4h 0 days 04:00:00`、`12h 0 days 12:00:00`。

2. [BLOCKING] High — Task 2.1 的 split 來源仍未決，且 CPCV/WF adapter 的多 fold 輸出與本刀「單一 OOS 報告」不相容  
證據：SPEC `:65-68` 明列「ML 孤島 adapter（CPCV/WF，多 fold）抑或單純時間順序 holdout」待決；`ic_split_adapter.py:41-50`、`:105-113` 回傳 `List[SplitPlanPair]`；SPEC `:80-84`、`:110-114` 又要求單一 train/test mask 與 test rows 報告。  
會怎麼失敗：實作者若選 adapter，會得到多個 folds，但 SPEC 沒定義 fold 聚合、選哪個 fold、summary/golden 如何合併；若選 holdout，又可能被認為違反「複用 ML 孤島」。  
修法：TODO 前寫死 cut1 採單一 chronological holdout；明定 train/test 比例或 train_window/test_window、purge/embargo、樣本不足處理與 mask 生成。CPCV/WF adapter 留 1e/Phase 2A。

3. [BLOCKING] High — 「所有清洗只用 train fit」漏掉 missing coverage 與 constant removal  
證據：SPEC 只要求 winsor/standardize train-only（`:88-107`）；現行 `DataPreprocessor.preprocess()` 在 winsor 後執行 `handle_missing()` 與 `remove_constant_features()`（`data_preprocessor.py:53-64`），其中 coverage 用全段 `filled.notna().mean()`（`:113-116`），constant 用全段 `df.nunique()`（`:120-124`）。  
會怎麼失敗：test 段缺失率或變異會決定 feature 是否被移除，形成 feature selection leakage；即使 winsor/standardize 修好，測試段仍影響候選集合。  
修法：Phase 3 增加 train-only `fit_mask` 對 `handle_missing` coverage 與 `remove_constant_features`；flag-off 保留全段舊路徑。

4. [BLOCKING] High — split mask 在 event_filter 後可能失效，SPEC 沒定義 row-filter 後的 mask 交集/重映射  
證據：`analyze()` 順序是 preprocessing `:114-115` → label `:117-120` → event_filter `:122-125`，event_filter 會 `features_df.loc[idx]` 改 row universe（`ic_filter_orchestrator.py:1096-1097`）；SPEC 要 ingestion 後、preprocessing 前產生 split（`:65-70`），並要求同一遮罩貫穿 stage（`:80-84`）。  
會怎麼失敗：event mode 下 pre-event mask 長度/row identity 與 post-event `features_df` 不一致，輕則 index error，重則 IC 用錯 train/test rows。  
修法：明定 base split 建在 stage0 full universe；stage3 row filter 後產生 derived test/train RowMaskPlan = split ∩ event rows，並驗證 base_universe_hash/row_index 對齊。

5. [BLOCKING] High — OOS 報告口徑不完整，Stage4/5 仍會混入全段衍生分析  
證據：SPEC 只說 `_stage4_ic_calculation/_stage5_statistical_validation` 對 test subset（`:110-121`）；現行 Stage4 除 `compute_ic/rolling_ic/icir` 外還算 `compute_ic_decay(features_df, close, ...)`（`ic_filter_orchestrator.py:1233-1242`）與 `compute_grouped_ic(features_df, label_series, raw_data, ...)`（`:1244-1251`）；Stage5 還用全 `features_df` 算 monotonicity/coverage/turnover（`:1284-1286`），summary 又納入 coverage/turnover/decay（`:1483-1522`）並 threshold coverage（`:1567-1570`）。  
會怎麼失敗：summary_table/passed_features 變成 IC 是 test，coverage/turnover/decay/grouped 是全段，報告口徑混雜，可能讓全段 coverage 決定 OOS passed_features。  
修法：flag-on 時所有進 summary/threshold/report 的 metrics 都明確用 test scope，或明確標 N/A 並禁止進 threshold。

### 10 類必查

1. 矛盾/互斥：  
[MAJOR] High — flag 預設策略前後矛盾。  
證據：BRIEF `:24` 說三方 PASS 後新算法預設開啟；BRIEF `:40` 又說「新算法一律藏在預設關閉的開關後」；SPEC `:126-128` 說初始 PR OFF，簽核後同 PR/緊接 PR ON。  
會怎麼失敗：實作者可能永久預設 OFF，或驗證前切 ON 破壞 G-OLD。  
修法：明確拆成「實作提交 default OFF → 簽核提交 default ON」，並保留顯式 off override 的 G-OLD 測試。

2. 漏項/端到端：見 findings 3、4、5。另 resume/retry 無新增狀態，單幣 cut1 可接受。

3. 不可測驗收：  
[MAJOR] Medium — G-OLD reference 仍含「取最新 hash」，不是凍結輸入。  
證據：SPEC `:35`「取 feature_library 最新 BTC/1h run hash，TODO 凍結前寫死」；現有 golden 目錄已有 `tests/golden/ic_phase1_contract/baseline_btc_1h.json` 與 input，但 cut1 新路徑 `baseline_old_btc_1h.json` 尚未定。  
會怎麼失敗：不同 agent/時間拿到不同 latest run，byte baseline 不可重現。  
修法：SPEC 直接引用固定 input path/hash 或要求 TODO 先凍結且 gate 不過不得派工。

4. 可疑 quant 假設：見 findings 2、3、5。holdout 切點選法目前未定，是 blocking。

5. 過度工程：  
[MAJOR] High — cut1 若引入 CPCV/WF adapter 是過度工程。  
證據：SPEC `:67` 把 CPCV/WF 多 fold 作為候選；本刀目標是單幣縱向 `analyze()` OOS 報告（manifest `:3`, `:29`）。  
會怎麼失敗：多 fold 聚合未定，增加正確性風險。  
修法：cut1 用單一 chronological holdout；adapter 留後續。

6. OOM/並行：無。未見新增巢狀並行要求。

7. Cache 正確性：  
[MINOR] Medium — G-NEW key 有 split 邊界，但 baseline path 未明確納入 symbol/tf/config_hash 命名規則。  
證據：SPEC `:37` 有 split boundary/hash 內容；`:139-142` 只寫同目錄 `baseline_new_btc_1h.json`。  
會怎麼失敗：多 config baseline 覆蓋或誤用。  
修法：檔名或 manifest 需含 symbol/timeframe/config_hash/split_id。

8. API/型別/相容：  
[MAJOR] Medium — config flag 落點模糊。  
證據：SPEC `:126` 寫 `momentum/Analysis/ic_config.py（或對應 config）+ api/core/config.py（如需 API 層）`；實際 `ic_config.py` 只是 re-export（`ic_config.py:1-8`），schema 在 `ic_config_schema.py`。  
會怎麼失敗：flag 可能接到 API env 而不進 `ICConfig.model_validate()`，或只在 engine schema 但 API 無法覆寫。  
修法：明確新增到 `ic_config_schema.ICConfig` 的哪個 section，並定義 API request `config_override` path。

9. 測試品質：  
[MAJOR] High — `test_single_symbol_universe_passed` 的「注入雜質 symbol row」在 `analyze()` 真實輸入上不可執行。  
證據：SPEC `:57-60` 要主流程傳 `{metadata["symbol"]}` 並注入雜質 symbol row；現行 feature HDF5 載入只形成 feature matrix + index（`ic_filter_orchestrator.py:993-1001`），metadata 只有全域 `symbol/timeframe`（測試 helper `test_ic_filter_orchestrator.py:73-75`），沒有 row-level symbol column。  
會怎麼失敗：測試只能造 synthetic symbols array，不會碰 `analyze()` 真實路徑；L4 allowlist 在 cut1 只能驗證 metadata symbol，不驗證 row-level contamination。  
修法：cut1 明確宣告 row-level cross-symbol contamination N/A，測試改為 metadata symbol missing/outside allowlist fail-closed；真正 row-level allowlist 留 multi-symbol/cut2。

10. Agent 可執行性：見 findings 2、6、8。每 task 大致有檔案/函式/不可做，但 unresolved decision 與 config 落點需修。

## holdout vs adapter 獨立裁決（你選哪個 + 理由）

我選 **單一 chronological holdout**。

理由：cut1 的產品語義是「單幣縱向主流程產出一份 OOS IC 報告」，不是模型選擇或多 fold validation。CPCV/WF adapter 會回傳多個 `SplitPlanPair`，目前沒有 fold 聚合、summary aggregation、golden freezing、UI/report 口徑。用 holdout 可以最小化 moving parts，同時仍能用既有 `SplitPlan`、`validate_split_pair_integrity`、expected_freq、allowed_symbols 紅線。CPCV/WF 留給 HAC/bootstrap、rolling OOS 或事件 OOS 更合理。

## 被當成事實的未驗證假設（逐一列）

- `pd.Timedelta("1h"/"4h"/"12h")` 可解析：SPEC 內未附實跑輸出，但我本次已驗證為真；需補回 SPEC。
- `主流程傳 allowed_symbols={metadata["symbol"]}` 能讓 L4 airtight：對 row-level cross-symbol 污染未驗證，因 `analyze()` 輸入沒有 row-level symbol；只能保 metadata-level allowlist。
- `只修 winsor/standardize 即等於清洗 train-only fit`：為假；missing coverage 與 constant removal 仍全段 fit。
- `split mask 可無損貫穿 preprocessing→event_filter→ic→stat`：未驗證且目前 event_filter 會改 row universe。
- `G-OLD baseline 可由 latest BTC/1h run 凍結`：未驗證且不 deterministic，需固定 input/hash/命令。

HANDOFF_NOT_UPDATED: read-only sandbox，依合約不寫 handoff 檔。  
STATUS: DONE