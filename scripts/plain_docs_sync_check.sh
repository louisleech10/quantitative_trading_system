#!/usr/bin/env bash
# plain_docs_sync_check.sh — 白話說明/ 過期偵測（產出端強制，非靠紀律）
#
# 為何存在（2026-08-05 使用者三次指出，逐次逼出更正確的設計）：
#   ①「白話說明和日誌你忘記或沒做即時更新，就斷了」
#   ②「你也是只會記得更新 README，其他檔案也不一定會記得？
#      而且這個腳本也是要你記得用才會比對，忘記也是沒有？」
#   三個缺陷、三次修正：
#     (a) 只檢查 README   → 改為**逐檔**檢查（見 MANAGED）
#     (b) 腳本要記得跑     → 接進 `scripts/gov_check.sh`（pre-push 唯一委派點）⇒ 忘記也會跑
#     (c) 判準只驗「有沒有動過」→ **實測證偽**：文件先更新、實作後改，仍算動過而放行，
#         **順序完全沒驗**。改為**比新舊**（見下），且**不再需要人工維護 SYNCED-AT 標記**。
#   本專案第 3 條治理原則＝工具必須自帶強制機制，不准靠紀律和記憶。
#
# 判準（可機械算，無主觀，無需人工標記）：
#   對每個受管檔 f 與其 WATCHED 路徑集合 w：
#     last_w = 最後一個觸及 w 的 commit；last_f = 最後一個觸及 f 的 commit
#     若 last_w 存在，且 last_w **不是** last_f 的祖先（含相等）⇒ f 過期。
#   ⇒ 語意＝「實作動了之後，說明檔必須也動過」。同一 commit 內同時改亦視為同步。
#
# 誠實邊界（勿宣稱超出）：
#   1. 只驗**時序**，**不驗內容是否真的反映現況**——可只改一字換綠燈。
#   2. `git push --no-verify` 或 `GOVERNANCE_SKIP_PREPUSH=1` 可繞過。
#   ⇒ 屬「擋意外不防蓄意」，與本 repo 既有機檢同級。內容正確性仍靠審查。
#
# 憲法：bash 3.2；禁 declare -A（用 case 分派）；rc 直接取禁經 pipe；不新增狀態檔。
set -u

REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "ERROR: 非 git repo（fail-closed）" >&2; exit 2; }
cd "${REPO}" || exit 2

DIR="白話說明"
[ -d "${DIR}" ] || { echo "[plain_docs_sync] 略過（無 ${DIR}/）"; exit 0; }

# 受管檔（不含 Archived/；已封存者不再要求同步）
#
# 2026-08-05 晚間追加 治理進度日誌.md：
#   初版刻意把它排除，理由是使用者說過「日誌我不會去看」。
#   **兩天後它就真的斷了**——日誌停在規格 R4，其間走完 R5–R7＋TODO 三輪＋B0–B3，
#   而本腳本一路回報全綠（因為它根本不在受管清單裡）。
#   使用者主動察覺並質問「日誌和總覽你有沒打算要更新」⇒ 靠人眼補上了機器該擋的洞。
#   「使用者不看」是**閱讀習慣**，不是「可以不維護」——兩者被初版混為一談。
# 🔴 受管清單改為**現讀導出**，不再人手列舉（2026-08-07）
#   出生事故：第 1 批新增 `第1批-在做什麼.md`／`第1批-施工清單.md` 兩檔，
#   舊版是硬編字串 ⇒ **新檔天生不受管**，而我在摩擦記錄裡寫的修法是「得記得手動加」——
#   **那正是本批在治的病，出現在治它的工具上**。
#   改為：資料夾內所有 `.md` 皆受管（Archived/ 除外）。新增批次不需要有人記得回來加一行。
_managed_list() {
  ( cd "${PLAIN_DIR:-白話說明}" 2>/dev/null && ls *.md 2>/dev/null | LC_ALL=C sort )
}
MANAGED="$(_managed_list)"
[ -n "${MANAGED}" ] || { echo "ERROR: 白話說明/ 無任何 .md（fail-closed）" >&2; exit 1; }

