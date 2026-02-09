# 文件整理與技術債清理檢查清單

> **建立日期**: 2026-02-07  
> **目的**: 配合 REFACTOR_ARCHITECTURE_V4 完成後的文件同步與過時內容清理  
> **相關**: Phase 0 系統驗證完成後的文件維護

---

## 📋 檢查清單總覽

| 類別 | 項目數 | 完成數 | 狀態 |
|------|--------|--------|------|
| 🔄 需要同步更新 | 4 | 2 | 🔄 進行中 |
| 🗑️ 建議刪除/歸檔 | 8+ | 0 | ⏳ 待審查 |
| 📁 資料夾結構優化 | 3 | 0 | ⏳ 待討論 |
| **總計** | **15+** | **2** | **~13%** |

---

## 🔄 需要同步更新的文件

### 1. `docs/ARCHITECTURE.md` - 系統架構總覽

**狀態**: ✅ 已完成（v3.0, 2026-02-08）  
**優先級**: 🔴 高  
**預計工時**: 2-3 小時

#### 需要更新的內容
- [x] **Decoupling 架構變更** (from REFACTOR_ARCHITECTURE_V4)
  - 新增 `KlineDataService` 作為統一資料存取層
  - 更新 Service 層的職責劃分
  - 更新 API Route → Service → Storage 的呼叫流程圖
  
- [x] **新增模組說明**
  - `momentum/core/protocols.py` - IModelTrainer Protocol
  - `momentum/factories.py` - 模型工廠模式
  - 更新 `KlineStorage` 的職責描述

- [x] **移除過時描述**
  - 檢查是否有提及已刪除的模組
  - 更新檔案路徑（若有重新命名）

#### 驗證方法
- [x] 對照 REFACTOR_ARCHITECTURE_V4.md 的變更清單逐項檢查
- [x] 確認架構圖與當前程式碼目錄結構一致
- [x] 確認所有範例程式碼可執行

---

### 2. `docs/API_SPECIFICATION.md` - API 端點規格

**狀態**: ✅ 已完成（v3.0, 2026-02-08）  
**優先級**: 🟠 中  
**預計工時**: 1-2 小時

#### 需要確認的內容
- [x] 檢查 API 端點是否有變動（特別是 kline 相關）
- [x] 確認 Request/Response 模型與 `api/models/` 一致
- [x] 添加新端點說明（若有新增）
- [x] 更新錯誤碼說明（DataContinuityError 等）

#### 驗證方法
- [x] 對照 FastAPI `/docs` Swagger UI 的實際端點
- [x] 使用 Postman/curl 測試範例請求
- [x] 確認所有端點都有對應文件說明

---

### 3. `README.md` - 快速啟動指令

**狀態**: ⏳ 待驗證  
**優先級**: 🟠 中  
**預計工時**: 30 分鐘

#### 需要驗證的內容
- [ ] **後端啟動**
  ```bash
  python run_api.py  # 確認可正常啟動
  ```
- [ ] **前端啟動**
  ```bash
  cd frontend
  npm install
  npm run dev  # 確認可正常啟動
  ```
- [ ] **測試執行**
  ```bash
  pytest tests/ -v --tb=short  # 確認測試通過率
  ```
- [ ] **環境變數說明** - 檢查是否需要補充新的環境變數

#### 驗證方法
- [ ] 在全新環境（或 Docker）中依照 README 步驟執行
- [ ] 確認所有指令可執行且無錯誤
- [ ] 檢查依賴套件版本是否正確（requirements.txt, package.json）

---

### 4. `.github/copilot-instructions.md` - AI Agent 指令

**狀態**: ⏳ 待更新  
**優先級**: 🟡 低  
**預計工時**: 1 小時

#### 需要更新的內容
- [ ] **Phase 0 完成狀態**
  - 更新為「✅ 已完成」
  - 添加驗證結果摘要
  
- [ ] **XGBoost 儀表板問題**
  - 記錄已知問題（CV AUC Mean N/A, OOT 缺失等）
  - 添加處理策略（Phase 2 review 修復）

- [ ] **資料流範例更新**
  - 更新 KlineDataService 的使用範例
  - 更新 Service 層呼叫模式

#### 驗證方法
- [ ] 讓 AI Agent 依照更新後的指令執行簡單任務
- [ ] 確認指令清晰無歧義

---

