# Reconcile — 20260911-splitunify-b9-review-r4

**來源** 20260911-splitunify-b9-review-r4-codex.md, 20260911-splitunify-b9-review-r4-composer.md, 20260911-splitunify-b9-review-r4-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **G1 核心目標第三種不可達形態：投影入口的四參數閘**——「`Task9.2`要求caller「不傳」：即使移除 str() 並傳 None，pipeline 的 canonical 投影閘要求四者同時非 None，會在抵達 build_event_keys 之前 fail-closed | P1 | GROK-R4-P1-01 | 採納（`Task 9.2` 檔案範圍加 `pipeline.py:723-732` 與 `pipeline.py:711-715` 之 docstring；投影門檻改為 `train_plan`／`test_plan`／`feature_index` 三者同時，`selected_timeframe` 降為可選；主委已逐字複驗該閘之 given 長度判斷） |
| **G2 (3.1) 有義務無施工落點：判側碼未派工**——「`D-002-C3`(3.1)定案spl」「`(3.1)`定案側別由事件級`deci」：split_projection 全檔無 decision_at_ms，判側仍逐列取 feature_cutoff_ms | P1 | COMPOSER-R4-P1-03, GROK-R4-P1-02 | 採納（新增 `Task 9.2b` 指名 `split_projection.py:530-553` 改以 `manifest.table` 之 `decision_at_ms` 每事件定側並廣播至該事件所有列；`feature_cutoff_ms` 不再參與 `split_label`；主委已複驗該檔 `decision_at_ms` 命中數為 0） |
| **G3 §V 缺 Task 9.2 全量斷言，mutation 懸空**——「第四次修訂已把`pipeline.py:」：§V 之 Task 9.2 僅驗 schema（實為 9.2a），M-SU-D2-20 所指全量測試無對位句 | P1 | COMPOSER-R4-P1-02, GROK-R4-P1-03 | 採納（§V 增經 `EventSamplePipeline.run` 之全量列數斷言；現有 schema 句改掛 `Task 9.2a`；`M-SU-D2-20` 改指新斷言，並增 `M-SU-D2-21`／`M-SU-D2-22`） |
| **G4 C5 (5.2) 舊語意與本延伸自身義務矛盾**——「`D-002-C5`(5.2)仍描述「選」：仍寫選定 feature TF 後 event_id 唯一、兩表僅以 event_id 標識 | P1 | COMPOSER-R4-P1-01, GROK-R4-P1-04 | 採納（`(5.2)` 改寫為本延伸落地後之契約：producer 預設全量、`(event_id, feature_timeframe)` 唯一、兩表含 `feature_timeframe`、`event_split.build_time_clusters` 維持事件級並交叉指向 `Task 9.2a`） |
| **G5 以上游收斂檔未蓋章為由拒審**——「R4依賴的R3reconcile尚未具備」：主張執行端合約要求未全數核可即不得開始本輪審查 | P1 | CODEX-R4-P1-01 | 駁回（AGENTS.md 第 12 條逐字為動工前不動工，本輪 brief 明列禁改碼禁改 SPEC 屬唯讀審查；且本批 R1 與 R2 與 R3 之收斂檔 RECONCILE-STAMP 數皆為 0，該家在那三輪分別交付 6 與 8 與 11 條實質 finding，同情境前後不一致；該讀法會使戳記與審查互為前置而流程無法啟動。本輪該家零實質審查，欠一輪，併入下一輪審第五版） |

**Verdict**: 需修補後合併

**本輪主委自評（三項，逐條可查證）**

1. **同一個核心目標，第三次以不同形態沒補到**。R3 抓到「只改被呼叫端、沒改 caller」；本輪 grok 抓到「就算改了 caller，投影入口的四參數閘先擋死」。兩者都不是委員擴張要求，而是我每次只補到被指出的那一層，沒有自己把整條生產路徑走一遍。修法：Task 9.2 的驗收改為**端到端**（經 EventSamplePipeline.run 產出全量列），而非任何單點。

2. **我把義務寫進規格，卻沒派施工單**。(3.1) 定死以 decision_at_ms 判側，但沒有任何 Task 指向真正在判側的那段碼——兩家獨立撞題。這與第 1 點同型：規格層自洽不等於實作層可達。

3. **三輪皆有具名攻擊面，無一輪以「無 finding」停輪**；本輪 8 條中 7 條採納、1 條駁回並附兩項碼證。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P1-01

**斷言**: R4 依賴的 R3 reconcile 尚未具備全數 APPROVED 戳記，因此依執行端合約不得開始本輪審查。

**碼證**: VERIFY: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260911-splitunify-b9-review-r3/synth.md codex,composer,grok`；stdout=`RECONCILE-STAMP FAIL: ... synth.md 缺『## 戳記』區段標題`；rc=1。`rg -n '^RECONCILE-STAMP:' handoffs/reconcile/20260911-splitunify-b9-review-r3/synth.md` 無輸出。RECHECK: 重跑上述 reconcile 命令。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r3/synth.md#4250837bfe6b

[BLOCKING] 信心度=High。`AGENTS.md` STAMP-BLOCKED 條款要求未全數 APPROVED 時輸出 blocked 並不動工；本輪因此未執行 brief 必答 1–5 的語意審查，亦未修改程式碼或 SPEC。

VERDICT: blocked
BLOCKED-BY: CODEX-R4-P1-01
CLOSED:

