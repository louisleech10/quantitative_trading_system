# SPLITUNIFY b9 — review-r15（R14 U1–U3 閉合再驗證 ＋ D-002 v15 重簽）— grok

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R15`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R15-BRIEF.md`  
**findings-round**: R15  
**brief-kind**: review  
**審查標的**: `git show 0de1a17f` 之 SPEC／TODO diff ＋ current block（C5-24／25／27／28／29、M-35..40、Task 9.2a／9.3／9.4）  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（僅允許 append 戳記）。

---

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: body sha256 → `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` ＝ `c674086e5f66985ed4bb3107483803425eaec27731acc49f173ed89efe4b8bf0`（與 brief 一致）。

fact-verified: mutation 40 列、01–40 連續無缺 → `grep -cE '^\| .M-SU-D2-[0-9]+.'`＝40；逐號 missing=[]。

fact-verified: §C-9 認領 40/40 → `awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md | grep -oE 'M-SU-D2-[0-9]{2}' | sort -u | wc -l`＝40。

fact-verified: register 29 列 → `grep -cE '^\| .C5-[0-9]+.'`＝29。

fact-verified: `共 **40** 條` 恰一行（mutation 目錄標題）。

fact-verified: `doc_format_precheck` 對 SPEC／TODO 皆 rc=0。

fact-verified: R14→v15 五列修補落地 → C5-24→`M-05`／`M-37`；C5-25→`M-38`；C5-27→`M-39`；C5-29→`M-40`；C5-28 之 `—` 具名 `blocked-by`；M-35／36 應紅欄含欄位存在斷言＋軟包禁令＋多 TF；Task 9.3 receipt 含改前分類對證＋path:line 存在性＋COMMIT＝audit round-start HEAD。

assumed（brief 攻 #1）: R14 窮舉已清乾淨 mutation **對應**；「應紅之測試」另維是否有洞 → **對應維成立**；應紅維見必答 (2)——預先未寫成之具名測試屬 Task 未開工可接受狀態，非錯配。

assumed（brief 攻 #2）: Task 9.3 receipt 加兩條後已無可行繞過 → **否證**。見 `GROK-R15-P2-01`（照抄 SPEC 第三欄＋全列同指一真實 `path:line` 仍過內容閘）。

---

## 必答

### (1a)(1b) 重跑本家 R14 反例

| finding | 判定 | 重跑命令與觀測 |
|---|---|---|
| `GROK-R14-P1-01` | **CLOSED** | `sed -n '124p' docs/SPLITUNIFY_SPEC.D-002.md` → `C5-29`…`M-SU-D2-40`；`sed -n '317p'` → M-40 WHAT＝`:372` 略過去重。不再指 `M-06`。 |
| `GROK-R14-P1-02` | **CLOSED** | `sed -n '120p'` → `C5-25`…`M-SU-D2-38`；`sed -n '315p'` → M-38 WHAT＝餵入未 `drop_duplicates`。不再指 `M-19`。 |
| `GROK-R14-P2-03` | **CLOSED** | `sed -n '312,313p'`＋Task 9.2a L546–549 → 明定先欄位存在斷言、軟包亦 FAIL、多 TF fixture。實跑：無欄＋先 `assert col in columns` ⇒ AssertionError（刪欄會紅）；對照軟 guard `if col in columns` 仍可綠——故義務已寫進應紅欄／TODO，洞已標死。 |
| `GROK-R14-P2-04` | **CLOSED**（原構造） | 原三構造：①全填同值 → 改前分類須＝SPEC 第三欄已殺（甲列抄成乙會 FAIL）；②`nowhere:0` → path 存在性閘殺（本輪 sim 29/29 fail）；③任意 COMMIT → 須＝audit round-start HEAD。殘餘新洞另立 `GROK-R15-P2-01`，不把 P2-04 留 STILL-OPEN。 |

Brief 表 (A) 他家系／撞題項落地核對（非本家 CLOSED 欄）：`CODEX-R14-P1-01`／`03`、`COMPOSER-R14-P2-01`／`02` 與上列同 diff 字面；`CODEX-R14-P2-04` 處置見必答 (4)。

### (2a)(2b) 「應紅之測試」維

**(2a)** 在「**指向錯誤／存在但不會因該破壞而紅**」意義下：**零條**存量錯配。

預先**尚未寫成**之具名測試（Task 未開工，**可接受**，非 finding）：

