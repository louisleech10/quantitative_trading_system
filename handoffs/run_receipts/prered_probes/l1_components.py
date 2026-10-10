"""PRE-RED 探針：於「目前工作目錄所在之 repo 版本」計算 BTCUSDT/12h L1 凍結基準五分量＋逐欄雜湊。

用法（須 PYTHONHASHSEED=0；cwd＝待測 worktree 根，其 data_cache 與 venv 已 symlink）：
    env PYTHONHASHSEED=0 venv/bin/python <本檔> <輸出 json>
與 tests/feature_engineering/test_failopen_contract.py::_compute_l1_canonical_sha256 同流程，
另輸出逐欄 (名稱, dtype, 值 sha, NaN 遮罩 sha) 以便跨 commit 定位改變之欄。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))


def _freeze():
    spec = importlib.util.spec_from_file_location("freeze_failopen_baseline", ROOT / "scripts/freeze_failopen_baseline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(out: str) -> int:
    assert os.environ.get("PYTHONHASHSEED") == "0"
    import numpy as np

    freeze = _freeze()
    for k, v in freeze.FIXED_ENV.items():
        os.environ[k] = v
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["FFACT_CGSA_WORK_DIR"] = str(Path(tmp) / "registry")
        from momentum.FeatureEngineering.core.column_group import LayerSource
        from momentum.factories import create_feature_factory

        factory = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
        payload = freeze._fixed_config_payload(["12h"], "12h")
        config = factory._resolve_config(payload)
        start, end = freeze._window_dates()
        config_hash = factory._compute_config_hash(config, "BTCUSDT", "12h", start_date=start, end_date=end)
        factory._cgsa_force_fresh = True
        factory._current_symbol = "BTCUSDT"
        factory._current_timeframe = "12h"
        factory._cgsa_registry = factory._prepare_cgsa_registry("BTCUSDT", "12h", config_hash)
        raw = factory._layer0_data_ingestion("BTCUSDT", "12h", config, start_date=start, end_date=end)
        res = factory._execute_layer1_6("Layer 1", factory._layer1_atomic_indicators, raw, config)
        reg = factory._cgsa_registry
        groups = reg.list_by_layer(LayerSource.L1)
        record = freeze._hash_registry_table(reg, groups, raw.index)
        per_col = []
        arrays = {}
        for g in freeze._ordered_groups(reg, groups):
            data = np.asarray(reg.load_data_native(g.group_id))
            for i, name in enumerate(g.columns):
                v = data[:, i]
                arrays[str(name)] = np.asarray(v, dtype=np.float64)
                per_col.append({
                    "name": str(name),
                    "dtype": str(np.dtype(g.dtype)),
                    "values": hashlib.sha256(freeze._canonical_array_bytes(v)).hexdigest(),
                    "mask": hashlib.sha256(np.packbits(np.isnan(v).astype(np.uint8), bitorder="little").tobytes()).hexdigest(),
                    "first_valid": int(np.argmax(~np.isnan(v))) if (~np.isnan(v)).any() else -1,
                })
        record["per_column"] = per_col
        record["window"] = [start, end]
        record["index_first_last"] = [int(raw.index[0]), int(raw.index[-1])]
        record["layer_result_type"] = type(res).__name__
    Path(out).write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    np.savez_compressed(str(Path(out).with_suffix(".npz")), **arrays)
    print("canonical", record["canonical_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
