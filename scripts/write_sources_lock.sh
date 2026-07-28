#!/usr/bin/env bash
# write_sources_lock.sh — 寫入 session sources.lock（Task 3.1 lock writer helper）
#
# 放在 scripts/（gate.sh dispatch 主體可呼叫）；**非** dispatch.sh 薄 wrapper（TC15）。
#
# 用法:
#   bash scripts/write_sources_lock.sh --session <session_dir> --roster fam1,fam2,...
#   bash scripts/write_sources_lock.sh --session <session_dir> --roster fam1 --roster fam2
#   bash scripts/write_sources_lock.sh --session <session_dir> --roster fam1 --mode discovery|review
#   bash scripts/write_sources_lock.sh --session <session_dir> --roster fam1 --mode discovery --round-id <id>
#   bash scripts/write_sources_lock.sh --session <session_dir> --roster fam1 --mode review --rebuild
#
# ⚠️ review lock 一律拒收呼叫端傳入的 --round-id（B1-FIX / 三家裁決 (甲)）:
#   identity 必須由本腳本自 audit 反查導出（以 session basename == session_name 為鍵,
#   套用「恰一筆 + OPEN」）。上方第 3 行的 --round-id 僅適用 discovery。
#   舊用法 `--mode review --round-id <id> --rebuild` **已失效**,照抄會 rc≠0。
#   (COMPOSER-R3-P2-01 / GROK-R3-P2-02: 本註解原本仍示範舊用法, 屬文件漂移)
#
# ⚠️ 雙預設不一致(COMPOSER-R3-P2-02, 已知且刻意保留):
#   本腳本預設 mode=review, 而 reconcile_build.sh 預設 discovery。
#   故【直呼本腳本不帶 --mode】會落入 review → 需要 audit → 比 B1 前更容易 fail-closed。
#   正式流程請一律經 reconcile_build.sh, 或明確帶 --mode。
#
# 行為:
#   - 掃描 <session>/sources/ 下一層 *.md（不遞迴）
#   - 僅收 *-<family>.md（family ∈ codex|composer|grok|claude|agy）
#   - 寫 sources.lock schema v1: version/session_id/round_id/expected_roster/sources[{realpath,sha256,family}]/freeze_ts/closure_state/mode
#   - mode: discovery|review（預設 review；非法值 exit≠0）
#   - sources 依 realpath 排序
#   - 既有 lock 且 closure_state=FROZEN → 拒覆寫 exit 1（freeze 後不可靜默改）
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
REGISTRY="${SCRIPT_DIR}/audit_events.json"

SESSION=""
ROSTER_CSV=""
ROSTER_ARGS=()
FORCE=0
MODE="review"
ROUND_ID=""
REBUILD=0

usage() {
  cat <<'EOF'
用法:
  bash scripts/write_sources_lock.sh --session <session_dir> --roster codex,composer,grok
  bash scripts/write_sources_lock.sh --session <session_dir> --roster codex --roster composer
選項:
  --mode discovery|review   lock 模式（預設 review；discovery 免 P0/P1 來源摘要 digest）
  --round-id <id>           僅供 discovery 相容路徑；review 一律由 audit 導出
  --rebuild                 只就地改寫既有 lock 的 mode 與 audit 導出的 round_id（discovery → review）
  --force   允許覆寫既有 FROZEN lock（僅重建/測試；正式 freeze 後勿用）
EOF
}

_lookup_round_id() {
  python3 - "${REGISTRY}" "${REPO}" "$1" <<'PY'
import json
import os
import sys

registry_path, repo, session_name = sys.argv[1:]
try:
    with open(registry_path, encoding="utf-8") as fh:
        registry = json.load(fh)
    audit_path = os.path.join(repo, registry["audit_log_path"])
    with open(audit_path, encoding="utf-8") as fh:
        lines = fh.readlines()
except Exception as exc:
    print(f"ERROR: audit 讀取失敗(fail-closed): {exc}", file=sys.stderr)
    sys.exit(1)

open_events = [
    name for name, spec in registry.get("debt_events", {}).items()
    if spec.get("opens_debt")
]
if len(open_events) != 1:
    print("ERROR: registry 的 opens_debt 事件不是恰一筆", file=sys.stderr)
    sys.exit(1)

hits = []
for line_no, raw in enumerate(lines, 1):
    line = raw.strip()
    if not line or not line.startswith("{"):
        continue
    try:
        record = json.loads(line)
    except Exception as exc:
        print(f"ERROR: audit 第 {line_no} 行 JSON 無法解析(fail-closed): {exc}", file=sys.stderr)
        sys.exit(1)
    if record.get("event") == open_events[0] and record.get("session_name") == session_name:
        hits.append(record)

if len(hits) != 1:
    print(f"ERROR: session_name 命中 {len(hits)} 筆(需恰 1): {session_name}", file=sys.stderr)
    sys.exit(1)
round_id = hits[0].get("round_id")
if not isinstance(round_id, str) or not round_id:
    print("ERROR: committee_round_open 缺非空 round_id", file=sys.stderr)
    sys.exit(1)
print(round_id)
PY
}

