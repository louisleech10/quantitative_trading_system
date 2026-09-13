# SPLITUNIFY b9 review-r27 — codex

審查範圍：`git show a1e9680e` 指定之 Task 9.2b 程式碼、測試與 golden；未修改程式碼、SPEC、TODO 或 `HANDOFF.md`。

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
