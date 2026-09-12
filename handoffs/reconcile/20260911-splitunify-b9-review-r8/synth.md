# Reconcile — 20260911-splitunify-b9-review-r8

**來源** 20260911-splitunify-b9-review-r8-codex.md, 20260911-splitunify-b9-review-r8-composer.md, 20260911-splitunify-b9-review-r8-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **K1 §G (G-4a) 不可機械歸因（三家獨立撞題）**——「G-4a的「重凍後只准因換錨改側」目前不」「§G(G-4a)要求單TFgolden於」「§G(G-4a)允許Task9.2b落地」 | P1 | CODEX-R8-P1-01, COMPOSER-R8-P1-01, GROK-R8-P1-01 | 採納（🔴 主委查得**現成骨架**：`scripts/freeze_splitunify_golden.py:133-138` 之 `_oracle_membership` docstring 逐字「與被測函式**無因果關係**」「刻意逐行重寫、**不 import 投影**」，且它**目前也用 cutoff 判側** ⇒ `Task 9.2b` 落地時**同步以 decision-anchor 逐行重寫該 oracle**，G-3b（`main()` 每次都驗之 `g1_membership != g3b_oracle`）即自動成為區分閘：換錨改側兩邊同步、實作寫錯只有投影那邊改即紅。**不必**新造 `allowed_reanchor_diff` 檔。另採納三家共同要求：改寫 §G 通過條件為「以新錨為 exact 基準」、保留 `decision == cutoff` 事件**零位移**硬斷言、`decision != cutoff` 邊界 fixture 須進 §V 與 mutation，並依 codex 保留 **v8 baseline 不覆寫**） |
| **K2 `Task 9.1` 殘留決策未落地、9A 目標互斥（三家獨立撞題）**——「Task9.1將終端可見性延期後，Pha」「`Task9.1`v8具名殘留使Phas」「Task9.1雖改採終端可見性具名殘留（」 | P1 | CODEX-R8-P1-02, COMPOSER-R8-P1-02, GROK-R8-P1-02 | 採納（第九次修訂須**同批改完四處**：`:140` 標題句「缺任一層即視為 9A 未完成」刪去 API／前端；`:135` 目標句改為「producer 層誠實揭露」；`:204` `Task 9.4` 之「同批必須補終端揭露」改掛同一殘留；`M-SU-D2-02`／`03` 改指 summary 與 `metadata.split_unify` 或刪除。🔴 **並真的寫進 §N**——此為我上一版寫了「登記於 §N」卻沒登記的部分） |
| **K3 殘留類別之判定**——「`Task9.1`將終端可見性標為`bl」 | P1 | COMPOSER-R8-P1-03 | 部分採納（**駁回**「`blocked-by` 須指名具體阻塞票」之前提：`templates/BRIEF_REVIEW_TEMPLATE.md:71` 之 `reason_code` 閉集為 `blocked-by`／`needs-research`／`cost`／`out-of-scope`（**四值**），且同檔 `R-BRIEF-1` 實例逐字為「`blocked-by` **現行派工架構**」＝指向架構限制而非票號 ⇒ 本案（投影路徑無生產接線）用 `blocked-by` **合規**，grok 判定為正確。**採納**其成立部分：殘留**必須真的寫進 §N**。🔴 主委自記：我先前依「分歧採較嚴版」採 composer 是**套錯場合**——該規則適用於雙方皆合規而寬嚴不同，此處是一方前提與範本牴觸，應查原文） |
| **K4 `metadata.split_unify` 是 exact-key 契約，加鍵會被擋（codex 獨得）**——「D-002要求`metadata.spl」 | P1 | CODEX-R8-P1-03 | 採納（`Task 9.1` 須補列同步施工面：`momentum/Analysis/contracts/split_unify.json`、`build_split_unify_disclosure`（`split_projection.py:123-180`，現回**五鍵**）、唯一 caller `ic_filter_orchestrator.py:1530-1534`、`tests/api/test_splitunify_disclosure.py:149-151,270-277` 之 exact-key 斷言，並明定新鍵型別為 `Dict[str, int]`；🔴 **reason 封閉值集不得改動**。此條使第三交付層之成本被誠實揭露——若成本過高，應與 K2 一併重新評估 9A 範圍） |
| **K5 時間域四條規則重疊、越界可先被判 train/test（codex 獨得）**——「Task9.2b的時間域四條規則有重疊且」 | P1 | CODEX-R8-P1-04 | 採納（我在 R7 才把判準從「位置映射」改成時間域，改完**又漏了邊界前置**：`index=[100,200,300,400]`、`train_last=200`、`test_start=300` 時 `decision=50` 同時命中「`<= train_last` ⇒ train」與「早於 `index_ms[0]` ⇒ raise」。修法：先以 `index_ms[0] <= decision_at_ms <= index_ms[-1]` 作**前置條件**（不滿足即 raise），**再**套三段式；並補 early／late 之 §V 斷言） |
| **K6 `(6.2)` 義務與 `Task 9.4` baseline 互斥（兩家）**——「J6將`baseline`之`n_tes」「`D-002-C6`(6.2)義務仍規定」 | P1 | COMPOSER-R8-P2-02, GROK-R8-P1-03 | 採納（改寫 `(6.2)` L92：在**事件級物化**前提下 `baseline` 之 `n_test`＝事件數（＝樣本數），刪去「複合鍵列數、不得改判為事件數」之例外句；若未來另立 per-TF adapter 再改義務。同步任何仍寫「複合鍵列數」之 §V 與 mutation） |
| **K7 反向 mutation 現行不紅、應紅測試未具名（兩家）**——「`M-SU-D2-04`／`06`–`1」「七條反向mutation中，`M-SU-」 | P1 | COMPOSER-R8-P2-01, GROK-R8-P1-04 | 採納（§V `Task 9.3` 把七條逐一指到**具名檔**；主委已實跑 `ls` 盤好落點：`04`→`test_feature_materialization.py`、`06`→`test_tables.py`、`08`→`test_counterexample_classifier.py`、`09`→`test_candidate_ledger.py`、`10`→`test_dedupe.py`、`02`／`03`→`test_splitunify_derive.py`；`07`（`ic_feed`）無專屬檔須擇 `test_gap3_conditional_ic.py` 或新建、`11`（前端）須新建 vitest。🔴 **在那些測試實際存在前，不得宣稱 mutation 網已閉**） |
| **K8 `M-SU-D2-02`／`03` 與殘留決策結構互斥**——「`M-SU-D2-02`／`03`仍要求」 | P2 | COMPOSER-R8-P2-03 | 採納（隨 K2 同批處理：改指 summary 與 `metadata.split_unify` 結構，或刪除並保持 ID 連續；不得留著逼實作者違反殘留去造 API 測試） |

**Verdict**: 需修補後合併

**本輪主委自評**

1. **K2 是我「寫了承諾卻沒執行」**：`Task 9.1` 寫「登記於 §N」而 §N 無此條，三家獨立抓到。承諾與動作只隔三行。
2. **K5 是我改判準時的邏輯漏洞**：R7 才因「位置映射未定義」改成時間域，**改完又漏了邊界前置**，四條規則彼此重疊。codex 獨得。
3. **K4 揭出第三交付層的真實成本**：`metadata.split_unify` 是 exact-key 契約且有測試鎖住，我當初把它當「順手擴欄」寫進交付，**沒查它是封閉契約**。
4. **K3 我採納規則時套錯場合**：「分歧採較嚴版」適用於雙方皆合規，此處一方前提與範本牴觸——應查原文而非挑保險的那邊。已自行更正並記錄。

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R8-P1-01
**斷言**: G-4a 的「重凍後只准因換錨改側」目前不可機械歸因，會讓錯誤實作與合法換錨差異一起被新 golden 接受。
**碼證**: `freeze_splitunify_golden.py:373-382` 的 `--write` 直接覆寫 golden；現行 `_manifest` 把 decision_at_ms 設成 feature_cutoff_ms，oracle 也沿用 cutoff，沒有 immutable v8 baseline、獨立 expected delta 或 decision!=cutoff fixture。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c; scripts/freeze_splitunify_golden.py#e331623163d2
[MAJOR] 信心度=High；重凍可同時掩蓋 membership/fingerprint 錯誤，commit message 不是 gate。保留 v8 baseline，另以獨立 old/new anchor 計算逐事件 expected side-flip，僅允許該集合變更且其餘 payload/NaN-mask/hash exact，並加入 decision_at_ms != feature_cutoff_ms fixture。
## CODEX-R8-P1-02
**斷言**: Task 9.1 將終端可見性延期後，Phase 9A 的「使用者看得到」與實際交付互斥；`blocked-by` 是呼叫圖事實但不是完成理由，且 §V 的舊 API/UI mutation 仍不可達。
**碼證**: `api/services/case_import_service.py:1592-1609` 實跑對 `build_event_keys` 為 0 個呼叫、只走 `run_event_study_only_with_params`；D-002 卻同時保留 terminal-visibility objective、producer-only delivery 與 API/UI mutation 02/03。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c; api/services/case_import_service.py#d2571793953f; tests/api/test_splitunify_event_study_only.py#c00ff1c14753
[MAJOR] 信心度=High；只完成 producer/summary 會讓實際使用者仍看不到丟棄列，驗收不能通過。要麼把 Phase 9A 留 blocked 並在 TODO §E 登記具名 residual/觸發依賴，要麼擴大本票到真實 producer route；不可用僅列 §N 的敘述冒充完成。
## CODEX-R8-P1-03
**斷言**: D-002 要求 `metadata.split_unify` 新增 `discarded_rows_by_feature_tf`，但既有封閉 contract、producer 與 orchestrator/test/UI shape 仍是精確五鍵，Task 9.1 未列出同步施工面。
**碼證**: `build_split_unify_disclosure` (`split_projection.py:123-180`) 只回五鍵且唯一 caller `ic_filter_orchestrator.py:1530-1534` 不傳 discarded；`tests/api/test_splitunify_disclosure.py:149-151,270-277` 對 `split_unify` 做 exact-key assertion。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c; momentum/Analysis/event_samples/split_projection.py#99bfddace904; momentum/Analysis/contracts/split_unify.json#5aaf5f8efa15; tests/api/test_splitunify_disclosure.py#f1bd211204f7
[MAJOR] 信心度=High；只改 summary/metadata 會被現行 contract gate 擋，改 contract 又需明定 Dict[str,int] schema、producer、caller、Python/TS tests。把這些檔案與 exact-key migration 納入 Task 9.1，並明確保留 reason 封閉值集。
## CODEX-R8-P1-04
**斷言**: Task 9.2b 的時間域四條規則有重疊且順序宣稱不得調換，故索引界外 decision 可能先被判 train/test 而非 fail-closed raise。
**碼證**: `decision<=train_last_ms ⇒ train` 與 `decision>=test_start_ms ⇒ test` 排在「早於 index_ms[0]／晚於末列 ⇒ raise」之前；例如 index=[100,200,300,400]、train_last=200、test_start=300 時 decision=50 同時命中 train 與 outside，decision=450 同時命中 test 與 outside。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c; momentum/Analysis/event_samples/split_projection.py#99bfddace904
[MAJOR] 信心度=High；實作者可合法選先分類，造成越界事件進 train/test。先以 `index_ms[0] <= decision <= index_ms[-1]` 作 precondition 並補 early/late tests，再套三段式側別規則。
## COMPOSER-R8-P1-01

**斷言**: §G (G-4a) 要求單 TF golden 於 Task 9.2b 後重凍且「僅允許因換錨而改側」，但規格未提供機械 allowlist／雙路徑 diff，重凍後**無法區分**合法換錨與實作寫錯导致的改側，回歸錨對改側類缺陷失效。

**碼證**: SPEC L127–128 (G-4a)；`alignment.py:87-93`；PROBE `test_start=1000, decision=1000, cutoff=900` → old train／new test；`freeze_splitunify_golden.py` 無 side-diff allowlist 輸出。RECHECK: 雙跑 cutoff vs decision 判側，比對 diff 集合是否等於 `{e | decision_at_ms != feature_cutoff_ms}` 之理論集合。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;momentum/Analysis/event_samples/alignment.py#0da3c48b2668;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。Task 9.2b 實作後若邊界公式 off-by-one，重凍會把錯側**固化進 golden**；後續 mutation 22（判側改回 cutoff）也可能被「已重凍」掩蓋。**修法**：採必答 2 替代①或②——CI 必備 `allowed_side_diff_events.json` 或 cutoff-anchor 平行鍵；§G 刪「僅允許一種差異」之空稱，改為可執行斷言。

## COMPOSER-R8-P1-02

**斷言**: `Task 9.1` v8 具名殘留使 Phase 9A 對終端使用者**零揭露**，且第三交付層「`metadata.split_unify` 承載 `discarded_rows_by_feature_tf`」在生產 IC 路徑上**不可達**——與 L135 目標及 §V L214 互斥。

**碼證**: L135「終端使用者看得到」；L145–147 殘留；`ic_filter_orchestrator.py:1530-1534` 僅 `build_split_unify_disclosure(n_test=...)`；`split_projection.py:175-177` 回傳無 discarded；`rg discarded_rows_by_feature_tf` → 0。RECHECK: 對讀 L135／L146／L214 與上述三處。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293;momentum/Analysis/event_samples/split_projection.py#55ca7327764f

[BLOCKING] 信心度=High。9A 交付後使用者仍完全看不到丟棄列；實作者對 `metadata.split_unify` 寫契約測試卻無生產資料流 ⇒ 假綠。**修法**：① 收回 L135「終端可見」或降級 Phase 9A 為「producer-only」並改 Phase 名；② 刪 §V 對 `metadata.split_unify` 之 discarded 斷言，改為僅 `EventSplitPlan.summary`；③ 或先開「projection wiring」Task 再接 9A 終端層。

## COMPOSER-R8-P1-03

**斷言**: `Task 9.1` 將終端可見性標為 `blocked-by` 並稱「登記於 §N」，但 §N **無對應殘留條目**，且零 `EventSamplePipeline.run` 呼叫點屬能力缺口而非被具名票阻塞——殘留分類與治理登記皆不成立。

**碼證**: L147「理由類別 `blocked-by`…登記於 §N」；§N L258–265 僅列 `SU-RESID-2`／`D1`／`R-3`／`R-4` 等，**無** 9.1 終端揭露；`api/` 無 `.run(` 生產呼叫（`case_import_service.py:1605` 僅註解提及）。RECHECK: `sed -n '147p;258,265p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;api/services/case_import_service.py#55ca7327764f

[BLOCKING] 信心度=High。治理模板 §2 要求殘留須在 §N 具名且理由成立；缺失會讓 R-5／D1 與本殘留混淆，後續無觸發條件可追。**修法**：§N 新增條目（例 `SU-RESID-9A-UI`，`blocked-by: <projection-wiring Task ID>` 或改 `needs-research`）；若堅持 `blocked-by` 須指名阻塞票號而非「零 grep」。

## COMPOSER-R8-P2-01

**斷言**: `M-SU-D2-04`／`06`–`11` 七條反向 mutation 中，**六條**在現行測試面下誤改為複合鍵**不會紅**——Task 9.3 只寫「加防誤改回歸測試」未派工到具名檔案，mutation 目錄形同空殼。

**碼證**: mutation 表 L230–237；`rg '誤改為複合鍵|byEventId.*composite' tests/` → 0；`test_dedupe.py` 無廣播案例；`tests/frontend` 無 `byEventId` 複合鍵匯出測試。RECHECK: 對七 ID 逐條 grep 應紅測試名稱。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c

[MAJOR] 信心度=High。實作者照 (5.1) 甲類維持 event-level，mutation 06–11 永不觸發 ⇒ mutation 自證失敗或被迫假綠。**修法**：§V Task 9.3 增具名 pytest 路徑（例 `tests/momentum/event_samples/test_splitunify_event_level_guards.py`）覆蓋七條；或暫標 `needs-research` 直至測試存在。

## COMPOSER-R8-P2-02

**斷言**: J6 將 `baseline` 之 `n_test` 更正為事件數（L205），但 `D-002-C6` (6.2) L92 仍寫 baseline 之 `n_test` 為「實際模型輸入樣本數（複合鍵列數）」——同檔兩處量詞**未同步**，實作者不知以哪條為準。

**碼證**: L92 vs L205；`baseline.py:118-121` `n_test = len(idx)` 隨 `features_at_decision` 索引（事件級物化下 `len(idx)`＝事件數）。RECHECK: `sed -n '92p;205p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;momentum/Analysis/event_samples/baseline.py#38c7ec473653

[MAJOR] 信心度=High。Task 9.4 驗收與 C6 義務衝突時，Agent 可能改 `n_test` 語意卻通過錯誤斷言。**修法**：修 (6.2) L92——在事件級物化前提下 baseline 樣本數＝事件數，刪除「複合鍵列數」例外句；或保留例外但明寫「僅適用 per-TF adapter 未來票」。

## COMPOSER-R8-P2-03

**斷言**: `M-SU-D2-02`／`03` 仍要求 API 回應／前端揭露契約測試，但 v8 已將終端可見性具名殘留且 §V L214 作廢該兩層——mutation 與殘留決策**互斥**，實作者無合法應紅測試可寫。

**碼證**: mutation L228–229；§V L214「v7 之 API 回應／前端型別兩層作廢」；L147 終端殘留。RECHECK: 對讀三處。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c

[MAJOR] 信心度=High。mutation 自證時 02／03 永遠灰態（寫測試違殘留、不寫測試違 mutation）。**修法**：刪除或改為 `DEGRADE` 直至接線；或將應紅測試改指 `EventSplitPlan.summary` 鍵（與 01 合併）。

## GROK-R8-P1-01

**斷言**: §G (G-4a) 允許 Task 9.2b 落地後重凍單 TF golden，但未提供可機械計算的 `allowed_reanchor_diff`；L127 仍要求「任一單 TF 舊值位移即 FAIL」，與 (G-4a) 互斥——重凍當次無法區分「因換錨改側」與「實作寫錯」。

**碼證**: SPEC L127「任一單 TF 舊值位移即 FAIL」↔ L128「重凍一次…僅允許因換錨而改側…須逐筆列出並在 commit 訊息說明」。`alignment.py:87-93` 允許 `cutoff < decision`。VERIFY 探針：`cutoff=900,decision=1000,test_start=1000,train_last=900` ⇒ 舊 train／新 test；同邊界下 `train_last` off-by-one 與不等式誤判可得到相同新側。RECHECK: 對讀 L127–128；重跑 `/tmp/grok-splitunify-b9-review-r8/probe_g4.txt` 邏輯。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;momentum/Analysis/event_samples/alignment.py#0da3c48b2668;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。不改則 Task 9.2b 實作後重凍時，任何 `g1_membership` 漂移都可寫進 commit 當「換錨」，回歸錨失去否證力。**修法**：①改寫 L127 通過條件＝「(G-4a) 新錨為 exact 基準」；②重凍前用 fixture 純函式算出 `allowed_reanchor_diff`（僅 `decision!=cutoff` 且兩套判側不一致之事件），重凍後 `actual_diff` 必須與之**集合全等**；③保留 `decision==cutoff` 事件零位移之硬斷言；④`decision!=cutoff` 邊界 fixture 必須進 §V／mutation，不得只寫在 (G-4) 散文。**可行性**：`train_last_ms`／`test_start_ms`／每事件 `decision_at_ms`／`feature_cutoff_ms` 皆可自 fixture 取得；比對是 set equality，無需人工讀 commit。

## GROK-R8-P1-02

**斷言**: Task 9.1 雖改採終端可見性具名殘留（`blocked-by`），但目標句、§N 登記、`M-SU-D2-02`／`03`、Task 9.4 終端揭露句均未同步——Phase 9A「使用者看得到」在交付定義上仍互相矛盾，靜默丟棄對使用者可見面仍然完全看不見。

**碼證**: L135「必須讓**終端使用者**看得到」；L147「登記於 §N」但 `### §N` 全文無終端可見／discarded／投影接線條目（僅 `R-4` 含 `blocked-by`）；mutation L228–229 `M-SU-D2-02`「不傳到 API 回應」／`M-SU-D2-03`「前端不顯示」；Task 9.4 L204「同批必須補該旗標之終端揭露」。`api/` 嚴格 `EventSamplePipeline().run` 命中 0；`build_split_unify_disclosure` 無 discarded 參數（`split_projection.py:123-143`）；IC `:1530` 只傳 `n_test`。RECHECK: `sed -n '134,147p;204p;228,229p;258,266p' docs/SPLITUNIFY_SPEC.D-002.md`＋本輪 api grep。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;momentum/Analysis/event_samples/split_projection.py#99bfddace904;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293

[BLOCKING] 信心度=High。`blocked-by` 類別有碼證、可保留；缺陷是**殘留決策沒落地**。實作者會同時看到「9A 未完成若缺 API／前端」「不得新增 API」「mutation 02／03 要紅 API／前端」。**修法**：①改 L135／Phase 9A 目標為 producer 層誠實（刪「終端使用者看得到」或明寫本延伸不做終端）；②§N 新增具名殘留（觸發＝`api/` 出現投影 `run()` 生產接線）；③`M-SU-D2-02`／`03` 改指 summary／`metadata.split_unify` 結構，或刪除並改 ID 連續；④Task 9.4 終端揭露改掛同一殘留，不得寫「同批必須補」。**可行性**：純 SPEC 同步；零呼叫點事實已多次實跑。

## GROK-R8-P1-03

**斷言**: `D-002-C6` (6.2) 義務仍規定 `baseline` 之 `n_test` 為複合鍵列數且「不得改判為事件數」，與 Task 9.4「物化維持事件級 ⇒ baseline `n_test` 仍為事件數、v7 一事件兩列作廢」同檔互斥。

**碼證**: L92「`baseline` 之 `n_test` 語意為**實際模型輸入樣本數**（複合鍵後即 `(event_id, feature_timeframe)` 列數），**不得**改判為事件數」；L205「故 `baseline` 之 `n_test` 在本延伸落地後**仍為事件數**…v7 之『一事件兩列、`n_test`＝2』作廢」。碼：`baseline.py:105-121` `n_test = len(idx)`，`idx` 來自事件級 `features_at_decision.index`。RECHECK: 對讀 L92↔L205↔`baseline.py:105-121`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;momentum/Analysis/event_samples/baseline.py#38c7ec473653

[BLOCKING] 信心度=High。義務區塊是 `obligation_block_check` 權威文；Agent 可依 (6.2) 寫「一事件兩列、`n_test=2`」fixture，直接違反 Task 9.3／9.4 物化定案。**修法**：改寫 (6.2) 與 Task 9.4 同文——在事件級物化前提下 `baseline.n_test`＝事件數（＝樣本數）；若未來 per-TF 模型輸入另立 adapter 再改義務。同步任何仍寫「複合鍵列數」之 mutation／§V。**可行性**：一字級義務修訂；與已採納之 J6 同向。

## GROK-R8-P1-04

**斷言**: 七條反向 mutation 中，`M-SU-D2-02`／`03` 與 Task 9.1 殘留決策結構互斥（應紅面已被延後）；`M-SU-D2-06`–`11` 在現行測試面即使誤改為複合鍵也不會紅——mutation 表把「應紅測試」寫成尚未存在的斷言，不能當已具備的回歸網。

**碼證**: mutation L228–229 仍指 API／前端；L232–237 之「應紅測試」為散文描述。現行 `tests/momentum/event_samples`／前端 vitest **無**「索引不得為複合鍵」「Map 鍵不得含 feature_timeframe」類斷言（本輪 grep `discarded_rows`／`byEventId` 防誤改面無命中）。對照：`feature_materialization.py:138-140` 之 `n_input` 不變式使 `04` 在多 TF 輸入下**可以**紅。RECHECK: `grep -rn 'discarded_rows_by_feature_tf\|byEventId\|複合鍵' tests/momentum/event_samples frontend --include='*.py' --include='*.ts*' | head`；對讀 mutation 表 02–11。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;frontend/src/lib/eventExport.ts#90528a561479;momentum/Analysis/event_samples/baseline.py#38c7ec473653

[BLOCKING] 信心度=High。不改則：(a) 實作者為讓 02／03 紅而違反殘留去造 API 測試；或 (b) 06–11 被當成已有防護，Task 9.3「加防誤改回歸」被省略而假綠。**修法**：02／03 與 P1-02 同批改指 producer／summary／`metadata.split_unify`（或刪除）；06–11 之「應紅測試」改為**具名**新增測試檔／函式（可複製命令），並在 §V Task 9.3 列同一組 ASSERT；在該等測試落地前不得宣稱 mutation 網已閉。**可行性**：Task 9.3 已要求「誤改為複合鍵即紅」——缺的是把 mutation 列接到具體測試名，而非再加新架構。

---

