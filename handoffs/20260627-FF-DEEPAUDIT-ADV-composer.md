# FF 深稽 Claude 腿 — Adversarial Review (Composer 2.5)

**審查者**: composer | **被審物**: `handoffs/20260627-FF-DEEPAUDIT-CLAUDE-LEG.md` | **日期**: 2026-06-27

**結論一行**: **須修後再審** — §A 主幹正確但 A5 漏報既有 V-5；§B B2/B3 已用真 run 坐實；§C 的 C1-2 規格不可證偽、C1-1 抓不到 B2、C2-1 warmup 策略有假綠路徑；§D 排除 P0-FF-3 與 C2 宣稱覆蓋範圍不一致。

---

## 必答逐項

### 1. §A 事實準不準

| 項 | 判定 | 理由 + 反例 |
|----|------|-------------|
| A1 TA-Lib atomic = smoke | **OK** | `tests/test_atomic_indicators.py` 僅 `in result.columns`；`tests/test_talib_wrapper.py` 僅 registry 數、shape、RSI(close)≠RSI(volume)，**零** `assert_allclose` vs `talib.*`。全 repo `tests/` grep `assert_allclose.*talib` = 0。 |
| A2 手刻 = property 非 reference | **OK** | `tests/momentum/test_entropy_indicators.py` 等：count/prefix/constant→0/insufficient→NaN；grep `assert_allclose|scipy|canonical` in entropy tests = 0。 |
| A3 衍生 volume 無值驗 | **OK** | `test_atomic_indicators.py::test_volume_indicator_engine` 只 assert `OBV`；VWAP/Klinger/ForceIndex/EOM 無專測。 |
| A4 requires_kline 不存在 | **OK** | `grep requires_kline tests/ momentum/` 僅 handoff/docs 命中；`pytest.ini` markers 無 `requires_kline`。 |
| A5 全鏈因果 = 窄 | **RISK** | 單算子 rolling-quantile MR 描述正確。但 **漏報** `tests/feature_engineering/test_failopen_correctness.py::test_v5_prefix_no_leakage_after_warmup`：已對 `generate_features()` 做 **end-date 截短 + warmup 後 prefix byte 相等**（fast config、單 TF、preprocessing off）。Claude 寫「非全鏈」過度 — 是 **窄 config 的全鏈**，非 bar 級尾端擾動 MR。另漏：**cycle/statistics/custom atomic 模組零專測**（`test_atomic_indicators` 只覆 trend/momentum/volatility/volume/pattern 五類）。 |

### 2. §B 可疑點真假

| 項 | 判定 | 真 run 反例 |
|----|------|-------------|
| B1 input_type 預設 single 陷阱 | **RISK**（機制真、現網未觸發） | `talib_wrapper.py:354-360` 未映射→`single`。`FAKE_HLC_IND`→`single` 已驗。現 132 指標皆在 `_INPUT_TYPE_MAP`/`CDL*`，**當前無 live misroute**；風險在新增指標靜默餵 close。 |
| B2 BETA/CORREL close_volume | **BLOCK（語義錯配）** | `abstract.Function('BETA').input_names` = `price0=high, price1=low`；實作餵 `(close, volume)`。真 run：`wrapper == talib.BETA(close,volume)` **True**；`== talib.BETA(high,low)` **False**。欄位名 `statistics_BETA_*` 暗示 TA-Lib β，實為 close–volume 相關，**非文件語義**。 |
| B3 Klinger/ForceIndex/EOM 非 canonical | **BLOCK（Klinger）/ RISK（FI/EOM）** | ForceIndex：`diff(close)*volume` raw，**非** EMA13 平滑 canonical（`match_raw=True`）。Klinger VF vs trend-aware canonical：**corr=0.59**，同號率 69.8% — 公式實質不同。EOM 缺常見 scale（1e8）；metadata 未標「簡化變體」。 |
| B4 compute_batch 忽略 data_sources | **OK** | ADX batch 欄 `hlc_momentum_ADX_14`；RSI batch 才迭代 close/open。設計正確，非 bug。 |

### 3. §C 測試設計會不會假綠

