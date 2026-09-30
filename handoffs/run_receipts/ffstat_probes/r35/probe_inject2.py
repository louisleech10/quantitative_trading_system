"""可行性探針：§G⑦ 分解——B'＝B 起點但 L1 遮罩前之值換成 A 之同時點值；A 與 B' 於 B' 首個有限值起須全等。
用法：venv/bin/python probe_inject.py <tf> <source_dir> <small|default> [winsor_off]"""
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

REPO = Path("/Users/louis/Desktop/quantitative_trading_system")
sys.path.insert(0, str(REPO))
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402
from tests.feature_engineering import test_ffstat_golden as g  # noqa: E402
from momentum.FeatureEngineering.preprocessing import stable_mask as sm  # noqa: E402
from momentum.FeatureEngineering.feature_storage import FeatureStorage  # noqa: E402
from momentum.factories import create_feature_factory  # noqa: E402
from momentum.FeatureEngineering.warmup_window import _collect_l1_warmup_bars  # noqa: E402

tf, source = sys.argv[1], str(REPO / sys.argv[2])
payload = g._small_dual_start_payload() if sys.argv[3] in ("small", "dm") else {}
if sys.argv[3] == "mom":
    payload = {"atomic_indicators": {c: {"enabled": c == "momentum"} for c in (
        "trend", "volatility", "volume", "statistics", "cycle", "pattern", "tail_risk", "microstructure",
        "entropy", "momentum")}}
if sys.argv[3] == "dm":
    payload["atomic_indicators"]["momentum"]["indicators"] = [
        {"name": "PLUS_DM", "enabled": True, "periods": [233]},
        {"name": "MINUS_DM", "enabled": True, "periods": [55]},
    ]
    payload["operators"]["binary_signal"] = {"enabled": False, "rules": []}
if len(sys.argv) > 4 and sys.argv[4] == "winsor_off":
    payload = dict(payload)
    payload["preprocessing"] = {**payload.get("preprocessing", {}), "winsorization": {"enabled": False}}
symbol = h.SYMBOL
orig_mask = sm.apply_l1_mask

body = dict(payload)
body["timeframes"] = {"primary": tf, "training": [tf]}
for pre in ("fractional_differencing", "adf_differencing"):
    body.setdefault("preprocessing", {}).setdefault(pre, {})["enabled"] = False


