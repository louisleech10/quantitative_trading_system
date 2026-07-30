#!/usr/bin/env bash
# debt_ledger.sh — P1-6 Task 2.1：只讀 audit 推導未結案債（不另存狀態檔）
#
# 子命令:
#   --list                 列出 cutoff 後各輪狀態（含 OPEN/CLOSED/ABANDONED）
#   --has-open             rc 0=無 OPEN 債／1=有 OPEN 債／2=fail-closed
#   --abandoned-count      依 abandon_kind 分開輸出兩個數字
#   --round-exists-single <round_id>
#                          只做該 round 存在性掃描（不跑全域序號連續性）
#                          rc 0=存在／1=不存在／2=fail-closed（缺檔/壞 JSON）
#   --round-state <round_id>
#                          印 OPEN|CLOSED|ABANDONED（含序號連續性；不存在→rc=1）
#
# 環境:
#   DEBT_AUDIT_OVERRIDE    測試隔離 audit 路徑；必須 GOVERNANCE_TEST_HARNESS=1
#   DEBT_CUTOFF_OVERRIDE   覆寫 registry cutoff_ts；必須 GOVERNANCE_TEST_HARNESS=1
#
# 憲法: bash 3.2；禁 declare -A／flock；rc 直接取禁經 pipe；不另存狀態檔。
#
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
REGISTRY="${SCRIPT_DIR}/audit_events.json"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
用法:
  bash scripts/debt_ledger.sh --list
  bash scripts/debt_ledger.sh --has-open
  bash scripts/debt_ledger.sh --abandoned-count
  bash scripts/debt_ledger.sh --round-exists-single <round_id>
  bash scripts/debt_ledger.sh --round-state <round_id>
EOF
}

