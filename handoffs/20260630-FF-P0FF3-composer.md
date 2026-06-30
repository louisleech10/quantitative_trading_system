# P0-FF-3 多 TF 全鏈截斷 MR — Composer 設計腿（委員會定案）

讀碼為主；`estimate_max_warmup_bars` 實跑對照（single vs mtf）；**未跑慢全鏈 generate**。

---

## 1. 多 TF config 定案

### 1.1 Production / correctness 事實（讀碼）

| 來源 | primary | training | 備註 |
|------|---------|----------|------|
| `FactoryConfig` 預設 | `12h` | `["12h"]` | 單 TF 預設，非 production multi-TF |
| `DATA_MANIFEST` / 深稽鐵律 | — | `{1h,4h,12h}` | 10 symbol × 3 TF 真 kline |
| `freeze_failopen_baseline.py` | `1h` | `1h, 12h` | fail-open baseline，缺 4h |
| V-6 `test_mtf_align_golden` | `1h` 或 `12h` | 雙向 down/up | 對齊算法 golden，非全鏈 MR |
| B2 `test_ff_fullchain_truncation_mr` | `1h` | `["1h"]` | 單 TF 全鏈 MR |

`generate_features` 路由（`feature_factory.py:326-341`）：`len(training_tfs) > 1` → `MultiTFGenerator.generate_multi_tf`；`timeframe` 參數仍傳 **primary**。

### 1.2 P0-FF-3 測試 config（定案）

```python
PRIMARY_TF = "1h"
TRAINING_TFS = ["1h", "4h", "12h"]  # 含 primary；與 DATA_MANIFEST 三 TF 對齊
ALIGNMENT_MODE = "open_minus"       # B2 / V-6 down 路徑 / production 慣例
SYMBOL = "BTCUSDT"                    # 與 B2 一致
```

**理由**

1. **「高頻截斷」語意**：截斷對象 = primary（最細）TF 尾 k bars；primary 必須是 `1h`。
2. **「production multi-TF 全欄」**：DATA_MANIFEST 三 TF 全進 training，覆蓋 1h 自對齊 + 4h/12h as-of 對齊衍生欄（欄名含 `_4h_`、`_12h_`，見 `test_adf_safe_skip.py` 等）。
3. **不採 failopen 的 `1h+12h` 缺 4h**：中間 TF 對齊是額外風險面，P0-FF-3 應覆蓋。
4. **v1 不做 12h primary 矩陣**：V-6 已覆 up-direction；P0-FF-3 增量是「細 TF 截斷 + 粗欄前綴不變」，1h primary 即主戰場。12h primary 可列 P1 擴展。

其餘與 B2 `_values_gate_mr_config_payload()` 相同：全 atomic、`preprocessing` 開 winsor/rank/adaptive_zscore/gaussian、**關** fracdiff/adf、`cross_sectional=False`、`l7_dead_feature_drop=False`、`FIXED_ENV` 同 B2（含 `FFACT_MULTI_TF_PARALLEL=0`）。

---

## 2. 對齊 look-ahead mutation 注入

### 2.1 洩漏在前綴怎麼現形（讀碼推理）

`TimeframeAligner.build_asof_index_map`（`tf_aligner.py:161`）因果實作 = `searchsorted(..., side="right") - 1` + `source_close <= decision` 守衛。

- **因果路徑**：截斷 primary 尾 k → `end_date` 提前 → 各 TF layer0 同縮短；backward as-of 在 `[warmup, n_trunc)` 內應 byte-級穩定（B2 收斂 gate）。
- **look-ahead 路徑**：full 比 trunc **多載**尾端粗 bar → forward/錯誤 as-of 會讓**前綴列**的 `idx_map` 指到更晚的粗 bar → **粗 TF 衍生欄數值變**（非僅尾段）。
- **V-6 證據**：`before.json` 指紋 `1h@12:00 → 91729`（修復前錯值）；`test_real_generate_down_open_close_and_invariant` 斷言修復後 `close_12h_raw` 在 `12:00` **不等於** 91729。現形 = **值 oracle**，不是單純 NaN 邊界位移。

