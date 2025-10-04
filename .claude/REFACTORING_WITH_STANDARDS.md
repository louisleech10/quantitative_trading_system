# 代碼重構與規範整合指南

## 核心原則

**不能只追求速度，忽略代碼質量**
- ❌ 錯誤：寫出快速但混亂的代碼
- ✅ 正確：寫出快速且符合規範的代碼

## 重構檢查清單

### 每個文件重構時必須檢查

#### 1. Ultra Think三步驟驗證
重構前：

分析現有代碼的問題
列出優化To-do List
實施優化並驗證

重構後：

Review優化後的代碼
列出剩餘問題清單
二次優化


#### 2. 數據真實性檢查
```python
# ❌ 錯誤：硬編碼
DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT']

# ✅ 正確：從配置或API獲取
def get_default_symbols():
    return config.get('default_symbols') or \
           data_loader.get_symbols_list()[:10]
3. 錯誤處理完整性
python# ❌ 錯誤：沒有錯誤處理
def process_symbol(symbol):
    data = api.get_klines(symbol)
    return calculate(data)

# ✅ 正確：完整錯誤處理
async def process_symbol(symbol: str) -> Optional[List[CaseData]]:
    try:
        data = await api.get_klines(symbol)
        if data is None or len(data) == 0:
            logger.warning(f"No data for {symbol}")
            return None
        return calculate(data)
    except APIError as e:
        logger.error(f"API error for {symbol}: {e}", exc_info=True)
        return None
    except CalculationError as e:
        logger.error(f"Calculation error for {symbol}: {e}")
        return None
4. Log規範檢查
python# ❌ 錯誤：log太多或太少
for symbol in symbols:
    logger.info(f"Processing {symbol}")  # 循環內大量log
    process(symbol)

# ✅ 正確：適當的log
logger.info(f"開始處理 {len(symbols)} 個symbol")
for idx, symbol in enumerate(symbols):
    if (idx + 1) % 50 == 0:  # 每50個才log一次
        logger.info(f"進度: {idx+1}/{len(symbols)}")
    process(symbol)
logger.info("處理完成")
5. 類型提示
python# ❌ 錯誤：沒有類型提示
def search_cases(symbols, config, start_date):
    ...

# ✅ 正確：完整類型提示
async def search_cases(
    symbols: List[str],
    config: SearchConfiguration,
    start_date: datetime
) -> List[CaseData]:
    ...
6. 性能考慮（M1優化）
python# ❌ 錯誤：Python循環
results = []
for row in df.iterrows():
    if row['price_change'] > threshold:
        results.append(row)

# ✅ 正確：向量化
results = df[df['price_change'] > threshold]
重構順序
Phase 1: 代碼審計（1天）
任務：
1. 閱讀所有搜索相關代碼
2. 列出不符合規範的地方
3. 列出性能瓶頸
4. 製作詳細的問題清單

產出：
- AUDIT_REPORT.md（審計報告）
- 優先級排序的問題列表
Phase 2: 規範化重構（3天）
優先順序：
1. 消除假數據和硬編碼
2. 完善錯誤處理
3. 規範log記錄
4. 添加類型提示
5. 補充註釋

每個文件重構後：
- 立即測試
- Git commit
- 更新文檔
Phase 3: 性能優化（5-7天）
在規範化基礎上進行性能優化：
1. 數據緩存系統
2. 並行處理架構
3. 向量化計算
4. 智能預篩選

每個優化後：
- 性能測試
- 對比優化前後
- Git commit
代碼審查標準
每次提交前檢查

 沒有假數據/硬編碼
 錯誤處理完整（try-except-finally）
 log記錄適當（不多不少）
 變量命名清晰（不用a, b, c）
 有類型提示
 複雜邏輯有註釋
 沒有重複代碼（DRY原則）
 性能合理（用profiler驗證）
 通過所有測試
 文檔已更新

實例：重構case_search_engine.py
Before（不符合規範）
pythondef search_cases(symbols, config):
    # 沒有類型提示
    # 沒有錯誤處理
    # 硬編碼batch_size
    results = []
    for symbol in symbols:  # 串行處理
        data = self.loader.get_klines(symbol)  # 沒錯誤處理
        cases = self._find(data)
        results.extend(cases)
    return results
After（符合規範且優化）
pythonasync def search_cases(
    self,
    symbols: List[str],
    config: SearchConfiguration,
    batch_size: Optional[int] = None,
    progress_callback: Optional[Callable] = None
) -> List[CaseData]:
    """
    搜索符合條件的交易案例
    
    Args:
        symbols: 交易對列表
        config: 搜索配置
        batch_size: 並行處理批次大小，None=自動偵測
        progress_callback: 進度回調函數
    
    Returns:
        符合條件的案例列表
    
    Raises:
        ValueError: 參數無效
        DataLoaderException: 數據加載失敗
    """
    # 參數驗證
    if not symbols:
        raise ValueError("symbols不能為空")
    
    # 自動偵測最佳batch_size
    if batch_size is None:
        batch_size = self._calculate_optimal_batch_size()
    
    logger.info(f"開始搜索: {len(symbols)}個symbol, batch_size={batch_size}")
    
    # 並行處理
    all_results = []
    try:
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            
            # 並行處理這批symbol
            tasks = [self._process_single_symbol(s, config) for s in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 處理結果和錯誤
            for symbol, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"處理{symbol}失敗: {result}")
                elif result:
                    all_results.extend(result)
            
            # 進度回調
            if progress_callback:
                progress_callback(
                    processed=min(i+batch_size, len(symbols)),
                    total=len(symbols)
                )
            
            # Log（每批次一次）
            logger.info(f"進度: {min(i+batch_size, len(symbols))}/{len(symbols)}")
        
        logger.info(f"搜索完成: 找到{len(all_results)}個案例")
        return all_results
        
    except Exception as e:
        logger.error(f"搜索失敗: {e}", exc_info=True)
        raise
    
def _calculate_optimal_batch_size(self) -> int:
    """根據系統資源自動計算最佳batch_size"""
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    # 保守策略：用70%的核心
    return max(1, int(cpu_count * 0.7))
成功標準
代碼質量指標

所有函數有類型提示：100%
所有外部調用有錯誤處理：100%
沒有硬編碼魔法數字：100%
關鍵邏輯有註釋：>80%

性能指標

4個symbol < 5秒
100個symbol < 30秒
500個symbol < 2分鐘
4000個symbol < 10分鐘

維護性指標

新增功能平均時間 < 1天
Bug修復平均時間 < 2小時
代碼覆蓋率 > 70%