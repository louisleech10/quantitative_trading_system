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
  # 🔴 `.kinds` 是空物件也要擋〔CODEX-R1-P1-02〕：`{"kinds":{}}` 過得了 type 檢查，
  #   然後每個檔都靜默回 unknown rc=0 —— 那是「看起來有判準、其實沒有」。
  jq -e '(.kinds | type == "object") and ((.kinds | length) > 0)' "${LIFECYCLE}" >/dev/null 2>&1 \
    || _die "SoT 無非空 .kinds 物件（fail-closed）: ${LIFECYCLE}"
}

# $1=file → stdout: 該檔自帶的 brief-kind 值（無則空字串）
# 🔴 尾端 CR 必須剝除〔CODEX-R1-P1-02〕：`brief-kind: review\r\n` 在
#   shell 路徑 `awk '{print $2}'` 會得到 `review\r`（awk 預設 FS 不含 \r）⇒ 查 SoT 失敗判 unknown；
#   但 awk 批次路徑的 `sub(/[[:space:]].*$/,"",k)` 會把 \r 當空白剝掉 ⇒ 判 findings。
#   兩條路徑對同一份檔給出不同答案 ＝ `--audit` 的矩陣不代表 `--single` 的行為。
_raw_kind_of() {
  grep -m1 '^brief-kind:' "${1-}" 2>/dev/null \
    | tr -d '\r' \
    | awk '{print $2}'
}

# $1=file [$2=corpus dir] → stdout: findings|non-findings|unknown
classify() {
  local f="${1-}" corpus="${2-}" bk v
  # 🔴 檔案不存在 ⇒ fail-closed〔CODEX-R1-P1-02〕：原本靜默回 unknown rc=0，
  #   呼叫端分不出「這檔沒宣告」與「這檔根本不在」。
  [ -f "${f}" ] || _die "受測檔不存在: ${f}"
  bk="$(_raw_kind_of "${f}")"
  if [ -z "${bk}" ] && [ -n "${corpus}" ]; then
    # 由**該輪 brief** 導出（非猜測）：committee_run.sh 機械產生
    # `<session>-<family>.md` 與 `<session>-brief.md`，兩者共用 session 前綴。
    bk="$(_kind_from_sibling_brief "${f}" "${corpus}")"
  fi
  if [ -z "${bk}" ]; then
    echo "unknown"          # SPEC 邊界 ③：無宣告且導不出 ⇒ 不猜
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

# $1=file $2=corpus → stdout: brief-kind 值（無則 "-"）
_brief_kind_of() {
  local bk
  bk="$(_raw_kind_of "${1-}")"
  [ -n "${bk}" ] && [ -n "${2-}" ] || :
  if [ -z "${bk}" ] && [ -n "${2-}" ]; then
    bk="$(_kind_from_sibling_brief "${1}" "${2}")"
  fi
  [ -n "${bk}" ] && printf '%s\n' "${bk}" || printf '%s\n' "-"
}

# 由同輪 brief 導出 kind〔COMPOSER-R1-P1-01 裁定 (B)：本票內補〕。
# $1=file $2=corpus → stdout: kind（導不出則空）
#
# 🔴 這是**導出**不是猜測：`scripts/committee_run.sh` 以
#   `<out前綴>-<family>.md` 產出委員交件檔，而 `<out前綴>` 即 brief 的 session 前綴，
#   對應的 brief 是 `<session>-brief.md`。兩者的關聯由工具機械產生，不是命名慣例。
# 🔴 只認**最長**匹配的 session 前綴，且 brief 本身不參與導出（避免自我循環）。
_kind_from_sibling_brief() {
  local f="${1-}" corpus="${2-}" base best="" bestlen=0 sess len
  base="$(basename "${f}")"
  case "${base}" in *-brief.md) return 0 ;; esac   # brief 自身不導出
  for b in "${corpus}"/*-brief.md; do
    [ -f "${b}" ] || continue
    sess="$(basename "${b}")"
    sess="${sess%-brief.md}"
    case "${base}" in
      "${sess}"-*)
        len="${#sess}"
        if [ "${len}" -gt "${bestlen}" ]; then bestlen="${len}"; best="${b}"; fi
        ;;
    esac
  done
  [ -n "${best}" ] || return 0
  _raw_kind_of "${best}"
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
    # --corpus 可選：給了才啟用 brief↔產出導出（單檔情境沒有語料就無從導出）
    if [ -n "${CORPUS}" ]; then
      [ -d "${CORPUS}" ] || _die "corpus 不是目錄: ${CORPUS}"
    fi
    classify "${SINGLE}" "${CORPUS}"
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
    # session → kind 映射（供無自帶宣告者導出；brief 本身不參與導出）
    _bmap="$(mktemp -t fkcb.XXXXXX)" || _die "mktemp 失敗"
    for _b in "${CORPUS}"/*-brief.md; do
      [ -f "${_b}" ] || continue
      _bk="$(_raw_kind_of "${_b}")"
      [ -n "${_bk}" ] || continue
      _bs="$(basename "${_b}")"
      printf '%s\t%s\n' "${_bs%-brief.md}" "${_bk}" >> "${_bmap}"
    done
    if [ "${_total}" -gt 0 ]; then
      LC_ALL=C awk -v mapf="${_map}" -v bmapf="${_bmap}" '
        BEGIN {
          while ((getline line < mapf) > 0) { split(line, m, "\t"); cls[m[1]] = m[2] }
          nb = 0
          while ((getline line < bmapf) > 0) {
            split(line, b, "\t"); nb++; bs[nb] = b[1]; bk[nb] = b[2]
          }
        }
        function base(p,   n, a) { n = split(p, a, "/"); return a[n] }
        function derive(p,   i, s, best, bestlen, bn) {
          bn = base(p); best = ""; bestlen = 0
          if (bn ~ /-brief\.md$/) return ""        # brief 自身不導出
          for (i = 1; i <= nb; i++) {
            s = bs[i]
            if (substr(bn, 1, length(s) + 1) == s "-" && length(s) > bestlen) {
              bestlen = length(s); best = bk[i]
            }
          }
          return best
        }
        {
          path = $0; k = ""
          # 與 classify() 同語意：第一行 ^brief-kind: 的第一個空白分隔欄位；尾端 CR 先剝除
          while ((getline l < path) > 0) {
            sub(/\r$/, "", l)
            if (l ~ /^brief-kind:/) {
              k = l
              sub(/^brief-kind:[[:space:]]*/, "", k)
              gsub(/\r/, "", k)
              sub(/[[:space:]].*$/, "", k)
              break
            }
          }
          close(path)
          if (k == "") k = derive(path)
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
      printf '%s\t%s\t%s\n' \
        "$(_brief_kind_of "${f}" "${CORPUS}")" "$(classify "${f}" "${CORPUS}")" "${f}"
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
