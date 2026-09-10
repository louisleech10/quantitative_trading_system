# HANDOFF — 當前任務狀態

**更新：2026-09-11 凌晨｜票：`SPLITUNIFY`（大；RISK a,b,c,d）｜狀態：SPEC/TODO **v5**；四輪規格審＋五輪戳記全收斂。**B1／B2a／B2b／B2c 全部完工並經審碼**（B1+B2a 一輪、B2b **三輪**、B2c 一輪），全部修補完成、債已清。下一步＝**B3（接線）**。**

## 使用者離線授權（2026-09-10 深夜，逐字）
> 「我要睡了，你繼續做完，有問題找委員會討論共識，做完前不要停下來」

⇒ **不停、不問、斷路器交委員會共識決**；分歧看碼證不數人頭，不決則採較嚴版並具名殘留。

## 🔴 本 session 最重要的四件事

1. **戳記閘攔下我三處收斂掉項。** codex（`-STAMP-R1`）REJECTED、composer（`-STAMP-R2`）
   附註 ⇒ 我把 19 條 consult findings 逐條重對，**11 條歸屬錯誤或缺漏**（grok 的 7 條全錯）。
   consult synth 由 5 個決議項修正為 **8 個**。五輪戳記後三家全數 APPROVED，
   `reconcile_stamps_check.sh` rc=0。
2. **C-0（接線落點）**：`EventSplitPlan` 唯一 producer `split_events` 只被 `pipeline.py:691`
   呼叫，其唯一生產 caller `case_import_service.py:1610` **既無 `SplitPlan` 也無 feature
   universe** ⇒ v1 的「投影」沒有落點。裁定：事件掃描端**恆走** event-study-only，
   本票不新增 universe 供給路徑（殘留 `R-5`）。
3. 🔴 **R3 codex 抓到我造成的真 OOS leakage（本 session 最嚴重）**：v3 的投影只做集合成員
   判定，簽名裡沒有 `label_end_ms` ⇒ 把 `event_split.py:114` 那道
   `label_end_ms > test_start - embargo` 的答案窗 purge **整個刪掉**，
   答案窗已跨進測試段的 train 事件會留在 train。而 C-1 附帶約束①「不得刪除任一既有 guard」
   是我自己寫的。R1／R2 兩輪都沒抓到，R3 才由 codex 以「介面可執行性」掃法抓出。
   ⇒ v4 改**兩段式判定**（先驗答案窗跨界 ⇒ purged，再做集合判定），新增 `M-SU-13`。
4. **我自己的探針否證過我自己兩次**：①多 symbol 全域 vs per-symbol 不等價
   （12 列 vs 8 列）；②「兩端各自用同一公式算 canonical 邊界」不成立——真實 ETHUSDT 1h
   20352 列，EVTALIGN 裁頭尾後邊界位移 5 根→2h、24 根→10h、168 根→67h。

## 檔案
- SPEC `docs/SPLITUNIFY_SPEC.md`（**v5**）／TODO `docs/SPLITUNIFY_TODO.md`（**v5**）
- GAP-3 兩條凍結鏈（**不同慣例，別搞混**）：`docs/GAP3_EVENT_UX_SPEC.D-002.md`（D-00N 慣例）
  與 `docs/GAP3_EVENT_SPEC_AMENDMENTS.md`（該檔檔頭逐字指定的路徑，**非** D-00N）
- consult 收斂 `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`
  （D1–D8；body-hash `120b4d042d38…`；三家 APPROVED）
- 規格審收斂 `handoffs/reconcile/20260911-splitunify-x-review-r{1,2,3,4}/synth.md`（C1–C13／D1–D11／E1–E7／F1–F4）
- B1＋B2a code review 收斂 `handoffs/reconcile/20260911-splitunify-b1-review-r1/synth.md`（G1–G8）
- 主委自產審查 `handoffs/20260911-splitunify-claude-selfreview{,-r2,-r3}.md`
- 探針 `handoffs/20260911-probe-splitunify-universe-gap.py`
  ＋ receipt `handoffs/run_receipts/20260910T154323Z-splitunify-universe-gap.log`
- 白話 `白話說明/SPLITUNIFY規格白話.md`、`白話說明/SPLITUNIFY施工進度.md`

