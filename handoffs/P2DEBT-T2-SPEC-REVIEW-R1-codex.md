# P2DEBT-T2 SPEC REVIEW R1 — codex
Task-id: p2debt-t2 | Date: 2026-07-11 | Mode: read-only adversarial（未讀其他 reviewer 產物）
## Receipts
- R1 `git status --short`：開工前已有 `.claude/*`、golden 5 檔及本票草稿/任務/交接未提交；本審不碰這些既有變更。
- R2 `rg -l --glob '*.py' '\.(analyze|start_analysis|refilter)\(' tests | sort` + targeted `rg -n`：除草稿 P0/P1 外，抓到 split/oos 漏網、3 個 generator、model 與 FF 真 persist；明細見表。
- R3 `rg -n '_persist_outputs\(' momentum/Analysis/ic_filter_orchestrator.py` + `sed -n '2780,2845p;3160,3210p' ...`：每次成功 longitudinal `analyze()` 都呼叫 `_persist_outputs`；report/filter-log 固定傳 `data_cache/reports`。
- R4 無落盤 spy 實跑：只 patch `_resolve_filtered_path` 後呼叫 `_persist_outputs(empty dfs,...)`，stdout=`[('report','data_cache/reports'),('filter','data_cache/reports')]`；故單一路徑 patch 攔不住 report。
- R5 `inspect.signature(...)` 實跑：`_persist_outputs(self,features_df,filtered_df,report,metadata,filter_log)`、`_materialize_features_for_ic(self,symbol,timeframe,config_hash)`、`_write_ic_meta_json(...feature_names=None)`，三者皆無 output root 注入點。
- R6 `/tmp` 同尺寸覆寫反例實跑：`AAAA→BBBB` 後 `(relative_path,size)` 前後皆 `('artifact.bin',4)`，`snapshot_diff=False`；證明草稿允許的 path+size oracle 假綠。
- R7 未跑 pytest body（禁止寫 production cache）；未跑 `--collect-only`，因 `tests/conftest.py::pytest_collection_modifyitems` 會寫 `tests/golden/l65/test_inventory.txt`，違反本次只准寫 review。

## 測試/寫入路徑對照（靜態可確證全集中的草稿覆蓋缺口）
| 類別 | caller / 寫入 | 草稿狀態 | 判定 |
|---|---|---|---|
| IC 已列 | cut1 golden×2、oos fallback/applied、e2e normal 4 + env-gated perf、feature-filter×1 → filtered H5 + reports | 部分列入 | 需逐 nodeid 寫死，不能只寫檔/class |
| IC 漏網 | `test_ic_1a_cut1_oos::test_flag_toggles_path`（成功 analyze×2）；`test_ic_1a_cut1_split::test_pipeline_order_split_before_preprocessing`（stage7 stub 後仍 persist reports） | 未列 | **漏一個即阻塞** |
| Service materialize | `test_ic_analysis_service` 兩 nodeid → `reports/ic_ingest_cache/*.{h5,json}` | 已列 | API subtree 無法取得 `tests/momentum/conftest.py` fixture |
| Model 真 persist | `test_lightgbm_analyzer.py`、`test_lightgbm_edge_cases.py`、`test_xgboost_protocol_methods.py`、兩個 phase3 檔 → `data_cache/models/*.pkl` | Phase 4/另票 | 任務要求全 `tests/`，不可在同一 SPEC 宣稱全集後 N/A |
| FF 真 service 路徑 | `tests/test_feature_factory_e2e.py` 多個真 `generate_features()`；production default `persist=True` + default `FeatureStorage('data_cache/features')` | 誤列為「多數只讀」且未納 scope | 冷 cache/force path 可寫 features，BLOCKING |
| tests/ generator | `fixtures/gen_ic_run_selector_baseline.py`、`golden/ic_phase1_contract/freeze_baseline.py`、cut1 `freeze_baseline*.py` → materialize/persist reports；另寫 baseline | 只列 cut1 兩支且僅「文件化」 | 漏 contract/run-selector；需明確手動 hermetic contract |

## Findings
- **B1 BLOCKING — 覆蓋表非全集。** 上表至少漏 split、oos、FF、model、兩類 generator；Phase 4 延後與任務「全 tests/ 漏一個即 BLOCKING」衝突。R2/R3 可重放。
- **B2 BLOCKING — redirect 設計不可執行且掛載未閉合。** marker 本身不會 request fixture；Analysis conftest 不覆蓋 momentum 根，momentum conftest 不覆蓋 API。硬編碼 local `Path` 無注入參數；wrap 若重寫 method 會複製 production 語意，若 `chdir(tmp)` 則 golden 的相對 `BASELINE_PATH/FEATURES_PATH` 會 skip/找不到。須寫死可執行 patch seam、`usefixtures`/參數掛載及 API plugin 路徑，並逐一路徑 spy 斷言 production prefix 從未收到。
- **B3 BLOCKING — §V 可假綠。** 單一 pytest test 不會包住另一次 V1 suite；path+size 漏同尺寸覆寫（R6）；pre/postflight 只擋「縮減」，新增/同尺寸覆寫可過；V4 又允許「expected fail 或 xpass」未定義 exit contract。須用同一外層 harness 的 before/after per-file digest（或明確等價強 oracle），mutation 同檔自證 baseline 綠→撤 redirect 被 oracle 捕捉→還原綠，且全程只寫 tmp substitute；V1/V2 禁 skip 冒充 0 failed。
- **B4 BLOCKING — golden 契約目前只有條件式聲稱。** 正確的純 path-argument redirect 不必改 in-memory report，故目前不判定「必然」聯合票 5；但草稿未提供該 seam，且 chdir/複寫 method 會改測試行為。須加 redirect 前後 normalized result exact/hash 的同輸入 A/B oracle，並驗證兩個 golden nodeid 真 `passed` 非 skip；否則不得聲稱票 5 邊界成立。
- **B5 BLOCKING — suite 漂移 gate 無效。** Task 1.2 的 collect-only `grep -c ic_persist_redirect == 0` 不能證明 fixture 未執行，且本 repo collect-only 自身寫 inventory。須以 spy/canary 證明未 opt-in governance/其他 momentum/API nodeid 不觸 redirect，opt-in nodeid 每條落盤 seam 都觸發；不得 root autouse。
- **B6 BLOCKING — RISK 大小錯。** `RISK-HIT: a,b` 判定準確；但任一 (a)/(b) 已依專案規則屬「大」，且派工明示已升大，草稿仍寫「中」，缺大任務白話/manifest 與相應雙家族閉合條款。
- **M1 MINOR — §G/V 內部矛盾。** §G 宣稱 normalized SHA exact/`2 passed`，V1 只要求 `0 failed` 且沒有 SHA 命令，缺 baseline 時 2 skip 仍可綠；須統一成可機掃的 passed-count + digest receipt。
Verdict: BLOCK — B1–B6：全集、可執行 redirect seam、可證偽 hermetic/mutation、golden 邊界、隔離 gate 與大任務分級均未閉合
