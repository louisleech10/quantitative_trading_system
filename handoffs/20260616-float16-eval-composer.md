# CGSA L7_raw float16 vs float32 — 技術評估（Composer，讀取型）

> 日期：2026-06-16 | 任務：讀取型評估（禁改 production）  
> 觸發：Batch2D T4 調查 — CGSA `L7_raw` parquet 存 **float16**，非 CGSA frame/HDF5 存 **float32**；L1/L2 交集欄 max abs diff ~**0.0009**，NaN mask 100% 一致（`docs/BATCH2D_DSTAR_ALIGN_MANIFEST.md`、d2 調查 handoff）。

---

## 1) `feature_storage.py`：哪裡、為何選 float16

### 1.1 位置（兩條 CGSA 寫盤路徑共用同一套 gate）

| 函式 | 行號（約） | 用途 |
|------|-----------|------|
| `_select_parquet_storage_array` | 2548–2582 | **per-column** 決定 float16 或 float32 |
| `_select_parquet_storage_columns` | 2585–2612 | 組 parquet part；記 `float32_cols` fallback 清單 |
| `persist_registry_to_parquet` | 2238+ | 舊 V7 registry 整組 persist |
| `write_raw_from_registry_stream` | 733+ | **主路徑** CGSA L6.5 → L7_raw streaming |

持久化前一律 `_coerce_persistence_array` → **float32**（:47–49, :2380–2382, :875）；float16 只在 **寫 parquet 前最後一步** cast。

### 1.2 門檻邏輯（roundtrip-safe gate）

常數（:2172–2173）：

```python
FLOAT16_MAX_REL_ERROR = 1e-3   # 0.1%
FLOAT16_MAX_ABS_ERROR = 1e-12
```

`_select_parquet_storage_array` 流程（:2548–2582）：

1. 空 array → float16  
2. `source` = float32（persistence 邊界）  
3. `data_float16 = source.astype(np.float16)`  
4. 若 finite 值 roundtrip 後出 inf/NaN（overflow/underflow）→ **整欄 float32**  
5. 否則算 `abs_error = |roundtrip_f32 - source_f32|` on finite  
6. `tolerance = max(1e-12, |source| * 1e-3)` per element  
7. 任一 finite 超 tolerance → **整欄 float32**；否則 **float16**

設計意圖（docstring :2247–2249, :2551–2553）：BTC 價格尺度 overflow、極小 quote underflow、一般 ratio 特徵省 **~50% 未壓縮 cell**；不安全欄 per-column fallback float32。manifest `dtype_summary` 記錄 fallback parts（:2623–2646），供跨 symbol 稽核。

### 1.3 實測 ~0.0009 與 gate 的關係

- Batch2D live 抽樣：`frame=-0.7070665` vs `cgsa=-0.70703125`（差 ~3.5e-5，unit-scale ratio）  
- max abs **~0.0009** 對 |x|~1 特徵 ≈ **0.09% rel**，**低於但接近** 1e-3 gate 上限 → **被判定 roundtrip-safe 而存 float16 屬預期行為**，非 gate 失效。  
- NaN mask 全符 → 量化只動 finite 值，無 silent NaN 污染。

單元測試覆蓋：`tests/momentum/test_feature_storage.py` — overflow/underflow→float32、safe→float16、mixed part per-column fallback。

---

## 2) float16 省碟 / 記憶體 vs 精度損失

### 2.1 效益（程式假設）

| 維度 | float16 | float32 | 備註 |
|------|---------|---------|------|
| 未壓縮 cell | 2 B | 4 B | disk precheck 以 float16 估 `estimated_final_bytes`（:2658–2670） |
| zstd parquet | 仍壓縮 | 仍壓縮 | 實際省碟 **≤50%**，高熵 float32 可能差距縮小 |
| 8GB tier 峰值 | 註解指 batch 中 Arrow table 以 float16 估 RAM（:2345–2346） | 2× | 與 L7 persist OOM 歷史相關 |
| 產品 gate | L7_raw ≤ **1.5 GB**（`L65_OPTIMIZATION_SPEC_V2` C-OPT-5） | 約 2× 風險 | full schema ~165k+ cols × 367 rows 量級 |

### 2.2 精度損失（unit-scale ratio 特徵）

- float16 在 |x|≈1：**有效精度 ~3–4 十進位**，機器 epsilon ~**9.8e-4**（2⁻¹⁰）  
- 本 repo **明確允許** roundtrip rel error **≤0.1%** 才存 float16  
- 對 **尺度 ~1 的 ratio / fracdiff / zscore 前 winsor 值**：0.1% 是 **可感知** 的（非 bit-identical），但通常 **不改變數量級**  
- 價格尺度、極小值已有 float32 fallback；L1/L2 ratio 類大多落在 gate 內 → **大量 float16**

### 2.3 取捨摘要

- **省**：多 symbol × 全 schema 下 L7_raw 體積與 8GB tier disk/RAM headroom（專案 Optimization Priority 4–5 在 1–3 保護後才考慮，但 L7 1.5GB gate 已 codified）  
- **失**：與 frame float32 **永遠無法 byte/value exact parity**；任何 Pearson/閾值/zscore 二次計算吃 stored raw 時帶 ~1e-3 級誤差