## 已完工（全部 commit+push）
- **B1**（`9607430d`＋`1be5be3f`）：`D-002` 延伸檔、`GAP3_EVENT_SPEC_AMENDMENTS.md`、
  `split_unify.json`＋8 條契約測試、既有紅 **19 條** nodeid 基準＋receipt（含 `pytest_rc=1`）。
- **B2a**（`a58754d6`＋`1be5be3f`）：`split_preview.holdout_boundary`＋測試。
- **B2b**（`864efeb9`→`e2e4314c`→`a8474406`→`bc561c7d`）：`split_projection.py`
  （兩段式判定＋`build_event_keys`＋`_assert_event_keys_wellformed`）、
  `event_split.py` 抽出 `build_time_clusters`／`time_cluster_bucket_ms` 共用、
  `split_preview` 新增 `assert_epoch_ms_array`／`assert_positional_rows` 兩支共用 validator。
- **B2c**（`be2f0735`＋K1–K5 修補）：`scripts/freeze_splitunify_golden.py`、
  `tests/golden/splitunify/splitunify_golden.json`、`test_splitunify_golden.py`（**9 條**）。
- **審碼**：B1+B2a 一輪（G1–G8）、B2b **三輪**（H0–H7／I0–I6／J 三條 P1）、
  B2c 一輪（**K1–K5**），全數修補完成；`debt_clear` 已清
  （round `64f80baa…`，session `20260911-splitunify-b3-review-r1`）。

## B2c 審碼收斂（K1–K5，`handoffs/reconcile/20260911-splitunify-b3-review-r1/synth.md`）
- **K1**（三家獨立命中）G-5③ 只驗 `label_start_ms` ⇒ **修法與三家提的不同**：前半照修（驗**兩端**），
  後半「缺 endpoint 必 purge」**不能照做**（R4／F1 明訂 endpoint 檢查不進投影）⇒ 改驗**前置條件** `precondition_breaches`。
- **K2** fingerprint 只凍 hash ⇒ **錯的也會被自凍結**；改為一併凍**明文** positions，測試端獨立重算 sha256。
- **K3**（最深）oracle 與 actual 共用 fixture／邊界 ⇒ 新增**手推錨點**（由 fixture 常數手算
  `split_point=140`、test `144..199` 共 56 列），不經邊界函式也不經投影。
  **實跑證明關鍵方向**：把 `holdout_boundary` 改壞後 `--write` 重凍，`-k hand_derived` 仍 FAILED。
- **K4** 失敗未指名首個 mismatch ⇒ `_fingerprint_diff`。**K5** 壞 JSON 裸 traceback ⇒ `GOLDEN CORRUPT` 分級。

## 現況數字（皆主委實跑）
- `test_splitunify_derive.py` **47 passed**｜`test_splitunify_golden.py` **9 passed**｜
  `test_splitunify_contract.py` **8 passed**。
- `freeze_splitunify_golden.py` → `GOLDEN OK` rc=0；可證偽兩方向：篡改 golden ⇒ rc=1 指名 `te2`；
  改壞生產碼（拿掉答案窗 purge）⇒ **3 failed**。
- mutation `handoffs/20260911-splitunify-b2b-mutate.py` **UNCOVERED=0**（**24 條**）。
- 負向注入 `handoffs/20260911-probe-splitunify-negative-injection.py` **9/9 全擋**。
- 回歸 core＋event_samples＋三支 splitunify → **684 passed**。
- 解耦逐值等於 `scripts/decouple_baseline.txt`（R2=1 R3=17 R4=3）。

## B3（接線）— 實作完成，待三家審碼
- **Task 3.1**：`_build_holdout_split_plan` 改走 `holdout_boundary`（🔴 IC 主線索引是
  DatetimeIndex **或 epoch 秒** ⇒ 呼叫前套本模組既有的 `_normalize_ic_time_index`；
  `base_universe_hash`／`time_bounds` 仍用**原始**索引，避免動到既有指紋）；
  `pipeline.run` 新增 `train_plan`／`test_plan`／`feature_index`／`selected_timeframe`
  **四者同時給才走投影、給一半 fail-closed**；投影路徑禁帶 `config.split.embargo_ms(_by_symbol)`。
- **Task 3.2**：多 symbol fail-closed 沿用 B2b；**自查補第四道**——兩 plan 之
  `base_universe_hash` 必須相同（symbol 相同不代表 universe 相同）。
