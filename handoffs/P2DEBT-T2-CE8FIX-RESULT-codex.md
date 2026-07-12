# P2DEBT T2 CE8 fix result — Codex — 2026-07-12

正在做：CE8 已完成修復與指定驗收，待 Claude 驗收/入帳。
待辦：主委檢視三個允許檔與本結果；本執行端未 commit。
阻塞：none。
本次決策：`MIN_INSTALLER_ARITY={S1:2,S2:3,S10:2}` 在 `_validate` fail-closed。
本次決策：subtarget mutation 改為 S1/S2/S10 各 pop 一項後呼叫 `activate()`。
本次決策：測試同時斷言 gate inactive、installed IDs 空、production function identity 未變。
本次決策：刪除 S9/S11 手寫假 source mutation；真 wiring 由 inventory 計數承擔。
本次決策：SPEC probe 降為 path-shape only，AMENDED C-CE8 指向雙 review。
踩坑提醒：rollback 合成 manifest 原先不滿新 arity，第一輪在 installer 前 fail；已補足 arity後保留 S2 mid-fail。
允許檔產出：tests/fixtures/ic_persist_redirect.py
允許檔產出：tests/momentum/Analysis/test_ic_persist_redirect_unit.py
允許檔產出：docs/P2DEBT_T2_DCREDIRECT_SPEC.md
結果產出：handoffs/P2DEBT-T2-CE8FIX-RESULT-codex.md
VERIFY：`venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q` → 36 passed in 2.33s。
POLARITY：顯式 Python probe exit 0；完整→`POLARITY_COMPLETE=PASS`。
POLARITY：pop S2 一 method→`RedirectCompletenessError: ... requires at least 3 installers, got 2`。
DELEGATED VERIFY：grok runner 執行 `bash scripts/run_ic_persist_hermetic.sh --set V7` → exit 0；133 passed, 8 skipped, 0 failed；`DIGEST_DIFF_EMPTY[V7]=1`。
FAILURES_SEEN：第一輪 unit 35 passed/1 failed（rollback fixture arity）；修正 fixture 後消失。
SCOPE_CHANGES：none；未改 momentum/、api/、data_cache/ 或根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT：none。
