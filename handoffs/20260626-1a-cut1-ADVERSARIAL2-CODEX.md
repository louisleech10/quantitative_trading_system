## Verdict：需修補後派工

## 第一輪 4 BLOCKING 修補核對（逐一：已解決/未解決/部分 + 證據）

- [BLK-1] timestamp identity 遮罩重導：**部分，仍不可派工**。SPEC/TODO 已要求 event_filter 後用 timestamp membership 重導遮罩（`docs/IC_PHASE1_1a_CUT1_SPEC.md:81-86`, `docs/IC_PHASE1_1a_CUT1_TODO.md:77-84`），方向正確；但現有契約 `SplitPlan.index_kind="timestamp"` 只是 enum，`validate_split_integrity()` 與 pair validator 仍把 `plan.row_index` 強制當 positional int 使用（`momentum/core/contracts.py:504-537`, `:559-583`）。TODO 又寫 `SplitPlan(index_kind="timestamp", row_index=<timestamp 或可映射>)`（`docs/IC_PHASE1_1a_CUT1_TODO.md:62`）。若實作者真的放 timestamp，會 cast/index 失敗；若放 positional，又與文件凍結的 timestamp identity 契約矛盾。  
- [BLK-2] purge_gap >= label horizon：**部分**。SPEC/TODO 已要求 `purge_gap >= horizon`（`docs/IC_PHASE1_1a_CUT1_SPEC.md:74-79`, `docs/IC_PHASE1_1a_CUT1_TODO.md:68-75`），且 `test=idx[split_point+purge_gap:]` 可形成 dead-zone；但「實際 label horizon」取得仍未定義完整。現行 `_stage2_label_generation()` 會在 default horizon 不在 configured horizons 時 fallback 到 `labels.horizons[0]`（`momentum/Analysis/ic_filter_orchestrator.py:1048-1051`），而 TODO 只說取 `config...default_horizon=5`（`docs/IC_PHASE1_1a_CUT1_TODO.md:71`）。config override 改 horizons 時，purge 可能綁錯 horizon。  
- [BLK-3] handle_missing/remove_constant train-only：**部分，修補點有列齊但 pipeline 依賴未解**。四個全段 fit/selection 路徑都被 TODO 覆蓋（`docs/IC_PHASE1_1a_CUT1_TODO.md:88-126`），對應現行洩漏點存在（`momentum/Analysis/data_preprocessor.py:43-70`, `:107-138`, `:144-172`）。但現行 `analyze()` 是 stage1 preprocessing 先跑，stage2 label 才跑（`momentum/Analysis/ic_filter_orchestrator.py:114-120`）；TODO 要 `_stage1_preprocessing` 用 split train mask（`docs/IC_PHASE1_1a_CUT1_TODO.md:120-126`），而 split 又依賴 Task 2.2 的 actual horizon。文件未指定要把 split/horizon resolution 前移到 stage1 前，冷啟動實作會卡在依賴倒置。  
- [BLK-4] D-3 全 stage5 指標 OOS：**部分**。stage5 summary/threshold 指標已要求 OOS（`docs/IC_PHASE1_1a_CUT1_SPEC.md:139-144`, `docs/IC_PHASE1_1a_CUT1_TODO.md:146-152`），能覆蓋現行全段 monotonicity/coverage/turnover（`momentum/Analysis/ic_filter_orchestrator.py:1284-1302`, `:1483-1570`）。但 stage6 redundancy 仍明列為 cut1 informational/N/A（`docs/IC_PHASE1_1a_CUT1_SPEC.md:201`），而現行 stage6 用 `features_df[passed_features]` 全段 correlation/filter 產生最終 `filtered_df`（`momentum/Analysis/ic_filter_orchestrator.py:1315-1347`）。若最終可用特徵看 filtered output，不只是 passed_features，仍會混入非 OOS 口徑。

## Findings（[BLOCKING|MAJOR|MINOR] + 信心度 + 證據(檔:行/章節) + 會怎麼失敗 + 修法；挑戰前提置頂）

