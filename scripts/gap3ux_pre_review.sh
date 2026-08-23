#!/usr/bin/env bash
# gap3ux_pre_review.sh — 派審前之一鍵閘（GAP3UX-PRE-REVIEW，2026-08-23）
#
# 出處＝R3 consult 三家共識（GROK Q2 之 S3、Q3 之「主委必須做」）：
#   「主委必須做：套用補丁後跑 scripts/gap3ux_pre_review.sh（包裝三閘＋locus）」
#
# 為何存在：主委七輪自傷 21 條，其中 3 條是「新增了一支閘卻沒把它加進檢查清單」
#   （R6 群集 F 三→四、R7 群集 A 四→五，同型相鄰兩輪各犯一次）。
#   ⇒ 把「該跑哪些閘」收斂成**單一入口**，不再散落在 brief／receipt／記憶裡。
#   🔴 **新增任何 GAP-3 UX 相關機械閘，必須加進本檔**——這是唯一清單。
#
# 用法：
#   bash scripts/gap3ux_pre_review.sh                    # 只跑規格三閘＋計數閘
#   bash scripts/gap3ux_pre_review.sh <patch.md> [...]   # 另加 locus 對證
# rc: 0=全綠；非 0=有閘紅（逐條列出）
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

SPEC=docs/GAP3_EVENT_UX_SPEC.md
FACTS=handoffs/20260823-gap3ux-x-review-r7-facts.sh
BASE=handoffs/run_receipts/gap3ux-spec-count-baseline.txt

fail=0
run() {  # run <名稱> <命令...>
  local name="$1"; shift
  "$@" > /tmp/.gap3ux_gate.$$ 2>&1
  local rc=$?          # 🔴 rc 直接取，禁經 pipe（CLAUDE.md 已載此坑）
  if [ "${rc}" -eq 0 ]; then
    printf '  ✓ %-28s rc=0\n' "${name}"
  else
    printf '  ✗ %-28s rc=%d\n' "${name}" "${rc}"
    sed -n '1,6p' /tmp/.gap3ux_gate.$$ | sed 's/^/      /'
    fail=1
  fi
  rm -f /tmp/.gap3ux_gate.$$
}

echo "[gap3ux_pre_review] 標的：${SPEC}"
run "doc_format_precheck"   bash scripts/doc_format_precheck.sh "${SPEC}"
run "spec_ruling_task_sync" bash scripts/spec_ruling_task_sync.sh "${SPEC}"
run "spec_v_task_ref_check" bash scripts/spec_v_task_ref_check.sh "${SPEC}"
run "quant_standard_check"  bash scripts/quant_standard_check.sh
run "spec_count_audit"      python3 scripts/spec_count_audit.py --check "${SPEC}" "${FACTS}" --baseline "${BASE}"

if [ "$#" -gt 0 ]; then
  echo "[gap3ux_pre_review] 補丁包 locus 對證（$# 份）"
  run "patch_locus_check" python3 scripts/patch_locus_check.py "$@"
else
  echo "[gap3ux_pre_review] （未傳補丁包 ⇒ 跳過 locus 對證）"
  echo "  ⚠️ 若本次 commit 觸及 ${SPEC}，依 R3 consult 之角色卡須附補丁包或 ERRATA id"
fi

if [ "${fail}" -eq 0 ]; then
  echo "[gap3ux_pre_review] ✅ 全綠，可派審"
  exit 0
fi
echo "[gap3ux_pre_review] ❌ 有閘未過，禁派審（見上）" >&2
exit 2
