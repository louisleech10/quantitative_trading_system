#!/usr/bin/env bash
# docrot2_metrics.sh — DOCROT2 Task 3.2（票 B-63）：成效報表入口。
#   薄包裝；計算唯一實作在 scripts/_docrot2_metrics.py report（契約＝scripts/docrot2_metric_contract.json）。
#   只讀 audit 與契約；交接重放以契約命令對 git 物件執行。不解析散文。
#
# 用法：bash scripts/docrot2_metrics.sh
# rc：0＝四條及格全過；1＝不及格、cohort 未定、缺事件、重複事件或事件／契約不合法（stderr 帶 DOCROT2_METRIC_REASON=<碼>）；
#     2＝用法錯。
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$#" -ne 0 ]; then
  echo "用法: bash scripts/docrot2_metrics.sh（無參數）" >&2
  exit 2
fi
cd "${SCRIPT_DIR}/.." || exit 2
exec python3 "${SCRIPT_DIR}/_docrot2_metrics.py" report
