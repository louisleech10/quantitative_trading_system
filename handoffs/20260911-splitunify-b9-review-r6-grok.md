# SPLITUNIFY D-002 閉合輪 R6 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R6`  
family: grok  
findings-round: R6  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第六次修訂；full sha12 `6073261d303a`）  
上游收斂: `handoffs/reconcile/20260911-splitunify-b9-review-r5/synth.md`  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r6/`（交件後清除；保留 `/tmp/claude-501*`）  
本家待閉: `GROK-R5-P1-01`、`GROK-R5-P1-02`、`GROK-R5-P1-03`

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: R5 十一條歸八群、全部採納 → 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r5/synth.md`；本家三條皆在 H1／H2／H3 採納列

fact-verified: 第六次修訂已寫入 Task 9.2 merge／`feature_timeframe`、Task 9.2b 之 (3.2) raise 落點與不等式判側、mutation 25 條、Task 9.1 二擇一前置、Task 9.4 baseline 例外、§V assignments 標的 → 本輪逐字讀 SPEC；`obligation_block_check`／`doc_format_precheck` 皆 rc=0；mutation 表列實數 25、ID 01–25 連續

fact-verified: `split_projection.py:291-292` 仍為 `validate="1:1"` on `event_id`；`:271` docstring 仍「恰有一列」；`:530-553` 仍 per-cutoff；`pipeline.py:723-732`／`:747` 仍四參數閘＋`str()` → `sed`／`grep`

fact-verified: `holdout_boundary` 在 `purge_gap+embargo>0` 時 train／test 列集合**不連續**（中間有 gap）→ 探針 `probe_ineq_vs_set.out`：gap 三列 set=PURGED、ineq=train、且 `outside_both_bounds=True`

fact-verified: `feature_materialization.py:93-132` 以 `groupby("event_id")+row_vals.update` 寬表合併（非依 `selected_timeframe` 丟列）；記帳 `n_input = per_tf["event_id"].nunique()`（`:137-140`）

assumed: `Task 9.2`（含 merge／輸出欄）＋`9.2a`＋`9.2b` 到位後，生產路徑不再丟列  
→ **對 selected_timeframe 靜默丟列：派工面已覆蓋到第四層（merge）**；但 assignments 之後的物化仍是事件級寬表，且 `tier_min` 計數路徑未派工——見必答 2／P1-03／P1-04。不是第五種「單選丟列」，而是**全量後的形狀／門檻層**。

assumed: `Task 9.2b` 不等式與現行 `train_ms`／`test_ms` 集合成員等價  
→ **否證**：purge／embargo gap 上 set=PURGED、ineq=train；「界外 fail-closed」若解成 outside both plan bounds，則 gap 走 raise，與兩者皆不同。見必答 3／P1-01。

assumed: `(3.2)` raise 放在複合鍵 guard 之後、寫入 assignments 之前正確  
→ **否證（對 purged 互動）**：只檢查即將寫入之 `split_label` 唯一，**抓不到**同事件「一列 purged、一列 test」；而 `M-SU-D2-24` 恰以此為缺陷。見必答 4／P1-02。

assumed: `Task 9.1` 二擇一足以讓 9A 可驗收  
→ **否證**：SPEC 要求實作者擇一，但**本身未擇**；兩邊皆缺可執行驗收命令所需的具名落點／fixture。見必答 5／P1-05。

---

## 必答 1–5

### 1. 本家 R5 finding 是否閉合

| R5 ID | 判定 | 確認方式 |
|---|---|---|
| `GROK-R5-P1-01` | **CLOSED**（派工字面） | Task 9.2 L155 逐行指名 `:291-303`（per_tf 行粒度、複合鍵 validate、新建 `feature_timeframe`）；`:271` docstring 列入必改；`(5.2)` L76 merge xref 改指 Task 9.2；`M-SU-D2-23` 對位 |
| `GROK-R5-P1-02` | **CLOSED**（派工字面） | Task 9.2b L174：複合鍵 guard 之後、寫入 assignments 之前，按 `event_id` 查 `split_label` 唯一，異側 `AlignmentViolationError`，函式 `_derive_single_symbol` |
| `GROK-R5-P1-03` | **CLOSED** | 正文 L207「共 **25** 條」；表列 `awk`＝25、ID 01–25 連續；含 `M-SU-D2-23`／`24`／`25` |

