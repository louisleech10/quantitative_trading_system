"""RATIOUNSAFE §G／Task 1.3／Task 2.2（docs/RATIOUNSAFE_SPEC.md v5）：S1 落盤路徑基準之產生與比對工具。

設定單一落點：`tests/_golden/ratiounsafe/contract.json`。一律經 `generate_features(persist=True)` 落盤至暫存目錄後讀
`raw` 成品（生產落盤路徑，L6.5 經 `transform_registry_groups_to_sink`）。真實 `data_cache/feature_klines/kline_cache.h5`；
不寫 `data_cache/features`。

用法：
  venv/bin/python scripts/freeze_ratiounsafe_baseline.py --stage before   # 動工前（HEAD）：寫 tests/_golden/ratiounsafe/baseline.json
  venv/bin/python scripts/freeze_ratiounsafe_baseline.py --stage after    # Task 2.1 驗收後、使用者核可之改後基準：寫 baseline_after.json
  venv/bin/python scripts/freeze_ratiounsafe_baseline.py --stage branch-oracle   # 動工前（HEAD）：寫 branch_oracle.json（safe 欄改前 oracle）
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


# ---------------------------------------------------------------- Task 2.1 分支強制（測試與改前 oracle 共用）

def branch_frame(columns: Optional[List[str]] = None):
    """真實 kline（契約 branch_kline）上以 TA-Lib 算之 ratio-unsafe（pattern）與 safe 欄；欄名為生成期未標記名。"""
    import numpy as np
    import pandas as pd
    import talib

    from tests.feature_engineering import ffstat_helpers as h

    c = contract()
    k = c["branch_kline"]
    base = h.kline_frame(symbol=k["symbol"], timeframe=k["timeframe"]).iloc[: k["rows"]]
    o, hi, lo, cl = (base[x].to_numpy(dtype=np.float64) for x in ("open", "high", "low", "close"))
    data = {}
    for spec in c["branch_columns"]["unsafe"]:
        data[spec["name"]] = getattr(talib, spec["fn"])(o, hi, lo, cl).astype(np.float64)
    for spec in c["branch_columns"]["safe"]:
        data[spec["name"]] = getattr(talib, spec["fn"])(cl, **spec["args"])
    frame = pd.DataFrame(data, index=base.index)
    return frame[columns] if columns else frame


def l65_config(mode: str = "replace", zscore: Optional[List[int]] = None, fracdiff: bool = False) -> dict:
    return {
        "enabled": True, "mode": mode, "causal_preprocessing": True,
        "winsorization": {"enabled": True, "method": "quantile", "quantile_range": [0.01, 0.99], "window": 252,
                          "apply_to": "all"},
        "fractional_differencing": {"enabled": bool(fracdiff)},
        "adf_differencing": {"enabled": False},
        "rank_transform": {"enabled": False},
        "adaptive_zscore": {"enabled": bool(zscore), "windows": list(zscore or [100]), "apply_to": "all"},
        "gaussian_normalize": {"enabled": False},
    }


def branch_config(branch: str) -> dict:
    spec = contract()["branches"][branch]
    return l65_config(spec.get("mode", "replace"), spec.get("zscore_windows"))


def run_branch(branch: str, frame, work_dir: Path, cfg: Optional[dict] = None, tag: str = "g",
               sink_log: Optional[list] = None, spy_calls: Optional[list] = None):
    """以契約之分支設定（env、shard 位元組、mode）跑一次 L6.5 registry 入口；回傳輸出 DataFrame（replace 欄序同輸入；
    append 依欄名排序）。`spy_calls` 收集具名分支待測物之呼叫（由呼叫端決定是否要求非空）。env 與 patch 於返回前還原。"""
    import numpy as np
    import pandas as pd

    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from momentum.FeatureEngineering.utils import hardware_utils

    spec = contract()["branches"][branch]
    cfg = cfg or branch_config(branch)
    mode = cfg.get("mode", "replace")
    saved_env = {k: os.environ.get(k) for k in spec.get("env", {})}
    saved_shard = hardware_utils.get_cgsa_shard_bytes
    saved_spy = getattr(FeaturePreprocessor, spec["spy"]) if spec.get("spy") else None
    try:
        os.environ.update(spec.get("env", {}))
        if "patch_shard_bytes" in spec:
            hardware_utils.get_cgsa_shard_bytes = lambda: int(spec["patch_shard_bytes"])
        if saved_spy is not None:
            def _spy(self, *args, **kwargs):
                if spy_calls is not None:
                    spy_calls.append(spec["spy"])
                return saved_spy(self, *args, **kwargs)

            setattr(FeaturePreprocessor, spec["spy"], _spy)
        pre = FeaturePreprocessor(cfg)
        registry = ColumnGroupRegistry(work_dir=Path(work_dir) / f"registry_{branch}_{tag}")
        group = ColumnGroup(group_id=f"12h_L1_ratiounsafe_{tag}", layer=LayerSource.L1, timeframe="12h",
                            data_source="ohlc", indicator="RATIOUNSAFE", columns=tuple(frame.columns), shape=(0, 0),
                            dtype="float32", disk_path=None)
        group = registry.save_data(group, frame.to_numpy(dtype=np.float32))
        if spec["entry"] == "transform_registry_groups":
            pre.transform_registry_groups(registry, n_workers=int(spec.get("n_workers", 1)))
            return pd.DataFrame(registry.load_data(group.group_id), columns=list(frame.columns), index=frame.index)
        parts = {}

        def _sink(group_id, columns, data, source_group_id, source_disk_path, cleanup_source) -> None:
            if sink_log is not None:
                sink_log.append((str(group_id), tuple(str(c) for c in columns)))
            arr = np.asarray(data, dtype=np.float64)
            for i, name in enumerate(columns):
                parts[str(name)] = arr[:, i].copy()

        pre.transform_registry_groups_to_sink(registry, _sink, n_workers=1)
        names = list(frame.columns) if mode == "replace" else sorted(parts)
        return pd.DataFrame({c: parts[c] for c in names}, index=frame.index)
    finally:
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        hardware_utils.get_cgsa_shard_bytes = saved_shard
        if saved_spy is not None:
            setattr(FeaturePreprocessor, spec["spy"], saved_spy)


def run_native(columns: List[str], work_dir: Path, native_calls: Optional[list] = None):
    """native 強制臂：compact-aligned 群組（真實 12h 值、均勻 idx_map）經 to_sink；回傳 {欄: 主週期陣列}、idx_map、source。"""
    import numpy as np

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from tests.feature_engineering.preprocessing.test_l65_native_tf import _make_compact_registry, _make_idx_map_uniform

    arm = contract()["native_arm"]
    saved_env = {k: os.environ.get(k) for k in arm["env"]}
    real = FeaturePreprocessor._maybe_run_native_l65_to_sink
    try:
        os.environ.update(arm["env"])

        def _spy(self, *args, **kwargs):
            result = real(self, *args, **kwargs)
            if native_calls is not None:
                native_calls.append(result)
            return result

        FeaturePreprocessor._maybe_run_native_l65_to_sink = _spy
        frame = branch_frame(columns)
        source = frame.to_numpy(dtype=np.float32)
        idx_map = _make_idx_map_uniform(source.shape[0], int(arm["ratio"]))
        registry = _make_compact_registry(Path(work_dir), source=source, idx_map=idx_map, columns=tuple(columns))
        parts = {}

        def _sink(group_id, cols, data, *rest) -> None:
            arr = np.asarray(data, dtype=np.float64)
            for i, name in enumerate(cols):
                parts[str(name)] = arr[:, i].copy()

        FeaturePreprocessor(l65_config()).transform_registry_groups_to_sink(registry, _sink, n_workers=1)
        return {"parts": parts, "idx_map": idx_map, "source": source}
    finally:
        FeaturePreprocessor._maybe_run_native_l65_to_sink = real
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def branch_oracle() -> dict:
    """改前 oracle（動工前於 HEAD 產）：各分支、native 臂、append 臂之**只含 safe 欄群組**之輸出逐欄 digest。
    safe 欄之 L6.5 為逐欄運算，故改後混合群組之 safe 欄（含 append 衍生欄）須逐位元組等於此。"""
    c = contract()
    safe = [s["name"] for s in c["branch_columns"]["safe"]]
    out: Dict[str, Dict[str, Dict[str, str]]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for branch in sorted(c["branches"]):
            calls: list = []
            frame = run_branch(branch, branch_frame(safe), Path(tmp), tag="oracle", spy_calls=calls)
            spec = c["branches"][branch]
            if spec.get("spy") and not calls:
                raise RuntimeError(f"改前 oracle：分支 {branch} 未執行 {spec['spy']}")
            out[branch] = {str(col): column_digest(frame[col]) for col in frame.columns}
        arm = c["append_arm"]
        frame = run_branch(arm["branch"], branch_frame(safe), Path(tmp), cfg=l65_config("append", arm["zscore_windows"]),
                           tag="oracle_append")
        out["append_arm"] = {str(col): column_digest(frame[col]) for col in frame.columns}
        native_calls: list = []
        nat = run_native(safe, Path(tmp) / "native", native_calls=native_calls)
        if not native_calls or native_calls[-1] is None:
            raise RuntimeError("改前 oracle：native 臂未走 native")
        out["native_arm"] = {col: column_digest(arr) for col, arr in nat["parts"].items()}
    return out


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
    parser.add_argument("--stage", choices=("before", "after", "branch-oracle"), required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    default = {"before": "baseline.json", "after": "baseline_after.json", "branch-oracle": "branch_oracle.json"}
    target = Path(args.out) if args.out else OUT_DIR / default[args.stage]
    data = branch_oracle() if args.stage == "branch-oracle" else build(args.stage)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
