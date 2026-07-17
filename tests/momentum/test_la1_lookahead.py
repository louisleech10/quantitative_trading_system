"""LA-1 M-lookahead 測試（B0 骨架 + B1/B2/B3 填實）。

SPEC: docs/IC_LA1_SPEC.md
TODO: docs/IC_LA1_TODO.md Task 0.3 / Phase B1 / Phase B2

collect == 10:
  - test_regime_pit[rule]
  - test_regime_pit[kmeans]
  - test_regime_pit[mid_segment]
  - test_regime_pit_empty_vol
  - test_regime_fallback_truth_table
  - test_la1_b1_production_mutations_red
  - test_long_short_pit
  - test_long_short_fixed_q
  - test_return_nan_mask_invariance
  - test_fallback_loud_and_status

B1/B2 去 skip 填實；B3 fallback loud 已填。
collect 不觸 data_cache 副作用。
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.long_short_analyzer import LongShortAnalyzer
from momentum.Analysis.pit_stats import (
    effective_count,
    pit_expanding_quantile_thresholds,
)
from momentum.Analysis.regime_detector import RegimeDetectionResult, RegimeDetector
from momentum.core.exceptions import InvalidInputError
from momentum.factories import create_kline_storage_manager, create_regime_detector
from tests.golden.la1.attribution_validator import (
    load_allowlist,
    validate_diffs,
    validate_diffs_or_raise,
)
from tests.golden.la1.gen_baseline import (
    RUNS,
    _base_config_override,
    _hash_string_array,
    _resolve_la0_feature_inputs,
    _run_analyze,
    _summarize_by_regime,
)

LA1_GOLDEN_DIR = Path(__file__).resolve().parents[1] / "golden" / "la1"
ATTR_ALLOWLIST = LA1_GOLDEN_DIR / "attribution_allowlist.json"
BASELINE_BTC = LA1_GOLDEN_DIR / "BTCUSDT_1h_baseline.json"
BASELINE_ETH = LA1_GOLDEN_DIR / "ETHUSDT_12h_baseline.json"
GEN_BASELINE = LA1_GOLDEN_DIR / "gen_baseline.py"

ATOL = 1e-12
M_TRUNC_RATIO = 0.75
EARLY_WINDOW_RATIO = 2.0 / 3.0
REFIT_INTERVAL_CONST = 50
KLINE_CACHE_DIR = "data_cache/feature_klines"
SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"
SYMBOL_TF = f"{SYMBOL}/{TIMEFRAME}"

DEFAULT_RULE_CONFIG: Dict[str, Any] = {
    "regime_definitions": {
        "high_vol_percentile": 80,
        "low_vol_percentile": 20,
    },
    "method": "spearman",
}


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def la1_baseline_paths() -> Dict[str, Path]:
    """Task 0.1 inputs / baseline 路徑（collect 期不讀 data_cache）。"""
    return {
        "golden_dir": LA1_GOLDEN_DIR,
        "allowlist": ATTR_ALLOWLIST,
        "baseline_btc": BASELINE_BTC,
        "baseline_eth": BASELINE_ETH,
        "gen_baseline": GEN_BASELINE,
    }


@pytest.fixture(scope="module")
def la1_inputs_dir(la1_baseline_paths: Dict[str, Path]) -> Path:
    return la1_baseline_paths["golden_dir"] / "inputs"


@pytest.fixture(scope="module")
def btc_kline() -> pd.DataFrame:
    """真實 kline BTCUSDT/1h（禁合成 fixture）。"""
    sm = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    raw = sm.read_klines(SYMBOL, TIMEFRAME)
    assert raw is not None and not raw.empty
    assert len(raw) == 20352
    return raw


@pytest.fixture(scope="module")
def btc_close(btc_kline: pd.DataFrame) -> pd.Series:
    return btc_kline["close"].astype(float)


@pytest.fixture(scope="module")
def btc_volume(btc_kline: pd.DataFrame) -> pd.Series:
    return btc_kline["volume"].astype(float)


@pytest.fixture(scope="module")
def btc_baseline() -> dict:
    return json.loads(BASELINE_BTC.read_text(encoding="utf-8"))


def _m_trunc_n_keep(n: int) -> int:
    return int(M_TRUNC_RATIO * int(n))


def _early_window_end(n_keep: int) -> int:
    return int(EARLY_WINDOW_RATIO * int(n_keep))


def _rolling_vol(close: pd.Series, lookback: int = 55) -> pd.Series:
    return close.pct_change(fill_method=None).rolling(lookback).std()


def _legacy_vol_masks(close: pd.Series) -> Dict[str, pd.Series]:
    """改前全域 nanpercentile high/low + bull/bear（B0 baseline 同源）。"""
    ema_55 = close.ewm(span=55, adjust=False).mean()
    vol = _rolling_vol(close)
    vol_values = vol.dropna()
    if vol_values.empty:
        z = pd.Series(False, index=close.index)
        return {"bull": z, "bear": z, "high_vol": z, "low_vol": z}
    high_thresh = float(np.nanpercentile(vol_values, 80))
    low_thresh = float(np.nanpercentile(vol_values, 20))
    return {
        "bull": (close > ema_55).fillna(False),
        "bear": (close < ema_55).fillna(False),
        "high_vol": (vol >= high_thresh).fillna(False),
        "low_vol": (vol <= low_thresh).fillna(False),
    }


def _production_rule_masks(
    engine: ICEngine, close: pd.Series, config: Optional[dict] = None
) -> Dict[str, pd.Series]:
    """產線 mask：走 ``ICEngine._build_regime_rule_masks``（禁本地重算）。"""
    masks = engine._build_regime_rule_masks(close, config or DEFAULT_RULE_CONFIG)
    assert masks is not None, "production rule masks unexpectedly None"
    return masks


def _count_early_bool_flips(
    full_mask: pd.Series, trunc_mask: pd.Series, early_end: int
) -> int:
    n = min(early_end, len(full_mask), len(trunc_mask))
    flips = 0
    for i in range(n):
        if bool(full_mask.iloc[i]) != bool(trunc_mask.iloc[i]):
            flips += 1
    return flips


def _count_early_label_flips(
    full_labels: np.ndarray, trunc_labels: np.ndarray, early_end: int
) -> int:
    n = min(early_end, len(full_labels), len(trunc_labels))
    flips = 0
    for i in range(n):
        if str(full_labels[i]) != str(trunc_labels[i]):
            flips += 1
    return flips


def _assert_rule_pit_post_zero(
    engine: ICEngine, close: pd.Series, n_keep: int, early_end: int
) -> None:
    """產線 rule M-trunc early high/low flip == 0（mutation 共用斷言）。"""
    full_pit = _production_rule_masks(engine, close)
    trunc_pit = _production_rule_masks(engine, close.iloc[:n_keep])
    high_flip = _count_early_bool_flips(
        full_pit["high_vol"], trunc_pit["high_vol"], early_end
    )
    low_flip = _count_early_bool_flips(
        full_pit["low_vol"], trunc_pit["low_vol"], early_end
    )
    assert high_flip == 0, f"PIT high_vol early flip={high_flip}"
    assert low_flip == 0, f"PIT low_vol early flip={low_flip}"
    bull_flip = _count_early_bool_flips(
        full_pit["bull"], trunc_pit["bull"], early_end
    )
    bear_flip = _count_early_bool_flips(
        full_pit["bear"], trunc_pit["bear"], early_end
    )
    assert bull_flip == 0
    assert bear_flip == 0


def _assert_kmeans_pit_post_zero(
    detector: RegimeDetector,
    close: pd.Series,
    volume: pd.Series,
    n_keep: int,
    early_end: int,
) -> RegimeDetectionResult:
    """產線 RegimeDetector.detect(expanding=True) early flip==0 + 非全 unknown。"""
    full = detector.detect(close, volume, expanding=True)
    trunc = detector.detect(
        close.iloc[:n_keep], volume.iloc[:n_keep], expanding=True
    )
    flip_post = _count_early_label_flips(full.labels, trunc.labels, early_end)
    assert flip_post == 0, f"kmeans PIT early label flip={flip_post}"
    nontrivial = [
        str(x)
        for x in full.labels
        if str(x) not in ("", "unknown")
    ]
    assert len(nontrivial) > 0, "kmeans production labels all empty/unknown"
    assert len(set(nontrivial)) >= 2, "kmeans production labels lack diversity"
    return full


def _build_phase_attribution_diffs(
    new_labels: List[str],
    baseline_xg: dict,
    *,
    path_prefix: str,
    index: str = SYMBOL_TF,
    cls: str = "P1-1c",
) -> List[dict]:
    """產線 labels vs baseline → 五鍵 diff 列（sha + value_counts）。"""
    new_arr = [str(x) for x in new_labels]
    old_arr = [str(x) for x in (baseline_xg.get("labels") or [])]
    assert len(new_arr) == len(old_arr), (
        f"{path_prefix} label length mismatch new={len(new_arr)} old={len(old_arr)}"
    )
    diffs: List[dict] = []
    new_sha = _hash_string_array(new_arr)
    old_sha = baseline_xg.get("labels_sha256") or _hash_string_array(old_arr)
    if new_sha != old_sha:
        diffs.append(
            {
                "path": f"{path_prefix}.labels_sha256",
                "index": index,
                "old": old_sha,
                "new": new_sha,
                "class": cls,
            }
        )
    old_vc = baseline_xg.get("value_counts") or dict(Counter(old_arr))
    new_vc = dict(Counter(new_arr))
    for name in sorted(set(old_vc) | set(new_vc)):
        # 空字串 key 為 warmup 佔位，skip 避免 path 噪音；與 allowlist 一致
        if name == "":
            continue
        o = int(old_vc.get(name, 0))
        n = int(new_vc.get(name, 0))
        if o != n:
            diffs.append(
                {
                    "path": f"{path_prefix}.value_counts.{name}",
                    "index": name,
                    "old": o,
                    "new": n,
                    "class": cls,
                }
            )
    return diffs


def _scalar_differs(old: Any, new: Any) -> bool:
    """old/new 是否不同（NaN==NaN）。"""
    if old != new:
        if isinstance(old, float) and isinstance(new, float):
            if np.isnan(old) and np.isnan(new):
                return False
        return True
    return False


def _resolve_baseline_leaf(baseline: dict, path: str) -> tuple[bool, Any]:
    """dotted path 是否存在於 baseline；回傳 (found, leaf)。"""
    cur: Any = baseline
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def _allowlist_row_in_baseline_scope(row: dict, baseline: dict) -> bool:
    """列是否屬於本測 baseline 符號域（path 存在且 old==B0 leaf）。

    共享 allowlist 混有 BTC+ETH 真 diff：ETH feature 子集 path 不在 BTC
    baseline；同 path 的 value_sha256/value_counts 則以 old≠B0 區分。
    """
    path = str(row.get("path") or "")
    found, leaf = _resolve_baseline_leaf(baseline, path)
    if not found:
        return False
    return not _scalar_differs(leaf, row.get("old"))


def _build_regime_kmeans_attribution_diffs(
    baseline_km: dict,
    new_km: dict,
    *,
    cls: str = "P1-1c",
) -> List[dict]:
    """產線 kmeans grouped IC summarize vs baseline.regime_kmeans → 五鍵 diff。

    真實 schema：name_set_sha256 / regime_names / per_regime.*.
    （禁 labels_sha256 / value_counts phantom path。）
    """
    diffs: List[dict] = []
    old = baseline_km or {}
    new = new_km or {}

    def _add(path: str, index: Any, o: Any, n: Any) -> None:
        if _scalar_differs(o, n):
            diffs.append(
                {
                    "path": path,
                    "index": index,
                    "old": o,
                    "new": n,
                    "class": cls,
                }
            )

    _add(
        "regime_kmeans.name_set_sha256",
        SYMBOL_TF,
        old.get("name_set_sha256"),
        new.get("name_set_sha256"),
    )
    if old.get("regime_names") != new.get("regime_names"):
        _add(
            "regime_kmeans.regime_names",
            SYMBOL_TF,
            old.get("regime_names"),
            new.get("regime_names"),
        )

    old_pr = old.get("per_regime") or {}
    new_pr = new.get("per_regime") or {}
    for rname in sorted(set(old_pr) | set(new_pr)):
        oreg = old_pr.get(rname) or {}
        nreg = new_pr.get(rname) or {}
        for meta_k in (
            "feature_name_set_sha256",
            "n_features",
            "nan_mask_sha256",
            "value_sha256",
        ):
            _add(
                f"regime_kmeans.per_regime.{rname}.{meta_k}",
                rname,
                oreg.get(meta_k),
                nreg.get(meta_k),
            )
        opf = oreg.get("per_feature") or {}
        npf = nreg.get("per_feature") or {}
        for feat in sorted(set(opf) | set(npf)):
            oic = (opf.get(feat) or {}).get("ic")
            nic = (npf.get(feat) or {}).get("ic")
            _add(
                f"regime_kmeans.per_regime.{rname}.per_feature.{feat}.ic",
                f"{rname}/{feat}",
                oic,
                nic,
            )
    return diffs


def _assert_mid_segment_pit_post_zero(
    close: pd.Series, volume: pd.Series, refit_interval: int = REFIT_INTERVAL_CONST
) -> None:
    """mid-segment trunc：固定 refit 段界，early-in-segment flip==0。"""
    min_fit = 100
    prev_end = 150
    trunc_at = prev_end + refit_interval // 2  # 175 when interval=50
    assert trunc_at > prev_end
    need = trunc_at + refit_interval + 50
    assert len(close) > need

    det = RegimeDetector(
        n_clusters=4,
        lookback=55,
        min_samples_for_fit=min_fit,
        refit_interval=refit_interval,
    )
    full = det.detect(
        close.iloc[: need + 100], volume.iloc[: need + 100], expanding=True
    )
    trunc = det.detect(
        close.iloc[:trunc_at], volume.iloc[:trunc_at], expanding=True
    )
    nontrivial = [str(x) for x in full.labels if str(x) not in ("", "unknown")]
    assert len(nontrivial) > 0, "mid_segment labels all empty/unknown"

    seg_flips = 0
    for i in range(prev_end, trunc_at):
        if str(full.labels[i]) != str(trunc.labels[i]):
            seg_flips += 1
    assert seg_flips == 0, f"mid-segment early-in-segment flip={seg_flips}"


# ---------------------------------------------------------------------------
# B1 — regime PIT
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case", ["rule", "kmeans", "mid_segment"])
def test_regime_pit(
    case: str,
    la1_baseline_paths: Dict[str, Path],
    btc_close: pd.Series,
    btc_volume: pd.Series,
    btc_baseline: dict,
) -> None:
    """P1-1 / P1-1c：rule / kmeans / mid_segment M-trunc early flip。"""
    n = len(btc_close)
    n_keep = _m_trunc_n_keep(n)
    early_end = _early_window_end(n_keep)
    assert n_keep > 0 and early_end > 0

    if case == "rule":
        _assert_rule_pit(btc_close, n_keep, early_end, btc_baseline)
    elif case == "kmeans":
        _assert_kmeans_pit(
            btc_close,
            btc_volume,
            n_keep,
            early_end,
            btc_baseline,
            la1_baseline_paths["allowlist"],
        )
    elif case == "mid_segment":
        _assert_mid_segment_pit(btc_close, btc_volume)
    else:  # pragma: no cover
        raise AssertionError(f"unknown case {case!r}")


def _assert_rule_pit(
    close: pd.Series,
    n_keep: int,
    early_end: int,
    baseline: dict,
) -> None:
    engine = ICEngine({"method": "spearman"})

    # --- M-trunc: legacy early high/low flip 改前 > 0（產線改前語意）---
    full_leg = _legacy_vol_masks(close)
    trunc_leg = _legacy_vol_masks(close.iloc[:n_keep])
    high_flip_pre = _count_early_bool_flips(
        full_leg["high_vol"], trunc_leg["high_vol"], early_end
    )
    low_flip_pre = _count_early_bool_flips(
        full_leg["low_vol"], trunc_leg["low_vol"], early_end
    )
    assert high_flip_pre > 0, f"legacy high_vol early flip={high_flip_pre}"
    assert low_flip_pre > 0, f"legacy low_vol early flip={low_flip_pre}"

    # --- 產線 PIT 改後 early flip == 0（_build_regime_rule_masks）---
    _assert_rule_pit_post_zero(engine, close, n_keep, early_end)

    # --- hand-calc expanding p20/p80 vs numpy（真實 kline 前綴）---
    sub = close.iloc[:300]
    vol = _rolling_vol(sub)
    lo_t, hi_t = pit_expanding_quantile_thresholds(
        vol, lo_q=0.20, hi_q=0.80, min_samples=100
    )
    counts = effective_count(vol)
    valid_ts = np.flatnonzero(counts >= 100)
    assert valid_ts.size > 0
    sample_ts = valid_ts[:120]
    assert sample_ts.size > 0
    step = max(1, len(sample_ts) // 5)
    for t in sample_ts[::step]:
        t = int(t)
        finite = vol.iloc[: t + 1].to_numpy(dtype=float)
        finite = finite[np.isfinite(finite)]
        expected_lo = float(np.quantile(finite, 0.20))
        expected_hi = float(np.quantile(finite, 0.80))
        assert lo_t.iloc[t] == pytest.approx(expected_lo, abs=ATOL)
        assert hi_t.iloc[t] == pytest.approx(expected_hi, abs=ATOL)

    # --- percent 轉換 + 產線 _compute_regime_groups_rule 入口 ---
    features = pd.DataFrame(
        {"f0": close.iloc[:200].pct_change()}, index=close.index[:200]
    )
    label = close.iloc[:200].pct_change().shift(-1)
    result = engine._compute_regime_groups_rule(
        features.fillna(0.0),
        label.fillna(0.0),
        close.iloc[:200],
        DEFAULT_RULE_CONFIG,
    )
    assert isinstance(result, dict)
    assert set(result.keys()) >= {"bull", "bear", "high_vol", "low_vol"}
    # 產線 masks true_count 對 baseline allowlist 契約（high/low 必變、bull/bear 不變）
    prod_masks = _production_rule_masks(engine, close)
    base_mm = (
        (baseline.get("regime_rule") or {})
        .get("mask_membership", {})
        .get("regimes", {})
    )
    if base_mm:
        assert int(prod_masks["high_vol"].sum()) != int(
            base_mm["high_vol"]["true_count"]
        )
        assert int(prod_masks["low_vol"].sum()) != int(
            base_mm["low_vol"]["true_count"]
        )
        assert int(prod_masks["bull"].sum()) == int(base_mm["bull"]["true_count"])
        assert int(prod_masks["bear"].sum()) == int(base_mm["bear"]["true_count"])

    vol200 = _rolling_vol(close.iloc[:200])
    _lo200, hi200 = pit_expanding_quantile_thresholds(
        vol200, 0.20, 0.80, min_samples=100
    )
    t2 = int(np.flatnonzero(effective_count(vol200) >= 100)[0])
    finite2 = vol200.iloc[: t2 + 1].to_numpy(dtype=float)
    finite2 = finite2[np.isfinite(finite2)]
    assert hi200.iloc[t2] == pytest.approx(
        float(np.quantile(finite2, 0.8)), abs=ATOL
    )

    # --- 非法界：InvalidInputError（含 NaN / None）---
    bad_cfgs = [
        {"high_vol_percentile": 80, "low_vol_percentile": 110},
        {"high_vol_percentile": 30, "low_vol_percentile": 50},
        {"high_vol_percentile": float("nan"), "low_vol_percentile": 20},
        {"high_vol_percentile": 80, "low_vol_percentile": None},
    ]
    for defs in bad_cfgs:
        with pytest.raises(InvalidInputError):
            engine._compute_regime_groups_rule(
                features.fillna(0.0),
                label.fillna(0.0),
                close.iloc[:200],
                {"regime_definitions": defs},
            )


def _assert_kmeans_pit(
    close: pd.Series,
    volume: pd.Series,
    n_keep: int,
    early_end: int,
    baseline: dict,
    allowlist_path: Path,
) -> None:
    detector = create_regime_detector(
        n_clusters=4, lookback=55, min_samples_for_fit=100, refit_interval=50
    )
    assert detector.refit_interval == REFIT_INTERVAL_CONST
    # n-derived 與固定 50 必須可分（否則 mutation 無分辨力）
    n_derived = max(50, len(close) // 10)
    assert n_derived != REFIT_INTERVAL_CONST

    # --- legacy expanding=False（_fit_global）early flip > 0 ---
    full_leg = detector.detect(close, volume, expanding=False)
    trunc_leg = detector.detect(
        close.iloc[:n_keep], volume.iloc[:n_keep], expanding=False
    )
    flip_pre = _count_early_label_flips(full_leg.labels, trunc_leg.labels, early_end)
    assert flip_pre > 0, f"legacy global-fit early label flip={flip_pre}"

    # --- 產線 Segment-causal early flip == 0 ---
    full = _assert_kmeans_pit_post_zero(
        detector, close, volume, n_keep, early_end
    )

    # --- caller 層鎖：IC kmeans / XGBoost phases 固定 expanding=True ---
    expand_calls: List[bool] = []
    real_detect = RegimeDetector.detect

    def _spy_detect(self, close_s, volume_s=None, expanding=True):  # type: ignore[no-untyped-def]
        expand_calls.append(bool(expanding))
        return real_detect(self, close_s, volume_s, expanding=expanding)

    with mock.patch.object(RegimeDetector, "detect", _spy_detect):
        det2 = create_regime_detector(
            n_clusters=4, lookback=55, min_samples_for_fit=100, refit_interval=50
        )
        # 短序列加速 spy 驗證
        short_c, short_v = close.iloc[:400], volume.iloc[:400]
        _ = det2.detect_phases_for_index(short_c, short_v, index=short_c.index)
        engine = ICEngine({"method": "spearman"})
        feats = pd.DataFrame(
            {"f0": short_c.pct_change().fillna(0.0)}, index=short_c.index
        )
        lab = short_c.pct_change().fillna(0.0)
        raw = pd.DataFrame({"close": short_c, "volume": short_v})
        engine._compute_regime_groups_kmeans(
            feats,
            lab,
            short_c,
            raw,
            {
                "regime_kmeans": {
                    "n_clusters": 4,
                    "lookback": 55,
                    "min_samples_for_fit": 100,
                    "refit_interval": 50,
                },
                "method": "spearman",
            },
        )
    assert expand_calls, "expected detect calls from IC/XGBoost callers"
    assert all(c is True for c in expand_calls), expand_calls
    # 全域 expanding=False 仍允許（§N residual → P2 _fit_global）
    ok_global = detector.detect(
        close.iloc[:500], volume.iloc[:500], expanding=False
    )
    assert ok_global.method in ("kmeans", "rule")

    # --- FINDING-3：產線 detect_phases_for_index vs baseline exact allowlist ---
    # detect_phases_for_index 為 detect 薄封裝；短序列對齊後用全長 detect 真輸出建 diff
    short_n = 500
    short_c, short_v = close.iloc[:short_n], volume.iloc[:short_n]
    phases_short = detector.detect_phases_for_index(
        short_c, short_v, index=short_c.index
    )
    det_short = detector.detect(short_c, short_v, expanding=True)
    assert [str(x) for x in phases_short] == [str(x) for x in det_short.labels]

    phases = [str(x) for x in full.labels]
    baseline_xg = baseline.get("xgboost_phases") or {}
    baseline_labels = baseline_xg.get("labels") or []
    assert len(phases) == len(baseline_labels)
    n_diff = sum(1 for a, b in zip(phases, baseline_labels) if str(a) != str(b))
    assert n_diff > 0, "expected P1-1c phase label changes vs B0 baseline"

    # P1-1c 歸因：
    # ① xgboost_phases.*（labels_sha256/value_counts）
    # ② regime_kmeans.*（name_set_sha256/per_regime — 真跑 analyze kmeans 路徑）
    # 禁 labels_sha256 phantom under regime_kmeans（composer F-B1-001）。
    xgb_diffs = _build_phase_attribution_diffs(
        phases, baseline_xg, path_prefix="xgboost_phases"
    )
    btc_run = next(r for r in RUNS if r["symbol"] == SYMBOL)
    h5_path, meta_path = _resolve_la0_feature_inputs(btc_run)
    _orch_km, report_km = _run_analyze(
        h5_path, meta_path, _base_config_override("kmeans")
    )
    by_regime_km = (report_km.get("grouped_ic") or {}).get("by_regime") or {}
    new_km_payload = _summarize_by_regime(by_regime_km)
    baseline_km = baseline.get("regime_kmeans") or {}
    km_diffs = _build_regime_kmeans_attribution_diffs(baseline_km, new_km_payload)
    assert km_diffs, "expected P1-1c regime_kmeans leaf diffs vs B0 baseline"
    assert any(
        d["path"].endswith("value_sha256") for d in km_diffs
    ), "expected at least one per_regime value_sha256 diff"
    all_diffs = xgb_diffs + km_diffs
    allowlist = load_allowlist(allowlist_path)
    # Task 1.5：P1-1b 零 diff 須有 machine-readable 說明
    zdj = allowlist.get("zero_diff_justifications") or {}
    assert "P1-1b" in zdj, "missing zero_diff_justifications.P1-1b"
    p11b_rows = [r for r in (allowlist.get("rows") or []) if r.get("class") == "P1-1b"]
    assert p11b_rows == [], f"P1-1b expected zero rows, got {len(p11b_rows)}"
    result = validate_diffs(all_diffs, allowlist)
    assert result.ok, (
        f"unlisted={result.unexpected_count} "
        f"unexpected={result.unexpected[:3]!r} "
        f"format={result.format_errors[:3]!r}"
    )
    validate_diffs_or_raise(all_diffs, allowlist)

    # 反向：allowlist 中 **BTC-scoped** xgboost_phases + regime_kmeans P1-1c
    # 列皆須被本測 builder 真 diff 命中。
    #
    # 共享 allowlist 含 ETH recursive 補列（disjoint feature 子集 + 同 path
    # 不同 old 的 value_sha256/value_counts）。本測只跑 BTC/1h，builder 無法
    # 產出 ETH leaf → 反向只要求「path 在 BTC baseline 且 old==B0 leaf」。
    # 禁為綠刪 ETH 真 diff（B4 ETH forward 仍需那些列）。
    produced_keys = {
        (d["path"], d["index"], d["old"], d["new"], d["class"]) for d in all_diffs
    }
    required_prefixes = ("xgboost_phases.", "regime_kmeans.")
    n_km_allow = 0
    n_xgb_allow = 0
    n_cross_symbol_skipped = 0
    for row in allowlist.get("rows") or []:
        if row.get("class") != "P1-1c":
            continue
        path = str(row.get("path") or "")
        if not path.startswith(required_prefixes):
            continue
        if not _allowlist_row_in_baseline_scope(row, baseline):
            n_cross_symbol_skipped += 1
            continue
        if path.startswith("regime_kmeans."):
            n_km_allow += 1
        else:
            n_xgb_allow += 1
        key = (row["path"], row["index"], row["old"], row["new"], row["class"])
        assert key in produced_keys, f"allowlist P1-1c row not produced: {row}"
    assert n_km_allow > 0, "allowlist missing BTC-scoped regime_kmeans.* P1-1c rows"
    assert n_xgb_allow > 0, "allowlist missing BTC-scoped xgboost_phases.* P1-1c rows"
    # ETH-only / cross-symbol 補列必須存在於共享帳本（否則 B4 ETH 會紅），
    # 且不得被誤當 BTC reverse 必達。
    assert n_cross_symbol_skipped > 0, (
        "expected cross-symbol P1-1c rows in shared allowlist "
        f"(km ETH feats / ETH xgb); got skipped={n_cross_symbol_skipped}"
    )


def _assert_mid_segment_pit(close: pd.Series, volume: pd.Series) -> None:
    _assert_mid_segment_pit_post_zero(close, volume, REFIT_INTERVAL_CONST)


def test_regime_pit_empty_vol(
    la1_baseline_paths: Dict[str, Path],
    btc_close: pd.Series,
) -> None:
    """空 vol → by_regime == {}（Opt-A legacy guard）。"""
    engine = ICEngine({"method": "spearman"})
    short = btc_close.iloc[:40]
    features = pd.DataFrame(
        {"f0": short.pct_change().fillna(0.0)}, index=short.index
    )
    label = short.pct_change().fillna(0.0)
    out = engine._compute_regime_groups_rule(
        features,
        label,
        short,
        DEFAULT_RULE_CONFIG,
    )
    assert out == {}


def test_regime_fallback_truth_table(
    la1_baseline_paths: Dict[str, Path],
    btc_close: pd.Series,
    btc_volume: pd.Series,
) -> None:
    """P1-1b 產線 detect(fallback) 真值表三列 + M-trunc early flip==0。"""
    det = RegimeDetector(n_clusters=4, lookback=55, min_samples_for_fit=100)

    # ① len(vol_values)<2 → 產線 fallback 全 "unknown"
    tiny = btc_close.iloc[:3]
    tiny_vol = btc_volume.iloc[:3]
    features_tiny = det._build_features(tiny, tiny_vol)
    fb_tiny = det._fallback_rule_based(tiny, tiny_vol, features_tiny)
    assert fb_tiny.method == "rule"
    assert all(str(x) == "unknown" for x in fb_tiny.labels), list(fb_tiny.labels)

    # ② warmup bar → 產線 detect(method=rule) 不得 unknown
    # rolling(55) 後需 ≥100 有效 vol → 至少 ~154 bars；用 300 確保非 warmup 存在
    close_mid = btc_close.iloc[:300]
    vol_mid = btc_volume.iloc[:300]
    det_fb = RegimeDetector(
        n_clusters=4, lookback=55, min_samples_for_fit=10_000
    )
    result_fb = det_fb.detect(close_mid, vol_mid, expanding=True)
    assert result_fb.method == "rule"
    vol_series = _rolling_vol(close_mid)
    counts = effective_count(vol_series)
    warmup_idx = np.flatnonzero(counts < 100)
    assert warmup_idx.size > 0
    allowed_warmup = {
        "mid_vol_ranging",
        "mid_vol_trending",
        "high_vol_trending",
        "low_vol_ranging",
    }
    for i in warmup_idx:
        lab = str(result_fb.labels[i])
        if lab == "":
            continue
        assert lab != "unknown", f"warmup i={i} unexpected unknown"
        assert lab in allowed_warmup, f"warmup i={i} lab={lab}"

    # ③ 非 warmup → 產線 detect 輸出 == 產線 _compute_pit_rule_labels
    pit_labels = det_fb._compute_pit_rule_labels(close_mid, vol_mid)
    non_warmup = np.flatnonzero(counts >= 100)
    assert non_warmup.size > 0, (
        f"expected non-warmup bars; max effective_count="
        f"{int(counts.max()) if len(counts) else 0}"
    )
    for i in non_warmup[:50]:
        assert str(result_fb.labels[i]) == str(pit_labels[i]), (
            f"non-warmup i={i}: got={result_fb.labels[i]} exp={pit_labels[i]}"
        )

    # M-trunc early flip 改後 == 0（產線 detect 強制 fallback：min_fit > n）
    n = len(btc_close)
    n_keep = _m_trunc_n_keep(n)
    early_end = _early_window_end(n_keep)
    det_pit = RegimeDetector(
        n_clusters=4, lookback=55, min_samples_for_fit=max(n + 1, 10_000)
    )
    full_fb = det_pit.detect(btc_close, btc_volume, expanding=True)
    trunc_fb = det_pit.detect(
        btc_close.iloc[:n_keep], btc_volume.iloc[:n_keep], expanding=True
    )
    assert full_fb.method == "rule" and trunc_fb.method == "rule"
    flip = _count_early_label_flips(full_fb.labels, trunc_fb.labels, early_end)
    assert flip == 0, f"fallback PIT early label flip={flip}"


def test_la1_b1_production_mutations_red(
    btc_close: pd.Series,
    btc_volume: pd.Series,
) -> None:
    """FINDING-2：產線 mutant 必須打紅（全域門檻 / 全 unknown / 無 re-predict / n-derived）。"""
    n = len(btc_close)
    n_keep = _m_trunc_n_keep(n)
    early_end = _early_window_end(n_keep)
    engine = ICEngine({"method": "spearman"})

    # --- mutant 1: 全域 nanpercentile 門檻（假 PIT）---
    def _global_threshold_masks(
        self: ICEngine, close: pd.Series, config: dict
    ) -> Optional[Dict[str, pd.Series]]:
        return _legacy_vol_masks(close)

    with mock.patch.object(
        ICEngine, "_build_regime_rule_masks", _global_threshold_masks
    ):
        with pytest.raises(AssertionError):
            _assert_rule_pit_post_zero(engine, btc_close, n_keep, early_end)

    # --- mutant 2: detect → 全 unknown ---
    def _all_unknown_detect(
        self: RegimeDetector,
        close: pd.Series,
        volume: Optional[pd.Series] = None,
        expanding: bool = True,
    ) -> RegimeDetectionResult:
        return RegimeDetectionResult(
            labels=np.full(len(close), "unknown", dtype=object),
            n_clusters=self.n_clusters,
            cluster_centers=np.zeros((self.n_clusters, 1)),
            cluster_stats=[],
            method="kmeans",
            feature_names=["volatility"],
        )

    det = create_regime_detector(
        n_clusters=4, lookback=55, min_samples_for_fit=100, refit_interval=50
    )
    # 用短序列加速（mutant 不需全長）
    short_n = 800
    short_keep = int(M_TRUNC_RATIO * short_n)
    short_early = int(EARLY_WINDOW_RATIO * short_keep)
    with mock.patch.object(RegimeDetector, "detect", _all_unknown_detect):
        with pytest.raises(AssertionError):
            _assert_kmeans_pit_post_zero(
                det,
                btc_close.iloc[:short_n],
                btc_volume.iloc[:short_n],
                short_keep,
                short_early,
            )

    # --- mutant 3: 去 same-model re-predict → 退回全期 _fit_global 當 expanding ---
    real_fit_exp = RegimeDetector._fit_expanding

    def _no_repredict_expanding(
        self: RegimeDetector,
        valid_df: pd.DataFrame,
        close: Optional[pd.Series] = None,
        volume: Optional[pd.Series] = None,
    ) -> np.ndarray:
        # look-ahead：用全期 fit 取代 Segment-causal
        return self._fit_global(valid_df)

    with mock.patch.object(
        RegimeDetector, "_fit_expanding", _no_repredict_expanding
    ):
        with pytest.raises(AssertionError):
            _assert_kmeans_pit_post_zero(
                det,
                btc_close.iloc[:short_n],
                btc_volume.iloc[:short_n],
                short_keep,
                short_early,
            )

    # --- mutant 4: n-derived refit interval（M-trunc 改 n → 改 interval → early flip）---
    real_detect = RegimeDetector.detect

    def _n_derived_detect(
        self: RegimeDetector,
        close: pd.Series,
        volume: Optional[pd.Series] = None,
        expanding: bool = True,
    ) -> RegimeDetectionResult:
        if expanding:
            # 依最終 n 推導 interval（SPEC 禁止）
            self.refit_interval = max(50, len(close) // 10)
        return real_detect(self, close, volume, expanding=expanding)

    with mock.patch.object(RegimeDetector, "detect", _n_derived_detect):
        with pytest.raises(AssertionError):
            _assert_kmeans_pit_post_zero(
                det,
                btc_close.iloc[:short_n],
                btc_volume.iloc[:short_n],
                short_keep,
                short_early,
            )

    # 確保本測試未永久污染 detector.refit_interval
    det.refit_interval = REFIT_INTERVAL_CONST
    assert real_fit_exp is not None


# ---------------------------------------------------------------------------
# B2 — long_short PIT
# ---------------------------------------------------------------------------
def _legacy_global_qcut_bins(
    feature: pd.Series, future_returns: pd.Series, q: int = 5
) -> pd.Series:
    """改前語意：concat dropna 後全域 qcut（僅供 legacy flip>0 對照，非產線）。"""
    data = pd.concat(
        [feature.rename("f"), future_returns.rename("r")], axis=1
    ).dropna()
    if len(data) < q:
        return pd.Series(np.nan, index=feature.index, dtype=float)
    try:
        raw = pd.qcut(data["f"], q=q, labels=False, duplicates="drop")
    except ValueError:
        return pd.Series(np.nan, index=feature.index, dtype=float)
    return pd.Series(raw, index=data.index, dtype=float).reindex(feature.index)


def _count_early_float_label_flips(
    full_bins: pd.Series, trunc_bins: pd.Series, early_end: int
) -> int:
    n = min(early_end, len(full_bins), len(trunc_bins))
    flips = 0
    for i in range(n):
        a = full_bins.iloc[i]
        b = trunc_bins.iloc[i]
        a_nan = pd.isna(a)
        b_nan = pd.isna(b)
        if a_nan and b_nan:
            continue
        if a_nan != b_nan or float(a) != float(b):
            flips += 1
    return flips


def _series_equal_nan(a: pd.Series, b: pd.Series) -> int:
    """逐元素相等（NaN==NaN）；回傳 diff 個數。"""
    same = (a.isna() & b.isna()) | (
        a.notna()
        & b.notna()
        & (a.to_numpy(dtype=float) == b.to_numpy(dtype=float))
    )
    return int((~same).sum())


def _analyze_capture_bins(
    analyzer: LongShortAnalyzer,
    feature: pd.Series,
    future_returns: pd.Series,
    num_quantiles: int,
) -> Tuple[Any, pd.Series, pd.Series, pd.Series]:
    """經產線 analyze() 捕捉 bins/long_mask/short_mask（F-B2-001：禁只測 helper）。

    攔截 analyze→compute_side_masks 真呼叫，mutant 若在 analyze 對 feat 做
    ``feat.where(ret.notna())`` 會改寫 bins，本 helper 必見差。
    """
    captured: Dict[str, Any] = {}
    real_masks = analyzer.compute_side_masks

    def _spy(
        feat: pd.Series,
        fut: Optional[pd.Series] = None,
        num_q: Optional[int] = None,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        bins, long_m, short_m = real_masks(feat, fut, num_q)
        captured["bins"] = bins
        captured["long_mask"] = long_m
        captured["short_mask"] = short_m
        captured["feat_arg"] = pd.Series(feat, dtype=float).copy()
        return bins, long_m, short_m

    with mock.patch.object(analyzer, "compute_side_masks", _spy):
        result = analyzer.analyze(feature, future_returns, num_quantiles=num_quantiles)
    assert "bins" in captured, "analyze() did not call compute_side_masks"
    return (
        result,
        captured["bins"],
        captured["long_mask"],
        captured["short_mask"],
    )


def test_long_short_pit(
    la1_baseline_paths: Dict[str, Path],
    btc_close: pd.Series,
) -> None:
    """P1-2：產線 analyze() bins/mask — M-trunc early flip + reduced-bin 不建議。"""
    # 真實 kline 前綴（禁合成 fixture）；長度足以過 bin min_samples 且 M-trunc 可分辨
    n = 2000
    feature = btc_close.iloc[:n].astype(float)
    future_returns = feature.pct_change(-1)
    n_keep = _m_trunc_n_keep(n)
    early_end = _early_window_end(n_keep)
    assert n_keep > early_end > 100

    analyzer = LongShortAnalyzer(
        {
            "num_quantiles": 5,
            "long_quantiles": [4, 5],
            "short_quantiles": [1, 2],
        }
    )
    q = 5

    # --- legacy 全域 qcut（concat-dropna 後）early flip 改前 > 0 ---
    full_leg = _legacy_global_qcut_bins(feature, future_returns, q=q)
    trunc_leg = _legacy_global_qcut_bins(
        feature.iloc[:n_keep], future_returns.iloc[:n_keep], q=q
    )
    bin_flip_pre = _count_early_float_label_flips(full_leg, trunc_leg, early_end)
    assert bin_flip_pre > 0, f"legacy global qcut early bin flip={bin_flip_pre}"

    # --- 產線 analyze() PIT：early bin / long_mask flip == 0 ---
    full_out, full_bins, full_long, _fs = _analyze_capture_bins(
        analyzer, feature, future_returns, q
    )
    trunc_out, trunc_bins, trunc_long, _ts = _analyze_capture_bins(
        analyzer,
        feature.iloc[:n_keep],
        future_returns.iloc[:n_keep],
        q,
    )
    bin_flip_post = _count_early_float_label_flips(full_bins, trunc_bins, early_end)
    assert bin_flip_post == 0, f"PIT early bin flip={bin_flip_post}"
    long_flip = _count_early_bool_flips(full_long, trunc_long, early_end)
    assert long_flip == 0, f"PIT early long_mask flip={long_flip}"

    # 產線 analyze() 真輸出
    assert isinstance(full_out, dict), f"unexpected skip: {full_out!r}"
    assert full_out["num_quantiles_used"] == q
    assert full_out["recommendation"] in (
        "雙向交易",
        "只做多",
        "只做空",
        "不建議",
    )
    assert isinstance(trunc_out, dict)
    assert trunc_out["num_quantiles_used"] == q

    # --- reduced-bin：2-unique × q=5 → 產線 bins isna + 雙側空 + recommendation==不建議 ---
    # n 足夠（≥100）→ 非 SkippedResult；僅結構 n_feat<100 才 cannot form quantiles
    med = float(feature.median())
    two_level = feature.apply(lambda x: 0.0 if x < med else 1.0)
    red_result, red_bins, red_long, red_short = _analyze_capture_bins(
        analyzer, two_level, future_returns, q
    )
    post_warm = red_bins.iloc[100:]
    assert int(post_warm.notna().sum()) == 0, (
        f"reduced-bin expected all-NaN post-warmup, got "
        f"{int(post_warm.notna().sum())} labels"
    )
    assert isinstance(red_result, dict), (
        f"reduced-bin with n={n}>=100 must not SkippedResult, got {red_result!r}"
    )
    assert red_result["long_analysis"]["samples"] == 0
    assert red_result["short_analysis"]["samples"] == 0
    assert np.isnan(red_result["long_analysis"]["mean_return"])
    assert np.isnan(red_result["short_analysis"]["mean_return"])
    assert np.isnan(red_result["long_analysis"]["ic"])
    assert np.isnan(red_result["short_analysis"]["ic"])
    assert red_result["recommendation"] == "不建議"
    assert red_result["num_quantiles_used"] == q
    assert not bool(red_long.any())
    assert not bool(red_short.any())

    # --- batch_analyze 真輸出（同 reduced-bin 語意）---
    batch = analyzer.batch_analyze(
        pd.DataFrame({"f0": two_level}),
        future_returns,
        top_n=1,
    )
    assert "f0" in batch
    assert batch["f0"].get("skipped") is not True
    assert batch["f0"]["recommendation"] == "不建議"
    assert batch["f0"]["long_analysis"]["samples"] == 0
    assert batch["f0"]["short_analysis"]["samples"] == 0

    # --- 重複 timestamp 邊界：analyze 不炸 ---
    if len(feature) >= 200:
        dup_feature = pd.Series(
            feature.iloc[:200].to_numpy(),
            index=list(range(100)) + list(range(100)),
            dtype=float,
        )
        dup_ret = pd.Series(
            future_returns.iloc[:200].to_numpy(),
            index=dup_feature.index,
            dtype=float,
        )
        dup_out, dup_bins, _, _ = _analyze_capture_bins(
            analyzer, dup_feature, dup_ret, q
        )
        assert len(dup_bins) == len(dup_feature)
        assert isinstance(dup_out, (dict, SkippedResult))

    # --- ±inf future_returns 不進 metrics（F-B2-004）---
    ret_inf = future_returns.copy()
    ret_inf.iloc[150:160] = np.inf
    ret_inf.iloc[160:170] = -np.inf
    inf_out, _, _, _ = _analyze_capture_bins(analyzer, feature, ret_inf, q)
    assert isinstance(inf_out, dict), f"unexpected skip with ±inf returns: {inf_out!r}"
    for side in ("long_analysis", "short_analysis"):
        mr = inf_out[side]["mean_return"]
        assert mr is None or (isinstance(mr, float) and np.isnan(mr)) or np.isfinite(
            mr
        ), f"{side}.mean_return not finite/NaN: {mr!r}"
        assert int(inf_out[side]["samples"]) >= 0


def test_long_short_fixed_q(
    la1_baseline_paths: Dict[str, Path],
    btc_close: pd.Series,
) -> None:
    """n≥200 → 產線 analyze() num_quantiles_used==5（固定 q，禁降 q）。"""
    n = 220
    feature = btc_close.iloc[:n].astype(float)
    future_returns = feature.pct_change(-1)
    analyzer = LongShortAnalyzer(config={"num_quantiles": 5})
    result, bins, _, _ = _analyze_capture_bins(analyzer, feature, future_returns, 5)
    assert isinstance(result, dict), f"unexpected skip: {result!r}"
    assert result["num_quantiles_used"] == 5
    assert int(bins.notna().sum()) > 0
    # 常數尾端（legacy 降 q 觸發點）仍報固定 q
    const_tail = feature.copy()
    const_tail.iloc[-40:] = float(const_tail.iloc[-41])
    result_const, _, _, _ = _analyze_capture_bins(
        analyzer, const_tail, future_returns, 5
    )
    if isinstance(result_const, dict):
        assert result_const["num_quantiles_used"] == 5


def test_return_nan_mask_invariance(
    la1_baseline_paths: Dict[str, Path],
    btc_close: pd.Series,
) -> None:
    """竄改未來報酬 NaN 分布 → 產線 analyze() bins 逐元素相等（RB-3；不等=FAIL）。

    核心斷言走 analyze() 真路徑（F-B2-001）：mutant 若 analyze 內
    ``compute_side_masks(feat.where(ret.notna()), …)`` 必改 bins → 本測紅。
    """
    n = 800
    feature = btc_close.iloc[:n].astype(float)
    base_ret = feature.pct_change(-1)
    analyzer = LongShortAnalyzer(config={"num_quantiles": 5})

    out_base, bins_base, _, _ = _analyze_capture_bins(
        analyzer, feature, base_ret, 5
    )
    assert isinstance(out_base, dict)

    # mutation A：尾端 returns 全 NaN
    ret_a = base_ret.copy()
    ret_a.iloc[int(0.5 * n) :] = np.nan
    out_a, bins_a, _, _ = _analyze_capture_bins(analyzer, feature, ret_a, 5)

    # mutation B：交錯 NaN mask
    ret_b = base_ret.copy()
    ret_b.iloc[::3] = np.nan
    out_b, bins_b, _, _ = _analyze_capture_bins(analyzer, feature, ret_b, 5)

    # mutation C：幾乎全 NaN returns（僅保留前 50；仍過 module min_samples=30）
    ret_c = base_ret.copy()
    ret_c.iloc[50:] = np.nan
    out_c, bins_c, _, _ = _analyze_capture_bins(analyzer, feature, ret_c, 5)

    for name, bins_m, out_m in (
        ("A", bins_a, out_a),
        ("B", bins_b, out_b),
        ("C", bins_c, out_c),
    ):
        n_diff = _series_equal_nan(bins_base, bins_m)
        assert n_diff == 0, (
            f"return-NaN mask mutation {name} changed {n_diff} bins via analyze() "
            f"(RB-3 leak: bins depend on future_returns)"
        )
        # metrics 可變；analyze 必須可跑（dict 或 samples 不足 skip）
        assert isinstance(out_m, (dict, SkippedResult))

    # batch_analyze 同 invariance：兩 mask 下 skipped/num_quantiles 結構可解析
    df = pd.DataFrame({"x": feature})
    batch_a = analyzer.batch_analyze(df, ret_a, top_n=1)
    batch_b = analyzer.batch_analyze(df, ret_b, top_n=1)
    assert "x" in batch_a and "x" in batch_b



# ---------------------------------------------------------------------------
# B3 — fallback loud（已填實；保留與並行 B3 相容）
# ---------------------------------------------------------------------------
def _find_fallback_inputs(inputs_dir: Path) -> tuple[Path, Path]:
    """定位 B0 物化的 BTC fallback_tail100 features + meta。"""
    candidates = sorted(inputs_dir.glob("BTCUSDT_*_fallback_tail100.h5"))
    if not candidates:
        pytest.fail(f"no fallback_tail100 h5 under {inputs_dir}")
    h5 = candidates[0]
    meta = h5.with_name(h5.stem + "_meta.json")
    if not meta.is_file():
        alt = inputs_dir / f"{h5.stem}_meta.json"
        meta = alt if alt.is_file() else meta
    if not meta.is_file():
        pytest.fail(f"fallback meta missing for {h5.name}")
    return h5, meta


def _find_ok_inputs(inputs_dir: Path) -> tuple[Path, Path]:
    """定位非 fallback 的 BTC tail2000 輸入（非觸發路徑）。"""
    candidates = sorted(
        p
        for p in inputs_dir.glob("BTCUSDT_*_tail2000.h5")
        if "fallback" not in p.name
    )
    if not candidates:
        pytest.fail(f"no BTC tail2000 h5 under {inputs_dir}")
    h5 = candidates[0]
    meta = inputs_dir / f"{h5.stem}_meta.json"
    if not meta.is_file():
        pytest.fail(f"ok-path meta missing for {h5.name}")
    return h5, meta


def test_fallback_loud_and_status(
    la1_baseline_paths: Dict[str, Path],
    caplog: Any,
) -> None:
    """P1-3：root analysis_status / oos_guarantees / caplog warning / 禁內層 persist。"""
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager
    from tests.golden.la1.gen_baseline import _isolate_orchestrator_persist

    inputs_dir = la1_baseline_paths["golden_dir"] / "inputs"
    short_h5, short_meta = _find_fallback_inputs(inputs_dir)
    ok_h5, ok_meta = _find_ok_inputs(inputs_dir)

    orch = create_ic_analyzer()
    tmp = _isolate_orchestrator_persist(orch)
    persist_calls: List[int] = []
    orig_persist = orch._persist_outputs

    def _counting_persist(*args: Any, **kwargs: Any) -> Any:
        persist_calls.append(1)
        return orig_persist(*args, **kwargs)

    orch._persist_outputs = _counting_persist  # type: ignore[method-assign]
    kline_reader = create_kline_storage_manager(cache_dir="data_cache/feature_klines")

    with caplog.at_level(
        logging.WARNING, logger="momentum.Analysis.ic_filter_orchestrator"
    ):
        report_fb = orch.analyze(
            features_path=str(short_h5.resolve()),
            labels_path="",
            meta_path=str(short_meta.resolve()),
            config_override={
                "ic_train_test_split": True,
                "min_test_rows": 10_000,
                "thresholds": {
                    "ic_mean_min": -1.0,
                    "icir_min": -1.0,
                    "p_value_max": 1.0,
                    "ic_hit_rate_min": 0.0,
                    "monotonicity_score_min": 0.0,
                    "coverage_min": 0.0,
                    "long_short_spread": {"enabled": False},
                },
            },
            kline_reader=kline_reader,
        )

    assert report_fb.get("analysis_status") == "degraded_full_sample"
    assert report_fb.get("oos_guarantees") is False
    assert (report_fb.get("metadata") or {}).get("oos_guarantees") is False
    assert (report_fb.get("metadata") or {}).get("fit_mode") == "full_sample"

    warning_text = " ".join(
        r.message for r in caplog.records if r.levelno >= logging.WARNING
    )
    assert (
        "full-sample fallback" in warning_text.lower()
        or "fallback" in warning_text.lower()
    )
    assert any(
        "reason"
        in (r.getMessage() if hasattr(r, "getMessage") else str(r.message)).lower()
        or "insufficient"
        in (r.getMessage() if hasattr(r, "getMessage") else str(r.message)).lower()
        or "fit_mode"
        in (r.getMessage() if hasattr(r, "getMessage") else str(r.message)).lower()
        for r in caplog.records
        if r.levelno >= logging.WARNING
    )

    assert len(persist_calls) == 1, (
        f"expected single wrapper persist, got {len(persist_calls)}"
    )

    for row in report_fb.get("summary_table") or []:
        if isinstance(row, dict):
            assert row.get("pass_class") == "full_sample_research_only"

    orch_ok = create_ic_analyzer()
    _isolate_orchestrator_persist(orch_ok)
    report_ok = orch_ok.analyze(
        features_path=str(ok_h5.resolve()),
        labels_path="",
        meta_path=str(ok_meta.resolve()),
        config_override={
            "ic_train_test_split": True,
            "thresholds": {
                "ic_mean_min": -1.0,
                "icir_min": -1.0,
                "p_value_max": 1.0,
                "ic_hit_rate_min": 0.0,
                "monotonicity_score_min": 0.0,
                "coverage_min": 0.0,
                "long_short_spread": {"enabled": False},
            },
            "grouped_analysis": {"by_regime": False},
            "report": {"include_regime_analysis": False},
        },
        kline_reader=kline_reader,
    )
    assert report_ok.get("analysis_status") == "ok_oos"
    assert report_ok.get("oos_guarantees") is True
    for row in report_ok.get("summary_table") or []:
        if isinstance(row, dict):
            assert row.get("pass_class") == "oos"

    assert tmp.exists()