### 2. 第五層在哪（`run` → `assignments` → `feature_materialization`）

**走過的關卡：**

| # | 關卡 | 現況 | 第六次修訂 |
|---|---|---|---|
| 1–5 | lookahead／`_prepare`／四參數閘／embargo／`str(selected)` caller | 仍擋全量 | Task 9.2 已派 |
| 6 | `build_event_keys` merge `1:1`＋輸出 trigger `timeframe` | 仍在 | Task 9.2 已派（H1） |
| 7–8 | 兩道 event_id 重複 guard | 仍單鍵 | Task 9.2a |
| 9 | `:530-553` per-cutoff 判側 | 仍在 | Task 9.2b |
| 10 | `(3.2)` raise | 碼尚無；SPEC 已有落點 | Task 9.2b L174 |
| 11 | `assignments` 組裝 | 無 `feature_timeframe` | Task 9.2a |
| 12 | **`_materialize`／`feature_materialization`：`groupby("event_id")+update` 寬表** | 已處理**全部** `per_tf` 列（無 selected 過濾）；折成**一列／事件**（欄位合併，非丟 TF） | Task 9.3 有改 groupby→複合鍵 MultiIndex，**但未改 `:137-140` 記帳** → **P1-03** |
| 13 | **`pipeline.py:760-762` 與 `split_projection.py:562`／`per_symbol_test_n` 以 assignment 列數當 `n_test`** | 多 TF 後膨脹 | Task 9.4 只點 pipeline／API／前端／wiring，**未點** `_derive_single_symbol` 之 `tier_min` 路徑 → **P1-04** |

**對「靜默丟列」主張：** 在 `assignments` **之前**，第六次修訂已把前四層（單選／caller／四參數閘／merge）寫進 Task；我**沒有**再找到第五個「selected_timeframe 式丟列」關卡——`feature_materialization` **本來就不讀** `selected_timeframe`，它吃完整 `per_tf`。

**真正的第五層＝全量之後的形狀／門檻：** (a) 物化仍事件級寬表 ⇒ assignments 多列 vs features 一列／事件；(b) `tier_min_test_events` 用列數 ⇒ TF 膨脹可繞過事件數下限。前者 Task 9.3 **有點名、改法不完整**；後者 **無施工落點**。

### 3. 不等式 vs 集合成員（有間隙）

`holdout_boundary(purge_gap=2, embargo=1)`：train=`[0..13]`，gap=`[14,15,16]`，test=`[17,18,19]`。

| 位置 | set 成員 | 不等式 `< test_start` | outside both plan bounds |
|---|---|---|---|
| train 內 | train | train | False |
| **gap** | **PURGED_else** | **train** | **True** |
| test 內 | test | test | False |

碼證：`probe_ineq_vs_set.out` `DIFF_COUNT 3`。  
另：gap＋答案窗未跨界（`label_end < test_start`）時，純不等式會把**現行一律 purge** 的時刻收成 **train 樣本**——切分成員集改變，不是「同語意換寫法」。  
SPEC L173 同時寫不等式與「界外 fail-closed」，但**未定義** gap（兩 plan `time_bounds` 之外、又 `< test_start`）算哪一種 ⇒ 實作者可走出 TRAIN／raise／（若誤留 set）PURGED 三條歧路。→ **P1-01**

### 4. `(3.2)` raise 的位置與 purged 互動

SPEC L174：複合鍵 guard 後、寫入 `assignments` 前，按 `event_id` 查 **`split_label` 唯一**。

**會漏的一類：** 同事件一 TF 進 `assign_rows`（有 `split_label`）、另一 TF 進 `purge_rows`（無 `split_label`）。只看 assignments 側 ⇒ 唯一、不 raise。  
探針：`MISS_PURGED_ASSIGN_MIX True`（`probe_tier_and_32.out`）。

此恰為 `M-SU-D2-24`／部分實作（事件級廣播側別＋仍用逐列 `in_train` 做答案窗）會留下的狀態；**(3.2) 檢查與 purged 列的互動未定義**，不能當該缺陷的安全網。→ **P1-02**

### 5. 修訂引入的新問題／衝突