_assert_round_open() {
  python3 - "${REGISTRY}" "${REPO}" "$1" <<'PY'
import json
import os
import sys

registry_path, repo, round_id = sys.argv[1:]
try:
    with open(registry_path, encoding="utf-8") as fh:
        registry = json.load(fh)
    audit_path = os.path.join(repo, registry["audit_log_path"])
    with open(audit_path, encoding="utf-8") as fh:
        lines = fh.readlines()
except Exception as exc:
    print(f"ERROR: audit 讀取失敗(fail-closed): {exc}", file=sys.stderr)
    sys.exit(1)

events = registry.get("debt_events", {})
open_events = [name for name, spec in events.items() if spec.get("opens_debt")]
close_events = {name for name, spec in events.items() if spec.get("closes_debt")}
terminal_events = {name for name, spec in events.items() if spec.get("terminal")}
if len(open_events) != 1 or len(close_events) != 1 or len(terminal_events) != 1:
    print("ERROR: registry 狀態事件契約不完整", file=sys.stderr)
    sys.exit(1)

open_count = 0
closed = False
for line_no, raw in enumerate(lines, 1):
    line = raw.strip()
    if not line or not line.startswith("{"):
        continue
    try:
        record = json.loads(line)
    except Exception as exc:
        print(f"ERROR: audit 第 {line_no} 行 JSON 無法解析(fail-closed): {exc}", file=sys.stderr)
        sys.exit(1)
    if record.get("round_id") != round_id:
        continue
    if record.get("event") == open_events[0]:
        open_count += 1
    elif record.get("event") in close_events or record.get("event") in terminal_events:
        closed = True

if open_count != 1 or closed:
    print(
        f"ERROR: round_id 非 OPEN(開債={open_count}, terminal_or_clear={str(closed).lower()})",
        file=sys.stderr,
    )
    sys.exit(1)
PY
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --session)
      SESSION="${2:-}"; shift 2 ;;
    --roster)
      if [ -z "${2:-}" ]; then echo "ERROR: --roster 需要值" >&2; exit 2; fi
      if [ -n "${ROSTER_CSV}" ]; then ROSTER_CSV="${ROSTER_CSV},$2"; else ROSTER_CSV="$2"; fi
      ROSTER_ARGS+=("$2")
      shift 2 ;;
    --mode)
      if [ -z "${2:-}" ]; then echo "ERROR: --mode 需要值 discovery|review" >&2; exit 2; fi
      MODE="$2"
      shift 2 ;;
    --round-id)
      if [ -z "${2:-}" ]; then echo "ERROR: --round-id 需要值" >&2; exit 2; fi
      ROUND_ID="$2"
      shift 2 ;;
    --rebuild)
      REBUILD=1
      shift ;;
    --force)
      FORCE=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "ERROR: 未知參數: $1" >&2; usage; exit 2 ;;
  esac
done

[ -n "${SESSION}" ] || { echo "ERROR: 必填 --session" >&2; usage; exit 2; }
if [ "${REBUILD}" != "1" ] && [ -z "${ROSTER_CSV}" ]; then
  echo "ERROR: 必填 --roster" >&2
  usage
  exit 2
fi

# mode 只允許 discovery|review（非法 → exit≠0；禁 env 覆寫）
case "${MODE}" in
  discovery|review) ;;
  *)
    echo "ERROR: --mode 非法值 '${MODE}'（允許: discovery|review）" >&2
    exit 1
    ;;
esac

