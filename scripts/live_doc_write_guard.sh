#!/usr/bin/env bash
# live_doc_write_guard.sh — DOCROT2 Task 2.1–2.4（票 B-63）：活文件寫入判定入口。
#   薄包裝；判定唯一實作在 scripts/_live_doc_write_guard.py（手寫狀態判定碼另與 gen_fact_key_blocks.sh 共用）。
#
# 用法：
#   bash scripts/live_doc_write_guard.sh                          # PreToolUse Edit|Write hook（stdin＝payload）
#   bash scripts/live_doc_write_guard.sh --staged                 # pre-commit：暫存之登記活文件
#   bash scripts/live_doc_write_guard.sh --tree <commit> --path <p>  # 以該 commit 之檔重放交接檔全文判定
# rc：hook 模式 0＝放行／2＝擋；--staged／--tree 0＝合規／1＝違規／2＝用法或環境錯誤
# 🔴 無略過旗標、無環境變數逃生口。
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${SCRIPT_DIR}/../venv/bin/python"
if [ ! -x "${PY}" ]; then
  PY="$(command -v python3 || true)"
fi
if [ -z "${PY}" ]; then
  echo "live_doc_write_guard: 找不到 python3 ⇒ fail-closed" >&2
  exit 2
fi
exec "${PY}" "${SCRIPT_DIR}/_live_doc_write_guard.py" "$@"
