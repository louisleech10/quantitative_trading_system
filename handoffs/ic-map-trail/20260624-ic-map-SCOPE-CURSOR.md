# SCOPE 提案 — Composer (Cursor)

> 依據：codebase 實查（`ic_engine.py`、`event_filter.py`、`ic_filter_orchestrator.py`、`signal_density_analyzer.py`、handoffs 20260624-*）+ 使用者處境 brief。本輪只定目錄與 schema，不寫條目正文。

---

## 1. 分析類型清單（分門別類）

### A. 你在問什麼？— IC 核心變體（「連續 vs 事件」的完整族譜）

| ID | 分析類型 | 白話：回答什麼問題 |
|----|----------|-------------------|
| A1 | **單標的時序 IC（Longitudinal / Continuous IC）** | 這個 symbol 上，特徵值與未來報酬「整段時間」是否一起漲跌？ |
| A2 | **Rolling IC / IC 時間序列** | 預測力是穩定的，還是只在某些時段有效？ |
| A3 | **ICIR（IC ÷ 波動）** | 預測力夠強、且夠穩定到值得用嗎？ |
| A4 | **橫截面 IC（Cross-Sectional Rank IC）** | 同一時刻、跨多 symbol，誰的特徵高誰未來漲得多嗎？（相對排名） |
| A5 | **Pooled / Panel 時序 IC（多 symbol 普適性）** | 把多 symbol 的 bar 或事件堆在一起，這個 pattern 是否「普遍」成立？（你缺的「普適性」） |
| A6 | **事件時點 IC（Event-at-timestamp IC）** | 只在「事件發生當下」的 bar，特徵與報酬有關嗎？ |
| A7 | **Case-Control 事件研究（正/反案例 + 事件前窗）** | 正向事件「發生前」的特徵，能否區分正案例 vs 反案例？（你的主戰場） |
| A8 | **條件 IC（Conditional / Filtered IC）** | 只在特定子樣本（query 條件）裡，預測力還在嗎？ |
| A9 | **Lead-Lag IC** | 特徵要領先報酬幾根 bar 才最有效？（信號提前量） |

### B. IC 動態與衰減

| ID | 分析類型 | 白話 |
|----|----------|------|
| B1 | **IC Decay / 半衰期** | 預測力能撐多久？多久後歸零？ |
| B2 | **IC 自相關 / 持續性** | 今天的 IC 能預測明天的 IC 嗎？（策略持倉週期線索） |
| B3 | **Horizon Sweep（多持有期 IC 曲面）** | 對不同 forward return 窗口，哪個 horizon 最強？ |

### C. 能不能賺錢？— 經濟意義（IC 之外必看的）

| ID | 分析類型 | 白話 |
|----|----------|------|
| C1 | **分位組合報酬 / 單調性（Quantile Monotonicity）** | 特徵越高，報酬是否單調遞增？（可交易性） |
| C2 | **Long-Short Spread** | 做多高分位、做空低分位，價差多少？ |
| C3 | **因子報酬歸因（Factor Return）** | 這個因子本身貢獻了多少超額報酬？ |
| C4 | **換手率（Turnover）** | 信號變化多快？實盤能跟嗎？ |
| C5 | **淨 IC / 成本後 IC（Net IC）** | 扣掉交易成本後，預測力還剩多少？ |
| C6 | **容量 / 擁擠代理（Capacity / Crowding Proxy）** | 很多人用類似信號時，邊際還有嗎？ |

### D. 夠不夠可信？— 統計與多重比較

| ID | 分析類型 | 白話 |
|----|----------|------|
| D1 | **IC 顯著性檢定（t-test / bootstrap CI）** | 這個 IC 是運氣還是統計上顯著？ |
| D2 | **多重比較修正（Bonferroni / FDR）** | 測了 43 萬個特徵，有多少是假陽性？ |
| D3 | **子樣本穩定性（Subsample / Block Bootstrap）** | 換一段時間或換一批 symbol，結果還成立嗎？ |
| D4 | **符號一致性（Cross-Symbol IC Concordance）** | 100 個 symbol 裡，多少比例同方向顯著？ |

### E. 什麼環境下有效？— 分組與 Regime

| ID | 分析類型 | 白話 |
|----|----------|------|
| E1 | **時間分組 IC（年/季）** | 牛市有效、熊市失效？ |
| E2 | **Regime 條件 IC（規則 / K-Means）** | 高波動 vs 低波動，哪種狀態下有效？ |
| E3 | **波動度分位 IC** | 極端波動時預測力是否不同？ |
| E4 | **元數據分組 IC（layer / category / data_source）** | 哪類特徵家族整體更強？ |

