# 產品願景與版本演進規劃

> **Authority**: 本文件定義系統長期演進方向，所有 Phase/Task 規劃須與此願景一致  
> **Version**: 1.1  
> **Created**: 2026-02-09  
> **Updated**: 2026-02-14  
> **Owner**: System Architect  
> **Status**: Living Document（隨系統發展持續更新）

---

## 📋 目錄

1. [願景聲明](#願景聲明)
2. [產品定位](#產品定位)
3. [版本演進路線](#版本演進路線)
4. [架構演進策略](#架構演進策略)
5. [技術債管理](#技術債管理)
6. [成功指標](#成功指標)

---

## 願景聲明

### 終極目標

**打造全自主量化研究 AI Agent**，能夠：
- 自主發現市場機會
- 自主驗證交易策略
- 自主優化模型參數
- 自主評估風險報酬
- 與人類研究員協作討論

### 核心價值主張

> **從「工具」演進到「智能研究員」**

```
V1.0（工具階段）  → 用戶手動操作 UI，系統執行任務
V2.0（助手階段）  → 用戶自然語言對話，AI 理解意圖並執行
V3.0（夥伴階段）  → AI 自主研究，向用戶提出建議，協作決策
```

---

## 產品定位

### 系統類型

**量化研究工作平台（Quantitative Research Platform）**

與傳統系統的差異：
```
傳統量化交易系統: 已知策略 → 優化參數 → 回測 → 實盤
本系統 V1.0:     探索案例 → 發現 Pattern → ML 優化 → 回測
本系統 V2.0:     自然語言描述想法 → AI 執行研究流程 → 對話式分析
本系統 V3.0:     AI 自主發現機會 → 向用戶提出假設 → 協作驗證
```

### 目標用戶

| 版本 | 目標用戶 | 使用門檻 | 典型場景 |
|------|---------|---------|---------|
| **V1.0** | 量化研究員、程式交易者 | 需理解技術指標、策略邏輯 | 手動配置參數 → 查看結果 → 下載數據分析 |
| **V2.0** | 一般投資人、策略分析師 | 不需編程，會描述交易想法 | "幫我找出 RSI 超賣後反彈的案例" → AI 執行 → 對話討論 |
| **V3.0** | 基金經理、研究團隊 | 提供市場約束條件即可 | AI: "我發現一個新 Pattern，勝率 65%..." → 人類審查 → 部署 |

---

## 版本演進路線

### V1.0 - 手動 UI 操作階段（2026 Q1-Q2）

#### 定位
**UI-Driven Research Platform** - 用戶透過 Web UI 手動執行研究流程

#### 核心功能

**1. 資料層 (Data Layer)**
- ✅ HDF5 K 線資料存儲（已完成）
- ✅ 幣安資料批量下載（已完成）
- ⚠️ 資料完整性檢查（進行中）

**2. 搜索層 (Search Layer)**
- ✅ 30 參數案例搜索（已完成）
- ✅ 並行多標的搜索（已完成）
- ✅ 反例控制邏輯（已完成）

**3. 特徵層 (Feature Layer)**
- ✅ FeatureFactory 7 層 Pipeline（已完成 - Task 1.5）
- ✅ 6514 特徵自動生成（已完成）
- ✅ 配置化 Preset 管理（已完成）

**4. 優化層 (Optimization Layer)**
- ✅ Optuna 參數優化（已完成 - Phase 3）
- ✅ 雙密度公式評分（已完成）
- ✅ WebSocket 實時進度（已完成）

**5. 視覺化層 (Visualization Layer)**
- ✅ 多 Pane 同步圖表（已完成）
- ✅ 9 個優化結果組件（已完成）
- ✅ 信號密度分析圖（已完成）

**6. ML 層 (ML Layer) - Phase 3.7**
- ✅ XGBoost + LightGBM 雙引擎 ML 系統（已完成）
- ✅ IModelTrainer Protocol 標準化引擎介面（已完成）
- ✅ 雙引擎對比報告（consensus_rate、feature_rank_correlation）（已完成）
- ✅ 四維參數系統（模型/訓練/驗證/運行）（已完成）
- ✅ 可插拔 Optuna Objective 架構（已完成）

**7. 導出層 (Export Layer)**
- ✅ CSV 原始資料導出（已完成）
- ✅ PNG 圖表導出（已完成）
- ❌ **AI 可讀檔案格式**（未定義）← **V1.0 缺口**

#### V1.0 完成標準

| 項目 | 標準 | 狀態 |
|------|------|------|
| UI 完整性 | 所有功能可透過 UI 操作 | ✅ 已達成 |
| 資料導出 | 支援 CSV + PNG | ✅ 已達成 |
| **雙引擎 ML** | **LightGBM + XGBoost 訓練、對比、Protocol 擴展** | **✅ 已達成 (Phase 3.7)** |
| **AI 可讀檔案** | **結構化 JSON/MD 格式，包含完整分析脈絡** | ❌ **待定義** |
| 效能 | 標準 Preset < 15s | ✅ 已達成（13.37s）|
| 文檔 | 使用者操作手冊 + API 文檔 | ⚠️ 進行中 |

#### V1.0 → V1.1 補完計劃

**AI 可讀檔案格式設計**（優先級：🔥🔥🔥 P0）

```json
{
  "analysis_metadata": {
    "task_type": "case_search | optimization | pattern_discovery",
    "created_at": "ISO-8601 timestamp",
    "system_version": "1.0.2",
    "execution_time_seconds": 13.37
  },
  "search_config": {
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "timeframe": "12h",
    "trigger_conditions": {...},
    "future_performance": {...}
  },
  "results_summary": {
    "total_cases": 156,
    "positive_cases": 89,
    "negative_cases": 67,
    "win_rate": 0.571,
    "avg_return": 0.0324
  },
  "detailed_cases": [...],
  "feature_importance": {...},
  "optimization_results": {...},
  "llm_analysis_hints": {
    "key_findings": ["Finding 1", "Finding 2"],
    "recommended_actions": ["Action 1", "Action 2"],
    "risk_warnings": ["Risk 1"]
  }
}
```

**Markdown 報告模板**（優先級：🔥🔥 P1）

````markdown
# 量化分析報告 - {Task Type}

## 執行概要
- **任務類型**: 案例搜索
- **執行時間**: 2026-02-09 14:32:15
- **處理標的**: 50 個加密貨幣
- **總執行時間**: 13.37 秒

## 搜索配置
- **時間框架**: 12h
- **觸發條件**: 價格上漲 > 3%, Taker Ratio > 0.65
- **驗證窗口**: 未來 1-12 根 K 線

## 核心發現
1. 找到 156 個符合條件的案例
2. 正例 89 個（勝率 57.1%）
3. 平均報酬率 3.24%

## 詳細案例
| Symbol | Timestamp | Entry Price | Exit Price | Return |
|--------|-----------|-------------|------------|--------|
| BTCUSDT | 2023-05-15 | 27500 | 28320 | 2.98% |
...

## 特徵重要性
...

## 建議行動
...
````

---

### V2.0 - Chat 自然語言階段（2026 Q3-Q4）

#### 定位
**Conversational Research Assistant** - 用戶用自然語言描述交易想法，AI 理解並執行

#### 核心功能

**1. 自然語言理解 (NLU Layer)**
- ❌ 交易意圖識別（"找出超賣反彈的案例"）
- ❌ 參數實體提取（時間框架、標的、指標閾值）
- ❌ 多輪對話狀態管理

**2. 任務編排 (Task Orchestration)**
- ❌ 自然語言 → 搜索配置轉換
- ❌ 自動選擇合適的分析流程
- ❌ 串接多個引擎（搜索 → 特徵 → 優化）

**3. 對話式分析 (Conversational Analytics)**
- ❌ 結果自然語言摘要
- ❌ 追問澄清（"你想要更保守還是激進的策略？"）
- ❌ 對話式圖表探索

**4. Chat UI**
- ❌ WebSocket 即時對話
- ❌ 圖表/表格內嵌在對話中
- ❌ 多模態輸入（文字 + 圖片標記）

#### V2.0 架構預準備（V1.x 階段須完成）

| 需求 | V1.0 狀態 | V2.0 需求 | Gap |
|------|----------|----------|-----|
| API 解耦 | ✅ FastAPI REST | - | 無 Gap |
| 任務異步化 | ✅ asyncio + WebSocket | - | 無 Gap |
| 結果結構化 | ⚠️ 部分 JSON | 完整 JSON Schema | 需補全 |
| LLM 提示詞模板 | ❌ 不存在 | Prompt Engineering | 需新增 |
| 對話狀態管理 | ❌ 無狀態 API | Session-based | 需新增 |

#### V2.0 技術棧預估

```yaml
NLU 引擎:
  - LangChain / LlamaIndex（任務編排）
  - OpenAI GPT-4 / Claude 3.5（意圖理解）
  - Few-shot Learning（領域特定微調）

對話管理:
  - Redis（Session 存儲）
  - WebSocket（實時對話流）

前端擴展:
  - Chat UI 組件（參考 ChatGPT 介面）
  - Markdown 渲染器（表格、圖表內嵌）
  - 語音輸入（可選）
```

#### V2.0 完成標準

- [ ] 用戶可用自然語言完成 80% 的 V1.0 功能
- [ ] 單次對話可串接 2-3 個分析步驟
- [ ] AI 回覆包含可操作的圖表/表格
- [ ] 對話歷史可追溯、可匯出

---

### V3.0 - 全自主 AI Agent 階段（2027+）

#### 定位
**Autonomous Quantitative Researcher** - AI 自主探索市場，向人類提出驗證的交易策略

#### 核心能力

**1. 自主發現 (Autonomous Discovery)**
- ❌ 掃描市場異動（價格、成交量、市場情緒）
- ❌ 主動生成搜索假設
- ❌ 無監督 Pattern Mining

**2. 自主驗證 (Autonomous Validation)**
- ❌ 自動設計反例測試
- ❌ 多時間框架交叉驗證
- ❌ 統計顯著性檢驗

**3. 自主優化 (Autonomous Optimization)**
- ❌ Meta-Learning（從過去的策略中學習）
- ❌ 多目標優化（報酬 vs 風險 vs 頻率）
- ❌ 動態參數調整

**4. 人機協作 (Human-AI Collaboration)**
- ❌ AI 提出策略假設，等待人類審查
- ❌ 解釋決策邏輯（SHAP、LIME）
- ❌ 風險預警系統

**5. 自我學習 (Self-Learning)**
- ❌ 策略表現回測 → 更新決策模型
- ❌ 錯誤案例分析 → 改進搜索邏輯
- ❌ 市場環境感知 → 動態策略切換

#### V3.0 架構需求

**新增模組**（V2.0 須預留擴展點）

```
momentum/Agent/
  ├── policy_engine.py          # 決策引擎
  ├── meta_learner.py           # 元學習器
  ├── market_scanner.py         # 市場掃描器
  ├── hypothesis_generator.py   # 假設生成器
  ├── risk_evaluator.py         # 風險評估器
  └── explainer.py              # 可解釋性模組

api/agent/
  ├── agent_orchestrator.py     # Agent 編排服務
  ├── approval_workflow.py      # 人類審批工作流
  └── monitoring.py             # 運行監控
```

#### V3.0 技術棧預估

```yaml
決策框架:
  - Reinforcement Learning（策略優化）
  - Bayesian Optimization（參數搜索）
  - Multi-Armed Bandit（策略選擇）

知識庫:
  - Vector Database（策略記憶）
  - Graph Database（市場關係圖）

可解釋性:
  - SHAP（特徵重要性）
  - Attention Visualization（模型注意力）
  - Counterfactual Explanation（反事實解釋）
```

#### V3.0 完成標準

- [ ] AI 每日自主產生 5-10 個策略假設
- [ ] 策略通過驗證率 > 30%（人類研究員水平）
- [ ] 決策可解釋性達到 90%（能清楚說明為何選擇某策略）
- [ ] 人類可在 5 分鐘內審查一個策略

---

## 架構演進策略

### 持續解耦原則

**所有版本演進必須遵循 7 條解耦規則**（canonical 定義唯一權威 = `CLAUDE.md` §The 7 Decoupling Rules;本表僅示意各版本演進方向,規則本體與現況以 CLAUDE.md 為準）：

> ⚠️ **現況欄據實**(2026-07-12 `check_decoupling.sh` 實跑):R2/R3/R4 目前**有既存違規**(多為 `momentum/FeatureEngineering` 共用工具的具體 import + 1 筆 service→service),非全綠;是否屬真違規或應豁免為共用基礎設施,列 ROADMAP P2 債票 triage。勿再標「已達成」。

| 規則 | V1.0 現況 | V2.0 | V3.0 |
|------|------|------|------|
| **Rule 1**: `momentum` 不依賴 `api` | ✅ 0 violation | 必須保持 | 必須保持 |
| **Rule 2**: Domain 內部用 Protocol | ⚠️ scanner 報 5 筆(FeatureEngineering 共用工具);待 triage | 擴展至 NLU | 擴展至 Agent |
| **Rule 3**: `api/services` 用 Factory 注入 | ⚠️ scanner 報 12 筆(同上);待 triage | 新增 Chat Service | 新增 Agent Service |
| **Rule 4**: Service 間禁止直接調用 | ⚠️ 1 已知違規(`feature_factory_batch_adapters.py`) | 必須保持 | 必須保持 |
| **Rule 5**: Config 單一來源 | ✅ scanner 綠 | 擴展至 Prompt Config | 擴展至 Policy Config |
| **Rule 6**: 測試不依賴 `run_api.py` | ✅ phase4(Strategy/ 子集)綠 | 必須保持 | 必須保持 |
| **Rule 7**: DTO 不跨層 | ✅ 0 violation | 必須保持 | 必須保持 |

### 模組化擴展策略

**V1 → V2 擴展點**：
```python
# V1.0 結構
api/
  routes/          # REST endpoints
  services/        # Business logic
  
# V2.0 新增（不影響 V1.0）
api/
  routes/          # 保持不變
  services/        # 保持不變
  chat/            # 新增：Chat 路由
    ├── chat_router.py
    ├── nlu_service.py
    └── conversation_manager.py
```

**V2 → V3 擴展點**：
```python
# V3.0 新增（不影響 V1.0/V2.0）
momentum/
  Agent/           # 新增：自主決策引擎
api/
  agent/           # 新增：Agent 管理服務
```

### 介面穩定性承諾

**API 穩定性**：
```yaml
V1.0 API: 
  - 保持向後相容至少 2 年
  - 新版本使用 /api/v2/ 路徑
  
V2.0 Chat API:
  - 獨立端點 /api/chat/
  - 不影響 V1.0 REST API
  
V3.0 Agent API:
  - 獨立端點 /api/agent/
  - 內部可調用 V1/V2 API
```

---

## 技術債管理

### V1.0 已知技術債

| 項目 | 影響 | 計劃償還時間 | 阻礙版本 |
|------|------|-------------|---------|
| AI 可讀檔案格式未定義 | 🔥🔥🔥 阻塞 V2.0 | V1.1 | V2.0 |
| 使用者操作手冊缺失 | 🔥🔥 降低採用率 | V1.2 | - |
| 錯誤處理不統一 | 🔥 維護困難 | V1.3 | - |
| 部分 Service 邏輯過重 | 🔥 測試困難 | V2.0 重構時處理 | - |

### V2.0 預期技術債

- Session 管理複雜度
- Prompt Engineering 維護成本
- 對話狀態一致性問題

### 償還策略

**每個版本預留 20% 時間處理技術債**：
```
V1.x 迭代: 60% 新功能 + 20% 技術債 + 20% 文檔/測試
V2.0 大版本: 50% 新功能 + 30% 重構 + 20% 基礎設施
```

---

## 成功指標

### V1.0 成功指標

**功能完整性**：
- [x] 案例搜索成功率 > 95%
- [x] 特徵生成穩定性 > 99%（無崩潰）
- [x] 優化任務完成率 > 90%
- [ ] 資料導出格式完整（含 AI 可讀）

**效能**：
- [x] 標準 Preset 生成時間 < 15s
- [x] API 響應時間 P95 < 2s
- [ ] 並行搜索吞吐量 > 100 標的/分鐘

**用戶體驗**：
- [ ] UI 操作流暢度評分 > 4.0/5.0
- [ ] 文檔完整度 > 80%
- [ ] Bug 修復時間 < 48h

### V2.0 成功指標

**意圖理解準確率**：
- [ ] 單輪對話意圖識別 > 85%
- [ ] 多輪對話完成率 > 70%
- [ ] 參數提取準確率 > 90%

**任務成功率**：
- [ ] 自然語言 → 正確搜索配置 > 80%
- [ ] AI 摘要相關性評分 > 4.0/5.0

**效率提升**：
- [ ] 用戶完成任務時間減少 50%
- [ ] 新手上手時間 < 10 分鐘

### V3.0 成功指標

**自主能力**：
- [ ] 策略發現成功率 > 30%
- [ ] 假陽性率 < 20%
- [ ] 決策可解釋性 > 90%

**協作效果**：
- [ ] 人類審查時間 < 5 分鐘/策略
- [ ] 人類採納率 > 40%

**學習能力**：
- [ ] 策略表現持續改善（月增長率 > 2%）
- [ ] 錯誤重複率 < 5%

---

## 文檔更新承諾

**本文件的維護節奏**：
- **每季度**：更新版本演進進度
- **每次架構變更**：同步更新演進策略
- **每個 Phase 完成後**：補充實際經驗與教訓

**相關文檔**：
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 當前架構設計
- [FEATURE_ROADMAP.md](./FEATURE_ROADMAP.md) - 短期功能計劃（6 個月）
- [SYSTEM_DECOUPING_PLAN_TODO.md](./SYSTEM_DECOUPING_PLAN_TODO.md) - 解耦執行計劃
- [Feature_Factory_PLAN.md](./Feature_Factory_PLAN.md) - Task 1 特徵工程計劃

---

## 附錄：決策記錄

### ADR-001: 為何選擇三階段演進？

**背景**：可以一次性開發 V3.0，為何分階段？

**決策**：採用漸進式演進，原因：
1. **風險控制**：每階段可獨立驗證價值
2. **學習市場需求**：V1.0 用戶反饋影響 V2.0 設計
3. **技術成熟度**：AI Agent 技術仍在快速演進
4. **資源分配**：分階段更易募資和招募

**後果**：
- ✅ 降低失敗風險
- ⚠️ 總開發時間可能延長
- ⚠️ 需要維護多個版本的相容性

### ADR-002: AI 可讀檔案格式為何必要？

**背景**：V1.0 已有 CSV/PNG 導出，為何還需要 AI 可讀格式？

**決策**：必須新增結構化 JSON/Markdown 格式，原因：
1. **V2.0 基礎**：Chat AI 需要理解 V1.0 的輸出
2. **可重現性**：完整記錄分析配置和結果
3. **API 整合**：方便其他系統/Agent 調用

**格式選擇**：
- JSON: 機器可讀，結構化完整
- Markdown: 人類可讀，適合報告

**後果**：
- ✅ V2.0 開發更順暢
- ✅ 系統間整合更容易
- ⚠️ V1.1 需要額外開發時間（預估 1-2 週）

---

**文檔版本歷史**：
- v1.1 (2026-02-14): 新增 Phase 3.7 雙引擎 ML 系統至 V1.0 功能層；更新完成標準表；更新 Rule 2 Protocol 狀態
- v1.0 (2026-02-09): 初始版本，定義 V1/V2/V3 演進路線