## 🗑️ 建議刪除/歸檔的檔案與資料夾

### 審查原則
- **刪除標準**: 完全被正式文件取代、無參考價值、過時且無歷史意義
- **歸檔標準**: 有歷史參考價值但不常用

---

### 1. `Claude資料備份/` 資料夾

**狀態**: ⏳ 待審查  
**優先級**: 🟠 中  
**建議**: 🗂️ 歸檔到 `docs/archive/claude_backup/`

#### 審查項目
- [ ] 檢查內容是否已整合進正式文件:
  - `GUIDELINES.md` → 是否已合併到 `docs/DEVELOPMENT_GUIDE.md`?
  - `PATTERN_DISCOVERY_ROADMAP.md` → 是否已整合到主架構文件?
  - `PERFORMANCE_ARCHITECTURE.md` → 是否已合併到 `docs/ARCHITECTURE.md`?
  - `SESSION_*.md` → 是否有歷史參考價值?

#### 行動方案
1. 逐一檢查每個檔案
2. 已整合的內容 → 刪除
3. 有參考價值但不常用 → 移至 `docs/archive/`
4. Session 記錄 → 保留最近 3 個月，其餘刪除

---

### 2. `Fix Doc/` 資料夾

**狀態**: ⏳ 待審查  
**優先級**: 🟠 中  
**建議**: 🗑️ 刪除（若為臨時修復記錄）

#### 審查項目
- [ ] 檢查內容類型
- [ ] 確認是否為臨時記錄
- [ ] 若有重要修復記錄，整合到 CHANGELOG 或 troubleshooting 文件

#### 行動方案
- 臨時記錄 → 刪除
- 重要修復 → 整合後刪除
- 持續使用 → 重新命名為 `docs/fixes/` 並整理結構

---

### 3. `sessions/` 資料夾

**狀態**: ⏳ 待審查  
**優先級**: 🟢 低  
**建議**: 🗑️ 刪除舊 session，保留近期

#### 審查項目
- [ ] 檢查 session 檔案數量與日期
- [ ] 確認是否有重要決策記錄

#### 行動方案
- 保留最近 1 個月的 session
- 其餘移至 `.gitignore` 或直接刪除
- 重要決策記錄整合到正式文件

---

### 4. `verification_data/` 資料夾

**狀態**: ⏳ 待審查  
**優先級**: 🟠 中  
**建議**: 🔄 與 `test_results/` 合併

#### 審查項目
- [ ] 對比 `verification_data/` 與 `test_results/` 的內容
- [ ] 確認是否有重複
- [ ] 確認資料夾用途差異

#### 行動方案
- 若內容重複 → 合併到 `test_results/`
- 若用途不同 → 在 README 中說明差異
- 統一測試結果輸出路徑

---

### 5. Legacy 測試檔案（專案根目錄）

**狀態**: ⏳ 待審查  
**優先級**: 🟠 中  
**建議**: 🗑️ 刪除（若已被正式測試取代）

#### 待審查檔案清單
- [ ] `simple_test.py` - 是否為早期測試檔案?
- [ ] `debug_price_change_method.py` - 是否為臨時除錯檔案?
- [ ] `test_price_change_calculation.py` - 是否已整合到 `tests/` 中?
- [ ] `verify_price_change_csv.py` - 是否為一次性驗證腳本?

#### 行動方案
對每個檔案:
1. 檢查 `git log` 確認最後修改時間
2. 檢查是否有對應的正式測試
3. 若已被取代 → 刪除
4. 若仍在使用 → 移至 `tests/legacy/` 並註記原因

---

### 6. `conftest.py` (根目錄)

**狀態**: ⏳ 待審查  
**優先級**: 🟢 低  
**建議**: 🔍 確認用途

#### 審查項目
- [ ] 確認是否與 `tests/conftest.py` 重複
- [ ] 檢查是否有被使用（pytest fixtures）

#### 行動方案
- 若未使用 → 刪除
- 若與 `tests/conftest.py` 重複 → 合併
- 若有特殊用途 → 添加註解說明

---

### 7. `market_data/` 資料夾

**狀態**: ⏳ 待審查  
**優先級**: 🟡 低  
**建議**: 🔍 確認用途與 `data_cache/` 差異

#### 審查項目
- [ ] 確認資料夾內容
- [ ] 對比 `data_cache/` 的用途
- [ ] 檢查是否有程式碼引用

