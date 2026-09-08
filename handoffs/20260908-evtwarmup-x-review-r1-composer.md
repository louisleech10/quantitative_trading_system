brief-kind: review
task-id: 20260908-EVTWARMUP-X-REVIEW-R1
family: composer
findings-round: R1
標的：`docs/EVTWARMUP_SPEC.md`、`docs/TFWINDOW_SPEC.md`、`docs/EVTWARMUP_TODO.md`（**尚未實作**）

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| 三份文件 template | **fact-verified** | `bash scripts/template_check.sh spec|todo` 三條 → TEMPLATE PASS, rc=0 |
| golden 探針 | **fact-verified** | `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` → `與既有 golden 相同？ **True**`；event `reason=rolling_warmup_insufficient test_rows=13`；global `analysis_status=ok_oos` |
| consult W1–W4 已收斂 | **fact-verified（brief）** | synth 已讀；本輪未重跑 consult |
| **`ASSUME-1`**：第三個 `analysis_status` 不破前端／survivor | **推翻** | `types.ts:2257` 兩值 union；`survivor_contract.py:456-461` 未知 status fail-closed；`normalize_analysis_status`（`:62-64`）未知字串→`degraded_full_sample` → P0-01／P1-01 |
| **`ASSUME-2`**：Task 1.2 只改 `normalize_analysis_status` 即可滿足 §G | **推翻** | `_stage7_report`（`:4014-4018`）由 `_resolve_root_status` 覆寫 root status，且該函式（`:1543`）僅兩值 → P0-01 |
| **`ASSUME-3`**：DegradedBanner `!== ok_oos` 足夠 | **部分成立** | banner 會顯示，但標題／正文寫死 full-sample 語意（`:47-51`）→ holdout+insufficient 會誤導 → P1-03 |
| stage6 tiebreaker 已有 ic_mean fallback | **推翻** | `redundancy_filter._score_value`（`:378-387`）tiebreaker=`icir` 且 NaN 時回 `-inf`，不會自動改讀 `ic_mean` → P2-01 |
| scan cube 110 格 reason 枚舉寫死 | **不成立** | `scan_cube.py` 透傳 cell `reason`；風險在 report／survivor 契約，非 cube 枚舉 |

---

## 必答（成對 verdict）

### 1a／1b 分流鍵可否被繞／誤擋

- **1a（主線逃 bar gate／事件當主線）**：**設計方向正確**（§C-3 禁 `event_filter.enabled` 單獨分流；mutation M2 已列）。**殘留繞道**：SPEC §C-3 與 TODO 1.1 邊界②對 `event_label_values={}` 矛盾——§C-3 以 `is not None` 判事件路徑，TODO 要求 `{}`⇒主線；若實作跟 SPEC，空 dict 仍 bypass warmup 但 stage3 未必產生 `label_source=event_label_value`（見 P1-02）。**fallback 重跑**：`_in_fallback_rerun` 內仍須套用同一分流（TODO 邊界③），SPEC §V M1 有 mutation 覆蓋，可執行。
- **1b（誤擋合法事件 run）**：**不會多擋**——現況是 34 測試段事件被 bar 規則誤擋；豁免後 13<30 走 `insufficient_test_events` loud 揭露，符合 consult W2。全域 34 **列**仍 fallback（SPEC Task 1.1 邊界②），與探針一致。

### 2a／2b 第三個 `analysis_status` vs 兩值契約

- **2a**：SPEC **已選**第三值 `degraded_insufficient_test_events`（Task 1.2），但**落地清單不完整且與現有守衛衝突**——`_resolve_root_status` 僅兩值、`test_resolve_root_status_behaviour_is_baseline` 斷言 `oos_guarantees=False⇒degraded_full_sample`（`test_gap3_oos_downgrade.py:102-115`）。僅改 `normalize_analysis_status` **不能**滿足 §G `analysis_status != "degraded_full_sample"`。見 P0-01。
- **2b**：若維持兩值、只用 `oos_downgrade.reason=insufficient_test_events` 區分，可避開 survivor／TS union 擴充，且與 `_resolve_root_status` 現形一致；但**與 SPEC §G 字面衝突**（已寫 `!= degraded_full_sample`）。兩值下 `degraded_full_sample` 對「holdout 已套用、僅事件統計不足」**確實誤導**（DegradedBanner 文案亦假設 full-sample，P1-03）。