def run(tmp: Path, label: str, drop: int, mp, mode: str, rec: dict):
    kdir = tmp / f"k_{label}"
    kdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(source) / "kline_cache.h5", kdir / "kline_cache.h5")
    if drop:
        import h5py
        with h5py.File(kdir / "kline_cache.h5", "r+") as f:
            grp = f[symbol][tf]
            arr = grp["data"][()]
            attrs = dict(grp["data"].attrs)
            del grp["data"]
            ds = grp.create_dataset("data", data=arr[drop:], maxshape=(None,), chunks=True)
            for k_, v in attrs.items():
                ds.attrs[k_] = v
    idx = {"i": 0, "bad": 0, "seen": {}, "own": []}

    def spy(values, origin, k):
        v = np.asarray(values, dtype=np.float64)
        spec = sys._getframe(1).f_locals.get("spec")
        label = f"{spec.engine}:{spec.indicator}:{spec.column}:{sorted(spec.params.items())}" if spec else "?"
        occ = idx["seen"].get(label, 0)
        idx["seen"][label] = occ + 1
        key = (label, occ)
        if mode == "record":
            rec[key] = v.copy()
        elif mode == "inject":
            idx["i"] += 1
            src = rec.get(key)
            if src is None or len(src) - len(v) != drop:
                idx["bad"] += 1
            else:
                idx["own"].append((key, orig_mask(v.copy(), origin, k), origin, int(k)))
                v = src[drop:].copy()
        return orig_mask(v, origin, k)

    mp.setattr(sm, "apply_l1_mask", spy)
    root = tmp / f"features_{label}"
    factory = create_feature_factory(cache_dir=str(kdir), validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    result = factory.generate_features(symbol, tf, config_override=body, force_regenerate=True,
                                       start_date=None, end_date=None, persist=True)
    mp.setattr(sm, "apply_l1_mask", orig_mask)
    cols = {}
    for p in sorted(root.rglob("*.parquet")):
        if p.name.endswith("_L65.parquet") or p.name == "timestamps.parquet":
            continue
        frame = pq.read_table(p).to_pandas()
        if "timestamp" in frame.columns:
            ix = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
        else:
            stamps = next(q for q in p.parents if (q / "timestamps.parquet").exists())
            ix = pd.to_datetime(pq.read_table(stamps / "timestamps.parquet").column("timestamp").to_numpy(), unit="s", utc=True)
        for n in frame.columns:
            if n not in ("timestamp", "__index_level_0__", "index"):
                cols[n] = pd.Series(frame[n].to_numpy(dtype=np.float64), index=ix)
    return cols, result, idx


mp = pytest.MonkeyPatch()
MUTANT = sys.argv[5] if len(sys.argv) > 5 else ""
if MUTANT == "pointwise":
    mp.setattr(sm, "mask_pointwise_prefix", lambda output, inputs: np.asarray(output, dtype=float).copy())
elif MUTANT == "winsor":
    mp.setattr(sm, "mask_incomplete_window_inplace", lambda values, window: values)
elif MUTANT == "l1mask":
    orig_mask = lambda values, origin, k: np.asarray(values, dtype=float).copy()  # noqa: E731
with tempfile.TemporaryDirectory(prefix=f"probe_inj_{tf}_") as t:
    tmp = Path(t)
    h.prepare_stat_env(mp, tmp)
    config = create_feature_factory(cache_dir=source, validate_continuity=False)._resolve_config(body)
    m = int(_collect_l1_warmup_bars(config))
    rec: dict = {}
    a, ares, _ = run(tmp, "a", 0, mp, "record", rec)
    shutil.rmtree(tmp / "features_a", ignore_errors=True)
    bp, _, idx = run(tmp, "bp", m, mp, "inject", rec)
    print("m", m, "l1_calls", len(rec), "inject_calls", idx["i"], "len_mismatch", idx["bad"])
    start_dep = set(ares.metadata.get(h.CONTRACT["start_dependent_key"], []))
    nonzero, mask_diff, compared, all_nan = {}, [], 0, 0
    for name, b in bp.items():
        if name in start_dep or name not in a:
            continue
        av = a[name].reindex(b.index).to_numpy()
        bv = b.to_numpy()
        fa, fb = np.isfinite(av), np.isfinite(bv)
        if not fb.any():
            all_nan += 1
            continue
        first = int(np.argmax(fb))
        if not np.array_equal(fa[first:], fb[first:]):
            mask_diff.append(name)
        both = fa & fb
        compared += 1
        d = np.abs(av[both] - bv[both])
        if d.size and d.max() > 0:
            nonzero[name] = (float(d.max()), int((d > 0).sum()), int(both.sum()))
    print("compared", compared, "all_nan", all_nan, "mask_diff", len(mask_diff), "nonzero", len(nonzero))
    TARGET = sys.argv[6] if len(sys.argv) > 6 else "PLUS-DM_233"
    pub = [n for n in a if n.endswith(TARGET) and "momentum" in n]
    print("TARGET public cols", pub)
    for key, vals in rec.items():
        if key[0].split("|")[0].endswith(TARGET) or TARGET in key[0]:
            v = vals
            print("REC", key, "len", len(v), "first_finite", int(np.argmax(np.isfinite(v))), "tail", v[-3:])
    for n in pub:
        av = a[n].to_numpy()
        bv = bp[n].to_numpy() if n in bp else None
        print("A_PUB", n, "len", len(av), "tail", av[-3:])
        if bv is not None:
            print("B_PUB", n, "len", len(bv), "tail", bv[-3:])
    own_t = [(k, o[-3:]) for k, o, _, _ in idx["own"] if TARGET in k[0]]
    print("B_OWN", own_t)
    for n in mask_diff[:15]:
        print("  MASK", n)
    for n, v in sorted(nonzero.items(), key=lambda kv: -kv[1][0])[:25]:
        print("  DIFF", n, v)
    # L1 本欄（遮罩前、未縮尾）：B 自身值於 origin+K 起與 A 同時點之 scale 正規化誤差
    l1_viol = {}
    for key, own, origin, k in idx["own"]:
        a_full = rec[key][m:]
        lo = int(np.argmax(np.isfinite(own))) if np.isfinite(own).any() else len(own)
        av, bv = a_full[lo:], own[lo:]
        both = np.isfinite(av) & np.isfinite(bv)
        if both.sum() < 1:
            continue
        ref = a_full[np.isfinite(a_full)]
        scale = max(float(np.percentile(np.abs(ref), 75)), float(np.std(ref)), 1e-8)
        err = float(np.max(np.abs(av[both] - bv[both])) / scale)
        if err > 0.005:
            first_bad = int(np.argmax(np.abs(av - bv) / scale > 0.005))
            l1_viol[f"{key[0]}#{key[1]}"] = (round(err, 5), k, first_bad)
    print("l1_own_checked", len(idx["own"]), "l1_own_viol", len(l1_viol))
    for n, v in sorted(l1_viol.items(), key=lambda kv: -kv[1][0])[:60]:
        print("  L1", n, v)
mp.undo()
