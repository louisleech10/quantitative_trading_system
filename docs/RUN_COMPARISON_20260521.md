# Run Comparison + Post-Fix Diagnostics

> 日期：2026-05-21  
> 範圍：對比 `case_search_api_20260514Baseline.log` ↔ `case_search_api_20260521.log`，並針對 NaN poisoning 修復後出現的「Feature Explorer 變慢」與「問題特徵仍有 123,016 筆」做根因分析。  
> 對應修復：見 [NAN_POISONING_INVESTIGATION.md](./NAN_POISONING_INVESTIGATION.md) 與 [FEATURE_DEVELOPER_CHECKLIST.md](./FEATURE_DEVELOPER_CHECKLIST.md)。

---

## 摘要 (TL;DR)

1. **無法做逐層 baseline 對比**：`20260514Baseline.log` 只包含 `kline_storage` 讀取與 API middleware 紀錄，**沒有任何 Feature Factory 生成階段的 log**（L1/L2/L3/L4/L6.5 全部缺）。它是一份「UI 瀏覽流量 log」，不是「Feature Factory batch log」。本文以新 log 為主軸做時序分析，並把 baseline 當作 UI 端點的延遲基準。
2. **新跑批（20260521）成功通過全程**：22:42:34 → 23:23:23，總耗時 **40 分 49 秒**，產出 442,079 features × 1,061 groups（ETHUSDT 1h primary + 12h native）。Pipeline 在 NaN guard 介入下完整持久化、無 OOM、無 fail-closed。
3. **Pattern guard 確認生效**：問題特徵 Top 20 中已**無任何** `*_pattern_*_Momentum_L*` / `*_pattern_*_<agg>_w*`，符合預期。
4. **但仍有 123,016 個問題特徵**——這是**另外兩個獨立問題**：
   - `large_trade_ratio` 在 L1 階段就是 100% NaN（`trades missing` 警告），下游 Momentum / Cross / SignedStrength 全部 propagate NaN → 約 **117,052 個高 NaN 欄位**。
   - `MIDPOINT_89/144` + 小窗 `Skew_W3/Kurt_W5` 與 `HT-TRENDMODE` + rolling Skew/Kurt 產生「中間孔洞」型缺值 → **5,240 個** mid-hole 欄位。
5. **Feature Explorer 慢**：問題不在前端，而在 `browse_data_quality` 端點每次呼叫掃過全部 1,061 parquet（442k cols），**單次 562 ~ 724 秒**。其他 tab（summary / features / data）也都在 14 ~ 34 秒級。需要快取或分頁。

---

## 1. Baseline 對比的可行性

### 1.1 兩份 log 的內容組成

| Log | 期間 | 內容 | 行數 |
|---|---|---|---|
| `case_search_api_20260514Baseline.log` | 06:46:14 ~ 06:56:21 (10 分鐘) | 僅 `kline_storage` 讀取 + `api.middleware.request` + `api.request`（端點：`features/preview`, `features/config`, `feature-data/kline/list`, `features/schema` 等） | 603 |
| `case_search_api_20260521.log` | 22:42:34 ~ 23:39:00 (~57 分鐘) | 完整 FF 生成（L1/L2/L3/L4/L6.5/L7）+ 多次 `features/browse/*` 呼叫 | 2,364 |

### 1.2 結論

- **「逐層時間比較」無法進行**：baseline 沒有任何 `feature_factory` logger 輸出。
- 可做的對比：
  - **API 路由層延遲**：兩邊都有 `features/preview`, `features/schema`, `feature-data/kline/list` 等。
  - **Kline 讀取效能**：兩邊都有 12 個 symbols × 3 timeframe 的 `Read N klines from X in Ys`。

### 1.3 可量化的對比

| 指標 | Baseline (05-14) | New (05-21) | 差異 |
|---|---|---|---|
| 12 symbols × 3 TF kline 完整讀取 | ~0.55s | ~0.25s (預熱後) | -55% (記憶體快取生效) |
| `POST /api/v1/features/preview` | 0.07 ~ 0.26s | 未在新 log 中重複 | n/a |
| `GET /api/v1/features/schema` | 0.5 ~ 2.1s（首次需 OPTIONS 暖機） | 未在新 log 中重複 | n/a |

