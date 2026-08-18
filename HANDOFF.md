# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：收 GAP-2 TODO adversarial **R8**（已派出、結果可能已在）→ TODO FROZEN → B1 實作

**現況**（2026-08-18 晚，session 因 context 不足暫停）：SPEC `docs/GAP2_MARGINAL_IC_SPEC.md` **R7 FROZEN**＋延伸檔 `docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..A1-3）；殘留 G2-R1／R2／R3／R5 在 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-2 待補完」。TODO `docs/GAP2_MARGINAL_IC_TODO.md` **DRAFT R2**（R7 三家 20 findings 全寫回；收斂檔 `handoffs/reconcile/20260818-gap2-x-review-r7/synth.md` 三家戳記）。**R8 已派**：session `20260818-gap2-x-review-r8`、task `20260818-GAP2-X-REVIEW-R8`、產出 `handoffs/20260818-gap2-todoadv-r8-{codex,composer,grok}.md`、runlog `handoffs/20260818-gap2-todoadv-r8-committee.runlog`（round_id `daa84f4e-95ca-4d30-ab6c-a8dfbbd02278`；**債 OPEN 中**，須銷）。**R8 已回件（未處理）**：codex 9 條「需修補」／grok 4 條（2 條 P0：§0 白名單漏 `FeatureTierPanel.tsx` 等）「不可 Frozen」／composer 2 條「可 Frozen（B4 前修）」⇒ 下一步＝reconcile R8 → TODO DRAFT R3 → stamp r9 → 派 R9 複核，**尚未收斂**。八份 synth 皆三家 RECONCILE-STAMP。

**接手步驟**：① `reconcile_build.sh 20260818-gap2-x-review-r8 --mode review <三檔>` → 填群集（三家 sentinel ⇒ 一群集）→ 若有修補：改 TODO（DRAFT R3）／SPEC 義務側走延伸檔 A1-4+ → `template_check.sh todo` → `gate.sh register-output` 三檔 → `debt_clear.sh --round-id … --session …` → 加 `## 戳記` 區＋派 stamp 輪 r9（🔴 每輪 review 後**必**接 stamp；session `*-stamp-r<N>` 單一 target；結束 `debt_clear --abandon --kind no-findings-expected`＋`register-output <task> <synth>`）→ commit＋push。② 三家皆「可 Frozen」⇒ TODO 版本行改 **FROZEN**、白話看板同步 → 派 B1（Claude 自做 Task 1.0→1.1→1.2→1.3；收尾 pytest→探針→commit→push→白話 5 檔→commit+push；review brief 附 registry「GAP-2 待補完」表）→ 三家 code review → 修 → stamp → B2…
② 白話 5 檔＝`白話說明/{README,接下來要做什麼,治理進度日誌,流程摩擦記錄,GAP-2施工進度}.md`（`plain_docs_sync_check.sh` 已註冊 GAP-2 看板 WATCHED；動 `scripts/`／新模組必同步）。

## ⚠ 坑（本 session 實踩；完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～六十九）
- 🔴 commit 訊息與 heredoc 內含 `codex`／`grok` 字樣可能被 gate_check 當派工擋（先 mint dispatch token 或改用 Edit 工具寫檔）。
- 🔴 stamp 輪 session 名須 `…-stamp-r<N>`（無 r<N> 拒發）；stamp 輪結束用 `debt_clear.sh --abandon --kind no-findings-expected`＋`gate.sh register-output <task> <synth>`。
- 🔴 判收斂看**每家最近一次內容審查**皆 sentinel，不是總數歸零（R3 codex 因流程停工未審內容 → R4 才出 4 條）。
- 委員產出須 `gate.sh register-output` 才過 pre-commit claim checker；commit 須帶 `Governance-Scope:` trailer（G-7）。
- `docs/API_SPECIFICATION.md` 受格式快閘不可編輯；`scripts/governance_families.json` 既有 no-op dirty 非本線。
