# B1 實作結果 — FF 深稽 Task 1.0~1.4

**執行者**: Composer 2.5 | **日期**: 2026-06-28 | **派工**: `handoffs/20260627-FF-DEEPAUDIT-B1-DISPATCH.md`

## 完成項

| Task | 內容 | 主要檔案 |
|------|------|----------|
| 1.0 | correctness mode：`FF_CORRECTNESS_MODE` + `FactoryConfig.fail_open_indicators` + `compute_guard` | `compute_guard.py`, 10× `*_indicators.py`, `feature_config.py`, `feature_factory.py` |
| 1.1 | C1-2 prepare_inputs equivalence + TALIB_INPUT_SEMANTICS | `talib_input_semantics.py`, `test_prepare_inputs_equivalence.py` |
| 1.2 | C1-1 atomic differential + 雙 oracle | `test_atomic_differential.py` |
| 1.3 | BUG-1 BETA/CORREL hl 標準 + Beta/CloseVolume 別名 | `talib_wrapper.py`, consumer sync, `test_bug1_beta_correl.py` |
| 1.4 | BUG-2 獨立 reference + variant=simplified | `tests/references/volume_indicators_ref.py`, `test_handcoded_reference.py` |

## Consumer Sync Checklist

見 `handoffs/20260627-FF-DEEPAUDIT-B1-CONSUMER-SYNC.md`

## 新舊差異表路徑

- BUG-1: `tests/_golden/ff_deepaudit/beta_correl_v0_v1_diff.json`
- BUG-2: `tests/_golden/ff_deepaudit/handcoded_variant_diff.json`

## TESTS_RUN

```bash
source venv/bin/activate
pytest tests/feature_engineering/atomic/ tests/feature_engineering/test_adf_safe_skip.py -v
# 176 passed
grep -r "from api\." momentum/  # 0 results
```

## Mutation fail 摘要（TDD-first 探針）

| ID | Patch 點 | 預期 | 驗證 |
|----|----------|------|------|
| C1-0 | 刪 MFI from `_INPUT_TYPE_MAP` + registry re-init | `compute_all` raise | `test_correctness_mode.py::test_correctness_mode_raises_on_registered_indicator_failure` |
| C1-2 | 刪 ATR from `_INPUT_TYPE_MAP` + re-init | prepare_inputs ≠ semantics | `test_prepare_inputs_equivalence.py::test_mutation_delete_atr_from_map_fails_equivalence` |
| C1-1 | RSI `_prepare_inputs` close→open | ≠ talib(close) | `test_atomic_differential.py::test_mutation_wrapper_source_close_to_open_fails` |
| BUG-1 | 標準 BETA 若回退 close/volume | ≠ hl oracle | `test_beta_correl_dual_oracle` 語義分離斷言 |
| BUG-2 | EOM `*`→`/` | ≠ simplified ref | `test_handcoded_reference.py::test_mutation_eom_multiply_to_divide_fails` |

## 通過條件

- 標準 `BETA`/`CORREL` == `talib(high,low)`
- `Beta_CloseVolume`/`Correl_CloseVolume` == 舊 `talib(close,volume)` + metadata `variant=non_standard_close_volume`
- correctness mode 下已登錄指標失敗 raise（非 warning）
- 三方數據簽核：**未宣稱通過**（差異表已產，待 Claude 接回）

## ASSUMPTIONS_VERIFIED

- kline: `create_kline_storage_manager(cache_dir='data_cache/feature_klines')` BTCUSDT/12h 1696 列
- `abstract.Function('BETA').input_names` = high/low；wrapper 改後 `hl_statistics_BETA_*` 對齊
- Column 命名：`Beta_CloseVolume` → `Beta-CloseVolume`（`normalize_indicator_name`）
- Registry 變更後須 `INDICATOR_REGISTRY.clear()` + `initialize()` 才影響 mutation 探針

## FAILURES_SEEN

- 首輪：registry 快取導致 mutation 假綠；MACD 多輸出；手刻 ref float 容差 — 已修

## SCOPE_CHANGES

- none（未改 B2/B3；未改 `tests/_golden/failopen/baseline.json` / `batch2d/provenance.json` 本體）

## NUMERIC_OR_SCHEMA_IMPACT

- **BUG-1**: L1 欄名/schema 變更 — `hl_*_statistics_BETA/CORREL_*` 新標準；`close-volume_*_statistics_Beta-CloseVolume/Correl-CloseVolume_*` 保留舊語義
- **BUG-2**: metadata 新增 `variant=simplified`（數值不變）
- L2–L7 provenance 衍生鍵受 BUG-1 Affected Column Closure 影響 — §G v1 重凍待三方簽核

## HANDOFF_NOT_UPDATED

根 `HANDOFF.md` 由 Claude 維護；本檔為 append-only 執行端交接。

