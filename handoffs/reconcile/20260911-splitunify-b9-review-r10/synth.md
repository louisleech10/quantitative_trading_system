# Reconcile — 20260911-splitunify-b9-review-r10

**來源** 20260911-splitunify-b9-review-r10-codex.md, 20260911-splitunify-b9-review-r10-composer.md, 20260911-splitunify-b9-review-r10-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **M1 (G-4e) 第三份未禁共用實作，擋不住三份同錯（三家獨立撞題）**——「G-4e的「第三份純函式」沒有要求與投影」「(G-4e)將第三份判準定義為「以Tas」 | P1 | CODEX-R10-P1-01, GROK-R10-P1-01 | 採納（**我的判斷錯誤**：第三份仍是「同一三段式的另一次編碼」。主委已自跑探針複驗（`handoffs/20260912-splitunify-b9-probe-g4e-triple.py`）：獨立實作時 `g4e_pass=False`、三份同錯時 `g4e_pass=True`。改法＝第三份改為 fixture **字面** `expected_side`（人手依三段式逐筆填，與公式編碼脫鉤），並**明禁** import／呼叫投影、oracle 及其共用 helper；主委已驗 `_event_keys()` 為逐 row dict 構造，加一欄成本為一欄＋一次人工填值＋一行比對；VERIFY:20260912T111826Z-splitunify-b9-g4e-triple） |
| **M2 整鏈驗值只在 Task 散文，§V 仍只驗鍵（三家獨立撞題）**——「Task9.1雖寫producer→su」「L7採納之producer→metada」「L7在`Task9.1`L150已要求p」 | P1 | CODEX-R10-P1-02, COMPOSER-R10-P1-02, GROK-R10-P1-03 | 採納（§V L220 之 metadata 句由「`ASSERT … 帶該鍵`」升級為**值相等**，與同句 summary 斷言對稱；並依 codex 指名「同一 caller／context 的來源物件」，不得只寫抽象交接） |
| **M3 baseline 舊鍵命運未寫死（三家獨立撞題）**——「L8新增`n_test_events`/」「L8第十次修訂在`Task9.4`L21」「L8修訂只改了`Task9.4`L211」 | P1 | CODEX-R10-P1-04, COMPOSER-R10-P1-01, GROK-R10-P1-02 | 採納（三處同改 `(6.2)` L92／`Task 9.4` L208／L211；並依主委三項碼證**擇定刪除舊鍵**——`baseline.py:120` 為唯一生產寫入點、前端命中皆屬別的 `n_test`、該鍵不在 `split_unify.json` 之 deny-by-default 登記內 ⇒ 留別名反使其繼續漂移。新增 `M-SU-D2-32`（保留舊鍵即紅）） |
| **M4 §V 缺 `Task 9.4` 母斷言**——「`M-SU-D2-31`應紅測試指向「`」 | P2 | COMPOSER-R10-P2-01 | 採納（§V 新增 `Task 9.4` 條目：`ASSERT WHEN test 含 e1 且物化 failures 含 e1 THEN n_test_events=1 AND n_test_samples=0`；此為主委自證清單遺漏之第二類——**mutation 應紅測試須有母斷言**） |
| **M5 座標契約未定，validator 會誤拒合法交錯批（codex 獨得）**——「Task9.2b要求derive呼叫既有」 | P1 | CODEX-R10-P1-03 | 採納（🔴 **我要求呼叫 validator 卻沒定義座標 adapter**：D-001 之 `row_index_local` 為**局部**座標，而 `validate_split_pair_integrity` 吃**全域** `row_index`；codex 實跑交錯 fixture 得 `IndexError: plan.row_index contains positions outside base universe` ⇒ 照現文實作會**錯誤拒絕合法多標的交錯批**。改法：明定傳入為 full-universe inputs，或定義 local→global rebase adapter；並補「非連續 global positions」fixture） |
| **M6 (G-4d)① 無不可變落點（codex 獨得）**——「G-4d的「保留v8baseline、重」 | P1 | CODEX-R10-P1-05 | 採納（`freeze_splitunify_golden.py:373-386` 現行為 `golden_path.write_text(...)` **直接覆寫**，且 golden 檔內**無**名為 v8 之舊鍵 ⇒ 該條款目前無落點。改法：指定 **separate baseline 檔或版本化鍵＋hash**，重凍前先驗舊 hash 未變、再允許列舉差異；`M-SU-D2-29` 須指名該不可變物件與測試落點） |
| **M7 `D-002-C5` 條數與實列不符（codex 獨得）**——「D-002-C5標題宣稱16處，但自身四」 | P1 | CODEX-R10-P1-06 | 採納（標題寫「16 處」而四層 named entries 機械計數為 **4+6+6+4=20** ⇒ 實作者按 16 或 20 皆可自稱合規。改法：建立**唯一編號 register**，逐列映射 `Task 9.3`／`9.4`／`9.5`、mutation 與測試，並修正標題與回退文字。此為 **R5 條數不符之同型第二次**，須納入自證清單） |
| **M8 殘留觸發條件之 grep 會漏報（codex 獨得）**——「`SU-RESID-9A-UI`的tri」 | P2 | CODEX-R10-P2-07 | 採納（現行觸發式只匹配 inline constructor call，**漏掉** `pipeline = create_event_sample_pipeline(); pipeline.run(...)` 之合法接線 ⇒ 殘留可被錯誤維持。改法：改為更廣之生產 call-site 掃描（排除 tests），或以 AST 判定；SPEC §N 與 TODO §E 兩處同步） |

**Verdict**: 需修補後合併

**本輪主委自評**

1. **M1／M5 是我的判斷錯誤**：前者我以為「第三份純函式」即足夠，三家與我自己的探針都證明擋不住同錯；後者我要求呼叫既有 validator，**卻沒查它吃的是全域座標**——這與「指名落點不等於該落點走得到」是同一型（第三次）。
2. **M2／M4 是自證清單的兩個新漏洞**：只驗「新增內容落點」，未驗「Task 正文與 §V 是否對稱」「mutation 是否有母斷言」。
3. **M7 是條數不符同型第二次**（R5 已被抓過一次），且這次我的自證只數了 mutation、**沒數 C5**。
4. **收斂性**：R10 共 13 條、三家獨立撞題三群，且**首次出現大量「部分閉合」**（codex 判 L1／L2／L8／L9／L10 為部分閉）——性質仍具體可閉合，停輪條件未觸發。

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R10-P1-01
**斷言**: G-4e 的「第三份純函式」沒有要求與投影、oracle 及共享 helper 實作獨立，不能阻止三者同錯。
**碼證**: VERIFY `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '128,130p;264,268p'`：G-4e 僅要求三者全等、M-SU-D2-28 僅改投影+oracle；反例 `decision=250, cutoff=200, train_last=200, test_start=300`，共享錯誤 helper 以 cutoff 判 train 時三者全等，G-3b/G-4e 均綠。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; scripts/freeze_splitunify_golden.py#e331623163d2。G4e 可抓不對稱錯誤但放過相關性錯誤；修法是第三判準禁止 import/call 兩邊及其 helper，另以 fixture literal expected-side 與 mutation 驗證；信心度=High。
## CODEX-R10-P1-02
**斷言**: Task 9.1 雖寫 producer→summary→metadata handoff，現有唯一 metadata caller 仍無 `EventSplitPlan`/`discarded`，整鏈並未被指定到可執行入口。
**碼證**: VERIFY `nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '648,691p;1530,1534p'`：caller 只傳 `n_test/test_timestamps_ms/per_symbol_counts`；`rg -n 'EventSamplePipeline\(\)\.run|create_event_sample_pipeline\(\)\.run' api --glob '*.py'` stdout 為空、rc=1。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293; momentum/Analysis/event_samples/split_projection.py#99bfddace904。孤立 builder 單測可綠而真實 producer 計數遺失；修法是指名同一 caller/context 的來源物件與值相等 E2E，或移除不可達層；L7 未閉，信心度=High。
## CODEX-R10-P1-03
**斷言**: Task 9.2b 要求 derive 呼叫既有 validator，卻未定義 D-001 `row_index_local` 與 validator 全域 `row_index`/`ts` 的 adapter，合法交錯 multi-symbol 路徑可被錯誤拒絕。
**碼證**: VERIFY 實跑 `venv/bin/python` 交錯 A/B fixture stdout：`A row_index=[0] [2] row_index_local=[0] [1]`; `validator(local universe)= IndexError plan.row_index contains positions outside base universe`；SPEC `nl -ba ... | sed -n '184p;587,589p;634,637p'` 分別要求 validator、宣告 local index、傳入 local index。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; momentum/core/contracts.py#1471cef968a3。L9 的非空/不重疊補強成立，但座標契約未閉；修法是明定 full-universe inputs 或 local rebase adapter，並加非連續 global positions fixture；信心度=High。
## CODEX-R10-P1-04
**斷言**: L8 新增 `n_test_events`/`n_test_samples` 仍未定義既有 baseline `n_test` 的退役、alias 或唯一語意，物化失敗時下游可讀到歧義。
**碼證**: VERIFY `nl -ba momentum/Analysis/event_samples/baseline.py | sed -n '105,121p'` 顯示 `n_test=len(idx)`；實跑缺一個 test event 的 fixture stdout：`n_test=1 ... test_event_ids=['e2','e3'] ... intersection=['e2']`，故事件數=2、樣本數=1。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; momentum/Analysis/event_samples/baseline.py#38c7ec473653。L8 只部分閉合；修法是定義 baseline exact schema、明確移除/保留 `n_test` 並更新 consumer/test，固定 failure fixture 斷言兩量；信心度=High。
## CODEX-R10-P1-05
**斷言**: G-4d 的「保留 v8 baseline、重凍寫新鍵」沒有指定 immutable key/file/hash 或 allowed-diff schema，現行 `--write` 仍可直接覆寫同一 golden。
**碼證**: VERIFY `nl -ba scripts/freeze_splitunify_golden.py | sed -n '373,386p'` stdout 顯示 `golden_path.write_text(...)`；`sed -n '1,28p' tests/golden/splitunify/splitunify_golden.json` 只有 `g1_membership/g3b_oracle/g4...`，無名為 v8 的舊鍵；default freeze 實跑 stdout `GOLDEN OK` 只證目前單檔相等。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; scripts/freeze_splitunify_golden.py#e331623163d2; tests/golden/splitunify/splitunify_golden.json#f270e007ca98。M-SU-D2-29 沒有指定不可變物件與測試落點；修法是 separate v8 baseline/hash + versioned new key，先驗舊 hash 不變再允許列舉差異；L2 未完全閉，信心度=High。
## CODEX-R10-P1-06
**斷言**: D-002-C5 標題宣稱 16 處，但自身四層 named entries 可機械計為 20，沒有 canonical register 會讓逐處 mutation coverage 不可驗。
**碼證**: VERIFY `nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '70,82p'` 並計算 stdout `C5-layer-counts: 4+6+6+4=20`；標題原文為 `單鍵消費面（16 處，分四層）`。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab。實作者可按 16 或按 20 漏改/漏測；修法是公布唯一編號 register，逐列映射 Task 9.3/9.4/9.5、mutation 與測試，並修正回退文字；信心度=High。
## CODEX-R10-P2-07
**斷言**: `SU-RESID-9A-UI` 的 trigger/recheck 只匹配 inline constructor call，會漏掉合法的 factory assignment 後 `.run()` 生產接線。
**碼證**: VERIFY `rg -n 'EventSamplePipeline\(\)\.run|create_event_sample_pipeline\(\)\.run' api --glob '*.py'` stdout 空、rc=1；TODO/SPEC 皆把此 regex 當觸發。反例 `pipeline=create_event_sample_pipeline(); pipeline.run(...)` 不命中，殘留可錯誤維持。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab; docs/SPLITUNIFY_TODO.md#b3a646c0e1cc; momentum/factories.py#未取摘要。這是 governance trigger 漏報；修法是 AST/更廣的 production call-site 掃描並排除 tests、要求 canonical args；信心度=High。
ASSUMPTIONS_VERIFIED: R9 synth 21 findings/11 groups；D-002 mutation table 01–31 set 連續（實跑 rows=31,result=PASS）；golden default rc=0；obligation/format/xref rc=0；API inline trigger 當前 0。
TESTS_RUN: `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` rc=0（A/C 2 rows、B/D expected raise）；`venv/bin/python scripts/freeze_splitunify_golden.py` rc=0/GOLDEN OK；validator/baseline counterexample commands above；`bash scripts/obligation_block_check.sh ...`, `doc_format_precheck.sh ...`, `spec_xref_check.sh --synth ...` 皆 rc=0。
FAILURES_SEEN: 僅 review counterexamples：baseline missing-materialization n_test=1；local-universe validator IndexError；均為規格缺口證據，未修改程式。
SCOPE_CHANGES: none；只新增 `handoffs/20260911-splitunify-b9-review-r10-codex.md`，未改 code、SPEC、TODO、data_cache 或既有 dirty files。
NUMERIC_OR_SCHEMA_IMPACT: 未修改執行輸出；本報告指出 D-002 metadata/baseline/golden schema 與 C5 coverage 需補契約。
VERDICT: blocked
BLOCKED-BY: CODEX-R10-P1-01,CODEX-R10-P1-02,CODEX-R10-P1-03,CODEX-R10-P1-04,CODEX-R10-P1-05,CODEX-R10-P1-06
CLOSED:
STATUS: DONE
## COMPOSER-R10-P1-01

**斷言**: L8 第十次修訂在 `Task 9.4` L211 否定 baseline「樣本數＝事件數」恆等並要求雙量輸出，但 `D-002-C6`(6.2) L92 **仍逐字宣稱兩者等價**，同檔義務互斥，實作者可依義務塊跳過 `n_test_events`。

**碼證**: `sed -n '92p;211p' docs/SPLITUNIFY_SPEC.D-002.md`；`baseline.py:105-120` 現僅 `n_test=int(len(idx))`。RECHECK: 對讀 (6.2) 與 Task 9.4；`rg '樣本數＝事件數' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab;momentum/Analysis/event_samples/baseline.py#38c7ec473653

