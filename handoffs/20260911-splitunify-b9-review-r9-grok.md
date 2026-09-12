# SPLITUNIFY D-002 閉合輪 R9 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R9`  
family: grok  
findings-round: R9  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第九次修訂；sha12 `e3ebec32d870`）  
上游收斂: `handoffs/reconcile/20260911-splitunify-b9-review-r8/synth.md`  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r9/`（交件後清除；保留 `/tmp/claude-501*`）  
本家待閉（敘述用，不入裁決欄）: `GROK-R8-P1-01`～`04`

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: R8 十四條歸八群 → 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r8/synth.md`

fact-verified: `_oracle_membership` docstring 逐字「與被測函式無因果關係」「不 import 投影」，且目前以 `feature_cutoff_ms` 判側；`_manifest` 之 `decision_at_ms` **直接複製** `feature_cutoff_ms` ⇒ 現行 golden 全事件 `decision==cutoff` → `sed -n '112-154p' scripts/freeze_splitunify_golden.py`

fact-verified: SPEC §N 殘留規則權威＝`templates/SPEC_TEMPLATE.md:107-112`（**三種**：`blocked-by`／`user-ruling`／`needs-research`，且必須帶 `為何現在不做:`）；adversarial 範本 `SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md:47-50` 同三值。BRIEF 範本 `BRIEF_REVIEW_TEMPLATE.md:71` 為**四值**（另含 `cost`／`out-of-scope`），對象是 brief 的 `reason_code` 欄，不是 SPEC §N → 對讀三檔

fact-verified: §N 已有 `SU-RESID-9A-UI`（`grep -c`＝3），但該條**無**字面 `為何現在不做:`（MISSING_FIELD）→ 探針

fact-verified: L137 目標仍寫「必須讓**終端使用者**看得到」；L142 已改「API／前端不再列入 9A 完成條件」；L149 仍留「若成本超出…應改為只交付前兩層」→ `sed -n '137,149p'`

fact-verified: `(6.2)` 已改「樣本數＝事件數」；mutation 02／03 已改指 summary／`metadata.split_unify`；§V Task 9.3 已具名檔；obl／fmt rc=0；mutation 表列 26／ID 01–26 連續（`26` 插在 `23` 後，實列仍 26）

fact-verified: §V 全文**無**「零位移」／`decision != cutoff`／G-4d 之 ASSERT 句；mutation 表亦無對應列 → `sed -n '216,226p'`＋表掃描

assumed: (G-4c)「同步改寫 oracle」與 allowlist **等效**  
→ **否證**：構造 `gapX`（decision=950, cutoff=900, train_last=900, test_start=1000）：正確三段式 ⇒ purged；R6 不等式（兩邊同寫）⇒ train；proj==oracle ⇒ G-3b **綠**，成員集錯。見必答 2／P1-01。

assumed: 步驟 0 前置條件窮盡重疊  
→ **部分成立**：正常 `train_last < test_start` 時四點互斥且窮盡（探針）；`train_last >= test_start` 時規則 1＋2 仍可同時命中——屬計畫不變量缺口，本輪未升 P1。

assumed: `SU-RESID-9A-UI` 觸發條件可機械判定  
→ **弱否證**：觸發字面可 grep，但**無人／無腳本**被指名在何時檢查；殘留未入 epic 權威登記處（SPEC_TEMPLATE 要求）。本輪併入 P1-02 格式缺口，不另開「永久沉睡」P1。

assumed: `(6.2)` 與 C6 其餘一致  
→ **本輪未否證**：L92 與 Task 9.4／baseline 敘事已同向。

---

## 必答 1–5

### 1. 本家 R8 finding 是否閉合

