# SPLITUNIFY D-001 閉合確認 R9（grok）

brief-kind: closure  
task-id: 20260911-SPLITUNIFY-X-REVIEW-R9  
family: grok  
findings-round: R9  
標的：`docs/SPLITUNIFY_SPEC.D-001.md`（reconcile body sha256 `b9bff86647f6…`）  
SCOPE: 只讀 closure；禁改碼、禁動 tracked 檔、禁 commit/push、禁跑 `tests/governance` 全套。  
**範本**：`templates/COMMITTEE_FINDING_TEMPLATE.md`（canonical finding 四欄＋末段 VERDICT／BLOCKED-BY／CLOSED；零 findings 用 `## GROK-R9-P3-00` sentinel）。全文照該範本。

### §0 前提

fact-verified: R8 群集 W1＝`CODEX-R8-P1-01` 已採納且修法落點改為 `row_index_local` → `handoffs/reconcile/20260911-splitunify-x-review-r8/synth.md` 群集表  
fact-verified: `_local_ordinals_for_symbol(row_index, symbol_arr, symbol)` 需全框 `symbol_arr` → `contracts.py:504-519`  
fact-verified: 現行 `SplitPlan` 無 `row_index_local`／無 membership 向量 → `contracts.py:377-390`  
fact-verified: 三 producer 已持 local ordinal，且建 plan 處 `symbol_arr` 可得 → `contracts.py:659-661`／`:690`；`ic_split_adapter.py:230-231`／`:258`；`ic_filter_orchestrator.py:631-643`／`:643-648`  
fact-verified: D-001 已寫入「簽名不收全框輸入／producer attest／derive 只消費 `row_index_local`／缺欄不得回退／M-SU-D1-11・12」→ D-001-C1 第 1 點；C2 第 4 點；Task 8.2 驗證段；mutation 表  
fact-verified: `derive_event_split_from_plans` 現行執行態消費 `row_index` 仍為長度閘／首尾對證／成員集合／test 起點四處（docstring 與缺欄檢查不算座標索引）→ `split_projection.py:454-488`  
assumed: producer attest 足以封住兩欄漂移 → 否證觀測見必答 3；未實作、未跑 pytest  
assumed: `row_index_local` 取代入口轉換不損失 R8 防護 → 否證觀測見必答 2；未實作

---

## 必答 1–5

### 1. `CODEX-R8-P1-01` 是否已閉合？

**已閉合（改採等價落點，非原文「補全框向量」）。**

R8 核心擋項＝R7「入口整批 `_local_ordinals_for_symbol`」在契約上叫不動（helper 要 `symbol_arr`，簽名與 `SplitPlan` 皆無）。現行 D-001 改為：

- 投影簽名**不收**全框輸入（C1 第 1 點）；
- producer 寫入並 attest `row_index_local`（C2 第 4 點）；
- `derive` **只消費** `row_index_local`，缺欄 fail-closed 且**不得**回退 `row_index`；
- 驗證／變異覆蓋 attest、缺欄、交錯、單標的相等（Task 8.2；`M-SU-D1-11`／`12`）。

故「不可執行」之契約缺口已消除。R8 建議的「補 membership 向量」未被採用，但擋項本身已被等價機制關閉。

**碼證**: D-001:44／:66-71／:119-122／:146-147；`contracts.py:504-519`／:377-390；R8 synth W1 處置段。

### 2. 主委落點是否真的等價？有無 R8 能擋、本修法擋不住之路徑？

**對 R8 原防護目標（交錯多標的下勿用全框列號索引短 `feature_index`）等價；未找到「R8 能擋、本修法擋不住」的失效路徑。**

| 失效模式 | R8（derive 收 `symbol_arr`＋入口轉換） | 本修法（`row_index_local`＋producer attest） |
|---|---|---|
| 交錯標的全框列號直接索引短 index | 入口轉 local 後擋 | 不索引 `row_index`；用 local 擋 |
| 缺轉換輸入／缺 local 欄 | 缺 `symbol_arr` 應紅 | 缺 `row_index_local` 應紅（禁回退） |
| producer 寫錯 local 且不 fail-closed | derive 端重算可蓋過／揭穿 | `M-SU-D1-11`＋Task 8.2 attest ASSERT 擋 |
| 把全框向量再送回投影 | R8 本身會做這事 | 本修法刻意不做（避免 R7 歧義復發） |

獨立複驗：在「標的內 frame 序＝時間序」前提下（`rows` purge 之 `validate_split_integrity` 已要求該 symbol 的 base timestamps 嚴格遞增，`contracts.py:563-568`），`train_local`／`test_local` 與 `_local_ordinals_for_symbol` 逐值相等（實跑交錯但標的內單調之 fixture → `eq=True`）。此為三個 producer 主路徑之前提。

另觀測（**不構成「R8 較優」**）：若 `purge_semantic="timedelta"` 且標的內 frame 序≠時間序，helper（frame-order）與 splitter 的 `train_local`（time-order）會分歧（實跑 A：`helper=[1,0]` vs `time_local=[0,1]`）。此時 R8 入口轉換會拿到**錯的** local；本修法若忠實寫入 `train_local` 反而對齊時間序 `feature_index`。D-001 同時要求「寫 `train_local`」與「attest＝helper」——在該病理形狀下兩句互斥，會在 producer 端 fail-closed（偏保守）。此為 timedelta 病理輸入之文件預條件缺口，**不是**「R8 能擋而本修法放行」；R8 在同一形狀下會靜默錯序。b8 實作應維持「寫 `train_local`」＋僅在 frame 已 per-symbol 時間單調時做 helper attest（與 rows purge 既有約束對齊）；不必為湊等價改回傳全框向量。

