#!/usr/bin/env bash
# govb1_final_gate.sh — GOVB1 GATE-FINAL（§0.2 G-1～G-8 ＋ _g0_tests／_g0_syntax）
# 判準唯一來源＝docs/GOVB1_INPUT_QUALITY_TODO.md §0.1b；本檔只實作。
# 用法：bash scripts/govb1_final_gate.sh [--only <檢查名>] | --print-plan
set -u

_base() { grep -m1 '^base_commit:' scripts/govb1_frozen_hashes.txt | awk '{print $2}'; }
_h()    { shasum -a 256 | cut -c1-12; }

# ── 抽取器（三條共用；各自附非空守衛，空對空恆綠是假綠）────────────────
_g2_consumers() {   # stdout: consumer 檔清單（一行一檔）；禁人手列舉
  _plan="$(bash scripts/govb1_final_gate.sh --print-plan)" || return 1
  # UNRESOLVED 職責：只檢查 _CHECKS 所列函式是否存在（非 consumer closure）
  printf '%s\n' "${_plan}" | grep -q '^UNRESOLVED' \
    && { echo "G-2 FAIL: plan 有檢查函式不存在（非 consumer closure，見 B.4#6）" >&2; return 1; }
  : "${GOVB1_SCOPE_MANIFEST:=scripts/govb1_scope.manifest}"
  _cons="$(awk '$1=="consumer"{print $2}' "${GOVB1_SCOPE_MANIFEST}" | LC_ALL=C sort -u)"
  _allow="$(_g7_policy)" || return 1
  # consumer 必為 allow 之子集；否則 manifest 自相矛盾 ⇒ fail-closed
  _bad="$(comm -23 <(printf '%s\n' "${_cons}") <(printf '%s\n' "${_allow}"))"
  [ -z "${_bad}" ] || { printf 'G-2 FAIL: consumer 不在 allow 內:\n%s\n' "${_bad}" >&2; return 1; }
  printf '%s\n' "${_cons}"
}
_G2_UNITS='份|列|個 fixture|個 Task'   # 量詞集合唯一定義處
# 🔴 必須傳 "$@"——偽碼若只寫 grep pattern 不帶檔案，會讀 stdin 恆空 ⇒ G-2 假綠
_frozen_hits() { grep -nE "[0-9]+[[:space:]]*(${_G2_UNITS})" "$@"; }

_behavior_rows() { awk '/^[[:space:]]*\| `.*` \| (\*\*)?rc==/ { print }'; }
_g6_func()       { awk '/^_maybe_register_stamp_output\(\)/ { f=1 } f { print } f && /^}/ { exit }'; }

_g7_policy() {   # stdout: 本批 scope 白名單（一行一筆；目錄以 `/` 結尾）
  : "${GOVB1_SCOPE_MANIFEST:=scripts/govb1_scope.manifest}"
  [ -s "${GOVB1_SCOPE_MANIFEST}" ] \
    || { echo "G-7 FAIL: 缺 scope manifest ${GOVB1_SCOPE_MANIFEST}（fail-closed）" >&2; return 1; }
  _want="$(grep -m1 '^scope_manifest:' scripts/govb1_frozen_hashes.txt | awk '{print $2}')"
  _got="$(shasum -a 256 "${GOVB1_SCOPE_MANIFEST}" | cut -c1-12)"
  [ -n "${_want}" ] && [ "${_want}" = "${_got}" ] \
    || { echo "G-7 FAIL: scope manifest 雜湊不符（want=${_want} got=${_got}）" >&2; return 1; }
  # manifest 為純資料：allow / deny；deny 優先
  awk '$1=="deny"{d[$2]=1} $1=="allow"{a[$2]=1}
       END{ for (p in a) if (!(p in d)) print p }' "${GOVB1_SCOPE_MANIFEST}" | LC_ALL=C sort -u
}
_nonempty() { [ -n "$2" ] || { echo "$1 FAIL: 抽取結果為空（pattern 失效）" >&2; return 1; }; }

