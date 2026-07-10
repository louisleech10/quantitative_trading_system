# IC1EB-B3-IMPL-RESULT — Task 3.1 cross_sectional 最小面

**Agent**: Grok 4.5 | **Date**: 2026-07-11 | **Status**: DONE  
**SPEC**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` §A D-H (v2) | **TODO**: Phase 3 Task 3.1  
**Prompt**: `handoffs/IC1EB-B3-IMPL-PROMPT.md` | **基底**: main `9df75d3`

## 改檔清單

| 檔案 | 變更 |
|------|------|
| `momentum/Analysis/ic_filter_orchestrator.py` | `_resolve_cross_sectional_label_horizon` 收斂為 Optional（禁 fallback-1）；新增 `_compute_hac_on_ic_series`；`analyze_cross_sectional` 於 `_label` 改名前解析 horizon；HAC `t_stat`/`p_value`/`p_value_adj`；metadata `horizon_unresolved`/`label_horizon`/`significance.*` |
| `tests/momentum/test_ic_1eb_b3_xsec.py` | **新建** T-3.1a/b/c + FDR/排序守衛 |
| `scripts/ic1eb_b3_mutation_probe.py` | **新建** mutation A(iid-swap)+B(label-rename) 真紅探針 | VERIFY:ic1eb-b3-mutation-probe 〔SUPERSEDED:mutation 紅燈屬轉紅驗證,還原後由 ic1eb-b3-full-gate 綠收據取代〕

**未改（禁項）**：ic_mean/icir/排序/門檻；縱向 stage5（B2）；xsec 單軸 labels_path 支援；`handoffs/ic1eb_baseline/` 唯讀；`data_cache/` 無 tracked 改動。

---

## 實作要點（對 D-H / CODEX-3）

1. **horizon 改名前解析**：labels_path 對 `_select_label_series` 原始欄名；in-frame 對命中候選欄；不可解析 → `sig_horizon=None`。
2. **h 可解析**：逐期 IC 序列作 z，NW `L=max(auto_bw, h-1)`，同 D-A cap/fail-closed；`t_stat`/`p_value` 取代 i.i.d.。
3. **h=None**：p 族（`p_value`/`p_value_adj`/`t_stat`）全 NaN；metadata `horizon_unresolved=True`（禁假 h=1 反保守 p）。
4. **FDR**：`apply_fdr` 對該路徑全 feature；`n_tests=finite p`；**排序仍 ICIR、無門檻**。
5. **單一真相源**：`_resolve_cross_sectional_label_horizon` 委派 `_resolve_label_horizon_from_column`，回 `None` 取代舊 fallback-1。coverage/split 結構下界在 h 不可解析時仍用 `structural_horizon=1`（**不**餵顯著性）。

---

## 驗收命令 receipt

### Gate A — full momentum  VERIFY:ic1eb-b3-full-gate

```bash
source venv/bin/activate
venv/bin/python -m pytest tests/momentum/ -q
```

**結果**：`1023 passed, 5 skipped, 1770 warnings in 188.60s`  
**receipt**：`handoffs/run_receipts/20260710T200047Z-ic1eb-b3-full-gate.json`

### Gate B — 解耦

```bash
grep -rn "from api\." momentum/ | wc -l
```

**結果**：`0`

### T-3.1 單元  VERIFY:ic1eb-b3-t31-unit

```bash
venv/bin/python -m pytest tests/momentum/test_ic_1eb_b3_xsec.py -q
```

**結果**：`8 passed`  
**receipt**：`handoffs/run_receipts/20260710T195731Z-ic1eb-b3-t31-unit.json`

### Mutation 真紅  VERIFY:ic1eb-b3-mutation-probe 〔SUPERSEDED:mutation 紅燈屬轉紅驗證,還原後由 ic1eb-b3-full-gate 綠收據取代〕

```bash
python scripts/run_with_receipt.py --claim-id ic1eb-b3-mutation-probe -- venv/bin/python scripts/ic1eb_b3_mutation_probe.py
```

**結果**：`MUTATION PROBE PASS: both A(iid) and B(label-rename)`；exit 0  
**receipt**：`handoffs/run_receipts/20260710T195407Z-ic1eb-b3-mutation-probe.json`

| Mutation | 注入 | 轉紅斷言 |
|----------|------|----------|
| A iid-swap | HAC t → i.i.d. t | T-3.1a kernel 直算 allclose 失敗 |
| B label-rename | 改名後對 `_label` 解析 | T-3.1b `horizon_unresolved is False` 失敗 |

---

## 各 T-3.1x receipt 摘要

### T-3.1a — p 非 None + kernel 一致 + i.i.d. 分離

- 合成 AR 共同因子 xsec frame；summary `p_value`/`t_stat` 與 `_compute_hac_on_ic_series` allclose(atol=0)；statsmodels HAC oracle rtol=1e-8；HAC t ≠ i.i.d. t（rtol=1e-3）。**PASSED**

### T-3.1b M-J — `return_5` maxlags≥4

- MultiIndex labels_path 欄 `return_5`（monkeypatch loader；禁單軸）；`label_horizon=5`；`maxlags==max(auto_bw,4)≥4`；`_label` 解析 → None。**PASSED**

### T-3.1c — horizon 不可解析

- 欄名 `label`；`horizon_unresolved=True`；p/t/q 全非有限；`n_tests=0`；`maxlags=None`。**PASSED**

### 附加守衛

- 排序仍 ICIR、無淘汰（輸出 2 feature）。  
- `p_value_adj` 與 `apply_fdr` 直算一致。  
- 既有 cut2 xsec：`7 passed`（回歸）。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: D-H z=逐期 IC；L=max(auto_bw,h-1)；horizon 改名前解析；_label 不可解析；單軸 labels_path 仍 raise；RECONCILE stamps APPROVED
TESTS_RUN: pytest tests/momentum/ → 1023 passed,5 skipped; test_ic_1eb_b3_xsec.py → 8 passed; cut2 xsec → 7 passed; grep from api. → 0; mutation probe exit 0
FAILURES_SEEN: T-3.1b 首輪 labels MultiIndex 非 monotonic → 改 sort_index 同 features 索引後綠（1 輪內）
SCOPE_CHANGES: none（僅 orchestrator + 新測試 + mutation probe）
NUMERIC_OR_SCHEMA_IMPACT: xsec summary p_value 由 None→HAC float/NaN；新增 p_value_adj；t_stat 改 HAC；metadata 增 horizon_unresolved/label_horizon/significance；ic_mean/icir/排序不變
```

STATUS: DONE
