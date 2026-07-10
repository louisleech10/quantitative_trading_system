# IC1EB-B1-IMPL-RESULT — Task 1.1–1.3 統計 kernel

**Agent**: Grok 4.5 | **Date**: 2026-07-10 | **Status**: DONE  
**SPEC**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` v2.2 | **TODO**: `docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` Phase1  
**Prompt**: `handoffs/IC1EB-B1-IMPL-PROMPT.md`

## 改了哪些檔

| 檔案 | 變更 |
|------|------|
| `momentum/Analysis/statistical_validator.py` | 新增 `compute_hac_ic_statistics`、`apply_fdr` 及 NW Bartlett 輔助；**未**改 `_fdr_bh` / `adjust_multiple_comparisons` / `compute_ic_statistics` 簽名 / 生產接線 |
| `tests/momentum/helpers/__init__.py` | 新建（helpers 包） |
| `tests/momentum/helpers/block_bootstrap.py` | 新建 circular block bootstrap 驗證腿（B=2000，僅 tests/） |
| `tests/momentum/test_statistical_validator.py` | 追加 T-1.1a/b/c/d、T-1.2a/b、T-1.3（**既有斷言全保留**） |
| `pytest.ini` | 註冊 `slow_stat` marker（消除 UnknownMarkWarning；T-1.1b 使用） |

**未改**（禁項核對）：`_stage5_statistical_validation` / `_apply_thresholds` / rolling_ic 消費 / `bootstrap_estimator.py` / `data_cache/` / `handoffs/ic1eb_baseline/`。

## 實作要點（對 SPEC D-A/D-B/D-C）

- **HAC kernel**：pairwise dropna → `zscore(rank(·), ddof=1)` 貢獻 `z=u*v` → `auto_bw=int(4*(n/100)**(2/9))`，`L=max(auto_bw,h-1)` → NW Bartlett SE → `t=mean(z)/se` → `p=2*t.sf(|t|,df=n-1)`。fail-closed：`L≥n-1` 或 `n<max(8,2L)` → 全 NaN dict。顯式 `maxlags<h-1` → `ValueError`。**無** `ic_mean` 回傳（CODEX-2）。
- **apply_fdr**：finite 子集 → 既有 `adjust_multiple_comparisons(method="fdr_bh")`；NaN 保位；`n_tests=len(finite)`；不做 α 比較。
- **block bootstrap（tests only）**：`block=max(h,ceil(n**(1/3)))`；null-imposed 中心化 z 的 circular block 重抽；雙尾 p（+1 校正）。

---

## 驗收命令 receipt

### Gate A — pytest（全綠）

```bash
source venv/bin/activate
pytest tests/momentum/test_statistical_validator.py tests/momentum/core/ -q
```

**結果（最終重跑）**：`75 passed, 1 warning in 2.38s`  
（warning = joblib serial mode，與本刀無關；`slow_stat` 已註冊，無 UnknownMarkWarning）

### Gate B — 解耦

```bash
grep -rn "from api\." momentum/ | wc -l
```

**結果**：`0`

### 分測 verbose（T-1.x 八項）

```bash
pytest tests/momentum/test_statistical_validator.py::test_t11a_hac_matches_statsmodels_oracle \
  tests/momentum/test_statistical_validator.py::test_t11b_ma_ar1_false_positive_size \
  tests/momentum/test_statistical_validator.py::test_t11c_boundary_table \
  tests/momentum/test_statistical_validator.py::test_t11d_mi_use_t_not_normal_default \
  tests/momentum/test_statistical_validator.py::test_t12a_apply_fdr_matches_multipletests \
  tests/momentum/test_statistical_validator.py::test_t12b_apply_fdr_nan_preserve_and_n_tests \
  tests/momentum/test_statistical_validator.py::test_t13_block_bootstrap_agrees_with_kernel \
  tests/momentum/test_statistical_validator.py::test_t13_mutation_kernel_t_times_two_breaks_agreement -v --tb=line
