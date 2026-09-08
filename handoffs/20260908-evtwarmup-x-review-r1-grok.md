brief-kind: review
task-id: 20260908-EVTWARMUP-X-REVIEW-R1
family: grok
findings-round: R1
標的：`docs/EVTWARMUP_SPEC.md`、`docs/TFWINDOW_SPEC.md`、`docs/EVTWARMUP_TODO.md`（尚未實作；HEAD=`b96428f2`）

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核 |
|---|---|---|
| 三份 template PASS | **fact-verified** | `bash scripts/template_check.sh spec\|todo` → 三條 TEMPLATE PASS, rc=0 |
| 改前 golden 探針 | **fact-verified** | `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` → `與既有 golden 相同？ **True**`；`event_run.reason=rolling_warmup_insufficient test_rows=13`；`global_run.analysis_status=ok_oos` |
| consult W1–W4 已收斂 | **fact-verified（讀 synth）** | `handoffs/reconcile/20260908-evtwarmup-x-consult-r1/synth.md` |
| brief assumed：第三 status 不破前端兩值 | **推翻** | `DegradedBanner.tsx` 以 `!== ok_oos` 顯示（會亮），但 `types.ts:2257` 兩值 union；標題寫死 Full-sample → P1-02 |
| brief assumed：survivor 兩值枚舉 | **推翻** | `survivor_contract.py:279`／`:461` 未知 status → `ContractValidationError` → P0-01／P1-01 |
| SPEC／TODO：分流＝`event_label_values is not None` 即事件條件路徑 | **assumption 當 fact** | 與 Task 1.1 驗證(c)／邊界②、以及 stage3 `insufficient` 棄條件 IC 後主線續跑互斥 → P0-02 |
| Task 2.1「缺 ICIR 走 ic_mean」已存在於碼 | **assumption** | `redundancy_filter._score_value` NaN→`-inf`，不讀 `ic_mean` → P2-01 |

---

## 必答（成對）

### 1a／1b 分流鍵

- **1a 可否被繞（主線逃 bar gate／事件當主線）**：**可被繞，若照現寫法實作。** §C-3 以 `event_label_values is not None` **或** `label_source==event_label_value` 判事件路徑；TODO helper 簽名只收 `event_label_values`。反例①：`event_label_values` 非空但 `event_filter.enabled=False` → stage3 `:3257-3260` 早退、主線 label，若預檢／stage4 仍因 `is not None` 豁免 warmup ⇒ **主線逃 bar gate**（恰為 §C-3 要防的洞，卻用錯誤判準自己挖開）。反例②：事件總數 `< min_events` → stage3 寫 `conditional_ic_abandoned`／`label_source=mainline_return_N`（`:3311-3324`）後全樣本續跑；若 stage4 仍看入口 `event_label_values is not None` ⇒ 主線路徑跳過 bar 安全網。反例③：`{}` 在 Python `is not None` 為真，與 TODO 邊界②「空 dict⇒主線」互斥。mutation M2 只釘 `event_filter.enabled` 單獨分流，**不覆蓋**上述「有 values 但非條件 IC」形狀。
- **1b 會否誤擋合法事件 run**：設計意圖下**不會多擋**（34 測試段事件現況被 131 bar 誤擋；豁免後改走 `min_test_events`）。誤擋風險反而在分流寫太窄（只看 `enabled`）——SPEC 已禁，方向對；問題在「或 `is not None`」寫太寬。

### 2a／2b 第三 `analysis_status`

- **2a 第三值是否必要**：對「語意誠實」有幫助，但**非唯一解**。維持兩值＋`oos_downgrade.reason=insufficient_test_events` 可與現行 `_resolve_root_status`（`:1543` 僅兩值）／survivor／TS union 相容，且前端已有 reason 文案表。SPEC 已選第三值並在 §G 寫 `analysis_status != "degraded_full_sample"`，卻**未改寫入點** `_resolve_root_status`／`_stage7_report:4014-4018`，也未列 survivor——照做會：要么被寫回 `degraded_full_sample`（違反 TODO「禁被吃成」與 §G），要么進 persist 被 survivor fail-closed。見 P0-01。
- **2b 兩值下 `degraded_full_sample` 字面是否誤導**：**是。** 本路徑 `fit_mode` 仍 `train_mask`、holdout 已套用，只是事件統計不足；字面與 DegradedBanner 主標「Full-sample research-only」（`:47-51`）及 `pass_class=full_sample_research_only`（`:1570-1571`）都會說成全樣本。兩值方案必須同步改 banner／pass_class 語意或加第三 pass_class；不是只加 reason 字串就夠。

