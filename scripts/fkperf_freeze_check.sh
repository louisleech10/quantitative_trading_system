#!/usr/bin/env bash
# fkperf_freeze_check.sh — FKPERF 收案總驗收（docs/FKPERF_SPEC.md；manifest docs/manifests/FKPERF.json 之 gate_cmd）。
#
# 逐項跑、逐項印 PASS／FAIL，最後一行為總結；任一項 FAIL ⇒ rc=1。
# 不含全套 pytest tests/governance（小時級；SPEC Task 4.5 另以背景手動跑，見 manifest not_executable）。
set -u
cd "$(dirname "$0")/.." || exit 2
PY="venv/bin/python"; [ -x "${PY}" ] || PY="python3"
fail=0; n=0
MUT_RECEIPT="handoffs/run_receipts/$(date +%Y%m%d)-fkperf-mutation.json"  # SPEC Task 4.2 逐列收據
_item() {  # $1=名稱 $2...=指令
  local name="$1"; shift
  n=$((n + 1))
  if "$@" > /tmp/fkperf_freeze_item.$$ 2>&1; then
    echo "PASS ${name}"
  else
    echo "FAIL ${name}"; tail -5 /tmp/fkperf_freeze_item.$$ | sed 's/^/    /'
    fail=1
  fi
  rm -f /tmp/fkperf_freeze_item.$$
}
_item "SPEC 範本機檢"            bash scripts/template_check.sh spec docs/FKPERF_SPEC.md
_item "manifest 機檢"            bash scripts/template_check.sh todofmt docs/manifests/FKPERF.json
_item "差分驗收"                 "${PY}" -m pytest -q -p no:cacheprovider tests/governance/test_fkperf_differential.py
_item "規模驗收"                 "${PY}" -m pytest -q -p no:cacheprovider tests/governance/test_fkperf_scale.py
_item "入口切換驗收"             env FKPERF_MUTATION_RECEIPT="${MUT_RECEIPT}" "${PY}" -m pytest -q -p no:cacheprovider tests/governance/test_fkperf_cutover.py
_item "mutation 逐列收據"        jq -e ".rows | length > 0 and all(.[]; .mutant_rc == 1 and .restored_rc == 0 and .fail_substr_seen == true and .precondition_failed == false)" "${MUT_RECEIPT}"
_item "GOVB1 同等檢查"           "${PY}" -m pytest -q -p no:cacheprovider tests/governance/test_fkperf_govb1_equiv.py
_item "既有生成器測試"           "${PY}" -m pytest -q -p no:cacheprovider tests/governance/test_govb1_factkey_gen.py tests/governance/test_govb1_factkey_hook.py
_item "既有 DOCROT2 測試"        "${PY}" -m pytest -q -p no:cacheprovider tests/governance/test_docrot2_registry.py tests/governance/test_docrot2_migration.py tests/governance/test_docrot2_write_guard.py tests/governance/test_docrot2_metrics.py
_item "mutation 靜態探針"        "${PY}" scripts/mutation_probe_static.py tests/governance/test_fkperf_differential.py tests/governance/test_fkperf_scale.py tests/governance/test_fkperf_cutover.py tests/governance/test_fkperf_govb1_equiv.py
_item "生成器 --check"           bash scripts/gen_fact_key_blocks.sh --check
bash scripts/restore_golden_inventory.sh > /dev/null 2>&1 || true
if [ "${fail}" -eq 0 ]; then
  echo "FKPERF FREEZE PASS：${n} 項皆通過"
else
  echo "FKPERF FREEZE FAIL：${n} 項中有未通過者"
  exit 1
fi
