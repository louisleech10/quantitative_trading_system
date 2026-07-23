#!/usr/bin/env bash
# completeness_check.sh — 綜合(reconcile/UNION)完整性機械檢查
#
# 病灶(2026-07-22 IC reconcile 手抄事故):Claude 手抄合併多方委員產物 → 靜默掉項。
# 方法:委員產物用 canonical finding ID;本腳本機械抽每個來源檔的 ID,
#   檢查是否**全部**出現在綜合檔。缺任一 → FAIL。
#
# 正式入口 (B3 Task 3.1):
#   bash scripts/completeness_check.sh --lock <session/sources.lock>
#   （可選 --synth <path>；預設 session/synth.md）
#   讀 lock 鎖定來源集合；**禁 argv/env 覆寫來源清單**。
#
# 測試隔離 argv 路徑（僅 tests/governance；須設 COMPLETENESS_ALLOW_ARGV_SOURCES=1）:
#   COMPLETENESS_ALLOW_ARGV_SOURCES=1 bash scripts/completeness_check.sh <綜合檔> <來源...>
#
# STRICT=1          → 來源無 ID 時 FAIL(預設 1)
# ALLOW_BARE_IDS=1  → 除錯用(B2 後仍拒非 canonical)
# ALLOW_ID_PATTERN_OVERRIDE=1 + ID_PATTERN=... → 除錯覆寫(gate/CI 禁止)
#
# B2: canonical ID / body 機檢 / digest / DEGRADE 命名空間 / dup
# B3: sources.lock / roster / 拒收 symlink·子目錄·root外·late·非md·非family / 拒 ADVISORY_ONLY
# B4 Task4.1: --self-check advisory + write-once first_draft receipt
# B4 Task5.1: DEGRADED_PENDING 狀態機（合法降級 exit 3；禁 waived:/skip 字串灰態）
#
# exit: 0=PASS/ADVISORY_MISSING(self-check); 1=FAIL/非法/檔缺; 3=DEGRADED_PENDING
set -u

# 全域：合法降級時由 _check_roster 置位；主路徑結束 exit 3
DEGRADED_MODE=0
DEGRADE_ESCALATE=0

