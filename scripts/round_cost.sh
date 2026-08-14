#!/usr/bin/env bash
# round_cost.sh — 委員輪成本量測：一件事花了幾輪、其中幾輪白跑。
#
# 為何存在（2026-08-14T17:10+08:00，使用者問「散文那類問題耗掉幾十小時，你判斷得出來嗎」）：
#   主委當下答不出來，只能憑印象。憑印象的成本估計無法支撐「哪些票該做、哪些不做」的取捨，
#   而那正是使用者面對 61 張票時最需要的判斷。
#
# 🔴 單位是「輪」不是「小時」（實測後改的）：
#   初版用開輪到銷帳的牆鐘時間，實測最長一輪 37 小時——那是行事曆跨度，
#   含睡覺與等待，**被污染**。輪數則乾淨：一輪 ≈ 三家 CLI 各跑一次 ＋ 主委收斂一次，
#   開銷相對固定，且每輪有唯一 round_id、開與結都有事件、配對率實測 100%。
#
# 用法：
#   bash scripts/round_cost.sh                 # 全域摘要 ＋ 依工作項目排序
#   bash scripts/round_cost.sh --item <名>     # 單一工作項目（供派工前顯示）
#   bash scripts/round_cost.sh --nofind-audit  # 抽驗「預期零 findings」標籤之真偽
#
# 🔴 誠實邊界：
#   ① 只涵蓋 JSON 期。稽核紀錄多數行為舊格式純文字，解析不到（跑 --summary 會印實際比例）。
#   ② 歸戶到**工作項目**（session 主題），不是票號——一輪常同時處理多票，
#      票級歸屬已由票 B-48／B-37 判為現有資料上不可得。
#   ③ 「無 findings」不等於「該輪沒價值」：戳記輪本來就不產 findings。
#      要分辨標籤真偽請用 --nofind-audit。
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2
LOG=".claude/gate/audit.log"
[ -f "${LOG}" ] || { echo "round_cost: 缺 ${LOG}" >&2; exit 2; }

# 零 findings 之 **sentinel 形態**＝`## <FAMILY>-R<n>-P3-00`
# （逐字定義見 templates/COMMITTEE_FINDING_TEMPLATE.md 之「零 findings 怎麼寫」節）。
# 🔴 它是「合法的沒有 findings」，**不是** finding；初版判準未排除它，
#   把 4 輪合法 sentinel 誤判為「標籤不實」（24 → 20）。
_RC_FINDING_RE='^#{2,6}[[:space:]]+[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}'
_RC_SENTINEL_RE='P3-00$'

