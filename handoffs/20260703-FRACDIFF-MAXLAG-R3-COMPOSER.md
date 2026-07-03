# R3 Composer read-only verdict — fracdiff max_lag

Task: `fracdiff-maxlag-r3-composer-20260703`  
Mode: read-only adjudication; only this output file was written.  
Input: `handoffs/20260703-FRACDIFF-MAXLAG-R3-FACTS.md`, receipt `20260703T094044Z-fracdiff-maxlag-convfix-slow.log`, cross-check `20260703T054245Z-fracdiff-maxlag-mr-green.log`.

---

## ① 事實 3 — 差分推理與 `_patch_kline_calibration_ohlcv` 設計判讀

### 差分推理（receipt 對照）

| 輪次 | receipt | `test_mutation_fracdiff_calibration_perturb_fails` | 同批其他訊號 |
|------|---------|---------------------------------------------------|--------------|
| 054245Z（resolver 已修、FFT conv 未修） | `…mr-green.log:7337` | **PASSED**（`pytest.raises` 有捕到 `AssertionError`） | 尾擾 MR 未在本輪單獨列出 fail |
| 094044Z（+conv direct 修復） | `…convfix-slow.log:16261` | **FAILED — `DID NOT RAISE`** | 尾擾 MR codec fail（見 §②） |

**裁決：差分推理成立。** conv 修復後 direct conv 消除 FFT 捨入假陽性；該控制在 054245Z 的 raise **不能**歸因於「校準擾動 → d\* 不對稱 → d\* gate」設計意圖路徑，而更像「d\* 已對稱 + FFT 值 gate 假紅」。094044Z 的 `DID NOT RAISE` 與 FACTS 事實 4（conv 行為正確、擾動不再假性外洩）一致。

### 窗座標與 `patch_fetch` 機制（附行號）

**`_build_truncation_pair`**（`tests/feature_engineering/ff_truncation_mr_helpers.py`）：

| 行號 | 行為 |
|------|------|
| `237-255` `_bar_window_dates` | 自 kline 尾端取 `window_bars` 列：`start` = 窗首、`full_end` = 窗尾、`trunc_end` = 窗尾前第 `TRUNC_K+1` 根（`TRUNC_K=10`） |
| `1327-1329` | 單一 `(start, full_end, trunc_end)` 座標 |
| `1333-1347` | `patch_fetch` monkeypatch `AdapterRegistry.fetch_aligned`；**full 與 trunc 兩次 generate 皆經同一 lambda** |
| `1358-1367` | full：`start_date=start`, `end_date=full_end` → fetch 長度 **= window_bars** |
| `1371-1380` | trunc：同 `start`, `end_date=trunc_end` → fetch 長度 **= window_bars − 10** |

**`_patch_kline_calibration_ohlcv`**（`1393-1411`）：

```text
window_start = len(out) - window_bars
cal_end      = window_start + calibration_bars   # calibration_bars=500
擾動區間      = out.iloc[window_start:cal_end]   # OHLCV +delta
```

| 跑次 | `len(out)` | `len < window_bars` 守衛 (`1402-1403`) | 實際擾動區間（fetch 內相對索引） |
|------|------------|----------------------------------------|----------------------------------|
| full | `window_bars` | 否 | `[0, 500)` — 窗內前 500 根 |
| trunc | `window_bars − 10` | **是 → 原樣返回，零擾動** | （無） |

**與 FACTS「兩跑座標對齊則無不對稱」的關係：**

- FACTS 描述的是「若兩跑皆 `len≥window_bars` 且擾動皆落在各自窗內前 500 根」的**假設性對齊**場景；在截斷 MR 實際幾何下 **trunc 永遠短 10 根**，守衛使 trunc **從不擾動**。
- 因此設計缺陷是**雙層**的，不只「對稱 lambda」：
  1. **結構**：同一 `patch_fetch` 套在兩跑，但 trunc fetch 更短 → 守衛使擾動**非對稱**（僅 full 可能擾動），卻**非**「僅 full 校準」的受控單邊實驗（沒有「只擾 full、trunc 保持乾淨」的顯式契約）。
  2. **意圖**：負向控制宣稱「校準擾動 → MR 必 FAIL」，但從未保證失敗走 **d\* gate**；054245Z 走 FFT 值假陽性，094044Z 全綠暴露 oracle 無效。
