"""ICHC B4 測試共用 runner：la0 真實 kline 衍生 fixture 跑 analyze()，persist 導 tmp。

與 scripts/ichc_freeze_p2_golden.py 同一 fixture 來源（ETHUSDT/12h tail2000）。
"""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parents[3]
LA0_INPUTS = REPO / "tests/golden/la0/inputs"
H5_GLOB = "ETHUSDT_12h_*_a0_tail2000.h5"
KLINE_CACHE_DIR = "data_cache/feature_klines"


def fixture_paths() -> tuple[Path, Path]:
    matches = sorted(LA0_INPUTS.glob(H5_GLOB))
    assert matches, f"fixture 缺席：{LA0_INPUTS}/{H5_GLOB}"
    h5 = matches[0]
    meta = h5.with_name(h5.stem + "_meta.json")
    assert meta.exists(), f"meta 缺席：{meta}"
    return h5, meta


def run_analyze(
    config_override: Optional[dict] = None,
    event_timestamps: Optional[list] = None,
    sidefx_dir: Optional[Path] = None,
    event_label_values: Optional[dict] = None,  # GAP-3 B2.3：條件 IC 事件 label（透傳；None ⇒ 原行為）
) -> dict:
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    h5, meta = fixture_paths()
    orchestrator = create_ic_analyzer()
    tmp = Path(sidefx_dir) if sidefx_dir else Path(tempfile.mkdtemp(prefix="ichc_b4_sidefx_"))
    reporter = orchestrator._reporter
    orig_save_report = reporter.save_report
    orig_save_filter_log = reporter.save_filter_log
    orig_save_filtered = reporter.save_filtered_features

    def _save_report(report, output_dir=None, case_id=None, **kwargs):
        return orig_save_report(report, output_dir=str(tmp / "reports"), case_id=case_id, **kwargs)

    def _save_filter_log(filter_log, output_dir=None, case_id=None, **kwargs):
        return orig_save_filter_log(filter_log, output_dir=str(tmp / "reports"), case_id=case_id, **kwargs)

    def _save_filtered(df, columns, output_path, **kwargs):
        return orig_save_filtered(df, columns, str(tmp / "features" / Path(str(output_path)).name), **kwargs)

    reporter.save_report = _save_report
    reporter.save_filter_log = _save_filter_log
    reporter.save_filtered_features = _save_filtered

    kline_reader = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    return orchestrator.analyze(
        features_path=str(h5.resolve()),
        labels_path="",
        meta_path=str(meta.resolve()),
        config_override=config_override,
        kline_reader=kline_reader,
        event_timestamps=event_timestamps,
        event_label_values=event_label_values,
    )


def feature_index(n: Optional[int] = None):
    """讀 fixture 的 DatetimeIndex（供構造 timestamps 子集）。

    fixture 佈局＝h5py `{SYMBOL}/{tf}/timestamps`（epoch 秒 int64）；
    orchestrator ingestion 會轉 DatetimeIndex——此處回傳同語意 DatetimeIndex。
    """
    import h5py
    import pandas as pd

    h5, _ = fixture_paths()
    with h5py.File(h5, "r") as handle:
        ts = handle["ETHUSDT/12h/timestamps"][:]
    idx = pd.to_datetime(ts, unit="s")
    if n is None:
        return idx
    # 等距散佈取樣（避開頭尾各 5%：warmup/label horizon 裁切帶）——
    # 使子集橫跨 holdout train/test 兩區，避免 test 遮罩空
    import numpy as np

    lo, hi = int(len(idx) * 0.05), int(len(idx) * 0.95)
    picks = np.linspace(lo, hi, num=n, dtype=int)
    return idx[picks]


def canonical_sha(report: dict) -> str:
    """排除時鐘鍵後 canonical sorted JSON sha256。

    排除清單寫死＝{generated_at, filtered_generated_at}：後者是前者的鏡像轉寫
    （orchestrator._persist_outputs 之 source_generated_at=report["generated_at"]），
    同一時鐘源，非第二個排除語意。
    """
    _CLOCK_KEYS = frozenset({"generated_at", "filtered_generated_at"})

    def scrub(node: Any) -> Any:
        if isinstance(node, dict):
            return {
                k: scrub(v) for k, v in node.items() if k not in _CLOCK_KEYS
            }
        if isinstance(node, list):
            return [scrub(v) for v in node]
        if isinstance(node, float) and math.isnan(node):
            return "__nan__"
        return node

    payload = json.dumps(
        scrub(report), sort_keys=True, separators=(",", ":"), allow_nan=False,
        ensure_ascii=False, default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
