# HANDOFF — 當前任務狀態

**更新：2026-09-03 08:10｜狀態：`G3-D2` SPEC 延伸 D-001 **三家戳記齊全**（r4 synth stamps check PASS；composer 於 TODO r1 補蓋）；TODO 延伸 D-006 review r1→r2 兩輪寫回（含 D-001 D5 戳記後具名修訂：隨機對照組規則身分）；r3 閉合輪派工中（session `20260903-gap3d2todo-x-review-r3`）；使用者離線（委員共識決）**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | **進行中**：D-001（五 phase；戳記 `handoffs/reconcile/20260903-gap3d2-x-review-r4/synth.md`＋鏡像於 D-001 `## 戳記`；戳記後修訂段待 TODO 戳記輪一併收）→ D-006（15 Task／五批串行 B-D1→…→B-D5）→ review r3 中 |
| `G3-R13` | 新登記：C「收盤後決策」在 D2-2 不可表示；user-ruling 待使用者裁 |
| `G3-D1`／`D3`…`D17` | CLOSED；`KLINE-1` OPEN |

## 委員共識已決、待使用者醒後否決（白話：`白話說明/接下來要做什麼.md` 頭條）
(甲) C 名實：只改揭露＋`event_known_at_decision`；(乙) 契約 `decision_offset_bars` 保留必填恆 0；(丙) k 掃描軟上限 10（判斷值）。另：既有 9 批因無 `label_rule` 不能與隨機對照批比較（面向未來不溯及既往，§N 殘留）。

## 下一步
1. r3 回來：三家 R2 全 CLOSED＋D-001 修訂段 APPROVED＋無新 P0/P1 ⇒ TODO 戳記輪（stamp-target＝r3 synth；同時收 D-001 修訂段 APPROVED）；否則 r4。
2. 實作 B-D1（Claude 自任；D-006 D1.1–D1.6）→ 三家 code review 至閉合 → B-D2 → B-D3 → B-D4 → B-D5（串行；每批 review CLOSED 後 commit＋push）。
3. 派工：task-id＝session 大寫（batch 只能 `b<n>`／`x`）；派前 `gate.sh dispatch` mint token；三家齊交件之 round 用 `debt_clear.sh --round-id … --session … --lock <synth 之 sources.lock>` 銷帳；composer 失敗 ⇒ `--abandon --kind collection-failed` → mint → `ROUND_ID=<id> cx_run.sh composer …`。
4. commit 含 scope 外路徑須 `Governance-Scope:` trailer；`handoffs/` 為 gitignore。

## 已知紅／不要誤判
- 七個 ABANDONED rounds（composer 整晚 CLI 失敗）；產物齊全、completeness PASS；composer 天亮恢復。
- `reconcile_cluster_attribution_check.sh` 對前輪 ID（正文提及）誤報「未被引用」＝假警。
- `tests/api` 既有紅（G3-R11）；`test_ic_deep_analysis` 並行 ERROR 單跑綠；`tsc --noEmit` 8 行既有債。
- 具名殘留：`R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`G3-R13`、`GOV-DOC-STATUS-1`。
