# Reconcile — 20260908-evtwarmup-x-review-r4

**來源** 20260908-evtwarmup-x-review-r4-codex.md, 20260908-evtwarmup-x-review-r4-composer.md, 20260908-evtwarmup-x-review-r4-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

composer／grok「可合併」（sentinel；驗收命令由其各自實跑，見兩家 VERIFY 表）；codex「需修補後合併」：1 P1＋2 P2，三條皆附實跑反例、皆成立，**皆已修**。

### Z1 — P1 refilter 路徑 stage6 仍吃快取 `icir`（`CODEX-R4-P1-01`）
**處置**：抽 `_redundancy_scores(event_info, stage5_results, icir_scores)` 單一 helper，analyze／refilter 共用（事件 ⇒ ic_mean 字典＋`tiebreaker_effective`；全域 ⇒ 原 icir、不寫鍵）；測試 `test_refilter_uses_same_scores_helper_as_analyze`（helper 行為＋refilter 源碼呼叫）；mutation M12。

### Z2 — P2 主線也用「事件 ∩ 測試段」覆蓋 bar 列數（`CODEX-R4-P2-02`）
**處置**：預檢只在 `event_conditional=True` 才算交集，否則 `test_events=None`、bar 列數不動；測試 `test_precheck_mainline_keeps_bar_rows_even_with_timestamps`；mutation M13。

### Z3 — P2 `ic_train_test_split=False` 之事件 run 無 `ic_window_disclosure`（`CODEX-R4-P2-03`）
**處置**：揭露搬出 split block（只依 consumed predicate），地板仍留 split block；測試 `test_event_path_without_split_still_discloses_window_and_icir_role`；M8 錨點隨之更新。

Verdict: 需修補後合併——Z1–Z3 已修並加測試／mutation（`test_evtwarmup.py` 13 條＋gap3 downgrade 套件 rc=0）；修補由 codex 於 TFWINDOW（B2）code review 以同一反例（refilter spy／200-50-3 預檢／split-off 事件 run）複驗。進 B2。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P1-01

**斷言**: 事件條件 IC 的公開 `refilter` 路徑仍把 stage6 冗餘排序交給快取的 `icir`，沒有沿用初次 `analyze` 已採用的 `ic_mean`；因此門檻重篩後 survivor 可能改變，而報告仍保留 `tiebreaker_effective=ic_mean` 的不實揭露。

**碼證**: 初次路徑在 `momentum/Analysis/ic_filter_orchestrator.py:1321-1335` 以事件 summary 的 `ic_mean` 建 `redundancy_scores`；`refilter()` 在同檔 `:2169-2185` 無條件傳 `self._ic_cache["icir"]`。`momentum/Analysis/redundancy_filter.py:378-391` 對 dict 讀設定的 `icir`，非有限值變成 `-inf`。實跑事件 refilter spy：`venv/bin/python -c '<object.__new__ ICFilterOrchestrator stub，event_info.label_source=event_label_value，呼叫 refilter>'` → `{'scores': {'a': {'icir': 9.0}}}`；同一 stub 的 stage5 summary 只有 `ic_mean=0.1`。公開入口為 `api/services/ic_analysis_service.py:2614-2630`／`api/routes/ic_analysis.py:597-615`。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#66eff72b8d56；momentum/Analysis/redundancy_filter.py#5f57224be356；api/services/ic_analysis_service.py#8a90e0f62529

[P1] 信心度=High。事件初次分析可保留 ICIR 為 `None` 並以 IC mean 做 tiebreaker，但使用者在 UI 改門檻後會經 `/refilter` 再走 stage6；此時 `None`／NaN 的 ICIR 被排序成 `-inf`，造成 survivor 選擇與初次分析不一致，且 metadata 仍可能聲稱 `ic_mean`。建議抽出單一「effective redundancy scores」helper，讓 analyze/refilter 共同以 `event_info.label_source == event_label_value` 選 summary `ic_mean`，全域保持 `icir`；加一個事件 refilter spy/regression，驗證傳入 stage6 的分數與 `tiebreaker_effective` 同步。

RECHECK：對事件報告執行一次 `analyzer.refilter({...})`，spy `_stage6_redundancy` 的第三個 positional argument；事件路徑應是 `{feature: ic_mean}`，全域路徑才是 `{feature: icir}`，且兩次 survivor 結果在門檻不變時一致。

## CODEX-R4-P2-02

