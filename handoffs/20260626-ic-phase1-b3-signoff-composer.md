# IC Phase 1 B3 — 三方數據正確性簽核 + Code Review（Composer 獨立）

**Reviewer**: Composer 2.5（非實作者）  
**日期**: 2026-06-26  
**範圍**: Task 1.3/1.4（B3 洩漏紅線 + `ICSplitAdapter`）  
**對照**: `docs/IC_PHASE1_CONTRACT_{SPEC,TODO}.md` §P Task 1.3/1.4  
**驗證命令**: `pytest tests/momentum/core/test_split_contract.py tests/momentum/Analysis/test_ic_split_adapter.py -v` → **13/13 PASS**（含 live log 觸發 CPCV `/2` 降級）

---

## 逐項簽核

### 1. 跨 symbol 洩漏（多 symbol / sorted 整 frame）

**結論：正確**

**證據（真實程式路徑）**

| 檢查點 | 路徑 | 行為 |
|--------|------|------|
| 契約 fail-closed | `momentum/core/contracts.py:402-416` | `plan.symbol is None` → `CrossSymbolLeakageError`；`np.unique(symbols[row_index])` 必須 == `{plan.symbol}` |
| 已 sorted 但整 frame 多 symbol | `tests/.../test_split_contract.py:122-140` | BTC 尾接 ETH、`row_index=arange(len(ts))`、`symbol="BTCUSDT"` → `pytest.raises(CrossSymbolLeakageError)` |
| 未 per-symbol 堆疊 | `tests/.../test_split_contract.py:101-119` | 同上模式，`test_cross_symbol_purge_blocked` |
| per-symbol helper | `contracts.py:473-507` `split_per_symbol` | `groupby(symbol_col)` 後才呼叫 splitter，每 plan 帶 `symbol=str(symbol)` 並呼叫 `validate_split_integrity` |
| Adapter CPCV/WF | `ic_split_adapter.py:53-82`, `105-129` | 同樣 `groupby` + per-symbol sort + `validate_split_integrity` |

**繞過路徑審查**

- **空 `row_index`**（`contracts.py:399-400`）提早 return，跳過全部校驗——不構成跨 symbol 洩漏（無列被選），但 caller 若誤用空 plan 會靜默通過。
- **直接建 `SplitPlan` 不呼叫 `validate_split_integrity`**：契約為 opt-in，B3 尚未接 IC 主 pipeline；屬 Phase 1 已知 surface-only 風險，非本刀演算法錯誤。
- **Adapter / `split_per_symbol` 路徑**：無法產出跨 symbol `row_index`（已實測 `split_per_symbol` 於真實 kline 2 symbol × 50 rows → 2 plan pairs，symbol 純度皆 1.0）。

**無繞過**：已 sorted 整 frame 多 symbol 在 `validate_split_integrity` 層被擋下，與 SPEC codex-B5 一致。

---

### 2. 單 symbol gap（base timeline / rows-purge 洩漏 / 假綠 / 1.05）

**結論：正確**（演算法與 SPEC F8 一致；有 1 項配置層殘餘風險見下方「有疑子點」）

**證據**

| 檢查點 | 路徑 | 行為 |
|--------|------|------|
| gap 查 **base** per-symbol 時間線 | `contracts.py:425-437` | `base_ts = ts_arr[symbol_arr == plan.symbol]` → `np.max(np.diff(base_ts))` 與 `expected_freq` 比較 |
| 非 purge 後子集 | 獨立實測 | 刪 bar 後 `plan.row_index=np.arange(5)`（gap 在 index 10-12）仍 raise `TimestampDiscontinuityError: rows purge requires continuous timestamps at expected_freq` |
| rows-purge 遇缺 bar | `test_split_contract.py:143-159` | 真實 `kline_cache.h5` BTCUSDT/1h 取 40 rows，`np.delete(..., 10:13)` 刪 3 bar → `TimestampDiscontinuityError` |
| 非合成假綠 | 同上 + `test_ic_split_adapter.py:24-39` | 測試讀 `data_cache/feature_klines/kline_cache.h5`（BTC 20352 rows，`dt=3600s`） |
| threshold ×1.05 | `contracts.py:434` | `max_gap > expected_delta * 1.05`；TODO §Task 1.3 `ATOL=0.05`；對 1h 等距 bar 合理（容許浮點/邊界，不會放寬到跨日） |
| selected 子集單調 | `contracts.py:418-424` | `selected_ts` 仍檢查嚴格遞增，避免 CPCV purge 洞誤殺 train subset |

**有疑子點（配置層，非演算法假綠）**

- `expected_freq=None` 時 **跳過 gap 檢查**（實測通過）；符合 SPEC/TODO「允許 gap 模式須 timedelta purge」債務，但 `create_ic_split_adapter()` 預設 `expected_freq=None`（`factories.py:573-580`）——caller 未設 `1h` 則 gap fail-closed 不生效。
- `split_per_symbol` **無專屬 pytest**（手動實測 PASS）；建議 B6 G3 補 integration。

**非假綠**：gap 測試在真實 kline 上刪 bar，非純 `np.arange` 合成時間軸。

---

### 3. CPCV embargo 降級偵測（effective vs requested / L75-79 /2）

**結論：正確**

**證據**

