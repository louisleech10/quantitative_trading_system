# 派工:實作 B2 mutation 2修定案(Composer)

讀 `handoffs/20260630-FF-B2-MUTFIX-RECONCILE.md`(三方定案)。只改 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 的 2 探針。

## 修1:`test_mutation_l4_lag_shift_minus_one_fails`
- **注入**:不再只 patch `LagProcessor._apply_lag`。改 patch `LagProcessor.compute_all`(或等價覆蓋 fast path),使所有 lag 產出走 `shift(-lag)`,覆蓋 production fast path(`estimated_output_cols <= FFACT_LAYER4_FAST_PATH_MAX_COLS` 的快路)。
- **oracle 改 c2_2 擾動**:探針改成 `with pytest.raises(AssertionError): <跑 c2_2 尾端擾動不變量邏輯>`(即建 perturbed/unperturbed pair 比前綴),而非 c2_1 截斷。值基偵測 shift(-1) 把擾動未來帶入前綴。
- 確認注入真生效:可選小 targeted 驗(秒級,小窗)L4 lag 欄走 shift(-lag)。

## 修2:`test_mutation_fracdiff_calibration_perturb_fails`
- 加行為不變 spy:保存 `FeaturePreprocessor._calibration_series` 原函式;`monkeypatch.setattr` 成 wrapper(呼叫原函式 + 計數);測試體末 `pytest.raises` 後斷言 spy 計數 >0。
- 目的:① 滿足 `mutation_probe_static.py` touches_system(顯式 monkeypatch 被測符號)② 證明負控觸達 fracdiff 校準。**不改 `mutation_probe_static.py`**。

## 收尾(別硬撐全鏈到timeout)
- 改完 `python -m py_compile` + `python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 須**全 PASS**(含 fracdiff 探針不再被 flag)。
- **全鏈 5 mutation 真紅留 Claude 長 timeout 驗**。改完即交。
- 更新 `handoffs/20260627-FF-DEEPAUDIT-B2-RESULT.md`。完成 STATUS: DONE/BLOCKED。
