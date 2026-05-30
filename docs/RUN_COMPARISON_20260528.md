# Run Comparison — NaN 優化前後 + IC-First/Fracdiff

> 日期：2026-05-28  
> 新 run：`case_search_api_20260528.log` + `data_cache/features/ETHUSDT/1h/31d6e92eb5f1de299e03d8ab74dbe693`  
> 對照組：`RUN_COMPARISON_20260521.md`（baseline pipeline）+ `problem_analysis_20260522_070240`（hash `c4403`，優化前 NaN summary）  
> 優化內容：`NAN_REDUCTION_STRATEGY.md` 三 step（cascade blacklist / dead feature drop / ADF safe-skip）

---

## 0. ⚠️ 比較前必讀：三個 confound（非 apples-to-apples）

這次 run 與 baseline **不是乾淨對照**，混入了三個同時變動的變因：

| 變因 | Baseline (20260521) | New (20260528) |
|------|---------------------|----------------|
| L6.5 mode | `legacy`（全特徵 winsor+rank+zscore+gaussian，**無 fracdiff**）| `ic_first_pre`（winsor+**fracdiff**，無 rank/zscore/gaussian）|
| Fracdiff | ❌ disabled | ✅ enabled |
| NaN 三優化 | ❌ 無 | ✅ 有 |
| Config hash | `c4403`（NaN summary）| `31d6e` |
| 指標範圍 | 全開（ms/ent/tr ON）| 全開（ms/ent/tr ON）|
| 資料範圍 | 20,352 rows | 20,352 rows（2024-01 ~ 2026-04）|

→ **時間差異無法單獨歸因於 NaN 優化**（IC-First 改變了 L6.5 工作量）。本報告會逐項拆解可歸因 vs 不可歸因。

---

## 1. TL;DR

1. **三優化中 2 個生效、1 個未生效、發現 2 個 bug**：
   - ✅ **ADF safe-skip 生效**：log 135 次呼叫，每 chunk bypass 18–46% 欄位 → 直接貢獻 L6.5 提速。
   - ⚠️ **Cascade blacklist 部分生效**：CDL 正確攔截（L2/L3/L4 各 strip 61 cols），但 **HT_DCPHASE 完全漏網（804 個衍生殘留）** ← **命名 bug**。
   - ❌ **Dead feature drop 完全未觸發**（0 次）：CGSA/IC-First mode 走 registry streaming，不經 frame path（此為 PLAN §2.7 已知限制，但意味生產模式下 0 效果）。
2. **發現命名 bug（critical）**：實際 codebase 對多組件指標用 **hyphen**（`HT-DCPHASE`、`MACD-Line`、`STOCH-slowk`、`AROON-aroonup`、`LINEARREG-ANGLE`），我的 pattern 用 **underscore** → HT_DCPHASE blacklist 與多個 ADF safe-skip pattern 失配。單元測試「通過」是因為測試也用了錯誤的假設命名。
3. **L6.5 提速 14%**（1,333s → 1,150s）儘管多做了 fracdiff — IC-First 省掉 rank/zscore/gaussian + ADF safe-skip 省掉 ~一半 ADF。
4. **特徵數幾乎不變**（442,079 → 441,103，-976）— 這 **符合設計**：headline HIGH_NAN（~117K）主體是 12h warmup 放大，依「不可能三角」我們刻意保留（Plan No-Buffer）。
5. **RSS 峰值下降**（2,670MB → 2,226MB），無 OOM。

---

## 2. Pipeline 階段時間比較

| 階段 | Baseline (legacy, no fracdiff) | New (ic_first_pre, +fracdiff) | 差異 | 可歸因？ |
|------|-------------------------------|-------------------------------|------|---------|
| L1 + L2 derived | 536.60s | **527.81s** | -1.6% | 不可歸因（L2 邏輯未變）|
| L3 rolling | ~302s（159,069 cols）| ~319s（159,069 cols）| +5.6% | 不可歸因（cols 相同；雜訊）|
| L4 lag | ~42s（13,488 cols）| ~（13,000 cols）| -488 cols | 部分歸因（CDL lag 被攔）|
| L6 meta | – （11 cols）| – （11 cols）| 0 | – |
| **L6.5 preprocessing** | **1,333.37s** | **1,150.15s** | **-13.7%** | ✅ 可歸因（IC-First + ADF safe-skip）|
| Total（L2 起 → persist）| ~2,449s (40m49s) | ~2,216s (~37min) | -9.5% | 混合 |

