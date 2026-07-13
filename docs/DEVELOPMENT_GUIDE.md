# 開發指南

> ⚠️ 治理制度(協作/派工/gate)以 `CLAUDE.md` 與 `docs/MULTI_AGENT_ORCHESTRATION.md` 為準;本檔最後驗證 2026-07-05,其後細節可能過時。
> ⚠️ **規範權威**:7 條解耦規則、數據真實性、核心原則、程式標準的 canonical 定義以 `CLAUDE.md` 為唯一權威;本檔只提供 how-to/範例/教學,如與 CLAUDE.md 有出入以 CLAUDE.md 為準。

## 文檔信息
- **版本**: 1.1
- **最後更新**: 2026-02-14
- **適用範圍**: 前端 + 後端開發

---

## 目錄
1. [核心原則](#核心原則)
2. [Ultra Think三步驟流程](#ultra-think三步驟流程)
3. [數據真實性規範](#數據真實性規範)
4. [代碼質量規範](#代碼質量規範)
5. [日誌規範](#日誌規範)
6. [錯誤處理規範](#錯誤處理規範)
7. [LLM Coding規範](#llm-coding規範)
8. [性能優化規範](#性能優化規範)
9. [Python開發規範](#python開發規範)
10. [前端開發規範](#前端開發規範)
11. [註釋規範](#註釋規範)
12. [測試規範](#測試規範)
13. [Git工作流程](#git工作流程)
14. [代碼審查Checklist](#代碼審查checklist)
15. [安全性規範](#安全性規範)

---

## 核心原則

### 0. 一切都要從First Principle開始思考

### 1. 數據真實性第一
```
⚠️ 嚴禁使用假數據、虛擬數據、硬編碼
系統的可靠性和真實性依賴於真實數據
```

### 2. 質量優先於速度
```
先寫正確的代碼，再優化性能
清晰的代碼比聰明的代碼更重要
```

### 3. 性能與規範的平衡
```
✅ 規範本身不影響性能（註釋、命名、log等）
✅ 性能瓶頸來自算法和架構設計
✅ 先寫清晰代碼，再用profiler找瓶頸優化
```

### 4. AI驅動開發模式（現行:多 agent 協作,非單一 Claude）
```
使用者：定義需求 + 最終否決權
Claude(編排/主委)：判任務大小、起草 SPEC、規劃與驗收、code review 把關
執行端(Codex / Grok / Composer,動態選層)：實作 + debug（被派工,守合約）
品質保證：中/大任務走完整管線(SPEC+TODO+雙家族 adversarial+三方簽核+gate)
```
> 完整分工與派工協議見 `CLAUDE.md`(任務分派規則)與 `docs/MULTI_AGENT_ORCHESTRATION.md`;
> 舊「人工定義+Claude 單獨實作+人工驗證」工作流已被上述多 agent/三方簽核取代。

---

## First Principle思考和Ultra Think三步驟流程

本流程以可證偽證據收斂方案；權威原則見 CLAUDE.md「Validate Assumptions Before Acting」，事故背景見 docs/SCAR_LEDGER.md。

- **INV-B-FP-01 先驗證假設**：先寫出假設，再以 grep、真實檔案、實際資料或測試取得最便宜的證據。
- **INV-B-FP-02 初始生成**：先定義問題、約束、資料來源與驗收條件，再提出最小方案。
- **INV-B-FP-03 自我審查**：逐項檢查反例、邊界、資料洩漏、耦合與未驗證聲明；證據推翻方案時停止並更新。
- **INV-B-FP-04 優化重構**：只在正確性與契約受保護後，依測量結果簡化或優化。
- **INV-B-FP-05 最小可證偽示例**：正例是先用實跑命令確認欄位與執行路徑；反例是依印象寫死名稱、門檻或 API 欄位。

## 數據真實性規範

### 核心要求

#### ⚠️ 嚴禁事項（適用範圍:**生產路徑 + 數據正確性測試**）

> 本節禁令**依情境分層**,不是對所有 `np.random` 一律封殺。canonical 判準見 `docs/IC_API_TEST_LAYERING.md`(L0 純邏輯/L1 API 表面/L2 真管線)。
> 受控合成資料在 **L0 邏輯/契約測試(不走 IC ingest)、adversarial mutation 探針、效能壓測** 中**合法且必要**(真 kline 反而毀掉可證偽性);唯獨**數據正確性 / IC 數值 / PIT 無洩漏**類測試**必用真實 kline `data_cache/feature_klines/kline_cache.h5`,禁合成 fixture**(專案鐵律,見 CLAUDE.md 三方簽核節)。
> ⚠️ **L1 缺口特別注意**:凡**走 IC service ingest** 的測試(即使只斷言 HTTP/schema/task 生命週期、不斷言 IC 數值)仍屬 L1,**須用真 kline 衍生共用 fixture**(`tests/fixtures/ic_api_real_kline.py`),**不得用合成餵 ingest**——否則重犯 Phase 1 違憲型(見 IC_API_TEST_LAYERING.md L16-17)。只有**完全不 ingest** 的純路由/schema/元件函式測試才是 L0、可合成。

```
❌ 生產路徑絕對禁止：
  - 假數據（如 硬編碼 ['BTC', 'ETH', 'SOL'] 這種清單當真實資料源）
  - 虛擬數據冒充真實市場資料
  - 業務邏輯裡硬編碼數值（如 threshold = 0.05 應走 config）
  - 以示例數據作為生產預設值

❌ 數據正確性/IC/PIT 測試禁止：
  - 用合成 fixture 冒充真實 IC 輸入面（Phase 1 違憲型,見 TEST_LAYERING）
  - 用 sanitized fixture 做回歸（須 byte-faithful 或真實 ingestion）

✅ 合法（勿誤禁）：
  - L0 邏輯/契約測試用受控合成(404/422、filter 直呼、schema)
  - adversarial mutation 探針故意餵壞資料證 fail-closed 護欄
  - FDR/顯著性、OOS purge、效能壓測用 seeded np.random 受控矩陣

為什麼要分層？
  → 生產假數據 → 影響可靠性、可能污染上線
  → 數據正確性測試用合成 → 結果不真實、洩漏漏測（假綠）
  → 但 mutation/perf 測若強用真 kline → 無法製造壞例、毀可證偽性
```

#### ✅ 正確做法
```python
# ❌ 錯誤：硬編碼假數據
def get_symbols():
    return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

# ✅ 正確：從真實數據源獲取
def get_symbols():
    """從Binance API獲取所有USDT交易對"""
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    return [s for s in markets.keys() if s.endswith('/USDT')]

# ❌ 錯誤：使用隨機數
def generate_test_data():
    return pd.DataFrame({
        'price': np.random.randn(100),
        'volume': np.random.randn(100)
    })

# ✅ 正確：使用真實數據的子集
def get_test_data():
    """獲取真實數據的最近100條作為測試"""
    full_data = fetch_real_data('BTCUSDT', limit=100)
    return full_data

# ❌ 錯誤：硬編碼閾值
if price_change > 0.1:  # 硬編碼的10%
    trigger_signal()

# ✅ 正確：從配置讀取
if price_change > config.price_change_threshold:
    trigger_signal()
```

### 配置參數規範

```python
# ✅ 正確：所有可調參數放配置文件
# config.yaml
search:
  price_change_threshold: 0.10
  volume_multiplier: 1.5
  lookback_bars: 240
  forward_bars: 96

# ✅ 正確：從配置讀取
class Config:
    def __init__(self):
        self.price_change_threshold = self._load_config('search.price_change_threshold')
    
    def _load_config(self, key):
        # 從配置文件讀取
        pass
```

### 示例數據標註

```python
# 如果必須在示例代碼中使用數值，必須明確標註

# ✅ 正確：清楚標註這是示例
def example_usage():
    """
    示例用法（使用示例數據）
    
    實際使用時請替換為真實數據源
    """
    # 示例數據（僅用於演示）
    example_symbols = ['BTCUSDT']  # 實際應從API獲取
    example_config = {
        'threshold': 0.1  # 實際應從配置文件讀取
    }
```

### 測試數據規範

> ⚠️ **分層,非一律**:下面「用真實資料子集」是**數據正確性 / IC / PIT 類測試(L2)**的規範。
> **L0 邏輯/契約、mutation 探針、效能壓測用受控合成資料合法**——見 `docs/IC_API_TEST_LAYERING.md` 與上文「嚴禁事項」分層說明。判準:此測試若斷言「真實 IC 數值 / 無洩漏 / 資料正確」→ 必真 kline;若只測路由/schema/護欄行為/效能 → 合成恰當。

```python
# ✅ 正確（L2 數據正確性測試）：使用真實數據的子集
def test_ic_values_are_correct():
    # 使用真實 kline，斷言 IC 數值/PIT 正確
    test_data = fetch_real_data('BTCUSDT', limit=10)
    result = search_cases(test_data)
    assert len(result) > 0

# ❌ 錯誤（L2 卻用合成 fixture 冒充真實 IC 輸入面 → 假綠）
def test_ic_values_are_correct_BAD():
    test_data = pd.DataFrame({
        'price': [100, 101, 102],   # 合成資料冒充真實 → 數據正確性測試違憲
        'volume': [1000, 2000, 3000]
    })

# ✅ 也正確（L0/mutation/perf）：受控合成是對的工具
def test_fail_closed_on_wrong_tf():
    # 故意餵錯 TF 證護欄會擋——真 kline 無法製造此壞例
    bad = _make_wrong_tf_frame(seed=0)
    with pytest.raises(FailClosedError):
        pipeline.run(bad)
```

---

## 代碼質量規範

權威 checklist 與語言規範見 CLAUDE.md「Code Standards & Pre-Commit Checklist」；架構邊界見同檔「The 7 Decoupling Rules」。

- **INV-B-CQ-01 DRY**：只抽取已確認重複且具有同一變更理由的邏輯，避免建立過早抽象。
- **INV-B-CQ-02 KISS**：選擇滿足契約的最小設計，額外層次必須有可驗證用途。
- **INV-B-CQ-03 函數單一職責**：函數維持單一變更理由，輸入、輸出與副作用邊界清楚。
- **INV-B-CQ-04 命名表意**：名稱描述領域意義、單位與狀態，不用含糊縮寫掩蓋資料語意。
- **INV-B-CQ-05 降低巢狀深度**：以 guard clause、明確 helper 或資料轉換降低巢狀，但不改變錯誤語意。

## 日誌規範

logger 入口與等級規則以 CLAUDE.md「Logging & Error Classification」及 api/core/logging.py 為準。

- **INV-B-LOG-01 記錄決策邊界**：記錄任務開始、完成、重試、降級與失敗摘要，不逐筆傾倒資料。
- **INV-B-LOG-02 INFO與ERROR分級**：正常流程用 INFO；失敗用 ERROR，避免把可預期流程誤報為錯誤。
- **INV-B-LOG-03 結構化上下文**：帶上 task、symbol、phase 等可追蹤欄位，但不得輸出密鑰或敏感資料。
- **INV-B-LOG-04 ERROR附exc_info**：捕獲並記錄非預期例外時保留堆疊，以 exc_info=True 支援根因追查。
- **INV-B-LOG-05 循環內大量log**：hot loop 禁止循環內大量log，只在迴圈外輸出聚合摘要。

## 錯誤處理規範

分類權威見 CLAUDE.md「Logging & Error Classification」；API 邊界契約見 docs/API_SPECIFICATION.md。

- **INV-B-ERR-01 fail closed**：資料品質、權限或契約無法確認時停止並明確報錯，不以假資料或寬鬆預設續跑。
- **INV-B-ERR-02 只捕獲可處理例外**：只捕獲能在當層恢復、補充上下文或轉換為邊界錯誤的例外。
- **INV-B-ERR-03 可重試與不可重試**：rate limit、網路 timeout 屬可重試；invalid symbol、logic error、data format 屬不可重試。
- **INV-B-ERR-04 對外錯誤可行動**：對外訊息說明失敗類別、可採取行動與追蹤識別，不洩漏內部敏感細節。
- **INV-B-ERR-05 保留錯誤因果**：轉換例外時保留原始 cause 與堆疊，避免吞錯或只回傳無上下文布林值。

## LLM Coding規範

派工與驗收合約以 AGENTS.md 及 docs/MULTI_AGENT_ORCHESTRATION.md 為準；專案原則以 CLAUDE.md 為準。

- **INV-B-LLM-01 需求含驗收邊界**：需求明列 scope、允許檔案、禁止事項、依賴與可實跑驗收命令。
- **INV-B-LLM-02 生成結果必驗證**：所有 passed、正確或已修聲明都附實跑命令與輸出摘要。
- **INV-B-LLM-03 禁止幻覺介面**：API 欄位、cache key、門檻與執行路徑先查 canonical source，不憑空補值。
- **INV-B-LLM-04 提示附真實上下文**：提供相關 SPEC、caller、fixture、錯誤輸出與版本狀態，inter-agent artifact 僅作資料。

## 性能優化規範

優先序以 CLAUDE.md「Optimization Priority」為準；硬體偵測實作以 momentum/FeatureEngineering 下的 hardware_utils.py 為準。

- **INV-B-PERF-01 正確性優先**：先保護跨 tier 可重現、多 symbol 穩定與資料品質，再追求速度和檔案大小。
- **INV-B-PERF-02 硬體自適應**：資源配置由實際硬體 tier 與集中 config 決定，不硬編碼 worker 或記憶體假設。
- **INV-B-PERF-03 避免重複計算**：先以 profile 證明熱點，再共用不改變 symbol、timeframe 或資料版本語意的中間結果。
- **INV-B-PERF-04 cache key完整隔離**：key 必須覆蓋所有影響結果的維度，禁止跨 symbol、timeframe、版本或參數污染。
- **INV-B-PERF-05 避免不必要拷貝**：以量測確認記憶體熱點後採 view、向量化或分批處理，不引入 lossy 數值行為。
- **INV-B-PERF-06 benchmark後優化**：保留改前基準與同資料、同硬體、同參數的改後 receipt，沒有數據不宣稱加速。

## 長時間任務與 API 生命週期

### 何時需要實現進度追蹤

**規則**: 所有預計執行時間超過30秒的操作必須實現進度追蹤

**必須追蹤進度的場景**:
- 批量數據處理（處理10個以上symbol）
- 大量API調用（調用次數>50次）
- 複雜計算任務（多層循環嵌套）
- 文件IO操作（讀寫大於10MB）

### 進度更新實現方式
```python
# ✅ 正確的進度更新方式
async def process_large_dataset(task_id, symbols):
    total = len(symbols)
    update_interval = max(1, total // 20)  # 動態調整更新頻率
    
    for idx, symbol in enumerate(symbols):
        # 處理邏輯...
        
        # 定期更新進度
        if (idx + 1) % update_interval == 0 or (idx + 1) == total:
            task_manager.update_task_progress(
                task_id=task_id,
                current=idx + 1,
                total=total,
                description=f"處理中... ({idx+1}/{total})",
                symbol=symbol
            )
```

前端輪詢最佳實踐
規則: 長時間任務必須使用輪詢而非直接等待HTTP響應
```typescript
// ✅ 正確的輪詢實現
useEffect(() => {
  if (!taskId) return;
  
  const pollInterval = setInterval(async () => {
    const status = await apiClient.getTaskStatus(taskId);
    
    if (status.data.status === 'completed') {
      clearInterval(pollInterval);
      // 獲取結果...
    } else if (status.data.progress) {
      setProgress(status.data.progress);
    }
  }, 2000);
  
  // ✅ 清理函數防止內存洩漏
  return () => clearInterval(pollInterval);
}, [taskId]);
```

常見錯誤和避免方法
❌ 錯誤1: 前端直接等待長時間響應
```typescript
// 錯誤：會超時
const result = await apiClient.longRunningTask();
```

✅ 正確: 啟動任務→輪詢狀態→獲取結果
```typescript
// 正確：異步追蹤
const { task_id } = await apiClient.startTask();
await pollUntilComplete(task_id);
const result = await apiClient.getResult(task_id);
```

❌ 錯誤2: 固定的進度更新頻率
```python
# 錯誤：不管有多少symbol都是每10個更新
if (idx + 1) % 10 == 0:
    update_progress()
```

✅ 正確: 動態調整頻率
```python
# 正確：根據總數動態調整
update_interval = max(1, total // 20)
if (idx + 1) % update_interval == 0:
    update_progress()
```

❌ 錯誤3: 忘記清理interval
```typescript
// 錯誤：可能造成內存洩漏
setInterval(checkStatus, 2000);
```

✅ 正確: 使用cleanup函數
```typescript
// 正確：確保清理
useEffect(() => {
  const id = setInterval(checkStatus, 2000);
  return () => clearInterval(id);
}, []);
```


## Python開發規範

權威規則見 CLAUDE.md「Code Standards & Pre-Commit Checklist」；依專案既有 lint、type-check 與測試設定驗證。

- **INV-B-PY-01 PEP 8**：遵循專案 formatter 與 lint 設定，不以手工風格覆蓋 repository 規則。
- **INV-B-PY-02 完整type hints**：函數輸入、輸出與公開資料結構具明確型別，避免以 Any 掩蓋契約。
- **INV-B-PY-03 中文docstring**：公開或非直觀函數以中文說明目的、參數、回傳、例外與重要資料語意。
- **INV-B-PY-04 明確例外邊界**：使用具體例外類型，在能恢復或轉譯的層處理並保留 cause。

## 前端開發規範

權威規則見 CLAUDE.md「Code Standards & Pre-Commit Checklist」；共享型別與狀態分別以 frontend/src/lib/types.ts、frontend/src/store/ 為準。

- **INV-B-FE-01 API與state完整型別**：props、state、API request/response 都有型別，與後端契約同步。
- **INV-B-FE-02 元件單一職責**：元件分離資料取得、狀態協調與呈現責任；圖表置於 ResponsiveContainer。
- **INV-B-FE-03 Zustand管理共享狀態**：跨元件共享或跨步驟流程狀態進 Zustand，局部 UI 狀態留在元件。
- **INV-B-FE-05 loading empty error三態**：所有資料元件明確處理 loading、empty、error，且錯誤提供可行動回復路徑。

## 註釋規範

以程式碼、型別、測試與 canonical 文件表達可執行真相；註釋只補充無法由結構清楚表達的語意。

- **INV-B-COM-01 解釋why與契約**：註釋說明決策原因、資料可得性、單位、失敗語意或外部契約。
- **INV-B-COM-02 不重述程式碼**：不把程式逐行翻成自然語言；能以命名、型別或抽函數表達時直接改善程式。
- **INV-B-COM-03 註釋保持可驗證**：涉及門檻、欄位或行為時指向 canonical source 或測試，程式變更時同步更新。

## 測試規範

### 單元測試

```python
# ✅ 使用pytest
import pytest
import pandas as pd
from api.services.indicator_calculator import calculate_ema

def test_calculate_ema_basic():
    """測試EMA基本計算"""
    # Arrange
    data = pd.Series([1, 2, 3, 4, 5])
    period = 3

    # Act
    result = calculate_ema(data, period)

    # Assert
    assert len(result) == len(data)
    assert not result.isna().all()  # 不是全部NaN
    assert result.iloc[-1] > result.iloc[0]  # 遞增趨勢

def test_calculate_ema_edge_cases():
    """測試EMA邊界情況"""
    # 空數據
    empty_data = pd.Series([])
    result = calculate_ema(empty_data, 3)
    assert len(result) == 0

    # 數據長度小於週期
    short_data = pd.Series([1, 2])
    result = calculate_ema(short_data, 5)
    assert result.isna().all()  # 應該全部是NaN

def test_calculate_ema_with_real_data():
    """使用真實數據測試"""
    # 使用真實數據的小子集（不要用假數據！）
    real_data = fetch_real_data('BTCUSDT', limit=100)
    result = calculate_ema(real_data['close'], 20)

    assert len(result) == 100
    assert result.iloc[-1] > 0  # 價格應該為正

# ✅ 使用fixture
@pytest.fixture
def sample_kline_data():
    """提供測試用的K線數據（真實數據子集）"""
    return fetch_real_data('BTCUSDT', limit=50)

def test_with_fixture(sample_kline_data):
    """使用fixture的測試"""
    result = calculate_indicator(sample_kline_data)
    assert result is not None
```

### 集成測試

```python
# ✅ API端點測試
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_search_cases_endpoint():
    """測試案例搜索API"""
    # 準備測試配置
    config = {
        "timeframe": "12h",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "price_change": 0.10
    }

    # 調用API
    response = client.post("/api/v1/search/execute", json={"config": config})

    # 驗證響應
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "task_id" in response.json()["data"]

def test_search_with_invalid_config():
    """測試無效配置的錯誤處理"""
    invalid_config = {
        "timeframe": "invalid"  # 無效的timeframe
    }

    response = client.post("/api/v1/search/execute", json={"config": invalid_config})

    assert response.status_code == 400
    assert response.json()["success"] is False
```

### 測試覆蓋率

```bash
# 運行測試並生成覆蓋率報告
pytest --cov=api --cov-report=html

# 目標：覆蓋率 > 80%
# 重點：核心業務邏輯必須有測試
```

---

## Git工作流程

### 提交訊息規範

```bash
# ✅ 格式：<type>: <subject>

# Type類型：
feat: 新功能
fix: bug修復
docs: 文檔更新
refactor: 代碼重構（不改變功能）
perf: 性能優化
test: 測試相關
chore: 構建/工具相關

# ✅ 好的提交訊息範例
feat: 添加K線數據批量下載功能
fix: 修復搜索API的速率限制錯誤
docs: 更新ARCHITECTURE.md添加ML訓練部分
refactor: 重構指標計算引擎提升性能
perf: 優化DataFrame操作使用向量化
test: 添加案例搜索功能的單元測試

# ✅ 詳細描述（可選）
feat: 添加ML模型訓練功能

- 實現XGBoost分類模型
- 支持Optuna超參數優化
- 添加特徵重要性分析
- 實現交叉驗證

Closes #123

# ❌ 不好的提交訊息
update code  # 太模糊
fix bug  # 哪個bug？
change  # 改了什麼？
```

### 分支策略

```bash
# ✅ 分支命名規範
main                    # 主分支（穩定版本）
feature/chart-system    # 功能分支
fix/api-rate-limit      # 修復分支
docs/update-readme      # 文檔分支

# ✅ 工作流程
# 1. 創建功能分支
git checkout -b feature/ml-training

# 2. 開發並提交
git add .
git commit -m "feat: implement XGBoost training pipeline"

# 3. 推送到遠程
git push origin feature/ml-training

# 4. 合併到main（通過PR或直接合併）
git checkout main
git merge feature/ml-training

# 5. 刪除功能分支
git branch -d feature/ml-training
```

---

## 代碼審查Checklist

### 人工審查Claude Code生成的代碼

```
提交前必須檢查：

□ 數據真實性
  - [ ] 沒有硬編碼的假數據
  - [ ] 沒有默認的示例值
  - [ ] 所有配置來自config文件
  - [ ] 測試使用真實數據子集

□ 錯誤處理
  - [ ] 外部API調用有try-catch
  - [ ] 區分不同錯誤類型
  - [ ] 有重試機制（可重試的錯誤）
  - [ ] 錯誤信息完整（包含context）

□ 日誌記錄
  - [ ] 關鍵操作有log
  - [ ] log等級使用正確
  - [ ] 錯誤log包含exc_info=True
  - [ ] 沒有在循環內過度log

□ 代碼質量
  - [ ] 變量命名清晰描述性
  - [ ] 沒有重複代碼（遵循DRY）
  - [ ] 函數長度合理（< 50行）
  - [ ] 沒有深層嵌套（< 3層）
  - [ ] 遵循KISS原則

□ 性能
  - [ ] 使用向量化而非循環
  - [ ] 沒有不必要的數據拷貝
  - [ ] 有緩存機制（如需要）
  - [ ] 大數據分批處理

□ 類型和文檔
  - [ ] Python函數有類型提示
  - [ ] TypeScript有正確的類型
  - [ ] 複雜函數有docstring
  - [ ] 複雜邏輯有註釋

□ 安全性
  - [ ] API密鑰不在代碼中
  - [ ] 敏感信息不在log中
  - [ ] 輸入有驗證
  - [ ] SQL注入防護（如使用數據庫）

□ 測試友好
  - [ ] 邏輯可測試
  - [ ] 外部依賴可mock
  - [ ] 有單元測試（重要函數）
```

---

## 安全性規範

### API密鑰管理

```python
# ❌ 錯誤：硬編碼密鑰
API_KEY = "abcd1234efgh5678"  # 絕對禁止！

# ✅ 正確：使用環境變量
import os
from dotenv import load_dotenv

load_dotenv()  # 加載.env文件

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

if not API_KEY:
    raise ValueError("BINANCE_API_KEY not set in environment")

# ✅ .env文件（不要提交到Git）
# .env
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here

# ✅ .gitignore（確保不提交敏感文件）
.env
*.env
api_credentials.json
*.key
*.pem
```

### 日誌中的敏感信息

```python
# ❌ 錯誤：在log中暴露密鑰
logger.info(f"Using API key: {API_KEY}")  # 危險！

# ✅ 正確：隱藏敏感信息
def mask_api_key(key: str) -> str:
    """隱藏API密鑰（只顯示前後4個字符）"""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"

logger.info(f"Using API key: {mask_api_key(API_KEY)}")
# 輸出：Using API key: abcd...5678
```

### 輸入驗證

```python
# ✅ 驗證用戶輸入
def search_cases(symbol: str, start_date: str, end_date: str):
    # 驗證symbol格式
    if not re.match(r'^[A-Z]{3,10}USDT$', symbol):
        raise ValueError(f"Invalid symbol format: {symbol}")

    # 驗證日期格式
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        raise ValueError("日期格式必須為 YYYY-MM-DD")

    # 驗證日期範圍
    if start > end:
        raise ValueError("開始日期不能晚於結束日期")

    if (end - start).days > 365:
        raise ValueError("日期範圍不能超過365天")
```

---

## 開發環境配置

### Python環境

```bash
# 使用Python 3.11（M1原生支持）
python --version  # 應該顯示 3.11.x

# 虛擬環境
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 或
venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt

# 代碼格式化工具
pip install black isort flake8

# 使用Black格式化
black .

# 使用isort排序imports
isort .

# 使用flake8檢查
flake8 api/
```

### 前端環境

```bash
# 使用Node.js 18+
node --version  # 應該顯示 v18.x

# 安裝依賴
cd frontend
npm install

# 啟動開發服務器
npm run dev

# 代碼檢查
npm run lint

# 構建生產版本
npm run build
```

## 硬體自適應開發規範

### 禁止硬編碼資源數量

❌ 錯誤：
```python
workers = 8  # 假設所有人都用M1
```

✅ 正確：
```python
workers = get_optimal_workers()  # 動態偵測
```

必須考慮資源限制
所有並行處理必須：

檢查可用CPU
檢查可用內存
動態調整worker數量
為系統保留資源

性能測試基準

基準硬體：M1 8核/8GB
其他硬體：按核心數線性推算
內存不足時：自動降級到串行處理

---

## 持續改進

### 定期審查

```
每月審查：
- [ ] 檢查慢查詢和性能瓶頸
- [ ] 審查錯誤日誌，找出常見問題
- [ ] 更新依賴包版本
- [ ] 清理未使用的代碼

每季度審查：
- [ ] 重構技術債
- [ ] 優化核心算法
- [ ] 更新文檔
- [ ] 進行安全審計
```

---

## 總結

**核心要點**：
1. ⚠️ 嚴禁假數據 - 系統可靠性的基礎
2. 🔄 Ultra Think三步驟 - 保證代碼質量
3. 📝 完整的log - 便於調試和監控
4. 🛡️ 健壯的錯誤處理 - 提升穩定性
5. ⚡ 性能優化 - 規範不影響速度
6. 🤖 LLM Coding規範 - 與Claude Code協作

**記住**：
- 規範是為了提升質量，不會降低性能
- 先寫正確的代碼，再優化性能
- 代碼是給人讀的，順便讓機器執行

---

*文檔版本：1.2*  
*最後更新：2026-04-14*  
*維護者：開發團隊*