| R8 ID | 判定 | 確認方式 |
|---|---|---|
| `GROK-R8-P1-01` | **字面 CLOSED／剩餘洞重開 R9** | (G-4c)(G-4d) 已寫入 §G；「commit 散文當閘」已取代。但兩邊同錯時 G-3b 仍綠，且 (G-4d)③ 未進 §V／mutation ⇒ 以 `GROK-R9-P1-01` 重開 |
| `GROK-R8-P1-02` | **未閉** | §N／mutation 02–03／Task 9.4／L140 已改；**L137 目標句仍要「終端使用者看得到」**與殘留互斥 ⇒ `GROK-R9-P1-04` |
| `GROK-R8-P1-03` | **CLOSED** | L92 已改「樣本數＝事件數」；與 L209 同向 |
| `GROK-R8-P1-04` | **CLOSED（義務面）** | §V 具名檔＋「測試存在前不得宣稱網已閉」；誠實邊界仍在 |

（依 R9 brief：跨輪 ID **不**填入本檔 `CLOSED:` 欄。）

### 2. 攻 (G-4c)

**(G-4c) 只能抓「投影改錯、oracle 沒一起改錯」的不對稱錯誤；不能抓「兩邊被改成同一個錯」。與 allowlist 不等效。**

構造（探針 `/tmp/grok-splitunify-b9-review-r9/probe_g4c.txt`）：

| eid | decision | cutoff | 舊(cutoff)側 | 正確(decision)側 | 兩邊同寫 R6 不等式 |
|---|---|---|---|---|---|
| `gapX` | 950 | 900 | train | **purged** | **train** |
| `bnd1` | 1000 | 900 | train | test | test（此例同錯＝碰巧對） |
| `eq1` | 900 | 900 | train | train | train（(G-4d)② 適用） |

- `gapX`：`decision != cutoff` ⇒ (G-4d)② 零位移**不適用**；proj 與 oracle 皆 `train` ⇒ **G-3b 綠**；正確應為隔離帶 `purged`。
- 「逐行重寫、不 import」只是 docstring **散文**——無機械閘驗 oracle 公式是否等於 Task 9.2b 三段式；同一實作者同一 commit 可把同一段錯公式貼進兩處。
- 現行 fixture 全是 `decision==cutoff`（`_manifest` 複製 cutoff），(G-4d)③ 要求的邊界 fixture **尚未**進 freeze／§V／mutation ⇒ 換錨差異本身現在測不到。
- allowlist（第三份、以正確三段式從 fixture 欄位純算 `allowed_reanchor_diff`，與投影／oracle **雙邊**比對）在 `gapX` 會要求 train→purged；兩邊同錯則實際 diff 為空或錯向，**會紅**。

⇒ **P1-01**

### 3. 攻 K3 的駁回

**`BRIEF_REVIEW_TEMPLATE` 不適用於 SPEC §N。**

| 文件 | 對象 | 殘留理由閉集 |
|---|---|---|
| `templates/SPEC_TEMPLATE.md:107-112` | **SPEC §N** | **三值**：`blocked-by`／`user-ruling`／`needs-research`；且**必須** `為何現在不做:` |
| `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md:47-50` | 審 SPEC 時攻 §N | 同上三值 |
| `templates/BRIEF_REVIEW_TEMPLATE.md:71,171` | **brief** 的 `reason_code`／brief 自身殘留 | **四值**（另 `cost`／`out-of-scope`）；`R-BRIEF-1` 是 brief 殘留實例 |

主委用 BRIEF 四值＋`R-BRIEF-1` 駁「須指名票號」——**引用錯層級**。正確依據是 SPEC_TEMPLATE：`blocked-by:<具體依賴（檔/層/前置票）>`。  
在該定義下，「投影路徑無生產接線」可算 **層／前置依賴**，`blocked-by` **類別本身仍可成立**；但：

1. 駁回文必須改引 SPEC_TEMPLATE，不得再把 BRIEF 四值寫進 §N 條目當依據（L267 現況正是錯引）；  
2. `SU-RESID-9A-UI` **缺**強制欄 `為何現在不做:`（探針 MISSING_FIELD）；  
3. SPEC_TEMPLATE 還要求同步 epic 權威登記處——本殘留目前只活在 D-002 §N。

⇒ **P1-02**

### 4. 攻 K4 的「成本超標時改交付範圍」

**是，又一個自己沒擇的二擇一（同型 J3）。必須現在擇定。**

衝突面（同檔）：