### 3a／3b 跳過 `icir_min` 副作用／全域逐位元組

- **3a**：stage5 `:4248` 為主閘；stage6 `_stage6_redundancy`→`redundancy_filter.filter` 以 `tiebreaker`（預設 `icir`）排序，NaN 時 `_score_value` 變 `-inf` 可能靜默改變冗餘剔除順序（非炸掉，但非「不影響」）。`get_top_features`（`:2895`）預設 `sort_by="icir"` 未列入 Task 2.1 檔案表。見 P2-01。
- **3b**：**全域路徑可保持逐位元組不變**（§C-2＋§G global_run 探針）；會變的鍵限 **event_run**：`ic_train_test_split.*`、`analysis_status`、`oos_guarantees`、`oos_downgrade`、`n_summary_rows`、stage5 `removed` 鍵（`icir`→`icir_skipped_event_path`）、`ic_window_disclosure`；`facts.adjusted_windows_default` 本票不變。

### 4a／4b TFWINDOW golden 互斥／`test_oos_ic_rolling_warmup`

- **4a**：**可執行**——TODO §B 兩 batch 互斥 commit、TFWINDOW §C-3 禁同 commit；12h `test_gap2_golden` sha 不變＋1h 新 golden `rolling_keys_1h.json` 有 sha256 門檻。
- **4b**：**不構成改測試換綠**——SPEC／TODO 明訂依 fixture 週期**重算期望**（`window_5`→換算後鍵名／長度），並新增 1h golden receipt；刪斷言才算換綠。風險在測試直接呼叫 `_stage4_ic_calculation`（`:135`） bypass `analyze` 注入點，與生產路徑不同（P2-02），但不否定互斥 golden 策略。

### 5 ≥10× 不必要複雜

**無**。三 Task＋另票 TFWINDOW；無 queue／distributed。

### 6 可否進實作

**需修補後派工**。P0-01（第三 status 與 `_resolve_root_status`／gap3 基線測試／消費端清單）未決前，§G `analysis_status != degraded_full_sample` 與事件 survivor 落檔無法同時滿足。

---

## §1 必查摘要

| 類 | 結果 |
|---|---|
| 1 矛盾 | §C-3 vs TODO `{}`；§G vs `_resolve_root_status`／gap3 測試 → P0-01、P1-02 |
| 2 漏項 | survivor／types.ts／`_resolve_root_status` 未入 TODO → P1-01 |
| 3 不可測 | §G／mutation／探針可證偽；TFWINDOW 1h golden 有 sha256 |
| 4 quant | W2 holdout+事件地板方向正確；EW-RESID-3 地板 30 為 needs-research 成立 |
| 5–11 | 無過度工程；cache N/A；§N 三殘留理由成立（EW-RESID-1 user-ruling；2/3 needs-research） |

---

## COMPOSER-R1-P0-01

**斷言**: Task 1.2 要求 `analysis_status="degraded_insufficient_test_events"` 且 §G 斷言 `!= "degraded_full_sample"`，但 root status **寫入點** `_resolve_root_status`（`ic_filter_orchestrator.py:1543`）僅輸出 `ok_oos|degraded_full_sample`，`_stage7_report`（`:4014-4018`）會覆寫；TODO 未列此函式，且既有 `test_resolve_root_status_behaviour_is_baseline` 鎖定 `oos_guarantees=False⇒degraded_full_sample`。

**碼證**: SPEC Task 1.2／§G；`grep -n "_resolve_root_status\|degraded_insufficient" docs/EVTWARMUP_TODO.md momentum/Analysis/ic_filter_orchestrator.py` → TODO 無前者、orchestrator 無後者；`tests/api/test_gap3_oos_downgrade.py:102-115`。RECHECK: 實作後跑 `pytest tests/api/test_evtwarmup.py -k min_test_events` 並斷言 `analysis_status=="degraded_insufficient_test_events"`；同跑 `test_gap3_oos_downgrade` 參數化基線——須**先改 SPEC**訂明新 metadata 形狀下 status 三分支，再更新測試。