[BLOCKING] 高信心 — `SplitPlan.index_kind="timestamp"` 契約是紙面支援，現有 validator 仍 positional-only。  
證據：TODO 要 `index_kind="timestamp"` 且 `row_index=<timestamp 或可映射>`（`docs/IC_PHASE1_1a_CUT1_TODO.md:62`）；`SplitPlan` enum 允許 timestamp（`momentum/core/contracts.py:360-365`），但 validator 立刻 `np.asarray(plan.row_index, dtype=int)` 並用作 array position（`momentum/core/contracts.py:504-537`, `:570-583`）。  
失敗模式：實作者照 TODO 放 DatetimeIndex 會在 dtype cast / bounds / array indexing 失敗；改放 int position 則 event_filter 後重導遮罩的「timestamp identity」不再是契約層保證，BLK-1 未真正修完。  
修法：明確二選一。要嘛本刀仍用 positional `row_index`，另用 timestamp set/time_bounds 做 `_derive_stage_masks`，並把 SPEC/TODO 全部改掉 `index_kind="timestamp"`；要嘛把 `validate_split_integrity`、pair validator、`_time_bounds_for_indices`、`RowMaskPlan.to_mask` 補成真正 timestamp-aware，並新增 timestamp row_index contract tests。

[BLOCKING] 高信心 — split/train mask 依賴順序未定義，Task 3.5 冷啟動不可執行。  
證據：現行 `analyze()` stage1 preprocessing 在 label generation 前（`momentum/Analysis/ic_filter_orchestrator.py:114-120`）；Task 3.5 要 stage1 接 split train mask（`docs/IC_PHASE1_1a_CUT1_TODO.md:120-126`）；Task 2.2 又說 purge 取「實際 label horizon」（`docs/IC_PHASE1_1a_CUT1_SPEC.md:74-79`）。  
失敗模式：實作者不知道 split helper 應插在 stage0 後、stage1 前，還是 stage2 後重跑 preprocessing；前者可能拿不到 actual label horizon，後者會先用全段 preprocessing，已經洩漏。  
修法：新增明確 orchestration task：在 stage0 後先解析 actual horizon（共用 `_stage2_label_generation` 的 fallback 規則或抽 helper），再建立 split，再把 train mask 傳入 stage1；禁止先全段 preprocess 再補 mask。

[BLOCKING] 高信心 — G-OLD baseline 前置不可執行：指定 script 不存在，config_hash 仍是 placeholder。  
證據：SPEC/TODO 要 `python scripts/freeze_baseline.py --symbol BTC --timeframe 1h --config-hash <寫死>`（`docs/IC_PHASE1_1a_CUT1_SPEC.md:35-37`, `docs/IC_PHASE1_1a_CUT1_TODO.md:164-170`）；repo 內沒有 `scripts/freeze_baseline.py`，只有 `tests/golden/ic_phase1_contract/freeze_baseline.py` 與其他 freeze scripts（`rg --files scripts | rg 'freeze|baseline'` 未列該檔）。  
失敗模式：dispatch gate 要求動工前凍 G-OLD，但執行端拿 TODO 會直接找不到命令；若自行改用別的 script 就違反 scope/反幻覺。  
修法：在 Frozen 前補真實可執行命令與固定 config_hash，或新增/指定正確 freeze script；TODO 不能保留 `<寫死>`。

[MAJOR] 高信心 — OOS rolling IC 語義未定義，`oos_test_size=0.2` 可能產生空 rolling/p-value NaN 而非可用 OOS 報告。  
證據：TODO 只說 flag on 對 test subset 算 rolling IC（`docs/IC_PHASE1_1a_CUT1_TODO.md:130-136`）；`compute_rolling_ic()` 若 rows < window 回空矩陣（`momentum/Analysis/ic_engine.py:268-302`, `:1293-1295`）；default rolling windows 是 `[21,63,126]`（`momentum/Analysis/ic_config_schema.py:64-68`）；p-value 從 rolling values 收集（`momentum/Analysis/statistical_validator.py:24-31`, `:75-80`）。  
失敗模式：短 OOS slice 下 rolling_ic 空、icir/p-value NaN，threshold 全 fail 或報告退化，但測試只看「用了 test rows」可能仍綠。  
修法：SPEC/TODO 定義 OOS 最小樣本規則：test rows 必須 >= max adjusted rolling window 或明確降窗策略；不足時 fail-closed `SkippedResult`/錯誤，並加入真實 BTC/1h/4h/12h coverage 測試。

[MAJOR] 中高信心 — actual horizon fallback 未納入 purge 測試。  
證據：現行 label horizon 可能 fallback：`if horizon not in labels_cfg.horizons: horizon = labels_cfg.horizons[0]`（`momentum/Analysis/ic_filter_orchestrator.py:1048-1051`）；TODO 只驗 horizon 變動/缺失，未驗 default 不在 horizons（`docs/IC_PHASE1_1a_CUT1_TODO.md:68-75`）。  
失敗模式：config override 設 `global.default_horizon=5`、`labels.horizons=[13]` 時，label 用 13、purge 仍可能是 5，前瞻洩漏回來。  
修法：抽 `_resolve_effective_label_horizon(config, labels_df)`，split 與 label generation 共用；新增 default not in horizons 的反例測試。

