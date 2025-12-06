# 量化交易系統指標架構決策文檔

## 1. 系統目標與背景

### 1.1 系統核心目標

本系統是一個**量化交易策略回測與優化平台**，核心目標包括：

1. **靈活擴展性**：支持快速新增技術指標（EMA, RSI, MACD, Bollinger Bands 等）
2. **策略組合**：支持基於多種指標組合的交易策略（三線排列、均線交叉等）
3. **參數優化**：使用 Optuna 進行多目標超參數優化
4. **AI 驅動擴展**：未來由 AI Agent（Claude Code, GitHub Copilot）自動新增指標和策略
5. **機器學習整合**：未來整合 XGBoost/LSTM，使用技術指標作為特徵

### 1.2 當前系統狀態

**已完成組件**：
- ✅ **Phase 1**: 策略註冊系統（`strategy_registry`）
- ✅ **Phase 2**: 動態參數優化（Optuna 整合）
- ✅ **指標系統**: EMA 指標實作（類裝飾器架構）
- ✅ **BaseIndicator**: 統一的錯誤處理、驗證、性能監控基類
- ✅ **IndicatorEngine**: 指標註冊與調用引擎
- ✅ **測試驗證**: Phase 2 整合測試（17/17 通過）

**待決策問題**：
- ❓ **指標實作架構**：如何標準化未來新增指標的實作方式
- ❓ **AI 友好度**：如何降低 AI Agent 實作新指標的難度
- ❓ **統一標準**：選擇一種架構作為未來唯一標準（避免混亂）

---

## 2. 為何進行架構評估

### 2.1 觸發原因

在撰寫擴展文檔時，發現**文檔中的函數式範例與實際代碼的類裝飾器架構不一致**：

```python
# 文檔中的範例（函數式）
def calculate_rsi(data: pd.Series, params: Dict) -> pd.Series:
    period = params.get('period', 14)
    # ...

# 實際的 EMA 代碼（類裝飾器）
@register_indicator("ema")
class EMAIndicator(BaseIndicator):
    def calculate(self, data: pd.Series, period: int = 20) -> pd.Series:
        # ...
```

### 2.2 評估必要性

如果不進行架構評估，直接按照現有類裝飾器架構撰寫文檔，可能錯失以下機會：

1. **優化 AI 友好度**：類裝飾器對 AI 的理解門檻較高
2. **降低實作成本**：每個指標 ~150 行代碼可能可以簡化
3. **提高系統靈活性**：探索是否有更好的架構選擇

### 2.3 評估目標

通過 **First Principle 思維**，從零開始分析：
1. 指標的本質需求是什麼？
2. 有哪些可能的架構方案？
3. 各方案的優劣勢如何？
4. 哪種方案最適合系統的長期目標？

---

## 3. 指標的本質需求分析（First Principle）

### 3.1 核心功能需求

一個技術指標的本質是：**輸入數據 + 參數 → 計算 → 輸出結果**

```
輸入: pd.Series (close price)
參數: {"period": 20}
       ↓
    [計算邏輯]
       ↓
輸出: pd.Series (EMA values)
```

**核心代碼量**：~10-20 行

### 3.2 系統附加需求

除了核心計算邏輯，系統還需要：

| 需求類別 | 具體需求 | 代碼量估計 |
|---------|---------|-----------|
| **參數驗證** | 類型檢查、範圍檢查、約束檢查 | ~10-20 行 |
| **錯誤處理** | 數據不足、無效輸入、計算異常 | ~20-30 行 |
| **邊界處理** | 前 N 個值為 NaN、數據對齊 | ~10-15 行 |
| **性能監控** | 計算時間記錄 | ~5-10 行 |
| **日誌記錄** | 調試信息、警告、錯誤 | ~10-15 行 |
| **註冊機制** | 自動發現、字符串調用 | ~5-10 行 |
| **元數據** | 默認參數、指標名稱、描述 | ~10-15 行 |

**系統需求總計**：~70-115 行
**核心邏輯**：~10-20 行
**總計**：~80-135 行

### 3.3 關鍵問題

**這些系統需求應該如何提供？**

- **選項 A**：每個指標獨立實作（純函數式）
  - 結果：10 個指標 = 10 份重複的錯誤處理、驗證邏輯