# ── 路徑／cutoff 解析（與 audit_append 同型）────────────────
_resolve_audit_path() {
  if [ -n "${DEBT_AUDIT_OVERRIDE:-}" ]; then
    if [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
      echo "ERROR: DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1" >&2
      return 1
    fi
    printf '%s\n' "${DEBT_AUDIT_OVERRIDE}"
    return 0
  fi
  python3 - "${REGISTRY}" "${REPO}" <<'PY'
import json
import os
import sys

reg_path, repo = sys.argv[1], sys.argv[2]
try:
    with open(reg_path, encoding="utf-8") as fh:
        reg = json.load(fh)
except Exception as exc:
    print(f"ERROR: registry 讀取失敗: {exc}", file=sys.stderr)
    sys.exit(1)
rel = reg.get("audit_log_path")
if not isinstance(rel, str) or not rel:
    print("ERROR: registry 缺 audit_log_path", file=sys.stderr)
    sys.exit(1)
print(os.path.join(repo, rel))
PY
}

_resolve_cutoff() {
  # stdout = ISO-8601 cutoff；fail → rc≠0
  if [ -n "${DEBT_CUTOFF_OVERRIDE:-}" ]; then
    if [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
      echo "ERROR: DEBT_CUTOFF_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1" >&2
      return 1
    fi
    printf '%s\n' "${DEBT_CUTOFF_OVERRIDE}"
    return 0
  fi
  python3 - "${REGISTRY}" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        reg = json.load(fh)
except Exception as exc:
    print(f"ERROR: registry 讀取失敗: {exc}", file=sys.stderr)
    sys.exit(1)
c = reg.get("cutoff_ts")
if not isinstance(c, str) or not c:
    print("ERROR: registry 缺 cutoff_ts", file=sys.stderr)
    sys.exit(1)
print(c)
PY
}

# ── Python 核心：掃描 audit ──────────────────────────────
# 模式經 argv 傳入：
#   list | has_open | abandoned_count | round_exists | round_state | dump_json
# dump_json：stdout 完整結構化結果（給 debt_clear 消費）
_ledger_core() {
  local mode="$1"
  local round_id_arg="${2:-}"
  local audit_path cutoff
  audit_path="$(_resolve_audit_path)" || return 2
  cutoff="$(_resolve_cutoff)" || return 2

  # 缺檔 → fail-closed（空檔可無債）
  if [ ! -e "${audit_path}" ]; then
    echo "ERROR: audit 檔缺失: ${audit_path}" >&2
    return 2
  fi
  if [ ! -f "${audit_path}" ]; then
    echo "ERROR: audit 路徑不是一般檔: ${audit_path}" >&2
    return 2
  fi

  DEBT_LEDGER_MODE="${mode}" \
  DEBT_LEDGER_ROUND_ID="${round_id_arg}" \
  DEBT_LEDGER_AUDIT="${audit_path}" \
  DEBT_LEDGER_CUTOFF="${cutoff}" \
  DEBT_LEDGER_REGISTRY="${REGISTRY}" \
  python3 <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

mode = os.environ["DEBT_LEDGER_MODE"]
round_id_arg = os.environ.get("DEBT_LEDGER_ROUND_ID") or ""
audit_path = os.environ["DEBT_LEDGER_AUDIT"]
cutoff_raw = os.environ["DEBT_LEDGER_CUTOFF"]
reg_path = os.environ["DEBT_LEDGER_REGISTRY"]

def die(msg: str, rc: int = 2) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(rc)

try:
    with open(reg_path, encoding="utf-8") as fh:
        reg = json.load(fh)
except Exception as exc:
    die(f"registry 壞: {exc}")

debt_events = set((reg.get("debt_events") or {}).keys())
legacy_events = set(reg.get("non_debt_legacy_events") or [])
if not debt_events:
    die("registry debt_events 空")

def parse_ts(s: str):
    if not isinstance(s, str) or not s:
        return None
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

cutoff_dt = parse_ts(cutoff_raw)
if cutoff_dt is None:
    die(f"cutoff_ts 無法解析: {cutoff_raw!r}")

try:
    raw = open(audit_path, encoding="utf-8").read()
except OSError as exc:
    die(f"讀 audit 失敗: {exc}")

records = []  # after-cutoff debt records (for debt math)
all_debt_for_seq = []  # all debt records with sequence (continuity)
malformed = False

for line_no, line in enumerate(raw.splitlines(), 1):
    s = line.strip()
    if not s:
        continue
    if not s.startswith("{"):
        # 非 JSON 行略過（註解／legacy 純文字）
        continue
    try:
        rec = json.loads(s)
    except json.JSONDecodeError as exc:
        # 以 { 開頭但解析失敗 → fail-closed（半截寫入不得靜默忽略）
        print(
            f"ERROR: audit 第 {line_no} 行 JSON 無法解析(fail-closed): {exc}",
            file=sys.stderr,
        )
        sys.exit(2)
    if not isinstance(rec, dict):
        continue
    ev = rec.get("event")
    if ev in legacy_events:
        continue
    if ev not in debt_events:
        # 非白名單 debt／legacy：略過（未知 p16 命名空間由 append 端擋）
        continue
    all_debt_for_seq.append(rec)
    ts = parse_ts(rec.get("ts") if isinstance(rec.get("ts"), str) else "")
    if ts is None:
        # 缺 ts 或壞 ts：保守 fail-closed（無法判定 cutoff）
        die(f"debt 事件缺合法 ts (line {line_no}, event={ev})")
    if ts < cutoff_dt:
        continue
    records.append(rec)

def seq_of(rec):
    seq = rec.get("sequence")
    if isinstance(seq, int) and not isinstance(seq, bool):
        return seq
    if isinstance(seq, str) and seq.isdigit():
        return int(seq)
    return None

def assert_seq_continuity(debt_recs) -> None:
    """白名單事件序號缺號／重號 → fail-closed。"""
    seqs = []
    for rec in debt_recs:
        s = seq_of(rec)
        if s is None:
            die(f"debt 事件缺 sequence: event={rec.get('event')}")
        seqs.append(s)
    if not seqs:
        return
    seqs_sorted = sorted(seqs)
    # 重號
    if len(seqs_sorted) != len(set(seqs_sorted)):
        die("白名單事件序號重號(fail-closed)")
    # 缺號：必須是 1..max 連續
    mx = seqs_sorted[-1]
    expected = list(range(1, mx + 1))
    if seqs_sorted != expected:
        die(f"白名單事件序號缺號(fail-closed): got={seqs_sorted} expected={expected}")

def build_rounds(recs):
    """回傳 {round_id: state_info}；同一 round 兩筆 open → fail-closed。"""
    opens = {}  # round_id -> open rec
    clears = {}  # round_id -> list clear recs
    abandons = {}  # round_id -> list abandon recs
    results = []  # family results

    for rec in recs:
        ev = rec.get("event")
        rid = rec.get("round_id")
        if not isinstance(rid, str) or not rid:
            # open/result/clear/abandon 皆需 round_id；缺則 fail-closed
            die(f"debt 事件缺 round_id: event={ev}")
        if ev == "committee_round_open":
            if rid in opens:
                die(f"同一 round_id 兩筆 committee_round_open: {rid}")
            opens[rid] = rec
        elif ev == "committee_debt_clear":
            clears.setdefault(rid, []).append(rec)
        elif ev == "debt_abandon":
            abandons.setdefault(rid, []).append(rec)
        elif ev == "committee_family_result":
            results.append(rec)

    rounds = {}
    for rid, open_rec in opens.items():
        if rid in abandons:
            state = "ABANDONED"
        elif rid in clears:
            state = "CLOSED"
        else:
            state = "OPEN"
        parts = open_rec.get("participants")
        if not isinstance(parts, list):
            parts = []
        parts_norm = [p for p in parts if isinstance(p, str)]
        rounds[rid] = {
            "round_id": rid,
            "state": state,
            "session_name": open_rec.get("session_name") or "",
            "participants": parts_norm,
            "open": open_rec,
            "clears": clears.get(rid, []),
            "abandons": abandons.get(rid, []),
        }

    # 孤兒 clear/abandon（無 open）不列為輪，但也不 crash——視為無效殘留
    return rounds, results

def latest_result_per_family(results, round_id: str):
    """同一 (round_id, family) 取 sequence 最大。"""
    best = {}
    for rec in results:
        if rec.get("round_id") != round_id:
            continue
        fam = rec.get("family")
        if not isinstance(fam, str) or not fam:
            continue
        s = seq_of(rec)
        if s is None:
            continue
        prev = best.get(fam)
        if prev is None or seq_of(prev) < s:
            best[fam] = rec
    return best

# ── 模式分派 ────────────────────────────────────────────
if mode == "round_exists":
    # 只做 round_id 存在性；不跑全域序號連續性（防死鎖）
    # 仍對壞 JSON fail-closed（上面已處理）
    # 語意 fail-closed：同一 round 非恰一筆 open → rc=2（不得讓 --abandon 吞掉）
    # pre-cutoff open 仍「存在」（SPEC：只做 round_id 存在性掃描）
    n_open = 0
    for rec in all_debt_for_seq:
        if rec.get("event") == "committee_round_open" and rec.get("round_id") == round_id_arg:
            n_open += 1
    if n_open == 0:
        sys.exit(1)
    if n_open != 1:
        print(
            f"ERROR: 同一 round_id 非恰一筆 committee_round_open（got={n_open}）: {round_id_arg}",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(0)

# 以下模式皆需序號連續性（round_exists 除外）
assert_seq_continuity(all_debt_for_seq)
rounds, results = build_rounds(records)

if mode == "list":
    # 穩定排序：依 open 的 sequence
    items = []
    for rid, info in rounds.items():
        s = seq_of(info["open"]) or 0
        items.append((s, rid, info))
    items.sort(key=lambda x: (x[0], x[1]))
    for _, rid, info in items:
        parts = ",".join(info["participants"])
        print(
            f"round_id={rid} state={info['state']} "
            f"session_name={info['session_name']} participants={parts}"
        )
    sys.exit(0)

if mode == "has_open":
    n_open = sum(1 for info in rounds.values() if info["state"] == "OPEN")
    sys.exit(0 if n_open == 0 else 1)

if mode == "abandoned_count":
    # 依 abandon_kind 分開計數；registry 是 SoT，缺失／空／非恰兩值 → fail-closed
    # （禁硬編 fallback：SoT 損壞不得產出「看起來可信」的稽核數字）
    kinds = (reg.get("enums") or {}).get("abandon_kind")
    if not isinstance(kinds, list) or len(kinds) != 2:
        die("registry enums.abandon_kind 須恰兩值（fail-closed，無硬編 fallback）")
    if not all(isinstance(k, str) and k for k in kinds):
        die("registry enums.abandon_kind 含非法值")
    counts = {k: 0 for k in kinds}
    for info in rounds.values():
        for ab in info.get("abandons") or []:
            k = ab.get("abandon_kind")
            if k in counts:
                counts[k] += 1
    # 固定輸出兩種（registry 順序）
    # 格式例：累積放棄：no-findings-expected 12 筆／collection-failed 1 筆
    parts = [f"{k} {counts.get(k, 0)} 筆" for k in kinds]
    print("累積放棄：" + "／".join(parts))
    sys.exit(0)

if mode == "round_state":
    if round_id_arg not in rounds:
        print(f"ERROR: round_id 不存在(cutoff 後): {round_id_arg}", file=sys.stderr)
        sys.exit(1)
    print(rounds[round_id_arg]["state"])
    sys.exit(0)

if mode == "dump_json":
    # 給 debt_clear 消費的結構化快照
    out_rounds = {}
    for rid, info in rounds.items():
        latest = latest_result_per_family(results, rid)
        out_rounds[rid] = {
            "round_id": rid,
            "state": info["state"],
            "session_name": info["session_name"],
            "participants": info["participants"],
            "latest_results": {
                fam: {
                    "result_state": rec.get("result_state"),
                    "output_path": rec.get("output_path"),
                    "output_sha256": rec.get("output_sha256"),
                    "sequence": seq_of(rec),
                }
                for fam, rec in latest.items()
            },
            "open": {
                "participants": info["participants"],
                "session_name": info["session_name"],
                "expected_outputs": info["open"].get("expected_outputs"),
            },
        }
    print(json.dumps({"rounds": out_rounds}, ensure_ascii=False, sort_keys=True))
    sys.exit(0)

die(f"未知 mode: {mode}")
PY
  return $?
}

# ── 具名函式（TODO 要求；供 source 或 CLI 呼叫）──────────
_iter_json_lines() {
  # stdout: 合法 JSON 行；壞 JSON → rc=2
  local audit_path
  audit_path="$(_resolve_audit_path)" || return 2
  [ -f "${audit_path}" ] || {
    echo "ERROR: audit 檔缺失: ${audit_path}" >&2
    return 2
  }
  DEBT_LEDGER_AUDIT="${audit_path}" python3 <<'PY'
import json, os, sys
path = os.environ["DEBT_LEDGER_AUDIT"]
try:
    raw = open(path, encoding="utf-8").read()
except OSError as exc:
    print(f"ERROR: 讀 audit 失敗: {exc}", file=sys.stderr)
    sys.exit(2)
for line_no, line in enumerate(raw.splitlines(), 1):
    s = line.strip()
    if not s or not s.startswith("{"):
        continue
    try:
        json.loads(s)
    except json.JSONDecodeError as exc:
        print(f"ERROR: audit 第 {line_no} 行 JSON 無法解析(fail-closed): {exc}", file=sys.stderr)
        sys.exit(2)
    print(s)
PY
}

_assert_seq_continuity() {
  _ledger_core has_open >/dev/null
  local rc=$?
  # has_open 的 0/1 皆表示連續性通過；2=fail
  if [ "${rc}" -eq 2 ]; then
    return 2
  fi
  return 0
}

_round_exists_single() {
  # $1=round_id；不跑全域序號連續性
  local rid="${1:-}"
  [ -n "${rid}" ] || {
    echo "ERROR: _round_exists_single 需要 round_id" >&2
    return 2
  }
  _ledger_core round_exists "${rid}"
}

_round_state() {
  # $1=round_id；stdout=OPEN|CLOSED|ABANDONED
  local rid="${1:-}"
  [ -n "${rid}" ] || {
    echo "ERROR: _round_state 需要 round_id" >&2
    return 2
  }
  _ledger_core round_state "${rid}"
}

_latest_result_per_family() {
  # $1=round_id；stdout=JSON object family→result
  local rid="${1:-}"
  [ -n "${rid}" ] || return 2
  local dump
  dump="$(_ledger_core dump_json)" || return $?
  DEBT_LEDGER_DUMP="${dump}" DEBT_LEDGER_RID="${rid}" python3 <<'PY'
import json, os, sys
dump = json.loads(os.environ["DEBT_LEDGER_DUMP"])
rid = os.environ["DEBT_LEDGER_RID"]
info = (dump.get("rounds") or {}).get(rid)
if not info:
    print("{}", end="")
    sys.exit(0)
print(json.dumps(info.get("latest_results") or {}, ensure_ascii=False, sort_keys=True))
PY
}

_cmd_list() {
  _ledger_core list
}

_cmd_has_open() {
  # ⚠️ 不可用 pipeline 取 rc（JSON parse 失敗 rc=2 會被吞）
  _ledger_core has_open
}

_cmd_abandoned_count() {
  _ledger_core abandoned_count
}

# ── CLI 入口 ────────────────────────────────────────────
_debt_ledger_main() {
  if [ $# -lt 1 ]; then
    usage
    exit 2
  fi
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    --list)
      _cmd_list
      exit $?
      ;;
    --has-open)
      _cmd_has_open
      exit $?
      ;;
    --abandoned-count)
      _cmd_abandoned_count
      exit $?
      ;;
    --round-exists-single)
      [ $# -ge 2 ] || die "--round-exists-single 需要 <round_id>"
      _round_exists_single "$2"
      exit $?
      ;;
    --round-state)
      [ $# -ge 2 ] || die "--round-state 需要 <round_id>"
      _round_state "$2"
      exit $?
      ;;
    --dump-json)
      # 內部／測試用
      _ledger_core dump_json
      exit $?
      ;;
    *)
      echo "ERROR: 未知參數: $1" >&2
      usage
      exit 2
      ;;
  esac
}

# 被 source 時不跑 CLI（debt_clear 會 source 本檔）。
# 判定 sourced **只可用 BASH_SOURCE**（bash 自身提供、呼叫端無法偽造）。
# 禁止任何外部 marker（含 DEBT_LEDGER_SOURCED）——env 當「內部呼叫」標記違反反 bypass 紅線。
if [ "${BASH_SOURCE[0]-}" = "${0}" ] || [ -z "${BASH_SOURCE[0]-}" ]; then
  _debt_ledger_main "$@"
fi
