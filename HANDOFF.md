# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：開 **GAP-2a 邊際 IC／多因子組合**（使用者 2026-08-18 點；新 session 開工）

**前提現況**（`git log origin/main..HEAD` 應為空；`bash scripts/debt_ledger.sh --list` 無 OPEN）：GAP-1 四批＋PA-CUMSUM＋G1-R11 皆 CLOSED（三家 review＋三家戳記；收斂檔在 `handoffs/reconcile/2026081{7,8}-*`）。無進行中 epic、無 OPEN 債。

**GAP-2a 定義與邊界**（`docs/IC_QUANT_GAP_REGISTRY.md` #2a／#2b；使用者裁定拆分）：
- 2a＝純 IC 層：「這因子相對已有的帶來多少**新**資訊」（邊際 IC／多因子組合）。正交化 residual 已在 `momentum/Analysis/factor_orthogonalizer.py`；真歸因現為誠實 `unavailable`（健檢 C11）。**不碰 ML、不碰事件型**。
- 2b＝IC→ML 橋：**契約先行**（倖存者輸出契約，須含 `sample_scope`＋provenance，序列型／事件型共用同一座橋），於 2a SPEC 內一併定義；**橋本體 blocked-by ML 層**（成熟度地圖：ML／回測屬不完整層），不接。
- 大任務（命中 a/d）⇒ 完整管線：Claude 起草 SPEC → 三家 adversarial（reconcile＋戳記）→ 白話給使用者審 → TODO → 實作分批 → 三家 code review → 戳記。範本 `templates/`；SPEC 建檔需 gate token（`bash scripts/gate.sh artifact`）。
- 開工前先稽核 HANDOFF／ROADMAP／registry vs repo，並看有無殘留委員行程（ps 查 cursor-agent／codex／grok）。

**GAP-3 事件型（不是本 session 的事，勿順手開）**：使用者重定義＝外部標好正反例匯入→PIT 對齊→條件 IC／ML（非 event study）；**開發前先討論**：第一步＝唯讀事件語意 consult，5 題見 registry「GAP-3 開發前討論題」節。

## ⚠ 收尾與坑（完整清單在 CLAUDE.md Gotchas／白話 摩擦記錄 六十一～六十七）
- 🔴 每批收尾：pytest → 探針 → commit → push（背景）→ 白話 5 檔同步 → commit+push（`plain_docs_sync_check` 是 pre-push 硬擋，動 `scripts/` 就要更新白話 5 檔）。commit+push 皆秒級。
- 🔴 委員 CLI 有看門狗（`cx_run.sh`）；brief 要求委員自建探針加 timeout；`handoffs/*` 新檔須 `git add -f`；白話 .md commit 時 pre-commit 同 commit 重生成 `docs/site/`。
- 🔴 `docs/API_SPECIFICATION.md` 受格式快閘不可編輯（摩擦六十七）——契約以 pydantic schema 為準，勿再嘗試。
- 對多處同型行做 `sed` 前先 `grep -c`；「為了讓閘門過而放寬規則」會被委員反例打回。
- `scripts/governance_families.json` 有既有 no-op dirty，非本線產生，未歸屬。
