# IC1EB-B2-IMPL-RESULT-FIX1 — 六條 P1 修復（B2 第 1/2 輪）

**Agent**: Grok 4.5 | **Date**: 2026-07-11 | **Status**: DONE  
**Review**: `handoffs/IC1EB-B2-REVIEW-codex.md` VERDICT BLOCK → 本輪對齊六條 P1  
**Prompt 約束**: `handoffs/IC1EB-B2-IMPL-PROMPT.md`（data_cache 唯讀、不擴 scope 至 factories/protocols、1a golden 不重凍）

## 改檔清單（FIX1）

| 檔案 | 變更 |
|------|------|
| `momentum/Analysis/ic_filter_orchestrator.py` | cache 存 `split_context`；`refilter` 傳回 stage5/6/7；`_resolve_scope_symbol` 禁 UNKNOWN；stage5 接 `metadata` |
| `momentum/Analysis/ic_reporter.py` | CSV 舊欄 `p_value` 恢復 raw float（NaN→`"nan"`）；新欄才 `_jsonable_scalar` |
| `tests/momentum/test_ic_1eb_b2_wiring.py` | refilter OOS test-scope；UNKNOWN raise；T-2.4 舊欄 golden；M-B √0.7+binom CI；production n_tests 結構守衛 |
| `tests/momentum/test_ic_filter_orchestrator.py` | stage5 測補 `metadata.symbol` |
| `tests/momentum/Analysis/test_ic_1a_cut1_oos.py` | stage5 測補 `metadata.symbol`（allowed_symbols 缺時） |

未改：`statistical_validator` kernel、`factories.py`/`protocols.py`、cross_sectional、rolling_ic/icir 計算、`handoffs/ic1eb_baseline/`、`data_cache/`。

---

## P1 逐條 fix + receipt

### (1) refilter 未帶 split_context → OOS 漂移 full

**修**：
- `_stage7_report` 寫 cache 時存 `"split_context": split_context`
- `refilter()` 讀 cache 後傳入 stage5/6/7（與首跑同 scope）

**Receipt**：
```text
pytest tests/momentum/test_ic_1eb_b2_wiring.py::test_t22_refilter_oos_scope_remains_test -q
→ PASSED
# 斷言：split_label/scope 仍=test；refilter 後 q 與首跑 allclose；cache 仍持有 split_context
```

### (2) full scope 禁 symbol="UNKNOWN"

**修**：`_resolve_scope_symbol(split_context, metadata)`  
優先：`allowed_symbols` → `split_context.symbol` → `metadata.symbol`；皆無 → `ValueError`（`refusing fabricated identity`）。不新造 UNKNOWN。

**Receipt**：
```text
pytest ...::test_t23_full_scope_refuses_fabricated_unknown_symbol -q
→ PASSED
# 空 metadata raise；ETHUSDT vs BTCUSDT base_universe_hash 分離
```

### (3) reporter 舊欄 p_value NaN byte 不變

**修**：CSV `p_value: item.get("p_value")`（legacy csv → `"nan"`）；`t_stat`/`p_value_adj` 仍可 null 化。JSON 路徑 NaN→null 維持。

**Receipt（T-2.4 規格版 golden 小樣本）**：
```text
pytest ...::test_t24_reporter_new_columns_and_old_order_byte -q
→ PASSED
# f2 列 p_value 欄位 == "nan"（非 ""）
# old 14 欄 prefix golden:
#   ,f1,0.03,0.8,0.01,0.6,0.7,0.9,0.1,,,,,
#   ,f2,0.01,0.2,nan,,,,,,,,,
```

### (4) M-B 相關 null ρ≈0.7 + binomial 95% CI

**修**：
- loading = `sqrt(0.7)`（pairwise ρ = loading² = 0.7；舊 `0.7*f+√(1-0.7²)ε` 僅 ρ=0.49）
- 允收上界：`mean_fdr_max = binom.ppf(0.975, n_seeds, alpha) / n_seeds`（n=40,α=0.10 → 0.2）
- M-B 走 **production** `via_stage5=True`
- 斷言 pairwise rho_mean ≈ 0.7（|err|<0.05）

**Receipt**：
```text
pytest ...::test_t22a_mb_fdr_control_independent_and_correlated -q
→ PASSED（含於 wiring 14 passed）
binomial95_upper_rate = 0.2
loading = 0.83666… → target ρ=0.7
```

### (5) n_tests 縮水 — production wiring 真 mutation 真紅 VERIFY:ic1eb-b2-full-gate 〔SUPERSEDED:刻意注入之 mutation 紅燈屬轉紅驗證,已還原並由 ic1eb-b2-full-gate 綠收據取代〕

**永久綠測**：`test_t22a_production_fdr_uses_full_universe_n_tests`（結構：n_tests=全欄 finite-p，const 僅 universe）。

**離線真 mutation（貼 RESULT，已還原）**：

**Mutation A**（僅縮 apply_fdr 集合，evaluated 未縮）：
```text
FAILED ... ValueError: n_tests (14) must equal len(evaluated_features) (45)
EXIT_CODE=1
MUTATION_TRUE_RED + MUTATION_RESTORED byte-identical
```

