# FF fracdiff 截斷 MR d* gate 失敗 — Composer 委員會第三腿

## Scope read
- `handoffs/20260702-FF-DSTAR-GATE-CLAUDE.md`、`handoffs/20260702-FF-DSTAR-GATE-CODEX.md`
- `tests/feature_engineering/ff_truncation_mr_helpers.py`（`_assert_d_star_gate`、`_build_truncation_pair`、`_fracdiff_mr_config_payload`）
- Production：`feature_preprocessor.py`（`_calibration_*`、`_find_min_d`、`_apply_fractional_differencing`）、`_slow_path_parallel.py`、` _d_star_cache.py`
- 對照：`handoffs/20260629-FF-B2-FRACDIFF-codex.md`（L6.5 隔離實測，固定 `max_lag=50`）
- 未跑慢測；靜態讀碼推理。

---

## 挑戰 Claude

**部分同意、核心機制不同意。**

| Claude 主張 | 判定 |
|---|---|
| d* 是 stateful、跨窗不穩、須持久化 epic | ✅ 與 `docs/ROADMAP.md` / stateful audit 一致 |
| production 現行是 whole-window fit，截斷必漂 | ❌ **讀碼不符**。正常路徑 `_calibration_series` / `_calibration_values` 只取 `iloc[:calibration_bars]`（min 500）；whole-window 是 mutation negative control（`test_mutation_fracdiff_full_fit_d_star_fails`） |
| gate 測「設計不保證的性質」，幾乎必然失敗 | ❌ **過強**。B2 設計（600→590、calibration=500）+ 2026-06-29 隔離 L6.5 實測（固定 `max_lag`）顯示 **d* 在尾端截斷下可相同**；現失敗不能歸因「截斷換窗」一句話 |

Claude 把 **cross-window 不穩**（換 start / 換 calibration 語意）與 **同 start、只砍尾 10 bars** 混為一談。後者在 prefix-causal 前提下 **應** 穩定；現失敗指向 **實作未完全 prefix-isolated**，不是「gate 本來就無效」。

---

## 挑戰 Codex

**大方向同意，根因歸因可再收斂。**

Codex 正確指出：production d* 搜尋輸入是 first-500 prefix；600→590 應保留校準前綴；不應把失敗當成「尾端砍掉所以 d* 可漂」的良性結論。

**Codex 列的四項可能** 中，讀碼後我認為 **(3) 不是泛泛的「數值邊界」**，而是可指認的具體耦合：

```3197:3200:momentum/FeatureEngineering/preprocessing/feature_preprocessor.py
        # 限制 weight 寬度：最多序列長度的 10%（上限 252），避免 d≈0.5 時產生大量 NaN
        max_lag = int(self.fracdiff_config.get("max_lag", 0))
        if max_lag <= 0:
            max_lag = min(max(2, len(df) // 10), 252)
```

- full 600 rows → `max_lag=60`
- trunc 590 rows → `max_lag=59`

d* 二分搜每一步都透過 `_fracdiff_values(..., max_width=max_lag)` 做 FFD；**校準輸入同為 500 bars，搜尋幾何卻隨總列數變**。`DStarCache` 的 `fracdiff_hash` / payload 亦含 `max_lag` 與 `row_count`，full/trunc 本來就分開重算——這解釋了 `0.4844 vs 0.4688`（≈1 個 precision=0.02 網格步）而 **不需** whole-window look-ahead。

**佐證**：`20260629-FF-B2-FRACDIFF-codex.md` 在 **同一前綴、pin `max_lag=50`** 時 600→590 **d* 全同**；僅值層 ~1e-10 浮點差。現 B2 full-chain 失敗在 **d* gate**，與 pin max_lag 實測分叉一致。

Codex 的「prefix 輸入可能不同」仍值得保留為 **次要假設 (a)**，但尚未優於 max_lag 耦合的靜態證據。

---

## 獨立判斷：full vs trunc d* 為何仍差？

在「d* 只吃 first-500、截斷是尾端 bar-level」前提下：

| 選項 | 判定 | 證據 |
|---|---|---|
| **(a) 截斷動到 prefix** | **次要可能，待診斷** | 同 `start_date`、trunc 只縮 `end_date`，因果全鏈 **應** 使 row 0..499 相同；若 L1–L6 任一非因果或 streaming 邊界污染，會在 fracdiff 前製造不同校準輸入。尚無靜態證明已發生，需 cheap prefix dump |
| **(b) d* 非純 prefix** | **主因 ✅** | 校準 **值** 取前 500，但 **`max_lag=f(len(df))`**（及 transform 時對全列長度的卷積）使搜尋/輸出 **未與尾端截斷解耦** |
| **(c) 真 bug** | **是 (b) 的具體實作缺陷** | 非 look-ahead 洩漏；是 **stateful 參數標定語意不一致**（校準窗固定、搜尋參數隨窗長漂移）。另：parallel `_statsmodels_adf_pvalue` 用 tail slice、serial/fast 用 head——路徑不一致，但不足以單獨解釋 full/trunc 對照 |
| **(d) 其他** | helper 讀錯 artifact | **排除**：`d_star_parent/full` vs `trunc` 分目錄；`_assert_d_star_gate` 邏輯與 c94c850 逐字相同 |