- **選項 B**：系統統一提供（類繼承或包裝器）
  - 結果：70-115 行基礎建設由系統提供，指標只需寫核心邏輯

---

## 4. 三種架構方案

### 4.1 方案 A：純函數式（Pure Functional）

#### 架構概念

每個指標實作為純函數，無類、無繼承、無裝飾器。

```python
# momentum/Indicators/ema.py

def calculate_ema(data: pd.Series, period: int = 20) -> pd.Series:
    """計算 EMA（最簡實作）"""
    # 邊界檢查
    if len(data) < period:
        return pd.Series([float('nan')] * len(data), index=data.index)

    # 計算
    return data.ewm(span=period, adjust=False).mean()

# 使用方式
from momentum.Indicators.ema import calculate_ema
result = calculate_ema(close_data, period=20)
```

#### 優勢

1. **極簡單**：AI 只需寫 ~10-20 行純函數
2. **無學習曲線**：不需要理解類、繼承、裝飾器
3. **函數式思維**：輸入 → 輸出，符合數學直覺
4. **直接調用**：可以直接 `import` 使用，無需引擎
5. **測試簡單**：純函數易於單元測試

#### 劣勢

1. **重複代碼嚴重**：
   - 每個指標需要自己實作參數驗證（~20 行）
   - 每個指標需要自己實作錯誤處理（~30 行）
   - 每個指標需要自己實作日誌記錄（~15 行）
   - **10 個指標 = ~650 行重複代碼**

2. **無統一接口**：
   - 函數簽名可能不一致（有的用 `period`，有的用 `window`）
   - 返回值格式可能不同（有的返回 Series，有的返回 DataFrame）
   - 難以批量處理

3. **難以擴展系統功能**：
   - 如果未來要加緩存機制 → 需要修改所有指標函數
   - 如果未來要加版本控制 → 需要修改所有指標函數
   - 如果未來要加性能監控 → 需要修改所有指標函數

4. **註冊機制複雜**：
   - 需要手動維護指標名稱 → 函數的映射表
   - 容易遺漏或出錯

#### 代碼量分析

```
單個指標：
  核心邏輯：~15 行
  參數驗證：~20 行
  錯誤處理：~30 行
  邊界處理：~15 行
  日誌記錄：~15 行
  ─────────────
  總計：~95 行

10 個指標：~950 行（包含大量重複邏輯）
```

---

### 4.2 方案 B：類裝飾器（Class Decorator - 現有架構）

#### 架構概念

每個指標繼承 `BaseIndicator` 基類，使用 `@register_indicator` 裝飾器自動註冊。

```python
# momentum/Indicators/ema_indicator.py

@register_indicator("ema")
class EMAIndicator(BaseIndicator):
    """EMA 指標實作"""

    @classmethod
    def get_indicator_name(cls) -> str:
        return "ema"

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {"period": 20}

    def calculate(self, data: pd.Series, period: int = 20, **kwargs) -> pd.Series:
        """核心計算邏輯（AI 填入）"""
        if len(data) < period:
            return pd.Series([float('nan')] * len(data), index=data.index)
        return data.ewm(span=period, adjust=False).mean()

    def validate_params(self, period: int = 20, **kwargs) -> bool:
        """參數驗證（AI 填入）"""
        if not isinstance(period, int):
            raise ValueError(f"period must be int")
        if not 2 <= period <= 200:
            raise ValueError(f"period must be in [2, 200]")
        return True

# 使用方式
engine = IndicatorEngine()
result = engine.calculate_indicator("ema", DataSourceEnum.CLOSE, "ETHUSDT", "1h", period=20)
```

#### 優勢

1. **無重複代碼**：
   - `BaseIndicator` 提供統一的錯誤處理（~80 行）
   - `BaseIndicator` 提供統一的數據驗證（~40 行）
   - `BaseIndicator` 提供統一的性能監控（~30 行）
   - `BaseIndicator` 提供統一的日誌記錄（貫穿整個基類）
   - **10 個指標共享 ~334 行基礎建設**

2. **統一接口**：
   - 所有指標必須實作 `calculate()` 和 `validate_params()`
   - 所有指標返回 `pd.Series`
   - 所有指標通過 `IndicatorEngine` 統一調用

