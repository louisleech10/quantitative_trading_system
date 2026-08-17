# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任（Fable/Opus）；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-1 **B1 已完工並過 review 修補**；**B2 已寫完待驗**

**文件三件套**：TODO **FROZEN R3**（`docs/GAP1_STRATEGY_OVERFIT_TODO.md`）
＋延伸檔 **A1-1..A1-20**（`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md`，**衝突以延伸檔為準**）
＋母 SPEC R8（未改）。收斂檔四份（r8／r9／b1-review-r10 已戳記或戳記中）。

**接手順序**：
1. **查 B1 戳記**：`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md`
   （composer／grok 已 APPROVED；codex 驗收中）。PASS ⇒ 銷該輪債（`debt_clear.sh --abandon`）。
2. **重跑 mutation 探針取乾淨 receipt**：`bash scripts/gap1_b1_mutation_probe.sh`（8 條，含 §V-7）。
   🔴 **委員在跑驗收時不要跑**——2026-08-18 撞過一次：codex 依 brief 故意弄紅 baseline 驗證 K2，
   我同時跑探針 ⇒ post-restore 檢查抓到牠的暫時性 broken test（探針本身沒問題，是時序）。
3. **commit B2**（Task 2.1–2.3 已寫完、90 passed）：契約 JSON＋`contract.py`＋`ledger.py`＋三個測試檔。
4. **派 B2 code review**（三家全員；brief 仿 `handoffs/20260817-gap1-b1-review-BRIEF.md`，
   task-id `20260818-GAP1-B2-REVIEW-R12`）→ 收斂 → 修 → 戳記 → **B3**。
5. B3（3.1–3.4）→ B4（4.1→4.2→4.3→**2.4**，wiring 閘 rc=0 只在 B4 收尾要求）。

## 現在的狀態

| 事實 | 怎麼查 |
|---|---|
| 待推筆數 | `git log --oneline origin/main..HEAD \| wc -l`（**push 需使用者明示**） |
| B1 產出 | `momentum/core/frequency.py`＋`momentum/Analysis/strategy_validation/{frequency,sharpe,returns_contract}.py`；改 `vectorized_backtest.py`／`objectives/strategy_backtest.py`（白名單內） |
| B2 產出（**未 commit**） | `momentum/Analysis/contracts/strategy_validation_contract.json`（16 頂層鍵）＋`strategy_validation/{contract,ledger}.py`＋`test_{contract,ledger,ledger_conformance}.py` |
| 測試現況 | `strategy_validation/` **90 passed**；全域既有紅 2 條（`test_model_hyperparam_enhanced`，與本 epic 無關） |
| mutation | 8 條（§V-5／7／8／9a／9b／10／13／15）；探針 baseline 與 post-restore 皆 fail-closed |
| 殘留 | registry「GAP-1 待補完」G1-R1..R7＋**R9**（ledger 完整性）＋**R10**（`IBacktestEngine` Protocol 未宣告新參） |

## ⚠ 本輪學到的（完整清單在 CLAUDE.md Gotchas，本檔不重述）

- 🔴 **委員驗收期間主控端不得跑會讀寫工作區的驗證腳本**——不只「不得改檔」。實例見上第 2 點。
- 🔴 **凡寫進契約的宣稱都要先有反例測試**：我在 A1-19 寫「不會靜默退回 730」，兩家各自造出反例推翻
  （engine 吞 kwargs 但不回填 annualization）⇒ A1-20 作廢該句並改成 fail-loud。同型錯誤本 epic 已犯兩次（J1／K1）。
- 🔴 **`git checkout` 還原不了未追蹤檔**；多檔 pathspec 有一個不存在會整條失敗 ⇒ 探針改 `cp` 備份還原。
- 🔴 **mutation 造成 SyntaxError（rc=2）不算「轉紅」**——那是 collection error，須斷言 rc=1 且 FAILED≥1。
- 🔴 委員產出要 `gate.sh register-output` 才過 claim checker；自寫 brief 可用
  `VERIFY-EXEMPT:doc-example:<id>` 並說明「本檔是提問清單非結論」。
- 🔴 commit trailer `Governance-Scope:` 必須與 `Co-Authored-By:` **同一段**（git 只解析最末段）。