1. **H6 不等式 ≠ 集合成員**（P1-01）；與 D-001「成員判定走集合」敘事張力——本延伸若改不等式須明寫成員集變更與 gap 處置。  
2. **H2 之 (3.2) 落點抓不住 H3 的 `M-SU-D2-24` 缺陷類**（P1-02）。  
3. **H7／Task 9.3 vs 物化記帳**：MultiIndex 列數＝`(event,tf)`，現況不變式用 `event_id.nunique()` ⇒ 字面實作即 `AssertionError` 或誘使保留 groupby event_id（P1-03）。  
4. **H4／Task 9.4 vs `tier_min`**：報告鏈改事件數，但投影摘要門檻仍可能吃列數（P1-04）；與 `D-002-C6`「n_test＝事件數」在 gate 路徑未閉合。  
5. **H5／Task 9.1**：二擇一寫進規格但未擇一 ⇒ 9A 驗收命令仍不可寫（P1-05）。  
6. H1 merge 落點與 `(5.2)` xref：本輪字面已對齊，不另開。  
7. 與 D-001 複合鍵／clusters 事件級：未見新互斥；clusters 不加 `feature_timeframe` 與 Task 9.2a 一致。

---

## Findings

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

## §1 十一類（摘要）

1. 矛盾：不等式「等價」vs gap 實測不等價（P1-01）；(3.2) vs M-SU-D2-24（P1-02）  
2. 漏項：物化記帳（P1-03）；tier_min 路徑（P1-04）；9.1 未擇一（P1-05）  
3. 不可測：9A 終端 ASSERT 無單一可執行命令（P1-05）  
4. quant：gap→train 改變成員；tier_min 膨脹（P1-01／04）  
5. 過度工程：無  
6. OOM：無  
7. Cache：無本輪新洞  
8. API／型別：9.1 可達性未閉  
9. 測試：M-SU-D2-24 與 (3.2) 安全網錯位  
10. Agent 可執行：9.3 缺記帳改法；9.1 缺決策  
11. 短命工：無

## 主動攻擊面（停輪③）

1. 本家 R5 三條 → **皆 CLOSED**（派工字面）  
2. 全路徑走讀含 `feature_materialization` → 第五層＝形狀／記帳／tier_min，非第五種 selected 丟列  
3. 不等式 vs 集合＋gap 探針 → **P1-01**  
4. (3.2) vs purged 探針 → **P1-02**  
5. H1–H7 交叉 → **P1-03／04／05**  

不改就進 Task 9.x：①9.2b 實作時 gap 成員集三歧／漂移；②(3.2) 綠仍放行 purged+assign 混態；③9.3 記帳炸或假綠；④tier_min 被 TF 膨脹；⑤9A 無單一驗收命令。

## 被當成事實的未驗證假設（§0 彙總）

1. 「9.2＋9.2a＋9.2b ⇒ 丟列消失」——對 selected 丟列派工已到 merge；第五層改為物化形狀／tier_min。  
2. 「不等式 ≡ 集合成員」——被 gap 探針否證。  
3. 「(3.2) 位置正確」——對 purged 混態否證。  
4. 「9.1 二擇一足夠驗收」——未擇一 ⇒ 否證。

ASSUMPTIONS_VERIFIED: 本家 R5 三條字面 CLOSED；obl／fmt rc=0；mutation 實列 25；gap 不等式≠集合探針；tier_min 膨脹探針；(3.2) miss purged+assign 探針；物化記帳 MultiIndex 破不變式探針；Task 9.3／9.4 無 tier_min／n_input 字樣  
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`PYTHONPATH=. venv/bin/python /tmp/grok-splitunify-b9-review-r6/probe_ineq_vs_set.py`；`probe_tier_and_32.py`；`probe_mat_accounting.py`；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r6-grok.md --family grok`  
FAILURES_SEEN: 探針初跑缺 PYTHONPATH（ModuleNotFoundError）→ 加 PYTHONPATH=. 後通過  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r6-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R6-P1-01,GROK-R6-P1-02,GROK-R6-P1-03,GROK-R6-P1-04,GROK-R6-P1-05
CLOSED: GROK-R5-P1-01,GROK-R5-P1-02,GROK-R5-P1-03
STATUS: DONE
