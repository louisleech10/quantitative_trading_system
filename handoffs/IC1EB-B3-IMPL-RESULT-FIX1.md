# IC1EB-B3-IMPL-RESULT-FIX1 — in-frame return_N 候選

**Agent**: Grok 4.5 | **Date**: 2026-07-11 | **Status**: DONE  
**Trigger**: `handoffs/IC1EB-B3-REVIEW-codex.md` FINDING 1  
**SPEC**: `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` §ADV-RESOLUTION L16 CODEX-3（in-frame `return_N`→同）

## 問題（已成立）

in-frame 分支候選硬編 `return_1`（orchestrator 舊 1038），未接受 resolver 已支援的一般 `return_N`。  
Codex 反例：MultiIndex frame 僅 `alpha`+`return_5`、無 labels_path → 應 `label_horizon=5`、`maxlags>=4`、不 raise；舊碼 raise。

## 修法（最小改動）

**優先序裁決**：維持既有候選優先序，僅把 `return_1` 位置泛化為 `return_N`。

```
label > return_N > future_return > target > y
```

**多 `return_N` 確定性規則（明文凍結）**：
1. 欄名 `re.fullmatch(r"return_(\d+)", name)` 命中者為候選
2. 取 **N 最小**
3. N 相同時取欄名 **字典序第一**

理由：N 最小與舊硬編 `return_1` 行為相容（有 `return_1` 時仍選它）；不引入新優先層級；不碰 labels_path / 其他分支。

### 改檔

| 檔案 | 變更 |
|------|------|
| `momentum/Analysis/ic_filter_orchestrator.py` | 新增 `_select_inframe_return_n_column`；in-frame 迴圈 `return_1`→`return_N` 槽 |
| `tests/momentum/test_ic_1eb_b3_xsec.py` | +3 測試：return_5 in-frame 反例、多 return_N 取 min N、label 仍優於 return_N |

**未改**：labels_path 分支、HAC kernel、FDR、排序、門檻、縱向 stage5、`data_cache/`。

## 新增測試

| 測試 | 斷言 |
|------|------|
| `test_t31_inframe_return_5_no_labels_path` | codex 反例：僅 alpha+return_5 → h=5、maxlags≥4、p 有限、不 raise |
| `test_t31_inframe_multi_return_n_picks_min_n` | return_5+return_3 欄序先 5 → 選 return_3、h=3；單元選取規則 |
| `test_t31_inframe_label_beats_return_n` | 同時有 label+return_5 → 仍選 label、horizon_unresolved |

## 驗收 receipt

### Gate A — full momentum  VERIFY:ic1eb-b3-fix1-full-gate

```bash
OPENBLAS_NUM_THREADS=1 python scripts/run_with_receipt.py --claim-id ic1eb-b3-fix1-full-gate -- \
  venv/bin/python -m pytest tests/momentum/ -q
```

**結果**：`1026 passed, 5 skipped, 1770 warnings in 180.77s`（exit 0）  
**receipt**：`handoffs/run_receipts/20260710T202717Z-ic1eb-b3-fix1-full-gate.json`  
（B3 基底 1023 + 本輪 +3 測試 = 1026）

### Gate B — T-3.1 單元  VERIFY:ic1eb-b3-fix1-t31-unit

```bash
OPENBLAS_NUM_THREADS=1 python scripts/run_with_receipt.py --claim-id ic1eb-b3-fix1-t31-unit -- \
  venv/bin/python -m pytest tests/momentum/test_ic_1eb_b3_xsec.py -q
```

**結果**：`11 passed`（exit 0）  
**receipt**：`handoffs/run_receipts/20260710T202727Z-ic1eb-b3-fix1-t31-unit.json`

### 解耦

```bash
grep -rn "from api\." momentum/ | wc -l  # → 0
```

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: CODEX FINDING-1 成立（舊硬編 return_1）；SPEC L16 in-frame return_N→同；優先序維持 label>return_N>future_return>target>y；多欄取 N 最小
TESTS_RUN: pytest tests/momentum/ → 1026 passed,5 skipped (VERIFY:ic1eb-b3-fix1-full-gate); test_ic_1eb_b3_xsec.py → 11 passed (VERIFY:ic1eb-b3-fix1-t31-unit); grep from api. → 0
FAILURES_SEEN: none（1 輪內綠）
SCOPE_CHANGES: none（僅 orchestrator in-frame 候選 + B3 測試檔）
NUMERIC_OR_SCHEMA_IMPACT: in-frame 有 return_N(N≠1) 時由 raise→可解析 h=N 並跑 HAC（修正 CODEX-3 缺口）；既有 return_1/label/labels_path 路徑數值不變
```

STATUS: DONE
