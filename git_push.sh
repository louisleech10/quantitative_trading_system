#!/bin/bash
# Git 推送腳本

cd /Users/louis/Desktop/quantitative_trading_system

echo "=== 清理合併狀態 ==="
rm -f .git/MERGE_HEAD .git/MERGE_MSG .git/MERGE_MODE .git/AUTO_MERGE .git/.MERGE_MSG.swp
echo "合併狀態檔案已刪除"

echo ""
echo "=== 重置到 HEAD ==="
git reset --hard HEAD

echo ""
echo "=== 查看當前狀態 ==="
git status --short

echo ""
echo "=== 查看最近 commit ==="
git log --oneline -3

echo ""
echo "=== 推送到遠端 ==="
git push origin main

echo ""
echo "=== 完成 ==="
