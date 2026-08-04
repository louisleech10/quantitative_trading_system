#!/usr/bin/env bash
# b15probe2.sh — B-15 第二段 alternation（claude[^|]*(-p|--print)）的誤擋重現。
# 2026-08-04：主委在唯讀查 push 結果時被實際擋下，據此定位。唯讀，不碰 repo 腳本。
set -u
RE='(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]|claude[^|]*(-p|--print)'

t() {
  local label="$1" cmd="$2" expect="$3"
  local got hit
  if printf '%s' "$cmd" | grep -Eq "$RE"; then got=BLOCK; else got=ALLOW; fi
  local mark; if [ "$got" = "$expect" ]; then mark="ok"; else mark="XX"; fi
  printf '%s %-5s want=%-5s | %s\n' "$mark" "$got" "$expect" "$label"
  if [ "$got" = "BLOCK" ]; then
    hit="$(printf '%s' "$cmd" | grep -Eo "$RE" | head -1 | cut -c1-70)"
    printf '        命中: %s\n' "$hit"
  fi
}

echo "===== 實際被擋的那條（2026-08-04 22:5x，唯讀查 push 結果）====="
t "head scratchpad + git rev-parse" \
  'head -3 "/private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/1a18e318/tasks/x.output"; git rev-parse --short origin/main' ALLOW

echo
echo "===== 拆解：哪一半才是兇手 ====="
t "只有 scratchpad 路徑（無 -p）" \
  'head -3 /private/tmp/claude-501/x/tasks/x.output' ALLOW
t "只有 git rev-parse（無 claude 路徑）" \
  'git rev-parse --short origin/main' ALLOW
t "scratchpad 路徑 + rev-parse（兩者併用）" \
  'head -3 /private/tmp/claude-501/x.output; git rev-parse --short HEAD' ALLOW

echo
echo "===== 同族：任何 -p 子字串都算 ====="
t "claude 路徑 + --porcelain" \
  'ls /private/tmp/claude-501/; git status --porcelain' ALLOW
t "claude 路徑 + rev-parse" \
  'cat .claude/tmp/x.txt; git rev-parse HEAD' ALLOW
t ".claude 相對路徑 + find -print" \
  'find .claude/tmp -name "*.md" -print' ALLOW
t ".claude 相對路徑 + --pretty" \
  'git log --pretty=oneline -3 .claude/gate/audit.log' ALLOW
t "backlog FP-3 原形：completeness --lock + claude 路徑 + -p" \
  'bash scripts/completeness_check.sh --lock /private/tmp/claude-501/sess; git rev-parse HEAD' ALLOW

echo
echo "===== 為什麼管線可以繞過（[^|] 不吃管線）====="
t "同一條指令但中間有管線" \
  'ls /private/tmp/claude-501/ | head -3; git rev-parse --short HEAD' ALLOW

echo
echo "===== TP：真的 claude 子代理，必須擋 ====="
t "claude -p 子代理" 'claude -p "do something"' BLOCK
t "claude --print" 'claude --print "x"' BLOCK