**結論一句**：失敗 **不是** Claude 說的 whole-window 校準洩漏；**是** Codex 說的「不應視為良性漂移」正確，但根因優先歸 **(b)+(c)：d* 搜尋未 prefix-isolated（max_lag∝row_count）**；**(a)** 需診斷排除後再論全鏈因果。

**Q2（look-ahead）**：現有證據 **不支持** production 用未來 tail 做 d* 決策；mutation full-fit 控制已存在。P0-FF-2 對 **非 fracdiff** 欄的截斷 MR 效力不受此 d* 缺陷否定。

---

## 待決 1–4（Composer 票）

### Q1 — 兩測試是否該存在 / xfail？
- **不刪**。測試意圖正確（600→590、tail perturb 不動 calibration）。
- **現階段可 `xfail(strict=True)`**，理由須寫：**「d* MR 失敗；根因 max_lag(row_count) 耦合或待證之 prefix 輸入差異 — 見 d* epic」**；**禁止**寫「d* 漂移屬預期」。

### Q2 — 截斷情境是否藏 look-ahead？
- **否（目前證據）**。whole-window 非 production 路徑。
- 是 **參數標定與窗長耦合 bug / 設計缺口**，需修或改測法，非放行。

### Q3 — 8 passed 能否收 P0-FF-3？
- **可**。主 MR 刻意排除 fracdiff；winsor/rank/zscore/gaussian/align 已覆蓋。
- **fracdiff 因果未簽核**；獨立 d* epic 待辦。

### Q4 — 修向（推薦 **C + 診斷 + 短期 xfail**）

1. **立即**：`test_fracdiff_truncation_invariant`、`test_fracdiff_tail_perturbation_invariant` → `xfail(strict=True)`，連結 ROADMAP d* 持久化 / `docs/FEATURE_STATEFUL_PARAM_AUDIT_FINAL.md`。
2. **Cheap diagnostic（下一小步）**：在 helper 加 `_diagnose_fracdiff_calibration_prefix(full, trunc)` — 對失敗欄（如 `close_statistics_LINEARREG-INTERCEPT_13_Log1p`）在 L6.5 入口 dump **first-500 原值** + 記錄兩跑的 `max_lag` / `row_count`；第一個 mismatch index 區分 (a) vs (b)。
3. **Production 修（epic）**：
   - **選一**：`max_lag` 改為 **固定 config** 或 **`f(calibration_bars)`**，禁止 `f(len(df))` 在 d* 搜尋路徑；
   - **或**：固定參考 d*（Option A / persisted d*）train-serve 一致。
4. **測試修（B 層）**：fixed-reference d* injection（full run 產 d* → 兩跑強制同 d*）再比 **fracdiff 輸出 prefix** — 測 **transform 因果**，與 **d* 校準 MR** 分層；保留 calibration perturb / full-fit mutations。
5. **勿** 用放寬 d* gate 門檻或刪除 exact 比對來假綠。

---

## 三方收斂建議

| 議題 | Claude | Codex | Composer |
|---|---|---|---|
| whole-window production? | 暗示是 | 否 | **否** |
| gate 是否本無效? | 幾乎必然失敗 | 有效意圖、現失敗待查 | **意圖有效；失敗有具體根因** |
| 主因 | 截斷換窗 | prefix 差 / 待查 | **max_lag(len(df)) 耦合 (b)(c)** |
| look-ahead? | 待決 | 未證實 | **未證實** |
| 修向 | xfail 引 epic | C+診斷+B | **同意 Codex C+診斷；補 max_lag 為首修候選** |

---

## Closure report

```
ASSUMPTIONS_VERIFIED:
  - _calibration_series/values 取 min(len, calibration_bars)，預設 ≥500（feature_preprocessor.py:175-187）
  - max_lag 預設 len(df)//10：600→60、590→59（feature_preprocessor.py:3198-3200）
  - d* 搜尋用 calibration prefix 值 + max_lag 寬度（_find_min_d:3699-3741；process_fracdiff_column_values:155-165）
  - fracdiff MR 窗 600→590、calibration_bars=500（ff_truncation_mr_helpers.py:207-234, 158-160）
  - 20260629 隔離 L6.5 pin max_lag=50 時 600→590 d* 相同（handoff 實測記錄）
  - helper d_star 分 full/trunc 目錄讀取（ff_truncation_mr_helpers.py:1320-1357）

TESTS_RUN: none (read-code only per request)

FAILURES_SEEN: none in this session; underlying B2 failure documented in Claude handoff (0.4844 vs 0.4688)

SCOPE_CHANGES: none; added this handoff only

NUMERIC_OR_SCHEMA_IMPACT: none
```

STATUS: DONE
