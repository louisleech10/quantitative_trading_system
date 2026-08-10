#!/usr/bin/env bash
# friction_tally.sh — 票 B-37 站 2.6：摩擦統計（唯讀最小版）
#
# 底本：docs/GOVB37_FRICTION_TALLY_SPEC.md（r3 定案，經 r1–r4 四輪雙家族對抗審）
#
# 🔴 唯讀：只讀 audit.log，**沒有任何寫入該檔之路徑**。不改任何判定邏輯、不掛任何既有閘。
#
# 用法：
#   bash scripts/friction_tally.sh <模式> [--log PATH]
#   模式（六選一，不得同時給兩個）：
#     --by-event        事件名 × 次數
#     --by-reason       僅 gate_deny：reason × match_rule × 次數
#     --by-day          日期 × 事件名 × 次數
#     --by-node         tool × kind × 次數
#     --by-signature    cmd_sha256 × cmd_head × 次數
#     --field-presence  event × 欄位名 × present/absent × 次數
#   輸出：TSV、LC_ALL=C sort、無時間戳、無絕對路徑；末兩列為 `#total` 與 `#unparsed`。
#
# 🔴 對帳恆等式（防漏算之機械 oracle）：`#total == 各分類次數和 ＋ #unparsed`。
#    `--field-presence` 之對帳為**逐事件**：present + absent == by-event(該事件)。
#
# 🔴 解析契約＝ SPEC Task 1.1 契約 2 之參考實作，**照抄不改寫**：
#    引號是否結束字串 ＝ 其前方連續反斜線數為**偶數**。
#    r2/r3 連續兩輪之 BLOCKING 皆源於「散文沒定義到某邊界」⇒ 契約以實作＋差分 fixture 表達。
#    9 類 fixture 見 SPEC；codex 已對本實作實跑 parity 2/4/6 得 0/1/0，
#    並確認字面 \n、非 UTF-8、1,000,016 byte 長行、BOM 皆正確。
#
# 🔴 不得整檔 jq：實測 audit.log 中 86.8% 的行非 JSON（含 `=== dispatch ===` 舊區塊）。
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

_ft_usage() {
  sed -n '8,20p' "${BASH_SOURCE[0]}" >&2
}

_ft_die() { printf '%s\n' "$*" >&2; exit 2; }

MODE=""
LOG="${REPO_ROOT}/.claude/gate/audit.log"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --by-event|--by-reason|--by-day|--by-node|--by-signature|--field-presence)
      # 同時給兩個模式 ⇒ fail（不得靜默取第一個）
      [ -z "${MODE}" ] || _ft_die "ERROR: 只接受一個模式（已有 ${MODE}，又收到 $1）"
      MODE="$1"; shift ;;
    --log)
      [ "$#" -ge 2 ] || _ft_die "ERROR: --log 缺值"
      LOG="$2"; shift 2 ;;
    -h|--help) _ft_usage; exit 0 ;;
    *) echo "ERROR: 未知參數 '$1'" >&2; _ft_usage; exit 2 ;;
  esac
done

[ -n "${MODE}" ] || { echo "ERROR: 未指定模式" >&2; _ft_usage; exit 2; }
[ -r "${LOG}" ] || _ft_die "ERROR: log 不存在或不可讀：${LOG}"

