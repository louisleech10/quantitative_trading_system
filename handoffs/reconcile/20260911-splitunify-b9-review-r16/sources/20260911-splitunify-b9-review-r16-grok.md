# SPLITUNIFY b9 — review-r16（R15 V1–V5 閉合再驗證 ＋ D-002 v16 重簽）— grok

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R16`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R16-BRIEF.md`  
**findings-round**: R16  
**brief-kind**: review  
**審查標的**: `git show 79b66dd1` 之 SPEC／TODO diff ＋ current block（`M-SU-D2-38`／`39`／`40`；Task 9.3／9.4）  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（僅允許 append 戳記）。

---

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: body sha256 → `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` ＝ `8607f2b770fb39f967c7c75686a90f4c1bc39a7d1536cc70bca1909e838021a0`（與 brief 一致）。

fact-verified: mutation 40 列、01–40 連續無缺 → `grep -cE '^\| .M-SU-D2-[0-9]+.'`＝40；missing=[]。

fact-verified: register 29 列 → `grep -cE '^\| .C5-[0-9]+.'`＝29。

fact-verified: `doc_format_precheck` 對 SPEC／TODO 皆 rc=0。

fact-verified: `M-SU-D2-38` 可達 → 實跑 `event_context_from_windows` 餵 unique vs 重複 `event_id` ⇒ `event_manifest_hash` **DRIFT=True**（`/tmp/grok-r16-work/hash_and_keyed.txt`）。

fact-verified: `M-SU-D2-40` 描述與 pandas 相符 → `tables.py:372` 現為 raw `set_index("event_id")["symbol"].reindex(idx)`（尚無顯式 reducer；mutation 為未來修補之逆）。

fact-verified: Task 9.3 已含 v16 keyed 碼證對證字面（`docs/SPLITUNIFY_TODO.md:652-656`）；Task 9.4 已含 `per_symbol_n`／`per_symbol_test_n` 計數斷言（`:704-706`）。

assumed（brief 攻 #1）: keyed 對證已無可行繞過 → **否證見 `GROK-R16-P2-01`**（register 多列無「落點檔」可對）。

assumed（brief 攻 #2）: `C5-25` 與 `M-SU-D2-38` 語意一致 → **部分否證見 `GROK-R16-P2-02`**（caller vs 函式入口可能是兩行碼）。

---

## 必答

### (1a)(1b) 重跑本家 R15 反例

| finding | 判定 | 重跑命令與觀測 |
|---|---|---|
| `GROK-R15-P2-01` | **CLOSED** | 原構造＝「照抄分類＋全列碼證＝同一真實行（如 `docs/SPLITUNIFY_SPEC.D-002.md:1`）」。v16 於 `docs/SPLITUNIFY_TODO.md:652-656` 加 **逐列 keyed 對證落點檔**。對有明確檔 token 之列，同錨必因 path≠register 落點而 FAIL（本輪計 23/29 列具模組或檔 token ⇒ 同 doc 錨被殺）。殘餘「無落點檔可對」另立 `GROK-R16-P2-01`，不把 P2-01 留 STILL-OPEN。 |

Brief 表 (A) 他家項落地核對（非本家 CLOSED 欄）：`CODEX-R15-P1-01`→keyed 字面；`P1-02`→M-38 改寫可達＋直接呼叫測試義務；`P1-03`→M-39／Task 9.4 計數斷言；`P1-04`→M-40 改 reducer 逆＋成對測試；`COMPOSER-R15-P2-01` 併入 keyed。

### (2a)(2b) register 落點不足以支撐 keyed 對證

**(2a)** 以「第 2 欄抽不出可機械比對的檔路徑（無 repo-relative／無 `*.py` 檔名；或僅模組名且無行號／無 map 契約）」為準，**不足列**：

| 類 | 列 |
|---|---|
| `NO_PATH_TOKEN`（契約／表名，無檔） | `C5-01`、`C5-02`、`C5-22` |
| `MODULE_ONLY_NO_LINE`（模組或函數名，無行號） | `C5-03`、`C5-07`、`C5-10`、`C5-11`、`C5-12`、`C5-17`、`C5-20`、`C5-25` |
| `MODULE_PLUS_LINE_NO_REPO_PATH`（有 `:line` 但無 repo path；需隱式 map） | `C5-04`、`C5-05`、`C5-06`、`C5-08`、`C5-09`、`C5-24` |

共 **17** 列。另 `C5-13`／`C5-27` 為同檔多點（行號集合 OR 即可），**不**列不足，但閘實作須認多行號。