3. **易於擴展系統功能**：
   - 新增緩存機制 → 只需修改 `BaseIndicator`
   - 新增版本控制 → 只需修改 `BaseIndicator`
   - 新增性能監控 → 只需修改 `BaseIndicator.safe_calculate()`
   - **一次修改，所有指標受益**

4. **自動註冊**：
   - `@register_indicator("ema")` 自動註冊到 `IndicatorEngine`
   - 通過字符串調用：`engine.calculate_indicator("ema", ...)`
   - Optuna 可動態發現所有已註冊指標

5. **已驗證穩定**：
   - 現有 EMA 已使用此架構
   - Phase 2 測試全部通過（17/17）
   - 無需重構現有代碼

#### 劣勢

1. **AI 理解成本**：
   - 需要理解類（class）的概念
   - 需要理解繼承（inheritance）
   - 需要理解類方法（@classmethod）
   - 需要理解裝飾器（@register_indicator）
   - 需要理解 `self` 參數

2. **代碼量較多**：
   - 每個指標 ~120-150 行（包含完整 docstring）
   - 相比純函數多 ~100 行（但多的是模板代碼）

3. **不能直接調用**：
   - 必須通過 `IndicatorEngine` 調用
   - 不能 `from ema_indicator import calculate_ema` 直接使用
   - （但有 `safe_calculate()` 可直接調用）

#### 代碼量分析

```
單個指標：
  模板代碼（固定）：~100 行
    - 類聲明、裝飾器：~5 行
    - get_indicator_name：~5 行
    - get_default_params：~5 行
    - calculate 框架：~30 行（含 docstring）
    - validate_params 框架：~30 行（含 docstring）
    - 文件頭 docstring：~25 行

  AI 填入邏輯：~30 行
    - calculate 核心邏輯：~15 行
    - validate_params 邏輯：~15 行
  ─────────────
  總計：~130 行

10 個指標：~1,300 行
BaseIndicator：~334 行（一次性，所有指標共享）
總計：~1,634 行

重複代碼：0 行（模板代碼不算重複，因為每個指標都需要 docstring）
```

---

### 4.3 方案 C：混合式（Hybrid - Function + Wrapper）

#### 架構概念

AI 寫純函數，系統自動包裝成類並註冊。

```python
# momentum/Indicators/ema.py

def calculate_ema(data: pd.Series, period: int = 20) -> pd.Series:
    """計算 EMA（核心邏輯）"""
    if len(data) < period:
        logger.warning(f"Data length ({len(data)}) < period ({period})")
        return pd.Series([float('nan')] * len(data), index=data.index)
    return data.ewm(span=period, adjust=False).mean()

def validate_ema_params(period: int = 20) -> bool:
    """驗證 EMA 參數"""
    if not isinstance(period, int):
        raise ValueError(f"period must be int")
    if not 2 <= period <= 200:
        raise ValueError(f"period must be in [2, 200]")
    return True

# 一行註冊（系統自動包裝成類）
register_functional_indicator(
    name="ema",
    calculate_fn=calculate_ema,
    validate_fn=validate_ema_params,
    default_params={"period": 20}
)

# 使用方式（兩種）
# 方式 1: 通過引擎（帶錯誤處理）
engine = IndicatorEngine()
result = engine.calculate_indicator("ema", DataSourceEnum.CLOSE, "ETHUSDT", "1h", period=20)

# 方式 2: 直接調用函數（測試用）
result = calculate_ema(close_data, period=20)
```

#### 包裝器實作（一次性）

```python
# momentum/Indicators/functional_wrapper.py

def register_functional_indicator(name, calculate_fn, validate_fn, default_params):
    """將函數包裝成類並註冊"""

    class FunctionalIndicator(BaseIndicator):
        @classmethod
        def get_indicator_name(cls):
            return name

        @classmethod
        def get_default_params(cls):
            return default_params.copy()

        def calculate(self, data, **params):
            return calculate_fn(data, **params)

        def validate_params(self, **params):
            return validate_fn(**params)

    FunctionalIndicator.__name__ = f"{name.upper()}Indicator"
    IndicatorEngine.register(name, FunctionalIndicator)

    return calculate_fn  # 返回原函數，可直接使用
```