- L148／L218／`M-SU-D2-03`：第三層 `metadata.split_unify` **在本延伸交付與應紅面內**
- L149 末句：「若評估後認為此成本超出…**應改為只交付前兩層**並併入殘留」

實作者讀 L149 可在 Task 9.1 動工時改選兩層，使 `M-SU-D2-03`／§V 之 `ASSERT metadata.split_unify 帶該鍵` 要嘛違殘留、要嘛無碼可紅——與 R7 J3 同型。

**應擇**：鎖定**三層**（producer 回傳 ＋ summary ＋ `metadata.split_unify` 五處同步），**刪除** L149 逃逸句。理由：五處施工面與 `Dict[str, int]` 已寫死、mutation 03 已改指、§V 已 ASSERT——成本評估若要做應在進 R9 前做完，不該留給實作時。若真要兩層，須同批刪 03、改 §V、把第三層併入 `SU-RESID-9A-UI` 並改「本延伸交付」句——那是現在的規格決策，不是實作時決策。

⇒ **P1-03**

### 5. 修訂引入的新問題／衝突

1. **(G-4c) ≠ allowlist**（P1-01）；**(G-4d)③ 只寫在 §G，§V／mutation 未落地**——又一次「義務有、施工／驗收無」  
2. **K3 錯引 BRIEF 範本**＋殘留缺 `為何現在不做:`（P1-02）  
3. **K4 逃逸句 vs 三層交付／mutation 03**（P1-03）  
4. **L137 vs `SU-RESID-9A-UI`**（P1-04）——K2「四處同批改完」漏了目標句  
5. 步驟 0 在正常計畫下成立；`(6.2)`／K6／K7／K8 字面落點本輪對讀一致  
6. D-001 更正義務本輪未再挖出新互斥

不改就進 Task 9.x：①重凍時隔離帶／邊界事件可被兩邊同錯寫進新 golden 且 G-3b 綠；②Agent 不知 §N 理由欄格式以哪份範本為準；③Agent 可合法砍掉第三層而自稱遵 L149；④9A 驗收文案仍寫「使用者看得到」而殘留說看不見。

---

## Findings

## GROK-R9-P1-01

**斷言**: (G-4c)「同步改寫 `_oracle_membership` 使 G-3b 成區分閘」**不能**取代 allowlist——投影與 oracle 被改成**同一錯誤語意**時 G-3b 仍綠；且 (G-4d)③ 要求的 `decision != cutoff` 邊界 fixture／零位移斷言尚未進入 §V 與 mutation。

**碼證**: SPEC L128 (G-4c)、L129 (G-4d)。`freeze_splitunify_golden.py:133-154`（oracle 用 cutoff；docstring 散文紀律）、`:117`（`decision_at_ms`←`feature_cutoff_ms`）。VERIFY 探針：`gapX` decision=950 cutoff=900 train_last=900 test_start=1000 ⇒ 正確 purged、R6 不等式 train、兩邊同寫時 G-3b 綠且 (G-4d)② 不適用。§V L216-226 無零位移／邊界 fixture ASSERT；mutation 01–26 無對應列。RECHECK: 重跑 `/tmp/grok-splitunify-b9-review-r9/probe_g4c.txt` 邏輯；`grep -n '零位移\\|decision != cutoff' docs/SPLITUNIFY_SPEC.D-002.md` 僅命中 §G。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。不改則 Task 9.2b 落地＋重凍時，實作者可把「忘記隔離帶」同時寫進投影與 oracle，G-3b 放行，錯誤成員集成為新 golden。(G-4d) 附帶條件若只留在 §G 散文，實作 checklist 掃 §V／mutation 會漏。**修法**：①保留 G-3b 同步改寫（抓不對稱錯）；②**另加**與投影／oracle 皆獨立的第三份判準——以 Task 9.2b 三段式（含步驟 0）從 fixture 欄位純函式算出每事件期望側，ASSERT 投影側與之全等（此即 allowlist／oracle-of-oracle；可內嵌測試、不必新檔）；③§V 具名 `ASSERT decision==cutoff ⇒ 相對 v8 baseline 零位移`、`ASSERT decision!=cutoff 邊界事件側別＝三段式期望`；④mutation 至少一條「只改投影、不改 oracle ⇒ G-3b 紅」＋一條「投影與 oracle 同寫成 R6 不等式 ⇒ 第三份判準紅」。**可行性**：三段式所需 `train_last_ms`／`test_start_ms`／`decision_at_ms`／`feature_cutoff_ms` 皆在 fixture；探針已展示 `gapX` 可區分；現成 G-3b 比對骨架在 `freeze_splitunify_golden.py:346-352` 附近，第三份比對可並列。