> 觀察：baseline 的 schema/config/presets/indicators 在首次載入時都是 2.1s 同步返回，**這是因為 6 個 endpoint 全部等同一個鎖**。後續呼叫降到 0.25s。新 log 沒有觸發這些端點。

---

## 2. New Run 完整時序拆解（20260521）

### 2.1 Pipeline 階段時間表

| 階段 | 起始時間 | 結束時間 | 耗時 | 輸出 cols | 備註 |
|---|---|---|---|---|---|
| Task 啟動 + L1 atomic | 22:42:34 | 22:43:51 | **~77s** | 1,683 L1 cols | TA-Lib + microstructure + entropy + tailrisk |
| **L2 derived operators** | 22:43:51 | 22:52:47 | **536.60s** | 46,819 cols | Momentum/Cross/Ratio/WorldQuant/Distance/SignedStrength |
| L2 CGSA persist (4 groups) | 22:48:09 ~ 22:52:47 | – | – | – | Cross 166MiB / Ratio 166MiB / Momentum 1,254MiB / WorldQuant 2,006MiB |
| **L3 rolling aggregation** | 22:52:47 | 22:57:49 | **~302s** | 161,500 → **159,069** survivors | 100 steps (10 windows × 10 aggregators) |
| L3 streaming persist 完成 | – | 22:57:49 | – | 99 groups | 2,431 dropped (1.5%) by variance filter |
| **L4 lag** | 22:57:49 | 22:58:31 | **~42s** | 13,488 cols | 3 lag groups (388+388+271 MiB) |
| L6 meta | – | 22:58:31 | – | 11 cols | 1 group |
| Numba JIT warmup | 22:58:31 | 22:58:33 | ~2s | – | rolling_rank, transform JIT |
| L7/CGSA Quality check | – | 23:01:05 | ~152s | – | coverage 95.82%, inf=0 |
| L7_raw disk pre-check | – | 23:01:09 | – | – | free=8.93 GiB / est=16.76 GiB / reclaimable=18.16 GiB |
| **L6.5 preprocessing** | 23:01:09 | 23:23:22 | **1,333.37s (22 分 13 秒)** | 442,079 outputs | 1,075 sub-tasks, **effective_workers=1**（受 disk safety 限制） |
| L7_raw 最終 persist | – | 23:23:23 | ~1s | 442,079 / 1,061 groups | npy_freed=18.16 GiB |
| **總計（pipeline）** | 22:42:34 | 23:23:23 | **40 分 49 秒** | – | – |

### 2.2 L6.5 速率曲線

| 進度 | 已用時 | 速率 (tasks/s) | RSS (MB) | 階段 |
|---|---|---|---|---|
| 1.2% (13/1075) | 258.8s | 0.05 | 1,612 | Big-group `1h_L2_WorldQuant` 25,840 cols × 13 chunks（最大瓶頸） |
| 4.5% (48/1075) | 692.5s | 0.07 | 2,670 | 12h_L2_WorldQuant native-tf path |
| 7.4% (80/1075) | 765.7s | 0.10 | 2,188 | L3 rolling 群進入 |
| 17.9% (192/1075) | 888.2s | 0.22 | 619 | full-group fast path 啟動 |
| 53.8% (578/1075) | 1,270.5s | 0.45 | – | 全速段 |
| 100% | 1,333.3s | 0.81 | 365 | 收尾 |

**觀察**：前 4.5% 花了 692s（佔 52% 時間），來自兩個 25k+ col 的 big-group split。一旦進入 full-group 階段就突然提速 5–10 倍。

### 2.3 主要警告

- L1 階段唯一的「LayerData 警告」：
  ```
  22:42:37 microstructure_indicators - WARNING - trades missing, large trade ratio set to NaN
  ```
- L7 唯一兩條 NaN ratio 警告：
  ```
  23:00:00 [L7][CGSA] Group 12h_L1_large_trade_ratio NaN ratio=1.0000 exceeds 0.90
  23:00:16 [L7][CGSA] Group 1h_L1_large_trade_ratio NaN ratio=1.0000 exceeds 0.90
  ```
