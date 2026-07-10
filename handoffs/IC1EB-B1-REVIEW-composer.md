# IC1EB-B1 Code Review — Composer（非實作者）

**審查員**: Composer | **日期**: 2026-07-10 | **對象**: Grok B1 未 commit diff  
**規格**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` v2.2 §D-A/D-B/D-C + `docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` Phase1 Task 1.1–1.3  
**實作者自報**: `handoffs/IC1EB-B1-IMPL-RESULT.md`（已獨立重驗，以下以 reviewer receipt 為準）

---

## 審查範圍

| 檔案 | 狀態 |
|------|------|
| `momentum/Analysis/statistical_validator.py` | modified |
| `tests/momentum/test_statistical_validator.py` | modified（僅追加 T-1.x；既有斷言未刪未弱） |
| `tests/momentum/helpers/block_bootstrap.py` | untracked 新檔 |
| `tests/momentum/helpers/__init__.py` | untracked 新檔（空 package） |
| `pytest.ini` | modified（`slow_stat` marker） |

生產路徑 `ic_filter_orchestrator.py` / `_apply_thresholds` / `compute_ic_statistics` 簽名：**本 diff 未觸及**（`git diff` 無變更；stage5 仍 `compute_ic_statistics(rolling_ic)` @ L2254）。

---

## (1) 凍結公式對照 SPEC D-A — **PASS**

| 條款 | 程式碼證據 | 獨立驗證 |
|------|-----------|----------|
| `auto_bw=int(4*(n_valid/100)**(2/9))` | `statistical_validator.py` L121 | n=512 → auto_bw=5 ✓ |
| `L=max(auto_bw, h-1)` | L122 | h=5,n=512 → L=5 ✓ |
| `p=2*t.sf(\|t\|, df=n_valid-1)` | L144 `stats.t.sf` | 與 Normal 不同（p_t≠p_norm）✓ |
| fail-closed: `L≥n_valid-1` 或 `n_valid<max(8,2L)` → 全 NaN | L125–127 `_hac_nan_result` | n=64,h=63 → L=62, `n<2L` → p=NaN ✓ |
| 顯式 `maxlags<h-1` → `ValueError` | L96–100 | `maxlags=2,h=5` → ValueError ✓ |
| spearman only，**無 `method` 參數** | `inspect.signature` 僅 `features_df,label,horizon,*,maxlags` | 無 `method` ✓ |
| 禁 Normal | 實作無 `norm.sf`；T-1.1d 斷言 Normal≠t | M-I PASS |

**可證偽反例（未觸發）**: 若改 `stats.norm.sf` 取代 `stats.t.sf`，T-1.1d `not np.allclose(p_normal, p_oracle)` 與 oracle rtol 測試應紅。

---

## (2) Oracle 實跑 statsmodels — **PASS**

Reviewer 獨立重打（非複製自報）:

```bash
pytest tests/momentum/test_statistical_validator.py::test_t11a_hac_matches_statsmodels_oracle -q
# 1 passed

