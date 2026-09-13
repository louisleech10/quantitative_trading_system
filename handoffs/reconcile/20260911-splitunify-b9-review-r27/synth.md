# Reconcile — 20260911-splitunify-b9-review-r27

**來源** 20260911-splitunify-b9-review-r27-codex.md, 20260911-splitunify-b9-review-r27-composer.md, 20260911-splitunify-b9-review-r27-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **M1 golden `--write` 整檔覆寫會靜默丟既有頂層鍵**——「`--write`在`scripts/f」 | P1 | CODEX-R27-P1-01 | 採納（該家以 sentinel 實跑證實 LEGACY_PRESENT False。已加護欄：新 payload 之頂層鍵集合須為既有之**超集**，任一既有鍵會消失即拒寫；值本身允許改變，那是重凍的正當用途且會先被 GOLDEN MISMATCH 攔下。🔴 **主委具名偏離該家修法**：該家要求「主檔保留 v8 舊值、只新增 v9 鍵」，但 `main()` 是拿**現行投影結果**與主檔比對——主檔若凍住 v8 值則比對永遠紅，該形狀不可實作；已改採等效且可實作的「不得丟鍵」護欄，v8 錨點之保全另由 M2 承擔） |
| **M2 v8 不可變基準可被「同步改寫檔案與旁檔」繞過**——「v8檔與`.v8.sha256`的完整性」 | P1 | CODEX-R27-P1-02 | 採納（該家實跑 NORMAL_MODE_RC 0／MATCHING_SIDECAR_ACCEPTED True。已改三層且**兩種模式都跑**：碼內外部錨 `V8_BASELINE_SHA256`（與 golden 目錄不同介質，改它必現於 diff）＋旁檔須與外部錨一致＋檔案內容須與外部錨一致。主委實跑該家探針複驗：改寫兩者後正常模式 rc=1、訊息指名「同步改寫檔案與旁檔之繞法在此擋下」） |
| **M3 (G-4e) 第三份判準缺席，投影與 oracle 同錯仍綠**——「`_event_keys()`沒有字面`」 | P1 | CODEX-R27-P1-03 | 採納（該家實跑 SAME_WRONG_PROJECTION_ORACLE_PASSES_G3B True。fixture 每列加**人手逐筆填入**之 `expected_side`，`main()` 做投影／oracle／人手三方相等。🔴 攤平函式**明禁含任何判準**，否則它退化成第三份**推導**而非第三份**判準**。主委實跑複驗：把投影與 oracle 同時改成同一錯值 ⇒ **G-3b 仍綠、G-4e 抓到**。🔴 三份人手同錯仍會一致，此誠實邊界具名保留） |
| **M4 步驟 0 把多標的 Mapping 餵給單標的 validator 得裸 `AttributeError`**——「`EventSamplePipeline」 | P1 | CODEX-R27-P1-04 | 採納（該家實跑 MAPPING_STEP0_EXCEPTION AttributeError。🔴 **主委另查明**：多標的**本來就到不了**此入口——`derive_event_split_from_plans` 之 Mapping 形式為 (plans, event_keys, feature_index_by_symbol)，與 `run` 的位置參數對不上 ⇒ 真正的缺陷是我的步驟 0 把 derive 原有的具名 fail-closed 變成**沒有病名**的錯誤。已依該家修法之最小版本改為具名拒絕，**不在此造第二份多標的邏輯**） |
| **M5 答案窗 purge 取 `label_end_ms.max()` 靜默吞掉事件級欄位不一致**——「答案窗purge使用同一event的`l」 | P2 | CODEX-R27-P2-05 | 採納（該家實跑 LABEL_END_MISMATCH_ACCEPTED True。已改唯一性 fail-closed，判準與 `decision_at_ms` 錨點唯一性同源：事件級欄逐列不同即上游壞掉，不得以 `max`／`first` 聚合吞掉。**這正是主委 brief 之 assumed 第 4 條，被該家實跑否證**） |
| **M6 錨點唯一性分支被更早的重複閘搶先而不可達**——「`manifest.table`的dup」 | P2 | CODEX-R27-P2-06 | 採納（該家實跑 ANCHOR_GUARD_REACHED False。已把錨點閘前移到 `man_dupes` 之前 ⇒ 帶著**不同錨點**的重複 manifest 得到「錨點不唯一」這個病名；並補**成對**測試守住「純重複（錨點一致）仍是裸 `ValueError`」之既有錯誤型別契約。**這正是主委 brief 之 assumed 第 2 條，被該家實跑否證**） |
| **M7 TODO `Task 2.2` 仍以 live 祈使句要求 cutoff 集合成員判側（同型第七次）**——codex「TODO`Task2.2`第208-21」／grok「`docs/SPLITUNIFY_TOD」 | P1 | CODEX-R27-P2-07, GROK-R27-P1-01 | 採納（🔴 **兩家撞題**。grok 另實跑證明：依該舊文把廣播迴圈改回 per-cutoff ⇒ test_event_level_anchor_broadcasts_side_to_all_feature_tf 轉紅。要點 1／2／4 三處已標 SUPERSEDED 並保留原字面。**同型第七次發作**——前六次見 v19–v21 沿革） |
| **M8 `SU-RESID-2` 帳面未隨批次前進**——「`SU-RESID-2`（TODO§E`」 | P1 | GROK-R27-P1-02 | 採納（9.2b 已落地卻仍寫 blocked-by:Task 9.2b／9.3 尚未實作，會誤阻 B9D 或讓狀態帳與碼不一致。兩檔同步為「尚未關閉者只剩 `Task 9.3`」，9.2b 半句刪節保留） |
| **M9 SPEC 四處仍以 9.2b 前碼態為「現況」**——grok「SPEC§P`Task9.2b``:21」／composer「SPEC§P`Task9.2b`「現況碼」 | P2 | GROK-R27-P2-01, COMPOSER-R27-P2-01 | 採納（🔴 **兩家撞題**。§P 之「現況碼證：`decision_at_ms` 命中數為 0」、§V `:261` 之「現行碼會給出 1h=test／4h=purged」、§G (G-4c) 之「目前也以 `feature_cutoff_ms` 判側」、以及 `_derive_single_symbol` docstring 之兩段式集合成員——四處皆標為「9.2b 前快照」並補現行描述。composer 判此條 doc-literal-only、不阻擋 B9D，grok 判併同批最省；主委採「同批修完」） |

### 本輪裁定

1. **三家對主委四條 assumed 之判定**：**A1 成立**（xfail fixture 依 SPEC §V 形狀遷移、node id 未改，codex 逐字認可）、**A3 成立**（三條舊測試屬語意遷移非刪測換綠）、**A2 不成立**、**A4 不成立**。🔴 **被推翻的兩條正是主委自己最沒把握的那兩條** ⇒ 連續第五輪（R18／R21／R22／R25／R27）自標疑慮被證實或被具體否證，做法維持。
2. **11 條全數採納並修完**；回歸六路 **728 passed、0 failed、0 xfailed**；兩份 `doc_format_precheck` rc=0。
3. 🔴 **M1 之處置與該家修法具名偏離**（理由見群集表）：該家要求主檔頂層鍵凍住 v8 值，但 `main()` 是拿現行投影結果與主檔比對，該形狀會使比對**永遠紅**、不可實作；改採等效之「不得丟鍵」護欄，v8 錨點之保全由 M2 之三層檢查承擔。此偏離請 r28 覆核。
4. **SPEC 進 v22**，新 body sha256 為 dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132 ⇒ v21 之三家戳記失效，須重簽。
5. 🔴 **同型第七次（M7）**：契約面一改動，舊 Task 段就落後。**本輪起再加一條**——`Task 9.3` 動工前之 register 重掃 receipt，須**一併**列出「本批改過的契約在 SPEC 與 TODO 的全部落點」，不再只掃 register。
6. **下一步**：派 `review-r28` 做 M1–M9 閉合再驗證 ＋ 對 v22 新 body 三家重簽；齊備後進 `Task 9.3`（批次 **B9D**）。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R27-P1-01

**斷言**: `--write` 在 `scripts/freeze_splitunify_golden.py:431-435` 以 `{_doc, **actual}` 整檔覆寫主 golden，沒有保留既有 11 個頂層鍵的護欄。實際檔案的 11 個 shared keys 中 `g1_membership`、`g3b_oracle`、`g4_per_symbol_n`、`g5_answer_window` 已相對 v8 改變；`g1_membership_v9`／`g3b_oracle_v9` 又只是目前同一份 actual 的重複值，故換錨回歸錨已被破壞。
**碼證**: CODE-ANCHOR: scripts/freeze_splitunify_golden.py:431
MUTATION: 暫存主檔先寫入 `{"legacy":"sentinel"}`，執行 `--write`；實跑輸出 `RC 0`、`LEGACY_PRESENT False`，證明既有內容可靜默消失。
**來源摘要**: scripts/freeze_splitunify_golden.py#d0944eb21d7c, docs/SPLITUNIFY_SPEC.D-002.md#3488868bdc68, tests/golden/splitunify/splitunify_golden.v8.json#f270e007ca98
修法：先恢復主檔 11 個 v8 舊值，再以只新增 `g1_membership_v9`／`g3b_oracle_v9` 的寫入形狀；寫入前逐值比較既有 11 鍵，任一變動即拒寫。新增暫存主檔 sentinel 與 altered-old-key 兩個紅測試。

## CODEX-R27-P1-02

**斷言**: v8 檔與 `.v8.sha256` 的完整性檢查只在 `if args.write` 內，且只比較檔案與可同時被改寫的旁檔；正常比對模式不驗 v8。同步改寫 v8 與旁檔可繞過不可變基準，外部 `V8_BASELINE_SHA256=` 錨點也不存在。
**碼證**: CODE-ANCHOR: scripts/freeze_splitunify_golden.py:423
MUTATION: 暫存 v8 寫入 `tampered-baseline`、旁檔寫入其新 sha256，保留正常主檔後執行 normal mode；實跑 `NORMAL_MODE_RC 0`、`MATCHING_SIDECAR_ACCEPTED True`。
**來源摘要**: scripts/freeze_splitunify_golden.py#d0944eb21d7c, docs/SPLITUNIFY_SPEC.D-002.md#3488868bdc68, docs/SPLITUNIFY_TODO.md#7a18de5a95ff
修法：每次 `main()` 先讀取外部固定 digest，拒絕缺檔、旁檔不符、外部 digest 不符；v8 建立使用 `O_EXCL` 且存在後一律拒寫。外部錨寫入需由委員會依 SPEC v21 規則核准，本輪未改 SPEC。

## CODEX-R27-P1-03

**斷言**: `_event_keys()` 沒有字面 `expected_side` 欄，`main()` 也沒有投影側／oracle 側／fixture 期望側三方相等斷言；目前只剩兩方 `g1_membership == g3b_oracle`。因此投影與 oracle 被同一錯誤改動時仍可通過，正是 G-4e 要排除的相關錯誤。
**碼證**: CODE-ANCHOR: scripts/freeze_splitunify_golden.py:93
MUTATION: 實跑 `rg -n 'expected_side' scripts/freeze_splitunify_golden.py tests/golden/splitunify tests/momentum/Analysis/test_splitunify_golden.py` 無命中；再將 `_build_actual()` 的 `g1_membership` 與 `g3b_oracle` 同時置為 `{'train':['WRONG'],'test':[],'purged':[]}`，實跑 `SAME_WRONG_PROJECTION_ORACLE_PASSES_G3B True`。
**來源摘要**: scripts/freeze_splitunify_golden.py#d0944eb21d7c, docs/SPLITUNIFY_SPEC.D-002.md#3488868bdc68, docs/SPLITUNIFY_TODO.md#7a18de5a95ff
修法：由 `_event_keys()` 每筆人手填入 `expected_side`，不 import 或呼叫投影、oracle 或共用 helper；`main()` 對三份逐 event 比對，另保留 G-3b 抓不對稱錯誤。三份人手同錯的誠實邊界仍須留在報告。

## CODEX-R27-P1-04

**斷言**: `EventSamplePipeline.run` 的步驟 0 以單一 `train_plan.symbol` 廣播 symbols，沒有 Mapping adapter 或 full-symbols 參數。若把已由 `derive_event_split_from_plans` 宣告支援的多標的 Mapping 傳入 run，validator 收到的是兩個 dict，且 symbols 會是空字串；這不是合法的多標的座標對驗。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:784
MUTATION: Mapping step-0 probe 以兩個 symbol 的 dict plans/index 呼叫 `EventSamplePipeline.run`；實跑 `MAPPING_VALIDATOR_CALLS [('dict', 'dict')]`、`MAPPING_STEP0_EXCEPTION AttributeError`、訊息 `'dict' object has no attribute 'row_index'`。
**來源摘要**: momentum/Analysis/event_samples/pipeline.py#320afcac9557, momentum/Analysis/event_samples/split_projection.py#5e72d9070c7e, docs/SPLITUNIFY_SPEC.D-002.md#3488868bdc68
修法：在具名入口增加多標的 adapter，對每個 symbol 以同一座標系的 full `ts`／`symbols`／global plan 呼叫 validator，再將局部 `row_index_local` 交給投影；若本入口暫不支援 Mapping，至少先以具名的 fail-closed 錯誤拒絕，而不是把 Mapping 餵給單標的 validator。補非連續 global positions 的四案真值測試。

## CODEX-R27-P2-05

**斷言**: 答案窗 purge 使用同一 event 的 `label_end_ms.max()`，但沒有先驗證事件級欄位一致。若同事件兩 feature TF 的 `label_end_ms` 不同，函式會接受輸入並按較大值整事件 purge，靜默吞掉上游事件級欄位不一致。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:734
MUTATION: `_anchor_case()` 後只改一個事件的 `event_keys.label_end_ms` 為 test 起點，執行 derive；實跑 `LABEL_END_MISMATCH_ACCEPTED True`、`PURGED_IDS ['e_train']`、`ASSIGNMENT_IDS []`。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#5e72d9070c7e, docs/SPLITUNIFY_SPEC.D-002.md#3488868bdc68
修法：在取 max 前要求每個 event 的 `label_start_ms`／`label_end_ms` 唯一且與 manifest 事件級欄位一致；不一致即 fail-closed。等值時才可退化為該唯一值。

## CODEX-R27-P2-06

**斷言**: `manifest.table` 的 duplicate `event_id` guard 在第 563 行先 raise，導致第 687-697 行的 `decision_at_ms` 非唯一 `AlignmentViolationError` 分支不可達；含不同 decision anchor 的 duplicate manifest 實際得到裸 `ValueError`。同側分組與跨表互斥兩個 invalid state 也只能由直接 helper 反例構造，合法廣播路徑本身不會生成它們。直接 helper 測試加 derive 接線測試足以守住兩個結構性 postcondition，但不足以宣稱 anchor-specific branch 已覆蓋。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:563
MUTATION: duplicate manifest anchor probe 實際輸出 `DUPLICATE_ANCHOR_EXCEPTION ValueError`、`ANCHOR_GUARD_REACHED False`；目前的 `test_opposite_sides_raise_alignment_violation` 與跨表測試則均在 targeted pytest 通過。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#5e72d9070c7e, tests/momentum/Analysis/test_splitunify_derive.py#4991b671db79, docs/SPLITUNIFY_SPEC.D-002.md#3488868bdc68
修法：若要保留該 exception contract，將 anchor uniqueness 檢查置於 duplicate-ID guard 前並補 differing-anchor 測試；duplicate manifest 本身仍維持既有 ValueError。若只要求 fail-closed，則刪除不可達分支或把其意圖併入具名 duplicate guard，避免宣稱錯誤型別已覆蓋。

## CODEX-R27-P2-07

**斷言**: TODO `Task 2.2` 第 208-218 行仍以未刪節文字要求 `feature_cutoff_ms` 集合成員決定 `train`／`test`，且第 232-236 行仍說 index 外事件 `purged`；後面的 `Task 9.2b` 已明令 `decision_at_ms` 三段式與 index 界外 raise。Task 2.2 僅對 selected-timeframe/schema 作 superseded 標記，沒有覆蓋這段舊判側敘述，會給下一個實作者相互矛盾的 live TODO。
**碼證**: CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:208
MUTATION: 以自立詞表掃描 `decision_at_ms|feature_cutoff_ms|split_label|purged|train_last_ms|test_start_ms`，命中同一 TODO 的舊 Task 2.2 與新 Task 9.2b；按 Task 2.2 文字實作 cutoff membership 會使已通過的事件級 anchor 測試轉紅。
**來源摘要**: docs/SPLITUNIFY_TODO.md#7a18de5a95ff, docs/SPLITUNIFY_SPEC.D-002.md#3488868bdc68
修法（可直接貼入 Task 2.2 第 207-218 行）：`🔴 SUPERSEDED BY Task 9.2b（B9C）：本段舊版 cutoff membership／index-外 purged 判準不再適用。現行投影先驗 train/test 非空、row set 不重疊與界外 raise；事件側只由 manifest.table.decision_at_ms 依 decision <= train_last_ms 為 train、>= test_start_ms 為 test、介於兩者為 purged，feature_cutoff_ms 不參與 split_label。` 保留原文只可放入明確 HISTORY／追溯區。

## 必答回覆

1. **r26 sentinel**：`CLOSED`。重跑 `venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; assert "metadata" in EventPipelineResult.__annotations__'`，輸出 `AssertionError`、rc=1；再次確認 `EventPipelineResult` 沒有 metadata 層，r26 的兩層交付／9A-UI deferred 立場仍成立。`CODEX-R25-P1-01` 保持 CLOSED。

