# VERIFYGATE B3 — Codex adversarial code review

**Scope**: B3 Task 3.1/3.2/3.3/3.4 + Claude 自改 `scripts/verify_task_provenance.py`  
**Reviewer**: Codex  
**Date**: 2026-07-02  
**Verdict**: `CHANGES_REQUIRED`

## BLOCKING

### B3-1 — pre-commit 掃 staged 檔名但讀 working tree，可被 partial-stage 繞過

- **檔案/行號**: `scripts/git_hooks/pre-commit:12` → `verification_claim_check.py --staged`; `scripts/verification_claim_check.py:1120-1128` 只取 staged 檔名；`scripts/verification_claim_check.py:1105-1108` 用 `path.read_text()` 讀 working tree。
- **反例**: temp repo 內先把 `HANDOFF.md` staged 為 `- align 已驗真紅`，再把 working tree 改回 `- clean note`，commit 成功；staged 的假 claim 進 commit。
- **影響**: Task 3.2 的「staged HANDOFF 含假 claim → commit 被拒」不成立；部分 stage 是日常 git workflow，不是惡意高成本繞過。
- **修法**: `--staged` 必須讀 index blob：用 `git diff --cached --name-only --diff-filter=ACMR -z` 找路徑，再對每個 path 用 `git show :<path>` 或 `git diff --cached --unified=0` 的 staged 新增內容送 checker。rename 應讀新 path 的 staged blob；delete 跳過。
- **測試缺口**: `tests/governance/test_verify_gate_b3.py:243-256` 只測 staged 與 working tree 相同的 happy red path，缺 partial-stage 反例。

### B3-2 — pre-commit 對 code-only commit 假紅，會阻斷正常提交

- **檔案/行號**: `scripts/git_hooks/pre-commit:12` 無條件 exec checker；`scripts/verification_claim_check.py:1249-1251` 在沒有 input files 時回傳 exit 2。
- **反例**: temp repo 安裝 hooks 後只 staged `foo.py`，`git commit -m 'feat: add foo'` 失敗，stderr 為 `verification_claim_check.py: no input files`。
- **影響**: hooks 安裝後，任何不改 `HANDOFF.md`/`handoffs/*.md`/`docs/*.md` 的正常 commit 都會被擋；這會讓 B3 git hook 無法實際啟用。
- **修法**: `pre-commit` 先檢查 staged scannable path；沒有就 `exit 0`。或讓 checker 在 `--staged` 模式下沒有 scannable input 時回傳 0，但保持一般 CLI 無 input exit 2。
- **測試缺口**: `tests/governance/test_verify_gate_b3.py:273-288` 的「正常 commit」仍改 `docs/note.md`，沒有覆蓋 code-only / non-scannable commit。

### B3-3 — health 接到 preflight/postflight 後，當前真實 repo 立即 fail；且 `py_compile` 在受限環境寫 pyc 會假紅

- **檔案/行號**: `scripts/agent_preflight.sh:21`、`scripts/agent_postflight.sh:45` 硬接 `verify_hooks_health.sh`；`scripts/verify_hooks_health.sh:14-18` 要求 `core.hooksPath=scripts/git_hooks`；`scripts/verify_hooks_health.sh:48-50` 用 `python -m py_compile`。
- **反例**: 真實 repo `git config --get core.hooksPath` 回傳 unset；`bash scripts/agent_preflight.sh /tmp/b3-review-snap.txt` exit 2。另 `venv/bin/python -m py_compile scripts/verification_claim_check.py` 在目前 workspace-write sandbox 嘗試寫 `/Users/louis/Library/Caches/...pyc`，`PermissionError: Operation not permitted`。
- **影響**: Composer 收尾明說「真實 repo 未執行 install_verify_hooks.sh」，但 preflight/postflight 已硬 fail；後續 Claude 派工安全檢查會被 B3 自己阻斷。`py_compile` 還會在受限 headless agent 環境中把健康檢查誤判為壞。
- **修法**: 二選一但要一致：A) B3 落地時把 `core.hooksPath` 設好並在交付中聲明真實 repo 已安裝；B) preflight/postflight 在 git hooks 未安裝時輸出明確 blocking setup 指引，但不要和「工具壞掉」混在一起。`py_compile` 改為不寫 pyc 的 syntax check，例如 `python -c 'import ast, pathlib; ast.parse(pathlib.Path("scripts/verification_claim_check.py").read_text())'`，或設定可寫 `PYTHONPYCACHEPREFIX` 到 `/tmp`。
- **測試缺口**: `tests/governance/test_verify_gate_b3.py:341-345` 只在 temp repo 已 install hooks 後測 health 綠，沒有驗證真實 repo preflight 在交付狀態可用；也沒有覆蓋 pyc cache 受限環境。

