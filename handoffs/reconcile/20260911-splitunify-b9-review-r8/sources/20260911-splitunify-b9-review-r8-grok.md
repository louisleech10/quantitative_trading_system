# SPLITUNIFY D-002 閉合輪 R8 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R8`  
family: grok  
findings-round: R8  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第八次修訂；full sha12 `a2ac7731fd7c`）  
上游收斂: `handoffs/reconcile/20260911-splitunify-b9-review-r7/synth.md`  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r8/`（交件後清除；保留 `/tmp/claude-501*`）  
本家待閉（敘述用，不入裁決欄）: `GROK-R7-P1-01`、`GROK-R7-P1-02`、`GROK-R7-P1-03`

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: R7 十五條歸八群、全部採納 → 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r7/synth.md`；本家三條皆在 J1／J3／J5 採納列

fact-verified: 第八次修訂已寫入 Task 9.3 與 (5.1) 同文、七條反向 mutation、時間域三段式＋隔離帶 `purged`、§G (G-4a)、Task 9.1 具名殘留敘述、baseline 於 Task 9.4 改事件數 → 本輪逐字讀 SPEC；`obligation_block_check`／`doc_format_precheck` 皆 rc=0；mutation 表列 26、ID 01–26 連續

fact-verified: golden `g1_membership.purged == ['gap1','gap2','tr_leak']`；`freeze_splitunify_golden.py:94,101-102` 刻意造隔離區 2 筆 → `python3` 讀 golden + `sed`

fact-verified: `api/` 對 `EventSamplePipeline().run`／`create_event_sample_pipeline().run` 嚴格命中 **0**；`pipeline.py:723-747` 仍為四參數閘＋`str(selected_timeframe)`；`build_split_unify_disclosure` 簽名無 `discarded` 參數 → grep／讀檔

fact-verified: §N **沒有**「終端可見性／discarded／投影接線」殘留條目（僅既有 `R-4` 含字面 `blocked-by`）→ 對讀 L147「登記於 §N」與 `### §N` 全文

fact-verified: `(6.2)` 義務仍寫 baseline `n_test`＝複合鍵列數且「**不得**改判為事件數」；Task 9.4 寫落地後「**仍為事件數**」→ 對讀 L92↔L205

assumed: §G (G-4a)「重凍一次、僅允許因換錨而改側」**在實務上可驗證**  
→ **否證**：SPEC 只要求「逐筆列出並在 commit 訊息說明」；無機械 oracle。探針顯示 off-by-one／不等式誤判與「合法換錨改側」可產生**相同**可觀測位移。見必答 2／P1-01。

assumed: `Task 9.1` 具名殘留**不會**讓 Phase 9A 名存實亡  
→ **否證**：L135 目標仍寫「必須讓終端使用者看得到」；§N 未登記；`M-SU-D2-02`／`03` 仍指向 API／前端；Task 9.4 仍要求同批終端揭露。見必答 3／P1-02。

assumed: 七條反向 mutation **能真的紅**  
→ **部分否證**：`04` 可依既有 `n_input` 不變式在多 TF 輸入下紅；`02`／`03` 與殘留決策互斥、現行無對應應紅面；`06`–`11` 在現行測試面無索引鍵形狀斷言，誤改不紅。見必答 4／P1-04。

assumed: `dedupe`「事件級保留＋廣播」不改變 `w=1/n`  
→ **本輪未否證**：`event_split._cluster_weight` 與 `dedupe` 權重皆建在事件級 table／clusters；廣播若只過濾 per-TF 存活列、不複製簇列，權重語意可維持。未另開 finding。

---

## 必答 1–5

### 1. 本家 R7 finding 是否閉合

| R7 ID | 判定 | 確認方式 |
|---|---|---|
| `GROK-R7-P1-01` | **CLOSED**（施工單已同步） | Task 9.3 L193–195 甲類維持＋丙類去重；`(5.3)`／`(5.4)` 改現況描述；`M-SU-D2-04`／`06`–`11` 已改反向。對讀 L74↔L190–195↔mutation 表 |
| `GROK-R7-P1-02` | **CLOSED**（隔離帶改回 purged＋時間域） | Task 9.2b L178–182：`train_last_ms`／`test_start_ms` 時間域；隔離帶 ⇒ `purged` 不得 raise；golden gap 敘述與探針一致 |
| `GROK-R7-P1-03` | **CLOSED（決策字面）／殘留落地未完成 → 重開 R8** | Task 9.1 L145–147 已改「具名殘留＋只交 producer／summary／`metadata.split_unify`」。但目標句、§N、mutation 02／03、Task 9.4 終端句**未跟著改完** ⇒ 以 `GROK-R8-P1-02` 重開 |

