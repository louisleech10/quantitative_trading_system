#!/usr/bin/env bash
# GOVB1 Task 4.1（`票 B-38`）— findings-kind 產出的機械分類判準。
#
# 目標：回答「**哪一份產出應該要有 findings**」，而且是**可證偽**地回答。
#   在此之前這個判斷散在人的腦袋裡：零 findings 的輪次到底是「本來就不該有」
#   還是「該有而漏了」，沒有機械判準 ⇒ 只能靠 `--abandon` 逃生口，
#   而那個逃生口不查核事實（`票 B-48`）。
#
# 🔴 本 Task **只產判準，不改判**：任何既有入口（completeness_check.sh --single／--lock、
#   cx_run.sh 交件路徑）的 rc 與 result_state 一律不得因本檔存在而改變。
#   機械看守＝tests/governance/test_govb1_zeroid_no_regression.py（三入口 × 三輸入矩陣）。
#   本檔**沒有任何 caller**（Task 4.2 才接）。
#
# 判準（單一真相源＝scripts/govflow_lifecycle.json，🔴 禁在本檔硬編 kind 白名單或 fallback）：
#   1. 取檔內第一行 `^brief-kind:` 的值
#   2. 沒有該行 ⇒ `unknown`（**不猜**；SPEC 邊界 ③）
#   3. 有 ⇒ 查 SoT 的 .kinds[<kind>].produces_findings
#        true → findings ／ false → non-findings ／ 缺鍵或非布林 → unknown
#
# 🔴 SoT 欄位名為 `produces_findings`。凍結 TODO:1068 的偽碼寫 `is_findings_kind`，
#   該鍵在 SoT 中**不存在**（實測 `jq 'keys'`）；逐字照抄會使全語料判為 unknown。
#   偏離與實測見 docs/GOV_B8_SCOPE_AMENDMENT.md §2。
#
# 用法：
#   bash scripts/findings_kind_classify.sh --single <file>
#   bash scripts/findings_kind_classify.sh --audit --corpus <dir>
#   bash scripts/findings_kind_classify.sh --sample --corpus <dir> --n <N> [--seed <S>]
#   bash scripts/findings_kind_classify.sh --wilson --fp <k> --n <n>
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
LIFECYCLE="${FINDINGS_KIND_LIFECYCLE:-${SCRIPT_DIR}/govflow_lifecycle.json}"

_die() { echo "FINDINGS-KIND FAIL: $*" >&2; exit 2; }

_require_deps() {
  command -v jq >/dev/null 2>&1 || _die "缺 jq（fail-closed，不猜判準）"
  [ -f "${LIFECYCLE}" ] || _die "SoT 不存在: ${LIFECYCLE}"
  jq -e '.kinds | type == "object"' "${LIFECYCLE}" >/dev/null 2>&1 \
    || _die "SoT 無 .kinds 物件（fail-closed）: ${LIFECYCLE}"
}

# $1=file → stdout: findings|non-findings|unknown
classify() {
  local f="${1-}" bk v
  [ -f "${f}" ] || { echo "unknown"; return 0; }
  bk="$(grep -m1 '^brief-kind:' "${f}" 2>/dev/null | awk '{print $2}')"
  if [ -z "${bk}" ]; then
    echo "unknown"          # SPEC 邊界 ③：無宣告 ⇒ 不猜
    return 0
  fi
  # 🔴 **不得**用 `.kinds[$k].produces_findings // "unknown"`（凍結 TODO:1068 偽碼的寫法）：
  #   jq 的 `//` 把 **false 視同空值**，故 `false // "unknown"` 回傳 "unknown"
  #   ⇒ 所有 produces_findings=false 的 kind（impl／stamp）會被**靜默誤判為 unknown**。
  #   實測：`jq -n 'false // "u"'` → "u"。改用 has() ＋ 型別檢查，缺鍵或非布林才落 unknown。
  v="$(LC_ALL=C jq -r --arg k "${bk}" '
        (.kinds[$k] // {}) as $e
        | if ($e | has("produces_findings")) and (($e.produces_findings | type) == "boolean")
          then ($e.produces_findings | tostring)
          else "unknown"
          end' "${LIFECYCLE}" 2>/dev/null)" \
    || v="unknown"
  case "${v}" in
    true)  echo "findings" ;;
    false) echo "non-findings" ;;
    *)     echo "unknown" ;;
  esac
}

