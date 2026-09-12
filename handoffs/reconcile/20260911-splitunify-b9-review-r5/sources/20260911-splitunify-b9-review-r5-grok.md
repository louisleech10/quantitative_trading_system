# SPLITUNIFY D-002 閉合輪 R5 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R5`  
family: grok  
findings-round: R5  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第五次修訂；full sha12 `51f66eb84f8e`）  
上游收斂: `handoffs/reconcile/20260911-splitunify-b9-review-r4/synth.md`  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r5/`（交件後清除；保留 `/tmp/claude-501*`）  
本家待閉: `GROK-R4-P1-01`、`GROK-R4-P1-02`、`GROK-R4-P1-03`、`GROK-R4-P1-04`

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: R4 八條歸五群、7 採納 1 駁回 → 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r4/synth.md`；本家四條皆在「採納」列（G1–G4）

fact-verified: 第五次修訂已寫入 Task 9.2 之 `723-732`／`711-715`、新增 `Task 9.2b`、§V 端到端全量 ASSERT、`(5.2)`「落地後契約」、`M-SU-D2-21`／`22` → 本輪逐字讀 SPEC＋`obligation_block_check`／`doc_format_precheck` 皆 rc=0

fact-verified: `pipeline.py:723-732` 仍為四參數 `given` 長度閘；`:747` 仍 `str(selected_timeframe)` → `sed -n '711,748p'`

fact-verified: `split_projection.py` 全檔 `decision_at_ms` 命中數＝0；`:530-553` 仍 `cutoff = int(rec["feature_cutoff_ms"])` → `grep -c`／`sed`

fact-verified: `build_event_keys` 於全量多 TF 時 `merge(..., validate="1:1")` 會 `MergeError`；即使改 `1:m`，輸出 `timeframe` 仍來自 `event_level`（trigger TF），不含 `per_tf.timeframe` → 探針 `probe_summary.txt`

fact-verified: mutation 表實列 **22** 條（`M-SU-D2-01`…`22`），正文與沿革宣稱「共 **23** 條」；`M-SU-D2-23` 不存在 → `awk` 計數

fact-verified: `manifest.table` 含 `decision_at_ms`（多 TF 探針）→ `probe_multitf_membership.txt`

assumed: `Task 9.2`＋`9.2a`＋`9.2b` 三者到位後，生產路徑不再丟列  
→ **否證**：三者即使照字面做完，`build_event_keys` 的 `validate="1:1"` merge（L291-293）仍會在全量多 TF 時先炸掉；且 `(5.2)` 把 merge 改判準「見 Task 9.2a」，但 Task 9.2a **正文零字**提及該 merge。見必答 2／P1-01。

assumed: `Task 9.2b` 之「以 `decision_at_ms` 每事件定側並廣播」不會與答案窗 purge 衝突  
→ **部分成立**：答案窗由「逐列 `in_train`」改「事件側」後，原「cutoff 落 train ⇒ 誤 purge、decision 其實在 test」的假 purge 會消失（探針 `mixed_side_decision_test`）；真正跨界（decision∈train ∧ label_end≥test_start）兩版皆 purge。見必答 3。

assumed: `(5.2)` 改寫為「落地後契約」不會讓實作者誤以為現況已是如此  
→ **本輪成立於字面**：L76 開首即「本延伸落地後之契約（改前形狀見 `D-002-C4`…）」。殘留風險改在「見 Task 9.2a」的懸空交叉引用（併入 P1-01），不另開 (5.2) 誤讀洞。

assumed: mutation 23 條已覆蓋三個 Task 與四參數閘  
→ **否證**：實為 22 條；且**沒有**對 `build_event_keys` merge／`feature_timeframe` 產出欄的 mutation。見 P1-03。

---

## 必答 1–5

### 1. 本家 R4 finding 是否閉合

| R4 ID | 判定 | 確認方式 |
|---|---|---|
| `GROK-R4-P1-01` | **CLOSED**（四參數閘派工面） | Task 9.2 L151 含 `pipeline.py:723-732` 與 `:711-715` docstring；投影門檻改三者；`M-SU-D2-21` 對位。**殘留改開 R5-P1-01**：閘後下一層 merge 仍擋全量 |
| `GROK-R4-P1-02` | **CLOSED**（(3.1) 施工落點面） | 新增 `Task 9.2b` L166-170 指名 `:530-553` 改 `decision_at_ms` 廣播；§V L194 錨定反例；`M-SU-D2-22` 對位 |
| `GROK-R4-P1-03` | **CLOSED**（§V 全量 ASSERT 面） | §V L192 端到端經 `EventSamplePipeline.run`；schema 句改掛 9.2a；`M-SU-D2-20` 改指端到端 |
| `GROK-R4-P1-04` | **CLOSED** | `(5.2)` L76 改寫為落地後契約（全量複合鍵／兩表含欄／clusters 事件級／側別錨定） |

