# Run Comparison — NaN 優化修正前 vs 修正後（同 config 對照）

> 日期：2026-05-28（修正後重跑）  
> **修正後 run**：`case_search_api_20260528.log` + `data_cache/features/ETHUSDT/1h/07fb57505d73dab63e7db73242c77c84`  
> **修正前 run**：`case_search_api_20260528old.log` + hash `31d6e92eb5f1de299e03d8ab74dbe693`（即 RUN_COMPARISON_20260528.md 分析的 run）  
> **兩 run config 完全相同**（全開 + IC-First + Fracdiff），唯一差異 = NaN 三優化的 bug 修正（hyphen 命名 + CGSA dead-drop）。這是**乾淨對照**（不像上一份報告有多重 confound）。

---

## 1. TL;DR

修正後三優化**全部生效**，且兩 run config 相同 → 差異可乾淨歸因於修正本身：

| 優化 | 修正前（31d6e）| 修正後（07fb）| 判定 |
|------|----------------|---------------|------|
| Cascade blacklist strip | 61 cols（僅 CDL，HT-DCPHASE 漏）| **64 cols**（CDL + HT-DCPHASE）| ✅ HT-DCPHASE 已納入 |
| HT-DCPHASE 衍生殘留 | 804 | **6**（僅 L1 raw 保留）| ✅ −798 錯誤值欄位 |
| L7 Dead Drop（CGSA）| **0 觸發** | **2,590 cols / 177 groups** | ✅ 修正後首次生效 |
| ADF Safe-Skip 呼叫 | 135 | **421** | ✅ 涵蓋更廣（hyphen 修正）|
| large_trade_ratio 殘留 | 214（全 NaN）| **0** | ✅ dead-drop 從輸出端清除 |
| L6.5 raw-sink 時間 | 1,150.15s | **989.64s** | ✅ −13.9% |
| RSS 峰值 | 2,226 MB | **1,312 MB** | ✅ −41%（部分含 run 變異）|
| 總特徵數 | 441,103 | **437,715** | −3,388 |

**結論：修正完全達到預期。** 三優化在生產（CGSA + IC-First）模式下都實際運作；錯誤值欄位（HT-DCPHASE 衍生）、資料缺失欄位（large_trade_ratio）、死特徵（常數/樣本不足）都被清除；計算更快、記憶體更省。headline high_nan 仍 ~116K（12h warmup，**依設計保留**）。

---

## 2. Pipeline 階段時間（乾淨對照）

| 階段 | 修正前（31d6e）| 修正後（07fb）| 差異 |
|------|----------------|---------------|------|
| L2 derived | 527.81s（46,819 cols）| **513.34s**（46,741 cols）| −2.7% |
| L3 rolling | ~319s（159,069 cols）| **~306s**（158,772 cols）| −4.1% |
| **L6.5 raw-sink** | **1,150.15s** | **989.64s** | **−13.9%** |
| generation_time | 1,072.67s | **1,022.36s** | −4.7% |
| 總 pipeline（L2 起→persist）| ~36m56s（2,216s）| **~33m13s（1,993s）** | −10.1% |

**L6.5 −13.9% 的歸因**（同 config，唯一差異是修正）：
- ADF safe-skip 呼叫 135 → 421（hyphen 修正讓 MACD-Line/STOCH-/AROON-/LINEARREG-ANGLE 等也命中）→ 省下更多 ADF 計算
- Cascade blacklist 修正後在 L6.5 前先剝掉 798 個 HT-DCPHASE 衍生 → L6.5 處理欄位更少

---

## 3. RSS / 記憶體

| 指標 | 修正前 | 修正後 | 差異 |
|------|--------|--------|------|
| L6.5 峰值 RSS | 2,226 MB | **1,312 MB** | −41% |
| raw-sink 完成時 RSS | 948 MB | 1,143 MB | +20%（收尾狀態，非峰值）|
| OOM | 無 | 無 | – |

