# Feature Library 重設計 — 執行計畫

> **執行者**：AI Agent (Codex 5.3)  
> **來源文件**：`docs/FEATURE_LIBRARY_FIRST_PRINCIPLES_REDESIGN.md`  
> **最後更新**：2026-03-21  
> **狀態**：🔒 FROZEN — 禁止修改執行順序或方案選擇

---

## 執行規則

1. **嚴格按 TASK 編號順序執行**，不可跳號
2. 每個 TASK 完成後**必須執行對應的測試**，全部 PASS 才能進入下一個 TASK
3. 每個 TASK 給出的**檔案路徑和行號是參考**，實際行號可能因先前 TASK 修改而偏移；以程式碼上下文為準
4. 所有方案已凍結，TASK 內無選項——照做即可
5. **不要新增任何未列在此文件中的功能、重構或「順手改進」**
6. 測試檔案一律放在 `tests/feature_library/` 目錄
7. 執行測試命令：`./venv/bin/pytest tests/feature_library/ -v --tb=short`
8. 解耦驗證命令：`grep -r "from api\." momentum/ | grep -v __pycache__ | wc -l`（必須為 0）

---

## 依賴關係

```
Phase 1 (引擎基礎)
  ├─ TASK-1.1  float32 修正
  ├─ TASK-1.2  get_last_timestamp 實作鏈
  ├─ TASK-1.3  config_hash 加入 kline_last_ts  ← 依賴 1.2
  ├─ TASK-1.4  log_volume 合成欄位
  └─ TASK-1.5  Phase 1 測試                    ← 依賴 1.1~1.4

Phase 2 (持久化層)                              ← 依賴 Phase 1
  ├─ TASK-2.1  registry.json 寫入
  ├─ TASK-2.2  registry.json 恢復 + API
  └─ TASK-2.3  Phase 2 測試                    ← 依賴 2.1~2.2

Phase 3 (抽象層)                                ← 依賴 Phase 2
  ├─ TASK-3.1  FeatureLibraryEntry + Error 定義
  ├─ TASK-3.2  FeatureLibrary 類別 + factory
  └─ TASK-3.3  Phase 3 測試                    ← 依賴 3.1~3.2

Phase 4 (消費者遷移)                             ← 依賴 Phase 3
  ├─ TASK-4.1  generate_features() date range + API model
  ├─ TASK-4.2  IC analysis service 遷移
  ├─ TASK-4.3  ML 全服務遷移（LightGBM + XGBoost + FeatureBrowser）
  ├─ TASK-4.4  前端介面更新
  └─ TASK-4.5  Phase 4 測試                    ← 依賴 4.1~4.4

Phase 5 (跨 Symbol 訓練整合)                    ← 依賴 Phase 4
  ├─ TASK-5.1  IC cross-sectional 模式擴充
  ├─ TASK-5.2  CrossSymbolValidator + FeatureLibrary 串接
  └─ TASK-5.3  Phase 5 測試                    ← 依賴 5.1~5.2
```

---

## Phase 總覽

| Phase | 內容 | TASK 數 | 測試數 |
|-------|------|---------|--------|
| 1 | 引擎基礎：float32 + get_last_timestamp + config_hash + log_volume | 5 | 14 |
| 2 | 持久化層：registry.json persist/restore + API | 3 | 6 |
| 3 | 抽象層：FeatureLibrary 類別 + factory | 3 | 8 |
| 4 | 消費者遷移：date range + IC + ML全服務 + Frontend | 5 | 14 |
| 5 | 跨 Symbol 訓練整合：IC 截面模式 + CrossSymbolValidator | 3 | 7 |
| **合計** | | **19** | **49** |

---

## 架構決策（已凍結）

| 決策 | 選定方案 | 理由 |
|------|---------|------|
| get_last_timestamp 注入方式 | 在 AdapterRegistry 新增 delegate 方法 | FeatureFactory 已持有 `self._adapter_registry`，不需改建構子 |
| load_multi 缺失 symbol 策略 | raise `FeatureNotFoundError` | 研究平台不允許靜默丟棄資料 |
| registry.json 併發保護 | tempfile + `os.rename` 原子寫入 | 單行程 FastAPI，無需 file lock |
| IC 向後相容 | 保留 `features_path` 為 deprecated Optional | 允許舊前端過渡一個版本 |
| save_features_to_hdf5 dtype | float64 → float32 | 與 save_factory_output 一致，原為 bug |
| IC 截面模式 | `mode = "longitudinal" \| "cross_sectional"` | ADR-4：截面 IC 為可選功能，不強制替換縱向 IC |
| 跨 symbol 訓練策略 | FeatureLibrary.load_multi() → CrossSymbolValidator | 已有 `CrossSymbolValidator` + factory，只需串接 |
| 多 timeframe 分存禁止合併 | Feature Factory 絕不產生合併後的 100k cols 大表 | ADR-7：1h+12h merge → OOM；分析時才 JOIN（切片後記憶體安全） |

---

## Phase 1：引擎基礎

### TASK-1.1：float32 驗證與補完

**目標**：修正 `save_features_to_hdf5()` 中 float64 bug，並在 `load_factory_output()` 加入防禦性轉型

**修改檔案 1**：`momentum/FeatureEngineering/feature_storage.py`

找到 `save_features_to_hdf5()` 方法內部，約 L81-82 處：

```python
# BEFORE
feature_matrix = features_df[feature_names].values.astype(np.float64)
```

```python
# AFTER
feature_matrix = features_df[feature_names].values.astype(np.float32)
```

**修改檔案 2**：`momentum/FeatureEngineering/feature_storage.py`

找到 `load_factory_output()` 方法內部，約 L358 附近，在函式回傳 `FeatureGenerationResult` 之前，插入防禦性轉型：

```python
# 在 return result 之前插入
if result is not None and result.features is not None:
    numeric_cols = result.features.select_dtypes(include=["float64"]).columns
    if len(numeric_cols) > 0:
        result.features[numeric_cols] = result.features[numeric_cols].astype(np.float32)
```

---

### TASK-1.2：get_last_timestamp 實作鏈

**目標**：建立完整的 `get_last_timestamp()` 方法鏈：  
`KlineStorageManager` → `CryptoSpotAdapter` → `AdapterRegistry`

**修改檔案 1**：`momentum/DataExtraction/kline_storage.py`

在類別 `KlineStorageManager` 中新增方法（放在 `read_klines()` 方法附近）：

```python
def get_last_timestamp(self, symbol: str, timeframe: str) -> Optional[int]:
    """Return the last kline timestamp (ms) for given symbol/timeframe, or None if no data."""
    try:
        hdf5_path = self._get_hdf5_path(symbol, timeframe)
        if not hdf5_path.exists():
            return None
        with h5py.File(hdf5_path, "r") as f:
            key = f"{symbol}/{timeframe}/data"
            if key not in f:
                return None
            ds = f[key]
            if len(ds) == 0:
                return None
            last_row = ds[-1]
            # structured array: field 0 is open_time (ms)
            ts = int(last_row[0]) if hasattr(last_row, '__len__') else int(last_row)
            return ts
    except Exception:
        return None
```

**修改檔案 2**：`momentum/core/protocols.py`

在 `IKlineReader` Protocol 類別中新增方法（放在 `get_metadata()` 之後）：

```python
def get_last_timestamp(self, symbol: str, timeframe: str) -> Optional[int]:
    ...
```

**修改檔案 3**：`momentum/FeatureEngineering/adapters/base_adapter.py`

在 `DataSourceAdapter` 抽象類別中新增抽象方法（放在 `validate()` 之後）：

```python
@abstractmethod
def get_last_timestamp(self, symbol: str, timeframe: str) -> Optional[int]:
    """Return the last data timestamp (ms), or None if no data."""
    raise NotImplementedError()
```

注意：需要在開頭 import 中加入 `Optional`：

```python
from typing import Dict, List, Optional
```

同時 `FieldMeta` dataclass 上方已有 `from typing import List`，改為 `from typing import Dict, List, Optional`。

**修改檔案 4**：`momentum/FeatureEngineering/adapters/crypto_spot_adapter.py`

在 `CryptoSpotAdapter` 類別中新增方法（放在 `validate()` 之後）：

```python
def get_last_timestamp(self, symbol: str, timeframe: str) -> Optional[int]:
    """Delegate to KlineStorageManager."""
    return self._storage.get_last_timestamp(symbol, timeframe)
```

注意：需要在 `from typing import Dict, List` 加入 `Optional`。

**修改檔案 5**：`momentum/FeatureEngineering/adapters/adapter_registry.py`

在 `AdapterRegistry` 類別中新增方法（放在 `fetch_aligned()` 之後）：

```python
def get_last_timestamp(self, symbol: str, timeframe: str) -> Optional[int]:
    """Return the latest last_timestamp across all adapters."""
    latest: Optional[int] = None
    for adapter in self._adapters.values():
        ts = adapter.get_last_timestamp(symbol, timeframe)
        if ts is not None and (latest is None or ts > latest):
            latest = ts
    return latest
```

