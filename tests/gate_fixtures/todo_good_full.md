# Probe TODO — 合規正樣本

## §0
- 只加強機檢；不碰 momentum/api/frontend/data_cache。

## §B
| Batch | 含 Task |
|---|---|
| B1 | 1.1 |

## Phase 1 — 正樣本

### Task 1.1 — 合規 Task
- SPEC ref：F-2
- 目標：per-Task 三欄齊全。
- **驗證**：`bash scripts/template_check.sh todo tests/gate_fixtures/todo_good_full.md; echo $?` → 0
- **邊界**：單 Task 亦須三欄
- **存活至**：批次 B2 完工後保留。
- **覆蓋風險**：無。
- 不可做：不得刪 §0/§B