- 094044Z log 可見 full 側 `1408` 行 `FutureWarning`（float64 賦值進 float32 欄，`…convfix-slow.log:15603` 等），顯示 full 至少**嘗試**施加 +1e6 擾動；trunc 側無對應擾動。全綠仍表示現行 gate 組合**不能**作為「校準路徑」負向控制。

**小結（事實 3）：** 差分推理 ✅；設計缺陷 ✅（測試 bug，非 engine regression）；需 D2 重設計，且驗收必須鎖定 **d\* gate** 為首要失敗路徑。

---

## ② 事實 2 — codec 翻面機制

**選型邏輯**（`momentum/FeatureEngineering/feature_storage.py`）：

| 行號 | 機制 |
|------|------|
| `2554-2562` | 空陣列 → float16；否則 coerce 後試 `astype(float16)` |
| `2568-2575` | 有限值 float16 roundtrip 須全有限，否則 **float32** |
| `2577-2586` | 每元素 abs error ≤ `max(FLOAT16_MAX_ABS_ERROR, abs(v)×FLOAT16_MAX_REL_ERROR)`（`2175-2176`：`1e-12` / `1e-3`），任一超限 → **float32** |
| `2591-2606` `_select_parquet_storage_columns` | **逐欄**對 `source[:, col_idx]` 全持久化向量選型，非前綴局部 |

**094044Z 實證**（`…convfix-slow.log:8546-8561`, `16248-16260`）：

- 欄：`close_1h_trend_BBANDS-Lower_233_fracdiff`
- `Max absolute difference: 0.0078125`（= 2⁻⁷，float16 量化步長）
- `x` 為 float32 精度列（`-18.84375`…），`y` 明載 `dtype=float16`（`-18.84`…）
- 尾擾 `+1e6` 改變全欄值域 → full/trunc 持久化時 codec 選型可翻 → **前綴比對 atol=1e-8 必炸**

**裁決：事實 2 完全成立**；與 B1 idx508（近零分母 → float16 溢出 → sanitize NaN）屬**同一家族、不同症狀**（本例為 ULP 精度差，非 NaN 翻面）。

---

## ③ 獨立裁決 D1–D4

### D1 尾擾 MR 處置

| 選項 | 裁決 | 理由 |
|------|------|------|
| **(a) xfail(strict) + storage epic** | **✅ 採用** | 失敗主因是 persistence codec 全窗值域依賴，非 fracdiff 尾因果洩漏；`FRACDIFF_ATOL=1e-8` 對 float16 儲存語意過嚴且與主 MR 的 `FLOAT16_RTOL` 雙標。xfail 須**獨立 reason**（引用 094044Z `0.0078125` / dtype 證據），可與 B1 同 epic 但勿混為同一症狀文案。 |
| (b) 改比 pre-persistence | ❌ 本 epic 不採 | 護網最強但改測點 + 可能動 helper；需明確授權與新 oracle 設計，應列 storage epic 或 follow-up。 |
| (c) 其他（如僅放寬 fracdiff atol 至 float16 容差） | ❌ 不採 | 會把 codec 翻面**常態化**為可接受誤差，削弱 fracdiff 值級護網且不解決根因。 |

**max_lag 面殘留護網（D1(a) 前提）：** d\* gate、3× max_lag mutation、`test_mutation_fracdiff_full_fit_d_star_fails` 仍有效；MRFAIL-RECONCILE §裁決案 2 聲稱「conv 修後尾擾 MR 轉綠」**已被 094044Z 推翻**——須在 D3 簽核聲明中更正。

### D2 calibration_perturb 控制重設計

