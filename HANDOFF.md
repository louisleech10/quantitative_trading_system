# HANDOFF — 當前任務狀態

**更新：2026-09-05（深夜）｜狀態：`G3-D2` **B-D4 ✅ 收工**（兩輪三家審碼收斂）。下一件＝**B-D5**（最後一批）。**

## 🔴 下一件＝B-D5（唯一待辦）

**唯一入口＝`docs/GAP3D2_IMPL_HANDOFF.md`**（§2 每批七步不得跳步；§5 收據）。
B-D5＝`docs/GAP3_EVENT_UX_TODO.D-006.md` Task **D5.1–D5.4**：
`random_control_spec` typed nested schema（`required:false` 鍵級語義）、`label_rule`、
規則身分閘四段、`POST /case/import-events/random-control`、
`compare_random_control`（唯一 owner `ic_analysis_service`）、決定性 golden。
B-D5 完工時之收尾動作見 `docs/GAP3D2_IMPL_HANDOFF.md` §1 之 Phase D5 Gate（registry 狀態變更、
`G3-R7` 收回、UAT 清單該項改寫）——**狀態字面住那裡，本檔不重述**。

## B-D4 收工紀錄（不需接手；供理解現況）

**commit 鏈**：`37fa0910`（實作）→ `34137230`（收據／殘留補登）→ `7904c0dd`（前端接線補做）
→ `d34228e1`＋`90aad087`（R1 閉合）→ `bc8c5e1e`（R2 閉合）。皆已 push。

**兩輪三家審碼**：R1 **10 findings／P0=0／P1=4**（去重 2 個獨立問題）→ R2 **4 findings／P1=0**，
三家 verdict 一致「可進 B-D5」。**findings 10→4、P1 4→0 ⇒ 收斂**。

**最終驗收數字**（皆本機實跑，逐條見 `docs/GAP3D2_IMPL_HANDOFF.md` §5）：
`pytest tests/momentum/event_samples/` **485**｜`pytest tests/api/test_gap3_{scan_grid,ic_event_label_defaults,event_batch_detail_dims}.py` **55**
｜`cd frontend && npx vitest run` **529**（B-D3 收工 502，本批 +27）｜`npx tsc --noEmit` **8 行既有債無新增**
｜golden `--check` **rc=0／46 cases**（原 23）｜解耦 `BASELINE OK`｜mutation **24/24 符合預期**（22 紅＋2 對照綠）。
🔴 `tests/api -k "gap3 or event"` 有 **1 條既有紅**（`test_service_passes_event_timestamps_kwarg`，`G3-R11`／`B1-WEAKTEST-1`：
它 grep 原始碼字串）；本批對該檔之 diff 為純新增，未觸及其目標行。

🔴 **前端測試必須在 `frontend` 目錄跑**（`cd frontend && npx vitest run`）——
`noTicketIdInUi.test.ts` 以相對路徑掃 `src/`，在 repo 根跑會**假紅**。我踩過一次。

## 🔴 三件我自己做的判斷（不是待決策，但不想讓它藏著）

1. **`D-001` D4.2 有一處規格洞**：它寫「既選非法 pair ⇒ 另一維重設為契約 `default`」，
   但 `entry_price_semantic.default = "trigger_close"` 本身就在 `open_to_close` 的拒收對裡
   ⇒ 該方向無解（**被我自己寫的 vitest 當場打穿**）。細化為「default 合法即用它；
   否則取契約 enum 順序第一個合法值並揭露原因」。**未經 SPEC 輪審查** ⇒ 殘留 `B4-SPECGAP-1`。
2. **`scan_grid_max_runs` 由暫定 121 改為 110**：benchmark 先於凍結（硬性約束照做），
   實測五階段單格 6.1ms；而 **121 是算術錯誤**（假設兩軸各 11 值，但 h 定義域自 1 起 ⇒ h 軸 10 值）。
3. **`CODEX-R2-P3-04` 不修**（每格建 analyzer 固定成本 110 次≈2.8s）：把 analyzer 快取回去
   會重現 R1 的 stateful 污染（那正是 R1 的 P1）。殘留 `B4-FACTORY-COST-1`。

## B-D4 新增殘留（皆已登記 `docs/IC_QUANT_GAP_REGISTRY.md` 之「G3-D2 實作批殘留」表）

`B4-COVERAGE-1`（coverage 條件以 warmup 代替）／`B4-SPECGAP-1`／`B4-TIMEOUT-1`（兩 timeout 為判斷值）
／`B4-ORPHAN-WORKER-1`（逾時 worker 仍會跑完，Python 無 thread cancellation）／`B4-FACTORY-COST-1`。

🔴 **`B1-VERIFY-1` 到期日逼近**：三值＝`cost`、觸發＝**收 epic 前**（＝B-D5 完工時）。
`tests/api` 與 `tests/governance` 各須再跑一次（上次跑的是 B-D3 以前的碼）。

## 環境現況

開放債為零；無未推送 commit。工作區僅餘 2026-09-01 遺留之兩個 `uat_samples/*拷貝*` 未追蹤檔、
`.claude/gate/*.sha` 未追蹤檔與 `market_data/*` 快取異動——**皆非主線產物，勿順手 commit**。
🔴 紀律不變：`pytest tests/governance` 小時級且不含量化測試，只有「動共用控制流**且**收 epic 前」才跑。

## 🔴 派工守檔（B-D4 期間實際踩到）

委員會會跑 `handoffs/20260905-gap3d2-b4-mutate.py`（**就地改生產碼再還原**）。
R1 期間有一次被中斷，`M8` 之 mutation 留在工作區未還原；我收件時以 baseline 對證發現，
並以 `git checkout --` 自版控還原（我方對該檔無未提交改動，故安全）。
⇒ **派工前**建 baseline：`git ls-files <目錄…> | xargs shasum -a 256 > .claude/gate/<batch>_baseline.sha`；
**收件後**先 `shasum -a 256 -c` 對證再讀 findings。
