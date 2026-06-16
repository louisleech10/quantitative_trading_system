# #2 d* fracdiff 設計委員會 — Composer 2.5 獨立版

> 日期：2026-06-15 | 角色：設計委員會（讀取型）| 使用者決策：**選 A 修復對齊**
> 背景：`docs/DSTAR_FRACDIFF_NONCGSA_FINDING.md` | 未讀其他 agent handoff 報告

---

## 1. 問題重述（已驗證）

非 CGSA frame path：`FeaturePreprocessor.transform()` → `_transform_single(source_layer=None)` → `_apply_fractional_differencing` → `_filter_fracdiff_target_columns` 在無 `source_layer` 時依 `_FRACDIFF_LAYER_RE = r"^(L\d+)_"` 解析欄名。生產欄名為裸名（如 `close_trend_EMA_5`），regex 全失敗 → 204 次 `unparsed_columns=2000/2000` → fracdiff/ADF/d* **靜默 no-op**。

CGSA path：`transform_registry_groups` 對每個 registry group 呼叫 `_transform_single(..., source_layer=_group_layer_name(group))`（`group.layer` → `L1`/`L2`/…），走 `_filter_fracdiff_target_columns` 的 `if source_layer:` 分支，**不依欄名前綴**（見 `test_fracdiff_registry_layer_filter_uses_group_metadata`）。

---

## 2. (a) `_run_layer6_5_preprocessor` 收的 `all_features` 是否保有 column→layer？

**結論：否。扁平 DataFrame 無 layer 歸屬；combine 前的 provenance 在 factory 內可重建但未傳遞。**

### 證據

| 觀察 | 檔:行 |
|------|-------|
| frame path 在 L6.5 前 `_combine_layers([layer1…layer6])` 橫向 concat，欄名不加重命名 | `feature_factory.py:348-364`, `3619-3635` |
| `_run_layer6_5_preprocessor` 只收 `all_features: pd.DataFrame`，無 layer 參數 | `feature_factory.py:2478-2517` |
| 非 CGSA 呼叫 `preprocessor.transform(all_features)`，無 `source_layer` | `feature_factory.py:2517`；`feature_preprocessor.py:215` |
| `_build_preprocessing_context` 只記 `feature_columns` 扁平列表 + hash，**無** column→layer map | `feature_factory.py:2613-2648` |
| `PreprocessingContext` dataclass 欄位無 layer map | `_d_star_cache.py:31-43` |
| CGSA 對照：layer 來自 `ColumnGroup.layer`（`group.layer.value`） | `feature_preprocessor.py:2217-2222`, `812`, `1819` |

### 補充

- Layer provenance **在 combine 前存在**：`layers = [layer1, layer2, …, layer6]` 順序固定（`feature_factory.py:348`）。
- `_combine_layers` 可能 drop duplicate columns（`feature_factory.py:3637-3651`），map 須與 dedup 規則一致（`keep="first"`）。
- 生產欄名慣例：`close_trend_EMA_*`（L1）、`*_Momentum_L{n}`（L2 derived）等——**無法**可靠用 suffix heuristic 取代 provenance（L3+ 欄名亦無 `L3_` 前綴）。

---

## 3. (b) 最小正確對齊設計（選 A）

### 原則

對齊 CGSA 語意：**fracdiff 目標層由 column 的來源 layer 決定，不由欄名字串 regex 推斷**。已有 `source_layer` 分支與測試（`test_fracdiff_registry_layer_filter_uses_group_metadata`），frame path 應餵同等資訊。

### 建議方案（最小 diff、不改輸出 schema）

**Step 1 — Factory 在 combine 時建立 map（單一真相來源）**

```python
# feature_factory.py — 新增靜態 helper
_LAYER_LABELS = ("L1", "L2", "L3", "L4", "L5", "L6")

def _build_column_layer_map(layers: List[pd.DataFrame]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for label, layer_df in zip(_LAYER_LABELS, layers):
        if layer_df is None or layer_df.empty:
            continue
        for col in layer_df.columns:
            key = str(col)
            if key not in mapping:  # align with keep="first" dedup
                mapping[key] = label
    return mapping
```

在 `generate_features` frame path（`feature_factory.py:363-378`）於 `_combine_layers` **之前**建 map，傳入 `_run_layer6_5_preprocessor(..., column_layer_map=...)`.

**Step 2 — 擴充 preprocessor 消費 map（不 rename 欄）**

優先選項（改動面最小）：

