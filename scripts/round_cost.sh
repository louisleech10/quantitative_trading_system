#!/usr/bin/env bash
# round_cost.sh — 委員輪成本量測：一件事花了幾輪、那些輪實際產出多少 findings。
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
#   bash scripts/round_cost.sh --nofind-audit  # 抽驗「預期零 findings」**自報標籤**之真偽
#   bash scripts/round_cost.sh --selftest      # 自檢：sentinel 排除與欄位對齊
#
# 🔴 2026-08-14 重大更正（使用者質疑「你能證明抓到的零 findings 是對的嗎」）：
#   舊版的「白跑／無finding」兩欄讀的是 `abandon_kind`——**主委銷帳時自己填的字串**，
#   不是量測。本檔自帶的 --nofind-audit 早已抓到該標籤 180 筆中 20 筆不實（11%）。
#   主委並曾據此推出「四成空轉」，拿去建議使用者砍掉整個委員流程
#   ⇒ **拿壞掉的尺量完再決定要不要拆房子。**
#   現版兩欄改為對**委員實際交件檔**機械計數，主委填什麼都影響不了。
#
# 🔴 誠實邊界：
#   ① 只涵蓋 JSON 期。稽核紀錄多數行為舊格式純文字，解析不到。
#   ② 歸戶到**工作項目**（session 主題），不是票號——一輪常同時處理多票，
#      票級歸屬已由票 B-48／B-37 判為現有資料上不可得。
#   ③ 🔴 **「空輪」不是浪費**：收斂輪／複驗輪／戳記輪本來就該零 findings，
#      那是**收斂成功**的訊號。把空輪當成空轉是錯誤推論（主委犯過）。
#   ④ 「無產出」只表示**現在**查不到那些檔，不推論當時發生什麼（舊檔可能已清理或改名）。
#   ⑤ findings 數只反映**數量**，不反映價值——一個 P0 與一個 P3 各算一個。
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

# 🔴 逐輪**實數**該輪委員交件檔裡的 canonical finding（2026-08-14 改，使用者質疑後）。
#
# 病根（使用者原話：「你能證明量測工具抓到的零 finding 是對的嗎」）：
#   舊版判「有沒有 findings」是讀 `abandon_kind`——那是**主委銷帳時自己填的字串**，
#   不是量測。而本檔自帶的 --nofind-audit 早已抓到該標籤 180 筆中 20 筆不實（11%）。
#   ⇒ 舊版兩欄（白跑／無finding）是自報，主委並曾據此推出「四成空轉」
#     並拿去建議使用者砍掉整個委員流程。**拿壞掉的尺量完再決定要不要拆房子。**
#
# 現法：`committee_round_open` 事件已帶該輪的 expected_outputs（委員交件檔路徑）
#   ⇒ 直接對那些檔數 `## <FAMILY>-R<n>-P<0-3>-<NN>` 標題行，扣掉零-findings sentinel。
#   主委填什麼都影響不了結果。
#
# 三態（封閉，皆機械可判）：
#   has     產出檔存在且有 ≥1 個非 sentinel 的 finding
#   empty   產出檔存在但零個真 finding（含只有 sentinel 者）—— **這是收斂成功，不是浪費**
#   missing 產出檔查不到 —— 該輪在磁碟上沒有留下可查的產物
#
# 🔴 誠實邊界：`missing` **不等於**「白跑」。舊檔可能已被清理或改名；
#   本欄只誠實說「現在查不到」，不推論當時發生什麼。
_rc_findings_by_round() {   # $1=rows 檔 → stdout: round_id \t 真findings數 \t 三態
  # 🔴 **不可**寫 `IFS=$'\t' read -r rid ev sess ak outs`：tab 屬 whitespace 類 IFS，
  #   連續 tab 會被併成單一分隔符。開輪事件的 abandon_kind 恆為空 ⇒ 欄位整排左移、
  #   路徑落到 ak 而 outs 變空 ⇒ 每一輪都被判成「無產出」。
  #   **它不報錯，只安靜地回報「全部查不到」**——2026-08-14 實際踩到（449/449 全 missing）。
  #   改由 awk 先濾出兩欄（awk -F'\t' 對空欄位是正確的），且 round_id 恆非空。
  local rid outs p n total seen _two
  _two="$(mktemp "${TMPDIR:-/tmp}/rctwo.XXXXXXXX")" || return 2
  LC_ALL=C awk -F'\t' '$2=="committee_round_open" { print $1 "\t" $5 }' "$1" > "${_two}"
  while IFS= read -r line; do
    rid="${line%%$'\t'*}"
    outs="${line#*$'\t'}"
    [ "${outs}" = "${line}" ] && outs=""      # 該行沒有 tab ⇒ 無路徑
    total=0; seen=0
    if [ -n "${outs}" ]; then
      IFS=',' read -ra _rc_paths <<< "${outs}"
      for p in "${_rc_paths[@]}"; do
        [ -f "${p}" ] || continue
        seen=1
        # 先抽出全部 canonical 標題，再剔除 sentinel，剩下的才是真 finding
        n="$(LC_ALL=C grep -oE "${_RC_FINDING_RE}" "${p}" 2>/dev/null \
             | LC_ALL=C grep -cvE "${_RC_SENTINEL_RE}")"
        total=$((total + ${n:-0}))
      done
    fi
    if   [ "${seen}"  -eq 0 ]; then printf '%s\t0\tmissing\n' "${rid}"
    elif [ "${total}" -gt 0 ]; then printf '%s\t%d\thas\n' "${rid}" "${total}"
    else                            printf '%s\t0\tempty\n' "${rid}"
    fi
  done < "${_two}"
  rm -f "${_two}"
}

