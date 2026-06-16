# Batch2D d* / T4 資料正確性獨立調查 — Composer

> 日期：2026-06-16 | 任務：讀取型調查（禁改 production、禁 commit）
> 資料：`BTCUSDT/12h` `2024-06-01~2024-12-01`，真實 kline `data_cache/feature_klines/kline_cache.h5`
> 程式狀態：工作區含 #2 fix 未提交 diff（`column_layer_map` + `_filter_fracdiff_target_columns` map 分支）

---

## 1) T3 d* parity（主 oracle）— 實測數字

**設定**：兩路皆 `preprocessing.fractional_differencing.enabled=True`（預設為 `False`，T3 必須顯式開啟）；各自 `monkeypatch` 隔離 `FeaturePreprocessor._d_star_cache_dir` → tmp；子程序外層同 `freeze_batch2d_baseline.py` env（`FFACT_USE_POLARS=0`, `CHUNK_SIZE=500`）。

| 指標 | 數值 |
|------|------|
| provenance L1/L2 欄位數（兩路一致） | 46,438 |
| frame path 寫出 d* 條目數 | 3,736 |
| CGSA path 寫出 d* 條目數 | 3,737 |
| L1/L2 provenance 交集且兩路皆有 d* | 3,736 |
| **d* exact match（交集）** | **3,736 / 3,736（100%）** |
| d* mismatch | 0 |
| 僅 CGSA 有 d*（L1/L2 邊界） | 1 |
| 僅 frame 有 d* | 0 |
| 兩路 d* cache 檔 fingerprint | 同 `d_star_BTCUSDT_12h_e7b598019841.json`（同 config/schema hash） |

**解讀**：
- #2 fix 後，非 CGSA frame path 在 fracdiff 開啟時會對 L1/L2 裸欄名正確選欄並計算 d*（修前根因見 `docs/DSTAR_FRACDIFF_NONCGSA_FINDING.md`：regex `L\d+_` 對裸名全 unparsed → 無 d*）。
- 46,438 是 provenance 全 L1/L2 欄；僅 3,736 有 d* 屬正常（`apply_to=non_stationary` + ADF safe-skip，非全欄皆進 fracdiff search）。
- CGSA 多 1 條 d* 未造成交集 mismatch（exact 仍 100% on overlap）。

**對照：fracdiff 預設關閉時**（P0 golden 同設定）：frame path **0** 個 d* cache 檔（`fracdiff.enabled=False` 確認於 golden metadata + 實測 listing 空目錄）。T3 不適用預設 config，須顯式 `enabled=True`。

---

## 2) T4 value parity 根因（次 oracle，frozen golden + 抽樣 live）

### 2.1 Frozen golden 靜態（`tests/_golden/batch2d/`）

P0 凍結：**control** = 非 CGSA + `fracdiff.enabled=False`；**cgsa_baseline** = CGSA + 預設 `fracdiff.enabled=False`。

| 檢查項 | 結果 |
|--------|------|
| provenance L1/L2（frame / cgsa map） | 各 46,438，交集 46,438，layer 一致 |
| control 輸出欄數 / 列數 | 165,268 cols × 367 rows |
| cgsa 輸出欄數 / 列數 | 165,309 cols × 367 rows |
| L1/L2 欄在兩邊 manifest 皆存在 | **37,524**（非 46,438） |
| L1/L2 在 provenance 但缺於 control | 8,914（L2: 8,690, L1: 224） |
| L1/L2 在 provenance 但缺於 cgsa | 8,881（與上 8,881 重疊 → dead-drop） |
| row-index hash | **不符**（長度同 367） |
| row-index dtype | control: `int64` name=`timestamp`；cgsa: `datetime64[ns]` name=`None` |
| L1/L2 交集 value hash | **0 / 37,524** |
| L1/L2 交集 nan_mask hash | **37,524 / 37,524** |

### 2.2 根因歸因（非單一 bug，多為既有結構差）

**A. row-index 不符 — 非 warmup/對齊錯位**
- 兩邊列數相同（367），但 index **型別不同**：frame/HDF5 用 epoch `int64`；CGSA raw_v2 用 `DatetimeIndex`（SPEC §A 已記載儲存路徑不對稱）。
- canonical hash 對 index bytes 敏感 → T4 row-index 必 fail；**不等於時間軸錯位**（需另比 epoch 值未在本次 hash 內展開，但列數一致）。

