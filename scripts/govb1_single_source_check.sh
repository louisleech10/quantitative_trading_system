#!/usr/bin/env bash
# govb1_single_source_check.sh — §0.1b「判準單一來源」之機械 guard
#
# 病史：「原則修了、實例沒修」本 session 已 13 次；前四次對策皆為紀律
#   （四面比對／先刪後補／單條通讀／單一來源表）⇒ 全部失效。
#
# 🔴 **本腳本第一版也犯了同一個病**：以「已廢判準 token 黑名單」掃全檔，
#    把現行資料結構 `_CHECKS`、無關旗標 `--review-role` 全部誤報。
#    ⇒ **用關鍵字偵測散文＝列舉，永遠列不完。**
#
# 改採**正向斷言**（可機械判、無列舉）：
#   「凡消費判準之位置，其文字必須含指向 §0.1b 之 pointer」。
#   缺 pointer ⇒ FAIL。**不判斷該處寫了什麼**，只判斷「有沒有指回唯一來源」。
#
# 誠實邊界（具名，不解）：
#   本檢查擋不住「有 pointer 但旁邊又寫了一段互斥判準」。
#   完整解＝把判準移出 markdown 進資料檔並以 generated block ＋ diff 強制
#   （與 `票 B-25` 之 fact-key 同型），**屬後續票，不在本批**。
#
# ── 票↔Task 歸屬（W′，2026-08-08）────────────────────────────
# 機械權威唯一來源＝`scripts/govb1_task_tickets.tsv`（`meta` 宣告）。
# 🔴 **不再讀 TODO §0.1a** 作歸屬判定（否則仍是兩份權威）。
# §0.1a 為待生成之投影；過渡期禁止手改（見 TSV 檔頭註解）。
set -u
TODO="${GOVB1_TODO:-docs/GOVB1_INPUT_QUALITY_TODO.md}"
TICKETS="${GOVB1_TASK_TICKETS:-scripts/govb1_task_tickets.tsv}"
rc=0

# §0.1b 必須存在
grep -q '^### 0\.1b ' "${TODO}" \
  || { echo "FAIL: 找不到 §0.1b（判準單一來源表）" >&2; exit 1; }

# 判準消費點（由結構定位，非人手列舉）：
#   ①§0.2 之 G-2 列  ②`_g2_consumers()` 之定義區塊
_pointer_re='§0\.1b'

_g2_row="$(grep -n '^| G-2 |' "${TODO}" || true)"
[ -n "${_g2_row}" ] || { echo "FAIL: 找不到 §0.2 之 G-2 列" >&2; exit 1; }
printf '%s\n' "${_g2_row}" | grep -q "${_pointer_re}" \
  || { echo "FAIL: G-2 列未指向 §0.1b（判準應只在 §0.1b 陳述）" >&2
       printf '%s\n' "${_g2_row}" | cut -c1-140 >&2; rc=1; }

_g2fn="$(awk '/^_g2_consumers\(\)/{f=1} f{print} f&&/^}/{exit}' "${TODO}")"
[ -n "${_g2fn}" ] || { echo "FAIL: 找不到 _g2_consumers() 區塊" >&2; exit 1; }
printf '%s\n' "${_g2fn}" | grep -q "${_pointer_re}" \
  || { echo "FAIL: _g2_consumers() 未指向 §0.1b" >&2; rc=1; }

# ── 票↔Task 歸屬完整性（TSV 機械權威）────────────────────────
# 用法：`--task <N.M>` 只驗該 Task；不帶則驗 TSV 涵蓋 TODO 全部 Task。
# 誠實邊界：只驗「有沒有填合法值」，**不驗「填得對不對」**（那要讀 Task 意圖，屬審查）。
#
# ticket 合法值：`—`（確實不對應單一票）或 `B-NN` 等具名票。
# 非法值：空、`未標註`、`待確認`。
[ -f "${TICKETS}" ] \
  || { echo "FAIL: 缺歸屬 TSV ${TICKETS}（fail-closed）" >&2; exit 1; }

_task_ticket_from_tsv() {   # $1=Task 編號 → stdout: ticket 欄；無列則空
  # 跳過 # 註解與表頭；tab 分隔；$2=task $3=ticket
  awk -F'\t' -v t="${1}" '
    /^#/ || /^[ \t]*$/ { next }
    $1=="batch" && $2=="task" { next }
    $2 == t { print $3; exit }
  ' "${TICKETS}"
}