[BLOCKING] 信心度=High。Task 9.4 實作者讀 (6.2) 可合法只改 `n_test` 而不拆雙量，物化失敗反例再次靜默。**修法**：(6.2) 改為「baseline 須輸出 `n_test_events`／`n_test_samples`，不得宣稱恆等；既有 `n_test` 語意明定為樣本數或 deprecate」；§V 增 Task 9.4 物化失敗 fixture 斷言。

## COMPOSER-R10-P1-02

**斷言**: L7 採納之 producer→metadata **整鏈**驗收只寫在 `Task 9.1` L150，§V L220 仍只有 summary／metadata **分層**鍵斷言——與 R9「寫了要做卻沒進 §V」同型，孤立 builder 單測仍可假綠。

**碼證**: L150「驗收須為 producer→summary→metadata 整鏈測試」；§V L220 五條 ASSERT **無**整鏈字樣；`build_split_unify_disclosure`（`split_projection.py:123-180`）仍無 `discarded` 參數。RECHECK: 對讀 L150 vs L220；`rg '整鏈' docs/SPLITUNIFY_SPEC.D-002.md` 僅 Task 段。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。真實 IC 路徑計數可在 orchestrator 邊界遺失而分層測試全綠。**修法**：§V `Task 9.1` 增 `ASSERT 經 EventSamplePipeline.run（或等價 derive 路徑）之 discarded_rows_by_feature_tf 與 metadata.split_unify 同值`。