_watched_for() {
  # bash 3.2 無 declare -A ⇒ case 分派
  case "$1" in
    # 🔴 前綴由 `docs/GOVB0_` 放寬為 `docs/GOV`（2026-08-07）：
    #    原設定只看第 0 批之 `GOVB0_*`，**第 1 批之 `docs/GOVB1_*` 完全不在監看範圍**
    #    ⇒ 整個第 1 批（SPEC／TODO 定版、設計與實作收斂）期間本守衛皆 rc=0，
    #    使用者打開白話說明看到的仍是數輪之前的狀態。**機制存在但沒接到現在的批次上。**
    #    修法用**前綴**而非逐批列舉——第 2、3 批之 `GOVB2_`／`GOVB3_` 自動涵蓋，
    #    不需要有人記得回來加一行（列舉永遠列不完）。
    "治理待辦總覽.md")               echo "handoffs/20260801-GOV-AMEND-BACKLOG.md" ;;
    "第0批-在做什麼.md")             echo "docs/GOVB0_FRICTION_SPEC.md" ;;
    # 🔴 樣式分派（非逐檔列舉）：`第N批-*.md` 與其餘治理說明檔一律看同一組路徑。
    #    新增批次之說明檔自動取得 WATCHED，不需要有人記得回來加一行。
    第*批-*.md)                       echo "scripts/ docs/GOV tests/governance/" ;;
    "README.md"|"治理進度日誌.md"|"流程摩擦記錄.md"|"接下來要做什麼.md")
                                      echo "scripts/ docs/GOV tests/governance/" ;;
    # 量化主線 ICHC epic 白話檔（2026-08-17）：看板盯憲章與閘門腳本；偵察結果盯缺口 registry
    "IC健檢施工進度.md")             echo "docs/IC_HEALTHCHECK_SPEC.md docs/IC_HEALTHCHECK_TODO.md scripts/ic_wiring_check.py" ;;
    # GAP-1 施工看板：WATCHED 含 scripts/（gap1 探針）⇒ 合法持有批次進度；實作路徑動了就必須同步
    "GAP-1施工進度.md")              echo "momentum/Analysis/strategy_validation/ momentum/core/frequency.py momentum/Analysis/contracts/strategy_validation_contract.json scripts/gap1_b1_mutation_probe.sh docs/GAP1_STRATEGY_OVERFIT_TODO.md docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md" ;;
    "IC健檢偵察結果.md")             echo "docs/IC_QUANT_GAP_REGISTRY.md" ;;
    # GAP-2 施工看板（2026-08-18）：盯新模組／契約／探針／TODO／延伸檔
    "GAP-2施工進度.md")              echo "momentum/Analysis/marginal_ic.py momentum/Analysis/factor_combiner.py momentum/Analysis/survivor_contract.py momentum/Analysis/contracts/ic_survivor_contract.json scripts/gap2_mutation_probe.sh scripts/gap2_freeze_golden.py docs/GAP2_MARGINAL_IC_TODO.md docs/GAP2_MARGINAL_IC_AMENDMENTS.md" ;;
    # GAP-3 施工看板（2026-08-21）：盯事件樣本模組／契約／測試／凍結 TODO 與 D 延伸檔／§G 凍結腳本（B2.3 建）
    # 2026-08-22 加入 `docs/GAP3_EVENT_UX_SPEC.md`：UAT 缺口修補 SPEC 之每輪修訂都要讓看板跟著動，
    #   否則使用者看到的仍是 B1–B5 收案時的狀態（＝摩擦八十二之同一病）。
    "GAP-3施工進度.md")              echo "momentum/Analysis/event_samples/ momentum/Analysis/contracts/event_import_contract.json tests/momentum/event_samples/ scripts/gap3_freeze_golden.py docs/GAP3_EVENT_TODO.md docs/GAP3_EVENT_TODO.D-001.md docs/GAP3_EVENT_UX_SPEC.md" ;;
    # GAP-3 事件型討論文檔（2026-08-19；使用者：「先寫成一個文檔，討論就修改文檔」）：盯缺口 registry 與 consult 收斂檔；
    #   日後 GAP-3 SPEC 出現時把 SPEC 路徑加進來（SPEC 定版前本檔是討論的唯一落點）。
    "GAP-3事件型討論.md")            echo "docs/IC_QUANT_GAP_REGISTRY.md handoffs/reconcile/20260819-gap3-x-consult-r1/synth.md handoffs/20260819-gap3-recon-BRIEF.md" ;;
    # GAP-3 委員意見對應檔（2026-08-19；逐項對應討論檔 U/J/K/S/T/P/G 編號）：盯 R2 收斂檔與 R2 brief
    "GAP-3事件型討論-委員意見.md")   echo "handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md handoffs/20260819-gap3-consult-r2-BRIEF.md" ;;
    # 42 Task 勾選表（2026-08-23 使用者要求）：盯 UX SPEC——Task 增減時本表必須跟著動，
    #   否則使用者看到的是過期的範圍清單（正是本表要治的病）。
    "GAP-3規格42個Task勾選表.md")    echo "docs/GAP3_EVENT_UX_SPEC.md" ;;
    # R11：凍結進度之白話總覽——盯 SPEC 本體（規格一改，「還差什麼」必須跟著重講）
    "GAP-3還差什麼才算完整.md")      echo "docs/GAP3_EVENT_UX_SPEC.md" ;;
    # 🔴 42 Task 施工看板（2026-08-24 使用者指出「沒有施工進度追蹤」而建）：
    #   由 FROZEN TODO ＋ 其 D 延伸檔**機械產生**（`scratchpad/gen_board2.py`），禁手抄。
    #   盯 TODO 與延伸檔——批次或 Task 一動，看板必須跟著重生，否則使用者看到的是過期批次。
    #   另盯事件樣本模組與測試：實作開跑後每個 Task 之狀態改變都源自那裡。
    "GAP-3施工看板.md")              echo "docs/GAP3_EVENT_UX_TODO.md docs/GAP3_EVENT_UX_TODO.D-001.md momentum/Analysis/event_samples/ tests/momentum/event_samples/" ;;
    # 🔴 具名殘留：catch-all 回空字串＝**新增的說明檔預設不受監看**，會靜默過期。
    #   這與本檔上方「列舉永遠列不完」的設計哲學矛盾，但改成預設監看是行為變更，
    #   需先量誤報面（同 `票 B-23` 紀律）。在那之前，**新增說明檔須手動加進上面的樣式或列舉**。
    *)                                echo "" ;;
  esac
}

