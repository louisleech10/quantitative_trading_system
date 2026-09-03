# HANDOFF — 當前任務狀態

**更新：2026-09-03 06:20｜狀態：`G3-D2` SPEC 延伸 D-001 戳記兩家 APPROVED（grok／codex；composer 待補，連六次 CLI 失敗）；TODO 延伸 `docs/GAP3_EVENT_UX_TODO.D-006.md` 已起草（dext＋todo 機檢 PASS）；TODO review r1 派工中（session `20260903-gap3d2-todo-review-r1`）；使用者離線（委員共識決）**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | **進行中**：D-001（五 phase）review r1–r4 收斂＋戳記（r4 synth `handoffs/reconcile/20260903-gap3d2-x-review-r4/synth.md`，body sha `7dbcbd0c…`；鏡像於 D-001 `## 戳記`）→ D-006 TODO（14 Task／五批）→ review r1 中 |
| `G3-R13` | 新登記：C「收盤後決策」在 D2-2 不可表示；user-ruling 待使用者裁 |
| `G3-D1`／`D3`…`D17` | CLOSED；`KLINE-1` OPEN |

## 委員共識已決、待使用者醒後否決（白話：`白話說明/接下來要做什麼.md` 頭條）
(甲) C 名實：只改揭露＋`event_known_at_decision`；(乙) 契約 `decision_offset_bars` 保留必填恆 0；(丙) k 掃描軟上限 10（判斷值）。

## 下一步
1. TODO review r1 回來 → reconcile → 修訂 → 閉合輪 → TODO 戳記（三家；composer 若仍失敗＝待補）。
2. 實作 B-D1（Claude 自任；D-006 §B 順序）→ 三家 code review → B-D2／B-D3 → B-D4 → B-D5。🔴 composer 戳記未補前，D-001／D-006 不得宣稱 FROZEN；實作開工前須再試 composer 一次；仍失敗 ⇒ 具名 DEGRADE 並在白話頭條告知使用者（由使用者裁是否等 composer）。
3. 派工：task-id＝session 大寫；派前 `gate.sh dispatch` mint token；composer 失敗 ⇒ `debt_clear.sh --abandon --kind collection-failed` → mint → `ROUND_ID=<id> cx_run.sh composer …`。
4. commit 含 scope 外路徑須 `Governance-Scope:` trailer；`handoffs/` 為 gitignore。

## 已知紅／不要誤判
- rounds `6810e862`／`9f647a31`／`f00c8209`／`8e29036f`／`3e591c88`／`f10955ca`／`af94a45c` 皆 ABANDONED（collection-failed；composer）；產物齊全、completeness PASS。
- `reconcile_cluster_attribution_check.sh` 對前輪 ID（正文提及）誤報「未被引用」＝假警。
- `tests/api` 既有紅（G3-R11）；`test_ic_deep_analysis` 並行 ERROR 單跑綠；`tsc --noEmit` 8 行既有債。
- 具名殘留：`R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`G3-R13`、`GOV-DOC-STATUS-1`。
