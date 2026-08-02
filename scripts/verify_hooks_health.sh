#!/usr/bin/env bash
# verify_hooks_health.sh — 偵測驗收防偽閘本身是否壞掉（fail-closed）。
#
# 檢查：core.hooksPath、hook 檔存在可執行含 checker 調用、jq、venv python、checker 可載入。
# 未安裝 hooks → WARN + exit 0（附 setup 指引，與「工具壞掉」區分）。
# 已安裝但缺件/被掏空 → FAIL exit 1。
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "HEALTH FAIL: 不在 git repo" >&2
  exit 1
}
cd "$ROOT" || exit 1

hooks_path="$(git config --get core.hooksPath 2>/dev/null || true)"
if [ "$hooks_path" != "scripts/git_hooks" ]; then
  echo "HEALTH WARN: git verify hooks 未安裝 (core.hooksPath=${hooks_path:-<unset>})" >&2
  echo "  安裝: bash scripts/install_verify_hooks.sh" >&2
  echo "  殘餘風險: commit 時不會執行 pre-commit claim checker" >&2
  exit 0
fi

fail=0

for hook in pre-commit commit-msg; do
  hp="scripts/git_hooks/$hook"
  if [ ! -f "$hp" ]; then
    echo "HEALTH FAIL: missing $hp" >&2
    fail=1
  elif [ ! -x "$hp" ]; then
    echo "HEALTH FAIL: $hp not executable" >&2
    fail=1
  elif ! grep -q 'verification_claim_check' "$hp"; then
    echo "HEALTH FAIL: $hp missing verification_claim_check invocation" >&2
    fail=1
  fi
done

if ! command -v jq >/dev/null 2>&1; then
  echo "HEALTH FAIL: jq not in PATH" >&2
  fail=1
fi

py="venv/bin/python"
[ -x "$py" ] || py="$(command -v python3 || command -v python)"  # 無 venv(如 CI)→ 系統 python3
checker="scripts/verification_claim_check.py"
if [ -z "$py" ]; then
  echo "HEALTH FAIL: python (venv 或系統) missing" >&2
  fail=1
elif [ ! -f "$checker" ]; then
  echo "HEALTH FAIL: $checker missing" >&2
  fail=1
else
  if ! "$py" -c "import ast, pathlib; ast.parse(pathlib.Path('$checker').read_text())" 2>/dev/null; then
    echo "HEALTH FAIL: verification_claim_check.py not loadable" >&2
    fail=1
  fi
fi

pretooluse="scripts/verify_pretooluse.sh"
if [ ! -f "$pretooluse" ]; then
  echo "HEALTH FAIL: missing $pretooluse" >&2
  fail=1
elif [ ! -x "$pretooluse" ]; then
  echo "HEALTH FAIL: $pretooluse not executable" >&2
  fail=1
fi

# GOV-DOC-CHECK-AT-WRITE（2026-08-02，CODEX-R2-P1-01）：治理文件格式檢查鏈。
# 這三支彼此呼叫（doc_format_precheck → template_check / brief_conformance_check），
# 且 doc_format_precheck 掛在 PostToolUse、被 gov_check 1b 段呼叫。
# **少任一支就代表格式防線有洞**，故納入 health gate；不做語法檢查（gov_check 1 段已做）。
for _f in scripts/doc_format_precheck.sh scripts/template_check.sh scripts/brief_conformance_check.sh; do
  if [ ! -f "$_f" ]; then
    echo "HEALTH FAIL: missing $_f (治理文件格式檢查鏈)" >&2
    fail=1
  fi
done
# ⚠️ 掛載檢查**必須 fail-closed**（CODEX-R3-P1-01）：第一版寫成
#   `[ -f settings ] && command -v jq && ...`，settings 不存在就**靜默通過** ⇒ 刪掉設定檔即可讓
#   health 回綠。且第一版只查 command 字串、**不查 matcher** ⇒ 把 checker 掛到
#   非 `Edit|Write` 的 matcher 底下（等於永不觸發）仍判健康。兩者都是 fail-open。
# 判準改為：同一個 PostToolUse 條目**同時**滿足 matcher 含 Edit 與 Write、且其 command 含 doc_format_precheck。
if [ ! -f .claude/settings.json ]; then
  echo "HEALTH FAIL: 缺 .claude/settings.json（無法確認產出端檢查已上線）→ fail-closed" >&2
  fail=1
elif ! command -v jq >/dev/null 2>&1; then
  # 前段已對缺 jq 報 FAIL；此處不重複計數，但明講本檢查未執行，避免看起來像通過
  echo "HEALTH FAIL: jq 缺席，無法驗證 PostToolUse 掛載（見上）" >&2
  fail=1
elif ! jq -e '
      [ .hooks.PostToolUse[]?
        | select(((.matcher // "") | test("Edit")) and ((.matcher // "") | test("Write")))
        | .hooks[]?.command ]
      | any(test("doc_format_precheck"))' .claude/settings.json >/dev/null 2>&1; then
  echo "HEALTH FAIL: .claude/settings.json 未在 PostToolUse 的 Edit|Write matcher 下掛 doc_format_precheck.sh" >&2
  echo "  （掛到別的 matcher＝永不觸發；產出端檢查形同未上線）" >&2
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "HEALTH OK: verify gate hooks and tools present"
fi
exit "$fail"