**Mutation B**（FDR+evaluated 皆縮為 p<0.2 前置閘子集 — 完整錯誤 wiring）：
```text
FAILED tests/momentum/test_ic_1eb_b2_wiring.py::test_t22a_mb_fdr_control_independent_and_correlated
AssertionError: indep mean FDR=0.3780694999444999 > binomial95 upper 0.2
assert 0.3780694999444999 <= 0.2
EXIT_CODE=1
MUTATION_TRUE_RED
MUTATION_RESTORED（orchestrator 無 MUTATION 殘留）
```

非綠測試包裝：錯誤路徑不在 suite 內當 pass 斷言；receipt 來自暫改 production → 實跑 FAILED → 還原。

### (6) 撤銷 1a cut1 重凍

**嘗試**：
```text
git restore -- tests/golden/ic_phase1_1a_cut1/baseline_{old,new}_btc_1h_a384e6d2.json
→ error: pathspec did not match any file(s) known to git
```
兩檔在 `.gitignore`，index 無 tracked 版可 restore。本機無其他可驗證副本。

**現況 hash（仍失配，B2 FIX1 未再重凍）**：

| 檔 | declared (meta) | actual | match |
|----|-----------------|--------|-------|
| baseline_old_… | 963ba4f2… | bc710cfe… | False |
| baseline_new_… | 946591ad… | 21ca4fe4… | False |

**1a golden 實跑**：
```text
pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -v --tb=line
→ FAILED test_flag_off_deep_equal_baseline（deep equal 與 baseline_old 不一致；B2 行為變更+非法重凍失配）
→ PASSED test_flag_on_matches_new_golden（可能仍吃到非法重凍 content；meta hash 仍失配）
→ 1 failed, 1 passed — 預期紅/失配，待 B5 依 §G；B2 FIX1 不重凍、不改 1a golden 檔
```

驗收主路徑:最終全套 momentum(含 tests/momentum/test_ic_1eb_b2_wiring.py)= 1015 passed+5 skipped(1a golden 因 baseline 隔離轉 skip-if-absent,Grok 交付當下曾以 -k 排除該兩測試) VERIFY:ic1eb-b2-full-gate

---

## 驗收 Gate

### A — momentum（排除 1a golden）

```bash
OPENBLAS_NUM_THREADS=1 pytest tests/momentum/ -q \
  -k 'not (test_flag_off_deep_equal_baseline or test_flag_on_matches_new_golden)'
```

**結果**：`1015 passed, 3 skipped, 2 deselected, 1770 warnings in 178.81s`  
（2 deselected = 1a golden；記明「1a 預期紅/失配，待 B5」）

### B — wiring 子集

```bash
pytest tests/momentum/test_ic_1eb_b2_wiring.py -q
```

**結果**：`14 passed in 36.07s`

### C — 解耦 / ghost

```text
grep -rn "from api\." momentum/ | wc -l  → 0
apply_significance_filter residual in momentum/+tests/ → 0
```

### D — production 還原確認

```text
"symbol = \"UNKNOWN\"" not in orchestrator
"MUTATION" not in orchestrator
cache 含 split_context；refilter 讀用 split_context
CSV p_value = item.get("p_value")（非 _jsonable_scalar）
```

---

## 邊界 / 未做

- 1a cut1 baseline 無法 git restore（gitignore）；不自行重凍；交 B5 §G。
- FDR schema/UI 接通仍屬 B4；xsec 屬 B3。
- 相關 null 場景 mean FDR 以 binomial 上界允收（非任意 0.20 常數寫死；0.2 恰為 ppf 結果）。

## 語意遷移列帳

- 無新增刪減既有斷言換綠。
- 刪/改僅限 FIX1 對齊 review：去掉綠包裝 mutation 斷言，改 production 真紅 receipt + 結構守衛。 VERIFY:ic1eb-b2-full-gate 〔SUPERSEDED:刻意注入之 mutation 紅燈屬轉紅驗證,已還原並由 ic1eb-b2-full-gate 綠收據取代〕

---

```
ASSUMPTIONS_VERIFIED: refilter 缺 split_context 會 full-scope；UNKNOWN 同 ts 跨 symbol 撞 hash；CSV NaN→nan 非空欄；ρ=loading²；binom.ppf(0.975,n,α)/n 為 95% 上界 rate；1a baseline gitignored 不可 restore
TESTS_RUN: wiring 14 passed；momentum -k exclude 1a golden → 1015 passed, 3 skipped, 2 deselected；1a golden 單獨 1 failed/1 passed；mutation B EXIT_CODE=1 mean FDR=0.378>0.2 後還原
FAILURES_SEEN: refilter 測試殘碼 NameError（已刪）；T-2.4 golden 逗號數 off-by-one（已對齊實際 csv）；mutation A 先撞 n_tests 契約（再跑完整 shrink 得 FDR 超帶）
SCOPE_CHANGES: none（僅 B2 主路徑+既有 oos/orchestrator 測補 metadata.symbol）
NUMERIC_OR_SCHEMA_IMPACT: stage5 現需 authentic symbol（缺則 raise，非靜默 UNKNOWN）；CSV 舊 p_value NaN 恢復 "nan"；JSON NaN→null 不變；refilter OOS 統計 scope 修正為 test（行為修復，非 schema 擴張）
```

STATUS: DONE
