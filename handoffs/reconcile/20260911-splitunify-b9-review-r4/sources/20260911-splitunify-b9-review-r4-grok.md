# SPLITUNIFY D-002 閉合輪 R4 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R4`  
family: grok  
findings-round: R4  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第四次修訂；full sha12 `d01a2fee2223`）  
上游收斂: `handoffs/reconcile/20260911-splitunify-b9-review-r3/synth.md`  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r4/`（交件後清除；保留 `/tmp/claude-501*`）  
本家待閉: `GROK-R3-P1-01`、`GROK-R3-P1-02`、`GROK-R3-P1-03`

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: 七群 15 條全部採納零駁回 → 讀 r3 `synth.md` 群集表；本家三條皆在「採納」列

fact-verified: 三道閘中義務／格式 rc=0 → 本輪實跑 `obligation_block_check.sh`／`doc_format_precheck.sh` 皆 rc=0；`spec_xref_check.sh --synth` 用法需第二參數，未依 brief 三份全跑（標未經覆核）

fact-verified: `pipeline.py:747` 仍為 `build_event_keys(receipts, selected_timeframe=str(selected_timeframe))` → `sed -n '745,748p'`

fact-verified: `grep -rn 'build_event_keys(' momentum api` → 生產呼叫**僅** `pipeline.py:747`（測試另計）

fact-verified: 現行側別判定用 `feature_cutoff_ms ∈ train_ms/test_ms`（`split_projection.py:530-553`）；`split_projection.py` 對 `decision_at` 僅註解一處，**零**判側用法

assumed: `(3.1)` 事件級錨定不會讓某 feature TF 拿到「該側不該看到」的特徵  
→ **判定＝兩者皆非（非洩漏、非本延伸新引入的資訊不足）**。見必答 2 與探針 `probe_31_summary.txt`。

assumed: `(3.2)` 改 fail-closed 不會讓合法資料上線後 raise  
→ **條件成立**：僅當側別改碼一併落地。若只加同側檢查、仍用 cutoff 判側 → 合法多 TF 會 raise／異結果（探針：1h=test、4h=PURGED）。見必答 3／P1-02。

assumed: 複合鍵唯一 guard 先於同側檢查不會把真異側吃成「重複鍵」  
→ **成立於可區分案例**。同 `(event_id, feature_timeframe)` 重複已是更基礎缺陷，先報鍵重複正確；異側且鍵唯一（不同 feature TF）會落到 C3 檢查。見必答 5。

assumed: 移除 `str()` 後 `selected_timeframe=None` 下游皆有定義  
→ **否證**：即便改 Optional 並傳 `None`，`pipeline.run` 的「四者同時」閘（L723-732）把 `None` 當缺參 → fail-closed。見必答 4／P1-01。

---

## 必答 1–5

### 1. 本家 R3 finding 是否閉合

| R3 ID | 判定 | 確認方式 |
|---|---|---|
| `GROK-R3-P1-01` | **CLOSED**（定義面） | L46 `(3.1)` 已寫死「側由 `decision_at_ms` 決定、cutoff 不參與判側、恆同側為結構性保證」；§V L186 正例改為「cutoff 不同仍同側且不誤 purge」。**殘留改開 R4-P1-02**：無 Task 指派改 `L530-553` |
| `GROK-R3-P1-02` | **CLOSED**（caller／`str()` 面） | Task 9.2 L150-152 含 `pipeline.py:747`、移除 `str()`、「只改被呼叫端不算完成」。**殘留改開 R4-P1-01／P1-03**：四參數閘＋§V 全量 ASSERT 仍缺 |
| `GROK-R3-P1-03` | **CLOSED** | L213 `M-SU-D2-19` 已改反向：「六鍵**被改成含 feature TF**」才是缺陷 |

### 2. `(3.1)` 事件級錨定——cutoff 早於 split 邊界是否洩漏？

**試了什麼（不得只讀 SPEC）：**

1. 構造：`decision_at=7e6∈test`；`cutoff_1h=7e6∈test`；`cutoff_4h=4e6∈train`；兩者皆 `<= decision_at`（PIT 契約）。
2. 現行 derive 語意（照抄 L530-553）：1h→`test`；4h→`PURGED(interval_crosses)`（因 `in_train and label_end>=test_start`）→ **同事件異結果**。
3. `(3.1)` 語意：兩列皆由 `decision_at` → 同為 `test`。
4. PIT：`alignment.py:207` 強制 `cutoff <= decision_at`；物化取 as-of 列，不取決策後 bar。

**結論：非洩漏、亦非本延伸新引入的資訊不足。**  
test 事件使用決策前（甚至落在 train 日曆區）的 as-of 特徵＝既有 `cutoff<=decision_at` 契約下的**陳舊特徵**，不是標籤／未來資訊洩漏。真正的非法 OOS 是「同事件各 TF 被判到不同側後被事件級消費者拼在一起」——那正是現行 cutoff 判側會造成、`(3.1)` 要消除的形態。

### 3. `(3.2)` 由 purge 改 fail-closed 是否正確？

**同意（在 `(3.1)` 落地＝側別改碼一併完成的前提下）。**  
`(3.1)` 成立後，合法 receipts 共享同一 `decision_at_ms`（`alignment.py:219` 寫入 event_level；`manifest.table` 同欄供 `event_split.py:68` 用）⇒ 異側**只能**來自實作仍走 per-cutoff 判側。此時 purge 會把實作缺陷算成樣本流失；改 `AlignmentViolationError` 正確。  
`interval_crosses_split_boundary` 維持事件級答案窗跨界（與 feature TF 無關）——與 C3 異側 raise **正交**，不衝突。  
**反對條件**：若只加同側檢查、不改 L530-553，則合法多 TF 會被 raise／異結果（探針已證）⇒ 那是 Task 漏派工，不是 `(3.2)` 裁決本身錯。

### 4. `Task 9.2` 是否真補上核心？

**Caller／`str()` 字面已補；端到端仍有兩洞使 `None`＝全量路徑不可達或不可驗。**

1. **四參數同時閘**（L711-732）：canonical 投影要求 `train_plan`＋`test_plan`＋`feature_index`＋`selected_timeframe` 四者同時非 `None`。Task 9.2 寫「不傳或明示 `None`」→ 兩者皆使 `given` 只有 3 項 → **立刻 fail-closed**，到不了 `build_event_keys`。Task 檔案範圍只點 `:747`，**未**點名此閘。→ **P1-01**
2. **§V L185** 仍只驗 schema 唯一（＝9.2a）；`M-SU-D2-20`「全量 keyed rows 測試」在 §V **無對位 ASSERT**。→ **P1-03**
3. `grep` 確認無第二生產 caller；測試／wiring 另計。

三者（Optional producer＋caller 不強制 selected＋去 `str()`）**再加上**放寬／重定義四參數閘之後，預設路徑的靜默丟棄才會消失；單選仍可作可選過濾＋Task 9.1 揭露。

### 5. 修訂引入的新問題／衝突

| 面 | 判定 |
|---|---|
| `(3.2)` raise vs D-001 purge 字面 | 正交：答案窗跨界仍 purge；異側改 raise。無衝突 |
| guard 先於 C3 | 正確；鍵重複與異側可區分 |
| §V 新斷言 vs `D-002-C6` | `n_event_tf_rows_purged` 與事件級 `n_purged` 並存＝符合量詞分離 |
| `M-SU-D2-19` 反向 | 與 C5 (5.4) survivor 事件級對齊；閉合 |
| **新洞** | ①四參數閘 vs `None`（P1-01）②側別改碼無 Task（P1-02）③§V 全量 ASSERT 缺（P1-03）④C5 (5.2) 仍寫 selected-only／僅 `event_id`（P1-04） |

不改就進 Task 9.x：照 Task 9.2 傳 `None` 會被四參數閘擋死；或繞過閘卻不改 L530-553 ⇒ 全量多 TF 混側／誤 purge；§V schema 綠燈可假完成核心。

---

## GROK-R4-P1-01

**斷言**: `Task 9.2` 要求 caller「不傳或明示傳 `selected_timeframe=None`」以輸出全量，但 `EventSamplePipeline.run` 的 canonical 投影閘把 `selected_timeframe` 列為四者同時非 `None` 之一（`pipeline.py:711-732`）——傳 `None` 或省略都會在到達 `build_event_keys` **之前** fail-closed；Task 只點名 `:747`，未派工改此閘。

**碼證**: L711-715 docstring「四者同時」；L723-732 `projection_args` 含 `selected_timeframe`，`given = [k for k,v in ... if v is not None]`，三者齊＋`selected=None` ⇒ `len(given)=3 != 4` raise。探針 `probe_31_summary.txt`：`four_arg … fail_closed=True`。SPEC Task 9.2 L150-152 只引 `:747`／`str()`。RECHECK: `sed -n '711,748p' momentum/Analysis/event_samples/pipeline.py`＋重跑四參數探針。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d01a2fee2223;momentum/Analysis/event_samples/pipeline.py#55ca7327764f

[BLOCKING] 信心度=High。Agent 若只改 `:747` 去 `str()` 並傳 `None`，生產路徑改報「參數未給齊」而非全量列——核心目標仍不可達。**修法**：Task 9.2 檔案範圍加上 `pipeline.py:723-732`；把投影門檻改為「`train_plan`＋`test_plan`＋`feature_index` 三者同時」，`selected_timeframe` 改為**可選**（`None`＝全量、有字串＝單選過濾＋Task 9.1 揭露）；同步改 L711-715 docstring「四者同時」措辭。**可行性**：該閘是單純存在性檢查；`selected_timeframe` 已是 `Optional[str]=None`（L704），只需把它移出 `projection_args` 的必填集合（或改用顯式「投影模式」旗標），不改切分數學。

---

## GROK-R4-P1-02

**斷言**: `(3.1)` 定案側別由事件級 `decision_at_ms` 決定，但**任一 Task 改法均未指名**將 `split_projection.py:530-553` 現行 per-`feature_cutoff_ms` 集合成員判定改為 `decision_at_ms` 廣播；且 `build_event_keys` 輸出欄無 `decision_at_ms`。Agent 可只做 schema／guard 而漏改側別迴圈，使 `(3.1)` 結構性保證與 §V 正例在實作上落空。

**碼證**: C3 L46；`grep decision_at momentum/Analysis/event_samples/split_projection.py` → 僅 L309 註解；L530-553 `cutoff = int(rec["feature_cutoff_ms"]); in_train/in_test = cutoff in train_ms/test_ms`。`build_event_keys` L300-302 輸出欄無 `decision_at_ms`。探針：同事件 1h=test／4h=PURGED。Task 9.2a 只定 guard 先後；Task 9.3 未列此迴圈。RECHECK: 讀 L528-556＋C3 L46＋探針。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d01a2fee2223;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。全量多 TF 上線後，合法異 cutoff 事件會混側或誤 purge；若再加 `(3.2)` raise 而未改判側，則合法輸入開始 raise（否證 brief assumed）。**修法**：在 `Task 9.2a`（或新建子項）寫明：`_derive_single_symbol` 以 `manifest.table["decision_at_ms"]`（已在作用域；`event_split.py:68` 同欄）對 `train_ms`／`test_ms` **每事件一次**定側，廣播到該 `event_id` 所有 feature TF 列；`feature_cutoff_ms` 只供物化／PIT，不參與 `split_label`；答案窗 `interval_crosses_split_boundary` 改按**事件側**（非 per-cutoff `in_train`）判定。**可行性**：`manifest` 已傳入 `_derive_single_symbol`；不必先改 `event_keys` schema 也能 join `decision_at_ms`。

---

## GROK-R4-P1-03

**斷言**: 第四次修訂已把 `pipeline.py:747` 納入 Task 9.2，但 §V 之 `Task 9.2` ASSERT 仍只有 `assignments` 含 `feature_timeframe` 且複合鍵唯一（＝9.2a schema）；`M-SU-D2-20` 所指「全量 keyed rows 測試」在 §V **無對位句**——完成字面 §V 後 live path 仍可單選假綠。

**碼證**: §V L185；L214 `M-SU-D2-20`；對照 Task 9.1 L184 已有 producer 級 `discarded` ASSERT，Task 9.2 無對稱全量 ASSERT。`pytest -k build_event_keys_picks_selected_timeframe_only` → 1 passed（現況仍單選）。RECHECK: `sed -n '184,186p;214p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d01a2fee2223;momentum/Analysis/event_samples/pipeline.py#55ca7327764f