| mutation | 應紅具名 | 現況 | 建立責任 |
|---|---|---|---|
| `M-35` | `test_assignments_composite_key_unique` | `grep -rn 'def test_assignments_composite_key_unique' tests/` → NONE | Task 9.2a |
| `M-36` | `test_purged_composite_key_unique` | NONE | Task 9.2a |
| `M-37` | `test_pattern_bridge.py` 具名「唯一側去重＋raise」 | 檔在、無該具名用例 | Task 9.3 |
| `M-38` | `test_gap3_conditional_ic.py` 具名「餵入去重後雜湊穩定」 | 檔在、無該具名用例 | Task 9.3 |
| `M-39` | `test_tier_min_test_events_counts_unique_event_ids` | NONE | Task 9.4 |
| `M-40` | `test_tables.py` 具名「assignments 消費去重」 | 檔在、無該具名用例 | Task 9.3 |
| `M-11` | `eventExportByEventId.test.tsx` | 檔 MISSING（同目錄另有四支 eventExport*） | Task 9.3 明文「須新建」 |

判定可接受：§V／Task 9.3 已寫「在上表測試實際存在之前，不得宣稱 mutation 網已閉」；建立責任已掛 Task，非「mutation 對應錯了」。

**(2b)** 核對命令（本輪實跑）：

```bash
grep -cE '^\| .M-SU-D2-[0-9]+.' docs/SPLITUNIFY_SPEC.D-002.md   # → 40
for n in test_assignments_composite_key_unique test_purged_composite_key_unique \
         test_tier_min_test_events_counts_unique_event_ids; do
  grep -rn "def $n" tests/ || echo NONE
done
ls frontend/src/app/search/eventExportByEventId.test.tsx  # → missing
# C5-24..29 mutation 欄 vs M-05/37/38/39/40/— ：sed -n '119,124p;312,317p'
```

### (3a)(3b) Task 9.3 receipt 還能繞過嗎？

**(3a) 能。** 見 `GROK-R15-P2-01`。

試過構造（workdir `/tmp/grok-r15-work`）：

1. **照抄 SPEC 第三欄作改前分類**＋**全 29 列碼證＝`docs/SPLITUNIFY_SPEC.D-002.md:1`**＋改後＝改前 → ID set `diff` PASS；改前分類對證 PASS；path:line 存在性 PASS（`content gate fails: NONE — BYPASS SUCCEEDS`；`distinct anchors: 1`）。
2. 對照：同結構但碼證 `nowhere:0` → 29 列皆 FAIL（證明 v15 存在性閘有效，只堵占位、不堵「真檔假錨」）。
3. COMMIT＝`deadbeef…` 仍會被 audit round-start 比對擋（本洞不依賴假 COMMIT）。

**(3b) 最小加強字面**（可直接貼進 Task 9.3 驗證第 4 點）：

> 碼證之 `path` 須為該 `C5-NN` 在 register 第 2 欄（消費面）所具名之 repo 相對路徑（允許僅差 `:line`）；`docs/`／`handoffs/` 不得作為碼證 path。另：全份 receipt 之 distinct `path` 數須 ≥ 8（或等於「第 2 欄具名之相異檔數」之較小者）。任一條違反即 FAIL。

### (4a)(4b) `CODEX-R14-P2-04` 處置

**(4a) 可接受。** 量測進行中由被量測者單方改判準不正當；同時報現行集合與加強集合兩數字保留可比較性，且不放寬達標門檻（兩判準下 r13／r14 皆 ≤0.30）。

**(4b)** 若日後要改判準：權在**使用者**（或量測結束後由主委提案、三家 stamp 的治理變更），不得在 DOCROT 量測窗內由委員／主委單方改 SSOT。本輪不改＝正確。

### (5a)(5b) 戳記

**(5a) `APPROVED`**（body sha `c674086e…`）。

**(5b)** Task 9.1 動工最可能先紅：`M-SU-D2-01`／`02`（summary／producer `discarded` 值相等）、`test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer`；以及 §N `SU-RESID-2` 要求「三家戳記通過後、Task 9.1 動工前」同步 TODO 狀態——漏同步會在治理面而非 pytest 面爆。`M-03`／metadata 層隨 `SU-RESID-9A-UI` 延後，**不應**在 9.1 宣稱已閉。

### (6a)(6b) 可否領 impl token 進 Task 9.1

