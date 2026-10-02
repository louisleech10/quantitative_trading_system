# FF-STAT B6 審查 r3 — COMPOSER

task-id: 20260926-FFSTAT-B6-REVIEW-R3  
brief: handoffs/20261002-FFSTAT-B6-REVIEW-R3-BRIEF.md  
family: COMPOSER  
brief-kind: review  
findings-round: R3  
note: 唯讀閉合輪；審查標的＝commit `1d09aaa4`（r2 捕獲改函式名封閉集合＋秒級邊界測 9 項）與 r2 synth。

## 必答（成對）

**(1a)** 就 composer：`COMPOSER-R2-P1-01` 原反例（warmup NaN mask 之 `warmup <檔>::<欄> NaN mask mismatch`、fracdiff atol 之 numpy `Not equal to tolerance` 頭、metadata 裸 assert／`present_timeframes missing`）在 `1d09aaa4` 下經 `_expect_causal_gate_failure` 之 traceback∩`_CAUSAL_GATE_FUNCS` 判定**被收**，與 r2 探針 `warmup_mask_actual: accepted=False` 之拒收狀態**閉合**；修法未改 gate 判準／容差，僅改捕獲契約並以 `test_ff_truncation_capture_boundary.py` 鎖正反例。**(1b)** `git show 1d09aaa4 --stat`；`PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q` → **9 passed in 0.18s** rc=0；重跑 r2 三反例 node：`::test_fracdiff_atol_values_gate_failure_is_accepted`、`::test_warmup_nan_mask_failure_is_accepted`、`::test_metadata_gate_failure_is_accepted` → **3 passed in 0.13s** rc=0（各 assert 回傳以 `_assert_values_gate:`／`_assert_warmup_nan_masks_equal:`／`_assert_metadata_gate:` 開頭）。

**(2a)** brief `assumed` ①②③ 在「意外漂移／漏測」威脅模型下**成立**；「我沒查」1–3 **不構成**本輪 P0／P1 阻擋（見下）。**(2b)** ① `excinfo.traceback` 取全路徑 `entry.name`（`:1522-1526`），atol／warmup／metadata 三例 pytest 實跑通過（必答 1b）；numpy／`_assert_arrays_values_close` 內 raise 時 stack 仍含 `_assert_values_gate`／`_assert_warmup_nan_masks_equal`。② `_assert_truncation_invariants`／`_fracdiff_check` 路徑上因果失敗皆自表列 gate 或其直接子呼叫拋出，表外輔助函式（`_assert_arrays_values_close` 等）不在 `allowed_gates` 但**不單獨**成為唯一 hit——gate 名仍在 frames；coverage／sampling：`coverage guard failed` 走 `_NON_CAUSAL_MARKERS`（`:1524`），sampling 用 `pytest.fail`（`:949-952`）非 `AssertionError`，不會被誤收為抓到。③ 對齊控制 `_run_align_lookahead_control` 先呼叫 `_assert_align_coarse_boundary_lookahead_detected`（捕獲區外，`:1688-1689`），再 `_expect_causal_gate_failure`+`_values_check`（`:1690`），與 `_assert_truncation_invariants` 內 align 無雙重 oracle 衝突。**我沒查 1**：coverage 訊息分流與 sampling 之 `pytest.fail` 與捕獲器契約一致，未見漏拒。**我沒查 2**：生產路徑 `check` 為 `_values_check` 之 lambda，失敗 traceback 含 gate 名；`test_non_gate_assertion_is_rejected` 已拒「訊息像值 gate 但非 gate 函式」；`<lambda>` 單獨不在白名單屬預期。**我沒查 3**：新增 gate 未入 `_CAUSAL_GATE_FUNCS` ⇒ 假紅（fail-closed），方向符合 v60「只收因果 gate」，非假綠。

**(3a)** 就捕獲邊界與 r2 P1 修補，**可**據 SPEC／manifest 排程主委 ~6.5h 全跑（串行、獨占）；本輪未跑生成型 node。**(3b)** 阻擋全跑者為時長／獨占／使用者「非必要測試不拖流程」，**非**本輪新見 P0／P1；codex r2 所留 assumed ②（全量 d* 控制若 strict 欄／d* 皆同將紅）仍交全跑收據判定，不升級為本家 blocking finding。

---

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
