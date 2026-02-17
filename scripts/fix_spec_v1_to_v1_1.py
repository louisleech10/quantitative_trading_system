#!/usr/bin/env python3
"""Fix Feature_Factory_優化SPEC.md V1.0 → V1.1 based on self-review audit."""
import os

SPEC_PATH = os.path.join(
    "/Users/louis/Desktop/quantitative_trading_system/docs",
    "Feature_Factory_優化SPEC.md"
)

with open(SPEC_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# Fix 1: Header - Update version and test count
# ============================================================
content = content.replace(
    '> **版本**: V1.0',
    '> **版本**: V1.1'
)
content = content.replace(
    '> **狀態**: 📝 V1.0 — Self-Review 中',
    '> **狀態**: 📝 V1.1 — Self-Review 修正版'
)
content = content.replace(
    '>   - 邊界條件 100% 覆蓋（51 項邊界條件 × 測試映射）',
    '>   - 邊界條件 100% 覆蓋（51 項邊界條件 × 測試映射）\n'
    '>   - (V1.1) 修正 5 個審計問題 + 3 個改進建議（見附錄 B）'
)

# ============================================================
# Fix 2: EntropyEngine __init__ - Add self.shannon_windows
# ============================================================
content = content.replace(
    "        self.hurst_windows = config.get('hurst_windows', [55, 100, 200])\n"
    "        self.fractal_kmax = config.get('fractal_kmax', 10)\n"
    "        self.use_numba = config.get('use_numba', True)\n"
    "        self.perm_m = config.get('perm_m', 3)",

    "        self.shannon_windows = config.get('shannon_windows', [21, 55, 100])\n"
    "        self.hurst_windows = config.get('hurst_windows', [55, 100, 200])\n"
    "        self.fractal_kmax = config.get('fractal_kmax', 10)\n"
    "        self.use_numba = config.get('use_numba', True)\n"
    "        self.perm_m = config.get('perm_m', 3)"
)

# ============================================================
# Fix 3: EntropyEngine compute_all - Clarify close_return resolution
# ============================================================
content = content.replace(
    '    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:\n'
    '        """計算所有啟用的資訊理論特徵。"""',

    '    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:\n'
    '        """計算所有啟用的資訊理論特徵。\n'
    '        \n'
    '        apply_to 欄位解析規則：\n'
    "        - 'close_return' → data['close'].pct_change()\n"
    "        - 'volume' → data['volume']\n"
    "        - 'taker_ratio' → data['taker_ratio']\n"
    '        其他 → 直接取 data[column_name]\n'
    '        """'
)

# ============================================================
# Fix 4: §7.1 Layer 6.5 integration logic - Fix feature duplication
# ============================================================
content = content.replace(
    """layer6_5 = pd.DataFrame()
if hasattr(config, 'preprocessing') and config.preprocessing.enabled:
    all_features = self._combine_layers([layer1, layer2, layer3, layer4, layer5, layer6])
    layer6_5 = self._safe_execute(
        "Layer 6.5",
        self._layer6_5_preprocessing,
        all_features,
        config
    )

result = self._layer7_validate_and_persist(
    symbol, timeframe, raw_data,
    [layer1, layer2, layer3, layer4, layer5, layer6, layer6_5],
    config, time.time() - start_time, config_hash
)""",

    """# Layer 6.5 Preprocessing（避免特徵重複的正確邏輯）
layers_for_validation = [layer1, layer2, layer3, layer4, layer5, layer6]

if hasattr(config, 'preprocessing') and config.preprocessing.enabled:
    all_features = self._combine_layers(layers_for_validation)
    preprocessed = self._safe_execute(
        "Layer 6.5",
        self._layer6_5_preprocessing,
        all_features,
        config
    )
    if not preprocessed.empty:
        # preprocessed 包含 winsorized 原始特徵 + append 的新欄位
        # 用 preprocessed 取代 layer1-6（避免重複）
        layers_for_validation = [preprocessed]

result = self._layer7_validate_and_persist(
    symbol, timeframe, raw_data,
    layers_for_validation,
    config, time.time() - start_time, config_hash
)"""
)

# ============================================================
# Fix 5: §6.6 FracDiff - Replace for loop with vectorized implementation
# ============================================================
content = content.replace(
    """def frac_diff_ffd(series: pd.Series, d: float, threshold: float = 1e-5) -> pd.Series:
    \"\"\"Fixed-Width Window Fractional Differencing。\"\"\"
    weights = get_weights_ffd(d, threshold)
    width = len(weights)
    result = pd.Series(index=series.index, dtype=float)
    for i in range(width - 1, len(series)):
        result.iloc[i] = np.dot(weights, series.iloc[i - width + 1:i + 1].values)
    return result""",

    """def frac_diff_ffd(series: pd.Series, d: float, threshold: float = 1e-5) -> pd.Series:
    \"\"\"Fixed-Width Window Fractional Differencing（向量化實作）。
    
    使用 np.convolve 進行向量化卷積，避免 Python for 迴圈。
    \"\"\"
    weights = get_weights_ffd(d, threshold)
    width = len(weights)
    vals = series.dropna().values
    # 向量化卷積：weights 已是逆序（get_weights_ffd 返回 w[::-1]）
    convolved = np.convolve(vals, weights[::-1], mode='full')[:len(vals)]
    result = pd.Series(np.nan, index=series.index, dtype=float)
    # 前 width-1 個值為 NaN（不足窗口）
    valid_idx = series.dropna().index[width - 1:]
    result.loc[valid_idx] = convolved[width - 1:]
    return result"""
)

# ============================================================
# Fix 6: §10 - Add test name mappings for degradation scenarios
# ============================================================
content = content.replace(
    """### 10.3 欄位缺失降級

| 缺失欄位 | 影響範圍 | 降級行為 |
|---------|---------|---------|
| `taker_buy_volume` | OFI, VPIN | 使用 `taker_ratio * volume` 替代，log WARNING |
| `taker_ratio` | OFI fallback | 使用 volume-only 估計（精度降低），log WARNING |
| `trades` | Large Trade Ratio | 跳過該指標，log WARNING |
| `quote_volume` | Amihud, Large Trade | 使用 `close * volume` 替代，log WARNING |""",

    """### 10.3 欄位缺失降級

| 缺失欄位 | 影響範圍 | 降級行為 | 測試名 |
|---------|---------|---------|--------|
| `taker_buy_volume` | OFI, VPIN | 使用 `taker_ratio * volume` 替代，log WARNING | `test_degrade_missing_taker_buy_vol` |
| `taker_ratio` | OFI fallback | 使用 volume-only 估計（精度降低），log WARNING | `test_degrade_missing_taker_ratio` |
| `trades` | Large Trade Ratio | 跳過該指標，log WARNING | `test_degrade_missing_trades` |
| `quote_volume` | Amihud, Large Trade | 使用 `close * volume` 替代，log WARNING | `test_degrade_missing_quote_volume` |"""
)

content = content.replace(
    """### 10.4 Optional 套件降級

```python
# 模式：try import → flag → conditional use

try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    logger.warning("Numba not available, ApEn/SampEn will use pure numpy (slower)")

try:
    from statsmodels.tsa.stattools import adfuller
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logger.warning("statsmodels not available, ADF/Fractional Differencing disabled")
```""",

    """### 10.4 Optional 套件降級

| 套件 | 影響範圍 | 降級行為 | 測試名 |
|------|---------|---------|--------|
| `numba` 不可用 | ApEn/SampEn | fallback 純 numpy（速度降低 10x） | `test_degrade_no_numba` |
| `statsmodels` 不可用 | ADF / Fractional Differencing | 兩者自動 disabled，log WARNING | `test_degrade_no_statsmodels` |

```python
# 模式：try import → flag → conditional use

try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    logger.warning("Numba not available, ApEn/SampEn will use pure numpy (slower)")

try:
    from statsmodels.tsa.stattools import adfuller
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logger.warning("statsmodels not available, ADF/Fractional Differencing disabled")
```"""
)

# ============================================================
# Fix 7: §13 - Update test counts and add degradation tests
# ============================================================
content = content.replace(
    """| 模組 | 測試內容 | 測試數 |
|------|---------|--------|
| `MicrostructureIndicatorEngine` | 7 指標正確性 + 邊界條件 (§3.9 × 11) + feature metadata | ~30 |
| `EntropyIndicatorEngine` | 6 指標正確性 + 邊界條件 (§4.8 × 11) + Numba fallback | ~28 |
| `TailRiskIndicatorEngine` | 6 指標正確性 + 邊界條件 (§5.8 × 11) | ~26 |
| `FeaturePreprocessor` | 6 轉換正確性 + 組合 + 邊界條件 (§6.8 × 12) + mode 切換 | ~32 |
| **合計** | | **~116** |""",

    """| 模組 | 測試內容 | 測試數 |
|------|---------|--------|
| `MicrostructureIndicatorEngine` | 7 指標正確性 + 邊界條件 (§3.9 × 11) + feature metadata | ~30 |
| `EntropyIndicatorEngine` | 6 指標正確性 + 邊界條件 (§4.8 × 11) + Numba fallback | ~28 |
| `TailRiskIndicatorEngine` | 6 指標正確性 + 邊界條件 (§5.8 × 11) | ~26 |
| `FeaturePreprocessor` | 6 轉換正確性 + 組合 + 邊界條件 (§6.8 × 12) + mode 切換 | ~32 |
| 降級場景 (§10) | 欄位缺失降級 (×4) + Optional 套件降級 (×2) | ~6 |
| **合計** | | **~122** |"""
)

content = content.replace(
    '所有 51 項邊界條件（§3.9 × 11 + §4.8 × 11 + §5.8 × 11 + §6.8 × 12 = 45 項 + §10 降級 × 6 = 51 項）均有對應的測試用例。',
    '所有 51 項邊界條件（§3.9 × 11 + §4.8 × 11 + §5.8 × 11 + §6.8 × 12 = 45 項 + §10.3 × 4 + §10.4 × 2 = 51 項）均有明確的測試名映射，100% 覆蓋。'
)

# ============================================================
# Fix 8: §15.2 - Update vectorization exception description
# ============================================================
content = content.replace(
    '- [ ] 所有計算向量化（無 Python for 迴圈 on data rows，除 ApEn/SampEn 的 Numba JIT 和 FracDiff 的 d* 搜尋）',
    '- [ ] 所有計算向量化（無 Python for 迴圈 on data rows，除 ApEn/SampEn 的 Numba JIT 內部迴圈、FracDiff 的 d* 二分搜尋 loop、以及 Hurst/Fractal 的 rolling.apply 回調）'
)

# ============================================================
# Improvement: Pydantic field validators for critical fields
# ============================================================
content = content.replace(
    '''class TailRiskConfig(BaseModel):
    """尾部風險指標配置"""
    enabled: bool = False
    windows: List[int] = [21, 55, 100]
    cvar_alphas: List[float] = [0.01, 0.05]
    rv_windows: List[int] = [13, 21, 55]
    mdd_windows: List[int] = [21, 55, 100]''',

    '''class TailRiskConfig(BaseModel):
    """尾部風險指標配置"""
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
        return v'''
)

content = content.replace(
    '''class EntropyConfig(BaseModel):
    """資訊理論指標配置"""
    enabled: bool = False
    windows: List[int] = [55, 100]
    n_bins: int = 10
    apen_m: int = 2
    apen_r_ratio: float = 0.2
    hurst_windows: List[int] = [55, 100, 200]
    fractal_kmax: int = 10
    use_numba: bool = True
    perm_m: int = 3
    perm_windows: List[int] = [21, 55, 100]
    apply_to: List[str] = ['close_return']
    shannon_windows: List[int] = [21, 55, 100]''',

    '''class EntropyConfig(BaseModel):
    """資訊理論指標配置"""
    enabled: bool = False
    windows: List[int] = [55, 100]
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
        return v'''
)

# ============================================================
# Update header test count from 124 to 134
# ============================================================
content = content.replace(
    '；測試 91→124 項；',
    '；測試 91→134 項（122 單元 + 7 整合 + 5 效能）；'
)

# ============================================================
# Update version history
# ============================================================
content = content.replace(
    """| V1.0 | 2026-02-17 | 新增 VPIN/Permutation Entropy/Rolling MDD/Fractional Differencing 4 指標；Codebase 對齊（Engine 建構子、get_feature_metadata）；新增 §9-§16（下游影響/錯誤處理/快取/Logging/效能/MCP）；邊界條件 45→51 項；測試 91→124 項；附錄文獻 12→14 篇 |""",

    """| V1.0 | 2026-02-17 | 新增 VPIN/Permutation Entropy/Rolling MDD/Fractional Differencing 4 指標；Codebase 對齊（Engine 建構子、get_feature_metadata）；新增 §9-§16（下游影響/錯誤處理/快取/Logging/效能/MCP）；邊界條件 45→51 項；附錄文獻 12→14 篇 |
| V1.1 | 2026-02-17 | Self-Review 修正：(1) EntropyEngine 新增 shannon_windows 初始化 (2) Layer 6.5 整合邏輯修正避免特徵重複 (3) §10 降級新增測試名映射 (4) FracDiff 改用 np.convolve 向量化 (5) Pydantic 新增 field_validator (6) EntropyEngine compute_all 明確 close_return 解析規則 (7) 測試合計更新為 134 |"""
)

# Update final status
content = content.replace(
    '> **狀態**: 📝 V1.0 — Self-Review 中',
    '> **狀態**: 📝 V1.1 — 待二次審計'
)

# ============================================================
# Write back
# ============================================================
with open(SPEC_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"V1.1 fixes applied. File size: {len(content)} chars, {content.count(chr(10))} lines")