> ⚠️ RSS 峰值 −41% 部分可歸因於修正（HT-DCPHASE 衍生不進 L6.5 big-group），但 RSS 峰值受機器當下狀態影響，含一定 run-to-run 變異，不宜全數歸因於優化。

---

## 4. 特徵數變化（−3,388 的乾淨拆解）

| 來源 | 減少 | 機制 |
|------|------|------|
| HT-DCPHASE 衍生不再生成 | **−798** | cascade blacklist 修正（hyphen 命名生效）|
| CGSA dead-drop（write 時）| **−2,590** | 常數欄 + 樣本不足欄 + 全 NaN 欄（含 large_trade_ratio 214 + 從未觸發的 CDL + sparse rolling 等）|
| **合計** | **−3,388** | 441,103 → 437,715 |

per-layer（generation 階段，dead-drop 前）：
| Layer | 修正前 | 修正後 | 差異 |
|-------|--------|--------|------|
| L2 | 46,819 | 46,741 | −78 |
| L3 | 159,069 | 158,772 | −297 |
| L4 | 13,000 | 12,976 | −24 |

---

## 5. NaN 比較

| 指標 | 修正前（31d6e）| 修正後（07fb）| 差異 |
|------|----------------|---------------|------|
| total features | 441,103 | 437,715 | −3,388 |
| high_nan | 116,912 | **115,943** | −969 |
| mid_holes | 5,256 | 5,261 | +5（持平）|
| trailing_nans | 724 | 727 | +3（持平）|
| recommended_start_index | 3,265（16.0%）| 3,229（15.9%）| −36 row |

**為何 high_nan 只降 969（而 dead-drop 清了 2,590）？**
- dead-drop 清的 2,590 欄中，只有「sparse（valid<100）+ 全 NaN（large_trade_ratio）」屬於 high_nan 類別 → 這部分 ≈ 969
- 其餘（常數欄、從未觸發的 CDL）本就不是 high_nan（是 CLEAN/constant）→ 移除不影響 high_nan 計數
- **high_nan 主體（~115K）仍是 12h warmup × tf_ratio 放大**，依「不可能三角」**刻意保留（Plan No-Buffer）** → 不該降，降了反而違反設計

→ **high_nan headline 幾乎不動是正確的**；真正該清的（錯誤值 + 資料缺失 + 死特徵）都清掉了。

---

## 6. 殘留檢查（修正前 vs 後）

| 項目 | 修正前 | 修正後 | 說明 |
|------|--------|--------|------|
| HT-DCPHASE 殘留 | 804 | **6** | 6 = L1 raw（3 sources × 2 TF），依設計保留供 IC Gatekeeper；798 個衍生（數學錯誤值）已清 |
| large_trade_ratio 殘留 | 214 | **0** | 全 NaN（trades 缺失）→ dead-drop 全清。等同從輸出端解決 RUN_COMPARISON_20260521 §3.2 |
| CDL 殘留 | 122 | **43** | L1 raw 中「從未觸發」的 CDL（全 0 = 常數）被 dead-drop 清；43 = 實際發生過的 pattern（nunique≥2 保留）。**正確行為** |

---

## 7. 三優化逐項實測（修正後）

| 優化 | log 證據 | 判定 |
|------|---------|------|
| **Step 1 Cascade Blacklist** | `[NaN Blacklist][L2/L3/L4] stripped 64 cols`（CDL + HT-DCPHASE）| ✅ 完整生效 |
| **Step 2 Dead Feature Drop（CGSA）** | `[L7 Dead Drop][CGSA] dropped 2590 cols across 177 groups` | ✅ 修正後首次生效 |
| **Step 3 ADF Safe-Skip** | 421 次呼叫，貢獻 L6.5 −13.9% | ✅ 涵蓋擴大 |

---

## 8. 是否符合預期？