# $1=file → stdout: brief-kind 值（無則 "-"）
_brief_kind_of() {
  local bk
  bk="$(grep -m1 '^brief-kind:' "${1-}" 2>/dev/null | awk '{print $2}')"
  [ -n "${bk}" ] && printf '%s\n' "${bk}" || printf '%s\n' "-"
}

# 決定性抽樣：djb2 雜湊路徑後排序取前 N。
# 🔴 不用 shuf／$RANDOM —— 抽樣必須可重現，否則誤擋率 receipt 無法被複驗。
# 🔴 也不用「檔名排序取前 N」—— 檔名帶日期與 session，前綴排序會系統性偏向早期輪次。
_sample_paths() {   # $1=dir $2=N $3=seed
  find "${1}" -maxdepth 1 -type f -name '*.md' 2>/dev/null \
  | LC_ALL=C sort \
  | LC_ALL=C awk -v n="${2}" -v seed="${3}" '
      BEGIN { for (i = 0; i < 256; i++) ord[sprintf("%c", i)] = i }
      function h(s,   i, v) {
        v = 5381 + seed
        for (i = 1; i <= length(s); i++) v = (v * 33 + ord[substr(s, i, 1)]) % 4294967291
        return v
      }
      { printf "%012d\t%s\n", h($0), $0 }
    ' \
  | LC_ALL=C sort -k1,1 -k2,2 \
  | head -n "${2}" \
  | cut -f2
}

# Wilson 95% CI（z=1.96）。$1=成功數(FP 數) $2=樣本數 → stdout: "low high"
_wilson() {
  LC_ALL=C awk -v k="${1}" -v n="${2}" 'BEGIN {
    if (n <= 0) { print "NaN NaN"; exit 1 }
    z = 1.96; z2 = z * z
    p = k / n
    den = 1 + z2 / n
    ctr = p + z2 / (2 * n)
    rad = z * sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    lo = (ctr - rad) / den; hi = (ctr + rad) / den
    if (lo < 0) lo = 0
    if (hi > 1) hi = 1
    printf "%.4f %.4f\n", lo * 100, hi * 100
  }'
}

MODE=""; CORPUS=""; SINGLE=""; N=""; SEED="0"; FP=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --single)  MODE="single"; SINGLE="${2-}"; shift 2 ;;
    --audit)   MODE="audit"; shift ;;
    --sample)  MODE="sample"; shift ;;
    --wilson)  MODE="wilson"; shift ;;
    --corpus)  CORPUS="${2-}"; shift 2 ;;
    --n)       N="${2-}"; shift 2 ;;
    --seed)    SEED="${2-}"; shift 2 ;;
    --fp)      FP="${2-}"; shift 2 ;;
    *) _die "未知參數: $1" ;;
  esac
done

_require_deps