# ── --staged 模式（pre-commit 用）───────────────────────
# 判準：本次 staged 檔案若命中某受管檔的 WATCHED，該受管檔**必須也在同一次 staged**。
# 為何要有這層（2026-08-05 使用者要求「想辦法能確保自己更新」）：
#   只掛 pre-push 的話，要等到 push 才發現，那時 commit 訊息都寫完了 ⇒ 回饋太晚。
#   pre-commit 在**當下**擋住，且語意更嚴（要求同 commit，而非「之後補」）。
if [ "${1:-}" = "--staged" ]; then
  # 🔴 必須 -c core.quotepath=false：否則中文路徑被逃脫成 "\347\231\275…"，
  #    比對永遠失敗 ⇒ 每次都誤報「說明檔沒帶到」，訓練使用者忽略提醒（比不報更糟）。
  #    出生事故：2026-08-05 本檔上線首次 commit 即誤報；同型 quotepath 陷阱當日第 3 次
  #    （另兩次：誤判遠端無重複檔、grep 中文檔名無效）。
  staged="$(git -c core.quotepath=false diff --cached --name-only --diff-filter=ACMR)"
  [ -n "${staged}" ] || { echo "[plain_docs_sync] (staged) 無 staged 檔，略過"; exit 0; }

  src=0
  for name in ${MANAGED}; do
    f="${DIR}/${name}"
    watched="$(_watched_for "${name}")"
    [ -n "${watched}" ] || continue

    hit=0
    for w in ${watched}; do
      case "${staged}" in
        *"${w}"*) hit=1; break ;;
      esac
    done
    [ "${hit}" -eq 1 ] || continue

    case "${staged}" in
      *"${f}"*) continue ;;
    esac

    src=1
    echo "[plain_docs_sync] ✗ (staged) ${f} 未一併更新" >&2
    echo "    本次 staged 命中其 WATCHED（${watched}），但該說明檔不在 staged 內。" >&2
  done

  if [ "${src}" -ne 0 ]; then
    echo "  ⇒ 現在更新該說明檔並 git add 最省事；否則 push 時會被硬擋。" >&2
    echo "  出處：使用者 2026-08-05「想辦法能確保自己更新白話說明的文檔」。" >&2
    echo "" >&2
    echo "  🔴 **本層是提醒，不擋 commit**（刻意設計）：若說明檔這次確實無需更動，" >&2
    echo "     硬擋會逼人養成用逃生口的習慣，反而使機制失效。" >&2
    echo "     真正的強制在 pre-push（gov_check 4/4）——**時序判準，繞不過去**：" >&2
    echo "     說明檔的最後更新不得早於其 WATCHED 的最後改動。" >&2
    exit 0
  fi
  echo "[plain_docs_sync] ✓ (staged) 白話說明 與本次改動同步"
  exit 0