**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6

[BLOCKING] 信心度=High。修法：SPEC Task 1.2 增寫入點 `_resolve_root_status`／`_annotate_root_status_and_pass_class` 分支表（holdout+`insufficient_test_events`→第三值；full-sample fallback→`degraded_full_sample`）；TODO 檔案表加入 orchestrator 該兩函式＋`tests/api/test_gap3_oos_downgrade.py` 基線更新；§G 與 mutation 同步。若委員會改採「兩值+reason」則須**回寫** §G 刪 `!= degraded_full_sample` 斷言（二選一，不可雙軌）。

---

## COMPOSER-R1-P1-01

**斷言**: 第三 `analysis_status` 之消費端清單在 TODO Task 1.2 不完整——`survivor_contract.build_survivor_output`（`:456-461`）與 `ic_report_contract.json` notes（兩值契約）及 `frontend/src/lib/types.ts:2257` 未列修改，事件 conditional run 落 survivor 將 fail-closed。

**碼證**: `rg "ok_oos|degraded_full_sample" momentum/Analysis/survivor_contract.py frontend/src/lib/types.ts momentum/Analysis/contracts/ic_report_contract.json`；TODO Task 1.2 檔案表（`docs/EVTWARMUP_TODO.md:33`）無上述三處。RECHECK: 實作後對 la0 事件 run 跑 `build_survivor_output` 單測或 `pytest tests/momentum/Analysis/test_survivor_contract.py`。

**來源摘要**: docs/EVTWARMUP_TODO.md#baf86b01c118

[MAJOR] 信心度=High。修法：TODO Task 1.2 補 `survivor_contract.py`、`contracts/ic_survivor_contract.json`（若擴枚舉）、`types.ts` ICReport union、`ic_report_contract.json` notes；或 SPEC 明訂第三值**僅 IC report root、survivor 仍 mirror 兩值**（須寫清映射規則，禁靜默 normalize）。

---

## COMPOSER-R1-P1-02

**斷言**: SPEC §C-3 分流條件含 `event_label_values is not None`，與 TODO Task 1.1 邊界②「`event_label_values={}` 視同 None（主線）」互斥；實作者無法同時滿足兩份文件。

**碼證**: `docs/EVTWARMUP_SPEC.md` §C-3；`docs/EVTWARMUP_TODO.md` Task 1.1 邊界②；現碼 `event_label_values is not None` 於 `defer_alignment_error`（`ic_filter_orchestrator.py:1076`）。RECHECK: 對 `{}` 輸入寫分流單測，預期主線仍觸發 precheck details。

**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6

[MAJOR] 信心度=High。修法：統一為 `event_label_values` 非空 dict（或 stage3 後 `label_source==event_label_value`）才 bypass；§C-3 改寫與 TODO 一致。修訂：SPEC §C-3、Task 1.1 邊界、`_is_event_conditional_path` 偽碼。

---

## COMPOSER-R1-P1-03

**斷言**: Task 1.2 後 holdout 已套用、`insufficient_test_events` 之路徑仍會觸發 DegradedBanner，但元件標題與正文寫死「Full-sample research-only／full-sample fallback」（`DegradedBanner.tsx:47-51`），與 consult W2「仍在 holdout 算點 IC」矛盾，使用者會以為沒有測試集。

**碼證**: `frontend/src/components/ic-analysis/DegradedBanner.tsx:37-51`；`oosDowngradeDocs.ts` 無 `insufficient_test_events` 鍵（TODO 僅列加文案）。RECHECK: 實作後 vitest `DegradedBanner.test.tsx` 對新 reason 斷言標題**不含** full-sample 字面。

**來源摘要**: frontend/src/components/ic-analysis/DegradedBanner.tsx#948bd7a9a5dd