### 3a／3b ICIR／全域不變

- **3a 跳過 `icir_min` 後其他消費者**：stage5 `:4248` 為硬篩（Task 2.1 主目標，正確）。stage6 經 `RedundancyFilter`，`_score_value`（`redundancy_filter.py:378-387`）在 tiebreaker=`icir` 且非有限時回 `-inf`，**不會**改讀 `ic_mean`——與 SPEC／TODO「缺 ICIR 走 ic_mean」字面不符；可能靜默改冗餘剔除序，非 raise。`get_top_features(..., sort_by="icir")`（`:2895`）同類。未炸進程，但「診斷降級無副作用」不成立 → P2-01。
- **3b 全域逐位元組**：§C-2／§G 以 `global_run` 探針＋gap2／ic1d 守住，方向可執行。預期變鍵僅 **event_run**：`ic_train_test_split.*`、`oos_guarantees`、`oos_downgrade`、`analysis_status`、`removed["icir*"]`、`ic_window_disclosure`；`facts.adjusted_windows_*` 本票不變（TFWINDOW 另票）。

### 4a／4b TFWINDOW

- **4a 互斥 golden 可執行**：TODO §B B1→B2、TFWINDOW §C-3 禁同 commit；12h over 向 `test_gap2_golden` 不變＋1h 新 `rolling_keys_1h.json`（鍵集／長度／值 sha256）清楚。
- **4b `test_oos_ic_rolling_warmup` 重算**：**不是改測試換綠**——fixture `timeframe=1h` 下期望鍵隨換算因子重算，屬正確化對齊；刪斷言才算換綠。附註：該測直接呼叫 `_stage4_ic_calculation`（`:135`），不經 `analyze` 注入——應以 `tests/api/test_tfwindow.py` 為接線主 gate（TODO 已有），避免「單測綠、接線漏」→ P2-02。

### 5 ≥10× 複雜？

**無。** 分流＋地板＋跳過 icir_min；TFWINDOW 單點接線。無 queue／distributed。

### 6 可進實作？

**需修補後派工。** P0-01（第三 status 與 root 寫入／§G／基線測試結構矛盾）與 P0-02（分流鍵過寬／自相矛盾）未改文件前，Agent 照做會開 OOS 洞或無法同時滿足 §G 與 survivor。

---

## §1 必查摘要（11 類）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | §C-3 vs TODO `{}`／驗證(c)；§G 第三 status vs `_resolve_root_status` 兩值；Task 2.1 ic_mean fallback vs `_score_value` → P0／P2 |
| 2 | 漏項 | TODO 1.2 未列 `_resolve_root_status`、survivor、types.ts、DegradedBanner 主標、pass_class → P0-01／P1 |
| 3 | 不可測 | §G／mutation／探針可證偽；TFWINDOW 1h sha256 門檻有 |
| 4 | quant | W2 方向正確；地板 30＝EW-RESID-3 needs-research 成立（非現在可證 power） |
| 5 | 過度工程 | 無 |
| 6 | OOM | 本票不擴並行；無 |
| 7 | Cache | N/A |
| 8 | API／相容 | 第三 status 破兩值契約（見 P0-01）；reason 只新增方向對 |
| 9 | 測試 | mutation M1–M5 形狀對；缺「values 有、非條件 IC」反例 → P0-02 |
| 10 | Agent 可執行 | helper 簽名 SPEC≠TODO；`ic_report_contract.reasons` 為分類物件，不能「加一字串」→ P2-03 |
| 11 | 短命工 | 無（`ic_window_disclosure.timeframe_adjustment` 值於 B2 變更、欄位保留，已登記） |

§N：`EW-RESID-1` user-ruling 另票成立；`EW-RESID-2/3` needs-research 成立（三家未收斂 estimand／無 power 推導）；`TW-RESID-1` user-ruling 成立。無「應收回為 Task」。

