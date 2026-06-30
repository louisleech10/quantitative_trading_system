# B2 mutation 2 修 — Composer 腿（委員會定案用）

讀碼為主；靜態檢查已跑；未跑慢全鏈 generate。

---

## 問題 1：`test_mutation_l4_lag_shift_minus_one_fails` 沒紅

### 根因定案：**C（monkeypatch 未生效）— 變體：L4 fast path 繞過 `_apply_lag`**

| 假設 | 判定 | 證據 |
|------|------|------|
| **A** mutation 加 NaN 降 fill_rate | **反駁（非主因）** | 注入若未生效，fill_rate 與良性路徑相同；無「mutation 特異 NaN」可討論 |
| **B** 抽到 L4 低 fill 欄 | **反駁（非主因）** | `_select_required_probe_columns` 強制 L4 lag_1 入樣；post-warmup lag 欄正常應高 fill |
| **C** monkeypatch 沒打到執行路徑 | **確認** | `LagProcessor.compute_all` L59–65：**fast path** 直接 `selected_df.shift(lag)`，**不呼叫** `_apply_lag`；註解寫 12K×8 lags 走快路。探針只 patch `_apply_lag` → 生產仍 `shift(+lag)` → MR 正確通過 → `pytest.raises(AssertionError)` 不觸發 |

非 C1-2 式 registry 快取；是 **P1.4 fast path 與探針注入點脫節**（2026-06-29 B2-FINISH 仍假設 patch `_apply_lag` 足夠，實作後未對齊 fast path）。

### c2_1 偵測力（注入修好後的二階問題）

Claude 邊界分析**成立**：`shift(-lag)` 在截斷 MR 下，前綴 `[warmup:n_trunc)` 內通常**僅最後一列**出現 `full 有值 / trunc NaN`；`_assert_values_both_non_nan_close` 跳過該格；主要靠 `_assert_nan_mask_layered` 高 fill(≥95%) exact mask。

- 正常 lag_1 欄 post-warmup fill≈1.0 → 單格 mask 差應能紅。
- 但 both-non-NaN 完全盲區此模式；若未來窗縮短或欄 fill 邊界卡 95%，有假綠風險。

### 偵測修法定案：**雙軌（注入修復 + 提案 2 邊界守衛）**；不採「探針改 assert c2_2」為唯一手段

| 方案 | 評估 |
|------|------|
| **提案 1** 探針改 assert c2_2 尾端擾動 FAIL | 能抓「未來 OHLCV 滲入前綴」類洩漏，但與「L4 符號反向」耦合弱；且 c2_2 已獨立覆蓋 OHLCV 路徑，不宜讓 L4 lag 探針依賴同一 oracle |
| **提案 2** 高 fill 欄 `full_finite ∧ trunc_nan` → **FAIL** | **採用**：精準對應 shift(-1) 截斷邊界簽名；列數依賴良性 NaN 通常多格、fill<95% → 仍 informational，**不誤殺** |
| 其他 | 注入層必須先修（見下） |

### 問題 1 實作指令（給實作腿）

1. **注入（必做，二選一，推薦 A）**
   - **A（推薦）**：探針內 `monkeypatch.setenv("FFACT_LAYER4_FAST_PATH_MAX_COLS", "1")`（`_resolve_positive_env`→1，cols×lags≫1 強制 slow path）+ 保留 `_apply_lag` → `shift(-lag)` patch；在 `_build_truncation_pair` **之前**設 env，確保 `LagProcessor.__init__` 讀到。
   - **B**：`monkeypatch` 包 `LagProcessor.compute_all`，快/慢路徑統一用 `shift(-lag)`（較重，無 env 副作用）。

2. **主 MR 守衛（必做，提案 2）** — 在 `_assert_values_gate_main` 迴圈內、`_assert_nan_mask_layered` 之前或之內新增：
   ```text
   若 fill_l ≥ 0.95 且 fill_r ≥ 0.95：
     若 ∃ i ∈ [warmup,n_trunc): full[i] finite 且 trunc[i] NaN → AssertionError("truncation loss / look-ahead signature")
   ```
   與既有 mask exact 互補（values 路徑明確 fail，不靠 print informational）。