# 反 bypass(CODEX-B3C-P2-01)：--force 覆寫 FROZEN lock 僅測試 harness 可用；正式路徑拒。
if [ "${FORCE}" = "1" ] && [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
  echo "ERROR: --force 覆寫 FROZEN lock 僅允許 GOVERNANCE_TEST_HARNESS=1（正式路徑 fail-closed）" >&2
  exit 1
fi

if [ "${REBUILD}" = "1" ] && [ "${FORCE}" = "1" ]; then
  echo "ERROR: --rebuild 不得與 --force 併用" >&2
  exit 1
fi

# BC4：physical path 統一（macOS /var → /private/var；與 lock realpath 一致）
SESSION="$(cd "${SESSION}" && pwd -P)"
SOURCES_DIR="${SESSION}/sources"
LOCK_PATH="${SESSION}/sources.lock"

if [ ! -d "${SOURCES_DIR}" ]; then
  echo "ERROR: sources/ 不存在: ${SOURCES_DIR}" >&2
  exit 1
fi

if [ "${REBUILD}" = "1" ]; then
  [ -z "${ROUND_ID}" ] || {
    echo "ERROR: --rebuild 拒收呼叫端 --round-id；identity 必須由 audit 導出" >&2
    exit 1
  }
  [ "${MODE}" = "review" ] || {
    echo "ERROR: --rebuild 僅允許目標 mode=review" >&2
    exit 1
  }
  [ -f "${LOCK_PATH}" ] || {
    echo "ERROR: --rebuild 需既有 sources.lock: ${LOCK_PATH}" >&2
    exit 1
  }
  ROUND_ID="$(_lookup_round_id "$(basename "${SESSION}")")" || exit 1
  _assert_round_open "${ROUND_ID}" || exit 1
  python3 - "${LOCK_PATH}" "${MODE}" "${ROUND_ID}" <<'PY'
import json
import sys

lock_path, target_mode, round_id = sys.argv[1:]
try:
    with open(lock_path, encoding="utf-8") as fh:
        lock = json.load(fh)
except Exception as exc:
    print(f"ERROR: sources.lock 無法解析: {exc}", file=sys.stderr)
    sys.exit(1)

if target_mode != "review":
    print("ERROR: --rebuild 僅允許目標 mode=review", file=sys.stderr)
    sys.exit(1)
if lock.get("mode") != "discovery":
    print(
        "ERROR: --rebuild 僅允許 discovery → review；"
        f"現有 mode={lock.get('mode', '') or 'missing'}",
        file=sys.stderr,
    )
    sys.exit(1)
if lock.get("closure_state") != "FROZEN":
    print("ERROR: --rebuild 只允許既有 FROZEN lock", file=sys.stderr)
    sys.exit(1)

# 只改兩個 identity/mode 欄位；sources、hash、expected_roster 及其餘欄位原樣保留。
lock["mode"] = "review"
lock["round_id"] = round_id
with open(lock_path, "w", encoding="utf-8") as fh:
    json.dump(lock, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
print(f"OK: rebuilt {lock_path} (mode=review, round_id={round_id})")
PY
  exit $?
fi

if [ "${MODE}" = "review" ]; then
  [ -z "${ROUND_ID}" ] || {
    echo "ERROR: review lock 拒收呼叫端 --round-id；identity 必須由 audit 導出" >&2
    exit 1
  }
  ROUND_ID="$(_lookup_round_id "$(basename "${SESSION}")")" || exit 1
fi

if [ -f "${LOCK_PATH}" ] && [ "${FORCE}" != "1" ]; then
  state="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("closure_state",""))' "${LOCK_PATH}" 2>/dev/null || echo "")"
  if [ "${state}" = "FROZEN" ]; then
    echo "ERROR: sources.lock 已 FROZEN，拒覆寫（用 --force 僅限測試重建）: ${LOCK_PATH}" >&2
    exit 1
  fi
fi

python3 - "${SESSION}" "${ROSTER_CSV}" "${LOCK_PATH}" "${MODE}" "${ROUND_ID}" <<'PY'
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

session, roster_csv, lock_path, mode, round_id = sys.argv[1:6]
if mode not in ("discovery", "review"):
    print(f"ERROR: --mode 非法值 '{mode}'（允許: discovery|review）", file=sys.stderr)
    sys.exit(1)
sources_dir = os.path.join(session, "sources")
family_re = re.compile(r"^.+-(codex|composer|grok|claude|agy)\.md$", re.I)
allow = {"codex", "composer", "grok", "claude", "agy"}

roster = []
for part in roster_csv.split(","):
    p = part.strip().lower()
    if not p:
        continue
    if p not in allow:
        print(f"ERROR: roster family 不在 allowlist: {p}", file=sys.stderr)
        sys.exit(1)
    if p not in roster:
        roster.append(p)

entries = []
for name in sorted(os.listdir(sources_dir)):
    path = os.path.join(sources_dir, name)
    if not os.path.isfile(path) and not os.path.islink(path):
        continue
    m = family_re.match(name)
    if not m:
        # 不收入 lock（M9 等污染由 completeness 磁碟掃描/名規抓）
        continue
    fam = m.group(1).lower()
    rp = os.path.realpath(path)
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    entries.append({"realpath": rp, "sha256": digest, "family": fam})

entries.sort(key=lambda e: e["realpath"])

lock = {
    "version": 1,
    "session_id": os.path.basename(session.rstrip("/")),
    "expected_roster": roster,
    "sources": entries,
    "freeze_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "closure_state": "FROZEN",
    "mode": mode,
}
if round_id:
    lock["round_id"] = round_id

with open(lock_path, "w", encoding="utf-8") as fh:
    json.dump(lock, fh, indent=2, ensure_ascii=False)
    fh.write("\n")

print(f"OK: wrote {lock_path} ({len(entries)} sources, roster={roster}, mode={mode})")
PY

exit $?
