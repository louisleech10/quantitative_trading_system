# SPLITUNIFY SPEC v3/TODO v3 — Claude 自產獨立審查（R3，與三家平行）

依 `feedback_claude_own_version`。審查對象＝我自己寫的
`docs/SPLITUNIFY_SPEC.md`（sha256 `d851e56dc1bf…`）與 `docs/SPLITUNIFY_TODO.md`
（sha256 `a9ec9e1559a8…`），commit `7f040c93`。
🔴 **本檔之修法一律等 R3 收斂後才動檔**——三家正在讀這兩份的 `d851e56dc1bf…` 版本，
我現在改會讓他們引用的雜湊失效。

---

## CLAUDE-R3-P1-01

**斷言**: v3 之 Task 3.3 驗證命令指名的前端測試檔 `EventTablesPanel.test.tsx` **不存在**，該 nodeid 無法執行。

**碼證**: `ls frontend/src/components/ic-analysis/ | grep -i EventTablesPanel` → 只有 `EventTablesPanel.tsx` 與 `eventTablesPanelByLabel.test.tsx`（**沒有** `EventTablesPanel.test.tsx`）。SPEC Task 3.3「驗證」欄與 TODO Task 3.3「驗證」欄皆寫 `vitest run src/components/ic-analysis/EventTablesPanel.test.tsx`。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#d851e56dc1bf

修法（R3 後套用）：改為**新增** `frontend/src/components/ic-analysis/eventTablesPanelCapability.test.tsx`
（與既有 `eventTablesPanelByLabel.test.tsx` 之命名慣例一致），並在「修改檔案」欄列為新檔。
這是我在 R3 brief 的「我沒查的」第 2 條，派工後自己查掉的。

---

## CLAUDE-R3-P3-02

**斷言**: R3 brief 之 assumed 第 2 條（刪 `n_train`／`n_test`／`n_purged` 三鍵會打破 `test_gap3_split_blocked.py`）**經查不成立**——該測試只斷言 `execution_mode`，不碰三鍵。

**碼證**: `tests/momentum/event_samples/test_gap3_split_blocked.py:78` ＝ `assert res.summary["execution_mode"] == "event_study_only"`；全檔 `grep -n "n_train\|n_test\|n_purged"` 除該行外只命中 `summary={}` 的 stub（`:128`、`:150`、`:170`）。對照 `momentum/Analysis/event_samples/pipeline.py:731-736` 確認三鍵與 `"split": None`、`"execution_mode"` 同批寫入。

**來源摘要**: docs/SPLITUNIFY_TODO.md#a9ec9e1559a8

⇒ D2 之「刪三鍵」在 `tests/momentum/event_samples` 側**無既有測試阻擋**；
真正要盯的是前端 `EventTablesPanel.tsx:352` 與任何讀 `summary["n_test"]` 的 API 層 caller。
本條記為**已自證**，不需三家再答（若三家仍答，以本碼證覆核）。

---

## Verdict

**可進 B1**，但 `CLAUDE-R3-P1-01`（不存在的測試檔名）須在 R3 收斂時一併修掉——
它會讓實作端在 B3 跑一個不存在的 nodeid 而得到假綠或假紅。
