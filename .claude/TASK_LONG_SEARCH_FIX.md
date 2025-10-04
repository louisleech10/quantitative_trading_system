# 長時間搜索超時修復任務

## 任務目標
修復ALL_USDT搜索時前端超時問題,實現進度追蹤機制

## 背景
- 用戶使用ALL_USDT搜索2025/01/01-2025/10/04時出現超時
- 後端成功處理(1506秒, 13049案例)但前端超時
- 錯誤: ERR_NETWORK_IO_SUSPENDED, TypeError: Failed to fetch

## 修改檔案清單

### 1. api/services/standalone_search_service.py
**位置**: `_run_search_task`方法
**目標**: 添加進度更新邏輯

需要改動的地方:

_run_search_task方法中添加進度更新邏輯
每處理N個symbol更新一次TaskProgress
記錄當前處理的symbol和進度百分比

建議給CLI的指引:
在_run_search_task方法中:
1. 計算總symbol數量
2. 每處理10個symbol後,調用task_manager.update_task_progress()
3. 傳入: current=已處理數, total=總數, symbol=當前symbol
4. 確保在搜索完成前定期更新

**修改重點**:
```python
# 在symbol處理循環中添加
total_symbols = len(symbols)
for idx, symbol in enumerate(symbols):
    # ... 處理邏輯 ...
    
    # 每10個symbol更新一次進度
    if (idx + 1) % 10 == 0 or (idx + 1) == total_symbols:
        self.task_manager.update_task_progress(
            task_id=task_id,
            current=idx + 1,
            total=total_symbols,
            description=f"處理交易對中...",
            symbol=symbol
        )

2. frontend/src/lib/api.ts
**位置**: executeTwoStageSearch方法
**目標**: 實現輪詢機制替代長時間等待

需要改動的地方:

修改executeTwoStageSearch方法
不再直接等待完整響應,改為輪詢
使用waitForTaskCompletion輔助方法

建議給CLI的指引:
修改executeTwoStageSearch方法:
1. 啟動搜索後立即返回(不等待完整響應)
2. 使用setInterval每2秒調用getTaskStatus
3. 檢查status是否為'completed'
4. 完成後調用getTaskResult獲取結果
5. 超時設定為10分鐘(600秒)
6. 記得clearInterval避免內存洩漏

**修改重點**:
typescript// 不直接等待完整響應
const response = await this.executePositiveSearch(request, operators, rangeValues);
const taskId = response.data.task_id;

// 使用輪詢等待完成
const pollInterval = setInterval(async () => {
  const status = await this.getTaskStatus(taskId);
  
  if (status.data.status === 'completed') {
    clearInterval(pollInterval);
    // 獲取結果
  } else if (status.data.progress) {
    // 更新進度顯示
    onProgress?.(status.data.progress);
  }
}, 2000); // 每2秒檢查一次

3. frontend/src/app/search/page.tsx
位置: 搜索執行部分
目標: 實現進度顯示UI

需要改動的地方:

添加進度狀態管理(useState)
在輪詢過程中更新進度顯示
顯示當前symbol和完成百分比

建議給CLI的指引:
在搜索執行時:
1. 添加useState管理進度: [progress, setProgress]
2. 在輪詢getTaskStatus時,提取progress資訊
3. 更新UI顯示: "處理中... X/Y個symbol (當前: BTCUSDT)"
4. 顯示進度條(使用percentage)
5. 保留現有的setCurrentStage邏輯

修改重點:
typescriptconst [searchProgress, setSearchProgress] = useState({
  current: 0,
  total: 0,
  symbol: '',
  percentage: 0
});

// 在輪詢時更新
onProgress: (progress) => {
  setSearchProgress(progress);
  setCurrentStage(
    `處理中... ${progress.current}/${progress.total} (${progress.percentage.toFixed(1)}%) - ${progress.symbol}`
  );
}

4. momentum/DataExtraction/case_search_engine.py
位置: search_cases方法
目標: 優化batch_size

需要改動的地方:

search_cases方法中的批量處理邏輯
增加batch_size默認值
添加進度回調支持

建議給CLI的指引:
優化search_cases方法:
1. 將batch_size默認值從1改為10
2. 添加progress_callback參數
3. 每處理一批symbol後調用callback
4. callback傳入: processed_count, total_count, current_symbol

修改重點:
pythonasync def search_cases(
    self,
    config: SearchConfiguration,
    symbols: List[str],
    batch_size: int = 10,  # 改為10
    progress_callback: Optional[Callable] = None,  # 新增
    save_results: bool = True
):
    # ... 處理邏輯 ...
    
    # 調用進度回調
    if progress_callback:
        progress_callback(processed_count, len(symbols), symbol)

5. api/services/standalone_task_manager.py
修改目的: 確保TaskProgress正確更新
檢查事項:

update_task_progress方法是否正常工作
TaskProgress的percentage計算是否正確
是否支持symbol和description更新

建議給CLI的指引:
確認StandaloneTaskManager:
1. update_task_progress方法支持所有TaskProgress欄位
2. 確保thread-safe(使用lock)
3. 驗證percentage計算: (current/total)*100
4. 支持estimated_remaining_seconds計算