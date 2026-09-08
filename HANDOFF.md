# HANDOFF — 當前任務狀態

**更新：2026-09-09 凌晨｜狀態：EVTALIGN 五批＋EVTWARMUP 兩批（含 TFWINDOW）皆已實作 commit；code review R5 進行中；使用者 UAT B26–B33 待驗。**

## 使用者最後兩條指示（逐字）
> 「那這個修正後的排序改SPEC。B26/B27等上述完成後再驗收。我要先睡了」
> 「你跟委員討論決定共識看要怎麼做」

⇒ B26／B27 驗收暫緩至 EVTALIGN 收完。路線已由 consult 共識決定，**不再問使用者**。

## 當前票：`EVTALIGN`
SPEC=`docs/GAP3_EVENT_ALIGNMENT_SPEC.md`／TODO=`docs/GAP3_EVENT_ALIGNMENT_TODO.md`（皆 TEMPLATE PASS）。

**審查軌跡**：R1 19 條（3 P0）→ R2 19 條（**6 P0**，變差）→ consult 三家一致 **B＋D**。
R2 六個 P0 同一形狀＝「每個判準都做成呼叫端傳入，可偽造」。
codex：「A 為堵洞而改…實質收斂成 B＋D 的較大改動面」⇒ A 之終點就是 B＋D。
三輪債皆 `debt_clear`；收斂檔 `handoffs/reconcile/2026090{7,8}-evtalign-x-*/synth.md`。

## 裁定的路線
- **B**（Task 1.1）：**不動 `validate_alignment` 任何一行**。label 生成前把 `close` 裁到 feature 尾
  （`_coterminalize_close`，單一 helper），**stage0 `:2790` 與 stage2 `:2923` 兩呼叫點都接**。
  不新增任何參數 ⇒ R2 之「可偽造」形狀無從產生。
  前提已實跑：`handoffs/20260908-probe-option-b-trim.py` rc=0（裁切把截短化約為同尾，label 逐位元組相同）。
- **D**（Task 2.1，**B 之必要配套**）：驗實際被消費的 label；`label_kind` 由 producer 之 `label_source` 導出；
  `event_given` 加 `(event_id, timestamp, label_value)` 三元組逐筆綁定。
  codex：不做 D ＝ event_id 錯配進條件 IC ＝**錯誤輸出**。
- P3 期間自動對齊＋丟失事件 ID 揭露；P4 進度＋記憶體 WARN（**不得擋**）；P5 purge/embargo 揭露。

## B0 完成（2026-09-08）
Task 0.2 golden 重做：`handoffs/20260907-probe-split-baseline.py --write` → 9 組（8 ok＋1 skip），
含 stage0 預載（`horizon_source=column_parse`）、`split_row_fingerprint`、`retained_event_ids`；
sha256=`e378c706…ba7201`，重跑對證 True。
Task 0.1 scaffold：`scripts/evtalign_phase_gate.sh`、`handoffs/20260907-evtalign-mutate.py`、
三個 placeholder 測試（`pytest.skip`）。實測 rc 直接取：phase 0 PASS；phase 1 rc=1（2 skip＋UNCOVERED=5）＝預期。
🔴 mutate 首版把 pytest rc=5（沒收集到測試）當「紅」⇒ B3 假 PASS；已改為 rc=5 計 UNCOVERED、紅只認 rc=1。

## B1 完成（2026-09-08，commit `efb16e4c`）
Task 1.1：`_coterminalize_close` 接 stage0＋stage2；守衛 sha256 `9c8aeb69…` 釘在測試。
Task 2.1：contracts `derive_label_kind`／`validate_event_given`／`validate_consumed_label`；stage3 覆寫後驗；
`event_label_owners` 透傳＋service `_assert_event_triple_bound` 回比 `event_label_by_id`。
🔴 **更正**：我曾寫「golden 8 檔通過」——實為 **4 failed／78 passed（rc=1）**，我只看 harness exit code 沒讀 pytest rc。
A/B（`097dae40` worktree）證實四條在 B1 前就紅（reporter stub 缺 kwarg×2、config_hash 凍結過期、event_timestamps kwarg 正則），
登記 `EA-RESID-6`；事故寫在 reconcile R3 E4。**驗收一律逐檔看 pytest 的 rc／summary 行，禁看 harness exit code。**

## R3 完成（2026-09-08）
三家一致「可合併、無新 P0」；D1–D4／D6／D7／D9 CLOSED。共同 P1＝D5（事件 label 將覆寫時 stage2 仍硬擋鷹架）：
三家裁「資料驅動延後」不違 §C-6 ⇒ 已實作 `_settle_deferred_scaffold`（覆寫 ⇒ 診斷揭露；未覆寫 ⇒ 原樣 raise），
TODO 2.1 要點 3／SPEC Task 2.1 要點 5 改寫；P1-02（stage0 預載）以 fail-closed 測試閉合；mutation 加 E1／E2。
新測試 18 條 rc=0；template_check 兩份 PASS；reconcile `handoffs/reconcile/20260908-evtalign-x-review-r3/synth.md`。

