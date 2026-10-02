# FF-STAT 第 6 批 審查 r1 — grok

task-id: 20260926-FFSTAT-B6-REVIEW-R1
family: grok
findings-round: R1
brief-kind: review
brief: handoffs/20261002-FFSTAT-B6-REVIEW-R1-BRIEF.md
template: templates/COMMITTEE_FINDING_TEMPLATE.md

本輪唯讀。未改碼、未改 SPEC／manifest／templates、未 git 寫入。未跑兩新檔生成型 node。秒級探針在 `/tmp/ffstat_b6_r1_work`，先呼叫 `isolate()`／`isolate_dstar_cache()`。

## 前提

fact-verified: 主委事實 1–4（單週期一對 519.9s／3.01GB／窗 3594／37709 欄基線綠；多週期 1h＋4h 一對 2249s／4.12GB／窗 12786／75416 欄基線綠；1h＋4h＋12h 需窗 ≥34302、本機 1h 20352 根；`--collect-only` 20 node；分母尺度呼叫經 `causal_near_zero_mask` 以模組全域名取 `causal_denominator_scale`）。

assumed: brief ①②③。
→ 否證觀測：①既有函式預設參數於定義時綁定全設定、或 `_build_truncation_pair` 在 `window_bars is None` 時另取未縮小 payload；②縮小後 L3／L4／winsor 層不在抽樣或 seam 未解析到產品函式；③某遮罩 mutant 使 full／trunc 前綴不同卻未交給 §G⑦。／我跑了：①② AST＋匯入期 monkeypatch 模擬＋`_resolve_config`；③讀 SPEC Task 4.2「不納入之 mutant」與 helpers 同起點窗算法。生成型 mutant 實跑交主委獨占機器。

---

## 必答（成對）

### (1a) Task 4.2 之設計是否足以作為 FF-STAT 收案前置

足以作為諮詢 r4 較嚴版所要求的收案前置：獨立入口、同套 mutant、窗 ≥ `_required_window_bars`、明示非全欄覆蓋；完整兩檔登 RM-FULLSCALE（fact_keys ④⑤）。縮小版證明的是具名缺陷集合之鑑別力，不是全設定等價。

### (1b) 依據（codex r4 設計要點逐項）

對照 `handoffs/reconcile/20260926-ffstat-b5-consult-r4/synth.md` 採納之 GROK-R4-P1-02／CODEX-R4-P2-02／COMPOSER-R4-P2-03：

| 諮詢 r4 要點 | Task 4.2／本輪碼 |
|---|---|
| 獨立測試入口、不改既有兩檔斷言 | `test_ff_*_truncation_small_mr.py`；helpers 只新增縮小 payload |
| 真實 kline、原 full／trunc 日期與尾擾 | 直接呼叫既有函式本體；align 測試仍走 `_bar_window_dates_at_12h_boundary` |
| 同 helper／gate／容差／CGSA persist | 斷言不另寫；`_assert_truncation_invariants` 內 `_assert_mutation_layer_coverage` |
| L3 聚合器全部、L4、縮尾／rank／zscore／gaussian | `_resolve_config`：10 個 aggregators 全開、`lag_features.enabled`、winsor／rank／zscore／gaussian 開 |
| L3 窗 5／13、trend＋momentum、至少一源非 close | 窗 [5,13]；源 close＋volume；無合成源 |
| RSI／STOCHRSI／ADXR、Ratio／Cross／Momentum／binary_signal | 解析後 momentum 含 RSI／STOCHRSI／ADX／ADXR；ratio／cross／momentum／binary_signal 開、worldquant 關 |
| 原 L3 center、winsor 全量 fit、L4 shift、fracdiff maxlag／parallel／校準擾動／全量 d* | 單週期 12 項對應既有生成項；多週期 7 項對應既有生成項 |
| 分母尺度改回全欄中位數 | `test_small_mutation_denominator_scale_full_column_fails` |
| L1／縮尾／第④類遮罩 mutant 交雙起點 | SPEC「不納入之 mutant」；截斷 MR 同起點 |
| 預熱窗不裁 | 探針窗 3594／12786＝`_required_window_bars`；kline 20352 根足夠 |
| 多週期不可用單週期綠代替 | 另檔 1h＋4h；12h 因資料長度登 RM-FULLSCALE |
| 不證全欄／不以縮小版宣稱既有檔通過 | SPEC 誠實邊界與「不可做」 |

### (2a) assumed ①②③ 與「我沒查」1–5

