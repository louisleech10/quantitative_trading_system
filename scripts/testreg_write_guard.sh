#!/usr/bin/env bash
# testreg_write_guard.sh — TESTREG 產出端登記檢查（PostToolUse Edit|Write；docs/TESTREG_SPEC.md Task 1.5）。
#
# 用法：
#   bash scripts/testreg_write_guard.sh     # hook 模式（stdin＝PostToolUse payload，取 .tool_input.file_path）
#   rc 0＝非管轄之檔，或檢查通過／2＝檢查未過（訊息回給寫入者）
#
# 管轄（路徑相對本檔所在 repo 根；repo 由本檔位置推導，不讀環境變數）：
#   tests/**/test_*.py 或 tests/registry/catalog.json ⇒ testreg.py check --paths <p>
#   docs/manifests/*.json                              ⇒ testreg.py check --manifest <p>
#   tests/ 下其他 .py（conftest、fixtures、helper）     ⇒ testreg.py check --helpers <p>
#   tests/registry/ 之非 .py 契約檔                     ⇒ testreg.py validate
#   其餘路徑一律放行（rc 0）。hook 內不跑 pytest、不讀 git 全史。
#
# TODO 凍結之介面（docs/manifests/TESTREG.json）：本檔目前為空殼，第 1 批實作並掛載於 .claude/settings.json。
set -u
cat >/dev/null
echo "testreg_write_guard: 未實作（TESTREG Task 1.5）" >&2
exit 2