### 2. 攻 §G (G-4a)

**(G-4a) 取捨方向（承認換錨改側、保住 `(3.1)`）可成立；但「僅允許一種差異」目前不可機械驗證，會讓回歸錨在重凍當次失效。**

碼證衝突：
- L127 仍寫「單 TF 路徑逐值不變（exact）；**任一**單 TF 舊值位移即 FAIL」
- L128 (G-4a) 又允許重凍且「僅允許因換錨而改側」

機械區分失敗（探針 `/tmp/grok-splitunify-b9-review-r8/probe_g4.txt`）：
- 合法換錨：`cutoff=900, decision=1000, test_start=1000, train_last=900` ⇒ 舊 train／新 test
- `train_last` off-by-one（899）與 R6 不等式誤判，在此邊界上可得到**相同**新側 `test`
- SPEC 驗收手段＝「commit 訊息逐筆說明」⇒ 審查者無法用腳本區分「允許的換錨」與「實作寫錯」

**替代（須寫進 §G，取代 commit 散文）**：重凍前用 fixture 欄位純函式算出  
`allowed_reanchor_diff = {eid: (old_side, new_side) | decision!=cutoff ∧ side_cutoff≠side_decision}`；  
重凍後 `actual_diff` 必須與該集合**全等**；集合外任何位移 FAIL；`decision==cutoff` 之事件必須零位移。並改寫 L127 通過條件為「以 (G-4a) 新錨為 exact 基準」。→ **P1-01**

### 3. 攻 `Task 9.1` 具名殘留

**`blocked-by` 類別本身正確**（零 `EventSamplePipeline.run` 呼叫點，依賴投影生產接線）。  
**但現行寫法讓 Phase 9A「消除靜默丟棄之誠實性缺陷、且終端使用者看得到」名存實亡**，且殘留未真正入帳：

| 檢查項 | 結果 |
|---|---|
| L135 目標「必須讓終端使用者看得到」 | **未改**，與 L147 殘留互斥 |
| L140 標題「缺任一層即視為 9A 未完成」仍含 API／前端 | 作廢落點字面仍可誤導實作者 |
| L147「登記於 §N」 | §N **無**對應條目（grep 終端可見／discarded／接線 → False） |
| `M-SU-D2-02`／`03` | 仍要求 API 回應／前端面板應紅測試（J8 宣稱要改、未改） |
| Task 9.4 L204 | 仍要求「同批必須補」`insufficient_events_in_test` 終端揭露 |
| 第三交付層 `metadata.split_unify` | `build_split_unify_disclosure` 無 `discarded` 參數；IC caller 無 discarded 來源 ⇒ 擴欄後仍無真實值可填 |

⇒ 9A 交付後，使用者可見面對「靜默丟棄」**仍然完全看不見**；producer／summary 鍵只在測試／內部物件可見。  
**修法**：改寫 L135／Phase 9A 目標為「producer 層誠實揭露」；§N 具名殘留（類別 `blocked-by`、觸發＝投影路徑出現生產 `run()` 接線）；刪除或改寫 `M-SU-D2-02`／`03` 與 Task 9.4 終端句，使其與殘留一致；或改採 (b1) 真接一條可達路徑。→ **P1-02**

### 4. 七條反向 mutation 是否真能紅

