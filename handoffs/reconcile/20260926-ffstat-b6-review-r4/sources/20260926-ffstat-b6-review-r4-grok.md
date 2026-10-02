# FF-STAT 第 6 批 審查 r4 — grok

task-id: 20260926-FFSTAT-B6-REVIEW-R4
family: grok
findings-round: R4
brief-kind: review
brief: handoffs/20261002-FFSTAT-B6-REVIEW-R4-BRIEF.md
template: templates/COMMITTEE_FINDING_TEMPLATE.md
round-id: 427fb0f0-661e-4ba5-8a68-8c8e65139c9e

本輪唯讀。未改碼、未改文檔、未 git 寫入。未跑生成型 node。秒級測試與 log 對帳在 `/tmp/ffstat_r4_parse`。指令列與暫存路徑無家族名。

## 前提

fact-verified: 主委事實 1–3（六段 log 之 collect／PASSED／FAILED／XFAIL 與收據逐 node 對得上；s1／s2／m1 為 v60 測試碼、m2–m4 為 v61；捕獲邊界 12 passed）。
assumed: brief ①②。
→ 否證觀測：①某 v60 下被抓到之 mutant 於 v61 下改由非允許 gate 拋出；②全設定含縮小版沒有之欄類於比較窗有合法 mask 不對稱。／本輪：①讀 `_assert_nan_mask_layered` 呼叫點在 `_assert_values_gate_main` 內（該名在 `_CAUSAL_GATE_FUNCS`）；②未跑全設定 13 項（本機禁生成型 node）。

---

## 必答（成對）

### (1a) 本家諮詢 r1 條是否閉合（置中窗 mutant 於 v61 下被抓到；尾擾動長度耦合已撤）？

閉合。`GROK-R1-P0-01`：v61 比較窗 mask 雙方向全等後，單週期置中窗 mutant 於 m2 被 `_expect_causal_gate_failure` 收下（PASSED）；多週期同 mutant 於 m3 亦 PASSED。`GROK-R1-P2-01`：縮小版與既有全鏈檔皆已刪除尾擾動版長度耦合測試函式，現行列點無該 node。

### (1b) log 行號或秒級測試輸出

置中窗（GROK-R1-P0-01）：

- s2（v60）`handoffs/run_receipts/20261002-ffstat-small-mr-s2.log:1802` `FAILED [ 33%]` 對應 `:10` 起跑之 `test_small_mutation_numba_rolling_center_true_fails`；`:5331` `Failed: DID NOT RAISE <class 'AssertionError'>`；`:5334` 起 captured stdout 為 `NaN mask informational` 且 `full=1.000 trunc=0.700`；檔內該字面 236 行；footer `:7128-7129` 1 failed／5 passed。
- m2（v61）`:3007` 起跑同一單週期 node，`:3627` `PASSED [100%]`；footer 3 passed in 5054.17s；該段 `NaN mask informational` 計數 0（raise 取代 print）。
- m3（v61）`:10` 起跑多週期 `test_small_mutation_numba_rolling_center_true_fails`，footer 2 passed in 3142.87s。
- 現行碼 `tests/feature_engineering/ff_truncation_mr_helpers.py:797-818`：mask 不等即 `AssertionError`（`NaN mask mismatch`），不再依 fill_rate 放行；`:977-983` 於 `_assert_values_gate_main` 內先於 both-non-NaN 值比對呼叫；`:1456-1462` `_CAUSAL_GATE_FUNCS` 含 `_assert_values_gate_main`。
- `venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q --tb=short -p no:cacheprovider` → **12 passed in 0.19s** rc=0，含 `test_main_values_gate_rejects_mask_only_asymmetry[trunc_tail_nan]`／`[full_tail_nan]` 與 `test_main_values_gate_accepts_equal_sparse_mask`。

尾擾動長度耦合（GROK-R1-P2-01）：