### 2. 第四層在哪（`EventSamplePipeline.run` → `assignments`）

**走過的關卡（生產投影分支 `if given:`）：**

| # | 關卡 | 現況 | 第五次修訂是否派工 |
|---|---|---|---|
| 1 | `assert_split_allowed` | lookahead 閘 | 不在本延伸 |
| 2 | `_prepare` → receipts／manifest | 可產出多 feature TF `per_tf` | 不改 |
| 3 | 四參數 `projection_args` 閘 L723-732 | `selected=None` ⇒ fail-closed | **Task 9.2 已派** |
| 4 | embargo 雙隔離閘 L739-744 | 投影時禁毫秒 embargo | 不在本延伸 |
| 5 | `build_event_keys(..., str(selected))` L747 | 必傳＋`str()` | **Task 9.2 已派** |
| 6 | **`build_event_keys` 內 `merge validate="1:1"` L291-293** | 全量多 TF ⇒ `MergeError`；且未把 `per_tf.timeframe` 帶成 `feature_timeframe`（輸出 `timeframe`＝trigger） | **未派工（第四層）** |
| 7 | L284-289 選定 TF 下 `event_id` 唯一 | 全量後必須改複合鍵 | Task 9.2a |
| 8 | derive 入口 L441-444 `event_id` 重複閘 | 同上 | Task 9.2a |
| 9 | L530-553 per-`feature_cutoff_ms` 判側 | 異 cutoff 異結果 | Task 9.2b |
| 10 | `(3.2)` 異側 `AlignmentViolationError` | 義務＋§V＋mutation 有；**無 Task 改法行** | **見 P1-02** |
| 11 | `assignments` 組裝（無 `feature_timeframe` 欄） | 現欄＝`event_id,symbol,split_label` | Task 9.2a（加欄） |

**第四層＝#6。** 探針：`MERGE_1to1_RAISE type=MergeError msg=Merge keys are not unique in right dataset`；`OUT_TIMEFRAMES=['1d']  # trigger, NOT feature`。  
`(5.2)` 雖寫「`merge validate="1:1"` 之判準隨之改為複合鍵，見 `Task 9.2a`」，但 Task 9.2a 全文**無** `merge`／`validate`／`291`——懸空交叉引用。  
找不到「比 merge 更後面、且會在 merge 之前就讓全量路徑靜默丟列」的第五層；若 merge 不改，路徑在組 `event_keys` 時就結束，到不了 assignments。

### 3. `Task 9.2b` 的 purge 語意

現行（`:540-542`）：`if in_train and label_end_ms >= test_start_ms: purge`，其中 `in_train`＝**該列** `feature_cutoff_ms ∈ train_ms`。

9.2b 後：先以事件級 `decision_at_ms` 定側並廣播，答案窗改按**事件側**的 `in_train` 判定。

| 案例 | 現行 | 9.2b | 差異 |
|---|---|---|---|
| decision∈train，label 跨 test，兩 TF cutoff∈train | 兩列 PURGED | 兩列 PURGED | 無 |
| decision∈test，1h cutoff∈test，4h cutoff∈train（皆 ≤decision） | 1h=test／4h=PURGED | 兩列皆 test | **有（消除假 purge）** |
| decision∈train∧label 跨界 | purge | purge | 無 |

碼證：探針 `PURGE_CASE mixed_side_decision_test: current={'1h':'test','4h':'PURGED'} 9.2b={'1h':'test','4h':'test'} differ=True`。  
此差異是 `(3.1)` 的**預期修正**（假 purge→同側），不是與答案窗契約衝突。歷史路徑 `event_split.py:150` 本就用 `decision_at_ms >= test_start` 不等式判側，與「事件級錨定」同族。

### 4. `(3.2)` fail-closed 與 `Task 9.2b` 上線順序

**若先上 `(3.2)` raise、9.2b 未完成：合法多 TF 輸入會 raise／異結果。**  
證據：現行 per-cutoff 下同事件可 1h=test／4h=PURGED；若再加「異側即 `AlignmentViolationError`」而不改判側，會把合法資料當缺陷（與 R4 探針同型）。

