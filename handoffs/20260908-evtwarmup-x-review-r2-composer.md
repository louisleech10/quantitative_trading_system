brief-kind: review
task-id: 20260908-EVTWARMUP-X-REVIEW-R2
family: composer
findings-round: R2
標的：`docs/EVTWARMUP_SPEC.md`（R1 修訂）、`docs/EVTWARMUP_TODO.md`、`docs/TFWINDOW_SPEC.md`（**仍未實作**）

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| 三份 template | **fact-verified** | `bash scripts/template_check.sh spec|todo` 三條 → TEMPLATE PASS, rc=0 |
| golden 探針 | **fact-verified** | `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` → `與既有 golden 相同？ **True**` |
| R1 synth V1–V6 已落檔 | **fact-verified** | `git diff b96428f2..HEAD -- docs/EVTWARMUP_*.md docs/TFWINDOW_SPEC.md` 252 行；§C-3/§C-4/§G/Task 2.1 與 synth 逐條對照 |
| 方案 B 下 banner+EW-RESID-4 足夠 | **部分成立** | DegradedBanner 已列 reason 分流（Task 1.2）；`MarginalICTable`／`generate_ai_json` 仍寫死 full-sample 語意 → P2-02 |
| `pass_class` 下游不誤導 | **assumed（本輪 grep）** | `rg pass_class momentum api frontend/src` → 寫入點 `_annotate_root_status_and_pass_class`；前端 `MarginalICTable` 讀 `pass_class` 字面；契約 notes 已文件化鏡像語意 |

---

## R1 原提出方 CLOSED／OPEN（1a）

| R1 ID | 判定 | 修訂後文件位置／反例 |
|---|---|---|
| **COMPOSER-R1-P0-01** | **CLOSED** | 採方案 B：`docs/EVTWARMUP_SPEC.md` §C-4「維持兩值契約」；§G `event_run` 斷言 `analysis_status=="degraded_full_sample"`＋`oos_downgrade.reason=="insufficient_test_events"`；Task 1.2「不新增 status 值」 |
| **COMPOSER-R1-P1-01** | **CLOSED** | 第三值撤回；Task 1.2 邊界④「survivor 不改（status 仍兩值）」；§C-4 明訂 survivor／TS union 一字不改 |
| **COMPOSER-R1-P1-02** | **CLOSED** | §C-3 兩段判：`bool(event_label_values) and enabled`＋`label_source=="event_label_value"`；Task 1.1 驗證 (c)(d)(e)；§V M2–M4 |
| **COMPOSER-R1-P1-03** | **CLOSED** | Task 1.2／TODO 1.2：`DegradedBanner.tsx` 依 reason 分主標；vitest 主標不含「Full-sample」 |
| **COMPOSER-R1-P2-01** | **CLOSED** | Task 2.1：事件路徑 `tiebreaker="ic_mean"`；`redundancy_filter.py` 不改；reporter `_finite_or_neg_inf` |
| **COMPOSER-R1-P2-02** | **CLOSED** | `docs/TFWINDOW_SPEC.md` §G「引擎層回歸 vs 接線主 gate」；TODO 3.1 mutation M9 主 gate 紅／引擎層綠 |

**1b 閉合是否製造新矛盾（SPEC↔TODO）**：**有兩處殘留**——(1) Task 1.2 地板判定時點寫「切分後、預檢後」但未限定 `_is_event_conditional_consumed`，與 Task 1.1 驗證 (e) 衝突（P1-01）；(2) Task 1.2 新增第三個 `oos_downgrade` 寫出點，但驗收要求整檔 `test_gap3_oos_downgrade.py` 綠且未列更新 `test_oos_downgrade_has_exactly_two_write_sites`（P1-02）。其餘 SPEC↔TODO 分流／ICIR／golden 互斥一致。

---

## 必答（成對 verdict）

### 2a／2b 方案 B 下「只看 status／pass_class 字面」消費端

- **2a**：**仍有誤導風險，但已文件化可接受邊界**。`analysis_status` 仍 `degraded_full_sample`；`pass_class` 仍 `full_sample_research_only`（`ic_filter_orchestrator.py:1570-1571`）。前端 `MarginalICTable.tsx:48-62` 在 `oos_guarantees===false` 時固定印「Full-sample research-only」；`ic_reporter.generate_ai_json`（`:598-604`）對一切 degraded 插入「full-sample fallback」警語——holdout+`insufficient_test_events` 會被誤讀（P2-02）。**不讀 reason 的決策消費者**：grep 未見 export／survivor 依 `pass_class` 分支；survivor validate 只檢查兩值配對（`:271-277`）。
- **2b**：**最小修法仍在本票**：§C-4 已選文案／notes 路徑；P2-02 建議 Task 1.2 補 `MarginalICTable` reason 分流（或讀 `metadata.oos_downgrade.reason`），不必擴枚舉。

