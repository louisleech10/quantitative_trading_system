# Probe TODO — 末 Task 缺三欄（Composer C-4 / U3）

## §0
- 全域規則：探針用；末 Task 故意缺欄。

## §B
| Batch | 含 Task |
|---|---|
| B1 | 1.1, 1.2 |

## Phase 1 — 探針

### Task 1.1 — 有完整三欄
- SPEC ref：探針
- **驗證**：`grep -c "### Task" tests/gate_fixtures/todo_bad.md` == 2
- **邊界**：首 Task 三欄齊全；末 Task 故意缺欄
- 不可做：不得補末 Task 欄位

### Task 1.2 — 故意缺三欄
- SPEC ref：探針
- 目標：全域 grep 仍 PASS（現行繞過）。
