#!/usr/bin/env bash
# govb1_final_gate.sh — GOVB1 GATE-FINAL（§0.2 G-1～G-8 ＋ _g0_tests／_g0_syntax）
# 判準唯一來源＝docs/GOVB1_INPUT_QUALITY_TODO.md §0.1b；本檔只實作。
# 用法：bash scripts/govb1_final_gate.sh [--only <檢查名>] | --print-plan
#        | --print-batch3-paths | --print-batch3-targets
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
  # schema／hash 守衛（未知動詞 fail-closed 等）
  _g7_policy >/dev/null || return 1
  # consumer ⊆ allow−deny（不含 meta；meta 非產品 scope）
  _allow="$(awk '$1=="deny"{d[$2]=1} $1=="allow"{a[$2]=1}
                 END{ for (p in a) if (!(p in d)) print p }' \
            "${GOVB1_SCOPE_MANIFEST}" | LC_ALL=C sort -u)"
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
  # 未知動詞 fail-closed〔CODEX-R1-P0-01〕：打錯字被靜默忽略 ≡ 該列不存在
  _unk="$(awk 'NF && $1 !~ /^#/ && $1 != "allow" && $1 != "deny" && $1 != "consumer" && $1 != "meta" {
                 print $1
               }' "${GOVB1_SCOPE_MANIFEST}")"
  [ -z "${_unk}" ] \
    || { printf 'G-7 FAIL: scope manifest 含未知動詞（fail-closed）:\n%s\n' "${_unk}" >&2; return 1; }
  # 路徑形態守衛〔CODEX-R5-P1-01〕：凍結 manifest grammar。
  # 在「未知動詞」之後、產出 decl 之前：先取 raw 段（動詞後恰好一個分隔空白/tab），
  # 再判形態，最後才決定是否採用。不得先 sub() 吃掉前導/尾端空白再事後判斷。
  # 為何這就算收（類別封閉，不再逐變體追逐）：
  #   - 宣告端：路徑要嘛正確解析、要嘛被顯式拒絕 ⇒ 不可能靜默誤判
  #   - 未宣告端：任何形態皆落在 actual−decl 差集 ⇒ 恆被擋（fail-closed 不變）
  # 不支援：路徑前導/尾端空白或 tab、路徑含控制字元（C0 除 tab；tab 中段仍允）。
  # 不「支援」那些形態——只做顯式拒絕。
  # LC_ALL=C：逐 byte 判 C0，避免 UTF-8 locale 下 towc 對 CJK 路徑炸掉
  _form_err="$(
    LC_ALL=C awk '
      function form_of(raw,   i, c) {
        if (raw ~ /^[ \t]/) return "leading-whitespace"
        if (raw ~ /[ \t]$/) return "trailing-whitespace"
        for (i = 1; i <= length(raw); i++) {
          c = substr(raw, i, 1)
          if (c == "\t") continue
          # C0 控制字元（0x00-0x1F）除 tab；含 \\n/\\r 與其他 C0
          if (c ~ /[\001-\010\012-\037]/) return "control-char"
        }
        return ""
      }
      NF && $1 !~ /^#/ && ($1 == "allow" || $1 == "deny" || $1 == "consumer" || $1 == "meta") {
        line = $0
        sub(/^[ \t]+/, "", line)
        if (!match(line, /^(allow|deny|consumer|meta)[ \t]/)) next
        raw = substr(line, RSTART + RLENGTH)
        f = form_of(raw)
        if (f != "") {
          printf "form=%s line=%s\n", f, $0
        }
      }
    ' "${GOVB1_SCOPE_MANIFEST}"
  )"
  [ -z "${_form_err}" ] \
    || { printf 'G-7 FAIL: scope manifest 路徑形態不支援（fail-closed）:\n%s\n' "${_form_err}" >&2; return 1; }
  # meta expected-set〔CODEX-R1-P0-01／b2-review-r1／CODEX-R2-P0-02〕：
  # 精確凍結 6 項（列數＋multiset），寫死於實作端。
  # 集合語義：順序無關（兩側 sort 後比；不 -u，保留重複以便列數契約生效）。
  # 重複列 ⇒ 列數≠6，訊息指出重複路徑。多一／少一／改字皆立即非零。
  # 不得改由 manifest 自身宣告（自證＝無檢查）。
  # 「不在 Task 欄」只能解釋為不能用 allow，不能自動產生 meta。
  _meta_want="$(printf '%s\n' \
    'HANDOFF.md' \
    'CLAUDE.md' \
    'handoffs/20260801-GOV-AMEND-BACKLOG.md' \
    '白話說明/' \
    'scripts/govb1_task_tickets.tsv' \
    'scripts/govb1_single_source_check.sh' | LC_ALL=C sort)"
  _meta_got_raw="$(
    awk '
      function mpath(   p) {
        p = $0
        sub(/^[ \t]+/, "", p)
        if (p == "" || p ~ /^#/) return ""
        if (!match(p, /^meta[ \t]+/)) return ""
        return substr(p, RSTART + RLENGTH)
      }
      $1 == "meta" {
        p = mpath()
        if (p != "") print p
      }
    ' "${GOVB1_SCOPE_MANIFEST}"
  )"
  # 列數契約：重複路徑先拒並具名〔CODEX-R2-P0-02／COMPOSER-R2-P0-02〕
  # 兩側皆不用 sort -u：只改一側會使比對永遠不等。順序無關＝集合語義（正確行為）。
  _meta_dups="$(printf '%s\n' "${_meta_got_raw}" | LC_ALL=C sort | uniq -d)"
  if [ -n "${_meta_dups}" ]; then
    echo "G-7 FAIL: meta 重複路徑（列數契約；精確凍結 6 項，禁重複列）:" >&2
    printf '%s\n' "${_meta_dups}" | sed 's/^/    /' >&2
    return 1
  fi
  _meta_got="$(printf '%s\n' "${_meta_got_raw}" | LC_ALL=C sort)"
  if [ "${_meta_got}" != "${_meta_want}" ]; then
    echo "G-7 FAIL: meta expected-set 不符（精確凍結集合；多一/少一/改字皆拒）" >&2
    echo "  expected:" >&2
    printf '%s\n' "${_meta_want}" | sed 's/^/    /' >&2
    echo "  got:" >&2
    printf '%s\n' "${_meta_got}" | sed 's/^/    /' >&2
    return 1
  fi
  # manifest 為純資料：allow | deny | consumer | meta；decl = (allow ∪ meta) − deny；deny 優先
  # 🔴 path = 動詞後整段（含空白／"）；禁 $2 截斷〔CODEX-R4-P1-01〕
  # 🔴 raw 抽取：動詞後恰好一個空白/tab，不再 sub 吃掉路徑自身前後空白〔CODEX-R5-P1-01〕
  #    （上段 form 守衛已拒不支援形態；此處合法列與守衛同一抽取規則 ⇒ decl 一致）
  awk '
    function mpath(   p) {
      p = $0
      sub(/^[ \t]+/, "", p)
      if (p == "" || p ~ /^#/) return ""
      if (!match(p, /^(allow|deny|consumer|meta)[ \t]/)) return ""
      return substr(p, RSTART + RLENGTH)
    }
    $1 == "deny" {
      p = mpath()
      if (p != "") d[p] = 1
      next
    }
    $1 == "allow" || $1 == "meta" {
      p = mpath()
      if (p != "") a[p] = 1
      next
    }
    END {
      for (p in a)
        if (!(p in d)) print p
    }
  ' "${GOVB1_SCOPE_MANIFEST}" | LC_ALL=C sort -u
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
# ── G-7 交付形態守衛（批 3：task-scoped 放寬 M）────────────────────────
# 裁定：handoffs/reconcile/20260808-govb1-b3-consult-r1/synth.md 群集 3
#   批3已開工 := base..HEAD 含 Task 1.2／1.4「新建」欄 proxy（由凍結 TODO 導出）
#   窄守衛仍在 := status case 僅匹配 ?? / A*（無 M）
#   不變式    := NOT (批3已開工 AND 窄守衛仍在)
# 放寬（task-scoped，禁 epic-wide allow 匹配 M）：
#   - 全量 allow 之 ??|A* 交付形態檢查維持不變
#   - 批3開工後，僅對 Task 1.2／1.4「修改∪新建」路徑另匹配 M /MM
#   - ambient M（例：scripts/gate_check.sh 在 allow 且現為 M）不得誤紅
# 路徑集合來源＝凍結 TODO（與 tests/_todo_new_paths 同源；禁 govb1_batch_markers.tsv）

_GOVB1_TODO="${GOVB1_TODO:-docs/GOVB1_INPUT_QUALITY_TODO.md}"

# $1=task_id → stdout：該 Task 區段（### Task <id> … 下一 ### Task／EOF）
_todo_task_section() {
  awk -v t="$1" '
    BEGIN { p = 0 }
    $0 ~ ("^### Task " t "( |$)") { p = 1; print; next }
    p && /^### Task / { exit }
    p { print }
  ' "${_GOVB1_TODO}"
}

# stdin → 只保留 repo 路徑形態之 backtick 內容
_todo_path_tokens() {
  grep -oE '`(scripts|tests|templates|docs)/[A-Za-z0-9_./-]+`' | tr -d '`'
}

# $1=task_id → stdout：新建欄路徑
_todo_new_paths() {
  _todo_task_section "$1" | awk '
    /\*\*新建\*\*：/ { n = 1 }
    n && /\*\*只讀\*\*/ { exit }
    n { print }
  ' | _todo_path_tokens
}

# $1=task_id → stdout：修改欄路徑（至新建／只讀）
_todo_mod_paths() {
  _todo_task_section "$1" | awk '
    /\*\*修改\*\*：/ { m = 1 }
    m && /\*\*新建\*\*：/ { exit }
    m && /\*\*只讀\*\*/ { exit }
    m { print }
  ' | _todo_path_tokens
}

# 批 3 proxy＝Task 1.2／1.4 新建欄（= _BATCH3_PROXY_PATHS）
_g7_batch3_proxy_paths() {
  { _todo_new_paths 1.2; _todo_new_paths 1.4; } | LC_ALL=C sort -u
}

# 批 3 標的＝Task 1.2／1.4 修改∪新建（task-scoped M 僅對此集合）
_g7_batch3_target_paths() {
  {
    _todo_mod_paths 1.2
    _todo_new_paths 1.2
    _todo_mod_paths 1.4
    _todo_new_paths 1.4
  } | LC_ALL=C sort -u
}

# rc=0 ⇔ base..HEAD 含任一 proxy
_g7_batch3_started() {
  _prox="$(_g7_batch3_proxy_paths)"
  [ -n "${_prox}" ] || return 1
  while IFS= read -r -d '' p; do
    [ -n "${p}" ] || continue
    printf '%s\n' "${_prox}" | grep -qxF "${p}" && return 0
  done < <(git -c core.quotepath=false diff --name-only -z --diff-filter=ACMRD "$(_base)" HEAD 2>/dev/null)
  return 1
}

_g7() { decl="$(_g7_policy)" || return 1; _nonempty G-7 "${decl}" || return 1
        # 交付形態守衛〔CODEX-R17-P0-01〕＋批 3 task-scoped M：
        #   1) 全量 allow：?? / A* 未 commit ⇒ FAIL（新建未交付）
        #   2) 批3開工後：僅批 3 標的路徑之 M/MM 未 commit ⇒ FAIL
        #   3) 非標的 ambient M（gate_check.sh 等）不觸發
        _b3_targets="$(_g7_batch3_target_paths)"
        _b3_on=0
        _g7_batch3_started && _b3_on=1
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
            \ M|M\ |MM)
              # task-scoped M：批3開工 且 路徑 ∈ 批3標的
              if [ "${_b3_on}" -eq 1 ] \
                && printf '%s\n' "${_b3_targets}" | grep -qxF "${p}"; then
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
        # core.quotepath=false：非 ASCII 路徑（如 白話說明/）不得被 C-quote，
        # 否則與 manifest meta 前綴比對永遠 miss（方案 B 簿記目錄會假紅）。
        # -z：含空白／" 之路徑不得被行式 name-only 的 C-quote 或空白截斷〔CODEX-R4-P1-01〕
        extra=""
        while IFS= read -r -d '' p; do
          [ -n "${p}" ] || continue
          _g7_covered "${p}" "${decl}" || extra="${extra}${p}"$'\n'
        done < <(git -c core.quotepath=false diff --name-only -z --diff-filter=ACMRD "$(_base)" HEAD)
        [ -z "${extra}" ] || { printf 'G-7 FAIL: 未宣告即修改:\n%s\n' "${extra}" >&2; return 1; }; }