### B3-4 — CI 對 binary/non-UTF changed files 會 crash；`--files` 未過 scannable filter

- **檔案/行號**: `.github/workflows/verify_claim.yml:51-54` 把所有 changed files 展開傳給 `--files`；`scripts/verification_claim_check.py:1226-1227` 對 explicit `--files` 直接 append；`scripts/verification_claim_check.py:1105-1108` 對每個 path 直接 `read_text(encoding="utf-8")`。
- **反例**: `printf '\xff\xfe\x00' > blob.bin; venv/bin/python scripts/verification_claim_check.py --files blob.bin` 直接 `UnicodeDecodeError`，exit 1。
- **影響**: PR/push 只要包含 binary 或非 UTF-8 檔案，CI 會紅在 traceback，不是 claim violation。這不是 fail-closed 的有效 enforcement，而是高誤報 blocker。
- **修法**: CI 的 `CHANGED` 只傳 scannable markdown path：`git diff --name-only ... -- HANDOFF.md 'handoffs/*.md' 'docs/*.md'` 類似做法。checker 端也應對 explicit `--files` 套 `_is_scannable_path()`，並對 unreadable/non-UTF 檔案回傳可診斷的 exit 2 或跳過非 scannable。
- **測試缺口**: Task prompt 要審 binary，現有 B3 測試沒有 binary/non-UTF changed file 反例。

## NON-BLOCKING

### NB-1 — `verify_task_provenance.py` regex 放寬與 legacy allowlist 目前未見新繞過

- **檔案/行號**: `scripts/verify_task_provenance.py:21-23`、`:31-59`、`:151-159`。
- **證據**: `handoffs/20260630-FF-P0FF3-RECONCILE.md:32-33` 兩個戳記為 `task:p0ff3-r2`，`bash scripts/reconcile_body_hash.sh handoffs/20260630-FF-P0FF3-RECONCILE.md` 輸出 `5da75188a4eebde3ef41a054462273e2c9958af27b5ad2b24dd7b1c3f72d93cd`，與 allowlist 一致。`venv/bin/python scripts/verify_task_provenance.py check-stamp ... --file handoffs/20260630-FF-P0FF3-RECONCILE.md` exit 0。
- **建議**: 可補一個單元測試鎖住 `task:p0ff3-r2` 不被截成 `p0ff3`，以及非 allowlist 的 `task:p0ff3-r2` 仍需 committee audit。

## Attack Surface Matrix

1. **3.1 hook 判定**: 部分 PASS。Edit/Write HANDOFF 假 claim probe 會擋；非 HANDOFF 會放。未發現 JSON parse fail-open。但 B3-3 使整體 hook/health 接線在當前交付狀態不可用。
2. **3.2 git hooks**: BLOCKING。B3-1 partial-stage 繞過；B3-2 code-only commit 假紅。commit-msg 會掃 body，這點 PASS。
3. **3.3 CI**: BLOCKING。B3-4 binary/non-UTF crash。未見 `continue-on-error` / `|| true`。
4. **3.4 health**: BLOCKING。B3-3 現狀真實 repo preflight 會 fail；`py_compile` 在受限 agent 環境假紅。
5. **測試牙齒**: BLOCKING。現有 12 項覆蓋 happy red/green，但缺 partial-stage、non-scannable commit、binary CI、受限 py_compile/preflight 交付狀態。
6. **回歸覆蓋**: 不足。Composer 報告的 67 passed 不能覆蓋以上反例；且本 review 未重跑全量，避免污染/超出只寫 handoff 約束。