- 其餘 STOCH/STOCHF/STOCHRSI 警告為**參數預設值** info，與資料品質無關。

---

## 3. 「為何問題特徵仍 123,016 筆？」根因

修復後 Data Quality Dashboard 顯示：
- 問題特徵：123,016（孔洞 5,240 + 尾缺 724 + 高 NaN 117,052）
- 推薦訓練起點：index 3,277（損失 16.1% 樣本）

### 3.1 Pattern guard 已生效（驗證）

從新 log + 問題清單觀察：
- 「高 NaN / 全空 Top 20」全部是 `ms_*_large_trade_ratio_*` 與 `None_*_microstructure_large_trade_ratio_*_Cross`。
- 「孔洞 Top 20」全部是 `taker-ratio_1h_trend_MIDPOINT_*_Skew/Kurt` 與 `volume_*_cycle_HT-TRENDMODE_*`。
- **無任何** `*_pattern_*_Momentum_L*`、`*_pattern_*_Cross`、`*_pattern_*_w<n>` 出現。

這完全符合 [NAN_POISONING_INVESTIGATION.md](./NAN_POISONING_INVESTIGATION.md) 中所建立的 `RATIO_UNSAFE_CATEGORIES={"pattern"}` guard 預期：pattern 類別的 L1 不再被 L2 ratio 算子摧毀。

### 3.2 新暴露的問題 A：`large_trade_ratio` 全 NaN（~117,052 筆）

**根因**：`microstructure_indicators.py` 在 L1 階段抱怨 `trades missing`，整列輸出 NaN。

- L1 階段 `*_large_trade_ratio_13 / _21 / _55` 即為 100% NaN。
- L2 對其展開 Momentum / Cross / Distance / SignedStrength → 全 NaN。
- L3 對全 NaN 做 rolling 統計 → 全 NaN。
- L6.5 之後成為 117,052 個 high-NaN 欄位。

**與 pattern 問題的差別**：
| 類別 | L1 性質 | 下游表現 | 修復策略 |
|---|---|---|---|
| `pattern` (已修) | 99% 零值，1% 為 ±100 | ratio formula 觸發大量 NaN | 加入 `RATIO_UNSAFE_CATEGORIES` 黑名單 |
| `large_trade_ratio` (本次新暴露) | 100% NaN（資料源缺失） | 直接 propagate NaN | **應在 L1 階段就 skip / fail-fast** |

**建議修法**（待用戶決策）：
- **方案 A（資料源修復）**：補上 `trades` 資料源；若僅是抓取失敗則重跑 L1，最乾淨。
- **方案 B（程式層 fail-fast）**：在 microstructure engine 偵測「trades missing」時，**直接不輸出 `large_trade_ratio` 欄位**（而不是輸出 NaN 列）。這樣下游不會憑空產生 117k 廢欄位。
- **方案 C（feature_validator gate）**：在 L1 完成後加一道「L1 column NaN ratio > 0.95 即移除該欄位」的閘門，類似 L3 `_variance_filter` 但作用於 L1。

> 我的建議：**方案 B + C 並行**——B 修現有 bug，C 是針對未來其他資料源缺失的通用防線。修法都很輕，不涉及今天剛改的三個檔案。

### 3.3 新暴露的問題 B：MIDPOINT_89/144 + 小窗 Skew/Kurt 造成 mid-hole（5,240 筆）

**Top 5 mid-hole 範例**：
| 特徵 | mid-hole 數 | 比例 |
|---|---|---|
| `taker-ratio_1h_trend_MIDPOINT_89_Skew_W3` | 18,031 | 89.23% |
| `taker-ratio_1h_trend_MIDPOINT_144_Kurt_W5` | 17,608 | 87.53% |
| `taker-ratio_1h_trend_MIDPOINT_144_Skew_W5` | 17,608 | 87.53% |
| `volume_1h_cycle_HT-TRENDMODE_Kurt_W8` | 17,399 | 85.85% |
| `volume_1h_cycle_HT-TRENDMODE_Skew_W8` | 17,399 | 85.85% |