case "${MODE}" in
  single)
    [ -n "${SINGLE}" ] || _die "--single 需要檔案路徑"
    classify "${SINGLE}"
    ;;

  audit)
    [ -n "${CORPUS}" ] || _die "--audit 需要 --corpus <dir>"
    [ -d "${CORPUS}" ] || _die "corpus 不是目錄: ${CORPUS}"
    # 🔴 逐檔開 grep/awk/jq 在 ~3000 檔語料上要開近萬個 process ⇒ 分鐘級。
    #   改成三段式：①SoT 映射算一次 ②整批 grep 一次 ③awk join。
    #   語意與 classify() 完全一致（同一 SoT、同一「無宣告即 unknown」規則），
    #   一致性由 test_audit_agrees_with_single 逐檔比對釘死。
    _tmp="$(mktemp -t fkc.XXXXXX)" || _die "mktemp 失敗"
    _map="$(mktemp -t fkcmap.XXXXXX)" || _die "mktemp 失敗"
    _files="$(mktemp -t fkcf.XXXXXX)" || _die "mktemp 失敗"
    LC_ALL=C jq -r '
      .kinds | to_entries[]
      | .key as $k
      | .value as $e
      | if ($e | has("produces_findings")) and (($e.produces_findings | type) == "boolean")
        then "\($k)\t\(if $e.produces_findings then "findings" else "non-findings" end)"
        else "\($k)\tunknown"
        end' "${LIFECYCLE}" > "${_map}" 2>/dev/null \
      || _die "SoT kind 映射導出失敗"
    find "${CORPUS}" -maxdepth 1 -type f -name '*.md' 2>/dev/null | LC_ALL=C sort > "${_files}"
    _total="$(grep -c '' "${_files}" 2>/dev/null || echo 0)"
    if [ "${_total}" -gt 0 ]; then
      LC_ALL=C awk -v mapf="${_map}" '
        BEGIN { while ((getline line < mapf) > 0) { split(line, m, "\t"); cls[m[1]] = m[2] } }
        {
          path = $0; k = ""
          # 與 classify() 同語意：取第一行 ^brief-kind: 的第一個空白分隔欄位
          while ((getline l < path) > 0) {
            if (l ~ /^brief-kind:/) {
              k = l
              sub(/^brief-kind:[[:space:]]*/, "", k)
              sub(/[[:space:]].*$/, "", k)
              break
            }
          }
          close(path)
          if (k == "") { print "-\tunknown"; next }
          print k "\t" ((k in cls) ? cls[k] : "unknown")
        }' "${_files}" > "${_tmp}"
    fi
    echo "# findings-kind 分類矩陣"
    echo "# corpus=${CORPUS}  SoT=${LIFECYCLE}"
    echo "# 分母（實際掃描檔數，現跑導出）=${_total}"
    echo
    printf '%-14s %-14s %s\n' "brief-kind" "分類" "檔數"
    LC_ALL=C sort "${_tmp}" | LC_ALL=C uniq -c \
      | LC_ALL=C awk '{ c = $1; bk = $2; cl = $3; printf "%-14s %-14s %d\n", bk, cl, c }'
    echo
    echo "# 分類小計"
    LC_ALL=C awk -F'\t' '{ c[$2]++ } END { for (k in c) printf "%-14s %d\n", k, c[k] }' "${_tmp}" \
      | LC_ALL=C sort
    mv "${_tmp}" "${_tmp}.done" 2>/dev/null || true
    ;;

  sample)
    [ -n "${CORPUS}" ] || _die "--sample 需要 --corpus <dir>"
    [ -d "${CORPUS}" ] || _die "corpus 不是目錄: ${CORPUS}"
    [ -n "${N}" ] || _die "--sample 需要 --n <N>"
    case "${N}" in ''|*[!0-9]*) _die "--n 須為正整數: ${N}" ;; esac
    [ "${N}" -ge 1 ] || _die "--n 須 ≥1"
    _sample_paths "${CORPUS}" "${N}" "${SEED}" | while IFS= read -r f; do
      [ -n "${f}" ] || continue
      printf '%s\t%s\t%s\n' "$(_brief_kind_of "${f}")" "$(classify "${f}")" "${f}"
    done
    ;;

  wilson)
    [ -n "${FP}" ] || _die "--wilson 需要 --fp <k>"
    [ -n "${N}" ] || _die "--wilson 需要 --n <n>"
    case "${FP}" in ''|*[!0-9]*) _die "--fp 須為非負整數: ${FP}" ;; esac
    case "${N}" in ''|*[!0-9]*) _die "--n 須為正整數: ${N}" ;; esac
    [ "${N}" -ge 1 ] || _die "--n 須 ≥1"
    [ "${FP}" -le "${N}" ] || _die "--fp 不得大於 --n"
    set -- $(_wilson "${FP}" "${N}")
    # 🔴 §V-FP：報區間不報點估計。禁寫「誤擋率 0%」。
    printf 'fp=%s n=%s  Wilson 95%% CI = [%s%%, %s%%]\n' "${FP}" "${N}" "${1}" "${2}"
    ;;

  *)
    _die "須指定 --single / --audit / --sample / --wilson 之一"
    ;;
esac