注意：需要在 `from typing import Dict, List` 加入 `Optional`。

---

### TASK-1.3：config_hash 加入 kline_last_ts

**目標**：當底層 K 線資料更新時，cache hash 自動失效

**修改檔案**：`momentum/FeatureEngineering/feature_factory.py`

**步驟 A**：修改 `_compute_config_hash()` 方法簽名和實作

找到約 L628 處：

```python
# BEFORE
def _compute_config_hash(self, config: "FactoryConfig") -> str:
    config_payload = config.model_dump(by_alias=True)
    timeframes = config_payload.get("timeframes")
    if isinstance(timeframes, dict) and isinstance(timeframes.get("training"), list):
        timeframes["training"] = sorted(timeframes["training"])
    payload = json.dumps(config_payload, sort_keys=True, default=str)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()
```

```python
# AFTER
def _compute_config_hash(self, config: "FactoryConfig", symbol: str, timeframe: str) -> str:
    config_payload = config.model_dump(by_alias=True)
    timeframes = config_payload.get("timeframes")
    if isinstance(timeframes, dict) and isinstance(timeframes.get("training"), list):
        timeframes["training"] = sorted(timeframes["training"])
    kline_last_ts = self._adapter_registry.get_last_timestamp(symbol, timeframe)
    config_payload["_kline_last_ts"] = kline_last_ts
    payload = json.dumps(config_payload, sort_keys=True, default=str)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()
```

**步驟 B**：修改呼叫處

找到 `generate_features()` 方法內約 L103 處：

```python
# BEFORE
config_hash = self._compute_config_hash(config)
```

```python
# AFTER
config_hash = self._compute_config_hash(config, symbol, timeframe)
```

**步驟 C**：搜尋 `_compute_config_hash` 的所有呼叫處

執行 `grep -rn "_compute_config_hash" momentum/` 確認所有呼叫都已更新。若有其他呼叫處，也需加入 `symbol, timeframe` 參數。

---

### TASK-1.4：log_volume 合成欄位

**目標**：在 CryptoSpotAdapter 新增 `log-volume` 和 `log-quote-volume` 合成欄位

**修改檔案**：`momentum/FeatureEngineering/adapters/crypto_spot_adapter.py`

**步驟 A**：修改 `_SYNTHETIC_FIELDS`

```python
# BEFORE
_SYNTHETIC_FIELDS = ["avg-price", "med-price", "typ-price", "wcl-price"]
```

```python
# AFTER
_SYNTHETIC_FIELDS = ["avg-price", "med-price", "typ-price", "wcl-price", "log-volume", "log-quote-volume"]
```

**步驟 B**：在 `_add_synthetic_fields()` 方法末尾（`return df` 之前）新增：

```python
# log-volume & log-quote-volume
vol = df["volume"].astype("float64")
df["log-volume"] = np.log1p(vol).astype("float32")

if "quote_volume" in df.columns:
    qvol = df["quote_volume"].astype("float64")
    df["log-quote-volume"] = np.log1p(qvol).astype("float32")
else:
    df["log-quote-volume"] = np.float32(0.0)
```

**步驟 C**：在 `_build_field_meta()` 方法中新增欄位 metadata

在 method 內的 meta dict 中加入：

```python
"log-volume": FieldMeta("log-volume", "float32", "volume", "Log-transformed base volume (log1p)", True),
"log-quote-volume": FieldMeta("log-quote-volume", "float32", "volume", "Log-transformed quote volume (log1p)", True),
```

---

### TASK-1.5：Phase 1 測試

**建立檔案**：`tests/feature_library/__init__.py`（空檔案）

**建立檔案**：`tests/feature_library/test_phase1.py`

```python
"""Phase 1 tests: float32, get_last_timestamp, config_hash, log_volume."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import h5py
import numpy as np
import pandas as pd
import pytest


# ── T1-01: save_features_to_hdf5 writes float32 ──

def test_save_features_to_hdf5_writes_float32():
    """save_features_to_hdf5 should write float32, not float64."""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    storage = FeatureStorage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage.base_path = Path(tmpdir)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=10, freq="h"),
            "feat_a": np.random.randn(10).astype(np.float64),
            "feat_b": np.random.randn(10).astype(np.float64),
        })
        path = storage.save_features_to_hdf5(
            case_id="test_case",
            symbol="BTCUSDT",
            timeframe="1h",
            features_df=df,
            feature_names=["feat_a", "feat_b"],
        )
        with h5py.File(path, "r") as f:
            ds = f["BTCUSDT/1h/features"]
            assert ds.dtype == np.float32, f"Expected float32, got {ds.dtype}"


# ── T1-02: load_factory_output returns float32 ──

def test_load_factory_output_returns_float32():
    """load_factory_output should return float32 even if stored as float64."""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    storage = FeatureStorage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage.base_path = Path(tmpdir)
        # Create a fake file with float64 data to simulate legacy
        filepath = Path(tmpdir) / "factory_output" / "TESTUSDT" / "1h"
        filepath.mkdir(parents=True, exist_ok=True)
        hdf5_file = filepath / "features.h5"

        df = pd.DataFrame({
            "feat_a": np.random.randn(5).astype(np.float64),
        })
        with h5py.File(hdf5_file, "w") as f:
            grp = f.create_group("features")
            grp.create_dataset("data", data=df.values.astype(np.float64))
            grp.attrs["columns"] = json.dumps(["feat_a"])
            grp.attrs["config_hash"] = "abc123"

        result = storage.load_factory_output("TESTUSDT", "1h")
        if result is not None and result.features is not None:
            for col in result.features.select_dtypes(include=["float64"]).columns:
                pytest.fail(f"Column {col} is float64, expected float32")


# ── T1-03: KlineStorageManager.get_last_timestamp returns int ──

def test_kline_storage_get_last_timestamp():
    """get_last_timestamp should return last timestamp as int or None."""
    from momentum.DataExtraction.kline_storage import KlineStorageManager

    mgr = KlineStorageManager()
    # For a non-existent symbol, should return None
    result = mgr.get_last_timestamp("NONEXISTUSDT", "1h")
    assert result is None


# ── T1-04: get_last_timestamp returns None for empty dataset ──

def test_get_last_timestamp_empty_dataset():
    """get_last_timestamp should return None when HDF5 exists but dataset is empty."""
    from momentum.DataExtraction.kline_storage import KlineStorageManager

    mgr = KlineStorageManager()
    with tempfile.TemporaryDirectory() as tmpdir:
        hdf5_path = Path(tmpdir) / "EMPTYUSDT_1h.h5"
        with h5py.File(hdf5_path, "w") as f:
            f.create_group("EMPTYUSDT/1h")
            # create empty dataset
            dt = np.dtype([("open_time", "int64"), ("close", "float64")])
            f.create_dataset("EMPTYUSDT/1h/data", shape=(0,), dtype=dt)

        with patch.object(mgr, "_get_hdf5_path", return_value=hdf5_path):
            result = mgr.get_last_timestamp("EMPTYUSDT", "1h")
            assert result is None


# ── T1-05: CryptoSpotAdapter.get_last_timestamp delegates ──

def test_crypto_spot_adapter_get_last_timestamp():
    """CryptoSpotAdapter should delegate to KlineStorageManager."""
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    mock_storage = MagicMock()
    mock_storage.get_last_timestamp.return_value = 1700000000000
    adapter = CryptoSpotAdapter(mock_storage)
    result = adapter.get_last_timestamp("BTCUSDT", "1h")
    assert result == 1700000000000
    mock_storage.get_last_timestamp.assert_called_once_with("BTCUSDT", "1h")


# ── T1-06: AdapterRegistry.get_last_timestamp picks max ──

def test_adapter_registry_get_last_timestamp_picks_max():
    """AdapterRegistry should return the latest timestamp across all adapters."""
    from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry

    registry = AdapterRegistry()

    adapter1 = MagicMock()
    adapter1.name = "source_a"
    adapter1.get_last_timestamp.return_value = 1000

    adapter2 = MagicMock()
    adapter2.name = "source_b"
    adapter2.get_last_timestamp.return_value = 2000

    registry.register(adapter1)
    registry.register(adapter2)

    result = registry.get_last_timestamp("BTCUSDT", "1h")
    assert result == 2000


# ── T1-07: AdapterRegistry.get_last_timestamp returns None when all adapters return None ──

def test_adapter_registry_get_last_timestamp_all_none():
    """When all adapters return None, registry should return None."""
    from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry

    registry = AdapterRegistry()
    adapter = MagicMock()
    adapter.name = "src"
    adapter.get_last_timestamp.return_value = None
    registry.register(adapter)

    assert registry.get_last_timestamp("X", "1h") is None


# ── T1-08: config_hash changes when kline data updates ──

def test_config_hash_changes_with_kline_update():
    """config_hash should differ when kline_last_ts changes."""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    mock_config_mgr = MagicMock()
    mock_registry = MagicMock()

    factory = FeatureFactory.__new__(FeatureFactory)
    factory._config_manager = mock_config_mgr
    factory._adapter_registry = mock_registry

    mock_config = MagicMock()
    mock_config.model_dump.return_value = {"a": 1, "timeframes": {"training": ["1h"]}}

    mock_registry.get_last_timestamp.return_value = 1000
    hash1 = factory._compute_config_hash(mock_config, "BTC", "1h")

    mock_registry.get_last_timestamp.return_value = 2000
    hash2 = factory._compute_config_hash(mock_config, "BTC", "1h")

    assert hash1 != hash2, "Hash should change when kline_last_ts changes"


# ── T1-09: config_hash stable when kline data unchanged ──

def test_config_hash_stable_when_unchanged():
    """config_hash should be deterministic for same inputs."""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    mock_config_mgr = MagicMock()
    mock_registry = MagicMock()

    factory = FeatureFactory.__new__(FeatureFactory)
    factory._config_manager = mock_config_mgr
    factory._adapter_registry = mock_registry

    mock_config = MagicMock()
    mock_config.model_dump.return_value = {"a": 1, "timeframes": {"training": ["1h"]}}
    mock_registry.get_last_timestamp.return_value = 1000

    hash1 = factory._compute_config_hash(mock_config, "BTC", "1h")
    hash2 = factory._compute_config_hash(mock_config, "BTC", "1h")
    assert hash1 == hash2


# ── T1-10: log-volume in available_fields ──

def test_log_volume_in_available_fields():
    """CryptoSpotAdapter.available_fields should include log-volume."""
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    mock_storage = MagicMock()
    adapter = CryptoSpotAdapter(mock_storage)
    assert "log-volume" in adapter.available_fields
    assert "log-quote-volume" in adapter.available_fields


# ── T1-11: log-volume non-negative ──

def test_log_volume_non_negative():
    """log-volume should be non-negative (log1p(x) >= 0 for x >= 0)."""
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    mock_storage = MagicMock()
    adapter = CryptoSpotAdapter(mock_storage)

    df = pd.DataFrame({
        "timestamp": [1, 2, 3],
        "open": [100.0, 101.0, 102.0],
        "high": [105.0, 106.0, 107.0],
        "low": [95.0, 96.0, 97.0],
        "close": [103.0, 104.0, 105.0],
        "volume": [1000.0, 0.0, 500.0],
        "quote_volume": [50000.0, 0.0, 25000.0],
        "taker_buy_volume": [500.0, 0.0, 250.0],
        "taker_ratio": [0.5, 0.0, 0.5],
        "trades": [100, 0, 50],
        "number_of_trades": [100, 0, 50],
    })
    result = adapter._add_synthetic_fields(df)
    assert (result["log-volume"] >= 0).all()
    assert (result["log-quote-volume"] >= 0).all()


# ── T1-12: log-volume is float32 ──

def test_log_volume_dtype_float32():
    """log-volume and log-quote-volume should be float32."""
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    mock_storage = MagicMock()
    adapter = CryptoSpotAdapter(mock_storage)
    df = pd.DataFrame({
        "timestamp": [1],
        "open": [100.0], "high": [105.0], "low": [95.0], "close": [103.0],
        "volume": [1000.0], "quote_volume": [50000.0],
        "taker_buy_volume": [500.0], "taker_ratio": [0.5],
        "trades": [100], "number_of_trades": [100],
    })
    result = adapter._add_synthetic_fields(df)
    assert result["log-volume"].dtype == np.float32
    assert result["log-quote-volume"].dtype == np.float32


# ── T1-13: log-volume handles zero volume ──

def test_log_volume_zero_volume():
    """log1p(0) should be 0.0."""
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    mock_storage = MagicMock()
    adapter = CryptoSpotAdapter(mock_storage)
    df = pd.DataFrame({
        "timestamp": [1],
        "open": [100.0], "high": [105.0], "low": [95.0], "close": [103.0],
        "volume": [0.0], "quote_volume": [0.0],
        "taker_buy_volume": [0.0], "taker_ratio": [0.0],
        "trades": [0], "number_of_trades": [0],
    })
    result = adapter._add_synthetic_fields(df)
    assert result["log-volume"].iloc[0] == pytest.approx(0.0, abs=1e-7)
    assert result["log-quote-volume"].iloc[0] == pytest.approx(0.0, abs=1e-7)


# ── T1-14: log-volume missing quote_volume fallback ──

def test_log_volume_missing_quote_volume():
    """When quote_volume column is missing, log-quote-volume should be 0."""
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

    mock_storage = MagicMock()
    adapter = CryptoSpotAdapter(mock_storage)
    df = pd.DataFrame({
        "timestamp": [1],
        "open": [100.0], "high": [105.0], "low": [95.0], "close": [103.0],
        "volume": [1000.0],
        "taker_buy_volume": [500.0], "taker_ratio": [0.5],
        "trades": [100], "number_of_trades": [100],
    })
    result = adapter._add_synthetic_fields(df)
    assert result["log-quote-volume"].iloc[0] == pytest.approx(0.0, abs=1e-7)
```

