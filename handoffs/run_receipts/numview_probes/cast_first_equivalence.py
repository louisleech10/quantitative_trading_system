"""NUMVIEW Task 3.4 ⑨ mutation 可觀測性實測（docs/NUMVIEW_SPEC.md Task 3.4 mutation「轉換改在核心之前」）：

擇定核心（`pandas_legacy`）對真實 float16 raw 欄之原生輸出，與輸入先轉 float32 後之輸出逐位元比對（NaN 同位視為相等）。
資料＝Task 1.6 收據 (b)（`C_BTCUSDT_1h` 全特徵格）凍結 run 之複本：①Task 1.6 所列 legacy 原生輸出為 float16 之欄（全欄）；
②raw 中 float16 欄之前 300 欄（依群組檔序）取不同值數 > 20 者（非退化）。設定＝IC 頁預設請求之 post-IC 設定，經
`transform()` 環境分派走該核心（同 `tests/api/test_numview_ic_page.py:core_native_output`）。
收據 `handoffs/run_receipts/<date>-numview-cast-first-equivalence.json`。用法：`venv/bin/python <本檔>`（秒級）。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:  # 以腳本執行時 repo 根不在 sys.path（同 winsor_key_inventory.py）
    sys.path.insert(0, str(REPO))
RECEIPTS_DIR = REPO / "handoffs" / "run_receipts"
CORE_ENV = {"FFACT_USE_POLARS": "0", "FFACT_L65_OPTIMIZATION_PROFILE": "legacy", "FFACT_L65_CHUNK_SIZE": "0"}
CANDIDATE_LIMIT = 300
MIN_UNIQUE = 20


def _native(frame: Any) -> Any:
    from momentum.factories import create_feature_preprocessor, create_post_ic_transform_config
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    cfg = create_post_ic_transform_config(rank=True, rank_window=252, zscore=True, zscore_windows=[100, 252], gaussian=False)
    outer = create_feature_preprocessor(cfg.model_dump())
    post = outer._build_post_ic_transform_config(selected_columns=list(frame.columns), config=cfg)
    pre = FeaturePreprocessor(post, context=outer._preprocessing_context, column_layer_map=outer._column_layer_map)
    assert not pre._can_use_optimized_dataframe_path()
    out = pre.transform(frame.copy())
    return out.loc[:, list(frame.columns)]


def _compare(frame: Any) -> Dict[str, Any]:
    import numpy as np

    native = _native(frame)
    cast = _native(frame.astype(np.float32))
    a, b = native.astype(np.float32).to_numpy(), cast.astype(np.float32).to_numpy()
    differ = ~((a == b) | (np.isnan(a) & np.isnan(b)))
    nonconst = [c for c in native.columns if native[c].dropna().nunique() > 1]
    return {"columns": int(frame.shape[1]), "rows": int(frame.shape[0]),
            "input_dtypes": {k: int(v) for k, v in frame.dtypes.astype(str).value_counts().items()},
            "native_output_dtypes": {k: int(v) for k, v in native.dtypes.astype(str).value_counts().items()},
            "cast_first_output_dtypes": {k: int(v) for k, v in cast.dtypes.astype(str).value_counts().items()},
            "finite_native_cells": int(np.isfinite(a).sum()), "differing_cells": int(differ.sum()),
            "native_columns_with_more_than_one_value": len(nonconst)}


def main() -> int:
    import pyarrow.parquet as pq

    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from tests.feature_engineering import numview_helpers as nh

    os.environ.update(CORE_ENV)
    select = sorted(RECEIPTS_DIR.glob("*-numview-postic-core-select.json"))[-1]
    receipt = json.loads(select.read_text(encoding="utf-8"))
    unit = next(u for u in receipt["units"] if u.get("core") == "pandas_legacy" and u.get("input") == "b")
    f16_out = list(json.loads((Path(unit["out_dir"]) / "meta.json").read_text(encoding="utf-8"))["blocks"]["float16"])
    b = receipt["inputs"]["b"]
    root, ch = Path(b["features_root"]), str(b["config_hash"])
    reader = FeatureReader(str(root))
    candidates: List[str] = []
    for group in sorted((root / "BTCUSDT" / "1h" / ch / "raw").glob("*.parquet")):
        candidates += [f.name for f in pq.read_schema(group) if str(f.type) == "halffloat"]
        if len(candidates) >= CANDIDATE_LIMIT:
            break
    raw = reader.load_columns_v2("BTCUSDT", "1h", ch, candidates[:CANDIDATE_LIMIT])
    nontrivial = raw.loc[:, [c for c in raw.columns if raw[c].nunique() > MIN_UNIQUE]]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    stamp = datetime.now(timezone.utc)
    out = {"schema_version": 1, "generated_at": stamp.isoformat(), "head": head,
           "command": "venv/bin/python handoffs/run_receipts/numview_probes/cast_first_equivalence.py",
           "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           # 每份 numview 收據須記現行判準檔 sha256（SPEC Task 0.3 ③）
           "criteria_sha256": hashlib.sha256(Path(nh.current_criteria_path()).read_bytes()).hexdigest(),
           "source_receipt": str(select.relative_to(REPO)), "core_env": CORE_ENV,
           "cases": {"legacy_float16_output_columns": _compare(reader.load_columns_v2("BTCUSDT", "1h", ch, f16_out)),
                     "nontrivial_float16_raw_columns": _compare(nontrivial)}}
    path = RECEIPTS_DIR / f"{stamp.strftime('%Y%m%d')}-numview-cast-first-equivalence.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path.relative_to(REPO), json.dumps({k: (v["differing_cells"], v["finite_native_cells"]) for k, v in out["cases"].items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