**✅ 必做（本 epic 內，測試 bug 修）。**

最低要求：

1. **單邊擾動**：僅 full（或僅 trunc）校準段 +`PERTURB_DELTA`；禁止兩跑共用同一對稱 lambda 卻假設 d\* 不對稱。
2. **顯式 oracle**：`pytest.raises` 內斷言失敗來自 `_assert_d_star_gate`（或先跑 d\* gate 再 values），**不得**再接受 FFT/codec 假陽性。
3. **修補 trunc 守衛**：若仍用相對 `window_bars` 索引，須保證 trunc fetch 長度與座標語意一致，或改為絕對 timestamp 區間擾動。
4. **dtype**：賦值前 `.astype(float64)` 或欄位相容 cast，消除 `1408` FutureWarning 造成的「以為擾動了、實際未寫入」風險。

### D3 簽核範圍聲明

**✅ 照載，並補一條：**

- 已確認：**per-column parquet codec 依全窗值域選 float16/float32** → 影響 B1 截斷 MR 與尾擾值級 MR；**不**納入 max_lag epic 數值正確性簽核。
- **更正：** conv 修復 ≠ 尾擾 MR 綠燈；094044Z 已證 tail 仍紅（codec）。
- storage epic 立案前，尾擾 fracdiff 值級護網視為 **xfail 暫停**，非「已驗證通過」。

### D4 storage epic 立案升級

**✅ 照載。**

立案文字採用 FACTS 版本：**已確認根因** — per-column float16/32 codec 依**全窗**欄位值選型 → 長度/尾值可改寫前綴儲存精度（B1：NaN/inf 翻面；尾擾：ULP 差）。不再是假說。

---

## ④ 對 Claude 建議票（D1=(a), D2/D3/D4 照載）的挑戰

| Claude 票 | Composer 立場 |
|-----------|---------------|
| D1=(a) | **同意方向，加三項約束** |
| D2 必做 | **同意** |
| D3/D4 照載 | **同意，且必含 MRFAIL 預測更正** |

**對 D1(a) 的具體挑戰（非推翻，是防再假綠）：**

1. **勿寫成「尾擾只是 noise」** — 0.0078125 是確定性 storage 語意問題；xfail = 明確放棄一條真護網，直到 codec 決定論或 pre-persistence oracle。
2. **B1 與尾擾 xfail reason 應分 symptom 引用** — B1：idx508 finite↔NaN；尾擾：094044Z float32 vs float16 / 2⁻⁷。同 epic、不同 receipt 錨點。
3. **轉綠 gate 須寫進 TODO** — storage 修復後：`test_fracdiff_tail_perturbation_invariant` 去 xfail + 094044Z 同命令全綠；不得僅靠 d\* gate 綠就宣稱尾擾已驗。
4. **D2 驗收應優先於 D1 敘事閉環** — 否則會再次出現「mutation 綠 = 校準路徑已驗」的錯覺（本輪 094044Z 已示範）。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - 054245Z calibration_perturb PASSED vs 094044Z DID NOT RAISE（log 行號已核）
  - _build_truncation_pair patch_fetch 兩跑皆經同一 lambda（1333-1347）；full/trunc 窗長差 TRUNC_K=10（1358-1380）
  - _patch_kline_calibration_ohlcv trunc 側 len<window_bars 早退（1402-1403）；full 側擾動 [0,500)（1404-1410）
  - feature_storage._select_parquet_storage_array 全欄 roundtrip 門檻（2554-2588）；尾擾 fail dtype/0.0078125（094044Z:8546-8561）

TESTS_RUN: none（read-only 源碼 + receipt 檢視）

FAILURES_SEEN: none（本任務）；引用 094044Z：tail codec fail + calibration DID NOT RAISE

SCOPE_CHANGES: none；僅寫本檔

NUMERIC_OR_SCHEMA_IMPACT: none（裁決識別既有 storage 精度影響，未改碼）
```

STATUS: DONE