ASSUMPTIONS_VERIFIED: R3 reconcile 戳記前置條件已用實際命令驗證為未通過。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260911-splitunify-b9-review-r3/synth.md codex,composer,grok` → rc=1；缺 `## 戳記`。
FAILURES_SEEN: none
SCOPE_CHANGES: none；未改 code、SPEC、TODO 或根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT: handoffs/20260911-splitunify-b9-review-r4-codex.md
STATUS: BLOCKED — reconcile 未核可
## COMPOSER-R4-P1-01

**斷言**: `D-002-C5` (5.2) 仍描述「選定 feature TF 後 `event_id` 唯一」與 assignments／purged「僅以 `event_id` 標識」，與第四次修訂之 `Task 9.2`（全量複合鍵）及 `Task 9.2a`（兩表加 `feature_timeframe`）**直接矛盾**；R3 `CODEX-R3-P1-01` 同型問題**未閉**。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:76` (5.2) 逐字保留 selected-only／event-only 形狀；同檔 `:148-157` 要求全量 `(event_id, feature_timeframe)` 與兩表加欄。`sed -n '76p;148,157p' docs/SPLITUNIFY_SPEC.D-002.md`。RECHECK: 重跑 sed＋對照沿革 L235（第四次修訂未列 (5.2) 更新）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d01a2fee2223

[BLOCKING] 信心度=High。Agent 照 (5.2) 實作會保留單選 producer 與 event-only 兩表，與 Task 9.2／9.2a 及 `M-SU-D2-20` 衝突，形成假綠。**修法**：將 (5.2) 三處改寫為 post-D002 契約（全量複合鍵 producer、assignments／purged 含 `feature_timeframe`、clusters 維持事件級並 cross-ref Task 9.2a L158）。**可行性**：純文檔替換，不改程式；與 Task 9.2／9.2a 現文一致即可機械 grep 驗證。

## COMPOSER-R4-P1-02

**斷言**: 第四次修訂已把 `pipeline.py:747` 納入 `Task 9.2`，但 §V 之 `Task 9.2` ASSERT 仍只有 `assignments` schema（=9.2a），**缺**經 `EventSamplePipeline.run`／`build_event_keys(selected_timeframe=None)` 之全量列數 ASSERT；`M-SU-D2-20` 指向的「全量 keyed rows 測試」在 §V **無對位句**，Agent 可只改 schema 而 live path 仍單選。

**碼證**: §V L185：`Task 9.2` 僅 `assignments … feature_timeframe … 唯一`；L214 `M-SU-D2-20` 寫「`Task 9.2` 全量 keyed rows 測試」。Task 9.1 §V L184 對 `discarded` 有 producer 級 ASSERT，Task 9.2 **無對稱** pipeline 級。`pipeline.py:747` 現仍必傳 selected。RECHECK: `sed -n '184,186p;214p' docs/SPLITUNIFY_SPEC.D-002.md`＋`pytest -k build_event_keys_picks_selected_timeframe_only`（1 passed，確認現況仍單選）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d01a2fee2223;momentum/Analysis/event_samples/pipeline.py#55ca7327764f

[BLOCKING] 信心度=High。Task 9.x 實作可讓 §V L185 綠燈而 `pipeline.run` 仍傳 `selected_timeframe=str(...)`，SU-RESID-2 核心目標假完成。**修法**：§V 增 `Task 9.2` ASSERT：`WHEN per_tf 含 1h+4h 且經 EventSamplePipeline.run（selected_timeframe=None）THEN build_event_keys 輸出列數=per_tf 列數且兩 TF 皆在`；schema 唯一性 ASSERT 標為 `Task 9.2a`；`M-SU-D2-20` 改指該 ASSERT。**可行性**：全 repo 僅一處生產 caller（已 grep）；現有 `test_splitunify_wiring.py` 可擴一條 pipeline 級案例。

## COMPOSER-R4-P1-03

**斷言**: `D-002-C3` (3.1) 定案 split 側由 `decision_at_ms` 決定，但**任一 Task 之「改法」均未指名** `split_projection.py:530-553` 現行 per-`feature_cutoff_ms` 判側須改為事件級 `decision_at_ms`；Agent 可只完成 Task 9.2a（guard／schema）而漏改側別邏輯，§V 正例 ASSERT（L186）才會紅。

**碼證**: C3 L46 要求 decision_at 錨定；`rg decision_at_ms momentum/Analysis/event_samples/split_projection.py` → **0 命中**；L530-553 逐列 `cutoff = rec["feature_cutoff_ms"]` 後 `in_train/in_test`。Task 9.2a L159-161 只定 guard 先後；Task 9.3 未列此迴圈。RECHECK: 讀 `split_projection.py:528-556`＋C3 L46。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d01a2fee2223;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。實作者照 Task 清單改 guard 與欄位、不改 L530-553 ⇒ (3.1) 名義落地、行為仍 per-cutoff 混側，C3 正例 ASSERT 失敗或靠僥倖通過。**修法**：在 `Task 9.2a` 或 `Task 9.3` 增改法條：`derive_event_split_from_plans`／`_derive_single_symbol` 集合成員判定改以 `manifest.table`（或 event_keys 帶出）之 `decision_at_ms` 對 `train_ms`／`test_ms` 定側並廣播到同事件各 feature TF 列；`feature_cutoff_ms` 僅保留給下游物化。**可行性**：`manifest` 已在 `_derive_single_symbol` 作用域（L337）；`manifest.table` 含 `decision_at_ms`（`event_split.py:68` 同欄用法可照抄）。

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

