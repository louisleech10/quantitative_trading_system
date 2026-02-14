# 開發指導原則

**快速參考** - Claude Code CLI 每次工作必讀

---

## 🚨 核心原則（絕不違反）

### 0. 一切都要從First Principle開始思考

### 1. 數據真實性 - 最重要！
```
❌ 嚴禁：假數據、虛擬數據、硬編碼數值
✅ 必須：來自真實API、配置文件、實際計算
```

**範例**：
```python
# ❌ 錯誤 - 硬編碼
symbols = ["BTCUSDT", "ETHUSDT"]

# ✅ 正確 - 從配置讀取
symbols = config.get_symbols()

# ❌ 錯誤 - 假數據
return {"win_rate": 0.65, "trades": 100}

# ✅ 正確 - 真實計算
return calculate_real_metrics(trade_history)
```

---

### 2. First Principle思考和Ultra Think 三步驟

**思考邏輯要遵守First Principle**
**所有代碼生成必須遵循**：

```
步驟 1: 生成初版代碼
        ↓
步驟 2: 自我審查步驟1生成的代碼是否有錯誤和可優化之處(必做)+ 列出優化 To-do List
        ↓
步驟 3: 根據 To-do List 生成最終優化版本
```

**不要跳過步驟2！** 即使看起來簡單的代碼。

---

### 3. 完整錯誤處理

```python
# ✅ 標準錯誤處理模板
try:
    result = risky_operation()
    logger.info(f"操作成功: {result}")
    return result
    
except SpecificError as e:
    # 可重試錯誤
    logger.warning(f"可重試錯誤: {e}")
    return retry_logic()
    
except Exception as e:
    # 不可重試錯誤
    logger.error(f"嚴重錯誤: {e}", exc_info=True)
    raise
```

**必須區分**：
- 可重試錯誤（網路timeout、API限流）
- 不可重試錯誤（數據格式錯誤、邏輯錯誤）

---

### 4. 適當的日誌記錄

```python
# ✅ 關鍵操作記錄
logger.info(f"開始搜索: {len(symbols)} 個標的")

# ✅ 錯誤記錄（包含 exc_info）
logger.error(f"搜索失敗: {e}", exc_info=True)

# ❌ 避免：循環內大量log
for symbol in symbols:
    logger.info(f"處理 {symbol}")  # 太多！

# ✅ 改為：批次記錄
logger.info(f"處理進度: {i}/{total}")
```

---

## 🛠️ 技術規範

### Python 代碼風格

```python
# ✅ 類型提示
def calculate_metrics(
    data: pd.DataFrame,
    window: int = 20
) -> Dict[str, float]:
    ...

# ✅ 文檔字串
def search_cases(config: SearchConfig) -> List[Case]:
    """搜索符合條件的交易案例
    
    Args:
        config: 搜索配置對象
        
    Returns:
        符合條件的案例列表
        
    Raises:
        ValueError: 當配置無效時
    """
    ...

# ✅ 向量化優於循環
# ❌
results = []
for row in df.iterrows():
    results.append(calculate(row))

# ✅  
results = df.apply(calculate, axis=1)
```

---

### 性能優化（M1 Mac）

**優先級順序**：
```
1. 向量化操作（pandas/numpy）
2. Numba JIT 編譯
3. 多進程並行（8核）
4. Python 原生循環（最後選擇）
```

**範例**：
```python
# ✅ 向量化
df['returns'] = df['close'].pct_change()

# ✅ Numba加速關鍵計算
@numba.jit(nopython=True)
def fast_calculation(arr):
    ...

# ✅ 並行處理（8核M1）
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor(max_workers=8) as executor:
    results = list(executor.map(process_symbol, symbols))
```

---

### Git 提交規範

```bash
# 格式：<type>: <subject>

feat: 添加K線批量下載功能
fix: 修復搜索API速率限制錯誤
docs: 更新API文檔添加新端點
refactor: 重構指標計算引擎為類
perf: 優化DataFrame操作使用向量化
test: 添加搜索引擎單元測試
chore: 更新依賴版本
```

---

## 📐 系統架構原則

### API 設計
- RESTful風格
- 統一的響應格式
- 清晰的錯誤碼
- API版本控制（/api/v1）