1. `FeaturePreprocessor.__init__` 或 `transform()` 接受 `column_layer_map: Optional[Mapping[str, str]]`，存為 `self._column_layer_map`。
2. `_filter_fracdiff_target_columns` 在 `source_layer is None` 時：
   - 若 `column in self._column_layer_map` 且 `map[column] in _fracdiff_apply_to_layers` → **target**
   - 否則 fallback 現有 regex（保留 synthetic `L1_*` / 測試相容）
3. `_transform_single` / `_transform_chunked` 傳遞 map（chunked path 目前 `2651` 亦無 layer，須一併接線）。
4. `_group_requires_slow_transform` 中 `source_layer None` 的 column filter（`1205-1206`）同步使用 map。

**不建議**：在 `_combine_layers` 對生產欄名加 `L1_` 前綴——會改 `feature_schema_hash`、破壞既有 HDF5/下游 consumers。

**不建議**：僅靠欄名 heuristic（`*_Momentum_L5` → L2）——L1/L2 邊界不完整，與 CGSA registry 不一致。

### ADF / d* cache 連帶

map 修好後，frame path 的 fracdiff 會真正執行；`DStarCache` 仍依 `PreprocessingContext.symbol/timeframe`（`feature_factory.py:2618-2619`）。生產 run 有 `_current_symbol/timeframe` → cache 可寫。無需另開「接線」任務，但 SPEC 應驗證修後 `data_cache/feature_preprocessing/d_star_*.json` 對非 CGSA run 有新增。

### Scope 邊界

| 檔案 | 變更 |
|------|------|
| `feature_factory.py` | `_build_column_layer_map`、L6.5 呼叫鏈傳 map |
| `feature_preprocessor.py` | map 消費、`_filter_fracdiff_target_columns`、chunked path |
| `scripts/build_l65_golden.py` | tier2a d_star 匯出（見 §5） |
| 測試 | 新增 frame-path parity + map unit test |

`PreprocessingContext` 擴欄位為可選優化，非必須；instance-level map 足夠。

---

## 4. (c) Golden 驗證策略：CGSA == 非 CGSA

### 分層

| Tier | 目的 | 做法 |
|------|------|------|
| **T1 單元** | map 正確性 | `_build_column_layer_map` 對已知 layer DFs；dedup 與 `_combine_layers` 一致 |
| **T2 過濾** | 對齊 CGSA filter 語意 | 裸名 + map → 與 `source_layer="L1"` 同結果（延伸 `test_l65_parallel.py:214-228`） |
| **T3 數值 parity（必做）** | 修後非 CGSA 輸出 ≡ CGSA | 真實 kline：`FFACT_USE_CGSA=1` vs `0`，同 symbol/tf/window（建議 `BTCUSDT/12h`，與 finding 實測一致） |
| **T4 d* parity** | cache 語意一致 | 比對兩 path 對 L1/L2 non-stationary 欄的 d*（允許 cache hit 路徑差異，但 miss 時數值一致） |
| **T5 golden 重生** | 回歸錨點 | 修後重跑 `build_tier2_synthetic` / tier2b；更新 `tests/golden/l65/*` |

### T3 可證偽斷言（建議）

```python
# 偽代碼 — 須用真實 data_cache/feature_klines
os.environ["FFACT_USE_CGSA"] = "1"
out_cgsa = factory.generate_features(..., persist=False, short_window)

os.environ["FFACT_USE_CGSA"] = "0"
out_frame = factory.generate_features(..., persist=False, short_window)

# 取 L1/L2 交集欄（由 map 或 registry metadata 定義）
common = intersect_columns(out_cgsa, out_frame)
np.testing.assert_allclose(out_cgsa[common], out_frame[common], rtol=..., atol=..., equal_nan=True)
```

**注意**：CGSA path L6.5 後回傳空 frame（`feature_factory.py:2508-2511`），L7 從 registry 讀——parity 須在 **L7_raw 產物** 或 **L6.5 後中間抽樣** 比對，不能比 `generate_features` 直接回傳的 DataFrame。實作時應 hook `feature_storage` / registry export 或加 test-only 抽樣 API（SPEC 需明示）。

### 數值/schema 影響（選 A 必然）

- 非 CGSA path **新增** fracdiff 數值（原本 no-op → 有差分），輸出與 CGSA 對齊為目標。
- 欄名/schema **不變**（無 rename）。
- d* cache 檔案可能新增（非 regression）。

---

## 5. (d) tier2a「Synthetic d_star output is empty」— 同源嗎？

**結論：症狀同批處理，根因不同源。BATCH3 triage「同源」過度簡化。**

