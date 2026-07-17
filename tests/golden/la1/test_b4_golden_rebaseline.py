"""LA-1 B4 Task 4.1 — golden 重基準 + 歸因收口 + 跨 symbol。

SPEC §G / TODO Task 4.1 / B4-fix (codex review):
  ① 三 control **各自獨立 run**（regime OFF / LS OFF / 非觸發 fallback）
     vs B0 control artifact element-level deep-equal（atol=1e-12）
  ② 修改路徑：**完整 baseline 五路徑 recursive diff** → allowlist 對帳
     （B4 只驗不 append；未枚舉欄位自動進對帳）
  ③ 跨 symbol ETHUSDT/12h：全量 live diffs 送 validator，gap>0 即 FAIL
  ④ machine line UNEXPECTED=0（freeze/format FAIL 時禁假綠）
  ⑤ 禁 kmeans 入 control；禁擅擴 allowlist
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import pytest

from momentum.Analysis.long_short_analyzer import LongShortAnalyzer
from momentum.factories import create_kline_storage_manager, create_regime_detector
from tests.golden.la1.attribution_validator import (
    allowlist_rows_fingerprint,
    deep_equal_json,
    load_allowlist,
    recursive_json_diff,
    validate_allowlist_not_expanded,
    validate_b4_attribution,
    validate_diffs_or_raise,
)
from tests.golden.la1.gen_baseline import (
    CONTROL_KINDS,
    CONTROL_SCHEMA_VERSION,
    CONTROL_VOLATILE_RECEIPT_NAME,
    CONTROL_VOLATILE_RULES_NAME,
    FALLBACK_TAIL_BARS,
    PATH_KEYS,
    RUNS,
    VOLATILE_SENTINEL_KEY,
    _assert_exact_rfc6901_pointer,
    _base_config_override,
    _hash_bool_array,
    _mask_payload,
    _materialize_short_features,
    _resolve_la0_feature_inputs,
    _run_analyze,
    _summarize_by_regime,
    _summarize_fallback,
    _summarize_long_short,
    _summarize_phases,
    assert_receipt_matches_rules,
    canonical_full_report,
    control_artifact_name,
    control_regime_off_config,
    control_volatile_receipt_path,
    control_volatile_rules_path,
    load_volatile_receipt,
    load_volatile_rules,
    rules_sha256,
    run_control_one,
    validate_volatile_value,
)
from tests.golden.la1.test_attribution_validator import (
    FROZEN_ALLOWLIST_ROW_COUNT,
    FROZEN_ALLOWLIST_ROWS_SHA256,
)

LA1_DIR = Path(__file__).resolve().parent
ALLOWLIST_PATH = LA1_DIR / "attribution_allowlist.json"
BTC_BASELINE_PATH = LA1_DIR / "BTCUSDT_1h_baseline.json"
ETH_BASELINE_PATH = LA1_DIR / "ETHUSDT_12h_baseline.json"
KLINE_CACHE_DIR = "data_cache/feature_klines"
ATOL = 1e-12

DEFAULT_RULE_CONFIG: Dict[str, Any] = {
    "regime_definitions": {
        "high_vol_percentile": 80,
        "low_vol_percentile": 20,
    },
    "method": "spearman",
}


def _regime_off_config() -> dict[str, Any]:
    """control-1 config（與 gen_baseline.control_regime_off_config 同源）。"""
    return control_regime_off_config()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _load_baseline(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _scalar_differs(old: Any, new: Any) -> bool:
    """old/new 是否不同（NaN==NaN）。與 test_la1_lookahead reverse scope 同源。"""
    if old != new:
        if isinstance(old, float) and isinstance(new, float):
            if old != old and new != new:  # NaN
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

    共享 allowlist 混有 BTC+ETH 真 diff：跨 symbol feature 子集 path 不在
    對側 baseline；同 path 的 value_sha256 則以 old≠B0 區分。
    """
    path = str(row.get("path") or "")
    found, leaf = _resolve_baseline_leaf(baseline, path)
    if not found:
        return False
    return not _scalar_differs(leaf, row.get("old"))


def _run_for_symbol(symbol: str) -> Tuple[dict, Path, Path]:
    run = next(r for r in RUNS if r["symbol"] == symbol)
    h5, meta = _resolve_la0_feature_inputs(run)
    return run, h5, meta


def _production_rule_masks(close: pd.Series) -> Dict[str, pd.Series]:
    from momentum.Analysis.ic_engine import ICEngine

    engine = ICEngine({"method": "spearman"})
    masks = engine._build_regime_rule_masks(close, DEFAULT_RULE_CONFIG)
    assert masks is not None
    return masks


def _read_kline(symbol: str, timeframe: str) -> pd.DataFrame:
    sm = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    raw = sm.read_klines(symbol, timeframe)
    assert raw is not None and not raw.empty
    return raw


def _b0_control_mask_artifact(baseline: dict) -> dict[str, Any]:
    """B0 control artifact：bull/bear mask_membership（P1-1 不改 bull/bear）。"""
    mm = (
        (baseline.get("regime_rule") or {})
        .get("mask_membership", {})
        .get("regimes", {})
    )
    out: dict[str, Any] = {}
    for side in ("bull", "bear"):
        assert side in mm, f"B0 missing control regime {side}"
        body = mm[side]
        out[side] = {
            "membership_sha256": body["membership_sha256"],
            "true_count": body["true_count"],
            "len": body["len"],
            "true_rate": body["true_rate"],
        }
    return out


