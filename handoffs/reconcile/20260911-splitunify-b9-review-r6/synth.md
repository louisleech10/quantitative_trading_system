# Reconcile — 20260911-splitunify-b9-review-r6

**來源** 20260911-splitunify-b9-review-r6-codex.md, 20260911-splitunify-b9-review-r6-composer.md, 20260911-splitunify-b9-review-r6-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **I1 我上一輪的不等式判準在隔離帶上與集合成員不等價（三家獨立撞題）**——「`decision_at_ms<test_start_ms`不等價」「`Task9.2b`同時要求「`deci」「Task9.2b宣稱以不等式（`deci」 | P1 | CODEX-R6-P1-01, COMPOSER-R6-P1-01, GROK-R6-P1-01 | 採納（`Task 9.2b` 把 gap 處置**寫死為 fail-closed**：`decision_at_ms` 映射之位置落在半開區間 `[split_point, split_point+purge_gap+embargo)` 即 raise 且含 event_id，**不得**收成 train 亦不得靜默 purge；主委已複驗 `split_preview.holdout_test_row_index:41-43` 之 `start = split_point + purge_gap + embargo`，gap 範圍可精確定義） |
| **I2 (3.2) 檢查抓不到「一列 purged、一列 assignments」（三家獨立撞題）**——「C3.2「複合鍵guard後、寫assi」「`(3.2)`之`AlignmentViol」「Task9.2b將`(3.2)`檢查定在」 | P1 | CODEX-R6-P1-02, COMPOSER-R6-P1-02, GROK-R6-P1-02 | 採納（`Task 9.2b` 增跨表 fail-closed：`set(purged["event_id"]) ∩ set(assignments["event_id"]) == ∅`；主委已複驗 `purged` 僅 `["event_id","reason"]` 兩欄、**無** `split_label`，故只驗 `split_label` 唯一結構上抓不到；答案窗 purge 須按事件側一次決定並廣播） |
| **I3 物化層與其下游 consumer 契約（codex＋grok）**——「第五層`feature_materializat」「Task9.3要求`feature_mat」 | P1 | CODEX-R6-P1-03, GROK-R6-P1-03 | 採納（`Task 9.3` 對 `feature_materialization` 之改法**整段改寫為維持事件級橫向合併**；主委自產碼證：`_combined_columns:22-32` 逐字「多 TF 特徵欄名合併；衝突 ⇒ loud 拒」＝各 TF 欄名互斥是**設計**，`:138-140` 之 `n_input = per_tf["event_id"].nunique()` 記帳不變式照原施工單改會直接 AssertionError，`baseline`／`pattern_bridge` 亦以事件級 Index 交集） |
| **I4 Task 9.3 形狀規則與「事件級表不變」自相矛盾**——「Task9.3同時要求`tables`等s」 | P1 | CODEX-R6-P1-04 | 採納（`D-002-C5` 之 16 處清單**逐處重新分類為三類**：事件級維持／複合鍵改／事件級但需去重取唯一值；主委已自行讀完全部 16 處並取得碼證，結論為九處誤列、一處派工過度、一處真缺陷但原改法錯、三處確需改） |
| **I5 Task 9.1 二擇一規格自己沒擇（三家獨立撞題）**——「Task9.1的二擇一仍未選定，故dis」「`Task 9.1`L143二擇一（改un」「Task9.1雖要求先「二者擇一」解決生」 | P1 | CODEX-R6-P1-05, COMPOSER-R6-P2-01, GROK-R6-P1-05 | 採納（主委**擇 (b)** 並定案：碼證 `case_import_service.py:1592-1609` 逐字「事件掃描端恆走 event-study-only」且註明為 SPEC C-0 決議③／R2 之 D1 既有裁定、殘留已具名給 `R-5` ⇒ 選 (a) 會推翻本票自己的裁定。`Task 9.1` 原指名之 route／service／前端行號**整組作廢**，改掛真正走投影之 IC 主線並補 route 級契約測試） |
| **I6 前端 Map 改複合鍵會讓匯出附帶欄位靜默變空（codex 獨得）**——「Task9.5要求搜尋頁`byEventI」 | P1 | CODEX-R6-P1-06 | 採納（`Task 9.5` 將該 event-level 匯出 Map **排除**於複合鍵遷移之外；碼證 `eventExport.ts:516-535` 之 record 僅 `event_id`／`symbol`／`timeframe`／`t0`，無 `feature_timeframe`，改鍵即全數 miss，且違反 `D-002-C0` (0.6)「既有 wire 欄位原樣保留」） |
| **I7 事件數下限與 per_symbol_n 被 TF 維度膨脹（grok＋composer）**——「複合鍵後若仍用`assignments`」「`_derive_single_symbol`之`per」 | P1 | GROK-R6-P1-04, COMPOSER-R6-P2-02 | 採納（`Task 9.4` 增指名 `split_projection.py:562`／`:569`／`:716-719` 與 `per_symbol_n`，改以 `event_id` 去重計數、列數另立新名；🔴 主委追加：`insufficient_events_in_test` **不擋任何分析**且**前端完全未顯示**，故須與終端揭露一起處理，否則修了也沒人看得到） |
| **I8 M-SU-D2-23 把兩個獨立缺陷用 OR 合併**——「M-SU-D2-23把「保留`valida」 | P2 | CODEX-R6-P2-07 | 採納（拆為兩條獨立 mutation：保留 `validate="1:1"`／未寫 `feature_timeframe`，各配自己的應紅測試，條數與 ID 連續性同步更新並由主委自數） |

