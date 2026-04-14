# Feature Factory 優化 Implementation PLAN

> **版本**: V5  
> **建立日期**: 2026-02-17  
> **設計文件**: `docs/Feature_Factory_優化SPEC.md` V1.1 (Frozen)  
> **基底 PLAN**: `docs/Feature_Factory_PLAN.md` V7 (Frozen)  
> **目的**: AI Agent 可依序執行的實作清單；人類可審閱檢查  
> **範圍**: Feature Factory 優化 — 微觀結構引擎、資訊理論引擎、尾部風險引擎、前處理層 (Layer 6.5)  
> **狀態**: � V2 Frozen — 自審通過，凍結  
> **前置條件**: Feature_Factory_PLAN V7 (Frozen) 已完成至少 Phase 1.1（Config + Atomic + Factory 骨架 + scan_config.yaml）
> Changelog: V2 → V3：補齊後段任務驗證檢查點（含成功與失敗/邊界 PASS）並修正 `hasattr` 相容性敘述矛盾。

---

## Changelog

| 版本 | 日期 | 變更摘要 |
|------|------|----------|
| V1 | 2026-02-17 | 初版生成，覆蓋 SPEC §1-§17 全部內容 |
| V2 | 2026-02-17 | 自審修訂：移除冗餘 hasattr、修正 EntropyConfig windows、精確化 pipeline 整合程式碼、新增 conftest.py fixture 模板、新增 Changelog |
| V3 | 2026-02-17 | 補齊 Task 2.2.4/2.5.2/2.5.3/2.5.4 的 `### 驗證檢查點`（成功 + 失敗/邊界 PASS），並修正舊版 YAML 相容性描述與本 PLAN 決策一致 |
| V4 | 2026-02-17 | Task 2.4.1 實測回寫：修復 Layer 2/3 實跑錯誤（MIDPOINT/MIDPRICE 註冊、PLUS_DM/MINUS_DM 參數衝突、RollingAggregator 重複欄名）並補上強制重算 PASS 證據 |

---

## 架構原則與解耦要求

