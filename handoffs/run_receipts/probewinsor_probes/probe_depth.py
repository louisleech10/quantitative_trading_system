"""PROBEWINSOR 偵察：公開域預熱探測（_resolve_public_window）之深度／晚到欄，現行碼 vs 模擬修正（前處理關 ⇒ 探測不縮尾）。

只跑探測、不跑完整生成、不落盤（探測之校準域暫存於系統暫存目錄，結束即刪）。真實 kline。
用法：python probe_depth.py <case> <mode current|fixed> <out.json>
case 見 CASES；mode=fixed 以 monkeypatch 模擬「_calibration_winsorizer 於 preprocessing.enabled=False 時回 None」。
"""
from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from momentum.factories import create_feature_factory  # noqa: E402
from momentum.FeatureEngineering.feature_factory import FeatureFactory  # noqa: E402
from momentum.FeatureEngineering.atomic.l1_output_points import check_config_coverage as check_l1_warmup_coverage  # noqa: E402
from tests.feature_engineering.fftfmeta_golden_helpers import fast_payload  # noqa: E402

KLINE_DIR = str(REPO / "data_cache" / "feature_klines")
SYMBOL = "BTCUSDT"
import os as _os

WINDOW = tuple(_os.environ.get("PW_WINDOW", "2026-01-01,2026-01-31").split(","))


def _payload(primary: str, training: list, pp_enabled: bool) -> dict:
    p = fast_payload(list(training), max_nan_ratio=1.0)
    p["timeframes"] = {"primary": primary, "training": list(training), "alignment_mode": "open_minus"}
    p["preprocessing"]["enabled"] = pp_enabled
    return p


def _short_payload(primary: str, training: list, pp_enabled: bool) -> dict:
    """短窗設定（ICFIRSTALIGN s2：只 close、trend EMA 8＋滾動 5／13）：D₀ 小，探測縮尾窗相對大。"""
    from tests.feature_engineering import icfirstalign_helpers as h

    p = h.s2_payload(list(training))
    p["timeframes"] = {"primary": primary, "training": list(training), "alignment_mode": "open_minus"}
    p["preprocessing"]["enabled"] = pp_enabled
    return p


def _l45(p: dict) -> dict:
    p["lag_features"] = {"enabled": True}
    p["cross_sectional"] = {"enabled": True, "reference_symbol": "ETHUSDT"}
    return p


def _deaddrop(p: dict) -> dict:
    p["nan_strategy"] = {"l7_dead_feature_drop": {"enabled": True}}
    return p


VARIANTS = {"_l45": _l45, "_dd": _deaddrop}


SHORT_CASES = {
    "e1h_off": ("1h", ["1h"], False),
    "e1h_on": ("1h", ["1h"], True),
    "e12h_off": ("12h", ["12h"], False),
    "e1h12h_off": ("1h", ["1h", "12h"], False),
    "e1h12h_on": ("1h", ["1h", "12h"], True),
}

CASES = {
    "s1h_off": ("1h", ["1h"], False),
    "s1h_on": ("1h", ["1h"], True),
    "s12h_off": ("12h", ["12h"], False),
    "m1h12h_off": ("1h", ["1h", "12h"], False),
    "m1h12h_on": ("1h", ["1h", "12h"], True),
    "m12h1h_off": ("12h", ["12h", "1h"], False),
}


def main() -> int:
    case, mode, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    primary, training, pp_enabled, build = resolve_case(case)
    return run_probe(case, mode, out, primary, training, pp_enabled, build)


def resolve_case(case: str):
    """case＝<基本格>[_l45|_dd]；回傳 (主週期, 訓練週期, 前處理開關, payload 建構函式)。"""
    variant = None
    for suffix in VARIANTS:
        if case.endswith(suffix):
            variant, case = VARIANTS[suffix], case[: -len(suffix)]
    if case in SHORT_CASES:
        primary, training, pp_enabled = SHORT_CASES[case]
        base = _short_payload
    else:
        primary, training, pp_enabled = CASES[case]
        base = _payload
    build = base if variant is None else (lambda p, t, e: variant(base(p, t, e)))
    return primary, training, pp_enabled, build


def run_probe(case, mode, out, primary, training, pp_enabled, build) -> int:
    if mode == "fixed":
        original = FeatureFactory._calibration_winsorizer

        def patched(self, config, timeframe):
            if not config.preprocessing.enabled:
                return None
            return original(self, config, timeframe)

        FeatureFactory._calibration_winsorizer = patched
    elif mode != "current":
        raise SystemExit(f"unknown mode {mode}")
    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    config = factory._resolve_config(build(primary, training, pp_enabled))
    check_l1_warmup_coverage(config)
    data_start = {}
    for tf in dict.fromkeys(training):
        data = factory._layer0_data_ingestion(SYMBOL, tf, config, start_date=None, end_date=WINDOW[1])
        data_start[tf] = str(factory._calibration_datetime_index(data.index)[0])
        del data
    t0 = time.time()
    window = factory._resolve_public_window(SYMBOL, primary, config, WINDOW[0], WINDOW[1])
    elapsed = time.time() - t0
    late = sorted(factory._public_warmup_late[1]) if factory._public_warmup_late else None
    first_finite = factory._public_warmup_first_finite
    ff_canon = json.dumps(first_finite, sort_keys=True, ensure_ascii=False)
    record = {
        "case": case,
        "mode": mode,
        "primary": primary,
        "training": training,
        "preprocessing_enabled": pp_enabled,
        "winsorization_enabled": bool(config.preprocessing.winsorization.enabled),
        "winsor_window": int(config.preprocessing.winsorization.window),
        "window": [WINDOW[0], WINDOW[1]],
        "data_start": data_start,
        "max_warmup_bars": int(window.max_warmup_bars),
        "ingest_start": window.ingest_start,
        "rounds": factory._public_warmup_probe,
        "late_count": None if late is None else len(late),
        "late_sha256": None if late is None else hashlib.sha256("\n".join(late).encode()).hexdigest(),
        "late_sample": None if late is None else late[:20],
        "first_finite_columns": {tf: len(v) for tf, v in first_finite.items()},
        "first_finite_sha256": hashlib.sha256(ff_canon.encode()).hexdigest(),
        "elapsed_seconds": round(elapsed, 2),
        "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 1),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    (out.with_suffix(".first_finite.json")).write_text(ff_canon, encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("case", "mode", "data_start", "max_warmup_bars", "ingest_start", "rounds", "late_count", "elapsed_seconds", "peak_rss_mb")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