### 3a／3b 兩段分流

- **3a**：**預檢＋stage4 兩段判在文件層不可再靠 `is not None` 繞**（§C-3、M2–M4）。**殘留**：Task 1.2 若用 precheck 旗標在 stage3 前寫地板，case (e) 可能先被標 `insufficient_test_events` 再進 mainline（P1-01）。
- **3b**：**不會多擋合法事件 run**——34 測試段事件 precheck+consumed 雙真仍豁免；scan cube「每格各自判定」（Task 1.1 邊界③）；fallback 重跑 predicate 重算。case (e) 應走 bar 規則，但地板時點寫錯會誤標（見 P1-01）。

### 4a／4b Task 2.1 ICIR

- **4a**：**reporter 三處已列**；stage6 呼叫端已列。**漏列**：`ic_filter_orchestrator.get_top_features`（`:2903-2907`，`sort_by` 預設 `icir`；`icir=None` 時 `item.get("icir",-inf)` 回 `None` ⇒ `sorted` TypeError）——違反 SPEC §C-6「TODO 逐一列出」（P2-01）。
- **4b**：**全域順序不變**——TODO 2.1 明訂 `_finite_or_neg_inf` 且「既有值皆有限」；`test_gap2_golden`／探針 `global_run` 逐鍵鎖。事件路徑 `icir=null` 不進 byte-locked global golden。

### 5 ≥10× 不必要複雜

**無**。B1 三 Task + 獨票 B2；無 queue／framework。

### 6 可否進 B1 實作

**需修補後派工**。P1-01（地板判定時點／predicate）與 P1-02（gap3 寫出點基線測試）為文件層自相矛盾，實作者照 TODO 字面會紅測或誤標 case (e)。P2 可並行修文案／消費端清單。

---

## §1 必查摘要

| 類 | 結果 |
|---|---|
| 1 矛盾 | Task 1.2 時點 vs 1.1(e)；gap3 兩寫出點 vs 第三寫出點 → P1-01、P1-02 |
| 2 漏項 | `get_top_features`、MarginalICTable／AI JSON 文案 → P2-01、P2-02 |
| 3–11 | 其餘無新 BLOCKING；§N 殘留理由仍成立；mutation／golden 可證偽 |

---

## COMPOSER-R2-P1-01

**斷言**: Task 1.2 地板判定寫在「切分後、預檢後」且條件為未定義的 `event_conditional`，實作者若在 stage3 前執行，會對 Task 1.1 驗證 (e)（values 非空＋enabled 但 `n_events<min_events` ⇒ `label_source=mainline_return_N` ⇒ stage4 仍 bar skip）先寫 `oos_downgrade.reason=insufficient_test_events`／`ic_train_test_split.oos_guarantees=false`，與「棄條件 IC 走主線」矛盾。

**碼證**: `docs/EVTWARMUP_TODO.md` Task 1.2「切分後、預檢後：`if event_conditional and split_context["test_events"]<...`」；同檔 Task 1.1 驗證 (e)；`analyze` 現序：precheck（`:1147`）→ stage3（`:1193`）→ stage4（`:1228`）。RECHECK: 對照若地板寫在 `:1163` 前 vs stage3 後＋`_is_event_conditional_consumed(event_info)`，case (e) 是否仍僅 bar skip。

**來源摘要**: docs/EVTWARMUP_TODO.md#b60b4a88a8cf

[MAJOR] 信心度=High。修法：Task 1.2 改「stage3 之後、stage4 之前」且條件＝`_is_event_conditional_consumed(event_info)`（與 §C-3 stage4 段一致）；`split_context["test_events"]` 在 stage3 後重算後再比 `min_test_events`。SPEC Task 1.2 同步一句。

---

## COMPOSER-R2-P1-02

**斷言**: Task 1.2 要求在 `analyze` 新增 `metadata["oos_downgrade"]={reason:insufficient_test_events,...}` 第三寫出點，但驗收要求 `pytest tests/api/test_gap3_oos_downgrade.py -q` 全綠且僅聲明 `test_resolve_root_status_behaviour_is_baseline` 不改——現有 `test_oos_downgrade_has_exactly_two_write_sites_with_precedence` 以 `src.count('"oos_downgrade"] = ')==2` 鎖死，實作後必紅。

**碼證**: `tests/api/test_gap3_oos_downgrade.py:29-42`；`momentum/Analysis/ic_filter_orchestrator.py` 現僅兩處（`:1418` fallback、`:1564` annotate 補寫）；TODO Task 1.2 驗證「`test_gap3_oos_downgrade.py -q` rc=0（基線不改）」。RECHECK: 假想 `analyze` 加第三處 `"oos_downgrade"] = ` → 該測試 count==3 失敗。