**碼證**: D-001:66-71；`contracts.py:504-519`／:563-568／:659-661；`ic_split_adapter.py:62-63`／:230-231；`ic_filter_orchestrator.py:923-934`（timedelta 路徑）；實跑證明見本輪 `/tmp` 外之 venv python 觀測摘要（上表）。

### 3. 並存欄是否構成第二份 row 語意？attest 是否夠？

**是並存兩份座標語意（全框 `row_index` vs symbol-local `row_index_local`）；在三個 producer 路徑上，強制 helper attest＋frozen dataclass 足以封住寫入時漂移。不足之處只在「繞過 producer 的手工造 plan」。**

- 寫入時：同一支 `_local_ordinals_for_symbol` 逐值相等（D-001:69）；不等 ⇒ fail-closed。  
- 寫入後：`SplitPlan` 為 `frozen=True`（`contracts.py:377`），欄位不能被就地改寫。  
- 投影時：只讀 `row_index_local`；缺欄不回退（D-001:70-71）⇒ 不會在 derive 內用過期全框列號「補」出第二套答案。  
- 指紋／首尾對證仍對 `feature_index` 時刻（C2 第 6／8 點）⇒ 即使 local 被惡意填成與全框無關的同長度序號，時刻對證仍應紅。

**attest 封不住的路徑**：呼叫端**不經**三 producer、自行 `SplitPlan(..., row_index=..., row_index_local=錯誤值)` 且湊齊指紋／bounds。此屬敵意／測試造假輸入；生產入口不在此。D-001 已登記 `SU-RESID-4` 追蹤「是否應讓 `row_index` 本身改為 local」。不擋 b8。

**碼證**: D-001:66-74／:156；`contracts.py:377-390`／:504-519。

### 4. 單標的路徑不對稱是否還有殘留風險？

**有殘留認知風險，無擋 b8 的契約缺口。**

- orchestrator holdout（`:631-643`）：frame 單標的 ⇒ 現行 `row_index` 已是 local；D-001 要求 `row_index_local` 逐值等於 `row_index`（Task 8.2 ASSERT）。  
- 另兩 producer：`row_index` 仍為全框，`row_index_local` 為 `train_local`／`test_local`。  
- 風險＝未來消費端誤假設「兩欄恆等」而拿 `row_index_local` 去做全框 IC 校驗，或拿 `row_index` 去做 per-symbol 投影。前者超出 b8 投影範圍；後者被「derive 不得索引 `row_index`」＋`M-SU-D1-10`／`12` 擋住。  
- C2 第 4 點已明示不改 `row_index` 既有語意；`SU-RESID-4` 追蹤長期收斂。

**碼證**: D-001:66／:122／:156；`ic_filter_orchestrator.py:631-648`；`contracts.py:659-661`；`ic_split_adapter.py:230-231`。

### 5. 可否進入實作？

**可以。`VERDICT: proceed`。**

`CODEX-R8-P1-01` 之不可執行缺口已閉；主委落點在交錯防護上與 R8 等價且避免全框輸入回流；並存欄漂移由 attest＋frozen＋derive 禁回退封住；單標的不對稱有 ASSERT 與 `SU-RESID-4`。文件中仍殘「入口轉換」措辭（C2 封閉清單／Task 8.1 ASSERT 第 93 行）屬 b8 施工時應同步改寫的敘述債（與 docstring `:351-353` 同一類），不重新打開 P1。

---

## GROK-R9-P3-00

**斷言**: 本輪逐項核對後無 finding；`CODEX-R8-P1-01` 已由 `row_index_local` 落點等價閉合，可進 b8 實作。

**碼證**: 重讀 D-001-C1／C2／Task 8.2／mutation；重讀 `contracts.py:377-390`／:504-519／:659-690、`ic_split_adapter.py:215-261`、`ic_filter_orchestrator.py:631-650`、`split_projection.py:351-488`；對照 R8 synth W1；實跑確認 rows-purge 單調交錯下 `train_local==helper`，以及 timedelta 病理序下 helper 與 time-local 可分歧（見必答 2，不升級為擋項）。`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `b9bff86647f633e6a4ecea7dbbf55378e7e252baf23b9d2ab39ec41dedf0c636`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#b9bff86647f6；handoffs/reconcile/20260911-splitunify-x-review-r8/synth.md#54dd8fdff576；momentum/core/contracts.py#642aecf26b32；momentum/Analysis/event_samples/split_projection.py#98ee62905643；momentum/Analysis/ic_split_adapter.py#c2dd93482826；momentum/Analysis/ic_filter_orchestrator.py#4b1b8bc9f22a；handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R9-BRIEF.md#1d934d79c6e2

本輪為閉合確認：必答 1–5 皆有立場與碼證；零實質新 finding，故以 sentinel 收斂，未捏造擋項。

---

RECONCILE-STAMP: grok APPROVED 2026-09-12 sha256:b9bff86647f633e6a4ecea7dbbf55378e7e252baf23b9d2ab39ec41dedf0c636 task:20260911-SPLITUNIFY-X-REVIEW-R9

VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE

ASSUMPTIONS_VERIFIED: brief／HANDOFF／R8 synth／現行 D-001／三 producer 與 helper／derive 消費點已讀；body hash 實跑；train_local↔helper 在單調與病理兩類 fixture 實跑。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `b9bff86647f6…`；venv python 兩組 fixture 觀測 helper vs time-local；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-review-r9-grok.md --family grok`（交件後執行）。
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r9-grok.md
TMP_CLEANUP: `/tmp` 無 `*workdir*` 可清；已保留 `/tmp/claude-501`。
