# HANDOFF — 當前任務狀態

**更新：2026-09-03 03:10｜狀態：`G3-D2` D-001 延伸檔 review r1 三家收斂（16 findings 八群集全寫回，commit `f852e4db`）；review r2 閉合輪派工中（session `20260903-gap3d2-x-review-r2`）；使用者離線（委員共識決）**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | **進行中**：consult 收斂 → `docs/GAP3_EVENT_UX_SPEC.D-001.md`（五 phase D1 B→D2 A→D3 two_stage→D4 (c)＋k→D5 (b)）→ review r1 收斂（`handoffs/reconcile/20260903-gap3d2-x-review-r1/synth.md`，本機）→ **r2 閉合輪**（brief `handoffs/20260903-GAP3D2-X-REVIEW-R2-BRIEF.md`）|
| `G3-R13` | 新登記：C「收盤後決策」在 D2-2 不可表示；user-ruling 待使用者裁 |
| `G3-D1`／`D3`…`D17` | CLOSED；`KLINE-1` OPEN（可穿插） |

## 委員共識已決、待使用者醒後否決（白話：`白話說明/接下來要做什麼.md` 頭條）
(甲) C 名實：只改揭露＋`event_known_at_decision`，不改 D2-2；(乙) 契約 `decision_offset_bars` 保留必填恆 0；(丙) k 掃描軟上限 10（判斷值）。

## review r1 主要修訂（已入 D-001）
矩陣剔除 `{trigger_close, decision_bar_close}×open_to_close`（`zero_length_label_window`）＋差分 oracle 網格；Task 7.6 六鍵覆寫範圍；hash payload 以 D4.1 code fence 為唯一權威（覆寫 (iii)）；A 匯出標記 `search_unlabeled`（not_importable）；two_stage 須兩段；D5 envelope wire／四段驗收／`/case/import-events/random-control`／排除區間／分層配額／period 對齊；D4.3 種子表銜接清單；殘留三條（舊 B 批只讀、hash fence 分叉、真空約束）。

## 下一步
1. r2 回來：三家自家 R1 全 CLOSED 且無新 P0/P1 ⇒ 戳記輪（brief kind=stamp，`stamp-target: docs/GAP3_EVENT_UX_SPEC.D-001.md`，append 至 `## 戳記`）；否則修訂後 r3。
2. TODO 延伸檔（`docs/GAP3_EVENT_UX_TODO.D-006.md`；D-001…D-005 已 SUPERSEDED-BY-R，編號不重用）→ 三家 review → 實作（Claude 自任，逐 phase）→ 三家 code review。
3. 派工：task-id＝session 大寫；派前 `gate.sh dispatch` mint token；composer 常 ETIMEDOUT ⇒ 若再失敗：`debt_clear.sh --abandon --kind collection-failed` → mint → `ROUND_ID=<id> cx_run.sh composer …`。
4. commit 含 scope 外路徑須 `Governance-Scope:` trailer（最末段）；`handoffs/` 為 gitignore。

## 已知紅／不要誤判
- consult round `6810e862`、review round `9f647a31` 皆 ABANDONED（collection-failed；composer 網路逾時），產物齊全、completeness PASS。
- `tests/api` 既有紅（G3-R11）；`test_ic_deep_analysis` 並行 ERROR 單跑綠；`tsc --noEmit` 8 行既有債。
- 具名殘留：`R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`G3-R13`、`GOV-DOC-STATUS-1`。