### F. 會不會重複？— 因子結構與冗餘

| ID | 分析類型 | 白話 |
|----|----------|------|
| F1 | **相關性冗餘篩選（Greedy / Hierarchical）** | 100 個「好 IC」裡，其實是不是同一個訊號？ |
| F2 | **VIF / 多重共線性** | 回歸視角：特徵是否互相解釋、放大噪音？ |
| F3 | **因子正交化（Orthogonalization）** | 去掉已知因子的影響後，還有獨立 alpha 嗎？ |
| F4 | **因子中心性（Factor Centrality）** | 在因子網路裡，誰是「樞紐」？ |
| F5 | **因子暴露（Factor Exposure）** | 組合對各因子的敏感度是多少？ |
| F6 | **多樣化選取（Diversification Selection）** | 選一組互補、低相關的因子子集 |

### G. 有沒有偷看未來？— 驗證、洩漏、OOS

| ID | 分析類型 | 白話 |
|----|----------|------|
| G1 | **Train / Test 時序切分（IC 主路徑）** | 用過去選特徵、用未來驗證，有沒有偷看？ |
| G2 | **Walk-Forward / Rolling OOS** | 滾動重複「訓練→驗證」，穩定性如何？ |
| G3 | **Purged / Combinatorial Purged CV** | 事件重疊時，CV 有沒有標籤洩漏？ |
| G4 | **PSI / 分布漂移** | 特徵或標籤分布變了，模型還可信嗎？ |
| G5 | **PIT 對齊審計（Point-in-Time）** | 每個 bar 用的特徵，當時真的算得出來嗎？ |
| G6 | **跨標的泛化驗證（Cross-Symbol ML Validation）** | 在 A 幣訓練、B 幣測試，還有效嗎？ |

### H. 非線性與 ML 視角

| ID | 分析類型 | 白話 |
|----|----------|------|
| H1 | **模型驗證 IC（XGBoost / LightGBM AUC 等）** | 線性 IC 看不到的非線性關係存在嗎？ |
| H2 | **SHAP / 特徵重要性** | ML 模型認為哪些特徵真的在驅動預測？ |
| H3 | **學習曲線（Learning Curve）** | 加更多資料，表現還在漲還是已飽和？ |
| H4 | **對抗驗證（Adversarial Validation）** | train/test 分布是否太像（洩漏警訊）或太不像（無法泛化）？ |
| H5 | **機率校準（Calibration）** | 預測機率與實際頻率一致嗎？ |

### I. 多因子組合

| ID | 分析類型 | 白話 |
|----|----------|------|
| I1 | **IC 加權組合** | 多個弱因子合成一個強訊號，怎麼配權？ |
| I2 | **組合層 IC / 組合單調性** | 合成後的訊號，經濟意義還在嗎？ |

### J. 資料與訊號品質診斷（常被忽略）

| ID | 分析類型 | 白話 |
|----|----------|------|
| J1 | **覆蓋率（Coverage）** | 特徵有多少 bar 是 NaN？夠不夠算 IC？ |
| J2 | **常數 / 近常數特徵偵測** | 沒變化的欄位會污染排名與相關矩陣 |
| J3 | **NaN / Inf / float16 Gate** | 髒資料有沒有被擋在計算外？ |
| J4 | **訊號密度（Signal Density）** | 事件前後，pattern 在時間上多「密」？（`signal_density_analyzer` 路徑，與 IC 不同域） |
| J5 | **前處理影響審計（Winsor / Z-score）** | 標準化是否用未來資訊？跨欄操作是否破壞 streaming？ |

### K. 參數與敏感度（泛用平台應有）

| ID | 分析類型 | 白話 |
|----|----------|------|
| K1 | **參數敏感度（Parameter Sensitivity）** | 窗口長度、閾值改一點，IC 還穩嗎？ |
| K2 | **趨勢分析（Trend over Rolling Windows）** | IC 是在變強還是變弱？ |

### L. 我補充、業界常做但使用者可能不知道的

| ID | 分析類型 | 白話 |
|----|----------|------|
| L1 | **事件研究對照設計（Matched Control / 配對反案例）** | 反案例要與正案例「可比」（同波動、同 regime），否則假陽性 |
| L2 | **事件前窗對齊（Pre-Event Window Alignment）** | 每個事件取「發生前 N 根 bar」對齊，而非事件當根 |
| L3 | **標籤構造審計（Forward Return / Label Leakage）** | 你的 label 有沒有含當根或事件內資訊？ |
| L4 | **Selection Window / 樣本期限制** | 只用研究期內資料，排除上市初期或資料空洞 |
| L5 | **Deflated / Haircut Significance** | 試了很多特徵後，對「最佳 IC」做折扣顯著性 |
| L6 | **Rank 自相關（Signal Autocorrelation）** | 預測換手前的先行指標 |
| L7 | **Batch / Multi-Symbol 編排與 Resume** | 100 symbol 跑不完怎麼斷點續跑、怎麼隔離 cache？ |

