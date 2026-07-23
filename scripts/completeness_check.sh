#!/usr/bin/env bash
# completeness_check.sh — 綜合(reconcile/UNION)完整性機械檢查
#
# 病灶(2026-07-22 IC reconcile 手抄事故):Claude 手抄合併多方委員產物 → 靜默掉項。
# 方法:委員產物用 canonical finding ID(見下);本腳本機械抽每個來源檔的 ID,
#   檢查是否**全部**出現在綜合檔。缺任一 → FAIL。把「靜默掉項」變「機器擋下」。
#
# 用法:
#   bash scripts/completeness_check.sh <綜合檔> <來源檔1> [來源檔2 ...]
#   STRICT=1          → 來源無 ID 時 FAIL(預設 1; STRICT=0 才 WARN+續跑)。
#   ALLOW_BARE_IDS=1  → 除錯用(B2 後仍拒非 canonical;保留旗標相容,正式路徑禁)。
#   ALLOW_ID_PATTERN_OVERRIDE=1 + ID_PATTERN=... → 除錯覆寫(gate/CI 禁止)。
#
# B2 (Task 2.1) 升級:
#   - canonical ID: ^([A-Z]+)-(R[0-9]+)-(P[0-3])-([0-9]{2,})$
#   - FAMILY allowlist: CODEX|COMPOSER|GROK|CLAUDE|AGY
#   - body 機檢: 每 ## ID 後須同時含 **斷言** 與 **碼證**
#   - P0/P1 須 **來源摘要**: path#sha256[:12] 或 harness source_digest:
#   - DEGRADE-* 第二命名空間:不進 union、不當 invalid
#   - 同檔/跨源 duplicate ID → FAIL
#   - severity 全級(P0-P3) missing → FAIL(只排序不免檢)
#
# 誠實邊界:
#   ✅ 擋:dropped-ID / invalid ID / empty shell / 缺 digest(P0/P1) / dup ID
#   ❌ 不擋:語意降級、錯併、argv 縮減來源(B3 lock)、body 竄改但 digest 對(M4b OOS)
set -u

SYNTH="${1:-}"
shift || true
[ -n "${SYNTH}" ] || { echo "用法: bash scripts/completeness_check.sh <綜合檔> <來源檔...>"; exit 2; }
[ -f "${SYNTH}" ] || { echo "COMPLETENESS FAIL: 綜合檔不存在: ${SYNTH}"; exit 2; }
[ "$#" -ge 1 ] || { echo "用法: 至少一個來源檔"; exit 2; }

STRICT="${STRICT:-1}"
ALLOW_BARE_IDS="${ALLOW_BARE_IDS:-0}"

# 至少 ## (h2+)。單一 # 會把 markdown 註解誤當 heading。
HEADING_LINE_RE='^[[:space:]]*#{2,6}[[:space:]][[:space:]]*'

# B2 canonical: FAM-Rn-Pn-NN
CANONICAL_ID_RE='^([A-Z]+)-(R[0-9]+)-(P[0-3])-([0-9]{2,})$'
# FAMILY allowlist (exact)
FAMILY_ALLOW_RE='^(CODEX|COMPOSER|GROK|CLAUDE|AGY)$'
# DEGRADE 第二命名空間(整行 heading;不進 union、不當 invalid)
DEGRADE_HEADING_RE='^[[:space:]]*#{2,6}[[:space:]]+DEGRADE-[A-Z]+-[0-9]{2,}[[:space:]]*$'
DEGRADE_TOKEN_RE='^DEGRADE-[A-Z]+-[0-9]{2,}$'
# 看起來像 finding ID 候選(有 hyphen 段)但未過 full schema → invalid
CANDIDATE_ID_RE='^[A-Z]+(-[A-Z0-9]+)+$'

if [ -n "${ID_PATTERN:-}" ]; then
  if [ "${ALLOW_ID_PATTERN_OVERRIDE:-}" != "1" ]; then
    echo "COMPLETENESS FAIL: ID_PATTERN 覆寫已禁用(紅隊 F-c/A6)。除錯請設 ALLOW_ID_PATTERN_OVERRIDE=1, gate/CI 禁止。"
    exit 1
  fi
  USE_PATTERN_OVERRIDE=1
