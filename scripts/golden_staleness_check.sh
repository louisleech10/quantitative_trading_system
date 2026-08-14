#!/usr/bin/env bash
# golden_staleness_check.sh — golden／baseline 基準是否比「它守的程式」還舊。
#
# 🔴🔴🔴 **本工具的輸出目前不可採信，禁用於刪檔或判斷回歸**（2026-08-14 實測，主委自陳）。
#   首版跑出「STALE=32／ORPHAN=40」並向使用者報告後，使用者一句「你確定嗎」，
#   自我攻擊即找到**兩個各自獨立就足以推翻結論**的 bug：
#
#   ① **檔名碰撞**：`_gs_referrers` 以 basename grep 找引用者。實測 repo 內真的叫
#      `baseline.json` 的只有 2 個檔，但**提到該字串的測試檔有 14 個** ⇒ 所有 14 個都被
#      算成每一個 `baseline.json` 的引用者，於是把無關模組的 commit 日期拉進來當
#      「程式最後改動」。`failopen/baseline.json` 被報「程式 2026-07-22 改過」，
#      而 `momentum/FeatureEngineering/` **那天根本沒有 commit**。
#   ② **動態組路徑**：測試常以「目錄 ＋ f-string 檔名」讀基準（`GOLDEN_DIR / f"{sym}.parquet"`），
#      basename grep 抓不到 ⇒ **有在用的被判成 ORPHAN**。實測前三個「孤兒」所在目錄
#      被 4 個測試檔引用；照著清會直接弄壞測試。
#
#   🔴 **`--selftest` 當時是「通過」的——它為錯的理由通過**：只斷言 failopen 那列被標 STALE，
#      沒有驗證推導鏈。**弱 oracle 的綠燈等於沒有綠燈**，這是本檔最該記住的一條。
#
#   🔴 更根本的一條（使用者 2026-08-14 指出，邏輯上無反駁餘地）：
#      commit 日期反映的是「什麼時候提交」，不是「什麼時候改的」——本專案常態是
#      開發數日、commit 一次 ⇒ **拿它當「程式比基準新」的判準本來就不成立**。
#      且基準與測試**兩側都是 Claude 產的**，互相量測是循環論證。
#
#   ⇒ 保留本檔作為**問題的紀錄與後續修法的起點**，不作為判準。要用必須先修 ①②
#      並換掉日期判準，且自檢須驗**推導鏈**而非只驗標籤。
#
# ── 為何存在（2026-08-14，使用者定）────────────────────────────────────
# 使用者原話：「我之前就有說過測過不需要的腳本或過時的腳本就要作廢，你也不執行，
#   現在跑這個有什麼意義，跑完跟我說一個錯的答案，然後把寫好的程式翻掉？」
#
# 實際事故（本日親身）：主委跑全套量化測試，看到 `*_matches_frozen_baseline` 一批紅，
#   直接對使用者報「主線已經是紅的」。查證後：
#     · `tests/_golden/failopen/baseline.json` 凍結於 2026-06-18
#     · 它守的 `momentum/FeatureEngineering/` 於 2026-07-18 被**刻意**改行為
#       （`ic-la2` B1：winsorized label 禁用＋三層 fail-closed）
#   ⇒ 那些紅是**基準過期**，不是回歸。若照著「修紅」，會把 7/18 改對的行為
#     翻回一個月前的舊基準——**拿過期的尺去翻掉正確的程式**，比不跑還糟。
#
# ⇒ 本檢查回答一個問題：**這個基準現在還可信嗎？**
#   不可信的基準，它的紅與綠**都沒有意義**——綠也可能只是巧合。
#
# ── 判準（機械可導出，無主觀判斷）──────────────────────────────────
#   對每個基準檔 B：
#     ① 找出引用 B 的測試檔（grep basename，非註解行）
#     ② 自那些測試檔抽出它們 import 的專案模組（`from momentum…` / `from api…`）
#     ③ 取那些模組**最後一次 commit 的日期** M
#     ④ B 的最後 commit 日期 < M  ⇒ **STALE**（基準比它守的程式舊）
#
# ── 誠實邊界（逐條，不誇大）────────────────────────────────────────
#   1. **STALE ≠ 有 bug**。它只說「這個基準不能當判準用」，
#      至於該重凍還是該作廢，需要人看那次程式改動是不是刻意的。
#   2. 反過來**不成立**：基準比程式新，不保證它是對的（可能凍到錯的值）。
#      本檢查**只抓一個方向**，不宣稱涵蓋基準正確性。
#   3. 判準 ② 只看 import，抓不到「測試經 subprocess 跑腳本」那類間接依賴
#      ⇒ 該類會被判為 UNKNOWN（**不猜**），不會誤報成 OK。
#   4. 未被任何測試引用的基準 ⇒ ORPHAN（可能就是該作廢的那種）。
#   5. 日期取自 git，未 commit 的改動不算。
#
# 用法：
#   bash scripts/golden_staleness_check.sh            # 全表
#   bash scripts/golden_staleness_check.sh --stale    # 只列 STALE（rc=1 若有）
#   bash scripts/golden_staleness_check.sh --selftest # 自檢（用已知答案驗）
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

_mode="${1:-}"

_gs_last_commit_date() {   # $1=path → YYYY-MM-DD，取不到回空
  git log -1 --date=short --pretty=%ad -- "$1" 2>/dev/null
}