NaN mask：對齊邊界（V-6：`idx_map[0]==-1`，首個 valid @12）會產生暖機 NaN；look-ahead 可能改變 valid/invalid 邊界，但 **主偵測信號仍是 both-non-NaN 區間的值漂移**（mutation 實證 >> `rtol=2e-3`）。c2_2 尾端擾動 + align lookahead 為加強組合，非唯一手段。

### 2.2 注入點（定案）

**Monkeypatch `TimeframeAligner.build_asof_index_map`**（靜態方法），在 `_build_truncation_pair` 之前安裝；與 V-6 `_run_real_generate` 同一 hook，但改為 **主動突變** 而非 capture。

```python
_ORIGINAL_MAP = TimeframeAligner.build_asof_index_map

def _lookahead_build_asof_index_map(primary_ts, source_ts, source_dur_ns, primary_dur_ns, mode):
    """模擬修復前 forward 偏置：在因果 idx 上 +1（cap 到 len(source)-1）。"""
    idx = _ORIGINAL_MAP(primary_ts, source_ts, source_dur_ns, primary_dur_ns, mode)
    out = idx.copy()
    valid = out >= 0
    if np.any(valid):
        out[valid] = np.minimum(out[valid] + 1, len(source_ts) - 1)
    return out
```

**不 patch `align_to_primary` 本體**：CGSA / searchsorted 路徑皆經 `build_asof_index_map`（`tf_aligner.py:199-205`）；單點覆蓋面最大。

**不複用 `test_before_baseline_shows_lookahead` 為 mutation**：該測試只讀 frozen `before.json`，無 runtime 注入；**機制可複用**（同 hook），但 P0-FF-3 需 `pytest.raises(AssertionError)` + `_assert_truncation_invariants` 動態探針。

### 2.3 預期 FAIL 路徑

| 探針 | 預期 |
|------|------|
| `test_mutation_align_lookahead_fails` | patch `build_asof_index_map` → `_build_truncation_pair` + `_assert_truncation_invariants` → **AssertionError** |
| `test_mutation_align_lookahead_with_tail_perturb_fails`（可選加強） | 同上 + `patch_fetch` 尾 k OHLCV ±1e6（B2 c2_2）→ 必 FAIL |
| B2 既有 center/winsor/lag mutation | **改 config 為 multi-TF 後仍須 FAIL**（防抽樣/層覆蓋回歸） |

**Oracle 優先序**：values gate（交集 × both-non-NaN × `rtol=2e-3`）> 高 fill NaN mask exact > c2_2。粗 TF 欄（`_12h_` / `_4h_`）應為最早觸發欄族。

---

## 3. Window 估算

### 3.1 實跑 warmup（已驗證）

```
single 1h training=[1h]:        warmup=2051
mtf 1h training=[1h,4h,12h]:    warmup=2051
```

主導項 = L3 `W233`（`warmup_window.py` + atomic `range_max=233`），非 L6.5 `scale_window_for_native`（12h 上 360→30 primary bars，仍 < 2051）。

### 3.2 窗長公式（定案）

```python
TRUNC_K = 10                    # 與 B2 一致
POST_WARMUP_BARS = 20           # 與 B2 一致
ALIGN_MARGIN = 12               # TIMEFRAME_SECONDS["12h"] // TIMEFRAME_SECONDS["1h"]

def _required_window_bars_mtf(config_payload) -> int:
    factory = create_feature_factory(...)
    config = factory._resolve_config(config_payload)
    training = config.timeframes.training
    warmup = estimate_max_warmup_bars(config, PRIMARY_TF, training)
    return warmup + TRUNC_K + POST_WARMUP_BARS + ALIGN_MARGIN
# → 2051 + 10 + 20 + 12 = 2093 primary 1h bars
```

`ALIGN_MARGIN=12`：V-6 首個有效 12h 對齊在 primary index 12（`open_minus`）；保守吸收多 TF 邊界效應，避免 prefix 可比區貼近對齊斷點。

