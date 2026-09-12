# SPLITUNIFY D-001 閉合確認 R11（grok）

brief-kind: closure  
task-id: 20260911-SPLITUNIFY-X-REVIEW-R11  
family: grok  
findings-round: R11  
標的：`docs/SPLITUNIFY_SPEC.D-001.md`（R10 後修訂版；`bash scripts/reconcile_body_hash.sh` → `dbb0a67e4553d31ffbf5365a2a6a1342965f414289878c3de6668dc82f780238`）  
SCOPE: 只讀 closure；禁改碼、禁動 tracked 檔、禁 commit/push、禁跑 `tests/governance` 全套。  
**範本**：`templates/COMMITTEE_FINDING_TEMPLATE.md`（canonical finding 四欄＋末段 VERDICT／BLOCKED-BY／CLOSED）。

### §0 前提

fact-verified: R10 兩條 P1（W1／W2）與主委自產條皆採納並落入 D-001 → `handoffs/reconcile/20260911-splitunify-x-review-r10/synth.md`  
fact-verified: 權威守衛改寫為入口指紋重驗、不可變性降為縱深防禦、`SU-RESID-5` 已登記 → D-001:72-75／:173  
fact-verified: attest 判準改為時間序往返；R9「frame 序非時間序 ⇒ fail-closed」條款已刪 → D-001:69／:76；ASSERT :131-132；`M-SU-D1-15`  
fact-verified: 現行碼尚無 `row_index_local`／`row_time_fingerprint`／入口指紋比對（待 b8）→ `contracts.py:377-390`；`split_projection.py:330+`  
fact-verified: `assert_positional_rows(..., require_sorted=True)` 預設擋非嚴格遞增 → `split_preview.py:123-163`  
assumed: 入口指紋重驗足以擋建構後對 `row_index_local` 的竄改 → 否證見必答 2（已跑規格語意探針）  
assumed: 時間序往返在亂序輸入下不誤擋且仍有偵錯力 → 否證見必答 3（已跑）

---

## 必答 1–5

### 1. `CODEX-R10-P1-01` 與 `CODEX-R10-P1-02` 是否已閉合？

| ID | 規格面 | 碼證 |
|---|---|---|
| **CODEX-R10-P1-01** | **已閉合** | 根因（numpy 層無法完整封住）→ D-001:72；權威守衛＝入口重驗 → :73；縱深防禦＋誠實邊界 → :74；`SU-RESID-5` → :75／:173；ASSERT 竄改 local 應紅 → :133；`M-SU-D1-16`／`17` → :162-163。本輪複驗 `asarray`+`setflags` 可翻回、`frombuffer` 擋翻回但 `pickle`／`deepcopy` 仍 writeable。 |
| **CODEX-R10-P1-02** | **未完全閉合** | 敘事與新 ASSERT／mutation 已改對（:69／:76／:131-132／`M-SU-D1-15`），但 Task 8.2 **仍殘留**舊 ASSERT :123（要求 `_local_ordinals_for_symbol(...) == row_index_local`），與 :132「亂序＋正確 local ⇒ rc=0」及 :69「不得用 helper 當判準」互斥。見 `GROK-R11-P1-01`。 |

### 2. 攻擊「入口指紋重驗足以擋下建構後對 `row_index_local` 的竄改」

**結論：集合被改的竄改會被指紋擋下；同集合重排會同指紋，但無法在「嚴格遞增」約束下改變語意；雙改 fingerprint 字串屬 frozen 逃生口。未找到可繞過「指紋＋遞增閘」且改變成員集合的構造。**

① **同指紋竄改？** 依 D-001 形狀（`[position, feature_ts_ms, symbol, hash]`，先依 position 排序再 `sha256`）實跑：

| 竄改 | same_fp | set_same |
|---|---|---|
| `local+1`／換元／重複 | False | False |
| 中段重排／全反／旋轉／任意同集合 perm | True | True |
| 兩 position 同時刻但不同 position | False | — |

同集合且 **strictly increasing** 的 perm **只有恆等**（5!＝120 個同指紋 perm 中僅 1 個遞增）。故：改集合 → 指紋必變；只重排 → 指紋不變，但 `assert_positional_rows(require_sorted=True)`（消費封閉清單①）會擋非遞增。指紋**單獨**擋不住重排；與遞增閘合取後，無「同指紋＋仍遞增＋改集合」的構造。

`object.__setattr__(plan, "row_time_fingerprint", new_fp)` 可在改 local 後把字串欄改成匹配值（正常屬性寫入被 `FrozenInstanceError` 擋）。此為 Python frozen 已知逃生口，與 R10 對 `object.__setattr__` 的立場一致，**不升級為本輪擋項**。

② **是否所有投影入口都執行比對？** 現行 `derive_event_split_from_plans` **尚無** fingerprint／`row_index_local`（`fingerprint in src == False`）。生產呼叫點僅 `pipeline.py:745` → 單一函式；列消費前有多個 early-return，皆不索引 row。規格要求 wrapper 不得含第二份判定、比對點在投影入口（C2 第 6 點）。**未找到**可在消費 `row_index_local` 之後／之外繞過比對的第二條活路徑；比對本身待 b8 落地，`M-SU-D1-16` 守「略過比對」。

