# Probe SPEC — 標題行含「已驗證」、事實在下層 bullet（ADV-CODEX-1 VERIFY 原文）

## §RISK
- **命中高風險原則**：不命中 (a)/(d)。
- RISK-HIT: none

## §A
- **已驗證事實 1 條**（附驗證方式）：
  - raw_data dtype 是 int64，DataFrame shape 已驗證。
- **待使用者確認**：待確認：無

## §C
- 約束：grep rc=0

## §G
- 行為 golden：exit == 0

## §P
### Phase 1
**Task 1.1**
- **驗證**：`grep x y; echo rc=0`
- **邊界**：空輸入；缺檔
- 不可做：不可放寬

## §V
- 測試：exit == 0

## §R
- revert commit

## §N
- 無