## GROK-R9-P1-02

**斷言**: K3 駁回所引 `BRIEF_REVIEW_TEMPLATE` **不適用於 SPEC §N**；§N 權威為 `SPEC_TEMPLATE.md` 之三值＋強制欄 `為何現在不做:`——`SU-RESID-9A-UI` 缺該欄，且條目正文仍錯引 BRIEF 四值當依據。

**碼證**: `templates/SPEC_TEMPLATE.md:107-112`「值**只允許三種**…每條殘留**必須**帶 `為何現在不做:`」；`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md:47-50` 審 §N 同三值；`templates/BRIEF_REVIEW_TEMPLATE.md:71` 四值＋`:171` `R-BRIEF-1` 屬 **brief** 殘留。SPEC L267 `SU-RESID-9A-UI`：有觸發條件與 `blocked-by` 字樣，但 `grep`／探針確認**無** `為何現在不做:`；同段括號「類別依據：BRIEF_REVIEW_TEMPLATE…四值」為錯引。RECHECK: `sed -n '107,112p' templates/SPEC_TEMPLATE.md`；`sed -n '267p' docs/SPLITUNIFY_SPEC.D-002.md | grep -c '為何現在不做'` 期望 0。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870;templates/SPEC_TEMPLATE.md#0b2f68f0c38a;templates/BRIEF_REVIEW_TEMPLATE.md#82dfcbd10f3e;templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#36b518be40fa

[BLOCKING] 信心度=High。類別 `blocked-by` 在 SPEC_TEMPLATE「`blocked-by:<具體依賴（檔/層/前置票）>`」下**仍可**形容「投影層無生產接線」——問題不是類別必錯，而是**依據文件引錯＋強制欄缺失**，後續審核會繼續用錯閉集（甚至把 `cost`／`out-of-scope` 寫進 SPEC §N）。**修法**：①L267 刪 BRIEF 四值依據，改引 `SPEC_TEMPLATE.md` §N；②補 `為何現在不做: blocked-by:投影路徑無 EventSamplePipeline.run 生產接線（api/ 呼叫點=0）`；③若 epic 有權威殘留登記處則同步 pointer（無則於 §N 明寫「登記處＝本 SPEC §N」避免假同步）。**可行性**：純文件同步；零呼叫點事實已多次 grep 實證。

## GROK-R9-P1-03

**斷言**: Task 9.1 L149「若成本超出 9A 定位，應改為只交付前兩層並併入殘留」是**未擇定的二擇一**，與同 Task 已寫死的三層交付、`M-SU-D2-03`、§V `ASSERT metadata.split_unify` 互斥——實作時可合法砍第三層。

**碼證**: L148 本延伸交付含 `metadata.split_unify`；L149 逃逸句；L218 `ASSERT metadata.split_unify 帶該鍵`；mutation L233 `M-SU-D2-03`「summary 帶了但**不傳入** `metadata.split_unify`」。契約現恰五鍵（`split_unify.json` → `n_test,split_authority,boundary_hash,per_symbol_counts,reason`）；加鍵須改契約＋exact-key 測試（L149 前半已承認）。RECHECK: `sed -n '148,149p;218p;233p' docs/SPLITUNIFY_SPEC.D-002.md`；`python3 -c "import json;print(json.load(open('momentum/Analysis/contracts/split_unify.json'))['split_unify_keys'])"`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870;momentum/Analysis/contracts/split_unify.json#5aaf5f8efa15