def _live_control_mask_artifact(masks: Dict[str, pd.Series]) -> dict[str, Any]:
    payload = _mask_payload(masks)
    regimes = payload.get("regimes") or {}
    out: dict[str, Any] = {}
    for side in ("bull", "bear"):
        body = regimes[side]
        out[side] = {
            "membership_sha256": body["membership_sha256"],
            "true_count": body["true_count"],
            "len": body["len"],
            "true_rate": body["true_rate"],
        }
    return out


def _assert_deep_equal(
    old: Any, new: Any, *, label: str, atol: float = ATOL
) -> None:
    mismatches = deep_equal_json(old, new, path=label, atol=atol)
    assert not mismatches, f"{label} deep-equal FAIL ({len(mismatches)}):\n" + "\n".join(
        mismatches[:20]
    )


def _class_for_path(path: str) -> str:
    if path.startswith("long_short"):
        return "P1-2"
    if path.startswith("regime_kmeans") or path.startswith("xgboost_phases"):
        return "P1-1c"
    if path.startswith("regime_rule"):
        return "P1-1"
    if path.startswith("fallback"):
        return "P1-3-obs"
    if path in ("analysis_status", "oos_guarantees") or path.startswith(
        "summary_table"
    ) or path.startswith("filter_log"):
        return "P1-3-obs"
    return "P1-1"


def _index_for_path(path: str, symbol_tf: str) -> Any:
    """對齊 B1/B2/B3 allowlist index 慣例。"""
    parts = path.split(".")
    if path.startswith("regime_rule.mask_membership.regimes.") and len(parts) >= 4:
        return parts[3]
    if path.startswith("regime_rule.per_regime.") and len(parts) >= 3:
        rname = parts[2]
        if "per_feature" in parts:
            fi = parts.index("per_feature")
            feat = parts[fi + 1] if fi + 1 < len(parts) else rname
            return f"{rname}/{feat}"
        return rname
    if path.startswith("regime_kmeans.per_regime.") and len(parts) >= 3:
        rname = parts[2]
        if "per_feature" in parts:
            fi = parts.index("per_feature")
            feat = parts[fi + 1] if fi + 1 < len(parts) else rname
            return f"{rname}/{feat}"
        return rname
    if path.startswith("xgboost_phases.value_counts.") and len(parts) >= 3:
        return parts[2]
    if path.startswith("xgboost_phases"):
        return symbol_tf
    if path.startswith("long_short.features.") and len(parts) >= 3:
        return f"{symbol_tf}/{parts[2]}"
    if path.startswith("long_short"):
        return symbol_tf
    if path.startswith("fallback"):
        return symbol_tf
    if path == "analysis_status" or path == "oos_guarantees":
        return "root"
    if path == "summary_table.pass_class":
        return symbol_tf  # caller 覆寫為 feature
    return symbol_tf


def _retag_diffs(
    diffs: List[dict], *, symbol_tf: str
) -> List[dict]:
    out: List[dict] = []
    for d in diffs:
        path = d["path"]
        row = {
            "path": path,
            "index": _index_for_path(path, symbol_tf),
            "old": d["old"],
            "new": d["new"],
            "class": _class_for_path(path),
        }
        out.append(row)
    return out


def _build_live_five_path_artifact(
    symbol: str, timeframe: str, h5: Path, meta: Path, raw: pd.DataFrame
) -> dict[str, Any]:
    """與 gen_baseline 五路徑同形的 live artifact（post B1/B2/B3）。"""
    close = raw["close"].astype(float)
    volume = raw["volume"].astype(float)
    kline_ts = raw["timestamp"]
    symbol_tf = f"{symbol}/{timeframe}"

    # ① regime rule
    orch_rule, report_rule = _run_analyze(h5, meta, _base_config_override("rule"))
    by_regime_rule = (report_rule.get("grouped_ic") or {}).get("by_regime") or {}
    regime_rule_payload = _summarize_by_regime(by_regime_rule)
    masks_rule = _production_rule_masks(close)
    regime_rule_payload["mask_membership"] = _mask_payload(masks_rule)

    # ② kmeans
    _orch_km, report_km = _run_analyze(h5, meta, _base_config_override("kmeans"))
    by_regime_km = (report_km.get("grouped_ic") or {}).get("by_regime") or {}
    regime_km_payload = _summarize_by_regime(by_regime_km)

    # ③ xgboost phases
    det = create_regime_detector(
        n_clusters=4, lookback=55, min_samples_for_fit=100, refit_interval=50
    )
    phases = det.detect_phases_for_index(close, volume, index=close.index)
    phases_payload = _summarize_phases([str(x) for x in phases], kline_ts)

    # ④ long_short
    ic_cache = orch_rule._ic_cache or {}
    features_df = ic_cache.get("features_df")
    label_series = ic_cache.get("label_series")
    assert features_df is not None and label_series is not None
    ls_analyzer = LongShortAnalyzer(
        {
            "enabled": True,
            "num_quantiles": 5,
            "long_quantiles": [4, 5],
            "short_quantiles": [1, 2],
        }
    )
    ls_results = ls_analyzer.batch_analyze(
        features_df, label_series, top_n=len(features_df.columns)
    )
    long_short_payload = _summarize_long_short(ls_results)

    # ⑤ fallback（triggered 短樣本；與 B0 同形）
    run = next(r for r in RUNS if r["symbol"] == symbol)
    short_h5, short_meta = _materialize_short_features(
        h5, symbol, timeframe, run["config_hash"], FALLBACK_TAIL_BARS
    )
    fb_override = _base_config_override("rule")
    fb_override["min_test_rows"] = 10_000
    _orch_fb, report_fb = _run_analyze(short_h5, short_meta, fb_override)
    fallback_payload = _summarize_fallback(report_fb)
    fallback_payload["trigger_config"] = {
        "n_bars": FALLBACK_TAIL_BARS,
        "min_test_rows_override": 10_000,
    }

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "symbol_tf": symbol_tf,
        "regime_rule": regime_rule_payload,
        "regime_kmeans": regime_km_payload,
        "xgboost_phases": phases_payload,
        "long_short": long_short_payload,
        "fallback": fallback_payload,
        "report_rule": report_rule,
        "report_fb": report_fb,
        "report_km": report_km,
    }


