#!/bin/bash
S=/private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/929a358b-897c-4786-82fe-c60c3cf83d65/scratchpad
W=$S/wt_4bdc2d56
cd "$W" || exit 9
run_one() {
  export BISECT_FILE="$1" BISECT_K="$2"
  git bisect reset > /dev/null 2>&1
  git bisect start bcb04a5b 4bdc2d56 > /dev/null 2>&1
  git bisect run bash "$S/bisect_run.sh" 2>&1 | grep -E "is the first bad commit" -A1 | head -2
  git bisect reset > /dev/null 2>&1
}
echo "== mutation_scope"
run_one tests/governance/test_mutation_scope_extension.py "test_true_positive_i_quant_fatal_set_is_the_named_12"
echo "== fftfmeta_sample"
run_one tests/governance/test_todofmt_sample_fftfmeta.py "test_boundary_03_callers_now_empty_callers_later_nonempty or test_boundary_06_each_case_has_named_test or test_coverage_risk_lists_each_equation_with_named_test"
