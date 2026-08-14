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
  # 🔴 narrow_check_router.sh 於 2026-08-14 加入：它是 PostToolUse 的窄觸發路由器，
  #   其 _routes() 對照表就是「誰被掛上」的權威來源之一。漏了它 ⇒ 表列的檢查
  #   明明已上線卻仍顯示「未掛」（S6.1 抓過的同一種登記錯誤）。
  for c in gate.sh gov_check.sh committee_run.sh cx_run.sh reconcile_build.sh narrow_check_router.sh; do
    [ "${b}" = "${c}" ] && continue
    # 🔴 **排除註解行**：純 grep 會把「檔頭註解提到某支腳本」當成掛載。
    #   2026-08-14 實際發生：narrow_check_router.sh 的成本說明提到 check_doc_anchors.sh、
    #   邊界說明提到 factkey_write_guard.sh，兩支立刻被記成「經 narrow_check_router 掛載」——
    #   而它們根本不在 _routes() 表裡。本檔 §五.2 早已寫明「提及 ≠ 產出」，
    #   偏偏這支導出器自己犯了同一條。
    # 🔴 COMPOSER-R1-P2-01（沙箱實構）：只排整行 `#` 仍會把三種「提及」判成掛載——
    #   ①行尾註解 `echo ok  # scripts/x.sh` ②`: 'scripts/x.sh'` 區塊註解 ③heredoc 內字面量。
    #   ①②已於下方剝除；🔴 ③ **仍是具名邊界**：heredoc 內容在 shell 層無法只用 grep 分辨，
    #   要根治須做 shell 解析。現樹無此形態（已逐支確認），故列為已知邊界不強解。
    [ -f "scripts/${c}" ] || continue
    LC_ALL=C grep -v '^[[:space:]]*#' "scripts/${c}" 2>/dev/null \
      | LC_ALL=C sed -e 's/[[:space:]]#.*$//' -e '/^[[:space:]]*:[[:space:]]/d' \
      | LC_ALL=C grep -q "${b}" && out="${out}${c%.sh} "
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
    # 納入判準＝**檔名樣式 ∪ 自身宣告 --check 模式**。
    # 🔴 只用檔名是 proxy，會漏：`extract_phase2_expected_flips.py` 有 --check 卻因命名隱形，
    #   於 2026-08-14 掛載盤點時才發現它「不在清單上所以沒人知道它沒掛」。
    #   補法刻意**不是**把漏掉的檔名一個個加進來（黑名單永遠列不完），
    #   而是改成可導出的封閉述詞：宣告了 --check 就是有通過／不通過語意的檢查。
    case "${b}" in
      *check*|*guard*|*verify*) : ;;
      *) LC_ALL=C grep -qE '^[[:space:]]*(--check\)|"--check",?$)' "${f}" 2>/dev/null || continue ;;
    esac
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
    # 🔴 GROK-R1-P1-01（BLOCKING，實構命中）：原版只讀 `${2:-}`，
    #   但 `.claude/settings.json` 的 PostToolUse 是以 **stdin JSON** 餵 `tool_input.file_path`、
    #   **不帶 argv**。⇒ p 恆為空字串 ⇒ 落到 `*) exit 0` ⇒ **本守衛從未真正跑過**，
    #   是個掛著卻恆綠的空心格。體例改為與 factkey_write_guard.sh 一致：argv 優先、否則讀 stdin。
    p="${2:-}"
    if [ -z "${p}" ] && [ ! -t 0 ]; then
      p="$(python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit(0)
ti = d.get("tool_input") or {}
v = ti.get("file_path") or ti.get("path") or ""
print(v if isinstance(v, str) else "")' 2>/dev/null || true)"
      # 絕對路徑轉 repo 相對（hook 給的是絕對路徑；封閉列舉全是相對路徑）
      case "${p}" in
        "${PWD}"/*) p="${p#"${PWD}"/}" ;;
      esac
    fi
    case "${p}" in
      .claude/settings.json|scripts/git_hooks/*|docs/GOV_ACTIVE_MECHANISMS.md) : ;;
      scripts/gate.sh|scripts/gov_check.sh|scripts/committee_run.sh|scripts/cx_run.sh|scripts/reconcile_build.sh) : ;;
      scripts/*.sh|scripts/*.py) : ;;
      *) exit 0 ;;
    esac
    # 🔴 須以 `bash` 呼叫：本檔未必有可執行位（實測 Permission denied）。
    #   這個 bug 在 P1-01 的空心格修好之前**永遠不會被執行到** ⇒ 空心格會藏住下游缺陷。
    out="$(bash "$0" --check 2>&1)" || {
      printf '[mechanisms] 🔴 掛載一覽與實況不一致（你剛改了 %s）\n' "${p}" >&2
      printf '%s\n' "${out}" | sed 's/^/  /' >&2
      exit 2
    }
    ;;
  *) _emit ;;
esac