規格怎麼寫順序：
- Task 9.2b「不可做」L170：**不得在 `(3.2)` fail-closed 上線前保留 per-cutoff 判側**（有寫）。
- §R L229：Phase 9B **須在單一批次內完成，不得部分上線**（有寫）。
- 但 `(3.2)` 的 **raise 本身沒有 Task 改法落點**（無檔案:行指派「在 derive 何處插入同側檢查」）——只有義務 L48、§V L195、mutation 14／15。Task 9.2a 只寫「複合鍵 guard **先於** C3 同側檢查」，預設檢查已存在。→ **P1-02**

### 5. 修訂引入的新問題／衝突

1. **懸空交叉引用**：`(5.2)`→Task 9.2a 的 merge 改判準，9.2a 未接住（P1-01）。  
2. **mutation 算術**：宣稱 23、實列 22；沿革「20→23（新增 21、22）」＝20+2＝22（P1-03）。  
3. **缺 merge mutation**：第四層無 `M-SU-D2-23`（P1-03）。  
4. `(5.2)` 誤讀現況：本輪字面已標「落地後」→不另開。  
5. 與 D-001／`D-002-C6`：未見新衝突；`n_train` 列數化風險仍由 Task 9.4／C6 覆蓋。

---

## Findings

## GROK-R5-P1-01

**斷言**: 第五次修訂宣稱 Task 9.2／9.2a／9.2b 到位後全量路徑可達，但 `build_event_keys` 的 `event_level.merge(..., validate="1:1")`（`split_projection.py:291-293`）在全量多 feature TF 時必 `MergeError`；且 merge 未納入 `per_tf.timeframe` 為 `feature_timeframe`（輸出 `timeframe` 來自 `event_level`＝trigger TF）。`(5.2)` 把 merge 改判準掛在 Task 9.2a，但 Task 9.2a 正文未提及該 merge——核心目標第四種不可達形態。

**碼證**: VERIFY: 探針構造 2 event × 2 TF → `MergeError: Merge keys are not unique in right dataset`；`1:m` 後 `OUT_TIMEFRAMES=['1d']`（trigger）。`sed -n '279,303p' momentum/Analysis/event_samples/split_projection.py`。SPEC：`(5.2)` L76 含「merge validate…見 Task 9.2a」；Task 9.2a L156-164 無 `merge`／`validate`／`291`。RECHECK: 重跑 `/tmp/grok-splitunify-b9-review-r5/probe_summary.txt` 步驟＋對讀 L76 vs Task 9.2a。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。Agent 若只改四參數閘＋caller `None`＋Optional 過濾，進 `build_event_keys` 全量分支仍被 merge 擋死，§V 端到端全量 ASSERT 必紅或被繞去單選假綠。**修法**：在 `Task 9.2`（或 9.2a）具名 `split_projection.py:291-302`——(a) 全量時 merge 改 `validate="1:m"`（或先以 `(event_id, feature_timeframe)` 為鍵再與 event_level 接合）；(b) 自 `per_tf` 帶出 `timeframe` 並**新建**輸出欄 `feature_timeframe`（不得把 trigger 的 `event_level.timeframe` 冒充）；(c) 單選過濾路徑維持每事件一列時可續用 `1:1`。**可行性證據**：同探針 `PROPER_MERGE rows=4 ftf=['1h','4h']`（rename＋`1:m`）已跑通；不改切分數學、只改 keyed 表組裝。

## GROK-R5-P1-02

**斷言**: `(3.2)` 要求投影端對異側擲 `AlignmentViolationError`，且 Task 9.2a 以「同側檢查」為 guard 先後前提，但**任一 Task 之「改法」均未指名**在 `derive`／`_derive_single_symbol` 何處插入該檢查；義務／§V／mutation 有、施工單無——與 R4 之「(3.1) 有義務無落點」同型殘留。

**碼證**: `AlignmentViolationError` 僅出現於 SPEC L48（義務）、L195（§V）、L217-218（mutation 14／15）；Task 9.2／9.2a／9.2b 改法段無此符號、無「插入同側檢查」行。Task 9.2a L162 只寫複合鍵 guard「須在 D-002-C3 同側檢查**之前**執行」。RECHECK: `grep -n AlignmentViolation docs/SPLITUNIFY_SPEC.D-002.md`＋讀 Task 9.2a／9.2b 全文。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e

[BLOCKING] 信心度=High。實作者可做完 9.2b 廣播（結構性同側）而**永不寫** fail-closed 檢查 ⇒ `M-SU-D2-14`／`15` 與 §V 反例無碼可紅、回歸可把檢查整段刪掉而不被 Task 清單擋住。順序上 9.2b「不可做」與 §R「不得部分上線」有文字，但缺落點仍會讓「先上 raise」或「從未上 raise」兩種失敗。**修法**：在 `Task 9.2b`（或 9.2a）增改法條——於複合鍵唯一 guard 之後、寫入 `assignments` 之前，按 `event_id` 分組檢查 `split_label` 唯一，異側即 `raise AlignmentViolationError`（訊息須含 event_id）；指名函式 `_derive_single_symbol`（與現判側迴圈同檔）。**可行性**：`AlignmentViolationError` 已在專案他處使用（b8 adapter 路徑）；同檔已有 fail-closed raise 模式，只需加分組檢查，不改 purge reason 字面。

