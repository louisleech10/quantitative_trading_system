#!/usr/bin/env bash
# todofmt_write_guard.sh — TODOFMT Task 1.2：新票寫散文 TODO 即擋（PreToolUse Write|Edit）。
#   規格：docs/TODOFMT_SPEC.md Task 1.2、§P「生效之判定」。
#
# 用法：
#   bash scripts/todofmt_write_guard.sh                         # hook 模式（stdin＝PreToolUse payload）；rc 0＝放行／2＝擋
#   bash scripts/todofmt_write_guard.sh --legacy-list <檔>      # 測試用：以參數傳入既有清單（一行一路徑，已正規化）
#
# 判定順序（SPEC 步驟 1–4，不得調換；步驟 0 與步驟 1、2 之補強見 SPEC Task 1.2「實作期補強」）：
#   0. 路徑值含控制字元（換行、tab 等）⇒ 擋。
#   1. 字串層正規化：轉絕對、字面折疊 `.`／`..`／空段（與 Write 工具一致）、剝 repo 根前綴，整串 casefold。
#   2. 先比樣式、後解 symlink：檔名符合 ^[a-z0-9_]+_todo(\.[a-z0-9-]+)?\.md$，且首段為 docs 才管轄，否則放行。
#      字串層首段不為 docs 者，再以 `-ef` 由近而遠比對祖先目錄是否即 repo 之 docs（符號連結／firmlink 別名）。
#   3. 既有清單比對：正規化字串、或 realpath 解析後之 repo 相對路徑（casefold），任一命中清單即放行。
#      硬連結別名不做 inode 比對——以別名路徑寫入者視為新路徑而擋。
#   4. 未命中 ⇒ 擋，印五類落點指引。
# 🔴 不以 git 狀態（ls-files／status／diff）判定；不讀任何外部清單檔（生產呼叫只用下方字面清單）。
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# BEGIN TODOFMT LEGACY TODO LIST（L 樹中符合步驟 2 樣式之全部路徑；由 tests/governance/_todofmt_anchor.py 生成，勿手改）
_LEGACY_TODOS='
docs/archived/feature_factory_multitf_multisymbol_todo.md
docs/archived/feature_factory_optimization_todo.md
docs/archived/feature_library_plan_todo.md
docs/archived/feature_optimization_todo.md
docs/archived/ui_plan_todo.md
docs/b7_l65_parallel_todo.md
docs/convergence_method_todo.md
docs/decouple_allowlist_todo.md
docs/decouple_fix4_todo.md
docs/decouple_p3_todo.md
docs/decouple_scan2_todo.md
docs/docrot2_todo.md
docs/docsimplify_batchb_todo.md
docs/evtlabel_todo.md
docs/evtwarmup_todo.md
docs/ff_deepaudit_p0_todo.md
docs/fracdiff_maxlag_todo.md
docs/gap1_strategy_overfit_todo.md
docs/gap2_marginal_ic_todo.md
docs/gap3_event_alignment_todo.md
docs/gap3_event_disclosure_todo.md
docs/gap3_event_todo.d-001.md
docs/gap3_event_todo.md
docs/gap3_event_ux_todo.d-001.md
docs/gap3_event_ux_todo.d-002.md
docs/gap3_event_ux_todo.d-003.md
docs/gap3_event_ux_todo.d-004.md
docs/gap3_event_ux_todo.d-005.md
docs/gap3_event_ux_todo.d-006.md
docs/gap3_event_ux_todo.md
docs/gap3_scan_cube_todo.md
docs/gov_b49_path_grant_todo.md
docs/gov_dispatch_flow_fix_todo.md
docs/gov_o3ext_r7_todo.md
docs/govb0_friction_todo.md
docs/govb1_input_quality_todo.md
docs/govb25_status_factkey_todo.md
docs/govb37_friction_tally_todo.md
docs/govb50_workspace_drift_todo.md
docs/governance_harness_p0_todo.md
docs/ic1c_netic_todo.md
docs/ic1cfr_full_todo.md
docs/ic1cfr_stopgap_todo.md
docs/ic1d_attribution_todo.md
docs/ic_healthcheck_todo.md
docs/ic_la0_todo.md
docs/ic_la1_todo.md
docs/ic_la2_todo.md
docs/ic_phase0_todo.md
docs/ic_phase1_1a_align_todo.md
docs/ic_phase1_1a_cut1_todo.md
docs/ic_phase1_1a_cut2_rowindex_todo.md
docs/ic_phase1_1a_cut2_xsectional_todo.md
docs/ic_phase1_1e1b_signif_todo.md
docs/ic_phase1_contract_todo.md
docs/ic_run_selector_todo.md
docs/icresult_paging_todo.md
docs/instrev_phasea_todo.md
docs/instrev_phaseb_todo.md
docs/p16_committee_debt_todo.md
docs/p16_d001_impl_todo.md
docs/p2debt_t1_govfix_todo.md
docs/p2debt_t2_dcredirect_todo.md
docs/p2debt_t3_tscfix_todo.md
docs/redispatch_todo.md
docs/splitunify_todo.md
docs/template_gate_fix_todo.md
docs/verdictgate_todo.md
docs/verify_gate_todo.md
'
# END TODOFMT LEGACY TODO LIST

_list="${_LEGACY_TODOS}"
if [ "${1:-}" = "--legacy-list" ]; then
  [ -n "${2:-}" ] && [ -f "${2}" ] || { echo "todofmt_write_guard: --legacy-list 需一個存在之檔" >&2; exit 2; }
  _list="$(cat "${2}")"
  shift 2