| ID | 誤改後誰該紅 | 現行能否紅 |
|---|---|---|
| `M-SU-D2-04` | 物化值斷言；既有 `:138-140` `n_input` 不變式 | **能**（多 TF 輸入進 materialization 時既有 assert 可炸） |
| `M-SU-D2-06` | tables 事件級 lookup 值斷言 | **現行不能**——無防誤改測試；單 TF fixture 下改複合鍵索引甚至可能仍綠 |
| `M-SU-D2-07` | ic_feed 逐列值 | **現行不能**（同上） |
| `M-SU-D2-08` | 分類綁定 | **現行不能** |
| `M-SU-D2-09` | 帳本綁定 | **現行不能** |
| `M-SU-D2-10` | 「兩 TF 皆存活而簇仍一列」 | **現行不能**（該測試尚未存在） |
| `M-SU-D2-11` | 匯出 extras 值斷言 | **現行不能**（無 vitest 斷言 Map 鍵形狀） |

另：**`M-SU-D2-02`／`03` 不是反向 mutation，但是 J8 應改而未改**——殘留下它們要求的 API／前端應紅面已被正式延後 ⇒ **結構上永遠不會在本延伸紅**（或逼實作者違反殘留決策去造 API）。→ **P1-04**（並支撐 P1-02）

### 5. 修訂引入的新問題／衝突

1. **(G-4a) vs L127 exact**（P1-01）  
2. **Task 9.1 殘留 vs 目標／§N／mutation 02–03／Task 9.4**（P1-02）  
3. **`(6.2)` 義務 vs Task 9.4 baseline 事件數**（P1-03）——義務區塊仍寫「不得改判為事件數」，施工單寫「仍為事件數」；實作者讀任一侧都可自稱合規  
4. **反向 mutation 表 vs 現行測試面**（P1-04）  
5. J1／J2／J5／J7 字面落點與 (5.1) 本輪對讀**一致**；`dedupe` 廣播與 `w=1/n` 未否證；D-001 更正義務本輪未再挖出新互斥

不改就進 Task 9.x：①重凍 golden 時任意成員漂移可被標成「換錨」而假綠；②9A 驗收與殘留／mutation 互斥，Agent 不知該不該寫 API 測試；③baseline 記帳可依 (6.2) 做成複合鍵列數而與物化事件級衝突。

---

## Findings

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

## §1 十一類（摘要）

1. 矛盾：(G-4a)↔L127；Task 9.1 殘留↔目標／mutation；(6.2)↔Task 9.4  
2. 漏項：§N 未登記終端可見殘留；mutation 防誤改測試未具名  
3. 不可測：(G-4a) 允許差異無機械 oracle；02／03 應紅面被延後  
4. quant：換錨成員集漂移可被散文掩蓋（P1-01）  
5. 過度工程：無  
6. OOM：無  
7. Cache：無  
8. API／型別：9A 終端面刻意延後但文件未一致  
9. 測試：反向 mutation 多條現行不紅  
10. Agent 可執行：同檔互斥指示  
11. 短命工：無

## 主動攻擊面（停輪③）

1. 本家 R7 三條 → 字面 CLOSED（9.1 殘留落地缺口重開 R8）  
2. 攻 (G-4a) 可驗證性 → **P1-01**  
3. 攻 Task 9.1 殘留／Phase 9A → **P1-02**  
4. 七條反向 mutation 現行紅面 → **P1-04**  
5. J6 落點遺漏：(6.2) 義務未改 → **P1-03**

## 被當成事實的未驗證假設（§0 彙總）

1. 「commit 訊息逐筆說明 ⇒ 可驗證只允許換錨差異」——被探針否證。  
2. 「寫了具名殘留 ⇒ Phase 9A 目標與 §N／mutation 已一致」——被 L135／§N／02–03 否證。  
3. 「mutation 表有反向列 ⇒ 誤改會紅」——被現行測試面否證（除 04）。  
4. 「(6.2) 與 Task 9.4 已等價」——義務字面仍互斥。

ASSUMPTIONS_VERIFIED: 本家 R7 三條字面 CLOSED（9.1 殘留重開）；obl／fmt rc=0；mutation 實列 26 連續；golden gap1/gap2 purged；api 零 run()；§N 無終端可見殘留；(6.2)↔Task 9.4 對讀；G-4 邊界探針  
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`PYTHONPATH=. venv/bin/python` G-4／api 探針 → `/tmp/grok-splitunify-b9-review-r8/probe_*.txt`；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r8-grok.md --family grok`  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r8-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R8-P1-01,GROK-R8-P1-02,GROK-R8-P1-03,GROK-R8-P1-04
CLOSED:
STATUS: DONE