# ---------------------------------------------------------------------------
# BC1 反 bypass：COMPLETENESS_ALLOW_ARGV_SOURCES 僅 GOVERNANCE_TEST_HARNESS=1 才認
# （正式路徑偵測到未 harness 的 argv 繞過 → fail-closed，非靜默忽略）
# ---------------------------------------------------------------------------
if [ -n "${COMPLETENESS_ALLOW_ARGV_SOURCES:-}" ] && [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
  echo "COMPLETENESS FAIL: COMPLETENESS_ALLOW_ARGV_SOURCES 僅允許 GOVERNANCE_TEST_HARNESS=1（正式路徑 fail-closed 拒 argv 來源）" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 正式路徑主動拒 COMPLETENESS_ADVISORY_ONLY（禁逃生口；TC24）
# ---------------------------------------------------------------------------
_reject_advisory_flag() {
  if [ -n "${COMPLETENESS_ADVISORY_ONLY:-}" ]; then
    echo "COMPLETENESS FAIL: advisory-only 逃生口禁用（COMPLETENESS_ADVISORY_ONLY）" >&2
    exit 1
  fi
}
_reject_advisory_flag

STRICT="${STRICT:-1}"
ALLOW_BARE_IDS="${ALLOW_BARE_IDS:-0}"

# 至少 ## (h2+)。單一 # 會把 markdown 註解誤當 heading。
HEADING_LINE_RE='^[[:space:]]*#{2,6}[[:space:]][[:space:]]*'

# B2 canonical: FAM-Rn-Pn-NN
CANONICAL_ID_RE='^([A-Z]+)-(R[0-9]+)-(P[0-3])-([0-9]{2,})$'
FAMILY_ALLOW_RE='^(CODEX|COMPOSER|GROK|CLAUDE|AGY)$'
DEGRADE_HEADING_RE='^[[:space:]]*#{2,6}[[:space:]]+DEGRADE-[A-Z]+-[0-9]{2,}[[:space:]]*$'
DEGRADE_TOKEN_RE='^DEGRADE-[A-Z]+-[0-9]{2,}$'
CANDIDATE_ID_RE='^[A-Z]+(-[A-Z0-9]+)+$'

# 檔名 *-<family>.md（family 小寫 allowlist）
FAMILY_FILE_RE='^(.+)-(codex|composer|grok|claude|agy)\.md$'

if [ -n "${ID_PATTERN:-}" ]; then
  # 反 bypass(CODEX-B3C-P0-03)：ID_PATTERN/ALLOW_ID_PATTERN_OVERRIDE 為 env 過濾 finding 的旁路,
  #   須同 BC1 綁 GOVERNANCE_TEST_HARNESS=1;正式/生產路徑 fail-closed。
  if [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
    echo "COMPLETENESS FAIL: ID_PATTERN 覆寫僅允許 GOVERNANCE_TEST_HARNESS=1（正式路徑 fail-closed 拒 env 過濾 finding）。" >&2
    exit 1
  fi
  if [ "${ALLOW_ID_PATTERN_OVERRIDE:-}" != "1" ]; then
    echo "COMPLETENESS FAIL: ID_PATTERN 覆寫需 ALLOW_ID_PATTERN_OVERRIDE=1(僅測試 harness)。" >&2
    exit 1
  fi
  USE_PATTERN_OVERRIDE=1
else
  USE_PATTERN_OVERRIDE=0
fi

_sha256_file() {
  local f="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${f}" | awk '{print $1}'
  else
    shasum -a 256 "${f}" | awk '{print $1}'
  fi
}

# ---------------------------------------------------------------------------
# extract_heading_ids — 輸出合法 canonical ID(每行一個;保留同檔重複以便 dup 偵測)
# ---------------------------------------------------------------------------
extract_heading_ids() {
  local file="$1"
  local rc=0
  if [ "${USE_PATTERN_OVERRIDE}" = "1" ]; then
    grep -oE "${ID_PATTERN}" "${file}" 2>/dev/null || true
    return 0
  fi

  # shellcheck disable=SC2016
  awk -v heading_re="${HEADING_LINE_RE}" '
    BEGIN {
      fam["CODEX"]=1; fam["COMPOSER"]=1; fam["GROK"]=1; fam["CLAUDE"]=1; fam["AGY"]=1
    }
    /^[[:space:]]*#{2,6}[[:space:]]+DEGRADE-[A-Z]+-[0-9]{2,}[[:space:]]*$/ { next }
    /^[[:space:]]*#{2,6}[[:space:]]/ {
      line=$0
      sub(/^[[:space:]]*#{2,6}[[:space:]]+/, "", line)
      sub(/[[:space:]]+$/, "", line)
      if (line == "") next
      if (line ~ /^DEGRADE-[A-Z]+-[0-9]{2,}$/) next
      if (line ~ /^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$/) {
        split(line, segs, "-")
        family=segs[1]
        if (!(family in fam)) {
          print "COMPLETENESS FAIL: invalid family in ID: " line " (file=" FILENAME ")" > "/dev/stderr"
          bad=1
          next
        }
        print line
        next
      }
      n=split(line, parts, /[[:space:]]+/)
      tok=parts[1]
      sub(/[^A-Za-z0-9_-].*$/, "", tok)
      if (tok ~ /^[A-Z]+(-[A-Z0-9]+)+$/) {
        print "COMPLETENESS FAIL: invalid finding ID (schema/trailing): " line " (file=" FILENAME ")" > "/dev/stderr"
        bad=1
        next
      }
      next
    }
    END { if (bad) exit 1 }
  ' "${file}"
  rc=$?
  return "${rc}"
}

# ---------------------------------------------------------------------------
# _validate_finding_body — 每 ## canonical ID 後須 **斷言**+**碼證**；P0/P1 另須 digest
# ---------------------------------------------------------------------------
_validate_finding_body() {
  local file="$1"
  # shellcheck disable=SC2016
  awk '
    BEGIN {
      id=""; sev=""; seen_assert=0; seen_code=0; seen_digest=0; bad=0
    }
    function flush() {
      if (id == "") return
      if (!(seen_assert && seen_code)) {
        print "COMPLETENESS FAIL: empty-shell finding (缺 **斷言**/**碼證**): " id " (file=" FILENAME ")" > "/dev/stderr"
        bad=1
      }
      if (sev == "P0" || sev == "P1") {
        if (!seen_digest) {
          print "COMPLETENESS FAIL: P0/P1 missing source digest (**來源摘要** or source_digest:): " id " (file=" FILENAME ")" > "/dev/stderr"
          bad=1
        }
      }
    }
    /^[[:space:]]*#{2,6}[[:space:]]/ {
      if ($0 ~ /^[[:space:]]*#{2,6}[[:space:]]+DEGRADE-[A-Z]+-[0-9]{2,}[[:space:]]*$/) {
        flush()
        id=""; sev=""; seen_assert=0; seen_code=0; seen_digest=0
        next
      }
      line=$0
      sub(/^[[:space:]]*#{2,6}[[:space:]]+/, "", line)
      n=split(line, parts, /[[:space:]]+/)
      tok=(n >= 1 ? parts[1] : "")
      sub(/[^A-Za-z0-9_-].*$/, "", tok)
      if (tok ~ /^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$/) {
        flush()
        id=tok
        split(tok, segs, "-")
        sev=segs[3]
        seen_assert=0; seen_code=0; seen_digest=0
        next
      }
      if (id != "") {
        flush()
        id=""; sev=""; seen_assert=0; seen_code=0; seen_digest=0
      }
      next
    }
    id != "" {
      if ($0 ~ /\*\*斷言\*\*/) seen_assert=1
      if ($0 ~ /\*\*碼證\*\*/) seen_code=1
      if ($0 ~ /\*\*來源摘要\*\*/ && $0 ~ /#[0-9a-fA-F]{12}/) seen_digest=1
      if ($0 ~ /source_digest:[[:space:]]*[0-9a-fA-F]{12,}/) seen_digest=1
    }
    END {
      flush()
      if (bad) exit 1
    }
  ' "${file}"
}

_check_same_file_dups() {
  local file="$1"
  local ids="$2"
  local dups
  dups="$(printf '%s\n' "${ids}" | sed '/^$/d' | sort | uniq -d)"
  if [ -n "${dups}" ]; then
    echo "COMPLETENESS FAIL: same-file duplicate ID(s) in ${file}:" >&2
    while IFS= read -r d; do
      [ -n "${d}" ] && printf '  · %s\n' "${d}" >&2
    done <<< "${dups}"
    return 1
  fi
  return 0
}

# ---------------------------------------------------------------------------
# _load_lock — 讀 sources.lock；version 不符 / 缺檔 → exit 1
# 設定全域: LOCK_PATH, SESS_DIR, SOURCES_ROOT, LOCK_JSON 相關透過 temp 檔
# ---------------------------------------------------------------------------
_load_lock() {
  local lock_path="$1"
  if [ ! -f "${lock_path}" ]; then
    echo "COMPLETENESS FAIL: sources.lock 不存在(fail-closed): ${lock_path}" >&2
    exit 1
  fi
  # BC4：一律 physical path（pwd -P / realpath），避免 macOS /var vs /private/var 前綴誤判
  LOCK_PATH="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${lock_path}")"
  SESS_DIR="$(python3 -c 'import os,sys; print(os.path.realpath(os.path.dirname(sys.argv[1])))' "${LOCK_PATH}")"
  SOURCES_ROOT="${SESS_DIR}/sources"

  # version 必須為 1
  local ver
  ver="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("version",""))' "${LOCK_PATH}" 2>/dev/null || echo "")"
  if [ "${ver}" != "1" ]; then
    echo "COMPLETENESS FAIL: sources.lock version 不符(期望 1, 得 ${ver:-missing})" >&2
    exit 1
  fi

  local state
  state="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("closure_state",""))' "${LOCK_PATH}" 2>/dev/null || echo "")"
  if [ "${state}" != "FROZEN" ]; then
    echo "COMPLETENESS FAIL: sources.lock closure_state 須為 FROZEN(得 ${state:-missing})" >&2
    exit 1
  fi
}

# ---------------------------------------------------------------------------
# _check_degrade_event — 合法降級前提：DEGRADE heading + degrade.json + min_families≥2
# 成功 → 設 DEGRADED_MODE=1（與可選 DEGRADE_ESCALATE）；失敗 → return 1
# ---------------------------------------------------------------------------
_check_degrade_event() {
  local lock_path="$1"
  local missing_csv="$2"   # comma-separated lower-case families
  local synth="${3:-}"
  local sess_dir
  sess_dir="$(python3 -c 'import os,sys; print(os.path.realpath(os.path.dirname(sys.argv[1])))' "${lock_path}")"
  local degrade_json="${sess_dir}/degrade.json"

  if [ -z "${synth}" ]; then
    synth="${sess_dir}/synth.md"
  fi

  # 禁 waived:/skip 字串（任何 degrade 資料面；非灰態逃生口）
  if [ -f "${degrade_json}" ]; then
    if grep -Eiq 'waived:|/skip\b|\bskip\b|ALLOWLIST|ADVISORY_ONLY' "${degrade_json}" 2>/dev/null; then
      echo "COMPLETENESS FAIL: degrade.json 含禁用語(waived:/skip/ALLOWLIST/ADVISORY_ONLY)；P0/P1 不得 waiver" >&2
      return 1
    fi
  fi

  # min_families：present families from lock.sources
  local present_n
  present_n="$(python3 - "${lock_path}" <<'PY'
import json, sys
lock = json.load(open(sys.argv[1], encoding="utf-8"))
fams = {str(s.get("family", "")).lower() for s in (lock.get("sources") or []) if s.get("family")}
print(len(fams))
PY
)"
  if [ "${present_n}" -lt 2 ]; then
    echo "COMPLETENESS FAIL: min_families<2 硬停（present=${present_n}；不得以降級繞過）" >&2
    return 1
  fi

  if [ ! -f "${degrade_json}" ]; then
    echo "COMPLETENESS FAIL: roster 缺席但無 degrade.json（無合法 DEGRADED_PENDING）" >&2
    return 1
  fi

  if [ ! -f "${synth}" ]; then
    echo "COMPLETENESS FAIL: synth 不存在，無法驗證 DEGRADE 事件: ${synth}" >&2
    return 1
  fi

  # 逐缺席家族：須 ## DEGRADE-<FAM>-01（FAM 大寫）
  local fam up_fam heading
  IFS=',' read -r -a _miss_arr <<< "${missing_csv}"
  for fam in "${_miss_arr[@]}"; do
    [ -z "${fam}" ] && continue
    up_fam="$(printf '%s' "${fam}" | tr '[:lower:]' '[:upper:]')"
    heading="DEGRADE-${up_fam}-01"
    if ! grep -Eiq "^[[:space:]]*#{2,6}[[:space:]]+${heading}[[:space:]]*$" "${synth}"; then
      echo "COMPLETENESS FAIL: 缺席家族 ${fam} 無顯式 ## ${heading}（synth）" >&2
      return 1
    fi
  done

  # degrade.json schema + 與缺席家族對齊 + P0/P1 不得 waiver
  local deg_report
  deg_report="$(python3 - "${degrade_json}" "${missing_csv}" <<'PY'
import json, re, sys
from datetime import datetime

path, missing_csv = sys.argv[1], sys.argv[2]
missing = [m for m in missing_csv.split(",") if m]
try:
    d = json.load(open(path, encoding="utf-8"))
except Exception as e:
    print("BAD_JSON " + str(e))
    sys.exit(0)

required = ["absent_family", "reason", "approver", "expiry", "remediation_owner", "round"]
for k in required:
    if k not in d or d[k] is None or d[k] == "":
        print("MISSING_FIELD " + k)
        sys.exit(0)

# 禁 waived/skip 字串（欄位值）
blob = json.dumps(d, ensure_ascii=False)
if re.search(r"waived\s*:|/skip\b|\bskip\b|ALLOWLIST|ADVISORY_ONLY", blob, re.I):
    print("FORBIDDEN_WAIVER_STRING")
    sys.exit(0)

# P0/P1 不得 waiver：reason/approver 若明示 waiver P0/P1 → 拒
if re.search(r"\bP[01]\b.*waiv|\bwaiv.*\bP[01]\b", blob, re.I):
    print("P0_P1_WAIVER")
    sys.exit(0)

af = str(d.get("absent_family", "")).lower().strip()
if af not in missing:
    print("ABSENT_MISMATCH want_one_of=" + ",".join(missing) + " got=" + af)
    sys.exit(0)

# multi-absent: schema 單數；僅允許恰好一個缺席家族走合法降級
if len(missing) != 1:
    print("MULTI_ABSENT_UNSUPPORTED count=" + str(len(missing)))
    sys.exit(0)

try:
    round_n = int(d["round"])
except Exception:
    print("BAD_ROUND")
    sys.exit(0)
if round_n < 1:
    print("BAD_ROUND")
    sys.exit(0)

expiry = str(d["expiry"])
# BF4: 真 ISO8601 解析；非法格式 / 過期 → FAIL（不可建 DEGRADED_PENDING）
from datetime import datetime, timezone
try:
    exp_s = expiry.strip()
    if exp_s.endswith("Z"):
        exp_dt = datetime.fromisoformat(exp_s[:-1] + "+00:00")
    else:
        exp_dt = datetime.fromisoformat(exp_s)
    if exp_dt.tzinfo is None:
        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
except Exception:
    print("BAD_EXPIRY")
    sys.exit(0)
now = datetime.now(timezone.utc)
if exp_dt < now:
    print("EXPIRED_EXPIRY")
    sys.exit(0)

print("OK round=" + str(round_n) + " family=" + af)
PY
)"

  if echo "${deg_report}" | grep -q '^FORBIDDEN_WAIVER_STRING\|^P0_P1_WAIVER'; then
    echo "COMPLETENESS FAIL: P0/P1 不得 waiver；degrade 禁 waived:/skip 字串（${deg_report}）" >&2
    return 1
  fi
  if ! echo "${deg_report}" | grep -q '^OK '; then
    echo "COMPLETENESS FAIL: degrade.json 非法或不對齊缺席家族: ${deg_report}" >&2
    return 1
  fi

  local round_n
  round_n="$(echo "${deg_report}" | awk '/^OK /{for(i=1;i<=NF;i++) if($i ~ /^round=/){sub(/^round=/,"",$i); print $i}}')"
  if [ -n "${round_n}" ] && [ "${round_n}" -ge 2 ] 2>/dev/null; then
    DEGRADE_ESCALATE=1
    echo "DEGRADE_ESCALATE: family=$(echo "${deg_report}" | awk '{for(i=1;i<=NF;i++) if($i ~ /^family=/){sub(/^family=/,"",$i); print $i}}') round=${round_n}（連續≥2 輪同家族 → 升級使用者/主委端 AskUserQuestion）" >&2
  fi

  DEGRADED_MODE=1
  echo "COMPLETENESS INFO: 合法降級路徑就緒（absent=${missing_csv} present_families=${present_n}）" >&2
  return 0
}