fi
[ $# -eq 0 ] || { echo "用法: todofmt_write_guard.sh [--legacy-list <檔>]" >&2; exit 2; }

command -v jq >/dev/null 2>&1 || { echo "todofmt_write_guard: 找不到 jq ⇒ fail-closed" >&2; exit 2; }
_payload="$(cat)"

# 0. 路徑值含控制字元（換行、tab 等）即擋——於 JSON 字串層以 jq 判定（命令替換會吃掉尾端換行，不可於 shell 層判）。
#    下方逐行之清單比對會把換行拆成多個樣式（b3 審碼 codex：「清單內之檔＋換行＋新檔名」被當成清單內之檔而放行）。
if printf '%s' "${_payload}" | jq -e '(.tool_input.file_path // "") | test("[[:cntrl:]]")' >/dev/null 2>&1; then
  echo "[todofmt_write_guard] 🔴 擋下：路徑含控制字元（換行、tab 等）：$(printf '%s' "${_payload}" | jq -c '.tool_input.file_path')" >&2
  exit 2
fi
_fp="$(printf '%s' "${_payload}" | jq -r '.tool_input.file_path // empty' 2>/dev/null)" || _fp=""
[ -n "${_fp}" ] || exit 0

_lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }
# 字面折疊 `.`／`..`／空段（輸入為絕對路徑）。Write 工具實測亦如此折疊：經不存在之目錄之 `..` 照樣寫入折疊後之路徑。
_lexfold() {
  _lf_in="${1#/}/"; _lf_out=""
  while [ -n "${_lf_in}" ]; do
    _lf_seg="${_lf_in%%/*}"; _lf_in="${_lf_in#*/}"
    case "${_lf_seg}" in
      ''|.) : ;;
      ..) _lf_out="${_lf_out%/*}" ;;
      *) _lf_out="${_lf_out}/${_lf_seg}" ;;
    esac
  done
  printf '%s' "${_lf_out:-/}"
}

# 1. 字串層正規化：轉絕對（相對路徑視為 repo 相對）、字面折疊（含剝 `./`）、剝 repo 根前綴（casefold 比對）
_absin="${_fp}"
case "${_absin}" in /*) : ;; *) _absin="${REPO_ROOT}/${_fp}" ;; esac
_lex="$(_lexfold "${_absin}")"
_rel="${_lex}"
case "$(_lower "${_lex}")" in "$(_lower "${REPO_ROOT}")/"*) _rel="${_lex:$(( ${#REPO_ROOT} + 1 ))}" ;; esac
_norm="$(_lower "${_rel}")"

# 2. 樣式：檔名以寫入之字面為準（先比樣式、後解 symlink），且位於 docs/ 下
_base="${_norm##*/}"
printf '%s' "${_base}" | grep -Eq '^[a-z0-9_]+_todo(\.[a-z0-9-]+)?\.md$' || exit 0
case "${_norm}" in
  docs/*) : ;;
  *)
    # 字串層不在 docs/ 下（例：經指向 repo 之符號連結、/System/Volumes/Data 別名寫入）：由近而遠比對各祖先目錄
    # 是否即 repo 之 docs（`-ef`＝同裝置同 inode）；命中即以其下之剩餘段為 docs/ 下之路徑。
    # 只比祖先目錄、不解檔案本身，故檔名樣式仍以寫入之字面為準（b3 審碼 grok）。
    _d="${_lex%/*}"; _rest="${_lex##*/}"; _rel=""
    while [ -n "${_d}" ]; do
      if [ "${_d}" -ef "${REPO_ROOT}/docs" ]; then _rel="docs/${_rest}"; break; fi
      _rest="${_d##*/}/${_rest}"; _d="${_d%/*}"
    done
    [ -n "${_rel}" ] || exit 0
    _norm="$(_lower "${_rel}")" ;;
esac

# 3. 既有清單比對（字串；realpath 後再比一次）。含控制字元之值一律不算命中（逐行比對會被它拆成多個樣式）
_in_list() {
  case "$1" in *[[:cntrl:]]*) return 1 ;; esac
  printf '%s\n' "${_list}" | grep -Fxq -- "$1"
}
_in_list "${_norm}" && exit 0
if _rp="$(realpath "${_lex}" 2>/dev/null)"; then
  _root_real="$(realpath "${REPO_ROOT}" 2>/dev/null || printf '%s' "${REPO_ROOT}")"
  case "${_rp}" in "${_root_real}/"*) _in_list "$(_lower "${_rp#"${_root_real}/"}")" && exit 0 ;; esac
fi

# 4. 擋
cat >&2 <<EOF
[todofmt_write_guard] 🔴 擋下：${_fp} 是新的散文 TODO（檔名符合 *_TODO*.md，且不在設計定案時之既有清單內）。
新票之 TODO 不再寫散文，改為五類落點（docs/TODOFMT_SPEC.md Task 0.1）：
  1. 生產模組空殼（stub_modules）
  2. 具名驗收測試／驗收腳本（test_files、script_acceptance）
  3. 契約 JSON（contract_jsons）
  4. 機讀批次卡（batch_card）
  5. 實跑收據（run_receipts，資訊性）
以 manifest 串起：docs/manifests/<EPIC>.json；生成指引見 templates/TODO_GENERATION_PROMPT.md；
機檢：bash scripts/template_check.sh todofmt docs/manifests/<EPIC>.json
EOF
exit 2