2a. **六項實作要點與四條不可做**：

   1. helper 的同側分組、跨表互斥、`AlignmentViolationError`、寫入 DataFrame 前檢查：**已落地**；14-target targeted pytest 全綠，接線與順序測試均存在。
   2. manifest decision anchor、anchor 型別／界外閘、三段式、答案窗按事件廣播、移除 cutoff 判側：**大部已落地**；第 563 行 duplicate guard 使 anchor-specific uniqueness 分支不可達，見 P2-06。
   3. 空 train raise、時間重疊 raise：**已落地**；targeted test 均通過。
   4. run 步驟 0 於 derive 前呼叫 validator，並以 naive datetime64 毫秒時鐘：**單標的已落地；多標的未落地**，見 P1-04。
   5. golden `bnd_shift`、decision oracle、v9 鍵、v8 拒寫／旁檔檢查：**部分落地**；G-4e、主檔護欄、write-once、外部錨與全模式 v8 驗證缺失，見 P1-01～03。
   6. 新增／改寫測試與 xfail 解除：**核心正例、反例、接線測試已落地；golden immutable／expected-side 測試未落地**，故不能以 721 全綠宣稱本批完整。

   四條不可做逐條：`feature_cutoff_ms` 不得決定 split_label：**遵守**；界外不得成第四分類分支：**遵守**；validator 不得藏入 derive：**遵守**；異側不得靜默取一側或改判 purged：**helper 遵守，且已有直接反例與接線測試**。

