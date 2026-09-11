#!/usr/bin/env bash
# ticket_batch_check.sh — VERDICTGATE Phase 3（Task 3.2／3.3）：任何含生產碼之 commit 皆須宣告批次並持有效 token；
#   小任務走 `small`；small 不得連鎖拆分。**唯一實作**，三個呼叫點只做薄包裝：
#     commit-msg hook  → --msg <msgfile>        （staged 生產檔 ⇒ 訊息最末段須有 Ticket-Batch trailer；rc=2 拒 commit）
#     post-commit hook → --emit-event <sha>     （對含 trailer 之 commit 寫 audit ticket_commit{sha,trailer,root,batch,prod_files,token_fresh}）
#     gov_check 1c     → --push-range <range> --local-sha <sha>[,<sha>…]
#                        （range 內每個生產 commit 驗 trailer＋token_fresh=true；small 持續視窗聯集 >3 或含三檔名 ⇒ 拒）
#
# 規則（SPEC v9 Task 3.2／3.3；C-2 不動 G-7、C-7 逃生口留痕、C-8 事件 schema）：
#   生產路徑＝^(momentum|api|frontend/src)/ ；三檔名＝factories.py|protocols.py|config.py
#   `<root>/b<N>` ⇒ .claude/gate/impl.<root>-b<N>.token 存在且 mtime 在 900s 內（commit 當下；post-commit 記 token_fresh）
#   `small`      ⇒ staged 生產檔 ≤3 且不含三檔名
#   small 視窗：自最近一筆**被消費的** impl_token_issued（其後有同 <root>/b<N> 之 ticket_commit.token_fresh=true 且
#              prod_files∩生產路徑≠∅）起，全部 trailer=small 之 ticket_commit（先過濾對 local sha 不可達之幽靈 sha），
#              prod_files 聯集 >3 或含三檔名 ⇒ 拒；push 成功不清零；全 repo 全域。無錨 ⇒ 自首筆 small 起算。
#   §N E-2（使用者 2026-09-11 裁定）：本規則凍結於此語意，不再加重置條件。
set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GATE_DIR="${GATE_DIR_OVERRIDE:-${REPO_ROOT}/.claude/gate}"
AUDIT="${GATE_DIR}/audit.log"
if [ -n "${DEBT_AUDIT_OVERRIDE:-}" ]; then
  [ "${GOVERNANCE_TEST_HARNESS:-}" = "1" ] || { echo "ERROR: DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1" >&2; exit 2; }
  AUDIT="${DEBT_AUDIT_OVERRIDE}"
fi
PROD_RE='^(momentum|api|frontend/src)/'
SPECIAL_RE='(^|/)(factories\.py|protocols\.py|config\.py)$'
# B3 R1 CODEX-R1-P2-03：`<root>/b<N>` 以錨定 regex 驗（shell glob `*/b[0-9]*` 會收 `ROOT/b2oops`）
BATCH_RE='^[A-Za-z0-9._-]+/b[1-9][0-9]*$'
# B3 R1 CODEX-R1-P1-01：生產檔判定含刪除（D）——刪 production code 也是 production change
DIFF_FILTER='ACDMR'
TOKEN_TTL=900
ZERO40='0000000000000000000000000000000000000000'

_mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1"; }
_batch_ok() { printf '%s' "$1" | grep -Eq "${BATCH_RE}"; }
_token_fresh() {   # $1=root $2=batch → true|false
  local t="${GATE_DIR}/impl.$1-b$2.token"
  [ -f "$t" ] || { echo false; return; }
  local now m; now="$(date +%s)"; m="$(_mtime "$t")"
  [ $(( now - m )) -le "${TOKEN_TTL}" ] && echo true || echo false
}
_parse_trailer() {   # stdin=訊息 → stdout=Ticket-Batch 值（空＝無）
  git interpret-trailers --parse 2>/dev/null | awk -F': *' 'tolower($1)=="ticket-batch"{v=$2} END{print v}'
}
_prod_of() { grep -E "${PROD_RE}" || true; }