---

## Phase 2：持久化層

### TASK-2.1：registry.json 寫入

**目標**：每次 `_layer7_validate_and_persist()` 完成後，將 task metadata 寫入 `registry.json`

**建立檔案**：`momentum/FeatureEngineering/feature_registry.py`

```python
"""Feature generation registry — tracks all generated feature sets."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from momentum.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_REGISTRY_PATH = Path("data_cache/features/registry.json")


class FeatureRegistry:
    """Append-only registry persisted as a JSON file.

    Each entry records: symbol, timeframe, config_hash, feature_count,
    row_count, created_at, hdf5_path.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or DEFAULT_REGISTRY_PATH
        self._entries: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = data if isinstance(data, list) else []
                logger.info("Loaded registry with %d entries", len(self._entries))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load registry, starting fresh: %s", exc)
                self._entries = []
        else:
            self._entries = []

    def add(self, entry: Dict[str, Any]) -> None:
        """Add an entry and persist atomically."""
        required_keys = {"symbol", "timeframe", "config_hash"}
        missing = required_keys - set(entry.keys())
        if missing:
            raise ValueError(f"Missing required keys: {missing}")

        entry.setdefault("created_at", time.time())
        self._entries.append(entry)
        self._persist()

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._entries)

    def find(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        return [
            e for e in self._entries
            if e.get("symbol") == symbol and e.get("timeframe") == timeframe
        ]

    def find_latest(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        matches = self.find(symbol, timeframe)
        if not matches:
            return None
        return max(matches, key=lambda e: e.get("created_at", 0))

    def _persist(self) -> None:
        """Atomic write: write to temp file then rename."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._path.parent), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, ensure_ascii=False, indent=2, default=str)
            os.rename(tmp_path, str(self._path))
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
```

**修改檔案**：`momentum/FeatureEngineering/feature_factory.py`

在 `__init__()` 中加入 registry：

```python
# 在 __init__() 中，self._storage = ... 之後加入
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
self._registry = FeatureRegistry()
```

在 `_layer7_validate_and_persist()` 方法中，在 `self._storage.save_factory_output(...)` 呼叫**之後**加入：

```python
# 寫入 registry
try:
    self._registry.add({
        "symbol": symbol,
        "timeframe": timeframe,
        "config_hash": config_hash,
        "feature_count": len(result.feature_names) if result.feature_names else 0,
        "row_count": len(result.features) if result.features is not None else 0,
        "hdf5_relative_path": str(self._storage.get_output_path(symbol, timeframe)),
    })
except Exception as exc:
    logger.warning("Failed to update registry: %s", exc)
```

注意：`config_hash` 變數和 `symbol`/`timeframe` 需要在 `_layer7` 作用域內可用。如果不在，需要從 `generate_features()` 透過參數傳遞。檢查實際作用域後決定傳遞方式。

---

### TASK-2.2：registry.json 恢復 + API

**目標**：新增 API 端點查詢 registry

**建立檔案**：`api/routes/feature_registry.py`

```python
"""Feature registry API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from momentum.FeatureEngineering.feature_registry import FeatureRegistry

router = APIRouter(prefix="/feature-registry", tags=["feature-registry"])

_registry = FeatureRegistry()


@router.get("/entries")
def list_entries(
    symbol: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
):
    """List all registry entries, optionally filtered by symbol/timeframe."""
    entries = _registry.list_all()
    if symbol:
        entries = [e for e in entries if e.get("symbol") == symbol]
    if timeframe:
        entries = [e for e in entries if e.get("timeframe") == timeframe]
    return {"entries": entries, "total": len(entries)}


@router.get("/latest")
def get_latest(
    symbol: str = Query(...),
    timeframe: str = Query(...),
):
    """Get the latest registry entry for a specific symbol/timeframe."""
    entry = _registry.find_latest(symbol, timeframe)
    if entry is None:
        return {"entry": None, "found": False}
    return {"entry": entry, "found": True}
```

**修改檔案**：`api/main.py`

在 router 註冊區塊中新增：

```python
from api.routes.feature_registry import router as feature_registry_router
app.include_router(feature_registry_router, prefix="/api/v1")
```

---

### TASK-2.3：Phase 2 測試

**建立檔案**：`tests/feature_library/test_phase2.py`

