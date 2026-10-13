#!/usr/bin/env bash
# TESTREG b3 Task 3.1 歸因探針：git bisect run 用之單一 nodeid 判定（於 worktree 根執行；venv／data_cache 以 symlink 指回主工作樹）。
# 用法：git bisect run bash <本檔絕對路徑> <nodeid>
# rc：0＝passed（good）、1＝failed（bad）、125＝收集錯誤或其他（skip）。
set -u
NODE="$1"
# numba 快取導到暫存（repo 內已追蹤之 __pycache__ 被改寫會使 bisect 無法切換提交）；跑完還原本 worktree 之追蹤檔
NUMBA_CACHE_DIR=$(mktemp -d)
export NUMBA_CACHE_DIR
OUT=$(venv/bin/python -m pytest -q -p no:cacheprovider -p no:testreg_recorder "$NODE" 2>&1)
git checkout -q -- . 2>/dev/null
rm -rf "$NUMBA_CACHE_DIR"
if printf '%s\n' "$OUT" | grep -qE '^[0-9]+ passed'; then exit 0; fi
if printf '%s\n' "$OUT" | grep -qE '^[0-9]+ failed'; then exit 1; fi
if printf '%s\n' "$OUT" | grep -qE '(^| )1 failed'; then exit 1; fi
if printf '%s\n' "$OUT" | grep -qE '(^| )1 passed'; then exit 0; fi
exit 125
