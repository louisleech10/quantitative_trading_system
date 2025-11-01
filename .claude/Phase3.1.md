## 任務3.1: 多數據源指標計算引擎 - 開發TODO（精簡版）

### 開發策略
**4個連續的可交付模塊，每個都是完整功能**

---

### 📦 模塊1: BaseIndicator基礎架構

**目標**: 建立指標計算器的通用基礎

**交付內容**:
- BaseIndicator抽象類別（定義calculate, validate_params, validate_data方法）
- DataSourceManager類別（統一讀取和管理7種數據源）
- DataSourceEnum枚舉（close/open/high/low/volume/taker_volume/taker_ratio）
- 基礎的參數驗證工具函數
- 單元測試（驗證數據源管理器正常運作）

**設計要點**:
- BaseIndicator定義統一介面，所有指標都繼承它
- DataSourceManager從HDF5讀取案例K線，提供標準化訪問
- 驗證數據完整性（無NaN、長度一致）
- 清晰的錯誤處理機制

**驗收標準**:
- ✅ 可以成功讀取任一案例的7種數據源
- ✅ 數據驗證功能正常（檢測NaN、長度不一致）
- ✅ 測試通過（至少5個真實案例）
- ✅ API清晰，有docstring

**涉及檔案**:
- momentum/Indicators/base.py（BaseIndicator抽象類）
- momentum/Indicators/data_source_manager.py
- momentum/Indicators/types.py（枚舉定義）
- tests/test_base_indicator.py

---

### 📦 模塊2: EMA指標完整實作

**目標**: 實作第一個指標作為範本

**交付內容**:
- EMAIndicator類別（繼承BaseIndicator）
- EMA計算核心（使用pandas.ewm或手動實作）
- 參數驗證（period範圍檢查）
- 單一數據源計算方法
- 批量計算方法（一次計算7種數據源）
- 完整的單元測試（對比TA-Lib或手算結果）
- 性能測試（確保1000根K線 < 100ms）

**計算規範**:
- 輸入：數據源Series + period參數
- 輸出：等長的EMA Series（前N個為NaN）
- 公式：EMA[t] = price[t] × α + EMA[t-1] × (1-α)，α = 2/(period+1)
- 避免未來函數（當前值只用過去數據）

**驗收標準**:
- ✅ EMA計算結果正確（與TA-Lib誤差 < 1e-6）
- ✅ 支援單一數據源計算
- ✅ 支援批量計算（7種數據源）
- ✅ 參數驗證生效（非法輸入會報錯）
- ✅ 性能達標（100根K線 < 10ms）
- ✅ 測試覆蓋率 > 80%

**涉及檔案**:
- momentum/Indicators/ema_indicator.py
- tests/test_ema_indicator.py

---

### 📦 模塊3: 指標計算引擎

**目標**: 統一的指標調用入口

**交付內容**:
- IndicatorEngine類別（統一管理所有指標）
- 指標註冊機制（動態註冊可用指標）
- 配置驅動的批量計算（根據配置計算多個指標）
- 與案例數據的整合（讀取HDF5 → 計算 → 返回完整數據）
- 錯誤處理和降級策略
- 整合測試（真實案例端到端測試）

**API設計**:
```
# 單一指標計算
calculate_indicator(indicator_name, data_source, params, case_data)

# 批量計算（根據配置）
calculate_indicators(indicator_configs, case_data)

# 從案例ID計算
calculate_for_case(case_id, indicator_configs)
```

**配置格式**:
```python
[
  {"indicator": "ema", "data_source": "close", "params": {"period": 20}},
  {"indicator": "ema", "data_source": "volume", "params": {"period": 10}},
]
```

**驗收標準**:
- ✅ 可以註冊和調用EMA指標
- ✅ 批量計算功能正常（一次計算多個指標配置）
- ✅ 與HDF5整合成功（讀取案例 → 計算 → 返回）
- ✅ 錯誤處理完善（案例不存在、指標不存在、計算失敗）
- ✅ 整合測試通過（至少10個真實案例）
- ✅ 性能測試通過（1000個案例 < 10秒）

