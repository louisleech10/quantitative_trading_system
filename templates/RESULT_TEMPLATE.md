# RESULT — <task-id>（執行端收尾，結構化欄位）

> 誠實邊界：checker 只讀下方枚舉欄位，不猜自然語言段落。PASS 須有 receipt 支撐。

## 結構欄位（必填，枚舉值）

STATIC_CHECK=NOT_RUN
RUNTIME_CHECK=NOT_RUN
MUTATION_CHECK=NOT_RUN
RECEIPTS=[]
OPEN_PENDING=[]

## 枚舉允許值

- `STATIC_CHECK` / `RUNTIME_CHECK` / `MUTATION_CHECK`：`NOT_RUN` | `PASS` | `FAIL` | `N/A:<reason>`
- `RECEIPTS`：JSON 陣列，元素為 receipt_id 或 `handoffs/run_receipts/<file>.json` 路徑
- `OPEN_PENDING`：JSON 陣列，元素為 pending_id（無則 `[]`）

## 規則

- `RUNTIME_CHECK=PASS` 時 `RECEIPTS` 不得為空
- `MUTATION_CHECK=NOT_RUN` 時，同 task 不得宣稱「已驗 / DONE / 全綠」等 operational 極性
- 自然語言摘要可寫在下方，但判定以結構欄位為準

## 摘要（可選）

<!-- claim-context: discussion -->
（討論、traceback 摘錄等非 operational 狀態文字）
