#!/usr/bin/env python
"""R3 前提實跑：stage0（預載 labels）路徑之裁切對 oracle 抽樣集合是否有影響。

    venv/bin/python handoffs/20260908-probe-stage0-trim-oracle.py

命題：同尾預載 label＋全長 close 時，裁切前／後 `alignment_report.checked_samples` 相同
（候選列集合恆等：tail_nans=lag 已保證有值列之 r+lag ≤ 最後 feature 列）。
以 monkeypatch 關掉 helper 模擬「改前」，比對 stage0_log。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from momentum.Analysis import ic_filter_orchestrator as orch_mod  # noqa: E402
from momentum.Analysis.ic_config_schema import load_ic_config  # noqa: E402
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator  # noqa: E402

BASE_S, STEP_S, N_FEAT, N_CLOSE = 1_704_067_200, 43_200, 157, 200
CLOSE = np.linspace(100.0, 200.0, N_CLOSE)
META = {"symbol": "BTCUSDT", "timeframe": "12h", "f1": {"name": "f1", "category": "trend", "layer": 1}}


class _Reader:
    def __init__(self, n): self.n = n
    def read_klines(self, _s, _t):
        idx = pd.Index(BASE_S + np.arange(self.n, dtype=np.int64) * STEP_S, name="timestamp")
        return pd.DataFrame({"close": CLOSE[: self.n]}, index=idx)


def _features():
    idx = pd.Index(BASE_S + np.arange(N_FEAT, dtype=np.int64) * STEP_S, name="timestamp")
    return pd.DataFrame({"f1": np.arange(N_FEAT, dtype=np.float64)}, index=idx)


def _stage0(trim: bool):
    config = load_ic_config()
    o = ICFilterOrchestrator(config)
    real = orch_mod._coterminalize_close
    orch_mod._coterminalize_close = real if trim else (lambda c, f: c)
    try:
        _, labels_df = o._stage2_label_generation(None, META, config, _Reader(N_FEAT), features_df=_features())
        pre = labels_df.copy()
        pre.index = _features().index
        o._load_features_hdf5 = lambda _p: (_features(), {})
        o._load_labels_hdf5 = lambda _p: pre
        o._load_meta_json = lambda _p: dict(META)
        _, _, _, log = o._stage0_ingestion("f", "l", "m", config=config, kline_reader=_Reader(N_CLOSE))
        return log["alignment_report"]
    finally:
        orch_mod._coterminalize_close = real


def main() -> int:
    a, b = _stage0(trim=False), _stage0(trim=True)
    print(f"改前（不裁切）alignment_report = {a}")
    print(f"改後（裁切）  alignment_report = {b}")
    same = a == b
    print(f"逐鍵相同 = {same}")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
