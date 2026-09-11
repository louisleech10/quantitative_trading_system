#!/usr/bin/env bash
# spec_xref_hook.sh — spec_xref_check 之**產出端**掛載（PostToolUse on Write|Edit）。
#
# 為何不只掛 pre-commit／debt_clear（使用者 2026-09-11 當面質問）：那兩處是輪級消費端——
#   一輪內主委可 Edit SPEC 十幾次，錯誤要到 commit 才看到；違反 CLAUDE.md「治理檢查必須擋在
#   產出端」鐵律。本 hook 在**每次寫 SPEC/TODO 當下**跑兩道：
#   ① 對 HEAD 版做殘留掃描（spec_xref_check --files）；
#   ② 找「宣告以本檔為修訂標的」之最新 synth，跑處置對證（--synth）。
#   任一紅 ⇒ rc=2（阻塞）並印出，主委不能往下寫。pre-commit／debt_clear 降為後備。
#
# 邊界：①只對 docs/*SPEC*.md｜docs/*TODO*.md（其他路徑零成本 rc=0）；②HEAD 無此檔（新檔）⇒ 跳過①；
#   ③無 synth 宣告本檔 ⇒ 跳過②；④hook 自身故障（python 缺、stdin 壞）⇒ 靜默放行，不得因自己壞而擋工作；
#   ⑤GOVERNANCE_TEST_HARNESS=1 時讀 SPEC_XREF_HOOK_TARGET 取代 stdin（測試用，非逃生口——仍照常判定）。
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0
CHECK="scripts/spec_xref_check.sh"; [ -f "$CHECK" ] || exit 0

target=""
if [ "${GOVERNANCE_TEST_HARNESS:-}" = "1" ] && [ -n "${SPEC_XREF_HOOK_TARGET:-}" ]; then
  target="${SPEC_XREF_HOOK_TARGET}"
else
  [ -t 0 ] && exit 0
  target="$(python3 -c 'import json,signal,sys
signal.alarm(5)
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit(0)
ti = d.get("tool_input") or {}
p = ti.get("file_path") or ti.get("path") or ""
print(p if isinstance(p, str) else "")' 2>/dev/null || true)"
fi
[ -n "$target" ] || exit 0
case "$target" in /*) rel="${target#"$ROOT"/}" ;; *) rel="$target" ;; esac
# 觸發集合（使用者 2026-09-11：不限 SPEC/TODO；偵察／討論與審 SPEC 同等）：
#   docs/ 下 SPEC|TODO|PLAN|RECON 命名者，或**任何目錄**下被某份 synth 宣告為修訂標的之 .md
#   （consult 層的標的常是主委偵察稿 handoffs/*-RECON-claude.md）。
case "$rel" in *.md) : ;; *) exit 0 ;; esac
[ -f "$rel" ] || exit 0
declared="$(grep -l -m1 -E "^\*\*修訂標的\*\*：${rel}\$" handoffs/reconcile/*/synth.md 2>/dev/null | head -1)"
case "$rel" in docs/*SPEC*.md|docs/*TODO*.md|docs/*PLAN*.md|docs/*RECON*.md) : ;; *) [ -n "$declared" ] || exit 0 ;; esac

rc=0
# ① 殘留掃描 vs HEAD
if git cat-file -e "HEAD:${rel}" 2>/dev/null; then
  tmp_old="$(mktemp)"; git show "HEAD:${rel}" > "$tmp_old"
  bash "$CHECK" --files "$tmp_old" "$rel"; r=$?; rm -f "$tmp_old"
  [ "$r" -eq 0 ] || rc=2
fi
# ② 最新宣告本檔為修訂標的之 synth
synth="$(grep -l -m1 -E "^\*\*修訂標的\*\*：${rel}\$" handoffs/reconcile/*/synth.md 2>/dev/null | xargs -I{} ls -t {} 2>/dev/null | head -1)"
if [ -n "$synth" ]; then
  bash "$CHECK" --synth "$synth" "$rel"; r=$?
  [ "$r" -eq 0 ] || rc=2
fi
if [ "$rc" -ne 0 ]; then
  echo "[spec_xref_hook] 🔴 ${rel}：改一處漏一處——上列殘留或 synth 處置未同步，修掉再繼續" >&2
fi
exit "$rc"
