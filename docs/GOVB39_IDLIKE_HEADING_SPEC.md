# B-39 — id-like heading 誤判修正 SPEC（草案 R1）

**狀態**：DRAFT — 待雙家族審查
**票**：`票 B-39 GOV-IDLIKE-HEADING-FALSE-POSITIVE`（`handoffs/20260801-GOV-AMEND-BACKLOG.md`）
**開票依據**：`handoffs/reconcile/20260806-govamend-x-consult-r1/synth.md` 群集 `G-2`
（`CODEX-R21-P0-01` ＋ `GROK-R21-P0-01`，兩家皆列 BLOCKING）

## §0 全域規則與約束

### §0.A 數值影響

N/A — 純字串／標題判定，不涉數值計算、不動 `data_cache/`、不影響 ML 或回測路徑。

### §0.B 不變式（違反即 BLOCKING）

1. **放寬不得漏收畸形 canonical-like heading**（例 `## CODEX-R99-P9-01`，`P9` 非法）。
2. **不得以「禁用 `###`」作為修法**——那是把摩擦轉嫁給每位委員與每份 brief，不修根因。
3. 既有收斂檔**一律不改**（forward-only）。
4. **禁改測試斷言以取得綠燈**；**禁恆真斷言**。

## §C 約束

| # | 約束 | 來源 |
|---|---|---|
| C-1 | bash 3.2 相容；`completeness_check.sh` 為熱路徑，**禁新增 subprocess 呼叫** | 既有檔頭約束 |
| C-2 | **不得改 canonical schema**（`^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$`）——本票只改「誰進通道」 | §0.B-1 |
| C-3 | **不得動 body-hash 範圍**（`H2_LINE_RE` 用 `##(?!#)`）——那是另一個 Oracle | §V 邊界 |
| C-4 | forward-only：既有收斂檔一律不改 | 使用者 2026-08-06「釘死不動」 |
| C-5 | **淨摩擦須為負**（見下方定義）——不是「增量為零」 | 使用者 2026-08-06 更正 |

🔴 **C-5 的更正紀錄（主委錯誤，具名保留）**

本 SPEC 初版寫「摩擦增量須為 **0**」並掛在使用者名下。**兩處都錯**：

1. **使用者未說過此話**——屬主委自行加碼後冒充使用者裁定。
2. **該約束自我矛盾**：若增量必須為零，則**任何機械檢查都不得新增**，
   而使用者早已定死「**工具必須自帶強制機制，不准靠紀律和記憶**」。
   ⇒ 該約束若生效，會擋掉本 epic 幾乎全部工作。

**使用者原話（2026-08-06）**：

> 「我沒說要摩擦增為 0 吧，且針對摩擦增量需為 0 就太絕對。
> **你多做一件機械檢查，是多做一件事，但後面可以省掉一直被退件重來
> 或省掉浪費好幾輪重複做，這是摩擦增加還是減少？**」

**⇒ 正確判準＝淨摩擦**：

```
淨摩擦 = 新增的每次成本 × 發生次數  −  省下的重工成本 × 避免的次數
```

**本票的試算**：

| 項 | 值 |
|---|---|
| 新增每次成本 | 一次字串判定（在既有迴圈內，無新增 I/O） |
| 發生次數 | 每次委員交件（`--single`）與每次收斂 |
| 省下的重工 | **整輪作廢重跑**（一輪＝2～3 家委員） |
| 已避免次數 | **3**（2026-08-06 實證，皆可由 audit／runlog 定位） |

⇒ **淨摩擦顯著為負。**

### §0.C 本批不做

- `B-38`（零 findings 判 vacuous）——同族但根因不同，**不合併**。
- 群集 ID 登記（`B-26` 缺口）——另票。
- 委員範本措辭調整。

## §RISK 風險分級

RISK-HIT: b

- **(b) 跨模組／共用路徑**：`completeness_check.sh` 由 `reconcile_build.sh`／`debt_clear.sh`／
  `gate.sh` 共用，且 `cx_run.sh` 於交件當下呼叫 `--single`。改動面波及**每一輪委員派工**。
- **(a) 數值** 不命中；**(c) 多 phase／難回退** 不命中（單函式、單 commit 可回退）；
  **(d) ML／回測** 不命中。

## §A 問題陳述

`completeness_check.sh:60` 的 `HEADING_LINE_RE='^[[:space:]]*#{2,6}[[:space:]]...'`
把 `##`～`######` **全部**送進 finding-ID 通道；不符 canonical schema 者 hard-fail。

