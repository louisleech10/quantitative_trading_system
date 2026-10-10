"""PRE-RED 探針：於 cwd 之 repo 版本跑凍結腳本之 _multi_tf_record（BTCUSDT），輸出 merged_L7 五分量與 group／feature 摘要。

用法（須 PYTHONHASHSEED=0）：venv/bin/python <本檔> <輸出 json>
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))


def main(out: str) -> int:
    assert os.environ.get("PYTHONHASHSEED") == "0"
    spec = importlib.util.spec_from_file_location("freeze_failopen_baseline", ROOT / "scripts/freeze_failopen_baseline.py")
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    for k, v in freeze.FIXED_ENV.items():
        os.environ[k] = v
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        rec = freeze._multi_tf_record("BTCUSDT", Path(tmp))
    m = rec["merged_L7"]
    keys = ("canonical_sha256", "column_order_sha256", "dtypes_sha256", "index_sha256", "values_sha256",
            "nan_mask_sha256", "rows", "columns", "nan_count")
    summary = {"elapsed_seconds": round(time.perf_counter() - t0, 1), "config_hash": rec["config_hash"],
               "feature_count": rec["feature_count"], "group_set_sha256": rec["group_set_sha256"],
               "merged_L7": {k: m.get(k) for k in keys}}
    Path(out).write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("elapsed", summary["elapsed_seconds"], "merged", m["canonical_sha256"][:8], "groups", rec["group_set_sha256"][:8],
          "features", rec["feature_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