---

## GROK-R1-P0-01

**斷言**: SPEC Task 1.2／§G 要求事件不足時 `analysis_status="degraded_insufficient_test_events"` 且 `!= "degraded_full_sample"`，但 root 唯一寫入鏈 `_resolve_root_status`→`_annotate_root_status_and_pass_class`（`ic_filter_orchestrator.py:1542-1543,4014-4018`）只產出兩值；TODO 只改 `normalize_analysis_status` 不夠；且 `test_resolve_root_status_behaviour_is_baseline`（`test_gap3_oos_downgrade.py:102-115`）鎖死 `oos_guarantees=False⇒degraded_full_sample`。

**碼證**: 實讀 `normalize_analysis_status`（`ic_reporter.py:50-65`）未知字串→`degraded_full_sample`；`_resolve_root_status` 原文 `return ("ok_oos", True) if branch is None else ("degraded_full_sample", False)`；TODO Task 1.2 檔案表無 `_resolve_root_status`。RECHECK: 假想 metadata `{ic_train_test_split:{applied:True,oos_guarantees:False}, oos_downgrade:{reason:insufficient_test_events}}` 呼叫 `_resolve_root_status` 必得 `degraded_full_sample`；§G 與該基線測試不可同時綠，除非先改 SPEC 分支表並更新測試。

**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6；momentum/Analysis/ic_filter_orchestrator.py#644bd066457d；momentum/Analysis/ic_reporter.py#73006e6bb658

[BLOCKING] 信心度=High。會怎麼失敗：Agent 在 analyze 寫第三值 → stage7 覆寫回兩值（§G 紅／TODO「禁被吃成」失敗）；或強改 normalize 放行第三值但未改 `_resolve_root_status` 則報告仍兩值。修法（二選一，禁雙軌）：**(A)** SPEC／TODO 明訂 `_downgrade_branch`／`_resolve_root_status` 三分支（holdout+`insufficient_test_events`→第三值；真 full-sample fallback→`degraded_full_sample`），並更新 gap3 基線＋所有消費端；**(B)** 撤回第三值，§G 改為 `analysis_status=="degraded_full_sample"` 且 `oos_downgrade.reason=="insufficient_test_events"`，另修 banner／pass_class 誠實性（見 P1-02）。

---

## GROK-R1-P0-02

**斷言**: 分流鍵若實作為「`event_label_values is not None` ⇒ 豁免 bar warmup」，會讓「有 values 但非條件 IC」的主線路徑逃過 warmup 門檻，開 OOS 洞；SPEC §C-3 的「或 is not None」、TODO helper 只收 `event_label_values`、與 Task 1.1 驗證(c)／邊界②自相矛盾。

**碼證**: SPEC §C-3／Task 1.1 簽名 `(event_label_values, event_info)`；TODO Task 1.1 簽名 `(event_label_values)->bool`＋驗證(c)「values 給了但 enabled=False⇒主線⇒回 details」＋邊界②`{}`⇒主線；現碼 stage3 `if not event_cfg.enabled: return ...`（`:3257-3260`）、insufficient 棄條件 IC（`:3311-3324`）。預檢在 stage3 **之前**（`:1147`），當時尚無 `label_source`。RECHECK: 單測三案——(1) values 非空＋enabled=False ⇒ precheck 仍回 details；(2) values 非空＋enabled 但 n_events<min_events ⇒ stage4 仍套 bar 規則；(3) values=`{}` ⇒ 主線。mutation 須紅若分流只看 `is not None`。

**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6；docs/EVTWARMUP_TODO.md#baf86b01c118；momentum/Analysis/ic_filter_orchestrator.py#644bd066457d

[BLOCKING] 信心度=High。修法：統一分流＝**實際條件 IC 產生者**。(預檢) `bool(event_label_values) and event_filter.enabled`（空 dict 假）；(stage4) `event_info.get("label_source")=="event_label_value"`（棄條件後必假）。§C-3 刪「或 is not None」寬條款；TODO helper 簽名與 SPEC 對齊並傳 `enabled`／stage 後 `event_info`；mutation 加上述三反例。

---

## GROK-R1-P1-01

