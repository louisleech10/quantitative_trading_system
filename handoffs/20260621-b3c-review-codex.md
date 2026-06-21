# B3c Review — Codex (2026-06-21)

## Verdict
PASS with test-fidelity gaps. 224e896 implements the required real-free backpressure and resume reconcile semantics; 295abbe adds meaningful path tests, but disk path is not directly asserted at `shutil.disk_usage(features_root)` and crash-C discard-after-delete retry is inferred rather than directly covered.

## Findings
1. [OK] Backpressure uses real disk free: `_disk_free_bytes()` calls `shutil.disk_usage(path).free`; `_read_disk_free_bytes()` passes `_resolve_features_root()` = `settings.data_cache_path / "features"` (`api/services/feature_factory_batch_service.py:1785-1824`).
2. [OK] Wakeup rereads free bytes: successful retain/discard calls `_try_wakeup_from_disk_backpressure()`, which reloads checkpoint and calls `_evaluate_disk_backpressure()` before deciding resume/pause/hard-pause (`:1765-1767`, `:1900-1923`).
3. [OK] `free<reserve` + pending pauses; `free<reserve` + no pending sets observable `paused_disk_hard` and persists `disk_backpressure.action=hard_pause` (`:1826-1898`). This is terminal in practice because no pending decision remains to wake it.
4. [OK] Crash (a) resume reconcile marks completed registered-but-uncovered items pending without register/recompute; existing retained/discarded/pending are skipped, so idempotent (`:1960-2021`). Tests include helper and real `resume_batch()` path.
5. [OK] Crash (b) pending/deciding with missing artifact converges to discarded on resume (`:1966-1979`). Tests include helper and real `resume_batch()` path.
6. [OK/Gap] Crash (c) checkpoint write fail returns 5xx and retry is idempotent for retain (`tests/api/test_batch_retention.py:1251-1294`). Discard-after-delete + checkpoint write fail is not directly tested; code should converge on retry via `delete_run` KeyError catch (`:1737-1757`), but this exact path is unasserted.
7. [Gap] Backpressure tests patch `_read_disk_free_bytes()` (`tests/api/test_batch_retention.py:959-986`), not `shutil.disk_usage`; they prove behavior/wakeup sequencing, but not the actual measurement path or `features_root` argument. Add one small unit test patching `shutil.disk_usage` and asserting path.
8. [OK] No diff touched `momentum/` generation path, post-hoc register timing, decision atomic implementation, public `delete_run` route semantics, or generation parameters. 224e896 only changes batch service; 295abbe only tests + prior Composer handoff.

## Review Notes
- Tests not rerun by Codex; this was a read-only code review plus handoff write.
- Pre-existing working tree changes observed and untouched: `.claude/settings.json` modified, `dev_stack` deleted.

STATUS: DONE