## GROK-R5-P1-03

**斷言**: SPEC §V mutation 目錄宣稱「共 23 條」，表格實列僅 `M-SU-D2-01`…`22`（22 條）；沿革「20→23（新增 21、22）」算術亦為 22；且對 P1-01 之 merge／`feature_timeframe` 產出欄**無**對位 mutation——宣稱覆蓋三 Task＋四參數閘為假。

**碼證**: `awk` 計數表列＝22；`grep M-SU-D2-23`＝0；L200 正文「共 23 條」；L247 沿革「20 → **23** 條（新增 `M-SU-D2-21`…`22`）」。RECHECK: 重跑表列計數＋對照 L200／L247。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e

[BLOCKING] 信心度=High。機械／人工驗收若信「23」會以為目錄完整；缺 merge mutant 則 Agent 可保留 `validate="1:1"` 而端到端全量測試若被寫成只打 pipeline 閘＋schema，仍可能假綠。**修法**：①正文與沿革改為「共 22 條」或補 `M-SU-D2-23`；②新增 `M-SU-D2-23`＝「全量路徑仍保留 `merge validate='1:1'` 或不寫入 `feature_timeframe`」→ 應紅＝Task 9.2 端到端全量列數＋`feature_timeframe` 值斷言。**可行性**：純文檔＋一列 mutation；與既有 20→22 表格格式相同。

---

## §1 十一類（摘要）

1. 矛盾：mutation 23 vs 22；`(5.2)`→9.2a merge 懸空（P1-01／03）  
2. 漏項：merge 落點；(3.2) raise 落點（P1-01／02）  
3. 不可測：§V 端到端句在 merge 未改前無法綠  
4. quant：9.2b 消除假 purge＝正確方向（必答 3）  
5. 過度工程：無  
6. OOM：無  
7. Cache：無本輪新洞  
8. API／型別：無本輪新洞  
9. 測試：缺 merge mutation（P1-03）  
10. Agent 可執行：第四層未點行號；(3.2) 無改法行  
11. 短命工：無

## 主動攻擊面（停輪③）

1. 本家 R4 四條 → **皆 CLOSED**（定義／派工字面）  
2. 全路徑走讀 `run`→`assignments` → **開洞 P1-01（merge 第四層）**  
3. 9.2b purge 語意探針 → 假 purge 消除為預期；無新衝突 finding  
4. (3.2)／9.2b 順序 → 文字有、raise **落點無** → **P1-02**  
5. mutation 23 宣稱 → **P1-03**  
6. (5.2) 誤讀現況 → 字面已標落地後，不開洞  

不改就進 Task 9.x：①全量路徑在 `build_event_keys` merge 處炸掉／無 feature_timeframe；②(3.2) 檢查可被整段省略而 mutation 14／15 無碼可紅；③mutation 目錄自相矛盾且漏第四層。

---

## 被當成事實的未驗證假設（§0 彙總）

1. 「9.2＋9.2a＋9.2b 到位 ⇒ 丟列消失」——被 merge 第四層否證。  
2. 「9.2b purge 與答案窗不衝突」——真跨界一致；假 purge 消除為預期。  
3. 「(5.2) 不會被誤讀為現況」——開首已標落地後；懸空 xref 另計。  
4. 「mutation 23 已覆蓋」——被 22 列＋缺 merge mutant 否證。  
5. IC e2e 真實 run——仍未跑（§N 同限）。

ASSUMPTIONS_VERIFIED: 本家 R4 四條字面 CLOSED；obl／fmt rc=0；四參數閘與 str() 仍在；decision_at_ms 於 split_projection=0；merge 1:1 全量 MergeError 探針；mutation 實列 22；manifest 含 decision_at_ms；purge 語意三案例探針  
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；探針 `probe_summary.txt`／`probe_multitf_membership.txt`；`awk` mutation 計數＝22；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r5-grok.md --family grok`  
FAILURES_SEEN: none（本輪為規格複驗，無實作失敗）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r5-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R5-P1-01,GROK-R5-P1-02,GROK-R5-P1-03
CLOSED: GROK-R4-P1-01,GROK-R4-P1-02,GROK-R4-P1-03,GROK-R4-P1-04
STATUS: DONE