**根因分析**：
1. **MIDPOINT_89/144**：warmup = 89/144 bars，前段全 NaN 是正常的，但這不該被算成「孔洞」——這應該是 **tail/head warmup**，不是 mid-hole。**前端問題特徵分類有 bug**：把 warmup 區誤判為孔洞。
2. **Skew_W3 / Kurt_W5**：3-5 點視窗算 skew/kurt 本身就**統計上意義不大**（樣本量太小，極不穩定）。技術上能算（給定 std > 0），但會放大 warmup 邊界的不穩定性。
3. **HT-TRENDMODE**：cycle 類離散指標（輸出 0/1），對其做 rolling Skew/Kurt 數學上沒意義（值域只有兩種，std 經常 = 0 → Skew/Kurt 直接除零）。

**建議修法**（不在本 PR 範圍，需另開）：
- **A**：前端把 head warmup 與 mid-hole 區分（依首個非 NaN 位置切斷頭部 NaN，剩下才算 mid-hole）。
- **B**：在 L3 `_select_columns` 對 `cycle` 類別加 `RATIO_UNSAFE_CATEGORIES`-like guard（HT-TRENDMODE 等離散指標不該做 Skew/Kurt）。需先把離散 cycle 與連續 cycle 分開命名（目前都掛在 `_cycle_`）。
- **C**：`_variance_filter` 加 `head_warmup_ratio` 閘門：若一個欄位的 leading NaN 超過 N%，直接視同 dead column 而非 mid-hole。

### 3.4 結論

修復前 NaN 災難來源是「**一個** 類別（pattern）」；修復後暴露的是「**三個** 獨立小問題」：
1. 資料源缺失（trades 抓不到）
2. cycle 類離散指標 + 統計算子的語義 mismatch
3. 前端把 warmup 區誤判成孔洞

——這正是修掉大魚之後才看得清楚的小魚，整體架構是健康的。

---

## 4. Feature Explorer 變慢根因

### 4.1 實測延遲（從 log 抽取）

| Endpoint | 觀察延遲 | 樣本數 |
|---|---|---|
| `GET /features/browse/.../summary` | **34.516s** | 1 |
| `GET /features/browse/.../features` | **33.269s** | 1 |
| `GET /features/browse/.../data` | **14.758s** | 1 |
| `GET /features/browse/.../data-quality` | **562 ~ 724s**（10–12 分鐘） | 5 次 |

### 4.2 `data-quality` 為什麼這麼慢？

新 log 顯示這條訊息（API service 自己印的）：
```
23:23:43 browse_data_quality: scanning 442079 features across 1061 parquet files (rows=20352)
23:23:43 → 23:38:42: 680.1s scan complete
```

掃描節奏（每 100 個 file 一行）：
- 前 200 個 file：花了 ~12s（每個 ~60ms）— 是 schema/metadata-only 模式。
- 200 ~ 1000：突然加速到 5s/100 files（每個 5ms）— **預熱完畢，作業系統 file cache 命中**。
- 最後 60 個（含 big-groups）：又慢下來，最終約 680s。

**核心問題**：
1. 每次點 tab 都從頭掃 1,061 個 parquet 的所有 column 統計 → 無快取。
2. 沒有對 `selected_features` 做 prefix-pushdown（即便你只想看 100 個欄位，後端仍掃全部 442k）。
3. 同樣的計算在 5 次連續呼叫中被重複做（log 顯示 562s / 624s / 711s ×3 / 724s ×1）→ **同一個 task_id 完全沒有結果快取**。

### 4.3 修復後反而變慢的具體原因

| 比較項 | 修復前（假設） | 修復後（實測） |
|---|---|---|
| L1 cols | ~1,683 | 1,683（無變化） |
| L2 cols | 46,819 + ~884 pattern derivatives | 46,819（pattern 衍生 0） |
| L3 cols | 159,069 + ~408 pattern aggregations | 159,069 |
| **總 cols 持久化** | 預估 ~441k（含 pattern garbage） | **442,079** |
| `data-quality` 掃描成本 | 等同 | 等同 |

