#!/usr/bin/env bash
# write_sources_lock.sh — 寫入 session sources.lock（Task 3.1 lock writer helper）
#
# 放在 scripts/（gate.sh dispatch 主體可呼叫）；**非** dispatch.sh 薄 wrapper（TC15）。
#
# 用法:
#   bash scripts/write_sources_lock.sh --session <session_dir> --roster fam1,fam2,...
#   bash scripts/write_sources_lock.sh --session <session_dir> --roster fam1 --roster fam2
#   bash scripts/write_sources_lock.sh --session <session_dir> --roster fam1 --mode discovery|review
#
# 行為:
#   - 掃描 <session>/sources/ 下一層 *.md（不遞迴）
#   - 僅收 *-<family>.md（family ∈ codex|composer|grok|claude|agy）
#   - 寫 sources.lock schema v1: version/session_id/expected_roster/sources[{realpath,sha256,family}]/freeze_ts/closure_state/mode
#   - mode: discovery|review（預設 review；非法值 exit≠0）
#   - sources 依 realpath 排序
#   - 既有 lock 且 closure_state=FROZEN → 拒覆寫 exit 1（freeze 後不可靜默改）
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"

SESSION=""
ROSTER_CSV=""
ROSTER_ARGS=()
FORCE=0
MODE="review"

usage() {
  cat <<'EOF'
用法:
  bash scripts/write_sources_lock.sh --session <session_dir> --roster codex,composer,grok
  bash scripts/write_sources_lock.sh --session <session_dir> --roster codex --roster composer
選項:
  --mode discovery|review   lock 模式（預設 review；discovery 免 P0/P1 來源摘要 digest）
  --force   允許覆寫既有 FROZEN lock（僅重建/測試；正式 freeze 後勿用）
EOF
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
    --force)
      FORCE=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "ERROR: 未知參數: $1" >&2; usage; exit 2 ;;
  esac
done

[ -n "${SESSION}" ] || { echo "ERROR: 必填 --session" >&2; usage; exit 2; }
[ -n "${ROSTER_CSV}" ] || { echo "ERROR: 必填 --roster" >&2; usage; exit 2; }

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

# BC4：physical path 統一（macOS /var → /private/var；與 lock realpath 一致）
SESSION="$(cd "${SESSION}" && pwd -P)"
SOURCES_DIR="${SESSION}/sources"
LOCK_PATH="${SESSION}/sources.lock"

if [ ! -d "${SOURCES_DIR}" ]; then
  echo "ERROR: sources/ 不存在: ${SOURCES_DIR}" >&2
  exit 1
fi

if [ -f "${LOCK_PATH}" ] && [ "${FORCE}" != "1" ]; then
  state="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("closure_state",""))' "${LOCK_PATH}" 2>/dev/null || echo "")"
  if [ "${state}" = "FROZEN" ]; then
    echo "ERROR: sources.lock 已 FROZEN，拒覆寫（用 --force 僅限測試重建）: ${LOCK_PATH}" >&2
    exit 1
  fi
fi

python3 - "${SESSION}" "${ROSTER_CSV}" "${LOCK_PATH}" "${MODE}" <<'PY'
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

session, roster_csv, lock_path, mode = sys.argv[1:5]
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

with open(lock_path, "w", encoding="utf-8") as fh:
    json.dump(lock, fh, indent=2, ensure_ascii=False)
    fh.write("\n")

print(f"OK: wrote {lock_path} ({len(entries)} sources, roster={roster}, mode={mode})")
PY

exit $?
