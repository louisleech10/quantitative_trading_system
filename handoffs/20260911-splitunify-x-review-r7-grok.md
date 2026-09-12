# SPLITUNIFY D-001 閉合確認 R7（grok）

brief-kind: closure
task-id: 20260911-SPLITUNIFY-X-REVIEW-R7
family: grok
findings-round: R7
標的：`docs/SPLITUNIFY_SPEC.D-001.md`（R6 後修訂版；body sha256 via `reconcile_body_hash.sh`＝`1b63e785a829…`）
SCOPE: closure-only；禁改碼、禁動 tracked 檔、禁 commit／push、禁跑 `tests/governance` 全套
**範本**：`templates/COMMITTEE_FINDING_TEMPLATE.md`
RECONCILE-STAMP: grok APPROVED 2026-09-12 sha256:1b63e785a82981a8359addc742d453d9969e1b310f669f2e05e85419f2839b3e task:20260911-SPLITUNIFY-X-REVIEW-R7

## §0 前提宣告

fact-verified: R6 本家三條（`GROK-R6-P1-01`／`GROK-R6-P2-01`／`GROK-R6-P2-02`）皆列於 `handoffs/reconcile/20260911-splitunify-x-review-r6/synth.md` 群集表且處置＝採納 → 重讀 synth W3–W5
fact-verified: D-001-C2 第 1 點已釘死 `list[list]`、元素順序固定、禁 `list[dict]`、欄位名稱僅文件稱呼 → `docs/SPLITUNIFY_SPEC.D-001.md:56-60`
fact-verified: list vs dict 序列化 sha256 仍不同 → `venv/bin/python` 實跑 list=`69b4daef0b4b…`／dict=`d99c508f6f03…`
fact-verified: freeze 腳本註解仍寫舊欄名 `ts_ms`（修法要求列入 Task 8.2，尚未實作改註解屬預期）→ `scripts/freeze_splitunify_golden.py:152`
fact-verified: C1.2 已改為「指紋已含 symbol…三角相等仍為獨立必查…兩者目的不同」；舊句「指紋不足以分辨」全文不存在 → `grep -n '指紋不足以' docs/SPLITUNIFY_SPEC.D-001.md` 無輸出；`:48`
fact-verified: 觸及面改標「之簽名段」＋限定句「BASE C-4 其餘段落全部原文仍有效…未在本延伸重述 ≠ 已廢止」→ D-001 `:16`／`:20`；BASE C-4 仍含禁 positional zip／兩段式／`build_event_keys`（`git show b095cc75:docs/SPLITUNIFY_SPEC.md`）
fact-verified: producer 仍以全框 `positions[local]` 寫入 `row_index` → `momentum/core/contracts.py:660-677`；既有 `_local_ordinals_for_symbol` 已能全框→local（`:505-519`）
fact-verified: derive 現行以 `assert_positional_rows(row_index, n=len(feature_index))` 直接索引 → `split_projection.py:453-458`
fact-verified: `SU-RESID-4` 已登記（needs-research；觸發＝下一次動 IC 切分契約）→ D-001 `:142`
fact-verified: Task 8.1／8.2 檔案清單含 `freeze_splitunify_golden.py`／`test_splitunify_wiring.py`／`test_splitunify_golden.py`；C2 第 7 點 oracle＝對證 producer 寫入欄；轉換層三條 ASSERT＋`M-SU-D1-08`／`09` 已列 → `:77-111`／`:132-133`
assumed: 無損轉換層足以橋接兩套 row 語意而不引入第二份判定 → 否證觀測見必答 2①（本輪判定：在「指紋計算＋比對共用同一 helper、membership 續用全框 row_index 對 plan 建置時之 universe」讀法下，否證不成立為擋項）
assumed: `SU-RESID-4` 登記為殘留不影響 b8 自洽 → 否證觀測見必答 2②（本輪判定：兩套語意並存是具名長期債，但有 fail-closed／往返 ASSERT 可守 b8；非本輪擋實作）

## 必答 1–3

### 1. 本家 R6 findings 逐條閉合重驗

| R6 ID | 本輪 | 重驗碼證 |
|---|---|---|
| `GROK-R6-P1-01` | **已閉合** | C2 第 1 點逐字釘死 `rows`＝`list[list]`、順序 `[int(position), int(feature_ts_ms), str(symbol), str(base_universe_hash)]`、與 freeze 逐字同形、禁 `list[dict]`、欄位名不進 JSON；Task 8.2 列 freeze 註解 `ts_ms`→`feature_ts_ms`；`M-SU-D1-08` 對形狀漂移。RECHECK: `:56-60`＋list/dict sha 實跑仍異＋freeze `:152` 仍舊註解（待 b8 改，規格已要求） |
| `GROK-R6-P2-01` | **已閉合** | C1.2 末段改寫為「指紋已含 symbol、可區分列所屬標的；三角相等仍為獨立必查，兩者目的不同」；`grep '指紋不足以'`＝0 hit。RECHECK: `:48` |
| `GROK-R6-P2-02` | **已閉合** | 觸及面覆寫改「**之簽名段（僅該函式簽名，見下方限定句）**」；L20 限定句明示 BASE C-4 其餘（keyed `event_keys`、禁 positional zip、兩段式、`build_event_keys`）原文仍有效、未重述≠廢止。RECHECK: `:16`／`:20`＋BASE C-4 義務仍在 `b095cc75` |