**主委原診斷「凡 `###` 必 fail」過寬**，已由 `GROK-R21-P0-01` 三探針推翻：

| 探針 | rc | 判定路徑 |
|---|---|---|
| `### G-1 extra` | **1** | id-like（大寫＋連字號＋數字）⇒ 進 finding 通道 ⇒ 非 canonical ⇒ fail |
| `### 另外要回答的` | **0** | 非 id-like ⇒ 未進 finding 通道 |

⇒ **根因＝id-like 判定過寬**。

**實證 3 輪作廢**（2026-08-06）：`GOVB35-SPEC-REVIEW`（`## OUT-OF-SCOPE`）／
`GOVB35-SPEC-REVIEW2`（`### OUT-OF-SCOPE`，**委員照主委 brief 指示所寫**）／
`GATELEX-REDESIGN`（三家皆把 brief 小節代號寫成 `##`）。

**待使用者確認：本任務無。** 全部事實可由 repo 程式碼與 audit／runlog 導出。

## §P Phase 與依賴

**Task 1.1 — 結構標題 allowlist 與 finding 通道分流**
- 產出：`completeness_check.sh` 內新增結構標題 allowlist；
  只有 **canonical** 或 **近似 canonical 的畸形** 進入 finding 通道。
- 依賴：無。
- **存活至**：長期（本票唯一交付物）。
- **覆蓋風險**：`B-38` 若採「`FINDINGS_COUNT: 0` 明示欄」修法，會動到同一函式的相鄰分支；本 Task 須讓兩者可各自獨立測試（`pytest -k` 分別選中），不得共用同一旗標。
- **驗證**：§V 六項全過；`pytest tests/governance -q` rc **== 0** 且測試數 **不減少**。
- **邊界**：只改「哪些標題進 finding 通道」；**不改** canonical schema 本身、不改 body-hash 範圍。
- **不可做**：不得以停用 `HEADING_LINE_RE` 或全面放行 `###` 達成；不得改既有收斂檔。

**Task 1.2 — 反向 mutation 測試**
- 產出：mutation 測試，移除 Task 1.1 修法後 §V 項目 1／2 須轉紅。
- 依賴：Task 1.1。
- **存活至**：長期（回歸保護）。
- **覆蓋風險**：無後續 Phase 覆寫；若 `B-38` 改動同函式，本測試須仍為紅／綠可鑑別。
- **驗證**：隔離副本跑 `completeness_check.sh --single`，未突變 rc **== 0**、移除 allowlist 分支後 rc **== 1**；兩次都要貼出。
- **邊界**：只針對本票修法做 mutation，不擴及其他 Oracle。
- **不可做**：不得用「刪掉斷言」當 mutation（那證明不了修法有效）。

## §V 驗證策略與邊界

| # | 待驗項目 | 期望值 |
|---|---|---|
| V-1 | `### 另外要回答的`（中文子標題） | rc **== 0** |
| V-2 | `### 逐項核對表`（結構標題） | rc **== 0** |
| V-3 | `## CODEX-R99-P1-01`（合法 canonical） | rc **== 0** |
| V-4 | `## CODEX-R99-P9-01`（**畸形 canonical-like**，`P9` 非法） | rc **≠ 0** ← **放寬不得漏收** |
| V-5 | `## OUT-OF-SCOPE` 作 h2 | 由審查裁定：維持拒收或改列結構標題。**須明寫選擇與理由** |
| V-6 | mutation：移除修法後 V-1／V-2 | **須轉紅** |

**邊界**：本票只驗 heading 分流；不驗 body-hash、不驗 dropped-ID、不驗 lock——那些既有 Oracle 不動。

## §R 回退

單一 commit、單一函式 ⇒ `git revert <commit>` 即可。
回退代價＝恢復 3 輪作廢的風險，**不會**造成資料或既有產出損壞。

## §N N/A 登記

| 項目 | 判定 | 理由 |
|---|---|---|
| §0.A 數值影響 | **N/A** | 純字串判定 |
| ML／回測正確性 | **N/A** | 不觸 `momentum/`、`data_cache/` |
| 前端／API | **N/A** | 不動 `api/`、`frontend/` |
| 資料遷移 | **N/A** | 無持久化格式變更 |
| 效能 | **N/A** | 判定在既有迴圈內，無新增 I/O |

## §G Golden 狀態

**filled** — golden ＝ §V 六項的期望 rc 表；其中 V-4／V-6 為**防退化樁**，
任一轉綠即代表修法過寬或 mutation 失效。既有 golden 檔一律不動。
