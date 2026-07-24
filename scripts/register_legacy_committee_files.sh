#!/usr/bin/env bash
# register_legacy_committee_files.sh — one-time committee-process file registration.
#
# This script is intentionally narrow: it only registers the eight audited legacy
# handoff files from GOV_O3EXT_R7 Task 2.2 when their raw bytes match the
# hardcoded sha256 values below.

set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PY="${REPO_ROOT}/venv/bin/python"
[ -x "${VENV_PY}" ] || VENV_PY="$(command -v python3 || command -v python)"  # 無 venv(如 CI)→ python3
GATE_DIR="${GATE_DIR_OVERRIDE:-.claude/gate}"
AUDIT="${GATE_DIR}/audit.log"
mkdir -p "${GATE_DIR}"

usage() {
  echo "用法: bash scripts/register_legacy_committee_files.sh <handoffs/file.md> [more...]"
}

sha256_file() {
  "${VENV_PY}" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"
}

expected_sha() {
  case "$1" in
    handoffs/20260702-FF-ALIGN-ORACLE-FACTS.md) echo "984f27c04f57eca7689add75375e0aa3853d8d5e0473a71a6157c6d31e8e08c3" ;;
    handoffs/20260702-FF-ALIGN-ORACLE-DESIGN-CODEX.md) echo "53e7f6afc88faad3e4b4a80b12af13ddfb2d3fd26579f8d4f429361d120eceee" ;;
    handoffs/20260702-FF-DSTAR-GATE-CLAUDE.md) echo "e8a6b8e0180b135c5a0b023a2016e48e35378e38816cfc58e382cdaa0155cb1c" ;;
    handoffs/20260702-FF-DSTAR-GATE-CODEX.md) echo "35d4201f02f379adcec9b3483716f0d72e53ce5b64a0d178540b7cb6f75a0af4" ;;
    handoffs/20260702-FF-P0FF3-ALIGN-PROBE-FIX-PROMPT.md) echo "129e04e0f14b338acedec7ad0bdbef844433b49ab1ff2ccb5c4db3df4764ceab" ;;
    handoffs/20260702-FF-P0FF3-PROBE-FIX2-composer.md) echo "f8d08f90c7fa2d9486079d86c4b6626c43d18f03075e0466b207d7793e846992" ;;
    handoffs/20260702-FF-P1-57-IMPL-codex.md) echo "a7b7419f267b2a5145e00dc6b66190fa05c7cc12fe018cbf8e641b65435020db" ;;
    handoffs/20260702-FF-P1-57-REVIEW-composer.md) echo "c61ea432b7c811121a74a3b335ec11245d8fc9f59cb3a68ab3055d6200926143" ;;
    *) return 1 ;;
  esac
}

norm_rel() {
  "${VENV_PY}" - "$1" <<'PY'
import sys
from pathlib import Path

raw = sys.argv[1]
norm = raw.replace("\\", "/")
if norm.startswith("/"):
    root = Path.cwd().resolve()
    try:
        norm = Path(raw).resolve().relative_to(root).as_posix()
    except ValueError:
        marker = "handoffs/"
        idx = norm.find(marker)
        if idx >= 0:
            norm = norm[idx:]
print(norm)
PY
}

append_event() {
  local rel="$1"
  local sha="$2"
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%dT%H:%M:%SZ')"
  "${VENV_PY}" - "$rel" "$sha" "$ts" <<'PY' >> "${AUDIT}"
import json
import sys

path, sha, ts = sys.argv[1:4]
print(json.dumps(
    {
        "event": "committee_output",
        "task_id": "legacy-gov-o3ext-r7",
        "family": "legacy",
        "output_path": path,
        "output_sha256": sha,
        "ts": ts,
    },
    ensure_ascii=False,
    sort_keys=True,
))
PY
}

[ "$#" -gt 0 ] || { usage; exit 1; }

for arg in "$@"; do
  rel="$(norm_rel "$arg")"
  expected="$(expected_sha "$rel" 2>/dev/null)" || { echo "ERROR: legacy whitelist 不含:${arg}"; exit 1; }
  [ -f "$rel" ] || { echo "ERROR: legacy 檔不存在:${rel}"; exit 1; }
  actual="$(sha256_file "$rel")"
  [ "$actual" = "$expected" ] || { echo "ERROR: legacy sha256 不符:${rel} expected=${expected} actual=${actual}"; exit 1; }
done

for arg in "$@"; do
  rel="$(norm_rel "$arg")"
  append_event "$rel" "$(sha256_file "$rel")"
  echo "registered legacy committee file: ${rel}"
done