# ---------------------------------------------------------------------------
# _check_roster — roster 缺檔 ∧ 無合法 DEGRADED_PENDING → exit 1
# 合法降級（Task 5.1）→ 置 DEGRADED_MODE=1 後繼續（最終 exit 3）
# 另: 每 roster 家族恰 1 檔；多餘同家族=跨 round 混入(M8)
# ---------------------------------------------------------------------------
_check_roster() {
  local lock_path="$1"
  local synth_for_deg="${2:-}"
  # Python: print missing families and multi-file families; exit code via stdout tags
  local report
  report="$(python3 - "${lock_path}" <<'PY'
import json
import sys
from collections import Counter

lock = json.load(open(sys.argv[1], encoding="utf-8"))
roster_raw = [str(x).lower() for x in lock.get("expected_roster") or []]
sources = lock.get("sources") or []
allow = {"codex", "composer", "grok", "claude", "agy"}

# New-07: expected_roster 本身唯一性 + allowlist（先於 MISSING/degrade）
roster_counts: Counter[str] = Counter(roster_raw)
dups = sorted([f for f, n in roster_counts.items() if n > 1])
if dups:
    print("ROSTER_DUP " + ",".join(f"{f}:{roster_counts[f]}" for f in dups))
unknown_roster = sorted({f for f in roster_raw if f not in allow})
if unknown_roster:
    print("ROSTER_UNKNOWN " + ",".join(unknown_roster))

# 後續 MISSING/MULTI 用去重 roster（dup 已標 ROSTER_DUP 硬拒）
roster = list(dict.fromkeys(roster_raw))
fam_counts: Counter[str] = Counter()
for s in sources:
    fam = str(s.get("family", "")).lower()
    fam_counts[fam] += 1

missing = []
multi = []
for fam in roster:
    n = fam_counts.get(fam, 0)
    if n == 0:
        missing.append(fam)
    elif n > 1:
        multi.append(f"{fam}:{n}")

# sources family not in roster (unknown / extra family)
extras = []
for fam, n in fam_counts.items():
    if fam not in roster:
        extras.append(f"{fam}:{n}")

if missing:
    print("MISSING " + ",".join(missing))
if multi:
    print("MULTI " + ",".join(multi))
if extras:
    print("EXTRA_FAM " + ",".join(extras))
if not roster and not sources:
    print("EMPTY_ROSTER_AND_SOURCES")
# present count for min_families diagnostics
present = [f for f in roster if fam_counts.get(f, 0) == 1]
print("PRESENT_N " + str(len({str(s.get("family","")).lower() for s in sources if s.get("family")})))
PY
)"

  if echo "${report}" | grep -q '^EMPTY_ROSTER_AND_SOURCES'; then
    echo "COMPLETENESS FAIL: empty roster 且無 sources（vacuous 拒收）" >&2
    return 1
  fi
  # New-07: expected_roster 重複 / allowlist 外 → 硬 FAIL（即使有 degrade 事件也不可 rc3 放行）
  if echo "${report}" | grep -q '^ROSTER_DUP '; then
    local rd
    rd="$(echo "${report}" | awk '/^ROSTER_DUP /{print $2}')"
    echo "COMPLETENESS FAIL: expected_roster 含重複家族: ${rd}" >&2
    return 1
  fi
  if echo "${report}" | grep -q '^ROSTER_UNKNOWN '; then
    local ru
    ru="$(echo "${report}" | awk '/^ROSTER_UNKNOWN /{print $2}')"
    echo "COMPLETENESS FAIL: expected_roster 含 allowlist 外家族: ${ru}（允許: codex,composer,grok,claude,agy）" >&2
    return 1
  fi
  # BF2: 合法降級不提前 return；MISSING 通過後仍須跑完整 MULTI/EXTRA_FAM 不變式
  if echo "${report}" | grep -q '^MISSING '; then
    local miss
    miss="$(echo "${report}" | awk '/^MISSING /{print $2}')"
    # Task 5.1：嘗試合法降級；失敗 → 硬 FAIL
    if ! _check_degrade_event "${lock_path}" "${miss}" "${synth_for_deg}"; then
      echo "COMPLETENESS FAIL: roster 缺席家族(無合法 DEGRADED_PENDING): ${miss}" >&2
      return 1
    fi
    # 合法降級就緒（DEGRADED_MODE=1）— 繼續 MULTI/EXTRA_FAM
  fi
  if echo "${report}" | grep -q '^MULTI '; then
    local multi
    multi="$(echo "${report}" | awk '/^MULTI /{print $2}')"
    echo "COMPLETENESS FAIL: 同家族多來源檔(跨 round/混入): ${multi}" >&2
    return 1
  fi
  if echo "${report}" | grep -q '^EXTRA_FAM '; then
    local ex
    ex="$(echo "${report}" | awk '/^EXTRA_FAM /{print $2}')"
    echo "COMPLETENESS FAIL: lock 含 roster 外家族/unknown: ${ex}" >&2
    return 1
  fi
  return 0
}

