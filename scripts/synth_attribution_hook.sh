#!/usr/bin/env bash
# synth_attribution_hook.sh — 收斂檔（synth.md）之**產出端**閘（PostToolUse on Write|Edit）。
#
# 病根（使用者 2026-09-11：「一堆 reconcile 和討論不就又沒做到？」）：主委八輪靠 scratchpad 手跑
#   「每個 finding ID 都進群集表」，那是紀律；既有 reconcile_cluster_attribution_check.sh 恆 rc=0。
#   本 hook＝VERDICTGATE Task 4.1 之最小可證偽產出端形態，先上；Task 4.1 實作時擴成引用 20 字＋處置 token。
#
# 判準（封閉）：對 handoffs/reconcile/*/synth.md 每次寫入——
#   ① 附錄每個 `## <FAMILY>-R<n>-P<x>-<nn>` 必出現在群集段某一表列（`|…|`）；
#   ② 目錄名含 `-x-`（SPEC/TODO/consult 層）者必有 `**修訂標的**：<path>` 行且該檔存在；
#   ③ 群集段仍含骨架佔位「（待填）」且附錄已有 ID ⇒ 視為未填（只在①②都過時才報，避免填寫中誤擋）。
#   任一紅 ⇒ rc=2 阻塞。
# 邊界：非 synth 路徑零成本 rc=0；hook 自身故障靜默放行；GOVERNANCE_TEST_HARNESS=1 時讀 SYNTH_HOOK_TARGET。
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

target=""
if [ "${GOVERNANCE_TEST_HARNESS:-}" = "1" ] && [ -n "${SYNTH_HOOK_TARGET:-}" ]; then
  target="${SYNTH_HOOK_TARGET}"
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
case "$rel" in handoffs/reconcile/*/synth.md) : ;; *) exit 0 ;; esac
[ -f "$rel" ] || exit 0

python3 - "$rel" <<'PY'
import os, re, sys
rel = sys.argv[1]
t = open(rel, encoding="utf-8").read()
head, _, app = t.partition("## 附錄")
ids = re.findall(r"^## ([A-Z]+-R\d+-P[0-3]-\d{2,})\s*$", app, re.M)
rows = [l for l in head.splitlines() if l.strip().startswith("|")]
errs = []
miss = [i for i in ids if not any(i in r for r in rows)]
if miss:
    errs.append(f"① 附錄有 ID 未列入群集表：{', '.join(miss)}")
session_dir = rel.split("/")[2]
if "-x-" in session_dir:
    m = re.search(r"^\*\*修訂標的\*\*：(\S+)$", head, re.M)
    if not m:
        errs.append("② -x- 層 synth 未宣告修訂標的（**修訂標的**：docs/<檔>.md）")
    elif "<填" in m.group(1) or not os.path.isfile(m.group(1)):
        errs.append(f"② 修訂標的未填或不存在：{m.group(1)}")
if not errs and ids and "（待填）" in head:
    errs.append("③ 群集段仍是骨架佔位「（待填）」")
if errs:
    print(f"[synth_attribution_hook] 🔴 {rel}")
    for e in errs:
        print("   " + e)
    print(f"   findings={len(ids)}；修好再繼續（這是 VERDICTGATE Task 4.1 之產出端最小版）")
    sys.exit(2)
print(f"[synth_attribution_hook] ✓ {rel} findings={len(ids)} 全在群集表")
PY
