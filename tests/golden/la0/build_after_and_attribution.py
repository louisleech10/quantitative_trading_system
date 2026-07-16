#!/usr/bin/env python3
"""LA-0 B6: 以 B0 凍結輸入重跑 PIT 引擎 → after baseline + attribution.json。

SPEC: docs/IC_LA0_SPEC.md §G L2 / RULING-4 / LA0-5
TODO: docs/IC_LA0_TODO.md Task 6.1

- 不重選特徵（鎖 B0 input_contract features_path/meta_path）
- B0 ``*_baseline.json`` 為改前(legacy)；本腳本產 ``*_baseline_after.json``
- 只填 allowlist 既有列的 before/after/delta（禁增 expected 列）
- control 列必 |Δ|≈0，否則 class=unexpected → exit 1
- 非-control：值變但缺 M-lookahead oracle → unexpected（禁洗歸因）
- 未列 metric 有 diff → unexpected（RULING-4 unlisted_diff）
- 另產 split-OFF after-golden（flag off / pit_expanding）供 live deep-equal
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.golden.la0 import gen_baseline as gb  # noqa: E402
from momentum.Analysis.pit_stats import PIT_STATS_VERSION  # noqa: E402
from momentum.factories import create_ic_analyzer  # noqa: E402

OUT = Path(__file__).resolve().parent
CONTROL_ATOL = 1e-12
BEFORE_FILES = {
    "BTCUSDT_1h": "BTCUSDT_1h_baseline.json",
    "ETHUSDT_12h": "ETHUSDT_12h_baseline.json",
}

# metric_value 可抽出的全量 catalog（未列 allowlist 的 diff → unexpected）
ALL_EXTRACTABLE_METRICS: tuple[str, ...] = (
    "rolling_ic_spearman",
    "icir",
    "ic_hit_rate",
    "mono_bin_t",
    "monotonicity_score",
    "quantile_mean_returns",
    "turnover_scalar",
    "turnover_time_series",
    "rank_change_rate",
    "rank_change_time_series",
    "stage1_winsorize_full_sample_fallback",
    "passed_features_set",
    "control_pearson_rolling_ic",
    "control_train_mask_winsorize",
)

SPLIT_OFF_OVERRIDE: dict[str, Any] = {"ic_train_test_split": False}


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_analyze_with_override(
    h5_path: Path,
    meta_path: Path,
    config_override: Optional[dict[str, Any]] = None,
) -> tuple[Any, dict, float, int, int]:
    """與 gen_baseline._run_analyze 等價，可注入 config_override（split OFF 等）。"""
    orchestrator = create_ic_analyzer()
    gb._isolate_orchestrator_persist(orchestrator)
    kline_reader = gb.create_kline_storage_manager(cache_dir=gb.KLINE_CACHE_DIR)
    rss_before = gb._rss_kb()
    t0 = time.perf_counter()
    report = orchestrator.analyze(
        features_path=str(h5_path.resolve()),
        labels_path="",
        meta_path=str(meta_path.resolve()),
        config_override=config_override,
        kline_reader=kline_reader,
    )
    wall_s = float(time.perf_counter() - t0)
    rss_after = gb._rss_kb()
    return orchestrator, report, wall_s, rss_before, rss_after


def _train_mask_winsorize_control(
    orchestrator: Any,
    raw_features: Any,
    train_mask: np.ndarray,
) -> dict[str, Any]:
    """B4 後 winsorize 須顯式 fit_mode=train_mask。"""
    preproc = orchestrator._preprocessor
    winsor_cfg = getattr(orchestrator._config.preprocessing, "winsorization", None)
    method = "percentile"
    lower = 1.0
    upper = 99.0
    if winsor_cfg is not None:
        method = getattr(winsor_cfg, "method", method)
        lower = float(getattr(winsor_cfg, "lower_percentile", lower))
        upper = float(getattr(winsor_cfg, "upper_percentile", upper))

    clipped, _log = preproc.winsorize(
        raw_features.copy(),
        method=method,
        lower=lower,
        upper=upper,
        metadata=None,
        fit_mask=train_mask,
        fit_mode="train_mask",
    )
    train_vals = clipped.loc[clipped.index[train_mask]]
    first_row = (
        train_vals.iloc[0].to_numpy(dtype=np.float64)
        if len(train_vals)
        else np.array([], dtype=np.float64)
    )
    return {
        "train_rows": int(train_mask.sum()),
        "value_sha256": gb._hash_float_array(train_vals.to_numpy(dtype=np.float64)),
        "nan_mask_sha256": gb._hash_bool_array(train_vals.isna().to_numpy()),
        "shape": [int(train_vals.shape[0]), int(train_vals.shape[1])],
        "early_prefix": {
            "n_rows": min(gb.EARLY_PREFIX_N, int(len(train_vals))),
            "row_timestamps": [
                gb._ts_str(t) for t in train_vals.index[: gb.EARLY_PREFIX_N].tolist()
            ],
            "first_row_values": gb._json_safe_float_list(first_row),
            "first_row_sha256": gb._hash_float_array(first_row),
        },
    }


def collect_after_from_frozen(
    before: dict[str, Any],
    *,
    config_override: Optional[dict[str, Any]] = None,
    baseline_role: str = "after_pit",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """對 B0 凍結 h5/meta 重跑 orchestrator，產出 after baseline。

    config_override:
      - None → 預設 split ON（與 B0 同）
      - SPLIT_OFF_OVERRIDE → flag-off / pit_expanding 路徑
    """
    h5 = REPO_ROOT / before["input_contract"]["features_path"]
    meta_path = REPO_ROOT / before["input_contract"]["meta_path"]
    if not h5.is_file() or not meta_path.is_file():
        raise FileNotFoundError(f"frozen input missing: {h5} / {meta_path}")

    symbol = before["symbol"]
    timeframe = before["timeframe"]
    config_hash = before["config_hash"]

    orchestrator, report, wall_s, rss_before, rss_after = _run_analyze_with_override(
        h5, meta_path, config_override=config_override
    )
    ic_cache = orchestrator._ic_cache or {}
    features_df = ic_cache.get("features_df")
    label_series = ic_cache.get("label_series")
    if features_df is None or label_series is None:
        raise RuntimeError(f"{symbol}/{timeframe}: ic_cache missing features/label")

    split_context = ic_cache.get("split_context")
    rolling_ic = ic_cache.get("rolling_ic") or {}
    icir = ic_cache.get("icir") or {}
    mono_cache = orchestrator._monotonicity_cache or report.get("quantile_returns") or {}
    turnover = report.get("turnover_analysis") or {}
    filter_log = report.get("filter_log") or {}
    stage5_log = filter_log.get("stage5_thresholds") or {}
    all_features = [str(c) for c in features_df.columns]
    passed_features, rejected_features, _ = gb._stage5_passed_rejected(
        all_features, stage5_log
    )

    windows = list(orchestrator._config.ic_calculation.rolling_windows)
    stride = int(orchestrator._config.ic_calculation.rolling_stride)
    test_mask = train_mask = None
    if split_context is not None:
        test_mask = np.asarray(split_context.get("test_mask"), dtype=bool)
        train_mask = np.asarray(split_context.get("train_mask"), dtype=bool)

    rolling_features = features_df
    rolling_label = label_series
    rolling_test_mask = test_mask
    if split_context is not None and test_mask is not None and train_mask is not None:
        allowed = train_mask | test_mask
        rolling_features = features_df.loc[features_df.index[allowed]]
        rolling_label = label_series.loc[label_series.index[allowed]]
        rolling_test_mask = test_mask[allowed]

    bin_t = gb._extract_bin_t_series(features_df, label_series, test_mask)
    pearson = gb._pearson_control(
        orchestrator,
        features_df,
        label_series,
        split_context,
        windows,
        stride,
    )
    train_winsor_control = None
    if train_mask is not None and train_mask.any():
        raw_from_orch, _ = orchestrator._load_features_hdf5(str(h5.resolve()))
        raw_from_orch = raw_from_orch.reindex(columns=list(features_df.columns))
        if len(raw_from_orch) == len(train_mask):
            train_winsor_control = _train_mask_winsorize_control(
                orchestrator, raw_from_orch, train_mask
            )

    stage1_value_sha = gb._hash_float_array(features_df.to_numpy(dtype=np.float64))
    stage1_nan_mask_sha = gb._hash_bool_array(features_df.isna().to_numpy())
    preproc_log = ic_cache.get("preproc_log") or {}
    n_rows = int(len(features_df))
    n_features = int(features_df.shape[1])
    actual_default_n = before["counts"]["actual_default_N"]

    split_flag = bool(orchestrator._config.ic_train_test_split)
    if config_override and "ic_train_test_split" in config_override:
        split_flag = bool(config_override["ic_train_test_split"])

    baseline: dict[str, Any] = {
        "schema_version": "la0_b6_after_v1",
        "pit_stats_version": PIT_STATS_VERSION,
        "baseline_role": baseline_role,
        "before_ref": {
            "schema_version": before.get("schema_version"),
            "pit_stats_version": before.get("pit_stats_version"),
            "features_h5_sha256": before["input_contract"]["features_h5_sha256"],
            "meta_sha256": before["input_contract"]["meta_sha256"],
        },
        "symbol": symbol,
        "timeframe": timeframe,
        "config_hash": config_hash,
        "kline_h5_group": before["kline_h5_group"],
        "input_contract": {
            **before["input_contract"],
            "features_h5_sha256": _sha_file(h5),
            "meta_sha256": _sha_file(meta_path),
        },
        "config_snapshot": {
            "default_method": orchestrator._config.global_settings.default_method,
            "rolling_windows": windows,
            "rolling_stride": stride,
            "monotonicity_score_min": float(
                orchestrator._config.thresholds.monotonicity_score_min
            ),
            "turnover_enabled": bool(orchestrator._config.turnover.enabled),
            "ic_train_test_split": split_flag,
            "winsorization_enabled": bool(
                orchestrator._config.preprocessing.winsorization.enabled
            ),
            "winsorization_method": orchestrator._config.preprocessing.winsorization.method,
            "standardize": "none",
        },
        "counts": {
            "n_rows": n_rows,
            "n_features": n_features,
            "n_passed_features": int(len(passed_features)),
            "n_rejected_features": int(len(rejected_features)),
            "train_rows": int(train_mask.sum()) if train_mask is not None else None,
            "test_rows": int(test_mask.sum()) if test_mask is not None else None,
            "actual_default_N": actual_default_n,
        },
        "schema": before.get("schema"),
        "rolling_ic": gb._rolling_ic_payload(
            rolling_ic,
            rolling_features,
            rolling_label,
            windows,
            stride,
            rolling_test_mask,
        ),
        "icir": gb._icir_payload(icir),
        "monotonicity": {"scores": gb._mono_payload(mono_cache), "bin_t": bin_t},
        "turnover": gb._turnover_payload(turnover),
        "stage1": {
            "winsorize_value_sha256": stage1_value_sha,
            "nan_mask_sha256": stage1_nan_mask_sha,
            "preproc_log": {
                "winsorized_features": list(preproc_log.get("winsorized_features") or []),
                "skipped_winsorization": list(
                    preproc_log.get("skipped_winsorization") or []
                ),
                "removed_features": preproc_log.get("removed_features") or {},
                "fit_mode": preproc_log.get("fit_mode"),
            },
            "shape": [n_rows, n_features],
        },
        "passed_features": {
            "names": passed_features,
            "sha256": gb._hash_string_set(passed_features),
            "count": int(len(passed_features)),
            "rejected_names": rejected_features,
            "rejected_count": int(len(rejected_features)),
            "rejected_sha256": gb._hash_string_set(rejected_features),
            "stage5_threshold_log": {
                "input_features": stage5_log.get("input_features"),
                "output_features": stage5_log.get("output_features"),
                "alpha_effective": stage5_log.get("alpha_effective"),
                "n_tests": stage5_log.get("n_tests"),
                "removed_features": stage5_log.get("removed_features"),
            },
        },
        "control": {
            "pearson_rolling_ic": pearson,
            "train_mask_winsorize": train_winsor_control,
        },
        "after_perf_telemetry": {
            "n_features": n_features,
            "n_rows": n_rows,
            "actual_default_N": actual_default_n,
            "rolling_windows": windows,
            "method": "spearman",
            "wall_seconds": wall_s,
            "rss_before_raw": rss_before,
            "rss_after_raw": rss_after,
            "rss_unit_note": "resource.ru_maxrss: bytes on macOS, KB on Linux",
            "note": "B6 after (PIT engine) non-blocking telemetry",
        },
        "report_metadata": {
            k: (report.get("metadata") or {}).get(k)
            for k in (
                "symbol",
                "timeframe",
                "feature_count_original",
                "feature_count_filtered",
                "truncation_mode",
                "ic_train_test_split",
            )
        },
    }
    for _feat, body in baseline["turnover"].items():
        if isinstance(body, dict) and "time_series" in body:
            body["time_series"]["legacy_length_policy"] = "n_aligned_source_index_s2"

    live = {
        "symbol": symbol,
        "timeframe": timeframe,
        "wall_seconds": wall_s,
        "n_passed": len(passed_features),
        "n_rejected": len(rejected_features),
        "rss_after_raw": rss_after,
    }
    return baseline, live


def metric_value(baseline: dict[str, Any], name: str) -> Any:
    """從 baseline 抽出 attribution 列的 before/after 值（digest 為主）。"""
    if name == "rolling_ic_spearman":
        parts: list[str] = []
        ric = (baseline.get("rolling_ic") or {}).get("per_feature_window") or {}
        for f in sorted(ric):
            for w in sorted(ric[f]):
                parts.append(f"{f}|{w}|{ric[f][w].get('sha256')}")
        return {
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "n_series": len(parts),
        }
    if name == "icir":
        vals = {
            f: s.get("icir")
            for f, s in sorted((baseline.get("icir") or {}).items())
        }
        parts = [f"{f}|{v}" for f, v in vals.items()]
        return {
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "values": vals,
        }
    if name == "ic_hit_rate":
        vals = {
            f: s.get("ic_hit_rate")
            for f, s in sorted((baseline.get("icir") or {}).items())
        }
        parts = [f"{f}|{v}" for f, v in vals.items()]
        return {
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "values": vals,
        }
    if name == "mono_bin_t":
        parts = []
        bt = ((baseline.get("monotonicity") or {}).get("bin_t") or {})
        for f in sorted(bt):
            parts.append(
                f"{f}|{bt[f].get('bin_t_sha256')}|len={bt[f].get('bin_t_len')}"
            )
        return {
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "n": len(parts),
        }
    if name == "monotonicity_score":
        scores = ((baseline.get("monotonicity") or {}).get("scores") or {})
        vals = {
            f: s.get("monotonicity_score") for f, s in sorted(scores.items())
        }
        parts = [f"{f}|{v}" for f, v in vals.items()]
        return {
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "values": vals,
        }
    if name == "quantile_mean_returns":
        scores = ((baseline.get("monotonicity") or {}).get("scores") or {})
        parts = [
            f"{f}|{s.get('quantile_mean_returns_sha256')}"
            for f, s in sorted(scores.items())
        ]
        return {
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "n": len(parts),
        }
    if name == "turnover_scalar":
        to = baseline.get("turnover") or {}
        vals = {
            f: body.get("quantile_turnover") for f, body in sorted(to.items())
        }
        parts = [f"{f}|{v}" for f, v in vals.items()]
        return {
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "values": vals,
        }
    if name == "turnover_time_series":
        to = baseline.get("turnover") or {}
        parts = []
        lens: dict[str, Any] = {}
        for f, body in sorted(to.items()):
            ts = body.get("time_series") or {}
            parts.append(
                f"{f}|{ts.get('quantile_turnovers_sha256')}|"
                f"len={ts.get('quantile_turnovers_len')}"
            )
            lens[f] = ts.get("quantile_turnovers_len")
        return {
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "lens": lens,
        }
    if name == "rank_change_rate":
        to = baseline.get("turnover") or {}
        vals = {
            f: body.get("rank_change_rate") for f, body in sorted(to.items())
        }
        parts = [f"{f}|{v}" for f, v in vals.items()]
        return {
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "values": vals,
        }
    if name == "rank_change_time_series":
        to = baseline.get("turnover") or {}
        parts = []
        lens = {}
        for f, body in sorted(to.items()):
            ts = body.get("time_series") or {}
            parts.append(
                f"{f}|{ts.get('rank_change_rates_sha256')}|"
                f"len={ts.get('rank_change_rates_len')}"
            )
            lens[f] = ts.get("rank_change_rates_len")
        return {
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "lens": lens,
        }
    if name == "stage1_winsorize_full_sample_fallback":
        s1 = baseline.get("stage1") or {}
        # 數值門檻只比 value/nan hash（fit_mode 元資料不計 delta）
        return {
            "value_sha256": s1.get("winsorize_value_sha256"),
            "nan_mask_sha256": s1.get("nan_mask_sha256"),
            "shape": s1.get("shape"),
        }
    if name == "passed_features_set":
        pf = baseline.get("passed_features") or {}
        return {
            "sha256": pf.get("sha256"),
            "names": pf.get("names"),
            "count": pf.get("count"),
            "rejected_sha256": pf.get("rejected_sha256"),
            "rejected_count": pf.get("rejected_count"),
        }
    if name == "control_pearson_rolling_ic":
        parts = []
        ric = (
            ((baseline.get("control") or {}).get("pearson_rolling_ic") or {}).get(
                "per_feature_window"
            )
            or {}
        )
        for f in sorted(ric):
            for w in sorted(ric[f]):
                parts.append(f"{f}|{w}|{ric[f][w].get('sha256')}")
        return {
            "digest": hashlib.sha256("\n".join(parts).encode()).hexdigest(),
            "n_series": len(parts),
        }
    if name == "control_train_mask_winsorize":
        c = (baseline.get("control") or {}).get("train_mask_winsorize") or {}
        return {
            "value_sha256": c.get("value_sha256"),
            "nan_mask_sha256": c.get("nan_mask_sha256"),
            "shape": c.get("shape"),
            "first_row_sha256": (c.get("early_prefix") or {}).get("first_row_sha256"),
        }
    raise KeyError(f"unknown attribution metric: {name}")


def delta_of(before_v: Any, after_v: Any) -> float:
    return 0.0 if before_v == after_v else 1.0


def _is_control_row(row: dict[str, Any]) -> bool:
    name = str(row.get("name") or "")
    return row.get("component") == "control" or name.startswith("control_")


def _oracle_m_lookahead_ok(row: dict[str, Any]) -> bool:
    """expected-leakfix 值變時須綁非空 m_lookahead mutation nodeid。"""
    oracle = row.get("oracle_passed") or {}
    m_la = oracle.get("m_lookahead")
    return isinstance(m_la, str) and len(m_la.strip()) > 0


def scan_unlisted_metric_diffs(
    before_map: dict[str, dict[str, Any]],
    after_map: dict[str, dict[str, Any]],
    allowlist_names: set[str],
) -> list[str]:
    """枚舉 ALL_EXTRACTABLE_METRICS；任一 symbol 有 diff 但不在 allowlist → unexpected 名。

    RULING-4 / policy.unlisted_diff=unexpected。
    """
    unlisted: list[str] = []
    for name in ALL_EXTRACTABLE_METRICS:
        if name in allowlist_names:
            continue
        for key in ("BTCUSDT_1h", "ETHUSDT_12h"):
            if key not in before_map or key not in after_map:
                continue
            try:
                b_v = metric_value(before_map[key], name)
                a_v = metric_value(after_map[key], name)
            except KeyError:
                continue
            if delta_of(b_v, a_v) != 0.0:
                unlisted.append(name)
                break
    return unlisted


def classify_row_runtime(
    filled: dict[str, Any],
    *,
    d: float,
    eth_d: float,
) -> tuple[str, Optional[str]]:
    """依 RULING-4 決定 runtime class；回 (class, unexpected_reason|None)。

    - control：|Δ|>atol → unexpected
    - 非-control expected-leakfix：值變但缺 m_lookahead oracle → unexpected
    - 其餘：保留 predeclare class（禁 silent 洗成其他 expected）
    """
    predeclared = str(filled.get("class") or "")
    is_control = _is_control_row(filled)
    if is_control:
        if abs(float(d)) > CONTROL_ATOL or abs(float(eth_d)) > CONTROL_ATOL:
            return "unexpected", "control_drift"
        return predeclared, None

    value_changed = abs(float(d)) > CONTROL_ATOL or abs(float(eth_d)) > CONTROL_ATOL
    if predeclared == "expected-leakfix" and value_changed:
        if not _oracle_m_lookahead_ok(filled):
            return "unexpected", "leakfix_without_m_lookahead_oracle"
    # expected-downstream 允許隨主錨變，仍須 predeclare；不在此洗 class
    return predeclared, None


def build_attribution(
    before_map: dict[str, dict[str, Any]],
    after_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    allowlist = json.loads((OUT / "attribution_allowlist.json").read_text(encoding="utf-8"))
    btc_b = before_map["BTCUSDT_1h"]
    eth_b = before_map["ETHUSDT_12h"]
    btc_a = after_map["BTCUSDT_1h"]
    eth_a = after_map["ETHUSDT_12h"]

    allow_names = {r["name"] for r in allowlist["rows"]}
    rows: list[dict[str, Any]] = []
    unexpected: list[str] = []
    unexpected_reasons: dict[str, str] = {}

    for row in allowlist["rows"]:
        name = row["name"]
        b_v = metric_value(btc_b, name)
        a_v = metric_value(btc_a, name)
        d = delta_of(b_v, a_v)
        eth_bv = metric_value(eth_b, name)
        eth_av = metric_value(eth_a, name)
        eth_d = delta_of(eth_bv, eth_av)

        filled = copy.deepcopy(row)
        filled["before"] = b_v
        filled["after"] = a_v
        filled["delta"] = d
        # 雙 symbol hash 並列（§G L3 / 驗收）
        filled["dual_symbol"] = {
            "BTCUSDT_1h": {
                "before": b_v,
                "after": a_v,
                "delta": d,
            },
            "ETHUSDT_12h": {
                "before": eth_bv,
                "after": eth_av,
                "delta": eth_d,
            },
        }

        runtime_class, reason = classify_row_runtime(filled, d=d, eth_d=eth_d)
        filled["class"] = runtime_class
        if reason is not None:
            unexpected.append(name)
            unexpected_reasons[name] = reason
            filled["unexpected_reason"] = reason
        elif _is_control_row(filled):
            # control 穩定：強制 Δ=0 展示
            filled["delta"] = 0.0
            filled["dual_symbol"]["BTCUSDT_1h"]["delta"] = 0.0
            filled["dual_symbol"]["ETHUSDT_12h"]["delta"] = 0.0
        rows.append(filled)

    # 未列 allowlist 的 extractable metric 有 diff → unexpected
    unlisted = scan_unlisted_metric_diffs(before_map, after_map, allow_names)
    for name in unlisted:
        if name not in unexpected:
            unexpected.append(name)
        unexpected_reasons[name] = "unlisted_diff"
        rows.append(
            {
                "name": name,
                "before": None,
                "after": None,
                "delta": 1.0,
                "component": "unlisted",
                "oracle_passed": {"m_lookahead": None, "control": None},
                "class": "unexpected",
                "reason": "RULING-4 unlisted_diff: metric changed but not in B0 allowlist",
                "unexpected_reason": "unlisted_diff",
            }
        )

    by_class = dict(Counter(r["class"] for r in rows))
    by_comp: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_comp.setdefault(r["component"], []).append(
            {"name": r["name"], "class": r["class"], "delta": r["delta"]}
        )

    control_unexpected = [
        n
        for n, reason in unexpected_reasons.items()
        if reason == "control_drift"
    ]

    return {
        "schema_version": "la0_attribution_v1",
        "spec_ref": "docs/IC_LA0_SPEC.md §G L2 + RULING-4",
        "todo_ref": "docs/IC_LA0_TODO.md Task 6.1",
        "allowlist_ref": "tests/golden/la0/attribution_allowlist.json",
        "policy": allowlist["policy"],
        "before_baselines": {
            "BTCUSDT_1h": "tests/golden/la0/BTCUSDT_1h_baseline.json",
            "ETHUSDT_12h": "tests/golden/la0/ETHUSDT_12h_baseline.json",
            "sha256_prefix": {
                "BTCUSDT_1h": _sha_file(OUT / "BTCUSDT_1h_baseline.json")[:16],
                "ETHUSDT_12h": _sha_file(OUT / "ETHUSDT_12h_baseline.json")[:16],
            },
        },
        "after_baselines": {
            "BTCUSDT_1h": "tests/golden/la0/BTCUSDT_1h_baseline_after.json",
            "ETHUSDT_12h": "tests/golden/la0/ETHUSDT_12h_baseline_after.json",
            "sha256_prefix": {
                "BTCUSDT_1h": _sha_file(OUT / "BTCUSDT_1h_baseline_after.json")[:16]
                if (OUT / "BTCUSDT_1h_baseline_after.json").exists()
                else None,
                "ETHUSDT_12h": _sha_file(OUT / "ETHUSDT_12h_baseline_after.json")[:16]
                if (OUT / "ETHUSDT_12h_baseline_after.json").exists()
                else None,
            },
            "pit_stats_version": btc_a.get("pit_stats_version"),
        },
        "rows": rows,
        "summary": {
            "n_rows": len(rows),
            "n_unexpected": len(unexpected),
            "unexpected_names": unexpected,
            "unexpected_reasons": unexpected_reasons,
            "unlisted_diff_names": unlisted,
            "control_stable": len(control_unexpected) == 0 and len(unlisted) == 0
            and all(
                r["class"] != "unexpected"
                for r in rows
                if _is_control_row(r)
            ),
            "by_class": by_class,
            "by_component": by_comp,
            "s2_turnover_size": {
                "note": "legacy n-1 → after n (aligned source index; JSON null warmup)",
                "BTCUSDT_1h_before_lens": metric_value(
                    btc_b, "turnover_time_series"
                ).get("lens"),
                "BTCUSDT_1h_after_lens": metric_value(
                    btc_a, "turnover_time_series"
                ).get("lens"),
                "ETHUSDT_12h_before_lens": metric_value(
                    eth_b, "turnover_time_series"
                ).get("lens"),
                "ETHUSDT_12h_after_lens": metric_value(
                    eth_a, "turnover_time_series"
                ).get("lens"),
            },
        },
    }


def validate_attribution_payload(
    attr: dict[str, Any],
    allowlist: dict[str, Any],
    before_map: dict[str, dict[str, Any]],
    after_map: dict[str, dict[str, Any]],
) -> None:
    """RULING-4 強 validator（可被 mutation 測紅）。

    (a) 每列 class == B0 predeclare allowlist class（禁 silent 重分類洗歸因）
    (b) 未列 metric 有 diff → FAIL
    (c) 非-control expected-leakfix 值變須綁 m_lookahead；否則 FAIL
    另：before/after/delta 可重算；control-stable；無 unexpected。
    """
    allow_rows = allowlist["rows"]
    allow_by_name = {r["name"]: r for r in allow_rows}
    allow_names = set(allow_by_name)

    # 只比 allowlist 列（unlisted 由 scan 另驗，不得 silent 進 expected）
    attr_allow_rows = [r for r in attr["rows"] if r["name"] in allow_names]
    attr_names = [r["name"] for r in attr_allow_rows]
    assert attr_names == [r["name"] for r in allow_rows], (
        f"attribution allowlist rows must match exactly; "
        f"extra={set(attr_names) - allow_names} "
        f"missing={allow_names - set(attr_names)}"
    )

    unexpected: list[str] = []
    for row, allow_row in zip(attr_allow_rows, allow_rows):
        missing = {
            "name",
            "before",
            "after",
            "delta",
            "component",
            "oracle_passed",
            "class",
            "reason",
        } - set(row.keys())
        assert not missing, f"{row.get('name')}: missing keys {missing}"
        assert row["name"] == allow_row["name"]
        assert row["component"] == allow_row["component"]
        # (a) 禁 silent 重分類：class 必須等於 B0 predeclare
        assert row["class"] == allow_row["class"], (
            f"{row['name']}: class washed {row['class']!r} != allowlist "
            f"{allow_row['class']!r}"
        )
        assert row["class"] in {
            "expected-leakfix",
            "expected-downstream",
            "unexpected",
        }
        if row["class"] == "unexpected":
            unexpected.append(row["name"])

        assert row["before"] is not None, f"{row['name']}: before null"
        assert row["after"] is not None, f"{row['name']}: after null"
        assert row["delta"] is not None, f"{row['name']}: delta null"

        dual = row.get("dual_symbol") or {}
        assert "BTCUSDT_1h" in dual and "ETHUSDT_12h" in dual, (
            f"{row['name']}: dual_symbol missing"
        )

        # 可重算 before/after/delta（亂改值 → 打紅）
        name = row["name"]
        for key, bl_map in (
            ("BTCUSDT_1h", (before_map["BTCUSDT_1h"], after_map["BTCUSDT_1h"])),
            ("ETHUSDT_12h", (before_map["ETHUSDT_12h"], after_map["ETHUSDT_12h"])),
        ):
            b_live = metric_value(bl_map[0], name)
            a_live = metric_value(bl_map[1], name)
            d_live = delta_of(b_live, a_live)
            assert dual[key]["before"] == b_live, (
                f"{name}/{key}: before washed vs recomputed baseline"
            )
            assert dual[key]["after"] == a_live, (
                f"{name}/{key}: after washed vs recomputed baseline"
            )
            # control 展示 Δ 可被 clamp 為 0；非-control 須等於 recompute
            if _is_control_row(row):
                assert abs(float(dual[key]["delta"])) <= CONTROL_ATOL
                assert d_live == 0.0, f"control {name}/{key} live delta={d_live}"
            else:
                assert float(dual[key]["delta"]) == float(d_live), (
                    f"{name}/{key}: delta washed {dual[key]['delta']} != {d_live}"
                )

        # (c) expected-leakfix + 值變 → 必須綁 m_lookahead
        btc_d = float(dual["BTCUSDT_1h"]["delta"])
        eth_d = float(dual["ETHUSDT_12h"]["delta"])
        value_changed = (
            abs(btc_d) > CONTROL_ATOL or abs(eth_d) > CONTROL_ATOL
        )
        if (
            not _is_control_row(row)
            and row["class"] == "expected-leakfix"
            and value_changed
        ):
            assert _oracle_m_lookahead_ok(row), (
                f"{name}: expected-leakfix delta!=0 but m_lookahead oracle missing "
                f"(would be unexpected / wash risk)"
            )

        if _is_control_row(row):
            assert abs(btc_d) <= CONTROL_ATOL
            assert abs(eth_d) <= CONTROL_ATOL
            assert abs(float(row["delta"])) <= CONTROL_ATOL

    # (b) 未列 diff
    unlisted = scan_unlisted_metric_diffs(before_map, after_map, allow_names)
    assert not unlisted, f"unlisted metric diffs (unexpected): {unlisted}"

    assert not unexpected, f"unexpected attribution rows: {unexpected}"
    assert attr.get("summary", {}).get("n_unexpected", 1) == 0
    assert attr.get("summary", {}).get("control_stable") is True


def _write_after_baselines(
    before_map: dict[str, dict[str, Any]],
    *,
    config_override: Optional[dict[str, Any]],
    role: str,
    name_suffix: str,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """重跑並寫 ``*_baseline_after{name_suffix}.json``。"""
    after_map: dict[str, dict[str, Any]] = {}
    telem: list[dict[str, Any]] = []
    for key, fname in BEFORE_FILES.items():
        before = before_map[key]
        print(
            f"[b6] building after{name_suffix} for {key} "
            f"override={config_override} ..."
        )
        after, live = collect_after_from_frozen(
            before,
            config_override=config_override,
            baseline_role=role,
        )
        after_name = fname.replace(
            "_baseline.json", f"_baseline_after{name_suffix}.json"
        )
        after_path = OUT / after_name
        raw = gb._canonical_json_bytes(after)
        after_path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        print(
            f"[b6] wrote {after_name} sha={digest[:16]} "
            f"passed={after['counts']['n_passed_features']} "
            f"rejected={after['counts']['n_rejected_features']} "
            f"split={after['config_snapshot']['ic_train_test_split']} "
            f"wall={live['wall_seconds']:.2f}s"
        )
        after_map[key] = after
        telem.append(
            {
                **live,
                "after_sha256": digest,
                "after_file": after_name,
                "config_override": config_override,
                "baseline_role": role,
            }
        )
    return after_map, telem


def main() -> int:
    before_map: dict[str, dict[str, Any]] = {}
    for key, fname in BEFORE_FILES.items():
        before_path = OUT / fname
        before_map[key] = json.loads(before_path.read_text(encoding="utf-8"))

    # --- split-ON after（主歸因）---
    after_map, telem = _write_after_baselines(
        before_map,
        config_override=None,
        role="after_pit",
        name_suffix="",
    )

    # --- split-OFF after（flag-off / pit_expanding live gate）---
    after_off_map, telem_off = _write_after_baselines(
        before_map,
        config_override=SPLIT_OFF_OVERRIDE,
        role="after_pit_split_off",
        name_suffix="_split_off",
    )
    # 契約：split OFF 必須關掉 holdout，且 stage1 fit_mode=pit_expanding
    for key, after_off in after_off_map.items():
        if after_off["config_snapshot"]["ic_train_test_split"] is not False:
            print(f"[b6] FAIL: {key} split-off golden still has split ON")
            return 1
        fit_mode = (after_off.get("stage1") or {}).get("preproc_log", {}).get(
            "fit_mode"
        )
        if fit_mode != "pit_expanding":
            print(
                f"[b6] FAIL: {key} split-off fit_mode={fit_mode!r} "
                f"expected pit_expanding"
            )
            return 1

    attr = build_attribution(before_map, after_map)
    attr["after_baselines"]["sha256_prefix"] = {
        "BTCUSDT_1h": _sha_file(OUT / "BTCUSDT_1h_baseline_after.json")[:16],
        "ETHUSDT_12h": _sha_file(OUT / "ETHUSDT_12h_baseline_after.json")[:16],
    }
    attr["after_baselines_split_off"] = {
        "BTCUSDT_1h": "tests/golden/la0/BTCUSDT_1h_baseline_after_split_off.json",
        "ETHUSDT_12h": "tests/golden/la0/ETHUSDT_12h_baseline_after_split_off.json",
        "sha256_prefix": {
            "BTCUSDT_1h": _sha_file(
                OUT / "BTCUSDT_1h_baseline_after_split_off.json"
            )[:16],
            "ETHUSDT_12h": _sha_file(
                OUT / "ETHUSDT_12h_baseline_after_split_off.json"
            )[:16],
        },
        "pit_stats_version": after_off_map["BTCUSDT_1h"].get("pit_stats_version"),
        "config": SPLIT_OFF_OVERRIDE,
    }
    (OUT / "attribution.json").write_bytes(gb._canonical_json_bytes(attr))
    (OUT / "after_perf_telemetry_receipt.json").write_bytes(
        gb._canonical_json_bytes(
            {
                "schema_version": "la0_b6_after_perf_receipt_v1",
                "note": "B6 after PIT engine telemetry; frozen B0 inputs re-analyzed",
                "runs": telem,
                "runs_split_off": telem_off,
            }
        )
    )

    print(
        f"[b6] attribution unexpected={attr['summary']['unexpected_names']} "
        f"control_stable={attr['summary']['control_stable']} "
        f"by_class={attr['summary']['by_class']}"
    )
    for r in attr["rows"]:
        eth_d = (r.get("dual_symbol") or {}).get("ETHUSDT_12h", {}).get("delta")
        print(
            f"  {r['name']:40s} class={r['class']:20s} "
            f"Δ={r['delta']} ethΔ={eth_d}"
        )

    # 再跑 validator 自洽
    allowlist = json.loads(
        (OUT / "attribution_allowlist.json").read_text(encoding="utf-8")
    )
    try:
        validate_attribution_payload(attr, allowlist, before_map, after_map)
    except AssertionError as exc:
        print(f"[b6] FAIL validator: {exc}")
        return 1

    if attr["summary"]["n_unexpected"] > 0:
        print("[b6] FAIL: unexpected attribution rows")
        return 1
    if not attr["summary"]["control_stable"]:
        print("[b6] FAIL: control not stable")
        return 1
    print("[b6] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
