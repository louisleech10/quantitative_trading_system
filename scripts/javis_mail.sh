#!/usr/bin/env bash
# Javis 信箱（Louis 之個人助理 Javis ↔ Claude 之非同步管道）——雙方**唯一**建檔入口。
#
# 用法：
#   bash scripts/javis_mail.sh new   <from> <topic>  [--needs-louis yes|no]  建新信，印出路徑
#   bash scripts/javis_mail.sh reply <from> <原信id> [--needs-louis yes|no]  建回信（自動帶 in-reply-to），印出路徑
#   bash scripts/javis_mail.sh ack   <from> <原信id>                          已讀無需再回：建一封已 closed 之回信
#   bash scripts/javis_mail.sh list  [--unanswered] [--for cc|javis]         列 open 之信（--unanswered：且無對應回信）
#   bash scripts/javis_mail.sh close <caller> <id>                            原寄件者關閉自己的信
#   bash scripts/javis_mail.sh notify                                         UserPromptSubmit 用：有寄給 cc 之未回覆信才印一行
#   bash scripts/javis_mail.sh pending                                        SessionStart 用：列寄給 cc 之未回覆信
#   bash scripts/javis_mail.sh watch [--interval 秒] [--max-min 分]           信箱 session 背景守候：有信即印出並結束
#   bash scripts/javis_mail.sh unwatch                                        解除守候標記（其他 session 立即恢復提示）
#
# 守候語意：watch 每輪更新 handoffs/javis/.watcher；該檔 15 分鐘內有更新 ⇒ notify／pending 不輸出，
#   由守候中之信箱 session 處理，不打斷其他工作 session。守候中斷 >15 分鐘 ⇒ 自動恢復提示，信不會漏。
#
# 規則見 CLAUDE.md「Javis 信箱」節：每封信只由寄件者寫；建檔後寄件者填一次內文，之後唯一可改＝status→closed。
# 「已回覆」不記欄位，由對向資料夾之 in-reply-to 導出。信箱不進 git（.git/info/exclude 之 handoffs/*）。
# 誠實邊界：close 之 <caller> 為自報身分，只擋誤操作，不防冒稱。
set -u
shopt -s nullglob
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

BOX="handoffs/javis"
TO_CC="${BOX}/to_cc"
TO_JAVIS="${BOX}/to_javis"
ID_RE='^[0-9]{8}-[0-9]{4}-(javis|cc)-[a-z0-9]+(-[a-z0-9]+)*$'
WATCH_MARK="${BOX}/.watcher"
WATCH_FRESH_MIN=15

# 守候中＝標記檔 WATCH_FRESH_MIN 分鐘內被更新過（find -mmin 跨 BSD／GNU，免 stat 平台差異）
_watching() { [ -f "${WATCH_MARK}" ] && [ -n "$(find "${WATCH_MARK}" -mmin -"${WATCH_FRESH_MIN}" 2>/dev/null)" ]; }

die() { echo "[javis_mail] $*" >&2; exit 2; }

_usage() { sed -n '4,13p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }

# 寄件者 → 其寄件夾（javis 寄給 cc ⇒ to_cc；cc 寄給 javis ⇒ to_javis）
_outbox() { case "$1" in javis) echo "${TO_CC}" ;; cc) echo "${TO_JAVIS}" ;; *) return 1 ;; esac; }
_other()  { case "$1" in "${TO_CC}") echo "${TO_JAVIS}" ;; *) echo "${TO_CC}" ;; esac; }

# 每檔一行：path<TAB>from<TAB>status<TAB>needs-louis<TAB>in-reply-to（只讀第一段 --- 檔頭）
_heads() {
  [ "$#" -gt 0 ] || return 0
  LC_ALL=C awk '
    function out() { if (fn != "") printf "%s\t%s\t%s\t%s\t%s\n", fn, fr, st, nl, irt }
    FNR == 1 { out(); fn = FILENAME; fr = st = nl = irt = ""; inh = ($0 == "---"); next }
    inh && $0 == "---"     { inh = 0; next }
    inh && /^from:/        { fr = $2 }
    inh && /^status:/      { st = $2 }
    inh && /^needs-louis:/ { nl = $2 }
    inh && /^in-reply-to:/ { irt = $2 }
    END { out() }
  ' "$@"
}