**L6.5 拆解**（最大可歸因項）：
- Baseline legacy：全 442K 特徵跑 winsor + rank + zscore + gaussian（無 fracdiff）
- New ic_first_pre：全 441K 特徵跑 winsor + **fracdiff**（無 rank/zscore/gaussian）
- 即使**多做了 fracdiff**，因 (a) IC-First 省掉 rank/zscore/gaussian (b) ADF safe-skip 對 135 個 chunk 各 bypass 18–46% 欄位 → 淨 **-13.7%**。

---

## 3. RSS / 記憶體

| 指標 | Baseline | New | 差異 |
|------|---------|-----|------|
| L6.5 峰值 RSS | 2,670 MB（12h_L2_WorldQuant）| 2,226 MB（1h_L2_Ratio）| -16.6% |
| OOM | 無 | 無 | – |
| effective_workers | 1（disk safety）| 1（disk safety）| 同 |

兩者都在 8GB M1 上有充分餘裕，CGSA streaming 穩定。

---

## 4. 特徵數比較

| Layer | Baseline | New | 差異 | 說明 |
|-------|---------|-----|------|------|
| L1 | 1,683 | 1,683 | 0 | 不變 |
| L2 | 46,819 | 46,819 | **0** | CDL 在 baseline 已由 `RATIO_UNSAFE_CATEGORIES` 攔 → 我們的 L2 blacklist 對 CDL **冗餘**；HT_DCPHASE 因 bug 未攔 |
| L3 | 159,069 | 159,069 | **0** | 同上：CDL 已被既有 guard 攔；HT_DCPHASE 漏網 |
| L4 | 13,488 | 13,000 | **-488** | ✅ CDL lag 新被攔（L4 在 baseline 無 pattern guard）|
| L6 | 11 | 11 | 0 | – |
| **Total** | 442,079 | 441,103 | **-976** | 主要來自 L4 CDL lag |

→ **特徵減少極小（-0.2%）**，且幾乎全部來自 L4 CDL lag。原因：
1. CDL 在 L2/L3 早已被 `RATIO_UNSAFE_CATEGORIES` 攔 → 我們的 cascade blacklist 對 CDL 在這兩層是冗餘（無新增效果）。
2. HT_DCPHASE 因命名 bug 完全沒攔到（應攔 804 個，實際 0）。
3. Dead feature drop 在 CGSA mode 未觸發。

---

## 5. NaN 比較

| 指標 | Baseline (`c4403` problem_analysis) | New (`31d6e` data_quality) | 說明 |
|------|-------------------------------------|----------------------------|------|
| total features | 442,079 | 441,103 | -976 |
| HIGH_NAN | 117,052 | 116,912 | **-140（幾乎不變）** |
| MID_HOLE | 2,358 | 5,256 | +2,898（注意：兩工具定義不同，見下）|
| trailing | 0 | 724 | 工具差異 |
| recommended_start | index 3,277（16.1% loss）| index 3,265（16.0% loss）| 幾乎不變 |

> ⚠️ **HIGH_NAN / MID_HOLE 跨工具不可直接比**：baseline 用 `problem_analysis`（WARMUP_ONLY 獨立分類），new 用 `browse_data_quality`（無 WARMUP_ONLY 分類，warmup 散入 high_nan）。MID_HOLE 數字差異主要是分類定義不同，非實質惡化。

