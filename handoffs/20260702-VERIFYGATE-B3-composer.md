# VERIFYGATE B3 — Composer 實作收尾

**Task**: B3 (Task 3.1/3.2/3.3/3.4)  
**Agent**: Composer 2.5  
**Date**: 2026-07-02

## 逐 Task 檔案清單

| Task | 檔案 | 動作 |
|------|------|------|
| 3.1 | `scripts/verify_pretooluse.sh` | 新增 — PreToolUse JSON stdin；僅 Edit/Write + HANDOFF/handoffs；違規 exit 2 |
| 3.1 | `.claude/settings.json` | 增一條 PreToolUse hook（Edit\|Write → verify_pretooluse）；既有 gate_check 未動 |
| 3.1 | `scripts/verification_claim_check.py` | 增 `--stdin-operational` + `check_stdin_operational()`（3.1 管線必要） |
| 3.2 | `scripts/git_hooks/pre-commit` | 新增 — `--staged` |
| 3.2 | `scripts/git_hooks/commit-msg` | 新增 — `--commit-msg $1` |
| 3.2 | `scripts/install_verify_hooks.sh` | 新增 — 冪等 `core.hooksPath=scripts/git_hooks` + `--uninstall` |
| 3.3 | `.github/workflows/verify_claim.yml` | 新增 — PR/push；`--range` + `--files`；無 continue-on-error/\|\| true |
| 3.4 | `scripts/verify_hooks_health.sh` | 新增 — hooksPath/hook/jq/python/py_compile checker/pretooluse |
| 3.4 | `scripts/agent_preflight.sh` | 加一行 `verify_hooks_health.sh` |
| 3.4 | `scripts/agent_postflight.sh` | 加一行 `verify_hooks_health.sh` |
| 測試 | `tests/governance/test_verify_gate_b3.py` | 新增 12 項（含 mutation 探針） |

## ASSUMPTIONS_VERIFIED

- V7 誤報=0 已達標（`test_v7_false_positive_zero_on_spec_files` 綠）→ PreToolUse 全量啟用，未降級。
- PreToolUse hook JSON 欄位：`tool_name`、`tool_input.file_path`、`tool_input.new_string`（Edit）、`tool_input.content`（Write）；實測 `verify_pretooluse.sh` 模擬 JSON 行為符合預期。
- `yaml.safe_load` 將 GitHub Actions 的 `on:` 解析為 `True` 鍵；測試用 `data.get("on") or data.get(True)`。
- health import 檢查：`importlib.exec_module` 在 symlink 路徑下因 dataclass 失敗；改 `py_compile` 後 temp repo health 綠。
- 真實 repo **未**執行 `install_verify_hooks.sh`；`core.hooksPath` 測試僅在 temp git repo。

## TESTS_RUN

```
pytest tests/governance/test_verify_gate_b3.py -q --tb=short
# 12 passed in 2.90s

pytest tests/governance/ -q --tb=line
# 67 passed in 12.71s

bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md
# TEMPLATE PASS

bash scripts/template_check.sh todo docs/VERIFY_GATE_TODO.md
# TEMPLATE PASS

bash scripts/reconcile_stamps_check.sh handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md
# RECONCILE-STAMP PASS
```

## FAILURES_SEEN

- Round 1：`verify_hooks_health.sh` importlib 載入失敗 → 改 `py_compile`。
- Round 1：YAML `on` 鍵 KeyError → 測試修正。
- Round 1：`guard_real_repo_state` per-test 與並發 audit.log 寫入 flake → 改 module scope。

## SCOPE_CHANGES

- `scripts/verification_claim_check.py`：增 `--stdin-operational`（TODO 3.1 明列管線，非弱化 B2）。

## NUMERIC_OR_SCHEMA_IMPACT

- none（無 momentum/api/frontend/數值/schema 變更）

## 啟用說明

1. PreToolUse：需 **session 重啟** + 使用者 `/hooks` 核准 `.claude/settings.json` 新條目。
2. Git hooks：使用者自行 `bash scripts/install_verify_hooks.sh`（本實作未對真實 repo 設 hooksPath）。
3. CI：`verify_claim.yml` 隨 push/PR 自動跑。

STATUS: DONE
