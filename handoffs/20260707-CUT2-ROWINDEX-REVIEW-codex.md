# 20260707 CUT2-ROWINDEX-REVIEW codex handoff

正在做: completed independent adversarial data-correctness review for IC cut2 row_index attach.
待辦: restore or separate unrelated `tests/golden/l65/test_inventory.txt` diff before row_index commit.
阻塞: none for row_index data correctness signoff.
本次決策: Verdict PASS written to `handoffs/CUT2-ROWINDEX-REVIEW-codex.md`.
判斷點1: poisoned IC ingest cache does not need code invalidation for this signoff if current cache is scanned clean; future validation/versioning recommended.
判斷點2: retargeted split-boundary test is faithful to observed row_index failure; full analyze completion remains orthogonal performance coverage.
判斷點3: 1d frequency map gap can be deferred until a real 1d artifact exists for validation.
踩坑提醒: `meta_12h_Time_MonthOfYear` is not a safe raw equality oracle due derived/fractional behavior near month boundaries; use DayOfWeek/HourOfDay/IsWeekend for row-order semantic checks.
驗證: pytest row_index/config_hash/ic_service subset => 13 passed in 89.02s.
驗證: independent read-only script => 9 sidecars monotonic/frequency-correct, target axis byte-equal, IC H5 cache not arange and split frequency validation passed.
驗證: `grep -r "from api\\." momentum/ | wc -l` => 0.