# ── 兩條全域（GATE-FINAL 條件欄宣稱者，須真的在腳本裡）──────────────
_g0_tests()  { venv/bin/python -m pytest tests/governance -q >/dev/null; }
_g0_syntax() { s=0; for f in scripts/*.sh; do bash -n "$f" || s=1; done; return "$s"; }

# ── 八條禁令 ──────────────────────────────────────────────────
_g1() { venv/bin/python -m pytest tests/governance/test_completeness_idlike_fp.py -q >/dev/null \
        && [ -z "$(git diff --stat tests/governance/test_completeness_idlike_fp.py)" ]; }
_g2() { c="$(_g2_consumers)"; _nonempty G-2 "${c}" || return 1
        # shellcheck disable=SC2086
        ! _frozen_hits ${c} 2>/dev/null | grep -q .; }
_g3() { ! grep -rnqE 'WARN_ONLY|--dry-run|DISABLED_BY_DEFAULT|SKIP_.*=1' \
        scripts/gen_fact_key_blocks.sh scripts/findings_kind_classify.sh scripts/gen_govb1_contract_matrix.sh 2>/dev/null; }
_g4() { [ -z "$(git diff --stat scripts/gen_govflow_manifest.sh)" ]; }
_g5() { b="$(git show "$(_base):docs/GOV_DISPATCH_FLOW_FIX_SPEC.md" | _behavior_rows)"
        w="$(_behavior_rows < docs/GOV_DISPATCH_FLOW_FIX_SPEC.md)"
        _nonempty G-5 "${b}" && _nonempty G-5 "${w}" || return 1
        [ "$(printf '%s\n' "${b}" | _h)" = "$(printf '%s\n' "${w}" | _h)" ]; }
_g6() { b="$(git show "$(_base):scripts/cx_run.sh" | _g6_func)"
        w="$(_g6_func < scripts/cx_run.sh)"
        _nonempty G-6 "${b}" && _nonempty G-6 "${w}" || return 1
        [ "$(printf '%s\n' "${b}" | _h)" = "$(printf '%s\n' "${w}" | _h)" ]; }

# 唯一 path-vs-decl 比對點（守衛與主體共用）
_g7_covered() {   # $1=path $2=decl(多行) → rc=0 表示被涵蓋
  while IFS= read -r d; do
    [ -n "${d}" ] || continue
    case "${d}" in
      */) case "$1" in "${d}"*) return 0 ;; esac ;;
      *)  [ "$1" = "${d}" ] && return 0 ;;
    esac
  done <<EOF
$2
EOF
  return 1
}
_g7() { decl="$(_g7_policy)" || return 1; _nonempty G-7 "${decl}" || return 1
        # 交付形態守衛〔CODEX-R17-P0-01〕：本批新建檔未 commit ⇒ FAIL。
        # 只盯 untracked／added（?? / A*）：ambient M（例：B3 十檔）即使落在
        # 後續 Task 的 allow 內，也不進 base..HEAD actual，不得當成「本批未交付」。
        # 完整 epic allow 於 Task 0.1 凍結（F5／hash-lock），與 ambient dirty 並存。
        _uc="${TMPD:-/tmp}/g7_uncommitted.$$"
        : > "${_uc}"
        while IFS= read -r -d '' rec; do
          [ -n "${rec}" ] || continue
          # porcelain -z：一般列 = "XY path"
          _st="${rec:0:2}"
          p="${rec:3}"
          [ -n "${p}" ] || continue
          case "${_st}" in
            \?\?|A\ |A?|A*)
              if _g7_covered "${p}" "${decl}"; then
                echo "UNCOMMITTED:${p}" >> "${_uc}"
                break
              fi
              ;;
          esac
        done < <(git status --porcelain=v1 --untracked-files=all -z)
        if [ -s "${_uc}" ]; then
          echo "G-7 FAIL: UNSUPPORTED-DELIVERY-SHAPE — 本批宣告路徑仍未 commit" >&2
          cat "${_uc}" >&2
          rm -f "${_uc}"
          return 1
        fi
        rm -f "${_uc}"
        # ancestor 驗證：base 須為 HEAD 之祖先
        git merge-base --is-ancestor "$(_base)" HEAD \
          || { echo "G-7 FAIL: base_commit 非 HEAD 祖先（range 無意義）" >&2; return 1; }
        actual="$(git diff --name-only --diff-filter=ACMRD "$(_base)" HEAD | LC_ALL=C sort -u)"
        # 引號保留：含空白路徑不得斷詞（COMPOSER-R8-P2-01）
        extra=""
        while IFS= read -r p; do
          [ -n "${p}" ] || continue
          _g7_covered "${p}" "${decl}" || extra="${extra}${p}"$'\n'
        done <<EOF
