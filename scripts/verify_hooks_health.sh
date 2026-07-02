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
checker="scripts/verification_claim_check.py"
if [ ! -x "$py" ]; then
  echo "HEALTH FAIL: $py missing or not executable" >&2
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

if [ "$fail" -eq 0 ]; then
  echo "HEALTH OK: verify gate hooks and tools present"
fi
exit "$fail"