①成立：既有測試以模組全域名於執行期取設定；無預設參數綁定；`window_bars is None` 用傳入的 `config_payload` 估窗。
②成立：縮小後 L3 十個聚合器、L4、winsor 仍開；收據 L3 17956／L4 7224 欄；mutant 仍 patch `fused_rolling_stats_multi_window`／`_apply_winsorization`／`LagProcessor.compute_all`。
③成立：截斷對同起點；三類遮罩 mutant 兩邊同錯，交 §G⑦ 為正確分工。
「我沒查」1：兩支 strict xfail 原因字面自既有函式 `pytestmark[0].kwargs["reason"]` 拷入；縮小設定仍開 fracdiff 專屬 payload。若 XPASS，strict 契約使測試紅，SPEC 已寫須改一般測試、不得改 non-strict。
「我沒查」2：momentum 含 STOCHRSI；`causal_near_zero_mask` 以模組全域名呼叫 `causal_denominator_scale`（numeric_guards.py:111）；mutant 換的是同一名字。尺度只進近零遮罩——若可比窗內無列跨兩種門檻，`pytest.raises(AssertionError)` 會紅（fail-closed），不是靜默綠。主委正在實跑。
「我沒查」3：oracle 列仍是 12h 收盤邊界（亦為 4h 邊界）；`ALIGN_COARSE_TFS=["4h"]` 只抽 4h 欄。對齊 look-ahead 會改整個粗週期 asof，values gate 抽樣 4h 欄，不是只看 12h 格點。鑑別力未從「4h 欄＋12h 邊界」再被拿掉。
「我沒查」4：L2 Ratio／Cross 的 pair 鍵是 `(source, category, indicator)`，本來就不是 close 對 volume。volume 在 `enabled_sources`，trend／momentum 無 per-indicator `data_sources` ⇒ 走全域源，volume 源 L1 與同指標 Ratio 仍在。
「我沒查」5：SPEC 已寫不證全欄、不得以縮小版宣稱既有兩檔通過、完整版登 RM-FULLSCALE。fact_keys RM-FULLSCALE 已增 ④⑤。收案條件不必再加第四種表述。

### (2b) 碼證或秒級探針

- `venv/bin/python -m pytest --collect-only -p no:cacheprovider tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py tests/feature_engineering/test_ff_multitf_truncation_small_mr.py -q` → `20 tests collected in 0.04s` rc=0。
- `venv/bin/python /tmp/ffstat_b6_r1_work/probe_scope.py` rc=0：窗 3594／12786／fracdiff 3342；kline 20352；default_binds 空；attr 限定名載入空；monkeypatch 後源 close＋volume、volatility 關；`causal_near_zero_mask` 內 `causal_denominator_scale` 為 Name（行 111）；兩支 small xfail `strict=True` 原因與既有檔相同。
- 基線收據 `handoffs/run_receipts/20261002-ffstat-small-mr-probe-1h.json`、`…-1h4h.json`。

### (3a) 兩新檔寫法會否假綠或漏測

autouse 換的是既有模組全域名，既有函式本體在執行期查這些名；新檔把 pair／window 當位置參數傳入，不啟動既有檔的 module fixture。漏測風險在「縮小後 seam 不在場」——解析後 seam 仍在，且 `_assert_mutation_layer_coverage` 缺 L3／L4／winsor 會 AssertionError（mutant 測試的 `pytest.raises` 若因缺層而過，基線 node 會先紅）。秒級 smoke 故意不重複，留在既有檔。

### (3b) 具體反例或證明

反例不成立：AST 掃描 `test_ff_fullchain_truncation_mr.py`／`test_ff_multitf_truncation_mr.py` 之函式預設參數，零處綁定 `_values_gate_mr_config_payload`／`_fracdiff_mr_config_payload`／`_multitf_config_payload`。`_build_truncation_pair` 於 `window_bars is None` 呼叫 `_required_window_bars(config_payload, …)`。單週期 13 個 `def test_`（12 對應＋分母尺度）；多週期 7 個；合計 20，與 collect-only 一致。

### (4a) 可否據此實跑（全套約 6.5 小時，串行、獨占）

可以。窗與本機 1h 根數相容；峰值收據 3.01／4.12GB；標記 `slow`＋`requires_kline`、不入 pre-push。須串行獨占、以 node id 分段。

### (4b) 若否，只列擋之 P0／P1

無 P0／P1。

---

## GROK-R1-P3-00

**斷言**: 本輪逐項核對後無 finding；Task 4.2 縮小版設計與兩新檔寫法對諮詢 r4 較嚴版與 brief 攻擊面均對得上，不阻擋主委獨占實跑。

**碼證**: `venv/bin/python -m pytest --collect-only -p no:cacheprovider tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py tests/feature_engineering/test_ff_multitf_truncation_small_mr.py -q` → 20 collected rc=0（單週期 13＋多週期 7）。`venv/bin/python /tmp/ffstat_b6_r1_work/probe_scope.py` rc=0：`_resolve_config` 後 L1 只 trend＋momentum、源 close＋volume、L3 窗 [5,13] 且 aggregators 10 全開、L2 ratio／cross／momentum／binary_signal 開、worldquant 關、L4 開、主 MR 縮尾／rank／zscore／gaussian 開；RSI／STOCHRSI／ADXR 在場；窗 3594／12786 與可行性收據相同；kline 20352 ≥ 兩窗；既有測試檔 AST 預設參數綁定 0、helpers 屬性載入 payload 0；`_build_truncation_pair` 之 `window_bars is None` 使用傳入 payload；`causal_near_zero_mask` 行 111 以 Name 取 `causal_denominator_scale`；兩支 small fracdiff xfail 為 strict 且 reason 與既有檔相同。核對依據另見上方必答 (1b)(2a)(3b) 對 consult r4 要點、assumed ①②③、「我沒查」1–5 之逐項結果。未跑生成型 node（brief 禁）。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#01951d939d34

正文：審查標的為 SPEC v59 Task 4.2、manifest 兩新檔與探針收據、helpers `_apply_small_mr_scope`／`_small_*_payload`、兩新測試檔、fact_keys RM-FULLSCALE ④⑤。威脅模型為意外漂移與未來洩漏之漏測。本輪未發現可證偽的漏測路徑；分母尺度 mutant 若在縮小窗內不跨門檻，測試會以 `pytest.raises` 未觸發而紅，屬 fail-closed，交主委實跑收據判定。

VERDICT: proceed
BLOCKED-BY:
CLOSED:
