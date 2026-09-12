# HANDOFF — 當前任務狀態

**更新：2026-09-12｜現行票：`SPLITUNIFY 收尾`（大；RISK a,b,c）——用已結案之四閘治理票全程跑並記錄摩擦（使用者 2026-09-12 指示）｜規格階段：consult 18 條 → D-001 → R5 11 條 → R6 6 條 → R7 2 → R8 1 → R9 2 → R10 3 → R11 3 → R12 6 → **C2 第 4 點整節重寫為單一現行態**（沿革移出至各輪 synth）→ R13 已派兩家（session `20260911-splitunify-x-review-r13`）**

## 已完成（皆已 push）
- **D-001 延伸檔** `docs/SPLITUNIFY_SPEC.D-001.md`：`c6b99d5a` 初版、`091b1e97` R5 版、`90835929` R6 版、`df91e459` **R7 版（現行）**。落實 §N `R-1`＋TODO §E `SU-RESID-3`＋per-symbol 門檻修正。類別＝**D 延伸**（原檔 Task 3.2 自寫「存活至 per-symbol 投影實作後改寫」）。
- **四輪收斂全部清債**：consult R2（18）／R5（11）／R6（6）／R7（2），`debt_clear` 皆 rc=0，收斂檔在 `handoffs/reconcile/20260911-splitunify-x-{consult-r2,review-r5,review-r6,review-r7}/synth.md`。

## 🔴 R7／R8 閉合輪之裁決（b8 實作依此）
- **座標由 producer attest，投影端不轉換**（R8 推翻 R7 之「入口轉換」：既有 helper 需全框 `symbol_arr`，而簽名與 `SplitPlan` 皆無該向量 ⇒ 不可執行）。`SplitPlan` 新增 `row_index_local`，三個 producer 直接寫入其已有之標的內序號、並以**時間序往返** attest（`sorted_positions[row_index_local]` 逐值等於 `row_index`；🔴 R10：**不得**改用 `_local_ordinals_for_symbol` 之 frame 序結果，會誤擋亂序輸入之直呼叫端；🔴 R11：往返比對**之前**須先跑前置合法性閘（整數、範圍內、無重複、嚴格遞增，複用 `assert_positional_rows` 且不得關 `require_sorted`）——負索引會回捲使往返誤判相等）；`derive` 只消費該欄，缺欄 fail-closed 且**不得回退** `row_index`。🔴 **R10 核心轉向**：不可變性無法保證（唯讀旗標可翻回、`pickle`／`deepcopy` 還原又可寫）⇒ 權威守衛＝投影入口之指紋重驗（指紋是字串欄、凍結擋得住改綁），不可變性僅為縱深防禦；竄改 `row_index` 只影響全框消費端，登記 `SU-RESID-5`。消費全框值者僅五處（`split_projection.py:453-458`／`:473-484`／`:486-487`／`:488`＋指紋），R8 獨立覆核**無第六處**；docstring `:351-353` 須同步改寫。
- **`feature_index_by_symbol` ＝該標的自己的 post-trim 短索引**，不可被全框 `row_index` 直接索引。R7 兩家讀法相反（另一家讀為「須是能被全框列號索引之同一 universe」）⇒ 證明原句有歧義，已在 C1 第 1 點釘死並明記不採之理由（與 C2 第 4 點 `position`＝symbol-local ordinal 互斥）。
- 指定**複用** `momentum/core/contracts.py::_local_ordinals_for_symbol`（`:504-519`）做 producer 端 attest，不得另寫等價函式。🔴 `row_index` 之座標語意在三個 producer 間**本來就不一致**（`contracts.py:659-661` 與 `ic_split_adapter.py:230-231` 為全框；`ic_filter_orchestrator.py:631-643` 因單標的而本即標的內）。

## 定案（b8 實作依此，不得再自行改動）
- **批次序**：**b8＝R-1＋SU-RESID-3** → **b9＝SU-RESID-2＋下游單鍵** → **`D1` 走 R 重開重戳** → **b10＝R-5**。R-5 不得與未完成之 D1 同批上線。
- **hash 不變式**：同 symbol 之 train/test hash 一致；**跨 symbol 允許共用整框 joint hash**（`ic_split_adapter.py:189-199` → `ic_filter_orchestrator.py:907` 現行已如此），🔴 禁把「必互異」寫成閘。身分由「Mapping key／`plan.symbol`／事件 symbol」三角相等承擔。
- **指紋**：`rows` 為 `list[list]`，元素順序 `[int(position), int(feature_ts_ms), str(symbol), str(base_universe_hash)]`，與 `freeze_splitunify_golden.py` 逐字同形；禁 `list[dict]`（實跑 sha 不同）；禁舊欄名 `row_pos`／`ts_ms`。正規化只走 `_index_as_ms`／`assert_epoch_ms_array`，**明文排除** `contracts._coerce_timestamp_array`（秒預設）。空 `row_index` ⇒ `sha256("[]")`。
- 🔴 **producer 三處必須一起改**：`contracts::split_per_symbol`、`ic_split_adapter::_build_plan_pair`、`ic_filter_orchestrator` holdout 路徑。只改比對端會讓生產 plan 全面缺欄。新欄對非 derive 呼叫點給相容 default，**derive 入口缺欄仍 fail-closed**。
- **b8 連動必修**：`split_projection.py:569` 之 `insufficient` 條件與迴圈變數無關（用整批 `n_test`）⇒ 改逐 symbol；`test_splitunify_derive.py:537` 之「`single_symbol` 恆亮」在 R-1 後成假前提，解除條件寫死「僅 `n_symbols > 1`」。
- **mutation**：`M-SU-D1-01`～`20`（15＝attest 判準退回 frame 序、16＝入口略過指紋重算、18＝略過前置合法性閘、19＝關掉 `require_sorted`、20＝只留指紋而移除遞增閘）。🔴 **指紋與遞增閘是合取**：指紋先依序號排序再雜湊 ⇒ 對同集合**重排無感**，擋重排的是遞增閘；規格不得只寫其一。

## 🔴 交件格式三紅線（本票已四度回頭正規化，派工 brief 必須逐字寫出）
findings 用 `## <FAMILY>-R<n>-P<x>-<nn>` **二級**標題；`CLOSED:` 無內容**留空**、不得寫 `none`；完成訊號**逐字** `STATUS: DONE`（裁決 blocked 也一樣）。

## 待辦（R8 回來後）
①收斂 R12 → ②若 proceed 則派三家戳記輪（歷輪戳記因規格續改皆已失效，須重簽；R8 有一份戳記寫 `PLACEHOLDER` 屬無效）→ ③b8 實作。
🔴 兩個坑：①戳記外置於 reconcile synth，對 `docs/*.md` 直接跑 `reconcile_stamps_check.sh` 必 rc=1，不是治理真空 ②`handoffs/*` 已被 `.git/info/exclude` 排除，新交件檔須 `git add -f` 才入版（前幾輪 synth 與 sources.lock 已入版，比照辦理）。

## 開工前固定動作
`bash scripts/agent_preflight.sh`；b8 開工前 `bash scripts/gate.sh dispatch --impl-self --task-id 20260911-SPLITUNIFY-impl-b8-claude …` 自證；生產路徑 commit 必帶 `Ticket-Batch: 20260911-SPLITUNIFY/b8`。🔴 task-id／session 之日期前綴屬 root：一律沿用 `20260911-SPLITUNIFY`（跨日不得改前綴，否則語料對不上、`CLOSED` 被拒）。