**包裝器代碼量**：~80 行（一次性實作，所有函數式指標共享）

#### 優勢

1. **AI 友好**：
   - AI 只需寫 ~30-40 行純函數（`calculate` + `validate`）
   - 無需理解類、繼承、裝飾器
   - 函數式思維，直觀易懂

2. **保留系統優勢**：
   - 通過包裝器自動獲得 `BaseIndicator` 的所有功能
   - 統一錯誤處理、性能監控、日誌記錄
   - 自動註冊到 `IndicatorEngine`
   - Optuna 可動態發現

3. **靈活調用**：
   - 可以通過 `IndicatorEngine` 調用（帶錯誤處理）
   - 也可以直接 `import` 函數調用（測試用）

4. **向後兼容**：
   - 現有類裝飾器指標可以保留
   - 新指標使用函數式
   - 兩種方式可以共存

#### 劣勢

1. **需實作包裝器**：
   - 一次性成本 ~80-100 行
   - 需要測試驗證包裝器的正確性
   - （但這是一次性成本，未來所有函數式指標都受益）

2. **調試複雜度**：
   - 錯誤棧會顯示：`FunctionalIndicator.calculate → calculate_ema`
   - 多一層間接（但錯誤信息仍然清晰）
   - 需要理解包裝器的工作原理（調試包裝器時）

3. **文檔負擔**：
   - 需要解釋"什麼是包裝器"
   - 需要解釋"為什麼要包裝"
   - 增加學習成本（但對 AI 實作新指標影響不大）

4. **混合架構**：
   - 系統中同時存在兩種模式（類裝飾器 + 函數式）
   - 可能造成困惑（什麼時候用哪種？）
   - （可以統一規定：新指標用函數式，舊指標保留）

#### 代碼量分析

```
單個指標：
  calculate 函數：~20 行
  validate 函數：~15 行
  註冊調用：~5 行
  ─────────────
  總計：~40 行

10 個指標：~400 行
包裝器（一次性）：~80 行
BaseIndicator：~334 行（共享）
總計：~814 行

重複代碼：0 行（包裝器自動生成所有模板代碼）
```

---

## 5. 三種方案對比總結

### 5.1 量化對比表

| 維度 | 純函數式 | 類裝飾器 | 混合式 |
|------|---------|---------|--------|
| **AI 實作難度** | ⭐⭐⭐⭐⭐ (最簡單) | ⭐⭐⭐ (中等) | ⭐⭐⭐⭐⭐ (簡單) |
| **單指標代碼量** | ~95 行 | ~130 行 | ~40 行 |
| **10指標總代碼量** | ~950 行 | ~1,634 行 | ~814 行 |
| **重複代碼量** | ~650 行 | 0 行 | 0 行 |
| **系統基礎建設** | 0 行 | ~334 行 (BaseIndicator) | ~414 行 (BaseIndicator + Wrapper) |
| **統一接口** | ❌ 無 | ✅ 強制統一 | ✅ 強制統一 |
| **錯誤處理** | ⚠️ 自己實作 | ✅ 統一提供 | ✅ 統一提供 |
| **性能監控** | ⚠️ 自己實作 | ✅ 統一提供 | ✅ 統一提供 |
| **調試難度** | ⭐⭐⭐⭐⭐ (直接) | ⭐⭐⭐⭐ (直觀) | ⭐⭐⭐⭐ (多一層) |
| **擴展系統功能** | ❌ 困難 | ✅ 容易 | ✅ 容易 |
| **Optuna 整合** | ⚠️ 需手動維護映射 | ✅ 自動發現 | ✅ 自動發現 |
| **已驗證穩定** | ❌ 未實作 | ✅ EMA 已實作 | ❌ 需實作包裝器 |
| **向後兼容** | ❌ 需重構 EMA | ✅ 完全兼容 | ✅ 兼容（可共存） |
| **實作成本** | 低（無基礎建設） | 0（已存在） | 中（需實作包裝器） |

### 5.2 核心權衡

#### 純函數式的權衡
- ✅ **AI 最簡單** vs ❌ **重複代碼嚴重、難以維護**
- **適用場景**：只有 1-3 個指標的小型系統
- **不適用**：有 10+ 個指標的系統（重複代碼不可接受）