**(6a) 本家同意領**——前提是三家對 v15 皆 APPROVED 且 `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0，並先做 §N 之 `SU-RESID-2` TODO 同步。

**(6b)** 本輪檢查：R14 本家四條 CLOSED；五列 register 修補＋M-35／36／receipt 字面落地；fact 計數全綠；殘餘 P2 屬 Task 9.3 閘、**不擋** 9.1。最小閉合集合若要坚持零 P2 再開工 9.3：貼上 (3b) 字面即可（非 9.1 前置）。

**收斂判準（非感覺）**：以「同缺陷類在已宣告窮舉子空間的復發次數」計——register×mutation **對應**類在 R14 窮舉後本輪 **0 復發**；閘偏鬆類本輪 **1 條殘餘**（R14 U3 同族的下一層）。⇒ **對應維已入窮舉遞減報酬**；閘收緊維仍可能再 0–1 輪，但不得再把「對應錯配」當未窮舉重跑整表。

---

## 攻擊面補答

| 面向 | 結論 |
|---|---|
| 應紅之測試維 | 無「錯指／存在但不紅」；未寫成者掛 Task 可接受 |
| M-37／38／40 測試不存在 | 可接受（Task 9.3 義務＋§V 禁提前宣稱網閉） |
| receipt 閘 | 仍可「照抄＋同錨」繞過 → P2-01 |
| C5-28／`SU-RESID-9A-UI` | `—`＋`blocked-by` 成立；TODO:816 recheck＝`grep -rn "\.run(" api --include='*.py'` 可執行 |
| DOCROT 雙數字 | 可接受 |

## §1 必查（11 類；範圍＝v15 diff／current block）

1. 矛盾/互斥：無（五列修補與 M-37..40 一致）  
2. 漏項：無（C5-28 刻意無 mutation 已具名）  
3. 不可測驗收：Task 9.3 receipt 殘餘繞過（P2）  
4. 可疑 quant：無  
5. 過度工程：無  
6. OOM/並行：無  
7. Cache：無  
8. API/型別：無  
9. 測試品質：預先未寫成之應紅測試可接受；receipt 語意閘仍可假完成  
10. Agent 可執行性：9.1 可領（戳記齊＋SU-RESID-2 同步後）  
11. 必要性/短命工：無  

## 被當成事實的未驗證假設（§0）

1. 「receipt 兩條內容對證後已無繞過」——否證（照抄＋同錨仍過）。  
2. 「應紅欄指向未存在測試＝缺陷」——不成立（Task 掛鉤＋§V 禁提前閉網）。

---

## GROK-R15-P2-01

**斷言**: Task 9.3 register-rescan receipt 在 v15 加「改前分類＝SPEC 第三欄」與「path:line 須存在」後，仍可用「逐列照抄 SPEC 分類＋全列碼證指向同一真實存在行（例如 `docs/SPLITUNIFY_SPEC.D-002.md:1`）」通過檔案級內容閘，而無需真實重掃各消費面。

**碼證**: 實跑構造 `/tmp/grok-r15-work/bypass-same-anchor.txt`：29 列 `C5-NN <SPEC第三欄> -> <同值> docs/SPLITUNIFY_SPEC.D-002.md:1` → ID set 與 SPEC register `diff` rc=0；改前分類對證 0 fail；path 存在且 line≤檔長 0 fail；`distinct anchors=1`。對照同檔改 `nowhere:0` → 29 fail（證存在性閘有效）。閘字面落點 `docs/SPLITUNIFY_TODO.md:647-651`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#23f19deb2784

[MAJOR] 信心度=High。修法＝必答 (3b) 最小字面（碼證 path 須落在該 C5 第 2 欄具名檔；禁 `docs/`／`handoffs/`；distinct path 下限）。可行性：register 第 2 欄已具名消費路徑（如 `pattern_bridge`／`tables.py:372`），機械比對只需從該欄抽 path token，無需新架構。不阻擋 Task 9.1；阻擋的是 Task 9.3「重掃已做」之語意驗收。非空殼。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R14-P1-01,GROK-R14-P1-02,GROK-R14-P2-03,GROK-R14-P2-04

ASSUMPTIONS_VERIFIED: body sha `c674086e…`；mutation 40 連續；§C-9 認領 40；register 29；doc_format 雙綠；C5-24..29／M-35..40 字面落地；M-35 欄位存在斷言探針；receipt 照抄＋同錨 bypass 與 nowhere:0 對照；具名測試 def 探針；SU-RESID-9A-UI recheck 字面存在
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `c674086e…`；`bash scripts/doc_format_precheck.sh` SPEC／TODO → rc=0；receipt sim bypass／nowhere 對照；`grep -rn 'def test_assignments_composite_key_unique' tests/` → NONE（及 M-36／M-39 同）；pandas 欄位存在斷言探針
FAILURES_SEEN: none
SCOPE_CHANGES: none（未改 SPEC／TODO 正文；僅 append APPROVED 戳記）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r15-grok.md

STATUS: DONE