[BLOCKING] 信心度=High。與本家 R3-P1-02 驗收缺口同型、第四次修訂未補。**修法**：§V 增 `Task 9.2` ASSERT：`WHEN per_tf 含 1h+4h 且 EventSamplePipeline.run(selected_timeframe=None)（或 build_event_keys(None)）THEN 輸出列數＝per_tf 列數且兩 TF 皆在`；現 L185 schema 句改掛 `Task 9.2a`；`M-SU-D2-20` 改指該全量 ASSERT（含經 pipeline 一條）。**可行性**：已有 `test_splitunify_wiring.py`／`test_splitunify_derive.py` 可擴；生產 caller 僅一處。

---

## GROK-R4-P1-04

**斷言**: `D-002-C5` (5.2) 仍描述「選定 feature TF 後 `event_id` 唯一」與 assignments／purged「僅以 `event_id` 標識」，與同檔 Task 9.2（全量複合鍵）／Task 9.2a（兩表加 `feature_timeframe`）**直接矛盾**；第四次修訂沿革未列更新 (5.2)。

**碼證**: L76 (5.2) 逐字；L148-160 Task 9.2／9.2a 要求全量與兩表加欄。`clusters` 維持事件級與 (5.2) 第三句相容，但前兩句已過期。RECHECK: `sed -n '76p;148,160p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d01a2fee2223

[BLOCKING] 信心度=High。Agent 若以 (5.2) 為 producer／投影契約會保留單選與 event-only 兩表，與 Task 9.2／`M-SU-D2-20` 衝突。**修法**：改寫 (5.2) 為 post-D002——`build_event_keys` 預設全量、`(event_id, feature_timeframe)` 唯一；assignments／purged 含 `feature_timeframe`；`build_time_clusters` 維持事件級並 cross-ref Task 9.2a。**可行性**：純文檔對齊，grep 三句即可驗。

---

## 11 類快掃（§1）

1. 矛盾／互斥：(5.2)↔Task 9.2／9.2a（P1-04）；Task 9.2 `None`↔四參數閘（P1-01）；(3.1)↔現行 L530-553 無 Task（P1-02）  
2. 漏項：四參數閘、側別改碼落點、§V 全量 ASSERT  
3. 不可測：`M-SU-D2-20` 悬空（P1-03）  
4. quant：(3.1) 錨定本身正確（必答 2）；缺改碼落點才是洞  
5. 過度工程：無  
6. OOM：無  
7. Cache：survivor 反向 mutation 已對齊  
8. API／型別：Task 9.1 落點已指名；本輪不另開  
9. 測試：§V／mutation 缺口如上  
10. Agent 可執行：P1-01／02 會讓「照 Task 做」走錯或做不完  
11. 短命工：無

## 主動攻擊面（停輪③）

1. 本家 R3 三條 → 定義／caller／mutation **CLOSED**；殘留以 R4 新 ID 重開  
2. `(3.1)` 洩漏假設 → 探針否證為「非洩漏」；改開「無 Task 改碼」  
3. `(3.2)` 修訂 R2 裁決 → 同意；條件＝側別改碼  
4. Task 9.2 端到端 → 四參數閘＋§V 缺口  
5. guard 先後／`M-SU-D2-19`／§N TODO 時點 → 未再開洞  
6. (5.2) 過期契約 → P1-04  
7. 多 TF 探針 A/C NO_RAISE、B/D RAISED（與 §A 一致）

## 被當成事實的未驗證假設（§0 彙總）

1. 「七群修訂已消掉 R3 洞」——對本家三條**定義／caller／mutation 面**成立；修訂**新暴露／未補** P1-01..04。  
2. 「`(3.1)` 無洩漏」——本輪探針支持（非洩漏）。  
3. 「`(3.2)` 不上線即 raise」——僅在側別改碼後成立。  
4. 「傳 `None` 即全量」——被四參數閘否證。  
5. 「IC e2e」——仍未跑（§N 同限）。

ASSUMPTIONS_VERIFIED: 本家 R3 三條定義／caller／mutation CLOSED；obligation／format rc=0；build_event_keys 唯一生產 caller＝pipeline:747；四參數閘對 None fail-closed；cutoff 判側異結果探針；multitf A/C/B/D；pytest selected-only 1 passed  
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → A/C NO_RAISE、B/D RAISED；`pytest -k build_event_keys_picks_selected_timeframe_only -q` → 1 passed；探針 `probe_31_summary.txt`；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r4-grok.md --family grok`  
FAILURES_SEEN: none（規格複驗）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r4-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R4-P1-01,GROK-R4-P1-02,GROK-R4-P1-03,GROK-R4-P1-04
CLOSED: GROK-R3-P1-01,GROK-R3-P1-02,GROK-R3-P1-03
STATUS: DONE
