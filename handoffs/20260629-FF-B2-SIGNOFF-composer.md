# FF 因果性三方簽核 + B2 測試設計 — Composer 腿

> 委員獨立腿。依據 `handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-CLAUDE.md` 證據摘要 + 讀碼複核。**未重跑全鏈 generate_features**。

---

## A. FF 因果性：可用於量化？

### 結論

**SIGN-OFF: FF-CAUSAL PASS**

FF 特徵計算主路徑（L1→L7 raw，含 L6.5 前處理）在單 TF、MR 測試 config 下**無真 look-ahead**；截斷未來 bar 後暖機區前綴值穩定（≤ float16 儲存容差）與讀碼一致。可用於量化研究；上線前須處理兩個已知 caveat（非新危機）。

### 證據採信（Claude 腿，未重跑）

| 證據 | 採信理由 |
|------|----------|
| 截斷 K=10、窗 2081、暖機後前綴值在 rtol 1e-3 內一致 | `LINEARREG-ANGLE_144` rel_err=9.999e-4 與 `feature_storage.FLOAT16_MAX_REL_ERROR=1e-3` 機制吻合 |
| 差異來自 float16 roundtrip + 列數依賴 NaN/dead | 讀碼確認 `_select_parquet_storage_array` 邊界翻面邏輯；L7 dead_drop 在 MR config 已關閉 |
| mutation 探針（center/shift(-1)/全量 winsor）必紅 | 測試檔 `test_mutation_*` 結構符合章程 §B1.1；注入點對準 L3/L4/L6.5 |

### 讀碼複核（獨立查證）

**L3 `numba_rolling.py`** — 無 look-ahead  
- `fused_rolling_stats` / `rolling_rank` / `rolling_slope` 皆為 `for row_idx in range(n_rows)` 單向掃描；環形緩衝在 `row_idx >= window` 時移除 `row_idx - window` 的舊值。  
- 無 `center=True`；與 mutation `fused_rolling_stats_multi_window` + `center=True` 探針對稱。

**L4 `lag_processor.py`** — 無 look-ahead  
- `_normalize_lags` 僅保留 `lag >= 1`；`_apply_lag` = `data.shift(lag)`（正 lag = 往過去移）。  
- 全庫 `shift(-n)` 在特徵路徑僅見 `feature_factory._build_default_ic_label`（IC 標籤，非 persist 特徵）與 `labels/label_generator.py`（標籤域）。

**L2 `derived_operators.py`** — 無 look-ahead  
- `ts_argmax/ts_argmin/ts_corr/ts_rank/decay_linear` 皆 `series.rolling(window)`（pandas 預設 `center=False`）。  
- Momentum 用 `shift(lag)` 正 lag；Polars 路徑 `polars_l2_derived_momentum` 同理。

**L6.5 `preprocessing/`** — 因果強制  
- `causal_preprocessing=False` 被忽略並強制 `True`（`feature_preprocessor.py:149-157`）。  
- Winsor quantile：`rolling_quantile_2d` docstring「row-wise causal」；sliding kernel 用 `values[start:r+1]`。  
- Gaussian：`_gaussian_2d(causal=True)` → `_rolling_rank_numba`，非全樣本 `rank(pct=True)`。  
- Fracdiff d-star：`_calibration_series` = `series.iloc[:bars]`（僅前綴校準）；mutation 全量 fit 探針已覆蓋。

**儲存層 `feature_storage.py:2554-2588`** — 邊界 float16 行為與 HANDOFF/Claude 一致；屬儲存優化非計算洩漏。

**未在本 MR 覆蓋但 HANDOFF 已標強項**：Multi-TF 對齊（V-6）、L6.5 causal winsor 單測（V-5）。B2 主 MR 為單 TF；不因此 HOLD 因果結論，但 cross_sectional / multi-TF 全鏈因果應留在 B3 分級。

### 兩個 Caveat — 同意

1. **float16 可重現性（輕）**：borderline 欄跨窗 ≤0.1% 值差、dtype 翻面。ML 噪音級；研究可用，bit-repro 不可宣稱。  
2. **特徵集列數依賴（中，已有 epic）**：NaN blacklist / L7 dead_drop 使 near-empty 欄跨窗出現不對稱。屬 **stateful-param-audit** 範疇，非 look-ahead。MR 關閉 `l7_dead_feature_drop` 正確。

### 反駁檢查（為何非 HOLD）

- 未發現任何層在計算 row `t` 時讀取 `t+1..` 的 OHLCV 或特徵值。  
- 理論上「僅 NaN mask 洩漏、值不變」極難在暖機後大量欄位同時成立；`test_c2_2` 尾端 OHLCV ±1e6 擾動前綴不變提供額外保證。  
- 若存在未抽查路徑（如 cross_sectional enabled、某 atomic wrapper 餵錯欄），屬 **覆蓋率缺口** 而非已證實 look-ahead；B1 已修 BETA/CORREL/Klinger 類問題。

---

## B. B2 測試設計：怎麼收？

### 結論