else
  USE_PATTERN_OVERRIDE=0
fi

# ---------------------------------------------------------------------------
# extract_heading_ids — 輸出合法 canonical ID(每行一個;保留同檔重複以便 dup 偵測)
# 副作用: 發現 invalid candidate → 印 stderr 並 return 1
# DEGRADE-* 排除(不進 union、不當 invalid)
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
      # family allowlist
      fam["CODEX"]=1; fam["COMPOSER"]=1; fam["GROK"]=1; fam["CLAUDE"]=1; fam["AGY"]=1
    }
    # DEGRADE 整行 heading → skip entirely
    /^[[:space:]]*#{2,6}[[:space:]]+DEGRADE-[A-Z]+-[0-9]{2,}[[:space:]]*$/ { next }
    # h2+ heading
    /^[[:space:]]*#{2,6}[[:space:]]/ {
      line=$0
      sub(/^[[:space:]]*#{2,6}[[:space:]]+/, "", line)
      # anchored:trim 尾空白後,整行須完全等於 canonical/DEGRADE(拒尾隨文字/尾標點, CODEX-B2-P1-01)
      sub(/[[:space:]]+$/, "", line)
      if (line == "") next
      # DEGRADE full-line (anchored)
      if (line ~ /^DEGRADE-[A-Z]+-[0-9]{2,}$/) next
      # full canonical FAM-Rn-Pn-NN(整行 anchored)
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
      # 非整行匹配:取首 token 判是否「像 ID」(含 canonical+尾隨文字、缺欄變體 M5)→ invalid
      n=split(line, parts, /[[:space:]]+/)
      tok=parts[1]
      sub(/[^A-Za-z0-9_-].*$/, "", tok)
      if (tok ~ /^[A-Z]+(-[A-Z0-9]+)+$/) {
        print "COMPLETENESS FAIL: invalid finding ID (schema/trailing): " line " (file=" FILENAME ")" > "/dev/stderr"
        bad=1
        next
      }
      # prose heading → ignore
      next
    }
    END { if (bad) exit 1 }
  ' "${file}"
  rc=$?
  return "${rc}"
}

# ---------------------------------------------------------------------------
# _validate_finding_body — 每 ## canonical ID 後至下個 heading 須同時含 **斷言**+**碼證**
# P0/P1 另須 digest(**來源摘要**: ...#sha12 或 source_digest:)
# ---------------------------------------------------------------------------
_validate_finding_body() {
  local file="$1"
  # shellcheck disable=SC2016
  awk '
    BEGIN {
      id=""; sev=""; seen_assert=0; seen_code=0; seen_digest=0; bad=0
    }
    function flush(    need_digest) {
      if (id == "") return
      if (!(seen_assert && seen_code)) {
        print "COMPLETENESS FAIL: empty-shell finding (缺 **斷言**/**碼證**): " id " (file=" FILENAME ")" > "/dev/stderr"
        bad=1
      }
      # P0/P1 require digest
      if (sev == "P0" || sev == "P1") {
        if (!seen_digest) {
          print "COMPLETENESS FAIL: P0/P1 missing source digest (**來源摘要** or source_digest:): " id " (file=" FILENAME ")" > "/dev/stderr"
          bad=1
        }
      }
    }
    # next heading of interest (canonical or any ##)
    /^[[:space:]]*#{2,6}[[:space:]]/ {
      # DEGRADE headings: flush previous finding, do not start new finding body
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
        # extract severity Pn
        split(tok, segs, "-")
        sev=segs[3]
        seen_assert=0; seen_code=0; seen_digest=0
        next
      }
      # other heading ends previous finding body
      if (id != "") {
        flush()
        id=""; sev=""; seen_assert=0; seen_code=0; seen_digest=0
      }
      next
    }
    id != "" {
      if ($0 ~ /\*\*斷言\*\*/) seen_assert=1
      if ($0 ~ /\*\*碼證\*\*/) seen_code=1
      # **來源摘要**: path#sha256[:12]
      if ($0 ~ /\*\*來源摘要\*\*/ && $0 ~ /#[0-9a-fA-F]{12}/) seen_digest=1
      # harness injection
      if ($0 ~ /source_digest:[[:space:]]*[0-9a-fA-F]{12,}/) seen_digest=1
    }
    END {
      flush()
      if (bad) exit 1
    }
  ' "${file}"
}

