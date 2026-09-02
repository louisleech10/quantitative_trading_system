# HANDOFF — 當前任務狀態

**更新：2026-09-03 01:40｜狀態：`G3-D2` consult r1 已收斂（commit `eba9e389`）；D 延伸 `docs/GAP3_EVENT_UX_SPEC.D-001.md` 已起草（dext 機檢 PASS）；adversarial review r1 派工中；使用者離線（委員共識決）**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | **進行中**：consult 收斂 `handoffs/reconcile/20260903-gap3d2-x-consult-r1/synth.md`（本機；九群集）→ D-001 五 phase（D1 B→D2 A→D3 two_stage→D4 (c)＋k→D5 (b)）→ review session `20260903-gap3d2-x-review-r1`（brief `handoffs/20260903-GAP3D2-X-REVIEW-R1-BRIEF.md`）|
| `G3-R13` | **新登記**：C「收盤後決策」在 D2-2 不可表示；user-ruling 待使用者裁 |
| `G3-D1`／`D3`…`D17` | CLOSED；`KLINE-1` OPEN（可穿插） |

## 委員共識已決、待使用者醒後否決（白話：`白話說明/接下來要做什麼.md` 頭條）
(甲) C 名實：本票只改揭露＋`event_known_at_decision`，不改 D2-2；(乙) 契約 `decision_offset_bars` 保留必填恆 0（codex 異議＝optional）；(丙) k 掃描軟上限 10（判斷值）。

## 下一步
1. review r1 三家回來 → `reconcile_build … --mode review` → attribution／completeness → debt_clear → 原提出方閉合輪 → 三家 RECONCILE-STAMP（append 至 D-001 `## 戳記`）。
2. TODO（`templates/TODO_GENERATION_PROMPT.md`；配 `docs/GAP3_EVENT_UX_TODO.D-006.md`？——注意 TODO 延伸檔已 D-001…D-005 SUPERSEDED-BY-R，編號不重用 ⇒ 用 D-006）→ 三家 review → 實作（Claude 自任，逐 phase）→ 三家 code review。
3. 派工命名 `<YYYYMMDD>-gap3d2-<batch>-<kind>-r<N>`，**task-id＝session 大寫**；派前 `gate.sh dispatch` 先 mint token（hook 需 fresh token 才放 committee_run）；commit 含 scope 外路徑須 `Governance-Scope:` trailer（最末段）。

## 已知紅／不要誤判
- `handoffs/` 為 gitignore：委員產物與 reconcile 只在本機。
- consult round `6810e862` 被 committee_run 自動 abandon（composer ETIMEDOUT），composer 以 cx_run 同 round 重跑成功；reconcile 四來源 completeness PASS；`debt_clear` 對 ABANDONED 拒銷（已無 open debt，不擋派工）。
- `tests/api` 既有紅（G3-R11）；`test_ic_deep_analysis` 並行 ERROR 單跑綠；`tsc --noEmit` 8 行既有債。
- 具名殘留：`R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`G3-R13`、`GOV-DOC-STATUS-1`。