**合計：約 50 條**（地圖可再拆細，但不建議再粗併）。

---

## 2. 每條目的內容 Schema

建議每條固定 **12 欄 + 3 個機器可掃標籤**：

### 必填欄位（教學 + 決策）

| # | 欄位 | 用途 |
|---|------|------|
| 1 | **`id`** | 如 `A7`，穩定錨點 |
| 2 | **`name_zh` / `name_en`** | 雙語名，非量化看中文 |
| 3 | **`one_liner`** | ≤20 字：這是在問什麼 |
| 4 | **`when_to_use`** | 什麼研究情境該用；與易混淆類型的差異（例：A6 vs A7） |
| 5 | **`input_shape`** | 資料形狀：`T×C` 單 symbol / `T×N×C` panel / 事件清單 `(symbol, ts, label)` / 截面 `T×N` |
| 6 | **`industry_standard`** | 業界典型做法（方法、指標、常見門檻**須標來源或「慣例」**） |
| 7 | **`platform_status`** | 見下方枚舉 |
| 8 | **`platform_modules`** | 對應模組路徑（如 `ic_engine.compute_ic_decay`） |
| 9 | **`correctness_gaps`** | 做對沒、已知漏洞（契約不一致、幽靈參數、無 train/test…） |
| 10 | **`scale_430k_notes`** | 430K 欄 × 20K 列 / 100 symbol 下：串流、分塊、候選集 gate、禁止物化什麼 |
| 11 | **`pit_leakage_checklist`** | PIT / 洩漏檢查項（逐條 checkbox 語意） |
| 12 | **`user_battlefield_priority`** | `P0` / `P1` / `P2` / `N/A`（相對你的 case-control 主戰場） |

### 機器可掃標籤（供篩選與 reconcile）

| 標籤 | 值域 |
|------|------|
| **`status`** | `implemented` / `partial` / `broken` / `missing` / `wrong_domain`（有程式但在別條產品路徑，如 signal_density） |
| **`data_shape_tag`** | `longitudinal` / `cross_sectional` / `panel` / `event_list` / `case_control` |
| **`pipeline_stage`** | `ingest` / `preprocess` / `label` / `filter` / `ic_core` / `stats` / `economic` / `structure` / `validation` / `ml` / `report` |

### 可選欄（第二輪地圖再填）

- `confused_with`：易混淆條目 ID 列表  
- `golden_test_ref`：對應測試/fixture  
- `ui_surface`：前端是否暴露、哪個 panel  
- `depends_on`：前置分析類型（例：A7 依賴 L2）  

---

## 3. 地圖組織方式

**建議：雙軸，主軸給人看、副軸給工程 reconcile。**

### 主軸（非量化使用者）— 按「研究問題」分 5 章 + 1 附錄

1. **「這個訊號有沒有預測力？」** → A 類 + B 類  
2. **「能不能變成可交易策略？」** → C 類  
3. **「結果可信嗎、會不會是運氣？」** → D 類 + G 類  
4. **「什麼時候有效、跟誰重複？」** → E 類 + F 類  
5. **「多因子 / ML 怎麼接？」** → H 類 + I 類  
6. **附錄：資料品質與平台營運** → J 類 + K 類 + L 類  

每章開頭一張 **「決策樹」**（3–5 個問題導到條目 ID），例如：  
「你有明確事件清單嗎？」→ 是 →「有正反標籤嗎？」→ 是 → **A7**；否 → **A6**；否 →「多 symbol 嗎？」→ 是 → **A4 或 A5**。

### 副軸（工程 / 委員會）— 三張索引表

- **按 `data_shape_tag`**：快速看 panel / case-control 缺口  
- **按 `platform_status`**：修復 backlog  
- **按 `pipeline_stage`**：對齊八階段管線 Stage 0–8  

### 排序原則

1. 章內：**`user_battlefield_priority` P0 置頂**  
2. 同優先級：**主戰場路徑順序**（事件清單 → 前窗對齊 → case-control IC → pooled 普適性 → train/test）  
3. 其餘：按決策樹出現順序，非字母序  

---

## 4. 優先級與現況標記

