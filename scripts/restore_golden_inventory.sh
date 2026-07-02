#!/usr/bin/env bash
# 例行還原：測試跑完後把 golden inventory 的副作用改動還原（見 HANDOFF 慢測鐵律）。
# 只還原這一個檔案，不碰其他工作樹變更。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git checkout -- tests/golden/l65/test_inventory.txt
echo "restored: tests/golden/l65/test_inventory.txt"
