# HANDOFF — 當前任務狀態

**更新：2026-09-04｜狀態：`G3-D2` 灰色項目——SPEC 延伸 D-001 與 TODO 延伸 D-006 v2 三家戳記 FROZEN；**使用者 2026-09-04 已放行實作**。實作交接＝`docs/GAP3D2_IMPL_HANDOFF.md`（唯一入口）。下一件＝**B-D0（Task D4.1 取價修法）**。**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | **實作中（待開工 B-D0）**：五批串行 B-D0→B-D1→B-D3→B-D4→B-D5，每批三家 code review 至閉合；收據填 `docs/GAP3D2_IMPL_HANDOFF.md` §5 |
| `G3-R13` | 新登記：C「收盤後決策」在 D2-2 不可表示；user-ruling 待使用者裁 |
| `G3-D1`／`D3`…`D17` | CLOSED；`KLINE-1` OPEN（可穿插） |

## 新 session 開工指令（使用者貼的 prompt 已含；此處備份）
1. 稽核本檔＋`docs/GAP3D2_IMPL_HANDOFF.md` vs repo 實況（`git status`、兩延伸檔 `## 戳記`、`reconcile_stamps_check.sh`）。
2. B-D0：讀 D-006 Task D4.1＋D-001 Phase D0／D4.1 → 實作 → mutation 自證 → golden → review brief → 三家 review 至閉合 → commit＋push → 填 §5 → B-D1。

## 已知紅／不要誤判
- 派工命名／gate／外部故障處置／commit trailer／白話守衛：見 `docs/GAP3D2_IMPL_HANDOFF.md` §3。
- `tests/api` 既有紅（G3-R11）；`test_ic_deep_analysis` 並行 ERROR 單跑綠；`tsc --noEmit` 8 行既有債。
- 具名殘留：`R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`G3-R13`、`GOV-DOC-STATUS-1`；9/1 之 9 批事件檔為測試檔（使用者確認）。