### 數據流向
```
用戶請求 → FastAPI → Service層 → Core業務邏輯 → 數據源
         ↓
     統一響應格式
```

### 文件組織
```
api/          # FastAPI 層（路由、模型）
├── routes/   # API端點
├── services/ # 業務邏輯
└── models/   # 數據模型

momentum/     # 核心業務邏輯
├── core/            # Protocol、Config、Contracts
├── factories.py     # 統一工廠創建函式
├── DataExtraction/  # 數據獲取
├── Indicator/       # 指標計算
├── Analysis/        # 分析功能（XGBoost + LightGBM 雙引擎）
├── FeatureEngineering/ # 特徵工程
└── Optimization/    # Optuna 參數優化 + 可插拔 Objective
```

### Protocol 與 Factory 架構模式（Phase 3.7）

新增 ML 引擎或跨 Domain 依賴必須使用 Protocol + Factory：

```python
# ✅ 正確：透過 Protocol 協議定義引擎介面
from momentum.core.protocols import IModelTrainer

class MyService:
    def __init__(self, trainer: IModelTrainer):  # 注入 Protocol
        self.trainer = trainer

# ✅ 正確：透過 Factory 創建實例
from momentum.factories import create_model_trainer
trainer = create_model_trainer("lightgbm")

# ❌ 錯誤：直接實例化引擎
from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer
analyzer = LightGBMAnalyzer()  # 違反 Rule 3
```

---

## 🎯 何時讀取哪個文檔？

### 每天開始工作
```bash
# Claude Code CLI 自動讀取 .claude/
> 早安，繼續昨天的工作
```

### 開始新功能
```bash
> 我要開發圖表功能，請讀取：
  docs/ARCHITECTURE.md 搜索"圖表系統"
```

### 需要API規範
```bash
> 請讀取 docs/API_SPECIFICATION.md
```

### 不確定設計決策
```bash
> 我們之前怎麼設計的？
# 使用 Project Knowledge 自動搜索相關文檔
```

### 忘記開發規範
```bash
> 這樣寫符合規範嗎？讀 docs/DEVELOPMENT_GUIDE.md
```

---

## 📝 Session Status 管理

### 什麼是 Session Status？

Session Status 是**細粒度的會話追蹤系統**，用於：
- **跨對話追蹤**：同一任務可能跨多個對話串
- **跨 AI 協作**：在 Claude 和 Copilot 間無縫切換
- **PLAN 執行追蹤**：每個 PLAN 從提出到完成的完整記錄
- **問題可追溯**：debug 過程和決策理由完整保存

### 核心原則

```
⚠️ 強制規則：每次提出 PLAN 前，必須先更新 Session Status
⚠️ 強制規則：開始執行、完成、遇到阻塞時，必須更新 Session Status
⚠️ 強制規則：切換 AI 前，必須記錄切換點和原因
```

### 檔案命名

```
SESSION_Phase[X].[Y].md
```

**範例**:
- `SESSION_Phase2.3.md` - Phase 2 任務 2.3（當前進行中）
- `sessions/SESSION_Phase2.1_ARCHIVED.md` - 已完成並歸檔

### 六大更新時機

| 時機 | 必須動作 | 範例 |
|------|----------|------|
| **1. 提出 PLAN** | 記錄到計劃列表（PLANNED） | 新增「實作縮放功能」 |
| **2. 開始執行** | PLANNED → IN_PROGRESS | 標記「正在實作縮放」 |
| **3. 完成任務** | IN_PROGRESS → COMPLETED + DoD 檢查 | 標記「縮放功能完成」 |
| **4. 遇到阻塞** | IN_PROGRESS → BLOCKED + 原因 | 「Token limit reached」 |
| **5. 切換 AI** | 記錄切換點 + 更新負責 AI | Claude → Copilot |
| **6. Debug** | DEBUG_START/END + 問題追蹤 | 記錄 Bug 和解決方案 |

### 狀態機

```
PLANNED → IN_PROGRESS → COMPLETED
              ↓
           BLOCKED (可恢復)
```

### 快速開始

