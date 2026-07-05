# Probe SPEC — §A 未解待確認（應 FAIL，facts-resolved 正例）

## §RISK
- **大小**：小。
- RISK-HIT: none

## §A
- **待使用者確認**（未確認前不得實作）：
  - UI 預設並行度是多少？
  - 覆蓋語義選 A 還是 B？

## §C
- 約束：grep rc=0。

## §G
- 行為 golden：本探針預期 exit 1。

## §P
### Phase 1
**Task 1.1**
- **驗證**：`bash scripts/template_check.sh spec tests/gate_fixtures/spec_pending_unresolved.md; echo $?` → 1。
- **邊界**：無「已確認」亦無「待確認：無」。
- 不可做：不得偷填已確認。

## §V
- 探針維持 FAIL。

## §R
- N/A

## §N
- 無。