**來源摘要**: docs/EVTWARMUP_TODO.md#b60b4a88a8cf

[MAJOR] 信心度=High。修法：TODO 1.2 驗證表明列更新 `test_oos_downgrade_has_exactly_two_write_sites` 為「三寫出點＋優先序」（fallback 富版 > analyze 事件地板 > annotate 缺席補寫），或改為行為測試「富版不被覆蓋」；不可同時要求 count==2 與第三寫出點。

---

## COMPOSER-R2-P2-01

**斷言**: SPEC §C-6 要求「survivor／top-features／export 之 ICIR 讀取點由 TODO 逐一列出」，但 Task 2.1 檔案表未列 `ic_filter_orchestrator.get_top_features`；事件路徑 summary `icir=None` 時 `sorted(..., key=lambda item: item.get("icir", float("-inf")))` 取到 `None`（鍵存在）⇒ Python 3 `TypeError`，API `get_top_features`／export 可能炸。

**碼證**: `docs/EVTWARMUP_SPEC.md` §C-6；`docs/EVTWARMUP_TODO.md` Task 2.1 檔案表（無 `get_top_features`）；`ic_filter_orchestrator.py:2903-2907`；`api/routes/ic_analysis.py:497-508`。RECHECK: 事件路徑報告含 `icir: null` 呼叫 `get_top_features(sort_by="icir")` 是否 raise。

**來源摘要**: docs/EVTWARMUP_SPEC.md#c880b0f33f13

[MINOR] 信心度=High。修法：Task 2.1 補 `get_top_features` 排序 key 用 `_finite_or_neg_inf`（或事件路徑預設 `sort_by="ic_mean"`）＋單測；或 §C-6 降級聲明「top-features API 事件路徑禁用 icir 排序」。

---

## COMPOSER-R2-P2-02

**斷言**: Task 1.2 只規範 `DegradedBanner` 依 reason 分標，但 `MarginalICTable`（`oos_guarantees===false` ⇒ 固定「Full-sample research-only」）與 `ic_reporter.generate_ai_json`（degraded 一律插入「full-sample fallback」警語）未列入修改；holdout+`insufficient_test_events` 使用者在邊際 IC／AI 匯出仍見 full-sample 字面，與 consult W2 部分矛盾。

**碼證**: `frontend/src/components/ic-analysis/MarginalICTable.tsx:48-62`；`momentum/Analysis/ic_reporter.py:598-604`；Task 1.2 檔案表僅 `DegradedBanner.tsx`。RECHECK: 模擬 `oos_guarantees=false`＋`oos_downgrade.reason=insufficient_test_events` 渲染 MarginalICTable／generate_ai_json 輸出字串。

**來源摘要**: frontend/src/components/ic-analysis/MarginalICTable.tsx#948bd7a9a5dd

[MINOR] 信心度=Medium。修法：Task 1.2 增 MarginalICTable（讀 `oos_downgrade.reason` 或 `fit_mode`）與 `generate_ai_json` degraded 文案分流；或 EW-RESID-4 延伸登記「非 banner 消費端仍誤名」並接受研究用途風險。

---

## Verdict：需修補後派工

R1 六條本人 CLOSED；修訂版方向正確。B1 前須解 P1-01（地板 stage／predicate）與 P1-02（gap3 寫出點測試契約），否則照做會誤標 case (e) 或 gap3 全檔紅。P2 補 ICIR 消費端清單與非 banner 文案可與實作同批。

---

## VERIFY（本輪實跑）

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/EVTWARMUP_SPEC.md` | TEMPLATE PASS, rc=0 |
| `bash scripts/template_check.sh spec docs/TFWINDOW_SPEC.md` | TEMPLATE PASS, rc=0 |
| `bash scripts/template_check.sh todo docs/EVTWARMUP_TODO.md` | TEMPLATE PASS, rc=0 |
| `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` | `與既有 golden 相同？ **True**`, rc=0 |
| `rg '"oos_downgrade"\] = ' momentum/Analysis/ic_filter_orchestrator.py` | 2 處（`:1418`, `:1564`） |
| `rg pass_class frontend/src momentum/Analysis/survivor_contract.py` | 見 2a 碼證 |

---

ASSUMPTIONS_VERIFIED: 模板三 PASS；探針 True；R1 修訂 diff 對照；gap3 寫出點 count；analyze 階序讀碼
TESTS_RUN: 見 VERIFY 表（未跑 `pytest tests/governance`）
FAILURES_SEEN: none
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查）
產出檔: handoffs/20260908-evtwarmup-x-review-r2-composer.md

STATUS: DONE