$(printf '%s\n' "${actual}")
EOF
        [ -z "${extra}" ] || { printf 'G-7 FAIL: 未宣告即修改:\n%s\n' "${extra}" >&2; return 1; }; }
_g8() { bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260807-govb1-x-consult-r1/synth.md >/dev/null; }

# 檢查本身資料化——單一表格即唯一真相源
# 欄位：name | files | fn（多檔以空白分隔）
# name 與 CLI --only 對齊（無前導底線）：g0_tests / g2 / …
_CHECKS='
g0_tests|tests/governance|_g0_tests
g0_syntax|SCRIPTS_GLOB|_g0_syntax
g1|tests/governance/test_completeness_idlike_fp.py|_g1
g2|scripts/govb1_final_gate.sh|_g2
g3|scripts/gen_fact_key_blocks.sh scripts/findings_kind_classify.sh scripts/gen_govb1_contract_matrix.sh|_g3
g4|scripts/gen_govflow_manifest.sh|_g4
g5|docs/GOV_DISPATCH_FLOW_FIX_SPEC.md|_g5
g6|scripts/cx_run.sh|_g6
g7|scripts/govb1_scope.manifest scripts/govb1_frozen_hashes.txt|_g7
g8|handoffs/reconcile/20260807-govb1-x-consult-r1/synth.md|_g8
'
_rows() { printf '%s\n' "${_CHECKS}" | grep -v '^[[:space:]]*$'; }
_plan() {   # stdout: FILE\t<path> 或 UNRESOLVED\t<name>\t<reason>
  _rows | while IFS='|' read -r name files fn; do
    type "${fn}" >/dev/null 2>&1 \
      || { printf 'UNRESOLVED\t%s\t函式 %s 不存在\n' "${name}" "${fn}"; continue; }
    # shellcheck disable=SC2086
    for f in ${files}; do
      if [ "${f}" = "SCRIPTS_GLOB" ]; then
        for s in scripts/*.sh; do printf 'FILE\t%s\n' "${s}"; done
      else
        printf 'FILE\t%s\n' "${f}"
      fi
    done
  done
}
if [ "${1:-}" = "--print-plan" ]; then _plan; exit 0; fi

_names() { _rows | cut -d'|' -f1; }
if [ "${1:-}" = "--only" ]; then
  _sel_raw="${2:-}"
  # 相容 _g2 與 g2
  _sel="${_sel_raw#_}"
  _names | grep -qx "${_sel}" \
    || { echo "ERROR: 未知檢查 '${_sel_raw}'（可用：$(_names | tr '\n' ' ')）" >&2; exit 2; }
  sel="${_sel}"
else sel=""; fi

# plan 若有任何 UNRESOLVED，執行前即 fail-closed
_plan | grep -q '^UNRESOLVED' && { _plan | grep '^UNRESOLVED' >&2; exit 2; }

rc=0; ran=0
for g in $(_names); do
  [ -z "${sel}" ] || [ "${g}" = "${sel}" ] || continue
  fn="$(_rows | awk -F'|' -v n="${g}" '$1==n{print $3}')"
  ran=$(( ran + 1 ))
  if "${fn}"; then echo "PASS ${g}"; else echo "FAIL ${g}" >&2; rc=1; fi
done
[ "${ran}" -gt 0 ] || { echo "ERROR: 零檢查執行（空轉）" >&2; exit 2; }
exit "${rc}"
