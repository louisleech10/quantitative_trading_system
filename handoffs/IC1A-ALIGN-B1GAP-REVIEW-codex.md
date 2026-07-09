# IC1A-ALIGN-B1GAP-REVIEW codex
TASK_ID: ic1a-align-b1gap-review
SCOPE: review diff in contracts.py, ic_filter_orchestrator.py, test_alignment_contract.py
STATUS: review complete

FINDINGS:
- NONE/BLOCKING: no blocking issues found.
- NONE/NON-BLOCKING: no non-blocking issues found.

RECEIPTS:
- simple formula: LabelGenerator.generate_return is close.shift(-horizon)/close-1; inline check formula_equal=True and validate_alignment simple checked_samples=23.
- alignment tests: pytest tests/momentum/core/test_alignment_contract.py -q -> 19 passed.
- cross-kind mutation: PYTHONPATH=$PWD pytest /tmp/ic1a_oracle_mutation_test.py -q with log oracle pointed at simple lambda -> FAILED with DID NOT RAISE; mutation exit=1, shell asserted nonzero.
- fail-closed: inline check excess/risk_adjusted/winsorized with close all raised unsupported oracle return_kind; no-close returned Tier1 checked_samples=0 gap_count=0.
- orchestrator golden: pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q -> 2 passed, 3 warnings.
- assertion weakening: git diff --unified=0 tests/momentum/core/test_alignment_contract.py shows only added tests/assertions, no existing assertion removal or weakening.

DECISIONS:
- APPROVE: ORACLE_RETURN_KINDS gates Tier-2 close passing; unsupported types stay Tier-1 unless caller incorrectly supplies close, then fail closed.
- APPROVE: log caller behavior covered by existing golden path; no observed byte/golden regression.

OUTPUTS:
- handoffs/IC1A-ALIGN-B1GAP-REVIEW-codex.md

VERDICT: APPROVE
Verdict: APPROVE