2b. 未完整落地的最小修法是：先補 P1-01～03 的 golden 三層防護，再補 P1-04 的多標的座標 adapter；anchor uniqueness 與 label 欄一致性依 P2-06／P2-05 補上，並同步補對應 mutation tests。

3a. 四條 assumed verdict：A1 fixture 遷移**成立**；合法事件級廣播後異側不能由正常輸入生成，SPEC §V 明確要求直接構造 assignments，node id 未改且 xfail 已解除。A2「三道 guard 至少一道公開入口可達」**不成立（字面上）**；同側／跨表 invalid state 由公開 derive 的合法廣播路徑結構上不可達，anchor 非唯一又先被 duplicate-ID ValueError 擋下。A3 三條舊測試屬語意遷移**成立**；它們沒有刪除，而是分別改打 post-trim 洞的 decision train、時間重疊、界內 off-grid decision，與新契約一致。A4 `label_end_ms.max()` 正確且保守**不成立**；等值時正確，異值時會靜默改成較大答案窗，探針已實際觀測。

3b. A2 的最小修法是補 anchor-specific 可達測試並在 duplicate-ID guard 前驗 anchor；若決策保留「所有 duplicate manifest 都先 ValueError」，就應刪掉不可達 `AlignmentViolationError` 宣稱而改測實際 contract。A4 在 max 前補 event-level uniqueness／manifest equality guard，不一致即 fail-closed。