fi

rc=0
stale_n=0
n_managed=0

# ── 進度單一出處（2026-08-05 使用者：「有些更新有些又沒有，搞不清楚你在做什麼」）──
# 事故：第0批-在做什麼.md 內含「現在進度」表，寫著「實作 ⬜ 還沒開始」時實際已完成 4 批。
#   本腳本抓不到，因為該檔 WATCHED=規格（凍結後永不變動）。
#   ⇒ 錯在「把會變的進度，塞進監看不會變之來源的檔」。
# 不變式：**只有 WATCHED 含 scripts/ 的受管檔可以寫批次進度**（它們才會隨實作過期）。
#   其餘受管檔出現進度表 ⇒ 該進度必然無人看管 ⇒ fail-closed。
_has_progress_markers() {
  grep -nE '批做完|^\| *實作 *\||^\| *驗收 *\|' "$1" 2>/dev/null
}

for name in ${MANAGED}; do
  f="${DIR}/${name}"
  [ -f "${f}" ] || continue
  case "$(_watched_for "${name}")" in
    *scripts/*) continue ;;                 # 進度合法持有者
  esac
  hits="$(_has_progress_markers "${f}")"
  if [ -n "${hits}" ]; then
    echo "ERROR: ${f} 含批次進度，但其 WATCHED 不含 scripts/ ⇒ 進度會過期且無人看管" >&2
    echo "${hits}" | sed 's/^/    /' >&2
    echo "    修：把進度移回 README.md／第0批-施工清單.md，本檔只留指標連結。" >&2
    rc=2
  fi
done

for name in ${MANAGED}; do
  f="${DIR}/${name}"
  n_managed=$((n_managed + 1))

  if [ ! -f "${f}" ]; then
    echo "ERROR: 受管檔缺失: ${f}（fail-closed；若已封存請自 MANAGED 移除並註明）" >&2
    rc=2
    continue
  fi

  watched="$(_watched_for "${name}")"
  if [ -z "${watched}" ]; then
    echo "ERROR: ${name} 無 WATCHED 定義（fail-closed）" >&2
    rc=2
    continue
  fi

  # shellcheck disable=SC2086
  last_w="$(git log --format=%H -1 -- ${watched})"
  [ -n "${last_w}" ] || continue          # WATCHED 從未被改 ⇒ 無需同步

  last_f="$(git log --format=%H -1 -- "${f}")"
  if [ -z "${last_f}" ]; then
    echo "[plain_docs_sync] ✗ 過期: ${f}（尚未進版控，但其 WATCHED 已有改動）" >&2
    stale_n=$((stale_n + 1))
    rc=1
    continue
  fi

  # last_w 是 last_f 的祖先（或相等）⇒ 說明檔不早於實作 ⇒ 同步
  if git merge-base --is-ancestor "${last_w}" "${last_f}" 2>/dev/null; then
    continue
  fi

  stale_n=$((stale_n + 1))
  [ "${rc}" -eq 2 ] || rc=1               # 硬錯（rc=2）不得被「過期」降級
  echo "[plain_docs_sync] ✗ 過期: ${f}" >&2
  echo "    其 WATCHED（${watched}）最後改動 ${last_w:0:8}，晚於本檔最後更新 ${last_f:0:8}" >&2
  echo "    WATCHED 的該次改動：" >&2
  git log --format='      %h %s' -1 "${last_w}" >&2
done

if [ "${rc}" -eq 0 ]; then
  echo "[plain_docs_sync] ✓ 白話說明 全數同步（受管 ${n_managed} 檔，判準＝說明檔不早於其 WATCHED）"
elif [ "${rc}" -eq 1 ]; then
  echo "  ⇒ ${stale_n} 個檔過期。修：更新該檔內容並與實作同 commit（或之後）提交。" >&2
  echo "  出處：使用者 2026-08-05「其他檔案也不一定會記得」「忘記也是沒有」。" >&2
fi
exit "${rc}"