> **Authority**: 本 PLAN 必須遵循系統全局解耦架構（REFACTOR_ARCHITECTURE_V4），參見：  
> - [docs/ARCHITECTURE.md - 解耦架構原則](./ARCHITECTURE.md#解耦架構原則)  
> - [docs/PRODUCT_VISION.md - 版本演進策略](./PRODUCT_VISION.md#架構演進策略)  
> - [docs/全系統解耦Prompt.md](./全系統解耦Prompt.md) (V4.2)  
> - [docs/SYSTEM_DECOUPING_PLAN_TODO.md](./SYSTEM_DECOUPING_PLAN_TODO.md) (V11)

### 解耦規則遵循清單

**本 PLAN 所有 Task 必須符合以下 7 條規則**：

| 規則 | 要求 | 本 PLAN 實作方式 |
|------|------|----------------|
| **Rule 1** | `momentum/` 不依賴 `api/` | ✅ 所有新引擎在 `momentum/FeatureEngineering/atomic/` 和 `preprocessing/`，不 import `api.*` |
| **Rule 2** | Cross-Domain 用 Protocol 注入 | ✅ 新引擎不直接 import 其他 Domain 的 concrete class |
| **Rule 3** | Service 用 Factory | ✅ `create_feature_factory()` 已存在，新引擎透過 FeatureFactory 內部建構 |
| **Rule 4** | Service 間禁止互調 | ✅ 不涉及 Service 層修改 |
| **Rule 5** | Config 單一來源 | ✅ 所有新配置從 `config/scan_config.yaml` 讀取（via ConfigManager）|
| **Rule 6** | Test 配置隔離 | ✅ 測試直接建構 Engine/Preprocessor，不需 `run_api.py` |
| **Rule 7** | DTO 不跨層 | ✅ 新引擎使用原生 dict/DataFrame，不引用 `api/models/` |

### 設計約束（來自 SPEC §1.2）

1. **不修改現有 Layer 0-7 Pipeline**：新功能以新增引擎或新增 Layer 方式整合
2. **Config-Driven**：所有新功能透過 `scan_config.yaml` 控制，預設 `enabled: false`
3. **向量化優先**：所有計算使用 pandas/numpy 向量化，避免 Python for 迴圈（ApEn/SampEn 的 Numba JIT 內部迴圈、FracDiff 的 d* 二分搜尋、Hurst/Fractal 的 rolling.apply 除外）
4. **解耦架構**：遵循 Rule 1-7
5. **漸進式啟用**：每個新引擎可獨立啟用/停用，不影響既有特徵
6. **Codebase 一致性**：新引擎的類別簽名、方法命名、config 載入模式與既有引擎保持一致

### V2.0/V3.0 演進準備

| 版本 | 使用方式 | 可行性 |
|------|---------|--------|
| **V1.0** | REST API: `POST /api/v1/features/generate`（config 中啟用新引擎） | ✅ 已設計 |
| **V2.0** | Chat: "幫我生成含微觀結構的特徵給 BTCUSDT 12h" | ✅ Config override 開啟新引擎 |
| **V3.0** | Agent: 自主判斷是否需要尾部風險/entropy 特徵 | ✅ 透過 ConfigManager 動態切換 |

---

## 全域常量與約定

| 項目 | 值 |
|------|-----|
| 專案根目錄 | `/Users/louis/Desktop/quantitative_trading_system/` |
| Python venv | `venv/` |
| 後端核心路徑 | `momentum/FeatureEngineering/` |
| Config 路徑 | `config/` |
| 測試路徑 | `tests/momentum/` |
| 日誌標準 | `from momentum.core.logging import get_logger; logger = get_logger(__name__)` |
| 錯誤處理 | 所有外部呼叫 try/except + error classification |
| 新引擎統一介面 | `__init__(self, config: Dict, data_sources: List[str])` + `compute_all(data) -> DataFrame` + `get_feature_metadata() -> Dict` |

### 新增特徵命名規範

新增的 3 類引擎使用獨立的 prefix，不使用七段式（因為微觀結構/entropy/尾部風險非 TA-Lib 指標）：

| 引擎 | Prefix | 範例 |
|------|--------|------|
| Microstructure | `ms_` | `ms_amihud_illiq_21`, `ms_kyle_lambda_13`, `ms_vpin_50` |
| Entropy | `ent_` | `ent_shannon_close_return_21`, `ent_hurst_100`, `ent_perm_55` |
| Tail Risk | `tr_` | `tr_cvar_5pct_21`, `tr_rv_up_13`, `tr_mdd_55` |
| Preprocessing suffix | `_{transform}` | `_rank`, `_gaussian`, `_zscore`, `_diff{d}`, `_fracdiff` |

---

## Phase 依賴圖

```
Phase 2.1 (Config 擴展)
  2.1.1 Pydantic Config Models ──→ 2.1.2 scan_config.yaml 擴展
  2.1.1 ──→ 2.2.* (所有 Engine 依賴 Config)
  2.1.1 ──→ 2.3.* (Preprocessor 依賴 Config)

Phase 2.2 (Layer 1 新增引擎)
  2.2.1 MicrostructureIndicatorEngine
  2.2.2 EntropyIndicatorEngine
  2.2.3 TailRiskIndicatorEngine
  2.2.4 atomic/__init__.py 更新
  ⚠️ 2.2.1-2.2.3 可平行開發，無互相依賴

Phase 2.3 (Layer 6.5 前處理層)
  2.3.1 preprocessing 目錄 + FeaturePreprocessor
  ⚠️ 可與 Phase 2.2 平行開發

Phase 2.4 (Pipeline 整合)
  依賴 2.2.4 + 2.3.1 完成
  2.4.1 feature_factory.py 修改

Phase 2.5 (測試與驗收)
  依賴 ALL 上述 Phase
  2.5.1 單元測試 → 2.5.2 整合測試 → 2.5.3 效能測試 → 2.5.4 驗收報告
```

**關鍵依賴**：
```
2.1.1 (Config) ──→ 2.1.2 (YAML) ──→ 2.2.* + 2.3.*
2.2.1-3 (Engines) ──→ 2.2.4 (__init__)
2.2.4 + 2.3.1 ──→ 2.4.1 (Pipeline)
ALL ──→ 2.5.* (Testing)
```

---

## Phase 2.1：Config 與 Pydantic 擴展

### Task 2.1.1：Pydantic Config Models 新增（SPEC §7.3）

**檔案**：
- `momentum/FeatureEngineering/feature_config.py` (修改)

**新增 Pydantic Models**：

```python
# === 新增 Layer 1 Engine Config Models ===

from pydantic import BaseModel, Field, field_validator
from typing import List, Union

class MicrostructureConfig(BaseModel):
    """微觀結構指標配置（SPEC §3）"""
    enabled: bool = False
    windows: List[int] = [5, 13, 21, 55]
    epsilon: float = 1e-10
    min_trades: int = 1
    enabled_features: Union[str, List[str]] = 'all'
    cs_spread_smooth: List[int] = [5, 13, 21]
    ofi_raw: bool = True
    kyle_lambda_windows: List[int] = [13, 21, 55]
    vpin_n_buckets: List[int] = [30, 50]
    vpin_zscore_windows: List[int] = [21, 55]

class EntropyConfig(BaseModel):
    """資訊理論指標配置（SPEC §4）"""
    enabled: bool = False
    windows: List[int] = [55, 100]           # ApEn/SampEn/Fractal Dim 共用
    n_bins: int = 10
    apen_m: int = 2
    apen_r_ratio: float = 0.2
    hurst_windows: List[int] = [55, 100, 200]
    fractal_kmax: int = 10
    use_numba: bool = True
    perm_m: int = 3
    perm_windows: List[int] = [21, 55, 100]
    apply_to: List[str] = ['close_return']
    shannon_windows: List[int] = [21, 55, 100]

    @field_validator('perm_m')
    @classmethod
    def validate_perm_m(cls, v):
        if v < 2:
            raise ValueError(f"perm_m must be >= 2, got {v}")
        return v

class TailRiskConfig(BaseModel):
    """尾部風險指標配置（SPEC §5）"""
    enabled: bool = False
    windows: List[int] = [21, 55, 100]
    cvar_alphas: List[float] = [0.01, 0.05]
    rv_windows: List[int] = [13, 21, 55]
    mdd_windows: List[int] = [21, 55, 100]

    @field_validator('cvar_alphas')
    @classmethod
    def validate_alphas(cls, v):
        for a in v:
            if not 0 < a < 1:
                raise ValueError(f"cvar_alpha must be in (0, 1), got {a}")
        return v

# === 新增 Layer 6.5 Preprocessing Config Models ===

class WinsorConfig(BaseModel):
    """Winsorization 配置（SPEC §6.5）"""
    enabled: bool = True
    method: str = 'sigma'       # 'sigma' or 'quantile'
    sigma_k: float = 3.0
    quantile_range: List[float] = [0.01, 0.99]
    apply_to: Union[str, List[str]] = 'all'

class ADFDifferencingConfig(BaseModel):
    """ADF 整數差分配置（SPEC §6.3）"""
    enabled: bool = False
    adf_threshold: float = 0.05
    max_diff: int = 2
    sample_size: int = 500
    apply_to: str = 'non_stationary'

class FractionalDifferencingConfig(BaseModel):
    """分數差分配置（SPEC §6.6 — 推薦優先使用）"""
    enabled: bool = False
    d_range: List[float] = [0.0, 1.0]
    adf_threshold: float = 0.05
    weight_threshold: float = 1e-5
    precision: float = 0.01
    apply_to: str = 'non_stationary'
    cache_d_star: bool = True

class RankTransformConfig(BaseModel):
    """排名轉換配置（SPEC §6.1）"""
    enabled: bool = True
    window: int = 252
    apply_to: Union[str, List[str]] = 'all'

class GaussianNormalizeConfig(BaseModel):
    """高斯正規化配置（SPEC §6.2）"""
    enabled: bool = False
    clip_range: List[float] = [0.001, 0.999]
    apply_to: Union[str, List[str]] = 'all'

class AdaptiveZScoreConfig(BaseModel):
    """自適應 Z-Score 配置（SPEC §6.4）"""
    enabled: bool = True
    windows: List[int] = [100, 252]
    epsilon: float = 1e-8
    apply_to: Union[str, List[str]] = 'all'

class PreprocessingConfig(BaseModel):
    """前處理層完整配置（SPEC §6）"""
    enabled: bool = False
    mode: str = 'append'        # 'append' (新增帶 suffix 的欄位) or 'replace' (原位替代)
    winsorization: WinsorConfig = WinsorConfig()
    adf_differencing: ADFDifferencingConfig = ADFDifferencingConfig()
    fractional_differencing: FractionalDifferencingConfig = FractionalDifferencingConfig()
    rank_transform: RankTransformConfig = RankTransformConfig()
    gaussian_normalize: GaussianNormalizeConfig = GaussianNormalizeConfig()
    adaptive_zscore: AdaptiveZScoreConfig = AdaptiveZScoreConfig()

# === AtomicIndicatorConfig 擴展 ===
# 在既有 AtomicIndicatorConfig 中新增 3 個欄位：

class AtomicIndicatorConfig(BaseModel):
    # ... 既有 7 個 CategoryConfig 不修改 ...
    trend: CategoryConfig = Field(default_factory=CategoryConfig)
    momentum: CategoryConfig = Field(default_factory=CategoryConfig)
    volatility: CategoryConfig = Field(default_factory=CategoryConfig)
    volume: CategoryConfig = Field(default_factory=CategoryConfig)
    cycle: CategoryConfig = Field(default_factory=CategoryConfig)
    pattern: CategoryConfig = Field(default_factory=CategoryConfig)
    statistics: CategoryConfig = Field(default_factory=CategoryConfig)
    # 新增（使用專用 Config，因為不使用 TA-Lib）
    microstructure: MicrostructureConfig = MicrostructureConfig()
    entropy: EntropyConfig = EntropyConfig()
    tail_risk: TailRiskConfig = TailRiskConfig()

# === FactoryConfig 擴展 ===
# 在既有 FactoryConfig 中新增 preprocessing 欄位：

class FactoryConfig(BaseModel):
    # ... 既有欄位不修改 ...
    preprocessing: PreprocessingConfig = PreprocessingConfig()
```

**依賴**：pydantic (已有)

**驗收條件**：
- [x] `MicrostructureConfig(enabled=True)` 正確實例化，所有預設值符合 SPEC §3
- [x] `EntropyConfig(perm_m=1)` 觸發 `ValueError` 驗證
- [x] `TailRiskConfig(cvar_alphas=[0.0])` 觸發 `ValueError` 驗證
- [x] `PreprocessingConfig` 包含全部 6 個子 config
- [x] `AtomicIndicatorConfig` 包含 `microstructure`, `entropy`, `tail_risk` 欄位
- [x] `FactoryConfig` 包含 `preprocessing` 欄位
- [x] 舊版 `FactoryConfig`（無新欄位）反序列化時使用預設值（向後相容）

**驗收方式**：
```python
# tests/momentum/test_feature_factory_opt_config.py
def test_microstructure_config_defaults():
    config = MicrostructureConfig()
    assert config.enabled is False
    assert config.windows == [5, 13, 21, 55]
    assert config.epsilon == 1e-10

def test_entropy_config_perm_m_validation():
    with pytest.raises(ValueError):
        EntropyConfig(perm_m=1)

def test_tail_risk_config_alpha_validation():
    with pytest.raises(ValueError):
        TailRiskConfig(cvar_alphas=[0.0])

def test_factory_config_backward_compat():
    """舊版 YAML（無新欄位）能正常載入"""
    old_yaml = {"version": "2.2", "global_settings": {}, ...}
    config = FactoryConfig(**old_yaml)
    assert config.preprocessing.enabled is False
    assert config.atomic_indicators.microstructure.enabled is False
```

### 驗證檢查點
- PASS: 所有新 Pydantic Model 的 `model_dump()` 輸出與 SPEC §7.3 定義一致
- PASS: `field_validator` 正確攔截無效值

**Checklist**：
- [x] `MicrostructureConfig` 定義（含所有 SPEC §3.8 參數）
- [x] `EntropyConfig` 定義（含所有 SPEC §4.7 參數 + `perm_m` validator）
- [x] `TailRiskConfig` 定義（含所有 SPEC §5.7 參數 + `cvar_alphas` validator）
- [x] `WinsorConfig` 定義
- [x] `ADFDifferencingConfig` 定義
- [x] `FractionalDifferencingConfig` 定義
- [x] `RankTransformConfig` 定義
- [x] `GaussianNormalizeConfig` 定義
- [x] `AdaptiveZScoreConfig` 定義
- [x] `PreprocessingConfig` 定義（組合 6 個子 config）
- [x] `AtomicIndicatorConfig` 擴展（新增 3 欄位）
- [x] `FactoryConfig` 擴展（新增 `preprocessing` 欄位）
- [x] 向後相容性測試
- [x] 單元測試通過

---

### Task 2.1.2：scan_config.yaml 擴展（SPEC §7.2）

**檔案**：
- `config/scan_config.yaml` (修改)

**新增 YAML Section**：

在 `atomic_indicators` 區段尾部新增：

```yaml
atomic_indicators:
  # ... 既有 7 個 engines 不修改 ...

  microstructure:
    enabled: false  # 預設關閉，需顯式啟用
    windows: [5, 13, 21, 55]
    epsilon: 1.0e-10
    min_trades: 1
    enabled_features: all  # or list: [amihud, kyle_lambda, roll_spread, cs_spread, ofi, large_trade_ratio, vpin]
    cs_spread_smooth: [5, 13, 21]
    ofi_raw: true
    kyle_lambda_windows: [13, 21, 55]
    vpin_n_buckets: [30, 50]
    vpin_zscore_windows: [21, 55]

  entropy:
    enabled: false
    windows: [55, 100]
    n_bins: 10
    apen_m: 2
    apen_r_ratio: 0.2
    hurst_windows: [55, 100, 200]
    fractal_kmax: 10
    use_numba: true
    perm_m: 3
    perm_windows: [21, 55, 100]
    apply_to:
      - close_return
    shannon_windows: [21, 55, 100]

  tail_risk:
    enabled: false
    windows: [21, 55, 100]
    cvar_alphas: [0.01, 0.05]
    rv_windows: [13, 21, 55]
    mdd_windows: [21, 55, 100]
```

新增頂層 `preprocessing` section：

```yaml
preprocessing:
  enabled: false  # 預設關閉
  mode: append    # 'append' (新增帶 suffix 的欄位) or 'replace' (原位替代)

  winsorization:
    enabled: true
    method: sigma    # 'sigma' or 'quantile'
    sigma_k: 3.0
    quantile_range: [0.01, 0.99]
    apply_to: all

  adf_differencing:
    enabled: false   # 較慢，預設關閉（推薦使用 fractional_differencing）
    adf_threshold: 0.05
    max_diff: 2
    sample_size: 500
    apply_to: non_stationary

  fractional_differencing:
    enabled: false   # 較慢但品質更高
    d_range: [0.0, 1.0]
    adf_threshold: 0.05
    weight_threshold: 1.0e-5
    precision: 0.01
    apply_to: non_stationary
    cache_d_star: true

  rank_transform:
    enabled: true
    window: 252
    apply_to: all

  gaussian_normalize:
    enabled: false
    clip_range: [0.001, 0.999]
    apply_to: all

  adaptive_zscore:
    enabled: true
    windows: [100, 252]
    epsilon: 1.0e-8
    apply_to: all
```

**依賴**：Task 2.1.1 (Pydantic Models 必須先定義)

**驗收條件**：
- [x] `ConfigManager.get_merged_config()` 正確解析新 sections
- [x] 所有新 section 預設 `enabled: false`
- [x] YAML 可完整反序列化為 `FactoryConfig`
- [x] 移除新 section 時（舊版 YAML），Pydantic 使用預設值（不報錯）

**驗收方式**：
```python
def test_yaml_with_new_sections():
    cm = ConfigManager()
    config = cm.get_merged_config()
    assert config.atomic_indicators.microstructure.enabled is False
    assert config.atomic_indicators.entropy.enabled is False
    assert config.atomic_indicators.tail_risk.enabled is False
    assert config.preprocessing.enabled is False

def test_yaml_enable_microstructure():
    cm = ConfigManager()
    config = cm.get_merged_config(api_override={
        "atomic_indicators": {"microstructure": {"enabled": True}}
    })
    assert config.atomic_indicators.microstructure.enabled is True
    assert config.atomic_indicators.microstructure.windows == [5, 13, 21, 55]
```

### 驗證檢查點
- PASS: `python -c "from momentum.FeatureEngineering.config_manager import ConfigManager; cm = ConfigManager(); c = cm.get_merged_config(); print(c.atomic_indicators.microstructure.enabled)"` 輸出 `False`

**Checklist**：
- [x] `atomic_indicators.microstructure` section 新增
- [x] `atomic_indicators.entropy` section 新增
- [x] `atomic_indicators.tail_risk` section 新增
- [x] `preprocessing` 頂層 section 新增（含 6 個子 section）
- [x] 所有預設值與 SPEC + Pydantic Models 一致
- [x] ConfigManager 合併測試通過

---

### Task 2.1.3：ConfigManager preview 擴展

**檔案**：
- `momentum/FeatureEngineering/config_manager.py` (修改)

**修改重點**：

在 `preview_feature_count()` 方法中新增對新引擎的估算邏輯：

```python
def preview_feature_count(self, config: FactoryConfig) -> FeatureCountPreview:
    # ... 既有邏輯 ...
    
    # 新增：微觀結構特徵估算
    if hasattr(config.atomic_indicators, 'microstructure') and config.atomic_indicators.microstructure.enabled:
        ms_count = self._estimate_microstructure_features(config.atomic_indicators.microstructure)
        breakdown['microstructure'] = ms_count
    
    # 新增：資訊理論特徵估算
    if hasattr(config.atomic_indicators, 'entropy') and config.atomic_indicators.entropy.enabled:
        ent_count = self._estimate_entropy_features(config.atomic_indicators.entropy)
        breakdown['entropy'] = ent_count
    
    # 新增：尾部風險特徵估算
    if hasattr(config.atomic_indicators, 'tail_risk') and config.atomic_indicators.tail_risk.enabled:
        tr_count = self._estimate_tail_risk_features(config.atomic_indicators.tail_risk)
        breakdown['tail_risk'] = tr_count
    
    # 新增：前處理層估算（append mode 會增加欄位）
    if hasattr(config, 'preprocessing') and config.preprocessing.enabled:
        preprocess_multiplier = self._estimate_preprocessing_multiplier(config.preprocessing)
        breakdown['preprocessing_added'] = int(total * (preprocess_multiplier - 1))

def _estimate_microstructure_features(self, config: MicrostructureConfig) -> int:
    """估算微觀結構特徵數，基於 SPEC §3.8 output schema"""
    count = 0
    count += len(config.windows)                     # amihud: 4
    count += len(config.kyle_lambda_windows)         # kyle_lambda: 3
    count += len(config.kyle_lambda_windows)         # roll_spread: 3 (同 windows)
    count += len(config.cs_spread_smooth)            # cs_spread: 3
    count += 1 + len(config.windows)                 # ofi: 1 raw + 4 zscore = 5
    count += len(config.kyle_lambda_windows)         # large_trade_ratio: 3
    count += len(config.vpin_n_buckets) + len(config.vpin_zscore_windows)  # vpin: 2+2 = 4
    return count  # 預設 25

def _estimate_entropy_features(self, config: EntropyConfig) -> int:
    """估算資訊理論特徵數，基於 SPEC §4.7 output schema"""
    n_sources = len(config.apply_to)
    count = 0
    count += len(config.shannon_windows) * n_sources  # shannon: 3
    count += len(config.windows)                      # apen: 2
    count += len(config.windows)                      # sampen: 2
    count += len(config.hurst_windows)                # hurst: 3
    count += len(config.windows)                      # fractal_dim: 2 (使用 config.windows)
    count += len(config.perm_windows)                 # permutation: 3
    return count  # 預設 15

def _estimate_tail_risk_features(self, config: TailRiskConfig) -> int:
    """估算尾部風險特徵數，基於 SPEC §5.7 output schema"""
    count = 0
    count += len(config.cvar_alphas) * len(config.windows)  # cvar: 2*3 = 6
    count += 3 * len(config.rv_windows)                     # rv_up + rv_down + rsj: 3*3 = 9
    count += len(config.rv_windows)                          # ud_vol_ratio: 3
    count += len(config.windows)                             # gpr: 3
    count += 2                                               # jb: 2 (windows [55,100])
    count += len(config.mdd_windows)                         # mdd: 3
    return count  # 預設 26

def _estimate_preprocessing_multiplier(self, config: PreprocessingConfig) -> float:
    """估算前處理層的特徵膨脹倍率（append mode）"""
    if config.mode == 'replace':
        return 1.0
    multiplier = 1.0
    if config.rank_transform.enabled:
        multiplier += 1.0       # 每個特徵 +1 rank 版
    if config.gaussian_normalize.enabled:
        multiplier += 1.0       # +1 gaussian 版
    if config.adaptive_zscore.enabled:
        multiplier += len(config.adaptive_zscore.windows)  # +N zscore 版
    # winsorization 是 in-place，不增加欄位
    # adf/fracdiff 只對非定態特徵做，估算 20% 啟用
    if config.adf_differencing.enabled or config.fractional_differencing.enabled:
        multiplier += 0.2
    return multiplier
```

**依賴**：Task 2.1.1

**驗收條件**：
- [x] `preview_feature_count()` 啟用 microstructure 時回傳 +25
- [x] `preview_feature_count()` 啟用 entropy 時回傳 +15
- [x] `preview_feature_count()` 啟用 tail_risk 時回傳 +26
- [x] breakdown 包含 `microstructure`, `entropy`, `tail_risk` key

**驗收方式**：
```python
def test_preview_with_new_engines():
    cm = ConfigManager()
    config = cm.get_merged_config(api_override={
        "atomic_indicators": {
            "microstructure": {"enabled": True},
            "entropy": {"enabled": True},
            "tail_risk": {"enabled": True}
        }
    })
    preview = cm.preview_feature_count(config)
    assert preview.breakdown.get('microstructure', 0) == 25
    assert preview.breakdown.get('entropy', 0) == 15
    assert preview.breakdown.get('tail_risk', 0) == 26
```

### 驗證檢查點
- PASS: 啟用全部 3 個新引擎時 preview 增加 66 特徵

**Checklist**：
- [x] `_estimate_microstructure_features()` 方法
- [x] `_estimate_entropy_features()` 方法
- [x] `_estimate_tail_risk_features()` 方法
- [x] `_estimate_preprocessing_multiplier()` 方法
- [x] `preview_feature_count()` 整合新引擎回傳
- [x] 單元測試通過

---

## Phase 2.2：Layer 1 新增引擎

### Task 2.2.1：MicrostructureIndicatorEngine（SPEC §3）

**檔案**：
- `momentum/FeatureEngineering/atomic/microstructure_indicators.py` (新建)

**函式簽名**：

```python
import numpy as np
import pandas as pd
from typing import Dict, List
from momentum.core.logging import get_logger

logger = get_logger(__name__)

class MicrostructureIndicatorEngine:
    """Layer 1 Indicator Engine: 微觀結構與流動性特徵。
    
    計算 7 類微觀結構指標（共 25 features），全面量化市場流動性狀態。
    所有計算使用 numpy/pandas 向量化操作，無 Python for 迴圈。
    
    Required data columns: close, high, low, volume, quote_volume,
                          taker_buy_volume, taker_ratio, trades
    
    指標列表（§3.1-§3.7）：
    1. Amihud Illiquidity Ratio (§3.1) — 4 features
    2. Kyle's Lambda (§3.2) — 3 features
    3. Roll's Implied Spread (§3.3) — 3 features
    4. Corwin-Schultz Spread (§3.4) — 3 features
    5. Order Flow Imbalance + Z-Score (§3.5) — 5 features
    6. Large Trade Ratio (§3.6) — 3 features
    7. VPIN (§3.7) — 4 features
    """
    
    def __init__(self, config: Dict, data_sources: List[str]):
        """
        Args:
            config: microstructure section from scan_config.yaml
            data_sources: 不使用（微觀結構使用固定欄位），接受參數以符合 Engine 統一介面
        """
        self._config = config
        self._data_sources = data_sources
        self.windows = config.get('windows', [5, 13, 21, 55])
        self.epsilon = config.get('epsilon', 1e-10)
        self.min_trades = config.get('min_trades', 1)
        self.enabled_features = config.get('enabled_features', 'all')
        self.cs_spread_smooth = config.get('cs_spread_smooth', [5, 13, 21])
        self.kyle_lambda_windows = config.get('kyle_lambda_windows', [13, 21, 55])
        self.vpin_n_buckets = config.get('vpin_n_buckets', [30, 50])
        self.vpin_zscore_windows = config.get('vpin_zscore_windows', [21, 55])
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """計算所有啟用的微觀結構特徵。
        
        Args:
            data: raw OHLCV DataFrame（必須含 close, high, low, volume, 
                  quote_volume, taker_buy_volume, taker_ratio, trades）
        
        Returns:
            DataFrame with microstructure features, same index as data
        """
        frames = []
        methods = [
            ('amihud', self._compute_amihud),
            ('kyle_lambda', self._compute_kyle_lambda),
            ('roll_spread', self._compute_roll_spread),
            ('cs_spread', self._compute_cs_spread),
            ('ofi', self._compute_ofi),
            ('large_trade_ratio', self._compute_large_trade_ratio),
            ('vpin', self._compute_vpin),
        ]
        for name, method in methods:
            if self.enabled_features == 'all' or name in self.enabled_features:
                try:
                    frames.append(method(data))
                except Exception as e:
                    logger.warning(f"Microstructure indicator {name} failed: {e}")
        return pd.concat(frames, axis=1) if frames else pd.DataFrame(index=data.index)
    
    def get_feature_metadata(self) -> Dict[str, Dict]:
        """返回所有特徵的 Metadata。
        
        Returns:
            Dict[feature_name, {"layer": "layer1", "category": "microstructure", 
                               "indicator": str, "params": dict, "description": str}]
        """
    
    # --- 7 個內部計算方法 ---
    
    def _compute_amihud(self, data: pd.DataFrame) -> pd.DataFrame:
        """Amihud Illiquidity Ratio（§3.1）
        
        amihud = rolling_mean(|return| / quote_volume, window)
        
        降級：quote_volume 缺失 → 使用 close * volume 替代
        邊界：quote_volume 全為 0 → 返回 NaN
        """
    
    def _compute_kyle_lambda(self, data: pd.DataFrame) -> pd.DataFrame:
        """Kyle's Lambda via rolling covariance/variance（§3.2）
        
        signed_volume = volume * sign(close.pct_change())
        delta_price = close.diff()
        lambda = Cov(ΔP, SignedVol) / Var(SignedVol)
        
        邊界：價格不變（return=0） → lambda = 0
        """
    
    def _compute_roll_spread(self, data: pd.DataFrame) -> pd.DataFrame:
        """Roll's Implied Spread（§3.3）
        
        dp = close.diff()
        autocov = dp.rolling(window).cov(dp.shift(1))
        spread = 2 * sqrt(max(-autocov, 0))
        
        邊界：autocovariance > 0 → spread = 0（非 NaN）
        """
    
    def _compute_cs_spread(self, data: pd.DataFrame) -> pd.DataFrame:
        """Corwin-Schultz Spread Estimator（§3.4）
        
        完全向量化，使用 rolling(2).max()/min()
        
        邊界：high == low → spread = 0
        """
    
    def _compute_ofi(self, data: pd.DataFrame) -> pd.DataFrame:
        """Order Flow Imbalance + Z-Score（§3.5）
        
        OFI = 2 * taker_ratio - 1（標準化到 [-1, 1]）
        OFI_zscore = (OFI - mean) / std
        
        降級：taker_ratio 缺失 → 使用 taker_buy_volume / volume
        """
    
    def _compute_large_trade_ratio(self, data: pd.DataFrame) -> pd.DataFrame:
        """Large Trade Ratio（§3.6）
        
        avg_trade_size = quote_volume / trades
        LTR = avg_trade_size / rolling_median(avg_trade_size, window)
        
        邊界：trades = 0 → 返回 NaN
        """
    
    def _compute_vpin(self, data: pd.DataFrame) -> pd.DataFrame:
        """VPIN via Bulk Volume Classification（§3.7）
        
        BVC: buy_pct = Φ(ΔP / σ)（向量化 scipy.stats.norm.cdf）
        VPIN = rolling_sum(|buy_vol - sell_vol|) / rolling_sum(volume)
        + VPIN Z-Score
        
        邊界：
        - sigma = 0 → buy_pct fallback 0.5 → VPIN = 0
        - volume 全為 0 → VPIN = NaN
        """
```

**依賴**：numpy, pandas, scipy.stats.norm (VPIN)

**資料需求**：`close, high, low, volume, quote_volume, taker_buy_volume, taker_ratio, trades`

**輸出 Schema**（25 features，見 SPEC §3.8）：
```
ms_amihud_illiq_{5,13,21,55}           — 4 features
ms_kyle_lambda_{13,21,55}              — 3 features
ms_roll_spread_{13,21,55}              — 3 features
ms_cs_spread_{5,13,21}                 — 3 features
ms_ofi_raw                             — 1 feature
ms_ofi_zscore_{5,13,21,55}            — 4 features
ms_large_trade_ratio_{13,21,55}        — 3 features
ms_vpin_{30,50}                        — 2 features
ms_vpin_zscore_{21,55}                 — 2 features
Total: 25 features
```

**邊界條件（SPEC §3.9，11 項）**：

| # | 條件 | 預期行為 | 測試名 |
|---|------|---------|--------|
| 1 | `quote_volume` 全為 0 | Amihud 返回 NaN | `test_amihud_zero_volume` |
| 2 | `trades` 全為 0 或缺失 | Large Trade Ratio 返回 NaN | `test_ltr_zero_trades` |
| 3 | 資料列數 < min window | 依賴該 window 的特徵返回 NaN | `test_micro_insufficient_data` |
| 4 | 價格完全不變（return = 0） | Kyle's Lambda = 0, Roll's Spread = 0 | `test_constant_price` |
| 5 | `taker_ratio` 缺失 | OFI 使用 `taker_buy_volume / volume` 替代 | `test_ofi_fallback` |
| 6 | 極端 volume spike（1000x） | 正常計算，不 clip | `test_volume_spike` |
| 7 | `high == low`（所有 bar） | Corwin-Schultz spread = 0 | `test_zero_range_bar` |
| 8 | Roll 的 autocovariance > 0 | spread = 0（非 NaN） | `test_roll_positive_autocov` |
| 9 | VPIN 窗口內 volume 全為 0 | VPIN = NaN | `test_vpin_zero_volume` |
| 10 | VPIN sigma_deltaP = 0 | fallback 0.5 → VPIN = 0 | `test_vpin_zero_sigma` |
| 11 | 特徵名 prefix 唯一 (`ms_`) | 無衝突 | `test_micro_feature_name_unique` |

**驗收條件**：
- [x] 7 個指標全部正確計算（與 SPEC §3.1-§3.7 公式比對）
- [x] 輸出 25 個特徵，命名符合 `ms_*` pattern
- [x] `compute_all()` 內部逐指標 try/except，單一指標失敗不影響其他
- [x] `get_feature_metadata()` 為每個特徵回傳 Metadata dict
- [x] 所有 11 項邊界條件通過
- [x] 降級場景（§10.3）正確處理

**驗收方式**：
```bash
pytest tests/momentum/test_microstructure_indicators.py -v --tb=short
```

### 驗證檢查點
- PASS: BTCUSDT 12h 真實數據上 `compute_all()` 回傳 25 欄位 DataFrame，無例外
- PASS: 所有 `ms_*` 欄位的 NaN 比率 < 20%（前幾根 warmup 除外）

**Checklist**：
- [x] `__init__` 參數解析（config + data_sources 統一介面）
- [x] `_compute_amihud()` — SPEC §3.1 公式
- [x] `_compute_kyle_lambda()` — SPEC §3.2 向量化 Cov/Var
- [x] `_compute_roll_spread()` — SPEC §3.3 向量化 rolling.cov
- [x] `_compute_cs_spread()` — SPEC §3.4 完全向量化
- [x] `_compute_ofi()` — SPEC §3.5 raw + Z-Score
- [x] `_compute_large_trade_ratio()` — SPEC §3.6
- [x] `_compute_vpin()` — SPEC §3.7 BVC + rolling sum
- [x] `get_feature_metadata()` — 25 features 的 Metadata
- [x] 逐指標 try/except 隔離
- [x] 降級邏輯（quote_volume / taker_ratio / trades 缺失）
- [x] 11 項邊界條件覆蓋
- [x] 不 import `api.*`（Rule 1）
- [x] 使用 `momentum.core.logging`

---

### Task 2.2.2：EntropyIndicatorEngine（SPEC §4）

**檔案**：
- `momentum/FeatureEngineering/atomic/entropy_indicators.py` (新建)

**函式簽名**：

```python
import numpy as np
import pandas as pd
from typing import Dict, List
from momentum.core.logging import get_logger

logger = get_logger(__name__)

# Optional: Numba JIT
try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    logger.warning("Numba not available, ApEn/SampEn will use pure numpy (slower)")

class EntropyIndicatorEngine:
    """Layer 1 Indicator Engine: 資訊理論與複雜度特徵。
    
    計算 6 類資訊理論指標（共 15 features），量化時間序列的可預測性和複雜度。
    
    效能特性：
    - Shannon Entropy: O(N*window) — 較快
    - Permutation Entropy: O(N*window*m) — 較快（無需 Numba）
    - ApEn/SampEn: O(N*window²) — 較慢，建議限制 window ≤ 100，Numba JIT 加速
    - Hurst/Fractal: O(N*window*log(window)) — 中等
    
    Required data columns: close (計算 returns 後使用)
    
    指標列表（§4.1-§4.6）：
    1. Shannon Entropy (§4.1) — 3 features
    2. Approximate Entropy (§4.2) — 2 features
    3. Sample Entropy (§4.3) — 2 features
    4. Hurst Exponent (§4.4) — 3 features
    5. Fractal Dimension (§4.5) — 2 features
    6. Permutation Entropy (§4.6) — 3 features
    """
    
    def __init__(self, config: Dict, data_sources: List[str]):
        """
        Args:
            config: entropy section from scan_config.yaml
            data_sources: 用於決定哪些序列計算 entropy（預設 ['close_return']）
        """
        self._config = config
        self._data_sources = data_sources
        self.windows = config.get('windows', [55, 100])
        self.n_bins = config.get('n_bins', 10)
        self.apen_m = config.get('apen_m', 2)
        self.apen_r_ratio = config.get('apen_r_ratio', 0.2)
        self.shannon_windows = config.get('shannon_windows', [21, 55, 100])
        self.hurst_windows = config.get('hurst_windows', [55, 100, 200])
        self.fractal_kmax = config.get('fractal_kmax', 10)
        self.use_numba = config.get('use_numba', True) and HAS_NUMBA
        self.perm_m = config.get('perm_m', 3)
        self.perm_windows = config.get('perm_windows', [21, 55, 100])
        self.apply_to = config.get('apply_to', ['close_return'])
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """計算所有啟用的資訊理論特徵。
        
        apply_to 欄位解析規則：
        - 'close_return' → data['close'].pct_change()
        - 'volume' → data['volume']
        - 'taker_ratio' → data['taker_ratio']
        其他 → 直接取 data[column_name]
        """
    
    def get_feature_metadata(self) -> Dict[str, Dict]:
        """返回所有特徵的 Metadata。"""
    
    def _resolve_series(self, data: pd.DataFrame, source: str) -> pd.Series:
        """解析 apply_to 中的 source 為 pd.Series。"""
    
    def _compute_shannon_entropy(self, series: pd.Series, source_name: str) -> pd.DataFrame:
        """Rolling Shannon Entropy（§4.1）
        
        向量化策略：np.apply_along_axis + np.histogram
        """
    
    def _compute_approximate_entropy(self, series: pd.Series) -> pd.DataFrame:
        """Rolling Approximate Entropy（§4.2）
        
        使用 Numba JIT 加速（若可用），否則 fallback 純 numpy。
        
        邊界：窗口內 std = 0 → tolerance fallback to 1e-8
        """
    
    def _compute_sample_entropy(self, series: pd.Series) -> pd.DataFrame:
        """Rolling Sample Entropy（§4.3）
        
        使用 Numba JIT 加速（若可用），否則 fallback 純 numpy。
        """
    
    def _compute_hurst(self, series: pd.Series) -> pd.DataFrame:
        """Rolling Hurst Exponent via R/S analysis（§4.4）
        
        多子序列長度 log-log 回歸。
        
        邊界：回歸 R² < 0.1 → 返回 NaN（不可靠估計）
        """
    
    def _compute_fractal_dimension(self, series: pd.Series) -> pd.DataFrame:
        """Rolling Fractal Dimension via Higuchi method（§4.5）"""
    
    def _compute_permutation_entropy(self, series: pd.Series) -> pd.DataFrame:
        """Rolling Permutation Entropy（§4.6）
        
        純 numpy 實作，使用 np.argsort + 編碼為整數 → np.bincount 統計。
        正規化：PE / log2(m!)
        
        邊界：m > window → NaN
              窗口內值全部相同 → PE = 0
        """
```

**依賴**：numpy, pandas; Optional: numba

**輸出 Schema**（15 features，見 SPEC §4.7）：
```
ent_shannon_close_return_{21,55,100}   — 3 features
ent_apen_{55,100}                      — 2 features
ent_sampen_{55,100}                    — 2 features
ent_hurst_{55,100,200}                 — 3 features
ent_fractal_dim_{55,100}               — 2 features
ent_perm_{21,55,100}                   — 3 features
Total: 15 features
```

**邊界條件（SPEC §4.8，11 項）**：

| # | 條件 | 預期行為 | 測試名 |
|---|------|---------|--------|
| 1 | 資料列數 < min window | 返回 NaN | `test_entropy_insufficient_data` |
| 2 | 全部 return = 0 | Shannon = 0, Hurst → NaN | `test_entropy_constant_returns` |
| 3 | 窗口內 std = 0 | ApEn/SampEn r fallback to 1e-8 | `test_entropy_zero_variance` |
| 4 | 含大量 NaN（>50%） | 返回 NaN | `test_entropy_many_nans` |
| 5 | 極端報酬（±50%） | 正常計算 | `test_entropy_extreme_returns` |
| 6 | Hurst 回歸 R² < 0.1 | 返回 NaN | `test_hurst_low_r_squared` |
| 7 | Numba 不可用 | fallback 純 numpy + WARNING | `test_entropy_no_numba` |
| 8 | apply_to 欄位不存在 | skip + WARNING | `test_entropy_missing_column` |
| 9 | Permutation Entropy m > window | 返回 NaN | `test_perm_entropy_m_exceeds_window` |
| 10 | PE 窗口內值全部相同 | PE = 0 | `test_perm_entropy_constant_values` |
| 11 | PE m = 1 | raise ValueError | `test_perm_entropy_invalid_m` |

**驗收條件**：
- [x] 6 個指標全部正確計算（與 SPEC §4.1-§4.6 公式比對）
- [x] 輸出 15 個特徵，命名符合 `ent_*` pattern
- [x] Numba 可用時使用 JIT 加速 ApEn/SampEn；不可用時 fallback 純 numpy
- [x] 11 項邊界條件全部通過

**驗收方式**：
```bash
pytest tests/momentum/test_entropy_indicators.py -v --tb=short
```

### 驗證檢查點
- PASS: BTCUSDT 12h 真實數據上 `compute_all()` 回傳 15 欄位，無例外
- PASS: Numba 不可用時仍正常運作（只是較慢）

**Checklist**：
- [x] `_resolve_series()` — apply_to 解析邏輯
- [x] `_compute_shannon_entropy()` — SPEC §4.1（rolling binning + H(X)）
- [x] `_compute_approximate_entropy()` — SPEC §4.2（Numba JIT / pure numpy）
- [x] `_compute_sample_entropy()` — SPEC §4.3（Numba JIT / pure numpy）
- [x] `_compute_hurst()` — SPEC §4.4（R/S analysis + log-log regression）
- [x] `_compute_fractal_dimension()` — SPEC §4.5（Higuchi method）
- [x] `_compute_permutation_entropy()` — SPEC §4.6（np.argsort + bincount）
- [x] `get_feature_metadata()` — 15 features 的 Metadata
- [x] Numba 條件 import 與 fallback
- [x] `HAS_NUMBA` flag
- [x] 逐指標 try/except 隔離
- [x] 11 項邊界條件覆蓋
- [x] 不 import `api.*`（Rule 1）

---

### Task 2.2.3：TailRiskIndicatorEngine（SPEC §5）

**檔案**：
- `momentum/FeatureEngineering/atomic/tail_risk_indicators.py` (新建)

**函式簽名**：

```python
import numpy as np
import pandas as pd
from typing import Dict, List
from momentum.core.logging import get_logger

logger = get_logger(__name__)

class TailRiskIndicatorEngine:
    """Layer 1 Indicator Engine: 高階分佈與尾部風險特徵。
    
    計算 6 類尾部風險指標（共 26 features），量化非對稱風險和極端事件。
    所有計算完全向量化（pandas/numpy），無 Python for 迴圈。
    
    Required data columns: close (計算 returns)
    
    指標列表（§5.1-§5.6）：
    1. CVaR / Expected Shortfall (§5.1) — 6 features
    2. Realized Volatility Decomposition (§5.2) — 9 features
    3. Up/Down Volatility Ratio (§5.3) — 3 features
    4. Gain-to-Pain Ratio (§5.4) — 3 features
    5. Jarque-Bera Statistic (§5.5) — 2 features
    6. Rolling Maximum Drawdown (§5.6) — 3 features
    """
    
    def __init__(self, config: Dict, data_sources: List[str]):
        """
        Args:
            config: tail_risk section from scan_config.yaml
            data_sources: 不使用（tail risk 使用 close returns），接受參數以符合 Engine 統一介面
        """
        self._config = config
        self._data_sources = data_sources
        self.windows = config.get('windows', [21, 55, 100])
        self.cvar_alphas = config.get('cvar_alphas', [0.01, 0.05])
        self.rv_windows = config.get('rv_windows', [13, 21, 55])
        self.mdd_windows = config.get('mdd_windows', [21, 55, 100])
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """計算所有尾部風險特徵。"""
    
    def get_feature_metadata(self) -> Dict[str, Dict]:
        """返回所有特徵的 Metadata。"""
    
    def _compute_cvar(self, returns: pd.Series) -> pd.DataFrame:
        """Rolling CVaR / Expected Shortfall（§5.1）
        
        CVaR_α = E[r | r ≤ VaR_α]
        使用 rolling quantile + 條件平均
        """
    
    def _compute_rv_decomposition(self, returns: pd.Series) -> pd.DataFrame:
        """Realized Volatility Decomposition + RSJ（§5.2）
        
        RV+ = sqrt(sum(r² * 1(r>0)))
        RV- = sqrt(sum(r² * 1(r<0)))
        RSJ = RV+ - RV-
        完全向量化。
        """
    
    def _compute_ud_vol_ratio(self, returns: pd.Series) -> pd.DataFrame:
        """Up/Down Volatility Ratio（§5.3）
        
        UDVR = RV+ / RV-
        邊界：RV- = 0 → NaN
        """
    
    def _compute_gpr(self, returns: pd.Series) -> pd.DataFrame:
        """Gain-to-Pain Ratio（§5.4）
        
        GPR = sum(gains) / |sum(losses)|
        邊界：全正/全負 → clip to [0, 100]
        """
    
    def _compute_jarque_bera(self, returns: pd.Series) -> pd.DataFrame:
        """Rolling Jarque-Bera Statistic（§5.5）
        
        JB = (n/6) * (S² + K²/4)
        使用 rolling.skew() 和 rolling.kurt()
        """
    
    def _compute_max_drawdown(self, close: pd.Series) -> pd.DataFrame:
        """Rolling Maximum Drawdown（§5.6）
        
        rolling_max → drawdown → rolling min
        完全向量化，O(N)。
        
        邊界：
        - 價格單調上漲 → MDD = 0
        - close 含 0 或負值 → NaN + WARNING
        """
```

**依賴**：numpy, pandas（全部向量化，無額外套件需求）

**輸出 Schema**（26 features，見 SPEC §5.7）：
```
tr_cvar_1pct_{21,55,100}               — 3 features
tr_cvar_5pct_{21,55,100}               — 3 features
tr_rv_up_{13,21,55}                    — 3 features
tr_rv_down_{13,21,55}                  — 3 features
tr_rsj_{13,21,55}                      — 3 features
tr_ud_vol_ratio_{13,21,55}             — 3 features
tr_gpr_{21,55,100}                     — 3 features
tr_jb_{55,100}                         — 2 features
tr_mdd_{21,55,100}                     — 3 features
Total: 26 features
```

**邊界條件（SPEC §5.8，11 項）**：

| # | 條件 | 預期行為 | 測試名 |
|---|------|---------|--------|
| 1 | 資料列數 < min window | 返回 NaN | `test_tail_risk_insufficient_data` |
| 2 | 全部 return = 0 | CVaR=0, RV=0, GPR→NaN, MDD=0 | `test_tail_risk_zero_returns` |
| 3 | 單方向 returns（全正/全負） | GPR clip to [0, 100] | `test_tail_risk_one_sided` |
| 4 | 窗口內只有 1 個負 return | CVaR = 該值 | `test_tail_risk_rare_negative` |
| 5 | RV_down = 0 | UDVR = NaN | `test_udvr_zero_downside` |
| 6 | 極端報酬（±50%） | 正常計算 | `test_tail_risk_extreme` |
| 7 | alpha 超出範圍（0 或 1） | raise ValueError in `__init__` | `test_cvar_invalid_alpha` |
| 8 | NaN 超過 50% | 返回 NaN | `test_tail_risk_many_nans` |
| 9 | MDD 窗口內價格單調上漲 | MDD = 0 | `test_mdd_monotonic_up` |
| 10 | MDD 窗口內價格單調下跌 | MDD = (first-last)/first | `test_mdd_monotonic_down` |
| 11 | close 含 0 或負值 | MDD = NaN + WARNING | `test_mdd_invalid_price` |

**驗收條件**：
- [x] 6 個指標全部正確計算，全向量化
- [x] 輸出 26 個特徵，命名符合 `tr_*` pattern
- [x] 11 項邊界條件全部通過

**驗收方式**：
```bash
pytest tests/momentum/test_tail_risk_indicators.py -v --tb=short
```

### 驗證檢查點
- PASS: 全部指標 100% 向量化（無 Python for 迴圈 on data rows）
- PASS: BTCUSDT 12h 真實數據 300 bars → 執行時間 < 200ms

**Checklist**：
- [x] `_compute_cvar()` — SPEC §5.1（rolling quantile + 條件平均）
- [x] `_compute_rv_decomposition()` — SPEC §5.2（向量化 RV+, RV-, RSJ）
- [x] `_compute_ud_vol_ratio()` — SPEC §5.3
- [x] `_compute_gpr()` — SPEC §5.4（GPR clip [0, 100]）
- [x] `_compute_jarque_bera()` — SPEC §5.5（rolling skew/kurt）
- [x] `_compute_max_drawdown()` — SPEC §5.6（O(N) 向量化）
- [x] `get_feature_metadata()` — 26 features
- [x] 逐指標 try/except 隔離
- [x] cvar_alphas 驗證
- [x] 11 項邊界條件覆蓋
- [x] 不 import `api.*`（Rule 1）

---

### Task 2.2.4：atomic/__init__.py 更新匯出

**檔案**：
- `momentum/FeatureEngineering/atomic/__init__.py` (修改)

**修改內容**：

在既有匯出之後新增：

```python
# === 既有匯出（不修改） ===
from .trend_indicators import TrendIndicatorEngine
from .momentum_indicators import MomentumIndicatorEngine
from .volatility_indicators import VolatilityIndicatorEngine
from .volume_indicators import VolumeIndicatorEngine
from .cycle_indicators import CycleIndicatorEngine
from .pattern_indicators import PatternIndicatorEngine
from .statistics_indicators import StatisticsIndicatorEngine
from .custom_indicators import CustomIndicatorEngine

# === 新增匯出 ===
from .microstructure_indicators import MicrostructureIndicatorEngine
from .entropy_indicators import EntropyIndicatorEngine
from .tail_risk_indicators import TailRiskIndicatorEngine
```

**依賴**：Task 2.2.1, 2.2.2, 2.2.3

**驗收條件**：
- [x] `from momentum.FeatureEngineering.atomic import MicrostructureIndicatorEngine` 成功
- [x] `from momentum.FeatureEngineering.atomic import EntropyIndicatorEngine` 成功
- [x] `from momentum.FeatureEngineering.atomic import TailRiskIndicatorEngine` 成功
- [x] 既有 8 個 Engine 的匯出不受影響

**驗收方式**：
```bash
python -c "from momentum.FeatureEngineering.atomic import MicrostructureIndicatorEngine, EntropyIndicatorEngine, TailRiskIndicatorEngine; print('OK')"
```

### 驗證檢查點
- PASS: 成功路徑 — 三個新增 Engine 皆可被 `momentum.FeatureEngineering.atomic` 匯入，且既有 8 個 Engine 匯入不受影響
- PASS: 失敗/邊界路徑 — 任一新 Engine 檔案暫不可用時，錯誤僅發生於該匯入，能明確定位到對應 import（不改變其他 Task 的責任範圍）

**Checklist**：
- [x] 新增 3 行 import
- [x] 既有匯出不修改
- [x] import 驗證通過

---

## Phase 2.3：Layer 6.5 前處理層

### Task 2.3.1：preprocessing 目錄 + FeaturePreprocessor（SPEC §6）

**檔案**：
- `momentum/FeatureEngineering/preprocessing/__init__.py` (新建)
- `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` (新建)

**`preprocessing/__init__.py`**：
```python
from .feature_preprocessor import FeaturePreprocessor
```

**函式簽名**：

```python
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union
from momentum.core.logging import get_logger

logger = get_logger(__name__)

# Optional: statsmodels for ADF
try:
    from statsmodels.tsa.stattools import adfuller
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logger.warning("statsmodels not available, ADF/Fractional Differencing disabled")

class FeaturePreprocessor:
    """Layer 6.5: 特徵前處理與正規化。
    
    在所有特徵生成後（Layer 0-6），對 features DataFrame 做統一的
    前處理/正規化轉換，然後交給 Layer 7 validation。
    
    六種轉換（各自可獨立啟用/停用）：
    1. Winsorization (極端值裁剪) — §6.5
    2. ADF + Auto-Differencing (整數差分) — §6.3
    3. Fractional Differencing (分數差分) — §6.6（推薦，較 §6.3 保留更多記憶）
    4. Cross-Sectional Rank Transform — §6.1
    5. Quantile-to-Gaussian Normalization — §6.2
    6. Adaptive Z-Score — §6.4
    
    執行順序（固定）：
    Winsorization → Fractional Differencing / ADF → Rank Transform → Gaussian → Z-Score
    
    設計說明：
    - Winsorization 先做，避免極端值影響後續統計
    - 差分處理非定態（Fractional 優先，ADF fallback）
    - Rank/Gaussian 是分佈轉換
    - Z-Score 最後做標準化
    - Winsorization 是 in-place 修改（不新增欄位）
    - 其他 transform 在 'append' mode 新增帶 suffix 的欄位
    """
    
    def __init__(self, config: Dict):
        """
        Args:
            config: preprocessing section from scan_config.yaml
        """
        self.rank_config = config.get('rank_transform', {})
        self.gaussian_config = config.get('gaussian_normalize', {})
        self.adf_config = config.get('adf_differencing', {})
        self.zscore_config = config.get('adaptive_zscore', {})
        self.winsor_config = config.get('winsorization', {})
        self.fracdiff_config = config.get('fractional_differencing', {})
        self.mode = config.get('mode', 'append')
    
    def transform(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """對所有特徵做前處理/正規化（固定執行順序）。
        
        Args:
            features_df: 所有 Layer 0-6 產出的特徵 DataFrame
        
        Returns:
            處理後的 DataFrame
        """
    
    def _apply_winsorization(self, df: pd.DataFrame) -> pd.DataFrame:
        """Winsorization（§6.5）— in-place 修改。
        
        method='sigma': clip to [μ-kσ, μ+kσ]
        method='quantile': clip to [Q_lower, Q_upper]
        """
    
    def _apply_fractional_differencing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fractional Differencing（§6.6 — 推薦）。
        
        使用 Fixed-Width Window FFD + 二分搜尋最小 d*。
        快取 d* 避免每次重算。
        
        邊界：
        - d* 搜尋收斂失敗 → fallback d=1.0 + WARNING
        - 權重長度 > 資料長度 → 截斷權重
        - ADF 和 FracDiff 同時啟用 → FracDiff 優先，ADF skip 已處理欄位
        """
    
    def _apply_adf_differencing(self, df: pd.DataFrame) -> pd.DataFrame:
        """ADF + Auto-Differencing（§6.3）。
        
        對每個非定態特徵做整數差分。
        邊界：NaN 過多 → skip + 保留原始
        """
    
    def _apply_rank_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cross-Sectional Rank Transform（§6.1）。
        
        ranked = series.rolling(window).rank(pct=True)
        Output suffix: _rank
        """
    
    def _apply_gaussian_normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Quantile-to-Gaussian（§6.2）。
        
        clip to [0.001, 0.999] → scipy.special.erfinv
        Output suffix: _gaussian
        """
    
    def _apply_adaptive_zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adaptive Z-Score（§6.4）。
        
        z = (x - rolling_mean) / (rolling_std + epsilon)
        Output suffix: _zscore
        """
    
    def _select_columns(self, df: pd.DataFrame, apply_to: Union[str, List[str]]) -> List[str]:
        """根據 apply_to 配置選擇要處理的欄位。
        
        支援：
        - 'all': 所有數值欄位
        - 'non_stationary': 只處理未通過 ADF 的欄位
        - 'layer1_only': 只處理 Layer 1 atomic indicators
        - regex pattern: match column names
        - list: 明確列出欄位名稱
        """
    
    # --- Fractional Differencing 核心函式（§6.6） ---
    
    @staticmethod
    def _get_weights_ffd(d: float, threshold: float = 1e-5) -> np.ndarray:
        """計算 FFD 權重。"""
    
    @staticmethod
    def _frac_diff_ffd(series: pd.Series, d: float, threshold: float = 1e-5) -> pd.Series:
        """Fixed-Width Window Fractional Differencing（向量化 np.convolve）。"""
    
    def _find_min_d(self, series: pd.Series, adf_threshold: float = 0.05,
                    d_range: Tuple[float, float] = (0.0, 1.0),
                    precision: float = 0.01) -> float:
        """二分搜尋最小 d* 使序列通過 ADF 定態性檢定。"""
    
    def _load_d_star_cache(self, symbol: str, timeframe: str) -> Dict[str, float]:
        """載入 d* 快取（JSON）。"""
    
    def _save_d_star_cache(self, symbol: str, timeframe: str, cache: Dict[str, float]) -> None:
        """儲存 d* 快取。"""
```

**依賴**：numpy, pandas; Optional: scipy.special.erfinv (Gaussian), statsmodels (ADF/FracDiff)

**邊界條件（SPEC §6.8，12 項）**：

| # | 條件 | 預期行為 | 測試名 |
|---|------|---------|--------|
| 1 | 空 DataFrame | 返回空 DataFrame | `test_preprocess_empty_df` |
| 2 | 全部 NaN 欄位 | 轉換後仍為 NaN | `test_preprocess_all_nan_column` |
| 3 | 單一值欄位（std=0） | Z-Score=0, Rank=0.5, Gaussian=0 | `test_preprocess_constant_column` |
| 4 | ADF 遇到 NaN 過多 | skip 差分，保留原始 | `test_adf_nan_heavy` |
| 5 | Gaussian 邊界值（0 或 1） | clip to [0.001, 0.999] | `test_gaussian_boundary` |
| 6 | Winsorization 使 std=0 | 不影響後續 zscore | `test_winsor_then_zscore` |
| 7 | replace mode | 原位修改，column count 不變 | `test_preprocess_replace_mode` |
| 8 | append mode | 新增帶 suffix 欄位，原始不變 | `test_preprocess_append_mode` |
| 9 | 1000+ 欄位大 DataFrame | < 30s | `test_preprocess_performance` |
| 10 | FracDiff d* 搜尋收斂失敗 | d=1.0 fallback + WARNING | `test_fracdiff_convergence_failure` |
| 11 | FracDiff 權重長度 > 資料長度 | 截斷，前 width-1 個 NaN | `test_fracdiff_short_data` |
| 12 | ADF 和 FracDiff 同時啟用 | FracDiff 優先，ADF skip 已處理 | `test_fracdiff_adf_coexist` |

**驗收條件**：
- [x] 6 種轉換全部正確實作
- [x] 執行順序固定：Winsor → FracDiff/ADF → Rank → Gaussian → Z-Score
- [x] append mode 正確新增帶 suffix 欄位
- [x] replace mode 原位修改
- [x] d* 快取正常運作
- [x] Optional 套件降級（statsmodels 不可用 → ADF/FracDiff disabled）
- [x] 12 項邊界條件全部通過

**驗收方式**：
```bash
pytest tests/momentum/test_feature_preprocessor.py -v --tb=short
```

### 驗證檢查點
- PASS: transform() 的執行順序不受 config 順序影響（固定程式碼順序）
- PASS: append mode 的輸出 column count > 輸入 column count
- PASS: replace mode 的輸出 column count == 輸入 column count

**Checklist**：
- [x] `preprocessing/` 目錄建立
- [x] `preprocessing/__init__.py`
- [x] `FeaturePreprocessor.__init__` — Config 解析
- [x] `transform()` — 固定順序執行 6 種轉換
- [x] `_apply_winsorization()` — SPEC §6.5（sigma / quantile）
- [x] `_apply_fractional_differencing()` — SPEC §6.6（FFD + d* 二分搜尋）
- [x] `_get_weights_ffd()` — 權重計算
- [x] `_frac_diff_ffd()` — 向量化卷積
- [x] `_find_min_d()` — 二分搜尋
- [x] `_load_d_star_cache()` / `_save_d_star_cache()` — JSON 快取
- [x] `_apply_adf_differencing()` — SPEC §6.3
- [x] `_apply_rank_transform()` — SPEC §6.1（rolling.rank(pct=True)）
- [x] `_apply_gaussian_normalize()` — SPEC §6.2（erfinv）
- [x] `_apply_adaptive_zscore()` — SPEC §6.4
- [x] `_select_columns()` — apply_to 解析（all / non_stationary / regex / list）
- [x] statsmodels 條件 import + `HAS_STATSMODELS` flag
- [x] mode 切換（append / replace）
- [x] 12 項邊界條件覆蓋
- [x] 不 import `api.*`（Rule 1）

---

## Phase 2.4：Pipeline 整合

### Task 2.4.1：feature_factory.py 修改（SPEC §7.1）

**檔案**：
- `momentum/FeatureEngineering/feature_factory.py` (修改)

**修改內容**：

#### 修改 1：新增 import（檔案頂部）

```python
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine
from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
```

#### 修改 2：`_layer1_atomic_indicators` 方法尾部新增

在既有 `CustomIndicatorEngine` block 之前（statistics block 之後）新增。  
**注意**：不使用 `hasattr`——Pydantic 預設值確保這些欄位始終存在，與既有 trend/momentum/... pattern 一致。

```python
# === 新增 3 個引擎（SPEC §7.1 擴展後）===
# 插入位置：statistics block 之後，custom_indicators block 之前

if config.atomic_indicators.microstructure.enabled:
    engine = MicrostructureIndicatorEngine(
        config.atomic_indicators.microstructure.model_dump(),
        sources
    )
    frames.append(engine.compute_all(data))

if config.atomic_indicators.entropy.enabled:
    engine = EntropyIndicatorEngine(
        config.atomic_indicators.entropy.model_dump(),
        sources
    )
    frames.append(engine.compute_all(data))

if config.atomic_indicators.tail_risk.enabled:
    engine = TailRiskIndicatorEngine(
        config.atomic_indicators.tail_risk.model_dump(),
        sources
    )
    frames.append(engine.compute_all(data))
```

#### 修改 3：`generate_features` 方法中，layer6 之後新增 Layer 6.5

在現有程式碼中，`_layer7_validate_and_persist` 的呼叫如下：

```python
# 現有程式碼（修改前）
result = self._layer7_validate_and_persist(
    symbol, timeframe, raw_data,
    [layer1, layer2, layer3, layer4, layer5, layer6],
    config, time.time() - start_time, config_hash,
)
```

**修改為**：

```python
# 修改後：插入 Layer 6.5
layers = [layer1, layer2, layer3, layer4, layer5, layer6]

# Layer 6.5: Preprocessing（僅在 config.preprocessing.enabled 時啟用）
if config.preprocessing.enabled:
    all_features = self._combine_layers(layers)
    preprocessed = self._safe_execute(
        "Layer 6.5", self._layer6_5_preprocessing, all_features, config
    )
    if not preprocessed.empty:
        layers = [preprocessed]

result = self._layer7_validate_and_persist(
    symbol, timeframe, raw_data,
    layers, config, time.time() - start_time, config_hash,
)
```

> **向後相容**：`preprocessing.enabled` 預設 `False`（Pydantic 預設值），因此 Layer 6.5 不會被執行。

#### 修改 4：新增 `_layer6_5_preprocessing` 和 `_combine_layers` 方法

```python
def _layer6_5_preprocessing(self, all_features: pd.DataFrame, config) -> pd.DataFrame:
    """Layer 6.5: Feature Preprocessing & Normalization（SPEC §6）。"""
    preprocessor = FeaturePreprocessor(config.preprocessing.model_dump())
    return preprocessor.transform(all_features)

def _combine_layers(self, layers: List[pd.DataFrame]) -> pd.DataFrame:
    """合併多個 Layer 的 DataFrame。"""
    non_empty = [l for l in layers if not l.empty]
    if not non_empty:
        return pd.DataFrame()
    return pd.concat(non_empty, axis=1)
```

**hasattr 防護說明**：不使用 `hasattr`。Pydantic Model 的預設值機制 + `FactoryConfig` 的 `model_config = ConfigDict(extra=\"allow\")` 確保向後相容——舊版 YAML（未包含新 section）會使用 `enabled: false` 預設，不會觸發 `AttributeError`。此設計與既有 `trend`/`momentum`/... pattern 完全一致。

**依賴**：Task 2.2.4 + Task 2.3.1

**驗收條件**：
- [x] 全部新引擎 disabled 時，pipeline 行為完全不變（向後相容）
- [x] 啟用 microstructure 後，pipeline 輸出包含 `ms_*` 欄位
- [x] 啟用 entropy 後，pipeline 輸出包含 `ent_*` 欄位
- [x] 啟用 tail_risk 後，pipeline 輸出包含 `tr_*` 欄位
- [x] 啟用 preprocessing 後，pipeline 輸出包含 `_rank` / `_zscore` suffix 欄位
- [x] 單一新引擎失敗時，其他引擎正常運作
- [x] Layer 0 失敗仍直接 raise（不可恢復）
- [x] 修復 Layer 2 指標註冊問題：`MIDPOINT`/`MIDPRICE` 可正常計算
- [x] 修復 Layer 1 動量指標參數衝突：`PLUS_DM`/`MINUS_DM` 不再出現 `timeperiod` 重複傳參錯誤
- [x] 修復 Layer 3 重複欄名情境：`RollingAggregator` 不再觸發 scalar `rename` 例外

**驗收方式**：
```bash
# 基本整合驗證
python -c "
from momentum.factories import create_feature_factory
f = create_feature_factory()
result = f.generate_features('BTCUSDT', '12h', config_override={
    'atomic_indicators': {
        'microstructure': {'enabled': True},
        'tail_risk': {'enabled': True}
    }
})
print(f'Features: {result.feature_count}')
print([c for c in result.features_df.columns if c.startswith('ms_')][:5])
print([c for c in result.features_df.columns if c.startswith('tr_')][:5])
"
```

### 驗證檢查點
- PASS: `generate_features()` 在全部新引擎 disabled 時輸出完全相同（binary comparison）
- PASS: 啟用全部新引擎 + preprocessing 時，feature_count 增加約 66 + preprocessing 膨脹
- PASS: 強制重算（`force_regenerate=True`）全流程驗證通過；日誌 `test_results/full_validation_fix3_force_20260217_135612.log`，摘要為 `feature_count=30309`、`rows=657`、`cols=30309`
- PASS: 已知錯誤字串清空（`Indicator not registered: MIDPOINT/MIDPRICE`、`PLUS_DM()/MINUS_DM() got multiple values`、`Layer 2 failed`、`Layer 3 failed`、`close_trend_MAVP_Slope_W5`）

**Checklist**：
- [x] 新增 4 行 import（頂部）
- [x] `_layer1_atomic_indicators` 新增 3 個引擎建構（匹配既有 `config.atomic_indicators.X.enabled` pattern）
- [x] `generate_features` 新增 Layer 6.5 邏輯（`config.preprocessing.enabled`）
- [x] `_layer6_5_preprocessing()` 方法
- [x] `_combine_layers()` 方法
- [x] 既有 Layer 0-7 不修改
- [x] 向後相容性驗證（preprocessing 預設 disabled，新引擎預設 disabled）
- [x] 不 import `api.*`
- [x] `TALibWrapper` 新增/修正註冊：`MIDPOINT`、`MIDPRICE`
- [x] `TALibWrapper` 輸入型別修正：`PLUS_DM`、`MINUS_DM` 改為 `hl`
- [x] `RollingAggregator` 修正重複欄名存取：以位置索引保證 `Series`
- [x] 回歸測試補齊：`tests/test_feature_factory_operators.py`（MIDPOINT/MIDPRICE/PLUS_DM/duplicate columns）

---

## Phase 2.5：測試與驗收

### Task 2.5.1：單元測試（SPEC §13.1 — ~122 測試）

**檔案**：
- `tests/momentum/test_microstructure_indicators.py` (新建)
- `tests/momentum/test_entropy_indicators.py` (新建)
- `tests/momentum/test_tail_risk_indicators.py` (新建)
- `tests/momentum/test_feature_preprocessor.py` (新建)

**測試結構**：

```python
# tests/momentum/test_microstructure_indicators.py (~30 tests)
import pytest
import pandas as pd
import numpy as np
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine

@pytest.fixture(scope="module")
def btcusdt_data():
    """載入 BTCUSDT 12h 真實數據"""
    from momentum.factories import create_kline_storage_manager
    storage = create_kline_storage_manager()
    return storage.read_klines("BTCUSDT", "12h")

@pytest.fixture
def default_engine():
    config = {"windows": [5, 13, 21, 55], "epsilon": 1e-10, ...}
    return MicrostructureIndicatorEngine(config, [])

# === 正確性測試 ===
class TestMicrostructureCorrectness:
    def test_amihud_basic(self, default_engine, btcusdt_data): ...
    def test_kyle_lambda_basic(self, default_engine, btcusdt_data): ...
    def test_roll_spread_basic(self, default_engine, btcusdt_data): ...
    def test_cs_spread_basic(self, default_engine, btcusdt_data): ...
    def test_ofi_basic(self, default_engine, btcusdt_data): ...
    def test_large_trade_ratio_basic(self, default_engine, btcusdt_data): ...
    def test_vpin_basic(self, default_engine, btcusdt_data): ...

# === 邊界條件測試（SPEC §3.9 × 11 項） ===
class TestMicrostructureBoundary:
    def test_amihud_zero_volume(self): ...            # §3.9 #1
    def test_ltr_zero_trades(self): ...               # §3.9 #2
    def test_micro_insufficient_data(self): ...       # §3.9 #3
    def test_constant_price(self): ...                # §3.9 #4
    def test_ofi_fallback(self): ...                  # §3.9 #5
    def test_volume_spike(self): ...                  # §3.9 #6
    def test_zero_range_bar(self): ...                # §3.9 #7
    def test_roll_positive_autocov(self): ...         # §3.9 #8
    def test_vpin_zero_volume(self): ...              # §3.9 #9
    def test_vpin_zero_sigma(self): ...               # §3.9 #10
    def test_micro_feature_name_unique(self): ...     # §3.9 #11

# === Metadata 測試 ===
class TestMicrostructureMetadata:
    def test_feature_metadata_count(self, default_engine): ...
    def test_feature_metadata_format(self, default_engine): ...

# === 降級測試（SPEC §10.3） ===
class TestMicrostructureDegradation:
    def test_degrade_missing_taker_buy_vol(self): ...
    def test_degrade_missing_taker_ratio(self): ...
    def test_degrade_missing_trades(self): ...
    def test_degrade_missing_quote_volume(self): ...

# === compute_all 整體測試 ===
class TestMicrostructureComputeAll:
    def test_compute_all_output_shape(self, default_engine, btcusdt_data): ...
    def test_compute_all_feature_names(self, default_engine, btcusdt_data): ...
    def test_compute_all_partial_failure(self): ...
```

**各模組測試數量**：

| 模組 | 正確性 | 邊界條件 | Metadata | 降級 | 其他 | 合計 |
|------|--------|---------|----------|------|------|------|
| Microstructure | 7 | 11 | 2 | 4 | 6 | ~30 |
| Entropy | 6 | 11 | 2 | 2 | 7 | ~28 |
| Tail Risk | 6 | 11 | 2 | 0 | 7 | ~26 |
| Preprocessor | 6 | 12 | 0 | 2 | 12 | ~32 |
| **合計** | | | | | | **~116** |

加上降級場景（§10.3 × 4 + §10.4 × 2 = 6）共 **~122 測試**。

**依賴**：ALL Phase 2.1-2.4

**驗收條件**：
- [x] 所有 122 測試 PASS
- [x] 51 項邊界條件 100% 覆蓋
- [x] 使用真實數據（BTCUSDT 12h HDF5），非假數據

**驗收方式**：
```bash
pytest tests/momentum/test_microstructure_indicators.py tests/momentum/test_entropy_indicators.py tests/momentum/test_tail_risk_indicators.py tests/momentum/test_feature_preprocessor.py -v --tb=short
```

### 驗證檢查點
- PASS: `pytest ... -v --tb=short` 全部 PASS
- PASS: 無使用假數據（grep -r "random\." tests/momentum/test_*_indicators.py 為 0）

**Checklist**：
- [x] `test_microstructure_indicators.py` — ~30 tests
- [x] `test_entropy_indicators.py` — ~28 tests
- [x] `test_tail_risk_indicators.py` — ~26 tests
- [x] `test_feature_preprocessor.py` — ~32 tests + 降級 6 tests
- [x] 邊界條件 51 項全覆蓋（SPEC §3.9 + §4.8 + §5.8 + §6.8 + §10.3 + §10.4）
- [x] 真實數據 fixture
- [x] 不依賴 `run_api.py`（Rule 6）

---

### Task 2.5.2：整合測試（SPEC §13.2 — 7 測試）

**檔案**：
- `tests/momentum/test_feature_factory_optimization_e2e.py` (新建)

**測試內容**：

```python
# tests/momentum/test_feature_factory_optimization_e2e.py

class TestOptimizationE2E:
    """端對端整合測試：驗證新引擎在完整 pipeline 中的行為。"""
    
    def test_pipeline_with_microstructure(self):
        """啟用 microstructure → Layer 1 output 包含 ms_* 欄位"""
    
    def test_pipeline_with_entropy(self):
        """啟用 entropy → Layer 1 output 包含 ent_* 欄位"""
    
    def test_pipeline_with_tail_risk(self):
        """啟用 tail_risk → Layer 1 output 包含 tr_* 欄位"""
    
    def test_pipeline_with_preprocessing(self):
        """啟用 preprocessing → Layer 6.5 output 有 _rank/_zscore suffix"""
    
    def test_pipeline_all_new_features(self):
        """全部啟用 → feature count 增加、Layer 7 validation 通過"""
    
    def test_pipeline_backward_compatible(self):
        """全部新功能 disabled → pipeline 行為完全不變"""
    
    def test_pipeline_partial_engine_failure(self):
        """一個新引擎失敗 → 其他正常、pipeline 完成"""
```

**驗收條件**：
- [x] 7 個整合測試全部 PASS

**驗收方式**：
```bash
pytest tests/momentum/test_feature_factory_optimization_e2e.py -v --tb=short
```

### 驗證檢查點
- PASS: 成功路徑 — 7 個 E2E 測試全數 PASS，且 `test_pipeline_all_new_features` 能驗證新特徵有進入 Layer 7 驗證流程
- PASS: 失敗/邊界路徑 — `test_pipeline_partial_engine_failure` PASS，證明單一新引擎失敗時 pipeline 仍可完成，符合本 Task 原責任

**Checklist**：
- [x] 7 個 E2E 測試
- [x] 使用 `create_feature_factory()` 建構（Rule 3）
- [x] 向後相容性驗證（disabled 時不影響）

---

### Task 2.5.3：效能測試（SPEC §13.3 — 5 測試）

**檔案**：
- `tests/momentum/test_feature_factory_optimization_perf.py` (新建)

**測試內容與目標**（SPEC §14.1）：

| 測試 | 目標（M1 Mac, 300 bars） | 條件 |
|------|--------------------------|------|
| `test_microstructure_performance` | < 500ms | 全部 windows |
| `test_entropy_performance` | < 5s（含 Numba warmup）| ApEn/SampEn(window=100) |
| `test_tail_risk_performance` | < 200ms | 全部指標 |
| `test_preprocessing_performance` | < 30s | 1000 features × 300 bars |
| `test_full_pipeline_overhead` | overhead < 50% | 全部新功能啟用 vs 禁用 |

**驗收方式**：
```bash
pytest tests/momentum/test_feature_factory_optimization_perf.py -v --tb=short -s
```

### 驗證檢查點
- PASS: 成功路徑 — 5 個效能測試皆執行並達成各自門檻（含 `test_full_pipeline_overhead` < 50%）
- PASS: 失敗/邊界路徑 — 任一效能門檻未達時，對應測試明確 fail 並輸出超標項目，能直接對應 §14 目標而不擴張責任範圍

**Checklist**：
- [x] 5 個效能測試
- [x] 使用 `time.time()` 或 `timeit` 計量
- [x] M1 Mac 為基準硬體

---

### Task 2.5.4：驗收報告（SPEC §15）

**驗收清單彙整**：

#### 功能驗收（SPEC §15.1）
- [x] 微觀結構引擎：7 指標（含 VPIN）正確計算，命名 `ms_*`
- [x] 資訊理論引擎：6 指標（含 Permutation Entropy）正確計算，命名 `ent_*`
- [x] 尾部風險引擎：6 指標（含 Rolling MDD）正確計算，命名 `tr_*`
- [x] 前處理器：6 種轉換（含 Fractional Differencing）正確，支援 append/replace
- [x] Config-Driven：預設 disabled，顯式啟用正常運作
- [x] 向後相容：禁用所有新功能時 pipeline 不變

#### 品質驗收（SPEC §15.2）
- [x] 向量化計算（排除 ApEn/SampEn Numba、FracDiff d* 搜尋、Hurst/Fractal rolling.apply）
- [x] 51 項邊界測試全 PASS
- [x] 測試覆蓋率 ≥ 90%
- [x] 無 hardcoded 數據
- [x] Logging 符合 §12 規範

#### 架構驗收（SPEC §15.3）
- [x] Rule 1: `momentum/` 不 import `api/`
- [x] Rule 2: 無 cross-domain 直接 import
- [x] Rule 5: Config 從 `scan_config.yaml` 讀取
- [x] Rule 6: 測試獨立運行，不需 `run_api.py`
- [x] Engine 建構子簽名一致：`__init__(self, config: Dict, data_sources: List[str])`
- [x] 所有 Engine 實作 `get_feature_metadata()`

#### 效能驗收（SPEC §15.4）
- [x] §14 所有效能目標達成
- [x] 全部新功能啟用時 pipeline overhead < 50%
- [x] d* 快取正常運作

**最終驗證命令**：
```bash
# 1. Architecture Rule 1
grep -rn "from api\." momentum/FeatureEngineering/atomic/microstructure_indicators.py
grep -rn "from api\." momentum/FeatureEngineering/atomic/entropy_indicators.py
grep -rn "from api\." momentum/FeatureEngineering/atomic/tail_risk_indicators.py
grep -rn "from api\." momentum/FeatureEngineering/preprocessing/feature_preprocessor.py
# 期望：全部 0 結果

# 2. 全部測試
pytest tests/momentum/test_microstructure_indicators.py tests/momentum/test_entropy_indicators.py tests/momentum/test_tail_risk_indicators.py tests/momentum/test_feature_preprocessor.py tests/momentum/test_feature_factory_optimization_e2e.py -v --tb=short

# 3. E2E 驗證
python -c "
from momentum.factories import create_feature_factory
f = create_feature_factory()
# 全部啟用
result = f.generate_features('BTCUSDT', '12h', config_override={
    'atomic_indicators': {
        'microstructure': {'enabled': True},
        'entropy': {'enabled': True},
        'tail_risk': {'enabled': True}
    },
    'preprocessing': {'enabled': True}
})
print(f'Total features: {result.feature_count}')
print(f'Generation time: {result.generation_time:.2f}s')
print(f'Layer counts: {result.layer_counts}')
ms = [c for c in result.features_df.columns if c.startswith('ms_')]
ent = [c for c in result.features_df.columns if c.startswith('ent_')]
tr = [c for c in result.features_df.columns if c.startswith('tr_')]
print(f'Microstructure: {len(ms)} features')
print(f'Entropy: {len(ent)} features')
print(f'Tail Risk: {len(tr)} features')
"
```

**Checklist**：
- [x] 功能驗收 6 項全 PASS
- [x] 品質驗收 5 項全 PASS
- [x] 架構驗收 6 項全 PASS
- [x] 效能驗收 3 項全 PASS

### 驗證檢查點
- PASS: 成功路徑 — 四類驗收清單（功能/品質/架構/效能）所有勾選項均可由「最終驗證命令」產生對應證據
- PASS: 失敗/邊界路徑 — 任一驗收項未達成時，驗收報告保留未勾選狀態並回指對應命令輸出，不以口頭結論替代可測證據

---

## 測試 Fixtures（conftest.py 模板）

```python
# tests/momentum/conftest_optimization.py
# 或直接放在 tests/momentum/conftest.py 中

import pytest
import pandas as pd
import numpy as np


@pytest.fixture(scope="session")
def btcusdt_12h_data():
    """載入 BTCUSDT 12h 真實 K 線數據（session 級別快取）。
    
    所有優化測試共用此 fixture，避免重複 IO。
    """
    from momentum.factories import create_kline_storage_manager
    storage = create_kline_storage_manager()
    data = storage.read_klines("BTCUSDT", "12h")
    assert len(data) > 100, "測試需要至少 100 bars 的數據"
    return data


@pytest.fixture
def sample_ohlcv_300():
    """取 BTCUSDT 前 300 bars 作為效能測試基準。"""
    from momentum.factories import create_kline_storage_manager
    storage = create_kline_storage_manager()
    data = storage.read_klines("BTCUSDT", "12h")
    return data.head(300)


@pytest.fixture
def microstructure_config():
    """微觀結構引擎預設配置。"""
    return {
        "windows": [5, 13, 21, 55],
        "epsilon": 1e-10,
        "min_trades": 1,
        "enabled_features": "all",
        "cs_spread_smooth": [5, 13, 21],
        "ofi_raw": True,
        "kyle_lambda_windows": [13, 21, 55],
        "vpin_n_buckets": [30, 50],
        "vpin_zscore_windows": [21, 55],
    }


@pytest.fixture
def entropy_config():
    """資訊理論引擎預設配置。"""
    return {
        "windows": [55, 100],
        "n_bins": 10,
        "apen_m": 2,
        "apen_r_ratio": 0.2,
        "hurst_windows": [55, 100, 200],
        "fractal_kmax": 10,
        "use_numba": True,
        "perm_m": 3,
        "perm_windows": [21, 55, 100],
        "apply_to": ["close_return"],
        "shannon_windows": [21, 55, 100],
    }


@pytest.fixture
def tail_risk_config():
    """尾部風險引擎預設配置。"""
    return {
        "windows": [21, 55, 100],
        "cvar_alphas": [0.01, 0.05],
        "rv_windows": [13, 21, 55],
        "mdd_windows": [21, 55, 100],
    }


@pytest.fixture
def preprocessing_config():
    """前處理層預設配置。"""
    return {
        "mode": "append",
        "winsorization": {"enabled": True, "method": "sigma", "sigma_k": 3.0},
        "adf_differencing": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "rank_transform": {"enabled": True, "window": 252},
        "gaussian_normalize": {"enabled": False},
        "adaptive_zscore": {"enabled": True, "windows": [100, 252], "epsilon": 1e-8},
    }


@pytest.fixture
def constant_df():
    """全部為常數值的 DataFrame（用於邊界條件測試）。"""
    idx = pd.date_range("2024-01-01", periods=100, freq="12h")
    return pd.DataFrame({
        "close": 50000.0,
        "high": 50000.0,
        "low": 50000.0,
        "open": 50000.0,
        "volume": 100.0,
        "quote_volume": 5000000.0,
        "taker_buy_volume": 50.0,
        "taker_ratio": 0.5,
        "trades": 1000,
    }, index=idx)


@pytest.fixture
def nan_heavy_df():
    """含大量 NaN 的 DataFrame（>50%，用於邊界條件測試）。"""
    idx = pd.date_range("2024-01-01", periods=100, freq="12h")
    df = pd.DataFrame({
        "close": np.random.uniform(40000, 60000, 100),
        "volume": np.random.uniform(100, 1000, 100),
    }, index=idx)
    df.iloc[:60] = np.nan  # 60% NaN
    return df
```

---

## AI Agent 每 Task 完成後驗證命令

| Task | 驗證命令 |
|------|---------|
| 2.1.1 | `python -c "from momentum.FeatureEngineering.feature_config import MicrostructureConfig, EntropyConfig, TailRiskConfig, PreprocessingConfig; print('Config Models OK')"` |
| 2.1.2 | `python -c "from momentum.FeatureEngineering.config_manager import ConfigManager; cm = ConfigManager(); c = cm.get_merged_config(); print(f'microstructure enabled: {c.atomic_indicators.microstructure.enabled}')"` |
| 2.1.3 | `python -c "from momentum.FeatureEngineering.config_manager import ConfigManager; cm = ConfigManager(); c = cm.get_merged_config({'atomic_indicators':{'microstructure':{'enabled':True}}}); p = cm.preview_feature_count(c); print(f'microstructure: {p.breakdown.get(\"microstructure\", 0)}')"` |
| 2.2.1 | `pytest tests/momentum/test_microstructure_indicators.py -v --tb=short` |
| 2.2.2 | `pytest tests/momentum/test_entropy_indicators.py -v --tb=short` |
| 2.2.3 | `pytest tests/momentum/test_tail_risk_indicators.py -v --tb=short` |
| 2.2.4 | `python -c "from momentum.FeatureEngineering.atomic import MicrostructureIndicatorEngine, EntropyIndicatorEngine, TailRiskIndicatorEngine; print('Import OK')"` |
| 2.3.1 | `pytest tests/momentum/test_feature_preprocessor.py -v --tb=short` |
| 2.4.1 | `python -c "from momentum.factories import create_feature_factory; f = create_feature_factory(); r = f.generate_features('BTCUSDT', '12h', config_override={'atomic_indicators':{'microstructure':{'enabled':True}}}); print(f'Features: {r.feature_count}')"` |
| 2.5.1 | `pytest tests/momentum/test_*_indicators.py tests/momentum/test_feature_preprocessor.py -v --tb=short` |
| 2.5.2 | `pytest tests/momentum/test_feature_factory_optimization_e2e.py -v --tb=short` |
| 2.5.3 | `pytest tests/momentum/test_feature_factory_optimization_perf.py -v -s` |
| 2.5.4 | 全部驗收命令（見上方 §15 區塊） |

---

## 錯誤處理與降級策略（SPEC §10 對應）

### 引擎級別隔離（§10.1）

每個新引擎在 `_safe_execute()` 內執行。失敗時：
1. ERROR log（含 `exc_info=True`）
2. 返回空 DataFrame
3. Pipeline 繼續

### 指標級別降級（§10.2）

引擎內部 `compute_all()` 逐指標 try/except：
```python
for name, method in methods:
    try:
        frames.append(method(data))
    except Exception as e:
        logger.warning(f"Indicator {name} failed: {e}")
```

### 欄位缺失降級（§10.3）

| 缺失欄位 | 影響 | 降級行為 | 對應 Task |
|---------|------|---------|----------|
| `taker_buy_volume` | OFI, VPIN | `taker_ratio * volume` 替代 | 2.2.1 |
| `taker_ratio` | OFI fallback | volume-only 估計 | 2.2.1 |
| `trades` | Large Trade Ratio | skip + WARNING | 2.2.1 |
| `quote_volume` | Amihud, Large Trade | `close * volume` 替代 | 2.2.1 |

### Optional 套件降級（§10.4）

| 套件 | 影響 | 降級行為 | 對應 Task |
|------|------|---------|----------|
| `numba` | ApEn/SampEn | fallback 純 numpy（10x slower） | 2.2.2 |
| `statsmodels` | ADF / FracDiff | 自動 disabled + WARNING | 2.3.1 |

---

## 快取策略（SPEC §11 對應）

### Layer 1 特徵快取（§11.1）

新引擎輸出隨 Layer 1 其他特徵一起由 `FeatureStorage` 快取至 HDF5。快取 key 基於 `config_hash`。

### Fractional Differencing d* 快取（§11.2）

- **格式**：JSON — `data_cache/features/{symbol}_{timeframe}_d_star_cache.json`
- **內容**：`Dict[feature_name, float]`
- **失效條件**：
  1. 特徵數據長度變更 > 20%
  2. Config 中 `adf_threshold` 或 `precision` 變更
  3. `force_regenerate=True`
- **對應 Task**：2.3.1

### ADF 結果快取（§11.3）

- **格式**：`Dict[feature_name, bool]`（True = 定態）
- **對應 Task**：2.3.1

---

## Logging 規範（SPEC §12 對應）

### 引擎層級（§12.1）

| 事件 | Level | 範例 |
|------|-------|------|
| 引擎啟動 | INFO | `"MicrostructureEngine: computing 7 indicators for 300 bars"` |
| 引擎完成 | INFO | `"MicrostructureEngine: 25 features computed in 0.3s"` |
| 個別指標失敗 | WARNING | `"VPIN computation failed: missing taker_buy_volume"` |
| 引擎完全失敗 | ERROR | `"EntropyEngine failed: {exc}"` (with `exc_info=True`) |
| Optional 套件缺失 | WARNING | `"Numba not available, using pure numpy fallback"` |

### 前處理層級（§12.2）

| 事件 | Level | 範例 |
|------|-------|------|
| Layer 6.5 啟動 | INFO | `"Preprocessing: 6 transforms on 1500 features"` |
| 個別 transform 完成 | INFO | `"Winsorization: clipped 23 values in 15 columns"` |
| d* 快取命中 | DEBUG | `"FracDiff d* cache hit for 1200/1500 features"` |
| ADF/FracDiff 跳過 | DEBUG | `"Skipping 800 already-stationary features"` |
| transform 失敗 | WARNING | `"Gaussian normalize failed for column X: all NaN"` |

### 禁止事項（§12.3）

- ❌ 不在 hot loop 內做逐行 log
- ❌ 不 log 原始數據值
- ❌ 不使用 `print()` — 統一使用 `momentum.core.logging.get_logger()`

---

## 下游影響分析（SPEC §9 對應）

### 新增 Layer 1 特徵的下游傳播（§9.1）

| 下游 Layer | 影響 | 膨脹倍率 | 控制方式 |
|-----------|------|---------|---------|
| Layer 2 (Derived) | `ms_*/ent_*/tr_*` 進入算子 | ~4-8x | `operators.apply_to` 限制 |
| Layer 3 (Rolling Agg) | 做 slope/std/mean 等聚合 | ~10x | `rolling_aggregation.apply_to` 限制 |
| Layer 4 (Lag) | lag 展開 | ~3-5x | `lag_features.apply_to` 限制 |
| Layer 5 (Cross-Sectional) | 不受影響 | 1x | — |
| Layer 6 (Meta) | 不直接使用新特徵 | 1x | — |
| Layer 6.5 (Preprocessing) | rank/zscore/差分 | ~2-3x | `preprocessing.apply_to` |

### 特徵數量膨脹估計（§9.2）

- **極端情境**（所有 downstream 開啟，apply_to='all'）：~6,000+ 特徵
- **建議配置**（使用 `apply_to` 限制）：膨脹約 200-500 特徵
- **記憶體影響**：可忽略（66 features × 300 bars × 4 bytes = ~79 KB）

---

## 風險對照表（SPEC §14 延伸）

| 風險 | 說明 | 緩解措施 | 對應 Task |
|------|------|---------|----------|
| Entropy 計算緩慢 | ApEn/SampEn O(N²) | Numba JIT 必須啟用 | 2.2.2 |
| FracDiff d* 搜尋慢 | 首次需多次 ADF 檢定 | 快取 d* + `cache_d_star: true` | 2.3.1 |
| 特徵膨脹 | Layer 2-4 對新特徵做全量展開 | `apply_to` 限制 + `preview_feature_count` 預警 | 2.1.3, 2.4.1 |
| statsmodels 缺失 | ADF/FracDiff 無法運作 | 條件 import + WARNING + 自動 disabled | 2.3.1 |
| Numba 缺失 | ApEn/SampEn 慢 10x | 條件 import + WARNING + fallback 純 numpy | 2.2.2 |
| 舊版 YAML 不含新 section | 相容性風險 | Pydantic 預設值 + `extra=allow` 確保缺欄位時使用預設並保持可載入 | 2.4.1 |
| VPIN 近似品質 | 時間 bar 非 volume bar | 使用 BVC 分類（業界標準近似） | 2.2.1 |

---

## 相依套件（SPEC §8.3）

| 套件 | 用途 | 必要性 | 條件 import 策略 |
|------|------|--------|-----------------|
| `numpy` / `pandas` | 全部向量化計算 | 必要（已安裝） | 直接 import |
| `scipy` | `erfinv`（Gaussian）、`norm.cdf`（VPIN BVC） | 必要（已安裝） | 直接 import |
| `statsmodels` | `adfuller`（ADF / FracDiff §6.3/§6.6） | 選用 | `try: import ... except ImportError: HAS_STATSMODELS = False` |
| `numba` | ApEn/SampEn JIT 加速（§4.2/§4.3） | 選用 | `try: import ... except ImportError: HAS_NUMBA = False` |

---

## 檔案結構彙整（SPEC §8）

### 新增檔案（8 個）

```
momentum/FeatureEngineering/
├── atomic/
│   ├── microstructure_indicators.py    ← SPEC §3
│   ├── entropy_indicators.py           ← SPEC §4
│   └── tail_risk_indicators.py         ← SPEC §5
├── preprocessing/
│   ├── __init__.py
│   └── feature_preprocessor.py         ← SPEC §6
tests/momentum/
├── test_microstructure_indicators.py
├── test_entropy_indicators.py
├── test_tail_risk_indicators.py
└── test_feature_preprocessor.py
```

### 修改檔案（4 個）

```
momentum/FeatureEngineering/
├── feature_factory.py                  ← Layer 1 新增 3 engine + Layer 6.5
├── feature_config.py                   ← 新增 10+ Pydantic Models
├── config_manager.py                   ← preview_feature_count 擴展
├── atomic/__init__.py                  ← 新增 3 engine 匯出
config/
└── scan_config.yaml                    ← 新增 microstructure, entropy, tail_risk, preprocessing
```

### 新增目錄（1 個）

```
momentum/FeatureEngineering/preprocessing/
```

### 新增測試檔案（2 個額外）

```
tests/momentum/
├── test_feature_factory_optimization_e2e.py
└── test_feature_factory_optimization_perf.py
```

### 統計

| 類別 | 檔案數 |
|------|--------|
| 新增核心模組 | 5 (3 engines + 1 preprocessor + 1 __init__) |
| 新增測試 | 6 |
| 新增目錄 | 1 |
| 修改檔案 | 5 |
| **合計** | **17 (11 新增 + 5 修改 + 1 目錄)** |

---

## MCP Tool Interface 預留（SPEC §16 — 不在本期實作範圍）

> **狀態**：規格已定（SPEC §16），不在本 PLAN 實作範圍。
> 為 V2.0 Chat / V3.0 Agent 預留。

預留 Tool 定義參見 SPEC §16.1。設計約束：
- Tool 不直接呼叫 Engine，透過 `api/services/` 的 Service 層
- Service 使用 `create_feature_factory()` 建構 FeatureFactory
- 符合 Rule 3

---

## 業界覆蓋率對標（SPEC §15.5）

| 面向 | 指標 | V0.1 覆蓋 | 本 PLAN 新增 | 業界覆蓋率 |
|------|------|----------|-------------|-----------|
| 微觀結構 | Amihud, Kyle's Lambda, Roll's, CS, OFI, LTR | ✅ | VPIN | ~90% |
| 資訊理論 | Shannon, ApEn, SampEn, Hurst, Fractal Dim | ✅ | Permutation Entropy | ~90% |
| 尾部風險 | CVaR, RV Decomposition, UDVR, GPR, JB | ✅ | Rolling Max Drawdown | ~90% |
| 前處理 | Rank, Gaussian, ADF, Z-Score, Winsorization | ✅ | Fractional Differencing | ~95% |

---

## 預估時程（SPEC §2 對應）

| Phase | 任務 | 預估天數 |
|-------|------|---------|
| 2.1 | Config & Pydantic 擴展 | 1 天 |
| 2.2 | Layer 1 × 3 引擎 | 6-9 天 |
| 2.3 | Layer 6.5 前處理 | 3-4 天 |
| 2.4 | Pipeline 整合 | 1 天 |
| 2.5 | 測試與驗收 | 2 天 |
| **合計** | | **~13-17 天** |

---

---

# Part 3：前端 UI 整合、多格式匯出與特徵數據瀏覽器

> **版本**: V5  
> **建立日期**: 2026-02-17  
> **基底**: Feature_Factory_優化PLAN.md Part 2（Frozen）+ Feature Generation Factory.md V2.2 + Feature_Factory_優化SPEC.md V1.1  
> **依據**: PRODUCT_VISION.md ADR-002（AI 可讀檔案格式）、業界特徵工程可視化實務（WorldQuant / Two Sigma / Kaggle / QuantConnect）  
> **目的**: 補足 V1.0→V1.1 三個產品級缺口：(1) 新功能前端可及性 (2) 多格式匯出 (3) 特徵數據瀏覽器  
> **範圍**: 前端 UI + 後端 API + 匯出格式定義；不修改 Pipeline 核心引擎  
> **狀態**: 🔒 V5 Frozen — 自審 4 輪通過（V1 初版→V2 自審→V3 二審→V4 三審精修→V5 驗證收斂修補）  
> Changelog: V4 → V5：補齊 Part 3 各 Task 驗證檢查點的失敗/邊界 PASS 條件，並明確 `max_rows=0` 與參數錯誤路徑的可測判準。  
> **Changelog**:  
>   - V1: 初版生成（3 Phase × 16 Task）  
>   - V2: 自審修訂 — 補齊邊界條件、修正 API streaming、新增 Dashboard 互動連動、補 a11y/響應式/效能預算  
>   - V3: 二審收斂 — 修正 Markdown 前端渲染安全、補 Token 預算計算、分頁 API 規格、Dashboard 空狀態處理、E2E 測試覆蓋
>   - V4: 三審精修 — 補 featureFactoryStore explorer state 擴展規格、useFeatureFactory hook 擴展規格、lib/types.ts 新增 interface 清單、Cross-Tab 互動機制（FeatureTable↔Distribution/Correlation 連動）、Quality Score 計算公式、npm 依賴清單（@tanstack/react-virtual）
>   - V5: 驗證收斂修補 — 補齊各 Task `### 驗證檢查點` 的失敗/邊界 PASS 條件，保持原責任範圍不擴張

---

## Part 3 架構原則

> 繼承 Part 2 全部解耦規則（Rule 1-7），額外新增前端相關約束。

### 前端架構約束

| 約束 | 說明 |
|------|------|
| **F1** | 新元件位於 `frontend/src/components/feature-factory/` 下，不建新頂層目錄 |
| **F2** | 狀態管理使用既有 `featureFactoryStore.ts` 擴展，不建新 Store |
| **F3** | API 呼叫統一透過 `useFeatureFactory` hook 擴展 |
| **F4** | 所有新 UI 元件必須支援 Empty State / Loading State / Error State |
| **F5** | 圖表匯出統一支援 PNG（html2canvas）+ CSV（前端生成） |
| **F6** | 響應式設計：≥1440px 雙欄、≥768px 單欄堆疊、<768px 壓縮 |
| **F7** | 效能預算：首次渲染 < 200ms（不含 API fetch）、10,000 行×100 欄虛擬捲動 60fps |

### 後端約束

| 約束 | 說明 |
|------|------|
| **B1** | 新 API 端點位於既有 `api/routes/feature_factory.py`，不建新 Router |
| **B2** | 大量 CSV 串流使用 `StreamingResponse`，避免一次性載入整個 DataFrame 到記憶體 |
| **B3** | JSON/Markdown 匯出在 `api/services/` 層實作，不在 Route 層組裝 |
| **B4** | 分頁 API 使用 cursor-based 分頁（offset + limit），非頁碼式 |

---

## Phase 3.1：前端新功能開關 UI — 分級引擎控制面板

### 業界難易度分級定義

根據量化金融業界使用實務（Two Sigma / AQR / WorldQuant 公開研究、Kaggle 量化競賽標準配置），將所有特徵引擎分為三個等級：

| 等級 | 名稱 | 色標 | 定義 | 適用對象 |
|------|------|------|------|---------|
| **L1** | 🟢 基礎必用 | `emerald` | 業界公認標配，幾乎所有量化策略都會使用 | 所有使用者 |
| **L2** | 🟡 中階進階 | `amber` | 需要一定量化背景理解，進階策略研究常用 | 有量化基礎的研究者 |
| **L3** | 🔴 高階專業 | `rose` | 學術前沿/高頻領域，需深厚數理背景 | 專業量化研究員 |

### 引擎分級對照表（完整）

#### Layer 1 原子指標引擎

| 引擎 | 等級 | 理由 | 預設 | 來源文件 |
|------|------|------|------|---------|
| **Trend** (趨勢) | L1 🟢 | EMA/SMA/MACD 是最基本的技術分析指標 | `enabled: true` | Feature Generation Factory.md §3.1 |
| **Momentum** (動量) | L1 🟢 | RSI/Stochastic/ROC 是動量策略的核心 | `enabled: true` | Feature Generation Factory.md §3.1 |
| **Volatility** (波動) | L1 🟢 | ATR/BB/歷史波動率是風險管理基本功 | `enabled: true` | Feature Generation Factory.md §3.1 |
| **Volume** (量能) | L1 🟢 | OBV/VWAP/量價分析是市場微結構基礎 | `enabled: true` | Feature Generation Factory.md §3.1 |
| **Statistics** (統計) | L2 🟡 | Skewness/Kurtosis 需統計學知識 | `enabled: false` | Feature Generation Factory.md §3.1 |
| **Cycle** (週期) | L2 🟡 | Hilbert Transform/Fourier 需信號處理背景 | `enabled: false` | Feature Generation Factory.md §3.1 |
| **Pattern** (型態) | L2 🟡 | K 線型態識別，需要 K 線分析經驗 | `enabled: false` | Feature Generation Factory.md §3.1 |
| **Tail Risk** (尾部風險) | L2 🟡 | CVaR/RV 分解需風險管理知識 | `enabled: false` | 優化 SPEC §5 |
| **Microstructure** (微觀結構) | L3 🔴 | Amihud/Kyle's Lambda/VPIN 需市場微結構理論 | `enabled: false` | 優化 SPEC §3 |
| **Entropy** (資訊理論) | L3 🔴 | ApEn/SampEn/Hurst 需資訊理論/非線性動力學背景 | `enabled: false` | 優化 SPEC §4 |

#### Layer 2-6 算子與前處理

| 功能 | 等級 | 理由 | 預設 | 來源文件 |
|------|------|------|------|---------|
| **Derived Features** (衍生特徵 Layer 2) | L1 🟢 | Distance/Cross/Ratio 是因子工程標準操作 | `enabled: true` | Feature Generation Factory.md §3.2 |
| **Rolling Aggregation** (滑動聚合 Layer 3) | L1 🟢 | Slope/Std/ZScore 是時間序列分析基礎 | `enabled: true` | Feature Generation Factory.md §3.3 |
| **Lag Features** (滯後展開 Layer 4) | L1 🟢 | T-1~T-N 歷史快照是 ML 預測必備 | `enabled: true` | Feature Generation Factory.md §3.4 |
| **Cross-Sectional** (橫截面 Layer 5) | L2 🟡 | Rank/Demean 需多資產概念 | `enabled: false` | Feature Generation Factory.md §3.5 |
| **Meta-Feature** (元特徵 Layer 6) | L2 🟡 | 交互特徵需特徵工程經驗 | `enabled: false` | Feature Generation Factory.md §3.6 |
| **Winsorization** (極端值裁剪) | L1 🟢 | 資料清洗基本步驟 | `enabled: true` | 優化 SPEC §6.5 |
| **Rank Transform** (排名轉換) | L1 🟢 | 消除量綱，ML 友善 | `enabled: true` | 優化 SPEC §6.1 |
| **Adaptive Z-Score** (自適應標準化) | L2 🟡 | 需理解滾動統計 | `enabled: true` | 優化 SPEC §6.4 |
| **Gaussian Normalize** (高斯正規化) | L2 🟡 | 需理解分位數轉換 | `enabled: false` | 優化 SPEC §6.2 |
| **ADF Differencing** (整數差分) | L3 🔴 | 需理解定態性/單位根檢定 | `enabled: false` | 優化 SPEC §6.3 |
| **Fractional Differencing** (分數差分) | L3 🔴 | López de Prado 高階技巧 | `enabled: false` | 優化 SPEC §6.6 |

### Task 3.1.1：IndicatorSelector 擴展 — 分級引擎開關

**檔案**：
- `frontend/src/components/feature-factory/IndicatorSelector.tsx` (修改)

**修改重點**：

1. **擴展 `CATEGORY_LABELS`**：新增 `microstructure`、`entropy`、`tail_risk` 三個分類
2. **新增分級系統**：每個引擎附加 `level` / `color` / `tooltip` 屬性
3. **分級篩選 UI**：頂部 Tab 切換「全部 / 🟢 基礎 / 🟡 中階 / 🔴 高階」
4. **一鍵啟用/停用分級**：「啟用所有基礎」「啟用所有中階+」按鈕

```typescript
// 新增引擎分級定義
interface EngineDefinition {
  key: string;
  label: string;
  description: string;
  level: 'L1' | 'L2' | 'L3';
  levelLabel: string;
  color: string;        // Tailwind color variant
  featureCount: number;  // 從 preview breakdown 動態取得
  source: string;        // 來源文件參考
}

const ENGINE_DEFINITIONS: EngineDefinition[] = [
  // L1 基礎必用
  { key: 'trend', label: '趨勢', description: 'EMA, SMA, MACD, ADX, Parabolic SAR', level: 'L1', levelLabel: '基礎必用', color: 'emerald', featureCount: 0, source: 'Factory §3.1' },
  { key: 'momentum', label: '動量', description: 'RSI, Stochastic, ROC, Williams %R, CCI', level: 'L1', levelLabel: '基礎必用', color: 'emerald', featureCount: 0, source: 'Factory §3.1' },
  { key: 'volatility', label: '波動', description: 'ATR, Bollinger Bands, Keltner Channel', level: 'L1', levelLabel: '基礎必用', color: 'emerald', featureCount: 0, source: 'Factory §3.1' },
  { key: 'volume', label: '量能', description: 'OBV, VWAP, MFI, AD Line', level: 'L1', levelLabel: '基礎必用', color: 'emerald', featureCount: 0, source: 'Factory §3.1' },
  // L2 中階進階
  { key: 'statistics', label: '統計', description: 'Skewness, Kurtosis, Linear Regression', level: 'L2', levelLabel: '中階進階', color: 'amber', featureCount: 0, source: 'Factory §3.1' },
  { key: 'cycle', label: '週期', description: 'Hilbert Transform, Sine Wave, Dominant Period', level: 'L2', levelLabel: '中階進階', color: 'amber', featureCount: 0, source: 'Factory §3.1' },
  { key: 'pattern', label: '型態', description: 'Doji, Hammer, Engulfing 等 K 線型態', level: 'L2', levelLabel: '中階進階', color: 'amber', featureCount: 0, source: 'Factory §3.1' },
  { key: 'tail_risk', label: '尾部風險', description: 'CVaR, RV 分解, GPR, Jarque-Bera, MDD', level: 'L2', levelLabel: '中階進階', color: 'amber', featureCount: 0, source: '優化 SPEC §5' },
  // L3 高階專業
  { key: 'microstructure', label: '微觀結構', description: 'Amihud, Kyle\'s Lambda, VPIN, OFI', level: 'L3', levelLabel: '高階專業', color: 'rose', featureCount: 0, source: '優化 SPEC §3' },
  { key: 'entropy', label: '資訊理論', description: 'Shannon, ApEn, SampEn, Hurst, Permutation', level: 'L3', levelLabel: '高階專業', color: 'rose', featureCount: 0, source: '優化 SPEC §4' },
];
```

**UI 結構**：

```
┌─────────────────────────────────────────────────┐
│ 指標引擎                                         │
│ [全部] [🟢 基礎必用(4)] [🟡 中階(4)] [🔴 高階(2)]│
│                                                   │
│ ┌──────────────┐ ┌──────────────┐                │
│ │ 🟢 趨勢      │ │ 🟢 動量      │                │
│ │ EMA,SMA,MACD │ │ RSI,Stoch... │                │
│ │ ~120 features│ │ ~90 features │                │
│ │ [✓ 已啟用]   │ │ [✓ 已啟用]   │                │
│ └──────────────┘ └──────────────┘                │
│ ...                                               │
│ ┌──────────────┐ ┌──────────────┐                │
│ │ 🔴 微觀結構  │ │ 🔴 資訊理論  │                │
│ │ Amihud,VPIN  │ │ Hurst,ApEn   │                │
│ │ 25 features  │ │ 15 features  │                │
│ │ [○ 未啟用]   │ │ [○ 未啟用]   │                │
│ └──────────────┘ └──────────────┘                │
│                                                   │
│ [一鍵啟用所有基礎] [啟用基礎+中階] [全部啟用]     │
└─────────────────────────────────────────────────┘
```

**驗收條件**：
- [x] 10 個引擎類別全部顯示（原 7 + 新增 microstructure/entropy/tail_risk）
- [x] 分級 Tab 篩選正確：L1=4、L2=4、L3=2
- [x] 點擊引擎卡片正確切換 `config.atomic_indicators.{key}.enabled`
- [x] 一鍵啟用按鈕批次修改 config
- [x] 每個卡片顯示 `featureCount`（從 preview.breakdown 映射）
- [x] 響應式：≥1440px 4 欄、≥768px 2 欄、<768px 1 欄

### 驗證檢查點
- PASS: 切換 Tab 後卡片數正確篩選
- PASS: 點擊 microstructure 卡片後 `config.atomic_indicators.microstructure.enabled` 變為 true，preview 即時更新 feature count
- PASS: 失敗/邊界路徑 — `preview.breakdown` 缺少新引擎 key 時，卡片 `featureCount` 顯示 `—` 且不拋例外

**Checklist**：
- [x] ENGINE_DEFINITIONS 常量定義（10 個引擎）
- [x] 分級 Tab UI
- [x] 引擎卡片元件（含 level badge / description / feature count）
- [x] 一鍵批次啟用按鈕
- [x] preview.breakdown 映射 featureCount
- [x] TypeScript 型別安全（extends FeatureFactoryConfig['atomic_indicators']）
- [x] 響應式 grid

---

### Task 3.1.2：PreprocessingPanel — 前處理層控制面板（新建）

**檔案**：
- `frontend/src/components/feature-factory/PreprocessingPanel.tsx` (新建)

**功能**：讓使用者控制 Layer 6.5 的 6 種前處理轉換，每種可獨立啟用/停用並調整參數。

**分級**：

| 轉換 | 等級 | 預設 |
|------|------|------|
| Winsorization | L1 🟢 | `enabled: true` |
| Rank Transform | L1 🟢 | `enabled: true` |
| Adaptive Z-Score | L2 🟡 | `enabled: true` |
| Gaussian Normalize | L2 🟡 | `enabled: false` |
| ADF Differencing | L3 🔴 | `enabled: false` |
| Fractional Differencing | L3 🔴 | `enabled: false` |

**UI 結構**：

```
┌───────────────────────────────────────────────┐
│ 前處理層 (Layer 6.5)          [主開關 ○ / ●]  │
│ 模式：[➤ Append] [Replace]                    │
│                                                │
│ 執行順序（固定）：                              │
│ ① Winsorization 🟢 [✓] ──→ ② FracDiff 🔴 [○]│
│ ──→ ③ Rank 🟢 [✓] ──→ ④ Gaussian 🟡 [○]     │
│ ──→ ⑤ Z-Score 🟡 [✓]                          │
│                                                │
│ ┌─ Winsorization ──────────── 🟢 基礎 ──┐     │
│ │ 方法: [sigma ▾]   sigma_k: [3.0 ━━●━] │     │
│ └────────────────────────────────────────┘     │
│ ┌─ Fractional Differencing ── 🔴 高階 ──┐     │
│ │ ADF threshold: [0.05]                   │     │
│ │ Precision: [0.01]  Cache d*: [✓]       │     │
│ │ ⚠️ 較慢，建議小數據集先試驗              │     │
│ └─────────────────────────────────────────┘    │
└───────────────────────────────────────────────┘
```

**驗收條件**：
- [x] 6 種轉換全部可獨立開關，參數可調
- [x] 主開關控制 `config.preprocessing.enabled`
- [x] mode 切換 `append` / `replace`
- [x] 執行順序視覺化（固定順序，不可拖曳排序）
- [x] L3 高階轉換顯示效能警告 tooltip
- [x] 參數修改即時觸發 preview 更新

### 驗證檢查點
- PASS: 主開關切換 → preprocessing.enabled 正確
- PASS: 開啟 fractional_differencing → preview.breakdown.preprocessing_added > 0
- PASS: 失敗/邊界路徑 — `preprocessing.enabled=false` 且子項目 `enabled=true` 時，preview 不計入 preprocessing 膨脹

**Checklist**：
- [x] 主開關 + mode 選擇
- [x] 6 個轉換卡片（各含 enabled toggle + 參數 slider/input）
- [x] 執行順序流程圖（純視覺，不可排序）
- [x] 效能警告（L3 items）
- [x] config.preprocessing deep merge
- [x] TypeScript 型別對齊 PreprocessingConfig

---

### Task 3.1.3：page.tsx 整合 — 新增 PreprocessingPanel 到頁面

**檔案**：
- `frontend/src/app/feature-factory/page.tsx` (修改)

**修改重點**：

在 `ConfigPanel` 和 `PreviewPanel` 區塊之間（或 ConfigPanel 下方），新增 `PreprocessingPanel`：

```tsx
import PreprocessingPanel from '@/components/feature-factory/PreprocessingPanel';

// 在 grid 布局中新增：
<div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-6">
  <div className="space-y-6">
    <ConfigPanel ... />
    <PreprocessingPanel
      config={config?.preprocessing}
      onChange={(next) => updateConfigPartial({ preprocessing: next })}
    />
  </div>
  <div className="space-y-6">
    <PreviewPanel preview={preview} />
    ...
  </div>
</div>
```

**驗收條件**：
- [x] PreprocessingPanel 正確顯示在 ConfigPanel 下方
- [x] 所有交互正常：開關、參數調整、preview 即時更新
- [x] 不影響既有元件功能

### 驗證檢查點
- PASS: 頁面載入無 console error
- PASS: 啟用 preprocessing → 點擊生成 → 任務完成後 feature_count 包含 preprocessing 膨脹
- PASS: 失敗/邊界路徑 — 舊版 config 無 `preprocessing` 欄位時頁面仍可渲染，Panel 以預設值顯示且不拋例外

**Checklist**：
- [x] import PreprocessingPanel
- [x] 佈局整合
- [x] props 接線（config.preprocessing → onChange → updateConfigPartial）

---

### Task 3.1.4：Preset 擴展 — 新增分級 Preset 模板

**檔案**：
- `api/services/feature_factory_service.py` (修改 get_presets 方法)
- 或 `config/` 新增 preset YAML

**新增 Preset**：

| Preset 名稱 | 描述 | 啟用範圍 | 預估特徵數 |
|-------------|------|---------|-----------|
| `basic_essential` | 🟢 基礎必用 — 業界標配 | L1 全部引擎 + Winsor + Rank | ~3,000-5,000 |
| `intermediate_research` | 🟡 中階研究 — 進階策略開發 | L1+L2 全部引擎 + 全部 L1/L2 前處理 | ~10,000-15,000 |
| `professional_full` | 🔴 專業全量 — 量化研究全配 | 全部引擎 + 全部前處理 | ~25,000-35,000 |
| `ml_optimized` | 🤖 ML 友善 — 去冗餘、已正規化 | L1+L2 引擎 + 全部前處理 + replace mode | ~8,000-12,000 |

**驗收條件**：
- [x] 4 個新 Preset 可正確載入
- [x] 選擇 Preset 後 IndicatorSelector + PreprocessingPanel 正確反映開關狀態
- [x] 既有 Preset 不受影響

### 驗證檢查點
- PASS: 選擇 `professional_full` → preview.total_features > 25000
- PASS: 選擇 `basic_essential` → microstructure/entropy disabled
- PASS: 失敗/邊界路徑 — 載入 Preset 若缺少 Part 3 新欄位時，使用預設值補齊且既有 Preset 行為不變

**Checklist**：
- [x] 4 個 Preset config 定義
- [x] Preset 選擇與 Config 聯動
- [x] PresetSelector 顯示等級 badge

---

## Phase 3.2：多格式匯出系統

### 匯出格式規格

根據 PRODUCT_VISION.md ADR-002 和 V2.0/V3.0 演進需求，定義 4 種匯出格式：

| 格式 | 用途 | 受眾 | 大小限制 |
|------|------|------|---------|
| **HDF5** | 高效能二進位儲存、Pipeline 內部使用 | 系統內部 | 無限制 |
| **CSV** | Excel/Pandas 分析、外部工具匯入 | 人類分析師 | 單檔 < 500MB（串流式） |
| **JSON** | AI Agent / LLM 消費、V2.0 Chat 準備 | AI Agent | 含 Metadata + 統計摘要 + 樣本數據 |
| **Markdown** | LLM context window 友善、人類可讀報告 | AI + 人類 | Token 預算限制（可配置） |

### Task 3.2.1：後端 CSV 串流匯出 API

**檔案**：
- `api/routes/feature_factory.py` (修改 — 新增端點)
- `api/services/feature_factory_service.py` (修改 — 新增匯出邏輯)

**新增端點**：

```python
from fastapi.responses import StreamingResponse

@router.get("/export/{task_id}/csv")
async def export_features_csv(
    task_id: str,
    columns: Optional[str] = Query(None, description="逗號分隔的欄位名，空=全部"),
    max_rows: Optional[int] = Query(None, description="最大行數，空=全部"),
    include_metadata_header: bool = Query(True, description="CSV 前方加入 #metadata 註解行"),
):
    """串流匯出特徵數據為 CSV。
    
    使用 StreamingResponse 逐 chunk 寫出，避免大 DataFrame 一次性載入。
    Chunk size: 10,000 行 / chunk。
    """
```

**實作策略**：

```python
# api/services/feature_factory_service.py

import io
import csv

def export_csv_stream(self, task_id: str, columns: Optional[List[str]], 
                       max_rows: Optional[int], include_metadata: bool):
    """Generator：逐 chunk 串流 CSV。"""
    result = self._load_hdf5_result(task_id)
    df = result.features_df
    
    if columns:
        df = df[columns]
    if max_rows is not None:
        df = df.head(max_rows)
    
    # Metadata header（可選）
    if include_metadata:
        yield f"# task_id: {task_id}\n"
        yield f"# symbol: {result.symbol}\n"
        yield f"# timeframe: {result.timeframe}\n"
        yield f"# feature_count: {len(df.columns)}\n"
        yield f"# row_count: {len(df)}\n"
        yield f"# generated_at: {result.generated_at}\n"
    
    # Header
    yield ','.join(df.columns) + '\n'
    
    # Data chunks
    chunk_size = 10_000
    for start in range(0, len(df), chunk_size):
        chunk = df.iloc[start:start + chunk_size]
        buffer = io.StringIO()
        chunk.to_csv(buffer, header=False, index=True)
        yield buffer.getvalue()
```

**邊界條件**：

| # | 條件 | 預期行為 |
|---|------|---------|
| 1 | task_id 不存在 | 404 Not Found |
| 2 | HDF5 檔案已刪除 | 404 + 錯誤訊息 |
| 3 | columns 含不存在的欄位名 | 400 + 列出有效欄位 |
| 4 | max_rows = 0 | 只回傳 header（無資料行） |
| 5 | 30,000+ 欄位 × 1,000 行 | 串流正常、記憶體 < 200MB |

**驗收條件**：
- [x] `GET /api/v1/features/export/{task_id}/csv` 正確串流回傳
- [x] Content-Disposition header 含檔名
- [x] Metadata header 正確（含 task_id, symbol, timeframe, feature_count）
- [x] 5 項邊界條件全部通過

### 驗證檢查點
- PASS: `curl -o output.csv http://localhost:8000/api/v1/features/export/{task_id}/csv` 產生合法 CSV
- PASS: 30,000 欄 × 600 行串流匯出記憶體峰值 < 200MB
- PASS: 失敗/邊界路徑 — `columns` 含不存在欄位或 `task_id` 不存在時分別回傳 400/404，且錯誤訊息可定位問題

**Checklist**：
- [x] StreamingResponse 設定（media_type, headers）
- [x] chunk generator
- [x] metadata header
- [x] columns 篩選 + 驗證
- [x] max_rows 限制
- [x] 5 項邊界條件測試

---

### Task 3.2.2：後端 JSON 結構化匯出 API

**檔案**：
- `api/routes/feature_factory.py` (修改 — 新增端點)
- `api/services/feature_export_service.py` (新建)

**新增端點**：

```python
@router.get("/export/{task_id}/json")
async def export_features_json(
    task_id: str,
    include_sample_data: bool = Query(True, description="包含前 N 行樣本數據"),
    sample_rows: int = Query(5, ge=1, le=100, description="樣本行數"),
    include_statistics: bool = Query(True, description="包含每欄統計摘要"),
    include_correlation_top_k: int = Query(10, ge=0, le=50, description="Top-K 高相關特徵對"),
):
    """匯出 AI Agent / LLM 可消費的結構化 JSON。"""
```

**JSON Schema 定義**（ADR-002 對齊）：

```json
{
  "version": "1.0",
  "type": "feature_factory_report",
  "metadata": {
    "task_id": "uuid",
    "symbol": "BTCUSDT",
    "timeframe": "12h",
    "generated_at": "2026-02-17T12:00:00Z",
    "total_features": 25000,
    "total_rows": 657,
    "generation_time_seconds": 45.2,
    "config_hash": "abc123",
    "engines_enabled": ["trend", "momentum", "volatility", "volume", "tail_risk"],
    "preprocessing_enabled": true,
    "preprocessing_mode": "append"
  },
  "feature_catalog": {
    "by_category": {
      "trend": { "count": 120, "features": ["close_trend_EMA_W5", "..."] },
      "microstructure": { "count": 25, "features": ["ms_amihud_illiq_5", "..."] }
    },
    "by_level": {
      "L1_basic": { "count": 3000, "categories": ["trend","momentum","volatility","volume"] },
      "L2_intermediate": { "count": 5000, "categories": ["statistics","cycle","pattern","tail_risk"] },
      "L3_advanced": { "count": 2000, "categories": ["microstructure","entropy"] }
    },
    "by_layer": {
      "layer1_atomic": 500,
      "layer2_derived": 2000,
      "layer3_rolling": 8000,
      "layer4_lag": 10000,
      "layer5_cross_sectional": 1000,
      "layer6_meta": 500,
      "layer6_5_preprocessing": 3000
    }
  },
  "statistics": {
    "summary": {
      "nan_ratio_mean": 0.02,
      "nan_ratio_max": 0.15,
      "inf_count": 0,
      "constant_features": 3,
      "high_correlation_pairs": 42
    },
    "per_feature": [
      {
        "name": "ms_amihud_illiq_21",
        "category": "microstructure",
        "level": "L3",
        "layer": "layer1",
        "dtype": "float64",
        "nan_ratio": 0.03,
        "mean": 0.00045,
        "std": 0.00012,
        "min": 0.00001,
        "max": 0.0032,
        "skewness": 2.1,
        "kurtosis": 8.5,
        "description": "Amihud Illiquidity Ratio (21-day window)"
      }
    ]
  },
  "sample_data": {
    "columns": ["open_time", "ms_amihud_illiq_21", "ent_shannon_close_return_21", "..."],
    "rows": [
      ["2025-01-01T00:00:00Z", 0.00045, 2.31, "..."],
      ["2025-01-01T12:00:00Z", 0.00048, 2.28, "..."]
    ]
  },
  "quality_alerts": [
    { "severity": "warning", "feature": "ms_vpin_30", "message": "NaN ratio 12% exceeds 10% threshold" },
    { "severity": "info", "feature": "ent_hurst_200", "message": "Requires 200-bar warmup, first 200 rows are NaN" }
  ],
  "correlation_hotspots": [
    { "feature_a": "tr_rv_up_13", "feature_b": "tr_rv_down_13", "correlation": 0.95 }
  ]
}
```

**驗收條件**：
- [x] JSON 輸出符合上述 Schema
- [x] `feature_catalog.by_level` 正確分級
- [x] `statistics.per_feature` 包含所有特徵的統計摘要
- [x] `quality_alerts` 自動偵測 NaN 比率高 / 常量特徵 / warmup 警告
- [x] `correlation_hotspots` 回傳 Top-K 高相關對
- [x] sample_data 行數可控（sample_rows 參數）

### 驗證檢查點
- PASS: JSON 輸出可被 `json.loads()` 解析
- PASS: `feature_catalog.by_level.L3_advanced.categories` 包含 `["microstructure", "entropy"]`
- PASS: Token 估算：30,000 特徵的 per_feature statistics JSON < 2MB
- PASS: 失敗/邊界路徑 — `include_correlation_top_k=0` 時 `correlation_hotspots` 為空陣列，Schema 仍完整

**Checklist**：
- [x] `FeatureExportService` 類別定義
- [x] `_build_metadata()` — 基本資訊
- [x] `_build_feature_catalog()` — 分類/分級/分層統計
- [x] `_build_statistics()` — per-feature 統計摘要
- [x] `_build_sample_data()` — 前 N 行取樣
- [x] `_build_quality_alerts()` — 自動品質警告
- [x] `_build_correlation_hotspots()` — Top-K 相關對
- [x] 不 import `momentum.*` 以外的 Engine（透過 Service 層讀取 HDF5 結果）

---

### Task 3.2.3：後端 Markdown 報告匯出 API

**檔案**：
- `api/routes/feature_factory.py` (修改 — 新增端點)
- `api/services/feature_export_service.py` (修改 — 新增方法)

**新增端點**：

```python
@router.get("/export/{task_id}/markdown")
async def export_features_markdown(
    task_id: str,
    max_token_budget: int = Query(4000, ge=500, le=32000, description="Token 預算上限"),
    sections: Optional[str] = Query(None, description="逗號分隔的 section 名，空=全部"),
    language: str = Query("zh-TW", description="報告語言"),
):
    """匯出 LLM context window 友善的 Markdown 報告。
    
    Token 預算策略：
    - metadata + catalog: ~500 tokens（固定）
    - statistics summary: ~300 tokens（固定）
    - per_feature top-K: 依預算動態調整 K
    - quality_alerts: ~200 tokens（固定）
    - sample_data: 依剩餘預算決定行數
    """
```

**Markdown 範本**：

```markdown
# Feature Factory Report: BTCUSDT 12h

> Generated: 2026-02-17T12:00:00Z | Features: 25,000 | Rows: 657

## 📊 Feature Catalog

| Category | Level | Count | % |
|----------|-------|------:|--:|
| Trend | 🟢 L1 | 120 | 4.8% |
| Momentum | 🟢 L1 | 90 | 3.6% |
| Microstructure | 🔴 L3 | 25 | 1.0% |
| Entropy | 🔴 L3 | 15 | 0.6% |
| ... | | | |

## 🔍 Quality Summary

- **NaN 平均比例**: 2.0%
- **常量特徵**: 3 個（建議移除）
- **高相關特徵對**: 42 組（|ρ| > 0.95）

## ⚠️ Quality Alerts

1. `ms_vpin_30` — NaN 比例 12%，超過 10% 門檻
2. `ent_hurst_200` — 需要 200 bars warmup

## 📈 Top Features by Variation

| Feature | Category | Std | Skew | Kurt |
|---------|----------|----:|-----:|-----:|
| tr_cvar_1pct_21 | Tail Risk | 0.023 | -1.8 | 12.3 |
| ms_kyle_lambda_13 | Microstructure | 0.15 | 3.2 | 18.7 |

## 🔗 Correlation Hotspots

| Feature A | Feature B | |ρ| |
|-----------|-----------|----:|
| tr_rv_up_13 | tr_rv_down_13 | 0.95 |
```

**Token 預算控制邏輯**：

```python
def _estimate_tokens(self, text: str) -> int:
    """粗估 token 數：英文 ~4 chars/token、中文 ~2 chars/token。"""
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    non_ascii = len(text) - ascii_chars
    return (ascii_chars // 4) + (non_ascii // 2)

def _build_markdown(self, report_data: dict, max_tokens: int) -> str:
    """根據預算動態裁剪 sections。"""
    sections = []
    remaining = max_tokens
    
    # 固定 sections（~1000 tokens）
    header = self._md_header(report_data)
    sections.append(header)
    remaining -= self._estimate_tokens(header)
    
    catalog = self._md_catalog(report_data)
    sections.append(catalog)
    remaining -= self._estimate_tokens(catalog)
    
    quality = self._md_quality(report_data)
    sections.append(quality)
    remaining -= self._estimate_tokens(quality)
    
    # 動態 sections（依剩餘預算）
    if remaining > 500:
        top_k = min(remaining // 50, len(report_data['statistics']['per_feature']))
        top_features = self._md_top_features(report_data, top_k)
        sections.append(top_features)
        remaining -= self._estimate_tokens(top_features)
    
    if remaining > 300:
        sample_rows = min(remaining // 100, 10)
        sample = self._md_sample(report_data, sample_rows)
        sections.append(sample)
    
    return '\n\n'.join(sections)
```

**安全性**：Markdown 輸出前對所有動態字串做 HTML entity escape（防止前端渲染時的 XSS），特徵名中的 `|` `<` `>` 字元轉義。

**驗收條件**：
- [x] Markdown 輸出為合法 Markdown（可被 markdown parser 解析）
- [x] Token 預算控制：max_token_budget=4000 時輸出 < 4000 tokens
- [x] sections 參數可選擇性包含/排除區段
- [x] 中文/英文雙語支援
- [x] 動態字串 HTML entity escape

### 驗證檢查點
- PASS: `max_token_budget=500` → 只輸出 header + catalog（最精簡）
- PASS: `max_token_budget=32000` → 全部 sections 展開
- PASS: 特徵名含特殊字元時不破壞 Markdown 表格
- PASS: 失敗/邊界路徑 — `sections` 含不存在區段時仍可回傳合法 Markdown，且只包含有效區段

**Checklist**：
- [x] `_build_markdown()` 動態裁剪邏輯
- [x] `_estimate_tokens()` 粗估函式
- [x] `_md_header()` / `_md_catalog()` / `_md_quality()` / `_md_top_features()` / `_md_sample()`
- [x] Token 預算分配策略
- [x] 語言切換（zh-TW / en）
- [x] HTML entity escape
- [x] Content-Type: text/markdown

---

### Task 3.2.4：前端 ExportButtons 擴展

**檔案**：
- `frontend/src/components/feature-factory/ExportButtons.tsx` (修改)

**修改重點**：

在既有 2 個按鈕（匯出 Config / 匯出特徵清單）之後，新增 4 個按鈕：

```
┌─────────────────────────────────────────┐
│ 匯出                                     │
│                                           │
│ 📋 設定                                   │
│ [匯出 Config JSON]  [匯出特徵清單 TXT]   │
│                                           │
│ 📊 數據（需先完成生成）                    │
│ [匯出特徵 CSV ↓]  [匯出 AI JSON ↓]      │
│ [匯出 Markdown 報告 ↓]  [匯出 PNG ↓]    │
│                                           │
│ ⚙️ CSV 選項                               │
│ 欄位：[全部 ▾]  行數：[全部 ▾]            │
│ [✓] 包含 Metadata header                  │
│                                           │
│ 📝 Markdown 選項                           │
│ Token 預算：[4000 ━━●━━━]                  │
│ 語言：[zh-TW ▾]                            │
└─────────────────────────────────────────┘
```

**驗收條件**：
- [x] 4 個新按鈕正確觸發後端 API
- [x] CSV 下載使用 `fetch` + `blob` + `URL.createObjectURL`
- [x] JSON 下載同上
- [x] Markdown 下載同上
- [x] 未完成生成時按鈕 disabled + tooltip 提示
- [x] CSV 選項（columns / max_rows / metadata header）正確傳遞

### 驗證檢查點
- PASS: 點擊 CSV 按鈕 → 瀏覽器下載 .csv 檔案
- PASS: 點擊 JSON 按鈕 → 瀏覽器下載 .json 檔案
- PASS: 點擊 Markdown 按鈕 → 瀏覽器下載 .md 檔案
- PASS: 失敗/邊界路徑 — 任務未完成時匯出按鈕維持 disabled，且不發出 API 請求

**Checklist**：
- [x] 4 個新按鈕 UI
- [x] CSV 選項子面板
- [x] Markdown 選項子面板
- [x] fetch + streaming download
- [x] disabled 狀態管理
- [x] 檔名格式：`{symbol}_{timeframe}_features_{task_id}.{ext}`

---

## Phase 3.3：特徵數據瀏覽器 — 業界級 Feature Explorer

### 業界特徵工程可視化標準

根據業界實務（Two Sigma Alpha Research / WorldQuant WebSim / QuantConnect / Kaggle Feature Competition），量化研究員查看特徵時需要以下分析維度：

| 維度 | 說明 | 業界工具參考 |
|------|------|-------------|
| **Feature Table** | 可排序/篩選的特徵列表，含統計摘要 | Pandas Profiling / Sweetviz |
| **Distribution** | 每個特徵的分佈直方圖 + QQ-Plot | ydata-profiling / Plotly |
| **Time Series** | 特徵值隨時間變化的走勢圖 | TradingView / QuantConnect |
| **Correlation Matrix** | 特徵間相關性熱力圖 | Seaborn / Plotly |
| **NaN Heatmap** | 缺失值分佈模式 | missingno |
| **Feature Importance** | 與 IC / LightGBM 重要性的交叉比對 | SHAP / Feature Importance |
| **Stationarity** | ADF 定態檢定結果 | statsmodels |
| **Category Breakdown** | 按引擎/Layer/等級分類的特徵數量統計 | 自訂 Dashboard |

### Task 3.3.1：後端分頁數據 API

**檔案**：
- `api/routes/feature_factory.py` (修改 — 新增端點)
- `api/services/feature_factory_service.py` (修改)

**新增端點**：

```python
@router.get("/browse/{task_id}/features")
async def browse_features(
    task_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    sort_by: Optional[str] = Query(None, description="排序欄位：nan_ratio, std, skewness, kurtosis, name"),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    category: Optional[str] = Query(None, description="篩選類別"),
    level: Optional[str] = Query(None, regex="^(L1|L2|L3)$"),
    search: Optional[str] = Query(None, description="特徵名模糊搜尋"),
):
    """分頁瀏覽特徵列表 + 統計摘要。"""
```

**回傳 Schema**：

```json
{
  "total": 25000,
  "offset": 0,
  "limit": 50,
  "filters_applied": { "category": "microstructure", "level": "L3" },
  "features": [
    {
      "name": "ms_amihud_illiq_21",
      "category": "microstructure",
      "level": "L3",
      "layer": "layer1",
      "nan_ratio": 0.03,
      "mean": 0.00045,
      "std": 0.00012,
      "min": 0.00001,
      "q25": 0.00030,
      "median": 0.00042,
      "q75": 0.00058,
      "max": 0.0032,
      "skewness": 2.1,
      "kurtosis": 8.5,
      "is_stationary": true,
      "adf_pvalue": 0.001
    }
  ]
}
```

```python
@router.get("/browse/{task_id}/data")
async def browse_feature_data(
    task_id: str,
    features: str = Query(..., description="逗號分隔的特徵名（最多 20）"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """取得指定特徵的原始數據（時間序列）。"""
```

```python
@router.get("/browse/{task_id}/correlation")
async def browse_correlation(
    task_id: str,
    features: str = Query(..., description="逗號分隔的特徵名（最多 50）"),
    method: str = Query("pearson", regex="^(pearson|spearman|kendall)$"),
):
    """取得指定特徵集合的相關矩陣。"""
```

```python
@router.get("/browse/{task_id}/distribution")
async def browse_distribution(
    task_id: str,
    feature: str = Query(..., description="單一特徵名"),
    n_bins: int = Query(50, ge=10, le=200),
):
    """取得單一特徵的分佈直方圖數據。"""
```

```python
@router.get("/browse/{task_id}/nan-pattern")
async def browse_nan_pattern(
    task_id: str,
    sample_features: int = Query(50, ge=10, le=200, description="取樣特徵數"),
):
    """取得 NaN 分佈模式矩陣（missingno 風格）。"""
```

```python
@router.get("/browse/{task_id}/summary")
async def browse_summary(task_id: str):
    """取得整體摘要 Dashboard 數據。"""
```

**回傳 Schema（summary）**：

```json
{
  "total_features": 25000,
  "total_rows": 657,
  "by_category": { "trend": 120, "microstructure": 25, "..." : "..." },
  "by_level": { "L1": 3000, "L2": 5000, "L3": 2000 },
  "by_layer": { "layer1": 500, "layer2": 2000, "..." : "..." },
  "quality": {
    "nan_ratio_mean": 0.02,
    "nan_ratio_max": 0.15,
    "nan_ratio_distribution": [0.0, 0.01, 0.02, 0.05, 0.1, 0.15],
    "constant_features": ["feature_a", "feature_b"],
    "high_corr_pairs_count": 42,
    "stationary_ratio": 0.85
  },
  "generation_info": {
    "task_id": "uuid",
    "symbol": "BTCUSDT",
    "timeframe": "12h",
    "generated_at": "2026-02-17T12:00:00Z",
    "generation_time": 45.2,
    "config_hash": "abc123"
  }
}
```

**驗收條件**：
- [x] 6 個端點全部正常回傳
- [x] 分頁 + 排序 + 篩選正確
- [x] correlation 端點特徵數限制 ≤ 50（避免 O(n²) 爆記憶體）
- [x] browse/data 特徵數限制 ≤ 20
- [x] search 支援模糊搜尋（大小寫不敏感）

### 驗證檢查點
- PASS: `/browse/{task_id}/features?category=microstructure&level=L3` → 只回傳 microstructure 的 L3 特徵
- PASS: `/browse/{task_id}/correlation?features=ms_amihud_illiq_21,ms_kyle_lambda_13` → 2×2 相關矩陣
- PASS: `/browse/{task_id}/summary` → quality.constant_features 正確列出常量特徵
- PASS: 失敗/邊界路徑 — `sort_by` 非法值與 `features` 超過上限（data>20, correlation>50）時回傳 4xx，且錯誤內容明確

**Checklist**：
- [x] `browse_features()` — 分頁 + 排序 + 篩選
- [x] `browse_feature_data()` — 指定特徵的時間序列數據
- [x] `browse_correlation()` — 相關矩陣
- [x] `browse_distribution()` — 直方圖 bin counts + edges
- [x] `browse_nan_pattern()` — NaN 分佈矩陣
- [x] `browse_summary()` — 整體摘要
- [x] HDF5 讀取效率（只讀指定欄位，不載入全量）
- [x] 參數驗證 + 限制

---

### Task 3.3.2：前端 FeatureExplorer 主頁面元件

**檔案**：
- `frontend/src/components/feature-factory/FeatureExplorer.tsx` (新建)

**功能**：整合所有瀏覽器子元件的主容器，提供 Tab 導航。

**UI 結構**：

```
┌─────────────────────────────────────────────────────────┐
│ 🔍 Feature Explorer                    [BTCUSDT · 12h] │
│                                                          │
│ [📊 Overview] [📋 Feature Table] [📈 Time Series]       │
│ [🔥 Correlation] [📉 Distribution] [❓ NaN Pattern]     │
│                                                          │
│ ┌─ 當前 Tab 內容區域 ──────────────────────────────┐   │
│ │                                                     │   │
│ │  （根據選擇的 Tab 切換子元件）                       │   │
│ │                                                     │   │
│ └─────────────────────────────────────────────────────┘   │
│                                                          │
│ [匯出 CSV] [匯出 JSON] [匯出 Markdown] [匯出 PNG]      │
└─────────────────────────────────────────────────────────┘
```

**驗收條件**：
- [x] 6 個 Tab 正確切換
- [x] 載入時顯示 Loading skeleton
- [x] 任務不存在或未完成時顯示 Empty State（引導使用者先生成特徵）
- [x] Tab 切換不重新 fetch 已載入的數據（客戶端快取）

### 驗證檢查點
- PASS: 頁面載入 → Overview Tab 自動顯示 summary 數據
- PASS: 切換到 Feature Table → 分頁表格正確載入
- PASS: 無生成結果時 → 顯示 Empty State + 「前往生成」按鈕
- PASS: 失敗/邊界路徑 — Tab 快速切換時不重複發送同一請求，已載入資料可被快取重用

**Store 擴展規格**（`featureFactoryStore.ts`）：

```typescript
// 新增 explorer 相關 state
interface FeatureFactoryState {
  // ... 既有 state
  
  // Explorer state
  explorerTaskId: string | null;        // 當前瀏覽的已完成任務 ID
  explorerActiveTab: ExplorerTab;        // 當前 Tab: 'overview' | 'table' | 'timeseries' | 'correlation' | 'distribution' | 'nan'
  explorerSelectedFeature: string | null;  // 從 FeatureTable 點擊跳轉時帶入的特徵名
  explorerSelectedFeatures: string[];    // 從 FeatureTable 多選帶入的特徵列表
  explorerSummary: FeatureSummary | null; // 快取 summary 數據
  
  // Actions
  setExplorerTaskId: (taskId: string) => void;
  setExplorerActiveTab: (tab: ExplorerTab, selectedFeature?: string) => void;
  setExplorerSelectedFeatures: (features: string[]) => void;
}
```

**Cross-Tab 互動機制**：
- **FeatureTable → Distribution**：點擊特徵名 → `setExplorerActiveTab('distribution', featureName)` → Distribution Tab 自動載入該特徵
- **FeatureTable → Correlation**：多選勾選 → 點擊「比較」→ `setExplorerSelectedFeatures([...]) + setExplorerActiveTab('correlation')` → Correlation Tab 自動載入選中特徵
- **任何 Tab → FeatureTable**：Breadcrumb 或「回到列表」按鈕 → `setExplorerActiveTab('table')`

**Hook 擴展規格**（`useFeatureFactory.ts`）：

```typescript
// 新增 browse API 呼叫方法
const useBrowseFeatures = (taskId: string, params: BrowseParams) => { /* ... */ };
const useBrowseSummary = (taskId: string) => { /* ... */ };
const useBrowseCorrelation = (taskId: string, features: string[], method: string) => { /* ... */ };
const useBrowseDistribution = (taskId: string, feature: string, nBins: number) => { /* ... */ };
const useBrowseNanPattern = (taskId: string, sampleFeatures: number) => { /* ... */ };
const useBrowseData = (taskId: string, features: string[], offset: number, limit: number) => { /* ... */ };
```

**TypeScript 型別定義**（`lib/types.ts`）：

新增以下 interface：
- `FeatureSummary` — `/browse/{task_id}/summary` 回傳
- `BrowseFeatureItem` — 單一特徵的 metadata + 統計
- `BrowseFeaturesResponse` — 分頁回傳（items + total + offset + limit）
- `CorrelationMatrix` — `{ features: string[], matrix: number[][] }`
- `DistributionData` — `{ bins: number[], edges: number[], stats: FeatureStats }`
- `NanPatternData` — `{ features: string[], matrix: boolean[][], nan_ratios: number[] }`
- `ExplorerTab` — union type `'overview' | 'table' | 'timeseries' | 'correlation' | 'distribution' | 'nan'`

**Checklist**：
- [x] Tab 導航元件
- [x] Lazy loading（Tab 內容首次點擊時才 fetch）
- [x] 客戶端數據快取（store 或 React Query）
- [x] Empty / Loading / Error 三態處理
- [x] 響應式佈局
- [x] `featureFactoryStore.ts` explorer state 擴展
- [x] `useFeatureFactory.ts` browse API 方法擴展
- [x] `lib/types.ts` 新增 Explorer 相關 interface
- [x] Cross-Tab 互動連動（shared state）

---

### Task 3.3.3：OverviewDashboard — 總覽儀表板

**檔案**：
- `frontend/src/components/feature-factory/OverviewDashboard.tsx` (新建)

**功能**：讀取 `/browse/{task_id}/summary` 的數據，以 Dashboard 形式呈現全局概覽。

**UI 結構**：

```
┌─────────────────────────────────────────────────────────┐
│ 📊 Overview Dashboard                                    │
│                                                          │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│ │ Features │ │  Rows    │ │ NaN Avg  │ │ Quality  │   │
│ │  25,000  │ │   657    │ │  2.0%    │ │  85/100  │   │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                          │
│ ┌─ By Category (Treemap) ─┐ ┌─ By Level (Donut) ────┐  │
│ │ ┌──trend──┐┌momentum──┐ │ │      ┌──┐              │  │
│ │ │  120    ││   90     │ │ │   ┌──┘L1└──┐           │  │
│ │ └────────┘└──────────┘ │ │   │  3000   │           │  │
│ │ ┌microstr┐┌entropy──┐  │ │   └──┬──────┘           │  │
│ │ │  25    ││  15     │  │ │ L2: 5000  L3: 2000     │  │
│ │ └────────┘└─────────┘  │ └─────────────────────────┘  │
│ └─────────────────────────┘                              │
│                                                          │
│ ┌─ By Layer (Stacked Bar) ──────────────────────────┐   │
│ │ Layer1 ████ 500                                     │   │
│ │ Layer2 ████████ 2000                                │   │
│ │ Layer3 ████████████████ 8000                        │   │
│ │ Layer4 ████████████████████ 10000                   │   │
│ │ Layer6.5 ██████ 3000                                │   │
│ └─────────────────────────────────────────────────────┘  │
│                                                          │
│ ┌─ Quality Alerts ──────────────────────────────────┐   │
│ │ ⚠️ ms_vpin_30 — NaN 12% (超過 10%)                │   │
│ │ ℹ️ ent_hurst_200 — 200 bars warmup                 │   │
│ │ ⚠️ 3 個常量特徵建議移除                              │   │
│ └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Quality Score 計算公式**：

```python
# 0-100 分，加權計算
quality_score = (
    (1 - nan_ratio_mean) * 40          # NaN 越少分越高（40 分）
    + stationary_ratio * 30             # 定態比越高越好（30 分）
    + (1 - constant_ratio) * 15         # 常量特徵越少越好（15 分）
    + (1 - high_corr_ratio) * 15        # 高相關對越少越好（15 分）
) 
# 其中：
# constant_ratio = len(constant_features) / total_features
# high_corr_ratio = high_corr_pairs_count / (total_features * (total_features - 1) / 2)
```

色碼：≥ 80 綠（emerald）、60-79 黃（amber）、< 60 紅（rose）。

**驗收條件**：
- [x] 4 個頂部 KPI 卡片（Features / Rows / NaN Avg / Quality Score）
- [x] Quality Score 公式正確實作且色碼正確
- [x] Category Treemap 或 Bar Chart（響應式，<768px 改為清單）
- [x] Level Donut Chart（L1/L2/L3 分佈）
- [x] Layer Stacked Bar Chart
- [x] Quality Alerts 列表（severity 色碼：warning=amber, info=blue, error=rose）
- [x] 所有圖表支援 PNG 匯出
- [x] 無數據時顯示空狀態提示

### 驗證檢查點
- PASS: KPI 數字與 summary API 回傳一致
- PASS: Treemap 各區塊面積比例正確
- PASS: Quality Alerts 排序：error > warning > info
- PASS: 失敗/邊界路徑 — summary 無資料時 Dashboard 顯示 Empty State，不渲染錯誤圖表

**Checklist**：
- [x] KPI 卡片元件
- [x] Category 圖表（Recharts Treemap 或 Bar）
- [x] Level Donut（Recharts PieChart）
- [x] Layer Stacked Bar（Recharts BarChart）
- [x] Quality Alerts 列表
- [x] PNG 匯出按鈕
- [x] Empty State 處理
- [x] 響應式適配

---

### Task 3.3.4：FeatureTable — 可排序/篩選的特徵列表

**檔案**：
- `frontend/src/components/feature-factory/FeatureTable.tsx` (新建)

**功能**：讀取 `/browse/{task_id}/features` 的分頁數據，以高效能虛擬捲動表格呈現。

**特性**：
- **虛擬捲動**：使用 `@tanstack/react-virtual` 或 `react-window`，支援 10,000+ 行 60fps
- **伺服端分頁**：每頁 50 筆，捲動到底自動載入下一頁
- **排序**：點擊 column header 排序（nan_ratio / std / skewness / kurtosis / name）
- **篩選**：
  - Category dropdown（trend / momentum / ... / microstructure / entropy）
  - Level Tab（L1 / L2 / L3 / All）
  - 搜尋框（模糊搜尋特徵名）
- **色彩編碼**：
  - NaN ratio：< 5% 綠、5-10% 黃、> 10% 紅
  - Skewness：|s| < 1 綠、1-3 黃、> 3 紅
  - Kurtosis：k < 5 綠、5-10 黃、> 10 紅
- **行動作**：
  - 點擊特徵名 → 跳轉 Distribution Tab（帶入該特徵）
  - 勾選多個特徵 → 「比較」按鈕 → 跳轉 Correlation Tab

**Table Columns**：

| 欄位 | 寬度 | 排序 | 說明 |
|------|------|------|------|
| ☐ | 40px | — | 多選勾選框 |
| Feature Name | 250px | ✓ | 特徵名（可搜尋） |
| Category | 100px | — | 引擎分類 badge |
| Level | 60px | — | 等級 badge (🟢🟡🔴) |
| Layer | 60px | — | Pipeline 層 |
| NaN% | 80px | ✓ | NaN 比率（色碼） |
| Mean | 100px | ✓ | 平均值 |
| Std | 100px | ✓ | 標準差 |
| Skew | 80px | ✓ | 偏度（色碼） |
| Kurt | 80px | ✓ | 峰度（色碼） |
| Stationary | 80px | ✓ | ADF 定態性 (✓/✗) |

**驗收條件**：
- [x] 25,000 筆特徵 list 流暢捲動（60fps）
- [x] 排序 + 篩選正確（伺服端）
- [x] 色彩編碼正確
- [x] 行交互（點擊跳轉 / 多選比較）
- [x] 搜尋防抖（300ms debounce）

### 驗證檢查點
- PASS: 輸入 "ms_" → 表格只顯示 microstructure 特徵
- PASS: 選擇 L3 Tab → 只顯示 microstructure + entropy
- PASS: 勾選 3 個特徵 → 點擊「比較」→ Correlation Tab 載入 3×3 矩陣
- PASS: 失敗/邊界路徑 — 搜尋字串含特殊字元時可安全查詢並保持結果可渲染（無前端例外）

**Checklist**：
- [x] 虛擬捲動 or infinity scroll
- [x] 伺服端排序 API 呼叫
- [x] 篩選 UI（category / level / search）
- [x] 色碼函式（NaN / Skew / Kurt）
- [x] 行交互（點擊 / 多選）
- [x] 搜尋防抖
- [x] 分頁載入指示器
- [x] Empty State

---

### Task 3.3.5：TimeSeriesChart — 特徵時間序列圖

**檔案**：
- `frontend/src/components/feature-factory/FeatureTimeSeriesChart.tsx` (新建)

**功能**：讀取 `/browse/{task_id}/data` 的數據，繪製可疊加的多特徵走勢圖。

**特性**：
- **多特徵疊加**：最多疊加 5 條線（不同顏色）
- **特徵選擇器**：搜尋式 dropdown，從 feature list 中選取
- **雙 Y 軸**：左右兩軸支援不同量級的特徵
- **十字準星**：滑鼠懸停顯示精確值 + 日期
- **縮放**：X 軸範圍滑桿，可縮放時間範圍
- **基準線**：可選 OHLC 價格作為 overlay 基準

**驗收條件**：
- [x] 選擇 1-5 個特徵，走勢圖正確繪製
- [x] 雙 Y 軸正確處理不同量級
- [x] 十字準星 tooltip 顯示所有選中特徵的值
- [x] 縮放滑桿操作流暢

### 驗證檢查點
- PASS: 選擇 `ms_amihud_illiq_21` + `close` → 雙軸顯示（左軸 Amihud，右軸 Price）
- PASS: 縮放到最近 100 bars → 圖表正確更新
- PASS: 失敗/邊界路徑 — 選擇特徵超過 5 條時 UI 阻擋超額選取並保留既有 1-5 條曲線渲染

**Checklist**：
- [x] 特徵選擇器（searchable dropdown）
- [x] Recharts LineChart + dual YAxis
- [x] Custom Tooltip（十字準星風格）
- [x] X 軸縮放 Brush
- [x] OHLC overlay 選項
- [x] Loading / Empty state

---

### Task 3.3.6：CorrelationHeatmap — 相關性熱力圖

**檔案**：
- `frontend/src/components/feature-factory/FeatureCorrelationHeatmap.tsx` (新建)

**功能**：讀取 `/browse/{task_id}/correlation` 的數據，繪製 N×N 相關矩陣熱力圖。

**特性**：
- **特徵選擇**：從 FeatureTable 多選帶入，或手動搜尋選擇（最多 50 個）
- **快捷選擇**：「選取某 Category 全部」「選取 Top-K by Std」
- **色彩**：-1（深藍）→ 0（白）→ +1（深紅）
- **互動**：懸停顯示精確相關係數 + 特徵對名稱
- **方法切換**：Pearson / Spearman / Kendall
- **高相關警告**：|ρ| > 0.95 的格子標記黃色三角警告

**驗收條件**：
- [x] 50×50 矩陣渲染流暢
- [x] 色彩比例正確
- [x] Tooltip 顯示精確值
- [x] 方法切換正確重新計算
- [x] 高相關對警告視覺化

### 驗證檢查點
- PASS: 選取 microstructure 全部 25 特徵 → 25×25 熱力圖正確
- PASS: 切換 Spearman → 矩陣值更新
- PASS: |ρ| > 0.95 的格子有警告標記
- PASS: 失敗/邊界路徑 — 請求超過 50 特徵或 method 非法值時回傳 4xx，前端顯示錯誤訊息且不崩潰

**Checklist**：
- [x] 特徵多選 UI
- [x] 快捷選擇按鈕
- [x] SVG/Canvas 熱力圖繪製
- [x] 色彩 scale（diverging blue-white-red）
- [x] Tooltip
- [x] 方法切換
- [x] 高相關警告
- [x] PNG 匯出

---

### Task 3.3.7：DistributionChart — 分佈圖

**檔案**：
- `frontend/src/components/feature-factory/FeatureDistributionChart.tsx` (新建)

**功能**：讀取 `/browse/{task_id}/distribution` 的數據，繪製單特徵分佈直方圖 + 統計資訊面板。

**特性**：
- **直方圖**：可調 bin 數（10-200）
- **Normal overlay**：疊加常態分佈曲線（使用 mean/std）
- **統計面板**：Mean / Std / Skew / Kurtosis / ADF p-value / NaN ratio
- **QQ-Plot**：理論分位數 vs 實際分位數散點圖
- **特徵切換**：快速切換查看不同特徵

**驗收條件**：
- [x] 直方圖 bin 調整即時更新
- [x] Normal overlay 曲線正確
- [x] 統計面板數值正確
- [x] QQ-Plot 正確繪製
- [x] 特徵切換不閃爍

### 驗證檢查點
- PASS: `ms_amihud_illiq_21` 分佈為右偏（skew > 0）→ 直方圖視覺上右偏
- PASS: QQ-Plot 偏離對角線 → 確認非常態
- PASS: 失敗/邊界路徑 — 特徵全 NaN 或常量時仍回傳可渲染資料結構（空/單峰），UI 顯示對應提示

**Checklist**：
- [x] Recharts BarChart（直方圖）
- [x] Normal distribution overlay（Line）
- [x] 統計資訊面板
- [x] QQ-Plot（Scatter）
- [x] bin 數滑桿
- [x] 特徵切換 dropdown

---

### Task 3.3.8：NaNPatternChart — 缺失值分佈圖

**檔案**：
- `frontend/src/components/feature-factory/NaNPatternChart.tsx` (新建)

**功能**：讀取 `/browse/{task_id}/nan-pattern` 的數據，以 missingno 風格視覺化缺失值分佈。

**特性**：
- **矩陣圖**：X 軸為時間，Y 軸為特徵（取樣 50 個）
  - 黑格 = 有值、白格 = NaN
- **NaN 比率排序**：按 NaN ratio 由高到低排列
- **分群**：相同 NaN pattern 的特徵自動分群（warmup 類 vs 隨機遺漏）
- **統計面板**：完整率分佈直方圖 + 危險特徵列表（NaN > 10%）

**驗收條件**：
- [x] 矩陣圖正確顯示 NaN 分佈模式
- [x] warmup NaN（左側集中）和隨機 NaN 可視覺區分
- [x] 危險特徵列表正確

### 驗證檢查點
- PASS: Entropy/Hurst 特徵在左側（early bars）呈現明顯 warmup NaN pattern
- PASS: 大部分 Layer 1 特徵完整率 > 95%
- PASS: 失敗/邊界路徑 — 所有特徵 NaN=0% 時回傳空矩陣並顯示「所有特徵完整」訊息

**Checklist**：
- [x] SVG/Canvas 矩陣繪製
- [x] NaN ratio 排序
- [x] 分群邏輯
- [x] 統計面板
- [x] PNG 匯出

---

### Task 3.3.9：page.tsx 整合 — FeatureExplorer 嵌入頁面

**檔案**：
- `frontend/src/app/feature-factory/page.tsx` (修改)

**修改重點**：

在 `GenerationProgress` 之後、`AutoResearchPanel` 之前，新增 `FeatureExplorer`：

```tsx
import FeatureExplorer from '@/components/feature-factory/FeatureExplorer';

// 在 GenerationProgress 之後
{currentTask?.status === 'completed' && (
  <FeatureExplorer taskId={currentTask.task_id} />
)}
```

**渲染條件**：只在任務完成後顯示（`currentTask.status === 'completed'`）。

**驗收條件**：
- [x] 任務未完成 → FeatureExplorer 不渲染
- [x] 任務完成 → FeatureExplorer 自動出現
- [x] 頁面不因 Explorer 載入而卡頓（Lazy loading）

### 驗證檢查點
- PASS: 生成任務完成 → FeatureExplorer 自動出現
- PASS: Overview Tab 自動載入 summary
- PASS: 失敗/邊界路徑 — 任務非 completed 狀態時 FeatureExplorer 不渲染且不觸發 browse API

**Checklist**：
- [x] import FeatureExplorer
- [x] 條件渲染
- [x] taskId 傳遞
- [x] Lazy loading（React.lazy + Suspense）

---

## Phase 3.4：測試與驗收

### Task 3.4.1：後端 API 測試

**檔案**：
- `tests/api/test_feature_export.py` (新建)

**測試內容**：

| 類別 | 測試數 | 覆蓋 |
|------|--------|------|
| CSV 匯出 | 5 | 正常串流 / 欄位篩選 / 行數限制 / metadata header / 404 |
| JSON 匯出 | 5 | Schema 驗證 / 分級正確 / per_feature 統計 / quality_alerts / correlation |
| Markdown 匯出 | 4 | Token 預算 / sections 篩選 / 語言切換 / XSS 防護 |
| Browse API | 8 | 分頁 / 排序 / 篩選 / 相關矩陣 / 分佈 / NaN / summary / 搜尋 |
| **合計** | **22** | |

**驗收條件**：
- [x] 22 個測試全部 PASS
- [x] CSV 串流使用 `httpx.AsyncClient` streaming

### 驗證檢查點
- PASS: `pytest tests/api/test_feature_export.py -v --tb=short` 全通過
- PASS: 失敗/邊界路徑 — 測試集包含至少一個不存在 `task_id`/非法參數案例，能穩定斷言 4xx 與錯誤訊息

---

### Task 3.4.2：前端整合驗收

**驗收清單**：

| # | 項目 | 驗收方式 |
|---|------|---------|
| 1 | IndicatorSelector 顯示 10 個引擎 | 肉眼驗證 |
| 2 | 分級 Tab 篩選正確 | 點擊各 Tab 比對數量 |
| 3 | PreprocessingPanel 6 種轉換可控 | 開關操作 + preview 更新 |
| 4 | Preset 載入正確 | 選擇各 Preset → 比對 config |
| 5 | ExportButtons 4 種匯出格式 | 各點一次 → 檢查下載檔案 |
| 6 | FeatureExplorer Overview Dashboard | 生成後自動顯示 → KPI 數字正確 |
| 7 | FeatureTable 分頁排序篩選 | 操作表格 → 驗證結果 |
| 8 | TimeSeriesChart 多特徵疊加 | 選 3 特徵 → 3 條線正確 |
| 9 | CorrelationHeatmap 50×50 | 選 50 特徵 → 矩陣渲染無卡頓 |
| 10 | DistributionChart 直方圖 + QQ | 選 1 特徵 → 圖表正確 |
| 11 | NaNPatternChart warmup 可見 | Entropy 特徵左側 NaN 模式 |
| 12 | 響應式 1440/768/375px | 三種寬度截圖比對佈局 |
| 13 | Empty State 處理 | 未生成時各元件正確顯示空狀態 |
| 14 | TypeScript 編譯 zero errors | `npm run build` |

---

### Task 3.4.3：驗收報告

#### 功能驗收
- [x] 10 個引擎前端可開關（含 microstructure / entropy / tail_risk）
- [x] 6 種前處理前端可控
- [ ] 4 種匯出格式（HDF5 / CSV / JSON / Markdown）
- [x] 6 個 Explorer Tab 全部可用
- [ ] 4 個分級 Preset 正確載入

#### 品質驗收
- [ ] CSV 串流不 OOM（30,000 欄 × 600 行）
- [ ] JSON Schema 符合 ADR-002
- [ ] Markdown Token 預算控制有效
- [ ] 前端 10,000+ 行虛擬捲動 60fps
- [x] 所有動態字串 HTML entity escaped

#### 架構驗收
- [x] 新 API 端點在既有 Router（B1）
- [x] 新前端元件在既有目錄（F1）
- [x] Store 擴展不建新 Store（F2）
- [ ] Rule 1-7 無違規

#### 效能驗收
- [ ] CSV 串流 30,000 欄 × 600 行 < 10s
- [ ] JSON 匯出 25,000 特徵 < 5s
- [ ] Markdown 匯出 < 1s
- [ ] 前端首次渲染 < 200ms
- [ ] CorrelationHeatmap 50×50 渲染 < 500ms

---

## Phase 依賴圖（Part 3）

```
Phase 3.1 (前端開關 UI)
  3.1.1 IndicatorSelector 擴展
  3.1.2 PreprocessingPanel (新建)
  3.1.3 page.tsx 整合
  3.1.4 Preset 擴展
  ⚠️ 3.1.1-3.1.2 可平行開發

Phase 3.2 (多格式匯出)
  3.2.1 CSV 串流 API ──→ 3.2.4 前端 ExportButtons
  3.2.2 JSON API      ──→ 3.2.4
  3.2.3 Markdown API   ──→ 3.2.4
  ⚠️ 3.2.1-3.2.3 可平行開發

Phase 3.3 (Feature Explorer)
  3.3.1 Browse API (6 端點) ──→ 3.3.2~3.3.8 前端元件
  3.3.2 FeatureExplorer 主框架 ──→ 3.3.3~3.3.8 子元件
  3.3.3 OverviewDashboard
  3.3.4 FeatureTable
  3.3.5 TimeSeriesChart
  3.3.6 CorrelationHeatmap
  3.3.7 DistributionChart
  3.3.8 NaNPatternChart
  3.3.9 page.tsx 整合
  ⚠️ 3.3.3-3.3.8 可平行開發

Phase 3.4 (測試與驗收)
  依賴 ALL Phase 3.1-3.3
  3.4.1 後端 API 測試
  3.4.2 前端整合驗收
  3.4.3 驗收報告
```

**跨 Phase 依賴**：
```
Phase 3.1.1 (IndicatorSelector) ──→ Phase 3.3.4 (FeatureTable 的 level filter)
Phase 3.2.2 (JSON API) ──→ Phase 3.3.1 (Browse API 共用 FeatureExportService)
Phase 3.1.4 (Preset) 無外部依賴，可最早開發
```

---

## 檔案清單（Part 3）

### 新增檔案

```
frontend/src/components/feature-factory/
├── PreprocessingPanel.tsx          (Task 3.1.2)
├── FeatureExplorer.tsx             (Task 3.3.2)
├── OverviewDashboard.tsx           (Task 3.3.3)
├── FeatureTable.tsx                (Task 3.3.4)
├── FeatureTimeSeriesChart.tsx      (Task 3.3.5)
├── FeatureCorrelationHeatmap.tsx   (Task 3.3.6)
├── FeatureDistributionChart.tsx    (Task 3.3.7)
└── NaNPatternChart.tsx             (Task 3.3.8)

api/services/
└── feature_export_service.py       (Task 3.2.2)

tests/api/
└── test_feature_export.py          (Task 3.4.1)
```

### 修改檔案

```
frontend/src/components/feature-factory/
├── IndicatorSelector.tsx           (Task 3.1.1)
└── ExportButtons.tsx               (Task 3.2.4)

frontend/src/app/feature-factory/
└── page.tsx                        (Task 3.1.3, 3.3.9)

frontend/src/store/
└── featureFactoryStore.ts          (擴展 explorer state)

frontend/src/hooks/
└── useFeatureFactory.ts            (擴展 browse API 呼叫)

frontend/src/lib/
└── types.ts                        (新增 Explorer 相關 interface)

api/routes/
└── feature_factory.py              (Task 3.2.1~3.2.3, 3.3.1)

api/services/
└── feature_factory_service.py      (Task 3.1.4, 3.2.1, 3.3.1)
```

### 統計

| 類別 | 檔案數 |
|------|--------|
| 新增前端元件 | 8 |
| 新增後端 Service | 1 |
| 新增測試 | 1 |
| 修改前端檔案 | 6 |
| 修改後端檔案 | 2 |
| **合計** | **18 (10 新增 + 8 修改)** |

### npm 新增依賴

| 套件 | 版本 | 用途 |
|------|------|------|
| `@tanstack/react-virtual` | ^3.x | FeatureTable 萬行虛擬捲動 |

---

## 預估時程

| Phase | 任務 | 預估天數 |
|-------|------|---------|
| 3.1 | 前端開關 UI + Preset | 2-3 天 |
| 3.2 | 多格式匯出 API + UI | 3-4 天 |
| 3.3 | Feature Explorer (API + 6 元件 + 整合) | 5-7 天 |
| 3.4 | 測試與驗收 | 2 天 |
| **合計** | | **~12-16 天** |

---

> **狀態**: 🔒 V5 Frozen — 自審 4 輪通過

<!-- STATUS: CONVERGED / READY TO FREEZE -->
