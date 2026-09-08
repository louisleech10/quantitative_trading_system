# Reconcile — 20260908-evtwarmup-x-review-r1

**來源** 20260908-evtwarmup-x-review-r1-codex.md, 20260908-evtwarmup-x-review-r1-composer.md, 20260908-evtwarmup-x-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

三家皆「需修補後派工」：codex 4 P1；composer 1 P0＋3 P1＋2 P2；grok 2 P0＋2 P1＋3 P2。全部為**文件層**缺陷（照做會錯／開洞），無一否定 consult 方向。

### V1 🔴 P0 — 第三個 `analysis_status` 值撞兩值硬契約（`COMPOSER-R1-P0-01`、`GROK-R1-P0-01`、`CODEX-R1-P1-02`、`GROK-R1-P1-01`、`COMPOSER-R1-P1-01`）
**出處**：root 寫入鏈 `_resolve_root_status`→`_annotate_root_status_and_pass_class` 只產兩值；`normalize_analysis_status` 把未知吃成 `degraded_full_sample`；survivor `validate` 對非兩值 raise；TS union 兩值；`test_resolve_root_status_behaviour_is_baseline` 鎖死。
**處置**：採 grok 方案 **B**——撤回第三值。SPEC §C-4／§G 改為 `analysis_status=="degraded_full_sample"`（字面歷史遺留、語意＝無 OOS 保證）＋`oos_downgrade.reason=="insufficient_test_events"`＋`fit_mode=="train_mask"`；`pass_class` 契約 notes 文件化為 `oos_guarantees` 鏡像；誤名登 `EW-RESID-4`（user-ruling：兩值契約不得擴）。

### V2 🔴 P0 — 分流鍵 `is not None` 可繞（`GROK-R1-P0-02`、`CODEX-R1-P1-01`、`COMPOSER-R1-P1-02`）
**出處**：預檢在 stage3 前尚無 `label_source`；`{}`、`enabled=False`、事件不足棄條件三案 SPEC/TODO 自相矛盾。
**處置**：SPEC §C-3 改**兩段判**：預檢 `bool(values) and enabled`；stage4 之後 `label_source=="event_label_value"`；刪「或 is not None」；Task 1.1 驗證加 (c)(d)(e) 三反例、mutation M2/M3/M4。

### V3 — P1 ICIR 消費端未列全（`CODEX-R1-P1-03`、`COMPOSER-R1-P2-01`、`GROK-R1-P2-01`）
**出處**：`redundancy_filter._score_value` 對非有限 icir 回 `-inf` 不讀 `ic_mean`；reporter 三處 `key=item.get("icir",-inf)` 遇 None TypeError。
**處置**：Task 2.1 列全：呼叫端事件路徑傳 `tiebreaker="ic_mean"`（`redundancy_filter.py` 不改）；reporter 排序 key `_finite_or_neg_inf`；事件路徑 `icir` 寫 NaN 非 None；各釘測試。

### V4 — P1 全域揭露鍵撞 byte golden；artifact 尚不存在（`CODEX-R1-P1-04`）
**處置**：`ic_window_disclosure` B1 **只寫事件路徑**；全域揭露隨 TFWINDOW（B2）重凍 golden 時一併進，重凍 diff 只准含該鍵（TFWINDOW §G 補述）。artifact（測試檔／mutation／gate）＝Task 交付物，TODO 已列路徑；不在 SPEC 階段寫實作。

### V5 — P1 DegradedBanner 文案／pass_class 誠實性（`COMPOSER-R1-P1-03`、`GROK-R1-P1-02`）
**處置**：Task 1.2 明訂 banner 依 reason 分主標（`insufficient_test_events` ⇒ 不含「Full-sample」，顯示 `test_events/min_test_events`）；vitest 釘。

### V6 — P2 契約 `reasons` 為分類→陣列（`GROK-R1-P2-03`）；TFWINDOW 測試層級（`COMPOSER-R1-P2-02`、`GROK-R1-P2-02`）
**處置**：新增分類鍵 `reasons.oos_downgrade`（既有 8 鍵＋新值），前端 vitest 讀契約；TFWINDOW §G 註明引擎層回歸 vs 接線主 gate，mutation 須「主 gate 紅、引擎層綠」。

### V7 — 流程（codex STATUS BLOCKED：completeness 因 OPEN 債被 gate 拒）
非文件缺陷；codex 產出完整，completeness 由主委端 `completeness_check --lock` 執行（PASS）。