4a. 改寫測試不是全部空殼：直接 helper 反例原本會在刪 production call 時照綠，但新增 wiring spy 已補上該 seam；然而 P1-01～03 顯示 golden 的 v8 immutable、主檔保留、第三份 expected-side 判準目前根本沒有對應測試。兩處以上實際 mutation 結果如下。

4b. `M-SU-D2-14` mutation：把 `_assert_event_level_side_consistency` 改為 `lambda assignments, purged: None`，並讓測試模組綁到該 mutant；執行 `test_opposite_sides_raise_alignment_violation` → `RED (Failed)`。還原後同 node 在 targeted pytest → `PASSED`。第二個 mutation：包住 `_derive_single_symbol`，在返回後把 `result.assignments.loc[:, 'split_label'] = 'test'`；執行 `test_event_level_anchor_broadcasts_side_to_all_feature_tf` → `RED (AssertionError)`，還原後 → `PASSED`。另兩個實際 golden mutation 是主檔 sentinel `--write` → `RC 0 / LEGACY_PRESENT False`，以及同步改 v8／旁檔 → normal mode `RC 0 / MATCHING_SIDECAR_ACCEPTED True`。

5a. 固定掃描命令：`rg -n -i 'decision_at_ms|decision[- ]anchor|feature_cutoff_ms|split_label|train_last_ms|test_start_ms|隔離帶|expected_side|V8_BASELINE_SHA256|write[- ]once|O_EXCL|多標的|Mapping|row_index_local|local.*global' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md`，輸出 91 行。自立詞表包含：`decision_at_ms`、`decision-anchor`、`feature_cutoff_ms`、`split_label`、`train_last_ms`、`test_start_ms`、`隔離帶`、`expected_side`、`V8_BASELINE_SHA256`、`write-once`、`O_EXCL`、`多標的`、`Mapping`、`row_index_local`、`local→global`。

   - SPEC §D-002-C3、§G、§P Task 9.2b、§V `:256-273` 的 live normative contract 一致要求 decision anchor、三段式、界外 raise、expected_side、外部 v8 anchor；未發現 semantic 上互相放寬 cutoff 判側的 live 條款。SPEC §P `:216` 的「現況碼證：decision 命中 0」是已被 a1e 修正後的 stale factual sentence，但本輪明禁重開 SPEC v21，列為 doc-literal-only，不改。
   - TODO Task 9.2b `:592-625` 與 §V `:258-273` 對事件級 anchor 及 validator 前置一致；TODO Task 9.5 `:786-810` 明確列 expected_side、write-once、外部錨與主檔 11 鍵護欄，這些是本輪程式碼未完成之契約，非互斥描述。Task 9.3～9.5 設計本輪不重開。
   - TODO Task 2.2 `:208-218`、`:232-236` 是 live 未刪節的舊 cutoff／index-outside-purged 描述，與 Task 9.2b `:601-616` 互斥；此為 P2-07。其余舊 schema 段落已有 `SUPERSEDED` 標示，未另立 finding。

