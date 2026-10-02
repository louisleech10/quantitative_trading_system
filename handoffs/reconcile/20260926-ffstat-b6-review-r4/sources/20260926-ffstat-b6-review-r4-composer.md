# FF-STAT B6 審查 r4 — COMPOSER

task-id: 20260926-FFSTAT-B6-REVIEW-R4  
brief: handoffs/20261002-FFSTAT-B6-REVIEW-R4-BRIEF.md  
family: COMPOSER  
brief-kind: review  
findings-round: R4  
note: 唯讀；審查標的＝收據 `handoffs/run_receipts/20261002-ffstat-small-mr.json`、六段 log（commit `055af679` 跑次）、SPEC v61 碼（`ab94ec28`／`055af679`）、諮詢 r1 收斂 `handoffs/reconcile/20260926-ffstat-b6-consult-r1/synth.md`。

## 必答（成對）

**(1a)** 本家諮詢 r1 條**已閉合**：① `COMPOSER-R1-P0-01`／`P1-01` 之 L3 置中窗漏測已由 v61 `_assert_nan_mask_layered` 改為比較窗 mask 雙方向 `array_equal`，不再走 fill_rate informational 旁路；`test_small_mutation_numba_rolling_center_true_fails` 於 **m2（v61 碼）PASSED**（s2 在 v60 下 `DID NOT RAISE` 為預期歷史紅）。② `COMPOSER-R1-P2-03` 尾擾動版 fracdiff 長度耦合：`test_small_mutation_fracdiff_maxlag_len_coupling_tail_fails` 已自縮小版／全鏈檔撤除（v61 註解與 node 清單可證）；截斷／並行兩控制仍 PASSED（s1／s2）。③ `P2-01`（維持 `POST_WARMUP_BARS=20`）、`P2-02`（`min_periods=window`）、`P2-04`（多週期基線 informational 0 行）與收斂敘述一致。

**(1b)** `handoffs/run_receipts/20261002-ffstat-small-mr-s2.log:5324-5331` → `Failed: DID NOT RAISE`（center，v60）；`20261002-ffstat-small-mr-m2.log:3006,3627` → 同 node **PASSED**；`20261002-ffstat-small-mr-s1.log:8206-8207` → 僅 `test_small_mutation_fracdiff_maxlag_len_coupling_tail_fails` FAILED（v60 撤除前）；`grep -c 'NaN mask informational' …-m1.log` → **0**。秒級：`PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q` → **12 passed in 0.22s** rc=0；`test_main_values_gate_rejects_mask_only_asymmetry[trunc_tail_nan|full_tail_nan]` 斷言 `got.startswith("_assert_values_gate_main:")` 且含 `NaN mask mismatch`（`:132-142`）。

**(2a)** brief `assumed` **①**（v60 段基線 informational 0、已抓 mutant 於更嚴 gate 仍被抓）**成立**；**②**（全設定 13 項無假紅）**未在本機否證亦未證實**，維持收據 `honest_bounds` 與 RM-FULLSCALE，**不阻擋** Task 4.2 縮小版收案前置。「我沒查」**1**（收據逐 node 對 log）：本家對六段 summary 與 s2 六 node 執行結果抽樣**一致**（例 s2 `1 failed, 5 passed` 對 receipt；m2 `3 passed` 對 receipt），未做全表逐行 PASSED 行與 pytest 樹逐 node 機械對照，**殘餘不一致風險不升級為 P0／P1**（非漏測機制）。**2**（gate 名未寫入收據）：收據已明示；是否補輕量列印重跑屬可觀測性／收據完整性，**非未來洩漏漏測**，不擋收案前置。**3**（Task 4.2 v61 兩新檔全綠）：見 **(3a)**。

**(2b)** ① m1 `nan_mask_informational_lines=0`（receipt＋log 無匹配）；m2 置中 mutant 由 v61 重跑綠；捕獲允許集合含 `_assert_values_gate_main`（`ff_truncation_mr_helpers.py:1456-1463`），mask 失敗在 `:977-983` 呼叫鏈內。② 未跑全設定。③ 單週期現行 11 node＝10 pass＋1 strict xfail（`final_status_by_v61_node`）；多週期 7 pass；與 `test_ff_fullchain_truncation_small_mr.py`／`test_ff_multitf_truncation_small_mr.py` 現行 `def test_` 清單一致（尾擾動 coupling tail 已無）。

**(3a)** **Task 4.2 本機縮小版（v61）驗收已完成**，可作 FF-STAT **收案前置**（仍受 honest_bounds：非全欄／非 12h 對齊／全鏈 13 項登 RM-FULLSCALE）。**不**宣稱既有兩大檔全設定已跑通。

**(3b)** 無本家 P0／P1 阻擋項（威脅模型＝未來洩漏漏測）。

---

## COMPOSER-R4-P3-00

**斷言**: 本輪對 v61 gate、六段收據／log、諮詢 r1 閉合條與 12 項捕獲邊界測逐項核對後，無達 P0／P1 且可重現之未來洩漏漏測。

**碼證**: 讀碼 `tests/feature_engineering/ff_truncation_mr_helpers.py:797-818,924-988,1456-1463`；收據 `handoffs/run_receipts/20261002-ffstat-small-mr.json`；log 行號見必答 **(1b)**；`pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q` → 12 passed 0.22s rc=0；`git status --short -- momentum api frontend tests templates config` 與 `/tmp/ffstat-r4-status-before.txt` 同型（無本輪源碼寫入）。

**類別**: other

**來源摘要**: handoffs/run_receipts/20261002-ffstat-small-mr.json#913352d34cf3;tests/feature_engineering/ff_truncation_mr_helpers.py#8aa3e85a536c;tests/feature_engineering/test_ff_truncation_capture_boundary.py#f7e0a495b156;handoffs/reconcile/20260926-ffstat-b6-consult-r1/synth.md;docs/FFSTAT_SPEC.md#af2d63a0fb19

正文：v61 採諮詢較嚴版「雙方向 mask 全等」，覆蓋本家 consult 最低限度「單側尾端 NaN 必抓」；舊分層規則下 s2 236 行 informational 於 v61 下改為硬失敗，m2 已證 center mutant。尾擾動長度耦合 tail 控制撤除與三家共識一致，不構成殘留漏測出口。未跑生成型 node；未審全設定 13 項假紅；收據未逐 node 列 gate 函式名屬誠實邊界，建議主委銷帳時保留 receipt `honest_bounds` 第 2 條，非本輪 blocking。

---

ASSUMPTIONS_VERIFIED: 主委 fact-verified 1–3 與 log／現行測試清單一致；m2 center PASSED；capture 12 passed 與 brief 一致。  
TESTS_RUN: `pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q` → 12 passed 0.22s rc=0；`grep -c 'NaN mask informational' handoffs/run_receipts/20261002-ffstat-small-mr-m1.log` → 0。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀）  
NUMERIC_OR_SCHEMA_IMPACT: none  
產出: `handoffs/20260926-ffstat-b6-review-r4-composer.md`

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:

STATUS: DONE
