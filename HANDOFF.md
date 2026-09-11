# HANDOFF — 當前任務狀態

**更新：2026-09-12｜現行票：`SPLITUNIFY 收尾`（大；RISK a,b,c）——用已結案之 `VERDICTGATE` 四閘全程跑並記錄摩擦（使用者 2026-09-12 指示）｜**規格階段：偵察 consult 收斂 → 延伸檔 D-001 → 對抗審 R5 收斂修訂 → R6 三家重審進行中**（session `20260911-splitunify-x-review-r6`）｜前一張治理票 `VERDICTGATE` 已結案（票號與狀態見 `docs/GOV_TICKET_SOT.md`）**

## 已完成（皆已 push）
- **consult 收斂**（`b095cc75`）：三家 18 條＝15 採納／1 部分採納／2 駁回。收斂檔 `handoffs/reconcile/20260911-splitunify-x-consult-r2/synth.md`。
- **延伸檔** `docs/SPLITUNIFY_SPEC.D-001.md`（`c6b99d5a` 初版、`091b1e97` R5 修訂版）：落實 §N 之 `R-1`（per-symbol 投影）與 TODO §E 之 `SU-RESID-3`（逐列時刻指紋），並修 per-symbol 門檻失效。類別＝**D 延伸**（原檔 Task 3.2 自寫「存活至 per-symbol 投影實作後改寫」「不得只刪 raise」；R5 兩家覆核成立）。
- **對抗審 R5 收斂**（`091b1e97`）：三家 11 條＝10 實質全採納、1 程序性 P0 駁回。收斂檔 `handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md`。
- R6 brief `fde8bc41`。

## 定案（b8 實作依此，不得再自行改動）
- **批次序**：**b8＝R-1＋SU-RESID-3**（識別基礎）→ **b9＝SU-RESID-2＋下游單鍵** → **`D1` 走 R 重開重戳** → **b10＝R-5**。R-5 不得與未完成之 D1 同批上線。
- **hash 不變式**：同 symbol 之 train/test hash 一致；**跨 symbol 允許共用整框 joint hash**（`ic_split_adapter.py:189-199` → `ic_filter_orchestrator.py:907` 現行已如此），🔴 禁把「必互異」寫成閘（會拒收現行 IC 多標的計畫）。symbol 身分由「Mapping key／`plan.symbol`／事件 symbol」三角相等承擔，不由 hash 或指紋承擔。
- **指紋**：payload 對齊 §G G-5① 四元組 `(position, feature_ts_ms, symbol, base_universe_hash)`（禁用舊欄名）；元素強制 `int(...)`；正規化只走 `_index_as_ms`／`assert_epoch_ms_array`，**明文排除** `contracts._coerce_timestamp_array`（秒預設）；取數必從該 symbol 之 post-trim `feature_index`；重複 `position`／NaT ⇒ fail-closed；空 `row_index` ⇒ `sha256("[]")`。
- 🔴 **producer 寫入點必須一起改**（R5 兩家 P1）：`momentum/core/contracts.py::split_per_symbol`、`momentum/Analysis/ic_split_adapter.py::_build_plan_pair`、`momentum/Analysis/ic_filter_orchestrator.py` holdout 路徑。只改比對端會讓生產 plan 全面缺欄、單標的綠徑全滅。新欄對非 derive 呼叫點給相容 default，**derive 入口缺欄仍 fail-closed**。
- **C-4 已列入覆寫**（非依賴）：投影簽名改 `Mapping[symbol,(train,test)]`＋`feature_index_by_symbol`；單標的舊式保留為**薄 wrapper**（不得含第二份判定邏輯）；`pipeline.py` 呼叫要一併改。
- **b8 連動必修**：`split_projection.py:569` 之 `insufficient` 條件與迴圈變數無關（用整批 `n_test`）⇒ 改逐 symbol，配「一標的低於門檻但總數高於門檻」負例；`test_splitunify_derive.py:537` 之「`single_symbol` 恆亮是預期的」在 R-1 後成假前提，解除條件寫死「僅 `n_symbols > 1`」並配 mutation。
- **mutation**：`M-SU-D1-01`～`07`（07＝跨 symbol 混用 `feature_index`）。

## 🔴 交件格式三紅線（本票已三度回頭正規化，派工 brief 必須逐字寫出）
findings 用 `## <FAMILY>-R<n>-P<x>-<nn>` **二級**標題；`CLOSED:` 無內容**留空**、不得寫 `none`；完成訊號**逐字** `STATUS: DONE`（裁決 blocked 也一樣）。

## 摩擦（使用者要求檢驗；已記 11 筆於 `白話說明/流程摩擦記錄.md`）
最重一筆＝**兩道閘互斥**：委員交件格式錯，不改則 completeness 硬閘擋（掉項）、改了則 `debt_clear` 之「交件後不得改動」擋。**處置慣例：`handoffs/` 原檔保持交件原狀供稽核，格式正規化只落在 `handoffs/reconcile/<session>/sources/` 複本**（lock 記複本 sha、completeness 驗複本、debt_clear 驗原檔）；若該輪尚未註冊，則正規化後 `register-output`，以 `committee_output.output_sha256` 為權威。另 3 筆是主委自己的判讀錯誤（戳記檢查器用錯對象、`rc` 讀成 pipe 尾端、委員名進指令列被派工閘誤判）。

## 開工前固定動作
`bash scripts/agent_preflight.sh`；b8 開工前 `bash scripts/gate.sh dispatch --impl-self --task-id 20260911-SPLITUNIFY-impl-b8-claude …` 自證；生產路徑 commit 必帶 `Ticket-Batch: 20260911-SPLITUNIFY/b8`。
🔴 task-id／session 之日期前綴屬 root：本票一律沿用 `20260911-SPLITUNIFY`（跨日不得改前綴，否則語料對不上、`CLOSED` 被拒）。