**斷言**: `_precheck_rolling_warmup()` 在 `event_conditional=False`（disabled／空值／棄條件的主線語意）時仍先用 `event_timestamps ∩ test_mask` 覆寫 `test_rows`，會把主線 bar warmup 錯當成事件列數。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:3268-3284` 的 timestamp 交集計數不受 `event_conditional` 守衛，守衛只在 `:3280` 才檢查；`analyze:1147-1149` 在 filter disabled 時傳入 false；stage3 disabled 亦明確在 `:3326-3329` 回 `{"mode": "none"}`。實跑命令：`venv/bin/python -c '200 bars；50 test rows；3 event_timestamps；event_conditional=False；_rolling_warmup_min_rows=131；呼叫 _precheck_rolling_warmup'` → `{'result': {'train_rows': 150, 'test_rows': 3, 'min_test_rows': 131, ...}, 'computed_test_events': 3, 'bar_test_rows': 50}`。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#66eff72b8d56；tests/api/test_evtwarmup.py#4a76e02354cc

[P2] 信心度=Medium。這會在實際主線有足夠 50 根測試 bar、但傳入少量事件 timestamp 時錯誤觸發 rolling-warmup fallback；目前 API service 對帶 timestamp 的公開 request 會自動開啟 event filter，所以直接暴露度低，但 core orchestrator、未來 caller 與 config-disabled 路徑仍違反 SPEC 的「disabled 仍走 bar 規則」。修法是只有 `event_conditional=True` 才計算事件交集；否則保留 bar `test_rows`，並將 `test_events` 設為 `None`。現有 disabled 測試只斷言「非 None」，沒有鎖住 `test_rows` 應等於 bar rows，應補回歸。

RECHECK：同上面的 200/50/3 最小案例，修後 `event_conditional=False` 應回傳 `None`（50 >= 131 的案例可改為 50 >= min；或在案例中將 min 設為 40）且不寫事件計數；`event_conditional=True` 才記錄 3 並豁免 bar warmup。

## CODEX-R4-P2-03

**斷言**: 事件條件 IC 在 `ic_train_test_split=False` 時仍使用未依 timeframe 換算的 rolling window、且 ICIR 已降為診斷欄，但 `ic_window_disclosure` 完全缺席，前端因此不顯示窗口單位與 ICIR 角色。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:1212-1257` 把 window disclosure 放在 `if split_context is not None` 內；事件 tiebreaker／ICIR 角色判定在 `:1322-1329` 卻只依 consumed label，不依 split。實跑真實 la0 fixture：`venv/bin/python -c 'run_analyze({"ic_train_test_split":False,"event_filter":{"enabled":True,"min_events":30,"min_test_events":30}}, event_timestamps=..., event_label_values=..., event_context=...)'` → `{'status': 'ok_oos', 'oos': True, 'label_source': 'event_label_value', 'window_disclosure': None, 'tiebreaker': 'ic_mean', 'split': None}`；`frontend/src/lib/icIsolation.ts:44-54` 對缺鍵回傳 null。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#66eff72b8d56；frontend/src/lib/icIsolation.ts#8600718412ea

[P2] 信心度=Medium。這是無 split 的明確設定邊界，不影響本票 global golden 數值，但使用者看不到 event path 的 `bars_unadjusted`／`icir_role=diagnostic`，容易把診斷結果誤讀成已依 run 週期校正的 OOS 結果。建議把 disclosure 的事件 consumed 判定移到 split block 外，僅將 `test_events`／地板判定留在 split block；補一個 split-off event regression。這項不改全域鍵，亦不要求改兩值 status 契約。

RECHECK：事件 label 已 consumed、`ic_train_test_split=False` 的真實 fixture 應有完整 `ic_window_disclosure`，且 `windowDisclosureLine(report.metadata)` 非 null。

### 必答 1：分流可繞否與合法事件 run

1a. 正常兩段 predicate 是 `bool(event_label_values) and enabled`（precheck）與 `label_source == event_label_value`（consumed）；空 dict、disabled、stage3 棄條件 `mainline_return_N` 都回主線。mutation M1/M2/M3 已分別把這些守衛打壞並變紅。例外是 P2-02：timestamp 計數在 precheck 守衛外，故 disabled 仍可被事件數繞動 bar rule。fallback 會透傳事件參數並關閉 split；scan cube 每格走獨立分析，未發現本 diff 造成的跨格 cache 證據，但本輪未另跑 110 格實機網格。

1b. 合法 `event_label_value` run 不再被 bar rolling warmup 擋；stage3 後地板不足只標 `oos_guarantees=false`／`insufficient_test_events`，不走 full-sample rerun；事件 ICIR 不作門檻，初次 stage6 以 `ic_mean`。P1-01 是合法事件 run 在公開 refilter 後的例外。

### 必答 2：地板時序與事件計數

2a. 通過：地板位於 stage3 後 `:1225-1246`，且只認 consumed predicate；棄條件 `mainline_return_N` 不寫 `insufficient_test_events`。`tests/api/test_evtwarmup.py` 的 abandoned regression 綠。