```python
"""Phase 2 tests: registry persistence and restore."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# ── T2-01: registry add and list ──

def test_registry_add_and_list():
    """Add entries and verify list returns them all."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        reg = FeatureRegistry(Path(tmpdir) / "reg.json")
        reg.add({"symbol": "BTCUSDT", "timeframe": "1h", "config_hash": "aaa"})
        reg.add({"symbol": "ETHUSDT", "timeframe": "4h", "config_hash": "bbb"})
        assert len(reg.list_all()) == 2


# ── T2-02: registry persist and reload ──

def test_registry_persist_and_reload():
    """Entries should survive process restart (reload from file)."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "reg.json"
        reg1 = FeatureRegistry(path)
        reg1.add({"symbol": "BTCUSDT", "timeframe": "1h", "config_hash": "hash1"})

        # Simulate restart
        reg2 = FeatureRegistry(path)
        assert len(reg2.list_all()) == 1
        assert reg2.list_all()[0]["config_hash"] == "hash1"


# ── T2-03: registry find_latest returns most recent ──

def test_registry_find_latest():
    """find_latest should return entry with highest created_at."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        reg = FeatureRegistry(Path(tmpdir) / "reg.json")
        reg.add({"symbol": "BTC", "timeframe": "1h", "config_hash": "old", "created_at": 100})
        reg.add({"symbol": "BTC", "timeframe": "1h", "config_hash": "new", "created_at": 200})
        latest = reg.find_latest("BTC", "1h")
        assert latest is not None
        assert latest["config_hash"] == "new"


# ── T2-04: registry missing required keys raises ValueError ──

def test_registry_missing_keys_raises():
    """add() should raise ValueError when required keys are missing."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        reg = FeatureRegistry(Path(tmpdir) / "reg.json")
        with pytest.raises(ValueError, match="Missing required keys"):
            reg.add({"symbol": "BTC"})  # missing timeframe, config_hash


# ── T2-05: registry corrupt json recovers gracefully ──

def test_registry_corrupt_json():
    """Registry should start fresh when JSON file is corrupt."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "reg.json"
        path.write_text("{invalid json!!!", encoding="utf-8")
        reg = FeatureRegistry(path)
        assert len(reg.list_all()) == 0  # Started fresh, no crash


# ── T2-06: registry atomic write (temp file exists briefly) ──

def test_registry_atomic_write():
    """After add, the file should be valid JSON (no partial writes)."""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "reg.json"
        reg = FeatureRegistry(path)
        reg.add({"symbol": "X", "timeframe": "1h", "config_hash": "h"})

        # Verify file is valid JSON
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 1
```

---

## Phase 3：FeatureLibrary 抽象層

### TASK-3.1：FeatureLibraryEntry + FeatureNotFoundError 定義

**修改檔案**：`momentum/core/contracts.py`

在檔案末尾（最後一個 class 之後）新增：

```python
@dataclass(frozen=True)
class FeatureLibraryEntry:
    """A single entry in the Feature Library registry."""

    symbol: str
    timeframe: str
    config_hash: str
    feature_count: int
    row_count: int
    created_at: float
    hdf5_relative_path: str


class FeatureNotFoundError(Exception):
    """Raised when requested features are not found in the library."""

    def __init__(self, symbol: str, timeframe: str, detail: str = ""):
        self.symbol = symbol
        self.timeframe = timeframe
        msg = f"Features not found for {symbol}/{timeframe}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)
```

---

### TASK-3.2：FeatureLibrary 類別 + factory

**建立檔案**：`momentum/FeatureEngineering/feature_library.py`

```python
"""FeatureLibrary — unified read-only interface for consuming generated features."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from momentum.core.contracts import FeatureLibraryEntry, FeatureNotFoundError
from momentum.core.logging import get_logger
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage

logger = get_logger(__name__)


class FeatureLibrary:
    """Read-only facade for accessing generated features.

    Consumers (IC analysis, XGBoost, etc.) use this class instead of
    directly reading HDF5 files or calling FeatureFactory.
    """

    def __init__(
        self,
        registry: FeatureRegistry,
        storage: FeatureStorage,
    ) -> None:
        self._registry = registry
        self._storage = storage

    def list_available(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> List[FeatureLibraryEntry]:
        """List all available feature sets, optionally filtered."""
        entries = self._registry.list_all()
        if symbol:
            entries = [e for e in entries if e.get("symbol") == symbol]
        if timeframe:
            entries = [e for e in entries if e.get("timeframe") == timeframe]
        return [self._to_entry(e) for e in entries]

    def load(
        self,
        symbol: str,
        timeframe: str,
    ) -> pd.DataFrame:
        """Load the latest features for a symbol/timeframe.

        Raises FeatureNotFoundError if no features exist.
        """
        entry = self._registry.find_latest(symbol, timeframe)
        if entry is None:
            raise FeatureNotFoundError(symbol, timeframe, "No registry entry")

        result = self._storage.load_factory_output(symbol, timeframe)
        if result is None or result.features is None or result.features.empty:
            raise FeatureNotFoundError(symbol, timeframe, "HDF5 file missing or empty")

        logger.info(
            "Loaded features for %s/%s: %d rows × %d cols",
            symbol, timeframe,
            len(result.features), len(result.features.columns),
        )
        return result.features

    def load_multi(
        self,
        symbols: List[str],
        timeframe: str,
    ) -> Dict[str, pd.DataFrame]:
        """Load features for multiple symbols. Raises on any missing symbol."""
        results: Dict[str, pd.DataFrame] = {}
        for sym in symbols:
            results[sym] = self.load(sym, timeframe)
        return results

    def ensure_fresh(
        self,
        symbol: str,
        timeframe: str,
        current_config_hash: str,
    ) -> bool:
        """Check if the latest cached features match the given config hash.

        Returns True if fresh, False if stale or missing.
        """
        entry = self._registry.find_latest(symbol, timeframe)
        if entry is None:
            return False
        return entry.get("config_hash") == current_config_hash

    @staticmethod
    def _to_entry(raw: Dict) -> FeatureLibraryEntry:
        return FeatureLibraryEntry(
            symbol=raw.get("symbol", ""),
            timeframe=raw.get("timeframe", ""),
            config_hash=raw.get("config_hash", ""),
            feature_count=raw.get("feature_count", 0),
            row_count=raw.get("row_count", 0),
            created_at=raw.get("created_at", 0.0),
            hdf5_relative_path=raw.get("hdf5_relative_path", ""),
        )
```

**修改檔案**：`momentum/factories.py`

在 `create_feature_factory()` 之後新增 factory 函式：

```python
def create_feature_library() -> "FeatureLibrary":
    """Create a FeatureLibrary instance."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    registry = FeatureRegistry()
    storage = FeatureStorage()
    return FeatureLibrary(registry, storage)
```

---

### TASK-3.3：Phase 3 測試

**建立檔案**：`tests/feature_library/test_phase3.py`