---

## 3) 下游：吃 raw 還是 processed？~1e-3 對 IC / ML / 回測

### 3.1 資料流（CGSA 主路徑）

```
L1–L6 → L6.5(mode) → L7_raw (parquet, 常為 float16)
         ↓
    [IC-First downstream]
         IC Gate ← read raw (pd.read_parquet, float16)
         → ic_selected_features.json
         → load selected from raw → post_ic (rank/zscore/gaussian)
         → L7_processed (可 integer codec)
         → 可 cleanup raw/
```

- **Generation 只產 L7_raw**；processed 為 downstream optional（`L65_OPTIMIZATION_SPEC_V2` § 開頭）。  
- L6.5 三模式（`feature_factory.py:2419–2444`）：`none` / `ic_first_pre`（Winsor+FracDiff/ADF only）/ `legacy`（含 rank/zscore/gaussian 全寫入 raw）。

### 3.2 各下游實際讀取

| 消費者 | artifact | 讀取方式 | float16 影響 |
|--------|----------|----------|--------------|
| **IC Gatekeeper** | **raw** | `ic_engine.compute_ic_from_l7_raw` → `pd.read_parquet`（:203）；預設 **Spearman**（:128, :985） | **低**：Spearman 用 rank；~1e-3 level noise 極少改 rank，除非大量 tie 邊界 |
| **IC-first post_ic** | raw → processed | `load_columns_v2(..., artifact_kind="raw")`（factory :2088–2094） | post_ic 在 float16 上再做 rank/zscore；rank 會「再離散化」，通常 **進一步掩蓋** level error |
| **FeatureLibrary / ML 訓練** | **raw**（優先） | `feature_library.py:114–119` `artifact_kind="raw"`；fallback HDF5 float32 | **中**：`ModelTaskService` 直接 `feature_library.load` → XGB/LGBM 吃 pandas dtype（可能 float16）；**LSTM** 自行 `astype(float32)` |
| **Coverage / browse** | raw | `coverage_analyzer` raw；browse UI **轉 float64** 算 mean/std（`feature_factory_service.py:2017–2023`） | browse 已規避；coverage 視統計而定 |
| **回測** | 不直接讀 L7_raw | `momentum/Strategy/` 無 FeatureReader | **無直接影響**（信號/倉位層） |
| **d* parity** | JSON cache | 非 parquet dtype | **無**（T3 3736/3736 exact 已驗） |

### 3.3 ~1e-3 是否「實質」影響

| 場景 | 判斷 | 理由 |
|------|------|------|
| Spearman IC 篩特徵 | **通常否** | 預設方法；0.1% level jitter 罕見改 rank 序 |
| Pearson IC（若啟用） | **可能** | 直接相關係數對 level error 敏感 |
| IC 閾值 ~0.02 邊界特徵 | **邊界可能** | 若 IC 本身 ~0.02±0.001，量化可能 flip pass/fail（需 empirical，本次未跑全量 IC A/B） |
| 樹模型 (XGB/LGBM) on raw | **通常否** | 分裂看排序/閾值；float16 對 ~1 特徵仍保留足夠序信息 |
| 線性/NN on raw | **是** | FeatureLibrary 餵 raw float16 時梯度/係數會吃量化 noise |
| 跨路徑 audit（CGSA vs frame） | **是（結構性）** | 非 row 錯位；mask 一致 value 不一致 — 阻礙 exact golden |
| 回測 PnL 真實性 | **間接、通常弱** | 多層 downstream；主風險在 **特徵選擇/模型** 而非 backtest 引擎直接讀 raw |

---

## 4) 量化最佳實務：float16 特徵儲存可接受性

### 4.1 業界對照

- **Archive / feature store 冷存**：float16 或 int8/int16 quantization 常見，前提是有 **明確 decode 語義** 且下游以 **rank/分箱/樹** 為主。  
- **Research reproducibility / cross-run parity**：研究與回測 sign-off 通常要求 **float32 或 float64** 可重現 artifact；float16 需 document tolerance。  
- **Ratio/return 特徵（|x|~O(1)）**：float16 的 **0.1% rtol 是設計上限而非「無損」**；對 fracdiff、correlation-like、threshold 策略 **不算 best practice 的 lossless storage**。

### 4.2 本 repo 既有原則張力

- **C-OPT-5**：「最小可行輸出 — **不得 lossy numerical behavior**」 vs 現行 **明確 lossy float16 gate（1e-3）** → 解讀：允許 **有界、可稽核** 的 storage loss，但需在 manifest 披露（已做 `dtype_summary`）。  
- **Optimization Priority 1–3**（cross-tier、multi-symbol、data quality）優先於 4–5：float16 **不影響** NaN/inf gate、跨 symbol cache 隔離；**影響** cross-path numeric parity 與 strict ML reproducibility。

### 4.3 尺度 ~1 ratio 特徵