**HIGH_NAN 主體分析（為何幾乎不變 — 符合設計）**：
- New run `warmup_distribution`：`>1000` bucket = 115,020 個（26%）→ 這些是 **12h 指標 warmup × tf_ratio 放大**的特徵。
- 依 `NAN_REDUCTION_STRATEGY.md` 不可能三角，我們**刻意選 Plan No-Buffer**（保留 warmup NaN，XGBoost 原生處理）。所以 HIGH_NAN headline 不該降 — **這是預期行為**。
- 真正該被優化清掉的是「計算錯誤值」（CDL/HT_DCPHASE 衍生）與「死特徵」，而非 warmup NaN。

**仍殘留的問題特徵（與 baseline 相同，非本次優化目標）**：
- `ms_*_large_trade_ratio_*`（~117K 潛在）：資料源缺失（trades missing），屬 RUN_COMPARISON_20260521 §3.2 方案 B+C，**尚未實作**。
- `*_MIDPOINT_*_Skew_W3` / `*_HT-TRENDMODE_*_Kurt_W*`：warmup 誤判 + 離散指標統計算子語義 mismatch，屬 RUN_COMPARISON_20260521 §3.3，**尚未實作**。

---

## 6. 三優化逐項實測效果

| 優化 | 預期 | 實測 | 判定 |
|------|------|------|------|
| **Step 1 Cascade Blacklist** | 攔 CDL + HT_DCPHASE 下游衍生 | CDL：✅ L2/L3/L4 各 strip 61 cols（log 確認）；HT_DCPHASE：❌ **0 攔（804 殘留）** | ⚠️ **半成功**（CDL 對；HT_DCPHASE naming bug）|
| **Step 2 Dead Feature Drop** | 清 `nunique<2` / `valid<100` | ❌ **0 次觸發**（CGSA/IC-First 走 registry，不經 frame path）| ❌ **生產模式無效**（已知限制）|
| **Step 3 ADF Safe-Skip** | bypass 嚴格 I(0) 欄位的 ADF | ✅ **135 次**，每 chunk bypass 18–46%；貢獻 L6.5 -13.7% | ⚠️ **生效但漏一半**（MACD-Line/HT-SINE/STOCH-*/AROON-*/LINEARREG-ANGLE 因 naming bug 未 skip，本可更快）|

---

## 7. 發現的 2 個問題

### 7.1 🐛 Critical：hyphen/underscore 命名失配

實際 codebase 對**多組件指標**用 hyphen，我的 pattern 全用 underscore：

| 指標 | 我的 pattern | 實際命名 | 命中 | 漏失 |
|------|------------|---------|------|------|
| HT_DCPHASE（blacklist）| `HT_DCPHASE` | `HT-DCPHASE` | 0 | **804** |
| MACD Line/Hist/Signal | `_MACD_Line_` 等 | `MACD-Line` 等 | 0 | 10,452 |
| HT-SINE | `_HT_SINE_` | `HT-SINE` | 0 | 1,608 |
| STOCH-slowk/d | `_STOCH_slowk_` 等 | `STOCH-slowk` 等 | 0 | 3,216 |
| AROON-aroonup/down | `_AROON_aroonup_` | `AROON-aroonup` | 56 | 2,352 |
| LINEARREG-ANGLE | `_LINEARREG_ANGLE_` | `LINEARREG-ANGLE` | 216 | 7,236 |
| PLUS-DI / MINUS-DI | `_PLUS_DI_` | `PLUS-DI` | – | – |
| L2 Cross | `_Cross_` | `..._Cross`（suffix）| 0 | 4,292 |

**正確命中的**（指標名無內部 hyphen）：`_RSI_`、`_MOM_`、`_ROC_`、`_TRIX_`、`_ADX_`、`_WILLR_`、`_MFI_`、`_CMO_`、`_NATR_`、`_APO_`、`_PPO_`、`_ULTOSC_`、`_BOP`、`_CORREL_`、`_TsRank_`、`_BinarySignal_`。

**根因**：寫 pattern 前未驗證真實 codebase 命名；單元測試用了同樣的假設命名 → 測試通過但與現實脫節。

**影響**：
- Cascade blacklist：HT_DCPHASE 的 804 個「數學錯誤值」衍生洩漏到輸出（correctness 問題，0.18% 特徵）。
- ADF safe-skip：MACD-Line/HT-SINE/STOCH-*/AROON-*/LINEARREG-ANGLE 沒被 skip → ADF 多跑了（performance only，非 correctness）。

