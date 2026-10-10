"""PRE-RED 發現 F-4 查證：以凍結腳本之健康設定（365 天窗）於 cwd 之版本生成並落盤，印 L7 manifest 品質判定。

用法（cwd＝worktree；PYTHONHASHSEED=0）：venv/bin/python <本檔> <symbol> <tf>
"""

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))


def main(symbol: str, tf: str) -> None:
    spec = importlib.util.spec_from_file_location("freeze_failopen_baseline", ROOT / "scripts/freeze_failopen_baseline.py")
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    for k, v in freeze.FIXED_ENV.items():
        os.environ[k] = v
    from momentum.FeatureEngineering.feature_storage import FeatureStorage, resolve_run_status
    from momentum.factories import create_feature_factory

    start, end = freeze._window_dates()
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["FFACT_CGSA_WORK_DIR"] = str(Path(tmp) / "registry")
        f = create_feature_factory(cache_dir=str(freeze.KLINE_PATH.parent), validate_continuity=False)
        f._storage = FeatureStorage(str(Path(tmp) / "features"))
        res = f.generate_features(symbol=symbol, timeframe=tf, config_override=freeze._fixed_config_payload([tf], tf),
                                  force_regenerate=True, start_date=start, end_date=end, persist=True)
        for p in sorted(Path(tmp, "features").rglob("feature_manifest.json")):
            m = json.loads(p.read_text(encoding="utf-8"))
            arts = {k: {x: a.get(x) for x in ("quality_status", "failure_reasons")} for k, a in m.get("artifacts", {}).items()}
            print("L7 resolved=", resolve_run_status(m), json.dumps(arts, ensure_ascii=False)[:600])
        print("result", res.metadata.get("quality_status"), res.metadata.get("nan_ratio"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
