# 量化交易策略系統

> 基於AI的量化研究工作平台 - 從案例發現到策略優化的完整工作流

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 目錄

- [系統簡介](#系統簡介)
- [核心特色](#核心特色)
- [技術棧](#技術棧)
- [系統架構](#系統架構)
- [功能狀態](#功能狀態)
- [快速開始](#快速開始)
- [項目結構](#項目結構)
- [開發指南](#開發指南)
- [文檔索引](#文檔索引)
- [開發路線圖](#開發路線圖)
- [常見問題](#常見問題)

---

## 系統簡介

### 這是什麼？

**量化研究工作平台** - 一個創新的交易策略研究系統，不同於傳統量化交易平台：

```
傳統量化平台：已知策略 → 優化參數 → 回測 → 實盤
本系統：    探索案例 → 發現Pattern → ML優化 → 回測 → (未來)實盤
```

### 核心價值

- 🔍 **案例發現引擎** - 從海量歷史數據中找出符合特定模式的交易機會
- 🧪 **指標實驗室** - 自動測試數十種技術指標的有效性
- 🎯 **IC 篩選系統** - Information Coefficient 特徵篩選，自動識別預測力強的指標
- 🤖 **ML優化系統** - 使用機器學習自動發現盈利Pattern
- 📊 **完整研究流程** - 支持從假設驗證到策略回測的全流程
- 🌐 **多市場支持** - 設計可擴展至加密貨幣、台股、美股

### 系統定位

這不是一個「交易執行系統」，而是一個「策略研究平台」：
- ✅ 幫助發現有效的交易策略
- ✅ 驗證技術指標的有效性
- ✅ 優化策略參數
- ✅ 回測驗證績效
- ⏳ (未來) 部署實盤交易

---

## 核心特色

### 1. 案例搜索引擎（已完成 ✅）

**20參數框架** - 精確定義搜索條件：
- 6個觸發條件（價格變化、成交量倍數、主動買入比例等）
- 12個未來表現驗證（1-12根K線的收益率和最大回撤）
- 2個反例控制參數（正負比例、時間分離）

**智能採樣策略**：
- 標的內部採樣（正反例來自相同標的池）
- 時間分離驗證（避免相同市場事件影響）
- 分層採樣（按時間、市場環境、波動度分層）

### 2. 圖表分析系統（已完成 ✅）

**TradingView 風格圖表**：
- 多層同步圖表（Price K 線、Volume、Taker Ratio、指標）
- 信號箭頭標記（策略信號可視化）
- 案例時間點高亮（TO/TC 標記系統）
- 流暢的縮放和拖曳（Lightweight Charts）

### 3. IC 特徵篩選系統（Phase 2 完成 ✅）

**八階段篩選管線** - Information Coefficient 驅動的特徵選擇：
- **Stage 0**: 資料攝入（HDF5 特徵 + 標籤 + Metadata JSON）
- **Stage 1**: 數據前處理（Winsorization、缺失值處理、標準化、常數特徵移除）
- **Stage 2**: 標籤生成（收益率計算、時間跨度轉換、forward_N_return）
- **Stage 3**: 事件篩選（Query/Timestamp 模式、樣本數分層 tier_1/2/3）
- **Stage 4**: IC 計算（Rolling IC、ICIR、IC Decay、Grouped IC 按年/季/狀態）
- **Stage 5**: 統計驗證（t-test、p-value、信賴區間、Bonferroni/FDR 多重比較修正）
- **Stage 6**: 單調性測試（分位數報酬、單調性分數、Long-Short 價差）
- **Stage 7**: 冗餘篩選（相關矩陣分析、Greedy/Hierarchical/VIF、多樣化評估）
- **Stage 8**: 報告生成（JSON、Markdown、HDF5、AI 摘要四種格式）

**三種 IC 方法**:
- **Spearman**（非線性關係、對離群值穩健、適合單調關係）
- **Pearson**（線性關係、最大解釋力、適合連續變數）
- **Kendall**（排序一致性、樣本數小時穩定、適合序數資料）

**四種冗餘篩選演算法**:
- **Greedy 去重**（迭代保留高 IC 特徵、快速剔除冗餘）
- **Hierarchical Clustering**（樹狀結構自動分組、視覺化相似度）
- **VIF**（方差膨脹因子、多重共線性偵測、回歸分析必備）
- **Diversification**（多樣化評估、確保特徵互補、降低模型風險）

**模型驗證子系統**（5 個模組）:
- **時間序列交叉驗證**（CV Validator - OOT 切分、AUC/Precision/Recall/F1）
- **Out-of-Time 驗證**（OOT Validator - CV-OOT Gap 評估、穩定性分析）
- **PSI 漂移監控**（PSI Calculator - 分布穩定性、drift 偵測）
- **滾動 AUC 追蹤**（Rolling AUC - 時間序列性能、趨勢分析）
- **SHAP 可解釋性**（Case SHAP - 單案例解釋、批次特徵重要性）

**效能表現**:
- 200 features × 10K samples < 2s（超標 4 倍）
- 支援 refilter 模式（讀取已計算 IC，重新套用篩選條件，10 倍加速）
- HDF5 特徵存儲（gzip 壓縮、metadata 管理）
- 向量化計算（Pandas/NumPy 優化、避免 Python 循環）

**測試覆蓋**:
- 26 個測試檔案、159 tests passed、2 warnings
- 100% coverage (1,563/1,563 statements)
- 效能基準測試：200 features × 10K samples < 2s

**架構合規**:
- ✅ Rule 1-7 完全遵守（Protocol 注入、Factory 建構、無跨域 import）
- ✅ 模組化設計（12 核心 + 5 驗證 + 1 例外處理）
- ✅ 三層配置系統（Default < YAML < API Override）

### 4. 雙引擎 ML 系統（Phase 3.7 完成 ✅）

**LightGBM + XGBoost 雙引擎訓練**：
- ✅ XGBoost 引擎（8 個 Protocol 方法，向後相容）
- ✅ LightGBM 引擎（平行架構，性能對比）
- ✅ 雙引擎對比系統（自動推薦最佳引擎、共識率分析）
- ✅ 四維參數系統（YAML / Dict / 自然語言 / Optuna 搜尋空間）
- ✅ 可插拔 Optuna 目標函式（ModelHyperparam / SignalDensity / StrategyBacktest）
- ✅ IModelTrainer Protocol 架構（8 個方法、可替換引擎）
- ✅ 160+ 測試覆蓋（邊界條件 100%）
- LSTM 時序模型（未來擴展）

### 5. 回測系統（計劃中 📋）

**完整績效評估**：
- Sharpe Ratio、Sortino Ratio、Calmar Ratio
- 最大回撤、勝率、賺賠比
- 權益曲線、交易明細
- 策略對比分析

---

## 技術棧

### 後端 (Python)

```yaml
框架: FastAPI 0.100+
語言: Python 3.11+ (M1原生支持)

數據處理:
  - pandas 2.0+ (數據分析)
  - numpy 1.24+ (數值計算)
  - polars (可選，大數據場景)

技術指標:
  - pandas-ta (技術指標庫)
  - ta-lib (經典指標)

API交互:
  - python-binance (幣安API)
  - ccxt (多交易所支持)

機器學習:
  - XGBoost (分類模型)
  - LightGBM 4.0+ (雙引擎訓練)
  - SHAP (模型可解釋性)
  - Optuna (參數優化、可插拔目標函式)

數據存儲:
  - HDF5 (大量K線數據)
  - CSV (搜索結果)
```

### 前端 (TypeScript)

```yaml
框架: Next.js 15 (App Router)
語言: TypeScript 5.x
樣式: Tailwind CSS 3.x
狀態管理: Zustand

圖表庫:
  - Lightweight Charts (K線圖表)
  - Recharts (Dashboard統計圖表)

組件:
  - React 18
  - shadcn/ui
```

### 開發環境

```yaml
硬件: MacBook M1
Python: 3.11+ (M1原生)
Node: 18+
IDE: VS Code
版本控制: Git + GitHub
```

---

## 系統架構

### 整體架構圖

```
┌─────────────────────────────────────────┐
│         用戶界面層 (Next.js)              │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
│  │案例  │ │圖表  │ │指標  │ │ML    │  │
│  │搜索  │ │分析  │ │測試  │ │訓練  │  │
│  └───┬──┘ └───┬──┘ └───┬──┘ └───┬──┘  │
└──────┼────────┼────────┼────────┼──────┘
       │        │        │        │
┌──────▼────────▼────────▼────────▼──────┐
│         API服務層 (FastAPI)             │
│  ┌──────────────────────────────────┐  │
│  │ 案例搜索 │ 圖表數據 │ 指標測試  │  │
│  │ ML訓練   │ 回測引擎 │ ...       │  │
│  └──────────────────────────────────┘  │
└──────┬────────┬────────┬────────┬──────┘
       │        │        │        │
┌──────▼────────▼────────▼────────▼──────┐
│         核心業務層 (Python)             │
│  - case_search_engine.py                │
│  - signal_analyzer.py                   │
│  - indicator_calculator.py              │
│  - ml_training_engine.py                │
└──────┬────────┬────────┬────────┬──────┘
       │        │        │        │
┌──────▼────────▼────────▼────────▼──────┐
│              數據層                      │
│  Binance API │ HDF5存儲 │ CSV導出      │
└─────────────────────────────────────────┘
```

### 數據流向

```
用戶輸入搜索條件
    ↓
搜索歷史數據，標記案例
    ↓
批量下載K線數據（240前/96後）
    ↓
計算技術指標 + 參數優化
    ↓
ML模型訓練 + Pattern發現
    ↓
回測驗證 + 績效分析
    ↓
(未來) 實盤部署
```

---

## 功能狀態

### ✅ 已完成（可用）

- [x] **Case Search系統**
  - 20參數搜索框架
  - 正反例採樣
  - Web界面操作
  - CSV導出功能
  
- [x] **搜索結果展示**
  - 統計圖表（市場階段、時間分布）
  - 結果篩選和排序
  - 數據完整性驗證

- [x] **基礎架構**
  - FastAPI後端
  - Next.js前端
  - Zustand狀態管理
  - 數據加載系統

- [x] **K線數據批量下載** (階段1)
  - HDF5 存儲系統
  - Binance API 整合
  - 批次並行下載
  - Gap 自動填補

- [x] **圖表分析系統** (階段1)
  - Lightweight Charts 整合
  - 多層同步圖表 (Price/Volume/TakerRatio)
  - TO/TC 標記系統
  - 信號笭頭標記

- [x] **指標測試系統** (Phase 3.1-3.4)
  - 多數據源指標計算引擎
  - 信號密度分析
  - 策略配置 UI
  - 圖表信號標記

- [x] **Optuna 參數優化** (Phase 3.5)
  - 5 種 Sampler (TPE/CmaEs/Random/GP/NSGA-II)
  - 多目標優化 (Pareto 前沿)
  - WebSocket 實時進度
  - Checkpoint 容錯機制

- [x] **優化結果視覺化** (Phase 3.6)
  - 9 個核心元件 (Metrics/Density/Stability/History)
  - CSV/PNG 匯出功能
  - 錯誤處理系統
  - 參數重要性分析

- [x] **雙引擎 ML 系統** (Phase 3.7) ★ 2026-02-14
  - LightGBM + XGBoost 雙引擎訓練
  - IModelTrainer Protocol 架構（8 個方法）
  - 模型對比系統（A/B 測試 + 共識率分析）
  - 四維參數系統（YAML/Dict/NL/Optuna）
  - 可插拔 Optuna 目標函式（3 種目標）
  - 10 個新 API 端點（/model/*、/lightgbm/*）
  - 前端雙引擎對比 UI（6 個新元件）
  - 160+ 測試覆蓋（邊界條件 100%）

- [x] **IC 特徵篩選系統** (Phase 2 - IC Gatekeeper)
  - 八階段篩選管線 (Stage 0-8)
  - 三種 IC 方法 (Spearman/Pearson/Kendall)
  - 四種冗餘篩選 (Greedy/Hierarchical/VIF/Diversification)
  - 多報告格式 (JSON/Markdown/HDF5/AI 摘要)
  - 100% 測試覆蓋 (159 tests, 1563/1563 statements)

- [x] **模型驗證子系統** (Phase 2)
  - CV Validator (時間序列交叉驗證)
  - OOT Validator (Out-of-Time 驗證)
  - PSI Calculator (PSI 漂移監控)
  - Rolling AUC (滾動 AUC 追蹤)
  - Case SHAP (SHAP 可解釋性)

### 🔨 開發中

- [ ] **IC Gatekeeper 前端 UI**
  - IC 分析結果視覺化
  - 互動篩選控制面板
  - 報告下載功能 (JSON/Markdown/HDF5)
  - 相關性矩陣熱力圖
  - 特徵對比圖表

- [ ] **Feature Factory 前端整合**
  - Feature 管理介面
  - 批次計算控制
  - 特徵工程配置

### 📋 計劃中

- [ ] **回測系統** (3-4 週)
- [ ] **Pattern 精煉與深度分析增強**
- [ ] **AI 可讀檔案格式（結構化 JSON/Markdown 導出）**

### 💡 未來擴展

- [ ] 實盤交易系統（雲端部署）
- [ ] 多市場支持（台股、美股）
- [ ] 鏈上數據整合

---

## 快速開始

### 前置要求

```bash
# Python 3.11+
python --version

# Node.js 18+
node --version

# Git
git --version
```

### 安裝步驟

#### 1. 克隆項目

```bash
git clone https://github.com/your-username/quantitative_trading_system.git
cd quantitative_trading_system
```

#### 2. 後端設置

```bash
# 創建虛擬環境
python -m venv venv

# 激活虛擬環境
source venv/bin/activate  # Mac/Linux
# 或
venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt

# 配置環境變量
cp .env.example .env
# 編輯.env文件，添加API密鑰

# 啟動後端
python run_api.py
```

後端將在 `http://localhost:8000` 運行

#### 3. 前端設置

```bash
# 進入前端目錄
cd frontend

# 安裝依賴
npm install

# 啟動開發服務器
npm run dev
```

前端將在 `http://localhost:3000` 運行

#### 4. 驗證安裝

訪問以下URL確認系統正常：
- 前端: http://localhost:3000
- 後端API文檔: http://localhost:8000/docs
- 後端健康檢查: http://localhost:8000/health

---

## 項目結構

```
quantitative_trading_system/
├── api/                        # 後端API
│   ├── core/                   # 核心配置
│   ├── routes/                 # API路由
│   ├── services/               # 業務邏輯
│   ├── models/                 # 數據模型
│   └── utils/                  # 工具函數
│
├── frontend/                   # 前端應用
│   ├── src/
│   │   ├── app/               # Next.js頁面
│   │   ├── components/        # React組件
│   │   ├── lib/               # 工具庫
│   │   └── store/             # Zustand狀態
│   ├── public/                # 靜態資源
│   └── package.json
│
├── momentum/                   # 核心業務邏輯
│   ├── core/                  # 基礎設施（Protocol、Config、Logging）
│   ├── factories.py           # 所有 Domain 物件工廠（唯一建構入口）
│   ├── DataExtraction/        # 數據獲取（CaseSearch、HDF5、Binance）
│   ├── Analysis/              # 分析引擎
│   │   ├── xgboost_analyzer.py    # XGBoost 引擎
│   │   ├── lightgbm_analyzer.py   # LightGBM 引擎
│   │   ├── model_comparison.py    # 雙引擎對比
│   │   ├── model_config.py        # 四維參數系統
│   │   ├── model_types.py         # 共用 dataclass
│   │   └── ...                    # SHAP、PSI、Pattern 等
│   ├── FeatureEngineering/    # 特徵工程（7 層 Pipeline）
│   ├── Indicator/             # 純函式技術指標
│   ├── Indicators/            # OOP 指標引擎
│   └── Optimization/          # Optuna 優化（可插拔目標）
│       └── objectives/        # 目標函式套件
│
├── docs/                       # 項目文檔
│   ├── ARCHITECTURE.md        # 系統架構
│   ├── FEATURE_ROADMAP.md     # 開發路線圖
│   ├── API_SPECIFICATION.md   # API規範
│   └── DEVELOPMENT_GUIDE.md   # 開發指南
│
├── data_cache/                 # 數據緩存（.gitignore）
├── results/                    # 搜索結果（.gitignore）
├── requirements.txt            # Python依賴
├── run_api.py                  # 後端啟動腳本
└── README.md                   # 本文件
```

---

## 開發指南

### 開發模式

本項目採用 **AI驅動開發模式**：
- 🤖 **Claude Code CLI** 負責代碼生成和bug修復
- 👨‍💻 **人工** 負責需求定義、功能驗證、錯誤報告
- 🔄 **協作迭代** 快速開發、持續改進

### Ultra Think三步驟流程

**所有代碼生成必須遵循此流程**：

```
步驟1 - 初始生成：
  根據需求生成初版代碼

步驟2 - 自我審查：
  Review代碼，列出優化To-do List

步驟3 - 優化重構：
  根據To-do List生成最終版本
```

### 核心開發原則

#### ⚠️ 數據真實性（最重要）
```
嚴禁使用假數據、虛擬數據、硬編碼
所有數據必須來自真實數據源或配置文件
```

#### 📝 日誌規範
```
- 關鍵操作記錄INFO級別log
- 錯誤記錄ERROR級別並包含exc_info=True
- 避免在循環內大量log
```

#### 🛡️ 錯誤處理
```
- 外部API調用必須try-catch
- 區分錯誤類型（可重試 vs 不可重試）
- 給用戶友好的錯誤提示
```

#### ⚡ 性能優化（M1）
```
優先級：向量化 > Numba > 並行 > Python循環
- 使用pandas向量化操作
- 關鍵計算用Numba加速
- 充分利用M1的8核心並行
```

### 代碼審查Checklist

提交前必須檢查：
- [ ] 沒有假數據/硬編碼
- [ ] 錯誤處理完整
- [ ] log記錄適當
- [ ] 變量命名清晰
- [ ] 沒有重複代碼
- [ ] 性能合理
- [ ] 有類型提示
- [ ] 複雜邏輯有註釋

### Git提交規範

```bash
# 格式：<type>: <subject>
feat: 添加K線數據批量下載功能
fix: 修復搜索API的速率限制錯誤
docs: 更新README添加快速開始指南
refactor: 重構指標計算引擎
perf: 優化DataFrame操作使用向量化
```

---

## 文檔索引

### 核心文檔

| 文檔 | 說明 | 行數 |
|------|------|------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系統整體架構設計 | ~4000 |
| [FEATURE_ROADMAP.md](docs/FEATURE_ROADMAP.md) | 24週開發計劃 | ~2500 |
| [API_SPECIFICATION.md](docs/API_SPECIFICATION.md) | API接口規範 | ~700 |
| [DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) | 開發規範和指南 | ~3500 |

### 快速鏈接

- **新手入門** → [快速開始](#快速開始)
- **理解架構** → [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **開始開發** → [DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md)
- **API使用** → [API_SPECIFICATION.md](docs/API_SPECIFICATION.md)
- **功能規劃** → [FEATURE_ROADMAP.md](docs/FEATURE_ROADMAP.md)

### 其他文檔

| 文檔 | 說明 |
|------|------|
| [程式碼生成規範](docs/standards/coding_standards.md) | Ultra Think三步驟 |
| [Git工作流程](docs/guides/git_workflow.md) | Git使用指南 |
| [GitHub清理指南](docs/guides/github_cleanup.md) | 倉庫容量管理 |

---

## 開發路線圖

### 當前進度（2026 Q1）

```
✅ 已完成 → 🔨 開發中 → 📋 計劃中

Phase 1: 案例搜索系統 + Web UI [✅ 100%]
  ✅ Case Search 30 參數框架
  ✅ 搜索結果展示
  ✅ 基礎架構搭建

Phase 2 (K線圖表): K 線下載 + 圖表系統 [✅ 100%]
  ✅ Lightweight Charts 整合
  ✅ K線數據批量下載
  ✅ 信號標記系統

Phase 2 (IC Gatekeeper): IC 特徵篩選 [✅ 100%]
  ✅ 八階段 IC 篩選管線
  ✅ 模型驗證子系統
  ✅ 159 tests, 100% coverage

Phase 3: Optuna + 信號分析 + 視覺化 [✅ 100%]
  ✅ Optuna 參數優化（5 種 Sampler）
  ✅ 信號密度分析
  ✅ 9 個視覺化元件

Phase 3.5: 特徵工程 + XGBoost [✅ 100%]
  ✅ Feature Factory 7 層 Pipeline
  ✅ XGBoost 分析（21 個端點）

Phase 3.7: 雙引擎 ML 系統 [✅ 100%] ★ 2026-02-14
  ✅ LightGBM + XGBoost 雙引擎
  ✅ 模型對比 + 四維參數系統
  ✅ 160+ 測試覆蓋

REFACTOR V4: 架構解耦 [✅ 100%]
  ✅ 7 條規則、Protocol 注入、Factory 模式

📋 下一步:
  📋 回測系統
  📋 Pattern 精煉
```

### 時間線

```
2025 Q3-Q4: 案例搜索 + 圖表系統 + 指標引擎
2026 Q1:    IC Gatekeeper + Feature Factory + 雙引擎 ML + 架構解耦
2026 Q2:    回測系統 + Pattern 精煉 + AI 導出
2026 Q3+:   Chat 自然語言介面（V2.0）
```

詳細開發計劃見 [FEATURE_ROADMAP.md](docs/FEATURE_ROADMAP.md)

---

## 常見問題

### Q: 這個系統與TradingView有什麼不同？

**A:** TradingView是圖表和分析工具，本系統是**策略研究平台**：
- ✅ 自動化案例搜索（TradingView需手動找）
- ✅ ML模型優化策略（TradingView沒有）
- ✅ 完整的研究工作流（從假設到驗證）
- ✅ 可擴展到實盤交易

### Q: 需要編程基礎嗎？

**A:** 
- **使用系統**：不需要，Web界面操作
- **開發功能**：需要Python/TypeScript基礎
- **AI輔助**：Claude Code CLI協助開發

### Q: 支持哪些市場？

**A:** 
- ✅ **已支持**：加密貨幣（Binance, OKX）
- 📋 **計劃中**：台股、美股
- 🔧 **架構設計**：易於擴展新市場

### Q: 數據從哪裡來？

**A:**
- **加密貨幣**：Binance API、OKX API
- **台股**（未來）：證交所API、yfinance
- **美股**（未來）：IBKR API、yfinance
- ⚠️ **嚴禁使用假數據**：所有數據必須真實

### Q: M1 Mac有什麼優勢？

**A:**
- ✅ Python 3.11原生支持
- ✅ 8核心並行處理
- ✅ 向量化計算優化
- ✅ Numba JIT加速
- ✅ 16GB/32GB大內存

### Q: 可以商業使用嗎？

**A:** 請查看LICENSE文件。系統本身供個人研究使用，實盤交易需自負風險。

### Q: 如何報告bug？

**A:**
1. 檢查是否已有相同issue
2. 提供詳細的錯誤信息
3. 說明復現步驟
4. 附上相關log

### Q: 如何貢獻代碼？

**A:**
1. Fork項目
2. 創建feature分支
3. 遵循DEVELOPMENT_GUIDE.md規範
4. 提交Pull Request

---

## 性能指標

### 目標性能

| 功能 | 目標 | 當前 |
|------|------|------|
| 案例搜索 | < 10 秒/1000 個標的 | ✅ 8 秒 |
| K 線下載 | < 30 秒/1000 個案例 | ✅ 已完成 |
| IC 特徵篩選 | < 2 秒/200 features × 10K | ✅ 已達標（超標 4 倍） |
| XGBoost/LightGBM 訓練 | < 30 秒/案例 | ✅ 已完成 |
| 圖表渲染 | 60fps 流暢 | ✅ 已完成 |

### 優化策略

- **向量化** > Numba > 並行 > Python循環
- **HDF5壓縮** 減少存儲空間
- **智能緩存** 避免重複計算
- **分批處理** 避免內存溢出

---

## 致謝

### 核心技術

- [FastAPI](https://fastapi.tiangolo.com/) - 現代化Python Web框架
- [Next.js](https://nextjs.org/) - React框架
- [Lightweight Charts](https://tradingview.github.io/lightweight-charts/) - TradingView開源圖表
- [pandas](https://pandas.pydata.org/) - 數據分析
- [Optuna](https://optuna.org/) - 超參數優化
- [XGBoost](https://xgboost.readthedocs.io/) - 機器學習（分類模型）
- [LightGBM](https://lightgbm.readthedocs.io/) - 機器學習（雙引擎）

### 靈感來源

- QuantConnect - 量化研究平台
- Numerai - 數據科學競賽
- TradingView - 圖表分析

---

## 聯繫方式

- **項目維護**: [GitHub Issues](https://github.com/your-username/quantitative_trading_system/issues)
- **功能建議**: [GitHub Discussions](https://github.com/your-username/quantitative_trading_system/discussions)
- **文檔問題**: 在相關文檔中提issue

---

## 許可證

本項目採用 [MIT License](LICENSE)

---

## 更新日誌

### v0.5.0 (2026-02-14) — Phase 3.7 雙引擎 ML 系統

**新功能**：
- ✅ LightGBM + XGBoost 雙引擎訓練系統
- ✅ IModelTrainer Protocol 架構（8 個方法）
- ✅ 模型對比系統（A/B 測試 + 共識率）
- ✅ 四維參數系統（YAML/Dict/NL/Optuna）
- ✅ 可插拔 Optuna 目標函式
- ✅ 前端雙引擎對比 UI（6 個新元件）
- ✅ 10 個新 API 端點
- ✅ 160+ 測試覆蓋

### v0.4.0 (2026-02-12) — IC Gatekeeper + Feature Factory

**新功能**：
- ✅ IC 八階段篩選管線（159 tests, 100% coverage）
- ✅ Feature Factory 7 層 Pipeline（6514 特徵自動生成）
- ✅ 模型驗證子系統（CV/OOT/PSI/Rolling AUC/SHAP）

### v0.3.0 (2026-02-05) — 架構解耦 V4

**改進**：
- ✅ 7 條解耦規則全部通過
- ✅ Protocol 注入 + Factory 模式
- ✅ KlineDataService 統一資料存取層

### v0.2.0 (2026-01-09) — Optuna + XGBoost 分析

**新功能**：
- ✅ Optuna 參數優化（5 種 Sampler、WebSocket）
- ✅ XGBoost 分析系統（21 個端點）
- ✅ 9 個視覺化元件

### v0.1.0 (2025-09-30) — Case Search 系統

**新功能**：
- ✅ Case Search 系統完整實現
- ✅ 20 參數搜索框架
- ✅ 正反例採樣策略
- ✅ Web 界面和 API

---

<div align="center">

**⭐ 如果這個項目對你有幫助，請給個Star！⭐**

Made with ❤️ and 🤖 (Claude Code CLI)

</div>