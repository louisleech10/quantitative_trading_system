# Reconcile — 20260911-splitunify-x-review-r9

**來源** 20260911-splitunify-x-review-r9-codex.md, 20260911-splitunify-x-review-r9-grok.md　|　**roster** codex,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **W1 凍結只擋整欄改綁，陣列可原地改寫 ⇒ 兩欄會漂移**——「R8的global→symbol-loc」 | P1 | CODEX-R9-P1-01 | 採納（抽驗屬實，且主委實跑另抓到第二面：`setflags` 未設唯讀故陣列 `writeable` 為真、可原地改寫；且建構時無 defensive copy，呼叫端原陣列之後續改動會滲入已建好的 plan。修法：`SplitPlan` 建構時對 `row_index` 與 `row_index_local` 兩欄皆複製並設為唯讀，附原地改寫與外部別名兩條應紅之變異） |
| **W2 attest 之前提條件未寫明（`timedelta` 語意下標的內序非時間序）**——「本輪逐項核對後無finding；`COD」 | P2 | GROK-R9-P3-00 | 採納（該家判無 finding 且 proceed，但其必答二揭露之前提缺口經主委抽驗**在生產可達**，非假想形狀；而「標的內時刻嚴格遞增」之保證只在 rows 語意下成立 ⇒ 規格同時要求「寫入 `train_local`」與「attest 以 helper 重算相等」在該形狀下互斥。修法：明寫 attest 之前提與該形狀下之處置。🔴 另記：該家必答三稱「凍結 ⇒ 欄位不能被就地改寫」與主委實跑不符，該句不採，見 W1） |

**Verdict**: 需修補後合併——W1 為 P1 擋項，W2 為 P2 文件預條件缺口；D-001 依上表修訂後須由原提出方於 R10 重驗閉合。本輪兩家所附戳記因規格續有實質改動而失效，須重簽。

## 本輪程序記錄

- 本輪兩家裁決相反：一家 blocked 並開 P1，另一家 proceed 且為 sentinel。兩家對「凍結是否擋得住原地改寫」給出**相反的事實斷言**，主委以實跑判定。
- 主委實跑（`venv/bin/python`，建一個最小 plan）：整欄改綁被 `FrozenInstanceError` 擋下；`p.row_index[0] = 99` **成功**，讀回 `[99 2]`，`flags.writeable` 為 `True`；另建一個 plan 後改動傳入之來源陣列，plan 內容同步變成 `[77 6]` ⇒ **無 defensive copy**。故 W1 成立，且範圍比原報更大（原報只提原地改寫，未提別名）。
- 主委抽驗 W2 之可達性：`momentum/Analysis/ic_filter_orchestrator.py:930` 以 `purge_semantic="timedelta"` 建 plan（同檔 `:626` 之另一路徑為 `"rows"`）；而 `momentum/core/contracts.py:562-568` 之「base symbol timestamps must be strictly increasing」僅在 `purge_semantic == "rows"` 分支內。故該前提缺口是生產可達，不是理論形狀。
- 主委抽驗 W1 所指之全框消費端皆屬實：`momentum/Analysis/ic_filter_orchestrator.py:1318`（以 `row_index` 取測試段時刻）、`:1335`（selection count）、`:1359-1360`（rows count）。這些仍讀全框欄，而投影端改讀 local 欄，故原地改寫會使兩側分歧。
- 該 proceed 之一家另指出 D-001 仍殘「入口轉換」措辭（R8 已改為 producer attest），主委同意並於本輪一併改寫，不留待實作期。
- 兩家戳記（codex sha `28a56a9e…`、grok sha `b9bff866…`）於本輪交件檔內，因 D-001 續改而失效。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R9-P1-01

**斷言**: R8 的 global→symbol-local 契約缺口已由 `row_index_local` 補上，但 producer 一次性 attest 不足以維持 `row_index`／`row_index_local` 的並存不變式；`SplitPlan(frozen=True)` 的 numpy 陣列仍可原地修改，故 b8 仍可能在投影與既有全框消費端之間產生漂移。

**碼證**: D-001:66-75、118-122 明定 producer 以 `_local_ordinals_for_symbol` 逐值 attest、derive 只消費 `row_index_local` 且缺欄不得回退；`momentum/core/contracts.py:377-403` 顯示 `SplitPlan` 只以 `@dataclass(frozen=True)` 凍結欄位，`row_index: np.ndarray` 且 `__post_init__` 沒有 defensive copy、`setflags(write=False)` 或兩欄的持續對證。實跑 `venv/bin/python -c '...'` 輸出 `mutated_frozen_field [99, 2]`，證明 frozen dataclass 的 numpy 欄仍可原地改寫。既有 consumer 仍以全框欄位取值：`momentum/Analysis/ic_filter_orchestrator.py:1318` 的 `features_df.index[test_plan.row_index]`、`:1335` 的 selection count、`:1359-1360` 的 rows count；新投影契約則改讀 local 欄。具體路徑是 producer attest 後有人執行 `test_plan.row_index[0] = ...`：derive 讀到未變的 `row_index_local`／fingerprint 而可通過，orchestrator 及 row identity consumer 卻讀到已變的 `row_index`，兩套結果分歧。靜態查核 `rg -n 'setflags|writeable|deep.?freeze|row_index_local' momentum/core/contracts.py momentum/Analysis/event_samples/split_projection.py momentum/Analysis/ic_split_adapter.py momentum/Analysis/ic_filter_orchestrator.py` 未見此契約的防漂移 guard。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#b978f441274b；momentum/core/contracts.py#642aecf26b32；momentum/Analysis/ic_filter_orchestrator.py#4b1b8bc9f22a；momentum/Analysis/event_samples/split_projection.py#98ee62905643

本 finding 不否定 R8 修法在「未被變異的 producer plan」上的座標等價性：`row_index_local` 使 derive 不需全框 symbol vector，交錯 symbol 的越界／錯時刻路徑已被設計上的 producer attest 與缺欄 fail-closed 擋住。因此 `CODEX-R8-P1-01` 已閉合。惟它不等價於「每次 derive 入口依當下 `row_index` 重新轉換」：後者不會繞過同一個 plan 的最新全框欄位，而新方案在 producer attest 後把全框欄位的變動與投影欄位脫鉤。

必答 1：已閉合，證據為 D-001:66-75 的 `row_index_local` producer attest、D-001:70-71 的 derive-only local consumption／缺欄 fail-closed，以及 D-001:118-122 的五條驗證斷言。

必答 2：在 producer 產生後不再變異的前提下，落點等價；在現行 mutable numpy array 契約下不完全等價，具體失效路徑如上。

必答 3：兩欄會漂移；producer 一次性 attest 不足，因 frozen dataclass 未提供深層不可變性，且 derive 刻意不再讀 `row_index`，無法在該入口重建 global→local 關聯。修法需在 D-001／`SplitPlan` 契約中加入兩個 row array 的 defensive copy＋唯讀 guard（或不可變 row 容器）及 mutation regression；單靠 producer attest 不足。

必答 4：orchestrator 單標的初始狀態下 `row_index_local == row_index`，故座標不對稱本身已被消除；但相同的原地變異會使 local 欄保持舊值而 orchestrator 的既有 `row_index` consumer 讀到新值，殘留風險仍在。

必答 5：目前不可進實作，`VERDICT: blocked`。若不補不變式，b8 可通過 construction-time attest／交錯 fixture，卻在 plan 共享後的原地變異路徑中同時產生不同的投影歸屬與 IC 選樣／row identity 數字。

ASSUMPTIONS_VERIFIED: `HANDOFF.md`、`CLAUDE.md`、本 brief、`docs/SPLITUNIFY_SPEC.D-001.md`、`docs/SPLITUNIFY_TODO.md`、R8 reconcile synth 與 R8 source 已讀；D-001 目前 body hash 為 `b9bff86647f633e6a4ecea7dbbf55378e7e252baf23b9d2ab39ec41dedf0c636`；`SplitPlan` shallow-frozen array probe 實跑輸出 `mutated_frozen_field [99, 2]`；R8 producer-attest／derive-local 落點逐條對讀。
TESTS_RUN: `bash scripts/agent_preflight.sh` → rc=0；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `b9bff86647f633e6a4ecea7dbbf55378e7e252baf23b9d2ab39ec41dedf0c636`；`venv/bin/python -c '...SplitPlan...p.row_index[0]=99...'` → `mutated_frozen_field [99, 2]`；`rg -n 'setflags|writeable|deep.?freeze|row_index_local' ...` → 未見 SplitPlan row-array 防漂移 guard。未跑產品 pytest，因 brief 明定 closure／禁改碼且不得跑 `tests/governance` 全套。
FAILURES_SEEN: literal `bash scripts/completeness_check.sh --single ... --family codex` once blocked by PreToolUse dispatch/debt gate before script start；shell-expanded same arguments then passed rc=0；審查期間未執行修正輪。
SCOPE_CHANGES: none；只新增本交件檔，未改 tracked code/data、未 commit/push。
NUMERIC_OR_SCHEMA_IMPACT: none；未改產品數值、schema、golden 或輸出資料；本 finding 建議補契約不可變性與 mutation test。
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r9-codex.md
TMP_CLEANUP: `find /tmp -maxdepth 1 -mindepth 1 \( -name '*workdir*' -o -name 'claude-501' \) -print` → no candidates；未刪除任何項目，`claude-501` 不在場。

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