- 觀測 max abs ~0.0009 即 **gate 允許範圍內的典型 float16 量化**，非 anomaly。  
- 若產品要求「CGSA raw 與 frame HDF5 數值可比」→ float16 **不可接受**（除非 frame 也降精度）。  
- 若產品要求「IC Spearman + 樹模型 + 1.5GB L7 gate」→ float16 **在工程上可接受**，但應 **文件化 rtol=1e-3** 且禁止宣稱 byte parity。

---

## 5) 建議

### 建議：**條件式維持 float16 儲存 + 收緊消費端（短期）；中長期再決是否全面 float32**

#### 5.1 短期（推薦，改動小、風險低）

1. **維持** `_select_parquet_storage_array` float16 + 1e-3 gate（**勿 silent 放寬**；BTC/underflow 已有 float32 fallback）。  
2. **消費端 promotion（建議另 ticket）**：`FeatureReader.load_columns_v2` / `stream_groups_v2` 在 `consumer="strict"`（training / IC recompute）將 float16 **升 float32**，儲存仍 half、**讀取 lossless for compute** — 兼顧 C-OPT-5 與 1.5GB gate。  
3. **文件 / manifest**：在 run metadata 標 `storage_rtol=1e-3`；T4 類 cross-path 測試 **禁止** 用 value exact 比 CGSA vs frame（已 Batch2D 裁定）。  
4. **ML 路徑**：確認 `FeatureLibrary.load(..., for_training=True)` 走 strict promotion；或訓練前 `X.astype(np.float32)`（與 LSTM 一致）。

#### 5.2 不建議立即「全面改 float32 儲存」

- L7_raw **~2×** 可能觸碰 **1.5GB / 8GB OOM** gate（SPEC：解壓 ~14GB 若全載；persist 峰值亦敏感）。  
- 不解決 frame vs CGSA **L6.5 拓撲差**（T4 0/37524 value hash 主因之一）；改 float32 只消除 **量化差**，非全部 T4 gap。  
- 需全量 re-persist / manifest migration，多 symbol 成本高。

#### 5.3 若未來必須 float32 儲存（觸發條件）

- 產品 sign-off 要求 **Pearson IC / 線性模型 / cross-artifact exact parity** 為硬 gate；或  
- 實測 IC boundary flip / ML metric regression 由 float16 造成（需 A/B，目前 **無全量 IC A/B 證據**）。  
- 配套：調高 L7 size budget、24GB+ tier 驗證、phase2_skip_evidence 更新。

#### 5.4 不建議

- **收緊 gate 到 1e-4** 而不改 storage dtype：會使大量 L1/L2 ratio 欄 fallback float32，**省碟效益驟降**且 manifest mixed dtype 激增，性價比差。  
- **僅改測試 tolerance 假綠**：違反 C-OPT-3 / Batch2D exact-only 精神。

### 5.5 風險矩陣

| 方案 | 主要收益 | 主要風險 |
|------|----------|----------|
| 維持 float16（現狀） | 1.5GB gate、8GB disk/RAM | ML/audit parity、Pearson IC 邊界 |
| 全面 float32 儲存 | 跨路徑 numeric 可比、strict reproducibility | 2× L7 體積、OOM/disk、re-run 成本 |
| **float16 存 + strict 讀 float32（推薦）** | 省碟 + 計算端無 quantization | 實作面小改 FeatureReader；parquet 仍 lossy（audit 讀 disk 仍见 half） |

---

## 6) 驗證依據（本次已讀碼，未改檔）

- `momentum/FeatureEngineering/feature_storage.py` — gate 常數、`_select_parquet_storage_*`、`write_raw_from_registry_stream`  
- `momentum/FeatureEngineering/feature_reader.py` — 讀取 **不** 自動升 precision  
- `momentum/Analysis/ic_engine.py` — IC 讀 raw parquet；Spearman 預設  
- `momentum/FeatureEngineering/feature_factory.py` — IC-first / L6.5 模式、processed 下游  
- `momentum/FeatureEngineering/feature_library.py` — ML 優先 `artifact_kind="raw"`  
- `tests/momentum/test_feature_storage.py` — float16/float32 fallback 行為  
- `handoffs/20260616-d2-parity-investigation-composer.md`、`docs/BATCH2D_DSTAR_ALIGN_MANIFEST.md` — max abs ~0.0009、mask 一致

---

ASSUMPTIONS_VERIFIED: float16 gate at feature_storage.py:2172-2173 and :2548-2582; IC reads raw via read_parquet; FeatureLibrary training path uses artifact_kind=raw; max abs ~0.0009 within 1e-3 gate (Batch2D manifest + d2 handoff)
TESTS_RUN: none（讀取型）；依既有 Batch2D T3/T4 實測引用
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅新增本 handoff）
NUMERIC_OR_SCHEMA_IMPACT: none（評估-only）；若採「strict 讀升 float32」為後續 ticket，不改 parquet schema

STATUS: DONE — **建議：條件式維持 L7_raw float16 儲存（現行 1e-3 roundtrip gate 合理且 ~0.0009 屬預期）；另開小 ticket 在 FeatureReader strict/training 路徑升 float32，不立即全面改 float32 寫盤（L7 體積/8GB 風險）。**
