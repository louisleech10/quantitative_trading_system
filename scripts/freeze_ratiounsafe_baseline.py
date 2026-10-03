"""RATIOUNSAFE §G／Task 1.3／Task 2.2（docs/RATIOUNSAFE_SPEC.md v5）：S1 落盤路徑基準之產生與比對工具。

設定單一落點：`tests/_golden/ratiounsafe/contract.json`。一律經 `generate_features(persist=True)` 落盤至暫存目錄後讀
`raw` 成品（生產落盤路徑，L6.5 經 `transform_registry_groups_to_sink`）。真實 `data_cache/feature_klines/kline_cache.h5`；
不寫 `data_cache/features`。

用法：
  venv/bin/python scripts/freeze_ratiounsafe_baseline.py --stage before   # 動工前（HEAD）：寫 tests/_golden/ratiounsafe/baseline.json
  venv/bin/python scripts/freeze_ratiounsafe_baseline.py --stage after    # Task 2.1 驗收後、使用者核可之改後基準：寫 baseline_after.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
CONTRACT_PATH = REPO / "tests/_golden/ratiounsafe/contract.json"
OUT_DIR = REPO / "tests/_golden/ratiounsafe"


def contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for key, value in extra.items():
        out[key] = _merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def _end_and_start(symbol: str, timeframe: str, days: int):
    import h5py
    import numpy as np
    import pandas as pd

    with h5py.File(REPO / "data_cache/feature_klines/kline_cache.h5", "r") as f:
        end = pd.Timestamp(int(np.asarray(f[f"/{symbol}/{timeframe}/data"]["timestamp"]).max()), unit="s", tz="UTC")
    return (end - pd.Timedelta(days=days)).strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def generate_raw(payload: dict, symbol: str, timeframe: str, days: int):
    """一次生成並落盤至暫存目錄，回傳 (raw 成品 DataFrame, parquet 總 bytes)。"""
    import pandas as pd

    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.factories import create_feature_factory

    os.environ.setdefault("FFACT_LAYER1_PARALLEL", "0")
    start, end = _end_and_start(symbol, timeframe, days)
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["FFACT_CGSA_WORK_DIR"] = str(Path(tmp) / "cgsa")
        factory = create_feature_factory(cache_dir=str(REPO / "data_cache/feature_klines"), validate_continuity=False)
        factory._storage = FeatureStorage(str(Path(tmp) / "features"))
        factory.generate_features(symbol, timeframe, config_override=payload, force_regenerate=True,
                                  start_date=start, end_date=end, persist=True)
        manifests = sorted(Path(tmp, "features").rglob("feature_manifest.json"))
        if not manifests:
            raise FileNotFoundError("暫存目錄無 feature_manifest.json")
        run_dir = manifests[0].parent
        reader = FeatureReader(str(Path(tmp, "features")))
        parts = [df for _, df in reader.stream_groups_v2(symbol, timeframe, run_dir.name, "raw", allow_partial=True)]
        frame = pd.concat(parts, axis=1) if parts else pd.DataFrame()
        nbytes = sum(p.stat().st_size for p in run_dir.rglob("*.parquet"))
    return frame, nbytes


def s1_payload(arm: str, preprocessing: bool) -> dict:
    c = contract()["s1"]
    payload = _merge(c["payload"], c["arms"][arm])
    payload["timeframes"] = {"primary": c["timeframe"], "training": [c["timeframe"]]}
    if not preprocessing:
        payload["preprocessing"] = {"enabled": False}
    return payload


def column_digest(series) -> Dict[str, str]:
    import numpy as np

    arr = np.asarray(series, dtype=np.float64)
    return {"value_sha256": hashlib.sha256(np.nan_to_num(arr, nan=0.0).tobytes()).hexdigest(),
            "nan_mask_sha256": hashlib.sha256(np.isnan(arr).tobytes()).hexdigest()}


def record(frame, nbytes: int) -> dict:
    names = sorted(str(c) for c in frame.columns)
    return {"names_sha256": hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest(), "names": names,
            "n_columns": len(names), "n_rows": int(len(frame)), "parquet_bytes": int(nbytes),
            "columns": {str(c): column_digest(frame[c]) for c in frame.columns}}


def s1_record(arm: str, preprocessing: bool) -> dict:
    c = contract()["s1"]
    frame, nbytes = generate_raw(s1_payload(arm, preprocessing), c["symbol"], c["timeframe"], int(c["days"]))
    return record(frame, nbytes)


def multi_tf_names() -> List[str]:
    c = contract()["multi_tf_names"]
    payload = {"timeframes": {"primary": c["primary"], "training": list(c["training"])},
               "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
               "atomic_indicators": c["atomic_indicators"]}
    frame, _ = generate_raw(payload, c["symbol"], c["primary"], int(c["days"]))
    return sorted(str(col) for col in frame.columns)


def build(stage: str) -> dict:
    out: Dict[str, object] = {"stage": stage, "spec": "docs/RATIOUNSAFE_SPEC.md v5"}
    for arm in ("off", "on"):
        out[f"s1_{arm}"] = s1_record(arm, True)
    if stage == "before":
        for arm in ("off", "on"):
            out[f"s1_{arm}_preprocessing_disabled"] = s1_record(arm, False)
        names = multi_tf_names()
        out["multi_tf_names"] = {"names": names,
                                 "names_sha256": hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()}
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("before", "after"), required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    target = Path(args.out) if args.out else OUT_DIR / ("baseline.json" if args.stage == "before" else "baseline_after.json")
    data = build(args.stage)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