R3 修法 commit `ba408826`；`evtalign_phase_gate.sh 1` rc=0（mutation 10/10）；debt 已清（lock 升 review，`27030457`）。

## B2 完成（2026-09-08）
Task 2.2 `tests/momentum/test_validated_series_is_used_series.py`：四情境（global_with_labels／global_without_labels／event／
cross_sectional=not_applicable 具名 EA-RESID-2）spy 斷言「最後被驗的 series ＝ 進 stage4 的 series」；5 條 rc=0。
mutation phase 2：A6a（global 驗 A 用 B）／A6b（event 驗 A 用 B）。

B2 commit `a8a6f3f5`；`evtalign_phase_gate.sh 2` rc=0（A6a／A6b 紅）。

## B3 完成（2026-09-08）
Task 3.1：orchestrator `_intersect_features_with_kline_period`（stage0、切分前；`metadata.period_alignment` 只在真裁時寫）；
service `check_feature_run_coverage` 改逐事件（回 `FeatureRunCoverage`；`dropped_events.ids` 揭露、全丟才 fail-closed），
`_inject_period_alignment` 併進報告。`tests/api/test_period_auto_align.py` 8 條；coverage_gate ⑦ 改新語意；mutation A7／A8／A9。

## B4 完成（2026-09-08）
Task 4.1：`DataPreprocessor.preprocess(progress=)`（winsorize 迴圈每 `_progress_interval` 欄回報，ETA 兩次後才估）；
orchestrator `_stage1_progress_hook`＋`_memory_pressure`（psutil；WARN 一次不擋）；service `_apply_stage_progress`→`/task` 之
`sub_progress`／`warnings`；前端 store／hook／`icProgressLabel.ts`／頁面顯示。`tests/api/test_stage_progress.py` 12 條；vitest 4 條；mutation A8／A10／A11。

B3＋B4 commit `ae71dbb6`（既有測試：B3 後 226/1 紅＝EA-RESID-6；B4 後 134 passed）。

## B5 完成（2026-09-08）
Task 5.1：service `_inject_isolation_source`（事件路徑、切分已套用時由 `ic_train_test_split` 組 `metadata.isolation`；
落點改 service 之理由見 TODO 5.1 要點 3）；前端 `IsolationNote`／`icIsolation.ts`。另補 B3 前端 `PeriodAlignmentBanner`／
`icPeriodAlignment.ts`；驗收清單新增 **B28／B29／B30**。`tests/api/test_isolation_disclosure.py` 5 條；mutation A12／A13。

B5 commit `411e9b90`；gate 1–5 全 PASS（`d398b194`）；B5 後 service 既有 124 passed。

## R4 完成（2026-09-08）
composer／grok 判可合併、零 finding；codex 兩條 P2（第 4 段進度回報：欄數<3 回報不足；回報在處理前發、done 高估一欄）⇒ 已修
（`_after_column` 於處理後發；下界改 `min(3,total)`；`tests/api/test_stage_progress.py` 加 n∈{1,2,3} 與 done＝已處理欄數 spy，rc=0）。
三家一致 B5 落點維持 service。reconcile `handoffs/reconcile/20260908-evtalign-x-review-r4/synth.md`（F1／F2）；debt 已清。

## UAT 實機修補（2026-09-08 晚，使用者在線）
① 兩個 next dev 互蓋 `.next`（環境，非碼）②WS 未轉發 `sub_*`（`6bdda097`）③`/task` 404 終態（`0a6a56b1`）
④Ctrl+C 後協作式中止 `AnalysisCancelled`（`2b96a899`）⑤rolling warmup **預檢**移到預處理前（`_precheck_rolling_warmup`，
規則與 stage4 同一份 `_rolling_warmup_min_rows`）＋降級原因即時推送（`fallback_reason`）＋`POST /task/{id}/cancel`＋前端取消鈕／
紅字說明＋`ICTaskStatusResponse` 補 `sub_progress/warnings/fallback/cancel_requested`（response_model 會濾掉未宣告欄）。

