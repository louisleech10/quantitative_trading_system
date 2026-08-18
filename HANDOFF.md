# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-2 TODO adversarial R7 收斂 → TODO FROZEN → B1 實作

**現況**（2026-08-18 晚）：SPEC `docs/GAP2_MARGINAL_IC_SPEC.md` **R7 FROZEN**（六輪三家 adversarial 14→12→4→4→2→0；七份 synth 三家 RECONCILE-STAMP；使用者白話閘核准；B5 表格＋`marginal_ic` toggle 預設開）；殘留 G2-R1／R2／R3／R5 已登記 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-2 待補完」。TODO `docs/GAP2_MARGINAL_IC_TODO.md` **DRAFT R1** 已送三家（session `20260818-gap2-x-review-r7`，task `20260818-GAP2-X-REVIEW-R7`；產出 `handoffs/20260818-gap2-todoadv-{codex,composer,grok}.md`）。

**接手步驟**：① 若 R7 已回：`reconcile_build.sh 20260818-gap2-x-review-r7 --mode review <三檔>` → 填群集 → 修 TODO（SPEC 義務側缺陷寫**延伸檔** `docs/GAP2_MARGINAL_IC_AMENDMENTS.md`，母 SPEC 不就地改）→ `template_check.sh todo` → register-output 三檔 → `debt_clear.sh` → **加 `## 戳記` 區＋派 stamp 輪**（🔴 每輪 review 後**必**接 stamp 輪，session `*-stamp-r<N>`、單一 target；漏跑會被 codex 依 AGENTS 12 條停工，本 session 已再犯一次）→ commit＋push；三家皆「可 Frozen」⇒ TODO FROZEN → 派 B1（Claude 自做：Task 1.0→1.1→1.2→1.3；收尾 pytest→探針→commit→push→白話 5 檔→commit+push）→ 三家 code review → 修 → stamp → B2…
② 白話 5 檔＝`白話說明/{README,接下來要做什麼,治理進度日誌,流程摩擦記錄,GAP-2施工進度}.md`（`plain_docs_sync_check.sh` 已註冊 GAP-2 看板 WATCHED；動 `scripts/`／新模組必同步）。

## ⚠ 坑（本 session 實踩；完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～六十九）
- 🔴 commit 訊息與 heredoc 內含 `codex`／`grok` 字樣可能被 gate_check 當派工擋（先 mint dispatch token 或改用 Edit 工具寫檔）。
- 🔴 stamp 輪 session 名須 `…-stamp-r<N>`（無 r<N> 拒發）；stamp 輪結束用 `debt_clear.sh --abandon --kind no-findings-expected`＋`gate.sh register-output <task> <synth>`。
- 🔴 判收斂看**每家最近一次內容審查**皆 sentinel，不是總數歸零（R3 codex 因流程停工未審內容 → R4 才出 4 條）。
- 委員產出須 `gate.sh register-output` 才過 pre-commit claim checker；commit 須帶 `Governance-Scope:` trailer（G-7）。
- `docs/API_SPECIFICATION.md` 受格式快閘不可編輯；`scripts/governance_families.json` 既有 no-op dirty 非本線。
