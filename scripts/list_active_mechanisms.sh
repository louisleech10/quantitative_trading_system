#!/usr/bin/env bash
# 治理機制掛載一覽 —— 由權威源**機械導出**，非手寫。
#
# 用法：
#   bash scripts/list_active_mechanisms.sh            # 印出 markdown 表格
#   bash scripts/list_active_mechanisms.sh --write    # 寫入 docs/GOV_ACTIVE_MECHANISMS.md 之生成區塊
#   bash scripts/list_active_mechanisms.sh --check    # 比對；不一致 ⇒ rc≠0（fail-closed）
#
# 為何存在（2026-08-14）：使用者要求這份分類「絕對正確」。手寫表格下一刻就會漂，
# 故改為從 .claude/settings.json／scripts/git_hooks/／各呼叫端**實際掃描**導出，
# 並以 --check 掛產出端強制一致。
#
# 🔴 掛載判定以 **basename** 比對，非完整相對路徑——呼叫端常寫 "${SCRIPT_DIR}/x.sh"。
#   初版用相對路徑比對造成**偽陰性**：review_quorum_check（gate.sh:776）、
#   reconcile_stamps_check（gate.sh:368）、reconcile_cluster_attribution_check
#   （reconcile_build.sh）三支全被判成「未掛」，主委差點據此宣稱「文件說機器強制但實際沒掛」。
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

DOC="docs/GOV_ACTIVE_MECHANISMS.md"
MARK="gov-active-mechanisms"

_where() {   # $1=腳本路徑 → 掛載點（空白分隔；無則「未掛」）
  b="$(basename "$1")"; out=""
  ev="$(LC_ALL=C jq -r --arg s "${b}" '
    .hooks | to_entries[] | .key as $e | .value[] | .hooks[]
    | select((.command // "") | contains($s)) | $e' .claude/settings.json 2>/dev/null \
    | LC_ALL=C sort -u | tr '\n' ',' | sed 's/,$//')"
  [ -n "${ev}" ] && out="${out}${ev} "
  for h in pre-commit commit-msg pre-push; do
    LC_ALL=C grep -q "${b}" "scripts/git_hooks/${h}" 2>/dev/null && out="${out}${h} "
  done
  for c in gate.sh gov_check.sh committee_run.sh cx_run.sh reconcile_build.sh; do
    [ "${b}" = "${c}" ] && continue
    LC_ALL=C grep -q "${b}" "scripts/${c}" 2>/dev/null && out="${out}${c%.sh} "
  done
  printf '%s' "${out:-未掛}"
}

_kind() {    # $1=basename → 常態檢查／一次性驗證（封閉檔名樣式，非主觀判斷）
  case "$1" in
    verify_*_independent.sh|*_selftest.sh|test_*.sh|verify_b*fix*.sh) printf '一次性驗證' ;;
    install_*.sh|*_probe*.sh)                                         printf '工具' ;;
    *)                                                                printf '常態檢查' ;;
  esac
}

_emit() {
  echo "| 腳本 | 類別 | 掛載點（機械導出） |"
  echo "|---|---|---|"
  for f in scripts/*.sh scripts/*.py; do
    [ -f "${f}" ] || continue
    b="$(basename "${f}")"
    case "${b}" in *check*|*guard*|*verify*) : ;; *) continue ;; esac
    printf '| `%s` | %s | %s |\n' "${b}" "$(_kind "${b}")" "$(_where "${f}")"
  done
}

case "${1:-}" in
  --write)
    # 🔴 表格經**檔案**傳給 awk，不用 -v：awk 的 -v 不接受含換行之值
    #   （實測 "newline in string"；本專案已於 S0.6 踩過同一個坑）。
    tbl="$(mktemp)"; _emit > "${tbl}"
    tmp="$(mktemp)"
    LC_ALL=C awk -v mark="${MARK}" -v tblf="${tbl}" '
      $0 == "<!-- BEGIN GENERATED: " mark " -->" {
        print
        while ((getline l < tblf) > 0) print l
        close(tblf)
        skip = 1; next
      }
      $0 == "<!-- END GENERATED: " mark " -->" { skip = 0 }
      !skip { print }
    ' "${DOC}" > "${tmp}"
    # 🔴 fail-closed：產出必須非空、且兩個標記都在，否則**不寫入**。
    #   本腳本初版缺此保護：awk 因 -v 換行而失敗、產出空檔，cp 照樣覆蓋 ⇒ **把文件清成 0 行**。
    #   寫入型腳本一律先驗產出再落地，這是本專案其他腳本都有、唯獨此支漏掉的一條。
    if [ ! -s "${tmp}" ] \
       || ! LC_ALL=C grep -q "BEGIN GENERATED: ${MARK}" "${tmp}" \
       || ! LC_ALL=C grep -q "END GENERATED: ${MARK}" "${tmp}"; then
      echo "[mechanisms] 🔴 產出為空或缺標記 → 不寫入（原檔保留）" >&2
      rm -f "${tmp}" "${tbl}"; exit 3
    fi
    cp "${tmp}" "${DOC}"; rm -f "${tmp}" "${tbl}"
    echo "已寫入 ${DOC}"
    ;;
  --check)
    cur="$(LC_ALL=C awk -v mark="${MARK}" '
      $0 == "<!-- BEGIN GENERATED: " mark " -->" { inb=1; next }
      $0 == "<!-- END GENERATED: " mark " -->"   { inb=0 }
      inb { print }' "${DOC}" 2>/dev/null)"
    [ -n "${cur}" ] || { echo "[mechanisms] ${DOC} 缺生成區塊 → fail-closed" >&2; exit 1; }
    if [ "${cur}" != "$(_emit)" ]; then
      echo "[mechanisms] 🔴 ${DOC} 之掛載表與實況不一致 → fail-closed" >&2
      echo "  修：bash scripts/list_active_mechanisms.sh --write" >&2
      exit 1
    fi
    ;;
  --hook)
    # 產出端模式：只在**會改變掛載關係**的檔被改時才跑 --check（否則秒退）。
    # 受管集合為封閉列舉：hook 設定／git hooks／五個呼叫端／本文件／新增之 scripts 腳本。
    # 🔴 全量 --check 約 1.3 秒，對每次 Edit 都跑會疊在既有守衛之上 ⇒ 條件觸發。
    p="${2:-}"
    case "${p}" in
      .claude/settings.json|scripts/git_hooks/*|docs/GOV_ACTIVE_MECHANISMS.md) : ;;
      scripts/gate.sh|scripts/gov_check.sh|scripts/committee_run.sh|scripts/cx_run.sh|scripts/reconcile_build.sh) : ;;
      scripts/*.sh|scripts/*.py) : ;;
      *) exit 0 ;;
    esac
    out="$("$0" --check 2>&1)" || {
      printf '[mechanisms] 🔴 掛載一覽與實況不一致（你剛改了 %s）\n' "${p}" >&2
      printf '%s\n' "${out}" | sed 's/^/  /' >&2
      exit 2
    }
    ;;
  *) _emit ;;
esac