**Verdict**: 需修補後合併

**本輪主委自評**

1. **我上一輪的修法自己引入新缺陷**（I1）：為修「跨 TF 網格不一致」而把判準改成不等式，卻沒驗它會不會破壞原本成立的性質——舊的集合成員判定除了判邊，還**順帶承擔「隔離帶事件要丟掉」**，我換掉它時把那個職責一起丟了。三家獨立撞題。
2. **16 處消費面清單是用形狀判準列的**（I3／I4）：我以「有無 `set_index("event_id")`」為判準，未逐處問「這張表的一列代表什麼」——而 `Task 9.3` 正文是我自己寫的「不得用形狀規則」。本輪我已自行讀完全部 16 處並取得碼證。
3. **`Task 9.1` 我指名了行號卻沒查可達性**（I5）：那條 route 在本票設計上永遠不會有 `discarded`。**指名落點 ≠ 該落點走得到**。
4. 三輪連續：R4 四參數閘、R5 producer merge、R6 gap 與物化契約——**沒有任何一輪以「無 finding」停輪**。

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R6-P1-01
**斷言**: `decision_at_ms < test_start_ms` 不等價於含 purge/embargo 間隙的 train/test 集合成員；Task 9.2b 雖說界外 fail-closed，卻未定義 gap 的明確錯誤/守恆處置，照單一不等式實作會把 gap 事件判 train。 **碼證**: SPEC:169-175；TODO:30-43 的 purge/embargo 邊界；上述 probe 已重現 inequality=train、membership=purged。RECHECK: 用相同 6 點 index、train `[0,1]`、test `[4,5]` 重跑 gap probe，必觀察兩判準不同。 **來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;docs/SPLITUNIFY_TODO.md#e44da6448b01;momentum/Analysis/event_samples/split_projection.py#99bfddace904。 [MAJOR] 信心度=High；不修會把 embargo gap 納入 train，或各 agent 對「fail-closed」分別實作成 purge、raise、或接受。修法：先驗 `decision_at_ms` 落在 train/test 的明確可接受區間，gap 明確 raise（含事件 ID）並加正反例；不以 `test_start` 單獨決定側別。
## CODEX-R6-P1-02
**斷言**: C3.2「複合鍵 guard 後、寫 assignments 前」的檢查若只看 assignments 內 `split_label`，會放過同一事件分散在 assignments 與 purged 的異狀態。 **碼證**: SPEC:169-175、198-202 只要求 assignments 分組與 purged 複合鍵唯一；現行 `split_projection.py:539-553` 的逐列分支，加上實跑同一 `event_id=e` 同時出現在 assignment/test 與 purge 的 stdout。RECHECK: 以 `test_start=40`、train cutoff=10 且 label_end=40、test cutoff=40 的兩列重跑 probe；輸出應被單一事件狀態閘拒絕。 **來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/split_projection.py#99bfddace904。 [MAJOR] 信心度=High；不修會違反 C3.3 的全 TF 同側/同一處置，且 summary 的 event/row 守恆可看似正確而掩蓋資料分裂。修法：在寫入兩容器前對所有 pending `(event_id, feature_timeframe)` 計算唯一事件狀態；明確要求 assignment 與 purge event sets 互斥，答案窗跨界時廣播 purge。
## CODEX-R6-P1-03
**斷言**: 第五層 `feature_materialization` 仍不能按 Task 9.3 直接改成全量多 TF：同名特徵先被 `_combined_columns` loud 拒絕，若只改 groupby 成 MultiIndex，baseline/pattern_bridge 仍以 event_id Index 交集/`.loc[ids]`，會空集合或索引不匹配。 **碼證**: `feature_materialization.py:88,93-140`；`baseline.py:105-120`；`pattern_bridge.py:122-141`；probe 對 `{'1h':['f'],'4h':['f']}` stdout=`ValueError: 多 TF 特徵欄名衝突`。RECHECK: 重跑 `_combined_columns` probe，並用一事件兩 feature-TF fixture 執行 baseline/pattern bridge。 **來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2;momentum/Analysis/event_samples/baseline.py#38c7ec473653;momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2。 [MAJOR] 信心度=High；不修會在全量物化時先 Merge/欄名失敗，或改完輸出後 baseline `n_test`/pattern train-test 變空而靜默失效。修法：明定 `(event_id,feature_timeframe)` 特徵/label contract、重疊欄位的 namespace/拒絕策略、各 consumer 的 adapter 與一事件兩列 value/count 測試。
## CODEX-R6-P1-04
**斷言**: Task 9.3 同時要求 `tables` 等 scalar lookup 改複合鍵，又要求 event-level 表/cluster 粒度不變，與現有 tables 的 event-level receipt/cluster lookup 互斥，且 pattern_bridge 的 features/assignments 仍是 event_id 粒度。 **碼證**: SPEC:159-184；`tables.py:214,229,234,257,326,372-373` 對 `receipts.event_level`/`clusters` 以 event_id `.loc`；`pattern_bridge.py:122-141` 以 event_id 交集。RECHECK: 對照 SPEC 的「tables composite」與「event-level 表不變」，再以同 event 多 TF fixture 執行 tables/bridge，要求值不可空且 cluster 不複製。 **來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/tables.py#843ba7f68172;momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2;momentum/Analysis/event_samples/ic_feed.py#741f697b3964。 [MAJOR] 信心度=High；照 composite 形狀規則會讓 `.loc[eid]` 找不到 event-level receipt/cluster，照現狀則 9.3 的 scalar consumer 要求無法驗收，並可能改壞 D-001/C6 的事件級計數/簇權重。修法：逐函式列出真正 per-TF keyed input 與 event-level input；只對前者用 composite，receipts.event_level、manifest、clusters 保持 event_id。
## CODEX-R6-P1-05
**斷言**: Task 9.1 的二擇一仍未選定，故 discarded 的 producer→summary→API→前端資料流沒有可執行生產路徑。 **碼證**: SPEC:133-145 明列必先選 (a)/(b) 但未具名方案；`case_import_service.py:1592-1609` 永遠 `run_event_study_only`，`EventAnalyzeRequest:295-303` 無 universe/run id；response `summary` 為寬 Dict（models:306-318），面板 `EventTablesPanel.tsx:347-379` 在 unavailable 只顯示 capability，不顯示 discarded。RECHECK: 以 route/service call trace 確認無 `build_event_keys`/universe/discarded producer。 **來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;api/services/case_import_service.py#d2571793953f;api/models/event_import_models.py#82c83da611f5;frontend/src/components/ic-analysis/EventTablesPanel.tsx#393f5cf7bd9a。 [MAJOR] 信心度=High；不修會出現 API 契約測試無法觸發 discarded、或 agent 任選錯誤 producer 的假綠。修法：在 Task 9.1 明選 (a) 並定義 universe source/lifecycle/request 欄位，或選 (b) 指定實際投影 consumer、回應形狀與 UI 位置，兩者均附 route-level contract test。
## CODEX-R6-P1-06
**斷言**: Task 9.5 要求搜尋頁 `byEventId` Map 改複合鍵會與既有事件匯出 payload 脫節，導致所有 extras 對不到而在 CSV 靜默消失。 **碼證**: SPEC:191-205 要求 Map composite；`search/page.tsx:825-835` Map key 由 `canonicalEventId(symbol,timeframe,t0)` 建立、lookup 只用 `rec.event_id`；`eventExport.ts:516-535` record 只有 event_id/symbol/timeframe/t0，無 `feature_timeframe`；`eventId.ts:11-30` canonical template 為 `{symbol}:{timeframe}:{t0}`。RECHECK: 以一筆 payload record 與同 event source row 走 export，改 composite key 後確認 `byEventId.get(String(rec.event_id))` miss。 **來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;frontend/src/app/search/page.tsx#744a997b6c9d;frontend/src/lib/eventExport.ts#90528a561479;frontend/src/lib/eventId.ts#c3f19e5d1b1d。 [MAJOR] 信心度=High；這會直接造成使用者匯出的附帶欄位全部變空/漏欄，違反 C0「既有 wire event_id 不變」。修法：將此 event-level export Map 排除出 composite migration，或明確把 feature-TF 帶進 payload/source 並以完整 composite key 對齊；補同鍵多 TF 與 extras value test。
## CODEX-R6-P2-07
**斷言**: M-SU-D2-23 把「保留 `validate=1:1`」與「不寫 `feature_timeframe`」兩個獨立缺陷用 OR 合併成一個 mutation，違反 §V 逐處對應，造成 mutation 數字雖為 25 但 coverage/歸因不精確。 **碼證**: SPEC:206-234；`rg -o 'M-SU-D2-[0-9]{2}' docs/SPLITUNIFY_SPEC.D-002.md | sort -u | wc -l` stdout=`25`，其中 23 行明列 OR。RECHECK: 將兩個變異分別注入，確認各自由不同 assertion kill，再拆成獨立 ID。 **來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a。 [MINOR] 信心度=High；不修不一定阻擋功能，但會讓回歸報告無法指出究竟哪個 producer defect 被覆蓋。修法：一 mutation 一 defect/一應紅測試，更新連續 ID、條數與 Task 9.2 交叉引用。
必查類別：矛盾/端到端/不可測驗收＝P1-01～06；quant/OOM/cache＝本輪無新增；API/型別＝P1-05/06；測試品質/Agent 可執行性＝P1-01～06、P2-07；必要性/短命工＝無新增；§RISK/§A/§G/§N 的未驗證假設已在上述必答與 findings 標明。
ASSUMPTIONS_VERIFIED: fact-verified 為 R5 八群全採納（synth:14-21）、SPEC 第六修訂落點、現行 run→projection→materialization→consumer/API 路徑；assumed→refuted 為 gap 等價與 assignment/purge 單事件狀態；H1-H7 文字落點已逐項對讀。
TESTS_RUN: `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` rc=0（A/C 各 2 列但只 1h，B/D raise）；gap probe rc=0（train vs purged）；purge interaction probe rc=0（assignment+purge 同 eid）；duplicate TF probe rc=0（ValueError）；mutation count rc=0（25）；`venv/bin/python -m pytest -q tests/momentum/event_samples/test_splitunify_wiring.py --tb=short` rc=0（9 passed）。
FAILURES_SEEN: 初次 `rg` pattern 以 `--single` 開頭而被當旗標（命令 rc=2），且一次 `git diff --check` 混入 `/tmp` 而回報 outside repository；改用 `rg -n --`、awk 檔案檢查後完成，未改程式。
SCOPE_CHANGES: none；僅新增 `handoffs/20260911-splitunify-b9-review-r6-codex.md`，未改碼、SPEC、TODO、HANDOFF 或 data_cache；/tmp 本輪無可刪除項，保留 claude-501（若存在）。
NUMERIC_OR_SCHEMA_IMPACT: 未改執行輸出；本審查指出預計 schema/grain 風險：`(event_id,feature_timeframe)`、baseline `n_test` 與 event count 必須分名，未自行變更。
VERDICT: blocked
BLOCKED-BY: CODEX-R6-P1-01,CODEX-R6-P1-02,CODEX-R6-P1-03,CODEX-R6-P1-04,CODEX-R6-P1-05,CODEX-R6-P1-06
CLOSED:
STATUS: DONE
## COMPOSER-R6-P1-01