- s1（v60）`:5543` `FAILED [100%]`；`:5546-5558` 該 node 於 helpers:1744 以 `allowed=['_assert_columns_gate', '_assert_d_star_gate']` 捕獲，實際路徑含 `_assert_values_gate`，訊息 `Not equal to tolerance rtol=0, atol=1e-08`、`volume_1h_trend_EMA_144_Momentum_L55_fracdiff`、Max rel 0.00042215。
- 現行 `tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py:100-101` 僅註解「v61 撤除」；`:96-97` 截斷版與 `:104-105` 並行版仍在。既有檔 `test_ff_fullchain_truncation_mr.py:171-172` 同撤。
- `--collect-only` 兩縮小檔＋捕獲邊界 → 30 collected in 0.04s；單週期 11 node（無 `*_tail_fails`）、多週期 7、捕獲 12。

### (2a) assumed ①② 與「我沒查」1–3 是否成立？

①成立。②作為 Task 4.2 縮小版之推論成立，全設定 13 項仍為 SPEC 誠實邊界（本機未跑）。「我沒查」1 成立（收據與 log 逐 node 一致）。2 可接受，不須為列印回傳值再跑生成。3 成立：現行兩新檔全部 node 於 v61 解釋下綠（單週期 10 過 1 xfail、多週期 7 過）。

### (2b) 依據

- ①：v61 只把 informational 改為同一函式內的 `AssertionError`。s1／m1 基線 informational 計數 0 ⇒ 收緊後基線不致假紅。s2 五支已抓到之 mutant 於 v60 已由允許 gate 拋出；mask 先於值比對 raise 時 traceback 仍經 `_assert_values_gate_main`（允許集未縮）。否證觀測①未出現。
- ②：縮小設定 L1 只 trend＋momentum、源 close＋volume（helpers `_SMALL_MR_CATEGORIES`／`_SMALL_MR_SOURCES`）。volume 已在縮小版（s1 尾擾動失敗欄即 `volume_1h_trend_EMA_*_fracdiff`）。volatility／pattern 不在縮小版；全設定 13 項登 RM-FULLSCALE。m1 0 informational 只證縮小多週期基線。
- 「我沒查」1：awk 對六段 log 抽「行首 `tests/...::node` 後接 PASSED／FAILED／XFAIL」：s1 7 項（捕獲 atol PASSED、C2-1 PASSED、C2-2 PASSED、fracdiff 截斷 PASSED、fracdiff 尾擾 XFAIL、長度耦合截斷 PASSED、長度耦合尾擾 FAILED）；s2 6 項（並行 PASSED、置中 FAILED、縮尾 PASSED、L4 PASSED、校準 PASSED、全量 d* PASSED）；m1 2 PASSED；m2 3 PASSED（對齊、對齊＋尾擾、單週期置中）；m3 2 PASSED（多週期置中、縮尾）；m4 1 PASSED（L4）。與收據 `segments[].nodes` 及 footer 秒數（s1 2697.21、s2 2647.97、m1 4582.34、m2 5054.17、m3 3142.87、m4 2311.42）一致。警告區重複印 node 名不計入結果。
- 「我沒查」2：SPEC Task 4.2 驗證條款已寫「確切 gate 名與訊息不另寫入收據（v61 實跑以 `-rfE` 執行、回傳值未列印）」。PASSED 之負控制由測試內 `_expect_causal_gate_failure` 保證失敗經允許集；不成立即 FAILED（s1 尾擾動即此出口）。補列印需各控制再生成一對，屬生成型 node，本輪禁跑，且不增加鑑別力。置中窗之失敗型已由 s2 informational＋捕獲邊界 `NaN mask mismatch` 經 `_assert_values_gate_main` 釘住。
- 「我沒查」3：現行 collect 單週期 11＝基線 4＋xfail 1＋負控制 6（長度耦合截斷／並行、置中、縮尾、L4、校準、全量 d*）；多週期 7＝基線 2＋負控制 5。v61 `final_status_by_v61_node` 單週期 10 passed／1 xfail、多週期 7 passed。v60 紅的兩 node：置中已於 m2 用 v61 碼重跑綠；尾擾動長度耦合已撤。

