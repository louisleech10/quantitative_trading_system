# FF-STAT B6 審碼 r1 — COMPOSER

task-id: 20260926-FFSTAT-B6-REVIEW-R1  
brief: handoffs/20261002-FFSTAT-B6-REVIEW-R1-BRIEF.md  
family: COMPOSER  
brief-kind: review  
findings-round: R1  
note: 唯讀；標的＝SPEC v59 Task 4.2 縮小版全鏈截斷 MR（設計＋測試本體）；未跑生成型 node（brief 禁 heavy）。

## 必答（成對）

**(1a)** Task 4.2 **設計**足以作為 FF-STAT 收案前置（相對諮詢 r4 較嚴版）：獨立測試入口（兩新檔＋manifest 登記）✓；沿用既有函式本體與 gate／容差／mutant 斷言、只縮生成範圍（`_apply_small_mr_scope`）✓；`window_bars` 經 `_required_window_bars` 與探針窗 3,594／12,786 一致 ✓；同套具名 mutant（L3 center、縮尾 full-fit、L4 shift、fracdiff 族、多週期 align look-ahead）仍經 `orig.test_*` 呼叫 ✓；新增分母尺度 mutant 具 spy（`calls[0] > 0`）✓；誠實邊界與 RM-FULLSCALE ④⑤（`scripts/fact_keys.json`）✓；不以縮小版宣稱完整兩檔已通過 ✓。對照 codex r4（`handoffs/reconcile/20260926-ffstat-b5-consult-r4/synth.md` **CODEX-R4-P2-02**）：縮小版須證「具名缺陷集合鑑別力」而非僅減類別——本設計保留 L2／L3 聚合器／L4 與 layer 覆蓋守衛（經 `_assert_truncation_invariants`→`_assert_mutation_layer_coverage`），符合。**收案執行面**仍缺下文 P1-01 之全套收據，設計≠已驗收。

**(1b)** 靜讀 `docs/FFSTAT_SPEC.md` Task 4.2（`:187-201`）、`ff_truncation_mr_helpers.py:237-260`、兩新測試檔 autouse fixture；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → TODOFMT PASS；探針收據 `20261002-ffstat-small-mr-probe-1h.json`（519.9s／3.01GB／37,709 欄基線綠）、`20261002-ffstat-small-mr-probe-1h4h.json`（2,249s／4.12GB 基線綠）；`pytest …/test_ff_*_small_mr.py --collect-only` → **20** node。

**(2a)** **assumed ①**（monkeypatch 後既有函式本體皆取縮小設定）：**成立**。`orig` 內測試以定義模組 globals 解析 `_values_gate_mr_config_payload`／`_fracdiff_mr_config_payload`／`_multitf_config_payload` 與 `TRAINING_TFS` 等；autouse 以 `monkeypatch.setattr(orig, …)` 替換後，`test_c2_2_*` 等路徑之 global 已指向縮小版（非 helpers 模組未 patch 之副本）。模組級 fixture 在 small 檔內直接呼叫 `_small_*` 建 pair，不依賴 autouse 順序。**assumed ②**（縮小設定下 L3／縮尾／L4 seam 仍被抽樣）：**成立（靜態）**——探針 L2 11,621 欄、L3 17,956、L4 7,224；基線路徑仍跑 `_assert_mutation_layer_coverage`（`ff_truncation_mr_helpers.py:953`）。**assumed ③**（三類遮罩 mutant 由 §G⑦ 負責、截斷 MR 不納入）：**成立**，與 SPEC `:198-199` 一致。**「我沒查」1**（strict xfail 兩項是否 XPASS）：未跑 fracdiff 生成，保留 strict xfail 拷貝自既有 reason（`test_ff_fullchain_truncation_small_mr.py:76-84`），風險與既有檔同級。**「我沒查」2**（分母尺度 mutant 是否真使前綴不同）：主委實跑進行中（brief 事實 5），本輪未否證。**「我沒查」3**（12h oracle 對 4h 鑑別力）：見 P2-01。**「我沒查」4**（close＋volume 是否仍有跨源 L2）：operators 開、探針 L2 欄數非零，**未**逐欄驗 `_Ratio` 命名。**「我沒查」5**（誠實邊界是否寫清）：SPEC Task 4.2「誠實邊界」＋ RM-FULLSCALE 已寫，**足夠**。

**(2b)** `/tmp/ffstat_b6_r1_probe.py`（先 `isolate()`）→ `test_c2_2_global_is_small True`、`small_window_bars 3594`、`operators_enabled True`、`sources ['close', 'volume']`；`venv/bin/python -m pytest tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py tests/feature_engineering/test_ff_multitf_truncation_small_mr.py --collect-only -q` → 20 collected rc=0。

**(3a)** **直接呼叫 `orig.test_*` ＋ autouse 換 `orig` 模組名稱**：在 assumed ① 機制下**不構成**「斷言重寫假綠」——斷言與 gate 仍在既有函式內，small 檔未複製 `_assert_*` 邏輯。**漏測風險**在於：若未來有人在 `orig` 內改為 `from helpers import _values_gate_mr_config_payload as _payload` 後在測試內呼叫 `_payload()` 而非常規名稱，或改為 helpers 直調而不經 `orig` 全域，才會 bypass patch（現碼未見）。