## Probes Run

```
printf '## 正在做\n\n- align 已驗真紅\n' | venv/bin/python scripts/verification_claim_check.py --stdin-operational HANDOFF.md
# exit 1, fake operational claim blocked

printf '{"tool_name":"Write","tool_input":{"file_path":"HANDOFF.md","content":"## 正在做\n\n- align 已驗真紅\n"}}' | bash scripts/verify_pretooluse.sh
# exit 2, Write fake claim blocked

bash scripts/verify_hooks_health.sh
# exit 1, hooksPath unset + py_compile not loadable in current sandbox

bash scripts/agent_preflight.sh /tmp/b3-review-snap.txt
# exit 2, health failure; temp snapshot removed after probe

temp git repo partial-stage probe
# staged HANDOFF fake claim + clean working tree -> git commit exit 0 (bypass)

temp git repo code-only commit probe
# staged foo.py only -> git commit exit 1, "no input files"

binary --files probe
# UnicodeDecodeError on non-UTF blob, exit 1

venv/bin/python scripts/verify_task_provenance.py check-stamp ... task:p0ff3-r2 --file handoffs/20260630-FF-P0FF3-RECONCILE.md
# exit 0
```

## Structured Closeout

ASSUMPTIONS_VERIFIED: staged hook reads working tree not index; code-only commit fails; real repo hooksPath unset; health py_compile writes outside workspace cache in current sandbox; binary explicit --files crashes; p0ff3-r2 allowlist hash matches current reconcile body.  
TESTS_RUN: targeted probes above; no full pytest run.  
FAILURES_SEEN: probe failures are the findings; no repo state changes retained.  
SCOPE_CHANGES: none; review only, wrote only this handoff.  
NUMERIC_OR_SCHEMA_IMPACT: none.

VERDICT: CHANGES_REQUIRED
STATUS: DONE

---

## Closure Re-Review After Composer Fix

**Reviewer**: Codex  
**Date**: 2026-07-02  
**Scope**: 重跑本檔 4 個 BLOCKING 原反例 + B3-2 新繞過抽查 + B3 新測試牙齒。

### B3-1 — CLOSED
- 原反例重跑：temp repo staged `HANDOFF.md` fake claim，working tree 改回 clean note，再 commit。
- 結果：`git commit` exit 1；stderr 指向 `HANDOFF.md:3 operational claim 缺少 VERIFY/REF/SIGNOFF backing`。
- 判定：pre-commit 現在讀 staged index blob，不再被 working tree clean 內容繞過。
- 可證偽測試：`test_git_hook_rejects_partial_stage_fake_claim`。

### B3-2 — CLOSED
- 原反例重跑：temp repo 只 staged `foo.py`，commit message `feat: add foo`。
- 結果：`git commit` exit 0。
- 新繞過抽查：同一 commit staged `foo.py + HANDOFF.md(fake)` → exit 1；`foo.py + handoffs/evil.md(fake operational section)` → exit 1。
- 判定：`--staged` 的 no-scannable exit 0 只在 staged set 沒有 scoped scannable path 時生效；不能把 HANDOFF/handoffs operational 假 claim 夾在 code-only commit 內放過。`docs/*.md` 仍依既有 router 語境判斷，非 B3-2 no-scannable 分支。
- 可證偽測試：`test_git_hook_allows_code_only_commit`、`test_git_hook_rejects_fake_claim_handoff`。

