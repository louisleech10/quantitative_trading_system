#!/bin/zsh
# 盤點 data_cache/features 各 run 之 config_hash 被 tests／momentum／api／scripts／frontend/src 引用之處（唯讀）。
REPO=/Users/louis/Desktop/quantitative_trading_system
for d in $REPO/data_cache/features/*/*/*(/); do
  h=${d:t}
  s=${h[1,8]}
  files=$(grep -rl "$s" $REPO/tests $REPO/momentum $REPO/api $REPO/scripts $REPO/frontend/src 2>/dev/null | grep -v "\.pyc$\|/logs/" | sed "s|$REPO/||")
  n=$(printf '%s' "$files" | grep -c . )
  echo "${d#$REPO/data_cache/features/} refs=$n $(printf '%s' "$files" | head -4 | tr '\n' ' ')"
done
