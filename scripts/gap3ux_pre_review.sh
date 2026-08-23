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
#   bash scripts/gap3ux_pre_review.sh                    # 只跑常駐閘（清單見下方 run 呼叫）
#   bash scripts/gap3ux_pre_review.sh <patch.md> [...]   # 另加 locus 對證
# 🔴 本檔與任何文件一律**不寫閘數**——閘數字面漂移已犯三次（R6 三→四、R7 四→五、R8 清單分歧）。
#    要知道跑了哪些閘，看下方 `run "..."` 之呼叫序列，那是唯一清單。
# rc: 0=全綠；非 0=有閘紅（逐條列出）
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

SPEC=docs/GAP3_EVENT_UX_SPEC.md
# 🔴 R8 群集 H：計數稽核之掃描面與呼叫方式**唯一來源＝scripts/gap3ux_count_check.sh**。
#    原本此處與 narrow_check_router 各寫一份、且寫死輪次（`…-r7-facts.sh`）
#    ⇒ 「加閘／換檔未同步清單」第三、四次。本檔不得自帶參數清單。

fail=0
LOG=".claude/gate/gap3ux_pre_review.last.log"
mkdir -p "$(dirname "${LOG}")" 2>/dev/null
: > "${LOG}"

run() {  # run <名稱> <命令...>
  local name="$1"; shift
  "$@" > /tmp/.gap3ux_gate.$$ 2>&1
  local rc=$?          # 🔴 rc 直接取，禁經 pipe（CLAUDE.md 已載此坑）
  if [ "${rc}" -eq 0 ]; then
    printf '  ✓ %-28s rc=0\n' "${name}"
  else
    printf '  ✗ %-28s rc=%d\n' "${name}" "${rc}"
    # 🔴 2026-08-23：原本此處為 `sed -n '1,6p'`，**截斷輸出**。
    #    實際後果（主委當場踩到）：一次傳四份補丁包跑 locus 對證，前兩份的未達 locus
    #    就把六行用完，**後兩份的未達 locus 完全不顯示** ⇒ 主委一度判定「後兩份全過」。
    #    這是報告層的 fail-open，與 R8 那三個假綠同型（工具自己騙自己）。
    #    ⇒ 一律全量輸出；量大時看 ${LOG} 之完整副本。
    sed 's/^/      /' /tmp/.gap3ux_gate.$$
    cat /tmp/.gap3ux_gate.$$ >> "${LOG}"
    fail=1
  fi
  rm -f /tmp/.gap3ux_gate.$$
}

echo "[gap3ux_pre_review] 標的：${SPEC}"
run "doc_format_precheck"   bash scripts/doc_format_precheck.sh "${SPEC}"
run "spec_ruling_task_sync" bash scripts/spec_ruling_task_sync.sh "${SPEC}"
run "spec_v_task_ref_check" bash scripts/spec_v_task_ref_check.sh "${SPEC}"
run "quant_standard_check"  bash scripts/quant_standard_check.sh
run "spec_count_audit"      bash scripts/gap3ux_count_check.sh
# 🔴 R16（CODEX-R16-P2-05）：檔頭 current-round receipt 由散文改為機械閘。
#    主委裁決之範圍與**不採**的兩項（關鍵字黑名單／先問後做），理由寫在該檔頭註解與 SPEC §N。
run "spec_header_round"     bash scripts/gap3ux_header_round_check.sh

if [ "$#" -gt 0 ]; then
  # 🔴 R9（CODEX-R9-P1-06／GROK-R9-P1-04；三家議題一裁定）：補丁包 locus 對證新增 stage 維度。
  #    · SYNC-LOCI 每列可加 `@spec`／`@doc`／`@harness`／`@impl`，**缺省＝@spec**（最嚴）。
  #    · 未達之 `@impl` 印 DEFERRED、不計 rc（凍前不實作）。
  #    · 呼叫端只有 `--also-impl` 這個**加寬**旗標；**本檔不得**新增任何縮窄旗標
  #      （角色卡：不得為降噪收窄掃描面）。實作階段驗收時由呼叫者自行加 `--also-impl`。
  #    · commit 後複驗須帶 `--diff-base <套用前 ref>`，否則已落地之 locus 會被誤報未改動。
  #    · 另修 patch_locus_check 之 CJK 路徑假紅（git 之 core.quotepath；GROK-R9-P1-04）。
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
