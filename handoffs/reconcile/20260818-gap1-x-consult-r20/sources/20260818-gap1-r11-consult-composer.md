brief-kind: consult

# GAP-1 G1-R11 consult — COMPOSER R20

**task-id**: `20260818-GAP1-X-CONSULT-R20`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap1-r11-consult-BRIEF.md`  
**date**: 2026-08-18

---

## Verdict

**採主委方案**：退化條件改為 `std == 0.0 or not np.isfinite(std) or np.ptp(values) == 0.0`（`sharpe.py` 與 `pbo._sharpe_pp_1d` 同步）；**不**採相對容差 ε；**不**維持現狀。

理由摘要：（1）Task 1.2 docstring 已寫「常數序列 ⇒ NaN＋status 非 ok」，80×`0.01` 在 `ptp==0` 且 `std≈1.75e-18` 屬實作與 SPEC 字面不一致，非新語意發明；（2）業界套件亦無相對容差／`ptp`，近常數浮點 case 多回巨大有限 SR——本專案選擇 stricter 退化 NaN 合理；（3）golden 三案例與常數切片 fixture 實跑不受影響；（4）ULP 分裂反例（段 C）在真實管線極罕見，可作具名 residual 邊界，不足以改推 ε 容差。

---

## §0 挑戰前提（brief 逐條）

| 前提 | 標記 | 本輪結論 |
|---|---|---|
| `compute_sharpe` 退化條件為 `std == 0.0`（`sharpe.py:89`） | fact-verified | **成立**（現碼 L88–90：`std == 0.0 or not np.isfinite(std)`，無 `ptp`） |
| 80×`0.01` ⇒ `std≈1.75e-18`、SR≈5.7e15、非 NaN | fact-verified | **成立**（探針：`std=1.745668e-18` `ptp=0.0` `sr=5.728465e+15` `status=ok`） |
| `np.ptp(np.full(80,0.01))==0.0` | fact-verified | **成立**（同探針） |
| 業界主流對 std=0 不特判或回 inf/NaN，且**無**相對容差 | assumed | **部分推翻**：無相對容差／無 `ptp` **成立**；但「不特判」不成立——**精確** `std==0` 時 empyrical/quantstats/ffn/vectorbt 有明確分支（`inf` 或 `nan`）；**近常數**（80×0.01）則與本 repo 同型巨大有限值 |
| 真實管線不會產生同數學值、不同 double 之常數序列 | assumed | **可攻但邊際**：CSV 同字串／`float32→float64`／`np.full` 皆 `ptp==0`；ULP 反例需混合不同計算路徑（段 C） |
| `ptp==0` 修法不改 golden 三案例 | assumed | **成立**（pytest 四項實跑 4 passed；矩陣為 `standard_normal*0.01`，無全常數欄） |

---

## A. 業界實作（≥3 源碼，行號）

| 套件 | 常數／std=0 行為 | 近常數 80×0.01 | 相對容差／ptp |
|---|---|---|---|
| **empyrical** `stats.py:700-717` | `len<2`→`nan`；`nanmean/nanstd` 直接除；doc L687「adjusted returns are 0」→ nan | 實跑 `3.03e16` | **無** ε；**無** ptp；`std==0` 走 divide→測試 `flat_line_1` 期望 **`inf`**（`test_stats.py:373`） |
| **quantstats** `stats.py:798-807` | `divisor=returns.std(ddof=1)` 直接除 | 實跑 `1.91e15` | **無** ε；**無** ptp；zeros ⇒ `nan`（除零 warning） |
| **ffn** `core.py:1424-1427` | `er.std(ddof=1)` + `np.divide` + `errstate` | 實跑 `1.91e15` | **無** ε；**無** ptp |
| **vectorbt** `returns/nb.py:330-343` | **`if std == 0.: return np.inf`**（精確比對） | 邏輯重現 `9.09e16` | **無** ε；**無** ptp |
| **pyfolio** `timeseries.py:287` | 委派 `empyrical.sharpe_ratio` | 同上 | 同上 |
| **pandas** / **scipy** | 無 Sharpe 函式；`Series.std(ddof=1)` 對 80×0.01 得 `5.24e-18`（非 0） | — | 無 SR 退化語意 |

**結論 A**：業界一致用 **`std==0` 精確比對**（或無分支直接除），**零**相對容差、**零** `ptp`／`all equal`。精確常數（`std` 恰 0）→ `inf`/`nan`；**G1-R11 同型**近常數浮點 case → 巨大有限 SR。本專案 SPEC 要求常數⇒NaN 比 empyrical/vectorbt 更嚴，主委 `ptp==0` 是對 SPEC 的補洞而非偏離業界。

---

## B. 文獻

| 來源 | 零波動／退化 |
|---|---|
| **Sharpe (1994)** / 標準定義 | SR = 超額報酬均值／報酬標準差；σ→0 時比率在數學上無界，文獻以風險資產需 σ>0 為前提，**不**定義有限 SR 值 |
| **Lo (2002)** *The Statistics of Sharpe Ratios* | 推 SR **估計量**之分布與標準誤；分母為樣本 σ̂，**未**給 σ̂=0 之有限 SR 或 ε 容差；強調估計誤差，非實作退化表 |
| **Bailey & López de Prado — PSR/DSR** | DSR 分母含 `sqrt(1 - γ₃·SR* + …)`；常數報酬 ⇒ SR* 無界或矩 undefined ⇒ 檢定統計**不**可當正常 SR 使用；與「常數切片退化」一致，**未**建議 relative-std 容差 |

**結論 B**：文獻層級**不**支持自訂 ε；零波動屬**未定義／退化**，本專案 NaN+status 合理。

---

## C. 主委方案反例（`ptp==0` 漏網）

探針：`y = np.array([0.01, 0.01, 0.010000000000000002])`

- `np.ptp(y) = 1.734723e-18 ≠ 0`（三個 **不同** IEEE754 位元）
- `std(ddof=1) ≈ 1.23e-18`，`compute_sharpe` ⇒ `status=ok`，`|SR|≈8.15e15`
- `ptp==0` **不**捕捉此列

**真實管線可能性**：本 repo per-period 報酬來自 `pct_change`/向量化算術，同一常數報酬列用 `np.full` 或 CSV 同字串解析 ⇒ **`ptp==0` 實跑成立**（80 字串 CSV、`float32→float64` 探針皆 `ptp=0`）。ULP 反例需刻意混用不同生成路徑（如 `0.01` 常數 + `0.01+1e-16` 累加），**非** Feature Factory／PBO golden 路徑；可列 G1-R11 子項 residual，**不**改推 ε。

---

## D. PBO 影響

實跑：`venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_noise_band tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_detectable tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_undetectable tests/momentum/Analysis/strategy_validation/test_pbo.py::test_constant_slices_produce_exclusions_and_all_degenerate -q` → **4 passed** rc=0。

| 案例 | ptp 修法影響 |
|---|---|
| golden ①②②b | 噪音／alpha 矩陣，無全常數 per-period 欄 ⇒ **PBO 值不變** |
| `test_constant_slices`（全零） | 已 `std==0` 且 `ptp==0` 退化 ⇒ **不變** |
| `test_vectorized_sharpe_matches_compute_sharpe` col 7（80×0.01） | 修法後兩路皆 NaN ⇒ **須更新** col7 断言（現鎖 `|SR|>1e6` 為 G1-R11 殘留）；**非** golden 三案例 |

**結論 D**：golden 三案例 **excl 仍 0**；僅 B4 等價測試需同步（預期）。

---

## E. 修法歸類

**判定：實作 bug 修補（非語意變更）** — 可走 **小任務 + 三家 review**，**不必**延伸檔 + adversarial。

| 依據 | 說明 |
|---|---|
| SPEC / docstring | Task 1.2 已蓋章：「退化：`std(ddof=1)==0`」+ 敘述「常數序列 ⇒ NaN」；80×0.01 為浮點 **未** 滿足字面常數判定 |
| 非新參數 | `ptp==0` 無 ε 選擇問題 |
| 與業界 | 比 empyrical **更嚴**（常數⇒NaN 非 inf），屬契約執行非研究發明 |
| 測試 | golden 不變；`test_vectorized_sharpe` col7 改為 NaN 断言 = 關閉 G1-R11，非 PBO 語意漂移 |

---

## Findings

## COMPOSER-R20-P3-00

**斷言**: 本輪逐項核對 A–E 與 §0 前提後，支持採主委 `ptp==0` 方案、拒絕相對容差與現狀；無需額外 blocking finding。

**碼證**: 探針 `80×0.01`：`ptp=0` `std=1.75e-18` `SR=5.73e15`；行業 4 套件源碼無 ε/ptp（empyrical `stats.py:709-717`、quantstats `798-807`、ffn `1424-1427`、vectorbt `341-342`）；ULP 反例 `ptp=1.73e-18`；pytest golden+constant **4 passed**；`ptp` 仿真：`80×0.01`/`zeros`/`0.5` 皆 degenerate，`edge3`/`micro` 不 degenerate。

**來源摘要**: handoffs/20260818-gap1-r11-consult-BRIEF.md#0daaf5679e9c

[P3] 核對依據＝§0 表 + A–E 段；ULP residual 已記於 C 段，不升格 blocking。

---

ASSUMPTIONS_VERIFIED: sharpe.py L88-90；80×0.01 探針；4 套件源碼+實跑；ULP/CSV/f32 探針；pytest 4 cases  
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_noise_band tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_detectable tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_undetectable tests/momentum/Analysis/strategy_validation/test_pbo.py::test_constant_slices_produce_exclusions_and_all_degenerate -q` → 4 passed rc=0；`bash scripts/completeness_check.sh --single handoffs/20260818-gap1-r11-consult-composer.md --family composer`（收尾跑）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀 consult；`/tmp/composer-gap1-r20` 為探針用）  
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）  
OUTPUT_ARTIFACT: `handoffs/20260818-gap1-r11-consult-composer.md`  
TMP_CLEANUP: 刪除 `/tmp/composer-gap1-r20`；保留 `/tmp/claude-501`  
STATUS: DONE
