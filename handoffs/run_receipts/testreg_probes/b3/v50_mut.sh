#!/bin/bash
# v50 驗收 (t) 之 mutation：拿掉外掛 autouse 遍歷（CODEX-R48-P1-01 之單行 mutant）⇒ (t) 須轉紅；(s) 對照。
W=/private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/9fa03a2f-8653-4b8d-a632-cc80fa7b1e68/scratchpad/wt_v50
cd "$W" || exit 2
f=scripts/testreg.py
cp "$f" /private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/9fa03a2f-8653-4b8d-a632-cc80fa7b1e68/scratchpad/testreg_v50_backup.py
[ "$(grep -c 'info\["auto"\] + used' "$f")" = 1 ] || { echo "anchor missing"; exit 2; }
sed -i '' 's/info\["auto"\] + used/used/' "$f"
echo "== M9 (autouse traversal removed) =="
venv/bin/python -m pytest -p no:cacheprovider -q \
  "tests/registry/test_testreg_repair_additive.py::test_t_session_scope_plugin_autouse_param_fixture_not_enumerable" \
  "tests/registry/test_testreg_repair_additive.py::test_s_session_scope_plugin_param_fixture_not_enumerable" 2>&1 | grep -E "passed|failed|PASSED|FAILED" | tail -4
cp /private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/9fa03a2f-8653-4b8d-a632-cc80fa7b1e68/scratchpad/testreg_v50_backup.py "$f"
git diff --quiet HEAD -- "$f" && echo "restore-check: unexpected clean" || echo "restored to trial"
