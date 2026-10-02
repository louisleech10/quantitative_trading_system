# FF-STAT 第 6 批 審查 r3 — grok

task-id: 20260926-FFSTAT-B6-REVIEW-R3
family: grok
findings-round: R3
brief-kind: review
brief: handoffs/20261002-FFSTAT-B6-REVIEW-R3-BRIEF.md
template: templates/COMMITTEE_FINDING_TEMPLATE.md
commit: 1d09aaa4
round-id: 6d0c7851-df5d-470f-90b3-805001600c7d

本輪唯讀。未改碼、未改文檔、未 git 寫入。未跑生成型 node。秒級探針在 `/tmp/ffstat_b6_capchk`，先呼叫 `isolate()`／`isolate_dstar_cache()`。指令列與暫存路徑無家族名。

## 前提

fact-verified: 主委事實 1（`test_ff_truncation_capture_boundary.py` 9 passed 0.13s）。
assumed: brief ①②③。
→ 否證觀測：①某 gate 失敗之 traceback 缺該 gate 名；②某因果失敗由表外函式拋出且路徑不含表列 gate；③對齊控制於捕獲區內之失敗只由 align oracle 函式拋出。／本輪：①②以真實 gate 對小 parquet 取 `excinfo.traceback` 函式名＋helpers 內 `raise AssertionError` 之呼叫點核對；③讀 `_run_align_lookahead_control` 呼叫序。未跑生成型 node。

---

## 必答（成對）

### (1a) 本家 r2 條以原反例（warmup／atol／metadata 真實訊息）重跑是否閉合？

閉合。`GROK-R2-P1-01` 之三處實際訊息（numpy atol 頭、`warmup <檔>::<欄> NaN mask mismatch`、metadata 裸 assert 空字串）在 commit `1d09aaa4` 之函式名判定下均被 `_expect_causal_gate_failure` 收下；前綴判定對同訊息仍對不上。

### (1b) 實跑輸出

隔離探針 `TMPDIR=/tmp/ffstat_b6_capchk PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/ffstat_b6_capchk/probe.py`（isolate 後直接呼叫 helpers 原碼）：

| 反例 | 訊息頭 | traceback 函式名 | 捕獲 |
|---|---|---|---|
| atol 值 gate | `Not equal to tolerance rtol=0, atol=1e-08` | `_assert_values_gate`、`assert_allclose`、`inner`、`assert_array_compare`、`<lambda>` | ACCEPT `_assert_values_gate: Not equal to tolerance...` |
| warmup NaN mask | `warmup 1h_L1_trend_EMA_5_L65.parquet::close_fracdiff NaN mask mismatch` | `_assert_warmup_nan_masks_equal`、`_assert_arrays_values_close`、`<lambda>` | ACCEPT `_assert_warmup_nan_masks_equal: warmup ...` |
| metadata symbol／列數裸 assert | 空字串（`msg_len=0`） | `_assert_metadata_gate`、`<lambda>` | ACCEPT `_assert_metadata_gate:`（訊息空仍收） |

`venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q --tb=short -p no:cacheprovider` → `9 passed in 0.13s` rc=0（含 atol／warmup／metadata／strict 欄集合收；覆蓋守衛路徑／覆蓋守衛訊息／非 gate 仿值訊息拒；尾擾動 fracdiff 拒值 gate；前史只改起始日前）。

`pytest --collect-only -q` 四截斷 MR 檔＋捕獲邊界檔 → `50 tests collected in 0.06s` rc=0（41＋9）。

scoped `git status --short -- momentum api frontend tests templates config` 與開跑前相同（僅既有 `__pycache__`／golden 噪音）。

### (2a) assumed ①②③ 與「我沒查」1–3 是否成立？

①成立。②成立（呼叫點核對，未跑生成）。③成立。「我沒查」1 分流完整；2 lambda 名不造成誤收；3 未入表之新 gate 會誤拒（紅）而非假綠，方向正確。

### (2b) 依據

