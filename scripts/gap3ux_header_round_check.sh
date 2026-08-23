#!/usr/bin/env bash
# gap3ux_header_round_check.sh — SPEC 檔頭 current-round receipt 之機械閘
#
# 出處（CODEX-R16-P2-05）：SPEC 檔頭之「本行為單一 current-round receipt：每輪落地須同批
#   更新」自 R14 起是**散文**，靠主委自認觸發。而它正是 reviewer 判讀「現在到哪一輪」的依據
#   ——R14 抓到它自 R8 起停了六輪未更新。codex 主張此觸發面有限、可機械判定；
#   grok／composer 判「維持具名殘留」可接受。主委裁定採 codex 之可機械化子集＝本檔。
#
# 🔴 R17 重寫（CODEX-R17-P2-07）：R16 首版以「SPEC 有未提交改動」當唯一觸發，兩個 skip
#   分支 **fail-open**——①clean tree 直接 rc=0（**已提交之 stale header 擋不到**）
#   ②glob 找不到委員產出直接 rc=0（漏交產出反而變綠）。
#   改為以**債務帳本之輪次狀態**判定（可導出、與 worktree 狀態無關）：
#     · 最新一輪 state=CLOSED ⇒ 該輪**已落地** ⇒ 檔頭**必須等於**該輪（clean tree 也查）
#     · 最新一輪 state=OPEN   ⇒ 審查中或落地中 ⇒ 檔頭須 ∈ {N-1, N}；
#                                若 SPEC 另有未提交改動（＝正在落地）則**必須等於 N**
#     · 帳本中完全沒有本 epic 之輪次 ⇒ 真·新 epic 首輪，skip（唯一合法 skip）
#
# 🔴 **不採** codex 之另兩項（理由寫在 SPEC §N，供後續覆核）：
#   (b)「diff 出現 producer／transport／receipt／encoder／parallel fixture 字面即要求五欄包」
#       ——關鍵字黑名單，同 `_g2_regions` 一機制衍生四條旁路之型；codex 所指之封閉集合
#       是「機制種類」的集合，不是「diff 字面」的集合，兩者之對應才是未解的部分。
#   (c)「先問後做」——決定「不先問」不會在任何 diff 留下痕跡，結構上不可觀測。
#       （CODEX-R17-P2-08 提出以 consult receipt 之 ancestry 觀測；見 §N 之 R17 處置）
#
# 用法：bash scripts/gap3ux_header_round_check.sh
# rc: 0=通過或不適用；2=fail-closed（檔頭落後／格式不可解析／帳本不可解析）
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

SPEC=docs/GAP3_EVENT_UX_SPEC.md
EPIC_RE='gap3ux-x-review-r'
[ -f "${SPEC}" ] || { echo "[header_round] ✗ 找不到 ${SPEC}"; exit 2; }

# ── ① 解析檔頭輪次；格式不可解析或多於一行 ⇒ fail-closed
hdr_lines=$(grep -c '^\*\*版本\*\*：R[0-9]\{1,\}-landing' "${SPEC}")
if [ "${hdr_lines}" -ne 1 ]; then
  echo "[header_round] ✗ 檔頭 current-round receipt 不是恰好一行（實得 ${hdr_lines} 行）"
  echo "               期望格式：**版本**：R<n>-landing（…）"
  exit 2
fi
hdr_round=$(grep -o '^\*\*版本\*\*：R[0-9]\{1,\}-landing' "${SPEC}" | head -1 |
            sed 's/^\*\*版本\*\*：R//; s/-landing$//')

# ── ② 由債務帳本取本 epic 之最大輪次與其狀態（不靠 handoffs glob）
ledger="$(bash scripts/debt_ledger.sh --list 2>/dev/null)"
led_rc=$?
if [ "${led_rc}" -ne 0 ]; then
  echo "[header_round] ✗ 無法讀取債務帳本（debt_ledger --list rc=${led_rc}）⇒ fail-closed"
  exit 2
fi

max_round=""
max_state=""
while IFS= read -r line; do
  case "${line}" in *"${EPIC_RE}"*) ;; *) continue;; esac
  n=$(printf '%s\n' "${line}" | sed -n "s/.*${EPIC_RE}\([0-9]\{1,\}\).*/\1/p")
  s=$(printf '%s\n' "${line}" | sed -n 's/.*state=\([A-Z]\{1,\}\).*/\1/p')
  [ -n "${n}" ] || continue
  if [ -z "${max_round}" ] || [ "${n}" -gt "${max_round}" ]; then
    max_round="${n}"; max_state="${s}"
  fi
done <<EOF
${ledger}
EOF

if [ -z "${max_round}" ]; then
  echo "[header_round] （債務帳本中無本 epic 之輪次 ⇒ 真·新 epic 首輪，不適用）"
  exit 0
fi
[ -n "${max_state}" ] || {
  echo "[header_round] ✗ 帳本可讀但 state 欄不可解析（round=R${max_round}）⇒ fail-closed"; exit 2; }

# ── ③ SPEC 是否有未提交改動（＝正在落地）
git diff --quiet -- "${SPEC}";        rc_wt=$?   # 🔴 rc 直接取，禁經 pipe
git diff --cached --quiet -- "${SPEC}"; rc_st=$?
dirty=0
[ "${rc_wt}" -eq 0 ] && [ "${rc_st}" -eq 0 ] || dirty=1

# ── ④ 判定
prev=$((max_round - 1))
fail() {
  echo "[header_round] ✗ 檔頭 current-round receipt 不符"
  echo "               檔頭＝R${hdr_round}-landing"
  echo "               帳本最新輪次＝R${max_round}（state=${max_state}）；SPEC dirty=${dirty}"
  echo "               ${1}"
  echo "               （出處 CODEX-R14：該行自 R8 起停了六輪，會誤導 reviewer 判讀 FROZEN 狀態；"
  echo "                 R17 由 worktree 觸發改為帳本狀態觸發，CODEX-R17-P2-07）"
  exit 2
}

if [ "${max_state}" = "CLOSED" ]; then
  # 該輪已收案 ⇒ 落地應已完成，檔頭必須等於它（**clean tree 也查**，這是 R17 封的洞）
  [ "${hdr_round}" -eq "${max_round}" ] || fail "已收案之輪次要求檔頭＝R${max_round}-landing"
else
  # OPEN：審查中（檔頭＝R$prev）或落地中（檔頭應已改為 R$max_round）
  if [ "${dirty}" -eq 1 ]; then
    [ "${hdr_round}" -eq "${max_round}" ] || \
      fail "SPEC 有未提交改動（＝正在落地）⇒ 檔頭必須先改為 R${max_round}-landing"
  else
    [ "${hdr_round}" -eq "${max_round}" ] || [ "${hdr_round}" -eq "${prev}" ] || \
      fail "審查中允許 R${prev} 或 R${max_round}，實得 R${hdr_round}"
  fi
fi

echo "[header_round] ✓ 檔頭＝R${hdr_round}-landing｜帳本最新＝R${max_round}(${max_state})｜dirty=${dirty}"
exit 0
