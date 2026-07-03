"""P0-FF-2/P0-FF-3 共用 — 全鏈截斷 MR helper（gates/抽樣/build pair）。

從 test_ff_fullchain_truncation_mr.py 抽出；B2 與 multi-TF MR 共用。
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Literal, Optional, Set, Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.operators.lag_processor import LagProcessor
from momentum.FeatureEngineering.preprocessing._d_star_cache import read_d_star_json
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner
from momentum.FeatureEngineering.warmup_window import estimate_max_warmup_bars
from momentum.factories import create_feature_factory, create_kline_storage_manager

_ORIGINAL_BUILD_ASOF_INDEX_MAP = TimeframeAligner.build_asof_index_map
AlignLookaheadSide = Literal["full", "trunc"]

ROOT = Path(__file__).resolve().parents[2]
KLINE_CACHE_DIR = "data_cache/feature_klines"
SYMBOL = "BTCUSDT"
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_PRIMARY_TF = "1h"
SYMBOL = DEFAULT_SYMBOL
TIMEFRAME = DEFAULT_PRIMARY_TF
TRUNC_K = 10
ALIGN_MARGIN = 12  # 12h // 1h; multi-TF window padding

POST_WARMUP_BARS = 20
FRACDIFF_MIN_BARS = 600
PERTURB_DELTA = 1e6
FRACDIFF_ATOL = 1e-8
# 與 feature_storage.FLOAT16_MAX_REL_ERROR(1e-3)對齊,但取 2× 餘量:
# 同一 causal 值在 full(float32-stored,≈true)vs trunc(float16-stored,≤1e-3 from true)
# 之間最多差 ~1e-3;rtol 設恰好 1e-3 會卡邊界假紅(實測 LINEARREG-ANGLE rel_err=9.999e-4)。
# 2e-3 安全避開邊界,且真 look-ahead(mutation 實證 >>0.1%)仍遠超此容差被抓。
FLOAT16_RTOL = 2e-3
FLOAT16_ATOL = 1e-12
# 主 MR columns gate：不對稱掉欄門檻 max(100, 0.1%×|union|)（三方收斂 B2 設計）
COLUMNS_ASYMMETRIC_MIN = 100
COLUMNS_ASYMMETRIC_PCT = 0.001
# NaN mask 分層：高 fill_rate 欄須 exact mask；低 fill_rate 僅 informational
HIGH_FILL_RATE_THRESHOLD = 0.95
# 覆蓋率守衛：防全欄歸 informational 空轉
COVERAGE_COLUMN_FRACTION = 0.95
# B2 比對效能：分層抽樣（見 handoffs/20260629-FF-B2-PERF-RECONCILE.md）
B2_SAMPLE_K_DEFAULT = 40
B2_SAMPLE_MIN_COLUMNS = 3000
B2_SAMPLE_MAX_COLUMNS = 8000
B2_SAMPLE_VERSION = "B2-MR-v1"

_COARSE_TF_TAG = re.compile(r"_(4h|12h)_", re.IGNORECASE)

_L3_SUFFIX_RE = re.compile(r"_([^_]+)_W(\d+)$", re.IGNORECASE)
_L4_LAG_SUFFIX_RE = re.compile(r"_Lag_(\d+)$", re.IGNORECASE)
_CHUNK_STEM_RE = re.compile(r"_(\d+)$")
_L2_OPERATOR_TOKENS = (
    "decay_linear",
    "ts_argmax",
    "ts_argmin",
    "ts_corr",
    "ts_rank",
    "_Momentum_L",
    "_Ratio",
    "_Distance",
    "_Cross",
    "BinarySignal",
    "SignedStrength",
)
_L65_TYPE_TOKENS = (
    ("winsor", "winsor"),
    ("rank", "rank"),
    ("zscore", "zscore"),
    ("gaussian", "gaussian"),
    ("fracdiff", "fracdiff"),
)
# append 模式：winsor 原位寫入 L1–L6 原欄；L65 parquet 僅含 rank/zscore/gaussian 追加欄。
_WINSOR_PROBE_LAYERS = frozenset({"L1", "L2", "L3", "L4", "L5", "L6"})

_ALL_ATOMIC_CATEGORIES = (
    "trend",
    "momentum",
    "volatility",
    "volume",
    "statistics",
    "cycle",
    "pattern",
    "tail_risk",
    "microstructure",
    "entropy",
)

_ADAPTIVE_ZSCORE_WINDOWS = [
    20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200,
    220, 240, 260, 280, 320, 360,
]

FIXED_ENV = {
    "FFACT_LAYER1_PARALLEL": "0",
    "FFACT_USE_CGSA": "1",
    "FFACT_USE_POLARS": "1",
    "FFACT_L3_PERSIST_MODE": "streaming",
    "FFACT_MULTI_TF_PARALLEL": "0",
}


@dataclass(frozen=True)
class GenerationArtifacts:
    """單次 generate_features(persist=True) 的 L7 raw 產物與 metadata。"""

    raw_dir: Path
    run_dir: Path
    metadata: Dict[str, Any]
    manifest: Dict[str, Any]
    row_count: int
    d_star_path: Optional[Path] = None


@dataclass(frozen=True)
class TruncationPair:
    """full vs trunc 成對產物（同 start、trunc 少尾 k bars）。"""

    warmup: int
    n_trunc: int
    full: GenerationArtifacts
    trunc: GenerationArtifacts


def _required_window_bars(
    config_payload: Dict[str, Any],
    *,
    primary_tf: str = DEFAULT_PRIMARY_TF,
    training_tfs: Optional[List[str]] = None,
    min_post_warmup: int = POST_WARMUP_BARS,
    align_margin: int = 0,
) -> int:
    """窗長 ≥ config-driven warmup + trunc_k + 可比較後綴 (+ 可選 multi-TF align margin)。"""
    if training_tfs is None:
        training_tfs = [primary_tf]
    factory = create_feature_factory(cache_dir=KLINE_CACHE_DIR, validate_continuity=False)
    config = factory._resolve_config(config_payload)
    warmup = estimate_max_warmup_bars(config, primary_tf, training_tfs)
    return int(warmup + TRUNC_K + min_post_warmup + align_margin)


def _fracdiff_window_bars(config_payload: Dict[str, Any]) -> int:
    """fracdiff MR 須同時滿足 calibration 窗與全鏈 warmup。"""
    return max(FRACDIFF_MIN_BARS, _required_window_bars(config_payload))


def _atomic_indicators_all_enabled() -> Dict[str, Dict[str, bool]]:
    return {category: {"enabled": True} for category in _ALL_ATOMIC_CATEGORIES}


def _mr_nan_strategy() -> Dict[str, Any]:
    """關閉 L7 dead_drop：min_valid 依總列數，會讓 columns gate 假紅（非 look-ahead）。"""
    return {"l7_dead_feature_drop": {"enabled": False}}


def _values_gate_mr_config_payload(
    *,
    primary_tf: str = DEFAULT_PRIMARY_TF,
    training_tfs: Optional[List[str]] = None,
    alignment_mode: str = "open_minus",
) -> Dict[str, Any]:
    """明確全開（不呼叫 apply_preset）；主 MR 排除 fracdiff/adf，gaussian 納入。"""
    if training_tfs is None:
        training_tfs = [primary_tf]
    return {
        "timeframes": {
            "primary": primary_tf,
            "training": list(training_tfs),
            "alignment_mode": alignment_mode,
        },
        "cross_sectional": {"enabled": False},
        "atomic_indicators": _atomic_indicators_all_enabled(),
        "preprocessing": {
            "enabled": True,
            "mode": "append",
            "causal_preprocessing": True,
            "winsorization": {"enabled": True},
            "rank_transform": {"enabled": True},
            "adaptive_zscore": {
                "enabled": True,
                "windows": _ADAPTIVE_ZSCORE_WINDOWS,
            },
            "gaussian_normalize": {"enabled": True},
            "adf_differencing": {"enabled": False},
            "fractional_differencing": {"enabled": False},
        },
        "nan_strategy": _mr_nan_strategy(),
    }


def _fracdiff_mr_config_payload() -> Dict[str, Any]:
    """fracdiff 專屬 MR：全 atomic，L6.5 僅 fracdiff（加速）；窗須 ≥ calibration_bars。"""
    return {
        "timeframes": {
            "primary": TIMEFRAME,
            "training": [TIMEFRAME],
            "alignment_mode": "open_minus",
        },
        "cross_sectional": {"enabled": False},
        "atomic_indicators": _atomic_indicators_all_enabled(),
        "preprocessing": {
            "enabled": True,
            "mode": "append",
            "causal_preprocessing": True,
            "calibration_bars": 500,
            "winsorization": {"enabled": False},
            "rank_transform": {"enabled": False},
            "adaptive_zscore": {"enabled": False},
            "gaussian_normalize": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "fractional_differencing": {
                "enabled": True,
                "cache_d_star": True,
                "apply_to": "non_stationary",
            },
        },
        "nan_strategy": _mr_nan_strategy(),
    }


def _bar_window_dates(
    kline_df: pd.DataFrame,
    *,
    window_bars: int,
    trunc_k: int,
) -> Tuple[str, str, str]:
    """由真 kline timestamp 欄推算 full/trunc end（bar 級 ISO，非事後 :-k 切片）。"""
    if len(kline_df) < window_bars:
        pytest.fail(f"requires_kline: need >={window_bars} rows, got {len(kline_df)}")
    window = kline_df.iloc[-window_bars:]
    ts = window["timestamp"].astype(np.int64)

    def _iso(epoch: int) -> str:
        return pd.Timestamp(int(epoch), unit="s").strftime("%Y-%m-%d %H:%M:%S")

    start = _iso(int(ts.iloc[0]))
    full_end = _iso(int(ts.iloc[-1]))
    trunc_end = _iso(int(ts.iloc[-(trunc_k + 1)]))
    return start, full_end, trunc_end


def _is_12h_close_boundary_bar_open(ts_epoch: int) -> bool:
    """1h bar open 時間戳：其 close 落在 12h grid（align mutation 邊界選窗）。"""
    h1 = TIMEFRAME_SECONDS["1h"]
    h12 = TIMEFRAME_SECONDS["12h"]
    return (int(ts_epoch) + h1) % h12 == 0


def _bar_window_dates_at_12h_boundary(
    kline_df: pd.DataFrame,
    *,
    window_bars: int,
    trunc_k: int,
) -> Tuple[str, str, str]:
    """選 full_end 落 12h 收盤邊界的窗（align look-ahead mutation 必要）。"""
    if len(kline_df) < window_bars:
        pytest.fail(f"requires_kline: need >={window_bars} rows, got {len(kline_df)}")
    if trunc_k <= 0 or trunc_k >= 12:
        pytest.fail(f"12h-boundary window requires 0 < trunc_k < 12, got {trunc_k}")

    ts_all = kline_df["timestamp"].astype(np.int64).to_numpy()

    def _iso(epoch: int) -> str:
        return pd.Timestamp(int(epoch), unit="s").strftime("%Y-%m-%d %H:%M:%S")

    for end_idx in range(len(ts_all) - 1, window_bars - 2, -1):
        last_ts = int(ts_all[end_idx])
        if not _is_12h_close_boundary_bar_open(last_ts):
            continue
        start_idx = end_idx - window_bars + 1
        if start_idx < 0:
            break
        window_ts = ts_all[start_idx : end_idx + 1]
        start = _iso(int(window_ts[0]))
        full_end = _iso(last_ts)
        trunc_end = _iso(int(window_ts[-(trunc_k + 1)]))
        return start, full_end, trunc_end

    pytest.fail(
        f"no 12h-close-boundary window of {window_bars} bars found in kline "
        f"(trunc_k={trunc_k})"
    )


def _apply_fixed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in FIXED_ENV.items():
        monkeypatch.setenv(name, value)


def _ensure_module_env() -> None:
    for name, value in FIXED_ENV.items():
        os.environ[name] = value


def _make_factory(features_root: Path, *, d_star_dir: Optional[Path] = None):
    _ensure_module_env()
    factory = create_feature_factory(cache_dir=KLINE_CACHE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(features_root))
    if d_star_dir is not None:
        FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: d_star_dir)  # type: ignore[method-assign]
    return factory


def _run_generation(
    factory,
    *,
    features_root: Path,
    config_payload: Dict[str, Any],
    start_date: str,
    end_date: str,
    symbol: str = DEFAULT_SYMBOL,
    primary_tf: str = DEFAULT_PRIMARY_TF,
    d_star_dir: Optional[Path] = None,
) -> GenerationArtifacts:
    if d_star_dir is not None:
        d_star_dir.mkdir(parents=True, exist_ok=True)
        FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: d_star_dir)  # type: ignore[method-assign]
    result = factory.generate_features(
        symbol,
        primary_tf,
        config_override=config_payload,
        force_regenerate=True,
        start_date=start_date,
        end_date=end_date,
        persist=True,
    )
    config_hash = str(result.metadata["config_hash"])
    run_dir = features_root / symbol / primary_tf / config_hash
    raw_dir = run_dir / "raw"
    manifest_path = run_dir / "feature_manifest.json"
    if not raw_dir.is_dir():
        pytest.fail(f"L7 raw dir missing after persist=True: {raw_dir}")
    if not manifest_path.is_file():
        pytest.fail(f"feature_manifest.json missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row_count = int(manifest.get("row_count") or len(result.features_df.index))
    d_star_path: Optional[Path] = None
    if d_star_dir is not None:
        candidates = sorted(d_star_dir.glob(f"d_star_{symbol}_{primary_tf}_*.json"))
        if candidates:
            d_star_path = candidates[-1]
    return GenerationArtifacts(
        raw_dir=raw_dir,
        run_dir=run_dir,
        metadata=dict(result.metadata),
        manifest=manifest,
        row_count=row_count,
        d_star_path=d_star_path,
    )


def _iter_raw_parquet_frames(raw_dir: Path) -> Iterator[Tuple[str, pd.DataFrame]]:
    for path in sorted(raw_dir.glob("*.parquet")):
        if path.name == "timestamps.parquet":
            continue
        yield path.name, pd.read_parquet(path)


def _collect_column_names(raw_dir: Path) -> List[str]:
    names: List[str] = []
    for _, frame in _iter_raw_parquet_frames(raw_dir):
        names.extend(str(col) for col in frame.columns)
    return names


def _build_column_frame_map(raw_dir: Path) -> Dict[str, Tuple[str, str]]:
    """欄名 → (parquet 檔名, 欄名)。"""
    mapping: Dict[str, Tuple[str, str]] = {}
    for fname, frame in _iter_raw_parquet_frames(raw_dir):
        for col in frame.columns:
            mapping[str(col)] = (fname, str(col))
    return mapping


@dataclass(frozen=True)
class SamplingReport:
    """分層抽樣摘要（供覆蓋率守衛與驗收輸出）。"""

    version: str
    total_common: int
    sampled_count: int
    group_count: int
    fallback_count: int
    required_probe_count: int
    parquet_file_count: int


def _parquet_stem(fname: str) -> str:
    return fname[:-8] if fname.endswith(".parquet") else fname


def _chunk_class_from_stem(stem: str) -> str:
    """L3/L4 chunked parquet 去尾 `_\\d+` 得語義 class（避免只抽第一 chunk）。"""
    return _CHUNK_STEM_RE.sub("", stem)


def _layer_from_stem(stem: str) -> str:
    """由 parquet stem 解析 layer token（L1–L6、L65）；stem 含 L65 時優先。"""
    parts = stem.split("_")
    if any(part in {"L65", "L6.5"} for part in parts):
        return "L65"
    for part in parts:
        if part.startswith("L") and len(part) > 1:
            suffix = part[1:]
            if suffix.replace(".", "", 1).isdigit():
                return "L65" if suffix in {"6.5", "65"} else part
    return "L?"


def _infer_l2_operator(col: str) -> str:
    lowered = col.lower()
    for token in _L2_OPERATOR_TOKENS:
        if token.lower() in lowered:
            return token.lstrip("_").split("_")[0] if token.startswith("_") else token
    return "derived"


def _infer_l65_type(col: str) -> str:
    lowered = col.lower()
    for needle, label in _L65_TYPE_TOKENS:
        if needle in lowered:
            return label
    return "raw_passthrough"


def _is_winsor_probe_layer(layer: str) -> bool:
    """winsor mutation 探針須覆蓋原位 winsor 欄（非 L65 追加欄）。"""
    return layer in _WINSOR_PROBE_LAYERS


def _build_strat_group_key(col: str, parquet_fname: str) -> Tuple[Any, ...]:
    """分層抽樣分組鍵：parquet stem + 欄名 suffix。"""
    stem = _parquet_stem(parquet_fname)
    layer = _layer_from_stem(stem)
    parts = stem.split("_")

    if layer == "L1" and len(parts) >= 4:
        return (layer, parts[2], parts[3])
    if layer == "L2" and len(parts) >= 3:
        return (layer, parts[2], _infer_l2_operator(col))
    if layer == "L3":
        match = _L3_SUFFIX_RE.search(col)
        if match:
            return (layer, match.group(1).lower(), int(match.group(2)))
        return (layer, "unknown", hash(col) % 997)
    if layer == "L4":
        match = _L4_LAG_SUFFIX_RE.search(col)
        if match:
            return (layer, int(match.group(1)))
        return (layer, "unknown", hash(col) % 997)
    if layer in {"L5", "L6"}:
        indicator = parts[3] if len(parts) >= 4 else "unknown"
        return (layer, _chunk_class_from_stem(stem), indicator)
    if layer == "L65":
        return (layer, _infer_l65_type(col), _chunk_class_from_stem(stem))

    return (layer, "unknown", hash(col) % 997)


def _stride_sample_with_boundaries(cols: List[str], k: int) -> List[str]:
    """確定性 stride 抽樣 + first/middle/last 邊界樣本。"""
    ordered = sorted(cols)
    if not ordered:
        return []
    if len(ordered) <= k:
        return ordered
    stride = max(1, len(ordered) // k)
    picked: List[str] = list(ordered[0::stride][:k])
    for idx in (0, len(ordered) // 2, len(ordered) - 1):
        boundary = ordered[idx]
        if boundary not in picked:
            picked.append(boundary)
    return sorted(set(picked))


def _align_probe_priority(col: str) -> int:
    """粗 TF 探針優先 close/volume 類（high-fill）。"""
    lowered = col.lower()
    if "close" in lowered:
        return 0
    if "volume" in lowered:
        return 1
    return 2


def _coarse_tf_from_column(col: str) -> Optional[str]:
    match = _COARSE_TF_TAG.search(col)
    return match.group(1).lower() if match else None


def _select_required_probe_columns(
    common_cols: List[str],
    col_to_parquet: Dict[str, Tuple[str, str]],
    *,
    align_coarse_tfs: Optional[List[str]] = None,
) -> List[str]:
    """mutation 硬保證：L3 mean 族、L4 lag_1、L6.5 winsor；可選粗 TF 對齊欄。"""
    probes: Set[str] = set()

    l3_mean_candidates: List[str] = []
    l4_lag1_candidates: List[str] = []
    winsor_probe_candidates: List[str] = []
    align_candidates: Dict[str, List[str]] = {}

    for col in common_cols:
        loc = col_to_parquet.get(col)
        if loc is None:
            continue
        fname, _ = loc
        stem = _parquet_stem(fname)
        layer = _layer_from_stem(stem)
        lowered = col.lower()

        coarse_tf = _coarse_tf_from_column(col)
        if align_coarse_tfs and coarse_tf in align_coarse_tfs:
            align_candidates.setdefault(coarse_tf, []).append(col)

        if layer == "L3" and "_mean_w" in lowered:
            l3_mean_candidates.append(col)
        elif layer == "L3" and not l3_mean_candidates:
            match = _L3_SUFFIX_RE.search(col)
            if match and match.group(1).lower() == "mean":
                l3_mean_candidates.append(col)

        if layer == "L4":
            match = _L4_LAG_SUFFIX_RE.search(col)
            if match and int(match.group(1)) == 1:
                l4_lag1_candidates.append(col)
            elif match and not l4_lag1_candidates:
                l4_lag1_candidates.append(col)

        if _is_winsor_probe_layer(layer):
            winsor_probe_candidates.append(col)

    if l3_mean_candidates:
        probes.add(sorted(l3_mean_candidates)[0])
    if l4_lag1_candidates:
        probes.add(sorted(l4_lag1_candidates)[0])
    if not l3_mean_candidates and winsor_probe_candidates:
        probes.add(sorted(winsor_probe_candidates)[0])

    if align_coarse_tfs:
        for tf in align_coarse_tfs:
            candidates = align_candidates.get(tf, [])
            if candidates:
                probes.add(
                    sorted(candidates, key=lambda c: (_align_probe_priority(c), c))[0]
                )

    return sorted(probes)


def _cap_sampled_columns(sampled: List[str], cap: int) -> List[str]:
    """超過上限時等權 stride 裁切（保留順序穩定）。"""
    if len(sampled) <= cap:
        return sampled
    ordered = sorted(sampled)
    stride = max(1, len(ordered) // cap)
    return ordered[0::stride][:cap]


def _build_sampled_columns(
    common_cols: List[str],
    col_to_parquet: Dict[str, Tuple[str, str]],
    *,
    align_coarse_tfs: Optional[List[str]] = None,
) -> Tuple[List[str], SamplingReport]:
    """分層抽樣 ∪ required-probe；共用於 values / NaN mask / warmup。"""
    groups: Dict[Tuple[Any, ...], List[str]] = {}
    fallback_count = 0

    for col in common_cols:
        loc = col_to_parquet.get(col)
        if loc is None:
            continue
        key = _build_strat_group_key(col, loc[0])
        if key[1] == "unknown":
            fallback_count += 1
        groups.setdefault(key, []).append(col)

    sampled: Set[str] = set()
    for cols in groups.values():
        k = min(B2_SAMPLE_K_DEFAULT, len(cols))
        sampled.update(_stride_sample_with_boundaries(cols, k))

    # 每個 parquet 檔至少 1 欄（chunk 覆蓋）
    by_parquet: Dict[str, List[str]] = {}
    for col in common_cols:
        loc = col_to_parquet.get(col)
        if loc is None:
            continue
        by_parquet.setdefault(loc[0], []).append(col)
    for cols in by_parquet.values():
        sampled.add(sorted(cols)[0])

    required = _select_required_probe_columns(
        common_cols, col_to_parquet, align_coarse_tfs=align_coarse_tfs
    )
    sampled.update(required)

    sampled_list = _cap_sampled_columns(sorted(sampled), B2_SAMPLE_MAX_COLUMNS)

    if len(sampled_list) < B2_SAMPLE_MIN_COLUMNS and len(common_cols) >= B2_SAMPLE_MIN_COLUMNS:
        extra_stride = max(1, len(common_cols) // B2_SAMPLE_MIN_COLUMNS)
        sampled_list = sorted(
            set(sampled_list) | set(sorted(common_cols)[0::extra_stride])
        )
        sampled_list = _cap_sampled_columns(sampled_list, B2_SAMPLE_MAX_COLUMNS)
        if len(sampled_list) < B2_SAMPLE_MIN_COLUMNS:
            sampled_list = sorted(common_cols)[:B2_SAMPLE_MIN_COLUMNS]

    report = SamplingReport(
        version=B2_SAMPLE_VERSION,
        total_common=len(common_cols),
        sampled_count=len(sampled_list),
        group_count=len(groups),
        fallback_count=fallback_count,
        required_probe_count=len(required),
        parquet_file_count=len(by_parquet),
    )
    return sampled_list, report


def _assert_mutation_layer_coverage(
    sampled_cols: List[str],
    col_to_parquet: Dict[str, Tuple[str, str]],
    *,
    align_coarse_tfs: Optional[List[str]] = None,
) -> None:
    """mutation 層覆蓋 sanity：缺層 = 測試設計錯，不准假綠。"""
    layers_present: Set[str] = set()
    has_winsor = False
    coarse_present: Set[str] = set()
    for col in sampled_cols:
        loc = col_to_parquet.get(col)
        if loc is None:
            continue
        layer = _layer_from_stem(_parquet_stem(loc[0]))
        layers_present.add(layer)
        if _is_winsor_probe_layer(layer):
            has_winsor = True
        coarse = _coarse_tf_from_column(col)
        if coarse:
            coarse_present.add(coarse)

    missing: List[str] = []
    if "L3" not in layers_present:
        missing.append("L3")
    if "L4" not in layers_present:
        missing.append("L4")
    if not has_winsor:
        missing.append("L65_winsor")
    if align_coarse_tfs:
        for tf in align_coarse_tfs:
            if tf not in coarse_present:
                missing.append(f"alignment({tf})")
    if missing:
        raise AssertionError(
            "mutation layer coverage failed (sampling design error): "
            f"missing {missing} in sampled set"
        )


def _group_sampled_by_parquet(
    sampled_cols: List[str],
    col_to_parquet: Dict[str, Tuple[str, str]],
) -> Dict[str, List[str]]:
    """抽樣欄按 parquet 檔分桶（batch 讀前置）。"""
    buckets: Dict[str, List[str]] = {}
    for col in sampled_cols:
        loc = col_to_parquet.get(col)
        if loc is None:
            continue
        buckets.setdefault(loc[0], []).append(col)
    return buckets


def _read_parquet_columns(path: Path, columns: List[str]) -> pd.DataFrame:
    """單檔批次讀取指定欄（消除逐欄 read_parquet）。"""
    if not columns:
        return pd.DataFrame()
    return pd.read_parquet(path, columns=sorted(set(columns)))


def _log_sampling_report(report: SamplingReport) -> None:
    print(
        f"B2 sampling [{report.version}]: "
        f"sampled={report.sampled_count}/{report.total_common} common, "
        f"groups={report.group_count}, parquet_files={report.parquet_file_count}, "
        f"fallback={report.fallback_count}, required_probes={report.required_probe_count}"
    )


def _fill_rate(segment: np.ndarray) -> float:
    """區段非 NaN 比例。"""
    if segment.size == 0:
        return 0.0
    return float(np.sum(~np.isnan(segment))) / float(segment.size)


def _assert_arrays_values_close(
    left: np.ndarray,
    right: np.ndarray,
    *,
    context: str = "",
    rtol: float = FLOAT16_RTOL,
    atol: float = FLOAT16_ATOL,
) -> None:
    """值因果穩定（容差內）：NaN mask exact；不檢查 dtype（float16↔float32 翻面合法）。"""
    lnan = np.isnan(left)
    rnan = np.isnan(right)
    assert np.array_equal(lnan, rnan), f"{context} NaN mask mismatch"
    finite = ~lnan
    if finite.any():
        left_f = left[finite].astype(np.float32, copy=False)
        right_f = right[finite].astype(np.float32, copy=False)
        if not np.allclose(left_f, right_f, rtol=rtol, atol=atol):
            diff = np.abs(left_f - right_f)
            rel = diff / np.maximum(np.abs(left_f), np.finfo(np.float32).tiny)
            worst = int(np.argmax(rel))
            idx = int(np.where(finite)[0][worst])
            raise AssertionError(
                f"{context} values mismatch at index {idx}: "
                f"{left[idx]!r} vs {right[idx]!r} "
                f"(rel_err={rel[worst]:.3e}, rtol={rtol}, atol={atol})"
            )


def _assert_values_both_non_nan_close(
    left: np.ndarray,
    right: np.ndarray,
    *,
    context: str = "",
    rtol: float = FLOAT16_RTOL,
    atol: float = FLOAT16_ATOL,
) -> None:
    """僅比 both-non-NaN 位置（主 MR values gate）。"""
    both_finite = ~np.isnan(left) & ~np.isnan(right)
    if not both_finite.any():
        return
    left_f = left[both_finite].astype(np.float32, copy=False)
    right_f = right[both_finite].astype(np.float32, copy=False)
    if not np.allclose(left_f, right_f, rtol=rtol, atol=atol):
        diff = np.abs(left_f - right_f)
        rel = diff / np.maximum(np.abs(left_f), np.finfo(np.float32).tiny)
        worst = int(np.argmax(rel))
        idx = int(np.where(both_finite)[0][worst])
        raise AssertionError(
            f"{context} values mismatch at index {idx}: "
            f"{left[idx]!r} vs {right[idx]!r} "
            f"(rel_err={rel[worst]:.3e}, rtol={rtol}, atol={atol})"
        )


def _assert_nan_mask_layered(
    left: np.ndarray,
    right: np.ndarray,
    *,
    context: str,
    fill_rate_left: float,
    fill_rate_right: float,
) -> None:
    """高 fill_rate(≥95%) 共同欄 → NaN mask exact；否則 informational。"""
    lnan = np.isnan(left)
    rnan = np.isnan(right)
    if np.array_equal(lnan, rnan):
        return
    if (
        fill_rate_left >= HIGH_FILL_RATE_THRESHOLD
        and fill_rate_right >= HIGH_FILL_RATE_THRESHOLD
    ):
        raise AssertionError(
            f"{context} high-fill-rate NaN mask mismatch "
            f"(fill_rate full={fill_rate_left:.3f} trunc={fill_rate_right:.3f})"
        )
    print(
        f"NaN mask informational {context}: "
        f"fill_rate full={fill_rate_left:.3f} trunc={fill_rate_right:.3f}"
    )


def _diagnose_column_mismatch(full_cols: List[str], trunc_cols: List[str]) -> str:
    only_full = sorted(set(full_cols) - set(trunc_cols))
    only_trunc = sorted(set(trunc_cols) - set(full_cols))
    lines = [
        f"only_in_full={len(only_full)} only_in_trunc={len(only_trunc)}",
        f"sample only_full: {only_full[:8]}",
        f"sample only_trunc: {only_trunc[:8]}",
    ]
    return "\n".join(lines)


def _assert_columns_gate(full_dir: Path, trunc_dir: Path, *, strict: bool = False) -> None:
    full_cols = _collect_column_names(full_dir)
    trunc_cols = _collect_column_names(trunc_dir)
    if strict:
        if full_cols != trunc_cols:
            raise AssertionError(
                "columns gate failed (strict):\n"
                + _diagnose_column_mismatch(full_cols, trunc_cols)
            )
        return

    full_set = set(full_cols)
    trunc_set = set(trunc_cols)
    union = full_set | trunc_set
    only_full = sorted(full_set - trunc_set)
    only_trunc = sorted(trunc_set - full_set)
    asymmetric_count = len(only_full) + len(only_trunc)
    threshold = max(COLUMNS_ASYMMETRIC_MIN, int(COLUMNS_ASYMMETRIC_PCT * len(union)))

    if asymmetric_count > threshold:
        samples = (only_full + only_trunc)[:10]
        raise AssertionError(
            "columns gate failed: "
            f"asymmetric={asymmetric_count} > threshold={threshold} "
            f"(union={len(union)})\n"
            f"only_in_full={len(only_full)} only_in_trunc={len(only_trunc)}\n"
            f"sample asymmetric columns: {samples}"
        )

    if asymmetric_count > 0:
        samples = (only_full + only_trunc)[:10]
        print(
            "columns gate (informational): "
            f"asymmetric={asymmetric_count} <= threshold={threshold} "
            f"sample={samples}"
        )


def _assert_warmup_nan_masks_equal(
    full_dir: Path,
    trunc_dir: Path,
    *,
    warmup: int,
    n_trunc: int,
    intersection_only: bool = False,
    sampled_cols: Optional[List[str]] = None,
    col_to_parquet: Optional[Dict[str, Tuple[str, str]]] = None,
) -> None:
    """warmup 區 [0:warmup) NaN mask 一致（2.1/2.2 共用）；抽樣集與 values gate 共用。"""
    if warmup <= 0:
        return

    if sampled_cols is not None and col_to_parquet is not None:
        for fname, cols in _group_sampled_by_parquet(sampled_cols, col_to_parquet).items():
            trunc_path = trunc_dir / fname
            if not trunc_path.is_file():
                continue
            full_frame = _read_parquet_columns(full_dir / fname, cols)
            trunc_frame = _read_parquet_columns(trunc_path, cols)
            for col in cols:
                if col not in full_frame.columns or col not in trunc_frame.columns:
                    continue
                full_vals = full_frame[col].to_numpy()[:n_trunc]
                trunc_vals = trunc_frame[col].to_numpy()
                _assert_arrays_values_close(
                    full_vals[:warmup],
                    trunc_vals[:warmup],
                    context=f"warmup {fname}::{col}",
                )
        return

    for fname, full_frame in _iter_raw_parquet_frames(full_dir):
        trunc_path = trunc_dir / fname
        if not trunc_path.is_file():
            continue
        trunc_frame = pd.read_parquet(trunc_path)
        if intersection_only:
            common_cols = set(full_frame.columns) & set(trunc_frame.columns)
            cols_to_check = [col for col in full_frame.columns if col in common_cols]
        else:
            assert list(full_frame.columns) == list(trunc_frame.columns)
            cols_to_check = list(full_frame.columns)
        for col in cols_to_check:
            full_vals = full_frame[col].to_numpy()[:n_trunc]
            trunc_vals = trunc_frame[col].to_numpy()
            _assert_arrays_values_close(
                full_vals[:warmup],
                trunc_vals[:warmup],
                context=f"warmup {fname}::{col}",
            )


def _assert_values_gate_main(
    full_dir: Path,
    trunc_dir: Path,
    *,
    warmup: int,
    n_trunc: int,
    align_coarse_tfs: Optional[List[str]] = None,
) -> Tuple[List[str], Dict[str, Tuple[str, str]]]:
    """主 MR values gate：交集欄分層抽樣、batch parquet 讀、both-non-NaN 比對、覆蓋率守衛。"""
    if warmup >= n_trunc:
        pytest.fail("no post-warmup rows in truncation window")

    full_cols = set(_collect_column_names(full_dir))
    trunc_cols = set(_collect_column_names(trunc_dir))
    common_cols = sorted(full_cols & trunc_cols)
    if not common_cols:
        pytest.fail("values gate: no common columns between full and trunc")

    full_map = _build_column_frame_map(full_dir)
    sampled_cols, report = _build_sampled_columns(
        common_cols, full_map, align_coarse_tfs=align_coarse_tfs
    )
    if report.sampled_count < B2_SAMPLE_MIN_COLUMNS and len(common_cols) >= B2_SAMPLE_MIN_COLUMNS:
        pytest.fail(
            f"sampling guard failed: sampled={report.sampled_count} < min={B2_SAMPLE_MIN_COLUMNS}"
        )
    _assert_mutation_layer_coverage(
        sampled_cols, full_map, align_coarse_tfs=align_coarse_tfs
    )
    _log_sampling_report(report)

    comparable_columns = 0
    for fname, cols in _group_sampled_by_parquet(sampled_cols, full_map).items():
        trunc_path = trunc_dir / fname
        if not trunc_path.is_file():
            continue
        full_frame = _read_parquet_columns(full_dir / fname, cols)
        trunc_frame = _read_parquet_columns(trunc_path, cols)
        for col in cols:
            if col not in full_frame.columns or col not in trunc_frame.columns:
                continue
            full_slice = full_frame[col].to_numpy()[:n_trunc]
            trunc_slice = trunc_frame[col].to_numpy()
            segment_full = full_slice[warmup:n_trunc]
            segment_trunc = trunc_slice[warmup:n_trunc]

            fill_l = _fill_rate(segment_full)
            fill_r = _fill_rate(segment_trunc)
            both_finite = ~np.isnan(segment_full) & ~np.isnan(segment_trunc)
            if both_finite.any():
                comparable_columns += 1

            context = f"values {fname}::{col}"
            _assert_nan_mask_layered(
                segment_full,
                segment_trunc,
                context=context,
                fill_rate_left=fill_l,
                fill_rate_right=fill_r,
            )
            _assert_values_both_non_nan_close(
                segment_full,
                segment_trunc,
                context=context,
            )

    coverage = comparable_columns / len(sampled_cols)
    if coverage < COVERAGE_COLUMN_FRACTION:
        raise AssertionError(
            "coverage guard failed: "
            f"{comparable_columns}/{len(sampled_cols)} sampled columns "
            f"({coverage:.1%}) have post-warmup both-non-NaN cells; "
            f"required >= {COVERAGE_COLUMN_FRACTION:.0%} "
            f"(total_common={report.total_common})"
        )
    return sampled_cols, full_map


def _assert_values_gate(
    full_dir: Path,
    trunc_dir: Path,
    *,
    warmup: int,
    n_trunc: int,
    atol: Optional[float] = None,
    column_filter: Optional[Callable[[str], bool]] = None,
) -> None:
    """values gate：共同前綴 [warmup:n_trunc) float16 容差（主 MR）或 fracdiff atol。"""
    if warmup >= n_trunc:
        pytest.fail("no post-warmup rows in truncation window")
    for fname, full_frame in _iter_raw_parquet_frames(full_dir):
        trunc_frame = pd.read_parquet(trunc_dir / fname)
        assert list(full_frame.columns) == list(trunc_frame.columns)
        for col in full_frame.columns:
            col_name = str(col)
            if column_filter is not None and not column_filter(col_name):
                continue
            full_slice = full_frame[col].to_numpy()[:n_trunc]
            trunc_slice = trunc_frame[col].to_numpy()
            segment_full = full_slice[warmup:n_trunc]
            segment_trunc = trunc_slice[warmup:n_trunc]
            if atol is None:
                _assert_arrays_values_close(
                    segment_full,
                    segment_trunc,
                    context=f"values {fname}::{col}",
                )
            else:
                lnan = np.isnan(segment_full)
                rnan = np.isnan(segment_trunc)
                assert np.array_equal(lnan, rnan), f"fracdiff NaN mask {fname}::{col}"
                finite = ~lnan
                if finite.any():
                    np.testing.assert_allclose(
                        segment_full[finite],
                        segment_trunc[finite],
                        atol=atol,
                        rtol=0.0,
                        err_msg=f"fracdiff values {fname}::{col}",
                    )


def _assert_metadata_gate(
    full: GenerationArtifacts,
    trunc: GenerationArtifacts,
    *,
    expected_training_tfs: Optional[List[str]] = None,
) -> None:
    """metadata gate：symbol/tf 不變；row_count/data_range 反映截斷。

    欄集一致性（含 feature_schema_hash/total_features）由 columns gate 有界把關，
    不在此做 exact match（多 TF 對齊 near-empty 欄 churn 會使 hash/計數略異）。
    """
    for key in ("symbol", "tf"):
        assert full.manifest.get(key) == trunc.manifest.get(key)
    assert full.metadata.get("symbol") == trunc.metadata.get("symbol")
    assert full.metadata.get("timeframe") == trunc.metadata.get("timeframe")

    full_rows = int(full.manifest.get("row_count", full.row_count))
    trunc_rows = int(trunc.manifest.get("row_count", trunc.row_count))
    assert trunc_rows < full_rows
    assert trunc_rows == full_rows - TRUNC_K

    full_range = full.manifest.get("time_range") or {}
    trunc_range = trunc.manifest.get("time_range") or {}
    if full_range and trunc_range:
        assert trunc_range.get("end") != full_range.get("end")

    if expected_training_tfs is not None:
        present = list(full.metadata.get("present_timeframes") or [])
        config_training = (
            full.metadata.get("config_used", {}).get("timeframes", {}).get("training", [])
        )
        for tf in expected_training_tfs:
            assert tf in present, (
                f"present_timeframes missing {tf!r}: {present}"
            )
            assert tf in config_training, (
                f"config_used.timeframes.training missing {tf!r}: {config_training}"
            )


def _assert_truncation_invariants(
    pair: TruncationPair,
    *,
    atol: Optional[float] = None,
    align_coarse_tfs: Optional[List[str]] = None,
    expected_training_tfs: Optional[List[str]] = None,
) -> None:
    _assert_columns_gate(pair.full.raw_dir, pair.trunc.raw_dir)
    sampled_cols: Optional[List[str]] = None
    full_map: Optional[Dict[str, Tuple[str, str]]] = None
    if atol is None:
        sampled_cols, full_map = _assert_values_gate_main(
            pair.full.raw_dir,
            pair.trunc.raw_dir,
            warmup=pair.warmup,
            n_trunc=pair.n_trunc,
            align_coarse_tfs=align_coarse_tfs,
        )
    else:
        _assert_values_gate(
            pair.full.raw_dir,
            pair.trunc.raw_dir,
            warmup=pair.warmup,
            n_trunc=pair.n_trunc,
            atol=atol,
        )
    _assert_warmup_nan_masks_equal(
        pair.full.raw_dir,
        pair.trunc.raw_dir,
        warmup=pair.warmup,
        n_trunc=pair.n_trunc,
        intersection_only=True,
        sampled_cols=sampled_cols,
        col_to_parquet=full_map,
    )
    _assert_metadata_gate(
        pair.full, pair.trunc, expected_training_tfs=expected_training_tfs
    )


def _read_d_star_values(path: Optional[Path]) -> Dict[str, float]:
    if path is None or not path.is_file():
        return {}
    return read_d_star_json(path)


def _assert_d_star_gate(full: GenerationArtifacts, trunc: GenerationArtifacts) -> None:
    full_d = _read_d_star_values(full.d_star_path)
    trunc_d = _read_d_star_values(trunc.d_star_path)
    if not full_d or not trunc_d:
        pytest.fail("fracdiff MR requires d_star cache artifacts from both runs")
    common = sorted(set(full_d) & set(trunc_d))
    if not common:
        pytest.fail("no overlapping d_star keys between full and trunc runs")
    mismatches = [
        (key, full_d[key], trunc_d[key])
        for key in common
        if full_d[key] != trunc_d[key]
    ]
    if mismatches:
        sample = mismatches[:5]
        raise AssertionError(f"d_star mismatch (sample): {sample}")


def _is_fracdiff_column(name: str) -> bool:
    return "fracdiff" in name.lower()


def _assert_fracdiff_truncation_invariants(pair: TruncationPair) -> None:
    _assert_columns_gate(pair.full.raw_dir, pair.trunc.raw_dir, strict=True)
    _assert_d_star_gate(pair.full, pair.trunc)
    _assert_values_gate(
        pair.full.raw_dir,
        pair.trunc.raw_dir,
        warmup=pair.warmup,
        n_trunc=pair.n_trunc,
        atol=FRACDIFF_ATOL,
        column_filter=_is_fracdiff_column,
    )
    _assert_warmup_nan_masks_equal(
        pair.full.raw_dir,
        pair.trunc.raw_dir,
        warmup=pair.warmup,
        n_trunc=pair.n_trunc,
    )
    _assert_metadata_gate(pair.full, pair.trunc)


def _lookahead_build_asof_index_map(
    primary_ts: np.ndarray,
    source_ts: np.ndarray,
    source_dur_ns: int,
    primary_dur_ns: int,
    mode: str,
) -> np.ndarray:
    """Forward 偏置：因果 idx +1（cap 到 len(source)-1）。"""
    idx = _ORIGINAL_BUILD_ASOF_INDEX_MAP(
        primary_ts, source_ts, source_dur_ns, primary_dur_ns, mode
    )
    out = idx.copy()
    valid = out >= 0
    if np.any(valid):
        out[valid] = np.minimum(out[valid] + 1, len(source_ts) - 1)
    return out


def _set_align_lookahead_patch(
    monkeypatch: Optional[pytest.MonkeyPatch],
    *,
    enabled: bool,
) -> None:
    """切換 build_asof_index_map 是否帶 +1 forward 偏置（供不對稱 mutation 探針）。"""
    if monkeypatch is None:
        return
    if enabled:
        monkeypatch.setattr(
            TimeframeAligner,
            "build_asof_index_map",
            staticmethod(_lookahead_build_asof_index_map),
        )
    else:
        monkeypatch.setattr(
            TimeframeAligner,
            "build_asof_index_map",
            staticmethod(_ORIGINAL_BUILD_ASOF_INDEX_MAP),
        )


def _primary_indices_at_12h_boundaries(
    ts_vals: np.ndarray,
    *,
    warmup: int,
    n_trunc: int,
) -> List[int]:
    """可比較窗 [warmup, n_trunc) 內 12h 收盤邊界 primary row index。"""
    return [
        i
        for i in range(warmup, n_trunc)
        if i < len(ts_vals) and _is_12h_close_boundary_bar_open(int(ts_vals[i]))
    ]


def _read_artifact_timestamps(artifact: GenerationArtifacts) -> np.ndarray:
    """讀 feature_manifest row_index 指向的 primary timestamp sidecar（epoch seconds）。"""
    row_index = artifact.manifest.get("row_index") or {}
    path_key = row_index.get("path")
    count = row_index.get("count")
    unit = row_index.get("unit")
    if not path_key or count is None or not unit:
        raise AssertionError(
            "align oracle: missing row_index "
            f"(path/count/unit) in manifest for {artifact.run_dir}"
        )

    ts_path = artifact.run_dir / str(path_key)
    if not ts_path.is_file():
        raise AssertionError(
            f"align oracle: missing timestamp sidecar {ts_path} "
            f"(count={count}, unit={unit})"
        )

    ts_vals = pd.read_parquet(ts_path).iloc[:, 0].astype(np.int64).to_numpy()
    count_i = int(count)
    unit_s = str(unit)
    if unit_s != "s":
        raise AssertionError(
            f"align oracle: row_index unit must be 's', got {unit_s!r} at {ts_path}"
        )
    if len(ts_vals) != count_i or len(ts_vals) != artifact.row_count:
        raise AssertionError(
            f"align oracle: timestamp count mismatch at {ts_path}: "
            f"len={len(ts_vals)} row_index.count={count_i} "
            f"artifact.row_count={artifact.row_count}"
        )
    return ts_vals


def _assert_align_coarse_boundary_lookahead_detected(
    pair: TruncationPair,
    *,
    align_coarse_tfs: List[str],
) -> None:
    """Oracle：粗 TF 欄在 12h 邊界 index 上 full vs trunc 必須可見差異（可讀 fail 訊息）。"""
    ts_vals = _read_artifact_timestamps(pair.trunc)
    boundary_idxs = _primary_indices_at_12h_boundaries(
        ts_vals, warmup=pair.warmup, n_trunc=pair.n_trunc
    )
    if not boundary_idxs:
        raise AssertionError(
            "align oracle: no 12h boundary rows in "
            f"[warmup={pair.warmup}, n_trunc={pair.n_trunc})"
        )

    full_map = _build_column_frame_map(pair.full.raw_dir)
    trunc_map = _build_column_frame_map(pair.trunc.raw_dir)
    common_cols = sorted(set(full_map) & set(trunc_map))
    probe_cols = _select_required_probe_columns(
        common_cols, full_map, align_coarse_tfs=align_coarse_tfs
    )
    align_probes = [c for c in probe_cols if _coarse_tf_from_column(c) in align_coarse_tfs]
    if not align_probes:
        raise AssertionError(
            f"align oracle: no coarse probe columns for {align_coarse_tfs!r}"
        )

    mismatches: List[str] = []
    for col in align_probes:
        fname, _ = full_map[col]
        trunc_path = pair.trunc.raw_dir / fname
        if not trunc_path.is_file():
            continue
        full_vals = _read_parquet_columns(pair.full.raw_dir / fname, [col])[col].to_numpy()[
            : pair.n_trunc
        ]
        trunc_vals = _read_parquet_columns(trunc_path, [col])[col].to_numpy()
        for idx in boundary_idxs:
            full_v = full_vals[idx]
            trunc_v = trunc_vals[idx]
            if np.isnan(full_v) and np.isnan(trunc_v):
                continue
            if not np.isclose(
                full_v, trunc_v, rtol=FLOAT16_RTOL, atol=FLOAT16_ATOL, equal_nan=True
            ):
                mismatches.append(
                    f"{fname}::{col} idx={idx} ts={int(ts_vals[idx])} "
                    f"full={full_v!r} trunc={trunc_v!r}"
                )

    if not mismatches:
        raise AssertionError(
            "align lookahead oracle: no coarse column mismatch at 12h boundaries "
            f"(probes={align_probes!r}, boundary_idxs={boundary_idxs[:8]})"
        )


def _build_truncation_pair(
    features_root: Path,
    kline_df: pd.DataFrame,
    *,
    config_payload: Dict[str, Any],
    primary_tf: str = DEFAULT_PRIMARY_TF,
    training_tfs: Optional[List[str]] = None,
    symbol: str = DEFAULT_SYMBOL,
    window_bars: Optional[int] = None,
    align_margin: int = 0,
    window_date_fn: Callable[..., Tuple[str, str, str]] = _bar_window_dates,
    patch_fetch: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
    patch_fetch_full_only: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
    d_star_parent: Optional[Path] = None,
    monkeypatch: Optional[pytest.MonkeyPatch] = None,
    align_lookahead_side: Optional[AlignLookaheadSide] = None,
) -> TruncationPair:
    if training_tfs is None:
        training_tfs = [primary_tf]
    if monkeypatch is not None:
        _apply_fixed_env(monkeypatch)

    if window_bars is None:
        window_bars = _required_window_bars(
            config_payload,
            primary_tf=primary_tf,
            training_tfs=training_tfs,
            align_margin=align_margin,
        )

    start, full_end, trunc_end = window_date_fn(
        kline_df, window_bars=window_bars, trunc_k=TRUNC_K
    )
    features_root.mkdir(parents=True, exist_ok=True)
    factory = _make_factory(features_root)

    patch_fetch_side: Optional[Literal["full", "trunc"]] = None
    if patch_fetch is not None or patch_fetch_full_only is not None:
        from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry

        original_fetch = AdapterRegistry.fetch_aligned

        def _patched_fetch(self, sym: str, timeframe: str, sources: List[str]) -> pd.DataFrame:
            data = original_fetch(self, sym, timeframe, sources)
            if sym == symbol and timeframe == primary_tf:
                if patch_fetch is not None:
                    data = patch_fetch(data.copy())
                elif patch_fetch_full_only is not None and patch_fetch_side == "full":
                    data = patch_fetch_full_only(data.copy())
            return data

        if monkeypatch is not None:
            monkeypatch.setattr(AdapterRegistry, "fetch_aligned", _patched_fetch)
        else:
            AdapterRegistry.fetch_aligned = _patched_fetch  # type: ignore[method-assign]

    config = factory._resolve_config(config_payload)
    warmup = estimate_max_warmup_bars(config, primary_tf, training_tfs)

    full_d_dir = d_star_parent / "full" if d_star_parent else None
    trunc_d_dir = d_star_parent / "trunc" if d_star_parent else None

    _set_align_lookahead_patch(
        monkeypatch, enabled=(align_lookahead_side == "full")
    )
    patch_fetch_side = "full"
    full = _run_generation(
        factory,
        features_root=features_root,
        config_payload=config_payload,
        start_date=start,
        end_date=full_end,
        symbol=symbol,
        primary_tf=primary_tf,
        d_star_dir=full_d_dir,
    )
    _set_align_lookahead_patch(
        monkeypatch, enabled=(align_lookahead_side == "trunc")
    )
    patch_fetch_side = "trunc"
    trunc = _run_generation(
        factory,
        features_root=features_root,
        config_payload=config_payload,
        start_date=start,
        end_date=trunc_end,
        symbol=symbol,
        primary_tf=primary_tf,
        d_star_dir=trunc_d_dir,
    )
    patch_fetch_side = None
    _set_align_lookahead_patch(monkeypatch, enabled=False)
    return TruncationPair(warmup=warmup, n_trunc=trunc.row_count, full=full, trunc=trunc)


def _patch_kline_tail_ohlcv(df: pd.DataFrame, *, k: int, delta: float) -> pd.DataFrame:
    out = df.copy()
    for col in ("open", "high", "low", "close", "volume"):
        if col in out.columns:
            out.iloc[-k:, out.columns.get_loc(col)] = out.iloc[-k:][col].astype(float).to_numpy() + delta
    return out


def _patch_kline_calibration_ohlcv(
    df: pd.DataFrame,
    *,
    window_bars: int,
    calibration_bars: int,
    delta: float,
) -> pd.DataFrame:
    """擾動 calibration 窗內（相對於當前 window 尾段的 first calibration_bars）。"""
    out = df.copy()
    if len(out) < window_bars:
        return out
    window_start = len(out) - window_bars
    cal_end = window_start + calibration_bars
    for col in ("open", "high", "low", "close", "volume"):
        if col in out.columns:
            out.iloc[window_start:cal_end, out.columns.get_loc(col)] = (
                out.iloc[window_start:cal_end][col].astype(float).to_numpy() + delta
            )
    return out