| 檢查點 | 路徑 | 行為 |
|--------|------|------|
| CPCV silent `/2` 源碼 | `combinatorial_purged_cv.py:75-79` | `train_indices.size == 0` → `embargo_pct = max(0, embargo_backup / 2)` 重算 |
| Adapter 用 **requested** config 重算 | `ic_split_adapter.py:250-284` `_assert_requested_cpcv_embargo` | `embargo_len = int(n_samples * embargo_pct)`（原始值，非 `/2`）；`np.array_equal(returned, expected_train)` 不等 → `EmbargoRelaxedError` |
| 測試真觸發降級 | `test_ic_split_adapter.py:127-141` + pytest live log | WARNING `embargo 清空訓練集，自動降低 embargo`；ERROR `returned=2 expected=0 extra=[58, 59]`；`pytest.raises(EmbargoRelaxedError)` |
| 多 test group 演算法對齊 | 獨立實測 | `n_groups=4, n_test_groups=2, embargo_pct=0.05` → 6 folds **0 mismatches**（adapter expected == CPCV returned，無 false positive） |

**繞過**：`strict_embargo=False`（`ICSplitAdapter.strict_embargo`）可關閉偵測；預設 `True`（factory 同）。關閉後 relaxation 可能流到 `SplitPlan` 建構（小 train + 大 `purge_gap` 仍可能被 `SplitPlan.__post_init__` 擋下）。

---

### 4. WF adapter（區間 → arange / 是否改既有碼）

**結論：正確**

**證據**

| 檢查點 | 路徑 | 行為 |
|--------|------|------|
| 區間語意 | `walk_forward_validator.py:256-273` | 回 `((train_start, train_end), (test_start, test_end))`，`train_end = train_start + train_size`（半開） |
| arange 展開 | `ic_split_adapter.py:114-116` | `np.arange(train_range[0], train_range[1])` — 與 WF `[start, end)` 一致 |
| 測試對齊 | `test_ic_split_adapter.py:93-124` | `np.array_equal` vs `wf._generate_rolling_splits(220, 80, 30, 40)` + `btc_positions[arange(...)]` |
| 未改 WF/CPCV | `git diff momentum/Analysis/model_validation/{combinatorial_purged_cv,walk_forward_validator}.py` | **空 diff** |

**備註**：WF path 將 `embargo` 寫入 `SplitPlan` metadata（`len(group)*embargo_pct`），但 `_generate_rolling_splits` 本身不含 embargo 區間——與 SPEC「WF 只讀、不改內部」一致；strict embargo 偵測僅 CPCV path。

---

### 5. 是否使用真實 `kline_cache.h5`

**結論：正確**

**證據**

- `tests/momentum/core/test_split_contract.py:17` → `KLINE_CACHE_PATH = "data_cache/feature_klines/kline_cache.h5"`
- `tests/momentum/Analysis/test_ic_split_adapter.py:21` → 同路徑
- 檔案存在：11 symbols，BTCUSDT/1h **20352 rows**，`timestamp` 間隔 **3600s**（epoch 秒）
- 讀取方式：`h5py.File`（避開 PyTables dylib 問題，與實作者 handoff 一致）
- **未**用 `synthetic_binary_data` 或純 `np.arange` 時間軸代替 [C-3] 反例測試

---

## Code Review Findings

### BLOCKING
無。

### MAJOR
無。

### MINOR / 營運風險

1. **`expected_freq` 預設 None**（`create_ic_split_adapter`）— gap fail-closed 需 caller 顯式傳 `"1h"`；接線 B5/B6 時應寫死或從 timeframe 推導。
2. **`split_per_symbol` 無 pytest** — 手動驗證通過，建議 G3 golden 補覆蓋。
3. **空 `row_index` 跳過校驗** — 邊界合理但應在 1a 接線時禁止空 split 進 IC 計算。
4. **`strict_embargo` 可關** — 預設 on；文件化「僅 debug 用」即可。
5. **契約 opt-in** — B3 未接 `ic_analysis_service`；正確性紅線在接線前僅保護經 adapter/`validate_split_integrity` 的路徑（符合 Phase 1 contract-first 範圍）。

### POSITIVE

- gap 檢查用 **base symbol timeline** 而非 selected subset，正確實作 adversarial F8。
- CPCV embargo 偵測用完整 train set 相等性，實測抓到 L75-79 `/2` 降級（非僅 assert raise 空殼）。
- 解耦：`grep -rE "from api\." momentum/` → **0**。
- WF/CPCV 既有檔零改動。

---

## 整體 Verdict

**資料正確：PASS**

B3 在 Task 1.3/1.4 範圍內，跨 symbol 洩漏、單 symbol gap（`expected_freq` 已設時）、CPCV silent embargo 降級、WF 區間展開均 fail-closed 且以真實 `kline_cache.h5` 可證偽驗證。殘餘風險為 **caller 配置**（`expected_freq=None`）與 **契約尚未接主 pipeline**，不構成本刀演算法錯誤；建議 B6 G3 補 `split_per_symbol` + `expected_freq` 接線測試後關閉配置缺口。

---

## 結構化收尾（Reviewer）

```
ASSUMPTIONS_VERIFIED:
  - kline_cache.h5 存在且 BTCUSDT/1h dt=3600s（h5py 實讀）
  - CPCV L75-79 /2 降級路徑存在（源碼 + pytest live WARNING/ERROR）
  - gap 檢查用 base_ts 非 selected subset（獨立 Python 實測）
  - WF/CPCV 檔案無 git diff
TESTS_RUN:
  - pytest tests/momentum/core/test_split_contract.py tests/momentum/Analysis/test_ic_split_adapter.py -v → 13 passed
  - 獨立實測：split_per_symbol 真實 kline、multi-group embargo 0 mismatch、expected_freq=None gap 跳過
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀 review）
NUMERIC_OR_SCHEMA_IMPACT: none（review only）
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護；本檔為 Composer 獨立簽核 append-only
```

STATUS: DONE
