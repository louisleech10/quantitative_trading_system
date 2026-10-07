#!/bin/bash
# 用法：attrib_worktree.sh <commit> <worktree 目錄> <log>；在指定 commit 之 worktree 跑第 2 段之 12 項失敗節點（以檔＋-k 名稱過濾）
C="$1"; W="$2"; LOG="$3"
REPO=/Users/louis/Desktop/quantitative_trading_system
cd "$REPO" || exit 9
[ -d "$W" ] || git worktree add -f "$W" "$C" > /dev/null 2>&1 || { echo "worktree fail" > "$LOG"; exit 7; }
[ -e "$W/data_cache" ] || ln -s "$REPO/data_cache" "$W/data_cache"
[ -e "$W/venv" ] || ln -s "$REPO/venv" "$W/venv"
cd "$W" || exit 9
venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/governance/test_mutation_scope_extension.py \
  tests/governance/test_todofmt_constitution_sync.py \
  tests/governance/test_todofmt_sample_fftfmeta.py \
  -k "test_true_positive_i_quant_fatal_set_is_the_named_12 or test_step1b_no_new_exception_clause_outside_allowlist or test_boundary_03_callers_now_empty_callers_later_nonempty or test_boundary_06_each_case_has_named_test or test_coverage_risk_lists_each_equation_with_named_test" \
  -rfEX > "$LOG" 2>&1
echo "PYTEST_RC=$? COMMIT=$C" >> "$LOG"