**(2b)** 最小修補——**放寬為「檔集合包含」＋固定模組 map**（可直接貼進 Task 9.3 驗證第 4 點 keyed 段，取代「須與落點檔相同」之過嚴字面）：

> keyed 對證改為「檔集合包含」：自該 `C5-NN` register 第 2 欄抽取檔 token（`momentum|api|frontend|tests/...`、裸 `*.py`、以及模組名經固定 map `momentum/Analysis/event_samples/<mod>.py`；前端／golden 列用欄內已寫之路徑）。receipt 之 path 正規化後須 **∈** 該集合；行號若該列有列舉／範圍則須命中其一，若該列無行號則只驗檔 ∈ 集合。若抽取結果為**空集**（`C5-01`／`02`／`22`），則改對證該列 Task 欄對應消費面之測試檔所屬模組路徑（由 Task 9.3／9.4／9.5 表推得），**不得**用 `docs/`／`handoffs/`。任一列不符即 FAIL。

### (3a)(3b) `M-SU-D2-38` 破壞點 vs `C5-25` 施工點

**(3a) 不一定同一行。**  
- 破壞／應紅測試（M-38）：直接呼叫 `event_context_from_windows`；去重須在函式內 `rows` 組裝前（現 `ic_feed.py:56` 一帶），否則含重複 `event_id` 之直接呼叫仍漂移。  
- 若「餵入端」解讀為 caller：`pipeline.py:407` 傳 `prepared.windows`——**另一檔另一行**。只在 caller 去重 ⇒ 具名直接呼叫測試永遠紅、與 M-38 破壞點錯位。

**(3b)** 正確 seam＝函式入口；可直接貼：

> `C5-25` 落點改寫為：`momentum/Analysis/event_samples/ic_feed.py` 之 `event_context_from_windows` **函式入口**（`rows = sorted(...)` 之前）按 `event_id` 去重；**不得**只在 `pipeline.event_context_for_analysis`（`pipeline.py:407`）caller 去重。Task 9.3 `ic_feed` 列同步此字面。

### (4a)(4b) 「應紅之測試已存在但不會因該破壞而紅」

**(4a) 零條**（current block 之 M-38／39／40 所具名應紅測試皆尚未寫成；既有鄰近測試不在「應紅之測試」集合內，故不構成「已存在但不紅」錯配）。

**(4b)** 核對命令（本輪實跑）：

```bash
grep -rn 'def test_tier_min_test_events_counts_unique_event_ids' tests/   # → NONE
grep -rn 'def test_assignments_composite_key_unique\|def test_purged_composite_key_unique' tests/  # → NONE
grep -n 'event_context_from_windows' tests/momentum/event_samples/test_gap3_conditional_ic.py  # → 無直接呼叫
grep -n 'drop_duplicates\|duplicate.*symbol\|fail-closed' tests/momentum/event_samples/test_tables.py  # → 無 M-40 成對用例
# mutation 40 連續：
venv/bin/python -c '...'  # missing=[] count=40
```

### (5a)(5b) 停輪判準歸類（必答）

**(5a)** 本輪 findings 屬 **「P2 級字面」**（閘可執行性殘餘＋施工點字面歧義）。**不是**「register 錯配」（mutation 欄 ID 指錯）也**不是**「條數不一致」（仍 40／01–40 連續）。

**(5b)** 依 r15 已定判準：**進 `Task 9.1` 實作**；本輪兩條 P2 於 `Task 9.3` 驗收時補洞（貼 (2b)(3b) 字面即可）。

### (6a)(6b) 戳記

**(6a) `APPROVED`**（body sha `8607f2b770fb…`）。