2b. 通過：stage3 的 event filter 先把 features 留成實際消費事件列，再重算 train/test mask；feature filter 位於地板之後且只篩欄位，未刪事件列。因此 `test_mask.sum()` 是實際消費事件與測試段交集。缺少 scan cube 全網格實機驗證，列為未查而非通過宣稱。

### 必答 3：ICIR 消費端與 global 保真

3a. 已查到的消費端包含 `_apply_thresholds`、初次 stage6、reporter 三個排序點、`get_top_features`、summary serializer；API summary 與 survivor scalar 已有 None-safe 处理，scan cube 讀上游已 sanitize 的 summary。唯一新缺口是 P1-01 的 refilter stage6，未見另一個未處理的 ICIR consumer。

3b. global path 保留 `_apply_thresholds(icir_gate=True)` 預設與 `ic_results["icir"]` 分數；事件限定的 `tiebreaker_effective`／window disclosure 不寫 global。實跑 `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` 後，`global_run` 逐鍵與 `tests/golden/evtwarmup/baseline.json` 相同（直接 diff rc=0）。指定的 `test_gap2_golden.py` 前兩項到 40% 綠，但 budget benchmark 執行約一小時仍無新輸出，Ctrl-C 後 rc=130；不宣稱 gap2 全套通過。

### 必答 4：status／root／survivor／前端誠實性

4a. split event floor 的 root 是既有兩值 `degraded_full_sample`、`oos_guarantees=false`，reason 是 `insufficient_test_events`，fit mode 是 `train_mask`；survivor／TS 未擴 enum，banner、marginal table、AI JSON 已按 reason 改文案。P1-01 會使 survivor 選擇與 metadata 的 tiebreaker 說法不一致。

4b. 三個本票指定的 Full-sample 消費端已 reason-aware；`insufficient_test_events` 文案明確寫 holdout 仍套用、沒有 full-sample 擬合。未發現本 diff 仍把該 reason 說成 full-sample；P2-03 是缺揭露，不是錯誤文案。

### 必答 5：mutation 充分性

5a. 在 `/tmp/evtwarmup-r4-codex-clone` 接入既有真實 la0 H5／kline cache symlink 後，`venv/bin/python handoffs/20260908-evtwarmup-mutate.py --phase 1` 實跑：M1/M2/M3/M5/M6/M7/M8/M10/M11 全 rc=1，C0 rc=0；`SUMMARY pass=10 fail=0 skip=0 / 10`、`UNCOVERED=0`、`RESTORED clean=True`。M4/M9 是共享 predicate 的併項；M9 的 abandoned 行為由既有 e′ test 覆蓋，但 M4「只改 stage4 caller、不改 helper」沒有獨立 mutation anchor，不能宣稱已獨立證明，建議補一個 caller-level mutation/test。

5b. 紅因是行為斷言：每個 mutant 都先收集專屬 pytest selector，結果為 pytest rc=1；C0 全測 rc=0。第一次 clone 缺 gitignored fixture 的 rc=1 是環境 setup error，接入真實 fixture 後才採納上述 10/10 結果。

### 必答 6：是否有 ≥10× 不必要複雜

無。B1 的主要變更集中在既有兩段 predicate、地板、ICIR 消費端與既有 report/UI contract；P1-01 可用共用 helper 收斂重複分支。沒有證據顯示需另建架構。

### 必答 7：可否並進 B2 TFWINDOW

不可直接合併。先修 P1-01；P2-02、P2-03 可隨同修補或登記，但至少需補 refilter regression。global golden／gap2 保真 gate 完成且沒有新 P0 後，才可進 B2；TFWINDOW 仍應維持獨立 commit 與 golden。

### §1 其餘類別

矛盾／互斥：除 P1-01 的 analyze/refilter 分歧外，無新的 SPEC/TODO 互斥。

漏項／端到端：P1-01 是後端 API refilter 端到端漏接；其餘事件 banner、marginal、AI JSON、TS null 已接線。

不可測驗收：B1 golden、定向 API tests、serializer tests 與 mutation gate 可執行；scan cube 110 格與無 split disclosure 缺專門回歸。

Quant／資料品質：未發現新增 look-ahead、跨 symbol contamination 或公式改動；P1-01 是 survivor selection consistency 問題。

過度工程：無 ≥10× 複雜度 finding。

OOM／並行：本 diff 未新增並行或資料複製控制流；無新 finding。

Cache 正確性：初次 `_ic_cache` 的 event_info 存在，但 refilter 未用它選 effective tiebreaker（P1-01）；未見跨 symbol cache key 新問題。

API／型別／相容：事件 `icir: number | null` 與前端測試已對證；refilter survivor 行為不一致仍待修。

測試品質：phase-1 mutation 10/10 有效；M4 caller-level mutation 與 scan cube 110 格尚未獨立覆核。

Agent 可執行性：Task 檔案、函式與 gate 明確；無新 finding。

