#!/usr/bin/env bash
# gap3ux_header_round_check.sh — SPEC 檔頭 current-round receipt 之機械閘（R16 新建）
#
# 出處（CODEX-R16-P2-05）：SPEC 檔頭之「本行為單一 current-round receipt：每輪落地須同批
#   更新」自 R14 起是**散文**，靠主委自認觸發。而它正是 reviewer 判讀「現在到哪一輪」的依據
#   ——R14 抓到它自 R8 起停了六輪未更新。codex 主張此觸發面有限、可機械判定；
#   grok／composer 判「維持具名殘留」可接受。
#
# 🔴 主委裁決（兩造之間，非第三方案；理由亦寫入 SPEC §N 供 R17 覆核）：
#   · **採 codex** 之可機械化子集＝本檔（檔頭輪次落後）。觸發面確實封閉：
#     「SPEC 有未提交改動」× 「檔頭輪次 ≠ 已有委員產出之最大輪次」，兩者皆為可導出值。
#   · **不採** codex 之另兩項：
#     (b) 「diff 出現 producer／transport／receipt／encoder／parallel fixture 字面即要求五欄包」
#         ——那是**關鍵字黑名單**，正是 `_g2_regions` 一機制衍生四條旁路的同型；
#         codex 所指之封閉集合是「機制種類」的集合，不是「diff 字面」的集合，
#         兩者之對應關係才是未解的部分 ⇒ 維持具名殘留（needs-research）。
#     (c) 「先問後做」——決定「不先問」這件事不會在任何 diff 裡留下痕跡，結構上不可觀測。
#
# 用法：bash scripts/gap3ux_header_round_check.sh
# rc: 0=通過或不適用；2=fail-closed（檔頭落後／格式不可解析）
#
# 🔴 誠實邊界（刻意不擋，寫明以免被當成保證）：
#   · SPEC 未被改動時本檔**不檢查**（rc=0）——它守的是「落地當下」，不是任意時刻。
#   · 同一輪若分成兩個 commit 落地，第二個 commit 時檔頭已等於最大輪次 ⇒ 仍 rc=0（正確）。
#   · 尚無任何委員產出時（新 epic 首輪派工前）⇒ 印訊息並 rc=0（無基準可比）。
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

SPEC=docs/GAP3_EVENT_UX_SPEC.md
[ -f "${SPEC}" ] || { echo "[header_round] ✗ 找不到 ${SPEC}"; exit 2; }

# ── ① 是否處於「落地當下」＝ SPEC 有未提交改動（working tree 或 staged）
git diff --quiet -- "${SPEC}"
rc_wt=$?                       # 🔴 rc 直接取，禁經 pipe（CLAUDE.md 已載此坑）
git diff --cached --quiet -- "${SPEC}"
rc_st=$?
if [ "${rc_wt}" -eq 0 ] && [ "${rc_st}" -eq 0 ]; then
  echo "[header_round] （${SPEC} 無未提交改動 ⇒ 非落地當下，不適用）"
  exit 0
fi

# ── ② 解析檔頭輪次；格式不可解析或多於一行 ⇒ fail-closed
hdr_lines=$(grep -c '^\*\*版本\*\*：R[0-9]\{1,\}-landing' "${SPEC}")
if [ "${hdr_lines}" -ne 1 ]; then
  echo "[header_round] ✗ 檔頭 current-round receipt 不是恰好一行（實得 ${hdr_lines} 行）"
  echo "               期望格式：**版本**：R<n>-landing（…）"
  exit 2
fi
hdr_round=$(grep -o '^\*\*版本\*\*：R[0-9]\{1,\}-landing' "${SPEC}" | head -1 |
            sed 's/^\*\*版本\*\*：R//; s/-landing$//')

# ── ③ 已有委員產出之最大輪次（三家任一份即算該輪存在）
max_round=""
for f in handoffs/*gap3ux-x-review-r*-codex.md \
         handoffs/*gap3ux-x-review-r*-composer.md \
         handoffs/*gap3ux-x-review-r*-grok.md; do
  [ -f "${f}" ] || continue
  n=$(printf '%s\n' "${f}" | sed -n 's/.*-review-r\([0-9]\{1,\}\)-[a-z]*\.md$/\1/p')
  [ -n "${n}" ] || continue
  if [ -z "${max_round}" ] || [ "${n}" -gt "${max_round}" ]; then max_round="${n}"; fi
done

if [ -z "${max_round}" ]; then
  echo "[header_round] （尚無任何委員產出 ⇒ 無基準可比，不適用）"
  exit 0
fi

# ── ④ 判定
if [ "${hdr_round}" -ne "${max_round}" ]; then
  echo "[header_round] ✗ 檔頭 current-round receipt 落後／不符"
  echo "               檔頭＝R${hdr_round}-landing　已有委員產出之最大輪次＝R${max_round}"
  echo "               修：把 ${SPEC} 之「**版本**：」行同批更新為 R${max_round}-landing"
  echo "               （出處 CODEX-R14：該行自 R8 起停了六輪，會誤導 reviewer 判讀 FROZEN 狀態）"
  exit 2
fi

echo "[header_round] ✓ 檔頭＝R${hdr_round}-landing，與最大委員輪次一致"
exit 0
