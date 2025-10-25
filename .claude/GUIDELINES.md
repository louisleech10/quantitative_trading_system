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
├── DataExtraction/  # 數據獲取
├── Indicator/       # 指標計算
└── Analysis/        # 分析功能
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

- [ ] 沒有假數據/硬編碼
- [ ] 遵循 Ultra Think 三步驟
- [ ] 完整的錯誤處理
- [ ] 適當的日誌記錄
- [ ] 類型提示完整
- [ ] 變量命名清晰
- [ ] 關鍵邏輯有註釋
- [ ] 沒有重複代碼
- [ ] 性能合理（避免明顯瓶頸）
- [ ] Git commit message 符合規範

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