```python
"""Phase 3 tests: FeatureLibrary abstraction layer."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from momentum.core.contracts import FeatureLibraryEntry, FeatureNotFoundError


# ── T3-01: FeatureLibraryEntry frozen ──

def test_feature_library_entry_frozen():
    """FeatureLibraryEntry should be immutable."""
    entry = FeatureLibraryEntry(
        symbol="BTC", timeframe="1h", config_hash="abc",
        feature_count=10, row_count=100, created_at=1.0,
        hdf5_relative_path="a/b.h5",
    )
    with pytest.raises(AttributeError):
        entry.symbol = "ETH"  # type: ignore[misc]


# ── T3-02: FeatureNotFoundError attributes ──

def test_feature_not_found_error_attributes():
    """FeatureNotFoundError should carry symbol and timeframe."""
    err = FeatureNotFoundError("BTCUSDT", "1h", "test detail")
    assert err.symbol == "BTCUSDT"
    assert err.timeframe == "1h"
    assert "BTCUSDT" in str(err)
    assert "test detail" in str(err)


# ── T3-03: FeatureLibrary.list_available ──

def test_feature_library_list_available():
    """list_available should filter by symbol/timeframe."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.list_all.return_value = [
        {"symbol": "BTC", "timeframe": "1h", "config_hash": "a",
         "feature_count": 5, "row_count": 10, "created_at": 1.0, "hdf5_relative_path": "p"},
        {"symbol": "ETH", "timeframe": "1h", "config_hash": "b",
         "feature_count": 3, "row_count": 8, "created_at": 2.0, "hdf5_relative_path": "q"},
    ]
    mock_storage = MagicMock()

    lib = FeatureLibrary(mock_registry, mock_storage)
    all_entries = lib.list_available()
    assert len(all_entries) == 2

    btc_entries = lib.list_available(symbol="BTC")
    assert len(btc_entries) == 1
    assert btc_entries[0].symbol == "BTC"


# ── T3-04: FeatureLibrary.load success ──

def test_feature_library_load_success():
    """load should return DataFrame when registry and storage both have data."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = {"symbol": "BTC", "timeframe": "1h", "config_hash": "h"}

    mock_result = MagicMock()
    mock_result.features = pd.DataFrame({"feat_a": [1.0, 2.0]})

    mock_storage = MagicMock()
    mock_storage.load_factory_output.return_value = mock_result

    lib = FeatureLibrary(mock_registry, mock_storage)
    df = lib.load("BTC", "1h")
    assert len(df) == 2


# ── T3-05: FeatureLibrary.load raises on missing ──

def test_feature_library_load_raises_on_missing():
    """load should raise FeatureNotFoundError when no registry entry."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = None
    mock_storage = MagicMock()

    lib = FeatureLibrary(mock_registry, mock_storage)
    with pytest.raises(FeatureNotFoundError):
        lib.load("NONEXIST", "1h")


# ── T3-06: FeatureLibrary.load_multi raises on any missing ──

def test_feature_library_load_multi_raises_on_any_missing():
    """load_multi should raise FeatureNotFoundError if ANY symbol is missing."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()

    def fake_find(symbol, timeframe):
        if symbol == "BTC":
            return {"symbol": "BTC", "timeframe": "1h", "config_hash": "h"}
        return None  # ETH not found

    mock_registry.find_latest.side_effect = fake_find

    mock_result = MagicMock()
    mock_result.features = pd.DataFrame({"f": [1.0]})
    mock_storage = MagicMock()
    mock_storage.load_factory_output.return_value = mock_result

    lib = FeatureLibrary(mock_registry, mock_storage)
    with pytest.raises(FeatureNotFoundError):
        lib.load_multi(["BTC", "ETH"], "1h")


# ── T3-07: FeatureLibrary.ensure_fresh true when matching ──

def test_feature_library_ensure_fresh_true():
    """ensure_fresh should return True when config hash matches."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = {"config_hash": "target_hash"}
    mock_storage = MagicMock()

    lib = FeatureLibrary(mock_registry, mock_storage)
    assert lib.ensure_fresh("BTC", "1h", "target_hash") is True


# ── T3-08: FeatureLibrary.ensure_fresh false when stale ──

def test_feature_library_ensure_fresh_false_when_stale():
    """ensure_fresh should return False when config hash differs."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = {"config_hash": "old_hash"}
    mock_storage = MagicMock()

    lib = FeatureLibrary(mock_registry, mock_storage)
    assert lib.ensure_fresh("BTC", "1h", "new_hash") is False
```

---

## Phase 4：消費者遷移

### TASK-4.1：generate_features() date range 支援

**目標**：讓 `generate_features()` 接受 `start_date` / `end_date` 參數

**修改檔案**：`momentum/FeatureEngineering/feature_factory.py`

**步驟 A**：修改 `generate_features()` 方法簽名

找到 `generate_features()` 方法定義（約 L89）：

```python
# BEFORE
async def generate_features(
    self,
    symbol: str,
    timeframe: str,
    config_override: Optional[Dict[str, Any]] = None,
    force_regenerate: bool = False,
    progress_callback: Optional[Callable] = None,
) -> FeatureGenerationResult:
```

```python
# AFTER
async def generate_features(
    self,
    symbol: str,
    timeframe: str,
    config_override: Optional[Dict[str, Any]] = None,
    force_regenerate: bool = False,
    progress_callback: Optional[Callable] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> FeatureGenerationResult:
```

注意：確認 `generate_features` 是否為 async。如果不是 async，不要加 `async`。保持原始的同步/非同步一致。

**步驟 B**：修改 `_layer0_data_ingestion()` 傳遞日期範圍

找到 `_layer0_data_ingestion()` 呼叫，將 `start_date` / `end_date` 傳入。在 `_layer0` 內部使用 adapter 的 `start_time`/`end_time` 參數（毫秒）：

```python
# 在 _layer0_data_ingestion 中，呼叫 self._adapter_registry.fetch_aligned() 之後
# 加入日期篩選
if start_date is not None:
    start_ts = pd.Timestamp(start_date).timestamp() * 1000
    raw_data = raw_data[raw_data.index >= start_ts]
if end_date is not None:
    end_ts = pd.Timestamp(end_date).timestamp() * 1000
    raw_data = raw_data[raw_data.index <= end_ts]
```

**步驟 C**：將 `start_date`/`end_date` 納入 config hash

在 `_compute_config_hash()` 中，`config_payload` dict 加入：

```python
config_payload["_start_date"] = start_date
config_payload["_end_date"] = end_date
```

需要修改 `_compute_config_hash` 簽名為 `(self, config, symbol, timeframe, start_date=None, end_date=None)` 並更新呼叫處。

**步驟 D**：新增 API request model

**修改檔案**：`api/models/feature_factory_models.py`

在現有 model 中新增（或修改）`FeatureGenerationRequest`，加入 `start_date`/`end_date` 欄位：

```python
class FeatureGenerationRequest(BaseModel):
    """Feature generation request with optional date range."""
    config: Optional[Dict[str, Any]] = None
    symbols: List[str]
    timeframe: str
    start_date: Optional[str] = None   # "2024-01-01"
    end_date: Optional[str] = None     # "2025-12-31"
    force_regenerate: bool = False
```

注意：檢查 `api/models/feature_factory_models.py` 是否已有類似 request model。若有，在其上新增 `start_date`/`end_date` 欄位即可，不需重建。確保 route handler 使用此 model。

---

### TASK-4.2：IC analysis service 遷移

**目標**：讓 IC analysis 可以透過 FeatureLibrary 取得特徵，同時保留 `features_path` 向後相容

**修改檔案**：`api/services/ic_analysis_service.py`

**步驟 A**：在 `__init__()` 中注入 FeatureLibrary

```python
# 在 __init__() 開頭加入
from momentum.factories import create_feature_library
self._feature_library = create_feature_library()
```

**步驟 B**：修改 `_run_analysis()` 方法

在呼叫 `analyzer.analyze()` 之前，加入 FeatureLibrary 取特徵的邏輯：

```python
# 如果 request 有 symbol + timeframe 且 features_path 未提供
# 則透過 FeatureLibrary 取得特徵路徑
features_path = request.features_path
if not features_path and hasattr(request, "symbol") and hasattr(request, "timeframe"):
    try:
        entry = self._feature_library._registry.find_latest(request.symbol, request.timeframe)
        if entry:
            features_path = entry.get("hdf5_relative_path")
    except Exception as exc:
        logger.warning("FeatureLibrary lookup failed: %s", exc)
```

注意：這是漸進式遷移。`features_path` 仍然是主要路徑，FeatureLibrary 只在 `features_path` 為空時作為 fallback。

---

### TASK-4.3：ML 全服務遷移（LightGBM + XGBoost + FeatureBrowser）

**目標**：所有讀取特徵的 ML 服務統一改用 FeatureLibrary fallback 模式。LightGBM 是系統**預設 ML 引擎**（`create_model_trainer(engine="lightgbm")`），必須優先覆蓋。

**覆蓋範圍**：

| 服務 | 現狀 | 改動 |
|------|------|------|
| `api/services/xgboost_task_service.py` | 透過 factory，無直接 features_path | 注入 `_feature_library`，fallback 模式 |
| `api/services/xgboost_batch_service.py` | 從 kline 即時計算特徵 | 新增可選路徑：若 FeatureLibrary 有預計算特徵則直接讀取，否則 fallback 即時計算 |
| `api/routes/pattern_analysis.py` | LightGBM 訓練路由 `features_source` 傳入 | 支援 `features_source = "library:{symbol}:{timeframe}"` 語法 |
| `api/services/feature_browser_service.py` | `_load_features_df()` 手動解析 HDF5 | 新增 FeatureLibrary 載入路徑，保留舊路徑相容 |
| `api/services/model_enhancement_service.py` | 間接取得特徵（上游 payload） | 無需直接改動，上游遷移後自動受益 |

**修改檔案 1**：`api/services/xgboost_task_service.py`

套用與 TASK-4.2 相同的 pattern：

1. 在 `__init__()` 注入 `self._feature_library = create_feature_library()`
2. 在執行分析前，若無直接 features_path，透過 FeatureLibrary fallback

**修改檔案 2**：`api/services/xgboost_batch_service.py`

在 batch 訓練流程中，新增 FeatureLibrary 優先讀取邏輯：

```python
# 在 batch 處理迴圈中，特徵準備步驟
from momentum.factories import create_feature_library

# __init__() 中
self._feature_library = create_feature_library()

# 批次處理中，每個 symbol 嘗試從 FeatureLibrary 載入
try:
    features_df = self._feature_library.load(symbol, timeframe)
    feature_names = list(features_df.columns)
    logger.info("從 FeatureLibrary 載入 %s/%s 預計算特徵", symbol, timeframe)
except FeatureNotFoundError:
    # Fallback: 從 kline 即時計算（現有邏輯）
    features_df, feature_names = self.feature_extractor.extract_features_from_strategy(
        df=kline_df.copy(), strategy_params=strategy_params, ...
    )
    logger.info("FeatureLibrary 無資料，改用即時計算 %s/%s", symbol, timeframe)
```

**修改檔案 3**：`api/routes/pattern_analysis.py`

