# B1 Worker Logging — Codex Review

Verdict: PASS WITH MINOR CAVEAT. 6 adversarial findings are materially addressed; no blocking correctness/numeric issue found.

Reviewed: `git show 58797f1` impl, `git show fbbd8cb` tests, `docs/B1_WORKER_LOGGING_SPEC.md`, `handoffs/20260619-b1-adv-codex.md`.

Checks:
- adv#1 idempotent: same-process repeated init does not duplicate handler/log line.
- adv#2 namespace attach: handler added to `momentum`/`api`; root handlers/list and root level not changed.
- adv#4 fail-open: tests cover FileHandler raise still calls generation; generation raise still propagates as compute failure.
- adv#3 smoke: committed ProcessPool smoke asserts json.loads/id-set/no dup/partial for parent+1..4 children.
- adv#5 generate_features call: args unchanged; only env/init wrapper added around existing call.
- adv#6 env restore: previous None/value and ProcessPool init failure covered.
- Numeric: `python scripts/build_l65_golden_baseline.py --check` PASS locally.

Local verification:
- `pytest tests/api/test_worker_logging.py -q`: 9 pass, 4 smoke fail in managed sandbox at ProcessPool semaphore permission (`SC_SEM_NSEMS_MAX`), before assertions.
- Ad hoc subprocess smoke (no ProcessPool semaphore): parent+4 child JSON lines parse, exact id set, no dup/partial.
- `pytest tests/api/ -k "worker_logging or worker_log_env" -q`: collection blocked by unrelated Binance network imports in route tests.

Findings:
1. MINOR — `init_worker_logging()` idempotence is too broad for future process reuse. After one marked handler exists, later init with a different path/symbol/tf returns early, so logs keep first file/context. Current wave uses max_workers=len(items), so this is not blocking for B1, but helper does not satisfy the stronger path+pid identity described in adv#1.

防假綠:
- New tests assert behavior, not only call presence.
- Smoke test is real multiprocess in normal env, but not runnable in this sandbox due OS semaphore restriction.
- No existing assertions were loosened in these commits.

SCOPE_CHANGES: none.
NUMERIC_OR_SCHEMA_IMPACT: none observed; byte check PASS.
STATUS: DONE
