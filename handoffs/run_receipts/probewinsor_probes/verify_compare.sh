#!/usr/bin/env bash
# 驗 affected_compare.py 之 fail-closed：真實輸入通過；缺 --ratiounsafe、空歸因、RATIOUNSAFE 不等皆不通過
set -u
R=/Users/louis/Desktop/quantitative_trading_system
S=/private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/b433f210-2afd-44b3-b365-54a46b211dec/scratchpad
PY="${R}/venv/bin/python"
C="${R}/handoffs/run_receipts/probewinsor_probes/affected_compare.py"
RU="${R}/handoffs/run_receipts/probewinsor_probes/out/ratiounsafe_ppoff_fixed.json"
AT="${R}/handoffs/run_receipts/probewinsor_probes/affected_attribution.json"
cd "${R}" || exit 2
echo '{"tests/feature_engineering/test_tf_aligner.py::test_hash_changes_with_align_version": {}}' > "${S}/attr_empty.json"
jq '.equal = false | .arms.on.equal = false | .arms.on.diff_keys = ["columns"]' "${RU}" > "${S}/ru_bad.json"
"${PY}" "${C}" "${S}/affected" anchor fixed --ratiounsafe "${RU}" --attribution "${AT}" --receipt "${S}/rc_ok.json" > /dev/null 2>&1
echo "真實輸入 rc=$?（預期 0）"
"${PY}" "${C}" "${S}/affected" anchor fixed --attribution "${AT}" --receipt "${S}/rc_nru.json" > /dev/null 2>&1
echo "缺 --ratiounsafe rc=$?（預期非 0）"
"${PY}" "${C}" "${S}/affected" anchor fixed --ratiounsafe "${RU}" --attribution "${S}/attr_empty.json" --receipt "${S}/rc_empty.json" > /dev/null 2>&1
echo "空歸因 rc=$?（預期 1）；errors=$(jq -c '.attribution_errors' "${S}/rc_empty.json")"
"${PY}" "${C}" "${S}/affected" anchor fixed --ratiounsafe "${S}/ru_bad.json" --attribution "${AT}" --receipt "${S}/rc_rubad.json" > /dev/null 2>&1
echo "RATIOUNSAFE 不等 rc=$?（預期 1）；errors=$(jq -c '.ratiounsafe_errors' "${S}/rc_rubad.json")"