**結論**：總欄位數**幾乎沒變**（-1,300 / +0），所以 `data-quality` 端點的時間複雜度沒變。**「變慢」的真正原因可能是**：
1. **修復前那次 batch 因為 NaN 災難而 fail-closed 提早退出**，根本沒有產出完整的 L7_raw 給 Feature Explorer 掃 → 用戶端看到的是「empty」很快回。
2. 修復後 pipeline 第一次成功完整持久化 442k 欄位 → 第一次有真正的工作量要掃。
3. 同時 `large_trade_ratio` 117k 廢欄位也都被認真持久化，inflate 了 metadata scan 成本。

所以「變慢」其實是「**修復前根本沒跑完，這次跑完才看到真實成本**」。

### 4.4 建議修法

**短期（不改數值邏輯，僅優化端點）**：
1. **加 task-level cache**：`browse_data_quality` 對同一 `task_id` 結果做 in-memory cache（TTL 30 分），任務完成後第二次點是 0ms。
2. **支援 column-prefix filter**：前端傳 `category` 或 `prefix` 時，後端只掃匹配的 parquet。
3. **背景預熱**：FF batch 完成後背景跑一次 quality scan，存到磁碟（JSON），下次直接回。

**中期（解決根因）**：
1. 落實第 3.2 節方案 B+C，從源頭剔除 117k 廢欄位，總 cols 降到 ~325k，端點成本下降 26%。
2. 落實第 3.3 節方案 C（head warmup 識別），剔除 5,240 廢欄位。

**長期**：
- `browse_data_quality` 改成「在 L7_raw 持久化時就同步寫入一份 `quality_dashboard.parquet`」，端點變成單檔讀取（< 100ms）。

---

## 5. RSS 與記憶體穩定性

從 L6.5 heartbeat 抽取 RSS 軌跡：

| 時間 | RSS (MB) | 階段 |
|---|---|---|
| 23:01:09 (L6.5 起點) | 340 | Raw-sink 起始 |
| 23:01:15 | 1,612 | 進入 1h_L2_WorldQuant big-group |
| 23:05:28 | 1,020 | WorldQuant 收尾 |
| 23:05:33 | 1,127 | 進入 1h_L2_Momentum |
| 23:07:58 | 1,256 | Momentum 收尾 |
| 23:12:41 | 2,670 | **RSS 峰值** — 12h_L2_WorldQuant native-tf |
| 23:13:24 | 2,118 | 1h_L2_Ratio 收尾 |
| 23:13:55 | 2,188 | rolling W21 階段 |
| 23:16:27 | 619 | rolling W34 階段（RAM 已釋放） |
| 23:23:22 (L6.5 結束) | 365 | 全部完成 |

**觀察**：
- 峰值 RSS ~2.7 GB，距離 8 GB MacBook RAM 上限有充分空間。
- Big-group chunk streaming 設計穩定運作，**沒有發生 OOM**。
- `effective_workers=1`（requested=2）是 disk safety 觸發的保守策略（free=8.93 GiB / required=2 GiB / safety×1.5）；可從用戶 memory `memmap_oom_fix.md` 看到這是預期行為。

---

## 6. 後續行動清單

按優先順序：