### (3a) Task 4.2 是否完成、可否作 FF-STAT 收案前置？

可以。兩新檔現行 node 全綠（尾擾動 fracdiff 基線為既有 codec strict xfail）；諮詢 r1 之置中窗漏測與無鑑別力尾擾動控制均已閉合；捕獲邊界 12 項秒級綠。完整 13 項與未選欄類仍依 SPEC 誠實邊界登 RM-FULLSCALE，不擋本前置。

### (3b) 若否，只列擋之 P0／P1

無。本輪無 P0／P1。

---

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding；諮詢 r1 之置中窗漏測於 v61 下被抓到、尾擾動長度耦合已撤，Task 4.2 兩新檔現行 node 全綠，可作 FF-STAT 收案前置。

**碼證**: `venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q --tb=short -p no:cacheprovider` → 12 passed in 0.19s rc=0。`--collect-only` 兩縮小檔＋捕獲邊界 → 30 collected in 0.04s（單週期 11、多週期 7、捕獲 12；無 `*_maxlag_len_coupling_tail_fails`）。六段 log 與收據 `handoffs/run_receipts/20261002-ffstat-small-mr.json` 逐 node 一致；s2:5331 DID NOT RAISE 對 v60 置中窗、m2:3627 同 node v61 PASSED；s1:5546-5558 尾擾動長度耦合值 gate 不在允許集。helpers:797-818 雙方向 mask 全等；`:1456-1462` 允許集含 `_assert_values_gate_main`。`cmp` 開跑前／後 scoped `git status --short -- momentum api frontend tests templates config` rc=0。

**類別**: other

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#8aa3e85a536c; tests/feature_engineering/test_ff_truncation_capture_boundary.py#f7e0a495b156; tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py#1eea8efdbc3a; docs/FFSTAT_SPEC.md#af2d63a0fb19; handoffs/run_receipts/20261002-ffstat-small-mr.json#913352d34cf3; handoffs/run_receipts/20261002-ffstat-small-mr-s2.log#ff5498e42586; handoffs/run_receipts/20261002-ffstat-small-mr-m2.log#54d97f961456; handoffs/reconcile/20260926-ffstat-b6-consult-r1/synth.md#bea3cd80332c; handoffs/20260926-ffstat-b6-consult-r1-grok.md#d7192f2624e6; handoffs/20261002-FFSTAT-B6-REVIEW-R4-BRIEF.md#e5b504486bbe

核對範圍：諮詢 r1 本家 `GROK-R1-P0-01`／`GROK-R1-P2-01`；SPEC v61 Task 4.2 驗證條款與誠實邊界；現行 helpers mask／捕獲／允許集；六段 log 與收據；秒級捕獲邊界 12 項；collect-only 列點。未跑生成型 node。未發現可重現之未來洩漏漏測。`HIGH_FILL_RATE_THRESHOLD` 常數仍在 helpers:55、函式本體已不再讀它，屬死常數，不構成本輪 finding。

---

ASSUMPTIONS_VERIFIED: ① mask raise 仍經 `_assert_values_gate_main`（允許集未縮）；s1／m1 informational 0。②縮小版＋多週期基線 0 informational；全設定 13 項未跑、已登 RM-FULLSCALE。
TESTS_RUN: `venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q --tb=short -p no:cacheprovider` → 12 passed in 0.19s rc=0；`--collect-only` 三檔 → 30 collected in 0.04s rc=0；awk 六段 log 對帳與收據一致。
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀）
NUMERIC_OR_SCHEMA_IMPACT: none
產出: `handoffs/20260926-ffstat-b6-review-r4-grok.md`
HANDOFF_NOT_UPDATED: 本輪唯讀 brief；根 HANDOFF 與另份狀態交接均未改寫，交件落點為本檔。

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R1-P0-01,GROK-R1-P2-01

STATUS: DONE
