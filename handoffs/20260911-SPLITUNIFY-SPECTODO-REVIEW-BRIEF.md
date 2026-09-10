# SPLITUNIFY — SPEC v1 ＋ TODO v1 adversarial 審（R1）

brief-kind: review
task-id: 20260911-SPLITUNIFY-X-REVIEW-R1
findings-round: R1

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0（挑戰前提）與 canonical finding
四欄格式**全文照做**；findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`，結尾附 **Verdict**。
審查對象＝`docs/SPLITUNIFY_SPEC.md` 與 `docs/SPLITUNIFY_TODO.md`（commit `08391e4c`）。
**禁改碼**；碼證以檔案:行號指名。

## 這是什麼

兩套切分（`SplitPlan` 走 IC 主線、`EventSplitPlan` 走事件路徑）同一批事件會給出**兩個不同的
驗證段**（實測 31 vs 33）。使用者 UAT 時無法判斷哪一個是結論依據。本票統一之。
切法已由前一輪 consult 三家收斂（`handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`）：
D1 時間切分為 canonical 權威、事件切分改為投影；D2 多 symbol fail-closed；D3 三態投影；
D4 GAP-3 走 `D-002` 延伸檔；D5 大票四批。

**本輪不是重開 D1–D5**，除非你有 consult 當時沒有的碼證。本輪要打的是
**SPEC／TODO 有沒有把 D1–D5 正確地落成可執行、可證偽的工程計畫**。

## 現況碼證（我實跑，逐條可複驗）

fact-verified: `EventSplitPlan` 生產端 7 檔（`baseline.py`／`event_split.py`／`ic_feed.py`／
`pattern_bridge.py`／`pipeline.py`／`tables.py`／`types.py`）、測試端 6 檔
← `grep -rln EventSplitPlan momentum api tests`。

fact-verified: `SplitPlan` 已有 `symbol: Optional[str]` 欄
← `momentum/core/contracts.py:390`。

fact-verified: `split_per_symbol` **已存在且已在生產使用**，但只在
`analyze_cross_sectional` 分支（`ic_filter_orchestrator.py:903`，回傳 per-symbol
`(train_plan, test_plan)` pair 串）——**事件路徑不走它**。

fact-verified: 事件路徑走 `analyze` → `_build_holdout_split_plan`
（`ic_filter_orchestrator.py:561`，docstring 逐字「建立**單幣** chronological holdout
train/test SplitPlan」，`ic_filter_orchestrator.py:1256` 呼叫），
其 `index_kind="positional"`、`row_index` 為對 `features_df` 的**位置索引**
（`ic_filter_orchestrator.py:604-611`）。

fact-verified: 多 symbol 非等價已有實跑 receipt
`handoffs/run_receipts/20260910T150504Z-splitunify-multisymbol.json`
（全域切法 12 列 vs per-symbol 8 列，4 列只在全域出現）。

fact-verified: 既有紅基準 `tests/momentum/Analysis` 20 failed / 1615 passed，
**非本票造成**（見 `HANDOFF.md`「既有紅盤點」）。

## 本 brief 之 assumed（請正面打）

assumed: `_build_holdout_split_plan` 的 `index_kind="positional"` 可以在投影函式內
安全地經 `features_df.index` 還原成時間戳，且事件時間戳與該 index 的對齊語意唯一。
← 否證觀測：某情境下同一位置索引在事件端與特徵端指到不同時間（例如特徵端被裁過頭尾）。
／我跑了：**沒跑**，只讀了 `_time_bounds_for_rows` 與 `holdout_test_row_index` 的簽名。
（EVTALIGN 票曾做過「特徵比 K 線長就裁頭尾」的處理，這正是可能的 off-by-N 來源。）

assumed: `baseline.py`／`pattern_bridge.py` 只是**型別**依賴 `EventSplitPlan`，
換成投影產物後數值不變。
← 否證觀測：接線後 baseline OOS AUC 或 pattern_bridge 輸出改變。／我跑了：**沒跑**。

assumed: TODO 之 B3 驗收「`tests/momentum/Analysis` failed 數 <= 20」足以擋住迴歸。
← 否證觀測：本票改壞了某條，同時另一條既有紅偶然變綠，總數仍 <= 20 ⇒ 假綠。
／我跑了：**沒跑**。這條我自己就覺得可疑，請正面打（必答 5）。

## 🔴 我沒查的

| claim | observable_if_false | reason_code |
|---|---|---|
| `pattern_bridge.py` 是否讀 `EventSplitPlan` 的 `clusters` 語意而非只讀成員集合 | 接線後 pattern 輸出改變 | cost |
| GAP-3 UAT 清單（B26–B34）是否有項目直接驗事件切分邊界 | 統一後既有 UAT 項失效 | cost |
| `event_split.py` 現行「緩衝 bars」與 `purge+embargo` 的實際大小關係 | 投影後隔離**變鬆**而非變嚴 | cost |

## 🔴 必答（每題給明確立場＋碼證，不得只列選項）

1. **投影的索引語意**：SPEC C-3／TODO Task 2.1 把投影簽名定為
   `(train_plan, test_plan, event_index) -> EventSplitPlan`。但 `SplitPlan.row_index` 是
   **positional**（`ic_filter_orchestrator.py:604`）。這個簽名夠不夠？是否必須同時傳
   `features_df.index`（或改傳已還原的時間戳陣列）？請給**確定的簽名**。

2. **三態的邊界定義**：SPEC 說「∈train ⇒ train、∈test ⇒ test、皆不在 ⇒ purged」。
   事件的時間戳若**不落在任何特徵列上**（事件在兩根 bar 之間）該歸哪一態？
   TODO Task 2.1 的邊界欄沒寫這條——是漏了，還是上游保證不會發生？請指名碼證。

3. **fail-closed 是否過嚴**：`split_per_symbol` 已在生產（`:903`）。
   B3 直接改走 per-symbol 投影、而非先 fail-closed，是否**更省一次改寫**？
   代價是什麼？請給立場（維持 fail-closed／改為直接支援），並說明你的判準。

4. **golden G-3 的設計**：TODO Task 2.2 要凍結「新舊兩套 producer 的差集」，但
   SPEC C-2 已宣告兩者**不等價**。凍結一份「預期有差」的 golden 是有效防護，
   還是把已知錯誤合法化？若無效，你的替代方案是什麼？

5. **B3 驗收判準**：「failed 數 <= 20」是聚合期望數，`docs/` 的 brief 紅線明文禁止
   驗收寫聚合期望數。請給一個**逐條可證偽**的替代判準（例如 `--deselect` 既有紅清單後
   要求 rc=0，或以 `-p no:randomly` 固定順序後逐檔比對）。指名可執行命令。

6. **批次切分**：B1（文件＋枚舉，不動生產碼）是否值得獨立一批？
   若你認為應併入 B2，說明併了以後 review 的可審性損失在哪。

7. **mutation 表夠不夠**：TODO §D 只列 3 條（二態化／拿掉 fail-closed／首 symbol 冒充）。
   請補你認為缺的，每條寫「改壞哪一行 → 哪個測試會紅」。

8. **漏掉的消費者**：7 個生產端檔中，SPEC／TODO 只點名了 `pipeline.py`、`orchestrator`、
   `baseline.py`、`ic_feed.py`、`tables.py`。`pattern_bridge.py` 與 `event_split.py`
   的處置是否寫得夠明確？有沒有第 8 個我沒找到的消費者？

## 停輪條件

① 必答 1–8 皆有明確立場（不得只列選項）；② 必答 1／2／5 有具體檔案:行號或可執行命令；
③ 三家若分歧，各自寫出**判準**（看碼證不數人頭），我依較嚴版本收斂並具名殘留。
④ 禁以「三家零 finding」當停輪理由——零 finding 須走 sentinel 契約。

## ⚠️ 前置

- **禁改碼**、禁改 `docs/SPLITUNIFY_*.md`（findings 寫進你自己的交件檔）。
- 不得跑 `pytest tests/governance`（小時級）。
- 既有紅基準見上方 fact-verified，不得把它們當成本票的 finding。
- 收尾清 /tmp workdir（保留 claude-501）。

## 產出

canonical 四欄 findings ＋ **Verdict**（一句話結論＋是否可進 B1）。
