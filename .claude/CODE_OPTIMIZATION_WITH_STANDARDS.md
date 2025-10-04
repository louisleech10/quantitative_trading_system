# 基於規範的代碼優化計劃

## 核心原則
1. First Principle思考（速度是根本需求）
2. 遵循DEVELOPMENT_GUIDE.md所有規範
3. Ultra Think三步驟必須執行
4. 數據真實性絕不妥協

## 優化時必須遵守的規範

### 1. 數據真實性（最重要）
❌ 錯誤做法：
```python為了測試快速，用假數據
test_data = pd.DataFrame({'close': [100, 101, 102]})

✅ 正確做法：
```python即使在開發階段，也用真實緩存數據
test_data = cache_manager.get_cached_klines('BTCUSDT', start, end)

### 2. 完整的錯誤處理
每個並行任務都必須有錯誤處理：
```pythonasync def process_symbol_safe(symbol, config):
try:
return await process_symbol(symbol, config)
except APIError as e:
logger.error(f"API錯誤 {symbol}: {e}", exc_info=True)
return None  # 不讓單個失敗影響全局
except Exception as e:
logger.error(f"未預期錯誤 {symbol}: {e}", exc_info=True)
return None

### 3. 適當的LOG記錄
並行處理時的LOG策略：
- 每個batch開始/結束記錄INFO
- 單個symbol錯誤記錄ERROR
- 避免在循環內大量DEBUG log

### 4. 變量命名清晰
```python❌ 錯誤
def f(s, t):
return [x for x in s if x > t]✅ 正確
def filter_symbols_by_volume(symbols: List[str], min_volume_threshold: float):
return [symbol for symbol in symbols if get_volume(symbol) > min_volume_threshold]

### 5. 性能優化不違反規範
- 向量化操作仍需清晰命名
- Numba編譯的函數仍需類型提示
- 並行處理仍需錯誤處理

## 每個Phase的規範檢查清單

### Phase 0: 數據緩存系統
- [ ] 無假數據/硬編碼路徑
- [ ] 完整錯誤處理（網絡失敗、磁盤滿等）
- [ ] INFO級別log記錄關鍵操作
- [ ] 變量命名清晰（cache_manager不寫成cm）
- [ ] 類型提示完整
- [ ] 通過Ultra Think三步驟

### Phase 1: 並行處理
- [ ] 進程池資源正確釋放
- [ ] 單個任務失敗不影響整體
- [ ] 進度聚合邏輯清晰
- [ ] CPU核心數動態偵測（問題3相關）
- [ ] 通過Ultra Think三步驟

### Phase 2: 向量化計算
- [ ] Pandas操作可讀性高
- [ ] Numba函數有完整docstring
- [ ] 性能提升有benchmark證明
- [ ] 通過Ultra Think三步驟

### Phase 3: 智能預篩選
- [ ] 篩選條件透明化（問題4相關）
- [ ] 用戶可選擇關閉
- [ ] 記錄被過濾的symbol
- [ ] 通過Ultra Think三步驟

## Ultra Think檢查流程

每個功能開發必須經過：

**步驟1 - 初始生成**
- 實現核心邏輯
- 添加基本錯誤處理
- 記錄關鍵log

**步驟2 - 自我審查**
生成To-do List：
- [ ] 是否有假數據？
- [ ] 錯誤處理完整嗎？
- [ ] log記錄適當嗎？
- [ ] 變量命名清晰嗎？
- [ ] 性能合理嗎？
- [ ] 符合M1優化原則嗎？

**步驟3 - 優化重構**
根據To-do List逐項修正

## 代碼審查時的雙重標準

每次提交前檢查：
✅ 功能正確性
✅ 性能達標
✅ 規範遵循
✅ 無假數據
✅ 錯誤處理完整
✅ log適當
✅ 命名清晰