**斷言**: `Task 9.2b` 同時要求「`decision_at_ms < test_start_ms` ⇒ train」不等式與「`decision_at_ms` 落 plan 時間界外 ⇒ fail-closed」，但未定義兩者先後；在 train/test 間 embargo 間隙，不等式給 **train**、集合成員語意給 **purged**，實作可靜默選錯側。

**碼證**: 反例構造見必答 3（`train_ms={1000,2000,3000}`、`test_start_ms=6000`、`decision_at_ms=4500`）。現行集合成員路徑 `split_projection.py:532-553`；規格 `Task 9.2b` L173 兩句並列無優先。RECHECK: 讀 L173＋對照 `:532-553` 行為。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。Agent 實作 9.2b 時若只寫不等式，embargo 區事件會進 train assignments 而 canonical plan 根本不承認該時刻 ⇒ 與 IC 邊界不一致、§V `Task 9.2b` 反例可假綠。**修法**：`Task 9.2b` 增**有序**判準——(1) 先用 `train_plan.time_bounds`／`test_plan.time_bounds`（或 `row_index_local` 首尾）驗 `decision_at_ms` 落在 train 或 test 覆蓋區，否則 fail-closed；(2) 僅在 (1) 通過後才用不等式／集合成員定側；§V 增成對 ASSERT（間隙 `decision_at` 須 raise 或整事件 purged，不得標 train）。**可行性**：僅改 `_derive_single_symbol` 判側區塊與測試，不動切分數學；`time_bounds` 同源閘已在 L511–522 存在，可复用同一 `feature_index` 切片。

