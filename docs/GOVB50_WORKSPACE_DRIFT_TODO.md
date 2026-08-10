# 票 B-50 — 執行端工作區污染偵測 TODO

FACT-KEY: govb50-workspace-drift-todo
LAST-RULED: 2026-08-10
RULED-BY: `20260810-govb1-x-review-r1` 必答 1（codex ＋ composer 兩家裁 **(B)**）

---

## §0  全域規則與約束

🔴 **本 TODO 是補正，不是事前規劃。**

主委在 `20260810-govb1-x-review-r1` 之前**先實作、先 commit、才派 adversarial**，
**沒有寫 TODO**。兩家皆裁 **(B)＝跳步**，並判定為 B8「用程序當藉口」的**鏡像**
——上次拿程序當藉口**少做**，這次拿「規格已存在」當藉口**跳過程序**。

**兩家給的往後可援引界線（逐字要點）**：

- codex：「只有在**動工前已存在、canonical、含任務拆解與驗收欄位**的 SPEC+TODO，才可沿用；
  **已核准 backlog／reconcile 不是自動等價物**。」
- composer：「收斂規格**可代 SPEC**，**不可**代 TODO ＋ 事前 review。」
- composer 對稱點：「在**把程序步驟當可選**，而非方向相同。」

**兩家亦皆裁：不撤回實作**（codex：「不必以破壞性 revert 代替流程補正」；
composer：「**不撤回** ②③ 實作」）⇒ 本 TODO 補齊追蹤面，實作由 r2 重審。

**規格來源**（本 TODO 不重述，只指回）：
`handoffs/20260801-GOV-AMEND-BACKLOG.md` 的 `## B-50 票 GOV-EXECUTOR-WORKSPACE-NOT-RESTORED` 節
（出自 `handoffs/reconcile/20260809-govb1-b5-review-r2/synth.md`，兩家 `RECONCILE-STAMP APPROVED`）。

---

## §B  批次執行策略

**單一批次、單一 Task。** 本票只有一個交付面（`committee_run.sh` 的偵測層），
無跨批依賴；`票 B-51`（允許清單）與 `票 B-53`（fail-closed）為**後續票**，不在本批。

依賴序：無前置。並發風險：無（`committee_run.sh` 於本 epic 期間無其他票在改）。

### Task 1.1 — 派工前後工作區快照比對

- **目標**：執行端把工作區留在壞狀態時**不得靜默**。依票的閉合條件逐字
  「**不必擋，但不得靜默**」⇒ 只回報、`return 0`、**不動 `rc_all`**。

- **修改檔案**｜**修改**：`scripts/committee_run.sh`
  （新增 `_ws_snapshot()`／`_ws_git_ok()`／`_report_workspace_drift()`；
  派工迴圈**前**取快照、wait 迴圈**後**比對）｜
  **新建**：`tests/governance/test_govb1_b50_workspace_drift.py`｜
  **只讀**：`handoffs/20260801-GOV-AMEND-BACKLOG.md`（B-50 節＝規格來源）、
  `AGENTS.md`／`.cursorrules`（執行端合約，禁 `git checkout`／`git stash` 的出處）。
  **既有 caller**：Claude 主控端 → `committee_run.sh`。

- **改法**：
  1. `_ws_snapshot` ＝ `git -c core.quotePath=false status --porcelain -z` → NUL 轉行 → `sort`
  2. 形態② ＝ 派工前 `^( M|M |MM| T) ` 之路徑，派工後**不在**路徑集合內
     （逐筆 **exact record** 比對 `grep -qxF`）
  3. 形態③ ＝ `git diff -U0` 之**新增行**含 `MUTATION`
  4. ②③ 皆未命中 ⇒ 壓成**一行**低噪摘要；命中才用紅色告警並展開明細
  5. git 不可用 ⇒ 輸出 checker-unavailable receipt，**不得靜默**

- **驗證**（`venv/bin/python -m pytest tests/governance/test_govb1_b50_workspace_drift.py -q` 全綠）：
  - `T-B50-U1`：形態② 觸發，含**前綴路徑**反例（before=` M a`；還原 `a` 並新增 `a-new`）
  - `T-B50-U2`：形態③ 觸發；未追蹤檔提及 `MUTATION` **不**誤觸
  - `T-B50-U3`：非 ASCII 路徑／含空白路徑之形態② 不得漏報
  - `T-B50-U4`：checker 不可用 ⇒ 留 receipt 且 rc=0
  - `T-B50-U5`：正常輪（僅新增未追蹤檔）⇒ stderr **恰一行**低噪摘要
  - `T-B50-N1`：無變動 ⇒ **完全安靜**（反空轉：否則「永遠在叫」會讓上列全綠）
  - `T-B50-N2`：既有 ambient M 單獨存在 ⇒ 不誤報
  - `T-B50-C1`：回報函式**任何輸入**皆 rc=0（污染 `rc_all` 比靜默更糟）
  - `T-B50-C2`：快照取在**派工之前**（順序錯 ⇒ 比對恆空）
  - `T-B50-C3`：`grep -qxF`／`--porcelain -z`／`core.quotePath=false` 為不可刪 invariant
  - **mutation N/A**：整合路徑，以上述正反 rc 對照覆蓋。

- **邊界（≥2）**：
  ① git 不可用 ⇒ receipt，**不得**當成「乾淨」
  ② 已 dirty 之路徑**內容再變**（status 行不變）⇒ **本層看不到**，屬宣告上界非缺陷

- **不可做**：
  - 不得改成**硬擋**（本票閉合條件逐字「不必擋」；改成擋是超出本票）
  - 不得為涵蓋形態① 而自行擴 scope（需 brief 攜帶「允許改動清單」，與 `票 B-51` 同源）
  - 不得刪 `core.quotePath=false`（中文路徑會被轉義成 `\NNN` 而對不上）
  - 不得把 `grep -qxF` 退回 `grep -qF`（`CODEX-R1-P1-02` 的前綴漏報會復發）

- **存活至**：`票 B-51` 的允許清單落地並與本層合併時重評。

- **覆蓋風險**：🔴 **有**——`票 B-51`（brief 攜帶「允許改動清單」）落地後，
  形態① 會由本層的「只列不判」升級為真判定，屆時
  `_report_workspace_drift` 的輸出契約與 `test_form1_limitation_is_declared_not_silently_dropped`
  **都會被覆蓋**（後者的存在理由是「形態① 尚未實作」，B-51 完成即應退場）。
  `票 B-53`（fail-closed）不覆蓋本層——那是主委產出端，與執行端偵測不同路徑。

## 🔴 誠實邊界（不得於任何文件宣稱已閉合）

| 形態 | 狀態 |
|---|---|
| ② ambient M 被還原成 HEAD | ✅ 閉合 |
| ③ 工作區殘留 `MUTATION` 標記 | ✅ 閉合（啟發式；以 `git diff` 新增行為界） |
| ① 改動逸出「該輪允許清單」 | 🔴 **未閉合**——brief 無此欄位；只列變動、不判違規 |
| 既有 dirty path 的內容增量 | 🔴 **偵測不到**——status 集合不變；宣告上界 |
| 歸因（executor vs coordinator） | 🔴 **無 provenance**——主控端自己動的檔也會被列出 |
| 效能（status 集合上的重複 grep） | 🔴 codex 列為後續可量測項；**本輪未捏造門檻**，留 `票 B-37` |

⇒ `TICKET-STATUS` 維持 **OPEN**；任何文件不得宣稱 `票 B-50` 已完成。
