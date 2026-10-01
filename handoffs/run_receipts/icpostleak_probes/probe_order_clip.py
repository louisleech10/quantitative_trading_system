"""探針：IC 頁手寫版 rank→zscore→gaussian 時，gaussian 之輸入（z 分數）落在 [0.001, 0.999] 外而被裁切之比例。
同 probe_icpage_leak 之真實輸入（BTCUSDT 1h 前 3000 根 close、volume），重放手寫版該段之公式（ic_analysis_service.py:2876-2898）。"""
import sys
from pathlib import Path

import numpy as np

REPO = Path("/Users/louis/Desktop/quantitative_trading_system")
sys.path.insert(0, str(REPO))
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

df = h.kline_frame().iloc[:3000][["close", "volume"]].astype(float)
rank_window, zwin = 252, 100
df = df.rolling(rank_window, min_periods=max(rank_window // 2, 1)).rank(pct=True)
roll = df.rolling(zwin, min_periods=max(zwin // 2, 1))
z = (df - roll.mean()) / roll.std().fillna(0.0).clip(lower=1e-8)
vals = z.to_numpy(float)
fin = np.isfinite(vals)
clipped = fin & ((vals <= 0.001) | (vals >= 0.999))
print(f"gaussian 輸入（z 分數）有限值 {int(fin.sum())} 格，其中落在 [0.001, 0.999] 外而被裁切 {int(clipped.sum())} 格"
      f"（{clipped.sum() / fin.sum():.1%}）；被裁切者 ppf 後只剩 ±{abs(float(np.round(__import__('scipy.stats').stats.norm.ppf(0.001), 3)))} 兩值")
