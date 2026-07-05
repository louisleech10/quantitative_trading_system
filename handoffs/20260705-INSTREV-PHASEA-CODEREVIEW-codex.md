# INSTREV Phase A Codex Code Review
task-id: instrev-phasea-codereview
Verdict: FAIL / BLOCKING findings
Findings:
1. BLOCKING - `docs/MULTI_AGENT_ORCHESTRATION.md:260,263,273,292` still contains a second selection conclusion: "Codex 主力", "預設 Codex 主力", "否則維持預設 codex 主力", and model pin table "主力執行 | codex". This violates Phase A [A-7] single dynamic source and the requested role swap to Composer implementation + Codex review. `docs/MULTI_AGENT_ORCHESTRATION.md:37` is correct, but §6/§7 can still steer Claude back to Codex implementation.
2. BLOCKING - `CLAUDE.md:92-93` preserves the "三方數據" token but weakens the old rule. Removed obligations from `HEAD:CLAUDE.md:151-156` include: data-correctness scope "生成/計算/merge/split/無洩漏", pass condition "任一方有疑→不通過", committee-designed falsifiable checks, and behavior-preserving refactor byte-level invariants. This fails "規則零刪減 / 非塞字".
Checklist:
- CLAUDE.md 12-token gate: PASS by grep, but semantic review FAILS on the 三方數據 rule above.
- Contract A-12 tokens: PASS and substantive in `AGENTS.md:38-40`, `.cursorrules:24-26`; `反提示注入` preserved.
- SCAR_LEDGER migration: PASS for required keywords and table size; `grep -c "^|" docs/SCAR_LEDGER.md` => 14; required `記憶(原始 commit 未尋獲)` present.
- Role swap: FAIL due ORCH §6/§7 residual Codex-main defaults; current §1 line itself is correct.
- Debug 2 rounds: PASS; no `3 輪` / `≤3 輪` in CLAUDE.md, AGENTS.md, .cursorrules, ORCH, BOOTSTRAP.
- Scope: PASS for requested technical scope; no tracked/untracked changes under scripts/, templates/, momentum/, api/, frontend/, data_cache/. ARCHITECTURE/DEVELOPMENT_GUIDE diffs are header banner only.
- New contract clauses: PASS; they impose stop/report/list-output obligations rather than empty labels.
TODO §B Gate outputs rerun:
- `bash scripts/check_agent_contract_sync.sh` => `✅ 四源關鍵不變式一致（presence check）`
- `wc -l CLAUDE.md .github/copilot-instructions.md` => `128 CLAUDE.md`, `8 .github/copilot-instructions.md`
- `grep -n "3 輪\|≤3 輪" AGENTS.md .cursorrules docs/MULTI_AGENT_ORCHESTRATION.md docs/MULTI_AGENT_BOOTSTRAP.md` => no output, exit 1
- `grep -rn "每 5 分鐘" CLAUDE.md AGENTS.md .cursorrules docs/MULTI_AGENT_ORCHESTRATION.md` => no output, exit 1
- `grep -cE "^\*\*現行分工|^- \*\*現行分工|現行分工\(" docs/MULTI_AGENT_ORCHESTRATION.md` => `1`
- `ls docs/SCAR_LEDGER.md` => `docs/SCAR_LEDGER.md`
- CLAUDE.md 12-token loop => no `DELETED_RULE`
- contract token loop => no `MISSING_CONTRACT`
- SCAR keyword loop => no `SCAR_MISSING`
- CLAUDE moved-keyword loop for `1970-01-21 feature-browser` => no `NOT_MOVED`
Notes:
- One attempted grep used unescaped shell backticks around `HANDOFF.md`; it produced `zsh:1: command not found: HANDOFF.md` and was discarded. Safe rerun with single quotes returned no output for obsolete "更新 HANDOFF.md".
- Non-target worktree changes observed: `.claude/gate/audit.log`, `handoffs/20260705-INSTREV-RECONCILE.md`, and Phase A spec/todo/adv handoff files. They were not part of this reviewed diff except where needed as inputs.