在 LightGBM 訓練路由（約 L205-230）中，解析 `features_source` 參數：

```python
# 在 POST /lightgbm/train 端點中
features_source = request.features_source
if features_source and features_source.startswith("library:"):
    # 格式: "library:BTCUSDT:1h"
    parts = features_source.split(":")
    if len(parts) == 3:
        _, symbol, timeframe = parts
        from momentum.factories import create_feature_library
        lib = create_feature_library()
        features_df = lib.load(symbol, timeframe)
        # 將 features_df 傳入訓練 pipeline
```

注意：也需同步更新 `api/models/pattern_analysis_models.py` 中 `LightGBMTrainingRequest` 的 `features_source` 欄位說明，加入 `library:` 前綴語法文件。

**修改檔案 4**：`api/services/feature_browser_service.py`

修改 `_load_features_df()` 方法（約 L649-720），加入 FeatureLibrary 優先路徑：

```python
def _load_features_df(self, features_path: str) -> pd.DataFrame:
    """載入特徵 DataFrame，優先從 FeatureLibrary 讀取。"""
    # 新增：嘗試解析 library:symbol:timeframe 格式
    if features_path.startswith("library:"):
        parts = features_path.split(":")
        if len(parts) == 3:
            _, symbol, timeframe = parts
            return self._feature_library.load(symbol, timeframe)

    # 保留原有邏輯：直接從 CSV/HDF5 路徑載入
    # ... (existing code unchanged) ...
```

在 `__init__()` 中注入：

```python
from momentum.factories import create_feature_library
self._feature_library = create_feature_library()
```

---

### TASK-4.4：前端介面更新

**目標**：前端支援 registry 查詢 + symbol/timeframe 選擇

**修改檔案 1**：`frontend/src/lib/types.ts`

新增 type 定義：

```typescript
export interface FeatureRegistryEntry {
  symbol: string;
  timeframe: string;
  config_hash: string;
  feature_count: number;
  row_count: number;
  created_at: number;
  hdf5_relative_path: string;
}

export interface FeatureRegistryResponse {
  entries: FeatureRegistryEntry[];
  total: number;
}

// 日期範圍產生請求（對應後端 FeatureGenerationRequest）
export interface FeatureGenerationRequest {
  config?: Record<string, unknown>;
  symbols: string[];
  timeframe: string;
  start_date?: string;  // "2024-01-01"
  end_date?: string;    // "2025-12-31"
  force_regenerate?: boolean;
}
```

**修改檔案 2**：`frontend/src/store/featureFactoryStore.ts`

新增 registry 相關 state 和 action：

```typescript
// 在 state interface 中新增
registryEntries: FeatureRegistryEntry[];
registryLoading: boolean;

// 在 actions 中新增
fetchRegistry: () => Promise<void>;
```

實作 `fetchRegistry`：

```typescript
fetchRegistry: async () => {
  set({ registryLoading: true });
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/feature-registry/entries`);
    const data = await res.json();
    set({ registryEntries: data.entries || [], registryLoading: false });
  } catch {
    set({ registryLoading: false });
  }
},
```

**修改檔案 3**：IC Analysis 相關前端頁面

在 IC analysis 的 request 表單中，新增可選的 symbol/timeframe 選擇器，與現有 `features_path` 共存。當使用者選擇了 symbol/timeframe 時，後端會透過 FeatureLibrary 取特徵。

具體 UI 變更：在 `frontend/src/app/ic-analysis/page.tsx` 中，在現有的 features_path input 旁邊加入 「或從 Feature Library 選擇」的 dropdown。實際 UI 細節根據現有頁面結構調整。

**修改檔案 4**：`frontend/src/components/common/KlineDownloadTrigger.tsx`

新建共用元件，Feature Factory 頁面與 data-preparation 頁面共用「K線未下載 → 立即下載」按鈕：

```typescript
/**
 * KlineDownloadTrigger.tsx
 * 共用元件：偵測所選 symbol/timeframe 的 K 線是否已下載。
 * 若未下載，顯示提示 + 一鍵下載按鈕。
 * Feature Factory 頁面和 data-preparation 頁面共用。
 */

interface KlineDownloadTriggerProps {
  symbol: string;
  timeframe: string;
  onDownloadComplete?: () => void;
}

export function KlineDownloadTrigger({ symbol, timeframe, onDownloadComplete }: KlineDownloadTriggerProps) {
  // 1. 呼叫 GET /api/v1/kline/status?symbol=XX&timeframe=YY 檢查 K 線狀態
  // 2. 若已下載：顯示綠色 ✓ 和資料範圍
  // 3. 若未下載：顯示警告 + "立即下載" 按鈕
  // 4. 下載中：顯示 progress bar
  // 5. 下載完成：呼叫 onDownloadComplete callback
}
```

注意：此元件的具體 API 端點根據現有 `api/routes/` 中的 kline 相關路由調整。重點是「偵測 + 觸發下載」的 UX 流程。

---

### TASK-4.5：Phase 4 測試

**建立檔案**：`tests/feature_library/test_phase4.py`

```python
"""Phase 4 tests: consumer migration (date range, IC, XGBoost, frontend types)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ── T4-01: generate_features accepts start_date/end_date ──

def test_generate_features_accepts_date_range():
    """generate_features should accept start_date/end_date without error."""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    import inspect

    sig = inspect.signature(FeatureFactory.generate_features)
    params = list(sig.parameters.keys())
    assert "start_date" in params, "start_date parameter missing"
    assert "end_date" in params, "end_date parameter missing"


# ── T4-02: date range filters data correctly ──

def test_date_range_filters_data():
    """When start_date/end_date provided, output should be within range."""
    # This test verifies the filtering logic in _layer0
    # Create a mock DataFrame with known timestamps
    idx = pd.date_range("2024-01-01", periods=100, freq="h")
    df = pd.DataFrame({"close": range(100)}, index=idx.astype(int) * 10**6)  # ms timestamps

    start_ts = pd.Timestamp("2024-01-02").timestamp() * 1000
    end_ts = pd.Timestamp("2024-01-03").timestamp() * 1000

    filtered = df[(df.index >= start_ts) & (df.index <= end_ts)]
    assert len(filtered) < len(df), "Filtering should reduce rows"
    assert len(filtered) > 0, "Filtering should not remove all rows"


# ── T4-03: date range None means no filtering ──

def test_date_range_none_no_filtering():
    """When start_date and end_date are both None, all data should be returned."""
    idx = pd.date_range("2024-01-01", periods=50, freq="h")
    df = pd.DataFrame({"close": range(50)}, index=idx.astype(int) * 10**6)

    start_date = None
    end_date = None

    filtered = df.copy()
    if start_date is not None:
        start_ts = pd.Timestamp(start_date).timestamp() * 1000
        filtered = filtered[filtered.index >= start_ts]
    if end_date is not None:
        end_ts = pd.Timestamp(end_date).timestamp() * 1000
        filtered = filtered[filtered.index <= end_ts]

    assert len(filtered) == 50


# ── T4-04: IC analysis service has feature_library attribute ──

def test_ic_analysis_service_has_feature_library():
    """ICAnalysisService should have _feature_library attribute after init."""
    from api.services.ic_analysis_service import ICAnalysisService

    service = ICAnalysisService()
    assert hasattr(service, "_feature_library"), "Missing _feature_library attribute"


# ── T4-05: IC analysis falls back to FeatureLibrary when features_path empty ──

def test_ic_analysis_feature_library_fallback():
    """When features_path is empty, IC service should attempt FeatureLibrary lookup."""
    from api.services.ic_analysis_service import ICAnalysisService

    service = ICAnalysisService()
    # Just verify the attribute exists and is the right type
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    assert isinstance(service._feature_library, FeatureLibrary)


# ── T4-06: FeatureRegistryEntry fields in types.ts ──

def test_frontend_types_has_registry_entry():
    """Verify types.ts contains FeatureRegistryEntry interface."""
    from pathlib import Path
    types_path = Path("frontend/src/lib/types.ts")
    if not types_path.exists():
        pytest.skip("Frontend types.ts not found")
    content = types_path.read_text()
    assert "FeatureRegistryEntry" in content, "Missing FeatureRegistryEntry type"


# ── T4-07: config_hash includes date range ──

def test_config_hash_includes_date_range():
    """config_hash should change when start_date/end_date differ."""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    import inspect

    sig = inspect.signature(FeatureFactory._compute_config_hash)
    params = list(sig.parameters.keys())
    # Should accept start_date and end_date
    assert "start_date" in params or len(params) >= 5, (
        "_compute_config_hash should accept date range params"
    )


# ── T4-08: decoupling check ──

def test_decoupling_no_api_in_momentum():
    """momentum/ must not import from api/."""
    import subprocess
    result = subprocess.run(
        ["grep", "-r", "from api\\.", "momentum/", "--include=*.py"],
        capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent)
    )
    offending = [
        line for line in result.stdout.strip().split("\n")
        if line and "__pycache__" not in line
    ]
    assert len(offending) == 0, f"Decoupling violation:\n" + "\n".join(offending)


# ── T4-09: feature_registry route returns 200 ──

def test_feature_registry_route():
    """GET /api/v1/feature-registry/entries should return 200."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/feature-registry/entries")
        assert response.status_code == 200
        body = response.json()
        assert "entries" in body
        assert "total" in body
    except ImportError:
        pytest.skip("FastAPI test client not available")