_create() {  # $1=from $2=topic $3=in-reply-to $4=needs-louis [$5=status 預設 open] [$6=結論內文]
  local from="$1" topic="$2" irt="$3" nl="$4" st="${5:-open}" body="${6:-}" dir stamp iso id path
  dir="$(_outbox "${from}")" || die "from 只能是 javis 或 cc：${from}"
  printf '%s' "${topic}" | LC_ALL=C grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$' \
    || die "topic 須為小寫英數字加連字號（如 test-ping）：${topic}"
  case "${nl}" in yes|no) ;; *) die "--needs-louis 只能是 yes 或 no：${nl}" ;; esac
  read -r stamp iso <<<"$(TZ=Asia/Taipei date '+%Y%m%d-%H%M %Y-%m-%dT%H:%M:%S')"
  id="${stamp}-${from}-${topic}"
  path="${dir}/${id}.md"
  mkdir -p "${TO_CC}" "${TO_JAVIS}" || die "建立信箱資料夾失敗"
  # noclobber：同名已存在即失敗，不覆蓋（同一分鐘同主題）
  ( set -C; printf -- '---\nid: %s\nfrom: %s\ndate: %s+08:00\nin-reply-to:%s\nstatus: %s\nneeds-louis: %s\n---\n\n## 問題或結論\n%s\n## 需要對方做什麼\n\n## 證據\n' \
      "${id}" "${from}" "${iso}" "${irt:+ ${irt}}" "${st}" "${nl}" "${body:+${body}
}" > "${path}" ) 2>/dev/null \
    || die "同名信已存在或無法寫入：${path}（同一分鐘同主題請稍候或換 topic）"
  printf '%s\n' "${path}"
}

_parse_nl() {  # 從剩餘參數取 --needs-louis，預設 no
  NL="no"
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --needs-louis) [ "$#" -ge 2 ] || die "--needs-louis 缺值"; NL="$2"; shift 2 ;;
      *) die "不認得的參數：$1" ;;
    esac
  done
}

cmd_new() {
  [ "$#" -ge 2 ] || _usage
  local from="$1" topic="$2"; shift 2
  _parse_nl "$@"
  _create "${from}" "${topic}" "" "${NL}"
}

cmd_reply() {
  [ "$#" -ge 2 ] || _usage
  local from="$1" orig="$2" odir; shift 2
  _parse_nl "$@"
  _outbox "${from}" >/dev/null || die "from 只能是 javis 或 cc：${from}"
  printf '%s' "${orig}" | LC_ALL=C grep -Eq "${ID_RE}" || die "原信 id 格式不符：${orig}"
  odir="$(_other "$(_outbox "${from}")")"   # 回信只回對方寄來的信 ⇒ 原信在對向資料夾
  [ -f "${odir}/${orig}.md" ] || die "找不到原信：${odir}/${orig}.md（只能回覆對方寄來的信）"
  _create "${from}" "${orig#*-*-*-}" "${orig}" "${NL}" "${ACK_STATUS:-open}" "${ACK_BODY:-}"
}

# 已讀、無需再回：建一封已 closed 之回信 ⇒ 原信不再算未回覆，對方也不會被提示（關閉迴圈，免 ack 互回）
cmd_ack() {
  [ "$#" -eq 2 ] || _usage
  ACK_STATUS=closed ACK_BODY="已讀，無需回覆。" cmd_reply "$1" "$2"
}