_check_task_ticket() {
  _t="$1"
  _ticket="$(_task_ticket_from_tsv "${_t}")"
  if [ -z "${_ticket}" ]; then
    # 區分「列不存在」vs「ticket 欄為空」：再查 task 欄是否出現
    if ! awk -F'\t' -v t="${_t}" '
          /^#/ || /^[ \t]*$/ { next }
          $1=="batch" && $2=="task" { next }
          $2 == t { found=1; exit }
          END { exit !found }
        ' "${TICKETS}"; then
      echo "FAIL: 歸屬 TSV 無 Task ${_t} 之列（表未涵蓋該 Task）" >&2
      echo "  TSV=${TICKETS}" >&2
      return 1
    fi
    echo "FAIL: Task ${_t} 之歸屬票為空 ⇒ 不得派工。" >&2
    echo "  合法值：—（不對應單一票）或 B-NN；不得寫空白／未標註／待確認。" >&2
    return 1
  fi
  case "${_ticket}" in
    未標註|待確認|*未標註*|*待確認*)
      echo "FAIL: Task ${_t} 之歸屬票仍為「未標註／待確認」⇒ 不得派工。" >&2
      echo "  理由：無歸屬票 ⇒ 無法機械證明「本批 N 張票被 M 個 Task 完全覆蓋」，" >&2
      echo "        既可能有票沒人修，也可能有 Task 做了沒票要求的事（scope 膨脹）。" >&2
      echo "" >&2
      echo "  🔴 解鎖路徑（**不是死鎖**，本閘只擋 impl 派工）：" >&2
      echo "   1. 派一輪 consult（**不帶 --todo，本閘不擋**）請三家依 Task 意圖裁定歸屬票" >&2
      echo "   2. 依裁定更新 scripts/govb1_task_tickets.tsv 該列（§0.1a 為投影，過渡期禁手改）" >&2
      echo "   3. 重跑本檢查應轉 PASS" >&2
      echo "  🔴 **主委不得自行推測**：內文第一個出現的票號常為交叉引用而非歸屬" >&2
      echo "     （如 Task 2.1 之 \`票 B-23\`、Task 3.1 之 \`票 B-6\` 皆不在本批八張內）。" >&2
      echo "     「只看誰沒歸類就填空」＝ 2026-08-07 兩次對帳配反之根因。" >&2
      echo "  📌 本閘**不擋**其他批次之 Task；歸屬票已具名者照常放行（如 Task 0.1）。" >&2
      return 1 ;;
  esac
  # 「—」與 B-NN 等具名值皆 PASS
  return 0
}

if [ "${1:-}" = "--task" ]; then
  [ -n "${2:-}" ] || { echo "FAIL: --task 需帶 Task 編號（如 0.1）" >&2; exit 2; }
  _check_task_ticket "${2}" || rc=1
  [ "${rc}" -eq 0 ] && echo "PASS: Task ${2} 之歸屬票已具名（TSV）"
  exit "${rc}"
fi

# 全表模式：TSV 必須涵蓋 TODO 內全部 ^### Task N.M（現讀導出，禁寫死清單）
_all_tasks="$(grep -ohE '^### Task [0-9]+\.[0-9]+' "${TODO}" | sed 's/^### Task //' | LC_ALL=C sort -u)"
_missing=""
while IFS= read -r t; do
  [ -n "${t}" ] || continue
  if ! awk -F'\t' -v tt="${t}" '
        /^#/ || /^[ \t]*$/ { next }
        $1=="batch" && $2=="task" { next }
        $2 == tt { found=1; exit }
        END { exit !found }
      ' "${TICKETS}"; then
    _missing="${_missing} ${t}"
  fi
done <<EOF
${_all_tasks}
EOF
[ -z "${_missing}" ] || { echo "FAIL: 歸屬 TSV 未涵蓋 Task:${_missing}" >&2; rc=1; }

# 全表亦驗每列 ticket 值合法（空／未標註／待確認 ⇒ FAIL）
while IFS= read -r t; do
  [ -n "${t}" ] || continue
  _check_task_ticket "${t}" || rc=1
done <<EOF
${_all_tasks}
EOF

[ "${rc}" -eq 0 ] && echo "PASS: 判準消費點皆指向 §0.1b；歸屬 TSV 涵蓋全部 Task"
exit "${rc}"