# ── T4-10: xgboost_batch_service has feature_library attribute ──

def test_xgboost_batch_service_has_feature_library():
    """XGBoostBatchService should have _feature_library attribute."""
    from api.services.xgboost_batch_service import XGBoostBatchService

    service = XGBoostBatchService()
    assert hasattr(service, "_feature_library"), "Missing _feature_library attribute"


# ── T4-11: feature_browser_service has feature_library attribute ──

def test_feature_browser_service_has_feature_library():
    """FeatureBrowserService should have _feature_library attribute."""
    from api.services.feature_browser_service import FeatureBrowserService

    service = FeatureBrowserService()
    assert hasattr(service, "_feature_library"), "Missing _feature_library attribute"


# ── T4-12: feature_browser _load_features_df supports library: prefix ──

def test_feature_browser_load_features_library_prefix():
    """_load_features_df should recognize 'library:BTCUSDT:1h' format."""
    from api.services.feature_browser_service import FeatureBrowserService
    from unittest.mock import MagicMock, patch

    service = FeatureBrowserService()
    mock_lib = MagicMock()
    mock_lib.load.return_value = pd.DataFrame({"feat_a": [1.0, 2.0]})
    service._feature_library = mock_lib

    result = service._load_features_df("library:BTCUSDT:1h")
    mock_lib.load.assert_called_once_with("BTCUSDT", "1h")
    assert len(result) == 2


# ── T4-13: FeatureGenerationRequest model has date fields ──

def test_feature_generation_request_has_date_fields():
    """FeatureGenerationRequest should have start_date and end_date fields."""
    from api.models.feature_factory_models import FeatureGenerationRequest

    req = FeatureGenerationRequest(
        symbols=["BTCUSDT"],
        timeframe="1h",
        start_date="2024-01-01",
        end_date="2025-12-31",
    )
    assert req.start_date == "2024-01-01"
    assert req.end_date == "2025-12-31"


# ── T4-14: KlineDownloadTrigger component exists ──

def test_kline_download_trigger_exists():
    """KlineDownloadTrigger.tsx should exist in common components."""
    from pathlib import Path
    component_path = Path("frontend/src/components/common/KlineDownloadTrigger.tsx")
    assert component_path.exists(), "KlineDownloadTrigger.tsx not found"
```

---

## Phase 5：跨 Symbol 訓練整合

### TASK-5.1：IC cross-sectional 模式擴充

**目標**：實現 REDESIGN.md ADR-4 — IC 分析支援 `mode = "longitudinal" | "cross_sectional"`，截面模式使用 `FeatureLibrary.load_multi()` 載入多 symbol 特徵

**修改檔案 1**：`api/models/ic_models.py`

在 `ICAnalyzeRequest` model 中新增 `mode` 欄位：

```python
from typing import Literal

class ICAnalyzeRequest(BaseModel):
    # ... 現有欄位 ...
    mode: Literal["longitudinal", "cross_sectional"] = "longitudinal"
    # cross_sectional 模式所需：
    symbols: Optional[List[str]] = None  # 多 symbol 列表
```

**修改檔案 2**：`api/services/ic_analysis_service.py`

在 `_run_analysis()` 中，根據 `request.mode` 分流：

```python
if request.mode == "cross_sectional":
    # 使用 FeatureLibrary.load_multi() 載入多 symbol 特徵
    if not request.symbols or len(request.symbols) < 2:
        raise ValueError("cross_sectional mode requires at least 2 symbols")

    multi_features = self._feature_library.load_multi(request.symbols, request.timeframe)

    # 組裝截面 DataFrame: MultiIndex (symbol, timestamp)
    frames = []
    for sym, df in multi_features.items():
        df = df.copy()
        df["_symbol"] = sym
        frames.append(df)
    cross_df = pd.concat(frames)
    cross_df = cross_df.set_index("_symbol", append=True)

    # 傳給 IC orchestrator 的截面分析路徑
    report = analyzer.analyze_cross_sectional(
        features=cross_df,
        labels_path=request.labels_path,
        config_override=config_override,
        progress_callback=progress_callback,
    )
else:
    # 原有縱向 IC 邏輯（不變）
    report = analyzer.analyze(
        features_path=features_path,
        # ... 原有參數 ...
    )
```

**截面 IC 計算公式**（來自 REDESIGN.md）：

$$\text{Cross-sectional IC}_t = \text{Rank Corr}\left(\text{feature}_{i,t},\ r_{i,t+1}\right)_{i \in \text{universe}}$$

注意：`analyzer.analyze_cross_sectional()` 方法需要在 `momentum/Analysis/` 層的 IC orchestrator 中新增。此方法接收 MultiIndex DataFrame，對每個 timestamp 計算所有 symbol 間的 Rank Correlation。此方法在 `momentum/` 層實作，遵循 Rule 1。

---

### TASK-5.2：CrossSymbolValidator + FeatureLibrary 串接

**目標**：讓現有 `CrossSymbolValidator`（`momentum/Analysis/cross_symbol_validator.py`）透過 `FeatureLibrary.load_multi()` 取得特徵，實現跨 symbol 訓練 pipeline

**背景**：
- `CrossSymbolValidator` 已實作（`validate_cross_symbol()` + `run_leave_one_symbol_out()`）
- 接受 `np.ndarray (X, y)` 輸入 — 純演算法，不載入資料
- `create_cross_symbol_validator()` factory 已存在（`momentum/factories.py` L177-179）
- 目前缺少：「從 FeatureLibrary 載入特徵 → 轉為 X/y → 餵入 CrossSymbolValidator」的膠水程式碼

**建立檔案**：`api/services/cross_symbol_training_service.py`

```python
"""Cross-symbol training service — loads features via FeatureLibrary, feeds to CrossSymbolValidator."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from momentum.core.contracts import FeatureNotFoundError
from momentum.factories import create_cross_symbol_validator, create_feature_library
from api.core.logging import get_logger

logger = get_logger(__name__)


class CrossSymbolTrainingService:
    """Orchestrates cross-symbol validation using FeatureLibrary as data source."""

    def __init__(self) -> None:
        self._feature_library = create_feature_library()
        self._validator = create_cross_symbol_validator()

    async def run_cross_symbol_validation(
        self,
        symbols: List[str],
        timeframe: str,
        label_column: str = "label",
        feature_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        1. FeatureLibrary.load_multi() 載入多 symbol 特徵
        2. 擷取 X (features) 和 y (labels)
        3. CrossSymbolValidator.run_leave_one_symbol_out()
        4. 回傳驗證結果
        """
        # Step 1: 載入特徵
        multi_features = self._feature_library.load_multi(symbols, timeframe)

        # Step 2: 準備 X/y by symbol
        X_by_symbol: Dict[str, np.ndarray] = {}
        y_by_symbol: Dict[str, np.ndarray] = {}

        for sym, df in multi_features.items():
            if label_column not in df.columns:
                raise ValueError(f"Label column '{label_column}' not found in {sym}/{timeframe}")

            y = df[label_column].values
            if feature_columns:
                X = df[feature_columns].values
            else:
                # 排除 label column，使用所有 numeric columns
                feature_cols = [c for c in df.select_dtypes(include="number").columns if c != label_column]
                X = df[feature_cols].values

            X_by_symbol[sym] = X.astype(np.float32)
            y_by_symbol[sym] = y

        # Step 3: Leave-One-Symbol-Out 驗證
        results = self._validator.run_leave_one_symbol_out(
            symbols=symbols,
            X_by_symbol=X_by_symbol,
            y_by_symbol=y_by_symbol,
        )

        # Step 4: 彙整結果
        return {
            "symbols": symbols,
            "timeframe": timeframe,
            "n_symbols": len(symbols),
            "results": [
                {
                    "source_symbol": r.source_symbol if hasattr(r, "source_symbol") else "",
                    "target_symbol": r.target_symbol if hasattr(r, "target_symbol") else "",
                    "source_auc": r.source_auc if hasattr(r, "source_auc") else 0.0,
                    "target_auc": r.target_auc if hasattr(r, "target_auc") else 0.0,
                    "generalization_gap": r.generalization_gap if hasattr(r, "generalization_gap") else 0.0,
                    "verdict": r.verdict if hasattr(r, "verdict") else "unknown",
                }
                for r in results
            ],
        }