## COMPOSER-R6-P1-02

**斷言**: `(3.2)` 之 `AlignmentViolationError` 若只檢查即將寫入 `assignments` 的 `split_label` 唯一，**漏掉**「同一 `event_id` 同時出現在 `purge_rows` 與 `assign_rows`」——現行逐列答案窗 purge 即可觸發，且 (3.2) 不會 raise。

**碼證**: `split_projection.py:540-553`：1h 列 `in_train`＋答案窗 ⇒ `purge_rows`；4h 列 `in_test` ⇒ `assign_rows` test；無後續「同 event 跨表」檢查。`Task 9.2b` L174 僅寫 `split_label` 唯一。RECHECK: 構造 `label_end_ms≥test_start_ms` 且兩 TF cutoff 分屬 train/test 集合之 `event_keys` 兩列，單步執行 L530–553 迴圈。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。部分實作（先上 C3.2、未改事件側 purge）會留下非法 OOS 前兆而測試綠。**修法**：`Task 9.2b` L174 增——同 `event_id` **不得**同時出現在 `purge_rows` 與 `assign_rows`（或：答案窗 purge 須在判側後對該 event **所有** feature TF 列廣播後再檢查）；§V 增 ASSERT「異側或 purged∩test 混合 ⇒ raise」。**可行性**：迴圈後加 `set(purge_rows.event_id) ∩ set(assign_rows.event_id)` 檢查即可；與 `M-SU-D2-24` 互補。