```bash
# 1. 創建新 Session
> 複製 .claude/SESSION_TEMPLATE.md 為 SESSION_Phase2.3.md

# 2. 開始工作時讀取
> 讀取 .claude/SESSION_Phase2.3.md 和 SESSION_GUIDELINES.md

# 3. 提出 PLAN 前更新
> 在 Session Status 記錄這個 PLAN

# 4. 完成後歸檔
> 移動到 .claude/sessions/ 並更新 STATUS.md
```

### 詳細規範

完整的使用規範請參閱：[SESSION_GUIDELINES.md](SESSION_GUIDELINES.md)

---

## 🤖 工作流程自動化（重要！）

### 核心原則
應該是**全自動運作**，不應該反覆提醒用戶。

### 自動執行規則

#### 1️⃣ 改代碼文件 - 直接改，無需提示
```
✅ 情況：修改 Python/TypeScript/JSON 等代碼文件
✅ 做法：直接使用 replace_string_in_file 改動
✅ 結果：不出現 approve 按鈕
✅ 提示：完全無需提示用戶

❌ 錯誤做法：
  - 先問用戶要不要改
  - 改完後還問用戶要不要提交
  - 每次對話都重複說明工具用法
```

#### 2️⃣ 執行必要命令 - 自動執行，勿需提醒
```
✅ 情況：git commit/push、測試、運行程序等
✅ 做法：使用 run_in_terminal 直接執行
✅ 結果：自動出現 approve，直接通過，無需用戶確認
✅ 提示：完成後直接報告結果，不要反覆提醒

❌ 錯誤做法：
  - 詢問「要我幫你執行嗎？」
  - 一遍遍解釋為什麼需要 approve
  - 等待用戶手動提交（應該自動做）
```

#### 3️⃣ 工作完成 - 自動更新文件
```
✅ 情況：工作結束時
✅ 做法：
   1. 自動 git add/commit/push
   2. 自動更新 .claude/STATUS.md 記錄完成工作
   3. 自動更新 SESSION 文件（如進行中）
✅ 結果：用戶無需手動操作
✅ 提示：不要等用戶說「更新一下狀態」

❌ 錯誤做法：
  - 「要我更新 STATUS.md 嗎？」
  - 工作完成後等待用戶指示推送
  - 完成後不更新任何記錄
```

#### 4️⃣ 切換 Model - 直接接工作
```
✅ 情況：用戶切換到新 AI（Claude ↔ Copilot）
✅ 做法：
   1. 自動讀取最新的 SESSION_Phase*.md
   2. 自動讀取 STATUS.md 瞭解進度
   3. 自動讀取 GUIDELINES.md 和規範
   4. 直接接工作，無需用戶重新說明
✅ 結果：新 AI 無縫接手，用戶無感
✅ 提示：不要問「請告訴我之前做了什麼」

❌ 錯誤做法：
  - 「現在換我了，請先說一遍之前的工作」
  - 「我需要重新開始」
  - 要求用戶重新解釋需求
```

#### 5️⃣ 每次對話開始 - 無需額外提示
```
✅ 情況：開始新對話或新工作
✅ 做法：
   1. 自動讀取 .claude/STATUS.md 瞭解項目狀態
   2. 自動讀取 SESSION_Phase*.md 瞭解當前任務
   3. 自動讀取 GUIDELINES.md 遵循規範
   4. 如有工具使用說明，記住一次即可，不重複說明
✅ 結果：直接進入工作
✅ 提示：無需每次都解釋「replace_string_in_file 是什麼」

❌ 錯誤做法：
  - 每次對話都問「你知道 replace_string_in_file 嗎？」
  - 重複解釋為什麼不用 terminal
  - 詢問「要我自動改嗎？」而不是直接改
```

### 實施檢查清單

工作完成前確保：

- [ ] 代碼改動是否直接用 replace_string_in_file（不用 terminal）
- [ ] 必要命令是否自動執行（git/test/run）
- [ ] 工作完成是否自動更新 STATUS.md 和 SESSION
- [ ] 沒有反覆提醒用戶相同的內容
- [ ] 沒有要求用戶進行重複操作（如 approve）
- [ ] 切換 AI 時是否無縫接手（讀取所有必要文件）
- [ ] 新對話開始時是否自動讀取上下文（無需用戶再說）

