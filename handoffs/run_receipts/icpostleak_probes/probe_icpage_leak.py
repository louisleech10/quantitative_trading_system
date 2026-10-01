"""探針：IC 頁「套用後處理」（ic_analysis_service._apply_transforms_sync）是否用到未來資料。
以真實 kline（BTCUSDT 1h close／volume）為兩個特徵欄，跑一次；再只改「最後一列」重跑，比較前面各列是否改變。
寫檔之相對路徑 data_cache/reports 經 chdir 導向 tmp；只讀真實 kline。"""
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/louis/Desktop/quantitative_trading_system")
sys.path.insert(0, str(REPO))
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

klines = h.kline_frame().iloc[:3000][["close", "volume"]].astype(float)
tmp = Path(tempfile.mkdtemp(prefix="probe_icpage_"))
os.chdir(tmp)
from api.services.ic_analysis_service import ic_analysis_service as svc  # noqa: E402


def run(frame: pd.DataFrame, tag: str, **flags) -> pd.DataFrame:
    path = tmp / f"feat_{tag}.parquet"
    frame.to_parquet(path)
    tid = f"probe_{tag}"
    svc._tasks[tid] = {"req_features_path": str(path), "result": {"analysis_status": "ok_oos", "oos_guarantees": True}}
    out = svc._apply_transforms_sync(tid, ["close", "volume"], flags.get("rank", False), flags.get("zscore", False),
                                     flags.get("gaussian", False), 252, [100, 252])
    return pd.read_hdf(out["output_path"], key="features")


for flags in ({"gaussian": True}, {"rank": True}, {"zscore": True}, {"rank": True, "zscore": True, "gaussian": True}):
    tag = "_".join(k for k, v in flags.items() if v)
    base = run(klines, tag + "_a", **flags)
    pert = klines.copy()
    pert.iloc[-1, :] = pert.iloc[-1, :] * 50.0
    moved = run(pert, tag + "_b", **flags)
    a, b = base.iloc[:-1].to_numpy(float), moved.iloc[:-1].to_numpy(float)
    changed = ~((a == b) | (np.isnan(a) & np.isnan(b)))
    first_finite = [int(np.argmax(np.isfinite(base[c].to_numpy(float)))) for c in base.columns]
    print(f"{tag:22s} 改最後一列後，前 {len(a)} 列中值改變之格數={int(changed.sum())}；各欄首個有限值列={first_finite}")