# GATE-B3：同檔序列 1.2→1.4（brief_conformance_check.sh）＋雙 proxy 時強制
# 驗收時點＝B3 收案當下（兩 proxy 皆在 base..HEAD）；未開工 ⇒ 跳過。
# 拒：合併單一 commit／逆序（1.4 先於 1.2）；「不防蓄意」誠實邊界保留。
_gate_b3() {
  _prox="$(_g7_batch3_proxy_paths)"
  _n_prox=0
  _n_hit=0
  while IFS= read -r p; do
    [ -n "${p}" ] || continue
    _n_prox=$((_n_prox + 1))
    git -c core.quotepath=false diff --name-only --diff-filter=ACMRD "$(_base)" HEAD \
      | grep -qxF "${p}" && _n_hit=$((_n_hit + 1))
  done <<EOF
${_prox}
EOF
  # 未齊 → 不強制（批 3 進行中或未開工）
  [ "${_n_prox}" -gt 0 ] && [ "${_n_hit}" -eq "${_n_prox}" ] || return 0

  _bc="scripts/brief_conformance_check.sh"
  # 兩獨立 commit 觸及 brief_conformance（合併 ⇒ 僅 1）
  _n_bc="$(git log --oneline "$(_base)"..HEAD -- "${_bc}" | wc -l | tr -d ' ')"
  [ "${_n_bc}" -ge 2 ] \
    || { echo "GATE-B3 FAIL: ${_bc} 在 base..HEAD 須 ≥2 獨立 commit（現 ${_n_bc}；禁合併 1.2+1.4）" >&2; return 1; }

  # 序：_check_id_pattern 首次出現之 commit 須為 _check_fact_verified 之祖先
  _first_id=""
  _first_fv=""
  while IFS= read -r c; do
    [ -n "${c}" ] || continue
    _blob="$(git show "${c}:${_bc}" 2>/dev/null)" || continue
    printf '%s' "${_blob}" | grep -q '_check_id_pattern' \
      && [ -z "${_first_id}" ] && _first_id="${c}"
    printf '%s' "${_blob}" | grep -q '_check_fact_verified' \
      && [ -z "${_first_fv}" ] && _first_fv="${c}"
  done < <(git log --reverse --format='%H' "$(_base)"..HEAD -- "${_bc}")

  [ -n "${_first_id}" ] \
    || { echo "GATE-B3 FAIL: base..HEAD 未見 _check_id_pattern 引入" >&2; return 1; }
  [ -n "${_first_fv}" ] \
    || { echo "GATE-B3 FAIL: base..HEAD 未見 _check_fact_verified 引入" >&2; return 1; }
  [ "${_first_id}" != "${_first_fv}" ] \
    || { echo "GATE-B3 FAIL: 1.2 與 1.4 併於同一 commit（禁合併）" >&2; return 1; }
  git merge-base --is-ancestor "${_first_id}" "${_first_fv}" \
    || { echo "GATE-B3 FAIL: 逆序——_check_fact_verified 先於 _check_id_pattern" >&2; return 1; }

  # 誤擋率 receipt（TODO §0.2 GATE-B3：T-1.2／T-1.4 全綠 ＋ 兩份 receipt）
  # fail-closed：缺檔／空檔／缺母體／缺 95% CI／上界>5%／缺非實作者複核狀態 ⇒ 非零
  # 誠實邊界：handoffs/* ∈ .git/info/exclude ⇒ 僅驗工作樹，無版控
  _rcp_dir="handoffs/receipts"
  _rcp_ok=0
  _rcp_ids=""
  shopt -s nullglob
  for _rcp in "${_rcp_dir}"/govb1-fp-*.md; do
    [ -s "${_rcp}" ] || continue
    grep -q '母體定義' "${_rcp}" || continue
    # 非實作者複核狀態（待複核／已複核皆可；必須有欄位標記）
    grep -qE '非實作者' "${_rcp}" || continue
    grep -qE '複核' "${_rcp}" || continue
    _ci_line="$(grep -oE '95% CI \[[0-9.]+%, [0-9.]+%\]' "${_rcp}" | head -1)"
    [ -n "${_ci_line}" ] || continue
    _ub="$(printf '%s' "${_ci_line}" | sed -nE 's/.*\[([0-9.]+)%, ([0-9.]+)%\].*/\2/p')"
    [ -n "${_ub}" ] || continue
    awk -v u="${_ub}" 'BEGIN{ if ((u+0)>5) exit 1; exit 0 }' || continue
    _tid="$(basename "${_rcp}" .md)"
    _tid="${_tid#govb1-fp-}"
    # 不同 TASK_ID
    case " ${_rcp_ids} " in
      *" ${_tid} "*) continue ;;
    esac
    _rcp_ids="${_rcp_ids}${_tid} "
    _rcp_ok=$((_rcp_ok + 1))
  done
  shopt -u nullglob
  [ "${_rcp_ok}" -ge 2 ] \
    || { echo "GATE-B3 FAIL: 須至少兩個不同 TASK_ID 之誤擋率 receipt（現 ${_rcp_ok}；dir=${_rcp_dir}/govb1-fp-*.md；須含母體定義／95% CI 上界≤5%／非實作者複核狀態）" >&2; return 1; }
  return 0
}