- **Task 3.3**：`case_import_service.analyze` **恆走** event-study-only（`run_with_params`
  分支整段移除，不留死碼）；`run_event_study_only` 之 summary **刪掉** `n_train`／`n_test`／
  `n_purged`（不是填 0）；`tables._common_constraint_block` 新增 `estimand_scope`；
  前端 `splitCapability.ts`＋`EventTablesPanel` 揭露兩條可分辨的 reason 並隱藏切分計數。
- **實跑**：B3 mutation `handoffs/20260911-splitunify-b3-mutate.py` **UNCOVERED=0**（9 紅＋C0 綠）｜
  `tests/momentum/event_samples` 616 passed（含新 `test_splitunify_wiring.py` 8 條）｜
  `tests/api/test_splitunify_event_study_only.py` 7 passed｜前端 vitest **713 passed/92 files**｜
  `npm run build` rc=0｜解耦 R2=1 R3=17 R4=3。
- **`tests/api` 逐檔對照**（先 `git stash` 跑 HEAD、再跑本批）：HEAD 8 failed → 本批 9 failed，
  **唯一新增**是 `test_gap3_horizon_declaration_07`（前提被 Task 3.3 消滅 ⇒ 已改寫為
  「宣告的數字不得靜默消失」，該檔 10 passed）。其餘 8 條為既有紅。
- **G-2 byte golden 更新**：`common` 新增鍵 ⇒ `test_return_table_by_label` 之 sha 換值；
  **變更範圍已逐項對證**（拿掉新鍵後重算逐字等於舊值）。
- 殘留新增 `SU-RESID-3`（投影未對證 plan universe ＝ 傳入之 `feature_index`；
  現行 hash 是秒語意、事件側是毫秒，改 hash 輸入會移動既有 IC golden digest）。
- **`tests/momentum/Analysis` 全套（16 分 41 秒）：20 failed / 1166 passed / 15 skipped**。
  對照 B1 凍結之 19 條清單：**沒有一條變短**，多出**一條**
  `test_gap2_survivor_persist.py::test_hermetic_no_production_write`。
  🔴 **已證明非本批造成**：`git stash` 掉 B3 全部改動後在 HEAD 上**同樣 FAILED**。
  真因是該測試的「fresh」判準＝`mtime >= 輸出檔 mtime − 3600`，等於**過去一小時內**
  有人寫過 `data_cache/reports/ic_survivors_*.json` 就判紅——而 `tests/api` 全套
  （本 session 04:38–04:47 跑過）確實會寫那兩個檔。⇒ 兩件事各自成立：
  ①這條測試對「同一小時內跑過別的套件」不 hermetic（時間窗判準）；
  ②**真的有測試在寫生產路徑** `data_cache/reports/`。兩者皆早於本票，列入 `REDSWEEP`。
  **刻意不把它加進凍結清單**——那是把新紅合法化（測試遊戲化），不是修好。

## B3 三家審碼 R1（`handoffs/reconcile/20260911-splitunify-b4-review-r1/synth.md`；債已清）
三家 findings **收斂成同一條**，分歧只在嚴重度：codex P1／**不可進 B4**；composer MAJOR／
可進但「B4 接 IC 前必須關」；grok P2／不擋。🔴 **依較嚴版當輪修完**——不是數人頭，是碼證
只有一個方向：三家**各自獨立**跑出可重現的靜默錯分，而判「不擋」的理由都是時序性的
（「現行生產呼叫點不走投影」），那個理由會隨 B4 第一個 caller 消失。
- **L1（三方獨立命中）**：投影只比兩 plan 的 `base_universe_hash` **字面**，沒對證
  「plan 的 universe ＝ 傳入的 `feature_index`」。反例：①plan 建在較短網格＋長 index
  ⇒ 靜默成功；②index 同長度整體平移 50 根 ⇒ `ev3` 由 test 變 train、`labels_equal=False`、
  全程 `NO_RAISE`。⇒ 以 `plan.time_bounds` 與傳入 index 在該 plan **首尾列**上逐值對證
  （`_plan_bounds_as_ms`；單位**型別驅動**：datetime-like 轉毫秒、整數必須本來就是毫秒，
  餵秒指名擋下，**不做** magnitude 猜測）。四條測試＋mutation `M-SU-B3-10`。