case "${1:-}" in
  --msg)
    f="${2:-}"; [ -f "$f" ] || { echo "用法: --msg <msgfile>" >&2; exit 2; }
    [ -f "$(git rev-parse --git-dir 2>/dev/null)/MERGE_HEAD" ] && exit 0      # merge commit 豁免（邊界②）
    prod="$(git diff --cached --name-only --diff-filter="${DIFF_FILTER}" 2>/dev/null | _prod_of)"
    [ -n "${prod}" ] || exit 0                                                   # docs-only ⇒ 不管
    trailer="$(_parse_trailer < "$f")"
    n="$(printf '%s\n' "${prod}" | grep -c .)"
    if [ -z "${trailer}" ]; then
      echo "commit-msg: 🔴 staged 含生產碼（${n} 檔）但訊息最末段無 Ticket-Batch trailer" >&2
      echo "  加 'Ticket-Batch: <root>/b<N>'（須先 bash scripts/gate.sh dispatch --impl-self 領 token）或 'Ticket-Batch: small'（≤3 生產檔且不含 factories/protocols/config）" >&2
      exit 2
    fi
    if [ "${trailer}" = "small" ]; then
      [ "${n}" -le 3 ] || { echo "commit-msg: 🔴 Ticket-Batch: small 但 staged 生產檔 ${n} > 3 ⇒ 改領 --impl-self" >&2; exit 2; }
      printf '%s\n' "${prod}" | grep -qE "${SPECIAL_RE}" && { echo "commit-msg: 🔴 small 不得碰 factories.py|protocols.py|config.py（膨脹訊號）⇒ 改領 --impl-self" >&2; exit 2; }
      exit 0
    fi
    _batch_ok "${trailer}" || { echo "commit-msg: 🔴 Ticket-Batch 值不合法: '${trailer}'（只准 <root>/b<N>（N 為正整數）或 small）" >&2; exit 2; }
    root="${trailer%/b*}"; batch="${trailer##*/b}"
    [ "$(_token_fresh "${root}" "${batch}")" = "true" ] || { echo "commit-msg: 🔴 Ticket-Batch: ${trailer} 但 token 不存在或已過期（900s）⇒ bash scripts/gate.sh dispatch --impl-self --task-id ${root}-impl-b${batch}-claude 重領" >&2; exit 2; }
    exit 0 ;;

  --emit-event)
    sha="${2:-HEAD}"; sha="$(git rev-parse "${sha}" 2>/dev/null)" || exit 0
    trailer="$(git log -1 --format='%B' "${sha}" | _parse_trailer)"
    [ -n "${trailer}" ] || exit 0
    prod_json="$(git show --name-only --format= --diff-filter="${DIFF_FILTER}" "${sha}" | _prod_of | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')"
    if [ "${trailer}" = "small" ]; then root="small"; batch="0"; fresh="null"
    elif _batch_ok "${trailer}"; then root="${trailer%/b*}"; batch="${trailer##*/b}"; fresh="$(_token_fresh "${root}" "${batch}")"
    else
      # 不合法 trailer（只可能來自 --no-verify）⇒ 不寫事件；push 時 1c 以「trailer 不合法」擋（fail-closed）
      echo "post-commit: ⚠ Ticket-Batch 值不合法 '${trailer}'，不寫 ticket_commit（push 時 1c 會擋）" >&2; exit 0
    fi
    bash "${SCRIPT_DIR}/audit_append.sh" --event ticket_commit --field "sha=${sha}" --field "trailer=${trailer}" \
      --field "root=${root}" --field "batch=${batch}" --field "prod_files=@${prod_json}" --field "token_fresh=${fresh}" \
      --field "actor=post-commit" --field "origin_script=git_hooks/post-commit" \
      || { echo "post-commit: ERROR 寫 audit ticket_commit 失敗（commit 已成立；push 時 1c 會以「有 trailer 無事件」擋）" >&2; exit 0; }
    exit 0 ;;

  --push-range)
    range="${2:-}"; shift 2 2>/dev/null || true
    local_shas=""
    while [ $# -gt 0 ]; do case "$1" in --local-sha) local_shas="${2:-}"; shift 2 ;; *) echo "未知參數 $1" >&2; exit 2 ;; esac; done
    [ -n "${range}" ] || { echo "用法: --push-range <range> --local-sha <sha>[,<sha>]" >&2; exit 2; }
    [ -n "${local_shas}" ] || local_shas="$(git rev-parse HEAD)"
    rc=0
    # B3 R1（主委自查 CLAUDE-R1-P1-01）：SPEC 字面 `--range 0000000..<sha>`（首次 push）之 rev-list rc=128 曾被 2>/dev/null
    #   吞掉 ⇒ 迴圈空 ⇒ rc=0 fail-open。全零前綴 ⇒ 正規化為 `<sha>`（全部可達）；其餘 rev-list 失敗 ⇒ fail-closed。
    case "${range}" in
      "${ZERO40}"..*|0000000..*) range="${range#*..}" ;;
    esac
    commits="$(git rev-list "${range}" 2>/dev/null)" || { echo "1c: 🔴 range '${range}' 無法解析（git rev-list 失敗）⇒ 待驗範圍不明，fail-closed" >&2; exit 1; }
    # ① range 內每個生產 commit：trailer 必在且合法；<root>/b<N> ⇒ 須有 ticket_commit.token_fresh=true；有 trailer 卻無事件 ⇒ 拒
    for c in ${commits}; do
      prod="$(git show --name-only --format= --diff-filter="${DIFF_FILTER}" "${c}" | _prod_of)"
      trailer="$(git log -1 --format='%B' "${c}" | _parse_trailer)"
      if [ -n "${prod}" ] && [ -z "${trailer}" ]; then
        echo "1c: 🔴 ${c:0:8} 含生產碼但無 Ticket-Batch trailer（--no-verify 繞過 commit-msg？）" >&2; rc=1; continue
      fi
      [ -n "${trailer}" ] || continue
      if [ "${trailer}" != "small" ] && ! _batch_ok "${trailer}"; then
        echo "1c: 🔴 ${c:0:8} Ticket-Batch 值不合法 '${trailer}'（只准 <root>/b<N> 或 small）" >&2; rc=1; continue
      fi
      ev="$(grep '"event": "ticket_commit"' "${AUDIT}" 2>/dev/null | grep "\"sha\": \"${c}\"" | tail -1)"
      if [ -z "${ev}" ]; then
        echo "1c: 🔴 ${c:0:8} 有 Ticket-Batch: ${trailer} 卻無 audit ticket_commit 事件（post-commit 未跑或寫入失敗）" >&2; rc=1; continue
      fi
      case "${trailer}" in
        small) : ;;
        *) printf '%s' "${ev}" | grep -q '"token_fresh": "true"' || { echo "1c: 🔴 ${c:0:8} Ticket-Batch: ${trailer} 於 commit 當下 token 無效（token_fresh≠true；事後領 token 不追認）" >&2; rc=1; } ;;
      esac
    done
    # ② small 持續視窗（讀 audit；錨＝被消費的 token；幽靈過濾）
    python3 - "${AUDIT}" "${local_shas}" <<'PY' || rc=1