**斷言**: 若堅持第三 `analysis_status`，TODO Task 1.2 消費端清單不完整——`survivor_contract.py:271-279,456-461` 對非 `{ok_oos,degraded_full_sample}` raise；`ic_report_contract.json` notes 仍寫兩值契約；`frontend/src/lib/types.ts:2257` 與 `api/models/ic_models.py` 描述兩值——事件 run 落 survivor 會 fail-closed。

**碼證**: `grep`／實讀上述路徑；TODO Task 1.2 檔案表（`EVTWARMUP_TODO.md:33`）無 survivor／types／survivor 契約。scan_cube 只透傳 `analysis_status`（`scan_cube.py:223`），本身不拒枚舉——風險在 survivor／normalize，非 cube。RECHECK: 以第三 status 呼叫 `build_survivor_output`／`validate_survivor_output` 必 raise。

**來源摘要**: momentum/Analysis/survivor_contract.py#eb9ecff6333b；docs/EVTWARMUP_TODO.md#baf86b01c118；frontend/src/lib/types.ts#7612e6b1d329

[MAJOR] 信心度=High。修法：若選 P0-01 方案 A，TODO 補 survivor 驗證分支＋契約 notes／TS／Pydantic 描述＋`pass_class` 配對規則；若選方案 B，本條隨第三值撤回而關閉，改推 P1-02。

---

## GROK-R1-P1-02

**斷言**: Task 1.2 路徑（holdout 已套用、僅 `insufficient_test_events`）仍會亮 DegradedBanner（`status !== ok_oos`），但主標／正文寫死「Full-sample research-only／full-sample fallback」（`DegradedBanner.tsx:47-51`），且 `_annotate_root_status_and_pass_class` 非 ok_oos 一律 `pass_class=full_sample_research_only`（`:1570-1571`）——對「仍在 holdout 算點 IC」為假陳述。

**碼證**: 實讀 `DegradedBanner.tsx:37-51`；`oosDowngradeDocs.ts` 尚無 `insufficient_test_events` 鍵（TODO 只說加文案，未改主標）。RECHECK: vitest 對新 reason 斷言主標**不含** Full-sample／full-sample fallback 字面，並顯示 `test_events/min_test_events`。

**來源摘要**: frontend/src/components/ic-analysis/DegradedBanner.tsx#948bd7a9a5dd；frontend/src/lib/oosDowngradeDocs.ts#737cf477ffdc

[MAJOR] 信心度=High。修法：TODO 1.2 明訂 banner 依 reason 分流標題；`pass_class` 對 holdout+事件不足改用非 full_sample 字面（或文件化「pass_class 只表 oos_guarantees 鏡像、不表 fit 範圍」並改前端解讀）——與 consult W2 對齊。

---

## GROK-R1-P2-01

**斷言**: Task 2.1 宣稱 stage6 tiebreaker 缺 ICIR 走 `ic_mean`，但 `redundancy_filter._score_value` 在 `tiebreaker=="icir"` 且值非有限時回 `-inf`，不會讀 `ic_mean`；事件路徑 ICIR 全 NaN 時冗餘剔除序可能變，且未釘測。

**碼證**: `momentum/Analysis/redundancy_filter.py:378-387`；SPEC／TODO Task 2.1 未列改 `redundancy_filter.py`。RECHECK: 事件 34 路徑比對 `redundancy_log`；或單測 `_score_value({"f":{"icir":nan,"ic_mean":0.2}},"f","icir")` 現況為 `-inf`。

**來源摘要**: momentum/Analysis/redundancy_filter.py#5f57224be356

[MINOR] 信心度=High（行為）／Medium（影響幅度）。修法：事件路徑傳 `tiebreaker_effective=ic_mean` 或改 `_score_value` 在 icir 非有限時 fallback；TODO 列入檔案＋測試。或 SPEC 改寫為「順序不保證、僅跳過 icir_min 硬篩」。

---

## GROK-R1-P2-02

**斷言**: TFWINDOW 把 `test_oos_ic_rolling_warmup` 列為須重算之回歸，但該測直接呼叫 `_stage4_ic_calculation`（`test_ic_1a_cut1_oos.py:135`），不經 `analyze` 的 `set_timeframe` 注入——不能單獨當接線驗收。

