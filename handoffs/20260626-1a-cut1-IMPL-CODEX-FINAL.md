ASSUMPTIONS_VERIFIED: B3 root cause was invalid test fixture `max_fill_forward=0`; changed to valid default `3`. Flag remains default OFF. G-OLD baseline was not re-frozen and flag-off deep-equal passed with only `generated_at` popped.
TESTS_RUN: `pytest tests/momentum/Analysis/test_ic_1a_cut1_leakage.py -k 'train_only or legacy_no_mask' -q` PASS 5; `pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py -q` PASS 5; `pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py -q` PASS 25; `grep -rE "from api\." momentum/ | wc -l` → 0; `./scripts/check_decoupling_phase4.sh` PASS, including 135 strategy tests.
FAILURES_SEEN: B5 first run had one test helper bug in `test_flag_toggles_path` using data without `close`; fixed test label generation, no production-code workaround.
SCOPE_CHANGES: none beyond authorized B3-B5 implementation/tests; no service/frontend changes.
NUMERIC_OR_SCHEMA_IMPACT: flag-on adds OOS/train-test split behavior and report `scope=test`; flag-off G-OLD deep-equal PASS. No `data_cache/` tracked diff.

STATUS: DONE