# $1=unanswered(0|1) $2=for(cc|javis|空)
_list() {
  local unans="$1" for="$2" d other replied
  local dirs=()
  case "${for}" in
    cc) dirs=("${TO_CC}") ;;
    javis) dirs=("${TO_JAVIS}") ;;
    "") dirs=("${TO_CC}" "${TO_JAVIS}") ;;
    *) die "--for 只能是 cc 或 javis：${for}" ;;
  esac
  for d in "${dirs[@]}"; do
    [ -d "${d}" ] || continue
    other="$(_other "${d}")"
    # 對向回信（R 列）與本資料夾信件（M 列）同一條管線餵進 awk。
    # 🔴 不得以 awk -v 傳多行值：BSD awk 拒收含換行之 -v（"newline in string"），
    #   初版即因此在回信 ≥2 封時 rc=2（Javis 2026-10-09 回報）。
    { _heads "${other}"/*.md | sed 's/^/R	/'
      _heads "${d}"/*.md | sed 's/^/M	/'
    } | LC_ALL=C awk -F'\t' -v u="${unans}" '
      $1 == "R" { if (u == 1 && $6 != "") done[$6] = 1; next }
      $1 == "M" && $4 == "open" {
        id = $2; sub(/^.*\//, "", id); sub(/\.md$/, "", id)
        if (id in done) next
        printf "%s\tneeds-louis=%s\n", $2, $5
      }' || return 2
  done
}

cmd_list() {
  local unans=0 for=""
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --unanswered) unans=1; shift ;;
      --for) [ "$#" -ge 2 ] || die "--for 缺值"; for="$2"; shift 2 ;;
      *) die "不認得的參數：$1" ;;
    esac
  done
  _list "${unans}" "${for}"
}

cmd_close() {
  [ "$#" -eq 2 ] || _usage
  local caller="$1" id="$2" dir f fr st tmp
  dir="$(_outbox "${caller}")" || die "caller 只能是 javis 或 cc：${caller}"
  printf '%s' "${id}" | LC_ALL=C grep -Eq "${ID_RE}" || die "id 格式不符：${id}"
  f="${dir}/${id}.md"
  [ -f "${f}" ] || die "找不到 ${caller} 寄出之信：${f}（只能關閉自己寄的信）"
  IFS=$'\t' read -r _ fr st _ _ <<<"$(_heads "${f}")"
  [ "${fr}" = "${caller}" ] || die "此信 from=${fr}，非 ${caller}，不得關閉"
  case "${st}" in
    closed) echo "已是 closed：${f}"; return 0 ;;
    open) ;;
    *) die "status 非 open／closed（${st}）：${f}" ;;
  esac
  tmp="$(mktemp "${f}.XXXXXX")" || die "mktemp 失敗"
  LC_ALL=C awk '
    NR == 1 && $0 == "---" { inh = 1; print; next }
    inh && $0 == "---"     { inh = 0 }
    inh && !done && $0 == "status: open" { print "status: closed"; done = 1; next }
    { print }' "${f}" > "${tmp}" && mv "${tmp}" "${f}" || { rm -f "${tmp}"; die "改寫失敗：${f}"; }
  echo "已關閉：${f}"
}

# hook 用：永遠 rc=0、無信時零輸出
cmd_pending() {
  _watching && return 0
  _list 1 cc
}

cmd_watch() {
  local interval=60 maxmin=110 start out
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --interval) [ "$#" -ge 2 ] || die "--interval 缺值"; interval="$2"; shift 2 ;;
      --max-min) [ "$#" -ge 2 ] || die "--max-min 缺值"; maxmin="$2"; shift 2 ;;
      *) die "不認得的參數：$1" ;;
    esac
  done
  printf '%s%s' "${interval}" "${maxmin}" | LC_ALL=C grep -Eq '^[0-9]+$' || die "--interval／--max-min 須為非負整數"
  [ "${interval}" -ge 1 ] || die "--interval 須 ≥1"
  mkdir -p "${TO_CC}" "${TO_JAVIS}" || die "建立信箱資料夾失敗"
  start="$(date +%s)"
  while :; do
    touch "${WATCH_MARK}"
    out="$(_list 1 cc 2>&1)" || { echo "⚠️ Javis 信箱守候：讀信失敗，守候結束：${out}"; exit 1; }
    if [ -n "${out}" ]; then
      echo "📬 Javis 信箱：有寄給 Claude 之未回覆信"; printf '%s\n' "${out}"; exit 0
    fi
    if [ $(( $(date +%s) - start )) -ge $(( maxmin * 60 )) ]; then
      echo "⏱ Javis 信箱守候：${maxmin} 分鐘無新信，到期結束（請重啟守候）"; exit 0
    fi
    sleep "${interval}"
  done
}

cmd_unwatch() {
  [ -f "${WATCH_MARK}" ] && rm -f "${WATCH_MARK}"
  echo "已解除守候標記：其他 session 恢復信件提示"
}

cmd_notify() {
  local n out
  _watching && exit 0   # 信箱 session 守候中 ⇒ 不打斷其他 session
  # 列信失敗不得靜默成「沒信」：改印一行警告（仍 rc=0，不擋使用者送出）
  out="$(_list 1 cc 2>&1)" || { echo "⚠️ Javis 信箱：讀信失敗（bash scripts/javis_mail.sh list --unanswered --for cc 查原因）"; exit 0; }
  n="$(printf '%s' "${out}" | LC_ALL=C grep -c .)"
  [ "${n:-0}" -gt 0 ] 2>/dev/null \
    && echo "📬 Javis 信箱：${n} 封寄給 Claude 的信未回覆（bash scripts/javis_mail.sh list --unanswered --for cc；規則見 CLAUDE.md「Javis 信箱」節）"
  exit 0
}

[ "$#" -ge 1 ] || _usage
sub="$1"; shift
case "${sub}" in
  new) cmd_new "$@" ;;
  reply) cmd_reply "$@" ;;
  ack) cmd_ack "$@" ;;
  list) cmd_list "$@" ;;
  close) cmd_close "$@" ;;
  notify) cmd_notify ;;
  pending) cmd_pending ;;
  watch) cmd_watch "$@" ;;
  unwatch) cmd_unwatch ;;
  *) _usage ;;
esac