def _five_path_recursive_diffs(
    baseline: dict, live: dict, *, symbol_tf: str
) -> List[dict]:
    """對 B0 baseline 五路徑做完整 recursive diff（canonical walker）。"""
    all_diffs: List[dict] = []
    for key in PATH_KEYS:
        old = baseline.get(key)
        new = live.get(key)
        raw_diffs = recursive_json_diff(
            old,
            new,
            path_prefix=key,
            class_name=_class_for_path(key),
            index=symbol_tf,
            atol=ATOL,
            default_index=symbol_tf,
        )
        all_diffs.extend(_retag_diffs(raw_diffs, symbol_tf=symbol_tf))
    return all_diffs


def _build_p13_obs_diffs(
    report_degraded: dict,
    report_ok: dict,
) -> List[dict]:
    """P1-3-obs：root 紅標 + summary pass_class + filter_log（B3 append 契約）。"""
    diffs: List[dict] = []
    for status, report in (
        ("degraded_full_sample", report_degraded),
        ("ok_oos", report_ok),
    ):
        st = report.get("analysis_status")
        if st is not None:
            diffs.append(
                {
                    "path": "analysis_status",
                    "index": "root",
                    "old": None,
                    "new": st,
                    "class": "P1-3-obs",
                }
            )
        oos = report.get("oos_guarantees")
        if oos is not None:
            diffs.append(
                {
                    "path": "oos_guarantees",
                    "index": "root",
                    "old": None,
                    "new": oos,
                    "class": "P1-3-obs",
                }
            )
        for row in report.get("summary_table") or []:
            if not isinstance(row, dict):
                continue
            feat = row.get("feature") or row.get("name") or row.get("feature_name")
            pc = row.get("pass_class")
            if feat is None or pc is None:
                continue
            diffs.append(
                {
                    "path": "summary_table.pass_class",
                    "index": feat,
                    "old": None,
                    "new": pc,
                    "class": "P1-3-obs",
                }
            )
        fl = report.get("filter_log") or {}
        s5 = fl.get("stage5_thresholds") or {}
        if isinstance(s5, dict):
            if s5.get("pass_class") is not None:
                diffs.append(
                    {
                        "path": "filter_log.stage5_thresholds.pass_class",
                        "index": (
                            status if status == "ok_oos" else "degraded_full_sample"
                        ),
                        "old": None,
                        "new": s5.get("pass_class"),
                        "class": "P1-3-obs",
                    }
                )
            out_f = s5.get("output_features") or {}
            if isinstance(out_f, dict) and out_f.get("pass_class") is not None:
                diffs.append(
                    {
                        "path": (
                            "filter_log.stage5_thresholds.output_features.pass_class"
                        ),
                        "index": (
                            status if status == "ok_oos" else "degraded_full_sample"
                        ),
                        "old": None,
                        "new": out_f.get("pass_class"),
                        "class": "P1-3-obs",
                    }
                )
    seen = set()
    uniq: List[dict] = []
    for d in diffs:
        key = (d["path"], d["index"], d["old"], d["new"], d["class"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(d)
    return uniq


# ---------------------------------------------------------------------------
# ① 0-skip 閘
# ---------------------------------------------------------------------------
def test_la1_lookahead_module_has_zero_skips() -> None:
    """Task 4.1①：test_la1_lookahead.py 殘 skip=FAIL。"""
    path = Path(__file__).resolve().parents[2] / "momentum" / "test_la1_lookahead.py"
    assert path.is_file(), path
    skip_hits: List[str] = []
    text = path.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.split("#", 1)[0]
        if "pytest.mark.skip" in stripped or "pytest.skip(" in stripped:
            skip_hits.append(f"line {i}: {stripped.strip()}")
        if "pytest.mark.xfail" in stripped:
            skip_hits.append(f"line {i}: {stripped.strip()}")
    assert not skip_hits, f"residual skip/xfail in test_la1_lookahead.py: {skip_hits}"


# ---------------------------------------------------------------------------
# ② 三 control 各自獨立 run + 凍結 **全樹** control artifact deep-equal
#    （B4-CODEX-1 SYNTHESIS：禁投影；volatile sentinel scrub）
# ---------------------------------------------------------------------------
def _control_artifact_path(symbol: str, timeframe: str, kind: str) -> Path:
    return LA1_DIR / control_artifact_name(symbol, timeframe, kind)


def _assert_control_artifact_full_tree(
    symbol: str, timeframe: str, kind: str
) -> dict[str, Any]:
    """載入凍結 full-tree control artifact，與 live ``run_control_one`` deep-equal。

    float abs atol=1e-12；NaN→typed marker；非 float exact；禁投影。
    """
    assert kind in CONTROL_KINDS
    art_path = _control_artifact_path(symbol, timeframe, kind)
    assert art_path.is_file(), (
        f"missing frozen control full artifact {art_path.name}; "
        f"run: python tests/golden/la1/gen_baseline.py --controls-only"
    )
    frozen = _load_baseline(art_path)
    run = next(
        r for r in RUNS if r["symbol"] == symbol and r["timeframe"] == timeframe
    )
    live = run_control_one(run, kind)
    _assert_deep_equal(
        frozen,
        live,
        label=f"{symbol}/{timeframe}.control_full.{kind}",
        atol=ATOL,
    )
    assert frozen["schema_version"] == CONTROL_SCHEMA_VERSION
    assert frozen["control_kind"] == kind
    assert frozen["symbol"] == symbol
    assert frozen["timeframe"] == timeframe
    report = frozen.get("report") or {}
    assert report.get("analysis_status") == "ok_oos"
    # 全樹契約：必含 summary_table（投影反例的關鍵欄）
    assert "summary_table" in report, (
        f"CONTROL_FULL_TREE_CHECK=FAIL reason=projection_keys "
        f"report_keys={sorted(report.keys())}"
    )
    assert isinstance(report["summary_table"], list)
    assert len(report["summary_table"]) > 0
    # volatile sentinel 存在
    gen = report.get("generated_at")
    assert isinstance(gen, dict) and gen.get(VOLATILE_SENTINEL_KEY) == "/generated_at"
    return frozen


@pytest.mark.parametrize(
    "symbol,timeframe,baseline_path,expected_rows",
    [
        ("BTCUSDT", "1h", BTC_BASELINE_PATH, 20352),
        ("ETHUSDT", "12h", ETH_BASELINE_PATH, 1696),
    ],
    ids=["BTCUSDT/1h", "ETHUSDT/12h"],
)
def test_b4_control_regime_off_deep_equal(
    symbol: str,
    timeframe: str,
    baseline_path: Path,
    expected_rows: int,
) -> None:
    """control-1：regime OFF 全樹 deep-equal（非投影）。"""
    raw = _read_kline(symbol, timeframe)
    assert len(raw) == expected_rows
    close = raw["close"].astype(float)

    frozen = _assert_control_artifact_full_tree(symbol, timeframe, "regime_off")
    by_regime = (frozen["report"].get("grouped_ic") or {}).get("by_regime") or {}
    _assert_deep_equal(
        {},
        by_regime,
        label=f"{symbol}.regime_off.by_regime_frozen",
    )

    # high/low 為修改路徑（非 control）；BTC 必須與 B0 main baseline 不同
    baseline = _load_baseline(baseline_path)
    live_masks = _production_rule_masks(close)
    base_mm = (
        (baseline.get("regime_rule") or {})
        .get("mask_membership", {})
        .get("regimes", {})
    )
    for side in ("high_vol", "low_vol"):
        if side not in base_mm:
            continue
        live_tc = int(live_masks[side].astype(bool).sum())
        if symbol == "BTCUSDT":
            assert live_tc != int(base_mm[side]["true_count"]), side

    # kmeans 不入 control artifact envelope
    assert "regime_kmeans" not in frozen
    assert "kmeans" not in json.dumps(frozen.get("control_config") or {})


@pytest.mark.parametrize(
    "symbol,timeframe,baseline_path",
    [
        ("BTCUSDT", "1h", BTC_BASELINE_PATH),
        ("ETHUSDT", "12h", ETH_BASELINE_PATH),
    ],
    ids=["BTCUSDT/1h", "ETHUSDT/12h"],
)
def test_b4_control_ls_off_deep_equal(
    symbol: str,
    timeframe: str,
    baseline_path: Path,
) -> None:
    """control-2：LS OFF 全樹 deep-equal。"""
    frozen = _assert_control_artifact_full_tree(symbol, timeframe, "ls_off")
    # LS OFF：report 頂層可能無 long_short 或 features 空
    ls = frozen["report"].get("long_short") or frozen["report"].get(
        "long_short_analysis"
    )
    if isinstance(ls, dict):
        feats = ls.get("features") or ls.get("results") or {}
        _assert_deep_equal(
            {},
            feats,
            label=f"{symbol}.ls_off.features_frozen",
        )
    baseline = _load_baseline(baseline_path)
    _assert_deep_equal(
        _b0_control_mask_artifact(baseline),
        frozen["mask_membership_control"],
        label=f"{symbol}.ls_off.bull_bear_vs_b0",
    )


@pytest.mark.parametrize(
    "symbol,timeframe,baseline_path",
    [
        ("BTCUSDT", "1h", BTC_BASELINE_PATH),
        ("ETHUSDT", "12h", ETH_BASELINE_PATH),
    ],
    ids=["BTCUSDT/1h", "ETHUSDT/12h"],
)
def test_b4_control_non_trigger_fallback_deep_equal(
    symbol: str,
    timeframe: str,
    baseline_path: Path,
) -> None:
    """control-3：非觸發 fallback 全樹 deep-equal。"""
    frozen = _assert_control_artifact_full_tree(
        symbol, timeframe, "non_trigger_fallback"
    )
    assert frozen["report"]["oos_guarantees"] is True
    assert frozen["report"]["analysis_status"] == "ok_oos"
    baseline = _load_baseline(baseline_path)
    _assert_deep_equal(
        _b0_control_mask_artifact(baseline),
        frozen["mask_membership_control"],
        label=f"{symbol}.non_trigger.bull_bear_vs_b0",
    )


# ---------------------------------------------------------------------------
# ②b SYNTHESIS 負例（全必紅）+ 投影移除 + 兩跑穩定
# ---------------------------------------------------------------------------
def test_control_projection_removed() -> None:
    """gen_baseline 無 _control_report_section；artifact report 含 summary_table。"""
    src = (LA1_DIR / "gen_baseline.py").read_text(encoding="utf-8")
    assert "_control_report_section" not in src
    frozen = _load_baseline(
        _control_artifact_path("BTCUSDT", "1h", "regime_off")
    )
    assert "summary_table" in (frozen.get("report") or {})
    assert frozen.get("schema_version") == CONTROL_SCHEMA_VERSION


def test_control_full_tree_detects_raw_drift() -> None:
    """① codex 反例：raw summary_table[0] 數值 leaf 竄改 → deep-equal 必紅。

    實欄位為 ``ic_mean``（report 無 ``ic`` 鍵）；mutate 999 後 mismatch 必命中。
    """
    frozen = _load_baseline(
        _control_artifact_path("BTCUSDT", "1h", "regime_off")
    )
    report = frozen["report"]
    row0 = report["summary_table"][0]
    # 優先 ic，否則 ic_mean（實欄）
    field = "ic" if "ic" in row0 else "ic_mean"
    assert field in row0, f"no numeric ic field in summary_table[0]: {sorted(row0)}"
    original = row0[field]
    assert original != 999.0

    mutated = json.loads(json.dumps(report))  # deep copy via json
    mutated["summary_table"][0][field] = 999.0
    mismatches = deep_equal_json(
        report, mutated, path="report", atol=ATOL
    )
    assert mismatches, (
        "CONTROL_DRIFT_TEST=FAIL reason=mutation_invisible "
        f"path=report.summary_table[0].{field}"
    )
    assert any(
        f"summary_table" in m and field in m for m in mismatches
    ), mismatches[:5]
    # receipt 給交接
    print(
        f"CODEX_IC_COUNTEREXAMPLE_RED field={field} "
        f"original={original!r} mutated=999.0 "
        f"mismatch_count={len(mismatches)} sample={mismatches[0]!r}"
    )


def test_control_denylist_inject_ic_mean_fails() -> None:
    """② denylist 塞 /summary_table/0/ic_mean → 型別/格式 validator 必紅。"""
    rules = load_volatile_rules()
    bad = {
        "pointer": "/summary_table/0/ic_mean",
        "expected_type": "str",
        "validator": "iso8601_timestamp",
        "reason": "tamper inject",
        "producer_ref": "test",
    }
    # 對真實 report 值（float）驗證應 FAIL
    frozen = _load_baseline(
        _control_artifact_path("BTCUSDT", "1h", "regime_off")
    )
    # frozen 已 scrub；用 live raw
    run = next(r for r in RUNS if r["symbol"] == "BTCUSDT")
    live = run_control_one(run, "regime_off")
    # live report 已 scrub；重新拿 raw
    from tests.golden.la1.gen_baseline import (
        _run_analyze_isolated,
        control_config_for_kind,
        _resolve_la0_feature_inputs as _res,
    )
    h5, meta = _res(run)
    raw_report = _run_analyze_isolated(h5, meta, control_config_for_kind("regime_off"))
    ic_val = raw_report["summary_table"][0]["ic_mean"]
    with pytest.raises(ValueError, match="volatile type mismatch|format fail"):
        validate_volatile_value(ic_val, bad)
    # 整包 canonical 亦紅
    with pytest.raises(ValueError):
        canonical_full_report(raw_report, rules + [bad])


def test_control_glob_pointer_forbidden() -> None:
    """③ pointer 改 glob → FAIL。"""
    with pytest.raises(ValueError, match="glob"):
        _assert_exact_rfc6901_pointer("/metadata/*_path")
    with pytest.raises(ValueError, match="glob|RFC6901|pointer"):
        canonical_full_report(
            {"generated_at": "2026-01-01T00:00:00"},
            [
                {
                    "pointer": "/generated_at*",
                    "expected_type": "str",
                    "validator": "iso8601_timestamp",
                    "reason": "x",
                    "producer_ref": "x",
                }
            ],
        )


def test_control_unused_pointer_fails() -> None:
    """④ unused pointer（report 無此鍵）→ FAIL。"""
    rules = [
        {
            "pointer": "/does_not_exist_volatile",
            "expected_type": "str",
            "validator": "iso8601_timestamp",
            "reason": "unused",
            "producer_ref": "test",
        }
    ]
    with pytest.raises(ValueError, match="unused volatile pointer"):
        canonical_full_report({"generated_at": "2026-01-01T00:00:00"}, rules)


def test_control_wrong_type_or_format_fails() -> None:
    """⑤ 原值型別/格式錯 → FAIL。"""
    rules = load_volatile_rules()
    # 型別錯：int 充 str timestamp
    with pytest.raises(ValueError, match="type mismatch|format fail"):
        canonical_full_report(
            {
                "generated_at": 12345,
                "metadata": {
                    "filtered_generated_at": "2026-01-01T00:00:00",
                    "filtered_features_path": (
                        "/var/folders/x/T/la1_b0_sidefx_x/features/a.h5"
                    ),
                },
            },
            rules,
        )
    # 格式錯：非 ISO timestamp
    with pytest.raises(ValueError, match="format fail|type mismatch"):
        canonical_full_report(
            {
                "generated_at": "not-a-timestamp",
                "metadata": {
                    "filtered_generated_at": "2026-01-01T00:00:00",
                    "filtered_features_path": (
                        "/var/folders/x/T/la1_b0_sidefx_x/features/a.h5"
                    ),
                },
            },
            rules,
        )


def test_control_receipt_observed_ne_rules_fails() -> None:
    """⑥ receipt observed ≠ rules → FAIL。"""
    rules = load_volatile_rules()
    receipt = load_volatile_receipt()
    bad_receipt = dict(receipt)
    bad_receipt["observed_pointers"] = list(receipt["observed_pointers"]) + [
        "/extra_fake_pointer"
    ]
    with pytest.raises(ValueError, match="receipt observed"):
        assert_receipt_matches_rules(bad_receipt, rules)
    # 少一個
    bad2 = dict(receipt)
    bad2["observed_pointers"] = list(receipt["observed_pointers"])[:-1]
    with pytest.raises(ValueError, match="receipt observed"):
        assert_receipt_matches_rules(bad2, rules)


def test_control_rules_receipt_artifact_sha_tamper_fails() -> None:
    """⑦ rules/receipt/artifact 任一 sha 改動 → 自洽檢查紅。"""
    rules = load_volatile_rules()
    rsha = rules_sha256(rules)
    receipt = load_volatile_receipt()
    assert receipt.get("rules_sha256") == rsha

    # rules sha 改動
    tampered_rules = [dict(r) for r in rules]
    tampered_rules[0] = dict(tampered_rules[0])
    tampered_rules[0]["reason"] = "tampered"
    assert rules_sha256(tampered_rules) != rsha

    # receipt.rules_sha256 與真實 rules 不一致
    bad_receipt = dict(receipt)
    bad_receipt["rules_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="rules_sha256 mismatch"):
        assert_receipt_matches_rules(bad_receipt, rules)

    # artifact content_sha256 改動
    frozen = _load_baseline(
        _control_artifact_path("BTCUSDT", "1h", "regime_off")
    )
    body_wo = {k: v for k, v in frozen.items() if k != "content_sha256"}
    from tests.golden.la1.gen_baseline import _canonical_json_bytes, _sha256_bytes

    recomputed = _sha256_bytes(_canonical_json_bytes(body_wo))
    assert recomputed == frozen["content_sha256"]
    frozen_bad = dict(frozen)
    frozen_bad["content_sha256"] = "f" * 64
    assert frozen_bad["content_sha256"] != recomputed


def test_control_two_run_stable() -> None:
    """兩次重跑 full-tree 相等（flaky=denylist 不足=紅）。"""
    run = next(r for r in RUNS if r["symbol"] == "BTCUSDT")
    a = run_control_one(run, "regime_off")
    b = run_control_one(run, "regime_off")
    _assert_deep_equal(
        a, b, label="BTCUSDT.control_two_run.regime_off", atol=ATOL
    )
    # 與凍結 artifact 亦相等
    frozen = _load_baseline(
        _control_artifact_path("BTCUSDT", "1h", "regime_off")
    )
    _assert_deep_equal(
        frozen, a, label="BTCUSDT.control_two_run_vs_frozen", atol=ATOL
    )


def test_control_volatile_rules_and_receipt_files_exist() -> None:
    """rules + receipt 凍結檔存在且集合相等。"""
    assert control_volatile_rules_path().name == CONTROL_VOLATILE_RULES_NAME
    assert control_volatile_receipt_path().name == CONTROL_VOLATILE_RECEIPT_NAME
    rules = load_volatile_rules()
    receipt = load_volatile_receipt()
    assert_receipt_matches_rules(receipt, rules)
    assert len(rules) >= 1
    for r in rules:
        assert r["pointer"].startswith("/")
        assert "*" not in r["pointer"]


# ---------------------------------------------------------------------------
# ③ 修改路徑：完整 recursive five-path diff + P1-3-obs → UNEXPECTED 對帳
# ---------------------------------------------------------------------------
def test_b4_modified_path_attribution_unexpected_zero() -> None:
    """BTC 五路徑 recursive diff + P1-3-obs ⊆ allowlist；machine line UNEXPECTED=0。

    B4 只驗不 append；freeze fingerprint = dba5716 literal。
    若 allowlist discriminator 與 live 不一致 → 如實 FAIL（勿為綠改 allowlist）。
    """
    allowlist = load_allowlist(ALLOWLIST_PATH)
    assert len(allowlist.get("rows") or []) == FROZEN_ALLOWLIST_ROW_COUNT
    assert (
        allowlist_rows_fingerprint(allowlist) == FROZEN_ALLOWLIST_ROWS_SHA256
    )
    freeze_errs = validate_allowlist_not_expanded(
        allowlist, frozen_fingerprint=FROZEN_ALLOWLIST_ROWS_SHA256
    )
    assert not freeze_errs, freeze_errs

    baseline = _load_baseline(BTC_BASELINE_PATH)
    run, h5, meta = _run_for_symbol("BTCUSDT")
    symbol_tf = f"{run['symbol']}/{run['timeframe']}"
    raw = _read_kline(run["symbol"], run["timeframe"])

    live = _build_live_five_path_artifact(
        run["symbol"], run["timeframe"], h5, meta, raw
    )

    # 完整 recursive（禁手選 builders）
    all_diffs = _five_path_recursive_diffs(baseline, live, symbol_tf=symbol_tf)

    # control bull/bear 不得進 diff
    control_leaks = [
        d
        for d in all_diffs
        if ".regimes.bull." in d["path"] or ".regimes.bear." in d["path"]
        or d["path"].endswith(".regimes.bull") or d["path"].endswith(".regimes.bear")
    ]
    assert control_leaks == [], f"control bull/bear leaked: {control_leaks[:5]}"

    # P1-3-obs（report-root；不在五路徑 JSON）
    _orch_ok, report_ok = _run_analyze(h5, meta, _regime_off_config())
    assert report_ok.get("analysis_status") == "ok_oos"
    p13 = _build_p13_obs_diffs(live["report_fb"], report_ok)
    assert p13, "expected P1-3-obs diffs"
    all_diffs.extend(p13)

    assert all_diffs, "expected non-empty modified-path diffs"

    result = validate_b4_attribution(
        all_diffs,
        allowlist,
        frozen_fingerprint=FROZEN_ALLOWLIST_ROWS_SHA256,
    )
    # 如實輸出：綠則 UNEXPECTED=0；紅則帶 unexpected 摘要（勿為綠妥協）
    if not result.ok:
        # 結構化失敗摘要（供 handoff / 編排端裁決 B1-B3 discriminator）
        sample = result.unexpected[:30]
        fmt = result.format_errors[:5]
        pytest.fail(
            f"BTC attribution RED: {result.machine_line()} "
            f"unexpected_count={result.unexpected_count} "
            f"format_errors={fmt!r} sample={sample!r}"
        )
    assert result.machine_line() == "UNEXPECTED=0"
    assert result.unexpected_count == 0
    validate_diffs_or_raise(all_diffs, allowlist)


# ---------------------------------------------------------------------------
# ④ 跨 symbol ETH：全量 diffs 送 validator；gap>0 即 FAIL
# ---------------------------------------------------------------------------
def test_b4_cross_symbol_eth_independent() -> None:
    """ETHUSDT/12h：control + 全修改路徑 recursive；零容忍 gap + ETH reverse。

    forward：all_diffs ⊆ allowlist（UNEXPECTED=0）。
    reverse：allowlist 中 **ETH-scoped** P1-1c regime_kmeans/xgboost_phases
    列皆須被本測 ETH builder 真 diff 命中（鏡像 BTC reverse；baseline=ETH）。
    BTC-scoped 列 skip，但 n_cross_symbol_skipped>0 防刪跨 symbol 真 row。
    """
    allowlist = load_allowlist(ALLOWLIST_PATH)
    baseline = _load_baseline(ETH_BASELINE_PATH)
    assert baseline["symbol"] == "ETHUSDT"
    assert baseline["timeframe"] == "12h"
    btc = _load_baseline(BTC_BASELINE_PATH)
    assert baseline["input_contract"]["kline_sha16"] != btc["input_contract"]["kline_sha16"]
    assert baseline["input_contract"]["kline_rows"] == 1696

    run, h5, meta = _run_for_symbol("ETHUSDT")
    symbol_tf = f"{run['symbol']}/{run['timeframe']}"
    raw = _read_kline("ETHUSDT", "12h")
    close = raw["close"].astype(float)

    # control bull/bear deep-equal
    _assert_deep_equal(
        _b0_control_mask_artifact(baseline),
        _live_control_mask_artifact(_production_rule_masks(close)),
        label="ETH.control.bull_bear",
    )

    live = _build_live_five_path_artifact(
        run["symbol"], run["timeframe"], h5, meta, raw
    )
    all_diffs = _five_path_recursive_diffs(baseline, live, symbol_tf=symbol_tf)

    _orch_ok, report_ok = _run_analyze(h5, meta, _regime_off_config())
    assert report_ok.get("analysis_status") == "ok_oos"
    all_diffs.extend(_build_p13_obs_diffs(live["report_fb"], report_ok))

    assert all_diffs, "ETH expected modified-path diffs vs B0"

    # 零容忍：全量 diffs 原封不動送 validator（禁 covered/gaps 篩選）
    result = validate_b4_attribution(
        all_diffs,
        allowlist,
        frozen_fingerprint=FROZEN_ALLOWLIST_ROWS_SHA256,
    )
    if not result.ok:
        sample = result.unexpected[:30]
        pytest.fail(
            f"ETH attribution RED: {result.machine_line()} "
            f"unexpected_count={result.unexpected_count} sample={sample!r}"
        )
    assert result.machine_line() == "UNEXPECTED=0"
    assert result.unexpected_count == 0
    validate_diffs_or_raise(all_diffs, allowlist)

    # 反向：allowlist 中 **ETH-scoped** xgboost_phases + regime_kmeans P1-1c
    # 列皆須被本測 ETH five-path builder 真 diff 命中。
    #
    # 共享 allowlist 含 BTC recursive 列；本測只跑 ETH/12h，builder 無法產出
    # BTC leaf → 反向只要求「path 在 ETH baseline 且 old==ETH B0 leaf」。
    # 禁為綠刪 BTC 真 diff（BTC reverse / B4 BTC forward 仍需那些列）。
    # allowlist P1-1c 五鍵皆為可 hash 標量；recursive walker 偶有 dict leaf
    # （非 P1-1c 帳本列），建 set 時略過 unhashable，不影響 reverse 比對。
    produced_keys: set[tuple] = set()
    for d in all_diffs:
        key = (d["path"], d["index"], d["old"], d["new"], d["class"])
        try:
            hash(key)
        except TypeError:
            continue
        produced_keys.add(key)
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
        assert key in produced_keys, f"allowlist P1-1c row not produced (ETH): {row}"
    assert n_km_allow > 0, "allowlist missing ETH-scoped regime_kmeans.* P1-1c rows"
    assert n_xgb_allow > 0, "allowlist missing ETH-scoped xgboost_phases.* P1-1c rows"
    # BTC-only / cross-symbol 列必須存在於共享帳本（否則 BTC reverse 會紅），
    # 且不得被誤當 ETH reverse 必達。
    assert n_cross_symbol_skipped > 0, (
        "expected cross-symbol P1-1c rows in shared allowlist "
        f"(km BTC feats / BTC xgb); got skipped={n_cross_symbol_skipped}"
    )


def test_b4_machine_line_unexpected_zero_empty_and_listed() -> None:
    """validator machine line 契約：空 diff / 全 listed → UNEXPECTED=0。"""
    allowlist = load_allowlist(ALLOWLIST_PATH)
    r0 = validate_b4_attribution(
        [], allowlist, frozen_fingerprint=FROZEN_ALLOWLIST_ROWS_SHA256
    )
    assert r0.machine_line() == "UNEXPECTED=0"
    row = next(r for r in allowlist["rows"] if r.get("class") == "P1-1")
    listed = [
        {
            "path": row["path"],
            "index": row["index"],
            "old": row["old"],
            "new": row["new"],
            "class": row["class"],
        }
    ]
    r1 = validate_b4_attribution(
        listed,
        allowlist,
        frozen_fingerprint=FROZEN_ALLOWLIST_ROWS_SHA256,
    )
    assert r1.machine_line() == "UNEXPECTED=0"
    assert r1.ok is True


def test_b4_recursive_diff_catches_unenumerated_field() -> None:
    """未枚舉欄位 mutation 經 recursive walker 自動進對帳。"""
    old = {
        "regime_rule": {
            "mask_membership": {
                "regimes": {
                    "high_vol": {
                        "membership_sha256": "a" * 64,
                        "true_count": 10,
                        "true_rate": 0.1,
                    }
                }
            }
        }
    }
    new = {
        "regime_rule": {
            "mask_membership": {
                "regimes": {
                    "high_vol": {
                        "membership_sha256": "a" * 64,
                        "true_count": 10,
                        "true_rate": 0.999,  # 未在 allowlist 的欄位
                    }
                }
            }
        }
    }
    diffs = recursive_json_diff(
        old["regime_rule"],
        new["regime_rule"],
        path_prefix="regime_rule",
        class_name="P1-1",
        index="high_vol",
        atol=ATOL,
    )
    paths = {d["path"] for d in diffs}
    assert "regime_rule.mask_membership.regimes.high_vol.true_rate" in paths
    allowlist = load_allowlist(ALLOWLIST_PATH)
    tagged = _retag_diffs(diffs, symbol_tf="BTCUSDT/1h")
    result = validate_b4_attribution(
        tagged, allowlist, frozen_fingerprint=FROZEN_ALLOWLIST_ROWS_SHA256
    )
    assert result.ok is False
    assert result.unexpected_count >= 1
    assert result.machine_line().startswith("UNEXPECTED=")
    assert result.machine_line() != "UNEXPECTED=0"