| 項 | 判定 | 理由 |
|----|------|------|
| C2-1 warmup 對齊 | **BLOCK** | 腿未指定 warmup 算法。既有 V-5 用 `_warmup_cutoff_row` = **首個全欄非 NaN 列**（data-dependent），非 `estimate_max_warmup_bars(config)`。假綠路徑：(a) 截斷改變「首全填列」→ `max(cutoff)` 仍可能對齊錯誤語義的 warmup；(b) 只比 post-warmup → **warmup 區 leakage 全掩蓋**；(c) V-5 用 `_fast_config_payload`（preprocessing off、單 close source）— C2-1 宣稱 L1–L6.5+CGSA+multi-TF **與現網 V-5 不等價**，不能當已覆蓋。 |
| C1-3 canonical oracle | **BLOCK** | 「手算 canonical」未定義出處 = 易拿實作反推。Klinger 已證與主流公式分歧；若 golden 來自現實作 = 自指 oracle。 |
| C1-1 vs talib differential | **RISK** | 對 **single-input + 正確欄位** 的 wrapper 傳遞有效。但 **抓不到 B2**：測試若沿 `_prepare_inputs` 路徑，錯誤 (close,volume) 與 wrapper 一致仍綠。須對 BETA/CORREL 額外 assert `talib.BETA(high,low)` 或明示產品語義。 |
| C1-2 input_type vs talib | **BLOCK** | 規格寫「欄位集合 ⊆ `abstract.Function.input_names`」**不可實作**。talib abstract 用 `price`/`prices`/`price0`/`price1`，非 `high`/`low`/`real`；腳本審計 132 指標 **71 條假陽性**。 |
| mutation 門檻 | **RISK** | C1-mutation（改 source/param）對 C1-1 有效。C2-mutation `shift(-1)` 在 post-warmup 可比區才紅；warmup-only leak 仍綠。C1-mutation 改 EOM 不影響 B2。未要求 **實作前先寫 failing mutation probe**（章程 §B 硬門檻）。 |

### 4. §D 邊界

| 項 | 判定 | 理由 |
|----|------|------|
| 不全重測 V-6/L6.5/L3 | **OK** | 與 reconcile 一致；`test_numba_rolling.py`、`test_causal_winsor.py`、`test_failopen_correctness` V-6 為真 P0。 |
| 本批僅 1/2/4，排除 3 | **BLOCK** | reconcile 列 P0-FF-3（MultiTF 高頻截斷 + **production 全欄**）與 P0-FF-2 同級。C2-1 宣稱 multi-TF+全層，§D 卻 defer P0-FF-3 — **範圍自相矛盾**。現 V-5 僅 fast/minimal，**production preset 全欄矩陣仍零 MR**。 |
| P1-FF-7 vs P0-FF-1 重疊 | **RISK** | reconcile P1-FF-7（wrapper source）與本腿 P0-FF-1 重疊；须在 SPEC 合併避免雙重或漏項。 |

### 5. §E 四個前提（委員答案）

| # | 答案 |
|---|------|
| E1 warmup 不假綠 | 比對區間 = `common_index[:N-k]` 的 **config-driven** `estimate_max_warmup_bars(preset)` 之後，**禁止** data-dependent「首全填列」。另加 C2-2 尾端 OHLCV 擾動。先 assert `columns` 集合與順序完全一致再比 values+NaN mask。 |
| E2 BETA/CORREL | **Bug（除非產品明示）**：特徵語義應麼改餵 `(high,low)` 對齊 TA-Lib，要麼改名（如 `Beta_CloseVolume`）+ metadata 標非標準。 |
| E3 C1-3 canonical | 分級：(1) talib/scipy/pandas 有一致 API → EXACT differential；(2) 文獻公式 → 獨立 reference 實作（**不得** import 被測模組）；(3) 簡化變體 → 章程 §B8 三方簽 off 後 golden-lock + metadata `variant=simplified`。 |
| E4 requires_kline + CI | 雙 job：**PR** `-m "not requires_kline"` smoke；**nightly correctness** 缺 manifest/kline → **FAIL**。須同步 `pytest.ini` 註冊 marker（章程 A18 已列、repo 未建）。逃生口只給開發者顯式 exclude，不給 CI 靜默綠。 |

---

## BLOCK 清單

1. **C1-2 規格不可證偽** — 反例：talib `RSI` 的 `input_names={'price':'close'}`，我方 `single`；按腿文「欄位 ⊆ input_names」永遠失敗或需另寫映射表。**修法**：建 `TALIB_INPUT_SEMANTICS` 表（indicator → 我們的 input_type → 對應 df 欄位），測 `_prepare_inputs` 產出的 ndarray 與 talib 直呼用同欄位 **byte 相等**；另加「從 map 刪除 ATR」mutation 必紅。

2. **B2 BETA/CORREL 語義錯配（已真 run）** — 反例：`talib.BETA(high,low,5)` ≠ wrapper 輸出；`= talib.BETA(close,volume,5)`。**修法**：產品決策前 C1-1 須含 **雙 oracle** 測試；預設應 fail 直到對齊 high/low 或改名。

3. **C2-1 warmup 策略未定 + 與 V-5 不等價** — 反例：V-5 `_fast_config_payload` preprocessing off；C2 宣稱 L6.5 on。`_warmup_cutoff_row` 在 trunc 改變填滿模式時可比區漂移。**修法**：寫死 `preset=production`（或與 P0-FF-3 同批）、warmup = `estimate_max_warmup_bars`、比對 `iloc[warmup:-k]`；列清與 V-5 差異表。

4. **§D 排除 P0-FF-3 與 C2 覆蓋宣稱矛盾** — 反例：reconcile 三腿 P0#3；本腿 C2「multi-TF 粗→細」但 §D defer FF-3。**修法**：要麼 C2-1 第一版僅單 TF + 明示不取代 FF-3，要麼本批納入 FF-3 抽樣欄。