## COMPOSER-R6-P2-01

**斷言**: `Task 9.1` L143 二擇一（改 universe producer **或** 移出終端揭露）仍無**具名** route／service／掛載點，兩選項皆無法寫出可執行驗收命令。

**碼證**: `case_import_service.py:1609` 仍固定 `run_event_study_only_with_params`；L143 僅抽象描述。RECHECK: `rg -n 'run_event_study_only' api/services/case_import_service.py`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;api/services/case_import_service.py#d2571793953f

[MAJOR] 信心度=High。9A 可在無生產路徑下「規格完成」而終端永不顯示 `discarded`。**修法**：擇一後寫死——例 (a) `POST …/analyze` 改調 `holdout_boundary`＋`EventSamplePipeline.run` 並指名 universe 來源欄位；或 (b) 揭露改掛 IC 投影 route 與前端面板路徑。**可行性**：與 R5 H5 同型，僅缺指名；IC 主線已有 `run()` 可複用（`pipeline.py` 已存在）。

## COMPOSER-R6-P2-02

**斷言**: `_derive_single_symbol` 之 `per_symbol_n`（L559–561）與 `insufficient_events_in_test` 門控（L716–718）用 `event_keys` **行數**，複合鍵後會膨脹；`Task 9.4` 未指派修正 `plan.summary.per_symbol_n`。

