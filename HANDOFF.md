# Handoff
**Agent**: Claude | **Time**: 2026-06-11 | **Branch**: main

## 結案:L1-L4 因果化 L6.5 perf 回歸 = winsor(已修),非 fracdiff
我的因果化(fff522b/f1714e4)把 L6.5 的 winsor 從全樣本改成 rolling,舊 `_rolling_quantile_numba` 每窗 full-sort → 在 45 萬欄全量上炸開。**fracdiff 不是主因(只 ~2%)**;先前「fracdiff 543x」是我讀 log 時間位置誤判,繞了一大圈 P1(已作廢)。

## 修法 P0(已 commit + push:d1440c3 kernel/oracle、81e475b flip 預設、e941c33/92aa963 housekeeping)
- `_rolling_quantile_numba` 旁加 `_rolling_quantile_sliding_numba`(per-column sliding sorted window,二分插入保等值時序+移除最舊等值,buffer window+1 防 numba OOB)。保 `(lower,upper)` API、4 caller、簽名不動。
- flag `FFACT_ROLLING_QUANTILE_KERNEL=sliding|legacy`(**預設 sliding**,call-time;legacy 一鍵回退)。
- **byte-identical 三方簽核**:Claude byte gate 16/16(array_equal+uint8-view,含 ties/inf/±0.0/NaN fuzz)+ Codex 實作 + Composer review「可合併」。e2e 雙路徑(Polars 19.2x/pandas 19.8x)byte-identical。
- 測試:`tests/feature_engineering/preprocessing/test_perf_winsor_identical.py`(reference `tests/_fixtures/rolling_quantile_legacy.py` + 真實 ETH fixture sha256)。

## 全量驗證(使用者真實 UI run,鐵證)
- 修正前 `case_search_api_20260610-before fix.log`:L6.5 跑 47 分到 **1.2%**、ETA 爆表 → **沒跑完**。
- 修正後 `case_search_api_20260611.log`:L6.5 = **36 分,100% 完成**。
- **兩 run d* cache 命中序列完全相同**(193/870…)→ 唯一變數=winsor kernel → 鐵證 winsor 是回歸主因、P0 已解。
- 殘差(36 分 vs 非因果 baseline 22 分):**因果正確性的合理成本**(因果把更多欄判為非平穩→更多 d* 搜尋:870 vs baseline 511),非 bug、非 winsor。

## 結論
- **P0 winsor 修復完成並全量驗證:L6.5 從「跑不完」→ 36 分完成,值 byte-identical(因果正確性不變)。**
- **P1(fracdiff 優化)結案=不需做**(只佔 ~2%)。
- 比較分析:見對話(可比照 docs/L65_20260514_VS_20260521_COMPARISON.md 格式存檔,使用者未要求存)。

## 鐵律(本任務血淚)
實測>假設:**用合成資料外推誤判多輪**(8GB死路/ADF硬底/fracdiff 543x 全錯),真相靠使用者真實 log + COMPARISON.md。2 輪 solo 失敗早該停。byte-identical 不可 atol。不偽造 adversarial。