**B. value 全不符 + nan_mask 全符 — 非 row 錯位主因**
- 若列錯位，nan pattern 通常也會分歧；實測 **mask 100% 一致、value 0% 一致** → 同列對齊下 **L6.5 數值路徑不同**（winsor / rank / zscore / 浮點累積），不是整表 shift。
- P0 golden 兩路 **fracdiff 皆關** → 37,524 列 value 差異**不能**歸因於 #2 fracdiff 修復（修復只影響 fracdiff 開啟時）。

**C. 欄集差（46,438 expected vs 37,524 共有）— dead-drop，非 map 錯**
- 8,914 個 provenance L1/L2 欄未進 control 輸出（主要 L2）；8,881 兩邊皆缺 → **L7 dead-feature drop**（`min_valid_samples` 等）在兩路各裁不同子集。
- cgsa 比 control 多 41 欄（非 L1/L2 為主）；L1/L2 在 cgsa manifest 多 33 欄相對 control 的 L1/L2 子集。

**D. live 抽樣（兩路 fracdiff ON，欄 `close_12h_trend_EMA_20`）**
- 367 rows 對齊；nan pattern 一致（各 116 NaN）。
- **249/367** 位置 float32 不完全相等；首差例 idx 117：`frame=-0.7070665` vs `cgsa=-0.70703125`（同量級微小差 → rank/zscore/fracdiff 路徑浮點差，非數量級錯誤）。

### 2.3 與 #2 fix 的關係

| 現象 | 是否 #2 regression |
|------|-------------------|
| T3 d*（fracdiff ON） | **否** — fix 使 frame path 達 parity |
| T4 value（golden，fracdiff OFF） | **否** — 兩路本來就走不同 L6.5 執行模型（registry group+`source_layer` vs combined frame+chunked+`column_layer_map`）；SPEC §N 標 L3-L6 跨路徑 value 全對齊 out-of-scope |
| T4 row-index dtype | **否** — 既有 HDF5 vs raw_v2 差異 |
| 欄集 37,524 vs 46,438 | **否** — L7 dead-drop 既有行為 |

---

## 3) 結論

1. **#2 對齊在 d* 層已達成（T3 主 oracle）**：在 fracdiff 顯式開啟、隔離 cache、真實 BTCUSDT/12h 下，L1/L2 交集 d* **3736/3736 exact match，0 mismatch**。這是 batch2d 的通過條件 (1) 核心。
2. **T4 value 差異屬 out-of-scope 既有 CGSA vs frame 結構差異，非 #2 fix bug**：
   - 儲存 index 型別不同；
   - L6.5 執行拓撲不同（per-group vs chunked combined）導致同 NaN 遮罩下 float32 值不同；
   - L7 dead-drop 使 8,881 個 L1/L2 provenance 欄兩邊皆未輸出。
3. **建議**：T4 維持 SPEC `exact-only` → **BLOCKED 分案**（不應放寬 rtol）；P4 驗收應以 **T3 pass + control L3-L6 unchanged + CGSA baseline regression** 為 merge gate，T4 記 inventory 即可。
4. **踩坑**：`fractional_differencing.enabled` 預設 `False`；未開啟時 frame path 無 d* 檔，不得用 P0 golden（control 刻意關 fracdiff）評 T3。

---

## 驗證命令（本次已跑）

```bash
# T3 live（腳本在 /tmp，未入庫）
python3 /tmp/batch2d_t3_parity_probe.py  # → 見 /tmp/batch2d_t3_summary.json

# T4 golden 靜態
python3 -c '...'  # provenance + control.json + cgsa_baseline.json 比對（見 §2.1）

# 預設 fracdiff 關閉 → 無 d* 檔
# golden metadata: control/cgsa fractional_differencing.enabled = False
```

---

ASSUMPTIONS_VERIFIED: fracdiff 預設 False（config dump）；T3 需 enabled=True；d* key 為裸欄名；golden row 數兩邊皆 367
TESTS_RUN: T3 live dual-path d* compare (3736/3736); golden static T4 hash inventory; live single-column fracdiff-ON sample
FAILURES_SEEN: none（調查任務）；T4/T3-oracle 對預期為 fail/pass 分離
SCOPE_CHANGES: none（唯讀；/tmp 探針未 commit）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 production）

STATUS: DONE — T3 d*: **3736/3736 exact (0 mismatch)** on L1/L2 intersection with fracdiff enabled; **#2 d* alignment achieved**; T4 value gaps are **pre-existing CGSA vs frame structural differences (index dtype, L6.5 topology, dead-drop), not #2 fix bug** — T4 remains BLOCKED per exact-only SPEC.
