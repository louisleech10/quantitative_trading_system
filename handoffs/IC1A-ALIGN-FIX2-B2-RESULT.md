# IC1A-ALIGN-FIX2-B2 Result
task-id: ic1a-align-fix2-b2
date: 2026-07-09

正在做: B2 review 三個 BLOCKING 已補完，待 Claude review/register-output。
已改: stage0 Tier-2 close 改 `to_numpy(copy=False)`，與 stage2 close dtype 行為一致。
已測: 新增 `test_alignment_gate_stage0_wrong_tf_raises` 覆蓋 12h features + 1h labels fail-closed。
已測: 新增 `test_alignment_gate_m5_dual_leg`，gate ON 命中 M1 錯位，monkeypatch no-op 同資料會讓測試邏輯 AssertionError。
已測: 新增 stage0/stage2 close dtype hermetic 對照，捕捉傳入 gate 的 close dtype 皆為 float32。
註記: B2-DTYPE-02 以 dtype 對照測試明示 `_assign_datetime_index_preserving_values` 不涵蓋 close dtype，caller 需另驗。
踩坑提醒: 第一輪新 fixture 只有 16/32 rows 且未固定 log return，被 `_validate_input total samples < 100` 與非 log oracle 條件推翻；已改 120 rows + log config。
TESTS_RUN: `pytest tests/momentum/ -k 'alignment_gate or slice_alignment or event_filter' -q` -> 28 passed。
TESTS_RUN: `pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q` -> 2 passed, 3 warnings。
TESTS_RUN: `pytest tests/momentum/core/ tests/momentum/Analysis/ -q` -> 390 passed, 273 warnings。
SCOPE_CHANGES: none; 未改根 `HANDOFF.md`，未改 data_cache tracked state。
NUMERIC_OR_SCHEMA_IMPACT: stage0 close caller 不再強制 float64；無輸出 schema/檔案大小變更。