---

## C1-2 假綠修復（2026-06-28，派工 `handoffs/20260627-FF-DEEPAUDIT-B1-C12FIX-PROMPT.md`）

### 根因

`build_talib_input_semantics()` 從 `TALibWrapper.list_indicators()` / `_INPUT_TYPE_MAP` 衍生 oracle → mutation 同時污染 SUT 與 oracle（自指 tautology）。Codex review：刪 ATR 後 `test_prepare_inputs_byte_equal_to_semantics_table` 仍 15 passed。

### 修法

- `TALIB_INPUT_SEMANTICS` 改為 **134 條獨立硬編 mapping**（`talib_input_semantics.py`），**零 import** `talib_wrapper`
- `build_talib_input_semantics()` 僅回傳硬編表（`registry_names` 保留 API 相容）
- 次要：`test_correctness_mode_raises_across_engines_on_map_deletion` 參數化 5 個 talib engine（MFI/ATR/OBV/BETA/SAR）；cycle/pattern 指標走 `single`/`CDL*` 預設不在 map，fault-injection 不適用，仍以 `compute_guard` code-inspect + momentum 探針覆蓋

### C1-2 mutation 前後 pytest 證明

**Baseline（無 mutation）**

```text
pytest ...::test_prepare_inputs_byte_equal_to_semantics_table[ATR-params1] -v
# 1 passed
```

**Mutation 後（同 process 刪 ATR from `_INPUT_TYPE_MAP["hlc"]` + registry re-init）**

```text
# in-process 執行 parametrized test body（同 test_prepare_inputs_byte_equal_to_semantics_table[ATR]）
# wrapper len: 1 (single/close) vs semantic len: 3 (hlc) → AssertionError length mismatch
test_prepare_inputs_byte_equal_to_semantics_table[ATR] FAILED as expected
```

`test_mutation_delete_atr_from_map_fails_equivalence` PASSED（in-test mutation 探針）。

### TESTS_RUN（C1-2 fix）

```bash
source venv/bin/activate
pytest tests/feature_engineering/atomic/test_prepare_inputs_equivalence.py tests/feature_engineering/atomic/test_correctness_mode.py -v
# 24 passed
pytest tests/feature_engineering/atomic/ -q
# 51 passed
grep -r "from api\." momentum/  # 0 results
```

### ASSUMPTIONS_VERIFIED（C1-2）

- `talib_input_semantics.py` 無 `TALibWrapper` import（僅 docstring 提及）
- ATR mutation：`spec.input_type` 變 `single`；oracle 仍 `hlc` → byte 比對可證偽

### SCOPE_CHANGES（C1-2）

- none（僅 C1-2 oracle + correctness 跨 engine 測試；未動 BUG-1/2）

### NUMERIC_OR_SCHEMA_IMPACT（C1-2）

- none（測試/oracle 表 only）

---

## B1 完成批（2026-06-28，派工 `handoffs/20260628-FF-DEEPAUDIT-B1-COMPLETE-PROMPT.md`）

### BUG-2 canonical 升級

| 指標 | v0 simplified | v1 canonical | BTCUSDT/12h 差異（測試 run 產出） |
|------|---------------|--------------|-----------------------------------|
| ForceIndex | raw diff×volume | EMA13(diff×volume) | corr=0.516, max_abs_diff≈5.6e8 |
| Klinger | VF=vol×(2c-h-l)/(h-l) | trend-aware VF + cumulative cm + EMA34−55 | corr=-0.559, max_abs_diff≈2.2e5 |
| EOM | 不動 | 不動 | vs 1e8 ref corr≈1.0（僅 scale） |

- `volume_indicators.py`：Klinger/ForceIndex 改 canonical；metadata 移除 `variant=simplified`（EOM 保留）
- `tests/references/volume_indicators_ref.py`：獨立 canonical 實作（零 import 被測模組）
- 因果 MR：`test_handcoded_no_lookahead_invariant`（截尾 25 bar 前段不變）

### correctness-mode 8 engine 覆蓋

| Engine | fault-injection | 測試 |
|--------|-----------------|------|
| Momentum | 刪 MFI from hlcv map | parametrized + standalone |
| Volatility | 刪 ATR from hlc map | parametrized |
| Volume | 刪 OBV from close_volume map | parametrized |
| Statistics | 刪 BETA from hl map | parametrized |
| Trend | 刪 SAR from hl map | parametrized |
| Cycle | 刪 CCI from hlc map | parametrized |
| Pattern | 刪 BOP from ohlc map | parametrized |
| Microstructure | monkeypatch `_compute_amihud` raise | `test_correctness_mode_raises_on_microstructure_failure` |

### mutation 探針證據

```bash
bash scripts/mutation_probe_check.sh tests/feature_engineering/atomic/
# MUTATION-PROBE PASS: 6 個探針真跑過
pytest tests/feature_engineering/atomic/ -q
# 59 passed
grep -r "from api\." momentum/  # 0
```