_g8() { bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260807-govb1-x-consult-r1/synth.md >/dev/null; }

# ── lifecycle embed ≡ 權威 JSON（Task 1.1 修補案 C2；關 R-8 假綠）──────────
# 權威檔不存在 ⇒ FAIL（repo 層 fail-closed；執行期缺檔仍可 embed 物化，見 brief 裁定）。
# 兩支腳本之 _LIFECYCLE_EMBED_B64 解碼後須與權威檔 jq -S 正規化後相等（禁漂移第二真相源）。
_lifecycle_embed() {
  _json="scripts/govflow_lifecycle.json"
  if [ ! -f "${_json}" ]; then
    echo "lifecycle_embed FAIL: 權威檔不存在: ${_json}" >&2
    return 1
  fi
  if ! jq empty "${_json}" 2>/dev/null; then
    echo "lifecycle_embed FAIL: 權威檔語法錯: ${_json}" >&2
    return 1
  fi
  _jnorm="$(mktemp)"
  _enorm="$(mktemp)"
  _edec="$(mktemp)"
  _le_rc=0
  if ! jq -S . "${_json}" > "${_jnorm}" 2>/dev/null; then
    echo "lifecycle_embed FAIL: jq 正規化權威檔失敗: ${_json}" >&2
    rm -f "${_jnorm}" "${_enorm}" "${_edec}"
    return 1
  fi
  for _s in scripts/brief_conformance_check.sh scripts/cx_run.sh; do
    if [ ! -f "${_s}" ]; then
      echo "lifecycle_embed FAIL: 腳本不存在: ${_s}" >&2
      _le_rc=1
      break
    fi
    _b64="$(sed -n "s/^_LIFECYCLE_EMBED_B64='\\(.*\\)'\$/\\1/p" "${_s}" | head -1)"
    if [ -z "${_b64}" ]; then
      echo "lifecycle_embed FAIL: ${_s} 缺 _LIFECYCLE_EMBED_B64" >&2
      _le_rc=1
      break
    fi
    if ! printf '%s' "${_b64}" | base64 -d > "${_edec}" 2>/dev/null; then
      echo "lifecycle_embed FAIL: ${_s} embed base64 解碼失敗" >&2
      _le_rc=1
      break
    fi
    if ! jq -S . "${_edec}" > "${_enorm}" 2>/dev/null; then
      echo "lifecycle_embed FAIL: ${_s} embed 解碼後非合法 JSON" >&2
      _le_rc=1
      break
    fi
    if ! diff -q "${_jnorm}" "${_enorm}" >/dev/null 2>&1; then
      echo "lifecycle_embed FAIL: ${_s} embed ≠ ${_json}（jq -S 正規化後不等）" >&2
      _le_rc=1
      break
    fi
  done
  rm -f "${_jnorm}" "${_enorm}" "${_edec}"
  return "${_le_rc}"
}

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
gate_b3|scripts/brief_conformance_check.sh docs/GOVB1_INPUT_QUALITY_TODO.md|_gate_b3
g8|handoffs/reconcile/20260807-govb1-x-consult-r1/synth.md|_g8
lifecycle_embed|scripts/govflow_lifecycle.json scripts/brief_conformance_check.sh scripts/cx_run.sh|_lifecycle_embed
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
# 唯讀 probe：anti-drift 測試必須呼叫 production exporter，禁複製 parser（CODEX-R1-P1-04）
if [ "${1:-}" = "--print-batch3-paths" ]; then _g7_batch3_proxy_paths; exit 0; fi
if [ "${1:-}" = "--print-batch3-targets" ]; then _g7_batch3_target_paths; exit 0; fi
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