LC_ALL=C awk -v mode="${MODE}" '
  # ---- SPEC Task 1.1 契約 2：quote-aware 逐行 JSON 判準（照抄，勿改寫）----
  function json_line_ok(s,   i, j, c, n, inq, depth, objs, bs) {
    n = length(s); inq = 0; depth = 0; objs = 0
    for (i = 1; i <= n; i++) {
      c = substr(s, i, 1)
      if (inq) {
        if (c == "\"") {
          bs = 0; j = i - 1
          while (j >= 1 && substr(s, j, 1) == "\\") { bs++; j-- }
          if (bs % 2 == 0) inq = 0
        }
        continue
      }
      if (c == "\"") { inq = 1; continue }
      if (c == "{") { depth++; if (depth == 1) objs++ }
      else if (c == "}") { depth--; if (depth < 0) return 0 }
    }
    return (inq == 0 && depth == 0 && objs == 1)
  }

  # 讀一個 JSON 字串常量（s 之第 st 字元須為 `"`）；回傳結束引號位置，值置於 STRVAL
  function read_str(s, st,   i, n, c, bs, j, out) {
    n = length(s); out = ""
    for (i = st + 1; i <= n; i++) {
      c = substr(s, i, 1)
      if (c == "\"") {
        bs = 0; j = i - 1
        while (j >= st + 1 && substr(s, j, 1) == "\\") { bs++; j-- }
        if (bs % 2 == 0) { STRVAL = out; return i }
      }
      out = out c
    }
    STRVAL = ""; return 0
  }

  # ---- 契約 3：root-only 鍵擷取（巢狀物件內之同名鍵不得計入）----
  function parse_root(s,   i, n, c, depth, inq, k, v, p, key) {
    for (key in F) delete F[key]
    n = length(s); depth = 0; i = 1
    while (i <= n) {
      c = substr(s, i, 1)
      if (c == "{") { depth++; i++; continue }
      if (c == "}") { depth--; i++; continue }
      if (c == "\"" && depth == 1) {
        p = read_str(s, i); if (p == 0) return
        k = STRVAL; i = p + 1
        while (i <= n && substr(s, i, 1) ~ /[ \t]/) i++
        if (substr(s, i, 1) != ":") continue
        i++
        while (i <= n && substr(s, i, 1) ~ /[ \t]/) i++
        c = substr(s, i, 1)
        if (c == "\"") { p = read_str(s, i); if (p == 0) return
                         F[k] = STRVAL; i = p + 1 }
        else if (c == "{" || c == "[") { F[k] = "<nested>" }   # 值為結構 ⇒ 不取字串值
        else { v = ""
               while (i <= n && substr(s, i, 1) !~ /[,}]/) { v = v substr(s, i, 1); i++ }
               gsub(/[ \t]+$/, "", v); F[k] = v }
        continue
      }
      if (c == "\"") { p = read_str(s, i); if (p == 0) return; i = p + 1; continue }
      i++
    }
  }

  function g(k) { return (k in F && F[k] != "") ? F[k] : "-" }

  { total++
    if (!json_line_ok($0)) { unparsed++; next }
    parse_root($0)
    ev = g("event")
    EVCNT[ev]++
    if (mode == "--by-event")      { C[ev]++ }
    else if (mode == "--by-reason") { if (ev == "gate_deny") C[g("reason") "\t" g("match_rule")]++ }
    else if (mode == "--by-day")    { d = g("ts"); if (d == "-" || length(d) < 10) d = "unknown"
                                      else d = substr(d, 1, 10)
                                      C[d "\t" ev]++ }
    else if (mode == "--by-node")   { C[g("tool") "\t" g("kind")]++ }
    else if (mode == "--by-signature") { C[g("cmd_sha256") "\t" g("cmd_head")]++ }
    else if (mode == "--field-presence") {
      # 🔴 key 必含 event（r4 CODEX-R4-P1-01）：全域與單一事件之答案不同，無 event 無法唯一對帳
      nf = split("reason,match_rule,cmd_sha256,cmd_head,tool,kind,ts", FL, ",")
      for (fi = 1; fi <= nf; fi++)
        C[ev "\t" FL[fi] "\t" ((FL[fi] in F && F[FL[fi]] != "") ? "present" : "absent")]++
    }
  }
  END {
    for (k in C) printf "%s\t%d\n", k, C[k]
    printf "#total\t%d\n", total + 0
    printf "#unparsed\t%d\n", unparsed + 0
  }
' "${LOG}" | LC_ALL=C sort