③ **缺欄／空字串是否先於比對？** 規格有「缺 `row_time_fingerprint` ⇒ rc!=0」（:121）。模擬閘：`None`／`""` → `FAIL_MISSING_OR_EMPTY`（先於 mismatch）；空列合法值＝`sha256("[]")`（≠`""`）。**找不到**「空字串被當成合法指紋而走到錯比對」的規格缺口——前提是 b8 把 `""` 與缺欄同等 fail-closed（建議與 :121 同測）。

### 3. 時間序往返：不誤擋 × 仍有偵錯力

① **亂序輸入 rc=0？** 構造 frame_ts 打亂之單標的面板；`sorted_positions = argsort(ts)` 後 `train_local=0..4`、`train_rows=sorted_positions[train_local]` → 往返 `sorted_positions[train_local]==train_rows` 為 **True**。同資料上舊 helper（frame 序 `0..n` 索引）`helper_local==train_local` 為 **False**（會誤擋）。與 :69／:132 一致。

② **錯誤 local 是否必然不等？** `train_local+1` → 往返 False；另標的／尾端位移 `local=[1,2]` 對 `sorted_pos_A=[0,2,4]` 且真值 `[0,2]` → False。故整體位移與錯映會被抓。

### 4. `SU-RESID-5` 延後是否可接受？

**可接受，不擋 b8 收案。** 全框消費端（`ic_filter_orchestrator.py:1318`／`:1335`／`:1359-1360`）讀 `row_index` 無入口重驗，屬 SplitPlan **既有**可寫性，非本批引入。b8 投影正確性由指紋重驗＋`row_index_local` 覆蓋；不做 SU-RESID-5 **不會**讓 per-symbol 投影 ASSERT／交錯 fixture 出現可證偽假綠。若堅持本批做，失敗模式是 IC holdout 在「建構後竄改 `row_index`」下靜默錯 `test_timestamps`／class 計數——那是殘留研究題，不是 R-1／SU-RESID-3 收案條件。

### 5. 可否進入實作？

**不可。`VERDICT: blocked`。** 必答 2–4 對主委核心主張與往返判準的攻擊未找到可繞過之實作級漏洞，但 `CODEX-R10-P1-02` 的 ASSERT 清單仍留舊 helper 句，b8 若照 :123 實作／驗收會與 :132 互斥並重回「亂序誤擋」。須先刪或改寫 :123 後再進實作。

---

## GROK-R11-P1-01

**斷言**: D-001 Task 8.2 之 ASSERT :123 仍要求 `_local_ordinals_for_symbol(...)` 逐值等於 `row_index_local`，與同節 :132（亂序輸入＋正確 local ⇒ rc=0）及 C2 第 4 點「不得以 helper 當 attest 判準」互斥；保留則 b8 無法同時滿足兩條 ASSERT，且會把 R10 已刪之 frame 序閘變相加回。

**碼證**: `docs/SPLITUNIFY_SPEC.D-001.md:123` 原文 vs `:69`／`:132`／`:161`（`M-SU-D1-15`＝把判準改回 helper 應紅）。實跑亂序單標的：`train_local=[0,1,2,3,4]`、`train_rows=[1,3,5,7,0]`、`helper_locals=searchsorted(frame_pos, train_rows)=[1,3,5,7,0]` ⇒ `helper==train_local` 為 False；往返 `sorted_positions[train_local]==train_rows` 為 True。`contracts.py:504-519`（helper＝frame 序）、`:657-661`（先 `sort_values` 再取 local）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#dbb0a67e4553；handoffs/reconcile/20260911-splitunify-x-review-r10/synth.md#c8f4e5dd23ef；handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R11-BRIEF.md#8d8ec08a18ba；momentum/core/contracts.py#642aecf26b32

修法：刪除或改寫 :123，使唯一 attest ASSERT 與時間序往返（:131-132）一致；不得再把 helper 相等寫成正向綠徑義務。

---

RECONCILE-STAMP: grok APPROVED 2026-09-12 sha256:dbb0a67e4553d31ffbf5365a2a6a1342965f414289878c3de6668dc82f780238 task:20260911-SPLITUNIFY-X-REVIEW-R11

VERDICT: blocked
BLOCKED-BY: GROK-R11-P1-01
CLOSED:
STATUS: DONE

ASSUMPTIONS_VERIFIED: brief／HANDOFF／R10 synth／修訂後 D-001；指紋同集合／遞增合取；缺欄閘序；亂序往返 vs helper；shift／位移偵錯；derive 單一路徑無 fingerprint；SU-RESID-5 消費點行號；ASSERT :123↔:132 互斥實跑。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `dbb0a67e4553…`；venv 探針（指紋篡改矩陣、setattr 逃生、缺欄閘、亂序往返、helper 衝突、same_fp∩increasing 僅恆等）；completeness 見下。
FAILURES_SEEN: 探針首跑末段 `datetime64`→`int` 轉型錯，改用 int64 epoch 後重跑通過。
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r11-grok.md
TMP_CLEANUP: 見收尾；保留 `/tmp/claude-501`。