**截斷機制**：與 B2 相同——`_bar_window_dates(kline_df_1h, window_bars=2093, trunc_k=10)` 得 `start/full_end/trunc_end`；`patch_fetch` 仍只改 **primary 1h** kline（`AdapterRegistry.fetch_aligned` @ `timeframe==PRIMARY_TF`）。粗 TF 由 `MultiTFGenerator` 按同一 `end_date` 載入，不假裝「只截細不截粗」。

**kline 前置**：`requires_kline`；`BTCUSDT/1h` 列數 ≥ 2093（DATA_MANIFEST min_row_count 遠大於此）。

---

## 4. 複用 B2 基建（檔案結構定案）

### 4.1 不擴寫 B2 單檔

`test_ff_fullchain_truncation_mr.py` 已 ~1400 行；P0-FF-3 再塞入會混雜 P0-FF-2 / P0-FF-3 職責。

### 4.2 定案結構

| 檔案 | 職責 |
|------|------|
| **新建** `tests/feature_engineering/ff_truncation_mr_helpers.py` | 從 B2 **抽出**共用：`TruncationPair`、`GenerationArtifacts`、gates（columns/values/NaN 分層/覆蓋）、批次 parquet 讀、分層抽樣、`_build_truncation_pair`（參數化 `primary_tf` / `training_tfs` / `symbol`）、`FIXED_ENV`、mutation layer coverage |
| **新建** `tests/feature_engineering/test_ff_multitf_truncation_mr.py` | P0-FF-3 專用：multi-TF config、module-scoped pair fixture、C3 主 MR + mutations |
| **小改** `tests/feature_engineering/test_ff_fullchain_truncation_mr.py` | 改為 `from ff_truncation_mr_helpers import ...`（行為不變，P0-FF-2 回歸） |

**禁止** test-to-test 直接 import（anti-pattern）；一次性 helper 抽取成本 < 後續雙檔維護。

### 4.3 抽樣 / 效能

沿用 B2 定案（`handoffs/20260629-FF-B2-PERF-RECONCILE.md`）：批次讀 parquet + 分層抽樣 K≈40/組、總 3k–8k 欄、mutation 層硬保證。multi-TF 欄數約 ×2.5–3，**不降低** `B2_SAMPLE_MIN_COLUMNS=3000`。

### 4.4 Mutation 層覆蓋守衛擴展（定案）

在 `_assert_mutation_layer_coverage` 新增 **`MTF_align`** 條件：

```python
_COARSE_TF_TAG = re.compile(r"_(4h|12h)_", re.I)

def _has_align_layer(cols) -> bool:
    return any(_COARSE_TF_TAG.search(c) for c in cols)
```

`_select_required_probe_columns` 新增：**至少 1 欄**粗 TF L1（優先 `close_12h` 族）或 L3 `_12h_` + `_mean_w` 欄入 `required` ∪ sampled。

既有 L3/L4/L65_winsor 硬保證保留。

---

## 5. 測試清單（實作驗收）

| ID | 測試名 | 類型 | 說明 |
|----|--------|------|------|
| C3-1 | `test_c3_1_multitf_fullchain_bar_truncation_invariant` | 主 MR | module fixture 共用 full+trunc；gate 同 B2 收斂設計 |
| C3-2 | `test_c3_2_multitf_tail_perturbation_prefix_invariant` | 主 MR | 尾 k OHLCV ±1e6 → 前綴不變 |
| M3-1 | `test_mutation_align_lookahead_fails` | mutation | `build_asof_index_map` +1 → 必 FAIL |
| M3-2 | `test_mutation_align_lookahead_with_tail_perturb_fails` | mutation | M3-1 + c2_2 patch_fetch |
| M3-3..5 | 沿用 B2 center/winsor/lag | mutation | multi-TF config 下仍必 FAIL |
| — | `test_multitf_sampling_includes_align_layer` | 設計守衛 | 靜態/輕量：抽樣結果含 `_12h_` 或 `_4h_` 欄 |

**不在 v1**：multi-TF fracdiff 專屬 MR（B2 單 TF fracdiff MR 已存在；native TF L6.5 路徑另批）。

