# 派工:實作 B2 三方收斂設計(Composer)

三方數據簽核 PASS(FF 因果健全)。讀 `handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-RECONCILE.md` §二(定案設計)。改 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 的主 MR gate 對齊收斂設計。**不改 fracdiff 專屬 MR(維持嚴格)、不改 mutation 探針。**

## 改 1:columns gate(現 strict equality → 交集+門檻)
- `_assert_columns_gate`:比交集即可;**不對稱掉欄(only_in_full ∪ only_in_trunc)數量 > `max(100, int(0.1% × |union_columns|))` 才 fail**;assertion 列 ≤10 個 sample 欄名。低於門檻 = informational print 不 fail。

## 改 2:values + NaN mask 分層(現全段 mask exact → 分層)
- values:交集欄 × `[warmup:n_trunc)` × **both-non-NaN** 位置 `np.allclose(rtol=FLOAT16_RTOL=2e-3, atol=1e-12)`(已有,確認只比 both-non-NaN)。
- NaN mask 分層:
  - 對共同欄,各算該欄在 `[warmup:n_trunc)` 的 fill_rate(非NaN比例);
  - **fill_rate ≥ 0.95(full 與 trunc 皆是)→ NaN mask 須 exact**(違反 fail,防 mask-only look-ahead 躲);
  - fill_rate < 0.95 或 near-empty / 僅一側 → informational 記錄不 fail。
- **覆蓋率守衛**(防全被歸 informational 空轉):≥95% 共同欄有 ≥1 個可比 post-warmup both-non-NaN cell;否則 fail。

## 驗收(自跑,給夠 timeout)
- `pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py::test_c2_1_fullchain_bar_truncation_invariant -q`(單測 ~13分)PASS。
- `bash scripts/mutation_probe_check.sh tests/feature_engineering/test_ff_fullchain_truncation_mr.py`(慢,給 ≥2700s)→ 5 探針真紅(PASS)。
- 若你自跑會 timeout,**至少把改完的測試檔交回 + 說明哪些自驗了哪些沒**,Claude 接手用長 timeout 驗(別硬撐到 timeout 沒收尾)。
- 寫 `handoffs/20260627-FF-DEEPAUDIT-B2-RESULT.md`。跑後 git checkout 還原 golden。完成 STATUS: DONE/BLOCKED。
