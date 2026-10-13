#!/usr/bin/env bash
# 驗 affected_compare.py 之 fail-closed（審碼 r1 CODEX-R1-P1-01／02；r2 CODEX-R2-P1-01：逐案斷言預期 rc 與收據欄位，任一不符 ⇒ exit 1）：
#   ①真實輸入 rc 0 且 pass=True ②缺 --ratiounsafe rc 2 ③空歸因 rc 1 且 attribution_errors 非空、pass=False
#   ④RATIOUNSAFE 一臂不等 rc 1 且 ratiounsafe_errors 非空、pass=False
# 用法：bash verify_compare.sh <兩輪 junit 與進度之 out_dir> <暫存目錄>
set -u
OUT="${1:?out_dir}"; TMP="${2:?tmp_dir}"
R="$(cd "$(dirname "$0")/../../.." && pwd)"
PY="${R}/venv/bin/python"
C="${R}/handoffs/run_receipts/probewinsor_probes/affected_compare.py"
RU="${R}/handoffs/run_receipts/probewinsor_probes/out/ratiounsafe_ppoff_fixed.json"
AT="${R}/handoffs/run_receipts/probewinsor_probes/affected_attribution.json"
# 每次執行用新建之子目錄（r3 CODEX-R3-P1-01：重用同目錄時舊收據會讓「本次未寫收據」之變體假綠）
mkdir -p "${TMP}" && RUN="$(mktemp -d "${TMP}/run.XXXXXX")" || { echo "建暫存子目錄失敗"; exit 2; }
fails=0
check() {  # check <案名> <實得 rc> <預期 rc> [<jq 條件> <收據>]
  local name="$1" got="$2" want="$3"
  if [ "${got}" != "${want}" ]; then
    echo "FAIL ${name}：rc=${got}（預期 ${want}）"; fails=$((fails + 1)); return
  fi
  if [ $# -ge 5 ] && ! jq -e "$4" "$5" > /dev/null 2>&1; then
    echo "FAIL ${name}：收據不合 $4"; fails=$((fails + 1)); return
  fi
  echo "OK   ${name}：rc=${got}"
}
cd "${R}" || exit 2
echo '{"tests/feature_engineering/test_tf_aligner.py::test_hash_changes_with_align_version": {}}' > "${RUN}/attr_empty.json"
jq '.equal = false | .arms.on.equal = false | .arms.on.diff_keys = ["columns"]' "${RU}" > "${RUN}/ru_bad.json"

"${PY}" "${C}" "${OUT}" anchor fixed --ratiounsafe "${RU}" --attribution "${AT}" --receipt "${RUN}/rc_ok.json" > /dev/null 2>&1
check "真實輸入" "$?" 0 '.pass == true and .attribution_errors == [] and .ratiounsafe_errors == []' "${RUN}/rc_ok.json"
"${PY}" "${C}" "${OUT}" anchor fixed --attribution "${AT}" --receipt "${RUN}/rc_nru.json" > /dev/null 2>&1
check "缺 --ratiounsafe" "$?" 2
"${PY}" "${C}" "${OUT}" anchor fixed --ratiounsafe "${RU}" --attribution "${RUN}/attr_empty.json" --receipt "${RUN}/rc_empty.json" > /dev/null 2>&1
check "空歸因" "$?" 1 '.pass == false and (.attribution_errors | length) > 0' "${RUN}/rc_empty.json"
"${PY}" "${C}" "${OUT}" anchor fixed --ratiounsafe "${RUN}/ru_bad.json" --attribution "${AT}" --receipt "${RUN}/rc_rubad.json" > /dev/null 2>&1
check "RATIOUNSAFE 不等" "$?" 1 '.pass == false and (.ratiounsafe_errors | length) > 0' "${RUN}/rc_rubad.json"

[ "${fails}" -eq 0 ] || { echo "verify_compare：${fails} 案不符"; exit 1; }
echo "verify_compare：4 案皆符"
