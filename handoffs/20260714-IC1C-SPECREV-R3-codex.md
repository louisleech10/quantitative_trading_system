# IC1C SPEC r3 閉合重驗 — codex
標的:`docs/IC1C_NETIC_SPEC.md` v0.3；日期:2026-07-14；reconcile 現值 sha256:`36a71f17fe819e6ca4add428eca716ab69aaefa8f03d54a8646ecac1d31d75ca`。

## r2 五條 BLOCKING 逐項重跑
- **CODEX-3 CLOSED** — §P Task 2.1:101 改為 reject `config_override.net_ic_analysis` 整節（白名單空集），原 typed false + override true、`cost_scenarios` 與未知鍵反例皆同步 422。
- **CODEX-5 CLOSED** — §U:34-38 枚舉 SKIPPED/GROSS_ONLY/COST_ENABLED 三套頂層精確鍵集合，§G:68 以 equality 拒絕多/少鍵；原第 4 feature 偷增 reason/status 鍵會紅。
- **CODEX-6 CLOSED** — §U:33 與 Task 2.1:103 凍唯一 `{status,value,reason}` union 且 HTTP/TS 同構；原裸 null、頂層 reason、裸 number 三形反例均非法。
- **CODEX-7 STILL-OPEN（BLOCKING）** — M4:126 的正確性測試含 T4 `NetICChart.test.tsx:sends_cost_bps`，但 mutation 僅列 T2；破壞前端 request construction、保留後端 passthrough 時，T2 probe 仍綠。這不符合 B1.1「每個正確性測試同檔 `test_mutation_*`」及本 finding 的原反例；`mutation_probe_check.sh` 也只掃 Python，無法補證 T4。
- **CODEX-R2-1 CLOSED** — §U:39/Task 1.1:83 已把 config 欄與三 profile 提前 Phase 1，Phase 2 明定只做 API/UI 傳導；原「Phase 1 使用 Phase 2 才存在欄位」反例不成立。

## r3 delta 新洞
- **CODEX-R3-1（BLOCKING）— union presence 自相矛盾。** §U:33 說三 conditional metrics「一律輸出物件」，但 :36 GROSS_ONLY 明禁 breakeven/profitable，:35 SKIPPED 三者全無。相同 gross-only 結果可依 :33 判缺鍵 FAIL、依 :36 判出現鍵 FAIL；須明定 union 僅約束「存在時」或讓三 profile 一致含鍵。
- **CODEX-R3-2（BLOCKING）— G-NEW/Phase 3 仍倒置。** Task 1.1:82 與 COST_ENABLED profile 在 Phase 1 已強制 `cost_sensitivity`，同 Phase 又刪舊 `cost_scenarios`；唯一新階梯 `{c/2,c,2c,5c}` 卻到 Task 3.1:110 才定義。Phase 1 無合法 scenarios oracle；若先實作該階梯即偷做 Phase 3，若 Phase 3 才改則 G-NEW/G-NEW2 凍結後輸出再變且無 G-NEW3 gate。須把算法提前 Phase 1，或延後該鍵並新增 Phase 3 golden。
- **CODEX-R3-3（BLOCKING）— 非有限輸入無合法 profile。** 新 `cost_bps: float|None` (:83/:101) 未凍 finite/range validator，SKIPPED predicate (:35) 也不含非有限 turnover/cost；`cost_bps=NaN/inf` 或 `turnover=inf` 會令裸 `cost_bps/cost_drag_return` 非有限，但 §G:72 禁 JSON NaN/inf，且這兩欄不是 §U union，無 unavailable 表示。須凍 API+config+direct analyzer 的 finite/range 行為及對應 profile/test。

ASSUMPTIONS_VERIFIED: 完整讀 HANDOFF/CLAUDE/SPEC v0.3/r2 codex/reconcile/TEST_DESIGN_CHARTER B1.1+B4+B8；核現行 analyzer/config/API/TS 路徑與 mutation checker 能力。
TESTS_RUN: `nl -ba docs/IC1C_NETIC_SPEC.md`→147 行逐行核對；`rg` 現行 cost/config/consumer→確認舊 scenarios 與 5bps 路徑；`test -x scripts/mutation_probe_check.sh`→存在可執行但僅收 `test_*.py`；`shasum -a 256 ...RECONCILE.md`→`36a71f...d75ca`。review-only，未跑實作 pytest。
FAILURES_SEEN: 4 個 blocking（1 舊 finding 未閉合、3 個 r3 delta）；SCOPE_CHANGES: none，唯一產出本檔；NUMERIC_OR_SCHEMA_IMPACT: review-only，未改數值/schema/輸出大小。
SPEC-REVIEW-R3: REJECT(4 BLOCKING)