#### 類裝飾器的權衡
- ✅ **無重複代碼、易於維護** vs ⚠️ **AI 理解成本中等**
- **適用場景**：中大型系統，需要長期維護
- **關鍵**：通過模板化降低 AI 實作難度

#### 混合式的權衡
- ✅ **AI 最簡單 + 無重複代碼** vs ⚠️ **需實作包裝器、混合架構**
- **適用場景**：需要極致 AI 友好度的系統
- **關鍵**：一次性成本換取長期收益

---

## 6. 決策分析

### 6.1 系統目標回顧

| 目標 | 純函數式 | 類裝飾器 | 混合式 |
|------|---------|---------|--------|
| **靈活擴展性** | ⚠️ 無統一接口 | ✅ 統一接口 | ✅ 統一接口 |
| **AI 驅動擴展** | ✅ 簡單 | ⚠️ 需模板 | ✅ 簡單 |
| **長期可維護性** | ❌ 重複代碼 | ✅ 優秀 | ✅ 優秀 |
| **XGBoost/LSTM 整合** | ⚠️ 需手動管理 | ✅ 自動管理 | ✅ 自動管理 |
| **向後兼容** | ❌ 需重構 | ✅ 無需修改 | ✅ 可共存 |

### 6.2 關鍵決策因素

#### 因素 1：未來指標數量

- **預期**：10-50 個技術指標
- **影響**：純函數式的重複代碼成本隨指標數量線性增長
- **結論**：❌ 排除純函數式

#### 因素 2：AI 實作頻率

用戶原話："未來我只會跟你提出我要新增哪些指標參數和策略，你就跟著範本新增"

- **預期使用場景**：用戶提出需求 → Claude 實作新指標
- **關鍵**：Claude 能否高效理解和實作

**類裝飾器 + 模板**：
```python
# Claude 的工作流程
1. 複製模板文件
2. 全局替換標識符（INDICATOR_NAME → rsi）
3. 填入核心邏輯（~20 行）
```

**混合式 + 函數**：
```python
# Claude 的工作流程
1. 新建 .py 文件
2. 寫 calculate 函數（~20 行）
3. 寫 validate 函數（~15 行）
4. 調用 register_functional_indicator（~5 行）
```

**差異分析**：
- 類裝飾器：需要理解模板結構（但結構固定，理解一次即可）
- 混合式：需要理解包裝器的作用（但實作時不需要）

**我的能力評估**：
- 我（Claude）能理解類裝飾器模板（已證明：我實作了 EMA）
- 我能理解混合式包裝器（概念更簡單）
- **兩者對我來說難度相當**

#### 因素 3：系統穩定性

- **類裝飾器**：已實作並測試（EMA + Phase 2 測試通過）
- **混合式**：需要新增包裝器（~80 行）+ 測試驗證（~1 小時）

**風險評估**：
- 類裝飾器：✅ 零風險（已驗證）
- 混合式：⚠️ 低風險（包裝器邏輯簡單，但需測試）

#### 因素 4：文檔複雜度

**類裝飾器文檔結構**：
```markdown
## 如何新增指標
1. 複製模板
2. 替換標識符
3. 填入 calculate 邏輯
4. 填入 validate 邏輯
5. 完成

## 模板說明
- @register_indicator: 自動註冊
- BaseIndicator: 提供錯誤處理
- get_indicator_name: 返回指標名稱
- ...
```

**混合式文檔結構**：
```markdown
## 如何新增指標
1. 寫 calculate 函數
2. 寫 validate 函數
3. 調用 register_functional_indicator

## 包裝器說明
- register_functional_indicator: 自動包裝成類
- 為什麼要包裝: 統一錯誤處理、性能監控
- 包裝器如何工作: 動態生成類
- ...
```

**複雜度對比**：
- 類裝飾器：需要解釋 5 個概念（類、繼承、類方法、裝飾器、self）
- 混合式：需要解釋 1 個概念（包裝器）+ 5 個函數式概念（但 AI 已懂）

**結論**：混合式文檔更簡潔（假設 AI 已懂函數）

---

## 7. 最終建議

### 7.1 建議方案：**混合式（Hybrid）**

#### 推薦理由