**(6b)** N/A（未 REJECTED）。阻擋進 impl token 的剩餘條件＝三家對同一 body APPROVED 且 `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0（本家已 append；他家／機械閘由主委收斂）。

---

## 攻擊面補答

| 面向 | 結論 |
|---|---|
| r15 修補後新不可達／不一致 | M-38／40 可達／描述正確（實跑）；M-39 字面已補計數；keyed 引入「無落點檔」新洞 → P2-01 |
| keyed 碼證 | 同錨 bypass 對有 token 列已死；17 列不足 → P2-01 |
| M-38 施工 vs 破壞 | 可能兩行（caller vs 函式）→ P2-02 |
| 應紅已存在但不紅 | 零條（命令見 4b） |
| 停輪判準 | **P2 級字面 → 進 Task 9.1** |

## §1 必查（11 類；範圍＝v16 diff／current block）

1. 矛盾/互斥：C5-25「餵入端」vs M-38 直接呼叫義務（P2-02）  
2. 漏項：keyed 前提「register 已有 path:line」對 17 列不成立（P2-01）  
3. 不可測驗收：同上，Task 9.3 receipt 機械閘對空落點列無定義  
4. 可疑 quant：無  
5. 過度工程：無  
6. OOM/並行：無  
7. Cache：無  
8. API/型別：無  
9. 測試品質：具名應紅測試未寫成＝Task 未開工可接受；無「已存在但不紅」  
10. Agent 可執行性：P2-02 若只改 caller 會與測試義務衝突——已給字面釘死函式入口  
11. 必要性/短命工：無  

## 被當成事實的未驗證假設（§0）

1. 「register 本來就逐列寫了落點 path:line」——**否證**（17 列不足；TODO:656 理由句過滿）。  
2. 「C5-25 餵入端＝M-38 函式內去重」——**未釘死**（caller 亦可讀成餵入端）。

---

## GROK-R16-P2-01

**斷言**: Task 9.3 v16 keyed 碼證對證假設「register 同列已載落點檔」，但 `C5-01`／`02`／`03`／`04`–`12`／`17`／`20`／`22`／`24`／`25` 等共 17 列第 2 欄無 repo-relative 檔路徑（或僅模組名），機械「path 相同」對證對這些列無定義或必靠未成文的模組 map。

**碼證**: 分類探針（本輪）：`NO_PATH_TOKEN`＝C5-01,02,22；`MODULE_ONLY_NO_LINE`＝C5-03,07,10,11,12,17,20,25；`MODULE_PLUS_LINE_NO_REPO_PATH`＝C5-04,05,06,08,09,24。閘字面 `docs/SPLITUNIFY_TODO.md:652-656`。對照：具檔／模組 token 之 23 列上，全填 `docs/SPLITUNIFY_SPEC.D-002.md:1` 會被 keyed 殺掉（原 GROK-R15-P2-01 構造已閉）。

**來源摘要**: docs/SPLITUNIFY_TODO.md#33911fd6b944

[MAJOR] 信心度=High。doc-literal-only（閘前提）。修法＝必答 (2b)「檔集合包含＋固定 map＋空集回退消費面測試路徑」。可行性：map 對 `event_samples/<mod>.py` 九個消費模組已唯一；空集列僅三個契約名。不擋 Task 9.1；擋的是 Task 9.3 receipt 語意驗收之可執行性。非空殼。

---

## GROK-R16-P2-02

**斷言**: `C5-25` 寫「`ic_feed` survivor 餵入端」去重，而 `M-SU-D2-38`／Task 9.3 要求直接呼叫 `event_context_from_windows` 驗不變性——若實作只在 `pipeline.py:407` caller 去重，則破壞點（函式內 `rows`）與施工點不是同一行，具名測試與 register 語意分裂。

**碼證**: `momentum/Analysis/event_samples/ic_feed.py:56-65` 現無去重、重複輸入雜湊漂移（實跑 DRIFT=True）；caller `momentum/Analysis/event_samples/pipeline.py:406-408` 直接傳 `prepared.windows`。register `C5-25` 落點仍無 `path:line`（`docs/SPLITUNIFY_SPEC.D-002.md` register 列）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#8607f2b770fb

[MAJOR] 信心度=High。修法＝必答 (3b)（釘死函式入口去重、禁只改 caller）。可行性：單函式入口一處 `drop_duplicates`／dict 保序即可同時滿足直接呼叫測試與 caller 路徑。不擋 Task 9.1；屬 Task 9.3 施工說明。非空殼。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R15-P2-01

ASSUMPTIONS_VERIFIED: body sha `8607f2b7…`；mutation 40 連續；register 29；doc_format 雙綠；M-38 hash DRIFT；tables.py:372 raw reindex；Task 9.3 keyed／Task 9.4 計數字面落地；keyed 不足 17 列分類；同 doc 錨對有 token 列可殺；具名應紅 def＝NONE
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `8607f2b7…`；`bash scripts/doc_format_precheck.sh` SPEC／TODO → rc=0；`event_context_from_windows` unique/dup hash probe → DRIFT=True；register 落點分類探針 → 17 insuff；`grep -rn 'def test_tier_min_test_events_counts_unique_event_ids' tests/` → NONE
FAILURES_SEEN: hash probe 初缺 `horizon_bars` → KeyError，補 LD 後通過
SCOPE_CHANGES: none（未改 SPEC／TODO 正文；僅 append APPROVED 戳記）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r16-grok.md

STATUS: DONE