### B3-3 — CLOSED
- 原反例重跑：真實 repo `core.hooksPath` unset 狀態下跑 `bash scripts/agent_preflight.sh /tmp/b3-closure-preflight-snap.txt`。
- 結果：exit 0；輸出 `HEALTH WARN: git verify hooks 未安裝 ... 安裝: bash scripts/install_verify_hooks.sh`，快照已刪除。
- `py_compile` 檢查：`rg -n "py_compile" ...` 無命中；`verify_hooks_health.sh` 使用 `ast.parse(pathlib.Path(...).read_text())`，未走 pyc 寫入路徑。
- 判定：交付狀態 preflight 可用；hook 未安裝被明確標為 WARN/setup 風險，不再誤判工具壞；已安裝但壞 hook 仍由測試覆蓋為 FAIL。
- 可證偽測試：`test_preflight_usable_without_hooks_installed`、`test_health_warns_without_hooks_installed`、`test_mutation_removed_precommit_checker_fails_health`。

### B3-4 — CLOSED
- 原反例重跑：`--files /tmp/.../blob.bin` 帶 binary。
- 結果：exit 2，stderr `verification_claim_check.py: no input files`，無 traceback。
- 補充重跑：`--files /tmp/.../docs/evil.md` 帶 non-UTF scannable markdown。
- 結果：exit 2，stderr `cannot read docs/evil.md: not valid UTF-8...`，無 traceback。
- 判定：binary/non-UTF 不再 crash；非 scannable binary 行為明確為 no input files，scannable non-UTF 行為明確為診斷型 exit 2。
- 可證偽測試：`test_explicit_files_binary_non_utf8_no_crash`、`test_explicit_files_non_scannable_skipped_no_crash`、`test_verify_claim_workflow_scannable_pathspec_only`。

## Tests / Probes Run

```
temp git repo partial-stage probe
# staged HANDOFF fake claim + clean working tree -> commit exit 1

temp git repo code-only probe
# staged foo.py only -> commit exit 0

temp git repo B3-2 abuse probe
# staged foo.py + HANDOFF fake -> commit exit 1
# staged foo.py + handoffs/evil.md fake operational section -> commit exit 1

bash scripts/agent_preflight.sh /tmp/b3-closure-preflight-snap.txt
# exit 0, HEALTH WARN for hooksPath unset, snapshot removed

rg -n "py_compile" scripts/verify_hooks_health.sh scripts/agent_preflight.sh scripts/agent_postflight.sh scripts/verification_claim_check.py
# no matches

venv/bin/python scripts/verification_claim_check.py --files /tmp/.../blob.bin
# exit 2, no traceback, no input files

venv/bin/python scripts/verification_claim_check.py --files /tmp/.../docs/evil.md
# exit 2, no traceback, cannot read / not valid UTF-8

pytest tests/governance/test_verify_gate_b3.py -q
# 20 passed

pytest tests/governance/ -q
# 75 passed
```

## Side Effects

- Temp repos and temp binary/preflight files removed after probes.
- Real repo `core.hooksPath` remained unset; no hook install/uninstall mutation performed.
- Final `git status --short` shows the same B3/FF WIP surface plus this appended review file; no probe artifacts retained.

## Closure Structured Closeout

ASSUMPTIONS_VERIFIED: B3-1 staged index is scanned; B3-2 code-only commit passes but mixed scoped fake claims reject; B3-3 real repo preflight is usable with hooks unset and health uses ast.parse not py_compile; B3-4 binary/non-UTF explicit files no longer traceback; B3 tests are falsifiable and governance suite passes.  
TESTS_RUN: targeted temp git probes above; `bash scripts/agent_preflight.sh /tmp/b3-closure-preflight-snap.txt` pass/WARN; `pytest tests/governance/test_verify_gate_b3.py -q` 20 passed; `pytest tests/governance/ -q` 75 passed.  
FAILURES_SEEN: none in closure; original four counterexamples now reproduce as expected closed behavior.  
SCOPE_CHANGES: none; appended closure to this review file only.  
NUMERIC_OR_SCHEMA_IMPACT: none.

FINAL VERDICT: APPROVED — B3-1/B3-2/B3-3/B3-4 CLOSED
STATUS: DONE
