#!/usr/bin/env bash
# live_doc_registry_update.sh — DOCROT2 Task 1.1：新增活文件之唯一登記交易。
#   薄包裝；判定與寫入唯一實作在 scripts/_live_doc_registry.py（update_add）。
#
# 用法：
#   bash scripts/live_doc_registry_update.sh --add <repo 相對路徑> [--class <類別>]
#     未給類別：已由 prefix 涵蓋 ⇒ rc=0 不寫入；否則依 `_schema.live_spec_predicate`
#     判定（docs/ 頂層且檔名含 SPEC／TODO／PLAN ⇒ LIVE-SPEC，其餘 ⇒ `_schema.default_class`）。
#     寫入後 exact 依（類別, 路徑）之 UTF-8 位元組排序，輸出決定性。
# rc：0＝已登記或不需登記；1＝拒絕（已登記、範圍外、類別不合、登記後不合規）；2＝用法或環境錯誤
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${SCRIPT_DIR}/../venv/bin/python"
if [ ! -x "${PY}" ]; then
  PY="$(command -v python3 || true)"
fi
if [ -z "${PY}" ]; then
  echo "live_doc_registry_update: 找不到 python3 ⇒ fail-closed" >&2
  exit 2
fi
exec "${PY}" "${SCRIPT_DIR}/_live_doc_registry.py" update "$@"
