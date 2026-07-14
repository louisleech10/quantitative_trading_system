# IC1C SPEC r5 閉合重驗 — codex
標的:`docs/IC1C_NETIC_SPEC.md` v0.5；日期:2026-07-14；reconcile 現值 sha256:`e3774b483965f66ca328fd5d6f4985de6cd905ad16ad1d465512dd46fbdb79cd`。

## r4 兩條 BLOCKING 原反例重跑
- **CODEX-R4-1 CLOSED** — §U:41 唯一合法域仍為 finite `0 < cost_bps ≤ 1000`；Task 1.1:89 已把原 `cost=0(drag=0)` 改為 `cost_bps=0` 非法，並裁明無成本唯一表示為 `cost_enabled=False`；§V M10:130 與邊界目錄:141 同步要求 config/API/analyzer 三層拒絕 0。同一 direct-analyzer 輸入不再同時有 raise/return 0 兩個 oracle。
- **CODEX-R4-2 CLOSED** — §V:122 將 config schema 指定為 T5；M10:130 對 analyzer/API/config 分別綁 T1:`test_finite_invariants`、T2:`test_cost_bps_range_422`、T5:`test_net_ic_cost_validator`，並各自配置同檔 `test_mutation_m10_{drop_finite_guard,api_drop_validator,config_drop_validator}`。移除任一層 validator 都有該層具名 test+自證 probe，原「一層 probe 代證三層」缺口消失。

## r5 delta 掃描
- reconcile r4 末節 F25/F26 與 SPEC r5 落點一致，未曲解兩項 finding；`cost_bps=0`、合法域、M10、validator/probe 全文搜尋未見殘留相反要求。
- r5 只收斂零值裁決與三層可證偽矩陣；未新增數值公式、輸出 profile、phase 依賴或 consumer scope，未發現新 BLOCKING。

ASSUMPTIONS_VERIFIED: 完整讀 HANDOFF/CLAUDE/SPEC v0.5/r4 codex/reconcile/TEST_DESIGN_CHARTER B1.1+B4+B8；以 r4 原反例逐條核 §U/Task 1.1/§V 與 reconcile r5 裁決。
TESTS_RUN: `nl -ba docs/IC1C_NETIC_SPEC.md`→151 行逐行核對；`rg -n 'cost_bps=0|0 < cost_bps|M10|test_mutation_m10|validator' ...`→零值三處一致、T1/T2/T5 各有 test+同檔 probe；`shasum -a 256 handoffs/20260714-IC1C-SPECREV-RECONCILE.md`→`e3774b...b79cd`。review-only，未跑未實作的 pytest/vitest。
FAILURES_SEEN: CODEX-R4-1、CODEX-R4-2 均 CLOSED；r5 delta 無新 blocking。
SCOPE_CHANGES: none；唯一產出 `handoffs/20260714-IC1C-SPECREV-R5-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT: review-only；未改數值/schema/輸出大小。
RECONCILE-STAMP APPROVED — codex 2026-07-14 sha256:e3774b483965f66ca328fd5d6f4985de6cd905ad16ad1d465512dd46fbdb79cd
SPEC-REVIEW-R5: APPROVE