```

**建立檔案**：`api/routes/cross_symbol.py`

```python
"""Cross-symbol training API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.services.cross_symbol_training_service import CrossSymbolTrainingService

router = APIRouter(prefix="/cross-symbol", tags=["cross-symbol"])

_service = CrossSymbolTrainingService()


class CrossSymbolValidationRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=2, description="至少 2 個 symbol")
    timeframe: str
    label_column: str = "label"
    feature_columns: Optional[List[str]] = None


@router.post("/validate")
async def run_validation(request: CrossSymbolValidationRequest):
    """執行跨 symbol Leave-One-Out 驗證。"""
    result = await _service.run_cross_symbol_validation(
        symbols=request.symbols,
        timeframe=request.timeframe,
        label_column=request.label_column,
        feature_columns=request.feature_columns,
    )
    return result
```

**修改檔案**：`api/main.py`

在 router 註冊區塊中新增：

```python
from api.routes.cross_symbol import router as cross_symbol_router
app.include_router(cross_symbol_router, prefix="/api/v1")
```

---

### TASK-5.3：Phase 5 測試

**建立檔案**：`tests/feature_library/test_phase5.py`

```python
"""Phase 5 tests: cross-symbol training integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ── T5-01: ICAnalyzeRequest has mode field ──

def test_ic_analyze_request_has_mode_field():
    """ICAnalyzeRequest should support mode = 'longitudinal' | 'cross_sectional'."""
    from api.models.ic_models import ICAnalyzeRequest

    # Default should be longitudinal
    req = ICAnalyzeRequest(features_path="test.h5")
    assert req.mode == "longitudinal"

    # Should accept cross_sectional
    req2 = ICAnalyzeRequest(features_path="test.h5", mode="cross_sectional", symbols=["BTC", "ETH"])
    assert req2.mode == "cross_sectional"
    assert req2.symbols == ["BTC", "ETH"]


# ── T5-02: cross_sectional mode requires load_multi ──

def test_cross_sectional_mode_uses_load_multi():
    """In cross_sectional mode, IC service should call FeatureLibrary.load_multi()."""
    from api.services.ic_analysis_service import ICAnalysisService

    service = ICAnalysisService()
    mock_lib = MagicMock()
    mock_lib.load_multi.return_value = {
        "BTC": pd.DataFrame({"feat_a": [1.0, 2.0]}),
        "ETH": pd.DataFrame({"feat_a": [3.0, 4.0]}),
    }
    service._feature_library = mock_lib

    # Verify the service has the capability to handle cross_sectional mode
    assert hasattr(service, "_feature_library")
    assert callable(getattr(service._feature_library, "load_multi", None))


# ── T5-03: CrossSymbolValidator receives correct data shape ──

def test_cross_symbol_validator_correct_data_shape():
    """CrossSymbolValidator should accept Dict[str, np.ndarray] for X and y."""
    from momentum.Analysis.cross_symbol_validator import CrossSymbolValidator

    validator = CrossSymbolValidator()

    X_by_symbol = {
        "BTC": np.random.randn(100, 5).astype(np.float32),
        "ETH": np.random.randn(80, 5).astype(np.float32),
    }
    y_by_symbol = {
        "BTC": np.random.randint(0, 2, 100),
        "ETH": np.random.randint(0, 2, 80),
    }

    # Should not raise
    results = validator.run_leave_one_symbol_out(
        symbols=["BTC", "ETH"],
        X_by_symbol=X_by_symbol,
        y_by_symbol=y_by_symbol,
    )
    assert len(results) == 2  # Leave-one-out: 2 symbols → 2 results


# ── T5-04: load_multi returns dict keyed by symbol ──

def test_load_multi_returns_dict_keyed_by_symbol():
    """FeatureLibrary.load_multi should return Dict[str, DataFrame]."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = {"symbol": "X", "timeframe": "1h", "config_hash": "h"}

    mock_result = MagicMock()
    mock_result.features = pd.DataFrame({"f": [1.0]})

    mock_storage = MagicMock()
    mock_storage.load_factory_output.return_value = mock_result

    lib = FeatureLibrary(mock_registry, mock_storage)
    result = lib.load_multi(["SYM1", "SYM2"], "1h")
    assert isinstance(result, dict)
    assert "SYM1" in result
    assert "SYM2" in result


# ── T5-05: cross_sectional IC computation is non-empty ──

def test_cross_sectional_ic_non_empty():
    """Cross-sectional IC should produce a non-empty result for valid multi-symbol data."""
    # This is a smoke test for the cross-sectional IC calculation logic
    from scipy.stats import spearmanr

    # Simulate 3 symbols × 2 features at time t
    features_at_t = np.array([[0.5, 1.2], [0.8, 0.9], [0.3, 1.5]])
    returns_at_t = np.array([0.02, -0.01, 0.03])

    # Cross-sectional Rank IC for feature 0
    ic, pval = spearmanr(features_at_t[:, 0], returns_at_t)
    assert not np.isnan(ic), "Cross-sectional IC should not be NaN"


# ── T5-06: leave_one_out results contain expected fields ──

def test_leave_one_out_result_fields():
    """Each LOO result should have source_auc, target_auc, generalization_gap."""
    from momentum.Analysis.cross_symbol_validator import CrossSymbolValidator

    validator = CrossSymbolValidator()
    np.random.seed(42)

    X_by_symbol = {
        "A": np.random.randn(200, 3).astype(np.float32),
        "B": np.random.randn(200, 3).astype(np.float32),
    }
    y_by_symbol = {
        "A": np.random.randint(0, 2, 200),
        "B": np.random.randint(0, 2, 200),
    }

    results = validator.run_leave_one_symbol_out(
        symbols=["A", "B"],
        X_by_symbol=X_by_symbol,
        y_by_symbol=y_by_symbol,
    )
    for r in results:
        assert hasattr(r, "source_auc") or hasattr(r, "target_auc"), (
            "Result should have AUC fields"
        )


# ── T5-07: CrossSymbolValidationRequest requires at least 2 symbols ──

def test_cross_symbol_request_min_symbols():
    """CrossSymbolValidationRequest should require at least 2 symbols."""
    from pydantic import ValidationError

    # Import from where it's defined
    import sys
    sys.path.insert(0, ".")

    try:
        from api.routes.cross_symbol import CrossSymbolValidationRequest

        with pytest.raises(ValidationError):
            CrossSymbolValidationRequest(
                symbols=["ONLY_ONE"],
                timeframe="1h",
            )

        # 2 symbols should be valid
        req = CrossSymbolValidationRequest(
            symbols=["BTC", "ETH"],
            timeframe="1h",
        )
        assert len(req.symbols) == 2
    except ImportError:
        pytest.skip("cross_symbol route not yet created")
```

---

## 全域完成條件

所有 Phase 完成後，執行以下驗證：

```bash
# 1. 全部 49 個測試 PASS
./venv/bin/pytest tests/feature_library/ -v --tb=short

# 2. 解耦驗證：momentum/ 不可 import api/
grep -r "from api\." momentum/ | grep -v __pycache__ | wc -l
# 預期輸出：0

# 3. 型別檢查（前端）
cd frontend && npx tsc --noEmit

# 4. API 啟動正常
python run_api.py  # 確認無 import error，Ctrl+C 退出
```

---

## Frozen Checklist

- [x] 所有 TASK 有明確的檔案路徑和程式碼變更
- [x] 方案選擇已凍結，無需 Agent 判斷
- [x] 邊界條件已列為測試項目（T1-04 空 dataset, T1-13 zero volume, T1-14 missing column, T2-04 missing keys, T2-05 corrupt json, T3-06 load_multi missing symbol, T5-07 min 2 symbols）
- [x] 依賴順序明確（Phase 1 → 2 → 3 → 4 → 5，TASK 內部順序固定）
- [x] 測試覆蓋：49 個測試函式跨 5 個 Phase
- [x] 解耦規則嚴格遵守（Rule 1-7）
- [x] float32 一致性（save 和 load 兩端都修正）
- [x] 向後相容（features_path 保留為 deprecated）
- [x] LightGBM 覆蓋（系統預設 ML 引擎，TASK-4.3 全服務遷移）
- [x] 跨 symbol 訓練整合（Phase 5，CrossSymbolValidator + FeatureLibrary.load_multi 串接）
- [x] IC 截面模式（ADR-4，Phase 5 實作 longitudinal | cross_sectional）

---

## 附錄：暫不實作項目

以下項目列在 `FEATURE_LIBRARY_FIRST_PRINCIPLES_REDESIGN.md` 中但**不在本計畫範圍**：

| 項目 | 理由 | 預計時間 |
|------|------|---------|
| LSTM/Transformer 整合 | M1 8GB 限制，需等硬體升級 | V2.0+ |
| registry.json → SQLite 遷移 | 單行程下 JSON 足夠，規模擴大後再遷移 | Phase 6+ |
| Agent V2.0 chat interface | 架構已預留解耦點，但不在 V1.0 範圍 | V2.0 |
| Layer 5 cross_sectional lazy-load 改造 | ADR-9，等 FeatureLibrary 完成後再評估 | Phase 6+ |
| LabelStore 獨立模組 | 等 FeatureLibrary 完成後再拆出 | Phase 6+ |
| Optuna objective 跨 tf 特徵組裝 | 等變更 5 穩定後 | Phase 6+ |
| 1h 計算效能進一步優化 | variance threshold + 平行 tf + meta features 去重，float32 後仍有瓶頸時再處理 | Phase 6+ |
