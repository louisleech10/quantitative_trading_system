"""以 v51 helper 跑 4h（或指定週期）之設定並摘要。用法：venv/bin/python helper_mom.py <tf> <mom|default|small> <out.json>"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path("/Users/louis/Desktop/quantitative_trading_system")
sys.path.insert(0, str(REPO))
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402
from tests.feature_engineering import test_ffstat_golden as g  # noqa: E402

tf, kind, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
if kind == "mom":
    payload = {"atomic_indicators": {c: {"enabled": c == "momentum"} for c in (
        "trend", "volatility", "volume", "statistics", "cycle", "pattern", "tail_risk", "microstructure",
        "entropy", "momentum")}}
elif kind == "small":
    payload = g._small_dual_start_payload()
else:
    payload = {}
source = str(REPO / h.CONTRACT["dual_start"]["timeframes"][tf])
mp = pytest.MonkeyPatch()
with tempfile.TemporaryDirectory(prefix=f"ffstat_v51_{tf}_") as tmp:
    try:
        h.prepare_stat_env(mp, Path(tmp))
        r = h.dual_start_report(Path(tmp), tf, payload, source)
    finally:
        mp.undo()
out.write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
print(tf, kind, {k: r.get(k) for k in ("rows", "m", "f_max", "margin", "eligible")})
for k in ("l1_violations", "l1_ineligible", "exact_violations", "mask_violations", "injection_unmatched",
          "dtype_differs", "all_nan"):
    v = r.get(k)
    print(k, len(v) if v is not None else None)
ev = sorted(r.get("exact_violations", {}).items(), key=lambda kv: -kv[1]["max_abs_diff"])
for n, v in ev[:20]:
    print("  EXACT", n, v)
for n, v in sorted(r.get("l1_violations", {}).items(), key=lambda kv: -(kv[1] if isinstance(kv[1], float) else 9))[:40]:
    print("  L1", n, v)
