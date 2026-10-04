import os, sys, tempfile, json
sys.path.insert(0, os.getcwd())
from pathlib import Path
import pandas as pd
from scripts.ic1d_baseline_freeze import _build_advanced_config, prepare_real_kline_inputs
from momentum.Analysis import ic_filter_orchestrator as ifo
tmp = Path(tempfile.mkdtemp(prefix="fu2_"))
fp, lp, mp_, kr, src = prepare_real_kline_inputs(tmp)
orch = ifo.ICFilterOrchestrator(_build_advanced_config()); orch._suppress_persist = True
orch.analyze(features_path=str(fp), labels_path=str(lp), meta_path=str(mp_), kline_reader=kr)
c = orch._ic_cache["close_series"]; f = orch._ic_cache["features_df"]
raw = kr.read_klines(json.loads(Path(mp_).read_text())["symbol"], json.loads(Path(mp_).read_text())["timeframe"])
print(json.dumps({"close_len": len(c), "close_all_nan": bool(c.isna().all()), "close_nan_count": int(c.isna().sum()),
  "features_index_type": type(f.index).__name__, "features_index_head": [str(x) for x in f.index[:2]],
  "close_index_head": [str(x) for x in c.index[:2]], "raw_index_type": type(raw.index).__name__,
  "raw_index_head": [str(x) for x in raw.index[:2]], "raw_cols": list(raw.columns)[:8], "source_close_all_nan": bool(src.isna().all())}, indent=1))