- ① numpy 實際 raise 在 `assert_allclose`／`inner`；`excinfo.traceback` 仍含 `_assert_values_gate`。metadata 經 pytest 斷言改寫後 traceback 仍含 `_assert_metadata_gate`，無截成只剩內部名。
- ② helpers 內 `raise AssertionError` 且走 `check()` 路徑者：表列六 gate；表外 `_assert_arrays_values_close` 只由 `_assert_warmup_nan_masks_equal` 與 `_assert_values_gate`（無 atol）呼叫；`_assert_nan_mask_layered`／`_assert_values_both_non_nan_close` 只由 `_assert_values_gate_main` 呼叫。warmup 探針 frames 同時有表外 inner 與表列父 gate，`frames & allowed_gates` 非空。`_assert_truncation_invariants`／`_assert_fracdiff_truncation_invariants` 自身無 `raise AssertionError`，只轉呼叫表列 gate。`_assert_align_coarse_boundary_lookahead_detected` 與 `_read_artifact_timestamps` 之 AssertionError 不在 `check()` 內。
- ③ `_run_align_lookahead_control` 先呼叫 oracle（捕獲區外正向檢查），再 `_expect_causal_gate_failure(..., _values_check)`；oracle 名不在 `_CAUSAL_GATE_FUNCS`。捕獲區內對齊相關失敗走 `_assert_values_gate_main` 之抽樣／值比對（表列）。若 oracle 被誤放入 `check()`，函式名不在允許集 ⇒ 拒收（紅），與值 gate 不互相冒充。
- 「我沒查」1：coverage 為 `AssertionError("coverage guard failed: ...")`，即使 nested 函式名為 `_assert_values_gate_main`（會命中允許集），`_NON_CAUSAL_MARKERS` 仍拒；探針 `coverage_marker.ok=false` 訊息 `非因果 gate 之失敗不算抓到`。sampling 為 `pytest.fail` ⇒ `builtins.Failed`，`isinstance(..., AssertionError)=false`；`pytest.raises(AssertionError)` 捕不到，測試以 Failed 紅（fail-closed）。層覆蓋另經 `_NON_CAUSAL_FUNCS={_assert_mutation_layer_coverage}`；測試 `test_layer_coverage_failure_is_rejected` 綠。
- 「我沒查」2：`lambda: throw(AssertionError("values something"))` 路徑 `['<genexpr>', '<lambda>', '_expect_causal_gate_failure']`，捕獲 `失敗不由允許之 gate 拋出`。`<lambda>` 不在允許集，不誤收；真實 gate 外包 lambda（九項測試與本探針 atol／warmup）仍收父 gate 名。
- 「我沒查」3：新 gate 未入 `_CAUSAL_GATE_FUNCS`／`_FRACDIFF_PRE_VALUES_GATES` 時 `hit` 空 ⇒ 負控制紅。與尾擾動拒收 `_assert_values_gate` 同型。屬漏表誤拒，不是漏測假綠。

### (3a) 可否據此全跑（約 6.5 小時，串行、獨占）？

可以。r2 捕獲誤拒已以原三反例閉合；本輪未找到會把因果失敗當抓到、或把覆蓋／抽樣／非 gate 當抓到之 P0／P1。全跑仍須串行獨占、不與其他真實 CGSA 並行。

### (3b) 若否，只列擋之 P0／P1

無。本輪無 P0／P1。

---

## GROK-R3-P3-00

**斷言**: 本輪逐項核對後無 finding；commit `1d09aaa4` 之函式名封閉集合判定收下 r2 三反例之真實 gate 失敗，且 coverage／sampling／非 gate／尾擾動值 gate 仍拒。

**碼證**: `venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q --tb=short -p no:cacheprovider` → 9 passed in 0.13s rc=0。探針 `/tmp/ffstat_b6_capchk/probe.py`：r2 atol／warmup／metadata 皆 `capture.ok=true`；numpy 頭仍為 `Not equal to tolerance rtol=0, atol=1e-08`（前綴法會拒、函式名收下）；lambda／具名非 gate 拒；coverage marker 拒；sampling 為 Failed 非 AssertionError；`allowed_gates=_FRACDIFF_PRE_VALUES_GATES` 時值 gate 拒、strict 欄集合收；`_pre_start_rows`／`_patch_kline_pre_start_ohlcv` 只改起始日前 5 列。helpers `_CAUSAL_GATE_FUNCS` 六名與 SPEC Task 4.2 兩處文字一致；`_CAUSAL_GATE_PREFIXES` 已不在 helpers。collect-only 50 node 0.06s。scoped git status 與開跑前相同。

**類別**: other

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#aba8dc92e20b; tests/feature_engineering/test_ff_truncation_capture_boundary.py#3332fe88dc49; docs/FFSTAT_SPEC.md#f8a327dafd6a; handoffs/reconcile/20260926-ffstat-b6-review-r2/synth.md#e8d6f94eefcd; handoffs/20261002-FFSTAT-B6-REVIEW-R3-BRIEF.md#cb281f5555b5

核對範圍：commit `1d09aaa4` 之 `_CAUSAL_GATE_FUNCS`、`_NON_CAUSAL_FUNCS`、`_expect_causal_gate_failure`、`_FRACDIFF_PRE_VALUES_GATES`、新增邊界測試九項、SPEC v60 Task 4.2 兩處；r2 收斂檔三家同一 P1 之修法（改函式名、不改 gate 訊息／容差）。未跑生成型 node。未發現可重現之意外漂移或未來洩漏漏測。

---

ASSUMPTIONS_VERIFIED: ① traceback 含 helpers 內 gate 名（numpy atol 與 metadata 裸 assert 實測）；② check() 路徑表外 AssertionError 皆經表列父 gate；③ 對齊 oracle 在捕獲區外且不在允許集。
TESTS_RUN: `pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q` → 9 passed 0.13s rc=0；`pytest --collect-only` 五檔 → 50 collected 0.06s rc=0；`venv/bin/python /tmp/ffstat_b6_capchk/probe.py` 三反例 ACCEPT、非 gate／coverage／尾擾動值 REJECT。
FAILURES_SEEN: 探針列數反例曾誤設 trunc_rows < full_rows 為真而 DID NOT RAISE，改為 trunc==full 後空訊息仍 ACCEPT；sampling 之 Failed 須以 BaseException 捕。皆探針腳本問題，非產品缺陷。
SCOPE_CHANGES: none（唯讀）
NUMERIC_OR_SCHEMA_IMPACT: none
產出: `handoffs/20260926-ffstat-b6-review-r3-grok.md`

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R2-P1-01

STATUS: DONE