1. **最佳 AI 友好度**：
   - AI 只需寫 ~40 行純函數（vs 類裝飾器的 ~130 行模板）
   - 無需理解類、繼承等複雜概念
   - 函數式思維直觀易懂

2. **無重複代碼**：
   - 包裝器自動提供錯誤處理、驗證、監控
   - 10 個指標共享 ~414 行基礎建設
   - 總代碼量最少（~814 行 vs 類裝飾器的 ~1,634 行）

3. **系統優勢不減**：
   - 保留統一接口
   - 保留 Optuna 自動發現
   - 保留性能監控和日誌

4. **向後兼容**：
   - 現有 EMA 類可保留（不強制重構）
   - 新指標用函數式
   - 兩種方式可共存（過渡期）

5. **一次性成本換長期收益**：
   - 實作包裝器：~80 行 + ~1 小時測試
   - 未來每個指標節省 ~90 行代碼
   - 第 1 個新指標後即回本

#### 實作計劃

**階段 1: 實作包裝器**（~1 小時）
```python
# momentum/Indicators/functional_wrapper.py
def register_functional_indicator(name, calculate_fn, validate_fn, default_params, description=""):
    # 動態生成類，繼承 BaseIndicator
    # 註冊到 IndicatorEngine
    pass
```

**階段 2: 創建 EMA 函數式版本**（~30 分鐘）
```python
# momentum/Indicators/ema.py (NEW)
def calculate_ema(data, period=20): ...
def validate_ema_params(period=20): ...
register_functional_indicator("ema", calculate_ema, validate_ema_params, {"period": 20})
```

**階段 3: 測試驗證**（~30 分鐘）
- 驗證功能與現有 EMA 類等價
- 運行 Phase 2 測試確保無破壞
- 創建單元測試覆蓋包裝器

**階段 4: 更新文檔**（~1 小時）
- 說明混合架構的設計理念
- 提供函數式模板和範例
- 保留類裝飾器說明（向後兼容）

**總時間**：~3 小時

### 7.2 備選方案：**類裝飾器（保持現狀）**

#### 適用條件

如果以下任一條件成立，建議保持類裝飾器：

1. **時間緊迫**：沒有 3 小時實作和測試包裝器
2. **風險厭惡**：不想引入新組件（即使風險很低）
3. **AI 能力充足**：認為 Claude 理解類裝飾器無困難

#### 補償措施

如果選擇類裝飾器，必須提供**極致優化的模板**：

```python
# momentum/Indicators/_template.py

"""
========================================
指標模板 - AI 填空式實作
========================================

使用步驟:
1. 複製此文件
2. 全局替換 INDICATOR_NAME → 你的指標名稱（如 rsi）
3. 全局替換 NAME → 大寫指標名稱（如 RSI）
4. 搜尋「AI 填入」標記，填入邏輯
5. 完成！

========================================
"""

@register_indicator("INDICATOR_NAME")  # ← 替換 INDICATOR_NAME
class NAMEIndicator(BaseIndicator):    # ← 替換 NAME

    @classmethod
    def get_indicator_name(cls) -> str:
        return "INDICATOR_NAME"  # ← 替換 INDICATOR_NAME

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        # ===== AI 填入：默認參數 =====
        return {"period": 20}
        # =============================

    def calculate(self, data: pd.Series, period: int = 20, **kwargs) -> pd.Series:
        # 驗證參數
        if not self.validate_params(period=period):
            raise ValueError(f"Invalid parameters")

        # 檢查數據長度
        if len(data) < period:
            return pd.Series([float('nan')] * len(data), index=data.index)

        # ===== AI 填入：核心計算邏輯 =====
        result = data.ewm(span=period, adjust=False).mean()
        # ===================================

        return result

    def validate_params(self, period: int = 20, **kwargs) -> bool:
        # ===== AI 填入：參數驗證邏輯 =====
        if not isinstance(period, int):
            raise ValueError(f"period must be int")
        if not 2 <= period <= 200:
            raise ValueError(f"period must be in [2, 200]")
        # ===================================

        return True
```

### 7.3 不推薦方案：**純函數式**

#### 不推薦理由

1. **重複代碼不可接受**：10 個指標 = ~650 行重複代碼
2. **違反 DRY 原則**：錯誤處理、驗證邏輯重複實作
3. **難以維護**：新增系統功能需修改所有指標
4. **無統一接口**：難以批量處理和擴展

