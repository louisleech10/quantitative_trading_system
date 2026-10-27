# Probe SPEC — 「待使用者確認：本任務無」誠實變體（修前誤擋、修後應 PASS）

## §RISK
- **大小**：小。
- RISK-HIT: none

## §A
- **待使用者確認**：本任務無

## §C
- 約束：grep rc=0。

## §G
- 行為 golden：修後 exit 0。

## §P
### Phase 1
**Task 1.1**
- **驗證**：`bash scripts/template_check.sh spec tests/gate_fixtures/spec_pending_none_variant.md; echo $?` → 修前 1、修後 0。
- **邊界**：措辭含「使用者」字樣。
- **存活至**：Phase 1 保留。
- **覆蓋風險**：無。
- 不可做：不得改寫成「待確認：無」以外未教學寫法。

## §V
- regex 變體探針。

## §R
- revert Task 2.4。

## §B 驗證運算預算
| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |
|---|---|---|---|---|---|
| FIX-BUDGET-1 | 無重型跑（範例 SPEC） | 不適用 | 不適用 | 0 秒（無重型跑） | 無 |

## §B 四項平衡實測
- N/A：範例 SPEC，不改計算路徑與使用者操作。

## §N
- 無。
