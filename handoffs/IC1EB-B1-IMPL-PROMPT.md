# IC 1e+1b — B1 實作派工(Task 1.1+1.2+1.3:統計 kernel)

**執行端**:Grok 4.5(首批真實任務,加密驗收中)
**SPEC**:`docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md`(v2.2 凍結)　**TODO**:`docs/IC_PHASE1_1E1B_SIGNIF_TODO.md`(v2.2)
**先讀**:TODO §0 全域規則 → Phase 1 全文(Task 1.1/1.2/1.3)→ SPEC §A D-A/D-B/D-C 與 §G-3。

## Scope(只做這些)
1. **Task 1.1** `compute_hac_ic_statistics(features_df, label, horizon, *, maxlags=None) -> dict[str, dict]` 落 `momentum/Analysis/statistical_validator.py`。逐 bar 貢獻序列+Newey-West;參數全寫死:`auto_bw=int(4*(n_valid/100)**(2/9))`;`L=max(auto_bw, horizon-1)`;`p=2*scipy.stats.t.sf(abs(t), df=n_valid-1)`(禁 Normal);fail-closed:`L>=n_valid-1` 或 `n_valid<max(8,2*L)` → 全 NaN dict;顯式 maxlags `<horizon-1` → raise ValueError。spearman only,無 method 參數。
2. **Task 1.2** `apply_fdr(p_values: dict[str,float], alpha: float) -> tuple[dict[str,float], int]` 同檔。finite p 子集餵既有 `adjust_multiple_comparisons(method="fdr_bh")`;NaN 保位 q=NaN;n_tests=len(finite);空 dict→({},0)。不做 α 比較。
3. **Task 1.3** `tests/momentum/helpers/block_bootstrap.py`(circular block,block=max(h, ceil(n**(1/3))),B=2000 固定 seed)——僅測試側,不進 momentum/ 生產樹。
4. **測試**:T-1.1a(statsmodels oracle `OLS(z,ones).fit(cov_type="HAC",cov_kwds={"maxlags":L},use_t=True)` 之 se/t/p `allclose(rtol=1e-8)`,含 h∈{1,5,63}×n∈{64,512}×ties 重場景)、T-1.1b(M-A:AR(1) φ=0.9 null×200 固定 seeds,舊法假陽率 receipt≫α、新法落 binomial 95% 允收帶,帶寫進測試碼,掛 `slow_stat` marker)、T-1.1c(邊界表:全NaN/std=0/h=1/ties>50%/n=下限 出值、n=下限-1 NaN/h=63 短序列 NaN)、T-1.1d(M-I:同資料 statsmodels use_t 預設(Normal)之 p 與 oracle p assert not allclose,n=32)、T-1.2a(vs `multipletests` allclose 含 ties/單元素)、T-1.2b(NaN 保位+n_tests)、T-1.3(bootstrap 與 kernel 同判,p 差≤0.05;附轉紅 receipt:kernel t 人為×2→測試轉紅,receipt 貼輸出後還原)。

## 禁止事項(違反=退件)
- 不接線生產:不改 `_stage5_statistical_validation`/`_apply_thresholds`/`compute_ic_statistics` 簽名;不動 `_fdr_bh`/`adjust_multiple_comparisons` 本體;不消費 rolling_ic。
- 不得放寬/刪除既有測試斷言(`tests/momentum/test_statistical_validator.py` 既有斷言全保留;語意遷移屬 B2 不在本批)。
- `mean(z)` 禁回傳/覆蓋任何 ic_mean 類欄位(CODEX-2)。
- data_cache 唯讀;禁 git checkout/stash/restore tracked 檔;`handoffs/ic1eb_baseline/` 唯讀。
- 解耦:`grep "from api\." momentum/` → 0 保持。kernel 熱迴圈不 log。
- 統計測試:固定 seed;允收帶寫進測試碼;長測掛 `slow_stat` + 預算上限。

## 驗收命令(全綠才交)(VERIFY-EXEMPT:doc-example:dispatch-prompt-future-commands)
```bash
source venv/bin/activate
pytest tests/momentum/test_statistical_validator.py tests/momentum/core/ -q
grep -rn "from api\." momentum/ | wc -l   # 必須 0
```

## 交付
- 產出摘要寫 `handoffs/IC1EB-B1-IMPL-RESULT.md`:改了哪些檔、每條 T-1.x 的實跑 receipt(命令+關鍵輸出)、轉紅 receipt、假陽率數字、邊界表結果。
- 兩輪解不了的 bug/測試/疑問 → 停手寫入 RESULT 標 `BLOCKED`,交回編排端(斷路器,禁硬幹)。