**(3b)** 反例（若 patch 錯模組才會發生）：對 `helpers._values_gate_mr_config_payload` patch 而跑 `orig.test_c2_2_*` 仍會用全設定——本實作 patch 目標為 `orig`，探針證 `orig.test_c2_2_tail_perturbation_prefix_invariant.__globals__["_values_gate_mr_config_payload"]` 為 small 函式。

**(4a)** **可以**據主委實測與探針，在獨占機器串行跑全套（約 6.5 小時、峰值 ≤4.12GB 已量）：單週期 13 有效 node（含 2× strict xfail、1 基線共用 pair）＋多週期 7 node；須分段與收據（SPEC `:195-196`）。

**(4b)** 阻擋收案前置之 P0／P1：**COMPOSER-R1-P1-01**（缺 SPEC 要求之全套 `*-ffstat-small-mr.json` 收據）；分母尺度 mutant 實證待主委收據（非設計缺陷，不另列 ID）。

---

## COMPOSER-R1-P1-01

**斷言**: SPEC v59 Task 4.2 要求兩新檔**全部 node 綠**且產出 `handoffs/run_receipts/<日期>-ffstat-small-mr.json`（逐 node 結果、mutant seam 證據）；目前僅有 baseline 探針 `20261002-ffstat-small-mr-probe-*.json`（**未跑 mutant**），**收案前置驗收條未滿足**。

**碼證**: `docs/FFSTAT_SPEC.md:196` 驗收條文；`ls handoffs/run_receipts/*ffstat-small-mr.json` → **無匹配**（僅 `*-probe-1h.json`／`*-probe-1h4h.json`）；`docs/manifests/FFSTAT.json` `run_receipts` 亦未登記 aggregate 收據；`pytest --collect-only` → 20 node 待實跑。CODE-ANCHOR: docs/FFSTAT_SPEC.md:196  
MUTATION: `test -f handoffs/run_receipts/20261002-ffstat-small-mr.json && jq -e '.nodes | length>=20' handoffs/run_receipts/20261002-ffstat-small-mr.json` → 現狀第一步即失敗（檔不存在）。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#01951d939d34;docs/manifests/FFSTAT.json#7a49a11402d1;handoffs/run_receipts/20261002-ffstat-small-mr-probe-1h.json#2266342a057a

正文：**修法（執行，非再加機制）**：獨占機器串行 `pytest tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py tests/feature_engineering/test_ff_multitf_truncation_small_mr.py -q`，並依 SPEC 寫入 aggregate JSON（每 node pass／xfail／耗時；mutant 附 seam 計數或 `lengths_seen`／`parallel_calls`）；登記 manifest `run_receipts`。**可行性**：探針已證 baseline 一對可完成且 RSS≤4.12GB；全套時間 SPEC 已估（~6.5h）。影響：在收據落地前，Task 4.2 不可視為 FF-STAT 收案前置已完成。

---

## COMPOSER-R1-P2-01

**斷言**: 多週期縮小版將 `ALIGN_COARSE_TFS` 從完整檔之 `["4h","12h"]` 縮為 `["4h"]`（`test_ff_multitf_truncation_small_mr.py:35-58`），`_assert_align_coarse_boundary_lookahead_detected` 與 `_assert_mutation_layer_coverage` 之粗週期 oracle **不再涵蓋 12h 欄**；12h 對齊類回歸僅能依 RM-FULLSCALE 完整檔或 §G⑦，縮小版鑑別力弱於完整 multitf MR（與 SPEC 誠實邊界一致，但委員須明示）。

**碼證**: `test_ff_multitf_truncation_mr.py:50` vs `test_ff_multitf_truncation_small_mr.py:35-58`；`ff_truncation_mr_helpers.py:1266-1291` oracle 依 `align_coarse_tfs` 篩欄；窗選取仍用 `_bar_window_dates_at_12h_boundary`（4h 邊界為 12h 邊子集，brief 前提 ③ 未查之殘餘）。

**類別**: code-contract

**來源摘要**: tests/feature_engineering/test_ff_multitf_truncation_small_mr.py#84f7d73fdabe;tests/feature_engineering/test_ff_multitf_truncation_mr.py#3f5403e6490c;docs/FFSTAT_SPEC.md#01951d939d34

正文：非要求恢復 12h（本機 kline 長度不足，SPEC 已記）；屬**已知縮減**，換機 fullscale ⑤ 仍必跑。不阻擋設計合併，但收斂時勿將縮小 multitf 等同完整 9 項之對齊覆蓋。

---

ASSUMPTIONS_VERIFIED: monkeypatch 綁定（probe）；20 collect-only；TODOFMT PASS；探針 JSON 與 brief 事實 1–4 一致。  
TESTS_RUN: `pytest test_ff_*_small_mr.py --collect-only -q` rc=0；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` rc=0；`/tmp/ffstat_b6_r1_probe.py` rc=0。  
FAILURES_SEEN: none（未跑 slow 生成）。  
SCOPE_CHANGES: none（唯讀）  
NUMERIC_OR_SCHEMA_IMPACT: none  
產出: `handoffs/20260926-ffstat-b6-review-r1-composer.md`

VERDICT: blocked  
BLOCKED-BY: COMPOSER-R1-P1-01  
CLOSED:

STATUS: DONE
