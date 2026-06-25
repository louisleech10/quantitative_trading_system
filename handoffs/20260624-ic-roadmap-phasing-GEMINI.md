使用者可稽核：cat .claude/gate/audit.log
作為量化規劃委員會，我們已審閱 Claude 提出的「IC 地圖修法分階段執行計畫」。

這是一份工程邏輯清晰的草案，但從**量化研究的嚴謹性與 Alpha 發現的真實流程**來看，我們需要進行一些關鍵挑戰與重排。

---

### [決策] 對 §0 核心排序的表態

**強烈同意你的主張：「正確性先修（小尺度）」，絕對優先於「大尺度架構」。**

在量化領域有一條鐵律：**「快速算出錯誤的結果（假 Alpha），比慢速算出正確的結果更具毀滅性。」** 
如果沒有 Train/Test 切分、沒有 FDR 校正，系統一上線 430K 串流，只會變成一台「超高效率的過擬合垃圾製造機」，誤導使用者投入真金白銀。

**回答你的疑問：正確性方法在串流重寫後會白做嗎？**
**不會。** 
1. Train/Val/Test 切分本質上是 index/timestamp 遮罩，這在串流讀取資料時直接當作 filter 條件即可。
2. FDR (Benjamini-Hochberg) 是對最終產出的 p-value 陣列做後處理（Post-processing），與特徵矩陣是如何串流計算的完全無關。
3. HAC/Block Bootstrap 是統計公式的定義。在記憶體內先實作，反而能為未來的串流重寫提供**「Ground Truth（黃金標準）」**。未來寫 Streaming 演算法時，直接拿小尺度的記憶體算法結果做單元測試（Assert Almost Equal），這在工程上是不可或缺的防線。

---

### [挑戰 2] 主戰場（事件 Case-Control） vs 大尺度（430K 串流）誰先？

**從量化研究價值排序：Phase 2 (主戰場事件) 優先於 Phase 3 (大尺度 430K)。**

**理由：**
1. **資料量自然縮減（天然避開效能瓶頸）：** Event-driven / Case-Control 研究（例如觀察大額爆倉、特定波動率 Regime 切換），本質上是選取特定時間窗（如事件前後 30 分鐘）。這會讓資料列數大幅減少（Sparse Rows）。在沒有大尺度串流架構下，系統依然能無痛處理，且立刻產生極高的 Alpha 研究價值。
2. **無腦暴力 vs 邏輯演繹：** 把 430K 個無腦特徵丟進全時段去硬算 IC（Phase 3），通常只會得到一堆假訊號或高度共線性的結果。真實的 Alpha 往往存在於「特定的市場狀態（Regime）」或「微觀結構事件」中。先有 Case-Control 能力，研究員才能驗證其金融邏輯。

---

### [挑戰 3] 漏排的關鍵修法與量化盲點

Claude 的計畫偏重「統計指標的補齊」，但漏了幾個量化系統最致命的毒藥：

1. **[紅線] 前瞻偏誤 (Look-ahead Bias) 與對齊檢驗：** 這是量化第一殺手。在算 IC 之前，必須有硬性防線檢測 $Feature_{t}$ 與 $Target_{t+1}$ 之間是否有微秒級的 timestamp 錯位。只要錯位 1 tick，IC 就會爆表。這必須在 Phase 1。
2. **[盲點] 目標變數 (Target Y) 的重疊性 (Overlapping Returns)：** 算 5 分鐘的未來報酬，但如果取樣頻率是 1 分鐘，資料就有 4 分鐘的重疊。這會導致序列高度自相關，一般 p-value 完全失效。HAC 是解法，但更基礎的是要能讓使用者自訂或認知到 Target Horizon 與 Sampling Rate 的關係。
3. **[盲點] 換手率與摩擦成本懲罰：** 一個半衰期 (Decay) 只有 5 秒的特徵，就算 IC 再高，扣除手續費和滑點 (Slippage) 後 Net IC 也是負的。Net IC 不能只靠 Grinold 粗估，必須引入特徵自相關性（Autocorrelation / Turnover proxy）作為折價。

---

### [委員會版本] Phase 計畫重排

基於上述挑戰，我們將 Phase 重新切分，以「研究員能逐步建立信任」為核心主軸：

#### Phase 0 — 止血與工程阻礙排除 (立即可動)
*(維持你的版本，無異議)*
- 解決 GroupedConfig 崩潰、feature_filter 幽靈落地、analyze to_thread 防卡死、WS 錯誤顯示。
- **目的：** 讓系統跑得完，不會中途炸掉。

#### Phase 1 — 防漏與正確性紅線 (Ground Truth)
*(強化防禦機制)*
- **1a 嚴格的 Train/Val/Test 切分主路徑。** (絕對優先)
- **1b [新增] 強制前瞻偏誤 (Lookahead) 檢測：** 特徵與標籤的 timestamp 嚴格對齊驗證。
- **1c FDR 接線與真送：** 阻斷多重比較陷阱。
- **1d 目標對齊與 HAC 校正：** 針對 Overlapping returns 實作 HAC 或 Block Bootstrap，確保顯著性檢定有效。
- **1e 靜默空圖修復與 Schema 修正。**
- **目的：** 確保算出來的每一個數字，在小尺度下都是絕對正確、無洩漏、經得起考驗的。

#### Phase 2 — 主戰場：Event-Driven & Case-Control
*(提前，因為研究價值最高，且運算成本較低)*
- 事件清單 Ingestion (正反標籤)。
- 事件前後時間窗 (Event Window) 對齊與截取。
- Purged Cross-Validation (剔除事件重疊期的樣本外測試)。
- 正反例 Matching 與判別指標 (AUC/t-stat)。
- **目的：** 賦予研究員驗證特定金融邏輯（如爆倉套利、流動性枯竭）的能力。

#### Phase 3 — 特徵經濟學與實質 IC (Real-world Value)
*(從原 Phase 4 抽出，因為即使小規模也需要知道特徵能不能交易)*
- **3a [新增] 換手率懲罰與真實 Net IC：** 引入特徵自相關性計算，結合手續費/滑點假設，過濾高頻雜訊。
- **3b 邊際 IC 與特徵正交化：** 解決特徵間的多重共線性，確認新特徵是否有增量貢獻。
- **3c factor_attribution 實作。**

#### Phase 4 — 大尺度架構 (Streaming 430K)
*(延後至此，基礎邏輯已穩固)*
- 串流分塊、Tier-adaptive chunk、Cross-sectional 串流。
- **策略：** 將 Phase 1-3 在小尺度驗證過的數學邏輯 (Ground Truth) 作為單元測試，保證串流重構時不破壞正確性。

#### Phase 5 — 策略整合與 Agent 顧問層 (V2)
- IC 倖存者對接 XGB/LGBM 模型。
- 過擬合檢定 (DSR/PBO)。
- Agent 結構化解讀與委員會式評估。

### 結論
你的直覺是對的。**「正確性先修」是唯一符合量化思維的路徑。** 委員會的版本進一步將「防漏 (Data Leakage)」與「摩擦成本 (Turnover)」補齊，並將「Case-Control」明確排在大尺度串流之前，這將最大化系統在每個開發階段的實用價值。