_rc_tally() {   # stdout: 輪數 \t findings數 \t 空輪 \t 無產出 \t 銷帳 \t 工作項目
  local _r _f
  _r="$(mktemp "${TMPDIR:-/tmp}/rcrows.XXXXXXXX")" || return 2
  _f="$(mktemp "${TMPDIR:-/tmp}/rcfind.XXXXXXXX")" || { rm -f "${_r}"; return 2; }
  # 🔴 rc 直接取，不經 pipe（CLAUDE.md 明載；本 epic 已犯三次）
  _rc_rows > "${_r}"
  local _rc=$?
  if [ "${_rc}" -ne 0 ] || [ ! -s "${_r}" ]; then
    echo "round_cost: 稽核事件抽取失敗或為空（rc=${_rc}）→ 拒絕輸出可能誤導的統計" >&2
    rm -f "${_r}" "${_f}"; return 2
  fi
  _rc_findings_by_round "${_r}" > "${_f}"
  LC_ALL=C awk -F'\t' "${_rc_topic_awk}"'
      FNR==NR { fc[$1]=$2; st[$1]=$3; next }
      $2=="committee_round_open" { ss[$1]=topic($3); next }
      $2=="committee_debt_clear" { ok[$1]=1; next }
      END {
        for (r in ss) {
          s=ss[r]; n[s]++
          g[s] += fc[r]+0
          if (st[r]=="empty")   e[s]++
          if (st[r]=="missing") m[s]++
          if (r in ok)          k[s]++
        }
        for (s in n) printf "%d\t%d\t%d\t%d\t%d\t%s\n", n[s], g[s]+0, e[s]+0, m[s]+0, k[s]+0, s
      }' "${_f}" "${_r}" | LC_ALL=C sort -rn
  rm -f "${_r}" "${_f}"
}