**碼證**: `split_projection.py:559-561` `value_counts()` on `event_keys`；`Task 9.4` L186–189 只列 pipeline 頂層 count 與 wiring。RECHECK: 2 event×2 TF ⇒ `per_symbol_n` 報 4 非 `n_events=2`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[MAJOR] 信心度=Medium。可能誤觸／誤過 `tier_min_test_events` 與 degraded 旗標。**修法**：`Task 9.4` 增 `per_symbol_n` 改 `nunique(event_id)` 或並列 `n_event_tf_rows`。**可行性**：單行聚合改動，與 C6 同批。

## GROK-R6-P1-01

**斷言**: Task 9.2b 宣稱以不等式（`decision_at_ms < test_start_ms`）定側可替代集合成員，但在 `purge_gap`／`embargo` 造成的 train／test **間隙**上兩者結果不同（set=PURGED、ineq=train）；且「界外 fail-closed」未定義 gap 屬界外或 train，會讓實作走出 TRAIN／raise／PURGED 三歧路並改變切分成員集。

**碼證**: VERIFY: `PYTHONPATH=. venv/bin/python /tmp/grok-splitunify-b9-review-r6/probe_ineq_vs_set.py` → `DIFF_COUNT 3`；gap rows 14–16：`set=PURGED_else ineq=train outside_both_bounds=True`。現行碼 `split_projection.py:524-553` 用 `in train_ms/test_ms` else purge；`split_preview.py:312-316` train=`arange(0,split)`、test=`arange(split+purge+embargo,n)`。SPEC L173 不等式＋界外並寫、無 gap 定義。RECHECK: 重跑該探針＋對讀 L173 與 `holdout_boundary`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/core/split_preview.py#95a85ec0de54;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。不改則 Task 9.2b 實作時：(a) 純不等式把現行 gap purge 收成 train（答案窗未跨界時尤甚）；(b) 把界外解成 outside both bounds 則 gap raise，與「等價改寫」假說三方不一致；golden／IC 樣本集漂移且無單一驗收神諭。**修法**：在 Task 9.2b 明定 gap 處置為三者擇一並寫死——建議 **fail-closed**（與 `outside_both_bounds=True` 一致，且不把隔離帶收成 train）；配 ASSERT「`decision_at`∈(train_end, test_start) ⇒ raise」；mutation 一條「把 gap 當 train」。**可行性**：探針已標出 `outside_both_bounds`；現況 else 分支本就不當成 train；只把「界外」操作化，不改答案窗跨界公式。

## GROK-R6-P1-02

**斷言**: Task 9.2b 將 `(3.2)` 檢查定在「寫入 assignments 前、只驗 `split_label` 唯一」，會**漏掉**同事件「一列 purged、一列 test／train」；該狀態正是 `M-SU-D2-24` 要抓的缺陷，且 SPEC 未定義 (3.2) 與 `purged` 列的互動。

**碼證**: SPEC L174 逐字「按 `event_id` 分組檢查 `split_label` 唯一」；`purged` 列無 `split_label`（現碼 `:541/:553` 只寫 `event_id,reason`）。探針 `probe_tier_and_32.out`：`assign_only_异侧 {}` 且 `MISS_PURGED_ASSIGN_MIX True`。`M-SU-D2-24` L233：同事件一列 purged、另一列 test＝缺陷。RECHECK: 對讀 L174↔L233＋重跑探針。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。實作者可完成「廣播側別＋split_label 唯一檢查」卻保留逐列答案窗 purge ⇒ C3 raise 全綠、`M-SU-D2-24` 場景仍存活。**修法**：在 Task 9.2b 增——(a) 答案窗 purge **必須**按事件側一次決定，同事件所有 feature TF 列同進 `purged` 或同留 assignments；(b) (3.2) 之外另立「同 `event_id` 不得同時出現在 assignments 與 purged」之 fail-closed（或把 provisional label 含 `PURGED` 再做唯一性）。**可行性**：事件級廣播已是 L172 改法；補一條跨表存在性檢查即可，不新增值集 reason。

## GROK-R6-P1-03

**斷言**: Task 9.3 要求 `feature_materialization` 改 `groupby(["event_id","feature_timeframe"])`＋MultiIndex，但**未**改現況記帳不變式 `n_input = per_tf["event_id"].nunique()`（`:137-140`）；字面實作會使 `len(features)`＝列數而 `n_input`＝事件數 ⇒ `AssertionError`，或誘使保留 event 級 groupby 以假綠。