| 維度 | 修正前判定 | 修正後判定 |
|------|-----------|-----------|
| ADF 計算節省 | ✅（未達上限）| ✅ 達標（135→421 次，L6.5 −13.9%）|
| CDL 下游清除 | ✅ | ✅ |
| HT-DCPHASE 下游清除 | ❌ 0 攔（bug）| ✅ **804→6** |
| 死特徵清除 | ❌ CGSA 0 觸發 | ✅ **2,590 清除** |
| 資料缺失欄清除（large_trade_ratio）| ❌ 214 殘留 | ✅ **0** |
| 不誤殺有效特徵 | ✅ | ✅（43 個實際發生的 CDL 保留；good 欄全留）|
| 不以 NaN ratio 丟欄位 | ✅ | ✅ high_nan 主體（warmup）保留 |
| 計算時間 | ✅ | ✅ L6.5 −13.9%、總 −10.1%、RSS −41% |

**總評：完全符合預期（8/8 達標）。** 上一份報告的 2 個未達標項（HT-DCPHASE、死特徵）在修正後都轉為達標，且附帶解決了 large_trade_ratio 資料缺失問題。三優化在生產 CGSA + IC-First + Fracdiff 模式下完整運作。

---

## 9. 與 RUN_COMPARISON_20260528.md 的關係

上一份報告（修正前）的結論是「部分符合預期（4✅/2❌/1半）」並抓出 2 個 bug。本報告（修正後乾淨對照）確認：
- bug #1（hyphen 命名）修正 → HT-DCPHASE 衍生 804→6
- bug #2（dead-drop CGSA 0 觸發）修正 → 2,590 死特徵清除
- 附帶效益：large_trade_ratio 214→0、L6.5 −13.9%、RSS −41%

**關於 mid_holes（5,261）的釐清（2026-05-28 實測更正）**：
- 原本（RUN_COMPARISON_20260521 §3.3）推測是「前端把 warmup 誤判成 mid-hole」。**實測推翻此假設**。
- 後端分類器（`feature_factory_service.py:2451`）公式 `hole_count = nan_total − warmup_len − trailing_len` **已正確扣除 leading warmup**，分類器無 bug、前端無 bug。
- 實測 `taker-ratio_1h_trend_MIDPOINT_89_Skew_W3`：first_valid=101、trailing=43、mid_holes=18,031，中段 NaN 89.2% **散在**（非頭部）。
- **真正根因**：Skew/Kurt 在小窗（W3/W5/W8）對「近常數序列（MIDPOINT 慢變）」或「離散序列（HT-TRENDMODE 0/1）」計算時，視窗 std≈0 → skew/kurt 數學上無定義 → 回傳 NaN，散佈整個有效區。top 20 mid_holes 100% 是此 pattern（Skew/Kurt/ZScore × W3/W5/W8 × MIDPOINT/HT-TRENDMODE/cvar/mdd）。
- **決議（使用者）：維持現狀，不改 code**。這些是合法標註的 MID_HOLE（非 warmup 誤判）；XGBoost 原生處理 NaN，IC Gatekeeper 會因低 IC 自然淘汰。未來若要主動消除，可考慮「常數窗 Skew/Kurt 填 0」或「L3 對小窗/離散指標不算 Skew/Kurt」，但本次不做。

---

## 10. 結論

修正後的乾淨對照證明 NaN 三優化**設計正確且執行到位**：
- **錯誤值欄位**（HT-DCPHASE 衍生）：804 → 6 ✅
- **資料缺失欄位**（large_trade_ratio 全 NaN）：214 → 0 ✅
- **死特徵**（常數/樣本不足）：CGSA dead-drop 清除 2,590 ✅
- **計算效率**：L6.5 −13.9%、總 pipeline −10.1%、RSS 峰值 −41% ✅
- **warmup NaN 主體保留**（Plan No-Buffer）：high_nan ~116K 維持，符合設計 ✅

「headline NaN 不大降」不是失敗，而是設計使然 — 我們從不打算清除 12h warmup（那是合法特徵，XGBoost 原生處理）；我們清的是「計算錯誤 + 資料缺失 + 零資訊」的欄位，這三類修正後都歸零或大幅下降。
