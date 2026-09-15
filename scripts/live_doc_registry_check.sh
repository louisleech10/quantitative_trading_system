#!/usr/bin/env bash
# live_doc_registry_check.sh — DOCROT2 Task 1.1：活文件類別登記之檢查入口。
#   薄包裝；判定唯一實作在 scripts/_live_doc_registry.py（discover_live_docs／classify／validate_registry）。
#
# 用法：
#   bash scripts/live_doc_registry_check.sh --path <repo 相對路徑>   # 單檔分類；範圍外 rc=0
#   bash scripts/live_doc_registry_check.sh --all                    # 全樹清冊＋登記檔自身＋status_scope 涵蓋
#   bash scripts/live_doc_registry_check.sh --staged                 # 暫存之新增／重新命名 .md 須已登記
# rc：0＝合規或範圍外；1＝違規；2＝用法或環境錯誤（fail-closed）
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${SCRIPT_DIR}/../venv/bin/python"
if [ ! -x "${PY}" ]; then
  PY="$(command -v python3 || true)"
fi
if [ -z "${PY}" ]; then
  echo "live_doc_registry_check: 找不到 python3 ⇒ fail-closed" >&2
  exit 2
fi
exec "${PY}" "${SCRIPT_DIR}/_live_doc_registry.py" check "$@"