Verdict: 需修補後派工——V1–V6 已全部改進 SPEC（R1 修訂版）／TODO／TFWINDOW SPEC，template_check PASS；進 R2 由原提出方逐條 CLOSED 判定後派 B1。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: `event_label_values is not None` 不能直接等同「事件 label 已被消費」；現行前檢可能放行主線或將空 dict 當事件 label。
**碼證**: SPEC §C-3/TODO Task1.1 同時列入口鍵與 `label_source`，但 TODO 又規定 disabled/空 dict 視主線；`ic_filter_orchestrator.py:1074-77,1144-49,3204-21,3257-60,3333-49,3361-69` 顯示前檢早於 stage3 產生者判定；RECHECK: `nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '1074,1149p;3204,3221p;3257,3260p;3333,3369p'`。
**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6;docs/EVTWARMUP_TODO.md#baf86b01c118;momentum/Analysis/ic_filter_orchestrator.py#644bd066457d
MAJOR 信心度=High；disabled 時 stage3 明確回 `mode=none`，空 dict 在 enabled 分支仍進 given-label 驗證，可能繞 bar gate 或以 NaN/缺值失敗。修法是先定義完整 truth table，令同一個「實際被消費」predicate 同時供 precheck、stage4、fallback rerun；不得用 raw non-None 取代它。
## CODEX-R1-P1-02
**斷言**: Task1.2 要求的 `degraded_insufficient_test_events` 與現有 root/status、survivor、前端二值契約不相容；只加字串會被吞成 full-sample 或 fail-closed 拒收。
**碼證**: `normalize_analysis_status` 明定兩值；root resolver 只回兩值；survivor validate/build 只接受兩值；TS `ICReport` 只宣告兩值、Banner 文案固定 full-sample；VERIFY: `normalize_third=degraded_full_sample`。
**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6;docs/EVTWARMUP_TODO.md#baf86b01c118;momentum/Analysis/ic_reporter.py#73006e6bb658;momentum/Analysis/survivor_contract.py#eb9ecff6333b;frontend/src/lib/types.ts#7612e6b1d329;frontend/src/components/ic-analysis/DegradedBanner.tsx#948bd7a9a5d
MAJOR 信心度=High；若維持二值，`fit_mode=train_mask` 的 holdout run 會被標成 `full_sample_research_only`；若新增第三值，persist/export/API/scan/pass_class/UI 全要同步。文件須先選定「二值＋結構化 reason」或完整三值矩陣，並給 `oos_downgrade`、pass_class、消費端與 `min_test_events=0` 的一致契約；不能僅在 orchestrator 加值。
## CODEX-R1-P1-03
**斷言**: 跳過事件路徑 `icir_min` 後，TODO 指定的 tiebreaker `ic_mean` fallback 尚未落到實際 ICIR 消費者，會造成靜默排序退化或 TypeError。
**碼證**: `_apply_thresholds` 在 `ic_filter_orchestrator.py:4220-50` 無事件參數；stage6 將 `ic_scores` 傳入 redundancy `:3931-35`；`redundancy_filter.py:378-87` 缺/非有限 icir 回 `-inf`、不讀 `ic_mean`；reporter `:403-11,572-78` 與 orchestrator `:2903-06` 仍按 icir 排序。VERIFY: `tiebreaker_nan_score=-inf`、`mixed_icir_sort=TypeError`。
**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6;docs/EVTWARMUP_TODO.md#baf86b01c118;momentum/Analysis/redundancy_filter.py#5f57224be356;momentum/Analysis/ic_reporter.py#73006e6bb658;momentum/Analysis/ic_filter_orchestrator.py#644bd066457d
MAJOR 信心度=High；NaN/None ICIR 會讓冗餘挑選把有 IC mean 的特徵視為 `-inf`，混合 None/float 的報告排序可直接炸。修法須列出 stage6、top-features、AI/export、survivor 的讀取點，僅對明定 tiebreaker/呈現排序做安全 fallback，保留 NaN/inf gate，並分別釘事件與全域測試。
## CODEX-R1-P1-04
**斷言**: Task2.1 的 global disclosure 與逐位元組 golden、以及 TFWINDOW 的生產接線與新 gate，目前互相矛盾且缺少可執行 artifact。
**碼證**: TODO 要求兩路徑寫 `ic_window_disclosure` 且 SPEC §C-2/G 要 global 逐鍵不變；`_build_report_metadata` 會保留新增 metadata (`ic_filter_orchestrator.py:4301-33`)，而 `scripts/gap2_freeze_golden.py:40-63` 僅 scrub 固定鍵。`test_ic_1a_cut1_oos.py:129-155` 直呼 stage4，不能證明 analyze→metadata timeframe 注入。VERIFY `for p ...; test -e "$p"` 對 `tests/api/test_evtwarmup.py`, `tests/api/test_tfwindow.py`, `tests/golden/tfwindow/rolling_keys_1h.json`, mutation script, phase gate 均輸出 MISSING。
**來源摘要**: docs/EVTWARMUP_SPEC.md#b4a2ce9a51c6;docs/EVTWARMUP_TODO.md#baf86b01c118;docs/TFWINDOW_SPEC.md#6dc2c594ede4;momentum/Analysis/ic_filter_orchestrator.py#644bd066457d;scripts/gap2_freeze_golden.py#a3e234e4fc75;tests/momentum/Analysis/test_ic_1a_cut1_oos.py#99ad604dc54d
MAJOR 信心度=High；若 disclosure 進 global 報告，完整 canonical 會變但 probe 子投影可能假綠；若只改 `window_5` assertion，則可能未測到 production setter。文件須先明定 disclosure 是否在 byte-locked projection 外、補齊 1h/missing/invalid production-path golden、mutation、gate 與測試檔，再派工。§N：EW-RESID-1=user-ruling 成立；EW-RESID-2/3=needs-research 理由成立，30 目前是經驗地板而非 power 事實。
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

