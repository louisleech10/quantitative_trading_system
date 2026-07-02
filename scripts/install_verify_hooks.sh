#!/usr/bin/env bash
# install_verify_hooks.sh — 冪等設定 core.hooksPath 指向 repo-tracked git hooks。
#
# 用法：
#   bash scripts/install_verify_hooks.sh          # 安裝
#   bash scripts/install_verify_hooks.sh --uninstall  # 還原（僅當指向 scripts/git_hooks）
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "install_verify_hooks: 不在 git repo" >&2
  exit 2
}
cd "$ROOT" || exit 2
HOOKS_REL="scripts/git_hooks"

if [ "${1:-}" = "--uninstall" ]; then
  current="$(git config --get core.hooksPath 2>/dev/null || true)"
  if [ "$current" = "$HOOKS_REL" ]; then
    git config --unset core.hooksPath
    echo "install_verify_hooks: 已還原 core.hooksPath"
  else
    echo "install_verify_hooks: core.hooksPath=${current:-<unset>}，非 $HOOKS_REL，跳過還原"
  fi
  exit 0
fi

git config core.hooksPath "$HOOKS_REL"
echo "install_verify_hooks: 已設定 core.hooksPath=$HOOKS_REL"
