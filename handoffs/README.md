# handoffs/ — 執行端交接檔（append-only）

對應 council review #2：根 `HANDOFF.md` 是共享可變單點，多執行端 / 背景任務 / resume
同時寫會互相覆蓋（本專案實測已發生）。解法 = 隔離。

## 規則
- **執行端（Codex / Cursor / agy）**：交接寫進**自己的檔** `handoffs/<YYYYMMDD>-<task-id>.md`，
  append-only，**絕不重寫或刪改根 `HANDOFF.md`**。
- **Claude**：維護根 `HANDOFF.md` 作為**索引 + 當前 active 狀態**；驗收後把該任務結論收斂進去。
- **唯讀 / 不改檔任務**：不建交接檔，改在收尾輸出 `HANDOFF_NOT_UPDATED: <原因>`。

## 單檔建議格式
```
# <task-id> — <一句話任務>
Agent: <codex|cursor|agy> | Base commit: <sha> | Time: <ts>
## 做了什麼 / 改了哪些檔
## 驗證（命令 + pass/fail）
## 待辦 / 阻塞
## 踩坑
```
