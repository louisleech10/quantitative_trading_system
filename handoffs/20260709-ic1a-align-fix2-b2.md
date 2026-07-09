# 20260709 ic1a-align-fix2-b2
正在做: B2 review blocking fix completed; awaiting Claude validation.
待辦: Claude review diff and register `handoffs/IC1A-ALIGN-FIX2-B2-RESULT.md`.
阻塞: none.
本次決策: stage0 close dtype follows stage2 via `to_numpy(copy=False)`.
本次決策: M5 implemented as helper assertion; no-op `validate_alignment` must raise AssertionError on same shifted-label fixture.
踩坑提醒: M1/M4 hermetic fixtures require `labels.return_type=log` to exercise Tier-2 close oracle.
踩坑提醒: Stage0 unit fixtures need >=100 rows or `_validate_input` raises before post-gate assertions.
驗證: `pytest tests/momentum/ -k 'alignment_gate or slice_alignment or event_filter' -q` -> 28 passed.
驗證: `pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q` -> 2 passed, 3 warnings.
驗證: `pytest tests/momentum/core/ tests/momentum/Analysis/ -q` -> 390 passed, 273 warnings.
產出: `handoffs/IC1A-ALIGN-FIX2-B2-RESULT.md`.
