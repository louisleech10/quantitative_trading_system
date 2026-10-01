"""探針：正式 post-IC 路徑（FeaturePreprocessor.transform_selected）之洩漏與首個有限值列（同 IC 頁探針之輸入與擾動）。"""
import sys
from pathlib import Path

import numpy as np

REPO = Path("/Users/louis/Desktop/quantitative_trading_system")
sys.path.insert(0, str(REPO))
from momentum.FeatureEngineering.feature_config import PreprocessingConfig  # noqa: E402
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor  # noqa: E402
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

klines = h.kline_frame().iloc[:3000][["close", "volume"]].astype(float)


def run(frame, rank, zscore, gaussian):
    cfg = PreprocessingConfig(
        enabled=True, mode="replace",
        winsorization={"enabled": False}, fractional_differencing={"enabled": False}, adf_differencing={"enabled": False},
        rank_transform={"enabled": rank, "window": 252, "apply_to": "all"},
        adaptive_zscore={"enabled": zscore, "windows": [100, 252], "apply_to": "all"},
        gaussian_normalize={"enabled": gaussian, "apply_to": "all"},
    )
    pre = FeaturePreprocessor(cfg.model_dump())
    out = pre.transform_selected(["close", "volume"], {"g": frame}, config=cfg)
    return out["g"]


for rank, zscore, gaussian in ((False, False, True), (True, False, False), (False, True, False), (True, True, True)):
    tag = "_".join(n for n, v in (("rank", rank), ("zscore", zscore), ("gaussian", gaussian)) if v)
    base = run(klines, rank, zscore, gaussian)
    pert = klines.copy()
    pert.iloc[-1, :] = pert.iloc[-1, :] * 50.0
    moved = run(pert, rank, zscore, gaussian)
    a, b = base.iloc[:-1].to_numpy(float), moved.iloc[:-1].to_numpy(float)
    changed = ~((a == b) | (np.isnan(a) & np.isnan(b)))
    first = [int(np.argmax(np.isfinite(base[c].to_numpy(float)))) for c in base.columns]
    print(f"{tag:22s} cols={list(base.columns)} 前 {len(a)} 列值改變格數={int(changed.sum())}；首個有限值列={first}")