**B2-DESIGN: 同意（附 3 項具體修正）**

同意 Claude 主軸：**測因果（過去不依賴未來）而非測儲存/bit 級確定性**；主 MR 排除 fracdiff + fracdiff 專屬 MR 兩層；mutation 探針保留必紅。

### 對挑戰題的回答

**Q1: common-valid-region + rtol 2e-3 會不會放走真 look-ahead？**  
- **不會（實務上）**。真 look-ahead 在 row `t` 改變計算輸入集 → 暖機後前綴值差通常遠超 2e-3（mutation 實證數量級）。  
- 2e-3 選擇合理：對齊 `FLOAT16_MAX_REL_ERROR=1e-3` 並留 2× 邊界餘量（實測 9.999e-4 卡 1e-3）。  
- **mask-only 洩漏**：理論可能（同一有限值、僅 NaN 邊界翻轉），但 (a) 截斷 MR 測的是「未來不存在時過去怎麼算」；(b) `test_c2_2` 擾動未來 OHLCV 驗前綴不變。純 mask 洩漏需與列數依賴 NaN 處理區分——後者記錄、前者用下方修正 #2 兜底。

**Q2: columns drop 上限該設多少？**  
- 建議 **FAIL 門檻**：`max(100, 0.1% × |union_columns|)` 不對稱掉欄（only_in_full 或 only_in_trunc）。  
  - 以 ~15 萬欄估算 ≈ 150 欄；near-empty 衍生欄在 10 bar 差異下預期遠低於此。  
  - 同時 **必須** 在 assertion 訊息列出 sample 欄名（現有 `_diagnose_column_mismatch` 已有雛形）。  
- 現行測試 `_assert_columns_gate` 仍要求 **完全相等**——與根因分析矛盾；實作應改為 **交集比對 + 不對稱掉欄 informational/門檻 fail**。

**Q3: NaN mask 退讓到哪仍可證偽？**  
- **值比對**：僅在 **交集欄 × both-non-NaN** 上做 `allclose(rtol=2e-3)`（Claude common-valid-region）。  
- **NaN mask**：  
  - 對 **高填充率欄**（在 `[warmup:n_trunc)` 段 fill_rate ≥ 95% 於 full 與 trunc 各自計算）→ **仍要求 mask exact**；違反則 fail（防 mask-only 洩漏）。  
  - 對 **低填充率 / 僅一側存在的 near-empty 欄** → 記錄不 fail（列數依賴良性）。  
- 暖機區 `[0:warmup)`：維持現行容差值比對即可；不要求全段 mask exact（暖機本來就大量 NaN）。

### 三項修正（相對 Claude 草案）

| # | 修正 | 理由 |
|---|------|------|
| 1 | columns gate 改 **交集** + 不對稱掉欄門檻 `max(100, 0.1%×union)` | 現 strict equality 與列數依賴根因衝突；門檻防「大量掉欄掩蓋」 |
| 2 | NaN mask **分層**：高 fill_rate(≥95%) 欄 mask exact；低 fill_rate 僅記錄 | 在放寬良性 NaN 差異時保留對穩定欄的證偽力 |
| 3 | 保留 **test_c2_2 尾端擾動** 與 **四支 mutation + 兩支 fracdiff negative control** 為 P0 硬門檻 | 單靠截斷 MR 無法覆蓋「未來 OHLCV 污染過去」的某些邊界；章程 §B1 要求 |

### 已實作 vs 待改（讀碼）

- ✅ 主 MR float16 容差 `FLOAT16_RTOL=2e-3`、L7 dead_drop 關閉、fracdiff 分層、mutation 探針結構  
- ⚠️ `_assert_arrays_values_close` 仍先要求 **全段 NaN mask exact**（L288）——與 B2 收斂設計未完全一致，應按上表 #2 改  
- ⚠️ `_assert_columns_gate` 仍 **strict equality**——應按 #1 改

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - numba_rolling 單向 Welford/ring buffer，無 center=True（讀碼）
  - L4 僅 lag>=1 的 shift(lag)（讀碼）
  - L6.5 causal_preprocessing 強制 True；winsor/gaussian 走 rolling causal 路徑（讀碼）
  - float16 roundtrip gate 1e-3 與 LINEARREG-ANGLE 實測邊界 case 一致（讀碼+Claude 證據）
  - shift(-1) 僅標籤/IC helper，不在 persist 特徵管線（grep）

TESTS_RUN: none（依 prompt 勿重跑全鏈）

FAILURES_SEEN: none

SCOPE_CHANGES: none（簽核腿，唯讀）

NUMERIC_OR_SCHEMA_IMPACT: 簽核同意 B2 改為容差值比對+交集欄；不主張改變生產輸出語意
```

**SIGN-OFF: FF-CAUSAL PASS**  
**B2-DESIGN: 同意（交集欄 + both-non-NaN 值 rtol 2e-3 + 掉欄門檻 max(100,0.1%union) + 高 fill_rate NaN mask exact + mutation/fracdiff MR 保留）**

STATUS: DONE