### 證據對照

| 維度 | 生產 frame no-op | tier2a golden 失敗 |
|------|------------------|-------------------|
| 欄名 | 裸名，regex 全 fail | `L1_synthetic_*` / `L2_synthetic_*`（`build_l65_golden.py:166`）→ regex **可解析** |
| fracdiff 是否執行 | 否 | **是**（前綴滿足 `_FRACDIFF_LAYER_RE`） |
| 失敗點 | filter 回空 | `_run_l65_full_preprocessing` 讀取 d_star（`236-241`, `252-253`） |
| 直接原因 | 無 layer map | `preprocessor._d_star_cache = {}` 後，`transform` 用 ephemeral `DStarCache`（`3215-3230`），**未寫回** `self._d_star_cache`；`dict({}).items()` → 空 |

### tier2a 修法（與 frame map 正交，但應同 PR 修）

```python
def _run_l65_full_preprocessing(frame):
    ctx = PreprocessingContext(symbol="SYNTHETIC", timeframe="golden", row_count=len(frame), ...)
    preprocessor = FeaturePreprocessor(config, context=ctx)
    preprocessor._d_star_cache_shared = True  # 讓 cache 掛在 self._d_star_cache
    processed = preprocessor.transform(frame)
    cache = preprocessor._d_star_cache
    d_star = {
        col: float(entry["d_star"])
        for col, entry in (cache._entries if cache else {}).items()
        if entry.get("d_star") is not None
    }
```

更佳：在 `DStarCache` 加 `export_d_star_values() -> Dict[str, float]` 公開 API，避免測試觸 private `_entries`。

### 與 frame 修復的關係

- Frame map 修復 **不解** tier2a empty d_star（synthetic 本來就能選中 L1/L2 欄）。
- 兩者皆在「#2 d* fracdiff」里程碑內交付合理，但 SPEC 應分開驗收條目，避免「修 map 即 tier2a 綠」的假設。

---

## 6. 風險與踩坑

1. **Chunked L6.5**（大欄數）：map 須跨 chunk 一致；shared d* cache 已在 chunked path 啟用（`2629-2633`）。
2. **IC-First post_ic**：`post_ic_features` 為子集，map 應為全量 map 的子查詢，勿重建。
3. **Duplicate columns**：map 必須與 `_combine_layers` dedup 一致，否則 map 指向已 drop 欄。
4. **Parity 測試 hook**：CGSA 不回傳 L6.5 DataFrame，需 SPEC 定義比對點（L7_raw HDF5 或 test helper）。
5. **optimized path**：`fracdiff enabled` 時不走 optimized（`2229-2230`），無額外分支。

---

## 7. 建議 SPEC 驗收清單（摘要）

- [ ] `FFACT_USE_CGSA=0` + fracdiff on：log 無 `unparsed_columns=N/N`（或僅 L3+ 預期 unparsed）
- [ ] 同 run 產生 d_star cache 檔（symbol/tf 已知）
- [ ] CGSA vs 非 CGSA：L7_raw 上 L1/L2 交集欄 `allclose`
- [ ] `test_l65_golden_tier2a_synthetic_baseline_exists` 綠（d_star 非空）
- [ ] 既有 `test_fracdiff_registry_layer_filter_*` 不弱化

---

## 8. 信心度

| 項目 | 信心 | 說明 |
|------|------|------|
| (a) 無 column→layer | **高** | 程式路徑直接可讀，無推測 |
| (b) map + filter 擴充為最小正確設計 | **高** | 複用既有 `source_layer` 語意與測試 |
| (c) golden parity 策略 | **中-高** | 策略明確；CGSA 空 frame 回傳使比對點需額外設計 |
| (d) tier2a 不同根因 | **高** | synthetic 有 `L1_` 前綴 + builder 讀空 dict 可重現 |
| 整體選 A 可行性 | **高** | scope 可控，命中 (a)(b) 原則 |

---

ASSUMPTIONS_VERIFIED: 非 CGSA transform 不傳 source_layer；combine 前 layers 順序固定；synthetic fixture 欄名含 L1_/L2_ 前綴；DStarCache 非 shared 時不更新 self._d_star_cache
TESTS_RUN: 程式碼靜態閱讀（未執行 pytest）
FAILURES_SEEN: none
SCOPE_CHANGES: none（設計建議 only）
NUMERIC_OR_SCHEMA_IMPACT: 選 A 實作後非 CGSA 將新增 fracdiff 數值；欄名 schema 不變

STATUS: DONE