- **L2（我的 brief 前提過寬）**：我寫「事件端永遠拿不到 FF run」，codex 實查指出
  `ic_analysis_service` 的事件分支（`event_import_id`＋FeatureLibrary run）**確實同時握有
  事件與特徵 universe**（已複查屬實）。正確敘述＝**`case_import_service` 的掃描端**拿不到
  （Task 3.3 裁定不變），**IC 路由那條有**——那正是 B4／R-5 要接投影的地方。
- **L3**：`test_hermetic_no_production_write` 維持不加進凍結清單，另開 `REDSWEEP`（三家附議）。
- **L4**：四參數介面三家一致判「對」；B4 之約束＝由**同一** `features_df` 一次產出
  `(train_plan, test_plan, feature_index)` 三元組，禁 service 層拆開組裝。
- **L5**：前端再露 `execution_mode`／`estimand_scope` ⇒ 併入 B4 一起做。
- `SU-RESID-3` **收窄**：現在只剩「首尾相同、中間間距不同」的對抗性網格（plan 身上只有兩個
  端點可比）；要關掉需 producer 隨 plan 傳完整時刻指紋（動 IC 契約），屬 R-5／B4 之後。

## B4（報告與畫面只暴露一個驗證段）— 實作完成，待三家審碼
- **canonical 揭露**：`metadata.split_unify = {n_test, split_authority, boundary_hash,
  per_symbol_counts, reason}`，唯一產生點 `split_projection.build_split_unify_disclosure`；
  只在事件路徑寫（全域 run 不寫 ⇒ 全域報告逐位元組不變，G-2）。
- **`boundary_hash`**：sorted＋int64 毫秒＋無空白 JSON 之 sha256（`split_preview.boundary_hash`）；
  三個約束各配一條可證偽測試（換順序同雜湊／換時刻不同雜湊／餵秒被擋）。
- **「恰一個」怎麼判**：`split_unify.json` 新增 `test_segment_count_keys` **封閉登記**
  （`canonical` 恰一個、`diagnostic_only`、`row_semantics_not_event_count`）——散文判準會漂。
- 🔴 **實測關鍵事實**：`test_rows=335`、`n_test=13`——335 根 K 線、其中 13 根上有事件。
  **兩個數字都對，但只有一個是「驗證段事件數」**；測試釘 `0 < n_test <= test_rows`，
  **不是**硬要相等（我第一版寫成相等，被實跑打掉）。
- **fail-closed**：`n_test` 為 `null` 不是 `0`，且 hash／counts 一併清空（留半套數字更糟）。
- **前端**：`SplitUnifyBadge`（單一數字＋來源標籤，缺鍵不渲染）＋`splitAuthority.ts`
  （值集自契約讀）；L5 併做——事件掃描頁加「表已算好，但估計量範圍是全樣本」。
- **實跑**：`tests/api/test_splitunify_disclosure.py` **12 passed**｜B4 mutation（9＋C0）
  **UNCOVERED=0**｜前端 **721 passed / 93 files**、`npm run build` rc=0｜
  事件路徑＋event_samples＋core **676 passed**｜`tests/momentum/Analysis` **19 failed /
  1172 passed**＝**逐條等於**既有紅清單（無新增、無變短）｜解耦 R2=1 R3=17 R4=3｜
  survivor golden rc=0、splitunify golden `GOLDEN OK`。

## 下一步（順序）
1. **B4 三家審碼** → 收斂 → 收票。
2. `GLOBALH`（中票）→ **使用者 UAT B26–B34**。

## 🔴 既有紅盤點（非本票造成，建議另立 `REDSWEEP`）
🔴 以 B1 凍結之 receipt 為準：`tests/momentum/Analysis` **19 failed / 1103 passed / 15 skipped**（清單 `tests/baselines/analysis_known_failures.nodeids`）；舊記的「20 failed / 1615 passed」是不同收集面的舊量測，不再引用：①8 條單獨跑會綠（測試間污染）
②golden digest 3 條 ③inventory／contract sync 漂移。B1 之 Task 1.3 會把它們凍成逐條 nodeid 清單，
驗收改「只准變短」的方向性判準（不再用聚合計數）。

## 後續票序
`SPLITUNIFY` → `GLOBALH`（中票）→ **使用者 UAT B26–B34**（最後）。

