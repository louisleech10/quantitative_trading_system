# IC Phase 1 B1 Contract DTO Handoff

## 正在做
- B1 已完成：SplitPlan、RowMaskPlan、SelectionScope、AlignmentSpec、validate_alignment 簽名。

## 待辦
- B2 eval_status 與 v1 序列化排除尚未開始。
- B3 validate_split_integrity / ic_split_adapter 尚未開始。

## 阻塞
- none

## 本次決策
- 契約只新增於 `momentum/core/contracts.py`，未接既有 IC 計算路徑。
- `validate_alignment()` 固定 `NotImplementedError("1-align 落地")`。
- Root `HANDOFF.md` 未覆蓋；依 headless 合約寫入本 append-only handoff。

## 踩坑提醒
- `grep -rE 'from api\.' momentum/` 無輸出，exit code 1 代表 0 match。
- 指定 pytest 四檔 17 tests passed。