#### 行動方案
- 若與 `data_cache/` 重複 → 刪除
- 若為原始下載暫存 → 添加 README 說明
- 若未使用彈 gitignore

---

### 8. `results/` 和 `search_results/` 資料夾

**狀態**: ⏳ 待審查  
**優先級**: 🟡 低  
**建議**: 🔄 統一命名或合併

#### 審查項目
- [ ] 確認兩個資料夾的用途差異
- [ ] 檢查是否有重複內容
- [ ] 確認程式碼中的輸出路徑設定

#### 行動方案
- 若用途相同 → 合併為 `results/`
- 若用途不同 → 在 README 中說明差異
- 統一輸出路徑配置（config.py 或 settings）

---

## 📁 資料夾結構優化建議

### 1. 統一測試結果輸出位置

**問題**: `test_results/` vs `verification_data/` vs `results/`

**建議方案**:
```
test_results/              # 自動化測試輸出
├── unit/                 # 單元測試結果
├── integration/          # 整合測試結果
├── continuity/           # 資料連續性驗證
└── performance/          # 效能測試結果

verification_data/        # (刪除，合併到上述)
results/                  # (重新命名為 backtest_results/)
search_results/           # (重新命名為 case_search_results/)
```

---

### 2. 整合備份與歸檔文件

**問題**: `Claude資料備份/` vs `sessions/` vs 潛在的其他備份

**建議方案**:
```
docs/
├── archive/              # 歷史文件歸檔
│   ├── claude_backup/   # Claude 備份內容
│   ├── sessions/        # 重要 session 記錄
│   └── deprecated/      # 過時但有參考價值的文件
├── ... (其他正式文件)
```

---

### 3. 集中臨時開發檔案

**問題**: 根目錄散落臨時測試/除錯檔案

**建議方案**:
```
temp/                     # 臨時開發檔案 (加入 .gitignore)
├── debug/               # 除錯用腳本
├── experiments/         # 實驗性程式碼
└── scratch/             # 草稿與筆記

.gitignore 添加:
temp/
*.debug.py
*.scratch.py
```

---

## ✅ 執行計劃

### Phase 1: 文件同步更新（Week 1）
- [x] Day 1-2: 更新 `ARCHITECTURE.md`
- [x] Day 3: 更新 `API_SPECIFICATION.md`
- [ ] Day 4: 驗證 `README.md`
- [ ] Day 5: 更新 `.github/copilot-instructions.md`

### Phase 2: 檔案審查與歸檔（Week 2）
- [ ] Day 1: 審查 `Claude資料備份/`
- [ ] Day 2: 審查 `Fix Doc/`, `sessions/`
- [ ] Day 3: 審查 `verification_data/`, legacy 測試檔案
- [ ] Day 4: 審查 `market_data/`, `results/`, `search_results/`
- [ ] Day 5: 執行刪除/歸檔動作

### Phase 3: 結構優化（Week 3）
- [ ] Day 1: 統一測試結果輸出
- [ ] Day 2: 整合備份與歸檔
- [ ] Day 3: 建立 `temp/` 結構
- [ ] Day 4: 更新 `.gitignore`
- [ ] Day 5: 文件更新（添加 README 說明）

---

## 📊 進度追蹤

### 完成標準
- [ ] 所有「需要同步更新」的文件完成修改
- [ ] 所有「建議刪除」的項目完成審查並決策
- [ ] 所有「結構優化」方案完成實施
- [ ] README 包含最新的資料夾結構說明
- [ ] 更新 `.gitignore` 排除臨時檔案

### 驗證方法
- [ ] 全新環境依照 README 可成功啟動系統
- [ ] 所有文件交叉引用正確（無 404 連結）
- [ ] 測試套件可正常執行
- [ ] Git 歷史乾淨（無誤刪重要檔案）

---

## 🔗 相關文件

- [主架構文件](IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md)
- [未來優化清單](../未來優化清單.md)
- [重構記錄](REFACTOR_ARCHITECTURE_V4.md)
- [系統架構](ARCHITECTURE.md)

---

**注意**: 
1. 刪除任何檔案前請先確認 `git log` 和 `git blame`
2. 重要決策記錄應保存到正式文件中
3. 大量刪除前建議先建立 Git tag: `git tag -a pre-cleanup -m "Before doc cleanup"`