5. **C1-3 自指 oracle 風險（B3 已證）** — 反例：Klinger VF corr=0.59 vs trend-canonical；用現輸出 freeze golden 會鎖死錯公式。**修法**：手刻指標先 adversarial 定義 variant + 獨立 reference，再 golden。

6. **A5 漏報 V-5 致 scoping 失真** — 反例：`test_v5_prefix_no_leakage_after_warmup` 已存在。**修法**：§A 改為「bar 級尾端擾動 MR 缺；end-date 截短 MR 有（窄 config）」。

---

## RISK 清單

- **B1**：預設 `single` 陷阱在碼上；需 registry 完整性測 + 新增指標 CI gate。
- **C1-1**：抓 wrapper 傳遞不抓 B2 類語義錯配；須 case 表含 close_volume 族。
- **C2-mutation**：post-warmup-only 比較；須加 C2-2 擾動 + warmup 區不得有 non-NaN 差異的獨立 assert。
- **C4**：`requires_kline`/`DATA_MANIFEST` 方向對，但 `pytest.ini` 未註冊 marker；C4 未規定 manifest 覆蓋哪些 symbol×TF（三方簽核要求 10×3）。
- **cycle/statistics/custom atomic**：A1 暗示 cycle/statistics 有測，實無 — P0-FF-1 抽樣須明示含這三模組。
- **P1-FF-7 與 P0-FF-1**：避免 SPEC 重複或漏 wrapper 多路徑（polars/numba）。

## OK 清單

- A1–A4 核心斷言經 grep/讀碼確認。
- B4 compute_batch 行為符合設計。
- 不全重測 V-6/L6.5/L3 numba differential 合理。
- C1-1 / C4-1/2/3 方向正確（在修 BLOCK 後）。
- `test_feature_factory_operators.py` 對 L2 derived 有手算 oracle（腿未列，但不削弱 A1）。

---

## §C 測試設計補強（讓 mutation 真的擋得住）

1. **C1-2 替換為「prepare_inputs equivalence」**：每指標 `wrapper.compute` vs 依 `TALIB_INPUT_SEMANTICS` 直呼 `talib.FUNC(*arrays)`；mutation：從 `_INPUT_TYPE_MAP` 刪一項 → 測試必紅。

2. **B2 專項**：`test_beta_correl_semantics` — assert wrapper == `BETA(high,low)` **或** pytest.mark 明示 `intended_close_volume` + 與 `BETA(high,low)` **不相等**（防回歸成假 talib）。

3. **C2-1 warmup**：`warmup = estimate_max_warmup_bars(config, primary_tf, tfs)`；`compare = full.iloc[warmup:-k]` vs `trunc.iloc[warmup:-k]`；**禁止** `_warmup_cutoff_row` 類 data-dependent cutoff。

4. **C2-2 必與 C2-1 同檔**：尾 k bar OHLCV `±1e6` 後 `full.iloc[:-k]` 與 unperturbed `trunc` 比；mutation `shift(-1)` 在 L3 rolling 必紅。

5. **C1-3 手刻**：獨立 `references/volume_indicators_ref.py`（不 import 被測模組）；Klinger/EOM 標 `variant`；mutation EOM `*`→`/` 必紅。

6. **C1/C2/C4 mutation 先於實作**：TDD 順序寫 failing probe（章程 §B），合併前 adversarial 重跑同一反例（§B8）。

7. **Config 分級**：`test_ff_causal_mr_production`（requires_kline, nightly）vs `test_ff_causal_mr_fast`（smoke）— 勿用 fast 冒充 production 覆蓋。

8. **Columns gate**：C2 先 `assert list(full.columns)==list(trunc.columns)` 再比 values，防 silent drop 假綠。

---

## 驗證命令摘要

```bash
# A1/A4
grep -rn "requires_kline" tests/ momentum/
rg "assert_allclose.*talib" tests/  # 0

# B2/B1/B3 真 run（2026-06-27 已執行）
# BETA: wrapper==BETA(close,volume) True; ==BETA(high,low) False
# Klinger VF corr vs trend-canonical: 0.5938
# ForceIndex == raw diff*volume: True
```

---

ASSUMPTIONS_VERIFIED: §A grep/讀碼；B1/B2/B3/B4 真 run `BTCUSDT/12h` kline；V-5/C2 讀 `test_failopen_correctness.py`；pytest.ini markers 讀檔
TESTS_RUN: 上述 inline python 驗證腳本（非 pytest）；repo grep
FAILURES_SEEN: none（審查任務）
SCOPE_CHANGES: none（僅寫 review 檔）
NUMERIC_OR_SCHEMA_IMPACT: none

HANDOFF_NOT_UPDATED: 審查任務，依合約不覆寫根 HANDOFF.md

STATUS: DONE
