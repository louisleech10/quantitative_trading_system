# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-2 **B1 實作**（TODO 已 FROZEN）→ 三家 code review → 戳記 → B2

**現況**（2026-08-18 深夜）：SPEC `docs/GAP2_MARGINAL_IC_SPEC.md` **R7 FROZEN**＋延伸檔 `docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..A1-6，衝突時以延伸檔為準）；TODO `docs/GAP2_MARGINAL_IC_TODO.md` **FROZEN**（五輪 adversarial 20→15→7→1→0；十一份收斂檔 `handoffs/reconcile/20260818-gap2-x-{consult-r1,review-r1..r11}/synth.md` 皆三家 RECONCILE-STAMP）；殘留 G2-R1／R2／R3／R5 在 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-2 待補完」；債務清單乾淨。**B1 尚未開始寫碼**（或看 git log 是否已有 `feat(gap2): B1` commit）。

**B1 步驟**（TODO §B／Phase B1；Claude 自做）：Task 1.0 `momentum/Analysis/contracts/ic_survivor_contract.json`＋`survivor_contract.py::load_survivor_contract()`＋`tests/momentum/Analysis/test_survivor_contract.py -k load` → Task 1.1 `marginal_ic.py::normal_scores/fit_projection/apply_residual/Projection` → Task 1.2 `MarginalICParams/MarginalICResult/compute_marginal_ic/block_bootstrap_ci`＋`test_marginal_ic.py`（§G O1a/O1b/O2/O3/O5/O6/O7/O9＋⑧–⑮ 含 `fit_projection` spy）→ Task 1.3 `scripts/gap2_mutation_probe.sh --batch B1`（十條唯一對映；沿用 `scripts/gap1_b1_mutation_probe.sh` 骨架）。收尾固定順序：pytest（兩條分跑）→ `bash scripts/mutation_probe_check.sh <兩測試檔>` → 探針 → commit → push（背景）→ 白話 5 檔 → commit+push。之後派三家 code review（brief 附 registry「GAP-2 待補完」表＋每 Task 派工 prompt 樣板 §B）→ 修 → stamp → B2。
**注意**：venv Python **3.9.6**（禁 3.10+ 語法；Task 4.2 `hashlib.file_digest` 為 3.11+，B4 時用等價寫法並在 review brief 標明）；scipy 1.13.1／numpy 1.26.4／pandas 2.3.2。
白話 5 檔＝`白話說明/{README,接下來要做什麼,治理進度日誌,流程摩擦記錄,GAP-2施工進度}.md`（`plain_docs_sync_check.sh` WATCHED 含 marginal_ic.py／factor_combiner.py／survivor_contract.py／契約 JSON／gap2 腳本／TODO／AMENDMENTS）。

## ⚠ 坑（本 session 實踩；完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～七十）
- 🔴 `committee_run.sh` 的 Bash 呼叫會被 gate_check 當 dispatch 擋（指令含家族名）：先 `bash scripts/gate.sh dispatch <同 flags>` mint token，再跑 committee_run（同 flags）；gate.sh dispatch 在債 OPEN 時拒發 ⇒ 先 register-output＋debt_clear。
- 🔴 review brief 前提須逐條 `fact-verified:`／`assumed:` 前綴（各 ≥1），否則 committee_run 在 brief 檢查即失敗、不派任何一家。
- 🔴 `debt_clear.sh --abandon` 必帶 `--approver main-agent`；stamp 輪 session 名須 `…-stamp-r<N>`；每輪 review 後必接 stamp。
- 🔴 判收斂看**每家最近一次內容審查**皆 sentinel，不是總數歸零；駁回委員 finding 須附可重跑碼證＋下一輪叫提出方重跑確認。
- 委員產出須 `gate.sh register-output` 才過 pre-commit claim checker；commit 須帶 `Governance-Scope:` trailer（G-7）；handoffs 檔被 `.git/info/exclude` 排除，須 `git add -f`。
- `docs/API_SPECIFICATION.md` 受格式快閘不可編輯；`scripts/governance_families.json` 既有 no-op dirty 非本線。
