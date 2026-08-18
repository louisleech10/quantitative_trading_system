# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：收 GAP-2 TODO adversarial **R10**（已派出）→ TODO FROZEN → B1 實作

**現況**（2026-08-18 深夜）：SPEC `docs/GAP2_MARGINAL_IC_SPEC.md` **R7 FROZEN**＋延伸檔 `docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..A1-6）；殘留 G2-R1／R2／R3／R5 在 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-2 待補完」。TODO `docs/GAP2_MARGINAL_IC_TODO.md` **DRAFT R4**（R9 三家 7 findings 三群集 V1–V3 全接受＋A1-5（page.tsx 白名單；**主委補正掛 basic tab 末段，待 R10 三家判**）／A1-6（write_failed 字面封閉）；收斂檔 `handoffs/reconcile/20260818-gap2-x-review-r9/synth.md` 三家 RECONCILE-STAMP，stamp r10）。**R10 已派**：session `20260818-gap2-x-review-r10`、task `20260818-GAP2-X-REVIEW-R10`、產出 `handoffs/20260818-gap2-todoadv-r10-{codex,composer,grok}.md`、runlog `…-r10-committee.runlog`（round_id 見 runlog；**債 OPEN 中**，須銷）。八份 review synth＋consult 皆三家戳記。

**接手步驟**：① `reconcile_build.sh 20260818-gap2-x-review-r10 --mode review <三檔>` → 填群集 → 若有修補：改 TODO（DRAFT R5）／SPEC 義務側走延伸檔 A1-7+ → `template_check.sh todo` → `gate.sh register-output` 三檔 → `debt_clear.sh --round-id … --session …` → 加 `## 戳記` 區＋派 stamp 輪 r11（🔴 每輪 review 後**必**接 stamp；先 `gate.sh dispatch` mint token 再 `committee_run.sh --session *-stamp-r<N>`；結束 `debt_clear --abandon --kind no-findings-expected --approver main-agent`＋`register-output <task> <三檔＋synth>`）→ commit＋push。② 三家皆「可 Frozen」（每家最近一次內容審查皆 sentinel／無 BLOCKING）⇒ TODO 版本行改 **FROZEN**、白話看板同步 → 派 B1（Claude 自做 Task 1.0→1.1→1.2→1.3；收尾 pytest→探針→commit→push→白話 5 檔→commit+push；review brief 附 registry「GAP-2 待補完」表）→ 三家 code review → 修 → stamp → B2…
③ 白話 5 檔＝`白話說明/{README,接下來要做什麼,治理進度日誌,流程摩擦記錄,GAP-2施工進度}.md`（`plain_docs_sync_check.sh` 已註冊 GAP-2 看板 WATCHED 含 TODO／AMENDMENTS；動 `scripts/`／新模組必同步）。

## ⚠ 坑（本 session 實踩；完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～七十）
- 🔴 `committee_run.sh` 的 Bash 呼叫會被 gate_check 當 dispatch 擋（指令含家族名）：先 `bash scripts/gate.sh dispatch <同 flags>` mint token，再跑 committee_run（同 flags）。
- 🔴 `debt_clear.sh --abandon` 必帶 `--approver main-agent`；stamp 輪 session 名須 `…-stamp-r<N>`。
- 🔴 判收斂看**每家最近一次內容審查**皆 sentinel，不是總數歸零；駁回委員 finding 須附可重跑碼證＋下一輪叫提出方重跑確認。
- 委員產出須 `gate.sh register-output` 才過 pre-commit claim checker；commit 須帶 `Governance-Scope:` trailer（G-7）；handoffs 檔被 `.git/info/exclude` 排除，須 `git add -f`。
- `docs/API_SPECIFICATION.md` 受格式快閘不可編輯；`scripts/governance_families.json` 既有 no-op dirty 非本線。
