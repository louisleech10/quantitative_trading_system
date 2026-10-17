#!/usr/bin/env bash
# test_change_review.sh — 測試刪改之「待審清單」（使用者 2026-10-17 逐字「我要跟業界做法一樣，以後不准有任何一次同樣
#   事情再次發生」「同意小任務也一定要派委員審清單」）。pre-commit 將 TESTREG V01／V07／V15／V19／V20 之清單登記為
#   .testreg/test_change_review/tree-<tree>.txt；post-commit 改名為 pending-<sha>.txt；pre-push 擋未審者。
#
# 用法：
#   bash scripts/test_change_review.sh bind              # post-commit：HEAD 之 tree 若有待審清單 ⇒ 綁 HEAD sha
#   bash scripts/test_change_review.sh check             # pre-push：有 pending ⇒ rc 1 並列出
#   bash scripts/test_change_review.sh mark <sha> <synth> # 委員審清單之收斂檔已含該 sha ⇒ 標已審
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 2
D=.testreg/test_change_review
case "${1:-}" in
  bind)
    t="$D/tree-$(git rev-parse 'HEAD^{tree}').txt"
    [ -f "$t" ] && mv "$t" "$D/pending-$(git rev-parse HEAD).txt"
    exit 0 ;;
  check)
    [ -d "$D" ] || exit 0
    n=0
    for p in "$D"/pending-*.txt; do
      [ -e "$p" ] || continue
      sha="${p##*/pending-}"; sha="${sha%.txt}"
      echo "  未審：commit ${sha:0:8}（$(wc -l < "$p" | tr -d ' ') 項測試刪改）清單 $p" >&2
      n=$((n + 1))
    done
    [ "$n" -eq 0 ] && exit 0
    echo "pre-push: ✗ 有含測試刪改之 commit 未經委員審清單 → 拒 push。派審後：bash scripts/test_change_review.sh mark <sha> <收斂檔>" >&2
    exit 1 ;;
  mark)
    sha="${2:-}"; synth="${3:-}"
    p="$D/pending-$sha.txt"
    [ -f "$p" ] || { echo "無待審清單：$p" >&2; exit 2; }
    [ -f "$synth" ] || { echo "收斂檔不存在：$synth" >&2; exit 2; }
    grep -q "${sha:0:8}" "$synth" || { echo "收斂檔未提及 commit ${sha:0:8}" >&2; exit 2; }
    ls "$(dirname "$synth")/sources/"*.md > /dev/null 2>&1 || { echo "收斂檔無委員來源（sources/*.md）" >&2; exit 2; }
    printf 'reviewed_by=%s\n' "$synth" >> "$p"
    mv "$p" "$D/reviewed-$sha.txt"
    echo "已標已審：${sha:0:8}" ;;
  *)
    sed -n 2,11p "$0"; exit 2 ;;
esac