### 為什麼這很重要？

```
用戶友好度：
  ❌ 每次對話都提醒工具用法 = 低效
  ✅ 一次學會，自動執行 = 高效

協作效率：
  ❌ 反覆確認「要不要做？」= 浪費時間
  ✅ 直接做，報告進度 = 高效

AI 協作：
  ❌ 每次切換 AI 都要重複說明 = 無法平滑協作
  ✅ 自動讀取上下文，無縫接手 = 真正的協作
```

---

## ⚠️ 常見陷阱

### 1. 過度優化（Overfitting）
```
❌ 回測勝率 95%（太好了，可疑）
✅ 回測勝率 55-65%（合理）

❌ 100個參數的模型
✅ 10-20個關鍵參數

❌ 只在訓練集驗證
✅ 嚴格的訓練/驗證/測試分離
```

### 2. 數據洩漏
```
❌ 使用未來數據計算當前信號
✅ 嚴格的時間序列切分

❌ 測試集參與參數優化
✅ 測試集只用於最終驗證（一次）
```

### 3. 性能問題
```
❌ 循環處理 DataFrame
✅ 使用向量化操作

❌ 沒有緩存重複計算
✅ 智能緩存機制

❌ 同步處理大量API請求
✅ 異步批量處理
```

---

## 🔍 代碼審查檢查清單

提交前必須檢查：

- [ ] 是否從First Principle開始思考
- [ ] 沒有假數據/硬編碼
- [ ] 遵循 Ultra Think 三步驟
- [ ] 遵循 Ultra Think步驟 1: 生成初版代碼
- [ ] 遵循 Ultra Think步驟 2: 自我審查步驟1生成的代碼是否有錯誤和可優化之處(必做)+ 列出優化 To-do List
- [ ] 遵循 Ultra Think步驟 3: 根據 To-do List 生成最終優化版本
- [ ] 完整的錯誤處理
- [ ] 適當的日誌記錄
- [ ] 類型提示完整
- [ ] 變量命名清晰
- [ ] 關鍵邏輯有註釋
- [ ] 沒有重複代碼
- [ ] 性能合理（避免明顯瓶頸）
- [ ] Git commit message 符合規範
- [ ] Session Status 已更新（如適用）

---

## 🚀 快速命令參考

### 開發相關
```bash
# 啟動後端
python run_api.py

# 啟動前端
cd frontend && npm run dev

# 執行測試
pytest tests/

# 代碼格式化
black . && isort .
```

### Git 相關
```bash
# 查看狀態
git status

# 提交變更
git add .
git commit -m "feat: 添加XXX功能"
git push

# 查看日誌
git log --oneline -10
```

### Claude Code CLI 相關
```bash
# 啟動（自動讀取 .claude/）
claude

# 帶項目知識啟動
claude --project

# 常用指令
> 讀取 .claude/STATUS.md 和 TODO.md
> 更新 .claude/STATUS.md 記錄今天完成的工作
> 幫我生成 git commit message
```

---

## 💡 最佳實踐提醒

### 開發流程
1. **小步快跑**：每次只實現一個功能
2. **及早測試**：寫完立刻測試，不要積累
3. **頻繁提交**：功能可用就提交，不要等「完美」
4. **記錄問題**：發現bug立刻記錄到 TODO.md

### 溝通技巧（與 Claude Code CLI）
```
✅ 明確：「請實現批量下載K線數據的功能」
❌ 模糊：「做個下載功能」

✅ 具體：「修復搜索API在超過1000個標的時超時的問題」
❌ 籠統：「優化性能」

✅ 有上下文：「繼續昨天的圖表組件開發，現在實現縮放功能」
❌ 無上下文：「做個縮放」
```

---

**記住**：
- 數據真實性永遠第一優先
- 要從FIRST Principle思考
- Ultra Think 三步驟不能跳過
- 錯誤處理和日誌記錄很重要
- 性能優化要有實際測量數據支撐
- 代碼審查清單每次提交前必查

**本文檔應該**：
- 每天工作前快速瀏覽
- 不確定時查閱相應章節
- 發現新問題時及時更新