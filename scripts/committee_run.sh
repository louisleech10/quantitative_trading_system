#!/usr/bin/env bash
# committee_run.sh — 一次完成「開 gate token → 平行派 N 家委員 → 等全部完成 → 逐家回報」。
#
# 為何存在(2026-07-25):每輪派工原需 gate.sh + cx_run×N + 逐檔讀 = 4~6 個動作;
#   本 session 跑了 ~10 輪。收斂成單一命令,且**家族數完全動態**(2/3/4…N 家皆可)。
#
# 家族**不寫死**:逐個對 SoT `scripts/governance_families.json` 驗證 →
#   未來在 SoT 加一家,本腳本一字不用改。
#   (誠實邊界:新家族仍須在 cx_run.sh 補該 CLI 的呼叫配方——各 CLI 參數不同,無法通用化。)
#
# 用法:
#   bash scripts/committee_run.sh <brief> <out前綴> <fam1,fam2,...> -- <gate.sh dispatch 的 flags...>
# 例:
#   bash scripts/committee_run.sh handoffs/X-BRIEF.md handoffs/20260725-xreview codex,composer,grok -- \
#     --intent "..." --risk low --facts-asked "..." --review-role "..." --template "n/a: 用 brief"
#
# 產出:<out前綴>-<family>.md(檔名帶家族後綴 → reconcile_build.sh 可直接吃)
#      <out前綴>-<family>.runlog(該家執行 log;失敗時自動印 tail)
# Claude 用法:以 Bash run_in_background:true 執行本腳本(勿自行加 `&`);全部跑完會一次通知。
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

usage() {
  echo "用法: bash scripts/committee_run.sh <brief> <out前綴> <fam1,fam2,...> -- <gate dispatch flags...>" >&2
}

brief="${1:-}"; out_prefix="${2:-}"; fams_csv="${3:-}"
[ -n "${brief}" ] && [ -n "${out_prefix}" ] && [ -n "${fams_csv}" ] || { usage; exit 2; }
shift 3
if [ "${1:-}" = "--" ]; then shift; fi
[ "$#" -ge 1 ] || { echo "ERROR: 缺 gate.sh dispatch flags(-- 之後)" >&2; usage; exit 2; }

[ -f "${brief}" ] || { echo "ERROR: brief 不存在: ${brief}" >&2; exit 2; }
case "${out_prefix}" in handoffs/*) : ;; *) echo "ERROR: out前綴須在 handoffs/: ${out_prefix}" >&2; exit 2 ;; esac

# --- 家族驗證(對 SoT,非硬編) ---
# shellcheck source=/dev/null
. "${SCRIPT_DIR}/governance_families.sh" || { echo "ERROR: 無法載入 family SoT(fail-closed)" >&2; exit 1; }
valid_fams="$(families_get families ' ')" || { echo "ERROR: 讀 SoT families 失敗(fail-closed)" >&2; exit 1; }
advisory="$(families_get advisory_only ' ' 2>/dev/null || echo "")"

fams="$(printf '%s' "${fams_csv}" | tr ',' ' ')"
n_fams=0
for f in ${fams}; do
  case " ${valid_fams} " in
    *" ${f} "*) : ;;
    *) echo "ERROR: 未知家族 '${f}'(SoT 合法值: ${valid_fams})。新增家族請改 scripts/governance_families.json + cx_run.sh 配方" >&2; exit 2 ;;
  esac
  case " ${advisory} " in
    *" ${f} "*) echo "[committee_run] ⚠️ ${f} 為 advisory_only:諮詢性質,**不計入 quorum**" ;;
  esac
  n_fams=$((n_fams + 1))
done
[ "${n_fams}" -ge 1 ] || { echo "ERROR: 家族清單為空" >&2; exit 2; }

echo "[committee_run] brief=${brief}  families=${fams_csv}(${n_fams} 家)  out=${out_prefix}-<family>.md"

# --- 1) 開 gate token(fail-closed:沒過就不派) ---
echo "[committee_run] === gate.sh dispatch ==="
bash "${SCRIPT_DIR}/gate.sh" dispatch "$@" || {
  echo "ERROR: gate 未放行 → 不派工(fail-closed)" >&2; exit 1; }

# --- 2) 平行派 N 家(索引陣列配對 pid↔family;bash 3.2 相容) ---
PIDS=()
FAMS=()
for f in ${fams}; do
  out="${out_prefix}-${f}.md"
  log="${out_prefix}-${f}.runlog"
  echo "[committee_run] → 派 ${f}(out=${out})"
  bash "${SCRIPT_DIR}/cx_run.sh" "${f}" "${brief}" "${out}" >"${log}" 2>&1 &
  PIDS+=("$!")
  FAMS+=("${f}")
done

# --- 3) 等全部完成 + 逐家回報 ---
rc_all=0
idx=0
while [ "${idx}" -lt "${#PIDS[@]}" ]; do
  pid="${PIDS[${idx}]}"
  fam="${FAMS[${idx}]}"
  idx=$((idx + 1))
  if wait "${pid}"; then
    out="${out_prefix}-${fam}.md"
    if [ -s "${out}" ]; then
      echo "[committee_run] ✅ ${fam} 完成 → ${out}"
    else
      echo "[committee_run] ⚠️ ${fam} rc=0 但產出缺/空: ${out}(檢查 ${out_prefix}-${fam}.runlog)" >&2
      rc_all=1
    fi
  else
    echo "[committee_run] ❌ ${fam} 失敗(見下 log tail)" >&2
    tail -15 "${out_prefix}-${fam}.runlog" 2>/dev/null | sed 's/^/    /' >&2
    rc_all=1
  fi
done

if [ "${rc_all}" -eq 0 ]; then
  echo "[committee_run] ✅ ${n_fams} 家全數完成。接著:bash scripts/reconcile_build.sh <session> ${out_prefix}-*.md"
else
  echo "[committee_run] ⚠️ 有家族未正常完成 — 勿當作已收齊(見上)" >&2
fi
exit "${rc_all}"