[MAJOR] 中信心 — final filtered output 的 redundancy 仍是全段口徑，與「OOS 報告」語義不自洽。  
證據：SPEC 把 `stage6 redundancy 全段→OOS` 登記為 informational/N/A（`docs/IC_PHASE1_1a_CUT1_SPEC.md:201`）；但現行 stage6 會用全段 `features_df[passed_features]` filter 並寫入 `filtered_df`/report metadata（`momentum/Analysis/ic_filter_orchestrator.py:1315-1347`, `:1394-1409`）。  
失敗模式：passed_features 是 OOS，最後 exported/filtered features 可能因 train+test 全段 correlation 被移除或保留，最終使用者看到的 feature set 不是純 OOS 口徑。  
修法：若 cut1 不做 stage6 OOS，則 flag-on 報告必明確區分 `passed_features_oos` 與 `filtered_features_full_sample_redundancy`，且 default selection 不得宣稱全 OOS；更乾淨是 stage6 redundancy 在 flag-on 只對 test subset 做或不影響最終 OOS passed set。

[MAJOR] 高信心 — TODO 冷啟動仍有不可複製驗證命令。  
證據：多數 Task 驗證使用 `pytest ...::test_*` placeholder（例如 `docs/IC_PHASE1_1a_CUT1_TODO.md:55`, `:66`, `:75`, `:84`, `:136`, `:152`, `:178`），而 prompt 要 §B 批次派工 prompt 可直接複製。  
失敗模式：headless executor 需自行猜測 test file/function，違反「沒讀過 SPEC 拿了就能寫」與 scope 合約；也會讓 gate/驗收無法機械執行。  
修法：每個 Task 或每批次給完整 pytest nodeid；不存在的新測試也要給確定新檔名與函式名。

[MINOR] 中信心 — Task 5.1 說改 `api/services/ic_analysis_service.py`，但現有 config_override 已可 deep-merge，是否需要改服務未說清。  
證據：service `_build_config_override()` 回傳 dict，orchestrator `_apply_config_override()` 用 `ICConfig.model_validate` merge（`api/services/ic_analysis_service.py:1061-1097`, `momentum/Analysis/ic_filter_orchestrator.py:1828-1835`）；TODO 仍列服務修改檔（`docs/IC_PHASE1_1a_CUT1_TODO.md:156-162`）。  
失敗模式：執行端可能做無必要 API churn，增加 flag-off byte diff 風險。  
修法：若只需透傳 arbitrary config_override，刪除服務改檔；若要前端/模型顯式欄位，補 API model/task。

§1 必查 10 類摘要：  
1. 矛盾/互斥：有，timestamp SplitPlan 與 validator positional-only；stage1 mask 與 split/horizon 順序矛盾。  
2. 漏項/端到端：有，G-OLD freeze script/config_hash 缺。  
3. 不可測驗收：有，多處 `pytest ...` placeholder；G-OLD 命令不可跑。  
4. 可疑 quant 假設：有，rolling OOS window/test_size 未定義；actual horizon fallback 未處理。  
5. 過度工程：無 blocking；`_derive_stage_masks` 本身合理，但契約需收斂。  
6. OOM/並行：無，新路徑未引入巢狀並行。  
7. Cache 正確性：非 blocking；`_ic_cache` 每次 report 覆寫，但 split/default flag metadata 應在 report/golden 中固定。  
8. API/型別/相容：有 minor，service 是否需改不清。  
9. 測試品質：有，真實 kline 要求存在，但 nodeids/fixture path 未完整可執行。  
10. Agent 可執行性：未達標；B2/B3/B5 會讓 cold-start executor 卡住或越界猜測。

## 被當成事實的未驗證假設（逐一；無則「無」）

- 「`SplitPlan.index_kind='timestamp'` 與既有 positional 契約相容」未驗證，且讀碼證據顯示目前不相容。
- 「Task 3.5 可在不改 pipeline 順序下取得 train fit mask」未驗證，且現行 stage order 反證。
- 「`scripts/freeze_baseline.py` 可用」未驗證，repo 內未找到該 script。
- 「`oos_test_size=0.2` 對所有 crypto/timeframe 足以支撐 rolling IC/icir/p-value」未驗證。
- 「purge 取 default_horizon 就等於實際 label horizon」未驗證，現行 fallback 可能推翻。

STATUS: DONE