## EVTWARMUP（2026-09-08 晚，使用者裁定「同意方向＋修第二個 bug」）
consult R1 三家一致（`handoffs/reconcile/20260908-evtwarmup-x-consult-r1/synth.md` W1–W4）：事件路徑豁免 bar-rolling warmup、
OOS＝K 線 holdout 上測試段事件 pooled IC＋HAC、`min_test_events`(30) loud、ICIR 降診斷；timeframe 接線另票 `docs/TFWINDOW_SPEC.md`。
SPEC/TODO：`docs/EVTWARMUP_SPEC.md`／`docs/EVTWARMUP_TODO.md`（R1 review 3P0/9P1/5P2 全文件層，已依 synth V1–V6 修：
status 維持兩值方案 B、分流兩段判、ICIR 消費端列全、揭露只寫事件路徑、icir 缺值 None）。改前 golden `tests/golden/evtwarmup/baseline.json`。
SPEC/TODO 三輪審查（R1 3P0／R2 1P0／R3 1P1，全文件層）皆收斂、債清；R3 三家 R2 全 CLOSED。
**第一批已實作**（`_is_event_conditional_precheck`／`_consumed` 兩段分流；`min_test_events`（stage3 後判、第三寫出點）；
`_apply_thresholds(icir_gate)`；stage6 事件路徑 ic_mean 分數字典；`_finite_or_neg_inf` 排序；serializer icir／ic_mean→null；
契約 `reasons.oos_downgrade`；前端 DegradedBanner／MarginalICTable 依 reason、types null、IsolationNote 視窗揭露）。
`tests/api/test_evtwarmup.py` 10 條；mutation `handoffs/20260908-evtwarmup-mutate.py`（M1–M11 含併項）；gate `scripts/evtwarmup_phase_gate.sh`。
發現既有 `long_short_spread` 等欄位落檔為 JSON `NaN` 字面（改前即如此）⇒ `EW-RESID-5`。

B1 commit `39b48531`＋`1a2cfd90`（M6 紅錨補強）；`evtwarmup_phase_gate.sh 1` PASS（9 紅＋C0 綠）；既有 278/280（2 紅＝EW-RESID-6）；
前端 250＋27。R4 三條（codex P1 refilter 同源、P2 預檢主線列數、P2 split=False 揭露）已修，commit `7a1dd8f0`，gate 1 PASS（12 mutation），債清。

## EVTWARMUP 第二批 TFWINDOW Task 3.1 完成（2026-09-09，commit `a17b57e7`，已 push）
`ICEngine.set_timeframe()` 三值揭露；`analyze` 於 period_alignment 後注入 `metadata.timeframe`，**全路徑**寫 `ic_window_disclosure`
（事件路徑覆蓋 `icir_role=diagnostic`）。gap2 golden 重凍：刪該鍵後 sha == 舊 golden（`handoffs/run_receipts/tfwindow_refreeze_probe.log`
`DIFF_ONLY_DISCLOSURE=YES`）。1h golden `tests/golden/tfwindow/rolling_keys_1h.json`（`window_252/756/1512`，落 `degraded_full_sample`＝TW-RESID-1 預期）。
🔴 兩處與 SPEC 措辭有落差，已交 R5 裁定：①缺／非法 timeframe 在 analyze 層於切分先 `ValueError` fail-closed，`not_applied:*` 只在引擎層可觀測；
②1h golden 值比對用 canonical-JSON sha 代替 `atol=1e-12`。`test_oos_applied_true_when_sufficient` 1h fixture 760→8500 根（門檻 1517）。
既有紅：`test_ic_1a_cut1_oos::test_flag_toggles_path` 於 HEAD~1 亦紅（未登記，R5 必答 7 裁定是否登記）。
gate 3 PASS（T1／T2 紅、C1 綠；`handoffs/run_receipts/tfwindow_mutate_phase3.log`）。白話 B33 已寫。
**code review R5 派出中**（session `20260909-evtwarmup-x-review-r5`，brief `handoffs/20260909-EVTWARMUP-X-REVIEW-R5-BRIEF.md`，債 round `4f359ce8`）。

## 下一步
R5 收斂（`reconcile_build.sh 20260909-evtwarmup-x-review-r5 <三檔>` → synth → `debt_clear.sh` → `gate.sh register-output`）＋修 finding
→ 使用者 UAT B26–B33（後端須重啟才吃新碼）→ EVTWARMUP 收案（UAT＋EW-RESID-1..6＋TW-RESID-1 登記）。
**使用者 UAT B26–B31**（`白話說明/GAP-3驗收清單.md`；B26/B27 掃描瀏覽器、B28 期間對齊、B29 進度、B30 事件 label、B31 隔離區）。
UAT 回報後依結果修；EVTALIGN 收案條件＝UAT 通過＋`EA-RESID-1..6` 皆已登記三值理由（SPEC §N）。

## 具名殘留
`EA-RESID-1` preprocessing 峰值記憶體（17 GB／8 GB）｜`EA-RESID-2` 橫截面無守衛（模組未完工，**非缺陷**）
`EA-RESID-3` `_validate_expected_frequency` 對 tz-aware 拋 `TypeError`（潛伏，現行 naive）
`EA-RESID-4` close 指紋不證原始 K 線品質｜`EA-RESID-5` `excess`/`risk_adjusted` 無 oracle（B 下不再阻擋，但登記）

## 已完成待驗收
`SCANCUBE` 五 Phase 全完成，立方體實測正確。限制：滿格 110 格不保證圖表（已列白話頭條）。

## 環境
開放債為零。`scripts/_add_cube_contract_keys.py`、`scripts/_todo_r2_patch.py` 為一次性腳本（可刪）。
`uat_samples/*`、`market_data/*` 未追蹤異動勿 commit。