# ---------------------------------------------------------------------------
# _check_same_file_dups — 同檔重複 ID → FAIL
# ---------------------------------------------------------------------------
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
# Main
# ---------------------------------------------------------------------------
overall=0
sources_with_ids=0

# Accumulate valid IDs across sources for cross-source dup (id -> count of files)
# Use temp files for portability
tmp_union="$(mktemp -t completeness_union.XXXXXX)"
tmp_cross="$(mktemp -t completeness_cross.XXXXXX)"
trap 'rm -f "${tmp_union}" "${tmp_cross}"' EXIT

# Validate + extract synth first
if ! synth_ids_raw="$(extract_heading_ids "${SYNTH}")"; then
  overall=1
  synth_ids_raw=""
fi
if ! _validate_finding_body "${SYNTH}"; then
  overall=1
fi
if ! _check_same_file_dups "${SYNTH}" "${synth_ids_raw}"; then
  overall=1
fi
# unique sorted for comm
synth_ids="$(printf '%s\n' "${synth_ids_raw}" | sed '/^$/d' | sort -u)"

for src in "$@"; do
  if [ ! -f "${src}" ]; then
    echo "COMPLETENESS FAIL: 來源檔不存在: ${src}"
    overall=1
    continue
  fi

  src_ids_raw=""
  if ! src_ids_raw="$(extract_heading_ids "${src}")"; then
    overall=1
    # still try body? skip if invalid IDs already fail
  fi

  if ! _validate_finding_body "${src}"; then
    overall=1
  fi

  if ! _check_same_file_dups "${src}" "${src_ids_raw}"; then
    overall=1
  fi

  src_ids="$(printf '%s\n' "${src_ids_raw}" | sed '/^$/d' | sort -u)"

  if [ -z "${src_ids}" ]; then
    echo "COMPLETENESS WARN: ${src} 抽不到任何 heading ID(來源未用 ## <ID>?) → 本腳本無法保護,須人工/覆議"
    if [ "${STRICT}" = "1" ]; then
      overall=1
    fi
    continue
  fi
  sources_with_ids=$((sources_with_ids + 1))

  # cross-source: record each unique id once per file
  while IFS= read -r iid; do
    [ -z "${iid}" ] && continue
    printf '%s\n' "${iid}" >> "${tmp_cross}"
  done <<< "${src_ids}"

  # dropped-ID: source IDs must appear in synth (all severities P0-P3; 只排序不免檢)
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

# cross-source duplicate IDs (same ID in ≥2 source files)
if [ -s "${tmp_cross}" ]; then
  cross_dups="$(sort "${tmp_cross}" | uniq -d)"
  if [ -n "${cross_dups}" ]; then
    echo "COMPLETENESS FAIL: cross-source duplicate ID(s):" >&2
    while IFS= read -r d; do
      [ -n "${d}" ] && printf '  · %s\n' "${d}" >&2
    done <<< "${cross_dups}"
    overall=1
  fi
fi

# 全滅 vacuous PASS
if [ "${sources_with_ids}" -eq 0 ]; then
  echo "COMPLETENESS FAIL: 無任何來源抽出 heading ID(vacuous;可能 prose-only 或未遵守 ## <ID> 慣例)。"
  exit 1
fi

if [ "${overall}" -ne 0 ]; then
  echo "COMPLETENESS FAIL: 完整性檢查未過(invalid ID / empty shell / 缺 digest / dup / dropped-ID)。補齊後重跑。"
  exit 1
fi
echo "COMPLETENESS PASS(dropped-ID+schema 層): 全來源 heading ID 皆在綜合且 body/digest 合法。注意:仍不保證語意忠實/無錯併/來源清單完整(須委員覆議+dispatch 注入來源)。"
exit 0