**碼證**: 實讀該測；TFWINDOW Task 3.1 主驗收應為 `tests/api/test_tfwindow.py`（TODO 已列）。RECHECK: 刻意漏 `set_timeframe` 時 `test_tfwindow -k window_keys` 須紅、而 `test_oos_ic_rolling_warmup` 可仍綠。

**來源摘要**: docs/TFWINDOW_SPEC.md#6dc2c594ede4；tests/momentum/Analysis/test_ic_1a_cut1_oos.py（HEAD）

[MINOR] 信心度=Medium。修法：§G／TODO 標註該測＝引擎層、`test_tfwindow.py`＝接線主 gate（已有則加一句即可）。

---

## GROK-R1-P2-03

**斷言**: TODO Task 1.2 寫「`ic_report_contract.json::reasons` 加 `insufficient_test_events`」，但該檔 `reasons` 是**分類→字串陣列**物件（`event_fallback`／`analysis_rejected`…），不是扁平字串集；Agent 無法「加一個字面」而不先定分類鍵。

**碼證**: `momentum/Analysis/contracts/ic_report_contract.json:12-22`；現有 oos_downgrade reason 實際由 orchestrator 字面＋`oosDowngradeDocs.ts` 對證，**未**住在該 `reasons` 區塊。RECHECK: 讀契約後指出應新增之分類鍵名（建議 `oos_downgrade`）或改 TODO 指向真正 SSOT。

**來源摘要**: momentum/Analysis/contracts/ic_report_contract.json#0895efeec513；docs/EVTWARMUP_TODO.md#baf86b01c118

[MINOR] 信心度=High。修法：TODO 改為新增 `reasons.oos_downgrade`（含既有 rolling_warmup 等＋新值）並讓前端／測試改讀契約；或明示 SSOT＝orchestrator 字面＋`oosDowngradeDocs` 機檢（維持現制）、契約不加。

---

## Verdict：需修補後派工

P0-01、P0-02 為文件層結構缺陷（照做會錯／開洞），須先改 SPEC／TODO 再派 B1。P1 為第三 status 消費端與 banner／pass_class 誠實性。P2 不阻開工但應同批補。TFWINDOW 互斥策略可執行；§N 三殘留理由成立；無 ≥10× 複雜。

---

## VERIFY（本輪實跑）

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/EVTWARMUP_SPEC.md` | TEMPLATE PASS, rc=0 |
| `bash scripts/template_check.sh spec docs/TFWINDOW_SPEC.md` | TEMPLATE PASS, rc=0 |
| `bash scripts/template_check.sh todo docs/EVTWARMUP_TODO.md` | TEMPLATE PASS, rc=0 |
| `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` | `與既有 golden 相同？ **True**`；event `rolling_warmup_insufficient test_rows=13`；global `ok_oos` |
| `grep -n "degraded_full_sample\|ok_oos\|normalize_analysis_status" momentum/Analysis/ic_reporter.py momentum/Analysis/survivor_contract.py frontend/src/lib/types.ts frontend/src/components/ic-analysis/DegradedBanner.tsx` | 兩值契約／banner 主標寫死 Full-sample |
| `grep -n "icir\|_score_value\|tiebreaker" momentum/Analysis/ic_filter_orchestrator.py momentum/Analysis/redundancy_filter.py` | stage5 `:4248`；`_score_value` NaN→`-inf` |
| `grep -n "event_label_values\|label_source\|_precheck_rolling_warmup" momentum/Analysis/ic_filter_orchestrator.py` | 預檢先於 stage3；insufficient 棄條件 IC |

未跑 `pytest tests/governance`（brief 禁）。

---

ASSUMPTIONS_VERIFIED: 模板三 PASS；探針 True；brief 未查四列已用 grep／實讀覆核（前端／survivor／ICIR／scan_cube）
TESTS_RUN: 見 VERIFY 表；未跑產品 pytest（review-only）
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（本產出不改碼；標記 event_run schema／status 枚舉為 SPEC 預期變更且目前與現碼衝突）
產出檔: handoffs/20260908-evtwarmup-x-review-r1-grok.md

STATUS: DONE
