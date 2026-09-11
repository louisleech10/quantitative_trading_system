# SPLITUNIFY 閉合確認輪（原提出方重跑自己的反例）

brief-kind: review
task-id: 20260911-SPLITUNIFY-B7-REVIEW-R1
findings-round: R1

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；
findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`，結尾附 **Verdict**。**禁改碼**。
（task-id 用 `b7` 是命名規約限制——`batch` 只准 `b<數字>`；本輪不是新批次，是**閉合確認**。）

## 為什麼有這一輪（主委的錯，逐字承認）

本票**每一個批次邊界**都是在至少一家明寫「不可進」的情況下跨過去的，且**從未讓原提出方回來確認閉合**：

| 批次邊界 | 當時寫「不可進」者 | 主委做了什麼 |
|---|---|---|
| B1＋B2a → B2b | codex | 直接進 B2b |
| B2b R3 → B2c | codex、grok | 直接進 B2c（主委當時援引「95% 就收」——該原則已於 2026-09-11 全專案廢止） |
| B2c → B3 | codex、grok | 直接進 B3 |
| B3 → B4 | codex | 直接進 B4 |
| B4 R2 | codex、grok（不可收票） | 已修，**尚未確認** |

根因：批次之間的 `review_quorum_check.sh` 只在「派實作給執行端」（task_id `*-impl-b<N>-<家族>`）時觸發；
本票實作由主委自任、從未派實作 ⇒ **該閘一次都沒跑過**；且它只驗「有沒有派出去審」，不讀裁決。

另：2026-09-11 歸屬回溯稽核（`handoffs/run_receipts/splitunify-attribution-audit-20260911.txt`）
撈回 **3 條被主委弄丟的意見**，已於 `539431fc` 修掉，也請原提出方確認。

## 🔴 必答：每一家只確認**自己**當初提的那幾條

**對象 commit：`539431fc`**（HEAD）。每條逐一回「**已閉合／未閉合**」＋**你自己原本那個反例的實跑輸出**
（不是讀碼判斷、不是「看起來修好了」——是重跑同一個反例）。

### codex

1. `handoffs/20260911-splitunify-b1-review-r1-codex.md`：**CODEX-R1-P1-01**（D-002 覆寫錨點不是 BASE heading）、
   **CODEX-R1-P1-02**（Task 1.3 驗證條件 19≠30）。
2. `handoffs/20260911-splitunify-b2-review-r3-codex.md`：**CODEX-R3-P1-01**（DatetimeIndex 未驗遞增）、
   **CODEX-R3-P1-02**（row_index 未驗順序）、**CODEX-R3-P3-04**（裸 KeyError——🔴 當輪被主委漏掉，`539431fc` 才修）。
3. `handoffs/20260911-splitunify-b3-review-r1-codex.md`（審 B2c）：**CODEX-R1-P1-01／P1-02／P1-03**（G-5③／fingerprint 無外部對證／oracle 共用 fixture）。
4. `handoffs/20260911-splitunify-b4-review-r1-codex.md`（審 B3）：**CODEX-R1-P1-01**（投影未對證 plan 與 feature_index 同源）。
5. `handoffs/20260911-splitunify-b6-review-r1-codex.md`（審 B4 R2）：**CODEX-R2-P1-01**（「鍵名含 test」可被改名逃逸）。
6. `handoffs/20260911-splitunify-b2-review-r1-codex.md`：**CODEX-R1-P2-04 之附帶項**
   （`tier_min_test_events` 責任邊界）——🔴 主委當輪寫「列入 B3 Task 3.1」後消失，實況是投影路徑把設定**靜默換成 1**，`539431fc` 才修。

### grok

1. `handoffs/20260911-splitunify-b2-review-r3-grok.md`：**GROK-R3-P1-01**（DatetimeIndex 分支繞過）。
2. `handoffs/20260911-splitunify-b3-review-r1-grok.md`（審 B2c）：**GROK-R1-P1-01**（G-5③ 只驗 start）。
3. `handoffs/20260911-splitunify-b6-review-r1-grok.md`（審 B4 R2）：**GROK-R2-P1-01**（改名逃逸）。
4. `handoffs/20260911-splitunify-b2-review-r1-grok.md`：**GROK-R1-P2-02**（答案窗 mutation 缺口：
   `>= test_start_ms - 1` 與改讀 `time_bounds[0]`）——🔴 主委當輪掛在 H5 下但**那條測試從沒補**，`539431fc` 才補前半；
   後半主委判定已被 B3 同源對證變成**等價 mutant**——**請正面驗證這個「等價」判定是否成立**。

### composer

composer 在 B4 R1 寫「不可收票」、R2 改判「可收票」。請確認：
1. `handoffs/20260911-splitunify-b5-review-r1-composer.md`：**COMPOSER-R1-P1-01／P1-02** 在 HEAD 已閉合。
2. 🔴 **獨立檢查**：上表以外，你在任一輪提過而**主委從未回應**的意見。回溯稽核只比對了「編號是否掛在決議上」，
   沒比對「決議是否真的處理了」——請以提出者身分挑戰這一點。

## 停輪條件

① 每家必答的每一條皆有「已閉合／未閉合」＋**實跑輸出**；② 未閉合者標 P0/P1 並說明「不改會怎麼失敗」；
③ 禁以讀碼判斷代替重跑；④ 禁以「三家零 finding」當停輪。

## 本 brief 之前提（逐條標）

fact-verified: 上表各輪裁決由主委以腳本逐檔擷取（`scratchpad/verdict_table.py`），命令與輸出已存。

fact-verified: `review_quorum_check.sh` 之觸發條件見 `scripts/gate.sh:783-803`（`case "${task_id}" in *-impl-b[0-9]*-*)`）。

fact-verified: `539431fc` 之 B2b mutation 27 條＋C0、B3 mutation 13 條＋C0 皆 UNCOVERED=0；
相關 pytest 701 passed。

assumed: 回溯稽核撈到的 3 條是全部
← 否證觀測：還有意見「掛在對的決議下、但處置沒真正回應它」而主委沒看出來。
／我跑了：只比對了**編號歸屬**與**原文 vs 決議標題**，沒有逐條驗證處置內容。請正面打（composer 必答 2）。

## 🔴 我沒查的

| claim | observable_if_false | reason_code |
|---|---|---|
| 規格審查 R2–R4 之歸屬 | 那幾輪有委員戳記但只蓋在 consult 與 R1；R2–R4 之 synth 戳記為 0 | cost（本輪先處理程式碼審查） |

## ⚠️ 前置

- **禁改碼**、禁改 golden 值；要證明會紅請用 **repo 外**的 worktree。
- 🔴 **禁與主委或其他委員平行跑 mutation／全套測試**——本 session 已有一次 OOM；
  需要跑重的請只跑**自己那幾條反例**，不要跑 `tests/momentum/Analysis` 全套。
- 跑完 `bash scripts/restore_golden_inventory.sh`，並檢查 `git status tests/golden/`。收尾清 /tmp workdir。

## 產出

canonical 四欄 findings ＋ **Verdict**（第一句「已全數閉合」或「未閉合：<ID>」）。
