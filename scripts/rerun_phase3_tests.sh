#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"
LOG_DIR="$ROOT_DIR/test_results"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
LOG_FILE="$LOG_DIR/phase3_rerun_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "找不到 Python 執行環境: $PYTHON_BIN"
  echo "請先建立並啟用 venv"
  exit 1
fi

cd "$ROOT_DIR"

exec > >(tee "$LOG_FILE") 2>&1

echo "========================================"
echo "Phase3 一鍵重跑開始"
echo "Root: $ROOT_DIR"
echo "Python: $PYTHON_BIN"
echo "Log: $LOG_FILE"
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

echo ""
echo "[1/3] 清除快取與覆蓋率暫存"
rm -rf .pytest_cache .coverage htmlcov
find . -name '.coverage.*' -type f -delete
find . -type d -name '__pycache__' -prune -exec rm -rf {} +

echo ""
echo "[2/3] Baseline 測試（不含 coverage）"
"$PYTHON_BIN" -m pytest \
  tests/momentum/Analysis \
  tests/momentum/Optimization \
  tests/api/test_model_api_endpoints.py \
  -q

echo ""
echo "[3/3] Coverage 測試（lightgbm_analyzer）"
"$PYTHON_BIN" -m pytest \
  tests/momentum/Analysis \
  tests/momentum/Optimization \
  tests/api/test_model_api_endpoints.py \
  --cov=momentum.Analysis.lightgbm_analyzer \
  --cov-report=term-missing \
  -q

echo ""
echo "========================================"
echo "Phase3 一鍵重跑完成"
echo "完成時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "完整 log: $LOG_FILE"
echo "========================================"