必要性／短命工：無。B1 的事件 disclosure 會存活；TFWINDOW 的後續 global disclosure 是既定範圍，不屬本批白工。

### 被當成事實的未驗證假設（§0）

無新增未驗證假設可列為 blocking。scan cube 110 格、無 split event path 的回歸，以及 gap2 budget benchmark 分別是未查／未納入專門回歸／因長跑無終態而未驗證，已明確標示，不當作通過。

## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對後無需阻擋合併的 P0／P1／P2 finding；B1 實作與 SPEC R2 逐條一致，必答 1–7 雙向有碼證，mutation 集合與 brief oracle 對位。

**碼證**: `git diff 8f10d2e1..HEAD` 對照 `docs/EVTWARMUP_SPEC.md` §C-3／§C-4／§C-6／Task 1.1–2.1；`venv/bin/python -m pytest tests/api/test_evtwarmup.py tests/api/test_gap3_oos_downgrade.py -q -rs` → 53 passed, 0 skip, rc=0；vitest 四檔 → 27 passed, rc=0；讀碼 `ic_filter_orchestrator.py:3233-3280`（分流）、`:1225-1257`（地板）、`:3856-4332`（ICIR gate）、`ic_reporter.py:22-30`／`:609-621`／`:950-952`；`shasum -a 256 -c handoffs/20260908-evtwarmup-r4-baseline.sha` → 全 OK。

**來源摘要**: docs/EVTWARMUP_SPEC.md#713968799d0210dce56f336aa2e0da727f26fcea7ae9f64d981e8bbbe99c4eaa;momentum/Analysis/ic_filter_orchestrator.py#9b3524583e64c3e9ab721590f3330e77182e35f35d25fb04e7063c351810c2c9;tests/api/test_evtwarmup.py#4a76e02354cc96b08e3ac58214c90463c1a32d7ad5d59c0006f7df8df6e1b5ae;handoffs/20260908-evtwarmup-mutate.py#d1d15bbfff1a9b0ef94b31fcbd8c1ac95da2ee297215a5220748fac3067ba814

[NON-BLOCKING] 信心度=High。核對依據：分流兩段判＋stage4 consumed 守衛；地板 stage3 後 consumed predicate＋(e′) 測試；ICIR 門檻跳過與消費端 `_finite_or_neg_inf`／sanitizer；三寫出點優先序；前端／AI JSON reason-aware；全域 golden 子集不變。brief NOT_RUN 項列入 §0 unverified，不升格 finding。

---

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——Task 1.1／1.2／2.1 與前端接線在碼證＋驗收命令＋clean-clone mutation（UNCOVERED=0）下與 SPEC §C-3／§C-4／§C-6／§G 一致，無新 P0／P1。

**碼證**: `pytest tests/api/test_evtwarmup.py tests/api/test_gap3_oos_downgrade.py -q -rs` → 53 passed 0 skip rc=0；探針 `global_run` 逐鍵 == golden、`event_run.reason=insufficient_test_events`／`test_events=13`；vitest 27 passed；clean-clone `evtwarmup-mutate.py --phase 1` → M1/M2/M3/M5/M6/M7/M8/M10/M11 紅＋C0 綠、UNCOVERED=0；baseline sha 1137 OK；必答 1a–5b 雙向見上表。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#66eff72b8d56；momentum/Analysis/ic_reporter.py#c2e1fbaaf094；docs/EVTWARMUP_SPEC.md#713968799d02；handoffs/20260908-evtwarmup-mutate.py#d1d15bbfff1a

[MINOR] 信心度=High。哨兵非實質缺陷；合併判定見 Verdict。

---

ASSUMPTIONS_VERIFIED: 兩段分流不可用 is-not-None／enabled 單判繞過；地板只在 consumed＋stage3 後；棄條件不寫 insufficient_test_events；ICIR 事件路徑診斷化且消費端 None-safe；全域 golden／global_run 不變；mutation 紅集合＝oracle；兩值 status＋reason 分文案
TESTS_RUN: pytest evtwarmup+oos_downgrade 53 passed rc=0；probe global_run==True event_run 形狀符合 §G；vitest 27 passed；mutate phase1 UNCOVERED=0 rc=0；baseline sha rc=0；gap2 `-k 'not budget_bench'` 4 passed rc=0；budget_bench 另跑（見交接若未齊則標未驗證）
FAILURES_SEEN: 首跑 clone 缺 la0 fixture → C0 假紅（非產品）；共用樹誤留 C0 註解 → 已 checkout 還原
SCOPE_CHANGES: none（唯讀；/tmp clone 僅供 mutation）
NUMERIC_OR_SCHEMA_IMPACT: none（本輪未改碼；產品已落地之 null icir／ic_mean 與既有 EW-RESID-5 邊界如 brief）
產出檔: handoffs/20260908-evtwarmup-x-review-r4-grok.md

STATUS: DONE
