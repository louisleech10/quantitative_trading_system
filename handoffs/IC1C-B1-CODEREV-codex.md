# IC1C-B1 Code Review (Codex, 2026-07-14)

## Verdict
- Task 1.1: REJECT；核心 B-strict/§T/§U runtime 正確，但 G-NEW 驗收鏈有 2 個 blocking。
- Task 1.2: PASS；`_run_net_ic` 只傳 summary/turnover，factor_returns 未接入。
- Task 1.3: PASS；proxy 正名，公式無 ×2，負/非有限 turnover raise。
- Task 1.4: PASS；reporter/summary CSV 無精確 `net_ic` 欄，手算 0.0015 通過。

## BLOCKING
1. `scripts/ic1c_freeze_baseline.py:282-315,507-515` 只生成/驗 `SCHEMA_COST_ENABLED`+`SCHEMA_SKIPPED`；實際 `g_new.json` 為 4 COST_ENABLED+3 SKIPPED、0 GROSS_ONLY，違反 TODO Phase 1「G-NEW 三 profile 恰等/預設產 GROSS_ONLY」。
2. `scripts/ic1c_freeze_baseline.py:390-481` 的 manifest 由被驗 diff 自動生成再驗自己；無 Frozen 必變/允許變動 allowlist，summary 也只列 key、不列 5→4/3→0 等 value change。實證：注入 `bogus_unapproved_field`/`bogus_summary` 後 `_validate_diff_against_manifest(...) == []`，故 G-NEW oracle 可假綠。
3. 刪除 `tests/phase25/test_net_ic_analyzer.py:63-67` 時遺失仍有效的 `test_compute_net_factor_return_empty_aligned`；production 函式仍保留且本批改了成本公式。RESULT 改寫理由表未逐條解釋此測試，違反 §V 防假綠。
4. `git diff HEAD` 非 B1 scope-clean：另含 `.claude/settings.json`、`.claude/gate/{audit,verify_audit}.log`、`tests/golden/l65/test_inventory.txt`；後者仍是 collect 副作用 `BLOCKER: no L6.5/preprocessing tests collected`，且 RESULT 卻聲稱 `SCOPE_CHANGES:none`。需用 preflight 證據隔離歸屬並恢復 B1 可驗 diff。

## Verified evidence
- `PYTHONDONTWRITEBYTECODE=1 venv/bin/pytest -p no:cacheprovider <B1四測試檔> -q` → 57 passed；phase26 factories/integration → 14 passed。
- 手動 mutant：M2 ×2→`test_cost_drag_hand_calc` RED；M9 bare-null→`test_unavailable_union_shape` RED；M11 clamp→`test_negative_turnover_skipped` RED；基線 57 綠，三支非空心。
- 靜態/產物：精確 `net_ic` output key 未見於 momentum/reporter/CSV/G-NEW；`net_ic_analysis` 模組鍵保留；config schema+analyzer 均拒非有限、0、>1000，enabled 缺 bps 亦拒。
- `shasum -a 256 -c handoffs/ic1c_baseline/g_new.sha256` → OK；但只證檔案完整，不閉合上述 profile/oracle 問題。

ASSUMPTIONS_VERIFIED: Frozen SPEC/TODO reconcile 三家 APPROVED；審查範圍為 HEAD tracked diff+B1 untracked artifacts/RESULT。
TESTS_RUN: B1 57 passed；phase26 14 passed；3 manual mutants RED；manifest adversarial probe 接受未核可欄位。
FAILURES_SEEN: none in pytest；4 個規格/證據鏈 blocking 如上。
SCOPE_CHANGES: reviewer 僅新增本檔；未改 implementation/HANDOFF/data_cache。
NUMERIC_OR_SCHEMA_IMPACT: review-only；實作移除 net_ic、改三 profile/成本公式，需修 blocking 後重凍 G-NEW。
CODE-REVIEW: REJECT(4 BLOCKING)
