# IC1EB-B1-IMPL-RESULT-FIX1 — Codex review 三條修復

**Agent**: Grok 4.5 | **Date**: 2026-07-10 | **Status**: DONE  
**Review**: `handoffs/IC1EB-B1-REVIEW-codex.md`（BLOCK → 本輪修）  
**Prompt 約束**: `handoffs/IC1EB-B1-IMPL-PROMPT.md` 禁止事項全守

## 修了什麼（對照 finding）

| # | Finding | 處置 |
|---|---------|------|
| (1) BLOCKING D-B | `block_bootstrap` 對 centered z 重抽 | **改成** circular block 成對取 `x[idx],y[idx]`，每輪 `_spearman_ic` 重算 rank corr；null-imposed 置中 IC 分布算雙尾 p |
| (2) 邊界測試 | n&lt;2*block / 全相同值缺顯式 pytest | 新增 `test_t13_boundary_n_lt_2block_skips`、`test_t13_boundary_all_equal_rank_degenerate` |
| (3) 轉紅 receipt | 僅綠測試包 mutant，無真紅跑 | **臨時** production `t_stat *= 2` → 實跑主同判測試 FAILED exit=1 → **還原**（無 mutant 殘留） |
| (4) NON-BLOCKING | maxlags 成功路徑；apply_fdr ceremony | 新增 `test_t11a_explicit_maxlags_legal_override`；`apply_fdr` 仍走既有 `adjust_multiple_comparisons(...,"fdr_bh")`（一行實例呼叫） |

## 改了哪些檔（本 FIX1）

| 檔案 | 變更 |
|------|------|
| `tests/momentum/helpers/block_bootstrap.py` | D-B 成對重抽 + 每輪重算 Spearman IC |
| `tests/momentum/test_statistical_validator.py` | 邊界×2、maxlags legal override；T-1.3 同判斷言保留 |
| `momentum/Analysis/statistical_validator.py` | 僅 apply_fdr 呼叫寫法微調（行為不變）；**無** t×2 殘留 |

**未改**：`ic_filter_orchestrator.py` / `bootstrap_estimator.py` / `_fdr_bh` 本體 / `compute_ic_statistics` 簽名 / `data_cache/`。

## D-B 反例核對（review 給的可證偽例）

```
x=[1,2,3], y=[1,3,2], idx=[0,1,1]
obs mean(z)=1/3
fixed-z resample mean=1/3   # 舊錯法
pair recompute mean(z)=2/3  # 新正確法（重 rank）
pair recompute spearmanr=1.0
```

## 實跑 receipt

### Gate A — 驗收 pytest（全綠）

```bash
source venv/bin/activate
pytest tests/momentum/test_statistical_validator.py tests/momentum/core/ -q
```

**結果**：`78 passed, 1 warning in 3.19s`  
（較 B1 初交 75→78：+maxlags legal、+boundary skip、+boundary degenerate）

### Gate B — 解耦

```bash
grep -rn "from api\." momentum/ | wc -l
```

**結果**：`0`

### 無生產接線

```bash
git diff --exit-code HEAD -- momentum/Analysis/ic_filter_orchestrator.py momentum/Analysis/bootstrap_estimator.py
```

**結果**：exit 0（無 diff）

### T-1.3 同判（修後仍綠）

```bash
pytest tests/momentum/test_statistical_validator.py::test_t13_block_bootstrap_agrees_with_kernel -q
```

**結果**：PASSED（null/signal |p_kernel−p_boot|≤0.05 且顯著性同判）

### 邊界測試

```bash
pytest tests/momentum/test_statistical_validator.py::test_t13_boundary_n_lt_2block_skips \
  tests/momentum/test_statistical_validator.py::test_t13_boundary_all_equal_rank_degenerate -v
```

**結果**（含於 78 passed）：
- n=15,h=10 → `skip=True`, `skip_reason="n<2*block"`
- 全相同值 → `skip=True`, `skip_reason="rank_degenerate"`, 不 raise

### maxlags 合法 override

```bash
pytest tests/momentum/test_statistical_validator.py::test_t11a_explicit_maxlags_legal_override -q
```

**結果**：PASSED（h=5, maxlags=6 → L=6, se/t/p allclose oracle rtol=1e-8）

---

### 真實轉紅 receipt（finding 3）

**步驟**：臨時改 `statistical_validator.py`：

```python
t_stat = float(mean_z / se) * 2.0  # TEMP MUTANT
```

**命令**：

```bash
pytest tests/momentum/test_statistical_validator.py::test_t13_block_bootstrap_agrees_with_kernel -v --tb=short
```

**結果（非零退出）**：`RED_EXIT_CODE=1`

```
FAILED test_t13_block_bootstrap_agrees_with_kernel
AssertionError: null: |0.31159782791865875-0.591704147926037|=0.28010632000737823 > 0.05
assert 0.28010632000737823 <= 0.05
1 failed in 1.61s
```

**還原**：移除 `* 2.0` mutant；`rg TEMP MUTANT` → 無殘留；同測 PASSED；`t_stat = float(mean_z / se)` 乾淨。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: D-B 要求成對 (x,y) 重抽+每輪重 rank corr（非 fixed-z）；反例 mean 1/3 vs 2/3 已核；null/signal 同判 tol=0.05 仍成立
TESTS_RUN: pytest tests/momentum/test_statistical_validator.py tests/momentum/core/ -q → 78 passed; 轉紅 mutant 主同判 → exit 1 FAILED; 還原後 PASSED; grep from api. → 0
FAILURES_SEEN: 無（本輪一次修過）
SCOPE_CHANGES: none（僅 tests helper + test 追加 + apply_fdr 呼叫微調）
NUMERIC_OR_SCHEMA_IMPACT: bootstrap 驗證腿 p 計算路徑改為 pair-recompute IC（測試側）；production HAC kernel 數值公式未改；schema 無變更
```

STATUS: DONE