### 7.2 ⚠️ Dead Feature Drop 在 CGSA/IC-First mode 0 效果

- PLAN §2.7 已明載「CGSA-streamed L3 不在範圍」，但實測發現**整個 dead drop 在 CGSA mode 都不觸發**（不只 L3）—因 `_run_layer6_5_preprocessor` 在 CGSA 分支走 `transform_registry_groups` 並回傳空 frame，frame-path 的 dead drop 形同虛設。
- 由於 M1 8GB 生產環境預設走 CGSA，**dead feature drop 實質上在生產從不執行**。
- 這比 PLAN 預想的「只缺 L3」更嚴重：L1/L2/L4/L6 的死特徵在 CGSA mode 也沒被清。

---

## 8. 是否符合預期？

| 維度 | 預期 | 實際 | 評分 |
|------|------|------|------|
| ADF 計算節省 | 省 ADF CPU | ✅ 135 次 bypass，L6.5 -13.7% | ✅ 達標（但因 naming bug 未達上限）|
| CDL 下游清除 | 全層攔截 | ✅ L4 -488；L2/L3 既有 guard 已攔 | ✅ 達標 |
| HT_DCPHASE 下游清除 | 全層攔截 | ⚠️→✅ 原 0 攔（naming bug）；**修正後命中 804** | ✅ 修正後達標 |
| 死特徵清除 | nunique<2 / valid<100 | ⚠️→✅ 原 CGSA 0 觸發；**行動 #3 已實作 CGSA dead-drop** | ✅ 修正後達標（待重跑驗證）|
| 不誤殺有效特徵 | L1 CDL/HT_DCPHASE 保留 | ✅ L1 CDL 122 個保留 | ✅ 達標 |
| 不以 NaN ratio 丟欄位 | warmup NaN 保留 | ✅ HIGH_NAN 主體保留 | ✅ 達標（符合設計）|
| 計算時間 | 不增（甚至略減）| ✅ L6.5 -13.7%, RSS -16.6% | ✅ 達標 |

**總評：部分符合預期（4✅ / 2❌ / 1半）**。核心架構與設計方向正確（ADF safe-skip、CDL 攔截、不誤殺、不碰 warmup NaN 都對），但兩個 bug 讓 HT_DCPHASE 攔截與死特徵清除實質失效。**這次比較最大的價值是抓出單元測試漏掉的命名失配 + CGSA mode 限制。**

---

## 9. 修正行動清單

| # | 行動 | 嚴重度 | 範圍 | 狀態 |
|---|------|--------|------|------|
| 1 | **修 hyphen 命名**：`cascade_blacklist` 預設 `HT_DCPHASE`→`HT-DCPHASE`；`adf_safe_skip` whitelist 多組件 pattern 全改 hyphen；L2 Cross `_Cross_`→`_Cross` | **P0 correctness** | utils/cascade_blacklist.py, utils/adf_safe_skip.py | ✅ 完成 |
| 2 | **測試改用真實命名**：從 catalog 抽真實 column name 當 fixture，加「真實命名回歸測試」防再脫節 | **P0** | tests/feature_engineering/test_*.py | ✅ 完成 |
| 3 | **Dead drop 支援 CGSA mode**：`write_raw_from_registry_stream._write_group` per-column 剔除（`dead_column_mask`，與 frame-path 標準一致）；整組全 dead 仍釋放源頭 | **P1** | feature_storage.py, feature_factory.py, utils/dead_feature_filter.py | ✅ 完成（2026-05-28）|
| 4 | 重跑驗證：修正後 HT-DCPHASE 衍生應 ≈ 0（僅 L1 raw 保留）；ADF safe-skip 命中率 ~55%；CGSA dead-drop log 出現 | **P1** | 重跑 ETHUSDT | ⏳ 待使用者重跑 |
| 5 | （既有待辦）large_trade_ratio fail-fast（#3 已從輸出端清除全 NaN 衍生）| **P2** | microstructure_indicators.py | ⏸️ 延後 |
| 6 | ~~前端 warmup 誤判成 mid-hole~~ — **2026-05-28 實測推翻**：分類器正確（已扣 warmup），mid_holes 是小窗 Skew/Kurt 對近常數/離散序列的真實散在 NaN（std≈0→NaN）。**使用者決議維持現狀**（XGBoost + IC Gatekeeper 處理）。詳見 RUN_COMPARISON_20260528_POSTFIX.md §9 | — | — | ✅ 已釐清（不需改）|

