#!/usr/bin/env bash

set -euo pipefail

# ⚠️ 編號對照(canonical 定義見 CLAUDE.md §The 7 Decoupling Rules):
#   本腳本抽驗 Rule 1/2/3 == canonical R1/R2/R3;
#   本腳本「Rule 6」(pytest tests/momentum/Strategy/ 可獨立跑) == canonical R6(測試不依賴 run_api.py)。
#   注意:另一支 check_decoupling.sh 的「Rule 6」語意不同(=callback bypass / named invariant Rule 9)。

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

error_count=0
PYTHON_BIN="${ROOT_DIR}/venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "❌ Python venv not found: $PYTHON_BIN"
  exit 1
fi

count_matches() {
  local pattern="$1"
  local target="$2"
  (grep -rEn --include='*.py' "$pattern" "$target" 2>/dev/null || true) | wc -l | tr -d ' '
}

echo "[Phase4.6.2] Decoupling checks start"

rule1_strategy_count="$(count_matches 'from api\.' 'momentum/Strategy')"
echo "Rule 1 (momentum/Strategy -> api.*): $rule1_strategy_count"
if [[ "$rule1_strategy_count" != "0" ]]; then
  echo "❌ Rule 1 violated in momentum/Strategy"
  error_count=$((error_count + 1))
fi

rule1_optimization_count="$(count_matches 'from api\.' 'momentum/Optimization')"
echo "Rule 1 (momentum/Optimization -> api.*): $rule1_optimization_count"
if [[ "$rule1_optimization_count" != "0" ]]; then
  echo "❌ Rule 1 violated in momentum/Optimization"
  error_count=$((error_count + 1))
fi

rule2_protocol_count="$(count_matches 'IBacktestEngine|IPositionSizer' 'momentum/Optimization/objectives/strategy_backtest.py')"
echo "Rule 2 (Protocol usage in strategy_backtest.py): $rule2_protocol_count"
if [[ "$rule2_protocol_count" -lt "1" ]]; then
  echo "❌ Rule 2 failed: protocol symbols not found"
  error_count=$((error_count + 1))
fi

rule3_backtest_factory="$(count_matches 'create_backtest_engine' 'momentum/factories.py')"
rule3_sizer_factory="$(count_matches 'create_position_sizer' 'momentum/factories.py')"
echo "Rule 3 (Factory create_backtest_engine): $rule3_backtest_factory"
echo "Rule 3 (Factory create_position_sizer): $rule3_sizer_factory"
if [[ "$rule3_backtest_factory" -lt "1" || "$rule3_sizer_factory" -lt "1" ]]; then
  echo "❌ Rule 3 failed: required factory functions not found"
  error_count=$((error_count + 1))
fi

echo "Rule 6 (independent tests): $PYTHON_BIN -m pytest tests/momentum/Strategy/ --no-header -q"
if ! "$PYTHON_BIN" -m pytest tests/momentum/Strategy/ --no-header -q; then
  echo "❌ Rule 6 failed: tests/momentum/Strategy/ did not pass"
  error_count=$((error_count + 1))
fi

if [[ "$error_count" -gt "0" ]]; then
  echo "[Phase4.6.2] FAILED with $error_count issue(s)"
  exit 1
fi

echo "[Phase4.6.2] PASSED"
