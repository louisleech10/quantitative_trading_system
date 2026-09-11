#!/usr/bin/env bash
# reconcile_cluster_attribution_check.sh — 收斂檔群集歸戶**閘**（VERDICTGATE Task 4.1；SPEC C-1）。
#
# 用法：bash scripts/reconcile_cluster_attribution_check.sh <synth.md> [--todo <TODO.md>] [--report]
#   rc=0 通過；rc=1 逐條指名（stderr）；rc=2 用法／讀檔錯。
# 判準（全量；與 synth_attribution_hook.sh 同一模組 scripts/_synth_attr.py）：
#   ① 附錄每個 `## <ID>` 必列於群集表；② 該列逐字引用斷言前 20 Unicode 字（NFC、去空白、不寬容標點）；
#   ③ 該列第 4 欄含處置 token ∈ governance_verdicts.json.disposition_values；
#   ④ `延後→<目標>` 之目標須存在於 --todo 檔（缺 --todo 而有延後 ⇒ rc=1）；⑤ -x- 層必宣告修訂標的；⑥ 無骨架佔位。
# 歷史：2026-08-14 之前本腳本恆 rc=0（只印報告，票 B-36 具名寫死「沒有機械保護」）；Task 4.1 起為閘，
#   掛於 debt_clear.sh（completeness 之後、synth_xref 之前）。歷史 synth（已清債）不回改、不再跑。
set -u
cd "$(git rev-parse --show-toplevel)" || exit 2
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
[ $# -ge 1 ] || { echo "用法: reconcile_cluster_attribution_check.sh <synth.md> [--todo <TODO.md>] [--report]" >&2; exit 2; }
SYNTH="$1"; shift
[ -f "${SYNTH}" ] || { echo "ERROR: synth 不存在: ${SYNTH}" >&2; exit 2; }
exec python3 "${SCRIPT_DIR}/_synth_attr.py" "${SYNTH}" --mode gate "$@"