---

## 9b. 修正後記（2026-05-28 同日完成 bug #1 #2）

bug #1（hyphen 命名）與 bug #2（測試脫節）已修正並對真實 catalog 驗證：

| 項目 | 修正前 | 修正後（對 441,103 真實欄位驗證）|
|------|--------|------------------------------|
| Cascade blacklist 命中 HT-DCPHASE | 0（bug）| **804**（含 L1 raw 6 + 衍生 798）|
| Cascade blacklist 命中 CDL | 122（L1 raw 保留）| 122（不變，正確）|
| ADF safe-skip 覆蓋率 | 部分（hyphen 漏失）| **54.7%**（241,082 / 441,103）|
| hyphen 指標（MACD-Line/STOCH-slowk/AROON-aroonup/LINEARREG-ANGLE）| 未命中 | ✅ 全部命中 |

**修正內容**：
- `cascade_blacklist` 預設 `HT_DCPHASE` → `HT-DCPHASE`（config + Pydantic default + scan_config.yaml）
- `adf_safe_skip` whitelist 多組件 pattern 全改 hyphen（MACD-/MACDEXT-/MACDFIX-/HT-/STOCH-/STOCHF-/STOCHRSI-/AROON-/LINEARREG-ANGLE/PLUS-DI/MINUS-DI）；L2 Cross `_Cross_` → `_Cross`（suffix）
- 測試改用**真實 catalog 命名**（187 tests pass），新增 `test_real_catalog_naming_regression` 防再脫節

**bug #2 dead-drop CGSA 支援（行動 #3）已於 2026-05-28 完成**：
- 新增 `dead_column_mask`（numpy 向量化，與 frame-path `find_dead_columns` 標準一致，契約測試鎖定）
- `write_raw_from_registry_stream` 新增 `dead_drop_min_valid` 參數，在 `_write_group`（CGSA 所有特徵流向 parquet 的單一咽喉點）per-column 剔除常數/樣本不足/全 NaN 欄；整組全 dead 時跳過 parquet 但源頭 npy 仍釋放（安全 invariant I-1~I-6）
- `feature_factory.py` 在 registry stream write 傳入 config（enabled=False → None no-op）
- 新增整合測試 `test_cgsa_dead_drop_stream.py`（4 tests，含 CGSA vs frame-path 標準一致契約）；既有 `test_l7_raw_streaming.py` 12 tests 回歸通過
- **下次重跑 ETHUSDT 全開時，CGSA dead-drop 會自動清除常數/樣本不足欄（含 trades 缺失的全 NaN large_trade_ratio 衍生，若 write 時確為全 NaN）**

**仍待辦**：行動 #4（使用者重跑驗證）、行動 #5-part2（前端 warmup 誤判，純顯示層，獨立 issue）。

---

## 10. 結論

- **架構正確、執行有 bug**：三優化的設計方向都對，但「未驗證真實命名」導致 HT_DCPHASE 攔截與部分 ADF skip 失配；「CGSA mode 不走 frame path」導致 dead drop 在生產 0 效果。
- **headline NaN 不變是預期的**：12h warmup 放大的 HIGH_NAN 依設計保留（Plan No-Buffer），優化目標本就不是它。
- **最大收穫**：這次真實 run 比較抓出了單元測試無法發現的命名失配 — 凸顯「測試 fixture 必須來自真實 codebase 而非假設」的教訓。
- **下一步**：修 #1 #2（命名 + 測試），重跑驗證 HT_DCPHASE 歸零；評估 #3（CGSA dead drop）。