## 踩坑（本 session 新增）
- FF run 之 `data_cache/features/**/timestamps.parquet` 是 **epoch 秒**（int64）。
  同一條路徑上流著 positional／秒／毫秒三種單位。
- `_normalize_ic_time_index`（`ic_filter_orchestrator.py:259`）是**「秒」語意**，
  餵毫秒會 raise。事件側時鐘是毫秒 ⇒ 不可復用它。
- `reconcile_cluster_attribution_check.sh` 只驗「ID 字串出現在檔內」，**不驗歸屬是否正確**
  （殘留 `SU-RESID-1`）。攔下兩類收斂失誤的是委員逐條對照，不是機檢。
- `gate.sh dispatch` 帶 `--spec` 會被當 impl 派工而要求 `--brief`＋`--reconcile`；
  review／stamp 派工不要帶 `--spec/--todo`。session `kind` 只准
  `{impl, review, stamp, consult, fix}`——`confirm` 會 fail-closed。
- `debt_clear.sh` 要求 `sources.lock` mode=review；discovery 需
  `reconcile_build.sh <session> --mode review --rebuild`（**不可**再帶委員檔）。
- 🔴 **grep 加 `head -N` 會讓我做出錯誤結論**：v3 曾據截斷輸出宣稱
  `extract_event_patterns` 無任何 caller，實際有 8 處測試 caller（`CODEX-R3-P2-04` 抓出）。
- 🔴 **GAP-3 有兩份凍結 SPEC，修訂慣例不同**：`GAP3_EVENT_UX_SPEC.md` 走 `D-00N`；
  `GAP3_EVENT_SPEC.md` 走 `GAP3_EVENT_SPEC_AMENDMENTS.md`。B1 曾在 D-002 宣告一個
  在其 BASE 內根本不存在的 heading（`Task B1.3` 住在兄弟檔），由 `CODEX-R1-P1-01` 抓出。
- 🔴 **pytest `-q` 的進度條殘片會混進 `^FAILED`**：30 行中只有 19 行是真 nodeid，
  萃取必須 `grep '::'`；且**加了過濾就要同步改驗證條件**（我漏了，`CODEX-R1-P1-02` 抓出）。
- 🔴 **抽出共用函式會讓「新 vs 舊」的回歸測試變成同義反覆**：抽出後舊實作自己就呼叫新函式，
  該測試永遠綠。B2b 犯過一次（567 passed 掩蓋了它）。⇒ 抽出時必須同步把 oracle 換成
  **獨立凍結**的期望值（`tests/golden/splitunify/clusters_oracle.json`）。
- 🔴 **fail-closed 要寫在「不變式」上，不是「有沒有給」上**：B2b 兩輪審碼共九條 P1，
  全部是這個形態（身份對帳、symbol 相等、索引遞增、唯一性、finite、整數、正數、區間有序）。
- 🔴 **code review 的必答必須明確要求「主動餵壞資料」**：只寫「請審查」時，三家會做正向
  對照而漏掉這一整類；R2 brief 加了負向注入清單後，R1 零意見的那一家找到兩條。
- 🔴 **委員為證明「golden 不存在會紅」而移走 golden，收尾只還原了一份**：B2c R1 後
  `tests/golden/splitunify/clusters_oracle.json` 留在委員自建的 `splitunify_hidden/` 裡，
  主線兩條 cluster oracle 測試 `FileNotFoundError` 紅了一整輪。⇒ **審碼收尾必查
  `git status tests/golden/`**；brief 的「請用暫存複本」要改成「暫存複本放 repo 外」。
- 🔴 session 命名：`kind ∈ {impl, review, stamp, consult, fix}`、`batch` 須為 `b<數字>` 或 `x`
  （`b2b` 不合規，用 `b2`）；且 `--task-id` 必須與 session 名**同步大寫對應**。

## 殘留
`EA-RESID-1..6`；`EVTLABEL R-1..R-9`；stage6b `role="diagnostic"`；`REDSWEEP` 約 17 條；
`SPLITUNIFY R-1..R-5`、`SU-RESID-1`、`SU-RESID-2`（見 SPEC §N）；
另有一批**早於本票**的白話說明過期（`GAP-3事件型討論`／`GAP-3施工看板`／`GAP-3驗收清單`／
`IC健檢偵察結果`／`README`，來自 EVTLABEL 期間的 commit），依「面向未來不溯及既往」記錄不追。
