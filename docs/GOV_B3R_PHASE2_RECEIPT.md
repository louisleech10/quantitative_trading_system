# `B3R` Phase 2 — 原型與差分收據（站 4）

**建立**：2026-08-11　**性質**：唯讀收據，非機械驗收。
**規格**：`docs/GOVB0_B3R_LEXER_SPEC.md`（**唯讀**）；出處 `handoffs/reconcile/20260809-govb1-b3-review-r8/synth.md:44-50`（`CODEX-R8-P1-03`）。

> 本檔由 `HANDOFF.md` 逐字搬出（HANDOFF 須 ≤30 行，該段 46 行）。
> HANDOFF 保留指標；細節在此。**內容一字未改**。

---

### 🔴 主委 2026-08-11 已做完 Phase 2 原型與差分，**但 C-5 未達標 ⇒ 依 SPEC 不得進 repo**

原型與量測全在 `.claude/tmp/probe-r11r12/`（git worktree，**主樹 `scripts/_gate_lex.sh` 一字未動**）。

| 項 | 舊版 | 原型 |
|---|---|---|
| quoted 100K | **1s** | **0s** |
| quoted 500K | **29s** | **11s** |
| 差分（95 條語料：`gate_decision_corpus` ＋ `gate_invariance_corpus`） | — | `pre_diff=0 rc_diff=0`（前處理輸出**逐位元組相同**、判定 rc 全同） |

🔴 **29s 這個數字與 SPEC `E-2` 記載的 `500K→29.92s` 吻合** ⇒ 量測可信、可重跑。

**原型改了什麼**：`ACC_RESET/ACC_ADD/ACC_GET` 三個 awk 函式取代所有 `out = out c`／`src = src line`／
`line = line substr(...)`（共 20 處，以斷言命中次數的腳本機械替換，漏一處即拒寫檔）；
`ACC_GET` 用**兩兩合併**（log 深度）而非線性串接。

🔴 **為什麼 2.6× 之後就卡住（profiling 結論，別再重試同一路）**：
`prof_lex.sh` 把 `_gate_cmd_is_dispatch` 拆三段量測 ⇒ 500K 時 `grep_pre=0 preprocess=11 match_scan=0 grep_post=0`
——**全部時間都在 awk 前處理內**，且把 chunk 由 8192 改 128＋log 合併**完全沒有改善**（仍 11s）
⇒ 瓶頸**不是字串累加**，是**每字元一次 awk 函式呼叫／迴圈迭代**本身（1M 次）。
⇒ 真正的解＝**批次掃描**（一次跳到下一個特殊字元，整段 `substr` 搬移），
  而 POSIX awk 沒有「從偏移量開始 match」的原語 ⇒ 這是**演算法重寫**，不是微調。
  這正是 SPEC 把它放進 Phase 2「原型與差分」而非直接實作的理由。

**接手時**（四支工具皆在 `.claude/tmp/`，**gitignored 但本機留存**；session scratchpad 會隨壓縮消失，故已複製出來）：

| 檔 | 用途 |
|---|---|
| `.claude/tmp/on_rewrite.py` | 把 20 處逐字元累加機械替換成 `ACC_*`；**每條規則斷言命中次數，漏一處即拒寫檔** |
| `.claude/tmp/bench_lex.sh` | C-5 效能樁（輸出 `gen=` 與 `lex=` 分開，避免把測具耗時算進去） |
| `.claude/tmp/diff_lex.sh` | 舊 vs 新之差分：前處理輸出逐位元組 ＋ 判定 rc，出口＝差異 0 |
| `.claude/tmp/prof_lex.sh` | 把 `_gate_cmd_is_dispatch` 拆四段計時，定位瓶頸落在哪一段 |

原型 worktree：`.claude/tmp/probe-r11r12`（`git worktree list` 可見，detached `4b8346d6`）。
若已被清掉：`git worktree add .claude/tmp/probe-r11r12 --detach <sha>` 後跑 `on_rewrite.py` 即可重建。
🔴 **`bench` 的 payload 生成必須是 O(n)**（`sprintf("%*s")`＋`gsub`）——初版用逐字元累加造字串，
量到的是測具自己，主委已踩過一次。

- 🔴 **`scripts/_gate_lex.sh` 不在 `govb1_scope.manifest` allow** ⇒ commit 須帶 OOE trailer；
  它是**共用控制流**（`gate_check.sh` 的 PreToolUse hook 每次工具呼叫都走它；命中高風險 (b)）
  ⇒ 走完整管線，規格已存在：`docs/GOVB0_B3R_LEXER_SPEC.md`（**唯讀**）。
- 🔴 **不得只因「比較快」就把原型落地**：SPEC Task 2.1 的出口是 C-1～C-5 **全數通過**，
  C-5 未過 ⇒ Phase 3 不得開始。落一個「快 2.6 倍但仍不達標」的版本，
  只會讓下一手誤以為這件事做完了——那是本 epic 一路在治的病。

## ✅ 本 session 已交付（2026-08-10～11，皆兩家 `RECONCILE-STAMP APPROVED`）