**Markers**：`@pytest.mark.requires_kline`、`@pytest.mark.slow`；CI smoke 排除 `-m "not requires_kline"`。

**驗收命令**（實作腿長 timeout）：

```bash
pytest tests/feature_engineering/test_ff_multitf_truncation_mr.py -m requires_kline -v --tb=short
# mutation 快驗（仍含 2× generate，但無 module baseline 時可單跑）
pytest tests/feature_engineering/test_ff_multitf_truncation_mr.py::test_mutation_align_lookahead_fails -m requires_kline -v
# P0-FF-2 回歸
pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py::test_c2_1_fullchain_bar_truncation_invariant -m requires_kline -v
```

預期 generate：multi-TF 全 atomic ≈ B2 單 TF 的 **2.5–3×** wall time（3 TF）；比對 <2min（B2 perf 定案）。

---

## 6. P0-FF-3 設計定案摘要

| 決策項 | 定案 |
|--------|------|
| Multi-TF 組合 | `primary=1h`, `training=[1h,4h,12h]`, `open_minus`, `BTCUSDT` |
| 截斷 | primary 1h 尾 `TRUNC_K=10`；B2 同 gate |
| Window | `estimate_max_warmup_bars` + 10 + 20 + **12** = **2093** bars |
| Align mutation | patch `TimeframeAligner.build_asof_index_map`（idx+1）；值 oracle 為主 |
| V-6 複用 | 同 hook；`before.json` 測試不當 mutation，只作歷史指紋參考 |
| 檔案 | helper 抽取 + `test_ff_multitf_truncation_mr.py`；B2 改 import |
| 抽樣守衛 | +`MTF_align` 粗 TF 欄必入樣 |
| 範圍外 v1 | fracdiff multi-TF、12h primary 矩陣 |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - generate_features multi-TF 路由: training>1 → MultiTFGenerator (feature_factory.py:326-341)
  - warmup single vs mtf [1h,4h,12h] 皆 2051 (python 實跑 estimate_max_warmup_bars)
  - V-6 look-ahead 現形為粗欄值變 (before.json + test_mtf_align_golden 讀碼)
  - build_asof_index_map 為 searchsorted/merge 共同入口 (tf_aligner.py:199-205)
  - DATA_MANIFEST TFs = {1h,4h,12h}; B2 僅單 1h

TESTS_RUN:
  - estimate_max_warmup_bars 對照腳本 PASS (single=2051, mtf=2051)
  - 未跑全鏈 generate (依 prompt)

FAILURES_SEEN: none

SCOPE_CHANGES: none (設計腿)

NUMERIC_OR_SCHEMA_IMPACT: 無（設計腿）；實作後僅增測試 + helper 抽取，不改引擎輸出
```

STATUS: DONE

---

## R2 reconcile 確認 (2026-06-30)

對照 `handoffs/20260630-FF-P0FF3-RECONCILE.md` 與 Composer 設計腿：config primary=1h/training=[1h,4h,12h]、helper 抽取結構、warmup=2051/window=2093、build_asof_index_map +1 wrap（不 patch align_to_primary）、值 oracle（B2 rtol2e-3）、對齊層覆蓋守衛（4h_/12h_）、metadata gate — 均忠實收斂；Codex 12h 邊界選窗為必要增補、不與 Composer 衝突。`reconcile_body_hash.sh` → `5da75188a4eebde3ef41a054462273e2c9958af27b5ad2b24dd7b1c3f72d93cd`。已 append RECONCILE-STAMP composer APPROVED。

```
ASSUMPTIONS_VERIFIED: reconcile 本體與 Composer 腿逐項對照；hash 與 codex 戳記一致
TESTS_RUN: bash scripts/reconcile_body_hash.sh handoffs/20260630-FF-P0FF3-RECONCILE.md → 5da75188...
FAILURES_SEEN: none
SCOPE_CHANGES: none (R2 確認+戳記 only)
NUMERIC_OR_SCHEMA_IMPACT: none
```

STATUS: DONE