[MAJOR] 信心度=High。修法：TODO Task 1.2 增 DegradedBanner 依 `oos_downgrade.reason` 分流標題（holdout+事件不足 vs 真 full-sample）；`insufficient_test_events` 顯示 `test_events/min_test_events`（TODO 已列，需含 banner 主標）。

---

## COMPOSER-R1-P2-01

**斷言**: Task 2.1 稱 stage6 tiebreaker「缺 ICIR 走 `ic_mean`」，但 `redundancy_filter._score_value` 在 tiebreaker=`icir` 且值 NaN 時回 `-inf`，不會 fallback 讀 `ic_mean`；冗餘剔除順序可能與改前不同且未釘測試。

**碼證**: `momentum/Analysis/redundancy_filter.py:378-387`；SPEC Task 2.1／TODO Task 2.1 未列 `redundancy_filter.py`。RECHECK: 事件路徑 34 事件跑 stage6，比對 `redundancy_log.removed_features` 與改前（允許差異則 SPEC 須寫「順序可變」）。

**來源摘要**: momentum/Analysis/redundancy_filter.py#5f57224be356

[MINOR] 信心度=Medium。修法：Task 2.1 補 `_score_value` 或傳入 event-path 時 tiebreaker_effective=`ic_mean` 之檔案行；或降級為「診斷揭露 only、stage6 順序不保證」並寫入 §V。

---

## COMPOSER-R1-P2-02

**斷言**: TFWINDOW Task 3.1 驗收含 `test_oos_ic_rolling_warmup`，但該測試直接呼叫 `_stage4_ic_calculation`（`test_ic_1a_cut1_oos.py:135`），不經 `analyze` 的 `set_timeframe` 注入——與生產路徑不一致，可能「測試綠、接線漏」。

**碼證**: `tests/momentum/Analysis/test_ic_1a_cut1_oos.py:129-155`；TFWINDOW TODO Task 3.1 驗證表。RECHECK: Task 3.1 另增 `tests/api/test_tfwindow.py` 整合路徑覆蓋 rolling 鍵（TODO 已有，需標為主驗收）。

**來源摘要**: docs/TFWINDOW_SPEC.md#6dc2c594ede4

[MINOR] 信心度=Medium。修法：TFWINDOW §G 註明 `test_oos_ic_rolling_warmup` 為引擎層回歸、`test_tfwindow.py` 為接線主 gate；或改測試經 `analyze` 薄封裝。

---

## Verdict：需修補後派工

P0-01 為 §G 與現有 gap3 status 基線之結構矛盾，必先改 SPEC／TODO 訂明 `_resolve_root_status` 三分支與測試更新，並決定第三值是否擴及 survivor／TS。P1 補分流 `{}` 統一、消費端清單、DegradedBanner 文案後可進 B1。TFWINDOW 互斥 golden 策略可執行；EW-RESID 三殘留理由成立。

---

## VERIFY（本輪實跑）

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/EVTWARMUP_SPEC.md` | TEMPLATE PASS, rc=0 |
| `bash scripts/template_check.sh spec docs/TFWINDOW_SPEC.md` | TEMPLATE PASS, rc=0 |
| `bash scripts/template_check.sh todo docs/EVTWARMUP_TODO.md` | TEMPLATE PASS, rc=0 |
| `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` | `與既有 golden 相同？ **True**`, rc=0 |
| `rg "degraded_full_sample\|ok_oos" frontend/src api/ momentum/Analysis/*.py` | 見 P0-01／P1-01 碼證 |
| `rg "icir" momentum/Analysis/ic_filter_orchestrator.py momentum/Analysis/redundancy_filter.py` | stage5 `:4248`；tiebreaker `_score_value` |

---

ASSUMPTIONS_VERIFIED: 模板三 PASS；探針 True；ASSUME-1/2 推翻（讀碼）；分流／ICIR 消費者 grep
TESTS_RUN: 見 VERIFY 表（未跑 `pytest tests/governance`）
FAILURES_SEEN: none
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查；標記 event_run golden 預期變更已於 SPEC §G）
產出檔: handoffs/20260908-evtwarmup-x-review-r1-composer.md

STATUS: DONE