# ---------------------------------------------------------------------------
# _validate_sources — 拒收 symlink 出目錄/子目錄/root外/late sha/非md/非 *-<family>.md
# 並掃描 sources/ 磁碟：lock 未列之檔 → 拒收(late/污染)
# ---------------------------------------------------------------------------
_validate_sources() {
  local lock_path="$1"
  local overall=0

  if [ ! -d "${SOURCES_ROOT}" ]; then
    echo "COMPLETENESS FAIL: sources/ 目錄不存在: ${SOURCES_ROOT}" >&2
    return 1
  fi

  # Export lock entries as lines: realpath|sha256|family
  local entries
  entries="$(python3 - "${lock_path}" <<'PY'
import json, sys
lock = json.load(open(sys.argv[1], encoding="utf-8"))
for s in sorted(lock.get("sources") or [], key=lambda x: x.get("realpath", "")):
    print("|".join([
        s.get("realpath", ""),
        s.get("sha256", ""),
        str(s.get("family", "")).lower(),
    ]))
PY
)"

  # Build set of lock basenames for disk scan
  local lock_basenames=""
  local line rp sha fam base parent actual resolved entry_path

  while IFS= read -r line; do
    [ -z "${line}" ] && continue
    rp="${line%%|*}"
    rest="${line#*|}"
    sha="${rest%%|*}"
    fam="${rest#*|}"

    if [ -z "${rp}" ] || [ -z "${sha}" ] || [ -z "${fam}" ]; then
      echo "COMPLETENESS FAIL: lock source 欄位不完整: ${line}" >&2
      overall=1
      continue
    fi

    # Resolve path: lock stores realpath; file must exist
    if [ ! -e "${rp}" ]; then
      echo "COMPLETENESS FAIL: lock 列示來源不存在: ${rp}" >&2
      overall=1
      continue
    fi

    # Symlink: realpath 必須仍落在 SOURCES_ROOT 下
    if [ -L "${rp}" ]; then
      resolved="$(cd "$(dirname "${rp}")" && pwd -P)/$(basename "${rp}")"
      # For symlink file, use python realpath
      resolved="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${rp}")"
    else
      resolved="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${rp}")"
    fi

    case "${resolved}" in
      "${SOURCES_ROOT}"/*) ;;
      *)
        echo "COMPLETENESS FAIL: 來源 realpath 出 session sources/（symlink/root外）: ${rp} → ${resolved}" >&2
        overall=1
        continue
        ;;
    esac

    # 禁子目錄: parent 必須恰為 SOURCES_ROOT
    parent="$(dirname "${resolved}")"
    if [ "${parent}" != "${SOURCES_ROOT}" ]; then
      echo "COMPLETENESS FAIL: 來源在子目錄（禁）: ${resolved}" >&2
      overall=1
      continue
    fi

    base="$(basename "${resolved}")"

    # 非 *.md
    case "${base}" in
      *.md) ;;
      *)
        echo "COMPLETENESS FAIL: 非 *.md 來源: ${base}" >&2
        overall=1
        continue
        ;;
    esac

    # 檔名 *-<family>.md 且 family 與 lock.family 一致、在 allowlist
    file_fam="$(python3 -c '
import re,sys
m=re.match(r"^.+-(codex|composer|grok|claude|agy)\.md$", sys.argv[1], re.I)
print(m.group(1).lower() if m else "")
' "${base}")"
    if [ -z "${file_fam}" ]; then
      echo "COMPLETENESS FAIL: 檔名不匹配 *-<family>.md: ${base}" >&2
      overall=1
      continue
    fi
    if [ "${file_fam}" != "${fam}" ]; then
      echo "COMPLETENESS FAIL: lock.family(${fam}) ≠ 檔名家族(${file_fam}): ${base}" >&2
      overall=1
      continue
    fi

    # late: sha ≠ lock
    actual="$(_sha256_file "${resolved}")"
    if [ "${actual}" != "${sha}" ]; then
      echo "COMPLETENESS FAIL: late/竄改（sha≠lock）: ${base} lock=${sha:0:12}… actual=${actual:0:12}…" >&2
      overall=1
      continue
    fi

    lock_basenames="${lock_basenames}${base}"$'\n'
  done <<< "${entries}"

  # 磁碟掃描: sources/ 下任何檔若不在 lock → 拒收（M9 若未入 lock、late 混入）
  local f b
  # include hidden? no — only regular files
  shopt -s nullglob
  for f in "${SOURCES_ROOT}"/* "${SOURCES_ROOT}"/.*; do
    base="$(basename "${f}")"
    [ "${base}" = "." ] || [ "${base}" = ".." ] && continue
    [ -e "${f}" ] || continue
    if [ -d "${f}" ] && [ ! -L "${f}" ]; then
      echo "COMPLETENESS FAIL: sources/ 含子目錄: ${base}" >&2
      overall=1
      continue
    fi
    # skip if not a file-like
    if [ ! -f "${f}" ] && [ ! -L "${f}" ]; then
      continue
    fi
    if ! printf '%s\n' "${lock_basenames}" | grep -qxF "${base}"; then
      echo "COMPLETENESS FAIL: sources/ 出現 lock 未列檔（污染/跨 round/late）: ${base}" >&2
      overall=1
      continue
    fi
  done
  shopt -u nullglob

  # 另: 若 lock 列了檔但 disk 掃描用 realpath basename — 已在上面存在性檢查
  return "${overall}"
}

# ---------------------------------------------------------------------------
# 從 lock 解析來源路徑列表（stdout 每行一 path）
# ---------------------------------------------------------------------------
_lock_source_paths() {
  python3 - "${1}" <<'PY'
import json, sys
lock = json.load(open(sys.argv[1], encoding="utf-8"))
for s in sorted(lock.get("sources") or [], key=lambda x: x.get("realpath", "")):
    print(s.get("realpath", ""))
PY
}

# ---------------------------------------------------------------------------
# ID 層完整性（對 synth + 來源列表）
# ---------------------------------------------------------------------------
_run_id_layer() {
  local synth="$1"
  shift
  # remaining = sources

  local overall=0
  local sources_with_ids=0
  local tmp_cross
  tmp_cross="$(mktemp -t completeness_cross.XXXXXX)"
  trap 'rm -f "${tmp_cross}"' RETURN

  if [ ! -f "${synth}" ]; then
    echo "COMPLETENESS FAIL: 綜合檔不存在: ${synth}" >&2
    return 1
  fi

  local synth_ids_raw=""
  if ! synth_ids_raw="$(extract_heading_ids "${synth}")"; then
    overall=1
    synth_ids_raw=""
  fi
  if ! _validate_finding_body "${synth}"; then
    overall=1
  fi
  if ! _check_same_file_dups "${synth}" "${synth_ids_raw}"; then
    overall=1
  fi
  local synth_ids
  synth_ids="$(printf '%s\n' "${synth_ids_raw}" | sed '/^$/d' | sort -u)"

  local src src_ids_raw src_ids missing n_src n_miss iid
  for src in "$@"; do
    if [ ! -f "${src}" ]; then
      echo "COMPLETENESS FAIL: 來源檔不存在: ${src}" >&2
      overall=1
      continue
    fi

    src_ids_raw=""
    if ! src_ids_raw="$(extract_heading_ids "${src}")"; then
      overall=1
    fi
    if ! _validate_finding_body "${src}"; then
      overall=1
    fi
    if ! _check_same_file_dups "${src}" "${src_ids_raw}"; then
      overall=1
    fi

    src_ids="$(printf '%s\n' "${src_ids_raw}" | sed '/^$/d' | sort -u)"

    if [ -z "${src_ids}" ]; then
      echo "COMPLETENESS WARN: ${src} 抽不到任何 heading ID(來源未用 ## <ID>?) → 本腳本無法保護,須人工/覆議" >&2
      if [ "${STRICT}" = "1" ]; then
        overall=1
      fi
      continue
    fi
    sources_with_ids=$((sources_with_ids + 1))

    while IFS= read -r iid; do
      [ -z "${iid}" ] && continue
      printf '%s\n' "${iid}" >> "${tmp_cross}"
    done <<< "${src_ids}"

    missing="$(comm -23 <(printf '%s\n' "${src_ids}") <(printf '%s\n' "${synth_ids}"))"
    n_src="$(printf '%s\n' "${src_ids}" | grep -c . || true)"
    if [ -n "${missing}" ]; then
      n_miss="$(printf '%s\n' "${missing}" | grep -c . || true)"
      echo "COMPLETENESS FAIL: ${src} — ${n_miss}/${n_src} 個 ID 未出現在綜合檔:"
      while IFS= read -r mid; do
        [ -n "${mid}" ] && printf '  · %s\n' "${mid}"
      done <<< "${missing}"
      overall=1
    else
      echo "COMPLETENESS PASS: ${src} — ${n_src}/${n_src} 個 ID 全在綜合檔。"
    fi
  done

  if [ -s "${tmp_cross}" ]; then
    local cross_dups
    cross_dups="$(sort "${tmp_cross}" | uniq -d)"
    if [ -n "${cross_dups}" ]; then
      echo "COMPLETENESS FAIL: cross-source duplicate ID(s):" >&2
      while IFS= read -r d; do
        [ -n "${d}" ] && printf '  · %s\n' "${d}" >&2
      done <<< "${cross_dups}"
      overall=1
    fi
  fi

  if [ "${sources_with_ids}" -eq 0 ]; then
    echo "COMPLETENESS FAIL: 無任何來源抽出 heading ID(vacuous;可能 prose-only 或未遵守 ## <ID> 慣例)。" >&2
    return 1
  fi

  if [ "${overall}" -ne 0 ]; then
    echo "COMPLETENESS FAIL: 完整性檢查未過(invalid ID / empty shell / 缺 digest / dup / dropped-ID)。補齊後重跑。" >&2
    return 1
  fi
  echo "COMPLETENESS PASS(dropped-ID+schema+lock 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。"
  return 0
}

# ---------------------------------------------------------------------------
# _collect_union_and_missing — stdout JSON line: missing_ids + coverage stats
# （self-check / coverage.json 用；不因漏 ID 而 return≠0）
# ---------------------------------------------------------------------------
_collect_union_and_missing() {
  local synth="$1"
  shift
  python3 - "${synth}" "$@" <<'PY'
import re, sys
from pathlib import Path

HEADING = re.compile(r"^#{2,6}\s+(\S+)")
CANON = re.compile(r"^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$")
DEGRADE = re.compile(r"^DEGRADE-[A-Z]+-[0-9]{2,}$")
FAM = {"CODEX", "COMPOSER", "GROK", "CLAUDE", "AGY"}

def ids_of(path: str) -> set[str]:
    out: set[str] = set()
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        m = re.match(r"^\s*#{2,6}\s+(\S+)", line)
        if not m:
            continue
        tok = m.group(1)
        if DEGRADE.match(tok):
            continue
        if CANON.match(tok) and tok.split("-", 1)[0] in FAM:
            out.add(tok)
    return out

synth = sys.argv[1]
sources = sys.argv[2:]
union: set[str] = set()
for s in sources:
    union |= ids_of(s)
synth_ids = ids_of(synth)
missing = sorted(union - synth_ids)
present = sorted(union & synth_ids)
cov = (len(present) / len(union)) if union else 0.0
import json
print(json.dumps({
    "missing_ids": missing,
    "union_size": len(union),
    "synth_hit": len(present),
    "id_coverage": cov,
}, ensure_ascii=False))
PY
}

# ---------------------------------------------------------------------------
# _write_first_draft_receipt — write-once first_draft.sha256 + coverage.json
# BF1: O_EXCL 原子建檔 + 寫入 rc 檢查（失敗 exit1，不吞成 advisory）
# New-08: coverage.json 同 first_draft.sha256 用 O_EXCL write-once（不可變 receipt 對）
# ---------------------------------------------------------------------------
_write_first_draft_receipt() {
  local sess_dir="$1"
  local synth="$2"
  local coverage_json_blob="$3"   # from _collect_union_and_missing

  local receipt="${sess_dir}/first_draft.sha256"
  local cov_path="${sess_dir}/coverage.json"

  # 快速路徑（非競態保證；O_EXCL 為真 write-once）— 兩檔皆不可變 receipt 對
  if [ -e "${receipt}" ]; then
    echo "COMPLETENESS FAIL: 初稿 receipt 已存在不可回寫（write-once）: ${receipt}" >&2
    return 1
  fi
  if [ -e "${cov_path}" ]; then
    echo "COMPLETENESS FAIL: coverage.json 已存在不可回寫（write-once）: ${cov_path}" >&2
    return 1
  fi
  if [ ! -f "${synth}" ]; then
    echo "COMPLETENESS FAIL: 初稿 synth 不存在: ${synth}" >&2
    return 1
  fi

  local draft_sha
  draft_sha="$(_sha256_file "${synth}")"
  if [ -z "${draft_sha}" ]; then
    echo "COMPLETENESS FAIL: 無法計算 synth sha256: ${synth}" >&2
    return 1
  fi

  # 原子寫入：receipt + coverage 皆 O_EXCL write-once（SPEC L107-110 不可變 receipt 對）
  # rc: 0=ok, 2=write-once 衝突, 1=寫入/IO 失敗
  local py_rc=0
  python3 - "${receipt}" "${cov_path}" "${draft_sha}" "${coverage_json_blob}" <<'PY'
import json
import os
import sys

receipt_path, cov_path, draft_sha, blob = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

try:
    data = json.loads(blob)
except Exception as e:
    print(f"COVERAGE_PARSE_ERROR: {e}", file=sys.stderr)
    sys.exit(1)

out = {
    "missing_ids": data.get("missing_ids") or [],
    "draft_sha256": draft_sha,
    "id_coverage": float(data.get("id_coverage") or 0.0),
}

flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL

def _unlink_quiet(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass

try:
    fd = os.open(receipt_path, flags, 0o644)
except FileExistsError:
    print("RECEIPT_EXISTS", file=sys.stderr)
    sys.exit(2)
except OSError as e:
    print(f"RECEIPT_WRITE_ERROR: {e}", file=sys.stderr)
    sys.exit(1)

try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(draft_sha + "\n")
        f.flush()
        os.fsync(f.fileno())
except Exception as e:
    print(f"RECEIPT_WRITE_ERROR: {e}", file=sys.stderr)
    _unlink_quiet(receipt_path)
    sys.exit(1)

# New-08: coverage.json 同 O_EXCL；pre-existing 不得 os.replace 覆寫
try:
    fd_c = os.open(cov_path, flags, 0o644)
except FileExistsError:
    print("COVERAGE_EXISTS", file=sys.stderr)
    # 半寫：撤銷 receipt，避免 write-once 死鎖
    _unlink_quiet(receipt_path)
    sys.exit(2)
except OSError as e:
    print(f"COVERAGE_WRITE_ERROR: {e}", file=sys.stderr)
    _unlink_quiet(receipt_path)
    sys.exit(1)

try:
    with os.fdopen(fd_c, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
except Exception as e:
    print(f"COVERAGE_WRITE_ERROR: {e}", file=sys.stderr)
    _unlink_quiet(cov_path)
    _unlink_quiet(receipt_path)
    sys.exit(1)

sys.exit(0)
PY
  py_rc=$?
  if [ "${py_rc}" -eq 2 ]; then
    echo "COMPLETENESS FAIL: 初稿 receipt/coverage 已存在不可回寫（write-once）: ${receipt} / ${cov_path}" >&2
    return 1
  fi
  if [ "${py_rc}" -ne 0 ]; then
    echo "COMPLETENESS FAIL: 初稿 receipt/coverage 寫入失敗（rc=${py_rc}；不吞成 advisory）" >&2
    return 1
  fi
  if [ ! -f "${receipt}" ] || [ ! -f "${cov_path}" ]; then
    echo "COMPLETENESS FAIL: 初稿 receipt/coverage 寫入後仍缺檔" >&2
    return 1
  fi
  echo "COMPLETENESS INFO: write-once 初稿 receipt → ${receipt}" >&2
  return 0
}

# ---------------------------------------------------------------------------
# _self_check — Task 4.1：列漏 ID → ADVISORY_MISSING exit0；輸入/執行錯 → exit1
# ---------------------------------------------------------------------------
_self_check() {
  local lock_path="$1"
  local synth="$2"

  _load_lock "${lock_path}"

  if [ -z "${synth}" ]; then
    synth="${SESS_DIR}/synth.md"
  fi

  # 輸入錯誤極性：檔缺 / lock 壞 → exit 1（不吞成 advisory）
  if [ ! -f "${synth}" ]; then
    echo "COMPLETENESS FAIL: self-check 輸入錯誤 — synth 不存在: ${synth}" >&2
    return 1
  fi
  if [ ! -d "${SOURCES_ROOT}" ]; then
    echo "COMPLETENESS FAIL: self-check 輸入錯誤 — sources/ 不存在: ${SOURCES_ROOT}" >&2
    return 1
  fi

  # roster/來源完整性仍硬（缺席家族不是 advisory）
  if ! _check_roster "${LOCK_PATH}" "${synth}"; then
    return 1
  fi
  # 合法降級在 self-check 也不當 PASS 省委員：self-check 遇 DEGRADED_MODE 仍可寫 receipt 但標 INFO
  if ! _validate_sources "${LOCK_PATH}"; then
    return 1
  fi

  SRC_PATHS=()
  while IFS= read -r _sp; do
    [ -n "${_sp}" ] && SRC_PATHS+=("${_sp}")
  done < <(_lock_source_paths "${LOCK_PATH}")
  if [ "${#SRC_PATHS[@]}" -eq 0 ]; then
    echo "COMPLETENESS FAIL: self-check 輸入錯誤 — lock.sources 為空" >&2
    return 1
  fi

  # body/schema 硬錯誤（非法 ID / empty shell）→ exit 1，不當 advisory
  local src
  if ! extract_heading_ids "${synth}" >/dev/null; then
    echo "COMPLETENESS FAIL: self-check — synth ID schema 非法" >&2
    return 1
  fi
  if ! _validate_finding_body "${synth}"; then
    return 1
  fi
  for src in "${SRC_PATHS[@]}"; do
    if [ ! -f "${src}" ]; then
      echo "COMPLETENESS FAIL: self-check 輸入錯誤 — 來源不存在: ${src}" >&2
      return 1
    fi
    if ! extract_heading_ids "${src}" >/dev/null; then
      echo "COMPLETENESS FAIL: self-check — 來源 ID schema 非法: ${src}" >&2
      return 1
    fi
    if ! _validate_finding_body "${src}"; then
      return 1
    fi
  done

  local cov_blob
  cov_blob="$(_collect_union_and_missing "${synth}" "${SRC_PATHS[@]}")" || {
    echo "COMPLETENESS FAIL: self-check 無法計算 coverage" >&2
    return 1
  }

  if ! _write_first_draft_receipt "${SESS_DIR}" "${synth}" "${cov_blob}"; then
    return 1
  fi

  # BF5: 合法降級不得 rc0 灰態掩蓋 — 標 DEGRADED_PENDING 並 return 3
  if [ "${DEGRADED_MODE}" = "1" ]; then
    echo "DEGRADED_PENDING"
    echo "COMPLETENESS INFO: self-check 合法降級（DEGRADED_PENDING；不得當 advisory PASS）" >&2
    if [ "${DEGRADE_ESCALATE}" = "1" ]; then
      echo "COMPLETENESS INFO: DEGRADED_PENDING + ESCALATE（round≥2）" >&2
    fi
    return 3
  fi

  local missing_n
  missing_n="$(python3 -c 'import json,sys; print(len(json.loads(sys.argv[1]).get("missing_ids") or []))' "${cov_blob}")"
  if [ "${missing_n}" -gt 0 ]; then
    echo "ADVISORY_MISSING"
    python3 -c '
import json,sys
d=json.loads(sys.argv[1])
for mid in d.get("missing_ids") or []:
    print("  · " + mid)
print("id_coverage=%.4f" % float(d.get("id_coverage") or 0.0))
' "${cov_blob}"
    echo "COMPLETENESS ADVISORY: self-check 列漏 ID（不阻塞；最終稿須獨立出口重跑）" >&2
    return 0
  fi

  echo "COMPLETENESS ADVISORY: self-check 無漏 ID（仍不得跳過委員語意審；receipt 已 write-once）"
  return 0
}

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
LOCK_ARG=""
SYNTH_ARG=""
SELF_CHECK=0
POSITIONAL=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --lock)
      [ "$#" -ge 2 ] || { echo "用法: --lock <path>" >&2; exit 2; }
      LOCK_ARG="$2"
      shift 2
      ;;
    --synth)
      [ "$#" -ge 2 ] || { echo "用法: --synth <path>" >&2; exit 2; }
      SYNTH_ARG="$2"
      shift 2
      ;;
    --self-check)
      SELF_CHECK=1
      shift
      ;;
    --)
      shift
      while [ "$#" -gt 0 ]; do POSITIONAL+=("$1"); shift; done
      break
      ;;
    # 反 bypass：明確拒任何 skip/waiver 類選項（不新增逃生口）
    --skip|--skip-completeness|--advisory-only)
      echo "COMPLETENESS FAIL: 禁 --skip/--skip-completeness/--advisory-only 逃生口" >&2
      exit 1
      ;;
    -*)
      echo "COMPLETENESS FAIL: 未知選項: $1" >&2
      exit 1
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

if [ -n "${LOCK_ARG}" ]; then
  # ---- 正式 lock 路徑：禁 argv 來源覆寫 ----
  if [ "${#POSITIONAL[@]}" -gt 0 ]; then
    echo "COMPLETENESS FAIL: 正式 --lock 入口禁 argv 來源覆寫（收到 ${#POSITIONAL[@]} 個多餘參數）" >&2
    exit 1
  fi
  # 禁 env 覆寫來源清單
  if [ -n "${COMPLETENESS_SOURCES_OVERRIDE:-}" ]; then
    echo "COMPLETENESS FAIL: COMPLETENESS_SOURCES_OVERRIDE 禁用（來源只讀 lock）" >&2
    exit 1
  fi

  if [ "${SELF_CHECK}" = "1" ]; then
    _load_lock "${LOCK_ARG}"  # warm SESS_DIR for default synth（_self_check 內會再 load）
    if [ -z "${SYNTH_ARG}" ]; then
      SYNTH_ARG="${SESS_DIR}/synth.md"
    fi
    # BF5: 傳播 return 3（DEGRADED_PENDING），勿把非 0 一律壓成 exit 1 / 勿 exit 0 掩蓋
    _self_check "${LOCK_PATH}" "${SYNTH_ARG}"
    sc_rc=$?
    if [ "${sc_rc}" -eq 3 ]; then
      exit 3
    fi
    if [ "${sc_rc}" -ne 0 ]; then
      exit 1
    fi
    exit 0
  fi

  _load_lock "${LOCK_ARG}"

  if [ -z "${SYNTH_ARG}" ]; then
    SYNTH_ARG="${SESS_DIR}/synth.md"
  fi

  if ! _check_roster "${LOCK_PATH}" "${SYNTH_ARG}"; then
    exit 1
  fi
  if ! _validate_sources "${LOCK_PATH}"; then
    exit 1
  fi

  # 來源路徑只從 lock 讀（bash 3.2：不用 mapfile）
  SRC_PATHS=()
  while IFS= read -r _sp; do
    [ -n "${_sp}" ] && SRC_PATHS+=("${_sp}")
  done < <(_lock_source_paths "${LOCK_PATH}")
  if [ "${#SRC_PATHS[@]}" -eq 0 ]; then
    echo "COMPLETENESS FAIL: lock.sources 為空（非 vacuous PASS）" >&2
    exit 1
  fi

  # Task 5.1 + BF3: 合法降級 → ID 層細節走 stderr；stdout 唯一 DEGRADED_PENDING
  if [ "${DEGRADED_MODE}" = "1" ]; then
    if ! _run_id_layer "${SYNTH_ARG}" "${SRC_PATHS[@]}" >&2; then
      exit 1
    fi
    # 主輸出乾淨：僅一行 token（不與 COMPLETENESS PASS 混）
    printf '%s\n' "DEGRADED_PENDING"
    if [ "${DEGRADE_ESCALATE}" = "1" ]; then
      echo "COMPLETENESS INFO: DEGRADED_PENDING + ESCALATE（round≥2）" >&2
    fi
    exit 3
  fi

  if ! _run_id_layer "${SYNTH_ARG}" "${SRC_PATHS[@]}"; then
    exit 1
  fi
  exit 0
fi

# ---- 非 lock：僅測試隔離允許 argv ----
if [ "${SELF_CHECK}" = "1" ]; then
  echo "COMPLETENESS FAIL: --self-check 必須搭配 --lock <sources.lock>" >&2
  exit 1
fi

if [ "${COMPLETENESS_ALLOW_ARGV_SOURCES:-}" != "1" ]; then
  echo "COMPLETENESS FAIL: 正式入口必須 --lock <sources.lock>（argv 來源僅 tests 隔離 COMPLETENESS_ALLOW_ARGV_SOURCES=1）" >&2
  exit 1
fi

if [ "${#POSITIONAL[@]}" -lt 2 ]; then
  echo "用法: bash scripts/completeness_check.sh --lock <sources.lock> [--synth path] [--self-check]" >&2
  echo "  或: COMPLETENESS_ALLOW_ARGV_SOURCES=1 bash scripts/completeness_check.sh <綜合檔> <來源...>" >&2
  exit 2
fi

SYNTH="${POSITIONAL[0]}"
SRC_ARGS=("${POSITIONAL[@]:1}")
if ! _run_id_layer "${SYNTH}" "${SRC_ARGS[@]}"; then
  exit 1
fi
exit 0
