# Reconcile — 20260926-ffstat-b6-review-r3

**來源** 20260926-ffstat-b6-review-r3-codex.md, 20260926-ffstat-b6-review-r3-composer.md, 20260926-ffstat-b6-review-r3-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/FFSTAT_SPEC.md

三家 proceed、零 finding；各以原反例（warmup／fracdiff atol／metadata 真實 gate 訊息）重跑確認本家 r2 條閉合（CLOSED：CODEX-R2-P1-01、COMPOSER-R2-P1-01、GROK-R2-P1-01），覆蓋／抽樣守衛、非 gate 拋出、尾擾動值 gate 仍拒。SPEC v60 Task 4.2 與測試本體收斂 ⇒ 主委獨占機器全跑兩縮小版檔（單週期 12 項、多週期 7 項，分段 < 2 小時）並產收據，收據交三家結果審。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| 放行：本輪逐項核對後無finding。原war | P3 | CODEX-R3-P3-00 | 採納（proceed） | other |
| 放行：本輪對`1d09aaa4`全面複驗（函式 | P3 | COMPOSER-R3-P3-00 | 採納（proceed） | other |
| 放行：本輪逐項核對後無finding；comm | P3 | GROK-R3-P3-00 | 採納（proceed） | other |

Verdict: 可合併（測試本體收斂，進入全跑）

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R3-P3-00

**斷言**: 本輪逐項核對後無 finding。原 warmup／fracdiff atol／metadata 反例均被新捕獲器接收，實際 coverage／sampling 守衛仍拒收，對齊 oracle 與主 MR 捕獲鏈未見衝突。

**碼證**: 複本命令 A → `9 passed in 2.65s`、rc=0；命令 B → `ACCEPT main_value`、`ACCEPT main_mask`、`REJECT real_coverage_guard`、`REJECT real_sampling_fail Failed`、`ACCEPT dstar_prevalues`、`ACCEPT align_oracle_then_main`、三條 `R2_CLOSED`、`PROBE_OK`，rc=0。helpers:1456–1472 定義六個因果函式與非因果守衛，1517–1530 以 traceback 做分流；1089–1126／1157–1171 之 check 呼叫鏈全部斷言落點已對照，align oracle 僅於1689之捕獲區外執行。命令 C → 四檔 `41 tests collected in 2.23s`、rc=0，無生成。

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#aba8dc92e20b;tests/feature_engineering/test_ff_truncation_capture_boundary.py#3332fe88dc49;docs/FFSTAT_SPEC.md#f8a327dafd6a;docs/manifests/FFSTAT.json#b1c0efc364c3

**類別**: other

## COMPOSER-R3-P3-00

**斷言**: 本輪對 `1d09aaa4` 全面複驗（函式名封閉集合、非因果守衛、尾擾動 fracdiff 子集合、9 項邊界測）後，無達 P0／P1 且可重現之捕獲契約缺陷。

**碼證**: `git show 1d09aaa4`；靜讀 `ff_truncation_mr_helpers.py:1459-1527,1703-1744,1688-1690`；pytest 9+3 node 見必答 **(1b)**；`git status --short -- momentum api frontend tests templates config` 與開跑前同型（僅既有 __pycache__／golden 等噪音，無本輪源碼寫入）。

**類別**: other

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#aba8dc92e20b;tests/feature_engineering/test_ff_truncation_capture_boundary.py#3332fe88dc49;handoffs/reconcile/20260926-ffstat-b6-review-r2/synth.md;handoffs/20261002-FFSTAT-B6-REVIEW-R3-BRIEF.md#cb281f5555b5;docs/FFSTAT_SPEC.md#f8a327dafd6a

正文：r2 `COMPOSER-R2-P1-01` 之前綴誤拒已由 traceback 函式名判定修復；主委 fact-verified 9 passed 與本輪一致。未跑 6.5h 全跑；未深查 ProcessPool／未來新增 gate 之維運文件化，與 brief「我沒查」一致。

---

ASSUMPTIONS_VERIFIED: 主委 fact-verified 1（9 passed ~0.19s）與本輪 pytest 一致；r2 synth 採納敘述與 `1d09aaa4` diff 一致。  
TESTS_RUN: `pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q` → 9 passed 0.18s rc=0；三 r2 反例 node → 3 passed 0.13s rc=0。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀）  
NUMERIC_OR_SCHEMA_IMPACT: none  
產出: `handoffs/20260926-ffstat-b6-review-r3-composer.md`

VERDICT: proceed  
BLOCKED-BY:  
CLOSED: COMPOSER-R2-P1-01

STATUS: DONE
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