#### 唯一適用場景

- 系統只有 1-3 個指標
- 不需要 Optuna 整合
- 不需要 XGBoost/LSTM 整合
- **本系統不符合以上條件**

---

## 8. 決策建議總結

### 推薦順序

1. **首選：混合式**
   - 理由：AI 最友好 + 無重複代碼 + 總代碼量最少
   - 成本：~3 小時實作和測試
   - 風險：低（包裝器邏輯簡單）

2. **備選：類裝飾器**
   - 理由：已驗證穩定 + 零實作成本
   - 成本：需提供極致優化的模板
   - 風險：無（已存在）

3. **不推薦：純函數式**
   - 理由：重複代碼嚴重 + 難以維護
   - 適用場景：小型系統（1-3 個指標）
   - 本系統不適用

### 最終建議

**選擇混合式架構**，理由如下：

1. **用戶需求**："未來由 AI 實作新指標" → 需要最 AI 友好的架構
2. **系統規模**：10-50 個指標 → 需要無重複代碼的架構
3. **長期目標**：XGBoost/LSTM 整合 → 需要統一接口
4. **投資回報**：~3 小時實作成本，每個新指標節省 ~90 行代碼

**實作優先級**：
1. 實作包裝器（~1 小時）
2. 創建 EMA 函數式版本作為範例（~30 分鐘）
3. 測試驗證（~30 分鐘）
4. 更新文檔（~1 小時）

**回報期**：第 1 個新指標後即回本（節省 ~90 行代碼）

---

## 9. 附錄：給 Claude 的實作指南

### 當用戶要求新增指標時（混合式架構）

**步驟 1: 創建指標文件**
```python
# momentum/Indicators/{indicator_name}.py
import pandas as pd
import logging
from .functional_wrapper import register_functional_indicator

logger = logging.getLogger(__name__)

def calculate_{indicator_name}(data: pd.Series, param1: int = default1) -> pd.Series:
    """核心計算邏輯"""
    # 邊界處理
    if len(data) < required_length:
        logger.warning(f"Data length insufficient")
        return pd.Series([float('nan')] * len(data), index=data.index)

    # 計算邏輯
    result = ...  # 根據用戶需求填入
    return result

def validate_{indicator_name}_params(param1: int = default1) -> bool:
    """參數驗證邏輯"""
    if not isinstance(param1, expected_type):
        raise ValueError(f"param1 must be {expected_type}")
    if not min_value <= param1 <= max_value:
        raise ValueError(f"param1 must be in [{min_value}, {max_value}]")
    return True

# 註冊
register_functional_indicator(
    name="{indicator_name}",
    calculate_fn=calculate_{indicator_name},
    validate_fn=validate_{indicator_name}_params,
    default_params={"param1": default1},
    description="指標描述"
)
```

**步驟 2: 測試**
```python
# 使用 IndicatorEngine 測試
engine = IndicatorEngine()
result = engine.calculate_indicator(
    "{indicator_name}",
    DataSourceEnum.CLOSE,
    "ETHUSDT",
    "1h",
    param1=value1
)
print(f"Calculated {len(result)} values")
```

**步驟 3: 更新文檔**
- 在 `docs/STRATEGY_EXTENSION_GUIDE.md` 添加範例

### 當用戶要求新增指標時（類裝飾器架構）

**步驟 1: 複製模板**
```bash
cp momentum/Indicators/_template.py momentum/Indicators/{indicator_name}_indicator.py
```

**步驟 2: 全局替換**
- `INDICATOR_NAME` → `{indicator_name}`
- `NAME` → `{INDICATOR_NAME}`

**步驟 3: 填入邏輯**
- 搜尋 `AI 填入` 標記
- 填入默認參數、計算邏輯、驗證邏輯

**步驟 4: 測試**
```python
engine = IndicatorEngine()
result = engine.calculate_indicator(
    "{indicator_name}",
    DataSourceEnum.CLOSE,
    "ETHUSDT",
    "1h",
    param1=value1
)
```

---

**文檔版本**: 1.0
**創建日期**: 2025-12-04
**作者**: Claude (Sonnet 4.5)
**狀態**: 待用戶決策
