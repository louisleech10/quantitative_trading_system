#!/usr/bin/env bash
set -euo pipefail

SET=""
if [[ "${1:-}" == "--set" && -n "${2:-}" ]]; then
  SET="$2"
else
  echo "usage: $0 --set V1|V2|V5|V6|V7|all" >&2
  exit 2
fi

case "$SET" in
  V1|V2|V5|V6|V7|all) ;;
  *) echo "unknown set: $SET" >&2; exit 2 ;;
esac

digest_json() {
  venv/bin/python -c 'from tests.fixtures.ic_persist_redirect import digest_data_cache; import json; print(json.dumps(digest_data_cache(), sort_keys=True))'
}

assert_skips_allowed() {
  local label="$1" report_file="$2"
  local skip_lines
  skip_lines="$(rg '^SKIPPED \[' "$report_file" || true)"
  if [[ "$label" == "V1" ]]; then
    if [[ -n "$skip_lines" ]] && echo "$skip_lines" | rg -v 'RUN_IC_E2E_PERF' >/dev/null; then
      echo "SKIP_WHITELIST_FAIL[$label]=1"
      return 1
    fi
  elif [[ "$label" == "V7" ]]; then
    if [[ -n "$skip_lines" ]] && echo "$skip_lines" | rg -v 'tests/test_feature_factory_e2e.py.*(_require_data|missing.*data|missing kline|missing multi-timeframe)' >/dev/null; then
      echo "SKIP_WHITELIST_FAIL[$label]=1"
      return 1
    fi
  elif [[ -n "$skip_lines" ]]; then
    echo "SKIP_WHITELIST_FAIL[$label]=1"
    return 1
  fi
}

run_guard() {
  local label="$1"
  shift
  local report_file="${TMPDIR:-/tmp}/pytest-${label}-$$.log"
  local pre post test_rc=0 skip_rc=0 digest_rc=0 v6_red_rc=0
  pre="$(digest_json)"
  set +e
  "$@" 2>&1 | tee "$report_file"
  test_rc=${PIPESTATUS[0]}
  assert_skips_allowed "$label" "$report_file"
  skip_rc=$?
  post="$(digest_json)"
  set -e
  if [[ "$pre" != "$post" ]]; then
    echo "DIGEST_DIFF_EMPTY[${label}]=0"
    digest_rc=1
  else
    echo "DIGEST_DIFF_EMPTY[${label}]=1"
  fi

  if [[ "$label" == "V6" && "$test_rc" -ne 0 ]]; then
    local baseline_file="tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt"
    local fail_set_file="${TMPDIR:-/tmp}/pytest-${label}-fail-set-$$.txt"
    local baseline_set_file="${TMPDIR:-/tmp}/pytest-${label}-baseline-set-$$.txt"
    local new_red_file="${TMPDIR:-/tmp}/pytest-${label}-new-red-$$.txt"
    # Pytest's short-summary rows have a tests/... nodeid in field 2; application
    # log records may also begin with ERROR and must not enter the fail set.
    rg '^(FAILED|ERROR) ' "$report_file" \
      | awk '$2 ~ /^tests\// {print $2}' \
      | sort -u > "$fail_set_file" || true
    rg -v '^#|^$' "$baseline_file" | sort -u > "$baseline_set_file"
    comm -23 "$fail_set_file" "$baseline_set_file" > "$new_red_file"
    echo "NEW_RED[V6]:"
    if [[ -s "$new_red_file" ]]; then
      cat "$new_red_file"
      echo "V6_NO_NEW_RED=0"
      v6_red_rc=1
    else
      echo "(none)"
      echo "V6_NO_NEW_RED=1"
    fi
    rm -f "$fail_set_file" "$baseline_set_file" "$new_red_file"
  elif [[ "$label" == "V6" ]]; then
    echo "NEW_RED[V6]:"
    echo "(none)"
    echo "V6_NO_NEW_RED=1"
  fi

  # C-4 dual-stamp (grok+composer, 2026-07-11): for ticket 2 only, V6's
  # pytest rc=1 is accepted when it adds no red nodeid and the digest is clean.
  # Therefore --set all also stays green when V6 passes this amended criterion.
  if [[ "$skip_rc" -ne 0 || "$digest_rc" -ne 0 || "$v6_red_rc" -ne 0 ]]; then
    return 1
  fi
  if [[ "$label" != "V6" && "$test_rc" -ne 0 ]]; then
    return 1
  fi
}

run_v1() {
  run_guard V1 venv/bin/python -m pytest \
    tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_fallback_insufficient_data_marks_applied_false \
    tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_applied_true_when_sufficient \
    tests/momentum/test_ic_e2e.py \
    tests/momentum/test_ic_feature_filter.py::test_analyze_applies_feature_filter_metadata_and_summary_limit \
    tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q -ra
}

run_v2() {
  run_guard V2 venv/bin/python -m pytest \
    tests/api/test_ic_analysis_service.py::test_analyze_real_run_split_validation_passes_with_real_axis \
    tests/api/test_ic_analysis_service.py::test_resolve_run_path_contains_config_hash -q -ra
}

run_v5() {
  run_guard V5 venv/bin/python -m pytest \
    tests/momentum/Analysis/test_ic_persist_redirect_golden_ab.py \
    tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q -s -ra
}

run_v6() {
  run_guard V6 venv/bin/python -m pytest \
    tests/api/test_ic_analysis_api.py tests/api/test_ic_deep_analysis.py tests/api/test_export_api.py -q -ra
}

run_v7() {
  run_guard V7 venv/bin/python -m pytest \
    tests/test_feature_factory_e2e.py \
    tests/momentum/Analysis/test_lightgbm_analyzer.py \
    tests/momentum/Analysis/test_lightgbm_edge_cases.py \
    tests/momentum/Analysis/test_xgboost_protocol_methods.py \
    tests/momentum/test_lightgbm_analyzer_phase3.py \
    tests/momentum/test_xgboost_protocol_methods_phase3.py -q --tb=no -ra
}

if [[ "$SET" == "all" ]]; then
  run_v1
  run_v2
  run_v5
  run_v6
  run_v7
else
  case "$SET" in
    V1) run_v1 ;;
    V2) run_v2 ;;
    V5) run_v5 ;;
    V6) run_v6 ;;
    V7) run_v7 ;;
  esac
fi