## COMPOSER-R10-P2-01

**斷言**: `M-SU-D2-31` 應紅測試指向「`Task 9.4` 物化失敗 fixture」，但 §V **無任何 `Task 9.4` 斷言列**——mutation 表與驗收目錄脫鉤（主委自證只驗 mutation 條數，未驗應紅測試是否有母斷言）。

**碼證**: mutation 表 L268 `M-SU-D2-31`；`rg '^- \`Task 9\.4' docs/SPLITUNIFY_SPEC.D-002.md` → **0**（§V 區段）。RECHECK: 對讀 L268 vs §V L218-235。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab

[MAJOR] 信心度=High。實作者可無測試依據實作 M-31 或宣稱已覆蓋。**修法**：§V 增 `Task 9.4`：`ASSERT WHEN test 含 e1 且物化 failures 含 e1 THEN n_test_events=1 AND n_test_samples=0`。

## GROK-R10-P1-01

**斷言**: (G-4e) 將第三份判準定義為「以 Task 9.2b 三段式從 fixture 欄位再編碼一次的純函式」時，**擋不住**投影／oracle／第三份被同一次改動寫入同一錯誤語意——三者仍全等而放行。

**碼證**: SPEC L129 (G-4e)、L227、`M-SU-D2-28`。VERIFY 探針：`decision=250,train_last=200,test_start=300` 正確＝`purged`；三份同寫 `decision < test_start ⇒ train` ⇒ `proj=oracle=third=train`，G-3b 與 (G-4e) **皆綠**。L129 對第三份**無**「不得與投影／oracle 共用實作」句（對照 L128 oracle「不 import 投影」）。RECHECK: 重跑 `/tmp/grok-splitunify-b9-review-r10/probe_g4e_l9.txt` 之 G-4e 段；`sed -n '129p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。這是 R9 `GROK-R9-P1-01`／L1 採納後的**剩餘洞**：方向對（要第三份），定義弱（第三份仍是同公式）。不改則 Task 9.2b 落地＋重凍可把「忘記隔離帶」同時寫進三處並通過 G-3b／(G-4e)。**修法**：①第三份改為 fixture **字面** `expected_side`（或獨立 expected-membership 表），對每個 `decision!=cutoff`／隔離帶／邊界事件預先填好；ASSERT `proj == oracle == fixture.expected_side`；②明令第三份**不得**與投影／oracle 共用函式／import；③保留現有「三段式純函式」最多當開發期輔助，**不得**單獨充當 (G-4e) 閘。**可行性證據**：同一探針顯示 `literal_expected="purged"` 時 `all_wrong_r6` 會紅；freeze 已有 per-event 欄位可加一欄；新邊界事件本就要進 fixture（§V L226 前置），填 expected_side 為同批一行成本。

## GROK-R10-P1-02

**斷言**: L8 修訂只改了 `Task 9.4` L211（雙量＋不得恆等），**未**回寫 `(6.2)` L92（仍寫樣本數＝事件數「等價」）與 L208「依 (6.2)…定為事件數」——同檔義務互斥，實作者可選任一側自稱合規。

**碼證**: L92 逐字「故其 `n_test`＝**樣本數＝事件數**，兩者在本延伸落地後**等價**」；L211 逐字「須**同時輸出** `n_test_events`…與 `n_test_samples`…**不得**宣稱兩者恆等」；L208「依 (6.2) 將 `n_train`／`n_test`／`n_purged` 明確定為事件數」。`baseline.py:120` 現行 `"n_test": int(len(idx))`。RECHECK: `sed -n '92p;208p;211p' docs/SPLITUNIFY_SPEC.D-002.md`；`sed -n '118,121p' momentum/Analysis/event_samples/baseline.py`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab;momentum/Analysis/event_samples/baseline.py#38c7ec473653

[BLOCKING] 信心度=High。屬本輪必答 2 之自證漏網（主委改 L211 沒 grep 回 (6.2)）。不改則：①Agent 依 (6.2) 可拒絕雙量；②或輸出雙量卻保留語意不明的舊 `n_test`，讀報告者混用。**修法**：①(6.2) 刪「等價」句，改寫為「`baseline` 必須同時輸出 `n_test_events` 與 `n_test_samples`；物化失敗時兩量可不等」；②L208 改為「summary／報告鏈之 `n_test` 為事件數；`baseline` 見 L211 雙量，**不**再使用單一 `n_test` 充當兩者」；③明定舊鍵 `n_test` 在 baseline 回傳中：**刪除**或**僅作 `n_test_samples` 之暫時別名並在 §V／mutation 限期移除**（擇一寫死）；④§V／`M-SU-D2-31` 已指向物化失敗 fixture——保持，並加 ASSERT 兩鍵皆在。**可行性**：純 SPEC 同步；碼側只多兩個 int 鍵；測試呼叫面已盤為 `test_baseline_oracle.py`／`test_mutation_guard.py`。

## GROK-R10-P1-03

**斷言**: L7 在 `Task 9.1` L150 已要求 producer→summary→metadata **整鏈驗值**，但 §V L220 對 `metadata.split_unify` 僅 ASSERT「**帶該鍵**」，未要求與 producer／summary **值相等**——孤立欄位單測仍可過 §V。

**碼證**: L150 逐字「驗收須為 **producer→summary→metadata 整鏈**測試（驗**值**相等，非只驗鍵存在）」；L220 逐字「`ASSERT metadata.split_unify 帶該鍵且其 reason 封閉值集未被改動`」（summary 句有「值與 producer 回傳相同」，metadata 句無）。`build_split_unify_disclosure` 簽名仍無 discarded（`split_projection.py:123-180`）；唯一 caller `ic_filter_orchestrator.py:1530-1534` 仍不傳。RECHECK: `sed -n '150p;220p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab

[BLOCKING] 信心度=High。屬本輪必答 2 之第二處自證漏網（改 Task 正文、§V 沒跟上）。不改則 L7 採納名存實亡：Agent 寫 `test_…_disclosure` 手塞 `discarded_rows_by_feature_tf={}` 即可滿足「帶該鍵」。**修法**：§V `Task 9.1` 改為 `ASSERT metadata.split_unify["discarded_rows_by_feature_tf"] == EventSplitPlan.summary["discarded_rows_by_feature_tf"] == producer.discarded`（值相等）；`M-SU-D2-03` 之應紅面加「鍵在但值與 summary 不一致」。**可行性**：L150 已寫交接路徑（summary → orchestrator → builder 參數）；§V 只差把「帶該鍵」升級為值相等——與既有 summary 值斷言對稱。

---