import json, re, subprocess, sys
audit, local_shas = sys.argv[1], [s for s in sys.argv[2].split(",") if s]
PROD = re.compile(r"^(momentum|api|frontend/src)/"); SPECIAL = re.compile(r"(^|/)(factories\.py|protocols\.py|config\.py)$")
rows = []
try:
    for raw in open(audit, encoding="utf-8").read().splitlines():
        s = raw.strip()
        if s.startswith("{"):
            try: rows.append(json.loads(s))
            except json.JSONDecodeError: pass
except OSError:
    sys.exit(0)
def reachable(sha):
    return any(subprocess.run(["git", "merge-base", "--is-ancestor", sha, l], capture_output=True).returncode == 0 for l in local_shas)
# 錨：最近一筆 impl_token_issued，且其後有同 root/batch 之 ticket_commit token_fresh=true 且 prod_files 含生產路徑
anchor = -1
for i, r in enumerate(rows):
    if r.get("event") != "impl_token_issued":
        continue
    root, batch = r.get("root"), str(r.get("batch"))
    consumed = any(j > i and o.get("event") == "ticket_commit" and o.get("root") == root and str(o.get("batch")) == batch
                   and str(o.get("token_fresh")) == "true" and any(PROD.match(p) for p in (o.get("prod_files") or []))
                   for j, o in enumerate(rows))
    if consumed:
        anchor = i
union = set(); ghosts = 0
for i, r in enumerate(rows):
    if i <= anchor or r.get("event") != "ticket_commit" or r.get("trailer") != "small":
        continue
    if not reachable(r.get("sha") or ""):
        ghosts += 1; continue
    union |= {p for p in (r.get("prod_files") or []) if PROD.match(p)}
bad = sorted(p for p in union if SPECIAL.search(p))
if len(union) > 3 or bad:
    print(f"1c: 🔴 small 累計生產檔 {len(union)} 個（>3）或含 {bad}：{sorted(union)}；起算＝{'首筆 small' if anchor < 0 else 'seq '+str(rows[anchor].get('sequence'))}（被消費 token）。改領 --impl-self（幽靈 sha 已濾 {ghosts}）", file=sys.stderr)
    sys.exit(1)
print(f"1c: ✓ small 累計生產檔 {len(union)}/3（幽靈已濾 {ghosts}）")
PY
    exit "${rc}" ;;

  *) echo "用法: ticket_batch_check.sh --msg <file> | --emit-event <sha> | --push-range <range> --local-sha <sha>[,<sha>]" >&2; exit 2 ;;
esac