**碼證**: Task 9.3 L179 只寫 groupby／MultiIndex／merge validate／索引唯一；全文零「記帳／n_input／nunique」。現碼 `:137-140`。探針 `probe_mat_accounting.out`：`CURRENT_INVARIANT_BREAKS True`（2 events×2 TF → n_input=2、len_features=4）。RECHECK: `sed -n '137,140p' feature_materialization.py`＋對讀 Task 9.3。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2

[BLOCKING] 信心度=High。此為必答 2 之第五層缺口：9.2 全量 assignments 後，物化若不改基數則與複合鍵列對不齊；只改 groupby 不改記帳則 Task 9.3 無法綠或被繞。**修法**：Task 9.3 增改法——記帳改為 `len(per_tf)`（或 `(event_id,timeframe)` 唯一列數）`== len(features)+len(failures)`，failures 亦升為複合鍵粒度；§V／`M-SU-D2-04` 旁加「刪記帳改寫仍綠」之反例。**可行性**：現不變式已是顯式 AssertionError；改右／左側計數定義即可，與 MultiIndex 同批。

## GROK-R6-P1-04

**斷言**: 複合鍵後若仍用 `assignments` **列數**餵 `tier_min_test_events`（`split_projection.py:562`→`per_symbol_test_n`→`_build_summary:717-719`），一事件兩 feature TF 可使 `n_test_rows=2 ≥ tier_min=2` 而事件數僅 1，**靜默繞過**「test 段事件數下限」；Task 9.4 檔案清單未含此路徑。

**碼證**: `:562` `n_test = (assignments["split_label"]=="test").sum()`；`:569` `per_symbol_test_n={s: n_test ...}`；`:717-719` 以該值比 `tier_min_test_events`。Task 9.4 L187-189 只列 pipeline count／API／前端／wiring／baseline 例外。探針：`INFLATION_BYPASS True`。RECHECK: `sed -n '560,571p;714,719p' split_projection.py`＋對讀 Task 9.4。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。屬 quant 樣本門檻被 TF 維度膨脹（風險 d）；只改 pipeline 摘要顯示不夠——閘在投影 summary 內先算完。**修法**：Task 9.4（或 9.2a summary）具名 `split_projection.py:562`／多 symbol `:641`——`per_symbol_test_n` 改 `event_id` 去重計數；列數另鍵；配 fixture「1 event×2 TF、tier_min=2 ⇒ 仍 insufficient」。**可行性**：與 C6／9.4 事件數語意同向；單行 `.nunique()` 即可，baseline 例外不波及此閘。

## GROK-R6-P1-05

**斷言**: Task 9.1 雖要求先「二者擇一」解決生產可達性，但 SPEC **未擇定** (a) 或 (b)，兩邊皆缺可寫進 §V 的具名 producer／替代消費者與驗收命令 ⇒ 標「先解可達性」仍不足以讓 9A 可驗收。

**碼證**: L143「須**先**明定二者擇一並寫入改法：(a)…(b)…」——祈使句指向未來實作者，正文無「本延伸採用 (a)/(b)」。`case_import_service.py:1592-1626` 仍恆 `run_event_study_only`、capability 無 ok 分支。§V Task 9.1 L197 之 API／前端 ASSERT 未附「在何 route 用何 fixture 跑通 discarded」命令。RECHECK: 對讀 L143↔L197；確認無「採用 (a)」或具名替代 endpoint。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#6073261d303a;api/services/case_import_service.py

[BLOCKING] 信心度=High。(a) 缺：universe／`features_run_id` 從何注入 analyze、是否違反「事件掃描端不自切」既裁；(b) 缺：移出後掛哪個**確實走投影**的消費者、EventTablesPanel 是否仍為顯示面。兩邊任一未寫死 ⇒ Agent 無法寫出單一 pytest／契約測試命令。**修法**：主委在 Task 9.1 **擇一**寫死；若 (a)——具名參數來源與「仍不得自算邊界」；若 (b)——具名替代 API／面板與 9A 顯示遷徙；§V 補一條可複製命令。**可行性**：service 註解已承認日後 `features_run_id` 殘留 R-5——擇 (a) 有既有敘事錨；擇 (b) 則把 discarded 掛 IC／投影 disclosure 路徑，避開 event-study-only。

---