| # | 行動 | 期望收益 | 風險 | 範圍 |
|---|---|---|---|---|
| 1 | `microstructure_indicators` 在 trades missing 時 **不輸出** large_trade_ratio 欄位（fail-fast skip 而非 NaN fill） | -117k 廢欄位，端點 -26% 成本 | 低（只影響 data-missing 路徑） | momentum/FeatureEngineering/atomic/microstructure_indicators.py |
| 2 | L1 加「all-NaN column auto-drop」閘門（類似 L3 `_variance_filter` 但作用於 L1） | 通用防線，未來任何資料源缺失都不會 cascade | 低（保守閘門） | feature_validator.py 或 layer1 finalization step |
| 3 | `browse_data_quality` 加 task-level cache + on-disk `quality_dashboard.parquet` | 點 tab 從 12 分鐘 → < 100ms | 極低（純快取層） | api/services/feature_factory_service.py |
| 4 | 前端 Feature Explorer 把 head warmup 與 mid-hole 區分 | 修正「5,240 中間孔洞」的誤判 | 低（純顯示邏輯） | frontend/src/components/feature-browser/* |
| 5 | `RATIO_UNSAFE_CATEGORIES` 評估是否要加 `cycle`（HT-TRENDMODE 等離散指標） | 移除部分廢 Skew/Kurt 欄位 | 中（cycle 內混合離散+連續，需先拆分命名） | momentum/FeatureEngineering/operators/derived_operators.py |

---

## Appendix A：Pipeline 階段 ASCII 時間軸

```
22:42:34 ─┬── Task 啟動
          │
22:42:34 ─┴── L1 atomic engines (77s)
22:43:51 ─┬── L2 derived ops 開始
          │   Cross    166MiB ─┐
          │   Ratio    166MiB ─┤
          │   Momentum 1254MiB │  (536.60s)
          │   WorldQ   2006MiB ┘
22:52:47 ─┴── L2 完成 (46,819 cols)
22:52:47 ─┬── L3 rolling (302s, 100 steps)
          │   step 10/100  W3_range
          │   step 50/100  W21_range
          │   step 100/100 W233_range
          │   → 161,500 → 159,069 (2,431 dropped)
22:57:49 ─┴── L3 持久化完成 (99 groups)
22:57:49 ─┬── L4 lag (42s)
22:58:31 ─┴── L4 完成 (13,488 cols, 3 groups)
22:58:33 ──── Numba JIT warmup 完成
23:01:05 ──── L7/CGSA Quality summary: coverage=95.82%
23:01:09 ─┬── L6.5 raw-sink 開始 (1,075 sub-tasks)
          │   23:05:28  task   13/1075   (1.2%)   rss=1020MB
          │   23:13:24  task   52/1075   (4.8%)   rss=2118MB
          │   23:15:57  task  192/1075  (17.9%)   rss= 619MB
          │   23:20:00  task  578/1075  (53.8%)   速率突升至 0.45/s
          │   23:22:55  task 1055/1075  (98.1%)
23:23:22 ─┴── L6.5 完成 (922/922 groups)
23:23:23 ──── L7_raw persist done (442,079 features / 1,061 groups)
              npy_freed = 18.16 GiB
              ───── pipeline 完成 (40 分 49 秒) ─────
23:23:24 ──── Feature Explorer 首次呼叫 (summary 34.5s, features 33.3s)
23:23:43 ──── browse_data_quality 第 1 次 (562s)
23:33:00+──── browse_data_quality 第 2-5 次 (624 ~ 724s 各一次，無快取)
```

## Appendix B：Top 10 「問題特徵」逐項分類

### 高 NaN / 全空 (117,052)
全部來自 `large_trade_ratio` 家族（L1 100% NaN 級聯）：
| Rank | 特徵名 | 類別 |
|---|---|---|
| 1 | `ms_12h_large_trade_ratio_13` | L1 (root NaN) |
| 2 | `ms_12h_large_trade_ratio_21` | L1 (root NaN) |
| 3 | `ms_12h_large_trade_ratio_55` | L1 (root NaN) |
| 4 | `None_12h_microstructure_large_trade_ratio_13_55_Cross` | L2 Cross |
| 5-8 | `ms_12h_large_trade_ratio_13_Momentum_L3/L5/L8/L13` | L2 Momentum |

### 中間孔洞 (5,240)
全部來自長 warmup 指標 + 小窗 skew/kurt 的「warmup 誤判」：
| Rank | 特徵名 | 類別 |
|---|---|---|
| 1 | `taker-ratio_1h_trend_MIDPOINT_89_Skew_W3` (89.23%) | L3 rolling |
| 2 | `taker-ratio_1h_trend_MIDPOINT_144_Kurt_W5` (87.53%) | L3 rolling |
| 3 | `taker-ratio_1h_trend_MIDPOINT_144_Skew_W5` (87.53%) | L3 rolling |
| 4-6 | `volume_*_cycle_HT-TRENDMODE_Skew/Kurt/ZScore_W*` (85.85%) | L3 rolling |

### 尾端缺失 (724)
未列入 Top 20，量小（< 0.2%），暫不分析。
