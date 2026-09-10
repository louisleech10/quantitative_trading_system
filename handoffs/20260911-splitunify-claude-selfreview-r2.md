# SPLITUNIFY SPEC v2/TODO v2 — Claude 自產獨立審查（R2，與三家平行）

依 `feedback_claude_own_version`：主委不只編排，先自產完整一版，再與三家互審。
**審查對象＝我自己寫的** `docs/SPLITUNIFY_SPEC.md`（sha256 `84ab732b021b…`）與
`docs/SPLITUNIFY_TODO.md`（sha256 `7d6d4f0c4e90…`），commit `7fd0a255`。
逐條附碼證（檔案:行號），皆為本輪實讀，非引用。

---

## CLAUDE-R2-P1-01

**斷言**: R2 brief 的 assumed 第 1 條（「無 universe ⇒ event-study-only 會讓 `event_forward_return_table` 退回全樣本而被誤讀為 OOS」）**是錯的**——該表早已完整支援 `event_split_plan=None`，且是往**更保守**的方向降級，不是退回全樣本。

**碼證**: `momentum/Analysis/event_samples/tables.py:130-149` 之 `_common_constraint_block`：`event_split_plan is None` ⇒ `formal_pooled_inference_allowed=False` 且 `reason="no_event_split_plan"`；`:251` `"ci": "unavailable" if event_split_plan is None else …`；`:161-166` 之 docstring 逐字「`event_split_plan` 可為 `None`＝**未執行切分**之 Task 1.12 路徑」；`pipeline.py:55` 之 `split_plan: Optional[EventSplitPlan]  # None ＝ Task 1.12 之 event-study-only`。另 `:194-207` 兩道守衛明文禁止「以空 plan 冒充未切分」——正好是本票要防的反向錯誤。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

影響：**這條對 v2 是好消息**——C-0 決議③（無 canonical universe ⇒ 明示 event-study-only）
所需的下游承接**已經全部存在**，Task 3.3 真的只是「分派到既有分支」，不是新造機制。
修法：把本碼證寫進 SPEC Task 3.3 的「實作要點」，讓實作端不必重新確認；
並把 R2 brief 那條 assumed 標為**已自證否**（我在派工後自己查的，不等委員回答）。

---

## CLAUDE-R2-P2-02

**斷言**: SPEC C-5／TODO Task 2.2 要求 `summary` 之 `degraded` 沿用 `_degraded_flags`，但在多 symbol fail-closed（Task 3.2）之後 `n_symbols` 恆為 1 ⇒ `single_symbol` 旗標**恆亮**，該旗標退化為常數、失去鑑別力。

**碼證**: `momentum/Analysis/event_samples/event_split.py:22-33` 之 `_degraded_flags`：`n_symbols == 1` ⇒ append `"single_symbol"`。唯一下游消費者＝`tables.py:138` 之 `allowed = bool(event_split_plan is not None and not degraded and …)` ⇒ `degraded` 非空即 `formal_pooled_inference_allowed=False`。`grep -rn "single_symbol" momentum api frontend/src` 除契約檔與上述兩處外無其他消費者。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

判定：**不是 bug，但值得具名**。旗標恆亮的效果是 `formal_pooled_inference_allowed` 恆 False，
方向是**保守**的（不會讓不該做的 pooled inference 通過），故不改行為。
但 SPEC 應明寫這件事，否則實作端看到「恆亮的旗標」可能誤以為是自己寫壞而去「修正」它。
修法：Task 2.2 之實作要點第 6 點補一句「多 symbol fail-closed 期間 `single_symbol` 恆亮，
這是預期的；`formal_pooled_inference_allowed` 因此恆 False，方向保守，不得為了讓它變 True 而放寬」。

---

## CLAUDE-R2-P2-03

**斷言**: TODO Task 1.3 之既有紅 nodeid 清單在 B1 凍結、B3 才用，中間若有任一條被修好（本票副作用或 `REDSWEEP`），B3 的「集合相等」檢查會判紅，而該紅**不是迴歸**。

**碼證**: TODO Task 1.3「邊界」欄②「清單中任一條變綠 ⇒ 必須主動移出」；Task 3.1「驗證」欄 (B)「既有紅之 FAILED nodeid 集合與該清單**集合相等**（多或少皆判紅）」。兩處合起來使「變綠」與「新壞」在 rc 上不可區分。

**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90

修法：把 (B) 之判準改為**方向性**而非集合相等——
「清單集合 ⊇ 實際 FAILED 集合」（只准變短，不准變長）為綠；
變短時額外要求 commit 訊息具名哪一條變綠並同步移出清單。
這樣「修好一條」是綠、「弄壞一條」是紅，兩者可區分。
現行寫法把兩件事混成同一個紅，會逼實作端在真的修好東西時去改驗收條件，
那正是「測試遊戲化」的入口。

---

## CLAUDE-R2-P3-04

**斷言**: SPEC §G 之 G-5 四項（逐 row test fingerprint／逐 event assignments 與 purged IDs／answer-window 完整性／leakage negative case）只寫了名字，沒有給任何一項的 oracle 與可證偽方式，屬「驗證欄不可證偽」之邊緣。

**碼證**: `docs/SPLITUNIFY_SPEC.md` §G 之 G-5 條目全文僅一句列舉；對照 G-1／G-2／G-3b 皆有具體比對方式（集合相等、sha256、獨立 oracle）。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

修法（我的提案，待三家覆核）：
- 逐 row test fingerprint ＝ `sha256` of sorted `feature_index[test_plan.row_index]` 之 int64 ms JSON。
- 逐 event IDs ＝ `assignments` 與 `purged` 之 event_id 集合各自 `sorted` 後 `sha256`。
- answer-window 完整性 ＝ 對每個 test 段事件斷言 `label_end_ms <= test 段最後一根之 close_ms`。
- leakage negative case ＝ 刻意把一個 train 事件的 `label_end_ms` 推進 test 段，
  斷言它被歸入 `purged`（不是 train）。

---

## 已被本輪查證**否證**的 R2 brief 項（誠實記錄）

- brief assumed 第 1 條：**已自證否**，見 `CLAUDE-R2-P1-01`。派工後我自己查了 `tables.py`，
  發現前提不成立。三家若照該假設回答，我會以本碼證覆核而非照單全收
  （`feedback_no_governance_tooling_selfloop` 之教訓：錯前提被委員照單全收會放大錯誤）。
- brief「我沒查的」第 3 條（`single_symbol` 旗標下游有無消費者）：**已查**，
  唯一消費者是 `tables.py:138`，見 `CLAUDE-R2-P2-02`。

---

## Verdict

**v2 可進 B1，但建議先吸收 P2-03（驗收判準改方向性）**。
P1-01 是好消息（C-0 決議③ 的下游承接已存在）；P2-02 與 P3-04 是文件補強，不擋施工。
P2-03 若不改，B3 會在「有人修好既有紅」時誤紅，並誘導實作端改驗收條件。