### 2. 新引入面反查（轉換層／`SU-RESID-4`）

① **轉換層是否可能成為第二份 row 語意來源？**  
**立場：可能，但規格已把可證偽的分叉面封住；在正確讀法下不構成必須於轉換層外另寫一份才能成立之情形。**  
碼證：C2 第 4 點限轉換於「指紋計算與比對」兩處、**同一支具名 helper**、映不到 fail-closed、往返測試、交錯 fixture；Task 8.2 ASSERT 三條＋`M-SU-D1-09`（映不到就丟棄→應紅）。Producer 寫指紋屬「指紋計算」，比對端在 `split_projection`——兩端必須呼叫同一 helper，不得各寫。既有 `contracts._local_ordinals_for_symbol`（`:505-519`）已是全框→local；b8 應复用／提升為該具名 helper，若再於投影側另寫等價函式才會形成第二份。  
membership 路徑現行仍 `feature_index[row_index]`（`split_projection.py:453-458`），且 C2 明定**不改** `row_index` 全框語意⇒ `feature_index_by_symbol[sym]` 必須是**可被全框 `row_index` 合法索引**的 universe（與 plan 建置時同一數字空間），不得誤讀成「僅含該 symbol 列的短 Index」後又在 membership 旁路再轉一次。該讀法與「轉換只在指紋兩處」＋「逐 symbol 走現行單標的路徑」一致。  
**否證觀測（brief assumed）不成立為擋項**：找不到「若不在轉換層外另寫一份 row 對應則 b8 無法自洽」的必經路徑；分叉只在違反「同一 helper」時出現，而該違反已被 ASSERT／mutation 列為應紅。

② **`SU-RESID-4` 是否留下兩套 row 語意並存的長期債？**  
**立場：會，且已誠實登記；不因此擋 b8。**  
碼證：`:142` 明寫全框 `row_index` 與 fingerprint 所需 local ordinal 並存、研究問題＝是否改 `row_index` 本身並遷移 IC 全框驗證／golden、觸發＝下一次動 IC 切分契約。  
具體錯分路徑（若忽視殘留、把 C2「position＝local」誤套到 `row_index` 本身）：交錯多標的下以短 Index 直接吃全框 `row_index` → `assert_positional_rows` 越界或指到錯時刻；或以全框值當 local 寫入指紋 → 與比對端 helper 結果永異。b8 防線＝helper 唯一＋映不到 fail-closed＋交錯 fixture ASSERT，不是靠消滅第二語意。殘留債在下一次動 IC 切分契約時用 `SU-RESID-4` 完成判準消化，而非本批偷改 `row_index`。

### 3. 可否進入實作？

**可（`VERDICT: proceed`）。** 本家 R6 三條皆已閉合；必答 2 之轉換層／殘留反查不構成新的 P0／P1 擋項。進入 b8 時須守：指紋計算（含 producer 寫入）與比對共用同一 helper；`feature_index_by_symbol` 與全框 `row_index` 數字空間相容；freeze 註解與 list 形狀依 Task 8.2 落地。

## GROK-R7-P3-00

**斷言**: 本輪逐項核對後無 finding；本家 R6 三條（P1-01／P2-01／P2-02）於修訂後 D-001 皆已閉合，轉換層與 `SU-RESID-4` 反查不另開擋項。

**碼證**: 對讀 D-001 `:16`／`:20`／`:48`／`:56-69`／`:77-111`／`:132-133`／`:142`；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `1b63e785a82981a8359addc742d453d9969e1b310f669f2e05e85419f2839b3e`；`grep -n '指紋不足以' docs/SPLITUNIFY_SPEC.D-001.md` → 無輸出；list/dict sha 實跑不同；producer `contracts.py:660-677` 仍全框；`_local_ordinals_for_symbol` `:505-519`；freeze `:152` 仍 `ts_ms`（規格已要求 b8 改）。RECHECK: 重讀上表三列＋必答 2。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#3fca8643e4c0;handoffs/20260911-splitunify-x-review-r6-grok.md#2a272f8fa764;handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R7-BRIEF.md#bc8d16405e06;handoffs/reconcile/20260911-splitunify-x-review-r6/synth.md

正文：sentinel only。閉合依據＝規格字面已落入 R6 修法落點表；未改碼、未重跑產品 pytest（closure 範圍）。

ASSUMPTIONS_VERIFIED: R6 三條落點字面皆在；list/dict sha 仍異；舊互斥句已刪；C-4 簽名段限定句在；producer 全框語意未變；`SU-RESID-4` 已登記；轉換層「同一 helper＋僅指紋兩處」與 membership 全框索引可並讀而無必經旁路轉換
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `1b63e785…`；`grep -n '指紋不足以' docs/SPLITUNIFY_SPEC.D-001.md` → 0；`venv/bin/python` list/dict sha 對照 → 不同；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-review-r7-grok.md --family grok` → 見下
FAILURES_SEEN: none（closure-only）
SCOPE_CHANGES: none（僅本產出檔＋交接檔）
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r7-grok.md

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R6-P1-01,GROK-R6-P2-01,GROK-R6-P2-02
STATUS: DONE
