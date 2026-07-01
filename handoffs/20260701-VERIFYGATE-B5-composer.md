# B5 實作收尾（Composer 2.5）

**Task**: VERIFYGATE B5 — Task 5.1/5.2/5.3  
**Agent**: Composer 2.5 (cursor-agent)

## 變更摘要

| 檔案 | 變更 |
|------|------|
| `templates/RESULT_TEMPLATE.md` | 新增 RESULT 硬欄位模板（枚舉 STATIC/RUNTIME/MUTATION + RECEIPTS + OPEN_PENDING） |
| `scripts/template_check.sh` | 新增 `result` kind 枚舉檢查；`spec` 加 W1 §A FACT-RECEIPT（僅「已確認」+資料結構詞） |
| `scripts/verification_claim_check.py` | 加 RESULT 結構欄讀取（PASS 需 receipt、NOT_RUN+已驗擋）；加 #6 `check_fingerprint_conflicts` |
| `tests/governance/test_verify_gate_b5.py` | 新增 13 項 B5 測試（隔離 tmp fixture） |

## ASSUMPTIONS_VERIFIED

- `docs/VERIFY_GATE_SPEC.md` §A 現況無「已確認+資料結構詞」行 → 新 FACT-RECEIPT 檢查不誤擋（實跑 template_check PASS）。
- §A FACT-RECEIPT 僅匹配 `DatetimeIndex|int64|dtype|型別|形狀|…` 等資料結構詞，不含純讀碼/grep 敘述（grandfather 設計）。
- B2 claim-object 路徑未改；僅在 `check_files` 尾端追加 RESULT 欄位檢查與 fingerprint 衝突掃描。
- 未碰 B3/B4 檔案（gate.sh、mutation_probe_check.sh、reconcile_stamps_check.sh、verify_audit_chain.py 等）。

## TESTS_RUN

```
$ venv/bin/python -m pytest tests/governance/test_verify_gate_b5.py -q
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/louis/Desktop/quantitative_trading_system
configfile: pytest.ini
plugins: asyncio-1.2.0, anyio-4.10.0, cov-7.0.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 13 items

tests/governance/test_verify_gate_b5.py::test_b5_result_runtime_pass_without_receipts_fails PASSED [  7%]
tests/governance/test_verify_gate_b5.py::test_b5_result_mutation_not_run_with_verified_claim_fails PASSED [ 15%]
tests/governance/test_verify_gate_b5.py::test_b5_result_valid_structured_fields_pass PASSED [ 23%]
tests/governance/test_verify_gate_b5.py::test_b5_template_check_result_invalid_enum_fails PASSED [ 30%]
tests/governance/test_verify_gate_b5.py::test_b5_template_check_result_valid_pass PASSED [ 38%]
tests/governance/test_verify_gate_b5.py::test_b5_fingerprint_conflict_green_then_red_without_superseded_fails PASSED [ 46%]
tests/governance/test_verify_gate_b5.py::test_b5_fingerprint_conflict_superseded_green_passes PASSED [ 53%]
tests/governance/test_verify_gate_b5.py::test_b5_spec_fact_receipt_missing_fails PASSED [ 61%]
tests/governance/test_verify_gate_b5.py::test_b5_spec_fact_receipt_present_passes PASSED [ 69%]
tests/governance/test_verify_gate_b5.py::test_b5_spec_pending_confirmation_passes PASSED [ 76%]
tests/governance/test_verify_gate_b5.py::test_b5_existing_verify_gate_spec_still_passes PASSED [ 84%]
tests/governance/test_verify_gate_b5.py::test_b5_existing_verify_gate_todo_still_passes PASSED [ 92%]
tests/governance/test_verify_gate_b5.py::test_b5_v7_zero_false_positive_regression PASSED [100%]

============================== 13 passed in 0.64s ==============================

$ bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md
TEMPLATE PASS (spec): docs/VERIFY_GATE_SPEC.md 含全部必填錨點，且無明顯空殼。

$ bash scripts/template_check.sh todo docs/VERIFY_GATE_TODO.md
TEMPLATE PASS (todo): docs/VERIFY_GATE_TODO.md 含全部必填錨點，且無明顯空殼。

$ venv/bin/python scripts/verification_claim_check.py --files docs/VERIFY_GATE_SPEC.md handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md docs/VERIFY_GATE_SPEC_PLAIN.md; echo "exit=$?"
WARN: 疑似極性詞 '驗證通過' 未收錄 — docs/VERIFY_GATE_SPEC_PLAIN.md:18
exit=0
```

## FAILURES_SEEN

- `test_b5_spec_pending_confirmation_passes` 初跑 FAIL：fixture §A 缺 C3「待確認：無」錨點 → 補 `- 待確認：無` 後通過。

## SCOPE_CHANGES

none

## NUMERIC_OR_SCHEMA_IMPACT

- 新增 `templates/RESULT_TEMPLATE.md` 結構 schema（枚舉欄位，不影響 runtime 數值）。
- `template_check.sh` 新增 `result` kind；`spec` §A 加 FACT-RECEIPT 錨點（只驗指標存在）。
- `verification_claim_check.py` 讀 RESULT 硬欄位與 fingerprint 衝突；不改 receipt/audit 格式。

## 設計備註

- #6 衝突：同 `claim_fingerprint` 出現 FAIL/紅燈後，未標 `SUPERSEDED:` 的 VERIFY 綠 claim 報違規；不做全域 render。
- FACT-RECEIPT：同行/鄰行須含 `FACT-RECEIPT:`；純設計用「待確認」放行。
