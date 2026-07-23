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
#
# exit: 0=PASS; 1=FAIL/非法; 3=DEGRADED_PENDING(B4;本檔 B3 不產)
set -u

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
# _check_roster — roster 缺檔 ∧ 無合法 DEGRADED_PENDING → exit 1（B3 無 degrade 第三態）
# 另: 每 roster 家族恰 1 檔；多餘同家族=跨 round 混入(M8)
# ---------------------------------------------------------------------------
_check_roster() {
  local lock_path="$1"
  # Python: print missing families and multi-file families; exit code via stdout tags
  local report
  report="$(python3 - "${lock_path}" <<'PY'
import json
import sys
from collections import Counter

lock = json.load(open(sys.argv[1], encoding="utf-8"))
roster = [str(x).lower() for x in lock.get("expected_roster") or []]
sources = lock.get("sources") or []
fam_counts: Counter[str] = Counter()
for s in sources:
    fam = str(s.get("family", "")).lower()
    fam_counts[fam] += 1

allow = {"codex", "composer", "grok", "claude", "agy"}
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
PY
)"

  if echo "${report}" | grep -q '^EMPTY_ROSTER_AND_SOURCES'; then
    echo "COMPLETENESS FAIL: empty roster 且無 sources（vacuous 拒收）" >&2
    return 1
  fi
  if echo "${report}" | grep -q '^MISSING '; then
    local miss
    miss="$(echo "${report}" | awk '/^MISSING /{print $2}')"
    # B3: 無合法 DEGRADED_PENDING 路徑 → 硬 FAIL（degrade 屬 B4/Task5.1）
    echo "COMPLETENESS FAIL: roster 缺席家族(無合法 DEGRADED_PENDING): ${miss}" >&2
    return 1
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
# CLI
# ---------------------------------------------------------------------------
LOCK_ARG=""
SYNTH_ARG=""
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
    --)
      shift
      while [ "$#" -gt 0 ]; do POSITIONAL+=("$1"); shift; done
      break
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

  _load_lock "${LOCK_ARG}"

  if [ -z "${SYNTH_ARG}" ]; then
    SYNTH_ARG="${SESS_DIR}/synth.md"
  fi

  if ! _check_roster "${LOCK_PATH}"; then
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

  if ! _run_id_layer "${SYNTH_ARG}" "${SRC_PATHS[@]}"; then
    exit 1
  fi
  exit 0
fi

# ---- 非 lock：僅測試隔離允許 argv ----
if [ "${COMPLETENESS_ALLOW_ARGV_SOURCES:-}" != "1" ]; then
  echo "COMPLETENESS FAIL: 正式入口必須 --lock <sources.lock>（argv 來源僅 tests 隔離 COMPLETENESS_ALLOW_ARGV_SOURCES=1）" >&2
  exit 1
fi

if [ "${#POSITIONAL[@]}" -lt 2 ]; then
  echo "用法: bash scripts/completeness_check.sh --lock <sources.lock> [--synth path]" >&2
  echo "  或: COMPLETENESS_ALLOW_ARGV_SOURCES=1 bash scripts/completeness_check.sh <綜合檔> <來源...>" >&2
  exit 2
fi

SYNTH="${POSITIONAL[0]}"
SRC_ARGS=("${POSITIONAL[@]:1}")
if ! _run_id_layer "${SYNTH}" "${SRC_ARGS[@]}"; then
  exit 1
fi
exit 0