_rc_summary() {
  _rc_tally | LC_ALL=C awk -F'\t' '
      BEGIN { printf "%-5s %-9s %-5s %-7s %-5s %s\n", "總輪", "findings", "空輪", "無產出", "銷帳", "工作項目" }
      { printf "%-5d %-9d %-5d %-7d %-5d %s\n", $1, $2, $3, $4, $5, $6
        t+=$1; tg+=$2; te+=$3; tm+=$4; tk+=$5 }
      END {
        printf "\n合計 %d 輪：真 findings %d 個｜空輪 %d｜無產出 %d｜銷帳 %d\n", t, tg, te, tm, tk
        print  "🔴 上列全部由**委員實際交件檔**機械數出（扣掉零-findings sentinel），不讀任何自報標籤。"
        print  "🔴 「空輪」不等於浪費——收斂輪／複驗輪／戳記輪本來就該零 findings，那是收斂成功的訊號。"
        print  "🔴 「無產出」只表示現在查不到那些檔，不推論當時發生什麼（舊檔可能已清理或改名）。"
        print  "   想知道自報標籤有多不可信：bash scripts/round_cost.sh --nofind-audit"
      }'
}

# 單一工作項目：供 committee_run 在開輪前顯示，使「要不要再花一輪」有數字可依
_rc_item() {
  _rc_tally | LC_ALL=C awk -F'\t' -v want="$1" '
      $6 == want { printf "[round_cost] 工作項目「%s」累計 %d 輪：真 findings %d 個｜空輪 %d｜無產出 %d｜銷帳 %d\n", $6, $1, $2, $3, $4, $5; found=1 }
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

# 🔴 自檢：把 2026-08-14 實際踩到的兩個坑釘死。兩者**都不會報錯**，只會安靜給出
#   看起來合理的錯誤數字——這正是本檔被使用者質疑「你能證明零 findings 是對的嗎」的根源。
#   ① sentinel 未排除 ⇒ 「沒問題」被算成「有問題」
#   ② 欄位位移（IFS=tab 併吞空欄）⇒ 每一輪都被判成「無產出」（實際發生過 449/449）
_rc_selftest() {
  local d rc=0
  d="$(mktemp -d "${TMPDIR:-/tmp}/rcself.XXXXXXXX")" || return 2
  mkdir -p "${d}/h"
  printf '## CODEX-R1-P1-01\n## CODEX-R1-P2-02\n' > "${d}/h/real.md"
  printf '## GROK-R2-P3-00\n'                      > "${d}/h/sentinel.md"
  # 第 4 欄（abandon_kind）**刻意留空**——這正是坑 ②
  {
    printf 'R-A\tcommittee_round_open\t20260101-demo-x-review-r1\t\t%s\n' "${d}/h/real.md"
    printf 'R-B\tcommittee_round_open\t20260101-demo-x-stamp-r2\t\t%s\n'  "${d}/h/sentinel.md"
    printf 'R-C\tcommittee_round_open\t20260101-demo-x-review-r3\t\t%s\n' "${d}/h/nope.md"
  } > "${d}/rows"

  local out; out="$(_rc_findings_by_round "${d}/rows")"
  _rc_expect() { printf '%s\n' "${out}" | LC_ALL=C grep -qx "$1" \
      || { echo "SELFTEST FAIL: 期望 '$1'，實得：" >&2; printf '%s\n' "${out}" | sed 's/^/    /' >&2; rc=1; }; }
  _rc_expect "$(printf 'R-A\t2\thas')"        # 兩個真 finding
  _rc_expect "$(printf 'R-B\t0\tempty')"      # 只有 sentinel ⇒ 0，且不是 missing
  _rc_expect "$(printf 'R-C\t0\tmissing')"    # 檔不存在
  rm -rf "${d}"
  if [ "${rc}" -eq 0 ]; then
    echo "SELFTEST PASS: sentinel 已排除、空欄位不造成欄位位移、三態判定正確"
  fi
  return "${rc}"
}

case "${1:-}" in
  --selftest)      _rc_selftest ;;
  --item)          [ $# -ge 2 ] || { echo "用法: --item <工作項目名>" >&2; exit 2; }; _rc_item "$2" ;;
  --nofind-audit)  _rc_nofind_audit ;;
  ""|--summary)    _rc_summary ;;
  *) echo "用法: bash scripts/round_cost.sh [--summary|--item <名>|--nofind-audit|--selftest]" >&2; exit 2 ;;
esac