| 探針 | 注入 | 預期 |
|------|------|------|
| `test_mutation_klinger_vf_sign_flip_fails` | VF trend 符號翻轉 | vs canonical ref AssertionError |
| `test_mutation_correctness_mode_off_vs_on` | 刪 MFI；off 不 raise / on raise | 自證 §B1.1 |
| `test_mutation_beta_input_type_close_volume_regression_fails` | BETA→close_volume map | ≠ hl oracle |

### TESTS_RUN（B1 完成批）

```bash
source venv/bin/activate
bash scripts/mutation_probe_check.sh tests/feature_engineering/atomic/
pytest tests/feature_engineering/atomic/ -q  # 59 passed
grep -r "from api\." momentum/  # 0 results
```

### ASSUMPTIONS_VERIFIED（B1 完成批）

- Klinger canonical = Investopedia/TradingView：trend on H+L+C, cumulative cm, VF=V×(2×dm/cm−1)×T×100, EMA(34,55)
- impl vs `volume_indicators_ref.klinger_canonical` corr=1.0, max_abs_diff=0
- ForceIndex impl vs ref corr=1.0（同 talib.EMA 路徑）
- golden 副作用：`tests/_golden/ff_deepaudit/*.json` 為 untracked，測試 run 後已刪除勿 commit

### FAILURES_SEEN（B1 完成批）

- 首輪：`test_mutation_correctness_mode_off_vs_on` 用 `fail_open_indicators=False` 導致 off 也 raise → 改 off 用預設 fail-open config

### SCOPE_CHANGES（B1 完成批）

- none

### NUMERIC_OR_SCHEMA_IMPACT（B1 完成批）

- **BUG-2 schema**：`hlcv_volume_ForceIndex`/`hlcv_volume_Klinger_34_55` 數值變 canonical；metadata 移除 simplified variant
- L2–L7 含上述欄位之 provenance 須三方簽核重凍

### HANDOFF_NOT_UPDATED

根 `HANDOFF.md` 由 Claude 維護。

---

## BUG-2 round-3（2026-06-28，派工 `handoffs/20260628-FF-B1-BUG2-R3-PROMPT.md`）

### Klinger 真 canonical（Stock.Indicators）

- **VF 公式修正**：`vf = volume * abs(2*((dm/cm)-1)) * trend * 100`（round2 缺 abs + 括號錯）
- `volume_indicators.py::_compute_klinger` 已改；trend/dm/cm 邏輯不變
- **獨立 oracle**：刪 `volume_indicators_ref.klinger_canonical`（自指拷貝）；改 8-bar 手推 VF literal + talib EMA 驗 KVO
- **§G 差異表**：`Klinger_round2_to_round3` 記 round2 錯公式 vs round3（corr≈-0.82）

### correctness-mode 補全

| Engine | fault-injection | 測試 |
|--------|-----------------|------|
| Entropy | monkeypatch `_compute_shannon_entropy` raise | `test_correctness_mode_raises_on_entropy_failure` + `test_mutation_entropy_off_vs_on` |
| TailRisk | monkeypatch `_compute_cvar` raise | `test_correctness_mode_raises_on_tail_risk_failure` + `test_mutation_tail_risk_off_vs_on` |

- `entropy_indicators.py`：`compute_all` 各 method 包 `guard_indicator_compute`

### mutation 探針

| 探針 | 注入 | 預期 |
|------|------|------|
| `test_mutation_klinger_missing_abs_fails` | 還原 round2 VF（無 abs） | vs 手推 VF literal AssertionError |

```bash
bash scripts/mutation_probe_check.sh tests/feature_engineering/atomic/
# MUTATION-PROBE PASS: 8 個探針真跑過
pytest tests/feature_engineering/atomic/ -q  # 64 passed
grep -r "from api\." momentum/  # 0
```

### ASSUMPTIONS_VERIFIED（round-3）

- Klinger canonical = Stock.Indicators：`vf = Volume * Abs(2*((dm/cm)-1)) * trend * 100`
- 8-bar worked-example VF：impl == 手推 literal（atol 1e-6）
- round2 vs round3 Klinger on BTCUSDT/12h：corr < -0.5（差異表 assert）
- entropy/tail_risk：off 不 raise、correctness on raise

### SCOPE_CHANGES

- none

### NUMERIC_OR_SCHEMA_IMPACT

- **Klinger round3**：`hlcv_volume_Klinger_34_55` 數值再變（round2→round3 abs 修正）；~73% bar 受影響
- ForceIndex/EOM 不變

### FAILURES_SEEN

- `_capture_klinger_vf` 首版 talib.EMA patch 遞迴 → 改存 `real_ema` 參考後 PASS