# 基準檔全集：golden/_golden 目錄下的資料檔 ∪ tests 下名含 baseline 的資料檔
# 🔴 只收**資料檔**（非 .py）——`test_*_baseline.py` 是測試碼不是基準。
_gs_baselines() {
  find tests -type f \
    \( -path "*/golden/*" -o -path "*/_golden/*" -o -name "*baseline*" \) \
    ! -name "*.py" ! -name "*.pyc" 2>/dev/null | LC_ALL=C sort
}

# 引用該基準的測試檔（非註解行）
_gs_referrers() {   # $1=basename
  LC_ALL=C grep -rl --include='test_*.py' -- "$1" tests/ 2>/dev/null | while IFS= read -r t; do
    LC_ALL=C grep -v '^[[:space:]]*#' "${t}" 2>/dev/null | LC_ALL=C grep -q -- "$1" && printf '%s\n' "${t}"
  done
}

# 測試檔 import 的專案模組 → 對應檔案路徑
_gs_guarded_paths() {   # $1=測試檔
  LC_ALL=C grep -hoE '^[[:space:]]*(from|import)[[:space:]]+(momentum|api)(\.[A-Za-z0-9_]+)*' "$1" 2>/dev/null \
    | LC_ALL=C sed -E 's/^[[:space:]]*(from|import)[[:space:]]+//' \
    | LC_ALL=C sort -u | while IFS= read -r m; do
        p="$(printf '%s' "${m}" | tr '.' '/')"
        [ -f "${p}.py" ] && printf '%s\n' "${p}.py"
        [ -d "${p}" ]    && printf '%s\n' "${p}"
      done
}

_gs_scan() {
  local b bn refs guarded newest d bd st any_stale=0
  while IFS= read -r b; do
    [ -n "${b}" ] || continue
    bn="$(basename "${b}")"
    bd="$(_gs_last_commit_date "${b}")"
    [ -n "${bd}" ] || { printf 'UNTRACKED\t%s\t-\t-\t%s\n' "-" "${b}"; continue; }

    refs="$(_gs_referrers "${bn}")"
    if [ -z "${refs}" ]; then
      printf 'ORPHAN\t%s\t-\t無測試引用\t%s\n' "${bd}" "${b}"
      continue
    fi

    newest=""
    while IFS= read -r t; do
      [ -n "${t}" ] || continue
      while IFS= read -r g; do
        [ -n "${g}" ] || continue
        d="$(_gs_last_commit_date "${g}")"
        [ -n "${d}" ] || continue
        [ "${d}" \> "${newest}" ] && newest="${d}"
      done <<EOF
$(_gs_guarded_paths "${t}")
EOF
    done <<EOF
${refs}
EOF

    if [ -z "${newest}" ]; then
      printf 'UNKNOWN\t%s\t-\t引用者未 import 專案模組（可能經 subprocess）\t%s\n' "${bd}" "${b}"
      continue
    fi

    if [ "${bd}" \< "${newest}" ]; then
      st="STALE"; any_stale=1
    else
      st="OK"
    fi
    printf '%s\t%s\t%s\t%s\t%s\n' "${st}" "${bd}" "${newest}" "$(printf '%s' "${refs}" | head -1)" "${b}"
  done <<EOF
$(_gs_baselines)
EOF
  return "${any_stale}"
}

_gs_report() {
  local out; out="$(_gs_scan)"; local rc=$?
  printf '%-9s %-11s %-11s %s\n' "狀態" "基準凍結" "程式最後改" "基準檔"
  printf '%s\n' "${out}" | LC_ALL=C awk -F'\t' '{ printf "%-9s %-11s %-11s %s\n", $1, $2, $3, $5 }'
  printf '\n'
  printf '%s\n' "${out}" | LC_ALL=C awk -F'\t' '
    { c[$1]++ } END { for (k in c) printf "%s=%d ", k, c[k]; print "" }'
  echo "🔴 STALE＝基準比它守的程式舊 ⇒ **該基準的紅與綠都不可信**（綠也可能只是巧合）。"
  echo "   處置需人看：那次程式改動若是刻意的 ⇒ 重凍基準；若該測試已無意義 ⇒ 作廢。"
  echo "🔴 ORPHAN＝沒有任何測試引用它。UNKNOWN＝引用者未 import 專案模組，本工具不猜。"
  return "${rc}"
}

# 🔴 自檢：用**已知答案**驗，不是驗它會不會跑。
#   已知事實（2026-08-14 人工查證）：tests/_golden/failopen/baseline.json 凍於 2026-06-18，
#   其引用者 import 的 momentum/FeatureEngineering 於 2026-07-18 被改 ⇒ 必須判 STALE。
_gs_selftest() {
  local out rc=0
  out="$(_gs_scan)"
  if printf '%s\n' "${out}" | LC_ALL=C grep -q "^STALE.*tests/_golden/failopen/baseline.json"; then
    echo "SELFTEST PASS: 已知的過期基準（failopen/baseline.json）被判為 STALE"
  else
    echo "SELFTEST FAIL: 已知過期基準未被判 STALE — 本工具的結論不可採信" >&2
    printf '%s\n' "${out}" | LC_ALL=C grep "failopen/baseline.json" >&2
    rc=1
  fi
  return "${rc}"
}

case "${_mode}" in
  --selftest) _gs_selftest ;;
  --stale)    _gs_scan | LC_ALL=C grep "^STALE" || { echo "無 STALE 基準"; exit 0; }; exit 1 ;;
  ""|--all)   _gs_report ;;
  *) echo "用法: bash scripts/golden_staleness_check.sh [--all|--stale|--selftest]" >&2; exit 2 ;;
esac