**涉及檔案**:
- momentum/Indicators/indicator_engine.py
- tests/test_indicator_engine.py
- tests/test_integration.py

---

### 📦 模塊4: 配置系統與文檔

**目標**: 易於擴展和使用

**交付內容**:
- 指標配置YAML檔案（定義可用指標、預設參數、參數範圍）
- 配置載入和驗證器
- 新增指標擴展指南（如何實作新指標的完整文檔）
- API使用文檔（常見場景範例）
- 性能優化建議文檔
- 給任務3.2的使用範例（如何調用指標引擎）

**配置範例**:
```yaml
indicators:
  ema:
    class_name: EMAIndicator
    description: "指數移動平均線"
    default_params:
      period: 20
    param_ranges:
      period: [2, 200]
    
  # 未來擴展用的佔位
  # sma:
  #   class_name: SMAIndicator
  #   ...
```

**擴展指南內容**:
- 繼承BaseIndicator的完整步驟
- 必須實作的方法說明
- 參數驗證規範
- 測試要求和範例
- 註冊到引擎的方式
- EMA作為完整範例

**驗收標準**:
- ✅ 配置YAML格式正確且可載入
- ✅ 配置驗證器正常運作
- ✅ 擴展指南清晰完整（其他人可以照著做）
- ✅ API文檔涵蓋常見場景
- ✅ 與任務3.2的銜接範例可運行

**涉及檔案**:
- config/indicators.yaml
- momentum/Indicators/config_loader.py
- docs/indicator_extension_guide.md
- docs/indicator_api_usage.md
- examples/calculate_indicators_example.py

---

## 📋 整體開發流程

```
模塊1（1-1.5h）: 基礎架構
    ↓ 基礎完成，開始實作指標
模塊2（1.5-2h）: EMA實作
    ↓ 有了範本，建立統一入口
模塊3（1.5-2h）: 指標引擎
    ↓ 核心完成，補充配置和文檔
模塊4（1h）: 配置與文檔

總計：5-6.5小時
```

---

## 🎯 給Claude Code CLI的指示

**執行順序**:
依序完成模塊1 → 2 → 3 → 4，每個模塊都是完整可測試的

**每個模塊的交付**:
- 實作代碼
- 單元測試
- 驗證通過
- 簡單使用範例

**關鍵原則**:
- 每個模塊獨立可用
- 完成一個再開始下一個
- 保持代碼簡潔清晰
- 充分測試

**測試數據**:
- 使用項目中真實的案例數據（從HDF5讀取）
- 至少測試5-10個不同案例
- 覆蓋不同時期和symbol

---

## ✅ 完成檢查清單

**模塊1完成**:
- [ ] BaseIndicator抽象類建立
- [ ] DataSourceManager可用
- [ ] 測試通過

**模塊2完成**:
- [ ] EMA計算正確
- [ ] 批量計算功能
- [ ] 性能達標
- [ ] 測試覆蓋率 > 80%

**模塊3完成**:
- [ ] 指標引擎可用
- [ ] 配置驅動計算正常
- [ ] 整合測試通過
- [ ] 性能測試通過

**模塊4完成**:
- [ ] 配置YAML可載入
- [ ] 擴展指南完整
- [ ] API文檔清晰
- [ ] 與任務3.2銜接確認

**整體驗收**:
- [ ] 所有模塊測試通過
- [ ] 可以計算真實案例的EMA
- [ ] 支援7種數據源
- [ ] 性能達標（1000根K線 < 100ms）
- [ ] 代碼清晰，文檔完整
- [ ] 準備好給任務3.2使用

---

這樣是不是更連貫了？4個完整的模塊，每個都可以獨立交付和測試。Claude Code CLI應該能清楚知道要做什麼。需要再調整嗎？