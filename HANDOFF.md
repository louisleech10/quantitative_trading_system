# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-2 **B4 code review 收件**（B1–B3 CLOSED；B4 寫完已派 review）→ 修 → 戳記 → B5

**現況**（2026-08-18 深夜）：SPEC `docs/GAP2_MARGINAL_IC_SPEC.md` **R7 FROZEN**＋延伸檔 `docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..A1-6，衝突時以延伸檔為準）；TODO `docs/GAP2_MARGINAL_IC_TODO.md` **FROZEN**（五輪 adversarial 20→15→7→1→0；十一份收斂檔 `handoffs/reconcile/20260818-gap2-x-{consult-r1,review-r1..r11}/synth.md` 皆三家 RECONCILE-STAMP）；殘留 G2-R1／R2／R3／R5 在 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-2 待補完」；債務清單乾淨。**B1／B2／B3 CLOSED**（收斂檔 `…-b1-review-r12`／`…-b2-review-r15`／`…-b3-review-r18` 皆三家戳記；A1-7／A1-8／A1-9）。**B4 寫完**（commit ab53c24e＋白話；A1-10）並已派三家 review：session `20260819-gap2-b4-review-r21`、task `20260819-GAP2-B4-REVIEW-R21`、產出 `handoffs/20260819-gap2-b4-review-{codex,composer,grok}.md`（**債 OPEN 中**，須銷）。

**B4 收件步驟**：`reconcile_build.sh 20260819-gap2-b4-review-r21 --mode review <三檔>` → 群集 → 修補（延伸檔 A1-11+）→ 重跑 gate（§B「B4→B5」列：pytest 六檔 71 passed／`mutation_probe_check` 三新檔／`ic_wiring_check.sh`／`gap2_freeze_golden.py --check`／`--batch B4`；探針約 20 分鐘且互斥）→ commit → register-output＋debt_clear → `## 戳記`＋stamp r22（兼修補驗收；in-memory only；single family 重驗如遇並行干擾）→ B4 CLOSED → **B5**（Task 5.1：`types.ts`／`icAnalysisStore.ts`／`FeatureTierPanel.tsx`／`app/ic-analysis/page.tsx` basic tab 末段掛載（A1-5 補正）＋新 `MarginalICTable.tsx`／`.test.tsx`；收尾 vitest／build／tsc／wiring／§V 24 條全實跑）。
**（B2 步驟留檔）**：`momentum/Analysis/factor_combiner.py::combine_factors`＋`CompositeResult`＋`block_bootstrap_ci` 自 `marginal_ic.py` 搬入（`marginal_ic.py` 改 import；避免循環 import：`factor_combiner` 對 `marginal_ic` 用函式內 lazy import）；`tests/momentum/Analysis/test_factor_combiner.py`（§G O4／O8／O9＋①–⑦＋`test_mutation_test_sign_breaks_o8`）；探針 `--batch B2` 加 V-7／8／9。Gate＝§B「B2→B3」列。之後 review brief 附 registry 表、stamp、B3。
**（B1 步驟留檔）**：Task 1.0 `momentum/Analysis/contracts/ic_survivor_contract.json`＋`survivor_contract.py::load_survivor_contract()`＋`tests/momentum/Analysis/test_survivor_contract.py -k load` → Task 1.1 `marginal_ic.py::normal_scores/fit_projection/apply_residual/Projection` → Task 1.2 `MarginalICParams/MarginalICResult/compute_marginal_ic/block_bootstrap_ci`＋`test_marginal_ic.py`（§G O1a/O1b/O2/O3/O5/O6/O7/O9＋⑧–⑮ 含 `fit_projection` spy）→ Task 1.3 `scripts/gap2_mutation_probe.sh --batch B1`（十條唯一對映；沿用 `scripts/gap1_b1_mutation_probe.sh` 骨架）。收尾固定順序：pytest（兩條分跑）→ `bash scripts/mutation_probe_check.sh <兩測試檔>` → 探針 → commit → push（背景）→ 白話 5 檔 → commit+push。之後派三家 code review（brief 附 registry「GAP-2 待補完」表＋每 Task 派工 prompt 樣板 §B）→ 修 → stamp → B2。
**注意**：venv Python **3.9.6**（禁 3.10+ 語法；Task 4.2 `hashlib.file_digest` 為 3.11+，B4 時用等價寫法並在 review brief 標明）；scipy 1.13.1／numpy 1.26.4／pandas 2.3.2。
白話 5 檔＝`白話說明/{README,接下來要做什麼,治理進度日誌,流程摩擦記錄,GAP-2施工進度}.md`（`plain_docs_sync_check.sh` WATCHED 含 marginal_ic.py／factor_combiner.py／survivor_contract.py／契約 JSON／gap2 腳本／TODO／AMENDMENTS）。

## ⚠ 坑（本 session 實踩；完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～七十）
- 🔴 `committee_run.sh` 的 Bash 呼叫會被 gate_check 當 dispatch 擋（指令含家族名）：先 `bash scripts/gate.sh dispatch <同 flags>` mint token，再跑 committee_run（同 flags）；gate.sh dispatch 在債 OPEN 時拒發 ⇒ 先 register-output＋debt_clear。
- 🔴 stamp／review brief **不得邀請委員就地改檔實驗**（B1 stamp r13 codex 因他家插 decoy 字面＋探針並行而 BLOCKED；改 codex 單家獨占 r14 才過）；判準寫「in-memory only」；有疑義派單家獨占重驗。session 名 `-stamp-r<N>` 只准純數字（`r13v2` 被拒）。
- 🔴 commit 訊息 `Governance-Scope:` trailer 須獨立成最後一段（同段夾其他行 ⇒ G-7 擋）。
- 🔴 review brief 前提須逐條 `fact-verified:`／`assumed:` 前綴（各 ≥1），否則 committee_run 在 brief 檢查即失敗、不派任何一家。
- 🔴 `debt_clear.sh --abandon` 必帶 `--approver main-agent`；stamp 輪 session 名須 `…-stamp-r<N>`；每輪 review 後必接 stamp。
- 🔴 判收斂看**每家最近一次內容審查**皆 sentinel，不是總數歸零；駁回委員 finding 須附可重跑碼證＋下一輪叫提出方重跑確認。
- 委員產出須 `gate.sh register-output` 才過 pre-commit claim checker；commit 須帶 `Governance-Scope:` trailer（G-7）；handoffs 檔被 `.git/info/exclude` 排除，須 `git add -f`。
- `docs/API_SPECIFICATION.md` 受格式快閘不可編輯；`scripts/governance_families.json` 既有 no-op dirty 非本線。
