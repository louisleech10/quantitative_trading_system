#!/usr/bin/env bash
# synth_attribution_hook.sh — 收斂檔（synth.md）之**產出端**閘（PostToolUse on Write|Edit）。
#
# 病根（使用者 2026-09-11：「一堆 reconcile 和討論不就又沒做到？」）：主委八輪靠 scratchpad 手跑
#   「每個 finding ID 都進群集表」，那是紀律；舊 reconcile_cluster_attribution_check.sh 恆 rc=0。
# VERDICTGATE Task 4.1（v3）：本 hook 與 debt_clear 前置閘**同一實作**（scripts/_synth_attr.py），本檔只是「寫入時子集」包裝：
#   check_ids ＋ check_target ＋ check_disposition(strict_defer=False：只驗 token 存在、不查延後目標)
#   ＋ check_quote20 **只對已完成列**（第 4 欄含處置 token；無 token 之列視為草稿不擋，避免中途存檔誤擋）
#   ＋ 骨架佔位（只在其餘皆過時才報）。debt_clear 跑全量（strict_defer=True＋全部非佔位列 quote20）。
# 任一紅 ⇒ rc=2 阻塞；理由一律走 stderr（harness 只回灌 stderr）。
# 邊界：非 synth 路徑零成本 rc=0；hook 自身故障（模組缺失／python 崩）靜默放行；GOVERNANCE_TEST_HARNESS=1 時讀 SYNTH_HOOK_TARGET。
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
MOD="${SYNTH_ATTR_MODULE:-scripts/_synth_attr.py}"
[ -f "${MOD}" ] || exit 0

python3 "${MOD}" "${rel}" --mode hook
rc=$?
case "${rc}" in
  0) exit 0 ;;
  1) echo "[synth_attribution_hook] 🔴 ${rel} 未過（VERDICTGATE Task 4.1 寫入時子集）；修好再繼續" >&2; exit 2 ;;
  *) exit 0 ;;   # 模組自身故障 ⇒ 靜默放行（誠實邊界：debt_clear 全量閘仍會擋）
esac