_rc_rows() {   # round_id \t event \t session \t abandon_kind \t expected_outputs
  LC_ALL=C grep -E '^\{' "${LOG}" \
    | LC_ALL=C jq -r '
        select(.round_id != null)
        | [ .round_id, .event, (.session_name // "?"), (.abandon_kind // ""),
            ((.expected_outputs // {}) | to_entries | map(.value) | join(",")) ]
        | @tsv' 2>/dev/null
}

# 工作項目＝session 主題（剝掉日期與輪次後綴，使同主題的多輪合併）
_rc_topic_awk='
  function topic(s) {
    sub(/-x-[a-z]+-r[0-9]+$/, "", s)
    sub(/-(rev|stamp|fix|impl|dev|supp|clos|consult)[a-z0-9]*$/, "", s)
    sub(/^[0-9]{8}-/, "", s)
    return s
  }'

_rc_tally() {   # stdout: 輪數 \t 白跑 \t 無finding \t 銷帳 \t 工作項目
  _rc_rows | LC_ALL=C awk -F'\t' "${_rc_topic_awk}"'
      $2=="committee_round_open" { ss[$1]=topic($3); next }
      $2=="committee_debt_clear" { ft[$1]="ok"; next }
      $2=="debt_abandon"         { ft[$1]=($4=="collection-failed" ? "waste" : "nofind"); next }
      END {
        for (r in ss) {
          s=ss[r]; n[s]++
          if (ft[r]=="waste")  w[s]++
          if (ft[r]=="nofind") f[s]++
          if (ft[r]=="ok")     k[s]++
        }
        for (s in n) printf "%d\t%d\t%d\t%d\t%s\n", n[s], w[s]+0, f[s]+0, k[s]+0, s
      }' | LC_ALL=C sort -rn
}

_rc_summary() {
  _rc_tally | LC_ALL=C awk -F'\t' '
      BEGIN { printf "%-5s %-5s %-9s %-5s %s\n", "總輪", "白跑", "無finding", "銷帳", "工作項目" }
      { printf "%-5d %-5d %-9d %-5d %s\n", $1, $2, $3, $4, $5
        t+=$1; tw+=$2; tf+=$3; tk+=$4 }
      END {
        printf "\n合計 %d 輪：銷帳 %d｜無finding %d｜白跑 %d（%.1f%%）\n", t, tk, tf, tw, (t?tw*100/t:0)
        print  "🔴 白跑＝collection-failed（該輪產出無法收斂）。"
        print  "🔴 「無finding」之標籤真偽未經機械驗證前不可當成「該輪確實沒東西可報」——跑 --nofind-audit。"
      }'
}

# 單一工作項目：供 committee_run 在開輪前顯示，使「要不要再花一輪」有數字可依
_rc_item() {
  _rc_tally | LC_ALL=C awk -F'\t' -v want="$1" '
      $5 == want { printf "[round_cost] 工作項目「%s」累計 %d 輪：銷帳 %d｜無finding %d｜白跑 %d\n", $5, $1, $4, $3, $2; found=1 }
      END { if (!found) printf "[round_cost] 工作項目「%s」尚無歷史輪次（本輪為第 1 輪）\n", want }'
}

# 抽驗「預期零 findings」標籤：產出檔含**非 sentinel** 的 canonical finding ⇒ 標籤不實
_rc_nofind_audit() {
  local outs; outs="$(_rc_rows | LC_ALL=C awk -F'\t' '
      $2=="committee_round_open" { o[$1]=$5; next }
      $2=="debt_abandon" && $4=="no-findings-expected" { m[$1]=1 }
      END { for (r in m) if (r in o && o[r] != "") print o[r] }')"
  local tot=0 bad=0 ok=0 miss=0 line p seen found
  while IFS= read -r line; do
    [ -n "${line}" ] || continue
    tot=$((tot+1)); seen=0; found=0
    IFS=',' read -ra _paths <<< "${line}"
    for p in "${_paths[@]}"; do
      [ -f "${p}" ] || continue
      seen=1
      if LC_ALL=C grep -oE "${_RC_FINDING_RE}" "${p}" 2>/dev/null \
         | LC_ALL=C grep -qvE "${_RC_SENTINEL_RE}"; then found=1; fi
    done
    if   [ "${seen}"  -eq 0 ]; then miss=$((miss+1))
    elif [ "${found}" -eq 1 ]; then bad=$((bad+1)); echo "  🔴 標籤不實: ${line}" >&2
    else ok=$((ok+1)); fi
  done <<EOF
${outs}
EOF
  printf '標為「預期零 findings」：%d｜屬實 %d｜🔴 不實 %d｜產出檔查不到 %d\n' "${tot}" "${ok}" "${bad}" "${miss}"
  echo "🔴 不實＝該輪委員確實提了 findings 卻以「預期零 findings」結案 ⇒ 那些 findings 無紀錄可證被處置。"
  echo "   此即票 B-48 之病；產出端之機械綁定見 scripts/debt_clear.sh 的同名檢查。"
}

case "${1:-}" in
  --item)          [ $# -ge 2 ] || { echo "用法: --item <工作項目名>" >&2; exit 2; }; _rc_item "$2" ;;
  --nofind-audit)  _rc_nofind_audit ;;
  ""|--summary)    _rc_summary ;;
  *) echo "用法: bash scripts/round_cost.sh [--summary|--item <名>|--nofind-audit]" >&2; exit 2 ;;
esac