```

**結果**：`8 passed in 2.34s`（全部 PASSED）

---

## 各 T-1.x 數值 receipt

### T-1.1a — statsmodels oracle

- 場景：`h∈{1,5,63} × n∈{64,512}` + ties 重場景；`rtol=1e-8`。
- fail-closed 場景（如 `n=64,h=63` → `L=62`，`n<2L`）斷言 NaN，不與 oracle 比。
- 非 fail-closed：se/t/p 與 `OLS(z,ones).fit(cov_type="HAC",cov_kwds={"maxlags":L},use_t=True)` allclose。
- 顯式 `maxlags=2 < h-1=4` → `ValueError`（測試 `test_t11a_explicit_maxlags_floor_raises` PASSED）。

### T-1.1b — M-A 假陽率（AR(1) φ=0.9 null × 200 seeds）

| 量 | 值 |
|----|-----|
| 設定 | n=5000, h=5, α=0.05, seeds=`10000..10199`, φ=0.9 |
| binomial 95% 允收帶（寫進碼） | count ∈ **[4, 16]**（`binom.ppf(0.025/0.975,200,0.05)`） |
| **舊法（i.i.d. t on z）** | **old_rej=86, old_rate=0.4300** ≫ α |
| **HAC 新法** | **new_rej=12, new_rate=0.0600** ∈ [4,16] |

實跑腳本摘要（與測試同 seed/公式）：
```
old_rej=86 old_rate=0.4300
new_rej=12 new_rate=0.0600 band=[4,16]
```

### T-1.1c — 邊界表

| 案例 | 結果 |
|------|------|
| 全 NaN feature | p=NaN, n_obs=0, maxlags=NaN |
| std=0 常數 | p=NaN, n_obs=64, maxlags=4 |
| h=1 | 有限 p 出值, maxlags=auto_bw |
| ties>50% | 有限 p + oracle allclose |
| n=8（下限）h=1 | 有限 p 出值（例 p≈0.78 依 seed） |
| n=7（下限-1） | p=NaN |
| h=63 短序列 n=64 | p=NaN, maxlags=62 |

### T-1.1d — M-I（n=32, seed=20260710）

```
kernel_p     = 0.365461621070435  (= oracle use_t=True)
oracle_t p   = 0.365461621070435
default_norm = 0.3583701449348651  (use_t 預設 False / Normal)
allclose(norm, t) = False
```

### T-1.2a — FDR vs multipletests

```
p={a:0.01,b:0.02,c:0.5}
q={a:0.03,b:0.03,c:0.5} n_tests=3
sm multipletests fdr_bh = [0.03, 0.03, 0.5]
```
含 ties p / 單元素用例 allclose PASSED。

### T-1.2b — NaN 保位

- `{}` → `({}, 0)`
- `{a:0.01,b:NaN,c:0.2,d:NaN}` → n_tests=2，b/d 的 q=NaN
- 全 NaN → n_tests=0，q 全 NaN

### T-1.3 — bootstrap 同判 + 轉紅 receipt

**綠路徑（固定 seed）**：

| 場景 | kernel p | boot p | \|Δp\| | 同判 α=0.05 |
|------|----------|--------|-------|-------------|
| null seed=0 n=300 h=5 | 0.612672 | 0.590705 | 0.02197 | 是（皆不拒） |
| signal seed=100 | 2.27e-07 | 0.000500 | 0.00050 | 是（皆拒） |

**轉紅 receipt（kernel t 人為 ×2 後對 bootstrap 套用同判斷言）**：

```
TURN_RED_RECEIPT: AssertionError
mutated |p diff|=0.2791068197575032 > 0.05
```

- 突變前 t 對應 p≈0.6127；t×2 → p_mut≈0.3116；vs boot p≈0.5907，|Δ|≈0.279 > 0.05。
- 測試碼內 `test_t13_mutation_kernel_t_times_two_breaks_agreement` 斷言 `agreement is False`（可證偽守衛，PASSED）；主同測 `test_t13_block_bootstrap_agrees_with_kernel` 保持綠。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - NW Bartlett se=sqrt(S/n) 與 statsmodels OLS+HAC use_t=True 數值恆等（rtol=1e-8）
  - auto_bw=int(4*(n/100)**(2/9)); L=max(auto_bw,h-1); p 用 t 非 Normal
  - 既有 _fdr_bh 與 multipletests fdr_bh allclose（apply_fdr 復用）
  - AR(1) φ=0.9 null 下舊 i.i.d. FPR≈0.43；HAC 於 n=5000 落入 [4,16]/200
TESTS_RUN:
  - pytest tests/momentum/test_statistical_validator.py tests/momentum/core/ -q → 75 passed
  - grep -rn "from api\." momentum/ | wc -l → 0
  - T-1.x 八項 -v → 8 passed
FAILURES_SEEN: none（首輪全綠，無 debug 第二輪）
SCOPE_CHANGES:
  - 額外改 pytest.ini 一行註冊 slow_stat（支撐 TODO marker；非生產邏輯）
  - 其餘無越界
NUMERIC_OR_SCHEMA_IMPACT:
  - 新 API 回傳 schema：per-feature {t_stat,p_value,se,n_obs,maxlags}；apply_fdr→(q_dict,n_tests)
  - 生產路徑未接線 → 現有 IC 輸出數值/檔案大小不變
  - 無 ic_mean 欄位
```

## 產出檔路徑

- `handoffs/IC1EB-B1-IMPL-RESULT.md`（本檔）
- `momentum/Analysis/statistical_validator.py`
- `tests/momentum/helpers/block_bootstrap.py`
- `tests/momentum/helpers/__init__.py`
- `tests/momentum/test_statistical_validator.py`
- `pytest.ini`（marker only）

STATUS: DONE