[BLOCKING] 信心度=High。與 R7 J3 同型：規格把決策推給實作者。**修法（擇 A）**：刪除 L149 逃逸句，鎖定三層＋五處同步為 9A 完成條件（與現行 mutation／§V 一致）。**若改擇 B**：同批刪 `M-SU-D2-03`、改 §V、改 L148「本延伸交付」為兩層、第三層併入 `SU-RESID-9A-UI`——不得留逃逸句。**可行性**：擇 A 是刪一句；五處清單與型別已寫好，無未決工程問題需要「實作時再估成本」。

## GROK-R9-P1-04

**斷言**: K2 宣稱「目標句已改」未完成——Task 9.1 L137 仍要求「必須讓**終端使用者**看得到」，與 L142／`SU-RESID-9A-UI`「終端可見性不在 9A 完成條件／使用者仍然看不見」正面衝突。

**碼證**: L137 逐字「且必須讓**終端使用者**看得到」；L142「API 與前端隨 §N 殘留延後，**不再**列入 9A 完成條件」；L267 誠實邊界「靜默丟棄對**終端使用者仍然看不見**」。沿革 L283 只記「`:140` 標題句刪去…」，未提 L137。RECHECK: `sed -n '137,142p;267p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870

[BLOCKING] 信心度=High。這是 R8 `GROK-R8-P1-02` 的**殘留未閉**（同型「改一處漏一處」）。驗收若讀目標句會要求終端面；讀殘留又禁止做終端面。**修法**：改 L137 為「先消除靜默丟棄之**producer 層**誠實性缺陷（終端可見性見 §N `SU-RESID-9A-UI`）」；全文再 grep「終端使用者看得到／必須讓…看得到」清殘句。**可行性**：一字級目標句修訂；與已落地之 L142／§N／mutation 02–03 同向。

---

## §1 十一類（摘要）

1. 矛盾：L137↔殘留；L149↔三層／03；(G-4c) 宣稱等效↔探針  
2. 漏項：(G-4d)③ 未進 §V／mutation；§N 缺 `為何現在不做:`  
3. 不可測：兩邊同錯無第三份判準  
4. quant：隔離帶／邊界成員集可被同錯凍結  
5. 過度工程：無（反而是該做的第三份判準被省掉）  
6. OOM：無  
7. Cache：無  
8. API／型別：第三層 exact-key 成本已承認但範圍未鎖  
9. 測試：G-4d 邊界／零位移無 mutation  
10. Agent 可執行：逃逸句＋錯範本依據  
11. 短命工：無

## 主動攻擊面（停輪③）

1. 本家 R8 四條 → 03／04 閉；01 字面閉剩洞；02 未閉  
2. 攻 (G-4c) 等效性 → **P1-01**  
3. 攻 K3 駁回依據 → **P1-02**  
4. 攻 K4 二擇一 → **P1-03**  
5. K1–K8 落點衝突 → L137／(G-4d)③／L149（P1-04／01／03）

## 被當成事實的未驗證假設（§0 彙總）

1. 「同步改寫 oracle ⇒ 等同 allowlist」——被 `gapX` 兩邊同錯否證。  
2. 「BRIEF 四值／R-BRIEF-1 可當 SPEC §N 依據」——被 SPEC_TEMPLATE 三值＋強制欄否證。  
3. 「成本超標時再改交付範圍」——與已寫死的三層／mutation 互斥，屬未決二擇一。  
4. 「K2 目標句已改完」——L137 仍在。

ASSUMPTIONS_VERIFIED: R8 四條對讀；obl／fmt rc=0；mutation 實列 26；G-4c 兩邊同錯探針；fixture decision==cutoff；SPEC_TEMPLATE vs BRIEF 閉集；SU-RESID 缺為何現在不做；L137／L149 原文；§V 無 G-4d ASSERT；split_unify 五鍵；步驟 0 正常互斥  
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`venv/bin/python` G-4c／step0／fixture 探針 → `/tmp/grok-splitunify-b9-review-r9/probe_*.txt`；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r9-grok.md --family grok`  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r9-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R9-P1-01,GROK-R9-P1-02,GROK-R9-P1-03,GROK-R9-P1-04
CLOSED:
STATUS: DONE