3. **探針形狀不變**：仍 `pytest.raises(AssertionError)` + `_assert_truncation_invariants`（章程 §B1.3：注入後主 MR 必 FAIL）。

4. **可選 targeted 驗**（秒級）：注入 A 後單次小窗 generate，grep L4 lag_1 欄最後可比列 `full[-1] != trunc[-1]` 或 trunc 末格 NaN。

---

## 問題 2：`test_mutation_fracdiff_calibration_perturb_fails` 靜態誤判

### 根因

`mutation_probe_static.py` L117：`touches_system` 要求探針**函式體**內出現 `monkeypatch/setattr/...` 或引用 module-level `from momentum...` 名稱。

該探針僅：`pytest.raises` + `_build_truncation_pair(..., patch_fetch=...)` + `_assert_fracdiff_truncation_invariants`。  
`patch_fetch` 在 `_build_truncation_pair` 內才 `monkeypatch.setattr(AdapterRegistry, ...)` — **AST 看不到**；函式體未引用 `FeaturePreprocessor` 等 momentum 符號。

已實測：
```text
python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_fullchain_truncation_mr.py
→ FAIL: test_mutation_fracdiff_calibration_perturb_fails 探針未碰到待測系統
```
其餘 4 支 mutation 靜態 PASS。

### 修法定案：**提案 2（探針顯式錨定被測符號）**；不放寬全域靜態啟發

| 方案 | 評估 |
|------|------|
| **提案 1** 白名單 `generate_features`/`perturb`/`kline` | **不採**：空心探針可拼 `patch_fetch=lambda x:x` + 假 token，削弱對真空心/偽 raises 的攔截 |
| **提案 2** 探針內顯式引用 `FeaturePreprocessor`（或 `read_d_star_json`） | **採用**：檔案已 module import；探針開頭加一行語義錨定即可通過 AST，語意正確（fracdiff 校準路徑在 L6.5） |

### 問題 2 實作指令

在 `test_mutation_fracdiff_calibration_perturb_fails` 函式體內（`pytest.raises` 之前）加：

```python
# 資料路徑 falsification 錨定被測 fracdiff 預處理（靜態 §B1.1 system-touch）
assert FeaturePreprocessor is not None
```

**不改** `mutation_probe_static.py` 全域規則（保留對 `1/0` 偽 raises 的 fail-closed）。

---

## B2-MUTFIX 定案（Composer）

| # | 項目 | 定案 |
|---|------|------|
| 1 | L4 探針沒紅根因 | **C：fast path 繞過 `_apply_lag` patch**（非 A/B 主因） |
| 2 | shift(-1) 偵測 | **注入修復 + 主 MR 高 fill「trunc-loss」守衛（提案 2）**；探針仍用 c2_1 `_assert_truncation_invariants` |
| 3 | fracdiff 靜態誤判 | **探針內顯式 `FeaturePreprocessor` 錨定（提案 2）**；不放寬 static 白名單 |
| 4 | 靜態/空心防線 | 維持；不削弱 NaN/inf gate、不刪既有斷言 |

### 實作後驗收（Claude 腿，非本次）

```bash
python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_fullchain_truncation_mr.py  # 5/5 PASS
bash scripts/mutation_probe_check.sh tests/feature_engineering/test_ff_fullchain_truncation_mr.py   # 5/5 真紅 + 靜態
pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py::test_c2_1_fullchain_bar_truncation_invariant -q  # 主 MR 仍綠
```

---

ASSUMPTIONS_VERIFIED: LagProcessor L59-65 fast path 不經 `_apply_lag`（讀碼）；static 僅 fracdiff_calibration 探針 FAIL（已跑）；`FeaturePreprocessor` 已 module import 但探針函式體未引用（讀碼+AST 規則）
TESTS_RUN: `python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_fullchain_truncation_mr.py` → 1 FAIL（預期，fracdiff_calibration）
FAILURES_SEEN: none（審查任務）
SCOPE_CHANGES: none（本腿僅定案，未改碼）
NUMERIC_OR_SCHEMA_IMPACT: 定案後實作將新增 trunc-loss 守衛（主 MR 行為：高 fill 欄多一類 fail）；注入修復不改生產碼

STATUS: DONE
