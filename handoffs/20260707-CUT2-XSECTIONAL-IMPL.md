# 20260707-CUT2-XSECTIONAL-IMPL

**執行端**: Composer | **時間**: 2026-07-07

## 正在做
- 無（本輪實作完成）

## 待辦
- Claude 接回 diff + 測試驗收 + 三方數據正確性簽核

## 阻塞
- 無

## 本次決策
- F3 審計 SplitPlan 用 `purge_semantic=timedelta` + `purge_gap=0`；時間隔離由 `test_min−train_max≥purge_td+embargo_td` 斷言（列序 purge_gap 與日曆切分實測不相容）

## 踩坑提醒
- `validate_split_pair_integrity` 列序 forbidden zone 在 train/test 日曆相鄰時會誤判 SplitPairLeakageError
- `_append_cross_sectional_labels` oracle 測試須 `droplevel("_symbol")` 再比對

## 產出
- `handoffs/CUT2-XSECTIONAL-IMPL-RESULT.md`

---

## Fix-round（2026-07-07 下午）

**正在做**: 無（FIX-1~4 完成）

**待辦**: Claude 接回 fix-round diff + Codex 複審 + 三方簽核

**阻塞**: 無

**本次決策**: F1 採 Option B（缺孔→NaN→F4）；F3 mutation 用 `effective_horizon=0`→`SplitPairLeakageError`

**踩坑**: kline 挖孔後 oracle 須用同份 holed kline；F4 all-NaN 先於 coverage 下界檢查

**VERIFY**: `pytest tests/api/test_ic_analysis_service.py tests/momentum/test_ic_cross_sectional_cut2.py -q` → 18 passed