圖例：`🔴主戰場必補` `🟠現有但壞/半成品` `⚫完全缺` `🟢可用(有 caveats)` `🔵別域有、IC 未接`

### 🔴 主戰場（Case-Control）必須優先補強

| ID | 說明 |
|----|------|
| **A7** | Case-Control 事件研究：無顯式 `(symbol, ts, case_label)` 輸入、無正/反對照 IC |
| **L1** | 配對反案例設計 |
| **L2** | 事件前窗對齊（非僅 `event_filter` 當根篩選） |
| **A5** | Pooled/Panel 多 symbol 普適性 IC |
| **D4** | 跨 100 symbol 一致性彙總 |
| **G1** | IC 主路徑 train/test 切分（`time_splitter` 存在但未進主 analyze） |
| **G3** | 事件重疊時的 Purged CV（事件研究必備） |
| **L3** | 標籤構造洩漏審計（事件前 pattern 研究極易踩雷） |

### 🟠 現有但壞掉 / 半成品

| ID | 證據摘要 |
|----|----------|
| **B1 IC Decay** | 45K 特徵熱迴圈 + 1.4 萬條 log；大 run 不可用 |
| **E1/E2/E3/E4 Grouped IC** | `GroupedConfig` vs `dict` 契約 → 崩潰；`by_volatility` schema 漂移 |
| **A4 Cross-Sectional** | 後端有 `analyze_cross_sectional`，但 `pd.concat` 多 symbol → OOM；>50 symbol policy 半成品 |
| **A8 Event Query** | `event_filter` 僅 query/timestamps，**不是** case-control |
| **F1–F6 冗餘/結構** | Stage 7 有；**`feature_filter` 幽靈參數**（前端送、後端不生效）→ 假過濾真全量 |
| **G2 Rolling OOS** | Deep analysis 模組有，**非主路徑預設** |
| **J5 前處理審計** | 全矩陣 preprocess 與 streaming 衝突未分類 |
| **L7 Batch 編排** | 100 symbol resume / cache 隔離在優化 epic 中未落地 |

### ⚫ 完全缺（IC Gatekeeper 主路徑）

| ID | 說明 |
|----|------|
| **A5** | Panel pooled IC |
| **A7, L1, L2** | 顯式 case-control 管線 |
| **A9 Lead-Lag IC** | 無系統化 horizon offset sweep |
| **G1** | 主 analyze 無 train/test |
| **G5** | 無一鍵 PIT 審計報告 |
| **L5 Deflated significance** | 無 |
| **I1/I2** | 多因子組合層分析未產品化 |

### 🟢 可用（有 caveats）

| ID | Caveat |
|----|--------|
| **A1–A3** | 單 symbol 連續 IC / Rolling / ICIR 主路徑可用；430K 需 streaming epic |
| **C1–C2** | Monotonicity stage 6 |
| **D1–D2** | Statistical validator + FDR |
| **C4, C5** | Turnover / Net IC（deep analysis） |
| **F1** | Redundancy filter（在倖存者子集上） |
| **H1–H5** | Deep analysis 可選模組 |
| **J1–J3** | Coverage / 常數移除 / quality gates |

### 🔵 別域已有、IC 未整合（地圖要標「wrong_domain」免假綠）

| ID | 位置 |
|----|------|
| **J4 Signal Density** | `signal_density_analyzer.py`：已有 positive/negative case、`tc_timestamp` 前窗 — **屬 pattern/case search，非 IC analyze** |
| **G6 Cross-Symbol ML** | `cross_symbol_validator.py` — ML 驗證，非 IC 引擎 |
| **G3 Purged CV** | `combinatorial_purged_cv` factory 存在，未接 IC UI |

---

## 附：與「只知道連續 IC / 事件 IC」的對照（給另三家詰問用）

| 使用者以為 | 實際缺的是 |
|------------|------------|
| 「事件 IC」 | 多半是 **A6（當根）** 或 **A8（query）**；主戰場要的是 **A7 + L2 + L1** |
| 「連續 IC」 | 只有 **A1 單標的**；100 symbol 普適性是 **A5 + D4**，不是多跑 100 次 A1 |
| 「IC 高就好」 | 還需 **C1/C4/C5（可交易）**、**D2（多重比較）**、**G1（OOS）** |
| 「跨 symbol」 | **A4（截面）≠ A5（panel 普適性）**；前者「同時刻排名」，後者「堆疊驗證共通 pattern」 |

---

**HANDOFF_NOT_UPDATED**: READ-ONLY 諮詢任務，依合約不覆寫根 `HANDOFF.md`。