python3 -c "..."  # n=512,h=5 獨立腳本
# se/t/p allclose rtol=1e-8 vs OLS(z,ones,cov_type=HAC,maxlags=L,use_t=True)
```

Receipt（n=512, h=5, L=5）:
- se: `0.04282713194102462` vs oracle `0.04282713194102463` ✓
- t: `6.010866550251934` vs `6.010866550251938` ✓
- p: `3.513e-09` vs `3.513e-09` ✓

場景覆蓋：T-1.1a 含 h∈{1,5,63}×n∈{64,512}+ties；fail-closed 場景跳過 oracle 比對邏輯正確。

---

## (3) T-1.1b M-A 假陽率 — **PASS**

Reviewer 獨立重跑（同測試公式/seed）:

```bash
pytest tests/momentum/test_statistical_validator.py::test_t11b_ma_ar1_false_positive_size -q
# 1 passed
```

| 量 | 實作者自報 | Reviewer 重跑 |
|----|-----------|---------------|
| binomial 95% 帶 [4,16] | ✓ | ✓ `(binom.ppf(0.025/0.975,200,0.05))==(4,16)` |
| 舊法 i.i.d. FPR | 86/200=0.430 | **86/200=0.430** |
| HAC 新法 FPR | 12/200=0.060 | **12/200=0.060** ∈ [4,16] |

舊法 `old_rate>0.20` 斷言成立（反保守 receipt）。

**可證偽反例**: 若 HAC kernel 靜默退回 i.i.d. SE，new_rej 應逼近 ~86，超出 [4,16]。

---

## (4) mean(z) 洩漏至 ic_mean（CODEX-2）— **PASS**

- `compute_hac_ic_statistics` 回傳鍵僅 `{t_stat,p_value,se,n_obs,maxlags}`；`mean_z` 為區域變數，未入 dict。
- T-1.1a 斷言 `"ic_mean" not in out` 且 `"mean_z" not in out`。
- Reviewer 抽樣 keys: `['maxlags','n_obs','p_value','se','t_stat']`，leak=∅。

**可證偽反例**: 若回傳增 `ic_mean=mean(z)`，T-1.1a 立即紅。

---

## (5) Task 1.2 `apply_fdr` — **PASS**

| 要點 | 狀態 |
|------|------|
| NaN 保位 | finite 子集進 BH；NaN key → q=NaN（T-1.2b PASS） |
| `n_tests=len(finite)` | `{}`→0；`{a,NaN,c,NaN}`→2 ✓ |
| 空 dict → `({},0)` | T-1.2b ✓ |
| 復用 `adjust_multiple_comparisons` | L185–186 呼叫 instance method → `_fdr_bh`；**未新寫 BH** |
| 不做 α 比較 | `del alpha` + docstring ✓ |

T-1.2a vs `multipletests(..., method="fdr_bh")` allclose rtol=1e-12（含 ties/單元素）。

**輕微觀察（非 BLOCK）**: 每次 `StatisticalValidator({})` 建 instance 包一層——行為正確，B2 可考慮 module-level 或靜態呼叫減少 ceremony。

---

## (6) Task 1.3 bootstrap（tests only）— **PASS**

| 要點 | 狀態 |
|------|------|
| 僅 `tests/momentum/helpers/` | `grep block_bootstrap momentum/` → 0 |
| `block=max(h,ceil(n**(1/3)))`, B=2000 | `block_bootstrap.py` L72,L53 |
| 同判 + \|p差\|≤0.05 | T-1.3 PASS |
| 轉紅 receipt（t×2） | Reviewer 獨立: `p_mut=0.311598`, `bp=0.590705`, `agreement=False` ✓ |

T-1.3 數值 receipt（reviewer）:
- null: kp=0.612672, bp=0.590705, |Δ|=0.022, 同判@α=0.05 ✓
- signal: kp≈2.27e-07, bp=0.000500, 同判拒絕 ✓
- mutation t×2: |Δ|=0.279>0.05, agreement=False ✓

**可證偽反例**: 若 mutation 測試被改成 `assert agreement is True`，應紅（目前守衛有效）。

**輕微觀察（非 BLOCK）**: signal 場景 p 絕對差大但仍在 0.05 容差內——符合 SPEC D-B 寫死容差，非實作缺陷。

---

## (7) 既有測試斷言未放寬/刪除 — **PASS**

`git diff tests/momentum/test_statistical_validator.py`:
- 既有 9 個測試函式**零行刪改**（diff 僅 `+` 追加 300 行 T-1.x）。
- `git diff ... | rg "^-.*assert"` → 無既有 assert 刪除。

Gate 全綠(VERIFY-EXEMPT:doc-example:composer-b1-r1-inline-receipt,委員實跑輸出在下方碼塊):
```bash
pytest tests/momentum/test_statistical_validator.py tests/momentum/core/ -q
# 75 passed in 2.64s
```

T-1.x 八項 `-v` → 9 passed（含 explicit maxlags raise）。

---

## (8) 未接線生產 — **PASS**

```bash
grep -n compute_hac_ic_statistics momentum/Analysis/ic_filter_orchestrator.py  # (none)
grep -n apply_fdr momentum/Analysis/ic_filter_orchestrator.py                  # (none)
```

`compute_ic_statistics(self, rolling_ic_dict: dict)` 簽名與 body 未改（HEAD vs working tree 無該函式 diff）。`_stage5_statistical_validation` 仍 L2254 `compute_ic_statistics(rolling_ic)`。

解耦: `grep -rn "from api\." momentum/ | wc -l` → **0**。

---

## 其他觀察（非 BLOCK）

1. **T-1.1a 缺口**: 僅測 `maxlags<h-1` raise，未測顯式合法 override 成功路徑（如 `maxlags=10,h=5` 仍 oracle 恆等）。SPEC M-C 變體偏 mutation；建議 B2 前可補，不阻 B1 kernel merge。
2. **`pytest.ini`**: 新增 `slow_stat` marker 消除 UnknownMarkWarning，與 TODO §0 一致；屬測試基礎設施，非生產邏輯。
3. **`tests/momentum/helpers/__init__.py`**: 空 package 檔，隨 bootstrap helper 合理。

---

## Reviewer 驗收命令摘要

```bash
source venv/bin/activate
pytest tests/momentum/test_statistical_validator.py::test_t11a_hac_matches_statsmodels_oracle \
  tests/momentum/test_statistical_validator.py::test_t11b_ma_ar1_false_positive_size \
  tests/momentum/test_statistical_validator.py::test_t12a_apply_fdr_matches_multipletests \
  tests/momentum/test_statistical_validator.py::test_t13_block_bootstrap_agrees_with_kernel \
  tests/momentum/test_statistical_validator.py::test_t13_mutation_kernel_t_times_two_breaks_agreement -q
# 5 passed (representative); full T-1.x 9/9; gate 75/75

grep -rn "from api\." momentum/ | wc -l  # 0
```

---

## 結構化摘要

```
ASSUMPTIONS_VERIFIED: 凍結公式/ORACLE/M-A/T-1.3 轉紅/CODEX-2/FDR 契約/生產未接線 — 均已獨立實跑
TESTS_RUN: pytest T-1.x 9 passed; gate 75 passed; 獨立 python oracle+M-A+mutation 腳本與自報一致
FAILURES_SEEN: none
SCOPE_CHANGES: reviewer 未改碼；實作額外 pytest.ini+helpers/ 在 B1 合理範圍
NUMERIC_OR_SCHEMA_IMPACT: 新 kernel API schema 僅模組級；生產輸出未變（未接線）
FINDINGS_BLOCKING: 0
FINDINGS_NONBLOCKING: 2（explicit maxlags 成功路徑未測；apply_fdr Validator 包裝 ceremony）
```

VERDICT: PASS