5b. 只有 TODO Task 2.2 需要語意修正，已在 P2-07 提供可直接貼入的 superseded 字面；SPEC stale factual sentence 不在本輪可改範圍。

6a. **不能進 Task 9.3**；最小 blocking closed set 是 P1-01、P1-02、P1-03、P1-04。P2-05、P2-06、P2-07 應在 B9C closure 一併處理，否則 consumer 施工會建立在未封閉的答案窗、anchor exception 與 TODO 指示上。

6b. 本輪已檢查：六路回歸、14 條側別／接線／空 train 目標、golden normal mode、v8／主檔 destructive probes、四條 assumptions、Mapping step-0、label_end mismatch、SPEC/TODO 自立詞表逐段掃描。由於四個 P1 仍開，沒有進入 Task 9.3 的條件。

ASSUMPTIONS_VERIFIED: r26 metadata sentinel CLOSED；A1、A3 成立；A2、A4 不成立；single-symbol 721 regression 與 14-target checks 實跑通過。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/Analysis/test_splitunify_contract.py tests/api/test_splitunify_disclosure.py tests/api/test_splitunify_event_study_only.py` → 721 passed in 70.51s；targeted derive → 14 passed；`venv/bin/python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`；mutation／Mapping／label mismatch／v8 probes output described above。
FAILURES_SEEN: 預期的兩個測試 mutation 均 RED；ad-hoc label probe 初次錯用 fixture 參數、位置參數及 frozen manifest，已改用正確 fixture／新 EventManifest 後取得上述證據；無產品測試失敗。
SCOPE_CHANGES: none；只新增 `handoffs/20260911-splitunify-b9-review-r27-codex.md`，未改碼、SPEC、TODO、`HANDOFF.md` 或 `data_cache/`。
NUMERIC_OR_SCHEMA_IMPACT: 審查發現 golden schema／immutable baseline 與多標的 validator 座標契約缺口；本輪未修改任何數值、schema 或輸出檔。
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r27-codex.md
VERDICT: blocked
BLOCKED-BY: CODEX-R27-P1-01,CODEX-R27-P1-02,CODEX-R27-P1-03,CODEX-R27-P1-04
CLOSED: CODEX-R25-P1-01
STATUS: DONE

## COMPOSER-R27-P2-01

**斷言**: SPEC §P `Task 9.2b` `:216-217` 與 §V `:261` 仍以「9.2b 前」碼態為**現況**，與 commit `a1e9680e` 已落地之事件級錨定互斥，可能誤導後續讀者。

**碼證**: `rg -n 'decision_at_ms' momentum/Analysis/event_samples/split_projection.py | wc -l` → **28**（非 0）；`split_projection.py:720-725` `_side_of` 僅讀 `decision_ms`；SPEC 掃描命令見必答 5a → `:216`、`:261` 命中。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#755f3d53c1f3

doc-literal-only；信心度=High。行為已由碼與測試鎖定，戳記 v21 仍有效；**建議下一 doc 同步輪**更新上述兩處字面（修法見必答 5b），不阻擋 B9D impl。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R26-P3-00

ASSUMPTIONS_VERIFIED: body/stamps rc=0；129 pytest + GOLDEN OK；四 assumed 逐條核對；破壞驗 3 處；SPEC/TODO 詞表掃描
TESTS_RUN: `pytest tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py tests/momentum/Analysis/test_splitunify_golden.py -q` → 129 passed；`scripts/freeze_splitunify_golden.py` → GOLDEN OK；破壞驗 3 組（見 4b）
FAILURES_SEEN: none（破壞驗預期紅，已還原）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r27-composer.md

STATUS: DONE

## GROK-R27-P1-01

**斷言**: `docs/SPLITUNIFY_TODO.md` `Task 2.2` 實作要點仍以 live 祈使句要求「`feature_cutoff_ms ∈ feature_index[…]` 集合成員判定定側／不在集合⇒purged」，且該段**未**標 SUPERSEDED；與已落地之 `Task 9.2b` 事件級錨定互斥，後續 agent 依 Task 2.2 會回退判側。

**碼證**: `awk 'NR>=208 && NR<=236' docs/SPLITUNIFY_TODO.md | grep -E '集合成員|feature_cutoff_ms ∈|SUPERSEDED'` → `:209`／`:217`／`:236` 無 SUPERSEDED；僅 `:225`（selected_timeframe）有。本輪 mut2 依該舊文改回 per-cutoff → `test_event_level_anchor_broadcasts_side_to_all_feature_tf` 轉紅。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:217
MUTATION: 依 Task 2.2:217 把廣播迴圈改回 `_side_of(int(rec["feature_cutoff_ms"]))`（本輪 mut2）→ `test_event_level_anchor_broadcasts_side_to_all_feature_tf` 轉紅（AlignmentViolationError 異側）

**來源摘要**: docs/SPLITUNIFY_TODO.md#7a18de5a95ff; momentum/Analysis/event_samples/split_projection.py#5e72d9070c7e

[BLOCKING] 信心度=High。同型 R21 `CODEX-R21-P1-02`（契約改後舊 Task 段未標 superseded）。**修法**：在 Task 2.2 要點 1／2／4（`:209`／`:217-218`／`:235-236`）旁加 SUPERSEDED→`Task 9.2b` 註（字面見必答 5b）；刪節線保留舊集合成員句。可行性：與 `:225`／`:242` 既有 SUPERSEDED 形態相同，不改碼。

---

## GROK-R27-P1-02

**斷言**: `SU-RESID-2`（TODO §E `:891` 與 SPEC §N `:327`）仍把「側別錨定（`Task 9.2b`）」列為**尚未關閉**且 `blocked-by:Task 9.2b／9.3 尚未實作`；B9C 落地後該半句為假，會誤阻 B9D 或讓狀態帳與碼不一致。

**碼證**: `grep -n '尚未關閉者\|blocked-by:Task 9.2b' docs/SPLITUNIFY_TODO.md docs/SPLITUNIFY_SPEC.D-002.md` → TODO:891 與 SPEC:327 皆仍列 9.2b；`grep -c decision_at_ms momentum/Analysis/event_samples/split_projection.py` → 12（非 0）。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:891
MUTATION: 保持 `blocked-by:Task 9.2b／9.3 尚未實作` 字面不變 → 開工檢核若 grep「9.2b 尚未」仍命中，即使 129 測全綠且 `decision_at_ms` 已落地

**來源摘要**: docs/SPLITUNIFY_TODO.md#7a18de5a95ff; docs/SPLITUNIFY_SPEC.D-002.md#3488868bdc68

[BLOCKING] 信心度=High。同型 R22「部分關閉」帳面未隨批次前進。**修法**：兩檔同步——尚未關閉者只留 `Task 9.3`；blocked-by 改 `Task 9.3 尚未實作`；9.2b 半句刪節保留（字面見必答 5b）。可行性：只改殘留列狀態句，不動 C5 register／mutation 條數。

---

## GROK-R27-P2-01

**斷言**: SPEC §P `Task 9.2b`「現況碼證」（`:216-217`）、§V `:261`「現行碼會給出…」、§G (G-4c) `:167`「oracle **目前**也以 cutoff 判側」，以及 `_derive_single_symbol` docstring `:462-464`，仍以 9.2b **前**碼態為現況／現行，與 commit `a1e9680e` 互斥。

**碼證**: `grep -c decision_at_ms momentum/Analysis/event_samples/split_projection.py` → 12（非 0）；`:720-725` `_side_of` 只讀 `decision_ms`；`freeze_splitunify_golden.py:176-187` oracle 已 decision-anchor；docstring `:462-464` 仍寫 `feature_cutoff_ms ∈ …` 定側。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#3488868bdc68; momentum/Analysis/event_samples/split_projection.py#5e72d9070c7e

doc-literal-only；信心度=High。行為已由測鎖定。**修法**：①`:216-217` 改標「9.2b 前快照／已過期」＋現行錨點／三段式／廣播碼證；②`:261` 改「9.2b 落地後正例；9.2b 前才會 1h=test／4h=purged」；③`:167`「目前」改「9.2b 前」；④docstring 兩段式改寫為事件級三段式＋廣播（或標 SUPERSEDED）。不單獨阻擋 B9D（併 P1 同批最省）。

---

VERDICT: blocked
BLOCKED-BY: GROK-R27-P1-01,GROK-R27-P1-02
CLOSED: GROK-R26-P3-00

ASSUMPTIONS_VERIFIED: body 755f3d53…；stamps rc=0；129 pytest；GOLDEN OK；四 assumed 逐條；mut1/2/3；詞表掃描含 Task 2.2／SU-RESID-2
TESTS_RUN: `pytest tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/event_samples/test_splitunify_wiring.py -q` → 129 passed；`scripts/freeze_splitunify_golden.py` → GOLDEN OK；mut1 wiring 紅／mut2 錨定紅／mut3 空 train 紅（皆還原）
FAILURES_SEEN: 並行 worktree 曾見 `test_membership_set_not_interval` 被改成 `assert not purged.empty`（非本家）；已 `git checkout --` 還原後 3 passed
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r27-grok.md

STATUS: DONE
